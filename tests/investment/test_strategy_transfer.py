from ztare.common.equivariance import stable_sha256
from ztare.investment.institutional_learning import (
    LAW_CANDIDATE_SCHEMA, LAW_EVALUATION_SCHEMA, LEARNING_STATE_SCHEMA, compile_law_candidate,
)
from ztare.investment.research_questions import compile_research_question_frontier
from ztare.investment.strategy_learning import STRATEGY_MOVE_LIBRARY_SCHEMA
from ztare.investment.strategy_transfer import (
    compile_strategy_program_transfer_index,
    compile_strategy_transfer_index,
    query_strategy_transfer,
)


def test_strategy_transfer_preserves_moderators_and_counterexamples():
    phenotype = {
        "action": "expand_adjacent_scope", "economic_bridge": "growth", "strategy_form": "scope",
        "addressed_actor_kinds": ["customer"],
        "implementation_mode": "acquisition",
    }
    phenotype_sha = stable_sha256(phenotype)
    candidate = compile_law_candidate({
        "schema": LAW_CANDIDATE_SCHEMA,
        "law_id": f"strategy-phenotype-{phenotype_sha[:16]}-durability",
        "version": "test", "name": "Adjacent scope via growth",
        "question": "Does this exact strategy phenotype improve earnings durability?",
        "created_at": "2025-01-01T00:00:00Z", "origin": "strategy_phenotype_compiler",
        "estimator": {"kind": "difference_in_differences", "expected_direction": "positive"},
        "cohort": {
            "entity_kinds": ["public_equity"], "horizon_days": [], "conditions": [],
            "evaluation_environments": ["industry_id"], "counterexample_fields": ["industry_id"],
        },
        "outcome_metric_id": "earnings_durability",
        "mechanism": {
            "antecedent_concepts": [f"strategy_phenotype:{phenotype_sha}"],
            "consequence_concept": "earnings_durability", "kind": "causal",
        },
        "validation": {}, "trial_family_id": "strategy-transfer-test", "authority": "diagnostic",
        "generation_receipt": {"mechanism_phenotype_sha256": phenotype_sha},
    })

    def move(entity, industry, status, effect):
        return {
            "entity_id": entity, "move_sha256": stable_sha256([entity, industry]),
            "mechanism_phenotype_sha256": phenotype_sha, "mechanism_phenotype": phenotype,
            "environment": {
                "industry_boundary": industry, "addressed_actor_kinds": ["customer"],
                "industry_actor_kinds": ["customer", "rival"],
            },
            "outcome_episodes": [{
                "episode_sha256": stable_sha256([entity, status]), "entity_id": entity,
                "metric_id": "earnings_durability", "estimated_effect": effect, "status": status,
                "available_at": "2026-01-01T00:00:00Z", "source_refs": [f"sec:{entity}"],
            }],
        }

    library = {
        "schema": STRATEGY_MOVE_LIBRARY_SCHEMA,
        "moves": [move("A", "software", "supports", 0.2), move("B", "industrial", "contradicts", -0.3)],
    }
    evaluation = {
        "schema": LAW_EVALUATION_SCHEMA, "law_key": candidate["law_key"],
        "law_sha256": candidate["law_sha256"], "generated_at": "2026-01-02T00:00:00Z",
        "status": "diagnostic_supported", "promotion_eligible": False,
    }
    state = {
        "schema": LEARNING_STATE_SCHEMA, "candidates": [candidate], "evaluations": [evaluation],
    }
    index = compile_strategy_transfer_index(library, state, generated_at="2026-01-03T00:00:00Z")
    result = query_strategy_transfer(index, action="expand_adjacent_scope", moderators={"industry_boundary": "industrial"})

    assert result["card_count"] == result["counterexample_count"] == 1
    assert result["cards"][0]["status"] == "challenged_by_settled_operating_outcome"
    assert result["cards"][0]["counterexamples"][0]["entity_id"] == "B"
    chain = result["cards"][0]["learning_chain"]
    assert chain["cohort"]["observed_company_count"] == 2
    assert chain["point_in_time_outcomes"]["settled_episode_count"] == 2
    assert chain["transfer"]["cross_company_observed"] is True
    assert chain["transfer"]["promotion_eligible"] is False
    assert result["cards"][0]["capital_authority"] is False

    frontier_body = {
        "schema": "jaggedthoughts-company-strategy-frontier-v1",
        "company": {"id": "TARGET"}, "evidence_epoch": "2026-01-02T00:00:00Z",
        "industry_state": {
            "boundary": "industrial",
            "pressures": [
                {"id": "customer", "actor_kind": "customer"},
                {"id": "rival", "actor_kind": "rival"},
            ],
        },
        "frontier_programs": [{"program_id": "f", "unique_option_ids": ["expand"]}],
        "local_peak_programs": [],
        "option_catalog": [{
            "option_id": "expand", "option_sha256": stable_sha256("expand"),
            "kind": "scope", "description": "Expand adjacent scope.",
            "claim_status": "supported", "addresses": ["customer"],
            "implementation_event": {
                "implementation_mode": "acquisition",
                "treatment_timing_status": "interval_censored_adoption_event",
            },
            "outcome_contracts": [{
                "metric_id": "earnings_durability", "contract_sha256": stable_sha256("contract"),
            }],
            "evidence_refs": ["target-filing"],
            "mechanism": {
                "action": "expand_adjacent_scope", "economic_bridge": "growth",
                "mechanism_sha256": stable_sha256("mechanism"),
            },
        }],
    }
    frontier = {**frontier_body, "strategy_frontier_sha256": stable_sha256(frontier_body)}
    target = {
        "entity_id": "TARGET", "entity_kind": "public_equity",
        "candidate_sha256": "c" * 64, "as_of": "2026-01-04T00:00:00Z",
        "screen_status": "qualified", "score_components": {}, "metrics": {},
    }
    question = compile_research_question_frontier(
        target, arm_id="disagreement_first", strategy_frontier=frontier,
        strategy_transfer_index=index,
    )
    edge = question["strategy_context"]["transfer_counterexample"]
    assert any(
        atom.startswith("strategy_counterexample:")
        for atom in question["selected_program"]["atom_ids"]
    )
    assert edge["counterexample_sha256"] == result["cards"][0]["counterexamples"][0]["counterexample_sha256"]
    assert edge["entity_relation"] == "cross_entity_public_equity"
    assert edge["causal_claim"] is edge["capital_authority"] is False
    assert "transfer_counterexample" not in compile_research_question_frontier(
        {**target, "as_of": "2026-01-02T00:00:00Z"},
        arm_id="disagreement_first", strategy_frontier=frontier,
        strategy_transfer_index=index,
    )["strategy_context"]


