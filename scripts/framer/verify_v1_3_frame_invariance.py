"""GP-152 Spec v1.3 — frame-invariance verification.

Verifies that the v1.3 MDL formula with first-principles BIC coefficient
(Jacobian term = -2·Σ log|h'|) is invariant under monotone scaling of h_out.

This is the falsification test for the v1.3 spec patch. v1.1 and v1.2
both fail this test (residual bias N·log|c| survives); v1.3 should pass
to within ~1 bit per data point across c ∈ {0.1, 0.5, 1, 2, 10}.

Pre-registered acceptance criterion (from spec v1.3 §2.1):
    max |MDL(c) − MDL(1)| < 1.0 bit  for all c in test set,
    on test case A (y = exp(x²)/(1+log x), N=200, σ=0.01, x ∈ [1, 10]).

If this test fails, v1.3 is wrong and we need v1.4 (or escalate to v2.0
first-principles NML / stochastic complexity).

Usage:
    python scripts/verify_v1_3_frame_invariance.py
"""
from __future__ import annotations

import math
import sys
from typing import Callable

import numpy as np

# v1.3 hyperparameters
LOG_J_CLIP_BITS = 10.0          # log-Jacobian clipping bound
SIGMA_NOISE_FLOOR_FACTOR = 0.25  # σ_noise floor multiplier

# Test case A parameters (from spec v1.3 §3.6)
N = 200
SIGMA_NOISE = 0.01
X_RANGE = (1.0, 10.0)
RNG_SEED = 7

# Frame-invariance c sweep
C_VALUES = [0.1, 0.5, 1.0, 2.0, 10.0]

# Acceptance threshold
INVARIANCE_TOLERANCE_BITS = 1.0


def make_test_data(seed: int = RNG_SEED) -> tuple[np.ndarray, np.ndarray]:
    """Test case A: y = exp(x²)/(1 + log x) + Gaussian(0, σ_noise).

    Used as the canary substrate: a known coordinate-transformable invariant.
    """
    rng = np.random.default_rng(seed)
    x = np.linspace(X_RANGE[0], X_RANGE[1], N)
    y_clean = np.exp(x ** 2) / (1.0 + np.log(x))
    noise = rng.normal(0, SIGMA_NOISE * np.maximum(np.abs(y_clean), 1.0), size=N)
    y = y_clean + noise
    return x, y


def lowess_residual_dispersion(x: np.ndarray, y: np.ndarray) -> float:
    """Estimate σ̂²_y' via simple polynomial-residual proxy.

    For frame-invariance verification we don't need full LOWESS — a degree-3
    polynomial regression captures the trend; the residual variance is what
    matters for the test. The actual implementation will use proper LOWESS.
    """
    deg = 3
    # Center-and-scale x for numerical stability
    x_mean = np.mean(x)
    x_std = np.std(x) if np.std(x) > 0 else 1.0
    xn = (x - x_mean) / x_std
    coeffs = np.polyfit(xn, y, deg)
    y_fit = np.polyval(coeffs, xn)
    residuals = y - y_fit
    return float(np.var(residuals))


def jacobian_mean_squared(h_out_prime: Callable, y: np.ndarray) -> float:
    """J̄ := (1/N) Σ |h'(y_i)|² — the mean-square Jacobian factor."""
    j = h_out_prime(y)
    return float(np.mean(j ** 2))


def log_jacobian_clipped(h_out_prime: Callable, y: np.ndarray) -> float:
    """clip( (1/N) Σ log|h'(y_i)|, -LOG_J_CLIP_BITS, +LOG_J_CLIP_BITS )."""
    j = np.abs(h_out_prime(y))
    log_j = np.log(np.clip(j, 1e-30, None))
    mean_log_j = float(np.mean(log_j))
    return float(np.clip(mean_log_j, -LOG_J_CLIP_BITS, LOG_J_CLIP_BITS))


def mdl_v1_1(x: np.ndarray, y: np.ndarray, h_out: Callable, h_out_prime: Callable, k_fn: int) -> float:
    """v1.1 MDL formula (the buggy one) — for reference comparison.

        MDL = N·log(max(σ̂², σ_n²·0.25)) + N·⟨log|h'|⟩ + K·log N
    """
    y_framed = h_out(y)
    sigma_sq = lowess_residual_dispersion(x, y_framed)
    sigma_floor_sq = SIGMA_NOISE * SIGMA_NOISE * SIGMA_NOISE_FLOOR_FACTOR
    log_arg = max(sigma_sq, sigma_floor_sq)
    log_j_unclipped = float(np.mean(np.log(np.clip(np.abs(h_out_prime(y)), 1e-30, None))))
    return N * math.log(log_arg) + N * log_j_unclipped + k_fn * math.log(N)


def mdl_v1_2(x: np.ndarray, y: np.ndarray, h_out: Callable, h_out_prime: Callable, k_fn: int) -> float:
    """v1.2 MDL formula — sigma_noise floor scaled, sign flipped, log-Jacobian clipped.
    Coefficient on Jacobian: -1 (still wrong by factor 2).

        MDL = N·log(max(σ̂², σ_n²·J̄·0.25)) - N·clip(⟨log|h'|⟩) + K·log N
    """
    y_framed = h_out(y)
    sigma_sq = lowess_residual_dispersion(x, y_framed)
    j_bar = jacobian_mean_squared(h_out_prime, y)
    sigma_floor_sq = SIGMA_NOISE * SIGMA_NOISE * j_bar * SIGMA_NOISE_FLOOR_FACTOR
    log_arg = max(sigma_sq, sigma_floor_sq)
    log_j = log_jacobian_clipped(h_out_prime, y)
    return N * math.log(log_arg) - N * log_j + k_fn * math.log(N)


