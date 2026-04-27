from __future__ import annotations

import argparse
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from src.ztare.common.paths import REPO_ROOT
from src.ztare.validator.utilities.document_assembler import (
    assemble_document_from_manifest,
    load_document_manifest,
)
from src.ztare.supervisor.supervisor_attended_autoloop import cmd_attended_autoloop
from src.ztare.supervisor.supervisor_backlog import sync_program_plan_markdown
from src.ztare.supervisor.supervisor_gate_resolution import (
    _append_human_turn,
    _append_jsonl,
    _update_registry_entry,
)
from src.ztare.supervisor.supervisor_loop import cmd_init
from src.ztare.supervisor.supervisor_manifest import (
    derive_packet_read_bundle,
    load_optional_program_manifest,
    next_manifest_packet,
    advance_manifest_packet,
    should_auto_promote_contract_promotion,
)
from src.ztare.supervisor.supervisor_registry import registry_path
from src.ztare.supervisor.supervisor_state import (
    Actor,
    HandoffEvent,
    HumanGateReason,
    StatusReason,
    SupervisorState,
    TurnUsageTelemetry,
    event_to_dict,
    status_from_dict,
    status_to_dict,
)
from src.ztare.supervisor.supervisor_wrappers import load_wrapper_configs, wrapper_config_path


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _status_paths_for_run(active_runs_root: Path, run_id: str) -> tuple[Path, Path, Path]:
    run_root = active_runs_root / run_id
    return run_root / "status.json", run_root / "events.jsonl", run_root / "staging"


def _run_suffix(run_id: str, *, prefix: str) -> int:
    if not run_id.startswith(prefix):
        return -1
    suffix = run_id[len(prefix) :]
    return int(suffix) if suffix.isdigit() else -1


def _next_run_id(*, program_id: str, active_runs_root: Path) -> str:
    prefix = f"{program_id}_"
    max_suffix = 0
    if active_runs_root.exists():
        for candidate in active_runs_root.iterdir():
            if not candidate.is_dir():
                continue
            max_suffix = max(max_suffix, _run_suffix(candidate.name, prefix=prefix))
    return f"{program_id}_{max_suffix + 1:03d}"


def _find_existing_run_for_target(
    *,
    program_id: str,
    target: str,
    active_runs_root: Path,
) -> str | None:
    best: tuple[int, str] | None = None
    if not active_runs_root.exists():
        return None
    for candidate in active_runs_root.iterdir():
        status_path = candidate / "status.json"
        if not status_path.exists():
            continue
        try:
            status = status_from_dict(_read_json(status_path))
        except Exception:
            continue
        if status.active_program != program_id or status.active_target != target:
            continue
        if status.human_gate_resolved and status.state == SupervisorState.D:
            continue
        suffix = _run_suffix(candidate.name, prefix=f"{program_id}_")
        if best is None or suffix > best[0]:
            best = (suffix, candidate.name)
    return best[1] if best is not None else None


def _validate_prompt_versions(*, program_id: str, target: str, wrapper_config: Path) -> None:
    manifest = load_optional_program_manifest(program_id)
    if manifest is None:
        return
    if not derive_packet_read_bundle(manifest, target=target):
        return
    expected = manifest.api_prompt_versions or {}
    configs = load_wrapper_configs(wrapper_config)

    expected_a1 = expected.get("research_a1")
    actual_a1 = configs[Actor.CLAUDE].research_a1_prompt_version
    if expected_a1 is None or actual_a1 != expected_a1:
        raise RuntimeError(
            f"research_a1 prompt version mismatch for `{program_id}`/{target}: "
            f"manifest={expected_a1!r} wrapper={actual_a1!r}"
        )

    expected_a2 = expected.get("research_a2")
    actual_a2 = configs[Actor.CODEX].research_a2_prompt_version
    if expected_a2 is None or actual_a2 != expected_a2:
        raise RuntimeError(
            f"research_a2 prompt version mismatch for `{program_id}`/{target}: "
            f"manifest={expected_a2!r} wrapper={actual_a2!r}"
        )

    expected_b = expected.get("research_b")
    actual_b = configs[Actor.CLAUDE].research_b_prompt_version
    if expected_b is None or actual_b != expected_b:
        raise RuntimeError(
            f"research_b prompt version mismatch for `{program_id}`/{target}: "
            f"manifest={expected_b!r} wrapper={actual_b!r}"
        )


