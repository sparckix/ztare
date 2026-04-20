from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ztare.supervisor.supervisor_state import (
    Actor,
    ArtifactPaths,
    ArtifactSnapshot,
    DeclaredScope,
    HandoffStatus,
    StatusReason,
    SupervisorState,
    TransitionInput,
)
from src.ztare.supervisor.supervisor_staging import (
    build_staging_context,
    build_staging_template,
    staging_filename,
)
from src.ztare.supervisor.supervisor_transitions import apply_transition


def _base_status(*, state: SupervisorState, next_actor: Actor) -> HandoffStatus:
    return HandoffStatus(
        run_id="staging_fixture",
        revision=3,
        state=state,
        active_program="supervisor_loop",
        active_target="phase2_gate",
        debate_file="research_areas/debates/supervisor/supervisor_loop.md",
        debate_last_turn=17,
        owner_mode="debate",
        last_actor=Actor.SYSTEM,
        next_actor=next_actor,
        status_reason=StatusReason.AWAITING_EVALUATION,
    )


def run_supervisor_staging_fixture_regression() -> dict[str, object]:
    staging_dir = Path("/tmp/supervisor_staging_fixture")
    a1_status = _base_status(state=SupervisorState.A1, next_actor=Actor.CLAUDE)
    b_status = _base_status(state=SupervisorState.B, next_actor=Actor.CODEX)
    b_status = HandoffStatus(
        **{
            **b_status.__dict__,
            "active_program": "stage2_derivation_seam_hardening",
            "active_target": "derivation_boundary",
            "debate_file": "research_areas/debates/kernel/stage2_derivation_seam_hardening.md",
            "verification_command": "python -m src.ztare.validator.stage2_derivation_fixture_regression && python -m src.ztare.validator.stage24_bridge_fixture_regression && python -m src.ztare.validator.stage4_fixture_regression",
            "artifact_paths": ArtifactPaths(
                spec="research_areas/debates/kernel/stage2_derivation_seam_hardening.md",
                implementation=(
                    "src/ztare/validator/hinge_handoff.py",
                    "src/ztare/validator/stage2_derivation.py",
                    "src/ztare/validator/stage24_bridge_fixture_regression.py",
                    "src/ztare/validator/stage4_fixture_regression.py",
                ),
            ),
        }
    )
    c_status = HandoffStatus(
        run_id="staging_fixture",
        revision=4,
        state=SupervisorState.C,
        active_program="stage2_derivation_seam_hardening",
        active_target="derivation_boundary",
        debate_file="research_areas/debates/kernel/stage2_derivation_seam_hardening.md",
        debate_last_turn=2,
        owner_mode="debate",
        last_actor=Actor.CODEX,
        next_actor=Actor.VERIFIER,
        status_reason=StatusReason.AWAITING_VERIFICATION,
        artifact_paths=ArtifactPaths(
            spec="research_areas/debates/kernel/stage2_derivation_seam_hardening.md",
            implementation=(
                "src/ztare/validator/stage2_derivation.py",
                "src/ztare/validator/stage2_derivation_fixture_regression.py",
            ),
        ),
        implementation_snapshot=(
            ArtifactSnapshot(
                path="src/ztare/validator/stage2_derivation.py",
                sha256="abc123",
            ),
            ArtifactSnapshot(
                path="src/ztare/validator/stage2_derivation_fixture_regression.py",
                sha256="def456",
            ),
        ),
        verification_command="python -m src.ztare.validator.stage2_derivation_fixture_regression",
    )

    context = build_staging_context(a1_status, staging_dir)
    template = build_staging_template(a1_status)
    a2_status = _base_status(state=SupervisorState.A2, next_actor=Actor.CLAUDE)
    a2_status = HandoffStatus(
        **{
            **a2_status.__dict__,
            "status_reason": StatusReason.AWAITING_DRAFT,
            "spec_refinement_rounds": 1,
            "gate_on_verifier_pass": True,
            "program_cost_usd": 1.75,
            "refinement_cost_usd": 0.5,
            "max_refinement_cost_usd": 2.0,
            "artifact_paths": ArtifactPaths(
                spec="research_areas/debates/kernel/stage2_derivation_seam_hardening.md",
                implementation=(
                    "src/ztare/validator/stage2_derivation.py",
                    "src/ztare/validator/stage2_derivation_fixture_regression.py",
                ),
            ),
        }
    )
    research_a2_status = HandoffStatus(
        **{
            **a2_status.__dict__,
            "active_program": "paper4_drafting",
            "active_target": "paper_outline",
            "pipeline_type": "research",
            "debate_file": "research_areas/private/papers/paper4.md",
            "seed_spec_path": "research_areas/seeds/active/paper4_managerial_capitalism.md",
            "artifact_paths": ArtifactPaths(),
            "next_actor": Actor.CODEX,
        }
    )
    a2_template = build_staging_template(a2_status)
    research_a2_template = build_staging_template(research_a2_status)
    research_context = build_staging_context(research_a2_status, staging_dir)
    b_template = build_staging_template(b_status)
    research_b_status = HandoffStatus(
        **{
            **b_status.__dict__,
            "active_program": "paper4_drafting",
            "active_target": "paper_outline",
            "pipeline_type": "research",
            "debate_file": "research_areas/private/papers/paper4.md",
            "next_actor": Actor.CLAUDE,
            "verification_command": None,
            "artifact_paths": ArtifactPaths(
                spec="research_areas/specs/paper4_drafting_paper_outline_prose_spec.json",
                implementation=("research_areas/drafts/paper4_drafting_paper_outline.md",),
            ),
        }
    )
    research_b_template = build_staging_template(research_b_status)
    verifier_template = build_staging_template(c_status)
    mismatch_request = TransitionInput(
        actor=Actor.CODEX,
        expected_revision=b_status.revision,
        target_state=SupervisorState.C,
        declared_scope=DeclaredScope(
            program_id="runner_hardening",
            target="R4",
        ),
    )

    mismatch_outcome = apply_transition(b_status, mismatch_request)

    results = [
        {
            "case_id": "staging_context_names_claude_a1",
            "passed": context.staging_path.endswith(staging_filename(Actor.CLAUDE, SupervisorState.A1)),
        },
        {
            "case_id": "staging_template_contains_declared_scope",
            "passed": template["declared_scope"]["program_id"] == a1_status.active_program
            and template["declared_scope"]["target"] == a1_status.active_target,
        },
        {
            "case_id": "a2_template_exposes_bounded_refinement_fields",
            "passed": a2_template["spec_refinement_requested"] is False
            and a2_template["gate_on_verifier_pass"] is True
            and a2_template["refinement_rounds_used"] == 1
            and a2_template["max_refinement_rounds"] == 2
            and a2_template["max_refinement_cost_usd"] == 2.0
            and a2_template["spec_path"]
            == "research_areas/debates/kernel/stage2_derivation_seam_hardening.md"
            and a2_template["expected_implementation_paths"]
            == [
                "src/ztare/validator/stage2_derivation.py",
                "src/ztare/validator/stage2_derivation_fixture_regression.py",
            ]
            and context.program_cost_usd == 0.0,
        },
        {
            "case_id": "stage2_context_exposes_exhausted_manifest_summary",
            "passed": (
                build_staging_context(c_status, staging_dir).manifest is not None
                and build_staging_context(c_status, staging_dir).manifest["next_packet"] is None
                and build_staging_context(c_status, staging_dir).manifest["num_complete"] == 3
            ),
        },
        {
            "case_id": "research_a2_template_prefills_prose_spec_and_draft_path",
            "passed": research_a2_template["spec_path"]
            == "research_areas/specs/paper4_drafting_paper_outline_prose_spec.json"
            and research_a2_template["expected_implementation_paths"]
            == ["research_areas/drafts/paper4_drafting_paper_outline.md"],
        },
        {
            "case_id": "research_context_contains_capped_debate_excerpt",
            "passed": research_context.debate_excerpt is not None
            and "Turn" in research_context.debate_excerpt
            and len(research_context.debate_excerpt) <= 8000,
        },
        {
            "case_id": "b_template_prefills_implementation_paths_and_verification_command",
            "passed": b_template["implementation_paths"]
            == [
                "src/ztare/validator/hinge_handoff.py",
                "src/ztare/validator/stage2_derivation.py",
                "src/ztare/validator/stage24_bridge_fixture_regression.py",
                "src/ztare/validator/stage4_fixture_regression.py",
            ]
            and b_template["verification_command"]
            == "python -m src.ztare.validator.stage2_derivation_fixture_regression && python -m src.ztare.validator.stage24_bridge_fixture_regression && python -m src.ztare.validator.stage4_fixture_regression",
        },
        {
            "case_id": "research_b_template_prefills_prose_verification_command",
            "passed": research_b_template["implementation_paths"]
            == ["research_areas/drafts/paper4_drafting_paper_outline.md"]
            and research_b_template["verification_command"]
            == "python -m src.ztare.validator.prose_verifier --draft-path research_areas/drafts/paper4_drafting_paper_outline.md --spec-path research_areas/specs/paper4_drafting_paper_outline_prose_spec.json",
        },
        {
            "case_id": "verifier_template_prefills_current_implementation_snapshot",
            "passed": verifier_template["current_implementation_snapshot"]
            == [
                {"path": "src/ztare/validator/stage2_derivation.py", "sha256": "abc123"},
                {
                    "path": "src/ztare/validator/stage2_derivation_fixture_regression.py",
                    "sha256": "def456",
                },
            ]
            and verifier_template["verification_passed"] is False
            and verifier_template["verification_report"] == "",
        },
        {
            "case_id": "declared_scope_mismatch_fails_closed",
            "passed": mismatch_outcome.fail_closed
            and mismatch_outcome.status.human_gate_reason is not None
            and mismatch_outcome.status.human_gate_reason.value == "scope_mismatch",
        },
    ]
    all_passed = all(item["passed"] for item in results)
    return {
        "suite": "supervisor_staging_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(results),
        "num_passed": sum(1 for item in results if item["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run supervisor staging fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_supervisor_staging_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Supervisor staging fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
