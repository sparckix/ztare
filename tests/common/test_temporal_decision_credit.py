from __future__ import annotations

import json

import pytest

from ztare.common.continual_skill_memory import (
    MEMORY_SCHEMA,
    decision_option_family_sha256,
    empty_continual_skill_memory,
    judge_combined_decision_option_task_credit,
    judge_decision_option_task_credit,
    load_continual_skill_memory,
    record_task_decision_experience,
    record_temporal_decision_chain,
    save_continual_skill_memory,
)
from ztare.common.guarded_experiment_protocol import (
    GuardedExperimentProtocol,
    GuardedProtocolCandidate,
    ProtocolCost,
    ProtocolResponseHypothesis,
    ProtocolYieldWeights,
    select_guarded_protocol,
)
from ztare.common.temporal_decision_credit import (
    DecisionChoiceAuthority,
    DecisionEligibilityChain,
    DecisionEligibilityEdge,
    compile_decision_yield_calibration,
    compile_temporal_decision_credit,
    settle_matched_temporal_pair,
    task_values_for_authority,
)


ADVANCE = "advance-family"
DETOUR = "detour-family"
FINISH = "finish-family"
WAIT = "wait-family"
MEASURE = "heldout-version-space-reduction-v1"


def _source_authority(
    *,
    continuation: str = "controller-v1",
    available: tuple[str, ...] = (ADVANCE, DETOUR),
) -> DecisionChoiceAuthority:
    return DecisionChoiceAuthority(
        task_contract_sha256="external-task",
        decision_namespace="anonymous-protocol-choice",
        choice_context_sha256="shared-source-state",
        continuation_context_sha256=continuation,
        available_option_family_sha256s=available,
    )


def _later_authority(
    context: str,
    *,
    continuation: str = "controller-v1",
) -> DecisionChoiceAuthority:
    return DecisionChoiceAuthority(
        task_contract_sha256="external-task",
        decision_namespace="anonymous-protocol-choice",
        choice_context_sha256=context,
        continuation_context_sha256=continuation,
        available_option_family_sha256s=(FINISH, WAIT),
    )


def _chain(
    pair: int,
    *,
    first_option: str,
    terminal: str,
    observed_yield: float,
    predicted_yield: float,
    continuation: str = "controller-v1",
    available: tuple[str, ...] = (ADVANCE, DETOUR),
    extra_edges: int = 0,
) -> DecisionEligibilityChain:
    arm = first_option.split("-", 1)[0]
    chain_ref = f"pair-{pair}:{arm}"
    successor = f"pair-{pair}:{arm}:state-1"
    first = DecisionEligibilityEdge(
        chain_ref=chain_ref,
        edge_index=0,
        authority=_source_authority(
            continuation=continuation,
            available=available,
        ),
        chosen_option_family_sha256=first_option,
        chosen_option_variant_sha256=first_option + "-variant",
        successor_decision_state_sha256=successor,
        predicted_information_yield=predicted_yield,
        observed_information_yield=observed_yield,
        information_yield_measure_sha256=MEASURE,
        primitive_action_cost=1.0,
        immediate_task_status="open",
        evidence_ref=f"edge:{chain_ref}:0",
    )
    edges = [first]
    current = successor
    for index in range(1, 2 + extra_edges):
        next_state = f"pair-{pair}:{arm}:state-{index + 1}"
        edges.append(DecisionEligibilityEdge(
            chain_ref=chain_ref,
            edge_index=index,
            authority=_later_authority(
                current,
                continuation=continuation,
            ),
            chosen_option_family_sha256=(
                FINISH if terminal == "attained" else WAIT
            ),
            chosen_option_variant_sha256=f"terminal-{terminal}",
            successor_decision_state_sha256=next_state,
            predicted_information_yield=0.2,
            observed_information_yield=0.2,
            information_yield_measure_sha256=MEASURE,
            primitive_action_cost=1.0,
            immediate_task_status=(
                terminal if index == 1 + extra_edges else "open"
            ),
            evidence_ref=f"edge:{chain_ref}:{index}",
        ))
        current = next_state
    return DecisionEligibilityChain(
        chain_ref=chain_ref,
        matched_pair_ref=f"pair-{pair}",
        arm_id=f"arm-{arm}",
        continuation_policy_sha256="shared-downstream-policy",
        edges=tuple(edges),
        terminal_task_status=terminal,
        terminal_adjudication_ref=f"adjudication:{chain_ref}:{terminal}",
    )


