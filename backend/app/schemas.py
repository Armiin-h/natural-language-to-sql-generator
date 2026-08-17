"""Pydantic request/response models for the API."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    ollama_model: str
    database: str
    sql_row_limit: int
    sql_timeout_seconds: float
    agent_recursion_limit: int = 25
    sql_max_attempts: int = 2
    tables_ready: bool = False
    ollama_reachable: bool = False
    table_counts: dict[str, int] = Field(default_factory=dict)


class ColumnSchema(BaseModel):
    name: str
    type: str
    nullable: bool
    primary_key: bool
    default: str | None = None


class ForeignKeySchema(BaseModel):
    constrained_columns: list[str]
    referred_table: str
    referred_columns: list[str]


class TableSchema(BaseModel):
    name: str
    columns: list[ColumnSchema]
    foreign_keys: list[ForeignKeySchema]
    sample_rows: list[dict[str, Any]]


class SchemaResponse(BaseModel):
    database: str
    dialect: str = "sqlite"
    tables: list[TableSchema]
    prompt_text: str


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    include_steps: bool = False

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("question must not be empty")
        return cleaned


class QueryStep(BaseModel):
    kind: str
    name: str | None = None
    content: str = ""
    tool_input: dict[str, Any] = Field(default_factory=dict)
    attempt: int | None = None


class QueryResponse(BaseModel):
    question: str
    answer: str
    success: bool
    final_sql: str | None = None
    sql_queries: list[str] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    error: str | None = None
    attempts: int = 1
    model: str
    database: str
    steps: list[QueryStep] = Field(default_factory=list)
