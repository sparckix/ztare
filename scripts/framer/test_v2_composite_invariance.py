"""test_v2_composite_invariance.py — v2.0 frame-invariance under composite transforms.

Tests that MDL_v2 is invariant under h_out → φ ∘ h_out for various monotone φ:
  - Linear: φ(y) = c·y + b
  - Power: φ(y) = sign(y)·|y|^p, p > 0
  - Exponential / log squash
  - Reciprocal

If v2.0 is truly raw-coords, none of these should change MDL by more than the
K_hout penalty (≈ log N ≈ 5.3 bits).
"""
import math
import sys
from pathlib import Path

import numpy as np

# Local sibling import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest_framer_mdl_v2_vs_v1 import (
    make_test_data,
    compute_v2_mdl,
    h_identity,
)

N = 200


def composite_test(label, phi, phi_inv, deg=5):
    x, y = make_test_data()
    h_in = lambda xx: xx
    h_b, h_b_inv, _ = h_identity()
    mdl_baseline, _ = compute_v2_mdl(
        x, y, h_in, h_b, h_b_inv, k_law=deg + 1, k_hin=0, k_hout=0, deg=deg
    )
    mdl_composite, _ = compute_v2_mdl(
        x, y, h_in, phi, phi_inv, k_law=deg + 1, k_hin=0, k_hout=1, deg=deg
    )
    drift_bits = (mdl_composite - mdl_baseline) / math.log(2)
    verdict = "PASS" if abs(drift_bits) < 5 else "INVESTIGATE"
    print(f"  {label:50s} ΔMDL = {drift_bits:+.4f} bits   ({verdict})")


def main() -> int:
    print("v2.0 composite-transform invariance:")
    print("  expectation: ΔMDL ≈ 0 (with K_hout penalty difference of +log N ≈ 5.3 bits)")
    print()

    composite_test(
        "scale_2_shift_1: y → 2y+1",
        lambda y: 2 * y + 1,
        lambda yp: (yp - 1) / 2,
    )
    composite_test(
        "power_0_5: y → sign(y)·sqrt(|y|)",
        lambda y: np.sign(y) * np.sqrt(np.abs(y) + 1e-30),
        lambda yp: np.sign(yp) * yp ** 2,
    )
    composite_test(
        "power_2: y → y²",
        lambda y: y ** 2,
        lambda yp: np.sqrt(np.abs(yp) + 1e-30),
    )
    composite_test(
        "log_squash: y → log(|y|+1)",
        lambda y: np.log(np.abs(y) + 1),
        lambda yp: np.exp(yp) - 1,
    )
    composite_test(
        "reciprocal_shifted: y → 1/(y+1)",
        lambda y: 1.0 / (y + 1),
        lambda yp: 1.0 / yp - 1,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
