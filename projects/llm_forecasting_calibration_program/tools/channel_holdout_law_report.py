#!/usr/bin/env python3
"""DB-first holdout report for the GP-245 channel law.

This answers a narrower question than channel_surface_report.py:

1. Train a per-family channel/error direction on non-heldout DB rows.
2. Evaluate heldout rows by corpus/pilot group.
3. Keep diagnostic error-readout separate from Brier-policy lift.

No model calls. No DB writes.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from src.ztare.experiment_stats import paired_permutation_test


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"

MIN_TRAIN = 30
MIN_POLICY_TRAIN = 100
MIN_TEST = 20
POLICY_ALPHA = 0.05
MIN_POLICY_DELTA = -0.005
SHRINK_GAMMA = 0.10
CHANNEL_ORDER = [
    "worry",
    "confidence",
    "bid_ask_spread",
    "self_brier_mid",
    "self_brier_width",
    "outside_view_gap",
    "decision_threshold_width",
    "sham_scalar_control",
    "resample_disagreement",
]


def load_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        data = json.loads(text)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        x = float(value)
    except Exception:
        return None
    return x if math.isfinite(x) else None


def maybe_scale_0_100(x: float) -> float:
    return x / 100.0 if abs(x) > 1.5 else x


def rankdata(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(values):
        j = i + 1
        while j < len(values) and values[order[j]] == values[order[i]]:
            j += 1
        rank = (i + j - 1) / 2.0 + 1.0
        for k in range(i, j):
            ranks[order[k]] = rank
        i = j
    return ranks


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(vx * vy)


def spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 4 or len(xs) != len(ys):
        return None
    return pearson(rankdata(xs), rankdata(ys))


def brier(p: float, y: int) -> float:
    return (p - y) ** 2


def clamp01(x: float) -> float:
    return min(1.0, max(0.0, x))


def extract_channels(parsed: dict[str, Any], p_success: float) -> dict[str, float]:
    channels: dict[str, float] = {}

    worry = as_float(parsed.get("tail_insurance_premium"))
    if worry is None:
        worry = as_float(parsed.get("worry"))
    if worry is not None:
        channels["worry"] = maybe_scale_0_100(worry)

    confidence = as_float(parsed.get("verbalized_confidence"))
    if confidence is None:
        confidence = as_float(parsed.get("confidence"))
    if confidence is not None:
        channels["confidence"] = maybe_scale_0_100(confidence)

    spread = as_float(parsed.get("spread"))
    if spread is None:
        buy = as_float(parsed.get("p_buy_yes_max"))
        sell = as_float(parsed.get("p_sell_yes_min"))
        if buy is not None and sell is not None:
            spread = sell - buy
    if spread is not None:
        channels["bid_ask_spread"] = float(spread)

    blo = as_float(parsed.get("predicted_brier_lo"))
    bhi = as_float(parsed.get("predicted_brier_hi"))
    if blo is not None and bhi is not None:
        channels["self_brier_mid"] = (blo + bhi) / 2.0
        channels["self_brier_width"] = bhi - blo

    p_base = as_float(parsed.get("p_base_outside"))
    if p_base is not None:
        channels["outside_view_base"] = p_base
        channels["outside_view_gap"] = abs(p_success - p_base)

    t_no = as_float(parsed.get("threshold_no_bad"))
    t_yes = as_float(parsed.get("threshold_yes_bad"))
    if t_no is not None and t_yes is not None:
        channels["decision_threshold_width"] = t_yes - t_no

    sham = as_float(parsed.get("sham"))
    if sham is not None:
        channels["sham_scalar_control"] = maybe_scale_0_100(sham)

    p2 = as_float(parsed.get("p2"))
    if p2 is not None:
        channels["resample_disagreement"] = abs(p_success - p2)

    return {k: v for k, v in channels.items() if math.isfinite(v)}


def holdout_group(row: dict[str, Any]) -> str | None:
    pilot = row["pilot_id"]
    source_corpus = row.get("source_corpus") or ""
    if pilot in {"premium_batch1", "premium_crossfamily"}:
        return "premium_clean"
    if pilot.startswith("v28") and source_corpus == "corpus_v25":
        return "public_v28_corpus_v25"
    if source_corpus == "corpus_v25":
        return "all_corpus_v25"
    return None


def load_rows(db: Path) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    cur = con.cursor()
    rows: list[dict[str, Any]] = []
    for (
        call_id,
        pilot_id,
        contract_id,
        family,
        p_success,
        brier_value,
        y_known,
        parsed_json,
        fired_at,
        source,
        source_corpus,
        task_type,
        run_corpus,
    ) in cur.execute(
        """
        SELECT pc.call_id, pc.pilot_id, pc.contract_id, pc.family, pc.p_success, pc.brier,
               c.y_known, pc.parsed_json, pc.fired_at, c.source, c.source_corpus, c.task_type,
               pr.corpus
        FROM pilot_calls pc
        JOIN contracts c ON c.contract_id = pc.contract_id
        LEFT JOIN pilot_runs pr ON pr.pilot_id = pc.pilot_id
        WHERE pc.schema_ok = 1
          AND pc.p_success IS NOT NULL
          AND pc.brier IS NOT NULL
          AND c.y_known IS NOT NULL
          AND pc.family IS NOT NULL
        """
    ):
        p = float(p_success)
        y = int(y_known)
        channels = extract_channels(load_json(parsed_json), p)
        if not channels:
            continue
        row = {
            "pilot_id": str(pilot_id),
            "call_id": int(call_id),
            "contract_id": str(contract_id),
            "family": str(family),
            "p_success": p,
            "brier": float(brier_value),
            "abserr": abs(p - y),
            "y_known": y,
            "fired_at": fired_at or "",
            "source": source or "",
            "source_corpus": source_corpus or "",
            "task_type": task_type or "",
            "run_corpus": run_corpus or "",
            "channels": channels,
        }
        row["holdout_group"] = holdout_group(row)
        rows.append(row)
    con.close()
    return rows


def values(rows: Iterable[dict[str, Any]], channel: str, target: str) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for row in rows:
        if channel not in row["channels"]:
            continue
        xs.append(float(row["channels"][channel]))
        ys.append(float(row[target]))
    return xs, ys


def zscore_params(rows: list[dict[str, Any]], channel: str) -> tuple[float, float] | None:
    xs = [float(row["channels"][channel]) for row in rows if channel in row["channels"]]
    if len(xs) < 2:
        return None
    mean = statistics.mean(xs)
    sd = statistics.pstdev(xs)
    if sd <= 0:
        return None
    return mean, sd


def train_rule(rows: list[dict[str, Any]], channel: str) -> dict[str, Any] | None:
    xs, ys = values(rows, channel, "abserr")
    if len(xs) < MIN_TRAIN:
        return None
    rho = spearman(xs, ys)
    params = zscore_params(rows, channel)
    if rho is None or params is None:
        return None
    mean, sd = params
    return {
        "n": len(xs),
        "rho_abserr": rho,
        "direction": 1.0 if rho >= 0 else -1.0,
        "mean": mean,
        "sd": sd,
    }


def adjusted_p(row: dict[str, Any], channel: str, rule: dict[str, Any], *, invert: bool = False) -> float | None:
    if channel not in row["channels"]:
        return None
    direction = float(rule["direction"]) * (-1.0 if invert else 1.0)
    z = (float(row["channels"][channel]) - float(rule["mean"])) / float(rule["sd"])
    risk = max(-2.0, min(2.0, direction * z))
    p = float(row["p_success"])
    return clamp01(p + SHRINK_GAMMA * risk * (0.5 - p))


def score_policy(
    test_rows: list[dict[str, Any]],
    channel: str,
    rule: dict[str, Any],
    *,
    inverted: bool = False,
) -> dict[str, Any] | None:
    raw: list[float] = []
    adj: list[float] = []
    for row in test_rows:
        p_adj = adjusted_p(row, channel, rule, invert=inverted)
        if p_adj is None:
            continue
        raw.append(float(row["brier"]))
        adj.append(brier(p_adj, int(row["y_known"])))
    if len(raw) < MIN_TEST:
        return None
    perm = paired_permutation_test(adj, raw, n_perm=5000, seed=42)
    delta = statistics.mean(a - r for a, r in zip(adj, raw))
    return {
        "n": len(raw),
        "mean_delta_brier": round(delta, 6),
        "improved": delta < 0,
        "paired_permutation": perm,
    }


def family_shuffle_rule(
    rules: dict[tuple[str, str], dict[str, Any]], family: str, channel: str
) -> dict[str, Any] | None:
    candidates = sorted(f for (f, ch) in rules if ch == channel and f != family)
    if not candidates:
        return None
    # Deterministic next-family control.
    greater = [f for f in candidates if f > family]
    chosen = greater[0] if greater else candidates[0]
    return rules.get((chosen, channel))


def summarize(db: Path) -> dict[str, Any]:
    rows = load_rows(db)
    holdout_names = ["premium_clean", "public_v28_corpus_v25", "all_corpus_v25"]
    trainable_channels = sorted({ch for row in rows for ch in row["channels"]}, key=lambda c: CHANNEL_ORDER.index(c) if c in CHANNEL_ORDER else 999)

    group_counts = {
        name: sum(1 for row in rows if row["holdout_group"] == name)
        for name in holdout_names
    }
    channel_counts = {
        channel: sum(1 for row in rows if channel in row["channels"])
        for channel in trainable_channels
    }

    group_results: list[dict[str, Any]] = []
    for group in holdout_names:
        train = [row for row in rows if row["holdout_group"] != group]
        test = [row for row in rows if row["holdout_group"] == group]
        rules: dict[tuple[str, str], dict[str, Any]] = {}
        for family in sorted({row["family"] for row in train}):
            fam_train = [row for row in train if row["family"] == family]
            for channel in trainable_channels:
                rule = train_rule(fam_train, channel)
                if rule:
                    rules[(family, channel)] = rule

        cells: list[dict[str, Any]] = []
        for family in sorted({row["family"] for row in test}):
            fam_test = [row for row in test if row["family"] == family]
            for channel in trainable_channels:
                rule = rules.get((family, channel))
                if not rule:
                    continue
                xs, ys_abs = values(fam_test, channel, "abserr")
                if len(xs) < MIN_TEST:
                    continue
                test_rho_abs = spearman(xs, ys_abs)
                _, ys_brier = values(fam_test, channel, "brier")
                test_rho_brier = spearman(xs, ys_brier)
                if test_rho_abs is None:
                    continue
                actual = score_policy(fam_test, channel, rule)
                inverted = score_policy(fam_test, channel, rule, inverted=True)
                shuffled_rule = family_shuffle_rule(rules, family, channel)
                shuffled = score_policy(fam_test, channel, shuffled_rule) if shuffled_rule else None
                direction_match = (rule["rho_abserr"] >= 0) == (test_rho_abs >= 0)
                beats_inverted = (
                    actual is not None
                    and inverted is not None
                    and actual["mean_delta_brier"] < inverted["mean_delta_brier"]
                )
                beats_family_shuffle = (
                    actual is not None
                    and shuffled is not None
                    and actual["mean_delta_brier"] < shuffled["mean_delta_brier"]
                )
                actual_p = (
                    actual["paired_permutation"].get("p_value")
                    if actual and isinstance(actual.get("paired_permutation"), dict)
                    else None
                )
                exploratory_control_pass = (
                    bool(direction_match)
                    and actual is not None
                    and actual["mean_delta_brier"] < 0
                    and beats_inverted
                    and (beats_family_shuffle if shuffled is not None else True)
                )
                policy_candidate = (
                    exploratory_control_pass
                    and rule["n"] >= MIN_POLICY_TRAIN
                    and actual["mean_delta_brier"] <= MIN_POLICY_DELTA
                    and actual_p is not None
                    and actual_p <= POLICY_ALPHA
                )
                cells.append(
                    {
                        "family": family,
                        "channel": channel,
                        "train_n": rule["n"],
                        "test_n": len(xs),
                        "train_rho_abserr": round(rule["rho_abserr"], 4),
                        "test_rho_abserr": round(test_rho_abs, 4),
                        "test_rho_brier": round(test_rho_brier, 4) if test_rho_brier is not None else None,
                        "direction_match": direction_match,
                        "actual_policy": actual,
                        "inverted_policy": inverted,
                        "family_shuffle_policy": shuffled,
                        "beats_inverted": beats_inverted,
                        "beats_family_shuffle": beats_family_shuffle if shuffled is not None else None,
                        "exploratory_control_pass": exploratory_control_pass,
                        "policy_candidate": policy_candidate,
                    }
                )
        cells.sort(
            key=lambda r: (
                r["policy_candidate"],
                r["direction_match"],
                -(r["actual_policy"]["mean_delta_brier"] if r["actual_policy"] else 999),
                r["test_n"],
            ),
            reverse=True,
        )
        group_results.append(
            {
                "group": group,
                "train_rows": len(train),
                "test_rows": len(test),
                "rules_trained": len(rules),
                "cells": cells,
                "policy_candidate_cells": [row for row in cells if row["policy_candidate"]],
            }
        )

    return {
        "schema": "gp245-channel-holdout-law-report-v1",
        "db": str(db),
        "rows_with_channels_brier_y_known": len(rows),
        "holdout_group_counts": group_counts,
        "channel_counts": channel_counts,
        "min_train": MIN_TRAIN,
        "min_policy_train": MIN_POLICY_TRAIN,
        "min_test": MIN_TEST,
        "policy_alpha": POLICY_ALPHA,
        "min_policy_delta": MIN_POLICY_DELTA,
        "shrink_gamma": SHRINK_GAMMA,
        "groups": group_results,
        "interpretation": {
            "diagnostic_endpoint": "Train Spearman(channel, |error|) on non-heldout rows; check heldout sign and strength.",
            "policy_endpoint": "Apply a frozen small shrink toward 0.5 using the trained direction; Brier delta < 0 is better.",
            "controls": "Inverted-direction and family-shuffled rules must not beat the actual family rule for a policy candidate.",
            "guardrail": "A diagnostic channel law is not a deployment policy unless heldout Brier lift beats controls.",
        },
    }


def write_outputs(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "channel_holdout_law_report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = ["# Channel Holdout Law Report", ""]
    lines.append(f"- Rows with channels, Brier, and y_known: {result['rows_with_channels_brier_y_known']}")
    lines.append(f"- Minimum train/test: {result['min_train']}/{result['min_test']}")
    lines.append(f"- Minimum policy train rows: {result['min_policy_train']}")
    lines.append(f"- Policy alpha: {result['policy_alpha']}")
    lines.append(f"- Minimum policy delta: {result['min_policy_delta']}")
    lines.append(f"- Shrink gamma: {result['shrink_gamma']}")
    lines.append("")
    lines.append("## Holdout Groups")
    lines.append("")
    for group, n in result["holdout_group_counts"].items():
        lines.append(f"- `{group}`: {n} rows")
    lines.append("")
    lines.append("## Policy Candidate Cells")
    lines.append("")
    any_candidate = False
    for group in result["groups"]:
        candidates = group["policy_candidate_cells"]
        lines.append(f"### {group['group']}")
        lines.append("")
        if not candidates:
            lines.append("- None under the current control filter.")
            lines.append("")
            continue
        any_candidate = True
        for row in candidates:
            actual = row["actual_policy"]
            inv = row["inverted_policy"]
            shuf = row["family_shuffle_policy"]
            lines.append(
                f"- `{row['family']}` / `{row['channel']}`: "
                f"train_n={row['train_n']}, test_n={row['test_n']}, "
                f"train_r={row['train_rho_abserr']}, test_r={row['test_rho_abserr']}, "
                f"delta={actual['mean_delta_brier'] if actual else None}, "
                f"p={actual['paired_permutation'].get('p_value') if actual else None}, "
                f"inverted_delta={inv['mean_delta_brier'] if inv else None}, "
                f"family_shuffle_delta={shuf['mean_delta_brier'] if shuf else None}"
            )
        lines.append("")
    if not any_candidate:
        lines.append("No cell currently licenses a Brier-policy claim.")
        lines.append("")
    lines.append("## Top Diagnostic Cells")
    lines.append("")
    for group in result["groups"]:
        lines.append(f"### {group['group']}")
        lines.append("")
        top = sorted(
            group["cells"],
            key=lambda r: (r["direction_match"], abs(r["test_rho_abserr"]), r["test_n"]),
            reverse=True,
        )[:12]
        if not top:
            lines.append("- No evaluable cells.")
            lines.append("")
            continue
        for row in top:
            actual = row["actual_policy"]
            lines.append(
                f"- `{row['family']}` / `{row['channel']}`: "
                f"train_n={row['train_n']}, test_n={row['test_n']}, "
                f"train_r={row['train_rho_abserr']}, test_r={row['test_rho_abserr']}, "
                f"direction_match={row['direction_match']}, "
                f"policy_delta={actual['mean_delta_brier'] if actual else None}, "
                f"policy_candidate={row['policy_candidate']}"
            )
        lines.append("")
    lines.append("## Guardrail")
    lines.append("")
    lines.append(result["interpretation"]["guardrail"])
    lines.append("")
    (out_dir / "channel_holdout_law_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()
    result = summarize(args.db)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.out_dir:
        write_outputs(result, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
