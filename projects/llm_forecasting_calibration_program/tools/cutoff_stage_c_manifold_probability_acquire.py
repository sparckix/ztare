#!/usr/bin/env python3
"""Acquire historical Manifold probabilities for Law 3 Stage-C.

Reads `cutoff_stage_c_base_rate_join_missing_contracts.jsonl`, fetches public
Manifold market/bet history, and writes a local JSONL probability join file.

No DB mutation. No model calls. The default target is seven days before the
recorded resolution date, so the value is a pre-outcome market-implied
difficulty/base-rate proxy rather than an outcome match.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
WORKSPACE = REPO / "projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace"
DEFAULT_MISSING = WORKSPACE / "cutoff_stage_c_base_rate_join_missing_contracts.jsonl"
DEFAULT_OUT = WORKSPACE
API_BASE = "https://api.manifold.markets/v0"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def parse_resolve_date(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value)
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        try:
            dt = datetime.fromisoformat(text + "T00:00:00")
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def target_timestamp_ms(row: dict[str, Any], days_before_resolution: int) -> int | None:
    resolved = parse_resolve_date(row.get("resolve_date"))
    if resolved is None:
        return None
    target = resolved - timedelta(days=days_before_resolution)
    return int(target.timestamp() * 1000)


def slug_from_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urllib.parse.urlparse(str(url))
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return None
    return parts[-1]


def market_id_from_contract_id(contract_id: str) -> str | None:
    if contract_id.startswith("manifold_"):
        return contract_id[len("manifold_") :]
    if contract_id.startswith("fb_manifold_bulk_"):
        return contract_id[len("fb_manifold_bulk_") :]
    if contract_id.startswith("fb_manifold_"):
        return contract_id[len("fb_manifold_") :]
    return None


def http_json(path: str, *, timeout: int = 30) -> Any:
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ztare-gp245-stage-c-base-rate/1.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def try_get_market(row: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    slug = slug_from_url(row.get("source_url"))
    if slug:
        try:
            market = http_json(f"/slug/{urllib.parse.quote(slug)}")
            if isinstance(market, dict) and market.get("id"):
                return market, "slug"
        except Exception:
            pass
    market_id = market_id_from_contract_id(str(row.get("contract_id") or ""))
    if market_id:
        try:
            market = http_json(f"/market/{urllib.parse.quote(market_id)}")
            if isinstance(market, dict) and market.get("id"):
                return market, "market_id"
        except Exception:
            pass
    return None, "not_found"


def fetch_bets(market: dict[str, Any], *, max_pages: int, sleep_ms: int) -> list[dict[str, Any]]:
    contract_id = market.get("id")
    if not contract_id:
        return []
    bets: list[dict[str, Any]] = []
    before: str | None = None
    for _ in range(max_pages):
        query = {
            "contractId": str(contract_id),
            "limit": "1000",
        }
        if before:
            query["before"] = before
        path = "/bets?" + urllib.parse.urlencode(query)
        page = http_json(path)
        if not isinstance(page, list) or not page:
            break
        bets.extend([row for row in page if isinstance(row, dict)])
        before = page[-1].get("id")
        if not before or len(page) < 1000:
            break
        if sleep_ms:
            time.sleep(sleep_ms / 1000)
    return bets


def probability_at_target(
    market: dict[str, Any],
    bets: list[dict[str, Any]],
    target_ms: int,
) -> tuple[float | None, dict[str, Any] | None, str]:
    prior_bets = [
        bet
        for bet in bets
        if isinstance(bet.get("createdTime"), (int, float))
        and int(bet["createdTime"]) <= target_ms
        and isinstance(bet.get("probAfter"), (int, float))
    ]
    if prior_bets:
        bet = max(prior_bets, key=lambda b: int(b["createdTime"]))
        return float(bet["probAfter"]), bet, "latest_bet_before_target"
    initial = market.get("initialProbability") or market.get("initialProb")
    if isinstance(initial, (int, float)):
        p = float(initial)
        if p > 1:
            p /= 100.0
        return p, None, "market_initial_probability"
    return None, None, "no_pre_target_probability"


def probability_band(p: float | None) -> str:
    if p is None:
        return "missing"
    lo = int(max(0.0, min(0.999999, p)) / 0.2) * 20
    return f"{lo / 100:.2f}_{(lo + 20) / 100:.2f}"


def acquire_one(
    row: dict[str, Any],
    *,
    days_before_resolution: int,
    max_pages: int,
    sleep_ms: int,
) -> dict[str, Any]:
    target_ms = target_timestamp_ms(row, days_before_resolution)
    base = {
        "contract_id": row.get("contract_id"),
        "source_url": row.get("source_url"),
        "cutoff_relation": row.get("cutoff_relation"),
        "stratum_key": row.get("stratum_key"),
        "topic": row.get("topic"),
        "question_length_bucket": row.get("question_length_bucket"),
        "resolve_date": row.get("resolve_date"),
        "target_days_before_resolution": days_before_resolution,
        "target_timestamp_ms": target_ms,
    }
    if target_ms is None:
        return {**base, "fetch_status": "missing_resolve_date"}
    market, market_lookup = try_get_market(row)
    if not market:
        return {**base, "fetch_status": "market_not_found", "market_lookup": market_lookup}
    try:
        bets = fetch_bets(market, max_pages=max_pages, sleep_ms=sleep_ms)
    except urllib.error.HTTPError as exc:
        return {
            **base,
            "fetch_status": "bets_http_error",
            "market_lookup": market_lookup,
            "market_id": market.get("id"),
            "market_slug": market.get("slug"),
            "http_status": exc.code,
        }
    except Exception as exc:
        return {
            **base,
            "fetch_status": "bets_fetch_error",
            "market_lookup": market_lookup,
            "market_id": market.get("id"),
            "market_slug": market.get("slug"),
            "error": type(exc).__name__,
        }
    p, bet, method = probability_at_target(market, bets, target_ms)
    if p is None:
        return {
            **base,
            "fetch_status": "probability_missing",
            "market_lookup": market_lookup,
            "market_id": market.get("id"),
            "market_slug": market.get("slug"),
            "bets_fetched": len(bets),
            "selection_method": method,
        }
    return {
        **base,
        "fetch_status": "joined",
        "market_lookup": market_lookup,
        "market_id": market.get("id"),
        "market_slug": market.get("slug"),
        "market_created_time": market.get("createdTime"),
        "market_close_time": market.get("closeTime"),
        "bets_fetched": len(bets),
        "base_rate_value": p,
        "base_rate_band": probability_band(p),
        "base_rate_provenance": (
            "manifold_api_bets.probAfter"
            if method == "latest_bet_before_target"
            else "manifold_api_market.initialProbability"
        ),
        "prior_timestamp": target_ms,
        "selected_bet_id": (bet or {}).get("id"),
        "selected_bet_created_time": (bet or {}).get("createdTime"),
        "selection_method": method,
    }


def build_report(rows: list[dict[str, Any]], acquired: list[dict[str, Any]]) -> dict[str, Any]:
    joined = [row for row in acquired if row.get("fetch_status") == "joined"]
    return {
        "schema": "gp245-cutoff-stage-c-manifold-probability-acquisition-v1",
        "input_rows": len(rows),
        "joined_rows": len(joined),
        "missing_rows": len(acquired) - len(joined),
        "status_counts": dict(sorted(Counter(row.get("fetch_status") for row in acquired).items())),
        "joined_relation_counts": dict(sorted(Counter(row.get("cutoff_relation") for row in joined).items())),
        "base_rate_band_counts": dict(sorted(Counter(row.get("base_rate_band") for row in joined).items())),
    }


def render_md(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Cutoff Stage-C Manifold Probability Acquisition",
            "",
            f"- Schema: `{report['schema']}`",
            f"- Input rows: {report['input_rows']}",
            f"- Joined rows: {report['joined_rows']}",
            f"- Missing rows: {report['missing_rows']}",
            f"- Status counts: `{report['status_counts']}`",
            f"- Joined relation counts: `{report['joined_relation_counts']}`",
            f"- Base-rate bands: `{report['base_rate_band_counts']}`",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_MISSING)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--days-before-resolution", type=int, default=7)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--sleep-ms", type=int, default=100)
    args = parser.parse_args()
    rows = load_jsonl(args.input)
    if args.limit is not None:
        rows = rows[: args.limit]
    acquired = [
        acquire_one(
            row,
            days_before_resolution=args.days_before_resolution,
            max_pages=args.max_pages,
            sleep_ms=args.sleep_ms,
        )
        for row in rows
    ]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_jsonl = args.out_dir / "cutoff_stage_c_manifold_probability_acquisition.jsonl"
    write_jsonl(out_jsonl, acquired)
    report = build_report(rows, acquired)
    (args.out_dir / "cutoff_stage_c_manifold_probability_acquisition_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "cutoff_stage_c_manifold_probability_acquisition_report.md").write_text(
        render_md(report),
        encoding="utf-8",
    )
    print(f"wrote {out_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
