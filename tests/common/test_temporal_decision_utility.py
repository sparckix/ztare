from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from ztare.common.equivariance import stable_sha256
from ztare.common.continual_skill_memory import (
    MEMORY_SCHEMA,
    compile_persisted_temporal_decision_utility,
    empty_continual_skill_memory,
    judge_combined_decision_option_task_credit,
    load_continual_skill_memory,
    record_temporal_utility_arm,
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
    compile_temporal_decision_credit,
)
from ztare.common.temporal_decision_utility import (
    ExternalUtilityMeasure,
    TemporalDecisionUtilityArm,
    compile_temporal_decision_utility,
    settle_matched_temporal_utility_pair,
)


ROOT = Path(__file__).resolve().parents[2]
H95 = (
    ROOT
    / "research_areas/pre_registrations"
    / "arc3_consumer_indexed_exception_frontier_20260723"
    / "h95_response_transport_square/result.json"
)


def _measure(task: str = "task") -> ExternalUtilityMeasure:
    return ExternalUtilityMeasure(
        task_contract_sha256=task,
        measure_id="weighted-task-efficiency-v1",
        component_weights=(
            ("efficiency_score", 0.2),
            ("task_score", 0.8),
        ),
    )


def _authority(
    *,
    task: str = "task",
    context: str = "choice-context",
    controller: str = "controller",
) -> DecisionChoiceAuthority:
    return DecisionChoiceAuthority(
        task_contract_sha256=task,
        decision_namespace="protocol-choice",
        choice_context_sha256=context,
        continuation_context_sha256=controller,
        available_option_family_sha256s=("causal", "placebo"),
    )


def _arm(
    pair: int,
    arm: str,
    *,
    task_score: float,
    efficiency_score: float,
    authority: DecisionChoiceAuthority | None = None,
    measure: ExternalUtilityMeasure | None = None,
    cost: float = 20.0,
    continuation: str = "policy",
    evidence: str | None = None,
) -> TemporalDecisionUtilityArm:
    active_authority = authority or _authority()
    active_measure = measure or _measure(
        active_authority.task_contract_sha256
    )
    option = "causal" if arm == "offer" else "placebo"
    return TemporalDecisionUtilityArm(
        matched_pair_ref=f"pair-{pair}",
        arm_id=arm,
        authority=active_authority,
        chosen_option_family_sha256=option,
        chosen_option_variant_sha256=f"{option}-variant",
        continuation_policy_sha256=continuation,
        utility_measure=active_measure,
        component_values=(
            ("task_score", task_score),
            ("efficiency_score", efficiency_score),
        ),
        primitive_action_cost=cost,
        immediate_task_status="open",
        terminal_task_status=(
            "attained" if task_score > 0.0 else "open"
        ),
        external_value=(
            (0.8 * task_score) + (0.2 * efficiency_score)
        ),
        external_outcome_ref=evidence or f"evidence:{pair}:{arm}",
    )


def test_graded_utility_retains_equal_terminal_efficiency_contrast() -> None:
    pair_1 = (
        _arm(1, "offer", task_score=1.0, efficiency_score=0.45),
        _arm(1, "withhold", task_score=0.0, efficiency_score=0.0),
    )
    pair_2 = (
        _arm(2, "offer", task_score=1.0, efficiency_score=0.45),
        _arm(2, "withhold", task_score=1.0, efficiency_score=0.10),
    )
    compilation = compile_temporal_decision_utility(
        (pair_1, pair_2),
        minimum_support=2,
    )
    assert [row.status for row in compilation.pair_receipts] == [
        "settled",
        "settled",
    ]
    assert compilation.pair_receipts[0].external_value_delta == pytest.approx(
        0.89
    )
    assert compilation.pair_receipts[1].external_value_delta == pytest.approx(
        0.07
    )
    receipt = compilation.to_receipt()
    assert receipt["mean_settled_external_delta"] == pytest.approx(0.48)
    judgments = {
        row.option_family_sha256: row for row in compilation.judgments
    }
    assert judgments["causal"].status == "utility_preferred"
    assert judgments["causal"].preferred_support == 2
    assert judgments["causal"].preference == 1
    assert judgments["placebo"].status == "utility_hazard"
    assert judgments["placebo"].hazard_support == 2
    assert judgments["placebo"].preference == -1
    assert not receipt["terminal_task_credit_authorized"]
    assert not receipt["information_yield_authorized"]
    assert pair_1[0].primitive_action_cost == pair_1[1].primitive_action_cost
    assert pair_2[0].primitive_action_cost == pair_2[1].primitive_action_cost


