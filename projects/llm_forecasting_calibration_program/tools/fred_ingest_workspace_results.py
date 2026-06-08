#!/usr/bin/env python3
"""Ingest FRED workspace artifacts into the canonical calibration DB.

This tool is intentionally narrow: it ingests the 2026-06-04 FRED official
time-series contract rows and the two Gemini/DeepSeek call ledgers produced
from them. It is idempotent and supports dry-run before commit.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_POST_CONTRACTS = WORKSPACE / "fred_forecastbench_manifest_2026_06_04/fred_forecastbench_contract_rows.jsonl"
DEFAULT_PRE_CONTRACTS = (
    WORKSPACE / "fred_pre_cutoff_companion_2026_06_04/fred_pre_cutoff_companion_contract_rows.jsonl"
)
DEFAULT_PAIR_CALLS = WORKSPACE / "fred_cutoff_pair_packet_2026_06_04/fred_cutoff_pair_calls.jsonl"
DEFAULT_CONTROL_CALLS = (
    WORKSPACE / "fred_blinded_value_control_packet_2026_06_04/fred_blinded_value_control_calls.jsonl"
)


CONTRACT_CORPORA = {
    "post": "fred_forecastbench_manifest_2026_06_04",
    "pre": "fred_pre_cutoff_companion_2026_06_04",
}
PILOT_META = {
    "fred_cutoff_pair_tool_free_v1": {
        "pilot_name": "FRED cutoff pair tool-free Gemini/DeepSeek panel",
        "primitive": "cutoff_validity_fred_pair",
        "corpus": "fred_official_timeseries_pre_post_pair",
    },
    "fred_blinded_value_control_v1": {
        "pilot_name": "FRED blinded outcome-balanced value control",
        "primitive": "cutoff_validity_fred_blinded_value_control",
        "corpus": "fred_official_timeseries_blinded_value_control",
    },
}


def repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"missing input: {path}")
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise SystemExit(f"{path}:{line_no}: expected JSON object")
        rows.append(row)
    return rows


def numeric_probability(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        p = float(value)
    except (TypeError, ValueError):
        return None
    if 0.0 <= p <= 1.0:
        return p
    return None


def brier(p: float | None, y: int | None) -> float | None:
    if p is None or y not in (0, 1):
        return None
    return (float(p) - int(y)) ** 2


def contract_payload(row: dict[str, Any], *, source_corpus: str) -> tuple[Any, ...]:
    raw = {
        **row,
        "source_corpus": source_corpus,
        "db_ingest_note": "inserted from FRED workspace artifact by fred_ingest_workspace_results.py",
    }
    return (
        row["contract_id"],
        row["question"],
        row.get("source") or "fred",
        source_corpus,
        row.get("horizon") or f"forecast_due={row.get('forecast_due_date')};resolution={row.get('resolution_date')}",
        int(row["y_known"]) if row.get("y_known") in (0, 1) else None,
        1 if bool(row.get("post_training_cutoff")) else 0,
        row.get("task_type"),
        row.get("external_market_open"),
        row.get("resolution_source_url"),
        row.get("y_known_provenance"),
        json.dumps(raw, sort_keys=True),
        datetime.now(timezone.utc).isoformat(),
    )


def ingest_contract_rows(
    con: sqlite3.Connection,
    rows: list[dict[str, Any]],
    *,
    source_corpus: str,
    dry_run: bool,
) -> dict[str, int]:
    inserted = 0
    skipped_existing = 0
    insert_sql = """
        INSERT INTO contracts
          (contract_id, question, source, source_corpus, horizon, y_known,
           post_training_cutoff, task_type, external_market_open,
           resolution_source_url, y_known_provenance, raw_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    for row in rows:
        if con.execute("SELECT 1 FROM contracts WHERE contract_id = ?", (row["contract_id"],)).fetchone():
            skipped_existing += 1
            continue
        if not dry_run:
            con.execute(insert_sql, contract_payload(row, source_corpus=source_corpus))
        inserted += 1
    return {"inserted": inserted, "skipped_existing": skipped_existing}


def ensure_pilot_run(
    con: sqlite3.Connection,
    *,
    pilot_id: str,
    calls_path: Path,
    dry_run: bool,
) -> None:
    if con.execute("SELECT 1 FROM pilot_runs WHERE pilot_id = ?", (pilot_id,)).fetchone():
        return
    meta = PILOT_META.get(
        pilot_id,
        {
            "pilot_name": f"FRED workspace pilot {pilot_id}",
            "primitive": "fred_workspace_ingest",
            "corpus": "fred_workspace_artifacts",
        },
    )
    if dry_run:
        return
    con.execute(
        """
        INSERT INTO pilot_runs
            (pilot_id, pilot_name, primitive, corpus, source_jsonl_path,
             fired_at, n_calls, n_schema_ok)
        VALUES (?, ?, ?, ?, ?, ?, 0, 0)
        """,
        (
            pilot_id,
            meta["pilot_name"],
            meta["primitive"],
            meta["corpus"],
            repo_relative(calls_path),
            datetime.now(timezone.utc).isoformat(),
        ),
    )


def refresh_pilot_counts(con: sqlite3.Connection, *, pilot_id: str) -> None:
    row = con.execute(
        """
        SELECT COUNT(*) AS n_calls,
               SUM(CASE WHEN schema_ok THEN 1 ELSE 0 END) AS n_schema_ok
        FROM pilot_calls
        WHERE pilot_id = ?
        """,
        (pilot_id,),
    ).fetchone()
    con.execute(
        "UPDATE pilot_runs SET n_calls = ?, n_schema_ok = ? WHERE pilot_id = ?",
        (int(row["n_calls"] or 0), int(row["n_schema_ok"] or 0), pilot_id),
    )


def ingest_calls(
    con: sqlite3.Connection,
    calls_path: Path,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    rows = load_jsonl(calls_path)
    if not rows:
        return {"rows": 0, "inserted": 0, "skipped_existing": 0, "invalid": 0, "pilot_id": None}
    pilot_ids = {str(row.get("pilot_id")) for row in rows if row.get("pilot_id")}
    if len(pilot_ids) != 1:
        raise SystemExit(f"{calls_path}: expected exactly one pilot_id, found {sorted(pilot_ids)}")
    pilot_id = next(iter(pilot_ids))
    ensure_pilot_run(con, pilot_id=pilot_id, calls_path=calls_path, dry_run=dry_run)
    y_map = {
        str(row["contract_id"]): int(row["y_known"]) if row["y_known"] in (0, 1) else None
        for row in con.execute("SELECT contract_id, y_known FROM contracts")
    }
    existing = {
        (str(row["contract_id"]), str(row["family"]), str(row["condition"]))
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
    skipped_existing = 0
    invalid = 0
    for row in rows:
        cid = str(row.get("contract_id") or "")
        family = str(row.get("family") or row.get("agent_id") or "")
        condition = str(row.get("condition") or "")
        if not (cid and family and condition):
            invalid += 1
            continue
        key = (cid, family, condition)
        if key in existing:
            skipped_existing += 1
            continue
        p = numeric_probability(row.get("p_success"))
        y = y_map.get(cid)
        parsed = row.get("parsed") if isinstance(row.get("parsed"), dict) else {}
        primitive = row.get("primitive") or PILOT_META.get(pilot_id, {}).get("primitive") or "fred_workspace_ingest"
        payload = (
            pilot_id,
            cid,
            row.get("agent_id") or family,
            family,
            condition,
            primitive,
            primitive,
            "full",
            None,
            row.get("paired_contract_id") or row.get("pair_id"),
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
    return {
        "pilot_id": pilot_id,
        "rows": len(rows),
        "inserted": inserted,
        "skipped_existing": skipped_existing,
        "invalid": invalid,
    }


def ingest(args: argparse.Namespace) -> dict[str, Any]:
    post_rows = load_jsonl(args.post_contracts)
    pre_rows = load_jsonl(args.pre_contracts)
    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    try:
        result = {
            "schema": "gp245-fred-workspace-db-ingest-v1",
            "db": repo_relative(args.db),
            "dry_run": args.dry_run,
            "contracts": {
                "post": ingest_contract_rows(
                    con,
                    post_rows,
                    source_corpus=CONTRACT_CORPORA["post"],
                    dry_run=args.dry_run,
                ),
                "pre": ingest_contract_rows(
                    con,
                    pre_rows,
                    source_corpus=CONTRACT_CORPORA["pre"],
                    dry_run=args.dry_run,
                ),
            },
            "calls": {
                "pair": ingest_calls(con, args.pair_calls, dry_run=args.dry_run),
                "control": ingest_calls(con, args.control_calls, dry_run=args.dry_run),
            },
        }
        if args.dry_run:
            con.rollback()
        else:
            con.commit()
        return result
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--post-contracts", type=Path, default=DEFAULT_POST_CONTRACTS)
    parser.add_argument("--pre-contracts", type=Path, default=DEFAULT_PRE_CONTRACTS)
    parser.add_argument("--pair-calls", type=Path, default=DEFAULT_PAIR_CALLS)
    parser.add_argument("--control-calls", type=Path, default=DEFAULT_CONTROL_CALLS)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    args.dry_run = bool(args.dry_run)
    result = ingest(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
