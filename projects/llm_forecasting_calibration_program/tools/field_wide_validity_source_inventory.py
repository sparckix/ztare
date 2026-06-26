#!/usr/bin/env python3
"""Emit the GP-245 external-source inventory for field-wide validity auditing.

This is an offline support file. It does not download benchmark rows or
recompute any external score. Its job is narrower: record, for each candidate
external route, whether the primary source appears to expose row-level data,
which validity fields are likely obtainable, and what remains before GP-245 can
make a field-wide prevalence claim.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"

CSV_COLUMNS = [
    "benchmark_id",
    "citation_key",
    "primary_source_url",
    "source_inventory_status",
    "row_level_access_status",
    "row_level_access_notes",
    "likely_obtainable_fields",
    "main_missing_fields",
    "conclusion_change_feasibility",
    "next_action",
]


ROWS = [
    {
        "benchmark_id": "forecastbench",
        "citation_key": "karger2024forecastbench",
        "primary_source_url": "https://www.forecastbench.org/datasets/",
        "source_inventory_status": "primary source exposes datasets repository, leaderboards, resolution values, question sets, processed forecast files, and 2024 human survey data; local row-schema and score audits completed on the cached 2026-04-12 round",
        "row_level_access_status": "high",
        "row_level_access_notes": "released source appears to include row-level question, resolution, forecast, and survey material",
        "likely_obtainable_fields": "question id; question set date; resolution value; leaderboard scores; processed model forecast rows; same-information market baseline values; human forecast rows for the released survey round",
        "main_missing_fields": "official-data rows still need data-vintage documentation; per-model knowledge cutoff and retrieval window must be reconstructed from each submission; event-family de-duplication and larger same-information human comparisons must be added",
        "conclusion_change_feasibility": "high for market-row equal-information checks and event-family filters; medium for official-data and human/model comparisons unless baseline timestamps and data vintages are aligned",
        "next_action": "Use the completed processed-forecast score audit and 2024 human-comparator audit as the ForecastBench baseline; add data-vintage checks and larger same-information human comparisons, then repeat the row-schema treatment on PolyBench.",
    },
    {
        "benchmark_id": "prophet_arena",
        "citation_key": "yang2025prophetarena",
        "primary_source_url": "https://arxiv.org/abs/2510.17638",
        "source_inventory_status": "paper reports continuously collected live tasks and pipeline-stage decomposition; public ai-prophet dataset repository exposes sample task releases and a local pilot fetched 68 task rows across four v1.0.0 samples; the same pilot checked five public AI Prophet repositories for submitted forecast traces",
        "row_level_access_status": "medium",
        "row_level_access_notes": "public task rows are accessible with task id, source/event ticker, predict_by deadline, context, metadata close time, and resolved labels for the resolved sample; public repos expose forecast/evaluation code but no committed Prophet Arena submission, leaderboard, or per-model trace archive",
        "likely_obtainable_fields": "task id; source/event ticker; prediction deadline; context; outcome options; resolved label and resolution timestamp for resolved sample rows",
        "main_missing_fields": "public submitted forecast probabilities, leaderboard or per-model trace archive, model input-bundle timestamps, same-time market or human baseline probabilities, score before/after validity filter",
        "conclusion_change_feasibility": "medium-low until forecast traces, leaderboard exports, or score files are released; high for task-row schema/access only",
        "next_action": "Use the Prophet Arena row-schema and trace-surface pilot as source-access evidence; acquire submitted forecast traces, leaderboard exports, or score files before attempting a conclusion-change test.",
    },
    {
        "benchmark_id": "halawi_2024_binary_resolved",
        "citation_key": "halawi2024approaching",
        "primary_source_url": "https://arxiv.org/abs/2402.18563",
        "source_inventory_status": "paper reports a dataset drawn from competitive forecasting platforms and a test set published after evaluated-model cutoffs",
        "row_level_access_status": "medium",
        "row_level_access_notes": "local project has only a date-distribution summary; raw rows must be acquired externally",
        "likely_obtainable_fields": "question id; platform; resolution date; human aggregate; model forecast if dataset release is acquired",
        "main_missing_fields": "raw rows, row labels, forecast timestamps, before/after score recomputation",
        "conclusion_change_feasibility": "medium once raw rows are available; currently limited to corpus-validity drift warning",
        "next_action": "Acquire the released rows and recompute eligibility under current model cutoffs.",
    },
    {
        "benchmark_id": "aia_forecaster",
        "citation_key": "alur2025aiaforecaster",
        "primary_source_url": "https://arxiv.org/abs/2511.07678",
        "source_inventory_status": "paper reports ForecastBench results, a liquid-market benchmark, market-consensus comparisons, and additive ensemble claims",
        "row_level_access_status": "unknown",
        "row_level_access_notes": "needs released question logs or market benchmark rows",
        "likely_obtainable_fields": "question id; forecast probability; market consensus; resolution; search/retrieval window if released",
        "main_missing_fields": "same-contract market-consensus timestamp and row-level model input bundle",
        "conclusion_change_feasibility": "high if market-consensus timestamps are released; low if only aggregate scores are available",
        "next_action": "Locate released question logs or market benchmark rows and check same-time market joins first.",
    },
    {
        "benchmark_id": "prediction_arena",
        "citation_key": "zhang2026predictionarena",
        "primary_source_url": "https://arxiv.org/abs/2604.07355",
        "source_inventory_status": "paper reports live Kalshi/Polymarket trading with real capital, 15-45 minute decisions, and platform-specific returns",
        "row_level_access_status": "unknown",
        "row_level_access_notes": "needs released decision logs",
        "likely_obtainable_fields": "decision timestamp; platform; position/trade; market state; resolution if logs are released",
        "main_missing_fields": "proper probability score separate from trading return; fees, liquidity, and position sizing must be isolated",
        "conclusion_change_feasibility": "medium if decision logs are released; low from returns alone",
        "next_action": "Look for the decision log release and split probability accuracy from execution outcomes.",
    },
    {
        "benchmark_id": "polybench",
        "citation_key": "cheng2026polybench",
        "primary_source_url": "https://arxiv.org/abs/2604.14199",
        "source_inventory_status": "paper reports timestamp-locked Polymarket snapshots, CLOB state, real-time news stream, 38,666 binary markets, and public code/data; repository/schema clone completed, but linked OneDrive dataset resolves to an HTML page rather than a direct database file in the noninteractive check",
        "row_level_access_status": "medium",
        "row_level_access_notes": "repository and database schema are accessible; GitHub has no release and no committed database/CSV/parquet row file; released SQLite database or equivalent row export was not available through the noninteractive dataset path in this run",
        "likely_obtainable_fields": "snapshot timestamp; market id; order book; news bundle time; model forecast; resolution; execution outcome",
        "main_missing_fields": "released SQLite database or equivalent row export; proper-score baseline against the same snapshot market probability may need reconstruction",
        "conclusion_change_feasibility": "high once the released database is available; currently source-schema ready but not scoreable here",
        "next_action": "Obtain the released database through a browser-authenticated or alternate public path, then run a 50-row row-schema pilot.",
    },
    {
        "benchmark_id": "predictionmarketbench",
        "citation_key": "arora2026predictionmarketbench",
        "primary_source_url": "https://arxiv.org/abs/2602.00133",
        "source_inventory_status": "paper and repository report deterministic replay from raw exchange streams, order books, trades, lifecycle, settlement, and public code; local row-schema pilot completed on the four included episodes",
        "row_level_access_status": "high",
        "row_level_access_notes": "repository includes four episode directories with metadata, orderbook parquet, trades parquet, and settlement JSON; stored model forecast rows are not included",
        "likely_obtainable_fields": "episode id; decision timestamp; order book; fees; agent action; settlement; market baseline",
        "main_missing_fields": "stored model or agent decision traces with probabilities; event-family de-duplication across sibling tickers",
        "conclusion_change_feasibility": "high for replay-row validity and market-baseline reconstruction; model-vs-market conclusion change requires submitted agent traces or a new benchmark run",
        "next_action": "Run or obtain submitted agent traces with explicit probabilities, then compare proper scores against the reconstructed same-time market baseline.",
    },
    {
        "benchmark_id": "foresight_arena",
        "citation_key": "nechepurenko2026foresight",
        "primary_source_url": "https://arxiv.org/abs/2605.00420",
        "source_inventory_status": "paper reports commit-reveal forecasts, Brier and alpha-over-market scores, open-source infrastructure, and live results pending",
        "row_level_access_status": "medium",
        "row_level_access_notes": "infrastructure appears inspectable; resolved live rows depend on deployment data release",
        "likely_obtainable_fields": "commit time; reveal time; market consensus; event id; resolution once live rows exist",
        "main_missing_fields": "resolved live forecasts and frozen market bars for completed rounds",
        "conclusion_change_feasibility": "high for future live data; currently protocol-level only",
        "next_action": "Use as an external design comparator now; audit live rows after public resolutions exist.",
    },
    {
        "benchmark_id": "evolvecast",
        "citation_key": "yuan2025evolvecast",
        "primary_source_url": "https://arxiv.org/abs/2509.23936",
        "source_inventory_status": "paper reports update scenarios where post-cutoff information is supplied and human forecasters are the comparator",
        "row_level_access_status": "unknown",
        "row_level_access_notes": "needs scenario release check",
        "likely_obtainable_fields": "initial forecast; update information time; revised forecast; human reference; final label",
        "main_missing_fields": "scenario release status, label vintage, and whether update information is source-visible to current models",
        "conclusion_change_feasibility": "medium if scenarios are released; low from aggregate update metrics alone",
        "next_action": "Locate scenario data and classify each update by information timestamp and current-model visibility.",
    },
    {
        "benchmark_id": "strategic_foresight_tournament",
        "citation_key": "csaszar2026strategicforesight",
        "primary_source_url": "https://arxiv.org/abs/2602.01684",
        "source_inventory_status": "paper reports a fully prospective Kickstarter venture tournament with 870 pairwise model comparisons and 346 experienced managers",
        "row_level_access_status": "unknown",
        "row_level_access_notes": "needs released pairwise rows and outcome labels",
        "likely_obtainable_fields": "venture pair id; evaluation time; model or human identity; outcome; ranking result",
        "main_missing_fields": "released pairwise rows and outcome labels; absolute probability forecasts are not the reported unit",
        "conclusion_change_feasibility": "medium for pairwise ranking robustness; low for point-probability claims",
        "next_action": "Treat as a ranking comparator and seek released pairwise rows for event-family de-duplication.",
    },
    {
        "benchmark_id": "marketbench",
        "citation_key": "fradkin2026marketbench",
        "primary_source_url": "https://arxiv.org/abs/2604.23897",
        "source_inventory_status": "paper reports 93 SWE-bench Lite tasks, model success-probability and token-usage calibration, and market-style allocation",
        "row_level_access_status": "unknown",
        "row_level_access_notes": "boundary-case route rather than direct event-forecast rows",
        "likely_obtainable_fields": "task id; self-reported success probability; token estimate; outcome; prior capability context if released",
        "main_missing_fields": "not an event-forecasting benchmark; task-success and cost calibration must be separated from GP-245 event forecasting",
        "conclusion_change_feasibility": "low for field-wide forecasting validity; useful as a self-assessment and allocation comparator",
        "next_action": "Keep in the audit as a boundary case, not as direct event-forecast evidence.",
    },
    {
        "benchmark_id": "reppo_infrastructure",
        "citation_key": "reppo2026",
        "primary_source_url": "https://reppo.xyz/",
        "source_inventory_status": "public site presents market infrastructure for training or evaluating AI through prediction-market mechanisms",
        "row_level_access_status": "unknown",
        "row_level_access_notes": "needs scored task rows or accessible example markets",
        "likely_obtainable_fields": "market definition; participant information time; settlement source; market baseline if examples are exposed",
        "main_missing_fields": "scored public task rows and settlement history are not confirmed in this inventory",
        "conclusion_change_feasibility": "low until example markets or task rows are accessible",
        "next_action": "Classify as infrastructure until row-level examples are available.",
    },
]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: list[dict[str, str]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        values = []
        for col in columns:
            values.append(str(row.get(col, "")).replace("\n", " ").replace("|", r"\|"))
        body.append("| " + " | ".join(values) + " |")
    return "\n".join([header, sep, *body])


def build_markdown(generated_at: str) -> str:
    focus = [
        "benchmark_id",
        "row_level_access_status",
        "conclusion_change_feasibility",
        "main_missing_fields",
        "next_action",
    ]
    counts: dict[str, int] = {}
    for row in ROWS:
        status = row["row_level_access_status"]
        counts[status] = counts.get(status, 0) + 1
    counts_text = ", ".join(f"{key}={counts[key]}" for key in sorted(counts))
    return "\n".join(
        [
            "# GP-245 Field-Wide Validity Source Inventory",
            "",
            f"Generated: `{generated_at}`",
            "",
            "Purpose: record the current external-source status for the 12 benchmark/evaluation routes in the GP-245 field-wide audit plan. This file is not a benchmark re-score. It identifies which sources appear to expose row-level data and which missing fields block a conclusion-change test.",
            "",
            f"Routes: `{len(ROWS)}`. Row-access status counts: `{counts_text}`.",
            "",
            "## Audit Readiness View",
            "",
            markdown_table(ROWS, focus),
            "",
            "## Full Source Inventory",
            "",
            markdown_table(ROWS, CSV_COLUMNS),
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    payload = {
        "schema": "gp245-field-wide-validity-source-inventory-v1",
        "generated_at": generated_at,
        "rows": ROWS,
    }

    json_path = args.out_dir / "field_wide_validity_source_inventory.json"
    csv_path = args.out_dir / "field_wide_validity_source_inventory.csv"
    md_path = args.out_dir / "field_wide_validity_source_inventory.md"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, ROWS)
    md_path.write_text(build_markdown(generated_at), encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "routes": len(ROWS),
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
