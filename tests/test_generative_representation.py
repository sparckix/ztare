from __future__ import annotations

import pytest

from ztare.leanmill.adapters.generic_fol_finite import (
    build_fixed_size_countermodel_finder,
    build_model_universe,
    compile_theory_language_expansion,
)
from ztare.leanmill.equational_formula_universe import EQUATIONAL_GRAMMAR_SCHEMA
from ztare.leanmill.finite_model import FiniteModel, evaluate_axiom
from ztare.leanmill.finite_theory_context import build_formal_theory_context
from ztare.leanmill.generative_representation import (
    CANDIDATE_SCHEMA,
    ISOMORPHISM_POLICY,
    admit_materialized_generative_representation,
    validate_materialized_generative_candidate,
)
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Binder,
    Formula,
    OperationSymbol,
    SortDecl,
    Term,
    TheorySignature,
    content_hash,
)


def _surface():
    signature = TheorySignature(
        name="UnaryRepresentationFixture",
        sorts=(SortDecl("S"),),
        operations=(OperationSymbol("step", ("S",), "S"),),
    )
    x = Term.var("x")
    involutive = AxiomFormula(
        "step_involutive",
        Formula.forall(
            (Binder("x", "S"),),
            Formula.eq(Term.app("step", Term.app("step", x)), x),
        ),
    )
    fixed = AxiomFormula(
        "step_fixed",
        Formula.forall(
            (Binder("x", "S"),), Formula.eq(Term.app("step", x), x)
        ),
    )
    return signature, involutive, fixed


def _context(size: int):
    signature, involutive, fixed = _surface()
    universe = build_model_universe(
        signature,
        strata=({"sort_sizes": {"S": size}},),
        base_axioms=(involutive,),
    )
    return build_formal_theory_context(
        signature=signature,
        formulas=(fixed,),
        universe=universe,
        base_axioms=(involutive,),
    )


def _candidate(source, *, gap_id="adapter-gap:fixture", request_id="request:fixture"):
    signature = source.signature
    source_models = {
        row.model_id: row.model.to_json() for row in source.universe.models
    }
    generated = FiniteModel(
        sort_sizes=(("S", 2),), operations=(("step", (1, 0)),)
    )
    core = {
        "schema": CANDIDATE_SCHEMA,
        "request_id": request_id,
        "gap_id": gap_id,
        "context_hash": source.context_hash,
        "codec_id": "fixture:materialized-involution-codec",
        "raw_signature": signature.to_json(),
        "abstract_signature": signature.to_json(),
        "raw_base_axioms": [row.to_json() for row in source.base_axioms],
        "source_alpha_models": source_models,
        "source_lowered_models": source_models,
        "generated_batches": [
            {
                "raw_sort_sizes": {"S": 2},
                "abstract_sort_sizes": {"S": 2},
                "models": [
                    {
                        "abstract_model": generated.to_json(),
                        "raw_model": generated.to_json(),
                    }
                ],
                "generator_ref": "fixture:complete-size-two-involution-classes",
            }
        ],
        "generator_provenance_refs": ["fixture:generator-check"],
        "max_relabelings": 720,
        "isomorphism_policy": ISOMORPHISM_POLICY,
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _resign(row):
    core = {key: value for key, value in row.items() if key != "receipt_sha256"}
    return {**core, "receipt_sha256": content_hash(core)}


def test_host_rejects_changed_raw_laws_and_failed_source_roundtrip():
    source = _context(2)
    candidate = _candidate(source)
    candidate["raw_base_axioms"] = []
    with pytest.raises(ValueError, match="frozen raw theory"):
        validate_materialized_generative_candidate(_resign(candidate), source)

    candidate = _candidate(source)
    model_ids = list(candidate["source_lowered_models"])
    assert len(model_ids) > 1
    candidate["source_lowered_models"][model_ids[0]] = candidate[
        "source_lowered_models"
    ][model_ids[1]]
    with pytest.raises(ValueError, match="roundtrip failed"):
        validate_materialized_generative_candidate(_resign(candidate), source)


def test_reviewed_materialization_builds_successor_finder_without_generated_code():
    signature, involutive, fixed = _surface()
    source = _context(1)
    candidate = _candidate(source)
    host = validate_materialized_generative_candidate(candidate, source)
    reviewed, application = admit_materialized_generative_representation(
        candidate,
        source_context=source,
        host_conformance=host,
        independent_review={
            "accepted": True,
            "reviewer_ref": "fixture:independent-review",
            "rationale": "The materialized relation replays at both boundaries.",
            "evidence_refs": ["sha256:" + host["receipt_sha256"]],
        },
    )
    compiled = compile_theory_language_expansion(
        request=None,
        source_context=source,
        formula_grammar={
            "schema": EQUATIONAL_GRAMMAR_SCHEMA,
            "max_total_operation_order": 2,
        },
        approved_application=application,
    )
    assert compiled["status"] == "compiled"
    assert reviewed.query_strata == ({"sort_sizes": {"S": 2}},)
    image = compiled["context"].universe.receipt
    finder = build_fixed_size_countermodel_finder(
        signature=signature,
        adapter_config={
            "functor_image": {
                "receipt_sha256": image.receipt_digest,
                "source_context_hash": source.context_hash,
                "source_object_count": len(source.object_ids),
                "canonical_model_count": len(compiled["context"].object_ids),
            },
            "generative_representation": reviewed.to_json(),
        },
    )
    receipt = finder((), fixed, sort_sizes={"S": 2}, timeout_ms=1)
    assert receipt.status == "countermodel_found"
    assert receipt.witness is not None
    assert not evaluate_axiom(signature, fixed, receipt.witness)
    assert receipt.solver.startswith("reviewed_generative_representation:")
    absence = finder((), involutive, sort_sizes={"S": 2}, timeout_ms=1)
    assert absence.status == "unknown"
    assert "not host-certified" in absence.reason
