from __future__ import annotations

import argparse
import json
import re
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from ztare.common.paths import REPO_ROOT
from ztare.supervisor.supervisor_backlog import sync_program_plan_markdown
from ztare.supervisor.supervisor_manifest import (
    advance_manifest_packet,
    load_optional_program_manifest,
    next_manifest_packet,
)
from ztare.supervisor.supervisor_registry import registry_path
from ztare.supervisor.supervisor_state import (
    Actor,
    HandoffEvent,
    HumanGateReason,
    StatusReason,
    TurnUsageTelemetry,
    event_to_dict,
    status_from_dict,
    status_to_dict,
    transition_input_from_dict,
)
from ztare.supervisor.supervisor_transitions import apply_transition

TURN_HEADER_RE = re.compile(r"^## Turn (\d+)\b", re.MULTILINE)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(payload) + "\n")


def _append_human_turn(status, *, decision: str, note: str) -> int:
    if not status.debate_file:
        return status.debate_last_turn or 0
    debate_path = Path(status.debate_file)
    if not debate_path.is_absolute():
        debate_path = REPO_ROOT / debate_path
    existing_text = debate_path.read_text() if debate_path.exists() else ""
    last_turn = max((int(item) for item in TURN_HEADER_RE.findall(existing_text)), default=0)
    new_turn = last_turn + 1

    heading = {
        "close": "Promotion accepted. Program closed at the human gate.",
        "freeze": "Promotion accepted. Program frozen at the human gate.",
        "resume": "Human gate resolved. Work resumes at A1.",
    }[decision]
    body_lines = [
        "",
        f"## Turn {new_turn} — Human",
        "",
        f"### {heading}",
        "",
        f"Run: `{status.run_id}`",
        f"Gate: `{status.human_gate_reason.value if status.human_gate_reason is not None else 'none'}`",
        "",
        note.strip() if note.strip() else "Human gate resolved through explicit supervisor command.",
        "",
        "<done>",
        "",
    ]
    prefix = existing_text.rstrip()
    if prefix:
        prefix += "\n"
    debate_path.write_text(prefix + "\n".join(body_lines))
    return new_turn


def _update_registry_entry(
    program_id: str,
    *,
    status_value: str,
    owner_mode: str,
    last_turn: int,
    registry_file: Path,
) -> None:
    payload = _read_json(registry_file)
    entry = payload["programs"][program_id]
    entry["status"] = status_value
    entry["owner_mode"] = owner_mode
    entry["last_turn"] = last_turn
    entry["reopen_condition"] = None
    _write_json(registry_file, payload)


def _close_or_freeze_program(args: argparse.Namespace) -> int:
    status = status_from_dict(_read_json(args.status_path))
    if status.state.value != "D" or status.next_actor != Actor.HUMAN:
        raise RuntimeError("Gate resolution requires a run parked at D with next_actor=human.")
    if status.human_gate_reason != HumanGateReason.CONTRACT_PROMOTION:
        raise RuntimeError(
            "Close/freeze resolution currently only supports human gate `contract_promotion`."
        )

    new_turn = _append_human_turn(status, decision=args.decision, note=args.note)
    manifest = load_optional_program_manifest(status.active_program)
    next_packet = next_manifest_packet(manifest)
    manifest_update = None
    if next_packet is not None:
        manifest_update = advance_manifest_packet(status.active_program, packet_id=next_packet.packet_id)
        sync_program_plan_markdown(status.active_program)

    new_status = replace(
        status,
        revision=status.revision + 1,
        last_actor=Actor.HUMAN,
        next_actor=Actor.HUMAN,
        status_reason=(
            StatusReason.PROGRAM_CLOSED
            if args.decision == "close"
            else StatusReason.PROGRAM_FROZEN
        ),
        debate_last_turn=new_turn,
        owner_mode="frozen",
        human_gate_resolved=True,
        closed_programs=tuple(sorted(set(status.closed_programs) | {status.active_program})),
        last_turn_usage=TurnUsageTelemetry(model_name="human_gate", telemetry_captured=False),
    )
    _write_json(args.status_path, status_to_dict(new_status))

    event = HandoffEvent(
        revision=new_status.revision,
        actor=Actor.HUMAN,
        prior_state=status.state,
        new_state=status.state,
        reason=(
            args.note.strip()
            or (
                "Human resolved contract promotion gate and closed the program."
                if args.decision == "close"
                else "Human resolved contract promotion gate and froze the program."
            )
        ),
        timestamp=datetime.now(timezone.utc).isoformat(),
        artifact_paths=new_status.artifact_paths,
        human_gate_reason=status.human_gate_reason,
    )
    _append_jsonl(args.events_path, event_to_dict(event))
    _update_registry_entry(
        status.active_program,
        status_value="closed" if args.decision == "close" else "frozen",
        owner_mode="frozen",
        last_turn=new_turn,
        registry_file=args.registry_path,
    )

    print(f"Resolved human gate for program: {status.active_program}")
    print(f"Decision: {args.decision}")
    print(f"Registry status: {'closed' if args.decision == 'close' else 'frozen'}")
    print(f"Debate turn: {new_turn}")
    if manifest_update is not None:
        print(f"Manifest completed packet: {manifest_update['completed_packet_id']}")
    return 0


def _resume_program(args: argparse.Namespace) -> int:
    status = status_from_dict(_read_json(args.status_path))
    if status.state.value != "D" or status.next_actor != Actor.HUMAN:
        raise RuntimeError("Resume requires a run parked at D with next_actor=human.")

    turn_number = _append_human_turn(status, decision="resume", note=args.note)
    request_payload = {
        "actor": "human",
        "expected_revision": status.revision,
        "target_state": "A1",
        "declared_scope": {
            "program_id": status.active_program,
            "target": status.active_target,
        },
        "note": args.note.strip() or "Human gate resolved; resume work.",
    }
    outcome = apply_transition(status, transition_input_from_dict(request_payload))
    resumed_status = replace(
        outcome.status,
        debate_last_turn=turn_number,
        owner_mode="debate",
        closed_programs=tuple(
            item for item in outcome.status.closed_programs if item != status.active_program
        ),
    )
    _write_json(args.status_path, status_to_dict(resumed_status))
    _append_jsonl(args.events_path, event_to_dict(outcome.event))
    _update_registry_entry(
        status.active_program,
        status_value="active",
        owner_mode="debate",
        last_turn=turn_number,
        registry_file=args.registry_path,
    )
    print(f"Resolved human gate for program: {status.active_program}")
    print("Decision: resume")
    print(f"Transition: {status.state.value} -> {resumed_status.state.value}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve a supervisor human gate.")
    parser.add_argument("--status-path", type=Path, required=True)
    parser.add_argument("--events-path", type=Path, required=True)
    parser.add_argument("--decision", choices=("resume", "close", "freeze"), required=True)
    parser.add_argument("--note", default="")
    parser.add_argument("--registry-path", type=Path, default=registry_path())
    args = parser.parse_args()

    if args.decision == "resume":
        return _resume_program(args)
    return _close_or_freeze_program(args)


if __name__ == "__main__":
    raise SystemExit(main())
