#!/usr/bin/env python3
"""Run a local ForecastBench row-schema pilot for GP-245.

The pilot uses the locally cached ForecastBench question and resolution bundle.
It does not download data, call models, or recompute a published benchmark
score. It classifies which row-level validity fields are already present and
which fields remain missing before a conclusion-change audit is possible.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "forecaster_skill_calibration_v1/workspace"
DEFAULT_QUESTIONS = WORKSPACE / "fb_2026_04_12_questions.json"
DEFAULT_RESOLUTIONS = WORKSPACE / "fb_2026_04_12_resolutions.json"
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"

CSV_COLUMNS = [
    "row_id",
    "source",
    "question_or_market_id",
    "forecast_timestamp",
    "model_cutoff_or_retrieval_window",
    "resolution_timestamp",
    "outcome_label",
    "label_vintage",
    "same_contract_baseline_type",
    "baseline_timestamp",
    "event_family_id",
    "decision_rule_status",
    "source_currency_status",
    "label_time_status",
    "equal_information_status",
    "score_reanalysis_status",
    "missing_fields",
]

MARKET_SOURCES = {"manifold", "metaculus", "polymarket", "infer", "gjopen", "cset"}
OFFICIAL_DATA_SOURCES = {"acled", "dbnomics", "fred", "wikipedia", "yfinance", "yahoo_finance"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_date(value: Any) -> datetime | None:
    if value in (None, "", "N/A"):
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.fromisoformat(text[:10])
        except ValueError:
            return None


def cutoff_status(resolution_timestamp: str | None, panel_cutoff: str) -> str:
    resolution_dt = parse_date(resolution_timestamp)
    cutoff_dt = parse_date(panel_cutoff)
    if resolution_dt is None or cutoff_dt is None:
        return "missing_resolution_or_cutoff"
    if resolution_dt.tzinfo is not None and cutoff_dt.tzinfo is None:
        cutoff_dt = cutoff_dt.replace(tzinfo=resolution_dt.tzinfo)
    return "post_cutoff" if resolution_dt > cutoff_dt else "pre_cutoff_or_source_visible"


def baseline_type(question: dict[str, Any]) -> str:
    source = str(question.get("source") or "")
    has_market_freeze = question.get("freeze_datetime") not in (None, "", "N/A") and question.get(
        "freeze_datetime_value"
    ) not in (None, "", "N/A")
    if has_market_freeze and source in MARKET_SOURCES:
        return "market"
    return "none"


def event_family_id(question: dict[str, Any]) -> str:
    source = str(question.get("source") or "unknown")
    url = str(question.get("url") or "")
    if url and url != "N/A":
        return f"{source}:{url}"
    return f"{source}:{question.get('id')}"


def row_from_question(
    question: dict[str, Any],
    resolution: dict[str, Any] | None,
    forecast_due_date: str,
    panel_cutoff: str,
) -> dict[str, str]:
    source = str(question.get("source") or "unknown")
    qid = str(question.get("id") or "")
    resolution_timestamp = str((resolution or {}).get("resolution_date") or question.get("resolution_dates") or "")
    outcome = (resolution or {}).get("resolved_to")
    baseline = baseline_type(question)
    baseline_timestamp = str(question.get("freeze_datetime") or "") if baseline == "market" else ""
    label_vintage = "not_documented"
    if source in MARKET_SOURCES and resolution_timestamp:
        label_vintage = "not_applicable_market_resolution"
    elif source in OFFICIAL_DATA_SOURCES and resolution_timestamp:
        label_vintage = "resolution_date_only"

    missing: list[str] = []
    if not qid:
        missing.append("question_or_market_id")
    if not forecast_due_date:
        missing.append("forecast_timestamp")
    if not panel_cutoff:
        missing.append("model_cutoff_or_retrieval_window")
    if not resolution_timestamp or resolution_timestamp == "N/A":
        missing.append("resolution_timestamp")
    if outcome is None:
        missing.append("outcome_label")
    if source in OFFICIAL_DATA_SOURCES and label_vintage == "resolution_date_only":
        missing.append("label_vintage")
    if baseline == "market" and not baseline_timestamp:
        missing.append("baseline_timestamp")
    if "score_before_validity_filter" not in question:
        missing.append("score_before_validity_filter")
    if "score_after_validity_filter" not in question:
        missing.append("score_after_validity_filter")

    source_status = cutoff_status(resolution_timestamp, panel_cutoff)
    label_status = (
        "market_resolution_not_vintage_sensitive"
        if source in MARKET_SOURCES and outcome is not None
        else "needs_official_vintage"
        if source in OFFICIAL_DATA_SOURCES and outcome is not None
        else "missing_outcome_or_resolution"
    )
    equal_info_status = (
        "market_baseline_timestamped"
        if baseline == "market" and baseline_timestamp
        else "no_same_contract_baseline_in_local_bundle"
    )
    score_status = "missing_before_after_scores"

    return {
        "row_id": f"forecastbench_20260412_{source}_{qid}",
        "source": source,
        "question_or_market_id": qid,
        "forecast_timestamp": forecast_due_date,
        "model_cutoff_or_retrieval_window": panel_cutoff,
        "resolution_timestamp": resolution_timestamp,
        "outcome_label": "" if outcome is None else str(outcome),
        "label_vintage": label_vintage,
        "same_contract_baseline_type": baseline,
        "baseline_timestamp": baseline_timestamp,
        "event_family_id": event_family_id(question),
        "decision_rule_status": "external_benchmark_row",
        "source_currency_status": source_status,
        "label_time_status": label_status,
        "equal_information_status": equal_info_status,
        "score_reanalysis_status": score_status,
        "missing_fields": ",".join(missing),
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    questions_obj = read_json(args.questions)
    resolutions_obj = read_json(args.resolutions)
    questions = [row for row in questions_obj.get("questions", []) if isinstance(row, dict)]
    forecast_due_date = str(resolutions_obj.get("forecast_due_date") or questions_obj.get("forecast_due_date") or "")
    resolution_by_key = {
        (str(row.get("source")), str(row.get("id"))): row
        for row in resolutions_obj.get("resolutions", [])
        if isinstance(row, dict)
    }
    rows = [
        row_from_question(
            question,
            resolution_by_key.get((str(question.get("source")), str(question.get("id")))),
            forecast_due_date,
            args.panel_cutoff,
        )
        for question in questions
    ]

    source_counts = Counter(row["source"] for row in rows)
    source_currency_counts = Counter(row["source_currency_status"] for row in rows)
    label_time_counts = Counter(row["label_time_status"] for row in rows)
    equal_info_counts = Counter(row["equal_information_status"] for row in rows)
    missing_field_counts: Counter[str] = Counter()
    for row in rows:
        for field in row["missing_fields"].split(","):
            if field:
                missing_field_counts[field] += 1

    complete_validity_rows = [
        row
        for row in rows
        if row["source_currency_status"] in {"post_cutoff", "pre_cutoff_or_source_visible"}
        and row["outcome_label"]
        and row["forecast_timestamp"]
        and row["model_cutoff_or_retrieval_window"]
    ]
    same_contract_market_rows = [
        row for row in rows if row["equal_information_status"] == "market_baseline_timestamped"
    ]
    conclusion_change_ready_rows = [
        row
        for row in rows
        if "score_before_validity_filter" not in row["missing_fields"]
        and "score_after_validity_filter" not in row["missing_fields"]
    ]

    verdict = (
        "row_schema_pilot_ready_score_audit_not_ready"
        if complete_validity_rows
        else "local_bundle_not_row_schema_ready"
    )
    return {
        "schema": "gp245-field-wide-forecastbench-row-schema-pilot-v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "questions_path": str(args.questions.relative_to(REPO)),
        "resolutions_path": str(args.resolutions.relative_to(REPO)),
        "panel_cutoff": args.panel_cutoff,
        "forecast_due_date": forecast_due_date,
        "row_count": len(rows),
        "complete_validity_rows": len(complete_validity_rows),
        "same_contract_market_rows": len(same_contract_market_rows),
        "conclusion_change_ready_rows": len(conclusion_change_ready_rows),
        "source_counts": dict(sorted(source_counts.items())),
        "source_currency_counts": dict(sorted(source_currency_counts.items())),
        "label_time_counts": dict(sorted(label_time_counts.items())),
        "equal_information_counts": dict(sorted(equal_info_counts.items())),
        "missing_field_counts": dict(sorted(missing_field_counts.items())),
        "verdict": verdict,
        "interpretation": (
            "The cached ForecastBench bundle is sufficient for a row-level validity coverage pilot. "
            "It is not sufficient for a conclusion-change audit because before/after benchmark scores "
            "and model/human forecast rows are not joined here."
        ),
        "next_action": (
            "Join released ForecastBench model or human forecast rows to this validity table, "
            "then recompute the headline comparison before and after source-currency, label-time, "
            "and event-family filters."
        ),
        "rows": rows,
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: list[dict[str, str]], columns: list[str], max_rows: int = 20) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows[:max_rows]:
        values = []
        for col in columns:
            values.append(str(row.get(col, "")).replace("\n", " ").replace("|", r"\|"))
        body.append("| " + " | ".join(values) + " |")
    if len(rows) > max_rows:
        body.append("| " + " | ".join(["..."] * len(columns)) + " |")
    return "\n".join([header, sep, *body])


def build_markdown(report: dict[str, Any]) -> str:
    sample_columns = [
        "row_id",
        "source",
        "source_currency_status",
        "label_time_status",
        "equal_information_status",
        "missing_fields",
    ]
    lines = [
        "# GP-245 ForecastBench Row-Schema Pilot",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"- Questions path: `{report['questions_path']}`",
        f"- Resolutions path: `{report['resolutions_path']}`",
        f"- Panel cutoff: `{report['panel_cutoff']}`",
        f"- Forecast due date: `{report['forecast_due_date']}`",
        f"- Row count: `{report['row_count']}`",
        f"- Complete validity rows: `{report['complete_validity_rows']}`",
        f"- Same-contract market rows: `{report['same_contract_market_rows']}`",
        f"- Conclusion-change ready rows: `{report['conclusion_change_ready_rows']}`",
        f"- Verdict: `{report['verdict']}`",
        "",
        "Interpretation: " + report["interpretation"],
        "",
        "Next action: " + report["next_action"],
        "",
        "## Counts",
        "",
        f"- Source counts: `{report['source_counts']}`",
        f"- Source-currency counts: `{report['source_currency_counts']}`",
        f"- Label-time counts: `{report['label_time_counts']}`",
        f"- Equal-information counts: `{report['equal_information_counts']}`",
        f"- Missing-field counts: `{report['missing_field_counts']}`",
        "",
        "## Sample Rows",
        "",
        markdown_table(report["rows"], sample_columns, max_rows=20),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--resolutions", type=Path, default=DEFAULT_RESOLUTIONS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--panel-cutoff", default="2025-10-01")
    args = parser.parse_args()

    report = build(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    json_path = args.out_dir / "field_wide_forecastbench_row_schema_pilot.json"
    csv_path = args.out_dir / "field_wide_forecastbench_row_schema_pilot.csv"
    md_path = args.out_dir / "field_wide_forecastbench_row_schema_pilot.md"
    jsonl_path = args.out_dir / "field_wide_forecastbench_row_schema_pilot_rows.jsonl"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, report["rows"])
    md_path.write_text(build_markdown(report), encoding="utf-8")
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in report["rows"]:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    print(
        json.dumps(
            {
                "schema": report["schema"],
                "row_count": report["row_count"],
                "complete_validity_rows": report["complete_validity_rows"],
                "same_contract_market_rows": report["same_contract_market_rows"],
                "conclusion_change_ready_rows": report["conclusion_change_ready_rows"],
                "verdict": report["verdict"],
                "outputs": [str(json_path), str(csv_path), str(md_path), str(jsonl_path)],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
