from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import replace
from pathlib import Path

from src.ztare.common.paths import REPO_ROOT
from src.ztare.supervisor.supervisor_state import (
    Actor,
    ArtifactSnapshot,
    HandoffStatus,
    HumanGateReason,
    StatusReason,
    SupervisorState,
    event_to_dict,
    status_from_dict,
    status_to_dict,
    transition_input_from_dict,
)
from src.ztare.supervisor.supervisor_registry import (
    OwnerMode,
    ProgramStatus,
    derive_closed_programs,
    load_program_registry,
    registry_path,
    registry_entry_map,
)
from src.ztare.supervisor.supervisor_genesis import (
    genesis_path_for_program,
    load_optional_program_genesis,
)
from src.ztare.supervisor.supervisor_manifest import (
    advance_manifest_packet,
    load_optional_program_manifest,
    manifest_summary,
    next_manifest_packet,
)
from src.ztare.supervisor.supervisor_backlog import sync_program_plan_markdown
from src.ztare.supervisor.supervisor_pipeline import (
    actor_for_pipeline_state,
    build_actor_for_pipeline,
    derive_pipeline_type,
)
from src.ztare.supervisor.supervisor_staging import write_staging_files
from src.ztare.supervisor.supervisor_transitions import apply_transition
from src.ztare.supervisor.supervisor_wrappers import (
    launch_staged_request,
    wrapper_config_path,
)

TURN_HEADER_RE = re.compile(r"^(?:##|###) Turn (\d+)\b", re.MULTILINE)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(payload) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_repo_path(raw_path: str | None) -> Path | None:
    if raw_path is None:
        return None
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return REPO_ROOT / raw_path
def _sync_debate_receipt(
    status: HandoffStatus,
    *,
    event_reason: str,
    actor: Actor,
    prior_state: SupervisorState,
    verification_report: str | None = None,
) -> HandoffStatus:
    debate_path = _resolve_repo_path(status.debate_file)
    if debate_path is None:
        return status

    existing_text = debate_path.read_text() if debate_path.exists() else ""
    last_turn = max((int(item) for item in TURN_HEADER_RE.findall(existing_text)), default=0)

    should_append_receipt = (
        (actor == Actor.CODEX and prior_state == SupervisorState.B)
        or (actor == Actor.VERIFIER and prior_state == SupervisorState.C)
    )

    if should_append_receipt and event_reason.strip():
        turn_number = last_turn + 1
        role_label = (
            "Implementation Agent (Codex)"
            if actor == Actor.CODEX
            else "Verifier"
        )
        phase_label = "B Commit" if actor == Actor.CODEX else "C Commit"
        lines = [
            "",
            f"## Turn {turn_number} — {role_label} — {phase_label} (revision {status.revision})",
            "",
            "### Supervisor receipt.",
            "",
            event_reason.strip(),
        ]
        if actor == Actor.CODEX and status.artifact_paths.implementation:
            lines.extend(
                [
                    "",
                    "Artifacts:",
                    *[f"- `{path}`" for path in status.artifact_paths.implementation],
                ]
            )
        if actor == Actor.VERIFIER and verification_report:
            lines.extend(
                [
                    "",
                    f"Verification report: `{verification_report}`",
                ]
            )
        lines.extend(["", "<done>", ""])
        prefix = existing_text.rstrip()
        if prefix:
            prefix += "\n"
        debate_path.write_text(prefix + "\n".join(lines))
        last_turn = turn_number

    return replace(status, debate_last_turn=last_turn)


def _build_snapshot(paths: tuple[str, ...]) -> tuple[ArtifactSnapshot, ...]:
    snapshots: list[ArtifactSnapshot] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            raise FileNotFoundError(f"Artifact path does not exist: {raw_path}")
        snapshots.append(ArtifactSnapshot(path=raw_path, sha256=_sha256(path)))
    return tuple(snapshots)


def _initial_status(
    run_id: str,
    program: str,
    target: str,
    *,
    debate_file: str | None,
    debate_last_turn: int | None,
    owner_mode: str | None,
    genesis_path: str | None,
    seed_spec_path: str | None,
    contract_boundary: str | None,
    success_condition: str | None,
    out_of_scope: tuple[str, ...],
    start_state: SupervisorState,
    next_actor: Actor,
    status_reason: StatusReason,
    pipeline_type: str,
    human_gate_reason=None,
    closed_programs: tuple[str, ...],
    max_refinement_cost_usd: float | None = None,
) -> HandoffStatus:
    return HandoffStatus(
        run_id=run_id,
        revision=0,
        state=start_state,
        active_program=program,
        active_target=target,
        pipeline_type=pipeline_type,
        debate_file=debate_file,
        debate_last_turn=debate_last_turn,
        owner_mode=owner_mode,
        genesis_path=genesis_path,
        seed_spec_path=seed_spec_path,
        contract_boundary=contract_boundary,
        success_condition=success_condition,
        out_of_scope=out_of_scope,
        last_actor=Actor.SYSTEM,
        next_actor=next_actor,
        status_reason=status_reason,
        max_refinement_cost_usd=max_refinement_cost_usd,
        human_gate_reason=human_gate_reason,
        closed_programs=closed_programs,
    )


