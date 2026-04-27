#!/usr/bin/env python3
"""GP-154h — offline test of VOID hypothesis families (2026-04-25 night).

Per user request "can u do the tests here w/o running again?": after the
void analysis of last 10 gp154 iters showed the mutator NEVER tried these
form families:

  1. Multiplicative N×D (Chinchilla bilinear): alpha = a * N^p * D^q
  2. Convention-conditioned exponent: alpha = a * N^(b + c*is_chin)
  3. Log-link: log(alpha) = a + b*log_N + c*is_chin
  4. Sigmoid crossover in N: alpha = a + b*sigmoid(log_N, c, w)
  5. Negative-coefficient (semantic-distractor aware)
  6. Loss-type-aware: alpha = base * loss_type_factor

We fit these via the exact same fit_features infrastructure used by the
mutator, run 5-fold stratified CV, and report mean MRE.

If any family drops below the v5 best baseline (1.28) by a meaningful
margin, the bounded-null narrative changes from "K<=7 mathematical wall"
to "mutator-prior basin lock — apparatus searched a too-narrow form
neighborhood." Either is a valid Nature MI finding but they are very
different stories.

Baselines being beaten:
  - Best charter K<=7:           1.58 ± 0.55
  - Best with v5 micro features: 1.28 (optimizer-only)
  - Threshold for victory:       <0.25
  - Threshold for "narrative shift": <1.00 (means feature/form gap was real)
"""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
import random

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

PROJECT_DIR = _REPO / "projects" / "gp154_scaling_law_exponents"
sys.path.insert(0, str(PROJECT_DIR))

from src.ztare.fit.fit_primitive_features import (  # noqa: E402
    fit_features,
    _safe_compile_form,
)
import features as _feats  # noqa: E402

FEATURES = _feats.FEATURES


def load_attributed_alphas() -> dict[int, float]:
    out: dict[int, float] = {}
    text_v = (PROJECT_DIR / "evidence.txt").read_text(encoding="utf-8")
    section = "VISIBLE"
    for raw in text_v.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if "===" in line:
                upper = line.upper()
                section = "VISIBLE" if "VISIBLE_SET" in upper or "VISIBLE-SET" in upper else "OTHER"
            continue
        if section != "VISIBLE":
            continue
        parts = line.split("\t") if "\t" in line else line.split()
        if len(parts) < 2:
            continue
        try:
            out[int(parts[0])] = float(parts[1])
        except (ValueError, IndexError):
            continue
    section = None
    for raw in (PROJECT_DIR / "evidence_holdout.txt").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if "===" in line:
                upper = line.upper()
                section = "H" if "HOLDOUT_SET" in upper and "FARTHER" not in upper else None
            continue
        if section != "H":
            continue
        parts = line.split("\t") if "\t" in line else line.split()
        if len(parts) < 2:
            continue
        try:
            out[int(parts[0])] = float(parts[1])
        except (ValueError, IndexError):
            continue
    return out


ALPHAS = load_attributed_alphas()
try:
    for rid, y, _ in _feats.visible_rows():
        if rid not in ALPHAS and y is not None:
            ALPHAS[int(rid)] = float(y)
except Exception:
    pass


def stratify_key(rid: int) -> tuple[str, str]:
    fd = FEATURES.get(rid, {})
    fc = fd.get("fit_convention", "")
    if fc in ("chinchilla_joint", "chinchilla_isoflop", "chinchilla_parametric",
              "compute_optimal", "joint_bivariate"):
        fc_fam = "chin"
    elif fc in ("kaplan_separable", "loss_curve_power", "loss_curve_power_const"):
        fc_fam = "kap"
    else:
        fc_fam = "oth"
    mod = (fd.get("modality") or "")
    if "language" in mod or mod in ("text",):
        mod_coarse = "lang"
    elif "vision" in mod or "image" in mod:
        mod_coarse = "vis"
    else:
        mod_coarse = "oth"
    return (fc_fam, mod_coarse)


