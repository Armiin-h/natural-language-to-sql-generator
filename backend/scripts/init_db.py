"""Create or reset the sample ecommerce SQLite database.

Usage (from backend/):
  python -m scripts.init_db
  python -m scripts.init_db --reset
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python -m scripts.init_db` from backend/
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.config import get_settings
from app.db.engine import create_db_engine
from app.db.seed import init_database, smoke_top_products_by_sales, table_row_counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Initialize the AskSQL sample database.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop all tables and reseeds from scratch.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print row counts as JSON.",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    engine = create_db_engine(settings)
    counts = init_database(engine, reset=args.reset)
    top = smoke_top_products_by_sales(engine, limit=5)

    payload = {
        "database": str(settings.sqlite_path),
        "reset": args.reset,
        "counts": counts,
        "top_products_by_sales": [
            {"product": name, "sales": sales} for name, sales in top
        ],
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        action = "Reset and seeded" if args.reset else "Ensured"
        print(f"{action} database at {settings.sqlite_path}")
        for table, count in table_row_counts(engine).items():
            print(f"  {table}: {count}")
        print("Top products by sales:")
        for name, sales in top:
            print(f"  {name}: {sales:.2f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
