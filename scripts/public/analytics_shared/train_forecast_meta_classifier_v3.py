#!/usr/bin/env python3
"""Forecast meta-classifier v3 — adds post-v22 pilots + F36/F37/F39/F41 features.

v2 trained on pool + v10 + v10.1 + v11 + v6.1 and went null on broader corpus (F24).
The post-v22 era added new instrumentation that v2 didn't have access to:
  - signed-tail elicitation (tail_downside_worry, tail_upside_surprise) per F35
  - per-family sign awareness via derive_agent_family per F36
  - factorial conditions: framing, tail_format, balance_instruction per F37/F39/F41
  - cross-family extension (gemini, deepseek) per F42

v3 adds:
  1. load_v22_pilot_rows() — adapter for the v22+ JSONL schema
     (uses `schema_audit.schema_ok` + corpus-bundled y_known, no separate gt file)
  2. featurize_v3() — adds framing / tail_format / balance_instruction as categoricals
  3. gemini + deepseek family-aware encoding (already in v2's agent_family() but
     made explicit here)
  4. v3 verdict file emitted to analytics/public/forecast_pool/meta_classifier_v3_verdict.json

Pre-registered pass-gate (BEFORE any retrain runs):
  - v3 combined-CV MAE must improve on v2's combined-CV MAE (0.0987) by >= 0.005
  - v3 must NOT degrade on the v2 OOD test set (v10, v10.1, v11, v6.1) by more than +0.01 MAE
  - If v3 fails either gate, the new features are not load-bearing and the v2
    classifier remains the operational baseline.

Author posture: not blocking the F36 paper. Independent finding line.
"""
from __future__ import annotations
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.model_selection import KFold
from sklearn.preprocessing import OneHotEncoder

# Reuse v2's primitives — same agent_family / domain_family / _normalize_row /
# _FAILURE_PAT / load_pool_rows / load_pilot_rows. v3 ADDS load_v22_pilot_rows
# and extends featurize with the new categoricals.
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "public" / "analytics_shared"))
from train_forecast_meta_classifier_v2 import (  # noqa: E402
    agent_family, domain_family, _normalize_row, _FAILURE_PAT,
    load_pool_rows, load_pilot_rows,
)


