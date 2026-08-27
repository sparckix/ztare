from __future__ import annotations

from dataclasses import replace

import pytest

from ztare.common.continual_skill_memory import (
    compile_persisted_temporal_decision_credit,
    empty_continual_skill_memory,
    judge_combined_decision_option_task_credit,
    record_temporal_decision_chain,
)
from ztare.common.temporal_decision_credit import (
    DecisionChoiceAuthority,
    compile_decision_yield_calibration,
    settle_matched_temporal_pair,
)
from ztare.common.two_stage_eligibility_ledger import (
    DecisionEpisodeUtilityAdjudication,
    DecisionEpisodeDraft,
    DecisionWindowEvidence,
    SealedDecisionReplayContract,
    SealedDecisionReplayAssignment,
    SealedDecisionUtilityContract,
    bind_episode_draft,
    materialize_episode_utility_arm,
    total_primitive_cost,
)
from ztare.common.temporal_decision_utility import (
    ExternalUtilityMeasure,
    settle_matched_temporal_utility_pair,
)


TASK = "external-task"
NAMESPACE = "protocol-choice"
SOURCE = "shared-source"
CONTROLLER = "controller-v1"
POLICY = "policy-v1"
ENVIRONMENT = "environment-source"
PREFIX = "frozen-replay-prefix"
MEASURE = "posterior-reduction-v1"
ADVANCE = "advance-family"
DETOUR = "detour-family"


def _first_authority(
    *,
    task: str = TASK,
    source: str = SOURCE,
    controller: str = CONTROLLER,
    available: tuple[str, ...] = (ADVANCE, DETOUR),
) -> DecisionChoiceAuthority:
    return DecisionChoiceAuthority(
        task_contract_sha256=task,
        decision_namespace=NAMESPACE,
        choice_context_sha256=source,
        continuation_context_sha256=controller,
        available_option_family_sha256s=available,
    )


def _draft(
    episode: str,
    *,
    first_option: str,
    terminal: str,
    authority: DecisionChoiceAuthority | None = None,
    environment: str = ENVIRONMENT,
    prefix: str = PREFIX,
    policy: str = POLICY,
    measure: str = MEASURE,
    extra_windows: int = 0,
) -> DecisionEpisodeDraft:
    first_authority = authority or _first_authority()
    first_successor = f"{episode}:state-1"
    windows = [DecisionWindowEvidence(
        authority=first_authority,
        chosen_option_family_sha256=first_option,
        chosen_option_variant_sha256=first_option + "-variant",
        successor_decision_state_sha256=first_successor,
        predicted_information_yield=(
            0.8 if first_option == ADVANCE else 1.2
        ),
        observed_information_yield=(
            0.5 if first_option == ADVANCE else 0.1
        ),
        information_yield_measure_sha256=measure,
        primitive_action_cost=1.0,
        immediate_task_status="open",
        decision_evidence_ref=f"decision:{episode}:0",
        observed_yield_evidence_ref=f"yield:{episode}:0",
    )]
    current = first_successor
    for index in range(1, 2 + extra_windows):
        next_state = f"{episode}:state-{index + 1}"
        later_authority = DecisionChoiceAuthority(
            task_contract_sha256=first_authority.task_contract_sha256,
            decision_namespace=first_authority.decision_namespace,
            choice_context_sha256=current,
            continuation_context_sha256=(
                first_authority.continuation_context_sha256
            ),
            available_option_family_sha256s=("finish", "wait"),
        )
        is_last = index == 1 + extra_windows
        immediate = terminal if is_last else "open"
        windows.append(DecisionWindowEvidence(
            authority=later_authority,
            chosen_option_family_sha256=(
                "finish" if terminal == "attained" else "wait"
            ),
            chosen_option_variant_sha256=f"{terminal}:{index}",
            successor_decision_state_sha256=next_state,
            predicted_information_yield=0.2,
            observed_information_yield=0.2,
            information_yield_measure_sha256=measure,
            primitive_action_cost=1.0,
            immediate_task_status=immediate,
            decision_evidence_ref=f"decision:{episode}:{index}",
            observed_yield_evidence_ref=f"yield:{episode}:{index}",
        ))
        current = next_state
    return DecisionEpisodeDraft(
        episode_ref=episode,
        environment_source_sha256=environment,
        replay_prefix_sha256=prefix,
        continuation_policy_sha256=policy,
        windows=tuple(windows),
        terminal_task_status=terminal,
        terminal_adjudication_ref=(
            f"terminal:{episode}:{terminal}"
        ),
    )


