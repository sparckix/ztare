#!/usr/bin/env python3
"""Adversarial missing-band sensitivity for GP-245 Law 3 Stage C.

The Stage-C base-rate repair joins a pre-outcome market probability for 51/80
contracts in the cutoff-validity panel. This tool asks a narrower truth
question: if the 29 missing contracts had any possible base-rate band, could
that erase the base-rate-matched pre/post effect?

No model calls and no DB mutation.
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import sqlite3
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_JOIN_REPORT = WORKSPACE / "cutoff_stage_c_base_rate_join_report.json"
DEFAULT_OUT = WORKSPACE
PILOT_ID = "cutoff_stage_b_panel_v1"
BANDS = ("0.00_0.20", "0.20_0.40", "0.40_0.60", "0.60_0.80", "0.80_1.00")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_calls(db: Path, contract_ids: list[str]) -> list[dict[str, Any]]:
    if not contract_ids:
        return []
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in contract_ids)
    rows = [
        dict(row)
        for row in con.execute(
            f"""
            SELECT contract_id, family, brier, schema_ok
            FROM pilot_calls
            WHERE pilot_id = ?
              AND contract_id IN ({placeholders})
              AND brier IS NOT NULL
              AND schema_ok = 1
            """,
            (PILOT_ID, *contract_ids),
        )
    ]
    con.close()
    return rows


def paired_delta(rows: list[dict[str, Any]], calls: list[dict[str, Any]]) -> dict[str, Any]:
    meta = {str(row["contract_id"]): row for row in rows}
    cells: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    for call in calls:
        row = meta.get(str(call["contract_id"]))
        if not row:
            continue
        band = row.get("base_rate_band")
        if not band or band == "missing":
            continue
        key = (
            str(call["family"]),
            str(row["stratum_key"]),
            str(band),
            str(row["cutoff_relation"]),
        )
        cells[key].append(float(call["brier"]))

    paired_pre: list[float] = []
    paired_post: list[float] = []
    prefixes = sorted({key[:-1] for key in cells})
    for prefix in prefixes:
        pre = cells.get((*prefix, "pre_cutoff"), [])
        post = cells.get((*prefix, "post_cutoff"), [])
        if pre and post:
            paired_pre.append(statistics.mean(pre))
            paired_post.append(statistics.mean(post))

    if not paired_pre:
        return {"paired_cells": 0, "post_minus_pre_brier": None}
    diffs = [post - pre for pre, post in zip(paired_pre, paired_post)]
    return {
        "paired_cells": len(paired_pre),
        "post_minus_pre_brier": round(statistics.mean(diffs), 6),
        "pre_mean": round(statistics.mean(paired_pre), 6),
        "post_mean": round(statistics.mean(paired_post), 6),
    }


def apply_assignment(joined: list[dict[str, Any]], missing: list[dict[str, Any]], assignment: dict[str, str]) -> list[dict[str, Any]]:
    out = [dict(row) for row in joined]
    for row in missing:
        item = dict(row)
        item["base_rate_band"] = assignment[str(row["contract_id"])]
        item["base_rate_provenance"] = "sensitivity_assigned_unknown"
        out.append(item)
    return out


def score_assignment(
    joined: list[dict[str, Any]],
    missing: list[dict[str, Any]],
    calls: list[dict[str, Any]],
    assignment: dict[str, str],
) -> float:
    effect = paired_delta(apply_assignment(joined, missing, assignment), calls)
    delta = effect["post_minus_pre_brier"]
    if delta is None:
        return float("inf")
    return float(delta)


def grouped_assignments(missing: list[dict[str, Any]], *, seed: int, starts: int) -> list[dict[str, str]]:
    """Generate band assignments at the missing stratum/relation level.

    Individual missing-row coordinate descent is overkill and slow. The paired
    test aggregates through stratum/relation/band cells, so assigning at that
    grouped level is the relevant adversarial sensitivity.
    """
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in missing:
        groups[(str(row["stratum_key"]), str(row["cutoff_relation"]))].append(str(row["contract_id"]))
    group_keys = sorted(groups)
    assignments: list[dict[str, str]] = []

    def expand(group_assignment: dict[tuple[str, str], str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for key, ids in groups.items():
            for cid in ids:
                out[cid] = group_assignment[key]
        return out

    for band in BANDS:
        assignments.append(expand({key: band for key in group_keys}))

    total = len(BANDS) ** len(group_keys)
    if total <= starts:
        for combo in itertools.product(BANDS, repeat=len(group_keys)):
            assignments.append(expand(dict(zip(group_keys, combo))))
    else:
        rng = random.Random(seed)
        seen = set()
        while len(seen) < starts:
            combo = tuple(rng.choice(BANDS) for _ in group_keys)
            if combo in seen:
                continue
            seen.add(combo)
            assignments.append(expand(dict(zip(group_keys, combo))))
    return assignments


def adversarial_search(
    joined: list[dict[str, Any]],
    missing: list[dict[str, Any]],
    calls: list[dict[str, Any]],
    *,
    direction: str,
    seed: int,
    starts: int,
) -> dict[str, Any]:
    best_assignment: dict[str, str] | None = None
    best_delta: float | None = None
    tested = 0
    for assignment in grouped_assignments(missing, seed=seed, starts=starts):
        tested += 1
        delta = score_assignment(joined, missing, calls, assignment)
        if best_delta is None:
            best_delta = delta
            best_assignment = assignment
        elif direction == "min" and delta < best_delta:
            best_delta = delta
            best_assignment = assignment
        elif direction == "max" and delta > best_delta:
            best_delta = delta
            best_assignment = assignment

    assert best_assignment is not None
    scored_rows = apply_assignment(joined, missing, best_assignment)
    effect = paired_delta(scored_rows, calls)
    return {
        "effect": effect,
        "assignments_tested": tested,
        "assignment_band_counts": dict(Counter(best_assignment.values())),
        "assignment_by_relation": {
            relation: dict(Counter(best_assignment[str(row["contract_id"])] for row in missing if row["cutoff_relation"] == relation))
            for relation in sorted({str(row["cutoff_relation"]) for row in missing})
        },
    }


def missing_profile(missing: list[dict[str, Any]], calls: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = defaultdict(list)
    for call in calls:
        by_id[str(call["contract_id"])].append(float(call["brier"]))
    relation_values: dict[str, list[float]] = defaultdict(list)
    stratum_counts = Counter()
    for row in missing:
        vals = by_id.get(str(row["contract_id"]), [])
        if vals:
            relation_values[str(row["cutoff_relation"])].append(statistics.mean(vals))
        stratum_counts[f"{row['cutoff_relation']}::{row['stratum_key']}"] += 1
    return {
        "missing_relation_counts": dict(Counter(str(row["cutoff_relation"]) for row in missing)),
        "missing_stratum_counts": dict(stratum_counts),
        "mean_contract_brier_by_relation": {
            relation: round(statistics.mean(values), 6)
            for relation, values in sorted(relation_values.items())
            if values
        },
    }


def build_report(db: Path, join_report_path: Path, starts: int, seed: int) -> dict[str, Any]:
    join_report = load_json(join_report_path)
    all_rows = join_report["contract_base_rates"]
    joined = [row for row in all_rows if row.get("fetch_status") == "joined"]
    missing = join_report["missing_contracts"]
    contract_ids = [str(row["contract_id"]) for row in all_rows]
    calls = load_calls(db, contract_ids)

    strict = paired_delta(joined, calls)
    low = adversarial_search(joined, missing, calls, direction="min", seed=seed, starts=starts)
    high = adversarial_search(joined, missing, calls, direction="max", seed=seed + 1, starts=starts)
    low_delta = low["effect"]["post_minus_pre_brier"]
    verdict = (
        "survives_adversarial_missing_band_assignment"
        if low_delta is not None and low_delta > 0.02
        else "missing_band_assignment_can_erase_or_flip_effect"
    )
    return {
        "schema": "gp245-cutoff-stage-c-missing-band-sensitivity-v1",
        "db": str(db),
        "join_report": str(join_report_path.relative_to(REPO)),
        "pilot_id": PILOT_ID,
        "contracts": {
            "total": len(all_rows),
            "joined": len(joined),
            "missing": len(missing),
        },
        "calls_loaded": len(calls),
        "bands_tested": list(BANDS),
        "strict_joined_only_effect": strict,
        "adversarial_min_effect": low,
        "adversarial_max_effect": high,
        "missing_profile": missing_profile(missing, calls),
        "verdict": verdict,
        "interpretation": (
            "This varies only the unknown base-rate band for missing Stage-C rows. "
            "It does not repair provenance and does not answer second-source robustness."
        ),
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cutoff_stage_c_missing_sensitivity_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Cutoff Stage-C Missing-Band Sensitivity",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Verdict: `{report['verdict']}`",
        f"- Contracts: `{report['contracts']}`",
        f"- Calls loaded: `{report['calls_loaded']}`",
        f"- Strict joined-only effect: `{report['strict_joined_only_effect']}`",
        f"- Adversarial minimum effect: `{report['adversarial_min_effect']['effect']}`",
        f"- Adversarial maximum effect: `{report['adversarial_max_effect']['effect']}`",
        f"- Missing relation counts: `{report['missing_profile']['missing_relation_counts']}`",
        f"- Missing mean contract Brier by relation: `{report['missing_profile']['mean_contract_brier_by_relation']}`",
        "",
        "## Interpretation",
        "",
        report["interpretation"],
        "",
    ]
    (out_dir / "cutoff_stage_c_missing_sensitivity_report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--join-report", type=Path, default=DEFAULT_JOIN_REPORT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--starts", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    report = build_report(args.db, args.join_report, args.starts, args.seed)
    write_outputs(report, args.out_dir)
    print(f"wrote {args.out_dir / 'cutoff_stage_c_missing_sensitivity_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
