#!/usr/bin/env python3
"""Audit simple LLM+market blends on the narrow Stage-C Manifold baseline.

This is intentionally scoped. It uses only the 51 DB-ingested Stage-C Manifold
pre-outcome market rows and same-contract Stage-B LLM calls. It is not a broad
human/crowd comparison and should not be reported as one.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
from pathlib import Path
from statistics import mean
from typing import Any

from src.ztare.experiment_stats import n_required_for_brier_delta, paired_permutation_test


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT_DIR = (
    REPO
    / "projects/llm_forecasting_calibration_program/truth_continuation_v1/workspace"
    / "market_llm_blend_stage_c_2026_06_03"
)


def brier(p: float, y: float) -> float:
    return (p - y) ** 2


def blend_brier(row: dict[str, Any], market_weight: float) -> float:
    y = float(row["y_known"])
    p = (
        market_weight * float(row["market_p"])
        + (1.0 - market_weight) * float(row["panel_p"])
    )
    return brier(p, y)


def rows_from_db(db: Path) -> list[dict[str, Any]]:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    rows: list[dict[str, Any]] = []
    sql = """
    WITH llm AS (
      SELECT
        pc.contract_id,
        AVG(pc.p_success) AS panel_p,
        AVG(pc.brier) AS family_mean_brier,
        COUNT(*) AS n_calls,
        COALESCE(json_extract(pc.raw_json, '$.cutoff_relation'), '') AS cutoff_relation
      FROM pilot_calls pc
      WHERE pc.pilot_id = 'cutoff_stage_b_panel_v1'
        AND pc.schema_ok = 1
      GROUP BY pc.contract_id
    ),
    market AS (
      SELECT
        contract_id,
        p_success AS market_p,
        brier AS market_brier,
        observed_at,
        days_before_resolution,
        equal_information_flag,
        source_currency_receipt,
        provenance_url,
        baseline_kind,
        platform
      FROM v_external_market_baselines
      WHERE pilot_id = 'market_baseline_stage_c_v1'
        AND schema_ok = 1
    )
    SELECT
      c.contract_id,
      c.question,
      c.y_known,
      llm.cutoff_relation,
      llm.panel_p,
      llm.family_mean_brier,
      llm.n_calls,
      market.market_p,
      market.market_brier,
      market.observed_at AS market_observed_at,
      market.days_before_resolution,
      market.equal_information_flag,
      market.source_currency_receipt,
      market.provenance_url,
      market.baseline_kind,
      market.platform AS market_platform
    FROM llm
    JOIN market USING(contract_id)
    JOIN contracts c ON c.contract_id = llm.contract_id
    WHERE c.y_known IS NOT NULL
    ORDER BY c.contract_id
    """
    for row in conn.execute(sql):
        item = dict(row)
        y = float(item["y_known"])
        item["panel_brier"] = brier(float(item["panel_p"]), y)
        item["equal_information_flag"] = int(item.get("equal_information_flag") or 0)
        rows.append(item)
    return rows


def paired_policy_tests(rows: list[dict[str, Any]], candidate_briers: list[float]) -> dict[str, Any]:
    market = [float(row["market_brier"]) for row in rows]
    panel = [float(row["panel_brier"]) for row in rows]
    if not rows:
        return {}
    diffs = [candidate - base for candidate, base in zip(candidate_briers, market)]
    delta = mean(diffs)
    sd = statistics.stdev(diffs) if len(diffs) > 1 else 0.0
    return {
        "candidate_minus_market_delta": delta,
        "candidate_minus_market_paired_permutation": paired_permutation_test(
            candidate_briers,
            market,
            n_perm=5000,
            seed=42,
        ),
        "n_required_for_observed_delta": (
            n_required_for_brier_delta(delta, sd_brier=sd) if sd > 0 and delta != 0 else None
        ),
        "candidate_minus_panel_delta": mean(
            candidate - base for candidate, base in zip(candidate_briers, panel)
        ),
    }


def summarize(rows: list[dict[str, Any]], weights: list[float]) -> dict[str, Any]:
    if not rows:
        return {
            "n_contracts": 0,
            "market_brier": None,
            "panel_mean_probability_brier": None,
            "family_call_mean_brier": None,
            "best_grid": None,
            "grid": [],
        }
    grid = []
    for market_weight in weights:
        blend_scores = [blend_brier(row, market_weight) for row in rows]
        grid.append(
            {
                "market_weight": market_weight,
                "llm_weight": round(1.0 - market_weight, 10),
                "blend_brier": mean(blend_scores),
            }
        )
    fixed_half = next(item for item in grid if abs(item["market_weight"] - 0.5) < 1e-12)
    fixed_half_scores = [blend_brier(row, 0.5) for row in rows]
    best_weight = float(min(grid, key=lambda item: item["blend_brier"])["market_weight"])
    best_scores = [blend_brier(row, best_weight) for row in rows]
    return {
        "n_contracts": len(rows),
        "n_llm_calls": sum(int(row["n_calls"]) for row in rows),
        "equal_information_contracts": sum(1 for row in rows if int(row.get("equal_information_flag") or 0) == 1),
        "not_equal_information_contracts": sum(
            1 for row in rows if int(row.get("equal_information_flag") or 0) == 0
        ),
        "market_brier": mean(float(row["market_brier"]) for row in rows),
        "panel_mean_probability_brier": mean(float(row["panel_brier"]) for row in rows),
        "family_call_mean_brier": mean(float(row["family_mean_brier"]) for row in rows),
        "fixed_half_market_half_llm": fixed_half,
        "best_grid": min(grid, key=lambda item: item["blend_brier"]),
        "grid": grid,
        "paired_tests": {
            "panel_mean_probability_vs_market": paired_policy_tests(
                rows,
                [float(row["panel_brier"]) for row in rows],
            ),
            "fixed_half_vs_market": paired_policy_tests(rows, fixed_half_scores),
            "best_in_sample_grid_vs_market": paired_policy_tests(rows, best_scores),
        },
    }


def loo_scores(rows: list[dict[str, Any]], weights: list[float]) -> list[dict[str, Any]]:
    """Leave-one-contract-out tuning over the market/LLM blend grid."""
    if len(rows) < 3:
        return []
    scored = []
    for i, heldout in enumerate(rows):
        train = rows[:i] + rows[i + 1 :]
        best = summarize(train, weights)["best_grid"]
        market_weight = float(best["market_weight"])
        scored.append(
            {
                "contract_id": heldout["contract_id"],
                "cutoff_relation": heldout["cutoff_relation"],
                "selected_market_weight": market_weight,
                "selected_llm_weight": round(1.0 - market_weight, 10),
                "brier": blend_brier(heldout, market_weight),
            }
        )
    return scored


def loo_grid(rows: list[dict[str, Any]], weights: list[float]) -> dict[str, Any] | None:
    scored = loo_scores(rows, weights)
    if not scored:
        return None
    briers = [item["brier"] for item in scored]
    return {
        "n_contracts": len(scored),
        "loo_brier": mean(briers),
        "selected_market_weight_mean": mean(item["selected_market_weight"] for item in scored),
        "selected_market_weight_counts": {
            f"{weight:.2f}": sum(1 for item in scored if item["selected_market_weight"] == weight)
            for weight in weights
            if any(item["selected_market_weight"] == weight for item in scored)
        },
        "paired_tests": {
            "loo_tuned_grid_vs_market": paired_policy_tests(rows, briers),
        },
    }


def relation_summary(rows: list[dict[str, Any]], weights: list[float]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for rel in sorted({str(row["cutoff_relation"]) for row in rows}):
        rel_rows = [row for row in rows if str(row["cutoff_relation"]) == rel]
        out[rel or "unknown"] = summarize(rel_rows, weights)
    return out


def verdict(report: dict[str, Any]) -> dict[str, Any]:
    overall_market = float(report["overall"]["market_brier"])
    overall_loo = float(report["loo_grid"]["loo_brier"])
    post = report["by_relation"].get("post_cutoff") or {}
    post_loo = (post.get("loo_grid") or {}).get("loo_brier")
    post_market = post.get("market_brier")
    paired = report["loo_grid"]["paired_tests"]["loo_tuned_grid_vs_market"][
        "candidate_minus_market_paired_permutation"
    ]
    if post_loo is not None and post_market is not None and post_loo >= post_market - 1e-12:
        state = "not_deployable_post_cutoff_prefers_market_only"
    elif paired.get("p_value") is not None and paired["p_value"] <= 0.05 and overall_loo < overall_market:
        state = "candidate_positive_needs_external_replication"
    elif overall_loo < overall_market:
        state = "weak_aggregate_positive_diagnostic_only"
    else:
        state = "no_blend_lift"
    return {
        "state": state,
        "overall_loo_minus_market": overall_loo - overall_market,
        "post_cutoff_loo_minus_market": (
            None if post_loo is None or post_market is None else float(post_loo) - float(post_market)
        ),
        "promotion_gate": (
            "Promote only if leave-one-out or heldout blend beats market-only by >=0.01 "
            "Brier, paired p<=0.05, and no post-cutoff/source-valid regression."
        ),
    }


def ptest_line(label: str, test: dict[str, Any]) -> str:
    perm = test["candidate_minus_market_paired_permutation"]
    return (
        f"- {label}: delta vs market `{test['candidate_minus_market_delta']:.6f}`, "
        f"paired p=`{perm.get('p_value')}`, CI "
        f"`[{perm.get('ci_lo')}, {perm.get('ci_hi')}]`, "
        f"n_required_for_observed_delta=`{test['n_required_for_observed_delta']}`"
    )


def write_report(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "market_llm_blend_stage_c_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Stage-C Market + LLM Blend Audit",
        "",
        f"- Scope: `{report['scope']}`",
        f"- Baseline source: `{report['baseline_source']}`",
        f"- Contracts: `{report['overall']['n_contracts']}`",
        f"- Equal-information baseline contracts: `{report['overall']['equal_information_contracts']}`",
        f"- Not-equal-information baseline contracts: `{report['overall']['not_equal_information_contracts']}`",
        f"- LLM calls: `{report['overall']['n_llm_calls']}`",
        f"- Market Brier: `{report['overall']['market_brier']:.6f}`",
        f"- LLM panel mean-probability Brier: `{report['overall']['panel_mean_probability_brier']:.6f}`",
        f"- LLM family-call mean Brier: `{report['overall']['family_call_mean_brier']:.6f}`",
        f"- Fixed 50/50 blend Brier: `{report['overall']['fixed_half_market_half_llm']['blend_brier']:.6f}`",
        f"- Best grid blend: market weight `{report['overall']['best_grid']['market_weight']:.2f}`, "
        f"LLM weight `{report['overall']['best_grid']['llm_weight']:.2f}`, "
        f"Brier `{report['overall']['best_grid']['blend_brier']:.6f}`",
        f"- Leave-one-out tuned-grid Brier: `{report['loo_grid']['loo_brier']:.6f}`",
        f"- Verdict: `{report['verdict']['state']}`",
        "",
        "## Paired Tests",
        "",
        ptest_line(
            "LLM panel mean-probability",
            report["overall"]["paired_tests"]["panel_mean_probability_vs_market"],
        ),
        ptest_line(
            "Fixed 50/50 blend",
            report["overall"]["paired_tests"]["fixed_half_vs_market"],
        ),
        ptest_line(
            "Best in-sample grid blend",
            report["overall"]["paired_tests"]["best_in_sample_grid_vs_market"],
        ),
        ptest_line(
            "Leave-one-out tuned-grid blend",
            report["loo_grid"]["paired_tests"]["loo_tuned_grid_vs_market"],
        ),
        "",
        "## Relation Breakdown",
        "",
    ]
    for rel, item in report["by_relation"].items():
        best = item["best_grid"]
        lines.extend(
            [
                f"### {rel}",
                "",
                f"- Contracts: `{item['n_contracts']}`",
                f"- Equal-information baseline contracts: `{item['equal_information_contracts']}`",
                f"- Not-equal-information baseline contracts: `{item['not_equal_information_contracts']}`",
                f"- Market Brier: `{item['market_brier']:.6f}`",
                f"- LLM panel mean-probability Brier: `{item['panel_mean_probability_brier']:.6f}`",
                f"- LLM family-call mean Brier: `{item['family_call_mean_brier']:.6f}`",
                f"- Fixed 50/50 blend Brier: `{item['fixed_half_market_half_llm']['blend_brier']:.6f}`",
                f"- Best grid blend: market weight `{best['market_weight']:.2f}`, "
                f"LLM weight `{best['llm_weight']:.2f}`, Brier `{best['blend_brier']:.6f}`",
                f"- Leave-one-out tuned-grid Brier: `{item['loo_grid']['loo_brier']:.6f}`",
                ptest_line(
                    "Leave-one-out tuned-grid blend",
                    item["loo_grid"]["paired_tests"]["loo_tuned_grid_vs_market"],
                ),
                "",
            ]
        )
    lines.extend(
        [
            "## Interpretation",
            "",
            "This is a narrow Manifold-only pre-outcome market bar. It can test "
            "whether the local Stage-C market snapshot adds to same-contract LLM "
            "panel probabilities, but it cannot support a broad human/crowd claim. "
            "The relation split is decisive for interpretation: post-cutoff rows "
            "prefer market-only in this grid, while the aggregate blend gain is "
            "mostly driven by pre-cutoff rows where source visibility likely helps "
            "the LLM panel. The best-grid row is exploratory because it selects a "
            "weight on the same outcomes; the leave-one-out row is the stricter "
            "within-slice check. The promotion gate is intentionally stricter "
            "than the observed result: a blend would need >=0.01 Brier lift, "
            "paired p<=0.05, and no post-cutoff/source-valid regression.",
            "",
        ]
    )
    (out_dir / "market_llm_blend_stage_c_report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()
    rows = rows_from_db(args.db)
    weights = [round(i / 20, 2) for i in range(21)]
    report = {
        "schema": "gp245-stage-c-market-llm-blend-v1",
        "scope": "narrow_stage_c_manifold_preoutcome_market_bar_not_broad_human_crowd",
        "baseline_source": "v_external_market_baselines",
        "db": str(args.db.relative_to(REPO)),
        "overall": summarize(rows, weights),
        "loo_grid": loo_grid(rows, weights),
        "by_relation": relation_summary(rows, weights),
    }
    for rel, rel_rows in {
        rel or "unknown": [row for row in rows if str(row["cutoff_relation"]) == rel]
        for rel in sorted({str(row["cutoff_relation"]) for row in rows})
    }.items():
        report["by_relation"][rel]["loo_grid"] = loo_grid(rel_rows, weights)
    report["verdict"] = verdict(report)
    write_report(report, args.out_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
