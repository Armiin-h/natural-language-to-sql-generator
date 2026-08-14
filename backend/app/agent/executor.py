"""Safe read-only SQL execution with timeout and JSON-friendly rows."""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterator

from sqlalchemy import event, text
from sqlalchemy.engine import Engine

from app.agent.safety import SafetyResult, validate_sql


@dataclass
class ExecutionResult:
    ok: bool
    sql: str
    columns: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)
    row_count: int = 0
    error: str | None = None
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


@contextmanager
def _connection_timeout(conn: Any, timeout_seconds: float) -> Iterator[None]:
    """Install a SQLite progress handler that aborts after timeout_seconds."""
    dbapi = getattr(conn.connection, "dbapi_connection", None) or getattr(
        conn.connection, "driver_connection", None
    )
    if dbapi is None:
        yield
        return

    started = time.monotonic()
    deadline = started + max(0.1, timeout_seconds)

    def _progress() -> int:
        return 1 if time.monotonic() > deadline else 0

    had_handler = hasattr(dbapi, "set_progress_handler")
    if had_handler:
        dbapi.set_progress_handler(_progress, 1000)
    try:
        try:
            conn.exec_driver_sql(f"PRAGMA busy_timeout={max(1, int(timeout_seconds * 1000))}")
        except Exception:
            pass
        yield
    finally:
        if had_handler:
            dbapi.set_progress_handler(None, 0)


def execute_readonly(
    engine: Engine,
    sql: str,
    *,
    row_limit: int = 100,
    timeout_seconds: float = 10.0,
) -> ExecutionResult:
    """Validate then execute a read-only query; return tabular rows."""
    safety: SafetyResult = validate_sql(sql, row_limit=row_limit)
    if not safety.ok:
        return ExecutionResult(ok=False, sql=safety.sql, error=safety.message)

    safe_sql = safety.sql
    try:
        with engine.connect() as conn:
            with _connection_timeout(conn, timeout_seconds):
                result = conn.execute(text(safe_sql))
                columns = list(result.keys())
                raw_rows = result.fetchmany(row_limit + 1)
    except Exception as exc:  # noqa: BLE001 - surface DB errors to the agent/UI
        return ExecutionResult(ok=False, sql=safe_sql, error=str(exc))

    truncated = len(raw_rows) > row_limit
    clipped = raw_rows[:row_limit]
    rows = [[_json_safe(cell) for cell in row] for row in clipped]
    return ExecutionResult(
        ok=True,
        sql=safe_sql,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        truncated=truncated,
    )
