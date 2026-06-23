from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import time

from ztare.supervisor.supervisor_loop import (
    _append_jsonl,
    _advance_manifest_after_successful_verifier,
    _prepare_request_payload,
    _read_json,
    _sync_debate_receipt,
    _write_json,
)
from ztare.supervisor.supervisor_manifest import (
    load_optional_program_manifest,
    manifest_summary,
    packet_for_target,
)
from ztare.supervisor.supervisor_state import (
    Actor,
    HandoffStatus,
    HumanGateReason,
    SupervisorState,
    TransitionInput,
    TransitionOutcome,
    TurnUsageTelemetry,
    event_to_dict,
    status_from_dict,
    status_to_dict,
    transition_input_from_dict,
)
from ztare.supervisor.supervisor_staging import write_staging_files
from ztare.supervisor.supervisor_transitions import apply_transition
from ztare.supervisor.supervisor_wrappers import (
    WrapperLaunchResult,
    WrapperMode,
    launch_staged_request,
    wrapper_config_path,
)


@dataclass(frozen=True)
class CommitDecision:
    should_commit: bool
    stop_reason: str
    requires_manual_commit: bool


@dataclass(frozen=True)
class CycleSummary:
    cycle_index: int
    revision: int
    actor: str
    state: str
    packet_id: str | None
    request_path: str
    launch_exit_code: int | None
    turn_cost_label: str
    preview_state: str
    preview_fail_closed: bool
    committed: bool
    next_state: str
    next_actor: str
    stop_reason: str | None


def format_turn_cost_label(turn_usage: TurnUsageTelemetry | None) -> str:
    if turn_usage is None:
        return "n/a"
    if turn_usage.estimated_cost_usd > 0:
        return f"${turn_usage.estimated_cost_usd:.8f}".rstrip("0").rstrip(".")
    if turn_usage.telemetry_captured:
        return "unpriced_exact_mode"
    return "n/a"


def fresh_input_tokens(turn_usage: TurnUsageTelemetry | None) -> int:
    if turn_usage is None:
        return 0
    if turn_usage.cache_read_input_tokens > turn_usage.input_tokens:
        base_uncached = turn_usage.input_tokens
    else:
        base_uncached = max(turn_usage.input_tokens - turn_usage.cache_read_input_tokens, 0)
    return base_uncached + turn_usage.cache_creation_input_tokens


def _packet_token_budget(status: HandoffStatus) -> dict[str, int]:
    manifest = load_optional_program_manifest(status.active_program)
    packet = packet_for_target(manifest, target=status.active_target)
    return dict(packet.token_budget or {}) if packet is not None and packet.token_budget else {}


def _effective_token_limits(
    *,
    status: HandoffStatus,
    max_output_tokens: int | None,
    max_fresh_input_tokens: int | None,
) -> tuple[int | None, int | None]:
    effective_max_output_tokens = max_output_tokens
    effective_max_fresh_input_tokens = max_fresh_input_tokens
    if not (status.pipeline_type == "research" and status.state == SupervisorState.A2):
        return effective_max_output_tokens, effective_max_fresh_input_tokens

    packet_budget = _packet_token_budget(status)
    budget_output_tokens = packet_budget.get("a2_max_output")
    if budget_output_tokens is not None:
        effective_max_output_tokens = (
            budget_output_tokens
            if effective_max_output_tokens is None
            else min(effective_max_output_tokens, budget_output_tokens)
        )
    budget_fresh_input_tokens = packet_budget.get("a2_max_fresh_input")
    if budget_fresh_input_tokens is not None:
        effective_max_fresh_input_tokens = (
            budget_fresh_input_tokens
            if effective_max_fresh_input_tokens is None
            else min(effective_max_fresh_input_tokens, budget_fresh_input_tokens)
        )
    return effective_max_output_tokens, effective_max_fresh_input_tokens


