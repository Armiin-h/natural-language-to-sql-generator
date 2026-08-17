# Natural Language to SQL Generator

**AskSQL** — ask database questions in plain English and get executable SQL plus live results.

Example: *"Show the top 5 products by sales"* → generated `SELECT` → results table.

[![CI](https://github.com/Armiin-h/natural-language-to-sql-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/Armiin-h/natural-language-to-sql-generator/actions/workflows/ci.yml)

## Features

- Local LLM via Ollama driving a LangGraph / LangChain SQL agent
- Schema-aware tools (list tables, inspect schema, check SQL, run query)
- Code-enforced read-only safety (SELECT-only, LIMIT caps, timeouts, retries)
- FastAPI `POST /query` + React UI (SQL panel + results table)
- Sample SQLite ecommerce schema with seed/reset scripts
- Labeled eval set scored by **execution accuracy**

## Stack

| Layer | Technology |
|-------|------------|
| LLM | Ollama (default `llama3.2`, tool-calling required) |
| Agent | LangChain / LangGraph SQL agent |
| Database | SQLite |
| Backend | FastAPI |
| Frontend | React + Vite |
| Deploy | Docker Compose |
| CI | GitHub Actions |

See [docs/architecture.md](docs/architecture.md) and [docs/demo.md](docs/demo.md).

## Prerequisites

- Python 3.11+
- Node.js 20+
- [Ollama](https://ollama.com/) with a tool-capable chat model
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
| Query | `POST /query` |

### Sample database

On API startup the sample ecommerce SQLite DB is created and seeded automatically.

```bash
cd backend
python -m scripts.init_db --reset
```

### Ask via CLI

```bash
cd backend
python -m scripts.ask "Show the top 5 products by sales"
```

### Evaluate

```bash
cd backend
python -m scripts.eval_accuracy --gold-only
python -m scripts.eval_accuracy --agent --limit 10
```

## Docker Compose

```bash
cp .env.example .env
# Ensure Ollama is running on the host
docker compose up --build
```

| Service | URL |
|---------|-----|
| UI | http://localhost:3000 |
| API | http://localhost:8000 |

## Sample database

| Table | Purpose |
|-------|---------|
| `categories` | Product categories |
| `products` | Catalog with price and stock |
| `customers` | Buyers |
| `orders` | Order headers (date, status) |
| `order_items` | Line items with quantity and unit price |

## Project layout

```text
backend/          FastAPI, SQL agent, eval cases
frontend/         React + Vite UI
docs/             Architecture + demo notes
docker-compose.yml
```

## License

MIT
