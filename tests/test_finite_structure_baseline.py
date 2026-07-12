from __future__ import annotations

from ztare.common.finite_incidence_context import build_incidence_context
from ztare.leanmill.adapters.generic_fol_finite import (
    GenericFiniteModelRecord,
    build_model_universe,
)
from ztare.leanmill.equational_formula_universe import enumerate_universal_equations
from ztare.leanmill.finite_model import FiniteModel
from ztare.leanmill.finite_structure_baseline import finite_structural_baseline
from ztare.leanmill.finite_theory_context import build_formal_theory_context
from ztare.leanmill.theory_interest import (
    COMBINED_EQUATIONAL_STRUCTURAL_BASELINE_REF,
    theory_residual_information_yield,
)
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Binder,
    Formula,
    OperationSymbol,
    RelationSymbol,
    SortDecl,
    Term,
    TheorySignature,
    render_formula_plain,
)


def _regular_unary_fixture():
    signature = TheorySignature(
        "RegularUnaryFixture",
        (SortDecl("S0"),),
        (
            OperationSymbol("op0", ("S0", "S0"), "S0"),
            OperationSymbol("op1", ("S0",), "S0"),
        ),
    )
    x, y, z = Term.var("x"), Term.var("y"), Term.var("z")

    def mul(left: Term, right: Term) -> Term:
        return Term.app("op0", left, right)

    def inv(value: Term) -> Term:
        return Term.app("op1", value)

    base = (
        AxiomFormula(
            "associative",
            Formula.forall(
                (Binder("x", "S0"), Binder("y", "S0"), Binder("z", "S0")),
                Formula.eq(mul(mul(x, y), z), mul(x, mul(y, z))),
            ),
        ),
        AxiomFormula(
            "selected_inverse_left",
            Formula.forall(
                (Binder("x", "S0"),),
                Formula.eq(x, mul(mul(x, inv(x)), x)),
            ),
        ),
        AxiomFormula(
            "selected_inverse_right",
            Formula.forall(
                (Binder("x", "S0"),),
                Formula.eq(inv(x), mul(mul(inv(x), x), inv(x))),
            ),
        ),
    )
    grammar = {
        "schema": "leanmill.universal_equation_grammar.v1",
        "max_total_operation_order": 2,
        "max_formulas": 10_000,
        "variable_renaming_quotient": True,
        "equation_side_quotient": True,
        "exclude_nonvariable_reflexive": True,
    }
    rows = enumerate_universal_equations(signature, grammar)
    formulas = tuple(row.axiom for row in rows)
    ids = {
        render_formula_plain(row.axiom.formula): row.formula_id for row in rows
    }
    universe = build_model_universe(
        signature,
        strata=({"sort_sizes": {"S0": 2}},),
        base_axioms=base,
        adapter_config={"isomorphism_quotient": True},
    )
    return build_formal_theory_context(
        signature=signature,
        formulas=formulas,
        universe=universe,
        base_axioms=base,
    ), ids


def test_constant_selector_projection_collapse_is_a_cheap_structural_baseline():
    context, ids = _regular_unary_fixture()
    presentation = (
        ids["forall x0:S0, op0(op1(x0), x0) = x0"],
        ids["forall x0:S0, x1:S0, op1(x0) = op1(x1)"],
    )
    right_zero_target = ids[
        "forall x0:S0, x1:S0, op0(op0(x0, x1), x1) = x1"
    ]

    signal = theory_residual_information_yield(context, presentation)

    assert right_zero_target in signal.joint_only_consequence_ids
    assert right_zero_target in signal.cheap_baseline_consequence_ids
    assert signal.residual_consequence_ids == ()
    assert signal.coordinates.identification_bits == 0.0
    assert signal.coordinates.baseline_ref == (
        COMBINED_EQUATIONAL_STRUCTURAL_BASELINE_REF
    )
    assert signal.structural_baseline is not None
    templates = {
        row["template_id"]
        for row in signal.structural_baseline["forced_templates"]
    }
    assert templates == {
        "operation:0:projection:1",
        "operation:1:constant",
    }
    assert signal.structural_baseline["explanation_map"][right_zero_target] == [
        "operation:0:projection:1"
    ]


