"""test_v2_pathological.py — does v2.0 correctly auto-disable on bad data?

Munger inversion: how would v2.0 fail catastrophically? Inject pathological
data and verify the canary, scope guards, and auto-disable mechanisms catch
it (or that v2.0 still produces a finite, sensible MDL).

Pathologies tested:
  1. Zero-residual collapse: y = exact_law(x), no noise → σ̂² → 0.
  2. Heteroscedastic: σ(y) ∝ |y|.
  3. Multi-modal: y from two stitched laws.
  4. Reciprocal near zero: y small, h_out=reciprocal blows up.
  5. Low precision: y quantized to 4 bits.
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest_framer_mdl_v2_vs_v1 import compute_v2_mdl


N = 200
RNG = np.random.default_rng(7)


def report(label, mdl, sigma_sq, expected_behavior, flags=None):
    print(f"  {label}")
    print(f"    MDL_v2 = {mdl:.2f}, σ̂²_raw = {sigma_sq:.4e}")
    print(f"    Expected: {expected_behavior}")
    if flags:
        for k, v in flags.items():
            print(f"    {k}: {v}")
    if math.isinf(mdl) or math.isnan(mdl):
        print("    ⚠️  MDL is inf/nan — v2.0 needs a σ̂² floor for zero-residual case!")
    print()


def main() -> int:
    x = np.linspace(1, 10, N)

    print("=== Pathology 1: Zero-residual collapse ===")
    y_clean = x ** 2
    mdl, sig = compute_v2_mdl(
        x, y_clean, lambda x_: x_, lambda y: y, lambda y: y,
        k_law=4, k_hin=0, k_hout=0, deg=3,
    )
    report(
        "identity-identity on noiseless y=x²",
        mdl, sig,
        "σ̂² near machine epsilon; MDL very negative; OK as long as not -inf",
    )

    print("=== Pathology 2: Heteroscedastic noise (would-be auto-disable) ===")
    y_bumpy = x ** 2 + RNG.normal(0, 0.01 * np.abs(x ** 2), size=N)
    mdl, sig = compute_v2_mdl(
        x, y_bumpy, lambda x_: x_, lambda y: y, lambda y: y,
        k_law=4, k_hin=0, k_hout=0, deg=3,
    )
    xn = (x - x.mean()) / (x.std() or 1.0)
    fit_resid = y_bumpy - np.polyval(np.polyfit(xn, y_bumpy, 3), xn)
    abs_resid = np.abs(fit_resid)
    r = float(np.corrcoef(abs_resid, np.abs(y_bumpy))[0, 1])
    report(
        f"heteroscedastic σ ∝ |y|; |corr(|resid|, |y|)| = {r:.3f}",
        mdl, sig,
        "corr should be > 0.3 → auto-disable triggers at runtime",
    )

    print("=== Pathology 3: Multi-modal data (two laws stitched) ===")
    y_a = x[: N // 2] ** 2
    y_b = -x[N // 2 :] ** 2 + 100
    y_multi = np.concatenate([y_a, y_b]) + RNG.normal(0, 0.1, size=N)
    mdl, sig = compute_v2_mdl(
        x, y_multi, lambda x_: x_, lambda y: y, lambda y: y,
        k_law=4, k_hin=0, k_hout=0, deg=3,
    )
    report(
        "multi-modal y (two distinct laws stitched)",
        mdl, sig,
        "σ̂²_raw will be huge; MDL gain over baseline ≈ 0 → G-LIB-COVER catches",
    )

    print("=== Pathology 4: Reciprocal near zero ===")
    x_small = np.linspace(0.001, 0.01, N)
    y_recip = 1.0 / x_small + RNG.normal(0, 0.1, size=N)
    ho = lambda y: 1.0 / np.where(np.abs(y) < 1e-30, 1e-30, y)
    ho_inv = ho
    try:
        mdl, sig = compute_v2_mdl(
            x_small, y_recip, lambda x_: x_, ho, ho_inv,
            k_law=4, k_hin=0, k_hout=0, deg=3,
        )
        report(
            "reciprocal h_out on y ∈ [100, 1000]",
            mdl, sig,
            "should compute fine; framing inverts the original 1/x relationship",
        )
    except Exception as exc:
        print(f"  EXCEPTION: {type(exc).__name__}: {exc}")

    print("=== Pathology 5: 4-bit quantization (would-be auto-disable) ===")
    y_clean5 = x ** 2 / 100
    y_quant = np.round(y_clean5 * 16) / 16
    unique_count = int(len(np.unique(y_quant)))
    mdl, sig = compute_v2_mdl(
        x, y_quant, lambda x_: x_, lambda y: y, lambda y: y,
        k_law=4, k_hin=0, k_hout=0, deg=3,
    )
    report(
        f"y quantized to 4 bits ({unique_count} unique values)",
        mdl, sig,
        "σ̂²_raw equals quantization variance; auto-disable should trigger at runtime",
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
