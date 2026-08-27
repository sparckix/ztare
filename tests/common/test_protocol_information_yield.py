from __future__ import annotations

from dataclasses import replace

import pytest

from ztare.common.guarded_experiment_protocol import (
    GuardedExperimentProtocol,
    GuardedProtocolCandidate,
    ProtocolCost,
    ProtocolResponseHypothesis,
    ProtocolYieldWeights,
    price_guarded_protocol,
)
from ztare.common.protocol_information_yield import (
    MEASURE_SHA256,
    compile_protocol_information_yield_forecast,
    observe_protocol_information_yield,
)
from ztare.common.temporal_decision_credit import DecisionChoiceAuthority
from ztare.common.two_stage_eligibility_ledger import DecisionWindowEvidence


def _candidate() -> GuardedProtocolCandidate:
    return GuardedProtocolCandidate(
        protocol=GuardedExperimentProtocol(
            protocol_id="partition-probe",
            preparation=("prepare",),
            probe="probe",
            target_key="target",
            cost=ProtocolCost(
                preparation_execution_units=1,
                probe_execution_units=1,
                control_units=1,
            ),
            novel_context=False,
        ),
        committee=(
            ProtocolResponseHypothesis("h1", "common"),
            ProtocolResponseHypothesis("h2", "common"),
            ProtocolResponseHypothesis("h3", "rare-b"),
            ProtocolResponseHypothesis("h4", "rare-c"),
        ),
    )


def test_realized_cell_reduction_matches_predicted_identification():
    candidate = _candidate()
    price = price_guarded_protocol(
        candidate,
        weights=ProtocolYieldWeights(1.0, 0.0, 0.0),
    )
    cost_before = price.cost.to_receipt()
    forecast = compile_protocol_information_yield_forecast(
        candidate,
        price,
    )
    assert forecast.predicted_information_yield == pytest.approx(0.75)
    assert (
        forecast.expected_realized_information_yield
        == pytest.approx(0.75)
    )
    assert forecast.measure_sha256 == MEASURE_SHA256
    assert forecast.cost.to_receipt() == cost_before
    assert not forecast.to_receipt()["task_credit_authorized"]

    common = observe_protocol_information_yield(
        forecast,
        observed_response="common",
        observation_evidence_ref="observation:common",
    )
    rare_b = observe_protocol_information_yield(
        forecast,
        observed_response="rare-b",
        observation_evidence_ref="observation:rare-b",
    )
    rare_c = observe_protocol_information_yield(
        forecast,
        observed_response="rare-c",
        observation_evidence_ref="observation:rare-c",
    )
    assert common.status == "witnessed_partition_cell"
    assert common.posterior_cell_size == 2
    assert common.observed_information_yield == pytest.approx(0.5)
    assert rare_b.posterior_cell_size == 1
    assert rare_b.observed_information_yield == pytest.approx(1.0)
    assert rare_c.observed_information_yield == pytest.approx(1.0)
    uniform_expectation = (
        2 * common.observed_information_yield
        + rare_b.observed_information_yield
        + rare_c.observed_information_yield
    ) / 4
    assert uniform_expectation == pytest.approx(
        forecast.predicted_information_yield
    )
    assert not common.to_receipt()["task_credit_authorized"]
    assert forecast.cost.to_receipt() == cost_before

    authority = DecisionChoiceAuthority(
        task_contract_sha256="external-task",
        decision_namespace="protocol-choice",
        choice_context_sha256="source",
        continuation_context_sha256="controller",
        available_option_family_sha256s=("advance", "detour"),
    )
    window = DecisionWindowEvidence(
        authority=authority,
        chosen_option_family_sha256="advance",
        chosen_option_variant_sha256=forecast.sha256,
        successor_decision_state_sha256="next",
        predicted_information_yield=(
            forecast.predicted_information_yield
        ),
        observed_information_yield=common.observed_information_yield,
        information_yield_measure_sha256=forecast.measure_sha256,
        primitive_action_cost=(
            forecast.cost.primitive_execution_units
        ),
        immediate_task_status="open",
        decision_evidence_ref="decision:advance",
        observed_yield_evidence_ref=common.sha256,
    )
    assert not window.to_receipt()["task_credit_authorized"]


def test_unseen_response_refutes_committee_without_task_credit():
    candidate = _candidate()
    forecast = compile_protocol_information_yield_forecast(
        candidate,
        price_guarded_protocol(
            candidate,
            weights=ProtocolYieldWeights(1.0, 0.0, 0.0),
        ),
    )
    observation = observe_protocol_information_yield(
        forecast,
        observed_response="outside-partition",
        observation_evidence_ref="observation:outside",
    )
    assert observation.status == "committee_refuted"
    assert observation.posterior_cell_size == 0
    assert observation.observed_information_yield == pytest.approx(1.0)
    assert not observation.to_receipt()["task_credit_authorized"]


def test_forecast_and_observation_fail_closed_on_identity_or_evidence_drift():
    candidate = _candidate()
    price = price_guarded_protocol(
        candidate,
        weights=ProtocolYieldWeights(1.0, 0.0, 0.0),
    )
    changed_committee = replace(
        candidate,
        committee=(
            *candidate.committee[:-1],
            ProtocolResponseHypothesis("different-h4", "rare-c"),
        ),
    )
    with pytest.raises(ValueError, match="committee identity drifted"):
        compile_protocol_information_yield_forecast(
            changed_committee,
            price,
        )
    with pytest.raises(ValueError, match="response partition drifted"):
        compile_protocol_information_yield_forecast(
            candidate,
            replace(price, partition_sha256="different-partition"),
        )

    forecast = compile_protocol_information_yield_forecast(
        candidate,
        price,
    )
    with pytest.raises(
        ValueError,
        match="observation_evidence_ref must be nonempty",
    ):
        observe_protocol_information_yield(
            forecast,
            observed_response="common",
            observation_evidence_ref="",
        )


def test_singleton_committee_has_zero_predicted_and_realized_yield():
    candidate = replace(
        _candidate(),
        committee=(ProtocolResponseHypothesis("only", "response"),),
    )
    forecast = compile_protocol_information_yield_forecast(
        candidate,
        price_guarded_protocol(
            candidate,
            weights=ProtocolYieldWeights(1.0, 0.0, 0.0),
        ),
    )
    observation = observe_protocol_information_yield(
        forecast,
        observed_response="response",
        observation_evidence_ref="observation:only",
    )
    assert forecast.predicted_information_yield == 0.0
    assert observation.observed_information_yield == 0.0
