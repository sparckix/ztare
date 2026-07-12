from __future__ import annotations

import ztare.leanmill.theory_interest as theory_interest
from ztare.common.information_yield_pricing import residual_information_yield
from ztare.leanmill.adapters.generic_fol_finite import build_model_universe
from ztare.leanmill.equational_baseline import (
    BoundedRewriteSearchReceipt,
    EquationalConsequenceAnalysis,
    bounded_equational_reduction_analysis,
    bounded_equational_reduction_witness,
    direct_equational_consequence_witness,
    direct_joint_rewrite_witness,
)
from ztare.leanmill.finite_theory_context import (
    build_formal_theory_context,
    load_formal_theory_context,
)
from ztare.leanmill.magma_law_universe import magma_laws_through_order
from ztare.leanmill.theory_interest import theory_residual_information_yield
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Binder,
    Formula,
    OperationSymbol,
    SortDecl,
    Term,
    TheorySignature,
)


def test_residual_information_yield_subtracts_named_baseline() -> None:
    coordinates = residual_information_yield(
        ("known", "residual"),
        ("known",),
        (0, 1, 2, 3),
        lambda candidate_id, obj: (
            True if candidate_id == "known" else int(obj) >= 2
        ),
        baseline_ref="test.cheap_baseline.v1",
        description_units=2,
        verification_cost_units=1,
    )

    assert coordinates.baseline_ref == "test.cheap_baseline.v1"
    assert coordinates.baseline_ids == ("known",)
    assert coordinates.residual_ids == ("residual",)
    assert coordinates.identification_bits == 1.0
    assert coordinates.information_per_cost == 1 / 3


def test_direct_rewrite_baseline_catches_first_science_candidate() -> None:
    laws = {row.postfix: row for row in magma_laws_through_order(3)}
    first = laws["x0 = x0 x0 x0 op0 x0 op0 op0"]
    second = laws["x0 x0 op0 = x0 x0 op0 x0 op0"]
    target = laws["x0 = x0 x0 x0 op0 op0"]

    witness = direct_joint_rewrite_witness((first.axiom, second.axiom), target.axiom)

    assert witness is not None
    assert witness.rewritten_side == "right"
    assert witness.rewrite_orientation == "right_to_left"
    assert witness.subterm_path == (1,)


def test_bounded_reduction_catches_short_regular_unary_bridge() -> None:
    x = Term.var("x")
    mul = lambda left, right: Term.app("mul", left, right)
    inv = lambda value: Term.app("inv", value)
    binder = (Binder("x", "S"),)

    def equation(name, left, right):
        return AxiomFormula(name, Formula.forall(binder, Formula.eq(left, right)))

    associative = AxiomFormula(
        "associative",
        Formula.forall(
            (Binder("x", "S"), Binder("y", "S"), Binder("z", "S")),
            Formula.eq(
                mul(mul(Term.var("x"), Term.var("y")), Term.var("z")),
                mul(Term.var("x"), mul(Term.var("y"), Term.var("z"))),
            ),
        ),
    )
    left_recovery = equation("left_recovery", mul(inv(x), x), x)
    square_is_inverse = equation("square_is_inverse", mul(x, x), inv(x))
    target = equation("right_recovery", mul(x, inv(x)), x)

    witness = bounded_equational_reduction_witness(
        (associative, left_recovery, square_is_inverse), target
    )

    assert witness is not None
    assert witness.schema == "leanmill.bounded_equational_reduction.v2"
    assert witness.max_states_per_side == 4_096
    assert witness.growth_policy == "root_or_direct_child"
    assert 1 <= witness.explored_left_states <= witness.max_states_per_side
    assert 1 <= witness.explored_right_states <= witness.max_states_per_side
    assert len(witness.steps) == 4
    assert {step["premise_hash"] for step in witness.steps} == {
        associative.semantic_hash,
        left_recovery.semantic_hash,
        square_is_inverse.semantic_hash,
    }