def test_graded_utility_refuses_authority_measure_cost_and_identity_drift() -> None:
    left = _arm(1, "offer", task_score=1.0, efficiency_score=0.4)
    right = _arm(1, "withhold", task_score=0.0, efficiency_score=0.0)
    cases = (
        (
            replace(
                right,
                authority=_authority(context="different-context"),
            ),
            "decision_choice_authority_mismatch",
        ),
        (
            replace(right, continuation_policy_sha256="other-policy"),
            "continuation_policy_mismatch",
        ),
        (
            replace(
                right,
                utility_measure=ExternalUtilityMeasure(
                    task_contract_sha256="task",
                    measure_id="different-measure",
                    component_weights=(
                        ("efficiency_score", 0.2),
                        ("task_score", 0.8),
                    ),
                ),
            ),
            "external_utility_measure_mismatch",
        ),
        (
            replace(right, primitive_action_cost=19.0),
            "primitive_action_cost_mismatch",
        ),
        (
            replace(right, arm_id="offer"),
            "arm_identity_reused",
        ),
        (
            replace(
                right,
                chosen_option_family_sha256="causal",
            ),
            "option_family_not_contrasted",
        ),
        (
            replace(
                right,
                chosen_option_variant_sha256="causal-variant",
            ),
            "option_variant_identity_reused",
        ),
        (
            replace(
                right,
                external_outcome_ref=left.external_outcome_ref,
            ),
            "external_evidence_identity_reused",
        ),
    )
    for drifted, reason in cases:
        receipt = settle_matched_temporal_utility_pair(left, drifted)
        assert receipt.status == "refused"
        assert receipt.reason == reason

    with pytest.raises(
        ValueError,
        match="external value does not match",
    ):
        replace(left, external_value=0.0)
    with pytest.raises(ValueError, match="pair identity was reused"):
        compile_temporal_decision_utility(
            ((left, right), (left, right)),
            minimum_support=1,
        )


def test_external_utility_tie_stays_uninformative() -> None:
    left = _arm(1, "offer", task_score=1.0, efficiency_score=0.4)
    right = _arm(1, "withhold", task_score=1.0, efficiency_score=0.4)
    receipt = settle_matched_temporal_utility_pair(left, right)
    assert receipt.status == "uninformative"
    assert receipt.reason == "external_utility_tie"
    compilation = compile_temporal_decision_utility(
        ((left, right),),
        minimum_support=1,
    )
    assert not compilation.judgments


