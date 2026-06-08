#!/usr/bin/env python3
"""DB-only report for the F105 effort-calibration sibling lane.

This consumes canonical `pilot_calls` rows produced by
`ingest_nonstandard_ledgers.py` for v5/v6 hard-prompt-break effort ledgers.
It does not make model calls and does not mutate the DB.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.ztare.experiment_stats import bootstrap_ci, paired_permutation_test


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = REPO / "projects/llm_forecasting_calibration_program/llm_effort_estimation/workspace"


def load_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        data = json.loads(text)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        x = float(value)
    except Exception:
        return None
    return x if math.isfinite(x) else None


def rounded(value: float | None, digits: int = 6) -> float | None:
    return round(value, digits) if value is not None and math.isfinite(value) else None


def mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def load_rows(db: Path) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows: list[dict[str, Any]] = []
    for row in con.execute(
        """
        SELECT pilot_id, contract_id, agent_id, family, condition, primitive,
               phase, schema_ok, parsed_json, fired_at
        FROM pilot_calls
        WHERE primitive_base = 'f105'
          AND primitive LIKE 'f105_%effort_estimation'
        ORDER BY pilot_id, family, contract_id
        """
    ):
        parsed = load_json(row["parsed_json"])
        actual = as_float(parsed.get("actual"))
        est = as_float(parsed.get("estimate_mid"))
        err = as_float(parsed.get("log_abs_ratio"))
        if actual is None or est is None or err is None:
            continue
        rows.append(
            {
                "pilot_id": row["pilot_id"],
                "contract_id": row["contract_id"],
                "agent_id": row["agent_id"],
                "family": row["family"],
                "condition": row["condition"],
                "primitive": row["primitive"],
                "metric": parsed.get("actual_metric") or row["primitive"],
                "unit": parsed.get("unit"),
                "task_id": parsed.get("task_id"),
                "split": parsed.get("split"),
                "arm": parsed.get("arm"),
                "estimate_mid": est,
                "actual": actual,
                "ratio": est / actual if actual else None,
                "log_abs_ratio": err,
                "passed": parsed.get("passed"),
                "schema_ok": bool(row["schema_ok"]),
            }
        )
    con.close()
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    errs = [float(r["log_abs_ratio"]) for r in rows]
    ratios = [float(r["ratio"]) for r in rows if r.get("ratio") is not None]
    point, lo, hi = bootstrap_ci(errs, seed=42)
    return {
        "n": len(rows),
        "schema_ok": sum(1 for r in rows if r["schema_ok"]),
        "mean_log_abs_ratio": rounded(mean(errs)),
        "ci95_mean_log_abs_ratio": [rounded(lo), rounded(hi)],
        "median_estimate_to_actual_ratio": rounded(statistics.median(ratios) if ratios else None),
        "mean_estimate": rounded(mean([float(r["estimate_mid"]) for r in rows])),
        "mean_actual": rounded(mean([float(r["actual"]) for r in rows])),
    }


def arm_contrasts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_cell: dict[tuple[str, str, str, str], dict[str, float]] = defaultdict(dict)
    for row in rows:
        if row["split"] != "eval":
            continue
        key = (row["pilot_id"], row["family"], row["metric"], row["task_id"])
        by_cell[key][str(row["arm"])] = float(row["log_abs_ratio"])
    out: list[dict[str, Any]] = []
    by_group: dict[tuple[str, str, str, str], list[tuple[float, float]]] = defaultdict(list)
    for (pilot_id, family, metric, _task_id), arms in by_cell.items():
        if "A" not in arms:
            continue
        for arm, err in arms.items():
            if arm == "A":
                continue
            by_group[(pilot_id, family, metric, arm)].append((err, arms["A"]))
    for (pilot_id, family, metric, arm), pairs in sorted(by_group.items()):
        arm_err = [p[0] for p in pairs]
        base_err = [p[1] for p in pairs]
        deltas = [a - b for a, b in pairs]
        perm = paired_permutation_test(arm_err, base_err, n_perm=5000, seed=42)
        out.append(
            {
                "pilot_id": pilot_id,
                "family": family,
                "metric": metric,
                "arm": arm,
                "n_pairs": len(pairs),
                "mean_arm_error": rounded(mean(arm_err)),
                "mean_A_error": rounded(mean(base_err)),
                "delta_vs_A": rounded(mean(deltas)),
                "paired_permutation": perm,
                "direction": "improves_vs_A" if mean(deltas) is not None and mean(deltas) < 0 else "worse_or_equal_vs_A",
            }
        )
    return out


def build_report(db: Path) -> dict[str, Any]:
    rows = load_rows(db)
    by_pilot: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_family_metric: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    by_arm: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_pilot[row["pilot_id"]].append(row)
        by_family_metric[(row["family"], row["metric"])].append(row)
        by_arm[(row["pilot_id"], row["family"], row["metric"], row["arm"])].append(row)
    contrasts = arm_contrasts(rows)
    support_rows = [
        row for row in contrasts
        if row["arm"] == "E" and row["delta_vs_A"] is not None and row["delta_vs_A"] < 0
    ]
    harm_rows = [
        row for row in contrasts
        if row["arm"] == "E" and row["delta_vs_A"] is not None and row["delta_vs_A"] > 0
    ]
    return {
        "schema": "f105-effort-rescue-report-v1",
        "db": str(db),
        "rows": len(rows),
        "pilot_summary": {k: summarize(v) for k, v in sorted(by_pilot.items())},
        "family_metric_summary": {
            f"{family}/{metric}": summarize(v)
            for (family, metric), v in sorted(by_family_metric.items())
        },
        "arm_summary": {
            f"{pilot}/{family}/{metric}/arm_{arm}": summarize(v)
            for (pilot, family, metric, arm), v in sorted(by_arm.items())
        },
        "arm_contrasts_vs_A": contrasts,
        "sibling_paper_status": {
            "db_canonicalized": len(rows) > 0,
            "token_length_families": sorted({r["family"] for r in rows if r["metric"] == "actual_tokens"}),
            "step_count_families": sorted({r["family"] for r in rows if r["metric"] == "actual_steps"}),
            "E_improves_family_metric_cells": len(support_rows),
            "E_harms_family_metric_cells": len(harm_rows),
            "verdict": "rescued_as_continuous_sibling_evidence_not_gp245_law",
        },
        "guardrail": (
            "F105 remains a sibling lane. These rows score continuous effort estimates; "
            "they do not supply binary Brier evidence for the three-law GP-245 paper."
        ),
    }


def write_outputs(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "f105_effort_rescue_db_report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = ["# F105 Effort Rescue DB Report", ""]
    lines.append(f"- Rows: {result['rows']}")
    lines.append(f"- Verdict: `{result['sibling_paper_status']['verdict']}`")
    lines.append(f"- Token-length families: {result['sibling_paper_status']['token_length_families']}")
    lines.append(f"- Step-count families: {result['sibling_paper_status']['step_count_families']}")
    lines.append("")
    lines.append("## Pilot Summary")
    lines.append("")
    for pilot, row in result["pilot_summary"].items():
        lines.append(
            f"- `{pilot}`: n={row['n']}, mean_log_abs={row['mean_log_abs_ratio']}, "
            f"median_ratio={row['median_estimate_to_actual_ratio']}"
        )
    lines.append("")
    lines.append("## Arm E vs A")
    lines.append("")
    e_rows = [r for r in result["arm_contrasts_vs_A"] if r["arm"] == "E"]
    if not e_rows:
        lines.append("- No Arm E contrasts.")
    for row in e_rows:
        lines.append(
            f"- `{row['pilot_id']}` / `{row['family']}` / `{row['metric']}`: "
            f"n={row['n_pairs']}, delta_vs_A={row['delta_vs_A']}, "
            f"p={row['paired_permutation'].get('p_value')}, {row['direction']}"
        )
    lines.append("")
    lines.append("## Guardrail")
    lines.append("")
    lines.append(result["guardrail"])
    lines.append("")
    (out_dir / "f105_effort_rescue_db_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = build_report(args.db)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.out_dir:
        write_outputs(result, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
