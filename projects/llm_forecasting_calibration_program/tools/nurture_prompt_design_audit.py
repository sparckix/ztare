#!/usr/bin/env python3
"""Cross-pilot construct-validity audit for forecast-nurture prompts.

This answers a narrower question than the Brier score reports: what prompt
classes have actually been tested well enough to scope, and what parts of the
"nurture" thesis remain untested because the instrument is too weak, too small,
or targets action rather than probability?
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "nurture_intervention_v1/workspace"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT_JSON = WORKSPACE / "nurture_prompt_design_audit_2026_06_03.json"
DEFAULT_OUT_MD = WORKSPACE / "nurture_prompt_design_audit_2026_06_03.md"


PILOTS = [
    {
        "pilot_id": "n1_nurture_intervention_v1",
        "queue": "n1_nurture_intervention_dispatch_queue.jsonl",
        "score": "n1_nurture_intervention_score_report.json",
        "prompt_classes": [
            "diagnostic_only",
            "reference_class_numeric",
            "contrastive_numeric_revision",
            "selective_action",
        ],
        "design_intent": "broad first-pass nurture packet",
    },
    {
        "pilot_id": "n2_selective_action_confirmatory_v1",
        "queue": "n2_selective_action_confirmatory_dispatch_queue.jsonl",
        "score": "n2_selective_action_confirmatory_v1_score_report.json",
        "prompt_classes": ["selective_action_confirmation"],
        "design_intent": "confirm N1 selective-action result",
    },
    {
        "pilot_id": "n3_high_worry_action_policy_v1",
        "queue": "n3_high_worry_action_policy_dispatch_queue.jsonl",
        "score": "n3_high_worry_action_policy_v1_score_report.json",
        "construct": "n3_high_worry_action_policy_v1_construct_validity_audit.json",
        "prompt_classes": ["high_worry_action_policy"],
        "design_intent": "utility/action policy on high-tail slice",
    },
    {
        "pilot_id": "n5_high_tail_probability_repair_v1",
        "queue": "n5_high_tail_probability_repair_dispatch_queue.jsonl",
        "score": "n5_high_tail_probability_repair_v1_score_report.json",
        "prompt_classes": ["base_rate_probability_repair"],
        "design_intent": "probability repair via explicit base rate",
    },
    {
        "pilot_id": "n6_selection_aware_probability_repair_v1",
        "queue": "n6_selection_aware_probability_repair_dispatch_queue.jsonl",
        "score": "n6_selection_aware_probability_repair_v1_score_report.json",
        "prompt_classes": ["selection_aware_probability_repair"],
        "design_intent": "repair N5 by pluralizing reference classes",
    },
    {
        "pilot_id": "n7_guarded_selection_aware_repair_v1",
        "queue": "n7_guarded_selection_aware_repair_combined_dispatch_queue.jsonl",
        "score": "n7_guarded_selection_aware_repair_v1_score_report.json",
        "prompt_classes": ["guarded_anchor_probability_repair"],
        "design_intent": "anchor-aware guarded reference-class repair",
    },
    {
        "pilot_id": "n9_carrier_vs_prose_v1",
        "queue": "n9_carrier_vs_prose_v1_dispatch_queue.jsonl",
        "score": "n9_carrier_vs_prose_v1_score_report.json",
        "prompt_classes": ["free_prose", "typed_carrier", "carrier_to_action"],
        "design_intent": "typed carrier vs ordinary prose",
    },
    {
        "pilot_id": "n10_hard_prompt_break_placebo_v1",
        "queue": "n10_hard_prompt_break_placebo_v1_dispatch_queue.jsonl",
        "score": "n10_hard_prompt_break_placebo_v1_score_report.json",
        "prompt_classes": ["hard_prompt_break", "two_stage_prose_placebo", "single_turn_carrier"],
        "design_intent": "hard prompt break plus two-call placebo control",
    },
]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def db_counts(db: Path, pilot_id: str) -> dict[str, Any]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            SELECT condition, COUNT(*) AS n,
                   SUM(CASE WHEN schema_ok = 1 THEN 1 ELSE 0 END) AS schema_ok,
                   SUM(CASE WHEN brier IS NOT NULL THEN 1 ELSE 0 END) AS with_brier,
                   COUNT(DISTINCT contract_id) AS contracts,
                   COUNT(DISTINCT family) AS families
            FROM pilot_calls
            WHERE pilot_id = ?
            GROUP BY condition
            """,
            (pilot_id,),
        ).fetchall()
    finally:
        con.close()
    by_condition = {str(row["condition"]): dict(row) for row in rows}
    return {
        "rows": sum(int(row["n"]) for row in by_condition.values()),
        "schema_ok_rows": sum(int(row["schema_ok"] or 0) for row in by_condition.values()),
        "with_brier_rows": sum(int(row["with_brier"] or 0) for row in by_condition.values()),
        "conditions": by_condition,
    }


