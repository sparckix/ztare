#!/usr/bin/env python3
"""Final submission-readiness audit for the GP-245 manuscript.

This is an offline, no-mutation check over the current paper, generated support
files, SQLite evidence database, and LaTeX log. It turns the camera-ready
questions into executable checks: sections present, key tables/figures labeled,
support files generated, broad-comparison boundaries explicit, and build log
clean.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
PAPER_DIR = REPO / "papers/llm-forecast-calibration-cross-corpus"
ROOT_PROJECT_DIR = REPO / "llm-forecast-calibration-cross-corpus"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/submission_readiness_2026_06_16"

MAIN_TEX = PAPER_DIR / "main.tex"
DRAFT_MD = PAPER_DIR / "draft.md"
MAIN_PDF = PAPER_DIR / "main.pdf"
MAIN_LOG = REPO / "llm-forecast-calibration-cross-corpus/working/paper_build_artifacts/main.log"
CONTROLLED_USE_AUDIT_SCRIPT = PROGRAM / "tools/controlled_use_audit.py"
CONTROLLED_USE_AUDIT_REPORT = PROGRAM / "paper_alignment_v1/workspace/controlled_use_audit.json"
EQUAL_INFO_FIGURE_SCRIPT = ROOT_PROJECT_DIR / "evidence/reproducers/make_equal_information_figure.py"
EQUAL_INFO_FIGURE_PDF = ROOT_PROJECT_DIR / "evidence/figures/equal_information_market_controls.pdf"
EQUAL_INFO_FIGURE_PNG = ROOT_PROJECT_DIR / "evidence/figures/equal_information_market_controls.png"
CLAIM_SUMMARY = PROGRAM / "public/CLAIM_SUMMARY.md"
METHODOLOGY = PROGRAM / "public/METHODOLOGY.md"

PUBLIC_SOURCE_TABLE_EXCLUDED = {
    "apparatus_effort",
    "apparatus_effort_v4",
}

CLAIM_GAP = PROGRAM / "paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16/claim_gap_matrix.json"
DECISIVE_CONTINUATION = (
    PROGRAM / "paper_alignment_v1/workspace/decisive_continuation_2026_06_16/decisive_continuation_matrix.json"
)
FIELD_PROTOCOL = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_validity_audit_protocol.json"
)
FIELD_LOCAL = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_validity_local_evidence_summary.json"
)
FIELD_SOURCE_INVENTORY = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_validity_source_inventory.json"
)
FORECASTBENCH_ROW_SCHEMA_PILOT = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_forecastbench_row_schema_pilot.json"
)
FORECASTBENCH_SCORE_AUDIT = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_forecastbench_score_audit.json"
)
FORECASTBENCH_HUMAN_COMPARATOR_AUDIT = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"
    / "field_wide_forecastbench_human_comparator_audit.json"
)
POLYBENCH_SOURCE_PILOT = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_polybench_source_pilot.json"
)
PREDICTIONMARKETBENCH_ROW_SCHEMA_PILOT = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_predictionmarketbench_row_schema_pilot.json"
)
PROPHET_ARENA_ROW_SCHEMA_PILOT = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_prophet_arena_row_schema_pilot.json"
)
COVERAGE_SUMMARY = (
    PROGRAM / "paper_alignment_v1/workspace/experiment_coverage_2026_06_16/experiment_coverage_summary.json"
)
APPLIED_SIGNAL_COVERAGE = (
    PROGRAM
    / "paper_alignment_v1/workspace/applied_signal_coverage_2026_06_17/applied_signal_coverage_audit.json"
)
SCORED_USE_PROCEDURE = (
    PROGRAM
    / "paper_alignment_v1/workspace/scored_use_procedure_2026_06_17/scored_use_procedure_audit.json"
)
PROSPECTIVE_COUNTEREXPLANATION = (
    PROGRAM
    / "paper_alignment_v1/workspace/prospective_counterexplanation_design_2026_06_17/prospective_counterexplanation_design_audit.json"
)
REVIEWER_CONCERN_COVERAGE = (
    PROGRAM
    / "paper_alignment_v1/workspace/reviewer_concern_coverage_2026_06_17/reviewer_concern_coverage_audit.json"
)
EVIDENCE_UPGRADE_PLAN = (
    PROGRAM / "paper_alignment_v1/workspace/evidence_upgrade_plan_2026_06_17/evidence_upgrade_plan.json"
)
BENCHMARK_BLUEPRINT = (
    PROGRAM
    / "paper_alignment_v1/workspace/forecast_row_validity_benchmark_blueprint_2026_06_17"
    / "forecast_row_validity_benchmark_blueprint.json"
)
NUMERIC_TRACE = (
    PROGRAM / "paper_alignment_v1/workspace/numeric_claim_trace_2026_06_16/numeric_claim_trace.json"
)
EFFECTIVE_N_AUDIT = (
    PROGRAM
    / "paper_alignment_v1/workspace/effective_n_audit_2026_06_16/central_evidence_effective_n_audit.json"
)
LITERATURE_POSITIONING_AUDIT = (
    PROGRAM
    / "paper_alignment_v1/workspace/literature_positioning_2026_06_16/literature_positioning_audit.json"
)
PAPER_CLAIM_ALIGNMENT = PROGRAM / "paper_alignment_v1/workspace/paper_claim_alignment_report.json"
COHERENCE_AUDIT = PROGRAM / "paper_alignment_v1/workspace/paper_coherence_audit.json"
READINESS_AUDIT = PROGRAM / "law_validation_v1/workspace/paper_readiness_exhaustion_audit.json"
RENDERED_PDF_SMOKE_SCRIPT = PROGRAM / "tools/rendered_pdf_smoke_audit.py"
RENDERED_PDF_SMOKE = (
    PROGRAM / "paper_alignment_v1/workspace/rendered_pdf_smoke_2026_06_17/rendered_pdf_smoke_audit.json"
)

REQUIRED_SECTIONS = [
    r"\section{Introduction}",
    r"\section{Core empirical results}",
    r"\section{What this paper does not establish}",
    r"\section{Conclusion}",
    r"\section{Reproducibility}",
    r"\section{Evidence ledger for compressed diagnostics}",
    r"\section{Coverage audit for omitted or deferred work}",
]

REQUIRED_LABELS = [
    "tab:claim-map",
    "tab:corpus-contrast",
    "sec:row-estimand",
    "tab:lit-positioning",
    "fig:evidence-flow",
    "tab:core-results",
    "fig:equal-info-bars",
    "tab:benchmark-blueprint",
    "tab:low-prob-family",
    "tab:field-audit-protocol",
    "tab:public-benchmark-audit",
    "tab:reaudit-sources",
    "tab:next-tests",
    "tab:reproduction-status",
    "tab:evidence-ledger",
    "tab:coverage-audit",
]

BOUNDARY_PHRASES = [
    "not claims that LLMs are superior to markets or humans",
    "does not report a failure rate across the field",
    "It does not show that LLMs beat humans, human crowds, or prediction markets",
    "replication on open models and public questions is required",
    "not evidence of prevalence across the field",
    "raw benchmark rows are not present locally",
]

BUILD_WARNING_PATTERNS = [
    r"undefined references",
    r"Reference .* undefined",
    r"Citation .* undefined",
    r"LaTeX Warning: There were undefined",
    r"Overfull",
    r"Underfull",
    r"Float too large",
    r"float specifier",
    r"Label\(s\) may have changed",
]

PUBLIC_PROSE_PATTERNS = [
    r"\bF47\b",
    r"\bF100\b",
    r"\bconfident-NO\b",
    r"\blandmark\b",
    r"\bapparatus\b",
    r"\bactuator\b",
    r"\bactuators\b",
    r"\brouter\b",
    r"\brouting\b",
    r"\boracle\b",
    r"\bsham\b",
    r"\bMIMIC\b",
    r"\bmimic\b",
    r"\breceipt\b",
    r"\breceipts\b",
    r"\bartifact\b",
    r"\bartifacts\b",
    r"\bcarrier\b",
    r"\bcarriers\b",
    r"\bdemote\b",
    r"\bdemoted\b",
    r"\bchartered\b",
    r"\bno-call\b",
    r"\blaw\b",
    r"\bLaw\b",
    r"\bnurture\b",
    r"\blane\b",
    r"\blanes\b",
    r"\bharness\b",
    r"\bslop\b",
    r"\bbullshit\b",
    r"\bfrankenstein\b",
    r"\bfrankestein\b",
    r"Accepted claim spin",
    r"should not be sold",
    r"sold as",
    r"claim spine",
    r"paper spine",
    r"load-bearing",
    r"load bearing",
    r"lands hard",
    r"real work",
    r"market-ahead",
    r"stress control",
    r"evidence carrier",
    r"inheritance frame",
    r"not deployable",
    r"production use",
    r"Continuation gates",
    r"Stopping condition",
    r"failed gates",
    r"same-shape",
    r"same-model repair",
    r"low-cost retests",
    r"as the retests complete",
    r"The re-audit rule:",
    r"\bTODO\b",
    r"\bplaceholder\b",
    r"\bscaffold\b",
    r"\bclaim-ready\b",
    r"\bcamera-ready\b",
    r"\bnot camera-ready\b",
    r"should not",
    r"should be",
    r"should ",
    r"system recipe",
    r"repair loops",
    r"methodological backbone",
    r"orthogonal to the three axes",
    r"axis-1/2/3",
    r"right unit is closer",
    r"not an established mechanism",
    r"not as an established mechanism",
    r"mechanism established by the current data",
    r"mechanism established by current data",
]

MANUSCRIPT_DEPENDENT_REPORTS = {
    "controlled_use_audit": CONTROLLED_USE_AUDIT_REPORT,
    "applied_signal_coverage": APPLIED_SIGNAL_COVERAGE,
    "scored_use_procedure": SCORED_USE_PROCEDURE,
    "prospective_counterexplanation": PROSPECTIVE_COUNTEREXPLANATION,
    "reviewer_concern_coverage": REVIEWER_CONCERN_COVERAGE,
    "forecast_row_validity_benchmark_blueprint": BENCHMARK_BLUEPRINT,
    "numeric_claim_trace": NUMERIC_TRACE,
    "literature_positioning_audit": LITERATURE_POSITIONING_AUDIT,
    "paper_claim_alignment": PAPER_CLAIM_ALIGNMENT,
    "paper_coherence_audit": COHERENCE_AUDIT,
    "rendered_pdf_smoke_audit": RENDERED_PDF_SMOKE,
}

GENERATOR_DEPENDENT_REPORTS = {
    "controlled_use_audit": (PROGRAM / "tools/controlled_use_audit.py", CONTROLLED_USE_AUDIT_REPORT),
    "applied_signal_coverage": (PROGRAM / "tools/applied_signal_coverage_audit.py", APPLIED_SIGNAL_COVERAGE),
    "scored_use_procedure": (PROGRAM / "tools/scored_use_procedure_audit.py", SCORED_USE_PROCEDURE),
    "prospective_counterexplanation": (
        PROGRAM / "tools/prospective_counterexplanation_design_audit.py",
        PROSPECTIVE_COUNTEREXPLANATION,
    ),
    "reviewer_concern_coverage": (PROGRAM / "tools/reviewer_concern_coverage_audit.py", REVIEWER_CONCERN_COVERAGE),
    "forecast_row_validity_benchmark_blueprint": (
        PROGRAM / "tools/forecast_row_validity_benchmark_blueprint.py",
        BENCHMARK_BLUEPRINT,
    ),
    "numeric_claim_trace": (PROGRAM / "tools/numeric_claim_trace_audit.py", NUMERIC_TRACE),
    "literature_positioning_audit": (PROGRAM / "tools/literature_positioning_audit.py", LITERATURE_POSITIONING_AUDIT),
    "paper_claim_alignment": (PROGRAM / "tools/paper_claim_alignment_report.py", PAPER_CLAIM_ALIGNMENT),
    "paper_coherence_audit": (PROGRAM / "tools/paper_coherence_audit.py", COHERENCE_AUDIT),
    "rendered_pdf_smoke_audit": (RENDERED_PDF_SMOKE_SCRIPT, RENDERED_PDF_SMOKE),
}


@dataclass
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def compact_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def scalar(cur: sqlite3.Cursor, sql: str) -> Any:
    row = cur.execute(sql).fetchone()
    return row[0] if row else None


def check(name: str, condition: bool, detail: str) -> Check:
    return Check(name=name, status="pass" if condition else "fail", detail=detail)


def manuscript_path_checks(main_tex: str, draft_md: str) -> list[Check]:
    tex_paths = sorted(set(re.findall(r"\\path\{([^}]+)\}", main_tex)))
    missing_tex_paths = [path for path in tex_paths if not (REPO / path).exists()]

    listed_scripts = sorted(set(re.findall(r"\\detokenize\{([^}]+\.py)\}", main_tex)))
    missing_scripts: list[str] = []
    for script in listed_scripts:
        if script == "make_equal_information_figure.py":
            candidate = ROOT_PROJECT_DIR / "evidence/reproducers" / script
        else:
            candidate = PROGRAM / "tools" / script
        if not candidate.exists():
            missing_scripts.append(script)

    draft_paths = sorted(
        set(
            token
            for token in re.findall(r"`([^`]+)`", draft_md)
            if token.startswith(("analytics/", "papers/", "projects/", "src/"))
        )
    )
    missing_draft_paths = [path for path in draft_paths if not (REPO / path).exists()]

    return [
        check(
            "manuscript_path_references_resolve",
            not missing_tex_paths,
            f"{len(tex_paths)} TeX path references resolve"
            if not missing_tex_paths
            else "missing: " + ", ".join(missing_tex_paths[:8]),
        ),
        check(
            "manuscript_script_names_resolve",
            not missing_scripts,
            f"{len(listed_scripts)} listed script names resolve"
            if not missing_scripts
            else "missing: " + ", ".join(missing_scripts[:8]),
        ),
        check(
            "markdown_path_references_resolve",
            not missing_draft_paths,
            f"{len(draft_paths)} markdown path references resolve"
            if not missing_draft_paths
            else "missing: " + ", ".join(missing_draft_paths[:8]),
        ),
    ]


def figure_table_structure_checks(main_tex: str) -> list[Check]:
    issues: list[str] = []
    for kind in ("table", "figure"):
        pattern = re.compile(rf"\\begin\{{{kind}\}}.*?\\end\{{{kind}\}}", re.DOTALL)
        for idx, match in enumerate(pattern.finditer(main_tex), start=1):
            block = match.group(0)
            if r"\caption{" not in block:
                issues.append(f"{kind}#{idx}: missing caption")
            if r"\label{" not in block:
                issues.append(f"{kind}#{idx}: missing label")
    return [
        check(
            "tables_and_figures_have_captions_and_labels",
            not issues,
            "all table/figure blocks have captions and labels"
            if not issues
            else "; ".join(issues[:8]),
        )
    ]


def db_counts(db: Path) -> dict[str, int]:
    con = sqlite3.connect(db)
    cur = con.cursor()
    try:
        return {
            "contracts": int(scalar(cur, "SELECT COUNT(*) FROM contracts") or 0),
            "pilot_runs": int(scalar(cur, "SELECT COUNT(*) FROM pilot_runs") or 0),
            "pilot_calls": int(scalar(cur, "SELECT COUNT(*) FROM pilot_calls") or 0),
            "schema_ok_calls": int(scalar(cur, "SELECT COUNT(*) FROM pilot_calls WHERE schema_ok=1") or 0),
            "calls_with_brier": int(scalar(cur, "SELECT COUNT(*) FROM pilot_calls WHERE brier IS NOT NULL") or 0),
            "resolved_contracts": int(scalar(cur, "SELECT COUNT(*) FROM contracts WHERE y_known IS NOT NULL") or 0),
            "source_currency_rows": int(scalar(cur, "SELECT COUNT(*) FROM source_currency_gate_rows") or 0),
            "source_currency_conflicts": int(scalar(cur, "SELECT COUNT(*) FROM v_source_currency_gate_conflicts") or 0),
            "external_market_rows": int(scalar(cur, "SELECT COUNT(*) FROM v_external_market_baselines") or 0),
            "equal_information_rows": int(
                scalar(cur, "SELECT COUNT(*) FROM v_external_market_baselines WHERE equal_information_flag = 1") or 0
            ),
            "label_time_rows": int(scalar(cur, "SELECT COUNT(*) FROM dataset_label_time_gate_rows") or 0),
        }
    finally:
        con.close()


def db_top_sources(db: Path, limit: int = 12) -> list[tuple[str, int, int, int, int]]:
    con = sqlite3.connect(db)
    cur = con.cursor()
    try:
        rows = cur.execute(
            """
            SELECT COALESCE(source,'NULL') AS source,
                   COUNT(*) AS contracts,
                   SUM(CASE WHEN y_known IS NOT NULL THEN 1 ELSE 0 END) AS resolved,
                   SUM(CASE WHEN post_training_cutoff=0 THEN 1 ELSE 0 END) AS pre_cutoff,
                   SUM(CASE WHEN post_training_cutoff=1 THEN 1 ELSE 0 END) AS post_cutoff
            FROM contracts
            GROUP BY COALESCE(source,'NULL')
            ORDER BY contracts DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [(str(a), int(b), int(c or 0), int(d or 0), int(e or 0)) for a, b, c, d, e in rows]
    finally:
        con.close()


