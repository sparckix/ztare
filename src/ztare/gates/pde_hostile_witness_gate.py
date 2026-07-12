"""Gate for PDE hostile/sharpness witness receipts.

This is the generic `pec_e` gate. It checks that a claimed hostile packet or
sharpness example has enough structure to stress an estimate, without deciding
whether the construction is mathematically decisive.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-PDE-HOSTILE-WITNESS"

REQUIRED_FIELDS = (
    "witness_family",
    "target_estimate_or_claim",
    "amplitude_scaling",
    "support_or_localization",
    "frequency_or_scale_regime",
    "norm_or_quantity_profile",
    "hypotheses_preserved",
    "conclusion_stressed_or_violated",
    "failure_mechanism",
    "parameter_limit",
    "claim_boundary_update",
)

WEAK_SUBSTITUTES = (
    "counterexample_label_only",
    "generic_spike_without_scaling",
    "hypotheses_not_checked",
    "conclusion_not_evaluated",
    "wrong_carrier_witness",
    "post_selected_witness",
    "analogy_only",
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


def run_pde_hostile_witness_gate(receipt: dict[str, Any]) -> dict[str, Any]:
    """Validate the receipt shape for a PDE hostile/sharpness witness."""
    missing = [
        field for field in REQUIRED_FIELDS
        if not _present(receipt.get(field))
    ]
    weak = [
        field for field in WEAK_SUBSTITUTES
        if _present(receipt.get(field))
    ]
    complete = not missing
    passed = complete and not weak
    classification = (
        "hostile_witness_receipt_complete"
        if passed else "hostile_witness_receipt_incomplete"
    )
    return {
        "schema": "pde-hostile-witness-gate-v1",
        "gate_id": GATE_ID,
        "label": str(receipt.get("label") or "pde_hostile_witness"),
        "passed": passed,
        "complete": complete,
        "classification": classification,
        "missing_fields": missing,
        "rejected_substitutes": weak,
        "required_fields": list(REQUIRED_FIELDS),
        "required_before_credit": [
            "family parameters and scaling",
            "support/localization and frequency regime",
            "norm/quantity profile",
            "hypotheses-preserved check",
            "conclusion stress or violation check",
            "boundary update explaining which claim survived or died",
        ],
        "credit_boundary": (
            "receipt_shape_only; estimate gates or theorem profiles decide "
            "whether the witness kills the target"
        ),
    }
