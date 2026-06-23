from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ztare.findings.prose_spec import (
    ProseAssertionType,
    ProseSpec,
    ProseSpecAssertion,
    prose_spec_to_dict,
)
from ztare.supervisor.supervisor_state import (
    Actor,
    ArtifactSnapshot,
    HandoffStatus,
    StatusReason,
    SupervisorState,
    TransitionInput,
)
from ztare.supervisor.supervisor_transitions import apply_transition


@dataclass(frozen=True)
class SupervisorFixtureCase:
    case_id: str
    description: str
    status: HandoffStatus
    request: TransitionInput
    expected_state: SupervisorState
    expected_next_actor: Actor
    expected_fail_closed: bool


def _base_status(*, state: SupervisorState, next_actor: Actor) -> HandoffStatus:
    return HandoffStatus(
        run_id="supervisor_fixture",
        revision=1,
        state=state,
        active_program="open_program",
        active_target="target_x",
        last_actor=Actor.SYSTEM,
        next_actor=next_actor,
        status_reason=StatusReason.AWAITING_EVALUATION,
    )


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def build_supervisor_fixture_cases(*, research_spec_path: str) -> list[SupervisorFixtureCase]:
    spec_snapshot = (ArtifactSnapshot(path="spec.md", sha256="spechash"),)
    impl_snapshot = (ArtifactSnapshot(path="src/module.py", sha256="implhash"),)

    a1_status = _base_status(state=SupervisorState.A1, next_actor=Actor.CLAUDE)
    a2_status = HandoffStatus(
        **{
            **a1_status.__dict__,
            "state": SupervisorState.A2,
            "next_actor": Actor.CLAUDE,
            "status_reason": StatusReason.AWAITING_DRAFT,
        }
    )
    b_status = HandoffStatus(
        **{
            **a2_status.__dict__,
            "state": SupervisorState.B,
            "next_actor": Actor.CODEX,
            "status_reason": StatusReason.AWAITING_BUILD,
            "artifact_paths": a2_status.artifact_paths.__class__(spec="spec.md", implementation=("src/module.py",)),
            "spec_snapshot": spec_snapshot,
        }
    )
    c_status = HandoffStatus(
        **{
            **b_status.__dict__,
            "state": SupervisorState.C,
            "next_actor": Actor.VERIFIER,
            "status_reason": StatusReason.AWAITING_VERIFICATION,
            "implementation_snapshot": impl_snapshot,
            "verification_command": "pytest tests/test_supervisor.py",
        }
    )
    research_a2_status = HandoffStatus(
        **{
            **a2_status.__dict__,
            "active_program": "paper4_drafting",
            "active_target": "paper_outline",
            "pipeline_type": "research",
            "debate_file": "[internal-ref]",
            "next_actor": Actor.CODEX,
        }
    )
    research_b_status = HandoffStatus(
        **{
            **research_a2_status.__dict__,
            "state": SupervisorState.B,
            "next_actor": Actor.CLAUDE,
            "status_reason": StatusReason.AWAITING_BUILD,
            "artifact_paths": research_a2_status.artifact_paths.__class__(
                spec=research_spec_path,
                implementation=("research_areas/drafts/paper4_drafting_paper_outline.md",),
            ),
            "spec_snapshot": (
                ArtifactSnapshot(
                    path=research_spec_path,
                    sha256="prosespec",
                ),
            ),
        }
    )
    research_c_status = HandoffStatus(
        **{
            **research_b_status.__dict__,
            "state": SupervisorState.C,
            "next_actor": Actor.VERIFIER,
            "status_reason": StatusReason.AWAITING_VERIFICATION,
            "implementation_snapshot": (
                ArtifactSnapshot(
                    path="research_areas/drafts/paper4_drafting_paper_outline.md",
                    sha256="draftmd",
                ),
            ),
            "verification_command": (
                "python -m src.ztare.findings.prose_verifier "
                "--draft-path research_areas/drafts/paper4_drafting_paper_outline.md "
                "--spec-path research_areas/specs/paper4_drafting_paper_outline_prose_spec.json"
            ),
        }
    )

    closed_a1_status = HandoffStatus(
        **{
            **a1_status.__dict__,
            "active_program": "runner_hardening",
            "closed_programs": ("runner_hardening",),
        }
    )

    return [
        SupervisorFixtureCase(
            case_id="a1_to_a2_open_program",
            description="Open program advances from A1 to A2.",
            status=a1_status,
            request=TransitionInput(
                actor=Actor.CLAUDE,
                expected_revision=1,
                target_state=SupervisorState.A2,
            ),
            expected_state=SupervisorState.A2,
            expected_next_actor=Actor.CLAUDE,
            expected_fail_closed=False,
        ),
        SupervisorFixtureCase(
            case_id="research_a1_to_a2_routes_to_codex_skeptic",
            description="Research pipeline routes A2 to the codex skeptic rather than Claude.",
            status=HandoffStatus(
                **{
                    **a1_status.__dict__,
                    "active_program": "paper4_drafting",
                    "active_target": "paper_outline",
                    "pipeline_type": "research",
                    "debate_file": "[internal-ref]",
                }
            ),
            request=TransitionInput(
                actor=Actor.CLAUDE,
                expected_revision=1,
                target_state=SupervisorState.A2,
            ),
            expected_state=SupervisorState.A2,
            expected_next_actor=Actor.CODEX,
            expected_fail_closed=False,
        ),
        SupervisorFixtureCase(
            case_id="a1_to_d_closed_program_gate",
            description="Closed program reopen attempt fails closed to D.",
            status=closed_a1_status,
            request=TransitionInput(
                actor=Actor.CLAUDE,
                expected_revision=1,
                target_state=SupervisorState.A2,
            ),
            expected_state=SupervisorState.D,
            expected_next_actor=Actor.HUMAN,
            expected_fail_closed=True,
        ),
        SupervisorFixtureCase(
            case_id="a2_to_b_records_spec",
            description="A2 records spec snapshot and expected implementation paths.",
            status=a2_status,
            request=TransitionInput(
                actor=Actor.CLAUDE,
                expected_revision=1,
                target_state=SupervisorState.B,
                spec_path="spec.md",
                expected_implementation_paths=("src/module.py",),
                spec_snapshot=spec_snapshot,
            ),
            expected_state=SupervisorState.B,
            expected_next_actor=Actor.CODEX,
            expected_fail_closed=False,
        ),
        SupervisorFixtureCase(
            case_id="a2_to_a1_spec_refinement",
            description="A2 may request bounded spec refinement back to A1.",
            status=a2_status,
            request=TransitionInput(
                actor=Actor.CLAUDE,
                expected_revision=1,
                target_state=SupervisorState.A1,
                spec_refinement_requested=True,
            ),
            expected_state=SupervisorState.A1,
            expected_next_actor=Actor.CLAUDE,
            expected_fail_closed=False,
        ),
        SupervisorFixtureCase(
            case_id="research_a2_to_a1_returns_to_claude_architect",
            description="Research skeptic refinement returns to the Claude architect.",
            status=research_a2_status,
            request=TransitionInput(
                actor=Actor.CODEX,
                expected_revision=1,
                target_state=SupervisorState.A1,
                spec_refinement_requested=True,
            ),
            expected_state=SupervisorState.A1,
            expected_next_actor=Actor.CLAUDE,
            expected_fail_closed=False,
        ),
        SupervisorFixtureCase(
            case_id="a2_to_d_refinement_cap_gate",
            description="A2 refinement beyond the cap fails closed to D.",
            status=HandoffStatus(
                **{**a2_status.__dict__, "spec_refinement_rounds": 2}
            ),
            request=TransitionInput(
                actor=Actor.CLAUDE,
                expected_revision=1,
                target_state=SupervisorState.A1,
                spec_refinement_requested=True,
            ),
            expected_state=SupervisorState.D,
            expected_next_actor=Actor.HUMAN,
            expected_fail_closed=True,
        ),
        SupervisorFixtureCase(
            case_id="b_to_c_records_impl",
            description="B records implementation snapshot and verifier command.",
            status=b_status,
            request=TransitionInput(
                actor=Actor.CODEX,
                expected_revision=1,
                target_state=SupervisorState.C,
                implementation_paths=("src/module.py",),
                implementation_snapshot=impl_snapshot,
                verification_command="pytest tests/test_supervisor.py",
            ),
            expected_state=SupervisorState.C,
            expected_next_actor=Actor.VERIFIER,
            expected_fail_closed=False,
        ),
        SupervisorFixtureCase(
            case_id="research_a2_to_b_routes_to_claude_writer",
            description="Research pipeline A2 routes B to Claude rather than Codex.",
            status=research_a2_status,
            request=TransitionInput(
                actor=Actor.CODEX,
                expected_revision=1,
                target_state=SupervisorState.B,
                spec_path=research_spec_path,
                expected_implementation_paths=("research_areas/drafts/paper4_drafting_paper_outline.md",),
                spec_snapshot=(
                    ArtifactSnapshot(
                        path=research_spec_path,
                        sha256="prosespec",
                    ),
                ),
            ),
            expected_state=SupervisorState.B,
            expected_next_actor=Actor.CLAUDE,
            expected_fail_closed=False,
        ),
        SupervisorFixtureCase(
            case_id="c_to_b_verifier_fail",
            description="Verifier fail returns to B with retries remaining.",
            status=c_status,
            request=TransitionInput(
                actor=Actor.VERIFIER,
                expected_revision=1,
                target_state=SupervisorState.B,
                verification_passed=False,
                error_report="reports/error.txt",
            ),
            expected_state=SupervisorState.B,
            expected_next_actor=Actor.CODEX,
            expected_fail_closed=False,
        ),
        SupervisorFixtureCase(
            case_id="research_c_to_b_returns_to_claude_writer",
            description="Research verifier fail returns to the Claude writer.",
            status=research_c_status,
            request=TransitionInput(
                actor=Actor.VERIFIER,
                expected_revision=1,
                target_state=SupervisorState.B,
                verification_passed=False,
                error_report="reports/error.txt",
            ),
            expected_state=SupervisorState.B,
            expected_next_actor=Actor.CLAUDE,
            expected_fail_closed=False,
        ),
        SupervisorFixtureCase(
            case_id="c_to_d_mismatch_gate",
            description="Verifier pass without matching implementation snapshot fails closed to D.",
            status=c_status,
            request=TransitionInput(
                actor=Actor.VERIFIER,
                expected_revision=1,
                target_state=SupervisorState.A1,
                verification_passed=True,
                current_implementation_snapshot=(
                    ArtifactSnapshot(path="src/module.py", sha256="otherhash"),
                ),
            ),
            expected_state=SupervisorState.D,
            expected_next_actor=Actor.HUMAN,
            expected_fail_closed=True,
        ),
        SupervisorFixtureCase(
            case_id="unauthorized_repo_write_fails_closed",
            description="Any wrapper-detected write outside the allowed artifact set fails closed to D.",
            status=a1_status,
            request=TransitionInput(
                actor=Actor.CLAUDE,
                expected_revision=1,
                target_state=SupervisorState.A2,
                write_scope_ok=False,
                unauthorized_repo_paths=("src/ztare/validator/hinge_handoff.py",),
            ),
            expected_state=SupervisorState.D,
            expected_next_actor=Actor.HUMAN,
            expected_fail_closed=True,
        ),
        SupervisorFixtureCase(
            case_id="stale_revision_fails_closed",
            description="Stale revision write fails closed to D.",
            status=a1_status,
            request=TransitionInput(
                actor=Actor.CLAUDE,
                expected_revision=0,
                target_state=SupervisorState.A2,
            ),
            expected_state=SupervisorState.D,
            expected_next_actor=Actor.HUMAN,
            expected_fail_closed=True,
        ),
        SupervisorFixtureCase(
            case_id="c_to_d_build_trap",
            description="Third consecutive verifier failure trips implementation trap.",
            status=HandoffStatus(
                **{**c_status.__dict__, "consecutive_build_failures": 2}
            ),
            request=TransitionInput(
                actor=Actor.VERIFIER,
                expected_revision=1,
                target_state=SupervisorState.B,
                verification_passed=False,
                error_report="reports/error.txt",
            ),
            expected_state=SupervisorState.D,
            expected_next_actor=Actor.HUMAN,
            expected_fail_closed=True,
        ),
        SupervisorFixtureCase(
            case_id="c_to_d_terminal_packet_gate",
            description="Verifier pass on a terminal packet routes to human promotion gate.",
            status=HandoffStatus(
                **{**c_status.__dict__, "gate_on_verifier_pass": True}
            ),
            request=TransitionInput(
                actor=Actor.VERIFIER,
                expected_revision=1,
                target_state=SupervisorState.D,
                verification_passed=True,
                verification_report="reports/verification.txt",
                current_implementation_snapshot=impl_snapshot,
            ),
            expected_state=SupervisorState.D,
            expected_next_actor=Actor.HUMAN,
            expected_fail_closed=False,
        ),
    ]