def source_checks(main_tex: str, draft_md: str) -> list[Check]:
    checks: list[Check] = []
    normalized_main = re.sub(r"\s+", " ", main_tex)
    normalized_draft = re.sub(r"\s+", " ", draft_md)
    missing_sections = [section for section in REQUIRED_SECTIONS if section not in main_tex]
    checks.append(
        check(
            "required_manuscript_sections",
            not missing_sections,
            "all required sections present" if not missing_sections else "missing: " + ", ".join(missing_sections),
        )
    )
    missing_labels = [label for label in REQUIRED_LABELS if f"\\label{{{label}}}" not in main_tex]
    checks.append(
        check(
            "required_tables_and_figures",
            not missing_labels,
            "all required labels present" if not missing_labels else "missing: " + ", ".join(missing_labels),
        )
    )
    checks.extend(figure_table_structure_checks(main_tex))
    missing_boundaries = [phrase for phrase in BOUNDARY_PHRASES if phrase not in main_tex]
    checks.append(
        check(
            "claim_boundaries_in_main_text",
            not missing_boundaries,
            "all broad-claim boundaries present"
            if not missing_boundaries
            else "missing: " + "; ".join(missing_boundaries),
        )
    )
    estimand_phrases = [
        "The paper's comparison unit is a scored forecast row",
        "validity indicator \\(V_{\\mathrm{row}}\\)",
        "not in the denominator for broad claims",
        "differences in Brier score are interpreted only after the row's information state is fixed",
    ]
    missing_estimand = [phrase for phrase in estimand_phrases if phrase not in main_tex]
    checks.append(
        check(
            "row_validity_estimand_defined",
            not missing_estimand,
            "forecast-row validity estimand is explicit"
            if not missing_estimand
            else "missing: " + "; ".join(missing_estimand),
        )
    )
    coverage_phrases = [
        "111 unique numbered rows in the full research log",
        "74 outside the curated paper ledger",
        "37 paper-relevant rows",
    ]
    missing_coverage_phrases = [
        phrase for phrase in coverage_phrases if phrase not in normalized_main or phrase not in normalized_draft
    ]
    checks.append(
        check(
            "full_log_coverage_counts_in_manuscript",
            not missing_coverage_phrases,
            "full-log and curated-ledger counts appear in main and draft"
            if not missing_coverage_phrases
            else "missing: " + "; ".join(missing_coverage_phrases),
        )
    )
    main_before_positioning = main_tex.split(r"\paragraph{Positioning.}", 1)[0]
    draft_before_positioning = draft_md.split("#### Positioning.", 1)[0]
    benchmark_front_phrases = [
        "companion benchmark design",
        "row validity, equal-information comparators, calibration",
        "which claim a packet can test before outcomes are scored",
        "what would make a positive result uninformative",
        "the simpler explanation it invites has already been made measurable",
        "not a current claim about a measured failure rate across the field",
    ]
    main_before_positioning_flat = compact_ws(main_before_positioning)
    draft_before_positioning_flat = compact_ws(draft_before_positioning)
    missing_benchmark_front = [
        phrase
        for phrase in benchmark_front_phrases
        if phrase not in main_before_positioning_flat or phrase not in draft_before_positioning_flat
    ]
    checks.append(
        check(
            "benchmark_design_front_loaded",
            not missing_benchmark_front,
            "companion benchmark design is visible before related work in main and draft"
            if not missing_benchmark_front
            else "missing: " + "; ".join(missing_benchmark_front),
        )
    )
    claim_summary_flat = compact_ws(read_text(CLAIM_SUMMARY))
    public_benchmark_phrases = [
        "This benchmark design is useful during research, not only after scoring.",
        "Before model calls are run or outcomes are known",
        "the simpler explanation that would make a positive result uninformative",
        "the missing timestamp, comparator, label-vintage, source, family, prompt-length, or market-overlap field",
    ]
    missing_public_benchmark = [phrase for phrase in public_benchmark_phrases if phrase not in claim_summary_flat]
    checks.append(
        check(
            "public_summary_benchmark_research_use",
            not missing_public_benchmark,
            "public summary states the companion benchmark's before-scoring research use"
            if not missing_public_benchmark
            else "missing: " + "; ".join(missing_public_benchmark),
        )
    )
    draft_refs = {
        "experiment_coverage_summary.py": "coverage summary",
        "applied_signal_coverage_audit.py": "applied signal coverage",
        "prospective_counterexplanation_design_audit.py": "prospective counter-explanation design",
        "reviewer_concern_coverage_audit.py": "reviewer concern coverage",
        "forecast_row_validity_benchmark_blueprint.py": "benchmark blueprint",
    }
    missing_draft_refs = [label for token, label in draft_refs.items() if token not in draft_md]
    checks.append(
        check(
            "markdown_draft_aligned",
            not missing_draft_refs,
            "draft references coverage, applied-signal, reviewer-concern, and benchmark-blueprint summaries"
            if not missing_draft_refs
            else "missing: " + ", ".join(missing_draft_refs),
        )
    )
    figure_wiring = {
        "main_includes_render": (
            r"\includegraphics[width=0.82\linewidth]{evidence/figures/equal_information_market_controls.png}" in main_tex
            or r"\includegraphics[width=0.82\linewidth]{evidence/figures/equal_information_market_controls.pdf}" in main_tex
        ),
        "main_lists_script": (
            r"\path{llm-forecast-calibration-cross-corpus/evidence/reproducers/}" in main_tex
            and r"\detokenize{make_equal_information_figure.py}" in main_tex
        ),
        "draft_includes_png": "evidence/figures/equal_information_market_controls.png" in draft_md,
    }
    failed = [name for name, ok in figure_wiring.items() if not ok]
    checks.append(
        check(
            "equal_information_figure_wired",
            not failed,
            "main render, draft PNG, and figure script references are present"
            if not failed
            else "missing: " + ", ".join(failed),
        )
    )
    checks.extend(manuscript_path_checks(main_tex, draft_md))
    return checks


