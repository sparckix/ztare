from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.carrier_conditioned_option import (
    compile_carrier_conditioned_option_prediction,
    settle_carrier_conditioned_option_prediction,
)
from ztare.worldmodel.compiled_fiber_planning import FiberFactors


class _Projection:
    projection_sha256 = "a" * 64

    @staticmethod
    def factor(state):
        return FiberFactors(
            controlled_base=((int(state), 0),),
            finite_configuration=(),
            presentation_assignment=(),
            ordered_budget=max(0, 10 - int(state)),
            one_shot_availability=(),
            ordered_feasibility_configuration=tuple(
                index >= int(state) for index in range(10)
            ),
        )


def _predict(carrier):
    return compile_carrier_conditioned_option_prediction(
        carrier=carrier,
        projection=_Projection(),
        source_state=1,
        start_time=7,
        operations=(2, 3),
        operation_namespace="fixture-operations",
        effect_namespace="fixture-effects",
        carrier_execution_sha256="b" * 64,
        source_skill_sha256="c" * 64,
        evidence_refs=("fixture#skill",),
    )


def test_carrier_conditioned_option_prediction_settles_exact_path():
    prediction = _predict(lambda state, operation, _time: state + operation)

    assert prediction.status == "predicted"
    assert prediction.predicted_final_state_sha256 == stable_sha256(6)
    assert prediction.predictive_effect_family_sha256
    assert not prediction.to_receipt()["externally_settled"]

    settlement = settle_carrier_conditioned_option_prediction(
        prediction,
        projection=_Projection(),
        observed_states=(1, 3, 6),
        environment_source_sha256="d" * 64,
        evidence_refs=("fixture#environment",),
    )

    assert settlement.status == "effect_confirmed"
    assert settlement.effect_matches
    assert settlement.intermediate_states_match
    assert settlement.final_state_matches
    assert settlement.observed_effect_family_sha256 == (
        prediction.predictive_effect_family_sha256
    )
    receipt = settlement.to_receipt()
    assert receipt["externally_settled"]
    assert not receipt["task_credit_transferred"]


def test_carrier_undefined_refuses_without_claiming_final_state():
    prediction = _predict(
        lambda state, operation, _time: (
            None if operation == 3 else state + operation
        )
    )

    assert prediction.status == "carrier_undefined"
    assert prediction.failed_step == 1
    assert prediction.predicted_final_state_sha256 == ""
    assert prediction.predictive_effect_family_sha256 == ""

    settlement = settle_carrier_conditioned_option_prediction(
        prediction,
        projection=_Projection(),
        observed_states=(1, 3, 6),
        environment_source_sha256="d" * 64,
        evidence_refs=("fixture#environment",),
    )
    assert settlement.status == "prediction_refused"
    assert not settlement.to_receipt()["externally_settled"]


def test_environment_mismatch_is_a_counterexample_not_effect_credit():
    prediction = _predict(lambda state, operation, _time: state + operation)
    settlement = settle_carrier_conditioned_option_prediction(
        prediction,
        projection=_Projection(),
        observed_states=(1, 4, 7),
        environment_source_sha256="d" * 64,
        evidence_refs=("fixture#counterexample",),
    )

    assert settlement.status == "counterexample"
    assert settlement.failed_step == 0
    assert not settlement.effect_matches
    assert not settlement.intermediate_states_match
    assert not settlement.final_state_matches
    assert not settlement.to_receipt()["externally_settled"]


def test_boundary_observation_cannot_confirm_effect_transport():
    prediction = _predict(lambda state, operation, _time: state + operation)
    settlement = settle_carrier_conditioned_option_prediction(
        prediction,
        projection=_Projection(),
        observed_states=(1, 3, 6),
        environment_source_sha256="d" * 64,
        evidence_refs=("fixture#boundary",),
        boundary_kind="level_transition",
    )

    assert settlement.status == "boundary_crossed"
    assert settlement.effect_matches
    assert not settlement.to_receipt()["externally_settled"]
