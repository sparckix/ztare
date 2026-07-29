from __future__ import annotations

import copy

import pytest
from jsonschema import ValidationError

from ztare.common.schema_routes import (
    audit_project_schema_routes,
    consequence_contract,
    validate_schema_route_registry,
)
from ztare.common.target_predicate import (
    RetrievedExample,
    TargetPredicateAdjudication,
    TargetPredicateContract,
    TargetPredicateReceipt,
)
from ztare.leanmill import target_predicate_replay
from ztare.leanmill.adapters import generic_fol_finite
from ztare.leanmill.frontier_campaign_runner import (
    _post_freeze_research_disposition,
)
from ztare.leanmill.theory_interpretation import compose_theory_interpretation
from ztare.leanmill.theory_ir import content_hash


def _contract() -> TargetPredicateContract:
    return TargetPredicateContract(
        contract_id="objective-epoch-7:derived-map-separation",
        owner="fixture prior-art boundary",
        lifecycle_scope="objective-epoch-7",
        context_hash="c" * 64,
        adapter_id="generic_fol_finite.v1",
        evaluator_capability="target_predicate_evaluator",
        predicate_ir={
            "kind": "derived_map_separation",
            "left_map": "source_then_extract",
            "right_map": "reconstructed_then_extract",
            "quantifier": "exists_normalized_probe",
        },
        input_schema={
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
            "required": ["modulus", "coefficients", "probe"],
            "properties": {
                "modulus": {"type": "integer", "minimum": 2},
                "coefficients": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["mixed"],
                    "properties": {"mixed": {"type": "integer"}},
                },
                "probe": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["x", "y", "z"],
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "z": {"type": "integer"},
                    },
                },
            },
        },
    )


def _example(*, mixed: int = 1) -> RetrievedExample:
    # Adapter fixture for the recovered affine construction. Its vocabulary and
    # arithmetic stay out of the common contract/replay implementation.
    return RetrievedExample(
        example_id=f"published-affine-example:mixed-{mixed}",
        source_id="published-construction-2008",
        source_url="https://example.test/published-construction",
        source_content_sha256="a" * 64,
        source_locator="Example 4.10, normalized test row",
        adapter_id="generic_fol_finite.v1",
        normalized_input={
            "modulus": 2,
            "coefficients": {"mixed": mixed},
            "probe": {"x": 1, "y": 0, "z": 1},
        },
        evidence_refs=("source:published-construction-2008#example-4.10",),
    )


def _affine_fixture_evaluator(*, contract, retrieved_example):
    assert contract["predicate_ir"]["kind"] == "derived_map_separation"
    value = retrieved_example["normalized_input"]
    modulus = value["modulus"]
    mixed = value["coefficients"]["mixed"]
    probe = value["probe"]
    source_then_extract = (
        probe["y"] + mixed * probe["x"] * probe["z"]
    ) % modulus
    reconstructed_then_extract = probe["y"] % modulus
    if source_then_extract != reconstructed_then_extract:
        return {
            "schema": "ztare-target-predicate-adjudication-v1",
            "outcome": "overlap",
            "reason_code": "retrieved_example_witnesses_target",
            "reason": "the normalized source construction separates the frozen maps",
            "witness": {
                "source_value": source_then_extract,
                "reconstructed_value": reconstructed_then_extract,
                "probe": probe,
            },
            "evidence_refs": ["adapter-check:derived-map-separation"],
        }
    return {
        "schema": "ztare-target-predicate-adjudication-v1",
        "outcome": "unknown",
        "reason_code": "retrieved_example_not_a_witness",
        "reason": "this example does not separate the frozen maps",
        "witness": {
            "source_value": source_then_extract,
            "reconstructed_value": reconstructed_then_extract,
        },
        "evidence_refs": [],
    }


