from __future__ import annotations

import pytest

from ztare.common.decision_use_gate import (
    ControllerDecisionProposal,
    DecisionUseContract,
)
from ztare.common.instrumented_proposal_plasticity import (
    InstrumentedProposalOutcome,
    compile_admission_decision,
    compile_instrumented_transition,
    estimate_instrumented_plasticity,
)
from ztare.common.wake_sleep_credit_router import MemoryScope


def _scope(context: str = "observation") -> MemoryScope:
    return MemoryScope(
        task_sha256="task",
        controller_sha256="controller-class",
        context_sha256=context,
        choice_set_sha256="choices",
        action_vocabulary_sha256="actions",
    )


def _contract(scope: MemoryScope | None = None) -> DecisionUseContract:
    return DecisionUseContract(
        scope=scope or _scope(),
        intervention_revision_sha256="intervention",
        required_features=("precondition_first",),
        forbidden_features=("terminal_first",),
        evidence_refs=("episode:7",),
    )


def _proposal(
    *,
    controller: str,
    action: str,
    features: tuple[str, ...],
    prediction: str = "prediction",
    parent: str = "",
    intervention: str = "",
    scope: MemoryScope | None = None,
) -> ControllerDecisionProposal:
    use_scope = scope or _scope()
    return ControllerDecisionProposal(
        scope=use_scope,
        controller_instance_sha256=controller,
        observation_sha256=use_scope.context_sha256,
        proposal_ref=f"{controller}:{action}:{prediction}:{features}",
        action_ref=action,
        predicted_consequence_ref=prediction,
        asserted_features=features,
        parent_proposal_sha256=parent,
        consumed_intervention_revision_sha256=intervention,
    )


def _transition(
    *,
    assignment: str,
    controller: str,
    before: tuple[str, ...],
    after: tuple[str, ...],
    before_action: str = "terminal",
    after_action: str = "precondition",
):
    contract = _contract()
    pre = _proposal(
        controller=controller,
        action=before_action,
        features=before,
    )
    post = _proposal(
        controller=controller,
        action=after_action,
        features=after,
        parent=pre.sha256,
        intervention=(
            contract.intervention_revision_sha256
            if assignment == "offer"
            else ""
        ),
    )
    return compile_instrumented_transition(
        trial_ref=f"trial:{controller}",
        stratum_sha256="stratum",
        assignment=assignment,
        pre_proposal=pre,
        post_proposal=post,
        contract=contract,
    )


def _outcome(
    transition,
    value: float,
    *,
    offer_cost: float = 0.0,
) -> InstrumentedProposalOutcome:
    return InstrumentedProposalOutcome(
        transition=transition,
        external_outcome_ref=f"outcome:{transition.trial_ref}",
        external_value=value,
        offer_cost=offer_cost,
        primitive_action_cost=20.0,
    )


def test_offer_and_spontaneous_transport_have_distinct_relations() -> None:
    offered = _transition(
        assignment="offer",
        controller="offered",
        before=("terminal_first",),
        after=("precondition_first",),
    )
    spontaneous = _transition(
        assignment="withhold",
        controller="withheld",
        before=("terminal_first",),
        after=("precondition_first",),
    )

    assert offered.relation == "offered_supported_transport"
    assert spontaneous.relation == "withheld_spontaneous_supported"
    assert offered.supported_transport is True
    assert spontaneous.supported_transport is True
    assert offered.response_signature_sha256 != (
        spontaneous.response_signature_sha256
    )


def test_withheld_revision_cannot_cite_the_intervention() -> None:
    contract = _contract()
    pre = _proposal(
        controller="controller",
        action="terminal",
        features=("terminal_first",),
    )
    post = _proposal(
        controller="controller",
        action="precondition",
        features=("precondition_first",),
        parent=pre.sha256,
        intervention="intervention",
    )

    with pytest.raises(
        ValueError,
        match="withheld post proposal cannot cite",
    ):
        compile_instrumented_transition(
            trial_ref="trial",
            stratum_sha256="stratum",
            assignment="withhold",
            pre_proposal=pre,
            post_proposal=post,
            contract=contract,
        )


def test_instrument_separates_offer_effect_from_endogenous_uptake() -> None:
    outcomes = [
        _outcome(
            _transition(
                assignment="offer",
                controller="offer-1",
                before=("terminal_first",),
                after=("precondition_first",),
            ),
            1.0,
            offer_cost=0.1,
        ),
        _outcome(
            _transition(
                assignment="offer",
                controller="offer-2",
                before=("terminal_first",),
                after=("terminal_first",),
                before_action="terminal",
                after_action="terminal",
            ),
            0.0,
            offer_cost=0.1,
        ),
        _outcome(
            _transition(
                assignment="withhold",
                controller="withhold-1",
                before=("terminal_first",),
                after=("terminal_first",),
                before_action="terminal",
                after_action="terminal",
            ),
            0.0,
        ),
        _outcome(
            _transition(
                assignment="withhold",
                controller="withhold-2",
                before=("terminal_first",),
                after=("terminal_first",),
                before_action="terminal",
                after_action="terminal",
            ),
            0.0,
        ),
    ]

    estimate = estimate_instrumented_plasticity(outcomes)

    assert estimate.status == "identified"
    assert estimate.offer_supported_transport_rate == 0.5
    assert estimate.withhold_supported_transport_rate == 0.0
    assert estimate.first_stage_transport_delta == 0.5
    assert estimate.intent_to_treat_net_delta == pytest.approx(0.4)
    assert estimate.complier_net_effect == pytest.approx(0.8)
    assert compile_admission_decision(estimate).action == "offer"


def test_equal_spontaneous_and_offered_transport_is_a_weak_instrument() -> None:
    outcomes = [
        _outcome(
            _transition(
                assignment="offer",
                controller="offer",
                before=("terminal_first",),
                after=("precondition_first",),
            ),
            1.0,
        ),
        _outcome(
            _transition(
                assignment="withhold",
                controller="withhold",
                before=("terminal_first",),
                after=("precondition_first",),
            ),
            1.0,
        ),
    ]

    estimate = estimate_instrumented_plasticity(outcomes)

    assert estimate.status == "weak_instrument"
    assert estimate.complier_net_effect is None
    assert compile_admission_decision(estimate).action == "explore"


def test_estimator_rejects_cross_scope_pooling() -> None:
    left = _transition(
        assignment="offer",
        controller="offer",
        before=("terminal_first",),
        after=("precondition_first",),
    )
    other_scope = _scope("other-observation")
    other_contract = _contract(other_scope)
    pre = _proposal(
        controller="withhold",
        action="terminal",
        features=("terminal_first",),
        scope=other_scope,
    )
    post = _proposal(
        controller="withhold",
        action="terminal",
        features=("terminal_first",),
        parent=pre.sha256,
        scope=other_scope,
    )
    right = compile_instrumented_transition(
        trial_ref="other",
        stratum_sha256="stratum",
        assignment="withhold",
        pre_proposal=pre,
        post_proposal=post,
        contract=other_contract,
    )

    with pytest.raises(ValueError, match="cross proposal scopes"):
        estimate_instrumented_plasticity([
            _outcome(left, 1.0),
            _outcome(right, 0.0),
        ])
