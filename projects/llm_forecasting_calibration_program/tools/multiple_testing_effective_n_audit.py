#!/usr/bin/env python3
"""Consolidated multiplicity and denominator audit for GP-245.

The manuscript reports many small, related comparisons. This audit puts the
tests used in the paper in one family, records the effective denominator used
for each result, applies a global Benjamini-Hochberg correction, and reports a
Benjamini-Yekutieli robustness column for arbitrary dependence. It reads stored
score reports only; it does not run models or rescore forecasts.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_OUT_DIR = PROGRAM / "paper_alignment_v1/workspace/multiple_testing_effective_n_2026_06_20"

SCORES = {
    "source_currency": PROGRAM / "cutoff_validity_v1/workspace/cutoff_stage_b_score_report.json",
    "polymarket_market": PROGRAM
    / "cutoff_validity_v1/workspace/equal_information_replacement_score_2026_06_15"
    / "equal_information_replacement_score.json",
    "manifold_market": PROGRAM
    / "cutoff_validity_v1/workspace/non_polymarket_equal_information_export_packet_2026_06_15"
    / "manifold_history_score_2026_06_15/non_polymarket_equal_information_score.json",
    "manifold_freeze0": PROGRAM
    / "paper_alignment_v1/workspace/non_polymarket_equal_information_score_freeze0_2026_06_20"
    / "non_polymarket_equal_information_score.json",
    "manifold_freeze1": PROGRAM
    / "paper_alignment_v1/workspace/non_polymarket_equal_information_score_freeze1_2026_06_20"
    / "non_polymarket_equal_information_score.json",
    "manifold_freeze2": PROGRAM
    / "paper_alignment_v1/workspace/non_polymarket_equal_information_score_freeze2_2026_06_20"
    / "non_polymarket_equal_information_score.json",
    "manifold_freeze7": PROGRAM
    / "paper_alignment_v1/workspace/non_polymarket_equal_information_score_freeze7_2026_06_20"
    / "non_polymarket_equal_information_score.json",
    "low_prob_policy": PROGRAM
    / "forecaster_skill_calibration_v1/workspace/f100_calibrator_audit_2026_06_04_policy_scoreable.json",
    "low_prob_source_stress": PROGRAM
    / "forecaster_skill_calibration_v1/workspace/f100_source_currency_audit_2026_06_03.json",
    "pairwise": PROGRAM
    / "forecaster_skill_calibration_v1/workspace/f47_source_balanced_consumer_score_2026_06_03.json",
    "pairwise_external": PROGRAM
    / "forecaster_skill_calibration_v1/workspace/f47_external_bar_score_2026_06_03.json",
    "gemini_prompt": PROGRAM
    / "structured_metacognition_v1/workspace/structured_metacognition_public_v1_score_report.json",
    "gemini_market": PROGRAM
    / "structured_metacognition_v1/workspace/structured_metacognition_public_v1_external_control_report.json",
    "claude_prompt": PROGRAM
    / "structured_metacognition_v1/workspace/structured_metacognition_public_v1_claude_replication_score_report.json",
    "codex_deepseek_prompt": PROGRAM
    / "structured_metacognition_v1/workspace/codex_deepseek_replication_v2_score"
    / "structured_metacognition_public_v1_codex_deepseek_replication_v2_score_report.json",
}

CSV_FIELDS = [
    "claim_id",
    "hypothesis",
    "evidence_track",
    "result_class",
    "pre_post_hoc_status",
    "effective_unit",
    "effective_n",
    "effect_size",
    "raw_p",
    "bh_fdr_q_global",
    "by_fdr_q_global",
    "correction_family",
    "included_in_global_fdr",
    "interpretation",
    "source_path",
]


@dataclass
class AuditRow:
    claim_id: str
    hypothesis: str
    evidence_track: str
    result_class: str
    pre_post_hoc_status: str
    effective_unit: str
    effective_n: str
    effect_size: str
    raw_p: float | None
    correction_family: str
    included_in_global_fdr: bool
    interpretation: str
    source_path: str
    bh_fdr_q_global: float | None = None
    by_fdr_q_global: float | None = None


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "NA"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def add_row(rows: list[AuditRow], **kwargs: Any) -> None:
    rows.append(AuditRow(**kwargs))


def low_p_policy_row(rows: list[AuditRow]) -> None:
    data = read_json(SCORES["low_prob_policy"])
    raw = ((data.get("policies") or {}).get("raw_mean_panel") or {})
    paired = raw.get("paired_vs_confident_no") or {}
    add_row(
        rows,
        claim_id="low_probability_rule_raw_vs_tempered",
        hypothesis="On documented public rows, tempering very small panel probabilities improves Brier versus the raw mean panel.",
        evidence_track="calibration",
        result_class="exploratory",
        pre_post_hoc_status="selected within the program; requires independent replication",
        effective_unit="contract panel",
        effective_n=str(raw.get("n", data.get("n_panels", "NA"))),
        effect_size=f"raw-minus-tempered Brier {fmt(raw.get('delta_vs_confident_no'))}",
        raw_p=paired.get("p_value"),
        correction_family="global_reported_tests",
        included_in_global_fdr=True,
        interpretation="Positive but selected after earlier calibration work; not a universal rule.",
        source_path=rel(SCORES["low_prob_policy"]),
    )


def low_p_stress_rows(rows: list[AuditRow]) -> None:
    data = read_json(SCORES["low_prob_source_stress"])
    for relation, label in [
        ("post_cutoff", "forward-looking rows"),
        ("pre_cutoff", "source-visible/pre-cutoff rows"),
    ]:
        item = ((data.get("by_cutoff_relation") or {}).get(relation) or {})
        paired = item.get("paired_permutation") or {}
        add_row(
            rows,
            claim_id=f"low_probability_rule_source_currency_stress_{relation}",
            hypothesis=f"The low-probability rule behaves differently on {label}.",
            evidence_track="calibration stress",
            result_class="diagnostic",
            pre_post_hoc_status="retrospective stress audit",
            effective_unit="model call, with contract count reported",
            effective_n=f"{item.get('n', 'NA')} calls / {item.get('contracts', 'NA')} contracts",
            effect_size=f"tempered-minus-raw Brier {fmt(item.get('delta_f100_minus_raw'))}",
            raw_p=paired.get("p_value"),
            correction_family="global_reported_tests",
            included_in_global_fdr=True,
            interpretation="The rule helps the forward-looking slice directionally and regresses on source-visible rows.",
            source_path=rel(SCORES["low_prob_source_stress"]),
        )


def market_row(
    rows: list[AuditRow],
    *,
    claim_id: str,
    source_key: str,
    result_class: str,
    pre_post_hoc_status: str,
    interpretation: str,
    comparison_id: str = "v28stake_full__v25_external::low",
) -> None:
    data = read_json(SCORES[source_key])
    if source_key == "polymarket_market":
        summary = data.get("summary") or {}
        paired = summary.get("paired_permutation_model_panel_vs_market") or {}
        effect = (
            f"panel-minus-market Brier {fmt(summary.get('model_panel_mean_p_minus_market_brier'))}; "
            f"panel {fmt(summary.get('model_panel_mean_p_brier'), 3)} vs market "
            f"{fmt(summary.get('mean_market_brier'), 3)}"
        )
        n = summary.get("contract_n", paired.get("n_paired"))
    else:
        score = next(
            (
                item
                for item in (data.get("pilot_scores") or [])
                if item.get("comparison_id") == comparison_id
            ),
            {},
        )
        paired = score.get("paired_permutation_model_panel_vs_market") or {}
        effect = (
            f"panel-minus-market Brier {fmt(score.get('model_panel_minus_market_brier'))}; "
            f"panel {fmt(score.get('model_panel_mean_p_brier'), 3)} vs market "
            f"{fmt(score.get('mean_market_brier_on_common_contracts'), 3)}"
        )
        n = score.get("contracts", paired.get("n_paired"))
    add_row(
        rows,
        claim_id=claim_id,
        hypothesis="Raw model panel does not outperform an equal-information market bar on the same contracts.",
        evidence_track="equal-information market control",
        result_class=result_class,
        pre_post_hoc_status=pre_post_hoc_status,
        effective_unit="contract with same-time market comparator",
        effective_n=str(n),
        effect_size=effect,
        raw_p=paired.get("p_value"),
        correction_family="global_reported_tests",
        included_in_global_fdr=True,
        interpretation=interpretation,
        source_path=rel(SCORES[source_key]),
    )


def prompt_rows(rows: list[AuditRow]) -> None:
    gemini = read_json(SCORES["gemini_prompt"])
    gate = ((gemini.get("condition_gates") or {}).get("expert_training_prompt") or {})
    for key, label in [("vs_bare", "bare prompt"), ("vs_placebo", "length-matched placebo")]:
        item = gate.get(key) or {}
        add_row(
            rows,
            claim_id=f"gemini_expert_training_{key}",
            hypothesis=f"Gemini expert-training prompt improves Brier versus {label}.",
            evidence_track="prompt intervention",
            result_class="exploratory",
            pre_post_hoc_status="selected intervention; completed Gemini packet",
            effective_unit="contract-condition block",
            effective_n=str(item.get("n", "NA")),
            effect_size=f"expert-minus-{label} Brier {fmt(item.get('mean_delta_brier'))}",
            raw_p=item.get("sign_p"),
            correction_family="global_reported_tests",
            included_in_global_fdr=True,
            interpretation="A Gemini-specific result, not a general prompting method.",
            source_path=rel(SCORES["gemini_prompt"]),
        )

    external = read_json(SCORES["gemini_market"])
    adjusted = ((external.get("low_probability_adjustment") or {}).get("expert_minus_adjusted_bare") or {})
    add_row(
        rows,
        claim_id="gemini_expert_training_vs_tempered_bare",
        hypothesis="Gemini expert-training prompt improves Brier versus the same-row tempered bare prompt.",
        evidence_track="prompt intervention",
        result_class="exploratory",
        pre_post_hoc_status="post-hoc external-control audit on the completed Gemini packet",
        effective_unit="contract-condition block",
        effective_n=str(adjusted.get("n", "NA")),
        effect_size=f"expert-minus-tempered-bare Brier {fmt(adjusted.get('mean_delta_brier'))}",
        raw_p=adjusted.get("sign_p"),
        correction_family="global_reported_tests",
        included_in_global_fdr=True,
        interpretation="Positive within Gemini; still weaker than matched market rows.",
        source_path=rel(SCORES["gemini_market"]),
    )

    for market_key, label in [
        ("all_market_rows", "all matched market rows"),
        ("equal_information_rows", "equal-information market rows"),
    ]:
        item = (
            ((external.get("market_controls") or {}).get(market_key) or {}).get("expert_minus_market")
            or {}
        )
        add_row(
            rows,
            claim_id=f"gemini_expert_training_vs_market_{market_key}",
            hypothesis=f"Gemini expert-training prompt is compared with {label}.",
            evidence_track="prompt market control",
            result_class="diagnostic",
            pre_post_hoc_status="post-hoc overlap audit",
            effective_unit="contract with market comparator",
            effective_n=str(item.get("n", "NA")),
            effect_size=f"expert-minus-market Brier {fmt(item.get('mean_delta_brier'))}",
            raw_p=item.get("sign_p"),
            correction_family="global_reported_tests",
            included_in_global_fdr=True,
            interpretation="Positive deltas mean Gemini is worse than market on the matched overlap.",
            source_path=rel(SCORES["gemini_market"]),
        )

    for model_key, model_name in [
        ("claude_prompt", "Claude"),
        ("codex_deepseek_prompt", "Codex+DeepSeek"),
    ]:
        rep = read_json(SCORES[model_key])
        gate = ((rep.get("condition_gates") or {}).get("expert_training_prompt") or {})
        for key, label in [("vs_bare", "bare prompt"), ("vs_placebo", "length-matched placebo")]:
            item = gate.get(key) or {}
            add_row(
                rows,
                claim_id=f"{model_name.lower().replace('+', '_')}_expert_training_{key}",
                hypothesis=f"{model_name} replication of the expert-training prompt versus {label}.",
                evidence_track="prompt replication",
                result_class="continuation",
                pre_post_hoc_status="replication check; not promoted",
                effective_unit="paired contract-condition block",
                effective_n=str(item.get("n", "NA")),
                effect_size=f"expert-minus-{label} Brier {fmt(item.get('mean_delta_brier'))}",
                raw_p=item.get("sign_p"),
                correction_family="global_reported_tests",
                included_in_global_fdr=True,
                interpretation="Current replication evidence does not reproduce the Gemini effect.",
                source_path=rel(SCORES[model_key]),
            )


def pairwise_rows(rows: list[AuditRow]) -> None:
    data = read_json(SCORES["pairwise"])
    collapsed = ((data.get("summaries") or {}).get("collapsed_by_unique_pair") or {})
    for key, label in [
        ("paired_vs_random", "random choice"),
        ("paired_vs_source_control", "source-control baseline"),
    ]:
        item = collapsed.get(key) or {}
        add_row(
            rows,
            claim_id=f"pairwise_ranking_{key}",
            hypothesis=f"Source-balanced pairwise comparisons outperform {label}.",
            evidence_track="relative judgment",
            result_class="exploratory",
            pre_post_hoc_status="source-balanced packet; probability translation not promoted",
            effective_unit="unique non-tie pair",
            effective_n=str(item.get("n_paired", collapsed.get("non_tie_n", "NA"))),
            effect_size=(
                f"accuracy {fmt(collapsed.get('contrastive_accuracy'), 3)}; "
                f"utility delta {fmt(item.get('observed_delta'))}"
            ),
            raw_p=item.get("p_value"),
            correction_family="global_reported_tests",
            included_in_global_fdr=True,
            interpretation="Supports ranking/tournament use only.",
            source_path=rel(SCORES["pairwise"]),
        )

    external = read_json(SCORES["pairwise_external"])
    comparisons = external.get("comparisons") or {}
    for key in ["translated_vs_raw", "translated_vs_f100", "translated_vs_market"]:
        item = comparisons.get(key) or {}
        paired = item.get("paired_permutation") or {}
        add_row(
            rows,
            claim_id=f"pairwise_probability_translation_{key}",
            hypothesis=f"Pairwise-derived probabilities are tested in {key.replace('_', ' ')}.",
            evidence_track="relative judgment probability translation",
            result_class="continuation",
            pre_post_hoc_status="underpowered external-bar check",
            effective_unit="contract with joined comparator",
            effective_n=str(item.get("n", paired.get("n_paired", "NA"))),
            effect_size=f"candidate-minus-baseline Brier {fmt(item.get('delta_candidate_minus_baseline'))}",
            raw_p=paired.get("p_value"),
            correction_family="global_reported_tests",
            included_in_global_fdr=True,
            interpretation="Does not promote pairwise translation as a probability layer.",
            source_path=rel(SCORES["pairwise_external"]),
        )


def source_currency_row(rows: list[AuditRow]) -> None:
    data = read_json(SCORES["source_currency"])
    paired = ((data.get("paired_stratum_delta") or {}).get("paired_permutation") or {})
    add_row(
        rows,
        claim_id="manifold_source_currency_post_minus_pre",
        hypothesis="Manifold rows after the model cutoff are harder than matched rows before cutoff or source-visible.",
        evidence_track="row validity",
        result_class="diagnostic",
        pre_post_hoc_status="retrospective audit of a matched Manifold panel",
        effective_unit="contract; paired-stratum test over matched cells",
        effective_n=f"{data.get('panel_contracts', 'NA')} contracts / {paired.get('n_paired', 'NA')} paired strata",
        effect_size=(
            f"aggregate post-minus-pre Brier {fmt((data.get('aggregate_delta') or {}).get('post_minus_pre'))}; "
            f"paired-stratum delta {fmt(paired.get('observed_delta'), 4)}"
        ),
        raw_p=paired.get("p_value"),
        correction_family="global_reported_tests",
        included_in_global_fdr=True,
        interpretation="Manifold-supported measurement result; second-source extension remains a follow-up.",
        source_path=rel(SCORES["source_currency"]),
    )


def build_rows() -> list[AuditRow]:
    rows: list[AuditRow] = []
    source_currency_row(rows)
    market_row(
        rows,
        claim_id="polymarket_equal_information_raw_panel_vs_market",
        source_key="polymarket_market",
        result_class="diagnostic",
        pre_post_hoc_status="post-hoc replacement packet with same-time market prices",
        interpretation="Rules out raw panel superiority on this Polymarket slice; not a general market estimate.",
    )
    market_row(
        rows,
        claim_id="manifold_equal_information_raw_panel_vs_market",
        source_key="manifold_market",
        result_class="diagnostic",
        pre_post_hoc_status="post-hoc Manifold history fill",
        interpretation="The market Brier is lower, but the paired test is inconclusive.",
    )
    for key, label in [
        ("manifold_freeze0", "same-day Manifold freeze expansion"),
        ("manifold_freeze1", "one-day Manifold freeze sensitivity"),
        ("manifold_freeze2", "two-day Manifold freeze sensitivity"),
        ("manifold_freeze7", "seven-day Manifold freeze sensitivity"),
    ]:
        market_row(
            rows,
            claim_id=f"{key}_raw_panel_vs_market",
            source_key=key,
            result_class="diagnostic",
            pre_post_hoc_status="post-hoc horizon sensitivity check",
            interpretation=f"{label}; overlapping Manifold rows, not an independent population sample.",
            comparison_id="v28rollback_full__v25_external::single",
        )
    low_p_policy_row(rows)
    low_p_stress_rows(rows)
    pairwise_rows(rows)
    prompt_rows(rows)
    return rows


def apply_fdr(rows: list[AuditRow]) -> None:
    tests = [
        (idx, row.raw_p)
        for idx, row in enumerate(rows)
        if row.included_in_global_fdr and row.raw_p is not None
    ]
    tests.sort(key=lambda item: float(item[1]))
    m = len(tests)
    harmonic = sum(1.0 / rank for rank in range(1, m + 1))

    for attr, multiplier in [("bh_fdr_q_global", 1.0), ("by_fdr_q_global", harmonic)]:
        running = 1.0
        q_by_idx: dict[int, float] = {}
        for rank_from_end, (idx, p_value) in enumerate(reversed(tests), start=1):
            rank = m - rank_from_end + 1
            q = min(float(p_value) * m * multiplier / rank, running, 1.0)
            running = q
            q_by_idx[idx] = q
        for idx, q_value in q_by_idx.items():
            setattr(rows[idx], attr, round(q_value, 6))


def write_csv(path: Path, rows: list[AuditRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            data = asdict(row)
            writer.writerow({key: data.get(key) for key in CSV_FIELDS})


def build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# GP-245 Multiple-Testing and Effective-N Audit",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Status: `{report['status']}`",
        "",
        report["interpretation"],
        "",
        "| Claim ID | Track | Class | Status | Unit | Effective N | Effect | Raw p | BH q | BY q | Interpretation |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in report["rows"]:
        raw_p = "NA" if row["raw_p"] is None else f"{float(row['raw_p']):.6g}"
        q_value = (
            "NA"
            if row["bh_fdr_q_global"] is None
            else f"{float(row['bh_fdr_q_global']):.6g}"
        )
        by_value = (
            "NA"
            if row["by_fdr_q_global"] is None
            else f"{float(row['by_fdr_q_global']):.6g}"
        )
        values = [
            row["claim_id"],
            row["evidence_track"],
            row["result_class"],
            row["pre_post_hoc_status"],
            row["effective_unit"],
            row["effective_n"],
            row["effect_size"],
            raw_p,
            q_value,
            by_value,
            row["interpretation"],
        ]
        escaped = [str(value).replace("|", "/") for value in values]
        lines.append("| " + " | ".join(escaped) + " |")
    lines.append("")
    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    rows = build_rows()
    apply_fdr(rows)
    return {
        "schema": "gp245-multiple-testing-effective-n-audit-v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "pass",
        "correction": {
            "method": "Benjamini-Hochberg FDR plus Benjamini-Yekutieli robustness",
            "family": "global_reported_tests",
            "n_tests": sum(
                1 for row in rows if row.included_in_global_fdr and row.raw_p is not None
            ),
            "justification": (
                "The manuscript reports related statistical comparisons across row validity, "
                "market controls, calibration, relative judgment, prompt intervention, and "
                "replication. A single global BH family keeps all reported tests visible. "
                "Because some panels overlap by source, contract family, model family, or "
                "prompt packet, the report also includes a BY q-value column, which is valid "
                "under arbitrary dependence and is used as a conservative robustness check. "
                "Rows without p-values would be descriptive only; every row here has a stored "
                "p-value and is included."
            ),
        },
        "interpretation": (
            "The p-values used by the manuscript are collected in one table with "
            "their effective denominator. The BY robustness column makes the dependence risk "
            "explicit: borderline rows are treated as sensitivity or continuation evidence, "
            "not as standalone claims. The main claim boundary remains: source and timing "
            "validity change what can be inferred; raw panel superiority is not supported; "
            "the low-probability rule, pairwise ranking, and Gemini prompt remain bounded "
            "and replication-dependent."
        ),
        "rows": [asdict(row) for row in rows],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    report = build_report()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "multiple_testing_effective_n_audit.json"
    csv_path = args.out_dir / "multiple_testing_effective_n_audit.csv"
    md_path = args.out_dir / "multiple_testing_effective_n_audit.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, [AuditRow(**row) for row in report["rows"]])
    md_path.write_text(build_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": report["schema"],
                "status": report["status"],
                "n_tests": report["correction"]["n_tests"],
                "out_dir": str(args.out_dir),
                "outputs": [str(json_path), str(csv_path), str(md_path)],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
