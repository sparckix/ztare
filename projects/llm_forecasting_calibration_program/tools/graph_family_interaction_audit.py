#!/usr/bin/env python3
"""No-call graph-neighborhood audit for family x contract interaction.

This tests the applied version of the bipartite forecasting graph idea without
new model calls. Contracts are represented by their five-family probability
vector; train-fold nearest neighbours provide local family Brier history; that
history is converted into family weights for the held-out contract.

The promotion question is deliberately strict: does this topology-derived
policy beat simple complete-panel baselines, especially confident-NO mean-panel,
under source controls?
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
DEFAULT_OUT_JSON = DEFAULT_OUT / "graph_family_interaction_audit_2026_06_03.json"
DEFAULT_OUT_MD = DEFAULT_OUT / "graph_family_interaction_audit_2026_06_03.md"
DEFAULT_PILOTS = ("v28a_full__v25_external", "v28a_refill__v25_external")
FAMILIES = ("claude", "codex_55", "codex_54mini", "gemini", "deepseek")
K_NEIGHBORS = 15
WEIGHT_EPS = 1e-4
BALANCED_MIN_SOURCE_N = 20


def parse_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def brier(p: float, y: int) -> float:
    return (p - y) ** 2


def confident_no(p: float) -> float:
    if p < 0.10:
        return p + (0.65 - p) * 0.5
    return p


def trimmed_mean(values: list[float]) -> float:
    if len(values) <= 2:
        return statistics.mean(values)
    xs = sorted(values)
    return statistics.mean(xs[1:-1])


def hash_bucket(text: str, modulo: int) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % modulo


def source_bucket(source: str, source_corpus: str) -> str:
    if source:
        return source
    if source_corpus:
        return source_corpus
    return "unknown"


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
                "source": source_bucket(str(row["source"] or ""), str(row["source_corpus"] or "")),
                "y": int(row["y_known"]),
                "families": {},
                "question_len": len(str(row["question"] or "")),
            },
        )
        family = str(row["family"])
        if family in FAMILIES:
            panel["families"][family] = float(row["p_success"])

    complete: list[dict[str, Any]] = []
    for panel in panels.values():
        if not all(family in panel["families"] for family in FAMILIES):
            continue
        probs = [panel["families"][family] for family in FAMILIES]
        panel["vector"] = probs
        panel["mean_p"] = statistics.mean(probs)
        panel["median_p"] = statistics.median(probs)
        panel["trimmed_mean_p"] = trimmed_mean(probs)
        panel["confident_no_mean_p"] = statistics.mean(confident_no(p) for p in probs)
        panel["sigma_p"] = statistics.pstdev(probs)
        panel["family_briers"] = {
            family: brier(float(panel["families"][family]), int(panel["y"]))
            for family in FAMILIES
        }
        complete.append(panel)
    complete.sort(key=lambda row: row["panel_id"])
    return complete


def distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def nearest(train: list[dict[str, Any]], row: dict[str, Any], *, same_source: bool) -> list[dict[str, Any]]:
    candidates = [r for r in train if (not same_source or r["source"] == row["source"])]
    if not candidates:
        candidates = train
    scored = sorted(
        ((distance(row["vector"], r["vector"]), r["panel_id"], r) for r in candidates),
        key=lambda item: (item[0], item[1]),
    )
    return [r for _, _, r in scored[: min(K_NEIGHBORS, len(scored))]]


def hash_control_neighbors(train: list[dict[str, Any]], row: dict[str, Any], *, same_source: bool) -> list[dict[str, Any]]:
    candidates = [r for r in train if (not same_source or r["source"] == row["source"])]
    if not candidates:
        candidates = train
    scored = sorted(
        (
            (
                hashlib.sha256(f"{row['panel_id']}::{r['panel_id']}".encode("utf-8")).hexdigest(),
                r,
            )
            for r in candidates
        ),
        key=lambda item: item[0],
    )
    return [r for _, r in scored[: min(K_NEIGHBORS, len(scored))]]


def family_weights(neighbors: list[dict[str, Any]]) -> dict[str, float]:
    mean_briers = {
        family: statistics.mean(float(row["family_briers"][family]) for row in neighbors)
        for family in FAMILIES
    }
    raw = {family: 1.0 / (WEIGHT_EPS + score) for family, score in mean_briers.items()}
    total = sum(raw.values())
    return {family: value / total for family, value in raw.items()}


def weighted_panel(row: dict[str, Any], weights: dict[str, float], *, adjusted: bool) -> float:
    return sum(
        weights[family]
        * (confident_no(float(row["families"][family])) if adjusted else float(row["families"][family]))
        for family in FAMILIES
    )


def best_family(train: list[dict[str, Any]]) -> str:
    scores = {
        family: statistics.mean(float(row["family_briers"][family]) for row in train)
        for family in FAMILIES
    }
    return min(scores, key=scores.get)


def source_best_map(train: list[dict[str, Any]], fallback: str) -> dict[str, str]:
    out: dict[str, str] = {"__fallback__": fallback}
    for source in sorted({row["source"] for row in train}):
        group = [row for row in train if row["source"] == source]
        if len(group) < 5:
            continue
        scores = {
            family: statistics.mean(float(row["family_briers"][family]) for row in group)
            for family in FAMILIES
        }
        out[source] = min(scores, key=scores.get)
    return out


def policy_prob(row: dict[str, Any], policy: str, ctx: dict[str, Any]) -> float:
    if policy == "train_best_single":
        return float(row["families"][ctx["train_best"]])
    if policy == "source_best_single":
        family = ctx["source_best"].get(row["source"], ctx["source_best"]["__fallback__"])
        return float(row["families"][family])
    if policy == "mean_panel":
        return float(row["mean_p"])
    if policy == "median_panel":
        return float(row["median_p"])
    if policy == "trimmed_mean_panel":
        return float(row["trimmed_mean_p"])
    if policy == "confident_no_mean_panel":
        return float(row["confident_no_mean_p"])
    if policy == "graph_neighbor_weighted_panel":
        weights = family_weights(nearest(ctx["train"], row, same_source=False))
        return weighted_panel(row, weights, adjusted=False)
    if policy == "graph_neighbor_confident_no_panel":
        weights = family_weights(nearest(ctx["train"], row, same_source=False))
        return weighted_panel(row, weights, adjusted=True)
    if policy == "source_graph_neighbor_weighted_panel":
        weights = family_weights(nearest(ctx["train"], row, same_source=True))
        return weighted_panel(row, weights, adjusted=False)
    if policy == "source_graph_neighbor_confident_no_panel":
        weights = family_weights(nearest(ctx["train"], row, same_source=True))
        return weighted_panel(row, weights, adjusted=True)
    if policy == "hash_neighbor_confident_no_control":
        weights = family_weights(hash_control_neighbors(ctx["train"], row, same_source=False))
        return weighted_panel(row, weights, adjusted=True)
    if policy == "source_hash_neighbor_confident_no_control":
        weights = family_weights(hash_control_neighbors(ctx["train"], row, same_source=True))
        return weighted_panel(row, weights, adjusted=True)
    raise ValueError(f"unknown policy {policy}")


POLICIES = (
    "train_best_single",
    "source_best_single",
    "mean_panel",
    "median_panel",
    "trimmed_mean_panel",
    "confident_no_mean_panel",
    "graph_neighbor_weighted_panel",
    "graph_neighbor_confident_no_panel",
    "source_graph_neighbor_weighted_panel",
    "source_graph_neighbor_confident_no_panel",
    "hash_neighbor_confident_no_control",
    "source_hash_neighbor_confident_no_control",
)


def cross_validate(rows: list[dict[str, Any]], folds: int = 5) -> dict[str, Any]:
    scores: dict[str, list[float]] = defaultdict(list)
    per_source: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    fold_contexts: dict[str, Any] = {}
    for fold in range(folds):
        train = [row for row in rows if hash_bucket(row["panel_id"], folds) != fold]
        test = [row for row in rows if hash_bucket(row["panel_id"], folds) == fold]
        if not train or not test:
            continue
        train_best = best_family(train)
        ctx = {
            "train": train,
            "train_best": train_best,
            "source_best": source_best_map(train, train_best),
        }
        fold_contexts[str(fold)] = {
            "n_train": len(train),
            "n_test": len(test),
            "train_best": train_best,
            "source_best": ctx["source_best"],
        }
        for row in test:
            y = int(row["y"])
            for policy in POLICIES:
                score = brier(policy_prob(row, policy, ctx), y)
                scores[policy].append(score)
                per_source[row["source"]][policy].append(score)

    aggregate = {
        policy: {
            "brier": round(statistics.mean(vals), 6),
            "n": len(vals),
        }
        for policy, vals in sorted(scores.items())
    }
    best_policy = min(aggregate, key=lambda policy: aggregate[policy]["brier"])
    graph_policies = [p for p in POLICIES if p.startswith("graph_") or p.startswith("source_graph_")]
    best_graph_policy = min(graph_policies, key=lambda policy: aggregate[policy]["brier"])
    comparisons: dict[str, Any] = {}
    for baseline in (
        "train_best_single",
        "source_best_single",
        "mean_panel",
        "median_panel",
        "confident_no_mean_panel",
        "hash_neighbor_confident_no_control",
        "source_hash_neighbor_confident_no_control",
    ):
        comparisons[f"{best_graph_policy}_minus_{baseline}"] = paired_permutation_test(
            scores[best_graph_policy], scores[baseline], n_perm=5000, seed=42
        )

    source_rows = []
    for source, source_scores in sorted(per_source.items()):
        source_aggregate = {
            policy: round(statistics.mean(vals), 6)
            for policy, vals in source_scores.items()
            if vals
        }
        source_rows.append(
            {
                "source": source,
                "n": len(next(iter(source_scores.values()))) if source_scores else 0,
                "best_policy": min(source_aggregate, key=source_aggregate.get),
                "best_graph_policy": min(graph_policies, key=lambda p: source_aggregate[p]),
                "scores": source_aggregate,
            }
        )

    return {
        "fold_contexts": fold_contexts,
        "aggregate": aggregate,
        "best_policy": best_policy,
        "best_graph_policy": best_graph_policy,
        "best_graph_comparisons": comparisons,
        "per_source": source_rows,
    }


def balanced_large_source_subset(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_source[row["source"]].append(row)
    eligible = {
        source: sorted(source_rows, key=lambda r: r["panel_id"])
        for source, source_rows in by_source.items()
        if len(source_rows) >= BALANCED_MIN_SOURCE_N
    }
    if len(eligible) < 2:
        return []
    cap = min(len(source_rows) for source_rows in eligible.values())
    out: list[dict[str, Any]] = []
    for source, source_rows in eligible.items():
        ranked = sorted(
            source_rows,
            key=lambda r: hashlib.sha256(f"balanced::{source}::{r['panel_id']}".encode("utf-8")).hexdigest(),
        )
        out.extend(ranked[:cap])
    return sorted(out, key=lambda r: r["panel_id"])


def interpret(cv: dict[str, Any]) -> str:
    aggregate = cv["aggregate"]
    best_graph = cv["best_graph_policy"]
    graph_brier = aggregate[best_graph]["brier"]
    confident = aggregate["confident_no_mean_panel"]["brier"]
    hash_control = min(
        aggregate["hash_neighbor_confident_no_control"]["brier"],
        aggregate["source_hash_neighbor_confident_no_control"]["brier"],
    )
    per_source = cv["per_source"]
    source_wins = sum(1 for row in per_source if row["best_policy"] == row["best_graph_policy"])
    if graph_brier < confident and graph_brier < hash_control and source_wins >= 2:
        return "graph_neighbor_policy_candidate_survives_initial_controls"
    if graph_brier < confident:
        return "graph_neighbor_policy_suggestive_but_source_or_hash_control_fragile"
    return "graph_neighbor_policy_not_supported_over_confident_no_mean_panel"


def build_report(db: Path, pilot_ids: tuple[str, ...]) -> dict[str, Any]:
    rows = load_panels(db, pilot_ids)
    cv = cross_validate(rows)
    balanced_rows = balanced_large_source_subset(rows)
    balanced_cv = cross_validate(balanced_rows) if balanced_rows else None
    return {
        "schema": "graph-family-interaction-audit-v1",
        "db": str(db),
        "pilot_ids": list(pilot_ids),
        "rows": len(rows),
        "families": list(FAMILIES),
        "k_neighbors": K_NEIGHBORS,
        "source_counts": dict(sorted(Counter(row["source"] for row in rows).items())),
        "outcome_counts": dict(sorted(Counter(str(row["y"]) for row in rows).items())),
        "balanced_large_source": {
            "min_source_n": BALANCED_MIN_SOURCE_N,
            "rows": len(balanced_rows),
            "source_counts": dict(sorted(Counter(row["source"] for row in balanced_rows).items())),
            "cv": balanced_cv,
            "interpretation": interpret(balanced_cv) if balanced_cv else "not_enough_large_sources",
        },
        "methods": {
            "contract_embedding": "five-family p_success vector on complete panels",
            "graph_neighborhood": "Euclidean nearest train-fold contract vectors",
            "family_weights": "inverse mean neighbor Brier per family, normalized",
            "controls": [
                "train_best_single",
                "source_best_single",
                "mean_panel",
                "median_panel",
                "confident_no_mean_panel",
                "hash-neighbor controls using same train folds",
            ],
        },
        "cv": cv,
        "interpretation": interpret(cv),
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# Graph Family Interaction Audit",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Rows: `{report['rows']}`",
        f"- Pilot IDs: `{report['pilot_ids']}`",
        f"- Source counts: `{report['source_counts']}`",
        f"- Outcome counts: `{report['outcome_counts']}`",
        f"- k-neighbors: `{report['k_neighbors']}`",
        f"- Best policy: `{report['cv']['best_policy']}`",
        f"- Best graph policy: `{report['cv']['best_graph_policy']}`",
        f"- Interpretation: `{report['interpretation']}`",
        "",
        "## Aggregate CV Scores",
        "",
        "```json",
        json.dumps(report["cv"]["aggregate"], indent=2, sort_keys=True),
        "```",
        "",
        "## Best Graph Comparisons",
        "",
        "```json",
        json.dumps(report["cv"]["best_graph_comparisons"], indent=2, sort_keys=True),
        "```",
        "",
        "## Per Source",
        "",
        "```json",
        json.dumps(report["cv"]["per_source"], indent=2, sort_keys=True),
        "```",
        "",
        "## Balanced Large-Source CV",
        "",
        "```json",
        json.dumps(report["balanced_large_source"], indent=2, sort_keys=True),
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--pilot-ids", default=",".join(DEFAULT_PILOTS))
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()
    pilot_ids = tuple(part.strip() for part in args.pilot_ids.split(",") if part.strip())
    report = build_report(args.db, pilot_ids)
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    args.out_md.write_text(render_md(report))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
