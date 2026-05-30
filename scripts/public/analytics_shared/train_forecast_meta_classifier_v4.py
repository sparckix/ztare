#!/usr/bin/env python3
"""Forecast meta-classifier v4 — push past v3's plateau.

v3 verdict: comparable to v2 (R² +0.015, MAE flat). The bottleneck is
that question_len + p_success account for 86% of feature importance,
swamping the F35/F37/F39/F41 factorial signals. Two changes in v4:

  1. DROP question_len. It's a corpus-bias dominator (Lean rows are
     long, apparatus rows are short — the classifier learns "long
     question → harder" which is structural, not calibration. Dropping
     forces the model to find signal in the actual calibration features.

  2. ADD agent × balance and agent × tail_format interaction features.
     F41 explicitly says balance helps claude only; F37 says signed-tail
     cancels claude's gap. The interaction is the per-family-rule signal
     made explicit. v3 had both as marginal features; v4 makes them
     compose.

Pre-registered pass-gate (BEFORE running):
  - v4 combined CV MAE must improve on v3 (0.1002) by >= 0.003, OR
  - v4 held-out v22+ MAE must improve on v3 (0.1525) by >= 0.005
  Either way demonstrates the new representation is load-bearing.

If both gates fail, v4 is also exploratory and the v2/v3 baseline holds.
"""
from __future__ import annotations
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.model_selection import KFold
from sklearn.preprocessing import OneHotEncoder

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "public" / "analytics_shared"))
from train_forecast_meta_classifier_v2 import (  # noqa: E402
    agent_family, domain_family, _normalize_row, _FAILURE_PAT,
    load_pool_rows, load_pilot_rows,
)
from train_forecast_meta_classifier_v3 import load_v22_pilot_rows  # noqa: E402


def featurize_v4(rows, fit_encoder=None):
    """v4 features: drop question_len, add per-family interaction features."""
    NUMERIC = ["p_success", "rationale_len",
               "rationale_word_count", "expected_cost"]
    # NOTE: question_len DROPPED — was dominating at 54% in v3 as a corpus-bias proxy
    OPT = [
        "p_dep", "p_lem", "p_reg",
        "tail_insurance_premium",
        "tail_signed_sum",
        "tail_signed_skew",
        "failure_mention_count",
    ]
    CAT = ["agent_family", "domain_family", "framing", "tail_format", "balance_instruction"]
    # v4 explicit interaction features. The F41 deployment rule says
    # "balance helps claude only" — encode that as an explicit feature so
    # the tree doesn't have to discover it from a sparse cross-product.
    INTERACTION_CAT = ["fam_balance_combo", "fam_tail_combo"]

    for r in rows:
        fam = _ensure_field(r, "agent_family")
        bal = _ensure_field(r, "balance_instruction")
        tf = _ensure_field(r, "tail_format")
        r["fam_balance_combo"] = f"{fam}__{bal}"
        r["fam_tail_combo"] = f"{fam}__{tf}"

    CAT_ALL = CAT + INTERACTION_CAT
    n = len(rows)
    Xn = np.zeros((n, len(NUMERIC) + len(OPT)))
    for i, r in enumerate(rows):
        for j, f in enumerate(NUMERIC):
            Xn[i, j] = r.get(f, 0) or 0
        for j, f in enumerate(OPT):
            v = r.get(f)
            Xn[i, len(NUMERIC) + j] = float(v) if isinstance(v, (int, float)) else -1.0
    cats = np.array([
        [_ensure_field(r, c) for c in CAT_ALL]
        for r in rows
    ])
    if fit_encoder is None:
        enc = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
        Xc = enc.fit_transform(cats)
    else:
        enc = fit_encoder
        Xc = enc.transform(cats)
    feat_names = NUMERIC + OPT + list(enc.get_feature_names_out(CAT_ALL))
    return np.hstack([Xn, Xc]), np.array([r["brier"] for r in rows]), enc, feat_names


def _ensure_field(r, key):
    v = r.get(key)
    if v is None or v == "":
        return "unknown"
    return str(v)


