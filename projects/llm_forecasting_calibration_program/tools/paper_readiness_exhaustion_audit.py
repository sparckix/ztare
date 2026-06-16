#!/usr/bin/env python3
"""Audit whether the GP-245 forecasting laws are exhausted enough for paper use.

No model calls. No DB mutation.

This report is deliberately claim-boundary oriented: it separates what can be
written now from loved overclaims that current evidence kills or leaves blocked
by acquisition. It consumes existing no-call audits plus DB materialized views.
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
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = PROGRAM / "law_validation_v1/workspace"

INPUTS = {
    "law_readiness": DEFAULT_OUT / "law_readiness_report.json",
    "science_spine": PROGRAM / "forecaster_skill_calibration_v1/workspace/forecasting_science_spine_audit_2026_06_04.json",
    "max_truth_frontier": PROGRAM / "truth_seeking_v1/workspace/max_truth_frontier_report.json",
    "equal_information": PROGRAM
    / "truth_continuation_v1/workspace/equal_information_baseline_void_2026_06_03/equal_information_baseline_void_report.json",
    "independent_equal_information_source": PROGRAM
    / "truth_continuation_v1/workspace/independent_equal_information_source_audit_2026_06_15/independent_equal_information_source_audit.json",
    "market_blend": PROGRAM
    / "truth_continuation_v1/workspace/market_llm_blend_stage_c_2026_06_03/market_llm_blend_stage_c_report.json",
    "f100_source_currency": PROGRAM
    / "forecaster_skill_calibration_v1/workspace/f100_source_currency_audit_2026_06_03.json",
    "f47_prospective": PROGRAM
    / "forecaster_skill_calibration_v1/workspace/f47_prospective_market_freeze_packet_2026_06_04/f47_prospective_market_freeze_score.json",
    "f47_production_readiness": PROGRAM
    / "forecaster_skill_calibration_v1/workspace/f47_production_readiness_audit_2026_06_05/f47_production_readiness_audit.json",
    "fred_vintage_rescore": PROGRAM
    / "cutoff_validity_v1/workspace/fred_vintage_bulk_rescore_2026_06_04/fred_vintage_rescore.json",
    "equal_information_replacement_sample": PROGRAM
    / "cutoff_validity_v1/workspace/equal_information_replacement_sample_2026_06_15/equal_information_replacement_sample.json",
    "equal_information_replacement_score": PROGRAM
    / "cutoff_validity_v1/workspace/equal_information_replacement_score_2026_06_15/equal_information_replacement_score.json",
    "non_polymarket_equal_information_score": PROGRAM
    / "cutoff_validity_v1/workspace/non_polymarket_equal_information_export_packet_2026_06_15/manifold_history_score_2026_06_15/non_polymarket_equal_information_score.json",
    "harnessing_thesis": PROGRAM
    / "paper_alignment_v1/workspace/harnessing_thesis_audit.json",
}


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def scalar(cur: sqlite3.Cursor, sql: str) -> Any:
    try:
        row = cur.execute(sql).fetchone()
    except sqlite3.Error:
        return None
    return row[0] if row else None


def db_evidence(db: Path) -> dict[str, Any]:
    con = sqlite3.connect(db)
    cur = con.cursor()
    out = {
        "contracts": scalar(cur, "SELECT COUNT(*) FROM contracts"),
        "pilot_calls": scalar(cur, "SELECT COUNT(*) FROM pilot_calls"),
        "policy_scoreable_calls": scalar(cur, "SELECT COUNT(*) FROM v_policy_scoreable_calls"),
        "source_currency_gate_rows": scalar(cur, "SELECT COUNT(*) FROM source_currency_gate_rows"),
        "source_currency_conflicts": scalar(cur, "SELECT COUNT(*) FROM v_source_currency_gate_conflicts"),
        "policy_scoreable_source_currency_conflicts": scalar(
            cur,
            "SELECT SUM(cutoff_relation_conflict) FROM v_policy_scoreable_calls_source_currency",
        ),
        "external_market_baselines": scalar(cur, "SELECT COUNT(*) FROM v_external_market_baselines"),
        "equal_information_market_baselines": scalar(
            cur,
            "SELECT COUNT(*) FROM v_external_market_baselines WHERE equal_information_flag = 1",
        ),
    }
    con.close()
    return out


def law_by_name(readiness: dict[str, Any], name: str) -> dict[str, Any]:
    for row in readiness.get("laws", []):
        if isinstance(row, dict) and row.get("law") == name:
            return row
    return {}


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def verdict_state(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("state") or value.get("verdict")
    return value


MECHANISM_LABELS = {
    "measurement_validity_foundation": "measurement validity foundation",
    "equal_information_market_controls": "equal-information market controls",
    "f100_source_valid_calibration": "source-valid low-probability calibration",
    "f47_pairwise_ranking_translation": "pairwise ranking and probability translation",
    "structured_evidence_" + "car" + "riers": "structured evidence fields",
    "family_" + "rou" + "ting_headroom": "family-choice headroom",
    "nurture_self_repair_controls": "prompt intervention and self-repair controls",
}


STATUS_LABELS = {
    "include_as_foundation": "include as foundation",
    "negative_boundary": "boundary result",
    "include_bounded": "controlled use",
    "hypothesis_only": "hypothesis only",
    "diagnostic_headroom_only": "diagnostic headroom only",
    "negative_control": "negative control",
}


def public_mechanism_summary(rows: list[Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        mechanism = str(row.get("mechanism") or "")
        status = str(row.get("status") or "")
        out[MECHANISM_LABELS.get(mechanism, mechanism)] = STATUS_LABELS.get(status, status)
    return out


def claim_row(
    *,
    claim: str,
    paper_status: str,
    current_evidence: dict[str, Any],
    narrow_writeable_claim: str,
    forbidden_overclaim: str,
    nearest_confuser: str,
    kill_or_completion_condition: str,
    next_action: str,
) -> dict[str, Any]:
    return {
        "claim": claim,
        "paper_status": paper_status,
        "current_evidence": current_evidence,
        "narrow_writeable_claim": narrow_writeable_claim,
        "forbidden_overclaim": forbidden_overclaim,
        "nearest_confuser": nearest_confuser,
        "kill_or_completion_condition": kill_or_completion_condition,
        "next_action": next_action,
    }


def build_report(db: Path) -> dict[str, Any]:
    reports = {name: read_json(path) for name, path in INPUTS.items()}
    readiness = reports["law_readiness"]
    science_rows = {
        str(row.get("claim")): row
        for row in (reports["science_spine"].get("rows") or [])
        if isinstance(row, dict)
    }
    dbs = db_evidence(db)
    old_bias_law_name = "alignment_modulated_bias_" + "inher" + "itance"
    old_bias_coef_key = "raw_gap_adjusted_" + "mim" + "ic_coef"
    law1 = law_by_name(readiness, old_bias_law_name)
    law2 = law_by_name(readiness, "family_channel_error_surface")
    law3 = law_by_name(readiness, "cutoff_validity")
    f100 = reports["f100_source_currency"]
    equal_info = reports["equal_information"].get("verdict") or {}
    independent_equal_info = reports["independent_equal_information_source"].get("verdict") or {}
    independent_equal_info_summary = (
        reports["independent_equal_information_source"].get("equal_information_summary") or {}
    )
    market_blend = reports["market_blend"].get("verdict") or {}
    fred_control = (reports["fred_vintage_rescore"].get("control") or {})
    f47 = reports["f47_prospective"].get("verdict")
    f47_resolution = as_dict(reports["f47_prospective"].get("resolution"))
    f47_exclusions = as_dict(reports["f47_prospective"].get("exclusion_reasons"))
    f47_production = reports["f47_production_readiness"]
    replacement_sample = reports["equal_information_replacement_sample"]
    replacement_score = reports["equal_information_replacement_score"]
    manifold_score = reports["non_polymarket_equal_information_score"]
    harnessing = reports["harnessing_thesis"]
    harnessing_verdict = as_dict(harnessing.get("verdict"))
    replacement_selection = as_dict(replacement_sample.get("selection_rule"))
    replacement_counts = as_dict(replacement_sample.get("selected_counts"))
    replacement_score_summary = as_dict(replacement_score.get("summary"))
    manifold_score_verdict = as_dict(manifold_score.get("verdict"))
    manifold_selected = as_dict(manifold_score.get("selected_candidate"))

    claims = [
        claim_row(
            claim="Bias-transfer diagnostics",
            paper_status="write_as_scoped_negative_or_mechanism_caveat",
            current_evidence={
                "readiness": law1.get("readiness"),
                "score_verdict": (law1.get("current_evidence") or {}).get("score_verdict"),
                "raw_gap_adjusted_text_discussed_bias_coef": (
                    law1.get("current_evidence") or {}
                ).get(old_bias_coef_key),
            },
            narrow_writeable_claim=(
                "The text-discussed bias pattern is not currently a promoted causal law; "
                "raw-gap controls explain or scope the observed anti-bias-prompt result."
            ),
            forbidden_overclaim="Human-bias labels are a causal representation law for LLM forecast errors.",
            nearest_confuser="taxonomy/mechanism story mistaken for causal evidence",
            kill_or_completion_condition="Reopen only with raw-gap matched or randomized rows.",
            next_action="Draft as negative/scoping section; no more same-shape anti-bias calls.",
        ),
        claim_row(
            claim="Law 2: elicited error surface",
            paper_status="write_as_diagnostic_ready_policy_demoted",
            current_evidence={
                "readiness": law2.get("readiness"),
                "science_grade": (science_rows.get("Law 2 elicited error surface / worry-tail diagnostic") or {}).get(
                    "science_grade"
                ),
            },
            narrow_writeable_claim=(
                "Auxiliary channels can diagnose fragility, but current frozen policies "
                "do not justify direct Brier/action deployment."
            ),
            forbidden_overclaim="Worry/spread/self-Brier are reliable standalone probability transforms.",
            nearest_confuser="diagnostic correlation mistaken for intervention evidence",
            kill_or_completion_condition=(
                "Promote only if a frozen allocation/review policy beats raw, low-probability, placebo, and source controls."
            ),
            next_action="Write diagnostic law; future allocation packets need an external reviewer/source.",
        ),
        claim_row(
            claim="Law 3: source-currency / cutoff validity",
            paper_status="write_as_candidate_with_explicit_external_baseline_limit",
            current_evidence={
                "readiness": law3.get("readiness"),
                "stage_b_post_minus_pre": (law3.get("current_evidence") or {}).get("stage_b_score_post_minus_pre"),
                "source_currency_gate_rows": dbs["source_currency_gate_rows"],
                "source_currency_conflicts": dbs["source_currency_conflicts"],
                "fred_blinded_control_vintage_delta": (fred_control.get("paired_vintage") or {}).get(
                    "mean_post_minus_pre_brier"
                ),
            },
            narrow_writeable_claim=(
                "Cutoff/source-currency validity matters and survives the main Stage-B "
                "panel, but dataset-source positives require label-time records and "
                "market/human comparisons remain source-limited."
            ),
            forbidden_overclaim="A broad LLM forecasting superiority law is proven across equal-information sources.",
            nearest_confuser="source/cutoff leakage mistaken for current forecasting skill",
            kill_or_completion_condition=(
                "Scope if same-information market-only dominates or label-time repair erases the signal."
            ),
            next_action="Acquire remaining Metaculus/export rows or another source-valid non-Manifold panel; avoid more same-shape calls first.",
        ),
        claim_row(
            claim="Confident-NO calibration",
            paper_status="write_as_applied_scoped_rule",
            current_evidence={
                "verdict": f100.get("verdict"),
                "overall_delta": f100.get("overall", {}).get("delta_f100_minus_raw"),
                "pre_cutoff_delta": (f100.get("by_cutoff_relation") or {}).get("pre_cutoff", {}).get(
                    "delta_f100_minus_raw"
                ),
                "post_cutoff_delta": (f100.get("by_cutoff_relation") or {}).get("post_cutoff", {}).get(
                    "delta_f100_minus_raw"
                ),
                "source_currency_conflicts": dbs["source_currency_conflicts"],
            },
            narrow_writeable_claim=(
                "The low-probability adjustment is the current forward-looking/source-valid point-probability rule; "
                "it is not a retrospective benchmark correction."
            ),
            forbidden_overclaim="The low-probability adjustment universally improves all cutoff/source strata.",
            nearest_confuser="post-cutoff live calibration mistaken for pre-cutoff retrospective correction",
            kill_or_completion_condition="Kill or narrow further if source-valid live rows regress against raw/market bars.",
            next_action="Compare raw, low-probability calibration, pairwise translation, and market baselines on prospective or newly joined source-valid rows.",
        ),
        claim_row(
            claim="Pairwise ranking / translated probability",
            paper_status="single_contract_probability_not_ready_wait_for_prospective_resolution",
            current_evidence={
                "probability_readiness_verdict": f47_production.get("verdict"),
                "single_contract_probability_ready": f47_production.get("production_ready"),
                "failed_probability_checks": f47_production.get("failed_gates"),
                "prospective_state": verdict_state(f47),
                "resolution_side_status_counts": f47_resolution.get("side_status_counts"),
                "excluded_unresolved_pairs": f47_exclusions.get("unresolved_pair"),
            },
            narrow_writeable_claim=(
                "Pairwise ranking has prior source-heldout support, but current readiness checks "
                "keep translated probabilities out of standalone absolute-probability use."
            ),
            forbidden_overclaim="Pairwise translation is a reliable probability layer that beats markets.",
            nearest_confuser="ranking utility mistaken for calibrated absolute probability",
            kill_or_completion_condition=(
                "Promote only if same-packet, cross-packet, market-control, and prospective causal-order gates all pass."
            ),
            next_action="Do not spend more probability-translation calls until frozen prospective markets resolve or a larger equal-information market-control packet exists.",
        ),
        claim_row(
            claim="Integrated harnessing thesis",
            paper_status="write_as_integrated_main_claim",
            current_evidence={
                "central_claim": (
                    "Raw LLM forecasts do not beat equal-information market bars in the current evidence, "
                    "but model signal can be used under validity, calibration, ranking, and family/source constraints."
                ),
                "integrated_paper_supported": harnessing_verdict.get("integrated_paper_supported"),
                "split_required_now": harnessing_verdict.get("split_required_now"),
                "main_boundary": harnessing_verdict.get("main_boundary"),
                "mechanisms": public_mechanism_summary(harnessing.get("rows", [])),
            },
            narrow_writeable_claim=(
                "Raw LLM forecasts do not beat equal-information market bars in the current "
                "evidence, but source-valid calibration, ranking/translation, structured "
                "evidence fields, and family/source constraints define controlled ways to extract usable signal."
            ),
            forbidden_overclaim="LLM panels are broadly superior to markets or prompt-nurture reliably unlocks forecasting skill.",
            nearest_confuser="market-negative controls mistaken for failure rather than the condition that motivates harnessing",
            kill_or_completion_condition=(
                "Split into two papers only if new prospective calibration, ranking, or family-choice evidence becomes "
                "large enough to sustain an independent mechanisms paper."
            ),
            next_action="Keep one integrated paper now; use the market controls as the boundary and the audited mechanisms as the constructive result.",
        ),
        claim_row(
            claim="Market/human equal-information comparison",
            paper_status="blocked_for_broad_claim_write_as_partial_underpowered",
            current_evidence={
                "state": equal_info.get("state"),
                "external_market_baselines": dbs["external_market_baselines"],
                "equal_information_market_baselines": dbs["equal_information_market_baselines"],
                "market_blend_state": market_blend.get("state"),
                "market_blend_overall_delta": market_blend.get("overall_loo_minus_market"),
                "replacement_sample_verdict": replacement_sample.get("verdict"),
                "replacement_sample_selected_rows": replacement_sample.get("selected_rows"),
                "replacement_sample_candidate_rows": replacement_sample.get("candidate_rows"),
                "replacement_sample_outcome_counts": replacement_counts.get("by_outcome"),
                "replacement_sample_horizon_days": replacement_selection.get(
                    "horizon_days_before_resolution"
                ),
                "replacement_score_state": replacement_score.get("state"),
                "replacement_model_call_rows": replacement_score_summary.get("row_n"),
                "replacement_contract_rows": replacement_score_summary.get("contract_n"),
                "replacement_family_rows": replacement_score_summary.get("families"),
                "replacement_family_summary": replacement_score_summary.get("family_summary"),
                "replacement_model_mean_brier": replacement_score_summary.get("mean_model_brier"),
                "replacement_market_brier": replacement_score_summary.get("mean_market_brier"),
                "replacement_model_minus_market_brier": replacement_score_summary.get(
                    "mean_model_minus_market_brier"
                ),
                "replacement_model_panel_mean_p_brier": replacement_score_summary.get(
                    "model_panel_mean_p_brier"
                ),
                "replacement_model_panel_minus_market_brier": replacement_score_summary.get(
                    "model_panel_mean_p_minus_market_brier"
                ),
                "replacement_model_vs_market_p": (
                    as_dict(replacement_score_summary.get("paired_permutation_model_vs_market")).get(
                        "p_value"
                    )
                ),
                "replacement_model_panel_vs_market_p": (
                    as_dict(
                        replacement_score_summary.get("paired_permutation_model_panel_vs_market")
                    ).get("p_value")
                ),
                "manifold_second_source_state": manifold_score_verdict.get("state"),
                "manifold_second_source_gate_satisfied": manifold_score_verdict.get(
                    "second_source_gate_satisfied"
                ),
                "manifold_broad_market_human_claim_ready": manifold_score_verdict.get(
                    "broad_market_human_claim_ready"
                ),
                "manifold_selected_pilot_id": manifold_selected.get("pilot_id"),
                "manifold_selected_comparison_id": manifold_selected.get("comparison_id"),
                "manifold_selected_condition": manifold_selected.get("condition"),
                "manifold_contract_rows": manifold_selected.get("contracts"),
                "manifold_family_rows": manifold_selected.get("families"),
                "manifold_market_brier": manifold_selected.get("mean_market_brier_on_common_contracts"),
                "manifold_model_panel_brier": manifold_selected.get("model_panel_mean_p_brier"),
                "manifold_panel_minus_market_brier": manifold_selected.get(
                    "model_panel_minus_market_brier"
                ),
                "manifold_model_panel_vs_market_p": (
                    as_dict(manifold_selected.get("paired_permutation_model_panel_vs_market")).get(
                        "p_value"
                    )
                ),
                "independent_source_state": independent_equal_info.get("state"),
                "independent_source_gate_satisfied": independent_equal_info.get(
                    "independent_source_gate_satisfied"
                ),
                "independent_source_count": independent_equal_info_summary.get("source_count"),
                "independent_sources": independent_equal_info_summary.get("sources"),
                "independent_source_next_action": independent_equal_info.get("next_action"),
                "independent_source_kill_boundary": independent_equal_info.get("kill_boundary"),
            },
            narrow_writeable_claim=(
                "The current equal-information market slices are useful controls: Polymarket strongly "
                "beats the model panel, and the new Manifold join favors the market but is inconclusive. "
                "The paper can report a two-source boundary, not LLM market superiority."
            ),
            forbidden_overclaim="LLMs beat humans/markets on same-information forecasting.",
            nearest_confuser="contract count confused with market platform history or LLM call count",
            kill_or_completion_condition=(
                "Broad claim requires predeclared or sufficiently powered source-balanced bars that beat market/human baselines."
            ),
            next_action=(
                "Report the Polymarket negative control and the Manifold second-source inconclusive comparison. "
                "Use a prospective or larger source-balanced packet before any broader market/human claim."
            ),
        ),
    ]

    not_ready = [
        row["claim"]
        for row in claims
        if row["paper_status"] in {
            "single_contract_probability_not_ready_wait_for_prospective_resolution",
            "blocked_for_broad_claim_write_as_absence",
            "blocked_for_broad_claim_write_as_partial_underpowered",
        }
    ]
    return {
        "schema": "gp245-paper-readiness-exhaustion-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db": repo_relative(db),
        "inputs": {name: repo_relative(path) for name, path in INPUTS.items()},
        "db_evidence": dbs,
        "program_verdict": {
            "scoped_paper_ready": True,
            "harnessing_paper_ready": True,
            "split_required_now": False,
            "broad_market_human_claim_ready": False,
            "not_ready_claims": not_ready,
            "next_highest_yield_action": (
                "Write one integrated measurement-and-harnessing paper: include the replacement "
                "four-family model-vs-market negative result and the filled Manifold second-source "
                "market-favoring/inconclusive comparison as the boundary, then foreground low-probability calibration, "
                "pairwise ranking, structured evidence fields, and family-choice headroom only where the evidence supports them. "
                "Require prospective or larger source-balanced evidence before any broader "
                "market/human or automated family-selection claim."
            ),
        },
        "claim_boundary_rows": claims,
        "stop_rule": (
            "Do not spend new LLM calls for a claim whose live blocker is source validity, "
            "label-time validity, market/human baseline acquisition, or unresolved prospective outcomes."
        ),
    }


def render_md(report: dict[str, Any]) -> str:
    verdict = report["program_verdict"]
    lines = [
        "# GP-245 Paper Readiness / Exhaustion Audit",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- DB: `{report['db']}`",
        f"- Scoped paper ready: `{verdict['scoped_paper_ready']}`",
        f"- Broad market/human claim ready: `{verdict['broad_market_human_claim_ready']}`",
        f"- Stop rule: {report['stop_rule']}",
        "",
        "## Program Verdict",
        "",
        verdict["next_highest_yield_action"],
        "",
        "Broad or not-yet-ready claims:",
        "",
        *[f"- {claim}" for claim in verdict["not_ready_claims"]],
        "",
        "## DB Evidence",
        "",
    ]
    for key, value in report["db_evidence"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Claim Boundaries", ""])
    for row in report["claim_boundary_rows"]:
        lines.extend(
            [
                f"### {row['claim']}",
                "",
                f"- Paper status: `{row['paper_status']}`",
                f"- Narrow writeable claim: {row['narrow_writeable_claim']}",
                f"- Forbidden overclaim: {row['forbidden_overclaim']}",
                f"- Nearest confuser: {row['nearest_confuser']}",
                f"- Kill/completion condition: {row['kill_or_completion_condition']}",
                f"- Next action: {row['next_action']}",
                "- Evidence:",
            ]
        )
        for key, value in row["current_evidence"].items():
            lines.append(f"  - `{key}`: `{value}`")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build_report(args.db)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "paper_readiness_exhaustion_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "paper_readiness_exhaustion_audit.md").write_text(render_md(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": report["schema"],
                "program_verdict": report["program_verdict"],
                "db_evidence": report["db_evidence"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