def _candidate(
    protocol_id: str,
    *,
    preparation: tuple[str, ...],
    responses: tuple[str, ...],
) -> GuardedProtocolCandidate:
    return GuardedProtocolCandidate(
        protocol=GuardedExperimentProtocol(
            protocol_id=protocol_id,
            preparation=preparation,
            probe="probe",
            target_key=protocol_id + "-target",
            cost=ProtocolCost(
                preparation_execution_units=len(preparation),
                probe_execution_units=1,
                control_units=1,
            ),
            novel_context=True,
        ),
        committee=tuple(
            ProtocolResponseHypothesis(
                hypothesis_id=f"h{index}",
                response=response,
            )
            for index, response in enumerate(responses)
        ),
    )


def _persistent_chain(
    pair: int,
    *,
    namespace: str,
    first_protocol: str,
    terminal: str,
    observed_yield: float,
    predicted_yield: float,
    continuation: str = "persistent-controller-v1",
    available_protocols: tuple[str, ...] = ("advance", "detour"),
) -> DecisionEligibilityChain:
    families = {
        protocol_id: decision_option_family_sha256(
            namespace,
            protocol_id,
        )
        for protocol_id in available_protocols
    }
    first_family = families[first_protocol]
    chain_ref = f"persistent-pair-{pair}:{first_protocol}"
    successor = f"{chain_ref}:successor"
    authority = DecisionChoiceAuthority(
        task_contract_sha256="persistent-external-task",
        decision_namespace=namespace,
        choice_context_sha256="persistent-shared-source",
        continuation_context_sha256=continuation,
        available_option_family_sha256s=tuple(families.values()),
    )
    later = DecisionChoiceAuthority(
        task_contract_sha256="persistent-external-task",
        decision_namespace=namespace,
        choice_context_sha256=successor,
        continuation_context_sha256=continuation,
        available_option_family_sha256s=("finish", "wait"),
    )
    return DecisionEligibilityChain(
        chain_ref=chain_ref,
        matched_pair_ref=f"persistent-pair-{pair}",
        arm_id=first_protocol,
        continuation_policy_sha256="persistent-policy",
        edges=(
            DecisionEligibilityEdge(
                chain_ref=chain_ref,
                edge_index=0,
                authority=authority,
                chosen_option_family_sha256=first_family,
                chosen_option_variant_sha256=(
                    first_protocol + "-variant"
                ),
                successor_decision_state_sha256=successor,
                predicted_information_yield=predicted_yield,
                observed_information_yield=observed_yield,
                information_yield_measure_sha256=MEASURE,
                primitive_action_cost=1.0,
                immediate_task_status="open",
                evidence_ref=f"edge:{chain_ref}:0",
            ),
            DecisionEligibilityEdge(
                chain_ref=chain_ref,
                edge_index=1,
                authority=later,
                chosen_option_family_sha256=(
                    "finish" if terminal == "attained" else "wait"
                ),
                chosen_option_variant_sha256=terminal + "-variant",
                successor_decision_state_sha256=f"{chain_ref}:terminal",
                predicted_information_yield=0.2,
                observed_information_yield=0.2,
                information_yield_measure_sha256=MEASURE,
                primitive_action_cost=1.0,
                immediate_task_status=terminal,
                evidence_ref=f"edge:{chain_ref}:1",
            ),
        ),
        terminal_task_status=terminal,
        terminal_adjudication_ref=f"adjudication:{chain_ref}:{terminal}",
    )


