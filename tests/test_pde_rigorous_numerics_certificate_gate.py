from ztare.gates.pde_rigorous_numerics_certificate_gate import (
    run_pde_rigorous_numerics_certificate_gate,
)


def _paid_receipt() -> dict:
    return {
        "label": "interval_tail_certificate",
        "certificate_type": "interval spectral Galerkin certificate",
        "pde_problem_statement": "semilinear elliptic PDE on bounded domain",
        "discretization_or_basis": "Chebyshev tensor basis with explicit mode cutoff",
        "interval_arithmetic_or_bounds": "directed rounding interval enclosure",
        "residual_bound": "||F(u_N)|| <= 1e-8",
        "truncation_tail_bound": "tail <= 1e-10 by analytic semigroup decay",
        "a_posteriori_argument": "radii polynomial negative on interval",
        "reproducibility_artifact": "certificates/elliptic_tail.json",
        "validator": "interval-tail-validator-v1",
        "theorem_linkage": "validated branch implies existence theorem hypothesis",
        "hostile_packet_or_failure_mode": "near-singular linearized operator packet",
    }


def test_rigorous_numerics_gate_requires_certificate_not_simulation() -> None:
    paid = run_pde_rigorous_numerics_certificate_gate(_paid_receipt())
    assert paid["passed"] is True
    assert paid["classification"] == "rigorous_numerics_certificate_paid"

    weak = dict(_paid_receipt())
    weak.pop("truncation_tail_bound")
    weak["simulation_only"] = True
    weak["no_roundoff_control"] = True

    rejected = run_pde_rigorous_numerics_certificate_gate(weak)
    assert rejected["passed"] is False
    assert rejected["missing_fields"] == ["truncation_tail_bound"]
    assert rejected["rejected_substitutes"] == [
        "simulation_only",
        "no_roundoff_control",
    ]
