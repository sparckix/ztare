#!/usr/bin/env python3
"""No-call expert-advice audit for family routing.

This tests the applied no-poolability hypothesis as an expert-advice problem:
given complete five-family panels, can a source-stratified online weighting rule
recover family-by-contract headroom better than the current confident-NO
mean-panel baseline?

No model calls. No DB mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.ztare.experiment_stats import paired_permutation_test


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = PROGRAM / "forecaster_skill_calibration_v1/workspace"
DEFAULT_JSON = DEFAULT_OUT / "expert_advice_router_audit_2026_06_03.json"
DEFAULT_MD = DEFAULT_OUT / "expert_advice_router_audit_2026_06_03.md"
DEFAULT_PILOTS = ("v28a_full__v25_external", "v28a_refill__v25_external")
FAMILIES = ("claude", "codex_55", "codex_54mini", "gemini", "deepseek")
ETAS = (0.25, 0.5, 1.0, 2.0, 4.0)
N_FOLDS = 5
BALANCED_MIN_SOURCE_N = 20


def brier(p: float, y: int) -> float:
    return (p - y) ** 2


def confident_no(p: float) -> float:
    if p < 0.10:
        return p + (0.65 - p) * 0.5
    return p


def clip_p(p: float) -> float:
    return min(0.999, max(0.001, float(p)))


def hash_bucket(text: str, modulo: int) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % modulo


def source_bucket(source: str | None, source_corpus: str | None) -> str:
    return str(source or source_corpus or "unknown")


def load_panels(db: Path, pilot_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    placeholders = ",".join("?" for _ in pilot_ids)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            f"""
            SELECT pc.pilot_id, pc.contract_id, pc.family, pc.p_success,
                   c.y_known, c.source, c.source_corpus, c.question
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
            },
        )
        family = str(row["family"])
        if family in FAMILIES:
            panel["families"][family] = clip_p(float(row["p_success"]))

    complete = [
        panel
        for panel in panels.values()
        if all(family in panel["families"] for family in FAMILIES)
    ]
    for panel in complete:
        ps = list(panel["families"].values())
        panel["mean_panel"] = statistics.mean(ps)
        panel["median_panel"] = statistics.median(ps)
        panel["confident_no_mean_panel"] = statistics.mean(confident_no(p) for p in ps)
        panel["family_briers"] = {
            family: brier(panel["families"][family], panel["y"])
            for family in FAMILIES
        }
    complete.sort(key=lambda item: item["panel_id"])
    return complete


