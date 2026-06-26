#!/usr/bin/env python3
"""Build the GP-245 claim-gap matrix from current stored evidence.

No network, no model calls, no database mutation.

The output is a reviewer-facing evidence table: each candidate claim is
classified as supported, scoped, underpowered, not valid for broad
conclusions, or dependent on external acquisition/prospective resolution.
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16"

PAPER_READINESS = PROGRAM / "law_validation_v1/workspace/paper_readiness_exhaustion_audit.json"
PAPER_COHERENCE = PROGRAM / "paper_alignment_v1/workspace/paper_coherence_audit.json"
STRUCTURED_PROMPTING_REPORT = (
    PROGRAM
    / "structured_metacognition_v1/workspace/structured_metacognition_public_v1_score_report.json"
)
STRUCTURED_PROMPTING_EXTERNAL_CONTROL = (
    PROGRAM
    / "structured_metacognition_v1/workspace/structured_metacognition_public_v1_external_control_report.json"
)
STRUCTURED_PROMPTING_CLAUDE_REPLICATION = (
    PROGRAM
    / "structured_metacognition_v1/workspace/structured_metacognition_public_v1_claude_replication_score_report.json"
)
F47_READINESS = (
    PROGRAM
    / "forecaster_skill_calibration_v1/workspace/f47_production_readiness_audit_2026_06_05"
    / "f47_production_readiness_audit.json"
)
F100_SOURCE = PROGRAM / "forecaster_skill_calibration_v1/workspace/f100_source_currency_audit_2026_06_03.json"
REPLACEMENT_MARKET = (
    PROGRAM
    / "cutoff_validity_v1/workspace/equal_information_replacement_score_2026_06_15"
    / "equal_information_replacement_score.json"
)
MANIFOLD_MARKET = (
    PROGRAM
    / "cutoff_validity_v1/workspace/non_polymarket_equal_information_export_packet_2026_06_15"
    / "manifold_history_score_2026_06_15/non_polymarket_equal_information_score.json"
)
FRED_VINTAGE = (
    PROGRAM / "cutoff_validity_v1/workspace/fred_vintage_bulk_rescore_2026_06_04/fred_vintage_rescore.json"
)
SECOND_SOURCE_VOID = PROGRAM / "cutoff_validity_v1/workspace/cutoff_second_source_void_miner_report.json"
FIELD_WIDE_PROTOCOL = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"
    / "field_wide_validity_audit_protocol.md"
)
FIELD_WIDE_LOCAL_EVIDENCE = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"
    / "field_wide_validity_local_evidence_summary.md"
)
FIELD_WIDE_SOURCE_INVENTORY = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"
    / "field_wide_validity_source_inventory.md"
)
FORECASTBENCH_ROW_SCHEMA_PILOT = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"
    / "field_wide_forecastbench_row_schema_pilot.md"
)
FORECASTBENCH_SCORE_AUDIT = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"
    / "field_wide_forecastbench_score_audit.md"
)
FORECASTBENCH_HUMAN_COMPARATOR_AUDIT = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"
    / "field_wide_forecastbench_human_comparator_audit.md"
)
POLYBENCH_SOURCE_PILOT = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"
    / "field_wide_polybench_source_pilot.md"
)
PREDICTIONMARKETBENCH_ROW_SCHEMA_PILOT = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"
    / "field_wide_predictionmarketbench_row_schema_pilot.md"
)
PROPHET_ARENA_ROW_SCHEMA_PILOT = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"
    / "field_wide_prophet_arena_row_schema_pilot.md"
)


COLUMNS = [
    "claim_id",
    "route",
    "candidate_claim",
    "current_effect",
    "source_scope",
    "family_scope",
    "contract_count",
    "independent_event_count",
    "same_contract_baseline",
    "source_currency_check",
    "label_time_check",
    "equal_information_baseline",
    "market_join",
    "human_join",
    "prospective_order",
    "control_condition",
    "source_leave_one_out",
    "family_leave_one_out",
    "falsifier_or_decision_rule",
    "gap_label",
    "next_action",
    "evidence_sources",
]


PAIRWISE_GATE_LABELS = {
    "same_packet_policy_beats_f100": "same-packet comparison against the calibrated baseline",
    "same_packet_policy_beats_raw": "same-packet comparison against raw probabilities",
    "cross_packet_bidirectional_transfer": "bidirectional cross-packet transfer",
    "joined_market_control": "joined market comparison",
    "prospective_causal_order_resolved": "prospective causal-order scoring",
}

STATUS_LABELS = {
    "claim_ready_for_ranking_not_probability": "Supported for ranking, not for probability conversion",
    "claim_ready_scoped_controlled_use": "Supported under scope",
    "claim_ready_scoped_intervention_pending_external_controls": (
        "Supported under scope; market/family checks open"
    ),
    "claim_ready_scoped_measurement": "Supported as a scoped measurement result",
    "diagnostic_headroom_only": "Diagnostic only",
    "field_audit_needed": "Potential field-wide contribution; needs benchmark audit",
    "needs_external_acquisition": "Needs external data",
    "negative_claim_ready_scoped": "Supported negative result under scope",
    "not_claim_ready_market_lower_brier_or_underpowered": "Not supported; market Brier is lower or evidence is underpowered",
    "reproducibility_gap": "Reproducibility gap",
    "underpowered_directional_not_source_stable": "Underpowered and not source-stable",
}

CHECK_LABELS = {
    "human_join": "human comparison",
    "prospective_order": "prospective order",
    "source_leave_one_out": "source-by-source check",
    "family_leave_one_out": "model-family check",
    "equal_information_baseline": "equal-information baseline",
}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def scalar(cur: sqlite3.Cursor, sql: str) -> Any:
    row = cur.execute(sql).fetchone()
    return row[0] if row else None


def db_counts(db: Path) -> dict[str, Any]:
    con = sqlite3.connect(db)
    cur = con.cursor()
    try:
        return {
            "contracts": scalar(cur, "SELECT COUNT(*) FROM contracts"),
            "pilot_calls": scalar(cur, "SELECT COUNT(*) FROM pilot_calls"),
            "source_currency_rows": scalar(cur, "SELECT COUNT(*) FROM source_currency_gate_rows"),
            "source_currency_conflicts": scalar(cur, "SELECT COUNT(*) FROM v_source_currency_gate_conflicts"),
            "label_time_rows": scalar(cur, "SELECT COUNT(*) FROM dataset_label_time_gate_rows"),
            "external_market_rows": scalar(cur, "SELECT COUNT(*) FROM v_external_market_baselines"),
            "equal_information_rows": scalar(
                cur, "SELECT COUNT(*) FROM v_external_market_baselines WHERE equal_information_flag = 1"
            ),
            "equal_information_contracts": scalar(
                cur,
                "SELECT COUNT(DISTINCT contract_id) FROM v_external_market_baselines WHERE equal_information_flag = 1",
            ),
            "structured_rows": scalar(
                cur,
                "SELECT COUNT(*) FROM pilot_calls WHERE pilot_id='structured_metacognition_public_v1' AND schema_ok=1",
            ),
            "structured_contracts": scalar(
                cur,
                "SELECT COUNT(DISTINCT contract_id) FROM pilot_calls WHERE pilot_id='structured_metacognition_public_v1' AND schema_ok=1",
            ),
        }
    finally:
        con.close()


def nested(obj: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = obj
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return default if cur is None else cur


def fnum(value: Any, digits: int = 6) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "NA"


def forecastbench_human_summary(report: dict[str, Any], filename: str) -> dict[str, Any]:
    for item in report.get("summaries", []) or []:
        if isinstance(item, dict) and item.get("forecast_file") == filename:
            return item
    return {}


def evidence(*paths: Path) -> str:
    return "; ".join(rel(path) for path in paths if path.exists())


def sources(*labels: str) -> str:
    return "; ".join(label for label in labels if label)


def friendly_gates(gates: list[Any]) -> str:
    return ", ".join(PAIRWISE_GATE_LABELS.get(str(gate), str(gate).replace("_", " ")) for gate in gates)


def row(**kwargs: Any) -> dict[str, str]:
    out = {column: "" for column in COLUMNS}
    for key, value in kwargs.items():
        if key not in out:
            raise KeyError(key)
        if isinstance(value, (list, tuple)):
            out[key] = "; ".join(str(item) for item in value)
        else:
            out[key] = "" if value is None else str(value)
    return out


def build_matrix(db: Path) -> dict[str, Any]:
    counts = db_counts(db)
    readiness = read_json(PAPER_READINESS)
    coherence = read_json(PAPER_COHERENCE)
    structured = read_json(STRUCTURED_PROMPTING_REPORT)
    structured_external = read_json(STRUCTURED_PROMPTING_EXTERNAL_CONTROL)
    structured_claude = read_json(STRUCTURED_PROMPTING_CLAUDE_REPLICATION)
    f47 = read_json(F47_READINESS)
    f100 = read_json(F100_SOURCE)
    replacement = read_json(REPLACEMENT_MARKET)
    manifold = read_json(MANIFOLD_MARKET)
    fred = read_json(FRED_VINTAGE)
    second_source_void = read_json(SECOND_SOURCE_VOID)
    forecastbench_score = read_json(FORECASTBENCH_SCORE_AUDIT.with_suffix(".json"))
    forecastbench_human = read_json(FORECASTBENCH_HUMAN_COMPARATOR_AUDIT.with_suffix(".json"))
    polybench_source = read_json(POLYBENCH_SOURCE_PILOT.with_suffix(".json"))
    predictionmarketbench = read_json(PREDICTIONMARKETBENCH_ROW_SCHEMA_PILOT.with_suffix(".json"))

    readiness_verdict = readiness.get("program_verdict") or {}
    coherence_verdict = coherence.get("verdict") or {}
    structured_gates = structured.get("condition_gates") or {}
    structured_claude_gates = structured_claude.get("condition_gates") or {}
    structured_claude_coverage = structured_claude.get("coverage") or {}
    expert_gate = structured_gates.get("expert_training_prompt") or {}
    audit_gate = structured_gates.get("audit_informed_prompt") or {}
    failure_gate = structured_gates.get("failure_mode_specific_prompt") or {}
    f47_failed = [gate.get("gate") for gate in f47.get("gates", []) if isinstance(gate, dict) and not gate.get("passed")]

    replacement_summary = replacement.get("summary") or {}
    replacement_panel_perm = replacement_summary.get("paired_permutation_model_panel_vs_market") or {}
    manifold_candidate = manifold.get("selected_candidate") or {}
    f100_overall = f100.get("overall") or {}
    f100_by_cutoff = f100.get("by_cutoff_relation") or {}
    f100_pre = f100_by_cutoff.get("pre_cutoff") or {}
    f100_post = f100_by_cutoff.get("post_cutoff") or {}
    fred_control = fred.get("control") or {}
    human_super = forecastbench_human_summary(forecastbench_human, "2024-07-21.ForecastBench.human_super.json")
    human_public = forecastbench_human_summary(forecastbench_human, "2024-07-21.ForecastBench.human_public.json")
    prophet_arena_pilot = read_json(PROPHET_ARENA_ROW_SCHEMA_PILOT.with_suffix(".json"))

    rows = [
        row(
            claim_id="row_level_validity_layer",
            route="measurement",
            candidate_claim=(
                "Forecast rows need source-currency, label-time, and equal-information status before "
                "broad conclusions can be drawn."
            ),
            current_effect=(
                f"{counts['source_currency_rows']} source-currency rows, "
                f"{counts['source_currency_conflicts']} cutoff conflicts; "
                f"{counts['label_time_rows']} label-time rows; "
                f"{counts['external_market_rows']} external market rows."
            ),
            source_scope="Manifold source-currency plus FRED label-time and market-source controls",
            family_scope="five-family program, strongest result in matched Manifold panel",
            contract_count=counts["contracts"],
            independent_event_count="not globally de-duplicated; equal-information replacement uses one row per event",
            same_contract_baseline="partial",
            source_currency_check="present",
            label_time_check="present for official-data rows",
            equal_information_baseline="partial",
            market_join=f"{counts['equal_information_rows']} equal-information rows",
            human_join=(
                "partial public ForecastBench aggregate files scored; strict same-information market overlap "
                "for human aggregate files remains two rows each"
            ),
            prospective_order="partial",
            control_condition="not applicable",
            source_leave_one_out="partial",
            family_leave_one_out="partial",
            falsifier_or_decision_rule="Field-wide audit finds few row-level validity failures or no conclusion changes.",
            gap_label="claim_ready_scoped_measurement",
            next_action="Add field-wide benchmark audit rows before claiming a general field failure.",
            evidence_sources=sources("paper-readiness audit", "paper-coherence audit", "FRED vintage rescore"),
        ),
        row(
            claim_id="raw_llm_market_or_human_superiority",
            route="measurement boundary",
            candidate_claim="Raw LLM panels beat markets or humans under equal information.",
            current_effect=(
                "Polymarket panel Brier "
                f"{fnum(replacement_summary.get('model_panel_mean_p_brier'))} vs market "
                f"{fnum(replacement_summary.get('mean_market_brier'))}, p="
                f"{fnum(replacement_panel_perm.get('p_value'), 4)}; "
                "Manifold panel-minus-market "
                f"{fnum(manifold_candidate.get('model_panel_minus_market_brier'))}, p="
                f"{fnum(nested(manifold_candidate, 'paired_permutation_model_panel_vs_market', 'p_value'), 4)}. "
                "ForecastBench 2024 human aggregate files are scoreable "
                f"(superforecaster/public Brier {fnum(human_super.get('resolved_brier_non_imputed'))}/"
                f"{fnum(human_public.get('resolved_brier_non_imputed'))}), but each has only two strict "
                "same-information market rows."
            ),
            source_scope="Polymarket and Manifold equal-information slices",
            family_scope="four-family Polymarket; selected five-family Manifold low-stake slice",
            contract_count=48,
            independent_event_count="48 same-contract market comparisons; broader event-family audit still separate",
            same_contract_baseline="present",
            source_currency_check="present for selected rows",
            label_time_check="not the limiting issue for market rows",
            equal_information_baseline="present but small",
            market_join="present",
            human_join="partial public ForecastBench human aggregate scores; too little strict market overlap",
            prospective_order="mostly retrospective fill",
            control_condition="not applicable",
            source_leave_one_out="two-source boundary only",
            family_leave_one_out="partial",
            falsifier_or_decision_rule="Predeclared source-balanced equal-information packet beats market/human baseline.",
            gap_label="not_claim_ready_market_lower_brier_or_underpowered",
            next_action="Do not claim superiority; acquire larger equal-information market/human bars.",
            evidence_sources=sources(
                "Polymarket equal-information comparison",
                "Manifold equal-information comparison",
                evidence(FORECASTBENCH_HUMAN_COMPARATOR_AUDIT),
            ),
        ),
        row(
            claim_id="source_valid_calibration_rule",
            route="controlled use",
            candidate_claim="A calibration rule improves point probabilities on rows that pass source checks.",
            current_effect=(
                "Forward-looking improvement on rows that pass source checks but regression on source-visible rows; "
                f"overall calibrated-minus-raw delta={fnum(f100_overall.get('delta_f100_minus_raw'))}, "
                f"source-visible delta={fnum(f100_pre.get('delta_f100_minus_raw'))}, "
                f"forward-looking delta={fnum(f100_post.get('delta_f100_minus_raw'))}."
            ),
            source_scope="forward-looking rows that pass source checks",
            family_scope="five-family public-domain panel",
            contract_count="documented in source-currency audit",
            independent_event_count="not globally de-duplicated",
            same_contract_baseline="raw/calibrated same-row comparison",
            source_currency_check="required and present for scoped use",
            label_time_check="required where official-data labels appear",
            equal_information_baseline="not required for scoped calibration, but needed for market additivity",
            market_join="partial",
            human_join="missing",
            prospective_order="needs future confirmation",
            control_condition="not applicable",
            source_leave_one_out="partial",
            family_leave_one_out="partial",
            falsifier_or_decision_rule="Source-valid live rows regress versus raw or market bars.",
            gap_label="claim_ready_scoped_controlled_use",
            next_action="Keep as calibration after source checks only; do not use as retrospective correction.",
            evidence_sources=sources("calibration audit after source checks", "paper-readiness audit"),
        ),
        row(
            claim_id="pairwise_ranking_interface",
            route="interface",
            candidate_claim="Pairwise ranking is supported under controls; absolute probability conversion is not yet ready.",
            current_effect=(
                "Ranking evidence survives, but probability conversion failed the following checks: "
                + friendly_gates(f47_failed)
            ),
            source_scope="source-balanced pairwise packet; joined market controls still small",
            family_scope="four-family pairwise packet",
            contract_count="24 unique non-tie pairs in main ranking result",
            independent_event_count="pair graph needs prospective event-family confirmation",
            same_contract_baseline="raw/calibrated comparisons present; market overlap small",
            source_currency_check="present for ranking packet",
            label_time_check="not the limiting issue",
            equal_information_baseline="insufficient for probability layer",
            market_join="underpowered",
            human_join="missing",
            prospective_order="unresolved prospective market-freeze packet",
            control_condition="source/orientation controls present",
            source_leave_one_out="partial",
            family_leave_one_out="partial",
            falsifier_or_decision_rule="Prospective graph-calibrated layer fails raw/calibrated/market controls.",
            gap_label="claim_ready_for_ranking_not_probability",
            next_action="Score prospective market-freeze packet after resolution; fit graph layer only under predeclared tests.",
            evidence_sources=sources("pairwise-ranking readiness audit"),
        ),
        row(
            claim_id="structured_prompting_intervention",
            route="intervention",
            candidate_claim="Structured prompting improves LLM forecast probabilities beyond bare and placebo prompts.",
            current_effect=(
                f"{structured.get('input_rows')} / 600 rows; expert-training improves paired Brier versus bare "
                f"(delta={fnum(nested(structured_gates, 'expert_training_prompt', 'vs_bare', 'mean_delta_brier'))}, "
                f"sign p={fnum(nested(structured_gates, 'expert_training_prompt', 'vs_bare', 'sign_p'), 4)}) "
                "and versus length-matched placebo "
                f"(delta={fnum(nested(structured_gates, 'expert_training_prompt', 'vs_placebo', 'mean_delta_brier'))}, "
                f"sign p={fnum(nested(structured_gates, 'expert_training_prompt', 'vs_placebo', 'sign_p'), 4)}). "
                "It also beats the same-row low-probability-adjusted bare prompt "
                f"(delta={fnum(nested(structured_external, 'low_probability_adjustment', 'expert_minus_adjusted_bare', 'mean_delta_brier'))}, "
                f"sign p={fnum(nested(structured_external, 'low_probability_adjustment', 'expert_minus_adjusted_bare', 'sign_p'), 4)}), "
                "but does not beat equal-information market rows on the current overlap "
                f"(delta={fnum(nested(structured_external, 'market_controls', 'equal_information_rows', 'expert_minus_market', 'mean_delta_brier'))}, "
                f"sign p={fnum(nested(structured_external, 'market_controls', 'equal_information_rows', 'expert_minus_market', 'sign_p'), 4)}). "
                "Audit-informed and failure-mode-specific prompts do not beat placebo. "
                "The partial Claude validation run does not replicate the expert-training effect: "
                f"{structured_claude_coverage.get('scored_rows', 'NA')} / "
                f"{structured_claude_coverage.get('planned_rows', 'NA')} rows, "
                f"{structured_claude_coverage.get('complete_contract_family_blocks', 'NA')} complete blocks; "
                "expert-training versus bare delta="
                f"{fnum(nested(structured_claude_gates, 'expert_training_prompt', 'vs_bare', 'mean_delta_brier'))}, "
                "versus placebo delta="
                f"{fnum(nested(structured_claude_gates, 'expert_training_prompt', 'vs_placebo', 'mean_delta_brier'))}. "
                "The audit-informed Claude arm is directionally favorable on mean but does not clear sign-test "
                "or source-split checks."
            ),
            source_scope="FRED, Manifold, Polymarket",
            family_scope="completed Gemini run; partial Claude validation is not supportive",
            contract_count=counts["structured_contracts"],
            independent_event_count=f"{counts['structured_contracts']} current contracts",
            same_contract_baseline="bare and length-matched placebo present",
            source_currency_check="source-currency-screened packet",
            label_time_check="required by packet; FRED remains label-time sensitive",
            equal_information_baseline="available only where joined market rows exist",
            market_join="partial; current overlap has lower market Brier",
            human_join="missing",
            prospective_order="retrospective public corpus",
            control_condition="bare and length-matched placebo present",
            source_leave_one_out=(
                "expert-training improves mean Brier in FRED, Manifold, and Polymarket; "
                "audit-informed regresses on FRED and Polymarket; "
                "failure-mode-specific regresses on FRED and Polymarket"
            ),
            family_leave_one_out="partial Claude validation does not reproduce the Gemini expert-training effect",
            falsifier_or_decision_rule="Result fails same-time market or model-family replication checks.",
            gap_label="claim_ready_scoped_intervention_pending_external_controls",
            next_action=(
                "Cite only as a Gemini public-corpus intervention result; preserve the Claude underpowered/below-gate "
                "boundary and prioritize larger same-time market/human overlap or field-validity "
                "work before more model-family spending."
            ),
            evidence_sources=sources(
                "structured-prompting score report",
                "structured-prompt external-control audit",
                evidence(STRUCTURED_PROMPTING_CLAUDE_REPLICATION),
            ),
        ),
        row(
            claim_id="source_general_source_currency",
            route="measurement extension",
            candidate_claim="Source-currency effect generalizes beyond Manifold.",
            current_effect=(
                "Main Manifold panel is strong; FRED vintage repair changes labels and weakens current-label positives; "
                "no local non-Manifold pre/post panel is available yet."
            ),
            source_scope="Manifold supported; FRED diagnostic; Metaculus/other sources blocked by data access",
            family_scope="multi-family where calls exist",
            contract_count="80 matched Manifold contracts plus FRED diagnostics",
            independent_event_count="requires source-specific event-family cap",
            same_contract_baseline="partial",
            source_currency_check="present on main panel",
            label_time_check="present for FRED diagnostics",
            equal_information_baseline="separate market-control check",
            market_join="partial",
            human_join="missing",
            prospective_order="not required for source-currency result, but useful",
            control_condition="not applicable",
            source_leave_one_out="missing for source-general claim",
            family_leave_one_out="partial",
            falsifier_or_decision_rule="Non-Manifold matched pre/post panel erases effect after label-time repair.",
            gap_label="needs_external_acquisition",
            next_action="Acquire non-Manifold matched pre/post rows before more similar model calls.",
            evidence_sources=sources("second-source data audit", "FRED vintage rescore"),
        ),
        row(
            claim_id="family_allocation_headroom",
            route="controlled use candidate",
            candidate_claim="Observable features can recover best-family headroom.",
            current_effect="Best-family-in-hindsight headroom exists, but current observable allocation rules do not recover it safely.",
            source_scope="public-domain panels",
            family_scope="five families",
            contract_count="varies by complete-family panel",
            independent_event_count="not globally de-duplicated",
            same_contract_baseline="raw/low-probability-corrected/family comparisons",
            source_currency_check="required for future use",
            label_time_check="required where official-data rows appear",
            equal_information_baseline="needed for market additivity",
            market_join="partial",
            human_join="missing",
            prospective_order="missing",
            control_condition="not applicable",
            source_leave_one_out="current rules fail or remain weak",
            family_leave_one_out="partial",
            falsifier_or_decision_rule="Predeclared allocator fails raw/calibrated/market controls after cost.",
            gap_label="diagnostic_headroom_only",
            next_action="Use an external reviewer, market, web, or human source before another model-only self-revision packet.",
            evidence_sources=sources("paper-readiness audit", "paper-coherence audit"),
        ),
        row(
            claim_id="prompt_self_repair_negative_control",
            route="negative control",
            candidate_claim="Generic reflection, action framing, and self-revision are not reliable forecast improvers.",
            current_effect="Prompt-intervention and self-revision families fail or regress against controls in current audits.",
            source_scope="public-domain and low-overlap diagnostics",
            family_scope="multiple closed families",
            contract_count="varies by packet",
            independent_event_count="not globally de-duplicated",
            same_contract_baseline="present in several packets",
            source_currency_check="partial",
            label_time_check="partial",
            equal_information_baseline="usually missing",
            market_join="usually missing",
            human_join="missing",
            prospective_order="mostly retrospective",
            control_condition="placebo present in strongest prompt packet",
            source_leave_one_out="partial",
            family_leave_one_out="partial",
            falsifier_or_decision_rule="New predeclared intervention beats bare/placebo/calibrated controls with source-by-source checks.",
            gap_label="negative_claim_ready_scoped",
            next_action="Keep as negative-control evidence; avoid more model-only prompt variants.",
            evidence_sources=sources("paper-readiness audit", "structured-prompting score report"),
        ),
        row(
            claim_id="field_wide_benchmark_validity_failure",
            route="field-wide measurement",
            candidate_claim="Published/current LLM forecasting benchmarks frequently lack row-level validity checks that can change conclusions.",
            current_effect=(
                "This program shows row-level validity failures and market-control reversals; "
                "the Halawi date-distribution warning is locally summarized, and the 12-route source inventory "
                "identifies ForecastBench as the high-access scored forecast route and PredictionMarketBench "
                "as a high-access replay-row route, while PolyBench is medium-access pending database "
                "acquisition. The local "
                "ForecastBench row-schema pilot inspects 500 rows, finds 475 core-validity rows and 250 "
                "timestamped same-contract market rows. The public ForecastBench score audit scores "
                f"{forecastbench_score.get('forecast_files_scored', 'NA')} processed forecast files over "
                f"{forecastbench_score.get('unique_scored_row_keys', 'NA')} unique resolved row keys; "
                f"{forecastbench_score.get('files_with_market_slice', 'NA')} files have a same-information "
                "market slice and only "
                f"{forecastbench_score.get('files_beating_market_baseline', 'NA')} beat the prior-day "
                "market baseline. The median file-level market-slice delta is "
                f"{forecastbench_score.get('median_market_delta_forecast_minus_baseline', 'NA')}. "
                "A separate 2024 ForecastBench human-comparator audit scores "
                f"{forecastbench_human.get('forecast_files_scored', 'NA')} files over "
                f"{forecastbench_human.get('unique_scored_row_keys', 'NA')} row keys and "
                f"{forecastbench_human.get('unique_event_family_keys', 'NA')} event-family keys; "
                "the human-super and public aggregate files each have 577 resolved non-imputed rows "
                "but only two strict same-information market rows. "
                "A Prophet Arena row-schema pilot fetches "
                f"{nested(prophet_arena_pilot, 'summary', 'task_rows') or 'NA'} public task rows across "
                f"{nested(prophet_arena_pilot, 'summary', 'datasets_checked') or 'NA'} sample releases, with "
                f"{nested(prophet_arena_pilot, 'summary', 'resolved_rows') or 'NA'} resolved rows, but includes "
                "0 submitted model forecast probabilities and 0 same-time market or human baseline probabilities; "
                "the same pilot checks "
                f"{nested(prophet_arena_pilot, 'summary', 'public_repositories_checked') or 'NA'} public AI Prophet "
                "repositories and finds "
                f"{nested(prophet_arena_pilot, 'summary', 'public_prophet_arena_trace_archives_found') or 0} "
                "public Prophet Arena submission or leaderboard trace archives. "
                "The PolyBench source-access pilot verifies repository/schema access but reports "
                f"{polybench_source.get('dataset_download_status', 'NA')}, so PolyBench is not yet "
                "a scored second public benchmark here. The PredictionMarketBench row-schema pilot "
                f"loads {predictionmarketbench.get('episodes', 'NA')} replay episodes, "
                f"{predictionmarketbench.get('settled_tickers', 'NA')} settled tickers, "
                f"{predictionmarketbench.get('orderbook_rows', 'NA')} orderbook rows, and "
                f"{predictionmarketbench.get('market_baseline_rows', 'NA')} same-time market-baseline "
                "rows, but includes 0 stored model forecast rows."
            ),
            source_scope="12-route source inventory plus ForecastBench row-schema/score audit, Prophet Arena row-schema and public trace-surface pilot, PredictionMarketBench row-schema pilot, and PolyBench source-access pilot; more scored benchmark families still needed",
            family_scope="not model-family dependent",
            contract_count="missing",
            independent_event_count="missing",
            same_contract_baseline="missing across field",
            source_currency_check="missing across field",
            label_time_check="missing across field",
            equal_information_baseline="missing across field",
            market_join="missing across field",
            human_join="partial ForecastBench human aggregate files, but broad same-information human comparisons still missing",
            prospective_order="varies by benchmark",
            control_condition="not applicable",
            source_leave_one_out="missing",
            family_leave_one_out="not applicable",
            falsifier_or_decision_rule="External benchmark audit shows validity checks rarely change conclusions.",
            gap_label="field_audit_needed",
            next_action="Obtain stored model or agent forecast traces for Prophet Arena and replay benchmarks, acquire the PolyBench database, and repeat score-audit treatment on additional public benchmark families before claiming field-wide prevalence.",
            evidence_sources=sources(
                "paper-coherence audit",
                "paper-readiness audit",
                evidence(
                    FIELD_WIDE_PROTOCOL,
                    FIELD_WIDE_SOURCE_INVENTORY,
                    FORECASTBENCH_ROW_SCHEMA_PILOT,
                    FORECASTBENCH_SCORE_AUDIT,
                    FORECASTBENCH_HUMAN_COMPARATOR_AUDIT,
                    PROPHET_ARENA_ROW_SCHEMA_PILOT,
                    POLYBENCH_SOURCE_PILOT,
                    PREDICTIONMARKETBENCH_ROW_SCHEMA_PILOT,
                    FIELD_WIDE_LOCAL_EVIDENCE,
                ),
            ),
        ),
        row(
            claim_id="private_low_overlap_generality",
            route="reproducibility",
            candidate_claim="Low-overlap elicitation findings generalize externally.",
            current_effect="Low-overlap diagnostics are informative but private and confounded with length/novelty/source.",
            source_scope="private low-overlap corpus",
            family_scope="five families in existing diagnostics",
            contract_count=15,
            independent_event_count=15,
            same_contract_baseline="present inside private corpus",
            source_currency_check="not the central issue",
            label_time_check="not the central issue",
            equal_information_baseline="missing",
            market_join="not applicable",
            human_join="missing",
            prospective_order="not applicable",
            control_condition="varies",
            source_leave_one_out="not applicable",
            family_leave_one_out="partial",
            falsifier_or_decision_rule="Public niche-domain replication fails or de-confounded design attributes effect to length/source only.",
            gap_label="reproducibility_gap",
            next_action="Release sanitized/substitute public niche corpus before claiming external generality.",
            evidence_sources=sources("paper-coherence audit"),
        ),
    ]

    summary = {
        "schema": "gp245-claim-gap-matrix-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db": rel(db),
        "db_counts": counts,
        "program_verdict": readiness_verdict,
        "central_claim": coherence_verdict.get("central_claim"),
        "rows": rows,
    }
    return summary


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def render_md(report: dict[str, Any]) -> str:
    rows = report["rows"]
    labels: dict[str, int] = {}
    for item in rows:
        labels[item["gap_label"]] = labels.get(item["gap_label"], 0) + 1
    lines = [
        "# GP-245 Evidence Matrix",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Database: `{report['db']}`",
        f"- Central claim: {report.get('central_claim')}",
        "",
        "Status counts:",
    ]
    for label, count in sorted(labels.items()):
        lines.append(f"- {STATUS_LABELS.get(label, label.replace('_', ' '))}: `{count}`")
    lines.extend(
        [
            "",
            "## Evidence Table",
            "",
            "| Candidate result | Route | Status | Current evidence | Missing checks and next action |",
            "|---|---|---|---|---|",
        ]
    )
    for item in rows:
        missing_bits = []
        for key in (
            "human_join",
            "prospective_order",
            "source_leave_one_out",
            "family_leave_one_out",
            "equal_information_baseline",
        ):
            value = item.get(key, "")
            if value and value not in {"present", "not applicable"}:
                missing_bits.append(f"{CHECK_LABELS.get(key, key.replace('_', ' '))}: {value}")
        missing_bits.append(f"next: {item['next_action']}")
        lines.append(
            "| "
            + " | ".join(
                [
                    item["candidate_claim"],
                    item["route"],
                    STATUS_LABELS.get(item["gap_label"], item["gap_label"].replace("_", " ")),
                    item["current_effect"].replace("|", "/"),
                    "<br>".join(bit.replace("|", "/") for bit in missing_bits),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Claim Details",
            "",
        ]
    )
    for item in rows:
        lines.extend(
            [
                f"### {item['candidate_claim']}",
                "",
                f"- Status: {STATUS_LABELS.get(item['gap_label'], item['gap_label'].replace('_', ' '))}",
                f"- Decision rule: {item['falsifier_or_decision_rule']}",
                f"- Next action: {item['next_action']}",
                f"- Evidence sources: {item['evidence_sources']}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    report = build_matrix(args.db)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "claim_gap_matrix.json"
    csv_path = args.out_dir / "claim_gap_matrix.csv"
    md_path = args.out_dir / "claim_gap_matrix.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, report["rows"])
    md_path.write_text(render_md(report) + "\n", encoding="utf-8")
    print(json.dumps({"json": rel(json_path), "csv": rel(csv_path), "md": rel(md_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
