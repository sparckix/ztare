from ztare.common.equivariance import stable_sha256
from ztare.investment.learning_scheduler import compile_learning_schedule
from ztare.investment.research_budget_tournament import freeze_research_budget_tournament


def _law(law_id, kind):
    return {
        "law_id": law_id,
        "law_sha256": law_id[0] * 64,
        "estimator": {
            "kind": "difference_in_differences" if kind == "strategy" else "rank_association"
        },
        "cohort": {"entity_kinds": ["public_equity"], "horizon_days": [21]},
        "mechanism": {
            "antecedent_concepts": ["strategic_choice_adoption"] if kind == "strategy" else ["value"]
        },
        "validation": {"minimum_inference_blocks": 8},
    }


def _job(work_id, kind, status="queued", created_at=1786490000):
    return {
        "work_id": work_id, "kind": f"jaggedthoughts_{kind}", "status": status,
        "created_at": created_at,
        "payload": {"entity_id": work_id.upper(), "entity_kind": "public_equity"},
    }


def test_strategy_outcome_rises_when_it_separates_and_fills_a_cohort_gap():
    state = {"candidates": [_law("a-value", "value"), _law("b-strategy", "strategy")]}
    queue = [_job("underwrite", "subscription_research"), _job("outcome", "strategy_outcome_research")]
    ranked = compile_learning_schedule(queue, state, generated_at="2026-08-12T00:00:00Z")
    assert ranked["next_action"]["work_id"] == "outcome"
    assert ranked["next_action"]["queue_priority"] > ranked["actions"][1]["queue_priority"]
    assert ranked["capital_authority"] is False
    assert ranked["policy"]["observed_information_gain"] is False


def test_successor_hypothesis_evidence_is_scheduled_as_its_own_learning_action():
    evidence = _job("successor-evidence", "hypothesis_set_evidence_research")
    action = compile_learning_schedule(
        [evidence], {}, generated_at="2026-08-12T00:00:00Z",
    )["next_action"]

    assert action["work_id"] == "successor-evidence"
    assert action["action_class"] == "test_successor_hypothesis_committee"


def test_priority_output_does_not_feed_back_into_the_next_schedule():
    queue = [_job("a", "subscription_research"), _job("b", "strategy_frontier_research")]
    at = "2026-08-12T00:00:00Z"
    first = compile_learning_schedule(queue, {}, generated_at=at)
    priorities = {row["work_id"]: row["queue_priority"] for row in first["actions"]}
    rewritten = [{**row, "priority": priorities[row["work_id"]]} for row in reversed(queue)]
    assert compile_learning_schedule(rewritten, {}, generated_at=at) == first


def test_candidate_potential_rank_remains_primary_over_learning_proxies():
    higher_potential = _job("rank-1", "subscription_research", created_at=1786490001)
    lower_potential = _job("rank-2", "subscription_research", created_at=1786490000)
    higher_potential["priority"] = 999_000
    lower_potential["priority"] = 998_000
    ranked = compile_learning_schedule(
        [lower_potential, higher_potential], {}, generated_at="2026-08-12T00:00:00Z",
    )
    assert [row["work_id"] for row in ranked["actions"]] == ["rank-1", "rank-2"]


def test_candidate_strategy_frontier_keeps_the_candidate_potential_order():
    frontier = _job("frontier", "strategy_frontier_research")
    frontier.update(priority=996_999)
    frontier["payload"]["potential_rank"] = {"rank": 3, "scope": "public_equity"}
    action = compile_learning_schedule(
        [frontier], {}, generated_at="2026-08-12T00:00:00Z",
    )["next_action"]
    assert (action["queue_priority"], action["ordering_basis"]) == (
        996_999, "candidate_potential_rank",
    )


def test_candidate_reassessment_keeps_current_candidate_priority():
    reassessment = _job("changed-filing", "subscription_reassessment")
    reassessment.update(priority=998_000)
    reassessment["payload"]["research_rank"] = 2

    action = compile_learning_schedule(
        [reassessment], {}, generated_at="2026-08-12T00:00:00Z",
    )["next_action"]

    assert (action["queue_priority"], action["ordering_basis"]) == (
        998_000, "candidate_potential_rank",
    )


def test_frozen_measurement_chain_closes_before_research_widens():
    measurement = _job("measure", "strategy_measurement_research")
    measurement["payload"]["frozen_chain_priority"] = 1_030_000
    activation = _job("widen", "subscription_activation_research")
    activation["priority"] = 1_025_000

    ranked = compile_learning_schedule(
        [activation, measurement], {}, generated_at="2026-08-12T00:00:00Z",
    )

    assert ranked["next_action"]["work_id"] == "measure"
    assert ranked["next_action"]["ordering_basis"] == "prospective_chain_successor"


def test_blind_constraint_dependency_is_a_frozen_chain_successor():
    evidence = _job("constraint", "strategy_constraint_evidence_research")
    evidence["payload"]["frozen_chain_priority"] = 1_030_000
    activation = _job("widen", "subscription_activation_research")
    activation["priority"] = 1_025_000

    next_action = compile_learning_schedule(
        [activation, evidence], {}, generated_at="2026-08-12T00:00:00Z",
    )["next_action"]

    assert (next_action["work_id"], next_action["ordering_basis"]) == (
        "constraint", "prospective_chain_successor",
    )


