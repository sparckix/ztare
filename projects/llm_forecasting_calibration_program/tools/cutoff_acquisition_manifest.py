#!/usr/bin/env python3
"""Build the Law 3 pre-cutoff acquisition manifest.

The Stage-B balance report says whether the current strict matched corpus is
ready. This script turns the deficit into an explicit acquisition plan: which
source/topic/length strata need new pre-cutoff public contracts, how many are
needed for the minimum gate, and how many would be needed to fully balance the
currently available post-cutoff side.

No model calls. No DB writes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM_ROOT = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_STAGE_B = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_stage_b_balance_report.json"
DEFAULT_OUT = PROGRAM_ROOT / "cutoff_validity_v1/workspace"
MIN_PRE_CONTRACTS = 40


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def allocate_minimum_need(strata: list[dict[str, Any]], needed: int) -> list[dict[str, Any]]:
    """Allocate `needed` rows across strata proportional to their post-side gap."""
    if needed <= 0:
        return [{**row, "minimum_acquisition_n": 0} for row in strata]
    rows = []
    total_gap = 0
    for row in strata:
        gap = max(int(row.get("post_n") or 0) - int(row.get("pre_n") or 0), 0)
        rows.append({**row, "_gap": gap})
        total_gap += gap
    if total_gap <= 0:
        return [{**row, "minimum_acquisition_n": 0} for row in strata]

    allocated = 0
    for row in rows:
        raw = needed * row["_gap"] / total_gap
        row["_raw_minimum"] = raw
        row["minimum_acquisition_n"] = min(row["_gap"], int(raw))
        allocated += row["minimum_acquisition_n"]

    remainder = needed - allocated
    for row in sorted(rows, key=lambda r: (r["_raw_minimum"] - int(r["_raw_minimum"]), r["_gap"]), reverse=True):
        if remainder <= 0:
            break
        if row["minimum_acquisition_n"] >= row["_gap"]:
            continue
        row["minimum_acquisition_n"] += 1
        remainder -= 1

    for row in rows:
        row.pop("_raw_minimum", None)
        row.pop("_gap", None)
    return rows


def acquisition_rows(
    allocated: list[dict[str, Any]],
    *,
    panel_cutoff_date: str,
    mode: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in allocated:
        n = int(row["minimum_acquisition_n"] if mode == "minimum" else row["full_balance_acquisition_n"])
        for idx in range(1, n + 1):
            source = row["source"]
            topic = row["topic"]
            length = row["question_length_bucket"]
            out.append(
                {
                    "acquisition_id": f"law3_{mode}_{source}_{topic}_{length}_{idx:03d}",
                    "law": "cutoff_validity",
                    "mode": mode,
                    "target_source": source,
                    "target_topic": topic,
                    "target_question_length_bucket": length,
                    "required_cutoff_relation": "pre_cutoff",
                    "panel_cutoff_date": panel_cutoff_date,
                    "required_resolution_date_rule": f"resolve_date <= {panel_cutoff_date}",
                    "required_fields": [
                        "contract_id",
                        "question",
                        "source",
                        "source_corpus",
                        "y_known",
                        "strict_resolve_date",
                        "computed_cutoff_relation",
                    ],
                    "exclusion_rules": [
                        "no latest-observed-data dates as resolve dates",
                        "no unresolved rows",
                        "no non-public apparatus effort rows",
                        "no duplicate event core already present in matched strict corpus",
                    ],
                    "target_existing_post_n": int(row.get("post_n") or 0),
                    "target_existing_pre_n": int(row.get("pre_n") or 0),
                }
            )
    return out


def build_report(stage_b_path: Path) -> dict[str, Any]:
    stage_b = read_json(stage_b_path)
    gate = stage_b.get("stage_b_gate") or {}
    matched = (stage_b.get("matched_strict_contracts") or {}).get("matched_strata") or []
    panel_cutoff_date = str(stage_b.get("panel_cutoff_date") or "2025-10-01")
    current_pre = int(gate.get("matched_pre_contracts") or 0)
    minimum_needed = max(MIN_PRE_CONTRACTS - current_pre, 0)

    base_rows: list[dict[str, Any]] = []
    for row in matched:
        pre = int(row.get("pre_n") or 0)
        post = int(row.get("post_n") or 0)
        base_rows.append(
            {
                "source": row.get("source"),
                "topic": row.get("topic"),
                "question_length_bucket": row.get("question_length_bucket"),
                "pre_n": pre,
                "post_n": post,
                "full_balance_acquisition_n": max(post - pre, 0),
            }
        )
    allocated = allocate_minimum_need(base_rows, minimum_needed)
    minimum_rows = acquisition_rows(allocated, panel_cutoff_date=panel_cutoff_date, mode="minimum")
    full_rows = acquisition_rows(allocated, panel_cutoff_date=panel_cutoff_date, mode="full_balance")
    try:
        stage_b_ref = str(stage_b_path.resolve().relative_to(REPO))
    except ValueError:
        stage_b_ref = str(stage_b_path)
    return {
        "schema": "gp245-cutoff-acquisition-manifest-v1",
        "stage_b_report": stage_b_ref,
        "panel_cutoff_date": panel_cutoff_date,
        "current_matched_pre_contracts": current_pre,
        "minimum_pre_contracts": MIN_PRE_CONTRACTS,
        "minimum_acquisition_total": len(minimum_rows),
        "full_balance_acquisition_total": len(full_rows),
        "allocation": allocated,
        "minimum_manifest": minimum_rows,
        "full_balance_manifest": full_rows,
        "verdict": "acquisition_needed" if minimum_rows else "no_acquisition_needed",
        "interpretation": (
            "The minimum manifest is the smallest no-call corpus-construction "
            "target that would let the strict matched pre-cutoff side reach "
            "Stage B. The full-balance manifest is larger and would match the "
            "currently available post-cutoff side inside each matched stratum."
        ),
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cutoff_acquisition_manifest_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (out_dir / "cutoff_pre_cutoff_acquisition_manifest.jsonl").open("w", encoding="utf-8") as f:
        for row in report["minimum_manifest"]:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    with (out_dir / "cutoff_pre_cutoff_full_balance_manifest.jsonl").open("w", encoding="utf-8") as f:
        for row in report["full_balance_manifest"]:
            f.write(json.dumps(row, sort_keys=True) + "\n")

    lines = [
        "# Cutoff Acquisition Manifest Report",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Verdict: `{report['verdict']}`",
        f"- Panel cutoff date: `{report['panel_cutoff_date']}`",
        f"- Current matched pre-cutoff contracts: {report['current_matched_pre_contracts']}",
        f"- Minimum acquisition rows: {report['minimum_acquisition_total']}",
        f"- Full-balance acquisition rows: {report['full_balance_acquisition_total']}",
        "",
        "## Allocation",
        "",
    ]
    for row in report["allocation"]:
        lines.append(
            f"- `{row['source']}` / `{row['topic']}` / `{row['question_length_bucket']}`: "
            f"pre={row['pre_n']}, post={row['post_n']}, "
            f"minimum_add={row['minimum_acquisition_n']}, "
            f"full_balance_add={row['full_balance_acquisition_n']}"
        )
    lines.extend(
        [
            "",
            "## Required Row Contract",
            "",
            "- Public forecasting source only.",
            "- Strict resolution date, not latest observed data.",
            "- `y_known` resolved binary outcome.",
            "- Computed relation must be `pre_cutoff` against the panel cutoff date.",
            "- No duplicate event core already present in the strict matched corpus.",
            "",
            "## Interpretation",
            "",
            report["interpretation"],
            "",
        ]
    )
    (out_dir / "cutoff_acquisition_manifest_report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-b-report", type=Path, default=DEFAULT_STAGE_B)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build_report(args.stage_b_report)
    print(json.dumps(report, indent=2, sort_keys=True))
    write_outputs(report, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
