"""Regression test: v3 reference benchmark on lorenz_bridge_test holdout.

Promoted from projects/lorenz_bridge_test/apparatus_candidate/benchmark_all.py
per GP-141 seam. Purpose: ensure the v3 reference implementation continues to
recover a near-truth candidate (k=10, matrix distance < 0.30 from truth) as
future apparatus changes land. Failure of this test indicates either a
regression in the Method A SINDy pipeline or a substrate drift.

Run: python -m pytest tests/primitives/test_continuous_A_plus_B_baselines.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
LB = REPO / "projects" / "lorenz_bridge_test"
sys.path.insert(0, str(LB))
sys.path.insert(0, str(LB / "apparatus_candidate"))


@pytest.fixture(scope="module")
def holdout_fixture():
    if not (LB / "_holdout_locked" / "truth.json").exists():
        pytest.skip("lorenz_bridge_test substrate not generated; run generate_family.py first")
    truth = json.loads((LB / "_holdout_locked" / "truth.json").read_text())
    traj = np.load(LB / "_holdout_locked" / "trajectories" / "traj_5.npy")
    return {
        "truth": truth,
        "holdout_traj": traj,
        "holdout_true_C": np.array(truth["holdout_pair"]["ode"]["coefficient_matrix"]),
        "dt": truth["dt"],
        "ic": np.array(truth["initial_state"]),
    }


def test_method_a_emits_candidates(holdout_fixture):
    """Method A (SINDy with derivative-residual) must emit at least 1 candidate."""
    from apparatus_v1_sindy import method_a_behavioral_set
    cands = method_a_behavioral_set(
        holdout_fixture["holdout_traj"],
        dt=holdout_fixture["dt"],
        ic=holdout_fixture["ic"],
    )
    assert len(cands) >= 1, "Method A emitted 0 candidates — SINDy pipeline or substrate regression"


def test_v3_argmin_recovers_near_truth(holdout_fixture):
    """v3 argmin_L candidate must have matrix distance < 0.30 from true generator."""
    from apparatus_v1_sindy import method_a_behavioral_set
    from apparatus_v3_combined import method_b_v3

    cands = method_a_behavioral_set(
        holdout_fixture["holdout_traj"],
        dt=holdout_fixture["dt"],
        ic=holdout_fixture["ic"],
    )
    result = method_b_v3(cands, holdout_fixture["holdout_traj"], holdout_fixture["dt"])
    argmin = result["argmin_L_dissipative"]
    assert argmin is not None, "v3 returned no dissipative candidate"
    C = np.array(argmin["coefficient_matrix"])
    dist = float(np.linalg.norm(C - holdout_fixture["holdout_true_C"]))
    assert dist < 0.30, f"v3 argmin matrix distance {dist:.4f} exceeds 0.30 tolerance"


def test_v2b_nml_admit_gate_discriminates(holdout_fixture):
    """v2b NML admit-gate must NOT admit everything (pathology check from INS-047 lineage)."""
    from apparatus_v1_sindy import method_a_behavioral_set
    from apparatus_v2b_nml_full import L_NML_bits, tau_NML_bits

    cands = method_a_behavioral_set(
        holdout_fixture["holdout_traj"],
        dt=holdout_fixture["dt"],
        ic=holdout_fixture["ic"],
    )
    traj = holdout_fixture["holdout_traj"]
    dt = holdout_fixture["dt"]
    N = traj.shape[0] * 3
    n_admitted = 0
    for cand in cands:
        C = np.array(cand["coefficient_matrix"])
        mdl = L_NML_bits(C, traj, dt)
        tau = tau_NML_bits(mdl["k"], N)
        if mdl["L_bits"] <= tau:
            n_admitted += 1
    # On chaotic substrate v2b should admit some but not all
    assert n_admitted < len(cands), f"v2b admitted all {n_admitted} candidates — regression to INS-047 NML-tautology pattern"


def test_liouville_dissipativity_on_true_rule(holdout_fixture):
    """Liouville check on true perturbed-Lorenz generator must report dissipative."""
    from apparatus_v2_rissanen import conservation_check
    cons = conservation_check(holdout_fixture["holdout_true_C"], holdout_fixture["holdout_traj"])
    assert cons["dissipative"], f"True generator reported non-dissipative; tr(J)={cons['tr_J_mean']:.3f}"
