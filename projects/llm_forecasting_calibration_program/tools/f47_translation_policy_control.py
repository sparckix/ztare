#!/usr/bin/env python3
"""Compare F47 translated probabilities against live applied baselines.

This is a no-call control audit over the already-fired overlapping F47
tournament packet. The promoted translation result only beat the prompt's own
same-packet probabilities; this script tests the sharper applied question:
does it beat F100 and panel baselines on the same contract rows?
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.ztare.experiment_stats import paired_permutation_test

from f47_translation_tournament_score import (
    DEFAULT_CALLS,
    DEFAULT_KEY,
    brier,
    contract_rows,
    fit_logistic,
    load_edges,
    sigmoid,
)


REPO = Path(__file__).resolve().parents[3]
WORKSPACE = (
    REPO
    / "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace"
)
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT_JSON = WORKSPACE / "f47_translation_policy_control_2026_06_03.json"
DEFAULT_OUT_MD = WORKSPACE / "f47_translation_policy_control_2026_06_03.md"
MARKET_PILOT = "market_baseline_stage_c_v1"


def confident_no(p: float) -> float:
    if p < 0.10:
        return p + (0.65 - p) * 0.5
    return p


def mean(values: list[float]) -> float:
    return statistics.mean(values) if values else float("nan")


def summarize_policy(rows: list[dict[str, Any]], policy_key: str) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    losses = [brier(float(row[policy_key]), int(row["y"])) for row in rows]
    return {
        "n": len(rows),
        "brier": round(mean(losses), 6),
        "yes_rate": round(mean([float(row["y"]) for row in rows]), 6),
        "mean_p": round(mean([float(row[policy_key]) for row in rows]), 6),
    }


def compare(rows: list[dict[str, Any]], candidate: str, baseline: str) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    cand_losses = [brier(float(row[candidate]), int(row["y"])) for row in rows]
    base_losses = [brier(float(row[baseline]), int(row["y"])) for row in rows]
    return {
        "n": len(rows),
        "candidate": candidate,
        "baseline": baseline,
        "candidate_brier": round(mean(cand_losses), 6),
        "baseline_brier": round(mean(base_losses), 6),
        "delta_candidate_minus_baseline": round(mean([c - b for c, b in zip(cand_losses, base_losses)]), 6),
        "paired_permutation": paired_permutation_test(cand_losses, base_losses, seed=47),
    }


def heldout_contract_predictions(edge_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    contracts = contract_rows(edge_rows)
    sources = sorted({row["source"] for row in contracts})
    out: list[dict[str, Any]] = []
    for source in sources:
        train = [row for row in contracts if row["source"] != source]
        test = [row for row in contracts if row["source"] == source]
        if not train or not test:
            continue
        intercept, slope = fit_logistic(
            [float(row["pairwise_score"]) for row in train],
            [int(row["y"]) for row in train],
        )
        for row in test:
            raw = float(row["raw_context_p"])
            out.append(
                {
                    **row,
                    "raw_context_p": raw,
                    "f100_family_p": confident_no(raw),
                    "translated_p": sigmoid(intercept + slope * float(row["pairwise_score"])),
                    "heldout_source": source,
                }
            )
    return out


def panel_rows(family_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in family_rows:
        grouped[str(row["contract_id"])].append(row)
    out: list[dict[str, Any]] = []
    for contract_id, rows in sorted(grouped.items()):
        y_values = {int(row["y"]) for row in rows}
        sources = {str(row["source"]) for row in rows}
        if len(y_values) != 1 or len(sources) != 1:
            raise SystemExit(f"inconsistent panel row for {contract_id}")
        raw_panel = mean([float(row["raw_context_p"]) for row in rows])
        out.append(
            {
                "contract_id": contract_id,
                "source": next(iter(sources)),
                "y": next(iter(y_values)),
                "family_count": len(rows),
                "raw_panel_p": raw_panel,
                "f100_panel_after_mean_p": confident_no(raw_panel),
                "f100_mean_family_p": mean([float(row["f100_family_p"]) for row in rows]),
                "translated_panel_p": mean([float(row["translated_p"]) for row in rows]),
            }
        )
    return out


def load_market_rows(db: Path) -> dict[str, float]:
    con = sqlite3.connect(db)
    try:
        rows = con.execute(
            """
            SELECT contract_id, p_success
            FROM pilot_calls
            WHERE pilot_id = ?
              AND schema_ok = 1
              AND p_success IS NOT NULL
            """,
            (MARKET_PILOT,),
        ).fetchall()
    finally:
        con.close()
    return {str(contract_id): float(p) for contract_id, p in rows}


def with_market(panel: list[dict[str, Any]], market: dict[str, float]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in panel:
        if row["contract_id"] not in market:
            continue
        item = dict(row)
        item["market_p"] = market[row["contract_id"]]
        item["market_half_translated_p"] = 0.5 * float(item["market_p"]) + 0.5 * float(item["translated_panel_p"])
        item["market_half_raw_p"] = 0.5 * float(item["market_p"]) + 0.5 * float(item["raw_panel_p"])
        rows.append(item)
    return rows


def split_comparisons(rows: list[dict[str, Any]], candidate: str, baselines: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {"overall": {baseline: compare(rows, candidate, baseline) for baseline in baselines}}
    by_source: dict[str, Any] = {}
    for source in sorted({str(row["source"]) for row in rows}):
        subset = [row for row in rows if str(row["source"]) == source]
        by_source[source] = {baseline: compare(subset, candidate, baseline) for baseline in baselines}
    out["by_source"] = by_source
    return out


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    edge_rows, exclusions = load_edges(args.calls, args.answer_key)
    family = heldout_contract_predictions(edge_rows)
    panel = panel_rows(family)
    market_rows = with_market(panel, load_market_rows(args.db))

    family_policy_keys = ["raw_context_p", "f100_family_p", "translated_p"]
    panel_policy_keys = [
        "raw_panel_p",
        "f100_panel_after_mean_p",
        "f100_mean_family_p",
        "translated_panel_p",
    ]
    market_policy_keys = [
        "market_p",
        "market_half_raw_p",
        "market_half_translated_p",
        "raw_panel_p",
        "translated_panel_p",
    ]
    verdict = "f47_translation_not_production_default"
    translated_vs_f100 = compare(panel, "translated_panel_p", "f100_mean_family_p")
    translated_vs_raw = compare(panel, "translated_panel_p", "raw_panel_p")
    if (
        translated_vs_f100["delta_candidate_minus_baseline"] <= -0.01
        and translated_vs_f100["paired_permutation"].get("p_value", 1.0) <= 0.05
        and all(
            compare([row for row in panel if row["source"] == source], "translated_panel_p", "f100_mean_family_p")[
                "delta_candidate_minus_baseline"
            ]
            <= 0
            for source in sorted({row["source"] for row in panel})
        )
    ):
        verdict = "f47_translation_beats_f100_on_same_packet_experimental"

    return {
        "schema": "f47-translation-policy-control-v1",
        "date": "2026-06-03",
        "calls": str(args.calls.relative_to(REPO)),
        "answer_key": str(args.answer_key.relative_to(REPO)),
        "db": str(args.db.relative_to(REPO)),
        "valid_edge_rows": len(edge_rows),
        "excluded_edge_rows": len(exclusions),
        "family_contract_rows": len(family),
        "panel_contract_rows": len(panel),
        "panel_family_count_distribution": dict(Counter(int(row["family_count"]) for row in panel)),
        "source_counts_family_rows": dict(Counter(str(row["source"]) for row in family)),
        "source_counts_panel_rows": dict(Counter(str(row["source"]) for row in panel)),
        "family_policy_summary": {key: summarize_policy(family, key) for key in family_policy_keys},
        "panel_policy_summary": {key: summarize_policy(panel, key) for key in panel_policy_keys},
        "family_comparisons": split_comparisons(
            family,
            "translated_p",
            ["raw_context_p", "f100_family_p"],
        ),
        "panel_comparisons": split_comparisons(
            panel,
            "translated_panel_p",
            ["raw_panel_p", "f100_panel_after_mean_p", "f100_mean_family_p"],
        ),
        "market_overlap": {
            "market_pilot": MARKET_PILOT,
            "n_contracts": len(market_rows),
            "note": "Only same-contract rows from the existing Stage-C market baseline are included; zero or small n is a scope limit, not evidence against market comparison.",
            "policy_summary": {key: summarize_policy(market_rows, key) for key in market_policy_keys},
            "comparisons": {
                "translated_vs_market": compare(market_rows, "translated_panel_p", "market_p"),
                "market_half_translated_vs_market": compare(market_rows, "market_half_translated_p", "market_p"),
                "market_half_raw_vs_market": compare(market_rows, "market_half_raw_p", "market_p"),
            },
        },
        "promotion_gate": {
            "requires_translated_panel_beats_f100_mean_family_by_at_least": -0.01,
            "requires_p_at_most": 0.05,
            "requires_no_source_regression_vs_f100": True,
            "requires_separate_market_or_human_join_before_deployment": True,
        },
        "verdict": verdict,
    }


def render_md(report: dict[str, Any]) -> str:
    panel = report["panel_policy_summary"]
    comps = report["panel_comparisons"]["overall"]
    lines = [
        "# F47 Translation Policy Control - 2026-06-03",
        "",
        f"- Verdict: `{report['verdict']}`",
        f"- Valid edge rows: `{report['valid_edge_rows']}`; family-contract rows: `{report['family_contract_rows']}`; panel contracts: `{report['panel_contract_rows']}`.",
        f"- Panel family-count distribution: `{report['panel_family_count_distribution']}`",
        f"- Source counts: `{report['source_counts_panel_rows']}`",
        "",
        "## Panel Policy Summary",
        "",
        "| policy | n | Brier | mean p | yes rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for key, row in panel.items():
        lines.append(f"| `{key}` | `{row['n']}` | `{row['brier']}` | `{row['mean_p']}` | `{row['yes_rate']}` |")
    lines.extend(["", "## Panel Comparisons", "", "| candidate | baseline | n | delta | p |", "|---|---|---:|---:|---:|"])
    for baseline, row in comps.items():
        lines.append(
            f"| `{row['candidate']}` | `{baseline}` | `{row['n']}` | "
            f"`{row['delta_candidate_minus_baseline']}` | `{row['paired_permutation'].get('p_value')}` |"
        )
    lines.extend(["", "## Source Split vs F100 Mean-Family", "", "| source | n | delta translated-F100 | p |", "|---|---:|---:|---:|"])
    for source, source_comps in report["panel_comparisons"]["by_source"].items():
        row = source_comps["f100_mean_family_p"]
        lines.append(
            f"| `{source}` | `{row['n']}` | `{row['delta_candidate_minus_baseline']}` | `{row['paired_permutation'].get('p_value')}` |"
        )
    market = report["market_overlap"]
    lines.extend(
        [
            "",
            "## Market Overlap",
            "",
            f"- Market pilot: `{market['market_pilot']}`",
            f"- Same-contract overlap: `{market['n_contracts']}`",
            f"- Note: {market['note']}",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calls", type=Path, default=DEFAULT_CALLS)
    parser.add_argument("--answer-key", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()
    report = build_report(args)
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(report), encoding="utf-8")
    print(json.dumps({
        "verdict": report["verdict"],
        "panel_policy_summary": report["panel_policy_summary"],
        "panel_vs_f100": report["panel_comparisons"]["overall"]["f100_mean_family_p"],
        "market_overlap_n": report["market_overlap"]["n_contracts"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