def mdl_v1_3(x: np.ndarray, y: np.ndarray, h_out: Callable, h_out_prime: Callable, k_fn: int) -> float:
    """v1.3 MDL formula — first-principles BIC. Coefficient on Jacobian: -2.

        MDL = N·log(max(σ̂², σ_n²·J̄·0.25)) - 2·N·clip(⟨log|h'|⟩) + K·log N

    Derivation: NLL_framed = (N/2)·log σ̂² + N/2 - Σ log|h'|;
    BIC = 2·NLL + K·log N gives N·log σ̂² - 2·Σ log|h'| + K·log N + const.
    Under h_out → c·h_out: σ̂²·c² contributes +2N·log|c|; Jacobian's
    -2·Σ log|c·h'| contributes -2N·log|c|; cancel.
    """
    y_framed = h_out(y)
    sigma_sq = lowess_residual_dispersion(x, y_framed)
    j_bar = jacobian_mean_squared(h_out_prime, y)
    sigma_floor_sq = SIGMA_NOISE * SIGMA_NOISE * j_bar * SIGMA_NOISE_FLOOR_FACTOR
    log_arg = max(sigma_sq, sigma_floor_sq)
    log_j = log_jacobian_clipped(h_out_prime, y)
    return N * math.log(log_arg) - 2.0 * N * log_j + k_fn * math.log(N)


def make_scaled_h_out(c: float, base_h: Callable | None = None, base_h_prime: Callable | None = None):
    """Returns (h_out, h_out_prime) that scale by factor c on top of the base.

    Default base = identity. Used to test invariance under monotone scaling.
    """
    if base_h is None:
        base_h = lambda y: y
        base_h_prime = lambda y: np.ones_like(y)
    h = lambda y: c * base_h(y)
    h_prime = lambda y: c * base_h_prime(y)
    return h, h_prime


def run_invariance_test(mdl_fn: Callable, label: str) -> dict:
    """Sweep c values; compute MDL drift relative to c=1; report max drift in bits."""
    x, y = make_test_data()
    drifts = {}
    h1, h1_prime = make_scaled_h_out(1.0)
    mdl_ref = mdl_fn(x, y, h1, h1_prime, k_fn=1)
    for c in C_VALUES:
        h, h_prime = make_scaled_h_out(c)
        mdl_c = mdl_fn(x, y, h, h_prime, k_fn=1)
        drift_bits = (mdl_c - mdl_ref) / math.log(2)
        drifts[c] = drift_bits
    max_abs_drift = max(abs(d) for d in drifts.values())
    passed = max_abs_drift < INVARIANCE_TOLERANCE_BITS
    return {
        "label": label,
        "drifts_bits": drifts,
        "max_abs_drift_bits": max_abs_drift,
        "tolerance_bits": INVARIANCE_TOLERANCE_BITS,
        "passed": passed,
    }


def main() -> int:
    print("=" * 70)
    print("GP-152 Spec v1.3 — Frame-Invariance Verification")
    print("=" * 70)
    print(f"Test case A: y = exp(x²)/(1 + log x), N={N}, σ={SIGMA_NOISE}")
    print(f"Scaling sweep: c ∈ {C_VALUES}")
    print(f"Acceptance threshold: max drift < {INVARIANCE_TOLERANCE_BITS} bit")
    print()

    results = []
    for fn, label in [(mdl_v1_1, "v1.1 (Jacobian sign error, floor in raw units)"),
                       (mdl_v1_2, "v1.2 (sign flipped, floor scaled, coef -1)"),
                       (mdl_v1_3, "v1.3 (first-principles BIC, coef -2)")]:
        r = run_invariance_test(fn, label)
        results.append(r)
        print(f"--- {label} ---")
        for c, d in r["drifts_bits"].items():
            print(f"  c={c:>5.2f}   ΔMDL = {d:+.3f} bits")
        verdict = "PASS" if r["passed"] else "FAIL"
        print(f"  max |drift| = {r['max_abs_drift_bits']:.3f} bits  → {verdict}")
        print()

    v1_3 = results[-1]
    if v1_3["passed"]:
        print("✅ v1.3 frame-invariance: PASSED")
        print("   First-principles BIC coefficient (-2) confirmed mathematically correct.")
        print("   Spec v1.3 ready for implementation.")
        return 0
    else:
        print("❌ v1.3 frame-invariance: FAILED")
        print("   The first-principles derivation is also leaking. Either:")
        print("   (a) the LOWESS residual estimator has a c-dependent bias,")
        print("   (b) the σ_noise floor logic introduces a discontinuity that breaks invariance,")
        print("   (c) the formula needs additional terms (e.g., heteroscedasticity correction).")
        print("   Escalate to v2.0 (NML / stochastic complexity / pre-quantized coding).")
        return 1


if __name__ == "__main__":
    sys.exit(main())
