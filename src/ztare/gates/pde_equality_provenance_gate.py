"""G-PDE-EQUALITY-PROVENANCE -- block equality laundering.

This gate is for PDE work units whose output is an equality of streams,
charges, carriers, or physical quantities.  It separates a paid equality
from a record field that merely assumes the equality.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-PDE-EQUALITY-PROVENANCE"

REQUIRED_FIELDS = (
    "equality_target",
    "left_stream",
    "right_stream",
    "provenance_kind",
    "constructor_or_theorem",
    "generated_fields",
    "source_binding",
    "anti_proxy_or_anti_laundering_fields",
    "hostile_packet_or_confuser",
    "proof_boundary",
)

REJECTED_SUBSTITUTES = (
    "assumed_record_field_only",
    "field_projection_only",
    "rfl_without_constructor_body",
    "label_match_only",
    "proxy_stream_allowed",
    "posthoc_selection_allowed",
    "same_type_as_same_source",
    "derived_equality_without_source_binding",
)

ACCEPTED_PROVENANCE_KINDS = {
    "constructor_definitional_assignment",
    "theorem_proves_equality_from_source_binding",
    "direct_same_stream_proof",
    "source_binding_isomorphism",
}

BAD_PROVENANCE_KINDS = {
    "assumed_record_field",
    "record_field_projection",
    "field_projection_only",
    "rfl_only",
    "label_match",
}


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


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if value in (None, ""):
        return []
    return [value]


def _as_text_list(value: Any) -> list[str]:
    return [str(item) for item in _as_list(value) if str(item).strip()]


def _constructor_body_supplied(receipt: dict[str, Any]) -> bool:
    assignments = receipt.get("constructor_body_assignments")
    if isinstance(assignments, dict):
        return bool(assignments)
    return bool(_as_text_list(assignments))


def _source_binding_supplied(receipt: dict[str, Any]) -> bool:
    binding = receipt.get("source_binding")
    if isinstance(binding, dict):
        return bool(binding)
    return bool(str(binding or "").strip())


def _next_required_work_units(
    *,
    missing_fields: list[str],
    rejected_substitutes: list[str],
    bad_provenance: bool,
    missing_constructor_body: bool,
) -> list[dict[str, Any]]:
    if not (missing_fields or rejected_substitutes or bad_provenance or missing_constructor_body):
        return []
    blocked_by = {
        "missing_fields": missing_fields,
        "rejected_substitutes": rejected_substitutes,
        "bad_provenance": bad_provenance,
        "missing_constructor_body": missing_constructor_body,
    }
    return [
        {
            "schema": "pde-next-required-work-unit-v1",
            "gate_id": GATE_ID,
            "action": "prove_equality_from_source_constructor",
            "work_unit_type": "estimate_derivation",
            "target": "source_equality_provenance",
            "goal": (
                "replace assumed equality-field projection with constructor "
                "body assignments or a theorem proving the equality from "
                "source binding"
            ),
            "blocked_by": blocked_by,
            "required_gate_ids": [GATE_ID, "G-PDE-PHYSICAL-ACCOUNTING"],
            "must_return": {
                "target_inequality_or_statement": "exact equality statement",
                "proof_steps": (
                    "constructor fields, source binding, anti-proxy fields, "
                    "and hostile packet survived"
                ),
                "first_failed_line_or_success": (
                    "first assumed/field-projected equality or success"
                ),
                "hostile_packet_tested": "proxy stream or record-field laundering packet",
                "currency_exchange_used": "source equality to target equality",
                "verdict": "CLOSE | FAIL | SHRINK | NEED_THEOREM",
            },
        }
    ]


def run_pde_equality_provenance_gate(receipt: dict[str, Any]) -> dict[str, Any]:
    """Validate that an equality is paid by provenance, not only assumed."""
    missing = [
        field for field in REQUIRED_FIELDS
        if not _present(receipt.get(field))
    ]
    rejected = [
        field for field in REJECTED_SUBSTITUTES
        if _present(receipt.get(field))
    ]
    provenance_kind = str(receipt.get("provenance_kind") or "").strip()
    bad_provenance = provenance_kind in BAD_PROVENANCE_KINDS
    accepted_provenance = provenance_kind in ACCEPTED_PROVENANCE_KINDS
    needs_constructor_body = provenance_kind in {
        "constructor_definitional_assignment",
        "source_binding_isomorphism",
    }
    missing_constructor_body = (
        needs_constructor_body and not _constructor_body_supplied(receipt)
    )
    missing_source_binding = not _source_binding_supplied(receipt)
    if missing_source_binding and "source_binding" not in missing:
        missing.append("source_binding")

    violations: list[dict[str, Any]] = []
    if missing:
        violations.append({
            "type": "equality_provenance_missing",
            "missing_fields": missing,
            "reason": (
                "equality work units must expose the target equality, both "
                "streams, constructor/theorem provenance, generated fields, "
                "source binding, anti-proxy fields, hostile packet, and proof boundary"
            ),
        })
    if rejected:
        violations.append({
            "type": "equality_laundering_substitute_rejected",
            "rejected_substitutes": rejected,
            "reason": (
                "assumed record fields, label matches, unproven rfl, proxy "
                "streams, or posthoc selection do not pay equality provenance"
            ),
        })
    if bad_provenance or (provenance_kind and not accepted_provenance):
        violations.append({
            "type": "equality_provenance_kind_rejected",
            "provenance_kind": provenance_kind,
            "accepted": sorted(ACCEPTED_PROVENANCE_KINDS),
            "reason": "provenance kind does not prove the equality from source data",
        })
    if missing_constructor_body:
        violations.append({
            "type": "constructor_body_assignments_missing",
            "reason": (
                "constructor-definitional equality needs explicit assignments "
                "showing how both sides are generated"
            ),
        })

    complete = not missing
    passed = (
        complete
        and not rejected
        and accepted_provenance
        and not bad_provenance
        and not missing_constructor_body
    )
    return {
        "schema": "pde-equality-provenance-gate-v1",
        "gate_id": GATE_ID,
        "label": str(receipt.get("label") or "pde_equality_provenance"),
        "passed": passed,
        "complete": complete,
        "classification": (
            "equality_provenance_paid" if passed
            else "equality_provenance_unpaid"
        ),
        "missing_fields": missing,
        "rejected_substitutes": rejected,
        "provenance_kind": provenance_kind,
        "accepted_provenance": accepted_provenance,
        "constructor_body_assignments_present": _constructor_body_supplied(receipt),
        "source_binding_present": _source_binding_supplied(receipt),
        "violations": violations,
        "next_required_work_units": _next_required_work_units(
            missing_fields=missing,
            rejected_substitutes=rejected,
            bad_provenance=bad_provenance or (provenance_kind and not accepted_provenance),
            missing_constructor_body=missing_constructor_body,
        ),
        "credit_boundary": (
            "passes only equality provenance shape; it does not prove the "
            "PDE constructor exists unless that constructor/theorem is supplied "
            "and separately verified"
        ),
    }
