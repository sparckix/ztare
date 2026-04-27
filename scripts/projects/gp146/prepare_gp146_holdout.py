"""Prepare the GP-146 Arnold Cat Map holdout: trajectory + ground-truth truth.json.

Run once before launching the GP-146 ZTARE run. Creates:
  projects/gp146_arnold_cat_map_validation/_holdout_locked/
      cat_map_trajectory.npy     — 10^6-step (x, y) trajectory
      truth.json                 — lambda_1 = 2*log(phi) to 30 digits + metadata

The Cat Map is T(x,y) = ((2x+y) mod 1, (x+y) mod 1).
The Jacobian A = [[2,1],[1,1]] has eigenvalues (3 +/- sqrt(5))/2.
The maximum Lyapunov exponent is lambda_1 = log((3+sqrt(5))/2) = 2*log(phi).

Usage:
  python scripts/prepare_gp146_holdout.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO / "projects" / "gp146_arnold_cat_map_validation"
HOLDOUT = PROJECT / "_holdout_locked"

N_STEPS = 1_000_000


def generate_trajectory() -> np.ndarray:
    """Deterministic Cat Map iteration from a Diophantine IC."""
    x = float(np.sqrt(2.0)) - 1.0   # ≈ 0.4142135623730951
    y = float(np.pi) - 3.0          # ≈ 0.14159265358979312
    traj = np.empty((N_STEPS, 2), dtype=np.float64)
    for i in range(N_STEPS):
        x, y = (2.0 * x + y) % 1.0, (x + y) % 1.0
        traj[i, 0] = x
        traj[i, 1] = y
    return traj


def compute_lyapunov_estimate(traj: np.ndarray) -> float:
    """Benettin-style estimator using the CONSTANT Jacobian A.

    Since A is constant (linear map), the estimator is simply the average
    log-growth of a tangent vector under repeated multiplication by A. After
    many steps every vector aligns with the leading eigenvector and the
    rate converges to log(lambda_+).

    We use QR normalization every step to avoid overflow.
    """
    A = np.array([[2.0, 1.0], [1.0, 1.0]])
    v = np.array([1.0, 0.0])
    log_growth_sum = 0.0
    # Use only a subset for the estimator; the full 10^6 is for the mutator
    n_est = min(len(traj), 10_000)
    for _ in range(n_est):
        v = A @ v
        nrm = float(np.linalg.norm(v))
        if nrm == 0.0:
            break
        log_growth_sum += np.log(nrm)
        v = v / nrm
    return log_growth_sum / n_est


def compute_truth_symbolic() -> dict:
    """Compute lambda_1 to 30 digits via high-precision arithmetic.

    Uses mpmath if available; falls back to extended-precision string constant
    from a pre-computed reference (see evidence.txt Set G).
    """
    try:
        import mpmath
        mpmath.mp.dps = 35
        phi = (mpmath.mpf(1) + mpmath.sqrt(5)) / mpmath.mpf(2)
        lam = 2 * mpmath.log(phi)
        lam_eq = mpmath.log((mpmath.mpf(3) + mpmath.sqrt(5)) / mpmath.mpf(2))
        # Sanity: two forms must agree to at least 30 digits
        delta = abs(lam - lam_eq)
        assert delta < mpmath.mpf("1e-33"), f"two forms disagree: delta={delta}"
        return {
            "lambda_1_symbolic_form_A": "2 * log((1 + sqrt(5)) / 2)",
            "lambda_1_symbolic_form_B": "log((3 + sqrt(5)) / 2)",
            "lambda_1_digits_30": mpmath.nstr(lam, 30, strip_zeros=False),
            "equivalence_check_delta": mpmath.nstr(delta, 5),
            "phi_digits_30": mpmath.nstr(phi, 30, strip_zeros=False),
            "precision_dps_used": 35,
        }
    except ImportError:
        # Reference value frozen from mpmath 35-dps calculation
        return {
            "lambda_1_symbolic_form_A": "2 * log((1 + sqrt(5)) / 2)",
            "lambda_1_symbolic_form_B": "log((3 + sqrt(5)) / 2)",
            "lambda_1_digits_30": "0.962423650119206894995517826849",
            "phi_digits_30": "1.61803398874989484820458683437",
            "precision_dps_used": "frozen-reference (mpmath not installed)",
        }


def main() -> int:
    if not PROJECT.is_dir():
        print(f"ERROR: project dir not found: {PROJECT}", file=sys.stderr)
        return 1
    HOLDOUT.mkdir(parents=True, exist_ok=True)

    print("Generating Cat Map trajectory (N = 1,000,000)...")
    traj = generate_trajectory()
    traj_path = HOLDOUT / "cat_map_trajectory.npy"
    np.save(traj_path, traj)
    print(f"  wrote {traj_path}  (shape={traj.shape}, dtype={traj.dtype})")

    print("Estimating Lyapunov via Benettin...")
    lam_est = compute_lyapunov_estimate(traj)
    print(f"  lambda_hat_1 ≈ {lam_est:.12f}")

    print("Computing symbolic ground truth...")
    truth = compute_truth_symbolic()
    lam_true = float(truth["lambda_1_digits_30"][:20])  # 20-digit float cast
    print(f"  lambda_1 (true, 30 digits): {truth['lambda_1_digits_30']}")
    print(f"  |lambda_hat - lambda_true| ≈ {abs(lam_est - lam_true):.2e}")

    truth["lambda_hat_numerical_estimate_10k_steps"] = lam_est
    truth["trajectory_initial_condition"] = {
        "x0": "sqrt(2) - 1",
        "y0": "pi - 3",
        "x0_numerical": float(np.sqrt(2.0)) - 1.0,
        "y0_numerical": float(np.pi) - 3.0,
    }
    truth["trajectory_length"] = N_STEPS
    truth["map_definition"] = "T(x, y) = ((2*x + y) mod 1, (x + y) mod 1)"
    truth["jacobian"] = "A = [[2, 1], [1, 1]]; eigenvalues (3 +/- sqrt(5)) / 2"
    truth["source_specification"] = "projects/gp146_arnold_cat_map_validation/project_charter.md"
    truth_path = HOLDOUT / "truth.json"
    truth_path.write_text(json.dumps(truth, indent=2))
    print(f"  wrote {truth_path}")

    print("")
    print("Holdout ready. Launch with:")
    print(f"  make loop PROJECT=gp146_arnold_cat_map_validation "
          f"RUBRIC=gp146_arnold_cat_map_validation ITERS=15 "
          f"MUTATOR_MODEL=o3 JUDGE_MODEL=o3")
    return 0


if __name__ == "__main__":
    sys.exit(main())
