#!/usr/bin/env python3
"""Check that likely reviewer concerns have explicit manuscript answers.

This audit does not create new empirical evidence. It verifies that the current
paper tells a reader where each major concern is answered, what evidence backs
the answer, and what boundary remains.
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
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/reviewer_concern_coverage_2026_06_17"

COLUMNS = [
    "concern",
    "manuscript_answer",
    "paper_anchor",
    "evidence_files",
    "remaining_boundary",
    "required_main_text",
]


ROWS: list[dict[str, Any]] = [
    {
        "concern": "The paper is only a measurement audit.",
        "manuscript_answer": (
            "The controlled-use section and controlled-use map state the usable components: "
            "calibration for very small probabilities, pairwise ranking, one Gemini prompt result, "
            "structured fields as a candidate interface, family-choice headroom, and negative guidance."
        ),
        "paper_anchor": "main.tex:tab:applied-outputs; main.tex:sec:controlled-use",
        "evidence_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/applied_signal_coverage_2026_06_17/applied_signal_coverage_audit.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16/claim_gap_matrix.json",
        ],
        "remaining_boundary": "The applied result is a controlled-use map, not a claim that an autonomous model beats markets.",
        "required_main_text": ["tab:applied-outputs", "The resulting order of use is concrete"],
    },
    {
        "concern": "Markets beat the raw model panel.",
        "manuscript_answer": (
            "The paper makes that a central boundary: the Polymarket same-contract slice has much "
            "lower market Brier under the raw paired test and BH correction, with BY sensitivity "
            "reported separately; the Manifold slice has lower market Brier but an inconclusive "
            "paired test."
        ),
        "paper_anchor": "main.tex:tab:core-results; main.tex:fig:equal-info-bars",
        "evidence_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16/claim_gap_matrix.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/numeric_claim_trace_2026_06_16/numeric_claim_trace.json",
        ],
        "remaining_boundary": "No claim is made that LLMs are superior to markets or humans.",
        "required_main_text": ["Polymarket", "0.267758", "0.072964"],
    },
    {
        "concern": "The prompt result may be a one-model effect.",
        "manuscript_answer": (
            "The manuscript reports the completed Gemini result, the market-overlap boundary, and "
            "the 591/600-call Claude run as underpowered and below gate, with Codex+DeepSeek "
            "not reproducing the Gemini effect."
        ),
        "paper_anchor": "main.tex:sec:controlled-use; main.tex:tab:claim-map",
        "evidence_files": [
            "projects/llm_forecasting_calibration_program/structured_metacognition_v1/workspace/structured_metacognition_public_v1_score_report.json",
            "projects/llm_forecasting_calibration_program/structured_metacognition_v1/workspace/structured_metacognition_public_v1_external_control_report.json",
            "projects/llm_forecasting_calibration_program/structured_metacognition_v1/workspace/structured_metacognition_public_v1_claude_replication_score_report.json",
        ],
        "remaining_boundary": "The result is a Gemini-specific public question candidate until cross-family replication passes.",
        "required_main_text": ["591/600-call Claude", "Gemini-specific candidate", "Does not beat the market on current overlap"],
    },
    {
        "concern": "The calibration rule for very small probabilities may be a retrospective correction.",
        "manuscript_answer": (
            "The manuscript states that the rule improves forward-looking rows that pass the source currency check but "
            "regresses on source-visible rows."
        ),
        "paper_anchor": "main.tex:sec:controlled-use; main.tex:tab:applied-outputs",
        "evidence_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16/claim_gap_matrix.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/numeric_claim_trace_2026_06_16/numeric_claim_trace.json",
        ],
        "remaining_boundary": "It is a calibration rule for rows that pass the source currency check, not a universal correction.",
        "required_main_text": ["calibration result for rows that pass the source currency check", "not a universal correction"],
    },
    {
        "concern": "Pairwise ranking may be overstated as probabilities.",
        "manuscript_answer": (
            "The manuscript keeps pairwise ranking as a relative-judgment use case and states that "
            "probability translation still lacks the required prospective and market controls."
        ),
        "paper_anchor": "main.tex:sec:controlled-use; main.tex:tab:next-tests",
        "evidence_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16/claim_gap_matrix.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/decisive_continuation_2026_06_16/decisive_continuation_matrix.json",
        ],
        "remaining_boundary": "The supported use is ranking or tournament support, not standalone probability translation.",
        "required_main_text": ["ranking or tournament support", "not yet a probability model"],
    },
    {
        "concern": "The private low-overlap corpus may block reproducibility.",
        "manuscript_answer": (
            "The manuscript states that the central validity, market control, and source currency "
            "calibration claims use public-market, official-data, database, scoring, and audit files; "
            "the private low-overlap corpus is secondary."
        ),
        "paper_anchor": "main.tex:sec:corpora; main.tex:tab:reproduction-status",
        "evidence_files": [
            "projects/llm_forecasting_calibration_program/public/METHODOLOGY.md",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/submission_readiness_2026_06_16/submission_readiness_audit.json",
        ],
        "remaining_boundary": "Direct replication of low-overlap diagnostics needs a sanitized or substitute corpus.",
        "required_main_text": ["not required for the paper's central", "sanitized or substitute"],
    },
    {
        "concern": "The field-wide claim may be too broad.",
        "manuscript_answer": (
            "The manuscript says it does not report a failure rate across the field and treats public "
            "benchmark work as a route and source inventory, not a prevalence estimate."
        ),
        "paper_anchor": "main.tex:tab:public-benchmark-audit; main.tex:sec:reaudit",
        "evidence_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_validity_source_inventory.json",
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_forecastbench_score_audit.json",
        ],
        "remaining_boundary": "Prevalence and conclusion-change rates remain future claims.",
        "required_main_text": ["does not report a failure rate across the field", "not evidence of prevalence across the field"],
    },
    {
        "concern": "Repeated calls may overstate the amount of evidence.",
        "manuscript_answer": (
            "The central evidence denominator audit records calls, contracts or pairs, market rows, "
            "source counts, and event-group status for each main evidence slice."
        ),
        "paper_anchor": "main.tex:tab:reproduction-status; main.tex:tab:next-tests",
        "evidence_files": [
            "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/effective_n_audit_2026_06_16/central_evidence_effective_n_audit.json",
        ],
        "remaining_boundary": "Several central rows still lack a global event-family key and are treated conservatively.",
        "required_main_text": ["model call rows from being treated as independent events", "event-group"],
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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def flatten_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        "concern": str(row["concern"]),
        "manuscript_answer": str(row["manuscript_answer"]),
        "paper_anchor": str(row["paper_anchor"]),
        "evidence_files": "; ".join(str(item) for item in row["evidence_files"]),
        "remaining_boundary": str(row["remaining_boundary"]),
        "required_main_text": "; ".join(str(item) for item in row["required_main_text"]),
    }


def build_report(main_tex: Path, generated_at: str) -> dict[str, Any]:
    main_text = read_text(main_tex)
    rows = []
    missing_text: list[str] = []
    missing_files: list[str] = []
    for row in ROWS:
        text_checks = {snippet: snippet in main_text for snippet in row["required_main_text"]}
        file_checks = {
            path: (REPO / path).exists() and (REPO / path).stat().st_size > 0 for path in row["evidence_files"]
        }
        for snippet, ok in text_checks.items():
            if not ok:
                missing_text.append(f"{row['concern']}: {snippet}")
        for path, ok in file_checks.items():
            if not ok:
                missing_files.append(f"{row['concern']}: {path}")
        rows.append({**row, "text_checks": text_checks, "file_checks": file_checks})
    return {
        "schema": "gp245-reviewer-concern-coverage-v1",
        "generated_at": generated_at,
        "status": "pass" if not missing_text and not missing_files else "fail",
        "rows": rows,
        "summary": {
            "concerns": len(rows),
            "all_text_checks_pass": not missing_text,
            "all_evidence_files_present": not missing_files,
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
        "# Reviewer Concern Coverage Audit",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Status: `{report['status']}`",
        f"Concerns checked: `{summary['concerns']}`",
        "",
        "| Concern | Manuscript answer | Remaining boundary | Paper anchor |",
        "|---|---|---|---|",
    ]
    for row in report["rows"]:
        values = [row["concern"], row["manuscript_answer"], row["remaining_boundary"], row["paper_anchor"]]
        lines.append("| " + " | ".join(str(value).replace("|", "/") for value in values) + " |")
    if summary["missing_text"] or summary["missing_files"]:
        lines.extend(["", "## Missing Checks", ""])
        for item in summary["missing_text"]:
            lines.append(f"- Missing manuscript text: {item}")
        for item in summary["missing_files"]:
            lines.append(f"- Missing evidence file: {item}")
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

    json_path = args.out_dir / "reviewer_concern_coverage_audit.json"
    csv_path = args.out_dir / "reviewer_concern_coverage_audit.csv"
    md_path = args.out_dir / "reviewer_concern_coverage_audit.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, report["rows"])
    md_path.write_text(build_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": report["schema"],
                "status": report["status"],
                "concerns": report["summary"]["concerns"],
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
