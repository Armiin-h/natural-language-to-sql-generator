"""Tests for execution-accuracy helpers and gold SQL cases."""

import json
from pathlib import Path

from app.agent.executor import execute_readonly
from app.config import get_settings
from app.db.engine import create_db_engine
from app.db.seed import ensure_database
from scripts.eval_accuracy import DEFAULT_CASES, evaluate_gold_only, load_cases, rows_match, summarize


def test_eval_cases_file_exists_and_loads():
    cases = load_cases(DEFAULT_CASES)
    assert len(cases) >= 30
    assert all("question" in case and "gold_sql" in case for case in cases)


def test_gold_sql_all_execute(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "eval.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()
    settings = get_settings()
    ensure_database(settings.sqlite_path, reset=True)
    engine = create_db_engine(settings)
    cases = load_cases(DEFAULT_CASES)
    results = evaluate_gold_only(cases, engine)
    summary = summarize(results)
    assert summary["gold_ok"] == summary["total_cases"]
    get_settings.cache_clear()


def test_rows_match_is_order_insensitive(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "match.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()
    settings = get_settings()
    ensure_database(settings.sqlite_path, reset=True)
    engine = create_db_engine(settings)
    left = execute_readonly(engine, "SELECT name FROM products ORDER BY name ASC", row_limit=100)
    right = execute_readonly(engine, "SELECT name FROM products ORDER BY name DESC", row_limit=100)
    assert left.ok and right.ok
    assert rows_match(left, right)
    get_settings.cache_clear()
