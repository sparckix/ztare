#!/usr/bin/env python3
"""DB-backed report for the GP-245 inheritance/alignment theory.

This report intentionally uses only forecaster_calibration.db rows. It does not
read the original JSONL ledgers except through `pilot_calls.raw_json`.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
DB = REPO / "analytics/public/calibration/forecaster_calibration.db"

ALIGNMENT_ORDER = ["claude", "codex_55", "codex_54mini", "gemini", "deepseek"]
INVERTED_GAP_BIASES = {"N"}
EQUIV_BAND = 0.05


def load_raw(raw_json: str | None) -> dict[str, Any]:
    if not raw_json:
        return {}
    try:
        return json.loads(raw_json)
    except Exception:
        return {}


def observed_cell(mean_gap: float, predicted_cell: str | None, bias_id: str, g0: float | None) -> str:
    if g0 is not None:
        excess = mean_gap - g0
        if bias_id in INVERTED_GAP_BIASES:
            excess = -excess
        if abs(mean_gap - g0) <= EQUIV_BAND:
            return "ESCAPE"
        if excess > EQUIV_BAND:
            return predicted_cell if predicted_cell in {"INHERIT", "MIMIC"} else "BIAS_PRESENT"
        return "ESCAPE"
    if mean_gap <= EQUIV_BAND:
        return "ESCAPE"
    return predicted_cell if predicted_cell in {"INHERIT", "MIMIC"} else "BIAS_PRESENT"


def paired_gap_rows(cur: sqlite3.Cursor, pilot_id: str) -> list[dict[str, Any]]:
    rows = cur.execute(
        """
        SELECT family, p_success, condition, raw_json, parsed_json
        FROM pilot_calls
        WHERE pilot_id = ?
          AND schema_ok = 1
          AND p_success IS NOT NULL
        """,
        (pilot_id,),
    ).fetchall()
    grouped: dict[tuple[str, str, str, str], dict[str, float]] = defaultdict(dict)
    meta: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for family, p_success, condition, raw_json, parsed_json in rows:
        raw = load_raw(raw_json)
        parsed = load_raw(parsed_json)
        bias_id = raw.get("bias_id")
        event_id = raw.get("event_id")
        agent_id = raw.get("agent_id") or family
        framing = raw.get("framing") or condition
        if not (bias_id and event_id and family and framing in {"A", "B"}):
            continue
        key = (str(family), str(agent_id), str(bias_id), str(event_id))
        grouped[key][framing] = float(p_success)
        meta[key] = {
            "family": family,
            "agent_id": agent_id,
            "bias_id": bias_id,
            "bias_name": raw.get("bias_name"),
            "predicted_cell": raw.get("predicted_cell") or parsed.get("predicted_cell"),
            "g0": raw.get("g0") if raw.get("g0") is not None else parsed.get("g0"),
        }
    out = []
    for key, vals in grouped.items():
        if "A" not in vals or "B" not in vals:
            continue
        item = dict(meta[key])
        item["gap"] = abs(vals["A"] - vals["B"])
        out.append(item)
    return out


def report(db: Path) -> dict[str, Any]:
    con = sqlite3.connect(db)
    cur = con.cursor()
    pilots = ["f106_ood_inheritance_cheap_n15", "f107_corrected_ood_panel"]
    pilot_reports = {}
    for pilot_id in pilots:
        gaps = paired_gap_rows(cur, pilot_id)
        by_family_bias: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in gaps:
            by_family_bias[(row["family"], row["bias_id"])].append(row)
        family_rows = []
        for (family, bias_id), vals in sorted(by_family_bias.items()):
            mean_gap = statistics.mean(v["gap"] for v in vals)
            pred = vals[0].get("predicted_cell")
            g0 = vals[0].get("g0")
            cell = observed_cell(mean_gap, pred, bias_id, g0)
            family_rows.append(
                {
                    "family": family,
                    "bias_id": bias_id,
                    "bias_name": vals[0].get("bias_name"),
                    "predicted_cell": pred,
                    "observed_cell": cell,
                    "match": cell == pred,
                    "mean_gap": round(mean_gap, 4),
                    "g0": g0,
                    "n_pairs": len(vals),
                }
            )
        by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in family_rows:
            by_family[row["family"]].append(row)
        family_summary = {}
        for family, rows in by_family.items():
            evaluable = [r for r in rows if r["predicted_cell"]]
            family_summary[family] = {
                "biases": len(evaluable),
                "matches": sum(1 for r in evaluable if r["match"]),
                "median_gap": round(statistics.median(r["mean_gap"] for r in evaluable), 4)
                if evaluable else None,
                "inherit_mean_excess": round(
                    statistics.mean(
                        (r["mean_gap"] - (r["g0"] or 0.0))
                        for r in evaluable
                        if r["predicted_cell"] == "INHERIT"
                    ),
                    4,
                ) if any(r["predicted_cell"] == "INHERIT" for r in evaluable) else None,
            }
        pilot_reports[pilot_id] = {
            "paired_rows": len(gaps),
            "family_summary": family_summary,
            "rows": family_rows,
        }
    con.close()

    f107 = pilot_reports.get("f107_corrected_ood_panel", {})
    alignment_gradient = []
    for family in ALIGNMENT_ORDER:
        summary = (f107.get("family_summary") or {}).get(family)
        if summary:
            alignment_gradient.append(
                {
                    "family": family,
                    "matches": summary["matches"],
                    "biases": summary["biases"],
                    "inherit_mean_excess": summary["inherit_mean_excess"],
                }
            )
    return {
        "schema": "gp245-theory-alignment-report-v1",
        "pilots": pilot_reports,
        "alignment_gradient_order": ALIGNMENT_ORDER,
        "alignment_gradient": alignment_gradient,
        "interpretation": {
            "cell_prediction": "Evaluate matches per family; >=7/9 was the strong predictive threshold.",
            "alignment_axis": "Check whether inherited-bias excess increases as alignment weakens.",
            "caveat": "This report is descriptive; final verdict discipline remains in the preregistered research log.",
        },
    }


def write_outputs(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "theory_alignment_report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = ["# Theory Alignment Report", ""]
    lines.append("## Alignment Gradient")
    lines.append("")
    for row in result["alignment_gradient"]:
        lines.append(
            f"- `{row['family']}`: matches={row['matches']}/{row['biases']}, "
            f"inherit_mean_excess={row['inherit_mean_excess']}"
        )
    lines.append("")
    for pilot_id, pilot in result["pilots"].items():
        lines.append(f"## {pilot_id}")
        lines.append("")
        for family, summary in sorted(pilot["family_summary"].items()):
            lines.append(
                f"- `{family}`: matches={summary['matches']}/{summary['biases']}, "
                f"median_gap={summary['median_gap']}"
            )
        lines.append("")
    (out_dir / "theory_alignment_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DB)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()
    result = report(args.db)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.out_dir:
        write_outputs(result, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

