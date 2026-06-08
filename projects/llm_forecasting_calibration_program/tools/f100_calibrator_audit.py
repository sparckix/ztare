#!/usr/bin/env python3
"""No-call calibration audit for F100 confident-NO.

Question: can a simple fitted calibrator beat the hand F100 confident-NO rule
under source-stratified out-of-fold evaluation, using only existing DB rows?
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from sklearn.feature_extraction import DictVectorizer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from src.ztare.experiment_stats import paired_permutation_test


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = PROGRAM / "forecaster_skill_calibration_v1/workspace"
DEFAULT_JSON = DEFAULT_OUT / "f100_calibrator_audit_2026_06_04_policy_scoreable.json"
DEFAULT_MD = DEFAULT_OUT / "f100_calibrator_audit_2026_06_04_policy_scoreable.md"
DEFAULT_PILOTS = ("v28a_full__v25_external", "v28a_refill__v25_external")
FAMILIES = ("claude", "codex_55", "codex_54mini", "gemini", "deepseek")
N_FOLDS = 5
MIN_SOURCE_CAL_ROWS = 30
TAIL_THRESHOLD = 0.10
TAIL_SHRINK_K = 20.0


def brier(p: float, y: int) -> float:
    return (p - y) ** 2


def clip_p(p: float) -> float:
    return min(0.999, max(0.001, float(p)))


def logit(p: float) -> float:
    p = clip_p(p)
    return math.log(p / (1.0 - p))


def confident_no(p: float) -> float:
    if p < 0.10:
        return p + (0.65 - p) * 0.5
    return p


def source_bucket(source: str | None, source_corpus: str | None) -> str:
    return str(source or source_corpus or "unknown")


def horizon_bucket(horizon: str | None) -> str:
    text = str(horizon or "")
    if "2025" in text:
        return "resolved_2025"
    if "2026-01" in text or "2026-02" in text or "2026-03" in text:
        return "resolved_2026_q1"
    if "2026-04" in text:
        return "resolved_2026_04"
    if "2026-05" in text:
        return "resolved_2026_05"
    return text[:32] or "unknown"


def load_panels(
    db: Path,
    pilot_ids: tuple[str, ...],
    *,
    use_policy_scoreable_view: bool = True,
) -> list[dict[str, Any]]:
    placeholders = ",".join("?" for _ in pilot_ids)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        if use_policy_scoreable_view:
            rows = con.execute(
                f"""
                SELECT pilot_id, contract_id, family, p_success,
                       y_known, source, source_corpus, horizon,
                       post_training_cutoff, question,
                       law_policy_scoreable_reason, dataset_family
                FROM v_policy_scoreable_calls
                WHERE schema_ok = 1
                  AND p_success IS NOT NULL
                  AND family IS NOT NULL
                  AND y_known IN (0, 1)
                  AND pilot_id IN ({placeholders})
                """,
                pilot_ids,
            ).fetchall()
        else:
            rows = con.execute(
                f"""
                SELECT pc.pilot_id, pc.contract_id, pc.family, pc.p_success,
                       c.y_known, c.source, c.source_corpus, c.horizon,
                       c.post_training_cutoff, c.question,
                       'legacy_current_label' AS law_policy_scoreable_reason,
                       NULL AS dataset_family
                FROM pilot_calls pc
                JOIN contracts c ON c.contract_id = pc.contract_id
                WHERE pc.schema_ok = 1
                  AND pc.p_success IS NOT NULL
                  AND pc.family IS NOT NULL
                  AND c.y_known IN (0, 1)
                  AND pc.pilot_id IN ({placeholders})
                """,
                pilot_ids,
            ).fetchall()
    finally:
        con.close()

    panels: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row["pilot_id"]), str(row["contract_id"]))
        panel = panels.setdefault(
            key,
            {
                "panel_id": f"{row['pilot_id']}|{row['contract_id']}",
                "pilot_id": str(row["pilot_id"]),
                "contract_id": str(row["contract_id"]),
                "source": source_bucket(row["source"], row["source_corpus"]),
                "source_corpus": str(row["source_corpus"] or ""),
                "horizon_bucket": horizon_bucket(row["horizon"]),
                "post_training_cutoff": int(row["post_training_cutoff"] or 0),
                "question_len": len(str(row["question"] or "")),
                "y": int(row["y_known"]),
                "law_policy_scoreable_reason": str(row["law_policy_scoreable_reason"] or ""),
                "dataset_family": str(row["dataset_family"] or ""),
                "families": {},
            },
        )
        family = str(row["family"])
        if family in FAMILIES:
            panel["families"][family] = clip_p(float(row["p_success"]))

    complete = [
        panel
        for panel in panels.values()
        if all(family in panel["families"] for family in FAMILIES)
    ]
    complete.sort(key=lambda row: row["panel_id"])
    return complete


def assign_source_stratified_folds(panels: list[dict[str, Any]], n_folds: int) -> dict[str, int]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in panels:
        by_source[row["source"]].append(row)
    assignment: dict[str, int] = {}
    for source, rows in by_source.items():
        for idx, row in enumerate(sorted(rows, key=lambda item: item["panel_id"])):
            assignment[row["panel_id"]] = idx % n_folds
    return assignment


def family_rows(panels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for panel in panels:
        for family in FAMILIES:
            rows.append(
                {
                    "panel_id": panel["panel_id"],
                    "family": family,
                    "p": panel["families"][family],
                    "y": panel["y"],
                    "source": panel["source"],
                    "source_corpus": panel["source_corpus"],
                    "horizon_bucket": panel["horizon_bucket"],
                    "post_training_cutoff": panel["post_training_cutoff"],
                    "question_len": panel["question_len"],
                    "law_policy_scoreable_reason": panel["law_policy_scoreable_reason"],
                    "dataset_family": panel["dataset_family"],
                }
            )
    return rows


def fit_global_isotonic(train_rows: list[dict[str, Any]]) -> IsotonicRegression:
    model = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    model.fit([row["p"] for row in train_rows], [row["y"] for row in train_rows])
    return model


def fit_source_isotonic(train_rows: list[dict[str, Any]]) -> tuple[IsotonicRegression, dict[str, IsotonicRegression]]:
    global_model = fit_global_isotonic(train_rows)
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in train_rows:
        by_source[row["source"]].append(row)
    models: dict[str, IsotonicRegression] = {}
    for source, rows in by_source.items():
        if len(rows) < MIN_SOURCE_CAL_ROWS or len({row["y"] for row in rows}) < 2:
            continue
        models[source] = fit_global_isotonic(rows)
    return global_model, models


def feature_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "logit_p": logit(row["p"]),
        "p": row["p"],
        "confident_no_p": confident_no(row["p"]),
        "family": row["family"],
        "source": row["source"],
        "source_corpus": row["source_corpus"],
        "horizon_bucket": row["horizon_bucket"],
        "post_training_cutoff": str(row["post_training_cutoff"]),
        "question_len_100": row["question_len"] / 100.0,
    }


def fit_logistic(train_rows: list[dict[str, Any]]):
    return make_pipeline(
        DictVectorizer(sparse=True),
        LogisticRegression(max_iter=2000, C=0.5, solver="liblinear", random_state=0),
    ).fit([feature_row(row) for row in train_rows], [row["y"] for row in train_rows])


def beta_mean(yes: float, n: float, *, alpha: float = 1.0, beta: float = 1.0) -> float:
    return (yes + alpha) / (n + alpha + beta)


def fit_tail_beta(train_rows: list[dict[str, Any]], threshold: float = TAIL_THRESHOLD) -> dict[str, Any]:
    tail_rows = [row for row in train_rows if row["p"] < threshold]
    global_yes = sum(row["y"] for row in tail_rows)
    global_n = len(tail_rows)
    global_theta = beta_mean(global_yes, global_n) if global_n else beta_mean(
        sum(row["y"] for row in train_rows), len(train_rows)
    )
    by_family: dict[str, dict[str, float]] = {}
    for family in FAMILIES:
        rows = [row for row in tail_rows if row["family"] == family]
        fam_yes = sum(row["y"] for row in rows)
        fam_n = len(rows)
        theta = (fam_yes + TAIL_SHRINK_K * global_theta) / (fam_n + TAIL_SHRINK_K)
        by_family[family] = {"n": float(fam_n), "yes": float(fam_yes), "theta": theta}
    by_source_family: dict[tuple[str, str], dict[str, float]] = {}
    for source in sorted({row["source"] for row in train_rows}):
        for family in FAMILIES:
            rows = [row for row in tail_rows if row["source"] == source and row["family"] == family]
            sf_yes = sum(row["y"] for row in rows)
            sf_n = len(rows)
            fam_theta = by_family[family]["theta"]
            theta = (sf_yes + TAIL_SHRINK_K * fam_theta) / (sf_n + TAIL_SHRINK_K)
            by_source_family[(source, family)] = {"n": float(sf_n), "yes": float(sf_yes), "theta": theta}
    return {
        "threshold": threshold,
        "global_n": global_n,
        "global_yes": global_yes,
        "global_theta": global_theta,
        "by_family": by_family,
        "by_source_family": by_source_family,
    }


def tail_beta_predict(
    row: dict[str, Any],
    fit: dict[str, Any],
    *,
    level: str,
    lam: float = 0.5,
) -> float:
    if row["p"] >= fit["threshold"]:
        return row["p"]
    if level == "global":
        theta = fit["global_theta"]
    elif level == "family":
        theta = fit["by_family"][row["family"]]["theta"]
    elif level == "source_family":
        theta = fit["by_source_family"].get(
            (row["source"], row["family"]),
            {"theta": fit["by_family"][row["family"]]["theta"]},
        )["theta"]
    else:
        raise ValueError(f"unknown tail beta level: {level}")
    return clip_p((1.0 - lam) * row["p"] + lam * theta)


def best_family(train_panels: list[dict[str, Any]]) -> str:
    scores = {
        family: statistics.mean(brier(panel["families"][family], panel["y"]) for panel in train_panels)
        for family in FAMILIES
    }
    return min(scores, key=scores.get)


def source_best_map(train_panels: list[dict[str, Any]], fallback: str) -> dict[str, str]:
    out = {"__fallback__": fallback}
    for source in sorted({row["source"] for row in train_panels}):
        group = [row for row in train_panels if row["source"] == source]
        if len(group) < 5:
            continue
        scores = {
            family: statistics.mean(brier(panel["families"][family], panel["y"]) for panel in group)
            for family in FAMILIES
        }
        out[source] = min(scores, key=scores.get)
    return out


def evaluate(panels: list[dict[str, Any]], n_folds: int) -> dict[str, Any]:
    folds = assign_source_stratified_folds(panels, n_folds)
    predictions: list[dict[str, Any]] = []
    fold_sizes = Counter(folds.values())

    for fold in range(n_folds):
        train_panels = [row for row in panels if folds[row["panel_id"]] != fold]
        test_panels = [row for row in panels if folds[row["panel_id"]] == fold]
        train_family_rows = family_rows(train_panels)
        global_iso, source_iso = fit_source_isotonic(train_family_rows)
        logistic = fit_logistic(train_family_rows)
        tail_beta = fit_tail_beta(train_family_rows)
        train_best = best_family(train_panels)
        source_best = source_best_map(train_panels, train_best)

        for panel in test_panels:
            fam_rows = [
                {
                    "panel_id": panel["panel_id"],
                    "family": family,
                    "p": panel["families"][family],
                    "y": panel["y"],
                    "source": panel["source"],
                    "source_corpus": panel["source_corpus"],
                    "horizon_bucket": panel["horizon_bucket"],
                    "post_training_cutoff": panel["post_training_cutoff"],
                    "question_len": panel["question_len"],
                    "law_policy_scoreable_reason": panel["law_policy_scoreable_reason"],
                    "dataset_family": panel["dataset_family"],
                }
                for family in FAMILIES
            ]
            source_model = source_iso.get(panel["source"], global_iso)
            logistic_ps = logistic.predict_proba([feature_row(row) for row in fam_rows])[:, 1]
            row_predictions = {
                "raw_mean_panel": statistics.mean(row["p"] for row in fam_rows),
                "confident_no_mean_panel": statistics.mean(confident_no(row["p"]) for row in fam_rows),
                "global_isotonic_mean_panel": statistics.mean(
                    float(global_iso.predict([row["p"]])[0]) for row in fam_rows
                ),
                "source_isotonic_mean_panel": statistics.mean(
                    float(source_model.predict([row["p"]])[0]) for row in fam_rows
                ),
                "logistic_context_mean_panel": statistics.mean(float(p) for p in logistic_ps),
                "tail_beta_global_mean_panel": statistics.mean(
                    tail_beta_predict(row, tail_beta, level="global") for row in fam_rows
                ),
                "tail_beta_family_mean_panel": statistics.mean(
                    tail_beta_predict(row, tail_beta, level="family") for row in fam_rows
                ),
                "tail_beta_source_family_mean_panel": statistics.mean(
                    tail_beta_predict(row, tail_beta, level="source_family") for row in fam_rows
                ),
                "train_best_single": panel["families"][train_best],
                "source_best_single": panel["families"][source_best.get(panel["source"], train_best)],
            }
            predictions.append(
                {
                    "panel_id": panel["panel_id"],
                    "contract_id": panel["contract_id"],
                    "source": panel["source"],
                    "fold": fold,
                    "y": panel["y"],
                    "predictions": row_predictions,
                }
            )

    policies = sorted(predictions[0]["predictions"]) if predictions else []
    policy_scores: dict[str, dict[str, Any]] = {}
    for policy in policies:
        briers = [brier(row["predictions"][policy], row["y"]) for row in predictions]
        policy_scores[policy] = {
            "n": len(briers),
            "mean_brier": round(statistics.mean(briers), 6),
        }

    reference = "confident_no_mean_panel"
    ref_briers = [brier(row["predictions"][reference], row["y"]) for row in predictions]
    for policy in policies:
        candidate = [brier(row["predictions"][policy], row["y"]) for row in predictions]
        test = paired_permutation_test(candidate, ref_briers, n_perm=5000, seed=42)
        policy_scores[policy]["delta_vs_confident_no"] = round(
            policy_scores[policy]["mean_brier"] - policy_scores[reference]["mean_brier"], 6
        )
        policy_scores[policy]["paired_vs_confident_no"] = test

    by_source: dict[str, dict[str, dict[str, Any]]] = {}
    for source in sorted({row["source"] for row in predictions}):
        source_rows = [row for row in predictions if row["source"] == source]
        by_source[source] = {}
        for policy in policies:
            briers = [brier(row["predictions"][policy], row["y"]) for row in source_rows]
            by_source[source][policy] = {
                "n": len(briers),
                "mean_brier": round(statistics.mean(briers), 6),
            }

    best_policy = min(policy_scores, key=lambda key: policy_scores[key]["mean_brier"])
    return {
        "n_panels": len(panels),
        "n_family_rows": len(panels) * len(FAMILIES),
        "fold_sizes": {str(k): v for k, v in sorted(fold_sizes.items())},
        "source_counts": dict(Counter(row["source"] for row in panels)),
        "scoreable_reason_counts": dict(Counter(row["law_policy_scoreable_reason"] for row in panels)),
        "dataset_family_counts": dict(Counter(row["dataset_family"] or "non_dataset_source" for row in panels)),
        "policies": policy_scores,
        "by_source": by_source,
        "best_policy": best_policy,
        "verdict": verdict(policy_scores, by_source, best_policy),
        "predictions": predictions,
    }


def verdict(policy_scores: dict[str, dict[str, Any]], by_source: dict[str, Any], best_policy: str) -> str:
    if best_policy == "confident_no_mean_panel":
        return "hand_f100_still_best"
    best = policy_scores[best_policy]
    delta = best["delta_vs_confident_no"]
    p_value = best["paired_vs_confident_no"].get("p_value")
    if delta < -0.01 and p_value is not None and p_value <= 0.05:
        ref = "confident_no_mean_panel"
        major_sources = [
            source for source, scores in by_source.items()
            if scores.get(ref, {}).get("n", 0) >= 20
        ]
        if all(
            by_source[source][best_policy]["mean_brier"] <= by_source[source][ref]["mean_brier"]
            for source in major_sources
        ):
            return "calibrator_promotable_to_confirmation"
    return "calibrator_not_promoted"


def render_md(result: dict[str, Any], pilot_ids: tuple[str, ...]) -> str:
    lines = [
        "# F100 Calibrator Audit (2026-06-04)",
        "",
        "No-call source-stratified audit over complete five-family public panels.",
        "",
        f"- Pilots: `{', '.join(pilot_ids)}`.",
        f"- Scoreable filter: `{result['scoreable_filter']}`.",
        f"- Panels: `{result['n_panels']}`; family rows: `{result['n_family_rows']}`.",
        f"- Source counts: `{json.dumps(result['source_counts'], sort_keys=True)}`.",
        f"- Scoreable reasons: `{json.dumps(result['scoreable_reason_counts'], sort_keys=True)}`.",
        f"- Dataset families: `{json.dumps(result['dataset_family_counts'], sort_keys=True)}`.",
        f"- Verdict: `{result['verdict']}`.",
        f"- Best policy: `{result['best_policy']}`.",
        "",
        "## Overall",
        "",
        "| policy | mean Brier | delta vs confident-NO | p vs confident-NO |",
        "|---|---:|---:|---:|",
    ]
    for policy, row in sorted(result["policies"].items(), key=lambda item: item[1]["mean_brier"]):
        p = row["paired_vs_confident_no"].get("p_value")
        lines.append(
            f"| `{policy}` | `{row['mean_brier']:.6f}` | "
            f"`{row['delta_vs_confident_no']:+.6f}` | `{p}` |"
        )
    lines.extend(["", "## Source Split", ""])
    for source, scores in result["by_source"].items():
        lines.append(f"### {source}")
        lines.append("")
        lines.append("| policy | n | mean Brier |")
        lines.append("|---|---:|---:|")
        for policy, row in sorted(scores.items(), key=lambda item: item[1]["mean_brier"]):
            lines.append(f"| `{policy}` | `{row['n']}` | `{row['mean_brier']:.6f}` |")
        lines.append("")
    lines.extend(
        [
            "## Promotion Rule",
            "",
            "A fitted calibrator promotes only if it beats confident-NO mean-panel by at least `0.01` Brier overall, paired `p<=0.05`, and does not lose to confident-NO in any major source cell (`n>=20`).",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--pilots", nargs="+", default=list(DEFAULT_PILOTS))
    parser.add_argument("--folds", type=int, default=N_FOLDS)
    parser.add_argument(
        "--legacy-current-labels",
        action="store_true",
        help="Use direct contracts.y_known filtering instead of v_policy_scoreable_calls.",
    )
    args = parser.parse_args()

    pilot_ids = tuple(args.pilots)
    panels = load_panels(
        args.db,
        pilot_ids,
        use_policy_scoreable_view=not args.legacy_current_labels,
    )
    if len(panels) < args.folds * 5:
        raise SystemExit(f"not enough complete panels for {args.folds} folds: {len(panels)}")
    result = evaluate(panels, args.folds)
    result["pilot_ids"] = list(pilot_ids)
    result["db"] = str(args.db)
    result["scoreable_filter"] = (
        "legacy_contracts_y_known" if args.legacy_current_labels else "v_policy_scoreable_calls"
    )
    args.out_json.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    args.out_md.write_text(render_md(result, pilot_ids), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("n_panels", "best_policy", "verdict")}, indent=2))


if __name__ == "__main__":
    main()
