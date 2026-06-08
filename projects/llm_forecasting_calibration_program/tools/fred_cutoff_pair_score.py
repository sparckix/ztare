#!/usr/bin/env python3
"""Score FRED paired cutoff dispatch receipts without DB ingestion."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from random import Random
from pathlib import Path
from statistics import mean
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DIR = PROGRAM / "cutoff_validity_v1/workspace/fred_cutoff_pair_packet_2026_06_04"
DEFAULT_CALLS = DEFAULT_DIR / "fred_cutoff_pair_calls.jsonl"
DEFAULT_ANSWER = DEFAULT_DIR / "fred_cutoff_pair_answer_key.jsonl"
DEFAULT_OUT = DEFAULT_DIR / "fred_cutoff_pair_score_report"


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relpath(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO))
    except ValueError:
        return str(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise SystemExit(f"{path}:{line_no}: expected JSON object")
        rows.append(row)
    return rows


def numeric_probability(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        p = float(value)
        if 0.0 <= p <= 1.0:
            return p
    return None


def brier(p: float, y: int) -> float:
    return (p - y) ** 2


def bootstrap_ci(values: list[float], *, reps: int = 5000, seed: int = 1729) -> list[float | None]:
    if not values:
        return [None, None]
    if len(values) == 1:
        return [values[0], values[0]]
    rng = Random(seed)
    means = []
    n = len(values)
    for _ in range(reps):
        means.append(mean(values[rng.randrange(n)] for _ in range(n)))
    means.sort()
    return [means[int(0.05 * (reps - 1))], means[int(0.95 * (reps - 1))]]


def sign_flip_p(values: list[float]) -> float | None:
    if not values:
        return None
    observed = abs(sum(values))
    n = len(values)
    if n > 20:
        rng = Random(1733)
        reps = 20000
        hits = 0
        for _ in range(reps):
            total = sum(v if rng.random() < 0.5 else -v for v in values)
            if abs(total) >= observed - 1e-15:
                hits += 1
        return hits / reps
    hits = 0
    total = 1 << n
    for mask in range(total):
        s = 0.0
        for i, v in enumerate(values):
            s += v if (mask >> i) & 1 else -v
        if abs(s) >= observed - 1e-15:
            hits += 1
    return hits / total


def score(calls_path: Path, answer_path: Path) -> dict[str, Any]:
    answer = {str(row["contract_id"]): row for row in load_jsonl(answer_path)}
    calls = load_jsonl(calls_path)
    scored: list[dict[str, Any]] = []
    invalid = 0
    for row in calls:
        if not row.get("schema_ok"):
            invalid += 1
            continue
        cid = str(row.get("contract_id"))
        ans = answer.get(cid)
        p = numeric_probability(row.get("p_success"))
        if ans is None or p is None:
            invalid += 1
            continue
        y = int(ans["y_known"])
        scored.append(
            {
                "dispatch_id": row.get("dispatch_id"),
                "contract_id": cid,
                "condition": row.get("condition"),
                "family": row.get("family"),
                "cutoff_relation": ans.get("cutoff_relation"),
                "series_id": ans.get("series_id"),
                "p_success": p,
                "y_known": y,
                "brier": brier(p, y),
                "recognition_self_report": (row.get("parsed") or {}).get("recognition_self_report"),
                "confidence": (row.get("parsed") or {}).get("confidence"),
            }
        )
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in scored:
        groups[f"family={row['family']}"].append(row)
        groups[f"condition={row['condition']}"].append(row)
        groups[f"relation={row['cutoff_relation']}"].append(row)
        groups[f"condition={row['condition']}|relation={row['cutoff_relation']}"].append(row)
        groups[f"condition={row['condition']}|family={row['family']}"].append(row)
        groups[f"family={row['family']}|relation={row['cutoff_relation']}"].append(row)
    summary = {
        key: {
            "n": len(rows),
            "mean_brier": mean([float(row["brier"]) for row in rows]) if rows else None,
            "mean_p_success": mean([float(row["p_success"]) for row in rows]) if rows else None,
            "yes_rate": mean([int(row["y_known"]) for row in rows]) if rows else None,
        }
        for key, rows in sorted(groups.items())
    }
    outcome_summary = {
        key: {
            "n": len(rows),
            "mean_brier": mean([float(row["brier"]) for row in rows]) if rows else None,
            "mean_p_success": mean([float(row["p_success"]) for row in rows]) if rows else None,
        }
        for key, rows in sorted(
            {
                f"relation={rel}|y={y}": [
                    row
                    for row in scored
                    if str(row["cutoff_relation"]) == rel and int(row["y_known"]) == y
                ]
                for rel in ("pre_cutoff", "post_cutoff")
                for y in (0, 1)
            }.items()
        )
    }
    baseline_rows = []
    empirical_yes = mean([int(row["y_known"]) for row in scored]) if scored else 0.5
    yes_by_relation = {
        rel: mean([int(row["y_known"]) for row in scored if str(row["cutoff_relation"]) == rel])
        for rel in ("pre_cutoff", "post_cutoff")
        if any(str(row["cutoff_relation"]) == rel for row in scored)
    }
    for row in scored:
        y = int(row["y_known"])
        rel = str(row["cutoff_relation"])
        baseline_rows.append(
            {
                "contract_id": row["contract_id"],
                "family": row["family"],
                "cutoff_relation": rel,
                "brier_model": row["brier"],
                "brier_p50": brier(0.5, y),
                "brier_global_empirical_yes": brier(float(empirical_yes), y),
                "brier_relation_empirical_yes": brier(float(yes_by_relation.get(rel, empirical_yes)), y),
            }
        )
    baseline_summary = {
        key: mean([float(row[key]) for row in baseline_rows]) if baseline_rows else None
        for key in ("brier_model", "brier_p50", "brier_global_empirical_yes", "brier_relation_empirical_yes")
    }
    paired = []
    by_condition_family_series: dict[tuple[str, str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in scored:
        by_condition_family_series[(str(row["condition"]), str(row["family"]), str(row["series_id"]))][
            str(row["cutoff_relation"])
        ] = row
    for (condition, family, series_id), rels in sorted(by_condition_family_series.items()):
        if "pre_cutoff" in rels and "post_cutoff" in rels:
            paired.append(
                {
                    "condition": condition,
                    "family": family,
                    "series_id": series_id,
                    "pre_brier": rels["pre_cutoff"]["brier"],
                    "post_brier": rels["post_cutoff"]["brier"],
                    "post_minus_pre_brier": rels["post_cutoff"]["brier"] - rels["pre_cutoff"]["brier"],
                }
            )
    paired_values = [float(row["post_minus_pre_brier"]) for row in paired]
    family_paired = {}
    for family in sorted({str(row["family"]) for row in paired}):
        values = [float(row["post_minus_pre_brier"]) for row in paired if str(row["family"]) == family]
        family_paired[family] = {
            "n": len(values),
            "mean_post_minus_pre_brier": mean(values) if values else None,
            "bootstrap_ci_90": bootstrap_ci(values),
            "sign_flip_p_two_sided": sign_flip_p(values),
        }
    condition_paired = {}
    for condition in sorted({str(row["condition"]) for row in paired}):
        values = [float(row["post_minus_pre_brier"]) for row in paired if str(row["condition"]) == condition]
        condition_paired[condition] = {
            "n": len(values),
            "mean_post_minus_pre_brier": mean(values) if values else None,
            "bootstrap_ci_90": bootstrap_ci(values),
            "sign_flip_p_two_sided": sign_flip_p(values),
        }
    return {
        "schema": "gp245-fred-cutoff-pair-score-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "calls": relpath(calls_path),
        "calls_sha256": sha256_file(calls_path),
        "answer_key": relpath(answer_path),
        "answer_key_sha256": sha256_file(answer_path),
        "calls_rows": len(calls),
        "scored_rows": len(scored),
        "invalid_or_unscored_rows": invalid,
        "relation_counts": dict(sorted(Counter(row["cutoff_relation"] for row in scored).items())),
        "family_counts": dict(sorted(Counter(str(row["family"]) for row in scored).items())),
        "summary": summary,
        "outcome_summary": outcome_summary,
        "baseline_summary": baseline_summary,
        "paired_complete": len(paired),
        "paired_mean_post_minus_pre_brier": mean(paired_values) if paired_values else None,
        "paired_bootstrap_ci_90": bootstrap_ci(paired_values),
        "paired_sign_flip_p_two_sided": sign_flip_p(paired_values),
        "family_paired_summary": family_paired,
        "condition_paired_summary": condition_paired,
        "verdict": (
            "scored_full_blinded_value_control_panel"
            if len(scored) == 192
            and {str(row.get("condition")) for row in scored}
            == {"blinded_prior_no_cutoff_label", "blinded_value_given_no_cutoff_label"}
            else
            "scored_full_gemini_deepseek_panel"
            if len(scored) >= 196
            else "scored_partial_panel"
            if scored
            else "no_scored_rows"
        ),
        "scored_rows_detail": scored,
        "paired_rows": paired,
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# FRED Cutoff Pair Score Report",
        "",
        f"- Calls rows: `{report['calls_rows']}`",
        f"- Scored rows: `{report['scored_rows']}`",
        f"- Invalid/unscored rows: `{report['invalid_or_unscored_rows']}`",
        f"- Relation counts: `{report['relation_counts']}`",
        f"- Family counts: `{report['family_counts']}`",
        f"- Paired complete: `{report['paired_complete']}`",
        f"- Paired mean post-minus-pre Brier: `{report['paired_mean_post_minus_pre_brier']}`",
        f"- Paired bootstrap 90% CI: `{report['paired_bootstrap_ci_90']}`",
        f"- Paired sign-flip p: `{report['paired_sign_flip_p_two_sided']}`",
        f"- Verdict: `{report['verdict']}`",
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(report["summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Outcome-Stratified Summary",
        "",
        "```json",
        json.dumps(report["outcome_summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Baseline Summary",
        "",
        "```json",
        json.dumps(report["baseline_summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Family Paired Summary",
        "",
        "```json",
        json.dumps(report["family_paired_summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Condition Paired Summary",
        "",
        "```json",
        json.dumps(report["condition_paired_summary"], indent=2, sort_keys=True),
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calls", type=Path, default=DEFAULT_CALLS)
    parser.add_argument("--answer-key", type=Path, default=DEFAULT_ANSWER)
    parser.add_argument("--out-prefix", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = score(args.calls, args.answer_key)
    args.out_prefix.parent.mkdir(parents=True, exist_ok=True)
    args.out_prefix.with_suffix(".json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.out_prefix.with_suffix(".md").write_text(render_md(report), encoding="utf-8")
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "calls_rows",
                    "scored_rows",
                    "invalid_or_unscored_rows",
                    "relation_counts",
                    "family_counts",
                    "paired_complete",
                    "paired_mean_post_minus_pre_brier",
                    "paired_bootstrap_ci_90",
                    "paired_sign_flip_p_two_sided",
                    "verdict",
                )
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
