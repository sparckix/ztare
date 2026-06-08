#!/usr/bin/env python3
"""Score an isolated Law 3 cutoff receipt packet against a frozen panel."""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.ztare.experiment_stats import bootstrap_ci, paired_permutation_test


REPO = Path(__file__).resolve().parents[3]
WORKSPACE = REPO / "projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace"
DEFAULT_PANEL = WORKSPACE / "cutoff_second_source_freeze_probe_2026_06_03/cutoff_stage_b_minimum_panel_contracts.jsonl"
DEFAULT_CALLS = WORKSPACE / "cutoff_second_source_freeze_probe_2026_06_03/cutoff_second_source_polymarket_gemini_smoke_calls.jsonl"
DEFAULT_OUT_JSON = WORKSPACE / "cutoff_second_source_freeze_probe_2026_06_03/cutoff_second_source_polymarket_gemini_score.json"
DEFAULT_OUT_MD = WORKSPACE / "cutoff_second_source_freeze_probe_2026_06_03/cutoff_second_source_polymarket_gemini_score.md"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def mean_ci(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "mean": None, "ci_lo": None, "ci_hi": None}
    point, lo, hi = bootstrap_ci(values, seed=42)
    return {
        "n": len(values),
        "mean": round(point, 6) if point is not None else None,
        "ci_lo": round(lo, 6) if lo is not None else None,
        "ci_hi": round(hi, 6) if hi is not None else None,
    }


def brier(p: float, y: int) -> float:
    return (p - y) ** 2


def path_label(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO))
    except ValueError:
        return str(path)


def build_report(panel_path: Path, calls_path: Path) -> dict[str, Any]:
    panel_path = panel_path.resolve()
    calls_path = calls_path.resolve()
    panel = read_jsonl(panel_path)
    meta = {str(row["contract_id"]): row for row in panel}
    observations: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for row in read_jsonl(calls_path):
        cid = str(row.get("contract_id"))
        m = meta.get(cid)
        p = row.get("p_success")
        if not row.get("schema_ok"):
            exclusions.append({"contract_id": cid, "reason": "schema_not_ok"})
            continue
        if m is None:
            exclusions.append({"contract_id": cid, "reason": "missing_panel_meta"})
            continue
        if isinstance(p, bool) or not isinstance(p, (int, float)):
            exclusions.append({"contract_id": cid, "reason": "missing_probability"})
            continue
        y = int(m["y_known"])
        observations.append(
            {
                "contract_id": cid,
                "source": m.get("source"),
                "cutoff_relation": m.get("cutoff_relation"),
                "stratum_key": m.get("stratum_key"),
                "family": row.get("family"),
                "p_success": float(p),
                "y_known": y,
                "brier": brier(float(p), y),
            }
        )

    by_relation: dict[str, list[float]] = defaultdict(list)
    for row in observations:
        by_relation[str(row["cutoff_relation"])].append(float(row["brier"]))
    pre = by_relation.get("pre_cutoff", [])
    post = by_relation.get("post_cutoff", [])

    cells: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in observations:
        cells[(str(row["stratum_key"]), str(row["cutoff_relation"]))].append(float(row["brier"]))
    paired_pre: list[float] = []
    paired_post: list[float] = []
    for stratum in sorted({key[0] for key in cells}):
        a = cells.get((stratum, "pre_cutoff"), [])
        b = cells.get((stratum, "post_cutoff"), [])
        if a and b:
            paired_pre.append(statistics.mean(a))
            paired_post.append(statistics.mean(b))

    post_minus_pre = statistics.mean(post) - statistics.mean(pre) if pre and post else None
    paired_delta = statistics.mean(paired_post) - statistics.mean(paired_pre) if paired_pre and paired_post else None
    report = {
        "schema": "gp245-law3-second-source-receipt-score-v1",
        "panel": path_label(panel_path),
        "calls": path_label(calls_path),
        "valid_rows": len(observations),
        "excluded_rows": len(exclusions),
        "families": sorted({str(row["family"]) for row in observations}),
        "exclusion_reasons": {
            reason: sum(1 for row in exclusions if row["reason"] == reason)
            for reason in sorted({row["reason"] for row in exclusions})
        },
        "aggregate_delta": {
            "pre": mean_ci(pre),
            "post": mean_ci(post),
            "post_minus_pre": round(post_minus_pre, 6) if post_minus_pre is not None else None,
        },
        "paired_stratum_delta": {
            "paired_cells": len(paired_pre),
            "post_minus_pre": round(paired_delta, 6) if paired_delta is not None else None,
            "paired_permutation": paired_permutation_test(paired_post, paired_pre, n_perm=5000, seed=42)
            if paired_pre and paired_post
            else None,
        },
        "by_relation": {key: mean_ci(values) for key, values in sorted(by_relation.items())},
        "verdict": {
            "promote_source_general_law3": False,
            "interpretation": (
                "This is a single-family Polymarket-only smoke. It can falsify or "
                "support the direction of the Law 3 mechanism on the newly acquired "
                "second-source slice, but it is not a paper-grade source-general replication."
            ),
        },
    }
    return report


def write_md(report: dict[str, Any], path: Path) -> None:
    agg = report["aggregate_delta"]
    paired = report["paired_stratum_delta"]
    family_label = "+".join(report.get("families") or ["unknown"])
    lines = [
        f"# Law 3 Polymarket second-source {family_label} smoke score",
        "",
        f"- Valid rows: `{report['valid_rows']}`",
        f"- Excluded rows: `{report['excluded_rows']}`",
        f"- Pre mean Brier: `{agg['pre']['mean']}` over `{agg['pre']['n']}` rows",
        f"- Post mean Brier: `{agg['post']['mean']}` over `{agg['post']['n']}` rows",
        f"- Post-minus-pre Brier: `{agg['post_minus_pre']}`",
        f"- Paired stratum cells: `{paired['paired_cells']}`",
        f"- Paired post-minus-pre: `{paired['post_minus_pre']}`",
        f"- Paired permutation: `{paired['paired_permutation']}`",
        "",
        "Interpretation: "
        + report["verdict"]["interpretation"],
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--calls", type=Path, default=DEFAULT_CALLS)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()
    report = build_report(args.panel, args.calls)
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_md(report, args.out_md)
    print(json.dumps(report["aggregate_delta"], indent=2, sort_keys=True))
    print(json.dumps(report["paired_stratum_delta"], indent=2, sort_keys=True))
    print(f"wrote {args.out_json}")
    print(f"wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
