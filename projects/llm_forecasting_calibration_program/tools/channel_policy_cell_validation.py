#!/usr/bin/env python3
"""Validate the sole GP-245 Law 2 Brier-policy candidate.

This is a no-call, no-DB-write demotion check for the current strict cell:
`codex_55 / worry` on `public_v28_corpus_v25`.

It composes the broad channel-holdout report primitives instead of defining a
new policy. The broad report finds candidate cells; this report asks whether
the surviving cell holds under temporal split and source leave-one-out checks.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

import channel_holdout_law_report as holdout
from src.ztare.experiment_stats import n_required_for_brier_delta, paired_permutation_test


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = REPO / "projects/llm_forecasting_calibration_program/channel_policy_cell_v1/workspace"

TARGET_GROUP = "public_v28_corpus_v25"
TARGET_FAMILY = "codex_55"
TARGET_CHANNEL = "worry"
MIN_SPLIT_TRAIN = 100
MIN_SPLIT_TEST = 40
MIN_SOURCE_TEST = 20
MIN_DELTA = -0.005
POLICY_ALPHA = 0.05


def candidate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row.get("holdout_group") == TARGET_GROUP
        and row.get("family") == TARGET_FAMILY
        and TARGET_CHANNEL in row.get("channels", {})
    ]


def ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda r: (str(r.get("fired_at") or ""), int(r.get("call_id") or 0)))


def score_rows(rows: list[dict[str, Any]], rule: dict[str, Any], *, inverted: bool = False) -> dict[str, Any] | None:
    raw: list[float] = []
    adj: list[float] = []
    diffs: list[float] = []
    for row in rows:
        p_adj = holdout.adjusted_p(row, TARGET_CHANNEL, rule, invert=inverted)
        if p_adj is None:
            continue
        raw_brier = float(row["brier"])
        adj_brier = holdout.brier(p_adj, int(row["y_known"]))
        raw.append(raw_brier)
        adj.append(adj_brier)
        diffs.append(adj_brier - raw_brier)
    if len(raw) < MIN_SPLIT_TEST:
        return None
    delta = statistics.mean(diffs)
    sd = statistics.pstdev(diffs) if len(diffs) > 1 else 0.0
    return {
        "n": len(raw),
        "mean_delta_brier": round(delta, 6),
        "sum_delta_brier": round(sum(diffs), 6),
        "sd_delta_brier": round(sd, 6),
        "paired_permutation": paired_permutation_test(adj, raw, n_perm=5000, seed=42),
        "n_required_for_observed_delta": n_required_for_brier_delta(delta, sd_brier=sd) if sd > 0 else None,
    }


def pass_policy(score: dict[str, Any] | None, inverted: dict[str, Any] | None = None) -> bool:
    if not score:
        return False
    p_value = (score.get("paired_permutation") or {}).get("p_value")
    beats_inverted = True
    if inverted:
        beats_inverted = score["mean_delta_brier"] < inverted["mean_delta_brier"]
    return (
        score["mean_delta_brier"] <= MIN_DELTA
        and p_value is not None
        and p_value <= POLICY_ALPHA
        and beats_inverted
    )


def external_holdout_validation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    train = [row for row in rows if row.get("holdout_group") != TARGET_GROUP]
    test = candidate_rows(rows)
    family_rules: dict[tuple[str, str], dict[str, Any]] = {}
    for family in sorted({row["family"] for row in train}):
        rule = holdout.train_rule(
            [row for row in train if row["family"] == family],
            TARGET_CHANNEL,
        )
        if rule:
            family_rules[(family, TARGET_CHANNEL)] = rule
    rule = family_rules.get((TARGET_FAMILY, TARGET_CHANNEL))
    shuffled = holdout.family_shuffle_rule(family_rules, TARGET_FAMILY, TARGET_CHANNEL)
    actual = score_rows(test, rule) if rule else None
    inverted = score_rows(test, rule, inverted=True) if rule else None
    shuffled_score = score_rows(test, shuffled) if shuffled else None
    return {
        "train_rows_all_families": len(train),
        "test_rows": len(test),
        "rule": rule,
        "actual": actual,
        "inverted": inverted,
        "family_shuffled": shuffled_score,
        "passes": pass_policy(actual, inverted)
        and (not shuffled_score or actual["mean_delta_brier"] < shuffled_score["mean_delta_brier"]),
    }


def temporal_split_validation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    target = ordered(candidate_rows(rows))
    if len(target) < MIN_SPLIT_TRAIN + MIN_SPLIT_TEST:
        return {
            "status": "insufficient_rows",
            "rows": len(target),
            "minimum_rows": MIN_SPLIT_TRAIN + MIN_SPLIT_TEST,
        }
    split = len(target) // 2
    train = target[:split]
    test = target[split:]
    rule = holdout.train_rule(train, TARGET_CHANNEL)
    actual = score_rows(test, rule) if rule else None
    inverted = score_rows(test, rule, inverted=True) if rule else None
    return {
        "status": "evaluated" if rule else "no_train_rule",
        "split": "first_half_train_second_half_test_by_fired_at_call_id",
        "train_rows": len(train),
        "test_rows": len(test),
        "rule": rule,
        "actual": actual,
        "inverted": inverted,
        "passes": pass_policy(actual, inverted),
    }


def source_bucket_report(rows: list[dict[str, Any]], external_rule: dict[str, Any] | None) -> dict[str, Any]:
    target = candidate_rows(rows)
    counts = Counter(row.get("source") or "unknown" for row in target)
    by_source: list[dict[str, Any]] = []
    for source, n in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        test = [row for row in target if (row.get("source") or "unknown") == source]
        external_score = score_rows(test, external_rule) if external_rule and len(test) >= MIN_SOURCE_TEST else None
        external_inverted = (
            score_rows(test, external_rule, inverted=True)
            if external_rule and len(test) >= MIN_SOURCE_TEST
            else None
        )
        by_source.append(
            {
                "source": source,
                "n": n,
                "external_rule_score": external_score,
                "external_rule_inverted": external_inverted,
                "external_rule_passes": pass_policy(external_score, external_inverted),
            }
        )
    total_gain = sum(
        abs(row["external_rule_score"]["sum_delta_brier"])
        for row in by_source
        if row.get("external_rule_score")
        and row["external_rule_score"]["sum_delta_brier"] < 0
    )
    for row in by_source:
        score = row.get("external_rule_score")
        row["share_of_positive_gain_abs"] = (
            round(abs(score["sum_delta_brier"]) / total_gain, 4)
            if score and score["sum_delta_brier"] < 0 and total_gain > 0
            else 0.0
        )
    return {
        "min_source_test": MIN_SOURCE_TEST,
        "sources": by_source,
        "max_positive_gain_share_abs": max((row["share_of_positive_gain_abs"] for row in by_source), default=0.0),
    }


def source_leave_one_out_validation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    target = candidate_rows(rows)
    counts = Counter(row.get("source") or "unknown" for row in target)
    checks: list[dict[str, Any]] = []
    for source, n in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        if n < MIN_SOURCE_TEST:
            checks.append({"source": source, "n": n, "status": "skipped_small_source"})
            continue
        train = [row for row in target if (row.get("source") or "unknown") != source]
        test = [row for row in target if (row.get("source") or "unknown") == source]
        rule = holdout.train_rule(train, TARGET_CHANNEL)
        actual = score_rows(test, rule) if rule else None
        inverted = score_rows(test, rule, inverted=True) if rule else None
        checks.append(
            {
                "source": source,
                "n": n,
                "train_rows": len(train),
                "status": "evaluated" if rule else "no_train_rule",
                "actual": actual,
                "inverted": inverted,
                "passes": pass_policy(actual, inverted),
            }
        )
    evaluated = [row for row in checks if row.get("status") == "evaluated"]
    failures = [row for row in evaluated if not row.get("passes")]
    return {
        "checks": checks,
        "evaluated_sources": len(evaluated),
        "failure_sources": [row["source"] for row in failures],
        "passes": bool(evaluated) and not failures,
    }


def verdict(external: dict[str, Any], temporal: dict[str, Any], source_loo: dict[str, Any], bucket: dict[str, Any]) -> str:
    if not external.get("passes"):
        return "demote_policy_cell_external_holdout_failed"
    if temporal.get("status") == "evaluated" and not temporal.get("passes"):
        return "demote_policy_cell_temporal_split_failed"
    if source_loo.get("evaluated_sources") and not source_loo.get("passes"):
        return "demote_policy_cell_source_fragile"
    if bucket.get("max_positive_gain_share_abs", 0.0) >= 0.70:
        return "demote_policy_cell_gain_concentrated"
    return "survives_existing_stress_needs_prospective_validation"


def build_report(db: Path) -> dict[str, Any]:
    rows = holdout.load_rows(db)
    target = candidate_rows(rows)
    external = external_holdout_validation(rows)
    temporal = temporal_split_validation(rows)
    source_bucket = source_bucket_report(rows, external.get("rule"))
    source_loo = source_leave_one_out_validation(rows)
    result_verdict = verdict(external, temporal, source_loo, source_bucket)
    return {
        "schema": "gp245-channel-policy-cell-validation-v1",
        "db": str(db),
        "target": {
            "family": TARGET_FAMILY,
            "channel": TARGET_CHANNEL,
            "holdout_group": TARGET_GROUP,
            "rows": len(target),
        },
        "thresholds": {
            "min_delta": MIN_DELTA,
            "policy_alpha": POLICY_ALPHA,
            "min_split_train": MIN_SPLIT_TRAIN,
            "min_split_test": MIN_SPLIT_TEST,
            "min_source_test": MIN_SOURCE_TEST,
        },
        "external_holdout": external,
        "temporal_split": temporal,
        "source_bucket": source_bucket,
        "source_leave_one_out": source_loo,
        "verdict": result_verdict,
        "interpretation": {
            "diagnostic_law": "Unaffected by a policy-cell demotion; worry can still reveal realized error.",
            "policy_translation": "Promote only if the frozen cell survives external holdout, temporal split, source checks, and later prospective rows.",
        },
    }


def write_outputs(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "channel_policy_cell_validation.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = ["# Channel Policy-Cell Validation", ""]
    lines.append(f"- Verdict: `{result['verdict']}`")
    target = result["target"]
    lines.append(
        f"- Target: `{target['family']}` / `{target['channel']}` on "
        f"`{target['holdout_group']}` ({target['rows']} rows)"
    )
    lines.append("")
    lines.append("## External Holdout")
    ext = result["external_holdout"]
    lines.append(f"- Passes: `{ext['passes']}`")
    lines.append(f"- Train rows all families: {ext['train_rows_all_families']}")
    lines.append(f"- Test rows: {ext['test_rows']}")
    for label in ("actual", "inverted", "family_shuffled"):
        score = ext.get(label)
        if score:
            lines.append(
                f"- `{label}`: n={score['n']}, delta={score['mean_delta_brier']}, "
                f"p={score['paired_permutation'].get('p_value')}, "
                f"n_required={score['n_required_for_observed_delta']}"
            )
    lines.append("")
    lines.append("## Temporal Split")
    temporal = result["temporal_split"]
    lines.append(f"- Status: `{temporal['status']}`")
    lines.append(f"- Passes: `{temporal.get('passes')}`")
    if temporal.get("actual"):
        actual = temporal["actual"]
        inv = temporal.get("inverted")
        lines.append(
            f"- Actual: n={actual['n']}, delta={actual['mean_delta_brier']}, "
            f"p={actual['paired_permutation'].get('p_value')}, "
            f"n_required={actual['n_required_for_observed_delta']}"
        )
        if inv:
            lines.append(
                f"- Inverted: n={inv['n']}, delta={inv['mean_delta_brier']}, "
                f"p={inv['paired_permutation'].get('p_value')}"
            )
    lines.append("")
    lines.append("## Source Buckets")
    for row in result["source_bucket"]["sources"]:
        score = row.get("external_rule_score")
        delta = score["mean_delta_brier"] if score else None
        p_value = score["paired_permutation"].get("p_value") if score else None
        lines.append(
            f"- `{row['source']}`: n={row['n']}, delta={delta}, p={p_value}, "
            f"pass={row.get('external_rule_passes')}, "
            f"gain_share={row['share_of_positive_gain_abs']}"
        )
    lines.append("")
    lines.append("## Source Leave-One-Out")
    lines.append(f"- Evaluated sources: {result['source_leave_one_out']['evaluated_sources']}")
    lines.append(f"- Failure sources: `{result['source_leave_one_out']['failure_sources']}`")
    for row in result["source_leave_one_out"]["checks"]:
        score = row.get("actual")
        delta = score["mean_delta_brier"] if score else None
        p_value = score["paired_permutation"].get("p_value") if score else None
        lines.append(
            f"- `{row['source']}`: status={row['status']}, n={row['n']}, "
            f"delta={delta}, p={p_value}, pass={row.get('passes')}"
        )
    lines.append("")
    lines.append("## Interpretation")
    for item in result["interpretation"].values():
        lines.append(f"- {item}")
    lines.append("")
    (out_dir / "channel_policy_cell_validation.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = build_report(args.db)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.out_dir:
        write_outputs(result, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
