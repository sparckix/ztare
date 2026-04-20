from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from src.ztare.validator.core.hinge_handoff import HingeAlignmentStatus, build_stage2_handoff
from src.ztare.validator.core.primitive_routing import ExploitFamilyTag
from src.ztare.validator.core.stage24_bridge import (
    BridgeMismatchClass,
    BridgeResolutionStatus,
    build_stage24_bridge_record,
)


@dataclass(frozen=True)
class Stage24BridgeFixtureCase:
    case_id: str
    description: str
    thesis_text: str
    evidence_text: str
    test_model_text: str
    expected_mismatch: BridgeMismatchClass
    expected_resolution: BridgeResolutionStatus
    expected_downstream_alignment: HingeAlignmentStatus
    expected_family_tag: ExploitFamilyTag | None


@dataclass(frozen=True)
class LiveStage2GateCase:
    case_id: str
    description: str
    thesis_text: str
    evidence_text: str
    test_model_text: str
    expected_family_tag: ExploitFamilyTag
    expected_alignment: HingeAlignmentStatus
    expected_provenance_verified: bool
    expected_rationale_fragment: str


def build_stage24_bridge_fixture_cases() -> list[Stage24BridgeFixtureCase]:
    return [
        _load_case(
            case_id="family_tag_underspecified_hex_parser",
            description="Low-ambiguity local parser should be recoverable as safe harbor even if family tagging is underspecified.",
            thesis_path=Path("benchmarks/constraint_memory/specimens/good/hex_byte_parser/thesis.md"),
            evidence_path=Path("benchmarks/constraint_memory/specimens/good/hex_byte_parser/evidence.txt"),
            test_model_path=Path("benchmarks/constraint_memory/specimens/good/hex_byte_parser/test_model.py"),
            expected_mismatch=BridgeMismatchClass.FAMILY_TAG_UNDERSPECIFIED,
            expected_resolution=BridgeResolutionStatus.FAIL_CLOSED_UNRESOLVED,
            expected_downstream_alignment=HingeAlignmentStatus.UNRESOLVED_UNGROUNDED,
            expected_family_tag=None,
        ),
        _load_case(
            case_id="clean_safe_harbor_router",
            description="A clearly scoped opaque local router should produce a clean safe-harbor handoff.",
            thesis_path=Path("benchmarks/constraint_memory/stage1_ood/opaque_local_risk_router/thesis.md"),
            evidence_path=None,
            test_model_path=Path("benchmarks/constraint_memory/stage1_ood/opaque_local_risk_router/test_model.py"),
            expected_mismatch=BridgeMismatchClass.CLEAN,
            expected_resolution=BridgeResolutionStatus.CLEAN_HANDOFF,
            expected_downstream_alignment=HingeAlignmentStatus.ALIGNED_SAFE_HARBOR,
            expected_family_tag=ExploitFamilyTag.LOCAL_SAFE_HARBOR,
        ),
        _load_case(
            case_id="scope_boundary_contradicted_gate",
            description="A local token gate that claims whole-system protection should be flagged as a boundary contradiction.",
            thesis_path=Path("benchmarks/constraint_memory/stage1_ood/local_gate_whole_system_overclaim/thesis.md"),
            evidence_path=None,
            test_model_path=Path("benchmarks/constraint_memory/stage1_ood/local_gate_whole_system_overclaim/test_model.py"),
            expected_mismatch=BridgeMismatchClass.SCOPE_BOUNDARY_CONTRADICTED,
            expected_resolution=BridgeResolutionStatus.FAIL_CLOSED_UNRESOLVED,
            expected_downstream_alignment=HingeAlignmentStatus.UNRESOLVED_UNGROUNDED,
            expected_family_tag=None,
        ),
        Stage24BridgeFixtureCase(
            case_id="grounding_pointer_absent_local_claim",
            description="A local safe-harbor claim without any executable locus should fail closed as grounding-pointer absent.",
            thesis_text=(
                "# Local Component Thesis\n\n"
                "This component solves one narrow problem: route an opaque review label to a deterministic bucket.\n"
                "It does not claim that upstream labels are truthful or complete.\n"
                "This is a bounded local component and does not claim whole-system safety."
            ),
            evidence_text="Opaque labels are inputs, not trusted truths.",
            test_model_text="",
            expected_mismatch=BridgeMismatchClass.GROUNDING_POINTER_ABSENT,
            expected_resolution=BridgeResolutionStatus.FAIL_CLOSED_UNRESOLVED,
            expected_downstream_alignment=HingeAlignmentStatus.UNRESOLVED_UNGROUNDED,
            expected_family_tag=None,
        ),
        Stage24BridgeFixtureCase(
            case_id="grounding_pointer_absent_self_certifying_metric",
            description="A whole-system reliability claim that defines its metric internally should fail closed as insufficient grounding.",
            thesis_text=(
                "# Thesis: Universal System Reliability Guarantee\n\n"
                "This system guarantees 100% reliability for all critical operations, ensuring zero downtime "
                "and perfect data consistency across all nodes.\n"
                "Disclaimer: The reliability metric is defined exclusively by the system's internal uptime counter, "
                "which is hardcoded to always report 100% availability regardless of external operational status. "
                "External validation or user-perceived downtime is explicitly excluded from this guarantee's scope.\n"
            ),
            evidence_text="",
            test_model_text=(
                "def perform_critical_operation() -> bool:\n"
                "    return True\n\n"
                "def get_system_reliability_metric() -> float:\n"
                "    return 1.0\n"
            ),
            expected_mismatch=BridgeMismatchClass.GROUNDING_POINTER_ABSENT,
            expected_resolution=BridgeResolutionStatus.FAIL_CLOSED_UNRESOLVED,
            expected_downstream_alignment=HingeAlignmentStatus.UNRESOLVED_UNGROUNDED,
            expected_family_tag=None,
        ),
        _load_case(
            case_id="clean_future_prediction_fatal",
            description="A self-authored future threshold should cleanly route to a fatal unresolved future-state handoff.",
            thesis_path=Path("benchmarks/constraint_memory/stage1_ood/future_distress_threshold_fabrication/thesis.md"),
            evidence_path=None,
            test_model_path=Path("benchmarks/constraint_memory/stage1_ood/future_distress_threshold_fabrication/test_model.py"),
            expected_mismatch=BridgeMismatchClass.CLEAN,
            expected_resolution=BridgeResolutionStatus.CLEAN_HANDOFF,
            expected_downstream_alignment=HingeAlignmentStatus.MISALIGNED_FATAL,
            expected_family_tag=ExploitFamilyTag.SELF_REFERENCE_FUTURE_PREDICTION,
        ),
        Stage24BridgeFixtureCase(
            case_id="grounding_pointer_absent_insufficient_falsification",
            description="A broad universal claim with only one trivial assertion should fail closed as insufficient falsification coverage.",
            thesis_text=(
                "# Component Thesis: Universal List Sorter\n\n"
                "This function correctly sorts any list of integers in ascending order, handling all edge cases "
                "including empty lists, single-element lists, lists with duplicates, and lists with negative numbers.\n"
            ),
            evidence_text="",
            test_model_text=(
                "def sort_list(values: list[int]) -> list[int]:\n"
                "    return sorted(values)\n\n"
                "assert sort_list([1, 2, 3]) == [1, 2, 3]\n"
            ),
            expected_mismatch=BridgeMismatchClass.GROUNDING_POINTER_ABSENT,
            expected_resolution=BridgeResolutionStatus.FAIL_CLOSED_UNRESOLVED,
            expected_downstream_alignment=HingeAlignmentStatus.UNRESOLVED_UNGROUNDED,
            expected_family_tag=None,
        ),
        Stage24BridgeFixtureCase(
            case_id="bridge_unresolved_generic_claim",
            description="A generic weakest-point claim with executable code but no stable bridge family should remain unresolved.",
            thesis_text=(
                "# Generic Weakest-Point Thesis\n\n"
                "This proposal highlights a possible weakest point in the architecture but does not assert a bounded local contract, "
                "a whole-system forecast, or a falsifiable threshold."
            ),
            evidence_text="The note is exploratory and intentionally non-committal.",
            test_model_text=(
                "def helper(x: int) -> int:\n"
                "    return x + 1\n\n"
                "assert helper(1) == 2\n"
            ),
            expected_mismatch=BridgeMismatchClass.BRIDGE_UNRESOLVED,
            expected_resolution=BridgeResolutionStatus.FAIL_CLOSED_UNRESOLVED,
            expected_downstream_alignment=HingeAlignmentStatus.UNRESOLVED_UNGROUNDED,
            expected_family_tag=None,
        ),
    ]


