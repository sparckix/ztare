#!/usr/bin/env python3
"""Probe Polymarket post-cutoff rows for comparable pre-outcome prices.

This is a no-DB, no-LLM acquisition check for the Law 3 second-source smoke.
It asks whether the frozen post-cutoff Polymarket rows have CLOB history at the
same pre-resolution freeze horizon used by the acquired pre-cutoff slice.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.error
from collections import Counter
from datetime import timedelta
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

from cutoff_polymarket_pre_cutoff_acquire import (  # noqa: E402
    GAMMA_BASE,
    as_number,
    as_probability,
    history_price_at,
    parse_dt,
    parse_json_array,
    probability_band,
    read_json_url,
    read_jsonl,
    yes_index,
)


PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_PANEL = (
    WORKSPACE
    / "cutoff_second_source_freeze_probe_deepseek_2026_06_03"
    / "cutoff_stage_b_minimum_panel_contracts.jsonl"
)
DEFAULT_OUT = WORKSPACE / "cutoff_second_source_polymarket_post_price_probe_2026_06_03"


def repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def slug_from_url(url: Any) -> str:
    text = str(url or "").strip().rstrip("/")
    if not text:
        return ""
    parts = urllib.parse.urlparse(text)
    bits = [part for part in parts.path.split("/") if part]
    if not bits:
        return ""
    return bits[-1]


def gamma_market_by_slug(slug: str) -> tuple[dict[str, Any] | None, str]:
    if not slug:
        return None, "missing_slug"
    params = urllib.parse.urlencode({"slug": slug, "limit": "5"})
    try:
        data = read_json_url(f"{GAMMA_BASE}/markets?{params}")
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        return None, f"gamma_fetch_failed:URLError:{reason}"
    except Exception as exc:
        return None, f"gamma_fetch_failed:{type(exc).__name__}:{exc}"
    if not isinstance(data, list) or not data:
        return None, "gamma_no_market"
    for row in data:
        if isinstance(row, dict) and str(row.get("slug") or "") == slug:
            return row, "gamma_slug_exact"
    for row in data:
        if isinstance(row, dict):
            return row, "gamma_first_result_slug_mismatch"
    return None, "gamma_no_object_market"


def final_yes_outcome(market: dict[str, Any], idx: int) -> int | None:
    prices = parse_json_array(market.get("outcomePrices"))
    if idx >= len(prices):
        return None
    p = as_probability(prices[idx])
    if p is None:
        return None
    if p >= 0.95:
        return 1
    if p <= 0.05:
        return 0
    return None


def row_probe(row: dict[str, Any], *, freeze_days_before_resolution: int) -> dict[str, Any]:
    slug = slug_from_url(row.get("resolution_source_url"))
    market, gamma_status = gamma_market_by_slug(slug)
    out: dict[str, Any] = {
        "schema": "gp245-polymarket-post-price-probe-row-v1",
        "contract_id": row.get("contract_id"),
        "question": row.get("question"),
        "source": row.get("source"),
        "cutoff_relation": row.get("cutoff_relation"),
        "stratum_key": row.get("stratum_key"),
        "topic": row.get("topic"),
        "question_length_bucket": row.get("question_length_bucket"),
        "resolve_date": row.get("resolve_date"),
        "y_known": row.get("y_known"),
        "resolution_source_url": row.get("resolution_source_url"),
        "slug": slug,
        "gamma_status": gamma_status,
    }
    if market is None:
        return {**out, "join_status": gamma_status}
    outcomes = parse_json_array(market.get("outcomes"))
    idx = yes_index(outcomes)
    token_ids = parse_json_array(market.get("clobTokenIds"))
    if idx is None or idx >= len(token_ids):
        return {**out, "join_status": "missing_yes_token", "outcomes": outcomes}
    resolved = parse_dt(row.get("resolve_date"))
    market_end = parse_dt(market.get("closedTime") or market.get("umaEndDate") or market.get("endDate"))
    target = (resolved or market_end)
    if target is None:
        return {**out, "join_status": "missing_resolution_datetime", "outcomes": outcomes}
    freeze_dt = target - timedelta(days=freeze_days_before_resolution)
    p_yes, history_ts, history_status = history_price_at(str(token_ids[idx]), freeze_dt)
    final_yes = final_yes_outcome(market, idx)
    join_status = "joined" if p_yes is not None else history_status
    return {
        **out,
        "join_status": join_status,
        "outcomes": outcomes,
        "yes_token_id": str(token_ids[idx]),
        "freeze_datetime": freeze_dt.isoformat(),
        "freeze_days_before_resolution": freeze_days_before_resolution,
        "freeze_datetime_value": p_yes,
        "freeze_history_timestamp": history_ts,
        "freeze_value_band": probability_band(p_yes),
        "history_status": history_status,
        "gamma_market_id": market.get("id"),
        "gamma_question": market.get("question"),
        "gamma_slug": market.get("slug"),
        "gamma_closed_time": market.get("closedTime"),
        "gamma_end_date": market.get("endDate"),
        "gamma_volume_num": as_number(market.get("volumeNum")),
        "gamma_final_yes": final_yes,
        "gamma_final_yes_matches_y_known": (
            final_yes == int(row["y_known"])
            if final_yes is not None and row.get("y_known") in (0, 1)
            else None
        ),
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    panel = read_jsonl(args.panel)
    rows = [
        row for row in panel
        if row.get("source") == "polymarket" and row.get("cutoff_relation") == "post_cutoff"
    ]
    probes: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        if i and args.sleep_ms:
            time.sleep(args.sleep_ms / 1000)
        probes.append(row_probe(row, freeze_days_before_resolution=args.freeze_days_before_resolution))
    joined = [row for row in probes if row.get("join_status") == "joined"]
    return {
        "schema": "gp245-polymarket-post-price-probe-v1",
        "panel": repo_rel(args.panel),
        "freeze_days_before_resolution": args.freeze_days_before_resolution,
        "rows_considered": len(rows),
        "joined_rows": len(joined),
        "join_status_counts": dict(Counter(str(row.get("join_status")) for row in probes)),
        "history_status_counts": dict(Counter(str(row.get("history_status")) for row in probes if row.get("history_status"))),
        "freeze_value_band_counts": dict(Counter(str(row.get("freeze_value_band")) for row in joined)),
        "final_yes_match_counts": dict(Counter(str(row.get("gamma_final_yes_matches_y_known")) for row in probes)),
        "interpretation": (
            "Post-cutoff Polymarket rows have comparable pre-outcome CLOB prices."
            if len(joined) == len(rows) and rows
            else "Post-cutoff Polymarket base-rate repair is incomplete at the matched freeze horizon."
        ),
        "rows": probes,
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cutoff_second_source_polymarket_post_price_probe.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (out_dir / "cutoff_second_source_polymarket_post_price_probe_rows.jsonl").open("w", encoding="utf-8") as fh:
        for row in report["rows"]:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    lines = [
        "# Law 3 Polymarket Post-Cutoff Price Probe",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Rows considered: `{report['rows_considered']}`",
        f"- Joined rows: `{report['joined_rows']}`",
        f"- Join status counts: `{report['join_status_counts']}`",
        f"- History status counts: `{report['history_status_counts']}`",
        f"- Freeze value bands: `{report['freeze_value_band_counts']}`",
        f"- Final YES match counts: `{report['final_yes_match_counts']}`",
        "",
        "## Interpretation",
        "",
        report["interpretation"],
        "",
    ]
    (out_dir / "cutoff_second_source_polymarket_post_price_probe.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--freeze-days-before-resolution", type=int, default=7)
    parser.add_argument("--sleep-ms", type=int, default=100)
    args = parser.parse_args()
    report = build(args)
    write_outputs(report, args.out_dir)
    print(json.dumps({k: report[k] for k in ("rows_considered", "joined_rows", "join_status_counts", "history_status_counts")}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
