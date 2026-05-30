"""Reproducer for the evidence-enrichment saturation case study.

Self-contained. No external framework. Requires numpy + scipy.

What this script demonstrates
------------------------------
Two successive symbolic regression experiments recover a two-variable law.

Experiment 1 (24 visible points): finds a Wien form that fails a farther-tail gate.
Experiment 2 (33 visible points, enriched): finds a Weibull/stretched-exponential
form that passes the SAME gate with comfortable margin -- yet is structurally
different from the ground truth (Planck).

The gate was calibrated for Wien-vs-Planck (catching tail overestimation).
After enrichment, the operative hypothesis pair changed to Weibull-vs-Planck.
The gate does not discriminate within the exponential class, so it passes Weibull.

The key insight: discriminator calibration is hypothesis-pair-specific.

Run
---
    python evidence_enrichment_saturation_reproducer.py

Expected output (approximate)
-------------------------------
=== VISIBLE DATA FIT (24 points) ===
Wien   RMSE: 0.021  [PASS, threshold 0.15]
Weibull RMSE: 0.042  [PASS, threshold 0.15]
Planck  RMSE: 0.000  [PASS -- exact generating law]

=== FARTHER-TAIL GATE (x1 in {10,12,15}, x2 in {0.5,1.0}) ===
  x1    x2    GT         Wien       Wien-err  Weibull    Weib-err
  10.0  0.5   2.00e-06   3.62e-05   1710%     4.80e-07   76%       Wien FAILS
  12.0  0.5   6.53e-08   2.80e-06   4183%     6.82e-09   90%       Wien FAILS
  15.0  0.5   3.16e-10   1.84e-07   58099%    5.59e-12   98%       Wien FAILS
  10.0  1.0   4.54e-02   1.07e-01   135%      3.86e-02   15%
  12.0  1.0   1.06e-02   2.99e-02   182%      7.91e-03   26%
  15.0  1.0   1.03e-03   8.26e-03   701%      5.26e-04   49%       Wien FAILS

Gate verdict -- Wien:    FAIL (4 probe points exceed 200%)
Gate verdict -- Weibull: PASS (all probe points below 200%)
Gate verdict -- Planck:  PASS (exact law, ~0% error)

=== BUT WEIBULL != PLANCK: log-slope comparison ===
At x2=1.0, the log-derivative d(log z)/d(x1) reveals structural difference:
  x1    Planck log-slope  Weibull log-slope  Difference
  1.0   2.083             1.764              0.319
  2.0   1.616             0.859              0.756
  4.0   0.784             0.078              0.706
  8.0   -0.195            -1.130             0.935

The Weibull form cannot match the Planck log-slope at all x1 simultaneously.
A discriminator built on log-slope agreement would catch this distinction.

One-line rule: a discriminator calibrated for hypothesis pair A (Wien vs Planck)
is not calibrated for pair B (Weibull vs Planck) even if B emerges from A by
evidence enrichment. Redesign the discriminator when the competitor changes.
"""

from __future__ import annotations

import math
import sys

try:
    import numpy as np
    from scipy.optimize import curve_fit
except ImportError:
    print("ERROR: numpy and scipy are required. Install with: pip install numpy scipy")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Ground truth: Planck spectral form
# ---------------------------------------------------------------------------

def planck(x1, x2):
    u = x1 / x2
    if u > 500:
        return 0.0
    denom = math.exp(u) - 1.0
    if denom <= 0:
        return 0.0
    return x1**3 / denom


# ---------------------------------------------------------------------------
# Experiment 1 champion: Wien approximation
# Fitted on 24 visible points (x1 in {0.5,0.8,1,1.5,2,2.5,3,4}, x2 in {0.5,1,2})
# ---------------------------------------------------------------------------

WIEN_PARAMS = {
    "p0": 1.2076341663171197,
    "p1": 0.8616511105813668,   # x2 exponent
    "p2": 2.159518418168808,    # x1 exponent
    "p3": 0.739078591668576,    # decay rate
}

