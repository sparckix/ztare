from __future__ import annotations

import json
from pathlib import Path
import tempfile

from ztare.supervisor.supervisor_attended_autoloop import (
    _commit_preview,
    _effective_token_limits,
    _pending_request_paths,
    decide_commit_action,
    fresh_input_tokens,
    format_turn_cost_label,
)
from ztare.supervisor.supervisor_state import (
    Actor,
    ArtifactPaths,
    DeclaredScope,
    HandoffEvent,
    HandoffStatus,
    StatusReason,
    SupervisorState,
    TransitionOutcome,
    TransitionInput,
    TurnUsageTelemetry,
)
from ztare.supervisor.supervisor_wrappers import WrapperLaunchResult, WrapperMode


def _status(*, state: SupervisorState, next_actor: Actor) -> HandoffStatus:
    return HandoffStatus(
        run_id="fixture",
        revision=1,
        state=state,
        active_program="stage2_derivation_seam_hardening",
        active_target="derivation_boundary",
        last_actor=Actor.CLAUDE,
        next_actor=next_actor,
        status_reason=StatusReason.AWAITING_BUILD,
    )


def _outcome(*, next_state: SupervisorState, fail_closed: bool = False) -> TransitionOutcome:
    status = _status(state=next_state, next_actor=Actor.CODEX if next_state == SupervisorState.B else Actor.HUMAN)
    event = HandoffEvent(
        revision=2,
        actor=Actor.CLAUDE,
        prior_state=SupervisorState.A2,
        new_state=next_state,
        reason="fixture",
        timestamp="2026-04-06T00:00:00Z",
    )
    return TransitionOutcome(status=status, event=event, fail_closed=fail_closed)


def _launch_result(
    *,
    exit_code: int | None = 0,
    unauthorized_repo_paths: tuple[str, ...] = (),
    telemetry: TurnUsageTelemetry | None = None,
    output_envelope_exceeded: bool = False,
    mode: WrapperMode = WrapperMode.EXTERNAL_AGENT,
) -> WrapperLaunchResult:
    return WrapperLaunchResult(
        actor=Actor.CODEX,
        mode=mode,
        executed=True,
        command=("codex", "exec"),
        prompt_path="prompt.txt",
        debug_path="debug.log",
        stdout_path="stdout.txt",
        stderr_path="stderr.txt",
        report_path=None,
        usage_path="usage.json",
        modified_repo_paths=unauthorized_repo_paths,
        unauthorized_repo_paths=unauthorized_repo_paths,
        output_envelope_exceeded=output_envelope_exceeded,
        turn_usage=telemetry,
        exit_code=exit_code,
    )