def _contract(pair: int, *, max_delay: int = 1):
    return SealedDecisionReplayContract(
        contract_ref=f"replay-contract-{pair}",
        first_authority=_first_authority(),
        continuation_policy_sha256=POLICY,
        environment_source_sha256=ENVIRONMENT,
        replay_prefix_sha256=PREFIX,
        information_yield_measure_sha256=MEASURE,
        arm_option_family_sha256s=(
            ("advance-arm", ADVANCE),
            ("detour-arm", DETOUR),
        ),
        max_eligibility_delay_steps=max_delay,
    )


def test_two_stage_replay_binding_grants_no_collection_time_credit():
    memory = empty_continual_skill_memory()
    assert memory.temporal_decision_chains == ()
    drafts = []
    chains = []
    pairs = []
    for pair in (1, 2):
        contract = _contract(pair)
        advance = _draft(
            f"pair-{pair}:advance",
            first_option=ADVANCE,
            terminal="attained",
        )
        detour = _draft(
            f"pair-{pair}:detour",
            first_option=DETOUR,
            terminal="open",
        )
        drafts.extend((advance, detour))
        assert not advance.to_receipt()["task_credit_authorized"]
        assert not detour.to_receipt()["task_credit_authorized"]

        advance_chain = bind_episode_draft(
            advance,
            contract,
            arm_id="advance-arm",
        )
        detour_chain = bind_episode_draft(
            detour,
            contract,
            arm_id="detour-arm",
        )
        chains.extend((advance_chain, detour_chain))
        pairs.append((advance_chain, detour_chain))
        memory = record_temporal_decision_chain(memory, advance_chain)
        memory = record_temporal_decision_chain(memory, detour_chain)

    compilation = compile_persisted_temporal_decision_credit(
        memory,
        minimum_support=2,
        max_eligibility_delay_steps=1,
    )
    by_option = {
        row.option_family_sha256: row
        for row in compilation.judgments
    }
    assert by_option[ADVANCE].preference == 1
    assert by_option[DETOUR].preference == -1
    assert total_primitive_cost(drafts) == total_primitive_cost(chains)
    calibration = compile_decision_yield_calibration(chains)
    assert calibration
    assert all(
        not row.to_receipt()["task_credit_authorized"]
        for row in calibration
    )

    authority = _first_authority()
    common = {
        "memory": memory,
        "decision_namespace": authority.decision_namespace,
        "task_contract_sha256": authority.task_contract_sha256,
        "choice_context_sha256": authority.choice_context_sha256,
        "continuation_context_sha256": (
            authority.continuation_context_sha256
        ),
        "available_option_family_sha256s": (
            authority.available_option_family_sha256s
        ),
    }
    assert judge_combined_decision_option_task_credit(
        **common,
        option_family_sha256=ADVANCE,
    ).preference == 1
    assert judge_combined_decision_option_task_credit(
        **common,
        option_family_sha256=DETOUR,
    ).preference == -1