def test_matched_delayed_credit_changes_selection_without_cost_drift():
    pairs = tuple(
        (
            _chain(
                pair,
                first_option=ADVANCE,
                terminal="attained",
                predicted_yield=0.8,
                observed_yield=observed,
            ),
            _chain(
                pair,
                first_option=DETOUR,
                terminal="open",
                predicted_yield=1.2,
                observed_yield=0.15 - 0.05 * (pair - 1),
            ),
        )
        for pair, observed in ((1, 0.4), (2, 0.6))
    )
    compilation = compile_temporal_decision_credit(
        pairs,
        minimum_support=2,
        max_eligibility_delay_steps=1,
    )
    judgments = {
        row.option_family_sha256: row
        for row in compilation.judgments
    }

    assert all(
        pair[0].edges[0].immediate_task_status == "open"
        and pair[1].edges[0].immediate_task_status == "open"
        for pair in pairs
    )
    assert judgments[ADVANCE].status == "task_credited"
    assert judgments[ADVANCE].enable_support == 2
    assert judgments[ADVANCE].preference == 1
    assert judgments[DETOUR].status == "task_hazard"
    assert judgments[DETOUR].hazard_support == 2
    assert judgments[DETOUR].preference == -1

    advance = _candidate(
        ADVANCE,
        preparation=("a", "b"),
        responses=("x", "x", "y"),
    )
    detour = _candidate(
        DETOUR,
        preparation=("d",),
        responses=("x", "y", "z"),
    )
    weights = ProtocolYieldWeights(1.0, 1.0, 1.0)
    baseline = select_guarded_protocol(
        (advance, detour),
        weights=weights,
    )
    assert baseline.selected_protocol_id == DETOUR
    task_values = task_values_for_authority(
        compilation,
        _source_authority(),
    )
    calibrated = select_guarded_protocol(
        (advance, detour),
        weights=weights,
        task_value_by_protocol_id=task_values,
    )
    assert calibrated.selected_protocol_id == ADVANCE
    assert {
        row.protocol_id: row.cost.to_receipt()
        for row in baseline.prices
    } == {
        row.protocol_id: row.cost.to_receipt()
        for row in calibrated.prices
    }


def test_information_yield_is_calibrated_separately_from_task_credit():
    chains = tuple(
        chain
        for pair, observed in ((1, 0.4), (2, 0.6))
        for chain in (
            _chain(
                pair,
                first_option=ADVANCE,
                terminal="open",
                predicted_yield=0.8,
                observed_yield=observed,
            ),
            _chain(
                pair,
                first_option=DETOUR,
                terminal="open",
                predicted_yield=1.2,
                observed_yield=0.15 - 0.05 * (pair - 1),
            ),
        )
    )
    compilation = compile_temporal_decision_credit(
        ((chains[0], chains[1]), (chains[2], chains[3])),
        minimum_support=2,
        max_eligibility_delay_steps=1,
    )
    assert compilation.judgments == ()
    assert all(
        row.status == "uninformative"
        for row in compilation.pair_receipts
    )

    calibration = compile_decision_yield_calibration(chains)
    first_edge_rows = {
        row.option_family_sha256: row
        for row in calibration
        if row.authority.choice_context_sha256 == "shared-source-state"
    }
    advance = first_edge_rows[ADVANCE]
    detour = first_edge_rows[DETOUR]
    assert advance.status == "calibrated"
    assert advance.observation_count == 2
    assert advance.mean_predicted_yield == pytest.approx(0.8)
    assert advance.mean_observed_yield == pytest.approx(0.5)
    assert advance.mean_error == pytest.approx(-0.3)
    assert advance.mean_absolute_error == pytest.approx(0.3)
    assert detour.mean_predicted_yield == pytest.approx(1.2)
    assert detour.mean_observed_yield == pytest.approx(0.125)
    assert detour.to_receipt()["task_credit_authorized"] is False


