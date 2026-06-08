#!/usr/bin/env python3
"""Validate and optionally ingest filled equal-information market bars.

No network and no model calls.

The companion export-packet tool emits the missing Polymarket post-cutoff rows.
This tool is the deterministic return path: validate a filled result JSONL and,
when requested, materialize eligible rows into the forecast DB using the
existing external_baseline_observations surface with equal_information_flag=1.
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
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_PACKET = (
    WORKSPACE
    / "equal_information_baseline_export_packet_2026_06_05"
    / "equal_information_baseline_export_packet.json"
)
DEFAULT_RESULTS = (
    WORKSPACE
    / "equal_information_baseline_export_packet_2026_06_05"
    / "equal_information_baseline_export_results.jsonl"
)
DEFAULT_OUT = WORKSPACE / "equal_information_baseline_result_ingest_2026_06_05"

PILOT_ID = "equal_information_polymarket_baseline_v1"
CONDITION = "polymarket_preoutcome_equal_information_market_probability"
PRIMITIVE = "equal_information_market_baseline"
BASELINE_KIND = "pre_outcome_market_probability"


def repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing packet: {path}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return obj


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            rows.append({"_line": lineno, "_parse_error": str(exc)})
            continue
        if not isinstance(obj, dict):
            rows.append({"_line": lineno, "_parse_error": "row is not a JSON object"})
            continue
        obj.setdefault("_line", lineno)
        rows.append(obj)
    return rows


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


def parse_timestamp(value: Any) -> datetime | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        try:
            return datetime.fromtimestamp(float(text), tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    if len(text) == 10:
        text = f"{text}T00:00:00+00:00"
    elif text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def target_datetime(date_text: Any) -> datetime | None:
    if not date_text:
        return None
    return parse_timestamp(str(date_text)[:10])


def brier(p: float | None, y: int | None) -> float | None:
    if p is None or y not in (0, 1):
        return None
    return (p - int(y)) ** 2


def request_index(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = packet.get("rows", [])
    if not isinstance(rows, list):
        raise SystemExit("packet rows must be a list")
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and row.get("contract_id"):
            out[str(row["contract_id"])] = row
    return out


def validate_result(row: dict[str, Any], request: dict[str, Any] | None) -> dict[str, Any]:
    cid = str(row.get("contract_id") or "")
    errors: list[str] = []
    warnings: list[str] = []
    if row.get("_parse_error"):
        errors.append(f"parse_error:{row['_parse_error']}")
    if not cid:
        errors.append("missing_contract_id")
    if request is None:
        errors.append("contract_not_in_request_packet")

    p = probability(row.get("yes_price_at_or_before_freeze"))
    if p is None:
        errors.append("invalid_yes_price")

    observed_at = parse_timestamp(row.get("history_timestamp"))
    if observed_at is None:
        errors.append("invalid_history_timestamp")

    target_at = target_datetime(request.get("target_freeze_date_utc") if request else None)
    if observed_at is not None and target_at is not None and observed_at > target_at:
        errors.append("history_timestamp_after_target_freeze")

    if not row.get("market_asset_id_yes"):
        errors.append("missing_market_asset_id_yes")
    if not row.get("history_source"):
        errors.append("missing_history_source")
    outcomes = row.get("outcomes")
    if not isinstance(outcomes, list) or not outcomes:
        errors.append("missing_outcomes")
    elif not any(str(item).strip().lower() == "yes" for item in outcomes):
        warnings.append("outcomes_do_not_literal_yes")

    return {
        "contract_id": cid or None,
        "schema_ok": 0 if errors else 1,
        "errors": errors,
        "warnings": warnings,
        "p_success": p,
        "observed_at": observed_at.isoformat() if observed_at else None,
        "target_freeze_at": target_at.isoformat() if target_at else None,
        "request": request,
        "result": row,
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


def ensure_pilot_run(con: sqlite3.Connection, result_path: Path) -> None:
    if con.execute("SELECT 1 FROM pilot_runs WHERE pilot_id = ?", (PILOT_ID,)).fetchone():
        return
    con.execute(
        """
        INSERT INTO pilot_runs
            (pilot_id, pilot_name, primitive, corpus, source_jsonl_path, fired_at, n_calls, n_schema_ok)
        VALUES (?, ?, ?, ?, ?, ?, 0, 0)
        """,
        (
            PILOT_ID,
            "GP-245 equal-information Polymarket market baseline",
            PRIMITIVE,
            "law3_cutoff_polymarket_post_cutoff_export_results",
            repo_rel(result_path),
            datetime.now(timezone.utc).isoformat(),
            0,
            0,
        ),
    )


def refresh_pilot_counts(con: sqlite3.Connection) -> None:
    row = con.execute(
        """
        SELECT COUNT(*) AS n_calls, SUM(CASE WHEN schema_ok THEN 1 ELSE 0 END) AS n_schema_ok
        FROM pilot_calls
        WHERE pilot_id = ?
        """,
        (PILOT_ID,),
    ).fetchone()
    con.execute(
        "UPDATE pilot_runs SET n_calls = ?, n_schema_ok = ? WHERE pilot_id = ?",
        (int(row["n_calls"] or 0), int(row["n_schema_ok"] or 0), PILOT_ID),
    )


def ingest(db: Path, result_path: Path, validations: list[dict[str, Any]], *, replace: bool) -> dict[str, Any]:
    eligible = [row for row in validations if row["schema_ok"] == 1 and row.get("contract_id")]
    y_by_contract = load_contract_outcomes(db, {str(row["contract_id"]) for row in eligible})
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    ensure_baseline_table(con)
    ensure_pilot_run(con, result_path)
    if replace:
        con.execute("DELETE FROM pilot_calls WHERE pilot_id = ?", (PILOT_ID,))
        con.execute("DELETE FROM external_baseline_observations WHERE pilot_id = ?", (PILOT_ID,))
    existing_calls = {
        str(row["contract_id"])
        for row in con.execute("SELECT contract_id FROM pilot_calls WHERE pilot_id = ?", (PILOT_ID,))
    }
    existing_baselines = {
        str(row["baseline_id"])
        for row in con.execute(
            "SELECT baseline_id FROM external_baseline_observations WHERE pilot_id = ?",
            (PILOT_ID,),
        )
    }
    generated_at = datetime.now(timezone.utc).isoformat()
    inserted_calls = 0
    inserted_baselines = 0
    skipped_existing = 0
    for row in eligible:
        cid = str(row["contract_id"])
        y = y_by_contract.get(cid)
        p = float(row["p_success"])
        observed_at = row["observed_at"]
        request = row["request"] or {}
        result = row["result"] or {}
        parsed = {
            "baseline_kind": BASELINE_KIND,
            "equal_information_human_or_market_baseline": True,
            "cutoff_relation": request.get("cutoff_relation"),
            "base_rate_provenance": result.get("history_source"),
            "prior_timestamp": observed_at,
            "target_freeze_date_utc": request.get("target_freeze_date_utc"),
            "selection_method": "nearest_yes_price_at_or_before_target_freeze",
            "source_question_id": request.get("market_slug"),
            "source_url": request.get("market_url"),
            "market_asset_id_yes": result.get("market_asset_id_yes"),
            "market_asset_id_no": result.get("market_asset_id_no"),
            "outcomes": result.get("outcomes"),
        }
        raw_payload = {"request": request, "result": result, "validation": row}
        if cid in existing_calls:
            skipped_existing += 1
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
                    PILOT_ID,
                    cid,
                    "polymarket_market",
                    "polymarket_market",
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
        baseline_id = f"{PILOT_ID}:{cid}:preoutcome_market"
        if baseline_id not in existing_baselines:
            receipt = {
                "cutoff_relation": request.get("cutoff_relation"),
                "source": request.get("source"),
                "baseline_scope": "equal_information_polymarket_preoutcome_market_probability",
                "target_freeze_date_utc": request.get("target_freeze_date_utc"),
                "observed_at": observed_at,
                "history_source": result.get("history_source"),
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
                    PILOT_ID,
                    cid,
                    BASELINE_KIND,
                    "polymarket",
                    p,
                    observed_at,
                    None,
                    1,
                    json.dumps(receipt, sort_keys=True),
                    request.get("market_url"),
                    brier(p, y),
                    1 if y in (0, 1) else 0,
                    generated_at,
                    json.dumps(raw_payload, sort_keys=True),
                ),
            )
            inserted_baselines += 1
            existing_baselines.add(baseline_id)
    refresh_pilot_counts(con)
    con.commit()
    counts = con.execute(
        """
        SELECT
          COUNT(*) AS rows,
          SUM(CASE WHEN schema_ok = 1 THEN 1 ELSE 0 END) AS schema_ok,
          SUM(CASE WHEN equal_information_flag = 1 THEN 1 ELSE 0 END) AS equal_information
        FROM external_baseline_observations
        WHERE pilot_id = ?
        """,
        (PILOT_ID,),
    ).fetchone()
    con.close()
    return {
        "pilot_id": PILOT_ID,
        "inserted_pilot_calls": inserted_calls,
        "inserted_external_baselines": inserted_baselines,
        "skipped_existing_calls": skipped_existing,
        "db_external_rows": int(counts["rows"] or 0),
        "db_external_schema_ok": int(counts["schema_ok"] or 0),
        "db_external_equal_information": int(counts["equal_information"] or 0),
        "replace": replace,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    packet = load_json(args.packet)
    requests = request_index(packet)
    result_rows = load_jsonl(args.results)
    seen = Counter(str(row.get("contract_id") or "") for row in result_rows if not row.get("_parse_error"))
    validations = [validate_result(row, requests.get(str(row.get("contract_id") or ""))) for row in result_rows]
    duplicate_ids = sorted(cid for cid, count in seen.items() if cid and count > 1)
    missing_ids = sorted(set(requests) - {str(row.get("contract_id")) for row in validations if row.get("contract_id")})
    if duplicate_ids:
        for row in validations:
            if row.get("contract_id") in duplicate_ids:
                row["schema_ok"] = 0
                row["errors"].append("duplicate_contract_id")
    error_counts = Counter(error for row in validations for error in row["errors"])
    warning_counts = Counter(warn for row in validations for warn in row["warnings"])
    summary = {
        "requested_rows": len(requests),
        "result_rows": len(result_rows),
        "valid_rows": sum(1 for row in validations if row["schema_ok"] == 1),
        "invalid_rows": sum(1 for row in validations if row["schema_ok"] != 1),
        "missing_requested_rows": len(missing_ids),
        "duplicate_contract_ids": len(duplicate_ids),
        "error_counts": dict(sorted(error_counts.items())),
        "warning_counts": dict(sorted(warning_counts.items())),
        "results_path_exists": args.results.exists(),
        "acceptance_gate": "valid_rows == requested_rows and missing_requested_rows == 0",
    }
    report: dict[str, Any] = {
        "schema": "gp245-equal-information-baseline-result-ingest-report-v1",
        "packet": repo_rel(args.packet),
        "results": repo_rel(args.results),
        "pilot_id": PILOT_ID,
        "condition": CONDITION,
        "summary": summary,
        "missing_contract_ids": missing_ids,
        "duplicate_contract_ids": duplicate_ids,
        "validations": validations,
    }
    if args.ingest_db:
        report["db_ingest"] = ingest(args.db, args.results, validations, replace=args.replace)
    return report


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "equal_information_baseline_result_ingest.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = report["summary"]
    lines = [
        "# Equal-Information Baseline Result Ingest",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Packet: `{report['packet']}`",
        f"- Results: `{report['results']}`",
        f"- Requested rows: `{summary['requested_rows']}`",
        f"- Result rows: `{summary['result_rows']}`",
        f"- Valid rows: `{summary['valid_rows']}`",
        f"- Missing requested rows: `{summary['missing_requested_rows']}`",
        f"- Acceptance gate: `{summary['acceptance_gate']}`",
    ]
    if summary["error_counts"]:
        lines.extend(["", "## Error Counts", ""])
        lines.extend(f"- `{key}`: `{value}`" for key, value in summary["error_counts"].items())
    if report.get("db_ingest"):
        lines.extend(["", "## DB Ingest", ""])
        lines.extend(f"- `{key}`: `{value}`" for key, value in report["db_ingest"].items())
    (out_dir / "equal_information_baseline_result_ingest.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
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