def _packet_with_contract() -> dict:
    contract = _contract()
    return {
        "schema": "leanmill.post_freeze_result_packet.v4",
        "packet_sha256": "packet:target-predicate-fixture",
        "context_hash": contract.context_hash,
        "formulas": [
            {"role": "premise", "formula_id": "f1"},
            {"role": "target", "formula_id": "f2"},
        ],
        "structural_source_search": {
            "operation_coordinate_variants": [],
            "finite_witnesses": [],
        },
        "unrestricted_lean": {"status": "proved_attributed"},
        "target_predicate_contract": {
            **contract.to_dict(),
            "contract_sha256": contract.sha256,
        },
    }


def _review() -> dict:
    return {
        "novelty_assessment": "not_located_in_bounded_review",
        "formula_matches": [
            {
                "formula_id": formula_id,
                "match_status": "not_found",
                "equivalence_kind": "none",
                "coordinate_variant_id": None,
            }
            for formula_id in ("f1", "f2")
        ],
        "implication_prior_art": [{
            "source_title": "Published construction",
            "source_url": "https://example.test/published-construction",
            "relationship": "supplies a normalized example family",
            "evidence": "the displayed construction was normalized for replay",
        }],
        "recognized_theory_connections": [],
        "finite_witness_matches": [],
        "mechanism_analysis": {},
        "summary": "fixture",
        "limitations": ["bounded"],
        "next_checks": ["expert review"],
    }


def test_registered_replay_turns_retrieved_construction_into_overlap_state(
    tmp_path, monkeypatch
):
    monkeypatch.setitem(
        generic_fol_finite.CAPABILITIES,
        "target_predicate_evaluator",
        _affine_fixture_evaluator,
    )
    project = tmp_path / "project"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)

    receipt = target_predicate_replay.evaluate_target_predicate_consequence(
        _contract(), _example(), receipts_dir=workspace
    )
    assert receipt.adjudication.outcome == "overlap"
    assert receipt.authority == "registered_adapter_prior_art_overlap_only"
    before = audit_project_schema_routes(project)
    assert any(
        row.get("contract_id") == "target_predicate_replay_outcome_totality.v1"
        and row.get("kind") == "produced_outcome_without_state_transition"
        for row in before["errors"]
    )

    transition = target_predicate_replay.consume_target_predicate_consequence(
        receipt.to_dict(), receipts_dir=workspace
    )
    assert transition["target_state"] == "prior_art_overlap_detected"
    assert transition["novelty_status"] == "overlap_detected"
    after = audit_project_schema_routes(project)
    assert not any(
        row.get("contract_id") == "target_predicate_replay_outcome_totality.v1"
        for row in after["errors"]
    )
    assert validate_schema_route_registry() == ()


def test_nonwitness_stays_unknown_and_cannot_mint_corpus_negative(monkeypatch):
    monkeypatch.setitem(
        generic_fol_finite.CAPABILITIES,
        "target_predicate_evaluator",
        _affine_fixture_evaluator,
    )
    receipt = target_predicate_replay.evaluate_target_predicate_consequence(
        _contract(), _example(mixed=0)
    )
    assert receipt.adjudication.outcome == "unknown"
    transition = target_predicate_replay.consume_target_predicate_consequence(receipt)
    assert transition["target_state"] == "prior_art_target_status_unknown"
    assert transition["novelty_status"] == "blocked_by_unknown"
    with pytest.raises(ValueError, match="overlap or unknown"):
        TargetPredicateAdjudication(
            outcome="no_overlap",
            reason_code="bounded_search_negative",
            reason="not found",
            witness=None,
        )
    with pytest.raises(ValueError, match="corpus completeness"):
        TargetPredicateContract(
            **{
                **_contract().__dict__,
                "claim_scope": "no_prior_art_exists",
            }
        )


def test_receipt_binds_exact_contract_and_retrieved_source(monkeypatch):
    monkeypatch.setitem(
        generic_fol_finite.CAPABILITIES,
        "target_predicate_evaluator",
        _affine_fixture_evaluator,
    )
    receipt = target_predicate_replay.evaluate_target_predicate_consequence(
        _contract(), _example()
    )
    stored = receipt.to_dict()
    assert TargetPredicateReceipt.from_dict(stored).sha256 == receipt.sha256

    tampered = copy.deepcopy(stored)
    tampered["retrieved_example"]["source_locator"] = "different source row"
    with pytest.raises(ValueError, match="example identity mismatch"):
        TargetPredicateReceipt.from_dict(tampered)


