#!/usr/bin/env python3
"""Audit the paper package against the current GP-245 paper objective.

This is a no-mutation verifier over the manuscript, PDF, and generated support
reports. It does not claim external acceptance; it checks whether the local
submission package has evidence for the concrete requirements: coherent
manuscript, supported claims, literature positioning, table/figure integrity,
continuation tests, readable prose, and explicit claim boundaries.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
PAPER = REPO / "papers/llm-forecast-calibration-cross-corpus"
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/paper_goal_completion_2026_06_17"

MAIN_TEX = PAPER / "main.tex"
DRAFT_MD = PAPER / "draft.md"
MAIN_PDF = PAPER / "main.pdf"

SUBMISSION_SCRIPT = PROGRAM / "tools/submission_readiness_audit.py"
GOAL_SCRIPT = PROGRAM / "tools/paper_goal_completion_audit.py"
SUBMISSION = PROGRAM / "paper_alignment_v1/workspace/submission_readiness_2026_06_16/submission_readiness_audit.json"
CLAIM_ALIGNMENT = PROGRAM / "paper_alignment_v1/workspace/paper_claim_alignment_report.json"
COHERENCE = PROGRAM / "paper_alignment_v1/workspace/paper_coherence_audit.json"
CONTROLLED_USE = PROGRAM / "paper_alignment_v1/workspace/controlled_use_audit.json"
LITERATURE = PROGRAM / "paper_alignment_v1/workspace/literature_positioning_2026_06_16/literature_positioning_audit.json"
NUMERIC_TRACE = PROGRAM / "paper_alignment_v1/workspace/numeric_claim_trace_2026_06_16/numeric_claim_trace.json"
EFFECTIVE_N = (
    PROGRAM / "paper_alignment_v1/workspace/effective_n_audit_2026_06_16/central_evidence_effective_n_audit.json"
)
APPLIED_SIGNAL = (
    PROGRAM / "paper_alignment_v1/workspace/applied_signal_coverage_2026_06_17/applied_signal_coverage_audit.json"
)
SCORED_USE = (
    PROGRAM / "paper_alignment_v1/workspace/scored_use_procedure_2026_06_17/scored_use_procedure_audit.json"
)
PROSPECTIVE = (
    PROGRAM
    / "paper_alignment_v1/workspace/prospective_counterexplanation_design_2026_06_17"
    / "prospective_counterexplanation_design_audit.json"
)
REVIEWER = (
    PROGRAM / "paper_alignment_v1/workspace/reviewer_concern_coverage_2026_06_17/reviewer_concern_coverage_audit.json"
)
DECISIVE = PROGRAM / "paper_alignment_v1/workspace/decisive_continuation_2026_06_16/decisive_continuation_matrix.json"
EVIDENCE_UPGRADE = PROGRAM / "paper_alignment_v1/workspace/evidence_upgrade_plan_2026_06_17/evidence_upgrade_plan.json"
BENCHMARK = (
    PROGRAM
    / "paper_alignment_v1/workspace/forecast_row_validity_benchmark_blueprint_2026_06_17"
    / "forecast_row_validity_benchmark_blueprint.json"
)
COVERAGE = PROGRAM / "paper_alignment_v1/workspace/experiment_coverage_2026_06_16/experiment_coverage_summary.json"


@dataclass
class Requirement:
    name: str
    status: str
    evidence: str


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def req(name: str, condition: bool, evidence: str) -> Requirement:
    return Requirement(name=name, status="pass" if condition else "fail", evidence=evidence)


def check_named(report: dict[str, Any], name: str) -> bool:
    checks = report.get("checks") or []
    for item in checks:
        if isinstance(item, dict) and item.get("name") == name:
            return item.get("status") == "pass"
    return False


def alignment_check(report: dict[str, Any], name: str) -> bool:
    checks = report.get("alignment_checks") or []
    for item in checks:
        if isinstance(item, dict) and item.get("name") == name:
            return item.get("status") == "pass"
    return False


def build_report(generated_at: str) -> dict[str, Any]:
    submission = read_json(SUBMISSION)
    alignment = read_json(CLAIM_ALIGNMENT)
    coherence = read_json(COHERENCE)
    controlled = read_json(CONTROLLED_USE)
    literature = read_json(LITERATURE)
    numeric = read_json(NUMERIC_TRACE)
    effective_n = read_json(EFFECTIVE_N)
    applied = read_json(APPLIED_SIGNAL)
    scored_use = read_json(SCORED_USE)
    prospective = read_json(PROSPECTIVE)
    reviewer = read_json(REVIEWER)
    decisive = read_json(DECISIVE)
    upgrade = read_json(EVIDENCE_UPGRADE)
    benchmark = read_json(BENCHMARK)
    coverage = read_json(COVERAGE)

    verdict = coherence.get("verdict") or {}
    controlled_verdict = controlled.get("verdict") or {}
    benchmark_summary = benchmark.get("summary") or {}
    reviewer_summary = reviewer.get("summary") or {}
    coverage_summary = coverage.get("summary") or {}
    applied_summary = applied.get("summary") or {}
    coverage_research_log = coverage.get("research_log") or {}

    paths_ok = all(path.exists() and path.stat().st_size > 0 for path in (MAIN_TEX, DRAFT_MD, MAIN_PDF))
    pdf_current = paths_ok and MAIN_PDF.stat().st_mtime >= MAIN_TEX.stat().st_mtime
    submission_source = read_text(SUBMISSION_SCRIPT)
    goal_source = read_text(GOAL_SCRIPT)

    requirements = [
        req(
            "manuscript_and_pdf_present",
            paths_ok and pdf_current,
            f"{rel(MAIN_TEX)}, {rel(DRAFT_MD)}, {rel(MAIN_PDF)} present; pdf_current={pdf_current}",
        ),
        req(
            "overall_submission_readiness",
            submission.get("status") == "pass"
            and SUBMISSION.exists()
            and SUBMISSION_SCRIPT.exists()
            and SUBMISSION.stat().st_mtime >= SUBMISSION_SCRIPT.stat().st_mtime,
            (
                f"submission_readiness status={submission.get('status')}; "
                f"report_current_with_script={SUBMISSION.exists() and SUBMISSION_SCRIPT.exists() and SUBMISSION.stat().st_mtime >= SUBMISSION_SCRIPT.stat().st_mtime}"
            ),
        ),
        req(
            "audit_dependency_graph_acyclic",
            "paper_goal_completion_audit" not in submission_source
            and "PAPER_GOAL_COMPLETION" not in submission_source
            and "submission_readiness_audit.json" in goal_source,
            "submission readiness is package-level; goal completion consumes submission readiness",
        ),
        req(
            "coherent_integrated_paper_shape",
            bool(verdict.get("central_claim"))
            and verdict.get("broad_claim_ready") is False
            and check_named(submission, "coherence_counterexplanation_design"),
            f"central_claim={bool(verdict.get('central_claim'))}; broad_claim_ready={verdict.get('broad_claim_ready')}",
        ),
        req(
            "claim_alignment_and_no_overclaim",
            alignment.get("alignment_status") == "pass"
            and alignment.get("finding_count") == 0
            and check_named(submission, "claim_boundaries_in_main_text")
            and check_named(submission, "readiness_verdict_scoped"),
            f"alignment={alignment.get('alignment_status')}; findings={alignment.get('finding_count')}",
        ),
        req(
            "evidence_sufficiency_for_current_claims",
            numeric.get("status") == "pass"
            and effective_n.get("status") == "pass"
            and applied_summary.get("supported_or_bounded_positive", 0) >= 6
            and controlled_verdict.get("integrated_paper_supported") is True
            and controlled_verdict.get("split_required_now") is False,
            (
                f"numeric={numeric.get('status')}; effective_n={effective_n.get('status')}; "
                f"applied={applied_summary.get('supported_or_bounded_positive')}"
            ),
        ),
        req(
            "scored_use_and_stop_rules",
            scored_use.get("status") == "pass"
            and (scored_use.get("summary") or {}).get("all_stop_conditions_present") is True,
            f"scored_use={scored_use.get('status')}; steps={(scored_use.get('summary') or {}).get('steps')}",
        ),
        req(
            "literature_positioning_current",
            literature.get("status") == "pass" and len(literature.get("rows") or []) >= 11,
            f"literature rows={len(literature.get('rows') or [])}; status={literature.get('status')}",
        ),
        req(
            "table_figure_and_build_integrity",
            check_named(submission, "tables_and_figures_have_captions_and_labels")
            and check_named(submission, "required_tables_and_figures")
            and check_named(submission, "latex_log_clean"),
            "caption/label, required-label, and build-log checks pass",
        ),
        req(
            "continuation_experiments_and_upgrade_gates",
            decisive.get("status") == "pass"
            and len(decisive.get("rows") or []) >= 7
            and upgrade.get("status") == "pass"
            and len(upgrade.get("rows") or []) >= 3
            and prospective.get("status") == "pass"
            and (prospective.get("summary") or {}).get("planned_results", 0) >= 7,
            (
                f"decisive_rows={len(decisive.get('rows') or [])}; "
                f"upgrade_rows={len(upgrade.get('rows') or [])}; prospective={prospective.get('status')}"
            ),
        ),
        req(
            "companion_benchmark_pre_scoring_design",
            benchmark.get("status") == "pass"
            and benchmark_summary.get("modules", 0) >= 8
            and benchmark_summary.get("has_prospective_inversion_planning") is True,
            (
                f"modules={benchmark_summary.get('modules')}; "
                f"prospective_planning={benchmark_summary.get('has_prospective_inversion_planning')}"
            ),
        ),
        req(
            "experiment_coverage_without_frankenstein_scope",
            coverage_research_log.get("unique_rows_detected", 0) >= 111
            and coverage.get("ledger_rows", 0) >= 37
            and check_named(submission, "full_log_coverage_counts_in_manuscript"),
            (
                f"research_log_unique={coverage_research_log.get('unique_rows_detected')}; "
                f"ledger_rows={coverage.get('ledger_rows')}"
            ),
        ),
        req(
            "reviewer_concerns_covered",
            reviewer.get("status") == "pass"
            and reviewer_summary.get("all_text_checks_pass") is True
            and reviewer_summary.get("all_evidence_files_present") is True,
            f"reviewer={reviewer.get('status')}; concerns={reviewer_summary.get('concerns')}",
        ),
        req(
            "human_readable_public_prose",
            check_named(submission, "public_prose_clean")
            and check_named(submission, "manuscript_project_labels_removed"),
            "public-prose and manuscript-label hygiene checks pass",
        ),
        req(
            "draft_mirror_and_reproducibility_surface",
            alignment_check(alignment, "draft_front_matches_tex")
            and check_named(submission, "support_files_present")
            and check_named(submission, "manuscript_path_references_resolve")
            and check_named(submission, "markdown_path_references_resolve"),
            "draft alignment, support files, and path-reference checks pass",
        ),
    ]

    failed = [item for item in requirements if item.status != "pass"]
    return {
        "schema": "gp245-paper-goal-completion-audit-v1",
        "generated_at": generated_at,
        "status": "pass" if not failed else "fail",
        "interpretation": (
            "Pass means the local paper package satisfies the concrete evidence requirements for the current "
            "submission-scope manuscript. It does not assert external acceptance or broad LLM superiority."
        ),
        "requirements": [item.__dict__ for item in requirements],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Paper Goal Completion Audit",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Status: `{report['status']}`",
        "",
        str(report["interpretation"]),
        "",
        "| Requirement | Status | Evidence |",
        "|---|---|---|",
    ]
    for item in report["requirements"]:
        lines.append(f"| {item['name']} | {item['status']} | {str(item['evidence']).replace('|', '/')} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    report = build_report(generated_at)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    json_path = args.out_dir / "paper_goal_completion_audit.json"
    md_path = args.out_dir / "paper_goal_completion_audit.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": report["schema"],
                "status": report["status"],
                "requirements": len(report["requirements"]),
                "out_dir": str(args.out_dir),
                "outputs": [str(json_path), str(md_path)],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
