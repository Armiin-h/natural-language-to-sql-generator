"""SQLAlchemy engine and session helpers for the sample SQLite database."""

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings


def sqlite_url_for_path(path: Path) -> str:
    """Build a SQLAlchemy SQLite URL from a filesystem path."""
    return f"sqlite:///{path.as_posix()}"


def create_db_engine(settings: Settings | None = None) -> Engine:
    """Create an engine pointed at the configured SQLite file."""
    settings = settings or get_settings()
    path = settings.sqlite_path
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        sqlite_url_for_path(path),
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