def test_bidirectional_reduction_reuses_selected_inverse_intermediate() -> None:
    x, y = Term.var("x"), Term.var("y")
    mul = lambda left, right: Term.app("mul", left, right)
    inv = lambda value: Term.app("inv", value)

    def equation(name, binders, left, right):
        return AxiomFormula(name, Formula.forall(binders, Formula.eq(left, right)))

    one = (Binder("x", "S"),)
    selected_inverse_right = equation(
        "selected_inverse_right",
        one,
        inv(x),
        mul(mul(inv(x), x), inv(x)),
    )
    selected_inverse_left = equation(
        "selected_inverse_left",
        one,
        x,
        mul(mul(x, inv(x)), x),
    )
    absorption = equation("absorption", one, mul(inv(x), x), x)
    commutative = equation(
        "commutative",
        (Binder("x", "S"), Binder("y", "S")),
        mul(x, y),
        mul(y, x),
    )
    target = equation("square_is_inverse", one, mul(x, x), inv(x))
    second_target = equation(
        "inverse_square_is_self",
        one,
        inv(mul(x, x)),
        x,
    )

    witness = bounded_equational_reduction_witness(
        (
            selected_inverse_right,
            selected_inverse_left,
            absorption,
            commutative,
        ),
        target,
    )

    assert witness is not None
    assert len(witness.steps) <= 8
    assert absorption.semantic_hash in {
        step["premise_hash"] for step in witness.steps
    }
    assert commutative.semantic_hash in {
        step["premise_hash"] for step in witness.steps
    }
    second_witness = bounded_equational_reduction_witness(
        (
            selected_inverse_right,
            selected_inverse_left,
            absorption,
            commutative,
        ),
        second_target,
    )
    assert second_witness is not None
    assert len(second_witness.steps) <= 8

    saturated = bounded_equational_reduction_analysis(
        (
            selected_inverse_right,
            selected_inverse_left,
            absorption,
            commutative,
        ),
        second_target,
        max_states_per_side=2,
    )
    assert saturated.witness is None
    assert saturated.bounded_search is not None
    assert saturated.bounded_search.status == "state_cap_saturated"
    assert saturated.bounded_search.saturated_sides == ("left", "right")


def test_direct_rewrite_baseline_stays_conservative_on_many_sorted_input() -> None:
    def equation(name: str, sort: str, left: Term, right: Term) -> AxiomFormula:
        return AxiomFormula(
            name,
            Formula.forall((Binder("x", sort),), Formula.eq(left, right)),
        )

    premise_a = equation("a", "A", Term.var("x"), Term.app("f", Term.var("x")))
    premise_b = equation("b", "B", Term.var("x"), Term.app("g", Term.var("x")))
    target = equation(
        "target", "A", Term.var("x"), Term.app("f", Term.app("f", Term.var("x")))
    )

    assert direct_joint_rewrite_witness((premise_a, premise_b), target) is None


def test_direct_baseline_catches_substitution_instance_from_residual_smoke() -> None:
    laws = {row.formula_id: row for row in magma_laws_through_order(3)}
    premise = laws[
        "formula:1ca04f756bb1f3a46bfed552fbea92a3f3db1f3cd2a8fa0de641b0be7b9f55b1"
    ]
    target = laws[
        "formula:c17c6866b4705cbe04dfaac0317845bf916c1d9ef39458d82ec70744ac95d420"
    ]

    witness = direct_equational_consequence_witness((premise.axiom,), target.axiom)

    assert witness is not None
    assert witness.schema == "leanmill.equational_substitution_instance.v1"
    assert witness.target_side_order == "swapped"
    assert set(witness.substitution) == {"x0", "x1"}


def test_direct_baseline_uses_the_frozen_base_theory() -> None:
    signature = TheorySignature(
        "BaseAwareBaseline",
        (SortDecl("S"),),
        (
            OperationSymbol("f", ("S",), "S"),
            OperationSymbol("g", ("S",), "S"),
        ),
    )
    x = Term.var("x")
    binder = (Binder("x", "S"),)
    base = AxiomFormula(
        "f_identity",
        Formula.forall(binder, Formula.eq(Term.app("f", x), x)),
    )
    candidate = AxiomFormula(
        "candidate",
        Formula.forall(
            binder,
            Formula.eq(Term.app("g", Term.app("f", x)), x),
        ),
    )
    target = AxiomFormula(
        "target",
        Formula.forall(binder, Formula.eq(Term.app("g", x), x)),
    )
    universe = build_model_universe(
        signature,
        strata=({"sort_sizes": {"S": 2}},),
        base_axioms=(base,),
        adapter_config={"isomorphism_quotient": False},
    )
    context = build_formal_theory_context(
        signature=signature,
        formulas=(candidate, target),
        universe=universe,
        base_axioms=(base,),
    )
    candidate_id = "formula:" + candidate.semantic_hash
    target_id = "formula:" + target.semantic_hash

    direct_witness = direct_equational_consequence_witness(
        (base, candidate), target
    )
    signal = theory_residual_information_yield(context, (candidate_id,))

    assert direct_witness is not None
    assert direct_witness.schema == "leanmill.direct_equational_rewrite.v1"
    assert direct_witness.rewrite_premise_hash == base.semantic_hash
    assert signal.joint_only_consequence_ids == (target_id,)
    assert signal.cheap_baseline_consequence_ids == (target_id,)
    assert signal.residual_consequence_ids == ()
    witness = signal.cheap_baseline_witnesses[target_id]
    assert witness["schema"] in {
        "leanmill.direct_equational_rewrite.v1",
        "leanmill.finite_structure_baseline_witness.v1",
    }


