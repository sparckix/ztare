#!/usr/bin/env python3
"""Validate and optionally ingest filled non-Polymarket equal-information rows.

No network and no model calls. By default this writes a validation report only.
Use --ingest-db to materialize valid rows into pilot_calls and
external_baseline_observations.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
PACKET_DIR = (
    PROGRAM
    / "cutoff_validity_v1/workspace/non_polymarket_equal_information_export_packet_2026_06_15"
)
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_FILLED_ROWS = (
    PACKET_DIR
    / "manifold_history_fill_2026_06_15/non_polymarket_equal_information_filled_rows.jsonl"
)
DEFAULT_OUT = PACKET_DIR / "manifold_history_ingest_2026_06_15"

PILOT_ID = "equal_information_manifold_history_baseline_v1"
CONDITION = "manifold_preoutcome_equal_information_market_probability"
PRIMITIVE = "equal_information_market_baseline"
BASELINE_KIND = "pre_outcome_market_probability"
PLATFORM = "manifold"


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO))
    except ValueError:
        return str(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            obj = {"_line": lineno, "schema_ok": 0, "errors": ["row_not_json_object"]}
        obj.setdefault("_line", lineno)
        rows.append(obj)
    return rows


def parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def probability(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
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
    return (p - y) ** 2


def validate_row(row: dict[str, Any]) -> dict[str, Any]:
    errors = list(row.get("errors") or [])
    cid = str(row.get("contract_id") or "")
    p = probability(row.get("history_probability"))
    y = row.get("resolved_binary_outcome")
    packet_y = row.get("packet_y_known")
    hist_dt = parse_dt(row.get("history_timestamp"))
    target_dt = parse_dt(row.get("target_freeze_datetime_utc"))
    if not cid:
        errors.append("missing_contract_id")
    if row.get("source") != "manifold":
        errors.append("source_not_manifold")
    if p is None:
        errors.append("invalid_history_probability")
    if y not in (0, 1):
        errors.append("invalid_resolved_binary_outcome")
    if packet_y not in (0, 1):
        errors.append("invalid_packet_y_known")
    if y in (0, 1) and packet_y in (0, 1) and int(y) != int(packet_y):
        errors.append("resolved_outcome_disagrees_with_packet")
    if hist_dt is None:
        errors.append("invalid_history_timestamp")
    if target_dt is None:
        errors.append("invalid_target_freeze_datetime")
    if hist_dt is not None and target_dt is not None and hist_dt > target_dt:
        errors.append("history_after_target_freeze")
    if not row.get("history_source"):
        errors.append("missing_history_source")
    if not row.get("manifold_contract_id"):
        errors.append("missing_manifold_contract_id")
    return {
        "contract_id": cid or None,
        "schema_ok": 0 if errors else 1,
        "errors": errors,
        "p_success": p,
        "observed_at": hist_dt.isoformat() if hist_dt else None,
        "target_freeze_at": target_dt.isoformat() if target_dt else None,
        "y": int(y) if y in (0, 1) else None,
        "brier": brier(p, int(y) if y in (0, 1) else None),
        "row": row,
    }


def load_contract_outcomes(db: Path, contract_ids: set[str]) -> dict[str, int | None]:
    if not contract_ids:
        return {}
    con = sqlite3.connect(db)
    placeholders = ",".join("?" for _ in contract_ids)
    rows = con.execute(
        f"SELECT contract_id, y_known FROM contracts WHERE contract_id IN ({placeholders})",
        tuple(sorted(contract_ids)),
    ).fetchall()
    con.close()
    return {str(cid): int(y) if y in (0, 1) else None for cid, y in rows}


def ensure_baseline_table(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS external_baseline_observations (
            baseline_id TEXT PRIMARY KEY,
            pilot_id TEXT NOT NULL,
            contract_id TEXT NOT NULL,
            baseline_kind TEXT NOT NULL,
            platform TEXT,
            p_success REAL NOT NULL,
            observed_at TEXT,
            days_before_resolution REAL,
            equal_information_flag INTEGER NOT NULL,
            source_currency_receipt TEXT NOT NULL,
            provenance_url TEXT,
            brier REAL,
            schema_ok INTEGER NOT NULL,
            generated_at TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            FOREIGN KEY (contract_id) REFERENCES contracts(contract_id)
        )
        """
    )
    con.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_external_baseline_contract_kind
        ON external_baseline_observations(contract_id, baseline_kind, platform)
        """
    )
    con.execute("DROP VIEW IF EXISTS v_external_market_baselines")
    con.execute(
        """
        CREATE VIEW v_external_market_baselines AS
        SELECT *
        FROM external_baseline_observations
        WHERE baseline_kind = 'pre_outcome_market_probability'
          AND schema_ok = 1
        """
    )


def ensure_pilot_run(con: sqlite3.Connection, result_path: Path, *, pilot_id: str) -> None:
    if con.execute("SELECT 1 FROM pilot_runs WHERE pilot_id = ?", (pilot_id,)).fetchone():
        return
    con.execute(
        """
        INSERT INTO pilot_runs
            (pilot_id, pilot_name, primitive, corpus, source_jsonl_path, fired_at, n_calls, n_schema_ok)
        VALUES (?, ?, ?, ?, ?, ?, 0, 0)
        """,
        (
            pilot_id,
            "GP-245 Manifold equal-information market baseline",
            PRIMITIVE,
            "non_polymarket_equal_information_manifold_history_2026_06_15",
            repo_relative(result_path),
            datetime.now(timezone.utc).isoformat(),
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
    db: Path,
    filled_rows: Path,
    validations: list[dict[str, Any]],
    *,
    pilot_id: str,
    replace: bool,
) -> dict[str, Any]:
    eligible = [row for row in validations if row["schema_ok"] == 1 and row.get("contract_id")]
    y_by_contract = load_contract_outcomes(db, {str(row["contract_id"]) for row in eligible})
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    ensure_baseline_table(con)
    ensure_pilot_run(con, filled_rows, pilot_id=pilot_id)
    if replace:
        con.execute("DELETE FROM pilot_calls WHERE pilot_id = ?", (pilot_id,))
        con.execute("DELETE FROM external_baseline_observations WHERE pilot_id = ?", (pilot_id,))
    generated_at = datetime.now(timezone.utc).isoformat()
    existing_calls = {
        str(row["contract_id"])
        for row in con.execute("SELECT contract_id FROM pilot_calls WHERE pilot_id = ?", (pilot_id,))
    }
    existing_baselines = {
        str(row["baseline_id"])
        for row in con.execute(
            "SELECT baseline_id FROM external_baseline_observations WHERE pilot_id = ?",
            (pilot_id,),
        )
    }
    inserted_calls = 0
    inserted_baselines = 0
    skipped_existing_calls = 0
    for validation in eligible:
        cid = str(validation["contract_id"])
        row = validation["row"]
        y = y_by_contract.get(cid)
        p = float(validation["p_success"])
        parsed = {
            "baseline_kind": BASELINE_KIND,
            "equal_information_human_or_market_baseline": True,
            "baseline_scope": "equal_information_manifold_preoutcome_market_probability",
            "source": "manifold",
            "manifold_contract_id": row.get("manifold_contract_id"),
            "market_slug": row.get("market_slug"),
            "source_url": row.get("market_url"),
            "history_source": row.get("history_source"),
            "probability_field": row.get("probability_field"),
            "target_freeze_datetime_utc": row.get("target_freeze_datetime_utc"),
            "observed_at": validation.get("observed_at"),
            "outcome_mapping": row.get("outcome_mapping"),
        }
        raw_payload = {"filled_row": row, "validation": validation}
        if cid in existing_calls:
            skipped_existing_calls += 1
        else:
            con.execute(
                """
                INSERT INTO pilot_calls
                    (pilot_id, contract_id, agent_id, family, condition, primitive,
                     primitive_base, phase, role, pair_id, p_success, brier,
                     schema_ok, parsed_json, fired_at, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pilot_id,
                    cid,
                    "manifold_market",
                    "manifold_market",
                    CONDITION,
                    PRIMITIVE,
                    "market_baseline",
                    "baseline",
                    "preoutcome_equal_information_market_bar",
                    cid,
                    p,
                    brier(p, y),
                    1 if y in (0, 1) else 0,
                    json.dumps(parsed, sort_keys=True),
                    generated_at,
                    json.dumps(raw_payload, sort_keys=True),
                ),
            )
            inserted_calls += 1
            existing_calls.add(cid)
        baseline_id = f"{pilot_id}:{cid}:preoutcome_market"
        if baseline_id not in existing_baselines:
            receipt = {
                "baseline_scope": "equal_information_manifold_preoutcome_market_probability",
                "source": "manifold",
                "platform": PLATFORM,
                "target_freeze_datetime_utc": row.get("target_freeze_datetime_utc"),
                "observed_at": validation.get("observed_at"),
                "history_source": row.get("history_source"),
                "manifold_contract_id": row.get("manifold_contract_id"),
                "probability_field": row.get("probability_field"),
                "outcome_mapping": row.get("outcome_mapping"),
            }
            con.execute(
                """
                INSERT INTO external_baseline_observations (
                    baseline_id, pilot_id, contract_id, baseline_kind, platform,
                    p_success, observed_at, days_before_resolution,
                    equal_information_flag, source_currency_receipt,
                    provenance_url, brier, schema_ok, generated_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    baseline_id,
                    pilot_id,
                    cid,
                    BASELINE_KIND,
                    PLATFORM,
                    p,
                    validation.get("observed_at"),
                    None,
                    1,
                    json.dumps(receipt, sort_keys=True),
                    row.get("market_url"),
                    brier(p, y),
                    1 if y in (0, 1) else 0,
                    generated_at,
                    json.dumps(raw_payload, sort_keys=True),
                ),
            )
            inserted_baselines += 1
            existing_baselines.add(baseline_id)
    refresh_pilot_counts(con, pilot_id=pilot_id)
    con.commit()
    counts = con.execute(
        """
        SELECT
          COUNT(*) AS rows,
          SUM(CASE WHEN schema_ok = 1 THEN 1 ELSE 0 END) AS schema_ok,
          SUM(CASE WHEN equal_information_flag = 1 THEN 1 ELSE 0 END) AS equal_information,
          AVG(brier) AS mean_brier
        FROM external_baseline_observations
        WHERE pilot_id = ?
        """,
        (pilot_id,),
    ).fetchone()
    con.close()
    return {
        "pilot_id": pilot_id,
        "inserted_pilot_calls": inserted_calls,
        "inserted_external_baselines": inserted_baselines,
        "skipped_existing_calls": skipped_existing_calls,
        "db_external_rows": int(counts["rows"] or 0),
        "db_external_schema_ok": int(counts["schema_ok"] or 0),
        "db_external_equal_information": int(counts["equal_information"] or 0),
        "db_external_mean_brier": counts["mean_brier"],
        "replace": replace,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    rows = load_jsonl(args.filled_rows)
    validations = [validate_row(row) for row in rows]
    seen = Counter(str(row.get("contract_id") or "") for row in validations)
    duplicate_ids = sorted(cid for cid, count in seen.items() if cid and count > 1)
    if duplicate_ids:
        for row in validations:
            if row.get("contract_id") in duplicate_ids:
                row["schema_ok"] = 0
                row["errors"].append("duplicate_contract_id")
    error_counts = Counter(error for row in validations for error in row["errors"])
    summary = {
        "filled_rows": len(rows),
        "valid_rows": sum(1 for row in validations if row["schema_ok"] == 1),
        "invalid_rows": sum(1 for row in validations if row["schema_ok"] != 1),
        "duplicate_contract_ids": len(duplicate_ids),
        "error_counts": dict(sorted(error_counts.items())),
        "acceptance_gate": "valid_rows == filled_rows and duplicate_contract_ids == 0",
    }
    report: dict[str, Any] = {
        "schema": "gp245-non-polymarket-equal-information-result-ingest-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filled_rows": repo_relative(args.filled_rows),
        "db": repo_relative(args.db),
        "pilot_id": args.pilot_id,
        "summary": summary,
        "duplicate_contract_ids": duplicate_ids,
        "validations": validations,
    }
    if args.ingest_db:
        report["db_ingest"] = ingest(
            args.db,
            args.filled_rows,
            validations,
            pilot_id=args.pilot_id,
            replace=args.replace,
        )
    return report


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "non_polymarket_equal_information_result_ingest.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = report["summary"]
    lines = [
        "# Non-Polymarket Equal-Information Result Ingest",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Filled rows: `{summary['filled_rows']}`",
        f"- Valid rows: `{summary['valid_rows']}`",
        f"- Invalid rows: `{summary['invalid_rows']}`",
        f"- Duplicate contract IDs: `{summary['duplicate_contract_ids']}`",
        f"- Error counts: `{summary['error_counts']}`",
        f"- Acceptance gate: `{summary['acceptance_gate']}`",
    ]
    if report.get("db_ingest"):
        lines.extend(["", "## DB Ingest", ""])
        lines.extend(f"- `{key}`: `{value}`" for key, value in report["db_ingest"].items())
    (out_dir / "non_polymarket_equal_information_result_ingest.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--filled-rows", type=Path, default=DEFAULT_FILLED_ROWS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--pilot-id", default=PILOT_ID)
    parser.add_argument("--ingest-db", action="store_true")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    report = build_report(args)
    write_outputs(report, args.out_dir)
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    if args.ingest_db:
        print(json.dumps(report["db_ingest"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
