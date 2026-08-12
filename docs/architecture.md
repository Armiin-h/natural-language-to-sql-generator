# Architecture

## Overview

AskSQL turns natural-language questions into SQL against a sample SQLite
database. The browser talks to a FastAPI service that will host a LangGraph /
LangChain SQL agent (schema tools + query execution). Results return as
structured JSON for an HTML table in the UI.

```text
┌────────────────────┐      JSON       ┌──────────────────────────┐
│  React (Vite) UI   │ ──────────────► │  FastAPI                 │
│  AskSQL            │ ◄────────────── │  /health, /schema        │
│  question + table  │                 │  /query  (later)         │
└────────────────────┘                 └────────────┬─────────────┘
                                                    │
                     ┌──────────────────────────────┼──────────────────────────────┐
                     │                              ▼                              │
                     │                    SQL Agent (Day 3+)                       │
                     │              list tables / schema / query / check           │
                     │                              │                              │
                     │              ┌───────────────┴───────────────┐              │
                     │              ▼                               ▼              │
                     │     SQLite ecommerce.db                 ChatOllama          │
                     │     categories/products/…               (local Ollama)      │
                     └─────────────────────────────────────────────────────────────┘
```

## Sample schema (Day 2)

```text
categories 1──* products 1──* order_items *──1 orders *──1 customers
```

- Seeded on API startup (`ensure_database`) and via `python -m scripts.init_db`
- `GET /schema` returns columns, FKs, sample rows, and prompt-ready text
- Introspection helpers feed the upcoming SQL agent system prompt

## Status

- Day 1: FastAPI `/health`, React shell, Compose stubs
- Day 2: ORM models, seed data, introspection, `/schema`

## Upcoming

| Day | Focus |
|-----|--------|
| 3 | SQL agent core |
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