def test_persistent_temporal_judgment_migrates_and_reranks_exact_scope(
    tmp_path,
):
    namespace = "persistent-protocol-choice"
    families = {
        protocol_id: decision_option_family_sha256(
            namespace,
            protocol_id,
        )
        for protocol_id in ("advance", "detour")
    }
    available = tuple(sorted(families.values()))
    immediate_scope = {
        "task_contract_sha256": "persistent-external-task",
        "decision_namespace": namespace,
        "choice_context_sha256": "persistent-shared-source",
        "continuation_context_sha256": "persistent-controller-v1",
        "available_option_family_sha256s": available,
    }
    legacy_memory = empty_continual_skill_memory()
    for trace_ref, protocol_id in (
        ("legacy-open-advance", "advance"),
        ("legacy-open-detour", "detour"),
    ):
        legacy_memory = record_task_decision_experience(
            legacy_memory,
            **immediate_scope,
            trace_ref=trace_ref,
            choice_index=0,
            outcome="open",
            chosen_option_family_sha256=families[protocol_id],
            chosen_option_variant_sha256=protocol_id + "-legacy",
            evidence_ref="legacy:" + trace_ref,
        )
    legacy_payload = legacy_memory.to_dict()
    legacy_payload["schema"] = "ztare-continual-skill-memory-v1"
    legacy_payload.pop("temporal_decision_chains")
    legacy_payload.pop("decision_yield_calibrations")
    memory_path = tmp_path / "continual-skill-memory.json"
    memory_path.write_text(
        json.dumps(legacy_payload),
        encoding="utf-8",
    )
    migrated = load_continual_skill_memory(memory_path)
    assert migrated.schema == MEMORY_SCHEMA
    assert migrated.temporal_decision_chains == ()
    assert all(
        judge_decision_option_task_credit(
            migrated,
            **immediate_scope,
            option_family_sha256=family,
        ).preference == 0
        for family in available
    )

    chains = tuple(
        chain
        for pair, advance_observed, detour_observed in (
            (1, 0.4, 0.15),
            (2, 0.6, 0.10),
        )
        for chain in (
            _persistent_chain(
                pair,
                namespace=namespace,
                first_protocol="advance",
                terminal="attained",
                predicted_yield=0.8,
                observed_yield=advance_observed,
            ),
            _persistent_chain(
                pair,
                namespace=namespace,
                first_protocol="detour",
                terminal="open",
                predicted_yield=1.2,
                observed_yield=detour_observed,
            ),
        )
    )
    memory = migrated
    for chain in chains:
        memory = record_temporal_decision_chain(memory, chain)
    calibration_before = tuple(
        row.to_receipt()
        for row in memory.decision_yield_calibrations
    )
    chain_hashes_before = tuple(
        chain.sha256 for chain in memory.temporal_decision_chains
    )
    save_continual_skill_memory(memory_path, memory)
    restored = load_continual_skill_memory(memory_path)
    assert tuple(
        chain.sha256 for chain in restored.temporal_decision_chains
    ) == chain_hashes_before
    assert tuple(
        row.to_receipt()
        for row in restored.decision_yield_calibrations
    ) == calibration_before
    assert all(
        not row["task_credit_authorized"]
        for row in calibration_before
    )

    judgments = {
        protocol_id: judge_combined_decision_option_task_credit(
            restored,
            **immediate_scope,
            option_family_sha256=family,
            minimum_temporal_support=2,
            max_eligibility_delay_steps=1,
        )
        for protocol_id, family in families.items()
    }
    assert judgments["advance"].immediate_preference == 0
    assert judgments["advance"].temporal_preference == 1
    assert judgments["advance"].preference == 1
    assert judgments["detour"].immediate_preference == 0
    assert judgments["detour"].temporal_preference == -1
    assert judgments["detour"].preference == -1

    candidates = (
        _candidate(
            "advance",
            preparation=("a", "b"),
            responses=("x", "x", "y"),
        ),
        _candidate(
            "detour",
            preparation=("d",),
            responses=("x", "y", "z"),
        ),
    )
    weights = ProtocolYieldWeights(1.0, 1.0, 1.0)
    baseline = select_guarded_protocol(candidates, weights=weights)
    reranked = select_guarded_protocol(
        candidates,
        weights=weights,
        task_value_by_protocol_id={
            protocol_id: judgment.preference
            for protocol_id, judgment in judgments.items()
        },
    )
    assert baseline.selected_protocol_id == "detour"
    assert reranked.selected_protocol_id == "advance"
    assert {
        row.protocol_id: row.cost.to_receipt()
        for row in baseline.prices
    } == {
        row.protocol_id: row.cost.to_receipt()
        for row in reranked.prices
    }

    mismatched = {
        protocol_id: judge_combined_decision_option_task_credit(
            restored,
            **{
                **immediate_scope,
                "continuation_context_sha256": "different-controller",
            },
            option_family_sha256=family,
        ).preference
        for protocol_id, family in families.items()
    }
    assert mismatched == {"advance": 0, "detour": 0}
    expanded_available = tuple(sorted((*available, "third-family")))
    choice_set_mismatched = {
        protocol_id: judge_combined_decision_option_task_credit(
            restored,
            **{
                **immediate_scope,
                "available_option_family_sha256s": expanded_available,
            },
            option_family_sha256=family,
        ).preference
        for protocol_id, family in families.items()
    }
    assert choice_set_mismatched == {"advance": 0, "detour": 0}
    mismatch_selection = select_guarded_protocol(
        candidates,
        weights=weights,
        task_value_by_protocol_id=mismatched,
    )
    assert mismatch_selection.selected_protocol_id == "detour"

    conflicting = restored
    for trace_ref, protocol_id, outcome in (
        ("immediate-positive-detour", "detour", "attained"),
        ("immediate-contrast-advance", "advance", "open"),
    ):
        conflicting = record_task_decision_experience(
            conflicting,
            **immediate_scope,
            trace_ref=trace_ref,
            choice_index=0,
            outcome=outcome,
            chosen_option_family_sha256=families[protocol_id],
            chosen_option_variant_sha256=protocol_id + "-conflict",
            evidence_ref="conflict:" + trace_ref,
        )
    for protocol_id, family in families.items():
        judgment = judge_combined_decision_option_task_credit(
            conflicting,
            **immediate_scope,
            option_family_sha256=family,
            max_eligibility_delay_steps=1,
        )
        assert judgment.status == "credit_conflict"
        assert judgment.preference == 0


