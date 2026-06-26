#!/usr/bin/env python3
"""Score the local ForecastBench 2026-04-12 processed forecast round.

This audit is deliberately scoped. It uses the public processed forecast files
after they have been downloaded and extracted outside the repository. It reports
how the denominator changes under GP-245 validity checks and compares submitted
forecasts with the prior-day market value on the same market rows where that
baseline exists.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_PROCESSED_DIR = (
    Path("/private/tmp/gp245_forecastbench/forecastbench-processed-forecast-sets/2026-04-12")
)
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"
DEFAULT_QUESTIONS = PROGRAM / "forecaster_skill_calibration_v1/workspace/fb_2026_04_12_questions.json"
PUBLIC_ARCHIVE_URL = (
    "https://www.forecastbench.org/assets/data/processed-forecast-sets/"
    "processed_forecast_sets.tar.gz"
)

MARKET_SOURCES = {"manifold", "metaculus", "polymarket", "infer"}
OFFICIAL_DATA_SOURCES = {"acled", "dbnomics", "fred", "wikipedia", "yfinance"}

SUMMARY_COLUMNS = [
    "forecast_file",
    "organization",
    "model",
    "leaderboard_eligible",
    "resolved_rows_all",
    "resolved_brier_all",
    "resolved_rows_non_imputed",
    "resolved_brier_non_imputed",
    "source_currency_ready_rows",
    "strict_label_time_rows",
    "official_data_excluded_rows",
    "market_rows",
    "market_forecast_brier",
    "market_baseline_brier",
    "market_delta_forecast_minus_baseline",
    "market_delta_perm_p",
    "event_family_capped_market_rows",
    "event_family_capped_market_delta_forecast_minus_baseline",
    "event_family_capped_market_delta_perm_p",
]

ROW_COLUMNS = [
    "forecast_file",
    "organization",
    "model",
    "row_id",
    "source",
    "forecast_due_date",
    "resolution_date",
    "resolved_to",
    "forecast",
    "imputed",
    "market_value_on_due_date_minus_one",
    "event_family_id",
    "source_currency_status",
    "label_time_status",
    "equal_information_status",
    "forecast_brier",
    "market_baseline_brier",
]


@dataclass
class ScoreSummary:
    forecast_file: str
    organization: str
    model: str
    leaderboard_eligible: bool
    resolved_rows_all: int
    resolved_brier_all: float | None
    resolved_rows_non_imputed: int
    resolved_brier_non_imputed: float | None
    source_currency_ready_rows: int
    strict_label_time_rows: int
    official_data_excluded_rows: int
    market_rows: int
    market_forecast_brier: float | None
    market_baseline_brier: float | None
    market_delta_forecast_minus_baseline: float | None
    market_delta_perm_p: float | None
    event_family_capped_market_rows: int
    event_family_capped_market_delta_forecast_minus_baseline: float | None
    event_family_capped_market_delta_perm_p: float | None

    def as_row(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for key in SUMMARY_COLUMNS:
            value = getattr(self, key)
            if isinstance(value, float):
                out[key] = f"{value:.12g}"
            else:
                out[key] = "" if value is None else str(value)
        return out


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_dt(value: Any) -> datetime | None:
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


def is_binary_resolved(row: dict[str, Any]) -> bool:
    return bool(row.get("resolved")) and row.get("resolved_to") in (0, 0.0, 1, 1.0)


def finite_probability(value: Any) -> float | None:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(x) or math.isinf(x):
        return None
    return min(1.0, max(0.0, x))


def brier(probability: float, outcome: float) -> float:
    return (probability - outcome) ** 2


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def source_currency_status(row: dict[str, Any], panel_cutoff: datetime) -> str:
    dt = parse_dt(row.get("resolution_date"))
    if dt is None:
        return "missing_resolution"
    cutoff = panel_cutoff
    if dt.tzinfo is not None and cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=dt.tzinfo)
    return "post_cutoff" if dt > cutoff else "pre_cutoff_or_source_visible"


def label_time_status(source: str) -> str:
    if source in MARKET_SOURCES:
        return "market_resolution_not_vintage_sensitive"
    if source in OFFICIAL_DATA_SOURCES:
        return "needs_official_vintage"
    return "unknown_source"


def equal_information_status(row: dict[str, Any]) -> str:
    if row.get("source") in MARKET_SOURCES and finite_probability(row.get("market_value_on_due_date_minus_one")) is not None:
        return "prior_day_market_baseline_present"
    return "no_prior_day_market_baseline"


def paired_permutation_p(deltas: list[float], *, iterations: int = 20000, seed: int = 245) -> float | None:
    if not deltas:
        return None
    observed = abs(mean(deltas) or 0.0)
    rng = random.Random(seed)
    ge = 0
    for _ in range(iterations):
        trial = sum(delta if rng.random() < 0.5 else -delta for delta in deltas) / len(deltas)
        if abs(trial) >= observed:
            ge += 1
    return (ge + 1) / (iterations + 1)


def row_id(row: dict[str, Any]) -> str:
    direction = json.dumps(row.get("direction"), sort_keys=True)
    return "|".join(
        [
            str(row.get("source")),
            str(row.get("id")),
            str(row.get("resolution_date")),
            direction,
        ]
    )


def question_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get("source") or ""), str(row.get("id") or ""))


def event_family_from_question(question: dict[str, Any] | None, row: dict[str, Any]) -> str:
    source = str(row.get("source") or "unknown")
    if question:
        url = str(question.get("url") or "")
        if url and url != "N/A":
            return f"{source}:{url}"
    return f"{source}:{row.get('id')}"


def first_event_family_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for item in rows:
        key = str(item["event_family_id"])
        current = selected.get(key)
        if current is None or str(item["row_id"]) < str(current["row_id"]):
            selected[key] = item
    return [selected[key] for key in sorted(selected)]


def score_file(
    path: Path,
    panel_cutoff: datetime,
    question_by_key: dict[tuple[str, str], dict[str, Any]],
) -> tuple[ScoreSummary, list[dict[str, str]]]:
    payload = read_json(path)
    rows = [row for row in payload.get("forecasts", []) if isinstance(row, dict)]
    organization = str(payload.get("organization") or "")
    model = str(payload.get("model") or "")
    leaderboard_eligible = bool(payload.get("leaderboard_eligible"))

    resolved_rows = []
    output_rows: list[dict[str, str]] = []
    for row in rows:
        if not is_binary_resolved(row):
            continue
        forecast = finite_probability(row.get("forecast"))
        if forecast is None:
            continue
        outcome = float(row["resolved_to"])
        source = str(row.get("source") or "")
        rid = row_id(row)
        event_family = event_family_from_question(question_by_key.get(question_key(row)), row)
        sc_status = source_currency_status(row, panel_cutoff)
        lt_status = label_time_status(source)
        ei_status = equal_information_status(row)
        market_probability = finite_probability(row.get("market_value_on_due_date_minus_one"))
        forecast_score = brier(forecast, outcome)
        market_score = brier(market_probability, outcome) if market_probability is not None else None
        resolved_rows.append(
            {
                "row": row,
                "source": source,
                "row_id": rid,
                "event_family_id": event_family,
                "forecast": forecast,
                "outcome": outcome,
                "imputed": bool(row.get("imputed")),
                "source_currency_status": sc_status,
                "label_time_status": lt_status,
                "equal_information_status": ei_status,
                "forecast_brier": forecast_score,
                "market_baseline_brier": market_score,
            }
        )
        output_rows.append(
            {
                "forecast_file": path.name,
                "organization": organization,
                "model": model,
                "row_id": rid,
                "source": source,
                "forecast_due_date": str(row.get("forecast_due_date") or ""),
                "resolution_date": str(row.get("resolution_date") or ""),
                "resolved_to": str(row.get("resolved_to")),
                "forecast": str(forecast),
                "imputed": str(bool(row.get("imputed"))),
                "market_value_on_due_date_minus_one": ""
                if market_probability is None
                else str(market_probability),
                "event_family_id": event_family,
                "source_currency_status": sc_status,
                "label_time_status": lt_status,
                "equal_information_status": ei_status,
                "forecast_brier": f"{forecast_score:.12g}",
                "market_baseline_brier": "" if market_score is None else f"{market_score:.12g}",
            }
        )

    all_scores = [item["forecast_brier"] for item in resolved_rows]
    non_imputed = [item for item in resolved_rows if not item["imputed"]]
    non_imputed_scores = [item["forecast_brier"] for item in non_imputed]
    source_ready = [item for item in non_imputed if item["source_currency_status"] == "post_cutoff"]
    strict_label_time = [
        item
        for item in source_ready
        if item["label_time_status"] == "market_resolution_not_vintage_sensitive"
    ]
    official_excluded = [
        item
        for item in source_ready
        if item["label_time_status"] == "needs_official_vintage"
    ]
    market_rows = [
        item
        for item in strict_label_time
        if item["equal_information_status"] == "prior_day_market_baseline_present"
        and item["market_baseline_brier"] is not None
    ]
    market_forecast_scores = [item["forecast_brier"] for item in market_rows]
    market_baseline_scores = [float(item["market_baseline_brier"]) for item in market_rows]
    paired_deltas = [
        item["forecast_brier"] - float(item["market_baseline_brier"])
        for item in market_rows
    ]
    capped_market_rows = first_event_family_rows(market_rows)
    capped_paired_deltas = [
        item["forecast_brier"] - float(item["market_baseline_brier"])
        for item in capped_market_rows
    ]

    summary = ScoreSummary(
        forecast_file=path.name,
        organization=organization,
        model=model,
        leaderboard_eligible=leaderboard_eligible,
        resolved_rows_all=len(resolved_rows),
        resolved_brier_all=mean(all_scores),
        resolved_rows_non_imputed=len(non_imputed),
        resolved_brier_non_imputed=mean(non_imputed_scores),
        source_currency_ready_rows=len(source_ready),
        strict_label_time_rows=len(strict_label_time),
        official_data_excluded_rows=len(official_excluded),
        market_rows=len(market_rows),
        market_forecast_brier=mean(market_forecast_scores),
        market_baseline_brier=mean(market_baseline_scores),
        market_delta_forecast_minus_baseline=mean(paired_deltas),
        market_delta_perm_p=paired_permutation_p(paired_deltas) if len(paired_deltas) >= 2 else None,
        event_family_capped_market_rows=len(capped_market_rows),
        event_family_capped_market_delta_forecast_minus_baseline=mean(capped_paired_deltas),
        event_family_capped_market_delta_perm_p=paired_permutation_p(capped_paired_deltas)
        if len(capped_paired_deltas) >= 2
        else None,
    )
    return summary, output_rows


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: list[dict[str, str]], columns: list[str], max_rows: int = 20) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows[:max_rows]:
        cells = [str(row.get(col, "")).replace("\n", " ").replace("|", r"\|") for col in columns]
        body.append("| " + " | ".join(cells) + " |")
    if len(rows) > max_rows:
        body.append("| " + " | ".join(["..."] * len(columns)) + " |")
    return "\n".join([header, sep, *body])


def build_markdown(report: dict[str, Any]) -> str:
    top_all = report["top_non_imputed_all_rows"]
    top_market = report["top_market_rows"]
    columns_all = [
        "forecast_file",
        "resolved_rows_non_imputed",
        "resolved_brier_non_imputed",
        "strict_label_time_rows",
    ]
    columns_market = [
        "forecast_file",
        "market_rows",
        "market_forecast_brier",
        "market_baseline_brier",
        "market_delta_forecast_minus_baseline",
        "market_delta_perm_p",
        "event_family_capped_market_rows",
        "event_family_capped_market_delta_forecast_minus_baseline",
        "event_family_capped_market_delta_perm_p",
    ]
    return "\n".join(
        [
            "# GP-245 ForecastBench Score Audit",
            "",
            f"Generated: `{report['generated_at']}`",
            "",
            f"- Processed directory: `{report['processed_dir']}`",
            f"- Public processed-forecast archive: `{report['public_archive_url']}`",
            f"- Forecast files scored: `{report['forecast_files_scored']}`",
            f"- Unique scored row keys: `{report['unique_scored_row_keys']}`",
            f"- Resolved binary rows per full file: `{report['resolved_rows_per_full_file']}`",
            f"- Resolved same-information market rows per full file: `{report['market_rows_per_full_file']}`",
            f"- Event-family-capped market rows per full file: `{report['event_family_capped_market_rows_per_full_file']}`",
            f"- Files beating the prior-day market baseline on the market slice: `{report['files_beating_market_baseline']}`",
            f"- Files beating the prior-day market baseline after event-family capping: `{report['files_beating_market_baseline_event_family_capped']}`",
            f"- Median market-slice delta, forecast minus prior-day market: `{report['median_market_delta_forecast_minus_baseline']}`",
            f"- Median event-family-capped market-slice delta: `{report['median_event_family_capped_market_delta_forecast_minus_baseline']}`",
            "",
            "Interpretation: " + report["interpretation"],
            "",
            "Limit: " + report["limit"],
            "",
            "## Top Files By All Resolved Non-Imputed Rows",
            "",
            markdown_table(top_all, columns_all, max_rows=12),
            "",
            "## Top Files By Same-Information Market Rows",
            "",
            markdown_table(top_market, columns_market, max_rows=12),
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--panel-cutoff", default="2025-10-01")
    parser.add_argument("--report-stem", default="field_wide_forecastbench_score_audit")
    args = parser.parse_args()

    if not args.processed_dir.exists():
        raise SystemExit(
            f"Processed ForecastBench directory not found: {args.processed_dir}. "
            f"Download {PUBLIC_ARCHIVE_URL} and extract the 2026-04-12 directory."
        )
    question_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    if args.questions.exists():
        questions_obj = read_json(args.questions)
        question_by_key = {
            question_key(row): row
            for row in questions_obj.get("questions", [])
            if isinstance(row, dict)
        }

    panel_cutoff = parse_dt(args.panel_cutoff)
    if panel_cutoff is None:
        raise SystemExit(f"Invalid panel cutoff: {args.panel_cutoff}")

    summaries: list[ScoreSummary] = []
    row_outputs: list[dict[str, str]] = []
    for path in sorted(args.processed_dir.glob("*.json")):
        summary, rows = score_file(path, panel_cutoff, question_by_key)
        if summary.resolved_rows_all == 0:
            continue
        summaries.append(summary)
        row_outputs.extend(rows)

    summary_rows = [item.as_row() for item in summaries]
    all_ranked = sorted(
        [row for row in summary_rows if row["resolved_rows_non_imputed"] and row["resolved_brier_non_imputed"]],
        key=lambda row: float(row["resolved_brier_non_imputed"]),
    )
    market_ranked = sorted(
        [row for row in summary_rows if row["market_rows"] and row["market_forecast_brier"]],
        key=lambda row: float(row["market_forecast_brier"]),
    )
    market_deltas = [
        float(row["market_delta_forecast_minus_baseline"])
        for row in summary_rows
        if row["market_delta_forecast_minus_baseline"]
    ]
    capped_market_deltas = [
        float(row["event_family_capped_market_delta_forecast_minus_baseline"])
        for row in summary_rows
        if row["event_family_capped_market_delta_forecast_minus_baseline"]
    ]
    median_delta = None
    if market_deltas:
        sorted_deltas = sorted(market_deltas)
        mid = len(sorted_deltas) // 2
        if len(sorted_deltas) % 2:
            median_delta = sorted_deltas[mid]
        else:
            median_delta = (sorted_deltas[mid - 1] + sorted_deltas[mid]) / 2
    capped_median_delta = None
    if capped_market_deltas:
        sorted_capped_deltas = sorted(capped_market_deltas)
        mid = len(sorted_capped_deltas) // 2
        if len(sorted_capped_deltas) % 2:
            capped_median_delta = sorted_capped_deltas[mid]
        else:
            capped_median_delta = (sorted_capped_deltas[mid - 1] + sorted_capped_deltas[mid]) / 2

    unique_row_keys = {row["row_id"] for row in row_outputs}
    unique_event_family_keys = {row["event_family_id"] for row in row_outputs if row["event_family_id"]}
    full_file_rows = [item.resolved_rows_all for item in summaries if item.resolved_rows_all]
    market_file_rows = [item.market_rows for item in summaries if item.market_rows]
    capped_market_file_rows = [
        item.event_family_capped_market_rows for item in summaries if item.event_family_capped_market_rows
    ]
    report = {
        "schema": "gp245-field-wide-forecastbench-score-audit-v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "processed_dir": str(args.processed_dir),
        "public_archive_url": PUBLIC_ARCHIVE_URL,
        "questions_path": str(args.questions),
        "panel_cutoff": args.panel_cutoff,
        "forecast_files_scored": len(summaries),
        "unique_scored_row_keys": len(unique_row_keys),
        "unique_event_family_keys": len(unique_event_family_keys),
        "resolved_rows_per_full_file": sorted(set(full_file_rows)),
        "market_rows_per_full_file": sorted(set(market_file_rows)),
        "event_family_capped_market_rows_per_full_file": sorted(set(capped_market_file_rows)),
        "files_beating_market_baseline": sum(
            1
            for item in summaries
            if item.market_delta_forecast_minus_baseline is not None
            and item.market_delta_forecast_minus_baseline < 0
        ),
        "files_beating_market_baseline_event_family_capped": sum(
            1
            for item in summaries
            if item.event_family_capped_market_delta_forecast_minus_baseline is not None
            and item.event_family_capped_market_delta_forecast_minus_baseline < 0
        ),
        "files_with_market_slice": sum(1 for item in summaries if item.market_rows > 0),
        "median_market_delta_forecast_minus_baseline": None
        if median_delta is None
        else f"{median_delta:.12g}",
        "median_event_family_capped_market_delta_forecast_minus_baseline": None
        if capped_median_delta is None
        else f"{capped_median_delta:.12g}",
        "interpretation": (
            "The public processed forecast archive supplies row-level forecasts for the local "
            "ForecastBench round. Source-currency filtering does not remove resolved rows under "
            "the 2025-10-01 panel cutoff, but the strict GP-245 label-time rule removes official-data "
            "rows that lack an admissible data-vintage field. The remaining same-information market "
            "slice has a prior-day market baseline and can be scored directly. The event-family-capped "
            "view repeats that market comparison after allowing at most one scored market row per "
            "question URL or source/id family."
        ),
        "limit": (
            "This is a ForecastBench row-level score audit, not a broad field-wide prevalence result. "
            "It does not audit Prophet Arena, AIA Forecaster, PolyBench, or other routes, and it treats "
            "official-data rows as requiring vintage documentation rather than as scored current-label evidence."
        ),
        "summaries": [item.__dict__ for item in summaries],
        "top_non_imputed_all_rows": all_ranked[:20],
        "top_market_rows": market_ranked[:20],
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / f"{args.report_stem}.json"
    csv_path = args.out_dir / f"{args.report_stem}.csv"
    rows_csv_path = args.out_dir / f"{args.report_stem}_rows.csv"
    md_path = args.out_dir / f"{args.report_stem}.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, summary_rows, SUMMARY_COLUMNS)
    write_csv(rows_csv_path, row_outputs, ROW_COLUMNS)
    md_path.write_text(build_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": report["schema"],
                "forecast_files_scored": report["forecast_files_scored"],
                "unique_scored_row_keys": report["unique_scored_row_keys"],
                "unique_event_family_keys": report["unique_event_family_keys"],
                "resolved_rows_per_full_file": report["resolved_rows_per_full_file"],
                "market_rows_per_full_file": report["market_rows_per_full_file"],
                "event_family_capped_market_rows_per_full_file": report[
                    "event_family_capped_market_rows_per_full_file"
                ],
                "files_beating_market_baseline": report["files_beating_market_baseline"],
                "files_beating_market_baseline_event_family_capped": report[
                    "files_beating_market_baseline_event_family_capped"
                ],
                "median_market_delta_forecast_minus_baseline": report[
                    "median_market_delta_forecast_minus_baseline"
                ],
                "median_event_family_capped_market_delta_forecast_minus_baseline": report[
                    "median_event_family_capped_market_delta_forecast_minus_baseline"
                ],
                "outputs": [str(json_path), str(csv_path), str(rows_csv_path), str(md_path)],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
