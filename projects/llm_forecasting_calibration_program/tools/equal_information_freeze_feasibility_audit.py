#!/usr/bin/env python3
"""Classify why equal-information Polymarket rows did not fill.

No network, no DB mutation.

The equal-information acceptance rule asks for the nearest YES price at or
before a seven-day pre-resolution freeze timestamp. For short-lived Polymarket
markets, the target timestamp can precede market creation or order acceptance,
making the requested row design-ineligible rather than merely missing from the
local API response. This audit separates joined rows, market-not-open rows, and
history gaps.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_PACKET = (
    WORKSPACE
    / "equal_information_baseline_export_packet_2026_06_05"
    / "equal_information_baseline_export_packet.json"
)
DEFAULT_PROBE = (
    WORKSPACE
    / "cutoff_second_source_polymarket_post_price_probe_2026_06_03"
    / "cutoff_second_source_polymarket_post_price_probe.json"
)
DEFAULT_OUT = WORKSPACE / "equal_information_freeze_feasibility_2026_06_15"


def repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return obj


def parse_dt(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) == 10:
        text = f"{text}T00:00:00+00:00"
    elif text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def classify(row: dict[str, Any], request: dict[str, Any] | None) -> dict[str, Any]:
    target = parse_dt((request or {}).get("target_freeze_date_utc"))
    market_start = parse_dt(row.get("gamma_start_date"))
    accepting_orders = parse_dt(row.get("gamma_accepting_orders_timestamp"))
    open_at = accepting_orders or market_start
    join_status = str(row.get("join_status") or "")
    if join_status == "joined":
        reason = "joined"
    elif target is not None and open_at is not None and open_at > target:
        reason = "market_not_open_by_target_freeze"
    elif join_status == "no_history_before_target":
        reason = "history_exists_only_after_target"
    elif join_status == "history_empty":
        reason = "clob_history_empty"
    else:
        reason = join_status or "unknown"
    return {
        "contract_id": row.get("contract_id"),
        "market_slug": row.get("slug"),
        "question": row.get("question"),
        "join_status": join_status,
        "feasibility_class": reason,
        "target_freeze_at": target.isoformat() if target else None,
        "market_start_at": market_start.isoformat() if market_start else None,
        "accepting_orders_at": accepting_orders.isoformat() if accepting_orders else None,
        "freeze_price": row.get("freeze_datetime_value"),
        "history_timestamp": row.get("freeze_history_timestamp"),
        "y_known": row.get("y_known"),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    packet = read_json(args.packet)
    probe = read_json(args.probe)
    requests = {
        str(row.get("contract_id")): row
        for row in packet.get("rows", [])
        if isinstance(row, dict) and row.get("contract_id")
    }
    rows = [
        classify(row, requests.get(str(row.get("contract_id"))))
        for row in probe.get("rows", [])
        if isinstance(row, dict)
    ]
    counts = Counter(str(row["feasibility_class"]) for row in rows)
    unfilled_counts = Counter(
        str(row["feasibility_class"]) for row in rows if row["feasibility_class"] != "joined"
    )
    return {
        "schema": "gp245-equal-information-freeze-feasibility-v1",
        "packet": repo_rel(args.packet),
        "probe": repo_rel(args.probe),
        "rows": rows,
        "summary": {
            "requested_rows": len(requests),
            "probe_rows": len(rows),
            "joined_rows": counts.get("joined", 0),
            "unfilled_rows": len(rows) - counts.get("joined", 0),
            "feasibility_counts": dict(sorted(counts.items())),
            "unfilled_feasibility_counts": dict(sorted(unfilled_counts.items())),
            "interpretation": (
                "Rows classified as market_not_open_by_target_freeze are not fillable under "
                "the seven-day freeze rule from public Polymarket history; they require a "
                "different predeclared freeze horizon or a different target sample."
            ),
        },
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "equal_information_freeze_feasibility.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Equal-Information Freeze Feasibility Audit",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Requested rows: `{report['summary']['requested_rows']}`",
        f"- Probe rows: `{report['summary']['probe_rows']}`",
        f"- Joined rows: `{report['summary']['joined_rows']}`",
        f"- Unfilled rows: `{report['summary']['unfilled_rows']}`",
        f"- Feasibility counts: `{report['summary']['feasibility_counts']}`",
        "",
        "## Interpretation",
        "",
        report["summary"]["interpretation"],
        "",
    ]
    (out_dir / "equal_information_freeze_feasibility.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--probe", type=Path, default=DEFAULT_PROBE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build_report(args)
    write_outputs(report, args.out_dir)
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