def test_commutative_absorption_collapse_is_a_cheap_equational_baseline():
    context, ids = _regular_unary_fixture()
    presentation = (
        ids["forall x0:S0, op0(op1(x0), x0) = x0"],
        ids[
            "forall x0:S0, x1:S0, op0(x0, x1) = op0(x1, x0)"
        ],
    )
    targets = {
        ids["forall x0:S0, op0(x0, x0) = op1(x0)"],
        ids["forall x0:S0, op1(op0(x0, x0)) = x0"],
    }

    signal = theory_residual_information_yield(context, presentation)

    assert targets <= set(signal.joint_only_consequence_ids)
    assert targets <= set(signal.cheap_baseline_consequence_ids)
    assert signal.residual_consequence_ids == ()
    assert signal.coordinates.identification_bits == 0.0
    assert all(
        signal.cheap_baseline_witnesses[target]["schema"]
        == "leanmill.bounded_equational_reduction.v2"
        for target in targets
    )


def test_empty_relation_template_is_detected_without_domain_vocabulary():
    signature = TheorySignature(
        "RelationFixture",
        (SortDecl("S0"),),
        relations=(RelationSymbol("rel0", ("S0",)),),
    )
    models = tuple(
        GenericFiniteModelRecord(
            model_id=f"model:{index}",
            stratum_id="size:2",
            model=FiniteModel(
                sort_sizes=(("S0", 2),),
                relations=(("rel0", table),),
            ),
        )
        for index, table in enumerate(
            ((False, False), (True, True), (True, False))
        )
    )
    incidence = build_incidence_context(
        object_ids=tuple(row.model_id for row in models),
        attribute_truth_bits={"empty_law": 0b001, "same_profile": 0b001},
        exact=True,
        completeness_ref="fixture:complete",
    )

    baseline = finite_structural_baseline(
        context_hash="fixture-context",
        signature=signature,
        models=models,
        incidence=incidence,
        presentation_ids=("empty_law",),
        candidate_formula_ids=("same_profile",),
    )

    assert [row.template_id for row in baseline.forced_templates] == [
        "relation:0:empty"
    ]
    assert baseline.conditioning_bits == 0b001
    assert baseline.explained_formula_ids == ("same_profile",)


def test_inessential_operation_argument_is_a_generic_structural_template():
    signature = TheorySignature(
        "ReducedArityFixture",
        (SortDecl("S0"),),
        operations=(OperationSymbol("op0", ("S0", "S0"), "S0"),),
    )
    models = tuple(
        GenericFiniteModelRecord(
            model_id=f"model:{index}",
            stratum_id="size:2",
            model=FiniteModel(
                sort_sizes=(("S0", 2),),
                operations=(("op0", table),),
            ),
        )
        for index, table in enumerate(
            (
                (1, 0, 1, 0),
                (0, 0, 1, 1),
                (0, 1, 1, 0),
            )
        )
    )
    incidence = build_incidence_context(
        object_ids=tuple(row.model_id for row in models),
        attribute_truth_bits={"row_independent": 0b001, "same_profile": 0b001},
        exact=True,
        completeness_ref="fixture:complete",
    )

    baseline = finite_structural_baseline(
        context_hash="reduced-arity-context",
        signature=signature,
        models=models,
        incidence=incidence,
        presentation_ids=("row_independent",),
        candidate_formula_ids=("same_profile",),
    )

    assert [row.template_id for row in baseline.forced_templates] == [
        "operation:0:inessential_argument:0"
    ]
    assert baseline.conditioning_bits == 0b001
    assert baseline.explained_formula_ids == ("same_profile",)
