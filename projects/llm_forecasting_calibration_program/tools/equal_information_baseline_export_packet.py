#!/usr/bin/env python3
"""Emit an export/acquisition packet for missing equal-information market bars.

No network, no model calls, no DB mutation.

The local public Polymarket route currently resets before we can recover
post-cutoff market asset ids and CLOB history. This packet makes the remaining
data request exact enough for an alternate export/provider route: every row has
the market slug, target freeze timestamp, required market-price fields, and the
validation rule that would make the row eligible.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import timedelta
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_POST_PROBE = (
    WORKSPACE
    / "cutoff_second_source_polymarket_post_price_probe_2026_06_03"
    / "cutoff_second_source_polymarket_post_price_probe.json"
)
DEFAULT_OUT = WORKSPACE / "equal_information_baseline_export_packet_2026_06_05"


def repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def parse_date(value: Any) -> str | None:
    text = str(value or "").strip()
    if len(text) >= 10:
        return text[:10]
    return None


def target_freeze_date(resolve_date: Any, freeze_days_before_resolution: int) -> str | None:
    date_text = parse_date(resolve_date)
    if not date_text:
        return None
    from datetime import date

    try:
        d = date.fromisoformat(date_text)
    except ValueError:
        return None
    return (d - timedelta(days=freeze_days_before_resolution)).isoformat()


def build_row(row: dict[str, Any], *, freeze_days_before_resolution: int) -> dict[str, Any]:
    freeze_date = target_freeze_date(row.get("resolve_date"), freeze_days_before_resolution)
    return {
        "schema": "gp245-equal-information-baseline-export-row-v1",
        "contract_id": row.get("contract_id"),
        "source": row.get("source"),
        "question": row.get("question"),
        "market_slug": row.get("slug"),
        "market_url": row.get("resolution_source_url"),
        "resolve_date": row.get("resolve_date"),
        "target_freeze_date_utc": freeze_date,
        "target_freeze_timestamp_rule": (
            "Use the nearest available YES price at or before target_freeze_date_utc "
            f"00:00:00 UTC, matching the existing {freeze_days_before_resolution}-day "
            "pre-resolution freeze rule."
        ),
        "y_known": row.get("y_known"),
        "cutoff_relation": row.get("cutoff_relation"),
        "stratum_key": row.get("stratum_key"),
        "topic": row.get("topic"),
        "question_length_bucket": row.get("question_length_bucket"),
        "local_probe_join_status": row.get("join_status"),
        "required_fields": {
            "market_asset_id_yes": "Polymarket CLOB YES token / market asset id",
            "market_asset_id_no": "Polymarket CLOB NO token / market asset id when available",
            "yes_price_at_or_before_freeze": "float in [0,1]",
            "history_timestamp": "Unix timestamp or ISO timestamp of selected price",
            "history_source": "API/export/provider/source filename",
            "outcomes": "ordered outcome labels used to verify YES token",
        },
        "eligibility_rule": (
            "Eligible only if yes_price_at_or_before_freeze is in [0,1], timestamp "
            "is <= target freeze timestamp, and the YES token/outcome mapping is auditable."
        ),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    probe = read_json(args.post_probe)
    freeze_days = int(probe.get("freeze_days_before_resolution") or args.freeze_days_before_resolution)
    rows = [
        build_row(row, freeze_days_before_resolution=freeze_days)
        for row in probe.get("rows", [])
        if row.get("source") == "polymarket" and row.get("cutoff_relation") == "post_cutoff"
    ]
    missing = [row for row in rows if row.get("local_probe_join_status") != "joined"]
    return {
        "schema": "gp245-equal-information-baseline-export-packet-v1",
        "post_probe": repo_rel(args.post_probe),
        "freeze_days_before_resolution": freeze_days,
        "rows": rows,
        "summary": {
            "rows": len(rows),
            "missing_rows": len(missing),
            "local_probe_status_counts": dict(
                Counter(str(row.get("local_probe_join_status")) for row in rows)
            ),
            "required_result_artifact": "JSONL with one gp245-equal-information-baseline-export-result-row-v1 per requested contract",
            "acceptance_gate": (
                "At least the 24 post-cutoff Polymarket rows need eligible prices before "
                "the Polymarket base-rate matched control is executable."
            ),
        },
        "alternate_route_notes": [
            "Official route: Gamma market metadata to recover CLOB token ids, then CLOB prices-history or batch-prices-history.",
            "If Gamma resets locally, use an export/provider route that returns token ids plus historical YES prices.",
            "Current/final page odds are not eligible; the row needs a pre-resolution freeze timestamp at or before target.",
        ],
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "equal_information_baseline_export_packet.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (out_dir / "equal_information_baseline_export_request_rows.jsonl").open("w", encoding="utf-8") as fh:
        for row in report["rows"]:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    lines = [
        "# Equal-Information Baseline Export Packet",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Post probe: `{report['post_probe']}`",
        f"- Rows: `{report['summary']['rows']}`",
        f"- Missing rows: `{report['summary']['missing_rows']}`",
        f"- Local probe statuses: `{report['summary']['local_probe_status_counts']}`",
        f"- Acceptance gate: {report['summary']['acceptance_gate']}",
        "",
        "## Alternate Route Notes",
        "",
        *[f"- {item}" for item in report["alternate_route_notes"]],
        "",
        "## Required Result Fields",
        "",
        "- `contract_id`",
        "- `market_asset_id_yes`",
        "- `yes_price_at_or_before_freeze`",
        "- `history_timestamp`",
        "- `history_source`",
        "- `outcomes`",
        "",
    ]
    (out_dir / "equal_information_baseline_export_packet.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--post-probe", type=Path, default=DEFAULT_POST_PROBE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--freeze-days-before-resolution", type=int, default=7)
    args = parser.parse_args()
    report = build_report(args)
    write_outputs(report, args.out_dir)
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
