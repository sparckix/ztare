#!/usr/bin/env python3
"""Sweep feasible Polymarket equal-information freeze horizons.

No DB mutation and no model calls.

The seven-day Polymarket packet failed mostly because markets were not open at
the target timestamp. This tool tests a small predeclared grid of shorter day
horizons on the same 24 post-cutoff rows so the next equal-information
experiment can be chosen from evidence rather than convenience.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

from cutoff_polymarket_post_price_probe import row_probe  # noqa: E402
from cutoff_polymarket_pre_cutoff_acquire import read_jsonl  # noqa: E402


PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_PANEL = (
    WORKSPACE
    / "cutoff_second_source_freeze_probe_deepseek_2026_06_03"
    / "cutoff_stage_b_minimum_panel_contracts.jsonl"
)
DEFAULT_OUT = WORKSPACE / "equal_information_horizon_sweep_2026_06_15"


def repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def post_cutoff_polymarket_rows(panel: Path) -> list[dict[str, Any]]:
    return [
        row
        for row in read_jsonl(panel)
        if row.get("source") == "polymarket" and row.get("cutoff_relation") == "post_cutoff"
    ]


def run_horizon(rows: list[dict[str, Any]], *, horizon_days: int, sleep_ms: int) -> dict[str, Any]:
    probed: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        if i and sleep_ms:
            time.sleep(sleep_ms / 1000)
        probed.append(row_probe(row, freeze_days_before_resolution=horizon_days))
    joined = [row for row in probed if row.get("join_status") == "joined"]
    ys = Counter(str(row.get("y_known")) for row in joined)
    return {
        "horizon_days_before_resolution": horizon_days,
        "rows_considered": len(rows),
        "joined_rows": len(joined),
        "join_rate": len(joined) / len(rows) if rows else None,
        "join_status_counts": dict(Counter(str(row.get("join_status")) for row in probed)),
        "history_status_counts": dict(
            Counter(str(row.get("history_status")) for row in probed if row.get("history_status"))
        ),
        "freeze_value_band_counts": dict(
            Counter(str(row.get("freeze_value_band")) for row in joined)
        ),
        "joined_outcome_counts": dict(sorted(ys.items())),
        "all_final_yes_match": all(row.get("gamma_final_yes_matches_y_known") is True for row in probed),
        "rows": probed,
    }


def choose_horizon(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [
        row
        for row in summaries
        if row["joined_rows"] == row["rows_considered"] and row["rows_considered"] > 0
    ]
    if eligible:
        # Prefer the longest horizon that fully covers the packet.
        best = max(eligible, key=lambda row: int(row["horizon_days_before_resolution"]))
        return {
            "decision": "fully_fillable_horizon_found",
            "recommended_horizon_days_before_resolution": best["horizon_days_before_resolution"],
            "reason": "longest predeclared day horizon with 24/24 joined rows",
        }
    best = max(summaries, key=lambda row: (int(row["joined_rows"]), int(row["horizon_days_before_resolution"]))) if summaries else None
    return {
        "decision": "no_fully_fillable_day_horizon_in_grid",
        "recommended_horizon_days_before_resolution": best["horizon_days_before_resolution"] if best else None,
        "reason": "best available horizon in the grid still leaves missing market-history rows",
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    rows = post_cutoff_polymarket_rows(args.panel)
    horizons = sorted(set(int(item) for item in args.horizons), reverse=True)
    reports = [
        run_horizon(rows, horizon_days=horizon, sleep_ms=args.sleep_ms)
        for horizon in horizons
    ]
    summaries = [
        {key: value for key, value in report.items() if key != "rows"}
        for report in reports
    ]
    return {
        "schema": "gp245-equal-information-horizon-sweep-v1",
        "panel": repo_rel(args.panel),
        "horizons_tested_days_before_resolution": horizons,
        "summary_by_horizon": summaries,
        "decision": choose_horizon(summaries),
        "reports": reports,
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "equal_information_horizon_sweep.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (out_dir / "equal_information_horizon_sweep_rows.jsonl").open("w", encoding="utf-8") as fh:
        for horizon_report in report["reports"]:
            horizon = horizon_report["horizon_days_before_resolution"]
            for row in horizon_report["rows"]:
                fh.write(json.dumps({"horizon_days_before_resolution": horizon, **row}, sort_keys=True) + "\n")
    lines = [
        "# Equal-Information Horizon Sweep",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Panel: `{report['panel']}`",
        f"- Horizons tested, days before resolution: `{report['horizons_tested_days_before_resolution']}`",
        f"- Decision: `{report['decision']['decision']}`",
        f"- Recommended horizon: `{report['decision']['recommended_horizon_days_before_resolution']}`",
        f"- Reason: {report['decision']['reason']}",
        "",
        "## Summary By Horizon",
        "",
    ]
    for row in report["summary_by_horizon"]:
        lines.extend(
            [
                f"### {row['horizon_days_before_resolution']} days",
                "",
                f"- Joined rows: `{row['joined_rows']} / {row['rows_considered']}`",
                f"- Join status counts: `{row['join_status_counts']}`",
                f"- Freeze value bands: `{row['freeze_value_band_counts']}`",
                f"- Joined outcome counts: `{row['joined_outcome_counts']}`",
                f"- Final YES matches y_known for all probed rows: `{row['all_final_yes_match']}`",
                "",
            ]
        )
    (out_dir / "equal_information_horizon_sweep.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--horizons",
        type=int,
        nargs="+",
        default=[7, 5, 3, 2, 1, 0],
        help="Pre-resolution day horizons to test.",
    )
    parser.add_argument("--sleep-ms", type=int, default=100)
    args = parser.parse_args()
    report = build_report(args)
    write_outputs(report, args.out_dir)
    print(json.dumps({"decision": report["decision"], "summary_by_horizon": report["summary_by_horizon"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
