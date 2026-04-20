from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.ztare.findings.prose_spec import (
    prose_spec_path_has_canonical_shape,
    validate_prose_spec_path,
)
from src.ztare.supervisor.supervisor_state import (
    Actor,
    ArtifactPaths,
    HandoffEvent,
    HandoffStatus,
    HumanGateReason,
    StatusReason,
    SupervisorState,
    TurnUsageTelemetry,
    TransitionInput,
    TransitionOutcome,
)
from src.ztare.supervisor.supervisor_pipeline import actor_for_pipeline_state, build_actor_for_pipeline

MAX_SPEC_REFINEMENT_ROUNDS = 2


def apply_transition(status: HandoffStatus, request: TransitionInput) -> TransitionOutcome:
    if request.expected_revision != status.revision:
        return _fail_closed(
            status,
            actor=request.actor,
            gate=HumanGateReason.STALE_REVISION_WRITE,
            reason="Transition request used a stale revision.",
            turn_usage=request.turn_usage,
        )
    if request.actor != status.next_actor:
        return _fail_closed(
            status,
            actor=request.actor,
            gate=HumanGateReason.STALE_REVISION_WRITE,
            reason="Transition request came from an actor that did not own the turn.",
            turn_usage=request.turn_usage,
        )
    if not request.write_scope_ok or request.unauthorized_repo_paths:
        unauthorized = ", ".join(request.unauthorized_repo_paths) or "unknown"
        return _fail_closed(
            status,
            actor=request.actor,
            gate=HumanGateReason.UNAUTHORIZED_ARTIFACT_WRITE,
            reason=(
                "Wrapper detected repository writes outside the allowed artifact scope: "
                f"{unauthorized}."
            ),
            turn_usage=request.turn_usage,
        )
    if request.declared_scope is not None and (
        request.declared_scope.program_id != status.active_program
        or request.declared_scope.target != status.active_target
    ):
        return _fail_closed(
            status,
            actor=request.actor,
            gate=HumanGateReason.SCOPE_MISMATCH,
            reason="Declared scope does not match the active program/target in supervisor state.",
            turn_usage=request.turn_usage,
        )

    current = status.state
    target = request.target_state

    if current == SupervisorState.A1:
        return _apply_from_a1(status, request)
    if current == SupervisorState.A2:
        return _apply_from_a2(status, request)
    if current == SupervisorState.B:
        return _apply_from_b(status, request)
    if current == SupervisorState.C:
        return _apply_from_c(status, request)
    if current == SupervisorState.D:
        return _apply_from_d(status, request)

    return _fail_closed(
        status,
        actor=request.actor,
        gate=HumanGateReason.STALE_REVISION_WRITE,
        reason=f"Unsupported state transition from {current.value} to {target.value}.",
        turn_usage=request.turn_usage,
    )


def _apply_from_a1(status: HandoffStatus, request: TransitionInput) -> TransitionOutcome:
    if request.target_state == SupervisorState.D:
        gate = request.human_gate_reason or HumanGateReason.REOPEN_CLOSED_PROGRAM
        return _transition(
            status,
            actor=request.actor,
            new_state=SupervisorState.D,
            status_reason=StatusReason.AWAITING_HUMAN_GATE,
            next_actor=Actor.HUMAN,
            human_gate_reason=gate,
            reason=request.note or "Human gate requested from A1.",
            turn_usage=request.turn_usage,
            increment_refinement_cost=status.spec_refinement_rounds > 0,
        )

    if request.target_state != SupervisorState.A2:
        return _fail_closed(
            status,
            actor=request.actor,
            gate=HumanGateReason.REOPEN_CLOSED_PROGRAM,
            reason="A1 may only advance to A2 or fail closed to D.",
            turn_usage=request.turn_usage,
        )

    if request.touches_closed_program or status.active_program in status.closed_programs:
        return _fail_closed(
            status,
            actor=request.actor,
            gate=HumanGateReason.REOPEN_CLOSED_PROGRAM,
            reason="A1 attempted to advance work inside a closed program without human authorization.",
            turn_usage=request.turn_usage,
        )

    return _transition(
        status,
        actor=request.actor,
        new_state=SupervisorState.A2,
        status_reason=StatusReason.AWAITING_DRAFT,
        next_actor=actor_for_pipeline_state(status.pipeline_type, SupervisorState.A2),
        reason=request.note or "Architect target approved inside open program.",
        turn_usage=request.turn_usage,
        increment_refinement_cost=status.spec_refinement_rounds > 0,
    )