def run_supervisor_fixture_regression() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="supervisor_fixture_") as tmp:
        tmp_path = Path(tmp)
        research_spec_path = str(tmp_path / "paper4_drafting_paper_outline_prose_spec.json")
        _write_json(
            Path(research_spec_path),
            prose_spec_to_dict(
                ProseSpec(
                    packet_id="paper4_drafting_paper_outline",
                    required_headers=("Introduction",),
                    assertions=(
                        ProseSpecAssertion(
                            assertion_id="intro_contains_agency_cost",
                            section_header="Introduction",
                            assertion_type=ProseAssertionType.CONTAINS_PHRASE,
                            target="agency cost",
                        ),
                    ),
                    global_word_min=10,
                    global_word_max=500,
                )
            ),
        )

        cases = build_supervisor_fixture_cases(research_spec_path=research_spec_path)
        results: list[dict[str, object]] = []
        all_passed = True

        for case in cases:
            outcome = apply_transition(case.status, case.request)
            passed = (
                outcome.status.state == case.expected_state
                and outcome.status.next_actor == case.expected_next_actor
                and outcome.fail_closed == case.expected_fail_closed
            )
            if case.case_id.startswith("research_"):
                passed = passed and outcome.status.pipeline_type == "research"
            if case.case_id == "c_to_d_terminal_packet_gate":
                passed = (
                    passed
                    and outcome.status.consecutive_build_failures == 0
                    and outcome.status.artifact_paths.error_report is None
                )
            all_passed = all_passed and passed
            results.append(
                {
                    "case_id": case.case_id,
                    "description": case.description,
                    "expected_state": case.expected_state.value,
                    "actual_state": outcome.status.state.value,
                    "expected_next_actor": case.expected_next_actor.value,
                    "actual_next_actor": outcome.status.next_actor.value,
                    "expected_fail_closed": case.expected_fail_closed,
                    "actual_fail_closed": outcome.fail_closed,
                    "pipeline_type": outcome.status.pipeline_type,
                    "passed": passed,
                    "event_reason": outcome.event.reason,
                }
            )

        return {
            "suite": "supervisor_fixture_regression",
            "all_passed": all_passed,
            "num_cases": len(cases),
            "num_passed": sum(1 for item in results if item["passed"]),
            "results": results,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run supervisor loop Phase 1 fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_supervisor_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Supervisor fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"  {status} {result['case_id']}: expected {result['expected_state']} -> {result['actual_state']}"
        )

    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
