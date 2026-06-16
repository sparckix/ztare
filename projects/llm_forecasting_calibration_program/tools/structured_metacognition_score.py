#!/usr/bin/env python3
"""Score the structured-metacognition public-corpus experiment."""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = PROGRAM / "structured_metacognition_v1/workspace"
DEFAULT_QUEUE = DEFAULT_OUT / "structured_metacognition_public_v1_dispatch_queue.jsonl"
DEFAULT_PILOT_ID = "structured_metacognition_public_v1"
CONTROL_CONDITIONS = ("bare_forecast", "length_matched_placebo")
INTERVENTION_CONDITIONS = (
    "expert_training_prompt",
    "audit_informed_prompt",
    "failure_mode_specific_prompt",
)
ALPHA = 0.05


def load_rows(db: Path, pilot_id: str) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        rows = [
            dict(row)
            for row in con.execute(
                """
                SELECT pc.contract_id, pc.family, pc.condition, pc.brier,
                       c.source, c.y_known
                FROM pilot_calls pc
                JOIN contracts c ON c.contract_id = pc.contract_id
                WHERE pc.pilot_id = ?
                  AND pc.schema_ok = 1
                  AND pc.brier IS NOT NULL
                  AND c.y_known IN (0, 1)
                """,
                (pilot_id,),
            )
        ]
    finally:
        con.close()
    return rows


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def sign_p_value(diffs: list[float]) -> float | None:
    nonzero = [diff for diff in diffs if abs(diff) > 1e-12]
    n = len(nonzero)
    if n == 0:
        return None
    wins = sum(1 for diff in nonzero if diff < 0)
    lower = sum(math.comb(n, k) for k in range(0, wins + 1)) / (2**n)
    upper = sum(math.comb(n, k) for k in range(wins, n + 1)) / (2**n)
    return min(1.0, 2 * min(lower, upper))


