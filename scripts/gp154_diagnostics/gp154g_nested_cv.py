#!/usr/bin/env python3
"""GP-154g — nested CV for form-family selection (Path A.4 / panel attack 1.4).

Per Nature MI panel attack 1.4: "Best-of-18 candidate form selection
across 5 families with no nested CV is winner's-curse p-hacking — the
1.58 is a downwardly-biased number."

This script implements proper nested CV: outer 5-fold for unbiased
generalization estimate, inner 5-fold for form-family selection. The
outer-fold mean MRE is the honest panel-survivable bound.

Protocol (exactly as a Nature MI reviewer would demand):
- Outer split: stratified 5-fold over n=51 attributable rows
- For each outer fold f_outer:
  - Inner split: stratified 5-fold over the (training - f_outer) data
  - For each candidate form C:
    - Average inner-CV MRE across the 5 inner folds → score_C
  - Pick C* = argmin_C score_C   (form selection done WITHOUT seeing f_outer)
  - Refit C* on full (training - f_outer) data
  - Evaluate on f_outer → outer_mre_f_outer
- Report: mean(outer_mre across 5 folds) ± std

The form-family selection is done inside-the-fold so the outer evaluation
is truly held-out from the selection process. Compare to gp154c's
"best-of-18" which let form selection see the full holdout — that is
exactly the p-hacking the panel flagged.

Usage:
    python scripts/gp154g_nested_cv.py [--seed 42]
"""
from __future__ import annotations

import argparse
import math
import random
import sys
from collections import Counter, defaultdict
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


def evaluate_one(form, params, train_data, holdout_truth) -> float:
    r = fit_features(form, params, train_data, n_starts=3, seed=2026, k_law_max=15,
                     disable_sparse_indicator_reject=True)
    if not r.success:
        return float("inf")
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
    return sum(errs) / len(errs) if errs else float("inf")


CANDIDATES = [
    ("constant_K=1", "params['c']", ["c"]),
    ("per_scaling_var_K=4",
     "params['c_N'] if features['scaling_var']=='N' else "
     "(params['c_D'] if features['scaling_var']=='D' else "
     "(params['c_C'] if features['scaling_var']=='C' else params['c_other']))",
     ["c_N","c_D","c_C","c_other"]),
    ("log_N_linear_K=2",
     "params['a'] + params['b'] * features['log10_N_params']",
     ["a","b"]),
    ("scaling_var_x_log_N_K=7",
     "(params['a_N'] + params['b_N'] * features['log10_N_params']) "
     "  if features['scaling_var']=='N' else "
     "((params['a_D'] + params['b_D'] * features['log10_N_params']) "
     "   if features['scaling_var']=='D' else "
     "((params['a_C'] + params['b_C'] * features['log10_N_params']) "
     "    if features['scaling_var']=='C' else params['a_other']))",
     ["a_N","b_N","a_D","b_D","a_C","b_C","a_other"]),
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
     ["a","b","c"]),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    alphas = load_alphas()
    print(f"Pool: {len(alphas)} attributed rows.")
    rids = sorted(alphas.keys())
    outer_folds = stratify_kfold(rids, 5, args.seed)
    print(f"Outer fold sizes: {[len(f) for f in outer_folds]}")
    print()

    print("─── Nested 5×5 CV (outer for evaluation, inner for form selection) ───")
    print(f"{'Outer fold':<12} {'Selected C*':<32} {'Outer MRE':<12} {'Inner CV MRE of C*':<20}")
    outer_mres = []
    selected_forms = Counter()
    for outer_idx, outer_fold in enumerate(outer_folds):
        outer_holdout = set(outer_fold)
        inner_pool = [r for r in rids if r not in outer_holdout]
        inner_folds = stratify_kfold(inner_pool, 5, args.seed + outer_idx + 1)
        # Score each candidate via inner CV
        candidate_scores = []
        for cname, cform, cparams in CANDIDATES:
            inner_mres = []
            for inner_holdout in inner_folds:
                inner_set = set(inner_holdout)
                inner_train = [(FEATURES[r], alphas[r])
                               for r in inner_pool if r not in inner_set and r in FEATURES]
                inner_truth = {r: alphas[r] for r in inner_holdout if r in FEATURES}
                m = evaluate_one(cform, cparams, inner_train, inner_truth)
                if math.isfinite(m):
                    inner_mres.append(m)
            inner_mean = sum(inner_mres) / len(inner_mres) if inner_mres else float("inf")
            candidate_scores.append((cname, cform, cparams, inner_mean))
        # Select winner
        winner = min(candidate_scores, key=lambda t: t[3])
        c_name, c_form, c_params, c_inner_score = winner
        selected_forms[c_name] += 1
        # Refit on full inner pool, evaluate on outer holdout
        full_train = [(FEATURES[r], alphas[r]) for r in inner_pool if r in FEATURES]
        outer_truth = {r: alphas[r] for r in outer_fold if r in FEATURES}
        outer_mre = evaluate_one(c_form, c_params, full_train, outer_truth)
        if math.isfinite(outer_mre):
            outer_mres.append(outer_mre)
        print(f"  fold {outer_idx}    {c_name:<32} {outer_mre:<12.4f} {c_inner_score:<20.4f}")

    print()
    if outer_mres:
        nested_mean = sum(outer_mres) / len(outer_mres)
        nested_var = sum((m - nested_mean)**2 for m in outer_mres) / len(outer_mres)
        nested_std = math.sqrt(nested_var)
    else:
        nested_mean = float("inf")
        nested_std = float("nan")

    print("=" * 80)
    print("VERDICT — winner's-curse-corrected bound:")
    print(f"  Naive 'best-of-5' (gp154c, p-hacked):       1.58 ± 0.55")
    print(f"  Nested CV (this script, panel-survivable):  {nested_mean:.4f} ± {nested_std:.4f}")
    print(f"  Form-selection stability across folds:      {dict(selected_forms)}")
    print()
    if nested_mean - 1.58 < 0.10:
        print(">>> Naive bound is honest within tolerance.")
        print("    The 1.58 number was not significantly biased downward by")
        print("    form-family selection. Panel attack 1.4 mostly defended.")
    else:
        print(">>> Nested CV reveals winner's-curse correction.")
        print(f"    True generalization bound is {nested_mean:.4f}, larger than 1.58.")
        print("    The Act II claim must use the nested-CV number, not the")
        print("    p-hacked 'best-of' number.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
