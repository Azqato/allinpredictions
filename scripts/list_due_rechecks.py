#!/usr/bin/env python3
"""List inconclusive prediction checks whose expected resolution date has passed.

Scans data/checks/*.json for entries with result == "inconclusive" and a
resolves_by date <= today (or a given --as-of date). These are candidates for
a recheck pass: re-run WebSearch-informed validation and either resolve them
(right/wrong/ambiguous) or roll resolves_by forward to a new expectation.

Only checks that carry a resolves_by field are considered -- as of 2026-08-31
this field is being backfilled retroactively in batches of 5 (see docs/PRD.md
roadmap) and applied going forward to all new checks, so most existing
inconclusive checks won't have one yet and are silently skipped, not treated
as overdue.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import List


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checks-dir", type=Path, default=Path("data/checks"))
    parser.add_argument(
        "--as-of",
        type=str,
        default=None,
        help="ISO date (YYYY-MM-DD) to compare against; defaults to today",
    )
    args = parser.parse_args(argv)

    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()

    due = []
    with_date = 0
    without_date = 0
    for path in sorted(args.checks_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[skip] {path.name}: failed to parse ({exc})", file=sys.stderr)
            continue
        for chk in data.get("checks", []):
            if chk.get("result") != "inconclusive":
                continue
            resolves_by = chk.get("resolves_by")
            if not resolves_by:
                without_date += 1
                continue
            with_date += 1
            try:
                due_date = date.fromisoformat(resolves_by)
            except ValueError:
                print(f"[warn] {path.name}: bad resolves_by '{resolves_by}' on {chk.get('id')}", file=sys.stderr)
                continue
            if due_date <= as_of:
                due.append(
                    {
                        "episode_id": path.stem,
                        "id": chk.get("id"),
                        "resolves_by": resolves_by,
                        "explanation": chk.get("explanation", ""),
                    }
                )

    print(f"As of {as_of.isoformat()}: {len(due)} check(s) overdue for recheck")
    print(f"({with_date} inconclusive checks carry a resolves_by date, {without_date} do not yet)")
    for row in due:
        print(f"- [{row['resolves_by']}] {row['episode_id']} :: {row['id']}")
        print(f"    {row['explanation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
