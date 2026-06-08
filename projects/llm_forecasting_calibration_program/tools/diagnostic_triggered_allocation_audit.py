#!/usr/bin/env python3
"""No-call audit for diagnostic-triggered forecast allocation policies."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.ztare.experiment_stats import paired_permutation_test


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_OUT = PROGRAM / "nurture_intervention_v1/workspace"
DEFAULT_PILOTS = ("v28a_full__v25_external", "v28a_refill__v25_external")
FAMILIES = ("claude", "codex_55", "codex_54mini", "gemini", "deepseek")


def brier(p: float, y: int) -> float:
    return (p - y) ** 2


def hash_bucket(text: str, modulo: int) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % modulo


def parse_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def confident_no(p: float) -> float:
    if p < 0.10:
        return p + (0.65 - p) * 0.5
    return p


def trimmed_mean(values: list[float]) -> float:
    if len(values) <= 2:
        return statistics.mean(values)
    ordered = sorted(values)
    return statistics.mean(ordered[1:-1])


def load_rows(db: Path, pilot_ids: list[str]) -> list[dict[str, Any]]:
    placeholders = ",".join("?" for _ in pilot_ids)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        f"""
        SELECT pc.pilot_id, pc.contract_id, pc.family, pc.p_success, pc.parsed_json,
               c.y_known, c.source, c.source_corpus
        FROM pilot_calls pc
        JOIN contracts c ON c.contract_id = pc.contract_id
        WHERE pc.schema_ok = 1
          AND pc.p_success IS NOT NULL
          AND c.y_known IN (0, 1)
          AND pc.pilot_id IN ({placeholders})
        """,
        pilot_ids,
    ).fetchall()
    con.close()
    panels: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        parsed = parse_json(row["parsed_json"])
        tail = numeric(parsed.get("tail_insurance_premium"))
        key = (str(row["pilot_id"]), str(row["contract_id"]))
        panel = panels.setdefault(
            key,
            {
                "panel_id": f"{row['pilot_id']}|{row['contract_id']}",
                "pilot_id": str(row["pilot_id"]),
                "contract_id": str(row["contract_id"]),
                "source": row["source"] or "",
                "source_corpus": row["source_corpus"] or "",
                "y": int(row["y_known"]),
                "families": {},
                "tail_by_family": {},
            },
        )
        family = str(row["family"])
        panel["families"][family] = float(row["p_success"])
        if tail is not None:
            panel["tail_by_family"][family] = float(tail)

    out = []
    for panel in panels.values():
        if not all(family in panel["families"] for family in FAMILIES):
            continue
        if len(panel["tail_by_family"]) < len(FAMILIES):
            continue
        probs = list(panel["families"].values())
        tails = list(panel["tail_by_family"].values())
        panel["mean_p"] = statistics.mean(probs)
        panel["median_p"] = statistics.median(probs)
        panel["trimmed_mean_p"] = trimmed_mean(probs)
        panel["sigma_p"] = statistics.pstdev(probs)
        panel["avg_tail"] = statistics.mean(tails)
        panel["max_tail"] = max(tails)
        out.append(panel)
    out.sort(key=lambda row: row["panel_id"])
    return out


def best_family(train: list[dict[str, Any]]) -> str:
    scores = {
        family: statistics.mean(brier(row["families"][family], row["y"]) for row in train)
        for family in FAMILIES
    }
    return min(scores, key=scores.get)


def source_best_map(train: list[dict[str, Any]], fallback: str) -> dict[str, str]:
    out = {}
    for source in sorted({row["source"] for row in train}):
        group = [row for row in train if row["source"] == source]
        if len(group) < 5:
            continue
        scores = {
            family: statistics.mean(brier(row["families"][family], row["y"]) for row in group)
            for family in FAMILIES
        }
        out[source] = min(scores, key=scores.get)
    out["__fallback__"] = fallback
    return out


def threshold(train: list[dict[str, Any]], field: str, quantile: float) -> float:
    values = sorted(float(row[field]) for row in train)
    if not values:
        return 0.0
    idx = min(len(values) - 1, max(0, round((len(values) - 1) * quantile)))
    return values[idx]


def policy_probability(row: dict[str, Any], policy: str, ctx: dict[str, Any]) -> float:
    probs = list(row["families"].values())
    train_best = ctx["train_best"]
    if policy == "train_best_single":
        return row["families"][train_best]
    if policy == "source_best_single":
        family = ctx["source_best"].get(row["source"], ctx["source_best"]["__fallback__"])
        return row["families"][family]
    if policy == "mean_panel":
        return statistics.mean(probs)
    if policy == "median_panel":
        return statistics.median(probs)
    if policy == "trimmed_mean_panel":
        return trimmed_mean(probs)
    if policy == "confident_no_mean_panel":
        return statistics.mean(confident_no(p) for p in probs)
    if policy == "tail_trigger_mean_else_train_best":
        return statistics.mean(probs) if row["avg_tail"] >= ctx["tail_q75"] else row["families"][train_best]
    if policy == "tail_trigger_median_else_train_best":
        return statistics.median(probs) if row["avg_tail"] >= ctx["tail_q75"] else row["families"][train_best]
    if policy == "tail_trigger_trimmed_else_train_best":
        return trimmed_mean(probs) if row["avg_tail"] >= ctx["tail_q75"] else row["families"][train_best]
    if policy == "disagreement_trigger_mean_else_train_best":
        return statistics.mean(probs) if row["sigma_p"] >= ctx["sigma_q75"] else row["families"][train_best]
    if policy == "tail_or_disagreement_mean_else_train_best":
        if row["avg_tail"] >= ctx["tail_q75"] or row["sigma_p"] >= ctx["sigma_q75"]:
            return statistics.mean(probs)
        return row["families"][train_best]
    raise ValueError(f"unknown policy: {policy}")


POLICIES = (
    "train_best_single",
    "source_best_single",
    "mean_panel",
    "median_panel",
    "trimmed_mean_panel",
    "confident_no_mean_panel",
    "tail_trigger_mean_else_train_best",
    "tail_trigger_median_else_train_best",
    "tail_trigger_trimmed_else_train_best",
    "disagreement_trigger_mean_else_train_best",
    "tail_or_disagreement_mean_else_train_best",
)


def cross_validate(rows: list[dict[str, Any]], folds: int = 5) -> dict[str, Any]:
    values: dict[str, list[float]] = defaultdict(list)
    route_counts: dict[str, Counter[str]] = defaultdict(Counter)
    per_source: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    fold_contexts = {}
    for fold in range(folds):
        train = [row for row in rows if hash_bucket(row["panel_id"], folds) != fold]
        test = [row for row in rows if hash_bucket(row["panel_id"], folds) == fold]
        if not train or not test:
            continue
        ctx = {
            "train_best": best_family(train),
            "source_best": source_best_map(train, best_family(train)),
            "tail_q75": threshold(train, "avg_tail", 0.75),
            "sigma_q75": threshold(train, "sigma_p", 0.75),
        }
        fold_contexts[str(fold)] = {
            "n_train": len(train),
            "n_test": len(test),
            "train_best": ctx["train_best"],
            "tail_q75": round(ctx["tail_q75"], 6),
            "sigma_q75": round(ctx["sigma_q75"], 6),
        }
        for row in test:
            y = row["y"]
            for policy in POLICIES:
                p = policy_probability(row, policy, ctx)
                values[policy].append(brier(p, y))
                if "trigger" in policy:
                    fired = (
                        row["avg_tail"] >= ctx["tail_q75"]
                        if policy.startswith("tail_trigger")
                        else row["sigma_p"] >= ctx["sigma_q75"]
                        if policy.startswith("disagreement_trigger")
                        else row["avg_tail"] >= ctx["tail_q75"] or row["sigma_p"] >= ctx["sigma_q75"]
                    )
                    route_counts[policy]["triggered" if fired else "train_best"] += 1
                per_source[row["source"]][policy].append(brier(p, y))
    aggregate = {
        policy: {
            "brier": round(statistics.mean(scores), 6),
            "n": len(scores),
            "route_counts": dict(route_counts[policy]),
        }
        for policy, scores in sorted(values.items())
    }
    best_policy = min(aggregate, key=lambda policy: aggregate[policy]["brier"])
    comparisons = {}
    for baseline in ("train_best_single", "source_best_single", "mean_panel", "median_panel", "confident_no_mean_panel"):
        comparisons[baseline] = paired_permutation_test(values[best_policy], values[baseline], n_perm=5000, seed=42)
    source_rows = []
    for source, source_values in sorted(per_source.items()):
        source_scores = {
            policy: round(statistics.mean(scores), 6)
            for policy, scores in source_values.items()
            if scores
        }
        source_rows.append(
            {
                "source": source,
                "n": len(next(iter(source_values.values()))) if source_values else 0,
                "best_policy": min(source_scores, key=source_scores.get),
                "scores": source_scores,
            }
        )
    return {
        "fold_contexts": fold_contexts,
        "aggregate": aggregate,
        "best_policy": best_policy,
        "best_policy_comparisons": comparisons,
        "per_source": source_rows,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    pilot_ids = [part.strip() for part in args.pilot_ids.split(",") if part.strip()]
    rows = load_rows(args.db, pilot_ids)
    cv = cross_validate(rows)
    return {
        "schema": "gp245-n8-diagnostic-triggered-allocation-audit-v1",
        "db": str(args.db),
        "pilot_ids": pilot_ids,
        "rows": len(rows),
        "families": list(FAMILIES),
        "source_counts": dict(sorted(Counter(row["source"] for row in rows).items())),
        "outcome_counts": dict(sorted(Counter(row["y"] for row in rows).items())),
        "cv": cv,
        "interpretation": interpret(cv),
    }


def interpret(cv: dict[str, Any]) -> str:
    best = cv["best_policy"]
    aggregate = cv["aggregate"]
    triggered = [name for name in aggregate if "trigger" in name]
    best_trigger = min(triggered, key=lambda name: aggregate[name]["brier"]) if triggered else None
    best_simple = min(
        ("train_best_single", "source_best_single", "mean_panel", "median_panel", "trimmed_mean_panel", "confident_no_mean_panel"),
        key=lambda name: aggregate[name]["brier"],
    )
    if best == best_trigger and aggregate[best]["brier"] < aggregate[best_simple]["brier"]:
        return "diagnostic_triggered_allocation_candidate_survives_initial_cv"
    if best_trigger and aggregate[best_trigger]["brier"] < aggregate[best_simple]["brier"]:
        return "diagnostic_triggered_allocation_suggestive_not_best_overall"
    return "diagnostic_triggered_allocation_not_supported_over_simple_baselines"


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# N8 Diagnostic-Triggered Allocation Audit",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Rows: {report['rows']}",
        f"- Pilot IDs: `{report['pilot_ids']}`",
        f"- Source counts: `{report['source_counts']}`",
        f"- Outcome counts: `{report['outcome_counts']}`",
        f"- Interpretation: `{report['interpretation']}`",
        f"- Best policy: `{report['cv']['best_policy']}`",
        "",
        "## Aggregate CV Scores",
        "",
        "```json",
        json.dumps(report["cv"]["aggregate"], indent=2, sort_keys=True),
        "```",
        "",
        "## Best-Policy Comparisons",
        "",
        "```json",
        json.dumps(report["cv"]["best_policy_comparisons"], indent=2, sort_keys=True),
        "```",
        "",
        "## Per Source",
        "",
        "```json",
        json.dumps(report["cv"]["per_source"], indent=2, sort_keys=True),
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--pilot-ids", default=",".join(DEFAULT_PILOTS))
    args = parser.parse_args()
    report = build_report(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = "n8_diagnostic_triggered_allocation_audit"
    (args.out_dir / f"{stem}.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out_dir / f"{stem}.md").write_text(render_md(report), encoding="utf-8")
    print(f"wrote {args.out_dir / f'{stem}.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