def decide_commit_action(
    *,
    auto_commit: bool,
    launch_result: WrapperLaunchResult,
    preview_outcome: TransitionOutcome,
    max_output_tokens: int | None = None,
    max_fresh_input_tokens: int | None = None,
) -> CommitDecision:
    if launch_result.output_envelope_exceeded:
        return CommitDecision(
            should_commit=False,
            stop_reason="output_envelope_exceeded",
            requires_manual_commit=False,
        )
    if launch_result.exit_code not in (None, 0) and launch_result.mode != WrapperMode.LOCAL_VERIFIER:
        return CommitDecision(
            should_commit=False,
            stop_reason="launch_exit_nonzero",
            requires_manual_commit=False,
        )
    if max_output_tokens is not None:
        output_tokens = launch_result.turn_usage.output_tokens if launch_result.turn_usage is not None else 0
        if output_tokens > max_output_tokens:
            return CommitDecision(
                should_commit=False,
                stop_reason="output_tokens_limit_exceeded",
                requires_manual_commit=True,
            )
    if max_fresh_input_tokens is not None:
        if fresh_input_tokens(launch_result.turn_usage) > max_fresh_input_tokens:
            return CommitDecision(
                should_commit=False,
                stop_reason="fresh_input_tokens_limit_exceeded",
                requires_manual_commit=True,
            )
    if launch_result.unauthorized_repo_paths:
        return CommitDecision(
            should_commit=False,
            stop_reason="unauthorized_repo_write",
            requires_manual_commit=False,
        )
    if preview_outcome.fail_closed:
        return CommitDecision(
            should_commit=False,
            stop_reason="preview_fail_closed",
            requires_manual_commit=True,
        )
    if preview_outcome.status.state == SupervisorState.D:
        return CommitDecision(
            should_commit=False,
            stop_reason="target_state_D_requires_manual_commit",
            requires_manual_commit=True,
        )
    if not auto_commit:
        return CommitDecision(
            should_commit=False,
            stop_reason="manual_commit_required",
            requires_manual_commit=True,
        )
    return CommitDecision(
        should_commit=True,
        stop_reason="auto_commit_authorized",
        requires_manual_commit=False,
    )


def build_commit_command(
    *,
    status_path: Path,
    events_path: Path,
    staging_dir: Path,
    request_path: Path,
) -> str:
    return (
        f"make supervisor-commit SUP_STATUS={status_path} SUP_EVENTS={events_path} "
        f"SUP_STAGING={staging_dir} SUP_REQUEST={request_path}"
    )


def _preview_request(status: HandoffStatus, request_path: Path) -> tuple[TransitionInput, TransitionOutcome]:
    raw_request = _read_json(request_path)
    request = transition_input_from_dict(_prepare_request_payload(raw_request))
    outcome = apply_transition(status, request)
    return request, outcome


def _commit_preview(
    *,
    status: HandoffStatus,
    request: TransitionInput,
    preview_outcome: TransitionOutcome,
    status_path: Path,
    events_path: Path,
    staging_dir: Path,
    request_path: Path,
) -> tuple[HandoffStatus, Path]:
    synced_status = _sync_debate_receipt(
        preview_outcome.status,
        event_reason=preview_outcome.event.reason,
        actor=request.actor,
        prior_state=status.state,
        verification_report=request.verification_report,
    )
    _advance_manifest_after_successful_verifier(
        status,
        request.actor,
        request.verification_passed,
        fail_closed=preview_outcome.fail_closed,
        target_state=request.target_state,
    )
    _write_json(status_path, status_to_dict(synced_status))
    _append_jsonl(events_path, event_to_dict(preview_outcome.event))

    archive_dir = staging_dir / "committed"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived_path = archive_dir / request_path.name
    request_path.replace(archived_path)
    return synced_status, archived_path


def _summary_path(staging_dir: Path, explicit_path: Path | None) -> Path:
    if explicit_path is not None:
        return explicit_path
    return staging_dir / "autoloop" / "cycle_summaries.jsonl"


def _pending_request_paths(staging_dir: Path) -> tuple[Path, ...]:
    if not staging_dir.exists():
        return ()
    pending: list[Path] = []
    for path in sorted(staging_dir.glob("*.json")):
        if path.name.endswith("_context.json"):
            continue
        try:
            payload = _read_json(path)
        except Exception:
            pending.append(path)
            continue
        if any(
            key in payload
            for key in (
                "turn_usage",
                "write_scope_ok",
                "modified_repo_paths",
                "unauthorized_repo_paths",
                "verification_passed",
                "current_implementation_snapshot",
            )
        ):
            pending.append(path)
    return tuple(pending)


def _append_summary(path: Path, summary: CycleSummary) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(asdict(summary)) + "\n")


def _packet_id_for_status(status: HandoffStatus) -> str | None:
    manifest = load_optional_program_manifest(status.active_program)
    summary = manifest_summary(manifest)
    if summary is None or summary["next_packet"] is None:
        return None
    return str(summary["next_packet"]["packet_id"])