def stratified_kfold(rids: list[int], k: int, seed: int) -> list[list[int]]:
    rng = random.Random(seed)
    strata: dict[tuple, list[int]] = defaultdict(list)
    for rid in rids:
        strata[stratify_key(rid)].append(rid)
    for ids in strata.values():
        rng.shuffle(ids)
    folds: list[list[int]] = [[] for _ in range(k)]
    for ids in strata.values():
        for i, rid in enumerate(ids):
            folds[i % k].append(rid)
    return folds


def evaluate_form(form: str, params: list[str], train_data, holdout_truth) -> tuple[float, bool]:
    result = fit_features(
        form, params, train_data,
        n_starts=8, seed=2026, k_law_max=15,
        disable_sparse_indicator_reject=True,
    )
    if not result.success:
        return float("inf"), False
    fn = _safe_compile_form(form)
    errs = []
    for rid, y_true in holdout_truth.items():
        try:
            y = float(fn(FEATURES[rid], result.fitted_params))
        except Exception:
            y = float("nan")
        if math.isnan(y) or math.isinf(y):
            errs.append(1.0)
            continue
        d = abs(y_true) if y_true != 0 else 1e-12
        errs.append(abs(y - y_true) / d)
    mre = sum(errs) / len(errs) if errs else float("inf")
    return mre, True


# ── VOID-FAMILY CANDIDATES ────────────────────────────────────────────────
# Every form must:
#   (a) be evaluable via _safe_compile_form (uses math, sigmoid, where, erf)
#   (b) compose only via primitives the mutator could have written
#   (c) gracefully degrade when augmented fields are None

# Helper expressions we'll reuse:
#   N_pow      = (10.0 ** features['log10_N_params'])
#   logN       = features['log10_N_params']
#   isCh       = (1.0 if features.get('is_chinchilla_family') else 0.0)
#   isKa       = (1.0 if features.get('is_kaplan_family') else 0.0)
#   D_log      = features.get('dataset_log10_tokens')
#   D_pow_safe = (10.0 ** D_log) if D_log is not None else 1e10
# (We inline these below to keep the strings self-contained.)

