"""Tests for sample database seeding and schema introspection."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text

from app.config import get_settings
from app.db.engine import sqlite_url_for_path
from app.db.introspect import introspect_schema, schema_prompt_text
from app.db.seed import init_database, smoke_top_products_by_sales


@pytest.fixture()
def seeded_engine(tmp_path: Path):
    db_path = tmp_path / "test_ecommerce.db"
    engine = create_engine(
        sqlite_url_for_path(db_path),
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    counts = init_database(engine, reset=True)
    assert counts["products"] == 10
    assert counts["orders"] == 10
    yield engine
    engine.dispose()


def test_seed_creates_expected_tables(seeded_engine):
    tables = {table.name for table in introspect_schema(seeded_engine, sample_rows=0)}
    assert tables == {"categories", "products", "customers", "orders", "order_items"}


def test_top_products_by_sales(seeded_engine):
    top = smoke_top_products_by_sales(seeded_engine, limit=3)
    assert len(top) == 3
    assert top[0][1] >= top[1][1] >= top[2][1]
    names = [name for name, _ in top]
    assert "4K Monitor" in names or "Wireless Headphones" in names


def test_foreign_keys_enforced(seeded_engine):
    with seeded_engine.begin() as conn:
        with pytest.raises(Exception):
            conn.execute(
                text(
                    "INSERT INTO order_items (order_id, product_id, quantity, unit_price) "
                    "VALUES (9999, 1, 1, 10.0)"
                )
            )


def test_schema_prompt_mentions_tables(seeded_engine):
    prompt = schema_prompt_text(seeded_engine, sample_rows=1)
    assert "Table products" in prompt
    assert "Table orders" in prompt
    assert "FK" in prompt


def test_schema_and_health_endpoints(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "api_ecommerce.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()

    from app import main as main_module

    main_module._engine = None

    with TestClient(main_module.app) as client:
        schema = client.get("/schema?sample_rows=1")
        assert schema.status_code == 200
        payload = schema.json()
        assert payload["dialect"] == "sqlite"
        assert len(payload["tables"]) == 5
        assert "products" in payload["prompt_text"]

        health = client.get("/health")
        assert health.status_code == 200
        body = health.json()
        assert body["tables_ready"] is True
        assert body["table_counts"]["products"] == 10
        assert body["version"] == "0.3.0"
        assert "ollama_reachable" in body

    get_settings.cache_clear()
    main_module._engine = None
