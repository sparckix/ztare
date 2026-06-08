#!/usr/bin/env python3
"""Effective-sample audit for the narrow Stage-C market/LLM comparison.

This is a no-call audit. It answers a narrower question than the blend audit:
are the low Brier scores and small market+LLM delta stable contract-level
evidence, or mostly a consequence of slice composition, outcome imbalance, and
pre-cutoff rows?
"""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
import statistics
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any

from src.ztare.experiment_stats import paired_permutation_test


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT_DIR = (
    REPO
    / "projects/llm_forecasting_calibration_program/truth_continuation_v1/workspace"
    / "market_llm_effective_n_stage_c_2026_06_03"
)


def brier(p: float, y: float) -> float:
    return (p - y) ** 2


def clamp01(value: float) -> float:
    return min(1.0, max(0.0, value))


def rows_from_db(db: Path) -> list[dict[str, Any]]:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    sql = """
    WITH llm AS (
      SELECT
        pc.contract_id,
        AVG(pc.p_success) AS panel_p,
        AVG(pc.brier) AS family_mean_brier,
        COUNT(*) AS n_calls,
        COALESCE(json_extract(pc.raw_json, '$.cutoff_relation'), '') AS cutoff_relation,
        COALESCE(json_extract(pc.raw_json, '$.topic'), '') AS topic
      FROM pilot_calls pc
      WHERE pc.pilot_id = 'cutoff_stage_b_panel_v1'
        AND pc.schema_ok = 1
      GROUP BY pc.contract_id
    ),
    market AS (
      SELECT contract_id, p_success AS market_p, brier AS market_brier
      FROM pilot_calls
      WHERE pilot_id = 'market_baseline_stage_c_v1'
        AND schema_ok = 1
    )
    SELECT
      c.contract_id,
      c.question,
      c.y_known,
      c.source,
      c.source_corpus,
      c.horizon,
      c.external_market_open,
      llm.cutoff_relation,
      llm.topic,
      llm.panel_p,
      llm.family_mean_brier,
      llm.n_calls,
      market.market_p,
      market.market_brier
    FROM llm
    JOIN market USING(contract_id)
    JOIN contracts c ON c.contract_id = llm.contract_id
    WHERE c.y_known IS NOT NULL
    ORDER BY c.contract_id
    """
    rows: list[dict[str, Any]] = []
    for row in conn.execute(sql):
        item = dict(row)
        y = float(item["y_known"])
        market_p = float(item["market_p"])
        panel_p = float(item["panel_p"])
        item["y_known"] = y
        item["market_p"] = market_p
        item["panel_p"] = panel_p
        item["panel_brier"] = brier(panel_p, y)
        item["fixed_half_p"] = 0.5 * market_p + 0.5 * panel_p
        item["fixed_half_brier"] = brier(float(item["fixed_half_p"]), y)
        item["abs_market_panel_gap"] = abs(market_p - panel_p)
        rows.append(item)
    return rows


def quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "p25": None, "median": None, "p75": None, "max": None}
    vals = sorted(values)
    def q(frac: float) -> float:
        pos = frac * (len(vals) - 1)
        lo = int(pos)
        hi = min(lo + 1, len(vals) - 1)
        if lo == hi:
            return vals[lo]
        return vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)
    return {
        "min": vals[0],
        "p25": q(0.25),
        "median": q(0.5),
        "p75": q(0.75),
        "max": vals[-1],
    }


def bootstrap_ci(values: list[float], *, n_boot: int = 5000, seed: int = 42) -> dict[str, Any]:
    if not values:
        return {"mean": None, "ci_lo": None, "ci_hi": None, "n_boot": n_boot}
    rng = random.Random(seed)
    n = len(values)
    draws = []
    for _ in range(n_boot):
        draws.append(mean(values[rng.randrange(n)] for _ in range(n)))
    draws.sort()
    return {
        "mean": mean(values),
        "ci_lo": draws[int(0.025 * (n_boot - 1))],
        "ci_hi": draws[int(0.975 * (n_boot - 1))],
        "n_boot": n_boot,
    }


def concentration(values: list[float]) -> dict[str, Any]:
    """How many largest absolute row contributions explain the absolute mass."""
    masses = sorted((abs(value) for value in values), reverse=True)
    total = sum(masses)
    if total <= 0:
        return {"total_abs_mass": 0.0, "n_for_50pct_abs_mass": 0, "n_for_80pct_abs_mass": 0}
    out: dict[str, Any] = {"total_abs_mass": total}
    for threshold in (0.5, 0.8):
        running = 0.0
        needed = 0
        for mass in masses:
            running += mass
            needed += 1
            if running / total >= threshold:
                break
        out[f"n_for_{int(threshold * 100)}pct_abs_mass"] = needed
    return out


