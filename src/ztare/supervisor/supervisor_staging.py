from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.ztare.common.paths import REPO_ROOT
from src.ztare.supervisor.supervisor_manifest import (
    load_optional_program_manifest,
    manifest_summary,
)
from src.ztare.supervisor.supervisor_pipeline import (
    default_research_draft_path,
    default_research_spec_path,
    default_research_verification_command,
)
from src.ztare.supervisor.supervisor_state import Actor, HandoffStatus, SupervisorState


@dataclass(frozen=True)
class StagingContext:
    actor: Actor
    state: SupervisorState
    status_revision: int
    active_program: str
    active_target: str
    pipeline_type: str
    debate_file: str | None
    debate_last_turn: int | None
    debate_excerpt: str | None
    owner_mode: str | None
    genesis_path: str | None
    seed_spec_path: str | None
    contract_boundary: str | None
    success_condition: str | None
    out_of_scope: tuple[str, ...]
    artifact_paths: dict[str, Any]
    verification_command: str | None
    gate_on_verifier_pass: bool
    spec_refinement_rounds: int
    program_cost_usd: float
    refinement_cost_usd: float
    max_refinement_cost_usd: float | None
    manifest: dict[str, Any] | None
    staging_path: str


def staging_filename(actor: Actor, state: SupervisorState) -> str:
    return f"{actor.value}_{state.value.lower()}.json"


def build_staging_context(status: HandoffStatus, staging_dir: Path) -> StagingContext:
    staging_path = staging_dir / staging_filename(status.next_actor, status.state)
    manifest = load_optional_program_manifest(status.active_program)
    return StagingContext(
        actor=status.next_actor,
        state=status.state,
        status_revision=status.revision,
        active_program=status.active_program,
        active_target=status.active_target,
        pipeline_type=status.pipeline_type,
        debate_file=status.debate_file,
        debate_last_turn=status.debate_last_turn,
        debate_excerpt=_build_debate_excerpt(status.debate_file),
        owner_mode=status.owner_mode,
        genesis_path=_relativize_repo_path(status.genesis_path),
        seed_spec_path=status.seed_spec_path,
        contract_boundary=status.contract_boundary,
        success_condition=status.success_condition,
        out_of_scope=status.out_of_scope,
        artifact_paths=asdict(status.artifact_paths),
        verification_command=status.verification_command,
        gate_on_verifier_pass=status.gate_on_verifier_pass,
        spec_refinement_rounds=status.spec_refinement_rounds,
        program_cost_usd=status.program_cost_usd,
        refinement_cost_usd=status.refinement_cost_usd,
        max_refinement_cost_usd=status.max_refinement_cost_usd,
        manifest=manifest_summary(manifest),
        staging_path=_relativize_repo_path(str(staging_path)),
    )


def _relativize_repo_path(path: str | None) -> str | None:
    if path is None:
        return None
    repo_prefix = str(REPO_ROOT) + "/"
    if path.startswith(repo_prefix):
        return path[len(repo_prefix) :]
    return path


TURN_HEADER_RE = re.compile(r"^(?:##|###) Turn \d+\b.*$", re.MULTILINE)
MAX_DEBATE_EXCERPT_CHARS = 8000
MAX_DEBATE_EXCERPT_TURNS = 2


def _build_debate_excerpt(debate_file: str | None) -> str | None:
    if not debate_file:
        return None
    path = Path(debate_file)
    if not path.exists():
        return None
    text = path.read_text()
    matches = list(TURN_HEADER_RE.finditer(text))
    if not matches:
        excerpt = text[-MAX_DEBATE_EXCERPT_CHARS:]
        return excerpt.strip() or None

    start_index = matches[max(0, len(matches) - MAX_DEBATE_EXCERPT_TURNS)].start()
    excerpt = text[start_index:]
    if len(excerpt) > MAX_DEBATE_EXCERPT_CHARS:
        excerpt = excerpt[-MAX_DEBATE_EXCERPT_CHARS:]
    return excerpt.strip() or None


