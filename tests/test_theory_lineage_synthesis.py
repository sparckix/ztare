from __future__ import annotations

import json
import pytest
from jsonschema import Draft202012Validator

from ztare.common.task_discharge import TaskDischargeContract
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.theory_lineage_synthesis import (
    build_theory_move_portfolio,
    compose_selected_language_expansion,
    formula_lineage_request_id,
    lineage_synthesis_input,
    lineage_request_matches_context,
    lineage_synthesis_output_schema,
    theory_move_consequence_receipt,
    validate_lineage_synthesis_decision,
)
from ztare.leanmill.theory_language import (
    build_theory_language_expansion_request,
)


def _navigation():
    formula = {
        "lineage_id": "lineage:a",
        "proposal": {
            "source_context_hash": "context:a",
            "source_epoch": 2,
            "formula_id": "formula:a",
        },
    }
    formula["request_id"] = formula_lineage_request_id(formula)
    return {
        "context_hash": "context:a",
        "context_epoch": 2,
        "expansion_proposals": [formula],
        "theory_language_expansion_requests": [
            {
                "lineage_id": "lineage:b",
                "request_id": "language:b",
                "request": {
                    "request_id": "language:b",
                    "source_context_hash": "context:a",
                    "source_epoch": 2,
                },
            }
        ],
        "isolation_receipt": {"receipt_sha256": "isolation:a"},
    }


def test_late_synthesis_partitions_frozen_requests_without_admission_authority():
    synthesis_input = lineage_synthesis_input(_navigation())
    formula_id = synthesis_input["formula_requests"][0]["request_id"]
    language_id = synthesis_input["theory_language_requests"][0]["request_id"]
    decision = {
        "route": "admit_formulas",
        "continuation_mode": "none",
        "selected_request_ids": [formula_id],
        "deferred_request_ids": [language_id],
        "rationale": "Test the signature-preserving coordinate first.",
        "next_discriminator": "Rebuild the context and test its profile.",
        "kill_condition": "The coordinate duplicates the prior chart.",
        "program_ids": [],
        "next_discriminator_request_ids": [formula_id],
    }
    Draft202012Validator(lineage_synthesis_output_schema()).validate(decision)
    assert "uniqueItems" not in json.dumps(lineage_synthesis_output_schema())

    receipt = validate_lineage_synthesis_decision(synthesis_input, decision)

    assert receipt["route"] == "admit_formulas"
    assert receipt["selected_requests"][0]["request_id"] == formula_id
    assert receipt["authority"] == "agent_choice_host_validated"


def test_compatible_selected_language_requests_form_one_typed_transition():
    first = build_theory_language_expansion_request(
        source_context_hash="context:a",
        source_epoch=2,
        change_kind="new_operation",
        blind_spot="The chart cannot lower the source object.",
        proposed_interface="operation lower_source(source, coordinate)",
        evidence_refs=["sha256:first", "sha256:shared"],
        discriminating_test="Enumerate every coordinate.",
        kill_condition="No member can be normalized.",
    )
    second = build_theory_language_expansion_request(
        source_context_hash="context:a",
        source_epoch=2,
        change_kind="new_operation",
        blind_spot="The chart cannot report family exhaustion.",
        proposed_interface="observable verify_member(candidate)",
        evidence_refs=["sha256:shared", "sha256:second"],
        discriminating_test="Verify every lowered member.",
        kill_condition="A member lacks an exact receipt.",
    )
    navigation = {
        "context_hash": "context:a",
        "context_epoch": 2,
        "theory_language_expansion_requests": [
            {
                "lineage_id": "lineage:a",
                "request_id": first.request_id,
                "request": first.to_json(),
            },
            {
                "lineage_id": "lineage:b",
                "request_id": second.request_id,
                "request": second.to_json(),
            },
        ],
    }
    synthesis_input = lineage_synthesis_input(navigation)
    selected = [first.request_id, second.request_id]
    synthesis = validate_lineage_synthesis_decision(
        synthesis_input,
        {
            "route": "escalate_language",
            "continuation_mode": "none",
            "selected_request_ids": selected,
            "deferred_request_ids": [],
            "rationale": "The two requests specify one conjunctive operation.",
            "next_discriminator": "Lower and verify every family member.",
            "kill_condition": "Reject if coverage or exact replay is absent.",
            "program_ids": [],
            "next_discriminator_request_ids": selected,
        },
    )

    composite, receipt = compose_selected_language_expansion(synthesis)

    assert composite.source_context_hash == "context:a"
    assert composite.change_kind == "new_operation"
    assert composite.discriminating_test == (
        "Lower and verify every family member."
    )
    assert composite.kill_condition == (
        "Reject if coverage or exact replay is absent."
    )
    assert composite.evidence_refs == (
        "sha256:first",
        "sha256:shared",
        "sha256:second",
    )
    assert receipt is not None
    assert receipt["source_request_ids"] == selected
    assert receipt["composite_request_id"] == composite.request_id