def main() -> int:
    print("=== Forecast Meta-Classifier v4 — drop question_len + add interaction features ===\n")

    print("Loading legacy sources...")
    pool = load_pool_rows()
    v10 = load_pilot_rows(
        "projects/llm_forecasting_calibration_program/calibration_channel_mechanism_v10/workspace/pilot_v10_calls.jsonl",
        "/tmp/ztare_calibration_channel_v10_ground_truth.json", "v10",
        corpus_path="projects/llm_forecasting_calibration_program/calibration_channel_mechanism_v10/workspace/corpus_v10.jsonl",
    )
    v10_1 = load_pilot_rows(
        "projects/llm_forecasting_calibration_program/calibration_channel_mechanism_v10/workspace/pilot_v10_1_calls.jsonl",
        "/tmp/ztare_forecaster_v1_3_ground_truth.json", "v10_1",
        corpus_path="projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/corpus_v1_3.jsonl",
    )
    v11 = load_pilot_rows(
        "projects/llm_forecasting_calibration_program/causal_probing_v11/workspace/pilot_v11_calls.jsonl",
        "/tmp/ztare_causal_probing_v11_ground_truth.json", "v11",
        corpus_path="projects/llm_forecasting_calibration_program/causal_probing_v11/workspace/corpus_v11.jsonl",
    )
    v6_1 = load_pilot_rows(
        "projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/workspace/pilot_v6_1_receiver_forecasts.jsonl",
        "/tmp/ztare_forecaster_v1_3_ground_truth.json", "v6_1",
        corpus_path="projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/corpus_v1_3.jsonl",
    )

    print("Loading v22+ pilots...")
    base = "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace"
    corpus_v22 = f"{base}/corpus_v22.jsonl"
    v22d = load_v22_pilot_rows(f"{base}/pilot_v22d_calls.jsonl", corpus_v22, "v22d")
    v22b = load_v22_pilot_rows(f"{base}/pilot_v22b_calls.jsonl", corpus_v22, "v22b")
    v22c = load_v22_pilot_rows(f"{base}/pilot_v22c_calls.jsonl", corpus_v22, "v22c")
    v22 = load_v22_pilot_rows(f"{base}/pilot_v22_calls.jsonl", corpus_v22, "v22")
    v23 = load_v22_pilot_rows(f"{base}/pilot_v23_calls.jsonl", corpus_v22, "v23")
    v24 = load_v22_pilot_rows(f"{base}/pilot_v24_calls.jsonl", corpus_v22, "v24")

    legacy_rows = pool + v10 + v10_1 + v11 + v6_1
    v22plus_rows = v22 + v22b + v22c + v22d + v23 + v24
    all_rows = legacy_rows + v22plus_rows

    print(f"\n  legacy n={len(legacy_rows)}  v22+ n={len(v22plus_rows)}  combined n={len(all_rows)}")

    # 1. Combined 5-fold CV
    X, y, enc, feat_names = featurize_v4(all_rows)
    print(f"\n=== Combined 5-fold CV (n={len(y)}, NO question_len + interactions) ===")
    kf = KFold(n_splits=5, shuffle=True, random_state=20260526)
    r2s, maes = [], []
    for fold, (tr, te) in enumerate(kf.split(X), 1):
        m = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=20260526)
        m.fit(X[tr], y[tr])
        ypte = m.predict(X[te])
        r2 = r2_score(y[te], ypte)
        mae = mean_absolute_error(y[te], ypte)
        r2s.append(r2); maes.append(mae)
        print(f"  fold {fold}: R² = {r2:+.3f}  MAE = {mae:.4f}")
    cv_r2 = float(np.mean(r2s)); cv_mae = float(np.mean(maes))
    print(f"  CV mean: R²={cv_r2:+.3f}  MAE={cv_mae:.4f}")

    # 2. Held-out v22+ test
    Xl, yl, encl, _ = featurize_v4(legacy_rows)
    Xv, yv, _, _ = featurize_v4(v22plus_rows, fit_encoder=encl)
    m_held = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=20260526)
    m_held.fit(Xl, yl)
    yv_pred = m_held.predict(Xv)
    held_r2 = r2_score(yv, yv_pred)
    held_mae = mean_absolute_error(yv, yv_pred)
    baseline_mae_v22plus = float(np.mean(np.abs(yv - np.mean(yl))))
    held_lift = baseline_mae_v22plus - held_mae
    print(f"\n=== HELD-OUT v22+ (train on legacy n={len(legacy_rows)}, predict v22+ n={len(v22plus_rows)}) ===")
    print(f"  R²={held_r2:+.3f}  MAE={held_mae:.4f}")
    print(f"  baseline-mean: MAE={baseline_mae_v22plus:.4f}")
    print(f"  lift over baseline: {held_lift:+.4f}")

    # 3. Verdict against v3
    V3_CV_MAE = 0.1002
    V3_HELD_MAE = 0.1525
    delta_cv = V3_CV_MAE - cv_mae
    delta_held = V3_HELD_MAE - held_mae
    print(f"\n=== v4 vs v3 verdict ===")
    print(f"  v3: CV MAE={V3_CV_MAE:.4f}  held-out MAE={V3_HELD_MAE:.4f}")
    print(f"  v4: CV MAE={cv_mae:.4f}  held-out MAE={held_mae:.4f}")
    print(f"  Δ:  CV MAE_reduction={delta_cv:+.4f}  held-out MAE_reduction={delta_held:+.4f}")
    if delta_cv >= 0.003 or delta_held >= 0.005:
        verdict = "v4-improves-on-v3"
        interpretation = "STRONG: dropping question_len + adding interactions improves prediction."
    elif delta_cv > -0.003 and delta_held > -0.005:
        verdict = "v4-comparable-to-v3"
        interpretation = "WEAK: v4 is on par with v3. The feature engineering is exploratory, not decisive."
    else:
        verdict = "v4-regresses"
        interpretation = "REGRESSION: v4 underperforms v3. question_len had real signal worth keeping."

    # 4. Top features
    m_full = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=20260526)
    m_full.fit(X, y)
    top = sorted(zip(feat_names, m_full.feature_importances_), key=lambda x: -x[1])[:20]
    print(f"\n=== Top features (v4 combined fit, top 20) ===")
    for name, imp in top:
        print(f"  {name:<50} importance = {imp:.4f}")

    # Per-source MAE
    yp_all = m_full.predict(X)
    per_source = {}
    for r, ypred in zip(all_rows, yp_all):
        per_source.setdefault(r["source_pilot"], []).append(abs(r["brier"] - ypred))
    print(f"\n=== Per-source MAE (v4 combined fit) ===")
    for src, errs in sorted(per_source.items()):
        print(f"  {src:<10} n={len(errs):>4}  MAE={np.mean(errs):.4f}")

    out_path = REPO / "analytics" / "public" / "forecast_pool" / "meta_classifier_v4_verdict.json"
    out_path.write_text(json.dumps({
        "schema": "forecast-meta-classifier-v4-verdict",
        "generated_at": "2026-05-26",
        "design_changes_vs_v3": [
            "DROP question_len (was 54% importance in v3, corpus-bias proxy)",
            "ADD fam_balance_combo categorical (agent_family × balance_instruction)",
            "ADD fam_tail_combo categorical (agent_family × tail_format)",
        ],
        "n_combined": len(all_rows),
        "n_features": int(X.shape[1]),
        "combined_cv_r2_mean": cv_r2,
        "combined_cv_mae_mean": cv_mae,
        "held_out_v22plus_r2": float(held_r2),
        "held_out_v22plus_mae": float(held_mae),
        "held_out_v22plus_baseline_mae": baseline_mae_v22plus,
        "held_out_v22plus_lift": float(held_lift),
        "v3_baseline_cv_mae": V3_CV_MAE,
        "v3_baseline_held_mae": V3_HELD_MAE,
        "delta_cv_mae_vs_v3": delta_cv,
        "delta_held_mae_vs_v3": delta_held,
        "verdict": verdict,
        "interpretation": interpretation,
        "top_features": [(n, float(i)) for n, i in top],
        "per_source_mae": {k: float(np.mean(v)) for k, v in per_source.items()},
    }, indent=2))
    print(f"\nVerdict: {verdict}")
    print(f"  {interpretation}")
    print(f"Written to: {out_path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
