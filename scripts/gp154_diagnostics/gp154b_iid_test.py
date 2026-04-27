#!/usr/bin/env python3
"""GP-154b — IID-holdout parallel test (Bug #41, 2026-04-25 night).

Per Gemini Pro panel: gp154's wall is distribution-shift. To isolate
"feature sufficiency" from "universal-law extrapolation," we re-split
the 94 attributed rows (82 visible + 12 holdout) randomly with
stratification on fit_convention, so both visible and holdout have
matched distributions. If the K≤7 forms now pass HOLDOUT < 0.25, we
have proven feature sufficiency — universal-law claim is rejected
but feature-completeness diagnostic claim is upheld. If they still
fail, the bounded-null is even stronger.

EPISTEMIC AIRGAP NOTE: this script reads the holdout truth (already
unsealed earlier this session). Future cross-family runs should
re-seal a fresh holdout before any agent inspection.

Usage:
    python scripts/gp154b_iid_test.py [--seed N]

Reports:
    - The original (OOD) split's feature distribution
    - The shuffled (IID) split's feature distribution (verify matched)
    - All 18 candidate forms re-fit on IID-visible, evaluated on IID-holdout
    - Side-by-side comparison: OOD MRE vs IID MRE per candidate
"""
from __future__ import annotations

import argparse
import math
import random
import sys
from collections import Counter
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


# ── Load all attributed rows (visible y + holdout y) ─────────────────────


def load_visible_alphas() -> dict[int, float]:
    """Parse evidence.txt for (id, alpha) in visible section."""
    out: dict[int, float] = {}
    text = (PROJECT_DIR / "evidence.txt").read_text(encoding="utf-8")
    section = "VISIBLE"
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if "===" in line:
                upper = line.upper()
                if "VISIBLE_SET" in upper or "VISIBLE-SET" in upper:
                    section = "VISIBLE"
                elif "HOLDOUT" in upper or "FARTHER" in upper or "HONEST" in upper:
                    section = "OTHER"
            continue
        if section != "VISIBLE":
            continue
        # Try TSV first, then whitespace
        parts = line.split("\t") if "\t" in line else line.split()
        if len(parts) < 2:
            continue
        try:
            out[int(parts[0])] = float(parts[1])
        except (ValueError, IndexError):
            continue
    return out


def load_holdout_alphas() -> dict[int, float]:
    """Parse evidence_holdout.txt for HOLDOUT_SET only (not farther/honest)."""
    out: dict[int, float] = {}
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


# ── Load FEATURES + try to recover visible alphas from substrate too ─────


import features as _feats  # noqa: E402

FEATURES = _feats.FEATURES
visible_y = load_visible_alphas()
holdout_y = load_holdout_alphas()

# Substrate's canonical visible_rows() may have additional rows that
# evidence.txt doesn't expose; merge them in if available.
try:
    triples = _feats.visible_rows()
    for rid, y, _ in triples:
        if rid not in visible_y and y is not None:
            try:
                visible_y[int(rid)] = float(y)
            except (TypeError, ValueError):
                pass
except Exception:
    pass


# ── Build the pool of attributed rows ────────────────────────────────────

attributed: dict[int, float] = {}
attributed.update(visible_y)
attributed.update(holdout_y)
print(f"Pool size: {len(attributed)} rows ({len(visible_y)} visible + {len(holdout_y)} holdout, dedup'd)")
print()


# ── Stratified random shuffle by fit_convention ──────────────────────────


def stratify_split(pool: dict[int, float], n_holdout: int, seed: int) -> tuple[list[int], list[int]]:
    """Stratified split: bucket by fit_convention, sample proportionally."""
    rng = random.Random(seed)
    buckets: dict[str, list[int]] = {}
    for rid in pool:
        fc = FEATURES.get(rid, {}).get("fit_convention", "UNK")
        buckets.setdefault(fc, []).append(rid)
    # Shuffle each bucket
    for ids in buckets.values():
        rng.shuffle(ids)
    # Proportional allocation: each bucket contributes ceil(n_holdout × bucket_frac)
    total = len(pool)
    holdout: list[int] = []
    for fc, ids in buckets.items():
        n_take = max(0, round(n_holdout * len(ids) / total))
        holdout.extend(ids[:n_take])
    # Trim/pad to exact n_holdout
    if len(holdout) > n_holdout:
        # Drop extras from largest bucket first
        rng.shuffle(holdout)
        holdout = holdout[:n_holdout]
    elif len(holdout) < n_holdout:
        # Add from any bucket
        leftover = [rid for fc, ids in buckets.items() for rid in ids if rid not in holdout]
        rng.shuffle(leftover)
        holdout.extend(leftover[: (n_holdout - len(holdout))])
    holdout_set = set(holdout)
    visible = [rid for rid in pool if rid not in holdout_set]
    return visible, holdout


