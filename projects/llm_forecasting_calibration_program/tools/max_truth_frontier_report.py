#!/usr/bin/env python3
"""GP-245 maximal-truth frontier report.

This report is intentionally broader than the current top-law queue. It asks:
which next question would most change what we believe, and what capability
surface are we failing to consider if we stay anchored on human forecasting
biases?

No calls and no DB mutation.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = PROGRAM / "truth_seeking_v1/workspace"

REPORT_PATHS = {
    "truth_continuation": PROGRAM / "truth_seeking_v1/workspace/truth_continuation_report.json",
    "next_packets": PROGRAM / "truth_seeking_v1/workspace/next_experiment_packets.json",
    "base_rate_join": PROGRAM / "cutoff_validity_v1/workspace/cutoff_stage_c_base_rate_join_report.json",
    "equal_information": PROGRAM
    / "truth_continuation_v1/workspace/equal_information_baseline_void_2026_06_03/equal_information_baseline_void_report.json",
    "market_llm_blend": PROGRAM
    / "truth_continuation_v1/workspace/market_llm_blend_stage_c_2026_06_03/market_llm_blend_stage_c_report.json",
    "market_llm_effective_n": PROGRAM
    / "truth_continuation_v1/workspace/market_llm_effective_n_stage_c_2026_06_03/market_llm_effective_n_stage_c_report.json",
    "premium": PROGRAM / "premium_channel_v1/workspace/premium_channel_report.json",
    "router": PROGRAM / "router_rederivation_v1/workspace/conditional_router_rederivation_report.json",
    "router_balanced": PROGRAM / "router_rederivation_v1/workspace/source_balanced_router_audit.json",
    "decision_utility": PROGRAM / "decision_utility_v20/workspace/decision_utility_verdict.json",
    "anti_bias": PROGRAM / "anti_bias_collapse_v1/workspace/anti_bias_collapse_score.json",
    "f105": PROGRAM / "llm_effort_estimation/workspace/f105_effort_rescue_db_report.json",
    "science_spine": PROGRAM
    / "forecaster_skill_calibration_v1/workspace/forecasting_science_spine_audit_2026_06_04.json",
    "expert_advice": PROGRAM
    / "forecaster_skill_calibration_v1/workspace/expert_advice_router_audit_2026_06_03.json",
    "f100_source_currency": PROGRAM
    / "forecaster_skill_calibration_v1/workspace/f100_source_currency_audit_2026_06_03.json",
    "diagnostic_review": PROGRAM
    / "nurture_intervention_v1/workspace/diagnostic_review_allocation_audit_2026_06_03.json",
    "f47_external_bar": PROGRAM
    / "forecaster_skill_calibration_v1/workspace/f47_external_bar_score_2026_06_03.json",
    "f47_prospective": PROGRAM
    / "forecaster_skill_calibration_v1/workspace/f47_prospective_market_freeze_packet_2026_06_04/f47_prospective_market_freeze_score.json",
    "fred_vintage_bulk_repair": PROGRAM
    / "cutoff_validity_v1/workspace/fred_vintage_bulk_repair_2026_06_04/fred_vintage_bulk_repair.json",
    "fred_vintage_bulk_rescore": PROGRAM
    / "cutoff_validity_v1/workspace/fred_vintage_bulk_rescore_2026_06_04/fred_vintage_rescore.json",
}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def scalar(cur: sqlite3.Cursor, sql: str, params: tuple[Any, ...] = ()) -> Any:
    row = cur.execute(sql, params).fetchone()
    return row[0] if row else None


def db_snapshot(db: Path) -> dict[str, Any]:
    con = sqlite3.connect(db)
    cur = con.cursor()
    out = {
        "contracts": scalar(cur, "SELECT COUNT(*) FROM contracts"),
        "contracts_y_known": scalar(cur, "SELECT COUNT(*) FROM contracts WHERE y_known IS NOT NULL"),
        "pilot_calls": scalar(cur, "SELECT COUNT(*) FROM pilot_calls"),
        "calls_with_brier": scalar(cur, "SELECT COUNT(*) FROM pilot_calls WHERE brier IS NOT NULL"),
        "complete_five_contracts": scalar(
            cur,
            """
            WITH fams AS (
              SELECT contract_id, COUNT(DISTINCT family) AS nfam
              FROM pilot_calls
              WHERE brier IS NOT NULL AND schema_ok = 1
              GROUP BY contract_id
            )
            SELECT COUNT(*) FROM fams WHERE nfam >= 5
            """,
        ),
        "stage_b_calls": scalar(
            cur,
            "SELECT COUNT(*) FROM pilot_calls WHERE pilot_id = 'cutoff_stage_b_panel_v1'",
        ),
        "premium_calls": scalar(
            cur,
            "SELECT COUNT(*) FROM pilot_calls WHERE pilot_id IN ('premium_batch1', 'premium_crossfamily')",
        ),
        "anti_bias_calls": scalar(
            cur,
            "SELECT COUNT(*) FROM pilot_calls WHERE pilot_id = 'anti_bias_collapse_v1'",
        ),
    }
    con.close()
    return out


def build_frontier(reports: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    premium = reports["premium"].get("cross_family_standard") or {}
    base_join = reports["base_rate_join"].get("coverage") or {}
    utility = reports["decision_utility"].get("overall_lift_tally") or {}
    router = reports["router"]
    router_balanced = reports["router_balanced"]
    anti = reports["anti_bias"]
    f105 = reports["f105"]
    equal_info = reports["equal_information"]
    blend = reports["market_llm_blend"]
    effective_n = reports["market_llm_effective_n"]
    f100 = reports["f100_source_currency"]
    expert_advice = reports["expert_advice"]
    diagnostic_review = reports["diagnostic_review"]
    f47_external = reports["f47_external_bar"]
    f47_prospective = reports["f47_prospective"]
    fred_repair = reports["fred_vintage_bulk_repair"]
    fred_rescore = reports["fred_vintage_bulk_rescore"]
    fred_summary = fred_repair.get("summary") or {}
    fred_control = fred_rescore.get("control") or {}
    return [
        {
            "rank": 1,
            "angle": "source_validity_and_equal_information_baselines",
            "de_anchor_question": (
                "Are we measuring current forecasting skill, source/cutoff leakage, "
                "or absence of a same-information human/market comparison?"
            ),
            "current_evidence": {
                "stage_b_post_minus_pre_brier": 0.191098,
                "base_rate_joined_contracts": base_join.get("joined_contracts"),
                "base_rate_missing_contracts": base_join.get("missing_contracts"),
                "joined_relation_counts": base_join.get("joined_relation_counts"),
                "base_rate_matched": (
                    reports["base_rate_join"].get("repaired_effect") or {}
                ).get("base_rate_matched"),
                "equal_information_verdict": equal_info.get("verdict"),
                "market_blend_verdict": blend.get("verdict"),
                "market_effective_n_verdict": effective_n.get("verdict"),
                "fred_vintage_verdict": fred_summary.get("verdict"),
                "fred_scoreable_rows": fred_summary.get("vintage_scoreable_rows"),
                "fred_label_changes": fred_summary.get("y_two_point_changed"),
                "fred_blinded_control_vintage_delta": (
                    (fred_control.get("paired_vintage") or {}).get("mean_post_minus_pre_brier")
                ),
            },
            "next_best_truth_action": (
                "Fill or newly freeze equal-information market/human baselines on "
                "source-valid rows; for dataset-source rows, require vintage/as-of "
                "labels before testing raw LLM, calibrated LLM, market-only, and "
                "LLM+market under the same cutoff and scoring window."
            ),
            "kills_or_scopes": (
                "Scopes LLM-vs-human/market claims if same-information market-only "
                "dominates, or if source/cutoff/label-time repair removes the "
                "apparent LLM lift."
            ),
            "why_not_another_llm_panel": (
                "More model calls without a matched bar and label-time receipts "
                "mostly increase precision on an ambiguous estimand."
            ),
        },
        {
            "rank": 2,
            "angle": "dataset_source_label_time_validity",
            "de_anchor_question": (
                "Can an official data source still be an invalid forecasting benchmark "
                "because its labels are current revisions rather than as-of values?"
            ),
            "current_evidence": {
                "fred_vintage_verdict": fred_summary.get("verdict"),
                "scoreable_rows": fred_summary.get("vintage_scoreable_rows"),
                "series_api_ok": fred_summary.get("series_api_ok"),
                "two_point_label_changes": fred_summary.get("y_two_point_changed"),
                "blinded_control_current_delta": (
                    (fred_control.get("paired_current") or {}).get("mean_post_minus_pre_brier")
                ),
                "blinded_control_vintage_delta": (
                    (fred_control.get("paired_vintage") or {}).get("mean_post_minus_pre_brier")
                ),
            },
            "next_best_truth_action": (
                "Promote label-time validation into the dataset-source acquisition gate; "
                "seek ALFRED/bulk-export confirmation or a third official source before "
                "spending more calls on FRED-shaped packets."
            ),
            "kills_or_scopes": (
                "Kills current-label official-data positives when vintage/as-of labels "
                "change the outcome or erase the post-cutoff penalty."
            ),
            "why_not_another_llm_panel": (
                "The decisive variable is the answer key, not another model sample."
            ),
        },
        {
            "rank": 3,
            "angle": "applied_forecast_improvement",
            "de_anchor_question": (
                "Which externally measurable transformation improves expected score "
                "conditional on family, source, cutoff, and base-rate band?"
            ),
            "current_evidence": {
                "f100_source_currency_verdict": f100.get("verdict"),
                "confident_no_live_status": "current strongest point-probability rule, source-validity scoped",
                "f47_external_bar_verdict": f47_external.get("verdict"),
                "f47_prospective_verdict": f47_prospective.get("verdict"),
                "prompt_nurture_status": (
                    "same-model self-repair/action/review prompts demoted by "
                    "N3-N8/N10 and diagnostic-review controls"
                ),
            },
            "next_best_truth_action": (
                "Run forward, source-valid comparisons of raw probability, F100 "
                "confident-NO calibration, prospective F47 ranking once outcomes "
                "resolve, and market-only / market+LLM baselines."
            ),
            "kills_or_scopes": (
                "Scopes applied nurture if calibrated post-processing and external "
                "baselines beat same-model prompt changes."
            ),
            "why_not_another_llm_panel": (
                "The highest-yield comparison is policy-vs-policy under equal "
                "information, not another ungrounded intervention arm."
            ),
        },
        {
            "rank": 4,
            "angle": "diagnostic_error_surfaces_not_actuators",
            "de_anchor_question": (
                "Which model-emitted channels identify fragility, and when do they "
                "fail as direct probability transforms?"
            ),
            "current_evidence": {
                "premium_rows": reports["premium"].get("rows"),
                "worry_positive_families": premium.get("worry_positive_families"),
                "worry_beats_confidence_and_sham_families": premium.get(
                    "worry_beats_confidence_and_sham_families"
                ),
                "diagnostic_review_verdict": diagnostic_review.get("verdict"),
                "channel_policy_boundary": (
                    "worry/spread/self-Brier channels are evidence-readouts unless "
                    "a frozen allocation policy beats raw/confident-NO controls"
                ),
            },
            "next_best_truth_action": (
                "Use worry, spread, self-Brier, and disagreement first as triage "
                "features for external information acquisition; promote only if a "
                "frozen policy beats raw, confidence, sham-trigger, and F100 controls."
            ),
            "kills_or_scopes": (
                "Keeps Law 2 diagnostic-only if triage does not improve score or "
                "utility after review cost."
            ),
            "model_native_affordances": [
                "self-predicted error",
                "worry/tail-risk",
                "bid-ask spread",
                "self-Brier interval",
                "cross-sample disagreement",
            ],
        },
        {
            "rank": 5,
            "angle": "no_poolability_and_expert_advice_headroom",
            "de_anchor_question": (
                "Is the useful unit a model, or a contract-family-source cell?"
            ),
            "current_evidence": {
                "router_verdict": router.get("verdict"),
                "n_contracts": router.get("n_contracts"),
                "selected_candidate": router.get("selected_candidate"),
                "source_balanced_verdict": router_balanced.get("verdict"),
                "source_balanced_contracts": router_balanced.get("balanced_contracts"),
                "source_balanced_scores": (
                    router_balanced.get("source_stratified_cv") or {}
                ).get("aggregate_scores"),
                "expert_advice_verdict": expert_advice.get("verdict"),
                "oracle_headroom_status": (
                    "family × contract interaction is real, but current hand router "
                    "and expert-advice audit do not yet recover it reliably"
                ),
            },
            "next_best_truth_action": (
                "Continue router work only as a predeclared expert-advice or "
                "contextual-bandit problem with source-balanced validation, "
                "complete-five panels, and confident-NO / market controls."
            ),
            "kills_or_scopes": (
                "Keeps no-poolability as mechanism/headroom if the learned router "
                "cannot beat mean-panel, F100, and market-aware baselines."
            ),
        },
        {
            "rank": 6,
            "angle": "prompt_geometry_exception_contrastive_ranking",
            "de_anchor_question": (
                "Are LLMs better at relative orderings than absolute probabilities, "
                "and can that be converted into calibrated forecasts?"
            ),
            "current_evidence": {
                "f47_external_bar_verdict": f47_external.get("verdict"),
                "f47_prospective_verdict": f47_prospective.get("verdict"),
                "f47_resolution_state": (
                    f47_prospective.get("resolution_status") or {}
                ).get("verdict"),
                "utility_cells": utility.get("n_cells"),
            },
            "next_best_truth_action": (
                "Stop spending attention until the prospective F47 market-freeze "
                "packet has resolved outcomes; then score ranking utility, Brier, "
                "and translation against the frozen market bar."
            ),
            "kills_or_scopes": (
                "Scopes F47 to a diagnostic/pairwise phenomenon if prospective "
                "market-bar or Brier tests fail."
            ),
        },
        {
            "rank": 7,
            "angle": "carrier_bias_beyond_human_bias_labels",
            "de_anchor_question": (
                "Are human-bias labels causal, or are they proxies for raw gap, "
                "textual salience, and source familiarity?"
            ),
            "current_evidence": {
                "anti_bias_verdict": anti.get("verdict"),
                "mimic_mean_collapse": ((anti.get("class_summary") or {}).get("MIMIC") or {}).get(
                    "mean_collapse"
                ),
                "raw_gap_adjusted_mimic_coef": (
                    anti.get("raw_gap_adjusted_control") or {}
                ).get("coef_mimic_after_raw_gap_and_family"),
            },
            "next_best_truth_action": (
                "Only reopen Law 1 with raw-gap matched or randomized rows."
            ),
            "kills_or_scopes": "Kills the three-axis transfer story as causal if raw-gap controls erase it.",
        },
        {
            "rank": 8,
            "angle": "reasoning_probability_decoupling",
            "de_anchor_question": (
                "What if reasoning text is a mostly separate output channel from "
                "the probability generator?"
            ),
            "current_evidence": {
                "known_fragments": [
                    "failure text often weakly tracks Brier",
                    "stake framing moves worry more than p_success",
                    "contrastive paired elicitation is a possible exception",
                ]
            },
            "next_best_truth_action": (
                "Prefer typed probabilistic circuits or reference-class arithmetic "
                "over more prose-only rationale prompts."
            ),
            "kills_or_scopes": "Kills rationale-improvement stories if numeric revision does not move calibration.",
        },
        {
            "rank": 9,
            "angle": "self_calibration_on_effort_and_resource_forecasts",
            "de_anchor_question": (
                "Can models forecast their own computational/resource needs better "
                "than they forecast world events?"
            ),
            "current_evidence": {
                "rows": f105.get("rows"),
                "status": (f105.get("sibling_paper_status") or {}).get("verdict")
                if isinstance(f105.get("sibling_paper_status"), dict)
                else f105.get("sibling_paper_status"),
            },
            "next_best_truth_action": "Run hidden objective-effort tasks with DB logging.",
            "kills_or_scopes": "Kills F105 sibling if hidden objective outcomes erase the signal.",
        },
        {
            "rank": 10,
            "angle": "human_crowd_comparison",
            "de_anchor_question": (
                "Do not ask whether LLMs beat humans until the same question, same "
                "timing, same information, and same scoring baseline exists."
            ),
            "current_evidence": {
                "equal_information_verdict": equal_info.get("verdict"),
                "market_blend_verdict": blend.get("verdict"),
                "market_effective_n_verdict": effective_n.get("verdict"),
                "local_status": "same-information broad bar remains incomplete",
            },
            "next_best_truth_action": (
                "Treat public LLM-vs-human and LLM+human claims as blocked until "
                "matched market/human rows exist with comparable effective N."
            ),
            "kills_or_scopes": "Kills public superiority claims if equal-access crowd baselines win.",
        },
    ]


def build(db: Path) -> dict[str, Any]:
    reports = {name: read_json(path) for name, path in REPORT_PATHS.items()}
    frontier = build_frontier(reports)
    return {
        "schema": "gp245-max-truth-frontier-v1",
        "db_snapshot": db_snapshot(db),
        "standing_questions": [
            "What observation would most change what we believe next?",
            "What loved explanation would this observation kill?",
            "What capability surface are we ignoring because it does not look human?",
            "What are we measuring because it is easy rather than because it is decisive?",
        ],
        "current_next_best": frontier[0],
        "frontier": frontier,
        "de_anchor_rules": [
            "Do not treat human-bias transfer as the whole program.",
            "Do not infer deployment policy from diagnostic correlation.",
            "Do not add model calls when the live confound is source/cutoff or a missing same-information bar.",
            "Do not use current-label dataset-source rows as policy evidence without vintage/as-of receipts.",
            "Do not pool across source, family, or channel when prior reports show sign instability.",
            "Do not spend new intervention budget on same-model self-repair prompts unless the construct differs from N3-N8/N10.",
            "Treat F100 as the current applied probability rule, F47 as a prospective ranking hypothesis, and worry as triage until policy evidence changes that.",
            "Promote a law only when the same artifact names its falsifier.",
        ],
    }


def render_md(result: dict[str, Any]) -> str:
    lines = [
        "# GP-245 Maximal-Truth Frontier",
        "",
        "Purpose: keep the forecasting program oriented toward the next observation",
        "that would most change belief, including model-native capability surfaces",
        "that do not look like human forecasting habits.",
        "",
        "## Standing Questions",
        "",
    ]
    for q in result["standing_questions"]:
        lines.append(f"- {q}")
    lines.extend(["", "## Current Next Best", ""])
    c = result["current_next_best"]
    lines.extend(
        [
            f"- Angle: `{c['angle']}`",
            f"- De-anchor question: {c['de_anchor_question']}",
            f"- Next action: {c['next_best_truth_action']}",
            f"- Kill/scope condition: {c['kills_or_scopes']}",
            "",
            "## Frontier",
            "",
        ]
    )
    for item in result["frontier"]:
        lines.extend(
            [
                f"### {item['rank']}. {item['angle']}",
                f"- De-anchor question: {item['de_anchor_question']}",
                f"- Next best truth action: {item['next_best_truth_action']}",
                f"- Kills/scopes: {item['kills_or_scopes']}",
                "- Current evidence:",
                "```json",
                json.dumps(item.get("current_evidence", {}), indent=2, sort_keys=True),
                "```",
                "",
            ]
        )
    lines.extend(["## De-Anchor Rules", ""])
    for rule in result["de_anchor_rules"]:
        lines.append(f"- {rule}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = build(args.db)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "max_truth_frontier_report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "max_truth_frontier_report.md").write_text(
        render_md(result),
        encoding="utf-8",
    )
    print(f"wrote {args.out_dir / 'max_truth_frontier_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
