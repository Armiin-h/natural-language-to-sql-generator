# Architecture

## Overview

AskSQL turns natural-language questions into SQL against a sample SQLite
database. The browser talks to a FastAPI service that will host a LangGraph /
LangChain SQL agent (schema tools + query execution). Results return as
structured JSON for an HTML table in the UI.

```text
┌────────────────────┐      JSON       ┌──────────────────────────┐
│  React (Vite) UI   │ ──────────────► │  FastAPI                 │
│  AskSQL            │ ◄────────────── │  /health (Day 1)         │
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
                     │     (sample schema)                     (local Ollama)      │
                     └─────────────────────────────────────────────────────────────┘
```

## Day 1 status

- FastAPI app with `/health` and settings from `.env`
- React shell that polls API health
- Docker Compose stubs for `api` + `frontend` (Ollama on the host)

## Upcoming

| Day | Focus |
|-----|--------|
| 2 | Sample DB schema + seed |
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
