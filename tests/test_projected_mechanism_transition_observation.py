from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from ztare.common.guarded_experiment_protocol import (
    GuardedExperimentProtocol,
    GuardedProtocolCandidate,
    ProtocolCost,
)
from ztare.common.partial_action_system import (
    PartialActionObservation,
    build_partial_action_system,
)
from ztare.worldmodel.compiled_fiber_planning import FiberFactors
from ztare.worldmodel.episode_log import Transition
from ztare.worldmodel.mechanism_effects import (
    fiber_mechanism_effect,
    operation_effect_token,
    project_mechanism_transition_observation,
)
from ztare.worldmodel.mechanism_protocols import (
    WitnessedProtocolLowering,
    compile_witnessed_protocol_response_readout,
)
from ztare.worldmodel.transition_identity import TransitionIdentity


class _Projection:
    projection_sha256 = "projection-v1"

    @staticmethod
    def factor(state: int) -> FiberFactors:
        return FiberFactors(
            controlled_base=((state, 0),),
            finite_configuration=(state % 2,),
            presentation_assignment=(),
            ordered_budget=10 - state,
            one_shot_availability=(),
            ordered_feasibility_configuration=(True,),
            operation_domain_assignment=(),
        )


class _Problem:
    projection = _Projection()
    projection_sha256 = projection.projection_sha256
    action_system = SimpleNamespace(sha256="action-system-v1")
    problem_id = "mechanism-problem-v1"

    def __init__(self, history_kind: str = ""):
        self.history_lift = (
            SimpleNamespace(history_kind=history_kind)
            if history_kind
            else None
        )

    def observed_start_key(
        self,
        state,
        action_history=(),
        operation_effect_history=(),
    ):
        if self.history_lift is None:
            return ("frame", state)
        if self.history_lift.history_kind == "operation_effect":
            return ("effect-history", state, tuple(operation_effect_history))
        return ("action-history", state, tuple(action_history))


def _transition(*, boundary: bool = False) -> Transition:
    identity = (
        TransitionIdentity(
            kind="epoch_boundary",
            authority="environment_adapter",
            source_epoch=1,
            target_epoch=2,
            boundary_kind="level_completed",
            evidence_refs=("adapter:boundary",),
        )
        if boundary
        else None
    )
    return Transition(
        t=3,
        s=1,
        a=2,
        s_next=2,
        identity=identity,
    )


def test_projection_advances_frame_action_and_effect_histories_once():
    transition = _transition()
    frame = project_mechanism_transition_observation(
        _Problem(),
        transition,
        action_history=(7,),
        operation_effect_history=("old-effect",),
        evidence_ref="live:frame",
    )
    assert frame.source_key == ("frame", 1)
    assert frame.successor_key == ("frame", 2)
    assert frame.effect == fiber_mechanism_effect(
        _Projection.factor(1),
        _Projection.factor(2),
    )

    action = project_mechanism_transition_observation(
        _Problem("action"),
        transition,
        action_history=(7,),
        operation_effect_history=("old-effect",),
        evidence_ref="live:action",
    )
    assert action.source_key == ("action-history", 1, (7,))
    assert action.successor_key == (
        "action-history",
        2,
        (7, 2),
    )
    assert action.action_history_after == (7, 2)

    effect = project_mechanism_transition_observation(
        _Problem("operation_effect"),
        transition,
        action_history=(7,),
        operation_effect_history=("old-effect",),
        evidence_ref="live:effect",
    )
    expected_token = operation_effect_token(_Projection, transition)
    assert effect.source_key == (
        "effect-history",
        1,
        ("old-effect",),
    )
    assert effect.successor_key == (
        "effect-history",
        2,
        ("old-effect", expected_token),
    )
    assert effect.operation_effect_history_after == (
        "old-effect",
        expected_token,
    )
    receipt = effect.to_receipt()
    assert receipt["projection_sha256"] == "projection-v1"
    assert receipt["action_system_sha256"] == "action-system-v1"
    assert receipt["problem_id"] == "mechanism-problem-v1"
    assert receipt["history_kind"] == "operation_effect"
    assert receipt["evidence_ref"] == "live:effect"
    assert receipt["task_status_read"] is False


def test_authoritative_boundary_projects_as_partiality():
    observation = project_mechanism_transition_observation(
        _Problem("action"),
        _transition(boundary=True),
        action_history=(7,),
        operation_effect_history=("old-effect",),
        evidence_ref="live:boundary",
    )
    assert observation.boundary_kind == "epoch_boundary"
    assert observation.successor_key is None
    assert observation.effect is None
    assert observation.action_history_after == ()
    assert observation.operation_effect_history_after == ()

    untrusted = replace(
        _transition(boundary=True),
        identity=replace(
            _transition(boundary=True).identity,
            authority="untrusted",
        ),
    )
    with pytest.raises(ValueError, match="lacks adapter or collector authority"):
        project_mechanism_transition_observation(
            _Problem("action"),
            untrusted,
            evidence_ref="live:untrusted-boundary",
        )


def test_projected_observation_enters_h102_only_at_exact_target_probe():
    problem = _Problem("action")
    transition = _transition()
    observation = project_mechanism_transition_observation(
        problem,
        transition,
        action_history=(7,),
        evidence_ref="live:projected-probe",
    )
    source = observation.source_key
    system = build_partial_action_system(
        (
            PartialActionObservation(
                source=source,
                operation=0,
                successor=("retained",),
                evidence_ref="retain-source",
            ),
        ),
        project=lambda state: state,
        effect=lambda *_args: "retained-effect",
        projection_id="projected-observation-fixture",
    )
    protocol = GuardedExperimentProtocol(
        protocol_id="projected-probe",
        preparation=(),
        probe=transition.a,
        target_key=source,
        cost=ProtocolCost(
            preparation_execution_units=0,
            probe_execution_units=1,
            control_units=0,
        ),
        novel_context=True,
    )
    lowering = WitnessedProtocolLowering(
        candidate=GuardedProtocolCandidate(
            protocol=protocol,
            committee=(),
        ),
        preparation_key_sha256s=(),
        response_readout_operations=(0, 1, 2, 3),
        control_plan_receipt=None,
    )
    readout = compile_witnessed_protocol_response_readout(
        system,
        lowering,
        **observation.to_response_kwargs(),
    )
    assert readout.source_key_sha256 == (
        observation.to_receipt()["source_key_sha256"]
    )
    assert readout.probe_sha256 == (
        observation.to_receipt()["operation_sha256"]
    )

    with pytest.raises(ValueError, match="source does not match target"):
        compile_witnessed_protocol_response_readout(
            system,
            lowering,
            **{
                **observation.to_response_kwargs(),
                "observed_source_key": ("different",),
            },
        )
    with pytest.raises(ValueError, match="operation does not match probe"):
        compile_witnessed_protocol_response_readout(
            system,
            lowering,
            **{
                **observation.to_response_kwargs(),
                "observed_operation": 3,
            },
        )


def test_projection_identity_drift_is_refused():
    problem = _Problem()
    problem.projection_sha256 = "different-projection"
    with pytest.raises(ValueError, match="projection identity drifted"):
        project_mechanism_transition_observation(
            problem,
            _transition(),
            evidence_ref="live:drift",
        )

    with pytest.raises(ValueError, match="require evidence_ref"):
        project_mechanism_transition_observation(
            _Problem(),
            _transition(),
            evidence_ref="",
        )
