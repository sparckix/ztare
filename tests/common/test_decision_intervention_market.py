from __future__ import annotations

from ztare.common.decision_intervention_market import (
    DecisionInterventionArmOutcome,
    DecisionInterventionProposal,
    allocate_decision_interventions,
    settle_pairwise_intervention_trial,
)
from ztare.common.wake_sleep_credit_router import (
    CreditObservation,
    MemoryAcquisitionProvenance,
    MemoryScope,
    RecallExperimentStratum,
    WakeSleepCreditState,
    authorize_recall_consumption,
    consume_recall_once,
    select_sparse_memories,
    settle_recall_credit,
)


def _scope() -> MemoryScope:
    return MemoryScope(
        task_sha256="task",
        controller_sha256="controller-class",
        context_sha256="current-decision",
        choice_set_sha256="choice-set",
        action_vocabulary_sha256="actions",
    )


def _acquisition(provider: str) -> MemoryAcquisitionProvenance:
    return MemoryAcquisitionProvenance(
        episode_sha256=f"{provider}-episode",
        observation_sha256=f"{provider}-source-observation",
        controller_instance_sha256=f"{provider}-source-controller",
        support_sha256s=(f"{provider}-support",),
    )


def _proposal(
    *,
    kind: str,
    provider: str,
    content: str,
    predicted: float,
    authority: float,
    tokens: int = 50,
    guard: tuple[str, ...] = (),
) -> DecisionInterventionProposal:
    return DecisionInterventionProposal(
        intervention_kind=kind,
        provider_id=provider,
        provider_revision_sha256=f"{provider}-source-revision",
        rendered_content_sha256=content,
        rendered_token_count=tokens,
        tokenizer_sha256="tokenizer-v1",
        scope=_scope(),
        acquisition_provenance=_acquisition(provider),
        predicted_decision_delta=predicted,
        prompt_cost_per_token=0.001,
        primitive_action_cost=5.0,
        authority_score=authority,
        actionability_score=1.0,
        recency_score=1.0,
        guard_features=guard,
        support_refs=(f"{provider}-support-ref",),
    )


def test_rendered_or_provider_identity_change_mints_new_intervention() -> None:
    original = _proposal(
        kind="briefing_provider",
        provider="survivors",
        content="content-a",
        predicted=0.5,
        authority=80,
    )
    content_changed = _proposal(
        kind="briefing_provider",
        provider="survivors",
        content="content-b",
        predicted=0.5,
        authority=80,
    )
    provider_changed = _proposal(
        kind="skill",
        provider="different-provider",
        content="content-a",
        predicted=0.5,
        authority=80,
    )

    assert (
        original.intervention_revision_sha256
        != content_changed.intervention_revision_sha256
    )
    assert (
        original.intervention_revision_sha256
        != provider_changed.intervention_revision_sha256
    )


def test_market_shares_one_exact_prompt_budget_across_provider_kinds() -> None:
    memory = _proposal(
        kind="episodic_memory",
        provider="sleep",
        content="memory-content",
        predicted=0.9,
        authority=50,
        tokens=70,
        guard=("mechanic",),
    )
    briefing = _proposal(
        kind="briefing_provider",
        provider="survivors",
        content="briefing-content",
        predicted=0.8,
        authority=90,
        tokens=40,
        guard=("candidate",),
    )
    skill = _proposal(
        kind="skill",
        provider="workflow",
        content="skill-content",
        predicted=0.7,
        authority=70,
        tokens=30,
        guard=("procedure",),
    )

    allocation = allocate_decision_interventions(
        WakeSleepCreditState(),
        (memory, briefing, skill),
        scope=_scope(),
        max_items=3,
        max_prompt_tokens=100,
    )
    selected = allocation.selected_proposal_revision_sha256s
    assert memory.intervention_revision_sha256 in selected
    assert skill.intervention_revision_sha256 in selected
    assert briefing.intervention_revision_sha256 not in selected
    assert allocation.recall.to_receipt()["selected_prompt_tokens"] == 100


def test_matched_outcomes_override_provider_kind_and_static_authority() -> None:
    causal = _proposal(
        kind="skill",
        provider="low-authority-skill",
        content="causal-content",
        predicted=0.2,
        authority=40,
    )
    confuser = _proposal(
        kind="briefing_provider",
        provider="high-authority-briefing",
        content="confuser-content",
        predicted=0.8,
        authority=100,
    )
    proposals = (causal, confuser)
    candidates = tuple(
        proposal.to_memory_candidate() for proposal in proposals
    )
    state = WakeSleepCreditState()

    initial = allocate_decision_interventions(
        state,
        proposals,
        scope=_scope(),
        max_items=1,
        max_prompt_tokens=50,
    )
    assert initial.selected_proposal_revision_sha256s == (
        confuser.intervention_revision_sha256,
    )

    for index in range(12):
        recall = allocate_decision_interventions(
            state,
            proposals,
            scope=_scope(),
            max_items=2,
            max_prompt_tokens=100,
            minimum_score=-2.0,
        ).recall
        for proposal, observed in (
            (causal, 0.8),
            (confuser, 0.0),
        ):
            state, receipt = settle_recall_credit(
                state,
                candidates,
                recall=recall,
                observation=CreditObservation(
                    scope=_scope(),
                    memory_revision_sha256=(
                        proposal.intervention_revision_sha256
                    ),
                    observed_decision_delta=observed,
                    external_outcome_ref=(
                        f"{proposal.provider_id}-outcome-{index}"
                    ),
                    matched_control_ref=(
                        f"{proposal.provider_id}-control-{index}"
                    ),
                    primitive_action_cost_before=5.0,
                    primitive_action_cost_after=5.0,
                ),
            )
            assert receipt.status == "settled"

    learned = allocate_decision_interventions(
        state,
        proposals,
        scope=_scope(),
        max_items=1,
        max_prompt_tokens=50,
    )
    assert learned.selected_proposal_revision_sha256s == (
        causal.intervention_revision_sha256,
    )


