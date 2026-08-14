"""SQL toolkit tools with a code-enforced safe query runner."""

from __future__ import annotations

from typing import Any

from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine

from app.agent.executor import ExecutionResult, execute_readonly
from app.config import Settings

class _QueryInput(BaseModel):
    query: str = Field(description="A detailed and correct read-only SQL query to run.")


def _format_execution(result: ExecutionResult) -> str:
    if not result.ok:
        return f"Error: {result.error}"
    header = ", ".join(result.columns) if result.columns else ""
    preview_rows = result.rows[:20]
    body = str([tuple(row) for row in preview_rows])
    note = ""
    if result.truncated:
        note = f"\n(Result truncated to {result.row_count} rows.)"
    if header:
        return f"Columns: {header}\nRows: {body}{note}"
    return f"Rows: {body}{note}"


def build_safe_sql_tools(
    *,
    toolkit: SQLDatabaseToolkit,
    engine: Engine,
    settings: Settings,
) -> list[BaseTool]:
    """Replace sql_db_query with a validated, timed, LIMIT-capped executor."""
    tools: list[BaseTool] = []
    for tool in toolkit.get_tools():
        if tool.name != "sql_db_query":
            tools.append(tool)
            continue

        def _safe_query(query: str) -> str:
            result = execute_readonly(
                engine,
                query,
                row_limit=settings.sql_row_limit,
                timeout_seconds=settings.sql_timeout_seconds,
            )
            return _format_execution(result)

        tools.append(
            StructuredTool.from_function(
                func=_safe_query,
                name="sql_db_query",
                description=(
                    "Input to this tool is a detailed and correct SQL query, output is a "
                    "result from the database. Only SELECT/WITH/EXPLAIN are accepted. "
                    "Destructive SQL is rejected before execution. If an error is returned, "
                    "rewrite the query and try again."
                ),
                args_schema=_QueryInput,
            )
        )
    return tools
