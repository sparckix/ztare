#!/usr/bin/env python3
"""Materialize filled equal-information result rows from the post-cutoff probe.

No network, no DB mutation.

The post-cutoff Polymarket probe already verifies the Gamma market metadata,
YES token mapping, final outcome mapping, and nearest CLOB history point at or
before the frozen target. This tool converts only joined probe rows into the
JSONL result artifact accepted by equal_information_baseline_result_ingest.py.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_PROBE = (
    WORKSPACE
    / "cutoff_second_source_polymarket_post_price_probe_2026_06_03"
    / "cutoff_second_source_polymarket_post_price_probe.json"
)
DEFAULT_PACKET = (
    WORKSPACE
    / "equal_information_baseline_export_packet_2026_06_05"
    / "equal_information_baseline_export_packet.json"
)
DEFAULT_RESULTS = (
    WORKSPACE
    / "equal_information_baseline_export_packet_2026_06_05"
    / "equal_information_baseline_export_results.jsonl"
)


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


def build_results(probe: dict[str, Any], packet: dict[str, Any], *, probe_path: Path) -> list[dict[str, Any]]:
    requested = {
        str(row.get("contract_id")): row
        for row in packet.get("rows", [])
        if isinstance(row, dict) and row.get("contract_id")
    }
    rows: list[dict[str, Any]] = []
    for row in probe.get("rows", []):
        if not isinstance(row, dict) or row.get("join_status") != "joined":
            continue
        cid = str(row.get("contract_id") or "")
        request = requested.get(cid)
        if request is None:
            continue
        rows.append(
            {
                "schema": "gp245-equal-information-baseline-export-result-row-v1",
                "contract_id": cid,
                "market_asset_id_yes": row.get("yes_token_id"),
                "market_asset_id_no": row.get("no_token_id"),
                "yes_price_at_or_before_freeze": row.get("freeze_datetime_value"),
                "history_timestamp": row.get("freeze_history_timestamp"),
                "history_source": (
                    f"{repo_rel(probe_path)}::clob.prices-history"
                    f"::target_freeze_date_utc={request.get('target_freeze_date_utc')}"
                ),
                "outcomes": row.get("outcomes"),
                "market_slug": request.get("market_slug"),
                "market_url": request.get("market_url"),
            }
        )
    return rows


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", type=Path, default=DEFAULT_PROBE)
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    args = parser.parse_args()

    probe = read_json(args.probe)
    packet = read_json(args.packet)
    rows = build_results(probe, packet, probe_path=args.probe)
    write_jsonl(rows, args.results)
    print(
        json.dumps(
            {
                "schema": "gp245-equal-information-baseline-result-from-post-probe-v1",
                "probe": repo_rel(args.probe),
                "packet": repo_rel(args.packet),
                "results": repo_rel(args.results),
                "result_rows": len(rows),
                "requested_rows": len(packet.get("rows", [])),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