def test_under_served_job_type_cannot_be_starved_by_a_higher_scoring_type():
    rows = [_job(f"done-{i}", "strategy_outcome_research", "done") for i in range(2)]
    rows += [_job("outcome", "strategy_outcome_research"), _job("frontier", "strategy_frontier_research")]
    ranked = compile_learning_schedule(rows, {}, generated_at="2026-08-12T00:00:00Z")
    assert ranked["next_action"]["work_id"] == "frontier"
    assert ranked["next_action"]["action_class_service_ratio"] == 0.0


def test_administrative_supersession_does_not_count_as_research_service():
    stale = _job("old", "subscription_research", "done")
    stale["payload"].update({"entity_id": "ALPHA", "stage": "superseded"})
    current = _job("current", "subscription_research")
    current["payload"]["entity_id"] = "ALPHA"
    action = compile_learning_schedule(
        [stale, current], {}, generated_at="2026-08-12T00:00:00Z",
    )["next_action"]
    assert action["same_entity_action_ordinal"] == 1
    assert action["action_class_service_ratio"] == 0.0


def test_future_laws_episodes_cohorts_and_queue_rows_are_invisible():
    past = _law("a-past", "value")
    future = {**_law("b-future", "value"), "created_at": "2026-08-13T00:00:00Z"}
    state = {
        "candidates": [future, past],
        "phenotype_episodes": [{
            "episode_id": "future-episode", "entity_id": "FUT", "entity_kind": "public_equity",
            "inference_block_id": "future-block", "opened_at": "2026-08-13T00:00:00Z",
        }],
        "cohorts": [{
            "law_sha256": past["law_sha256"], "generated_at": "2026-08-12T00:00:00Z",
            "inference_block_count": 8, "member_episode_ids": ["future-episode"],
        }],
    }
    queue = [_job("visible", "subscription_research"), _job("future", "subscription_research", created_at=2_000_000_000)]
    queue[0]["payload"]["entity_id"] = "FUT"
    ranked = compile_learning_schedule(queue, state, generated_at="2026-08-12T00:00:00Z")
    assert ranked["committee"]["law_count"] == 1
    assert [row["work_id"] for row in ranked["actions"]] == ["visible"]
    assert ranked["next_action"]["components"]["unseen_entity_context"] == 1.0
    assert ranked["next_action"]["components"]["cohort_sampling_gap_upper_bound"] == 1.0


def test_mandate_relevance_is_order_invariant_and_shadow_only():
    weights = ({"cash": 0.2, "us_equity": 0.8}, {"cash": 0.6, "us_equity": 0.4})
    classes = [{
        "decision_id": stable_sha256({"selected_sleeve_weights": row}),
        "selected_sleeve_weights": row,
    } for row in weights]
    mandate_body = {
        "schema": "jaggedthoughts-household-mandate-frontier-v1",
        "basis_sha256": "b" * 64, "decision_class_count": 2,
        "decision_classes": classes,
    }
    mandate = {**mandate_body, "mandate_frontier_sha256": stable_sha256(mandate_body)}
    implementation_body = {
        "schema": "jaggedthoughts-sleeve-implementation-frontier-v1",
        "basis_sha256": "b" * 64,
        "sleeves": [{
            "sleeve_id": sleeve_id,
            "eligible_instruments": [{
                "identity": {"subject_id": entity}, "research_eligible": True,
            }],
        } for sleeve_id, entity in (("cash", "CASH"), ("us_equity", "EQUITY"))],
    }
    implementation = {
        **implementation_body,
        "sleeve_implementation_sha256": stable_sha256(implementation_body),
    }
    queue = [_job("cash", "subscription_research"), _job("equity", "subscription_research")]
    first = compile_learning_schedule(
        queue, {}, generated_at="2026-08-12T00:00:00Z",
        household_mandate_frontier=mandate,
        sleeve_implementation_frontier=implementation,
    )
    second = compile_learning_schedule(
        list(reversed(queue)), {}, generated_at="2026-08-12T00:00:00Z",
        household_mandate_frontier=mandate,
        sleeve_implementation_frontier=implementation,
    )
    assert first == second
    actions = {row["work_id"]: row for row in first["actions"]}
    assert actions["equity"]["mandate_decision_relevance"]["maximum_planning_weight_upper_bound"] == 0.8
    assert actions["cash"]["mandate_decision_relevance"]["capital_authority"] is False
    assert [row["queue_priority"] for row in first["actions"]] == [
        row["queue_priority"] for row in compile_learning_schedule(
            queue, {}, generated_at="2026-08-12T00:00:00Z",
        )["actions"]
    ]
    freeze = freeze_research_budget_tournament(
        first, frozen_at="2026-08-12T01:00:00Z", inference_block_id="mandate-block",
    )
    arm = next(row for row in freeze["arms"] if row["policy_id"] == "mandate_decision_relevance_per_cost")
    assert arm["selected_work_ids"] == ["equity"]
    assert freeze["queue_mutation_authority"] is False
