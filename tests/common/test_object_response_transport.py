from __future__ import annotations

from ztare.common.decision_intervention_market import (
    DecisionInterventionProposal,
)
from ztare.common.instrumented_proposal_plasticity import (
    InstrumentedProposalOutcome,
)
from ztare.common.object_basin_response import (
    compile_object_response_family,
)
from ztare.common.object_linked_judgment import (
    ObjectLinkedControllerProposal,
    ObjectReferenceAuthority,
    ObjectRolePathContract,
    compile_object_linked_transition,
)
from ztare.common.object_response_transport import (
    compile_intervention_revision_transport,
    compile_response_transport_candidate,
    compile_unique_type_object_transport,
    transport_object_role_contract,
)
from ztare.common.wake_sleep_credit_router import (
    MemoryAcquisitionProvenance,
    MemoryScope,
)
from ztare.worldmodel.observation_object_catalog import (
    compile_grid_object_catalog,
)


def _grid(
    *,
    mover_origin: tuple[int, int],
    include_marker: bool = True,
) -> tuple[tuple[int, ...], ...]:
    rows = [[3 for _x in range(12)] for _y in range(12)]
    if include_marker:
        for y, x, value in (
            (2, 3, 0),
            (3, 2, 1),
            (3, 3, 0),
            (3, 4, 0),
            (4, 3, 1),
        ):
            rows[y][x] = value
    y0, x0 = mover_origin
    for dy in range(2):
        for dx in range(2):
            rows[y0 + dy][x0 + dx] = 12 if dy == 0 else 9
    return tuple(tuple(row) for row in rows)


def _scope(context: str) -> MemoryScope:
    return MemoryScope(
        task_sha256="task",
        controller_sha256="controller",
        context_sha256=context,
        choice_set_sha256="choices",
        action_vocabulary_sha256="actions",
    )


def _proposal(
    *,
    scope: MemoryScope,
    catalog_sha256: str,
    controller: str,
    controlled: str,
    waypoints: tuple[str, ...],
    parent: str = "",
    intervention: str = "",
) -> ObjectLinkedControllerProposal:
    return ObjectLinkedControllerProposal(
        scope=scope,
        controller_instance_sha256=controller,
        observation_sha256=scope.context_sha256,
        catalog_sha256=catalog_sha256,
        proposal_ref=f"proposal:{controller}:{parent or 'pre'}",
        action_ref="2" if parent else "0",
        predicted_consequence_ref=(
            f"prediction:{controller}:{parent or 'pre'}"
        ),
        controlled_object_ref=controlled,
        ordered_waypoint_refs=waypoints,
        parent_proposal_sha256=parent,
        consumed_intervention_revision_sha256=intervention,
    )


def _intervention(scope: MemoryScope) -> DecisionInterventionProposal:
    return DecisionInterventionProposal(
        intervention_kind="memory",
        provider_id="provider",
        provider_revision_sha256="provider-revision",
        rendered_content_sha256=f"rendered:{scope.context_sha256}",
        rendered_token_count=12,
        tokenizer_sha256="tokenizer",
        scope=scope,
        acquisition_provenance=MemoryAcquisitionProvenance(
            episode_sha256="episode",
            observation_sha256="acquisition-observation",
            controller_instance_sha256="acquisition-controller",
            support_sha256s=("support",),
        ),
        predicted_decision_delta=0.5,
        prompt_cost_per_token=0.0,
        primitive_action_cost=20.0,
        authority_score=1.0,
        actionability_score=1.0,
        recency_score=1.0,
        guard_features=("guard",),
        semantic_features=("semantic",),
        support_refs=("support",),
        content_ref="content",
    )


