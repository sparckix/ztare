"""Lyapunov spectrum + ergodic-divergence utilities for continuous-chaotic
substrates.

Ported from projects/lorenz_bridge_test/apparatus_candidate/apparatus_v3_combined.py
and apparatus_v5_ergodic.py during GP-143 kernel promotion (2026-04-24).

Key entry points:
  lyapunov_spectrum_approx(C, trajectory, dt) -> sorted-desc list of exponents
  kaplan_yorke_dimension(lyap_spectrum) -> float
  ergodic_divergence_filter(C, trajectory, dt) -> dict with pass/fail
"""
from __future__ import annotations

import numpy as np


# Method B / ergodic filter thresholds
ERGODIC_MARGIN = 0.01         # sum(lambda_i) < -ERGODIC_MARGIN for dissipative
FLOW_INVARIANT_EPS = 0.10     # min_i |lambda_i| <= FLOW_INVARIANT_EPS


def _rhs_degree2_3d(state: np.ndarray, C: np.ndarray) -> np.ndarray:
    """Compute RHS of a 3D degree-2 polynomial ODE with basis
    [1, x, y, z, x*x, x*y, x*z, y*y, y*z, z*z].
    C has shape (3, 10).
    """
    x, y, z = state
    basis = np.array([1.0, x, y, z, x * x, x * y, x * z, y * y, y * z, z * z])
    return C @ basis


def _jacobian_rhs_degree2_3d(state: np.ndarray, C: np.ndarray) -> np.ndarray:
    """Analytic Jacobian of the degree-2 3D polynomial RHS."""
    x, y, z = state
    dbasis_dx = np.array([0, 1, 0, 0, 2 * x, y, z, 0, 0, 0])
    dbasis_dy = np.array([0, 0, 1, 0, 0, x, 0, 2 * y, z, 0])
    dbasis_dz = np.array([0, 0, 0, 1, 0, 0, x, 0, y, 2 * z])
    return np.column_stack([C @ dbasis_dx, C @ dbasis_dy, C @ dbasis_dz])


def lyapunov_spectrum_approx(
    C: np.ndarray, trajectory: np.ndarray, dt: float, n_iter: int = 500
) -> list[float]:
    """Approximate Lyapunov spectrum via QR decomposition of evolved
    variational equations along the observed trajectory.
    """
    n_steps = min(n_iter, len(trajectory) - 1)
    Q = np.eye(3)
    log_r_sum = np.zeros(3)
    for i in range(n_steps):
        state = trajectory[i]
        J = _jacobian_rhs_degree2_3d(state, C)
        M = np.eye(3) + dt * J
        new_Q = M @ Q
        Q_new, R_new = np.linalg.qr(new_Q)
        diag_r = np.diag(R_new)
        log_r_sum += np.log(np.abs(diag_r) + 1e-30)
        Q = Q_new
    total_time = n_steps * dt
    if total_time <= 0:
        return [0.0, 0.0, 0.0]
    return sorted((log_r_sum / total_time).tolist(), reverse=True)


def kaplan_yorke_dimension(lyap: list[float]) -> float:
    """Kaplan-Yorke fractal dimension from sorted Lyapunov exponents."""
    cum = 0.0
    j = 0
    for i, l in enumerate(lyap):
        if cum + l < 0:
            if i == 0:
                return 0.0
            j = i - 1
            break
        cum += l
        j = i
    if j >= len(lyap) - 1:
        return float(len(lyap))
    sum_pos = sum(lyap[: j + 1])
    if lyap[j + 1] == 0:
        return float(j + 1)
    return (j + 1) + sum_pos / abs(lyap[j + 1])


def ergodic_divergence_filter(
    C: np.ndarray, trajectory: np.ndarray, dt: float, n_iter: int = 500
) -> dict:
    """Two LATTICE-LE filters composed:
      1. sum(lambda_i) < -ERGODIC_MARGIN (ergodic dissipativity)
      2. min_i |lambda_i| <= FLOW_INVARIANT_EPS (continuous flow invariant)
    Both must pass for law-certification.
    """
    lyap = lyapunov_spectrum_approx(C, trajectory, dt, n_iter=n_iter)
    lam_sum = float(sum(lyap))
    lam_zero_magnitude = float(min(abs(l) for l in lyap))
    ergodic_dissipative = lam_sum < -ERGODIC_MARGIN
    flow_invariant = lam_zero_magnitude <= FLOW_INVARIANT_EPS
    return {
        "lyapunov_spectrum": lyap,
        "lyap_sum": lam_sum,
        "lyap_zero_magnitude": lam_zero_magnitude,
        "ergodic_dissipative": bool(ergodic_dissipative),
        "flow_invariant": bool(flow_invariant),
        "both_pass": bool(ergodic_dissipative and flow_invariant),
        "kaplan_yorke_dim": kaplan_yorke_dimension(lyap),
    }
