from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ztare.validator.core.hinge_handoff import (
    ArtifactType,
    HingeAlignmentStatus,
    HingeGroundingPointer,
    HingeObject,
    HingeScopeLevel,
    Stage2Handoff,
)
from ztare.validator.core.primitive_routing import ExploitFamilyTag
from ztare.validator.committees.shadow_board import BoardAssignment, ShadowBoardRole, assign_shadow_board


@dataclass(frozen=True)
class Stage4FixtureCase:
    case_id: str
    description: str
    handoff: Stage2Handoff
    expected_primary: ShadowBoardRole
    expected_secondary: tuple[ShadowBoardRole, ...]


def _handoff(
    *,
    family_tag: ExploitFamilyTag,
    alignment_status: HingeAlignmentStatus,
    scope_level: HingeScopeLevel,
    decisive_variable: str,
    decisive_variable_origin: str,
    direct_test_present: bool,
    whole_system_claim_present: bool,
    artifact_type: ArtifactType | None,
    artifact_locus: str,
    rationale: str,
) -> Stage2Handoff:
    grounding_pointer = None
    if artifact_type is not None:
        grounding_pointer = HingeGroundingPointer(
            artifact_type=artifact_type,
            artifact_locus=artifact_locus,
        )
    hinge = HingeObject(
        hinge_claim_summary=rationale,
        decisive_variable=decisive_variable,
        decisive_variable_origin=decisive_variable_origin,
        scope_level=scope_level,
        grounding_pointer=grounding_pointer,
        direct_test_present=direct_test_present,
        whole_system_claim_present=whole_system_claim_present,
    )
    return Stage2Handoff(
        family_tag=family_tag,
        hinge=hinge,
        alignment_status=alignment_status,
        provenance_verified=alignment_status != HingeAlignmentStatus.UNRESOLVED_UNGROUNDED,
        rationale=rationale,
    )


