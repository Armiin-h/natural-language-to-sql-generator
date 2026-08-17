"""Natural language to SQL API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine

from app.agent.sql_agent import ollama_reachable
from app.config import get_settings
from app.db.engine import create_db_engine
from app.db.introspect import schema_as_dicts, schema_prompt_text
from app.db.seed import ensure_database, table_row_counts
from app.routers import query as query_router
from app.schemas import HealthResponse, SchemaResponse, TableSchema

_engine: Engine | None = None
APP_VERSION = "1.0.0"


def get_engine() -> Engine:
    """Return the process-wide SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _engine
    settings = get_settings()
    ensure_database(settings.sqlite_path, reset=False)
    _engine = create_db_engine(settings)
    yield
    if _engine is not None:
        _engine.dispose()
        _engine = None


app = FastAPI(
    title="Natural Language to SQL Generator",
    description=(
        "Ask questions in English; a local SQL agent generates and runs "
        "read-only queries against a sample SQLite database."
    ),
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router.router)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness check for local runs and Docker Compose."""
    settings = get_settings()
    engine = get_engine()
    counts = table_row_counts(engine)
    ready = sum(counts.values()) > 0
    return HealthResponse(
        status="ok",
        service="nl-to-sql-api",
        version=APP_VERSION,
        ollama_model=settings.ollama_model,
        database=settings.sqlite_path.name,
        sql_row_limit=settings.sql_row_limit,
        sql_timeout_seconds=settings.sql_timeout_seconds,
        agent_recursion_limit=settings.agent_recursion_limit,
        sql_max_attempts=settings.sql_max_attempts,
        tables_ready=ready,
        ollama_reachable=ollama_reachable(settings),
        table_counts=counts,
    )


@app.get("/schema", response_model=SchemaResponse)
def get_schema(
    sample_rows: int = Query(default=2, ge=0, le=10),
) -> SchemaResponse:
    """Return reflected table metadata for UI and agent prompting."""
    settings = get_settings()
    engine = get_engine()
    tables = [TableSchema.model_validate(item) for item in schema_as_dicts(engine, sample_rows=sample_rows)]
    return SchemaResponse(
        database=settings.sqlite_path.name,
        dialect="sqlite",
        tables=tables,
        prompt_text=schema_prompt_text(engine, sample_rows=sample_rows),
    )


@app.get("/examples")
def list_examples() -> dict[str, list[str]]:
    """Example questions for the UI and demos."""
    return {
        "examples": [
            "Show the top 5 products by sales",
            "How many customers live in the USA?",
            "List products in the Electronics category",
            "What is the average order value for completed orders?",
            "Which customers ordered Running Shoes?",
            "How many orders were cancelled?",
        ]
    }
