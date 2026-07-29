from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from ztare.leanmill.adapters.binary_linear_code import (
    ADAPTER_ID,
    BinaryGeneratorMatrix,
    build_evidence_context,
    binary_witness_construction_interface,
    canonical_row_basis,
    exact_minimum_distance,
    extend_with_parity,
    gf2_rank_with_dependency,
    normalize_binary_generator_candidate,
    preflight_blueprint,
    quasicyclic_generator_matrix,
    theory_task_capabilities,
    verify_binary_linear_code,
    verify_binary_generator_candidate,
)
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.theory_ir import SortDecl, TheorySignature


REPO = Path(__file__).resolve().parents[1]


def _target_config(*, minimum_distance: int = 14) -> dict:
    return {
        "construction_target": {
            "schema": "leanmill.binary_linear_code_target_config.v1",
            "field_order": 2,
            "length": 50,
            "dimension": 20,
            "minimum_distance": minimum_distance,
            "max_nonzero_messages": 2**20 - 1,
            "target_snapshot_sha256": "a" * 64,
        }
    }


def _campaign_config(*, minimum_distance: int = 14) -> dict:
    return {
        **_target_config(minimum_distance=minimum_distance),
        "evidence_panel": {
            "schema": "leanmill.binary_linear_code_evidence_panel.v1",
            "field_order": 1,
            "completeness_scope": "declared_control_panel_only",
            "completeness_ref": "fixture:binary-code-control-panel",
            "objects": [
                {
                    "object_id": "control:current",
                    "stratum_id": "matched_positive",
                    "payload": {"artifact_ref": "fixture:current"},
                },
                {
                    "object_id": "control:perturbed",
                    "stratum_id": "matched_negative",
                    "payload": {"artifact_ref": "fixture:perturbed"},
                },
            ],
            "hypotheses": [
                {
                    "hypothesis_id": "property:rank-20",
                    "satisfied_object_ids": [
                        "control:current",
                        "control:perturbed",
                    ],
                    "anonymous_shape": {
                        "kind": "exact_binary_code_property",
                        "complexity": 1,
                    },
                    "payload": {"checker_ref": "binary:rank"},
                },
                {
                    "hypothesis_id": "property:distance-13",
                    "satisfied_object_ids": ["control:current"],
                    "anonymous_shape": {
                        "kind": "exact_binary_code_property",
                        "complexity": 1,
                    },
                    "payload": {"checker_ref": "binary:distance"},
                },
            ],
        },
    }


def _current_50_20_code() -> BinaryGeneratorMatrix:
    # Grassl's current Chubenko--Kurz degree-five QC construction, with each
    # polynomial represented by its coefficient mask in F2[x]/(x^10 - 1).
    return quasicyclic_generator_matrix(
        (
            (
                1,
                0,
                sum(1 << exponent for exponent in (9, 8, 7, 6, 5, 3, 2, 1)),
                sum(1 << exponent for exponent in (9, 3, 2, 1)),
                sum(1 << exponent for exponent in (9, 6, 3)),
            ),
            (
                0,
                1,
                sum(1 << exponent for exponent in (8, 7, 6, 1, 0)),
                sum(1 << exponent for exponent in (6, 5, 3, 1)),
                sum(1 << exponent for exponent in (9, 8, 3)),
            ),
        ),
        block_size=10,
    )


def test_generator_wire_is_strict_and_row_basis_is_canonical() -> None:
    matrix = BinaryGeneratorMatrix(length=4, dimension=2, rows=(0b0011, 0b0110))
    assert BinaryGeneratorMatrix.from_json(matrix.to_json()) == matrix
    assert canonical_row_basis(matrix).rows == (0b0101, 0b0110)

    noncanonical = copy.deepcopy(matrix.to_json())
    noncanonical["rows_hex"][0] = "3"
    with pytest.raises(ValueError, match="canonical"):
        BinaryGeneratorMatrix.from_json(noncanonical)