def support_file_checks() -> list[Check]:
    files = {
        "main_pdf": MAIN_PDF,
        "controlled_use_audit_script": CONTROLLED_USE_AUDIT_SCRIPT,
        "controlled_use_audit_report": CONTROLLED_USE_AUDIT_REPORT,
        "equal_information_figure_script": EQUAL_INFO_FIGURE_SCRIPT,
        "equal_information_figure_pdf": EQUAL_INFO_FIGURE_PDF,
        "equal_information_figure_png": EQUAL_INFO_FIGURE_PNG,
        "claim_gap_matrix": CLAIM_GAP,
        "decisive_continuation_matrix": DECISIVE_CONTINUATION,
        "field_wide_protocol": FIELD_PROTOCOL,
        "field_wide_local_summary": FIELD_LOCAL,
        "field_wide_source_inventory": FIELD_SOURCE_INVENTORY,
        "forecastbench_row_schema_pilot": FORECASTBENCH_ROW_SCHEMA_PILOT,
        "forecastbench_score_audit": FORECASTBENCH_SCORE_AUDIT,
        "forecastbench_human_comparator_audit": FORECASTBENCH_HUMAN_COMPARATOR_AUDIT,
        "polybench_source_pilot": POLYBENCH_SOURCE_PILOT,
        "predictionmarketbench_row_schema_pilot": PREDICTIONMARKETBENCH_ROW_SCHEMA_PILOT,
        "prophet_arena_row_schema_pilot": PROPHET_ARENA_ROW_SCHEMA_PILOT,
        "experiment_coverage_summary": COVERAGE_SUMMARY,
        "applied_signal_coverage": APPLIED_SIGNAL_COVERAGE,
        "scored_use_procedure": SCORED_USE_PROCEDURE,
        "prospective_counterexplanation": PROSPECTIVE_COUNTEREXPLANATION,
        "reviewer_concern_coverage": REVIEWER_CONCERN_COVERAGE,
        "evidence_upgrade_plan": EVIDENCE_UPGRADE_PLAN,
        "forecast_row_validity_benchmark_blueprint": BENCHMARK_BLUEPRINT,
        "numeric_claim_trace": NUMERIC_TRACE,
        "central_evidence_effective_n_audit": EFFECTIVE_N_AUDIT,
        "literature_positioning_audit": LITERATURE_POSITIONING_AUDIT,
        "paper_claim_alignment": PAPER_CLAIM_ALIGNMENT,
        "paper_coherence_audit": COHERENCE_AUDIT,
        "paper_readiness_audit": READINESS_AUDIT,
        "rendered_pdf_smoke_script": RENDERED_PDF_SMOKE_SCRIPT,
        "rendered_pdf_smoke_audit": RENDERED_PDF_SMOKE,
    }
    missing = [name for name, path in files.items() if not path.exists() or path.stat().st_size == 0]
    return [
        check(
            "support_files_present",
            not missing,
            "all support files present" if not missing else "missing or empty: " + ", ".join(missing),
        )
    ]


