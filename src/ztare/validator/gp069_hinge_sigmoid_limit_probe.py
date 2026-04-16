"""GP-069 level-1.5 audit probe — hinge vs sigmoid-limit approximation.

Standalone numerical check (no LLM calls, no autoresearch_loop).

**Question.** Under L2 residual on a finite evidence grid, can a smooth
sigmoid-based wrapper be driven close enough to a hinge GT that the fit
primitive cannot distinguish them? If yes, the hinge sandbox fails GP-069
level-1.5 (sigmoid-limit collapse), and a naive hinge pre-registration is
unsafe.

**Protocol.**
  1. Seal a hinge GT:  y = a·(|x−x₀| + (x−x₀))/2 + b  (= a·max(0, x−x₀) + b)
  2. Sample on a uniform grid straddling x₀ with additive Gaussian noise.
  3. Fit two models to the same samples:
       (H)  the true hinge form (same family as GT)
       (S)  a sigmoid-approximation  a·σ((x−x₀)/τ)·(x−x₀) + b
     where σ(z) = 1/(1 + exp(−z)).
  4. Compare residuals. If S's best residual ≈ H's best residual, the
     fit primitive cannot discriminate under L2 on this grid — the
     sigmoid family is a viable competitor and the level-1.5 risk is real.

**Interpretation.** This probe does NOT exercise the ZTARE validator's
actual fit primitive — it uses scipy.optimize directly with both closed
forms. If even this direct-optimization setting shows indistinguishability,
the validator (which uses the same scipy backend) will be no harder to
fool. If this probe shows a clear separation, the validator-level risk
drops but is not eliminated (the validator's multistart and scoring
policy could still matter).

Run:
    python3 -m src.ztare.validator.gp069_hinge_sigmoid_limit_probe

Canonical result (2026-04-15, before first run) will be written to
research_areas/private/seams/GP-069_nesting_cleared_target_construction_seam.md
§ sigmoid-limit audit.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares


# ---------- GT and model forms ----------

def hinge_gt(x: np.ndarray, a: float, x0: float, b: float) -> np.ndarray:
    """Sealed GT — piecewise-linear hinge via the fabs identity."""
    return a * (np.abs(x - x0) + (x - x0)) / 2.0 + b


def sigmoid_model(x: np.ndarray, a: float, x0: float, b: float, tau: float) -> np.ndarray:
    """Smooth sigmoid approximation of the hinge.

    For small tau, approaches hinge at all x ≠ x0.
    """
    z = (x - x0) / tau
    # Stable sigmoid
    sig = np.where(z >= 0, 1.0 / (1.0 + np.exp(-z)), np.exp(z) / (1.0 + np.exp(z)))
    return a * sig * (x - x0) + b


# ---------- Fit harness ----------

@dataclass
class FitResult:
    params: dict
    residual_l2: float
    residual_max: float


def fit_hinge(x: np.ndarray, y: np.ndarray) -> FitResult:
    def resid(p):
        a, x0, b = p
        return hinge_gt(x, a, x0, b) - y

    best = None
    for a0 in (0.5, 1.0, 2.0):
        for x0_0 in np.linspace(x.min() + 0.1, x.max() - 0.1, 5):
            for b0 in (0.0, y.mean()):
                try:
                    r = least_squares(resid, x0=[a0, x0_0, b0], method="lm")
                except Exception:
                    continue
                if best is None or r.cost < best.cost:
                    best = r
    a, x0, b = best.x
    r = resid(best.x)
    return FitResult(
        params={"a": float(a), "x0": float(x0), "b": float(b)},
        residual_l2=float(math.sqrt(np.sum(r * r))),
        residual_max=float(np.max(np.abs(r))),
    )


def fit_sigmoid(x: np.ndarray, y: np.ndarray, tau_floor: float) -> FitResult:
    """Fit the sigmoid approximation, allowing tau ≥ tau_floor.

    tau_floor models the practical lower bound on tau that the ZTARE fit
    primitive would reach — either because of parameter bounds or numerical
    precision. Pass tau_floor very small (e.g. 1e-6) to probe the idealized
    limit; pass tau_floor ≈ grid_spacing/10 to probe a realistic lower bound.
    """

    def resid(p):
        a, x0, b, log_tau = p
        tau = math.exp(log_tau)
        if tau < tau_floor:
            tau = tau_floor
        return sigmoid_model(x, a, x0, b, tau) - y

    best = None
    for a0 in (0.5, 1.0, 2.0):
        for x0_0 in np.linspace(x.min() + 0.1, x.max() - 0.1, 5):
            for log_tau_0 in (math.log(0.01), math.log(0.1), math.log(1.0)):
                try:
                    r = least_squares(
                        resid, x0=[a0, x0_0, y.mean(), log_tau_0], method="lm"
                    )
                except Exception:
                    continue
                if best is None or r.cost < best.cost:
                    best = r
    a, x0, b, log_tau = best.x
    tau = max(math.exp(log_tau), tau_floor)
    r = resid(best.x)
    return FitResult(
        params={
            "a": float(a),
            "x0": float(x0),
            "b": float(b),
            "tau": float(tau),
        },
        residual_l2=float(math.sqrt(np.sum(r * r))),
        residual_max=float(np.max(np.abs(r))),
    )


# ---------- Experiment ----------

def run_probe(
    *,
    a_true: float = 2.0,
    x0_true: float = 0.37,
    b_true: float = 0.5,
    n_per_side: int = 15,
    noise_sigma: float = 0.02,
    seed: int = 20260415,
) -> None:
    rng = np.random.default_rng(seed)
    x = np.linspace(-1.0, 1.0, 2 * n_per_side)
    y_clean = hinge_gt(x, a_true, x0_true, b_true)
    y = y_clean + rng.normal(0.0, noise_sigma, size=x.shape)

    grid_spacing = float(np.mean(np.diff(x)))
    print(f"[GP-069 hinge probe] n={len(x)}, grid_spacing={grid_spacing:.4f}, "
          f"noise_sigma={noise_sigma}")
    print(f"  GT: y = {a_true}·max(0, x−{x0_true}) + {b_true}")

    fit_h = fit_hinge(x, y)
    print(f"\n[H] hinge fit")
    print(f"  params = {fit_h.params}")
    print(f"  L2 residual = {fit_h.residual_l2:.6f}")
    print(f"  max |residual| = {fit_h.residual_max:.6f}")

    for tau_floor, label in [
        (1e-6, "idealized (tau_floor=1e-6)"),
        (grid_spacing / 10.0, f"tau_floor=grid/10={grid_spacing/10.0:.4f}"),
        (grid_spacing / 2.0, f"tau_floor=grid/2={grid_spacing/2.0:.4f}"),
        (grid_spacing, f"tau_floor=grid={grid_spacing:.4f}"),
    ]:
        fit_s = fit_sigmoid(x, y, tau_floor=tau_floor)
        delta = fit_s.residual_l2 - fit_h.residual_l2
        print(f"\n[S] sigmoid fit — {label}")
        print(f"  params = {fit_s.params}")
        print(f"  L2 residual = {fit_s.residual_l2:.6f}")
        print(f"  max |residual| = {fit_s.residual_max:.6f}")
        print(f"  delta vs hinge = {delta:+.6f} "
              f"({'indistinguishable' if abs(delta) < noise_sigma else 'distinguishable'})")

    # Noise-free grid: isolate model-vs-model gap without noise confound.
    print("\n--- noise-free repeat (samples = GT exactly) ---")
    y_nf = y_clean
    fit_h_nf = fit_hinge(x, y_nf)
    print(f"[H] noise-free L2 residual = {fit_h_nf.residual_l2:.2e}")
    for tau_floor, label in [
        (1e-6, "idealized"),
        (grid_spacing / 10.0, "grid/10"),
        (grid_spacing, "grid"),
    ]:
        fit_s_nf = fit_sigmoid(x, y_nf, tau_floor=tau_floor)
        print(f"[S] noise-free {label}: L2 = {fit_s_nf.residual_l2:.2e}, "
              f"tau = {fit_s_nf.params['tau']:.2e}")


def bic(residual_l2: float, n: int, k: int) -> float:
    """BIC under Gaussian residuals: n·ln(SSE/n) + k·ln(n)."""
    sse = residual_l2 * residual_l2
    if sse <= 0:
        sse = 1e-300
    return n * math.log(sse / n) + k * math.log(n)


def aic(residual_l2: float, n: int, k: int) -> float:
    sse = residual_l2 * residual_l2
    if sse <= 0:
        sse = 1e-300
    return n * math.log(sse / n) + 2.0 * k


def run_probe_with_complexity_penalty(
    *,
    a_true: float = 2.0,
    x0_true: float = 0.37,
    b_true: float = 0.5,
    n_per_side: int = 15,
    noise_sigma: float = 0.02,
    seed: int = 20260415,
) -> None:
    """Repeat the probe but compare under BIC and AIC instead of raw L2.

    Hinge has 3 parameters (a, x0, b). Sigmoid has 4 (a, x0, b, tau).
    BIC/AIC penalize sigmoid for the extra τ parameter. If the hinge BIC
    beats the sigmoid BIC, the complexity-penalty defense is sufficient
    and the "structural limit" framing of the raw-L2 probe is a straw man
    against unregularized scoring.
    """
    rng = np.random.default_rng(seed)
    x = np.linspace(-1.0, 1.0, 2 * n_per_side)
    y_clean = hinge_gt(x, a_true, x0_true, b_true)
    y = y_clean + rng.normal(0.0, noise_sigma, size=x.shape)
    n = len(x)

    fit_h = fit_hinge(x, y)
    fit_s = fit_sigmoid(x, y, tau_floor=1e-6)

    k_h = 3  # a, x0, b
    k_s = 4  # a, x0, b, tau

    bic_h = bic(fit_h.residual_l2, n, k_h)
    bic_s = bic(fit_s.residual_l2, n, k_s)
    aic_h = aic(fit_h.residual_l2, n, k_h)
    aic_s = aic(fit_s.residual_l2, n, k_s)

    print("\n==== complexity-penalty re-audit ====")
    print(f"n = {n}, noise_sigma = {noise_sigma}")
    print(f"hinge:   L2 = {fit_h.residual_l2:.6f}  k={k_h}  BIC = {bic_h:+.4f}  AIC = {aic_h:+.4f}")
    print(f"sigmoid: L2 = {fit_s.residual_l2:.6f}  k={k_s}  BIC = {bic_s:+.4f}  AIC = {aic_s:+.4f}")
    print(f"Delta BIC (hinge − sigmoid) = {bic_h - bic_s:+.4f}  "
          f"({'hinge preferred' if bic_h < bic_s else 'sigmoid preferred'})")
    print(f"Delta AIC (hinge − sigmoid) = {aic_h - aic_s:+.4f}  "
          f"({'hinge preferred' if aic_h < aic_s else 'sigmoid preferred'})")
    print("\nReading: if BIC/AIC prefer hinge, the 'scorer structural limit' "
          "claim is a straw man against unregularized L2, and the fix is a "
          "complexity penalty on the ZTARE fit primitive — not a paper.")


if __name__ == "__main__":
    run_probe()
    run_probe_with_complexity_penalty()
