from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ztare.validator.committees.committee_instantiation import (
    instantiate_fixed_committee,
    record_to_dict,
)
from ztare.validator.core.hinge_handoff import (
    HingeAlignmentStatus,
    Stage2Handoff,
    build_stage2_handoff,
)
from ztare.validator.core.primitive_routing import ExploitFamilyTag


class ShadowBoardRole(str, Enum):
    SELF_REFERENCE_AUDITOR = "SELF_REFERENCE_AUDITOR"
    SAFE_HARBOR_AUDITOR = "SAFE_HARBOR_AUDITOR"
    SCOPE_OVERCLAIM_AUDITOR = "SCOPE_OVERCLAIM_AUDITOR"
    MANUAL_REVIEW_ARBITER = "MANUAL_REVIEW_ARBITER"


@dataclass(frozen=True)
class BoardAssignment:
    primary: ShadowBoardRole
    secondary: tuple[ShadowBoardRole, ...]
    family_tag: ExploitFamilyTag
    hinge_alignment_status: HingeAlignmentStatus
    provenance_verified: bool
    rationale: str


ROLE_DEFINITIONS: dict[ShadowBoardRole, dict[str, str]] = {
    ShadowBoardRole.SELF_REFERENCE_AUDITOR: {
        "role": "SELF_REFERENCE_AUDITOR",
        "persona": (
            "You attack self-certifying future-state reasoning. You look for thesis-authored decisive "
            "variables, thesis-authored thresholds, non-independent falsification, and arithmetic that "
            "only revalidates the thesis's own future claim."
        ),
        "focus_area": (
            "Identify whether the decisive future-state claim is being re-proved with thesis-authored "
            "variables or thresholds rather than independently falsified."
        ),
    },
    ShadowBoardRole.SAFE_HARBOR_AUDITOR: {
        "role": "SAFE_HARBOR_AUDITOR",
        "persona": (
            "You audit bounded local components. You do not attack upstream truthfulness directly unless "
            "the thesis overclaims. You look for claim-scope mismatch, missing local fail-closed behavior, "
            "and places where the local mechanism fails its own narrow contract."
        ),
        "focus_area": (
            "Verify that the thesis is truly a bounded local mapping, that its disclaimers are honored by "
            "the mechanism, and that its own local contract is exhaustively tested."
        ),
    },
    ShadowBoardRole.SCOPE_OVERCLAIM_AUDITOR: {
        "role": "SCOPE_OVERCLAIM_AUDITOR",
        "persona": (
            "You attack local mappings that are being smuggled into end-to-end guarantees. You look for "
            "language that overclaims exhaustiveness, infallibility, or system-level protection beyond what "
            "the code actually proves."
        ),
        "focus_area": (
            "Find any point where a bounded component is presented as proving whole-system validity, "
            "coverage, completeness, or silent-failure impossibility."
        ),
    },
    ShadowBoardRole.MANUAL_REVIEW_ARBITER: {
        "role": "MANUAL_REVIEW_ARBITER",
        "persona": (
            "You are the conservative fallback. When the family is unknown or the primary auditor's framing "
            "looks unstable, you surface ambiguity instead of inventing confidence."
        ),
        "focus_area": (
            "Identify ambiguity, missing classification support, or places where the current taxonomy should "
            "fail closed rather than guess."
        ),
    },
}

ROLE_DEFINITIONS_BY_KEY = {role.value: definition for role, definition in ROLE_DEFINITIONS.items()}


def assign_shadow_board(handoff: Stage2Handoff) -> BoardAssignment:
    if handoff.alignment_status == HingeAlignmentStatus.MISALIGNED_FATAL:
        return BoardAssignment(
            primary=ShadowBoardRole.SELF_REFERENCE_AUDITOR,
            secondary=(ShadowBoardRole.MANUAL_REVIEW_ARBITER,),
            family_tag=handoff.family_tag,
            hinge_alignment_status=handoff.alignment_status,
            provenance_verified=handoff.provenance_verified,
            rationale=(
                "Typed hinge handoff identified a fatal self-reference / unverifiable future-state "
                "claim, so self-reference auditing is activated with arbiter fallback."
            ),
        )
    if handoff.alignment_status == HingeAlignmentStatus.ALIGNED_SAFE_HARBOR:
        return BoardAssignment(
            primary=ShadowBoardRole.SAFE_HARBOR_AUDITOR,
            secondary=(ShadowBoardRole.MANUAL_REVIEW_ARBITER,),
            family_tag=handoff.family_tag,
            hinge_alignment_status=handoff.alignment_status,
            provenance_verified=handoff.provenance_verified,
            rationale=(
                "Typed hinge handoff verified a grounded local safe-harbor claim, so bounded "
                "local-contract auditing is activated with reserve arbiter coverage."
            ),
        )
    if handoff.alignment_status == HingeAlignmentStatus.MISALIGNED_OVERCLAIM:
        return BoardAssignment(
            primary=ShadowBoardRole.SCOPE_OVERCLAIM_AUDITOR,
            secondary=(ShadowBoardRole.MANUAL_REVIEW_ARBITER,),
            family_tag=handoff.family_tag,
            hinge_alignment_status=handoff.alignment_status,
            provenance_verified=handoff.provenance_verified,
            rationale=(
                "Typed hinge handoff identified a local-to-system overclaim, so scope-discipline "
                "auditing is activated with arbiter fallback."
            ),
        )
    return BoardAssignment(
        primary=ShadowBoardRole.MANUAL_REVIEW_ARBITER,
        secondary=(),
        family_tag=handoff.family_tag,
        hinge_alignment_status=handoff.alignment_status,
        provenance_verified=handoff.provenance_verified,
        rationale=(
            "Typed hinge handoff is unresolved or ungrounded, so the board fails closed to "
            "arbiter-only review."
        ),
    )


def build_shadow_board_committee(
    thesis_text: str,
    evidence_text: str,
    test_model_text: str = "",
    critiques_text: str = "",
) -> dict:
    handoff = build_stage2_handoff(
        thesis_text=thesis_text,
        evidence_text=evidence_text,
        test_model_text=test_model_text,
        critiques_text=critiques_text,
    )
    assignment = assign_shadow_board(handoff)

    roles = (assignment.primary,) + assignment.secondary
    committee, instantiation_record = instantiate_fixed_committee(
        profile_source="shadow_board_fixed_catalog_v1",
        role_keys=tuple(role.value for role in roles),
        role_definitions=ROLE_DEFINITIONS_BY_KEY,
    )
    metadata = {
        "family_tag": handoff.family_tag.value,
        "primary_role": assignment.primary.value,
        "secondary_roles": [role.value for role in assignment.secondary],
        "hinge_alignment_status": handoff.alignment_status.value,
        "provenance_verified": handoff.provenance_verified,
        "hinge_scope_level": handoff.hinge.scope_level.value,
        "grounding_pointer_type": (
            handoff.hinge.grounding_pointer.artifact_type.value
            if handoff.hinge.grounding_pointer
            else None
        ),
        "grounding_pointer_locus": (
            handoff.hinge.grounding_pointer.artifact_locus
            if handoff.hinge.grounding_pointer
            else ""
        ),
        "handoff_rationale": handoff.rationale,
        "assignment_rationale": assignment.rationale,
        "instantiation_record": record_to_dict(instantiation_record),
    }
    return {"committee": committee, "metadata": metadata}