def _h95_utility_pairs():
    result = json.loads(H95.read_text(encoding="utf-8"))
    causal = result["intervention_revision_transport"]
    placebo = result["placebo_intervention_revision_transport"]
    causal_family = str(causal["payload_invariant_sha256"])
    placebo_family = str(placebo["payload_invariant_sha256"])
    continuation = stable_sha256({
        "schema": "ztare-h95-continuation-policy-v1",
        "controller_sha256": result["pairs"][0]["stratum"]["scope"][
            "controller_sha256"
        ],
        "model": "gpt-5.6-sol",
        "reasoning_effort": "xhigh",
        "post_prefix_action_budget": result["aggregate"][
            "post_prefix_primitive_action_cost_per_arm"
        ],
        "proposal_inferences_before_action": result["aggregate"][
            "proposal_inferences_before_post_prefix_action"
        ],
    })
    pairs = []
    binary_pairs = []
    for row in result["pairs"]:
        scope = row["stratum"]["scope"]
        authority = DecisionChoiceAuthority(
            task_contract_sha256=str(scope["task_sha256"]),
            decision_namespace="arc3-response-transport-square",
            choice_context_sha256=str(scope["context_sha256"]),
            continuation_context_sha256=continuation,
            available_option_family_sha256s=(
                causal_family,
                placebo_family,
            ),
        )
        measure = ExternalUtilityMeasure(
            task_contract_sha256=authority.task_contract_sha256,
            measure_id="h95-weighted-task-efficiency-v1",
            component_weights=(
                (
                    "efficiency_score",
                    float(row["stratum"]["efficiency_score_weight"]),
                ),
                (
                    "task_score",
                    float(row["stratum"]["task_score_weight"]),
                ),
            ),
        )
        pair_ref = "h95-pair:" + stable_sha256({
            "experiment_sha256": result["experiment_sha256"],
            "pair_index": row["pair_index"],
        })
        utility_arms = []
        binary_arms = []
        for arm_id, option_family, variant in (
            (
                "offer",
                causal_family,
                causal["target_intervention_revision_sha256"],
            ),
            (
                "withhold",
                placebo_family,
                placebo["target_intervention_revision_sha256"],
            ),
        ):
            metrics = row[f"{arm_id}_metrics"]
            outcome = row[f"{arm_id}_outcome"]
            terminal = (
                "attained"
                if float(metrics["task_score"]) > 0.0
                else "open"
            )
            utility_arms.append(TemporalDecisionUtilityArm(
                matched_pair_ref=pair_ref,
                arm_id=arm_id,
                authority=authority,
                chosen_option_family_sha256=option_family,
                chosen_option_variant_sha256=str(variant),
                continuation_policy_sha256=continuation,
                utility_measure=measure,
                component_values=(
                    ("task_score", float(metrics["task_score"])),
                    (
                        "efficiency_score",
                        float(metrics["efficiency_score"]),
                    ),
                ),
                primitive_action_cost=float(
                    outcome["primitive_action_cost"]
                ),
                immediate_task_status="open",
                terminal_task_status=terminal,
                external_value=float(outcome["net_external_value"]),
                external_outcome_ref=str(outcome["external_outcome_ref"]),
            ))
            chain_ref = f"{pair_ref}:{arm_id}"
            binary_arms.append(DecisionEligibilityChain(
                chain_ref=chain_ref,
                matched_pair_ref=pair_ref,
                arm_id=arm_id,
                continuation_policy_sha256=continuation,
                edges=(DecisionEligibilityEdge(
                    chain_ref=chain_ref,
                    edge_index=0,
                    authority=authority,
                    chosen_option_family_sha256=option_family,
                    chosen_option_variant_sha256=str(variant),
                    successor_decision_state_sha256=(
                        "terminal:" + stable_sha256({
                            "pair_ref": pair_ref,
                            "arm_id": arm_id,
                            "terminal": terminal,
                        })
                    ),
                    predicted_information_yield=float(
                        metrics["information_yield"]
                    ),
                    observed_information_yield=float(
                        metrics["information_yield"]
                    ),
                    information_yield_measure_sha256=stable_sha256(
                        metrics["information_yield_measure"]
                    ),
                    primitive_action_cost=float(
                        outcome["primitive_action_cost"]
                    ),
                    immediate_task_status="open",
                    evidence_ref=str(outcome["external_outcome_ref"]),
                ),),
                terminal_task_status=terminal,
                terminal_adjudication_ref=str(
                    outcome["external_outcome_ref"]
                ),
            ))
        pairs.append(tuple(utility_arms))
        binary_pairs.append(tuple(binary_arms))
    return result, tuple(pairs), tuple(binary_pairs)


