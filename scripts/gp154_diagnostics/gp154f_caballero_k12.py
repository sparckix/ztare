#!/usr/bin/env python3
"""GP-154f — Caballero K≤12 broken-power-law benchmark (Path A.2).

Per Nature MI panel attack 2.2: "K≤7 cap is incompatible with the
published forms — Chinchilla has 5 globals + per-row N+D contributions,
testing undersized form vs oversized-form data and calling 'structural
impossibility' is a category error."

This script extends the 5-fold stratified CV at K=8, 10, 12 with
literature-established broken-power-law forms (Caballero et al. 2022
"Broken Neural Scaling Laws", Hoffmann 2022 full Chinchilla form,
Henighan 2020 generalized power-law-plus-constant). If the wall persists
at K=12, Claim 1 of the Nature MI paper survives the strawman attack.
If the wall collapses, Claim 1 was a complexity-cap artifact and the
bounded-null framing is wrong — better to know now.

Usage:
    python scripts/gp154f_caballero_k12.py [--k 5] [--seed 42]
"""
from __future__ import annotations

import argparse
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
PROJECT_DIR = _REPO / "projects" / "gp154_scaling_law_exponents"
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(PROJECT_DIR))

from src.ztare.fit.fit_primitive_features import (  # noqa: E402
    fit_features,
    _safe_compile_form,
    load_visible_from_substrate,
)
import features as _feats  # noqa: E402

FEATURES = _feats.FEATURES


def load_alphas() -> dict[int, float]:
    out: dict[int, float] = {}
    triples, _ = load_visible_from_substrate(PROJECT_DIR)
    if triples:
        for fd, y in triples:
            if y is None:
                continue
            for rid, v in FEATURES.items():
                if (v.get("study") == fd.get("study")
                    and v.get("log10_N_params") == fd.get("log10_N_params")
                    and v.get("scaling_var") == fd.get("scaling_var")
                    and v.get("modality") == fd.get("modality")
                    and v.get("architecture_class") == fd.get("architecture_class")):
                    try:
                        out[int(rid)] = float(y)
                    except (TypeError, ValueError):
                        pass
                    break
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


