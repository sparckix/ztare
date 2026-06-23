from __future__ import annotations

import argparse
import io
import json
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

import ztare.supervisor.supervisor_program_autoloop as program_autoloop_module
from ztare.supervisor.supervisor_manifest import ManifestPacket, ManifestPacketStatus, ProgramManifest
from ztare.supervisor.supervisor_registry import registry_path
from ztare.supervisor.supervisor_state import (
    Actor,
    ArtifactPaths,
    HandoffStatus,
    HumanGateReason,
    StatusReason,
    SupervisorState,
    status_to_dict,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _status(
    *,
    run_id: str,
    state: SupervisorState,
    next_actor: Actor,
    active_program: str,
    active_target: str,
    human_gate_reason: HumanGateReason | None = None,
) -> HandoffStatus:
    return HandoffStatus(
        run_id=run_id,
        revision=3,
        state=state,
        active_program=active_program,
        active_target=active_target,
        last_actor=Actor.SYSTEM,
        next_actor=next_actor,
        status_reason=(
            StatusReason.AWAITING_HUMAN_GATE
            if state == SupervisorState.D
            else StatusReason.AWAITING_EVALUATION
        ),
        pipeline_type="research",
        debate_file="[internal-ref]",
        debate_last_turn=31,
        owner_mode="debate",
        seed_spec_path="research_areas/seeds/active/paper4_manuscript.md",
        artifact_paths=ArtifactPaths(
            spec="research_areas/specs/paper4_manuscript_manuscript_theory_foundations_prose_spec.json",
            implementation=("research_areas/drafts/paper4_manuscript/02a_theory_foundations.md",),
        ),
        human_gate_reason=human_gate_reason,
    )


def run_supervisor_program_autoloop_fixture_regression() -> dict[str, object]:
    results: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix="supervisor_program_autoloop_fixture_") as tmp:
        tmp_root = Path(tmp)
        active_runs_root = tmp_root / "active_runs"
        active_runs_root.mkdir()
        registry_file = tmp_root / "program_registry.json"
        _write_json(registry_file, json.loads(registry_path().read_text()))

        prose_manifest = ProgramManifest(
            program_id="paper4_manuscript",
            completion_policy="manifest_exhausted_to_D",
            auto_promote_contract_promotion=False,
            document_manifest_path="research_areas/drafts/paper4_manuscript/document_manifest.json",
            api_prompt_versions={
                "research_a1": "research_packet_a1_api_v1",
                "research_a2": "research_packet_a2_api_v1",
                "research_b": "research_packet_b_api_v1",
            },
            packets=(
                ManifestPacket(
                    packet_id="manuscript_theory_foundations",
                    title="Theory Foundations",
                    status=ManifestPacketStatus.PENDING,
                    target="manuscript_theory_foundations",
                    summary="theory",
                    allowed_artifacts=("research_areas/drafts/paper4_manuscript/02a_theory_foundations.md",),
                    read_bundle=("research_areas/drafts/paper4_manuscript_manuscript_opening.md",),
                ),
            ),
        )

        prose_run = "paper4_manuscript_003"
        prose_status_path = active_runs_root / prose_run / "status.json"
        _write_json(
            prose_status_path,
            status_to_dict(
                _status(
                    run_id=prose_run,
                    state=SupervisorState.D,
                    next_actor=Actor.HUMAN,
                    active_program="paper4_manuscript",
                    active_target="manuscript_theory_foundations",
                    human_gate_reason=HumanGateReason.CONTRACT_PROMOTION,
                )
            ),
        )
        _write_json(active_runs_root / prose_run / "events.jsonl", {})
        (active_runs_root / prose_run / "staging").mkdir(parents=True, exist_ok=True)

        original_manifest_loader = program_autoloop_module.load_optional_program_manifest
        try:
            program_autoloop_module.load_optional_program_manifest = lambda _program_id: prose_manifest
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = program_autoloop_module.cmd_program_autoloop(
                    argparse.Namespace(
                        program="paper4_manuscript",
                        run_id=prose_run,
                        active_runs_root=active_runs_root,
                        registry_path=registry_file,
                        wrapper_config_path=program_autoloop_module.wrapper_config_path(),
                        execute=False,
                        auto_commit=True,
                        max_advances=4,
                        max_seconds=60,
                        max_program_cost_usd=None,
                        max_output_tokens=12000,
                        max_fresh_input_tokens=40000,
                        max_packets=1,
                        max_refinement_cost_usd=None,
                    )
                )
            case_prose_gate_passed = (
                rc == 0
                and "requires human prose review" in stdout.getvalue()
            )
        finally:
            program_autoloop_module.load_optional_program_manifest = original_manifest_loader
        results.append(
            {
                "case_id": "program_autoloop_stops_at_prose_contract_promotion",
                "passed": case_prose_gate_passed,
            }
        )

        nonprose_manifest = ProgramManifest(
            program_id="demo_factory",
            completion_policy="manifest_exhausted_to_D",
            auto_promote_contract_promotion=True,
            api_prompt_versions=None,
            packets=(
                ManifestPacket(
                    packet_id="demo_packet",
                    title="Demo",
                    status=ManifestPacketStatus.PENDING,
                    target="demo_target",
                    summary="demo",
                    allowed_artifacts=("research_areas/drafts/demo.md",),
                ),
            ),
        )
        nonprose_run = "demo_factory_001"
        nonprose_status_path = active_runs_root / nonprose_run / "status.json"
        _write_json(
            nonprose_status_path,
            status_to_dict(
                _status(
                    run_id=nonprose_run,
                    state=SupervisorState.D,
                    next_actor=Actor.HUMAN,
                    active_program="demo_factory",
                    active_target="demo_target",
                    human_gate_reason=HumanGateReason.CONTRACT_PROMOTION,
                )
            ),
        )
        _write_json(active_runs_root / nonprose_run / "events.jsonl", {})
        (active_runs_root / nonprose_run / "staging").mkdir(parents=True, exist_ok=True)

        original_manifest_loader = program_autoloop_module.load_optional_program_manifest
        original_auto_promote = program_autoloop_module._auto_promote_packet
        original_assemble = program_autoloop_module._assemble_if_configured
        promoted: list[str] = []
        try:
            program_autoloop_module.load_optional_program_manifest = lambda _program_id: nonprose_manifest
            program_autoloop_module._auto_promote_packet = lambda **kwargs: promoted.append("ok")
            program_autoloop_module._assemble_if_configured = lambda **kwargs: None
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = program_autoloop_module.cmd_program_autoloop(
                    argparse.Namespace(
                        program="demo_factory",
                        run_id=nonprose_run,
                        active_runs_root=active_runs_root,
                        registry_path=registry_file,
                        wrapper_config_path=program_autoloop_module.wrapper_config_path(),
                        execute=False,
                        auto_commit=True,
                        max_advances=4,
                        max_seconds=60,
                        max_program_cost_usd=None,
                        max_output_tokens=12000,
                        max_fresh_input_tokens=40000,
                        max_packets=1,
                        max_refinement_cost_usd=None,
                    )
                )
            case_nonprose_promote_passed = (
                rc == 0
                and promoted == ["ok"]
                and "Stopping: max_packets reached." in stdout.getvalue()
            )
        finally:
            program_autoloop_module.load_optional_program_manifest = original_manifest_loader
            program_autoloop_module._auto_promote_packet = original_auto_promote
            program_autoloop_module._assemble_if_configured = original_assemble
        results.append(
            {
                "case_id": "program_autoloop_auto_promotes_nonprose_contract_promotion",
                "passed": case_nonprose_promote_passed,
            }
        )

        prompt_manifest = ProgramManifest(
            program_id="paper4_manuscript",
            completion_policy="manifest_exhausted_to_D",
            auto_promote_contract_promotion=False,
            document_manifest_path="research_areas/drafts/paper4_manuscript/document_manifest.json",
            api_prompt_versions={
                "research_a1": "research_packet_a1_api_v1",
                "research_a2": "research_packet_a2_api_v1",
                "research_b": "research_packet_b_api_v1",
            },
            packets=(
                ManifestPacket(
                    packet_id="manuscript_theory_foundations",
                    title="Theory Foundations",
                    status=ManifestPacketStatus.PENDING,
                    target="manuscript_theory_foundations",
                    summary="theory",
                    allowed_artifacts=("research_areas/drafts/paper4_manuscript/02a_theory_foundations.md",),
                    read_bundle=("research_areas/drafts/paper4_manuscript_manuscript_opening.md",),
                ),
            ),
        )
        prompt_run = "paper4_manuscript_004"
        prompt_status_path = active_runs_root / prompt_run / "status.json"
        _write_json(
            prompt_status_path,
            status_to_dict(
                _status(
                    run_id=prompt_run,
                    state=SupervisorState.A1,
                    next_actor=Actor.CLAUDE,
                    active_program="paper4_manuscript",
                    active_target="manuscript_theory_foundations",
                )
            ),
        )
        _write_json(active_runs_root / prompt_run / "events.jsonl", {})
        (active_runs_root / prompt_run / "staging").mkdir(parents=True, exist_ok=True)

        bad_wrapper = tmp_root / "bad_wrapper_config.json"
        _write_json(
            bad_wrapper,
            {
                "wrappers": {
                    "claude": {
                        "mode": "external_agent",
                        "model_name": "claude-sonnet-4-6",
                        "research_a1_prompt_version": "research_packet_a1_api_v1",
                        "research_b_prompt_version": "wrong_b_version",
                        "enforce_read_allowlist": True,
                        "command": ["claude", "-p"],
                    },
                    "codex": {
                        "mode": "external_agent",
                        "research_a2_prompt_version": "research_packet_a2_api_v1",
                        "enforce_read_allowlist": True,
                        "command": ["codex", "exec", "--json"],
                    },
                    "verifier": {"mode": "local_verifier", "command": []},
                }
            },
        )

        original_manifest_loader = program_autoloop_module.load_optional_program_manifest
        original_attended = program_autoloop_module.cmd_attended_autoloop
        attended_calls: list[str] = []
        try:
            program_autoloop_module.load_optional_program_manifest = lambda _program_id: prompt_manifest
            program_autoloop_module.cmd_attended_autoloop = lambda _args: attended_calls.append("called")
            try:
                program_autoloop_module.cmd_program_autoloop(
                    argparse.Namespace(
                        program="paper4_manuscript",
                        run_id=prompt_run,
                        active_runs_root=active_runs_root,
                        registry_path=registry_file,
                        wrapper_config_path=bad_wrapper,
                        execute=False,
                        auto_commit=True,
                        max_advances=4,
                        max_seconds=60,
                        max_program_cost_usd=None,
                        max_output_tokens=12000,
                        max_fresh_input_tokens=40000,
                        max_packets=1,
                        max_refinement_cost_usd=None,
                    )
                )
                case_prompt_gate_passed = False
            except RuntimeError as exc:
                case_prompt_gate_passed = (
                    "research_b prompt version mismatch" in str(exc)
                    and not attended_calls
                )
        finally:
            program_autoloop_module.load_optional_program_manifest = original_manifest_loader
            program_autoloop_module.cmd_attended_autoloop = original_attended
        results.append(
            {
                "case_id": "program_autoloop_blocks_on_prompt_version_drift_before_launch",
                "passed": case_prompt_gate_passed,
            }
        )

    all_passed = all(result["passed"] for result in results)
    return {
        "suite": "supervisor_program_autoloop_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(results),
        "num_passed": sum(1 for result in results if result["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run supervisor program autoloop fixture regression.")
    parser.parse_args()

    summary = run_supervisor_program_autoloop_fixture_regression()
    print(
        f"Supervisor program autoloop fixture regression: "
        f"{summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
