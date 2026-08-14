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

from app.agent.executor import ExecutionResult, execute_readonly
from app.agent.llm import build_chat_model
from app.agent.parsing import ParsedAgentResult, parse_agent_messages
from app.agent.prompts import sql_agent_system_prompt
from app.agent.safety import validate_sql
from app.agent.tools import build_safe_sql_tools
from app.config import Settings, get_settings
from app.db.engine import create_db_engine, sqlite_url_for_path
from app.db.introspect import schema_prompt_text


@dataclass
class SqlAgentResult:
    question: str
    answer: str
    sql_queries: list[str] = field(default_factory=list)
    final_sql: str | None = None
    columns: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    success: bool = False
    error: str | None = None
    attempts: int = 1
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
) -> tuple[CompiledStateGraph, SQLDatabase, Engine]:
    """Create a ReAct agent with list/schema/checker tools + safe query tool."""
    settings = settings or get_settings()
    llm = llm or build_chat_model(settings)
    engine = engine or create_db_engine(settings)
    db = build_sql_database(settings, engine=engine)
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = build_safe_sql_tools(toolkit=toolkit, engine=engine, settings=settings)
    prompt = sql_agent_system_prompt(
        dialect=db.dialect,
        top_k=min(5, settings.sql_row_limit),
        schema_text=schema_prompt_text(engine, sample_rows=2),
    )
    agent = create_react_agent(llm, tools, prompt=prompt)
    return agent, db, engine


def _candidate_sqls(parsed: ParsedAgentResult) -> list[str]:
    """Prefer later queries (final attempts) when materializing tabular results."""
    return list(reversed(parsed.sql_queries))


def _materialize_rows(
    engine: Engine,
    parsed: ParsedAgentResult,
    settings: Settings,
) -> ExecutionResult | None:
    last_error: ExecutionResult | None = None
    for sql in _candidate_sqls(parsed):
        result = execute_readonly(
            engine,
            sql,
            row_limit=settings.sql_row_limit,
            timeout_seconds=settings.sql_timeout_seconds,
        )
        if result.ok:
            return result
        last_error = result
    return last_error


def ask_database(
    question: str,
    *,
    settings: Settings | None = None,
    engine: Engine | None = None,
    llm: Any | None = None,
    agent: CompiledStateGraph | None = None,
) -> SqlAgentResult:
    """Run one natural-language question through the SQL agent with retries."""
    settings = settings or get_settings()
    question = question.strip()
    if not question:
        raise ValueError("question must not be empty")

    owned_engine = engine
    if agent is None:
        agent, _db, owned_engine = build_sql_agent(settings, engine=engine, llm=llm)
    else:
        owned_engine = engine or create_db_engine(settings)

    assert owned_engine is not None

    all_steps: list[dict[str, Any]] = []
    all_sql: list[str] = []
    answer = ""
    last_exec: ExecutionResult | None = None
    last_error: str | None = None

    max_attempts = max(1, settings.sql_max_attempts)
    for attempt in range(1, max_attempts + 1):
        user_content = question
        if last_error:
            user_content = (
                f"{question}\n\n"
                f"Previous attempt failed with this error:\n{last_error}\n"
                "Inspect the schema if needed, rewrite a valid SELECT, "
                "and call sql_db_query again. Do not invent rows."
            )

        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_content}]},
            config={"recursion_limit": settings.agent_recursion_limit},
        )
        messages = result.get("messages", [])
        parsed: ParsedAgentResult = parse_agent_messages(messages)
        answer = parsed.answer or answer
        all_sql.extend(sql for sql in parsed.sql_queries if sql not in all_sql)
        all_steps.extend(
            {
                "kind": step.kind,
                "name": step.name,
                "content": step.content,
                "tool_input": step.tool_input,
                "attempt": attempt,
            }
            for step in parsed.steps
        )

        last_exec = _materialize_rows(owned_engine, parsed, settings)
        if last_exec is not None and last_exec.ok:
            return SqlAgentResult(
                question=question,
                answer=answer,
                sql_queries=all_sql,
                final_sql=last_exec.sql,
                columns=last_exec.columns,
                rows=last_exec.rows,
                row_count=last_exec.row_count,
                truncated=last_exec.truncated,
                success=True,
                error=None,
                attempts=attempt,
                steps=all_steps,
                model=settings.ollama_model,
                database=Path(settings.sqlite_path).name,
            )

        if last_exec is not None and last_exec.error:
            last_error = last_exec.error
        elif parsed.sql_queries:
            # SQL present but failed validation during materialize
            check = validate_sql(parsed.sql_queries[-1], row_limit=settings.sql_row_limit)
            last_error = check.message or "Query execution failed."
        else:
            last_error = "Agent did not produce an executable SQL query."

    return SqlAgentResult(
        question=question,
        answer=answer,
        sql_queries=all_sql,
        final_sql=last_exec.sql if last_exec else None,
        columns=last_exec.columns if last_exec else [],
        rows=last_exec.rows if last_exec else [],
        row_count=last_exec.row_count if last_exec else 0,
        truncated=last_exec.truncated if last_exec else False,
        success=False,
        error=last_error,
        attempts=max_attempts,
        steps=all_steps,
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