def _source_fixture():
    catalog = compile_grid_object_catalog(
        _grid(mover_origin=(8, 8)),
        observation_sha256="source-observation",
    )
    marker = catalog.resolve_selector({
        "palette": [0, 1],
        "cell_count": 5,
    })
    mover = catalog.resolve_selector({
        "palette": [9, 12],
        "cell_count": 4,
    })
    scope = _scope("source-observation")
    intervention = _intervention(scope)
    contract = ObjectRolePathContract(
        scope=scope,
        catalog_sha256=catalog.sha256,
        intervention_revision_sha256=(
            intervention.intervention_revision_sha256
        ),
        required_controlled_object_ref=mover.object_ref,
        required_waypoint_refs=(marker.object_ref,),
        forbidden_controlled_object_refs=(marker.object_ref,),
        evidence_refs=("source-evidence",),
    )
    outcomes = []
    witness_pre = None
    witness_post = None
    for index in range(2):
        for assignment in ("offer", "withhold"):
            controller = f"{assignment}:{index}"
            pre = _proposal(
                scope=scope,
                catalog_sha256=catalog.sha256,
                controller=controller,
                controlled=marker.object_ref,
                waypoints=(mover.object_ref,),
            )
            post = _proposal(
                scope=scope,
                catalog_sha256=catalog.sha256,
                controller=controller,
                controlled=(
                    mover.object_ref
                    if assignment == "offer"
                    else marker.object_ref
                ),
                waypoints=(
                    (marker.object_ref,)
                    if assignment == "offer"
                    else (mover.object_ref,)
                ),
                parent=pre.sha256,
                intervention=(
                    contract.intervention_revision_sha256
                    if assignment == "offer"
                    else ""
                ),
            )
            transition = compile_object_linked_transition(
                trial_ref=f"trial:{controller}",
                stratum_sha256=f"stratum:{index}",
                assignment=assignment,
                pre_proposal=pre,
                post_proposal=post,
                contract=contract,
                authority=ObjectReferenceAuthority(
                    observation_sha256=catalog.observation_sha256,
                    catalog_sha256=catalog.sha256,
                    object_refs=catalog.object_refs,
                ),
            )
            outcomes.append(InstrumentedProposalOutcome(
                transition=transition,
                external_outcome_ref=f"outcome:{controller}",
                external_value=1.0 if assignment == "offer" else 0.0,
                offer_cost=0.0,
                primitive_action_cost=20.0,
            ))
            if assignment == "offer" and witness_pre is None:
                witness_pre = pre
                witness_post = post
    family = compile_object_response_family(
        outcomes,
        source_result_ref="source-result.json",
        source_result_sha256="source-result",
    )
    assert witness_pre is not None and witness_post is not None
    return (
        catalog,
        marker,
        mover,
        intervention,
        contract,
        family,
        witness_pre,
        witness_post,
    )


def test_response_transport_compiles_candidate_square() -> None:
    (
        source_catalog,
        source_marker,
        source_mover,
        source_intervention,
        source_contract,
        family,
        source_pre,
        source_post,
    ) = _source_fixture()
    target_catalog = compile_grid_object_catalog(
        _grid(mover_origin=(8, 6)),
        observation_sha256="target-observation",
    )
    transport = compile_unique_type_object_transport(
        source_catalog,
        target_catalog,
        required_source_object_refs=(
            source_marker.object_ref,
            source_mover.object_ref,
        ),
        evidence_refs=("prefix:2",),
    )
    target_scope = _scope("target-observation")
    target_intervention = _intervention(target_scope)
    intervention_transport = compile_intervention_revision_transport(
        source_intervention,
        target_intervention,
        source_payload_invariant_sha256="payload",
        target_payload_invariant_sha256="payload",
        evidence_refs=("source-and-target-rendering",),
    )
    target_contract = transport_object_role_contract(
        source_contract,
        target_scope=target_scope,
        target_catalog=target_catalog,
        transport=transport,
        intervention_transport=intervention_transport,
        evidence_refs=("source-contract", f"transport:{transport.sha256}"),
    )
    target_pre = _proposal(
        scope=target_contract.scope,
        catalog_sha256=target_catalog.sha256,
        controller="target-controller",
        controlled=transport.map_ref(source_marker.object_ref),
        waypoints=(transport.map_ref(source_mover.object_ref),),
    )

    candidate = compile_response_transport_candidate(
        source_family=family,
        source_response=family.responses[0],
        object_transport=transport,
        intervention_transport=intervention_transport,
        source_contract=source_contract,
        target_contract=target_contract,
        source_pre_proposal=source_pre,
        source_post_proposal=source_post,
        target_pre_proposal=target_pre,
    )

    assert transport.status == "transportable"
    assert intervention_transport.status == "transportable"
    assert (
        target_contract.intervention_revision_sha256
        == target_intervention.intervention_revision_sha256
    )
    assert candidate.status == "candidate_commuting"
    assert candidate.action == "explore_transport"
    assert candidate.source_basin_signature == (
        candidate.target_basin_signature
    )


def test_response_transport_refuses_missing_contract_object() -> None:
    (
        source_catalog,
        source_marker,
        source_mover,
        _source_intervention,
        _source_contract,
        _family,
        _source_pre,
        _source_post,
    ) = _source_fixture()
    target_catalog = compile_grid_object_catalog(
        _grid(mover_origin=(8, 6), include_marker=False),
        observation_sha256="target-without-marker",
    )

    transport = compile_unique_type_object_transport(
        source_catalog,
        target_catalog,
        required_source_object_refs=(
            source_marker.object_ref,
            source_mover.object_ref,
        ),
        evidence_refs=("prefix:marker-contact",),
    )

    assert transport.status == "refused"
    assert transport.reason == (
        "required_contract_object_has_no_unique_target"
    )
