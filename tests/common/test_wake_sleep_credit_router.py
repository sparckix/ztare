from __future__ import annotations

import math

from ztare.common.wake_sleep_credit_router import (
    CreditObservation,
    MemoryAcquisitionProvenance,
    MemoryCandidate,
    MemoryScope,
    RecallExperimentStratum,
    RecallTrialArmOutcome,
    WakeSleepCreditState,
    authorize_recall_consumption,
    consume_recall_once,
    feature_overlap,
    select_sparse_memories,
    select_static_authority_baseline,
    settle_matched_recall_trial,
    settle_recall_credit,
    wake_sleep_credit_state_from_receipt,
)


def _scope(context: str = "context") -> MemoryScope:
    return MemoryScope(
        task_sha256="task",
        controller_sha256="controller",
        context_sha256=context,
        choice_set_sha256="choices",
        action_vocabulary_sha256="actions",
    )


def _candidate(
    revision: str,
    *,
    predicted: float,
    authority: float,
    guard: tuple[str, ...],
    semantic: tuple[str, ...] = (),
    scope: MemoryScope | None = None,
    primitive_action_cost: float = 7.0,
    prompt_token_cost: int = 0,
    acquisition: MemoryAcquisitionProvenance | None = None,
) -> MemoryCandidate:
    return MemoryCandidate(
        provider_id=f"provider-{revision}",
        memory_revision_sha256=revision,
        scope=scope or _scope(),
        predicted_decision_delta=predicted,
        retrieval_cost=0.05,
        primitive_action_cost=primitive_action_cost,
        prompt_token_cost=prompt_token_cost,
        authority_score=authority,
        actionability_score=1.0,
        recency_score=1.0,
        guard_features=guard,
        semantic_features=semantic,
        support_refs=(f"support-{revision}-boundary", f"support-{revision}-core"),
        boundary_support_refs=(f"support-{revision}-boundary",),
        acquisition_provenance=acquisition,
    )


def _settle(
    state: WakeSleepCreditState,
    candidates: tuple[MemoryCandidate, ...],
    revision: str,
    delta: float,
    index: int,
    *,
    contradiction: bool = False,
) -> WakeSleepCreditState:
    recall = select_sparse_memories(
        state,
        candidates,
        scope=_scope(),
        max_items=len(candidates),
        guard_overlap_weight=0.0,
        minimum_score=-2.0,
    )
    candidate = next(
        item
        for item in candidates
        if item.memory_revision_sha256 == revision
    )
    next_state, receipt = settle_recall_credit(
        state,
        candidates,
        recall=recall,
        observation=CreditObservation(
            scope=_scope(),
            memory_revision_sha256=revision,
            observed_decision_delta=delta,
            external_outcome_ref=f"outcome-{revision}-{index}",
            matched_control_ref=f"ablation-{revision}-{index}",
            primitive_action_cost_before=candidate.primitive_action_cost,
            primitive_action_cost_after=candidate.primitive_action_cost,
            authoritative_contradiction=contradiction,
        ),
    )
    assert receipt.status == "settled"
    return next_state


def test_outcome_credit_overrides_static_authority() -> None:
    causal = _candidate(
        "causal",
        predicted=0.2,
        authority=60,
        guard=("g1", "g2"),
    )
    confuser = _candidate(
        "confuser",
        predicted=0.8,
        authority=100,
        guard=("g1", "g2"),
    )
    candidates = (causal, confuser)
    state = WakeSleepCreditState()

    initial = select_sparse_memories(
        state,
        candidates,
        scope=_scope(),
        max_items=1,
    )
    assert initial.selections[0].memory_revision_sha256 == "confuser"
    assert (
        select_static_authority_baseline(
            candidates,
            scope=_scope(),
            max_items=1,
        )[0].memory_revision_sha256
        == "confuser"
    )

    for index in range(12):
        state = _settle(state, candidates, "causal", 0.8, index)
        state = _settle(state, candidates, "confuser", 0.45, index)

    learned = select_sparse_memories(
        state,
        candidates,
        scope=_scope(),
        max_items=1,
    )
    assert learned.selections[0].memory_revision_sha256 == "causal"


def test_hash_bound_credit_state_rehydrates_without_identity_drift() -> None:
    causal = _candidate(
        "causal",
        predicted=0.2,
        authority=60,
        guard=("g1",),
    )
    state = _settle(
        WakeSleepCreditState(),
        (causal,),
        "causal",
        0.75,
        0,
    )
    receipt = state.to_receipt()

    restored = wake_sleep_credit_state_from_receipt(receipt)
    assert restored == state

    mutated = {
        **receipt,
        "credits": [
            {
                **receipt["credits"][0],
                "sum_observed_delta": 0.5,
            }
        ],
    }
    try:
        wake_sleep_credit_state_from_receipt(mutated)
    except ValueError as exc:
        assert "hash mismatch" in str(exc)
    else:
        raise AssertionError("mutated credit receipt was accepted")


