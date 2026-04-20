from __future__ import annotations

from pathlib import Path

from src.ztare.supervisor.supervisor_seed_registry import (
    SeedPipelineType,
    load_seed_registry,
    seed_entry_by_spec_path,
)
from src.ztare.supervisor.supervisor_state import Actor, SupervisorState


def derive_pipeline_type(seed_spec_path: str | None) -> str:
    if not seed_spec_path:
        return SeedPipelineType.BUILD.value
    registry = load_seed_registry()
    entry = seed_entry_by_spec_path(registry).get(seed_spec_path)
    if entry is None:
        return SeedPipelineType.BUILD.value
    return entry.pipeline_type.value


def build_actor_for_pipeline(pipeline_type: str) -> Actor:
    return actor_for_pipeline_state(pipeline_type, SupervisorState.B)


def actor_for_pipeline_state(pipeline_type: str, state: SupervisorState) -> Actor:
    if state == SupervisorState.A2 and pipeline_type == SeedPipelineType.RESEARCH.value:
        return Actor.CODEX
    if state == SupervisorState.B and pipeline_type == SeedPipelineType.RESEARCH.value:
        return Actor.CLAUDE
    if state in {SupervisorState.A1, SupervisorState.A2}:
        return Actor.CLAUDE
    if state == SupervisorState.B:
        return Actor.CODEX
    if pipeline_type == SeedPipelineType.RESEARCH.value:
        return Actor.CLAUDE
    return Actor.CODEX


def default_research_spec_path(*, program_id: str, target: str) -> str:
    filename = f"{program_id}_{target}_prose_spec.json"
    return str(Path("research_areas") / "specs" / filename)


def default_research_draft_path(*, program_id: str, target: str) -> str:
    filename = f"{program_id}_{target}.md"
    return str(Path("research_areas") / "drafts" / filename)


def default_research_verification_command(*, draft_path: str, spec_path: str) -> str:
    return (
        "python -m src.ztare.validator.prose_verifier "
        f"--draft-path {draft_path} --spec-path {spec_path}"
    )
