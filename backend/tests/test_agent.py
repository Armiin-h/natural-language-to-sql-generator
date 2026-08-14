"""Unit tests for SQL agent parsing and toolkit wiring."""

from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent.parsing import extract_sql_from_tool_input, parse_agent_messages
from app.agent.prompts import sql_agent_system_prompt
from app.agent.sql_agent import SqlAgentResult, ask_database, build_sql_database
from app.config import get_settings
from app.db.seed import ensure_database


def test_system_prompt_mentions_read_only():
    prompt = sql_agent_system_prompt(
        dialect="sqlite",
        top_k=5,
        schema_text="Table products(id INTEGER, name VARCHAR)",
    )
    assert "SELECT" in prompt
    assert "INSERT" in prompt
    assert "sqlite" in prompt
    assert "Table products" in prompt
    assert "sql_db_query" in prompt


def test_extract_sql_from_tool_input():
    assert extract_sql_from_tool_input({"query": "SELECT 1"}) == "SELECT 1"
    assert extract_sql_from_tool_input({"input": "products, orders"}) is None
    assert extract_sql_from_tool_input({"input": "select name from products"}) is not None


def test_parse_agent_messages_captures_sql_and_answer():
    messages = [
        HumanMessage(content="Top products by sales"),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "sql_db_query",
                    "args": {
                        "query": (
                            "SELECT p.name, SUM(oi.quantity * oi.unit_price) AS sales "
                            "FROM order_items oi JOIN products p ON p.id = oi.product_id "
                            "GROUP BY p.name ORDER BY sales DESC LIMIT 5"
                        )
                    },
                    "id": "call-1",
                    "type": "tool_call",
                }
            ],
        ),
        ToolMessage(content="[('4K Monitor', 658.0)]", tool_call_id="call-1", name="sql_db_query"),
        AIMessage(content="The top product by sales is 4K Monitor at 658.00."),
    ]
    parsed = parse_agent_messages(messages)
    assert parsed.answer.startswith("The top product")
    assert len(parsed.sql_queries) == 1
    assert "ORDER BY sales DESC" in parsed.sql_queries[0]
    assert any(step.kind == "tool_call" for step in parsed.steps)


def test_sql_toolkit_exposes_expected_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "agent.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()
    settings = get_settings()
    ensure_database(settings.sqlite_path, reset=True)

    from langchain_community.agent_toolkits import SQLDatabaseToolkit
    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    llm = FakeListChatModel(responses=["ok"])
    db = build_sql_database(settings)
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tool_names = {tool.name for tool in toolkit.get_tools()}
    assert {
        "sql_db_query",
        "sql_db_schema",
        "sql_db_list_tables",
        "sql_db_query_checker",
    }.issubset(tool_names)
    get_settings.cache_clear()


def test_ask_database_with_stub_agent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "ask.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()
    settings = get_settings()
    ensure_database(settings.sqlite_path, reset=True)

    class StubAgent:
        def invoke(self, _payload, config=None):
            return {
                "messages": [
                    HumanMessage(content="How many products?"),
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "sql_db_query",
                                "args": {"query": "SELECT COUNT(*) AS n FROM products"},
                                "id": "c1",
                                "type": "tool_call",
                            }
                        ],
                    ),
                    ToolMessage(content="[(10,)]", tool_call_id="c1", name="sql_db_query"),
                    AIMessage(content="There are 10 products."),
                ]
            }

    result = ask_database(
        "How many products?",
        settings=settings,
        agent=StubAgent(),
    )
    assert isinstance(result, SqlAgentResult)
    assert result.success is True
    assert result.answer == "There are 10 products."
    assert result.final_sql is not None
    assert "COUNT(*)" in result.final_sql.upper()
    assert result.row_count == 1
    assert result.rows[0][0] == 10
    assert result.database == "ask.db"
    get_settings.cache_clear()


def test_build_sql_database_lists_tables(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "list.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()
    settings = get_settings()
    ensure_database(settings.sqlite_path, reset=True)
    db = build_sql_database(settings)
    names = set(db.get_usable_table_names())
    assert names == {"categories", "customers", "order_items", "orders", "products"}
    get_settings.cache_clear()


def test_safe_query_tool_rejects_delete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "tool.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()
    settings = get_settings()
    ensure_database(settings.sqlite_path, reset=True)

    from langchain_community.agent_toolkits import SQLDatabaseToolkit
    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    from app.agent.tools import build_safe_sql_tools
    from app.db.engine import create_db_engine

    llm = FakeListChatModel(responses=["ok"])
    engine = create_db_engine(settings)
    db = build_sql_database(settings, engine=engine)
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = {
        tool.name: tool
        for tool in build_safe_sql_tools(toolkit=toolkit, engine=engine, settings=settings)
    }
    query_tool = tools["sql_db_query"]
    output = query_tool.invoke({"query": "DELETE FROM products"})
    assert "Error" in output
    assert "Blocked" in output or "read-only" in output.lower()
    get_settings.cache_clear()
