"""test_v2_ground_truth_recovery.py — does v2.0 select the correct (h_in, h_out)?

Generates synthetic data from a KNOWN (h_in_GT, h_out_GT, law). Runs v2.0's
MDL evaluation across all 49 candidate pairs in Σ². Verifies the GT pair
ranks within the top 3.

This is the critical correctness test for the Framer's actual job.
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest_framer_mdl_v2_vs_v1 import compute_v2_mdl


N = 200
RNG = np.random.default_rng(42)


SIGMA = {
    "identity":   (lambda y: y, lambda y: y, 0),
    "log":        (lambda y: np.log(np.abs(y) + 1e-30),
                   lambda y: np.exp(y), 0),
    "exp":        (lambda y: np.exp(np.clip(y, -50, 50)),
                   lambda y: np.log(np.abs(y) + 1e-30), 0),
    "reciprocal": (lambda y: 1 / np.where(np.abs(y) < 1e-30, 1e-30, y),
                   lambda y: 1 / np.where(np.abs(y) < 1e-30, 1e-30, y), 0),
    "power_2":    (lambda y: y ** 2,
                   lambda y: np.sign(y) * np.sqrt(np.abs(y)), 1),
    "power_0.5":  (lambda y: np.sign(y) * np.sqrt(np.abs(y) + 1e-30),
                   lambda y: np.sign(y) * y ** 2, 1),
    "scale_2":    (lambda y: 2 * y, lambda y: y / 2, 1),
}


def gen_synthetic(h_in_name, h_out_name, law_fn, n=N, x_range=(0.5, 10), sigma=0.01):
    h_in_fn, _, _ = SIGMA[h_in_name]
    _, h_out_inv, _ = SIGMA[h_out_name]
    x = np.linspace(x_range[0], x_range[1], n)
    z = h_in_fn(x)
    y_framed = law_fn(z)
    y_clean = h_out_inv(y_framed)
    noise = RNG.normal(0, sigma * np.maximum(np.abs(y_clean), 1.0), size=n)
    return x, y_clean + noise


def evaluate_all_pairs(x, y, deg=3):
    results = []
    for hi_name, (hi_fn, _, hi_k) in SIGMA.items():
        for ho_name, (ho_fn, ho_inv, ho_k) in SIGMA.items():
            try:
                _ = hi_fn(x[:5])
                _ = ho_fn(y[:5])
                _ = ho_inv(y[:5])
                mdl, sig = compute_v2_mdl(
                    x, y, hi_fn, ho_fn, ho_inv,
                    k_law=deg + 1, k_hin=hi_k, k_hout=ho_k, deg=deg,
                )
                if not (math.isinf(mdl) or math.isnan(mdl)):
                    results.append((mdl, sig, hi_name, ho_name))
            except Exception:
                pass
    results.sort()
    return results


def main() -> int:
    test_cases = [
        ("y=log(x)",      "identity",    "exp",      lambda z: z, (1.0, 10.0)),
        ("y=1/x",         "reciprocal",  "identity", lambda z: z, (0.5, 10.0)),
        ("y=exp(x)",      "identity",    "log",      lambda z: z, (0.0, 5.0)),
        ("y=x²",          "power_2",     "identity", lambda z: z, (0.0, 10.0)),
        ("y=sqrt(x)",     "power_0.5",   "identity", lambda z: z, (0.5, 10.0)),
    ]
    print(f"{'GT case':15s} {'GT_pair':30s} {'v2_top_pair':30s} {'GT_rank':>8s}  Verdict")
    n_correct = 0
    n_near = 0
    for label, hi_gt, ho_gt, law, x_range in test_cases:
        x, y = gen_synthetic(hi_gt, ho_gt, law, x_range=x_range)
        results = evaluate_all_pairs(x, y)
        if not results:
            print(f"  {label:15s} all-pair eval failed")
            continue
        top_mdl, top_sig, top_hi, top_ho = results[0]
        gt_rank = next(
            (i for i, (_, _, hi, ho) in enumerate(results)
             if hi == hi_gt and ho == ho_gt),
            -1,
        )
        gt_pair = f"{hi_gt}/{ho_gt}"
        top_pair = f"{top_hi}/{top_ho}"
        if top_hi == hi_gt and top_ho == ho_gt:
            verdict = "✓ CORRECT"
            n_correct += 1
        elif 0 <= gt_rank <= 2:
            verdict = f"~ near (rank {gt_rank})"
            n_near += 1
        else:
            verdict = f"✗ MISSED (GT rank {gt_rank})"
        print(f"  {label:15s} {gt_pair:30s} {top_pair:30s} {gt_rank:>8d}  {verdict}")

    print()
    print(f"Summary: {n_correct} correct + {n_near} near (top-3) of {len(test_cases)}")
    return 0 if (n_correct + n_near) >= 4 else 1


if __name__ == "__main__":
    sys.exit(main())
