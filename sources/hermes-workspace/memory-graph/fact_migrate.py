#!/usr/bin/env python3
"""Hermes Fact Store migration CLI.

Safely upgrades legacy SQLite databases to the current Fact / Fact+ / Fact* /
Fact+* schema.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fact_store_api import FACT_DB, migrate_fact_store_db


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrate Hermes Fact Store SQLite databases")
    parser.add_argument("db_path", nargs="?", default=str(FACT_DB), help="Path to the SQLite database file")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args(argv)

    result = migrate_fact_store_db(Path(args.db_path))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"OK: migrated {result['db_path']}")
        if result["renamed_legacy_table"]:
            print("- renamed fact_records -> facts")
        if result["added_columns"]:
            print(f"- added columns: {', '.join(result['added_columns'])}")
        print(f"- indexes ensured: {result['index_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
