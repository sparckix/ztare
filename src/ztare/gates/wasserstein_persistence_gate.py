"""GP-143 Wasserstein-Persistence Gate (continuous-chaotic substrate class).

Law-certification gate for continuous-chaotic ODE candidates. Computes the
Wasserstein-1 distance between the persistence diagrams of (a) the
observation trajectory and (b) the candidate's simulated attractor. Admits
the candidate when W_1 is within the rubric-declared threshold derived from
the Fasy et al. 2014 stability bound.

Registration per GP-086: this gate lives in src/ztare/gates/, not embedded
in any solver module. The continuous-chaotic solver at
src/ztare/fit/continuous_chaotic/ calls this module via run_gate(...).

Design commitments inherited from GP-143 seam:
- Threshold is rubric-declared (noise_envelope_sigma, observation_T,
  wasserstein_admit_factor). Candidate cannot influence its own threshold.
- Hash-commitment discipline: each candidate record carries a SHA-256
  commitment over all its non-hash fields. The gate recomputes and verifies
  before admitting. Mutation detection.
- Return shape matches src/ztare/gates/global_gates._gate convention: dict
  with passed / actual / threshold / reason / extra. Legacy consumers treat
  it identically to existing gates.
- Mutator-visibility boundary: the gate's per-candidate metric values live in
  extra["per_candidate"] and are visible to operator and judge but filtered
  out before mutator prompt injection.

Dependencies: numpy, scipy.integrate.solve_ivp, ripser, persim.
"""
from __future__ import annotations

import hashlib
import json
from math import sqrt
from typing import Any, Optional

import numpy as np


GATE_ID = "wasserstein_persistence"
PRODUCER = "GP-143"
TRANSIENT_FRACTION = 0.20
PERSISTENCE_MAX_POINTS = 400
PERSISTENCE_MAX_DIM = 1


# ---------------------------------------------------------------------------
# Persistence diagram + Wasserstein-1 core (stateless; no rubric knobs here)
# ---------------------------------------------------------------------------

def persistence_diagram(
    trajectory: np.ndarray,
    max_points: int = PERSISTENCE_MAX_POINTS,
    max_dim: int = PERSISTENCE_MAX_DIM,
    discard_transient: bool = True,
) -> dict[str, np.ndarray]:
    """Compute H_0 + H_1 persistence diagrams of the Vietoris-Rips filtration
    of (the post-transient portion of) a trajectory.

    The essential H_0 class (death=infinity) is stripped rather than capped;
    it adds no discriminative information about attractor shape and injects
    arbitrary Wasserstein distance when capped per-diagram.
    """
    from ripser import ripser
    N = trajectory.shape[0]
    start = int(TRANSIENT_FRACTION * N) if discard_transient else 0
    traj = trajectory[start:]
    M = traj.shape[0]
    idx = np.linspace(0, M - 1, min(max_points, M), dtype=int)
    pts = traj[idx]
    result = ripser(pts, maxdim=max_dim)
    dgms = result["dgms"]
    return {
        "H0": dgms[0][np.isfinite(dgms[0][:, 1])],
        "H1": dgms[1] if len(dgms) > 1 else np.zeros((0, 2)),
    }


def wasserstein_1_diagrams(pd_a: dict[str, np.ndarray], pd_b: dict[str, np.ndarray]) -> dict[str, Any]:
    """Wasserstein-1 summed over H_0 and H_1; Bottleneck = max over dims."""
    from persim import wasserstein, bottleneck
    total = 0.0
    bmax = 0.0
    per_dim = {}
    for dim in ("H0", "H1"):
        a = pd_a.get(dim, np.zeros((0, 2)))
        b = pd_b.get(dim, np.zeros((0, 2)))
        w = float(wasserstein(a, b))
        bn = float(bottleneck(a, b))
        per_dim[dim] = {"wasserstein_1": w, "bottleneck": bn}
        total += w
        bmax = max(bmax, bn)
    return {"wasserstein_1_total": total, "bottleneck_max": bmax, "per_dim": per_dim}


# ---------------------------------------------------------------------------
# Hash-commitment verification
# ---------------------------------------------------------------------------