def freshness_checks() -> list[Check]:
    source_mtime = max(MAIN_TEX.stat().st_mtime, DRAFT_MD.stat().st_mtime)
    stale = [
        name
        for name, path in MANUSCRIPT_DEPENDENT_REPORTS.items()
        if not path.exists() or path.stat().st_mtime < source_mtime
    ]
    stale_generators = [
        name
        for name, (script, report) in GENERATOR_DEPENDENT_REPORTS.items()
        if not script.exists()
        or not report.exists()
        or report.stat().st_mtime < script.stat().st_mtime
    ]
    return [
        check(
            "manuscript_dependent_reports_current",
            not stale,
            "all manuscript-dependent reports are newer than main.tex/draft.md"
            if not stale
            else "stale or missing: " + ", ".join(stale),
        ),
        check(
            "generator_dependent_reports_current",
            not stale_generators,
            "all generated reports are newer than their generator scripts"
            if not stale_generators
            else "stale or missing: " + ", ".join(stale_generators),
        ),
    ]


def generated_report_checks() -> list[Check]:
    checks: list[Check] = []
    claim_gap = read_json(CLAIM_GAP)
    decisive_continuation = read_json(DECISIVE_CONTINUATION)
    field_protocol = read_json(FIELD_PROTOCOL)
    local_summary = read_json(FIELD_LOCAL)
    source_inventory = read_json(FIELD_SOURCE_INVENTORY)
    forecastbench_pilot = read_json(FORECASTBENCH_ROW_SCHEMA_PILOT)
    forecastbench_score = read_json(FORECASTBENCH_SCORE_AUDIT)
    forecastbench_human = read_json(FORECASTBENCH_HUMAN_COMPARATOR_AUDIT)
    polybench_source = read_json(POLYBENCH_SOURCE_PILOT)
    predictionmarketbench_pilot = read_json(PREDICTIONMARKETBENCH_ROW_SCHEMA_PILOT)
    prophet_arena_pilot = read_json(PROPHET_ARENA_ROW_SCHEMA_PILOT)
    coverage = read_json(COVERAGE_SUMMARY)
    applied_signal = read_json(APPLIED_SIGNAL_COVERAGE)
    scored_use = read_json(SCORED_USE_PROCEDURE)
    prospective_counterexplanation = read_json(PROSPECTIVE_COUNTEREXPLANATION)
    reviewer_concerns = read_json(REVIEWER_CONCERN_COVERAGE)
    benchmark_blueprint = read_json(BENCHMARK_BLUEPRINT)
    numeric_trace = read_json(NUMERIC_TRACE)
    effective_n = read_json(EFFECTIVE_N_AUDIT)
    literature_positioning = read_json(LITERATURE_POSITIONING_AUDIT)
    claim_alignment = read_json(PAPER_CLAIM_ALIGNMENT)
    coherence = read_json(COHERENCE_AUDIT)
    readiness = read_json(READINESS_AUDIT)
    rendered_pdf = read_json(RENDERED_PDF_SMOKE)

    claim_rows = claim_gap.get("rows") or []
    checks.append(check("claim_gap_matrix_populated", len(claim_rows) >= 10, f"{len(claim_rows)} candidate results"))

    continuation_rows = decisive_continuation.get("rows") or []
    first_continuation = continuation_rows[0].get("continuation") if continuation_rows else None
    checks.append(
        check(
            "decisive_continuation_matrix",
            decisive_continuation.get("status") == "pass"
            and len(continuation_rows) >= 7
            and first_continuation == "Public benchmark validity extension",
            f"{len(continuation_rows)} continuation rows; status={decisive_continuation.get('status')}",
        )
    )

    seed_rows = field_protocol.get("benchmark_seed") or []
    checks.append(check("field_audit_seed_matrix", len(seed_rows) >= 12, f"{len(seed_rows)} benchmark/evaluation routes"))

    inventory_rows = source_inventory.get("rows") or []
    inventory_high_access = [
        row
        for row in inventory_rows
        if str(row.get("row_level_access_status", "")).startswith("high")
    ]
    inventory_medium_access = [
        row
        for row in inventory_rows
        if str(row.get("row_level_access_status", "")).startswith("medium")
    ]
    checks.append(
        check(
            "field_audit_source_inventory",
            len(inventory_rows) >= 12
            and len(inventory_high_access) >= 2
            and len(inventory_medium_access) >= 3,
            (
                f"{len(inventory_rows)} routes inventoried; "
                f"{len(inventory_high_access)} high-access routes; "
                f"{len(inventory_medium_access)} medium-access routes"
            ),
        )
    )

    checks.append(
        check(
            "forecastbench_row_schema_pilot",
            forecastbench_pilot.get("row_count", 0) >= 500
            and forecastbench_pilot.get("complete_validity_rows", 0) >= 475
            and forecastbench_pilot.get("conclusion_change_ready_rows") == 0,
            (
                f"{forecastbench_pilot.get('row_count')} rows; "
                f"{forecastbench_pilot.get('complete_validity_rows')} complete validity rows; "
                f"{forecastbench_pilot.get('conclusion_change_ready_rows')} conclusion-change rows"
            ),
        )
    )

    checks.append(
        check(
            "forecastbench_score_audit",
            forecastbench_score.get("forecast_files_scored", 0) >= 70
            and forecastbench_score.get("unique_scored_row_keys", 0) >= 521
            and forecastbench_score.get("unique_event_family_keys", 0) >= 200
            and forecastbench_score.get("files_with_market_slice", 0) >= 68
            and forecastbench_score.get("files_beating_market_baseline_event_family_capped") == forecastbench_score.get(
                "files_beating_market_baseline"
            )
            and float(forecastbench_score.get("median_market_delta_forecast_minus_baseline") or 0) > 0,
            (
                f"{forecastbench_score.get('forecast_files_scored')} files; "
                f"{forecastbench_score.get('unique_scored_row_keys')} unique rows; "
                f"{forecastbench_score.get('unique_event_family_keys')} event families; "
                f"{forecastbench_score.get('files_with_market_slice')} market slices; "
                "median market-slice delta="
                f"{forecastbench_score.get('median_market_delta_forecast_minus_baseline')}; "
                "capped median delta="
                f"{forecastbench_score.get('median_event_family_capped_market_delta_forecast_minus_baseline')}"
            ),
        )
    )

    human_summaries = {
        str(item.get("forecast_file")): item for item in forecastbench_human.get("summaries", []) if isinstance(item, dict)
    }
    human_public = human_summaries.get("2024-07-21.ForecastBench.human_public.json") or {}
    human_super = human_summaries.get("2024-07-21.ForecastBench.human_super.json") or {}
    human_public_brier = human_public.get("resolved_brier_non_imputed")
    human_super_brier = human_super.get("resolved_brier_non_imputed")
    checks.append(
        check(
            "forecastbench_human_comparator_audit",
            forecastbench_human.get("forecast_files_scored", 0) >= 141
            and forecastbench_human.get("unique_scored_row_keys", 0) >= 7259
            and forecastbench_human.get("unique_event_family_keys", 0) >= 766
            and forecastbench_human.get("files_with_market_slice", 0) >= 139
            and human_public.get("resolved_rows_non_imputed") == 577
            and human_super.get("resolved_rows_non_imputed") == 577
            and human_public.get("market_rows") == 2
            and human_super.get("market_rows") == 2
            and human_public_brier is not None
            and human_super_brier is not None
            and float(human_super_brier) < float(human_public_brier),
            (
                f"{forecastbench_human.get('forecast_files_scored')} files; "
                f"{forecastbench_human.get('unique_scored_row_keys')} unique rows; "
                f"{forecastbench_human.get('unique_event_family_keys')} event families; "
                f"human_super Brier={human_super_brier}; human_public Brier={human_public_brier}; "
                "human aggregate strict market overlap="
                f"{human_super.get('market_rows')}/{human_public.get('market_rows')}"
            ),
        )
    )

    checks.append(
        check(
            "polybench_source_pilot",
            polybench_source.get("repo_available") is True
            and polybench_source.get("database_ready") is False
            and polybench_source.get("pilot_status") == "source_schema_ready_dataset_unavailable",
            (
                f"repo_available={polybench_source.get('repo_available')}; "
                f"database_ready={polybench_source.get('database_ready')}; "
                f"status={polybench_source.get('pilot_status')}"
            ),
        )
    )

    checks.append(
        check(
            "predictionmarketbench_row_schema_pilot",
            predictionmarketbench_pilot.get("episodes", 0) >= 4
            and predictionmarketbench_pilot.get("settled_tickers", 0) >= 33
            and predictionmarketbench_pilot.get("market_baseline_rows", 0) >= 370000
            and predictionmarketbench_pilot.get("stored_model_forecast_rows") == 0,
            (
                f"{predictionmarketbench_pilot.get('episodes')} episodes; "
                f"{predictionmarketbench_pilot.get('settled_tickers')} settled tickers; "
                f"{predictionmarketbench_pilot.get('market_baseline_rows')} market baseline rows; "
                f"{predictionmarketbench_pilot.get('stored_model_forecast_rows')} stored model forecast rows"
            ),
        )
    )

    prophet_summary = prophet_arena_pilot.get("summary") or {}
    checks.append(
        check(
            "prophet_arena_row_schema_pilot",
            prophet_summary.get("task_rows", 0) >= 50
            and prophet_summary.get("resolved_rows", 0) >= 20
            and prophet_summary.get("rows_with_model_forecast_probability") == 0
            and prophet_summary.get("rows_with_same_time_baseline") == 0
            and prophet_summary.get("public_repositories_checked", 0) >= 5
            and prophet_summary.get("public_prophet_arena_trace_archives_found") == 0,
            (
                f"{prophet_summary.get('task_rows')} task rows; "
                f"{prophet_summary.get('resolved_rows')} resolved rows; "
                f"{prophet_summary.get('rows_with_model_forecast_probability')} model forecast rows; "
                f"{prophet_summary.get('rows_with_same_time_baseline')} same time baseline rows; "
                f"{prophet_summary.get('public_repositories_checked')} public repos checked; "
                f"{prophet_summary.get('public_prophet_arena_trace_archives_found')} Prophet Arena trace archives"
            ),
        )
    )

    summaries = local_summary.get("summaries") or []
    local_ok = bool(summaries) and summaries[0].get("raw_rows_available_locally") is False
    checks.append(check("halawi_local_summary_scoped", local_ok, "local summary marks raw rows unavailable"))

    checks.append(
        check(
            "experiment_coverage_complete",
            coverage.get("ledger_rows") == 37
            and (coverage.get("research_log") or {}).get("unique_rows_detected", 0) >= 100
            and (coverage.get("research_log") or {}).get("highest_numbered_row", 0) >= 118
            and (coverage.get("research_log") or {}).get("rows_outside_curated_ledger", 0) >= 70,
            (
                f"{coverage.get('ledger_rows')} ledger rows classified; "
                f"{(coverage.get('research_log') or {}).get('unique_rows_detected')} full-log rows; "
                f"{(coverage.get('research_log') or {}).get('rows_outside_curated_ledger')} outside curated ledger"
            ),
        )
    )

    applied_summary = applied_signal.get("summary") or {}
    supported_or_scoped = applied_summary.get(
        "supported_or_scoped_candidate", applied_summary.get("supported_or_bounded_positive")
    )
    checks.append(
        check(
            "applied_signal_coverage_complete",
            applied_summary.get("applied_components") >= 8
            and supported_or_scoped >= 6
            and applied_summary.get("negative_guidance_rows") >= 1
            and applied_summary.get("evidence_route_rows") >= 1
            and applied_summary.get("all_have_paper_anchor") is True
            and applied_summary.get("all_have_boundary") is True
            and applied_summary.get("all_have_next_check") is True
            and applied_summary.get("all_have_support_files") is True,
            (
                f"{applied_summary.get('applied_components')} applied components; "
                f"{supported_or_scoped} supported/scoped candidate; "
                f"{applied_summary.get('negative_guidance_rows')} negative guidance; "
                f"{applied_summary.get('evidence_route_rows')} evidence route"
            ),
        )
    )

    scored_summary = scored_use.get("summary") or {}
    checks.append(
        check(
            "scored_use_procedure_complete",
            scored_use.get("status") == "pass"
            and scored_summary.get("steps") >= 5
            and scored_summary.get("all_manuscript_text_present") is True
            and scored_summary.get("all_support_files_present") is True
            and scored_summary.get("all_stop_conditions_present") is True
            and scored_summary.get("applied_not_superiority") is True,
            (
                f"{scored_summary.get('steps')} steps; "
                f"text={scored_summary.get('all_manuscript_text_present')}; "
                f"support={scored_summary.get('all_support_files_present')}; "
                f"stops={scored_summary.get('all_stop_conditions_present')}"
            ),
        )
    )

    prospective_summary = prospective_counterexplanation.get("summary") or {}
    checks.append(
        check(
            "prospective_counterexplanation_design_complete",
            prospective_counterexplanation.get("status") == "pass"
            and prospective_summary.get("planned_results") >= 7
            and prospective_summary.get("all_manuscript_text_present") is True
            and prospective_summary.get("all_support_files_present") is True
            and prospective_summary.get("all_counter_explanations_present") is True
            and prospective_summary.get("all_before_scoring_design_checks_present") is True
            and prospective_summary.get("before_scoring_not_after_scoring") is True,
            (
                f"{prospective_summary.get('planned_results')} planned results; "
                f"text={prospective_summary.get('all_manuscript_text_present')}; "
                f"support={prospective_summary.get('all_support_files_present')}; "
                f"before_scoring={prospective_summary.get('before_scoring_not_after_scoring')}"
            ),
        )
    )

    reviewer_summary = reviewer_concerns.get("summary") or {}
    checks.append(
        check(
            "reviewer_concern_coverage_complete",
            reviewer_concerns.get("status") == "pass"
            and reviewer_summary.get("concerns") >= 8
            and reviewer_summary.get("all_text_checks_pass") is True
            and reviewer_summary.get("all_evidence_files_present") is True,
            (
                f"{reviewer_summary.get('concerns')} concerns; "
                f"text_checks={reviewer_summary.get('all_text_checks_pass')}; "
                f"evidence_files={reviewer_summary.get('all_evidence_files_present')}"
            ),
        )
    )

    blueprint_summary = benchmark_blueprint.get("summary") or {}
    blueprint_support = benchmark_blueprint.get("support") or {}
    checks.append(
        check(
            "forecast_row_validity_benchmark_blueprint",
            benchmark_blueprint.get("status") == "pass"
            and blueprint_summary.get("modules") >= 8
            and blueprint_summary.get("has_row_validity_core") is True
            and blueprint_summary.get("has_same_information_layer") is True
            and blueprint_summary.get("has_applied_tracks", 0) >= 4
            and blueprint_summary.get("has_counterexplanation_layer") is True
            and blueprint_summary.get("has_pre_scoring_research_guide") is True
            and blueprint_summary.get("has_prospective_inversion_planning") is True
            and blueprint_summary.get("is_companion_not_current_claim") is True
            and blueprint_support.get("claim_gap_rows", 0) >= 10
            and blueprint_support.get("continuation_rows", 0) >= 7
            and blueprint_support.get("field_protocol_schema_rows", 0) >= 13
            and blueprint_support.get("prospective_counterexplanation_rows", 0) >= 7,
            (
                f"{blueprint_summary.get('modules')} modules; "
                f"{blueprint_summary.get('has_applied_tracks')} applied tracks; "
                f"{blueprint_support.get('field_protocol_schema_rows')} field schema rows; "
                f"counter={blueprint_summary.get('has_counterexplanation_layer')}; "
                f"pre_scoring={blueprint_summary.get('has_pre_scoring_research_guide')}; "
                f"inversion_planning={blueprint_summary.get('has_prospective_inversion_planning')}; "
                f"counter_rows={blueprint_support.get('prospective_counterexplanation_rows')}"
            ),
        )
    )

    trace_checks = numeric_trace.get("checks") or []
    trace_failed = [item for item in trace_checks if item.get("status") != "pass"]
    trace_names = {str(item.get("name")) for item in trace_checks if isinstance(item, dict)}
    checks.append(
        check(
            "numeric_claim_trace_passes",
            numeric_trace.get("status") == "pass" and len(trace_checks) >= 20 and not trace_failed,
            f"{len(trace_checks)} headline numbers traced"
            if not trace_failed
                else "failed: " + ", ".join(str(item.get("name")) for item in trace_failed[:5]),
        )
    )
    prompt_trace_required = {
        "structured_prompt_gemini_scored_rows",
        "structured_prompt_expert_vs_bare_delta",
        "structured_prompt_expert_vs_placebo_delta",
        "structured_prompt_expert_vs_adjusted_bare_delta",
        "structured_prompt_expert_vs_all_market_delta",
        "structured_prompt_expert_vs_equal_information_market_delta",
        "structured_prompt_claude_scored_rows",
        "structured_prompt_claude_expert_vs_bare_delta",
    }
    missing_prompt_trace = sorted(prompt_trace_required - trace_names)
    checks.append(
        check(
            "structured_prompt_numeric_trace",
            not missing_prompt_trace,
            f"{len(prompt_trace_required)} structured-prompt numbers traced"
            if not missing_prompt_trace
            else "missing: " + ", ".join(missing_prompt_trace),
        )
    )

    effective_rows = effective_n.get("rows") or []
    checks.append(
        check(
            "central_evidence_effective_n_audit",
            effective_n.get("status") == "pass"
            and len(effective_rows) >= 9
            and effective_n.get("rows_with_missing_global_event_group", 0) >= 3,
            (
                f"{len(effective_rows)} central evidence rows; "
                f"{effective_n.get('rows_with_missing_global_event_group')} rows missing a global event family key"
            ),
        )
    )

    literature_rows = literature_positioning.get("rows") or []
    checks.append(
        check(
            "literature_positioning_audit",
            literature_positioning.get("status") == "pass" and len(literature_rows) >= 9,
            f"{len(literature_rows)} related-work rows; status={literature_positioning.get('status')}",
        )
    )

    alignment_checks = claim_alignment.get("alignment_checks") or []
    alignment_failed = [item for item in alignment_checks if item.get("status") != "pass"]
    checks.append(
        check(
            "paper_claim_endpoint_alignment",
            claim_alignment.get("alignment_status") == "pass"
            and len(alignment_checks) >= 7
            and not alignment_failed
            and claim_alignment.get("finding_count") == 0,
            (
                f"{len(alignment_checks)} endpoint checks; policy findings={claim_alignment.get('finding_count')}"
                if not alignment_failed
                else "failed: " + ", ".join(str(item.get("name")) for item in alignment_failed[:5])
            ),
        )
    )

    verdict = coherence.get("verdict") or {}
    coherence_rows = coherence.get("rows") or []
    coherence_lanes = {str(row.get("lane")) for row in coherence_rows if isinstance(row, dict)}
    checks.append(
        check(
            "coherence_verdict_scoped",
            verdict.get("broad_claim_ready") is False and bool(verdict.get("central_claim")),
            "broad claim is not marked ready; central claim present",
        )
    )
    checks.append(
        check(
            "coherence_counterexplanation_design",
            "before_scoring_counterexplanation_design" in coherence_lanes
            and "integrated_controlled_use_argument" in coherence_lanes
            and "omitted_and_deferred_work_coverage" in coherence_lanes,
            (
                f"{len(coherence_rows)} coherence rows; before-scoring claim-test rule present"
                if "before_scoring_counterexplanation_design" in coherence_lanes
                else "missing before-scoring counter-explanation design row"
            ),
        )
    )

    program_verdict = readiness.get("program_verdict") or {}
    checks.append(
        check(
            "readiness_verdict_scoped",
            program_verdict.get("scoped_paper_ready") is True
            and program_verdict.get("broad_market_human_claim_ready") is False,
            "scoped paper ready; broad market/human claim not ready",
        )
    )
    rendered_pdf_summary = rendered_pdf.get("summary") or {}
    rendered_pdf_file = rendered_pdf.get("pdf") or {}
    checks.append(
        check(
            "rendered_pdf_smoke_audit",
            rendered_pdf.get("status") == "pass"
            and rendered_pdf_file.get("pages", 0) >= 30
            and rendered_pdf_summary.get("required_text_checks", 0) >= 15
            and rendered_pdf_summary.get("internal_language_hits") == 0
            and rendered_pdf_file.get("pdf_current_with_tex") is True,
            (
                f"status={rendered_pdf.get('status')}; pages={rendered_pdf_file.get('pages')}; "
                f"text_checks={rendered_pdf_summary.get('required_text_checks')}; "
                f"internal_hits={rendered_pdf_summary.get('internal_language_hits')}"
            ),
        )
    )
    return checks


