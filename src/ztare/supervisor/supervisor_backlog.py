from __future__ import annotations

import argparse
import tempfile
import json
from dataclasses import dataclass
from pathlib import Path

from ztare.common.paths import REPO_ROOT
from ztare.supervisor.supervisor_genesis import (
    genesis_path_for_program,
    load_optional_program_genesis,
)
from ztare.supervisor.supervisor_manifest import (
    ProgramManifest,
    load_optional_program_manifest,
    manifest_path_for_program,
    manifest_summary,
    validate_program_manifest,
)
from ztare.supervisor.supervisor_registry import load_program_registry, registry_entry_map
from ztare.supervisor.supervisor_state import Actor, StatusReason, status_from_dict
from ztare.supervisor.supervisor_wrappers import invoke_agent, load_wrapper_configs


@dataclass(frozen=True)
class BacklogLaunchResult:
    executed: bool
    command: tuple[str, ...]
    prompt_path: str
    context_path: str
    stdout_path: str
    stderr_path: str
    debug_path: str
    usage_path: str
    program_plan_path: str
    manifest_path: str
    modified_repo_paths: tuple[str, ...]
    unauthorized_repo_paths: tuple[str, ...]
    exit_code: int | None
    telemetry: dict[str, object] | None
    validation: dict[str, object]


def program_plan_directory() -> Path:
    return REPO_ROOT / "research_areas" / "program_plans"


def program_plan_path_for_program(program_id: str) -> Path:
    return program_plan_directory() / f"{program_id}.md"


def build_backlog_context(program_id: str) -> dict[str, object]:
    registry = load_program_registry()
    entries = registry_entry_map(registry)
    if program_id not in entries:
        raise KeyError(f"Program `{program_id}` is not present in the registry.")

    entry = entries[program_id]
    genesis = load_optional_program_genesis(program_id)
    manifest = load_optional_program_manifest(program_id)
    return {
        "program_id": program_id,
        "debate_file": entry.debate_file,
        "registry_status": entry.status.value,
        "registry_owner_mode": entry.owner_mode.value,
        "seed_spec_path": genesis.seed_spec_path if genesis is not None else None,
        "genesis_path": str(genesis_path_for_program(program_id)) if genesis is not None else None,
        "contract_boundary": genesis.contract_boundary if genesis is not None else None,
        "success_condition": genesis.success_condition if genesis is not None else None,
        "out_of_scope": list(genesis.out_of_scope) if genesis is not None else [],
        "manifest_path": str(manifest_path_for_program(program_id)),
        "program_plan_path": str(program_plan_path_for_program(program_id)),
        "manifest": manifest_summary(manifest),
    }