def build_stage4_fixture_cases() -> list[Stage4FixtureCase]:
    return [
        Stage4FixtureCase(
            case_id="t2_ai_inference",
            description="Whole-system future prediction with thesis-authored decisive threshold.",
            handoff=_handoff(
                family_tag=ExploitFamilyTag.SELF_REFERENCE_FUTURE_PREDICTION,
                alignment_status=HingeAlignmentStatus.MISALIGNED_FATAL,
                scope_level=HingeScopeLevel.WHOLE_SYSTEM,
                decisive_variable="future_distress_threshold",
                decisive_variable_origin="thesis-authored",
                direct_test_present=False,
                whole_system_claim_present=True,
                artifact_type=ArtifactType.UNVERIFIABLE_FUTURE_STATE,
                artifact_locus="",
                rationale="Typed fixture for stage-4 self-reference routing.",
            ),
            expected_primary=ShadowBoardRole.SELF_REFERENCE_AUDITOR,
            expected_secondary=(ShadowBoardRole.MANUAL_REVIEW_ARBITER,),
        ),
        Stage4FixtureCase(
            case_id="future_distress_threshold_fabrication",
            description="OOD self-reference future-threshold fabrication case.",
            handoff=_handoff(
                family_tag=ExploitFamilyTag.SELF_REFERENCE_FUTURE_PREDICTION,
                alignment_status=HingeAlignmentStatus.MISALIGNED_FATAL,
                scope_level=HingeScopeLevel.WHOLE_SYSTEM,
                decisive_variable="fabricated_future_cutoff",
                decisive_variable_origin="thesis-authored",
                direct_test_present=False,
                whole_system_claim_present=True,
                artifact_type=ArtifactType.UNVERIFIABLE_FUTURE_STATE,
                artifact_locus="",
                rationale="OOD fixture for thesis-authored future-threshold routing.",
            ),
            expected_primary=ShadowBoardRole.SELF_REFERENCE_AUDITOR,
            expected_secondary=(ShadowBoardRole.MANUAL_REVIEW_ARBITER,),
        ),
        Stage4FixtureCase(
            case_id="oncology_biomarker_progression_cutoff",
            description="OOD biology-domain future-threshold fabrication case.",
            handoff=_handoff(
                family_tag=ExploitFamilyTag.SELF_REFERENCE_FUTURE_PREDICTION,
                alignment_status=HingeAlignmentStatus.MISALIGNED_FATAL,
                scope_level=HingeScopeLevel.WHOLE_SYSTEM,
                decisive_variable="biomarker_progression_cutoff",
                decisive_variable_origin="thesis-authored",
                direct_test_present=False,
                whole_system_claim_present=True,
                artifact_type=ArtifactType.UNVERIFIABLE_FUTURE_STATE,
                artifact_locus="",
                rationale="OOD fixture for biology-domain future-state self-reference routing.",
            ),
            expected_primary=ShadowBoardRole.SELF_REFERENCE_AUDITOR,
            expected_secondary=(ShadowBoardRole.MANUAL_REVIEW_ARBITER,),
        ),
        Stage4FixtureCase(
            case_id="deterministic_score_contract",
            description="Grounded bounded local score aggregator.",
            handoff=_handoff(
                family_tag=ExploitFamilyTag.LOCAL_SAFE_HARBOR,
                alignment_status=HingeAlignmentStatus.ALIGNED_SAFE_HARBOR,
                scope_level=HingeScopeLevel.LOCAL_COMPONENT,
                decisive_variable="criterion_score_contract",
                decisive_variable_origin="empirical-data",
                direct_test_present=True,
                whole_system_claim_present=False,
                artifact_type=ArtifactType.LOCAL_CODE,
                artifact_locus="func: compute_final_score",
                rationale="Fixture for aligned local safe-harbor routing.",
            ),
            expected_primary=ShadowBoardRole.SAFE_HARBOR_AUDITOR,
            expected_secondary=(ShadowBoardRole.MANUAL_REVIEW_ARBITER,),
        ),
        Stage4FixtureCase(
            case_id="opaque_local_risk_router",
            description="Opaque upstream inputs with bounded local mapping.",
            handoff=_handoff(
                family_tag=ExploitFamilyTag.LOCAL_SAFE_HARBOR,
                alignment_status=HingeAlignmentStatus.ALIGNED_SAFE_HARBOR,
                scope_level=HingeScopeLevel.LOCAL_COMPONENT,
                decisive_variable="received_status_router",
                decisive_variable_origin="empirical-data",
                direct_test_present=True,
                whole_system_claim_present=False,
                artifact_type=ArtifactType.LOCAL_CODE,
                artifact_locus="func: route_status_token",
                rationale="Fixture for bounded local router routing.",
            ),
            expected_primary=ShadowBoardRole.SAFE_HARBOR_AUDITOR,
            expected_secondary=(ShadowBoardRole.MANUAL_REVIEW_ARBITER,),
        ),
        Stage4FixtureCase(
            case_id="hex_byte_parser",
            description="Clean local parser good control.",
            handoff=_handoff(
                family_tag=ExploitFamilyTag.LOCAL_SAFE_HARBOR,
                alignment_status=HingeAlignmentStatus.ALIGNED_SAFE_HARBOR,
                scope_level=HingeScopeLevel.LOCAL_COMPONENT,
                decisive_variable="hex_byte_contract",
                decisive_variable_origin="empirical-data",
                direct_test_present=True,
                whole_system_claim_present=False,
                artifact_type=ArtifactType.LOCAL_CODE,
                artifact_locus="func: parse_hex_byte",
                rationale="Fixture for clean parser safe-harbor routing.",
            ),
            expected_primary=ShadowBoardRole.SAFE_HARBOR_AUDITOR,
            expected_secondary=(ShadowBoardRole.MANUAL_REVIEW_ARBITER,),
        ),
        Stage4FixtureCase(
            case_id="local_gate_whole_system_overclaim",
            description="Local mapping overclaimed as system-wide protection.",
            handoff=_handoff(
                family_tag=ExploitFamilyTag.WHOLE_SYSTEM_OVERCLAIM,
                alignment_status=HingeAlignmentStatus.MISALIGNED_OVERCLAIM,
                scope_level=HingeScopeLevel.LOCAL_COMPONENT,
                decisive_variable="local_guard_contract",
                decisive_variable_origin="empirical-data",
                direct_test_present=True,
                whole_system_claim_present=True,
                artifact_type=ArtifactType.LOCAL_CODE,
                artifact_locus="func: local_guard",
                rationale="Fixture for local-to-system overclaim routing.",
            ),
            expected_primary=ShadowBoardRole.SCOPE_OVERCLAIM_AUDITOR,
            expected_secondary=(ShadowBoardRole.MANUAL_REVIEW_ARBITER,),
        ),
        Stage4FixtureCase(
            case_id="straw_man_design_central_station",
            description="Claim-test mismatch should fail closed to manual review.",
            handoff=_handoff(
                family_tag=ExploitFamilyTag.UNKNOWN,
                alignment_status=HingeAlignmentStatus.UNRESOLVED_UNGROUNDED,
                scope_level=HingeScopeLevel.GENERIC_WEAKEST_POINT,
                decisive_variable="generic_claim_test_mismatch",
                decisive_variable_origin="unknown",
                direct_test_present=False,
                whole_system_claim_present=False,
                artifact_type=None,
                artifact_locus="",
                rationale="Fixture for unknown-family/manual-review routing.",
            ),
            expected_primary=ShadowBoardRole.MANUAL_REVIEW_ARBITER,
            expected_secondary=(),
        ),
    ]


def _serialize_assignment(assignment: BoardAssignment) -> dict[str, object]:
    return {
        "primary": assignment.primary.value,
        "secondary": [role.value for role in assignment.secondary],
        "family_tag": assignment.family_tag.value,
        "hinge_alignment_status": assignment.hinge_alignment_status.value,
        "provenance_verified": assignment.provenance_verified,
        "rationale": assignment.rationale,
    }


def run_stage4_fixture_regression() -> dict[str, object]:
    cases = build_stage4_fixture_cases()
    results: list[dict[str, object]] = []
    all_passed = True

    for case in cases:
        first = assign_shadow_board(case.handoff)
        second = assign_shadow_board(case.handoff)
        passed = (
            first.primary == case.expected_primary
            and first.secondary == case.expected_secondary
            and first == second
        )
        all_passed = all_passed and passed
        results.append(
            {
                "case_id": case.case_id,
                "description": case.description,
                "expected_primary": case.expected_primary.value,
                "expected_secondary": [role.value for role in case.expected_secondary],
                "actual": _serialize_assignment(first),
                "deterministic_repeat_match": first == second,
                "passed": passed,
                "handoff": asdict(case.handoff),
            }
        )

    return {
        "suite": "stage4_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for result in results if result["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the isolated stage-4 typed-handoff fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_stage4_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Stage 4 fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"- {status} {result['case_id']}: expected {result['expected_primary']} -> "
            f"{result['actual']['primary']}"
        )

    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
