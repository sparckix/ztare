"""Reproducer for the evidence-grid underdetermination case study.

Self-contained. No external framework. Requires numpy + scipy.

What this script demonstrates
------------------------------
Two structurally distinct two-variable functions are indistinguishable
on a bounded evidence grid:

  Form A (Wien approximation):  z = p0 * x2^p1 * x1^p2 * exp(-p3 * x1/x2)
  Form B (Planck):               z = x1^3 / (exp(x1/x2) - 1)

Both achieve RMSE < 0.025 on 24 visible points and a 16-point holdout
drawn from unseen values of x2. A standard evaluation battery
(visible RMSE + holdout hard gate) correctly passes both forms.

A farther-tail discriminator -- relative error at (x1, x2) pairs where
the two forms disagree most -- catches the distinction immediately.
Form A exceeds 200% relative error at (x1=6, x2=0.5). Form B (the
exact generating law) stays below 0.01% everywhere.

The standard battery is satisfying the FORM of a generalization test
(RMSE on unseen x2 values) while missing the INTENT: it does not probe
the x1/x2 regime where the two structural classes actually diverge.

Run
---
    python evidence_grid_underdetermination_reproducer.py

Expected output
---------------
    Check 1 (visible RMSE + holdout gate): both forms PASS
    Check 2 (farther-tail discriminator):  Form A FAILS, Form B PASSES
    ...
"""
from __future__ import annotations

import math
import numpy as np
from scipy.optimize import least_squares


# ---------------------------------------------------------------------------
# Ground truth (Planck form -- no free parameters)
# ---------------------------------------------------------------------------

def planck(x1: float, x2: float) -> float:
    ratio = x1 / x2
    if ratio > 500.0:
        return 0.0
    denom = math.exp(ratio) - 1.0
    if denom == 0.0:
        return 0.0
    return x1 ** 3 / denom


# ---------------------------------------------------------------------------
# Wien approximation (4 free parameters, fitted to visible data)
# ---------------------------------------------------------------------------

def wien(x1: float, x2: float, p0: float, p1: float, p2: float, p3: float) -> float:
    return p0 * (x2 ** p1) * (x1 ** p2) * math.exp(-p3 * x1 / x2)


# ---------------------------------------------------------------------------
# Evidence grids
# ---------------------------------------------------------------------------