def test_settled_strategy_replication_requires_exact_prior_compatibility():
    phenotype = {
        "action": "expand_adjacent_scope", "economic_bridge": "growth",
        "strategy_form": "scope", "addressed_actor_kinds": ["customer"],
        "implementation_mode": "acquisition",
    }
    phenotype_sha = stable_sha256(phenotype)
    moderators = {
        "industry_boundary": "industrial", "addressed_actor_kinds": ["customer"],
        "industry_actor_kinds": ["customer", "rival"],
    }
    frontier_body = {
        "schema": "jaggedthoughts-company-strategy-frontier-v1",
        "company": {"id": "TARGET"}, "evidence_epoch": "2026-01-02T00:00:00Z",
        "industry_state": {
            "boundary": "industrial",
            "pressures": [
                {"id": "customer", "actor_kind": "customer"},
                {"id": "rival", "actor_kind": "rival"},
            ],
        },
        "frontier_programs": [{"program_id": "f", "unique_option_ids": ["expand"]}],
        "local_peak_programs": [],
        "option_catalog": [{
            "option_id": "expand", "option_sha256": stable_sha256("expand"),
            "kind": "scope", "description": "Expand adjacent scope.",
            "claim_status": "supported", "addresses": ["customer"],
            "implementation_event": {
                "implementation_mode": "acquisition",
                "treatment_timing_status": "interval_censored_adoption_event",
            },
            "outcome_contracts": [{
                "metric_id": "earnings_durability", "unit": "ratio",
                "contract_sha256": stable_sha256("contract"),
            }],
            "evidence_refs": ["target-filing"],
            "mechanism": {
                "action": "expand_adjacent_scope", "economic_bridge": "growth",
                "mechanism_sha256": stable_sha256("mechanism"),
            },
        }],
    }
    frontier = {**frontier_body, "strategy_frontier_sha256": stable_sha256(frontier_body)}
    candidate = {
        "entity_id": "TARGET", "entity_kind": "public_equity",
        "candidate_sha256": "c" * 64, "as_of": "2026-01-04T00:00:00Z",
        "rank_score": 0.42, "screen_status": "qualified", "score_components": {}, "metrics": {},
    }

    def transfer_index(status="supports", **changes):
        witness = {
            "kind": "settled_operating_outcome", "episode_sha256": "e" * 64,
            "move_sha256": "m" * 64, "entity_id": "SOURCE",
            "metric_id": changes.get("metric_id", "earnings_durability"),
            "unit": "ratio", "estimated_effect": 0.1, "status": status,
            "available_at": changes.get("available_at", "2026-01-01T00:00:00Z"),
            "moderators": changes.get("moderators", moderators),
            "source_refs": changes.get("source_refs", ["sec:SOURCE"]),
        }
        witness_row = {
            **witness,
            "witness_sha256": "" if changes.get("unhashed") else stable_sha256(witness),
        }
        card = {
            "schema": "jaggedthoughts-strategy-transfer-law-card-v1", "card_id": "card",
            "mechanism_phenotype_sha256": changes.get("phenotype_sha", phenotype_sha),
            "mechanism_phenotype": phenotype,
            "outcome_metric_id": changes.get("metric_id", "earnings_durability"),
            "learning_chain": {"cohort": {"declared_entity_kinds": ["public_equity"]}},
            "outcome_witnesses": [witness_row], "counterexamples": [],
        }
        card_row = {**card, "card_sha256": stable_sha256(card)}
        index = {
            "schema": "jaggedthoughts-strategy-transfer-index-v1",
            "generated_at": "2026-01-02T12:00:00Z", "cards": [card_row],
        }
        return {**index, "index_sha256": stable_sha256(index)}

    for status in ("supports", "inconclusive"):
        frozen_score = candidate["rank_score"]
        question = compile_research_question_frontier(
            candidate, arm_id="disagreement_first", strategy_frontier=frontier,
            strategy_transfer_index=transfer_index(status),
        )
        edge = question["strategy_context"]["transfer_replication"]
        assert any(
            atom.startswith("strategy_replication:")
            for atom in question["selected_program"]["atom_ids"]
        )
        assert edge["outcome_status"] == status
        assert edge["causal_claim"] is edge["paper_weight"] is edge["capital_authority"] is False
        assert candidate["rank_score"] == frozen_score

    incompatible = (
        {"available_at": "2026-01-05T00:00:00Z"},
        {"unhashed": True},
        {"source_refs": []},
        {"metric_id": "operating_margin"},
        {"moderators": {**moderators, "industry_boundary": "software"}},
        {"phenotype_sha": "f" * 64},
    )
    for changes in incompatible:
        question = compile_research_question_frontier(
            candidate, arm_id="disagreement_first", strategy_frontier=frontier,
            strategy_transfer_index=transfer_index(**changes),
        )
        assert "transfer_replication" not in question["strategy_context"]