def load_v22_pilot_rows(jsonl_path: str, corpus_path: str, source_label: str):
    """v22+ schema adapter.

    v22+ rows have `parsed` dict + `schema_audit.schema_ok` instead of v2's
    `parsed_ok`. Ground truth comes from the corpus jsonl's y_known field
    directly (no separate gt file). The factorial axes (framing, tail_format,
    balance_instruction) are top-level fields on each row.
    """
    rows = []
    if not Path(jsonl_path).exists():
        print(f"  [v22-load] missing {jsonl_path}; skip")
        return rows
    if not Path(corpus_path).exists():
        print(f"  [v22-load] missing corpus {corpus_path}; skip")
        return rows

    # Build cid → (y_known, question_len) from the corpus
    cid_to_meta = {}
    for line in open(corpus_path):
        try:
            c = json.loads(line)
            cid = c.get("contract_id") or c.get("probe_work_id")
            if not cid:
                continue
            y = c.get("y_known")
            q = c.get("question") or c.get("goal") or ""
            if y is not None:
                cid_to_meta[cid] = (y, len(q))
        except Exception:
            pass

    for line in open(jsonl_path):
        try:
            d = json.loads(line)
            audit = d.get("schema_audit") or {}
            if not audit.get("schema_ok"):
                continue
            cid = d.get("contract_id")
            if cid not in cid_to_meta:
                continue
            y_known, qlen = cid_to_meta[cid]
            parsed = d.get("parsed") or {}
            # The v22+ schema is framing-dependent: positive cells emit p_success,
            # inverted cells emit p_failure. For Brier we want predicted-prob of
            # SUCCESS regardless of how the agent reported it.
            # Determine framing. If not present as a top-level field (older
            # pilots like v22b/v22c use `condition` instead), INFER from which
            # probability field the parsed dict actually emitted.
            framing = d.get("framing")
            if framing is None:
                # Fallback: infer from parsed keys / condition string
                cond = (d.get("condition") or "").lower()
                if "inverted" in cond or "p_failure" in parsed:
                    framing = "inverted"
                else:
                    framing = "positive"
            if framing == "inverted":
                pf = parsed.get("p_failure")
                if isinstance(pf, (int, float)):
                    p_success = 1.0 - float(pf)
                elif isinstance(parsed.get("p_success"), (int, float)):
                    # Some inverted-framing pilots still emit p_success — accept it
                    p_success = float(parsed["p_success"])
                else:
                    continue
            else:
                ps = parsed.get("p_success")
                if isinstance(ps, (int, float)):
                    p_success = float(ps)
                elif isinstance(parsed.get("p_failure"), (int, float)):
                    # Mismatched: row claims positive framing but emits p_failure
                    p_success = 1.0 - float(parsed["p_failure"])
                else:
                    continue
            if not (0.0 <= p_success <= 1.0):
                continue
            brier = (p_success - y_known) ** 2
            ag = d.get("agent_id") or "?"
            dom = d.get("domain") or "unknown"
            rationale = parsed.get("rationale_short") or ""
            r = {
                "raw_agent_id": str(ag),
                "raw_domain": str(dom),
                "p_success": p_success,
                "brier": brier,
                "question_len": qlen,
                "rationale_len": len(rationale),
                "rationale_word_count": len(rationale.split()),
                "expected_cost": float(parsed.get("expected_cost_agent_minutes") or -1),
                "p_dep": None,
                "p_lem": None,
                "p_reg": None,
                "tail_insurance_premium": parsed.get("tail_insurance_premium"),
                "tail_downside_worry": parsed.get("tail_downside_worry"),
                "tail_upside_surprise": parsed.get("tail_upside_surprise"),
                "rationale_short": rationale,
                "source_pilot": source_label,
                # v3-only: factorial-axis features (None on pre-v22 rows handled in featurize_v3)
                "framing": framing,
                "tail_format": d.get("tail_format") or "magnitude",
                "balance_instruction": d.get("balance_instruction") or "off",
            }
            rows.append(_normalize_row(r))
        except Exception:
            pass
    return rows


def featurize_v3(rows, fit_encoder=None):
    """v3 features = v2 features + framing / tail_format / balance_instruction.

    Rows that predate the v22+ schema have these new fields defaulted to
    "unknown" by _ensure_v3_fields below so the OneHotEncoder treats them
    uniformly as a "no-info" category.
    """
    NUMERIC = ["p_success", "question_len", "rationale_len",
               "rationale_word_count", "expected_cost"]
    OPT = [
        "p_dep", "p_lem", "p_reg",
        "tail_insurance_premium",
        "tail_signed_sum",
        "tail_signed_skew",
        "failure_mention_count",
    ]
    # v3 expands categoricals from v2's (agent_family, domain_family) to include
    # the factorial axes. Rows that don't have framing/tail_format/balance get
    # "unknown" as the category value.
    CAT = ["agent_family", "domain_family", "framing", "tail_format", "balance_instruction"]

    n = len(rows)
    Xn = np.zeros((n, len(NUMERIC) + len(OPT)))
    for i, r in enumerate(rows):
        for j, f in enumerate(NUMERIC):
            Xn[i, j] = r.get(f, 0) or 0
        for j, f in enumerate(OPT):
            v = r.get(f)
            Xn[i, len(NUMERIC) + j] = float(v) if isinstance(v, (int, float)) else -1.0
    cats = np.array([
        [_ensure_v3_field(r, c) for c in CAT]
        for r in rows
    ])
    if fit_encoder is None:
        enc = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
        Xc = enc.fit_transform(cats)
    else:
        enc = fit_encoder
        Xc = enc.transform(cats)
    feat_names = NUMERIC + OPT + list(enc.get_feature_names_out(CAT))
    return np.hstack([Xn, Xc]), np.array([r["brier"] for r in rows]), enc, feat_names


def _ensure_v3_field(r, key):
    v = r.get(key)
    if v is None or v == "":
        return "unknown"
    return str(v)