def test_synthesis_input_carries_cited_governed_trace_receipts():
    trace_core = {
        "schema": "leanmill.axiompack_workbench_receipt.v1",
        "capability_id": "inspect_presentation_extent",
        "authority": "deterministic_host",
        "output_summary": {"status": "inspected"},
    }
    trace_receipt = {
        **trace_core,
        "receipt_id": "sha256:" + content_hash(trace_core),
    }
    request = build_theory_language_expansion_request(
        source_context_hash="context:a",
        source_epoch=2,
        change_kind="new_operation",
        blind_spot="The current language lacks a lowering.",
        proposed_interface="operation lower(source)",
        evidence_refs=[trace_receipt["receipt_id"], "context.json#artifact"],
        discriminating_test="Lower the frozen source.",
        kill_condition="No exact output is available.",
    )
    navigation = {
        "context_hash": "context:a",
        "context_epoch": 2,
        "theory_language_expansion_requests": [
            {
                "lineage_id": "lineage:a",
                "request_id": request.request_id,
                "request": request.to_json(),
            }
        ],
        "lineages": [
            {
                "lineage_id": "lineage:a",
                "navigation": {
                    "trace": [{"receipt": trace_receipt}],
                },
            }
        ],
    }

    synthesis_input = lineage_synthesis_input(navigation)

    assert synthesis_input["carried_evidence_receipts"] == [
        {
            "evidence_ref": trace_receipt["receipt_id"],
            "receipt": trace_receipt,
        }
    ]


