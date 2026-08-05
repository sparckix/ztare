from dataclasses import replace
import inspect
from typing import get_type_hints

import pytest

import ztare.common.filtered_obstruction as filtered_obstruction_module
from ztare.common.content_bound_evidence import EvidenceAuthority
from ztare.common.filtered_obstruction import (
    FilteredAction,
    FilteredAsymptoticClaim,
    FilteredAsymptoticEvidenceScope,
    FilteredAsymptoticInductionProblem,
    FilteredAsymptoticRateWitness,
    FilteredBasisVector,
    FilteredCoupledBlock,
    FilteredCoupledBlockProblem,
    FilteredGraphQuotientProblem,
    FilteredInductionProblem,
    FilteredInductionState,
    FilteredInductionTransition,
    FilteredObstructionError,
    FilteredObstructionProblem,
    FilteredPolynomialFiberProblem,
    FilteredPuiseuxClaim,
    FilteredPuiseuxEvidenceScope,
    FilteredPolarTensorClaim,
    FilteredPolarTensorEvidenceScope,
    FilteredPolarTensorFactorizationProblem,
    FilteredPolarTensorModel,
    FilteredPolarWittClaim,
    FilteredPolarWittEvidenceScope,
    FilteredPolarWittFactorizationProblem,
    FilteredPolarWittModel,
    FilteredPuiseuxFlowProblem,
    FilteredQuadraticDifferentialProblem,
    FilteredReachabilityProblem,
    FilteredRelation,
    FilteredSurplusProjectionProblem,
    FilteredSymbolCokernelProblem,
    FilteredSymbolMap,
    FilteredTailClaim,
    FilteredTailEvidenceScope,
    FilteredTailMinimaxCompositionProblem,
    FilteredTailOccurrenceOrder,
    FilteredTwoFlowPuiseuxProblem,
    compile_filtered_surplus_projection,
    compile_filtered_asymptotic_induction,
    compile_filtered_coupled_blocks,
    compile_filtered_graph_quotient,
    compile_filtered_induction,
    compile_filtered_symbol_cokernel,
    compile_filtered_tail_minimax_composition,
    compile_fixed_grade_obstruction,
    compile_filtered_obstruction,
    compile_filtered_polynomial_fiber,
    compile_filtered_polar_tensor_factorization,
    compile_filtered_polar_witt_factorization,
    compile_filtered_puiseux_flow_obstruction,
    compile_filtered_quadratic_differential_obstruction,
    compile_filtered_reachability,
    compile_filtered_two_flow_puiseux_obstruction,
    make_filtered_tail_context,
    make_filtered_tail_evidence,
    make_filtered_asymptotic_evidence,
    make_filtered_puiseux_context,
    make_filtered_puiseux_evidence,
    make_filtered_polar_tensor_context,
    make_filtered_polar_tensor_evidence,
    make_filtered_polar_witt_context,
    make_filtered_polar_witt_evidence,
)


def test_filtered_problem_inputs_have_no_boolean_premise_fields() -> None:
    offenders = {
        name: tuple(
            field_name
            for field_name, field_type in get_type_hints(candidate).items()
            if field_type is bool
        )
        for name, candidate in inspect.getmembers(
            filtered_obstruction_module,
            inspect.isclass,
        )
        if name.startswith("Filtered") and name.endswith("Problem")
    }
    assert {name: fields for name, fields in offenders.items() if fields} == {}


def _alien_problem(
    *,
    basis: tuple[FilteredBasisVector, ...] | None = None,
) -> FilteredObstructionProblem:
    return FilteredObstructionProblem(
        name="alien_three_step_filtration",
        basis=basis
        or (
            FilteredBasisVector("x", 0),
            FilteredBasisVector("y", 1),
            FilteredBasisVector("z", 2),
        ),
        relations=(
            FilteredRelation("r_x", 0, {"x": 1}),
            FilteredRelation("r_y", 1, {"y": 1}),
        ),
        actions=(
            FilteredAction(
                "raising",
                1,
                {"x": {"y": 2}, "y": {}, "z": {}},
            ),
        ),
        distinguished={"z": 3},
    )


def test_alien_model_has_replayable_one_dimensional_coinvariant() -> None:
    certificate = compile_filtered_obstruction(_alien_problem())
    assert certificate.relation_transport_verified
    assert certificate.coinvariant_dimension == 1
    assert certificate.distinguished_survives
    assert certificate.distinguished_pairing == "1"
    assert certificate.witness_by_basis == (("z", "1/3"),)


def test_alien_nilpotent_ladder_has_nontrivial_relation_transport() -> None:
    basis = (
        FilteredBasisVector("e0", 0),
        FilteredBasisVector("e1", 1),
        FilteredBasisVector("e2", 1),
        FilteredBasisVector("e3", 2),
        FilteredBasisVector("e4", 2),
    )
    problem = FilteredObstructionProblem(
        name="alien_nilpotent_ladder",
        basis=basis,
        relations=(
            FilteredRelation("r1", 1, {"e1": 1, "e2": -1}),
            FilteredRelation("r2", 2, {"e3": 1, "e4": -1}),
        ),
        actions=(
            FilteredAction(
                "epsilon",
                1,
                {
                    "e0": {"e1": "1/2", "e2": "1/2"},
                    "e1": {"e3": 1},
                    "e2": {"e4": 1},
                    "e3": {},
                    "e4": {},
                },
            ),
        ),
        distinguished={"e0": 1},
    )
    certificate = compile_filtered_obstruction(problem)
    assert certificate.relation_rank == 2
    assert certificate.action_image_rank == 3
    assert certificate.constraint_rank == 4
    assert certificate.coinvariant_dimension == 1
    assert certificate.witness_by_basis == (("e0", "1"),)


def test_basis_permutation_preserves_named_witness_and_dimension() -> None:
    permuted = (
        FilteredBasisVector("z", 2),
        FilteredBasisVector("x", 0),
        FilteredBasisVector("y", 1),
    )
    first = compile_filtered_obstruction(_alien_problem())
    second = compile_filtered_obstruction(_alien_problem(basis=permuted))
    assert first.coinvariant_dimension == second.coinvariant_dimension == 1
    assert first.witness_by_basis == second.witness_by_basis == (("z", "1/3"),)


