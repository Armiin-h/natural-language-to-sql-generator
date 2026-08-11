# Natural Language to SQL Generator

**AskSQL** — ask database questions in plain English and get executable SQL plus live results.

Example: *"Show the top 5 products by sales"* → generated `SELECT` → results table.

## Features (roadmap)

- Local LLM via Ollama driving a LangGraph / LangChain SQL agent
- Schema-aware tools (list tables, inspect schema, run query, check SQL)
- Read-only safety checks before execution
- FastAPI backend + React UI (SQL panel + results table)
- Sample SQLite ecommerce schema
- Execution-accuracy evaluation set

## Stack

| Layer | Technology |
|-------|------------|
| LLM | Ollama (default `qwen2.5-coder`) |
| Agent | LangChain / LangGraph SQL agent |
| Database | SQLite |
| Backend | FastAPI |
| Frontend | React + Vite |
| Deploy | Docker Compose |

See [docs/architecture.md](docs/architecture.md) for the request path and Docker topology.

## Prerequisites

- Python 3.11+
- Node.js 20+
- [Ollama](https://ollama.com/) with a coding-capable chat model (used from Day 3)
- Docker Desktop (optional)

```bash
ollama pull qwen2.5-coder
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

## Project layout

```text
backend/          FastAPI app
frontend/         React + Vite UI
docs/             Architecture notes
docker-compose.yml
```

## Current status

Day 1 scaffold: settings, `/health`, React shell, Docker stubs. Database seeding,
SQL agent, and query UI follow in later commits.

## License

MIT