def test_rank_dependency_and_low_weight_witness_are_replayable() -> None:
    rank, dependency = gf2_rank_with_dependency((0b0011, 0b0011))
    assert rank == 1
    assert dependency == 0b11

    rank_after_early_dependency, dependency = gf2_rank_with_dependency(
        (0, 0b0001, 0b0010)
    )
    assert rank_after_early_dependency == 2
    assert dependency == 0b001

    matrix = BinaryGeneratorMatrix(length=4, dimension=2, rows=(0b0011, 0b1100))
    result = verify_binary_linear_code(
        matrix,
        required_rank=2,
        required_minimum_distance=3,
    )
    assert result["status"] == "low_weight_counterexample"
    assert result["distance_replay"]["minimum_distance"] == 2
    assert result["distance_replay"]["codeword_hex"] in {"0x3", "0xc"}


def test_message_budget_refusal_has_no_distance_credit() -> None:
    matrix = BinaryGeneratorMatrix(length=4, dimension=2, rows=(0b0011, 0b1100))
    result = exact_minimum_distance(matrix, max_nonzero_messages=2)
    assert result.status == "unavailable_message_budget"
    assert result.minimum_distance is None
    assert result.examined_nonzero_messages == 0


def test_grassl_50_20_13_and_derived_51_20_14_controls() -> None:
    current = _current_50_20_code()
    assert (current.length, current.dimension) == (50, 20)
    current_result = verify_binary_linear_code(
        current,
        required_rank=20,
        required_minimum_distance=13,
    )
    assert current_result["status"] == "satisfied"
    assert current_result["observed_rank"] == 20
    assert current_result["distance_replay"]["minimum_distance"] == 13
    assert current_result["distance_replay"]["examined_nonzero_messages"] == 2**20 - 1

    extended = extend_with_parity(current)
    extended_result = verify_binary_linear_code(
        extended,
        required_rank=20,
        required_minimum_distance=14,
    )
    assert (extended.length, extended.dimension) == (51, 20)
    assert extended_result["status"] == "satisfied"
    assert extended_result["distance_replay"]["minimum_distance"] == 14


def test_rank_deficiency_precedes_distance_claim() -> None:
    matrix = BinaryGeneratorMatrix(length=4, dimension=2, rows=(0b0011, 0b0011))
    result = verify_binary_linear_code(
        matrix,
        required_rank=2,
        required_minimum_distance=2,
    )
    assert result["status"] == "rank_deficient"
    assert result["dependency_message_hex"] == "0x3"
    assert result["distance_replay"]["status"] == "not_run_rank_deficient"
    assert result["distance_replay"]["examined_nonzero_messages"] == 0
    assert result["claim_scope"] == (
        "candidate_replay_only_no_existence_or_nonexistence_claim"
    )


