# Natural Language to SQL Generator

Ask database questions in plain English and get executable SQL plus live results.

Example: *"Show the top 5 products by sales"* → generated `SELECT` → results table.

## Goals

- Turn natural-language questions into correct SQL against a real schema
- Execute queries safely (read-only) and show tabular results
- Demonstrate LLM + DBMS integration: schema context, agent tooling, and correctness checks

## Planned stack

| Layer | Technology |
|-------|------------|
| LLM | Ollama (local) |
| Agent | LangChain / LangGraph SQL agent + SQL tools |
| Database | SQLite (sample e-commerce / Chinook-style schema) |
| Backend | FastAPI |
| Frontend | React + Vite |
| Deploy | Docker Compose |

## Status

Project scaffolding in progress. Setup, agent pipeline, UI, safety checks, and evaluation will land in upcoming commits.

## Prerequisites (upcoming)

- Python 3.11+
- Node.js 20+
- [Ollama](https://ollama.com/) with a coding-capable chat model
- Docker Desktop (optional)

## License

MIT