CANDIDATES = [
    # ── BASELINES (sanity check fit_features works) ──
    ("BASE_constant_K1", "params['c']", ["c"]),
    ("BASE_log_N_linear_K2",
     "params['a'] + params['b'] * features['log10_N_params']",
     ["a", "b"]),
    ("BASE_per_convention_K3",
     "params['a'] + params['b'] * features['log10_N_params'] "
     "+ params['c'] * (1.0 if features.get('is_chinchilla_family') else 0.0)",
     ["a", "b", "c"]),

    # ── VOID FAMILY 1: MULTIPLICATIVE N×D (Chinchilla bilinear) ──
    # alpha = a * N^p * D^q, gracefully falls back to a + b*log_N when D missing.
    ("VOID1_mult_NxD_K4",
     "(params['a'] * (10.0**features['log10_N_params'])**params['p'] "
     "       * (10.0**features['dataset_log10_tokens'])**params['q']) "
     "  if features.get('dataset_log10_tokens') is not None "
     "  else (params['a'] + params['p'] * features['log10_N_params'])",
     ["a", "p", "q"]),

    # Linear-in-log version (more identifiable for n_starts):
    # alpha = a + p*log_N + q*log_D, falls back to a + p*log_N
    ("VOID1b_loglin_logN_logD_K3",
     "(params['a'] + params['p'] * features['log10_N_params'] "
     "  + params['q'] * features['dataset_log10_tokens']) "
     "  if features.get('dataset_log10_tokens') is not None "
     "  else (params['a'] + params['p'] * features['log10_N_params'])",
     ["a", "p", "q"]),

    # ── VOID FAMILY 2: CONVENTION-CONDITIONED EXPONENT ──
    # alpha = a * (N/N0)^(b + c*is_chinchilla)
    # In log space: log(alpha) = log(a) + (b + c*is_chin) * (log_N - log_N0)
    # Pick log_N0 = 8 (mid scale), reparam to: alpha = a + (b + c*is_chin) * (log_N - 8)
    # but keep it as power-law style:
    ("VOID2_conv_cond_exponent_K4",
     "params['a'] * (10.0 ** features['log10_N_params']) ** "
     "(params['b'] + params['c'] * (1.0 if features.get('is_chinchilla_family') else 0.0))",
     ["a", "b", "c"]),

    # Log-space variant (more stable):
    ("VOID2b_conv_cond_loglin_K4",
     "params['a'] + (params['b'] + params['c'] * "
     "  (1.0 if features.get('is_chinchilla_family') else 0.0)) "
     "  * features['log10_N_params']",
     ["a", "b", "c"]),

    # ── VOID FAMILY 3: LOG-LINK ──
    # log(alpha) = a + b*log_N + c*is_chinchilla  =>  alpha = exp(...)
    ("VOID3_log_link_K3",
     "math.exp(params['a'] + params['b'] * features['log10_N_params'] "
     "  + params['c'] * (1.0 if features.get('is_chinchilla_family') else 0.0))",
     ["a", "b", "c"]),

    # ── VOID FAMILY 4: SIGMOID CROSSOVER IN N ──
    # alpha = a + b * sigmoid(log_N, c, w)
    # sigmoid(x, center, width) primitive is available per fit_primitive_features.py
    ("VOID4_sigmoid_logN_K4",
     "params['a'] + params['b'] * sigmoid(features['log10_N_params'], "
     "params['c'], params['w'])",
     ["a", "b", "c", "w"]),

    # ── VOID FAMILY 5: NEGATIVE-COEFFICIENT (semantic-distractor aware) ──
    # alpha = base + neg_offset * (distractor=='semantic')
    # Cerebras has alpha = -0.16 — semantic distractor row. The mutator never
    # wrote a form that could go negative. This explicitly does.
    ("VOID5_neg_distractor_K4",
     "params['a'] + params['b'] * features['log10_N_params'] "
     "+ params['neg'] * (1.0 if features.get('distractor_class')=='semantic' else 0.0) "
     "+ params['ch'] * (1.0 if features.get('is_chinchilla_family') else 0.0)",
     ["a", "b", "neg", "ch"]),

    # ── VOID FAMILY 6: LOSS-TYPE-AWARE ──
    # alpha = base * loss_factor; accuracy task gets different scale than CE.
    # 14 rows have loss_type='accuracy', 3 have 'rmse', 91 have 'cross_entropy'
    ("VOID6_loss_type_aware_K4",
     "(params['a_acc'] if features.get('loss_type')=='accuracy' "
     "  else (params['a_rmse'] if features.get('loss_type')=='rmse' "
     "        else params['a_ce'])) "
     "+ params['b'] * features['log10_N_params']",
     ["a_acc", "a_rmse", "a_ce", "b"]),

    # ── COMPOSED VOID (most ambitious): regime-anchor + log-link + conv-cond ──
    # alpha = (1 if variance_limited)
    #       else (2/d if resolution_limited)
    #       else exp(a + b*log_N + c*is_chin + d*is_kap)
    # K=4 free, gracefully handles all 3 regimes
    ("VOID7_composed_K4",
     "(1.0 if features.get('regime_hint')=='variance_limited' "
     "  else ((2.0/features['intrinsic_dim_d']) "
     "        if (features.get('regime_hint')=='resolution_limited' "
     "            and features.get('intrinsic_dim_d') is not None) "
     "        else math.exp(params['a'] + params['b']*features['log10_N_params'] "
     "             + params['c'] * (1.0 if features.get('is_chinchilla_family') else 0.0) "
     "             + params['d'] * (1.0 if features.get('is_kaplan_family') else 0.0))))",
     ["a", "b", "c", "d"]),

    # ── COMPOSED + MULT N×D (most ambitious K<=7) ──
    # When D available: a*N^p*D^q within non-anchor regime
    # When D missing:   exp(a + b*log_N + c*is_chin)
    ("VOID8_composed_mult_NxD_K5",
     "(1.0 if features.get('regime_hint')=='variance_limited' "
     "  else ((2.0/features['intrinsic_dim_d']) "
     "        if (features.get('regime_hint')=='resolution_limited' "
     "            and features.get('intrinsic_dim_d') is not None) "
     "        else ((params['a'] * (10.0**features['log10_N_params'])**params['p'] "
     "                * (10.0**features['dataset_log10_tokens'])**params['q']) "
     "              if features.get('dataset_log10_tokens') is not None "
     "              else math.exp(params['a2'] + params['b']*features['log10_N_params']))))",
     ["a", "p", "q", "a2", "b"]),
]


