#!/usr/bin/env python3
"""Finite-width lower-grade recurrence for the prefix ``Q^3*C``.

The leading grade window has a finite logarithm, but the next reachable
grade ``(-16,-12)`` starts at cost five.  This replay solves the current
one-C columns in that quotient without rebuilding the full polynomial
staircase.
"""

from __future__ import annotations

from fractions import Fraction
from math import factorial
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
SRC_ROOT = HERE.parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gauge_cone_radial_triangular_staircase import (  # noqa: E402
    _canonical_c_multiplier,
)
from gauge_controlled_global_magnus_hamiltonian import (  # noqa: E402
    _add,
    _bracket,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    VelocityPlacement,
    forward_dexp_coefficients,
)


Exponent = tuple[int, int]
Sparse = dict[Exponent, sp.Expr]
TruncatedPolynomial = dict[tuple[int, int], sp.Expr]

TERMINAL_GRADE = (-16, -12)
SLOPE = 10

L_TWO: Sparse = {
    (3, 8): -sp.Rational(1, 64),
    (3, 9): sp.Rational(1, 32),
    (4, 8): -sp.Rational(3, 64),
    (4, 9): sp.Rational(9, 64),
    (5, 8): -sp.Rational(3, 64),
    (5, 9): sp.Rational(9, 32),
    (5, 10): -sp.Rational(33, 256),
    (6, 8): -sp.Rational(1, 64),
    (6, 9): sp.Rational(17, 64),
    (6, 10): -sp.Rational(111, 256),
    (7, 9): sp.Rational(3, 32),
    (7, 10): -sp.Rational(135, 256),
    (7, 11): sp.Rational(51, 256),
    (8, 10): -sp.Rational(57, 256),
    (8, 11): sp.Rational(57, 128),
    (9, 11): sp.Rational(67, 256),
    (9, 12): -sp.Rational(35, 256),
    (10, 12): -sp.Rational(39, 256),
    (11, 13): sp.Rational(9, 256),
}
L_THREE: Sparse = {
    (8, 12): -sp.Rational(191, 2048),
    (9, 12): sp.Rational(5, 128),
    (10, 13): sp.Rational(57, 1024),
    (12, 14): -sp.Rational(27, 2048),
}

P_NORMALIZED: TruncatedPolynomial = {
    (0, 0): sp.Integer(1),
    (1, 0): -sp.Rational(4, 3),
    (2, 1): -sp.Rational(2, 3),
}
Q_NORMALIZED: TruncatedPolynomial = {
    (0, 0): sp.Integer(1),
    (1, 0): -sp.Integer(1),
    (2, 1): -sp.Integer(1),
}
C_NORMALIZED: TruncatedPolynomial = {
    (0, 0): sp.Integer(1),
    (1, 0): -sp.Rational(4, 3),
    (2, 0): sp.Rational(4, 9),
    (2, 1): -sp.Rational(8, 9),
}

CORE_INITIAL_T = -sp.Rational(27, 2048)
CORE_INITIAL_C = sp.Rational(57, 1024)
CORE_INITIAL_E = -sp.Rational(191, 2048)


def _grade(exponent: Exponent, cost: int) -> tuple[int, int]:
    return (
        2 * exponent[0] - SLOPE * cost - 2,
        2 * exponent[1] - SLOPE * cost - 6,
    )


def _project(value: Sparse, cost: int) -> Sparse:
    return {
        exponent: sp.factor(coefficient)
        for exponent, coefficient in value.items()
        if (
            coefficient != 0
            and all(
                component >= terminal
                for component, terminal in zip(
                    _grade(exponent, cost),
                    TERMINAL_GRADE,
                    strict=True,
                )
            )
        )
    }


def _scale(value: Sparse, scalar: sp.Expr) -> Sparse:
    return {
        exponent: sp.factor(scalar * coefficient)
        for exponent, coefficient in value.items()
        if coefficient != 0
    }


