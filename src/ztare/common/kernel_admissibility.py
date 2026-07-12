"""Kernel-change admissibility receipts.

This is the small check behind the "not overfit" line: a kernel change may
compress, route, snapshot, or refine evidence, but it must preserve raw witness
fibers and leave raw gates as the authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SCHEMA = "ztare-kernel-change-admissibility-v1"

CHANGE_CLASSES = {
    "provenance",
    "quotient_compression",
    "abstraction_refinement",
    "gate_tightening",
    "optimization_certificate",
    "evidence_carrier",
}

MATH_ANCHORS = {
    "alpha_gamma",
    "finite_quotient",
    "cegar",
    "bisimulation",
    "mdl",
    "content_addressed_provenance",
    "raw_gate_authority",
}


@dataclass(frozen=True)
class AdmissibilityResult:
    passed: bool
    failures: tuple[str, ...]


def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(str(x).strip() for x in value)


def validate_kernel_change_admissibility(receipt: Any) -> AdmissibilityResult:
    """Validate the declared admissibility surface for a kernel change.

    The validator is intentionally modest. It checks the contract a proposer
    must make explicit; deterministic tests and substrate gates still decide
    whether the code is correct.
    """
    failures: list[str] = []
    if not isinstance(receipt, dict):
        return AdmissibilityResult(False, ("missing_receipt",))

    if receipt.get("schema") != SCHEMA:
        failures.append("bad_schema")

    change_class = str(receipt.get("change_class") or "")
    if change_class not in CHANGE_CLASSES:
        failures.append("bad_change_class")

    anchors = receipt.get("math_anchors")
    if not _nonempty_list(anchors):
        failures.append("missing_math_anchors")
    elif not set(map(str, anchors)) <= MATH_ANCHORS:
        failures.append("unknown_math_anchor")

    if not _nonempty_list(receipt.get("raw_evidence_refs")):
        failures.append("missing_raw_evidence_refs")
    if not _nonempty_list(receipt.get("verification_refs")):
        failures.append("missing_verification_refs")

    if receipt.get("preserves_raw_fiber") is not True:
        failures.append("raw_fiber_not_preserved")
    if receipt.get("candidate_promotion_authority") is not False:
        failures.append("candidate_promotion_authority_not_false")
    if receipt.get("introduces_substrate_specific_rule") is not False:
        failures.append("substrate_specific_rule_not_excluded")

    raw_gate_unchanged = receipt.get("raw_gates_unchanged")
    if change_class == "gate_tightening":
        if receipt.get("gate_tightening_only") is not True:
            failures.append("gate_change_not_declared_tightening")
    elif raw_gate_unchanged is not True:
        failures.append("raw_gates_changed_without_gate_tightening")

    if change_class in {"quotient_compression", "abstraction_refinement"}:
        if not receipt.get("quotient_or_abstraction"):
            failures.append("missing_quotient_or_abstraction")
        if not _nonempty_list(receipt.get("raw_witness_projection")):
            failures.append("missing_raw_witness_projection")

    if change_class == "provenance":
        if not _nonempty_list(receipt.get("content_addressed_refs")):
            failures.append("missing_content_addressed_refs")

    return AdmissibilityResult(not failures, tuple(failures))


def admissibility_payload_for_receipt(
    *,
    change_class: str,
    math_anchors: list[str],
    raw_evidence_refs: list[str],
    verification_refs: list[str],
    quotient_or_abstraction: str = "",
    raw_witness_projection: list[str] | None = None,
    content_addressed_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Build the common pass-case payload for carrier/provenance changes."""
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "change_class": change_class,
        "math_anchors": list(math_anchors),
        "raw_evidence_refs": list(raw_evidence_refs),
        "verification_refs": list(verification_refs),
        "preserves_raw_fiber": True,
        "raw_gates_unchanged": True,
        "candidate_promotion_authority": False,
        "introduces_substrate_specific_rule": False,
    }
    if quotient_or_abstraction:
        payload["quotient_or_abstraction"] = quotient_or_abstraction
    if raw_witness_projection is not None:
        payload["raw_witness_projection"] = list(raw_witness_projection)
    if content_addressed_refs is not None:
        payload["content_addressed_refs"] = list(content_addressed_refs)
    return payload
