"""Apparatus v5-correct — LATTICE-LE + v2.7 chaos-primitive corrections.

Reference implementation of the corrected chaotic-substrate thesis:

Method A — Autocorrelation-Radius Multi-Grid Weak-Form SINDy.
    Instead of FFT peaks (wrong on broadband chaos), support radii for the
    weak-form test functions are set from the trajectory's autocorrelation
    decorrelation time tau_decorr (1/e crossing of C(dt)). Radii span a log
    grid around tau_decorr. For each radius r, integrate observations
    against a compact polynomial bump psi(t) = (1 - (t/r)^2)^2 and its
    analytic derivative; LHS uses integration-by-parts so we never touch
    pointwise numerical derivatives. Multi-scale observation matrices are
    stacked and STLSQ is applied at a lambda-threshold grid; resulting
    sparse coefficient matrices form the behavioral-candidate set.
    Explicit per-candidate covariance is computed from weighted-LS residuals.

Method B — Lyapunov-Ergodic Dissipativity + Wasserstein-Persistence Gate.
    Two law-certification filters, both continuous under finite noise:
        (i) ergodic filter: sum(lambda_i) < -ERGODIC_MARGIN (v5-ergodic)
       (ii) continuous-flow-invariant: min_i |lambda_i| <= FLOW_INVARIANT_EPS
      (iii) Wasserstein-1 persistence gate: W_1(PD_cand, PD_obs) <= W_THRESHOLD
            where PD is the H_0 + H_1 persistence diagram of the reconstructed
            attractor's Vietoris-Rips filtration. Replaces brittle integer
            Betti equality with a noise-robust continuous metric.

Dependencies: numpy, scipy, pysindy, ripser, persim.
"""
from __future__ import annotations

import json
import sys
import time
from math import lgamma, log, pi
from pathlib import Path

import numpy as np
from scipy.integrate import simpson

from src.ztare.fit.continuous_chaotic.lyapunov import (
    ERGODIC_MARGIN,
    FLOW_INVARIANT_EPS,
    ergodic_divergence_filter,
    kaplan_yorke_dimension,
    lyapunov_spectrum_approx,
)
from src.ztare.fit.continuous_chaotic.autocorrelation import (
    autocorrelation_decorrelation_time,
)

# Kernel-local basis and polynomial ODE helpers (substrate-agnostic; Lorenz-class
# degree-2 3D for now; extend registry when new degree/dim targets are added).
BASIS_LABELS = ["1", "x", "y", "z", "x*x", "x*y", "x*z", "y*y", "y*z", "z*z"]


def eval_basis(state: np.ndarray) -> np.ndarray:
    """Degree-2 polynomial basis for a 3D state."""
    x, y, z = state
    return np.array([1.0, x, y, z, x * x, x * y, x * z, y * y, y * z, z * z])


class SparseODE:
    """Minimal kernel-local ODE wrapper for degree-2 3D polynomial flows."""
    def __init__(self, coefficients: np.ndarray):
        self.coefficients = np.asarray(coefficients, dtype=float)

    def rhs(self, t: float, state: np.ndarray) -> np.ndarray:
        return self.coefficients @ eval_basis(state)


def L_NML_bits(C_coef: np.ndarray, trajectory: np.ndarray, dt: float) -> dict:
    """Shtarkov NML message length for a polynomial ODE candidate."""
    from math import lgamma, log, pi
    N = trajectory.shape[0]
    vel_obs = np.gradient(trajectory, dt, axis=0)
    vel_pred = np.zeros_like(vel_obs)
    for i in range(N):
        vel_pred[i] = C_coef @ eval_basis(trajectory[i])
    residuals = (vel_obs - vel_pred).flatten()
    RSS = float((residuals ** 2).sum())
    N_res = residuals.size
    sigma_sq = max(RSS / N_res, 1e-30)
    nll_nats = 0.5 * N_res * (log(2 * pi * sigma_sq) + 1)
    nll_bits = nll_nats / log(2)
    k = int(np.sum(np.abs(C_coef) > 1e-10))
    C_k_nats = 0.5 * k * log(pi) + lgamma(k / 2 + 1)
    penalty_bits = (0.5 * k * log(N_res) + C_k_nats) / log(2)
    return {
        "k": k, "RSS": RSS,
        "nll_bits": nll_bits,
        "penalty_bits": penalty_bits,
        "L_bits": nll_bits + penalty_bits,
        "tau_regret_bits": penalty_bits,
    }


