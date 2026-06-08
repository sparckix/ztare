#!/usr/bin/env python3
"""Ingest forecast-nurture call receipts into the canonical forecast DB."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_WORKSPACE = PROGRAM / "nurture_intervention_v1/workspace"
DEFAULT_CALLS = DEFAULT_WORKSPACE / "n1_nurture_intervention_calls.jsonl"
PILOT_ID = "n1_nurture_intervention_v1"
PRIMITIVE = "n1_forecast_nurture_intervention"

REQUIRED_BY_CONDITION = {
    "baseline": {"p_success"},
    "diagnostic_only": {"p_success", "worry", "bid_ask_low", "bid_ask_high", "self_predicted_brier"},
    "reference_class_numeric": {
        "p_success_before_reference",
        "reference_class_yes_rate_used",
        "p_success",
        "revision_delta",
    },
    "contrastive_numeric_revision": {
        "p_success_initial",
        "contrast_relative_likelihood",
        "p_success",
        "revision_delta",
    },
    "probability_repair": {
        "p_success_before_repair",
        "base_rate_used",
        "p_success",
        "revision_delta",
        "repair_rationale_short",
    },
    "selection_aware_probability_repair": {
        "p_success_before_repair",
        "raw_event_base_rate",
        "market_selected_base_rate",
        "chosen_reference_class",
        "chosen_base_rate",
        "p_success",
        "revision_delta",
        "repair_rationale_short",
    },
    "guarded_selection_aware_probability_repair": {
        "baseline_anchor_p",
        "p_success_before_repair",
        "raw_event_base_rate",
        "market_selected_base_rate",
        "selection_premium",
        "guard_decision",
        "p_success",
        "revision_delta_vs_anchor",
        "repair_rationale_short",
    },
    "selective_action": {
        "p_success",
        "worry",
        "selected_action",
        "expected_utility",
        "action_rationale_short",
    },
    "free_prose_forecast": {
        "p_success",
        "rationale_short",
        "failure_modes_short",
    },
    "typed_carrier_forecast": {
        "source_facts",
        "residual_evidence_carrier",
        "nearest_confuser",
        "action_program",
        "deterministic_check",
        "p_success",
    },
    "single_turn_typed_carrier_forecast": {
        "source_facts",
        "residual_evidence_carrier",
        "nearest_confuser",
        "action_program",
        "deterministic_check",
        "p_success",
    },
    "hard_prompt_break_carrier_then_forecast": {
        "source_facts",
        "residual_evidence_carrier",
        "nearest_confuser",
        "action_program",
        "deterministic_check",
        "p_success",
        "stage2_execution_check",
        "stage1_forbade_p_success",
    },
    "two_stage_free_prose_then_forecast": {
        "rationale_short",
        "failure_modes_short",
        "p_success",
        "stage2_execution_check",
        "stage1_forbade_p_success",
    },
    "carrier_to_action_execution": {
        "source_facts",
        "residual_evidence_carrier",
        "nearest_confuser",
        "action_program",
        "deterministic_check",
        "p_success",
        "selected_action",
        "expected_utility",
        "action_rationale_short",
    },
}

ACTION_VALUES = {
    "forecast",
    "forecast_yes",
    "forecast_no",
    "yes",
    "no",
    "abstain",
    "reroute_or_judge",
    "reroute",
    "judge",
}
FORECAST_ACTION_ALIASES = {"forecast", "forecast_yes", "forecast_no", "yes", "no"}


def repo_relative(path: Path) -> str:
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


def parse_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            obj = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return obj if isinstance(obj, dict) else {}
    return {}


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


def row_parsed_payload(row: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_json_object(row.get("parsed"))
    if parsed:
        return parsed
    parsed = parse_json_object(row.get("parsed_json"))
    if parsed:
        return parsed
    return {key: row[key] for key in REQUIRED_FLAT_KEYS if key in row}


REQUIRED_FLAT_KEYS = sorted({key for keys in REQUIRED_BY_CONDITION.values() for key in keys})


def normalize_action(value: Any) -> str:
    action = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if action in {"forecasting", "make_forecast"}:
        return "forecast"
    if action in {"forecast_yes", "yes", "predict_yes", "forecast_y"}:
        return "forecast_yes"
    if action in {"forecast_no", "no", "predict_no", "forecast_n"}:
        return "forecast_no"
    if action == "reroute/judge":
        return "reroute_or_judge"
    return action


def carrier_schema_ok(condition: str, parsed: dict[str, Any], p_success: float | None) -> bool:
    required = REQUIRED_BY_CONDITION.get(condition)
    if not required:
        return False
    if p_success is None:
        return False
    if any(key not in parsed for key in required):
        return False
    if condition == "probability_repair":
        before = numeric_probability(parsed.get("p_success_before_repair"))
        base_rate = numeric_probability(parsed.get("base_rate_used"))
        if before is None or base_rate is None:
            return False
    if condition == "selection_aware_probability_repair":
        before = numeric_probability(parsed.get("p_success_before_repair"))
        raw_base = numeric_probability(parsed.get("raw_event_base_rate"))
        selected_base = numeric_probability(parsed.get("market_selected_base_rate"))
        chosen_base = numeric_probability(parsed.get("chosen_base_rate"))
        reference_class = str(parsed.get("chosen_reference_class") or "").strip()
        if before is None or raw_base is None or selected_base is None or chosen_base is None:
            return False
        if not reference_class:
            return False
    if condition == "guarded_selection_aware_probability_repair":
        anchor = numeric_probability(parsed.get("baseline_anchor_p"))
        before = numeric_probability(parsed.get("p_success_before_repair"))
        raw_base = numeric_probability(parsed.get("raw_event_base_rate"))
        selected_base = numeric_probability(parsed.get("market_selected_base_rate"))
        premium = parsed.get("selection_premium")
        try:
            premium_float = float(premium)
        except (TypeError, ValueError):
            premium_float = None
        guard_decision = str(parsed.get("guard_decision") or "").strip()
        if anchor is None or before is None or raw_base is None or selected_base is None:
            return False
        if premium_float is None or not guard_decision:
            return False
    if condition == "selective_action":
        action = normalize_action(parsed.get("selected_action"))
        if action not in ACTION_VALUES:
            return False
        parsed["selected_action_normalized"] = "forecast" if action in FORECAST_ACTION_ALIASES else action
    if condition == "free_prose_forecast":
        if not str(parsed.get("rationale_short") or "").strip():
            return False
        if not str(parsed.get("failure_modes_short") or "").strip():
            return False
    if condition in {"typed_carrier_forecast", "single_turn_typed_carrier_forecast"}:
        source_facts = parsed.get("source_facts")
        action_program = parsed.get("action_program")
        if not isinstance(source_facts, list) or not (2 <= len(source_facts) <= 5):
            return False
        if not isinstance(action_program, list) or not (2 <= len(action_program) <= 4):
            return False
        for key in ("residual_evidence_carrier", "nearest_confuser", "deterministic_check"):
            if not str(parsed.get(key) or "").strip():
                return False
    if condition == "hard_prompt_break_carrier_then_forecast":
        source_facts = parsed.get("source_facts")
        action_program = parsed.get("action_program")
        if not isinstance(source_facts, list) or not (2 <= len(source_facts) <= 5):
            return False
        if not isinstance(action_program, list) or not (2 <= len(action_program) <= 4):
            return False
        for key in ("residual_evidence_carrier", "nearest_confuser", "deterministic_check", "stage2_execution_check"):
            if not str(parsed.get(key) or "").strip():
                return False
        if parsed.get("stage1_forbade_p_success") is not True:
            return False
    if condition == "two_stage_free_prose_then_forecast":
        if not str(parsed.get("rationale_short") or "").strip():
            return False
        if not str(parsed.get("failure_modes_short") or "").strip():
            return False
        if not str(parsed.get("stage2_execution_check") or "").strip():
            return False
        if parsed.get("stage1_forbade_p_success") is not True:
            return False
    if condition == "carrier_to_action_execution":
        source_facts = parsed.get("source_facts")
        action_program = parsed.get("action_program")
        action = normalize_action(parsed.get("selected_action"))
        if not isinstance(source_facts, list) or not (2 <= len(source_facts) <= 5):
            return False
        if not isinstance(action_program, list) or not (2 <= len(action_program) <= 4):
            return False
        for key in ("residual_evidence_carrier", "nearest_confuser", "deterministic_check", "action_rationale_short"):
            if not str(parsed.get(key) or "").strip():
                return False
        if action not in ACTION_VALUES:
            return False
        parsed["selected_action_normalized"] = "forecast" if action in FORECAST_ACTION_ALIASES else action
    return True


def ensure_pilot_run(
    con: sqlite3.Connection,
    calls_path: Path,
    *,
    pilot_id: str,
    primitive: str,
    dry_run: bool,
) -> None:
    if con.execute("SELECT 1 FROM pilot_runs WHERE pilot_id = ?", (pilot_id,)).fetchone():
        return
    if dry_run:
        return
    con.execute(
        """
        INSERT INTO pilot_runs
            (pilot_id, pilot_name, primitive, corpus, source_jsonl_path, fired_at, n_calls, n_schema_ok)
        VALUES (?, ?, ?, ?, ?, datetime('now'), 0, 0)
        """,
        (
            pilot_id,
            f"GP-245 {pilot_id} forecast nurture intervention",
            primitive,
            "post_cutoff_resolved_forecast_contracts",
            repo_relative(calls_path),
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
        """
        UPDATE pilot_runs
        SET n_calls = ?, n_schema_ok = ?
        WHERE pilot_id = ?
        """,
        (int(row["n_calls"] or 0), int(row["n_schema_ok"] or 0), pilot_id),
    )


def ingest(calls_path: Path, db: Path, *, pilot_id: str, dry_run: bool) -> dict[str, Any]:
    rows = load_jsonl(calls_path)
    primitive_name = next((str(row.get("primitive")) for row in rows if row.get("primitive")), PRIMITIVE)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    ensure_pilot_run(con, calls_path, pilot_id=pilot_id, primitive=primitive_name, dry_run=dry_run)
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
    schema_fail = 0
    for row in rows:
        if row.get("pilot_id", pilot_id) != pilot_id:
            invalid += 1
            continue
        cid = row.get("contract_id")
        family = row.get("family")
        condition = row.get("condition")
        if not (cid and family and condition):
            invalid += 1
            continue
        key = (str(cid), str(family), str(condition))
        if key in existing:
            skipped += 1
            continue
        parsed = row_parsed_payload(row)
        p = numeric_probability(row.get("p_success"))
        if p is None:
            p = numeric_probability(parsed.get("p_success"))
        ok = carrier_schema_ok(str(condition), parsed, p)
        if not ok:
            schema_fail += 1
        y = y_map.get(str(cid))
        payload = (
            pilot_id,
            str(cid),
            row.get("agent_id") or str(family),
            str(family),
            str(condition),
            row.get("primitive") or PRIMITIVE,
            row.get("primitive") or PRIMITIVE,
            row.get("phase") or "intervention",
            row.get("role") or "n1_arm",
            row.get("pair_id") or f"{cid}|{family}",
            p,
            brier(p, y),
            1 if ok else 0,
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
    db_counts = con.execute(
        """
        SELECT COUNT(*) AS n_calls, SUM(CASE WHEN schema_ok THEN 1 ELSE 0 END) AS n_schema_ok
        FROM pilot_calls
        WHERE pilot_id = ?
        """,
        (pilot_id,),
    ).fetchone()
    con.close()
    return {
        "schema": "gp245-nurture-ingest-v2",
        "pilot_id": pilot_id,
        "db": str(db),
        "calls": str(calls_path),
        "calls_file_exists": calls_path.exists(),
        "dry_run": dry_run,
        "rows": len(rows),
        "inserted": inserted,
        "skipped_existing": skipped,
        "invalid": invalid,
        "schema_fail": schema_fail,
        "db_existing_calls": int(db_counts["n_calls"] or 0),
        "db_existing_schema_ok": int(db_counts["n_schema_ok"] or 0),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calls", type=Path, default=DEFAULT_CALLS)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--pilot-id", default=PILOT_ID)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    if not (args.dry_run or args.commit):
        raise SystemExit("Specify --dry-run or --commit.")
    result = ingest(args.calls, args.db, pilot_id=args.pilot_id, dry_run=not args.commit)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
