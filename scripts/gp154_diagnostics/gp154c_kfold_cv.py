#!/usr/bin/env python3
"""GP-154c — stratified k-fold cross-validation (Bug #42, 2026-04-25 night).

Per user 2026-04-25 night: "we chose that holdout arbitrarily, shouldn't
we do the holdout better?" Correct — n=12 single holdout has 3× MRE
variance across seeds (gp154b results 0.39-1.32). The rigorous fix is
stratified k-fold CV: every attributed row is held out exactly once,
across k folds. Final bound = mean(fold MREs) ± std(fold MREs).

Stratification: joint on fit_convention (load-bearing per gp158 audit) +
modality_coarse (language vs vision vs other). Ensures each fold has
representative distribution.

Reports per candidate:
    mean_CV_MRE ± std    n_folds_passing(<0.25)
plus aggregate decomposition:
    OOD wall (best, original split)             ← from offline_verify
    IID single-fold range across 5 seeds        ← from gp154b
    k-fold CV mean ± std across 5 folds         ← THIS SCRIPT
    Irreducible K≤7 heterogeneity bound         ← (best fold) lower envelope

Usage:
    python scripts/gp154c_kfold_cv.py [--k 5] [--seed 42]
"""
from __future__ import annotations

import argparse
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

PROJECT_DIR = _REPO / "projects" / "gp154_scaling_law_exponents"
sys.path.insert(0, str(PROJECT_DIR))

from src.ztare.fit.fit_primitive_features import (  # noqa: E402
    fit_features,
    _safe_compile_form,
)


def load_attributed_alphas() -> dict[int, float]:
    """Pool all (id, alpha) from evidence.txt + evidence_holdout.txt."""
    out: dict[int, float] = {}

    # Visible
    text_v = (PROJECT_DIR / "evidence.txt").read_text(encoding="utf-8")
    section = "VISIBLE"
    for raw in text_v.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if "===" in line:
                upper = line.upper()
                if "VISIBLE_SET" in upper or "VISIBLE-SET" in upper:
                    section = "VISIBLE"
                else:
                    section = "OTHER"
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

    # Holdout (HOLDOUT_SET only — exclude FARTHER, HONEST_NULL since unscored)
    section = None
    for raw in (PROJECT_DIR / "evidence_holdout.txt").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if "===" in line:
                upper = line.upper()
                if "HOLDOUT_SET" in upper and "FARTHER" not in upper:
                    section = "H"
                else:
                    section = None
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


import features as _feats  # noqa: E402

# Bug #43 (2026-04-25 night): allow swapping in features_augmented for the
# feature-completeness-diagnostic test — does adding C/D/E + joint-form
# parameters to 32 of 110 rows move the irreducible bound below 0.5?
import os as _os
if _os.environ.get("GP154C_USE_AUGMENTED", "").lower() in ("1", "true", "yes"):
    try:
        import features_augmented as _feats_aug  # type: ignore[import-not-found]
        FEATURES = _feats_aug.FEATURES
        print("[GP154C_USE_AUGMENTED=1] using features_augmented.py "
              "(adds joint_E/A/B/alpha/beta, dataset_log10_tokens, "
              "compute_log10_flops, is_compute_optimal_design, "
              "params_per_token_ratio, is_chinchilla_family, is_kaplan_family "
              "to the 32 attributable rows; None elsewhere)")
    except Exception as _e:
        print(f"[GP154C_USE_AUGMENTED=1] failed to load features_augmented: {_e} — falling back to features.py")
        FEATURES = _feats.FEATURES
else:
    FEATURES = _feats.FEATURES
ALPHAS = load_attributed_alphas()
# Add visible_rows() data if present
try:
    for rid, y, _ in _feats.visible_rows():
        if rid not in ALPHAS and y is not None:
            ALPHAS[int(rid)] = float(y)
except Exception:
    pass


def stratify_key(rid: int) -> tuple[str, str]:
    """Stratification key: (fit_convention_family, modality_coarse).
    fit_convention_family: chinchilla / kaplan / other.
    modality_coarse: language / vision / other."""
    fd = FEATURES.get(rid, {})
    fc = fd.get("fit_convention", "")
    if fc in (
        "chinchilla_joint", "chinchilla_isoflop", "chinchilla_parametric",
        "compute_optimal", "joint_bivariate",
    ):
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
    """Return k folds (lists of held-out IDs). Each row in exactly one fold.
    Stratified: each fold has roughly proportional count from each stratum."""
    rng = random.Random(seed)
    strata: dict[tuple, list[int]] = defaultdict(list)
    for rid in rids:
        strata[stratify_key(rid)].append(rid)
    for ids in strata.values():
        rng.shuffle(ids)
    folds: list[list[int]] = [[] for _ in range(k)]
    # Round-robin distribute each stratum across folds
    for ids in strata.values():
        for i, rid in enumerate(ids):
            folds[i % k].append(rid)
    return folds