def build_staging_template(status: HandoffStatus) -> dict[str, Any]:
    manifest = load_optional_program_manifest(status.active_program)
    next_packet = manifest_summary(manifest).get("next_packet") if manifest is not None else None
    template: dict[str, Any] = {
        "actor": status.next_actor.value,
        "expected_revision": status.revision,
        "target_state": _default_target_state_for_status(status).value,
        "declared_scope": {
            "program_id": status.active_program,
            "target": status.active_target,
        },
        "note": "",
    }
    if status.state == SupervisorState.C and status.next_actor == Actor.VERIFIER:
        template["current_implementation_snapshot"] = [
            {"path": item.path, "sha256": item.sha256}
            for item in status.implementation_snapshot
        ]
        template["verification_passed"] = False
        template["verification_report"] = ""
    if status.state == SupervisorState.A2 and status.next_actor in {Actor.CLAUDE, Actor.CODEX}:
        if status.pipeline_type == "research":
            template["spec_path"] = status.artifact_paths.spec or default_research_spec_path(
                program_id=status.active_program,
                target=status.active_target,
            )
        else:
            template["spec_path"] = status.artifact_paths.spec or status.debate_file
        expected_implementation_paths = list(status.artifact_paths.implementation)
        if not expected_implementation_paths and next_packet is not None:
            expected_implementation_paths = list(next_packet.get("allowed_artifacts") or ())
        if not expected_implementation_paths and status.pipeline_type == "research":
            expected_implementation_paths = [
                default_research_draft_path(
                    program_id=status.active_program,
                    target=status.active_target,
                )
            ]
        if expected_implementation_paths:
            template["expected_implementation_paths"] = expected_implementation_paths
        template["spec_refinement_requested"] = False
        template["gate_on_verifier_pass"] = status.gate_on_verifier_pass
        template["refinement_rounds_used"] = status.spec_refinement_rounds
        template["max_refinement_rounds"] = 2
        template["max_refinement_cost_usd"] = status.max_refinement_cost_usd
    if status.state == SupervisorState.B and status.next_actor in {Actor.CODEX, Actor.CLAUDE}:
        implementation_paths = list(status.artifact_paths.implementation)
        if not implementation_paths and next_packet is not None:
            implementation_paths = list(next_packet.get("allowed_artifacts") or ())
        if not implementation_paths and status.pipeline_type == "research":
            implementation_paths = [
                default_research_draft_path(
                    program_id=status.active_program,
                    target=status.active_target,
                )
            ]
        if implementation_paths:
            template["implementation_paths"] = implementation_paths
        verification_command = status.verification_command
        if not verification_command and next_packet is not None:
            verification_command = next_packet.get("verification_command")
        if (
            not verification_command
            and status.pipeline_type == "research"
            and implementation_paths
        ):
            verification_command = default_research_verification_command(
                draft_path=implementation_paths[0],
                spec_path=status.artifact_paths.spec
                or default_research_spec_path(
                    program_id=status.active_program,
                    target=status.active_target,
                ),
            )
        if verification_command:
            template["verification_command"] = verification_command
    return template


def write_staging_files(status: HandoffStatus, staging_dir: Path) -> tuple[Path, Path]:
    staging_dir.mkdir(parents=True, exist_ok=True)
    context = build_staging_context(status, staging_dir)
    context_path = staging_dir / f"{status.next_actor.value}_{status.state.value.lower()}_context.json"
    request_path = Path(context.staging_path)
    context_path.write_text(json.dumps(asdict(context), indent=2) + "\n")
    request_path.write_text(json.dumps(build_staging_template(status), indent=2) + "\n")
    return context_path, request_path


def _default_target_state_for_status(status: HandoffStatus) -> SupervisorState:
    if status.next_actor == Actor.VERIFIER and status.state == SupervisorState.C:
        return SupervisorState.D if status.gate_on_verifier_pass else SupervisorState.A1
    mapping = {
        (Actor.CLAUDE, SupervisorState.A1): SupervisorState.A2,
        (Actor.CLAUDE, SupervisorState.A2): SupervisorState.B,
        (Actor.CODEX, SupervisorState.A2): SupervisorState.B,
        (Actor.CLAUDE, SupervisorState.B): SupervisorState.C,
        (Actor.CODEX, SupervisorState.B): SupervisorState.C,
        (Actor.HUMAN, SupervisorState.D): SupervisorState.A1,
    }
    return mapping[(status.next_actor, status.state)]
