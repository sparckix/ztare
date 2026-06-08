#!/usr/bin/env python3
"""No-call raw-gap matching audit for Law 1 anti-bias collapse.

The original anti-bias-collapse scorer already reports a regression adjustment:
collapse ~ is_mimic + normal_abs_excess + family fixed effects.

This audit asks the complementary design question: do existing rows contain
enough raw-gap overlap to support a transparent MIMIC-vs-control matched-stratum
claim, or does Law 1 require new raw-gap-matched/randomized calls?
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from projects.llm_forecasting_calibration_program.tools.anti_bias_collapse_score import (
    DEFAULT_DB,
    DEFAULT_OUT,
    collapse_rows,
    frame_gap_rows,
    load_calls,
)
from src.ztare.experiment_stats import bootstrap_ci


DEFAULT_PILOT_ID = "anti_bias_collapse_v1"
DEFAULT_JSON = DEFAULT_OUT / "anti_bias_raw_gap_match_audit.json"
DEFAULT_MD = DEFAULT_OUT / "anti_bias_raw_gap_match_audit.md"
CALIPERS = (0.01, 0.025, 0.05, 0.10, 0.20)


def rounded(value: float | None, digits: int = 6) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return round(value, digits)


def mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "p25": None, "median": None, "p75": None, "max": None}
    vals = sorted(values)

    def q(frac: float) -> float:
        pos = frac * (len(vals) - 1)
        lo = int(pos)
        hi = min(lo + 1, len(vals) - 1)
        return vals[lo] if lo == hi else vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)

    return {
        "min": vals[0],
        "p25": q(0.25),
        "median": q(0.5),
        "p75": q(0.75),
        "max": vals[-1],
    }


def sign_flip_p_value(diffs: list[float], *, n_perm: int = 5000, seed: int = 42) -> dict[str, Any]:
    if not diffs:
        return {"n_paired": 0, "observed_delta": None, "p_value": None, "ci_lo": None, "ci_hi": None}
    observed = statistics.mean(diffs)
    rng = random.Random(seed)
    extreme = 0
    draws: list[float] = []
    for _ in range(n_perm):
        draw = statistics.mean((1 if rng.random() < 0.5 else -1) * diff for diff in diffs)
        draws.append(draw)
        if abs(draw) >= abs(observed):
            extreme += 1
    point, lo, hi = bootstrap_ci(diffs, seed=seed)
    return {
        "n_paired": len(diffs),
        "observed_delta": rounded(observed),
        "p_value": rounded((extreme + 1) / (n_perm + 1), 4),
        "ci_lo": rounded(lo),
        "ci_hi": rounded(hi),
    }


def rows_by_class(collapses: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    mimic = [row for row in collapses if row["class_bucket"] == "MIMIC"]
    control = [row for row in collapses if row["class_bucket"] == "INHERIT_CONTROL"]
    return mimic, control


def support_summary(collapses: list[dict[str, Any]]) -> dict[str, Any]:
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in collapses:
        by_class[row["class_bucket"]].append(row)
    out = {}
    for bucket, rows in sorted(by_class.items()):
        gaps = [float(row["normal_abs_excess"]) for row in rows]
        collapses_v = [float(row["collapse"]) for row in rows]
        out[bucket] = {
            "n": len(rows),
            "families": dict(sorted(Counter(row["family"] for row in rows).items())),
            "bias_ids": dict(sorted(Counter(row["bias_id"] for row in rows).items())),
            "normal_abs_excess_quantiles": {k: rounded(v) for k, v in quantiles(gaps).items()},
            "collapse_mean": rounded(mean(collapses_v)),
            "collapse_quantiles": {k: rounded(v) for k, v in quantiles(collapses_v).items()},
        }
    return out


def overlap_summary(mimic: list[dict[str, Any]], control: list[dict[str, Any]]) -> dict[str, Any]:
    by_family = {}
    for family in sorted({row["family"] for row in mimic + control}):
        m = [float(row["normal_abs_excess"]) for row in mimic if row["family"] == family]
        c = [float(row["normal_abs_excess"]) for row in control if row["family"] == family]
        if not m or not c:
            by_family[family] = {"mimic_n": len(m), "control_n": len(c), "overlap_width": 0.0}
            continue
        lo = max(min(m), min(c))
        hi = min(max(m), max(c))
        by_family[family] = {
            "mimic_n": len(m),
            "control_n": len(c),
            "mimic_range": [rounded(min(m)), rounded(max(m))],
            "control_range": [rounded(min(c)), rounded(max(c))],
            "overlap_range": [rounded(lo), rounded(hi)],
            "overlap_width": rounded(max(0.0, hi - lo)),
            "mimic_in_control_range": sum(1 for value in m if min(c) <= value <= max(c)),
        }
    return by_family


def nearest_matches(
    mimic: list[dict[str, Any]],
    control: list[dict[str, Any]],
    *,
    caliper: float | None,
) -> list[dict[str, Any]]:
    by_family_control: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in control:
        by_family_control[row["family"]].append(row)
    matches: list[dict[str, Any]] = []
    for m in mimic:
        candidates = by_family_control.get(m["family"], [])
        if not candidates:
            continue
        best = min(
            candidates,
            key=lambda c: (
                abs(float(m["normal_abs_excess"]) - float(c["normal_abs_excess"])),
                c["bias_id"],
                c["event_id"],
            ),
        )
        raw_gap_distance = abs(float(m["normal_abs_excess"]) - float(best["normal_abs_excess"]))
        if caliper is not None and raw_gap_distance > caliper:
            continue
        matches.append(
            {
                "family": m["family"],
                "mimic_bias_id": m["bias_id"],
                "mimic_event_id": m["event_id"],
                "control_bias_id": best["bias_id"],
                "control_event_id": best["event_id"],
                "mimic_normal_abs_excess": float(m["normal_abs_excess"]),
                "control_normal_abs_excess": float(best["normal_abs_excess"]),
                "raw_gap_distance": raw_gap_distance,
                "mimic_collapse": float(m["collapse"]),
                "control_collapse": float(best["collapse"]),
                "mimic_minus_control_collapse": float(m["collapse"]) - float(best["collapse"]),
            }
        )
    return matches


def greedy_no_replacement_matches(
    mimic: list[dict[str, Any]],
    control: list[dict[str, Any]],
    *,
    caliper: float | None,
) -> list[dict[str, Any]]:
    all_edges = []
    for m_idx, m in enumerate(mimic):
        for c_idx, c in enumerate(control):
            if m["family"] != c["family"]:
                continue
            dist = abs(float(m["normal_abs_excess"]) - float(c["normal_abs_excess"]))
            if caliper is not None and dist > caliper:
                continue
            all_edges.append((dist, m_idx, c_idx))
    used_m: set[int] = set()
    used_c: set[int] = set()
    matches: list[dict[str, Any]] = []
    for dist, m_idx, c_idx in sorted(all_edges):
        if m_idx in used_m or c_idx in used_c:
            continue
        used_m.add(m_idx)
        used_c.add(c_idx)
        m = mimic[m_idx]
        c = control[c_idx]
        matches.append(
            {
                "family": m["family"],
                "mimic_bias_id": m["bias_id"],
                "mimic_event_id": m["event_id"],
                "control_bias_id": c["bias_id"],
                "control_event_id": c["event_id"],
                "mimic_normal_abs_excess": float(m["normal_abs_excess"]),
                "control_normal_abs_excess": float(c["normal_abs_excess"]),
                "raw_gap_distance": dist,
                "mimic_collapse": float(m["collapse"]),
                "control_collapse": float(c["collapse"]),
                "mimic_minus_control_collapse": float(m["collapse"]) - float(c["collapse"]),
            }
        )
    return matches


def summarize_matches(matches: list[dict[str, Any]]) -> dict[str, Any]:
    diffs = [float(row["mimic_minus_control_collapse"]) for row in matches]
    distances = [float(row["raw_gap_distance"]) for row in matches]
    return {
        "n_matches": len(matches),
        "families": dict(sorted(Counter(row["family"] for row in matches).items())),
        "mean_raw_gap_distance": rounded(mean(distances)),
        "raw_gap_distance_quantiles": {k: rounded(v) for k, v in quantiles(distances).items()},
        "mean_mimic_minus_control_collapse": rounded(mean(diffs)),
        "test": sign_flip_p_value(diffs),
    }


def caliper_table(mimic: list[dict[str, Any]], control: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for caliper in CALIPERS:
        with_replacement = nearest_matches(mimic, control, caliper=caliper)
        no_replacement = greedy_no_replacement_matches(mimic, control, caliper=caliper)
        rows.append(
            {
                "caliper": caliper,
                "with_replacement": summarize_matches(with_replacement),
                "greedy_no_replacement": summarize_matches(no_replacement),
            }
        )
    rows.append(
        {
            "caliper": None,
            "with_replacement": summarize_matches(nearest_matches(mimic, control, caliper=None)),
            "greedy_no_replacement": summarize_matches(greedy_no_replacement_matches(mimic, control, caliper=None)),
        }
    )
    return rows


def verdict(report: dict[str, Any]) -> dict[str, Any]:
    strict = next(row for row in report["caliper_sensitivity"] if row["caliper"] == 0.05)
    strict_wr = strict["with_replacement"]
    strict_nr = strict["greedy_no_replacement"]
    if strict_wr["n_matches"] < 20 or strict_nr["n_matches"] < 10:
        state = "existing_rows_insufficient_for_matched_raw_gap_claim"
    elif strict_wr["test"]["p_value"] is not None and strict_wr["test"]["p_value"] <= 0.05:
        state = "matched_raw_gap_signal_candidate_needs_new_confirmation"
    else:
        state = "matched_raw_gap_audit_does_not_rescue_anti_bias_mechanism"
    return {
        "state": state,
        "promotion_gate": (
            "Promote only with >=20 with-replacement and >=10 no-replacement "
            "within-family raw-gap matches at caliper <=0.05, positive "
            "MIMIC-minus-control collapse, p<=0.05, and no family-sign reversal."
        ),
        "next_step": (
            "If Law 1 mechanism is needed beyond taxonomy, run a raw-gap-matched "
            "or raw-gap-randomized design; do not reuse the current anti-bias "
            "collapse packet as confirmatory evidence."
        ),
    }


def build_report(db: Path, pilot_id: str) -> dict[str, Any]:
    calls, meta = load_calls(db, pilot_id)
    gaps = frame_gap_rows(calls)
    collapses = collapse_rows(gaps)
    mimic, control = rows_by_class(collapses)
    report = {
        "schema": "gp245-law1-raw-gap-match-audit-v1",
        "db": str(db),
        "pilot_id": pilot_id,
        "meta": meta,
        "frame_gap_pairs": len(gaps),
        "collapse_pairs": len(collapses),
        "support_summary": support_summary(collapses),
        "overlap_summary": overlap_summary(mimic, control),
        "caliper_sensitivity": caliper_table(mimic, control),
    }
    report["verdict"] = verdict(report)
    return report


def write_report(report: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Law 1 Raw-Gap Match Audit",
        "",
        f"- Pilot: `{report['pilot_id']}`",
        f"- Usable calls: `{report['meta']['usable_calls']}`",
        f"- Collapse pairs: `{report['collapse_pairs']}`",
        f"- Verdict: `{report['verdict']['state']}`",
        f"- Promotion gate: {report['verdict']['promotion_gate']}",
        f"- Next step: {report['verdict']['next_step']}",
        "",
        "## Support Summary",
        "",
    ]
    for bucket, row in report["support_summary"].items():
        lines.append(
            f"- `{bucket}`: n=`{row['n']}`, families=`{row['families']}`, "
            f"raw-gap quantiles=`{row['normal_abs_excess_quantiles']}`, "
            f"mean collapse=`{row['collapse_mean']}`"
        )
    lines.extend(["", "## Family Overlap", ""])
    for family, row in report["overlap_summary"].items():
        lines.append(f"- `{family}`: `{row}`")
    lines.extend(["", "## Caliper Sensitivity", ""])
    for row in report["caliper_sensitivity"]:
        lines.append(f"### caliper `{row['caliper']}`")
        wr = row["with_replacement"]
        nr = row["greedy_no_replacement"]
        lines.append(
            f"- with replacement: n=`{wr['n_matches']}`, mean distance=`{wr['mean_raw_gap_distance']}`, "
            f"mean MIMIC-control collapse=`{wr['mean_mimic_minus_control_collapse']}`, "
            f"p=`{wr['test']['p_value']}`"
        )
        lines.append(
            f"- greedy no replacement: n=`{nr['n_matches']}`, mean distance=`{nr['mean_raw_gap_distance']}`, "
            f"mean MIMIC-control collapse=`{nr['mean_mimic_minus_control_collapse']}`, "
            f"p=`{nr['test']['p_value']}`"
        )
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--pilot-id", default=DEFAULT_PILOT_ID)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    report = build_report(args.db, args.pilot_id)
    write_report(report, args.json_out, args.md_out)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
