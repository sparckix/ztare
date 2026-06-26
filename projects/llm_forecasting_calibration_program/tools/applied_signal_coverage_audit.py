#!/usr/bin/env python3
"""Audit that applied forecast-signal findings are represented in the paper.

This is a reader-facing coverage check. It does not create a new empirical
result; it records whether each applied signal from the current program is in
the manuscript, bounded, or deliberately left as a future test.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/applied_signal_coverage_2026_06_17"

COLUMNS = [
    "applied_component",
    "status",
    "evidence_summary",
    "paper_anchor",
    "current_use",
    "boundary",
    "next_check",
    "support_files",
]


ROWS: list[dict[str, Any]] = [
    {
        "applied_component": "low-probability calibration",
        "status": "supported current rule",
        "evidence_summary": (
            "On forward-looking rows that pass the source-currency check, the raw mean panel is 0.029598 Brier points "
            "worse than the deterministic low-probability rule; family-level checks are favorable."
        ),
        "paper_anchor": "main.tex:tab:applied-outputs; main.tex:sec:controlled-use",
        "current_use": (
            "Use as a scoped post-processing rule for low panel probabilities after source-currency "
            "and label-time checks pass."
        ),
        "boundary": (
            "It regresses on source-visible rows, so it is not a universal correction and is applied "
            "only after the validity screen."
        ),
        "next_check": "Replicate on a larger public source-balanced packet with open and proprietary models.",
        "support_files": [
            "projects/llm_forecasting_calibration_program/tools/controlled_use_audit.py",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16/claim_gap_matrix.json",
        ],
    },
    {
        "applied_component": "pairwise ranking",
        "status": "supported relative-judgment signal",
        "evidence_summary": (
            "The source-balanced ranking slice has 24 non-tie pairs, accuracy 0.750, utility +0.583, "
            "and permutation p=0.0044 versus random choice."
        ),
        "paper_anchor": "main.tex:tab:applied-outputs; main.tex:tab:core-results",
        "current_use": "Use as a ranking or triage interface, not as a standalone probability model.",
        "boundary": (
            "Probability translation and market-additive use remain underpowered and require a "
            "larger prospective packet."
        ),
        "next_check": "Score the predeclared market-freeze ranking packet after enough markets resolve.",
        "support_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16/claim_gap_matrix.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/decisive_continuation_2026_06_16/decisive_continuation_matrix.json",
        ],
    },
    {
        "applied_component": "expert-training prompt",
        "status": "Gemini-specific candidate",
        "evidence_summary": (
            "The completed Gemini public-corpus run scores 600/600 planned calls and the expert-training "
            "arm beats bare, placebo, and same-row calibrated-bare checks."
        ),
        "paper_anchor": "main.tex:tab:applied-outputs; main.tex:tab:next-tests",
        "current_use": "Treat as a replication target and a candidate intervention family.",
        "boundary": (
            "It does not beat market baselines on the available rows, and the 591/600-call Claude "
            "run remains underpowered and below gate while Codex+DeepSeek does not reproduce the effect."
        ),
        "next_check": "Complete cross-family replication and require source-stratified survival before promotion.",
        "support_files": [
            "projects/llm_forecasting_calibration_program/structured_metacognition_v1/workspace/structured_metacognition_public_v1_score_report.json",
            "projects/llm_forecasting_calibration_program/structured_metacognition_v1/workspace/structured_metacognition_public_v1_external_control_report.json",
            "projects/llm_forecasting_calibration_program/structured_metacognition_v1/workspace/structured_metacognition_public_v1_claude_partial_report.json",
        ],
    },
    {
        "applied_component": "structured evidence fields",
        "status": "candidate interface",
        "evidence_summary": (
            "Small earlier tests suggest comparable fields can expose useful distinctions, but later "
            "placebo-controlled prompt tests are mixed."
        ),
        "paper_anchor": "main.tex:tab:applied-outputs; main.tex:sec:coverage-audit",
        "current_use": "Use for data collection and comparison hygiene, not as a proven scoring improvement.",
        "boundary": "No current result establishes a general gain from richer fields alone.",
        "next_check": "Test field structure against length-matched placebo prompts on public rows.",
        "support_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/experiment_coverage_2026_06_16/experiment_coverage_summary.json",
        ],
    },
    {
        "applied_component": "family-choice headroom",
        "status": "diagnostic headroom",
        "evidence_summary": (
            "Best-family-in-hindsight scoring shows large headroom, but cheap observed selection rules "
            "do not recover it reliably."
        ),
        "paper_anchor": "main.tex:tab:applied-outputs; main.tex:tab:coverage-audit",
        "current_use": "Use to justify held-out review and selection studies.",
        "boundary": "The paper does not offer a dependable family-selection rule.",
        "next_check": "Test selection features against held-out source and family splits.",
        "support_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/experiment_coverage_2026_06_16/experiment_coverage_summary.json",
        ],
    },
    {
        "applied_component": "negative prompt controls",
        "status": "negative applied guidance",
        "evidence_summary": (
            "Generic reflection, self-revision, selective action framing, and channel-only corrections "
            "mostly fail or regress under the stronger controls."
        ),
        "paper_anchor": "main.tex:tab:applied-outputs; main.tex:tab:evidence-ledger",
        "current_use": "Leave generic reflection, self-revision, and selective-action prompts unsupported until they clear the same controls.",
        "boundary": (
            "This does not rule out retrieval-grounded systems, expert-written procedures, or held-out "
            "tuning with independent checks."
        ),
        "next_check": "Require any new intervention to beat bare, placebo, calibrated-bare, and source splits.",
        "support_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/experiment_coverage_2026_06_16/experiment_coverage_summary.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16/claim_gap_matrix.json",
        ],
    },
    {
        "applied_component": "uncertainty-channel diagnostics",
        "status": "diagnostic signal",
        "evidence_summary": (
            "Worry, tail, and disagreement channels are sometimes informative, but they are not stable "
            "enough to serve as direct correction rules."
        ),
        "paper_anchor": "main.tex:tab:evidence-ledger; main.tex:sec:coverage-audit",
        "current_use": "Use as monitoring features and failure probes.",
        "boundary": "They remain monitoring features until a scored holdout test supports an automatic probability adjustment.",
        "next_check": "Run holdout scoring for any proposed channel-to-probability rule.",
        "support_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/experiment_coverage_2026_06_16/experiment_coverage_summary.json",
        ],
    },
    {
        "applied_component": "public benchmark validity extension",
        "status": "evidence route",
        "evidence_summary": (
            "ForecastBench, PredictionMarketBench, Prophet Arena, and PolyBench audits identify which "
            "public sources currently expose scored rows, same-time baselines, or only schema-level evidence."
        ),
        "paper_anchor": "main.tex:tab:field-audit-protocol; main.tex:tab:public-benchmark-audit",
        "current_use": "Use as the roadmap for an external validity replication.",
        "boundary": "The current paper does not report a field-wide prevalence estimate.",
        "next_check": "Acquire or reconstruct row-level traces before making benchmark-level prevalence claims.",
        "support_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_validity_source_inventory.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_forecastbench_score_audit.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_predictionmarketbench_row_schema_pilot.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_prophet_arena_row_schema_pilot.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_polybench_source_pilot.json",
        ],
    },
]


def rel(path: str | Path) -> str:
    path_obj = Path(path)
    if not path_obj.is_absolute():
        return str(path_obj)
    try:
        return str(path_obj.resolve().relative_to(REPO))
    except ValueError:
        return str(path_obj)


def flatten_row(row: dict[str, Any]) -> dict[str, str]:
    flat = {}
    for column in COLUMNS:
        value = row.get(column, "")
        if isinstance(value, list):
            flat[column] = "; ".join(str(item) for item in value)
        else:
            flat[column] = str(value)
    return flat


def build_report(rows: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    positive_statuses = {
        "supported current rule",
        "supported relative-judgment signal",
        "Gemini-specific candidate",
        "candidate interface",
        "diagnostic headroom",
        "diagnostic signal",
    }
    missing_anchor = [row["applied_component"] for row in rows if not row.get("paper_anchor")]
    missing_boundary = [row["applied_component"] for row in rows if not row.get("boundary")]
    missing_next_check = [row["applied_component"] for row in rows if not row.get("next_check")]
    missing_support = [row["applied_component"] for row in rows if not row.get("support_files")]
    supported_count = sum(1 for row in rows if row["status"] in positive_statuses)
    return {
        "schema": "gp245-applied-signal-coverage-v1",
        "generated_at": generated_at,
        "rows": rows,
        "summary": {
            "applied_components": len(rows),
            "supported_or_scoped_candidate": supported_count,
            "negative_guidance_rows": sum(1 for row in rows if row["status"] == "negative applied guidance"),
            "evidence_route_rows": sum(1 for row in rows if row["status"] == "evidence route"),
            "all_have_paper_anchor": not missing_anchor,
            "all_have_boundary": not missing_boundary,
            "all_have_next_check": not missing_next_check,
            "all_have_support_files": not missing_support,
            "missing_anchor": missing_anchor,
            "missing_boundary": missing_boundary,
            "missing_next_check": missing_next_check,
            "missing_support_files": missing_support,
        },
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(flatten_row(row) for row in rows)


def build_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Applied Signal Coverage Audit",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"Applied components: `{summary['applied_components']}`",
        f"Supported or scoped candidate components: `{summary['supported_or_scoped_candidate']}`",
        f"Negative guidance rows: `{summary['negative_guidance_rows']}`",
        f"Evidence-route rows: `{summary['evidence_route_rows']}`",
        "",
        "| Applied component | Status | Evidence summary | Current use | Boundary | Next check | Paper anchor |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in report["rows"]:
        values = [
            row["applied_component"],
            row["status"],
            row["evidence_summary"],
            row["current_use"],
            row["boundary"],
            row["next_check"],
            row["paper_anchor"],
        ]
        lines.append("| " + " | ".join(str(value).replace("|", "/") for value in values) + " |")
    lines.extend(
        [
            "",
            "This audit is a coverage check. It records where each applied signal appears in the manuscript and what boundary keeps it from being overused.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    report = build_report(ROWS, generated_at)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    json_path = args.out_dir / "applied_signal_coverage_audit.json"
    csv_path = args.out_dir / "applied_signal_coverage_audit.csv"
    md_path = args.out_dir / "applied_signal_coverage_audit.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, report["rows"])
    md_path.write_text(build_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
            "schema": report["schema"],
            "applied_components": report["summary"]["applied_components"],
            "supported_or_scoped_candidate": report["summary"]["supported_or_scoped_candidate"],
            "negative_guidance_rows": report["summary"]["negative_guidance_rows"],
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