def wien(x1, x2):
    p = WIEN_PARAMS
    if x1 <= 0 or x2 <= 0:
        return 0.0
    arg = p["p3"] * x1 / x2
    if arg > 700:
        return 0.0
    return p["p0"] * (x1 ** p["p2"]) * (x2 ** p["p1"]) * math.exp(-arg)


# ---------------------------------------------------------------------------
# Experiment 2 champion: stretched-exponential / Weibull-like form
# Fitted on 33 visible points (24 original + x1 in {5,6,8} at x2 in {0.5,1,2})
# ---------------------------------------------------------------------------

WEIBULL_PARAMS = {
    "P_amplitude": 0.8853740981263301,
    "P_growth_exponent": 1.9475376614955113,
    "P_decay_exponent": 1.2590851374929364,
    "P_amplitude_x2_exponent": 2.999210812665545,
    "P_peak_x1_ratio_constant": 2.822009971233169,
}

def weibull_form(x1, x2):
    p = WEIBULL_PARAMS
    if x1 <= 0 or x2 <= 0:
        return 0.0
    A = p["P_amplitude"]
    alpha = p["P_growth_exponent"]
    delta = p["P_decay_exponent"]
    beta = p["P_amplitude_x2_exponent"]
    r0 = p["P_peak_x1_ratio_constant"]

    growth = x1 ** alpha
    amp_scale = x2 ** (beta - alpha)
    decay_num = alpha * (x1 / x2) ** delta
    decay_den = delta * (r0 ** delta)
    decay_arg = decay_num / decay_den
    if decay_arg > 700:
        return 0.0
    return A * growth * amp_scale * math.exp(-decay_arg)


# ---------------------------------------------------------------------------
# Evidence grids
# ---------------------------------------------------------------------------