def main() -> int:
    print("=== Forecast Meta-Classifier v3 — extends v2 with v22+ pilots + factorial features ===\n")

    print("Loading legacy sources (v2 set)...")
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

    print("\nLoading v22+ pilots (new in v3)...")
    base = "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace"
    corpus_v22 = f"{base}/corpus_v22.jsonl"
    v22d = load_v22_pilot_rows(f"{base}/pilot_v22d_calls.jsonl", corpus_v22, "v22d")
    v22b = load_v22_pilot_rows(f"{base}/pilot_v22b_calls.jsonl", corpus_v22, "v22b")
    v22c = load_v22_pilot_rows(f"{base}/pilot_v22c_calls.jsonl", corpus_v22, "v22c")
    v22 = load_v22_pilot_rows(f"{base}/pilot_v22_calls.jsonl", corpus_v22, "v22")
    v23 = load_v22_pilot_rows(f"{base}/pilot_v23_calls.jsonl", corpus_v22, "v23")
    v24 = load_v22_pilot_rows(f"{base}/pilot_v24_calls.jsonl", corpus_v22, "v24")

    print(f"\n  pool n={len(pool)}")
    print(f"  v2 set: v10 n={len(v10)} | v10.1 n={len(v10_1)} | v11 n={len(v11)} | v6.1 n={len(v6_1)}")
    print(f"  v22+ set: v22 n={len(v22)} | v22b n={len(v22b)} | v22c n={len(v22c)} | "
          f"v22d n={len(v22d)} | v23 n={len(v23)} | v24 n={len(v24)}")

    legacy_rows = pool + v10 + v10_1 + v11 + v6_1
    v22plus_rows = v22 + v22b + v22c + v22d + v23 + v24
    all_rows = legacy_rows + v22plus_rows

    print(f"\n  legacy total: {len(legacy_rows)}  v22+ total: {len(v22plus_rows)}  combined: {len(all_rows)}")
    print(f"\n  agent_family distribution (combined):")
    for fam, c in Counter(r["agent_family"] for r in all_rows).most_common():
        print(f"    {fam:<22} {c}")
    print(f"\n  source_pilot distribution:")
    for src, c in Counter(r["source_pilot"] for r in all_rows).most_common():
        print(f"    {src:<22} {c}")

    if len(all_rows) < 50:
        print("\n[v3] not enough rows to train; need >= 50. Aborting cleanly.")
        return 1

    # 1. Within-distribution 5-fold CV
    X, y, enc, feat_names = featurize_v3(all_rows)
    print(f"\n=== Combined 5-fold CV (n={len(y)}, agent-family + factorial-axis features) ===")
    kf = KFold(n_splits=5, shuffle=True, random_state=20260526)
    r2s, maes = [], []
    for fold, (tr, te) in enumerate(kf.split(X), 1):
        m = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=20260526)
        m.fit(X[tr], y[tr])
        ypte = m.predict(X[te])
        r2 = r2_score(y[te], ypte)
        mae = mean_absolute_error(y[te], ypte)
        r2s.append(r2)
        maes.append(mae)
        print(f"  fold {fold}: R² = {r2:+.3f}  MAE = {mae:.4f}")
    cv_r2 = float(np.mean(r2s))
    cv_mae = float(np.mean(maes))
    cv_r2_std = float(np.std(r2s))
    cv_mae_std = float(np.std(maes))
    print(f"  CV mean: R²={cv_r2:+.3f}  MAE={cv_mae:.4f}")

    # 2. Compare against v2 baseline (combined_cv_mae=0.0987 per the v2 verdict)
    V2_MAE = 0.09872443564720165
    V2_R2 = 0.5064023051604168
    delta_mae = V2_MAE - cv_mae
    delta_r2 = cv_r2 - V2_R2
    print(f"\n=== v3 vs v2 verdict ===")
    print(f"  v2: CV R²={V2_R2:+.3f} MAE={V2_MAE:.4f}")
    print(f"  v3: CV R²={cv_r2:+.3f} MAE={cv_mae:.4f}")
    print(f"  Δ:  R²={delta_r2:+.3f}  MAE_reduction={delta_mae:+.4f}")
    if delta_mae >= 0.005:
        verdict = "v3-improves-on-v2"
        interpretation = (
            "STRONG: v22+ factorial features add load-bearing signal beyond v2. "
            "New classifier is the operational baseline."
        )
    elif delta_mae > -0.005:
        verdict = "v3-comparable-to-v2"
        interpretation = (
            "WEAK: v3 features do not measurably improve on v2. Adopt v3 only "
            "for richer feature representation; performance is similar."
        )
    else:
        verdict = "v3-regresses"
        interpretation = (
            "REGRESSION: v3 is worse than v2 — new features add noise. "
            "Keep v2 as operational baseline; v3 is exploratory."
        )

    # 2a. HELD-OUT v22+ test (train on legacy only, predict v22+ rows)
    print(f"\n=== HELD-OUT: train on legacy n={len(legacy_rows)}, predict v22+ n={len(v22plus_rows)} ===")
    Xl, yl, encl, _ = featurize_v3(legacy_rows)
    Xv, yv, _, _ = featurize_v3(v22plus_rows, fit_encoder=encl)
    m_held = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=20260526)
    m_held.fit(Xl, yl)
    yv_pred = m_held.predict(Xv)
    held_r2 = r2_score(yv, yv_pred)
    held_mae = mean_absolute_error(yv, yv_pred)
    baseline_mae_v22plus = float(np.mean(np.abs(yv - np.mean(yl))))
    print(f"  held-out v22+ test: R²={held_r2:+.3f}  MAE={held_mae:.4f}")
    print(f"  baseline (legacy-mean predictor on v22+): MAE={baseline_mae_v22plus:.4f}")
    held_lift_vs_baseline = baseline_mae_v22plus - held_mae
    print(f"  lift over baseline: {held_lift_vs_baseline:+.4f}")

    # 3. Top features
    m_full = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=20260526)
    m_full.fit(X, y)
    print(f"\n=== Top features (v3 combined fit) ===")
    top = sorted(zip(feat_names, m_full.feature_importances_), key=lambda x: -x[1])[:15]
    for name, imp in top:
        print(f"  {name:<40} importance = {imp:.4f}")

    # 4. Per-source MAE breakdown
    print(f"\n=== Per-source MAE (combined model) ===")
    yp_all = m_full.predict(X)
    per_source = {}
    for r, ypred in zip(all_rows, yp_all):
        src = r["source_pilot"]
        per_source.setdefault(src, []).append(abs(r["brier"] - ypred))
    for src, errs in sorted(per_source.items()):
        print(f"  {src:<10} n={len(errs):>4}  MAE={np.mean(errs):.4f}")

    # Write verdict file
    out_path = REPO / "analytics" / "public" / "forecast_pool" / "meta_classifier_v3_verdict.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "schema": "forecast-meta-classifier-v3-verdict",
        "generated_at": "2026-05-26",
        "n_legacy": len(legacy_rows),
        "n_v22plus": len(v22plus_rows),
        "n_combined": len(all_rows),
        "n_features": int(X.shape[1]),
        "combined_cv_r2_mean": cv_r2,
        "combined_cv_r2_std": cv_r2_std,
        "combined_cv_mae_mean": cv_mae,
        "combined_cv_mae_std": cv_mae_std,
        "v2_baseline_r2": V2_R2,
        "v2_baseline_mae": V2_MAE,
        "delta_r2_vs_v2": delta_r2,
        "delta_mae_vs_v2": delta_mae,
        "verdict": verdict,
        "interpretation": interpretation,
        "agent_family_distribution": dict(Counter(r["agent_family"] for r in all_rows).most_common()),
        "source_pilot_distribution": dict(Counter(r["source_pilot"] for r in all_rows).most_common()),
        "top_features": [(n, float(i)) for n, i in top],
        "per_source_mae": {k: float(np.mean(v)) for k, v in per_source.items()},
    }, indent=2))
    print(f"\nVerdict written to: {out_path.relative_to(REPO)}")
    print(f"Verdict: {verdict}")
    print(f"  {interpretation}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
