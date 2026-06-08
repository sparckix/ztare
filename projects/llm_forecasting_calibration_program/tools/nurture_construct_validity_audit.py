#!/usr/bin/env python3
"""Audit whether a forecast-nurture intervention is measuring its intended construct."""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_QUEUE = (
    REPO
    / "projects/llm_forecasting_calibration_program/nurture_intervention_v1/workspace"
    / "n3_high_worry_action_policy_dispatch_queue.jsonl"
)
DEFAULT_OUT = REPO / "projects/llm_forecasting_calibration_program/nurture_intervention_v1/workspace"
BASELINE = "baseline"


def repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def parse_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_calls(db: Path, pilot_id: str) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = [
        dict(row)
        for row in con.execute(
            """
            SELECT pc.pilot_id, pc.contract_id, pc.family, pc.condition,
                   pc.p_success, pc.brier, pc.schema_ok, pc.parsed_json,
                   c.y_known
            FROM pilot_calls pc
            LEFT JOIN contracts c ON c.contract_id = pc.contract_id
            WHERE pc.pilot_id = ?
            """,
            (pilot_id,),
        )
    ]
    con.close()
    return rows


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


def action_bucket(action: str) -> str:
    if action in {"forecast", "forecast_yes", "forecast_no", "yes", "no"}:
        return "forecast"
    return action or "missing"


def pair_calls(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in calls:
        if not row.get("schema_ok"):
            continue
        by_key[(str(row["contract_id"]), str(row["family"]))][str(row["condition"])] = row
    pairs = []
    for (contract_id, family), arms in sorted(by_key.items()):
        base = arms.get(BASELINE)
        action = arms.get("selective_action")
        if not base or not action:
            continue
        parsed_action = parse_json(action.get("parsed_json"))
        selected = normalize_action(
            parsed_action.get("selected_action_normalized") or parsed_action.get("selected_action")
        )
        pairs.append(
            {
                "contract_id": contract_id,
                "family": family,
                "baseline_p": base.get("p_success"),
                "action_p": action.get("p_success"),
                "baseline_brier": base.get("brier"),
                "action_brier": action.get("brier"),
                "p_changed": base.get("p_success") != action.get("p_success"),
                "brier_delta": (
                    float(action["brier"]) - float(base["brier"])
                    if action.get("brier") is not None and base.get("brier") is not None
                    else None
                ),
                "selected_action": selected,
                "selected_action_bucket": action_bucket(selected),
                "y_known": action.get("y_known"),
            }
        )
    return pairs


def build_report(db: Path, queue: Path, pilot_id: str) -> dict[str, Any]:
    dispatch = load_jsonl(queue)
    calls = load_calls(db, pilot_id)
    pairs = pair_calls(calls)
    action_counts = Counter(pair["selected_action_bucket"] for pair in pairs)
    p_unchanged = sum(1 for pair in pairs if not pair["p_changed"])
    brier_deltas = [pair["brier_delta"] for pair in pairs if pair["brier_delta"] is not None]
    utility_report = parse_score_report_json(pilot_id)
    design_flags = []
    if pairs and p_unchanged == len(pairs):
        design_flags.append("probability_endpoint_insensitive_all_action_ps_equal_baseline")
    if action_counts.get("reroute_or_judge", 0):
        design_flags.append("reroute_rows_require_blind_review_before_utility_claim")
    n3_utility = utility_report.get("n3_action_control_utility", {})
    selective_minus_controls = n3_utility.get("selective_minus_controls", {})
    if any(value is not None and float(value) < 0 for value in selective_minus_controls.values()):
        design_flags.append("current_action_policy_loses_to_at_least_one_simple_control")
    verdict = (
        "construct_validity_repair_required"
        if "probability_endpoint_insensitive_all_action_ps_equal_baseline" in design_flags
        else "construct_validity_watch"
    )
    return {
        "schema": "gp245-nurture-construct-validity-audit-v1",
        "pilot_id": pilot_id,
        "db": repo_relative(db),
        "queue": repo_relative(queue),
        "dispatch_rows": len(dispatch),
        "db_schema_ok_rows": sum(1 for row in calls if row.get("schema_ok")),
        "paired_rows": len(pairs),
        "p_unchanged_pairs": p_unchanged,
        "p_changed_pairs": len(pairs) - p_unchanged,
        "brier_delta_values": brier_deltas,
        "action_counts": dict(action_counts),
        "design_flags": design_flags,
        "verdict": verdict,
        "interpretation": (
            "Current N3 is a useful action-policy smoke, but Brier should be secondary unless the arm is redesigned "
            "to alter probability generation. For action policy, primary promotion should be utility against "
            "abstain-all, forecast-all, confidence-threshold abstention, and resolved blind-review reroute rows."
        ),
        "recommended_next_design": {
            "n3_current": "continue only as bounded smoke; do not promote if utility remains below controls",
            "n4_decision_only": (
                "separate action policy from probability repair: require selected_action in "
                "{forecast_yes,forecast_no,abstain,reroute_or_judge}; score utility as primary; "
                "do not require paired Brier improvement"
            ),
            "probability_repair_arm": (
                "if Brier improvement is the target, use a separate reference-class/base-rate repair arm "
                "with p_success as the primary endpoint"
            ),
        },
        "paired_examples": pairs[:20],
    }


def parse_score_report_json(pilot_id: str) -> dict[str, Any]:
    path = DEFAULT_OUT / f"{pilot_id}_score_report.json"
    if not path.exists():
        return {}
    return parse_json(path.read_text(encoding="utf-8"))


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# Nurture Construct-Validity Audit",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Pilot ID: `{report['pilot_id']}`",
        f"- Verdict: `{report['verdict']}`",
        f"- DB schema-ok rows: {report['db_schema_ok_rows']}",
        f"- Paired rows: {report['paired_rows']}",
        f"- p unchanged pairs: {report['p_unchanged_pairs']}",
        f"- p changed pairs: {report['p_changed_pairs']}",
        f"- Action counts: `{report['action_counts']}`",
        f"- Design flags: `{report['design_flags']}`",
        "",
        "## Interpretation",
        "",
        report["interpretation"],
        "",
        "## Recommended Next Design",
        "",
        "```json",
        json.dumps(report["recommended_next_design"], indent=2, sort_keys=True),
        "```",
        "",
        "## Paired Examples",
        "",
        "```json",
        json.dumps(report["paired_examples"], indent=2, sort_keys=True),
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--pilot-id", default="n3_high_worry_action_policy_v1")
    args = parser.parse_args()
    report = build_report(args.db, args.queue, args.pilot_id)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.pilot_id}_construct_validity_audit"
    (args.out_dir / f"{stem}.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (args.out_dir / f"{stem}.md").write_text(render_md(report))
    print(f"wrote {args.out_dir / f'{stem}.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