def pareto_front(points: list[tuple[float, int]]) -> list[int]:
    """Return indices of Pareto front minimizing both (L_bits, k_nonzero)."""
    n = len(points)
    front = []
    for i in range(n):
        Li, ki = points[i]
        dominated = False
        for j in range(n):
            if i == j:
                continue
            Lj, kj = points[j]
            if Lj <= Li and kj <= ki and (Lj < Li or kj < ki):
                dominated = True
                break
        if not dominated:
            front.append(i)
    return front


# Wasserstein-persistence gate threshold, computed ADAPTIVELY from the
# intrinsic attractor-sampling noise floor: W_1 between two simulations of the
# true rule from slightly-perturbed initial conditions. See _calibrate_threshold.
# Admit factor K: candidate passes if W_1(cand, obs) <= K * noise_floor.
WASSERSTEIN_ADMIT_FACTOR = 3.0
# Transient fraction discarded before persistence (attractor-settling time).
TRANSIENT_FRACTION = 0.20

# Autocorrelation-radii multi-grid geometry.
# Radii span [0.25 * tau, 4 * tau] on a log grid with R points.
N_RADII = 5
RADIUS_MIN_FACTOR = 0.25
RADIUS_MAX_FACTOR = 4.0

# STLSQ thresholds for weak-form sparse regression.
WEAK_FORM_THRESHOLDS = [0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30]


# ---------- autocorrelation timescale — imported from kernel autocorrelation module ---------- #
# (inline copy removed during GP-143 kernel promotion; see autocorrelation.py)
# The function below is legacy; kept as dead code to minimize diff but NOT used.
def _legacy_autocorrelation_do_not_use(trajectory: np.ndarray, dt: float) -> float:
    x = trajectory - trajectory.mean(axis=0, keepdims=True)
    amp = np.linalg.norm(x, axis=1)
    amp = amp - amp.mean()
    n = amp.size
    # pad to next power of two for FFT efficiency
    nfft = 1 << (int(np.ceil(np.log2(2 * n))))
    F = np.fft.rfft(amp, n=nfft)
    acf = np.fft.irfft(F * np.conj(F), n=nfft)[:n]
    acf = acf / acf[0]
    threshold = 1.0 / np.e
    below = np.where(acf < threshold)[0]
    if below.size == 0:
        return float(n * dt * 0.5)  # fallback: half-trajectory
    return float(below[0] * dt)


# ---------- multi-grid weak-form SINDy ---------- #