def test_frozen_control_replay_is_content_bound_and_recomputes() -> None:
    path = REPO / (
        "research_areas/pre_registrations/"
        "axiompack_binary_linear_code_frontier_v1_20260717/"
        "binary_code_control_replay.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    supplied = payload.pop("receipt_sha256")
    assert supplied == content_hash(payload)

    current = BinaryGeneratorMatrix.from_json(payload["current_matrix"])
    extended = BinaryGeneratorMatrix.from_json(payload["extended_matrix"])
    perturbed = BinaryGeneratorMatrix.from_json(payload["perturbation"]["matrix"])
    assert verify_binary_linear_code(
        current, required_rank=20, required_minimum_distance=13
    ) == payload["current_verification"]
    assert verify_binary_linear_code(
        extended, required_rank=20, required_minimum_distance=14
    ) == payload["extended_verification"]
    assert verify_binary_linear_code(
        perturbed, required_rank=20, required_minimum_distance=13
    ) == payload["perturbation"]["verification"]


def test_public_construction_interface_drives_registered_callbacks() -> None:
    current = _current_50_20_code()
    interface = binary_witness_construction_interface(
        length=50,
        dimension=20,
        minimum_distance=13,
        target_snapshot_sha256="a" * 64,
        max_nonzero_messages=2**20 - 1,
        target_config_sha256="b" * 64,
    )
    normalizer = {"adapter_id": ADAPTER_ID, **interface["normalizer"]}
    verifier = {"adapter_id": ADAPTER_ID, **interface["verifier"]}
    normalized = normalize_binary_generator_candidate(
        descriptor=normalizer,
        artifact=current.to_json(),
        predicate_ir=interface["predicate_ir"],
        witness_schema=interface["witness_schema"],
    )
    result = verify_binary_generator_candidate(
        descriptor=verifier,
        normalized_artifact=normalized,
        predicate_ir=interface["predicate_ir"],
        witness_schema=interface["witness_schema"],
    )
    assert result["outcome"] == "accepted"
    assert result["observed"]["distance_replay"]["minimum_distance"] == 13
    assert interface["discharge_policy"] == (
        "construction_artifact_ratification_required"
    )

    crossed = copy.deepcopy(normalizer)
    crossed["adapter_id"] = "another_adapter.v1"
    with pytest.raises(ValueError, match="descriptor"):
        normalize_binary_generator_candidate(
            descriptor=crossed,
            artifact=current.to_json(),
            predicate_ir=interface["predicate_ir"],
            witness_schema=interface["witness_schema"],
        )


def test_task_catalog_interface_is_bound_to_the_full_target_config() -> None:
    config = _target_config()
    catalog = theory_task_capabilities(adapter_config=config)
    assert len(catalog) == 1
    interface = catalog[0]["interface"]
    assert interface["target_config_sha256"] == content_hash(config)
    assert interface["predicate_ir"]["required_minimum_distance"] == 14
    assert interface["discharge_policy"] == (
        "construction_artifact_ratification_required"
    )

    changed = theory_task_capabilities(
        adapter_config=_target_config(minimum_distance=13)
    )[0]["interface"]
    assert changed["interface_sha256"] != interface["interface_sha256"]


def test_campaign_panel_is_exact_only_at_its_declared_scope() -> None:
    signature = TheorySignature(
        name="BinaryConstructionObservation",
        sorts=(SortDecl("Observation"),),
    )
    config = _campaign_config()
    preflight = preflight_blueprint(
        signature,
        adapter_config=config,
        formula_grammar={"kind": "declared_executable_hypothesis_panel"},
        strata=({"stratum_id": "declared_controls"},),
    )
    assert preflight["complete_census_available"] is True
    assert preflight["completeness_scope"] == "declared_control_panel_only"
    assert "no completeness claim over binary linear codes" in preflight[
        "claim_boundary"
    ]
    assert preflight["target_config_sha256"] == content_hash(config)

    context = build_evidence_context(
        signature,
        adapter_config=config,
        strata=({"stratum_id": "declared_controls"},),
    )
    assert context.adapter_id == ADAPTER_ID
    assert context.complete is True
    assert context.object_ids == ("control:current", "control:perturbed")
    assert context.extent_model_ids(("property:distance-13",)) == (
        "control:current",
    )

    crossed = copy.deepcopy(config)
    crossed["search_hint"] = "host-selected-polynomial"
    with pytest.raises(ValueError, match="configuration fields"):
        preflight_blueprint(
            signature,
            adapter_config=crossed,
            formula_grammar={"kind": "declared_executable_hypothesis_panel"},
            strata=({"stratum_id": "declared_controls"},),
        )


def test_frozen_campaign_adapter_config_preflights() -> None:
    path = REPO / (
        "research_areas/pre_registrations/"
        "axiompack_binary_linear_code_frontier_v1_20260717/"
        "campaign_adapter_config.json"
    )
    config = json.loads(path.read_text(encoding="utf-8"))
    signature = TheorySignature(
        name="BinaryConstructionObservation",
        sorts=(SortDecl("Observation"),),
    )
    preflight = preflight_blueprint(
        signature,
        adapter_config=config,
        formula_grammar={"kind": "declared_executable_hypothesis_panel"},
        strata=({"stratum_id": "declared_controls"},),
    )
    context = build_evidence_context(
        signature,
        adapter_config=config,
        strata=({"stratum_id": "declared_controls"},),
    )
    assert preflight["formula_count"] == 6
    assert preflight["labeled_model_count"] == 3
    assert preflight["truth_cell_count"] == 18
    assert context.formula_ids == (
        "property:full-rank-20",
        "property:length-50",
        "property:minimum-distance-at-least-13",
        "property:minimum-distance-at-least-14",
        "trace:one-coordinate-perturbation-of-current",
        "trace:parity-extension-of-current",
    )