def prompt_contract(row: dict[str, Any]) -> dict[str, Any]:
    pc = row.get("prompt_contract")
    return pc if isinstance(pc, dict) else {}


def queue_features(rows: list[dict[str, Any]]) -> dict[str, Any]:
    condition_counts = Counter(str(row.get("condition") or "") for row in rows)
    required_fields: dict[str, set[str]] = defaultdict(set)
    feature_counts = Counter()
    sources = Counter(str(row.get("source") or "") for row in rows)
    families = Counter(str(row.get("family") or "") for row in rows)
    for row in rows:
        condition = str(row.get("condition") or "")
        pc = prompt_contract(row)
        for field in pc.get("required_output_fields") or []:
            required_fields[condition].add(str(field))
        if pc.get("same_contract_across_arms"):
            feature_counts["same_contract_across_arms"] += 1
        if pc.get("no_web_tools"):
            feature_counts["no_web_tools"] += 1
        if pc.get("include_y_known") is False:
            feature_counts["outcome_hidden"] += 1
        if pc.get("correction_allowed") is False:
            feature_counts["diagnostic_no_correction"] += 1
        if "reference_class" in pc or "repair_contract" in pc:
            feature_counts["reference_or_repair_contract"] += 1
        if "utility_regime" in pc:
            feature_counts["utility_regime"] += 1
        if "carrier_contract" in pc:
            feature_counts["typed_carrier"] += 1
        if "stage_plan" in pc:
            feature_counts["multi_stage"] += 1
        if row.get("baseline_anchor_p") is not None:
            feature_counts["explicit_baseline_anchor"] += 1
    n = len(rows)
    return {
        "dispatch_rows": n,
        "condition_counts": dict(condition_counts),
        "source_counts": dict(sources),
        "family_counts": dict(families),
        "required_fields_by_condition": {
            condition: sorted(fields) for condition, fields in sorted(required_fields.items())
        },
        "feature_presence": {
            name: {"rows": count, "share": round(count / n, 4) if n else 0.0}
            for name, count in sorted(feature_counts.items())
        },
    }


