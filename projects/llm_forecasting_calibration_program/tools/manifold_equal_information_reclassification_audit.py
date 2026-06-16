#!/usr/bin/env python3
"""Audit whether Stage-C Manifold market rows can be reclassified.

No DB mutation. The goal is to prevent a tempting but invalid shortcut: taking
the 51 existing Manifold pre-outcome market rows and flipping
equal_information_flag from 0 to 1. The rows are useful stress controls, but
their own receipts say they were produced as Stage-C base-rate repair, not as a
frozen same-information baseline packet.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = (
    PROGRAM
    / "truth_continuation_v1/workspace/manifold_equal_information_reclassification_audit_2026_06_15"
)
PILOT_ID = "market_baseline_stage_c_v1"


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO))
    except ValueError:
        return str(path)


def parse_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        data = json.loads(value)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def fetch_rows(db: Path) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = [
        dict(row)
        for row in con.execute(
            """
            SELECT
              ebo.baseline_id,
              ebo.contract_id,
              ebo.platform,
              ebo.equal_information_flag,
              ebo.observed_at,
              ebo.days_before_resolution,
              ebo.p_success,
              ebo.source_currency_receipt,
              ebo.raw_json,
              c.source,
              c.source_corpus,
              c.y_known
            FROM external_baseline_observations ebo
            JOIN contracts c ON c.contract_id = ebo.contract_id
            WHERE ebo.pilot_id = ?
            ORDER BY ebo.contract_id
            """,
            (PILOT_ID,),
        )
    ]
    con.close()
    return rows


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    rows = fetch_rows(args.db)
    blocker_counts: Counter[str] = Counter()
    scope_counts: Counter[str] = Counter()
    provenance_counts: Counter[str] = Counter()
    cutoff_counts: Counter[str] = Counter()
    selection_counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []

    for row in rows:
        receipt = parse_json(row.get("source_currency_receipt"))
        raw_outer = parse_json(row.get("raw_json"))
        parsed = raw_outer.get("parsed_json") if isinstance(raw_outer.get("parsed_json"), dict) else {}
        raw = raw_outer.get("raw_json") if isinstance(raw_outer.get("raw_json"), dict) else {}

        scope = str(receipt.get("baseline_scope") or parsed.get("baseline_kind") or "unknown")
        scope_counts[scope] += 1
        provenance_counts[str(parsed.get("base_rate_provenance") or raw.get("base_rate_provenance") or "unknown")] += 1
        cutoff_counts[str(receipt.get("cutoff_relation") or parsed.get("cutoff_relation") or "unknown")] += 1
        selection_counts[str(parsed.get("selection_method") or raw.get("selection_method") or "none")] += 1

        if int(row.get("equal_information_flag") or 0) != 0:
            blocker_counts["unexpected_equal_information_flag"] += 1
        if receipt.get("not_equal_information_human_baseline") is True or parsed.get("not_equal_information_human_baseline") is True:
            blocker_counts["receipt_declares_not_equal_information"] += 1
        if scope != "narrow_stage_c_preoutcome_market_probability":
            blocker_counts["non_stage_c_scope"] += 1
        if row.get("days_before_resolution") is None:
            blocker_counts["missing_standard_days_before_resolution"] += 1
        if parsed.get("target_days_before_resolution") is None:
            blocker_counts["missing_target_days_before_resolution"] += 1
        if not parsed.get("source_question_id") and not raw.get("source_question_id"):
            blocker_counts["missing_source_question_id"] += 1
        if not parsed.get("source_url") and not raw.get("source_url"):
            blocker_counts["missing_source_url"] += 1
        if len(examples) < 5:
            examples.append(
                {
                    "contract_id": row.get("contract_id"),
                    "source_corpus": row.get("source_corpus"),
                    "observed_at": row.get("observed_at"),
                    "p_success": row.get("p_success"),
                    "y_known": row.get("y_known"),
                    "baseline_scope": scope,
                    "not_equal_information_human_baseline": receipt.get("not_equal_information_human_baseline")
                    or parsed.get("not_equal_information_human_baseline"),
                    "base_rate_provenance": parsed.get("base_rate_provenance")
                    or raw.get("base_rate_provenance"),
                    "selection_method": parsed.get("selection_method") or raw.get("selection_method"),
                }
            )

    can_reclassify = False
    return {
        "schema": "gp245-manifold-equal-information-reclassification-audit-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {"db": repo_relative(args.db), "pilot_id": PILOT_ID},
        "row_count": len(rows),
        "counts": {
            "scope_counts": dict(scope_counts),
            "provenance_counts": dict(provenance_counts),
            "cutoff_relation_counts": dict(cutoff_counts),
            "selection_method_counts": dict(selection_counts),
            "blocker_counts": dict(blocker_counts),
        },
        "examples": examples,
        "verdict": {
            "can_reclassify_existing_rows": can_reclassify,
            "state": "do_not_reclassify_stage_c_manifold_rows",
            "reason": (
                "The rows carry explicit not-equal-information receipts and were "
                "created as Stage-C pre-outcome market-prior/base-rate repair rows, "
                "not as a frozen same-information baseline packet."
            ),
            "valid_use": (
                "Use the 51 rows as a narrow Manifold stress control and market-prior "
                "repair surface."
            ),
            "invalid_use": (
                "Do not flip equal_information_flag to 1, do not count these rows as "
                "the independent equal-information source, and do not use them for a "
                "broad human/crowd comparison."
            ),
            "completion_path": (
                "Acquire a new Manifold packet under an explicit export/freeze rule: "
                "resolved binary contracts, auditable source URL/outcome, timestamped "
                "market probability at or before the target freeze, and prompts that "
                "withhold market prices from model calls."
            ),
        },
    }


def render_md(report: dict[str, Any]) -> str:
    verdict = report["verdict"]
    counts = report["counts"]
    lines = [
        "# Manifold Equal-Information Reclassification Audit",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Rows audited: `{report['row_count']}`",
        f"- State: `{verdict['state']}`",
        f"- Can reclassify existing rows: `{verdict['can_reclassify_existing_rows']}`",
        f"- Reason: {verdict['reason']}",
        f"- Valid use: {verdict['valid_use']}",
        f"- Invalid use: {verdict['invalid_use']}",
        f"- Completion path: {verdict['completion_path']}",
        "",
        "## Counts",
        "",
        f"- Scope counts: `{counts['scope_counts']}`",
        f"- Provenance counts: `{counts['provenance_counts']}`",
        f"- Cutoff relation counts: `{counts['cutoff_relation_counts']}`",
        f"- Selection method counts: `{counts['selection_method_counts']}`",
        f"- Blocker counts: `{counts['blocker_counts']}`",
        "",
        "## Examples",
        "",
        "| contract | corpus | observed_at | p | y | scope | not equal-info | provenance | selection |",
        "|---|---|---|---:|---:|---|---|---|---|",
    ]
    for row in report["examples"]:
        lines.append(
            "| {contract_id} | {source_corpus} | {observed_at} | {p_success} | {y_known} | {baseline_scope} | {neq} | {prov} | {sel} |".format(
                contract_id=row.get("contract_id"),
                source_corpus=row.get("source_corpus"),
                observed_at=row.get("observed_at"),
                p_success=row.get("p_success"),
                y_known=row.get("y_known"),
                baseline_scope=row.get("baseline_scope"),
                neq=row.get("not_equal_information_human_baseline"),
                prov=row.get("base_rate_provenance"),
                sel=row.get("selection_method"),
            )
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build_report(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "manifold_equal_information_reclassification_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "manifold_equal_information_reclassification_audit.md").write_text(
        render_md(report),
        encoding="utf-8",
    )
    print(json.dumps(report["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
