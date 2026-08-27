from copy import deepcopy

from ztare.common.equivariance import stable_sha256
from ztare.investment.institutional_learning import LEARNING_STATE_SCHEMA, STRATEGY_REGULARITY_SCHEMA
from ztare.investment.strategy_law_induction import (
    bind_strategy_effect,
    compile_causal_law_target_influence,
    compile_strategy_law_induction,
)
from ztare.investment.strategy_learning import STRATEGY_COHORT_PLAN_SCHEMA, STRATEGY_MOVE_LIBRARY_SCHEMA


PHENOTYPE = {
    "action": "expand_adjacent_scope", "economic_bridge": "growth",
    "strategy_form": "adjacent_platform", "addressed_actor_kinds": ["customer"],
    "implementation_mode": "acquisition",
}
PHENOTYPE_SHA = stable_sha256(PHENOTYPE)
MOVE_SHA = stable_sha256("move")
FIELDS = [
    "strategy_form", "addressed_actor_profile", "implementation_mode",
    "operating_object_scope",
]


def _inputs(with_outcome=False):
    request = {
        "request_sha256": stable_sha256("request"), "created_at": "2026-08-13T14:00:00Z",
    }
    plan = {
        "schema": STRATEGY_COHORT_PLAN_SCHEMA, "plan_sha256": stable_sha256("plan"),
        "requests": [request],
        "mechanism_environments": [{
            "mechanism_signature_sha256": stable_sha256("family"),
            "mechanism_phenotype_sha256": PHENOTYPE_SHA,
            "mechanism_phenotype": PHENOTYPE, "industry_id": "semiconductors",
            "focal_moves": [{
                "move_sha256": MOVE_SHA,
                "implementation_event": {"implementation_event_sha256": stable_sha256("event")},
            }],
        }],
    }
    environment = {
        "industry_id": "semiconductors",
        "mechanism_signature_sha256": stable_sha256("family"),
        "mechanism_phenotype_sha256": PHENOTYPE_SHA,
    }
    move_library = {
        "schema": STRATEGY_MOVE_LIBRARY_SCHEMA, "library_sha256": stable_sha256("library"),
        "moves": [{
            "move_sha256": MOVE_SHA, "kind": "adjacent_platform",
            "mechanism_signature_sha256": stable_sha256("family"),
            "mechanism_phenotype_sha256": PHENOTYPE_SHA,
            "mechanism_phenotype": PHENOTYPE,
            "mechanism": {"object_id": "adjacent-platform"},
            "implementation_event": {
                "implementation_event_sha256": stable_sha256("event"),
                "implementation_mode": "acquisition",
                "treatment_timing_status": "exact_adoption_event",
                "available_at": "2026-08-13T13:00:00Z",
            },
            "causal_panel_status": "treatment_event_ready",
            "evidence_epoch": "2026-08-13T13:00:00Z",
        }],
    }
    program_id = stable_sha256("projection")
    projection = {
        "schema": "jaggedthoughts-strategy-phenotype-projection-frontier-v1",
        "plan_sha256": plan["plan_sha256"], "projection_frontier_sha256": stable_sha256("frontier"),
        "certificate": {
            "certificate_sha256": stable_sha256("certificate"),
            "frontier_program_ids": [program_id],
            "scope": {"evidence_epoch": "2026-08-13T14:00:00Z"},
        },
        "projections": [{
            "program_id": program_id, "required_relation_fields": FIELDS,
            "classified_coverage_count": 1,
            "peer_roles": [{"entity_id": "PEER", "role": "control_candidate", "event_sha256s": []}],
        }],
    }
    state = {"schema": LEARNING_STATE_SCHEMA, "state_sha256": stable_sha256("empty"), "evaluations": []}
    if with_outcome:
        regularity = {
            "schema": STRATEGY_REGULARITY_SCHEMA,
            "law_key": "law@1", "regularity_evidence_sha256": stable_sha256("regularity"),
            "regularity_identity": {
                "mechanism_phenotype_sha256": PHENOTYPE_SHA,
                "outcome_metric_id": "earnings_durability",
            },
            "outcome_unit": "score",
            "prospective_holdout": {
                "eligible": True,
                "required": {"treated_units": 4, "control_units": 4, "transfer_environments": 2},
                "observed": {
                    "independent_treated_units": 4, "bounded_control_units": 4,
                    "transfer_environments": 2, "group_time_cells": 2,
                },
                "independent_treatment_event_sha256s": [stable_sha256("new-event")],
                "power_status": "declared_effect_resolved",
            },
            "diagnostics": {
                "aggregate_att": 0.08, "resampling_interval_95": [0.02, 0.14],
                "group_time_effects": [{"environment_sha256": stable_sha256("environment")}],
                "transport_effects": [{
                    "environment": environment,
                    "environment_sha256": stable_sha256(environment),
                    "estimate": 0.08, "resampling_interval_95": [0.02, 0.14],
                    "group_time_cell_sha256s": [stable_sha256("cell")],
                    "horizon": {
                        "kind": "calendar_days_after_adoption",
                        "minimum": 300, "maximum": 450,
                    },
                    "treated_unit_ids": ["phenotype:T1"],
                    "control_unit_ids": ["phenotype:C1"],
                }],
            },
            "provenance": {
                "prospective_panel_row_sha256s": [stable_sha256("new-row")],
                "source_refs": ["sec:peer"],
            },
            "counterexamples": [],
        }
        state = {
            "schema": LEARNING_STATE_SCHEMA, "state_sha256": stable_sha256("settled"),
            "evaluations": [{
                "strategy_regularity": regularity,
                "multiplicity": {"rows": [{"rejected_at_alpha": True}]},
            }],
        }
    return move_library, plan, projection, state


