#!/usr/bin/env python3
"""Summarize base-rate availability for the Polymarket second-source smokes."""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_PANEL = (
    WORKSPACE
    / "cutoff_second_source_freeze_probe_deepseek_2026_06_03"
    / "cutoff_stage_b_minimum_panel_contracts.jsonl"
)
DEFAULT_POST_PROBE = (
    WORKSPACE
    / "cutoff_second_source_polymarket_post_price_probe_2026_06_03"
    / "cutoff_second_source_polymarket_post_price_probe.json"
)
DEFAULT_OUT = WORKSPACE / "cutoff_second_source_polymarket_base_rate_availability_2026_06_03"


def repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def db_freeze_values(db: Path, contract_ids: list[str]) -> dict[str, float]:
    if not contract_ids:
        return {}
    con = sqlite3.connect(db)
    placeholders = ",".join("?" for _ in contract_ids)
    rows = con.execute(
        f"""
        SELECT contract_id, json_extract(raw_json, '$.freeze_datetime_value')
        FROM contracts
        WHERE contract_id IN ({placeholders})
        """,
        contract_ids,
    ).fetchall()
    con.close()
    out: dict[str, float] = {}
    for contract_id, value in rows:
        if value is None:
            continue
        try:
            p = float(value)
        except Exception:
            continue
        if 0.0 <= p <= 1.0:
            out[str(contract_id)] = p
    return out


def build(args: argparse.Namespace) -> dict[str, Any]:
    panel = [
        row for row in read_jsonl(args.panel)
        if row.get("source") == "polymarket"
    ]
    pre = [row for row in panel if row.get("cutoff_relation") == "pre_cutoff"]
    post = [row for row in panel if row.get("cutoff_relation") == "post_cutoff"]
    pre_values = db_freeze_values(args.db, [str(row["contract_id"]) for row in pre])
    post_values = db_freeze_values(args.db, [str(row["contract_id"]) for row in post])
    post_probe = read_json(args.post_probe)
    post_probe_joined = int(post_probe.get("joined_rows") or 0)
    post_probe_status = post_probe.get("join_status_counts") or {}
    verdict = (
        "base_rate_matched_control_executable"
        if len(pre_values) == len(pre) and (len(post_values) + post_probe_joined) == len(post) and pre and post
        else "base_rate_matched_control_not_executable"
    )
    return {
        "schema": "gp245-polymarket-second-source-base-rate-availability-v1",
        "panel": repo_rel(args.panel),
        "db": repo_rel(args.db),
        "post_probe": repo_rel(args.post_probe),
        "polymarket_rows": len(panel),
        "relation_counts": dict(Counter(str(row.get("cutoff_relation")) for row in panel)),
        "pre_cutoff_db_freeze_values": len(pre_values),
        "post_cutoff_db_freeze_values": len(post_values),
        "post_cutoff_probe_joined_rows": post_probe_joined,
        "post_cutoff_probe_join_status_counts": post_probe_status,
        "verdict": verdict,
        "interpretation": (
            "The Polymarket second-source smokes cannot yet be base-rate matched: "
            "the acquired pre-cutoff side has market prices, but the frozen post-cutoff side does not."
            if verdict != "base_rate_matched_control_executable"
            else "Both Polymarket pre- and post-cutoff sides have comparable market-price coverage."
        ),
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cutoff_second_source_polymarket_base_rate_availability.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Law 3 Polymarket Base-Rate Availability",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Verdict: `{report['verdict']}`",
        f"- Polymarket rows: `{report['polymarket_rows']}`",
        f"- Relation counts: `{report['relation_counts']}`",
        f"- Pre-cutoff DB freeze values: `{report['pre_cutoff_db_freeze_values']}`",
        f"- Post-cutoff DB freeze values: `{report['post_cutoff_db_freeze_values']}`",
        f"- Post-cutoff probe joined rows: `{report['post_cutoff_probe_joined_rows']}`",
        f"- Post-cutoff probe statuses: `{report['post_cutoff_probe_join_status_counts']}`",
        "",
        "## Interpretation",
        "",
        report["interpretation"],
        "",
    ]
    (out_dir / "cutoff_second_source_polymarket_base_rate_availability.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--post-probe", type=Path, default=DEFAULT_POST_PROBE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build(args)
    write_outputs(report, args.out_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