def paired_deltas(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        key = (str(row["contract_id"]), str(row["family"]))
        by_key[key][str(row["condition"])] = row

    out: list[dict[str, Any]] = []
    for (contract_id, family), conditions in sorted(by_key.items()):
        for condition, row in conditions.items():
            if condition in CONTROL_CONDITIONS:
                continue
            for control in CONTROL_CONDITIONS:
                control_row = conditions.get(control)
                if not control_row:
                    continue
                out.append(
                    {
                        "contract_id": contract_id,
                        "family": family,
                        "source": row.get("source"),
                        "condition": condition,
                        "control": control,
                        "delta_brier": float(row["brier"]) - float(control_row["brier"]),
                    }
                )
    return out


def condition_source_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        source = str(row.get("source") or "")
        condition = str(row.get("condition") or "")
        counts[f"{source}:{condition}"] += 1
    return dict(sorted(counts.items()))


def completion_coverage(scored_rows: list[dict[str, Any]], queue_rows: list[dict[str, Any]]) -> dict[str, Any]:
    planned = condition_source_counts(queue_rows)
    scored = condition_source_counts(scored_rows)
    missing = {
        key: planned_n - scored.get(key, 0)
        for key, planned_n in planned.items()
        if planned_n - scored.get(key, 0) > 0
    }
    by_contract: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in scored_rows:
        by_contract[(str(row["contract_id"]), str(row["family"]))].add(str(row["condition"]))
    required_conditions = {
        "bare_forecast",
        "length_matched_placebo",
        "expert_training_prompt",
        "audit_informed_prompt",
        "failure_mode_specific_prompt",
    }
    complete_blocks = sum(1 for conditions in by_contract.values() if required_conditions.issubset(conditions))
    return {
        "planned_rows": len(queue_rows),
        "scored_rows": len(scored_rows),
        "completion_share": round(len(scored_rows) / len(queue_rows), 6) if queue_rows else None,
        "planned_by_source_condition": planned,
        "scored_by_source_condition": scored,
        "missing_by_source_condition": dict(sorted(missing.items())),
        "complete_contract_family_blocks": complete_blocks,
        "complete_contract_family_block_share": round(complete_blocks / (len(queue_rows) / 5), 6) if queue_rows else None,
    }


def summarize_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    diffs = [float(row["delta_brier"]) for row in rows]
    return {
        "n": len(diffs),
        "mean_delta_brier": sum(diffs) / len(diffs),
        "wins": sum(1 for diff in diffs if diff < 0),
        "losses": sum(1 for diff in diffs if diff > 0),
        "ties": sum(1 for diff in diffs if abs(diff) <= 1e-12),
        "sign_p": sign_p_value(diffs),
    }


def source_survival_summary(by_source: dict[str, dict[str, Any]], condition: str) -> dict[str, Any]:
    sources = sorted(
        {
            key.split(":", 1)[0]
            for key in by_source
            if key.endswith(f":{condition}_vs_bare_forecast")
            or f":{condition}_vs_length_matched_placebo" in key
        }
    )
    rows: dict[str, dict[str, Any]] = {}
    regressions: list[str] = []
    directional_wins: list[str] = []
    for source in sources:
        vs_bare = by_source.get(f"{source}:{condition}_vs_bare_forecast", {})
        vs_placebo = by_source.get(f"{source}:{condition}_vs_length_matched_placebo", {})
        beats_bare_mean = vs_bare.get("n", 0) > 0 and vs_bare.get("mean_delta_brier", 1.0) < 0
        beats_placebo_mean = vs_placebo.get("n", 0) > 0 and vs_placebo.get("mean_delta_brier", 1.0) < 0
        regresses_bare_mean = vs_bare.get("n", 0) > 0 and vs_bare.get("mean_delta_brier", 0.0) > 0
        regresses_placebo_mean = vs_placebo.get("n", 0) > 0 and vs_placebo.get("mean_delta_brier", 0.0) > 0
        if beats_bare_mean and beats_placebo_mean:
            directional_wins.append(source)
        if regresses_bare_mean or regresses_placebo_mean:
            regressions.append(source)
        rows[source] = {
            "beats_bare_mean": beats_bare_mean,
            "beats_placebo_mean": beats_placebo_mean,
            "regresses_bare_mean": regresses_bare_mean,
            "regresses_placebo_mean": regresses_placebo_mean,
            "vs_bare": vs_bare,
            "vs_placebo": vs_placebo,
        }
    return {
        "sources": rows,
        "directional_win_sources": directional_wins,
        "regression_sources": sorted(set(regressions)),
        "survives_all_sources_directionally": bool(rows) and not regressions,
    }


def condition_gate_verdict(
    overall: dict[str, dict[str, Any]], by_source: dict[str, dict[str, Any]], condition: str
) -> dict[str, Any]:
    vs_bare = overall.get(f"{condition}_vs_bare_forecast", {})
    vs_placebo = overall.get(f"{condition}_vs_length_matched_placebo", {})
    source_survival = source_survival_summary(by_source, condition)
    required = {
        "beats_bare_mean": vs_bare.get("n", 0) > 0 and vs_bare.get("mean_delta_brier", 1.0) < 0,
        "beats_placebo_mean": vs_placebo.get("n", 0) > 0 and vs_placebo.get("mean_delta_brier", 1.0) < 0,
        "beats_bare_sign": (vs_bare.get("sign_p") or 1.0) <= ALPHA,
        "beats_placebo_sign": (vs_placebo.get("sign_p") or 1.0) <= ALPHA,
        "survives_source_means": source_survival["survives_all_sources_directionally"],
    }
    passes_pairwise_gate = all(required.values())
    if passes_pairwise_gate:
        verdict = "passes_pairwise_bare_and_placebo_gate_pending_source_and_external_controls"
    elif not required["beats_bare_mean"]:
        verdict = "does_not_beat_bare_mean"
    elif not required["beats_placebo_mean"]:
        verdict = "does_not_beat_placebo_mean"
    else:
        verdict = "directional_not_statistically_secure"
    return {
        "condition": condition,
        "verdict": verdict,
        "passes_pairwise_gate": passes_pairwise_gate,
        "requirements": required,
        "source_survival": source_survival,
        "vs_bare": vs_bare,
        "vs_placebo": vs_placebo,
    }


def build_report(rows: list[dict[str, Any]], pilot_id: str, queue_rows: list[dict[str, Any]]) -> dict[str, Any]:
    deltas = paired_deltas(rows)
    by_condition_control: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    by_source_condition_control: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in deltas:
        by_condition_control[(row["condition"], row["control"])].append(row)
        by_source_condition_control[(str(row["source"]), row["condition"], row["control"])].append(row)

    overall = {
        f"{condition}_vs_{control}": summarize_group(group)
        for (condition, control), group in sorted(by_condition_control.items())
    }
    by_source = {
        f"{source}:{condition}_vs_{control}": summarize_group(group)
        for (source, condition, control), group in sorted(by_source_condition_control.items())
    }

    condition_gates = {
        condition: condition_gate_verdict(overall, by_source, condition)
        for condition in INTERVENTION_CONDITIONS
    }
    passes_primary = any(gate["passes_pairwise_gate"] for gate in condition_gates.values())
    return {
        "schema": "structured-metacognition-score-v1",
        "pilot_id": pilot_id,
        "input_rows": len(rows),
        "paired_delta_rows": len(deltas),
        "coverage": completion_coverage(rows, queue_rows),
        "overall": overall,
        "by_source": by_source,
        "condition_gates": condition_gates,
        "primary_verdict": (
            "passes_primary_pairwise_gate_pending_source_and_external_controls"
            if passes_primary
            else "not_promoted_or_not_ready"
        ),
        "promotion_note": (
            "Primary gate requires an intervention arm to improve paired Brier over both bare forecast and "
            "length-matched placebo with a sign test at alpha=0.05; "
            "paper promotion also requires source-stratified survival and comparison with confident-NO where defined."
        ),
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# Structured Metacognition Score Report",
        "",
        f"- Pilot ID: `{report['pilot_id']}`",
        f"- Input scored rows: `{report['input_rows']}`",
        f"- Paired delta rows: `{report['paired_delta_rows']}`",
        f"- Primary verdict: `{report['primary_verdict']}`",
        "",
        "Coverage:",
        "```json",
        json.dumps(report["coverage"], indent=2, sort_keys=True),
        "```",
        "",
        "Overall paired deltas:",
        "```json",
        json.dumps(report["overall"], indent=2, sort_keys=True),
        "```",
        "",
        "Intervention gate verdicts:",
        "```json",
        json.dumps(report["condition_gates"], indent=2, sort_keys=True),
        "```",
        "",
        "Source-stratified paired deltas:",
        "```json",
        json.dumps(report["by_source"], indent=2, sort_keys=True),
        "```",
        "",
        report["promotion_note"],
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--pilot-id", default=DEFAULT_PILOT_ID)
    args = parser.parse_args()

    rows = load_rows(args.db, args.pilot_id)
    queue_rows = [row for row in load_jsonl(args.queue) if row.get("pilot_id") == args.pilot_id]
    report = build_report(rows, args.pilot_id, queue_rows)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / f"{args.pilot_id}_score_report.json"
    md_path = args.out_dir / f"{args.pilot_id}_score_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_md(report), encoding="utf-8")
    print(json.dumps({"report": str(json_path), "primary_verdict": report["primary_verdict"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