def database_checks(db: Path) -> list[Check]:
    counts = db_counts(db)
    floors = {
        "source_currency_rows": 240,
        "source_currency_conflicts": 39,
        "external_market_rows": 103,
        "equal_information_rows": 52,
        "label_time_rows": 165,
    }
    bad = [f"{key}={counts.get(key)} < {floor}" for key, floor in floors.items() if counts.get(key, 0) < floor]
    detail = "; ".join(f"{key}={counts[key]}" for key in sorted(counts))

    methodology = read_text(METHODOLOGY)
    snapshot_labels = {
        "contracts": "contracts",
        "pilot runs": "pilot_runs",
        "pilot calls": "pilot_calls",
        "schema-ok calls": "schema_ok_calls",
        "calls with Brier": "calls_with_brier",
        "resolved contracts": "resolved_contracts",
    }
    stale_snapshot: list[str] = []
    for label, key in snapshot_labels.items():
        match = re.search(rf"- {re.escape(label)}: `([0-9,]+)`", methodology)
        observed = int(match.group(1).replace(",", "")) if match else None
        expected = counts[key]
        if observed != expected:
            stale_snapshot.append(f"{label}: doc={observed} db={expected}")

    source_rows = db_top_sources(db)
    stale_sources: list[str] = []
    for source, contracts, resolved, pre_cutoff, post_cutoff in source_rows:
        if source in PUBLIC_SOURCE_TABLE_EXCLUDED:
            continue
        expected = f"| `{source}` | {contracts} | {resolved} | {pre_cutoff} | {post_cutoff} |"
        if expected not in methodology:
            stale_sources.append(expected)

    return [
        check("database_evidence_counts", not bad, detail if not bad else "; ".join(bad)),
        check(
            "methodology_db_snapshot_current",
            not stale_snapshot,
            "methodology DB snapshot matches SQLite"
            if not stale_snapshot
            else "; ".join(stale_snapshot),
        ),
        check(
            "methodology_source_coverage_current",
            not stale_sources,
            "methodology source table matches SQLite top public buckets"
            if not stale_sources
            else "missing/stale rows: " + "; ".join(stale_sources[:3]),
        ),
    ]


