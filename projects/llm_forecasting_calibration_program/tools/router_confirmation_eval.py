#!/usr/bin/env python3
"""Evaluate the registered F107 conditional router against master-DB rows."""
from __future__ import annotations

import argparse
import json
import math
import random
import sqlite3
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_PILOTS = ("v28a_full__v25_external", "v28a_refill__v25_external")
TRIO = ("claude", "codex_55", "codex_54mini")


def brier(p: float, y: int) -> float:
    return (p - y) ** 2


def paired_permutation_p(deltas: list[float], *, n_iter: int = 10000, seed: int = 107) -> float:
    if not deltas:
        return 1.0
    observed = abs(sum(deltas) / len(deltas))
    rng = random.Random(seed)
    extreme = 0
    for _ in range(n_iter):
        mean = sum(d if rng.random() < 0.5 else -d for d in deltas) / len(deltas)
        if abs(mean) >= observed:
            extreme += 1
    return (extreme + 1) / (n_iter + 1)


def load_rows(db: Path, pilot_ids: list[str]) -> dict[str, dict[str, Any]]:
    where = ""
    params: list[str] = []
    if pilot_ids:
        where = "AND pc.pilot_id IN (%s)" % ",".join("?" for _ in pilot_ids)
        params.extend(pilot_ids)

    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute(
        f"""
        SELECT pc.contract_id, pc.family, pc.p_success, c.y_known,
               c.source_corpus, c.source, c.horizon
        FROM pilot_calls pc
        JOIN contracts c ON c.contract_id = pc.contract_id
        WHERE pc.schema_ok = 1
          AND pc.p_success IS NOT NULL
          AND c.y_known IS NOT NULL
          {where}
        """,
        params,
    )
    by_contract: dict[str, dict[str, Any]] = defaultdict(lambda: {"families": {}, "meta": {}})
    for cid, family, p_success, y_known, source_corpus, source, horizon in cur.fetchall():
        by_contract[cid]["families"][str(family)] = float(p_success)
        by_contract[cid]["y"] = int(y_known)
        by_contract[cid]["meta"] = {
            "source_corpus": source_corpus,
            "source": source,
            "horizon": horizon,
        }
    con.close()
    return dict(by_contract)


def panel_sigma(ps: list[float]) -> float:
    if len(ps) < 2:
        return 0.0
    return statistics.pstdev(ps)


def f107_route(families: dict[str, float]) -> tuple[str, float] | None:
    if not families:
        return None
    sigma = panel_sigma(list(families.values()))
    if sigma < 0.073:
        if "claude" in families:
            return ("low_disagreement_claude", families["claude"])
    if sigma < 0.13:
        trio = [families[f] for f in TRIO if f in families]
        if trio:
            return ("medium_disagreement_trio_median", statistics.median(trio))
    if "gemini" in families:
        return ("high_disagreement_gemini", families["gemini"])
    if "claude" in families:
        return ("fallback_claude", families["claude"])
    fam = sorted(families)[0]
    return (f"fallback_{fam}", families[fam])


def score(by_contract: dict[str, dict[str, Any]]) -> dict[str, Any]:
    shared = {cid: row for cid, row in by_contract.items() if len(row["families"]) >= 2}
    complete5 = {cid: row for cid, row in by_contract.items() if len(row["families"]) >= 5}
    cohort = complete5 if complete5 else shared

    per_family: dict[str, list[float]] = defaultdict(list)
    rows = []
    for cid, row in cohort.items():
        y = row["y"]
        families = row["families"]
        for family, p in families.items():
            per_family[family].append(brier(p, y))
        route = f107_route(families)
        if route is None:
            continue
        route_name, route_p = route
        ps = list(families.values())
        rows.append(
            {
                "contract_id": cid,
                "y": y,
                "sigma": panel_sigma(ps),
                "route": route_name,
                "f107": brier(route_p, y),
                "mean": brier(sum(ps) / len(ps), y),
                "median": brier(statistics.median(ps), y),
                "family_briers": {family: brier(p, y) for family, p in families.items()},
            }
        )

    family_mean = {
        family: sum(values) / len(values)
        for family, values in sorted(per_family.items())
        if values
    }
    best_family = min(family_mean, key=family_mean.get) if family_mean else None
    route_counts: dict[str, int] = defaultdict(int)
    bucket_counts = {"low": 0, "medium": 0, "high": 0}
    for row in rows:
        route_counts[row["route"]] += 1
        if row["sigma"] < 0.073:
            bucket_counts["low"] += 1
        elif row["sigma"] < 0.13:
            bucket_counts["medium"] += 1
        else:
            bucket_counts["high"] += 1

    comparisons: dict[str, dict[str, float]] = {}
    baselines = ["mean", "median"]
    if best_family:
        baselines.append(f"best_single:{best_family}")

    for baseline in baselines:
        if baseline.startswith("best_single:"):
            family = baseline.split(":", 1)[1]
            deltas = [
                row["f107"] - row["family_briers"][family]
                for row in rows
                if family in row["family_briers"]
            ]
        else:
            deltas = [row["f107"] - row[baseline] for row in rows]
        comparisons[baseline] = {
            "delta_brier": sum(deltas) / len(deltas) if deltas else math.nan,
            "p_perm": paired_permutation_p(deltas) if deltas else math.nan,
            "n": len(deltas),
        }

    return {
        "schema": "router-confirmation-eval-v1",
        "cohort": "complete5" if complete5 else "shared2plus",
        "n_contracts": len(cohort),
        "n_shared2plus": len(shared),
        "n_complete5": len(complete5),
        "family_brier": family_mean,
        "best_single_family": best_family,
        "f107_brier": sum(row["f107"] for row in rows) / len(rows) if rows else math.nan,
        "mean_panel_brier": sum(row["mean"] for row in rows) / len(rows) if rows else math.nan,
        "median_panel_brier": sum(row["median"] for row in rows) / len(rows) if rows else math.nan,
        "route_counts": dict(route_counts),
        "bucket_counts": bucket_counts,
        "comparisons": comparisons,
    }


def write_report(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "router_confirmation_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Router Confirmation Report",
        "",
        f"- Cohort: `{result['cohort']}`",
        f"- Contracts: {result['n_contracts']}",
        f"- Complete five-family contracts: {result['n_complete5']}",
        f"- F107 Brier: {result['f107_brier']:.4f}",
        f"- Mean-panel Brier: {result['mean_panel_brier']:.4f}",
        f"- Median-panel Brier: {result['median_panel_brier']:.4f}",
        f"- Best single family: `{result['best_single_family']}`",
        "",
        "## Bucket Counts",
        "",
    ]
    for key, value in result["bucket_counts"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Comparisons", ""])
    for name, comp in result["comparisons"].items():
        lines.append(
            f"- F107 minus `{name}`: delta={comp['delta_brier']:+.4f}, "
            f"p_perm={comp['p_perm']:.4f}, n={comp['n']}"
        )
    lines.append("")
    (out_dir / "router_confirmation_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--pilot-id", action="append", default=[])
    parser.add_argument("--all-pilots", action="store_true")
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()

    pilot_ids = [] if args.all_pilots else (args.pilot_id or list(DEFAULT_PILOTS))
    result = score(load_rows(args.db, pilot_ids))
    result["pilot_filter"] = "ALL" if args.all_pilots else pilot_ids
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.out_dir:
        write_report(result, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