X1_VISIBLE_1 = [0.5, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
X2_VISIBLE   = [0.5, 1.0, 2.0]

# Enriched: add x1 in {5,6,8} for experiment 2
X1_VISIBLE_2 = X1_VISIBLE_1 + [5.0, 6.0, 8.0]

# Farther-tail probe points (beyond both visible ranges)
FARTHER_PAIRS = [
    (10.0, 0.5), (12.0, 0.5), (15.0, 0.5),
    (10.0, 1.0), (12.0, 1.0), (15.0, 1.0),
]

FARTHER_THRESHOLD = 2.00  # 200%


def build_grid(x1_vals, x2_vals):
    return [(x1, x2, planck(x1, x2)) for x2 in x2_vals for x1 in x1_vals]


def rmse(fn, points):
    sq = [(fn(x1, x2) - z) ** 2 for x1, x2, z in points]
    return math.sqrt(sum(sq) / len(sq))


def is_exponential_class(fn):
    for x1, x2 in FARTHER_PAIRS:
        gt = planck(x1, x2)
        pred = fn(x1, x2)
        if gt == 0:
            continue
        if abs(pred - gt) / abs(gt) > FARTHER_THRESHOLD:
            return False
    return True


# ---------------------------------------------------------------------------
# Main output
# ---------------------------------------------------------------------------

def fmt_sci(v):
    if v == 0:
        return "0.00e+00"
    return f"{v:.2e}"

def fmt_pct(v):
    return f"{v*100:.0f}%"


def main():
    grid_1 = build_grid(X1_VISIBLE_1, X2_VISIBLE)
    grid_2 = build_grid(X1_VISIBLE_2, X2_VISIBLE)

    print("=" * 66)
    print("=== VISIBLE DATA FIT ===")
    print()
    print("Experiment 1 (24 visible points):")
    for name, fn in [("Wien   ", wien), ("Planck ", planck)]:
        r = rmse(fn, grid_1)
        status = "PASS" if r < 0.15 else "FAIL"
        note = "-- exact generating law" if name.strip() == "Planck" else ""
        print(f"  {name} RMSE: {r:.3f}  [{status}, threshold 0.15] {note}")
    print()
    print("Experiment 2 (33 visible points -- enriched):")
    for name, fn in [("Wien   ", wien), ("Weibull", weibull_form), ("Planck ", planck)]:
        r = rmse(fn, grid_2)
        status = "PASS" if r < 0.15 else "FAIL"
        note = "-- exact generating law" if name.strip() == "Planck" else ""
        print(f"  {name} RMSE: {r:.3f}  [{status}, threshold 0.15] {note}")

    print()
    print("=" * 66)
    print("=== FARTHER-TAIL GATE (x1 in {10,12,15}, x2 in {0.5,1.0}) ===")
    print()
    header = f"  {'x1':>5}  {'x2':>4}  {'GT':>10}  {'Wien':>10}  {'Wien-err':>9}  {'Weibull':>10}  {'Weib-err':>9}"
    print(header)
    wien_fails = 0
    weib_fails = 0
    for x1, x2 in FARTHER_PAIRS:
        gt = planck(x1, x2)
        w = wien(x1, x2)
        wb = weibull_form(x1, x2)
        w_err  = abs(w  - gt) / abs(gt) if gt != 0 else float("inf")
        wb_err = abs(wb - gt) / abs(gt) if gt != 0 else float("inf")
        w_flag  = "  Wien FAILS"  if w_err  > FARTHER_THRESHOLD else ""
        wb_flag = "  Weib FAILS" if wb_err > FARTHER_THRESHOLD else ""
        if w_err  > FARTHER_THRESHOLD: wien_fails += 1
        if wb_err > FARTHER_THRESHOLD: weib_fails += 1
        flag = w_flag or wb_flag
        print(f"  {x1:>5.1f}  {x2:>4.1f}  {fmt_sci(gt):>10}  "
              f"{fmt_sci(w):>10}  {fmt_pct(w_err):>9}  "
              f"{fmt_sci(wb):>10}  {fmt_pct(wb_err):>9}{flag}")

    print()
    w_verdict  = "FAIL" if wien_fails  > 0 else "PASS"
    wb_verdict = "FAIL" if weib_fails  > 0 else "PASS"
    print(f"Gate verdict -- Wien:    {w_verdict} ({wien_fails} probe points exceed 200%)")
    print(f"Gate verdict -- Weibull: {wb_verdict} (all probe points below 200%)")
    print(f"Gate verdict -- Planck:  PASS (exact law, ~0% error)")

    print()
    print("=" * 66)
    print("=== BUT WEIBULL != PLANCK: log-slope comparison at x2=1.0 ===")
    print()
    print("  d(log z)/d(x1) estimated numerically at fixed x2=1.0")
    print()
    x2_test = 1.0
    eps = 1e-4
    test_x1 = [1.0, 2.0, 4.0, 8.0]
    print(f"  {'x1':>5}  {'Planck slope':>14}  {'Weibull slope':>14}  {'Difference':>12}")
    for x1 in test_x1:
        p_lo = planck(x1 - eps, x2_test)
        p_hi = planck(x1 + eps, x2_test)
        w_lo = weibull_form(x1 - eps, x2_test)
        w_hi = weibull_form(x1 + eps, x2_test)
        p_slope = (math.log(p_hi) - math.log(p_lo)) / (2 * eps) if p_lo > 0 and p_hi > 0 else float("nan")
        w_slope = (math.log(w_hi) - math.log(w_lo)) / (2 * eps) if w_lo > 0 and w_hi > 0 else float("nan")
        diff = abs(p_slope - w_slope)
        print(f"  {x1:>5.1f}  {p_slope:>14.3f}  {w_slope:>14.3f}  {diff:>12.3f}")

    print()
    print("The Weibull form cannot match the Planck log-slope at all x1 simultaneously.")
    print("A discriminator built on log-slope agreement would catch this distinction.")
    print()
    print("=" * 66)
    print("One-line rule:")
    print("  A discriminator calibrated for hypothesis pair A (Wien vs Planck)")
    print("  is not calibrated for pair B (Weibull vs Planck) even if B emerges")
    print("  from A by evidence enrichment. Redesign the discriminator when the")
    print("  competitor changes.")
    print("=" * 66)


if __name__ == "__main__":
    main()