def _prepare_request_payload(raw: dict) -> dict:
    payload = dict(raw)

    if payload.get("spec_path"):
        payload["spec_snapshot"] = [
            {
                "path": payload["spec_path"],
                "sha256": _sha256(Path(payload["spec_path"])),
            }
        ]

    if payload.get("implementation_paths"):
        payload["implementation_snapshot"] = [
            {"path": path, "sha256": _sha256(Path(path))}
            for path in payload["implementation_paths"]
        ]

    if payload.get("target_state") == "A1":
        implementation_paths = tuple(payload.get("implementation_paths", ()))
        if implementation_paths:
            payload["current_implementation_snapshot"] = [
                {"path": path, "sha256": _sha256(Path(path))}
                for path in implementation_paths
            ]

    return payload


def _advance_manifest_after_successful_verifier(
    status: HandoffStatus,
    request_actor: Actor,
    request_passed: bool | None,
    *,
    fail_closed: bool,
    target_state: SupervisorState,
) -> dict[str, object] | None:
    if fail_closed:
        return None
    if status.state != SupervisorState.C:
        return None
    if request_actor != Actor.VERIFIER or request_passed is not True:
        return None
    if target_state not in {SupervisorState.A1, SupervisorState.D}:
        return None

    manifest_before = load_optional_program_manifest(status.active_program)
    next_packet = next_manifest_packet(manifest_before)
    update = advance_manifest_packet(
        status.active_program,
        packet_id=next_packet.packet_id if next_packet is not None else None,
        target=status.active_target,
    )
    sync_program_plan_markdown(status.active_program)
    return update


