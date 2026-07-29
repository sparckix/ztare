from __future__ import annotations

import pytest

from ztare.leanmill.finite_model import (
    COUNTERMODEL,
    NO_COUNTERMODEL_WITHIN_BOUND,
    FiniteModel,
    FiniteSearchBounds,
)
from ztare.leanmill.finite_model_census import enumerate_magma_model_universe
from ztare.leanmill.finite_theory_context import build_formal_theory_context
from ztare.leanmill.magma_law_universe import anonymous_magma_signature, magma_laws_through_order
from ztare.leanmill.theory_landscape_morphism import (
    EquationalOperationImage,
    admit_checked_equational_interpretation,
    build_equational_interpretation,
    build_landscape_fingerprint,
    prepare_checked_equational_interpretation,
    propose_landscape_transport,
    test_compiled_landscape_mapping as compile_test,
    translate_interpreted_axiom,
    transport_axiom_through_checked_interpretation,
)
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Binder,
    Formula,
    OperationSymbol,
    SortDecl,
    Term,
    TheorySignature,
)


def _context(max_order):
    signature = anonymous_magma_signature()
    laws = magma_laws_through_order(max_order)
    return build_formal_theory_context(
        signature=signature,
        formulas=tuple(row.axiom for row in laws),
        universe=enumerate_magma_model_universe(signature, carrier_sizes=(2,)),
    )


def test_landscape_transport_starts_pending_and_requires_target_replay():
    source = build_landscape_fingerprint(_context(1))
    target = build_landscape_fingerprint(_context(2))
    morphism = propose_landscape_transport(source, target)
    assert all(row["status"] == "pending" for row in morphism.preservation_obligations)
    assert morphism.validate().verified is False
    mapping = {key: key for key in morphism.component_map}
    receipt = compile_test(morphism, compiled_mapping=mapping, target_test=lambda _row: True)
    assert receipt["status"] == "passed_local_target_test"
    assert receipt["axiom_authority_eligible"] is False


def _assoc_theories():
    source = TheorySignature(
        name="SourceMagma",
        sorts=(SortDecl("S"),),
        operations=(OperationSymbol("star", ("S", "S"), "S"),),
    )
    target = TheorySignature(
        name="TargetMagma",
        sorts=(SortDecl("T"),),
        operations=(OperationSymbol("mul", ("T", "T"), "T"),),
    )
    x, y, z = (Term.var(name) for name in ("x", "y", "z"))
    source_assoc = AxiomFormula(
        "source_assoc",
        Formula.forall(
            (Binder("x", "S"), Binder("y", "S"), Binder("z", "S")),
            Formula.eq(
                Term.app("star", Term.app("star", x, y), z),
                Term.app("star", x, Term.app("star", y, z)),
            ),
        ),
    )
    target_assoc = AxiomFormula(
        "target_assoc",
        Formula.forall(
            (Binder("x", "T"), Binder("y", "T"), Binder("z", "T")),
            Formula.eq(
                Term.app("mul", Term.app("mul", x, y), z),
                Term.app("mul", x, Term.app("mul", y, z)),
            ),
        ),
    )
    opposite = build_equational_interpretation(
        source,
        target,
        sort_map={"S": "T"},
        operation_images={
            "star": EquationalOperationImage(
                "star",
                ("left", "right"),
                Term.app("mul", Term.var("right"), Term.var("left")),
            )
        },
    )
    xor_model = FiniteModel(
        sort_sizes=(("T", 2),),
        operations=(("mul", (0, 1, 1, 0)),),
    )
    return source, source_assoc, target, target_assoc, opposite, xor_model


def test_opposite_semigroup_interpretation_has_finite_kill_and_lean_obligations():
    source, source_assoc, target, target_assoc, opposite, xor_model = (
        _assoc_theories()
    )
    translated = translate_interpreted_axiom(
        source_assoc, opposite, source, target
    )
    assert translated.formula.formulas[0].terms[0].to_json() == {
        "kind": "app",
        "symbol": "mul",
        "args": [
            {"kind": "var", "name": "z"},
            {
                "kind": "app",
                "symbol": "mul",
                "args": [
                    {"kind": "var", "name": "y"},
                    {"kind": "var", "name": "x"},
                ],
            },
        ],
    }

    plan = prepare_checked_equational_interpretation(
        source,
        (source_assoc,),
        target,
        (target_assoc,),
        opposite,
        bounds=FiniteSearchBounds(max_carrier_size=2),
        target_model=xor_model,
    )
    assert plan.finite_implication_receipt["status"] == (
        NO_COUNTERMODEL_WITHIN_BOUND
    )
    assert plan.noncollapse_receipt["status"] == "witnessed"
    assert plan.status == "bounded_supported_awaiting_lean"
    assert len(plan.lean_tasks) == 1
    assert plan.to_json()["plan_sha256"]


def test_finite_countermodel_refutes_an_unjustified_interpretation():
    source, source_assoc, target, _target_assoc, opposite, xor_model = (
        _assoc_theories()
    )
    plan = prepare_checked_equational_interpretation(
        source,
        (source_assoc,),
        target,
        (),
        opposite,
        bounds=FiniteSearchBounds(max_carrier_size=2),
        target_model=xor_model,
    )
    assert plan.finite_implication_receipt["status"] == COUNTERMODEL
    assert plan.status == "refuted_by_finite_countermodel"
    with pytest.raises(ValueError, match="countermodel"):
        admit_checked_equational_interpretation(
            plan,
            proof_texts={row.task_id: "by exact True.intro" for row in plan.lean_tasks},
            compile_fn=lambda _source: True,
            axiom_audit_fn=lambda _source, _target: (True, False, ()),
        )


def test_checked_admission_is_required_before_axiom_transport():
    source, source_assoc, target, target_assoc, opposite, xor_model = (
        _assoc_theories()
    )
    plan = prepare_checked_equational_interpretation(
        source,
        (source_assoc,),
        target,
        (target_assoc,),
        opposite,
        bounds=FiniteSearchBounds(max_carrier_size=2),
        target_model=xor_model,
    )
    admission = admit_checked_equational_interpretation(
        plan,
        proof_texts={row.task_id: "by exact True.intro" for row in plan.lean_tasks},
        compile_fn=lambda _source: True,
        axiom_audit_fn=lambda _source, _target: (True, False, ()),
    )
    assert admission["status"] == "checked"
    transport = transport_axiom_through_checked_interpretation(
        source_assoc, opposite, source, target, admission
    )
    assert transport["status"] == "transported_pending_target_adjudication"
    assert transport["target_axiom_sha256"]

    changed = dict(admission)
    changed["target_theory_hash"] = "0" * 64
    with pytest.raises(ValueError, match="checked interpretation"):
        transport_axiom_through_checked_interpretation(
            source_assoc, opposite, source, target, changed
        )