def source_balanced_rows(rows: list[dict[str, Any]], min_source_n: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_source[row["source"]].append(row)
    eligible = {
        source: group for source, group in by_source.items() if len(group) >= min_source_n
    }
    if not eligible:
        return [], {}
    per_source_n = min(len(group) for group in eligible.values())
    balanced: list[dict[str, Any]] = []
    for source, group in eligible.items():
        ordered = sorted(group, key=lambda row: (hash_bucket(row["panel_id"], 10_000), row["panel_id"]))
        balanced.extend(ordered[:per_source_n])
    balanced.sort(key=lambda row: row["panel_id"])
    return balanced, {source: per_source_n for source in sorted(eligible)}


def expert_names() -> tuple[str, ...]:
    raw = tuple(f"family_raw:{family}" for family in FAMILIES)
    adjusted = tuple(f"family_f100:{family}" for family in FAMILIES)
    pools = ("mean_panel", "median_panel", "confident_no_mean_panel")
    return (*raw, *adjusted, *pools)


EXPERTS = expert_names()


def expert_prob(row: dict[str, Any], expert: str) -> float:
    if expert.startswith("family_raw:"):
        return float(row["families"][expert.split(":", 1)[1]])
    if expert.startswith("family_f100:"):
        return confident_no(float(row["families"][expert.split(":", 1)[1]]))
    if expert in ("mean_panel", "median_panel", "confident_no_mean_panel"):
        return float(row[expert])
    raise ValueError(f"unknown expert: {expert}")


def weighted_prob(row: dict[str, Any], weights: dict[str, float]) -> float:
    total = sum(weights.values())
    if total <= 0:
        return float(row["confident_no_mean_panel"])
    return sum(weights[expert] * expert_prob(row, expert) for expert in EXPERTS) / total


def train_static_expert(train: list[dict[str, Any]]) -> str:
    losses = {
        expert: statistics.mean(brier(expert_prob(row, expert), row["y"]) for row in train)
        for expert in EXPERTS
    }
    return min(losses, key=losses.get)


def prequential_loss(train: list[dict[str, Any]], eta: float) -> float:
    ordered = sorted(train, key=lambda row: row["panel_id"])
    weights = {expert: 1.0 for expert in EXPERTS}
    losses: list[float] = []
    for row in ordered:
        p = weighted_prob(row, weights)
        losses.append(brier(p, row["y"]))
        for expert in EXPERTS:
            loss = brier(expert_prob(row, expert), row["y"])
            weights[expert] *= math.exp(-eta * loss)
    return statistics.mean(losses) if losses else float("inf")


def train_hedge(train: list[dict[str, Any]]) -> dict[str, Any]:
    eta_scores = {eta: prequential_loss(train, eta) for eta in ETAS}
    selected_eta = min(eta_scores, key=eta_scores.get)
    weights = {expert: 1.0 for expert in EXPERTS}
    for row in sorted(train, key=lambda item: item["panel_id"]):
        for expert in EXPERTS:
            loss = brier(expert_prob(row, expert), row["y"])
            weights[expert] *= math.exp(-selected_eta * loss)
    total = sum(weights.values())
    normalized = {expert: value / total for expert, value in weights.items()}
    top_weights = sorted(normalized.items(), key=lambda item: item[1], reverse=True)[:5]
    return {
        "eta": selected_eta,
        "eta_prequential_losses": {str(k): v for k, v in eta_scores.items()},
        "weights": normalized,
        "top_weights": top_weights,
    }


def fold_assignment(rows: list[dict[str, Any]], folds: int) -> dict[str, int]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_source[row["source"]].append(row)
    assignment: dict[str, int] = {}
    for source, group in by_source.items():
        ordered = sorted(group, key=lambda row: row["panel_id"])
        for idx, row in enumerate(ordered):
            assignment[row["panel_id"]] = idx % folds
    return assignment


def policy_prob(row: dict[str, Any], policy: str, ctx: dict[str, Any]) -> float:
    if policy == "mean_panel":
        return float(row["mean_panel"])
    if policy == "median_panel":
        return float(row["median_panel"])
    if policy == "confident_no_mean_panel":
        return float(row["confident_no_mean_panel"])
    if policy == "train_best_expert":
        return expert_prob(row, ctx["train_best_expert"])
    if policy == "hedge_expert_advice":
        return weighted_prob(row, ctx["hedge"]["weights"])
    if policy == "oracle_expert":
        return min((expert_prob(row, expert) for expert in EXPERTS), key=lambda p: brier(p, row["y"]))
    raise ValueError(f"unknown policy: {policy}")


POLICIES = (
    "mean_panel",
    "median_panel",
    "confident_no_mean_panel",
    "train_best_expert",
    "hedge_expert_advice",
    "oracle_expert",
)


def evaluate(rows: list[dict[str, Any]], folds: int) -> dict[str, Any]:
    assignment = fold_assignment(rows, folds)
    scores: dict[str, list[float]] = defaultdict(list)
    per_source: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    fold_details: dict[str, Any] = {}
    for fold in range(folds):
        train = [row for row in rows if assignment[row["panel_id"]] != fold]
        test = [row for row in rows if assignment[row["panel_id"]] == fold]
        if not train or not test:
            continue
        ctx = {
            "train_best_expert": train_static_expert(train),
            "hedge": train_hedge(train),
        }
        fold_details[str(fold)] = {
            "n_train": len(train),
            "n_test": len(test),
            "test_sources": dict(sorted(Counter(row["source"] for row in test).items())),
            "train_best_expert": ctx["train_best_expert"],
            "hedge_eta": ctx["hedge"]["eta"],
            "hedge_top_weights": ctx["hedge"]["top_weights"],
        }
        for row in test:
            y = row["y"]
            for policy in POLICIES:
                score = brier(policy_prob(row, policy, ctx), y)
                scores[policy].append(score)
                per_source[row["source"]][policy].append(score)
    aggregate = {
        policy: {
            "brier": statistics.mean(values),
            "n": len(values),
        }
        for policy, values in sorted(scores.items())
        if values
    }
    source_rows = []
    for source, source_scores in sorted(per_source.items()):
        source_rows.append(
            {
                "source": source,
                "n": len(next(iter(source_scores.values()))),
                "briers": {
                    policy: statistics.mean(values)
                    for policy, values in sorted(source_scores.items())
                },
                "hedge_minus_confident_no_mean_panel": (
                    statistics.mean(source_scores["hedge_expert_advice"])
                    - statistics.mean(source_scores["confident_no_mean_panel"])
                ),
            }
        )
    return {
        "folds": fold_details,
        "aggregate_scores": aggregate,
        "per_source": source_rows,
        "paired_tests": paired_tests(scores),
    }


def paired_tests(scores: dict[str, list[float]]) -> dict[str, Any]:
    base = scores["confident_no_mean_panel"]
    out = {}
    for policy in ("train_best_expert", "hedge_expert_advice", "oracle_expert", "mean_panel"):
        candidate = scores[policy]
        out[f"{policy}_vs_confident_no_mean_panel"] = paired_permutation_test(
            candidate,
            base,
            n_perm=5000,
            seed=42,
        )
    return out


def verdict(cv: dict[str, Any], source_cv: dict[str, Any]) -> dict[str, Any]:
    agg = cv["aggregate_scores"]
    hedge_delta = (
        agg["hedge_expert_advice"]["brier"]
        - agg["confident_no_mean_panel"]["brier"]
    )
    source_deltas = [
        row["hedge_minus_confident_no_mean_panel"]
        for row in source_cv["per_source"]
    ]
    p_value = cv["paired_tests"]["hedge_expert_advice_vs_confident_no_mean_panel"]["p_value"]
    if hedge_delta <= -0.01 and p_value <= 0.05 and source_deltas and all(delta <= 0 for delta in source_deltas):
        state = "promote_expert_advice_router_candidate"
    elif hedge_delta < 0:
        state = "aggregate_positive_but_not_promoted"
    else:
        state = "expert_advice_router_fails_confident_no_baseline"
    return {
        "state": state,
        "hedge_minus_confident_no_mean_panel": hedge_delta,
        "promotion_gate": (
            "Promote only if source-stratified hedge beats confident-NO mean-panel "
            "by >=0.01 Brier, paired p<=0.05, and no eligible major-source regression."
        ),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    rows = load_panels(args.db, tuple(args.pilot_id))
    balanced, source_counts = source_balanced_rows(rows, args.min_source_n)
    cv = evaluate(rows, args.folds)
    source_cv = evaluate(balanced, args.folds) if balanced else {}
    return {
        "schema": "gp245-expert-advice-router-audit-v1",
        "db": str(args.db.relative_to(REPO)) if args.db.is_relative_to(REPO) else str(args.db),
        "pilot_ids": list(args.pilot_id),
        "input_complete_five_panels": len(rows),
        "source_counts": dict(sorted(Counter(row["source"] for row in rows).items())),
        "balanced_source_counts": source_counts,
        "balanced_complete_five_panels": len(balanced),
        "policies": list(POLICIES),
        "experts": list(EXPERTS),
        "all_rows_cv": cv,
        "source_balanced_cv": source_cv,
        "verdict": verdict(cv, source_cv if source_cv else cv),
    }


def fmt(value: Any) -> str:
    if value is None:
        return "`None`"
    if isinstance(value, float):
        return f"`{value:.6f}`"
    return f"`{value}`"


def write_report(report: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Expert-Advice Router Audit",
        "",
        f"- Input complete-five panels: `{report['input_complete_five_panels']}`",
        f"- Source counts: `{report['source_counts']}`",
        f"- Balanced complete-five panels: `{report['balanced_complete_five_panels']}`",
        f"- Balanced source counts: `{report['balanced_source_counts']}`",
        f"- Verdict: `{report['verdict']['state']}`",
        f"- Hedge minus confident-NO mean-panel: {fmt(report['verdict']['hedge_minus_confident_no_mean_panel'])}",
        f"- Promotion gate: {report['verdict']['promotion_gate']}",
        "",
        "## All Rows CV",
        "",
    ]
    lines.extend(score_lines(report["all_rows_cv"]))
    lines.extend(["", "## Source-Balanced CV", ""])
    if report["source_balanced_cv"]:
        lines.extend(score_lines(report["source_balanced_cv"]))
    else:
        lines.append("- No eligible source-balanced slice.")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This treats family forecasts and simple pools as experts. The policy "
            "is allowed to learn weights from the training fold only, and the "
            "bar is the current applied baseline: confident-NO mean-panel. "
            "Oracle-expert remains a headroom diagnostic, not a deployable "
            "policy. A positive aggregate that fails the source-balanced or "
            "paired-significance gate stays diagnostic-only.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")


def score_lines(cv: dict[str, Any]) -> list[str]:
    lines = ["### Aggregate", ""]
    for policy, row in sorted(cv["aggregate_scores"].items()):
        lines.append(f"- `{policy}`: Brier {fmt(row['brier'])}, n=`{row['n']}`")
    lines.extend(["", "### Paired Tests vs Confident-NO Mean-Panel", ""])
    for name, row in sorted(cv["paired_tests"].items()):
        lines.append(
            f"- `{name}`: observed_delta={fmt(row.get('observed_delta'))}, "
            f"p={fmt(row.get('p_value'))}, CI=[{fmt(row.get('ci_lo'))}, {fmt(row.get('ci_hi'))}]"
        )
    lines.extend(["", "### Per Source", ""])
    for row in cv["per_source"]:
        lines.append(
            f"- `{row['source']}` n=`{row['n']}` hedge-minus-confident-NO="
            f"{fmt(row['hedge_minus_confident_no_mean_panel'])}; briers=`{row['briers']}`"
        )
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--pilot-id", action="append", default=list(DEFAULT_PILOTS))
    parser.add_argument("--folds", type=int, default=N_FOLDS)
    parser.add_argument("--min-source-n", type=int, default=BALANCED_MIN_SOURCE_N)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    report = build_report(args)
    write_report(report, args.json_out, args.md_out)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