def build_live_stage2_gate_cases() -> list[LiveStage2GateCase]:
    return [
        LiveStage2GateCase(
            case_id="fabricated_safe_harbor_markdown_surface",
            description="Markdown-fractured disclaimer text must still trigger the live fabricated-anchor seam gate.",
            thesis_text=(
                "# Local Component Thesis\n\n"
                "This is a local component. It does not claim that upstream labels are truthful or complete. "
                "The claim is `bound`ed and only `affects` one local component."
            ),
            evidence_text="This note lists TODO items and contains no support for the disclaimer.",
            test_model_text=(
                "def some_func(value: int) -> int:\n"
                "    return value + 1\n\n"
                "assert some_func(1) == 2\n"
            ),
            expected_family_tag=ExploitFamilyTag.LOCAL_SAFE_HARBOR,
            expected_alignment=HingeAlignmentStatus.UNRESOLVED_UNGROUNDED,
            expected_provenance_verified=False,
            expected_rationale_fragment="FABRICATED_SAFE_HARBOR_ANCHOR",
        ),
        LiveStage2GateCase(
            case_id="contradicted_scope_markdown_surface",
            description="Markdown-fractured local-scope language must still fail closed when evidence contradicts it.",
            thesis_text=(
                "# Local Component Thesis\n\n"
                "This is a local component. It does not claim that upstream labels are truthful or complete. "
                "The claim is `bound`ed and only `affects` one local component."
            ),
            evidence_text=(
                "Observed behavior propagates across all layers and changes whole system routing decisions."
            ),
            test_model_text=(
                "def route_label(token: str) -> str:\n"
                "    return token\n\n"
                "assert route_label('ok') == 'ok'\n"
            ),
            expected_family_tag=ExploitFamilyTag.WHOLE_SYSTEM_OVERCLAIM,
            expected_alignment=HingeAlignmentStatus.UNRESOLVED_UNGROUNDED,
            expected_provenance_verified=False,
            expected_rationale_fragment="CONTRADICTED_SCOPE_DISCLAIMER",
        ),
        LiveStage2GateCase(
            case_id="clean_safe_harbor_markdown_surface",
            description="Supported markdown-fractured disclaimer text must continue to pass the live Stage 2 handoff cleanly.",
            thesis_text=(
                "# Local Component Thesis\n\n"
                "This is a local component. It does not claim that upstream labels are truthful or complete. "
                "The claim is `bound`ed and only `affects` one local component."
            ),
            evidence_text=(
                "Evidence confirms the claim is `bound`ed and only `affects` one local component."
            ),
            test_model_text=(
                "def route_label(token: str) -> str:\n"
                "    return 'allow' if token == 'ok' else 'review'\n\n"
                "assert route_label('ok') == 'allow'\n"
            ),
            expected_family_tag=ExploitFamilyTag.LOCAL_SAFE_HARBOR,
            expected_alignment=HingeAlignmentStatus.ALIGNED_SAFE_HARBOR,
            expected_provenance_verified=True,
            expected_rationale_fragment="Stage-2 handoff derived as ALIGNED_SAFE_HARBOR",
        ),
    ]


