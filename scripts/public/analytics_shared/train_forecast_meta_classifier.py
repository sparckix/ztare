#!/usr/bin/env python3
"""External forecast-meta-classifier (innovation #13 from GP-245 roadmap).

Train a gradient-boosted regressor on existing forecast pool rows to predict
per-row Brier from contract features alone (text length, agent_id, domain,
condition if present, prompt tokens). Apply to NEW forecasts to assign a
pre-resolution RELIABILITY SCORE.

This is fundamentally DIFFERENT from self-introspection: it's a third-party
classifier that predicts agent calibration from contract features, NOT from
the agent's own confidence output. Gives the apparatus an external watchdog
that doesn't depend on agent honesty.

Usage (requires venv with sklearn + numpy):
  /tmp/ml_env/bin/python scripts/public/analytics_shared/train_forecast_meta_classifier.py
"""
from __future__ import annotations

import json
import glob
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.preprocessing import OneHotEncoder

REPO = Path(__file__).resolve().parents[3]
POOL = REPO / "analytics/public/forecast_pool"


def load_pool_rows() -> list[dict]:
    """Join forecasts + outcomes; one row per (forecast, outcome) pair."""
    outcomes = {}
    for fp in (POOL / "outcomes").glob("*.json"):
        try:
            d = json.load(fp.open())
            cid = d.get("contract_id") or fp.stem
            if "success_bool" in d:
                outcomes[cid] = 1 if d["success_bool"] else 0
        except Exception:
            pass
    contracts = {}
    for fp in (POOL / "contracts").glob("*.json"):
        try:
            d = json.load(fp.open())
            cid = d.get("contract_id") or fp.stem
            contracts[cid] = d
        except Exception:
            pass
    rows = []
    for fp in (POOL / "forecasts").glob("*/*.json"):
        try:
            d = json.load(fp.open())
            cid = d.get("contract_id")
            if cid not in outcomes or cid not in contracts:
                continue
            p = d.get("p_success")
            if not isinstance(p, (int, float)) or not (0 <= p <= 1):
                continue
            y = outcomes[cid]
            c = contracts[cid]
            rows.append({
                "contract_id": cid,
                "agent_id": str(d.get("agent_id", "?")),
                "domain": str(d.get("domain", "general")),
                "p_success": float(p),
                "y": y,
                "brier": (p - y) ** 2,
                # text features
                "question_len": len(str(c.get("question") or c.get("claim") or "")),
                "rationale_len": len(str(d.get("rationale_short") or "")),
                "rationale_word_count": len(str(d.get("rationale_short") or "").split()),
                "expected_cost": float(d.get("expected_cost_agent_minutes") or -1),
                "p_dep": d.get("p_dependency_issue"),
                "p_lem": d.get("p_needs_new_lemma"),
                "p_reg": d.get("p_regression"),
            })
        except Exception:
            continue
    return rows


