#!/usr/bin/env python3
"""
score_prediction_ledger_calibration.py

PATTERN-012 calibration analyzer. Sibling to scripts/public/validators/validate_prediction_ledger.py:
the validator enforces structural invariants (tier, append-only, schema); this
script scores CALIBRATION on resolved rows so PATTERN-012's demotion rules
("Brier worse than uniform after N=20", "predictions gamed by hedging") become
falsifiable.

Pre-registered against PL-017. Read-only on analytics/public/ledgers/prediction/prediction_ledger.jsonl;
writes only analytics/public/ledgers/prediction/prediction_ledger_calibration_summary.json plus stdout.

Outputs:
  1. Per-predictor Brier score on resolved-bucket multinomial predictions.
  2. Effort ratio (predicted / actual) histogram + per-predictor mean; flags
     any predictor whose mean ratio sits outside [0.5, 2.0].
  3. Cost ratio (predicted / actual) histogram + per-predictor mean; same flag.
  4. Tier distribution.
  5. Hedging-bias heuristic in two flavors:
       (5a) p assigned to the eventually realized bucket consistently below 0.4
            (predictor is under-confident in their own correct calls).
       (5b) average max(p) per row near 1/K (uniform); predictor is hedging
            toward base rate rather than expressing a view.
  6. Cross-predictor comparison (best/worst Brier among predictors with N>=2).
  7. Demotion-rule trigger check matching the pattern's stated rules.

The script implements the actual Brier formula
    BS = (1/N) * sum_i sum_k (p_{i,k} - y_{i,k})^2
where y_{i,k} is the one-hot indicator of the realized bucket k for row i.
"Worse than uniform" baseline for a K-bucket prediction is
    BS_uniform_K = (K-1) / K
    (uniform p_k = 1/K across all K buckets; one bucket realizes ->
     squared deviation = (1 - 1/K)^2 + (K-1)*(1/K)^2 = (K-1)/K)
We report uniform baseline matched to each row's K so the comparison is fair
across heterogeneous question shapes.

Apply PATTERN-007 inverted (no-bookkeeping clause): the script computes the
actual Brier formula above (NOT a vacuous mean of probabilities), runs the
hedging detector with concrete thresholds tied to the pattern's demotion rules,
and emits a falsifiable demotion verdict. If any of these reduces to a tautology,
the operator should flag the script and demote it.

Usage:
  python scripts/public/control/forecast/score_prediction_ledger_calibration.py [path]

Default path: analytics/public/ledgers/prediction/prediction_ledger.jsonl
Default output: analytics/public/ledgers/prediction/prediction_ledger_calibration_summary.json
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

LEDGER_DEFAULT = Path("analytics/public/ledgers/prediction/prediction_ledger.jsonl")
SUMMARY_DEFAULT = Path("analytics/public/ledgers/prediction/prediction_ledger_calibration_summary.json")

# --- thresholds tied to demotion rules ----------------------------------------
EFFORT_RATIO_LOW = 0.5
EFFORT_RATIO_HIGH = 2.0
COST_RATIO_LOW = 0.5
COST_RATIO_HIGH = 2.0
HEDGING_REALIZED_P_THRESHOLD = 0.4   # rule 5a: under-confidence on correct calls
HEDGING_UNDERCONF_FRACTION = 0.5      # >=50% of resolved rows below threshold -> hedger
DEMOTION_N_GATE = 20                  # pattern's "after N>=20 predictions" rule


# --- IO -----------------------------------------------------------------------
def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            print(f"FATAL: line {i}: malformed JSON — {exc}", file=sys.stderr)
            sys.exit(2)
    return rows


# --- Brier scoring ------------------------------------------------------------
def realized_index(row: dict[str, Any]) -> int | None:
    """Map actual_outcome_bucket "event_N_..." -> 0-based index N-1.

    Rows whose bucket label does not start with `event_<int>_` are not scoreable
    on the multinomial Brier component (caller must skip).
    """
    bucket = row.get("actual_outcome_bucket")
    if not isinstance(bucket, str) or not bucket.startswith("event_"):
        return None
    tail = bucket[len("event_"):]
    n_str = tail.split("_", 1)[0]
    try:
        return int(n_str) - 1
    except ValueError:
        return None


def brier_for_row(row: dict[str, Any]) -> dict[str, Any] | None:
    """Compute multinomial Brier contribution for one resolved row.

    Returns None if the row is not scoreable (no resolved bucket, missing odds,
    or odds shape inconsistent with bucket index).
    """
    odds = row.get("conditional_odds")
    if not isinstance(odds, list) or not odds:
        return None
    realized = realized_index(row)
    if realized is None:
        return None
    if realized >= len(odds):
        return None
    K = len(odds)
    probs = []
    for entry in odds:
        try:
            probs.append(float(entry.get("p", 0.0)))
        except (TypeError, ValueError):
            return None
    # Renormalise softly if probs sum is off by < 5% (tolerate rounding); else flag.
    total = sum(probs)
    normalisation_error = abs(total - 1.0)
    if total <= 0:
        return None
    if normalisation_error > 0.05:
        # Out of spec; do not silently renormalize.
        return {
            "prediction_id": row.get("prediction_id"),
            "K": K,
            "realized_index": realized,
            "p_realized": probs[realized] / total,
            "brier": None,
            "brier_uniform_baseline": (K - 1) / K,
            "skipped_reason": f"odds sum to {total:.3f}, normalisation_error={normalisation_error:.3f} > 0.05",
        }
    # One-hot target.
    sq_dev = 0.0
    for k, p in enumerate(probs):
        y = 1.0 if k == realized else 0.0
        sq_dev += (p - y) ** 2
    return {
        "prediction_id": row.get("prediction_id"),
        "K": K,
        "realized_index": realized,
        "p_realized": probs[realized],
        "brier": sq_dev,
        "brier_uniform_baseline": (K - 1) / K,
        "skipped_reason": None,
    }


# --- Effort / cost ratios -----------------------------------------------------
def effort_ratio(row: dict[str, Any]) -> float | None:
    pred = row.get("effort_estimate_agent_minutes")
    actual = row.get("actual_effort_minutes")
    if pred is None or actual is None:
        return None
    try:
        pred_f = float(pred)
        actual_f = float(actual)
    except (TypeError, ValueError):
        return None
    if actual_f <= 0:
        return None
    return pred_f / actual_f


def cost_ratio(row: dict[str, Any]) -> float | None:
    pred = row.get("cost_estimate_usd")
    actual = row.get("actual_cost_usd")
    if pred is None or actual is None:
        return None
    try:
        pred_f = float(pred)
        actual_f = float(actual)
    except (TypeError, ValueError):
        return None
    if actual_f <= 0:
        return None
    return pred_f / actual_f


def histogram(values: list[float], edges: list[float]) -> dict[str, int]:
    """Bin values into half-open buckets [edges[i], edges[i+1])."""
    counts: dict[str, int] = {}
    if not values:
        return counts
    bins = list(zip(edges[:-1], edges[1:]))
    for lo, hi in bins:
        label = f"[{lo:g}, {hi:g})"
        counts[label] = sum(1 for v in values if lo <= v < hi)
    counts[f">= {edges[-1]:g}"] = sum(1 for v in values if v >= edges[-1])
    counts[f"< {edges[0]:g}"] = sum(1 for v in values if v < edges[0])
    return counts


def safe_mean(xs: list[float]) -> float | None:
    return statistics.fmean(xs) if xs else None


# --- main analysis ------------------------------------------------------------
def analyse(rows: list[dict[str, Any]]) -> dict[str, Any]:
    resolved = [r for r in rows if r.get("resolved_at") and r.get("actual_outcome_bucket")]
    unresolved = [r for r in rows if not r.get("resolved_at")]

    # ---- per-row Brier -------------------------------------------------------
    brier_rows: list[dict[str, Any]] = []
    for row in resolved:
        b = brier_for_row(row)
        if b is not None:
            b["predictor"] = row.get("predictor")
            b["substrate"] = row.get("substrate")
            b["tier"] = row.get("tier")
            brier_rows.append(b)

    scoreable = [b for b in brier_rows if b["brier"] is not None]

    # ---- per-predictor aggregation ------------------------------------------
    by_predictor: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for b in scoreable:
        by_predictor[b["predictor"] or "?"].append(b)

    per_predictor_summary: dict[str, dict[str, Any]] = {}
    for predictor, items in by_predictor.items():
        briers = [it["brier"] for it in items]
        baselines = [it["brier_uniform_baseline"] for it in items]
        p_realized_vals = [it["p_realized"] for it in items]
        underconf_count = sum(1 for p in p_realized_vals if p < HEDGING_REALIZED_P_THRESHOLD)
        underconf_frac = underconf_count / len(p_realized_vals)
        flag_5a = underconf_frac >= HEDGING_UNDERCONF_FRACTION and len(p_realized_vals) >= 3
        # 5b: hedging-toward-uniform — average gap between max(p) and 1/K
        max_minus_uniform = []
        for it, src_row in zip(items, [next(r for r in resolved if r.get("prediction_id") == it["prediction_id"]) for it in items]):
            probs = [float(o.get("p", 0)) for o in src_row.get("conditional_odds", [])]
            if probs:
                K = len(probs)
                max_minus_uniform.append(max(probs) - 1.0 / K)
        avg_gap = safe_mean(max_minus_uniform)
        flag_5b = avg_gap is not None and avg_gap < 0.10 and len(items) >= 3
        per_predictor_summary[predictor] = {
            "n_scored": len(items),
            "brier_mean": safe_mean(briers),
            "brier_uniform_baseline_mean": safe_mean(baselines),
            "brier_minus_baseline_mean": (
                safe_mean(briers) - safe_mean(baselines)
                if briers and baselines else None
            ),
            "p_realized_mean": safe_mean(p_realized_vals),
            "underconfident_on_correct_call_fraction": underconf_frac,
            "avg_max_p_minus_uniform": avg_gap,
            "hedging_flag_5a_underconfident_on_correct": flag_5a,
            "hedging_flag_5b_clustering_near_uniform": flag_5b,
        }

    # ---- effort / cost ratios -----------------------------------------------
    effort_pairs: list[tuple[str, float]] = []
    cost_pairs: list[tuple[str, float]] = []
    for row in resolved:
        er = effort_ratio(row)
        if er is not None:
            effort_pairs.append((row.get("predictor") or "?", er))
        cr = cost_ratio(row)
        if cr is not None:
            cost_pairs.append((row.get("predictor") or "?", cr))

    effort_ratios = [r for _, r in effort_pairs]
    cost_ratios = [r for _, r in cost_pairs]
    effort_hist_edges = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]
    cost_hist_edges = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]

    by_predictor_effort: dict[str, list[float]] = defaultdict(list)
    for p, r in effort_pairs:
        by_predictor_effort[p].append(r)
    by_predictor_cost: dict[str, list[float]] = defaultdict(list)
    for p, r in cost_pairs:
        by_predictor_cost[p].append(r)

    effort_predictor_means = {
        p: {"n": len(rs), "mean_ratio": safe_mean(rs),
            "out_of_band": (
                safe_mean(rs) is not None
                and (safe_mean(rs) < EFFORT_RATIO_LOW or safe_mean(rs) > EFFORT_RATIO_HIGH)
            )}
        for p, rs in by_predictor_effort.items()
    }
    cost_predictor_means = {
        p: {"n": len(rs), "mean_ratio": safe_mean(rs),
            "out_of_band": (
                safe_mean(rs) is not None
                and (safe_mean(rs) < COST_RATIO_LOW or safe_mean(rs) > COST_RATIO_HIGH)
            )}
        for p, rs in by_predictor_cost.items()
    }

    # ---- tier distribution ---------------------------------------------------
    tier_distribution = {
        "tier_1": sum(1 for r in rows if r.get("tier") == 1),
        "tier_2": sum(1 for r in rows if r.get("tier") == 2),
        "tier_3": sum(1 for r in rows if r.get("tier") == 3),
        "untagged": sum(1 for r in rows if r.get("tier") is None),
    }

    # ---- cross-predictor comparison (predictors with N>=2) ------------------
    rankable = {p: s for p, s in per_predictor_summary.items() if s["n_scored"] >= 2}
    if rankable:
        ranked = sorted(rankable.items(), key=lambda kv: kv[1]["brier_mean"])
        cross_predictor = {
            "n_predictors_compared": len(ranked),
            "best_predictor": ranked[0][0],
            "best_brier_mean": ranked[0][1]["brier_mean"],
            "worst_predictor": ranked[-1][0],
            "worst_brier_mean": ranked[-1][1]["brier_mean"],
        }
    else:
        cross_predictor = {"n_predictors_compared": 0, "note": "no predictor with N>=2 scored rows"}

    # ---- demotion-rule trigger check ----------------------------------------
    overall_brier_mean = safe_mean([b["brier"] for b in scoreable])
    overall_baseline_mean = safe_mean([b["brier_uniform_baseline"] for b in scoreable])
    n_resolved_scored = len(scoreable)

    demotion_rule_brier = (
        n_resolved_scored >= DEMOTION_N_GATE
        and overall_brier_mean is not None
        and overall_baseline_mean is not None
        and overall_brier_mean >= overall_baseline_mean
    )
    # Hedging flag fires per-predictor at N>=3 (informational), but PATTERN-012
    # only demotes "after >=20 predictions". Keep the report flag visible for
    # operator review; only treat as a demotion trigger once the ledger crosses
    # the same N>=20 gate the Brier rule uses.
    hedging_flagged = any(
        s["hedging_flag_5a_underconfident_on_correct"] or s["hedging_flag_5b_clustering_near_uniform"]
        for s in per_predictor_summary.values()
    )
    demotion_rule_hedging = hedging_flagged and n_resolved_scored >= DEMOTION_N_GATE
    # human_hours-without-agent_minutes regression check on most recent 5 rows
    recent = sorted(rows, key=lambda r: r.get("predicted_at", ""))[-5:]
    human_hours_regression_count = sum(
        1 for r in recent
        if r.get("effort_estimate_human_hours") and not r.get("effort_estimate_agent_minutes")
    )
    demotion_rule_unit_regression = human_hours_regression_count >= 3

    demotion_triggers = {
        "rule_brier_worse_than_uniform_at_N20": demotion_rule_brier,
        "rule_hedging_detected_AND_n_ge_20": demotion_rule_hedging,
        "rule_hedging_flagged_informational": hedging_flagged,
        "rule_unit_regression_human_hours": demotion_rule_unit_regression,
        "n_resolved_scored": n_resolved_scored,
        "n_gate": DEMOTION_N_GATE,
        "overall_brier_mean": overall_brier_mean,
        "overall_uniform_baseline_mean": overall_baseline_mean,
    }
    demote_now = any([
        demotion_rule_brier,
        demotion_rule_hedging,
        demotion_rule_unit_regression,
    ])

    return {
        "n_rows_total": len(rows),
        "n_rows_resolved": len(resolved),
        "n_rows_unresolved": len(unresolved),
        "n_rows_brier_scored": n_resolved_scored,
        "n_rows_brier_skipped": len(brier_rows) - n_resolved_scored,
        "tier_distribution": tier_distribution,
        "per_predictor": per_predictor_summary,
        "cross_predictor": cross_predictor,
        "effort_ratio": {
            "n": len(effort_ratios),
            "mean": safe_mean(effort_ratios),
            "median": (statistics.median(effort_ratios) if effort_ratios else None),
            "min": (min(effort_ratios) if effort_ratios else None),
            "max": (max(effort_ratios) if effort_ratios else None),
            "histogram": histogram(effort_ratios, effort_hist_edges),
            "per_predictor": effort_predictor_means,
            "in_band_range": [EFFORT_RATIO_LOW, EFFORT_RATIO_HIGH],
        },
        "cost_ratio": {
            "n": len(cost_ratios),
            "mean": safe_mean(cost_ratios),
            "median": (statistics.median(cost_ratios) if cost_ratios else None),
            "histogram": histogram(cost_ratios, cost_hist_edges),
            "per_predictor": cost_predictor_means,
            "in_band_range": [COST_RATIO_LOW, COST_RATIO_HIGH],
            "note": (
                "no rows have both cost_estimate_usd and actual_cost_usd"
                if not cost_ratios else None
            ),
        },
        "brier_rows": scoreable,
        "demotion_check": demotion_triggers,
        "demote_now": demote_now,
    }


# --- formatting ---------------------------------------------------------------
def format_report(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("PATTERN-012 PREDICTION-LEDGER CALIBRATION REPORT")
    lines.append("=" * 60)
    lines.append(
        f"Rows: total={summary['n_rows_total']} "
        f"resolved={summary['n_rows_resolved']} "
        f"unresolved={summary['n_rows_unresolved']} "
        f"brier_scored={summary['n_rows_brier_scored']} "
        f"brier_skipped={summary['n_rows_brier_skipped']}"
    )
    td = summary["tier_distribution"]
    lines.append(
        f"Tier distribution: T1={td['tier_1']}  T2={td['tier_2']}  "
        f"T3={td['tier_3']}  untagged={td['untagged']}"
    )
    dc = summary["demotion_check"]
    lines.append("")
    lines.append("--- BRIER SCORE (per predictor) ---")
    for p, s in summary["per_predictor"].items():
        bm = s["brier_mean"]
        bb = s["brier_uniform_baseline_mean"]
        delta = s["brier_minus_baseline_mean"]
        flags = []
        if s["hedging_flag_5a_underconfident_on_correct"]:
            flags.append("HEDGING_5a_UNDERCONFIDENT")
        if s["hedging_flag_5b_clustering_near_uniform"]:
            flags.append("HEDGING_5b_NEAR_UNIFORM")
        flagstr = (" [" + ", ".join(flags) + "]") if flags else ""
        lines.append(
            f"  {p}: N={s['n_scored']}  brier={bm:.3f}  "
            f"uniform_baseline={bb:.3f}  delta={delta:+.3f}  "
            f"p_realized_mean={s['p_realized_mean']:.3f}  "
            f"underconf_frac={s['underconfident_on_correct_call_fraction']:.2f}"
            f"{flagstr}"
        )
    cp = summary["cross_predictor"]
    lines.append("")
    lines.append("--- CROSS-PREDICTOR COMPARISON ---")
    if cp.get("n_predictors_compared", 0) > 0:
        lines.append(
            f"  best:  {cp['best_predictor']}  brier={cp['best_brier_mean']:.3f}"
        )
        lines.append(
            f"  worst: {cp['worst_predictor']} brier={cp['worst_brier_mean']:.3f}"
        )
    else:
        lines.append(f"  {cp.get('note', '<none>')}")

    er = summary["effort_ratio"]
    lines.append("")
    lines.append("--- EFFORT RATIO (predicted_min / actual_min) ---")
    if er["n"]:
        lines.append(
            f"  N={er['n']}  mean={er['mean']:.2f}  median={er['median']:.2f}  "
            f"min={er['min']:.2f}  max={er['max']:.2f}  "
            f"in-band=[{er['in_band_range'][0]}, {er['in_band_range'][1]}]"
        )
        lines.append("  histogram:")
        for k, v in er["histogram"].items():
            lines.append(f"    {k}: {v}")
        lines.append("  per-predictor:")
        for p, s in er["per_predictor"].items():
            mr = s["mean_ratio"]
            mark = " OUT-OF-BAND" if s["out_of_band"] else ""
            lines.append(f"    {p}: N={s['n']}  mean_ratio={mr:.2f}{mark}")
    else:
        lines.append("  no scoreable rows")

    cr = summary["cost_ratio"]
    lines.append("")
    lines.append("--- COST RATIO (predicted_usd / actual_usd) ---")
    if cr["n"]:
        lines.append(
            f"  N={cr['n']}  mean={cr['mean']:.2f}  median={cr['median']:.2f}  "
            f"in-band=[{cr['in_band_range'][0]}, {cr['in_band_range'][1]}]"
        )
        for k, v in cr["histogram"].items():
            lines.append(f"    {k}: {v}")
    else:
        note = cr.get("note") or "no scoreable rows"
        lines.append(f"  {note}")

    lines.append("")
    lines.append("--- DEMOTION-RULE CHECK ---")
    lines.append(f"  N resolved scored: {dc['n_resolved_scored']} (gate: {dc['n_gate']})")
    obm = dc["overall_brier_mean"]
    obb = dc["overall_uniform_baseline_mean"]
    obm_str = f"{obm:.3f}" if obm is not None else "n/a"
    obb_str = f"{obb:.3f}" if obb is not None else "n/a"
    lines.append(f"  Overall brier_mean: {obm_str}  uniform_baseline: {obb_str}")
    lines.append(
        f"  rule_brier_worse_than_uniform_at_N20: "
        f"{dc['rule_brier_worse_than_uniform_at_N20']}"
    )
    lines.append(
        f"  rule_hedging_flagged_informational: "
        f"{dc['rule_hedging_flagged_informational']}"
    )
    lines.append(
        f"  rule_hedging_detected_AND_n_ge_20: "
        f"{dc['rule_hedging_detected_AND_n_ge_20']}"
    )
    lines.append(
        f"  rule_unit_regression_human_hours: "
        f"{dc['rule_unit_regression_human_hours']}"
    )
    lines.append(f"  DEMOTE NOW: {summary['demote_now']}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else LEDGER_DEFAULT
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else SUMMARY_DEFAULT
    if not src.exists():
        print(f"FATAL: ledger {src} does not exist", file=sys.stderr)
        return 2
    rows = parse_jsonl(src)
    summary = analyse(rows)
    print(format_report(summary))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, sort_keys=False) + "\n")
    print(f"Wrote summary: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
