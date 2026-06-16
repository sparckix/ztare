#!/usr/bin/env python3
"""Emit the GP-245 field-wide row-validity audit protocol.

No network access, model calls, or database mutation. The output is a seed
manifest for the field-wide measurement extension described in the paper: which
benchmark families to audit, which row-level fields to collect, and what
conclusion-change test would make the audit scientifically meaningful.
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
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"

SCHEMA_COLUMNS = [
    "field",
    "required",
    "meaning",
    "valid_values_or_format",
    "why_it_matters",
]

SEED_COLUMNS = [
    "benchmark_id",
    "benchmark_class",
    "citation_key",
    "audit_unit",
    "public_access_route",
    "row_fields_to_collect",
    "primary_validity_risk",
    "minimum_conclusion_change_test",
    "pilot_sample",
    "paper_grade_sample",
    "priority",
    "current_status",
]


SCHEMA_ROWS = [
    {
        "field": "row_id",
        "required": "yes",
        "meaning": "Stable benchmark-local row identifier.",
        "valid_values_or_format": "string",
        "why_it_matters": "Makes every exclusion, join, and score reproducible.",
    },
    {
        "field": "question_or_market_id",
        "required": "yes",
        "meaning": "Question, contract, market, or scenario identifier.",
        "valid_values_or_format": "string",
        "why_it_matters": "Allows same-contract joins to markets, human forecasts, and labels.",
    },
    {
        "field": "forecast_timestamp",
        "required": "yes",
        "meaning": "When the model, human, crowd, or agent forecast was made.",
        "valid_values_or_format": "ISO-8601 timestamp or documented date",
        "why_it_matters": "Defines the information state of the forecast.",
    },
    {
        "field": "model_cutoff_or_retrieval_window",
        "required": "yes for model rows",
        "meaning": "Model knowledge cutoff, retrieval cutoff, or timestamped input bundle.",
        "valid_values_or_format": "date, timestamp, or snapshot identifier",
        "why_it_matters": "Separates future-event prediction from source-visible answer recall.",
    },
    {
        "field": "resolution_timestamp",
        "required": "yes for resolved rows",
        "meaning": "When the event outcome became resolvable under the benchmark rules.",
        "valid_values_or_format": "ISO-8601 timestamp or documented date",
        "why_it_matters": "Allows source-currency classification for each model generation.",
    },
    {
        "field": "outcome_label",
        "required": "yes for scored rows",
        "meaning": "Resolved binary or multiclass label used for scoring.",
        "valid_values_or_format": "benchmark-specific label plus normalized binary label when applicable",
        "why_it_matters": "Defines the proper-score target.",
    },
    {
        "field": "label_vintage",
        "required": "yes for official-data or revised labels",
        "meaning": "The data vintage admissible at resolution time.",
        "valid_values_or_format": "timestamp, source revision id, or explicit not-applicable",
        "why_it_matters": "Prevents scoring against values revised after the forecast should have settled.",
    },
    {
        "field": "same_contract_baseline_type",
        "required": "yes for comparisons",
        "meaning": "Human, crowd, market, agent, or no same-contract baseline.",
        "valid_values_or_format": "human|crowd|market|agent|none",
        "why_it_matters": "Distinguishes model-only scoring from comparative claims.",
    },
    {
        "field": "baseline_timestamp",
        "required": "yes when a baseline is used",
        "meaning": "When the comparator probability, consensus, or market price was observed.",
        "valid_values_or_format": "ISO-8601 timestamp or documented date",
        "why_it_matters": "Tests whether the model and comparator had equal information.",
    },
    {
        "field": "event_family_id",
        "required": "yes",
        "meaning": "Identifier tying sibling markets, repeated questions, and duplicate events together.",
        "valid_values_or_format": "string",
        "why_it_matters": "Prevents row-rich but event-thin conclusions.",
    },
    {
        "field": "decision_rule_status",
        "required": "yes",
        "meaning": "Whether the tested rule was predeclared, tuned, replayed, or prospective.",
        "valid_values_or_format": "predeclared|tuned|retrospective_replay|prospective|unknown",
        "why_it_matters": "Separates exploratory analysis from supported decision rules.",
    },
    {
        "field": "score_before_validity_filter",
        "required": "yes when available",
        "meaning": "Original reported score on the benchmark slice.",
        "valid_values_or_format": "numeric plus metric name",
        "why_it_matters": "Needed to test whether row-level validity changes conclusions.",
    },
    {
        "field": "score_after_validity_filter",
        "required": "yes for audited slices",
        "meaning": "Recomputed score after source-currency, label-time, and equal-information checks.",
        "valid_values_or_format": "numeric plus metric name",
        "why_it_matters": "Supplies the conclusion-change result.",
    },
]


SEED_ROWS = [
    {
        "benchmark_id": "forecastbench",
        "benchmark_class": "future-question benchmark",
        "citation_key": "karger2024forecastbench",
        "audit_unit": "resolved question row",
        "public_access_route": "public benchmark release and paper appendices",
        "row_fields_to_collect": "forecast timestamp; model cutoff; resolution timestamp; expert/human comparator timestamp; source and topic strata",
        "primary_validity_risk": "future-only status may differ across model generations and replications",
        "minimum_conclusion_change_test": "Recompute model-vs-human/crowd scores after filtering rows whose resolution date is not after the evaluated model cutoff.",
        "pilot_sample": "50 resolved rows or all rows if fewer are public",
        "paper_grade_sample": "all public resolved rows with event-family de-duplication",
        "priority": "high",
        "current_status": "protocol only; not yet audited here",
    },
    {
        "benchmark_id": "halawi_2024_binary_resolved",
        "benchmark_class": "forecasting system benchmark",
        "citation_key": "halawi2024approaching",
        "audit_unit": "binary resolved question row",
        "public_access_route": "public dataset release referenced by the paper",
        "row_fields_to_collect": "resolution date; source platform; original model cutoff; replication model cutoff; human baseline timestamp if available",
        "primary_validity_risk": "corpus-validity drift for newer model generations",
        "minimum_conclusion_change_test": "Compare reported scores with scores after resolve_date > model_cutoff filtering for each evaluated generation.",
        "pilot_sample": "all rows needed for date histogram first; then 100-row scored audit",
        "paper_grade_sample": "full binary-resolved dataset",
        "priority": "high",
        "current_status": "paper reports a date-distribution warning; full row audit not yet included",
    },
    {
        "benchmark_id": "aia_forecaster",
        "benchmark_class": "forecasting system and market-consensus comparison",
        "citation_key": "alur2025aiaforecaster",
        "audit_unit": "question forecast row",
        "public_access_route": "paper tables plus any released question/system logs",
        "row_fields_to_collect": "question timestamp; retrieval window; market-consensus timestamp; human-superforecaster timestamp; resolution date",
        "primary_validity_risk": "market, model, and human comparison bars may not share the same information time",
        "minimum_conclusion_change_test": "Recompute additive-value claims only on rows with same-contract, same-time market consensus.",
        "pilot_sample": "50 rows with market-consensus joins",
        "paper_grade_sample": "all rows used for market/human comparison claims",
        "priority": "high",
        "current_status": "protocol only; not yet audited here",
    },
    {
        "benchmark_id": "prediction_arena",
        "benchmark_class": "live market-agent benchmark",
        "citation_key": "zhang2026predictionarena",
        "audit_unit": "market trade or forecast decision",
        "public_access_route": "paper release, market logs, and benchmark leaderboard if public",
        "row_fields_to_collect": "decision timestamp; market price at decision; market platform; fees/liquidity; resolution timestamp; agent input bundle",
        "primary_validity_risk": "profit and loss can mix probability accuracy with execution, fees, and liquidity",
        "minimum_conclusion_change_test": "Separate proper probabilistic score from trading profit on the same decisions and compare conclusion direction.",
        "pilot_sample": "50 decisions across at least two platforms",
        "paper_grade_sample": "all public decisions with platform-stratified scores",
        "priority": "medium",
        "current_status": "protocol only; not yet audited here",
    },
    {
        "benchmark_id": "polybench",
        "benchmark_class": "timestamped market replay benchmark",
        "citation_key": "cheng2026polybench",
        "audit_unit": "market snapshot row",
        "public_access_route": "released replay snapshots if public",
        "row_fields_to_collect": "snapshot timestamp; order-book state; news bundle timestamp; model forecast timestamp; market baseline at snapshot; resolution",
        "primary_validity_risk": "snapshot quality may be strong, but model and market bars still require same-time scoring",
        "minimum_conclusion_change_test": "Compare raw model confidence/returns with proper Brier/log scores against the snapshot market baseline.",
        "pilot_sample": "50 snapshot rows",
        "paper_grade_sample": "all public snapshot rows with source/platform stratification",
        "priority": "medium",
        "current_status": "protocol only; not yet audited here",
    },
    {
        "benchmark_id": "predictionmarketbench",
        "benchmark_class": "execution-realistic market replay benchmark",
        "citation_key": "arora2026predictionmarketbench",
        "audit_unit": "replay decision row",
        "public_access_route": "released benchmark rows if public",
        "row_fields_to_collect": "decision timestamp; available order book; trade constraints; fees; probability forecast; resolution; market baseline",
        "primary_validity_risk": "execution realism can obscure whether probability forecasts are calibrated",
        "minimum_conclusion_change_test": "Report probability score and trading-return score separately after equal-information market joins.",
        "pilot_sample": "50 replay decisions",
        "paper_grade_sample": "all public rows with event-family de-duplication",
        "priority": "medium",
        "current_status": "protocol only; not yet audited here",
    },
    {
        "benchmark_id": "foresight_arena",
        "benchmark_class": "commit-reveal forecasting arena",
        "citation_key": "nechepurenko2026foresight",
        "audit_unit": "committed forecast row",
        "public_access_route": "arena data export if public",
        "row_fields_to_collect": "commit timestamp; reveal timestamp; market consensus timestamp; event-family id; resolution timestamp",
        "primary_validity_risk": "small edges require many resolved rows and same-time market baselines",
        "minimum_conclusion_change_test": "Recompute alpha-over-market only on rows with market consensus frozen no later than the model commit.",
        "pilot_sample": "50 committed forecasts",
        "paper_grade_sample": "all resolved public forecasts",
        "priority": "medium",
        "current_status": "protocol only; not yet audited here",
    },
    {
        "benchmark_id": "evolvecast",
        "benchmark_class": "belief-updating benchmark",
        "citation_key": "yuan2025evolvecast",
        "audit_unit": "forecast update scenario",
        "public_access_route": "released scenarios if public",
        "row_fields_to_collect": "initial information timestamp; update information timestamp; model cutoff; forecast timestamps; resolution label and vintage",
        "primary_validity_risk": "the row is defined by an information transition, not only a final label",
        "minimum_conclusion_change_test": "Re-score update quality after excluding scenarios where update information or outcome labels are source-visible to the evaluated generation.",
        "pilot_sample": "50 update scenarios",
        "paper_grade_sample": "all public scenarios with source/time stratification",
        "priority": "medium",
        "current_status": "protocol only; not yet audited here",
    },
    {
        "benchmark_id": "marketbench",
        "benchmark_class": "agent market-participation benchmark",
        "citation_key": "fradkin2026marketbench",
        "audit_unit": "agent trial or market-participation decision",
        "public_access_route": "paper release and benchmark data if public",
        "row_fields_to_collect": "trial timestamp; capability information shown; cost estimate; outcome; market or task context",
        "primary_validity_risk": "success-probability calibration and cost calibration are different targets from event forecasting",
        "minimum_conclusion_change_test": "Separate capability/cost calibration from event-probability forecasting before comparing to GP-245 claims.",
        "pilot_sample": "50 trials",
        "paper_grade_sample": "all public trials with task-family stratification",
        "priority": "low",
        "current_status": "protocol only; not yet audited here",
    },
    {
        "benchmark_id": "reppo_infrastructure",
        "benchmark_class": "market infrastructure / evaluation substrate",
        "citation_key": "reppo2026",
        "audit_unit": "market or evaluation task definition",
        "public_access_route": "public infrastructure documentation",
        "row_fields_to_collect": "market creation time; question criteria; model/human participant information time; settlement source; market baseline",
        "primary_validity_risk": "infrastructure may enable valid rows without itself supplying a scored benchmark",
        "minimum_conclusion_change_test": "Classify whether the infrastructure records the fields needed for source-currency, label-time, and equal-information audits.",
        "pilot_sample": "documentation-level audit plus 10 example markets if accessible",
        "paper_grade_sample": "representative market/task sample after data-access route is defined",
        "priority": "low",
        "current_status": "protocol only; infrastructure audit, not a performance result",
    },
]


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: list[dict[str, str]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        cells = []
        for col in columns:
            value = str(row.get(col, "")).replace("\n", " ").replace("|", r"\|")
            cells.append(value)
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, sep, *body])


def build_markdown(generated_at: str) -> str:
    priority_counts: dict[str, int] = {}
    for row in SEED_ROWS:
        priority_counts[row["priority"]] = priority_counts.get(row["priority"], 0) + 1
    counts_text = ", ".join(f"{key}={priority_counts[key]}" for key in sorted(priority_counts))
    focus_columns = [
        "benchmark_id",
        "benchmark_class",
        "citation_key",
        "audit_unit",
        "primary_validity_risk",
        "minimum_conclusion_change_test",
        "priority",
    ]
    return "\n".join(
        [
            "# GP-245 Field-Wide Validity Audit Protocol",
            "",
            f"Generated: `{generated_at}`",
            "",
            "Purpose: define the external audit needed before GP-245 can claim a field-wide benchmark-validity failure rate. The current paper shows that row-level validity checks change conclusions inside this program; this protocol names the public benchmark families and row fields needed to test whether the failure mode is broader.",
            "",
            "Companion: `field_wide_validity_local_evidence.py` emits the local Halawi date-distribution summary as a limited warning. It does not replace raw-row audit or before/after score recomputation.",
            "",
            f"Seed benchmark families: `{len(SEED_ROWS)}` ({counts_text}).",
            "",
            "## Required Row Schema",
            "",
            markdown_table(SCHEMA_ROWS, SCHEMA_COLUMNS),
            "",
            "## Benchmark Seed Matrix",
            "",
            markdown_table(SEED_ROWS, focus_columns),
            "",
            "## Decision Rule",
            "",
            "A field-wide claim becomes supportable only after at least three benchmark families have row-level audits with: source-currency classification, label-time status where labels can revise, same-contract comparator timing when market or human comparisons are made, event-family de-duplication, and a before/after conclusion-change test. If the audits show low missingness or no conclusion changes, the field-wide claim should remain out of the paper.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    schema_csv = args.out_dir / "field_wide_validity_audit_schema.csv"
    seed_csv = args.out_dir / "field_wide_validity_audit_seed.csv"
    json_path = args.out_dir / "field_wide_validity_audit_protocol.json"
    md_path = args.out_dir / "field_wide_validity_audit_protocol.md"

    write_csv(schema_csv, SCHEMA_ROWS, SCHEMA_COLUMNS)
    write_csv(seed_csv, SEED_ROWS, SEED_COLUMNS)
    json_path.write_text(
        json.dumps(
            {
                "schema": "gp245-field-wide-validity-audit-protocol-v1",
                "generated_at": generated_at,
                "row_schema": SCHEMA_ROWS,
                "benchmark_seed": SEED_ROWS,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    md_path.write_text(build_markdown(generated_at), encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": "gp245-field-wide-validity-audit-protocol-v1",
                "out_dir": str(args.out_dir),
                "schema_rows": len(SCHEMA_ROWS),
                "benchmark_rows": len(SEED_ROWS),
                "outputs": [str(schema_csv), str(seed_csv), str(json_path), str(md_path)],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
