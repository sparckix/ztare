from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.ztare.common.paths import REPO_ROOT
from src.ztare.supervisor.supervisor_seed_registry import (
    SeedPipelineType,
    load_seed_registry,
    seed_entry_map,
)
from src.ztare.supervisor.supervisor_state import Actor
from src.ztare.supervisor.supervisor_wrappers import invoke_agent, load_wrapper_configs


MAX_PROPOSED_PACKETS = 5


@dataclass(frozen=True)
class ProposalResult:
    executed: bool
    command: tuple[str, ...]
    context_path: str
    prompt_path: str
    proposal_manifest_path: str
    proposal_plan_path: str
    planning_debate_path: str
    stdout_path: str
    stderr_path: str
    debug_path: str
    usage_path: str
    modified_repo_paths: tuple[str, ...]
    unauthorized_repo_paths: tuple[str, ...]
    exit_code: int | None
    telemetry: dict[str, object] | None
    validation: dict[str, object]


def proposed_manifest_directory() -> Path:
    return REPO_ROOT / "supervisor" / "proposed_manifests"


def proposed_manifest_path(program_id: str) -> Path:
    return proposed_manifest_directory() / f"{program_id}.json"


def planning_debate_path(program_id: str) -> Path:
    return REPO_ROOT / "research_areas" / "debates" / "planning" / f"{program_id}.md"


def proposal_plan_directory() -> Path:
    return REPO_ROOT / "research_areas" / "proposal_plans"


def proposal_plan_markdown_path(program_id: str) -> Path:
    return proposal_plan_directory() / f"{program_id}.md"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def load_optional_proposed_manifest(program_id: str) -> dict[str, Any] | None:
    path = proposed_manifest_path(program_id)
    if not path.exists():
        return None
    return _read_json(path)


def ensure_proposed_manifest(seed_id: str, program_id: str) -> Path:
    path = proposed_manifest_path(program_id)
    if path.exists():
        return path
    registry = load_seed_registry()
    entries = seed_entry_map(registry)
    if seed_id not in entries:
        raise KeyError(f"Seed `{seed_id}` is not present in research_areas/seed_registry.json.")
    seed = entries[seed_id]
    _write_json(
        path,
        {
            "program_id": program_id,
            "source_seed_id": seed_id,
            "pipeline_type": seed.pipeline_type.value,
            "completion_policy": "human_gate_before_execution",
            "packets": [],
        },
    )
    return path


def validate_proposed_manifest(program_id: str) -> dict[str, object]:
    path = proposed_manifest_path(program_id)
    issues: list[str] = []
    if not path.exists():
        return {
            "program_id": program_id,
            "proposal_manifest_path": str(path),
            "passed": False,
            "issues": ["proposal_manifest_missing"],
        }

    payload = _read_json(path)
    if payload.get("program_id") != program_id:
        issues.append(f"program_id_mismatch:{payload.get('program_id')}")
    if not payload.get("source_seed_id"):
        issues.append("source_seed_id_missing")
    if payload.get("pipeline_type") not in {item.value for item in SeedPipelineType}:
        issues.append(f"invalid_pipeline_type:{payload.get('pipeline_type')}")
    packets = payload.get("packets", [])
    if not isinstance(packets, list) or not packets:
        issues.append("packets_missing")
    elif len(packets) > MAX_PROPOSED_PACKETS:
        issues.append(f"too_many_packets:{len(packets)}>{MAX_PROPOSED_PACKETS}")

    packet_ids: set[str] = set()
    for packet in packets if isinstance(packets, list) else []:
        packet_id = packet.get("packet_id")
        if not packet_id:
            issues.append("packet_id_missing")
            continue
        if packet_id in packet_ids:
            issues.append(f"duplicate_packet_id:{packet_id}")
        packet_ids.add(packet_id)
        if not packet.get("title"):
            issues.append(f"title_missing:{packet_id}")
        if not packet.get("target"):
            issues.append(f"target_missing:{packet_id}")
        if not packet.get("summary"):
            issues.append(f"summary_missing:{packet_id}")
        if packet.get("status") not in {"pending", "blocked", "deferred", "complete", "in_progress"}:
            issues.append(f"invalid_status:{packet_id}:{packet.get('status')}")
    for packet in packets if isinstance(packets, list) else []:
        for dependency in packet.get("depends_on", []):
            if dependency not in packet_ids:
                issues.append(f"missing_dependency:{packet.get('packet_id')}->{dependency}")

    return {
        "program_id": program_id,
        "proposal_manifest_path": str(path),
        "passed": not issues,
        "issues": issues,
    }