def loo_prevalence_scores(rows: list[dict[str, Any]]) -> list[float]:
    if len(rows) < 2:
        return []
    out = []
    for i, row in enumerate(rows):
        train = rows[:i] + rows[i + 1 :]
        p = mean(float(item["y_known"]) for item in train)
        out.append(brier(p, float(row["y_known"])))
    return out


def probability_bins(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    bins = Counter()
    for row in rows:
        p = float(row[field])
        if p < 0.05:
            key = "[0,0.05)"
        elif p < 0.10:
            key = "[0.05,0.10)"
        elif p < 0.25:
            key = "[0.10,0.25)"
        elif p < 0.50:
            key = "[0.25,0.50)"
        elif p < 0.75:
            key = "[0.50,0.75)"
        elif p < 0.90:
            key = "[0.75,0.90)"
        elif p < 0.95:
            key = "[0.90,0.95)"
        else:
            key = "[0.95,1]"
        bins[key] += 1
    return dict(sorted(bins.items()))


def summarize(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    if not rows:
        return {"label": label, "n_contracts": 0}
    ys = [float(row["y_known"]) for row in rows]
    prevalence = mean(ys)
    market_scores = [float(row["market_brier"]) for row in rows]
    panel_scores = [float(row["panel_brier"]) for row in rows]
    half_scores = [float(row["fixed_half_brier"]) for row in rows]
    prevalence_scores = [brier(prevalence, y) for y in ys]
    loo_prev_scores = loo_prevalence_scores(rows)
    market_minus_panel = [
        float(row["market_brier"]) - float(row["panel_brier"]) for row in rows
    ]
    half_minus_market = [
        float(row["fixed_half_brier"]) - float(row["market_brier"]) for row in rows
    ]
    return {
        "label": label,
        "n_contracts": len(rows),
        "n_llm_calls": sum(int(row["n_calls"]) for row in rows),
        "outcome_yes_rate": prevalence,
        "n_yes": int(sum(ys)),
        "n_no": len(rows) - int(sum(ys)),
        "topic_counts": dict(Counter(str(row.get("topic") or "unknown") for row in rows).most_common()),
        "market_p_quantiles": quantiles([float(row["market_p"]) for row in rows]),
        "panel_p_quantiles": quantiles([float(row["panel_p"]) for row in rows]),
        "market_probability_bins": probability_bins(rows, "market_p"),
        "panel_probability_bins": probability_bins(rows, "panel_p"),
        "market_extreme_share_p_le_0_10_or_ge_0_90": mean(
            1.0 if float(row["market_p"]) <= 0.10 or float(row["market_p"]) >= 0.90 else 0.0
            for row in rows
        ),
        "panel_extreme_share_p_le_0_10_or_ge_0_90": mean(
            1.0 if float(row["panel_p"]) <= 0.10 or float(row["panel_p"]) >= 0.90 else 0.0
            for row in rows
        ),
        "mean_abs_market_panel_probability_gap": mean(
            float(row["abs_market_panel_gap"]) for row in rows
        ),
        "brier": {
            "market": mean(market_scores),
            "panel_mean_probability": mean(panel_scores),
            "fixed_half_market_half_llm": mean(half_scores),
            "in_sample_outcome_prevalence": mean(prevalence_scores),
            "loo_outcome_prevalence": None if not loo_prev_scores else mean(loo_prev_scores),
            "constant_0_5": mean(brier(0.5, y) for y in ys),
        },
        "bootstrap_ci_by_contract": {
            "market": bootstrap_ci(market_scores),
            "panel_mean_probability": bootstrap_ci(panel_scores),
            "fixed_half_market_half_llm": bootstrap_ci(half_scores),
            "market_minus_panel": bootstrap_ci(market_minus_panel),
            "fixed_half_minus_market": bootstrap_ci(half_minus_market),
        },
        "paired_tests": {
            "panel_vs_market": paired_permutation_test(panel_scores, market_scores, n_perm=5000, seed=42),
            "fixed_half_vs_market": paired_permutation_test(half_scores, market_scores, n_perm=5000, seed=42),
        },
        "delta_concentration": {
            "market_minus_panel": concentration(market_minus_panel),
            "fixed_half_minus_market": concentration(half_minus_market),
        },
        "easy_market_rows": {
            "market_brier_lt_0_01": sum(1 for score in market_scores if score < 0.01),
            "market_brier_lt_0_05": sum(1 for score in market_scores if score < 0.05),
            "share_market_brier_lt_0_05": mean(1.0 if score < 0.05 else 0.0 for score in market_scores),
        },
    }


def build_report(db: Path) -> dict[str, Any]:
    rows = rows_from_db(db)
    by_relation = {
        relation or "unknown": summarize(
            [row for row in rows if str(row.get("cutoff_relation") or "") == relation],
            relation or "unknown",
        )
        for relation in sorted({str(row.get("cutoff_relation") or "") for row in rows})
    }
    overall = summarize(rows, "overall")
    post = by_relation.get("post_cutoff", {})
    state = "matched_slice_too_small_for_general_market_or_human_claim"
    if (
        post
        and post.get("brier", {}).get("panel_mean_probability") is not None
        and post["brier"]["panel_mean_probability"] > post["brier"]["market"]
    ):
        state = "post_cutoff_market_dominates_llm_on_narrow_matched_slice"
    return {
        "schema": "market-llm-effective-n-stage-c-v1",
        "scope": "same 51-contract Stage-C Manifold preoutcome market bar used by market_llm_blend_stage_c_audit",
        "db": str(db.relative_to(REPO)) if db.is_relative_to(REPO) else str(db),
        "overall": overall,
        "by_relation": by_relation,
        "verdict": {
            "state": state,
            "main_read": (
                "Use contract count, not market platform history or LLM call count, "
                "as the unit of evidence for the matched comparison. The current "
                "slice is informative as a stress control but too small and too "
                "source-specific for a broad market/human conclusion."
            ),
        },
    }


def fmt(value: Any) -> str:
    if value is None:
        return "`None`"
    if isinstance(value, float):
        return f"`{value:.6f}`"
    return f"`{value}`"


def write_report(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "market_llm_effective_n_stage_c_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Stage-C Market/LLM Effective-N Audit",
        "",
        f"- Scope: `{report['scope']}`",
        f"- Verdict: `{report['verdict']['state']}`",
        f"- Main read: {report['verdict']['main_read']}",
        "",
        "## Overall Matched Slice",
        "",
    ]
    overall = report["overall"]
    lines.extend(summary_lines(overall))
    lines.extend(["", "## Relation Breakdown", ""])
    for relation, item in report["by_relation"].items():
        lines.extend([f"### {relation}", ""])
        lines.extend(summary_lines(item))
        lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "",
            "The matched unit is the contract. The market may be estimated from a "
            "large participant pool, but that does not create more independent "
            "matched test outcomes here. The current comparison has 51 contract "
            "outcomes, split 32 pre-cutoff and 19 post-cutoff. Low Brier should "
            "therefore be read against the outcome prevalence, market probability "
            "extremeness, and contract-bootstrap intervals above, not as a broad "
            "claim that either side is generally calibrated.",
            "",
        ]
    )
    (out_dir / "market_llm_effective_n_stage_c_report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def summary_lines(item: dict[str, Any]) -> list[str]:
    b = item.get("brier", {})
    ci = item.get("bootstrap_ci_by_contract", {})
    pt = item.get("paired_tests", {})
    lines = [
        f"- Contracts: `{item.get('n_contracts')}`",
        f"- LLM calls: `{item.get('n_llm_calls')}`",
        f"- Outcome YES rate: {fmt(item.get('outcome_yes_rate'))} "
        f"({item.get('n_yes')} YES / {item.get('n_no')} NO)",
        f"- Market Brier: {fmt(b.get('market'))}",
        f"- LLM panel mean-probability Brier: {fmt(b.get('panel_mean_probability'))}",
        f"- Fixed 50/50 Brier: {fmt(b.get('fixed_half_market_half_llm'))}",
        f"- LOO outcome-prevalence Brier: {fmt(b.get('loo_outcome_prevalence'))}",
        f"- Constant 0.5 Brier: {fmt(b.get('constant_0_5'))}",
        f"- Market extreme share p<=0.10 or >=0.90: {fmt(item.get('market_extreme_share_p_le_0_10_or_ge_0_90'))}",
        f"- Panel extreme share p<=0.10 or >=0.90: {fmt(item.get('panel_extreme_share_p_le_0_10_or_ge_0_90'))}",
        f"- Mean absolute market-panel probability gap: {fmt(item.get('mean_abs_market_panel_probability_gap'))}",
    ]
    for key in ("market", "panel_mean_probability", "fixed_half_market_half_llm"):
        row = ci.get(key) or {}
        lines.append(
            f"- Bootstrap {key} mean/CI: {fmt(row.get('mean'))} "
            f"[{fmt(row.get('ci_lo'))}, {fmt(row.get('ci_hi'))}]"
        )
    for key, row in pt.items():
        lines.append(
            f"- Paired test {key}: p={fmt(row.get('p_value'))}, "
            f"CI=[{fmt(row.get('ci_lo'))}, {fmt(row.get('ci_hi'))}]"
        )
    easy = item.get("easy_market_rows") or {}
    lines.append(
        f"- Market rows with Brier <0.05: `{easy.get('market_brier_lt_0_05')}` "
        f"({fmt(easy.get('share_market_brier_lt_0_05'))})"
    )
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()
    report = build_report(args.db)
    write_report(report, args.out_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
