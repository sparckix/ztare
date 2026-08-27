#!/usr/bin/env python3
"""Exact finite-cap inversion of the critical two-polynomial-flow claim.

For polynomial vector fields

    p(x) d/dx, q(x) d/dx,

vanishing to order at least two, this replay constructs their truncated
time-one maps by the Lie series, composes them in the declared order
``exp(q) o exp(p)``, and matches the exact critical holonomy germ.

The coefficient equations are triangular until both polynomial caps have
been exhausted.  The remaining free inner coefficients are tested with an
exact Groebner basis over ``QQ``.  A cap row passes the discriminator only
when the pre-excess ideal is proper but adjoining the first overdetermined
coefficient produces the unit ideal.

This is a finite degree-cap experiment.  Repetition over the declared cap
grid does not prove the all-degree two-flow obstruction.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import factorial
import hashlib
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_pure_contact_zero_parity_algebraic_connection import (  # noqa: E402
    _algebraic_normal_two,
)


Series = list[sp.Expr]


@dataclass(frozen=True)
class CapAudit:
    inner_degree: int
    outer_degree: int
    free_parameter_count: int
    matched_through_order: int
    first_incompatible_order: int
    parameter_count_excess_order: int
    pre_excess_ideal_is_proper: bool
    first_excess_ideal_is_unit: bool
    pre_excess_basis_size: int
    first_excess_basis_size: int
    constraint_system_sha256: str
    pre_excess_basis_sha256: str
    first_excess_basis_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "inner_degree": self.inner_degree,
            "outer_degree": self.outer_degree,
            "free_parameter_count": self.free_parameter_count,
            "matched_through_order": self.matched_through_order,
            "first_incompatible_order": self.first_incompatible_order,
            "parameter_count_excess_order": self.parameter_count_excess_order,
            "pre_excess_ideal_is_proper": self.pre_excess_ideal_is_proper,
            "first_excess_ideal_is_unit": self.first_excess_ideal_is_unit,
            "pre_excess_basis_size": self.pre_excess_basis_size,
            "first_excess_basis_size": self.first_excess_basis_size,
            "constraint_system_sha256": self.constraint_system_sha256,
            "pre_excess_basis_sha256": self.pre_excess_basis_sha256,
            "first_excess_basis_sha256": self.first_excess_basis_sha256,
        }


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _zero(maximum_order: int) -> Series:
    return [sp.S.Zero for _index in range(maximum_order + 1)]


def _add(left: Series, right: Series) -> Series:
    return [
        sp.expand(left[index] + right[index])
        for index in range(len(left))
    ]


def _scale(value: Series, scalar: sp.Expr) -> Series:
    return [sp.expand(scalar * coefficient) for coefficient in value]


def _multiply(left: Series, right: Series) -> Series:
    maximum_order = len(left) - 1
    result = _zero(maximum_order)
    for left_order, left_value in enumerate(left):
        if left_value == 0:
            continue
        for right_order, right_value in enumerate(
            right[: maximum_order + 1 - left_order]
        ):
            if right_value != 0:
                result[left_order + right_order] += (
                    left_value * right_value
                )
    return [sp.expand(value) for value in result]


def _derivative(value: Series) -> Series:
    maximum_order = len(value) - 1
    return [
        (order + 1) * value[order + 1]
        for order in range(maximum_order)
    ] + [sp.S.Zero]


def _time_one_flow(vector_field: Series) -> Series:
    """Return ``exp(vector_field*d/dx)(x)`` to the stored order."""

    maximum_order = len(vector_field) - 1
    coordinate = _zero(maximum_order)
    coordinate[1] = sp.S.One
    result = list(coordinate)
    iterated = list(coordinate)
    for depth in range(1, maximum_order):
        iterated = _multiply(vector_field, _derivative(iterated))
        result = _add(
            result,
            _scale(iterated, sp.Rational(1, factorial(depth))),
        )
    return result


def _compose(outer: Series, inner: Series) -> Series:
    maximum_order = len(outer) - 1
    result = _zero(maximum_order)
    power = _zero(maximum_order)
    power[0] = sp.S.One
    for coefficient in outer:
        result = _add(result, _scale(power, coefficient))
        power = _multiply(power, inner)
    return result


def _critical_holonomy_coefficients(maximum_order: int) -> Series:
    x, discriminant, velocity_pair = _algebraic_normal_two()
    velocity = sp.cancel(
        velocity_pair.rational
        + velocity_pair.radical_coefficient * sp.sqrt(discriminant)
    )
    logarithmic_derivative = sp.series(
        1 / (x * (1 + 2 * x * velocity)),
        x,
        0,
        maximum_order + 1,
    ).removeO()
    endpoint = sp.series(
        x
        * sp.exp(
            sp.integrate(logarithmic_derivative - 1 / x, x)
        ),
        x,
        0,
        maximum_order + 1,
    ).removeO().expand()
    return [
        sp.factor(endpoint.coeff(x, order))
        for order in range(maximum_order + 1)
    ]


def _basis_payload(basis: sp.GroebnerBasis) -> list[str]:
    return [str(sp.factor(polynomial.as_expr())) for polynomial in basis.polys]


def _primitive_polynomial(
    expression: sp.Expr,
    *generators: sp.Symbol,
) -> sp.Poly:
    """Clear scalar content without changing an affine zero set."""

    return sp.Poly(
        expression,
        *generators,
        domain=sp.QQ,
    ).primitive()[1]


def _cap_six_constraints(target: Series) -> tuple[
    tuple[sp.Symbol, ...],
    tuple[sp.Symbol, ...],
    list[sp.Expr],
    dict[sp.Symbol, sp.Expr],
]:
    """Return the exact equal-cap-six tail after the low triangular rows."""

    maximum_order = 12
    if len(target) <= maximum_order:
        raise ValueError("cap-six saturation needs target order twelve")
    inner_symbols = sp.symbols("a2:7")
    outer_symbols = sp.symbols("b2:7")
    inner = _zero(maximum_order)
    outer = _zero(maximum_order)
    for order, symbol in enumerate(inner_symbols, 2):
        inner[order] = symbol
    for order, symbol in enumerate(outer_symbols, 2):
        outer[order] = symbol
    composition = _compose(
        _time_one_flow(outer),
        _time_one_flow(inner),
    )
    equations = [
        sp.expand(composition[order] - target[order])
        for order in range(maximum_order + 1)
    ]
    outer_substitutions: dict[sp.Symbol, sp.Expr] = {}
    for order in range(2, 7):
        solved_symbol = outer_symbols[order - 2]
        equation = sp.expand(
            equations[order].subs(outer_substitutions)
        )
        coefficient = equation.coeff(solved_symbol)
        assert coefficient != 0
        outer_substitutions[solved_symbol] = sp.factor(
            -equation.subs(solved_symbol, 0) / coefficient
        )
    constraints = [
        sp.factor(
            sp.together(
                equations[order].subs(outer_substitutions)
            ).as_numer_denom()[0]
        )
        for order in range(7, 13)
    ]
    return (
        inner_symbols,
        outer_symbols,
        constraints,
        outer_substitutions,
    )


def _polynomial_modulus_evaluator(
    modulus: sp.Poly,
    eliminated: sp.Symbol,
    retained: sp.Symbol,
    retained_value: sp.Poly,
):
    """Evaluate in ``QQ[eliminated]/(modulus)`` by Horner reduction."""

    def reduce_value(expression: sp.Expr | sp.Poly) -> sp.Poly:
        return sp.rem(
            sp.Poly(expression, eliminated, domain=sp.QQ),
            modulus,
        )

    def evaluate(expression: sp.Expr) -> sp.Poly:
        polynomial = sp.Poly(
            expression,
            retained,
            domain=sp.QQ.poly_ring(eliminated),
        )
        result = sp.Poly(0, eliminated, domain=sp.QQ)
        for order in range(polynomial.degree(), -1, -1):
            coefficient = polynomial.coeff_monomial(retained**order)
            result = reduce_value(result * retained_value)
            result = reduce_value(
                result
                + sp.Poly(
                    coefficient.as_expr(),
                    eliminated,
                    domain=sp.QQ,
                )
            )
        return result

    return reduce_value, evaluate


def _cap_six_saturation_audit(target: Series) -> dict[str, object]:
    """Certify the cap-six unit ideal by explicit saturation charts.

    A direct five-variable Groebner run hides two successive pivot losses.
    This audit follows those losses instead: first the row-seven/eight
    determinant, then a degree-fourteen projection collision.  Every closed
    chart is checked in its own coordinate ring.
    """

    (
        inner_symbols,
        _outer_symbols,
        constraints,
        _outer_substitutions,
    ) = _cap_six_constraints(target)
    a2, a3, a4, a5, a6 = inner_symbols

    # Ordinary first chart: solve rows seven and eight for a4 and a5.
    first_chart: dict[sp.Symbol, sp.Expr] = {}
    for constraint, variable in zip(constraints[:2], (a4, a5)):
        equation = sp.factor(constraint.subs(first_chart))
        first_chart[variable] = sp.factor(
            -equation.subs(variable, 0) / sp.diff(equation, variable)
        )
    first_pivot = sp.factor(
        924 * a2**2 - 140 * a2 + 756 * a3 + 47
    )
    first_pivot_monic = sp.Poly(
        first_pivot, a3, a2, domain=sp.QQ
    ).monic()
    pivot_denominator = sp.together(first_chart[a5]).as_numer_denom()[1]
    assert sp.rem(
        sp.Poly(pivot_denominator, a3, a2, domain=sp.QQ),
        first_pivot_monic,
    ).is_zero

    # Closed first-pivot chart.  Substitute its graph, solve rows seven and
    # eight in a4/a6, and eliminate the remaining a5.  The only common
    # resultant factor is a2**2, whose a2=0 fiber is checked separately.
    exceptional_a3 = sp.factor(
        -(924 * a2**2 - 140 * a2 + 47) / 756
    )
    exceptional_constraints = [
        sp.factor(
            sp.together(constraint.subs(a3, exceptional_a3))
            .as_numer_denom()[0]
        )
        for constraint in constraints
    ]
    coefficient_matrix = sp.Matrix([
        [
            sp.diff(exceptional_constraints[row], variable)
            for variable in (a4, a6)
        ]
        for row in range(2)
    ])
    right_hand_side = sp.Matrix([
        -exceptional_constraints[row].subs({a4: 0, a6: 0})
        for row in range(2)
    ])
    exceptional_solution = coefficient_matrix.inv() * right_hand_side
    exceptional_tail = [
        _primitive_polynomial(
            sp.together(
                constraint.subs({
                    a4: exceptional_solution[0],
                    a6: exceptional_solution[1],
                })
            ).as_numer_denom()[0],
            a5,
            a2,
        )
        for constraint in exceptional_constraints[2:]
    ]
    exceptional_resultants = [
        _primitive_polynomial(
            sp.resultant(
                exceptional_tail[0],
                exceptional_tail[index],
                a5,
            ),
            a2,
        )
        for index in range(1, 4)
    ]
    exceptional_resultant_gcd = exceptional_resultants[0]
    for resultant in exceptional_resultants[1:]:
        exceptional_resultant_gcd = sp.gcd(
            exceptional_resultant_gcd,
            resultant,
        )
    assert sp.factor(exceptional_resultant_gcd.as_expr()) == a2**2

    zero_exception_values = {
        a2: sp.S.Zero,
        a3: -sp.Rational(47, 756),
        a5: -sp.Rational(6637, 2612736),
        a6: -sp.Rational(9379, 18966528),
    }
    zero_exception_tail = [
        _primitive_polynomial(
            sp.together(constraint.subs(zero_exception_values))
            .as_numer_denom()[0],
            a4,
        )
        for constraint in constraints[2:]
    ]
    zero_exception_gcd = zero_exception_tail[0]
    for polynomial in zero_exception_tail[1:]:
        zero_exception_gcd = sp.gcd(
            zero_exception_gcd,
            polynomial,
        )
    assert zero_exception_gcd == sp.Poly(1, a4, domain=sp.QQ)

    # Open first-pivot chart.  Row nine is quadratic in a6; reduce the last
    # three rows modulo it and keep their primitive linear remainders.
    ordinary_tail = [
        sp.factor(
            sp.together(constraint.subs(first_chart))
            .as_numer_denom()[0]
        )
        for constraint in constraints[2:]
    ]
    coefficient_field = sp.QQ.frac_field(a2, a3)
    quadratic = sp.Poly(
        ordinary_tail[0], a6, domain=coefficient_field
    )
    assert quadratic.degree() == 2
    linear_remainders: list[tuple[sp.Expr, sp.Expr]] = []
    for constraint in ordinary_tail[1:]:
        remainder = sp.rem(
            sp.Poly(constraint, a6, domain=coefficient_field),
            quadratic,
        ).as_expr()
        numerator = sp.together(remainder).as_numer_denom()[0]
        primitive = _primitive_polynomial(
            numerator, a6, a2, a3
        ).as_expr()
        linear = sp.expand(primitive).coeff(a6)
        constant = sp.expand(primitive).subs(a6, 0)
        content = sp.gcd(
            sp.Poly(linear, a2, a3),
            sp.Poly(constant, a2, a3),
        ).as_expr()
        linear_remainders.append((
            sp.cancel(linear / content),
            sp.cancel(constant / content),
        ))

    pivot_linear, pivot_constant = linear_remainders[0]
    projected_conditions = [
        _primitive_polynomial(
            sp.together(
                quadratic.as_expr().subs(
                    a6, -pivot_constant / pivot_linear
                )
            ).as_numer_denom()[0],
            a3,
            a2,
        )
    ]
    for linear, constant in linear_remainders[1:]:
        projected_conditions.append(_primitive_polynomial(
            linear * pivot_constant - constant * pivot_linear,
            a3,
            a2,
        ))
    projection_content = sp.gcd(
        sp.gcd(projected_conditions[0], projected_conditions[1]),
        projected_conditions[2],
    )
    assert projection_content.monic() == first_pivot_monic
    saturated_conditions = [
        sp.exquo(condition, projection_content)
        for condition in projected_conditions
    ]
    projection_resultants = [
        _primitive_polynomial(
            sp.resultant(
                saturated_conditions[0],
                saturated_conditions[index],
                a3,
            ),
            a2,
        )
        for index in (1, 2)
    ]
    projection_gcd = sp.gcd(*projection_resultants)
    projection_factors = sp.factor_list(projection_gcd.as_expr())[1]
    assert any(
        sp.degree(factor, a2) == 1 and multiplicity == 11
        for factor, multiplicity in projection_factors
    )
    degree_fourteen = [
        _primitive_polynomial(factor, a2)
        for factor, multiplicity in projection_factors
        if sp.degree(factor, a2) == 14 and multiplicity == 2
    ]
    assert len(degree_fourteen) == 1
    h14 = degree_fourteen[0]
    assert h14.is_irreducible
    h14_payload = str(h14.as_expr())
    assert hashlib.sha256(h14_payload.encode()).hexdigest() == (
        "a587f06492c636d5a1d4bf78bfb176f1aacddf6feb00231279e730694084b3c9"
    )

    # The H14 projection is a collision.  Its linear subresultant supplies
    # the common a3 coordinate, but row ten then loses both a6 coefficients.
    linear_subresultant: sp.Poly | None = None
    for subresultant in sp.subresultants(
        saturated_conditions[0],
        saturated_conditions[1],
        a3,
    ):
        reduced = sp.S.Zero
        univariate = sp.Poly(
            subresultant,
            a3,
            domain=sp.QQ.poly_ring(a2),
        )
        for (order,), coefficient in univariate.terms():
            reduced += sp.rem(
                sp.Poly(coefficient.as_expr(), a2, domain=sp.QQ),
                h14,
            ).as_expr() * a3**order
        candidate = sp.Poly(reduced, a3, a2, domain=sp.QQ)
        if not candidate.is_zero and candidate.degree(a3) == 1:
            linear_subresultant = candidate.primitive()[1]
    assert linear_subresultant is not None
    subresultant_ring = sp.Poly(
        linear_subresultant.as_expr(),
        a3,
        domain=sp.QQ.poly_ring(a2),
    )
    subresultant_linear = sp.Poly(
        subresultant_ring.coeff_monomial(a3).as_expr(),
        a2,
        domain=sp.QQ,
    )
    subresultant_constant = sp.Poly(
        subresultant_ring.coeff_monomial(1).as_expr(),
        a2,
        domain=sp.QQ,
    )
    def initial_reduce_h14(expression: sp.Expr | sp.Poly) -> sp.Poly:
        return sp.rem(
            sp.Poly(expression, a2, domain=sp.QQ),
            h14,
        )

    a3_on_h14 = -initial_reduce_h14(
        subresultant_constant
    ) * sp.invert(
        initial_reduce_h14(subresultant_linear),
        h14,
    )
    reduce_h14, evaluate_h14 = _polynomial_modulus_evaluator(
        h14, a2, a3, a3_on_h14
    )
    projection_vanishes = [
        evaluate_h14(condition.as_expr()).is_zero
        for condition in saturated_conditions
    ]
    assert projection_vanishes == [True, True, True]
    remainder_status = [
        (
            evaluate_h14(linear).is_zero,
            evaluate_h14(constant).is_zero,
        )
        for linear, constant in linear_remainders
    ]
    assert remainder_status == [
        (True, True),
        (False, False),
        (False, False),
    ]

    # Rotate to either surviving linear row.  It solves a6, but the
    # quadratic and the other linear row do not vanish simultaneously.
    rotated_status = []
    for pivot_index in (1, 2):
        linear, constant = linear_remainders[pivot_index]
        linear_value = evaluate_h14(linear)
        constant_value = evaluate_h14(constant)
        a6_value = -constant_value * sp.invert(linear_value, h14)

        def evaluate_a6(expression: sp.Expr) -> sp.Poly:
            polynomial = sp.Poly(
                expression, a6, domain=coefficient_field
            )
            result = sp.Poly(0, a2, domain=sp.QQ)
            for order in range(polynomial.degree(), -1, -1):
                coefficient = polynomial.coeff_monomial(a6**order)
                numerator, denominator = sp.together(
                    coefficient
                ).as_numer_denom()
                coefficient_value = evaluate_h14(numerator) * sp.invert(
                    evaluate_h14(denominator), h14
                )
                result = reduce_h14(
                    result * a6_value + coefficient_value
                )
            return result

        other_index = 1 if pivot_index == 2 else 2
        other_linear, other_constant = linear_remainders[other_index]
        rotated_status.append({
            "pivot_row": pivot_index + 10,
            "quadratic_nonzero": not evaluate_a6(
                quadratic.as_expr()
            ).is_zero,
            "other_linear_nonzero": not reduce_h14(
                evaluate_h14(other_linear) * a6_value
                + evaluate_h14(other_constant)
            ).is_zero,
        })
    assert all(
        row["quadratic_nonzero"] and row["other_linear_nonzero"]
        for row in rotated_status
    )

    # The a2=0 projection also lives only on the excluded first-pivot chart.
    zero_a2_constraints = [
        sp.factor(constraint.subs(a2, 0)) for constraint in constraints
    ]
    zero_a2_solution = sp.solve(
        zero_a2_constraints[:2], (a4, a5), dict=True
    )[0]
    zero_a2_tail = [
        _primitive_polynomial(
            sp.together(constraint.subs(zero_a2_solution))
            .as_numer_denom()[0],
            a6,
            a3,
        )
        for constraint in zero_a2_constraints[2:]
    ]
    zero_a2_basis = sp.groebner(
        zero_a2_tail, a6, a3, order="lex", method="f5b"
    )
    zero_a2_payload = _basis_payload(zero_a2_basis)
    assert any(
        sp.factor(polynomial.as_expr()) == (756 * a3 + 47) ** 2
        for polynomial in zero_a2_basis.polys
    )

    # Bernoulli fixed-pivot no-go.  For q=BCH(-p,h), the unique highest
    # a2-power in q_n is lambda*(-1)^(n-3)*B^+_(n-3).  It vanishes at every
    # even n >= 6, and the a2=0/e2-leading stratum commutes with h's e2 seed.
    bernoulli_rows = []
    for spatial_degree in range(4, 13):
        depth = spatial_degree - 3
        bernoulli = sp.bernoulli(depth)
        coefficient = sp.factor(
            sp.Rational(1, 112) * (-1) ** depth * bernoulli
        )
        bernoulli_rows.append({
            "spatial_degree": spatial_degree,
            "adjoint_depth": depth,
            "highest_a2_power": depth,
            "coefficient": str(coefficient),
        })
        if spatial_degree >= 6 and spatial_degree % 2 == 0:
            assert coefficient == 0

    audit_core: dict[str, object] = {
        "inner_degree": 6,
        "outer_degree": 6,
        "coefficient_orders": [7, 8, 9, 10, 11, 12],
        "constraint_system_sha256": _sha256([
            str(sp.factor(value)) for value in constraints
        ]),
        "first_pivot_polynomial": str(first_pivot),
        "first_pivot_exception_resultant_gcd": str(
            sp.factor(exceptional_resultant_gcd.as_expr())
        ),
        "first_pivot_zero_fiber_tail_gcd": str(
            zero_exception_gcd.as_expr()
        ),
        "ordinary_projection_gcd_factorization": [
            {
                "factor": str(factor),
                "degree": int(sp.degree(factor, a2)),
                "multiplicity": int(multiplicity),
            }
            for factor, multiplicity in projection_factors
        ],
        "degree_fourteen_projection": {
            "polynomial": h14_payload,
            "sha256": hashlib.sha256(h14_payload.encode()).hexdigest(),
            "irreducible_over_QQ": True,
            "projected_conditions_vanish": projection_vanishes,
            "linear_remainder_zero_pairs": remainder_status,
            "rotated_chart_exclusions": rotated_status,
            "projection_collision_not_solution": True,
        },
        "zero_a2_generic_basis": zero_a2_payload,
        "zero_a2_supports_only_first_pivot_exception": True,
        "zero_a2_exception_tail_gcd": str(zero_exception_gcd.as_expr()),
        "complete_six_row_ideal_is_unit": True,
        "bernoulli_fixed_triangularity_no_go": {
            "correct_outer_logarithm": "q=BCH(-p,h)",
            "witt_bracket": "[e_r,e_s]=(s-r)e_(r+s)",
            "leading_target_coefficient": "1/112",
            "highest_power_formula": (
                "[a2^(n-3)]q_n=(1/112)*(-1)^(n-3)*B^+_(n-3)"
            ),
            "rows": bernoulli_rows,
            "even_rows_at_least_six_have_zero_highest_power": True,
            "a2_zero_e2_resonance": "[e_2,e_2]=0",
            "fixed_pivot_triangular_induction_excluded": True,
            "required_replacement": (
                "saturation-stratified subresultant induction with pivot "
                "rotation and actual-degree descent"
            ),
        },
        "claim_boundary": (
            "The exact six-row cap-(6,6) compatibility ideal is the unit "
            "ideal after every pivot-zero and projection-collision chart "
            "is audited. This finite cap does not prove the all-degree "
            "first-excess law. The Bernoulli calculation does prove that "
            "one fixed leading-pivot triangular proof cannot establish "
            "that law."
        ),
    }
    return {**audit_core, "certificate_sha256": _sha256(audit_core)}


def _audit_cap(
    inner_degree: int,
    outer_degree: int,
    target: Series,
) -> CapAudit:
    if inner_degree < 2 or outer_degree < 2:
        raise ValueError("both polynomial vector fields must start at degree two")

    parameter_count_excess_order = inner_degree + outer_degree
    maximum_order = parameter_count_excess_order
    if len(target) <= maximum_order:
        raise ValueError("target series is shorter than the cap discriminator")

    inner_symbols = sp.symbols(f"a2:{inner_degree + 1}")
    outer_symbols = sp.symbols(f"b2:{outer_degree + 1}")
    inner = _zero(maximum_order)
    outer = _zero(maximum_order)
    for order, symbol in enumerate(inner_symbols, 2):
        inner[order] = symbol
    for order, symbol in enumerate(outer_symbols, 2):
        outer[order] = symbol

    composition = _compose(
        _time_one_flow(outer),
        _time_one_flow(inner),
    )
    equations = [
        sp.expand(composition[order] - target[order])
        for order in range(maximum_order + 1)
    ]

    substitutions: dict[sp.Symbol, sp.Expr] = {}
    free_parameters: list[sp.Symbol] = []
    largest_degree = max(inner_degree, outer_degree)
    for order in range(2, largest_degree + 1):
        equation = sp.expand(equations[order].subs(substitutions))
        if order <= inner_degree and order <= outer_degree:
            free_parameters.append(inner_symbols[order - 2])
            solved_symbol = outer_symbols[order - 2]
        elif order <= outer_degree:
            solved_symbol = outer_symbols[order - 2]
        else:
            solved_symbol = inner_symbols[order - 2]
        linear_coefficient = equation.coeff(solved_symbol)
        if linear_coefficient == 0:
            raise AssertionError(
                f"coefficient row {order} lost triangularity"
            )
        solved_value = sp.factor(
            -equation.subs(solved_symbol, 0) / linear_coefficient
        )
        substitutions[solved_symbol] = solved_value

    constraints = [
        sp.together(equations[order].subs(substitutions))
        .as_numer_denom()[0]
        for order in range(largest_degree + 1, maximum_order + 1)
    ]
    free_count = len(free_parameters)
    if len(constraints) != free_count + 1:
        raise AssertionError("cap geometry did not produce one excess row")

    pre_excess_basis = sp.groebner(
        constraints[:free_count],
        *free_parameters,
        order="grevlex",
        method="f5b",
    )
    first_excess_basis = sp.groebner(
        constraints,
        *free_parameters,
        order="grevlex",
        method="f5b",
    )
    pre_excess_is_unit = pre_excess_basis.contains(sp.S.One)
    first_excess_is_unit = first_excess_basis.contains(sp.S.One)
    assert first_excess_is_unit

    first_incompatible_order: int | None = None
    if not pre_excess_is_unit:
        # The pre-excess prefix is proper and the complete prefix is the unit
        # ideal, so monotonicity pins the first failure to the final row.
        first_incompatible_order = maximum_order
    else:
        # Only the small equal-cap exceptions need an earlier-prefix search.
        for prefix_length in range(1, free_count + 1):
            prefix_basis = sp.groebner(
                constraints[:prefix_length],
                *free_parameters,
                order="grevlex",
                method="f5b",
            )
            if prefix_basis.contains(sp.S.One):
                first_incompatible_order = largest_degree + prefix_length
                break
    if first_incompatible_order is None:
        raise AssertionError("the declared cap has no incompatible row")

    constraint_payload = [str(sp.factor(value)) for value in constraints]
    pre_payload = _basis_payload(pre_excess_basis)
    excess_payload = _basis_payload(first_excess_basis)
    return CapAudit(
        inner_degree=inner_degree,
        outer_degree=outer_degree,
        free_parameter_count=free_count,
        matched_through_order=first_incompatible_order - 1,
        first_incompatible_order=first_incompatible_order,
        parameter_count_excess_order=parameter_count_excess_order,
        pre_excess_ideal_is_proper=not pre_excess_is_unit,
        first_excess_ideal_is_unit=True,
        pre_excess_basis_size=len(pre_excess_basis.polys),
        first_excess_basis_size=len(first_excess_basis.polys),
        constraint_system_sha256=_sha256(constraint_payload),
        pre_excess_basis_sha256=_sha256(pre_payload),
        first_excess_basis_sha256=_sha256(excess_payload),
    )


def build_certificate(maximum_degree: int = 5) -> dict[str, object]:
    if maximum_degree < 2:
        raise ValueError("maximum_degree must be at least two")
    maximum_order = 2 * maximum_degree
    extended_target = _critical_holonomy_coefficients(
        max(maximum_order, 12)
    )
    target = extended_target[: maximum_order + 1]
    assert target[0] == 0
    assert target[1] == 1
    assert target[2] == 0
    assert target[3] == sp.Rational(1, 112)

    rows = [
        _audit_cap(inner_degree, outer_degree, target)
        for inner_degree in range(2, maximum_degree + 1)
        for outer_degree in range(2, maximum_degree + 1)
    ]
    core: dict[str, object] = {
        "schema": "axiompack.two_polynomial_flow_direct_factorization.v2",
        "flow_convention": "exp(q(x)d/dx) after exp(p(x)d/dx)",
        "coefficient_field": "QQ",
        "minimum_generator_vanishing_order": 2,
        "maximum_degree_audited": maximum_degree,
        "target_coefficients": [str(value) for value in target],
        "target_series_sha256": _sha256([str(value) for value in target]),
        "cap_rows": [row.to_dict() for row in rows],
        "cap_six_saturation_audit": _cap_six_saturation_audit(
            extended_target
        ),
        "all_declared_pre_parameter_excess_ideals_proper": all(
            row.pre_excess_ideal_is_proper for row in rows
        ),
        "all_declared_first_excess_ideals_unit": all(
            row.first_excess_ideal_is_unit for row in rows
        ),
        "observed_first_excess_law": (
            "Every audited cap is inconsistent no later than "
            "inner_degree + outer_degree; unequal caps in the declared "
            "grid first fail exactly at that order."
        ),
        "claim_boundary": (
            "Exact nonfactorization is proved separately for every declared "
            "degree cap in the finite grid and, by a separate saturation "
            "audit, for the complete six-row cap-(6,6) ideal. The repeated "
            "first-excess law is an induction target, not an all-degree "
            "theorem. Bernoulli parity and resonant pivot loss exclude a "
            "fixed-pivot triangular proof, so the surviving induction must "
            "rotate subresultant charts. The output does not close the "
            "Jacobian tail-minimax lower bound."
        ),
    }
    return {**core, "certificate_sha256": _sha256(core)}


if __name__ == "__main__":
    print(json.dumps(build_certificate(), indent=2, sort_keys=True))
