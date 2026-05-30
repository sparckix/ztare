"""G-AMBIGUOUS-PI-PINNING - receipt for physically pinning a free pi-group.

`pi_group_forcing` can prove that a target monomial is dimensionally
representable but underdetermined because the chosen source quantities contain
a non-trivial dimensionless group.  This gate checks the next contract: a
caller may spend that ambiguous monomial only after naming a physical or
analytic pinning law fixed before payoff on the same carrier/scope.

The gate is substrate-agnostic.  NS-specific meanings such as Reynolds ratio,
cutoff invoice, or selected owner root belong in the caller payload.
"""
from __future__ import annotations

from typing import Any, Mapping

GATE_ID = "G-AMBIGUOUS-PI-PINNING"
GATE_NAME = "ambiguous_pi_pinning"

_REQUIRED_FIELDS = (
    "physical_pinning_law",
    "pinning_identity_type",
    "source_bound_statement",
    "fixed_before_payoff",
    "same_carrier_or_scope",
    "not_dimensional_analysis_only",
    "consumed_by",
)

_KNOWN_PINNING_TYPES = {
    "active_scale_reynolds",
    "active_scale_reynolds_channel_estimate",
    "energy_identity",
    "coarea_identity",
    "normalization",
    "definition",
    "interpolation",
    "monotonicity_formula",
    "other",
}


def _pi_is_ambiguous(value: Any) -> bool:
    if isinstance(value, Mapping):
        return bool(value.get("ambiguous"))
    return bool(value)


def run_gate(*, pi_group_result: Any = None, ambiguous: bool | None = None,
             receipts: Mapping[str, Any] | None = None,
             label: str | None = None) -> dict[str, Any]:
    """Validate a physical pinning receipt for an ambiguous pi-group.

    If the pi-group is not ambiguous, no pinning receipt is required and the
    gate passes.  If it is ambiguous, every required receipt field must be
    present, and the boolean anti-laundering fields must be exactly true.
    """
    receipts = dict(receipts or {})
    is_ambiguous = _pi_is_ambiguous(pi_group_result)
    if ambiguous is not None:
        is_ambiguous = bool(ambiguous)

    if not is_ambiguous:
        return {
            "gate_id": GATE_ID,
            "gate_name": GATE_NAME,
            "label": label,
            "passed": True,
            "hard_fail": False,
            "ambiguous": False,
            "reason": "pi-group is not ambiguous; no physical pinning receipt required",
            "violations": [],
            "receipts": {field: receipts.get(field) for field in _REQUIRED_FIELDS},
        }

    violations: list[dict[str, Any]] = []
    missing = [field for field in _REQUIRED_FIELDS if receipts.get(field) in (None, "", [], {})]
    if missing:
        violations.append({"type": "missing_pi_pinning_receipts", "missing_fields": missing})

    bool_fields = ("fixed_before_payoff", "same_carrier_or_scope", "not_dimensional_analysis_only")
    false_fields = [field for field in bool_fields if receipts.get(field) is not True]
    if false_fields:
        violations.append({"type": "pi_pinning_receipt_false_or_unpaid", "fields": false_fields})

    identity_type = str(receipts.get("pinning_identity_type") or "").strip().lower().replace("-", "_")
    if identity_type and identity_type not in _KNOWN_PINNING_TYPES:
        violations.append({
            "type": "unknown_pinning_identity_type",
            "pinning_identity_type": receipts.get("pinning_identity_type"),
        })

    passed = not violations
    return {
        "gate_id": GATE_ID,
        "gate_name": GATE_NAME,
        "label": label,
        "passed": passed,
        "hard_fail": not passed,
        "ambiguous": True,
        "receipts": {field: receipts.get(field) for field in _REQUIRED_FIELDS},
        "violations": violations,
        "reason": (
            "ambiguous pi-group is backed by a physical/source pinning receipt"
            if passed else
            "ambiguous pi-group cannot be spent from dimensional analysis alone"
        ),
    }


def format_report(result: Mapping[str, Any]) -> str:
    status = "PASS" if result.get("passed") else "FAIL"
    label = result.get("label") or GATE_ID
    return f"{status} {label}: {result.get('reason')}"