def _assemble_if_configured(*, program_id: str) -> None:
    manifest = load_optional_program_manifest(program_id)
    if manifest is None or manifest.document_manifest_path is None:
        return
    assembly_manifest = load_document_manifest(REPO_ROOT / manifest.document_manifest_path)
    summary = assemble_document_from_manifest(assembly_manifest)
    print(
        f"Assembled document: output={summary['output_path']} "
        f"fragments={len(summary['fragments_included'])}"
    )


def _auto_promote_packet(
    *,
    status_path: Path,
    events_path: Path,
    registry_file: Path,
) -> None:
    status = status_from_dict(_read_json(status_path))
    if not (
        status.state == SupervisorState.D
        and status.next_actor == Actor.HUMAN
        and status.human_gate_reason == HumanGateReason.CONTRACT_PROMOTION
    ):
        raise RuntimeError("Auto-promotion requires a packet run parked at D for contract_promotion.")

    note = "Program autoloop accepted manuscript packet promotion on the ordinary happy path."
    new_turn = _append_human_turn(status, decision="freeze", note=note)
    manifest_update = advance_manifest_packet(status.active_program, target=status.active_target)
    sync_program_plan_markdown(status.active_program)

    new_status = replace(
        status,
        revision=status.revision + 1,
        last_actor=Actor.HUMAN,
        next_actor=Actor.HUMAN,
        status_reason=StatusReason.PROGRAM_FROZEN,
        debate_last_turn=new_turn,
        human_gate_resolved=True,
        owner_mode="frozen",
        last_turn_usage=TurnUsageTelemetry(model_name="human_gate", telemetry_captured=False),
    )
    _write_json(status_path, status_to_dict(new_status))
    event = HandoffEvent(
        revision=new_status.revision,
        actor=Actor.HUMAN,
        prior_state=status.state,
        new_state=status.state,
        reason=note,
        timestamp=datetime.now(timezone.utc).isoformat(),
        artifact_paths=new_status.artifact_paths,
        human_gate_reason=status.human_gate_reason,
    )
    _append_jsonl(events_path, event_to_dict(event))
    _update_registry_entry(
        status.active_program,
        status_value="active",
        owner_mode="debate",
        last_turn=new_turn,
        registry_file=registry_file,
    )
    print(
        f"Auto-promoted packet: target={status.active_target} "
        f"completed_packet={manifest_update['completed_packet_id']}"
    )


def _ensure_run_for_packet(
    *,
    program_id: str,
    target: str,
    requested_run_id: str | None,
    active_runs_root: Path,
    registry_file: Path,
    max_refinement_cost_usd: float | None,
) -> str:
    if requested_run_id is not None:
        status_path, _, _ = _status_paths_for_run(active_runs_root, requested_run_id)
        if status_path.exists():
            status = status_from_dict(_read_json(status_path))
            if status.active_program == program_id and status.active_target == target:
                return requested_run_id

    existing = _find_existing_run_for_target(
        program_id=program_id,
        target=target,
        active_runs_root=active_runs_root,
    )
    if existing is not None:
        return existing

    run_id = _next_run_id(program_id=program_id, active_runs_root=active_runs_root)
    status_path, _, _ = _status_paths_for_run(active_runs_root, run_id)
    cmd_init(
        argparse.Namespace(
            status_path=status_path,
            run_id=run_id,
            program=program_id,
            target=target,
            registry_path=registry_file,
            max_refinement_cost_usd=max_refinement_cost_usd,
        )
    )
    return run_id


