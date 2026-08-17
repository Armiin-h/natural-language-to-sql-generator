# Architecture

## Overview

AskSQL turns natural-language questions into SQL against a sample SQLite
database. A LangGraph ReAct agent uses LangChain SQL tools (list tables, schema,
query checker, safe query) backed by a local Ollama chat model. FastAPI serves
health/schema/query endpoints; React renders the SQL and result table.

```text
┌────────────────────┐      JSON       ┌──────────────────────────┐
│  React (Vite) UI   │ ──────────────► │  FastAPI                 │
│  AskSQL            │ ◄────────────── │  /health /schema /query  │
│  question + table  │                 │  /examples               │
└────────────────────┘                 └────────────┬─────────────┘
                                                    │
                     ┌──────────────────────────────┼──────────────────────────────┐
                     │                              ▼                              │
                     │              SQL Agent (create_react_agent)                 │
                     │         list / schema / checker / safe sql_db_query         │
                     │                              │                              │
                     │              ┌───────────────┴───────────────┐              │
                     │              ▼                               ▼              │
                     │     Safety + executor                   ChatOllama          │
                     │     SELECT-only, LIMIT, timeout         (local Ollama)      │
                     │              │                                              │
                     │              ▼                                              │
                     │     SQLite ecommerce.db                                     │
                     └─────────────────────────────────────────────────────────────┘
```

## Request path (`POST /query`)

1. UI posts `{ question }` to `/query`.
2. API checks Ollama reachability.
3. `ask_database` runs the ReAct agent (with optional error-driven retries).
4. `sql_db_query` validates SELECT-only SQL, caps LIMIT, applies timeout.
5. Response includes `final_sql`, `columns`, `rows`, `answer`, `success`, `error`.

## Safety

| Control | Enforcement |
|---------|-------------|
| SELECT / WITH / EXPLAIN only | `validate_sql` before execution |
| Block DML/DDL | Regex on comment-stripped SQL |
| Single statement | Reject multi-statement batches |
| Row cap | Inject/cap `LIMIT` via `sql_row_limit` |
| Timeout | SQLite progress handler + busy_timeout |
| Retries | Re-invoke agent with prior error (`sql_max_attempts`) |

## Sample schema

```text
categories 1──* products 1──* order_items *──1 orders *──1 customers
```

## Evaluation

`backend/eval/cases.json` holds labeled questions + gold SQL.
`python -m scripts.eval_accuracy --gold-only` validates gold queries.
`python -m scripts.eval_accuracy --agent` scores **execution accuracy**
(predicted and gold result sets match after normalization).

## Docker topology

- `api` container: FastAPI on `:8000`, volume `sql_data` for SQLite.
- `frontend` container: nginx serves the Vite build on `:3000` and proxies
  `/api/*` → `api:8000`.
- Ollama stays on the host; the API reaches it at `host.docker.internal:11434`.

## Status

Days 1–8 complete: scaffold, sample DB, SQL agent, safety, `/query` API,
React UI, execution-accuracy eval, docs/CI.
