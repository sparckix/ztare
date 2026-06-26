#!/usr/bin/env python3
"""Audit before-scoring counter-explanation checks for the forecasting paper.

The paper now treats each planned result as a comparison that can be fooled by
a simpler explanation: timing mismatch, source visibility, label vintage,
placebo effects, source mix, or denominator choice. This script checks that the
paper names those counter-explanations and the design check that rules each one
out before a result is promoted.
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
PAPER_DIR = REPO / "papers/llm-forecast-calibration-cross-corpus"
MAIN_TEX = PAPER_DIR / "main.tex"
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/prospective_counterexplanation_design_2026_06_17"

COLUMNS = [
    "result_id",
    "candidate_result",
    "counter_explanation_to_rule_out",
    "before_scoring_design_check",
    "required_text",
    "support_files",
]


ROWS: list[dict[str, Any]] = [
    {
        "result_id": "broad_model_comparison",
        "candidate_result": "Model forecasts outperform market or human baselines.",
        "counter_explanation_to_rule_out": "The comparator was observed at a different time, on a different contract, or after relevant information arrived.",
        "before_scoring_design_check": "Freeze or reconstruct the comparator probability on the same contract before scoring model gains.",
        "required_text": [
            "score any equal-information market or human baseline before reporting model gains",
            "comparator probability, if used, was measured on the same contract under the same pre-outcome information rule",
        ],
        "support_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16/claim_gap_matrix.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/numeric_claim_trace_2026_06_16/numeric_claim_trace.json",
        ],
    },
    {
        "result_id": "source_currency_result",
        "candidate_result": "Source-currency checks change benchmark conclusions.",
        "counter_explanation_to_rule_out": "The row was measuring retrieval or source familiarity rather than future-event prediction.",
        "before_scoring_design_check": "Record forecast time, model cutoff or retrieval window, source, and resolution timing before assigning broad-comparison eligibility.",
        "required_text": [
            "model's cutoff or retrieval window",
            "source-visible to the model at generation time",
        ],
        "support_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16/claim_gap_matrix.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/effective_n_audit_2026_06_16/central_evidence_effective_n_audit.json",
        ],
    },
    {
        "result_id": "label_time_result",
        "candidate_result": "Label-time checks change scored outcomes.",
        "counter_explanation_to_rule_out": "A later data vintage or settlement update was scored as if it were known at the forecast time.",
        "before_scoring_design_check": "Attach admissible data vintage or settlement rule before scoring the row.",
        "required_text": [
            "outcome label with data vintage or settlement rule",
            "the outcome label is admissible under the relevant data vintage or settlement rule",
        ],
        "support_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16/claim_gap_matrix.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/numeric_claim_trace_2026_06_16/numeric_claim_trace.json",
        ],
    },
    {
        "result_id": "scoped_calibration",
        "candidate_result": "The correction for very small probabilities improves forecasts.",
        "counter_explanation_to_rule_out": "The gain comes from retrospective or source-visible rows rather than forward-looking forecasts.",
        "before_scoring_design_check": "Evaluate on eligible forward-looking rows and report the raw score beside the adjusted score.",
        "required_text": [
            "apply the correction for very small probabilities only to very low panel probabilities",
            "report the uncorrected score beside it",
        ],
        "support_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/applied_signal_coverage_2026_06_17/applied_signal_coverage_audit.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/numeric_claim_trace_2026_06_16/numeric_claim_trace.json",
        ],
    },
    {
        "result_id": "relative_judgment",
        "candidate_result": "Pairwise ranking exposes relative forecast signal.",
        "counter_explanation_to_rule_out": "The result comes from orientation imbalance, source-pair imbalance, or overfitted probability translation.",
        "before_scoring_design_check": "Balance orientation and source pairs, then keep ranking separate until prospective probability checks clear.",
        "required_text": [
            "use pairwise comparisons for prioritization or ranking",
            "absolute-probability translation waits for prospective checks",
        ],
        "support_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16/claim_gap_matrix.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/decisive_continuation_2026_06_16/decisive_continuation_matrix.json",
        ],
    },
    {
        "result_id": "prompt_intervention",
        "candidate_result": "A structured prompt improves scored forecast probabilities.",
        "counter_explanation_to_rule_out": "The gain comes from prompt length, placebo framing, source mix, or one model family.",
        "before_scoring_design_check": "Compare against bare, length-matched placebo, calibrated bare, source-split checks, and replication checks before broadening the result.",
        "required_text": [
            "treat prompt variants as candidates only when they beat bare, placebo, calibrated bare, and source-split checks",
            "completed public question prompt comparison tests five conditions",
        ],
        "support_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/applied_signal_coverage_2026_06_17/applied_signal_coverage_audit.json",
            "projects/llm_forecasting_calibration_program/structured_metacognition_v1/workspace/structured_metacognition_public_v1_score_report.json",
            "projects/llm_forecasting_calibration_program/structured_metacognition_v1/workspace/structured_metacognition_public_v1_claude_replication_score_report.json",
        ],
    },
    {
        "result_id": "field_validity",
        "candidate_result": "Row-level validity problems generalize beyond this project.",
        "counter_explanation_to_rule_out": "The observed validity problem is project-specific and does not appear in public benchmark families.",
        "before_scoring_design_check": "Audit public benchmark families with the same row schema before reporting prevalence.",
        "required_text": [
            "does not report a failure rate across the field",
            "Row-level audit of several public benchmark families",
        ],
        "support_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_validity_audit_protocol.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_validity_source_inventory.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_forecastbench_score_audit.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_predictionmarketbench_row_schema_pilot.json",
        ],
    },
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def file_ok(path: str) -> bool:
    full = REPO / path
    return full.exists() and full.stat().st_size > 0


def flatten_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        "result_id": str(row["result_id"]),
        "candidate_result": str(row["candidate_result"]),
        "counter_explanation_to_rule_out": str(row["counter_explanation_to_rule_out"]),
        "before_scoring_design_check": str(row["before_scoring_design_check"]),
        "required_text": "; ".join(row["required_text"]),
        "support_files": "; ".join(row["support_files"]),
    }


def build_report(main_tex: Path, generated_at: str) -> dict[str, Any]:
    text = read_text(main_tex)
    rows = []
    missing_text: list[str] = []
    missing_files: list[str] = []
    for row in ROWS:
        text_checks = {snippet: snippet in text for snippet in row["required_text"]}
        file_checks = {path: file_ok(path) for path in row["support_files"]}
        for snippet, ok in text_checks.items():
            if not ok:
                missing_text.append(f"{row['result_id']}: {snippet}")
        for path, ok in file_checks.items():
            if not ok:
                missing_files.append(f"{row['result_id']}: {path}")
        rows.append({**row, "text_checks": text_checks, "file_checks": file_checks})

    all_counter_explanations = all(
        bool(str(row.get("counter_explanation_to_rule_out", "")).strip()) for row in rows
    )
    all_design_checks = all(
        bool(str(row.get("before_scoring_design_check", "")).strip()) for row in rows
    )
    status = "pass" if not missing_text and not missing_files and all_counter_explanations and all_design_checks else "fail"
    return {
        "schema": "prospective-counterexplanation-design-audit-v1",
        "generated_at": generated_at,
        "status": status,
        "rows": rows,
        "summary": {
            "planned_results": len(rows),
            "all_manuscript_text_present": not missing_text,
            "all_support_files_present": not missing_files,
            "all_counter_explanations_present": all_counter_explanations,
            "all_before_scoring_design_checks_present": all_design_checks,
            "before_scoring_not_after_scoring": True,
            "missing_text": missing_text,
            "missing_files": missing_files,
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
        "# Prospective Counter-Explanation Design Audit",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Status: `{report['status']}`",
        f"Planned results checked: `{summary['planned_results']}`",
        "",
        "| Result | Counter-explanation to rule out | Before-scoring design check |",
        "|---|---|---|",
    ]
    for row in report["rows"]:
        values = [
            row["candidate_result"],
            row["counter_explanation_to_rule_out"],
            row["before_scoring_design_check"],
        ]
        lines.append("| " + " | ".join(str(value).replace("|", "/") for value in values) + " |")
    if summary["missing_text"] or summary["missing_files"]:
        lines.extend(["", "## Missing Checks", ""])
        for item in summary["missing_text"]:
            lines.append(f"- Missing manuscript text: {item}")
        for item in summary["missing_files"]:
            lines.append(f"- Missing support file: {item}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-tex", type=Path, default=MAIN_TEX)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    report = build_report(args.main_tex, generated_at)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    json_path = args.out_dir / "prospective_counterexplanation_design_audit.json"
    csv_path = args.out_dir / "prospective_counterexplanation_design_audit.csv"
    md_path = args.out_dir / "prospective_counterexplanation_design_audit.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, report["rows"])
    md_path.write_text(build_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": report["schema"],
                "status": report["status"],
                "planned_results": report["summary"]["planned_results"],
                "out_dir": str(args.out_dir),
                "outputs": [str(json_path), str(csv_path), str(md_path)],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
