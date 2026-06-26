#!/usr/bin/env python3
"""Run a GP-245 row-schema pilot on PredictionMarketBench episodes.

The included PredictionMarketBench repository ships replay episodes, not stored
LLM forecast rows. This script therefore checks whether the released episode
data can support source-currency, label-time, and equal-information fields, and
whether a same-time market baseline can be reconstructed. It does not claim a
model-vs-market result.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_REPO_DIR = Path("/private/tmp/gp245_predictionmarketbench/PredictionMarketBench")
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"
PUBLIC_REPO_URL = "https://github.com/Oddpool/PredictionMarketBench"

EPISODE_COLUMNS = [
    "episode_id",
    "tickers",
    "settled_tickers",
    "orderbook_rows",
    "trade_rows",
    "market_baseline_rows",
    "market_baseline_brier",
    "start_ts",
    "end_ts",
]


@dataclass
class EpisodeSummary:
    episode_id: str
    tickers: int
    settled_tickers: int
    orderbook_rows: int
    trade_rows: int
    market_baseline_rows: int
    market_baseline_brier: float | None
    start_ts: str
    end_ts: str

    def as_row(self) -> dict[str, str]:
        return {
            "episode_id": self.episode_id,
            "tickers": str(self.tickers),
            "settled_tickers": str(self.settled_tickers),
            "orderbook_rows": str(self.orderbook_rows),
            "trade_rows": str(self.trade_rows),
            "market_baseline_rows": str(self.market_baseline_rows),
            "market_baseline_brier": ""
            if self.market_baseline_brier is None
            else f"{self.market_baseline_brier:.12g}",
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
        }


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_head(repo_dir: Path) -> str:
    head = (repo_dir / ".git/HEAD").read_text(encoding="utf-8").strip() if (repo_dir / ".git/HEAD").exists() else ""
    if head.startswith("ref:"):
        ref = head.split(" ", 1)[1]
        ref_path = repo_dir / ".git" / ref
        return ref_path.read_text(encoding="utf-8").strip() if ref_path.exists() else ""
    return head


def parse_levels(value: Any) -> list[dict[str, float]]:
    if value is None:
        return []
    if isinstance(value, float) and math.isnan(value):
        return []
    if isinstance(value, str):
        value = value.strip()
        if not value or value == "[]":
            return []
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if not isinstance(value, list):
        return []
    levels = []
    for item in value:
        if not isinstance(item, dict):
            continue
        price = item.get("price_cents", item.get("price"))
        size = item.get("size")
        try:
            price_cents = float(price)
            if price_cents < 1:
                price_cents *= 100.0
            size_f = float(size)
        except (TypeError, ValueError):
            continue
        if 0 < price_cents < 100 and size_f > 0:
            levels.append({"price_cents": price_cents, "size": size_f})
    return levels


def yes_mid_probability(row: pd.Series) -> float | None:
    yes_bids = parse_levels(row.get("yes_bids"))
    no_bids = parse_levels(row.get("no_bids"))
    if not yes_bids or not no_bids:
        return None
    yes_best_bid = max(item["price_cents"] for item in yes_bids)
    no_best_bid = max(item["price_cents"] for item in no_bids)
    yes_best_ask = 100.0 - no_best_bid
    if yes_best_ask <= 0 or yes_best_ask >= 100:
        return None
    midpoint = (yes_best_bid + yes_best_ask) / 200.0
    if math.isnan(midpoint) or midpoint < 0 or midpoint > 1:
        return None
    return midpoint


def brier(probability: float, outcome: float) -> float:
    return (probability - outcome) ** 2


def inspect_episode(episode_dir: Path) -> tuple[EpisodeSummary, list[dict[str, str]]]:
    metadata = read_json(episode_dir / "metadata.json")
    settlements = read_json(episode_dir / "settlement.json")
    outcomes = {
        ticker: 1.0 if str(item.get("result", "")).upper() == "YES" else 0.0
        for ticker, item in settlements.items()
        if item.get("result") in {"YES", "NO"}
    }
    settled_ts = {
        ticker: str(item.get("settled_ts") or "")
        for ticker, item in settlements.items()
        if item.get("result") in {"YES", "NO"}
    }
    orderbook = pd.read_parquet(episode_dir / "orderbook.parquet")
    trades = pd.read_parquet(episode_dir / "trades.parquet")

    baseline_scores: list[float] = []
    sample_rows: list[dict[str, str]] = []
    for _, row in orderbook.iterrows():
        ticker = str(row.get("ticker"))
        if ticker not in outcomes:
            continue
        probability = yes_mid_probability(row)
        if probability is None:
            continue
        score = brier(probability, outcomes[ticker])
        baseline_scores.append(score)
        if len(sample_rows) < 12:
            sample_rows.append(
                {
                    "episode_id": episode_dir.name,
                    "ticker": ticker,
                    "snapshot_ts": str(row.get("ts")),
                    "settled_ts": settled_ts.get(ticker, ""),
                    "outcome_yes": str(int(outcomes[ticker])),
                    "market_probability_yes_mid": f"{probability:.6f}",
                    "market_brier": f"{score:.12g}",
                }
            )

    summary = EpisodeSummary(
        episode_id=episode_dir.name,
        tickers=len(metadata.get("tickers") or []),
        settled_tickers=len(outcomes),
        orderbook_rows=len(orderbook),
        trade_rows=len(trades),
        market_baseline_rows=len(baseline_scores),
        market_baseline_brier=sum(baseline_scores) / len(baseline_scores) if baseline_scores else None,
        start_ts=str(metadata.get("start_ts") or ""),
        end_ts=str(metadata.get("end_ts") or ""),
    )
    return summary, sample_rows


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
        body.append("| " + " | ".join(str(row.get(col, "")).replace("|", r"\|") for col in columns) + " |")
    return "\n".join([header, sep, *body])


def build_markdown(report: dict[str, Any]) -> str:
    episode_rows = report["episode_summaries"]
    sample_rows = report["sample_rows"][:12]
    sample_columns = [
        "episode_id",
        "ticker",
        "snapshot_ts",
        "outcome_yes",
        "market_probability_yes_mid",
        "market_brier",
    ]
    lines = [
        "# GP-245 PredictionMarketBench Row-Schema Pilot",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"- Repository: `{report['public_repo_url']}`",
        f"- Repository directory: `{report['repo_dir']}`",
        f"- Repository commit: `{report['repo_head']}`",
        f"- Episodes: `{report['episodes']}`",
        f"- Tickers: `{report['tickers']}`",
        f"- Settled tickers: `{report['settled_tickers']}`",
        f"- Orderbook rows: `{report['orderbook_rows']}`",
        f"- Trade rows: `{report['trade_rows']}`",
        f"- Same-time market baseline rows: `{report['market_baseline_rows']}`",
        f"- Overall market-baseline Brier: `{report['market_baseline_brier']}`",
        f"- Stored model forecast rows: `{report['stored_model_forecast_rows']}`",
        "",
        "Interpretation: the released episodes provide timestamped market states and settlements, so a same-time market baseline is row-auditable. They do not contain stored LLM forecast rows; model comparisons require running the benchmark software or obtaining submitted agent traces.",
        "",
        "## Episode Summary",
        "",
        markdown_table(episode_rows, EPISODE_COLUMNS),
        "",
        "## Sample Baseline Rows",
        "",
        markdown_table(sample_rows, sample_columns),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-dir", type=Path, default=DEFAULT_REPO_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    episodes_dir = args.repo_dir / "episodes"
    if not episodes_dir.exists():
        raise SystemExit(f"PredictionMarketBench episodes directory not found: {episodes_dir}")
    episode_dirs = sorted(path for path in episodes_dir.iterdir() if path.is_dir())
    summaries: list[EpisodeSummary] = []
    sample_rows: list[dict[str, str]] = []
    for episode in episode_dirs:
        summary, samples = inspect_episode(episode)
        summaries.append(summary)
        sample_rows.extend(samples)

    total_orderbook = sum(item.orderbook_rows for item in summaries)
    total_trades = sum(item.trade_rows for item in summaries)
    total_tickers = sum(item.tickers for item in summaries)
    total_settled = sum(item.settled_tickers for item in summaries)
    baseline_scores_weighted = [
        (item.market_baseline_brier or 0.0, item.market_baseline_rows)
        for item in summaries
        if item.market_baseline_brier is not None
    ]
    total_baseline_rows = sum(weight for _, weight in baseline_scores_weighted)
    overall_brier = (
        sum(score * weight for score, weight in baseline_scores_weighted) / total_baseline_rows
        if total_baseline_rows
        else None
    )
    report = {
        "schema": "gp245-predictionmarketbench-row-schema-pilot-v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "public_repo_url": PUBLIC_REPO_URL,
        "repo_dir": str(args.repo_dir),
        "repo_head": repo_head(args.repo_dir),
        "episodes": len(summaries),
        "tickers": total_tickers,
        "settled_tickers": total_settled,
        "orderbook_rows": total_orderbook,
        "trade_rows": total_trades,
        "market_baseline_rows": total_baseline_rows,
        "market_baseline_brier": None if overall_brier is None else f"{overall_brier:.12g}",
        "stored_model_forecast_rows": 0,
        "row_schema_status": "episode_market_baseline_ready_model_forecasts_absent",
        "validity_fields": {
            "source_currency": "snapshot timestamp and settlement timestamp present",
            "label_time": "settlement outcome and settlement timestamp present",
            "equal_information": "same-time orderbook state present; midpoint baseline reconstructable",
            "model_comparison": "stored model forecast rows absent from released episodes",
        },
        "episode_summaries": [item.as_row() for item in summaries],
        "sample_rows": sample_rows,
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "field_wide_predictionmarketbench_row_schema_pilot.json"
    csv_path = args.out_dir / "field_wide_predictionmarketbench_row_schema_pilot.csv"
    sample_csv_path = args.out_dir / "field_wide_predictionmarketbench_sample_rows.csv"
    md_path = args.out_dir / "field_wide_predictionmarketbench_row_schema_pilot.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, [item.as_row() for item in summaries], EPISODE_COLUMNS)
    write_csv(
        sample_csv_path,
        sample_rows,
        [
            "episode_id",
            "ticker",
            "snapshot_ts",
            "settled_ts",
            "outcome_yes",
            "market_probability_yes_mid",
            "market_brier",
        ],
    )
    md_path.write_text(build_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": report["schema"],
                "episodes": report["episodes"],
                "tickers": report["tickers"],
                "orderbook_rows": report["orderbook_rows"],
                "trade_rows": report["trade_rows"],
                "market_baseline_rows": report["market_baseline_rows"],
                "stored_model_forecast_rows": report["stored_model_forecast_rows"],
                "outputs": [str(json_path), str(csv_path), str(sample_csv_path), str(md_path)],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
