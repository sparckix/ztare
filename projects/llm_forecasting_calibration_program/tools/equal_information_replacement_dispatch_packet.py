#!/usr/bin/env python3
"""Build the model-dispatch packet for the replacement equal-information sample.

No model calls. No DB mutation.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_SAMPLE = (
    WORKSPACE
    / "equal_information_replacement_sample_2026_06_15/equal_information_replacement_sample.json"
)
DEFAULT_OUT = WORKSPACE / "equal_information_replacement_dispatch_packet_2026_06_15"
DEFAULT_PILOT_ID = "equal_information_replacement_model_forecast_v1"
DEFAULT_BASELINE_PILOT_ID = "equal_information_replacement_polymarket_baseline_v1"
DEFAULT_PANEL_CUTOFF = "2025-10-01"

FAMILIES = {
    "claude": "claude_subscription",
    "codex_54mini": "codex_subscription",
    "gemini": "gemini_api_or_manual",
    "deepseek": "deepseek_api_or_manual",
}


def repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return obj


def length_bucket(question: str) -> str:
    n = len(question)
    if n < 80:
        return "short"
    if n < 180:
        return "medium"
    return "long"


def prompt(row: dict[str, Any], *, panel_cutoff_date: str) -> str:
    return (
        "You are making a tool-free binary forecast. Do not browse, search, or use external tools.\n"
        "Use only your internal knowledge as of the model cutoff implied by the experiment.\n"
        "Do not use or infer a prediction-market price.\n"
        "Estimate the probability that the event described by the question resolved YES.\n"
        "Return only a JSON object with keys: p_success, confidence, recognition_self_report, "
        "cutoff_relation, source, topic, base_rate_band, source_finding_ids, rationale_short.\n"
        "Echo these string fields exactly: cutoff_relation=\"post_cutoff\", source=\"polymarket\", "
        "topic=\"unknown\", base_rate_band=\"withheld\".\n\n"
        f"Question: {row['question']}\n"
        "Source: polymarket\n"
        f"Topic: {row.get('topic') or 'unknown'}\n"
        "Cutoff relation to echo: post_cutoff\n"
        "Base-rate band to echo: withheld\n"
        f"Panel cutoff date: {panel_cutoff_date}\n\n"
        "Definitions: p_success is a number in [0,1]. confidence is your confidence in that probability, "
        "in [0,1]. recognition_self_report is how much you believe you recognize this exact resolved "
        "question or answer from memory, in [0,1]. source_finding_ids must be "
        "[\"EQUAL_INFORMATION_REPLACEMENT_V1\"]. Keep rationale_short under 40 words."
    )


def contract_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_id": row["contract_id"],
        "question": row["question"],
        "source": "polymarket",
        "source_corpus": row.get("source_corpus")
        or "equal_information_replacement_polymarket_2026_06_15",
        "horizon": f"{row.get('horizon_days_before_resolution', 2)}d_before_resolution",
        "y_known": int(row["y_known"]),
        "post_training_cutoff": 1,
        "task_type": "binary_forecast",
        "external_market_open": row.get("market_start_at"),
        "resolution_source_url": row.get("resolution_source_url") or row.get("market_url"),
        "y_known_provenance": "polymarket_resolved_outcome_with_yes_no_token_mapping",
        "raw_json": json.dumps(row, sort_keys=True),
    }


def baseline_request_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_id": row["contract_id"],
        "question": row["question"],
        "source": "polymarket",
        "source_corpus": row.get("source_corpus")
        or "equal_information_replacement_polymarket_2026_06_15",
        "cutoff_relation": "post_cutoff",
        "market_slug": row.get("market_slug"),
        "market_url": row.get("market_url"),
        "target_freeze_date_utc": row.get("target_freeze_at"),
        "resolve_date": row.get("resolve_date"),
        "y_known": int(row["y_known"]),
        "topic": row.get("topic") or "unknown",
        "question_length_band": row.get("question_length_band"),
        "freeze_value_band": row.get("freeze_value_band"),
    }


def baseline_result_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "gp245-equal-information-baseline-export-result-row-v1",
        "contract_id": row["contract_id"],
        "market_slug": row.get("market_slug"),
        "market_url": row.get("market_url"),
        "market_asset_id_yes": row.get("market_asset_id_yes"),
        "market_asset_id_no": row.get("market_asset_id_no"),
        "outcomes": row.get("outcomes"),
        "yes_price_at_or_before_freeze": row.get("yes_price_at_or_before_freeze"),
        "history_timestamp": row.get("history_timestamp"),
        "history_source": row.get("history_source"),
    }


def dispatch_row(
    row: dict[str, Any],
    *,
    pilot_id: str,
    family: str,
    panel_cutoff_date: str,
) -> dict[str, Any]:
    question = str(row["question"])
    return {
        "schema": "gp245-equal-information-replacement-dispatch-v1",
        "pilot_id": pilot_id,
        "dispatch_id": f"{pilot_id}:{family}:{row['contract_id']}",
        "contract_id": row["contract_id"],
        "family": family,
        "runtime_route": FAMILIES[family],
        "condition": "tool_free_equal_information_replacement",
        "primitive": "equal_information_market_comparison_forecast",
        "cutoff_relation": "post_cutoff",
        "source": "polymarket",
        "topic": row.get("topic") or "unknown",
        "base_rate_band": "withheld",
        "question_length_bucket": length_bucket(question),
        "resolve_date": row.get("resolve_date"),
        "panel_cutoff_date": panel_cutoff_date,
        "source_finding_ids": ["EQUAL_INFORMATION_REPLACEMENT_V1"],
        "expected_json_keys": [
            "p_success",
            "confidence",
            "recognition_self_report",
            "cutoff_relation",
            "source",
            "topic",
            "base_rate_band",
            "source_finding_ids",
            "rationale_short",
        ],
        "prompt": prompt(row, panel_cutoff_date=panel_cutoff_date),
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    sample = load_json(args.sample)
    selected = [row for row in sample.get("selected_rows_data", []) if isinstance(row, dict)]
    if len(selected) != int(sample.get("selected_rows") or 0):
        raise SystemExit("selected_rows_data length does not match selected_rows")
    families = args.family or list(FAMILIES)
    invalid = sorted(set(families) - set(FAMILIES))
    if invalid:
        raise SystemExit(f"unknown families: {', '.join(invalid)}")
    contracts = [contract_row(row) for row in selected]
    requests = [baseline_request_row(row) for row in selected]
    results = [baseline_result_row(row) for row in selected]
    queue = [
        dispatch_row(row, pilot_id=args.pilot_id, family=family, panel_cutoff_date=args.panel_cutoff_date)
        for row in selected
        for family in families
    ]
    return {
        "schema": "gp245-equal-information-replacement-dispatch-packet-v1",
        "sample": repo_rel(args.sample),
        "pilot_id": args.pilot_id,
        "baseline_pilot_id": args.baseline_pilot_id,
        "panel_cutoff_date": args.panel_cutoff_date,
        "selected_rows": len(selected),
        "dispatch_rows": len(queue),
        "families": families,
        "outcome_counts": dict(sorted(Counter(str(row["y_known"]) for row in selected).items())),
        "freeze_band_counts": dict(
            sorted(Counter(str(row.get("freeze_value_band") or "unknown") for row in selected).items())
        ),
        "contract_rows": contracts,
        "baseline_packet": {"schema": "gp245-equal-information-baseline-export-packet-v1", "rows": requests},
        "baseline_results": results,
        "queue": queue,
        "interpretation": (
            "Frozen replacement packet. The market baseline is known before model calls, "
            "but prompts withhold market prices. Model-side validity still requires a "
            "credible cutoff receipt at or before panel_cutoff_date."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--pilot-id", default=DEFAULT_PILOT_ID)
    parser.add_argument("--baseline-pilot-id", default=DEFAULT_BASELINE_PILOT_ID)
    parser.add_argument("--panel-cutoff-date", default=DEFAULT_PANEL_CUTOFF)
    parser.add_argument("--family", action="append")
    args = parser.parse_args()
    packet = build(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "equal_information_replacement_dispatch_packet.json").write_text(
        json.dumps({k: v for k, v in packet.items() if k not in {"queue", "contract_rows", "baseline_packet", "baseline_results"}}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "equal_information_replacement_contract_rows.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in packet["contract_rows"]),
        encoding="utf-8",
    )
    (args.out_dir / "equal_information_replacement_baseline_packet.json").write_text(
        json.dumps(packet["baseline_packet"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "equal_information_replacement_baseline_results.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in packet["baseline_results"]),
        encoding="utf-8",
    )
    (args.out_dir / "equal_information_replacement_dispatch_queue.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in packet["queue"]),
        encoding="utf-8",
    )
    summary = {
        key: packet[key]
        for key in (
            "schema",
            "pilot_id",
            "baseline_pilot_id",
            "panel_cutoff_date",
            "selected_rows",
            "dispatch_rows",
            "families",
            "outcome_counts",
            "freeze_band_counts",
        )
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