def stratify_kfold(rids: list[int], k: int, seed: int) -> list[list[int]]:
    rng = random.Random(seed)
    strata: dict[tuple, list[int]] = defaultdict(list)
    for rid in rids:
        fd = FEATURES.get(rid, {})
        sv = fd.get("scaling_var", "UNK")
        mod_coarse = "lang" if "language" in (fd.get("modality") or "") else (
            "vis" if "vision" in (fd.get("modality") or "") or "image" in (fd.get("modality") or "") else "oth")
        strata[(sv, mod_coarse)].append(rid)
    for ids in strata.values():
        rng.shuffle(ids)
    folds: list[list[int]] = [[] for _ in range(k)]
    for ids in strata.values():
        for i, rid in enumerate(ids):
            folds[i % k].append(rid)
    return folds


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    alphas = load_alphas()
    print(f"Pool: {len(alphas)} attributed rows.")
    rids = sorted(alphas.keys())
    folds = stratify_kfold(rids, args.k, args.seed)
    print(f"Fold sizes: {[len(f) for f in folds]}")
    print()

    # ── Candidate forms by K-budget ───────────────────────────────
    # Each form uses fallbacks (10**log10_N for N when needed; intrinsic_dim_d
    # / intrinsic_dim_estimate for d when needed).
    candidates = [
        # K=8: per-scaling_var slope and intercept (from gp154c best),
        #      plus separate convention multiplier.
        ("K8_per_scaling_var_x_convention",
         "((params['a_N'] + params['b_N'] * features['log10_N_params']) "
         "  if features['scaling_var']=='N' else "
         "((params['a_D'] + params['b_D'] * features['log10_N_params']) "
         "   if features['scaling_var']=='D' else "
         "((params['a_C'] + params['b_C'] * features['log10_N_params']) "
         "    if features['scaling_var']=='C' else params['a_other']))) "
         "* (1.0 + params['c_chin'] * "
         "    (1.0 if features['fit_convention'] in "
         "      ('chinchilla_joint','chinchilla_isoflop','chinchilla_parametric',"
         "       'compute_optimal','joint_bivariate') else 0.0))",
         ["a_N", "b_N", "a_D", "b_D", "a_C", "b_C", "a_other", "c_chin"]),

        # K=10: Caballero broken-power-law adapted: alpha = a + b*N^c + d*N^e
        # (two-break power law, model size only)
        # plus regime anchor and convention multiplier.
        ("K10_caballero_broken_power_x_regime",
         "(1.0 if features['regime_hint']=='variance_limited' else "
         " (params['a'] + params['b'] * (10.0 ** features['log10_N_params']) ** params['c'] "
         "  + params['d'] * (10.0 ** features['log10_N_params']) ** params['e']) "
         "* (1.0 + params['f_chin'] * "
         "    (1.0 if features['fit_convention'] in "
         "      ('chinchilla_joint','chinchilla_isoflop','chinchilla_parametric',"
         "       'compute_optimal','joint_bivariate') else 0.0)) "
         "+ params['g'] * (features['scaling_var']=='C') "
         "+ params['h'] * (features['scaling_var']=='C_OPT'))",
         ["a", "b", "c", "d", "e", "f_chin", "g", "h"]),

        # K=10: Hoffmann full joint-form-like: alpha = E + A*N^p + B*X^q
        # (where X = features['log10_N_params'] reused as proxy when D unavailable)
        ("K10_hoffmann_full_form",
         "(params['E'] + params['A'] / "
         "  ((10.0 ** features['log10_N_params']) ** params['p']) "
         "  + params['B'] / "
         "    ((10.0 ** features['log10_N_params']) ** params['q'])) "
         "* (1.0 + params['c1'] * (features['scaling_var']=='D') "
         "       + params['c2'] * (features['scaling_var']=='C') "
         "       + params['c3'] * (features['fit_convention']=='kaplan_separable'))",
         ["E", "A", "B", "p", "q", "c1", "c2", "c3"]),

        # K=12: per-scaling_var × (intercept, slope, log_N_quadratic) — most flexible
        ("K12_per_scaling_var_quadratic_x_convention",
         "((params['a_N'] + params['b_N'] * features['log10_N_params'] "
         "  + params['c_N'] * features['log10_N_params'] * features['log10_N_params']) "
         "  if features['scaling_var']=='N' else "
         "((params['a_D'] + params['b_D'] * features['log10_N_params'] "
         "   + params['c_D'] * features['log10_N_params'] * features['log10_N_params']) "
         "   if features['scaling_var']=='D' else "
         "((params['a_C'] + params['b_C'] * features['log10_N_params'] "
         "    + params['c_C'] * features['log10_N_params'] * features['log10_N_params']) "
         "    if features['scaling_var']=='C' else "
         "(params['a_oth'] + params['b_oth'] * features['log10_N_params'] "
         " + params['c_oth'] * features['log10_N_params'] * features['log10_N_params']))))",
         ["a_N", "b_N", "c_N", "a_D", "b_D", "c_D", "a_C", "b_C", "c_C", "a_oth", "b_oth", "c_oth"]),

        # K=12: regime + Caballero broken-power-law per scaling_var
        ("K12_caballero_per_scaling_var_regime",
         "(1.0 if features['regime_hint']=='variance_limited' else "
         "((2.0 / features['intrinsic_dim_d']) "
         "  if (features['regime_hint']=='resolution_limited' "
         "      and features['intrinsic_dim_d'] is not None) else "
         "((params['a_N'] + params['b_N'] * features['log10_N_params'] "
         "  + params['c_N'] * (10.0 ** features['log10_N_params']) ** params['d_N']) "
         "  if features['scaling_var']=='N' else "
         "((params['a_D'] + params['b_D'] * features['log10_N_params']) "
         "  if features['scaling_var']=='D' else "
         "((params['a_C'] + params['b_C'] * features['log10_N_params']) "
         "  if features['scaling_var']=='C' else "
         "(params['a_oth'] + params['b_oth'] * features['log10_N_params']))))))",
         ["a_N", "b_N", "c_N", "d_N", "a_D", "b_D", "a_C", "b_C", "a_oth", "b_oth"]),
    ]

    print(f"─── 5-fold stratified CV at K=8 to K=12 ───")
    print(f"{'Form':<48} {'K':<4} {'mean MRE':<12} {'std MRE':<12} {'min':<10} {'max':<10}")

    overall_min_mre = float("inf")
    overall_min_form = ""
    overall_min_K = 0
    for name, form, params in candidates:
        K = len(params)
        fold_mres = []
        for holdout_fold in folds:
            holdout_set = set(holdout_fold)
            train_data = [
                (FEATURES[rid], alphas[rid])
                for rid in rids if rid not in holdout_set and rid in FEATURES
            ]
            holdout_truth = {rid: alphas[rid] for rid in holdout_fold if rid in FEATURES}
            r = fit_features(
                form, params, train_data,
                n_starts=5, seed=2026, k_law_max=15,
                disable_sparse_indicator_reject=True,
            )
            if not r.success:
                fold_mres.append(float("inf"))
                continue
            fn = _safe_compile_form(form)
            errs = []
            for rid, y_true in holdout_truth.items():
                try:
                    y = float(fn(FEATURES[rid], r.fitted_params))
                except Exception:
                    y = float("nan")
                if math.isnan(y) or math.isinf(y):
                    errs.append(1.0)
                    continue
                d = abs(y_true) if y_true != 0 else 1e-12
                errs.append(abs(y - y_true) / d)
            fold_mres.append(sum(errs) / len(errs) if errs else float("inf"))
        finite = [m for m in fold_mres if math.isfinite(m)]
        if not finite:
            print(f"  {name:<48} {K:<4} all folds failed")
            continue
        mean_mre = sum(finite) / len(finite)
        var = sum((m - mean_mre)**2 for m in finite) / len(finite)
        std_mre = math.sqrt(var)
        print(f"  {name:<48} {K:<4} {mean_mre:<12.4f} {std_mre:<12.4f} {min(finite):<10.4f} {max(finite):<10.4f}")
        if mean_mre < overall_min_mre:
            overall_min_mre = mean_mre
            overall_min_form = name
            overall_min_K = K

    print()
    print("=" * 80)
    print(f"BEST at K=8-12: {overall_min_form} (K={overall_min_K}) → mean CV MRE = {overall_min_mre:.4f}")
    print()
    print("Comparison:")
    print(f"  K≤7  best (gp154c baseline):  1.5756")
    print(f"  K≤12 best (this script):      {overall_min_mre:.4f}")
    print()
    if overall_min_mre < 0.25:
        print(">>> K≤12 PASSES — the wall WAS a complexity-cap artifact.")
        print("    Bounded-null Claim 1 collapses. Reframe needed.")
    elif overall_min_mre < 0.8:
        print(">>> K≤12 makes substantial progress (< 0.8 MRE).")
        print("    Wall is partially complexity-bound. Honest framing must")
        print("    name the K threshold at which it would close.")
    elif overall_min_mre < 1.2:
        print(">>> K≤12 marginal improvement over K≤7.")
        print("    Wall is mostly structural; Claim 1 survives panel attack 2.2")
        print("    with explicit caveat 'no K≤12 closed-form passes either.'")
    else:
        print(">>> K≤12 essentially identical to K≤7.")
        print("    Wall is fully structural. Claim 1 SURVIVES intact under")
        print("    extended-K test. Strawman attack 2.2 is fully defended.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