@pytest.mark.parametrize(
    ("mutation", "arm_id", "message"),
    (
        (
            lambda draft: _draft(
                "wrong-task",
                first_option=ADVANCE,
                terminal="attained",
                authority=_first_authority(task="different-task"),
            ),
            "advance-arm",
            "first-choice authority mismatch",
        ),
        (
            lambda draft: _draft(
                "wrong-source",
                first_option=ADVANCE,
                terminal="attained",
                authority=_first_authority(source="different-source"),
            ),
            "advance-arm",
            "first-choice authority mismatch",
        ),
        (
            lambda draft: _draft(
                "wrong-controller",
                first_option=ADVANCE,
                terminal="attained",
                authority=_first_authority(controller="different-controller"),
            ),
            "advance-arm",
            "first-choice authority mismatch",
        ),
        (
            lambda draft: _draft(
                "wrong-choice-set",
                first_option=ADVANCE,
                terminal="attained",
                authority=_first_authority(
                    available=(ADVANCE, DETOUR, "third-family"),
                ),
            ),
            "advance-arm",
            "first-choice authority mismatch",
        ),
        (
            lambda draft: replace(
                draft,
                environment_source_sha256="different-environment",
            ),
            "advance-arm",
            "environment source mismatch",
        ),
        (
            lambda draft: replace(
                draft,
                replay_prefix_sha256="different-prefix",
            ),
            "advance-arm",
            "replay prefix mismatch",
        ),
        (
            lambda draft: replace(
                draft,
                continuation_policy_sha256="different-policy",
            ),
            "advance-arm",
            "continuation policy mismatch",
        ),
        (
            lambda draft: _draft(
                "wrong-measure",
                first_option=ADVANCE,
                terminal="attained",
                measure="different-measure",
            ),
            "advance-arm",
            "information-yield measure mismatch",
        ),
        (
            lambda draft: draft,
            "detour-arm",
            "first option does not match replay arm",
        ),
        (
            lambda draft: draft,
            "undeclared-arm",
            "undeclared replay arm",
        ),
    ),
)
def test_replay_binding_refuses_authority_or_source_edits(
    mutation,
    arm_id,
    message,
):
    draft = _draft(
        "baseline",
        first_option=ADVANCE,
        terminal="attained",
    )
    with pytest.raises(ValueError, match=message):
        bind_episode_draft(
            mutation(draft),
            _contract(1),
            arm_id=arm_id,
        )


def test_replay_binding_refuses_expired_or_unmeasured_episode():
    expired = _draft(
        "expired",
        first_option=ADVANCE,
        terminal="attained",
        extra_windows=2,
    )
    with pytest.raises(ValueError, match="eligibility trace expired"):
        bind_episode_draft(
            expired,
            _contract(1, max_delay=1),
            arm_id="advance-arm",
        )

    with pytest.raises(
        ValueError,
        match="observed_yield_evidence_ref must be nonempty",
    ):
        DecisionWindowEvidence(
            authority=_first_authority(),
            chosen_option_family_sha256=ADVANCE,
            chosen_option_variant_sha256="advance-variant",
            successor_decision_state_sha256="next",
            predicted_information_yield=0.8,
            observed_information_yield=0.5,
            information_yield_measure_sha256=MEASURE,
            primitive_action_cost=1.0,
            immediate_task_status="open",
            decision_evidence_ref="decision",
            observed_yield_evidence_ref="",
        )


def test_equal_outcomes_do_not_create_credit_after_sealed_binding():
    contract = _contract(1)
    left = bind_episode_draft(
        _draft(
            "open-advance",
            first_option=ADVANCE,
            terminal="open",
        ),
        contract,
        arm_id="advance-arm",
    )
    right = bind_episode_draft(
        _draft(
            "open-detour",
            first_option=DETOUR,
            terminal="open",
        ),
        contract,
        arm_id="detour-arm",
    )
    receipt = settle_matched_temporal_pair(
        left,
        right,
        max_eligibility_delay_steps=1,
    )
    assert receipt.status == "uninformative"
    assert receipt.enabling_option_family_sha256 == ""
    assert receipt.hazardous_option_family_sha256 == ""


def _utility_measure() -> ExternalUtilityMeasure:
    return ExternalUtilityMeasure(
        task_contract_sha256=TASK,
        measure_id="prospective-task-efficiency-v1",
        component_weights=(("efficiency", 0.25), ("task", 0.75)),
    )


def _assignment(
    contract: SealedDecisionReplayContract,
    arm_id: str,
) -> SealedDecisionReplayAssignment:
    return SealedDecisionReplayAssignment(
        assignment_ref=f"{contract.contract_ref}:{arm_id}",
        contract=contract,
        arm_id=arm_id,
        randomization_evidence_ref=f"randomization:{arm_id}",
    )


def _utility_contract(
    contract: SealedDecisionReplayContract,
) -> SealedDecisionUtilityContract:
    return SealedDecisionUtilityContract(
        contract_ref=f"utility:{contract.contract_ref}",
        replay_contract=contract,
        utility_measure=_utility_measure(),
        external_adjudicator_id="task-adjudicator-v1",
    )