def test_alpha_blind_portfolio_requires_a_language_move_or_stop():
    objective = {
        "schema": "leanmill.frontier_objective_contract.v1",
        "instruction": "Invent a representation that changes the prediction frontier.",
    }
    navigation = {
        "context_hash": "context:a",
        "context_epoch": 2,
        "finalists": [
            {
                "theory_program": {"program_id": "theory-program:a"},
                "prediction_profile": {
                    "predictions": [
                        {"chart_status": "holds_on_complete_context"}
                    ]
                },
                "residual_information_yield": {"information_per_cost": 0.25},
            }
        ],
    }
    wave_core = {
        "schema": "leanmill.theory_search_wave_image.v1",
        "context_hash": "context:a",
        "context_epoch": 2,
        "search_wave": 3,
        "growth_kind": "alpha_blind",
        "raw_carriers": ["raw:a"],
        "image_carriers": [],
        "new_raw_count": 1,
        "new_image_count": 0,
        "continuation_semantics": "leaf should author a richer abstraction or stop unresolved",
        "authority": "deterministic_host_projection",
        "claim_boundary": "current outcome abstraction only",
    }
    from ztare.leanmill.theory_ir import content_hash

    navigation["search_wave_image_receipt"] = {
        **wave_core,
        "receipt_sha256": content_hash(wave_core),
    }
    portfolio = build_theory_move_portfolio(
        navigation, objective_contract=objective
    )
    synthesis_input = lineage_synthesis_input(
        {**navigation, "adaptive_move_portfolio": portfolio},
        objective_contract=objective,
    )
    blocked_decision = {
        "route": "continue_search",
        "continuation_mode": "formula_coordinate",
        "selected_request_ids": [],
        "deferred_request_ids": [],
        "program_ids": ["theory-program:a"],
        "next_discriminator_request_ids": [],
        "rationale": "The current image aliases new conjectures.",
        "next_discriminator": "Author a coordinate that separates the alias class.",
        "kill_condition": "The coordinate has an old semantic profile.",
    }
    assert portfolio["quality_diversity_state"]["growth_kind"] == "alpha_blind"
    options = {
        (row["route"], row["continuation_mode"]): row["availability"]
        for row in portfolio["options"]
    }
    assert options[("continue_search", "current_context")] == (
        "blocked_precondition"
    )
    assert options[("continue_search", "formula_coordinate")] == (
        "blocked_precondition"
    )
    assert options[("continue_search", "theory_language")] == "available"
    assert options[("defer_all", "none")] == "available"
    with pytest.raises(ValueError, match="not an available affordance"):
        validate_lineage_synthesis_decision(synthesis_input, blocked_decision)

    language_decision = {
        **blocked_decision,
        "continuation_mode": "theory_language",
        "rationale": "The current semantic image aliases the new candidates.",
        "next_discriminator": (
            "Author an abstraction with a new observable carrier."
        ),
        "kill_condition": "The successor leaves the image partition unchanged.",
    }
    receipt = validate_lineage_synthesis_decision(
        synthesis_input, language_decision
    )

    assert receipt["continuation_mode"] == "theory_language"
    assert receipt["selected_move_affordance"]["route"] == "continue_search"
    assert receipt["move_portfolio_receipt_sha256"] == portfolio["receipt_sha256"]

    consequence = theory_move_consequence_receipt(
        {
            "context_hash": "context:a",
            "context_epoch": 2,
            "search_wave": 4,
            "provider_calls": 1,
            "theory_language_expansion_requests": [
                {"request_id": "language-request:a"}
            ],
        },
        receipt,
    )
    assert consequence["status"] == "executed_as_planned"
    assert consequence["observed_move_modes"] == ["theory_language"]


def test_reviewed_prediction_is_removed_from_boundary_option_count():
    objective = {
        "schema": "leanmill.frontier_objective_contract.v1",
        "instruction": "Test one frozen prediction.",
    }
    portfolio = build_theory_move_portfolio(
        {
            "context_hash": "context:a",
            "context_epoch": 0,
            "finalists": [{
                "theory_program": {"program_id": "theory-program:a"},
                "prediction_profile": {
                    "predictions": [{
                        "prediction_formula_id": "formula:a",
                        "chart_status": "holds_on_complete_context",
                    }],
                },
                "objective_feedback": {
                    "prediction_outcomes": [{
                        "target_formula_id": "formula:a",
                        "status": "no_countermodel_at_boundary",
                    }],
                },
            }],
        },
        objective_contract=objective,
    )

    assert portfolio["residual_state"]["unresolved_prediction_count"] == 0
    boundary = next(
        row for row in portfolio["options"] if row["route"] == "proceed_boundary"
    )
    assert boundary["availability"] == "blocked_precondition"