def test_program_transfer_requires_independent_entities_and_environments():
    phenotype = {
        "composition_operator": "combine",
        "constituent_mechanism_phenotype_sha256s": ["a" * 64, "b" * 64],
        "constituent_count": 2,
    }
    phenotype_sha = stable_sha256(phenotype)
    plans, episodes = [], []
    for index, entity in enumerate(("A", "B", "C", "D")):
        readout_body = {
            "metric_id": "margin", "unit": "ratio", "direction": "increase",
            "minimum_effect": 0.01, "horizon_days": 365,
            "measurement_start_at": "2025-01-01T00:00:00Z",
            "due_at": "2026-01-01T00:00:00Z",
        }
        readout = {**readout_body, "readout_sha256": stable_sha256([entity, "readout"])}
        plan_body = {
            "schema": "jaggedthoughts-strategy-program-outcome-plan-v1",
            "entity_id": entity, "program_phenotype": phenotype,
            "program_phenotype_sha256": phenotype_sha,
            "program_roles": ["global_frontier"],
            "environment_boundaries": ["software" if index < 2 else "industrial"],
            "readouts": [readout],
        }
        plan = {**plan_body, "plan_sha256": stable_sha256(plan_body)}
        episode_body = {
            "schema": "jaggedthoughts-strategy-program-outcome-v1",
            "plan_sha256": plan["plan_sha256"], "readout_sha256": readout["readout_sha256"],
            "assessment": "contradicts" if entity == "D" else "supports",
            "available_at": "2026-02-01T00:00:00Z",
        }
        plans.append(plan)
        episodes.append({**episode_body, "episode_sha256": stable_sha256(episode_body)})
    local_readout = {
        "metric_id": "margin", "unit": "ratio", "direction": "increase",
        "minimum_effect": 0.01, "horizon_days": 365,
        "measurement_start_at": "2025-01-01T00:00:00Z",
        "due_at": "2026-01-01T00:00:00Z",
        "readout_sha256": stable_sha256(["LOCAL", "readout"]),
    }
    local_plan_body = {
        "schema": "jaggedthoughts-strategy-program-outcome-plan-v1",
        "entity_id": "LOCAL", "program_phenotype": phenotype,
        "program_phenotype_sha256": phenotype_sha,
        "program_roles": ["local_peak"], "environment_boundaries": ["software"],
        "readouts": [local_readout],
    }
    local_plan = {**local_plan_body, "plan_sha256": stable_sha256(local_plan_body)}
    local_episode_body = {
        "schema": "jaggedthoughts-strategy-program-outcome-v1",
        "plan_sha256": local_plan["plan_sha256"],
        "readout_sha256": local_readout["readout_sha256"],
        "assessment": "supports", "available_at": "2026-02-01T00:00:00Z",
    }
    plans.append(local_plan)
    episodes.append({
        **local_episode_body, "episode_sha256": stable_sha256(local_episode_body),
    })
    result = compile_strategy_program_transfer_index(
        plans, episodes, generated_at="2026-03-01T00:00:00Z",
    )
    card = result["cards"][0]
    assert card["comparison_ready"] is True
    assert card["descriptive_support_ready"] is True
    assert card["composition_increment_ready"] is False
    assert card["composition_increment_design"]["blockers"] == [
        "same_constituent_fragmented_controls_missing",
    ]
    assert card["counterexample_episode_sha256s"] == [episodes[3]["episode_sha256"]]
    assert card["entity_ids"] == ["A", "B", "C", "D"]
    assert card["settled_episode_count"] == 4
    assert result["causal_program_credit"] is False
