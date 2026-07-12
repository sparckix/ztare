"""Gate for rigorous-numerics PDE certificate receipts.

The gate does not verify a numerical proof. It enforces the minimum receipt
shape needed before a PDE leaf may treat validated numerics as a certificate
lane rather than an empirical simulation.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-PDE-RIGOROUS-NUMERICS"

REQUIRED_FIELDS = (
    "certificate_type",
    "pde_problem_statement",
    "discretization_or_basis",
    "interval_arithmetic_or_bounds",
    "residual_bound",
    "truncation_tail_bound",
    "a_posteriori_argument",
    "reproducibility_artifact",
    "validator",
    "theorem_linkage",
    "hostile_packet_or_failure_mode",
)

REJECTED_SUBSTITUTES = (
    "floating_point_sample_only",
    "plot_only",
    "simulation_only",
    "no_roundoff_control",
    "no_truncation_tail_bound",
    "unverifiable_code_pointer",
    "empirical_stability_as_proof",
    "mesh_refinement_label_only",
)


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def run_pde_rigorous_numerics_certificate_gate(
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """Check that a rigorous-numerics PDE certificate exposes core evidence."""
    missing = [
        field for field in REQUIRED_FIELDS
        if not _present(receipt.get(field))
    ]
    rejected = [
        field for field in REJECTED_SUBSTITUTES
        if _present(receipt.get(field))
    ]
    complete = not missing
    passed = complete and not rejected
    classification = (
        "rigorous_numerics_certificate_paid"
        if passed else "rigorous_numerics_certificate_unpaid"
    )
    return {
        "schema": "pde-rigorous-numerics-certificate-gate-v1",
        "gate_id": GATE_ID,
        "label": str(receipt.get("label") or "pde_rigorous_numerics_certificate"),
        "passed": passed,
        "complete": complete,
        "classification": classification,
        "missing_fields": missing,
        "rejected_substitutes": rejected,
        "required_fields": list(REQUIRED_FIELDS),
        "required_before_credit": [
            "roundoff/enclosure control",
            "residual bound",
            "truncation or tail bound",
            "a posteriori argument",
            "reproducible validator artifact",
            "theorem linkage explaining what the certificate proves",
        ],
        "credit_boundary": (
            "certificate_shape_only; independent validator and theorem linkage "
            "must be checked before proof or estimate credit"
        ),
    }