def score_summary(score: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in (
        "summary_by_condition",
        "condition_counts",
        "condition_pair_summary",
        "condition_vs_baseline",
        "n3_action_control_utility",
        "carrier_action_minus_controls",
    ):
        if key in score:
            out[key] = score[key]
    return out


def classify_scope(pilot: dict[str, Any], queue: dict[str, Any], db: dict[str, Any], construct: dict[str, Any]) -> dict[str, Any]:
    flags: list[str] = []
    tested: list[str] = []
    untested: list[str] = []
    condition_counts = queue.get("condition_counts", {})
    feature_presence = queue.get("feature_presence", {})
    with_brier = int(db.get("with_brier_rows") or 0)

    if "baseline" in condition_counts:
        tested.append("same-contract baseline control")
    else:
        flags.append("missing_baseline_control")
    if feature_presence.get("outcome_hidden", {}).get("share") == 1.0:
        tested.append("outcome hidden from prompt")
    else:
        flags.append("outcome_hiding_not_uniform")
    if feature_presence.get("no_web_tools", {}).get("share") == 1.0:
        tested.append("tool-free prompt effect")
    else:
        flags.append("tool_access_not_uniform_or_unknown")
    if feature_presence.get("utility_regime", {}).get("rows", 0) > 0:
        tested.append("costed action selection")
    if feature_presence.get("reference_or_repair_contract", {}).get("rows", 0) > 0:
        tested.append("structured reference-class repair")
    if feature_presence.get("typed_carrier", {}).get("rows", 0) > 0:
        tested.append("typed evidence carrier")
    if feature_presence.get("multi_stage", {}).get("rows", 0) > 0:
        tested.append("two-stage prompt split")
    if feature_presence.get("explicit_baseline_anchor", {}).get("rows", 0) > 0:
        tested.append("explicit baseline anchor repair")

    if with_brier < 20:
        flags.append("underpowered_or_smoke_only")
    if construct.get("verdict") == "construct_validity_repair_required":
        flags.append("prior_construct_repair_required")

    untested.extend(
        [
            "tool-using live research nurture",
            "interactive multi-turn Socratic correction",
            "retrieval-grounded evidence update with equal information controls",
            "trained/few-shot prompt optimized on heldout development set",
            "human-written expert prompt with blinded prompt-quality review",
        ]
    )
    if "hard_prompt_break" not in pilot["prompt_classes"]:
        untested.append("hard prompt break for this prompt class")
    if "guarded_anchor_probability_repair" not in pilot["prompt_classes"]:
        untested.append("guarded anchor repair for this prompt class")

    if "underpowered_or_smoke_only" in flags:
        verdict = "scopes_prompt_variant_only_smoke"
    elif "prior_construct_repair_required" in flags:
        verdict = "design_validity_repair_required"
    elif any(cls in pilot["prompt_classes"] for cls in ("typed_carrier", "hard_prompt_break", "guarded_anchor_probability_repair")):
        verdict = "moderate_construct_validity_for_specific_variant"
    else:
        verdict = "specific_prompt_variant_tested"

    return {
        "verdict": verdict,
        "design_flags": flags,
        "tested_constructs": tested,
        "not_ruled_out": sorted(set(untested)),
    }


def build_report(db: Path) -> dict[str, Any]:
    pilots = []
    verdict_counts = Counter()
    for pilot in PILOTS:
        queue_rows = load_jsonl(WORKSPACE / pilot["queue"])
        score = load_json(WORKSPACE / pilot["score"])
        construct = load_json(WORKSPACE / pilot["construct"]) if pilot.get("construct") else {}
        q = queue_features(queue_rows)
        d = db_counts(db, pilot["pilot_id"])
        scope = classify_scope(pilot, q, d, construct)
        verdict_counts[scope["verdict"]] += 1
        pilots.append(
            {
                "pilot_id": pilot["pilot_id"],
                "design_intent": pilot["design_intent"],
                "prompt_classes": pilot["prompt_classes"],
                "queue": pilot["queue"],
                "score": pilot["score"],
                "queue_features": q,
                "db_counts": d,
                "score_summary": score_summary(score),
                "construct_audit": construct,
                "scope": scope,
            }
        )

    return {
        "schema": "gp245-nurture-prompt-design-audit-v1",
        "db": str(db),
        "audited_pilots": len(pilots),
        "verdict_counts": dict(verdict_counts),
        "global_verdict": "specific_nurture_prompt_families_scoped_not_global_prompt_engineering_falsified",
        "global_interpretation": (
            "The N-series is good enough to demote the tested families of generic rationale, "
            "selective action, naive/selection-aware reference-class repair, typed carrier, and hard prompt break. "
            "It is not good enough to rule out all prompt engineering or all nurture: tool-using, interactive, "
            "retrieval-grounded, expert-written, or development-set-optimized prompt programs remain untested."
        ),
        "pilots": pilots,
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# Nurture Prompt Design Audit",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Audited pilots: `{report['audited_pilots']}`",
        f"- Global verdict: `{report['global_verdict']}`",
        f"- Verdict counts: `{report['verdict_counts']}`",
        "",
        report["global_interpretation"],
        "",
        "## Pilot Matrix",
        "",
        "| pilot | prompt classes | db brier rows | verdict | design flags |",
        "|---|---|---:|---|---|",
    ]
    for pilot in report["pilots"]:
        flags = ", ".join(pilot["scope"]["design_flags"]) or "none"
        classes = ", ".join(pilot["prompt_classes"])
        lines.append(
            f"| `{pilot['pilot_id']}` | {classes} | "
            f"{pilot['db_counts']['with_brier_rows']} | `{pilot['scope']['verdict']}` | {flags} |"
        )
    lines.extend(
        [
            "",
            "## What Remains Untested",
            "",
        ]
    )
    not_ruled_out = sorted(
        {
            item
            for pilot in report["pilots"]
            for item in pilot["scope"]["not_ruled_out"]
        }
    )
    for item in not_ruled_out:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## JSON Detail",
            "",
            "```json",
            json.dumps(report, indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()
    report = build_report(args.db)
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    args.out_md.write_text(render_md(report))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
