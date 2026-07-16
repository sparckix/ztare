from __future__ import annotations

from itertools import product

import pytest

from ztare.leanmill.finite_model import (
    FiniteModel,
    classify_single_operation_equivalence,
)
from ztare.leanmill.frontier_interpretation import (
    validate_post_freeze_finite_witness_matches,
)
from ztare.leanmill.theory_interpretation import compose_theory_interpretation
from ztare.leanmill.theory_ir import (
    OperationSymbol,
    SortDecl,
    TheorySignature,
    content_hash,
)


def _ternary_signature() -> TheorySignature:
    return TheorySignature(
        name="Ternary",
        sorts=(SortDecl("S0"),),
        operations=(OperationSymbol("op0", ("S0", "S0", "S0"), "S0"),),
    )


def _model(function) -> FiniteModel:
    table = tuple(function(*arguments) for arguments in product(range(3), repeat=3))
    return FiniteModel(
        sort_sizes=(("S0", 3),),
        operations=(("op0", table),),
    )


def _swap01(value: int) -> int:
    return 1 if value == 0 else 0 if value == 1 else 2


def test_finite_term_fingerprint_catches_axiompack_f1_recurrence() -> None:
    published = _model(
        lambda a, b, c: _swap01(a) if b == 2 and c == 2 else a
    )
    finalist_one = _model(
        lambda a, b, c: _swap01(a) if b == 2 and c in {0, 1} else a
    )

    receipt = classify_single_operation_equivalence(
        _ternary_signature(), finalist_one, published
    )

    assert receipt["status"] == "completed"
    assert receipt["relation"] == "mutual_term_equivalent"
    assert receipt["scope"] == "finite_witness_only"
    assert receipt["candidate_from_reference_term"] is not None
    assert receipt["reference_from_candidate_term"] is not None
    assert "no theory, variety" in receipt["claim_boundary"]


def test_finite_operation_fingerprint_distinguishes_coordinate_and_term_scope() -> None:
    reference = _model(lambda a, b, c: a)
    coordinate_opposite = _model(lambda a, b, c: b)

    receipt = classify_single_operation_equivalence(
        _ternary_signature(), coordinate_opposite, reference
    )

    assert receipt["relation"] == "operation_coordinate_equivalent"
    assert receipt["graph_coordinate_permutation"][-1] == 3


def test_finite_operation_fingerprint_reports_typed_bound_unavailability() -> None:
    reference = _model(lambda a, b, c: a)

    receipt = classify_single_operation_equivalence(
        _ternary_signature(), reference, reference, max_relabelings=1
    )

    assert receipt["status"] == "unavailable"
    assert receipt["relation"] == "unavailable_bounds"


def _source_review_packet() -> tuple[dict, dict]:
    signature = _ternary_signature()
    candidate = _model(
        lambda a, b, c: _swap01(a) if b == 2 and c in {0, 1} else a
    )
    reference = _model(
        lambda a, b, c: _swap01(a) if b == 2 and c == 2 else a
    )
    packet_core = {
        "schema": "leanmill.post_freeze_result_packet.v4",
        "context_hash": "context:test",
        "boundary_result_sha256": "boundary:test",
        "governance_recheck_sha256": "governance:test",
        "formulas": [],
        "interpretation_context": {"signature": signature.to_json()},
        "structural_source_search": {
            "operation_coordinate_variants": [],
            "finite_witnesses": [
                {
                    "candidate_model_id": "model:f1",
                    "stratum_id": "carrier_size:3",
                    "model_sha256": candidate.content_hash(signature),
                    "carrier_size": 3,
                    "operation": {
                        "symbol": "op0",
                        "arity": 3,
                        "table": list(candidate.operation_map["op0"]),
                    },
                }
            ],
        },
        "bounded_context": {},
        "unrestricted_lean": {"status": "proved_attributed"},
    }
    packet = {**packet_core, "packet_sha256": content_hash(packet_core)}
    source_url = "https://example.test/differential-modes"
    review = {
        "status": "completed",
        "formula_matches": [],
        "implication_prior_art": [
            {
                "source_title": "Differential Modes",
                "source_url": source_url,
                "relationship": "Supplies the finite reference operation only.",
                "evidence": "The complete order-three operation is displayed.",
            }
        ],
        "recognized_theory_connections": [],
        "finite_witness_matches": [
            {
                "candidate_model_id": "model:f1",
                "source_title": "Differential Modes",
                "source_url": source_url,
                "source_operation": {
                    "carrier_size": 3,
                    "arity": 3,
                    "table": list(reference.operation_map["op0"]),
                },
                "claimed_relation": "mutual_term_equivalent",
                "scope": "finite_witness_only",
                "confidence": "high",
                "evidence": "Compare the two complete tables.",
            }
        ],
        "novelty_assessment": "not_located_in_bounded_review",
        "summary": "A finite component recurs; the implication remains unmapped.",
        "limitations": ["One finite algebra pair."],
        "next_checks": ["Audit the universal bridge."],
    }
    return packet, review


def test_post_freeze_host_mints_f1_finite_recurrence_check() -> None:
    packet, review = _source_review_packet()

    checks = validate_post_freeze_finite_witness_matches(packet, review)

    assert checks[0]["status"] == "verified"
    assert checks[0]["computed_relation"] == "mutual_term_equivalent"
    assert checks[0]["equivalence_receipt"]["scope"] == "finite_witness_only"


def test_post_freeze_host_rejects_unbound_source_table() -> None:
    packet, review = _source_review_packet()
    review["implication_prior_art"] = []

    checks = validate_post_freeze_finite_witness_matches(packet, review)

    assert checks[0]["status"] == "rejected"
    assert "absent from the source review" in checks[0]["reason"]


def test_finite_recurrence_cannot_promote_unmapped_implication() -> None:
    packet, review = _source_review_packet()
    checks = validate_post_freeze_finite_witness_matches(packet, review)
    receipt_core = {
        "packet_sha256": packet["packet_sha256"],
        "finite_witness_host_checks": checks,
        "review": review,
    }
    receipt = {**receipt_core, "receipt_sha256": content_hash(receipt_core)}

    interpretation = compose_theory_interpretation(packet, receipt)

    assert interpretation["external_alignment"]["status"] == "unresolved"
    assert interpretation["external_alignment"]["origin_disposition"] == (
        "recorded_components_unmapped_recombination"
    )
    recurrence = interpretation["external_alignment"]["structural_recurrence"]
    assert recurrence["status"] == "verified_finite_recurrence"
    assert "does not establish theory" in recurrence["claim_boundary"]

    forged = dict(receipt)
    forged["finite_witness_host_checks"] = [
        {**checks[0], "computed_relation": "exact_isomorphism"}
    ]
    forged_core = {
        key: value for key, value in forged.items() if key != "receipt_sha256"
    }
    forged["receipt_sha256"] = content_hash(forged_core)
    with pytest.raises(ValueError, match="host check|equivalence receipt"):
        compose_theory_interpretation(packet, forged)
