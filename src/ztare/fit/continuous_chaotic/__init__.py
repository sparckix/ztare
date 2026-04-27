"""Continuous-chaotic substrate solver (kernel-promoted from v5-correct).

Promoted 2026-04-24 from projects/lorenz_bridge_test/apparatus_candidate/
apparatus_v5_correct.py (score-87 champion lineage under gp140
aggressive-judge run-2).

Substrate class: `continuous_chaotic_polynomial_ode` — 3-D dissipative
chaotic flow with polynomial vector field (Lorenz-class, Rössler-class,
bespoke perturbations).

Pipeline:
  Method A: autocorrelation-radius multi-grid weak-form SINDy
     - autocorrelation decorrelation time τ_decorr from C(Δt) 1/e crossing
     - support radii log-grid around τ_decorr
     - polynomial bump test functions, integration-by-parts residuals
     - STLSQ sparse solve per state dimension
  Method B: Lyapunov-ergodic + Wasserstein-persistence law certification
     - Σλᵢ < 0 dissipativity
     - |λ_zero| ≤ ε continuous-flow-invariant
     - W₁(PD_cand, PD_obs) ≤ threshold (calibrated floor or Fasy bound)

Kernel placement per GP-143 seam. Invoked by autoresearch_loop.py when
rubric declares `fit_score_mode: "dynamical_lattice"`.

Public API:
  - run_pipeline(trajectory, dt, rubric_params, initial_state) -> result dict
  - autocorrelation_decorrelation_time(trajectory, dt) -> float
  - persistence_diagram_of_trajectory(trajectory) -> dict[H0, H1]

Sub-modules (for operator-side inspection or extension):
  - .generator: Method A weak-form SINDy
  - .certifier: Method B gate composition
  - .autocorrelation: τ_decorr extraction
  - .lyapunov: spectrum + ergodic check
"""
from __future__ import annotations

SUBSTRATE_CLASS = "continuous_chaotic_polynomial_ode"
KERNEL_PROMOTION_DATE = "2026-04-24"
KERNEL_PROMOTION_SOURCE = "projects/lorenz_bridge_test/apparatus_candidate/apparatus_v5_correct.py"
KERNEL_PROMOTION_CHAMPION = "gp140 iter-10 CW-PT thesis (score 87 under o3 aggressive judge, 2026-04-24)"

# Method A variant registry. Extend when new Method A variants are added.
METHOD_A_VARIANTS = {
    "weak_form_sindy_auto_radii": "continuous_chaotic.generator:run_weak_form",
    # Future: chebyshev_weak_form (tracked for implementation when CW-PT
    # specifically is ported rather than the generic weak-form base).
}

# Method C variant registry — heavy-tail / fractional-operator family
# (gp150-derived, 2026-04-24). Distinct from Methods A/B because the governing
# equation contains a non-integer spatial derivative, so the underlying
# discriminator is divergence of the fourth (or q>α) spatial moment rather
# than a polynomial weak-form residual or Lyapunov dissipativity gate.
# Autoresearch_loop dispatches the diagnostic at the post-champion hook when
# rubric declares enable_fom=true. Live kernel wiring gated by
# fom_gate_stack_validated flag (requires G1 full + GP-146 pass).
METHOD_C_VARIANTS = {
    "heavy_tail_fractional_laplacian": "continuous_chaotic.fractional_operator:compute_fractional_derivative",
    # Future: heavy_tail_subordinator (full ρ_α density wrap with log-grid
    # tail compensation — implements the gp150 71-thesis module spec).
}


def run_pipeline(
    trajectory,
    dt: float,
    rubric_params: dict,
    initial_state=None,
):
    """Run the continuous-chaotic pipeline end-to-end.

    Delegates to the sub-modules. Provided as a stable kernel entry point
    so autoresearch_loop can import just `from src.ztare.fit.continuous_chaotic
    import run_pipeline` and never touch sub-module internals.
    """
    from .generator import run_weak_form_pipeline
    return run_weak_form_pipeline(
        trajectory=trajectory,
        dt=dt,
        rubric_params=rubric_params,
        initial_state=initial_state,
    )
