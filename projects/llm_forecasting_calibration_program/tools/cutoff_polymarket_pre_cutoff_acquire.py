#!/usr/bin/env python3
"""Acquire candidate Polymarket pre-cutoff rows for Law 3.

No DB mutation and no model calls. This is an external supply probe for the
second-source source-currency falsifier: find resolved Polymarket binary
markets whose resolution/closed time is before the panel cutoff and whose CLOB
price history contains a pre-outcome YES price.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.ztare.research_director.source_currency_discriminator import (
    classify_forecast_source_currency,
)


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_TARGETS = WORKSPACE / "cutoff_second_source_pre_cutoff_acquisition_targets.jsonl"
DEFAULT_OUT = WORKSPACE
GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"


def read_json_url(url: str, *, timeout: float = 20.0) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "ztare-gp245/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def parse_dt(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        try:
            dt = datetime.fromisoformat(text[:10])
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def parse_json_array(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if not isinstance(value, str):
        return []
    try:
        obj = json.loads(value)
    except Exception:
        return []
    return obj if isinstance(obj, list) else []


def as_probability(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    if 0 <= out <= 1:
        return out
    return None


def as_number(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def probability_band(value: float | None) -> str:
    if value is None:
        return "missing"
    if value < 0.10:
        return "0.00-0.10"
    if value < 0.25:
        return "0.10-0.25"
    if value < 0.50:
        return "0.25-0.50"
    if value < 0.75:
        return "0.50-0.75"
    if value < 0.90:
        return "0.75-0.90"
    return "0.90-1.00"


def length_band(question: str) -> str:
    n = len(question)
    if n < 80:
        return "<80"
    if n < 160:
        return "80-159"
    if n < 280:
        return "160-279"
    return "280+"


def yes_index(outcomes: list[Any]) -> int | None:
    for i, outcome in enumerate(outcomes):
        if str(outcome).strip().lower() == "yes":
            return i
    return None


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


def history_price_at(token_id: str, target: datetime) -> tuple[float | None, int | None, str]:
    params = urllib.parse.urlencode(
        {
            "market": token_id,
            "interval": "max",
            "fidelity": "1440",
        }
    )
    url = f"{CLOB_BASE}/prices-history?{params}"
    try:
        obj = read_json_url(url)
    except Exception as exc:
        return None, None, f"history_fetch_failed:{type(exc).__name__}"
    history = obj.get("history", []) if isinstance(obj, dict) else []
    if not history:
        return None, None, "history_empty"
    target_ts = int(target.timestamp())
    eligible = [
        row for row in history
        if isinstance(row, dict)
        and isinstance(row.get("t"), int)
        and row.get("t") <= target_ts
        and as_probability(row.get("p")) is not None
    ]
    if not eligible:
        return None, None, "no_history_before_target"
    row = max(eligible, key=lambda item: int(item["t"]))
    return float(row["p"]), int(row["t"]), "history_nearest_at_or_before_target"


def market_pages(*, limit: int, max_pages: int, sleep_ms: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in range(max_pages):
        params = urllib.parse.urlencode(
            {
                "closed": "true",
                "enableOrderBook": "true",
                "end_date_max": "2025-09-30T23:59:59Z",
                "order": "volumeNum",
                "ascending": "false",
                "limit": str(limit),
                "offset": str(page * limit),
            }
        )
        url = f"{GAMMA_BASE}/markets?{params}"
        data = read_json_url(url)
        if not isinstance(data, list) or not data:
            break
        rows.extend(row for row in data if isinstance(row, dict))
        if sleep_ms:
            time.sleep(sleep_ms / 1000)
    return rows


def target_counts(path: Path) -> Counter[tuple[str, str, str]]:
    counts: Counter[tuple[str, str, str]] = Counter()
    for row in read_jsonl(path):
        if row.get("source") != "polymarket":
            continue
        counts[
            (
                str(row.get("source")),
                str(row.get("freeze_value_band")),
                str(row.get("question_length_band")),
            )
        ] += int(row.get("target_pre_cutoff_rows") or 0)
    return counts


def candidate_from_market(
    market: dict[str, Any],
    *,
    cutoff_date: str,
    freeze_days_before_resolution: int,
) -> dict[str, Any] | None:
    question = str(market.get("question") or "")
    outcomes = parse_json_array(market.get("outcomes"))
    idx = yes_index(outcomes)
    if idx is None:
        return None
    token_ids = parse_json_array(market.get("clobTokenIds"))
    if idx >= len(token_ids):
        return None
    y_known = final_yes_outcome(market, idx)
    if y_known is None:
        return None
    closed_dt = parse_dt(market.get("closedTime") or market.get("umaEndDate") or market.get("endDate"))
    if closed_dt is None:
        return None
    target_dt = closed_dt - timedelta(days=freeze_days_before_resolution)
    p_yes, history_ts, status = history_price_at(str(token_ids[idx]), target_dt)
    if p_yes is None:
        return None
    source_currency = classify_forecast_source_currency(
        resolve_date=closed_dt.date().isoformat(),
        model_cutoff_date=cutoff_date,
        stored_post_training_cutoff=None,
        prefer_computed_cutoff=True,
    )
    if source_currency["cutoff_relation"] != "pre_cutoff":
        return None
    band = probability_band(p_yes)
    qband = length_band(question)
    return {
        "schema": "gp245-polymarket-pre-cutoff-candidate-v1",
        "source": "polymarket",
        "external_id": str(market.get("id")),
        "contract_id": f"polymarket::{market.get('id')}",
        "question": question,
        "slug": market.get("slug"),
        "url": f"https://polymarket.com/event/{market.get('slug')}",
        "resolution_source_url": market.get("resolutionSource") or "",
        "closed_time": closed_dt.isoformat(),
        "resolution_date": closed_dt.date().isoformat(),
        "cutoff_relation": source_currency["cutoff_relation"],
        "source_currency_receipt": source_currency,
        "freeze_datetime": target_dt.isoformat(),
        "freeze_days_before_resolution": freeze_days_before_resolution,
        "freeze_datetime_value": p_yes,
        "freeze_history_timestamp": history_ts,
        "freeze_value_band": band,
        "question_length": len(question),
        "question_length_band": qband,
        "y_known": y_known,
        "outcomes": outcomes,
        "yes_token_id": str(token_ids[idx]),
        "history_status": status,
        "event_slug": ((market.get("events") or [{}])[0] or {}).get("slug") if isinstance(market.get("events"), list) else None,
        "event_title": ((market.get("events") or [{}])[0] or {}).get("title") if isinstance(market.get("events"), list) else None,
        "category": market.get("category") or ((market.get("events") or [{}])[0] or {}).get("category") if isinstance(market.get("events"), list) else market.get("category"),
        "volume_num": as_number(market.get("volumeNum")),
        "raw_market": market,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    targets = target_counts(args.targets)
    target_total = sum(targets.values())
    target_length_bands = {key[2] for key in targets}
    markets = market_pages(limit=args.limit, max_pages=args.max_pages, sleep_ms=args.sleep_ms)
    candidates: list[dict[str, Any]] = []
    rejects = Counter()
    history_probes = 0
    for market in markets:
        question = str(market.get("question") or "")
        if length_band(question) not in target_length_bands:
            rejects["target_length_bucket_miss_before_history_probe"] += 1
            continue
        if history_probes >= args.max_history_probes:
            rejects["history_probe_cap_reached"] += 1
            continue
        history_probes += 1
        candidate = candidate_from_market(
            market,
            cutoff_date=args.cutoff_date,
            freeze_days_before_resolution=args.freeze_days_before_resolution,
        )
        if candidate is None:
            rejects["not_binary_yes_no_or_no_history_or_not_pre_cutoff"] += 1
            continue
        candidates.append(candidate)
        if len(candidates) >= target_total and args.stop_after_candidate_total:
            break
    by_cell: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        key = (candidate["source"], candidate["freeze_value_band"], candidate["question_length_band"])
        if key in targets:
            by_cell[" | ".join(key)].append(candidate)

    selected: list[dict[str, Any]] = []
    deficits: list[dict[str, Any]] = []
    for key, need in sorted(targets.items()):
        key_text = " | ".join(key)
        rows = sorted(by_cell.get(key_text, []), key=lambda r: float(r.get("volume_num") or 0), reverse=True)
        selected.extend(rows[:need])
        if len(rows) < need:
            deficits.append(
                {
                    "source": key[0],
                    "freeze_value_band": key[1],
                    "question_length_band": key[2],
                    "target_pre_cutoff_rows": need,
                    "candidate_rows_found": len(rows),
                    "deficit": need - len(rows),
                }
            )

    event_counts = Counter(str(row.get("event_slug") or row.get("slug")) for row in selected)
    candidate_event_counts = Counter(str(row.get("event_slug") or row.get("slug")) for row in candidates)
    category_counts = Counter(str(row.get("category") or "unknown") for row in selected)

    return {
        "schema": "gp245-polymarket-pre-cutoff-acquisition-v1",
        "cutoff_date": args.cutoff_date,
        "freeze_days_before_resolution": args.freeze_days_before_resolution,
        "api_basis": {
            "gamma": "https://gamma-api.polymarket.com/markets",
            "clob_history": "https://clob.polymarket.com/prices-history",
        },
        "targets_path": str(args.targets.relative_to(REPO)),
        "polymarket_target_total": sum(targets.values()),
        "markets_scanned": len(markets),
        "history_probes": history_probes,
        "max_history_probes": args.max_history_probes,
        "candidate_rows_found": len(candidates),
        "selected_rows": len(selected),
        "target_cells": [
            {
                "source": key[0],
                "freeze_value_band": key[1],
                "question_length_band": key[2],
                "target_pre_cutoff_rows": value,
            }
            for key, value in sorted(targets.items())
        ],
        "selected_by_cell": dict(Counter(
            f"{row['source']} | {row['freeze_value_band']} | {row['question_length_band']}"
            for row in selected
        )),
        "selected_unique_event_families": len(event_counts),
        "candidate_unique_event_families": len(candidate_event_counts),
        "selected_event_family_counts": dict(event_counts.most_common(20)),
        "candidate_event_family_counts": dict(candidate_event_counts.most_common(20)),
        "selected_category_counts": dict(category_counts.most_common(20)),
        "quality_flags": [
            "sibling_event_family_duplicates_present" if any(v > 1 for v in event_counts.values()) else "no_event_family_duplicates_detected",
            "manual_resolution_source_review_required",
        ],
        "deficits": deficits,
        "reject_counts": dict(rejects),
        "nearest_confuser_rejected": (
            "Using final settled outcomePrices as the pre-outcome baseline is rejected. "
            "Selected rows require a CLOB history price at or before the freeze datetime."
        ),
        "smallest_next_step": (
            "Review selected rows for duplicated event families and write an ingest preview; "
            "if selected_rows reaches the Polymarket target, the remaining Law 3 second-source "
            "deficit is Metaculus supply and/or manual quality review rather than public API access."
        ),
        "candidate_manifest": candidates,
        "selected_manifest": selected,
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# Polymarket Pre-Cutoff Acquisition Probe",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Cutoff date: `{report['cutoff_date']}`",
        f"- Freeze: {report['freeze_days_before_resolution']} days before resolution",
        f"- Polymarket target rows: {report['polymarket_target_total']}",
        f"- Markets scanned: {report['markets_scanned']}",
        f"- Candidate rows found: {report['candidate_rows_found']}",
        f"- Candidate unique event families: {report['candidate_unique_event_families']}",
        f"- Selected rows: {report['selected_rows']}",
        f"- Unique event families among selected rows: {report['selected_unique_event_families']}",
        "",
        "## Selected By Cell",
        "",
        "```json",
        json.dumps(report["selected_by_cell"], indent=2, sort_keys=True),
        "```",
        "",
        "## Deficits",
        "",
        "```json",
        json.dumps(report["deficits"], indent=2, sort_keys=True),
        "```",
        "",
        "## Selected Event Families",
        "",
        "```json",
        json.dumps(report["selected_event_family_counts"], indent=2, sort_keys=True),
        "```",
        "",
        "## Quality Flags",
        "",
        "```json",
        json.dumps(report["quality_flags"], indent=2, sort_keys=True),
        "```",
        "",
        "## Nearest Confuser Rejected",
        "",
        report["nearest_confuser_rejected"],
        "",
        "## Smallest Next Step",
        "",
        report["smallest_next_step"],
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--cutoff-date", default="2025-10-01")
    parser.add_argument("--freeze-days-before-resolution", type=int, default=7)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--max-history-probes", type=int, default=80)
    parser.add_argument("--stop-after-candidate-total", action="store_true")
    parser.add_argument("--sleep-ms", type=int, default=100)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args)
    (args.out_dir / "cutoff_polymarket_pre_cutoff_acquisition_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    (args.out_dir / "cutoff_polymarket_pre_cutoff_acquisition_report.md").write_text(
        render_md(report), encoding="utf-8"
    )
    with (args.out_dir / "cutoff_polymarket_pre_cutoff_candidate_manifest.jsonl").open(
        "w", encoding="utf-8"
    ) as f:
        for row in report["selected_manifest"]:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    with (args.out_dir / "cutoff_polymarket_pre_cutoff_all_candidates.jsonl").open(
        "w", encoding="utf-8"
    ) as f:
        for row in report["candidate_manifest"]:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in (
        "polymarket_target_total",
        "markets_scanned",
        "history_probes",
        "candidate_rows_found",
        "selected_rows",
        "deficits",
    )}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
