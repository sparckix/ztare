from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.ztare.validator.core.hinge_handoff import (
    HingeAlignmentStatus,
    HingeObject,
    _SEAM_CONTRADICTION_KEYWORDS,
    _SEAM_DISCLAIMER_KEYWORDS,
    _contains_any,
    _normalize_text,
    derive_hinge_object,
    evaluate_hinge_grounding,
)
from src.ztare.validator.core.primitive_routing import ExploitFamilyTag, derive_exploit_family_tag


class DerivationMismatchClass(str, Enum):
    CLEAN = "CLEAN"
    FABRICATED_SAFE_HARBOR_ANCHOR = "FABRICATED_SAFE_HARBOR_ANCHOR"
    CONTRADICTED_SCOPE_DISCLAIMER = "CONTRADICTED_SCOPE_DISCLAIMER"
    GROUNDING_POINTER_ABSENT = "GROUNDING_POINTER_ABSENT"
    UNRESOLVED_GENERIC = "UNRESOLVED_GENERIC"


@dataclass(frozen=True)
class DerivationRecord:
    hinge: HingeObject
    alignment_status: HingeAlignmentStatus
    mismatch_class: DerivationMismatchClass
    disclaimer_found_in_text: bool
    evidence_supports_disclaimer: bool
    grounding_pointer_source: str
    passed: bool


def evaluate_derivation_seam(
    thesis_text: str,
    evidence_text: str,
    test_model_text: str = "",
) -> DerivationRecord:
    family_tag, _ = derive_exploit_family_tag(
        thesis_text=thesis_text,
        evidence_text=evidence_text,
        critiques_text="",
    )
    hinge = derive_hinge_object(
        family_tag=family_tag,
        thesis_text=thesis_text,
        evidence_text=evidence_text,
        test_model_text=test_model_text,
    )
    alignment_status = evaluate_hinge_grounding(hinge)

    disclaimer_found_in_text = _contains_any(_normalize_text(thesis_text), _SEAM_DISCLAIMER_KEYWORDS)
    contradiction_present = _contains_any(_normalize_text(evidence_text), _SEAM_CONTRADICTION_KEYWORDS)
    evidence_supports_disclaimer = (
        disclaimer_found_in_text
        and _contains_any(_normalize_text(evidence_text), _SEAM_DISCLAIMER_KEYWORDS)
        and not contradiction_present
    )

    mismatch_class = _classify_mismatch(
        family_tag=family_tag,
        hinge=hinge,
        disclaimer_found_in_text=disclaimer_found_in_text,
        evidence_supports_disclaimer=evidence_supports_disclaimer,
        contradiction_present=contradiction_present,
    )
    grounding_pointer_source = _grounding_pointer_source(
        hinge=hinge,
        mismatch_class=mismatch_class,
        evidence_supports_disclaimer=evidence_supports_disclaimer,
    )
    return DerivationRecord(
        hinge=hinge,
        alignment_status=alignment_status,
        mismatch_class=mismatch_class,
        disclaimer_found_in_text=disclaimer_found_in_text,
        evidence_supports_disclaimer=evidence_supports_disclaimer,
        grounding_pointer_source=grounding_pointer_source,
        passed=mismatch_class == DerivationMismatchClass.CLEAN,
    )


def _classify_mismatch(
    *,
    family_tag: ExploitFamilyTag,
    hinge: HingeObject,
    disclaimer_found_in_text: bool,
    evidence_supports_disclaimer: bool,
    contradiction_present: bool,
) -> DerivationMismatchClass:
    if (
        family_tag == ExploitFamilyTag.LOCAL_SAFE_HARBOR
        and disclaimer_found_in_text
        and not evidence_supports_disclaimer
    ):
        return DerivationMismatchClass.FABRICATED_SAFE_HARBOR_ANCHOR

    if disclaimer_found_in_text and contradiction_present:
        return DerivationMismatchClass.CONTRADICTED_SCOPE_DISCLAIMER

    if family_tag == ExploitFamilyTag.UNKNOWN and not disclaimer_found_in_text:
        return DerivationMismatchClass.UNRESOLVED_GENERIC

    if not hinge.grounding_pointer or hinge.grounding_pointer.artifact_locus.strip() == "":
        return DerivationMismatchClass.GROUNDING_POINTER_ABSENT

    return DerivationMismatchClass.CLEAN


def _grounding_pointer_source(
    *,
    hinge: HingeObject,
    mismatch_class: DerivationMismatchClass,
    evidence_supports_disclaimer: bool,
) -> str:
    if mismatch_class == DerivationMismatchClass.FABRICATED_SAFE_HARBOR_ANCHOR:
        return "fabricated"
    if not hinge.grounding_pointer or hinge.grounding_pointer.artifact_locus.strip() == "":
        return "absent"
    if evidence_supports_disclaimer and hinge.grounding_pointer.artifact_type.value == "THESIS_PROSE":
        return "evidence"
    return "test_model"