def build_log_checks() -> list[Check]:
    log_text = read_text(MAIN_LOG)
    hits = []
    for pattern in BUILD_WARNING_PATTERNS:
        if re.search(pattern, log_text, flags=re.IGNORECASE):
            hits.append(pattern)
    return [check("latex_log_clean", not hits, "no warning patterns found" if not hits else "hits: " + ", ".join(hits))]


def public_prose_checks(extra_paths: list[Path]) -> list[Check]:
    paths = [MAIN_TEX, DRAFT_MD, CLAIM_SUMMARY, METHODOLOGY, *extra_paths]
    hits = []
    for path in paths:
        text = read_text(path)
        for pattern in PUBLIC_PROSE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                hits.append(f"{rel(path)}:{match.group(0)}")
                break
    return [check("public_prose_clean", not hits, "no banned/internal phrases found" if not hits else "; ".join(hits))]


def manuscript_project_label_checks() -> list[Check]:
    hits = []
    for path in [MAIN_TEX, DRAFT_MD]:
        text = read_text(path)
        for pattern in [r"\bGP-245\b", r"\bStage-[A-Z]\b"]:
            match = re.search(pattern, text)
            if match:
                hits.append(f"{rel(path)}:{match.group(0)}")
                break
    return [
        check(
            "manuscript_project_labels_removed",
            not hits,
            "no internal project/stage labels in manuscript"
            if not hits
            else "; ".join(hits),
        )
    ]


