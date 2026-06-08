#!/usr/bin/env python3
"""Source-balanced router audit for GP-245.

No model calls. No DB mutation.

This asks whether the conditional router survives the applied-science version
of the no-poolability question: can an interpretable family router beat simple
baselines when major sources are equally represented, or was the apparent lift
source-composition dependent?
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from projects.llm_forecasting_calibration_program.tools.conditional_router_rederivation import (
    CANDIDATES,
    DEFAULT_DB,
    brier,
    hash_bucket,
    load_rows,
    route_family,
    select_candidate,
    train_router,
)


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_OUT = PROGRAM / "router_rederivation_v1/workspace"
MIN_SOURCE_N = 30
BASELINES = (
    "train_best_single",
    "confident_no_train_best_single",
    "mean_panel",
    "confident_no_mean_panel",
    "median_panel",
)
SCORE_NAMES = (
    "selected_router",
    "selected_router_confident_no",
    *BASELINES,
    "oracle_family",
)


def confident_no_discount(p: float) -> float:
    if p < 0.10:
        return p + (0.65 - p) * 0.5
    return p


def source_balanced_rows(rows: list[dict[str, Any]], min_source_n: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        source = row["source"]
        if source:
            grouped[source].append(row)
    eligible = {source: group for source, group in grouped.items() if len(group) >= min_source_n}
    if not eligible:
        return [], {}
    per_source_n = min(len(group) for group in eligible.values())
    balanced: list[dict[str, Any]] = []
    for source, group in eligible.items():
        ordered = sorted(group, key=lambda row: (hash_bucket(row["contract_id"], 10_000), row["contract_id"]))
        balanced.extend(ordered[:per_source_n])
    balanced.sort(key=lambda row: row["contract_id"])
    return balanced, {source: per_source_n for source in sorted(eligible)}


def source_stratified_cv(rows: list[dict[str, Any]], folds: int = 5) -> dict[str, Any]:
    all_scores: dict[str, list[float]] = defaultdict(list)
    per_source_scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    selected_by_fold: dict[str, str] = {}
    fold_ns: dict[str, int] = {}
    fold_sources: dict[str, dict[str, int]] = {}
    for fold in range(folds):
        train = [row for row in rows if hash_bucket(row["contract_id"], folds) != fold]
        test = [row for row in rows if hash_bucket(row["contract_id"], folds) == fold]
        if not train or not test:
            continue
        selected = select_candidate(train)
        router = train_router(train)
        selected_by_fold[str(fold)] = selected
        fold_ns[str(fold)] = len(test)
        fold_sources[str(fold)] = dict(sorted(Counter(row["source"] for row in test).items()))
        for name in SCORE_NAMES:
            values = score_values(train, test, selected, router, name)
            all_scores[name].extend(values)
        for source in sorted({row["source"] for row in test}):
            source_test = [row for row in test if row["source"] == source]
            for name in SCORE_NAMES:
                values = score_values(train, source_test, selected, router, name)
                per_source_scores[source][name].extend(values)
    selected_names = sorted({name for name in selected_by_fold.values()})
    if len(selected_names) == 1:
        selected_label = selected_names[0]
    else:
        selected_label = "selected_router"
    aggregate = {
        name: {
            "brier": round(statistics.mean(values), 6),
            "n": len(values),
        }
        for name, values in sorted(all_scores.items())
        if values
    }
    source_rows = []
    for source, source_scores in sorted(per_source_scores.items()):
        selected_values: list[float] = []
        selected_adjusted_values: list[float] = []
        for fold, selected in selected_by_fold.items():
            fold_rows = [
                row for row in rows
                if row["source"] == source and hash_bucket(row["contract_id"], folds) == int(fold)
            ]
            if fold_rows:
                train = [row for row in rows if hash_bucket(row["contract_id"], folds) != int(fold)]
                router = train_router(train)
                selected_values.extend(score_values(train, fold_rows, selected, router, "selected_router"))
                selected_adjusted_values.extend(
                    score_values(train, fold_rows, selected, router, "selected_router_confident_no")
                )
        baseline_means = {
            name: statistics.mean(values)
            for name, values in source_scores.items()
            if name in BASELINES and values
        }
        best_baseline = min(baseline_means, key=baseline_means.get)
        selected_mean = statistics.mean(selected_values)
        selected_adjusted_mean = statistics.mean(selected_adjusted_values)
        source_rows.append(
            {
                "source": source,
                "n": len(selected_values),
                "selected_brier": round(selected_mean, 6),
                "selected_confident_no_brier": round(selected_adjusted_mean, 6),
                "best_baseline": best_baseline,
                "best_baseline_brier": round(baseline_means[best_baseline], 6),
                "selected_minus_best_baseline": round(selected_mean - baseline_means[best_baseline], 6),
                "selected_confident_no_minus_best_baseline": round(
                    selected_adjusted_mean - baseline_means[best_baseline],
                    6,
                ),
                "baseline_briers": {name: round(value, 6) for name, value in sorted(baseline_means.items())},
            }
        )
    return {
        "fold_ns": fold_ns,
        "fold_sources": fold_sources,
        "selected_by_fold": selected_by_fold,
        "selected_label": selected_label,
        "aggregate_scores": aggregate,
        "per_source": source_rows,
    }


def best_family_on_train(train: list[dict[str, Any]]) -> str:
    family_scores = {}
    for family in train[0]["families"]:
        family_scores[family] = statistics.mean(brier(row["families"][family], row["y"]) for row in train)
    return min(family_scores, key=family_scores.get)


def score_values(
    train: list[dict[str, Any]],
    test: list[dict[str, Any]],
    selected_candidate: str,
    router: dict[str, Any],
    name: str,
) -> list[float]:
    if not test:
        return []
    train_best = best_family_on_train(train)
    values = []
    for row in test:
        y = row["y"]
        if name == "selected_router":
            family = route_family(router, selected_candidate, row)
            p = row["families"][family]
        elif name == "selected_router_confident_no":
            family = route_family(router, selected_candidate, row)
            p = confident_no_discount(row["families"][family])
        elif name == "train_best_single":
            p = row["families"][train_best]
        elif name == "confident_no_train_best_single":
            p = confident_no_discount(row["families"][train_best])
        elif name == "mean_panel":
            p = statistics.mean(row["families"].values())
        elif name == "confident_no_mean_panel":
            p = statistics.mean(confident_no_discount(p_raw) for p_raw in row["families"].values())
        elif name == "median_panel":
            p = statistics.median(row["families"].values())
        elif name == "oracle_family":
            p = min(row["families"].values(), key=lambda p_raw: brier(p_raw, y))
        else:
            raise ValueError(f"unknown score name: {name}")
        values.append(brier(p, y))
    return values


def oracle_headroom(rows: list[dict[str, Any]]) -> dict[str, Any]:
    oracle = []
    mean_panel = []
    best_single_by_source = {}
    for source in sorted({row["source"] for row in rows}):
        source_rows = [row for row in rows if row["source"] == source]
        family_means = {
            family: statistics.mean(brier(row["families"][family], row["y"]) for row in source_rows)
            for family in source_rows[0]["families"]
        }
        best_single_by_source[source] = min(family_means, key=family_means.get)
    for row in rows:
        y = row["y"]
        oracle.append(min(brier(p, y) for p in row["families"].values()))
        mean_panel.append(brier(statistics.mean(row["families"].values()), y))
    return {
        "oracle_family_brier": round(statistics.mean(oracle), 6),
        "mean_panel_brier": round(statistics.mean(mean_panel), 6),
        "mean_minus_oracle": round(statistics.mean(mean_panel) - statistics.mean(oracle), 6),
        "best_single_by_source": best_single_by_source,
        "interpretation": "Contract-level family choice has headroom, but a usable router must recover it without source leakage.",
    }


def verdict(cv: dict[str, Any]) -> str:
    aggregate = cv["aggregate_scores"]
    selected_score = aggregate["selected_router"]
    selected_adjusted_score = aggregate["selected_router_confident_no"]
    best_baseline = min(BASELINES, key=lambda name: aggregate[name]["brier"])
    aggregate_delta = selected_score["brier"] - aggregate[best_baseline]["brier"]
    adjusted_delta = selected_adjusted_score["brier"] - aggregate[best_baseline]["brier"]
    source_survives = cv["per_source"] and all(row["selected_minus_best_baseline"] <= 0 for row in cv["per_source"])
    adjusted_source_survives = cv["per_source"] and all(
        row["selected_confident_no_minus_best_baseline"] <= 0 for row in cv["per_source"]
    )
    if adjusted_delta < 0 and adjusted_source_survives:
        return "source_balanced_router_confident_no_variant_survives"
    if aggregate_delta < 0 and source_survives:
        return "source_balanced_router_raw_candidate_survives"
    if aggregate_delta < 0 or adjusted_delta < 0:
        return "source_balanced_router_aggregate_only_source_fragile"
    return "source_balanced_router_failed"


def build(args: argparse.Namespace) -> dict[str, Any]:
    rows = load_rows(args.db, [] if args.all_pilots else args.pilot_id)
    balanced, source_counts = source_balanced_rows(rows, args.min_source_n)
    cv = source_stratified_cv(balanced)
    return {
        "schema": "gp245-source-balanced-router-audit-v1",
        "db": str(args.db),
        "pilot_filter": "ALL" if args.all_pilots else args.pilot_id,
        "input_complete_five_contracts": len(rows),
        "eligible_source_counts": source_counts,
        "balanced_contracts": len(balanced),
        "families": list(balanced[0]["families"].keys()) if balanced else [],
        "candidate_set": list(CANDIDATES),
        "baselines": list(BASELINES),
        "source_stratified_cv": cv,
        "oracle_headroom": oracle_headroom(balanced) if balanced else {},
        "verdict": verdict(cv),
        "interpretation": (
            "This is an applied-policy stress test. A router must beat simple "
            "baselines under source-balanced folds and within each major source; "
            "otherwise no-poolability remains a mechanism lead, not a policy."
        ),
    }


def render_md(report: dict[str, Any]) -> str:
    cv = report["source_stratified_cv"]
    lines = [
        "# Source-Balanced Router Audit",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Pilot filter: `{report['pilot_filter']}`",
        f"- Input complete-five contracts: `{report['input_complete_five_contracts']}`",
        f"- Balanced contracts: `{report['balanced_contracts']}`",
        f"- Eligible source counts: `{report['eligible_source_counts']}`",
        f"- Verdict: `{report['verdict']}`",
        "",
        "## Aggregate Source-Stratified CV",
        "",
        "```json",
        json.dumps(cv.get("aggregate_scores", {}), indent=2, sort_keys=True),
        "```",
        "",
        "## Per-Source Stress",
        "",
        "| source | n | selected brier | selected+confNO brier | best baseline | baseline brier | selected minus best | selected+confNO minus best |",
        "|---|---:|---:|---:|---|---:|---:|---:|",
    ]
    for row in cv.get("per_source", []):
        lines.append(
            f"| `{row['source']}` | {row['n']} | {row['selected_brier']:.6f} | "
            f"{row['selected_confident_no_brier']:.6f} | `{row['best_baseline']}` | "
            f"{row['best_baseline_brier']:.6f} | {row['selected_minus_best_baseline']:+.6f} | "
            f"{row['selected_confident_no_minus_best_baseline']:+.6f} |"
        )
    lines.extend(
        [
            "",
            "## Fold Selection",
            "",
            "```json",
            json.dumps(
                {
                    "fold_ns": cv.get("fold_ns"),
                    "fold_sources": cv.get("fold_sources"),
                    "selected_by_fold": cv.get("selected_by_fold"),
                    "selected_label": cv.get("selected_label"),
                },
                indent=2,
                sort_keys=True,
            ),
            "```",
            "",
            "## Oracle Headroom",
            "",
            "```json",
            json.dumps(report.get("oracle_headroom", {}), indent=2, sort_keys=True),
            "```",
            "",
            "## Interpretation",
            "",
            report["interpretation"],
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--pilot-id", action="append", default=[])
    parser.add_argument("--all-pilots", action="store_true", default=True)
    parser.add_argument("--min-source-n", type=int, default=MIN_SOURCE_N)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "source_balanced_router_audit.json"
    md_path = args.out_dir / "source_balanced_router_audit.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_md(report), encoding="utf-8")
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