def test_strategy_law_freezes_before_outcome_then_binds_exact_effect():
    initial = compile_strategy_law_induction(
        *_inputs(), generated_at="2026-08-13T14:20:00Z",
    )
    assert initial["eligible_candidate_count"] == 0
    assert initial["candidates"][0]["effect_estimate"]["status"] == "proposal_only"

    settled = compile_strategy_law_induction(
        *_inputs(with_outcome=True), generated_at="2026-09-01T00:00:00Z", prior=initial,
    )
    candidate = settled["candidates"][0]
    assert candidate["not_before"] == initial["candidates"][0]["not_before"]
    assert candidate["policy_review_eligible"] is True
    assert candidate["effect_estimate"]["status"] == "transported_magnitude_available"
    assert candidate["target_applications"][0]["status"] == "proposal_only"
    assert "target_move_in_training_support" in candidate["target_applications"][0]["blockers"]
    environment = {
        "industry_id": "semiconductors",
        "mechanism_signature_sha256": stable_sha256("family"),
        "mechanism_phenotype_sha256": PHENOTYPE_SHA,
    }
    bound = bind_strategy_effect(
        candidate, _inputs(with_outcome=True)[0],
        target_move_sha256=MOVE_SHA, target_environment=environment,
        metric_id="earnings_durability", unit="score", as_of="2026-09-01T00:00:00Z",
    )
    assert bound["status"] == "proposal_only"
    assert "target_move_in_training_support" in bound["blockers"]
    assert bound["capital_authority"] is False
    assert bind_strategy_effect(
        candidate, _inputs(with_outcome=True)[0],
        target_move_sha256=MOVE_SHA, target_environment=environment,
        metric_id="earnings_durability", unit="usd", as_of="2026-09-01T00:00:00Z",
    )["status"] == "proposal_only"
    wrong_scope_library = deepcopy(_inputs(with_outcome=True)[0])
    wrong_scope = {**wrong_scope_library["moves"][0], "move_sha256": stable_sha256("wrong-scope")}
    wrong_scope["mechanism"] = {"object_id": "unrelated-object"}
    wrong_scope_library["moves"].append(wrong_scope)
    rejected = bind_strategy_effect(
        candidate, wrong_scope_library,
        target_move_sha256=wrong_scope["move_sha256"], target_environment=environment,
        metric_id="earnings_durability", unit="score", as_of="2026-09-01T00:00:00Z",
    )
    assert "target_fails_frontier_selected_relation_program" in rejected["blockers"]


