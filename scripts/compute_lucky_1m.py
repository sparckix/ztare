#!/usr/bin/env python3
"""Compute 1M Lucky numbers for convergence rate verification.

Run: nohup python3 -u scripts/compute_lucky_1m.py > lucky_1m.log 2>&1 &
Expected time: ~50-60 minutes.
"""
import time, math, json
import numpy as np
from scipy.optimize import curve_fit
from pathlib import Path

def lucky_sieve(limit):
    sieve = list(range(1, limit + 1, 2))
    i = 1
    while i < len(sieve) and sieve[i] <= len(sieve):
        step = sieve[i]
        sieve = [s for j, s in enumerate(sieve) if (j + 1) % step != 0]
        i += 1
        if len(sieve) % 500000 == 0:
            print(f"  Sieve: {len(sieve):,d} remaining...")
    return sieve

print("Computing Lucky numbers (target: 1M+)...")
start = time.time()
lucky = lucky_sieve(16_000_000)
elapsed = time.time() - start
n_lucky = min(len(lucky), 1_000_000)
print(f"Done: {len(lucky):,d} Lucky numbers in {elapsed:.1f}s")
if n_lucky >= 1_000_000:
    print(f"L(1000000) = {lucky[999999]:,d}")

out = Path("projects/oeis_a000959/lucky_1m.json")
out.write_text(json.dumps(lucky[:n_lucky]))
print(f"Saved {n_lucky:,d} to {out}")

# Coefficient stability test with GP-113 form
def gp113_model(n, a, b, c, d, e):
    return a + b * np.log(n) + c / (n + d) + e * np.log(n)**2

print(f"\nGP-113 form stability across scales:")
print(f"{'Fit range':>25s}  {'b':>8s}  {'e':>10s}  {'b_eff':>8s}")
print("-" * 60)

for n_max in [50000, 100000, 200000, 500000, 1000000]:
    if n_max > n_lucky: break
    x = np.arange(500, n_max, dtype=float)
    y = np.array([lucky[i] / (i + 1) for i in range(499, n_max - 1)])
    try:
        popt, _ = curve_fit(gp113_model, x, y,
                           p0=[0.38, 1.24, -112, 5382, -0.003], maxfev=20000)
        b_eff = popt[1] + 2 * popt[4] * np.log(n_max)
        print(f"{'n=500..'+str(n_max):>25s}  {popt[1]:>8.4f}  {popt[4]:>10.6f}  {b_eff:>8.4f}")
    except Exception as ex:
        print(f"{'n=500..'+str(n_max):>25s}  FIT FAILED: {ex}")

print(f"\nIf b and e are stable from 500K to 1M: the log^2 correction is structural.")
print(f"If they drift: the form is a local surrogate (same pattern as a=1.200).")
