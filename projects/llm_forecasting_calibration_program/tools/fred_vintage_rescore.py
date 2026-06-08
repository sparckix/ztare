#!/usr/bin/env python3
"""Rescore existing FRED calls on vintage-stable/audited labels."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_AUDIT = WORKSPACE / "fred_vintage_timing_audit_2026_06_04/fred_vintage_timing_audit.json"
DEFAULT_PAIR_CALLS = WORKSPACE / "fred_cutoff_pair_packet_2026_06_04/fred_cutoff_pair_calls.jsonl"
DEFAULT_CONTROL_CALLS = WORKSPACE / "fred_blinded_value_control_packet_2026_06_04/fred_blinded_value_control_calls.jsonl"
DEFAULT_OUT = WORKSPACE / "fred_vintage_rescore_2026_06_04"


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO))
    except ValueError:
        return str(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
    return rows


def p_success(row: dict[str, Any]) -> float | None:
    try:
        p = float(row.get("p_success"))
    except (TypeError, ValueError):
        return None
    return p if 0.0 <= p <= 1.0 else None


def brier(p: float, y: int) -> float:
    return (p - y) ** 2


def paired_delta(rows: list[dict[str, Any]], *, brier_key: str) -> dict[str, Any]:
    by_pair: dict[tuple[str, str, str], dict[str, float]] = defaultdict(dict)
    for row in rows:
        key = (str(row["series_id"]), str(row["family"]), str(row.get("condition") or ""))
        by_pair[key][str(row["cutoff_relation"])] = float(row[brier_key])
    deltas = [
        vals["post_cutoff"] - vals["pre_cutoff"]
        for vals in by_pair.values()
        if "post_cutoff" in vals and "pre_cutoff" in vals
    ]
    return {
        "paired_complete": len(deltas),
        "mean_post_minus_pre_brier": mean(deltas) if deltas else None,
        "positive_delta_count": sum(1 for d in deltas if d > 0),
        "negative_delta_count": sum(1 for d in deltas if d < 0),
        "zero_delta_count": sum(1 for d in deltas if d == 0),
    }


def score_calls(calls: list[dict[str, Any]], audit_by_contract: dict[str, dict[str, Any]]) -> dict[str, Any]:
    scored: list[dict[str, Any]] = []
    skipped = 0
    for call in calls:
        audit = audit_by_contract.get(str(call.get("contract_id")))
        p = p_success(call)
        if not audit or p is None or audit.get("join_status") != "vintage_scoreable":
            skipped += 1
            continue
        y_current = audit.get("current_y_known")
        y_vintage = audit.get("y_two_point_realtime")
        if y_current not in (0, 1) or y_vintage not in (0, 1):
            skipped += 1
            continue
        scored.append(
            {
                "contract_id": call.get("contract_id"),
                "series_id": audit.get("series_id"),
                "cutoff_relation": audit.get("cutoff_relation"),
                "family": call.get("family") or call.get("agent_id"),
                "condition": call.get("condition"),
                "p_success": p,
                "y_current": int(y_current),
                "y_vintage": int(y_vintage),
                "label_changed": int(y_current) != int(y_vintage),
                "brier_current": brier(p, int(y_current)),
                "brier_vintage": brier(p, int(y_vintage)),
            }
        )
    by_condition = {}
    for condition in sorted({str(row.get("condition") or "") for row in scored}):
        cond_rows = [row for row in scored if str(row.get("condition") or "") == condition]
        by_condition[condition] = {
            "rows": len(cond_rows),
            "current_mean_brier": mean(row["brier_current"] for row in cond_rows),
            "vintage_mean_brier": mean(row["brier_vintage"] for row in cond_rows),
            "label_changed_calls": sum(1 for row in cond_rows if row["label_changed"]),
            "paired_current": paired_delta(cond_rows, brier_key="brier_current"),
            "paired_vintage": paired_delta(cond_rows, brier_key="brier_vintage"),
        }
    return {
        "calls_rows": len(calls),
        "scored_rows": len(scored),
        "skipped_rows": skipped,
        "label_changed_calls": sum(1 for row in scored if row["label_changed"]),
        "current_mean_brier": mean(row["brier_current"] for row in scored) if scored else None,
        "vintage_mean_brier": mean(row["brier_vintage"] for row in scored) if scored else None,
        "paired_current": paired_delta(scored, brier_key="brier_current"),
        "paired_vintage": paired_delta(scored, brier_key="brier_vintage"),
        "by_condition": by_condition,
        "rows": scored,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    args.audit = args.audit.resolve()
    args.pair_calls = args.pair_calls.resolve()
    args.control_calls = args.control_calls.resolve()
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    audit_by_contract = {
        str(row.get("contract_id")): row
        for row in audit.get("rows", [])
        if isinstance(row, dict)
    }
    pair = score_calls(load_jsonl(args.pair_calls), audit_by_contract)
    control = score_calls(load_jsonl(args.control_calls), audit_by_contract)
    return {
        "schema": "gp245-fred-vintage-rescore-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "audit": repo_relative(args.audit),
        "pair_calls": repo_relative(args.pair_calls),
        "control_calls": repo_relative(args.control_calls),
        "audit_summary": audit.get("summary"),
        "pair": {k: v for k, v in pair.items() if k != "rows"},
        "control": {k: v for k, v in control.items() if k != "rows"},
        "pair_rows": pair["rows"],
        "control_rows": control["rows"],
        "verdict": "vintage_labels_materially_change_fred_scores"
        if (pair.get("label_changed_calls") or control.get("label_changed_calls"))
        else "vintage_labels_no_rescore_change_on_scoreable_subset",
    }


def render_md(report: dict[str, Any]) -> str:
    pair = report["pair"]
    control = report["control"]
    lines = [
        "# FRED Vintage Rescore",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Verdict: `{report['verdict']}`",
        f"- Audit: `{report['audit']}`",
        "",
        "## Pair Panel",
        "",
        f"- Calls rows: `{pair['calls_rows']}`",
        f"- Vintage-scored rows: `{pair['scored_rows']}`",
        f"- Label-changed calls: `{pair['label_changed_calls']}`",
        f"- Current-label mean Brier on subset: `{pair['current_mean_brier']}`",
        f"- Vintage-label mean Brier on subset: `{pair['vintage_mean_brier']}`",
        f"- Current paired delta: `{pair['paired_current']}`",
        f"- Vintage paired delta: `{pair['paired_vintage']}`",
        "",
        "## Blinded Control",
        "",
        f"- Calls rows: `{control['calls_rows']}`",
        f"- Vintage-scored rows: `{control['scored_rows']}`",
        f"- Label-changed calls: `{control['label_changed_calls']}`",
        f"- Current-label mean Brier on subset: `{control['current_mean_brier']}`",
        f"- Vintage-label mean Brier on subset: `{control['vintage_mean_brier']}`",
        f"- Current paired delta: `{control['paired_current']}`",
        f"- Vintage paired delta: `{control['paired_vintage']}`",
        "",
        "## Blinded Control By Arm",
        "",
    ]
    for condition, data in control["by_condition"].items():
        lines.extend(
            [
                f"### `{condition}`",
                "",
                f"- Rows: `{data['rows']}`",
                f"- Label-changed calls: `{data['label_changed_calls']}`",
                f"- Current mean Brier: `{data['current_mean_brier']}`",
                f"- Vintage mean Brier: `{data['vintage_mean_brier']}`",
                f"- Current paired delta: `{data['paired_current']}`",
                f"- Vintage paired delta: `{data['paired_vintage']}`",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--pair-calls", type=Path, default=DEFAULT_PAIR_CALLS)
    parser.add_argument("--control-calls", type=Path, default=DEFAULT_CONTROL_CALLS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "fred_vintage_rescore.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (args.out_dir / "fred_vintage_rescore.md").write_text(render_md(report), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("schema", "generated_at", "verdict", "pair", "control")}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
