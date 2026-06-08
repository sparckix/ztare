#!/usr/bin/env python3
"""Law 3 Stage-B reuse audit for strict matched cutoff rows.

The candidate report answers "do we have enough strict pre/post cutoff
contracts?" This report answers the next local question: among the strict rows
already available, what scored-call evidence can be reused without new model
calls, and where is the matched-slate deficit?
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from cutoff_candidate_report import build_rows


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = REPO / "projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace"
PUBLIC_SOURCES = {
    "manifold",
    "polymarket",
    "metaculus",
    "fred",
    "yfinance",
    "yfinance_etf",
    "kalshi",
    "premium_public_clean",
}
MIN_STAGE_B_PRE = 40
MIN_STAGE_B_POST = 40


def stratum_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row["source"]),
        str(row["topic"]),
        str(row["question_length_bucket"]),
    )


def matched_keys(rows: list[dict[str, Any]]) -> set[tuple[str, str, str]]:
    by_relation: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    for row in rows:
        by_relation[row["cutoff_relation"]].add(stratum_key(row))
    return by_relation["pre_cutoff"] & by_relation["post_cutoff"]


def load_scored_calls(db: Path, contract_ids: set[str]) -> list[dict[str, Any]]:
    if not contract_ids:
        return []
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in contract_ids)
    rows = [
        dict(row)
        for row in con.execute(
            f"""
            SELECT pc.call_id, pc.pilot_id, pc.contract_id, pc.family,
                   pc.condition, pc.primitive, pc.brier, pc.schema_ok,
                   c.source, c.source_corpus, c.post_training_cutoff, c.y_known
            FROM pilot_calls pc
            JOIN contracts c ON c.contract_id = pc.contract_id
            WHERE pc.contract_id IN ({placeholders})
              AND pc.schema_ok = 1
              AND pc.brier IS NOT NULL
              AND pc.family IS NOT NULL
            """,
            sorted(contract_ids),
        )
    ]
    con.close()
    return rows


def aggregate_cells(
    calls: list[dict[str, Any]],
    row_meta: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    call_counts: Counter[tuple[str, str, str, str]] = Counter()
    for call in calls:
        meta = row_meta.get(str(call["contract_id"]))
        if not meta:
            continue
        key = (
            str(call["contract_id"]),
            str(call["family"]),
            str(call["condition"] or ""),
            str(meta["cutoff_relation"]),
        )
        grouped[key].append(float(call["brier"]))
        call_counts[key] += 1

    cells: list[dict[str, Any]] = []
    for (contract_id, family, condition, relation), values in sorted(grouped.items()):
        meta = row_meta[contract_id]
        cells.append(
            {
                "contract_id": contract_id,
                "family": family,
                "condition": condition,
                "cutoff_relation": relation,
                "source": meta["source"],
                "topic": meta["topic"],
                "question_length_bucket": meta["question_length_bucket"],
                "stratum": "/".join(stratum_key(meta)),
                "mean_brier": statistics.mean(values),
                "raw_call_rows": call_counts[(contract_id, family, condition, relation)],
            }
        )
    return cells


def summarize_contracts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    relation_counts = Counter(row["cutoff_relation"] for row in rows)
    strata = Counter((row["cutoff_relation"], *stratum_key(row)) for row in rows)
    matched = matched_keys(rows)
    matched_rows = []
    for source, topic, length in sorted(matched):
        pre = strata[("pre_cutoff", source, topic, length)]
        post = strata[("post_cutoff", source, topic, length)]
        matched_rows.append(
            {
                "source": source,
                "topic": topic,
                "question_length_bucket": length,
                "pre_n": pre,
                "post_n": post,
                "pre_needed_to_stage_b_or_match": max(min(post, MIN_STAGE_B_PRE) - pre, 0),
            }
        )
    return {
        "contracts_by_relation": dict(relation_counts),
        "matched_strata": matched_rows,
        "matched_strata_count": len(matched_rows),
    }


def summarize_cells(cells: list[dict[str, Any]]) -> dict[str, Any]:
    relation_cells = Counter(cell["cutoff_relation"] for cell in cells)
    relation_contracts: dict[str, set[str]] = defaultdict(set)
    relation_raw_calls = Counter()
    for cell in cells:
        relation_contracts[cell["cutoff_relation"]].add(cell["contract_id"])
        relation_raw_calls[cell["cutoff_relation"]] += int(cell["raw_call_rows"])

    by_family_relation: dict[tuple[str, str], list[float]] = defaultdict(list)
    for cell in cells:
        by_family_relation[(cell["family"], cell["cutoff_relation"])].append(cell["mean_brier"])

    family_deltas: list[dict[str, Any]] = []
    families = sorted({cell["family"] for cell in cells})
    for family in families:
        pre = by_family_relation.get((family, "pre_cutoff"), [])
        post = by_family_relation.get((family, "post_cutoff"), [])
        if not pre or not post:
            continue
        family_deltas.append(
            {
                "family": family,
                "pre_cells": len(pre),
                "post_cells": len(post),
                "pre_mean_brier": round(statistics.mean(pre), 6),
                "post_mean_brier": round(statistics.mean(post), 6),
                "post_minus_pre": round(statistics.mean(post) - statistics.mean(pre), 6),
            }
        )

    pre_all = [cell["mean_brier"] for cell in cells if cell["cutoff_relation"] == "pre_cutoff"]
    post_all = [cell["mean_brier"] for cell in cells if cell["cutoff_relation"] == "post_cutoff"]
    aggregate_delta = None
    if pre_all and post_all:
        aggregate_delta = {
            "pre_cells": len(pre_all),
            "post_cells": len(post_all),
            "pre_mean_brier": round(statistics.mean(pre_all), 6),
            "post_mean_brier": round(statistics.mean(post_all), 6),
            "post_minus_pre": round(statistics.mean(post_all) - statistics.mean(pre_all), 6),
        }

    return {
        "contracts_with_scored_calls_by_relation": {
            relation: len(ids) for relation, ids in sorted(relation_contracts.items())
        },
        "aggregate_cells_by_relation": dict(relation_cells),
        "raw_call_rows_by_relation": dict(relation_raw_calls),
        "aggregate_delta": aggregate_delta,
        "family_deltas": family_deltas,
    }


def non_public_pre_cutoff_diagnostic(db: Path) -> dict[str, Any]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = [
        dict(row)
        for row in con.execute(
            """
            SELECT c.contract_id, c.source, c.source_corpus, c.task_type,
                   COUNT(pc.call_id) AS scored_call_rows,
                   COUNT(DISTINCT pc.family) AS families
            FROM contracts c
            JOIN pilot_calls pc ON pc.contract_id = c.contract_id
            WHERE c.y_known IS NOT NULL
              AND c.post_training_cutoff = 0
              AND (c.source IS NULL OR c.source NOT IN (
                  'manifold', 'polymarket', 'metaculus', 'fred',
                  'yfinance', 'yfinance_etf', 'kalshi', 'premium_public_clean'
              ))
              AND pc.schema_ok = 1
              AND pc.brier IS NOT NULL
            GROUP BY c.contract_id, c.source, c.source_corpus, c.task_type
            """
        )
    ]
    con.close()
    return {
        "role": "non_public_diagnostic_only",
        "contracts": len(rows),
        "scored_call_rows": sum(int(row["scored_call_rows"]) for row in rows),
        "by_source": dict(Counter(str(row["source"]) for row in rows)),
        "sample": rows[:20],
    }


def build_report(
    db: Path,
    panel_cutoff_date: str,
    *,
    prefer_computed_cutoff: bool,
) -> dict[str, Any]:
    candidate_rows = build_rows(
        db,
        panel_cutoff_date,
        prefer_computed_cutoff=prefer_computed_cutoff,
    )
    eligible = [row for row in candidate_rows if row["eligible_for_matched_audit"]]
    keys = matched_keys(eligible)
    matched = [row for row in eligible if stratum_key(row) in keys]
    all_meta = {str(row["contract_id"]): row for row in eligible}
    matched_meta = {str(row["contract_id"]): row for row in matched}

    all_calls = load_scored_calls(db, set(all_meta))
    matched_calls = [call for call in all_calls if str(call["contract_id"]) in matched_meta]
    all_cells = aggregate_cells(all_calls, all_meta)
    matched_cells = aggregate_cells(matched_calls, matched_meta)

    matched_summary = summarize_contracts(matched)
    matched_pre = matched_summary["contracts_by_relation"].get("pre_cutoff", 0)
    matched_post = matched_summary["contracts_by_relation"].get("post_cutoff", 0)
    stage_b_ready = (
        matched_pre >= MIN_STAGE_B_PRE
        and matched_post >= MIN_STAGE_B_POST
        and matched_summary["matched_strata_count"] > 0
    )
    return {
        "schema": "gp245-cutoff-stage-b-slate-v1",
        "db": str(db),
        "panel_cutoff_date": panel_cutoff_date,
        "prefer_computed_cutoff": prefer_computed_cutoff,
        "verdict": "stage_b_ready" if stage_b_ready else "stage_b_not_ready_pre_cutoff_underpowered",
        "public_strict_contracts": summarize_contracts(eligible),
        "matched_strict_contracts": matched_summary,
        "all_eligible_call_reuse": summarize_cells(all_cells),
        "matched_call_reuse": summarize_cells(matched_cells),
        "non_public_pre_cutoff_diagnostic": non_public_pre_cutoff_diagnostic(db),
        "stage_b_gate": {
            "min_pre_contracts": MIN_STAGE_B_PRE,
            "min_post_contracts": MIN_STAGE_B_POST,
            "matched_pre_contracts": matched_pre,
            "matched_post_contracts": matched_post,
            "pre_deficit": max(MIN_STAGE_B_PRE - matched_pre, 0),
            "ready": stage_b_ready,
        },
        "interpretation": (
            "This is a scored-call reuse audit, not a new model-call result. "
            "The main comparison is restricted to strict public rows in strata "
            "that have both pre-cutoff and post-cutoff contracts."
        ),
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cutoff_stage_b_balance_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Cutoff Stage-B Balance Report",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Verdict: `{report['verdict']}`",
        f"- Panel cutoff date: `{report['panel_cutoff_date']}`",
        f"- Prefer computed cutoff: `{report['prefer_computed_cutoff']}`",
        f"- Matched pre/post contracts: {report['stage_b_gate']['matched_pre_contracts']} / {report['stage_b_gate']['matched_post_contracts']}",
        f"- Pre-cutoff deficit to Stage B: {report['stage_b_gate']['pre_deficit']}",
        "",
        "## Matched Strata",
        "",
    ]
    for row in report["matched_strict_contracts"]["matched_strata"]:
        lines.append(
            f"- `{row['source']}` / `{row['topic']}` / `{row['question_length_bucket']}`: "
            f"pre={row['pre_n']}, post={row['post_n']}, "
            f"needed={row['pre_needed_to_stage_b_or_match']}"
        )

    lines.extend(["", "## Matched Call Reuse", ""])
    reuse = report["matched_call_reuse"]
    lines.append(f"- Contracts with scored calls by relation: `{reuse['contracts_with_scored_calls_by_relation']}`")
    lines.append(f"- Aggregate cells by relation: `{reuse['aggregate_cells_by_relation']}`")
    lines.append(f"- Raw call rows by relation: `{reuse['raw_call_rows_by_relation']}`")
    if reuse["aggregate_delta"]:
        delta = reuse["aggregate_delta"]
        lines.append(
            f"- Aggregate Brier post-minus-pre: {delta['post_minus_pre']:+.4f} "
            f"(pre={delta['pre_mean_brier']:.4f}, post={delta['post_mean_brier']:.4f})"
        )

    lines.extend(["", "## Family Deltas In Matched Strata", ""])
    for row in reuse["family_deltas"]:
        lines.append(
            f"- `{row['family']}`: post-minus-pre={row['post_minus_pre']:+.4f} "
            f"(pre={row['pre_mean_brier']:.4f}, post={row['post_mean_brier']:.4f}, "
            f"cells={row['pre_cells']}/{row['post_cells']})"
        )

    diag = report["non_public_pre_cutoff_diagnostic"]
    lines.extend(["", "## Non-Public Diagnostic Surface", ""])
    lines.append(
        f"- Contracts: {diag['contracts']}; scored call rows: {diag['scored_call_rows']}; "
        "role: diagnostic only, excluded from public Law 3."
    )

    closeout = (
        "Stage B strict public matched supply is ready under the current gate; "
        "remaining limitations are source breadth, base-rate repair, and "
        "second-source/general-source replication."
        if report["stage_b_gate"]["ready"]
        else (
            "Stage B remains blocked until the matched strict public pre-cutoff "
            "side reaches the minimum supply threshold."
        )
    )
    lines.extend(["", "## Interpretation", "", report["interpretation"], "", closeout, ""])
    (out_dir / "cutoff_stage_b_balance_report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--panel-cutoff-date", default="2025-10-01")
    parser.add_argument("--prefer-computed-cutoff", action="store_true", default=True)
    parser.add_argument(
        "--use-stored-cutoff",
        action="store_true",
        help="Use stored post_training_cutoff instead of computed relation when both exist.",
    )
    args = parser.parse_args()
    report = build_report(
        args.db,
        args.panel_cutoff_date,
        prefer_computed_cutoff=not args.use_stored_cutoff,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.out_dir:
        write_outputs(report, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