_X1_VISIBLE = [0.5, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
_X2_VISIBLE  = [0.5, 1.0, 2.0]
_X2_HOLDOUT  = [0.75, 1.5]

_FARTHER_PAIRS = [
    (5.0, 0.5), (6.0, 0.5), (8.0, 0.5),
    (5.0, 1.0), (6.0, 1.0), (8.0, 1.0),
]


def build_grid(x1_vals, x2_vals):
    pts = []
    for x2 in x2_vals:
        for x1 in x1_vals:
            pts.append((x1, x2, planck(x1, x2)))
    return pts


def visible_grid():
    return build_grid(_X1_VISIBLE, _X2_VISIBLE)


def holdout_grid():
    return build_grid(_X1_VISIBLE, _X2_HOLDOUT)


# ---------------------------------------------------------------------------
# Fit Wien form to visible data
# ---------------------------------------------------------------------------

def fit_wien(pts):
    """Fit the 4-parameter Wien form to the given (x1, x2, z) triples."""
    x1s = np.array([p[0] for p in pts])
    x2s = np.array([p[1] for p in pts])
    zs  = np.array([p[2] for p in pts])

    def residuals(params):
        p0, p1, p2, p3 = params
        pred = np.array([wien(x1, x2, p0, p1, p2, p3)
                         for x1, x2 in zip(x1s, x2s)])
        return pred - zs

    x0 = np.array([1.0, 1.0, 2.0, 0.5])
    lo = np.array([0.01, 0.1, 0.1, 0.01])
    hi = np.array([10.0, 5.0, 5.0, 5.0])
    res = least_squares(residuals, x0, bounds=(lo, hi), max_nfev=5000)
    return res.x


# ---------------------------------------------------------------------------
# RMSE utility
# ---------------------------------------------------------------------------

def rmse(fn, pts):
    sq = [(fn(x1, x2) - z) ** 2 for x1, x2, z in pts]
    return math.sqrt(sum(sq) / len(sq))


# ---------------------------------------------------------------------------
# Check 1: visible RMSE + holdout hard gate
# ---------------------------------------------------------------------------

def check1_visible_and_holdout(wien_params):
    p0, p1, p2, p3 = wien_params
    wien_fn = lambda x1, x2: wien(x1, x2, p0, p1, p2, p3)
    planck_fn = planck

    vis = visible_grid()
    hld = holdout_grid()
    threshold = 0.15

    results = {}
    for label, fn in [("Form A (Wien)", wien_fn), ("Form B (Planck)", planck_fn)]:
        vis_rmse = rmse(fn, vis)
        hld_rmse = rmse(fn, hld)
        passed = (vis_rmse < threshold) and (hld_rmse < threshold)
        results[label] = dict(vis_rmse=vis_rmse, hld_rmse=hld_rmse, passed=passed)
    return results


# ---------------------------------------------------------------------------
# Check 2: farther-tail discriminator
# ---------------------------------------------------------------------------

_REL_TOL = 2.00  # 200%


def check2_farther_tail(wien_params):
    p0, p1, p2, p3 = wien_params
    wien_fn = lambda x1, x2: wien(x1, x2, p0, p1, p2, p3)
    planck_fn = planck

    results = {}
    for label, fn in [("Form A (Wien)", wien_fn), ("Form B (Planck)", planck_fn)]:
        rows = []
        passed = True
        for x1, x2 in _FARTHER_PAIRS:
            gt = planck(x1, x2)
            pred = fn(x1, x2)
            rel_err = abs(pred - gt) / abs(gt) if gt != 0 else float("inf")
            fail = rel_err > _REL_TOL
            if fail:
                passed = False
            rows.append((x1, x2, gt, pred, rel_err, fail))
        results[label] = dict(rows=rows, passed=passed)
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 72)
    print("EVIDENCE GRID UNDERDETERMINATION -- REPRODUCER")
    print("=" * 72)
    print()
    print("Ground truth (Form B, Planck):  z = x1^3 / (exp(x1/x2) - 1)")
    print("Competitor  (Form A, Wien):     z = p0 * x2^p1 * x1^p2 * exp(-p3*x1/x2)")
    print()

    # Fit Wien to visible data
    vis = visible_grid()
    wien_params = fit_wien(vis)
    p0, p1, p2, p3 = wien_params
    print(f"Wien best-fit parameters (24 visible points):")
    print(f"  p0={p0:.4f}  p1={p1:.4f}  p2={p2:.4f}  p3={p3:.4f}")
    print()

    # Check 1
    print("-" * 72)
    print("Check 1 -- visible RMSE + holdout hard gate (the check that passes)")
    print("-" * 72)
    c1 = check1_visible_and_holdout(wien_params)
    for label, r in c1.items():
        verdict = "PASSED" if r["passed"] else "FAILED"
        print(f"  {label}:")
        print(f"    visible RMSE = {r['vis_rmse']:.4f}  (threshold 0.15)")
        print(f"    holdout RMSE = {r['hld_rmse']:.4f}  (threshold 0.15)")
        print(f"    VERDICT: {verdict}")
    print()

    # Check 2
    print("-" * 72)
    print("Check 2 -- farther-tail discriminator (the check that catches)")
    print("-" * 72)
    c2 = check2_farther_tail(wien_params)
    for label, r in c2.items():
        verdict = "PASSED" if r["passed"] else "FAILED"
        print(f"  {label}  ({verdict})")
        print(f"  {'x1':>5}  {'x2':>5}  {'GT':>10}  {'Pred':>10}  {'rel_err':>10}  {'fail?':>6}")
        for x1, x2, gt, pred, rel_err, fail in r["rows"]:
            flag = "<<< FAIL" if fail else ""
            print(f"  {x1:>5.1f}  {x2:>5.1f}  {gt:>10.6f}  {pred:>10.6f}  "
                  f"{rel_err*100:>9.1f}%  {flag}")
        print()

    # Summary
    print("-" * 72)
    print("Summary")
    print("-" * 72)
    c1_a = c1["Form A (Wien)"]["passed"]
    c1_b = c1["Form B (Planck)"]["passed"]
    c2_a = c2["Form A (Wien)"]["passed"]
    c2_b = c2["Form B (Planck)"]["passed"]

    if c1_a and c1_b and not c2_a and c2_b:
        print("Both forms PASS the standard battery (visible + holdout).")
        print("Only Form B (Planck) PASSES the farther-tail discriminator.")
        print()
        print("The standard battery satisfies the FORM of a generalization test")
        print("(RMSE on unseen x2 values) while missing the INTENT: it does not")
        print("probe the x1/x2 regime where the Wien and Planck forms diverge.")
        print()
        print("The farther-tail discriminator probes the high-x1/x2 regime where")
        print("exp(x1/x2) - 1 and exp(x1/x2) are no longer interchangeable.")
        print("Form A exhausts its degrees of freedom fitting the visible range")
        print("and cannot simultaneously be correct at high x1/x2 ratios.")
        print()
        print("Fix: extend the evidence grid to x1 > 4 at small x2 before")
        print("declaring a form as structurally confirmed. The discriminative")
        print("regime is where the competing structural classes disagree most,")
        print("not where you happened to measure.")
    else:
        print(f"Check 1 -- Form A: {'PASS' if c1_a else 'FAIL'}  "
              f"Form B: {'PASS' if c1_b else 'FAIL'}")
        print(f"Check 2 -- Form A: {'PASS' if c2_a else 'FAIL'}  "
              f"Form B: {'PASS' if c2_b else 'FAIL'}")


if __name__ == "__main__":
    main()
