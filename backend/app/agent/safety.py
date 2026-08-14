"""Code-enforced SQL safety checks (SELECT-only, no multi-statement abuse)."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Destructive / mutating keywords blocked even inside comments-stripped SQL.
_BLOCKED = re.compile(
    r"\b("
    r"insert|update|delete|drop|alter|truncate|create|replace|attach|detach|"
    r"pragma|vacuum|reindex|grant|revoke|merge|call|exec|execute|"
    r"into\s+outfile|load_file"
    r")\b",
    re.IGNORECASE,
)

_LIMIT = re.compile(r"\blimit\s+(\d+)\b", re.IGNORECASE)
_WITH = re.compile(r"^\s*with\b", re.IGNORECASE)
_SELECT = re.compile(r"^\s*select\b", re.IGNORECASE)
_EXPLAIN = re.compile(r"^\s*explain\b", re.IGNORECASE)


@dataclass(frozen=True)
class SafetyResult:
    ok: bool
    sql: str
    message: str = ""


def _strip_sql_comments(sql: str) -> str:
    """Remove /* */ and -- comments so keyword checks cannot be bypassed."""
    without_block = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    without_line = re.sub(r"--.*?$", " ", without_block, flags=re.MULTILINE)
    return without_line


def _split_statements(sql: str) -> list[str]:
    parts = [part.strip() for part in sql.split(";")]
    return [part for part in parts if part]


def ensure_limit(sql: str, row_limit: int) -> str:
    """Cap or inject LIMIT so result sets stay bounded."""
    cleaned = sql.strip().rstrip(";").strip()
    match = _LIMIT.search(cleaned)
    if match:
        existing = int(match.group(1))
        if existing > row_limit:
            cleaned = _LIMIT.sub(f"LIMIT {row_limit}", cleaned, count=1)
        return cleaned
    return f"{cleaned} LIMIT {row_limit}"


def validate_sql(sql: str, *, row_limit: int = 100) -> SafetyResult:
    """Validate that SQL is a single read-only SELECT/WITH/EXPLAIN statement."""
    if not sql or not sql.strip():
        return SafetyResult(ok=False, sql="", message="Empty SQL is not allowed.")

    stripped = _strip_sql_comments(sql).strip()
    statements = _split_statements(stripped)
    if len(statements) != 1:
        return SafetyResult(
            ok=False,
            sql=sql.strip(),
            message="Only a single SQL statement is allowed.",
        )

    statement = statements[0]
    if _BLOCKED.search(statement):
        return SafetyResult(
            ok=False,
            sql=statement,
            message="Blocked: only read-only SELECT queries are allowed.",
        )

    if not (_SELECT.match(statement) or _WITH.match(statement) or _EXPLAIN.match(statement)):
        return SafetyResult(
            ok=False,
            sql=statement,
            message="Blocked: query must start with SELECT, WITH, or EXPLAIN.",
        )

    # EXPLAIN should not need a forced LIMIT rewrite in the same way; still cap SELECT bodies.
    if _EXPLAIN.match(statement):
        return SafetyResult(ok=True, sql=statement)

    limited = ensure_limit(statement, row_limit)
    return SafetyResult(ok=True, sql=limited)
