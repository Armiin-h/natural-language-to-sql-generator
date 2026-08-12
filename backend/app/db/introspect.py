"""Schema introspection helpers for prompts and API responses."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import inspect
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    type: str
    nullable: bool
    primary_key: bool
    default: str | None = None


@dataclass(frozen=True)
class ForeignKeyInfo:
    constrained_columns: list[str]
    referred_table: str
    referred_columns: list[str]


@dataclass(frozen=True)
class TableInfo:
    name: str
    columns: list[ColumnInfo]
    foreign_keys: list[ForeignKeyInfo]
    sample_rows: list[dict[str, object]]


def _format_default(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def introspect_schema(engine: Engine, *, sample_rows: int = 3) -> list[TableInfo]:
    """Reflect tables, columns, FKs, and a few sample rows for LLM context."""
    inspector = inspect(engine)
    tables: list[TableInfo] = []

    for table_name in inspector.get_table_names():
        columns = [
            ColumnInfo(
                name=column["name"],
                type=str(column["type"]),
                nullable=bool(column.get("nullable", True)),
                primary_key=bool(column.get("primary_key", False)),
                default=_format_default(column.get("default")),
            )
            for column in inspector.get_columns(table_name)
        ]
        foreign_keys = [
            ForeignKeyInfo(
                constrained_columns=list(fk["constrained_columns"]),
                referred_table=str(fk["referred_table"]),
                referred_columns=list(fk["referred_columns"]),
            )
            for fk in inspector.get_foreign_keys(table_name)
        ]

        samples: list[dict[str, object]] = []
        if sample_rows > 0:
            with engine.connect() as conn:
                result = conn.exec_driver_sql(
                    f'SELECT * FROM "{table_name}" LIMIT {int(sample_rows)}'
                )
                samples = [
                    {key: _json_safe(val) for key, val in dict(row._mapping).items()}
                    for row in result
                ]

        tables.append(
            TableInfo(
                name=table_name,
                columns=columns,
                foreign_keys=foreign_keys,
                sample_rows=samples,
            )
        )

    return tables


def schema_as_dicts(engine: Engine, *, sample_rows: int = 3) -> list[dict[str, object]]:
    """JSON-serializable schema payload."""
    return [asdict(table) for table in introspect_schema(engine, sample_rows=sample_rows)]


def schema_prompt_text(engine: Engine, *, sample_rows: int = 2) -> str:
    """Compact text schema for agent system prompts."""
    lines: list[str] = ["Database schema (SQLite ecommerce sample):", ""]
    for table in introspect_schema(engine, sample_rows=sample_rows):
        col_bits = [
            f"{col.name} {col.type}"
            + (" PK" if col.primary_key else "")
            + ("" if col.nullable else " NOT NULL")
            for col in table.columns
        ]
        lines.append(f"Table {table.name}({', '.join(col_bits)})")
        for fk in table.foreign_keys:
            lines.append(
                "  FK "
                f"{', '.join(fk.constrained_columns)} -> "
                f"{fk.referred_table}({', '.join(fk.referred_columns)})"
            )
        if table.sample_rows:
            lines.append(f"  Sample rows: {table.sample_rows}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
