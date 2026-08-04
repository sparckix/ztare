from __future__ import annotations

from dataclasses import dataclass, replace

from ztare.common.equivariance import stable_sha256
from ztare.common.guarded_experiment_protocol import (
    ProtocolYieldWeights,
    select_guarded_protocol,
)
from ztare.common.guarded_skill_compiler import (
    GuardedActionTrace,
    GuardedTraceTransition,
    compile_guarded_skill_library,
)
from ztare.common.partial_action_system import (
    PartialActionObservation,
    build_partial_action_system,
)
from ztare.common.predictive_quotient import (
    compile_predictive_compatibility,
)
from ztare.worldmodel.mechanism_protocols import (
    MechanismAcquisitionFrontiers,
    lower_witnessed_protocol,
    select_acquisition_protocols,
    select_witnessed_protocols,
)


def _system():
    observations = (
        PartialActionObservation("start", "prepare", "target", "e#0"),
        PartialActionObservation("target", "joint", "target2", "e#1"),
        PartialActionObservation("peer-a", "probe", "a-next", "e#2"),
        PartialActionObservation("peer-b", "probe", "b-next", "e#3"),
        PartialActionObservation(
            "peer-boundary",
            "probe",
            evidence_ref="e#4",
            boundary_kind="regime_change",
        ),
    )
    return build_partial_action_system(
        observations,
        project=lambda value: value,
        effect=lambda source, operation, successor, _left, _right: (
            "boundary",
            successor,
        ) if successor is None else ("effect", successor),
        projection_id="opaque-fixture",
    )


def _control_trace(trace_ref: str, start_key: str) -> GuardedActionTrace:
    return GuardedActionTrace(
        trace_ref=trace_ref,
        transitions=(
            GuardedTraceTransition(
                start_key,
                "prepare",
                "target",
                "prepared",
                f"{trace_ref}#0",
            ),
            GuardedTraceTransition(
                "target",
                "joint",
                "target2",
                "joined",
                f"{trace_ref}#1",
            ),
        ),
    )


def test_witnessed_protocol_builds_compatible_typed_response_committee():
    system = _system()
    compatibility = compile_predictive_compatibility(
        system,
        operations=("prepare", "joint", "probe"),
    )
    lowering = lower_witnessed_protocol(
        system,
        compatibility,
        start_key="start",
        actions=("prepare", "probe"),
        protocol_id="fixture",
    )
    candidate = lowering.candidate

    assert candidate.protocol.guard_admitted
    assert candidate.protocol.target_key == "target"
    assert candidate.protocol.novel_context
    assert candidate.protocol.cost.primitive_execution_units == 2
    assert len(candidate.committee) == 3
    assert len({member.response for member in candidate.committee}) == 3
    assert any(
        member.response[0] == "typed_boundary_response"
        for member in candidate.committee
    )


def test_additional_transport_program_reduces_control_not_interventions():
    system = _system()
    compatibility = compile_predictive_compatibility(
        system,
        operations=("prepare", "joint", "probe"),
    )
    current_trace = _control_trace("current-one-shot", "start")
    current_library = compile_guarded_skill_library(
        (current_trace,),
        max_word_length=2,
    )
    assert current_library.programs == ()
    learned_library = compile_guarded_skill_library(
        (
            current_trace,
            _control_trace("source-two", "source-two-start"),
            _control_trace("source-three", "source-three-start"),
        ),
        max_word_length=2,
    )
    assert len(learned_library.programs) == 1
    transported = replace(
        learned_library.programs[0],
        admission_authority="validated_transport",
    )

    lowering = lower_witnessed_protocol(
        system,
        compatibility,
        start_key="start",
        actions=("prepare", "joint", "probe"),
        protocol_id="transported-control",
        skill_library=current_library,
        allowed_skill_sha256s=frozenset({transported.skill_sha256}),
        additional_skill_programs=(transported,),
    )

    assert lowering.candidate.protocol.cost.preparation_execution_units == 2
    assert lowering.candidate.protocol.cost.primitive_execution_units == 3
    assert lowering.candidate.protocol.cost.control_units == 1
    assert lowering.control_plan_receipt is not None
    assert lowering.control_plan_receipt["skill_token_count"] == 1
    assert lowering.control_plan_receipt["token_savings"] == 1
    assert lowering.control_plan_receipt["exact_expansion"]


