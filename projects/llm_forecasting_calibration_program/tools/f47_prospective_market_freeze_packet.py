#!/usr/bin/env python3
"""Build a prospective F47 packet with market bars frozen before LLM calls.

This is a no-LLM, no-DB-mutation acquisition tool. It samples currently open
Polymarket binary markets, freezes the current YES market probability into a
hidden key, and writes a contrastive dispatch queue that does not expose the
market price to the model.

The packet answers the next applied-science question for F47: can pairwise
prompt geometry add to, or beat, an external market bar when the bar is frozen
before any model calls? Retrospective resolved packets cannot answer that
causal-order question.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
WORKSPACE = (
    REPO
    / "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace"
)
DEFAULT_OUT_DIR = WORKSPACE / "f47_prospective_market_freeze_packet_2026_06_04"
GAMMA_BASE = "https://gamma-api.polymarket.com"

REQUIRED_OUTPUT_FIELDS = [
    "p_success_a",
    "p_success_b",
    "predicted_delta",
    "delta_driver",
    "rationale_short",
]


def read_json_url(url: str, *, timeout: float) -> Any:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ztare-f47-prospective-market-freeze/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


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
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def as_float(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    if out != out:
        return None
    return out


def as_probability(value: Any) -> float | None:
    out = as_float(value)
    if out is None or out < 0 or out > 1:
        return None
    return out


def yes_index(outcomes: list[Any]) -> int | None:
    for i, outcome in enumerate(outcomes):
        if str(outcome).strip().lower() == "yes":
            return i
    return None


def slug_family(slug: str) -> str:
    text = slug.lower()
    text = re.sub(r"\b(20\d{2}|19\d{2})\b", "year", text)
    text = re.sub(r"\b\d+\b", "num", text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:96] or "unknown"


def event_family(market: dict[str, Any]) -> str:
    events = market.get("events")
    if isinstance(events, list) and events:
        event = events[0] if isinstance(events[0], dict) else {}
        series = event.get("series")
        if isinstance(series, list) and series and isinstance(series[0], dict):
            series_slug = str(series[0].get("slug") or "")
            if series_slug:
                return f"series:{slug_family(series_slug)}"
        event_slug = str(event.get("slug") or "")
        if event_slug:
            return f"event:{slug_family(event_slug)}"
    slug = str(market.get("slug") or "")
    return f"market:{slug_family(slug)}"


def topic_bucket(question: str, slug: str) -> str:
    text = f"{question} {slug}".lower()
    buckets = {
        "politics": ("election", "president", "senate", "congress", "trump", "biden", "minister", "party"),
        "macro": ("fed", "rate", "inflation", "gdp", "recession", "unemployment", "cpi"),
        "crypto": ("bitcoin", "ethereum", "solana", "crypto", "token", "btc", "eth"),
        "sports": ("world cup", "nba", "nfl", "mlb", "soccer", "fifa", "win the", "championship"),
        "tech": ("openai", "tesla", "apple", "google", "ai", "spacex", "nvidia"),
        "culture": ("movie", "album", "grammy", "oscar", "youtube", "tiktok"),
    }
    for bucket, cues in buckets.items():
        if any(cue in text for cue in cues):
            return bucket
    return "general"


def question_length_bucket(question: str) -> str:
    n = len(question)
    if n < 90:
        return "short"
    if n < 220:
        return "medium"
    return "long"


def row_hash(row: dict[str, Any]) -> str:
    payload = json.dumps(
        {
            "market_id": row["market_id"],
            "slug": row["slug"],
            "question": row["question"],
            "frozen_market_p_yes": row["frozen_market_p_yes"],
            "frozen_at": row["frozen_at"],
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def market_pages(
    *,
    limit: int,
    max_pages: int,
    sleep_ms: int,
    timeout: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    for page in range(max_pages):
        params = urllib.parse.urlencode(
            {
                "closed": "false",
                "active": "true",
                "enableOrderBook": "true",
                "order": "volumeNum",
                "ascending": "false",
                "limit": str(limit),
                "offset": str(page * limit),
            }
        )
        url = f"{GAMMA_BASE}/markets?{params}"
        try:
            data = read_json_url(url, timeout=timeout)
        except Exception as exc:
            attempts.append(
                {
                    "page": page,
                    "ok": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:240],
                }
            )
            break
        if not isinstance(data, list) or not data:
            attempts.append({"page": page, "ok": True, "rows": 0})
            break
        page_rows = [row for row in data if isinstance(row, dict)]
        rows.extend(page_rows)
        attempts.append({"page": page, "ok": True, "rows": len(page_rows)})
        if sleep_ms:
            time.sleep(sleep_ms / 1000)
    return rows, attempts


def candidate_from_market(
    market: dict[str, Any],
    *,
    frozen_at: str,
    min_volume: float,
    min_liquidity: float,
    min_days_to_end: float,
    max_days_to_end: float,
    min_p: float,
    max_p: float,
) -> tuple[dict[str, Any] | None, str]:
    outcomes = parse_json_array(market.get("outcomes"))
    idx = yes_index(outcomes)
    if idx is None:
        return None, "no_yes_outcome"
    prices = parse_json_array(market.get("outcomePrices"))
    token_ids = parse_json_array(market.get("clobTokenIds"))
    if idx >= len(prices) or idx >= len(token_ids):
        return None, "missing_yes_price_or_token"
    p_yes = as_probability(prices[idx])
    if p_yes is None:
        return None, "invalid_yes_price"
    if p_yes < min_p or p_yes > max_p:
        return None, "outside_probability_band"
    volume = as_float(market.get("volumeNum") or market.get("volume")) or 0.0
    liquidity = as_float(market.get("liquidityNum") or market.get("liquidity")) or 0.0
    if volume < min_volume:
        return None, "low_volume"
    if liquidity < min_liquidity:
        return None, "low_liquidity"
    end_dt = parse_dt(market.get("endDate") or market.get("endDateIso"))
    if end_dt is None:
        return None, "missing_end_date"
    now = datetime.fromisoformat(frozen_at.replace("Z", "+00:00"))
    days_to_end = (end_dt - now).total_seconds() / 86400.0
    if days_to_end < min_days_to_end:
        return None, "too_near_resolution"
    if days_to_end > max_days_to_end:
        return None, "too_far_resolution"
    question = str(market.get("question") or "").strip()
    if not question:
        return None, "missing_question"
    slug = str(market.get("slug") or "")
    row = {
        "schema": "f47-prospective-market-freeze-row-v1",
        "source": "polymarket",
        "market_id": str(market.get("id") or ""),
        "condition_id": str(market.get("conditionId") or ""),
        "question_id": str(market.get("questionID") or ""),
        "slug": slug,
        "url": f"https://polymarket.com/event/{slug}" if slug else "",
        "question": question,
        "description": str(market.get("description") or "")[:1200],
        "end_date": end_dt.isoformat().replace("+00:00", "Z"),
        "days_to_end_at_freeze": round(days_to_end, 3),
        "frozen_at": frozen_at,
        "frozen_market_p_yes": p_yes,
        "frozen_market_p_no": round(1.0 - p_yes, 10),
        "yes_token_id": str(token_ids[idx]),
        "outcomes": outcomes,
        "outcome_prices": prices,
        "best_bid": as_probability(market.get("bestBid")),
        "best_ask": as_probability(market.get("bestAsk")),
        "last_trade_price": as_probability(market.get("lastTradePrice")),
        "spread": as_float(market.get("spread")),
        "volume": volume,
        "liquidity": liquidity,
        "event_family": event_family(market),
        "topic_bucket": topic_bucket(question, slug),
        "question_length_bucket": question_length_bucket(question),
        "resolution_source": str(market.get("resolutionSource") or ""),
    }
    row["freeze_row_sha256"] = row_hash(row)
    return row, "accepted"


def load_candidates(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    frozen_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    raw_markets, attempts = market_pages(
        limit=args.page_size,
        max_pages=args.max_pages,
        sleep_ms=args.sleep_ms,
        timeout=args.timeout,
    )
    reject_counts: Counter[str] = Counter()
    accepted: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    event_counts: Counter[str] = Counter()
    for market in raw_markets:
        row, reason = candidate_from_market(
            market,
            frozen_at=frozen_at,
            min_volume=args.min_volume,
            min_liquidity=args.min_liquidity,
            min_days_to_end=args.min_days_to_end,
            max_days_to_end=args.max_days_to_end,
            min_p=args.min_p,
            max_p=args.max_p,
        )
        if row is None:
            reject_counts[reason] += 1
            continue
        market_id = str(row["market_id"])
        if market_id in seen_ids:
            reject_counts["duplicate_market_id"] += 1
            continue
        if event_counts[row["event_family"]] >= args.max_per_event_family:
            reject_counts["event_family_cap"] += 1
            continue
        seen_ids.add(market_id)
        event_counts[row["event_family"]] += 1
        accepted.append(row)
        if len(accepted) >= args.max_candidates:
            break
    meta = {
        "frozen_at": frozen_at,
        "raw_markets_seen": len(raw_markets),
        "fetch_attempts": attempts,
        "reject_counts": dict(sorted(reject_counts.items())),
        "accepted_candidates": len(accepted),
        "event_family_counts": dict(sorted(event_counts.items())),
    }
    return accepted, meta


def pair_candidates(candidates: list[dict[str, Any]], *, target_pairs: int, min_pair_gap: float) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    rows = sorted(candidates, key=lambda r: (float(r["frozen_market_p_yes"]), -float(r["volume"]), r["market_id"]))
    used: set[str] = set()
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    lo = 0
    hi = len(rows) - 1
    while lo < hi and len(pairs) < target_pairs:
        low = rows[lo]
        high = rows[hi]
        lo += 1
        hi -= 1
        if low["market_id"] in used or high["market_id"] in used:
            continue
        gap = abs(float(high["frozen_market_p_yes"]) - float(low["frozen_market_p_yes"]))
        if gap < min_pair_gap:
            continue
        if low["event_family"] == high["event_family"]:
            continue
        used.add(str(low["market_id"]))
        used.add(str(high["market_id"]))
        pairs.append((high, low))
    return pairs


def build_packet(candidates: list[dict[str, Any]], args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    pairs = pair_candidates(
        candidates,
        target_pairs=args.target_pairs,
        min_pair_gap=args.min_pair_gap,
    )
    dispatch: list[dict[str, Any]] = []
    key: list[dict[str, Any]] = []
    for i, (high, low) in enumerate(pairs, start=1):
        if i % 2:
            a, b = high, low
        else:
            a, b = low, high
        pair_id = f"f47_prospective_market_freeze_{i:03d}"
        dispatch.append(
            {
                "schema": "f47-prospective-market-freeze-dispatch-v1",
                "pair_id": pair_id,
                "source": "polymarket",
                "freeze_key_ref": "hidden_answer_key",
                "contract_a": {
                    "market_id": a["market_id"],
                    "slug": a["slug"],
                    "url": a["url"],
                    "question": a["question"],
                    "description": a["description"],
                    "end_date": a["end_date"],
                    "topic_bucket": a["topic_bucket"],
                    "question_length_bucket": a["question_length_bucket"],
                },
                "contract_b": {
                    "market_id": b["market_id"],
                    "slug": b["slug"],
                    "url": b["url"],
                    "question": b["question"],
                    "description": b["description"],
                    "end_date": b["end_date"],
                    "topic_bucket": b["topic_bucket"],
                    "question_length_bucket": b["question_length_bucket"],
                },
                "required_output_fields": REQUIRED_OUTPUT_FIELDS,
                "scoring_endpoint": "prospective_market_frozen_f47_pairwise_then_resolved_brier",
            }
        )
        key.append(
            {
                "schema": "f47-prospective-market-freeze-answer-key-v1",
                "pair_id": pair_id,
                "source": "polymarket",
                "frozen_at": a["frozen_at"],
                "market_id_a": a["market_id"],
                "market_id_b": b["market_id"],
                "slug_a": a["slug"],
                "slug_b": b["slug"],
                "event_family_a": a["event_family"],
                "event_family_b": b["event_family"],
                "topic_bucket_a": a["topic_bucket"],
                "topic_bucket_b": b["topic_bucket"],
                "frozen_market_p_a": a["frozen_market_p_yes"],
                "frozen_market_p_b": b["frozen_market_p_yes"],
                "frozen_market_delta_a_minus_b": round(
                    float(a["frozen_market_p_yes"]) - float(b["frozen_market_p_yes"]),
                    10,
                ),
                "end_date_a": a["end_date"],
                "end_date_b": b["end_date"],
                "freeze_row_sha256_a": a["freeze_row_sha256"],
                "freeze_row_sha256_b": b["freeze_row_sha256"],
                "y_a": None,
                "y_b": None,
                "resolution_status": "unresolved_at_packet_build",
            }
        )
    report = {
        "schema": "f47-prospective-market-freeze-packet-report-v1",
        "date": "2026-06-04",
        "packet": "f47_prospective_market_freeze_packet",
        "dispatch_rows": len(dispatch),
        "unique_markets_in_dispatch": len({row["contract_a"]["market_id"] for row in dispatch} | {row["contract_b"]["market_id"] for row in dispatch}),
        "candidate_rows": len(candidates),
        "target_pairs": args.target_pairs,
        "min_pair_gap": args.min_pair_gap,
        "orientation_balance": {
            "a_market_higher_than_b": sum(1 for row in key if row["frozen_market_delta_a_minus_b"] > 0),
            "a_market_lower_than_b": sum(1 for row in key if row["frozen_market_delta_a_minus_b"] < 0),
        },
        "topic_counts_in_dispatch": dict(
            sorted(
                Counter(
                    [row["contract_a"]["topic_bucket"] for row in dispatch]
                    + [row["contract_b"]["topic_bucket"] for row in dispatch]
                ).items()
            )
        ),
        "validity_note": (
            "The market bar is frozen before any LLM calls and hidden from the dispatch queue. "
            "This packet is not evidence until calls are fired and markets resolve. "
            "Score future results against frozen market-only, raw LLM, F100-adjusted LLM, "
            "F47-translated LLM, and predeclared market+LLM blends."
        ),
    }
    return dispatch, key, report


def contract_corpus_rows(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in sorted(candidates, key=lambda item: str(item["market_id"])):
        rows.append(
            {
                "schema": "f47-prospective-polymarket-contract-v1",
                "contract_id": str(row["market_id"]),
                "question": row["question"],
                "source": "polymarket",
                "horizon": f"unresolved-end-{row['end_date'][:10]}",
                "y_known": None,
                "post_training_cutoff": True,
                "task_type": "polymarket_open_binary",
                "external_market_open": row["url"],
                "resolution_source_url": row.get("resolution_source") or row["url"],
                "y_known_provenance": "unresolved_at_packet_build",
                "frozen_at": row["frozen_at"],
                "frozen_market_p_yes": row["frozen_market_p_yes"],
                "event_family": row["event_family"],
                "topic_bucket": row["topic_bucket"],
                "freeze_row_sha256": row["freeze_row_sha256"],
                "raw_packet_row": row,
            }
        )
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_report_md(path: Path, report: dict[str, Any], acquisition: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# F47 Prospective Market-Freeze Packet",
        "",
        "This packet freezes external market probabilities before any LLM calls. It is a prospective validation surface for F47 translation, not fresh forecasting evidence yet.",
        "",
        f"- Dispatch rows / pairs: `{report['dispatch_rows']}`",
        f"- Unique markets in dispatch: `{report['unique_markets_in_dispatch']}`",
        f"- Candidate rows after filters: `{report['candidate_rows']}`",
        f"- Frozen at: `{acquisition['frozen_at']}`",
        f"- Raw markets seen: `{acquisition['raw_markets_seen']}`",
        f"- Reject counts: `{acquisition['reject_counts']}`",
        f"- Orientation balance: `{report['orientation_balance']}`",
        f"- Topic counts in dispatch: `{report['topic_counts_in_dispatch']}`",
        "",
        "## Files",
        "",
        f"- Dispatch queue: `{out_dir / 'f47_prospective_market_freeze_dispatch_queue.jsonl'}`",
        f"- Hidden answer key: `{out_dir / 'f47_prospective_market_freeze_answer_key.json'}`",
        f"- Freeze ledger: `{out_dir / 'f47_prospective_market_freeze_ledger.jsonl'}`",
        f"- Contract corpus: `{out_dir / 'f47_prospective_market_freeze_contracts.jsonl'}`",
        f"- Report JSON: `{out_dir / 'f47_prospective_market_freeze_report.json'}`",
        "",
        "## Promotion Gate",
        "",
        "After resolution, promote only if F47-translated probabilities beat raw/F100 and market-only by at least `0.01` Brier with paired `p<=0.05`, and if a predeclared market+LLM blend beats market-only without event-family regression. Until then this is an experiment queue.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--sleep-ms", type=int, default=50)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--max-candidates", type=int, default=80)
    parser.add_argument("--target-pairs", type=int, default=24)
    parser.add_argument("--max-per-event-family", type=int, default=1)
    parser.add_argument("--min-volume", type=float, default=10_000.0)
    parser.add_argument("--min-liquidity", type=float, default=500.0)
    parser.add_argument("--min-days-to-end", type=float, default=7.0)
    parser.add_argument("--max-days-to-end", type=float, default=545.0)
    parser.add_argument("--min-p", type=float, default=0.02)
    parser.add_argument("--max-p", type=float, default=0.98)
    parser.add_argument("--min-pair-gap", type=float, default=0.20)
    parser.add_argument(
        "--contracts-from-ledger",
        type=Path,
        default=None,
        help="Materialize only the unresolved contract corpus from an existing freeze ledger.",
    )
    args = parser.parse_args()

    if args.contracts_from_ledger is not None:
        candidates = read_jsonl(args.contracts_from_ledger)
        args.out_dir.mkdir(parents=True, exist_ok=True)
        out_path = args.out_dir / "f47_prospective_market_freeze_contracts.jsonl"
        write_jsonl(out_path, contract_corpus_rows(candidates))
        print(
            json.dumps(
                {
                    "mode": "contracts_from_ledger",
                    "ledger": str(args.contracts_from_ledger),
                    "contracts": len(candidates),
                    "out": str(out_path.relative_to(REPO) if out_path.is_relative_to(REPO) else out_path),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    candidates, acquisition = load_candidates(args)
    dispatch, key, report = build_packet(candidates, args)
    report = {**report, "acquisition": acquisition}

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_dir / "f47_prospective_market_freeze_dispatch_queue.jsonl", dispatch)
    write_jsonl(args.out_dir / "f47_prospective_market_freeze_ledger.jsonl", candidates)
    write_jsonl(args.out_dir / "f47_prospective_market_freeze_contracts.jsonl", contract_corpus_rows(candidates))
    (args.out_dir / "f47_prospective_market_freeze_answer_key.json").write_text(
        json.dumps({"answer_key": key, "report": report}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "f47_prospective_market_freeze_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report_md(args.out_dir / "f47_prospective_market_freeze_report.md", report, acquisition, args.out_dir)
    print(
        json.dumps(
            {
                "packet": report["packet"],
                "dispatch_rows": report["dispatch_rows"],
                "unique_markets_in_dispatch": report["unique_markets_in_dispatch"],
                "candidate_rows": report["candidate_rows"],
                "frozen_at": acquisition["frozen_at"],
                "reject_counts": acquisition["reject_counts"],
                "out_dir": str(args.out_dir.relative_to(REPO) if args.out_dir.is_relative_to(REPO) else args.out_dir),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
