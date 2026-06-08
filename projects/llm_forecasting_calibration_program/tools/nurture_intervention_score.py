#!/usr/bin/env python3
"""Score or readiness-check a forecast-nurture intervention.

Reads the master DB and a frozen dispatch queue. If calls are not yet
ingested, emits an explicit DB gap report. If calls are present, scores paired
Brier deltas against baseline and a simple selective-action utility proxy.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.ztare.experiment_stats import paired_permutation_test


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_WORKSPACE = PROGRAM / "nurture_intervention_v1/workspace"
DEFAULT_QUEUE = DEFAULT_WORKSPACE / "n1_nurture_intervention_dispatch_queue.jsonl"
DEFAULT_OUT = DEFAULT_WORKSPACE
BASELINE = "baseline"
FORECAST_ACTION_ALIASES = {"forecast", "forecast_yes", "forecast_no", "yes", "no"}
ACTION_CONDITIONS = {"selective_action", "carrier_to_action_execution"}


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


def repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        obj = json.loads(text)
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def load_calls(db: Path, pilot_id: str) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = [
        dict(row)
        for row in con.execute(
            """
            SELECT pilot_id, contract_id, family, condition, p_success, brier,
                   schema_ok, parsed_json
            FROM pilot_calls
            WHERE pilot_id = ?
            """,
            (pilot_id,),
        )
    ]
    con.close()
    return rows


def load_y_known(db: Path, contract_ids: set[str]) -> dict[str, int | None]:
    if not contract_ids:
        return {}
    con = sqlite3.connect(db)
    placeholders = ",".join("?" for _ in contract_ids)
    rows = con.execute(
        f"SELECT contract_id, y_known FROM contracts WHERE contract_id IN ({placeholders})",
        tuple(contract_ids),
    ).fetchall()
    con.close()
    return {
        str(contract_id): int(y_known) if y_known in (0, 1) else None
        for contract_id, y_known in rows
    }


def paired_deltas(calls: list[dict[str, Any]]) -> dict[str, Any]:
    by_condition = paired_delta_values(calls)
    pair_values = paired_value_pairs(calls)
    return summarize_delta_values(by_condition, pair_values)


def paired_delta_values(calls: list[dict[str, Any]]) -> dict[str, list[float]]:
    by_key: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in calls:
        if not row.get("schema_ok") or row.get("brier") is None:
            continue
        key = (str(row["contract_id"]), str(row["family"]))
        by_key[key][str(row["condition"])] = row
    by_condition: dict[str, list[float]] = defaultdict(list)
    for arms in by_key.values():
        base = arms.get(BASELINE)
        if not base:
            continue
        for condition, row in arms.items():
            if condition == BASELINE:
                continue
            by_condition[condition].append(float(row["brier"]) - float(base["brier"]))
    return by_condition


def paired_value_pairs(calls: list[dict[str, Any]]) -> dict[str, tuple[list[float], list[float]]]:
    by_key: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in calls:
        if not row.get("schema_ok") or row.get("brier") is None:
            continue
        key = (str(row["contract_id"]), str(row["family"]))
        by_key[key][str(row["condition"])] = row
    out: dict[str, tuple[list[float], list[float]]] = {}
    values_by_condition: dict[str, tuple[list[float], list[float]]] = defaultdict(lambda: ([], []))
    for arms in by_key.values():
        base = arms.get(BASELINE)
        if not base:
            continue
        for condition, row in arms.items():
            if condition == BASELINE:
                continue
            condition_values, baseline_values = values_by_condition[condition]
            condition_values.append(float(row["brier"]))
            baseline_values.append(float(base["brier"]))
    for condition, pair in values_by_condition.items():
        out[condition] = pair
    return out


def summarize_delta_values(
    by_condition: dict[str, list[float]],
    pair_values: dict[str, tuple[list[float], list[float]]] | None = None,
) -> dict[str, Any]:
    pair_values = pair_values or {}
    out = {}
    for condition, values in sorted(by_condition.items()):
        condition_values, baseline_values = pair_values.get(condition, ([], []))
        perm = (
            paired_permutation_test(condition_values, baseline_values, n_perm=5000, seed=42)
            if condition_values and baseline_values
            else {}
        )
        out[condition] = {
            "paired_n": len(values),
            "mean_delta_vs_baseline": round(statistics.mean(values), 6) if values else None,
            "median_delta_vs_baseline": round(statistics.median(values), 6) if values else None,
            "improved_pairs": sum(1 for value in values if value < 0),
            "worsened_pairs": sum(1 for value in values if value > 0),
            "paired_permutation": perm,
        }
    return out


def paired_deltas_by_family(calls: list[dict[str, Any]]) -> dict[str, Any]:
    families = sorted({str(row.get("family")) for row in calls if row.get("family")})
    return {
        family: paired_deltas([row for row in calls if str(row.get("family")) == family])
        for family in families
    }


def family_sign_summary(by_family: dict[str, Any]) -> dict[str, Any]:
    by_condition: dict[str, dict[str, Any]] = defaultdict(lambda: {"families_improved": [], "families_worsened": [], "families_zero": []})
    for family, condition_map in by_family.items():
        for condition, summary in condition_map.items():
            delta = summary.get("mean_delta_vs_baseline")
            if delta is None:
                continue
            if delta < 0:
                by_condition[condition]["families_improved"].append(family)
            elif delta > 0:
                by_condition[condition]["families_worsened"].append(family)
            else:
                by_condition[condition]["families_zero"].append(family)
    out = {}
    for condition, summary in sorted(by_condition.items()):
        out[condition] = {
            "n_families_improved": len(summary["families_improved"]),
            "n_families_worsened": len(summary["families_worsened"]),
            "families_improved": summary["families_improved"],
            "families_worsened": summary["families_worsened"],
            "families_zero": summary["families_zero"],
        }
    return out


def action_utility(row: dict[str, Any], y_known: int | None) -> float | None:
    parsed = parse_json(row.get("parsed_json"))
    action = normalize_action(parsed.get("selected_action_normalized") or parsed.get("selected_action"))
    if not action:
        return None
    if action == "abstain":
        return 0.0
    if action in {"reroute", "reroute_or_judge", "judge"}:
        return None
    if action not in FORECAST_ACTION_ALIASES or y_known not in (0, 1):
        return None
    p = row.get("p_success")
    if p is None:
        p = parsed.get("p_success")
    if action in {"forecast_yes", "yes"}:
        pred = 1
    elif action in {"forecast_no", "no"}:
        pred = 0
    else:
        try:
            p_float = float(p)
        except Exception:
            return None
        pred = 1 if p_float >= 0.5 else 0
    return 1.0 if pred == int(y_known) else -1.0


def utility_summary(
    calls: list[dict[str, Any]],
    y_by_contract: dict[str, int | None],
    *,
    conditions: set[str] | None = None,
) -> dict[str, Any]:
    conditions = conditions or {"selective_action"}
    values = []
    unresolved_actions = Counter()
    action_counts = Counter()
    for row in calls:
        if row.get("condition") not in conditions or not row.get("schema_ok"):
            continue
        parsed = parse_json(row.get("parsed_json"))
        action = normalize_action(parsed.get("selected_action_normalized") or parsed.get("selected_action"))
        action_bucket = "forecast" if action in FORECAST_ACTION_ALIASES else action
        action_counts[action_bucket or "missing"] += 1
        util = action_utility(row, y_by_contract.get(str(row["contract_id"])))
        if util is None:
            unresolved_actions[action_bucket or "missing"] += 1
        else:
            values.append(util)
    return {
        "conditions": sorted(conditions),
        "action_counts": dict(action_counts),
        "scoreable_utility_rows": len(values),
        "mean_utility": round(statistics.mean(values), 6) if values else None,
        "unresolved_action_counts": dict(unresolved_actions),
        "note": "reroute_or_judge requires a review result before final utility can be scored",
    }


def forecast_utility_from_p(p: Any, y_known: int | None) -> float | None:
    if y_known not in (0, 1):
        return None
    try:
        p_float = float(p)
    except Exception:
        return None
    pred = 1 if p_float >= 0.5 else 0
    return 1.0 if pred == int(y_known) else -1.0


def action_control_summary(calls: list[dict[str, Any]], y_by_contract: dict[str, int | None], pilot_id: str) -> dict[str, Any]:
    baseline_rows = [
        row
        for row in calls
        if row.get("condition") == BASELINE and row.get("schema_ok") and row.get("p_success") is not None
    ]
    forecast_all_values = []
    threshold_values = []
    threshold_actions = Counter()
    for row in baseline_rows:
        y_known = y_by_contract.get(str(row["contract_id"]))
        util = forecast_utility_from_p(row.get("p_success"), y_known)
        if util is None:
            continue
        forecast_all_values.append(util)
        p_float = float(row["p_success"])
        if abs(p_float - 0.5) < 0.20:
            threshold_values.append(0.0)
            threshold_actions["abstain"] += 1
        else:
            threshold_values.append(util)
            threshold_actions["forecast"] += 1

    selective = utility_summary(calls, y_by_contract, conditions={"selective_action"})
    selective_mean = selective.get("mean_utility")
    controls = {
        "baseline_forecast_all": {
            "scoreable_rows": len(forecast_all_values),
            "mean_utility": round(statistics.mean(forecast_all_values), 6) if forecast_all_values else None,
        },
        "abstain_all": {
            "scoreable_rows": len(baseline_rows),
            "mean_utility": 0.0 if baseline_rows else None,
        },
        "confidence_threshold_abstain_abs_p_minus_0p5_lt_0p20": {
            "scoreable_rows": len(threshold_values),
            "mean_utility": round(statistics.mean(threshold_values), 6) if threshold_values else None,
            "action_counts": dict(threshold_actions),
        },
    }
    return {
        "schema": "gp245-action-control-score-v2",
        "applies_when_pilot_id": pilot_id,
        "baseline_rows_with_p": len(baseline_rows),
        "controls": controls,
        "selective_action_observed": selective,
        "selective_minus_controls": {
            control_id: (
                round(float(selective_mean) - float(summary["mean_utility"]), 6)
                if selective_mean is not None and summary.get("mean_utility") is not None
                else None
            )
            for control_id, summary in controls.items()
        },
        "promotion_rule": promotion_rule_for(pilot_id),
        "unresolved_judge_review_note": (
            "Rows selecting reroute_or_judge remain unresolved until an independent blind review row "
            "is ingested; unresolved rows cannot count as wins."
        ),
    }


def promotion_rule_for(pilot_id: str) -> str:
    if pilot_id == "n9_carrier_vs_prose_v1":
        return (
            "N9 promotes only if typed_carrier_forecast beats both baseline and "
            "free_prose_forecast on paired Brier, and carrier_to_action_execution "
            "beats forecast-all, abstain-all, and confidence-threshold controls on "
            "costed utility. Free-prose improvement alone does not support the carrier law."
        )
    if pilot_id == "n10_hard_prompt_break_v1":
        return (
            "N10 promotes only if hard_prompt_break_carrier_then_forecast beats baseline, "
            "free_prose_forecast, and single_turn_typed_carrier_forecast on paired Brier. "
            "A win over free prose alone supports at most the N9 carrier result, not the "
            "hard-prompt-break mechanism."
        )
    if pilot_id == "n4_decision_only_action_policy_v1":
        return (
            "N4 promotes only if selective_action mean utility beats abstain_all, "
            "baseline_forecast_all, and confidence-threshold abstention; paired Brier is "
            "secondary/reporting-only."
        )
    return (
        "N3 promotes only if selective_action beats paired Brier baseline and "
        "mean utility beats abstain_all plus the confidence-threshold abstention control."
    )


def utility_by_family(calls: list[dict[str, Any]], y_by_contract: dict[str, int | None]) -> dict[str, Any]:
    families = sorted({str(row.get("family")) for row in calls if row.get("family")})
    return {
        family: utility_summary([row for row in calls if str(row.get("family")) == family], y_by_contract)
        for family in families
    }


def carrier_action_utility_summary(calls: list[dict[str, Any]], y_by_contract: dict[str, int | None]) -> dict[str, Any]:
    action_calls = [
        row for row in calls if row.get("condition") == "carrier_to_action_execution" and row.get("schema_ok")
    ]
    observed = utility_summary(calls, y_by_contract, conditions={"carrier_to_action_execution"})
    baseline_rows = [
        row
        for row in calls
        if row.get("condition") == BASELINE and row.get("schema_ok") and row.get("p_success") is not None
    ]
    forecast_all = []
    threshold = []
    threshold_actions = Counter()
    for row in baseline_rows:
        y_known = y_by_contract.get(str(row["contract_id"]))
        util = forecast_utility_from_p(row.get("p_success"), y_known)
        if util is None:
            continue
        forecast_all.append(util)
        p_float = float(row["p_success"])
        if abs(p_float - 0.5) < 0.20:
            threshold.append(0.0)
            threshold_actions["abstain"] += 1
        else:
            threshold.append(util)
            threshold_actions["forecast"] += 1
    controls = {
        "baseline_forecast_all": {
            "scoreable_rows": len(forecast_all),
            "mean_utility": round(statistics.mean(forecast_all), 6) if forecast_all else None,
        },
        "abstain_all": {
            "scoreable_rows": len(baseline_rows),
            "mean_utility": 0.0 if baseline_rows else None,
        },
        "confidence_threshold_abstain_abs_p_minus_0p5_lt_0p20": {
            "scoreable_rows": len(threshold),
            "mean_utility": round(statistics.mean(threshold), 6) if threshold else None,
            "action_counts": dict(threshold_actions),
        },
    }
    observed_mean = observed.get("mean_utility")
    return {
        "schema": "gp245-carrier-action-utility-v1",
        "carrier_action_rows": len(action_calls),
        "observed": observed,
        "controls": controls,
        "carrier_action_minus_controls": {
            key: (
                round(float(observed_mean) - float(value["mean_utility"]), 6)
                if observed_mean is not None and value.get("mean_utility") is not None
                else None
            )
            for key, value in controls.items()
        },
    }


def probability_repair_summary(calls: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [
        row
        for row in calls
        if row.get("condition")
        in {
            "probability_repair",
            "selection_aware_probability_repair",
            "guarded_selection_aware_probability_repair",
        }
        and row.get("schema_ok")
    ]
    before_values = []
    final_values = []
    base_values = []
    raw_base_values = []
    selected_base_values = []
    chosen_base_values = []
    anchor_values = []
    revision_values = []
    condition_counts = Counter()
    chosen_reference_classes = Counter()
    guard_decisions = Counter()
    for row in rows:
        parsed = parse_json(row.get("parsed_json"))
        try:
            before_values.append(float(parsed["p_success_before_repair"]))
            final_values.append(float(row.get("p_success", parsed["p_success"])))
            condition_counts[str(row.get("condition"))] += 1
            if "base_rate_used" in parsed:
                base_values.append(float(parsed["base_rate_used"]))
            if "raw_event_base_rate" in parsed:
                raw_base_values.append(float(parsed["raw_event_base_rate"]))
            if "market_selected_base_rate" in parsed:
                selected_base_values.append(float(parsed["market_selected_base_rate"]))
            if "chosen_base_rate" in parsed:
                chosen_base_values.append(float(parsed["chosen_base_rate"]))
            if "baseline_anchor_p" in parsed:
                anchor_values.append(float(parsed["baseline_anchor_p"]))
            if parsed.get("chosen_reference_class"):
                chosen_reference_classes[str(parsed["chosen_reference_class"])] += 1
            if parsed.get("guard_decision"):
                guard_decisions[str(parsed["guard_decision"])] += 1
            if "revision_delta" in parsed:
                revision_values.append(float(parsed["revision_delta"]))
            elif "revision_delta_vs_anchor" in parsed:
                revision_values.append(float(parsed["revision_delta_vs_anchor"]))
        except Exception:
            continue
    return {
        "schema": "gp245-probability-repair-summary-v1",
        "rows": len(rows),
        "numeric_rows": len(final_values),
        "condition_counts": dict(condition_counts),
        "mean_p_before": round(statistics.mean(before_values), 6) if before_values else None,
        "mean_p_final": round(statistics.mean(final_values), 6) if final_values else None,
        "mean_baseline_anchor_p": round(statistics.mean(anchor_values), 6) if anchor_values else None,
        "mean_base_rate_used": round(statistics.mean(base_values), 6) if base_values else None,
        "mean_raw_event_base_rate": round(statistics.mean(raw_base_values), 6) if raw_base_values else None,
        "mean_market_selected_base_rate": round(statistics.mean(selected_base_values), 6) if selected_base_values else None,
        "mean_chosen_base_rate": round(statistics.mean(chosen_base_values), 6) if chosen_base_values else None,
        "mean_revision_delta": round(statistics.mean(revision_values), 6) if revision_values else None,
        "nonzero_revisions": sum(1 for value in revision_values if abs(value) > 1e-12),
        "chosen_reference_classes": dict(chosen_reference_classes),
        "guard_decisions": dict(guard_decisions),
    }


def build_report(db: Path, queue_path: Path, pilot_id: str) -> dict[str, Any]:
    dispatch = read_jsonl(queue_path)
    calls = load_calls(db, pilot_id)
    y_by_contract = load_y_known(db, {str(row["contract_id"]) for row in dispatch})
    expected_keys = {
        (row["contract_id"], row["family"], row["condition"])
        for row in dispatch
    }
    call_keys = {
        (row["contract_id"], row["family"], row["condition"])
        for row in calls
        if row.get("schema_ok")
    }
    missing = sorted(expected_keys - call_keys)
    extra = sorted(call_keys - expected_keys)
    condition_counts = Counter(row["condition"] for row in calls if row.get("schema_ok"))
    has_selective_action = any(row.get("condition") == "selective_action" for row in calls if row.get("schema_ok"))
    has_carrier_action = any(
        row.get("condition") == "carrier_to_action_execution" for row in calls if row.get("schema_ok")
    )
    has_probability_repair = any(
        row.get("condition")
        in {
            "probability_repair",
            "selection_aware_probability_repair",
            "guarded_selection_aware_probability_repair",
        }
        for row in calls
        if row.get("schema_ok")
    )
    ready = not missing and bool(expected_keys)
    scored_calls = [row for row in calls if row.get("schema_ok") and row.get("brier") is not None]
    paired = paired_deltas(calls)
    paired_family = paired_deltas_by_family(calls)
    utility = utility_summary(calls, y_by_contract)
    action_control = action_control_summary(calls, y_by_contract, pilot_id) if has_selective_action else None
    return {
        "schema": "gp245-nurture-score-v2",
        "pilot_id": pilot_id,
        "queue_path": repo_relative(queue_path),
        "expected_dispatch_rows": len(expected_keys),
        "db_schema_ok_rows": len(call_keys),
        "db_brier_rows": len(scored_calls),
        "missing_dispatch_rows": len(missing),
        "extra_db_rows": len(extra),
        "condition_counts": dict(sorted(condition_counts.items())),
        "status": "ready_to_score" if ready else ("partial_smoke_scored" if scored_calls else "db_calls_missing"),
        "paired_brier": paired,
        "paired_brier_by_family": paired_family,
        "family_sign_summary": family_sign_summary(paired_family),
        "selective_action_utility": utility,
        "selective_action_utility_by_family": utility_by_family(calls, y_by_contract),
        "action_control_utility": action_control,
        "carrier_action_utility": carrier_action_utility_summary(calls, y_by_contract) if has_carrier_action else None,
        "probability_repair_summary": probability_repair_summary(calls) if has_probability_repair else None,
        "missing_examples": [
            {"contract_id": cid, "family": family, "condition": condition}
            for cid, family, condition in missing[:20]
        ],
        "extra_examples": [
            {"contract_id": cid, "family": family, "condition": condition}
            for cid, family, condition in extra[:20]
        ],
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        f"# Forecast Nurture Score Report: {report['pilot_id']}",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Pilot ID: `{report['pilot_id']}`",
        f"- Status: `{report['status']}`",
        f"- Expected dispatch rows: {report['expected_dispatch_rows']}",
        f"- DB schema-ok rows: {report['db_schema_ok_rows']}",
        f"- DB Brier rows: {report['db_brier_rows']}",
        f"- Missing dispatch rows: {report['missing_dispatch_rows']}",
        f"- Extra DB rows: {report['extra_db_rows']}",
        f"- Condition counts: `{report['condition_counts']}`",
        "",
    ]
    if report["paired_brier"]:
        lines.extend(
            [
                "## Available Paired Brier",
                "",
                "```json",
                json.dumps(report["paired_brier"], indent=2, sort_keys=True),
                "```",
                "",
                "## Family Sign Summary",
                "",
                "```json",
                json.dumps(report["family_sign_summary"], indent=2, sort_keys=True),
                "```",
                "",
                "## Paired Brier By Family",
                "",
                "```json",
                json.dumps(report["paired_brier_by_family"], indent=2, sort_keys=True),
                "```",
                "",
                "## Selective Action Utility",
                "",
                "```json",
                json.dumps(report["selective_action_utility"], indent=2, sort_keys=True),
                "```",
                "",
                "## Selective Action Utility By Family",
                "",
                "```json",
                json.dumps(report["selective_action_utility_by_family"], indent=2, sort_keys=True),
                "```",
                "",
            ]
        )
    if report.get("probability_repair_summary"):
        lines.extend(
            [
                "## Probability-Repair Summary",
                "",
                "```json",
                json.dumps(report["probability_repair_summary"], indent=2, sort_keys=True),
                "```",
                "",
            ]
        )
    if report.get("action_control_utility"):
        lines.extend(
            [
                "## Action-Control Utility",
                "",
                "```json",
                json.dumps(report["action_control_utility"], indent=2, sort_keys=True),
                "```",
                "",
            ]
        )
    if report.get("carrier_action_utility"):
        lines.extend(
            [
                "## Carrier-To-Action Utility",
                "",
                "```json",
                json.dumps(report["carrier_action_utility"], indent=2, sort_keys=True),
                "```",
                "",
            ]
        )
    if report["status"] != "ready_to_score":
        lines.extend(
            [
                "## Missing Examples",
                "",
                "```json",
                json.dumps(report["missing_examples"], indent=2, sort_keys=True),
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--pilot-id", default="n1_nurture_intervention_v1")
    args = parser.parse_args()
    report = build_report(args.db, args.queue, args.pilot_id)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = "n1_nurture_intervention" if args.pilot_id == "n1_nurture_intervention_v1" else args.pilot_id
    (args.out_dir / f"{stem}_score_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / f"{stem}_score_report.md").write_text(
        render_md(report),
        encoding="utf-8",
    )
    print(f"wrote {args.out_dir / f'{stem}_score_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