def _adjudication(
    draft: DecisionEpisodeDraft,
    assignment: SealedDecisionReplayAssignment,
    utility_contract: SealedDecisionUtilityContract,
    *,
    task: float,
    efficiency: float,
) -> DecisionEpisodeUtilityAdjudication:
    return DecisionEpisodeUtilityAdjudication(
        utility_contract_sha256=utility_contract.sha256,
        replay_assignment_sha256=assignment.sha256,
        episode_sha256=draft.sha256,
        external_adjudicator_id=(
            utility_contract.external_adjudicator_id
        ),
        component_values=(("task", task), ("efficiency", efficiency)),
        external_outcome_ref=f"outcome:{draft.episode_ref}",
    )


def test_prospective_assignment_and_episode_utility_bind_exactly() -> None:
    contract = _contract(7)
    assert (
        SealedDecisionReplayContract.from_receipt(contract.to_receipt())
        == contract
    )
    advance_assignment = _assignment(contract, "advance-arm")
    detour_assignment = _assignment(contract, "detour-arm")
    assert (
        SealedDecisionReplayAssignment.from_receipt(
            advance_assignment.to_receipt()
        )
        == advance_assignment
    )
    utility_contract = _utility_contract(contract)
    assert (
        SealedDecisionUtilityContract.from_receipt(
            utility_contract.to_receipt()
        )
        == utility_contract
    )
    advance_draft = _draft(
        "prospective-advance",
        first_option=ADVANCE,
        terminal="attained",
    )
    detour_draft = _draft(
        "prospective-detour",
        first_option=DETOUR,
        terminal="attained",
    )
    advance_adjudication = _adjudication(
        advance_draft,
        advance_assignment,
        utility_contract,
        task=1.0,
        efficiency=0.8,
    )
    assert (
        DecisionEpisodeUtilityAdjudication.from_receipt(
            advance_adjudication.to_receipt()
        )
        == advance_adjudication
    )
    advance = materialize_episode_utility_arm(
        advance_draft,
        advance_assignment,
        utility_contract,
        advance_adjudication,
    )
    detour = materialize_episode_utility_arm(
        detour_draft,
        detour_assignment,
        utility_contract,
        _adjudication(
            detour_draft,
            detour_assignment,
            utility_contract,
            task=1.0,
            efficiency=0.2,
        ),
    )

    assert advance.chosen_option_family_sha256 == ADVANCE
    assert detour.chosen_option_family_sha256 == DETOUR
    assert advance.chosen_option_variant_sha256 == "advance-family-variant"
    assert advance.primitive_action_cost == advance_draft.primitive_action_cost
    assert detour.primitive_action_cost == detour_draft.primitive_action_cost
    assert advance.external_value == pytest.approx(0.95)
    assert detour.external_value == pytest.approx(0.80)
    receipt = settle_matched_temporal_utility_pair(advance, detour)
    assert receipt.status == "settled"
    assert receipt.preferred_option_family_sha256 == ADVANCE
    assert receipt.external_value_delta == pytest.approx(0.15)


def test_episode_utility_refuses_assignment_episode_and_adjudicator_drift():
    contract = _contract(8)
    assignment = _assignment(contract, "advance-arm")
    utility_contract = _utility_contract(contract)
    draft = _draft(
        "prospective-exact",
        first_option=ADVANCE,
        terminal="attained",
    )
    adjudication = _adjudication(
        draft,
        assignment,
        utility_contract,
        task=1.0,
        efficiency=0.5,
    )
    cases = (
        (
            replace(adjudication, episode_sha256="different-episode"),
            "episode mismatch",
        ),
        (
            replace(
                adjudication,
                replay_assignment_sha256="different-assignment",
            ),
            "assignment mismatch",
        ),
        (
            replace(
                adjudication,
                utility_contract_sha256="different-contract",
            ),
            "contract mismatch",
        ),
        (
            replace(
                adjudication,
                external_adjudicator_id="different-adjudicator",
            ),
            "adjudicator identity mismatch",
        ),
    )
    for drifted, message in cases:
        with pytest.raises(ValueError, match=message):
            materialize_episode_utility_arm(
                draft,
                assignment,
                utility_contract,
                drifted,
            )

    with pytest.raises(ValueError, match="first option"):
        materialize_episode_utility_arm(
            draft,
            _assignment(contract, "detour-arm"),
            utility_contract,
            replace(
                adjudication,
                replay_assignment_sha256=(
                    _assignment(contract, "detour-arm").sha256
                ),
            ),
        )