def build_proposal_context(seed_id: str, program_id: str) -> dict[str, object]:
    registry = load_seed_registry()
    entries = seed_entry_map(registry)
    if seed_id not in entries:
        raise KeyError(f"Seed `{seed_id}` is not present in research_areas/seed_registry.json.")
    seed = entries[seed_id]
    proposal = load_optional_proposed_manifest(program_id)
    return {
        "seed_id": seed.seed_id,
        "program_id": program_id,
        "seed_spec_path": seed.spec_path,
        "seed_status": seed.status.value,
        "pipeline_type": seed.pipeline_type.value,
        "seed_summary": seed.summary,
        "decision_reason": seed.decision_reason,
        "superseded_by": list(seed.superseded_by),
        "proposal_manifest_path": str(proposed_manifest_path(program_id)),
        "proposal_plan_path": str(proposal_plan_markdown_path(program_id)),
        "planning_debate_path": str(planning_debate_path(program_id)),
        "proposal_manifest_exists": proposal is not None,
        "proposal_manifest": proposal,
    }


def render_proposal_plan_markdown(seed_id: str, program_id: str) -> str:
    context = build_proposal_context(seed_id, program_id)
    proposal = context["proposal_manifest"]
    lines = [
        f"# {program_id} Proposal Plan",
        "",
        f"- seed_id: `{seed_id}`",
        f"- seed_spec: `{context['seed_spec_path']}`",
        f"- pipeline_type: `{context['pipeline_type']}`",
        f"- proposal_manifest: `{context['proposal_manifest_path']}`",
        f"- planning_debate: `{context['planning_debate_path']}`",
        "",
    ]
    if not proposal:
        lines.extend(
            [
                "No proposal manifest exists yet.",
                "",
                "Next action:",
                "- run `supervisor_proposal.py --execute` to draft a bounded proposal manifest and planning debate receipt.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(["## Proposed Packets", ""])
    for index, packet in enumerate(proposal.get("packets", []), start=1):
        lines.extend(
            [
                f"### {index}. {packet.get('title', 'Untitled Packet')}",
                "",
                f"- packet_id: `{packet.get('packet_id', 'missing')}`",
                f"- status: `{packet.get('status', 'missing')}`",
                f"- target: `{packet.get('target', 'missing')}`",
                f"- summary: {packet.get('summary', '')}",
            ]
        )
        depends_on = packet.get("depends_on", [])
        if depends_on:
            lines.append(f"- depends_on: {', '.join(f'`{dep}`' for dep in depends_on)}")
        allowed_artifacts = packet.get("allowed_artifacts", [])
        if allowed_artifacts:
            lines.append("- allowed_artifacts:")
            lines.extend(f"  - `{path}`" for path in allowed_artifacts)
        if packet.get("success_condition"):
            lines.append(f"- success_condition: {packet['success_condition']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def sync_proposal_plan_markdown(seed_id: str, program_id: str) -> Path:
    target = proposal_plan_markdown_path(program_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_proposal_plan_markdown(seed_id, program_id))
    return target


def ensure_planning_debate(program_id: str) -> Path:
    target = planning_debate_path(program_id)
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "# Planning Debate\n\n"
        f"## Program Proposal — `{program_id}`\n\n"
        "This file records pre-registry packet planning for a seed-driven proposal.\n"
    )
    return target


def build_proposal_prompt(seed_id: str, program_id: str, context_path: Path) -> str:
    context = build_proposal_context(seed_id, program_id)
    pipeline_type = context["pipeline_type"]
    pipeline_guidance = {
        "build": "Packets should resolve to code/test/integration work.",
        "research": "Packets should resolve to markdown/synthesis/evidence work, not Python implementation.",
        "product": "Packets should resolve to user-facing product/design/docs/tooling work with bounded deliverables.",
    }[pipeline_type]
    return (
        "You are the Spec Agent for a seed-to-proposal pass.\n\n"
        "Read these files first:\n"
        f"- `{context_path}`\n"
        f"- `{context['seed_spec_path']}`\n"
        f"- `{context['planning_debate_path']}`\n"
        f"- `{context['proposal_manifest_path']}`\n"
        f"- `{context['proposal_plan_path']}`\n\n"
        "Task:\n"
        "1. Draft or revise a bounded proposal manifest from the seed.\n"
        "2. Keep the backlog small: 1 to 5 packets maximum.\n"
        "3. Append one new planning turn to the planning debate file explaining the packet order.\n"
        "4. Refresh the proposal manifest and stop.\n\n"
        "Rules:\n"
        "- do not edit code\n"
        "- do not create registry entries\n"
        "- do not create genesis files\n"
        "- do not open a routable program\n"
        "- the output is a proposal manifest only\n"
        f"- pipeline type is `{pipeline_type}`: {pipeline_guidance}\n"
        "- every packet must have a target, summary, and explicit success condition\n"
        "- include only packet work that follows directly from the seed\n\n"
        "Allowed artifacts:\n"
        f"- `{context['proposal_manifest_path']}`\n"
        f"- `{context['planning_debate_path']}`\n\n"
        "After editing, stop.\n\n"
        f"Context:\n{json.dumps(context, indent=2)}\n"
    )


def run_proposal(seed_id: str, program_id: str, *, output_dir: Path, execute: bool) -> ProposalResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    proposed_manifest_directory().mkdir(parents=True, exist_ok=True)
    ensure_proposed_manifest(seed_id, program_id)
    ensure_planning_debate(program_id)
    proposal_plan_path = sync_proposal_plan_markdown(seed_id, program_id)

    context_path = output_dir / f"{program_id}_proposal_context.json"
    prompt_path = output_dir / f"{program_id}_proposal_prompt.txt"
    stdout_path = output_dir / f"{program_id}_proposal_stdout.txt"
    stderr_path = output_dir / f"{program_id}_proposal_stderr.txt"
    debug_path = output_dir / f"{program_id}_proposal_debug.log"
    usage_path = output_dir / f"{program_id}_proposal_usage.json"

    context = build_proposal_context(seed_id, program_id)
    context_path.write_text(json.dumps(context, indent=2) + "\n")
    prompt_text = build_proposal_prompt(seed_id, program_id, context_path)

    configs = load_wrapper_configs()
    claude = configs[Actor.CLAUDE]
    invocation = invoke_agent(
        command=claude.command,
        prompt_text=prompt_text,
        prompt_path=prompt_path,
        debug_path=debug_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        usage_path=usage_path,
        execute=execute,
        allowed_repo_paths=(
            str(proposed_manifest_path(program_id).relative_to(REPO_ROOT)),
            str(planning_debate_path(program_id).relative_to(REPO_ROOT)),
            str(proposal_plan_path.relative_to(REPO_ROOT)),
        ),
        default_model_name=claude.model_name,
    )
    proposal_plan_path = sync_proposal_plan_markdown(seed_id, program_id)
    validation = validate_proposed_manifest(program_id)
    if invocation.unauthorized_repo_paths:
        validation = {
            **validation,
            "passed": False,
            "issues": list(validation["issues"])
            + [f"unauthorized_repo_write:{path}" for path in invocation.unauthorized_repo_paths],
        }
    telemetry = None if invocation.turn_usage is None else invocation.turn_usage.__dict__
    return ProposalResult(
        executed=invocation.executed,
        command=invocation.command,
        context_path=str(context_path),
        prompt_path=invocation.prompt_path,
        proposal_manifest_path=str(proposed_manifest_path(program_id)),
        proposal_plan_path=str(proposal_plan_path),
        planning_debate_path=str(planning_debate_path(program_id)),
        stdout_path=invocation.stdout_path,
        stderr_path=invocation.stderr_path,
        debug_path=invocation.debug_path,
        usage_path=invocation.usage_path,
        modified_repo_paths=invocation.modified_repo_paths,
        unauthorized_repo_paths=invocation.unauthorized_repo_paths,
        exit_code=invocation.exit_code,
        telemetry=telemetry,
        validation=validation,
    )


def _print_result(result: ProposalResult) -> None:
    print(f"Context path: {result.context_path}")
    print(f"Prompt path: {result.prompt_path}")
    print(f"Proposal manifest path: {result.proposal_manifest_path}")
    print(f"Proposal plan path: {result.proposal_plan_path}")
    print(f"Planning debate path: {result.planning_debate_path}")
    print(f"Executed: {result.executed}")
    print(f"Command: {list(result.command)}")
    if result.executed:
        print(f"Stdout path: {result.stdout_path}")
        print(f"Stderr path: {result.stderr_path}")
        print(f"Debug path: {result.debug_path}")
        print(f"Usage path: {result.usage_path}")
        print(f"Exit code: {result.exit_code}")
        if result.telemetry is not None:
            print(
                "Usage telemetry: "
                f"captured={result.telemetry['telemetry_captured']} "
                f"model={result.telemetry['model_name']} "
                f"input_tokens={result.telemetry['input_tokens']} "
                f"output_tokens={result.telemetry['output_tokens']} "
                f"estimated_cost_usd={result.telemetry['estimated_cost_usd']}"
            )
        if result.modified_repo_paths:
            print(f"Modified repo paths: {list(result.modified_repo_paths)}")
        if result.unauthorized_repo_paths:
            print(f"Unauthorized repo paths: {list(result.unauthorized_repo_paths)}")
    print(
        f"Proposal validation: passed={result.validation['passed']} "
        f"issues={result.validation['issues']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Draft a pre-registry proposal manifest from a research seed.")
    parser.add_argument("--seed-id", required=True)
    parser.add_argument("--program-id", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/proposal"))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    result = run_proposal(
        args.seed_id,
        args.program_id,
        output_dir=args.output_dir,
        execute=args.execute,
    )
    _print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
