from __future__ import annotations

import pytest

from ztare.common.decision_use_gate import (
    ControllerDecisionProposal,
    DecisionUseContract,
    bind_gate_consumption,
    compile_decision_gate,
    compile_decision_use_transition,
)
from ztare.common.wake_sleep_credit_router import MemoryScope


def _scope() -> MemoryScope:
    return MemoryScope(
        task_sha256="task",
        controller_sha256="controller-class",
        context_sha256="observation",
        choice_set_sha256="choices",
        action_vocabulary_sha256="actions",
    )


def _proposal(
    *,
    action: str,
    prediction: str,
    features: tuple[str, ...],
    parent: str = "",
    intervention: str = "",
    controller: str = "controller-instance",
) -> ControllerDecisionProposal:
    return ControllerDecisionProposal(
        scope=_scope(),
        controller_instance_sha256=controller,
        observation_sha256="observation",
        proposal_ref=f"proposal:{action}:{prediction}",
        action_ref=action,
        predicted_consequence_ref=prediction,
        asserted_features=features,
        parent_proposal_sha256=parent,
        consumed_intervention_revision_sha256=intervention,
    )


def _contract() -> DecisionUseContract:
    return DecisionUseContract(
        scope=_scope(),
        intervention_revision_sha256="intervention",
        required_features=("state_precondition_checked",),
        forbidden_features=("terminal_before_precondition",),
        evidence_refs=("episode:7",),
    )


def test_gate_remains_silent_when_proposal_already_satisfies_contract() -> None:
    pre = _proposal(
        action="inspect-precondition",
        prediction="precondition-remains-valid",
        features=("state_precondition_checked",),
    )
    gate = compile_decision_gate(pre, _contract())

    assert gate.gate_action == "silence"
    transition = compile_decision_use_transition(
        pre_proposal=pre,
        contract=_contract(),
        gate_decision=gate,
    )
    assert transition.use_relation == "already_satisfied"
    assert transition.post_proposal_sha256 == ""


def test_challenge_records_accepted_proposal_change() -> None:
    pre = _proposal(
        action="attempt-terminal",
        prediction="terminal-now",
        features=("terminal_before_precondition",),
    )
    contract = _contract()
    gate = bind_gate_consumption(
        compile_decision_gate(pre, contract),
        consumption_receipt_sha256="consumption",
    )
    post = _proposal(
        action="inspect-precondition",
        prediction="state-will-change",
        features=("state_precondition_checked",),
        parent=pre.sha256,
        intervention="intervention",
    )

    transition = compile_decision_use_transition(
        pre_proposal=pre,
        contract=contract,
        gate_decision=gate,
        post_proposal=post,
    )
    assert gate.gate_action == "challenge"
    assert transition.use_relation == "accepted_change"
    assert transition.changed_action is True
    assert transition.added_required_features == (
        "state_precondition_checked",
    )
    assert transition.removed_forbidden_features == (
        "terminal_before_precondition",
    )


def test_ignored_injection_is_not_laundered_into_decision_use() -> None:
    pre = _proposal(
        action="explore",
        prediction="unknown",
        features=(),
    )
    contract = _contract()
    gate = bind_gate_consumption(
        compile_decision_gate(pre, contract),
        consumption_receipt_sha256="consumption",
    )
    post = _proposal(
        action="explore",
        prediction="unknown",
        features=(),
        parent=pre.sha256,
        intervention="intervention",
    )

    transition = compile_decision_use_transition(
        pre_proposal=pre,
        contract=contract,
        gate_decision=gate,
        post_proposal=post,
    )
    assert gate.gate_action == "inject"
    assert transition.use_relation == "rejected"
    assert transition.changed_action is False


def test_proposal_revision_cannot_cross_controller_instances() -> None:
    pre = _proposal(
        action="explore",
        prediction="unknown",
        features=(),
    )
    contract = _contract()
    gate = bind_gate_consumption(
        compile_decision_gate(pre, contract),
        consumption_receipt_sha256="consumption",
    )
    post = _proposal(
        action="inspect-precondition",
        prediction="state-will-change",
        features=("state_precondition_checked",),
        parent=pre.sha256,
        intervention="intervention",
        controller="other-controller",
    )

    with pytest.raises(
        ValueError,
        match="controller instance drifted",
    ):
        compile_decision_use_transition(
            pre_proposal=pre,
            contract=contract,
            gate_decision=gate,
            post_proposal=post,
        )