def test_consumer_replays_adapter_and_rejects_changed_adjudication(monkeypatch):
    monkeypatch.setitem(
        generic_fol_finite.CAPABILITIES,
        "target_predicate_evaluator",
        _affine_fixture_evaluator,
    )
    receipt = target_predicate_replay.evaluate_target_predicate_consequence(
        _contract(), _example()
    )

    def unavailable_afterward(*, contract, retrieved_example):
        return {
            "schema": "ztare-target-predicate-adjudication-v1",
            "outcome": "unknown",
            "reason_code": "replay_input_unavailable",
            "reason": "the normalized replay dependency is unavailable",
            "witness": None,
            "evidence_refs": [],
        }

    monkeypatch.setitem(
        generic_fol_finite.CAPABILITIES,
        "target_predicate_evaluator",
        unavailable_afterward,
    )
    with pytest.raises(ValueError, match="replay differs"):
        target_predicate_replay.consume_target_predicate_consequence(receipt)


def test_contract_input_schema_and_adapter_identity_are_enforced(monkeypatch):
    monkeypatch.setitem(
        generic_fol_finite.CAPABILITIES,
        "target_predicate_evaluator",
        _affine_fixture_evaluator,
    )
    invalid_input = _example().to_dict()
    invalid_input["normalized_input"]["probe"].pop("z")
    with pytest.raises(ValidationError, match="required property"):
        target_predicate_replay.evaluate_target_predicate_consequence(
            _contract(), invalid_input
        )

    mismatched = _example().to_dict()
    mismatched["adapter_id"] = "magma_equational.v1"
    with pytest.raises(ValueError, match="require one adapter"):
        target_predicate_replay.evaluate_target_predicate_consequence(
            _contract(), mismatched
        )

    transition = consequence_contract(
        "target_predicate_replay_outcome_totality.v1"
    )
    assert {row.outcome for row in transition.outcomes} == {"overlap", "unknown"}


def test_missing_registered_capability_is_typed_unknown(monkeypatch):
    monkeypatch.delitem(
        generic_fol_finite.CAPABILITIES,
        "target_predicate_evaluator",
        raising=False,
    )
    receipt = target_predicate_replay.evaluate_target_predicate_consequence(
        _contract(), _example()
    )
    assert receipt.adjudication.outcome == "unknown"
    assert receipt.adjudication.reason_code == "evaluator_capability_unavailable"
    assert target_predicate_replay.consume_target_predicate_consequence(receipt)[
        "novelty_status"
    ] == "blocked_by_unknown"


def test_review_first_fire_aggregates_source_bound_examples(monkeypatch, tmp_path):
    monkeypatch.setitem(
        generic_fol_finite.CAPABILITIES,
        "target_predicate_evaluator",
        _affine_fixture_evaluator,
    )
    packet = _packet_with_contract()
    payload = {
        "schema": "leanmill.retrieved_target_examples.v1",
        "contract_sha256": _contract().sha256,
        "examples": [_example().to_dict()],
    }
    summary = target_predicate_replay.replay_review_target_predicates(
        packet,
        _review(),
        payload,
        receipts_dir=tmp_path,
    )
    assert summary is not None
    assert summary["outcome"] == "overlap"
    assert summary["receipt_count"] == 1
    assert summary["transitions"][0]["target_state"] == (
        "prior_art_overlap_detected"
    )