def _verify_hash_commitment(candidate: dict[str, Any]) -> bool:
    """Recompute SHA-256 over the sorted-key JSON of all non-hash fields and
    compare to the candidate's committed hash. Returns True iff match.
    """
    committed = candidate.get("sha256_commitment")
    if not committed:
        return False
    payload = {k: v for k, v in candidate.items() if k != "sha256_commitment"}
    computed = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()
    return computed == committed


# ---------------------------------------------------------------------------
# Threshold derivation (rubric-driven; candidate-independent)
# ---------------------------------------------------------------------------

def fasy_stability_threshold(
    noise_envelope_sigma: float,
    observation_T: float,
    admit_factor: float = 2.0,
) -> float:
    """Fasy et al. 2014 stability bound for Wasserstein-1 on persistence
    diagrams of noisy point clouds, scaled by a rubric-declared admit factor.

        tau_W = admit_factor * 2 * sigma * sqrt(T)

    VALID: substrates with additive observation noise of declared sigma.
    INVALID: substrates whose intrinsic variance comes from chaotic
    attractor-sampling from finite-time integration. For those, use
    wasserstein_noise_floor (rubric-declared calibrated floor).

    Rubric-driven and candidate-independent per GP-143 seam Round 2 MA→AS.
    """
    return float(admit_factor) * 2.0 * float(noise_envelope_sigma) * sqrt(float(observation_T))


def derive_threshold(rubric_params: dict[str, Any]) -> tuple[float, str]:
    """Rubric-driven threshold selection.

    Precedence:
        1. wasserstein_noise_floor * admit_factor   (calibrated floor,
           correct for chaotic attractors)
        2. fasy_stability_threshold(sigma, T)        (additive-noise fallback)

    Returns (threshold, derivation_route) where derivation_route is
    "calibrated_floor" or "fasy_bound" for audit.
    """
    admit_factor = float(rubric_params.get("wasserstein_admit_factor", 2.0))
    if "wasserstein_noise_floor" in rubric_params:
        floor = float(rubric_params["wasserstein_noise_floor"])
        return admit_factor * floor, "calibrated_floor"
    sigma = float(rubric_params["noise_envelope_sigma"])
    T = float(rubric_params["observation_T"])
    return fasy_stability_threshold(sigma, T, admit_factor), "fasy_bound"


# ---------------------------------------------------------------------------
# Candidate attractor simulation (thin wrapper; substrate-class-specific
# generators provide the integration interface)
# ---------------------------------------------------------------------------

def _simulate_candidate(
    candidate: dict[str, Any],
    initial_state: np.ndarray,
    T: float,
    dt: float,
) -> Optional[np.ndarray]:
    """Integrate a candidate polynomial ODE forward. Returns trajectory array
    of shape (N, d), or None if integration fails / diverges.

    Assumes candidate["coefficient_matrix"] and candidate["basis_labels"]
    match the degree-2 polynomial basis convention of
    src/ztare/fit/continuous_chaotic/. For higher-degree bases, the solver
    package's generator.py overrides this via dependency injection.
    """
    from scipy.integrate import solve_ivp
    C = np.array(candidate["coefficient_matrix"])
    labels = candidate.get("basis_labels",
                           ["1", "x", "y", "z",
                            "x*x", "x*y", "x*z", "y*y", "y*z", "z*z"])
    # Build a numeric RHS from the basis labels (degree 2, 3D).
    # For higher-degree / different-dim cases, this helper is replaced.
    if len(labels) != 10 or C.shape != (3, 10):
        return None

    def rhs(t: float, s: np.ndarray) -> np.ndarray:
        x, y, z = s
        basis = np.array([
            1.0, x, y, z,
            x * x, x * y, x * z,
            y * y, y * z, z * z,
        ])
        return C @ basis

    t_eval = np.arange(0, T + dt / 2, dt)
    try:
        sol = solve_ivp(rhs, (0, T), initial_state, t_eval=t_eval,
                        method="RK45", rtol=1e-5, atol=1e-7)
    except Exception:
        return None
    if not sol.success:
        return None
    traj = sol.y.T
    if not np.all(np.isfinite(traj)) or np.max(np.abs(traj)) > 1e4:
        return None
    return traj


# ---------------------------------------------------------------------------
# Public gate entry
# ---------------------------------------------------------------------------

