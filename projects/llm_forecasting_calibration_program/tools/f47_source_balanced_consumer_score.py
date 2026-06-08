#!/usr/bin/env python3
"""Score F47 source-balanced contrastive consumer calls."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.ztare.experiment_stats import bootstrap_ci, paired_permutation_test


REPO = Path(__file__).resolve().parents[3]
WORKSPACE = (
    REPO
    / "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace"
)
DEFAULT_CALLS = WORKSPACE / "pilot_f47_source_balanced_consumer_calls_smoke_2026_06_03.jsonl"
DEFAULT_KEY = WORKSPACE / "f47_source_balanced_consumer_packet_2026_06_03_answer_key.json"
DEFAULT_OUT_JSON = WORKSPACE / "f47_source_balanced_consumer_score_2026_06_03.json"
DEFAULT_OUT_MD = WORKSPACE / "f47_source_balanced_consumer_score_2026_06_03.md"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_key(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text())
    return {row["pair_id"]: row for row in data["answer_key"]}


def as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        x = float(value)
    except Exception:
        return None
    return x if math.isfinite(x) else None


def sign(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def family_for(row: dict[str, Any]) -> str:
    runtime = str(row.get("runtime") or "")
    model = str(row.get("model") or "")
    if runtime == "codex" and model == "gpt-5.5":
        return "codex_55"
    if runtime == "codex" and model == "gpt-5.4-mini":
        return "codex_mini"
    return runtime or str(row.get("agent_id") or "unknown")


def decision_utility(predicted_sign: int, actual_sign: int) -> int:
    if predicted_sign == 0 or actual_sign == 0:
        return 0
    return 1 if predicted_sign == actual_sign else -1


def load_observations(
    calls_path: Path, key_path: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    key = load_key(key_path)
    observations: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for line_no, row in enumerate(read_jsonl(calls_path), start=1):
        pair_id = row.get("pair_id")
        parsed = row.get("parsed") or {}
        audit = row.get("schema_audit") or {}
        p_a = as_float(parsed.get("p_success_a"))
        p_b = as_float(parsed.get("p_success_b"))
        predicted_delta = as_float(parsed.get("predicted_delta"))
        if predicted_delta is None and p_a is not None and p_b is not None:
            predicted_delta = p_a - p_b
        reason = None
        if pair_id not in key:
            reason = "missing_answer_key"
        elif not audit.get("schema_ok"):
            reason = "schema_not_ok"
        elif p_a is None or p_b is None or predicted_delta is None:
            reason = "missing_probabilities"
        if reason:
            exclusions.append(
                {
                    "line": line_no,
                    "pair_id": pair_id,
                    "agent_id": row.get("agent_id"),
                    "reason": reason,
                }
            )
            continue
        answer = key[str(pair_id)]
        actual_delta = int(answer["actual_delta"])
        observations.append(
            {
                "pair_id": str(pair_id),
                "source": str(answer["source"]),
                "family": family_for(row),
                "agent_id": row.get("agent_id"),
                "p_a": p_a,
                "p_b": p_b,
                "predicted_delta": predicted_delta,
                "predicted_sign": sign(predicted_delta),
                "actual_delta": actual_delta,
                "actual_sign": sign(float(actual_delta)),
                "y_a": int(answer["y_a"]),
                "y_b": int(answer["y_b"]),
            }
        )
    return observations, exclusions


def source_control_signs(rows: list[dict[str, Any]]) -> list[int]:
    out: list[int] = []
    for idx, row in enumerate(rows):
        peers = [
            int(peer["actual_sign"])
            for j, peer in enumerate(rows)
            if j != idx
            and peer["pair_id"] != row["pair_id"]
            and peer["source"] == row["source"]
            and int(peer["actual_sign"]) != 0
        ]
        out.append(sign(float(sum(peers))))
    return out


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    non_tie = [row for row in rows if int(row["actual_sign"]) != 0]
    if not non_tie:
        return {"n": len(rows), "non_tie_n": 0, "error": "no non-tie pairs"}
    contrastive = [
        decision_utility(int(row["predicted_sign"]), int(row["actual_sign"]))
        for row in non_tie
    ]
    always_a = [decision_utility(1, int(row["actual_sign"])) for row in non_tie]
    always_b = [decision_utility(-1, int(row["actual_sign"])) for row in non_tie]
    random = [0 for _ in non_tie]
    source_signs = source_control_signs(non_tie)
    source_utils = [
        decision_utility(src, int(row["actual_sign"]))
        for src, row in zip(source_signs, non_tie)
    ]
    _, lo, hi = bootstrap_ci(contrastive, seed=42)
    return {
        "n": len(rows),
        "non_tie_n": len(non_tie),
        "contrastive_accuracy": round(sum(1 for v in contrastive if v == 1) / len(non_tie), 6),
        "contrastive_mean_utility": round(statistics.mean(contrastive), 6),
        "contrastive_utility_ci95": [
            round(lo, 6) if lo is not None else None,
            round(hi, 6) if hi is not None else None,
        ],
        "always_a_accuracy": round(sum(1 for v in always_a if v == 1) / len(non_tie), 6),
        "always_b_accuracy": round(sum(1 for v in always_b if v == 1) / len(non_tie), 6),
        "source_control_accuracy": round(sum(1 for v in source_utils if v == 1) / len(non_tie), 6),
        "source_control_abstain_rate": round(sum(1 for v in source_utils if v == 0) / len(non_tie), 6),
        "mean_utility_delta_vs_random": round(statistics.mean(contrastive), 6),
        "mean_utility_delta_vs_always_a": round(
            statistics.mean([c - a for c, a in zip(contrastive, always_a)]), 6
        ),
        "mean_utility_delta_vs_always_b": round(
            statistics.mean([c - b for c, b in zip(contrastive, always_b)]), 6
        ),
        "mean_utility_delta_vs_source_control": round(
            statistics.mean([c - s for c, s in zip(contrastive, source_utils)]), 6
        ),
        "paired_vs_random": paired_permutation_test(contrastive, random, seed=42),
        "paired_vs_always_a": paired_permutation_test(contrastive, always_a, seed=42),
        "paired_vs_always_b": paired_permutation_test(contrastive, always_b, seed=42),
        "paired_vs_source_control": paired_permutation_test(
            contrastive, source_utils, seed=42
        ),
    }


def collapse_by_unique_pair(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["pair_id"]].append(row)
    collapsed: list[dict[str, Any]] = []
    for group in grouped.values():
        base = dict(group[0])
        mean_delta = statistics.mean(float(row["predicted_delta"]) for row in group)
        base["family"] = "mean_all_families"
        base["agent_id"] = "mean_all_agents"
        base["predicted_delta"] = mean_delta
        base["predicted_sign"] = sign(mean_delta)
        base["collapsed_rows"] = len(group)
        collapsed.append(base)
    return collapsed


def build_report(rows: list[dict[str, Any]], exclusions: list[dict[str, Any]]) -> dict[str, Any]:
    groupings: dict[str, list[dict[str, Any]]] = {
        "all_calls": rows,
        "collapsed_by_unique_pair": collapse_by_unique_pair(rows),
    }
    for family in sorted({row["family"] for row in rows}):
        groupings[f"family::{family}"] = [row for row in rows if row["family"] == family]
    for source in sorted({row["source"] for row in rows}):
        groupings[f"source::{source}"] = [row for row in rows if row["source"] == source]
    summaries = {name: summarize_rows(items) for name, items in sorted(groupings.items())}
    unique = summaries.get("collapsed_by_unique_pair", {})
    p_random = unique.get("paired_vs_random", {}).get("p_value") if isinstance(unique.get("paired_vs_random"), dict) else None
    p_source = unique.get("paired_vs_source_control", {}).get("p_value") if isinstance(unique.get("paired_vs_source_control"), dict) else None
    passes = bool(
        unique.get("non_tie_n", 0) >= 20
        and unique.get("mean_utility_delta_vs_random", 0) > 0
        and unique.get("mean_utility_delta_vs_source_control", 0) > 0
        and p_random is not None
        and p_random <= 0.05
        and p_source is not None
        and p_source <= 0.05
    )
    return {
        "report": "f47_source_balanced_consumer_score",
        "date": "2026-06-03",
        "endpoint": "same-source pairwise choose-higher-probability utility",
        "valid_rows": len(rows),
        "excluded_rows": len(exclusions),
        "exclusion_reasons": {
            reason: sum(1 for e in exclusions if e["reason"] == reason)
            for reason in sorted({e["reason"] for e in exclusions})
        },
        "summaries": summaries,
        "verdict": {
            "source_balanced_consumer_promotable": passes,
            "minimum_unique_non_tie_pairs": 20,
            "interpretation": (
                "Promote only if the unique-pair collapse beats random and "
                "leave-one-pair-out source control at the predeclared threshold."
            ),
        },
    }


def fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:+.3f}"
    return str(value)


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# F47 source-balanced consumer score - 2026-06-03",
        "",
        "Endpoint: choose the contract with higher emitted `p_success`; utility is `+1` for selecting the true-YES side, `-1` for selecting the false side, and `0` for ties/abstains.",
        "",
        "| group | n | non-tie n | accuracy | utility | delta vs random | delta vs always-A | delta vs always-B | delta vs source | p vs source |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    preferred = ["all_calls", "collapsed_by_unique_pair"]
    preferred.extend(name for name in sorted(report["summaries"]) if name.startswith("family::"))
    preferred.extend(name for name in sorted(report["summaries"]) if name.startswith("source::"))
    for name in preferred:
        summary = report["summaries"].get(name)
        if not summary:
            continue
        p_source = None
        if isinstance(summary.get("paired_vs_source_control"), dict):
            p_source = summary["paired_vs_source_control"].get("p_value")
        lines.append(
            "| {name} | {n} | {nt} | {acc} | {util} | {rnd} | {aa} | {ab} | {src} | {psrc} |".format(
                name=name,
                n=summary.get("n"),
                nt=summary.get("non_tie_n"),
                acc=fmt(summary.get("contrastive_accuracy")),
                util=fmt(summary.get("contrastive_mean_utility")),
                rnd=fmt(summary.get("mean_utility_delta_vs_random")),
                aa=fmt(summary.get("mean_utility_delta_vs_always_a")),
                ab=fmt(summary.get("mean_utility_delta_vs_always_b")),
                src=fmt(summary.get("mean_utility_delta_vs_source_control")),
                psrc=fmt(p_source),
            )
        )
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            f"Promotable: `{report['verdict']['source_balanced_consumer_promotable']}`.",
            report["verdict"]["interpretation"],
            "",
            f"Valid rows: `{report['valid_rows']}`. Excluded rows: `{report['excluded_rows']}`.",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calls", type=Path, default=DEFAULT_CALLS)
    parser.add_argument("--answer-key", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()

    rows, exclusions = load_observations(args.calls, args.answer_key)
    report = build_report(rows, exclusions)
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    write_markdown(report, args.out_md)
    print(json.dumps(report["verdict"], indent=2, sort_keys=True))
    print(f"wrote {args.out_json}")
    print(f"wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