def test_failed_batch_replay_does_not_leave_orphaned_consequence(
    monkeypatch, tmp_path
):
    calls = 0

    def changing_evaluator(*, contract, retrieved_example):
        nonlocal calls
        calls += 1
        if calls == 1:
            return _affine_fixture_evaluator(
                contract=contract, retrieved_example=retrieved_example
            )
        return {
            "schema": "ztare-target-predicate-adjudication-v1",
            "outcome": "unknown",
            "reason_code": "changed_replay",
            "reason": "the second evaluation changed",
            "witness": None,
            "evidence_refs": [],
        }

    monkeypatch.setitem(
        generic_fol_finite.CAPABILITIES,
        "target_predicate_evaluator",
        changing_evaluator,
    )
    payload = {
        "schema": "leanmill.retrieved_target_examples.v1",
        "contract_sha256": _contract().sha256,
        "examples": [_example().to_dict()],
    }
    workspace = tmp_path / "workspace"
    summary = target_predicate_replay.replay_review_target_predicates(
        _packet_with_contract(), _review(), payload, receipts_dir=workspace
    )
    assert summary is not None and summary["outcome"] == "unknown"
    assert summary["receipt_count"] == 0
    consequence_path = workspace / "consequence_delivery.jsonl"
    assert not consequence_path.exists()


def test_contract_and_example_snapshot_mutable_inputs():
    predicate_ir = {"kind": "derived_map_separation", "steps": ["left"]}
    normalized = {
        "modulus": 2,
        "coefficients": {"mixed": 1},
        "probe": {"x": 1, "y": 0, "z": 1},
    }
    contract = TargetPredicateContract(
        **{
            **_contract().__dict__,
            "predicate_ir": predicate_ir,
        }
    )
    example = RetrievedExample(
        **{
            **_example().__dict__,
            "normalized_input": normalized,
        }
    )
    contract_sha = contract.sha256
    example_sha = example.sha256
    predicate_ir["steps"].append("right")
    normalized["probe"]["z"] = 0
    assert contract.sha256 == contract_sha
    assert example.sha256 == example_sha


def test_missing_review_replay_blocks_absence_but_overlap_changes_campaign_state(
    monkeypatch,
):
    monkeypatch.setitem(
        generic_fol_finite.CAPABILITIES,
        "target_predicate_evaluator",
        _affine_fixture_evaluator,
    )
    packet = _packet_with_contract()
    review = _review()

    unknown = target_predicate_replay.replay_review_target_predicates(
        packet, review, None
    )
    assert unknown is not None and unknown["outcome"] == "unknown"
    unknown_core = {
        "schema": "leanmill.post_freeze_interpretation.v1",
        "packet_sha256": packet["packet_sha256"],
        "finite_witness_host_checks": [],
        "target_predicate_replay": unknown,
        "review": review,
    }
    unknown_interpretation = compose_theory_interpretation(
        packet,
        {**unknown_core, "receipt_sha256": content_hash(unknown_core)},
    )
    assert unknown_interpretation["status"] == "inconclusive"
    assert unknown_interpretation["external_alignment"]["status"] == "unavailable"

    payload = {
        "schema": "leanmill.retrieved_target_examples.v1",
        "contract_sha256": _contract().sha256,
        "examples": [_example().to_dict()],
    }
    overlap = target_predicate_replay.replay_review_target_predicates(
        packet, review, payload
    )
    overlap_core = {
        **unknown_core,
        "target_predicate_replay": overlap,
    }
    overlap_literature = {
        **overlap_core,
        "receipt_sha256": content_hash(overlap_core),
    }
    overlap_interpretation = compose_theory_interpretation(
        packet, overlap_literature
    )
    alignment = overlap_interpretation["external_alignment"]
    assert overlap_interpretation["status"] == "mapped_to_recorded_knowledge"
    assert alignment["status"] == "target_overlap"
    assert alignment["origin_disposition"] == "retrieved_target_overlap"
    disposition = _post_freeze_research_disposition(
        overlap_literature, overlap_interpretation
    )
    assert disposition is not None
    assert disposition["recurrence_pressure"] is True
    assert disposition["typed_residual"] == (
        "distinguish_from_retrieved_target_overlap_or_change_objective"
    )
