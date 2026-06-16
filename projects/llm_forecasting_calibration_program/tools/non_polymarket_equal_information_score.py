#!/usr/bin/env python3
"""Score filled non-Polymarket equal-information market bars against model calls.

No network, no DB mutation. This is a post-acquisition audit: it consumes the
filled Manifold market-history rows and compares them to existing same-contract
model calls in the calibration DB.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ztare.experiment_stats import paired_permutation_test


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
PACKET_DIR = (
    PROGRAM
    / "cutoff_validity_v1/workspace/non_polymarket_equal_information_export_packet_2026_06_15"
)
DEFAULT_FILLED_ROWS = (
    PACKET_DIR
    / "manifold_history_fill_2026_06_15/non_polymarket_equal_information_filled_rows.jsonl"
)
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = PACKET_DIR / "manifold_history_score_2026_06_15"


MARKET_BASELINE_FAMILIES = {
    "manifold_market",
    "polymarket_market",
    "market",
}


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO))
    except ValueError:
        return str(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def brier(p: float, y: int) -> float:
    return (p - y) ** 2


def fetch_calls(db: Path, contract_ids: list[str]) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in contract_ids)
    rows = [
        dict(row)
        for row in con.execute(
            f"""
            SELECT
              pilot_id,
              contract_id,
              family,
              agent_id,
              primitive,
              condition,
              phase,
              role,
              p_success,
              brier,
              schema_ok,
              fired_at
            FROM pilot_calls
            WHERE contract_id IN ({placeholders})
              AND schema_ok = 1
              AND p_success IS NOT NULL
              AND brier IS NOT NULL
            """,
            contract_ids,
        )
    ]
    con.close()
    return rows


def permutation_panel_vs_market(panel_scores: list[float], market_scores: list[float]) -> dict[str, Any]:
    if not panel_scores or len(panel_scores) != len(market_scores):
        return {"n": 0, "p_value": None, "mean_delta": None}
    # paired_permutation_test returns a dict in this codebase.
    try:
        result = paired_permutation_test(panel_scores, market_scores)
    except TypeError:
        result = paired_permutation_test(panel_scores, market_scores, alternative="two-sided")
    if isinstance(result, dict):
        return result
    return {"n": len(panel_scores), "p_value": getattr(result, "p_value", None), "mean_delta": mean([a - b for a, b in zip(panel_scores, market_scores)])}


def score_pilot(
    comparison_id: str,
    pilot_id: str,
    condition: str,
    calls: list[dict[str, Any]],
    market_by_contract: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_contract: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in calls:
        by_family[str(row.get("family") or "")].append(row)
        by_contract[str(row["contract_id"])].append(row)

    common_contracts = sorted(set(by_contract) & set(market_by_contract))
    panel_rows = []
    for cid in common_contracts:
        ps = [float(row["p_success"]) for row in by_contract[cid]]
        y = int(market_by_contract[cid]["resolved_binary_outcome"])
        p_panel = mean(ps)
        if p_panel is None:
            continue
        market_b = float(market_by_contract[cid]["brier"])
        panel_rows.append(
            {
                "contract_id": cid,
                "model_panel_p": p_panel,
                "model_panel_brier": brier(p_panel, y),
                "market_p": float(market_by_contract[cid]["history_probability"]),
                "market_brier": market_b,
                "y": y,
                "n_model_calls": len(ps),
            }
        )
    family_summary = {}
    for family, rows in sorted(by_family.items()):
        if family in MARKET_BASELINE_FAMILIES:
            continue
        family_summary[family] = {
            "rows": len(rows),
            "contracts": len({str(row["contract_id"]) for row in rows}),
            "mean_brier": mean([float(row["brier"]) for row in rows]),
        }
    panel_scores = [float(row["model_panel_brier"]) for row in panel_rows]
    market_scores = [float(row["market_brier"]) for row in panel_rows]
    return {
        "comparison_id": comparison_id,
        "pilot_id": pilot_id,
        "condition": condition,
        "rows": len(calls),
        "contracts": len(common_contracts),
        "families": sorted(k for k in by_family if k not in MARKET_BASELINE_FAMILIES),
        "family_count": len({k for k in by_family if k not in MARKET_BASELINE_FAMILIES}),
        "mean_model_call_brier": mean([float(row["brier"]) for row in calls]),
        "mean_market_brier_on_common_contracts": mean(market_scores),
        "model_panel_mean_p_brier": mean(panel_scores),
        "model_call_minus_market_brier": (
            mean([float(row["brier"]) for row in calls]) - mean(market_scores)
            if mean([float(row["brier"]) for row in calls]) is not None and mean(market_scores) is not None
            else None
        ),
        "model_panel_minus_market_brier": (
            mean(panel_scores) - mean(market_scores)
            if mean(panel_scores) is not None and mean(market_scores) is not None
            else None
        ),
        "paired_permutation_model_panel_vs_market": permutation_panel_vs_market(
            panel_scores, market_scores
        ),
        "family_summary": family_summary,
        "panel_rows": panel_rows,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    filled = [row for row in load_jsonl(args.filled_rows) if int(row.get("schema_ok") or 0) == 1]
    market_by_contract = {str(row["contract_id"]): row for row in filled}
    contract_ids = sorted(market_by_contract)
    calls = [
        row
        for row in fetch_calls(args.db, contract_ids)
        if str(row.get("family") or "") not in MARKET_BASELINE_FAMILIES
    ]
    calls_by_comparison: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in calls:
        calls_by_comparison[(str(row["pilot_id"]), str(row.get("condition") or ""))].append(row)
    pilot_scores = [
        score_pilot(
            f"{pilot_id}::{condition or 'none'}",
            pilot_id,
            condition or "none",
            rows,
            market_by_contract,
        )
        for (pilot_id, condition), rows in sorted(calls_by_comparison.items())
    ]
    candidates = [
        row
        for row in pilot_scores
        if row["contracts"] >= args.min_contracts and row["family_count"] >= args.min_families
    ]
    candidates.sort(
        key=lambda row: (
            -(row["contracts"] or 0),
            -(row["family_count"] or 0),
            row["model_panel_minus_market_brier"]
            if row["model_panel_minus_market_brier"] is not None
            else 999,
        )
    )
    selected = candidates[0] if candidates else None
    return {
        "schema": "gp245-non-polymarket-equal-information-score-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "db": repo_relative(args.db),
            "filled_rows": repo_relative(args.filled_rows),
            "min_contracts": args.min_contracts,
            "min_families": args.min_families,
            "comparison_unit": "pilot_id_plus_condition",
        },
        "market_summary": {
            "contracts": len(contract_ids),
            "outcome_counts": {
                "0": sum(1 for row in filled if row.get("resolved_binary_outcome") == 0),
                "1": sum(1 for row in filled if row.get("resolved_binary_outcome") == 1),
            },
            "mean_market_brier": mean([float(row["brier"]) for row in filled]),
        },
        "candidate_count": len(candidates),
        "selected_candidate": selected,
        "pilot_scores": pilot_scores,
        "verdict": {
            "state": "scored_against_existing_model_calls" if selected else "no_sufficient_model_pilot",
            "second_source_gate_satisfied": bool(selected),
            "broad_market_human_claim_ready": False,
            "interpretation": (
                "This supplies a second non-Polymarket equal-information market bar and scores it "
                "against existing same-contract model calls. The current joined result is post-hoc "
                "and does not support an LLM-beats-market claim; treat it as second-source comparison "
                "evidence with an explicit power/significance boundary."
                if selected
                else "Filled market rows exist, but no model pilot met the coverage thresholds."
            ),
        },
    }


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "non_polymarket_equal_information_score.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Non-Polymarket Equal-Information Score",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- State: `{report['verdict']['state']}`",
        f"- Second-source gate satisfied: `{report['verdict']['second_source_gate_satisfied']}`",
        f"- Broad market/human claim ready: `{report['verdict']['broad_market_human_claim_ready']}`",
        f"- Market contracts: `{report['market_summary']['contracts']}`",
        f"- Market outcome counts: `{report['market_summary']['outcome_counts']}`",
        f"- Mean market Brier: `{fmt(report['market_summary']['mean_market_brier'])}`",
        f"- Candidate pilots: `{report['candidate_count']}`",
        f"- Interpretation: {report['verdict']['interpretation']}",
        "",
        "## Candidate Pilots",
        "",
        "| comparison | pilot | condition | contracts | families | model call Brier | panel Brier | market Brier | panel-market | p |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in [
        item
        for item in report["pilot_scores"]
        if item["contracts"] >= report["inputs"]["min_contracts"]
        and item["family_count"] >= report["inputs"]["min_families"]
    ]:
        perm = row.get("paired_permutation_model_panel_vs_market") or {}
        lines.append(
            "| {comparison} | {pilot} | {condition} | {contracts} | {families} | {call_brier} | {panel_brier} | {market_brier} | {delta} | {p} |".format(
                comparison=row["comparison_id"],
                pilot=row["pilot_id"],
                condition=row["condition"],
                contracts=row["contracts"],
                families=row["family_count"],
                call_brier=fmt(row["mean_model_call_brier"]),
                panel_brier=fmt(row["model_panel_mean_p_brier"]),
                market_brier=fmt(row["mean_market_brier_on_common_contracts"]),
                delta=fmt(row["model_panel_minus_market_brier"]),
                p=fmt(perm.get("p_value")),
            )
        )
    (out_dir / "non_polymarket_equal_information_score.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--filled-rows", type=Path, default=DEFAULT_FILLED_ROWS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--min-contracts", type=int, default=20)
    parser.add_argument("--min-families", type=int, default=4)
    args = parser.parse_args()
    report = build_report(args)
    write_outputs(report, args.out_dir)
    print(json.dumps(report["verdict"], indent=2, sort_keys=True))
    if report.get("selected_candidate"):
        selected = report["selected_candidate"]
        print(
            json.dumps(
                {
                    "pilot_id": selected["pilot_id"],
                    "comparison_id": selected["comparison_id"],
                    "condition": selected["condition"],
                    "contracts": selected["contracts"],
                    "families": selected["families"],
                    "model_panel_brier": selected["model_panel_mean_p_brier"],
                    "market_brier": selected["mean_market_brier_on_common_contracts"],
                    "panel_minus_market": selected["model_panel_minus_market_brier"],
                    "paired": selected["paired_permutation_model_panel_vs_market"],
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
