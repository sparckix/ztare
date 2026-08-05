#!/usr/bin/env python3
"""Universal contact-lowering symbol for the Jacobian target-lift algebra.

This adapter computes the exact ideal generated on the normalization of
``C=0`` by the filtration-order ``-1`` symbols of every lift-compatible
contact-zero Hamiltonian.  It then replays multiplication by the primitive
ideal generator as a cross-grade cokernel with the substrate-neutral
Filtered Obstruction Compiler.

The result is target-side.  It does not assert that the five residual target
classes survive the paired source image or the parameter-ordered Magnus
recursion.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
SRC = HERE.parents[2] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredBasisVector,
    FilteredReachabilityProblem,
    FilteredSymbolCokernelProblem,
    FilteredSymbolMap,
    compile_filtered_reachability,
    compile_filtered_symbol_cokernel,
)


def _poisson(
    left: sp.Expr,
    right: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> sp.Expr:
    return sp.expand(
        sp.diff(left, p) * sp.diff(right, q)
        - sp.diff(left, q) * sp.diff(right, p)
    )


def _r_coordinates(
    polynomial: sp.Expr,
    r: sp.Symbol,
    *,
    prefix: str,
    maximum_degree: int,
) -> dict[str, str]:
    value = sp.Poly(sp.expand(polynomial), r)
    if value.degree() > maximum_degree:
        raise AssertionError("symbol leaves the declared codomain window")
    coordinates = {
        f"{prefix}{degree}": str(value.coeff_monomial(r**degree))
        for degree in range(maximum_degree + 1)
        if value.coeff_monomial(r**degree) != 0
    }
    replay = sum(
        sp.Rational(coordinates.get(f"{prefix}{degree}", "0")) * r**degree
        for degree in range(maximum_degree + 1)
    )
    assert sp.expand(replay - polynomial) == 0
    return coordinates


def _compiler_window(
    multiplier_degree: int,
    generator: sp.Expr,
    r: sp.Symbol,
    *,
    problem_prefix: str,
    domain_prefix: str,
    codomain_prefix: str,
    domain_grade: int,
    codomain_grade: int,
    map_name: str,
    reverse_basis: bool = False,
) -> dict[str, object]:
    codomain_degree = multiplier_degree + sp.Poly(generator, r).degree()
    domain_degrees = list(range(multiplier_degree + 1))
    codomain_degrees = list(range(codomain_degree + 1))
    if reverse_basis:
        domain_degrees.reverse()
        codomain_degrees.reverse()
    domain_basis = tuple(
        FilteredBasisVector(f"{domain_prefix}{degree}", domain_grade)
        for degree in domain_degrees
    )
    codomain_basis = tuple(
        FilteredBasisVector(f"{codomain_prefix}{degree}", codomain_grade)
        for degree in codomain_degrees
    )
    columns = {
        f"{domain_prefix}{degree}": _r_coordinates(
            sp.expand(generator * r**degree),
            r,
            prefix=codomain_prefix,
            maximum_degree=codomain_degree,
        )
        for degree in range(multiplier_degree + 1)
    }
    problem = FilteredSymbolCokernelProblem(
        name=f"{problem_prefix}_{multiplier_degree}",
        domain_basis=domain_basis,
        domain_relations=(),
        codomain_basis=codomain_basis,
        codomain_relations=(),
        maps=(
            FilteredSymbolMap(
                map_name,
                codomain_grade - domain_grade,
                columns,
            ),
        ),
        distinguished={f"{codomain_prefix}0": 1},
    )
    return compile_filtered_symbol_cokernel(problem).to_dict()


def _polar_injectivity_certificate(
    polar_offset: int,
    multiplier_degree: int,
    r: sp.Symbol,
    contact_unit_axis: sp.Expr,
) -> dict[str, object]:
    if polar_offset < 1:
        raise ValueError("polar_offset must be positive")
    minimum_radial_degree = polar_offset + 3
    domain_degrees = list(
        range(
            minimum_radial_degree,
            minimum_radial_degree + multiplier_degree + 1,
        )
    )
    maximum_codomain_degree = domain_degrees[-1] + 1
    domain_basis = tuple(
        FilteredBasisVector(f"polar{polar_offset}_r{degree}", polar_offset)
        for degree in domain_degrees
    )
    codomain_basis = tuple(
        FilteredBasisVector(f"negative_layer_r{degree}", 0)
        for degree in range(maximum_codomain_degree + 1)
    )
    columns = {}
    for degree in domain_degrees:
        g = r**degree
        leading_layer = sp.expand(
            -polar_offset * sp.diff(contact_unit_axis, r) * g
            - 2 * contact_unit_axis * sp.diff(g, r)
        )
        columns[f"polar{polar_offset}_r{degree}"] = _r_coordinates(
            leading_layer,
            r,
            prefix="negative_layer_r",
            maximum_degree=maximum_codomain_degree,
        )
    problem = FilteredSymbolCokernelProblem(
        name=(
            f"jacobian_polar_offset_{polar_offset}_"
            f"degree_{multiplier_degree}"
        ),
        domain_basis=domain_basis,
        domain_relations=(),
        codomain_basis=codomain_basis,
        codomain_relations=(),
        maps=(
            FilteredSymbolMap(
                f"polar_leading_layer_{polar_offset}",
                -polar_offset,
                columns,
            ),
        ),
        distinguished={"negative_layer_r0": 1},
    )
    return compile_filtered_symbol_cokernel(problem).to_dict()


def run(maximum_multiplier_degree: int = 8) -> dict[str, object]:
    if maximum_multiplier_degree < 0:
        raise ValueError("maximum_multiplier_degree must be nonnegative")
    p, q, r = sp.symbols("P Q r")
    contact = 4 * p**3 - p**2 - 18 * p * q + 27 * q**2 + 4 * q
    p_normalized = r - sp.Rational(3, 4) * r**2
    q_normalized = sp.Rational(1, 4) * r**2 * (1 - r)
    substitution = {p: p_normalized, q: q_normalized}
    assert sp.expand(contact.subs(substitution)) == 0

    characteristic = (
        sp.diff(contact, q).subs(substitution),
        -sp.diff(contact, p).subs(substitution),
    )
    tangent = (sp.diff(p_normalized, r), sp.diff(q_normalized, r))
    ramification_square = (3 * r - 2) ** 2
    assert all(
        sp.expand(characteristic[index] - ramification_square * tangent[index])
        == 0
        for index in range(2)
    )

    lift_generators = {
        "P^3": p**3,
        "P*Q": p * q,
        "Q^2": q**2,
    }
    restrictions = {
        name: sp.factor(value.subs(substitution))
        for name, value in lift_generators.items()
    }
    leak_symbols = {
        name: sp.factor(_poisson(value, contact, p, q).subs(substitution))
        for name, value in lift_generators.items()
    }
    for name, restriction in restrictions.items():
        expected = sp.expand(
            ramification_square * sp.diff(restriction, r)
        )
        assert sp.expand(leak_symbols[name] - expected) == 0

    first, second, third = (
        leak_symbols["P^3"],
        leak_symbols["P*Q"],
        leak_symbols["Q^2"],
    )
    coefficient_first, coefficient_second, gcd_first_two = sp.gcdex(
        first,
        second,
        r,
    )
    coefficient_gcd, coefficient_third, gcd_all = sp.gcdex(
        gcd_first_two,
        third,
        r,
    )
    assert sp.expand(
        coefficient_first * first
        + coefficient_second * second
        - gcd_first_two
    ) == 0
    assert sp.expand(
        coefficient_gcd * gcd_first_two
        + coefficient_third * third
        - gcd_all
    ) == 0

    leak_generator = sp.expand(r**2 * (3 * r - 2) ** 3)
    unit_scale = sp.cancel(leak_generator / gcd_all)
    bezout = {
        "P^3": sp.factor(unit_scale * coefficient_gcd * coefficient_first),
        "P*Q": sp.factor(
            unit_scale * coefficient_gcd * coefficient_second
        ),
        "Q^2": sp.factor(unit_scale * coefficient_third),
    }
    assert sp.expand(
        sum(bezout[name] * leak_symbols[name] for name in lift_generators)
        - leak_generator
    ) == 0

    # Every liftable H is c+P^3*A+P*Q*B+Q^2*D.  Its restriction minus c
    # is divisible by r^3, while every derivative through (P(r),Q(r)) is
    # divisible by (3r-2).  Therefore every leak has the universal factor
    # below; the Bezout identity proves that the inclusion is equality.
    assert all(
        sp.rem(leak_symbols[name], leak_generator, domain=sp.QQ) == 0
        for name in lift_generators
    )

    source_pole_generator = sp.expand(r**2 * (3 * r - 2))
    ramification_multiplier = sp.expand((3 * r - 2) ** 2)
    independent_source_image_generator = sp.expand(
        r**2 * ramification_multiplier
    )
    assert sp.expand(
        source_pole_generator * ramification_multiplier - leak_generator
    ) == 0

    windows = []
    source_windows = []
    independent_source_windows = []
    for degree in range(maximum_multiplier_degree + 1):
        certificate = _compiler_window(
            degree,
            leak_generator,
            r,
            problem_prefix="jacobian_universal_leak_degree",
            domain_prefix="contact1_r",
            codomain_prefix="contact0_r",
            domain_grade=1,
            codomain_grade=0,
            map_name="universal_contact_lowering_symbol",
        )
        reversed_certificate = _compiler_window(
            degree,
            leak_generator,
            r,
            problem_prefix="jacobian_universal_leak_degree",
            domain_prefix="contact1_r",
            codomain_prefix="contact0_r",
            domain_grade=1,
            codomain_grade=0,
            map_name="universal_contact_lowering_symbol",
            reverse_basis=True,
        )
        assert certificate["cokernel_dimension"] == 5
        assert certificate["symbol_image_rank"] == degree + 1
        assert certificate["distinguished_survives"] is True
        assert certificate["cokernel_dimension"] == reversed_certificate[
            "cokernel_dimension"
        ]
        assert certificate["symbol_image_rank"] == reversed_certificate[
            "symbol_image_rank"
        ]
        windows.append({
            "maximum_multiplier_degree": degree,
            "certificate": certificate,
            "basis_permutation_control": True,
        })

        source_certificate = _compiler_window(
            degree,
            source_pole_generator,
            r,
            problem_prefix="jacobian_universal_source_pole_degree",
            domain_prefix="lift_r",
            codomain_prefix="source_pole_r",
            domain_grade=1,
            codomain_grade=0,
            map_name="universal_source_pole_symbol",
        )
        assert source_certificate["cokernel_dimension"] == 3
        assert source_certificate["symbol_image_rank"] == degree + 1
        source_windows.append({
            "maximum_multiplier_degree": degree,
            "certificate": source_certificate,
        })

        independent_source_certificate = _compiler_window(
            degree,
            independent_source_image_generator,
            r,
            problem_prefix="jacobian_independent_source_contact_degree",
            domain_prefix="source_diagonal_r",
            codomain_prefix="contact0_r",
            domain_grade=1,
            codomain_grade=0,
            map_name="independent_weighted_volume_source_symbol",
        )
        assert independent_source_certificate["cokernel_dimension"] == 4
        assert independent_source_certificate["symbol_image_rank"] == degree + 1
        independent_source_windows.append({
            "maximum_multiplier_degree": degree,
            "certificate": independent_source_certificate,
        })

    source_defect_basis = tuple(
        FilteredBasisVector(f"source_defect_r{degree}", 0)
        for degree in range(3)
    )
    target_defect_basis = tuple(
        FilteredBasisVector(f"target_defect_r{degree}", 0)
        for degree in range(5)
    )
    ramification_columns = {
        f"source_defect_r{degree}": _r_coordinates(
            sp.expand(ramification_multiplier * r**degree),
            r,
            prefix="target_defect_r",
            maximum_degree=4,
        )
        for degree in range(3)
    }
    ramification_problem = FilteredSymbolCokernelProblem(
        name="jacobian_paired_ramification_defect",
        domain_basis=source_defect_basis,
        domain_relations=(),
        codomain_basis=target_defect_basis,
        codomain_relations=(),
        maps=(
            FilteredSymbolMap(
                "multiply_by_contact_unit_axis_value",
                0,
                ramification_columns,
            ),
        ),
        distinguished={"target_defect_r0": 1},
    )
    ramification_certificate = compile_filtered_symbol_cokernel(
        ramification_problem
    )
    assert ramification_certificate.symbol_image_rank == 3
    assert ramification_certificate.cokernel_dimension == 2
    assert ramification_certificate.distinguished_survives

    # The local ramification quotient has coordinates given by value and
    # first derivative at r=2/3.  Both normalization coordinates are
    # stationary there, so every polynomial multiplier M(P,Q) has zero
    # first derivative.  The admissible control Q^2*C has nonzero value and
    # therefore spans exactly the value coordinate.
    ramification_parameter = sp.Rational(2, 3)
    assert sp.diff(p_normalized, r).subs(r, ramification_parameter) == 0
    assert sp.diff(q_normalized, r).subs(r, ramification_parameter) == 0
    q_squared_value = sp.factor(
        q_normalized.subs(r, ramification_parameter) ** 2
    )
    assert q_squared_value == sp.Rational(1, 729)
    multiplier_control_problem = FilteredSymbolCokernelProblem(
        name="jacobian_positive_contact_ramification_jet_control",
        domain_basis=(FilteredBasisVector("Q^2*C_control", 1),),
        domain_relations=(),
        codomain_basis=(
            FilteredBasisVector("ramification_value", 0),
            FilteredBasisVector("ramification_first_jet", 0),
        ),
        codomain_relations=(),
        maps=(
            FilteredSymbolMap(
                "positive_contact_multiplier_restriction",
                -1,
                {
                    "Q^2*C_control": {
                        "ramification_value": str(q_squared_value),
                    },
                },
            ),
        ),
        distinguished={"ramification_first_jet": 1},
    )
    multiplier_control_certificate = compile_filtered_symbol_cokernel(
        multiplier_control_problem
    )
    assert multiplier_control_certificate.symbol_image_rank == 1
    assert multiplier_control_certificate.cokernel_dimension == 1
    assert multiplier_control_certificate.distinguished_survives
    multiplier_reachability_certificate = compile_filtered_reachability(
        FilteredReachabilityProblem(
            name="jacobian_polynomial_multiplier_ramification_reachability",
            symbol_problem=multiplier_control_problem,
            forcing_columns={
                "polynomial_multiplier_family": {
                    "ramification_value": 1,
                },
            },
        )
    )
    assert multiplier_reachability_certificate.cokernel_dimension == 1
    assert (
        multiplier_reachability_certificate.reachable_cokernel_dimension
        == 0
    )
    assert (
        multiplier_reachability_certificate.unreachable_cokernel_dimension
        == 1
    )

    local_parameter = sp.Symbol("tau")
    local_leak_orders = {}
    for name, leak in leak_symbols.items():
        local_leak = sp.Poly(
            sp.expand(
                leak.subs(r, (local_parameter + 2) / 3)
            ),
            local_parameter,
        )
        order = min(monomial[0] for monomial in local_leak.monoms())
        assert order >= 3
        local_leak_orders[name] = order

    covariant_generator_pairs = []
    for left_name, left in lift_generators.items():
        for right_name, right in lift_generators.items():
            bracket_restriction = sp.factor(
                _poisson(left, right, p, q).subs(substitution)
            )
            first_jet = sp.factor(
                sp.diff(bracket_restriction, r).subs(
                    r, ramification_parameter
                )
            )
            assert first_jet == 0
            covariant_generator_pairs.append({
                "left": left_name,
                "right": right_name,
                "value": str(
                    sp.factor(
                        bracket_restriction.subs(
                            r, ramification_parameter
                        )
                    )
                ),
                "first_jet": "0",
            })

    crt_r, crt_ramification, crt_gcd = sp.gcdex(
        r**2,
        ramification_multiplier,
        r,
    )
    assert sp.expand(
        crt_r * r**2
        + crt_ramification * ramification_multiplier
        - crt_gcd
    ) == 0
    assert crt_gcd == 1

    source_cost_rows = []
    for source_hamiltonian_radial_degree in range(3, 13):
        source_component_degree = (
            2 * source_hamiltonian_radial_degree - 3
        )
        output_radial_degree = source_hamiltonian_radial_degree + 1
        assert source_component_degree == 2 * output_radial_degree - 5
        source_cost_rows.append({
            "source_hamiltonian": (
                f"(u*z)^{source_hamiltonian_radial_degree}"
            ),
            "source_component_degree": source_component_degree,
            "contact_scalar_radial_degree": output_radial_degree,
            "sharp_degree_law": "source_degree=2*radial_degree-5",
        })

    polynomial_degree, polar_offset = sp.symbols(
        "n d",
        integer=True,
        nonnegative=True,
    )
    leading_coefficient = sp.factor(
        -polar_offset * (-sp.Rational(9, 8))
        - 2 * (-sp.Rational(9, 16)) * polynomial_degree
    )
    assert sp.factor(
        leading_coefficient
        - sp.Rational(9, 8) * (polynomial_degree + polar_offset)
    ) == 0
    polar_compiler_rows = []
    for checked_offset in range(1, 6):
        for checked_degree in range(0, 7):
            certificate = _polar_injectivity_certificate(
                checked_offset,
                checked_degree,
                r,
                -ramification_multiplier / 16,
            )
            assert certificate["symbol_image_rank"] == checked_degree + 1
            polar_compiler_rows.append({
                "polar_offset": checked_offset,
                "additional_multiplier_degree": checked_degree,
                "domain_dimension": checked_degree + 1,
                "symbol_image_rank": certificate["symbol_image_rank"],
                "constraint_matrix_sha256": certificate[
                    "constraint_matrix_sha256"
                ],
            })

    return {
        "schema": "axiompack.jacobian_universal_contact_leak_symbol.v2",
        "normalization": {
            "P": str(p_normalized),
            "Q": str(q_normalized),
            "C_vanishes": True,
            "X_C_equals_ramification_square_times_tangent": True,
            "ramification_square": str(ramification_square),
        },
        "target_lift_algebra": "QQ + (P^3,P*Q,Q^2)",
        "generator_restrictions": {
            name: str(value) for name, value in restrictions.items()
        },
        "generator_leak_symbols": {
            name: str(value) for name, value in leak_symbols.items()
        },
        "universal_leak_ideal_generator": str(sp.factor(leak_generator)),
        "bezout_coefficients": {
            name: str(value) for name, value in bezout.items()
        },
        "bezout_replay": True,
        "contact_grade_m_symbol": (
            "[C^m*f] maps to m*[C^(m-1)*{H,C}|_(C=0)*f]"
        ),
        "characteristic_zero_contact_factor_nonzero": True,
        "universal_target_cokernel": "QQ[r]/(r^2*(3*r-2)^3)",
        "universal_target_cokernel_dimension": 5,
        "compiler_windows": windows,
        "universal_source_pole_ideal_generator": str(
            sp.factor(source_pole_generator)
        ),
        "universal_source_pole_cokernel": (
            "QQ[r]/(r^2*(3*r-2))"
        ),
        "universal_source_pole_cokernel_dimension": 3,
        "source_pole_compiler_windows": source_windows,
        "paired_ramification_exact_sequence": {
            "sequence": (
                "0 -> QQ[r]/(r^2*(3*r-2)) --*(3*r-2)^2--> "
                "QQ[r]/(r^2*(3*r-2)^3) -> "
                "QQ[r]/((3*r-2)^2) -> 0"
            ),
            "contact_unit_axis_factor": str(ramification_multiplier),
            "certificate": ramification_certificate.to_dict(),
            "residual_dimension": 2,
        },
        "ramification_local_action": {
            "local_parameter": "tau=3*r-2",
            "quotient": "QQ[tau]/(tau^2)",
            "contact_zero_generator_leak_orders": local_leak_orders,
            "contact_zero_backbone_action_on_quotient": "zero",
            "reason": (
                "every lift-compatible contact-zero leak is divisible by "
                "tau^3, while the complete polynomial source image is "
                "divisible by tau^2"
            ),
        },
        "positive_contact_multiplier_gate": {
            "chain_rule": (
                "d_r M(P(r),Q(r)) vanishes at r=2/3 for every "
                "polynomial M because P'(2/3)=Q'(2/3)=0"
            ),
            "polynomial_multiplier_image": "ramification value line",
            "Q^2_value_at_ramification": str(q_squared_value),
            "Q^2*C_spans_value_line": True,
            "first_jet_line_survives": True,
            "first_jet_line_excited_by_polynomial_multiplier": False,
            "certificate": multiplier_control_certificate.to_dict(),
            "reachability_certificate": (
                multiplier_reachability_certificate.to_dict()
            ),
        },
        "covariant_polynomial_closure": {
            "operator": "nabla_H(M)={H,M}|_(C=0)",
            "generator_pair_rows": covariant_generator_pairs,
            "all_polynomial_first_jets_vanish": True,
            "target_poisson_and_magnus_closure": True,
            "source_bracket_closure": True,
            "conclusion": (
                "coefficientwise-polynomial covariant transport cannot "
                "excite the surviving ramification first-jet line"
            ),
        },
        "independent_weighted_volume_source_image": {
            "density": "z^2*du^dz",
            "hamiltonian_field": (
                "Y_u=z^(-2)*d_z G, Y_z=-z^(-2)*d_u G"
            ),
            "blow_up_coordinate": "r=u*z",
            "monomial_formulas": {
                "G": "u^a*z^b",
                "Y_r": "(b-a)*r^a*z^(b-a-2)",
                "Y_z": "-a*r^(a-1)*z^(b-a-1)",
            },
            "contact_zero_row_requires": "a=b>=3",
            "image_ideal_generator": str(
                sp.factor(independent_source_image_generator)
            ),
            "combined_source_target_image_ideal": str(
                sp.factor(independent_source_image_generator)
            ),
            "combined_cokernel": "QQ[r]/(r^2*(3*r-2)^2)",
            "combined_cokernel_dimension": 4,
            "crt_decomposition": (
                "QQ[r]/(r^2) direct_sum QQ[r]/((3*r-2)^2)"
            ),
            "crt_bezout": {
                "coefficient_of_r_squared": str(sp.factor(crt_r)),
                "coefficient_of_ramification_squared": str(
                    sp.factor(crt_ramification)
                ),
            },
            "ramification_summand_dimension": 2,
            "source_degree_law": "2*w-5 for scalar radial degree w>=4",
            "source_degree_rows": source_cost_rows,
            "compiler_windows": independent_source_windows,
        },
        "polar_source_triangular_gate": {
            "polar_hamiltonian": "G=z^(-d)*g(r), d>=1",
            "source_polynomiality_requires": "g divisible by r^(d+3)",
            "leading_negative_layer_operator": (
                "T_d(g)=-d*U'(r)*g-2*U(r)*g'"
            ),
            "contact_unit_axis": "U=-(3*r-2)^2/16",
            "top_coefficient_on_degree_n": str(leading_coefficient),
            "polynomial_kernel": "zero for d>=1 in characteristic zero",
            "coefficientwise_finite_consequence": (
                "a homogeneous source-target gauge difference has no "
                "positive polar offset: choose the largest d and apply "
                "injectivity to its uncancellable leading negative layer"
            ),
            "compiler_rank_rows": polar_compiler_rows,
        },
        "claim_boundary": (
            "The full lift-compatible contact-zero target algebra has an "
            "exact common filtration-order-minus-one image ideal on every "
            "positive contact grade, with a five-dimensional target "
            "cokernel. Its forced source-pole ideal accounts for three "
            "classes, leaving a two-dimensional ramification quotient. "
            "Allowing every independent polynomial weighted-volume source "
            "symbol gives the larger image r^2*(3*r-2)^2 but leaves that "
            "same two-dimensional ramification summand. Off-diagonal polar "
            "source terms cannot remove it inside a homogeneous gauge "
            "difference because their leading negative-layer operator is "
            "polynomially injective. Removing a radial row of degree w "
            "through the regular diagonal source image has sharp component "
            "degree 2*w-5. Locally at r=2/3 the arbitrary contact-zero "
            "backbone acts trivially on the two ramification jets. Every "
            "polynomial positive-contact multiplier has zero first jet, "
            "and the admissible Q^2*C direction spans its value line. "
            "Consequently the surviving first-jet coordinate is dormant. "
            "Polynomial Poisson, source-bracket, and Magnus closure keep it "
            "dormant at every parameter order. The ramification cokernel is "
            "therefore structurally nonzero but unreachable by this family "
            "category, so it is not a tail obstruction."
        ),
        "next_residual": (
            "The ramification route is closed as unreachable. Compile the "
            "leading-amplitude Q^2*C source self-cascade modulo an arbitrary "
            "coefficientwise-polynomial contact-zero backbone. Prove that "
            "the terminal response survives every such backbone, or build "
            "a backbone whose coupled higher-contact schedule cancels it "
            "without an equal-or-higher logarithmic rate."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
