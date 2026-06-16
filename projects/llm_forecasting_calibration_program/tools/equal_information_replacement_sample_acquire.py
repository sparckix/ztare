#!/usr/bin/env python3
"""Acquire a replacement Polymarket equal-information sample.

No DB mutation and no model calls.

The first 24-row post-cutoff Polymarket packet was not salvageable: most
markets were not open by the seven-day target, and a shorter day-horizon sweep
still left missing CLOB history. This tool searches resolved Polymarket markets
for rows that are eligible before any LLM call is made:

1. resolved after the model cutoff,
2. binary YES/NO with a decoded final outcome,
3. market accepting orders at or before the target freeze timestamp,
4. nonempty CLOB history with a YES price at or before target,
5. optional one-row-per-event de-correlation.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

from cutoff_polymarket_pre_cutoff_acquire import (  # noqa: E402
    GAMMA_BASE,
    as_number,
    as_probability,
    final_yes_outcome,
    history_price_at,
    length_band,
    parse_dt,
    parse_json_array,
    probability_band,
    read_json_url,
    yes_index,
)
from src.ztare.research_director.source_currency_discriminator import (  # noqa: E402
    classify_forecast_source_currency,
)


PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_OUT = WORKSPACE / "equal_information_replacement_sample_2026_06_15"


def repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def market_url(market: dict[str, Any]) -> str:
    slug = str(market.get("slug") or "")
    event_slug = ""
    events = market.get("events")
    if isinstance(events, list) and events and isinstance(events[0], dict):
        event_slug = str(events[0].get("slug") or "")
    if event_slug:
        return f"https://polymarket.com/event/{event_slug}/{slug}"
    return f"https://polymarket.com/market/{slug}"


def event_slug(market: dict[str, Any]) -> str:
    events = market.get("events")
    if isinstance(events, list) and events and isinstance(events[0], dict):
        return str(events[0].get("slug") or "")
    return str(market.get("slug") or "")


def category(market: dict[str, Any]) -> str:
    if market.get("category"):
        return str(market.get("category"))
    events = market.get("events")
    if isinstance(events, list) and events and isinstance(events[0], dict):
        if events[0].get("category"):
            return str(events[0].get("category"))
    tags = market.get("tags")
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, dict) and tag.get("label"):
                return str(tag["label"])
    return "unknown"


def no_token_id(outcomes: list[Any], token_ids: list[Any]) -> str | None:
    for i, outcome in enumerate(outcomes):
        if str(outcome).strip().lower() == "no" and i < len(token_ids):
            return str(token_ids[i])
    return None


def market_pages(
    *,
    limit: int,
    max_pages: int,
    sleep_ms: int,
    end_date_min: str,
    end_date_max: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in range(max_pages):
        params = urllib.parse.urlencode(
            {
                "closed": "true",
                "enableOrderBook": "true",
                "end_date_min": end_date_min,
                "end_date_max": end_date_max,
                "order": "volumeNum",
                "ascending": "false",
                "limit": str(limit),
                "offset": str(page * limit),
            }
        )
        data = read_json_url(f"{GAMMA_BASE}/markets?{params}")
        if not isinstance(data, list) or not data:
            break
        rows.extend(row for row in data if isinstance(row, dict))
        if sleep_ms:
            time.sleep(sleep_ms / 1000)
    return rows


def candidate_from_market(
    market: dict[str, Any],
    *,
    cutoff_date: str,
    horizon_days_before_resolution: int,
) -> tuple[dict[str, Any] | None, str]:
    question = str(market.get("question") or "")
    outcomes = parse_json_array(market.get("outcomes"))
    idx = yes_index(outcomes)
    if idx is None:
        return None, "not_binary_yes_no"
    token_ids = parse_json_array(market.get("clobTokenIds"))
    if idx >= len(token_ids):
        return None, "missing_yes_token"
    y_known = final_yes_outcome(market, idx)
    if y_known is None:
        return None, "final_outcome_not_decoded"
    closed_dt = parse_dt(market.get("closedTime") or market.get("umaEndDate") or market.get("endDate"))
    if closed_dt is None:
        return None, "missing_close_datetime"
    source_currency = classify_forecast_source_currency(
        resolve_date=closed_dt.date().isoformat(),
        model_cutoff_date=cutoff_date,
        stored_post_training_cutoff=None,
        prefer_computed_cutoff=True,
    )
    if source_currency["cutoff_relation"] != "post_cutoff":
        return None, f"cutoff_relation_{source_currency['cutoff_relation']}"
    target_dt = closed_dt - timedelta(days=horizon_days_before_resolution)
    accepting_orders = parse_dt(market.get("acceptingOrdersTimestamp"))
    start_dt = parse_dt(market.get("startDate"))
    open_dt = accepting_orders or start_dt
    if open_dt is None:
        return None, "missing_open_datetime"
    if open_dt > target_dt:
        return None, "market_not_open_by_target"
    p_yes, history_ts, history_status = history_price_at(str(token_ids[idx]), target_dt)
    if p_yes is None:
        return None, history_status
    cid = f"polymarket_replacement_{market.get('conditionId') or market.get('id')}"
    return {
        "schema": "gp245-equal-information-replacement-polymarket-row-v1",
        "contract_id": cid,
        "source": "polymarket",
        "source_corpus": "equal_information_replacement_polymarket_2026_06_15",
        "external_id": str(market.get("id") or ""),
        "condition_id": str(market.get("conditionId") or ""),
        "question": question,
        "market_slug": market.get("slug"),
        "event_slug": event_slug(market),
        "market_url": market_url(market),
        "resolution_source_url": market.get("resolutionSource") or "",
        "resolve_date": closed_dt.date().isoformat(),
        "closed_time": closed_dt.isoformat(),
        "market_start_at": start_dt.isoformat() if start_dt else None,
        "accepting_orders_at": accepting_orders.isoformat() if accepting_orders else None,
        "target_freeze_at": target_dt.isoformat(),
        "horizon_days_before_resolution": horizon_days_before_resolution,
        "y_known": y_known,
        "outcomes": outcomes,
        "market_asset_id_yes": str(token_ids[idx]),
        "market_asset_id_no": no_token_id(outcomes, token_ids),
        "yes_price_at_or_before_freeze": p_yes,
        "history_timestamp": history_ts,
        "history_source": "clob.polymarket.com/prices-history",
        "history_status": history_status,
        "freeze_value_band": probability_band(p_yes),
        "question_length": len(question),
        "question_length_band": length_band(question),
        "topic": category(market),
        "volume_num": as_number(market.get("volumeNum")),
        "liquidity_num": as_number(market.get("liquidityNum")),
        "final_yes_matches_y_known": True,
        "source_currency_receipt": source_currency,
        "eligibility_receipt": {
            "post_cutoff": True,
            "binary_yes_no": True,
            "market_open_by_target": True,
            "nonempty_history_before_target": True,
            "auditable_yes_token_mapping": True,
            "equal_information_human_or_market_baseline": True,
        },
    }, "eligible"


def select_rows(candidates: list[dict[str, Any]], *, target_rows: int, max_per_event: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    event_counts: Counter[str] = Counter()
    # Prefer liquid markets, but enforce event spread before allowing repeats.
    for row in sorted(candidates, key=lambda item: float(item.get("volume_num") or 0), reverse=True):
        key = str(row.get("event_slug") or row.get("market_slug"))
        if event_counts[key] >= max_per_event:
            continue
        selected.append(row)
        event_counts[key] += 1
        if len(selected) >= target_rows:
            break
    return selected


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    markets = market_pages(
        limit=args.limit,
        max_pages=args.max_pages,
        sleep_ms=args.page_sleep_ms,
        end_date_min=args.end_date_min,
        end_date_max=args.end_date_max,
    )
    candidates: list[dict[str, Any]] = []
    rejects: Counter[str] = Counter()
    history_probes = 0
    for market in markets:
        if history_probes >= args.max_history_probes:
            rejects["history_probe_cap_reached"] += 1
            break
        candidate, status = candidate_from_market(
            market,
            cutoff_date=args.cutoff_date,
            horizon_days_before_resolution=args.horizon_days_before_resolution,
        )
        if candidate is None:
            rejects[status] += 1
            if status in {"history_empty", "no_history_before_target", "history_fetch_failed:URLError"}:
                history_probes += 1
            elif status.startswith("history_fetch_failed"):
                history_probes += 1
            continue
        history_probes += 1
        candidates.append(candidate)
        if args.stop_after_candidates and len(candidates) >= args.stop_after_candidates:
            break
    selected = select_rows(
        candidates,
        target_rows=args.target_rows,
        max_per_event=args.max_per_event,
    )
    selected_ids = {row["contract_id"] for row in selected}
    candidate_counts = {
        "by_topic": dict(Counter(str(row.get("topic") or "unknown") for row in candidates).most_common()),
        "by_outcome": dict(Counter(str(row.get("y_known")) for row in candidates).most_common()),
        "by_freeze_value_band": dict(Counter(str(row.get("freeze_value_band")) for row in candidates).most_common()),
        "by_question_length_band": dict(Counter(str(row.get("question_length_band")) for row in candidates).most_common()),
    }
    selected_counts = {
        "by_topic": dict(Counter(str(row.get("topic") or "unknown") for row in selected).most_common()),
        "by_outcome": dict(Counter(str(row.get("y_known")) for row in selected).most_common()),
        "by_freeze_value_band": dict(Counter(str(row.get("freeze_value_band")) for row in selected).most_common()),
        "by_question_length_band": dict(Counter(str(row.get("question_length_band")) for row in selected).most_common()),
        "events": len({str(row.get("event_slug") or row.get("market_slug")) for row in selected}),
    }
    return {
        "schema": "gp245-equal-information-replacement-sample-acquisition-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selection_rule": {
            "cutoff_date": args.cutoff_date,
            "end_date_min": args.end_date_min,
            "end_date_max": args.end_date_max,
            "horizon_days_before_resolution": args.horizon_days_before_resolution,
            "target_rows": args.target_rows,
            "max_per_event": args.max_per_event,
            "order": "Gamma closed, order=volumeNum desc; select highest-volume eligible rows under max_per_event",
            "no_llm_calls": True,
            "db_mutation": False,
        },
        "api_basis": {
            "gamma": f"{GAMMA_BASE}/markets",
            "clob_history": "https://clob.polymarket.com/prices-history",
        },
        "markets_scanned": len(markets),
        "history_probes": history_probes,
        "reject_counts": dict(sorted(rejects.items())),
        "candidate_rows": len(candidates),
        "selected_rows": len(selected),
        "candidate_counts": candidate_counts,
        "selected_counts": selected_counts,
        "verdict": (
            "replacement_sample_ready_for_model_packet"
            if len(selected) >= args.target_rows
            else "replacement_sample_underfilled"
        ),
        "next_action": (
            "Run model forecasts only after freezing this selected sample and its "
            "equal-information market baseline rows."
            if len(selected) >= args.target_rows
            else "Increase scan depth or relax event cap before model calls."
        ),
        "selected_rows_data": selected,
        "candidate_rows_data": [
            {**row, "selected": row["contract_id"] in selected_ids}
            for row in candidates
        ],
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "equal_information_replacement_sample.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (out_dir / "equal_information_replacement_selected_rows.jsonl").open("w", encoding="utf-8") as fh:
        for row in report["selected_rows_data"]:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    with (out_dir / "equal_information_replacement_candidate_rows.jsonl").open("w", encoding="utf-8") as fh:
        for row in report["candidate_rows_data"]:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    result_rows = [
        {
            "schema": "gp245-equal-information-baseline-export-result-row-v1",
            "contract_id": row["contract_id"],
            "market_asset_id_yes": row["market_asset_id_yes"],
            "market_asset_id_no": row["market_asset_id_no"],
            "yes_price_at_or_before_freeze": row["yes_price_at_or_before_freeze"],
            "history_timestamp": row["history_timestamp"],
            "history_source": row["history_source"],
            "outcomes": row["outcomes"],
            "market_slug": row["market_slug"],
            "market_url": row["market_url"],
        }
        for row in report["selected_rows_data"]
    ]
    with (out_dir / "equal_information_replacement_result_rows.jsonl").open("w", encoding="utf-8") as fh:
        for row in result_rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    lines = [
        "# Equal-Information Replacement Sample Acquisition",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Verdict: `{report['verdict']}`",
        f"- Generated: `{report['generated_at']}`",
        f"- Horizon days before resolution: `{report['selection_rule']['horizon_days_before_resolution']}`",
        f"- Markets scanned: `{report['markets_scanned']}`",
        f"- History probes: `{report['history_probes']}`",
        f"- Candidate rows: `{report['candidate_rows']}`",
        f"- Selected rows: `{report['selected_rows']}`",
        f"- Reject counts: `{report['reject_counts']}`",
        f"- Selected counts: `{report['selected_counts']}`",
        "",
        "## Next Action",
        "",
        report["next_action"],
        "",
        "## Artifacts",
        "",
        f"- Selected rows: `{repo_rel(out_dir / 'equal_information_replacement_selected_rows.jsonl')}`",
        f"- Candidate rows: `{repo_rel(out_dir / 'equal_information_replacement_candidate_rows.jsonl')}`",
        f"- Result rows: `{repo_rel(out_dir / 'equal_information_replacement_result_rows.jsonl')}`",
        "",
    ]
    (out_dir / "equal_information_replacement_sample.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--cutoff-date", default="2025-10-01")
    parser.add_argument("--end-date-min", default="2025-10-02T00:00:00Z")
    parser.add_argument("--end-date-max", default="2026-06-15T23:59:59Z")
    parser.add_argument("--horizon-days-before-resolution", type=int, default=2)
    parser.add_argument("--target-rows", type=int, default=24)
    parser.add_argument("--max-per-event", type=int, default=1)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=8)
    parser.add_argument("--max-history-probes", type=int, default=160)
    parser.add_argument("--stop-after-candidates", type=int, default=80)
    parser.add_argument("--page-sleep-ms", type=int, default=100)
    args = parser.parse_args()
    report = build_report(args)
    write_outputs(report, args.out_dir)
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "candidate_rows": report["candidate_rows"],
                "selected_rows": report["selected_rows"],
                "selected_counts": report["selected_counts"],
                "reject_counts": report["reject_counts"],
                "next_action": report["next_action"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
