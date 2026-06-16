#!/usr/bin/env python3
"""Ingest GP-245 Law 3 Stage-B call receipts into the canonical DB."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
WORKSPACE = REPO / "projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace"
DEFAULT_CALLS = WORKSPACE / "cutoff_stage_b_panel_v1_calls.jsonl"
PILOT_ID = "cutoff_stage_b_panel_v1"
DEFAULT_PILOT_NAME = "GP-245 Law 3 cutoff Stage-B constrained panel"
DEFAULT_PRIMITIVE = "cutoff_validity_stage_b"
DEFAULT_CORPUS = "law3_cutoff_matched_panel"


def repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise SystemExit(f"{path}:{line_no}: expected JSON object")
        rows.append(row)
    return rows


def numeric_probability(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        p = float(value)
        if 0.0 <= p <= 1.0:
            return p
    return None


def brier(p: float | None, y: int | None) -> float | None:
    if p is None or y is None:
        return None
    return (p - y) ** 2


def ensure_pilot_run(
    con: sqlite3.Connection,
    calls_path: Path,
    *,
    pilot_id: str,
    pilot_name: str,
    primitive: str,
    corpus: str,
    dry_run: bool,
) -> None:
    if con.execute("SELECT 1 FROM pilot_runs WHERE pilot_id = ?", (pilot_id,)).fetchone():
        return
    if dry_run:
        return
    con.execute(
        """
        INSERT INTO pilot_runs
            (pilot_id, pilot_name, primitive, corpus, source_jsonl_path, fired_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            pilot_id,
            pilot_name,
            primitive,
            corpus,
            repo_rel(calls_path),
        ),
    )


def refresh_pilot_counts(con: sqlite3.Connection, *, pilot_id: str) -> None:
    row = con.execute(
        """
        SELECT COUNT(*) AS n_calls, SUM(CASE WHEN schema_ok THEN 1 ELSE 0 END) AS n_schema_ok
        FROM pilot_calls
        WHERE pilot_id = ?
        """,
        (pilot_id,),
    ).fetchone()
    con.execute(
        "UPDATE pilot_runs SET n_calls = ?, n_schema_ok = ? WHERE pilot_id = ?",
        (int(row["n_calls"] or 0), int(row["n_schema_ok"] or 0), pilot_id),
    )


def ingest(
    calls_path: Path,
    db: Path,
    *,
    pilot_id: str,
    pilot_name: str,
    primitive: str,
    corpus: str,
    dry_run: bool,
) -> dict[str, Any]:
    rows = load_jsonl(calls_path)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    ensure_pilot_run(
        con,
        calls_path,
        pilot_id=pilot_id,
        pilot_name=pilot_name,
        primitive=primitive,
        corpus=corpus,
        dry_run=dry_run,
    )
    y_map = dict(con.execute("SELECT contract_id, y_known FROM contracts"))
    existing = {
        (row["contract_id"], row["family"], row["condition"])
        for row in con.execute(
            """
            SELECT contract_id, family, condition
            FROM pilot_calls
            WHERE pilot_id = ?
            """,
            (pilot_id,),
        )
    }
    insert_sql = """
        INSERT INTO pilot_calls
            (pilot_id, contract_id, agent_id, family, condition, primitive,
             primitive_base, phase, role, pair_id, p_success, brier,
             schema_ok, parsed_json, fired_at, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    inserted = 0
    skipped = 0
    invalid = 0
    for row in rows:
        if row.get("pilot_id") != pilot_id:
            invalid += 1
            continue
        cid = row.get("contract_id")
        family = row.get("family")
        condition = row.get("condition")
        if not (cid and family and condition):
            invalid += 1
            continue
        key = (cid, family, condition)
        if key in existing:
            skipped += 1
            continue
        p = numeric_probability(row.get("p_success"))
        y = y_map.get(cid)
        parsed = row.get("parsed") if isinstance(row.get("parsed"), dict) else {}
        payload = (
            pilot_id,
            cid,
            row.get("agent_id") or family,
            family,
            condition,
            row.get("primitive") or "cutoff_validity_stage_b",
            "cutoff_validity_stage_b",
            "full",
            None,
            None,
            p,
            brier(p, y),
            1 if row.get("schema_ok") else 0,
            json.dumps(parsed, sort_keys=True),
            row.get("fired_at"),
            json.dumps(row, sort_keys=True),
        )
        if not dry_run:
            con.execute(insert_sql, payload)
        existing.add(key)
        inserted += 1
    if not dry_run:
        refresh_pilot_counts(con, pilot_id=pilot_id)
        con.commit()
    con.close()
    return {
        "schema": "gp245-cutoff-stage-b-ingest-v1",
        "db": str(db),
        "calls": str(calls_path),
        "pilot_id": pilot_id,
        "dry_run": dry_run,
        "rows": len(rows),
        "inserted": inserted,
        "skipped_existing": skipped,
        "invalid": invalid,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calls", type=Path, default=DEFAULT_CALLS)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--pilot-id", default=PILOT_ID)
    parser.add_argument("--pilot-name", default=DEFAULT_PILOT_NAME)
    parser.add_argument("--primitive", default=DEFAULT_PRIMITIVE)
    parser.add_argument("--corpus", default=DEFAULT_CORPUS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    if not (args.dry_run or args.commit):
        raise SystemExit("Specify --dry-run or --commit.")
    result = ingest(
        args.calls,
        args.db,
        pilot_id=args.pilot_id,
        pilot_name=args.pilot_name,
        primitive=args.primitive,
        corpus=args.corpus,
        dry_run=not args.commit,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
