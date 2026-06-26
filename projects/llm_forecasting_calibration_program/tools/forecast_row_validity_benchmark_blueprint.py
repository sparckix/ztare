#!/usr/bin/env python3
"""Generate the companion forecast-row validity benchmark blueprint.

The blueprint is mined from the current claim-gap and continuation matrices.
It is a design file for future public benchmark construction, not a new
empirical result and not a claim that current evidence is field-wide.
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
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/forecast_row_validity_benchmark_blueprint_2026_06_17"

CLAIM_GAP = PROGRAM / "paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16/claim_gap_matrix.json"
DECISIVE_CONTINUATION = (
    PROGRAM / "paper_alignment_v1/workspace/decisive_continuation_2026_06_16/decisive_continuation_matrix.json"
)
FIELD_PROTOCOL = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_validity_audit_protocol.json"
)
APPLIED_SIGNAL = (
    PROGRAM
    / "paper_alignment_v1/workspace/applied_signal_coverage_2026_06_17/applied_signal_coverage_audit.json"
)
PROSPECTIVE_COUNTEREXPLANATION = (
    PROGRAM
    / "paper_alignment_v1/workspace/prospective_counterexplanation_design_2026_06_17/prospective_counterexplanation_design_audit.json"
)

BLUEPRINT_COLUMNS = [
    "module",
    "purpose",
    "minimum_fields_or_rows",
    "primary_score_or_output",
    "counter_explanation_design",
    "controls",
    "current_gap_source",
    "promotion_condition",
    "failure_condition",
]


BLUEPRINT_ROWS: list[dict[str, str]] = [
    {
        "module": "Row-validity core",
        "purpose": "Make each forecast row interpretable before any model, human, or market comparison.",
        "minimum_fields_or_rows": (
            "row id; question or market id; forecast timestamp; model cutoff or retrieval window; "
            "resolution timestamp; outcome label; label vintage; event-family id"
        ),
        "primary_score_or_output": "Eligibility labels for source currency, label-time validity, and event-family grouping.",
        "counter_explanation_design": "Rules out retrieval, source-familiarity, and label-vintage explanations before a row enters broad comparisons.",
        "controls": "Rows failing source-currency or label-time checks are scored separately from valid forecast rows.",
        "current_gap_source": "Claim-gap matrix: source-general and field-wide claims need external rows.",
        "promotion_condition": "At least two public benchmark families expose enough row metadata to recompute conclusions.",
        "failure_condition": "Public benchmark families already carry complete validity metadata and conclusions do not change.",
    },
    {
        "module": "Same-information comparator layer",
        "purpose": "Separate model forecast accuracy from unequal market or human information timing.",
        "minimum_fields_or_rows": "same-contract market, human, crowd, or expert probability with baseline timestamp.",
        "primary_score_or_output": "Paired Brier/log-score delta against a comparator under the same pre-outcome information rule.",
        "counter_explanation_design": "Rules out comparator timing and contract-mismatch explanations before reporting model gains.",
        "controls": "Event-family capped estimates; source-stratified estimates; no unmatched comparator bars.",
        "current_gap_source": "Current Polymarket and Manifold slices are small; ForecastBench human aggregate has only two strict market-overlap rows per file.",
        "promotion_condition": "A larger predeclared source-balanced packet shows a model-derived score or blend beats the matched baseline.",
        "failure_condition": "The matched baseline remains better or gains disappear under source/event-family checks.",
    },
    {
        "module": "Point-probability calibration track",
        "purpose": "Test whether simple post-processing improves model probabilities on rows that pass the source-currency check.",
        "minimum_fields_or_rows": "raw model probability; source-currency label; label-time label; source; horizon; family.",
        "primary_score_or_output": "Brier delta of calibrated probability versus raw probability.",
        "counter_explanation_design": "Rules out retrospective-row gains by separating forward-looking and source-visible rows before scoring.",
        "controls": "Forward-looking rows and source-visible rows scored separately; family and source splits reported.",
        "current_gap_source": "Low-probability correction improves eligible rows but regresses on source-visible rows.",
        "promotion_condition": "Rule improves larger public source-balanced packet and survives open-weight replication.",
        "failure_condition": "Rule regresses on eligible rows or only works on source-visible/retrospective rows.",
    },
    {
        "module": "Relative-judgment track",
        "purpose": "Test whether pairwise comparisons are a better interface than direct probabilities.",
        "minimum_fields_or_rows": "contract pairs; orientation; source; event-family id; pairwise choice; resolved pair outcome.",
        "primary_score_or_output": "Pairwise accuracy, utility, and optional predeclared graph-calibrated probabilities.",
        "counter_explanation_design": "Rules out orientation imbalance, source-pair imbalance, and overfitted probability conversion.",
        "controls": "Orientation balance; same-source and source-heldout checks; prospective market-freeze packet before probability translation.",
        "current_gap_source": "Pairwise ranking is supported; probability conversion lacks prospective and market controls.",
        "promotion_condition": "Predeclared pairwise-derived probabilities or rankings beat raw, calibrated, and market controls.",
        "failure_condition": "Pairwise-derived outputs lose to raw, calibrated, or market-only controls.",
    },
    {
        "module": "Intervention track",
        "purpose": "Test whether structured prompts or procedures improve scored probabilities beyond placebo and calibration baselines.",
        "minimum_fields_or_rows": "bare, placebo, intervention, calibrated-bare, source, family, market/human comparator where available.",
        "primary_score_or_output": "Paired Brier delta against bare, placebo, calibrated-bare, and same-information baselines.",
        "counter_explanation_design": "Rules out prompt-length, placebo, source-mix, and one-family explanations before broadening an intervention result.",
        "controls": "Length-matched placebo; source splits; family replication; matched market/human rows when available.",
        "current_gap_source": "Gemini expert-training prompt passes scoped checks; partial Claude validation does not reproduce the effect.",
        "promotion_condition": "At least one intervention beats bare, placebo, calibrated-bare, and matched baseline without source/family regression.",
        "failure_condition": "Effect fails family replication or remains dominated by matched market/human baselines.",
    },
    {
        "module": "Family-selection and review track",
        "purpose": "Decide whether observable features can recover best-family headroom or justify external review.",
        "minimum_fields_or_rows": "family probabilities; family diagnostics; source; horizon; event-family id; external review cost if used.",
        "primary_score_or_output": "Cost-adjusted Brier or utility delta versus simple pool and calibrated baseline.",
        "counter_explanation_design": "Rules out hindsight family choice by predeclaring features, review cost, and heldout splits.",
        "controls": "Heldout source and family splits; explicit review cost; market/human additivity when joined.",
        "current_gap_source": "Best-family-in-hindsight headroom exists but current cheap selection rules do not recover it.",
        "promotion_condition": "Observable or external-review rule recovers headroom after cost and survives heldout splits.",
        "failure_condition": "Selection rule fails simple pools or cannot justify review cost.",
    },
    {
        "module": "Open-weight replication track",
        "purpose": "Separate provider-specific findings from more portable forecasting behavior.",
        "minimum_fields_or_rows": "public rows, prompts, scoring code, open-weight model outputs, proprietary-provider comparison rows.",
        "primary_score_or_output": "Replication of validity, market-control, calibration, ranking, and intervention results.",
        "counter_explanation_design": "Rules out provider-snapshot explanations by repeating the same public-row checks on open-weight models.",
        "controls": "Same prompts where possible; public corpus only; source/family/event-family splits.",
        "current_gap_source": "Current scored calls use proprietary APIs or CLIs.",
        "promotion_condition": "Core scoped findings reproduce or differences are precisely bounded.",
        "failure_condition": "Findings depend on proprietary providers and do not transfer.",
    },
    {
        "module": "Public low-overlap substitute track",
        "purpose": "Make private low-overlap elicitation diagnostics externally checkable.",
        "minimum_fields_or_rows": "public niche-domain questions with novelty, source, topic, length, and horizon metadata.",
        "primary_score_or_output": "Replication of elicitation-channel diagnostics after design axes are separated.",
        "counter_explanation_design": "Rules out private-corpus specificity by separating novelty, source, topic, length, and horizon on public rows.",
        "controls": "Four-axis design that breaks novelty, source, topic, and horizon confounds.",
        "current_gap_source": "Private low-overlap corpus is secondary and not directly releasable.",
        "promotion_condition": "Diagnostics replicate on sanitized or substitute public corpus.",
        "failure_condition": "Diagnostics vanish or are explained by source, length, topic, or horizon.",
    },
]


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def build_report(generated_at: str) -> dict[str, Any]:
    claim_gap = read_json(CLAIM_GAP)
    continuation = read_json(DECISIVE_CONTINUATION)
    field_protocol = read_json(FIELD_PROTOCOL)
    applied = read_json(APPLIED_SIGNAL)
    prospective = read_json(PROSPECTIVE_COUNTEREXPLANATION)

    claim_rows = claim_gap.get("rows") or []
    continuation_rows = continuation.get("rows") or []
    schema_rows = field_protocol.get("row_schema") or []
    applied_summary = applied.get("summary") or {}
    prospective_summary = prospective.get("summary") or {}
    support_files = [CLAIM_GAP, DECISIVE_CONTINUATION, FIELD_PROTOCOL, APPLIED_SIGNAL, PROSPECTIVE_COUNTEREXPLANATION]

    return {
        "schema": "gp245-forecast-row-validity-benchmark-blueprint-v1",
        "generated_at": generated_at,
        "status": "pass",
        "interpretation": (
            "The paper's missing-evidence map implies a companion public benchmark design. The blueprint is "
            "a specification for future data collection and evaluation, and a pre-scoring research guide: "
            "row facts choose the comparator and failure condition before outcomes are scored. Each track "
            "also names what would make a positive result uninformative, so the simpler explanation is "
            "measurable before scoring. It is not a current field-wide result."
        ),
        "support": {
            "claim_gap_rows": len(claim_rows),
            "continuation_rows": len(continuation_rows),
            "field_protocol_schema_rows": len(schema_rows),
            "applied_components": applied_summary.get("applied_components"),
            "prospective_counterexplanation_rows": prospective_summary.get("planned_results"),
            "support_files": [rel(path) for path in support_files if path.exists()],
        },
        "rows": BLUEPRINT_ROWS,
        "summary": {
            "modules": len(BLUEPRINT_ROWS),
            "has_row_validity_core": any(row["module"] == "Row-validity core" for row in BLUEPRINT_ROWS),
            "has_same_information_layer": any(
                row["module"] == "Same-information comparator layer" for row in BLUEPRINT_ROWS
            ),
            "has_applied_tracks": sum(
                1
                for row in BLUEPRINT_ROWS
                if row["module"]
                in {
                    "Point-probability calibration track",
                    "Relative-judgment track",
                    "Intervention track",
                    "Family-selection and review track",
                }
            ),
            "has_counterexplanation_layer": all(
                bool(row.get("counter_explanation_design")) for row in BLUEPRINT_ROWS
            ),
            "has_pre_scoring_research_guide": all(
                bool(row.get("promotion_condition")) and bool(row.get("failure_condition"))
                for row in BLUEPRINT_ROWS
            ),
            "has_prospective_inversion_planning": all(
                bool(row.get("counter_explanation_design"))
                and bool(row.get("promotion_condition"))
                and bool(row.get("failure_condition"))
                for row in BLUEPRINT_ROWS
            ),
            "is_companion_not_current_claim": True,
        },
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BLUEPRINT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(report: dict[str, Any]) -> str:
    support = report["support"]
    summary = report["summary"]
    lines = [
        "# Forecast Row Validity Benchmark Blueprint",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Status: `{report['status']}`",
        "",
        str(report["interpretation"]),
        "",
        f"Modules: `{summary['modules']}`",
        f"Claim-gap rows consumed: `{support['claim_gap_rows']}`",
        f"Continuation rows consumed: `{support['continuation_rows']}`",
        f"Field-protocol schema rows consumed: `{support['field_protocol_schema_rows']}`",
        f"Applied components consumed: `{support['applied_components']}`",
        f"Prospective counter-explanation rows consumed: `{support['prospective_counterexplanation_rows']}`",
        f"Prospective inversion-planning guide: `{summary['has_prospective_inversion_planning']}`",
        "",
        "| Module | Purpose | Minimum fields or rows | Primary score or output | Counter-explanation design | Controls | Promotion condition | Failure condition |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in report["rows"]:
        values = [
            row["module"],
            row["purpose"],
            row["minimum_fields_or_rows"],
            row["primary_score_or_output"],
            row["counter_explanation_design"],
            row["controls"],
            row["promotion_condition"],
            row["failure_condition"],
        ]
        lines.append("| " + " | ".join(str(value).replace("|", "/") for value in values) + " |")
    lines.extend(
        [
            "",
            "## Support Files",
            "",
        ]
    )
    for path in support["support_files"]:
        lines.append(f"- `{path}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    report = build_report(generated_at)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    json_path = args.out_dir / "forecast_row_validity_benchmark_blueprint.json"
    csv_path = args.out_dir / "forecast_row_validity_benchmark_blueprint.csv"
    md_path = args.out_dir / "forecast_row_validity_benchmark_blueprint.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, report["rows"])
    md_path.write_text(build_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": report["schema"],
                "status": report["status"],
                "modules": report["summary"]["modules"],
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