def test_saved_h95_pairs_expose_graded_support_binary_discards() -> None:
    result, utility_pairs, binary_pairs = _h95_utility_pairs()
    utility = compile_temporal_decision_utility(
        utility_pairs,
        minimum_support=2,
    )
    binary = compile_temporal_decision_credit(
        binary_pairs,
        minimum_support=2,
        max_eligibility_delay_steps=0,
    )
    assert [
        row.external_value_delta for row in utility.pair_receipts
    ] == pytest.approx([0.89, 0.07])
    assert utility.to_receipt()["mean_settled_external_delta"] == (
        pytest.approx(
            result["aggregate"]["mean_offer_minus_withhold_composite"]
        )
    )
    assert {row.status for row in utility.judgments} == {
        "utility_preferred",
        "utility_hazard",
    }
    assert binary.to_receipt()["settled_pair_count"] == 1
    assert {row.status for row in binary.judgments} == {"undersampled"}

    h96_context = (
        "82e380095fe14a67f08a83d0fe7440877b83537d8ef72b6e58704c4d206175cf"
    )
    h96_like = replace(
        utility_pairs[0][1],
        authority=replace(
            utility_pairs[0][1].authority,
            choice_context_sha256=h96_context,
        ),
    )
    refused = settle_matched_temporal_utility_pair(
        utility_pairs[0][0],
        h96_like,
    )
    assert refused.status == "refused"
    assert refused.reason == "decision_choice_authority_mismatch"


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


def _opposing_task_pairs(
    authority: DecisionChoiceAuthority,
    continuation_policy_sha256: str,
    causal_family: str,
    placebo_family: str,
):
    pairs = []
    for pair_index in (1, 2):
        arms = []
        for arm_id, option, terminal in (
            ("causal", causal_family, "open"),
            ("placebo", placebo_family, "attained"),
        ):
            chain_ref = f"opposing:{pair_index}:{arm_id}"
            arms.append(DecisionEligibilityChain(
                chain_ref=chain_ref,
                matched_pair_ref=f"opposing:{pair_index}",
                arm_id=arm_id,
                continuation_policy_sha256=continuation_policy_sha256,
                edges=(DecisionEligibilityEdge(
                    chain_ref=chain_ref,
                    edge_index=0,
                    authority=authority,
                    chosen_option_family_sha256=option,
                    chosen_option_variant_sha256=f"{option}:opposing",
                    successor_decision_state_sha256=(
                        f"opposing-terminal:{pair_index}:{arm_id}"
                    ),
                    predicted_information_yield=0.5,
                    observed_information_yield=0.5,
                    information_yield_measure_sha256="opposing-measure",
                    primitive_action_cost=20.0,
                    immediate_task_status="open",
                    evidence_ref=f"opposing:{pair_index}:{arm_id}",
                ),),
                terminal_task_status=terminal,
                terminal_adjudication_ref=(
                    f"opposing-adjudication:{pair_index}:{arm_id}"
                ),
            ))
        pairs.append(tuple(arms))
    return tuple(pairs)