def test_persisted_yield_calibration_drift_is_rejected(tmp_path):
    namespace = "persistent-protocol-choice"
    memory = empty_continual_skill_memory()
    memory = record_temporal_decision_chain(
        memory,
        _persistent_chain(
            1,
            namespace=namespace,
            first_protocol="advance",
            terminal="attained",
            predicted_yield=0.8,
            observed_yield=0.4,
        ),
    )
    path = tmp_path / "tampered-memory.json"
    save_continual_skill_memory(path, memory)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["decision_yield_calibrations"][0]["mean_error"] = 9.0
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(
        ValueError,
        match="decision yield calibration receipt drifted",
    ):
        load_continual_skill_memory(path)


def test_authority_and_eligibility_boundaries_fail_closed():
    attained = _chain(
        1,
        first_option=ADVANCE,
        terminal="attained",
        predicted_yield=0.8,
        observed_yield=0.4,
    )
    wrong_controller = _chain(
        1,
        first_option=DETOUR,
        terminal="open",
        predicted_yield=1.2,
        observed_yield=0.1,
        continuation="controller-v2",
    )
    assert settle_matched_temporal_pair(
        attained,
        wrong_controller,
        max_eligibility_delay_steps=1,
    ).reason == "first_choice_authority_mismatch"

    wrong_choice_set = _chain(
        1,
        first_option=DETOUR,
        terminal="open",
        predicted_yield=1.2,
        observed_yield=0.1,
        available=(ADVANCE, DETOUR, "third-family"),
    )
    assert settle_matched_temporal_pair(
        attained,
        wrong_choice_set,
        max_eligibility_delay_steps=1,
    ).reason == "first_choice_authority_mismatch"

    expired_advance = _chain(
        2,
        first_option=ADVANCE,
        terminal="attained",
        predicted_yield=0.8,
        observed_yield=0.4,
        extra_edges=2,
    )
    expired_detour = _chain(
        2,
        first_option=DETOUR,
        terminal="open",
        predicted_yield=1.2,
        observed_yield=0.1,
        extra_edges=2,
    )
    assert settle_matched_temporal_pair(
        expired_advance,
        expired_detour,
        max_eligibility_delay_steps=1,
    ).reason == "eligibility_trace_expired"