def test_residual_smoke_singleton_excludes_premise_and_cheap_instance() -> None:
    context = load_formal_theory_context(
        "research_areas/pre_registrations/axiompack_gp251_smoke_20260710/"
        "formal_context.materialized.json"
    )
    premise = (
        "formula:1ca04f756bb1f3a46bfed552fbea92a3f3db1f3cd2a8fa0de641b0be7b9f55b1"
    )
    target = (
        "formula:c17c6866b4705cbe04dfaac0317845bf916c1d9ef39458d82ec70744ac95d420"
    )

    signal = theory_residual_information_yield(context, (premise,))

    assert premise not in signal.joint_only_consequence_ids
    assert signal.joint_only_consequence_ids == (target,)
    assert signal.cheap_baseline_consequence_ids == (target,)
    assert signal.residual_consequence_ids == ()
    assert signal.coordinates.identification_bits == 0.0


def test_saved_first_science_context_has_zero_residual_yield() -> None:
    context = load_formal_theory_context(
        "research_areas/pre_registrations/axiompack_gp251_smoke_20260710/"
        "formal_context.materialized.json"
    )
    premises = (
        "formula:1944272b3136907f1e971c006620ba5d92475726a49c922c715a527d05cb1737",
        "formula:c17c6866b4705cbe04dfaac0317845bf916c1d9ef39458d82ec70744ac95d420",
    )
    target = (
        "formula:4eb72b9af83fce02302ea8383da0459113feac5c2eb03a62aa3ded53bf5c5237"
    )

    signal = theory_residual_information_yield(context, premises)

    assert signal.joint_only_consequence_ids == (target,)
    assert signal.cheap_baseline_consequence_ids == (target,)
    assert signal.residual_consequence_ids == ()
    assert signal.coordinates.identification_bits == 0.0


def test_state_cap_saturation_is_inconclusive_not_positive_residual(
    monkeypatch,
) -> None:
    context = load_formal_theory_context(
        "research_areas/pre_registrations/axiompack_gp251_smoke_20260710/"
        "formal_context.materialized.json"
    )
    premises = (
        "formula:1944272b3136907f1e971c006620ba5d92475726a49c922c715a527d05cb1737",
        "formula:c17c6866b4705cbe04dfaac0317845bf916c1d9ef39458d82ec70744ac95d420",
    )
    target = (
        "formula:4eb72b9af83fce02302ea8383da0459113feac5c2eb03a62aa3ded53bf5c5237"
    )

    def saturated(_premises, target_axiom):
        return EquationalConsequenceAnalysis(
            None,
            BoundedRewriteSearchReceipt(
                target_hash=target_axiom.semantic_hash,
                status="state_cap_saturated",
                max_steps=8,
                max_states_per_side=2,
                explored_left_states=2,
                explored_right_states=2,
                saturated_sides=("left", "right"),
            ),
        )

    theory_interest._CACHE.clear()
    monkeypatch.setattr(
        theory_interest,
        "direct_equational_consequence_analysis",
        saturated,
    )
    try:
        signal = theory_interest.theory_residual_information_yield(
            context, premises
        )
    finally:
        theory_interest._CACHE.clear()

    assert signal.joint_only_consequence_ids == (target,)
    assert signal.cheap_baseline_consequence_ids == ()
    assert signal.residual_consequence_ids == ()
    assert signal.cheap_baseline_inconclusive_ids == (target,)
    assert signal.coordinates.identification_bits == 0.0
    assert (
        signal.cheap_baseline_inconclusive_receipts[target]["status"]
        == "state_cap_saturated"
    )
