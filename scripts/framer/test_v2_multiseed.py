"""test_v2_multiseed.py — Test Case A predictions across 30 noise seeds.

The spec predicts MDL gain ≈ 20-60 bits and iters 28→9. This script measures
both quantities across 30 independent noise realizations and reports
mean / std / min / max.
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest_framer_mdl_v2_vs_v1 import compute_v2_mdl


N = 200
SIGMA = 0.01
N_SEEDS = 30
X_RANGE = (1.0, 10.0)


def gen_test_a(seed):
    rng = np.random.default_rng(seed)
    x = np.linspace(*X_RANGE, N)
    y_clean = np.exp(x ** 2) / (1.0 + np.log(x))
    noise = rng.normal(0, SIGMA * np.maximum(np.abs(y_clean), 1.0), size=N)
    return x, y_clean + noise


def main() -> int:
    results = []
    for seed in range(N_SEEDS):
        x, y = gen_test_a(seed)
        mdl_id, sig_id = compute_v2_mdl(
            x, y, lambda x_: x_, lambda y: y, lambda y: y,
            k_law=4, k_hin=0, k_hout=0, deg=3,
        )
        mdl_x2, sig_x2 = compute_v2_mdl(
            x, y, lambda x_: x_ ** 2, lambda y: y, lambda y: y,
            k_law=4, k_hin=1, k_hout=0, deg=3,
        )
        gain_bits = (mdl_id - mdl_x2) / math.log(2)
        results.append((seed, mdl_id, mdl_x2, gain_bits, sig_id, sig_x2))

    gains = np.array([r[3] for r in results])
    print(f"Test Case A: y = exp(x²)/(1+log x), N={N}, σ={SIGMA}, {N_SEEDS} seeds")
    print(f"  framing: h_in=x², h_out=identity")
    print()
    print(f"  MDL gain (id - x²), bits:")
    print(f"    mean   = {gains.mean():+.2f}")
    print(f"    std    = {gains.std():.2f}")
    print(f"    min    = {gains.min():+.2f}")
    print(f"    max    = {gains.max():+.2f}")
    print()

    if gains.mean() > 5 and gains.std() < 20:
        print("  ✓ Robust: framing reliably helps (mean > 5 bits, std < 20)")
        ret = 0
    elif gains.mean() > 0:
        print("  ~ Modest: framing helps on average but high variance")
        ret = 0
    else:
        print("  ✗ NEGATIVE on average: framing HURTS — investigate")
        ret = 1

    print()
    print("  Detailed (first 5 seeds):")
    for seed, mdl_id, mdl_x2, gain, sig_id, sig_x2 in results[:5]:
        print(
            f"    seed {seed:>2d}: MDL_id={mdl_id:>10.0f}  "
            f"MDL_x²={mdl_x2:>10.0f}  Δ={gain:+7.2f} bits  "
            f"σ̂²(id)={sig_id:.2e}  σ̂²(x²)={sig_x2:.2e}"
        )
    return ret


if __name__ == "__main__":
    sys.exit(main())