def _series_bracket(
    left: list[Sparse],
    right: list[Sparse],
    maximum_order: int,
) -> list[Sparse]:
    result = [{} for _ in range(maximum_order + 1)]
    for left_order, left_value in enumerate(
        left[: maximum_order + 1]
    ):
        for right_order, right_value in enumerate(
            right[: maximum_order + 1 - left_order]
        ):
            order = left_order + right_order
            result[order] = _project(
                _add(
                    result[order],
                    _bracket(left_value, right_value, 2),
                ),
                order + 1,
            )
    return result


def _known_forward_velocity(
    logarithm: list[Sparse],
    cost: int,
) -> Sparse:
    maximum_velocity_order = cost - 1
    derivative = [
        _scale(logarithm[order + 1], order + 1)
        for order in range(maximum_velocity_order)
    ]
    derivative.append({})
    result = dict(derivative[maximum_velocity_order])
    nested = derivative
    forward = forward_dexp_coefficients(
        maximum_velocity_order,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    for depth in range(1, maximum_velocity_order + 1):
        nested = _series_bracket(
            logarithm,
            nested,
            maximum_velocity_order,
        )
        coefficient = forward[depth]
        if coefficient:
            result = _project(
                _add(
                    result,
                    _scale(
                        nested[maximum_velocity_order],
                        sp.Rational(
                            coefficient.numerator,
                            coefficient.denominator,
                        ),
                    ),
                ),
                cost,
            )
    return result


def _truncated_product(
    left: TruncatedPolynomial,
    right: TruncatedPolynomial,
    maximum_t_degree: int,
) -> TruncatedPolynomial:
    result: TruncatedPolynomial = {}
    for (left_t, left_z), left_coefficient in left.items():
        for (right_t, right_z), right_coefficient in right.items():
            t_degree = left_t + right_t
            if t_degree > maximum_t_degree:
                continue
            exponent = (t_degree, left_z + right_z)
            result[exponent] = (
                result.get(exponent, sp.Integer(0))
                + left_coefficient * right_coefficient
            )
    return {
        exponent: sp.factor(coefficient)
        for exponent, coefficient in result.items()
        if coefficient != 0
    }


def _truncated_power(
    value: TruncatedPolynomial,
    exponent: int,
    maximum_t_degree: int,
) -> TruncatedPolynomial:
    result: TruncatedPolynomial = {(0, 0): sp.Integer(1)}
    factor = value
    remaining = exponent
    while remaining:
        if remaining % 2:
            result = _truncated_product(
                result,
                factor,
                maximum_t_degree,
            )
        remaining //= 2
        if remaining:
            factor = _truncated_product(
                factor,
                factor,
                maximum_t_degree,
            )
    return result


def _c_seed_column(
    cost: int,
    multiplier_weight: int,
) -> tuple[tuple[int, int], Sparse] | None:
    multiplier = _canonical_c_multiplier(multiplier_weight + 2)
    if multiplier is None:
        return None
    p_exponent, q_exponent = multiplier
    amplitude_degree = (cost - 1) // 2
    weight_offset = (
        multiplier_weight - SLOPE * amplitude_degree
    )
    maximum_t_degree = 4 + weight_offset
    if maximum_t_degree < 0:
        return None
    normalized = _truncated_product(
        _truncated_power(
            P_NORMALIZED,
            p_exponent,
            maximum_t_degree,
        ),
        _truncated_power(
            Q_NORMALIZED,
            q_exponent,
            maximum_t_degree,
        ),
        maximum_t_degree,
    )
    normalized = _truncated_product(
        normalized,
        C_NORMALIZED,
        maximum_t_degree,
    )
    leading = sp.factor(
        8
        * (-sp.Rational(3, 4)) ** p_exponent
        * (-sp.Rational(1, 4)) ** q_exponent
        * (-sp.Rational(9, 16))
    )
    value: Sparse = {}
    for (
        t_degree,
        extra_normal_order,
    ), coefficient in normalized.items():
        radial_degree = multiplier_weight + 2 - t_degree
        normal_order = 2 + extra_normal_order
        exponent = (
            radial_degree,
            radial_degree + normal_order,
        )
        value[exponent] = (
            value.get(exponent, sp.Integer(0))
            + leading * coefficient
        )
    return multiplier, _project(value, cost)


def _solve_row(
    known_velocity: Sparse,
    cost: int,
) -> tuple[sp.Expr, list[dict[str, object]]]:
    amplitude_degree = (cost - 1) // 2
    terminal_exponent = (
        SLOPE * amplitude_degree - 2,
        SLOPE * amplitude_degree + 2,
    )
    columns = []
    for offset in range(-4, 1):
        multiplier_weight = SLOPE * amplitude_degree + offset
        column = _c_seed_column(cost, multiplier_weight)
        if column is not None:
            columns.append((
                multiplier_weight,
                column[0],
                column[1],
            ))

    controls = sp.symbols(f"c0:{len(columns)}")
    terminal_symbol = sp.symbols("d")
    exponents = sorted(
        set(known_velocity)
        | {terminal_exponent}
        | {
            exponent
            for _weight, _multiplier, column in columns
            for exponent in column
        }
    )
    equations = [
        known_velocity.get(exponent, 0)
        + cost
        * terminal_symbol
        * (1 if exponent == terminal_exponent else 0)
        - sum(
            symbol * column.get(exponent, 0)
            for symbol, (
                _weight,
                _multiplier,
                column,
            ) in zip(controls, columns, strict=True)
        )
        for exponent in exponents
    ]
    solution_set = sp.linsolve(
        equations,
        (*controls, terminal_symbol),
    )
    if solution_set is sp.EmptySet or len(solution_set) != 1:
        raise AssertionError(
            f"lower terminal row {cost} has no unique solve"
        )
    solution = tuple(next(iter(solution_set)))
    if solution[-1].free_symbols:
        raise AssertionError(
            f"lower terminal coefficient at {cost} retains freedom"
        )
    free_parameters = sorted(
        {
            str(symbol)
            for value in solution[:-1]
            for symbol in value.free_symbols
        }
    )
    return sp.factor(solution[-1]), [
        {
            "multiplier_weight": weight,
            "multiplier_p_exponent": multiplier[0],
            "multiplier_q_exponent": multiplier[1],
            "coefficient": str(sp.factor(coefficient)),
            "affine_parameters": free_parameters,
        }
        for (
            weight,
            multiplier,
            _column,
        ), coefficient in zip(
            columns,
            solution[:-1],
            strict=True,
        )
    ]


def _orbit_multiplier(depth: int) -> sp.Expr:
    return sp.prod(
        sp.Rational(9 * (5 * index - 2), 64)
        for index in range(depth)
    )


def _periodic_delta(index: int) -> int:
    return (0, -3, 3)[index % 3]


def _cokernel_coefficient(index: int) -> sp.Rational:
    return -sp.Rational(
        150 * index * index
        + 635 * index
        + 673
        + _periodic_delta(index),
        27,
    )


def _advance_core(
    index: int,
    transverse: sp.Expr,
    contact: sp.Expr,
    exterior: sp.Expr,
) -> tuple[sp.Expr, sp.Expr, sp.Expr]:
    return (
        sp.factor(
            sp.Rational(9 * (10 * index + 1), 128)
            * transverse
        ),
        sp.factor(
            -sp.Rational(105 * (5 * index + 3), 128)
            * transverse
            + sp.Rational(9 * (20 * index - 13), 256)
            * contact
        ),
        sp.factor(
            sp.Rational(51 * (20 * index + 17), 128)
            * transverse
            - sp.Rational(105 * (10 * index + 1), 256)
            * contact
            + sp.Rational(9 * (5 * index - 7), 64)
            * exterior
        ),
    )


def _core_forcing(
    maximum_depth: int,
) -> tuple[list[sp.Expr], list[sp.Expr]]:
    transverse = CORE_INITIAL_T
    contact = CORE_INITIAL_C
    exterior = CORE_INITIAL_E
    orbit = sp.Integer(1)
    ode_forcing = []
    divided_forcing = []
    for depth in range(maximum_depth + 1):
        transverse, contact, exterior = _advance_core(
            depth,
            transverse,
            contact,
            exterior,
        )
        cokernel = _cokernel_coefficient(depth)
        value = sp.factor(
            -sp.Rational(
                (-1) ** (depth + 1),
                factorial(depth + 2),
            )
            * (cokernel * transverse + exterior)
            / orbit
        )
        ode_forcing.append(value)
        divided_forcing.append(
            sp.factor(value / (2 * depth + 5))
        )
        orbit = sp.factor(
            orbit
            * sp.Rational(9 * (5 * depth - 2), 64)
        )
    return ode_forcing, divided_forcing


def _feedback_kernel(
    depth: int,
    earlier_depth: int,
) -> sp.Rational:
    return sp.Rational(
        (-1) ** (depth - earlier_depth + 1)
        * (2 * earlier_depth + 3),
        (2 * depth + 5)
        * factorial(depth - earlier_depth + 1),
    )


def _scalar_response(
    divided_forcing: list[sp.Expr],
) -> list[sp.Expr]:
    result = []
    for depth, forcing in enumerate(divided_forcing):
        result.append(sp.factor(
            forcing
            + sum(
                _feedback_kernel(depth, earlier_depth)
                * result[earlier_depth]
                for earlier_depth in range(depth)
            )
        ))
    return result


def _numerator_coefficients(
    ode_forcing: list[sp.Expr],
) -> list[sp.Expr]:
    return [
        sp.factor(
            sum(
                ode_forcing[forcing_order]
                / factorial(order - forcing_order)
                for forcing_order in range(order + 1)
            )
            / (2 * order + 5)
        )
        for order in range(len(ode_forcing))
    ]


def _alternating_arctangent_bounds(
    reciprocal: int,
    terms: int,
) -> tuple[Fraction, Fraction]:
    partial = Fraction(0)
    for order in range(terms):
        partial += Fraction(
            (-1) ** order,
            (2 * order + 1)
            * reciprocal ** (2 * order + 1),
        )
    next_term = Fraction(
        (-1) ** terms,
        (2 * terms + 1)
        * reciprocal ** (2 * terms + 1),
    )
    other_endpoint = partial + next_term
    return min(partial, other_endpoint), max(
        partial,
        other_endpoint,
    )


def _pi_bounds() -> tuple[Fraction, Fraction]:
    first = _alternating_arctangent_bounds(5, 60)
    second = _alternating_arctangent_bounds(239, 20)
    return (
        16 * first[0] - 4 * second[1],
        16 * first[1] - 4 * second[0],
    )


def _as_fraction(value: sp.Expr) -> Fraction:
    rational = sp.Rational(value)
    return Fraction(int(rational.p), int(rational.q))


def _imaginary_numerator_certificate(
    numerator: list[sp.Expr],
    truncation_order: int = 100,
) -> dict[str, object]:
    if len(numerator) < truncation_order:
        raise ValueError("the numerator prefix is too short")
    pi_lower, pi_upper = _pi_bounds()
    radius_lower = 2 * pi_lower
    radius_upper = 2 * pi_upper
    partial_lower = Fraction(0)
    partial_upper = Fraction(0)
    for order in range(1, truncation_order, 2):
        coefficient = (
            _as_fraction(numerator[order])
            * (-1) ** ((order - 1) // 2)
        )
        lower_power = radius_lower**order
        upper_power = radius_upper**order
        if coefficient >= 0:
            partial_lower += coefficient * lower_power
            partial_upper += coefficient * upper_power
        else:
            partial_lower += coefficient * upper_power
            partial_upper += coefficient * lower_power

    # The all-order bound |H_n| <=
    # 130*(n+2)^4/(n+2)! gives this evaluated J-tail at |x|<7.
    majorant_at_cut = Fraction(
        520
        * 14**truncation_order
        * (truncation_order + 2) ** 4,
        (2 * truncation_order + 5)
        * factorial(truncation_order + 2),
    )
    ratio_bound = Fraction(
        14 * (truncation_order + 3) ** 3,
        (truncation_order + 2) ** 4,
    )
    assert ratio_bound < Fraction(1, 6)
    tail_bound = majorant_at_cut / (1 - ratio_bound)
    assert partial_lower - tail_bound > Fraction(1, 4000)
    return {
        "evaluation_point": "2*pi*i",
        "truncation_order": truncation_order,
        "pi_enclosure": (
            "Machin: pi=16*atan(1/5)-4*atan(1/239), "
            "alternating remainders"
        ),
        "forcing_majorant": (
            "|H_n| <= 130*(n+2)^4/(n+2)!"
        ),
        "tail_majorant": (
            "520*14^N*(N+2)^4/((2*N+5)*(N+2)!) "
            "with geometric ratio < 1/6"
        ),
        "certified_imaginary_part_lower_bound": "1/4000",
        "numerator_nonzero": True,
        "nonremovable_response_pole": True,
    }


def _symbolic_all_order_checks() -> dict[str, object]:
    index = sp.symbols("k", integer=True, nonnegative=True)
    residue_rows = []
    for residue, p_exponent in ((0, 1), (1, 0), (2, 2)):
        q_exponent = (
            10 * (index + 2) - 2 * p_exponent
        ) / 3
        coefficient_t4_z2 = sp.factor(
            sp.Rational(4, 9)
            * p_exponent
            * (p_exponent - 1)
            / 2
            + q_exponent * (q_exponent - 1) / 2
            + sp.Rational(2, 3)
            * p_exponent
            * q_exponent
            + sp.Rational(16, 27) * p_exponent
            + sp.Rational(8, 9) * q_exponent
        )
        expected = sp.factor(
            (
                150 * index**2
                + 635 * index
                + 673
                + (0, -3, 3)[residue]
            )
            / 27
        )
        # The formula is used only on index == residue (mod 3).
        quotient = sp.factor(
            (
                coefficient_t4_z2 - expected
            ).subs(index, 3 * sp.symbols("m") + residue)
        )
        assert quotient == 0
        residue_rows.append({
            "residue": residue,
            "canonical_p_exponent": p_exponent,
            "canonical_q_exponent": str(q_exponent),
            "cokernel_coefficient": str(-expected),
        })

    # Normalize the core state after S_(k+1) by the terminal orbit p_k.
    # From k>=7, these bounds close under the absolute transition.
    transverse = CORE_INITIAL_T
    contact = CORE_INITIAL_C
    exterior = CORE_INITIAL_E
    orbit = sp.Integer(1)
    for depth in range(8):
        transverse, contact, exterior = _advance_core(
            depth,
            transverse,
            contact,
            exterior,
        )
        if depth < 7:
            orbit = sp.factor(
                orbit
                * sp.Rational(9 * (5 * depth - 2), 64)
            )
    assert abs(transverse / orbit) <= 9**2
    assert abs(contact / orbit) <= 10 * 9**3
    assert abs(exterior / orbit) <= 100 * 9**4

    shifted = sp.symbols("m", integer=True, nonnegative=True)
    k = shifted + 7
    transverse_margin = sp.factor(
        (k + 3) ** 2
        - (10 * k + 11)
        * (k + 2) ** 2
        / (2 * (5 * k - 2))
    )
    contact_margin = sp.factor(
        10 * (k + 3) ** 3
        - 35 * (5 * k + 8)
        * (k + 2) ** 2
        / (6 * (5 * k - 2))
        - (20 * k + 7)
        * 10
        * (k + 2) ** 3
        / (4 * (5 * k - 2))
    )
    exterior_margin = sp.factor(
        100 * (k + 3) ** 4
        - 100 * (k + 2) ** 4
        - 17 * (20 * k + 37)
        * (k + 2) ** 2
        / (6 * (5 * k - 2))
        - 35 * (10 * k + 11)
        * 10
        * (k + 2) ** 3
        / (12 * (5 * k - 2))
    )
    for margin in (
        transverse_margin,
        contact_margin,
        exterior_margin,
    ):
        numerator, denominator = sp.fraction(margin)
        assert sp.Poly(
            sp.expand(numerator),
            shifted,
        ).all_coeffs()
        assert all(
            coefficient > 0
            for coefficient in sp.Poly(
                sp.expand(numerator),
                shifted,
            ).all_coeffs()
        )
        assert denominator.subs(shifted, 0) > 0

    cokernel_bound_margin = sp.expand(
        810 * (index + 2) ** 2
        - (
            150 * index**2
            + 635 * index
            + 676
        )
    )
    assert all(
        coefficient > 0
        for coefficient in sp.Poly(
            cokernel_bound_margin,
            index,
        ).all_coeffs()
    )
    return {
        "seed_cokernel_residue_rows": residue_rows,
        "three_state_transition": {
            "T_next": "9*(10*k+1)*T/128",
            "C_next": (
                "-105*(5*k+3)*T/128"
                "+9*(20*k-13)*C/256"
            ),
            "E_next": (
                "51*(20*k+17)*T/128"
                "-105*(10*k+1)*C/256"
                "+9*(5*k-7)*E/64"
            ),
        },
        "normalized_core_majorant": (
            "|T_k|<=(k+2)^2, |C_k|<=10*(k+2)^3, "
            "|E_k|<=100*(k+2)^4 after orbit division"
        ),
        "forcing_majorant": (
            "|H_k|<=130*(k+2)^4/(k+2)!"
        ),
        "response_ode": (
            "2*x*f(x)*E'(x)+(2+3*f(x))*E(x)=H(x), "
            "f(x)=(1-exp(-x))/x"
        ),
        "response_solution": (
            "E(x)=x*J(x)/(exp(x)-1)"
        ),
    }


def run(maximum_depth: int = 40) -> dict[str, object]:
    if maximum_depth < 3:
        raise ValueError("at least four lower terminal rows are required")
    maximum_cost = 5 + 2 * maximum_depth
    logarithm = [{} for _ in range(maximum_cost + 1)]
    logarithm[2] = L_TWO
    logarithm[3] = L_THREE
    rows = []
    for depth in range(maximum_depth + 1):
        cost = 5 + 2 * depth
        known_velocity = _known_forward_velocity(logarithm, cost)
        terminal, controls = _solve_row(known_velocity, cost)
        exponent = (18 + 10 * depth, 22 + 10 * depth)
        logarithm[cost] = {exponent: terminal}
        rows.append({
            "depth": depth,
            "cost": cost,
            "exponent": list(exponent),
            "coefficient": str(terminal),
            "normalized_coefficient": str(
                sp.factor(terminal / _orbit_multiplier(depth))
            ),
            "nonzero": terminal != 0,
            "current_c_controls": controls,
        })

    expected = [
        sp.Rational(729, 2621440),
        sp.Rational(729, 146800640),
        sp.Rational(190269, 300647710720),
    ]
    assert [
        sp.Rational(row["coefficient"])
        for row in rows[:3]
    ] == expected
    certificate_depth = max(maximum_depth, 99)
    ode_forcing, divided_forcing = _core_forcing(
        certificate_depth
    )
    scalar_response = _scalar_response(divided_forcing)
    normalized_response = [
        sp.factor(
            sp.Rational(row["coefficient"])
            / _orbit_multiplier(depth)
        )
        for depth, row in enumerate(rows)
    ]
    assert (
        normalized_response
        == scalar_response[: maximum_depth + 1]
    )
    numerator = _numerator_coefficients(ode_forcing)
    pole_certificate = _imaginary_numerator_certificate(
        numerator
    )
    symbolic_certificate = _symbolic_all_order_checks()
    first_zero = next(
        (
            row["depth"]
            for row in rows
            if not row["nonzero"]
        ),
        None,
    )
    return {
        "schema": (
            "axiompack.jacobian_cone_q3c_"
            "lower_terminal_recurrence.v1"
        ),
        "grading": "(2*a-10*cost-2,2*b-10*cost-6)",
        "terminal_grade": list(TERMINAL_GRADE),
        "fixed_logarithmic_costs": [2, 3],
        "orbit_multiplier": "9*(5*k-2)/64",
        "maximum_depth": maximum_depth,
        "maximum_cost": maximum_cost,
        "first_zero_depth": first_zero,
        "all_checked_coefficients_nonzero": first_zero is None,
        "scalar_response_matches_full_recurrence": True,
        "all_order_terminal_ray_certificate": {
            **symbolic_certificate,
            **pole_certificate,
            "conclusion": (
                "J(2*pi*i) is nonzero, so E has a "
                "nonremovable pole and infinitely many "
                "nonzero lower-grade coefficients."
            ),
        },
        "rows": rows,
        "claim_boundary": (
            "All-order nontermination in the first lower grade of "
            "the Q^3*C prefix. This does not classify mixed one-C "
            "prefixes or higher powers of C."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