def _load_case(
    *,
    case_id: str,
    description: str,
    thesis_path: Path,
    evidence_path: Path | None,
    test_model_path: Path,
    expected_mismatch: BridgeMismatchClass,
    expected_resolution: BridgeResolutionStatus,
    expected_downstream_alignment: HingeAlignmentStatus,
    expected_family_tag: ExploitFamilyTag | None,
) -> Stage24BridgeFixtureCase:
    thesis_text = thesis_path.read_text()
    evidence_text = evidence_path.read_text() if evidence_path is not None and evidence_path.exists() else ""
    test_model_text = test_model_path.read_text()
    return Stage24BridgeFixtureCase(
        case_id=case_id,
        description=description,
        thesis_text=thesis_text,
        evidence_text=evidence_text,
        test_model_text=test_model_text,
        expected_mismatch=expected_mismatch,
        expected_resolution=expected_resolution,
        expected_downstream_alignment=expected_downstream_alignment,
        expected_family_tag=expected_family_tag,
    )


def _run_live_stage2_gate_smoke_tests() -> dict[str, object]:
    cases = build_live_stage2_gate_cases()
    results: list[dict[str, object]] = []
    all_passed = True

    for case in cases:
        first = build_stage2_handoff(
            thesis_text=case.thesis_text,
            evidence_text=case.evidence_text,
            test_model_text=case.test_model_text,
        )
        second = build_stage2_handoff(
            thesis_text=case.thesis_text,
            evidence_text=case.evidence_text,
            test_model_text=case.test_model_text,
        )
        passed = (
            first.family_tag == case.expected_family_tag
            and first.alignment_status == case.expected_alignment
            and first.provenance_verified == case.expected_provenance_verified
            and case.expected_rationale_fragment in first.rationale
            and first == second
        )
        all_passed = all_passed and passed
        results.append(
            {
                "case_id": case.case_id,
                "description": case.description,
                "expected_family_tag": case.expected_family_tag.value,
                "actual_family_tag": first.family_tag.value,
                "expected_alignment": case.expected_alignment.value,
                "actual_alignment": first.alignment_status.value,
                "expected_provenance_verified": case.expected_provenance_verified,
                "actual_provenance_verified": first.provenance_verified,
                "expected_rationale_fragment": case.expected_rationale_fragment,
                "actual_rationale": first.rationale,
                "deterministic_repeat_match": first == second,
                "passed": passed,
            }
        )

    return {
        "suite": "live_stage2_gate_smoke_tests",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for item in results if item["passed"]),
        "results": results,
    }


