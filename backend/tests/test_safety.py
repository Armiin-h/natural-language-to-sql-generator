"""Tests for SQL safety validation and read-only execution."""

from pathlib import Path

import pytest
from sqlalchemy import text

from app.agent.executor import execute_readonly
from app.agent.safety import ensure_limit, validate_sql
from app.config import get_settings
from app.db.engine import create_db_engine
from app.db.seed import ensure_database, init_database

@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM products",
        "DROP TABLE products",
        "UPDATE products SET name='x'",
        "INSERT INTO products (name) VALUES ('x')",
        "SELECT 1; DROP TABLE products",
        "/* SELECT 1 */ DELETE FROM products",
    ],
)
def test_validate_sql_blocks_dangerous_statements(sql: str):
    result = validate_sql(sql, row_limit=50)
    assert result.ok is False
    assert "Blocked" in result.message or "single" in result.message.lower()


def test_validate_sql_allows_select_and_injects_limit():
    result = validate_sql("SELECT name FROM products ORDER BY name", row_limit=25)
    assert result.ok is True
    assert "LIMIT 25" in result.sql.upper()


def test_ensure_limit_caps_existing_limit():
    assert "LIMIT 10" in ensure_limit("SELECT * FROM products LIMIT 999", 10).upper()


def test_execute_readonly_returns_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "safe.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()
    settings = get_settings()
    ensure_database(settings.sqlite_path, reset=True)
    engine = create_db_engine(settings)

    result = execute_readonly(
        engine,
        "SELECT name FROM products ORDER BY name",
        row_limit=5,
        timeout_seconds=5,
    )
    assert result.ok is True
    assert result.columns == ["name"]
    assert result.row_count == 5
    assert result.sql.upper().endswith("LIMIT 5")

    blocked = execute_readonly(engine, "DELETE FROM products", row_limit=5)
    assert blocked.ok is False
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
    assert int(count) == 10
    get_settings.cache_clear()


def test_blocked_delete_never_mutates(tmp_path: Path):
    from app.db.engine import sqlite_url_for_path
    from sqlalchemy import create_engine, event

    path = tmp_path / "mutate.db"
    eng = create_engine(sqlite_url_for_path(path), connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def _fk(dbapi_connection, _):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    init_database(eng, reset=True)
    before = execute_readonly(eng, "SELECT COUNT(*) AS n FROM products", row_limit=10)
    assert before.ok and before.rows[0][0] == 10
    denied = execute_readonly(eng, "DELETE FROM products", row_limit=10)
    assert denied.ok is False
    after = execute_readonly(eng, "SELECT COUNT(*) AS n FROM products", row_limit=10)
    assert after.rows[0][0] == 10
    eng.dispose()
