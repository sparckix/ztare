#!/usr/bin/env python3
"""No-call audit for costed diagnostic review allocation.

This asks whether emitted diagnostic channels are useful as allocation
features. The default forecast is the F100 confident-NO mean panel. A reviewed
row pays a cost and uses a train-fold proxy reviewer (source-best or train-best
family). Sham and inverted triggers with the same review rate are included.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.ztare.experiment_stats import paired_permutation_test


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = PROGRAM / "nurture_intervention_v1/workspace"
DEFAULT_JSON = DEFAULT_OUT / "diagnostic_review_allocation_audit_2026_06_03.json"
DEFAULT_MD = DEFAULT_OUT / "diagnostic_review_allocation_audit_2026_06_03.md"
DEFAULT_PILOTS = ("v28a_full__v25_external", "v28a_refill__v25_external")
FAMILIES = ("claude", "codex_55", "codex_54mini", "gemini", "deepseek")
COSTS = (0.0, 0.0025, 0.005, 0.01, 0.02)
PRIMARY_COST = 0.005
MAJOR_SOURCE_N = 20


def parse_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def num(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def brier(p: float, y: int) -> float:
    return (p - y) ** 2


def confident_no(p: float) -> float:
    if p < 0.10:
        return p + (0.65 - p) * 0.5
    return p


def source_bucket(source: str | None, source_corpus: str | None) -> str:
    return str(source or source_corpus or "unknown")


def hash_score(text: str) -> float:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(16**12 - 1)


def trimmed_mean(values: list[float]) -> float:
    if len(values) <= 2:
        return statistics.mean(values)
    xs = sorted(values)
    return statistics.mean(xs[1:-1])


def load_panels(db: Path, pilot_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    placeholders = ",".join("?" for _ in pilot_ids)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            f"""
            SELECT pc.pilot_id, pc.contract_id, pc.family, pc.p_success,
                   pc.parsed_json, c.y_known, c.source, c.source_corpus,
                   c.question
            FROM pilot_calls pc
            JOIN contracts c ON c.contract_id = pc.contract_id
            WHERE pc.schema_ok = 1
              AND pc.p_success IS NOT NULL
              AND pc.family IS NOT NULL
              AND c.y_known IN (0, 1)
              AND pc.pilot_id IN ({placeholders})
            """,
            pilot_ids,
        ).fetchall()
    finally:
        con.close()

    panels: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row["pilot_id"]), str(row["contract_id"]))
        panel = panels.setdefault(
            key,
            {
                "panel_id": f"{row['pilot_id']}|{row['contract_id']}",
                "pilot_id": str(row["pilot_id"]),
                "contract_id": str(row["contract_id"]),
                "source": source_bucket(row["source"], row["source_corpus"]),
                "question_len": len(str(row["question"] or "")),
                "y": int(row["y_known"]),
                "families": {},
                "tail": {},
                "spread": {},
                "brier_mid": {},
                "brier_width": {},
            },
        )
        family = str(row["family"])
        parsed = parse_json(row["parsed_json"])
        buy = num(parsed.get("p_buy_yes_max"))
        sell = num(parsed.get("p_sell_yes_min"))
        lo = num(parsed.get("predicted_brier_lo"))
        hi = num(parsed.get("predicted_brier_hi"))
        panel["families"][family] = float(row["p_success"])
        panel["tail"][family] = num(parsed.get("tail_insurance_premium"))
        panel["spread"][family] = None if buy is None or sell is None else max(0.0, sell - buy)
        panel["brier_mid"][family] = None if lo is None or hi is None else (lo + hi) / 2.0
        panel["brier_width"][family] = None if lo is None or hi is None else max(0.0, hi - lo)

    complete: list[dict[str, Any]] = []
    for panel in panels.values():
        if not all(family in panel["families"] for family in FAMILIES):
            continue
        if not all(panel["tail"].get(family) is not None for family in FAMILIES):
            continue
        if not all(panel["spread"].get(family) is not None for family in FAMILIES):
            continue
        if not all(panel["brier_width"].get(family) is not None for family in FAMILIES):
            continue
        probs = [float(panel["families"][family]) for family in FAMILIES]
        panel["raw_mean_p"] = statistics.mean(probs)
        panel["raw_median_p"] = statistics.median(probs)
        panel["confident_no_mean_p"] = statistics.mean(confident_no(p) for p in probs)
        panel["sigma_p"] = statistics.pstdev(probs)
        panel["avg_tail"] = statistics.mean(float(panel["tail"][family]) for family in FAMILIES)
        panel["max_tail"] = max(float(panel["tail"][family]) for family in FAMILIES)
        panel["avg_spread"] = statistics.mean(float(panel["spread"][family]) for family in FAMILIES)
        panel["avg_brier_mid"] = statistics.mean(float(panel["brier_mid"][family]) for family in FAMILIES)
        panel["avg_brier_width"] = statistics.mean(float(panel["brier_width"][family]) for family in FAMILIES)
        panel["diagnostic_composite"] = (
            panel["avg_tail"]
            + 100.0 * panel["avg_spread"]
            + 100.0 * panel["avg_brier_width"]
            + 100.0 * panel["sigma_p"]
        )
        complete.append(panel)
    complete.sort(key=lambda row: row["panel_id"])
    return complete


def source_stratified_folds(panels: list[dict[str, Any]], n_folds: int) -> dict[str, int]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in panels:
        by_source[row["source"]].append(row)
    out: dict[str, int] = {}
    for rows in by_source.values():
        for idx, row in enumerate(sorted(rows, key=lambda item: item["panel_id"])):
            out[row["panel_id"]] = idx % n_folds
    return out


def best_family(train: list[dict[str, Any]]) -> str:
    scores = {
        family: statistics.mean(brier(row["families"][family], row["y"]) for row in train)
        for family in FAMILIES
    }
    return min(scores, key=scores.get)


def source_best_map(train: list[dict[str, Any]], fallback: str) -> dict[str, str]:
    out = {"__fallback__": fallback}
    for source in sorted({row["source"] for row in train}):
        group = [row for row in train if row["source"] == source]
        if len(group) < 5:
            continue
        scores = {
            family: statistics.mean(brier(row["families"][family], row["y"]) for row in group)
            for family in FAMILIES
        }
        out[source] = min(scores, key=scores.get)
    return out


def threshold(train: list[dict[str, Any]], field: str, q: float) -> float:
    values = sorted(float(row[field]) for row in train)
    idx = min(len(values) - 1, max(0, round((len(values) - 1) * q)))
    return values[idx]


def trigger(row: dict[str, Any], policy: str, ctx: dict[str, Any]) -> bool:
    if policy.startswith("tail_high_"):
        return row["avg_tail"] >= ctx["tail_q75"]
    if policy.startswith("spread_high_"):
        return row["avg_spread"] >= ctx["spread_q75"]
    if policy.startswith("brier_width_high_"):
        return row["avg_brier_width"] >= ctx["brier_width_q75"]
    if policy.startswith("sigma_high_"):
        return row["sigma_p"] >= ctx["sigma_q75"]
    if policy.startswith("composite_high_"):
        return row["diagnostic_composite"] >= ctx["composite_q75"]
    if policy.startswith("tail_low_"):
        return row["avg_tail"] <= ctx["tail_q25"]
    if policy.startswith("hash_sham_"):
        return hash_score(row["panel_id"]) >= 0.75
    if policy.startswith("length_sham_"):
        return row["question_len"] >= ctx["question_len_q75"]
    return False


def reviewed_probability(row: dict[str, Any], reviewer: str, ctx: dict[str, Any]) -> float:
    if reviewer == "source_best":
        family = ctx["source_best"].get(row["source"], ctx["source_best"]["__fallback__"])
        return float(row["families"][family])
    if reviewer == "train_best":
        return float(row["families"][ctx["train_best"]])
    if reviewer == "raw_mean":
        return float(row["raw_mean_p"])
    if reviewer == "median":
        return float(row["raw_median_p"])
    if reviewer == "oracle_family":
        return min((float(row["families"][family]) for family in FAMILIES), key=lambda p: brier(p, row["y"]))
    raise ValueError(f"unknown reviewer: {reviewer}")


def policy_probability(row: dict[str, Any], policy: str, ctx: dict[str, Any]) -> tuple[float, bool]:
    if policy == "confident_no_forecast_all":
        return float(row["confident_no_mean_p"]), False
    if policy == "raw_mean_forecast_all":
        return float(row["raw_mean_p"]), False
    if policy == "source_best_forecast_all":
        return reviewed_probability(row, "source_best", ctx), False
    if policy == "train_best_forecast_all":
        return reviewed_probability(row, "train_best", ctx), False
    if policy == "oracle_family_review_ceiling":
        return reviewed_probability(row, "oracle_family", ctx), True

    for suffix, reviewer in (
        ("review_to_source_best", "source_best"),
        ("review_to_train_best", "train_best"),
        ("review_to_raw_mean", "raw_mean"),
        ("review_to_oracle_family", "oracle_family"),
    ):
        if policy.endswith(suffix):
            fired = trigger(row, policy, ctx)
            if fired:
                return reviewed_probability(row, reviewer, ctx), True
            return float(row["confident_no_mean_p"]), False
    raise ValueError(f"unknown policy: {policy}")


POLICIES = (
    "confident_no_forecast_all",
    "raw_mean_forecast_all",
    "source_best_forecast_all",
    "train_best_forecast_all",
    "tail_high_review_to_source_best",
    "tail_high_review_to_train_best",
    "tail_high_review_to_raw_mean",
    "spread_high_review_to_source_best",
    "brier_width_high_review_to_source_best",
    "sigma_high_review_to_source_best",
    "composite_high_review_to_source_best",
    "tail_low_review_to_source_best",
    "hash_sham_review_to_source_best",
    "length_sham_review_to_source_best",
    "tail_high_review_to_oracle_family",
    "composite_high_review_to_oracle_family",
    "oracle_family_review_ceiling",
)


def cross_validate(panels: list[dict[str, Any]], n_folds: int) -> dict[str, Any]:
    folds = source_stratified_folds(panels, n_folds)
    rows: list[dict[str, Any]] = []
    fold_contexts: dict[str, Any] = {}
    for fold in range(n_folds):
        train = [row for row in panels if folds[row["panel_id"]] != fold]
        test = [row for row in panels if folds[row["panel_id"]] == fold]
        train_best = best_family(train)
        ctx = {
            "train_best": train_best,
            "source_best": source_best_map(train, train_best),
            "tail_q25": threshold(train, "avg_tail", 0.25),
            "tail_q75": threshold(train, "avg_tail", 0.75),
            "spread_q75": threshold(train, "avg_spread", 0.75),
            "brier_width_q75": threshold(train, "avg_brier_width", 0.75),
            "sigma_q75": threshold(train, "sigma_p", 0.75),
            "composite_q75": threshold(train, "diagnostic_composite", 0.75),
            "question_len_q75": threshold(train, "question_len", 0.75),
        }
        fold_contexts[str(fold)] = {
            key: round(value, 6) if isinstance(value, float) else value
            for key, value in ctx.items()
            if key != "source_best"
        } | {"n_train": len(train), "n_test": len(test)}
        for row in test:
            for policy in POLICIES:
                p, reviewed = policy_probability(row, policy, ctx)
                rows.append(
                    {
                        "panel_id": row["panel_id"],
                        "source": row["source"],
                        "policy": policy,
                        "reviewed": reviewed,
                        "brier": brier(p, row["y"]),
                    }
                )
    return summarize(rows, fold_contexts)


def summarize(rows: list[dict[str, Any]], fold_contexts: dict[str, Any]) -> dict[str, Any]:
    by_policy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_policy[row["policy"]].append(row)

    aggregate: dict[str, Any] = {}
    for policy, policy_rows in sorted(by_policy.items()):
        review_rate = statistics.mean(1.0 if row["reviewed"] else 0.0 for row in policy_rows)
        mean_brier = statistics.mean(float(row["brier"]) for row in policy_rows)
        aggregate[policy] = {
            "n": len(policy_rows),
            "mean_brier": round(mean_brier, 6),
            "review_rate": round(review_rate, 6),
            "costed": {
                str(cost): round(mean_brier + cost * review_rate, 6)
                for cost in COSTS
            },
        }

    ref = "confident_no_forecast_all"
    ref_rows = by_policy[ref]
    ref_briers = [float(row["brier"]) for row in ref_rows]
    ref_costed = aggregate[ref]["costed"][str(PRIMARY_COST)]
    for policy, policy_rows in by_policy.items():
        candidate = [float(row["brier"]) for row in policy_rows]
        aggregate[policy]["delta_brier_vs_f100"] = round(
            aggregate[policy]["mean_brier"] - aggregate[ref]["mean_brier"], 6
        )
        aggregate[policy]["delta_costed_vs_f100_at_primary_cost"] = round(
            aggregate[policy]["costed"][str(PRIMARY_COST)] - ref_costed,
            6,
        )
        aggregate[policy]["paired_vs_f100"] = paired_permutation_test(candidate, ref_briers, n_perm=5000, seed=42)

    per_source: dict[str, dict[str, Any]] = {}
    for source in sorted({row["source"] for row in rows}):
        source_rows = [row for row in rows if row["source"] == source]
        source_by_policy: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in source_rows:
            source_by_policy[row["policy"]].append(row)
        per_source[source] = {}
        for policy, policy_rows in source_by_policy.items():
            review_rate = statistics.mean(1.0 if row["reviewed"] else 0.0 for row in policy_rows)
            mean_brier = statistics.mean(float(row["brier"]) for row in policy_rows)
            per_source[source][policy] = {
                "n": len(policy_rows),
                "mean_brier": round(mean_brier, 6),
                "review_rate": round(review_rate, 6),
                "costed_at_primary_cost": round(mean_brier + PRIMARY_COST * review_rate, 6),
            }

    best_costed = min(aggregate, key=lambda policy: aggregate[policy]["costed"][str(PRIMARY_COST)])
    return {
        "fold_contexts": fold_contexts,
        "aggregate": aggregate,
        "per_source": per_source,
        "best_costed_policy": best_costed,
        "primary_cost": PRIMARY_COST,
        "verdict": verdict(aggregate, per_source, best_costed),
    }


def verdict(aggregate: dict[str, Any], per_source: dict[str, Any], best_policy: str) -> str:
    if best_policy == "confident_no_forecast_all":
        return "review_allocation_not_supported_over_f100"
    if "oracle" in best_policy:
        return "only_oracle_review_ceiling_beats_f100"
    row = aggregate[best_policy]
    if row["delta_costed_vs_f100_at_primary_cost"] >= -0.01:
        return "review_allocation_not_promoted_small_or_negative_costed_lift"
    p_value = row["paired_vs_f100"].get("p_value")
    if p_value is None or p_value > 0.05:
        return "review_allocation_not_promoted_underpowered_or_unstable"
    for source, scores in per_source.items():
        if scores.get(best_policy, {}).get("n", 0) >= MAJOR_SOURCE_N:
            if scores[best_policy]["costed_at_primary_cost"] > scores["confident_no_forecast_all"]["costed_at_primary_cost"]:
                return "review_allocation_not_promoted_major_source_regression"
    if "sham" in best_policy or "low" in best_policy or "length" in best_policy:
        return "review_allocation_not_promoted_sham_or_inverted_trigger"
    return "review_allocation_candidate_for_prospective_confirmation"


def render_md(report: dict[str, Any]) -> str:
    cv = report["cv"]
    lines = [
        "# Diagnostic Review Allocation Audit (2026-06-03)",
        "",
        "No-call costed review-allocation audit over complete five-family public panels.",
        "",
        f"- Schema: `{report['schema']}`.",
        f"- Panels: `{report['panels']}`.",
        f"- Pilots: `{', '.join(report['pilot_ids'])}`.",
        f"- Source counts: `{json.dumps(report['source_counts'], sort_keys=True)}`.",
        f"- Primary review cost: `{cv['primary_cost']}` Brier-equivalent per reviewed row.",
        f"- Best costed policy: `{cv['best_costed_policy']}`.",
        f"- Verdict: `{cv['verdict']}`.",
        "",
        "## Aggregate",
        "",
        "| policy | mean Brier | review rate | costed @ primary | delta costed vs F100 | p vs F100 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    primary = str(cv["primary_cost"])
    for policy, row in sorted(cv["aggregate"].items(), key=lambda item: item[1]["costed"][primary]):
        p = row["paired_vs_f100"].get("p_value")
        lines.append(
            f"| `{policy}` | `{row['mean_brier']:.6f}` | `{row['review_rate']:.3f}` | "
            f"`{row['costed'][primary]:.6f}` | `{row['delta_costed_vs_f100_at_primary_cost']:+.6f}` | `{p}` |"
        )
    lines.extend(["", "## Major Source Split", ""])
    for source, scores in cv["per_source"].items():
        n = scores.get("confident_no_forecast_all", {}).get("n", 0)
        if n < MAJOR_SOURCE_N:
            continue
        lines.append(f"### {source} (`n={n}`)")
        lines.append("")
        lines.append("| policy | mean Brier | review rate | costed @ primary |")
        lines.append("|---|---:|---:|---:|")
        for policy, row in sorted(scores.items(), key=lambda item: item[1]["costed_at_primary_cost"]):
            lines.append(
                f"| `{policy}` | `{row['mean_brier']:.6f}` | `{row['review_rate']:.3f}` | "
                f"`{row['costed_at_primary_cost']:.6f}` |"
            )
        lines.append("")
    lines.extend(
        [
            "## Promotion Rule",
            "",
            "A non-oracle diagnostic review policy promotes only if it beats F100 forecast-all by at least `0.01` costed Brier at the primary nonzero review cost, paired `p<=0.05`, does not regress any major source, and beats sham/inverted triggers.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    pilot_ids = tuple(args.pilots)
    panels = load_panels(args.db, pilot_ids)
    cv = cross_validate(panels, args.folds)
    return {
        "schema": "gp245-diagnostic-review-allocation-audit-v1",
        "db": str(args.db),
        "pilot_ids": list(pilot_ids),
        "panels": len(panels),
        "source_counts": dict(Counter(row["source"] for row in panels)),
        "outcome_counts": dict(Counter(row["y"] for row in panels)),
        "cv": cv,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--pilots", nargs="+", default=list(DEFAULT_PILOTS))
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()
    report = build_report(args)
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    args.out_md.write_text(render_md(report), encoding="utf-8")
    print(json.dumps({
        "panels": report["panels"],
        "best_costed_policy": report["cv"]["best_costed_policy"],
        "verdict": report["cv"]["verdict"],
    }, indent=2))


if __name__ == "__main__":
    main()