def cmd_attended_autoloop(args: argparse.Namespace) -> int:
    summary_path = _summary_path(args.staging_dir, args.summary_path)
    start_time = time.monotonic()
    advances = 0

    while True:
        status = status_from_dict(_read_json(args.status_path))

        if status.state == SupervisorState.D:
            print(
                f"Stopping: run is already at D "
                f"({status.human_gate_reason.value if status.human_gate_reason else 'human_gate'})."
            )
            return 0
        if args.max_seconds is not None and (time.monotonic() - start_time) >= args.max_seconds:
            print("Stopping: max_seconds reached before next launch.")
            return 0
        if args.max_program_cost_usd is not None and status.program_cost_usd >= args.max_program_cost_usd:
            print(
                "Stopping: max_program_cost_usd reached "
                f"({status.program_cost_usd:.8f} >= {args.max_program_cost_usd:.8f})."
            )
            return 0
        pending_requests = _pending_request_paths(args.staging_dir)
        if pending_requests:
            print("Stopping: uncommitted staged request already exists.")
            for pending_path in pending_requests:
                print(f"Request: {pending_path}")
                print(
                    "Commit it first with: "
                    f"{build_commit_command(status_path=args.status_path, events_path=args.events_path, staging_dir=args.staging_dir, request_path=pending_path)}"
                )
            return 0
        if advances >= args.max_advances:
            print("Stopping: max_advances reached.")
            return 0

        context_path, request_path = write_staging_files(status, args.staging_dir)
        launch_result = launch_staged_request(
            status=status,
            staging_dir=args.staging_dir,
            execute=args.execute,
            config_path=args.wrapper_config_path,
        )
        effective_max_output_tokens, effective_max_fresh_input_tokens = _effective_token_limits(
            status=status,
            max_output_tokens=args.max_output_tokens,
            max_fresh_input_tokens=args.max_fresh_input_tokens,
        )
        if launch_result.output_envelope_exceeded:
            summary = CycleSummary(
                cycle_index=advances + 1,
                revision=status.revision,
                actor=status.next_actor.value,
                state=status.state.value,
                packet_id=_packet_id_for_status(status),
                request_path=str(request_path),
                launch_exit_code=launch_result.exit_code,
                turn_cost_label=format_turn_cost_label(launch_result.turn_usage),
                preview_state=status.state.value,
                preview_fail_closed=False,
                committed=False,
                next_state=status.state.value,
                next_actor=status.next_actor.value,
                stop_reason="output_envelope_exceeded",
            )
            _append_summary(summary_path, summary)
            print(
                f"[autoloop] cycle={summary.cycle_index} actor={summary.actor} "
                f"revision={summary.revision} stopped reason=output_envelope_exceeded "
                f"preview={status.state.value}->{status.state.value} cost={summary.turn_cost_label}"
            )
            if launch_result.output_envelope_limit is not None:
                print(
                    "Output envelope: "
                    f"limit={launch_result.output_envelope_limit} "
                    f"estimated_emitted={launch_result.estimated_output_tokens_emitted}"
                )
            print(f"Context: {context_path}")
            print(f"Request: {request_path}")
            return 0
        if launch_result.exit_code not in (None, 0) and launch_result.mode != WrapperMode.LOCAL_VERIFIER:
            summary = CycleSummary(
                cycle_index=advances + 1,
                revision=status.revision,
                actor=status.next_actor.value,
                state=status.state.value,
                packet_id=_packet_id_for_status(status),
                request_path=str(request_path),
                launch_exit_code=launch_result.exit_code,
                turn_cost_label=format_turn_cost_label(launch_result.turn_usage),
                preview_state=status.state.value,
                preview_fail_closed=False,
                committed=False,
                next_state=status.state.value,
                next_actor=status.next_actor.value,
                stop_reason="launch_exit_nonzero",
            )
            _append_summary(summary_path, summary)
            print(
                f"[autoloop] cycle={summary.cycle_index} actor={summary.actor} "
                f"revision={summary.revision} stopped reason=launch_exit_nonzero "
                f"preview={status.state.value}->{status.state.value} cost={summary.turn_cost_label}"
            )
            print(f"Context: {context_path}")
            print(f"Request: {request_path}")
            return 0
        request, preview_outcome = _preview_request(status, request_path)
        decision = decide_commit_action(
            auto_commit=args.auto_commit,
            launch_result=launch_result,
            preview_outcome=preview_outcome,
            max_output_tokens=effective_max_output_tokens,
            max_fresh_input_tokens=effective_max_fresh_input_tokens,
        )

        next_state = preview_outcome.status.state.value
        next_actor = preview_outcome.status.next_actor.value
        summary = CycleSummary(
            cycle_index=advances + 1,
            revision=status.revision,
            actor=status.next_actor.value,
            state=status.state.value,
            packet_id=_packet_id_for_status(status),
            request_path=str(request_path),
            launch_exit_code=launch_result.exit_code,
            turn_cost_label=format_turn_cost_label(launch_result.turn_usage),
            preview_state=next_state,
            preview_fail_closed=preview_outcome.fail_closed,
            committed=False,
            next_state=next_state,
            next_actor=next_actor,
            stop_reason=None if decision.should_commit else decision.stop_reason,
        )

        if decision.should_commit:
            new_status, archived_path = _commit_preview(
                status=status,
                request=request,
                preview_outcome=preview_outcome,
                status_path=args.status_path,
                events_path=args.events_path,
                staging_dir=args.staging_dir,
                request_path=request_path,
            )
            advances += 1
            summary = CycleSummary(
                **{**asdict(summary), "committed": True, "next_state": new_status.state.value, "next_actor": new_status.next_actor.value}
            )
            _append_summary(summary_path, summary)
            print(
                f"[autoloop] cycle={summary.cycle_index} actor={summary.actor} "
                f"revision={summary.revision} committed {status.state.value}->{new_status.state.value} "
                f"next_actor={new_status.next_actor.value} cost={summary.turn_cost_label} "
                f"request={archived_path.name}"
            )
            if args.max_seconds is not None and (time.monotonic() - start_time) >= args.max_seconds:
                print("Stopping: max_seconds reached after commit.")
                return 0
            if args.max_program_cost_usd is not None and new_status.program_cost_usd >= args.max_program_cost_usd:
                print(
                    "Stopping: max_program_cost_usd reached after commit "
                    f"({new_status.program_cost_usd:.8f} >= {args.max_program_cost_usd:.8f})."
                )
                return 0
            continue

        _append_summary(summary_path, summary)
        print(
            f"[autoloop] cycle={summary.cycle_index} actor={summary.actor} "
            f"revision={summary.revision} stopped reason={decision.stop_reason} "
            f"preview={status.state.value}->{next_state} cost={summary.turn_cost_label}"
        )
        if (
            effective_max_output_tokens is not None
            and launch_result.turn_usage is not None
            and launch_result.turn_usage.output_tokens > effective_max_output_tokens
        ):
            print(
                "Output tokens: "
                f"actual={launch_result.turn_usage.output_tokens} limit={effective_max_output_tokens}"
            )
        if (
            effective_max_fresh_input_tokens is not None
            and fresh_input_tokens(launch_result.turn_usage) > effective_max_fresh_input_tokens
        ):
            print(
                "Fresh input tokens: "
                f"actual={fresh_input_tokens(launch_result.turn_usage)} limit={effective_max_fresh_input_tokens}"
            )
        if launch_result.unauthorized_repo_paths:
            print("Unauthorized repo writes:")
            for path in launch_result.unauthorized_repo_paths:
                print(f"- {path}")
        print(f"Context: {context_path}")
        print(f"Request: {request_path}")
        if decision.requires_manual_commit:
            print(
                "Next manual commit command:\n"
                + build_commit_command(
                    status_path=args.status_path,
                    events_path=args.events_path,
                    staging_dir=args.staging_dir,
                    request_path=request_path,
                )
            )
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Attended autoloop wrapper over supervisor launch/commit with bounded auto-commit."
    )
    parser.add_argument("--status-path", type=Path, required=True)
    parser.add_argument("--events-path", type=Path, required=True)
    parser.add_argument("--staging-dir", type=Path, required=True)
    parser.add_argument("--wrapper-config-path", type=Path, default=wrapper_config_path())
    parser.add_argument("--summary-path", type=Path, default=None)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--auto-commit", action="store_true")
    parser.add_argument("--max-advances", type=int, default=8)
    parser.add_argument("--max-seconds", type=float, default=None)
    parser.add_argument("--max-program-cost-usd", type=float, default=None)
    parser.add_argument("--max-output-tokens", type=int, default=None)
    parser.add_argument("--max-fresh-input-tokens", type=int, default=None)
    parser.set_defaults(func=cmd_attended_autoloop)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