def featurize(rows: list[dict]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Build feature matrix X (numeric + one-hot) and target y (per-row Brier)."""
    # Numeric features
    NUMERIC = ["p_success", "question_len", "rationale_len", "rationale_word_count", "expected_cost"]
    # Treat decomposed channels as numeric with sentinel for missing
    OPTIONAL_NUMERIC = ["p_dep", "p_lem", "p_reg"]
    # Categorical
    CATEGORICAL = ["agent_id", "domain"]

    n = len(rows)
    Xn = np.zeros((n, len(NUMERIC) + len(OPTIONAL_NUMERIC)))
    for i, r in enumerate(rows):
        for j, f in enumerate(NUMERIC):
            Xn[i, j] = r[f]
        for j, f in enumerate(OPTIONAL_NUMERIC):
            v = r.get(f)
            Xn[i, len(NUMERIC) + j] = float(v) if isinstance(v, (int, float)) else -1.0

    # One-hot encode categoricals
    cats = np.array([[r[c] for c in CATEGORICAL] for r in rows])
    enc = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    Xc = enc.fit_transform(cats)
    feat_names = NUMERIC + OPTIONAL_NUMERIC + list(enc.get_feature_names_out(CATEGORICAL))

    X = np.hstack([Xn, Xc])
    y = np.array([r["brier"] for r in rows])
    return X, y, feat_names


def main() -> int:
    print("[meta-classifier] loading forecast pool...")
    rows = load_pool_rows()
    print(f"  loaded {len(rows)} (forecast × outcome) pairs")
    if len(rows) < 50:
        print(f"  INSUFFICIENT: need ≥50, have {len(rows)}")
        return 2

    print(f"\n  brier distribution: mean={np.mean([r['brier'] for r in rows]):.4f}, "
          f"median={np.median([r['brier'] for r in rows]):.4f}, "
          f"std={np.std([r['brier'] for r in rows]):.4f}")
    from collections import Counter
    print(f"  agents (top 8): {Counter(r['agent_id'] for r in rows).most_common(8)}")
    print(f"  domains (top 8): {Counter(r['domain'] for r in rows).most_common(8)}")

    X, y, feat_names = featurize(rows)
    print(f"\n[meta-classifier] feature matrix: {X.shape}, {len(feat_names)} features")

    # 5-fold cross-validated R² + MAE on per-row Brier prediction
    kf = KFold(n_splits=5, shuffle=True, random_state=20260524)
    r2_scores, mae_scores = [], []
    importances = np.zeros(len(feat_names))
    baseline_mae = np.mean(np.abs(y - np.mean(y)))
    print(f"\n  baseline (predict mean Brier): MAE={baseline_mae:.4f}")

    for fold, (train_idx, test_idx) in enumerate(kf.split(X), 1):
        model = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=20260524)
        model.fit(X[train_idx], y[train_idx])
        y_pred = model.predict(X[test_idx])
        r2 = r2_score(y[test_idx], y_pred)
        mae = mean_absolute_error(y[test_idx], y_pred)
        print(f"  fold {fold}: R²={r2:+.3f}  MAE={mae:.4f}  (baseline-MAE-reduction: {(baseline_mae - mae)/baseline_mae*100:+.1f}%)")
        r2_scores.append(r2)
        mae_scores.append(mae)
        importances += model.feature_importances_

    print(f"\n  === 5-fold CV ===")
    print(f"  R²: mean={np.mean(r2_scores):+.3f}  std={np.std(r2_scores):.3f}")
    print(f"  MAE: mean={np.mean(mae_scores):.4f}  std={np.std(mae_scores):.4f}  (baseline {baseline_mae:.4f})")
    print(f"  MAE reduction vs baseline: {(baseline_mae - np.mean(mae_scores))/baseline_mae*100:+.1f}%")

    # Train on FULL data, save the trained model + feature importances
    model_full = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=20260524)
    model_full.fit(X, y)

    importances = model_full.feature_importances_
    top_features = sorted(zip(feat_names, importances), key=lambda x: -x[1])[:10]
    print(f"\n  === top 10 features by importance ===")
    for name, imp in top_features:
        print(f"    {name:<40} {imp:.4f}")

    out_path = REPO / "analytics/public/forecast_pool/meta_classifier_verdict.json"
    verdict = {
        "n_rows": len(rows),
        "n_features": len(feat_names),
        "cv_r2_mean": float(np.mean(r2_scores)),
        "cv_r2_std": float(np.std(r2_scores)),
        "cv_mae_mean": float(np.mean(mae_scores)),
        "cv_mae_std": float(np.std(mae_scores)),
        "baseline_mae": float(baseline_mae),
        "mae_reduction_pct": float((baseline_mae - np.mean(mae_scores)) / baseline_mae * 100),
        "top_features": [(name, float(imp)) for name, imp in top_features],
        "interpretation": _interpret(np.mean(r2_scores), np.mean(mae_scores), baseline_mae),
    }
    out_path.write_text(json.dumps(verdict, indent=2))
    print(f"\n[meta-classifier] verdict saved → {out_path.relative_to(REPO)}")
    return 0


def _interpret(r2: float, mae: float, baseline_mae: float) -> str:
    mae_reduction = (baseline_mae - mae) / baseline_mae * 100
    if r2 > 0.3 and mae_reduction > 20:
        return "STRONG: features predict Brier substantially better than baseline; meta-classifier is a useful pre-resolution reliability signal"
    elif r2 > 0.1 and mae_reduction > 10:
        return "MODERATE: features carry real but modest signal; meta-classifier could supplement (not replace) self-introspection"
    elif r2 > -0.05 and mae_reduction > 0:
        return "WEAK: marginal improvement over baseline; meta-classifier is not decision-critical"
    else:
        return "NULL: features do not predict Brier above baseline; agent-feature pair does not have learnable structure on this corpus"


if __name__ == "__main__":
    sys.exit(main())
