from __future__ import annotations

from ztare.leanmill.finite_model import evaluate_axiom
from ztare.leanmill.finite_table_model_finder import (
    find_finite_countermodel,
    find_magma_countermodel,
)
from ztare.leanmill.magma_law_universe import anonymous_magma_signature, magma_laws_through_order
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Binder,
    Formula,
    OperationSymbol,
    SortDecl,
    Term,
    TheorySignature,
)


def _law(postfix):
    return next(row for row in magma_laws_through_order(2) if row.postfix == postfix)


def test_targeted_solver_finds_and_host_replays_countermodel():
    idempotent = _law("x0 = x0 x0 op0")
    commutative = _law("x0 x1 op0 = x1 x0 op0")
    receipt = find_magma_countermodel((idempotent,), commutative, carrier_size=2)
    assert receipt.status == "countermodel_found"
    assert receipt.witness is not None
    signature = anonymous_magma_signature()
    assert evaluate_axiom(signature, idempotent.axiom, receipt.witness)
    assert not evaluate_axiom(signature, commutative.axiom, receipt.witness)


def test_unsat_claim_is_scoped_to_fixed_carrier():
    commutative = _law("x0 x1 op0 = x1 x0 op0")
    receipt = find_magma_countermodel((commutative,), commutative, carrier_size=3)
    assert receipt.status == "no_countermodel_at_fixed_size"
    assert receipt.to_json()["claim_boundary"] == "one fixed finite carrier size"


def test_generic_receipt_binds_signature_base_and_does_not_launder_vacuity():
    signature = anonymous_magma_signature()
    impossible = AxiomFormula("impossible", Formula.falsity())
    target = _law("x0 = x0 x0 op0").axiom

    receipt = find_finite_countermodel(
        signature,
        (),
        target,
        carrier_size=2,
        base_axioms=(impossible,),
    )
    row = receipt.to_json()

    assert receipt.status == "no_premise_model_at_fixed_size"
    assert row["signature_sha256"] == signature.content_hash
    assert row["base_formula_ids"] == ["formula:" + impossible.semantic_hash]
    assert row["host_replay_status"] == "not_applicable"


def test_generic_unary_binary_countermodel_is_host_replayed():
    signature = TheorySignature(
        name="UnaryBinary",
        sorts=(SortDecl("S"),),
        operations=(
            OperationSymbol("inv", ("S",), "S"),
            OperationSymbol("mul", ("S", "S"), "S"),
        ),
    )
    x = Term.var("x")
    y = Term.var("y")
    idempotent = AxiomFormula(
        "idempotent",
        Formula.forall(
            (Binder("x", "S"),),
            Formula.eq(Term.app("mul", x, x), x),
        ),
    )
    commutative = AxiomFormula(
        "commutative",
        Formula.forall(
            (Binder("x", "S"), Binder("y", "S")),
            Formula.eq(Term.app("mul", x, y), Term.app("mul", y, x)),
        ),
    )

    receipt = find_finite_countermodel(
        signature,
        (idempotent,),
        commutative,
        sort_sizes={"S": 2},
    )

    assert receipt.status == "countermodel_found"
    assert receipt.witness is not None
    assert evaluate_axiom(signature, idempotent, receipt.witness)
    assert not evaluate_axiom(signature, commutative, receipt.witness)
    assert receipt.to_json()["host_replay_status"] == "passed"
