"""Pydantic response models for the API."""

from typing import Any

from pydantic import BaseModel, Field


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
