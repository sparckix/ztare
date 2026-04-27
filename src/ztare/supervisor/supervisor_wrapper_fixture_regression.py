from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import src.ztare.supervisor.supervisor_wrappers as supervisor_wrappers_module
from src.ztare.supervisor.supervisor_manifest import ManifestPacket, ManifestPacketStatus, ProgramManifest
from src.ztare.supervisor.supervisor_staging import write_staging_files
from src.ztare.supervisor.supervisor_state import (
    Actor,
    ArtifactPaths,
    ArtifactSnapshot,
    HandoffStatus,
    StatusReason,
    SupervisorState,
)
from src.ztare.supervisor.supervisor_wrappers import APITransportResult, launch_staged_request


def _base_status(*, state: SupervisorState, next_actor: Actor) -> HandoffStatus:
    return HandoffStatus(
        run_id="wrapper_fixture",
        revision=2,
        state=state,
        active_program="stage2_derivation_seam_hardening",
        active_target="derivation_boundary",
        last_actor=Actor.SYSTEM,
        next_actor=next_actor,
        status_reason=StatusReason.AWAITING_EVALUATION,
        debate_file="research_areas/debates/kernel/stage2_derivation_seam_hardening.md",
        seed_spec_path="research_areas/seeds/active/stage2_derivation_seam.md",
        contract_boundary="TextInput -> HingeObject / derivation record",
        success_condition="Fail closed on fabricated anchors",
        out_of_scope=("do not touch downstream contracts",),
    )