def run_gate(
    candidates: list[dict[str, Any]],
    observation_trajectory: np.ndarray,
    rubric_params: dict[str, Any],
    initial_state: np.ndarray,
    dt: float,
) -> dict[str, Any]:
    """Run the Wasserstein-persistence gate on a candidate set.

    Parameters
    ----------
    candidates : list[dict]
        Candidate records per GP-143 seam 6.4 JSONL schema.
    observation_trajectory : np.ndarray
        Locked holdout trajectory, shape (N, d).
    rubric_params : dict
        rubric_data["dynamical_lattice"]. Requires:
        - noise_envelope_sigma: float
        - observation_T: float
        - wasserstein_admit_factor: float
    initial_state : np.ndarray
        Locked holdout initial condition, shape (d,).
    dt : float
        Sampling interval.

    Returns
    -------
    dict
        Matches src/ztare/gates/global_gates._gate shape. Per-candidate
        detail in extra["per_candidate"]. Gate-level verdict = any candidate
        passes.
    """
    threshold, derivation_route = derive_threshold(rubric_params)
    T = float(rubric_params.get("observation_T",
                                (observation_trajectory.shape[0] - 1) * dt))

    pd_obs = persistence_diagram(observation_trajectory)

    per_candidate: list[dict[str, Any]] = []
    best_w1: Optional[float] = None
    any_pass = False
    champion_id: Optional[str] = None

    for cand in candidates:
        cid = cand.get("candidate_id", "?")
        # Hash-commitment verification FIRST (GP-143 spec OQ-4 resolution)
        if not _verify_hash_commitment(cand):
            per_candidate.append({
                "candidate_id": cid,
                "passed": False,
                "metric": None,
                "rationale": "hash_commitment_violation",
            })
            continue
        sim = _simulate_candidate(cand, initial_state, T, dt)
        if sim is None:
            per_candidate.append({
                "candidate_id": cid,
                "passed": False,
                "metric": None,
                "rationale": "integration_failed_or_diverged",
            })
            continue
        pd_cand = persistence_diagram(sim)
        w = wasserstein_1_diagrams(pd_cand, pd_obs)
        w1 = float(w["wasserstein_1_total"])
        passed = w1 <= threshold
        per_candidate.append({
            "candidate_id": cid,
            "passed": bool(passed),
            "metric": w1,
            "bottleneck_max": float(w["bottleneck_max"]),
            "per_dim": w["per_dim"],
            "rationale": "within_threshold" if passed else "exceeds_threshold",
        })
        if best_w1 is None or w1 < best_w1:
            best_w1 = w1
            if passed:
                champion_id = cid
        if passed:
            any_pass = True

    gate_passed = any_pass
    n_cert = sum(1 for c in per_candidate if c["passed"])
    admit_factor = float(rubric_params.get("wasserstein_admit_factor", 2.0))
    reason = (
        f"{n_cert}/{len(candidates)} candidates passed W1 <= {threshold:.4f} "
        f"(derivation={derivation_route}, admit_factor={admit_factor})"
    )
    return {
        "name": GATE_ID,
        "passed": gate_passed,
        "actual": best_w1,
        "threshold": threshold,
        "reason": reason,
        "penalty": 0 if gate_passed else 1,
        "hard_fail": False,
        "source": PRODUCER,
        "extra": {
            "n_candidates": len(candidates),
            "n_certified": n_cert,
            "champion_candidate_id": champion_id,
            "per_candidate": per_candidate,  # metric stays here; filter before mutator
            "threshold_derivation_route": derivation_route,
            "admit_factor": admit_factor,
        },
    }


def filter_per_candidate_for_mutator_prompt(gate_result: dict[str, Any]) -> dict[str, Any]:
    """Return a gate-result view safe for mutator injection.

    The mutator sees pass/fail counts and rationale categories. It does NOT
    see per-candidate raw metric values (GP-143 seam Round 3 MA resolution).
    Judge and operator receive the full gate_result; mutator receives this
    filtered view only.
    """
    filtered = {k: v for k, v in gate_result.items() if k != "extra"}
    extra = gate_result.get("extra", {})
    filtered["extra"] = {
        "n_candidates": extra.get("n_candidates"),
        "n_certified": extra.get("n_certified"),
        "threshold_derivation_route": extra.get("threshold_derivation_route"),
        "admit_factor": extra.get("admit_factor"),
        "rationale_categories": sorted({
            c.get("rationale", "")
            for c in extra.get("per_candidate", [])
        }),
    }
    return filtered
