#!/usr/bin/env python3
"""No-call consumer audit for F47 contrastive paired forecasts.

F47 establishes that emitted A/B probability deltas track y_a - y_b. This audit
asks the next applied question: can that ranking be consumed as a decision rule
without being explained by source/pairing artifacts?
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
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
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT_JSON = WORKSPACE / "f47_contrastive_policy_consumer_audit_2026_06_03.json"
DEFAULT_OUT_MD = WORKSPACE / "f47_contrastive_policy_consumer_audit_2026_06_03.md"

INPUTS = {
    "internal": WORKSPACE / "pilot_v26a_calls_full.jsonl",
    "external_v25": WORKSPACE / "pilot_v26a_calls_full_corpusv25.jsonl",
}
FAMILY_ALIASES = {
    "claude_v26": "claude",
    "codex_55_v26": "codex_55",
    "codex_54mini_v26": "codex_mini",
    "gemini_v26": "gemini",
    "deepseek_v26": "deepseek",
}


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


def sign(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def family_for(row: dict[str, Any]) -> str:
    agent_id = str(row.get("agent_id") or "")
    if agent_id in FAMILY_ALIASES:
        return FAMILY_ALIASES[agent_id]
    runtime = str(row.get("runtime") or "")
    model = str(row.get("model") or "")
    if runtime == "codex" and model == "gpt-5.5":
        return "codex_55"
    if runtime == "codex" and model == "gpt-5.4-mini":
        return "codex_mini"
    return runtime or agent_id or "unknown"


def source_bucket(row: dict[str, Any] | None) -> str:
    if not row:
        return "missing"
    source = str(row.get("source") or "")
    if source:
        return source
    source_corpus = str(row.get("source_corpus") or "")
    if source_corpus:
        return source_corpus
    return "unknown"


def load_contracts(db_path: Path) -> dict[str, dict[str, Any]]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            SELECT contract_id, question, source, source_corpus, y_known,
                   task_type, horizon
            FROM contracts
            WHERE y_known IS NOT NULL
            """
        ).fetchall()
    finally:
        con.close()
    return {
        str(row["contract_id"]): {
            "question": row["question"],
            "source": row["source"],
            "source_corpus": row["source_corpus"],
            "y_known": int(row["y_known"]),
            "task_type": row["task_type"],
            "horizon": row["horizon"],
        }
        for row in rows
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_observations(db_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    contracts = load_contracts(db_path)
    observations: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for corpus, path in INPUTS.items():
        for line_no, row in enumerate(read_jsonl(path), start=1):
            parsed = row.get("parsed") or {}
            audit = row.get("schema_audit") or {}
            contract_id = row.get("contract_id")
            partner_id = row.get("partner_contract_id")
            p_a = as_float(parsed.get("p_success_a"))
            p_b = as_float(parsed.get("p_success_b"))
            predicted_delta = as_float(parsed.get("predicted_delta"))
            reason = None
            if not audit.get("schema_ok"):
                reason = "schema_not_ok"
            elif not contract_id or not partner_id:
                reason = "missing_contract_or_partner"
            elif p_a is None or p_b is None or predicted_delta is None:
                reason = "missing_probabilities"
            elif contract_id not in contracts or partner_id not in contracts:
                reason = "missing_y_known"
            if reason:
                exclusions.append(
                    {
                        "corpus": corpus,
                        "line": line_no,
                        "agent_id": row.get("agent_id"),
                        "condition": row.get("sub_condition"),
                        "reason": reason,
                        "contract_id": contract_id,
                        "partner_contract_id": partner_id,
                    }
                )
                continue
            a = contracts[str(contract_id)]
            b = contracts[str(partner_id)]
            actual_delta = int(a["y_known"]) - int(b["y_known"])
            observations.append(
                {
                    "corpus": corpus,
                    "family": family_for(row),
                    "condition": row.get("sub_condition") or "unknown",
                    "contract_id": str(contract_id),
                    "partner_contract_id": str(partner_id),
                    "pair_id": f"{contract_id}::{partner_id}",
                    "source_a": source_bucket(a),
                    "source_b": source_bucket(b),
                    "source_pair": f"{source_bucket(a)}::{source_bucket(b)}",
                    "p_a": p_a,
                    "p_b": p_b,
                    "predicted_delta": predicted_delta,
                    "predicted_sign": sign(predicted_delta),
                    "actual_delta": actual_delta,
                    "actual_sign": sign(float(actual_delta)),
                    "y_a": int(a["y_known"]),
                    "y_b": int(b["y_known"]),
                }
            )
    return observations, exclusions


def decision_utility(predicted_sign: int, actual_sign: int) -> int:
    if actual_sign == 0:
        return 0
    if predicted_sign == 0:
        return 0
    return 1 if predicted_sign == actual_sign else -1


def source_control_signs(rows: list[dict[str, Any]]) -> list[int]:
    """Leave-one-pair-out majority actual sign for each source-pair template."""
    out: list[int] = []
    for idx, row in enumerate(rows):
        peers = [
            r["actual_sign"]
            for j, r in enumerate(rows)
            if j != idx
            and r["pair_id"] != row["pair_id"]
            and r["source_pair"] == row["source_pair"]
            and r["actual_sign"] != 0
        ]
        score = sum(peers)
        out.append(sign(float(score)))
    return out


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    non_tie = [r for r in rows if r["actual_sign"] != 0]
    if not non_tie:
        return {"n": len(rows), "non_tie_n": 0, "error": "no non-tie outcome pairs"}

    contrastive_utils = [
        decision_utility(int(r["predicted_sign"]), int(r["actual_sign"])) for r in non_tie
    ]
    always_a_utils = [decision_utility(1, int(r["actual_sign"])) for r in non_tie]
    always_b_utils = [decision_utility(-1, int(r["actual_sign"])) for r in non_tie]
    source_signs = source_control_signs(non_tie)
    source_utils = [
        decision_utility(src_sign, int(row["actual_sign"]))
        for src_sign, row in zip(source_signs, non_tie)
    ]
    random_utils = [0 for _ in non_tie]

    contrastive_correct = sum(1 for v in contrastive_utils if v == 1)
    source_correct = sum(1 for v in source_utils if v == 1)
    source_abstains = sum(1 for v in source_utils if v == 0)
    diff_vs_source = [c - s for c, s in zip(contrastive_utils, source_utils)]
    diff_vs_always_a = [c - a for c, a in zip(contrastive_utils, always_a_utils)]
    diff_vs_random = contrastive_utils[:]
    mean_util = statistics.mean(contrastive_utils)
    _, util_lo, util_hi = bootstrap_ci(contrastive_utils, seed=42)
    return {
        "n": len(rows),
        "non_tie_n": len(non_tie),
        "tie_n": len(rows) - len(non_tie),
        "source_pair_counts": dict(
            sorted(
                {r["source_pair"]: sum(1 for x in rows if x["source_pair"] == r["source_pair"]) for r in rows}.items()
            )
        ),
        "contrastive_accuracy": round(contrastive_correct / len(non_tie), 6),
        "contrastive_mean_utility": round(mean_util, 6),
        "contrastive_utility_ci95": [
            round(util_lo, 6) if util_lo is not None else None,
            round(util_hi, 6) if util_hi is not None else None,
        ],
        "source_control_accuracy": round(source_correct / len(non_tie), 6),
        "source_control_abstain_rate": round(source_abstains / len(non_tie), 6),
        "always_a_accuracy": round(sum(1 for v in always_a_utils if v == 1) / len(non_tie), 6),
        "always_b_accuracy": round(sum(1 for v in always_b_utils if v == 1) / len(non_tie), 6),
        "mean_utility_delta_vs_random": round(statistics.mean(diff_vs_random), 6),
        "mean_utility_delta_vs_always_a": round(statistics.mean(diff_vs_always_a), 6),
        "mean_utility_delta_vs_source_control": round(statistics.mean(diff_vs_source), 6),
        "paired_vs_random": paired_permutation_test(contrastive_utils, random_utils, seed=42),
        "paired_vs_always_a": paired_permutation_test(contrastive_utils, always_a_utils, seed=42),
        "paired_vs_source_control": paired_permutation_test(
            contrastive_utils, source_utils, seed=42
        ),
    }


def collapse_by_pair(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["corpus"], row["family"], row["condition"], row["pair_id"])].append(row)
    collapsed: list[dict[str, Any]] = []
    for group in grouped.values():
        base = dict(group[0])
        mean_delta = statistics.mean(float(r["predicted_delta"]) for r in group)
        base["predicted_delta"] = mean_delta
        base["predicted_sign"] = sign(mean_delta)
        base["collapsed_rows"] = len(group)
        collapsed.append(base)
    return collapsed


def collapse_by_unique_pair(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["corpus"], row["pair_id"])].append(row)
    collapsed: list[dict[str, Any]] = []
    for group in grouped.values():
        base = dict(group[0])
        mean_delta = statistics.mean(float(r["predicted_delta"]) for r in group)
        base["family"] = "mean_all_families"
        base["condition"] = "mean_all_conditions"
        base["predicted_delta"] = mean_delta
        base["predicted_sign"] = sign(mean_delta)
        base["collapsed_rows"] = len(group)
        collapsed.append(base)
    return collapsed