def test_motor_chunk_executes_without_unearned_decision_price_authority():
    system = _system()
    compatibility = compile_predictive_compatibility(
        system,
        operations=("prepare", "joint", "probe"),
    )
    current_trace = _control_trace("current-pricing-shot", "start")
    current_library = compile_guarded_skill_library(
        (current_trace,),
        max_word_length=2,
    )
    learned_library = compile_guarded_skill_library(
        (
            current_trace,
            _control_trace("pricing-source-two", "source-two-start"),
            _control_trace("pricing-source-three", "source-three-start"),
        ),
        max_word_length=2,
    )
    transported = replace(
        learned_library.programs[0],
        admission_authority="validated_transport",
    )
    shared = {
        "start_key": "start",
        "actions": ("prepare", "joint", "probe"),
        "protocol_id": "effect-credit-gate",
        "skill_library": current_library,
        "allowed_skill_sha256s": frozenset({
            transported.skill_sha256,
        }),
        "additional_skill_programs": (transported,),
    }

    uncredited = lower_witnessed_protocol(
        system,
        compatibility,
        **shared,
        pricing_allowed_skill_invocations=frozenset(),
    )
    credited = lower_witnessed_protocol(
        system,
        compatibility,
        **shared,
        pricing_allowed_skill_invocations=frozenset({(
            transported.skill_sha256,
            stable_sha256("start"),
        )}),
    )

    assert uncredited.control_plan_receipt["skill_token_count"] == 1
    assert uncredited.pricing_control_plan_receipt[
        "skill_token_count"
    ] == 0
    assert uncredited.candidate.protocol.cost.control_units == 2
    assert credited.control_plan_receipt["skill_token_count"] == 1
    assert credited.pricing_control_plan_receipt[
        "skill_token_count"
    ] == 1
    assert credited.candidate.protocol.cost.control_units == 1


def test_primitive_budget_cannot_be_paid_with_compiled_control_tokens():
    system = _system()
    compatibility = compile_predictive_compatibility(
        system,
        operations=("prepare", "joint", "probe"),
    )
    current_trace = _control_trace("current-budget-shot", "start")
    current_library = compile_guarded_skill_library(
        (current_trace,),
        max_word_length=2,
    )
    learned_library = compile_guarded_skill_library(
        (
            current_trace,
            _control_trace("budget-source-two", "source-two-start"),
            _control_trace("budget-source-three", "source-three-start"),
        ),
        max_word_length=2,
    )
    transported = replace(
        learned_library.programs[0],
        admission_authority="validated_transport",
    )

    portfolio = select_witnessed_protocols(
        system,
        compatibility,
        start_key="start",
        routes=(
            ("compressed-but-too-long", ("prepare", "joint", "probe")),
        ),
        weights=ProtocolYieldWeights(1.0, 0.5, 0.5),
        skill_library=current_library,
        allowed_skill_sha256s=frozenset({
            transported.skill_sha256,
        }),
        additional_skill_programs=(transported,),
        max_primitive_execution_units=2,
    )

    price = portfolio.selection.prices[0]
    assert price.cost.control_units == 1
    assert price.cost.primitive_execution_units == 3
    assert portfolio.selection.status == "no_affordable_protocol"
    assert portfolio.selection.selected is None
    assert portfolio.selection.budget_ineligible_protocol_ids == (
        "compressed-but-too-long",
    )
    receipt = portfolio.selection.to_receipt()
    assert receipt["max_primitive_execution_units"] == 2.0


def test_undefined_preparation_rejects_before_probe():
    system = _system()
    compatibility = compile_predictive_compatibility(
        system,
        operations=("prepare", "joint", "probe"),
    )
    lowering = lower_witnessed_protocol(
        system,
        compatibility,
        start_key="start",
        actions=("missing", "probe"),
        protocol_id="rejected",
    )
    selection = select_guarded_protocol(
        (lowering.candidate,),
        weights=ProtocolYieldWeights(1.0, 0.5, 0.5),
    )

    assert not lowering.candidate.protocol.guard_admitted
    assert lowering.candidate.committee == ()
    assert selection.status == "no_valued_protocol"
    assert selection.prices[0].status == "guard_rejected"


