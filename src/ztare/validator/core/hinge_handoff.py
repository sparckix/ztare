from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Optional

from src.ztare.validator.core.primitive_routing import ExploitFamilyTag, derive_exploit_family_tag


class HingeScopeLevel(str, Enum):
    LOCAL_COMPONENT = "LOCAL_COMPONENT"
    WHOLE_SYSTEM = "WHOLE_SYSTEM"
    GENERIC_WEAKEST_POINT = "GENERIC_WEAKEST_POINT"


class ArtifactType(str, Enum):
    LOCAL_CODE = "LOCAL_CODE"
    FROZEN_TEST = "FROZEN_TEST"
    THESIS_PROSE = "THESIS_PROSE"
    UNVERIFIABLE_FUTURE_STATE = "UNVERIFIABLE_FUTURE_STATE"


class HingeAlignmentStatus(str, Enum):
    ALIGNED_SAFE_HARBOR = "ALIGNED_SAFE_HARBOR"
    MISALIGNED_FATAL = "MISALIGNED_FATAL"
    MISALIGNED_OVERCLAIM = "MISALIGNED_OVERCLAIM"
    UNRESOLVED_UNGROUNDED = "UNRESOLVED_UNGROUNDED"


@dataclass(frozen=True)
class HingeGroundingPointer:
    artifact_type: ArtifactType
    artifact_locus: str


@dataclass(frozen=True)
class HingeObject:
    hinge_claim_summary: str
    decisive_variable: str
    decisive_variable_origin: str
    scope_level: HingeScopeLevel
    grounding_pointer: Optional[HingeGroundingPointer]
    direct_test_present: bool
    whole_system_claim_present: bool


@dataclass(frozen=True)
class Stage2Handoff:
    family_tag: ExploitFamilyTag
    hinge: HingeObject
    alignment_status: HingeAlignmentStatus
    provenance_verified: bool
    rationale: str


def evaluate_hinge_grounding(hinge: HingeObject) -> HingeAlignmentStatus:
    if hinge.scope_level == HingeScopeLevel.WHOLE_SYSTEM:
        if hinge.decisive_variable_origin == "thesis-authored":
            return HingeAlignmentStatus.MISALIGNED_FATAL
        if hinge.grounding_pointer and hinge.grounding_pointer.artifact_type in (
            ArtifactType.THESIS_PROSE,
            ArtifactType.UNVERIFIABLE_FUTURE_STATE,
        ):
            return HingeAlignmentStatus.MISALIGNED_FATAL

    if not hinge.grounding_pointer or hinge.grounding_pointer.artifact_locus.strip() == "":
        return HingeAlignmentStatus.UNRESOLVED_UNGROUNDED

    if hinge.grounding_pointer.artifact_type not in (
        ArtifactType.LOCAL_CODE,
        ArtifactType.FROZEN_TEST,
    ):
        return HingeAlignmentStatus.UNRESOLVED_UNGROUNDED

    if hinge.scope_level == HingeScopeLevel.LOCAL_COMPONENT and hinge.whole_system_claim_present:
        return HingeAlignmentStatus.MISALIGNED_OVERCLAIM

    if (
        hinge.scope_level == HingeScopeLevel.LOCAL_COMPONENT
        and hinge.direct_test_present
        and not hinge.whole_system_claim_present
        and hinge.grounding_pointer.artifact_type in (ArtifactType.LOCAL_CODE, ArtifactType.FROZEN_TEST)
    ):
        return HingeAlignmentStatus.ALIGNED_SAFE_HARBOR

    return HingeAlignmentStatus.UNRESOLVED_UNGROUNDED


def build_stage2_handoff(
    thesis_text: str,
    evidence_text: str,
    test_model_text: str = "",
    critiques_text: str = "",
) -> Stage2Handoff:
    family_tag, family_rationale = derive_exploit_family_tag(thesis_text, evidence_text, critiques_text)
    hinge = derive_hinge_object(family_tag, thesis_text, evidence_text, test_model_text)
    alignment_status = evaluate_hinge_grounding(hinge)

    seam_block = _evaluate_seam_gate(family_tag, thesis_text, evidence_text)
    if seam_block is not None:
        return Stage2Handoff(
            family_tag=family_tag,
            hinge=hinge,
            alignment_status=HingeAlignmentStatus.UNRESOLVED_UNGROUNDED,
            provenance_verified=False,
            rationale=f"{family_rationale} | Seam gate fail-closed: {seam_block}.",
        )

    provenance_verified = alignment_status != HingeAlignmentStatus.UNRESOLVED_UNGROUNDED
    rationale = (
        f"{family_rationale} | Stage-2 handoff derived as {alignment_status.value} "
        f"from typed hinge object."
    )
    return Stage2Handoff(
        family_tag=family_tag,
        hinge=hinge,
        alignment_status=alignment_status,
        provenance_verified=provenance_verified,
        rationale=rationale,
    )