def main(k: int = 5, seed: int = 42) -> int:
    print("=" * 80)
    print("GP-154h — VOID-FAMILY OFFLINE TEST (k=5 stratified CV)")
    print(f"Pool: {len(ALPHAS)} attributed rows, seed={seed}")
    print("=" * 80)

    rids = sorted(ALPHAS.keys())
    folds = stratified_kfold(rids, k, seed)
    print(f"Fold sizes: {[len(f) for f in folds]}")
    print()

    print(f"{'Form':<38} {'mean':<10} {'std':<10} {'min':<10} {'max':<10} {'pass':<8}")
    print("-" * 86)

    overall_min_mre = float("inf")
    overall_min_form = ""
    results = []

    for name, form, params in CANDIDATES:
        fold_mres = []
        for fold_i, holdout_fold in enumerate(folds):
            holdout_set = set(holdout_fold)
            train_data = [
                (FEATURES[rid], ALPHAS[rid])
                for rid in rids if rid not in holdout_set and rid in FEATURES
            ]
            holdout_truth = {rid: ALPHAS[rid] for rid in holdout_fold if rid in FEATURES}
            mre, success = evaluate_form(form, params, train_data, holdout_truth)
            fold_mres.append(mre if success else float("inf"))
        finite = [m for m in fold_mres if math.isfinite(m)]
        if not finite:
            print(f"  {name:<38} ALL FOLDS FAILED")
            continue
        mean_mre = sum(finite) / len(finite)
        var = sum((m - mean_mre) ** 2 for m in finite) / len(finite)
        std_mre = math.sqrt(var)
        min_mre = min(finite)
        max_mre = max(finite)
        n_pass = sum(1 for m in finite if m < 0.25)
        print(f"  {name:<38} {mean_mre:<10.4f} {std_mre:<10.4f} {min_mre:<10.4f} {max_mre:<10.4f} {n_pass}/{len(finite)}")
        results.append((name, mean_mre, std_mre, min_mre, max_mre))
        if mean_mre < overall_min_mre:
            overall_min_mre = mean_mre
            overall_min_form = name

    print()
    print("=" * 80)
    print(f"BEST: {overall_min_form} → mean CV MRE = {overall_min_mre:.4f}")
    print()
    print("Comparison vs prior bounds:")
    print(f"  Best charter K<=7 (5-fold CV):   1.58 ± 0.55")
    print(f"  Best v5 micro (optimizer):       1.28")
    print(f"  Best void-family (this run):     {overall_min_mre:.4f}")
    print()
    if overall_min_mre < 0.25:
        print(">>> THRESHOLD CROSSED. Void-family family solves the problem.")
        print("    The bounded-null narrative is OVERTURNED — apparatus had a")
        print("    mutator-prior basin lock, not a math wall. This is a")
        print("    HOSTILE finding for the v3 charter, FRIENDLY for the v4 reframe.")
    elif overall_min_mre < 1.00:
        print(">>> NARRATIVE SHIFT. Void family reaches mean MRE < 1.0,")
        print("    meaningfully below 1.28/1.58 wall. The mutator was searching")
        print("    a too-narrow neighborhood; the form gap was real.")
        print("    Story changes from 'K<=7 wall' to 'apparatus searched too narrow'.")
    elif overall_min_mre < 1.40:
        print(">>> MARGINAL. Void families ~ same as v5 baseline, no clear improvement.")
        print("    Bounded null robust at K<=7; form gap small, narrative survives.")
    else:
        print(">>> NULL CONFIRMED. Void families don't beat the wall.")
        print("    Bounded null is genuinely structural — both feature gap and")
        print("    form-class gap are exhausted at K<=7.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