def render_program_plan_markdown(program_id: str, manifest: ProgramManifest | None) -> str:
    if manifest is None:
        return f"# {program_id} Program Plan\n\nNo manifest exists yet.\n"

    lines = [
        f"# {program_id} Program Plan",
        "",
        f"- manifest: `{manifest_path_for_program(program_id)}`",
        f"- completion_policy: `{manifest.completion_policy}`",
        "",
        "## Packets",
        "",
    ]
    for index, packet in enumerate(manifest.packets, start=1):
        lines.extend(
            [
                f"### {index}. {packet.title}",
                "",
                f"- packet_id: `{packet.packet_id}`",
                f"- status: `{packet.status.value}`",
                f"- target: `{packet.target}`",
                f"- summary: {packet.summary}",
            ]
        )
        if packet.depends_on:
            lines.append(f"- depends_on: {', '.join(f'`{dep}`' for dep in packet.depends_on)}")
        if packet.allowed_artifacts:
            lines.append("- allowed_artifacts:")
            lines.extend(f"  - `{path}`" for path in packet.allowed_artifacts)
        if packet.success_condition:
            lines.append(f"- success_condition: {packet.success_condition}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def sync_program_plan_markdown(program_id: str) -> Path:
    manifest = load_optional_program_manifest(program_id)
    target = program_plan_path_for_program(program_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_program_plan_markdown(program_id, manifest))
    return target


def build_backlog_prompt(program_id: str, context_path: Path) -> str:
    context = build_backlog_context(program_id)
    debate_file = context["debate_file"]
    seed_spec_path = context["seed_spec_path"]
    manifest_path = context["manifest_path"]
    plan_path = program_plan_path_for_program(program_id)
    return (
        f"You are the Spec Agent for a bounded backlog-maintenance pass on program `{program_id}`.\n\n"
        "Read these files first:\n"
        f"- `{context_path}`\n"
        f"- `{seed_spec_path}`\n"
        f"- `{debate_file}`\n"
        f"- `{manifest_path}`\n"
        f"- `{plan_path}`\n\n"
        "Task:\n"
        "1. Revise the manifest into a bounded packet backlog for the current program state.\n"
        "2. Keep packet count small and explicit.\n"
        "3. Append one new turn to the debate file that records the packet revision or confirms the current packet order.\n"
        "4. Do not edit code. Do not change supervisor state files.\n\n"
        "Rules:\n"
        "- manifest is the source of truth for packet order\n"
        "- debate file should explain why the packet order changed or why it remains correct\n"
        "- if the current manifest is already correct, make the minimal update needed to record that explicitly\n"
        "- do not open new programs\n"
        "- do not touch seeds or genesis\n\n"
        "Allowed artifacts:\n"
        f"- `{manifest_path}`\n"
        f"- `{debate_file}`\n\n"
        "After editing, stop.\n\n"
        f"Context:\n{json.dumps(context, indent=2)}\n"
    )


def run_backlog(program_id: str, *, output_dir: Path, execute: bool) -> BacklogLaunchResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    context_path = output_dir / f"{program_id}_backlog_context.json"
    prompt_path = output_dir / f"{program_id}_backlog_prompt.txt"
    stdout_path = output_dir / f"{program_id}_backlog_stdout.txt"
    stderr_path = output_dir / f"{program_id}_backlog_stderr.txt"
    debug_path = output_dir / f"{program_id}_backlog_debug.log"
    usage_path = output_dir / f"{program_id}_backlog_usage.json"

    context = build_backlog_context(program_id)
    context_path.write_text(json.dumps(context, indent=2) + "\n")
    program_plan_path = sync_program_plan_markdown(program_id)
    prompt_text = build_backlog_prompt(program_id, context_path)

    validation = validate_program_manifest(program_id)
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
            str(manifest_path_for_program(program_id).relative_to(REPO_ROOT)),
            str(Path(context["debate_file"])),
            str(program_plan_path.relative_to(REPO_ROOT)),
        ),
        default_model_name=claude.model_name,
    )
    program_plan_path = sync_program_plan_markdown(program_id)
    validation = validate_program_manifest(program_id)
    if invocation.unauthorized_repo_paths:
        validation = {
            **validation,
            "passed": False,
            "issues": list(validation["issues"])
            + [f"unauthorized_repo_write:{path}" for path in invocation.unauthorized_repo_paths],
        }
    telemetry = None if invocation.turn_usage is None else invocation.turn_usage.__dict__
    return BacklogLaunchResult(
        executed=invocation.executed,
        command=invocation.command,
        prompt_path=invocation.prompt_path,
        context_path=str(context_path),
        stdout_path=invocation.stdout_path,
        stderr_path=invocation.stderr_path,
        debug_path=invocation.debug_path,
        usage_path=invocation.usage_path,
        program_plan_path=str(program_plan_path),
        manifest_path=str(manifest_path_for_program(program_id)),
        modified_repo_paths=invocation.modified_repo_paths,
        unauthorized_repo_paths=invocation.unauthorized_repo_paths,
        exit_code=invocation.exit_code,
        telemetry=telemetry,
        validation=validation,
    )


def build_what_next(status_path: Path) -> dict[str, object]:
    status = status_from_dict(json.loads(status_path.read_text()))
    manifest = load_optional_program_manifest(status.active_program)
    manifest_info = manifest_summary(manifest)

    next_action: str
    if status.status_reason == StatusReason.PROGRAM_CLOSED:
        next_action = "program_closed"
    elif status.status_reason == StatusReason.PROGRAM_FROZEN:
        next_action = "program_frozen"
    elif status.next_actor == Actor.HUMAN:
        next_action = "resolve_human_gate"
    elif status.next_actor == Actor.VERIFIER:
        next_action = "launch_or_run_verifier"
    elif status.state.value == "A1" and manifest_info is not None:
        if manifest_info["next_packet"] is None:
            next_action = "promote_or_close_program"
        else:
            next_action = "launch_spec_for_manifest_packet"
    else:
        next_action = "launch_current_supervisor_turn"

    return {
        "run_id": status.run_id,
        "program_id": status.active_program,
        "state": status.state.value,
        "next_actor": status.next_actor.value,
        "active_target": status.active_target,
        "human_gate_reason": (
            status.human_gate_reason.value if status.human_gate_reason is not None else None
        ),
        "manifest": manifest_info,
        "next_action": next_action,
    }


def _print_result(result: BacklogLaunchResult) -> None:
    print(f"Context path: {result.context_path}")
    print(f"Prompt path: {result.prompt_path}")
    print(f"Program plan path: {result.program_plan_path}")
    print(f"Manifest path: {result.manifest_path}")
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
        f"Manifest validation: passed={result.validation['passed']} "
        f"issues={result.validation['issues']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Draft or execute a bounded backlog pass for a program manifest.")
    parser.add_argument("--program", required=True)
    parser.add_argument("--output-dir", type=Path,
                        default=Path(tempfile.gettempdir()) / "ztare_supervisor_backlog",
                        help="Output directory for backlog artifacts. Default uses the system tempdir, not /tmp.")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    result = run_backlog(args.program, output_dir=args.output_dir, execute=args.execute)
    _print_result(result)
    return 0 if result.validation["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