def cmd_init(args: argparse.Namespace) -> int:
    registry = load_program_registry(args.registry_path)
    entries = registry_entry_map(registry)
    if args.program not in entries:
        raise KeyError(f"Program `{args.program}` is not present in {args.registry_path}.")
    entry = entries[args.program]
    genesis = load_optional_program_genesis(args.program)
    pipeline_type = derive_pipeline_type(genesis.seed_spec_path if genesis is not None else None)

    start_state = SupervisorState.A1
    next_actor = actor_for_pipeline_state(pipeline_type, SupervisorState.A1)
    status_reason = StatusReason.AWAITING_EVALUATION
    human_gate_reason = None
    if entry.owner_mode == OwnerMode.IMPLEMENTATION:
        start_state = SupervisorState.B
        next_actor = build_actor_for_pipeline(pipeline_type)
        status_reason = StatusReason.AWAITING_BUILD
    elif entry.owner_mode == OwnerMode.FROZEN or entry.status in {ProgramStatus.CLOSED, ProgramStatus.FROZEN}:
        start_state = SupervisorState.D
        next_actor = Actor.HUMAN
        status_reason = StatusReason.AWAITING_HUMAN_GATE
        human_gate_reason = HumanGateReason.REOPEN_CLOSED_PROGRAM

    status = _initial_status(
        run_id=args.run_id,
        program=args.program,
        target=args.target,
        debate_file=entry.debate_file,
        debate_last_turn=entry.last_turn,
        owner_mode=entry.owner_mode.value,
        genesis_path=str(genesis_path_for_program(args.program)) if genesis is not None else None,
        seed_spec_path=genesis.seed_spec_path if genesis is not None else None,
        contract_boundary=genesis.contract_boundary if genesis is not None else None,
        success_condition=genesis.success_condition if genesis is not None else None,
        out_of_scope=genesis.out_of_scope if genesis is not None else (),
        start_state=start_state,
        next_actor=next_actor,
        status_reason=status_reason,
        pipeline_type=pipeline_type,
        human_gate_reason=human_gate_reason,
        closed_programs=derive_closed_programs(registry),
        max_refinement_cost_usd=args.max_refinement_cost_usd,
    )
    _write_json(args.status_path, status_to_dict(status))
    print(f"Initialized supervisor status at {args.status_path}")
    print(f"Debate file: {status.debate_file}")
    print(f"Last turn: {status.debate_last_turn}")
    print(f"Next actor: {status.next_actor.value}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    status = status_from_dict(_read_json(args.status_path))
    payload = status_to_dict(status)
    manifest = load_optional_program_manifest(status.active_program)
    if manifest is not None:
        payload["manifest"] = manifest_summary(manifest)
    print(json.dumps(payload, indent=2))
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    status = status_from_dict(_read_json(args.status_path))
    raw_request = _read_json(args.request_path)
    request = transition_input_from_dict(_prepare_request_payload(raw_request))
    outcome = apply_transition(status, request)
    synced_status = _sync_debate_receipt(
        outcome.status,
        event_reason=outcome.event.reason,
        actor=request.actor,
        prior_state=status.state,
        verification_report=request.verification_report,
    )
    _advance_manifest_after_successful_verifier(
        status,
        request.actor,
        request.verification_passed,
        fail_closed=outcome.fail_closed,
        target_state=request.target_state,
    )

    _write_json(args.status_path, status_to_dict(synced_status))
    _append_jsonl(args.events_path, event_to_dict(outcome.event))

    print(f"Transition: {status.state.value} -> {synced_status.state.value}")
    print(f"Next actor: {synced_status.next_actor.value}")
    print(f"Status reason: {synced_status.status_reason.value}")
    print(f"Fail closed: {outcome.fail_closed}")
    if synced_status.human_gate_reason is not None:
        print(f"Human gate: {synced_status.human_gate_reason.value}")
    print(f"Event reason: {outcome.event.reason}")
    return 0


def cmd_emit_staging(args: argparse.Namespace) -> int:
    status = status_from_dict(_read_json(args.status_path))
    context_path, request_path = write_staging_files(status, args.staging_dir)
    manifest = load_optional_program_manifest(status.active_program)
    manifest_info = manifest_summary(manifest)
    print(f"Staging context: {context_path}")
    print(f"Staging request template: {request_path}")
    print(f"Expected actor: {status.next_actor.value}")
    print(f"Active program: {status.active_program}")
    print(f"Active target: {status.active_target}")
    if manifest_info is not None and manifest_info["next_packet"] is not None:
        next_packet = manifest_info["next_packet"]
        print(f"Manifest packet: {next_packet['packet_id']} -> {next_packet['target']}")
    return 0


def cmd_commit_staging(args: argparse.Namespace) -> int:
    status = status_from_dict(_read_json(args.status_path))
    staging_path = args.staging_path
    raw_request = _read_json(staging_path)
    request = transition_input_from_dict(_prepare_request_payload(raw_request))
    outcome = apply_transition(status, request)
    synced_status = _sync_debate_receipt(
        outcome.status,
        event_reason=outcome.event.reason,
        actor=request.actor,
        prior_state=status.state,
        verification_report=request.verification_report,
    )
    _advance_manifest_after_successful_verifier(
        status,
        request.actor,
        request.verification_passed,
        fail_closed=outcome.fail_closed,
        target_state=request.target_state,
    )

    _write_json(args.status_path, status_to_dict(synced_status))
    _append_jsonl(args.events_path, event_to_dict(outcome.event))

    archive_dir = args.staging_dir / "committed"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived_path = archive_dir / staging_path.name
    staging_path.replace(archived_path)

    print(f"Committed staging request: {archived_path}")
    print(f"Transition: {status.state.value} -> {synced_status.state.value}")
    print(f"Next actor: {synced_status.next_actor.value}")
    print(f"Fail closed: {outcome.fail_closed}")
    if synced_status.human_gate_reason is not None:
        print(f"Human gate: {synced_status.human_gate_reason.value}")
    return 0


def cmd_launch_staging(args: argparse.Namespace) -> int:
    status = status_from_dict(_read_json(args.status_path))
    context_path, request_path = write_staging_files(status, args.staging_dir)
    manifest = load_optional_program_manifest(status.active_program)
    manifest_info = manifest_summary(manifest)
    if status.next_actor == Actor.HUMAN:
        print(f"Staging context: {context_path}")
        print(f"Staging request template: {request_path}")
        if manifest_info is not None and manifest_info["next_packet"] is not None:
            next_packet = manifest_info["next_packet"]
            print(f"Manifest packet: {next_packet['packet_id']} -> {next_packet['target']}")
        print("Actor: human")
        print("Mode: human_gate")
        print("Executed: False")
        print("Human gate reached. No wrapper is launched for `human`.")
        print("Use `make supervisor-show ...` and inspect the staged human request directly.")
        return 0
    result = launch_staged_request(
        status=status,
        staging_dir=args.staging_dir,
        execute=args.execute,
        config_path=args.wrapper_config_path,
    )
    print(f"Staging context: {context_path}")
    print(f"Staging request template: {request_path}")
    if manifest_info is not None and manifest_info["next_packet"] is not None:
        next_packet = manifest_info["next_packet"]
        print(f"Manifest packet: {next_packet['packet_id']} -> {next_packet['target']}")
    print(f"Actor: {result.actor.value}")
    print(f"Mode: {result.mode.value}")
    print(f"Executed: {result.executed}")
    print(f"Command: {list(result.command)}")
    if result.prompt_path is not None:
        print(f"Prompt path: {result.prompt_path}")
    if result.debug_path is not None:
        print(f"Debug path: {result.debug_path}")
    if result.report_path is not None:
        print(f"Report path: {result.report_path}")
    if result.usage_path is not None:
        print(f"Usage path: {result.usage_path}")
    if result.stdout_path is not None:
        print(f"Stdout path: {result.stdout_path}")
    if result.stderr_path is not None:
        print(f"Stderr path: {result.stderr_path}")
    if result.sandbox_root is not None:
        print(f"Sandbox root: {result.sandbox_root}")
    if result.read_allowlist_paths:
        print(f"Read allowlist paths: {list(result.read_allowlist_paths)}")
    if result.exit_code is not None:
        print(f"Exit code: {result.exit_code}")
    if result.output_envelope_limit is not None:
        print(f"Output envelope limit: {result.output_envelope_limit}")
    if result.output_envelope_exceeded:
        print(
            "Output envelope exceeded: "
            f"estimated_output_tokens={result.estimated_output_tokens_emitted}"
        )
    if result.turn_usage is not None:
        cost_label = (
            "unpriced_exact_mode"
            if result.turn_usage.telemetry_captured
            and result.turn_usage.estimated_cost_usd == 0.0
            else str(result.turn_usage.estimated_cost_usd)
        )
        print(
            "Usage telemetry: "
            f"captured={result.turn_usage.telemetry_captured} "
            f"model={result.turn_usage.model_name} "
            f"input_tokens={result.turn_usage.input_tokens} "
            f"output_tokens={result.turn_usage.output_tokens} "
            f"estimated_cost_usd={cost_label}"
        )
    if result.modified_repo_paths:
        print(f"Modified repo paths: {list(result.modified_repo_paths)}")
    if result.unauthorized_repo_paths:
        print(f"Unauthorized repo paths: {list(result.unauthorized_repo_paths)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phase 1 supervisor loop shell.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize a supervisor status file.")
    init_parser.add_argument("--status-path", type=Path, required=True)
    init_parser.add_argument("--run-id", required=True)
    init_parser.add_argument("--program", required=True)
    init_parser.add_argument("--target", required=True)
    init_parser.add_argument("--registry-path", type=Path, default=registry_path())
    init_parser.add_argument("--max-refinement-cost-usd", type=float, default=None)
    init_parser.set_defaults(func=cmd_init)

    show_parser = subparsers.add_parser("show", help="Show current supervisor status.")
    show_parser.add_argument("--status-path", type=Path, required=True)
    show_parser.set_defaults(func=cmd_show)

    apply_parser = subparsers.add_parser("apply", help="Apply a transition request.")
    apply_parser.add_argument("--status-path", type=Path, required=True)
    apply_parser.add_argument("--events-path", type=Path, required=True)
    apply_parser.add_argument("--request-path", type=Path, required=True)
    apply_parser.set_defaults(func=cmd_apply)

    emit_parser = subparsers.add_parser("emit-staging", help="Emit next-actor staging context and request template.")
    emit_parser.add_argument("--status-path", type=Path, required=True)
    emit_parser.add_argument("--staging-dir", type=Path, required=True)
    emit_parser.set_defaults(func=cmd_emit_staging)

    commit_parser = subparsers.add_parser("commit-staging", help="Commit a staged transition request through the supervisor kernel.")
    commit_parser.add_argument("--status-path", type=Path, required=True)
    commit_parser.add_argument("--events-path", type=Path, required=True)
    commit_parser.add_argument("--staging-dir", type=Path, required=True)
    commit_parser.add_argument("--staging-path", type=Path, required=True)
    commit_parser.set_defaults(func=cmd_commit_staging)

    launch_parser = subparsers.add_parser(
        "launch-staging",
        help="Emit staging and invoke the configured wrapper without committing supervisor state.",
    )
    launch_parser.add_argument("--status-path", type=Path, required=True)
    launch_parser.add_argument("--staging-dir", type=Path, required=True)
    launch_parser.add_argument("--wrapper-config-path", type=Path, default=wrapper_config_path())
    launch_parser.add_argument("--execute", action="store_true")
    launch_parser.set_defaults(func=cmd_launch_staging)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
