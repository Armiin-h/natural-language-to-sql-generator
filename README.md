# Natural Language to SQL Generator

**AskSQL** — ask database questions in plain English and get executable SQL plus live results.

Example: *"Show the top 5 products by sales"* → generated `SELECT` → results table.

## Features

- Local LLM via Ollama driving a LangGraph / LangChain SQL agent
- Schema-aware tools (list tables, inspect schema, check SQL, run query)
- **Code-enforced** read-only safety (SELECT-only, LIMIT caps, timeouts, retries)
- FastAPI backend + React UI (SQL panel + results table — query UI next)
- Sample SQLite ecommerce schema
- Execution-accuracy evaluation set (upcoming)
## Stack

| Layer | Technology |
|-------|------------|
| LLM | Ollama (default `llama3.2`, tool-calling required) |
| Agent | LangChain / LangGraph SQL agent |
| Database | SQLite |
| Backend | FastAPI |
| Frontend | React + Vite |
| Deploy | Docker Compose |

See [docs/architecture.md](docs/architecture.md) for the request path and Docker topology.

## Prerequisites

- Python 3.11+
- Node.js 20+
- [Ollama](https://ollama.com/) with a coding-capable chat model
- Docker Desktop (optional)

```bash
ollama pull llama3.2
```

## Quick start (local)

```bash
cp .env.example .env

# Backend
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| OpenAPI docs | http://localhost:8000/docs |
| UI (Vite) | http://localhost:5173 |
| Health | http://localhost:8000/health |
| Schema | http://localhost:8000/schema |

### Sample database

On API startup the sample ecommerce SQLite DB is created and seeded automatically.
To rebuild it from scratch:

```bash
cd backend
python -m scripts.init_db --reset
```

### Ask via CLI (SQL agent)

With Ollama running and a **tool-capable** model pulled (default `llama3.2`):

```bash
cd backend
python -m scripts.ask "Show the top 5 products by sales"
python -m scripts.ask --verbose --json "How many customers live in USA?"
```

`/health` reports `ollama_reachable`. Prefer models that support Ollama tools;
plain text “JSON tool call” models will not drive the ReAct loop correctly.

Keep `OLLAMA_BASE_URL=http://localhost:11434` for host runs. Compose forces
`host.docker.internal` inside the API container.

## Docker Compose

```bash
cp .env.example .env
# Ensure Ollama is running on the host (needed once the agent lands)
docker compose up --build
```

| Service | URL |
|---------|-----|
| UI | http://localhost:3000 |
| API | http://localhost:8000 |

## Sample database

SQLite schema under `backend/data/ecommerce.db`:

| Table | Purpose |
|-------|---------|
| `categories` | Product categories |
| `products` | Catalog with price and stock |
| `customers` | Buyers |
| `orders` | Order headers (date, status) |
| `order_items` | Line items with quantity and unit price |

## Project layout

```text
backend/          FastAPI app, DB layer, SQL agent
frontend/         React + Vite UI
docs/             Architecture notes
docker-compose.yml
```

## Current status

Day 4: SELECT-only validation, LIMIT/timeouts, error-driven retries, and
structured SQL/rows results from `ask_database` / `scripts.ask`. Next: `/query` API.

## License

MIT