def _apply_from_a2(status: HandoffStatus, request: TransitionInput) -> TransitionOutcome:
    if request.target_state == SupervisorState.A1:
        if not request.spec_refinement_requested:
            return _fail_closed(
                status,
                actor=request.actor,
                gate=HumanGateReason.SPEC_IMPLEMENTATION_MISMATCH,
                reason="A2 -> A1 requires explicit spec_refinement_requested.",
                turn_usage=request.turn_usage,
            )
        if _refinement_budget_exceeded(status, request):
            return _fail_closed(
                status,
                actor=request.actor,
                gate=HumanGateReason.SPEC_REFINEMENT_BUDGET_REACHED,
                reason="A2 refinement budget reached; supervisor requires build or human gate.",
                turn_usage=request.turn_usage,
            )
        if status.spec_refinement_rounds >= MAX_SPEC_REFINEMENT_ROUNDS:
            return _fail_closed(
                status,
                actor=request.actor,
                gate=HumanGateReason.SPEC_REFINEMENT_CAP_REACHED,
                reason="A2 refinement cap reached; supervisor requires build or human gate.",
                turn_usage=request.turn_usage,
            )
        return _transition(
            status,
            actor=request.actor,
            new_state=SupervisorState.A1,
            status_reason=StatusReason.AWAITING_EVALUATION,
            next_actor=actor_for_pipeline_state(status.pipeline_type, SupervisorState.A1),
            spec_refinement_rounds=status.spec_refinement_rounds + 1,
            reason=request.note or "Spec refinement requested; returning from A2 to A1.",
            turn_usage=request.turn_usage,
            increment_refinement_cost=True,
        )

    if request.target_state != SupervisorState.B:
        return _fail_closed(
            status,
            actor=request.actor,
            gate=HumanGateReason.SPEC_IMPLEMENTATION_MISMATCH,
            reason="A2 may only advance to B in Phase 1.",
            turn_usage=request.turn_usage,
        )

    if not request.spec_path or not request.spec_snapshot:
        return _fail_closed(
            status,
            actor=request.actor,
            gate=HumanGateReason.SPEC_IMPLEMENTATION_MISMATCH,
            reason="A2 missing spec artifact path or spec snapshot.",
            turn_usage=request.turn_usage,
        )
    if not request.expected_implementation_paths:
        return _fail_closed(
            status,
            actor=request.actor,
            gate=HumanGateReason.SPEC_IMPLEMENTATION_MISMATCH,
            reason="A2 missing expected implementation artifact set.",
            turn_usage=request.turn_usage,
        )
    if status.pipeline_type == "research":
        spec_path = Path(request.spec_path)
        validation = validate_prose_spec_path(spec_path)
        if validation["passed"] is not True:
            return _fail_closed(
                status,
                actor=request.actor,
                gate=HumanGateReason.SPEC_IMPLEMENTATION_MISMATCH,
                reason=f"Research A2 produced an invalid prose spec: {validation['issues']}.",
                turn_usage=request.turn_usage,
            )
        if not prose_spec_path_has_canonical_shape(spec_path):
            return _fail_closed(
                status,
                actor=request.actor,
                gate=HumanGateReason.SPEC_IMPLEMENTATION_MISMATCH,
                reason=(
                    "Research A2 must emit the canonical prose spec schema with top-level "
                    "`assertions`, `global_word_min`, and `global_word_max`."
                ),
                turn_usage=request.turn_usage,
            )

    artifact_paths = ArtifactPaths(
        spec=request.spec_path,
        implementation=tuple(request.expected_implementation_paths),
    )
    return _transition(
        status,
        actor=request.actor,
        new_state=SupervisorState.B,
        status_reason=StatusReason.AWAITING_BUILD,
        next_actor=build_actor_for_pipeline(status.pipeline_type),
        artifact_paths=artifact_paths,
        spec_snapshot=request.spec_snapshot,
        implementation_snapshot=(),
        verification_command=None,
        gate_on_verifier_pass=request.gate_on_verifier_pass,
        spec_refinement_rounds=0,
        reason=request.note or "Spec drafted and implementation artifact set recorded.",
        turn_usage=request.turn_usage,
        increment_refinement_cost=status.spec_refinement_rounds > 0,
    )