def test_registered_task_program_is_an_executable_boundary_affordance():
    from ztare.leanmill.witness_construction_boundary import (
        GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR,
    )

    objective = {
        "schema": "leanmill.frontier_objective_contract.v1",
        "instruction": "Adjudicate one frozen construction task.",
    }
    task = TaskDischargeContract(
        contract_id="theory-task:witness",
        adjudicator_id=GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR,
        lifecycle_scope="campaign:a",
        owner="lineage:a",
        parameters={"kind": "test"},
    )
    navigation = {
        "context_hash": "context:a",
        "context_epoch": 0,
        "finalists": [
            {
                "theory_program": {
                    "program_id": "theory-program:task",
                    "task_discharge_contracts": [task.to_dict()],
                },
                "prediction_profile": {"predictions": []},
            }
        ],
    }
    portfolio = build_theory_move_portfolio(
        navigation, objective_contract=objective
    )
    boundary = next(
        row for row in portfolio["options"] if row["route"] == "proceed_boundary"
    )
    assert boundary["availability"] == "available"
    assert portfolio["residual_state"]["registered_boundary_task_count"] == 1

    synthesis_input = lineage_synthesis_input(
        {**navigation, "adaptive_move_portfolio": portfolio},
        objective_contract=objective,
    )
    decision = {
        "route": "proceed_boundary",
        "continuation_mode": "none",
        "selected_request_ids": [],
        "deferred_request_ids": [],
        "program_ids": ["theory-program:task"],
        "next_discriminator_request_ids": [],
        "rationale": "The task has a registered boundary consumer.",
        "next_discriminator": "Execute its exact adjudicator.",
        "kill_condition": "The adjudicator rejects the artifact.",
    }
    receipt = validate_lineage_synthesis_decision(synthesis_input, decision)
    assert receipt["route"] == "proceed_boundary"
    assert receipt["selected_move_affordance"]["availability"] == "available"

    stale_portfolio_core = {
        key: value for key, value in portfolio.items() if key != "receipt_sha256"
    }
    stale_options = [dict(row) for row in stale_portfolio_core["options"]]
    for row in stale_options:
        if row["route"] == "proceed_boundary":
            row["availability"] = "blocked_precondition"
    stale_portfolio_core["options"] = stale_options
    stale_portfolio = {
        **stale_portfolio_core,
        "receipt_sha256": content_hash(stale_portfolio_core),
    }
    stale_input = lineage_synthesis_input(
        {**navigation, "adaptive_move_portfolio": stale_portfolio},
        objective_contract=objective,
    )
    corrected = validate_lineage_synthesis_decision(stale_input, decision)
    assert corrected["selected_move_affordance"]["availability"] == "available"
    assert corrected["move_affordance_correction"]["prior_availability"] == (
        "blocked_precondition"
    )


def test_adaptive_consequence_consumes_a_receipted_diagnostic_before_timeout():
    source_core = {
        "schema": "leanmill.lineage_synthesis_decision.v1",
        "route": "continue_search",
        "continuation_mode": "current_context",
        "move_portfolio_receipt_sha256": "portfolio:a",
    }
    source = {**source_core, "receipt_sha256": content_hash(source_core)}

    consequence = theory_move_consequence_receipt(
        {
            "context_hash": "context:a",
            "context_epoch": 2,
            "search_wave": 4,
            "wave_provider_calls": 0,
            "lineages": [
                {
                    "navigation": {
                        "trace": [
                            {
                                "decision": "request",
                                "capability_id": "show_indistinguishable_objects",
                                "receipt": {"receipt_id": "sha256:contrast"},
                            },
                            {
                                "decision": "agent_turn_failed",
                                "receipt": {"receipt_sha256": "sha256:timeout"},
                            },
                        ]
                    }
                }
            ],
        },
        source,
    )

    assert consequence["status"] == "executed_as_planned"
    assert consequence["observed_move_modes"] == ["current_context"]
    assert consequence["evidence_refs"] == ["sha256:contrast", "sha256:timeout"]


def test_late_synthesis_cannot_mix_routes_or_drop_requests():
    synthesis_input = lineage_synthesis_input(_navigation())
    formula_id = synthesis_input["formula_requests"][0]["request_id"]
    language_id = synthesis_input["theory_language_requests"][0]["request_id"]
    common = {
        "rationale": "Choose one executable route.",
        "next_discriminator": "Replay the selected route.",
        "kill_condition": "The selected route adds no distinction.",
        "program_ids": [],
        "next_discriminator_request_ids": [],
    }
    with pytest.raises(ValueError, match="only formula"):
        validate_lineage_synthesis_decision(
            synthesis_input,
            {
                **common,
                "route": "admit_formulas",
                "selected_request_ids": [formula_id, language_id],
                "deferred_request_ids": [],
                "next_discriminator_request_ids": [formula_id, language_id],
            },
        )
    with pytest.raises(ValueError, match="partition"):
        validate_lineage_synthesis_decision(
            synthesis_input,
            {
                **common,
                "route": "defer_all",
                "selected_request_ids": [],
                "deferred_request_ids": [formula_id],
                "next_discriminator_request_ids": [],
            },
        )


