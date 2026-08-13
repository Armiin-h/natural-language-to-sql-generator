# Architecture

## Overview

AskSQL turns natural-language questions into SQL against a sample SQLite
database. A LangGraph ReAct agent uses LangChain SQL tools (list tables, schema,
query, checker) backed by a local Ollama chat model. The FastAPI service exposes
health/schema today; the query HTTP route lands next.

```text
┌────────────────────┐      JSON       ┌──────────────────────────┐
│  React (Vite) UI   │ ──────────────► │  FastAPI                 │
│  AskSQL            │ ◄────────────── │  /health, /schema        │
│  question + table  │                 │  /query  (Day 5)         │
└────────────────────┘                 └────────────┬─────────────┘
                                                    │
                     ┌──────────────────────────────┼──────────────────────────────┐
                     │                              ▼                              │
                     │              SQL Agent (create_react_agent)                 │
                     │         sql_db_list_tables / schema / query / checker       │
                     │                              │                              │
                     │              ┌───────────────┴───────────────┐              │
                     │              ▼                               ▼              │
                     │     SQLite ecommerce.db                 ChatOllama          │
                     │     categories/products/…               (local Ollama)      │
                     └─────────────────────────────────────────────────────────────┘
```

CLI path (Day 3): `python -m scripts.ask "…"`.

## Sample schema (Day 2)

```text
categories 1──* products 1──* order_items *──1 orders *──1 customers
```

- Seeded on API startup (`ensure_database`) and via `python -m scripts.init_db`
- `GET /schema` returns columns, FKs, sample rows, and prompt-ready text
- Agent system prompt enforces read-only SELECT behavior (code guards on Day 4)

## Status

- Day 1: FastAPI `/health`, React shell, Compose stubs
- Day 2: ORM models, seed data, introspection, `/schema`
- Day 3: Ollama + LangGraph SQL agent, `scripts/ask.py`

## Upcoming

| Day | Focus |
|-----|--------|
| 4 | Safety guards + retries |
| 5 | `/query` API |
| 6 | Full query UI |
| 7 | Execution-accuracy eval |
| 8 | Compose polish + docs |

## Docker topology

- `api` container: FastAPI on `:8000`, volume `sql_data` for SQLite.
- `frontend` container: nginx serves the Vite build on `:3000` and proxies
  `/api/*` → `api:8000`.
- Ollama stays on the host; the API reaches it at `host.docker.internal:11434`.
