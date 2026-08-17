"""API tests for POST /query and examples."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings


def test_examples_endpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "ex.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()

    from app import main as main_module

    main_module._engine = None
    with TestClient(main_module.app) as client:
        response = client.get("/examples")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["examples"]) >= 3

    get_settings.cache_clear()
    main_module._engine = None


def test_query_endpoint_with_stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "query.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()

    from app import main as main_module
    from app.agent import sql_agent
    from app.agent.sql_agent import SqlAgentResult

    main_module._engine = None

    def _fake_reachable(_settings=None):
        return True

    def _fake_ask(question, **_kwargs):
        return SqlAgentResult(
            question=question,
            answer="There are 10 products.",
            sql_queries=["SELECT COUNT(*) AS n FROM products"],
            final_sql="SELECT COUNT(*) AS n FROM products LIMIT 100",
            columns=["n"],
            rows=[[10]],
            row_count=1,
            success=True,
            attempts=1,
            model="stub",
            database="query.db",
        )

    monkeypatch.setattr(sql_agent, "ollama_reachable", _fake_reachable)
    monkeypatch.setattr("app.routers.query.ollama_reachable", _fake_reachable)
    monkeypatch.setattr("app.routers.query.ask_database", _fake_ask)

    with TestClient(main_module.app) as client:
        missing = client.post("/query", json={"question": "   "})
        assert missing.status_code == 422

        response = client.post(
            "/query",
            json={"question": "How many products?", "include_steps": False},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["rows"] == [[10]]
        assert body["final_sql"]
        assert body["steps"] == []

    get_settings.cache_clear()
    main_module._engine = None


def test_query_requires_ollama(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "down.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()

    from app import main as main_module

    main_module._engine = None
    monkeypatch.setattr("app.routers.query.ollama_reachable", lambda _s=None: False)

    with TestClient(main_module.app) as client:
        response = client.post("/query", json={"question": "How many products?"})
        assert response.status_code == 503

    get_settings.cache_clear()
    main_module._engine = None