def run_supervisor_wrapper_fixture_regression() -> dict[str, object]:
    results: list[dict[str, object]] = []
    all_passed = True

    with tempfile.TemporaryDirectory(prefix="supervisor_wrapper_fixture_") as tmp:
        staging_dir = Path(tmp) / "staging"

        a1_status = _base_status(state=SupervisorState.A1, next_actor=Actor.CLAUDE)
        write_staging_files(a1_status, staging_dir)
        dry_run = launch_staged_request(status=a1_status, staging_dir=staging_dir, execute=False)
        a1_prompt = Path(dry_run.prompt_path).read_text() if dry_run.prompt_path else ""
        case1_passed = (
            dry_run.executed is False
            and dry_run.command[0] == "claude"
            and "`research_areas/debates/kernel/stage2_derivation_seam_hardening.md`" in a1_prompt
            and "do not modify supervisor state files directly" in a1_prompt
        )
        all_passed = all_passed and case1_passed
        results.append(
            {
                "case_id": "claude_wrapper_dry_run_builds_prompt",
                "passed": case1_passed,
            }
        )

        research_a2_status = HandoffStatus(
            **{
                **a1_status.__dict__,
                "state": SupervisorState.A2,
                "active_program": "paper4_drafting",
                "active_target": "paper_outline",
                "pipeline_type": "research",
                "debate_file": "research_areas/private/papers/paper4.md",
                "seed_spec_path": "research_areas/seeds/active/paper4_managerial_capitalism.md",
                "status_reason": StatusReason.AWAITING_DRAFT,
                "next_actor": Actor.CODEX,
            }
        )
        write_staging_files(research_a2_status, staging_dir)
        research_a2_dry_run = launch_staged_request(
            status=research_a2_status,
            staging_dir=staging_dir,
            execute=False,
        )
        research_a2_prompt = (
            Path(research_a2_dry_run.prompt_path).read_text()
            if research_a2_dry_run.prompt_path
            else ""
        )
        case_research_a2_passed = (
            research_a2_dry_run.executed is False
            and research_a2_dry_run.command[0] == "codex"
            and "You are the Skeptic for supervisor state `A2`." in research_a2_prompt
            and "`research_areas/specs/paper4_drafting_paper_outline_prose_spec.json`" in research_a2_prompt
            and "set `spec_refinement_requested` to true" in research_a2_prompt
            and "the context JSON already contains a capped debate excerpt" in research_a2_prompt
            and "do not run broad repo-wide search commands" in research_a2_prompt
            and "write the deterministic prose spec JSON to `spec_path`" in research_a2_prompt
            and "`research_areas/drafts/paper4_drafting_paper_outline.md`" in research_a2_prompt
        )
        all_passed = all_passed and case_research_a2_passed
        results.append(
            {
                "case_id": "research_a2_wrapper_dry_run_requires_prose_spec_artifact",
                "passed": case_research_a2_passed,
            }
        )

        b_status = _base_status(state=SupervisorState.B, next_actor=Actor.CODEX)
        b_status = HandoffStatus(
            **{
                **b_status.__dict__,
                "artifact_paths": ArtifactPaths(
                    spec="research_areas/debates/kernel/stage2_derivation_seam_hardening.md",
                    implementation=(
                        "src/ztare/validator/stage2_derivation.py",
                        "src/ztare/validator/stage2_derivation_fixture_regression.py",
                    ),
                ),
                "verification_command": "python -m src.ztare.validator.core.stage2_derivation_fixture_regression",
            }
        )
        write_staging_files(b_status, staging_dir)
        dry_run_b = launch_staged_request(status=b_status, staging_dir=staging_dir, execute=False)
        b_prompt = Path(dry_run_b.prompt_path).read_text() if dry_run_b.prompt_path else ""
        case2_passed = (
            dry_run_b.executed is False
            and dry_run_b.command[0] == "codex"
            and "src/ztare/validator/stage2_derivation.py" in b_prompt
            and "src/ztare/validator/stage2_derivation_fixture_regression.py" in b_prompt
            and "`implementation_paths` must equal:" in b_prompt
            and "`verification_command`:" in b_prompt
        )
        all_passed = all_passed and case2_passed
        results.append(
            {
                "case_id": "codex_wrapper_dry_run_lists_allowed_artifacts",
                "passed": case2_passed,
            }
        )

        research_b_status = HandoffStatus(
            **{
                **b_status.__dict__,
                "active_program": "paper4_drafting",
                "active_target": "paper_outline",
                "pipeline_type": "research",
                "next_actor": Actor.CLAUDE,
                "debate_file": "research_areas/private/papers/paper4.md",
                "seed_spec_path": "research_areas/seeds/active/paper4_managerial_capitalism.md",
                "verification_command": None,
                "artifact_paths": ArtifactPaths(
                    spec="research_areas/specs/paper4_drafting_paper_outline_prose_spec.json",
                    implementation=("research_areas/drafts/paper4_drafting_paper_outline.md",),
                ),
            }
        )
        manifest_b_program = ProgramManifest(
            program_id="paper4_drafting",
            completion_policy="manifest_exhausted_to_D",
            packets=(
                ManifestPacket(
                    packet_id="paper_outline",
                    title="Outline",
                    status=ManifestPacketStatus.PENDING,
                    target="paper_outline",
                    summary="outline",
                    allowed_artifacts=("research_areas/drafts/paper4_drafting_paper_outline.md",),
                    read_bundle=(
                        "research_areas/drafts/paper4_drafting_paper_outline.md",
                        "research_areas/specs/paper4_drafting_paper_outline_prose_spec.json",
                    ),
                ),
            ),
        )
        original_manifest_loader = supervisor_wrappers_module.load_optional_program_manifest
        supervisor_wrappers_module.load_optional_program_manifest = lambda _program_id: (
            manifest_b_program if _program_id == "paper4_drafting" else None
        )
        try:
            write_staging_files(research_b_status, staging_dir)
            research_b_dry_run = launch_staged_request(
                status=research_b_status,
                staging_dir=staging_dir,
                execute=False,
            )
            research_b_prompt = (
                Path(research_b_dry_run.prompt_path).read_text()
                if research_b_dry_run.prompt_path
                else ""
            )
            case_research_b_passed = (
                research_b_dry_run.executed is False
                and research_b_dry_run.command[:2] == ("anthropic", "messages.create")
                and "Writing Agent" in research_b_prompt
                and "write the research draft markdown to the declared implementation path" in research_b_prompt
                and "`verification_command`: `python -m src.ztare.findings.prose_verifier --draft-path research_areas/drafts/paper4_drafting_paper_outline.md --spec-path research_areas/specs/paper4_drafting_paper_outline_prose_spec.json`" in research_b_prompt
            )
        finally:
            supervisor_wrappers_module.load_optional_program_manifest = original_manifest_loader
        all_passed = all_passed and case_research_b_passed
        results.append(
            {
                "case_id": "research_b_wrapper_dry_run_routes_to_anthropic_api_and_prose_verifier",
                "passed": case_research_b_passed,
            }
        )

        b_api_config_path = Path(tmp) / "wrapper_config_api_b.json"
        b_api_config_path.write_text(
            json.dumps(
                {
                    "wrappers": {
                        "claude": {
                            "mode": "external_agent",
                            "command": ["claude", "-p"],
                            "model_name": "claude-sonnet-4-6",
                            "research_b_api_model_name": "claude-sonnet-4-6",
                            "enforce_read_allowlist": True,
                        }
                    }
                },
                indent=2,
            )
            + "\n"
        )
        original_manifest_loader = supervisor_wrappers_module.load_optional_program_manifest
        original_b_api_call = supervisor_wrappers_module._call_anthropic_research_b_api
        supervisor_wrappers_module.load_optional_program_manifest = lambda _program_id: (
            manifest_b_program if _program_id == "paper4_drafting" else None
        )
        supervisor_wrappers_module._call_anthropic_research_b_api = lambda **kwargs: APITransportResult(
            request_payload={
                "actor": "claude",
                "expected_revision": 2,
                "target_state": "C",
                "declared_scope": {
                    "program_id": "paper4_drafting",
                    "target": "paper_outline",
                },
                "note": "Drafted the packet.",
                "implementation_paths": [
                    "research_areas/drafts/paper4_drafting_paper_outline.md"
                ],
                "verification_command": "python -m src.ztare.findings.prose_verifier --draft-path research_areas/drafts/paper4_drafting_paper_outline.md --spec-path research_areas/specs/paper4_drafting_paper_outline_prose_spec.json",
            },
            artifacts=(
                (
                    "research_areas/drafts/paper4_drafting_paper_outline.md",
                    "## Intro\n\nManagerial capitalism separates strategy from execution.\n",
                    "replace",
                ),
            ),
            turn_usage=supervisor_wrappers_module.TurnUsageTelemetry(
                model_name="claude-sonnet-4-6",
                input_tokens=1200,
                output_tokens=500,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
                estimated_cost_usd=0.0,
                telemetry_captured=True,
            ),
            raw_response_text='{"ok":true}',
        )
        draft_path = Path("research_areas/drafts/paper4_drafting_paper_outline.md")
        draft_original = draft_path.read_text() if draft_path.exists() else None
        try:
            write_staging_files(research_b_status, staging_dir)
            b_api_result = launch_staged_request(
                status=research_b_status,
                staging_dir=staging_dir,
                execute=True,
                config_path=b_api_config_path,
            )
            b_api_payload = json.loads((staging_dir / "claude_b.json").read_text())
            updated_draft = draft_path.read_text()
            case_research_b_execute_passed = (
                b_api_result.exit_code == 0
                and b_api_result.command[:2] == ("anthropic", "messages.create")
                and b_api_payload["target_state"] == "C"
                and b_api_payload["write_scope_ok"] is True
                and "Managerial capitalism separates strategy from execution." in updated_draft
            )
        finally:
            supervisor_wrappers_module.load_optional_program_manifest = original_manifest_loader
            supervisor_wrappers_module._call_anthropic_research_b_api = original_b_api_call
            if draft_original is not None:
                draft_path.write_text(draft_original)
            elif draft_path.exists():
                draft_path.unlink()
        all_passed = all_passed and case_research_b_execute_passed
        results.append(
            {
                "case_id": "research_b_packet_can_route_through_anthropic_api",
                "passed": case_research_b_execute_passed,
            }
        )

        read_allowlist_config_path = Path(tmp) / "wrapper_config_read_allowlist.json"
        read_allowlist_config_path.write_text(
            json.dumps(
                {
                    "wrappers": {
                        "codex": {
                            "mode": "external_agent",
                            "command": [
                                sys.executable,
                                "-c",
                                (
                                    "from pathlib import Path; import json; "
                                    "print(json.dumps({"
                                    "'allowed': Path('research_areas/private/papers/paper4.md').exists(), "
                                    "'blocked': Path('src/ztare/validator/supervisor_wrappers.py').exists()"
                                    "}))"
                                ),
                            ],
                            "enforce_read_allowlist": True,
                        }
                    }
                },
                indent=2,
            )
            + "\n"
        )
        write_staging_files(research_a2_status, staging_dir)
        read_allowlist_result = launch_staged_request(
            status=research_a2_status,
            staging_dir=staging_dir,
            execute=True,
            config_path=read_allowlist_config_path,
        )
        read_allowlist_stdout = Path(read_allowlist_result.stdout_path).read_text()
        read_allowlist_payload = json.loads(read_allowlist_stdout)
        case_read_allowlist_passed = (
            read_allowlist_result.exit_code == 0
            and read_allowlist_result.sandbox_root is not None
            and "research_areas/private/papers/paper4.md" in read_allowlist_result.read_allowlist_paths
            and read_allowlist_payload["allowed"] is True
            and read_allowlist_payload["blocked"] is False
        )
        all_passed = all_passed and case_read_allowlist_passed
        results.append(
            {
                "case_id": "research_wrapper_executes_inside_read_allowlist_sandbox",
                "passed": case_read_allowlist_passed,
            }
        )

        manifest_program = ProgramManifest(
            program_id="paper4_drafting",
            completion_policy="manifest_exhausted_to_D",
            packets=(
                ManifestPacket(
                    packet_id="paper_outline",
                    title="Outline",
                    status=ManifestPacketStatus.PENDING,
                    target="paper_outline",
                    summary="outline",
                    allowed_artifacts=("research_areas/drafts/paper4_drafting_paper_outline.md",),
                    read_bundle=(
                        "research_areas/drafts/paper4_drafting_paper_outline.md",
                        "research_areas/specs/paper4_drafting_paper_outline_prose_spec.json",
                    ),
                    token_budget={"a2_max_output": 2500, "a2_max_fresh_input": 15000},
                ),
            ),
        )
        original_manifest_loader = supervisor_wrappers_module.load_optional_program_manifest
        supervisor_wrappers_module.load_optional_program_manifest = lambda _program_id: manifest_program
        try:
            write_staging_files(research_a2_status, staging_dir)
            bundle_result = launch_staged_request(
                status=research_a2_status,
                staging_dir=staging_dir,
                execute=False,
            )
            bundle_prompt = Path(bundle_result.prompt_path).read_text() if bundle_result.prompt_path else ""
            case_bundle_passed = (
                "research_areas/drafts/paper4_drafting_paper_outline.md" in bundle_result.read_allowlist_paths
                and "research_areas/specs/paper4_drafting_paper_outline_prose_spec.json" in bundle_result.read_allowlist_paths
                and "read_bundle:" in bundle_prompt
                and '"a2_max_fresh_input": 15000' in bundle_prompt
            )
        finally:
            supervisor_wrappers_module.load_optional_program_manifest = original_manifest_loader
        all_passed = all_passed and case_bundle_passed
        results.append(
            {
                "case_id": "research_wrapper_uses_manifest_read_bundle_and_token_budget",
                "passed": case_bundle_passed,
            }
        )

        research_a1_status = HandoffStatus(
            **{
                **a1_status.__dict__,
                "active_program": "paper4_manuscript",
                "active_target": "manuscript_theory_foundations",
                "pipeline_type": "research",
                "debate_file": "research_areas/private/papers/paper4_manuscript.md",
                "seed_spec_path": "research_areas/seeds/active/paper4_manuscript.md",
                "next_actor": Actor.CLAUDE,
            }
        )
        manifest_a1_program = ProgramManifest(
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
                    read_bundle=(
                        "research_areas/drafts/paper4_drafting_paper_outline.md",
                        "research_areas/specs/paper4_drafting_paper_outline_prose_spec.json",
                        "research_areas/drafts/paper4_manuscript_manuscript_opening.md",
                    ),
                ),
            ),
        )
        original_manifest_loader = supervisor_wrappers_module.load_optional_program_manifest
        supervisor_wrappers_module.load_optional_program_manifest = lambda _program_id: (
            manifest_a1_program if _program_id == "paper4_manuscript" else manifest_program
        )
        try:
            write_staging_files(research_a1_status, staging_dir)
            research_a1_dry_run = launch_staged_request(
                status=research_a1_status,
                staging_dir=staging_dir,
                execute=False,
            )
            research_a1_prompt = (
                Path(research_a1_dry_run.prompt_path).read_text()
                if research_a1_dry_run.prompt_path
                else ""
            )
            case_research_a1_api_passed = (
                research_a1_dry_run.executed is False
                and research_a1_dry_run.command[:2] == ("anthropic", "messages.create")
                and "Return a request object and exactly one append-only debate turn artifact." in research_a1_prompt
            )
        finally:
            supervisor_wrappers_module.load_optional_program_manifest = original_manifest_loader
        all_passed = all_passed and case_research_a1_api_passed
        results.append(
            {
                "case_id": "research_a1_packet_dry_run_routes_to_anthropic_api",
                "passed": case_research_a1_api_passed,
            }
        )

        a1_api_config_path = Path(tmp) / "wrapper_config_api_a1.json"
        a1_api_config_path.write_text(
            json.dumps(
                {
                    "wrappers": {
                        "claude": {
                            "mode": "external_agent",
                            "command": ["claude", "-p"],
                            "model_name": "claude-sonnet-4-6",
                            "enforce_read_allowlist": True,
                        }
                    }
                },
                indent=2,
            )
            + "\n"
        )
        original_manifest_loader = supervisor_wrappers_module.load_optional_program_manifest
        original_a1_api_call = supervisor_wrappers_module._call_anthropic_research_a1_api
        supervisor_wrappers_module.load_optional_program_manifest = lambda _program_id: (
            manifest_a1_program if _program_id == "paper4_manuscript" else None
        )
        supervisor_wrappers_module._call_anthropic_research_a1_api = lambda **kwargs: APITransportResult(
            request_payload={
                "actor": "claude",
                "expected_revision": 2,
                "target_state": "A2",
                "declared_scope": {
                    "program_id": "paper4_manuscript",
                    "target": "manuscript_theory_foundations",
                },
                "note": "Turn 15 appended.",
            },
            artifacts=(
                (
                    "research_areas/private/papers/paper4_manuscript.md",
                    "## Turn 15 — Architect (A1)\n\nPacket-scoped revision.\n",
                    "append",
                ),
            ),
            turn_usage=supervisor_wrappers_module.TurnUsageTelemetry(
                model_name="claude-sonnet-4-6",
                input_tokens=1500,
                output_tokens=400,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
                estimated_cost_usd=0.0,
                telemetry_captured=True,
            ),
            raw_response_text='{"ok":true}',
        )
        debate_path = Path("research_areas/private/papers/paper4_manuscript.md")
        debate_original = debate_path.read_text() if debate_path.exists() else None
        try:
            write_staging_files(research_a1_status, staging_dir)
            a1_api_result = launch_staged_request(
                status=research_a1_status,
                staging_dir=staging_dir,
                execute=True,
                config_path=a1_api_config_path,
            )
            a1_api_payload = json.loads((staging_dir / "claude_a1.json").read_text())
            updated_debate = debate_path.read_text()
            case_research_a1_execute_passed = (
                a1_api_result.exit_code == 0
                and a1_api_result.command[:2] == ("anthropic", "messages.create")
                and a1_api_payload["target_state"] == "A2"
                and a1_api_payload["write_scope_ok"] is True
                and "## Turn 15 — Architect (A1)" in updated_debate
            )
        finally:
            supervisor_wrappers_module.load_optional_program_manifest = original_manifest_loader
            supervisor_wrappers_module._call_anthropic_research_a1_api = original_a1_api_call
            if debate_original is not None:
                debate_path.write_text(debate_original)
        all_passed = all_passed and case_research_a1_execute_passed
        results.append(
            {
                "case_id": "research_a1_packet_can_route_through_anthropic_api",
                "passed": case_research_a1_execute_passed,
            }
        )

        original_manifest_loader = supervisor_wrappers_module.load_optional_program_manifest
        original_a1_api_call = supervisor_wrappers_module._call_anthropic_research_a1_api
        supervisor_wrappers_module.load_optional_program_manifest = lambda _program_id: (
            manifest_a1_program if _program_id == "paper4_manuscript" else None
        )
        supervisor_wrappers_module._call_anthropic_research_a1_api = lambda **kwargs: APITransportResult(
            request_payload={
                "actor": "claude",
                "expected_revision": 2,
                "target_state": "A2",
                "declared_scope": {
                    "program_id": "paper4_manuscript",
                    "target": "manuscript_theory_foundations",
                },
                "note": "Invalid artifact path attempt.",
            },
            artifacts=(
                (
                    "research_areas/drafts/paper4_manuscript/02a_theory_foundations.md",
                    "# bogus\n",
                    "replace",
                ),
            ),
            turn_usage=supervisor_wrappers_module.TurnUsageTelemetry(
                model_name="claude-sonnet-4-6",
                input_tokens=1500,
                output_tokens=400,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
                estimated_cost_usd=0.0,
                telemetry_captured=True,
            ),
            raw_response_text='{"ok":true}',
        )
        invalid_draft_path = Path("research_areas/drafts/paper4_manuscript/02a_theory_foundations.md")
        invalid_draft_original = invalid_draft_path.read_text() if invalid_draft_path.exists() else None
        try:
            write_staging_files(research_a1_status, staging_dir)
            invalid_a1_result = launch_staged_request(
                status=research_a1_status,
                staging_dir=staging_dir,
                execute=True,
                config_path=a1_api_config_path,
            )
            invalid_a1_payload = json.loads((staging_dir / "claude_a1.json").read_text())
            current_draft = invalid_draft_path.read_text() if invalid_draft_path.exists() else ""
            case_research_a1_rejects_invalid_artifact_passed = (
                invalid_a1_result.exit_code == 0
                and "research_areas/drafts/paper4_manuscript/02a_theory_foundations.md"
                in invalid_a1_result.unauthorized_repo_paths
                and invalid_a1_payload["write_scope_ok"] is False
                and current_draft == (invalid_draft_original or "")
            )
        finally:
            supervisor_wrappers_module.load_optional_program_manifest = original_manifest_loader
            supervisor_wrappers_module._call_anthropic_research_a1_api = original_a1_api_call
            if invalid_draft_original is not None:
                invalid_draft_path.write_text(invalid_draft_original)
            elif invalid_draft_path.exists():
                invalid_draft_path.unlink()
        all_passed = all_passed and case_research_a1_rejects_invalid_artifact_passed
        results.append(
            {
                "case_id": "research_a1_api_rejects_invalid_artifact_path_before_write",
                "passed": case_research_a1_rejects_invalid_artifact_passed,
            }
        )

        original_manifest_loader = supervisor_wrappers_module.load_optional_program_manifest
        original_a1_api_call = supervisor_wrappers_module._call_anthropic_research_a1_api
        supervisor_wrappers_module.load_optional_program_manifest = lambda _program_id: (
            manifest_a1_program if _program_id == "paper4_manuscript" else None
        )
        supervisor_wrappers_module._call_anthropic_research_a1_api = lambda **kwargs: APITransportResult(
            request_payload={
                "actor": "claude",
                "expected_revision": 2,
                "target_state": "A2",
                "declared_scope": {
                    "program_id": "paper4_manuscript",
                    "target": "manuscript_theory_foundations",
                },
                "note": "Invalid artifact operation attempt.",
            },
            artifacts=(
                (
                    "research_areas/private/papers/paper4_manuscript.md",
                    "## Turn 15 — Architect (A1)\n\nPacket-scoped revision.\n",
                    "replace",
                ),
            ),
            turn_usage=supervisor_wrappers_module.TurnUsageTelemetry(
                model_name="claude-sonnet-4-6",
                input_tokens=1500,
                output_tokens=400,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
                estimated_cost_usd=0.0,
                telemetry_captured=True,
            ),
            raw_response_text='{"ok":true}',
        )
        debate_path = Path("research_areas/private/papers/paper4_manuscript.md")
        debate_original = debate_path.read_text() if debate_path.exists() else None
        try:
            write_staging_files(research_a1_status, staging_dir)
            invalid_op_result = launch_staged_request(
                status=research_a1_status,
                staging_dir=staging_dir,
                execute=True,
                config_path=a1_api_config_path,
            )
            invalid_op_payload = json.loads((staging_dir / "claude_a1.json").read_text())
            current_debate = debate_path.read_text() if debate_path.exists() else ""
            case_research_a1_rejects_invalid_operation_passed = (
                invalid_op_result.exit_code == 0
                and "research_areas/private/papers/paper4_manuscript.md"
                in invalid_op_result.unauthorized_repo_paths
                and invalid_op_payload["write_scope_ok"] is False
                and current_debate == (debate_original or "")
            )
        finally:
            supervisor_wrappers_module.load_optional_program_manifest = original_manifest_loader
            supervisor_wrappers_module._call_anthropic_research_a1_api = original_a1_api_call
            if debate_original is not None:
                debate_path.write_text(debate_original)
        all_passed = all_passed and case_research_a1_rejects_invalid_operation_passed
        results.append(
            {
                "case_id": "research_a1_api_rejects_replace_operation_on_debate_path",
                "passed": case_research_a1_rejects_invalid_operation_passed,
            }
        )

        api_config_path = Path(tmp) / "wrapper_config_api_a2.json"
        api_config_path.write_text(
            json.dumps(
                {
                    "wrappers": {
                        "codex": {
                            "mode": "external_agent",
                            "command": ["codex", "exec", "--json"],
                            "enforce_read_allowlist": True,
                            "research_a2_api_model_name": "o4-mini",
                            "research_a2_max_output_tokens": 2000,
                        }
                    }
                },
                indent=2,
            )
            + "\n"
        )
        original_api_call = supervisor_wrappers_module._call_openai_research_a2_api
        original_manifest_loader = supervisor_wrappers_module.load_optional_program_manifest
        supervisor_wrappers_module.load_optional_program_manifest = lambda _program_id: manifest_program
        supervisor_wrappers_module._call_openai_research_a2_api = lambda **kwargs: APITransportResult(
            request_payload={
                "actor": "codex",
                "expected_revision": 2,
                "target_state": "B",
                "declared_scope": {
                    "program_id": "paper4_drafting",
                    "target": "paper_outline",
                },
                "note": "Locking the outline to prose.",
                "spec_path": "research_areas/specs/paper4_drafting_paper_outline_prose_spec.json",
                "expected_implementation_paths": [
                    "research_areas/drafts/paper4_drafting_paper_outline.md"
                ],
                "spec_refinement_requested": False,
                "gate_on_verifier_pass": True,
                "refinement_rounds_used": 0,
                "max_refinement_rounds": 2,
                "max_refinement_cost_usd": None,
            },
            artifacts=(
                (
                    "research_areas/specs/paper4_drafting_paper_outline_prose_spec.json",
                    '{"packet_id":"paper_outline","required_headers":["Intro"],"assertions":[],"global_word_min":100,"global_word_max":300}',
                    "replace",
                ),
            ),
            turn_usage=supervisor_wrappers_module.TurnUsageTelemetry(
                model_name="o4-mini",
                input_tokens=1200,
                output_tokens=600,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
                estimated_cost_usd=0.0,
                telemetry_captured=True,
            ),
            raw_response_text='{"ok":true}',
        )
        try:
            write_staging_files(research_a2_status, staging_dir)
            api_result = launch_staged_request(
                status=research_a2_status,
                staging_dir=staging_dir,
                execute=True,
                config_path=api_config_path,
            )
            api_payload = json.loads((staging_dir / "codex_a2.json").read_text())
            api_spec = Path("research_areas/specs/paper4_drafting_paper_outline_prose_spec.json")
            case_api_transport_passed = (
                api_result.exit_code == 0
                and api_result.command[:3] == ("openai", "responses.parse", "--model")
                and api_result.turn_usage is not None
                and api_result.turn_usage.model_name == "o4-mini"
                and api_payload["target_state"] == "B"
                and api_payload["write_scope_ok"] is True
                and api_spec.exists()
            )
        finally:
            supervisor_wrappers_module._call_openai_research_a2_api = original_api_call
            supervisor_wrappers_module.load_optional_program_manifest = original_manifest_loader
            api_spec_repo = Path("research_areas/specs/paper4_drafting_paper_outline_prose_spec.json")
            if api_spec_repo.exists():
                api_spec_repo.unlink()
        all_passed = all_passed and case_api_transport_passed
        results.append(
            {
                "case_id": "research_a2_wrapper_can_route_through_openai_api",
                "passed": case_api_transport_passed,
            }
        )

        original_api_call = supervisor_wrappers_module._call_openai_research_a2_api
        original_manifest_loader = supervisor_wrappers_module.load_optional_program_manifest
        supervisor_wrappers_module.load_optional_program_manifest = lambda _program_id: manifest_program
        supervisor_wrappers_module._call_openai_research_a2_api = lambda **kwargs: APITransportResult(
            request_payload={
                "actor": "codex",
                "expected_revision": 2,
                "target_state": "A1",
                "declared_scope": {
                    "program_id": "paper4_drafting",
                    "target": "paper_outline",
                },
                "note": "Refine the spec.",
                "spec_path": "research_areas/specs/paper4_drafting_paper_outline_prose_spec.json",
                "expected_implementation_paths": [
                    "research_areas/drafts/paper4_drafting_paper_outline.md"
                ],
                "spec_refinement_requested": True,
                "gate_on_verifier_pass": False,
                "refinement_rounds_used": 0,
                "max_refinement_rounds": 2,
                "max_refinement_cost_usd": None,
            },
            artifacts=(
                (
                    "research_areas/specs/paper4_drafting_paper_outline_prose_spec.json",
                    '{"packet_id":"paper_outline","required_headers":["Intro"],"assertions":[],"global_word_min":100,"global_word_max":300}',
                    "update",
                ),
            ),
            turn_usage=supervisor_wrappers_module.TurnUsageTelemetry(
                model_name="o4-mini",
                input_tokens=1200,
                output_tokens=300,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
                estimated_cost_usd=0.0,
                telemetry_captured=True,
            ),
            raw_response_text='{"ok":true}',
        )
        invalid_spec_path = Path("research_areas/specs/paper4_drafting_paper_outline_prose_spec.json")
        invalid_spec_original = invalid_spec_path.read_text() if invalid_spec_path.exists() else None
        try:
            write_staging_files(research_a2_status, staging_dir)
            invalid_a2_result = launch_staged_request(
                status=research_a2_status,
                staging_dir=staging_dir,
                execute=True,
                config_path=api_config_path,
            )
            invalid_a2_payload = json.loads((staging_dir / "codex_a2.json").read_text())
            current_spec = invalid_spec_path.read_text() if invalid_spec_path.exists() else None
            case_research_a2_rejects_invalid_operation_passed = (
                invalid_a2_result.exit_code == 0
                and "research_areas/specs/paper4_drafting_paper_outline_prose_spec.json"
                in invalid_a2_result.unauthorized_repo_paths
                and invalid_a2_payload["write_scope_ok"] is False
                and current_spec == invalid_spec_original
            )
        finally:
            supervisor_wrappers_module._call_openai_research_a2_api = original_api_call
            supervisor_wrappers_module.load_optional_program_manifest = original_manifest_loader
            if invalid_spec_original is not None:
                invalid_spec_path.write_text(invalid_spec_original)
            elif invalid_spec_path.exists():
                invalid_spec_path.unlink()
        all_passed = all_passed and case_research_a2_rejects_invalid_operation_passed
        results.append(
            {
                "case_id": "research_a2_api_rejects_invalid_replace_operation",
                "passed": case_research_a2_rejects_invalid_operation_passed,
            }
        )

        fake_codex = Path(tmp) / "codex"
        fake_codex.write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys, time\n"
            "print(json.dumps({'type':'thread.started'}), flush=True)\n"
            "print(json.dumps({'type':'turn.started'}), flush=True)\n"
            "payload = {'type':'item.completed','item':{'id':'item_1','type':'agent_message','text':'x'*5000}}\n"
            "print(json.dumps(payload), flush=True)\n"
            "time.sleep(1)\n"
            "print(json.dumps(payload), flush=True)\n"
            "time.sleep(1)\n"
        )
        fake_codex.chmod(0o755)
        output_cap_config_path = Path(tmp) / "wrapper_config_output_cap.json"
        output_cap_config_path.write_text(
            json.dumps(
                {
                    "wrappers": {
                        "codex": {
                            "mode": "external_agent",
                            "command": [str(fake_codex), "exec", "--json"],
                            "enforce_read_allowlist": True,
                            "research_a2_max_output_tokens": 1000,
                        }
                    }
                },
                indent=2,
            )
            + "\n"
        )
        write_staging_files(research_a2_status, staging_dir)
        output_cap_result = launch_staged_request(
            status=research_a2_status,
            staging_dir=staging_dir,
            execute=True,
            config_path=output_cap_config_path,
        )
        output_cap_payload = json.loads((staging_dir / "codex_a2.json").read_text())
        case_output_cap_passed = (
            output_cap_result.output_envelope_exceeded is True
            and output_cap_result.output_envelope_limit == 1000
            and (output_cap_result.estimated_output_tokens_emitted or 0) > 1000
            and output_cap_payload["wrapper_abort_reason"] == "output_envelope_exceeded"
            and output_cap_payload["write_scope_ok"] is False
        )
        all_passed = all_passed and case_output_cap_passed
        results.append(
            {
                "case_id": "research_a2_wrapper_kills_run_on_output_envelope",
                "passed": case_output_cap_passed,
            }
        )

        codex_skip_check = Path(tmp) / "codex"
        codex_skip_check.write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            "print(json.dumps({'argv': sys.argv[1:]}))\n"
        )
        codex_skip_check.chmod(0o755)
        skip_config_path = Path(tmp) / "wrapper_config_codex_skip.json"
        skip_config_path.write_text(
            json.dumps(
                {
                    "wrappers": {
                        "codex": {
                            "mode": "external_agent",
                            "command": [str(codex_skip_check), "exec", "--json"],
                            "enforce_read_allowlist": True,
                        }
                    }
                },
                indent=2,
            )
            + "\n"
        )
        write_staging_files(research_a2_status, staging_dir)
        skip_result = launch_staged_request(
            status=research_a2_status,
            staging_dir=staging_dir,
            execute=True,
            config_path=skip_config_path,
        )
        skip_stdout = json.loads(Path(skip_result.stdout_path).read_text())
        case_skip_git_check_passed = (
            skip_result.exit_code == 0
            and "--skip-git-repo-check" in skip_result.command
            and "--skip-git-repo-check" in skip_stdout["argv"]
        )
        all_passed = all_passed and case_skip_git_check_passed
        results.append(
            {
                "case_id": "research_codex_wrapper_adds_skip_git_repo_check_in_sandbox",
                "passed": case_skip_git_check_passed,
            }
        )

        usage_config_path = Path(tmp) / "wrapper_config_with_usage.json"
        usage_config_path.write_text(
            json.dumps(
                {
                    "wrappers": {
                        "claude": {
                            "mode": "external_agent",
                            "command": [
                                sys.executable,
                                "-c",
                                "import json; print(json.dumps({'model_name': 'fixture-model', 'input_tokens': 1200, 'output_tokens': 300}))",
                            ],
                            "model_name": "fixture-model",
                        }
                    }
                },
                indent=2,
            )
            + "\n"
        )
        write_staging_files(a1_status, staging_dir)
        execute_with_usage = launch_staged_request(
            status=a1_status,
            staging_dir=staging_dir,
            execute=True,
            config_path=usage_config_path,
        )
        execute_payload = json.loads((staging_dir / "claude_a1.json").read_text())
        case3_passed = (
            execute_with_usage.exit_code == 0
            and execute_with_usage.turn_usage is not None
            and execute_with_usage.turn_usage.telemetry_captured is True
            and execute_payload["turn_usage"]["input_tokens"] == 1200
            and execute_payload["turn_usage"]["output_tokens"] == 300
            and execute_payload["turn_usage"]["model_name"] == "fixture-model"
        )
        all_passed = all_passed and case3_passed
        results.append(
            {
                "case_id": "external_wrapper_executes_and_injects_usage_telemetry",
                "passed": case3_passed,
            }
        )

        unauthorized_probe = Path(tmp) / "unauthorized_probe.py"
        unauthorized_repo_path = Path("research_areas") / "wrapper_unauthorized_probe.txt"
        unauthorized_probe.write_text(
            "from pathlib import Path\n"
            "Path('research_areas/wrapper_unauthorized_probe.txt').write_text('probe\\n')\n"
            "print('ok')\n"
        )
        unauthorized_config_path = Path(tmp) / "wrapper_config_unauthorized.json"
        unauthorized_config_path.write_text(
            json.dumps(
                {
                    "wrappers": {
                        "claude": {
                            "mode": "external_agent",
                            "command": [sys.executable, str(unauthorized_probe)],
                            "model_name": "fixture-model",
                        }
                    }
                },
                indent=2,
            )
            + "\n"
        )
        try:
            write_staging_files(a1_status, staging_dir)
            unauthorized_result = launch_staged_request(
                status=a1_status,
                staging_dir=staging_dir,
                execute=True,
                config_path=unauthorized_config_path,
            )
            unauthorized_payload = json.loads((staging_dir / "claude_a1.json").read_text())
            case4_passed = (
                unauthorized_result.exit_code == 0
                and unauthorized_payload["write_scope_ok"] is False
                and "research_areas/wrapper_unauthorized_probe.txt"
                in unauthorized_payload["unauthorized_repo_paths"]
            )
        finally:
            if unauthorized_repo_path.exists():
                unauthorized_repo_path.unlink()
        all_passed = all_passed and case4_passed
        results.append(
            {
                "case_id": "external_wrapper_detects_unauthorized_repo_write",
                "passed": case4_passed,
            }
        )

        c_status = _base_status(state=SupervisorState.C, next_actor=Actor.VERIFIER)
        c_status = HandoffStatus(
            **{
                **c_status.__dict__,
                "artifact_paths": ArtifactPaths(
                    spec="research_areas/debates/kernel/stage2_derivation_seam_hardening.md",
                    implementation=(
                        "src/ztare/validator/stage2_derivation.py",
                        "src/ztare/validator/stage2_derivation_fixture_regression.py",
                    ),
                ),
                "implementation_snapshot": (
                    ArtifactSnapshot(path="src/ztare/validator/stage2_derivation.py", sha256="abc123"),
                    ArtifactSnapshot(
                        path="src/ztare/validator/stage2_derivation_fixture_regression.py",
                        sha256="def456",
                    ),
                ),
                "verification_command": "python -c \"print('ok')\"",
            }
        )
        write_staging_files(c_status, staging_dir)
        verifier_result = launch_staged_request(status=c_status, staging_dir=staging_dir, execute=True)
        verifier_payload = json.loads((staging_dir / "verifier_c.json").read_text())
        case5_passed = (
            verifier_result.exit_code == 0
            and verifier_payload["verification_passed"] is True
            and verifier_payload["target_state"] == "A1"
            and verifier_payload["verification_report"].endswith("verification_report.txt")
            and verifier_payload["turn_usage"]["model_name"] == "local_verifier"
        )
        all_passed = all_passed and case5_passed
        results.append(
            {
                "case_id": "verifier_wrapper_executes_and_prefills_request",
                "passed": case5_passed,
            }
        )

    return {
        "suite": "supervisor_wrapper_fixture_regression",
        "all_passed": all_passed,
            "num_cases": len(results),
        "num_passed": sum(1 for item in results if item["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run supervisor wrapper fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_supervisor_wrapper_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Supervisor wrapper fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