def test_wrong_filtration_shift_is_rejected() -> None:
    problem = _alien_problem()
    wrong = FilteredObstructionProblem(
        name="wrong_shift",
        basis=problem.basis,
        relations=problem.relations,
        actions=(
            FilteredAction(
                "wrong",
                0,
                {"x": {"y": 1}, "y": {}, "z": {}},
            ),
        ),
        distinguished=problem.distinguished,
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_obstruction(wrong)
    assert error.value.code == "wrong_filtration_shift"


def test_noninvariant_relation_requires_moving_velocity() -> None:
    basis = (
        FilteredBasisVector("x", 0),
        FilteredBasisVector("y", 1),
        FilteredBasisVector("z", 2),
    )
    static = FilteredObstructionProblem(
        name="static_relation_failure",
        basis=basis,
        relations=(FilteredRelation("r_x", 0, {"x": 1}),),
        actions=(
            FilteredAction(
                "raising",
                1,
                {"x": {"y": 1}, "y": {}, "z": {}},
            ),
        ),
        distinguished={"z": 1},
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_obstruction(static)
    assert error.value.code == "relation_not_invariant"

    moving = FilteredObstructionProblem(
        name="moving_relation_repair",
        basis=basis,
        relations=static.relations,
        actions=(
            FilteredAction(
                "raising",
                1,
                {"x": {"y": 1}, "y": {}, "z": {}},
                relation_velocities={"r_x": {"y": -1}},
            ),
        ),
        distinguished={"z": 1},
    )
    certificate = compile_filtered_obstruction(moving)
    assert certificate.relation_transport_verified
    assert certificate.coinvariant_dimension == 1
    assert certificate.distinguished_survives


def test_killed_class_returns_exact_decomposition() -> None:
    problem = _alien_problem()
    killed = FilteredObstructionProblem(
        name="killed_by_relation",
        basis=problem.basis,
        relations=problem.relations,
        actions=problem.actions,
        distinguished={"y": 5},
    )
    certificate = compile_filtered_obstruction(killed)
    assert not certificate.distinguished_survives
    assert certificate.decomposition_by_column == (("relation:r_y", "5"),)


def test_omitted_action_column_is_not_silently_zero() -> None:
    problem = _alien_problem()
    incomplete = FilteredObstructionProblem(
        name="incomplete_action",
        basis=problem.basis,
        relations=problem.relations,
        actions=(FilteredAction("raising", 1, {"x": {"y": 1}}),),
        distinguished=problem.distinguished,
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_obstruction(incomplete)
    assert error.value.code == "incomplete_action_domain"


def test_fixed_grade_compiler_refuses_cross_grade_action() -> None:
    problem = _alien_problem()
    with pytest.raises(FilteredObstructionError) as error:
        compile_fixed_grade_obstruction(problem)
    assert error.value.code == "fixed_grade_has_multiple_degrees"

    single_grade = FilteredObstructionProblem(
        name="misdeclared_fixed_grade",
        basis=(
            FilteredBasisVector("x", 0),
            FilteredBasisVector("y", 0),
        ),
        relations=(),
        actions=(
            FilteredAction("lowering", -1, {"x": {}, "y": {}}),
        ),
        distinguished={"x": 1},
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_fixed_grade_obstruction(single_grade)
    assert error.value.code == "fixed_grade_nonzero_shift"


def test_product_filtration_action_and_zero_shift_are_typed() -> None:
    problem = FilteredObstructionProblem(
        name="alien_product_filtration",
        basis=(
            FilteredBasisVector("x", (0, 0)),
            FilteredBasisVector("y", (1, -2)),
            FilteredBasisVector("z", (2, -4)),
        ),
        relations=(),
        actions=(
            FilteredAction(
                "product_raising",
                (1, -2),
                {"x": {"y": 1}, "y": {"z": 1}, "z": {}},
            ),
        ),
        distinguished={"z": 1},
    )
    certificate = compile_filtered_obstruction(problem)
    assert not certificate.distinguished_survives

    fixed = FilteredObstructionProblem(
        name="alien_fixed_product_grade",
        basis=(
            FilteredBasisVector("a", (3, -1)),
            FilteredBasisVector("b", (3, -1)),
        ),
        relations=(),
        actions=(
            FilteredAction(
                "zero_product_shift",
                (0, 0),
                {"a": {}, "b": {}},
            ),
        ),
        distinguished={"a": 1},
    )
    assert compile_fixed_grade_obstruction(fixed).distinguished_survives


def test_product_filtration_rejects_wrong_or_mixed_shift() -> None:
    wrong = FilteredSymbolCokernelProblem(
        name="wrong_product_shift",
        domain_basis=(FilteredBasisVector("u", (2, 1)),),
        domain_relations=(),
        codomain_basis=(FilteredBasisVector("v", (1, 3)),),
        codomain_relations=(),
        maps=(FilteredSymbolMap("sigma", (-1, 1), {"u": {"v": 1}}),),
        distinguished={"v": 1},
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_symbol_cokernel(wrong)
    assert error.value.code == "wrong_symbol_shift"

    mixed = FilteredSymbolCokernelProblem(
        name="mixed_product_shift",
        domain_basis=(FilteredBasisVector("u", 2),),
        domain_relations=(),
        codomain_basis=(FilteredBasisVector("v", (1, 3)),),
        codomain_relations=(),
        maps=(FilteredSymbolMap("sigma", (-1, 1), {"u": {"v": 1}}),),
        distinguished={"v": 1},
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_symbol_cokernel(mixed)
    assert error.value.code == "incompatible_filtration_degree"


def test_coupled_blocks_retain_one_common_control() -> None:
    problem = FilteredCoupledBlockProblem(
        name="alien_incompatible_shared_demands",
        domain_basis=(FilteredBasisVector("control", 0),),
        domain_relations=(),
        blocks=(
            FilteredCoupledBlock(
                name="value",
                codomain_basis=(FilteredBasisVector("a", 2),),
                codomain_relations=(),
                symbol_map=FilteredSymbolMap(
                    "value_map", 2, {"control": {"a": 1}}
                ),
                distinguished={"a": 1},
            ),
            FilteredCoupledBlock(
                name="jet",
                codomain_basis=(FilteredBasisVector("b", 3),),
                codomain_relations=(),
                symbol_map=FilteredSymbolMap(
                    "jet_map", 3, {"control": {"b": 1}}
                ),
                distinguished={"b": 2},
            ),
        ),
    )
    certificate = compile_filtered_coupled_blocks(problem)
    assert certificate.common_control_rank == 1
    assert certificate.coupled_cokernel_dimension == 1
    assert certificate.distinguished_survives
    assert certificate.distinguished_pairing == "1"
    assert certificate.witness_by_block_basis == (
        ("jet::b", "1"),
        ("value::a", "-1"),
    )


def test_coupled_blocks_return_exact_common_cancellation() -> None:
    problem = FilteredCoupledBlockProblem(
        name="alien_consistent_shared_demands",
        domain_basis=(FilteredBasisVector("control", 0),),
        domain_relations=(),
        blocks=(
            FilteredCoupledBlock(
                name="value",
                codomain_basis=(FilteredBasisVector("a", 2),),
                codomain_relations=(),
                symbol_map=FilteredSymbolMap(
                    "value_map", 2, {"control": {"a": 1}}
                ),
                distinguished={"a": 2},
            ),
            FilteredCoupledBlock(
                name="jet",
                codomain_basis=(FilteredBasisVector("b", 3),),
                codomain_relations=(),
                symbol_map=FilteredSymbolMap(
                    "jet_map", 3, {"control": {"b": 1}}
                ),
                distinguished={"b": 2},
            ),
        ),
    )
    certificate = compile_filtered_coupled_blocks(problem)
    assert not certificate.distinguished_survives
    assert certificate.decomposition_by_column == (
        ("common_control:control", "2"),
    )


def test_coupled_blocks_validate_every_shift_and_relation_descent() -> None:
    wrong_shift = FilteredCoupledBlockProblem(
        name="alien_wrong_block_shift",
        domain_basis=(FilteredBasisVector("control", 0),),
        domain_relations=(),
        blocks=(
            FilteredCoupledBlock(
                name="bad",
                codomain_basis=(FilteredBasisVector("a", 2),),
                codomain_relations=(),
                symbol_map=FilteredSymbolMap(
                    "bad_map", 1, {"control": {"a": 1}}
                ),
                distinguished={"a": 1},
            ),
        ),
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_coupled_blocks(wrong_shift)
    assert error.value.code == "wrong_symbol_shift"

    bad_relation = FilteredCoupledBlockProblem(
        name="alien_bad_block_relation",
        domain_basis=(
            FilteredBasisVector("left", 0),
            FilteredBasisVector("right", 0),
        ),
        domain_relations=(
            FilteredRelation("equal", 0, {"left": 1, "right": -1}),
        ),
        blocks=(
            FilteredCoupledBlock(
                name="bad",
                codomain_basis=(
                    FilteredBasisVector("a", 1),
                    FilteredBasisVector("b", 1),
                ),
                codomain_relations=(),
                symbol_map=FilteredSymbolMap(
                    "bad_map",
                    1,
                    {"left": {"a": 1}, "right": {"b": 1}},
                ),
                distinguished={"a": 1},
            ),
        ),
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_coupled_blocks(bad_relation)
    assert error.value.code == "symbol_relation_not_invariant"


def test_coupled_blocks_reject_incomplete_common_domain() -> None:
    problem = FilteredCoupledBlockProblem(
        name="alien_incomplete_common_domain",
        domain_basis=(
            FilteredBasisVector("left", 0),
            FilteredBasisVector("right", 0),
        ),
        domain_relations=(),
        blocks=(
            FilteredCoupledBlock(
                name="bad",
                codomain_basis=(FilteredBasisVector("a", 1),),
                codomain_relations=(),
                symbol_map=FilteredSymbolMap(
                    "bad_map", 1, {"left": {"a": 1}}
                ),
                distinguished={"a": 1},
            ),
        ),
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_coupled_blocks(problem)
    assert error.value.code == "incomplete_symbol_domain"


def _polynomial_fiber_problem(
    *,
    first_demand: int = 1,
    second_demand: int,
    rational_point: dict[str, int] | None = None,
) -> FilteredPolynomialFiberProblem:
    return FilteredPolynomialFiberProblem(
        name=f"alien_polynomial_fiber_{second_demand}",
        linearization=FilteredCoupledBlockProblem(
            name="alien_polynomial_linearization",
            domain_basis=(
                FilteredBasisVector("x", 0),
                FilteredBasisVector("x2", 0),
            ),
            domain_relations=(),
            blocks=(
                FilteredCoupledBlock(
                    name="value",
                    codomain_basis=(FilteredBasisVector("a", 1),),
                    codomain_relations=(),
                    symbol_map=FilteredSymbolMap(
                        "value_map",
                        1,
                        {"x": {"a": -1}, "x2": {}},
                    ),
                    distinguished={"a": first_demand},
                ),
                FilteredCoupledBlock(
                    name="square",
                    codomain_basis=(FilteredBasisVector("b", 2),),
                    codomain_relations=(),
                    symbol_map=FilteredSymbolMap(
                        "square_map",
                        2,
                        {"x": {}, "x2": {"b": -1}},
                    ),
                    distinguished={"b": second_demand},
                ),
            ),
        ),
        parameters=("control",),
        monomial_exponents={"x": (1,), "x2": (2,)},
        rational_point=rational_point or {},
    )


def test_polynomial_fiber_refutes_relaxed_monomial_cancellation() -> None:
    certificate = compile_filtered_polynomial_fiber(
        _polynomial_fiber_problem(second_demand=2)
    )
    assert not certificate.linearized_bundle_survives
    assert certificate.common_control_rank == 2
    assert certificate.independent_equation_count == 2
    assert certificate.unit_ideal
    assert certificate.fiber_status == "empty_over_algebraic_closure"
    assert certificate.groebner_basis == ("1",)


def test_polynomial_fiber_verifies_an_exact_rational_point() -> None:
    certificate = compile_filtered_polynomial_fiber(
        _polynomial_fiber_problem(
            first_demand=2,
            second_demand=4,
            rational_point={"control": 1 + 1},
        )
    )
    assert not certificate.unit_ideal
    assert certificate.rational_point_verified
    assert certificate.fiber_status == "rational_point_verified"
    assert certificate.rational_point_by_parameter == (("control", "2"),)


def test_polynomial_fiber_keeps_a_proper_ideal_unresolved() -> None:
    problem = _polynomial_fiber_problem(second_demand=2)
    single_equation = FilteredPolynomialFiberProblem(
        name="alien_proper_polynomial_ideal",
        linearization=FilteredCoupledBlockProblem(
            name="alien_square_linearization",
            domain_basis=problem.linearization.domain_basis,
            domain_relations=(),
            blocks=(problem.linearization.blocks[1],),
        ),
        parameters=problem.parameters,
        monomial_exponents=problem.monomial_exponents,
    )
    certificate = compile_filtered_polynomial_fiber(single_equation)
    assert not certificate.unit_ideal
    assert not certificate.rational_point_verified
    assert certificate.fiber_status == "proper_ideal_unresolved"


def test_polynomial_fiber_rejects_bad_monomials_and_points() -> None:
    problem = _polynomial_fiber_problem(second_demand=4)
    incomplete = FilteredPolynomialFiberProblem(
        name="alien_incomplete_monomials",
        linearization=problem.linearization,
        parameters=problem.parameters,
        monomial_exponents={"x": (1,)},
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_polynomial_fiber(incomplete)
    assert error.value.code == "incomplete_polynomial_monomial_map"

    bad_point = FilteredPolynomialFiberProblem(
        name="alien_bad_polynomial_point",
        linearization=problem.linearization,
        parameters=problem.parameters,
        monomial_exponents=problem.monomial_exponents,
        rational_point={"control": 3},
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_polynomial_fiber(bad_point)
    assert error.value.code == "polynomial_rational_point_not_on_fiber"


def test_polynomial_fiber_eliminates_constant_linear_controls_exactly() -> None:
    domain = (
        FilteredBasisVector("x", 0),
        FilteredBasisVector("y", 0),
    )
    problem = FilteredPolynomialFiberProblem(
        name="alien_constant_linear_elimination",
        linearization=FilteredCoupledBlockProblem(
            name="alien_constant_linear_blocks",
            domain_basis=domain,
            domain_relations=(),
            blocks=(
                FilteredCoupledBlock(
                    name="first",
                    codomain_basis=(FilteredBasisVector("a", 1),),
                    codomain_relations=(),
                    symbol_map=FilteredSymbolMap(
                        "first_map", 1, {"x": {"a": 1}, "y": {"a": 1}}
                    ),
                    distinguished={},
                ),
                FilteredCoupledBlock(
                    name="second",
                    codomain_basis=(FilteredBasisVector("b", 2),),
                    codomain_relations=(),
                    symbol_map=FilteredSymbolMap(
                        "second_map", 2, {"x": {"b": 1}, "y": {"b": 1}}
                    ),
                    distinguished={"b": 1},
                ),
            ),
        ),
        parameters=("control_x", "control_y"),
        monomial_exponents={"x": (1, 0), "y": (0, 1)},
    )
    certificate = compile_filtered_polynomial_fiber(problem)
    assert certificate.unit_ideal
    assert certificate.groebner_basis == ("1",)
    assert certificate.eliminated_parameters == (
        "control_x",
        "control_y",
    )
    assert certificate.groebner_parameter_order == ()
    assert certificate.post_elimination_equations == ("1",)


def test_polynomial_fiber_uses_pure_power_radical_for_empty_fiber() -> None:
    problem = FilteredPolynomialFiberProblem(
        name="alien_pure_power_empty_fiber",
        linearization=FilteredCoupledBlockProblem(
            name="alien_pure_power_blocks",
            domain_basis=(
                FilteredBasisVector("x", 0),
                FilteredBasisVector("x2", 0),
            ),
            domain_relations=(),
            blocks=(
                FilteredCoupledBlock(
                    name="nilpotent",
                    codomain_basis=(FilteredBasisVector("a", 1),),
                    codomain_relations=(),
                    symbol_map=FilteredSymbolMap(
                        "nilpotent_map", 1, {"x": {}, "x2": {"a": 1}}
                    ),
                    distinguished={},
                ),
                FilteredCoupledBlock(
                    name="incompatible",
                    codomain_basis=(FilteredBasisVector("b", 2),),
                    codomain_relations=(),
                    symbol_map=FilteredSymbolMap(
                        "incompatible_map", 2, {"x": {"b": 1}, "x2": {}}
                    ),
                    distinguished={"b": 1},
                ),
            ),
        ),
        parameters=("control",),
        monomial_exponents={"x": (1,), "x2": (2,)},
    )
    certificate = compile_filtered_polynomial_fiber(problem)
    assert certificate.unit_ideal
    assert certificate.radical_zero_parameters == (("control", 2),)
    assert certificate.groebner_method == "constant_linear_elimination_over_QQ"


def test_polynomial_fiber_substitutes_a_rational_linear_pivot() -> None:
    problem = FilteredPolynomialFiberProblem(
        name="alien_triangular_polynomial_fiber",
        linearization=FilteredCoupledBlockProblem(
            name="alien_triangular_blocks",
            domain_basis=(
                FilteredBasisVector("x", 0),
                FilteredBasisVector("y", 0),
                FilteredBasisVector("x2", 0),
                FilteredBasisVector("y2", 0),
            ),
            domain_relations=(),
            blocks=(
                FilteredCoupledBlock(
                    name="linear",
                    codomain_basis=(FilteredBasisVector("a", 1),),
                    codomain_relations=(),
                    symbol_map=FilteredSymbolMap(
                        "linear_map",
                        1,
                        {
                            "x": {"a": 1},
                            "y": {"a": 1},
                            "x2": {},
                            "y2": {},
                        },
                    ),
                    distinguished={},
                ),
                FilteredCoupledBlock(
                    name="quadratic",
                    codomain_basis=(FilteredBasisVector("b", 2),),
                    codomain_relations=(),
                    symbol_map=FilteredSymbolMap(
                        "quadratic_map",
                        2,
                        {
                            "x": {},
                            "y": {},
                            "x2": {"b": 1},
                            "y2": {"b": 1},
                        },
                    ),
                    distinguished={"b": 1},
                ),
            ),
        ),
        parameters=("control_x", "control_y"),
        monomial_exponents={
            "x": (1, 0),
            "y": (0, 1),
            "x2": (2, 0),
            "y2": (0, 2),
        },
    )
    certificate = compile_filtered_polynomial_fiber(problem)
    assert not certificate.unit_ideal
    assert certificate.triangular_substitutions == (
        ("control_x", "-control_y"),
    )
    assert certificate.groebner_parameter_order == ("control_y",)
    assert certificate.fiber_status == "proper_ideal_unresolved"


def test_cross_grade_symbol_cokernel_and_relation_descent() -> None:
    problem = FilteredSymbolCokernelProblem(
        name="alien_lowering_symbol",
        domain_basis=(
            FilteredBasisVector("u0", 1),
            FilteredBasisVector("u1", 1),
        ),
        domain_relations=(
            FilteredRelation("u_equal", 1, {"u0": 1, "u1": -1}),
        ),
        codomain_basis=(
            FilteredBasisVector("v0", 0),
            FilteredBasisVector("v1", 0),
            FilteredBasisVector("v2", 0),
        ),
        codomain_relations=(
            FilteredRelation("v_equal", 0, {"v1": 1, "v2": -1}),
        ),
        maps=(
            FilteredSymbolMap(
                "sigma_minus_one",
                -1,
                {"u0": {"v1": 1}, "u1": {"v2": 1}},
            ),
        ),
        distinguished={"v0": 3},
    )
    certificate = compile_filtered_symbol_cokernel(problem)
    assert certificate.map_shifts == (("sigma_minus_one", -1),)
    assert certificate.domain_relation_rank == 1
    assert certificate.codomain_relation_rank == 1
    assert certificate.symbol_image_rank == 2
    assert certificate.constraint_rank == 2
    assert certificate.cokernel_dimension == 1
    assert certificate.distinguished_survives
    assert certificate.witness_by_codomain_basis == (("v0", "1/3"),)


def test_cross_grade_symbol_rejects_bad_relation_descent() -> None:
    problem = FilteredSymbolCokernelProblem(
        name="bad_lowering_symbol",
        domain_basis=(
            FilteredBasisVector("u0", 1),
            FilteredBasisVector("u1", 1),
        ),
        domain_relations=(
            FilteredRelation("u_equal", 1, {"u0": 1, "u1": -1}),
        ),
        codomain_basis=(
            FilteredBasisVector("v0", 0),
            FilteredBasisVector("v1", 0),
        ),
        codomain_relations=(),
        maps=(
            FilteredSymbolMap(
                "sigma_minus_one",
                -1,
                {"u0": {"v0": 1}, "u1": {"v1": 1}},
            ),
        ),
        distinguished={"v0": 1},
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_symbol_cokernel(problem)
    assert error.value.code == "symbol_relation_not_invariant"


def _alien_reachability_problem(
    forcing_columns: dict[str, dict[str, int]],
) -> FilteredReachabilityProblem:
    symbol_problem = FilteredSymbolCokernelProblem(
        name="alien_controlled_jet",
        domain_basis=(FilteredBasisVector("control", 1),),
        domain_relations=(),
        codomain_basis=(
            FilteredBasisVector("value", 0),
            FilteredBasisVector("first_jet", 0),
        ),
        codomain_relations=(),
        maps=(
            FilteredSymbolMap(
                "control_value",
                -1,
                {"control": {"value": 1}},
            ),
        ),
        distinguished={"first_jet": 1},
    )
    return FilteredReachabilityProblem(
        name="alien_forcing_after_control",
        symbol_problem=symbol_problem,
        forcing_columns=forcing_columns,
    )


def test_reachability_separates_ambient_cokernel_from_forcing() -> None:
    certificate = compile_filtered_reachability(
        _alien_reachability_problem({"family_value": {"value": 3}})
    )
    assert certificate.cokernel_dimension == 1
    assert certificate.forcing_span_rank == 1
    assert certificate.reachable_cokernel_dimension == 0
    assert certificate.unreachable_cokernel_dimension == 1
    assert certificate.forcing_survives_by_name == (
        ("family_value", False),
    )


def test_reachability_detects_excited_surviving_direction() -> None:
    certificate = compile_filtered_reachability(
        _alien_reachability_problem(
            {
                "family_value": {"value": 3},
                "family_jet": {"first_jet": 2},
            }
        )
    )
    assert certificate.cokernel_dimension == 1
    assert certificate.reachable_cokernel_dimension == 1
    assert certificate.unreachable_cokernel_dimension == 0
    assert certificate.forcing_survives_by_name == (
        ("family_value", False),
        ("family_jet", True),
    )


def test_reachability_rejects_unknown_or_zero_forcing() -> None:
    with pytest.raises(FilteredObstructionError) as unknown:
        compile_filtered_reachability(
            _alien_reachability_problem({"bad": {"missing": 1}})
        )
    assert unknown.value.code == "unknown_basis_name"

    with pytest.raises(FilteredObstructionError) as zero:
        compile_filtered_reachability(
            _alien_reachability_problem({"zero": {"value": 0}})
        )
    assert zero.value.code == "zero_forcing_column"


def _alien_surplus_problem(
    *,
    surplus_columns: dict[str, dict[str, int]],
    terminal_columns: dict[str, dict[str, int]],
) -> FilteredSurplusProjectionProblem:
    return FilteredSurplusProjectionProblem(
        name="alien_surplus_before_terminal",
        domain_basis=(
            FilteredBasisVector("x", 0),
            FilteredBasisVector("y", 0),
        ),
        domain_relations=(),
        surplus_basis=(FilteredBasisVector("higher", 1),),
        surplus_relations=(),
        terminal_basis=(FilteredBasisVector("terminal", 2),),
        terminal_relations=(),
        surplus_map=FilteredSymbolMap(
            "higher_projection",
            1,
            surplus_columns,
        ),
        terminal_map=FilteredSymbolMap(
            "terminal_projection",
            2,
            terminal_columns,
        ),
        distinguished_terminal={"terminal": 1},
    )


def test_surplus_projection_reports_forced_higher_payment() -> None:
    certificate = compile_filtered_surplus_projection(
        _alien_surplus_problem(
            surplus_columns={"x": {"higher": 1}, "y": {}},
            terminal_columns={"x": {"terminal": 1}, "y": {}},
        )
    )
    assert certificate.surplus_image_rank == 1
    assert certificate.surplus_kernel_dimension == 1
    assert certificate.terminal_reachable_without_surplus_dimension == 0
    assert not certificate.distinguished_cancellable_without_surplus
    assert certificate.distinguished_pairing == "1"
    assert certificate.witness_by_terminal_basis == (("terminal", "1"),)
    assert certificate.distinguished_surplus_is_zero
    assert certificate.distinguished_surplus_reachable
    assert not certificate.distinguished_pair_cancellable


def test_surplus_projection_uses_complete_kernel_not_columnwise_checks() -> None:
    certificate = compile_filtered_surplus_projection(
        _alien_surplus_problem(
            surplus_columns={
                "x": {"higher": 1},
                "y": {"higher": 1},
            },
            terminal_columns={"x": {"terminal": 1}, "y": {}},
        )
    )
    assert certificate.surplus_kernel_dimension == 1
    assert certificate.terminal_reachable_without_surplus_dimension == 1
    assert certificate.distinguished_cancellable_without_surplus
    assert certificate.cancellation_by_domain_basis == (
        ("x", "1"),
        ("y", "-1"),
    )


def test_surplus_projection_detects_direct_surplus_free_control() -> None:
    certificate = compile_filtered_surplus_projection(
        _alien_surplus_problem(
            surplus_columns={"x": {}, "y": {}},
            terminal_columns={"x": {"terminal": 1}, "y": {}},
        )
    )
    assert certificate.surplus_image_rank == 0
    assert certificate.surplus_kernel_dimension == 2
    assert certificate.distinguished_cancellable_without_surplus
    assert certificate.cancellation_by_domain_basis == (("x", "1"),)


def test_affine_surplus_projection_solves_both_demands() -> None:
    homogeneous = _alien_surplus_problem(
        surplus_columns={
            "x": {"higher": 1},
            "y": {"higher": 1},
        },
        terminal_columns={"x": {"terminal": 1}, "y": {}},
    )
    affine = FilteredSurplusProjectionProblem(
        **{
            **homogeneous.__dict__,
            "name": "alien_affine_surplus_and_terminal",
            "distinguished_surplus": {"higher": 2},
            "distinguished_terminal": {"terminal": 1},
        }
    )
    certificate = compile_filtered_surplus_projection(affine)
    assert not certificate.distinguished_surplus_is_zero
    assert certificate.distinguished_surplus_reachable
    assert certificate.distinguished_pair_cancellable
    assert not certificate.distinguished_cancellable_without_surplus
    assert certificate.cancellation_by_domain_basis == (
        ("x", "1"),
        ("y", "1"),
    )


def test_affine_surplus_projection_separates_terminal_residual() -> None:
    problem = FilteredSurplusProjectionProblem(
        name="alien_affine_terminal_failure",
        domain_basis=(FilteredBasisVector("x", 0),),
        domain_relations=(),
        surplus_basis=(FilteredBasisVector("higher", 1),),
        surplus_relations=(),
        terminal_basis=(FilteredBasisVector("terminal", 2),),
        terminal_relations=(),
        surplus_map=FilteredSymbolMap(
            "higher_projection",
            1,
            {"x": {"higher": 1}},
        ),
        terminal_map=FilteredSymbolMap(
            "terminal_projection",
            2,
            {"x": {"terminal": 1}},
        ),
        distinguished_surplus={"higher": 1},
        distinguished_terminal={"terminal": 2},
    )
    certificate = compile_filtered_surplus_projection(problem)
    assert certificate.distinguished_surplus_reachable
    assert not certificate.distinguished_pair_cancellable
    assert certificate.distinguished_pairing == "1"
    assert certificate.witness_by_terminal_basis == (("terminal", "1"),)


def test_affine_surplus_projection_separates_unreachable_surplus() -> None:
    problem = FilteredSurplusProjectionProblem(
        name="alien_affine_surplus_failure",
        domain_basis=(FilteredBasisVector("x", 0),),
        domain_relations=(),
        surplus_basis=(
            FilteredBasisVector("higher_0", 1),
            FilteredBasisVector("higher_1", 1),
        ),
        surplus_relations=(),
        terminal_basis=(FilteredBasisVector("terminal", 2),),
        terminal_relations=(),
        surplus_map=FilteredSymbolMap(
            "higher_projection",
            1,
            {"x": {"higher_0": 1}},
        ),
        terminal_map=FilteredSymbolMap(
            "terminal_projection",
            2,
            {"x": {"terminal": 1}},
        ),
        distinguished_surplus={"higher_1": 1},
        distinguished_terminal={"terminal": 1},
    )
    certificate = compile_filtered_surplus_projection(problem)
    assert not certificate.distinguished_surplus_reachable
    assert not certificate.distinguished_pair_cancellable
    assert certificate.distinguished_surplus_pairing == "1"
    assert certificate.witness_by_surplus_basis == (("higher_1", "1"),)


def test_surplus_projection_rejects_bad_relation_descent() -> None:
    problem = FilteredSurplusProjectionProblem(
        name="alien_bad_surplus_relation",
        domain_basis=(
            FilteredBasisVector("x", 0),
            FilteredBasisVector("y", 0),
        ),
        domain_relations=(
            FilteredRelation("same", 0, {"x": 1, "y": -1}),
        ),
        surplus_basis=(FilteredBasisVector("higher", 1),),
        surplus_relations=(),
        terminal_basis=(FilteredBasisVector("terminal", 2),),
        terminal_relations=(),
        surplus_map=FilteredSymbolMap(
            "bad_higher_projection",
            1,
            {"x": {"higher": 1}, "y": {}},
        ),
        terminal_map=FilteredSymbolMap(
            "terminal_projection",
            2,
            {"x": {}, "y": {}},
        ),
        distinguished_terminal={"terminal": 1},
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_surplus_projection(problem)
    assert error.value.code == "surplus_relation_not_invariant"


def test_surplus_projection_rejects_incomplete_or_moving_maps() -> None:
    incomplete = _alien_surplus_problem(
        surplus_columns={"x": {"higher": 1}},
        terminal_columns={"x": {"terminal": 1}, "y": {}},
    )
    with pytest.raises(FilteredObstructionError) as missing:
        compile_filtered_surplus_projection(incomplete)
    assert missing.value.code == "incomplete_symbol_domain"

    moving = FilteredSurplusProjectionProblem(
        **{
            **incomplete.__dict__,
            "surplus_map": FilteredSymbolMap(
                "moving_higher_projection",
                1,
                {"x": {"higher": 1}, "y": {}},
                relation_velocities={"ghost": {}},
            ),
        }
    )
    with pytest.raises(FilteredObstructionError) as dynamic:
        compile_filtered_surplus_projection(moving)
    assert dynamic.value.code == "moving_surplus_relation_not_supported"


def _alien_graph_problem(
    *,
    distinguished_source: dict[str, int] | None = None,
    distinguished_target: dict[str, int] | None = None,
) -> FilteredGraphQuotientProblem:
    return FilteredGraphQuotientProblem(
        name="alien_exact_boundary_graph",
        source_basis=(
            FilteredBasisVector("a", 1),
            FilteredBasisVector("b", 1),
        ),
        source_relations=(),
        target_basis=(FilteredBasisVector("h", 0),),
        target_relations=(),
        boundary_map=FilteredSymbolMap(
            "pullback",
            1,
            {"h": {"a": 1}},
        ),
        distinguished_source=distinguished_source or {"b": 1},
        distinguished_target=distinguished_target or {"h": 1},
    )


def test_graph_quotient_compresses_source_target_pair_exactly() -> None:
    certificate = compile_filtered_graph_quotient(_alien_graph_problem())
    assert certificate.relation_transport_verified
    assert certificate.graph_quotient_dimension == 2
    assert certificate.source_quotient_dimension == 2
    assert certificate.distinguished_survives
    assert certificate.compressed_source_survives
    assert certificate.compressed_source_by_basis == (
        ("a", "-1"),
        ("b", "1"),
    )
    assert certificate.compressed_witness_by_source_basis == (("a", "-1"),)


def test_graph_quotient_rejects_an_exact_boundary_pair() -> None:
    certificate = compile_filtered_graph_quotient(
        _alien_graph_problem(
            distinguished_source={"a": 3},
            distinguished_target={"h": 3},
        )
    )
    assert not certificate.distinguished_survives
    assert not certificate.compressed_source_survives
    assert certificate.compressed_source_by_basis == ()
    assert certificate.decomposition_by_graph_column == (
        ("symbol:pullback_graph:h", "3"),
    )


def test_graph_quotient_checks_target_relation_descent() -> None:
    problem = FilteredGraphQuotientProblem(
        name="alien_graph_bad_relation_descent",
        source_basis=(FilteredBasisVector("a", 1),),
        source_relations=(),
        target_basis=(
            FilteredBasisVector("h0", 0),
            FilteredBasisVector("h1", 0),
        ),
        target_relations=(
            FilteredRelation("same", 0, {"h0": 1, "h1": -1}),
        ),
        boundary_map=FilteredSymbolMap(
            "bad_pullback",
            1,
            {"h0": {"a": 1}, "h1": {}},
        ),
        distinguished_source={"a": 1},
        distinguished_target={},
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_graph_quotient(problem)
    assert error.value.code == "symbol_relation_not_invariant"


def test_graph_quotient_refuses_moving_boundary_relations() -> None:
    base = _alien_graph_problem()
    problem = FilteredGraphQuotientProblem(
        **{
            **base.__dict__,
            "boundary_map": FilteredSymbolMap(
                "moving_pullback",
                1,
                {"h": {"a": 1}},
                relation_velocities={"ghost": {}},
            ),
        }
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_graph_quotient(problem)
    assert error.value.code == "moving_graph_boundary_not_supported"


def _alien_induction_problem() -> FilteredInductionProblem:
    return FilteredInductionProblem(
        name="alien_budgeted_triangular_induction",
        states=(
            FilteredInductionState(
                name="top_shell",
                rank=(2, 1),
                local_certificate_sha256="0" * 64,
                complete_outcomes=("top_to_lower", "top_source_charge"),
            ),
            FilteredInductionState(
                name="lower_shell",
                rank=(1, 9),
                local_certificate_sha256="1" * 64,
                complete_outcomes=("lower_terminal", "lower_target_charge"),
            ),
        ),
        transitions=(
            FilteredInductionTransition(
                name="top_to_lower",
                source="top_shell",
                outcome="descend",
                target="lower_shell",
            ),
            FilteredInductionTransition(
                name="top_source_charge",
                source="top_shell",
                outcome="source_charged",
            ),
            FilteredInductionTransition(
                name="lower_terminal",
                source="lower_shell",
                outcome="terminal_survives",
            ),
            FilteredInductionTransition(
                name="lower_target_charge",
                source="lower_shell",
                outcome="target_charged",
            ),
        ),
        initial_states=("top_shell",),
    )


def test_filtered_induction_closes_every_declared_branch() -> None:
    certificate = compile_filtered_induction(_alien_induction_problem())
    assert certificate.local_coverage_verified
    assert certificate.strict_descent_verified
    assert certificate.all_states_reachable
    assert certificate.every_declared_branch_closes
    assert certificate.maximum_uncharged_descent_length == 1
    assert not certificate.adapter_completeness_inferred
    assert dict(certificate.branch_outcome_counts) == {
        "terminal_survives": 1,
        "source_charged": 1,
        "target_charged": 1,
        "descend": 1,
    }


def test_filtered_induction_rejects_a_nondecreasing_edge() -> None:
    problem = _alien_induction_problem()
    bad_states = (
        problem.states[0],
        FilteredInductionState(
            **{**problem.states[1].__dict__, "rank": (2, 2)}
        ),
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_induction(
            FilteredInductionProblem(
                **{**problem.__dict__, "states": bad_states}
            )
        )
    assert error.value.code == "nondecreasing_induction_transition"


def test_filtered_induction_rejects_incomplete_local_coverage() -> None:
    problem = _alien_induction_problem()
    incomplete = FilteredInductionState(
        **{
            **problem.states[0].__dict__,
            "complete_outcomes": ("top_to_lower",),
        }
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_induction(
            FilteredInductionProblem(
                **{
                    **problem.__dict__,
                    "states": (incomplete, problem.states[1]),
                }
            )
        )
    assert error.value.code == "incomplete_local_coverage"


def test_filtered_induction_rejects_unbound_or_unreachable_states() -> None:
    problem = _alien_induction_problem()
    bad_digest = FilteredInductionState(
        **{
            **problem.states[0].__dict__,
            "local_certificate_sha256": "not-a-digest",
        }
    )
    with pytest.raises(FilteredObstructionError) as digest_error:
        compile_filtered_induction(
            FilteredInductionProblem(
                **{
                    **problem.__dict__,
                    "states": (bad_digest, problem.states[1]),
                }
            )
        )
    assert digest_error.value.code == "invalid_local_certificate_digest"

    with pytest.raises(FilteredObstructionError) as reachability_error:
        compile_filtered_induction(
            FilteredInductionProblem(
                **{**problem.__dict__, "initial_states": ("lower_shell",)}
            )
        )
    assert reachability_error.value.code == "unreachable_induction_state"


def _alien_asymptotic_problem(
    *, order_intercept: int = 3,
) -> FilteredAsymptoticInductionProblem:
    induction = _alien_induction_problem()
    problem_name = "alien_asymptotic_budgeted_induction"
    return FilteredAsymptoticInductionProblem(
        name=problem_name,
        induction=induction,
        threshold=2,
        occurrence_order_intercept=order_intercept,
        occurrence_order_slope=2,
        occurrence_support_evidence=make_filtered_asymptotic_evidence(
            claim=FilteredAsymptoticClaim.INFINITE_OCCURRENCE_SUPPORT,
            subject_id=problem_name,
            induction=induction,
            authority=EvidenceAuthority.ADAPTER_EXACT,
            scope=(
                FilteredAsymptoticEvidenceScope.ALL_UNBOUNDED_OCCURRENCE_INDICES
            ),
            evidence_sha256="2" * 64,
        ),
        closing_witnesses=(
            FilteredAsymptoticRateWitness(
                transition_name="top_source_charge",
                side="source",
                payment_order_intercept=order_intercept,
                payment_order_slope=2,
                payment_excess_intercept=-1,
                payment_excess_slope=4,
                coefficient_certificate_sha256="3" * 64,
            ),
            FilteredAsymptoticRateWitness(
                transition_name="lower_terminal",
                side="source",
                payment_order_intercept=order_intercept,
                payment_order_slope=2,
                payment_excess_intercept=1,
                payment_excess_slope=5,
                coefficient_certificate_sha256="4" * 64,
            ),
            FilteredAsymptoticRateWitness(
                transition_name="lower_target_charge",
                side="target",
                payment_order_intercept=order_intercept,
                payment_order_slope=2,
                payment_excess_intercept=0,
                payment_excess_slope=4,
                coefficient_certificate_sha256="5" * 64,
            ),
        ),
    )


def test_filtered_asymptotic_induction_closes_limsup_rate() -> None:
    certificate = compile_filtered_asymptotic_induction(
        _alien_asymptotic_problem()
    )
    assert certificate.every_closing_branch_rate_certified
    assert certificate.same_order_payment_verified
    assert certificate.no_rebilling_verified
    assert certificate.parameter_shift_invariance_verified
    assert certificate.minimum_certified_rate == "2"
    assert certificate.maximum_uncharged_descent_length == 1
    assert not certificate.adapter_completeness_inferred
    assert certificate.asymptotic_certificate_sha256 == (
        "1f1e0285ec9274bc0f03bad062636326ccc9a406025747d560597a3f8d095cd2"
    )
    assert certificate.asymptotic_proof_envelope_sha256 == (
        "a0502073459d7e0fdbaed7fc041ec184a20ea23ed1d96e6272e4b8a7155212d1"
    )

    shifted = compile_filtered_asymptotic_induction(
        _alien_asymptotic_problem(order_intercept=103)
    )
    assert shifted.minimum_certified_rate == certificate.minimum_certified_rate


def test_filtered_asymptotic_induction_rejects_missing_or_cheap_branch() -> None:
    problem = _alien_asymptotic_problem()
    with pytest.raises(FilteredObstructionError) as missing_error:
        compile_filtered_asymptotic_induction(
            FilteredAsymptoticInductionProblem(
                **{
                    **problem.__dict__,
                    "closing_witnesses": problem.closing_witnesses[:-1],
                }
            )
        )
    assert missing_error.value.code == "missing_closing_rate_witness"

    cheap = FilteredAsymptoticRateWitness(
        **{
            **problem.closing_witnesses[0].__dict__,
            "payment_excess_slope": 3,
        }
    )
    with pytest.raises(FilteredObstructionError) as cheap_error:
        compile_filtered_asymptotic_induction(
            FilteredAsymptoticInductionProblem(
                **{
                    **problem.__dict__,
                    "closing_witnesses": (
                        cheap,
                        *problem.closing_witnesses[1:],
                    ),
                }
            )
        )
    assert cheap_error.value.code == "subcritical_closing_branch"


def test_filtered_asymptotic_induction_rejects_rebilling_and_side_mismatch() -> None:
    problem = _alien_asymptotic_problem()
    rebilled = FilteredAsymptoticRateWitness(
        **{
            **problem.closing_witnesses[0].__dict__,
            "payment_order_intercept": 7,
        }
    )
    with pytest.raises(FilteredObstructionError) as rebilling_error:
        compile_filtered_asymptotic_induction(
            FilteredAsymptoticInductionProblem(
                **{
                    **problem.__dict__,
                    "closing_witnesses": (
                        rebilled,
                        *problem.closing_witnesses[1:],
                    ),
                }
            )
        )
    assert rebilling_error.value.code == "payment_not_at_occurrence_order"

    wrong_side = FilteredAsymptoticRateWitness(
        **{
            **problem.closing_witnesses[0].__dict__,
            "side": "target",
        }
    )
    with pytest.raises(FilteredObstructionError) as side_error:
        compile_filtered_asymptotic_induction(
            FilteredAsymptoticInductionProblem(
                **{
                    **problem.__dict__,
                    "closing_witnesses": (
                        wrong_side,
                        *problem.closing_witnesses[1:],
                    ),
                }
            )
        )
    assert side_error.value.code == "charged_side_mismatch"


def test_asymptotic_induction_problem_has_no_boolean_assertion_fields() -> None:
    hints = get_type_hints(FilteredAsymptoticInductionProblem)
    assert all(hint is not bool for hint in hints.values())


def test_filtered_asymptotic_induction_rejects_tampered_support() -> None:
    problem = _alien_asymptotic_problem()
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_asymptotic_induction(
            FilteredAsymptoticInductionProblem(
                **{
                    **problem.__dict__,
                    "occurrence_support_evidence": replace(
                        problem.occurrence_support_evidence,
                        evidence_sha256="9" * 64,
                    ),
                }
            )
        )
    assert error.value.code == "evidence_receipt_digest_mismatch"


@pytest.mark.parametrize(
    ("authority", "scope", "error_code"),
    (
        (
            EvidenceAuthority.FINITE_EXPERIMENT,
            FilteredAsymptoticEvidenceScope.ALL_UNBOUNDED_OCCURRENCE_INDICES,
            "asymptotic_evidence_authority_insufficient",
        ),
        (
            EvidenceAuthority.ADAPTER_EXACT,
            FilteredAsymptoticEvidenceScope.FINITE_WINDOW,
            "asymptotic_evidence_scope_mismatch",
        ),
    ),
)
def test_filtered_asymptotic_induction_rejects_weak_support_authority_or_scope(
    authority: EvidenceAuthority,
    scope: FilteredAsymptoticEvidenceScope,
    error_code: str,
) -> None:
    problem = _alien_asymptotic_problem()
    evidence = make_filtered_asymptotic_evidence(
        claim=FilteredAsymptoticClaim.INFINITE_OCCURRENCE_SUPPORT,
        subject_id=problem.name,
        induction=problem.induction,
        authority=authority,
        scope=scope,
        evidence_sha256="2" * 64,
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_asymptotic_induction(
            FilteredAsymptoticInductionProblem(
                **{
                    **problem.__dict__,
                    "occurrence_support_evidence": evidence,
                }
            )
        )
    assert error.value.code == error_code


def test_filtered_asymptotic_induction_rejects_cross_subject_or_graph() -> None:
    problem = _alien_asymptotic_problem()
    wrong_subject = make_filtered_asymptotic_evidence(
        claim=FilteredAsymptoticClaim.INFINITE_OCCURRENCE_SUPPORT,
        subject_id="another_asymptotic_problem",
        induction=problem.induction,
        authority=EvidenceAuthority.ADAPTER_EXACT,
        scope=(
            FilteredAsymptoticEvidenceScope.ALL_UNBOUNDED_OCCURRENCE_INDICES
        ),
        evidence_sha256="2" * 64,
    )
    with pytest.raises(FilteredObstructionError) as subject_error:
        compile_filtered_asymptotic_induction(
            FilteredAsymptoticInductionProblem(
                **{
                    **problem.__dict__,
                    "occurrence_support_evidence": wrong_subject,
                }
            )
        )
    assert subject_error.value.code == "asymptotic_evidence_subject_mismatch"

    other_state = replace(
        problem.induction.states[0],
        local_certificate_sha256="9" * 64,
    )
    other_induction = replace(
        problem.induction,
        states=(other_state, *problem.induction.states[1:]),
    )
    wrong_graph = make_filtered_asymptotic_evidence(
        claim=FilteredAsymptoticClaim.INFINITE_OCCURRENCE_SUPPORT,
        subject_id=problem.name,
        induction=other_induction,
        authority=EvidenceAuthority.ADAPTER_EXACT,
        scope=(
            FilteredAsymptoticEvidenceScope.ALL_UNBOUNDED_OCCURRENCE_INDICES
        ),
        evidence_sha256="2" * 64,
    )
    with pytest.raises(FilteredObstructionError) as graph_error:
        compile_filtered_asymptotic_induction(
            FilteredAsymptoticInductionProblem(
                **{
                    **problem.__dict__,
                    "occurrence_support_evidence": wrong_graph,
                }
            )
        )
    assert graph_error.value.code == "asymptotic_evidence_context_mismatch"


def _puiseux_context(
    *,
    germ_id: str = "alien_fractional_holonomy.germ",
    exponent: str = "5/2",
    digest: str = "6" * 64,
):
    return make_filtered_puiseux_context(
        germ_id=germ_id,
        local_coordinate_id="formal_coordinate_u_at_selected_branch",
        first_fractional_exponent=exponent,
        local_expansion_evidence_sha256=digest,
    )


def _puiseux_evidence(
    context,
    *,
    flow_claim: FilteredPuiseuxClaim,
    coefficient_authority: EvidenceAuthority = EvidenceAuthority.ADAPTER_EXACT,
    flow_authority: EvidenceAuthority = EvidenceAuthority.ADAPTER_EXACT,
    coefficient_scope: FilteredPuiseuxEvidenceScope = (
        FilteredPuiseuxEvidenceScope.EXACT_FIRST_FRACTIONAL_GERM
    ),
    flow_scope: FilteredPuiseuxEvidenceScope = (
        FilteredPuiseuxEvidenceScope.EXACT_FORMAL_FLOW_IDENTITY
    ),
):
    digest = context.local_expansion_evidence_sha256
    return (
        make_filtered_puiseux_evidence(
            claim=FilteredPuiseuxClaim.REGULAR_LINEAR_COEFFICIENT_NONZERO,
            context=context,
            authority=coefficient_authority,
            scope=coefficient_scope,
            evidence_sha256=digest,
        ),
        make_filtered_puiseux_evidence(
            claim=(
                FilteredPuiseuxClaim.FIRST_FRACTIONAL_COEFFICIENT_NONZERO
            ),
            context=context,
            authority=coefficient_authority,
            scope=coefficient_scope,
            evidence_sha256=digest,
        ),
        make_filtered_puiseux_evidence(
            claim=flow_claim,
            context=context,
            authority=flow_authority,
            scope=flow_scope,
            evidence_sha256=digest,
        ),
    )


def _puiseux_problem(
    *,
    exponent: str = "5/2",
    name: str = "alien_fractional_holonomy",
) -> FilteredPuiseuxFlowProblem:
    context = _puiseux_context(exponent=exponent)
    return FilteredPuiseuxFlowProblem(
        name=name,
        context=context,
        evidence=_puiseux_evidence(
            context,
            flow_claim=FilteredPuiseuxClaim.JULIA_FLOW_IDENTITY,
        ),
    )


def _two_flow_puiseux_problem(
    *,
    exponent: str = "5/2",
    minimum_order: int = 2,
) -> FilteredTwoFlowPuiseuxProblem:
    context = _puiseux_context(
        germ_id="alien_two_sided_fractional_holonomy.germ",
        exponent=exponent,
        digest="9" * 64,
    )
    return FilteredTwoFlowPuiseuxProblem(
        name="alien_two_sided_fractional_holonomy",
        context=context,
        evidence=_puiseux_evidence(
            context,
            flow_claim=(
                FilteredPuiseuxClaim.TWO_FLOW_FACTORIZATION_IDENTITY
            ),
        ),
        minimum_generator_vanishing_order=minimum_order,
    )


def test_puiseux_problem_inputs_have_no_boolean_assertion_fields() -> None:
    assert bool not in get_type_hints(FilteredPuiseuxFlowProblem).values()
    assert bool not in get_type_hints(FilteredTwoFlowPuiseuxProblem).values()


def test_puiseux_flow_compiler_excludes_a_polynomial_generator() -> None:
    certificate = compile_filtered_puiseux_flow_obstruction(
        _puiseux_problem()
    )
    assert certificate.derivative_fractional_exponent == "3/2"
    assert certificate.nonroot_exponent_mismatch
    assert certificate.forced_root_multiplicity == "5/2"
    assert certificate.forced_root_multiplicity_is_noninteger
    assert certificate.polynomial_generator_excluded
    assert not certificate.adapter_completeness_inferred
    assert len(certificate.evidence_receipt_sha256) == 3
    assert certificate.puiseux_flow_certificate_sha256 == (
        "f92d623f934ca99088d243307796c6c17e79269165da95ac70ec56136b2034cc"
    )


@pytest.mark.parametrize(
    ("exponent", "error_code"),
    (("1", "nonregular_puiseux_exponent"), ("3", "integer_puiseux_exponent")),
)
def test_puiseux_flow_compiler_rejects_nonfractional_input(
    exponent: str,
    error_code: str,
) -> None:
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_puiseux_flow_obstruction(
            _puiseux_problem(
                exponent=exponent,
                name="bad_alien_fractional_holonomy",
            )
        )
    assert error.value.code == error_code


def test_puiseux_flow_compiler_rejects_missing_or_substituted_claim() -> None:
    problem = _puiseux_problem()
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_puiseux_flow_obstruction(
            replace(problem, evidence=problem.evidence[:2])
        )
    assert error.value.code == "puiseux_evidence_claim_set_incomplete"

    substitute = make_filtered_puiseux_evidence(
        claim=FilteredPuiseuxClaim.TWO_FLOW_FACTORIZATION_IDENTITY,
        context=problem.context,
        authority=EvidenceAuthority.ADAPTER_EXACT,
        scope=FilteredPuiseuxEvidenceScope.EXACT_FORMAL_FLOW_IDENTITY,
        evidence_sha256=problem.context.local_expansion_evidence_sha256,
    )
    with pytest.raises(FilteredObstructionError) as substitution_error:
        compile_filtered_puiseux_flow_obstruction(
            replace(problem, evidence=(*problem.evidence[:2], substitute))
        )
    assert substitution_error.value.code == (
        "puiseux_evidence_claim_set_incomplete"
    )


@pytest.mark.parametrize(
    ("authority", "scope", "error_code"),
    (
        (
            EvidenceAuthority.FINITE_EXPERIMENT,
            FilteredPuiseuxEvidenceScope.EXACT_FORMAL_FLOW_IDENTITY,
            "puiseux_evidence_authority_insufficient",
        ),
        (
            EvidenceAuthority.ADAPTER_EXACT,
            FilteredPuiseuxEvidenceScope.FINITE_TRUNCATION,
            "puiseux_evidence_scope_mismatch",
        ),
    ),
)
def test_puiseux_flow_compiler_rejects_weak_identity_evidence(
    authority: EvidenceAuthority,
    scope: FilteredPuiseuxEvidenceScope,
    error_code: str,
) -> None:
    problem = _puiseux_problem()
    evidence = _puiseux_evidence(
        problem.context,
        flow_claim=FilteredPuiseuxClaim.JULIA_FLOW_IDENTITY,
        flow_authority=authority,
        flow_scope=scope,
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_puiseux_flow_obstruction(
            replace(problem, evidence=evidence)
        )
    assert error.value.code == error_code


def test_puiseux_flow_compiler_rejects_tamper_and_cross_context() -> None:
    problem = _puiseux_problem()
    tampered = replace(problem.evidence[0], evidence_sha256="f" * 64)
    with pytest.raises(FilteredObstructionError) as tamper_error:
        compile_filtered_puiseux_flow_obstruction(
            replace(problem, evidence=(tampered, *problem.evidence[1:]))
        )
    assert tamper_error.value.code == "evidence_receipt_digest_mismatch"

    other = _puiseux_problem(exponent="7/3")
    with pytest.raises(FilteredObstructionError) as context_error:
        compile_filtered_puiseux_flow_obstruction(
            replace(
                problem,
                evidence=(other.evidence[0], *problem.evidence[1:]),
            )
        )
    assert context_error.value.code == "puiseux_evidence_context_mismatch"


def test_two_flow_puiseux_compiler_excludes_finite_factorization() -> None:
    certificate = compile_filtered_two_flow_puiseux_obstruction(
        _two_flow_puiseux_problem()
    )
    assert certificate.regular_finite_route_is_analytic
    assert certificate.infinity_route_equal_degrees_forced
    assert certificate.nonproportional_infinity_exponent_interval == (
        "1<lambda<2"
    )
    assert certificate.proportional_case_reduces_to_single_flow
    assert certificate.single_flow_polynomial_generator_excluded
    assert certificate.polynomial_two_flow_factorization_excluded
    assert not certificate.adapter_completeness_inferred
    assert len(certificate.evidence_receipt_sha256) == 3
    assert certificate.proportional_julia_receipt_sha256
    assert certificate.two_flow_puiseux_certificate_sha256 == (
        "78ac6ab89f4d74c41c10698c29009fd2b0d312d46cae8cdf6603d6f8bcc278a7"
    )


@pytest.mark.parametrize(
    ("changes", "error_code"),
    (
        (
            {"exponent": "3/2"},
            "insufficient_two_flow_exponent",
        ),
        (
            {"minimum_order": 1},
            "generator_not_tangent_to_identity",
        ),
    ),
)
def test_two_flow_puiseux_compiler_rejects_missing_premises(
    changes: dict[str, object],
    error_code: str,
) -> None:
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_two_flow_puiseux_obstruction(
            _two_flow_puiseux_problem(**changes)  # type: ignore[arg-type]
        )
    assert error.value.code == error_code


def test_two_flow_puiseux_compiler_rejects_wrong_flow_claim() -> None:
    problem = _two_flow_puiseux_problem()
    julia = make_filtered_puiseux_evidence(
        claim=FilteredPuiseuxClaim.JULIA_FLOW_IDENTITY,
        context=problem.context,
        authority=EvidenceAuthority.ADAPTER_EXACT,
        scope=FilteredPuiseuxEvidenceScope.EXACT_FORMAL_FLOW_IDENTITY,
        evidence_sha256=problem.context.local_expansion_evidence_sha256,
    )
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_two_flow_puiseux_obstruction(
            replace(problem, evidence=(*problem.evidence[:2], julia))
        )
    assert error.value.code == "puiseux_evidence_claim_set_incomplete"


def _polar_witt_problem(
    *,
    degree_multiplier: str | int = 2,
    include_face: bool = True,
    include_semidirect: bool = True,
    include_centralizer: bool = True,
) -> FilteredPolarWittFactorizationProblem:
    context = make_filtered_polar_witt_context(
        category_id="alien_tangent_polynomial_factorizations",
        filtration_id="alien_rees_newton_filtration",
        model=FilteredPolarWittModel.TANGENT_WITT_FIRST_DEFECT_NEWTON,
        adapter_evidence_sha256="b" * 64,
        centralizer_evidence_sha256="c" * 64,
    )
    rows = []
    if include_face:
        rows.append(make_filtered_polar_witt_evidence(
            claim=(
                FilteredPolarWittClaim.FINITE_MAXIMAL_FACE_DECOMPOSITION
            ),
            subject_id="alien_polar_witt.maximal_face",
            context=context,
            authority=EvidenceAuthority.ADAPTER_EXACT,
            scope=FilteredPolarWittEvidenceScope.ALL_FINITE_POSITIVE_FACES,
            evidence_sha256=context.adapter_evidence_sha256,
        ))
    if include_semidirect:
        rows.append(make_filtered_polar_witt_evidence(
            claim=(
                FilteredPolarWittClaim.SEMIDIRECT_NEWTON_QUOTIENT_APPLIES
            ),
            subject_id="alien_polar_witt.first_defect_quotient",
            context=context,
            authority=EvidenceAuthority.ADAPTER_EXACT,
            scope=(
                FilteredPolarWittEvidenceScope.EXACT_FIRST_DEFECT_QUOTIENT
            ),
            evidence_sha256=context.adapter_evidence_sha256,
        ))
    if include_centralizer:
        rows.append(make_filtered_polar_witt_evidence(
            claim=FilteredPolarWittClaim.CENTRALIZER_FLOW_EXCLUDED,
            subject_id="alien_polar_witt.centralizer",
            context=context,
            authority=EvidenceAuthority.FILTERED_COMPILER,
            scope=FilteredPolarWittEvidenceScope.SCALAR_CENTRALIZER_BRANCH,
            evidence_sha256=context.centralizer_evidence_sha256,
        ))
    return FilteredPolarWittFactorizationProblem(
        name="alien_polar_witt_factorization",
        threshold=2,
        degree_multiplier=degree_multiplier,
        context=context,
        evidence=tuple(rows),
    )


def test_polar_witt_problem_has_no_boolean_assertion_fields() -> None:
    assert bool not in get_type_hints(
        FilteredPolarWittFactorizationProblem
    ).values()


def test_polar_witt_compiler_closes_every_finite_positive_face() -> None:
    certificate = compile_filtered_polar_witt_factorization(
        _polar_witt_problem()
    )
    assert certificate.newton_invariant == "h*e+d*nu"
    assert certificate.tied_newton_faces_finite
    assert certificate.semidirect_transfer == "z/(1-exp(-z))"
    assert certificate.inverse_transfer_nonpolynomial_on_nonzero_polynomial_seed
    assert certificate.orbit_order_increment == "p=d-h>0"
    assert certificate.orbit_payment_degree_increment == "2*d"
    assert certificate.orbit_rate_formula == "2*(p+h)/p"
    assert certificate.noncentral_branch_strictly_supercritical
    assert certificate.centralizer_branch_reduces_to_polynomial_flow
    assert certificate.centralizer_polynomial_flow_excluded
    assert certificate.arbitrary_finite_polar_prefix_excluded
    assert not certificate.adapter_completeness_inferred
    assert len(certificate.evidence_receipt_sha256) == 3
    assert certificate.polar_witt_certificate_sha256 == (
        "56b97db9444fb0ecef119ec4d44666bd5d63e6b3f7cbc3e40a79b37507ed4333"
    )


@pytest.mark.parametrize(
    ("changes", "error_code"),
    (
        (
            {"include_face": False},
            "polar_witt_evidence_claim_set_incomplete",
        ),
        (
            {"include_semidirect": False},
            "missing_semidirect_newton_quotient",
        ),
        (
            {"include_centralizer": False},
            "polar_witt_evidence_claim_set_incomplete",
        ),
        (
            {"degree_multiplier": "3/2"},
            "insufficient_polar_orbit_rate",
        ),
    ),
)
def test_polar_witt_compiler_rejects_missing_branch_premises(
    changes: dict[str, object],
    error_code: str,
) -> None:
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_polar_witt_factorization(
            _polar_witt_problem(**changes)  # type: ignore[arg-type]
        )
    assert error.value.code == error_code


def test_polar_witt_compiler_rejects_tamper_and_cross_context() -> None:
    problem = _polar_witt_problem()
    tampered = replace(problem.evidence[0], subject_id="changed")
    with pytest.raises(FilteredObstructionError) as tamper_error:
        compile_filtered_polar_witt_factorization(
            replace(problem, evidence=(tampered, *problem.evidence[1:]))
        )
    assert tamper_error.value.code == "evidence_receipt_digest_mismatch"

    other_context = make_filtered_polar_witt_context(
        category_id="another_category",
        filtration_id=problem.context.filtration_id,
        model=problem.context.model,
        adapter_evidence_sha256=problem.context.adapter_evidence_sha256,
        centralizer_evidence_sha256=(
            problem.context.centralizer_evidence_sha256
        ),
    )
    graft = make_filtered_polar_witt_evidence(
        claim=FilteredPolarWittClaim.FINITE_MAXIMAL_FACE_DECOMPOSITION,
        subject_id="other.maximal_face",
        context=other_context,
        authority=EvidenceAuthority.ADAPTER_EXACT,
        scope=FilteredPolarWittEvidenceScope.ALL_FINITE_POSITIVE_FACES,
        evidence_sha256=other_context.adapter_evidence_sha256,
    )
    with pytest.raises(FilteredObstructionError) as context_error:
        compile_filtered_polar_witt_factorization(
            replace(problem, evidence=(graft, *problem.evidence[1:]))
        )
    assert context_error.value.code == "polar_witt_evidence_context_mismatch"


def test_polar_witt_compiler_rejects_finite_or_wrong_owned_evidence() -> None:
    problem = _polar_witt_problem()
    weak_face = make_filtered_polar_witt_evidence(
        claim=FilteredPolarWittClaim.FINITE_MAXIMAL_FACE_DECOMPOSITION,
        subject_id="weak.maximal_face",
        context=problem.context,
        authority=EvidenceAuthority.FINITE_EXPERIMENT,
        scope=FilteredPolarWittEvidenceScope.FINITE_WINDOW,
        evidence_sha256=problem.context.adapter_evidence_sha256,
    )
    with pytest.raises(FilteredObstructionError) as authority_error:
        compile_filtered_polar_witt_factorization(
            replace(problem, evidence=(weak_face, *problem.evidence[1:]))
        )
    assert authority_error.value.code == (
        "polar_witt_evidence_authority_insufficient"
    )

    wrong_centralizer = make_filtered_polar_witt_evidence(
        claim=FilteredPolarWittClaim.CENTRALIZER_FLOW_EXCLUDED,
        subject_id="wrong.centralizer",
        context=problem.context,
        authority=EvidenceAuthority.FILTERED_COMPILER,
        scope=FilteredPolarWittEvidenceScope.SCALAR_CENTRALIZER_BRANCH,
        evidence_sha256=problem.context.adapter_evidence_sha256,
    )
    with pytest.raises(FilteredObstructionError) as owner_error:
        compile_filtered_polar_witt_factorization(
            replace(problem, evidence=(*problem.evidence[:2], wrong_centralizer))
        )
    assert owner_error.value.code == (
        "polar_witt_centralizer_evidence_mismatch"
    )


def _polar_tensor_problem(
    *,
    name: str = "alien_split_tensor_factorization",
    category_id: str = "alien split tensor factorization category",
    filtration_id: str = "alien Rees filtration and degree dictionary",
    degree_multiplier: object = 2,
    face_scope: FilteredPolarTensorEvidenceScope = (
        FilteredPolarTensorEvidenceScope.ALL_FINITE_POSITIVE_FACES
    ),
    module_scope: FilteredPolarTensorEvidenceScope = (
        FilteredPolarTensorEvidenceScope.ALL_CRITICAL_MODULE_ORDERS
    ),
    terminal_scope: FilteredPolarTensorEvidenceScope = (
        FilteredPolarTensorEvidenceScope.ZERO_POSITIVE_FACE_TERMINAL
    ),
    face_authority: EvidenceAuthority = EvidenceAuthority.ADAPTER_EXACT,
    module_authority: EvidenceAuthority = EvidenceAuthority.FILTERED_COMPILER,
    terminal_authority: EvidenceAuthority = EvidenceAuthority.FILTERED_COMPILER,
    face_evidence_sha256: str = "3" * 64,
) -> FilteredPolarTensorFactorizationProblem:
    context = make_filtered_polar_tensor_context(
        category_id=category_id,
        filtration_id=filtration_id,
        model=FilteredPolarTensorModel.WITT_DENSITY_2_NEG3_NEG5,
        adapter_evidence_sha256="3" * 64,
    )
    evidence = (
        make_filtered_polar_tensor_evidence(
            claim=(
                FilteredPolarTensorClaim.FINITE_MAXIMAL_FACE_DECOMPOSITION
            ),
            subject_id=f"{name}.maximal_face",
            context=context,
            authority=face_authority,
            scope=face_scope,
            evidence_sha256=face_evidence_sha256,
        ),
        make_filtered_polar_tensor_evidence(
            claim=(
                FilteredPolarTensorClaim.CRITICAL_MODULE_INFINITE_SUPPORT
            ),
            subject_id=f"{name}.critical_module",
            context=context,
            authority=module_authority,
            scope=module_scope,
            evidence_sha256="4" * 64,
        ),
        make_filtered_polar_tensor_evidence(
            claim=FilteredPolarTensorClaim.CRITICAL_TERMINAL_EXCLUDED,
            subject_id=f"{name}.critical_terminal",
            context=context,
            authority=terminal_authority,
            scope=terminal_scope,
            evidence_sha256="5" * 64,
        ),
    )
    return FilteredPolarTensorFactorizationProblem(
        name=name,
        threshold=2,
        degree_multiplier=degree_multiplier,  # type: ignore[arg-type]
        context=context,
        evidence=evidence,
    )


def test_polar_tensor_problem_has_no_boolean_assertion_fields() -> None:
    annotations = get_type_hints(FilteredPolarTensorFactorizationProblem)
    assert bool not in annotations.values()


def test_polar_tensor_compiler_closes_finite_prefix_induction() -> None:
    certificate = compile_filtered_polar_tensor_factorization(
        _polar_tensor_problem()
    )
    assert certificate.tensor_action == (
        "rho(A)J=2*x*A*J'-3*x*A'*J-5*A*J"
    )
    assert certificate.maximum_resonant_start_exponents == 4
    assert certificate.infinite_support_has_nonresonant_seed
    assert certificate.newton_invariant == "h*e+d*nu"
    assert certificate.semidirect_transfer == "z/(1-exp(-z))"
    assert certificate.target_module_vanishes
    assert certificate.orbit_rate_formula == "2*d/(d-h)"
    assert certificate.positive_face_branch_strictly_supercritical
    assert certificate.finite_positive_prefix_induction_closed
    assert certificate.critical_terminal_factorization_excluded
    assert certificate.strict_subthreshold_factorization_excluded
    assert not certificate.adapter_completeness_inferred
    assert certificate.polar_tensor_certificate_sha256 == (
        "fae8ed2e458734d2012ca4f2dec4ba37817ffcf1dbd699621119abe4d1908e84"
    )
    assert len(certificate.evidence_receipt_sha256) == 3
    assert certificate.proof_contract_sha256 != (
        certificate.polar_tensor_certificate_sha256
    )


@pytest.mark.parametrize(
    ("changes", "error_code"),
    (
        (
            {"face_scope": FilteredPolarTensorEvidenceScope.FINITE_WINDOW},
            "polar_tensor_evidence_scope_mismatch",
        ),
        (
            {"module_scope": FilteredPolarTensorEvidenceScope.FINITE_WINDOW},
            "polar_tensor_evidence_scope_mismatch",
        ),
        (
            {"terminal_scope": FilteredPolarTensorEvidenceScope.FINITE_WINDOW},
            "polar_tensor_evidence_scope_mismatch",
        ),
        (
            {"face_authority": EvidenceAuthority.FINITE_EXPERIMENT},
            "polar_tensor_evidence_authority_insufficient",
        ),
        (
            {"face_evidence_sha256": "9" * 64},
            "polar_tensor_face_adapter_mismatch",
        ),
        (
            {"degree_multiplier": "3/2"},
            "insufficient_polar_tensor_orbit_rate",
        ),
    ),
)
def test_polar_tensor_compiler_rejects_missing_premises(
    changes: dict[str, object],
    error_code: str,
) -> None:
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_polar_tensor_factorization(
            _polar_tensor_problem(**changes)  # type: ignore[arg-type]
        )
    assert error.value.code == error_code


def test_polar_tensor_compiler_rejects_tamper_and_cross_context() -> None:
    problem = _polar_tensor_problem()
    tampered = replace(problem.evidence[0], subject_id="changed.subject")
    with pytest.raises(FilteredObstructionError) as tamper_error:
        compile_filtered_polar_tensor_factorization(
            replace(problem, evidence=(tampered, *problem.evidence[1:]))
        )
    assert tamper_error.value.code == "evidence_receipt_digest_mismatch"

    other = _polar_tensor_problem(
        name="alien_other_split_tensor",
        filtration_id="a different filtration dictionary",
    )
    with pytest.raises(FilteredObstructionError) as context_error:
        compile_filtered_polar_tensor_factorization(
            replace(
                problem,
                evidence=(other.evidence[0], *problem.evidence[1:]),
            )
        )
    assert context_error.value.code == "polar_tensor_evidence_context_mismatch"


def test_polar_tensor_compiler_rejects_duplicate_missing_and_unknown_model() -> None:
    problem = _polar_tensor_problem()
    with pytest.raises(FilteredObstructionError) as duplicate_error:
        compile_filtered_polar_tensor_factorization(
            replace(
                problem,
                evidence=(
                    problem.evidence[0],
                    problem.evidence[1],
                    problem.evidence[0],
                ),
            )
        )
    assert duplicate_error.value.code == "polar_tensor_evidence_claim_duplicate"

    with pytest.raises(FilteredObstructionError) as missing_error:
        compile_filtered_polar_tensor_factorization(
            replace(problem, evidence=problem.evidence[:2])
        )
    assert missing_error.value.code == (
        "polar_tensor_evidence_claim_set_incomplete"
    )

    unknown_context = replace(problem.context, model="invented")
    with pytest.raises(FilteredObstructionError) as model_error:
        compile_filtered_polar_tensor_factorization(
            replace(problem, context=unknown_context)
        )
    assert model_error.value.code == "polar_tensor_model_unknown"


def _tail_minimax_problem(
    *,
    name: str = "alien_polynomial_degree_tail",
    category_id: str = "QQ[x] coefficientwise polynomial degree tail",
    statistic_id: str = "limsup polynomial degree divided by row order",
    pure_bound: object = 2,
    positive_bound: object = "11/5",
    upper_bound: object = 2,
    pure_scope: FilteredTailEvidenceScope = (
        FilteredTailEvidenceScope.ALL_ORDER_FINITE_PREFIX_UNIFORM
    ),
    positive_scope: FilteredTailEvidenceScope = (
        FilteredTailEvidenceScope.ALL_ORDER_FINITE_PREFIX_UNIFORM
    ),
    upper_scope: FilteredTailEvidenceScope = (
        FilteredTailEvidenceScope.ADMISSIBLE_ALL_ORDER_CONSTRUCTION
    ),
    pure_authority: EvidenceAuthority = EvidenceAuthority.FILTERED_COMPILER,
    positive_authority: EvidenceAuthority = EvidenceAuthority.FILTERED_COMPILER,
    upper_authority: EvidenceAuthority = EvidenceAuthority.ADAPTER_EXACT,
) -> FilteredTailMinimaxCompositionProblem:
    context = make_filtered_tail_context(
        category_id=category_id,
        statistic_id=statistic_id,
        occurrence_order=(
            FilteredTailOccurrenceOrder.NAT_PARAMETER_POSITIVE_GRADE_LEX
        ),
        adapter_evidence_sha256="c" * 64,
    )
    evidence = (
        make_filtered_tail_evidence(
            claim=FilteredTailClaim.PURE_BRANCH_LOWER,
            subject_id=f"{name}.pure",
            context=context,
            bound=pure_bound,  # type: ignore[arg-type]
            authority=pure_authority,
            scope=pure_scope,
            evidence_sha256="9" * 64,
        ),
        make_filtered_tail_evidence(
            claim=FilteredTailClaim.LEAST_POSITIVE_BRANCH_LOWER,
            subject_id=f"{name}.least_positive",
            context=context,
            bound=positive_bound,  # type: ignore[arg-type]
            authority=positive_authority,
            scope=positive_scope,
            evidence_sha256="a" * 64,
        ),
        make_filtered_tail_evidence(
            claim=FilteredTailClaim.ADMISSIBLE_UPPER,
            subject_id=f"{name}.upper",
            context=context,
            bound=upper_bound,  # type: ignore[arg-type]
            authority=upper_authority,
            scope=upper_scope,
            evidence_sha256="b" * 64,
        ),
    )
    return FilteredTailMinimaxCompositionProblem(
        name=name,
        threshold=2,
        context=context,
        evidence=evidence,
    )


def test_tail_minimax_composition_closes_polynomial_degree_tail() -> None:
    certificate = compile_filtered_tail_minimax_composition(
        _tail_minimax_problem()
    )
    assert certificate.branch_partition == (
        "positive_support_empty",
        "least_positive_occurrence",
    )
    assert certificate.branch_partition_exhaustive
    assert certificate.unrestricted_lower_bound == "2"
    assert certificate.upper_construction_bound == "2"
    assert certificate.unrestricted_minimax_value == "2"
    assert certificate.all_lower_branches_all_order
    assert certificate.finite_prefix_uniform
    assert not certificate.adapter_completeness_inferred
    assert len(certificate.evidence_receipt_sha256) == 3
    assert certificate.proof_contract_sha256 != (
        certificate.tail_minimax_certificate_sha256
    )


def test_tail_minimax_problem_has_no_boolean_assertion_fields() -> None:
    annotations = get_type_hints(FilteredTailMinimaxCompositionProblem)
    assert bool not in annotations.values()


def test_tail_minimax_composition_transfers_to_valuation_support_tail() -> None:
    certificate = compile_filtered_tail_minimax_composition(
        _tail_minimax_problem(
            name="alien_valuation_support_tail",
            category_id="complete discretely valued support schedules",
            statistic_id="limsup support width divided by filtration time",
            pure_bound="5/2",
            positive_bound=3,
        )
    )
    assert certificate.unrestricted_minimax_value == "2"
    assert certificate.pure_branch_lower_bound == "5/2"
    assert certificate.least_positive_branch_lower_bound == "3"
    assert certificate.statistics_and_category_compatible


@pytest.mark.parametrize(
    ("changes", "error_code"),
    (
        (
            {"pure_scope": FilteredTailEvidenceScope.FINITE_WINDOW},
            "tail_evidence_scope_mismatch",
        ),
        (
            {"positive_scope": FilteredTailEvidenceScope.FINITE_WINDOW},
            "tail_evidence_scope_mismatch",
        ),
        (
            {"upper_scope": FilteredTailEvidenceScope.FINITE_WINDOW},
            "tail_evidence_scope_mismatch",
        ),
        (
            {"pure_authority": EvidenceAuthority.FINITE_EXPERIMENT},
            "tail_evidence_authority_insufficient",
        ),
        (
            {"pure_bound": "3/2"},
            "pure_tail_lower_bound_too_weak",
        ),
        (
            {"positive_bound": "3/2"},
            "least_positive_tail_lower_bound_too_weak",
        ),
        (
            {"upper_bound": "5/2"},
            "tail_upper_bound_does_not_match_threshold",
        ),
    ),
)
def test_tail_minimax_composition_rejects_incomplete_inputs(
    changes: dict[str, object],
    error_code: str,
) -> None:
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_tail_minimax_composition(
            _tail_minimax_problem(**changes)  # type: ignore[arg-type]
        )
    assert error.value.code == error_code


def test_tail_minimax_composition_rejects_tampered_receipt() -> None:
    problem = _tail_minimax_problem()
    forged = replace(problem.evidence[0], subject_id="changed.subject")
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_tail_minimax_composition(
            replace(problem, evidence=(forged, *problem.evidence[1:]))
        )
    assert error.value.code == "evidence_receipt_digest_mismatch"


def test_tail_minimax_composition_rejects_cross_context_graft() -> None:
    problem = _tail_minimax_problem()
    other = _tail_minimax_problem(
        name="alien_other_statistic",
        statistic_id="a different normalized statistic",
    )
    grafted = (other.evidence[0], *problem.evidence[1:])
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_tail_minimax_composition(
            replace(problem, evidence=grafted)
        )
    assert error.value.code == "tail_evidence_context_mismatch"


def test_tail_minimax_composition_rejects_duplicate_and_missing_claims() -> None:
    problem = _tail_minimax_problem()
    with pytest.raises(FilteredObstructionError) as duplicate_error:
        compile_filtered_tail_minimax_composition(
            replace(
                problem,
                evidence=(
                    problem.evidence[0],
                    problem.evidence[1],
                    problem.evidence[0],
                ),
            )
        )
    assert duplicate_error.value.code == "tail_evidence_claim_duplicate"
    with pytest.raises(FilteredObstructionError) as missing_error:
        compile_filtered_tail_minimax_composition(
            replace(problem, evidence=problem.evidence[:2])
        )
    assert missing_error.value.code == "tail_evidence_claim_set_incomplete"


def test_tail_minimax_composition_rejects_unknown_authority() -> None:
    problem = _tail_minimax_problem()
    unknown = replace(problem.evidence[0], authority="invented")
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_tail_minimax_composition(
            replace(problem, evidence=(unknown, *problem.evidence[1:]))
        )
    assert error.value.code == "evidence_authority_unknown"


def test_quadratic_differential_compiler_detects_incompatible_rows() -> None:
    certificate = compile_filtered_quadratic_differential_obstruction(
        FilteredQuadraticDifferentialProblem(
            name="alien_quadratic_connection",
            variable="x",
            rational_row=("1", "0", "0"),
            radical_row=("0", "1", "x"),
            adapter_certificate_sha256="f" * 64,
        )
    )
    assert certificate.determinant_nonzero
    assert certificate.rational_candidate_unique
    assert certificate.derivative_compatibility_nonzero
    assert certificate.rational_solution_excluded
    assert certificate.polynomial_solution_excluded
    assert certificate.compatibility_numerator_degree == 0
    assert not certificate.adapter_completeness_inferred


def test_quadratic_differential_compiler_excludes_rational_nonpolynomial() -> None:
    certificate = compile_filtered_quadratic_differential_obstruction(
        FilteredQuadraticDifferentialProblem(
            name="alien_unique_rational_connection",
            variable="x",
            rational_row=("1", "0", "-1/x**2"),
            radical_row=("0", "1", "1/x"),
            adapter_certificate_sha256="1" * 64,
        )
    )
    assert not certificate.derivative_compatibility_nonzero
    assert not certificate.rational_solution_excluded
    assert certificate.candidate_rational_not_polynomial
    assert certificate.polynomial_solution_excluded


@pytest.mark.parametrize(
    ("rational_row", "radical_row", "error_code"),
    (
        (
            ("1", "0", "0"),
            ("2", "0", "0"),
            "singular_quadratic_differential_rows",
        ),
        (
            ("1", "0", "0"),
            ("0", "1", "1"),
            "polynomial_differential_solution_not_excluded",
        ),
    ),
)
def test_quadratic_differential_compiler_rejects_no_obstruction(
    rational_row: tuple[str, str, str],
    radical_row: tuple[str, str, str],
    error_code: str,
) -> None:
    with pytest.raises(FilteredObstructionError) as error:
        compile_filtered_quadratic_differential_obstruction(
            FilteredQuadraticDifferentialProblem(
                name="bad_alien_quadratic_connection",
                variable="x",
                rational_row=rational_row,
                radical_row=radical_row,
                adapter_certificate_sha256="2" * 64,
            )
        )
    assert error.value.code == error_code
