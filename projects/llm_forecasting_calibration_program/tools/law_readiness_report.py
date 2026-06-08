#!/usr/bin/env python3
"""GP-245 law-readiness report.

This is a no-call, no-mutation status report for the forecasting paper spine.
It answers: which candidate laws are currently promotable, which are blocked,
and what exact next test would kill or upgrade them.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
PROGRAM_ROOT = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_OUT = PROGRAM_ROOT / "law_validation_v1/workspace"

PREMIUM_REPORT = PROGRAM_ROOT / "premium_channel_v1/workspace/premium_channel_report.json"
CHANNEL_HOLDOUT_REPORT = PROGRAM_ROOT / "channel_holdout_v1/workspace/channel_holdout_law_report.json"
CHANNEL_POLICY_CELL_REPORT = PROGRAM_ROOT / "channel_policy_cell_v1/workspace/channel_policy_cell_validation.json"
CUTOFF_AUDIT_REPORT = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_metadata_audit.json"
CUTOFF_CANDIDATE_REPORT = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_candidate_report.json"
CUTOFF_STAGE_B_REPORT = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_stage_b_balance_report.json"
CUTOFF_ACQUISITION_REPORT = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_acquisition_manifest_report.json"
CUTOFF_MANIFOLD_ACQUISITION_REPORT = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_manifold_acquisition_report.json"
CUTOFF_CANDIDATE_REVIEW_REPORT = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_candidate_review_report.json"
CUTOFF_CANDIDATE_INGEST_PREVIEW = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_candidate_ingest_preview.json"
CUTOFF_POLYMARKET_REVIEW_REPORT = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_polymarket_candidate_review_report.json"
CUTOFF_POLYMARKET_EVENT_CAP_REPORT = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_polymarket_event_family_cap_report.json"
CUTOFF_POLYMARKET_PROVENANCE_PACKET = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_polymarket_manual_provenance_packet.json"
CUTOFF_POLYMARKET_DECISION_PREVIEW = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_polymarket_provenance_decision_preview.json"
CUTOFF_GENERAL_SOURCE_CEC_PACKET = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_general_source_cec_packet.json"
CUTOFF_STAGE_B_FREEZE_REPORT = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_stage_b_freeze_report.json"
CUTOFF_STAGE_B_SCORE_REPORT = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_stage_b_score_report.json"
CUTOFF_BASE_RATE_JOIN_REPORT = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_stage_c_base_rate_join_report.json"
CUTOFF_SECOND_SOURCE_POLYMARKET_GEMINI_SCORE = (
    PROGRAM_ROOT
    / "cutoff_validity_v1/workspace/cutoff_second_source_freeze_probe_2026_06_03/"
    / "cutoff_second_source_polymarket_gemini_score.json"
)
CUTOFF_SECOND_SOURCE_POLYMARKET_DEEPSEEK_SCORE = (
    PROGRAM_ROOT
    / "cutoff_validity_v1/workspace/cutoff_second_source_freeze_probe_deepseek_2026_06_03/"
    / "cutoff_second_source_polymarket_deepseek_score.json"
)
CUTOFF_SECOND_SOURCE_POLYMARKET_BASE_RATE_AVAILABILITY = (
    PROGRAM_ROOT
    / "cutoff_validity_v1/workspace/cutoff_second_source_polymarket_base_rate_availability_2026_06_03/"
    / "cutoff_second_source_polymarket_base_rate_availability.json"
)
ANTI_BIAS_SLATE = PROGRAM_ROOT / "anti_bias_collapse_v1/workspace/anti_bias_collapse_slate.jsonl"
ANTI_BIAS_SMOKE_SLATE = PROGRAM_ROOT / "anti_bias_collapse_v1/workspace/anti_bias_collapse_smoke_slate.jsonl"
ANTI_BIAS_DISPATCH = PROGRAM_ROOT / "anti_bias_collapse_v1/workspace/anti_bias_collapse_dispatch_packet.json"
ANTI_BIAS_SCORE = PROGRAM_ROOT / "anti_bias_collapse_v1/workspace/anti_bias_collapse_score.json"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def scalar(cur: sqlite3.Cursor, sql: str, params: tuple[Any, ...] = ()) -> Any:
    row = cur.execute(sql, params).fetchone()
    return row[0] if row else None


def db_snapshot(db: Path) -> dict[str, Any]:
    con = sqlite3.connect(db)
    cur = con.cursor()
    out = {
        "contracts": scalar(cur, "SELECT COUNT(*) FROM contracts"),
        "pilot_runs": scalar(cur, "SELECT COUNT(*) FROM pilot_runs"),
        "pilot_calls": scalar(cur, "SELECT COUNT(*) FROM pilot_calls"),
        "contracts_y_known": scalar(cur, "SELECT COUNT(*) FROM contracts WHERE y_known IS NOT NULL"),
        "calls_with_brier": scalar(cur, "SELECT COUNT(*) FROM pilot_calls WHERE brier IS NOT NULL"),
        "anti_bias_collapse_calls": scalar(
            cur,
            "SELECT COUNT(*) FROM pilot_calls WHERE pilot_id = 'anti_bias_collapse_v1'",
        ),
        "anti_bias_collapse_runs": scalar(
            cur,
            "SELECT COUNT(*) FROM pilot_runs WHERE pilot_id = 'anti_bias_collapse_v1'",
        ),
        "v26_contracts": scalar(
            cur,
            "SELECT COUNT(*) FROM contracts WHERE source_corpus = 'corpus_v26_diversification_2026_05_29'",
        ),
        "v26_resolved": scalar(
            cur,
            """
            SELECT COUNT(*) FROM contracts
            WHERE source_corpus = 'corpus_v26_diversification_2026_05_29'
              AND y_known IS NOT NULL
            """,
        ),
        "premium_resolved_contracts": scalar(
            cur,
            """
            SELECT COUNT(*) FROM contracts
            WHERE source = 'premium_public_clean'
              AND y_known IS NOT NULL
            """,
        ),
        "premium_with_cutoff_flag": scalar(
            cur,
            """
            SELECT COUNT(*) FROM contracts
            WHERE source = 'premium_public_clean'
              AND y_known IS NOT NULL
              AND post_training_cutoff IS NOT NULL
            """,
        ),
        "polymarket_reviewed_cutoff_contracts": scalar(
            cur,
            """
            SELECT COUNT(*) FROM contracts
            WHERE source_corpus = 'law3_cutoff_acquisition_polymarket_public_clob_reviewed_2026_06_02'
            """,
        ),
    }
    con.close()
    return out


def law1_status(
    db: dict[str, Any],
    slate_rows: int,
    smoke_slate_rows: int,
    dispatch: dict[str, Any],
    score: dict[str, Any],
) -> dict[str, Any]:
    calls = int(db.get("anti_bias_collapse_calls") or 0)
    score_verdict = score.get("verdict")
    readiness = "not_paper_ready"
    dispatch_ready = bool(dispatch.get("ready_for_dispatch"))
    dispatch_queue_rows = (dispatch.get("dispatch_queue_summary") or {}).get("row_count")
    missing_for_smoke = dispatch.get("missing_for_minimal_smoke") or {}
    if calls and score_verdict and score_verdict != "not_run":
        status = f"score_report_{score_verdict}"
        if str(score_verdict).startswith("promote_"):
            readiness = "paper_ready_positive_mechanism"
            bottleneck = "paper_writeup"
            next_step = "Write Law 1 as a positive mechanism result with its controls and limits."
        elif "kill" in str(score_verdict) or "scope" in str(score_verdict):
            readiness = "negative_result_ready_for_scoped_section"
            bottleneck = "paper_writeup"
            next_step = (
                "Write Law 1 as a negative/scoping result: MIMIC mean collapse "
                "does not survive label-shuffle and raw-gap-adjusted controls."
            )
        else:
            bottleneck = "law_verdict_review"
            next_step = "Review anti-bias-collapse score report and update Law 1 claim status."
    elif calls:
        status = "executed_needs_scored_report"
        bottleneck = "collapse_metric_report"
        next_step = "Score frame-gap collapse by class/family and run label-shuffle negative control."
    elif smoke_slate_rows and dispatch_ready:
        status = "minimal_smoke_dispatch_ready_not_executed"
        bottleneck = "model_calls_and_db_ingest"
        next_step = (
            "Fire the 180-row anti-bias-collapse dispatch queue, rerun the "
            "dispatch packet to validate receipt coverage, ingest into "
            "pilot_calls, then score collapse before the full 384-call panel."
        )
    elif smoke_slate_rows:
        status = "minimal_smoke_slate_ready_dispatch_packet_missing"
        bottleneck = "dispatch_packet"
        next_step = (
            "Run projects/llm_forecasting_calibration_program/tools/"
            "anti_bias_collapse_dispatch_packet.py before model calls."
        )
    elif slate_rows:
        status = "ready_to_run_not_executed"
        bottleneck = "model_calls_and_db_ingest"
        next_step = "Fire the constrained anti-bias-collapse slate, ingest into pilot_calls, then score collapse."
    else:
        status = "protocol_without_slate"
        bottleneck = "candidate_supply"
        next_step = "Regenerate the anti-bias-collapse slate before any call dispatch."
    return {
        "law": "alignment_modulated_bias_inheritance",
        "readiness": readiness,
        "status": status,
        "bottleneck": bottleneck,
        "current_evidence": {
            "slate_rows": slate_rows,
            "minimal_smoke_rows": smoke_slate_rows,
            "minimal_smoke_calls_if_3_families": smoke_slate_rows * 3 if smoke_slate_rows else 0,
            "dispatch_ready": dispatch_ready,
            "dispatch_queue_rows": dispatch_queue_rows,
            "missing_for_minimal_smoke": missing_for_smoke,
            "pilot_calls": calls,
            "score_verdict": score_verdict,
            "collapse_pairs": score.get("collapse_pairs"),
            "mimic_mean_collapse": ((score.get("class_summary") or {}).get("MIMIC") or {}).get("mean_collapse"),
            "inherit_mean_collapse": ((score.get("class_summary") or {}).get("INHERIT_CONTROL") or {}).get("mean_collapse"),
            "class_shuffle_p": (score.get("class_shuffle_control") or {}).get("p_value"),
            "raw_gap_adjusted_mimic_coef": (score.get("raw_gap_adjusted_control") or {}).get("coef_mimic_after_raw_gap_and_family"),
            "raw_gap_adjusted_p": (score.get("raw_gap_adjusted_control") or {}).get("p_value"),
        },
        "next_eigenquestion": (
            "Does explicit anti-bias correction collapse MIMIC rows more than "
            "INHERIT controls after controlling for raw frame-gap size?"
        ),
        "next_step": next_step,
        "kill_condition": (
            "MIMIC does not differentially collapse, collapse is explained by "
            "raw gap size, or family order does not track F107 alignment damping."
        ),
    }


def policy_candidates(channel_report: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for group in channel_report.get("groups", []):
        group_name = group.get("group")
        for row in group.get("policy_candidate_cells", []):
            item = dict(row)
            item["group"] = group_name
            out.append(item)
    return out


def law2_status(
    premium: dict[str, Any],
    channel_holdout: dict[str, Any],
    policy_cell: dict[str, Any],
    db: dict[str, Any],
) -> dict[str, Any]:
    standard = premium.get("cross_family_standard", {})
    candidates = policy_candidates(channel_holdout)
    candidate_labels = [
        f"{c.get('group')}:{c.get('family')}/{c.get('channel')}" for c in candidates
    ]
    policy_verdict = policy_cell.get("verdict")
    policy_demoted = isinstance(policy_verdict, str) and policy_verdict.startswith("demote_")
    diagnostic_pass = bool(standard.get("passes_4_of_5_control_standard"))
    if diagnostic_pass and policy_demoted:
        status = "diagnostic_promoted_policy_translation_demoted"
        readiness = "diagnostic_ready_policy_demoted"
        bottleneck = "policy_translation_failed_stability_checks"
        next_step = (
            "Write Law 2 as a diagnostic error-readout law; treat Brier-policy "
            "translation as future prospective work, not a current paper claim."
        )
    elif diagnostic_pass and candidates:
        status = "diagnostic_promoted_policy_cell_unvalidated"
        readiness = "diagnostic_ready_policy_not_ready"
        bottleneck = "prospective_policy_cell_validation"
        next_step = "Validate or demote the frozen codex_55/worry policy cell; do not run broad worry scaling first."
    elif diagnostic_pass:
        status = "diagnostic_promoted_no_policy_cell"
        readiness = "diagnostic_ready_policy_rejected"
        bottleneck = "policy_translation"
        next_step = "Keep Law 2 as error-readout; stop searching broad policy unless a new frozen cell appears."
    else:
        status = "diagnostic_not_confirmed"
        readiness = "not_paper_ready"
        bottleneck = "diagnostic_replication"
        next_step = "Rerun premium-channel diagnostic before any policy claim."
    return {
        "law": "family_channel_error_surface",
        "readiness": readiness,
        "status": status,
        "bottleneck": bottleneck,
        "current_evidence": {
            "premium_rows": premium.get("rows") or (premium.get("pooled") or {}).get("n"),
            "worry_positive_families": standard.get("worry_positive_families"),
            "worry_beats_confidence_and_sham_families": standard.get("worry_beats_confidence_and_sham_families"),
            "policy_candidates": candidate_labels,
            "policy_cell_verdict": policy_verdict,
            "policy_cell_temporal_delta": ((policy_cell.get("temporal_split") or {}).get("actual") or {}).get("mean_delta_brier"),
            "policy_cell_temporal_p": (((policy_cell.get("temporal_split") or {}).get("actual") or {}).get("paired_permutation") or {}).get("p_value"),
            "policy_cell_source_failures": (policy_cell.get("source_leave_one_out") or {}).get("failure_sources"),
            "policy_cell_gain_concentration": (policy_cell.get("source_bucket") or {}).get("max_positive_gain_share_abs"),
            "v26_resolved": db.get("v26_resolved"),
        },
        "next_eigenquestion": (
            "Can a frozen family/channel correction improve heldout Brier, or "
            "is auxiliary-channel evidence only diagnostic?"
        ),
        "next_step": next_step,
        "kill_condition": (
            "The diagnostic law fails if auxiliary channels no longer predict error against controls; "
            "the current Brier-policy translation is already demoted by temporal/source stress."
        ),
    }


def law3_status(
    cutoff: dict[str, Any],
    cutoff_candidates: dict[str, Any],
    cutoff_stage_b: dict[str, Any],
    cutoff_acquisition: dict[str, Any],
    cutoff_manifold_acquisition: dict[str, Any],
    cutoff_candidate_review: dict[str, Any],
    cutoff_candidate_ingest_preview: dict[str, Any],
    cutoff_polymarket_review: dict[str, Any],
    cutoff_polymarket_event_cap: dict[str, Any],
    cutoff_polymarket_provenance: dict[str, Any],
    cutoff_polymarket_decision_preview: dict[str, Any],
    cutoff_general_source_cec: dict[str, Any],
    cutoff_stage_b_freeze: dict[str, Any],
    cutoff_stage_b_score: dict[str, Any],
    cutoff_base_rate_join: dict[str, Any],
    cutoff_second_source_polymarket_gemini_score: dict[str, Any],
    cutoff_second_source_polymarket_deepseek_score: dict[str, Any],
    cutoff_second_source_polymarket_base_rate_availability: dict[str, Any],
    db: dict[str, Any],
) -> dict[str, Any]:
    public_resolved = int(cutoff.get("public_resolved_contracts") or 0)
    extracted_dates = int(cutoff.get("extracted_resolve_date_rows") or 0)
    premium_resolved = int(db.get("premium_resolved_contracts") or 0)
    premium_with_cutoff = int(db.get("premium_with_cutoff_flag") or 0)
    candidate_summary = cutoff_candidates.get("summary") if isinstance(cutoff_candidates.get("summary"), dict) else {}
    matched_strata = int(candidate_summary.get("matched_strata_count") or 0)
    pre_candidates = int((candidate_summary.get("eligible_by_relation") or {}).get("pre_cutoff", 0))
    post_candidates = int((candidate_summary.get("eligible_by_relation") or {}).get("post_cutoff", 0))
    cutoff_relation_conflicts = int(candidate_summary.get("cutoff_relation_conflicts") or 0)
    minimum_stage_b_ready = bool(candidate_summary.get("minimum_stage_b_ready"))
    supply_plan = candidate_summary.get("pre_cutoff_supply_plan") or {}
    stage_b_gate = cutoff_stage_b.get("stage_b_gate") or {}
    matched_call_reuse = cutoff_stage_b.get("matched_call_reuse") or {}
    matched_delta = (matched_call_reuse.get("aggregate_delta") or {}).get("post_minus_pre")
    acquisition_allocation = cutoff_acquisition.get("allocation") or []
    selected_manifold_rows = int(cutoff_manifold_acquisition.get("selected_rows") or 0)
    ready_for_minimum_ingest = bool(cutoff_manifold_acquisition.get("ready_for_minimum_ingest"))
    manual_review_rows = int(cutoff_candidate_review.get("manual_review_rows") or 0)
    auto_clear_rows = int(cutoff_candidate_review.get("auto_clear_rows") or 0)
    ready_for_unreviewed_db_ingest = bool(cutoff_candidate_review.get("ready_for_unreviewed_db_ingest"))
    ingest_write_result = cutoff_candidate_ingest_preview.get("write_db_result") or {}
    ingest_accepted_rows = int(cutoff_candidate_ingest_preview.get("accepted_rows") or 0)
    ingest_inserted_rows = int(ingest_write_result.get("inserted") or 0)
    ingest_ready = bool(cutoff_candidate_ingest_preview.get("ready_for_db_ingest"))
    polymarket_candidate_rows = int(cutoff_polymarket_review.get("candidate_rows") or 0)
    polymarket_manual_review_rows = int(cutoff_polymarket_review.get("manual_review_rows") or 0)
    polymarket_auto_clear_rows = int(cutoff_polymarket_review.get("auto_clear_rows") or 0)
    polymarket_ready_for_db_ingest = bool(cutoff_polymarket_review.get("ready_for_db_ingest"))
    polymarket_unique_event_families = int(cutoff_polymarket_review.get("unique_event_families") or 0)
    polymarket_cap_selected_rows = int(cutoff_polymarket_event_cap.get("selected_rows") or 0)
    polymarket_cap_dropped_rows = int(cutoff_polymarket_event_cap.get("dropped_rows") or 0)
    polymarket_cap_deficits = cutoff_polymarket_event_cap.get("deficits") or []
    polymarket_provenance_rows = int(cutoff_polymarket_provenance.get("candidate_rows") or 0)
    polymarket_provenance_manual_rows = int(cutoff_polymarket_provenance.get("manual_review_rows") or 0)
    polymarket_provenance_outcome_matches = int(
        cutoff_polymarket_provenance.get("rows_with_final_outcome_price_matching_y_known") or 0
    )
    polymarket_decision_accepted_rows = int(cutoff_polymarket_decision_preview.get("accepted_rows") or 0)
    polymarket_decision_missing_rows = int(cutoff_polymarket_decision_preview.get("missing_decision_rows") or 0)
    polymarket_decision_invalid_rows = int(cutoff_polymarket_decision_preview.get("invalid_decision_rows") or 0)
    polymarket_decision_ready = bool(cutoff_polymarket_decision_preview.get("ready_for_full_slice_db_ingest"))
    polymarket_write_result = cutoff_polymarket_decision_preview.get("write_db_result") or {}
    polymarket_inserted_rows = int(polymarket_write_result.get("inserted") or 0)
    polymarket_reviewed_db_rows = int(db.get("polymarket_reviewed_cutoff_contracts") or 0)
    general_source_cec_verdict = cutoff_general_source_cec.get("verdict") or {}
    general_source_cec_state = cutoff_general_source_cec.get("current_state") or {}
    freeze_ready = bool(cutoff_stage_b_freeze.get("ready_for_dispatch"))
    freeze_dispatch = cutoff_stage_b_freeze.get("dispatch_slate") or {}
    freeze_minimum_panel = cutoff_stage_b_freeze.get("minimum_balanced_panel") or {}
    freeze_limitations = cutoff_stage_b_freeze.get("matching_limitations") or {}
    score_verdict = str(cutoff_stage_b_score.get("verdict") or "")
    score_coverage = cutoff_stage_b_score.get("call_coverage") or {}
    score_calls = int(score_coverage.get("schema_ok_calls") or 0)
    score_expected = int(score_coverage.get("expected_calls") or 0)
    score_delta = (cutoff_stage_b_score.get("aggregate_delta") or {}).get("post_minus_pre")
    base_rate_coverage = cutoff_base_rate_join.get("coverage") or {}
    base_rate_effect = (cutoff_base_rate_join.get("repaired_effect") or {}).get("base_rate_matched") or {}
    base_rate_paired_cells = int(base_rate_effect.get("paired_cells") or 0)
    base_rate_delta = base_rate_effect.get("post_minus_pre_brier")
    second_source_aggregate = cutoff_second_source_polymarket_gemini_score.get("aggregate_delta") or {}
    second_source_paired = cutoff_second_source_polymarket_gemini_score.get("paired_stratum_delta") or {}
    second_source_deepseek_aggregate = cutoff_second_source_polymarket_deepseek_score.get("aggregate_delta") or {}
    second_source_deepseek_paired = cutoff_second_source_polymarket_deepseek_score.get("paired_stratum_delta") or {}
    fetch_failures = [
        row for row in cutoff_manifold_acquisition.get("fetch_statuses", [])
        if not row.get("ok")
    ]
    if score_verdict.startswith("promote_"):
        status = "stage_b_panel_scored_law_candidate_promotable"
        readiness = "law_candidate_ready_for_paper_with_limitations"
        bottleneck = "paper_claim_drafting_with_limitations"
        if base_rate_paired_cells:
            status = "stage_b_scored_partial_base_rate_repair_survived"
            next_step = (
                "Write Law 3 with the Stage-B scorer delta, paired-stratum test, "
                "and Stage-C partial base-rate repair; keep unjoined-row and "
                "second-source limits explicit. For the second-source continuation, "
                "Polymarket's reviewed platform-resolver slice is DB-ingested "
                "and Gemini/DeepSeek live smokes are aggregate-positive on average "
                "but matched-stratum null/opposite-sign; "
                "the Polymarket market-price control is not executable yet because "
                "post-cutoff freeze prices are missing locally and the live probe "
                "joined 0 rows; "
                "complete the remaining Metaculus target through bot-benchmarking/"
                "data-download access or licensed export before model calls. "
                "Dataset-source rows may open a separate frozen replication design "
                "but are not a drop-in substitute for the Metaculus target cells."
            )
        else:
            next_step = "Write Law 3 with the scorer delta, paired-stratum test, and base-rate limitation."
    elif score_verdict.startswith("kill_"):
        status = "stage_b_panel_scored_law_killed_or_scoped"
        readiness = "scoped_result_ready_for_paper"
        bottleneck = "paper_scope_revision"
        next_step = "Scope Law 3 to the cutoff-validity audit result and remove the broad law claim."
    elif score_verdict == "inconclusive_needs_review":
        status = "stage_b_panel_scored_inconclusive"
        readiness = "not_paper_ready"
        bottleneck = "result_review_or_followup_power"
        next_step = "Inspect the family/relation cells before deciding whether to extend or scope Law 3."
    elif score_verdict == "partial_calls_not_paper_ready" or (score_calls and score_expected and score_calls < score_expected):
        status = "stage_b_panel_partial_calls_needs_completion"
        readiness = "not_paper_ready"
        bottleneck = "complete_model_call_dispatch"
        next_step = "Complete the remaining Stage-B calls, re-ingest receipts, and rerun cutoff-panel-score."
    elif minimum_stage_b_ready and freeze_ready:
        status = "stage_b_panel_frozen_ready_for_dispatch"
        readiness = "not_paper_ready"
        bottleneck = "model_call_dispatch"
        next_step = (
            "Run the 240-row constrained Stage-B dispatch slate, ingest calls, "
            "and score pre/post Brier with the base-rate limitation explicit."
        )
    elif minimum_stage_b_ready:
        status = "stage_b_candidate_corpus_ready_needs_panel"
        readiness = "not_paper_ready"
        bottleneck = "matched_model_panel"
        next_step = "Freeze the matched pre/post corpus and run the constrained Stage B model panel."
    elif selected_manifold_rows and manual_review_rows:
        status = "manifold_candidates_selected_manual_review_required"
        readiness = "not_paper_ready"
        bottleneck = "candidate_review_before_db_ingest"
        next_step = (
            "Review flagged Manifold candidate rows, reject or accept them, "
            "then ingest accepted contracts and rerun cutoff-candidates/stage-b."
        )
    elif selected_manifold_rows and ready_for_unreviewed_db_ingest:
        status = "manifold_candidates_selected_clear_for_ingest_preview"
        readiness = "not_paper_ready"
        bottleneck = "db_ingest_preview"
        next_step = (
            "Build an ingest preview for the selected contracts, insert accepted "
            "rows into the DB, then rerun cutoff-candidates/stage-b before calls."
        )
    elif selected_manifold_rows:
        status = "manifold_candidates_selected_needs_review_report"
        readiness = "not_paper_ready"
        bottleneck = "candidate_review_report_missing_or_incomplete"
        next_step = (
            "Run projects/llm_forecasting_calibration_program/tools/"
            "cutoff_candidate_review.py, resolve any flags, then ingest accepted "
            "contracts before model calls."
        )
    elif fetch_failures:
        status = "manifold_acquisition_attempted_api_unavailable"
        readiness = "not_paper_ready"
        bottleneck = "pre_cutoff_supply_acquisition_runtime"
        next_step = (
            "Rerun cutoff-manifold-acquire when the Manifold API is available, "
            "or feed cached Manifold export JSON via --raw-json."
        )
    elif matched_strata and pre_candidates < 40:
        status = "matched_strata_present_pre_cutoff_underpowered"
        readiness = "not_paper_ready"
        bottleneck = "pre_cutoff_supply_and_balance"
        next_step = (
            "Fill the 27-row minimum cutoff acquisition manifest for the "
            "matched source/topic/length strata before model calls."
        )
    elif matched_strata:
        status = "matched_candidate_strata_present_needs_balance_review"
        readiness = "not_paper_ready"
        bottleneck = "matched_corpus_balance"
        next_step = "Review matched-strata balance before authorizing Stage B model calls."
    elif cutoff_relation_conflicts:
        status = "stored_cutoff_flags_stale_needs_computed_relation"
        readiness = "not_paper_ready"
        bottleneck = "cutoff_relation_provenance"
        next_step = (
            "Rerun cutoff-candidates with --panel-cutoff-date and "
            "--prefer-computed-cutoff, then rebuild matched strata from computed relation."
        )
    elif public_resolved and extracted_dates and premium_with_cutoff < premium_resolved:
        status = "metadata_repair_before_matched_corpus"
        readiness = "not_paper_ready"
        bottleneck = "resolve_date_and_cutoff_relation_materialization"
        next_step = "Materialize resolve-date/cutoff-relation metadata, then build the matched pre/post corpus."
    elif public_resolved and extracted_dates:
        status = "candidate_metadata_present_needs_matching"
        readiness = "not_paper_ready"
        bottleneck = "matched_pre_post_corpus"
        next_step = "Build matched pre/post strata from the candidate metadata before model calls."
    else:
        status = "insufficient_metadata"
        readiness = "not_paper_ready"
        bottleneck = "candidate_eligibility_supply"
        next_step = "Repair resolve-date metadata and identify public pre/post candidate supply."
    return {
        "law": "cutoff_validity",
        "readiness": readiness,
        "status": status,
        "bottleneck": bottleneck,
        "current_evidence": {
            "public_resolved_contracts": public_resolved,
            "extracted_resolve_date_rows": extracted_dates,
            "premium_resolved_contracts": premium_resolved,
            "premium_resolved_with_cutoff_flag": premium_with_cutoff,
            "pre_cutoff_eligible_rows": pre_candidates,
            "post_cutoff_eligible_rows": post_candidates,
            "matched_strata_count": matched_strata,
            "minimum_stage_b_ready": minimum_stage_b_ready,
            "panel_cutoff_date": cutoff_candidates.get("panel_cutoff_date"),
            "prefer_computed_cutoff": cutoff_candidates.get("prefer_computed_cutoff"),
            "stored_relation_counts": candidate_summary.get("stored_relation_counts") or {},
            "computed_relation_counts": candidate_summary.get("computed_relation_counts") or {},
            "cutoff_relation_conflicts": cutoff_relation_conflicts,
            "pre_cutoff_deficit_to_stage_b_minimum": supply_plan.get("pre_cutoff_deficit_to_stage_b_minimum"),
            "repair_rows_already_computed_pre_cutoff": supply_plan.get("repair_rows_already_computed_pre_cutoff"),
            "y_known_rows_missing_resolve_or_relation": supply_plan.get("y_known_rows_missing_resolve_or_relation"),
            "pre_cutoff_supply_interpretation": supply_plan.get("interpretation"),
            "stage_b_matched_pre_contracts": stage_b_gate.get("matched_pre_contracts"),
            "stage_b_matched_post_contracts": stage_b_gate.get("matched_post_contracts"),
            "stage_b_pre_deficit": stage_b_gate.get("pre_deficit"),
            "matched_call_reuse_contracts": matched_call_reuse.get("contracts_with_scored_calls_by_relation") or {},
            "matched_call_reuse_raw_call_rows": matched_call_reuse.get("raw_call_rows_by_relation") or {},
            "matched_call_reuse_post_minus_pre_brier": matched_delta,
            "minimum_acquisition_total": cutoff_acquisition.get("minimum_acquisition_total"),
            "full_balance_acquisition_total": cutoff_acquisition.get("full_balance_acquisition_total"),
            "manifold_acquisition_selected_rows": selected_manifold_rows,
            "manifold_acquisition_ready_for_minimum_ingest": ready_for_minimum_ingest,
            "manifold_acquisition_fetch_failures": len(fetch_failures),
            "manifold_acquisition_remaining_needs": (
                (cutoff_manifold_acquisition.get("assignment") or {}).get("remaining_needs") or {}
            ),
            "candidate_review_auto_clear_rows": auto_clear_rows,
            "candidate_review_manual_rows": manual_review_rows,
            "candidate_review_ready_for_unreviewed_db_ingest": ready_for_unreviewed_db_ingest,
            "candidate_review_flag_counts": cutoff_candidate_review.get("flag_counts") or {},
            "candidate_ingest_accepted_rows": ingest_accepted_rows,
            "candidate_ingest_inserted_rows": ingest_inserted_rows,
            "candidate_ingest_skipped_existing_rows": ingest_write_result.get("skipped_existing"),
            "candidate_ingest_ready_for_db_ingest": ingest_ready,
            "polymarket_review_candidate_rows": polymarket_candidate_rows,
            "polymarket_review_auto_clear_rows": polymarket_auto_clear_rows,
            "polymarket_review_manual_rows": polymarket_manual_review_rows,
            "polymarket_review_ready_for_db_ingest": polymarket_ready_for_db_ingest,
            "polymarket_review_unique_event_families": polymarket_unique_event_families,
            "polymarket_review_flag_counts": cutoff_polymarket_review.get("flag_counts") or {},
            "polymarket_event_cap_selected_rows": polymarket_cap_selected_rows,
            "polymarket_event_cap_dropped_rows": polymarket_cap_dropped_rows,
            "polymarket_event_cap_deficits": polymarket_cap_deficits,
            "polymarket_provenance_candidate_rows": polymarket_provenance_rows,
            "polymarket_provenance_manual_review_rows": polymarket_provenance_manual_rows,
            "polymarket_provenance_outcome_price_y_known_matches": polymarket_provenance_outcome_matches,
            "polymarket_provenance_flag_counts": cutoff_polymarket_provenance.get("flag_counts") or {},
            "polymarket_decision_accepted_rows": polymarket_decision_accepted_rows,
            "polymarket_decision_missing_rows": polymarket_decision_missing_rows,
            "polymarket_decision_invalid_rows": polymarket_decision_invalid_rows,
            "polymarket_decision_ready_for_full_slice_db_ingest": polymarket_decision_ready,
            "polymarket_decision_inserted_rows": polymarket_inserted_rows,
            "polymarket_reviewed_db_rows": polymarket_reviewed_db_rows,
            "general_source_cec_existing_target_next_step": general_source_cec_verdict.get("existing_target_next_step"),
            "general_source_cec_dataset_source_substitution": general_source_cec_verdict.get("dataset_source_substitution"),
            "general_source_cec_dataset_source_new_lane": general_source_cec_verdict.get("dataset_source_new_lane"),
            "general_source_cec_metaculus_probe_verdict": general_source_cec_state.get("metaculus_probe_verdict"),
            "stage_b_freeze_ready_for_dispatch": freeze_ready,
            "stage_b_freeze_pilot_id": cutoff_stage_b_freeze.get("pilot_id"),
            "stage_b_freeze_dispatch_rows": freeze_dispatch.get("rows"),
            "stage_b_freeze_dispatch_sha256": freeze_dispatch.get("sha256"),
            "stage_b_freeze_minimum_panel_contracts": freeze_minimum_panel.get("contracts"),
            "stage_b_freeze_minimum_panel_counts": freeze_minimum_panel.get("counts_by_relation") or {},
            "stage_b_freeze_unknown_base_rate_contracts": freeze_limitations.get("minimum_panel_unknown_base_rate_contracts"),
            "stage_b_freeze_not_yet_matched_dimensions": freeze_limitations.get("not_yet_matched_dimensions") or [],
            "stage_b_score_verdict": score_verdict or None,
            "stage_b_score_expected_calls": score_expected or None,
            "stage_b_score_schema_ok_calls": score_calls,
            "stage_b_score_post_minus_pre": score_delta,
            "stage_c_base_rate_joined_contracts": base_rate_coverage.get("joined_contracts"),
            "stage_c_base_rate_missing_contracts": base_rate_coverage.get("missing_contracts"),
            "stage_c_base_rate_matched_paired_cells": base_rate_paired_cells,
            "stage_c_base_rate_matched_post_minus_pre": base_rate_delta,
            "second_source_polymarket_gemini_valid_rows": cutoff_second_source_polymarket_gemini_score.get("valid_rows"),
            "second_source_polymarket_gemini_post_minus_pre": second_source_aggregate.get("post_minus_pre"),
            "second_source_polymarket_gemini_paired_cells": second_source_paired.get("paired_cells"),
            "second_source_polymarket_gemini_paired_post_minus_pre": second_source_paired.get("post_minus_pre"),
            "second_source_polymarket_gemini_paired_p": (
                (second_source_paired.get("paired_permutation") or {}).get("p_value")
                if isinstance(second_source_paired.get("paired_permutation"), dict)
                else None
            ),
            "second_source_polymarket_deepseek_valid_rows": cutoff_second_source_polymarket_deepseek_score.get("valid_rows"),
            "second_source_polymarket_deepseek_post_minus_pre": second_source_deepseek_aggregate.get("post_minus_pre"),
            "second_source_polymarket_deepseek_paired_cells": second_source_deepseek_paired.get("paired_cells"),
            "second_source_polymarket_deepseek_paired_post_minus_pre": second_source_deepseek_paired.get("post_minus_pre"),
            "second_source_polymarket_deepseek_paired_p": (
                (second_source_deepseek_paired.get("paired_permutation") or {}).get("p_value")
                if isinstance(second_source_deepseek_paired.get("paired_permutation"), dict)
                else None
            ),
            "second_source_polymarket_base_rate_availability_verdict": cutoff_second_source_polymarket_base_rate_availability.get("verdict"),
            "second_source_polymarket_pre_cutoff_db_freeze_values": cutoff_second_source_polymarket_base_rate_availability.get("pre_cutoff_db_freeze_values"),
            "second_source_polymarket_post_cutoff_db_freeze_values": cutoff_second_source_polymarket_base_rate_availability.get("post_cutoff_db_freeze_values"),
            "second_source_polymarket_post_cutoff_probe_joined_rows": cutoff_second_source_polymarket_base_rate_availability.get("post_cutoff_probe_joined_rows"),
            "second_source_polymarket_post_cutoff_probe_join_status_counts": (
                cutoff_second_source_polymarket_base_rate_availability.get("post_cutoff_probe_join_status_counts") or {}
            ),
            "acquisition_allocation": [
                {
                    "source": row.get("source"),
                    "topic": row.get("topic"),
                    "question_length_bucket": row.get("question_length_bucket"),
                    "minimum_add": row.get("minimum_acquisition_n"),
                    "full_balance_add": row.get("full_balance_acquisition_n"),
                }
                for row in acquisition_allocation
            ],
        },
        "next_eigenquestion": (
            "Does matched pre-cutoff performance exceed matched post-cutoff performance "
            "after source/topic/base-rate controls?"
        ),
        "next_step": next_step,
        "kill_condition": "Matched pre/post rows show no calibration difference, or the difference is explained by matching failures.",
    }


def paper_status(laws: list[dict[str, Any]]) -> dict[str, Any]:
    blockers = [law for law in laws if law["readiness"] == "not_paper_ready"]
    policy_open = [law for law in laws if law["readiness"] == "diagnostic_ready_policy_not_ready"]
    policy_demoted = [law for law in laws if law["readiness"] == "diagnostic_ready_policy_demoted"]
    law1_negative = [
        law for law in laws if law["law"] == "alignment_modulated_bias_inheritance"
        and law["readiness"] == "negative_result_ready_for_scoped_section"
    ]
    law3_promoted = [
        law for law in laws if law["law"] == "cutoff_validity"
        and law["readiness"] == "law_candidate_ready_for_paper_with_limitations"
    ]
    law3_scoped = [
        law for law in laws if law["law"] == "cutoff_validity"
        and law["readiness"] == "scoped_result_ready_for_paper"
    ]
    if law3_promoted:
        law3_minimum = (
            "Write Law 3 from the completed cutoff-validity Stage-B panel, "
            "including the paired-stratum delta, Stage-C partial base-rate "
            "repair, and remaining unjoined-row / second-source limits."
        )
    elif law3_scoped:
        law3_minimum = "Write Law 3 as a scoped/negative cutoff-validity result."
    else:
        law3_minimum = "Run the Law 3 matched pre/post model panel, or scope Law 3 to analytic audit."
    return {
        "ready_for_landmark_claim": False,
        "ready_for_diagnostic_law_section": bool(laws[1]["readiness"].startswith("diagnostic_ready")),
        "minimum_before_submission": [
            (
                "Write Law 1 as a negative/scoping result, not as a promoted MIMIC-collapse law."
                if law1_negative
                else "Execute or kill Law 1 anti-bias-collapse."
            ),
            (
                "Write Law 2 as diagnostic-only and move Brier-policy translation "
                "to future work."
                if policy_demoted
                else "Validate or demote the Law 2 codex_55/worry policy cell."
            ),
            law3_minimum,
            "Update the paper so diagnostic laws and deployment-policy claims are separate.",
        ],
        "hard_blockers": [row["law"] for row in blockers],
        "policy_open_items": [row["law"] for row in policy_open],
    }


def build_report(db_path: Path) -> dict[str, Any]:
    db = db_snapshot(db_path)
    premium = read_json(PREMIUM_REPORT)
    channel_holdout = read_json(CHANNEL_HOLDOUT_REPORT)
    policy_cell = read_json(CHANNEL_POLICY_CELL_REPORT)
    cutoff = read_json(CUTOFF_AUDIT_REPORT)
    cutoff_candidates = read_json(CUTOFF_CANDIDATE_REPORT)
    cutoff_stage_b = read_json(CUTOFF_STAGE_B_REPORT)
    cutoff_acquisition = read_json(CUTOFF_ACQUISITION_REPORT)
    cutoff_manifold_acquisition = read_json(CUTOFF_MANIFOLD_ACQUISITION_REPORT)
    cutoff_candidate_review = read_json(CUTOFF_CANDIDATE_REVIEW_REPORT)
    cutoff_candidate_ingest_preview = read_json(CUTOFF_CANDIDATE_INGEST_PREVIEW)
    cutoff_polymarket_review = read_json(CUTOFF_POLYMARKET_REVIEW_REPORT)
    cutoff_polymarket_event_cap = read_json(CUTOFF_POLYMARKET_EVENT_CAP_REPORT)
    cutoff_polymarket_provenance = read_json(CUTOFF_POLYMARKET_PROVENANCE_PACKET)
    cutoff_polymarket_decision_preview = read_json(CUTOFF_POLYMARKET_DECISION_PREVIEW)
    cutoff_general_source_cec = read_json(CUTOFF_GENERAL_SOURCE_CEC_PACKET)
    cutoff_stage_b_freeze = read_json(CUTOFF_STAGE_B_FREEZE_REPORT)
    cutoff_stage_b_score = read_json(CUTOFF_STAGE_B_SCORE_REPORT)
    cutoff_base_rate_join = read_json(CUTOFF_BASE_RATE_JOIN_REPORT)
    cutoff_second_source_polymarket_gemini_score = read_json(CUTOFF_SECOND_SOURCE_POLYMARKET_GEMINI_SCORE)
    cutoff_second_source_polymarket_deepseek_score = read_json(CUTOFF_SECOND_SOURCE_POLYMARKET_DEEPSEEK_SCORE)
    cutoff_second_source_polymarket_base_rate_availability = read_json(CUTOFF_SECOND_SOURCE_POLYMARKET_BASE_RATE_AVAILABILITY)
    anti_bias_dispatch = read_json(ANTI_BIAS_DISPATCH)
    anti_bias_score = read_json(ANTI_BIAS_SCORE)
    slate_rows = count_jsonl(ANTI_BIAS_SLATE)
    smoke_slate_rows = count_jsonl(ANTI_BIAS_SMOKE_SLATE)
    laws = [
        law1_status(db, slate_rows, smoke_slate_rows, anti_bias_dispatch, anti_bias_score),
        law2_status(premium, channel_holdout, policy_cell, db),
        law3_status(
            cutoff,
            cutoff_candidates,
            cutoff_stage_b,
            cutoff_acquisition,
            cutoff_manifold_acquisition,
            cutoff_candidate_review,
            cutoff_candidate_ingest_preview,
            cutoff_polymarket_review,
            cutoff_polymarket_event_cap,
            cutoff_polymarket_provenance,
            cutoff_polymarket_decision_preview,
            cutoff_general_source_cec,
            cutoff_stage_b_freeze,
            cutoff_stage_b_score,
            cutoff_base_rate_join,
            cutoff_second_source_polymarket_gemini_score,
            cutoff_second_source_polymarket_deepseek_score,
            cutoff_second_source_polymarket_base_rate_availability,
            db,
        ),
    ]
    return {
        "schema": "gp245-law-readiness-v1",
        "db": str(db_path),
        "inputs": {
            "premium_report": str(PREMIUM_REPORT.relative_to(REPO)),
            "channel_holdout_report": str(CHANNEL_HOLDOUT_REPORT.relative_to(REPO)),
            "channel_policy_cell_report": str(CHANNEL_POLICY_CELL_REPORT.relative_to(REPO)),
            "cutoff_audit_report": str(CUTOFF_AUDIT_REPORT.relative_to(REPO)),
            "cutoff_candidate_report": str(CUTOFF_CANDIDATE_REPORT.relative_to(REPO)),
            "cutoff_stage_b_report": str(CUTOFF_STAGE_B_REPORT.relative_to(REPO)),
            "cutoff_acquisition_report": str(CUTOFF_ACQUISITION_REPORT.relative_to(REPO)),
            "cutoff_manifold_acquisition_report": str(CUTOFF_MANIFOLD_ACQUISITION_REPORT.relative_to(REPO)),
            "cutoff_candidate_review_report": str(CUTOFF_CANDIDATE_REVIEW_REPORT.relative_to(REPO)),
            "cutoff_candidate_ingest_preview": str(CUTOFF_CANDIDATE_INGEST_PREVIEW.relative_to(REPO)),
            "cutoff_polymarket_review_report": str(CUTOFF_POLYMARKET_REVIEW_REPORT.relative_to(REPO)),
            "cutoff_polymarket_event_cap_report": str(CUTOFF_POLYMARKET_EVENT_CAP_REPORT.relative_to(REPO)),
            "cutoff_polymarket_provenance_packet": str(CUTOFF_POLYMARKET_PROVENANCE_PACKET.relative_to(REPO)),
            "cutoff_polymarket_decision_preview": str(CUTOFF_POLYMARKET_DECISION_PREVIEW.relative_to(REPO)),
            "cutoff_stage_b_freeze_report": str(CUTOFF_STAGE_B_FREEZE_REPORT.relative_to(REPO)),
            "cutoff_stage_b_score_report": str(CUTOFF_STAGE_B_SCORE_REPORT.relative_to(REPO)),
            "cutoff_base_rate_join_report": str(CUTOFF_BASE_RATE_JOIN_REPORT.relative_to(REPO)),
            "cutoff_second_source_polymarket_gemini_score": str(
                CUTOFF_SECOND_SOURCE_POLYMARKET_GEMINI_SCORE.relative_to(REPO)
            ),
            "cutoff_second_source_polymarket_deepseek_score": str(
                CUTOFF_SECOND_SOURCE_POLYMARKET_DEEPSEEK_SCORE.relative_to(REPO)
            ),
            "cutoff_second_source_polymarket_base_rate_availability": str(
                CUTOFF_SECOND_SOURCE_POLYMARKET_BASE_RATE_AVAILABILITY.relative_to(REPO)
            ),
            "anti_bias_slate": str(ANTI_BIAS_SLATE.relative_to(REPO)),
            "anti_bias_smoke_slate": str(ANTI_BIAS_SMOKE_SLATE.relative_to(REPO)),
            "anti_bias_dispatch": str(ANTI_BIAS_DISPATCH.relative_to(REPO)),
            "anti_bias_score": str(ANTI_BIAS_SCORE.relative_to(REPO)),
        },
        "db_snapshot": db,
        "laws": laws,
        "paper_status": paper_status(laws),
        "void_mining": {
            "highest_yield_negative": "Law 3 matched pre/post corpus fails after acquisition, scoping cutoff-validity to a dataset-audit caveat.",
            "highest_yield_positive": "Law 3 matched pre/post pass plus Law 2 diagnostic pass would support a source-currency plus channel-surface paper spine.",
            "do_not_repeat": [
                "generic worry-vs-Brier without family/channel controls",
                "same anti-bias-collapse design without raw-gap matching or randomization",
                "cutoff-validity model calls before matched corpus metadata",
            ],
        },
        "primitive_amnesia_reuse": [
            "paired_permutation_test",
            "bootstrap_ci",
            "power_aware_verdict",
            "tost_equivalence",
            "n_required_for_brier_delta",
            "classify_forecast_source_currency",
        ],
    }


def write_outputs(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "law_readiness_report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = ["# GP-245 Law Readiness Report", ""]
    lines.append(f"- Schema: `{result['schema']}`")
    lines.append(f"- DB: `{result['db']}`")
    lines.append(f"- Ready for landmark claim: `{result['paper_status']['ready_for_landmark_claim']}`")
    lines.append(f"- Ready for diagnostic Law 2 section: `{result['paper_status']['ready_for_diagnostic_law_section']}`")
    lines.append("")
    lines.append("## Law Status")
    lines.append("")
    for law in result["laws"]:
        lines.append(f"### {law['law']}")
        lines.append("")
        lines.append(f"- Readiness: `{law['readiness']}`")
        lines.append(f"- Status: `{law['status']}`")
        lines.append(f"- Bottleneck: `{law['bottleneck']}`")
        lines.append(f"- Next eigenquestion: {law['next_eigenquestion']}")
        lines.append(f"- Next step: {law['next_step']}")
        lines.append(f"- Kill condition: {law['kill_condition']}")
        lines.append("- Current evidence:")
        for key, value in law["current_evidence"].items():
            lines.append(f"  - `{key}`: {value}")
        lines.append("")
    lines.append("## Minimum Before Submission")
    lines.append("")
    for item in result["paper_status"]["minimum_before_submission"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Void Mining Guardrails")
    lines.append("")
    lines.append(f"- Highest-yield negative: {result['void_mining']['highest_yield_negative']}")
    lines.append(f"- Highest-yield positive: {result['void_mining']['highest_yield_positive']}")
    for item in result["void_mining"]["do_not_repeat"]:
        lines.append(f"- Do not repeat: {item}")
    lines.append("")
    lines.append("## Primitive Reuse")
    lines.append("")
    for name in result["primitive_amnesia_reuse"]:
        lines.append(f"- `{name}`")
    lines.append("")
    (out_dir / "law_readiness_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = build_report(args.db)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.out_dir:
        write_outputs(result, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