def test_scope_and_primitive_cost_are_settlement_boundaries() -> None:
    causal = _candidate(
        "causal",
        predicted=0.7,
        authority=60,
        guard=("g1",),
    )
    candidates = (causal,)
    state = WakeSleepCreditState()
    recall = select_sparse_memories(
        state,
        candidates,
        scope=_scope(),
        max_items=1,
    )
    prior_sha = state.to_receipt()["sha256"]

    unchanged, mismatch = settle_recall_credit(
        state,
        candidates,
        recall=recall,
        observation=CreditObservation(
            scope=_scope("other-context"),
            memory_revision_sha256="causal",
            observed_decision_delta=1.0,
            external_outcome_ref="outside",
            matched_control_ref="outside-control",
            primitive_action_cost_before=7.0,
            primitive_action_cost_after=7.0,
        ),
    )
    assert mismatch.reason == "scope_mismatch"
    assert unchanged.to_receipt()["sha256"] == prior_sha

    unchanged, drift = settle_recall_credit(
        state,
        candidates,
        recall=recall,
        observation=CreditObservation(
            scope=_scope(),
            memory_revision_sha256="causal",
            observed_decision_delta=1.0,
            external_outcome_ref="drift",
            matched_control_ref="drift-control",
            primitive_action_cost_before=7.0,
            primitive_action_cost_after=6.0,
        ),
    )
    assert drift.reason == "primitive_action_cost_drift"
    assert unchanged.to_receipt()["sha256"] == prior_sha


def test_guard_overlap_beats_orthogonal_semantic_similarity() -> None:
    causal = _candidate(
        "causal",
        predicted=0.75,
        authority=60,
        guard=("shared-1", "shared-2"),
        semantic=("route", "switch"),
    )
    overlapping = _candidate(
        "overlapping",
        predicted=0.48,
        authority=100,
        guard=("shared-1", "shared-2"),
        semantic=("unrelated",),
    )
    semantic_twin = _candidate(
        "semantic-twin",
        predicted=0.42,
        authority=80,
        guard=("disjoint-1", "disjoint-2"),
        semantic=("route", "switch"),
    )
    candidates = (causal, overlapping, semantic_twin)
    state = WakeSleepCreditState()

    without_guard_cost = select_sparse_memories(
        state,
        candidates,
        scope=_scope(),
        max_items=2,
        guard_overlap_weight=0.0,
    )
    assert [
        row.memory_revision_sha256
        for row in without_guard_cost.selections
    ] == ["causal", "overlapping"]

    guarded = select_sparse_memories(
        state,
        candidates,
        scope=_scope(),
        max_items=2,
        guard_overlap_weight=0.2,
    )
    assert [
        row.memory_revision_sha256 for row in guarded.selections
    ] == ["causal", "semantic-twin"]
    assert feature_overlap(
        causal.guard_features,
        overlapping.guard_features,
    ) == 1.0
    assert feature_overlap(
        causal.semantic_features,
        semantic_twin.semantic_features,
    ) == 1.0


def test_contradiction_reopens_boundary_then_demotes() -> None:
    causal = _candidate(
        "causal",
        predicted=0.7,
        authority=60,
        guard=("g1",),
    )
    candidates = (causal,)
    state = _settle(
        WakeSleepCreditState(),
        candidates,
        "causal",
        0.8,
        0,
    )
    assert state.credit_for(causal).lifecycle == "active"

    state = _settle(
        state,
        candidates,
        "causal",
        -1.0,
        1,
        contradiction=True,
    )
    assert state.credit_for(causal).lifecycle == "probation"
    assert state.credit_for(causal).reopened_support_refs == (
        "support-causal-boundary",
    )

    state = _settle(
        state,
        candidates,
        "causal",
        -1.0,
        2,
        contradiction=True,
    )
    state = _settle(
        state,
        candidates,
        "causal",
        -1.0,
        3,
        contradiction=True,
    )
    assert state.credit_for(causal).lifecycle == "demoted"
    assert state.credit_for(causal).reopened_support_refs == ()
    recall = select_sparse_memories(
        state,
        candidates,
        scope=_scope(),
        max_items=1,
    )
    assert recall.selections == ()


def _acquisition() -> MemoryAcquisitionProvenance:
    return MemoryAcquisitionProvenance(
        episode_sha256="source-episode",
        observation_sha256="source-boundary-observation",
        controller_instance_sha256="source-controller-instance",
        support_sha256s=("support-a", "support-b"),
        boundary_support_sha256s=("support-b",),
    )


def test_acquisition_and_one_shot_consumption_are_distinct_identities() -> None:
    candidate = _candidate(
        "causal",
        predicted=0.7,
        authority=60,
        guard=("g1",),
        acquisition=_acquisition(),
    )
    recall = select_sparse_memories(
        WakeSleepCreditState(),
        (candidate,),
        scope=_scope(),
        max_items=1,
    )
    decision = authorize_recall_consumption(
        recall,
        (candidate,),
        controller_instance_sha256="inject-instance",
        observation_sha256="context",
        decision_ref="pair-1:inject:decision-0",
        compatibility_transport_sha256="transport-certificate",
    )

    assert (
        candidate.acquisition_provenance.observation_sha256
        != decision.observation_sha256
    )
    consumed, receipt = consume_recall_once(
        decision,
        controller_instance_sha256="inject-instance",
        observation_sha256="context",
    )
    assert receipt.status == "consumed"
    assert consumed.remaining_direct_injections == 0

    unchanged, replay = consume_recall_once(
        consumed,
        controller_instance_sha256="inject-instance",
        observation_sha256="context",
    )
    assert replay.reason == "direct_injection_already_consumed"
    assert unchanged == consumed

    _, changed_observation = consume_recall_once(
        decision,
        controller_instance_sha256="inject-instance",
        observation_sha256="later-observation",
    )
    assert changed_observation.reason == "observation_mismatch"


