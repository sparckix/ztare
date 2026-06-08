#!/usr/bin/env python3
"""Score the GP-245 Law 3 cutoff Stage-B panel from the canonical DB."""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.ztare.experiment_stats import bootstrap_ci, paired_permutation_test


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
WORKSPACE = REPO / "projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace"
DEFAULT_PANEL = WORKSPACE / "cutoff_stage_b_minimum_panel_contracts.jsonl"
DEFAULT_FREEZE = WORKSPACE / "cutoff_stage_b_freeze_report.json"
DEFAULT_OUT = WORKSPACE
PILOT_ID = "cutoff_stage_b_panel_v1"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def parse_json(text: str | None) -> dict[str, Any]:
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
        out = float(value)
    except Exception:
        return None
    return out


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


def load_calls(db: Path, contract_ids: set[str]) -> list[dict[str, Any]]:
    if not contract_ids:
        return []
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in contract_ids)
    rows = []
    for row in con.execute(
        f"""
        SELECT pc.call_id, pc.pilot_id, pc.contract_id, pc.family, pc.condition,
               pc.primitive, pc.p_success, pc.brier, pc.schema_ok, pc.parsed_json,
               pc.fired_at, c.y_known
        FROM pilot_calls pc
        JOIN contracts c ON c.contract_id = pc.contract_id
        WHERE pc.pilot_id = ?
          AND pc.contract_id IN ({placeholders})
        """,
        (PILOT_ID, *sorted(contract_ids)),
    ):
        item = dict(row)
        item["parsed"] = parse_json(item.get("parsed_json"))
        rows.append(item)
    con.close()
    return rows


def summarize_by_family_relation(calls: list[dict[str, Any]], panel_meta: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[float]] = defaultdict(list)
    for call in calls:
        if not call.get("schema_ok") or call.get("brier") is None:
            continue
        meta = panel_meta.get(str(call["contract_id"]))
        if not meta:
            continue
        groups[(str(call["family"]), str(meta["cutoff_relation"]))].append(float(call["brier"]))
    out: list[dict[str, Any]] = []
    for (family, relation), values in sorted(groups.items()):
        row = mean_ci(values)
        row.update({"family": family, "cutoff_relation": relation})
        out.append(row)
    return out


def aggregate_delta(calls: list[dict[str, Any]], panel_meta: dict[str, dict[str, Any]]) -> dict[str, Any]:
    by_relation: dict[str, list[float]] = defaultdict(list)
    for call in calls:
        if not call.get("schema_ok") or call.get("brier") is None:
            continue
        meta = panel_meta.get(str(call["contract_id"]))
        if meta:
            by_relation[str(meta["cutoff_relation"])].append(float(call["brier"]))
    pre = by_relation.get("pre_cutoff", [])
    post = by_relation.get("post_cutoff", [])
    result = {
        "pre": mean_ci(pre),
        "post": mean_ci(post),
        "post_minus_pre": None,
    }
    if pre and post:
        result["post_minus_pre"] = round(statistics.mean(post) - statistics.mean(pre), 6)
    return result


def paired_stratum_delta(calls: list[dict[str, Any]], panel_meta: dict[str, dict[str, Any]]) -> dict[str, Any]:
    cells: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for call in calls:
        if not call.get("schema_ok") or call.get("brier") is None:
            continue
        meta = panel_meta.get(str(call["contract_id"]))
        if not meta:
            continue
        key = (str(call["family"]), str(meta["stratum_key"]), str(meta["cutoff_relation"]))
        cells[key].append(float(call["brier"]))
    pre_vals: list[float] = []
    post_vals: list[float] = []
    families = sorted({key[0] for key in cells})
    strata = sorted({key[1] for key in cells})
    for family in families:
        for stratum in strata:
            pre = cells.get((family, stratum, "pre_cutoff"), [])
            post = cells.get((family, stratum, "post_cutoff"), [])
            if pre and post:
                pre_vals.append(statistics.mean(pre))
                post_vals.append(statistics.mean(post))
    return {
        "paired_cells": len(pre_vals),
        "post_minus_pre": (
            round(statistics.mean(post_vals) - statistics.mean(pre_vals), 6)
            if pre_vals and post_vals
            else None
        ),
        "paired_permutation": paired_permutation_test(post_vals, pre_vals, n_perm=5000, seed=42)
        if pre_vals and post_vals
        else None,
    }