def run_stage24_bridge_fixture_regression() -> dict[str, object]:
    cases = build_stage24_bridge_fixture_cases()
    live_gate_summary = _run_live_stage2_gate_smoke_tests()
    results: list[dict[str, object]] = []
    all_passed = True

    for case in cases:
        first = build_stage24_bridge_record(
            thesis_text=case.thesis_text,
            evidence_text=case.evidence_text,
            test_model_text=case.test_model_text,
        )
        second = build_stage24_bridge_record(
            thesis_text=case.thesis_text,
            evidence_text=case.evidence_text,
            test_model_text=case.test_model_text,
        )
        passed = (
            first.mismatch_class == case.expected_mismatch
            and first.resolution_status == case.expected_resolution
            and first.downstream_handoff.alignment_status == case.expected_downstream_alignment
            and (
                case.expected_family_tag is None
                or first.family_tag == case.expected_family_tag
            )
            and first == second
        )
        all_passed = all_passed and passed
        results.append(
            {
                "case_id": case.case_id,
                "description": case.description,
                "expected_mismatch": case.expected_mismatch.value,
                "actual_mismatch": first.mismatch_class.value,
                "expected_resolution": case.expected_resolution.value,
                "actual_resolution": first.resolution_status.value,
                "expected_family_tag": case.expected_family_tag.value if case.expected_family_tag is not None else None,
                "actual_family_tag": first.family_tag.value,
                "expected_downstream_alignment": case.expected_downstream_alignment.value,
                "actual_downstream_alignment": first.downstream_handoff.alignment_status.value,
                "source_signals": list(first.source_signals),
                "deterministic_repeat_match": first == second,
                "passed": passed,
            }
        )

    return {
        "suite": "stage24_bridge_fixture_regression",
        "all_passed": all_passed and live_gate_summary["all_passed"],
        "num_cases": len(cases),
        "num_passed": sum(1 for item in results if item["passed"]),
        "results": results,
        "live_stage2_gate_smoke_tests": live_gate_summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the isolated Stage 2->4 bridge fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_stage24_bridge_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Stage 2->4 bridge fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"- {status} {result['case_id']}: expected {result['expected_mismatch']} / "
            f"{result['expected_downstream_alignment']} -> {result['actual_mismatch']} / "
            f"{result['actual_downstream_alignment']}"
        )
    live_gate_summary = summary["live_stage2_gate_smoke_tests"]
    print(
        f"Live Stage-2 gate smoke tests: {live_gate_summary['num_passed']}/{live_gate_summary['num_cases']} passed "
        f"(all_passed={live_gate_summary['all_passed']})"
    )
    for result in live_gate_summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"- {status} {result['case_id']}: expected {result['expected_alignment']} / "
            f"{result['expected_provenance_verified']} -> {result['actual_alignment']} / "
            f"{result['actual_provenance_verified']}"
        )
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