def cmd_program_autoloop(args: argparse.Namespace) -> int:
    processed_packets = 0
    active_runs_root = args.active_runs_root
    requested_run_id = args.run_id

    while True:
        manifest = load_optional_program_manifest(args.program)
        next_packet = next_manifest_packet(manifest)
        if next_packet is None:
            _assemble_if_configured(program_id=args.program)
            print("Stopping: manifest exhausted.")
            return 0
        if args.max_packets is not None and processed_packets >= args.max_packets:
            print("Stopping: max_packets reached.")
            return 0

        run_id = _ensure_run_for_packet(
            program_id=args.program,
            target=next_packet.target,
            requested_run_id=requested_run_id,
            active_runs_root=active_runs_root,
            registry_file=args.registry_path,
            max_refinement_cost_usd=args.max_refinement_cost_usd,
        )
        requested_run_id = None
        status_path, events_path, staging_dir = _status_paths_for_run(active_runs_root, run_id)
        status = status_from_dict(_read_json(status_path))

        if status.state == SupervisorState.D:
            if status.human_gate_reason == HumanGateReason.CONTRACT_PROMOTION:
                if should_auto_promote_contract_promotion(manifest):
                    _auto_promote_packet(
                        status_path=status_path,
                        events_path=events_path,
                        registry_file=args.registry_path,
                    )
                    _assemble_if_configured(program_id=args.program)
                    processed_packets += 1
                    continue
                print(
                    f"Stopping: packet `{next_packet.packet_id}` reached contract_promotion "
                    "and requires human prose review."
                )
                return 0
            print(
                f"Stopping: run `{run_id}` is at D "
                f"({status.human_gate_reason.value if status.human_gate_reason else 'human_gate'})."
            )
            return 0

        _validate_prompt_versions(
            program_id=args.program,
            target=next_packet.target,
            wrapper_config=args.wrapper_config_path,
        )

        cmd_attended_autoloop(
            argparse.Namespace(
                status_path=status_path,
                events_path=events_path,
                staging_dir=staging_dir,
                summary_path=None,
                execute=args.execute,
                auto_commit=args.auto_commit,
                max_advances=args.max_advances,
                max_seconds=args.max_seconds,
                max_program_cost_usd=args.max_program_cost_usd,
                max_output_tokens=args.max_output_tokens,
                max_fresh_input_tokens=args.max_fresh_input_tokens,
                wrapper_config_path=args.wrapper_config_path,
            )
        )

        status = status_from_dict(_read_json(status_path))
        if status.state == SupervisorState.D:
            if status.human_gate_reason == HumanGateReason.CONTRACT_PROMOTION:
                if should_auto_promote_contract_promotion(manifest):
                    _auto_promote_packet(
                        status_path=status_path,
                        events_path=events_path,
                        registry_file=args.registry_path,
                    )
                    _assemble_if_configured(program_id=args.program)
                    processed_packets += 1
                    continue
                print(
                    f"Stopping: packet `{next_packet.packet_id}` reached contract_promotion "
                    "and requires human prose review."
                )
                return 0
            print(
                f"Stopping: packet `{next_packet.packet_id}` requires human judgment "
                f"({status.human_gate_reason.value if status.human_gate_reason else 'human_gate'})."
            )
            return 0

        print(
            f"Stopping: packet `{next_packet.packet_id}` autoloop exited before contract promotion "
            f"(state={status.state.value} next_actor={status.next_actor.value})."
        )
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run packet autoloops across a program manifest and assemble after successful packet promotion."
    )
    parser.add_argument("--program", required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--active-runs-root", type=Path, default=REPO_ROOT / "supervisor" / "active_runs")
    parser.add_argument("--registry-path", type=Path, default=registry_path())
    parser.add_argument("--wrapper-config-path", type=Path, default=wrapper_config_path())
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--auto-commit", action="store_true")
    parser.add_argument("--max-advances", type=int, default=12)
    parser.add_argument("--max-seconds", type=int, default=1800)
    parser.add_argument("--max-program-cost-usd", type=float, default=None)
    parser.add_argument("--max-output-tokens", type=int, default=None)
    parser.add_argument("--max-fresh-input-tokens", type=int, default=None)
    parser.add_argument("--max-packets", type=int, default=None)
    parser.add_argument("--max-refinement-cost-usd", type=float, default=None)
    parser.set_defaults(func=cmd_program_autoloop)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
