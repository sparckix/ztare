#!/usr/bin/env python3
"""F18 v2: meta-classifier with AGENT-FAMILY and DOMAIN-FAMILY aggregation.

Fixes F24's OOD-generalization failure: original F18 one-hot encoded raw
agent_ids (claude_rd, claude_v10, etc.) → unseen agents went to zero vector.
v2 aggregates agent_id → family ("claude_family", "codex_5_family",
"codex_5mini_family", "other") so new pilot agents inherit family signal.

Tests:
  1. Within-distribution 5-fold CV on combined pool + v10 + v10.1 + v6.1 + v11
  2. OOD: train on pool only, test on each new pilot

Run: /tmp/ml_env/bin/python scripts/public/analytics_shared/train_forecast_meta_classifier_v2.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from collections import Counter

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.preprocessing import OneHotEncoder

REPO = Path("/Users/daalami/figs_activist_loop")
POOL = REPO / "analytics/public/forecast_pool"


def agent_family(agent_id: str) -> str:
    """Aggregate raw agent_id → family. Generalizable across pilots."""
    aid = (agent_id or "").lower()
    if "claude" in aid:
        return "claude_family"
    if "codex" in aid and "54mini" in aid:
        return "codex_5mini_family"
    if "codex" in aid and "55" in aid:
        return "codex_5large_family"
    if "codex" in aid:
        return "codex_family_other"
    if "gemini" in aid:
        return "gemini_family"
    if "deepseek" in aid:
        return "deepseek_family"
    if "meta_darwin" in aid or "darwin" in aid:
        return "meta_darwin_family"
    if "research_director" in aid or aid.endswith("_rd"):
        return "rd_family_other"
    # Named-mutator predictor classes (Church4, Curry4, Bayes, Euler, etc.)
    if aid and aid[0].isupper() and len(aid) < 30:
        return "named_mutator_family"
    return "other"


def domain_family(domain: str) -> str:
    """Aggregate domain → family."""
    d = (domain or "").lower()
    if "ns" in d or "navier" in d: return "ns_family"
    if "gp225" in d: return "gp225_family"
    if "lean" in d: return "lean_family"
    if "external" in d or "apparatus_v10" in d or "external_v1_3" in d: return "external_family"
    if "gp225" in d or "apparatus" in d: return "apparatus_family"
    if "general" in d: return "general_family"
    return "other_family"


def load_pool_rows():
    outcomes = {}
    for fp in (POOL / "outcomes").glob("*.json"):
        try:
            d = json.load(fp.open())
            cid = d.get("contract_id") or fp.stem
            if "success_bool" in d: outcomes[cid] = 1 if d["success_bool"] else 0
        except: pass
    contracts = {}
    for fp in (POOL / "contracts").glob("*.json"):
        try:
            d = json.load(fp.open()); contracts[d.get("contract_id") or fp.stem] = d
        except: pass
    rows = []
    for fp in (POOL / "forecasts").glob("*/*.json"):
        try:
            d = json.load(fp.open()); cid = d.get("contract_id")
            if cid not in outcomes or cid not in contracts: continue
            p = d.get("p_success")
            if not isinstance(p, (int, float)) or not (0 <= p <= 1): continue
            y = outcomes[cid]; c = contracts[cid]
            rows.append(_normalize_row({
                "raw_agent_id": str(d.get("agent_id", "?")),
                "raw_domain": str(d.get("domain", "general")),
                "p_success": float(p), "brier": (p - y) ** 2,
                "question_len": len(str(c.get("question") or c.get("claim") or "")),
                "rationale_len": len(str(d.get("rationale_short") or "")),
                "rationale_word_count": len(str(d.get("rationale_short") or "").split()),
                "expected_cost": float(d.get("expected_cost_agent_minutes") or -1),
                "p_dep": d.get("p_dependency_issue"), "p_lem": d.get("p_needs_new_lemma"), "p_reg": d.get("p_regression"),
                # F8/F35/F36 channels (None when emitter predates schema change)
                "tail_insurance_premium": d.get("tail_insurance_premium"),
                "tail_downside_worry": d.get("tail_downside_worry"),
                "tail_upside_surprise": d.get("tail_upside_surprise"),
                "rationale_short": d.get("rationale_short") or "",
                "source_pilot": "pool",
            }))
        except: pass
    return rows


def load_pilot_rows(jsonl_path, gt_path, source_label, corpus_path=None):
    """Load pilot rows. If corpus_path given, JOIN to fetch real question_len."""
    rows = []
    if not Path(jsonl_path).exists(): return rows
    if not Path(gt_path).exists(): return rows
    gt = json.loads(Path(gt_path).read_text())
    # Build cid→question_len lookup from corpus jsonl if provided
    cid_to_qlen = {}
    if corpus_path and Path(corpus_path).exists():
        for line in open(corpus_path):
            try:
                c = json.loads(line)
                cid = c.get("contract_id") or c.get("probe_work_id")
                q = c.get("question") or c.get("goal") or ""
                if cid: cid_to_qlen[cid] = len(q)
            except: pass
    for line in open(jsonl_path):
        try:
            d = json.loads(line)
            if not d.get("parsed_ok"): continue
            cid = d.get("contract_id") or d.get("probe_work_id")
            if cid not in gt: continue
            p = (d.get("parsed") or {}).get("p_success") or (d.get("parsed") or {}).get("p_will_close")
            if not isinstance(p, (int, float)) or not (0 <= p <= 1): continue
            y = gt[cid]
            if isinstance(y, dict): y = y.get("resolved_to")
            if y is None: continue
            parsed = d.get("parsed") or {}
            ag = d.get("agent_id") or d.get("receiver_agent_id") or "?"
            dom = d.get("source_pool") or d.get("task_type") or "unknown"
            qlen = cid_to_qlen.get(cid, 250)  # fallback only if corpus join missed
            rows.append(_normalize_row({
                "raw_agent_id": str(ag), "raw_domain": str(dom),
                "p_success": float(p), "brier": (p - y) ** 2,
                "question_len": qlen,
                "rationale_len": len(parsed.get("rationale_short", "")),
                "rationale_word_count": len(parsed.get("rationale_short", "").split()),
                "expected_cost": float(parsed.get("expected_cost_agent_minutes") or -1),
                "p_dep": None, "p_lem": None, "p_reg": None,
                # F8/F35/F36 channels surfaced from pilot rows
                "tail_insurance_premium": parsed.get("tail_insurance_premium"),
                "tail_downside_worry": parsed.get("tail_downside_worry"),
                "tail_upside_surprise": parsed.get("tail_upside_surprise"),
                "rationale_short": parsed.get("rationale_short") or "",
                "source_pilot": source_label,
            }))
        except: pass
    return rows


def _normalize_row(r):
    r["agent_family"] = agent_family(r["raw_agent_id"])
    r["domain_family"] = domain_family(r["raw_domain"])
    # F35 / F37 / F38 derived features (2026-05-25): all default to None if absent
    # so older pool rows that predate the schema change are still consumable.
    dw = r.get("tail_downside_worry")
    us = r.get("tail_upside_surprise")
    if isinstance(dw, (int, float)) and isinstance(us, (int, float)):
        r["tail_signed_sum"] = float(dw) + float(us)   # total uncertainty intensity from signed split
        r["tail_signed_skew"] = float(dw) - float(us)  # directional skew: positive = downside-heavy
    else:
        r["tail_signed_sum"] = None
        r["tail_signed_skew"] = None
    # F38 rationale-diff finding: failure-mention count is a usable signal of
    # whether the rationale engaged the failure side. Computed inline so the
    # feature is always available regardless of which dispatcher produced the row.
    rat = r.get("rationale_short") or ""
    if rat:
        r["failure_mention_count"] = len(_FAILURE_PAT.findall(rat))
    else:
        r["failure_mention_count"] = None
    return r


# F38 rationale-diff: count of failure-mode mentions in rationale_short. Same regex
# as the v22 rationale-diff analysis so the classifier feature matches the
# H22e operationalization.
_FAILURE_PAT = re.compile(
    r"\b(fail|fails|failed|failure|miss|misses|missing|wrong|err|errors?|risk|risks|risky|"
    r"obstruct|block|blocked|cannot|won't|will not|not be able|unable|impossible|hard|"
    r"difficult|tough|unlikely|low chance|gap|inadequate|insufficient|breaks?|broken|"
    r"fall short)\b",
    re.I,
)


def featurize(rows, fit_encoder=None):
    NUMERIC = ["p_success", "question_len", "rationale_len", "rationale_word_count", "expected_cost"]
    # OPT fields are nullable; encoded as -1 sentinel when absent so the
    # GradientBoosting tree can split on the missingness.
    OPT = [
        "p_dep", "p_lem", "p_reg",
        # F8 legacy magnitude channel — kept for backward-compat; F36 per-family sign rule applies
        "tail_insurance_premium",
        # F35 signed-tail derived features
        "tail_signed_sum",
        "tail_signed_skew",
        # F38 rationale-diff feature
        "failure_mention_count",
    ]
    CAT = ["agent_family", "domain_family"]  # AGGREGATED — generalizes OOD
    n = len(rows)
    Xn = np.zeros((n, len(NUMERIC) + len(OPT)))
    for i, r in enumerate(rows):
        for j, f in enumerate(NUMERIC): Xn[i, j] = r.get(f, 0) or 0
        for j, f in enumerate(OPT):
            v = r.get(f); Xn[i, len(NUMERIC) + j] = float(v) if isinstance(v, (int, float)) else -1.0
    cats = np.array([[r[c] for c in CAT] for r in rows])
    if fit_encoder is None:
        enc = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
        Xc = enc.fit_transform(cats)
    else:
        enc = fit_encoder; Xc = enc.transform(cats)
    feat_names = NUMERIC + OPT + list(enc.get_feature_names_out(CAT))
    return np.hstack([Xn, Xc]), np.array([r["brier"] for r in rows]), enc, feat_names


def main() -> int:
    print("Loading all sources...")
    pool = load_pool_rows()
    v10  = load_pilot_rows("projects/llm_forecasting_calibration_program/calibration_channel_mechanism_v10/workspace/pilot_v10_calls.jsonl",
                           "/tmp/ztare_calibration_channel_v10_ground_truth.json", "v10",
                           corpus_path="projects/llm_forecasting_calibration_program/calibration_channel_mechanism_v10/workspace/corpus_v10.jsonl")
    v10_1 = load_pilot_rows("projects/llm_forecasting_calibration_program/calibration_channel_mechanism_v10/workspace/pilot_v10_1_calls.jsonl",
                            "/tmp/ztare_forecaster_v1_3_ground_truth.json", "v10_1",
                            corpus_path="projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/corpus_v1_3.jsonl")
    v11   = load_pilot_rows("projects/llm_forecasting_calibration_program/causal_probing_v11/workspace/pilot_v11_calls.jsonl",
                            "/tmp/ztare_causal_probing_v11_ground_truth.json", "v11",
                            corpus_path="projects/llm_forecasting_calibration_program/causal_probing_v11/workspace/corpus_v11.jsonl")
    v6_1  = load_pilot_rows("projects/llm_forecasting_calibration_program/forecast_insurance_calibration_v1/workspace/pilot_v6_1_receiver_forecasts.jsonl",
                            "/tmp/ztare_forecaster_v1_3_ground_truth.json", "v6_1",
                            corpus_path="projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/corpus_v1_3.jsonl")
    print(f"  pool n={len(pool)} | v10 n={len(v10)} | v10.1 n={len(v10_1)} | v11 n={len(v11)} | v6.1 n={len(v6_1)}")

    print(f"\n  agent_family distribution (combined):")
    all_rows = pool + v10 + v10_1 + v11 + v6_1
    for fam, c in Counter(r["agent_family"] for r in all_rows).most_common():
        print(f"    {fam:<22} {c}")

    # 1. Within-distribution combined CV
    X, y, enc, feat_names = featurize(all_rows)
    print(f"\n=== Combined 5-fold CV (n={len(y)}, agent-family aggregated) ===")
    kf = KFold(n_splits=5, shuffle=True, random_state=20260524)
    r2s, maes = [], []
    for fold, (tr, te) in enumerate(kf.split(X), 1):
        m = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=20260524)
        m.fit(X[tr], y[tr]); ypte = m.predict(X[te])
        r2 = r2_score(y[te], ypte); mae = mean_absolute_error(y[te], ypte)
        r2s.append(r2); maes.append(mae)
        print(f"  fold {fold}: R² = {r2:+.3f}  MAE = {mae:.4f}")
    print(f"  CV mean: R²={np.mean(r2s):+.3f}  MAE={np.mean(maes):.4f}")

    # 2. OOD tests: train on pool, predict each new pilot
    Xpool, ypool, encp, _ = featurize(pool)
    m = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=20260524)
    m.fit(Xpool, ypool)
    print(f"\n=== OOD generalization (train on pool n={len(pool)}, test on each pilot) ===")
    print(f"  using AGENT-FAMILY features (was raw agent_id in F18 v1 → F24 broke)")
    for label, rows in [("v10", v10), ("v10.1", v10_1), ("v11", v11), ("v6.1", v6_1)]:
        if not rows: continue
        Xt, yt, _, _ = featurize(rows, fit_encoder=encp)
        yp = m.predict(Xt)
        r2 = r2_score(yt, yp); mae = mean_absolute_error(yt, yp)
        baseline_mae = np.mean(np.abs(yt - np.mean(ypool)))
        reduction = (baseline_mae - mae) / baseline_mae * 100
        print(f"  pool → {label:<6}: n={len(yt):>4}  R² = {r2:+.3f}  MAE = {mae:.4f}  ({'+' if reduction>0 else ''}{reduction:.1f}% reduction vs baseline)")

    # 3. Feature importance on the combined fit
    m_full = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=20260524)
    m_full.fit(X, y)
    print(f"\n=== top features (combined fit n={len(y)}) ===")
    for name, imp in sorted(zip(feat_names, m_full.feature_importances_), key=lambda x: -x[1])[:12]:
        print(f"    {name:<30} {imp:.4f}")

    # Save v2 verdict
    verdict = {
        "n_pool": len(pool), "n_v10": len(v10), "n_v10_1": len(v10_1), "n_v11": len(v11), "n_v6_1": len(v6_1),
        "n_combined": len(all_rows),
        "combined_cv_r2_mean": float(np.mean(r2s)),
        "combined_cv_mae_mean": float(np.mean(maes)),
        "agent_family_distribution": dict(Counter(r["agent_family"] for r in all_rows)),
    }
    Path("analytics/public/forecast_pool/meta_classifier_v2_verdict.json").write_text(json.dumps(verdict, indent=2))
    print(f"\n  verdict → analytics/public/forecast_pool/meta_classifier_v2_verdict.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