def test_unchanged_context_cannot_discard_a_required_request():
    synthesis_input = lineage_synthesis_input(_navigation())
    formula_id = synthesis_input["formula_requests"][0]["request_id"]
    language_id = synthesis_input["theory_language_requests"][0]["request_id"]

    with pytest.raises(ValueError, match="cannot consume deferred requests"):
        validate_lineage_synthesis_decision(
            synthesis_input,
            {
                "route": "continue_search",
                "selected_request_ids": [],
                "deferred_request_ids": [formula_id, language_id],
                "program_ids": [],
                "next_discriminator_request_ids": [formula_id],
                "rationale": "Continue while relying on a discarded coordinate.",
                "next_discriminator": "Compose the deferred coordinate.",
                "kill_condition": "The composition adds no prediction.",
            },
        )


def test_late_objective_review_binds_programs_without_self_granting_authority():
    navigation = {
        "context_hash": "context:a",
        "context_epoch": 2,
        "finalists": [
            {
                "theory_program": {
                    "program_id": "theory-program:a",
                    "context_hash": "context:a",
                },
                "prediction_profile": {"joint_countermodel_count": 1},
                "residual_information_yield": {"information_per_cost": 0.25},
                "structural_baseline": {"status": "not_forced"},
                "navigator_rationale": "Two coordinates make an external prediction.",
            }
        ],
        "isolation_receipt": {"receipt_sha256": "isolation:a"},
    }
    objective = {
        "schema": "leanmill.frontier_objective_contract.v1",
        "instruction": "Invent a coordinate whose prediction leaves the seed chart.",
        "review_stage": "post_lineage_freeze_pre_boundary",
        "authority": "independent_leaf_choice_host_receipt_validation",
    }
    synthesis_input = lineage_synthesis_input(
        navigation, objective_contract=objective
    )
    frozen = synthesis_input["frozen_programs"][0]
    assert frozen["prediction_profile"]["joint_countermodel_count"] == 1
    assert frozen["residual_information_yield"]["information_per_cost"] == 0.25

    receipt = validate_lineage_synthesis_decision(
        synthesis_input,
        {
            "route": "continue_search",
            "selected_request_ids": [],
            "deferred_request_ids": [],
            "program_ids": ["theory-program:a"],
            "next_discriminator_request_ids": [],
            "rationale": "The program remains inside the seed chart.",
            "next_discriminator": "Author and compose a new coordinate.",
            "kill_condition": "No typed coordinate separates a host-shown pair.",
        },
    )

    assert receipt["route"] == "continue_search"
    assert receipt["program_ids"] == ["theory-program:a"]
    assert receipt["authority"] == "agent_choice_host_validated"


def test_boundary_route_rejects_predictions_already_refuted_in_seed_context():
    objective = {
        "schema": "leanmill.frontier_objective_contract.v1",
        "instruction": "Find a prediction that survives the seed chart.",
        "review_stage": "post_lineage_freeze_pre_boundary",
        "authority": "independent_leaf_choice_host_receipt_validation",
    }
    synthesis_input = lineage_synthesis_input(
        {
            "context_hash": "context:a",
            "context_epoch": 0,
            "finalists": [
                {
                    "theory_program": {"program_id": "theory-program:a"},
                    "prediction_profile": {
                        "predictions": [
                            {
                                "prediction_formula_id": "formula:a",
                                "chart_status": "refuted_in_context",
                            }
                        ]
                    },
                }
            ],
        },
        objective_contract=objective,
    )

    decision = {
        "route": "proceed_boundary",
        "selected_request_ids": [],
        "deferred_request_ids": [],
        "program_ids": ["theory-program:a"],
        "next_discriminator_request_ids": [],
        "rationale": "Spend boundary budget.",
        "next_discriminator": "Recheck the prediction.",
        "kill_condition": "A countermodel appears.",
    }
    with pytest.raises(ValueError, match="unresolved by the seed context"):
        validate_lineage_synthesis_decision(synthesis_input, decision)



