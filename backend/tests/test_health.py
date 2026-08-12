"""Health endpoint smoke tests."""

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_health_returns_ok(tmp_path, monkeypatch):
    db_path = tmp_path / "health.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()

    from app import main as main_module

    main_module._engine = None

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["service"] == "nl-to-sql-api"
        assert "ollama_model" in payload
        assert "database" in payload
        assert payload["tables_ready"] is True

    get_settings.cache_clear()
    main_module._engine = None
