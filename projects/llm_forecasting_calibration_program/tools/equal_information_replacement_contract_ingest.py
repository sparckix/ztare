#!/usr/bin/env python3
"""Ingest replacement equal-information contract rows into the calibration DB.

No model calls. This only materializes frozen contract metadata emitted by
equal_information_replacement_dispatch_packet.py.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_ROWS = (
    REPO
    / "projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace/"
    / "equal_information_replacement_dispatch_packet_2026_06_15/"
    / "equal_information_replacement_contract_rows.jsonl"
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise SystemExit(f"{path}:{line_no}: expected JSON object")
        rows.append(obj)
    return rows


def as_int01(value: Any) -> int | None:
    if value in (0, 1):
        return int(value)
    if str(value) in {"0", "1"}:
        return int(str(value))
    return None


def ingest(rows_path: Path, db: Path, *, dry_run: bool) -> dict[str, Any]:
    rows = load_jsonl(rows_path)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    existing = {str(row["contract_id"]) for row in con.execute("SELECT contract_id FROM contracts")}
    inserted = 0
    skipped = 0
    invalid = 0
    now = datetime.now(timezone.utc).isoformat()
    insert_sql = """
        INSERT INTO contracts (
            contract_id, question, source, source_corpus, horizon, y_known,
            post_training_cutoff, task_type, external_market_open,
            resolution_source_url, y_known_provenance, raw_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    for row in rows:
        cid = str(row.get("contract_id") or "")
        question = str(row.get("question") or "")
        y_known = as_int01(row.get("y_known"))
        if not cid or not question or y_known is None:
            invalid += 1
            continue
        if cid in existing:
            skipped += 1
            continue
        payload = (
            cid,
            question,
            row.get("source") or "polymarket",
            row.get("source_corpus") or "equal_information_replacement_polymarket_2026_06_15",
            row.get("horizon"),
            y_known,
            as_int01(row.get("post_training_cutoff")) or 1,
            row.get("task_type") or "binary_forecast",
            row.get("external_market_open"),
            row.get("resolution_source_url"),
            row.get("y_known_provenance"),
            row.get("raw_json") or json.dumps(row, sort_keys=True),
            now,
        )
        if not dry_run:
            con.execute(insert_sql, payload)
        existing.add(cid)
        inserted += 1
    if not dry_run:
        con.commit()
    con.close()
    return {
        "schema": "gp245-equal-information-replacement-contract-ingest-v1",
        "db": str(db),
        "rows": str(rows_path),
        "dry_run": dry_run,
        "input_rows": len(rows),
        "inserted": inserted,
        "skipped_existing": skipped,
        "invalid": invalid,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path, default=DEFAULT_ROWS)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    if not (args.dry_run or args.commit):
        raise SystemExit("Specify --dry-run or --commit.")
    result = ingest(args.rows, args.db, dry_run=not args.commit)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