def build_report(rows: list[dict[str, Any]], exclusions: list[dict[str, Any]]) -> dict[str, Any]:
    collapsed = collapse_by_pair(rows)
    unique_pair_collapsed = collapse_by_unique_pair(rows)
    groupings: dict[str, list[dict[str, Any]]] = {
        "all_calls": rows,
        "collapsed_by_pair_family_condition": collapsed,
        "collapsed_by_unique_pair": unique_pair_collapsed,
    }
    for corpus in sorted({r["corpus"] for r in rows}):
        groupings[f"corpus::{corpus}"] = [r for r in rows if r["corpus"] == corpus]
    for family in sorted({r["family"] for r in rows}):
        groupings[f"family::{family}"] = [r for r in rows if r["family"] == family]
    for condition in sorted({r["condition"] for r in rows}):
        groupings[f"condition::{condition}"] = [r for r in rows if r["condition"] == condition]

    summaries = {name: summarize_rows(items) for name, items in sorted(groupings.items())}
    all_summary = summaries["all_calls"]
    unique_summary = summaries["collapsed_by_unique_pair"]
    source_delta = unique_summary.get("mean_utility_delta_vs_source_control")
    source_p = (
        unique_summary.get("paired_vs_source_control", {}).get("p_value")
        if isinstance(unique_summary.get("paired_vs_source_control"), dict)
        else None
    )
    unique_vs_random_p = (
        unique_summary.get("paired_vs_random", {}).get("p_value")
        if isinstance(unique_summary.get("paired_vs_random"), dict)
        else None
    )
    unique_non_tie_n = int(unique_summary.get("non_tie_n") or 0)
    min_unique_non_tie_for_policy = 20
    passes_controls = bool(
        isinstance(source_delta, (int, float))
        and source_delta > 0
        and source_p is not None
        and source_p <= 0.05
        and unique_vs_random_p is not None
        and unique_vs_random_p <= 0.05
    )
    sample_sufficient = unique_non_tie_n >= min_unique_non_tie_for_policy
    verdict = {
        "contrastive_consumer_promotable": passes_controls and sample_sufficient,
        "unique_non_tie_n": unique_non_tie_n,
        "min_unique_non_tie_for_policy": min_unique_non_tie_for_policy,
        "passes_unique_pair_controls": passes_controls,
        "interpretation": (
            "Contrastive ranking is decision-useful in the repeated-call view and "
            "remains perfect after collapsing to unique pairs, but only six unique "
            "non-tie pairs exist. That is too few for an applied-policy claim. "
            "Treat this as a promising consumer surface only when source-balanced "
            "or same-source pairs are used."
        ),
    }
    if not verdict["contrastive_consumer_promotable"]:
        verdict["next_step"] = (
            "Do not promote F47 directly to policy. Design a source-balanced "
            "same-source/minimal-pair consumer packet, or use contrastive only "
            "as a diagnostic ranking surface."
        )
    else:
        verdict["next_step"] = (
            "Promote to a small source-balanced confirmation packet before any "
            "forecast-action deployment claim."
        )

    return {
        "report": "f47_contrastive_policy_consumer_audit",
        "date": "2026-06-03",
        "metric": "forced pairwise choose-higher-p utility on non-tie outcome pairs",
        "valid_rows": len(rows),
        "excluded_rows": len(exclusions),
        "exclusion_reasons": {
            reason: sum(1 for e in exclusions if e["reason"] == reason)
            for reason in sorted({e["reason"] for e in exclusions})
        },
        "summaries": summaries,
        "verdict": verdict,
    }


def fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:+.3f}"
    return str(value)


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# F47 contrastive-to-policy consumer audit - 2026-06-03",
        "",
        "No new model calls. This consumes existing v26a contrastive pairs and asks whether the pairwise ranking can be used as a decision rule.",
        "",
        "Policy endpoint: on pairs where `y_a - y_b` is non-zero, choose the side with higher emitted probability. Utility is `+1` for ranking the true-YES side higher, `-1` for ranking it lower, and `0` for abstain/tie. Controls are random (`0` expected utility), always-A, always-B, and a leave-one-out source-pair majority control.",
        "",
        "## Main Summaries",
        "",
        "| group | n | non-tie n | accuracy | utility | delta vs random | delta vs always-A | delta vs source control | p vs source |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in [
        "all_calls",
        "collapsed_by_pair_family_condition",
        "collapsed_by_unique_pair",
        "corpus::internal",
        "corpus::external_v25",
        "condition::base",
        "condition::signed",
    ]:
        summary = report["summaries"].get(name)
        if not summary:
            continue
        p_source = None
        if isinstance(summary.get("paired_vs_source_control"), dict):
            p_source = summary["paired_vs_source_control"].get("p_value")
        lines.append(
            "| {name} | {n} | {nt} | {acc} | {util} | {rnd} | {alwa} | {src} | {psrc} |".format(
                name=name,
                n=summary.get("n"),
                nt=summary.get("non_tie_n"),
                acc=fmt(summary.get("contrastive_accuracy")),
                util=fmt(summary.get("contrastive_mean_utility")),
                rnd=fmt(summary.get("mean_utility_delta_vs_random")),
                alwa=fmt(summary.get("mean_utility_delta_vs_always_a")),
                src=fmt(summary.get("mean_utility_delta_vs_source_control")),
                psrc=fmt(p_source),
            )
        )
    lines.extend(["", "## Per-Family", "", "| family | non-tie n | accuracy | utility | delta vs source | p vs source |", "|---|---:|---:|---:|---:|---:|"])
    for name, summary in report["summaries"].items():
        if not name.startswith("family::"):
            continue
        p_source = None
        if isinstance(summary.get("paired_vs_source_control"), dict):
            p_source = summary["paired_vs_source_control"].get("p_value")
        lines.append(
            "| {fam} | {n} | {acc} | {util} | {src} | {p} |".format(
                fam=name.split("::", 1)[1],
                n=summary.get("non_tie_n"),
                acc=fmt(summary.get("contrastive_accuracy")),
                util=fmt(summary.get("contrastive_mean_utility")),
                src=fmt(summary.get("mean_utility_delta_vs_source_control")),
                p=fmt(p_source),
            )
        )
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            report["verdict"]["interpretation"],
            "",
            report["verdict"]["next_step"],
            "",
            f"Valid rows: `{report['valid_rows']}`. Excluded rows: `{report['excluded_rows']}`.",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()
    rows, exclusions = load_observations(args.db)
    report = build_report(rows, exclusions)
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    write_markdown(report, args.out_md)
    print(json.dumps(report["verdict"], indent=2, sort_keys=True))
    print(f"wrote {args.out_json}")
    print(f"wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
