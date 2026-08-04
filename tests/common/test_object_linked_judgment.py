from __future__ import annotations

import pytest

from ztare.common.instrumented_proposal_plasticity import (
    InstrumentedProposalOutcome,
    estimate_instrumented_plasticity,
)
from ztare.common.object_basin_response import (
    compile_object_admission,
    compile_object_response_family,
    object_outcome_from_receipt,
    object_transition_from_receipt,
)
from ztare.common.object_linked_judgment import (
    ObjectLinkedControllerProposal,
    ObjectReferenceAuthority,
    ObjectRolePathContract,
    compile_object_linked_transition,
    proposal_satisfies_object_contract,
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


def _authority(
    observation: str = "observation",
) -> ObjectReferenceAuthority:
    return ObjectReferenceAuthority(
        observation_sha256=observation,
        catalog_sha256=f"catalog:{observation}",
        object_refs=("object:mover", "object:marker", "object:target"),
    )


def _contract(
    *,
    scope: MemoryScope | None = None,
    authority: ObjectReferenceAuthority | None = None,
) -> ObjectRolePathContract:
    use_scope = scope or _scope()
    use_authority = authority or _authority(use_scope.context_sha256)
    return ObjectRolePathContract(
        scope=use_scope,
        catalog_sha256=use_authority.catalog_sha256,
        intervention_revision_sha256="intervention",
        required_controlled_object_ref="object:mover",
        required_waypoint_refs=("object:marker", "object:target"),
        forbidden_controlled_object_refs=("object:marker",),
        evidence_refs=("episode:7",),
    )


def _proposal(
    *,
    controller: str,
    controlled: str,
    waypoints: tuple[str, ...],
    action: str = "0",
    prediction: str = "prediction",
    parent: str = "",
    intervention: str = "",
    scope: MemoryScope | None = None,
    authority: ObjectReferenceAuthority | None = None,
) -> ObjectLinkedControllerProposal:
    use_scope = scope or _scope()
    use_authority = authority or _authority(use_scope.context_sha256)
    return ObjectLinkedControllerProposal(
        scope=use_scope,
        controller_instance_sha256=controller,
        observation_sha256=use_scope.context_sha256,
        catalog_sha256=use_authority.catalog_sha256,
        proposal_ref=(
            f"{controller}:{controlled}:{waypoints}:{action}:{prediction}"
        ),
        action_ref=action,
        predicted_consequence_ref=prediction,
        controlled_object_ref=controlled,
        ordered_waypoint_refs=waypoints,
        parent_proposal_sha256=parent,
        consumed_intervention_revision_sha256=intervention,
    )


def _transition(
    *,
    assignment: str,
    controller: str,
    before_controlled: str = "object:marker",
    before_waypoints: tuple[str, ...] = ("object:target",),
    after_controlled: str = "object:mover",
    after_waypoints: tuple[str, ...] = (
        "object:marker",
        "object:target",
    ),
):
    authority = _authority()
    contract = _contract(authority=authority)
    pre = _proposal(
        controller=controller,
        controlled=before_controlled,
        waypoints=before_waypoints,
        authority=authority,
    )
    post = _proposal(
        controller=controller,
        controlled=after_controlled,
        waypoints=after_waypoints,
        action="1",
        parent=pre.sha256,
        intervention=(
            contract.intervention_revision_sha256
            if assignment == "offer"
            else ""
        ),
        authority=authority,
    )
    return compile_object_linked_transition(
        trial_ref=f"trial:{controller}",
        stratum_sha256="stratum",
        assignment=assignment,
        pre_proposal=pre,
        post_proposal=post,
        contract=contract,
        authority=authority,
    )


def test_ordered_object_path_controls_contract_satisfaction() -> None:
    contract = _contract()
    correct = _proposal(
        controller="controller",
        controlled="object:mover",
        waypoints=("object:marker", "object:target"),
    )
    reversed_path = _proposal(
        controller="controller",
        controlled="object:mover",
        waypoints=("object:target", "object:marker"),
    )

    assert proposal_satisfies_object_contract(correct, contract) is True
    assert proposal_satisfies_object_contract(
        reversed_path,
        contract,
    ) is False


def test_offer_compiles_typed_supported_transport() -> None:
    transition = _transition(
        assignment="offer",
        controller="offered",
    )

    assert transition.relation == "offered_supported_transport"
    assert transition.supported_transport is True
    assert transition.changed_path is True


def test_text_only_revision_cannot_manufacture_path_uptake() -> None:
    authority = _authority()
    contract = _contract(authority=authority)
    pre = _proposal(
        controller="controller",
        controlled="object:marker",
        waypoints=("object:target",),
        prediction="wrong words",
        authority=authority,
    )
    post = _proposal(
        controller="controller",
        controlled="object:marker",
        waypoints=("object:target",),
        prediction="now mentions the correct marker",
        parent=pre.sha256,
        intervention="intervention",
        authority=authority,
    )

    transition = compile_object_linked_transition(
        trial_ref="trial",
        stratum_sha256="stratum",
        assignment="offer",
        pre_proposal=pre,
        post_proposal=post,
        contract=contract,
        authority=authority,
    )

    assert transition.changed_prediction is True
    assert transition.changed_path is False
    assert transition.supported_transport is False


def test_unknown_and_cross_observation_refs_fail_closed() -> None:
    authority = _authority()
    contract = _contract(authority=authority)
    pre = _proposal(
        controller="controller",
        controlled="object:unknown",
        waypoints=("object:target",),
        authority=authority,
    )
    post = _proposal(
        controller="controller",
        controlled="object:mover",
        waypoints=("object:marker", "object:target"),
        parent=pre.sha256,
        intervention="intervention",
        authority=authority,
    )

    with pytest.raises(ValueError, match="unknown object refs"):
        compile_object_linked_transition(
            trial_ref="trial",
            stratum_sha256="stratum",
            assignment="offer",
            pre_proposal=pre,
            post_proposal=post,
            contract=contract,
            authority=authority,
        )

    other_authority = _authority("other-observation")
    with pytest.raises(ValueError, match="observation authority"):
        compile_object_linked_transition(
            trial_ref="trial",
            stratum_sha256="stratum",
            assignment="offer",
            pre_proposal=_proposal(
                controller="controller",
                controlled="object:marker",
                waypoints=("object:target",),
                authority=authority,
            ),
            post_proposal=post,
            contract=contract,
            authority=other_authority,
        )


def test_object_linked_transition_uses_generic_instrument_estimator() -> None:
    offered = _transition(
        assignment="offer",
        controller="offered",
    )
    withheld = _transition(
        assignment="withhold",
        controller="withheld",
        after_controlled="object:marker",
        after_waypoints=("object:target",),
    )
    outcomes = [
        InstrumentedProposalOutcome(
            transition=offered,
            external_outcome_ref="outcome:offer",
            external_value=1.0,
            offer_cost=0.1,
            primitive_action_cost=20.0,
        ),
        InstrumentedProposalOutcome(
            transition=withheld,
            external_outcome_ref="outcome:withhold",
            external_value=0.0,
            offer_cost=0.0,
            primitive_action_cost=20.0,
        ),
    ]

    estimate = estimate_instrumented_plasticity(
        outcomes,
        minimum_first_stage=0.5,
    )

    assert estimate.status == "identified"
    assert estimate.first_stage_transport_delta == 1.0
    assert estimate.intent_to_treat_net_delta == pytest.approx(0.9)


def _settled_response_rows():
    outcomes = []
    for index in range(2):
        offered = _transition(
            assignment="offer",
            controller=f"offered:{index}",
        )
        withheld = _transition(
            assignment="withhold",
            controller=f"withheld:{index}",
            after_controlled="object:marker",
            after_waypoints=("object:target",),
        )
        outcomes.extend([
            InstrumentedProposalOutcome(
                transition=offered,
                external_outcome_ref=f"outcome:offer:{index}",
                external_value=0.8,
                offer_cost=0.1,
                primitive_action_cost=20.0,
            ),
            InstrumentedProposalOutcome(
                transition=withheld,
                external_outcome_ref=f"outcome:withhold:{index}",
                external_value=0.1,
                offer_cost=0.0,
                primitive_action_cost=20.0,
            ),
        ])
    return tuple(outcomes)


def test_response_family_spends_credit_only_in_the_trained_basin() -> None:
    outcomes = _settled_response_rows()
    family = compile_object_response_family(
        outcomes,
        source_result_ref="result.json",
        source_result_sha256="source-result",
    )
    authority = _authority()
    contract = _contract(authority=authority)
    wrong_control = _proposal(
        controller="prospective",
        controlled="object:marker",
        waypoints=("object:target",),
        authority=authority,
    )

    decision = compile_object_admission(
        wrong_control,
        contract=contract,
        authority=authority,
        family=family,
    )

    assert len(family.responses) == 1
    assert family.responses[0].status == "identified_positive"
    assert family.responses[0].intent_to_treat_net_delta == (
        pytest.approx(0.6)
    )
    assert decision.action == "offer"
    assert decision.pre_basin_sha256 == (
        outcomes[0].transition.pre_basin_sha256
    )


def test_response_family_silences_satisfied_and_explores_unseen_plans() -> None:
    family = compile_object_response_family(
        _settled_response_rows(),
        source_result_ref="result.json",
        source_result_sha256="source-result",
    )
    authority = _authority()
    contract = _contract(authority=authority)
    satisfied = _proposal(
        controller="satisfied",
        controlled="object:mover",
        waypoints=("object:marker", "object:target"),
        authority=authority,
    )
    unseen = _proposal(
        controller="unseen",
        controlled="object:target",
        waypoints=("object:marker",),
        authority=authority,
    )

    assert compile_object_admission(
        satisfied,
        contract=contract,
        authority=authority,
        family=family,
    ).action == "silence"
    assert compile_object_admission(
        unseen,
        contract=contract,
        authority=authority,
        family=family,
    ).action == "explore"


def test_object_response_rehydration_rejects_receipt_drift() -> None:
    outcome = _settled_response_rows()[0]
    transition_receipt = outcome.transition.to_receipt()
    restored_transition = object_transition_from_receipt(
        transition_receipt
    )
    restored_outcome = object_outcome_from_receipt(
        outcome.to_receipt(),
        transition=restored_transition,
    )

    assert restored_transition == outcome.transition
    assert restored_outcome.to_receipt() == outcome.to_receipt()

    drifted = {**transition_receipt, "relation": "offered_no_uptake"}
    with pytest.raises(ValueError, match="hash or fields drifted"):
        object_transition_from_receipt(drifted)
