"""Build and run a LangGraph ReAct SQL agent over the sample database."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent
from sqlalchemy.engine import Engine

from app.agent.llm import build_chat_model
from app.agent.parsing import ParsedAgentResult, parse_agent_messages
from app.agent.prompts import sql_agent_system_prompt
from app.config import Settings, get_settings
from app.db.engine import create_db_engine, sqlite_url_for_path
from app.db.introspect import schema_prompt_text


@dataclass
class SqlAgentResult:
    question: str
    answer: str
    sql_queries: list[str] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)
    model: str = ""
    database: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_sql_database(
    settings: Settings | None = None,
    *,
    engine: Engine | None = None,
) -> SQLDatabase:
    """Wrap the sample SQLite DB in LangChain's SQLDatabase helper."""
    settings = settings or get_settings()
    if engine is not None:
        return SQLDatabase(engine)
    path = settings.sqlite_path
    return SQLDatabase.from_uri(sqlite_url_for_path(path))


def build_sql_agent(
    settings: Settings | None = None,
    *,
    engine: Engine | None = None,
    llm: Any | None = None,
) -> tuple[CompiledStateGraph, SQLDatabase]:
    """Create a ReAct agent with list/schema/query/checker SQL tools."""
    settings = settings or get_settings()
    llm = llm or build_chat_model(settings)
    db = build_sql_database(settings, engine=engine)
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = toolkit.get_tools()
    engine_for_schema = engine or create_db_engine(settings)
    prompt = sql_agent_system_prompt(
        dialect=db.dialect,
        top_k=min(5, settings.sql_row_limit),
        schema_text=schema_prompt_text(engine_for_schema, sample_rows=2),
    )
    agent = create_react_agent(llm, tools, prompt=prompt)
    return agent, db


def ask_database(
    question: str,
    *,
    settings: Settings | None = None,
    engine: Engine | None = None,
    llm: Any | None = None,
    agent: CompiledStateGraph | None = None,
) -> SqlAgentResult:
    """Run one natural-language question through the SQL agent."""
    settings = settings or get_settings()
    question = question.strip()
    if not question:
        raise ValueError("question must not be empty")

    if agent is None:
        agent, _db = build_sql_agent(settings, engine=engine, llm=llm)
    else:
        _db = build_sql_database(settings, engine=engine)

    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"recursion_limit": settings.agent_recursion_limit},
    )
    messages = result.get("messages", [])
    parsed: ParsedAgentResult = parse_agent_messages(messages)
    return SqlAgentResult(
        question=question,
        answer=parsed.answer,
        sql_queries=parsed.sql_queries,
        steps=[
            {
                "kind": step.kind,
                "name": step.name,
                "content": step.content,
                "tool_input": step.tool_input,
            }
            for step in parsed.steps
        ],
        model=settings.ollama_model,
        database=Path(settings.sqlite_path).name,
    )


def ollama_reachable(settings: Settings | None = None) -> bool:
    """Best-effort check that the Ollama HTTP API responds."""
    import urllib.error
    import urllib.request

    settings = settings or get_settings()
    url = settings.ollama_base_url.rstrip("/") + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=2.0) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def ensure_engine(settings: Settings | None = None) -> Engine:
    """Create an engine for the configured sample database."""
    return create_db_engine(settings or get_settings())