def test_causal_law_influences_only_unseen_exact_candidate_and_move():
    initial = compile_strategy_law_induction(
        *_inputs(), generated_at="2026-08-13T14:20:00Z",
    )
    settled = compile_strategy_law_induction(
        *_inputs(with_outcome=True), generated_at="2026-09-01T00:00:00Z", prior=initial,
    )
    library = deepcopy(_inputs(with_outcome=True)[0])
    target = deepcopy(library["moves"][0])
    target.update({
        "entity_id": "X", "move_sha256": stable_sha256("unseen-target-move"),
        "implementation_event": {
            **target["implementation_event"],
            "implementation_event_sha256": stable_sha256("unseen-target-event"),
        },
        "outcome_contracts": [{
            "contract_sha256": stable_sha256("target-contract"),
            "metric_id": "earnings_durability", "unit": "score",
            "direction": "increase", "horizon_days": 365,
        }],
        "outcome_episodes": [],
    })
    library["moves"].append(target)
    catalog = {
        "schema": "jaggedthoughts-public-market-catalog-v1",
        "catalog_sha256": stable_sha256("catalog"),
        "securities": [{
            "symbol": "X", "industry": "semiconductors",
            "available_at": "2026-08-30T00:00:00Z",
        }],
    }

    def candidate(**changes):
        body = {
            "candidate_id": "equity:X", "entity_id": "X",
            "entity_kind": "public_equity", "as_of": "2026-08-31T00:00:00Z",
            "screen_status": "monitor", "rank_score": 0.5, **changes,
        }
        return {**body, "candidate_sha256": stable_sha256(body)}

    active = compile_causal_law_target_influence(
        [candidate()], settled, library, catalog,
        generated_at="2026-09-01T00:00:00Z",
    )
    assert active["candidates"][0]["adjustment"] == 0.025
    receipt = next(row for row in active["attempts"] if row["status"] == "eligible_research_influence")
    assert receipt["training_overlap"] == {
        "entity_ids": [], "move_sha256s": [], "event_sha256s": [],
        "panel_row_sha256s": [],
    }
    assert receipt["screen_status_before"] == receipt["screen_status_after"] == "monitor"
    assert receipt["capital_authority"] is False

    no_event = deepcopy(library)
    no_event["moves"][-1]["implementation_event"] = None
    assert compile_causal_law_target_influence(
        [candidate()], settled, no_event, catalog,
        generated_at="2026-09-01T00:00:00Z",
    )["active_application_count"] == 0
    assert compile_causal_law_target_influence(
        [candidate(as_of="2026-09-02T00:00:00Z")], settled, library, catalog,
        generated_at="2026-09-01T00:00:00Z",
    )["active_application_count"] == 0

    leaked = deepcopy(library)
    leaked["moves"][-1]["outcome_episodes"] = [{
        "available_at": "2026-09-01T00:00:00Z",
        "panel_row_sha256": settled["candidates"][0]["cohort_identity"][
            "training_panel_row_sha256s"
        ][0],
    }]
    blocked = compile_causal_law_target_influence(
        [candidate()], settled, leaked, catalog,
        generated_at="2026-09-01T00:00:00Z",
    )
    assert blocked["active_application_count"] == 0
    assert any(
        "target_panel_row_in_training_support" in row["blockers"]
        for row in blocked["attempts"]
    )


def test_counterexample_refines_only_future_candidate():
    initial = compile_strategy_law_induction(
        *_inputs(), generated_at="2026-08-13T14:20:00Z",
    )
    args = list(_inputs(with_outcome=True))
    state = deepcopy(args[-1])
    state["evaluations"][0]["strategy_regularity"]["counterexamples"] = [
        {"field": "industry_id", "value": "hardware", "effect": -0.1},
    ]
    args[-1] = state
    challenged = compile_strategy_law_induction(
        *args, generated_at="2026-09-02T00:00:00Z", prior=initial,
    )["candidates"][0]
    assert challenged["status"] == "challenged_by_counterexample"
    assert challenged["effect_estimate"]["status"] == "proposal_only"
    refinement = challenged["cegar_refinements"][0]
    assert refinement["not_before"] == "2026-09-02T00:00:00Z"
    assert refinement["capital_authority"] is False
