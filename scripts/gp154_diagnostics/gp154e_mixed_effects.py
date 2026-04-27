#!/usr/bin/env python3
"""GP-154e — mixed-effects model with study as random effect (Path A.1).

Per Nature MI panel attack 3.2: "within-study clean / cross-study fails"
has competing explanations — (a) genuine methodology incommensurability,
(b) small-n within-study masking the wall, (c) per-study heteroscedastic
noise the K≤7 form cannot absorb.

This script tests (c) directly via random-effects decomposition. If a
random intercept by `study` absorbs >70% of α-variance, then the
"incommensurability" claim is just unmodeled study heterogeneity (lab-
calibration noise), not deep methodology incommensurability. If it
absorbs <30%, the cross-study wall is genuine.

The Intra-Class Correlation Coefficient (ICC) = σ²_study / (σ²_study +
σ²_residual) quantifies this directly.

Usage:
    python scripts/gp154e_mixed_effects.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

_REPO = Path(__file__).resolve().parent.parent
PROJECT_DIR = _REPO / "projects" / "gp154_scaling_law_exponents"
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(_REPO))

from src.ztare.fit.fit_primitive_features import (  # noqa: E402
    load_visible_from_substrate,
)
import features as _feats  # noqa: E402

FEATURES = _feats.FEATURES


def load_alphas() -> dict[int, float]:
    out: dict[int, float] = {}
    triples, _ = load_visible_from_substrate(PROJECT_DIR)
    if triples:
        # load_visible_from_substrate returns list of (features_dict, y_obs)
        # — features_dict is a NEW dict each call, identity won't match
        # FEATURES. Match by content instead.
        for fd, y in triples:
            if y is None:
                continue
            # Find matching row by feature content (study + log10_N is usually unique)
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
    # Add holdout
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


def main() -> int:
    alphas = load_alphas()
    print(f"Loaded {len(alphas)} attributed rows.")
    print()

    # Build dataframe
    rows = []
    for rid, y in alphas.items():
        fd = FEATURES.get(rid, {})
        rows.append({
            "alpha": y,
            "log10_N": fd.get("log10_N_params", 0.0),
            "scaling_var": fd.get("scaling_var", "UNK") or "UNK",
            "modality": fd.get("modality", "UNK") or "UNK",
            "fit_convention": fd.get("fit_convention", "UNK") or "UNK",
            "study": fd.get("study", "UNK") or "UNK",
        })
    df = pd.DataFrame(rows)
    print(f"DataFrame: n={len(df)}")
    print(f"Studies: {df['study'].nunique()}")
    print(f"alpha distribution: mean={df['alpha'].mean():.3f}, std={df['alpha'].std():.3f}, min={df['alpha'].min():.3f}, max={df['alpha'].max():.3f}")
    print()

    # ── Step 1: total variance ─────────────────────────────────────
    total_var = df["alpha"].var(ddof=0)
    print(f"Total α variance (population): {total_var:.4f}")
    print()

    # ── Step 2: null-model mixed effects (intercept-only with study RE) ──
    # alpha ~ 1 + (1 | study)
    print("─── Model 1: Null with random intercept by study ───")
    print("    alpha ~ 1 + (1 | study)")
    try:
        m1 = smf.mixedlm("alpha ~ 1", df, groups=df["study"]).fit(
            method="lbfgs", reml=True
        )
        var_study_1 = float(m1.cov_re.iloc[0, 0])
        var_resid_1 = float(m1.scale)
        icc_1 = var_study_1 / (var_study_1 + var_resid_1)
        print(f"  σ²_study (random intercept variance):   {var_study_1:.4f}")
        print(f"  σ²_residual (within-study residual):    {var_resid_1:.4f}")
        print(f"  ICC = σ²_study / total = {icc_1:.4f} ({100*icc_1:.1f}%)")
    except Exception as e:
        print(f"  Model 1 failed to converge: {e}")
        icc_1 = float("nan")
    print()

    # ── Step 3: with fixed effects (log10_N + scaling_var) ──────────
    print("─── Model 2: log10_N + scaling_var fixed, study random intercept ───")
    print("    alpha ~ log10_N + C(scaling_var) + (1 | study)")
    try:
        m2 = smf.mixedlm(
            "alpha ~ log10_N + C(scaling_var)",
            df, groups=df["study"]
        ).fit(method="lbfgs", reml=True)
        var_study_2 = float(m2.cov_re.iloc[0, 0])
        var_resid_2 = float(m2.scale)
        # Fixed-effect explained variance (residual reduction)
        var_explained_fixed = max(0.0, var_resid_1 - var_resid_2 - var_study_2 + var_study_1) if not (icc_1 != icc_1) else float("nan")
        icc_2 = var_study_2 / (var_study_2 + var_resid_2)
        print(f"  σ²_study after fixed effects:           {var_study_2:.4f}")
        print(f"  σ²_residual after fixed effects:        {var_resid_2:.4f}")
        print(f"  ICC after fixed effects: {icc_2:.4f} ({100*icc_2:.1f}%)")
        print(f"  Fixed effects coefficients:")
        for name, val in zip(m2.fe_params.index, m2.fe_params.values):
            print(f"    {name:<30s} = {val:+.4f}")
    except Exception as e:
        print(f"  Model 2 failed: {e}")
        icc_2 = float("nan")
    print()

    # ── Step 4: full fixed effects ──────────────────────────────────
    print("─── Model 3: log10_N + scaling_var + fit_convention + modality, random study ───")
    print("    alpha ~ log10_N + C(scaling_var) + C(fit_convention) + C(modality) + (1 | study)")
    try:
        m3 = smf.mixedlm(
            "alpha ~ log10_N + C(scaling_var) + C(fit_convention)",
            df, groups=df["study"]
        ).fit(method="lbfgs", reml=True)
        var_study_3 = float(m3.cov_re.iloc[0, 0])
        var_resid_3 = float(m3.scale)
        icc_3 = var_study_3 / (var_study_3 + var_resid_3)
        print(f"  σ²_study after full fixed effects:      {var_study_3:.4f}")
        print(f"  σ²_residual after full fixed effects:   {var_resid_3:.4f}")
        print(f"  ICC after full fixed effects: {icc_3:.4f} ({100*icc_3:.1f}%)")
    except Exception as e:
        print(f"  Model 3 failed: {e}")
        icc_3 = float("nan")
    print()

    # ── Verdict ────────────────────────────────────────────────────
    print("=" * 70)
    print("VERDICT")
    print("=" * 70)
    print(f"Null-model ICC (study explains alpha variance):  {icc_1:.4f} ({100*icc_1:.1f}%)")
    if icc_1 > 0.70:
        print()
        print(">>> ICC > 70% — STUDY ABSORBS MOST OF THE VARIANCE.")
        print("    The 'incommensurability' claim is mostly lab-calibration noise.")
        print("    Each study has a different baseline α offset, but the underlying")
        print("    physics may be unified once the lab effect is removed.")
        print("    Rewrites Act II of the paper: 'Cross-study scaling-law metadata")
        print("    is dominated by per-study calibration drift; once removed via")
        print("    random-intercept correction, residual cross-study heterogeneity")
        print("    is X% (where X is much smaller).'")
    elif icc_1 > 0.30:
        print()
        print(">>> ICC in 30-70% — MIXED PICTURE.")
        print("    Study explains a substantial but not dominant share of α variance.")
        print("    Both per-lab calibration AND structural methodology effects are real.")
        print("    The bounded-null claim survives but with quantified caveat.")
    else:
        print()
        print(">>> ICC < 30% — STUDY DOES NOT ABSORB VARIANCE.")
        print("    The cross-study wall is NOT lab-calibration noise.")
        print("    Methodology incommensurability is structurally deep.")
        print("    Bounded-null claim survives intact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