def derive_hinge_object(
    family_tag: ExploitFamilyTag,
    thesis_text: str,
    evidence_text: str,
    test_model_text: str = "",
) -> HingeObject:
    normalized = _normalize_text("\n".join(part for part in (thesis_text, evidence_text) if part))
    pointer = _derive_grounding_pointer(test_model_text)
    direct_test_present = _has_direct_test(test_model_text)

    if family_tag == ExploitFamilyTag.SELF_REFERENCE_FUTURE_PREDICTION:
        return HingeObject(
            hinge_claim_summary="Whole-system future prediction with thesis-authored decisive threshold.",
            decisive_variable="thesis_authored_future_threshold",
            decisive_variable_origin="thesis-authored",
            scope_level=HingeScopeLevel.WHOLE_SYSTEM,
            grounding_pointer=HingeGroundingPointer(ArtifactType.UNVERIFIABLE_FUTURE_STATE, ""),
            direct_test_present=direct_test_present,
            whole_system_claim_present=True,
        )

    if family_tag == ExploitFamilyTag.LOCAL_SAFE_HARBOR:
        if pointer is None:
            pointer = HingeGroundingPointer(ArtifactType.THESIS_PROSE, "local-scope disclaimer without executable locus")
        return HingeObject(
            hinge_claim_summary="Bounded local component claim with explicit upstream-disclaimer discipline.",
            decisive_variable="local_component_contract",
            decisive_variable_origin="empirical-data",
            scope_level=HingeScopeLevel.LOCAL_COMPONENT,
            grounding_pointer=pointer,
            direct_test_present=direct_test_present,
            whole_system_claim_present=False,
        )

    if family_tag == ExploitFamilyTag.WHOLE_SYSTEM_OVERCLAIM:
        if pointer is None:
            pointer = HingeGroundingPointer(ArtifactType.THESIS_PROSE, "local mapping overclaim without executable locus")
        return HingeObject(
            hinge_claim_summary="Local mapping presented with whole-system validity language.",
            decisive_variable="local_mapping_contract",
            decisive_variable_origin="empirical-data",
            scope_level=HingeScopeLevel.LOCAL_COMPONENT,
            grounding_pointer=pointer,
            direct_test_present=direct_test_present,
            whole_system_claim_present=True,
        )

    return HingeObject(
        hinge_claim_summary="Generic weakest-point claim without a verified hinge locus.",
        decisive_variable="generic_weakest_point",
        decisive_variable_origin="unknown",
        scope_level=HingeScopeLevel.GENERIC_WEAKEST_POINT,
        grounding_pointer=None,
        direct_test_present=direct_test_present,
        whole_system_claim_present=_contains_any(
            normalized,
            ("whole-system", "whole system", "end-to-end", "end to end"),
        ),
    )


def _derive_grounding_pointer(test_model_text: str) -> Optional[HingeGroundingPointer]:
    if not test_model_text.strip():
        return None

    for pattern in (r"^def\s+([A-Za-z_][A-Za-z0-9_]*)", r"^class\s+([A-Za-z_][A-Za-z0-9_]*)"):
        match = re.search(pattern, test_model_text, re.MULTILINE)
        if match:
            kind = "func" if pattern.startswith("^def") else "class"
            return HingeGroundingPointer(
                ArtifactType.LOCAL_CODE,
                f"{kind}: {match.group(1)}",
            )

    if "assert " in test_model_text:
        return HingeGroundingPointer(ArtifactType.FROZEN_TEST, "assert-based harness")

    return None


def _has_direct_test(test_model_text: str) -> bool:
    return bool(
        test_model_text.strip()
        and (
            "assert " in test_model_text
            or "unittest" in test_model_text
            or "pytest" in test_model_text
        )
    )


def _normalize_text(text: str) -> str:
    return text.lower().replace("**", "").replace("`", "")


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


# Seam gate vocabulary is shared with stage2_derivation.py.
_SEAM_DISCLAIMER_KEYWORDS: tuple[str, ...] = (
    "safe-harbor",
    "safe harbor",
    "local scope",
    "bounded",
    "only affects",
    "does not affect",
)

_SEAM_CONTRADICTION_KEYWORDS: tuple[str, ...] = (
    "propagates",
    "all layers",
    "whole system",
    "whole-system",
    "end-to-end",
    "end to end",
)


def _evaluate_seam_gate(
    family_tag: ExploitFamilyTag,
    thesis_text: str,
    evidence_text: str,
) -> str | None:
    """Return a block-reason string if the derivation should fail closed, else None.

    Mirrors the FABRICATED_SAFE_HARBOR_ANCHOR and CONTRADICTED_SCOPE_DISCLAIMER
    classification logic in stage2_derivation.evaluate_derivation_seam().  The
    stage2_derivation module cannot be imported here without creating a circular
    dependency, so the minimal gate logic is inlined with the same keyword sets.
    """
    normalized_thesis = _normalize_text(thesis_text)
    normalized_evidence = _normalize_text(evidence_text)

    disclaimer_present = _contains_any(normalized_thesis, _SEAM_DISCLAIMER_KEYWORDS)
    contradiction_present = _contains_any(normalized_evidence, _SEAM_CONTRADICTION_KEYWORDS)
    evidence_supports = (
        disclaimer_present
        and _contains_any(normalized_evidence, _SEAM_DISCLAIMER_KEYWORDS)
        and not contradiction_present
    )

    if family_tag == ExploitFamilyTag.LOCAL_SAFE_HARBOR and disclaimer_present and not evidence_supports:
        return "FABRICATED_SAFE_HARBOR_ANCHOR"

    if disclaimer_present and contradiction_present:
        return "CONTRADICTED_SCOPE_DISCLAIMER"

    return None