def test_matched_trial_uses_distinct_instances_and_fixed_primitive_cost() -> None:
    candidate = _candidate(
        "causal",
        predicted=0.4,
        authority=60,
        guard=("g1",),
        primitive_action_cost=4.0,
        acquisition=_acquisition(),
    )
    state = WakeSleepCreditState()
    recall = select_sparse_memories(
        state,
        (candidate,),
        scope=_scope(),
        max_items=1,
    )
    decision = authorize_recall_consumption(
        recall,
        (candidate,),
        controller_instance_sha256="inject-instance",
        observation_sha256="context",
        decision_ref="pair-1:inject:decision-0",
        compatibility_transport_sha256="transport-certificate",
    )
    _, consumption = consume_recall_once(
        decision,
        controller_instance_sha256="inject-instance",
        observation_sha256="context",
    )
    stratum = RecallExperimentStratum(
        scope=_scope(),
        restored_prefix_sha256="prefix",
        restored_observation_sha256="context",
        action_budget=4,
        primitive_action_cost=4.0,
        randomization_seed_sha256="seed",
    )
    inject = RecallTrialArmOutcome(
        stratum_sha256=stratum.sha256,
        arm_id="pair-1-inject",
        assignment="inject",
        controller_instance_sha256="inject-instance",
        runtime_controller_instance_ref="runtime-inject",
        trajectory_sha256="inject-trajectory",
        external_outcome_ref="inject-outcome",
        primitive_action_cost=4.0,
        task_score=1.0,
        efficiency_score=0.75,
        information_yield=0.5,
        recall_consumption_sha256=consumption.sha256,
    )
    ablate = RecallTrialArmOutcome(
        stratum_sha256=stratum.sha256,
        arm_id="pair-1-ablate",
        assignment="ablate",
        controller_instance_sha256="ablate-instance",
        runtime_controller_instance_ref="runtime-ablate",
        trajectory_sha256="ablate-trajectory",
        external_outcome_ref="ablate-outcome",
        primitive_action_cost=4.0,
        task_score=0.0,
        efficiency_score=0.0,
        information_yield=0.25,
    )

    next_state, matched = settle_matched_recall_trial(
        state,
        (candidate,),
        recall=recall,
        consumption_decision=decision,
        consumption_receipt=consumption,
        stratum=stratum,
        inject=inject,
        ablate=ablate,
        memory_revision_sha256="causal",
    )
    assert matched.status == "settled"
    assert matched.observed_task_delta == 1.0
    assert matched.observed_information_yield_delta == 0.25
    assert math.isclose(matched.observed_decision_delta, 0.95)
    assert next_state.credit_for(candidate).settlement_count == 1

    reused_controller = RecallTrialArmOutcome(
        stratum_sha256=stratum.sha256,
        arm_id="pair-1-ablate-reused",
        assignment="ablate",
        controller_instance_sha256="inject-instance",
        runtime_controller_instance_ref="runtime-ablate-reused",
        trajectory_sha256="other-trajectory",
        external_outcome_ref="other-ablate-outcome",
        primitive_action_cost=4.0,
        task_score=0.0,
        efficiency_score=0.0,
        information_yield=0.25,
    )
    unchanged, rejected = settle_matched_recall_trial(
        state,
        (candidate,),
        recall=recall,
        consumption_decision=decision,
        consumption_receipt=consumption,
        stratum=stratum,
        inject=inject,
        ablate=reused_controller,
        memory_revision_sha256="causal",
    )
    assert rejected.reason == "controller_instance_reused"
    assert unchanged == state


def test_sparse_recall_respects_exact_prompt_token_budget() -> None:
    first = _candidate(
        "first",
        predicted=0.9,
        authority=60,
        guard=("g1",),
        prompt_token_cost=70,
    )
    second = _candidate(
        "second",
        predicted=0.8,
        authority=50,
        guard=("g2",),
        prompt_token_cost=40,
    )
    third = _candidate(
        "third",
        predicted=0.7,
        authority=40,
        guard=("g3",),
        prompt_token_cost=30,
    )
    recall = select_sparse_memories(
        WakeSleepCreditState(),
        (first, second, third),
        scope=_scope(),
        max_items=3,
        max_prompt_tokens=100,
    )
    assert [
        row.memory_revision_sha256 for row in recall.selections
    ] == ["first", "third"]
    assert recall.to_receipt()["selected_prompt_tokens"] == 100
