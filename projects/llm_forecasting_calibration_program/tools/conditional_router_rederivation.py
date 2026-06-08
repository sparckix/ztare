#!/usr/bin/env python3
"""Analysis-first router rederivation for GP-245 no-poolability.

This is deliberately small and interpretable. It tests whether the
family-by-contract interaction evidence can be converted into a frozen router
without new model calls or black-box fitting.
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
from typing import Any, Callable

from src.ztare.experiment_stats import paired_permutation_test


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_PILOTS = ("v28a_full__v25_external", "v28a_refill__v25_external")
FAMILIES = ("claude", "codex_55", "codex_54mini", "gemini", "deepseek")
CANDIDATES = (
    "global_best_family",
    "source_best_family",
    "sigma_bucket_best_family",
    "source_sigma_best_family",
)
BASELINES = ("train_best_single", "mean_panel", "median_panel")
SIGMA_LOW = 0.073
SIGMA_MEDIUM = 0.13
MIN_BUCKET_N = 8
MIN_SOURCE_LOO_N = 5


def brier(p: float, y: int) -> float:
    return (p - y) ** 2


def hash_bucket(text: str, modulo: int) -> int:
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % modulo


def sigma_bucket(row: dict[str, Any]) -> str:
    sigma = statistics.pstdev(list(row["families"].values()))
    if sigma < SIGMA_LOW:
        return "low"
    if sigma < SIGMA_MEDIUM:
        return "medium"
    return "high"


def load_rows(db: Path, pilot_ids: list[str]) -> list[dict[str, Any]]:
    where = ""
    params: list[str] = []
    if pilot_ids:
        where = "AND pc.pilot_id IN (%s)" % ",".join("?" for _ in pilot_ids)
        params.extend(pilot_ids)

    con = sqlite3.connect(db)
    cur = con.cursor()
    by_contract: dict[str, dict[str, Any]] = {}
    cur.execute(
        f"""
        SELECT pc.contract_id, pc.family, pc.p_success, c.y_known,
               c.source, c.source_corpus, c.horizon
        FROM pilot_calls pc
        JOIN contracts c ON c.contract_id = pc.contract_id
        WHERE pc.schema_ok = 1
          AND pc.p_success IS NOT NULL
          AND c.y_known IS NOT NULL
          {where}
        """,
        params,
    )
    for cid, family, p_success, y_known, source, source_corpus, horizon in cur.fetchall():
        row = by_contract.setdefault(
            str(cid),
            {
                "contract_id": str(cid),
                "families": {},
                "y": int(y_known),
                "source": source or "",
                "source_corpus": source_corpus or "",
                "horizon": horizon or "",
            },
        )
        row["families"][str(family)] = float(p_success)
    con.close()

    rows = [
        row
        for row in by_contract.values()
        if all(family in row["families"] for family in FAMILIES)
    ]
    rows.sort(key=lambda row: row["contract_id"])
    return rows


def mean_brier_for_family(rows: list[dict[str, Any]], family: str) -> float:
    return statistics.mean(brier(row["families"][family], row["y"]) for row in rows)


def best_family(rows: list[dict[str, Any]]) -> str:
    return min(FAMILIES, key=lambda family: mean_brier_for_family(rows, family))


def family_map(
    rows: list[dict[str, Any]],
    key_fn: Callable[[dict[str, Any]], Any],
    *,
    min_n: int = MIN_BUCKET_N,
) -> dict[str, str]:
    grouped: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[key_fn(row)].append(row)
    out: dict[str, str] = {}
    for key, group in grouped.items():
        if len(group) >= min_n:
            out[str(key)] = best_family(group)
    return out


def train_router(train: list[dict[str, Any]]) -> dict[str, Any]:
    global_best = best_family(train)
    source_best = family_map(train, lambda row: row["source"])
    sigma_best = family_map(train, sigma_bucket)
    source_sigma_best = family_map(train, lambda row: f"{row['source']}|{sigma_bucket(row)}")
    return {
        "global_best_family": global_best,
        "source_best_family": source_best,
        "sigma_bucket_best_family": sigma_best,
        "source_sigma_best_family": source_sigma_best,
    }


def route_family(router: dict[str, Any], candidate: str, row: dict[str, Any]) -> str:
    global_best = router["global_best_family"]
    source_key = row["source"]
    sigma_key = sigma_bucket(row)
    source_sigma_key = f"{source_key}|{sigma_key}"

    if candidate == "global_best_family":
        return global_best
    if candidate == "source_best_family":
        return router["source_best_family"].get(source_key, global_best)
    if candidate == "sigma_bucket_best_family":
        return router["sigma_bucket_best_family"].get(sigma_key, global_best)
    if candidate == "source_sigma_best_family":
        return router["source_sigma_best_family"].get(
            source_sigma_key,
            router["source_best_family"].get(
                source_key,
                router["sigma_bucket_best_family"].get(sigma_key, global_best),
            ),
        )
    raise ValueError(f"unknown candidate: {candidate}")


def scores_for(
    train: list[dict[str, Any]],
    test: list[dict[str, Any]],
    candidate: str,
) -> tuple[float, list[float], Counter[str]]:
    router = train_router(train)
    values: list[float] = []
    routes: Counter[str] = Counter()
    for row in test:
        if candidate in CANDIDATES:
            family = route_family(router, candidate, row)
            p = row["families"][family]
            routes[family] += 1
        elif candidate == "train_best_single":
            family = router["global_best_family"]
            p = row["families"][family]
            routes[family] += 1
        elif candidate == "mean_panel":
            p = statistics.mean(row["families"].values())
            routes["mean_panel"] += 1
        elif candidate == "median_panel":
            p = statistics.median(row["families"].values())
            routes["median_panel"] += 1
        elif candidate == "oracle_family":
            family, p = min(
                row["families"].items(),
                key=lambda item: brier(item[1], row["y"]),
            )
            routes[family] += 1
        elif candidate in FAMILIES:
            p = row["families"][candidate]
            routes[candidate] += 1
        else:
            raise ValueError(f"unknown score candidate: {candidate}")
        values.append(brier(p, row["y"]))
    return (statistics.mean(values), values, routes)


def candidate_table(train: list[dict[str, Any]], test: list[dict[str, Any]]) -> dict[str, Any]:
    names = [*CANDIDATES, *BASELINES, "oracle_family", *FAMILIES]
    out: dict[str, Any] = {}
    for name in names:
        mean_score, values, routes = scores_for(train, test, name)
        out[name] = {
            "brier": round(mean_score, 6),
            "n": len(values),
            "route_counts": dict(sorted(routes.items())),
        }
    return out


def select_candidate(train: list[dict[str, Any]]) -> str:
    scores = {
        name: scores_for(train, train, name)[0]
        for name in CANDIDATES
    }
    return min(scores, key=scores.get)


def paired_comparisons(
    train: list[dict[str, Any]],
    test: list[dict[str, Any]],
    selected: str,
) -> dict[str, Any]:
    _, selected_values, _ = scores_for(train, test, selected)
    out: dict[str, Any] = {}
    for baseline in BASELINES:
        _, baseline_values, _ = scores_for(train, test, baseline)
        perm = paired_permutation_test(selected_values, baseline_values, n_perm=5000, seed=42)
        out[baseline] = {
            "selected_minus_baseline": perm,
            "selected_brier": round(statistics.mean(selected_values), 6),
            "baseline_brier": round(statistics.mean(baseline_values), 6),
            "delta_brier": round(statistics.mean(selected_values) - statistics.mean(baseline_values), 6),
        }
    return out


def deterministic_split(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train: list[dict[str, Any]] = []
    holdout: list[dict[str, Any]] = []
    for row in rows:
        if hash_bucket(row["contract_id"], 10) < 7:
            train.append(row)
        else:
            holdout.append(row)
    return train, holdout


def cross_validation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values: dict[str, list[float]] = defaultdict(list)
    fold_ns: dict[str, int] = {}
    for fold in range(5):
        train = [row for row in rows if hash_bucket(row["contract_id"], 5) != fold]
        test = [row for row in rows if hash_bucket(row["contract_id"], 5) == fold]
        fold_ns[str(fold)] = len(test)
        for name in [*CANDIDATES, *BASELINES]:
            _, row_scores, _ = scores_for(train, test, name)
            values[name].extend(row_scores)
    return {
        "fold_ns": fold_ns,
        "scores": {
            name: {
                "brier": round(statistics.mean(scores), 6),
                "n": len(scores),
            }
            for name, scores in sorted(values.items())
        },
    }


def source_leave_one_out(rows: list[dict[str, Any]], selected: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    sources = sorted({row["source"] for row in rows})
    for source in sources:
        test = [row for row in rows if row["source"] == source]
        if len(test) < MIN_SOURCE_LOO_N:
            continue
        train = [row for row in rows if row["source"] != source]
        if not train:
            continue
        table = candidate_table(train, test)
        selected_brier = table[selected]["brier"]
        baseline_briers = {name: table[name]["brier"] for name in BASELINES}
        best_baseline = min(baseline_briers, key=baseline_briers.get)
        out.append(
            {
                "source": source,
                "n": len(test),
                "selected": selected,
                "selected_brier": selected_brier,
                "best_baseline": best_baseline,
                "best_baseline_brier": baseline_briers[best_baseline],
                "selected_minus_best_baseline": round(
                    selected_brier - baseline_briers[best_baseline],
                    6,
                ),
                "scores": {
                    key: table[key]["brier"]
                    for key in [selected, *BASELINES]
                },
            }
        )
    return out


def verdict(
    holdout_comparisons: dict[str, Any],
    source_loo: list[dict[str, Any]],
) -> str:
    beats_train_best = holdout_comparisons["train_best_single"]["delta_brier"] <= -0.01
    beats_mean = holdout_comparisons["mean_panel"]["delta_brier"] < 0
    beats_median = holdout_comparisons["median_panel"]["delta_brier"] < 0
    source_survives = bool(source_loo) and all(
        row["selected_minus_best_baseline"] <= 0 for row in source_loo
    )
    if beats_train_best and beats_mean and beats_median and source_survives:
        return "router_candidate_passes_holdout_and_source_loo"
    if beats_train_best and beats_mean and beats_median:
        return "router_candidate_holdout_positive_source_loo_failed"
    return "router_candidate_failed_holdout"


def build_report(db: Path, pilot_ids: list[str]) -> dict[str, Any]:
    rows = load_rows(db, pilot_ids)
    train, holdout = deterministic_split(rows)
    selected = select_candidate(train)
    train_table = candidate_table(train, train)
    holdout_table = candidate_table(train, holdout)
    comparisons = paired_comparisons(train, holdout, selected)
    loo = source_leave_one_out(rows, selected)
    selected_delta_vs_oracle = round(
        holdout_table[selected]["brier"] - holdout_table["oracle_family"]["brier"],
        6,
    )
    return {
        "schema": "gp245-conditional-router-rederivation-v1",
        "db": str(db),
        "pilot_filter": "ALL" if not pilot_ids else pilot_ids,
        "cohort": "complete_five_family_contracts",
        "n_contracts": len(rows),
        "families": list(FAMILIES),
        "split": {
            "method": "sha256(contract_id) mod 10; train buckets 0-6, holdout buckets 7-9",
            "train_n": len(train),
            "holdout_n": len(holdout),
        },
        "candidate_set": list(CANDIDATES),
        "baselines": list(BASELINES),
        "selected_candidate": selected,
        "verdict": verdict(comparisons, loo),
        "train_scores": train_table,
        "holdout_scores": holdout_table,
        "holdout_comparisons": comparisons,
        "source_leave_one_out": loo,
        "cross_validation": cross_validation(rows),
        "oracle_gap_on_holdout": {
            "selected_minus_oracle_family": selected_delta_vs_oracle,
            "interpretation": "Remaining contract-level family-selection headroom after the interpretable router.",
        },
        "source_counts": dict(sorted(Counter(row["source"] for row in rows).items())),
        "sigma_bucket_counts": dict(sorted(Counter(sigma_bucket(row) for row in rows).items())),
        "interpretation": (
            "The no-poolability signal is real enough to justify routing research, "
            "but deployment routing is promoted only if the selected interpretable "
            "candidate beats train-best, mean, and median on holdout and survives "
            "source leave-one-out."
        ),
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "conditional_router_rederivation_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    selected = report["selected_candidate"]
    lines = [
        "# Conditional Router Rederivation Report",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Cohort: `{report['cohort']}`",
        f"- Contracts: {report['n_contracts']}",
        f"- Train / holdout: {report['split']['train_n']} / {report['split']['holdout_n']}",
        f"- Selected candidate: `{selected}`",
        f"- Verdict: `{report['verdict']}`",
        "",
        "## Holdout Scores",
        "",
    ]
    for name in [selected, *BASELINES, "oracle_family", *FAMILIES]:
        item = report["holdout_scores"].get(name)
        if item:
            lines.append(f"- `{name}`: Brier={item['brier']:.4f}, n={item['n']}")

    lines.extend(["", "## Holdout Comparisons", ""])
    for baseline, comp in report["holdout_comparisons"].items():
        perm = comp["selected_minus_baseline"]
        lines.append(
            f"- `{selected}` minus `{baseline}`: delta={comp['delta_brier']:+.4f}, "
            f"p={perm.get('p_value')}, n={perm.get('n_paired')}"
        )

    lines.extend(["", "## Source Leave-One-Out", ""])
    for row in report["source_leave_one_out"]:
        lines.append(
            f"- `{row['source']}` n={row['n']}: `{selected}` minus best baseline "
            f"({row['best_baseline']}) = {row['selected_minus_best_baseline']:+.4f}"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            report["interpretation"],
            "",
            "A positive holdout result without source leave-one-out survival is a "
            "research lead, not a deployment claim.",
            "",
        ]
    )
    (out_dir / "conditional_router_rederivation_report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--pilot-id", action="append", default=[])
    parser.add_argument("--all-pilots", action="store_true")
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()

    pilot_ids = [] if args.all_pilots else (args.pilot_id or list(DEFAULT_PILOTS))
    report = build_report(args.db, pilot_ids)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.out_dir:
        write_outputs(report, args.out_dir)
    return 0 if report["n_contracts"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
