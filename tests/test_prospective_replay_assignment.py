from __future__ import annotations

import pytest

from ztare.common.continual_skill_memory import (
    decision_option_family_sha256,
)
from ztare.common.temporal_decision_credit import DecisionChoiceAuthority
from ztare.common.two_stage_eligibility_ledger import (
    SealedDecisionReplayAssignment,
    SealedDecisionReplayContract,
)
from ztare.worldmodel.planner import compile_replay_protocol_assignment


TASK = "current-task"
NAMESPACE = "ztare-acquisition-protocol-choice-v1"
CHOICE_CONTEXT = "current-choice-context"
CONTROLLER = "current-continuation-controller"
PROTOCOLS = ("assigned-protocol", "epistemic-protocol")
FAMILIES = tuple(sorted(
    decision_option_family_sha256(NAMESPACE, protocol_id)
    for protocol_id in PROTOCOLS
))


def _authority() -> DecisionChoiceAuthority:
    return DecisionChoiceAuthority(
        task_contract_sha256=TASK,
        decision_namespace=NAMESPACE,
        choice_context_sha256=CHOICE_CONTEXT,
        continuation_context_sha256=CONTROLLER,
        available_option_family_sha256s=FAMILIES,
    )


def _assignment() -> SealedDecisionReplayAssignment:
    assigned_family = decision_option_family_sha256(
        NAMESPACE,
        "assigned-protocol",
    )
    epistemic_family = decision_option_family_sha256(
        NAMESPACE,
        "epistemic-protocol",
    )
    contract = SealedDecisionReplayContract(
        contract_ref="prospective-current-planner-pair",
        first_authority=_authority(),
        continuation_policy_sha256="continuation-policy",
        environment_source_sha256="environment-source",
        replay_prefix_sha256="replay-prefix",
        information_yield_measure_sha256="yield-measure",
        arm_option_family_sha256s=(
            ("assigned-arm", assigned_family),
            ("epistemic-arm", epistemic_family),
        ),
        max_eligibility_delay_steps=3,
    )
    return SealedDecisionReplayAssignment(
        assignment_ref="prospective-current-planner-pair:assigned",
        contract=contract,
        arm_id="assigned-arm",
        randomization_evidence_ref="randomization:pair-1",
    )


def test_current_planner_option_family_assignment_binds_exactly() -> None:
    assignment = _assignment()
    compiled = compile_replay_protocol_assignment(
        assignment,
        task_contract_sha256=TASK,
        decision_namespace=NAMESPACE,
        choice_context_sha256=CHOICE_CONTEXT,
        continuation_context_sha256=CONTROLLER,
        canonical_protocol_ids=reversed(PROTOCOLS),
    )

    assert compiled.assigned_protocol_id == "assigned-protocol"
    assert compiled.canonical_protocol_ids == PROTOCOLS
    assert compiled.decision_choice_authority_sha256 == _authority().sha256
    assert compiled.source_assignment_sha256 == assignment.sha256
    assert compiled.to_receipt()["task_value_authorized"] is False
    assert compiled.to_receipt()["external_utility_authorized"] is False
    assert compiled.to_receipt()["information_yield_authorized"] is False


@pytest.mark.parametrize(
    "updates",
    (
        {"task_contract_sha256": "different-task"},
        {"decision_namespace": "different-namespace"},
        {"choice_context_sha256": "different-context"},
        {"continuation_context_sha256": "different-controller"},
        {"canonical_protocol_ids": (*PROTOCOLS, "third-protocol")},
        {"canonical_protocol_ids": ("assigned-protocol",)},
    ),
)
def test_current_planner_assignment_refuses_authority_drift(updates) -> None:
    kwargs = {
        "task_contract_sha256": TASK,
        "decision_namespace": NAMESPACE,
        "choice_context_sha256": CHOICE_CONTEXT,
        "continuation_context_sha256": CONTROLLER,
        "canonical_protocol_ids": PROTOCOLS,
    }
    kwargs.update(updates)
    with pytest.raises(ValueError, match="planner choice authority"):
        compile_replay_protocol_assignment(_assignment(), **kwargs)


def test_current_planner_assignment_refuses_edited_contract() -> None:
    assignment = _assignment()
    receipt = assignment.to_receipt()
    receipt["contract"] = {
        **receipt["contract"],
        "contract_ref": "edited-contract",
    }
    with pytest.raises(ValueError, match="contract receipt drifted"):
        SealedDecisionReplayAssignment.from_receipt(receipt)