def evaluate_form(form: str, params: list[str], train_data, holdout_truth) -> tuple[float, float, bool]:
    """Returns (visible_mean_residual, holdout_MRE, success_flag)."""
    result = fit_features(
        form, params, train_data,
        n_starts=5, seed=2026, k_law_max=15,
        disable_sparse_indicator_reject=True,
    )
    if not result.success:
        return float("inf"), float("inf"), False
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
    return result.mean_abs_residual, mre, True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--k", type=int, default=5, help="number of folds")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print(f"GP-154c stratified {args.k}-fold cross-validation")
    print(f"Pool: {len(ALPHAS)} attributed rows (seed={args.seed})")
    print()

    rids = sorted(ALPHAS.keys())
    folds = stratified_kfold(rids, args.k, args.seed)
    print(f"Fold sizes: {[len(f) for f in folds]}")
    print(f"Stratum coverage per fold:")
    for i, fold in enumerate(folds):
        c = Counter(stratify_key(r) for r in fold)
        print(f"  fold {i}: {dict(c)}")
    print()

    candidates = [
        ("constant_K=1", "params['c']", ["c"]),
        ("per_scaling_var_K=4",
         "params['c_N'] if features['scaling_var']=='N' else "
         "(params['c_D'] if features['scaling_var']=='D' else "
         "(params['c_C'] if features['scaling_var']=='C' else params['c_other']))",
         ["c_N", "c_D", "c_C", "c_other"]),
        ("log_N_linear_K=2",
         "params['a'] + params['b'] * features['log10_N_params']",
         ["a", "b"]),
        ("scaling_var_x_log_N_K=7",
         "(params['a_N'] + params['b_N'] * features['log10_N_params']) "
         "  if features['scaling_var']=='N' else "
         "((params['a_D'] + params['b_D'] * features['log10_N_params']) "
         "   if features['scaling_var']=='D' else "
         "((params['a_C'] + params['b_C'] * features['log10_N_params']) "
         "    if features['scaling_var']=='C' else params['a_other']))",
         ["a_N", "b_N", "a_D", "b_D", "a_C", "b_C", "a_other"]),
        ("regime_anchored_with_N_K=3",
         "(1.0 if features['regime_hint'] == 'variance_limited' else "
         "  ((2.0 / features['intrinsic_dim_d']) "
         "    if (features['regime_hint'] == 'resolution_limited' "
         "        and features['intrinsic_dim_d'] is not None) "
         "    else "
         "    (params['a'] + params['b'] * features['log10_N_params'] "
         "     + params['c'] * "
         "       (1.0 if features['fit_convention'] in "
         "         ('chinchilla_joint','chinchilla_isoflop','chinchilla_parametric',"
         "          'compute_optimal','joint_bivariate') else 0.0))))",
         ["a", "b", "c"]),
        # Bug #43 (2026-04-25 night): augmented-feature candidates. These
        # gracefully degrade when augmented fields are None (rows without
        # canonical-source attribution). When features_augmented.py is loaded,
        # the chinchilla/kaplan rows get real C, D, E values.
        ("AUG_chinchilla_joint_form_K=3",
         # α ≈ joint_alpha (the published exponent from joint fit) when
         # augmentation provides it; else fall back to log_N_params linear.
         "params['scale'] * features.get('joint_alpha', 0.0) "
         "  if features.get('joint_alpha') is not None "
         "  else (params['a'] + params['b'] * features['log10_N_params'])",
         ["scale", "a", "b"]),
        ("AUG_with_dataset_size_K=4",
         # α = a + b/N^p + c/D^q   (Chinchilla bilinear form, separable)
         # Falls back to log_N linear when D unavailable.
         "(params['a'] + params['c'] / "
         "  (10.0 ** features.get('dataset_log10_tokens', 9.0))) "
         "  if features.get('dataset_log10_tokens') is not None "
         "  else (params['a'] + params['b'] * features['log10_N_params'])",
         ["a", "b", "c"]),
        ("AUG_compute_per_param_K=4",
         # α = a + b × (compute_log10_flops - log10_N_params)
         # Tests whether C/N ratio (compute richness) explains residual variance
         "(params['a'] + params['b'] * "
         "  (features.get('compute_log10_flops', 20.0) - features['log10_N_params'])) "
         "  if features.get('compute_log10_flops') is not None "
         "  else (params['c'] + params['d'] * features['log10_N_params'])",
         ["a", "b", "c", "d"]),
        ("AUG_compute_optimal_anchor_K=3",
         # α ≈ 0.5 in compute-optimal regime (Chinchilla isoFLOP); else linear
         "(0.5 if features.get('is_compute_optimal_design') is True "
         "  else (1.0 if features['regime_hint'] == 'variance_limited' "
         "        else (params['a'] + params['b'] * features['log10_N_params'] "
         "              + params['c'])))",
         ["a", "b", "c"]),
    ]

    print(f"─── {args.k}-fold CV results ───")
    print(f"{'Form':<32} {'mean MRE':<12} {'std MRE':<12} {'min MRE':<12} {'max MRE':<12} {'pass folds':<12}")

    overall_min_mre = float("inf")
    overall_min_form = ""
    for name, form, params in candidates:
        fold_mres = []
        fold_visibles = []
        for fold_i, holdout_fold in enumerate(folds):
            holdout_set = set(holdout_fold)
            train_data = [
                (FEATURES[rid], ALPHAS[rid])
                for rid in rids if rid not in holdout_set and rid in FEATURES
            ]
            holdout_truth = {rid: ALPHAS[rid] for rid in holdout_fold if rid in FEATURES}
            vis_res, mre, success = evaluate_form(form, params, train_data, holdout_truth)
            if not success:
                fold_mres.append(float("inf"))
                continue
            fold_mres.append(mre)
            fold_visibles.append(vis_res)
        finite_mres = [m for m in fold_mres if math.isfinite(m)]
        if not finite_mres:
            print(f"  {name:<32} all folds failed")
            continue
        mean_mre = sum(finite_mres) / len(finite_mres)
        var = sum((m - mean_mre)**2 for m in finite_mres) / len(finite_mres)
        std_mre = math.sqrt(var)
        min_mre = min(finite_mres)
        max_mre = max(finite_mres)
        n_pass = sum(1 for m in finite_mres if m < 0.25)
        print(f"  {name:<32} {mean_mre:<12.4f} {std_mre:<12.4f} {min_mre:<12.4f} {max_mre:<12.4f} {n_pass}/{len(finite_mres)}")
        if mean_mre < overall_min_mre:
            overall_min_mre = mean_mre
            overall_min_form = name

    print()
    print("=" * 80)
    print(f"BEST FORM by mean CV MRE: {overall_min_form} → {overall_min_mre:.4f}")
    print()
    print("Decomposition of the gp154 wall:")
    print(f"  OOD (current arbitrary holdout):         best HOLDOUT MRE = 3.51")
    print(f"  IID single-fold (gp154b, 5 seeds):       range 0.39-1.32, mean ~0.97")
    print(f"  k={args.k}-fold stratified CV (this run): best mean MRE = {overall_min_mre:.4f}")
    print()
    if overall_min_mre < 0.25:
        print(">>> k-fold CV PASSES <0.25 threshold.")
        print("    Feature sufficiency confirmed at K≤7. Original gp154 wall was")
        print("    arbitrary-holdout artifact + distribution shift, NOT structural.")
    elif overall_min_mre < 0.5:
        print(">>> k-fold CV in 0.25-0.5 range — close to threshold.")
        print("    Irreducible K≤7 heterogeneity is bounded above by ~0.5.")
        print("    With C/D/E features added (currently partial coverage),")
        print("    threshold is plausibly reachable. Recommend retest after full")
        print("    feature augmentation.")
    elif overall_min_mre < 1.0:
        print(">>> k-fold CV in 0.5-1.0 range — moderate irreducible heterogeneity.")
        print("    K≤7 cannot fully fit even with proper CV; either need K>7")
        print("    or additional features beyond {N, modality, arch, scaling_var,")
        print("    fit_convention, regime_hint, intrinsic_dim, study}.")
    else:
        print(">>> k-fold CV > 1.0 — irreducible heterogeneity is genuinely high.")
        print("    The gp154 dataset has structural noise that no K≤7 closed-form")
        print("    can absorb. Bounded null is robust under proper CV methodology.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
