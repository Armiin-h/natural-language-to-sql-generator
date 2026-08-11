"""Natural language to SQL API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

app = FastAPI(
    title="Natural Language to SQL Generator",
    description=(
        "Ask questions in English; a local SQL agent generates and runs "
        "read-only queries against a sample SQLite database."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str | int | float]:
    """Liveness check for local runs and Docker Compose."""
    settings = get_settings()
    return {
        "status": "ok",
        "service": "nl-to-sql-api",
        "version": "0.1.0",
        "ollama_model": settings.ollama_model,
        "database": settings.sqlite_path.name,
        "sql_row_limit": settings.sql_row_limit,
        "sql_timeout_seconds": settings.sql_timeout_seconds,
    }
