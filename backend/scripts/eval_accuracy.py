"""Execution-accuracy evaluation for AskSQL.

Modes:
  --gold-only   Verify every gold SQL runs and record baseline (no LLM).
  --agent       Run the SQL agent on each question and score execution accuracy.

Usage (from backend/):
  python -m scripts.eval_accuracy --gold-only
  python -m scripts.eval_accuracy --agent --limit 5
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.agent.executor import execute_readonly
from app.agent.sql_agent import ask_database, ollama_reachable
from app.config import get_settings
from app.db.engine import create_db_engine
from app.db.seed import ensure_database

DEFAULT_CASES = _BACKEND_ROOT / "eval" / "cases.json"


@dataclass
class CaseResult:
    id: str
    question: str
    success: bool
    execution_match: bool | None
    gold_ok: bool
    predicted_sql: str | None = None
    gold_sql: str | None = None
    error: str | None = None


def _normalize_rows(columns: list[str], rows: list[list[Any]]) -> list[tuple[Any, ...]]:
    """Order-insensitive multiset of rows with rounded floats."""
    normalized: list[tuple[Any, ...]] = []
    for row in rows:
        cells: list[Any] = []
        for value in row:
            if isinstance(value, float):
                cells.append(round(value, 2))
            else:
                cells.append(value)
        normalized.append(tuple(cells))
    return sorted(normalized)


def rows_match(left: Any, right: Any) -> bool:
    return _normalize_rows(left.columns, left.rows) == _normalize_rows(right.columns, right.rows)


def load_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_gold_only(cases: list[dict[str, Any]], engine) -> list[CaseResult]:
    results: list[CaseResult] = []
    settings = get_settings()
    for case in cases:
        gold = execute_readonly(
            engine,
            case["gold_sql"],
            row_limit=settings.sql_row_limit,
            timeout_seconds=settings.sql_timeout_seconds,
        )
        results.append(
            CaseResult(
                id=case["id"],
                question=case["question"],
                success=gold.ok,
                execution_match=True if gold.ok else None,
                gold_ok=gold.ok,
                predicted_sql=None,
                gold_sql=case["gold_sql"],
                error=gold.error,
            )
        )
    return results


def evaluate_agent(cases: list[dict[str, Any]], engine) -> list[CaseResult]:
    settings = get_settings()
    results: list[CaseResult] = []
    for case in cases:
        gold = execute_readonly(
            engine,
            case["gold_sql"],
            row_limit=settings.sql_row_limit,
            timeout_seconds=settings.sql_timeout_seconds,
        )
        if not gold.ok:
            results.append(
                CaseResult(
                    id=case["id"],
                    question=case["question"],
                    success=False,
                    execution_match=False,
                    gold_ok=False,
                    gold_sql=case["gold_sql"],
                    error=f"Gold SQL failed: {gold.error}",
                )
            )
            continue

        predicted = ask_database(case["question"], settings=settings, engine=engine)
        if not predicted.success or not predicted.final_sql:
            results.append(
                CaseResult(
                    id=case["id"],
                    question=case["question"],
                    success=False,
                    execution_match=False,
                    gold_ok=True,
                    predicted_sql=predicted.final_sql,
                    gold_sql=case["gold_sql"],
                    error=predicted.error or "Agent produced no executable SQL",
                )
            )
            continue

        pred_exec = execute_readonly(
            engine,
            predicted.final_sql,
            row_limit=settings.sql_row_limit,
            timeout_seconds=settings.sql_timeout_seconds,
        )
        match = pred_exec.ok and rows_match(gold, pred_exec)
        results.append(
            CaseResult(
                id=case["id"],
                question=case["question"],
                success=pred_exec.ok,
                execution_match=match,
                gold_ok=True,
                predicted_sql=predicted.final_sql,
                gold_sql=case["gold_sql"],
                error=None if match else (pred_exec.error or "Result set mismatch"),
            )
        )
    return results


def summarize(results: list[CaseResult]) -> dict[str, Any]:
    total = len(results)
    gold_ok = sum(1 for item in results if item.gold_ok)
    matched = sum(1 for item in results if item.execution_match is True)
    scored = sum(1 for item in results if item.execution_match is not None)
    return {
        "total_cases": total,
        "gold_ok": gold_ok,
        "scored_cases": scored,
        "execution_matches": matched,
        "execution_accuracy": (matched / scored) if scored else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate AskSQL execution accuracy.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--gold-only", action="store_true", help="Validate gold SQL only")
    mode.add_argument("--agent", action="store_true", help="Score the SQL agent")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--limit", type=int, default=0, help="Optional case limit")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    settings = get_settings()
    ensure_database(settings.sqlite_path, reset=False)
    engine = create_db_engine(settings)
    cases = load_cases(args.cases)
    if args.limit > 0:
        cases = cases[: args.limit]

    if args.agent and not ollama_reachable(settings):
        print(
            f"Ollama is not reachable at {settings.ollama_base_url}.",
            file=sys.stderr,
        )
        return 2

    results = evaluate_agent(cases, engine) if args.agent else evaluate_gold_only(cases, engine)
    summary = summarize(results)
    payload = {"summary": summary, "results": [asdict(item) for item in results]}

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"cases={summary['total_cases']} gold_ok={summary['gold_ok']} "
            f"matches={summary['execution_matches']} "
            f"accuracy={summary['execution_accuracy']}"
        )
        for item in results:
            mark = "OK" if item.execution_match else ("GOLD" if item.gold_ok and item.execution_match is None else "FAIL")
            print(f"  [{mark}] {item.id}: {item.question}")
            if item.error:
                print(f"         {item.error}")

    if args.gold_only:
        return 0 if summary["gold_ok"] == summary["total_cases"] else 1
    return 0 if summary["execution_accuracy"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
