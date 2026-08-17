"""Natural-language query endpoint."""

from fastapi import APIRouter, HTTPException

from app.agent.sql_agent import ask_database, ollama_reachable
from app.config import get_settings
from app.schemas import QueryRequest, QueryResponse, QueryStep

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
def run_query(body: QueryRequest) -> QueryResponse:
    """Generate and execute read-only SQL for a natural-language question."""
    settings = get_settings()
    if not ollama_reachable(settings):
        raise HTTPException(
            status_code=503,
            detail=(
                f"Ollama is not reachable at {settings.ollama_base_url}. "
                f"Start Ollama and pull `{settings.ollama_model}`."
            ),
        )

    # Import lazily to avoid circular imports with app.main
    from app.main import get_engine

    result = ask_database(
        body.question,
        settings=settings,
        engine=get_engine(),
    )
    steps = (
        [QueryStep.model_validate(step) for step in result.steps]
        if body.include_steps
        else []
    )
    return QueryResponse(
        question=result.question,
        answer=result.answer,
        success=result.success,
        final_sql=result.final_sql,
        sql_queries=result.sql_queries,
        columns=result.columns,
        rows=result.rows,
        row_count=result.row_count,
        truncated=result.truncated,
        error=result.error,
        attempts=result.attempts,
        model=result.model,
        database=result.database,
        steps=steps,
    )