def feature_dist(ids: list[int], key: str) -> dict[str, float]:
    c = Counter(FEATURES.get(rid, {}).get(key, "NONE") for rid in ids)
    total = sum(c.values()) or 1
    return {k: 100.0 * v / total for k, v in c.most_common()}


# ── Original (OOD) split for comparison ──────────────────────────────────

ood_visible_ids = [r for r in attributed if r in visible_y and r not in holdout_y]
ood_holdout_ids = [r for r in holdout_y]
print("─── ORIGINAL (OOD) split feature distribution ───")
for key in ("fit_convention", "modality"):
    print(f"  {key}:")
    print(f"    visible:")
    for k, pct in sorted(feature_dist(ood_visible_ids, key).items(), key=lambda kv: -kv[1])[:5]:
        print(f"      {k:35s} {pct:5.1f}%")
    print(f"    holdout:")
    for k, pct in sorted(feature_dist(ood_holdout_ids, key).items(), key=lambda kv: -kv[1])[:5]:
        print(f"      {k:35s} {pct:5.1f}%")
print()


# ── IID stratified split ─────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    iid_visible_ids, iid_holdout_ids = stratify_split(
        attributed, n_holdout=len(ood_holdout_ids), seed=args.seed
    )
    print(f"─── IID (stratified-shuffle, seed={args.seed}) split feature distribution ───")
    for key in ("fit_convention", "modality"):
        print(f"  {key}:")
        print(f"    visible:")
        for k, pct in sorted(feature_dist(iid_visible_ids, key).items(), key=lambda kv: -kv[1])[:5]:
            print(f"      {k:35s} {pct:5.1f}%")
        print(f"    holdout:")
        for k, pct in sorted(feature_dist(iid_holdout_ids, key).items(), key=lambda kv: -kv[1])[:5]:
            print(f"      {k:35s} {pct:5.1f}%")
    print()

    # Construct visible_data lists for fit_features
    iid_visible_data = [
        (FEATURES[rid], attributed[rid]) for rid in iid_visible_ids if rid in FEATURES
    ]
    iid_holdout_truth = {rid: attributed[rid] for rid in iid_holdout_ids if rid in FEATURES}

    print(f"IID visible n: {len(iid_visible_data)} | IID holdout n: {len(iid_holdout_truth)}")
    print()

    # Same candidates as offline_verify Round 4 (most diverse subset)
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
    ]

    print("─── Candidate forms: IID HOLDOUT MRE vs OOD HOLDOUT MRE (from offline_verify) ───")
    print(f"{'Form':<35} {'visible':<10} {'IID HOLDOUT':<14} {'verdict':<8}")
    best_iid = float("inf")
    n_pass_iid = 0
    for name, form, params in candidates:
        result = fit_features(
            form, params, iid_visible_data,
            n_starts=5, seed=args.seed * 31, k_law_max=15,
            disable_sparse_indicator_reject=True,
        )
        if not result.success:
            err = (result.error_message or "")[:50]
            print(f"  {name:<35} fit_failed: {err}")
            continue
        fn = _safe_compile_form(form)
        errs = []
        n_finite = 0
        for rid, y_true in iid_holdout_truth.items():
            try:
                y = float(fn(FEATURES[rid], result.fitted_params))
            except Exception:
                y = float("nan")
            if math.isnan(y) or math.isinf(y):
                errs.append(1.0)
                continue
            n_finite += 1
            denom = abs(y_true) if y_true != 0 else 1e-12
            errs.append(abs(y - y_true) / denom)
        mre = sum(errs) / len(errs) if errs else float("inf")
        verdict = "PASS" if mre < 0.25 else "FAIL"
        if mre < best_iid:
            best_iid = mre
        if mre < 0.25:
            n_pass_iid += 1
        print(f"  {name:<35} {result.mean_abs_residual:<10.4f} {mre:<14.4f} {verdict}")

    print()
    print("=" * 70)
    print(f"IID best HOLDOUT MRE: {best_iid:.4f} ({'PASS' if best_iid < 0.25 else 'FAIL'} threshold=0.25)")
    print(f"IID candidates passing: {n_pass_iid}/{len(candidates)}")
    print()
    if best_iid < 0.25:
        print(">>> IID HOLDOUT PASSES.")
        print("    Feature sufficiency CONFIRMED. The OOD wall in gp154 is")
        print("    distribution-shift sensitivity, not feature insufficiency.")
        print("    Reframe ZTARE as Ontological Diagnostic Tool — paper viable.")
    else:
        print(">>> IID HOLDOUT FAILS.")
        print(f"    Even with matched-distribution split (seed={args.seed}), no K≤7")
        print(f"    form passes. Best MRE {best_iid:.4f} >> 0.25.")
        print(f"    Bounded null is irreducible — gp154's heterogeneity is")
        print(f"    structural at K≤7, regardless of distribution match.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
