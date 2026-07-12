from __future__ import annotations

import json
import pytest
from jsonschema import Draft202012Validator

from ztare.leanmill.theory_lineage_synthesis import (
    formula_lineage_request_id,
    lineage_synthesis_input,
    lineage_synthesis_output_schema,
    validate_lineage_synthesis_decision,
)


def _navigation():
    formula = {
        "lineage_id": "lineage:a",
        "proposal": {
            "source_context_hash": "context:a",
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
                "request": {"request_id": "language:b"},
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

    with pytest.raises(ValueError, match="unresolved by the seed context"):
        validate_lineage_synthesis_decision(
            synthesis_input,
            {
                "route": "proceed_boundary",
                "selected_request_ids": [],
                "deferred_request_ids": [],
                "program_ids": ["theory-program:a"],
                "next_discriminator_request_ids": [],
                "rationale": "Spend boundary budget.",
                "next_discriminator": "Recheck the prediction.",
                "kill_condition": "A countermodel appears.",
            },
        )


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