def _apply_from_b(status: HandoffStatus, request: TransitionInput) -> TransitionOutcome:
    if request.target_state != SupervisorState.C:
        return _fail_closed(
            status,
            actor=request.actor,
            gate=HumanGateReason.SPEC_IMPLEMENTATION_MISMATCH,
            reason="B may only advance to C in Phase 1.",
            turn_usage=request.turn_usage,
        )

    expected_paths = tuple(status.artifact_paths.implementation)
    if not expected_paths:
        return _fail_closed(
            status,
            actor=request.actor,
            gate=HumanGateReason.SPEC_IMPLEMENTATION_MISMATCH,
            reason="B does not know which implementation artifacts must be built.",
            turn_usage=request.turn_usage,
        )
    if tuple(request.implementation_paths) != expected_paths:
        return _fail_closed(
            status,
            actor=request.actor,
            gate=HumanGateReason.SPEC_IMPLEMENTATION_MISMATCH,
            reason="B declared implementation artifacts that do not match the A2 expectation.",
            turn_usage=request.turn_usage,
        )
    if not request.implementation_snapshot:
        return _fail_closed(
            status,
            actor=request.actor,
            gate=HumanGateReason.SPEC_IMPLEMENTATION_MISMATCH,
            reason="B missing implementation artifact snapshot.",
            turn_usage=request.turn_usage,
        )
    if not request.verification_command:
        return _fail_closed(
            status,
            actor=request.actor,
            gate=HumanGateReason.SPEC_IMPLEMENTATION_MISMATCH,
            reason="B missing verification command for C.",
            turn_usage=request.turn_usage,
        )

    artifact_paths = ArtifactPaths(
        spec=status.artifact_paths.spec,
        implementation=expected_paths,
        verification_report=status.artifact_paths.verification_report,
        error_report=status.artifact_paths.error_report,
    )
    return _transition(
        status,
        actor=request.actor,
        new_state=SupervisorState.C,
        status_reason=StatusReason.AWAITING_VERIFICATION,
        next_actor=Actor.VERIFIER,
        artifact_paths=artifact_paths,
        spec_snapshot=status.spec_snapshot,
        implementation_snapshot=request.implementation_snapshot,
        verification_command=request.verification_command,
        reason=request.note or "Implementation recorded and verifier command prepared.",
        turn_usage=request.turn_usage,
    )


