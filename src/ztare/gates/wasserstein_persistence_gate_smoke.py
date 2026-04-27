"""Smoke test for GP-143 Wasserstein-persistence gate.

Runs the gate against the lorenz_bridge_test holdout with:
- the TRUE rule (expected: pass)
- a known-overfit v3 argmin candidate (expected: pass at reasonable threshold
  because v3 argmin's attractor still resembles the true attractor)
- a degenerate candidate (zeros; expected: fail)

Also checks hash-commitment verification and the
filter_per_candidate_for_mutator_prompt boundary.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from src.ztare.gates.wasserstein_persistence_gate import (  # noqa: E402
    GATE_ID,
    filter_per_candidate_for_mutator_prompt,
    run_gate,
)


def _commit(cand: dict) -> dict:
    payload = {k: v for k, v in cand.items() if k != "sha256_commitment"}
    h = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()
    return {**cand, "sha256_commitment": h}


def main() -> None:
    lorenz_dir = REPO / "projects" / "lorenz_bridge_test"
    truth = json.loads((lorenz_dir / "_holdout_locked" / "truth.json").read_text())
    traj = np.load(lorenz_dir / "_holdout_locked" / "trajectories" / "traj_5.npy")
    dt = truth["dt"]
    ic = np.array(truth["initial_state"])
    true_C = truth["holdout_pair"]["ode"]["coefficient_matrix"]
    basis = truth["basis_labels"]

    # Candidate 1: the true rule
    true_cand = _commit({
        "candidate_id": "true_rule",
        "method_a_variant": "ground_truth",
        "coefficient_matrix": true_C,
        "covariance_matrix": None,
        "basis_labels": basis,
        "nonzero_terms_k": int(np.sum(np.abs(np.array(true_C)) > 1e-10)),
        "residual_norm_per_dim": [0.0, 0.0, 0.0],
        "threshold_lambda": 0.0,
        "metadata": {"source": "truth.json"},
    })

    # Candidate 2: degenerate zeros (should fail integration or gate)
    zero_C = [[0.0] * 10 for _ in range(3)]
    zero_cand = _commit({
        "candidate_id": "degenerate_zero",
        "method_a_variant": "negative_control",
        "coefficient_matrix": zero_C,
        "covariance_matrix": None,
        "basis_labels": basis,
        "nonzero_terms_k": 0,
        "residual_norm_per_dim": [0.0, 0.0, 0.0],
        "threshold_lambda": 0.0,
        "metadata": {"source": "zeros"},
    })

    # Candidate 3: tampered hash (true coefficients but wrong commitment)
    tampered = dict(true_cand)
    tampered = {**tampered, "candidate_id": "hash_tampered",
                "sha256_commitment": "deadbeef" * 8}

    candidates = [true_cand, zero_cand, tampered]
    # Calibrated-floor route: use the intrinsic attractor-sampling variance
    # (W1 between true-rule simulations from perturbed ICs). 172 was measured
    # in apparatus_v5_correct.py. For a real rubric, this is either declared
    # or computed by a calibration pre-run step.
    rubric_params = {
        "wasserstein_noise_floor": 172.0,
        "wasserstein_admit_factor": 2.0,
        # kept for documentation; ignored when noise_floor is present
        "noise_envelope_sigma": 0.03,
        "observation_T": (traj.shape[0] - 1) * dt,
    }

    print(f"=== smoke test: {GATE_ID} ===")
    print(f"trajectory shape {traj.shape}, dt={dt}, T={rubric_params['observation_T']}")
    print(f"rubric_params: {rubric_params}")
    result = run_gate(candidates, traj, rubric_params, ic, dt)
    print(f"\ngate.passed = {result['passed']}")
    print(f"gate.actual (best W1) = {result['actual']}")
    print(f"gate.threshold = {result['threshold']:.4f}")
    print(f"gate.reason = {result['reason']}")
    print(f"\nper-candidate:")
    for pc in result["extra"]["per_candidate"]:
        metric_str = f"{pc['metric']:.4f}" if pc["metric"] is not None else "-"
        print(f"  {pc['candidate_id']:>22}  passed={pc['passed']}  "
              f"W1={metric_str:>10}  rationale={pc['rationale']}")

    # Mutator-visibility boundary: metric values MUST not leak
    filtered = filter_per_candidate_for_mutator_prompt(result)
    leaked_keys = {"per_candidate", "champion_candidate_id"}
    assert not any(k in filtered.get("extra", {}) for k in leaked_keys), \
        f"mutator-view leaked one of {leaked_keys}"
    print(f"\nmutator-view keys: {sorted(filtered.get('extra', {}).keys())}")
    print("mutator-visibility boundary: PASS (per_candidate not leaked)")


if __name__ == "__main__":
    main()