def test_h95_utility_persists_and_enters_conflict_neutral_selection(
    tmp_path,
) -> None:
    _result, utility_pairs, _binary_pairs = _h95_utility_pairs()
    legacy_payload = empty_continual_skill_memory().to_dict()
    legacy_payload["schema"] = "ztare-continual-skill-memory-v2"
    legacy_payload.pop("temporal_utility_arms")
    path = tmp_path / "continual-skill-memory.json"
    path.write_text(json.dumps(legacy_payload), encoding="utf-8")
    migrated = load_continual_skill_memory(path)
    assert migrated.schema == MEMORY_SCHEMA
    assert migrated.temporal_utility_arms == ()
    assert migrated.to_receipt()["temporal_utility_arm_count"] == 0

    memory = migrated
    for pair in utility_pairs:
        for arm in pair:
            memory = record_temporal_utility_arm(memory, arm)
    arm_receipts_before = tuple(
        arm.to_receipt() for arm in memory.temporal_utility_arms
    )
    save_continual_skill_memory(path, memory)
    restored = load_continual_skill_memory(path)
    assert tuple(
        arm.to_receipt() for arm in restored.temporal_utility_arms
    ) == arm_receipts_before
    assert "temporal_utility_judgments" not in restored.to_dict()
    compilation = compile_persisted_temporal_decision_utility(
        restored,
        minimum_support=2,
    )
    assert compilation.to_receipt()["settled_pair_count"] == 2
    assert compilation.to_receipt()[
        "mean_settled_external_delta"
    ] == pytest.approx(0.48)

    authority = utility_pairs[0][0].authority
    measure_sha = utility_pairs[0][0].utility_measure.sha256
    causal_family = utility_pairs[0][0].chosen_option_family_sha256
    placebo_family = utility_pairs[0][1].chosen_option_family_sha256

    def query(option: str, **overrides):
        scope = {
            "decision_namespace": authority.decision_namespace,
            "option_family_sha256": option,
            "task_contract_sha256": authority.task_contract_sha256,
            "choice_context_sha256": authority.choice_context_sha256,
            "continuation_context_sha256": (
                authority.continuation_context_sha256
            ),
            "available_option_family_sha256s": (
                authority.available_option_family_sha256s
            ),
            "external_utility_measure_sha256": measure_sha,
            "utility_compilation": compilation,
        }
        scope.update(overrides)
        return judge_combined_decision_option_task_credit(
            restored,
            **scope,
        )

    causal = query(causal_family)
    placebo = query(placebo_family)
    assert causal.immediate_preference == 0
    assert causal.temporal_preference == 0
    assert causal.utility_preference == 1
    assert causal.status == "utility_preferred"
    assert causal.preference == 1
    assert placebo.utility_preference == -1
    assert placebo.status == "utility_hazard"
    assert placebo.preference == -1
    assert causal.to_receipt()["authority_channels"] == {
        "immediate": "matched_external_terminal_adjudication",
        "temporal": "matched_external_terminal_adjudication",
        "utility": "matched_external_utility_adjudication",
        "information_yield": "selection_price_only",
    }

    candidates = (
        _candidate(
            "causal",
            preparation=("a", "b"),
            responses=("x", "x", "y"),
        ),
        _candidate(
            "placebo",
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
            "causal": causal.preference,
            "placebo": placebo.preference,
        },
    )
    assert baseline.selected_protocol_id == "placebo"
    assert reranked.selected_protocol_id == "causal"
    assert {
        row.protocol_id: row.cost.to_receipt()
        for row in baseline.prices
    } == {
        row.protocol_id: row.cost.to_receipt()
        for row in reranked.prices
    }

    assert query(
        causal_family,
        external_utility_measure_sha256="",
    ).preference == 0
    assert query(
        causal_family,
        external_utility_measure_sha256="wrong-measure",
    ).preference == 0
    assert query(
        causal_family,
        choice_context_sha256="wrong-context",
    ).preference == 0
    assert query(
        causal_family,
        continuation_context_sha256="wrong-controller",
    ).preference == 0
    assert query(
        causal_family,
        available_option_family_sha256s=(
            causal_family,
            "different-option",
        ),
    ).preference == 0
    assert query(
        causal_family,
        task_contract_sha256="wrong-task",
    ).preference == 0

    opposing = compile_temporal_decision_credit(
        _opposing_task_pairs(
            authority,
            utility_pairs[0][0].continuation_policy_sha256,
            causal_family,
            placebo_family,
        ),
        minimum_support=2,
        max_eligibility_delay_steps=0,
    )
    conflict = query(
        causal_family,
        temporal_compilation=opposing,
    )
    assert conflict.temporal_preference == -1
    assert conflict.utility_preference == 1
    assert conflict.status == "credit_conflict"
    assert conflict.preference == 0

    with pytest.raises(ValueError, match="conflicting evidence"):
        record_temporal_utility_arm(
            restored,
            replace(
                utility_pairs[0][0],
                external_outcome_ref="conflicting-evidence",
            ),
        )