def _apply_from_c(status: HandoffStatus, request: TransitionInput) -> TransitionOutcome:
    if request.target_state == SupervisorState.B:
        failures = status.consecutive_build_failures + 1
        if failures >= 3:
            return _fail_closed(
                status,
                actor=request.actor,
                gate=HumanGateReason.IMPLEMENTATION_TRAP,
                reason="Verifier failed three consecutive times; implementation trap triggered.",
                turn_usage=request.turn_usage,
            )
        artifact_paths = ArtifactPaths(
            spec=status.artifact_paths.spec,
            implementation=status.artifact_paths.implementation,
            verification_report=request.verification_report,
            error_report=request.error_report,
        )
        return _transition(
            status,
            actor=request.actor,
            new_state=SupervisorState.B,
            status_reason=StatusReason.AWAITING_BUILD,
            next_actor=build_actor_for_pipeline(status.pipeline_type),
            artifact_paths=artifact_paths,
            spec_snapshot=status.spec_snapshot,
            implementation_snapshot=status.implementation_snapshot,
            verification_command=status.verification_command,
            consecutive_build_failures=failures,
            spec_refinement_rounds=status.spec_refinement_rounds,
            reason=request.note or "Verifier failed; returning to builder with bounded error report.",
            turn_usage=request.turn_usage,
        )

    if request.target_state == SupervisorState.D:
        if request.verification_passed is True and not _implementation_corresponds(
            status, request.current_implementation_snapshot
        ):
            return _fail_closed(
                status,
                actor=request.actor,
                gate=HumanGateReason.SPEC_IMPLEMENTATION_MISMATCH,
                reason="Verifier pass did not correspond to the recorded implementation artifact set.",
                turn_usage=request.turn_usage,
            )
        successful_promotion = request.verification_passed is True
        gate = request.human_gate_reason or HumanGateReason.CONTRACT_PROMOTION
        return _transition(
            status,
            actor=request.actor,
            new_state=SupervisorState.D,
            status_reason=StatusReason.AWAITING_HUMAN_GATE,
            next_actor=Actor.HUMAN,
            artifact_paths=ArtifactPaths(
                spec=status.artifact_paths.spec,
                implementation=status.artifact_paths.implementation,
                verification_report=request.verification_report or status.artifact_paths.verification_report,
                error_report=(
                    None
                    if successful_promotion
                    else request.error_report or status.artifact_paths.error_report
                ),
            ),
            spec_snapshot=status.spec_snapshot,
            implementation_snapshot=status.implementation_snapshot,
            verification_command=status.verification_command,
            consecutive_build_failures=0 if successful_promotion else status.consecutive_build_failures,
            spec_refinement_rounds=0 if successful_promotion else status.spec_refinement_rounds,
            human_gate_reason=gate,
            reason=request.note or "Verifier routed to human gate.",
            turn_usage=request.turn_usage,
        )

    if request.target_state != SupervisorState.A1:
        return _fail_closed(
            status,
            actor=request.actor,
            gate=HumanGateReason.SPEC_IMPLEMENTATION_MISMATCH,
            reason="C may only advance to A1, B, or D.",
            turn_usage=request.turn_usage,
        )

    if request.verification_passed is not True:
        return _fail_closed(
            status,
            actor=request.actor,
            gate=HumanGateReason.SPEC_IMPLEMENTATION_MISMATCH,
            reason="C->A1 requires an explicit verifier pass.",
            turn_usage=request.turn_usage,
        )
    if not _implementation_corresponds(status, request.current_implementation_snapshot):
        return _fail_closed(
            status,
            actor=request.actor,
            gate=HumanGateReason.SPEC_IMPLEMENTATION_MISMATCH,
            reason="Verifier pass did not correspond to the recorded implementation artifact set.",
            turn_usage=request.turn_usage,
        )

    if status.gate_on_verifier_pass:
        return _transition(
            status,
            actor=request.actor,
            new_state=SupervisorState.D,
            status_reason=StatusReason.AWAITING_HUMAN_GATE,
            next_actor=Actor.HUMAN,
            artifact_paths=ArtifactPaths(
                spec=status.artifact_paths.spec,
                implementation=status.artifact_paths.implementation,
                verification_report=request.verification_report or status.artifact_paths.verification_report,
                error_report=None,
            ),
            spec_snapshot=status.spec_snapshot,
            implementation_snapshot=status.implementation_snapshot,
            verification_command=status.verification_command,
            consecutive_build_failures=0,
            spec_refinement_rounds=0,
            human_gate_reason=HumanGateReason.CONTRACT_PROMOTION,
            reason=request.note or "Verifier passed a terminal packet; supervisor routed to human promotion gate.",
            turn_usage=request.turn_usage,
        )

    return _transition(
        status,
        actor=request.actor,
        new_state=SupervisorState.A1,
        status_reason=StatusReason.AWAITING_EVALUATION,
        next_actor=actor_for_pipeline_state(status.pipeline_type, SupervisorState.A1),
        artifact_paths=ArtifactPaths(
            spec=status.artifact_paths.spec,
            implementation=status.artifact_paths.implementation,
            verification_report=request.verification_report or status.artifact_paths.verification_report,
            error_report=None,
        ),
        spec_snapshot=status.spec_snapshot,
        implementation_snapshot=status.implementation_snapshot,
        verification_command=status.verification_command,
        gate_on_verifier_pass=False,
        consecutive_build_failures=0,
        spec_refinement_rounds=0,
        reason=request.note or "Verifier passed and implementation corresponds to the recorded spec/build snapshot.",
        turn_usage=request.turn_usage,
    )