def recognition_sensitivity(calls: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for call in calls:
        if not call.get("schema_ok") or call.get("brier") is None:
            continue
        recog = as_float((call.get("parsed") or {}).get("recognition_self_report"))
        if recog is None:
            continue
        rows.append((recog, float(call["brier"])))
    if not rows:
        return {"rows_with_recognition": 0}
    low = [b for r, b in rows if r < 0.5]
    high = [b for r, b in rows if r >= 0.5]
    return {
        "rows_with_recognition": len(rows),
        "low_recognition_brier": mean_ci(low),
        "high_recognition_brier": mean_ci(high),
        "high_minus_low": (
            round(statistics.mean(high) - statistics.mean(low), 6)
            if low and high
            else None
        ),
    }


def verdict(report: dict[str, Any]) -> str:
    if report["call_coverage"]["schema_ok_calls"] == 0:
        return "not_run"
    coverage = report["call_coverage"]
    if coverage["schema_ok_calls"] < coverage["expected_calls"]:
        return "partial_calls_not_paper_ready"
    delta = report["aggregate_delta"].get("post_minus_pre")
    paired = report["paired_stratum_delta"].get("paired_permutation") or {}
    p_value = paired.get("p_value")
    if delta is None:
        return "scoring_incomplete"
    if delta > 0 and p_value is not None and p_value <= 0.05:
        return "promote_cutoff_validity_law_with_base_rate_limitation"
    if abs(delta) < 0.01:
        return "kill_or_scope_cutoff_validity_no_material_delta"
    return "inconclusive_needs_review"


def build_report(db: Path, panel_path: Path, freeze_path: Path) -> dict[str, Any]:
    panel = load_jsonl(panel_path)
    freeze = load_json(freeze_path)
    panel_meta = {str(row["contract_id"]): row for row in panel}
    calls = load_calls(db, set(panel_meta))
    schema_ok = [row for row in calls if row.get("schema_ok")]
    expected_calls = int((freeze.get("dispatch_slate") or {}).get("rows") or len(panel) * 3)
    call_counts = Counter(str(row.get("family")) for row in schema_ok)
    relation_counts = Counter(
        str(panel_meta[str(row["contract_id"])]["cutoff_relation"])
        for row in schema_ok
        if str(row.get("contract_id")) in panel_meta
    )
    report = {
        "schema": "gp245-cutoff-stage-b-score-v1",
        "db": str(db),
        "pilot_id": PILOT_ID,
        "panel_contracts": len(panel),
        "freeze_report": str(freeze_path),
        "panel_path": str(panel_path),
        "call_coverage": {
            "expected_calls": expected_calls,
            "calls_in_db": len(calls),
            "schema_ok_calls": len(schema_ok),
            "families": dict(call_counts),
            "relations": dict(relation_counts),
        },
        "matching_limitations": freeze.get("matching_limitations") or {},
        "family_relation_brier": summarize_by_family_relation(calls, panel_meta),
        "aggregate_delta": aggregate_delta(calls, panel_meta),
        "paired_stratum_delta": paired_stratum_delta(calls, panel_meta),
        "recognition_sensitivity": recognition_sensitivity(calls),
    }
    report["verdict"] = verdict(report)
    report["interpretation"] = (
        "Positive post_minus_pre means pre-cutoff rows had lower Brier. "
        "The current frozen panel is not base-rate matched unless matching_limitations says otherwise."
    )
    return report


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cutoff_stage_b_score_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Cutoff Stage-B Score Report",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Verdict: `{report['verdict']}`",
        f"- Pilot ID: `{report['pilot_id']}`",
        f"- Panel contracts: {report['panel_contracts']}",
        f"- Call coverage: `{report['call_coverage']}`",
        "",
        "## Aggregate Delta",
        "",
        f"- Post-minus-pre Brier: `{report['aggregate_delta'].get('post_minus_pre')}`",
        f"- Paired stratum delta: `{report['paired_stratum_delta']}`",
        "",
        "## Family / Relation Brier",
        "",
    ]
    for row in report["family_relation_brier"]:
        lines.append(
            f"- `{row['family']}` / `{row['cutoff_relation']}`: "
            f"n={row['n']}, mean={row['mean']}, ci=[{row['ci_lo']}, {row['ci_hi']}]"
        )
    lines.extend(
        [
            "",
            "## Limitation",
            "",
            (report.get("matching_limitations") or {}).get("interpretation", "No limitation text found."),
            "",
            report["interpretation"],
            "",
        ]
    )
    (out_dir / "cutoff_stage_b_score_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--freeze-report", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build_report(args.db, args.panel, args.freeze_report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.out_dir:
        write_outputs(report, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