def run_supervisor_attended_autoloop_fixture_regression() -> dict[str, object]:
    results: list[dict[str, object]] = []

    decision = decide_commit_action(
        auto_commit=False,
        launch_result=_launch_result(),
        preview_outcome=_outcome(next_state=SupervisorState.B),
    )
    results.append(
        {
            "name": "manual_mode_stops_for_commit",
            "passed": (not decision.should_commit and decision.requires_manual_commit),
        }
    )

    decision = decide_commit_action(
        auto_commit=True,
        launch_result=_launch_result(),
        preview_outcome=_outcome(next_state=SupervisorState.D),
    )
    results.append(
        {
            "name": "target_D_requires_manual_commit",
            "passed": (not decision.should_commit and decision.stop_reason == "target_state_D_requires_manual_commit"),
        }
    )

    decision = decide_commit_action(
        auto_commit=True,
        launch_result=_launch_result(unauthorized_repo_paths=("supervisor/program_registry.json",)),
        preview_outcome=_outcome(next_state=SupervisorState.C),
    )
    results.append(
        {
            "name": "unauthorized_write_blocks_autocommit",
            "passed": (not decision.should_commit and decision.stop_reason == "unauthorized_repo_write"),
        }
    )

    decision = decide_commit_action(
        auto_commit=True,
        launch_result=_launch_result(),
        preview_outcome=_outcome(next_state=SupervisorState.D, fail_closed=True),
    )
    results.append(
        {
            "name": "fail_closed_preview_blocks_autocommit",
            "passed": (not decision.should_commit and decision.stop_reason == "preview_fail_closed"),
        }
    )

    results.append(
        {
            "name": "exact_mode_cost_label_is_explicit",
            "passed": (
                format_turn_cost_label(
                    TurnUsageTelemetry(
                        model_name=None,
                        input_tokens=10,
                        output_tokens=20,
                        estimated_cost_usd=0.0,
                        telemetry_captured=True,
                    )
                )
                == "unpriced_exact_mode"
            ),
        }
    )

    results.append(
        {
            "name": "auto_commit_happy_path_allowed",
            "passed": decide_commit_action(
                auto_commit=True,
                launch_result=_launch_result(),
                preview_outcome=_outcome(next_state=SupervisorState.C),
            ).should_commit,
        }
    )

    results.append(
        {
            "name": "fresh_input_tokens_handles_cached_and_uncached_shapes",
            "passed": (
                fresh_input_tokens(
                    TurnUsageTelemetry(
                        model_name="claude-sonnet-4-6",
                        input_tokens=7,
                        output_tokens=10,
                        cache_creation_input_tokens=15811,
                        cache_read_input_tokens=125152,
                        estimated_cost_usd=0.1,
                        telemetry_captured=True,
                    )
                )
                == 15818
                and fresh_input_tokens(
                    TurnUsageTelemetry(
                        model_name=None,
                        input_tokens=345708,
                        output_tokens=100,
                        cache_creation_input_tokens=0,
                        cache_read_input_tokens=317184,
                        estimated_cost_usd=0.0,
                        telemetry_captured=True,
                    )
                )
                == 28524
            ),
        }
    )

    decision = decide_commit_action(
        auto_commit=True,
        launch_result=_launch_result(
            telemetry=TurnUsageTelemetry(
                model_name=None,
                input_tokens=345708,
                output_tokens=100,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=317184,
                estimated_cost_usd=0.0,
                telemetry_captured=True,
            )
        ),
        preview_outcome=_outcome(next_state=SupervisorState.C),
        max_fresh_input_tokens=20000,
    )
    results.append(
        {
            "name": "fresh_input_threshold_blocks_autocommit",
            "passed": (
                not decision.should_commit
                and decision.stop_reason == "fresh_input_tokens_limit_exceeded"
                and decision.requires_manual_commit
            ),
        }
    )

    decision = decide_commit_action(
        auto_commit=True,
        launch_result=_launch_result(output_envelope_exceeded=True),
        preview_outcome=_outcome(next_state=SupervisorState.B),
    )
    results.append(
        {
            "name": "output_envelope_exceeded_blocks_autocommit_without_manual_commit",
            "passed": (
                not decision.should_commit
                and decision.stop_reason == "output_envelope_exceeded"
                and not decision.requires_manual_commit
            ),
        }
    )

    decision = decide_commit_action(
        auto_commit=True,
        launch_result=_launch_result(exit_code=1),
        preview_outcome=_outcome(next_state=SupervisorState.B),
    )
    results.append(
        {
            "name": "launch_exit_nonzero_blocks_before_preview_commit",
            "passed": (
                not decision.should_commit
                and decision.stop_reason == "launch_exit_nonzero"
                and not decision.requires_manual_commit
            ),
        }
    )

    decision = decide_commit_action(
        auto_commit=True,
        launch_result=_launch_result(exit_code=1, mode=WrapperMode.LOCAL_VERIFIER),
        preview_outcome=_outcome(next_state=SupervisorState.B),
    )
    results.append(
        {
            "name": "local_verifier_exit_nonzero_still_allows_preview_commit",
            "passed": decision.should_commit,
        }
    )

    decision = decide_commit_action(
        auto_commit=True,
        launch_result=_launch_result(
            telemetry=TurnUsageTelemetry(
                model_name=None,
                input_tokens=100,
                output_tokens=16001,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
                estimated_cost_usd=0.0,
                telemetry_captured=True,
            )
        ),
        preview_outcome=_outcome(next_state=SupervisorState.C),
        max_output_tokens=16000,
    )
    results.append(
        {
            "name": "output_threshold_blocks_autocommit",
            "passed": (
                not decision.should_commit
                and decision.stop_reason == "output_tokens_limit_exceeded"
                and decision.requires_manual_commit
            ),
        }
    )

    research_a2_status = HandoffStatus(
        **{
            **_status(state=SupervisorState.A2, next_actor=Actor.CODEX).__dict__,
            "active_program": "paper4_manuscript",
            "active_target": "manuscript_theory_foundations",
            "pipeline_type": "research",
            "artifact_paths": ArtifactPaths(
                spec="research_areas/specs/paper4_manuscript_manuscript_theory_foundations_prose_spec.json",
                implementation=("research_areas/drafts/paper4_manuscript/02a_theory_foundations.md",),
            ),
        }
    )
    original_manifest_loader = __import__(
        "src.ztare.supervisor.supervisor_attended_autoloop", fromlist=["load_optional_program_manifest"]
    ).load_optional_program_manifest
    import ztare.supervisor.supervisor_attended_autoloop as autoloop_module
    from ztare.supervisor.supervisor_manifest import ManifestPacket, ManifestPacketStatus, ProgramManifest

    autoloop_module.load_optional_program_manifest = lambda _program_id: ProgramManifest(
        program_id="paper4_manuscript",
        completion_policy="manifest_exhausted_to_D",
        packets=(
            ManifestPacket(
                packet_id="manuscript_theory_foundations",
                title="Theory Foundations",
                status=ManifestPacketStatus.PENDING,
                target="manuscript_theory_foundations",
                summary="theory fragment",
                allowed_artifacts=("research_areas/drafts/paper4_manuscript/02a_theory_foundations.md",),
                token_budget={"a2_max_output": 2500, "a2_max_fresh_input": 15000},
            ),
        ),
    )
    try:
        a2_limits = _effective_token_limits(
            status=research_a2_status,
            max_output_tokens=9000,
            max_fresh_input_tokens=25000,
        )
        a1_limits = _effective_token_limits(
            status=HandoffStatus(
                **{
                    **research_a2_status.__dict__,
                    "state": SupervisorState.A1,
                    "next_actor": Actor.CLAUDE,
                }
            ),
            max_output_tokens=9000,
            max_fresh_input_tokens=25000,
        )
        case_packet_budget_scope_passed = a2_limits == (2500, 15000) and a1_limits == (9000, 25000)
    finally:
        autoloop_module.load_optional_program_manifest = original_manifest_loader
    results.append(
        {
            "name": "packet_budget_applies_only_to_research_a2",
            "passed": case_packet_budget_scope_passed,
        }
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        status_path = tmp / "status.json"
        events_path = tmp / "events.jsonl"
        staging_dir = tmp / "staging"
        staging_dir.mkdir()
        request_path = staging_dir / "claude_a1.json"
        request_path.write_text("{}")
        request = TransitionInput(
            actor=Actor.CLAUDE,
            expected_revision=1,
            target_state=SupervisorState.A2,
            declared_scope=DeclaredScope(program_id="stage2_derivation_seam_hardening", target="derivation_boundary"),
            note="fixture",
        )
        preview = _outcome(next_state=SupervisorState.A2)
        try:
            new_status, archived_path = _commit_preview(
                status=_status(state=SupervisorState.A1, next_actor=Actor.CLAUDE),
                request=request,
                preview_outcome=preview,
                status_path=status_path,
                events_path=events_path,
                staging_dir=staging_dir,
                request_path=request_path,
            )
            passed = new_status.state == SupervisorState.A2 and archived_path.exists() and events_path.exists()
        except TypeError:
            passed = False
        results.append(
            {
                "name": "commit_preview_passes_prior_state_and_archives_request",
                "passed": passed,
            }
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        staging_dir = tmp / "staging"
        staging_dir.mkdir()
        (staging_dir / "claude_a1_context.json").write_text("{}")
        (staging_dir / "claude_a1.json").write_text(json.dumps({"turn_usage": {"input_tokens": 1}}))
        (staging_dir / "codex_a2.json").write_text(json.dumps({"write_scope_ok": False}))
        pending = _pending_request_paths(staging_dir)
        results.append(
            {
                "name": "pending_request_guard_ignores_context_and_finds_requests",
                "passed": tuple(path.name for path in pending) == ("claude_a1.json", "codex_a2.json"),
            }
        )

    all_passed = all(item["passed"] for item in results)
    return {
        "suite": "supervisor_attended_autoloop_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(results),
        "num_passed": sum(1 for item in results if item["passed"]),
        "results": results,
    }


def main() -> int:
    summary = run_supervisor_attended_autoloop_fixture_regression()
    print(
        f"Supervisor attended autoloop fixture regression: "
        f"{summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['name']}")
    print(json.dumps(summary, indent=2))
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