def _apply_from_d(status: HandoffStatus, request: TransitionInput) -> TransitionOutcome:
    if request.actor != Actor.HUMAN:
        return _fail_closed(
            status,
            actor=request.actor,
            gate=HumanGateReason.STALE_REVISION_WRITE,
            reason="Only the human may resolve D in Phase 1.",
            turn_usage=request.turn_usage,
        )
    if request.target_state != SupervisorState.A1:
        return _fail_closed(
            status,
            actor=request.actor,
            gate=HumanGateReason.STALE_REVISION_WRITE,
            reason="Human resolution must return the loop to A1 in Phase 1.",
            turn_usage=request.turn_usage,
        )

    return _transition(
        status,
        actor=request.actor,
        new_state=SupervisorState.A1,
        status_reason=StatusReason.AWAITING_EVALUATION,
        next_actor=actor_for_pipeline_state(status.pipeline_type, SupervisorState.A1),
        artifact_paths=status.artifact_paths,
        spec_snapshot=status.spec_snapshot,
        implementation_snapshot=status.implementation_snapshot,
        verification_command=status.verification_command,
        gate_on_verifier_pass=False,
        consecutive_build_failures=0,
        spec_refinement_rounds=0,
        human_gate_reason=None,
        human_gate_resolved=True,
        reason=request.note or "Human gate resolved; loop returned to A1.",
        turn_usage=request.turn_usage,
    )


def _implementation_corresponds(
    status: HandoffStatus,
    current_snapshot,
) -> bool:
    expected_paths = tuple(status.artifact_paths.implementation)
    if not expected_paths:
        return False
    recorded_paths = tuple(item.path for item in status.implementation_snapshot)
    current_paths = tuple(item.path for item in current_snapshot)
    if recorded_paths != expected_paths or current_paths != expected_paths:
        return False
    recorded_hashes = tuple((item.path, item.sha256) for item in status.implementation_snapshot)
    current_hashes = tuple((item.path, item.sha256) for item in current_snapshot)
    return recorded_hashes == current_hashes


