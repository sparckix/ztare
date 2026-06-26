#!/usr/bin/env python3
"""Build the paper-level evidence map for the forecasting calibration study.

No model calls and no database mutation. This report is a guard against turning
the paper into an experiment catalogue: each evidence family is assigned a role
in the manuscript, a paper placement, and a reason for inclusion or exclusion.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROJECT = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_OUT = PROJECT / "paper_alignment_v1/workspace"


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO))
    except ValueError:
        return str(path)


def row(
    *,
    lane: str,
    paper_role: str,
    placement: str,
    include_status: str,
    evidence: str,
    reason: str,
    boundary: str,
    evidence_records: list[str],
) -> dict[str, Any]:
    return {
        "lane": lane,
        "paper_role": paper_role,
        "placement": placement,
        "include_status": include_status,
        "evidence": evidence,
        "reason": reason,
        "boundary": boundary,
        "evidence_records": evidence_records,
    }


def build_report() -> dict[str, Any]:
    rows = [
        row(
            lane="recent_forecasting_benchmark_positioning",
            paper_role="related-work boundary",
            placement="main text: implications for published forecasting literature",
            include_status="include",
            evidence=(
                "Halawi 2024 and ForecastBench establish future-event benchmark "
                "framing; AIA Forecaster reports superforecaster-level ForecastBench "
                "performance and additive market information; Reppo, Prediction "
                "Arena, PolyBench, Foresight Arena, PredictionMarketBench, and "
                "MarketBench move the field toward live markets, timestamped market "
                "states, proper scores, execution-realistic replay, and market-based "
                "coordination."
            ),
            reason=(
                "This literature makes the paper's contribution sharper: it is not "
                "another trading-agent benchmark, but the row-validity layer required "
                "before model, market, and human comparisons can be interpreted as "
                "forecasting evidence."
            ),
            boundary=(
                "Cite as positioning, not as evidence that this study beats live "
                "market agents or human forecasters."
            ),
            evidence_records=[
                "papers/llm-forecast-calibration-cross-corpus/refs.bib",
                "papers/llm-forecast-calibration-cross-corpus/main.tex",
            ],
        ),
        row(
            lane="source_currency_and_label_time_validity",
            paper_role="main contribution",
            placement="main text: abstract, introduction, re-audit discipline",
            include_status="include",
            evidence=(
                "Matched Manifold Stage-B panel: 80 contracts / 240 tool-free calls; "
                "post-minus-pre Brier +0.191098, paired-stratum delta +0.2155, "
                "permutation p=0.0004. Stage-C partial market-prior repair joins 51 "
                "contracts; missing-band sensitivity remains positive."
            ),
            reason=(
                "This is the cleanest general lesson: a row that was fair for one "
                "model generation can stop being fair for a later generation."
            ),
            boundary=(
                "Candidate measurement result, not a source-general superiority claim. "
                "FRED vintage repair and Polymarket matched-stratum stress keep the "
                "claim scoped."
            ),
            evidence_records=[
                "cutoff_validity_v1/workspace",
                "law_validation_v1/workspace/paper_readiness_exhaustion_audit.md",
                "forecaster_skill_calibration_v1/workspace/research_log.md#source-currency-stage-b",
            ],
        ),
        row(
            lane="equal_information_market_baselines",
            paper_role="main falsification boundary",
            placement="main text: equal-information comparison and limits",
            include_status="include",
            evidence=(
                "103 external market baseline rows; 52 equal-information rows across "
                "Polymarket and Manifold. The completed 24-contract Polymarket replacement slice has Claude, "
                "Codex, Gemini, and DeepSeek all losing to Polymarket; four-family "
                "panel Brier 0.267758 vs market 0.072964, paired p=0.0068. "
                "The 24-contract Manifold fill validates all requested rows and gives "
                "market Brier 0.160977 vs a five-family low-stake model-panel Brier 0.198723 "
                "(panel-minus-market +0.037746, paired p=0.5431), a lower-market-Brier but "
                "inconclusive second-source comparison."
            ),
            reason=(
                "A strong paper is allowed to contain controls that do not support the model panel. This result "
                "prevents the source-currency result from being misread as LLMs "
                "beating markets."
            ),
            boundary=(
                "Two-source same-information market control, but not predeclared or "
                "powered enough for broad LLM superiority over markets/humans."
            ),
            evidence_records=[
                "cutoff_validity_v1/workspace/equal_information_replacement_score_2026_06_15/equal_information_replacement_score.md",
                "truth_continuation_v1/workspace/equal_information_baseline_void_2026_06_03/equal_information_baseline_void_report.md",
                "truth_continuation_v1/workspace/independent_equal_information_source_audit_2026_06_15/independent_equal_information_source_audit.md",
                "truth_continuation_v1/workspace/manifold_equal_information_reclassification_audit_2026_06_15/manifold_equal_information_reclassification_audit.md",
                "cutoff_validity_v1/workspace/non_polymarket_equal_information_export_packet_2026_06_15/non_polymarket_equal_information_export_packet.md",
                "cutoff_validity_v1/workspace/non_polymarket_equal_information_export_packet_2026_06_15/manifold_history_fill_2026_06_15/non_polymarket_equal_information_result_acquire.md",
                "cutoff_validity_v1/workspace/non_polymarket_equal_information_export_packet_2026_06_15/manifold_history_ingest_2026_06_15/non_polymarket_equal_information_result_ingest.md",
                "cutoff_validity_v1/workspace/non_polymarket_equal_information_export_packet_2026_06_15/manifold_history_score_2026_06_15/non_polymarket_equal_information_score.md",
            ],
        ),
        row(
            lane="confident_no_calibration",
            paper_role="point-probability use after source-currency screening",
            placement="main text: controlled-use synthesis and calibration consequence",
            include_status="include_controlled",
            evidence=(
                "Low-probability calibration improves forward-looking rows that pass the source-currency check in the "
                "right slice, while a source-currency stress audit shows regression "
                "on pre-cutoff/source-visible rows."
            ),
            reason=(
                "This gives the paper one practical consequence without pretending "
                "that a hand rule is universal."
            ),
            boundary="Use as a live calibration rule after source-currency screening, not as a retrospective benchmark correction.",
            evidence_records=[
                "forecaster_skill_calibration_v1/workspace/research_log.md#confident-no-source-currency-audit",
                "public/CLAIM_SUMMARY.md",
            ],
        ),
        row(
            lane="pairwise_contrastive_ranking",
            paper_role="controlled ranking use",
            placement="main text: controlled-use synthesis; fuller details in appendix",
            include_status="include_controlled",
            evidence=(
                "Four-family source-balanced pairwise packet supports ranking "
                "utility; translated probability improves against raw in one "
                "cross-packet direction but remains below single-contract probability evidence bars "
                "and lacks broad market/human control."
            ),
            reason=(
                "It is interesting and connects to model-use policy, but it remains "
                "secondary to the measurement-validity result."
            ),
            boundary=(
                "Pairwise/tournament use only until prospective market-freeze outcomes "
                "resolve and raw/low-probability/market controls clear."
            ),
            evidence_records=[
                "forecaster_skill_calibration_v1/workspace/research_log.md#pairwise-ranking-production-readiness",
                "forecaster_skill_calibration_v1/workspace/research_log.md#prospective-market-freeze-packet",
            ],
        ),
        row(
            lane="integrated_controlled_use_argument",
            paper_role="main synthesis",
            placement="main text: dedicated controlled-use section",
            include_status="include",
            evidence=(
                "The controlled-use audit supports one integrated paper: the low-probability rule is "
                "the current calibration view after source-currency screening; pairwise ranking survives "
                "as relative-judgment evidence; structured evidence fields remain mixed; "
                "family-choice headroom is real but "
                "not recovered by simple allocation rules; prompt-intervention/self-repair controls mostly fail."
            ),
            reason=(
                "This turns the market-control result into the premise for a stricter "
                "claim: raw panels are not enough, but controlled interfaces can test "
                "which model outputs remain useful."
            ),
            boundary=(
                "Controlled use of model output, not LLM superiority, not validated "
                "prompt-only improvement, and not a reliable family-selection rule."
            ),
            evidence_records=[
                "paper_alignment_v1/workspace/controlled_use_audit.md",
                "public/CLAIM_SUMMARY.md",
                "papers/llm-forecast-calibration-cross-corpus/main.tex",
            ],
        ),
        row(
            lane="before_scoring_counterexplanation_design",
            paper_role="claim-test guard",
            placement="main text: forecast-row validity estimand; reproducibility table; companion benchmark blueprint",
            include_status="include",
            evidence=(
                "Each planned positive result names the simpler explanation it must rule "
                "out before scoring: mismatched comparator timing, source visibility, "
                "label vintage, prompt length, placebo framing, pair orientation, source mix, "
                "or denominator choice."
            ),
            reason=(
                "This turns the inversion habit into a paper-level decision rule: a result "
                "can remain diagnostic even when it cannot support a broader performance claim."
            ),
            boundary=(
                "Design rule for future and pending packets; not an extra positive result "
                "and not an explanation added after scored rows are known."
            ),
            evidence_records=[
                "paper_alignment_v1/workspace/prospective_counterexplanation_design_2026_06_17/prospective_counterexplanation_design_audit.json",
                "paper_alignment_v1/workspace/forecast_row_validity_benchmark_blueprint_2026_06_17/forecast_row_validity_benchmark_blueprint.json",
                "papers/llm-forecast-calibration-cross-corpus/main.tex",
            ],
        ),
        row(
            lane="manuscript_scope_hygiene",
            paper_role="coherence guard",
            placement="front evidence map and removal of unrelated proof-audit detour",
            include_status="include",
            evidence=(
                "The manuscript now states a front evidence map and removes the separate "
                "Lean/proof-audit case study from the forecasting paper."
            ),
            reason=(
                "A submission-facing forecasting paper loses focus when reviewers have to "
                "switch domains without a necessary forecasting example."
            ),
            boundary=(
                "The proof-audit work can live in another methods note; it does not "
                "carry argument weight in GP-245."
            ),
            evidence_records=[
                "papers/llm-forecast-calibration-cross-corpus/main.tex",
                "papers/llm-forecast-calibration-cross-corpus/draft.md",
            ],
        ),
        row(
            lane="front_loaded_core_results",
            paper_role="readability guard",
            placement="main text: introduction figure plus core empirical results section",
            include_status="include",
            evidence=(
                "The manuscript now puts an evidence-flow figure and a compact core-results "
                "table before the diagnostic sections: source-currency, equal-information "
                "market controls, low-probability calibration, pairwise ranking, and "
                "prompt-intervention/self-repair boundaries."
            ),
            reason=(
                "A reviewer sees the paper's main claim before the long channel and "
                "bias diagnostics."
            ),
            boundary=(
                "The table is an argument guide, not a substitute for the "
                "later evidence records and score details."
            ),
            evidence_records=[
                "papers/llm-forecast-calibration-cross-corpus/main.tex",
                "papers/llm-forecast-calibration-cross-corpus/draft.md",
            ],
        ),
        row(
            lane="applied_calibration_and_allocation",
            paper_role="policy-consequence guard",
            placement="main text: compact applied calibration and allocation section",
            include_status="include_controlled",
            evidence=(
                "Universal patterns, composed adjustment, low-probability calibration, and "
                "pairwise ranking are now organized by evidence grade: calibration after source-currency screening, "
                "ranking/translation, and allocation rules with unrecovered "
                "best-family-in-hindsight gain."
            ),
            reason=(
                "This prevents the applied section from reading as an experiment log "
                "and keeps the paper explicit about what is usable versus diagnostic."
            ),
            boundary=(
                "Low-probability calibration remains a rule for rows that pass source-currency checks; pairwise ranking remains "
                "ranking evidence; allocation rules remain prospective until they beat controls."
            ),
            evidence_records=[
                "papers/llm-forecast-calibration-cross-corpus/main.tex",
                "papers/llm-forecast-calibration-cross-corpus/draft.md",
            ],
        ),
        row(
            lane="reaudit_evidence_compression",
            paper_role="validity audit readability",
            placement="main text: source-currency, label-time, and equal-information audit table",
            include_status="include",
            evidence=(
                "The long chronological audit trail is now compressed into source families for "
                "Manifold source currency, Manifold market stress, Polymarket stress, "
                "Polymarket equal-information replacement, Manifold equal-information "
                "fill, FRED label-time, and Metaculus access."
            ),
            reason=(
                "The paper needs the evidence records and boundaries, not a chronological "
                "acquisition diary."
            ),
            boundary=(
                "Compact table preserves scores and limits; detailed acquisition "
                "records remain in workspace outputs."
            ),
            evidence_records=[
                "papers/llm-forecast-calibration-cross-corpus/main.tex",
                "papers/llm-forecast-calibration-cross-corpus/draft.md",
                "truth_continuation_v1/workspace/independent_equal_information_source_audit_2026_06_15/independent_equal_information_source_audit.md",
            ],
        ),
        row(
            lane="compressed_insight_preservation",
            paper_role="appendix evidence ledger",
            placement="appendix: evidence ledger for compressed diagnostics",
            include_status="include",
            evidence=(
                "The appendix now lists the compressed experiment families and the "
                "specific insight retained from each: uncertainty channels, "
                "self-assessed channel choice, universal calibration regularities, family-choice headroom, "
                "pairwise ranking, source/label-time audits, and prompt-intervention/self-repair negatives."
            ),
            reason=(
                "This keeps the main text readable without losing the study's "
                "experimental coverage or making compression look like deletion."
            ),
            boundary=(
                "Ledger is a map to evidence families, not a replacement for raw "
                "records, scores, or reproducibility evidence."
            ),
            evidence_records=[
                "papers/llm-forecast-calibration-cross-corpus/main.tex",
                "papers/llm-forecast-calibration-cross-corpus/draft.md",
            ],
        ),
        row(
            lane="omitted_and_deferred_work_coverage",
            paper_role="appendix coverage guard",
            placement="appendix: coverage audit for omitted or deferred work",
            include_status="include",
            evidence=(
                "The appendix now records why prompt-intervention variants, objective-effort "
                "calibration, proof-audit workflow findings, low-overlap retests, fitted "
                "allocation rules, prospective market-freeze packets, and deconfounded-corpus design "
                "are excluded or deferred rather than silently dropped."
            ),
            reason=(
                "This preserves insight from the research log and deferred-work list without "
                "turning the main paper into a chronological catalog."
            ),
            boundary=(
                "Coverage table is not a new evidence claim; it is a map of exclusions, "
                "sibling work, and continuation tests."
            ),
            evidence_records=[
                "forecaster_skill_calibration_v1/workspace/research_log.md",
                "forecaster_skill_calibration_v1/workspace/pilot_queue.md",
                "papers/llm-forecast-calibration-cross-corpus/main.tex",
            ],
        ),
        row(
            lane="law2_uncertainty_channels",
            paper_role="diagnostic support",
            placement="main text: compressed elicitation diagnostics section",
            include_status="include_controlled",
            evidence=(
                "Worry, bid-ask spread, frequency framing, self-predicted Brier, "
                "multi-channel fits, and conditional family-allocation probes are compressed "
                "into one diagnostic section. The evidence supports conditional "
                "family/source signal, while channel-only decision rules fail larger "
                "leave-one-out checks or source controls."
            ),
            reason=(
                "The channel evidence explains why family-specific forecasting "
                "outputs are not interchangeable, without letting diagnostics "
                "dominate the paper's main validity-and-controlled-use argument."
            ),
            boundary="Diagnostic pattern, not an applied probability transform.",
            evidence_records=[
                "law_validation_v1/workspace/law_readiness_report.json",
                "forecaster_skill_calibration_v1/workspace/research_log.md#uncertainty-channel-diagnostics",
            ],
        ),
        row(
            lane="bias_transfer_taxonomy",
            paper_role="secondary theory, not main claim",
            placement="main text: compressed secondary diagnostics section",
            include_status="compress",
            evidence=(
                "The bias-transfer taxonomy is useful, the prompt-stability "
                "audits warn against family-general allocation, and the anti-bias "
                "collapse pattern was weakened or scoped by raw-gap controls. This "
                "material is now compressed into one secondary diagnostics section."
            ),
            reason=(
                "The paper needs the warning, not a second theory paper. Keep only "
                "what explains source/family sensitivity and the failure of easy "
                "simple prompt-improvement stories."
            ),
            boundary="Taxonomy and caveat only; no causal prompt-improvement result.",
            evidence_records=[
                "anti_bias_collapse_v1/workspace",
                "law_validation_v1/workspace/paper_readiness_exhaustion_audit.md",
            ],
        ),
        row(
            lane="fred_yfinance_official_data",
            paper_role="negative label-time lesson",
            placement="appendix or limitation paragraph",
            include_status="appendix",
            evidence=(
                "FRED/yfinance adds source breadth, but vintage timing repair flips "
                "the optimistic current-label readout on scoreable rows."
            ),
            reason=(
                "This strengthens the label-time-validity argument without being a "
                "market/human baseline."
            ),
            boundary="Official-data source-currency analysis only; not a substitute for Metaculus or market baselines.",
            evidence_records=[
                "cutoff_validity_v1/workspace/fred_vintage_bulk_rescore_2026_06_04/fred_vintage_rescore.json",
                "public/CLAIM_SUMMARY.md",
            ],
        ),
        row(
            lane="prompt_intervention_action_frames_and_same_model_self_repair",
            paper_role="excluded from main claim",
            placement="appendix table or omit",
            include_status="exclude_from_main",
            evidence=(
                "Broad action framing, unguarded self-repair, and diagnostic-triggered "
                "allocation failed applied stress tests against raw/low-probability/placebo/source controls."
            ),
            reason="These are useful negative controls but they do not belong in the headline argument.",
            boundary="Reopen only with a genuinely new information source or predefined success/failure criterion.",
            evidence_records=[
                "forecaster_skill_calibration_v1/workspace/research_log.md#prompt-intervention-negative-controls",
                "forecaster_skill_calibration_v1/workspace/findings_completeness_ledger.md#prompt-intervention-and-self-repair",
            ],
        ),
    ]

    include_counts: dict[str, int] = {}
    for item in rows:
        include_counts[item["include_status"]] = include_counts.get(item["include_status"], 0) + 1

    return {
        "schema": "gp245-paper-coherence-audit-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": {
            "central_claim": (
                "Current equal-information market controls do not support raw LLM panel "
                "superiority, but some model outputs retain limited value after "
                "source-currency, label-time, calibration, ranking, and family/source checks."
            ),
            "paper_shape": (
                "Integrated measurement-and-controlled-use paper: validity checks are the "
                "foundation, and the applied result is a narrower set of calibrated "
                "and ranking-based uses."
            ),
            "main_text_rule": (
                "Main text gets source validity, equal-information market controls, "
                "and only the supported controlled-use results with explicit evidence records and limits."
            ),
            "broad_claim_ready": False,
            "next_test": "Use a prospective or larger source-balanced packet before any broad market/human superiority claim.",
        },
        "include_counts": include_counts,
        "rows": rows,
    }


def render_md(report: dict[str, Any]) -> str:
    evidence_family_labels = {
        "recent_forecasting_benchmark_positioning": "Recent forecasting benchmark positioning",
        "source_currency_and_label_time_validity": "Source and label-time validity",
        "equal_information_market_baselines": "Equal-information market baselines",
        "confident_no_calibration": "Low-probability calibration",
        "pairwise_contrastive_ranking": "Pairwise ranking",
        "integrated_controlled_use_argument": "Controlled-use synthesis",
        "before_scoring_counterexplanation_design": "Before-scoring counter-explanation design",
        "manuscript_scope_hygiene": "Manuscript scope",
        "front_loaded_core_results": "Front-loaded core results",
        "applied_calibration_and_allocation": "Applied calibration and allocation",
        "reaudit_evidence_compression": "Audit compression",
        "compressed_insight_preservation": "Compressed insight coverage",
        "omitted_and_deferred_work_coverage": "Omitted and deferred work",
        "law2_uncertainty_channels": "Uncertainty-channel diagnostics",
        "bias_transfer_taxonomy": "Bias-transfer diagnostics",
        "fred_yfinance_official_data": "Official-data label timing",
        "prompt_intervention_action_frames_and_same_model_self_repair": "Prompt intervention controls",
    }
    status_labels = {
        "include": "Include",
        "include_controlled": "Include with limits",
        "compress": "Compress",
        "appendix": "Appendix",
        "exclude_from_main": "Exclude from main claim",
    }

    def family_label(key: str) -> str:
        return evidence_family_labels.get(key, key.replace("_", " ").title())

    def status_label(key: str) -> str:
        return status_labels.get(key, key.replace("_", " "))

    verdict = report["verdict"]
    lines = [
        "# GP-245 Paper Coherence Audit",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Central claim: {verdict['central_claim']}",
        f"- Paper shape: {verdict['paper_shape']}",
        f"- Main-text rule: {verdict['main_text_rule']}",
        f"- Broad claim ready: `{verdict['broad_claim_ready']}`",
        f"- Next test: {verdict['next_test']}",
        f"- Include counts: `{report['include_counts']}`",
        "",
        "## Evidence Map",
        "",
        "| evidence family | role | placement | status | boundary |",
        "|---|---|---|---|---|",
    ]
    for item in report["rows"]:
        lines.append(
            "| {family} | {role} | {placement} | {status} | {boundary} |".format(
                family=family_label(item["lane"]),
                role=item["paper_role"],
                placement=item["placement"],
                status=status_label(item["include_status"]),
                boundary=item["boundary"],
            )
        )
    lines.extend(["", "## Details", ""])
    for item in report["rows"]:
        lines.extend(
            [
                f"### {family_label(item['lane'])}",
                "",
                f"- Status: {status_label(item['include_status'])}",
                f"- Evidence: {item['evidence']}",
                f"- Reason: {item['reason']}",
                f"- Boundary: {item['boundary']}",
                "- Source records are retained in the JSON sidecar.",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build_report()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "paper_coherence_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "paper_coherence_audit.md").write_text(
        render_md(report) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": report["schema"],
                "verdict": report["verdict"],
                "include_counts": report["include_counts"],
                "out_dir": repo_relative(args.out_dir),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
