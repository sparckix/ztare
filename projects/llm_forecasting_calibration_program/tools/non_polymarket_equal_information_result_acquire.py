#!/usr/bin/env python3
"""Fill the non-Polymarket equal-information packet from public Manifold APIs.

Network-only acquisition, no model calls, no DB mutation.

For each Manifold request row, this tool:
1. resolves the market slug to the public API market id,
2. verifies the resolved YES/NO outcome against the canonical packet outcome,
3. selects the latest public bet at or before the frozen timestamp, and
4. records that bet's probAfter as the market probability receipt.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
PACKET_DIR = (
    PROGRAM
    / "cutoff_validity_v1/workspace/non_polymarket_equal_information_export_packet_2026_06_15"
)
DEFAULT_REQUEST_ROWS = PACKET_DIR / "non_polymarket_equal_information_export_request_rows.jsonl"
DEFAULT_OUT = PACKET_DIR / "manifold_history_fill_2026_06_15"
MANIFOLD_API = "https://api.manifold.markets/v0"


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO))
    except ValueError:
        return str(path)


def read_json_url(url: str, *, timeout: int) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "gp245-equal-info-audit/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise SystemExit(f"row {lineno} in {path} is not a JSON object")
        rows.append(obj)
    return rows


def parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def probability(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        p = float(value)
    except (TypeError, ValueError):
        return None
    if 0.0 <= p <= 1.0:
        return p
    return None


def market_resolution_to_y(market: dict[str, Any]) -> int | None:
    resolution = str(market.get("resolution") or "").upper()
    if resolution == "YES":
        return 1
    if resolution == "NO":
        return 0
    return None


def fetch_market(slug: str, *, timeout: int) -> tuple[dict[str, Any] | None, str | None]:
    url = f"{MANIFOLD_API}/slug/{urllib.parse.quote(slug, safe='')}"
    try:
        obj = read_json_url(url, timeout=timeout)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return None, f"market_fetch_failed:{type(exc).__name__}"
    if not isinstance(obj, dict) or not obj.get("id"):
        return None, "market_fetch_invalid_payload"
    return obj, None


def fetch_latest_bet_before(
    contract_id: str, target_ms: int, *, timeout: int
) -> tuple[dict[str, Any] | None, str | None, str]:
    params = urllib.parse.urlencode(
        {
            "contractId": contract_id,
            "beforeTime": target_ms,
            "limit": 1,
            "order": "desc",
        }
    )
    url = f"{MANIFOLD_API}/bets?{params}"
    try:
        obj = read_json_url(url, timeout=timeout)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return None, url, f"bets_fetch_failed:{type(exc).__name__}"
    if not isinstance(obj, list):
        return None, url, "bets_fetch_invalid_payload"
    if not obj:
        return None, url, "no_bet_at_or_before_target"
    bet = obj[0]
    if not isinstance(bet, dict):
        return None, url, "bet_row_invalid_payload"
    return bet, url, "history_nearest_at_or_before_target"


def fill_row(row: dict[str, Any], *, timeout: int) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    source = str(row.get("source") or "")
    if source != "manifold":
        errors.append("unsupported_source")

    target_dt = parse_dt(row.get("target_freeze_datetime_utc"))
    if target_dt is None:
        errors.append("invalid_target_freeze_datetime")

    slug = str(row.get("market_slug") or "").strip()
    if not slug:
        errors.append("missing_market_slug")

    market: dict[str, Any] | None = None
    market_error: str | None = None
    if slug:
        market, market_error = fetch_market(slug, timeout=timeout)
        if market_error:
            errors.append(market_error)

    market_y = market_resolution_to_y(market or {})
    packet_y = int(row["y_known"]) if row.get("y_known") in (0, 1) else None
    if market_y is None:
        errors.append("market_resolution_not_binary_yes_no")
    elif packet_y is None:
        errors.append("packet_y_known_not_binary")
    elif market_y != packet_y:
        errors.append("market_resolution_disagrees_with_packet_y")

    bet: dict[str, Any] | None = None
    bet_url: str | None = None
    bet_status = "not_attempted"
    if market and target_dt is not None:
        bet, bet_url, bet_status = fetch_latest_bet_before(
            str(market["id"]), ms(target_dt), timeout=timeout
        )
        if bet is None:
            errors.append(bet_status)

    p = probability((bet or {}).get("probAfter"))
    if bet is not None and p is None:
        errors.append("missing_or_invalid_prob_after")

    created_time = (bet or {}).get("createdTime")
    if bet is not None and not isinstance(created_time, (int, float)):
        errors.append("missing_bet_created_time")
    if target_dt is not None and isinstance(created_time, (int, float)) and created_time > ms(target_dt):
        errors.append("bet_after_target_freeze")

    brier = None
    if p is not None and packet_y in (0, 1):
        brier = (p - packet_y) ** 2

    if market and market.get("outcomeType") != "BINARY":
        warnings.append(f"market_outcome_type:{market.get('outcomeType')}")

    return {
        "schema": "gp245-non-polymarket-equal-information-filled-row-v1",
        "contract_id": row.get("contract_id"),
        "source": source,
        "source_corpus": row.get("source_corpus"),
        "question": row.get("question"),
        "market_url": row.get("market_url"),
        "market_slug": slug,
        "manifold_contract_id": (market or {}).get("id"),
        "target_freeze_datetime_utc": row.get("target_freeze_datetime_utc"),
        "history_probability": p,
        "history_timestamp": (
            datetime.fromtimestamp(float(created_time) / 1000.0, tz=timezone.utc).isoformat()
            if isinstance(created_time, (int, float))
            else None
        ),
        "history_timestamp_ms": int(created_time) if isinstance(created_time, (int, float)) else None,
        "history_source": bet_url,
        "history_status": bet_status,
        "probability_field": "probAfter",
        "resolved_binary_outcome": market_y,
        "packet_y_known": packet_y,
        "market_resolution": (market or {}).get("resolution"),
        "outcome_mapping": {
            "probability_semantics": "Manifold binary market YES probability from latest public bet probAfter at or before target freeze",
            "resolution_semantics": "YES maps to 1 and NO maps to 0",
            "market_resolution": (market or {}).get("resolution"),
        },
        "brier": brier,
        "schema_ok": 0 if errors else 1,
        "errors": errors,
        "warnings": warnings,
        "raw_market": {
            "id": (market or {}).get("id"),
            "url": (market or {}).get("url"),
            "question": (market or {}).get("question"),
            "createdTime": (market or {}).get("createdTime"),
            "resolution": (market or {}).get("resolution"),
            "resolutionTime": (market or {}).get("resolutionTime"),
            "outcomeType": (market or {}).get("outcomeType"),
        },
        "raw_bet": bet,
    }


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    requests = load_jsonl(args.request_rows)
    fills: list[dict[str, Any]] = []
    for idx, row in enumerate(requests):
        if idx and args.sleep_ms:
            time.sleep(args.sleep_ms / 1000.0)
        fills.append(fill_row(row, timeout=args.timeout))

    valid = [row for row in fills if int(row.get("schema_ok") or 0) == 1]
    errors = Counter(err for row in fills for err in row.get("errors", []))
    status_counts = Counter(str(row.get("history_status")) for row in fills)
    outcome_counts = Counter(str(row.get("resolved_binary_outcome")) for row in valid)
    return {
        "schema": "gp245-non-polymarket-equal-information-result-acquire-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "request_rows": repo_relative(args.request_rows),
            "api_docs": "https://docs.manifold.markets/api",
            "manifold_api_base": MANIFOLD_API,
        },
        "rows": fills,
        "summary": {
            "requested_rows": len(requests),
            "valid_rows": len(valid),
            "invalid_rows": len(fills) - len(valid),
            "error_counts": dict(errors),
            "history_status_counts": dict(status_counts),
            "outcome_counts": dict(outcome_counts),
            "mean_market_brier": mean([float(row["brier"]) for row in valid if row.get("brier") is not None]),
            "state": (
                "filled_all_requested_rows"
                if len(valid) == len(requests)
                else "partial_or_failed_fill"
            ),
            "acceptance_gate": (
                "Rows may be ingested as equal-information evidence only when schema_ok=1, "
                "history_probability is in [0,1], history_timestamp is at or before the "
                "frozen timestamp, and the resolved binary outcome matches the packet row."
            ),
        },
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "non_polymarket_equal_information_result_acquire.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (out_dir / "non_polymarket_equal_information_filled_rows.jsonl").open(
        "w", encoding="utf-8"
    ) as fh:
        for row in report["rows"]:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    summary = report["summary"]
    lines = [
        "# Non-Polymarket Equal-Information Result Acquire",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- State: `{summary['state']}`",
        f"- Requested rows: `{summary['requested_rows']}`",
        f"- Valid rows: `{summary['valid_rows']}`",
        f"- Invalid rows: `{summary['invalid_rows']}`",
        f"- Error counts: `{summary['error_counts']}`",
        f"- History status counts: `{summary['history_status_counts']}`",
        f"- Outcome counts: `{summary['outcome_counts']}`",
        f"- Mean market Brier: `{summary['mean_market_brier']}`",
        f"- Acceptance gate: {summary['acceptance_gate']}",
        "",
        "## Rows",
        "",
        "| contract | status | p | y | brier | timestamp | errors |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in report["rows"]:
        lines.append(
            "| {contract} | {status} | {p} | {y} | {brier} | {ts} | {errors} |".format(
                contract=row.get("contract_id"),
                status="ok" if row.get("schema_ok") else "invalid",
                p=row.get("history_probability"),
                y=row.get("resolved_binary_outcome"),
                brier=row.get("brier"),
                ts=row.get("history_timestamp") or "",
                errors=", ".join(row.get("errors") or []),
            )
        )
    (out_dir / "non_polymarket_equal_information_result_acquire.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-rows", type=Path, default=DEFAULT_REQUEST_ROWS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--sleep-ms", type=int, default=100)
    args = parser.parse_args()
    report = build_report(args)
    write_outputs(report, args.out_dir)
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
