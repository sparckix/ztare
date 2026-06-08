#!/usr/bin/env python3
"""Backfill missing `contracts` rows for legacy GP-245 pilot_calls.

Older ingests allowed `pilot_calls.contract_id` to reference a task string that
had not been inserted into `contracts`. This script creates conservative
contract stubs from the first raw call row for each orphan contract. It does
not invent outcomes; `y_known` is filled only when the raw row already carries
an explicit ground-truth field.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
DB = REPO / "analytics/public/calibration/forecaster_calibration.db"


def load_raw(raw_json: str | None) -> dict[str, Any]:
    if not raw_json:
        return {}
    try:
        return json.loads(raw_json)
    except Exception:
        return {"raw_unparsed": raw_json[:500]}


def explicit_y_known(raw: dict[str, Any]) -> int | None:
    for key in ("y_known", "ground_truth_y", "success_bool", "completed_within_budget"):
        value = raw.get(key)
        if value is None:
            continue
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int) and value in (0, 1):
            return value
    return None


def question_for(contract_id: str, raw: dict[str, Any]) -> str:
    for key in ("question", "title", "prompt", "task_prompt", "task"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:1000]
    parsed = raw.get("parsed") if isinstance(raw.get("parsed"), dict) else {}
    rationale = parsed.get("rationale_short")
    if isinstance(rationale, str) and rationale.strip():
        return f"Legacy GP-245 contract {contract_id}: {rationale.strip()[:500]}"
    return f"Legacy GP-245 contract {contract_id}"


def backfill(*, dry_run: bool) -> dict[str, Any]:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT pc.contract_id,
               MIN(pc.pilot_id) AS example_pilot_id,
               MIN(pc.raw_json) AS raw_json,
               COUNT(*) AS call_rows
        FROM pilot_calls pc
        LEFT JOIN contracts c ON c.contract_id = pc.contract_id
        WHERE c.contract_id IS NULL
        GROUP BY pc.contract_id
        ORDER BY call_rows DESC, pc.contract_id
        """
    ).fetchall()
    inserted = 0
    y_filled = 0
    examples = []
    for row in rows:
        raw = load_raw(row["raw_json"])
        y = explicit_y_known(raw)
        if y is not None:
            y_filled += 1
        source_corpus = f"legacy_orphan_backfill::{row['example_pilot_id']}"
        payload = {
            "backfill_reason": "legacy_pilot_call_without_contract_row",
            "example_pilot_id": row["example_pilot_id"],
            "call_rows": row["call_rows"],
            "raw": raw,
        }
        examples.append(
            {
                "contract_id": row["contract_id"],
                "example_pilot_id": row["example_pilot_id"],
                "call_rows": row["call_rows"],
                "y_known": y,
            }
        )
        if not dry_run:
            con.execute(
                """
                INSERT INTO contracts
                  (contract_id, question, source, source_corpus, horizon, y_known,
                   post_training_cutoff, task_type, external_market_open,
                   resolution_source_url, y_known_provenance, raw_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["contract_id"],
                    question_for(row["contract_id"], raw),
                    "legacy_orphan_backfill",
                    source_corpus,
                    raw.get("horizon"),
                    y,
                    raw.get("post_training_cutoff"),
                    raw.get("task_type") or raw.get("experiment"),
                    raw.get("external_market_open"),
                    raw.get("resolution_source_url"),
                    "explicit_raw_field" if y is not None else None,
                    json.dumps(payload, sort_keys=True),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        inserted += 1
    if not dry_run:
        con.commit()
    remaining = con.execute(
        """
        SELECT COUNT(*)
        FROM pilot_calls pc
        LEFT JOIN contracts c ON c.contract_id = pc.contract_id
        WHERE c.contract_id IS NULL
        """
    ).fetchone()[0]
    con.close()
    return {
        "dry_run": dry_run,
        "contracts_to_backfill": len(rows),
        "contracts_inserted": 0 if dry_run else inserted,
        "contracts_with_explicit_y_known": y_filled,
        "remaining_orphan_calls": remaining,
        "examples": examples[:20],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(backfill(dry_run=args.dry_run), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

