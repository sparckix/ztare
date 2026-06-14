#!/usr/bin/env python3
"""Validate analytics/public/ledgers/catch/catch_ledger.jsonl.

SOX/PCAOB AS §1220 (concurring-partner) + AS §1215 (workpaper retention)
analog. Replaces narrative catch counting with structured artifact pointers.

Schema: see analytics/public/ledgers/catch/catch_ledger_schema.md.

Exit code: 0 if all rows valid, 1 if any row fails.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LEDGER_PATH = REPO_ROOT / "analytics" / "public" / "ledgers" / "catch" / "catch_ledger.jsonl"
ANTI_PATTERNS_DIR = REPO_ROOT / "org" / "anti-patterns"

REQUIRED_FIELDS = [
    "catch_id",
    "title",
    "author_agent",
    "concurring_agent",
    "workpaper_paths",
    "load_bearing",
    "category",
    "fix_artifact",
    "ratified_at",
    "status",
]

VALID_STATUSES = {"pending", "ratified", "retired"}

CATCH_ID_RE = re.compile(r"^C-\d{4}-\d{2}-\d{2}-\d{2,}$")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}([+-]\d{2}:?\d{2}|Z)$")


def load_categories() -> set[str]:
    """Read the 9 anti-pattern names from org/anti-patterns/*.md filenames."""
    cats: set[str] = set()
    for p in ANTI_PATTERNS_DIR.glob("*.md"):
        if p.name == "INDEX.md":
            continue
        cats.add(p.stem)
    return cats


def validate_row(row: dict, line_no: int, valid_categories: set[str]) -> list[str]:
    errors: list[str] = []
    rid = row.get("catch_id", f"<line {line_no}>")

    # Required fields present and non-null (workpaper_paths may be empty list? No — required non-empty)
    for field in REQUIRED_FIELDS:
        if field not in row:
            errors.append(f"{rid}: missing required field '{field}'")
            continue
        val = row[field]
        # fix_artifact may be null per schema; everything else must be non-null
        if field == "fix_artifact":
            continue
        if val is None:
            errors.append(f"{rid}: required field '{field}' is null")

    if errors:
        return errors

    # catch_id format
    if not CATCH_ID_RE.match(row["catch_id"]):
        errors.append(f"{rid}: catch_id does not match C-YYYY-MM-DD-NN")

    # Independence rule (the decision-critical assertion)
    if row["author_agent"] == row["concurring_agent"]:
        errors.append(
            f"{rid}: author_agent == concurring_agent ('{row['author_agent']}'); "
            "violates concurring-partner independence rule (AS §1220 analog)"
        )
    # pending concurring_agent allowed only when status == pending
    if row["concurring_agent"] == "pending" and row["status"] != "pending":
        errors.append(
            f"{rid}: concurring_agent='pending' requires status='pending'"
        )

    # workpaper_paths must be list, non-empty, all exist on disk
    wp = row["workpaper_paths"]
    if not isinstance(wp, list):
        errors.append(f"{rid}: workpaper_paths must be a list")
    elif len(wp) == 0:
        errors.append(f"{rid}: workpaper_paths must be non-empty")
    else:
        for path_str in wp:
            if not isinstance(path_str, str):
                errors.append(f"{rid}: workpaper_paths entry not a string: {path_str!r}")
                continue
            full = REPO_ROOT / path_str
            if not full.exists():
                errors.append(f"{rid}: workpaper_path does not exist on disk: {path_str}")

    # category in enum
    if row["category"] not in valid_categories:
        errors.append(
            f"{rid}: category '{row['category']}' not in anti-pattern enum "
            f"{sorted(valid_categories)}"
        )

    # status in enum
    if row["status"] not in VALID_STATUSES:
        errors.append(f"{rid}: status '{row['status']}' not in {sorted(VALID_STATUSES)}")

    # load_bearing must be bool
    if not isinstance(row["load_bearing"], bool):
        errors.append(f"{rid}: load_bearing must be bool, got {type(row['load_bearing']).__name__}")

    # ratified_at ISO 8601 (loose check)
    if not ISO_RE.match(str(row["ratified_at"])):
        errors.append(f"{rid}: ratified_at '{row['ratified_at']}' not ISO 8601")

    # retired requires superseded_by
    if row["status"] == "retired":
        sup = row.get("superseded_by")
        if not sup or not isinstance(sup, str):
            errors.append(f"{rid}: status='retired' requires non-empty superseded_by")

    # fix_artifact, if non-null string, must exist on disk
    fix = row["fix_artifact"]
    if fix is not None:
        if not isinstance(fix, str):
            errors.append(f"{rid}: fix_artifact must be string or null")
        else:
            if not (REPO_ROOT / fix).exists():
                errors.append(f"{rid}: fix_artifact path does not exist: {fix}")

    return errors


def main() -> int:
    if not LEDGER_PATH.exists():
        print(f"FATAL: ledger not found at {LEDGER_PATH}", file=sys.stderr)
        return 1

    valid_categories = load_categories()
    # The enum is dynamic: one per org/anti-patterns/*.md. No magic number
    # (was hardcoded 9; AP catalog grows — 13 as of 2026-05-15 incl.
    # lean_closure_laundering). Only an empty set is a real problem.
    if not valid_categories:
        print(
            "FATAL: no anti-pattern category files found under "
            f"{ANTI_PATTERNS_DIR}",
            file=sys.stderr,
        )
        return 1

    rows: list[dict] = []
    all_errors: list[str] = []
    catch_ids: dict[str, int] = {}

    with LEDGER_PATH.open() as f:
        for line_no, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as e:
                all_errors.append(f"line {line_no}: JSON parse error: {e}")
                continue
            rows.append(row)
            cid = row.get("catch_id", f"<line {line_no}>")
            if cid in catch_ids:
                all_errors.append(
                    f"{cid}: duplicate catch_id (also at line {catch_ids[cid]})"
                )
            else:
                catch_ids[cid] = line_no
            all_errors.extend(validate_row(row, line_no, valid_categories))

    # Validate superseded_by points at an existing catch_id
    for row in rows:
        sup = row.get("superseded_by")
        if sup and sup not in catch_ids:
            all_errors.append(
                f"{row.get('catch_id')}: superseded_by '{sup}' is not an existing catch_id"
            )

    total = len(rows)
    by_status = {"pending": 0, "ratified": 0, "retired": 0}
    for r in rows:
        s = r.get("status")
        if s in by_status:
            by_status[s] += 1
    load_bearing_ratified = sum(
        1 for r in rows if r.get("status") == "ratified" and r.get("load_bearing") is True
    )

    print("=== catch_ledger.jsonl validation ===")
    print(f"Path:      {LEDGER_PATH}")
    print(f"Total rows: {total}")
    print(f"  pending:  {by_status['pending']}")
    print(f"  ratified: {by_status['ratified']}")
    print(f"  retired:  {by_status['retired']}")
    print(f"Load-bearing ratified count (the honest tally): {load_bearing_ratified}")
    print(f"Categories enum: {sorted(valid_categories)}")
    print()

    if all_errors:
        print(f"FAIL — {len(all_errors)} validation error(s):")
        for e in all_errors:
            print(f"  - {e}")
        return 1

    print("OK — all rows valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
