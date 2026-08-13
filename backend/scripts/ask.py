"""Ask a natural-language question against the sample database via the SQL agent.

Usage (from backend/):
  python -m scripts.ask "Show the top 5 products by sales"
  python -m scripts.ask --json "How many customers are in USA?"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.agent.sql_agent import ask_database, ollama_reachable
from app.config import get_settings
from app.db.seed import ensure_database


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ask AskSQL a natural-language database question.")
    parser.add_argument("question", nargs="+", help="Question in English")
    parser.add_argument("--json", action="store_true", help="Print full result as JSON")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print tool-call steps as the agent runs",
    )
    args = parser.parse_args(argv)

    question = " ".join(args.question).strip()
    settings = get_settings()
    ensure_database(settings.sqlite_path, reset=False)

    if not ollama_reachable(settings):
        print(
            f"Ollama is not reachable at {settings.ollama_base_url}. "
            f"Start Ollama and pull `{settings.ollama_model}` first.",
            file=sys.stderr,
        )
        return 2

    result = ask_database(question, settings=settings)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return 0

    print(f"Question: {result.question}")
    print(f"Model:    {result.model}")
    print(f"Database: {result.database}")
    if result.sql_queries:
        print("SQL:")
        for sql in result.sql_queries:
            print(f"  {sql}")
    else:
        print("SQL: (none captured)")
    print("Answer:")
    print(result.answer or "(empty)")

    if args.verbose:
        print("\nSteps:")
        for index, step in enumerate(result.steps, start=1):
            label = step.get("name") or step.get("kind")
            content = (step.get("content") or "")[:240]
            print(f"  {index}. [{step.get('kind')}] {label}: {content}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