def test_active_intervention_duel_credits_both_sides_symmetrically() -> None:
    mechanics = _proposal(
        kind="episodic_memory",
        provider="mechanics",
        content="mechanics-content",
        predicted=0.4,
        authority=50,
    )
    redundant = _proposal(
        kind="episodic_memory",
        provider="redundant",
        content="redundant-content",
        predicted=0.8,
        authority=90,
    )
    state = WakeSleepCreditState()
    mechanics_candidate = mechanics.to_memory_candidate()
    redundant_candidate = redundant.to_memory_candidate()
    mechanics_recall = select_sparse_memories(
        state,
        (mechanics_candidate,),
        scope=_scope(),
        max_items=1,
    )
    redundant_recall = select_sparse_memories(
        state,
        (redundant_candidate,),
        scope=_scope(),
        max_items=1,
    )
    mechanics_decision = authorize_recall_consumption(
        mechanics_recall,
        (mechanics_candidate,),
        controller_instance_sha256="mechanics-instance",
        observation_sha256="current-decision",
        decision_ref="duel:mechanics",
        compatibility_transport_sha256="mechanics-transport",
    )
    redundant_decision = authorize_recall_consumption(
        redundant_recall,
        (redundant_candidate,),
        controller_instance_sha256="redundant-instance",
        observation_sha256="current-decision",
        decision_ref="duel:redundant",
        compatibility_transport_sha256="redundant-transport",
    )
    _, mechanics_consumption = consume_recall_once(
        mechanics_decision,
        controller_instance_sha256="mechanics-instance",
        observation_sha256="current-decision",
    )
    _, redundant_consumption = consume_recall_once(
        redundant_decision,
        controller_instance_sha256="redundant-instance",
        observation_sha256="current-decision",
    )
    stratum = RecallExperimentStratum(
        scope=_scope(),
        restored_prefix_sha256="prefix",
        restored_observation_sha256="current-decision",
        action_budget=5,
        primitive_action_cost=5.0,
        randomization_seed_sha256="seed",
    )
    mechanics_outcome = DecisionInterventionArmOutcome(
        stratum_sha256=stratum.sha256,
        proposal_revision_sha256=(
            mechanics.intervention_revision_sha256
        ),
        arm_id="mechanics-arm",
        controller_instance_sha256="mechanics-instance",
        runtime_controller_instance_ref="mechanics-runtime",
        trajectory_sha256="mechanics-trajectory",
        external_outcome_ref="mechanics-outcome",
        primitive_action_cost=5.0,
        task_score=1.0,
        efficiency_score=0.5,
        information_yield=0.4,
        consumption_receipt_sha256=mechanics_consumption.sha256,
    )
    redundant_outcome = DecisionInterventionArmOutcome(
        stratum_sha256=stratum.sha256,
        proposal_revision_sha256=(
            redundant.intervention_revision_sha256
        ),
        arm_id="redundant-arm",
        controller_instance_sha256="redundant-instance",
        runtime_controller_instance_ref="redundant-runtime",
        trajectory_sha256="redundant-trajectory",
        external_outcome_ref="redundant-outcome",
        primitive_action_cost=5.0,
        task_score=0.0,
        efficiency_score=0.0,
        information_yield=0.4,
        consumption_receipt_sha256=redundant_consumption.sha256,
    )

    next_state, receipt = settle_pairwise_intervention_trial(
        state,
        stratum=stratum,
        left_proposal=mechanics,
        right_proposal=redundant,
        left_recall=mechanics_recall,
        right_recall=redundant_recall,
        left_decision=mechanics_decision,
        right_decision=redundant_decision,
        left_consumption=mechanics_consumption,
        right_consumption=redundant_consumption,
        left_outcome=mechanics_outcome,
        right_outcome=redundant_outcome,
    )

    assert receipt.status == "settled"
    assert receipt.observed_decision_delta == 0.9
    assert (
        next_state.credit_for(mechanics_candidate).mean_observed_delta
        == 0.9
    )
    assert (
        next_state.credit_for(redundant_candidate).mean_observed_delta
        == -0.9
    )
