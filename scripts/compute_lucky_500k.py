#!/usr/bin/env python3
"""Compute 500K Lucky numbers and test coefficient stability.

Run: nohup python -u scripts/compute_lucky_500k.py > lucky_500k.log 2>&1 &
Expected time: ~10-20 minutes.
"""

import time, math, json
import numpy as np
from scipy.optimize import curve_fit
from pathlib import Path

def lucky_sieve(limit):
    """Sieve of Josephus Flavius."""
    sieve = list(range(1, limit + 1, 2))
    i = 1
    while i < len(sieve) and sieve[i] <= len(sieve):
        step = sieve[i]
        sieve = [s for j, s in enumerate(sieve) if (j + 1) % step != 0]
        i += 1
        if len(sieve) % 100000 == 0:
            print(f"  Sieve: {len(sieve):,d} remaining...")
    return sieve

print("Computing Lucky numbers (target: 500K+)...")
start = time.time()
lucky = lucky_sieve(8_500_000)
elapsed = time.time() - start
print(f"Done: {len(lucky):,d} Lucky numbers in {elapsed:.1f}s")
n_lucky = min(len(lucky), 500000)
if n_lucky >= 500000:
    print(f"L(500000) = {lucky[499999]:,d}, density = {lucky[499999]/500000:.4f}")
else:
    print(f"WARNING: only {n_lucky:,d} Lucky numbers (need 500K). Increase sieve limit.")

# Save
out = Path("projects/oeis_a000959/lucky_500k.json")
out.write_text(json.dumps(lucky[:n_lucky]))
print(f"Saved to {out}")

# Coefficient stability test
def model(n, a, b, c):
    return a * np.log(n) + b / n + c

print(f"\nCoefficient stability across scales:")
print(f"{'Fit range':>25s}  {'a':>8s}  {'b':>9s}  {'c':>8s}")
print("-" * 55)

for n_max in [5000, 10000, 50000, 100000, 200000, 500000]:
    if n_max > n_lucky:
        break
    x = np.arange(500, n_max, dtype=float)
    y = np.array([lucky[i] / (i + 1) for i in range(499, n_max - 1)])
    popt, _ = curve_fit(model, x, y, p0=[1.2, -5, 0.5], maxfev=10000)
    print(f"{'n=500..' + str(n_max):>25s}  {popt[0]:>8.4f}  {popt[1]:>9.2f}  {popt[2]:>8.4f}")

# Extrapolation test: fit on n=500..5000, predict at far end
if n_lucky >= 400000:
    print(f"\nExtrapolation test (100x beyond visible):")
    x_vis = np.arange(500, 5001, dtype=float)
    y_vis = np.array([lucky[i] / (i + 1) for i in range(499, 5000)])
    popt_vis, _ = curve_fit(model, x_vis, y_vis, p0=[1.2, -5, 0.5])

    far_start = min(400000, n_lucky - 1000)
    x_far = np.arange(far_start, n_lucky, dtype=float)
    y_far = np.array([lucky[i] / (i + 1) for i in range(far_start - 1, n_lucky - 1)])
    pred = model(x_far, *popt_vis)
    far_res = float(np.max(np.abs(y_far - pred)))
    far_rel = far_res / float(np.max(np.abs(y_far)))
    print(f"  Extrapolation range: n={far_start}..{n_lucky}")
    print(f"  Max absolute residual: {far_res:.6f}")
    print(f"  Max relative residual: {far_rel:.6f} ({far_rel*100:.4f}%)")
    print(f"  Gate threshold (absolute 0.05): {'PASS' if far_res < 0.05 else 'FAIL'}")
    print(f"  Gate threshold (relative 0.5%): {'PASS' if far_rel < 0.005 else 'FAIL'}")
else:
    print(f"\nSkipping extrapolation test (need >= 400K Lucky numbers, have {n_lucky:,d})")
