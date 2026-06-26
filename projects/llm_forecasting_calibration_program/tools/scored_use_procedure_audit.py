#!/usr/bin/env python3
"""Audit the paper's scored-use procedure for supported operational steps.

The manuscript now contains a short procedure for using model output after row
validity checks. This script checks that each procedural step is present in the
paper, backed by existing support files, and bounded by a stop condition. It is
not new empirical evidence.
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
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/scored_use_procedure_2026_06_17"

COLUMNS = [
    "step_id",
    "procedure_step",
    "action_when_eligible",
    "stop_condition",
    "required_text",
    "support_files",
]


ROWS: list[dict[str, Any]] = [
    {
        "step_id": "row_validity_screen",
        "procedure_step": "Attach the row's information state before scoring.",
        "action_when_eligible": "Rows with source currency and label-time documentation can enter broad score comparisons.",
        "stop_condition": "Rows failing those checks are diagnostic rows, not broad comparison rows.",
        "required_text": [
            "attach forecast time, model cutoff, source, label vintage, event family key, and comparator timestamp",
            "rows that fail source currency or label-time checks can be studied diagnostically",
        ],
        "support_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16/claim_gap_matrix.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/effective_n_audit_2026_06_16/central_evidence_effective_n_audit.json",
        ],
    },
    {
        "step_id": "same_information_baseline_first",
        "procedure_step": "Score the equal-information market or human baseline before reporting model gains.",
        "action_when_eligible": "Report model gains only when they beat the dated comparator on the same rows.",
        "stop_condition": "When the comparator wins, report the model result as diagnostic unless a predeclared rule or blend beats it.",
        "required_text": [
            "score any equal-information market or human baseline before reporting model gains",
            "When that baseline wins, the model result is reported as diagnostic",
        ],
        "support_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16/claim_gap_matrix.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/numeric_claim_trace_2026_06_16/numeric_claim_trace.json",
        ],
    },
    {
        "step_id": "low_probability_correction",
        "procedure_step": "Apply the correction for very small probabilities only on eligible forward-looking rows.",
        "action_when_eligible": "Use the correction for very low panel probabilities after validity checks pass, and report raw beside adjusted.",
        "stop_condition": "Do not apply it to source-visible rows or use it as a retrospective benchmark correction.",
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
        "step_id": "pairwise_ranking_only",
        "procedure_step": "Use pairwise comparisons for ranking or prioritization, not standalone probabilities.",
        "action_when_eligible": "Use pairwise outputs for relative triage when ranking is the target.",
        "stop_condition": "Probability translation waits for prospective checks against raw, calibrated, and market baselines.",
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
        "step_id": "prompt_variant_gate",
        "procedure_step": "Treat prompt variants as candidates only after placebo and source checks.",
        "action_when_eligible": "A prompt variant can be carried forward only if it beats bare, placebo, calibrated bare, and source-split checks.",
        "stop_condition": "Otherwise it remains a candidate or negative-control result rather than a confirmed prompt intervention.",
        "required_text": [
            "treat prompt variants as candidates only when they beat bare, placebo, calibrated bare, and source-split checks",
        ],
        "support_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/applied_signal_coverage_2026_06_17/applied_signal_coverage_audit.json",
            "projects/llm_forecasting_calibration_program/structured_metacognition_v1/workspace/structured_metacognition_public_v1_score_report.json",
            "projects/llm_forecasting_calibration_program/structured_metacognition_v1/workspace/structured_metacognition_public_v1_claude_replication_score_report.json",
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
        "step_id": str(row["step_id"]),
        "procedure_step": str(row["procedure_step"]),
        "action_when_eligible": str(row["action_when_eligible"]),
        "stop_condition": str(row["stop_condition"]),
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
                missing_text.append(f"{row['step_id']}: {snippet}")
        for path, ok in file_checks.items():
            if not ok:
                missing_files.append(f"{row['step_id']}: {path}")
        rows.append({**row, "text_checks": text_checks, "file_checks": file_checks})
    all_stop_conditions = all(bool(str(row.get("stop_condition", "")).strip()) for row in rows)
    return {
        "schema": "gp245-scored-use-procedure-audit-v1",
        "generated_at": generated_at,
        "status": "pass" if not missing_text and not missing_files and all_stop_conditions else "fail",
        "rows": rows,
        "summary": {
            "steps": len(rows),
            "all_manuscript_text_present": not missing_text,
            "all_support_files_present": not missing_files,
            "all_stop_conditions_present": all_stop_conditions,
            "applied_not_superiority": True,
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
        "# Scored-Use Procedure Audit",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Status: `{report['status']}`",
        f"Steps checked: `{summary['steps']}`",
        "",
        "| Step | Procedure | Action when eligible | Stop condition |",
        "|---|---|---|---|",
    ]
    for row in report["rows"]:
        values = [row["step_id"], row["procedure_step"], row["action_when_eligible"], row["stop_condition"]]
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

    json_path = args.out_dir / "scored_use_procedure_audit.json"
    csv_path = args.out_dir / "scored_use_procedure_audit.csv"
    md_path = args.out_dir / "scored_use_procedure_audit.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, report["rows"])
    md_path.write_text(build_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": report["schema"],
                "status": report["status"],
                "steps": report["summary"]["steps"],
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