def _transition(
    status: HandoffStatus,
    *,
    actor: Actor,
    new_state: SupervisorState,
    status_reason: StatusReason,
    next_actor: Actor,
    reason: str,
    turn_usage: TurnUsageTelemetry | None = None,
    increment_refinement_cost: bool = False,
    artifact_paths: ArtifactPaths | None = None,
    spec_snapshot=(),
    implementation_snapshot=(),
    verification_command: str | None = None,
    gate_on_verifier_pass: bool | None = None,
    consecutive_build_failures: int | None = None,
    spec_refinement_rounds: int | None = None,
    human_gate_reason: HumanGateReason | None = None,
    human_gate_resolved: bool = False,
) -> TransitionOutcome:
    turn_usage_value = turn_usage or TurnUsageTelemetry()
    turn_cost = _turn_cost(turn_usage)
    new_status = HandoffStatus(
        run_id=status.run_id,
        revision=status.revision + 1,
        state=new_state,
        active_program=status.active_program,
        active_target=status.active_target,
        pipeline_type=status.pipeline_type,
        debate_file=status.debate_file,
        debate_last_turn=status.debate_last_turn,
        owner_mode=status.owner_mode,
        genesis_path=status.genesis_path,
        seed_spec_path=status.seed_spec_path,
        contract_boundary=status.contract_boundary,
        success_condition=status.success_condition,
        out_of_scope=status.out_of_scope,
        last_actor=actor,
        next_actor=next_actor,
        status_reason=status_reason,
        artifact_paths=artifact_paths if artifact_paths is not None else status.artifact_paths,
        spec_snapshot=tuple(spec_snapshot) if spec_snapshot else status.spec_snapshot,
        implementation_snapshot=(
            tuple(implementation_snapshot)
            if implementation_snapshot
            else status.implementation_snapshot
        ),
        verification_command=(
            verification_command
            if verification_command is not None
            else status.verification_command
        ),
        gate_on_verifier_pass=(
            status.gate_on_verifier_pass
            if gate_on_verifier_pass is None
            else gate_on_verifier_pass
        ),
        consecutive_build_failures=(
            status.consecutive_build_failures
            if consecutive_build_failures is None
            else consecutive_build_failures
        ),
        spec_refinement_rounds=(
            status.spec_refinement_rounds
            if spec_refinement_rounds is None
            else spec_refinement_rounds
        ),
        human_gate_reason=human_gate_reason,
        human_gate_resolved=human_gate_resolved,
        last_turn_usage=turn_usage_value,
        program_cost_usd=round(status.program_cost_usd + turn_cost, 8),
        refinement_cost_usd=round(
            status.refinement_cost_usd + (turn_cost if increment_refinement_cost else 0.0),
            8,
        ),
        max_refinement_cost_usd=status.max_refinement_cost_usd,
        closed_programs=status.closed_programs,
    )
    event = HandoffEvent(
        revision=new_status.revision,
        actor=actor,
        prior_state=status.state,
        new_state=new_state,
        reason=reason,
        timestamp=datetime.now(timezone.utc).isoformat(),
        artifact_paths=new_status.artifact_paths,
        human_gate_reason=human_gate_reason,
    )
    return TransitionOutcome(status=new_status, event=event, fail_closed=False)


def _fail_closed(
    status: HandoffStatus,
    *,
    actor: Actor,
    gate: HumanGateReason,
    reason: str,
    turn_usage: TurnUsageTelemetry | None = None,
) -> TransitionOutcome:
    outcome = _transition(
        status,
        actor=actor,
        new_state=SupervisorState.D,
        status_reason=StatusReason.FAILED_CLOSED,
        next_actor=Actor.HUMAN,
        artifact_paths=status.artifact_paths,
        spec_snapshot=status.spec_snapshot,
        implementation_snapshot=status.implementation_snapshot,
        verification_command=status.verification_command,
        consecutive_build_failures=status.consecutive_build_failures,
        human_gate_reason=gate,
        reason=reason,
        human_gate_resolved=False,
        turn_usage=turn_usage,
        increment_refinement_cost=status.state in {SupervisorState.A1, SupervisorState.A2}
        and status.spec_refinement_rounds > 0,
    )
    return TransitionOutcome(status=outcome.status, event=outcome.event, fail_closed=True)


def _turn_cost(turn_usage: TurnUsageTelemetry | None) -> float:
    if turn_usage is None:
        return 0.0
    return float(turn_usage.estimated_cost_usd)


def _refinement_budget_exceeded(status: HandoffStatus, request: TransitionInput) -> bool:
    if status.max_refinement_cost_usd is None:
        return False
    projected_cost = status.refinement_cost_usd + _turn_cost(request.turn_usage)
    return projected_cost > status.max_refinement_cost_usd