def test_late_objective_review_can_continue_when_no_lineage_froze_a_program():
    objective = {
        "schema": "leanmill.frontier_objective_contract.v1",
        "instruction": "Compose authored coordinates into an external prediction.",
        "review_stage": "post_lineage_freeze_pre_boundary",
        "authority": "independent_leaf_choice_host_receipt_validation",
    }
    synthesis_input = lineage_synthesis_input(
        {
            "context_hash": "context:a",
            "context_epoch": 0,
            "finalists": [],
            "isolation_receipt": {"receipt_sha256": "isolation:a"},
        },
        objective_contract=objective,
    )

    receipt = validate_lineage_synthesis_decision(
        synthesis_input,
        {
            "route": "continue_search",
            "selected_request_ids": [],
            "deferred_request_ids": [],
            "program_ids": [],
            "next_discriminator_request_ids": [],
            "rationale": "No lineage froze a program that could meet the objective.",
            "next_discriminator": "Author a second independent coordinate.",
            "kill_condition": "No witnessed contrast supports another coordinate.",
        },
    )

    assert receipt["route"] == "continue_search"
    assert receipt["program_ids"] == []

    with pytest.raises(ValueError, match="bind at least one frozen program"):
        validate_lineage_synthesis_decision(
            synthesis_input,
            {
                "route": "proceed_boundary",
                "selected_request_ids": [],
                "deferred_request_ids": [],
                "program_ids": [],
                "next_discriminator_request_ids": [],
                "rationale": "Spend boundary budget.",
                "next_discriminator": "Replay larger carriers.",
                "kill_condition": "A larger carrier refutes the target.",
            },
        )


def test_cross_epoch_boundary_feedback_remains_visible_without_source_program():
    objective = {
        "schema": "leanmill.frontier_objective_contract.v1",
        "instruction": "Change representation after the prior boundary result.",
        "review_stage": "post_lineage_freeze_pre_boundary",
        "authority": "independent_leaf_choice_host_receipt_validation",
    }
    feedback_core = {
        "schema": "leanmill.boundary_search_feedback.v1",
        "context_hash": "context:source",
        "context_epoch": 1,
        "program_ids": ["theory-program:source"],
        "prediction_outcomes": [],
        "route": "continue_search",
    }
    feedback = {
        **feedback_core,
        "receipt_sha256": content_hash(feedback_core),
    }

    synthesis_input = lineage_synthesis_input(
        {
            "context_hash": "context:successor",
            "context_epoch": 2,
            "finalists": [],
            "objective_review_history": [feedback],
        },
        objective_contract=objective,
    )

    assert synthesis_input["frozen_programs"] == []
    assert synthesis_input["objective_review_history"] == [feedback]
    assert synthesis_input["boundary_stage"] == {
        "status": "completed_evidence_attached",
        "admission_semantics": "authorizes_discriminating_tests_not_outer_success",
        "capabilities": [
            "larger_carrier_countermodel_search",
            "formal_verification",
            "post_freeze_literature_review",
        ],
        "feedback_receipt_sha256s": [feedback["receipt_sha256"]],
    }


def test_stale_requests_are_visible_but_not_selectable_in_successor_context():
    navigation = _navigation()
    navigation["context_hash"] = "context:successor"
    navigation["context_epoch"] = 3
    synthesis_input = lineage_synthesis_input(
        navigation,
        objective_contract={"schema": "leanmill.frontier_objective_contract.v1"},
    )

    assert not synthesis_input["formula_requests"]
    assert not synthesis_input["theory_language_requests"]
    assert set(synthesis_input["archived_stale_request_ids"]) == {
        navigation["expansion_proposals"][0]["request_id"],
        "language:b",
    }
    assert not lineage_request_matches_context(
        navigation["expansion_proposals"][0],
        context_hash="context:successor",
        context_epoch=3,
    )