def test_portfolio_selection_owns_the_selected_operation_word():
    system = _system()
    compatibility = compile_predictive_compatibility(
        system,
        operations=("prepare", "joint", "probe"),
    )
    weights = ProtocolYieldWeights(1.0, 0.5, 0.5)
    forward = select_witnessed_protocols(
        system,
        compatibility,
        start_key="start",
        routes=(
            ("short", ("prepare", "probe")),
            (
                "long",
                ("prepare", "joint", "probe"),
            ),
        ),
        weights=weights,
    )
    reversed_routes = select_witnessed_protocols(
        system,
        compatibility,
        start_key="start",
        routes=(
            ("long", ("prepare", "joint", "probe")),
            ("short", ("prepare", "probe")),
        ),
        weights=weights,
    )

    assert forward.selection.selected_protocol_id == "short"
    assert forward.selected_operations == ("prepare", "probe")
    assert forward.to_receipt()["selection"] == (
        reversed_routes.to_receipt()["selection"]
    )


def test_acquisition_frontier_identity_requires_and_prices_all_producers():
    @dataclass(frozen=True)
    class Frontier:
        actions: tuple[str, ...]
        status: str

    system = _system()
    compatibility = compile_predictive_compatibility(
        system,
        operations=("prepare", "joint", "probe"),
    )
    frontiers = MechanismAcquisitionFrontiers(
        observed=Frontier(
            ("prepare", "joint", "probe"),
            "frontier_pair_found",
        ),
        boundary=Frontier(
            ("prepare", "joint", "probe"),
            "boundary_relevant_frontier_found",
        ),
        predictive_quotient=Frontier(
            ("prepare", "joint", "probe"),
            "frontier_pair_found",
        ),
        predictive_support=Frontier(
            ("prepare", "probe"),
            "support_gap_found",
        ),
        predictive_quotient_is_orbit_completion=False,
    )
    result = select_acquisition_protocols(
        system,
        compatibility,
        start_key="start",
        frontiers=frontiers,
        weights=ProtocolYieldWeights(1.0, 0.5, 0.5),
    )

    assert [name for name, _frontier in result.candidates] == [
        "observed_partial_action_frontier",
        "boundary_reachability_frontier",
        "predictive_quotient_frontier",
        "predictive_compatibility_support",
    ]
    assert result.selection.selected_protocol_id == (
        "predictive_compatibility_support"
    )
    assert result.selected_frontier is frontiers.predictive_support
    assert result.selected_operations == ("prepare", "probe")

    bounded = select_acquisition_protocols(
        system,
        compatibility,
        start_key="start",
        frontiers=frontiers,
        weights=ProtocolYieldWeights(1.0, 0.5, 0.5),
        max_primitive_execution_units=2,
    )
    assert bounded.selection.selected_protocol_id == (
        "predictive_compatibility_support"
    )
    assert set(bounded.selection.budget_ineligible_protocol_ids) == {
        "boundary_reachability_frontier",
        "observed_partial_action_frontier",
        "predictive_quotient_frontier",
    }

    blocked = select_acquisition_protocols(
        system,
        compatibility,
        start_key="start",
        frontiers=frontiers,
        weights=ProtocolYieldWeights(1.0, 0.5, 0.5),
        max_primitive_execution_units=1,
    )
    assert blocked.selection.status == "no_affordable_protocol"
    assert blocked.selection.selected is None
    assert blocked.selected_operations == ()


def test_acquisition_frontier_identity_filters_by_shared_status_contract():
    @dataclass(frozen=True)
    class Frontier:
        actions: tuple[str, ...]
        status: str

    frontiers = MechanismAcquisitionFrontiers(
        observed=Frontier((), "frontier_pair_found"),
        boundary=None,
        predictive_quotient=Frontier(
            ("prepare", "probe"),
            "not_admitted",
        ),
        predictive_support=Frontier(
            ("prepare", "probe"),
            "support_gap_found",
        ),
        predictive_quotient_is_orbit_completion=True,
    )

    assert [
        protocol_id
        for protocol_id, _frontier in frontiers.named_frontiers()
    ] == ["predictive_compatibility_support"]