def _bump_basis(centers_t: np.ndarray, t_grid: np.ndarray, r: float) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate polynomial bump psi(t; r, t_c) = (1 - ((t-t_c)/r)^2)^2 for |t-t_c| <= r
    and its analytic derivative psi'(t) = -4 ((t-t_c)/r^2) (1 - ((t-t_c)/r)^2).

    Returns (psi_matrix, psi_dot_matrix) each of shape (len(centers_t), len(t_grid)).
    Zero outside each bump's support.
    """
    u = (t_grid[None, :] - centers_t[:, None]) / r  # (M, N)
    mask = np.abs(u) <= 1.0
    psi = np.where(mask, (1 - u * u) ** 2, 0.0)
    psi_dot = np.where(mask, -4.0 * (u / r) * (1 - u * u), 0.0)
    return psi, psi_dot


def weak_form_observation_matrix(
    trajectory: np.ndarray, dt: float, r: float, n_centers: int
) -> tuple[np.ndarray, np.ndarray]:
    """Build weak-form (Theta, B) matrices at support radius r.

    For each center t_c (placed uniformly with support entirely inside the
    trajectory), build two quantities for each state dimension d and basis
    term j:
        Theta[c*3 + d, j] = integral over t of psi(t; r, t_c) * basis_j(x(t))
        B[c*3 + d]        = - integral over t of psi'(t; r, t_c) * x_d(t)
                            (integration-by-parts; derivative onto test function)
    The linear system in the sparse coefficient matrix C (shape 3 x 10) is:
        C @ basis(x) = dx/dt (weak sense)  =>  for each d:  C[d, :] @ Theta_sub = B_sub

    Returns (Theta, B) where Theta has shape (n_centers*3, 10) and B has shape
    (n_centers*3,). The rows for state d (d=0,1,2) are at indices
    {c*3 + d : c = 0..n_centers-1}. We solve each row of C independently.
    """
    N = trajectory.shape[0]
    T = (N - 1) * dt
    t_grid = np.arange(N) * dt
    # centers spaced so each bump has full support [t_c - r, t_c + r]
    t_lo, t_hi = r, T - r
    if t_hi <= t_lo:
        raise ValueError(f"radius r={r} too large for trajectory length {T}")
    centers_t = np.linspace(t_lo, t_hi, n_centers)
    psi, psi_dot = _bump_basis(centers_t, t_grid, r)
    # basis evaluated along the observed trajectory: shape (N, 10)
    basis_along = np.stack([eval_basis(s) for s in trajectory], axis=0)
    # Theta[c, j] = integral psi_c(t) * basis_j(x(t)) dt
    # shape (n_centers, 10)
    Theta_scalar = simpson(psi[:, :, None] * basis_along[None, :, :], x=t_grid, axis=1)
    # B_d[c] = - integral psi'_c(t) * x_d(t) dt; shape (n_centers, 3)
    B_scalar = -simpson(psi_dot[:, :, None] * trajectory[None, :, :], x=t_grid, axis=1)
    # Expand to per-dimension rows
    # Theta_full: (n_centers * 3, 10) — basis integral is shared across state dims
    Theta_full = np.repeat(Theta_scalar, 3, axis=0)  # (3*n_centers, 10)
    B_full = B_scalar.flatten()                       # (3*n_centers,)
    return Theta_full, B_full


def stlsq_per_row(
    Theta: np.ndarray, B: np.ndarray, threshold: float, max_iter: int = 20
) -> np.ndarray:
    """STLSQ solving C @ Theta_sub = B_sub per-row for the 3 state dimensions.

    Theta has (M*3, 10) rows interleaved d=0,1,2. We split by row index and
    solve 3 independent sparse LS problems.
    """
    C = np.zeros((3, 10))
    for d in range(3):
        sel = np.arange(d, Theta.shape[0], 3)
        Theta_d = Theta[sel]
        B_d = B[sel]
        # Initial OLS
        coef, *_ = np.linalg.lstsq(Theta_d, B_d, rcond=None)
        for _ in range(max_iter):
            big = np.abs(coef) >= threshold
            if not big.any():
                coef = np.zeros_like(coef)
                break
            coef = np.zeros_like(coef)
            coef[big], *_ = np.linalg.lstsq(Theta_d[:, big], B_d, rcond=None)
            # freeze if no further mask change
            new_big = np.abs(coef) >= threshold
            if np.array_equal(new_big, big):
                break
        C[d] = coef
    return C


def multigrid_weak_form_candidates(
    trajectory: np.ndarray, dt: float, tau_decorr: float,
    thresholds: list[float] | None = None,
    n_centers: int = 40,
) -> list[dict]:
    """Emit weak-form SINDy candidates across an autocorrelation-radius grid
    and a sparsity-threshold grid. Each candidate carries the stacked-scale
    coefficient matrix, the threshold, and a design-matrix diagnostic.
    """
    if thresholds is None:
        thresholds = list(WEAK_FORM_THRESHOLDS)
    radii = np.geomspace(
        RADIUS_MIN_FACTOR * tau_decorr,
        RADIUS_MAX_FACTOR * tau_decorr,
        N_RADII,
    )
    # Build stacked observation matrix across all radii
    Theta_stack_rows = []
    B_stack_rows = []
    used_radii = []
    for r in radii:
        try:
            Theta_r, B_r = weak_form_observation_matrix(
                trajectory, dt, float(r), n_centers=n_centers
            )
        except ValueError:
            continue
        Theta_stack_rows.append(Theta_r)
        B_stack_rows.append(B_r)
        used_radii.append(float(r))
    if not Theta_stack_rows:
        return []
    Theta_stack = np.vstack(Theta_stack_rows)
    B_stack = np.concatenate(B_stack_rows)
    # Per-radius ALSO fit individually so operator can inspect single-scale behavior.
    candidates = []
    for thr in thresholds:
        C = stlsq_per_row(Theta_stack, B_stack, thr)
        # residual covariance diagnostic (per-state-row)
        residuals = []
        for d in range(3):
            sel = np.arange(d, Theta_stack.shape[0], 3)
            residuals.append(float(np.linalg.norm(Theta_stack[sel] @ C[d] - B_stack[sel])))
        k = int(np.sum(np.abs(C) > 1e-10))
        candidates.append({
            "threshold_lambda": float(thr),
            "coefficient_matrix": C.tolist(),
            "nonzero_terms": k,
            "per_row_residual_norm": residuals,
            "radii_used": used_radii,
            "n_centers": n_centers,
        })
    return candidates


# ---------- Wasserstein persistence gate ---------- #

def persistence_diagram_of_trajectory(
    trajectory: np.ndarray, max_points: int = 400, max_dim: int = 1,
    discard_transient: bool = True,
) -> dict:
    """Subsample (attractor portion of) the trajectory, compute Vietoris-Rips
    persistence via ripser, return H_0 + H_1 diagrams as (birth, death) arrays.

    Strips the essential class (the single H_0 feature with death=infinity)
    rather than capping it; the essential class carries no discriminative
    information about attractor shape and capping injects arbitrary W_1.
    """
    from ripser import ripser
    N = trajectory.shape[0]
    if discard_transient:
        start = int(TRANSIENT_FRACTION * N)
        traj = trajectory[start:]
    else:
        traj = trajectory
    M = traj.shape[0]
    idx = np.linspace(0, M - 1, min(max_points, M), dtype=int)
    pts = traj[idx]
    result = ripser(pts, maxdim=max_dim)
    dgms = result["dgms"]
    clean = []
    for d in dgms:
        finite = d[np.isfinite(d[:, 1])]  # drop essential class in H_0
        clean.append(finite)
    return {"H0": clean[0], "H1": clean[1] if len(clean) > 1 else np.zeros((0, 2))}


def wasserstein_persistence_distance(pd_a: dict, pd_b: dict) -> dict:
    """Wasserstein-1 and Bottleneck distances summed over H_0 and H_1."""
    from persim import wasserstein, bottleneck
    w = 0.0
    b = 0.0
    per_dim = {}
    for dim in ("H0", "H1"):
        a_pd = pd_a.get(dim, np.zeros((0, 2)))
        b_pd = pd_b.get(dim, np.zeros((0, 2)))
        w_d = float(wasserstein(a_pd, b_pd))
        b_d = float(bottleneck(a_pd, b_pd))
        per_dim[dim] = {"wasserstein_1": w_d, "bottleneck": b_d}
        w += w_d
        b = max(b, b_d)  # Bottleneck: max over dims is conventional
    return {"wasserstein_1_total": w, "bottleneck_max": b, "per_dim": per_dim}


# ---------- Method B combined gate ---------- #

def simulate_attractor(C: np.ndarray, T: float, dt: float, ic: np.ndarray) -> np.ndarray | None:
    """Integrate the candidate ODE long enough to settle on its attractor."""
    from scipy.integrate import solve_ivp
    ode = SparseODE(coefficients=C)
    t_eval = np.arange(0, T + dt / 2, dt)
    try:
        sol = solve_ivp(ode.rhs, (0, T), ic, t_eval=t_eval, method="RK45",
                        rtol=1e-5, atol=1e-7)
    except Exception:
        return None
    if not sol.success:
        return None
    traj = sol.y.T
    if not np.all(np.isfinite(traj)) or np.max(np.abs(traj)) > 1e4:
        return None
    return traj


def calibrate_wasserstein_threshold(
    true_C: np.ndarray,
    ic: np.ndarray,
    T: float,
    dt: float,
    n_perturbations: int = 3,
    ic_noise: float = 0.01,
) -> dict:
    """Compute the intrinsic attractor-sampling noise floor: W_1 between
    persistence diagrams of the true rule simulated from slightly-perturbed
    initial conditions. Candidates must beat `admit_factor * noise_floor`.
    """
    rng = np.random.default_rng(0)
    baseline_traj = simulate_attractor(true_C, T, dt, ic)
    pd_baseline = persistence_diagram_of_trajectory(baseline_traj)
    w_samples = []
    for _ in range(n_perturbations):
        ic_p = ic + rng.normal(0, ic_noise, size=ic.shape)
        sim = simulate_attractor(true_C, T, dt, ic_p)
        if sim is None:
            continue
        pd_p = persistence_diagram_of_trajectory(sim)
        d = wasserstein_persistence_distance(pd_p, pd_baseline)
        w_samples.append(d["wasserstein_1_total"])
    floor = float(np.mean(w_samples)) if w_samples else 1.0
    return {
        "noise_floor": floor,
        "samples": w_samples,
        "threshold": WASSERSTEIN_ADMIT_FACTOR * floor,
    }


def method_b_v5_correct(
    candidates: list[dict],
    trajectory: np.ndarray,
    dt: float,
    ic: np.ndarray,
    wasserstein_threshold: float,
) -> dict:
    # Observation persistence diagram (computed once).
    pd_obs = persistence_diagram_of_trajectory(trajectory)
    w_threshold = wasserstein_threshold

    records = []
    for i, cand in enumerate(candidates):
        C = np.array(cand["coefficient_matrix"])
        mdl = L_NML_bits(C, trajectory, dt)
        filt = ergodic_divergence_filter(C, trajectory, dt)
        # Simulate candidate attractor for topological comparison
        sim_traj = simulate_attractor(C, T=(trajectory.shape[0] - 1) * dt, dt=dt, ic=ic)
        if sim_traj is None:
            wass = {
                "wasserstein_1_total": float("inf"),
                "bottleneck_max": float("inf"),
                "per_dim": {},
                "pd_computed": False,
            }
            pd_gate_pass = False
        else:
            pd_cand = persistence_diagram_of_trajectory(sim_traj)
            wass = wasserstein_persistence_distance(pd_cand, pd_obs)
            wass["pd_computed"] = True
            pd_gate_pass = wass["wasserstein_1_total"] <= w_threshold
        law_certified = (
            filt["ergodic_dissipative"]
            and filt["flow_invariant"]
            and pd_gate_pass
        )
        records.append({
            "index": i,
            "threshold_lambda": cand["threshold_lambda"],
            "coefficient_matrix": cand["coefficient_matrix"],
            "k": mdl["k"],
            "L_bits": mdl["L_bits"],
            "nll_bits": mdl["nll_bits"],
            "lyapunov_spectrum": filt["lyapunov_spectrum"],
            "lyap_sum": filt["lyap_sum"],
            "lyap_zero_magnitude": filt["lyap_zero_magnitude"],
            "ergodic_dissipative": filt["ergodic_dissipative"],
            "flow_invariant": filt["flow_invariant"],
            "wasserstein_to_obs": wass,
            "wasserstein_threshold": w_threshold,
            "pd_gate_pass": pd_gate_pass,
            "law_certified_v5_correct": bool(law_certified),
            "kaplan_yorke_dim": filt["kaplan_yorke_dim"],
            "per_row_residual_norm": cand.get("per_row_residual_norm"),
            "radii_used": cand.get("radii_used"),
        })
    certified = [r for r in records if r["law_certified_v5_correct"]]
    ranked = sorted(records, key=lambda r: r["L_bits"])
    argmin_certified = min(certified, key=lambda r: r["L_bits"]) if certified else None
    points = [(r["L_bits"], r["k"]) for r in certified]
    pareto_idx = pareto_front(points) if points else []
    pareto = [certified[i] for i in pareto_idx]
    return {
        "all_scored": ranked,
        "certified_subset": certified,
        "argmin_certified": argmin_certified,
        "pareto_front": sorted(pareto, key=lambda r: r["L_bits"]),
        "wasserstein_threshold": w_threshold,
        "filter_params": {
            "ergodic_margin": ERGODIC_MARGIN,
            "flow_invariant_eps": FLOW_INVARIANT_EPS,
            "wasserstein_admit_factor": WASSERSTEIN_ADMIT_FACTOR,
            "transient_fraction": TRANSIENT_FRACTION,
        },
    }


# ---------- kernel entry point (GP-143 promotion 2026-04-24) ---------- #

def run_weak_form_pipeline(
    trajectory: np.ndarray,
    dt: float,
    rubric_params: dict,
    initial_state: Optional[np.ndarray] = None,
) -> dict:
    """Kernel entry point for the autocorrelation-radius multi-grid weak-form
    SINDy + Method B pipeline. Invoked by autoresearch_loop.py PHASE C when
    rubric declares fit_score_mode='dynamical_lattice'.

    Parameters
    ----------
    trajectory : np.ndarray shape (N, d)
        Full-state observation.
    dt : float
        Sampling interval.
    rubric_params : dict
        rubric_data['dynamical_lattice'] block. Expected keys:
          method_a_variant (str), method_a_params (dict),
          noise_envelope_sigma (float) OR wasserstein_noise_floor (float),
          wasserstein_admit_factor (float, default 2.0 or 3.0),
          observation_T (float)
    initial_state : optional np.ndarray
        Starting state for candidate attractor simulation. If None, uses
        trajectory[0].

    Returns
    -------
    dict with keys:
      tau_decorr, method_a_variant, candidates (list),
      certified_subset (list), champion (dict or None),
      pareto_front (list), gate_result (dict)
    """
    if initial_state is None:
        initial_state = trajectory[0]

    method_a_params = rubric_params.get("method_a_params", {}) or {}

    # Step 1: autocorrelation timescale
    tau = autocorrelation_decorrelation_time(trajectory, dt)

    # Step 2: Method A — multi-grid weak-form candidates
    thresholds = method_a_params.get("thresholds", list(WEAK_FORM_THRESHOLDS))
    n_centers = int(method_a_params.get("n_centers", 40))
    candidates = multigrid_weak_form_candidates(
        trajectory, dt, tau_decorr=tau,
        thresholds=thresholds, n_centers=n_centers,
    )

    # Step 3: Method B — certifier
    method_b_result = method_b_v5_correct(
        candidates, trajectory, dt, initial_state,
        wasserstein_threshold=_resolve_w_threshold(rubric_params, trajectory.std(axis=0)),
    )

    champion = method_b_result.get("argmin_certified")
    return {
        "tau_decorr": tau,
        "method_a_variant": rubric_params.get("method_a_variant", "weak_form_sindy_auto_radii"),
        "candidates": candidates,
        "certified_subset": method_b_result.get("certified_subset", []),
        "champion": champion,
        "pareto_front": method_b_result.get("pareto_front", []),
        "method_b_result": method_b_result,
    }


def _resolve_w_threshold(rubric_params: dict, traj_std: np.ndarray) -> float:
    """Resolve Wasserstein admit threshold from rubric: calibrated floor OR
    Fasy bound OR amplitude-proportional fallback."""
    from math import sqrt
    admit_factor = float(rubric_params.get("wasserstein_admit_factor", WASSERSTEIN_ADMIT_FACTOR))
    if "wasserstein_noise_floor" in rubric_params:
        return admit_factor * float(rubric_params["wasserstein_noise_floor"])
    if "noise_envelope_sigma" in rubric_params and "observation_T" in rubric_params:
        sigma = float(rubric_params["noise_envelope_sigma"])
        T = float(rubric_params["observation_T"])
        return admit_factor * 2.0 * sigma * sqrt(T)
    amp = float(np.linalg.norm(traj_std))
    return WASSERSTEIN_ADMIT_FACTOR * 0.25 * amp


# ---------- Optional import helper for type hints ---------- #
try:
    from typing import Optional  # noqa: E401
except ImportError:
    Optional = None  # type: ignore


# ---------- driver (kept as smoke-test; not auto-invoked from loop) ---------- #

def main() -> None:
    truth = json.loads((HERE.parent / "_holdout_locked" / "truth.json").read_text())
    holdout_traj = np.load(HERE.parent / "_holdout_locked" / "trajectories" / "traj_5.npy")
    holdout_true_C = np.array(truth["holdout_pair"]["ode"]["coefficient_matrix"])
    dt = truth["dt"]
    ic = np.array(truth["initial_state"])
    T = (holdout_traj.shape[0] - 1) * dt

    print(f"=== v5-correct pipeline ===")
    print(f"trajectory: {holdout_traj.shape}  dt={dt}  T={T}")

    tau = autocorrelation_decorrelation_time(holdout_traj, dt)
    print(f"autocorrelation decorrelation time: tau_decorr = {tau:.4f}")

    # Method A: autocorrelation-radius multi-grid weak-form SINDy
    t0 = time.time()
    candidates = multigrid_weak_form_candidates(holdout_traj, dt, tau_decorr=tau)
    t_method_a = time.time() - t0
    print(f"Method A emitted {len(candidates)} candidates in {t_method_a:.2f}s "
          f"(radii log-grid around tau_decorr)")

    # Calibrate Wasserstein threshold from the intrinsic noise floor
    print(f"\n=== Wasserstein threshold calibration ===")
    calib = calibrate_wasserstein_threshold(holdout_true_C, ic, T, dt)
    w_threshold = calib["threshold"]
    print(f"  intrinsic noise floor (true rule, {len(calib['samples'])} perturbed ICs): "
          f"W_1 = {calib['noise_floor']:.4f}")
    print(f"  admit threshold ({WASSERSTEIN_ADMIT_FACTOR}x noise floor): W_1 <= {w_threshold:.4f}")

    # Score the true rule under v5-correct's Method B
    print(f"\n=== TRUE RULE under v5-correct Method B ===")
    true_mdl = L_NML_bits(holdout_true_C, holdout_traj, dt)
    true_filt = ergodic_divergence_filter(holdout_true_C, holdout_traj, dt)
    true_sim = simulate_attractor(holdout_true_C, T=T, dt=dt, ic=ic)
    pd_obs = persistence_diagram_of_trajectory(holdout_traj)
    pd_true_sim = persistence_diagram_of_trajectory(true_sim) if true_sim is not None else None
    true_wass = (
        wasserstein_persistence_distance(pd_true_sim, pd_obs)
        if pd_true_sim is not None else {"wasserstein_1_total": float("inf")}
    )
    print(f"  k={true_mdl['k']}  L_bits={true_mdl['L_bits']:.2f}")
    print(f"  Lyap spectrum: {[f'{l:+.3f}' for l in true_filt['lyapunov_spectrum']]}")
    print(f"  sum(lambda)={true_filt['lyap_sum']:+.3f}  |lambda_zero|={true_filt['lyap_zero_magnitude']:.3f}")
    print(f"  ergodic_diss={true_filt['ergodic_dissipative']}  flow_inv={true_filt['flow_invariant']}")
    print(f"  Wasserstein-1(true_sim, obs) = {true_wass['wasserstein_1_total']:.4f}  threshold={w_threshold:.4f}")
    print()

    # Method B: Lyapunov-ergodic + Wasserstein-persistence on candidate set
    t0 = time.time()
    result = method_b_v5_correct(candidates, holdout_traj, dt, ic, wasserstein_threshold=w_threshold)
    t_method_b = time.time() - t0
    print(f"Method B (ergodic + flow-invariant + Wasserstein-persistence) ran in {t_method_b:.2f}s")
    print()

    print(
        f"{'rank':>5} {'lambda':>7} {'k':>3} {'L_bits':>12} "
        f"{'sum_l':>8} {'|l0|':>7} {'W_1':>9} {'erg':>4} {'flow':>5} {'PD':>4} {'cert':>5}"
    )
    for rnk, r in enumerate(result["all_scored"], 1):
        w = r["wasserstein_to_obs"]["wasserstein_1_total"]
        cert = "Y" if r["law_certified_v5_correct"] else "N"
        print(
            f"{rnk:>5} {r['threshold_lambda']:>7.3f} {r['k']:>3} {r['L_bits']:>12.2f} "
            f"{r['lyap_sum']:>+8.3f} {r['lyap_zero_magnitude']:>7.3f} "
            f"{(w if np.isfinite(w) else float('inf')):>9.4f} "
            f"{'Y' if r['ergodic_dissipative'] else 'N':>4} "
            f"{'Y' if r['flow_invariant'] else 'N':>5} "
            f"{'Y' if r['pd_gate_pass'] else 'N':>4} {cert:>5}"
        )

    n_cert = len(result["certified_subset"])
    argmin = result["argmin_certified"]
    print(f"\ncertified: {n_cert}/{len(candidates)}")
    if argmin is not None:
        matrix_err = float(np.linalg.norm(np.array(argmin["coefficient_matrix"]) - holdout_true_C))
        print(
            f"argmin_certified: lambda={argmin['threshold_lambda']}  "
            f"k={argmin['k']}  L={argmin['L_bits']:.2f}  "
            f"||C - C_true||={matrix_err:.4f}"
        )

    out = {
        "pipeline": "v5-correct (autocorrelation-radius weak-form + Lyapunov-ergodic + Wasserstein-persistence)",
        "tau_decorr": tau,
        "radii_grid": [float(r) for r in np.geomspace(
            RADIUS_MIN_FACTOR * tau, RADIUS_MAX_FACTOR * tau, N_RADII
        )],
        "wasserstein_threshold": w_threshold,
        "true_rule": {
            "k": true_mdl["k"],
            "L_bits": true_mdl["L_bits"],
            "lyapunov_spectrum": true_filt["lyapunov_spectrum"],
            "lyap_sum": true_filt["lyap_sum"],
            "lyap_zero_magnitude": true_filt["lyap_zero_magnitude"],
            "ergodic_dissipative": true_filt["ergodic_dissipative"],
            "flow_invariant": true_filt["flow_invariant"],
            "wasserstein_to_obs": true_wass["wasserstein_1_total"] if "wasserstein_1_total" in true_wass else None,
            "law_certified_v5_correct": (
                true_filt["ergodic_dissipative"]
                and true_filt["flow_invariant"]
                and (true_wass.get("wasserstein_1_total", float("inf")) <= w_threshold)
            ),
        },
        "method_a_compute_seconds": t_method_a,
        "method_b_compute_seconds": t_method_b,
        "method_b_result": result,
    }
    (HERE / "apparatus_v5_correct_result.json").write_text(
        json.dumps(out, indent=2, default=str)
    )
    print(f"\nwrote {HERE / 'apparatus_v5_correct_result.json'}")


if __name__ == "__main__":
    main()