def build_report(db: Path) -> dict[str, Any]:
    main_tex = read_text(MAIN_TEX)
    draft_md = read_text(DRAFT_MD)
    extra_public = [
        PROGRAM / "paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16/claim_gap_matrix.md",
        PROGRAM / "paper_alignment_v1/workspace/decisive_continuation_2026_06_16/decisive_continuation_matrix.md",
        PROGRAM
        / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_validity_audit_protocol.md",
        PROGRAM
        / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_validity_local_evidence_summary.md",
        PROGRAM
        / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_validity_source_inventory.md",
        PROGRAM
        / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_forecastbench_row_schema_pilot.md",
        PROGRAM
        / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_forecastbench_score_audit.md",
        PROGRAM
        / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_polybench_source_pilot.md",
        PROGRAM
        / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_predictionmarketbench_row_schema_pilot.md",
        PROGRAM / "paper_alignment_v1/workspace/experiment_coverage_2026_06_16/experiment_coverage_summary.md",
        PROGRAM
        / "paper_alignment_v1/workspace/applied_signal_coverage_2026_06_17/applied_signal_coverage_audit.md",
        PROGRAM
        / "paper_alignment_v1/workspace/scored_use_procedure_2026_06_17/scored_use_procedure_audit.md",
        PROGRAM
        / "paper_alignment_v1/workspace/prospective_counterexplanation_design_2026_06_17"
        / "prospective_counterexplanation_design_audit.md",
        PROGRAM
        / "paper_alignment_v1/workspace/reviewer_concern_coverage_2026_06_17/reviewer_concern_coverage_audit.md",
        PROGRAM
        / "paper_alignment_v1/workspace/forecast_row_validity_benchmark_blueprint_2026_06_17"
        / "forecast_row_validity_benchmark_blueprint.md",
        PROGRAM / "paper_alignment_v1/workspace/numeric_claim_trace_2026_06_16/numeric_claim_trace.md",
        PROGRAM
        / "paper_alignment_v1/workspace/effective_n_audit_2026_06_16/central_evidence_effective_n_audit.md",
        PROGRAM
        / "paper_alignment_v1/workspace/literature_positioning_2026_06_16/literature_positioning_audit.md",
        PROGRAM / "paper_alignment_v1/workspace/paper_claim_alignment_report.md",
        PROGRAM / "paper_alignment_v1/workspace/controlled_use_audit.md",
        PROGRAM / "paper_alignment_v1/workspace/evidence_upgrade_plan_2026_06_17/evidence_upgrade_plan.md",
        PROGRAM
        / "paper_alignment_v1/workspace/rendered_pdf_smoke_2026_06_17/rendered_pdf_smoke_audit.md",
    ]
    checks = [
        *support_file_checks(),
        *freshness_checks(),
        *source_checks(main_tex, draft_md),
        *generated_report_checks(),
        *database_checks(db),
        *build_log_checks(),
        *manuscript_project_label_checks(),
        *public_prose_checks(extra_public),
    ]
    failed = [item for item in checks if item.status != "pass"]
    return {
        "schema": "gp245-submission-readiness-audit-v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "pass" if not failed else "fail",
        "checks": [item.__dict__ for item in checks],
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["name", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# GP-245 Submission Readiness Audit",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Status: `{report['status']}`",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for item in report["checks"]:
        detail = str(item["detail"]).replace("|", "/")
        lines.append(f"| {item['name']} | {item['status']} | {detail} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    report = build_report(args.db)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "submission_readiness_audit.json"
    csv_path = args.out_dir / "submission_readiness_audit.csv"
    md_path = args.out_dir / "submission_readiness_audit.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, report["checks"])
    md_path.write_text(build_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": report["schema"],
                "status": report["status"],
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
