#!/usr/bin/env python3
"""All-order lower rays for the exceptional ``P*Q^2*C`` and ``P*Q^3*C``.

Both prefixes have a finite leading logarithmic window.  One layer
below it, the projected cost-two adjoint action preserves a two-state
module.  Current cone columns cancel the companion state but do not
change the terminal quotient.  This file checks the complete finite
row solve and certifies the resulting nonpolynomial right-Magnus
response.
"""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class LowMixedCase:
    name: str
    prefix: str
    slope: int
    terminal_grade: tuple[int, int]
    cost_two: Sparse
    cost_three: Sparse
    zero_grade_coefficient: sp.Rational
    core_terminal: sp.Rational
    held_out_depth_twelve: sp.Rational


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


PQ2 = LowMixedCase(
    name="pq2",
    prefix="P*Q^2*C",
    slope=9,
    terminal_grade=(-15, -11),
    cost_two={
        (3, 7): -sp.Rational(1, 8),
        (3, 8): sp.Rational(11, 32),
        (4, 7): -sp.Rational(5, 32),
        (4, 8): sp.Rational(51, 64),
        (4, 9): -sp.Rational(37, 128),
        (5, 7): -sp.Rational(1, 16),
        (5, 8): sp.Rational(7, 8),
        (5, 9): -sp.Rational(75, 64),
        (6, 8): sp.Rational(23, 64),
        (6, 9): -sp.Rational(213, 128),
        (6, 10): sp.Rational(127, 256),
        (7, 9): -sp.Rational(13, 16),
        (7, 10): sp.Rational(169, 128),
        (8, 10): sp.Rational(231, 256),
        (8, 11): -sp.Rational(3, 8),
        (9, 11): -sp.Rational(63, 128),
        (10, 12): sp.Rational(27, 256),
    },
    cost_three={
        (7, 11): -sp.Rational(9, 1024),
        (9, 11): sp.Rational(9, 1024),
    },
    zero_grade_coefficient=sp.Rational(27, 256),
    core_terminal=sp.Rational(3159, 131072),
    held_out_depth_twelve=-sp.Rational(
        55615691736622684675837754865,
        18380933703309326321702196477952,
    ),
)


PQ3 = LowMixedCase(
    name="pq3",
    prefix="P*Q^3*C",
    slope=12,
    terminal_grade=(-18, -14),
    cost_two={
        (4, 9): -sp.Rational(5, 128),
        (4, 10): sp.Rational(13, 128),
        (5, 9): -sp.Rational(9, 128),
        (5, 10): sp.Rational(75, 256),
        (5, 11): -sp.Rational(45, 512),
        (6, 9): -sp.Rational(7, 128),
        (6, 10): sp.Rational(115, 256),
        (6, 11): -sp.Rational(231, 512),
        (7, 9): -sp.Rational(1, 64),
        (7, 10): sp.Rational(89, 256),
        (7, 11): -sp.Rational(465, 512),
        (7, 12): sp.Rational(201, 1024),
        (8, 10): sp.Rational(27, 256),
        (8, 11): -sp.Rational(429, 512),
        (8, 12): sp.Rational(765, 1024),
        (9, 11): -sp.Rational(75, 256),
        (9, 12): sp.Rational(995, 1024),
        (9, 13): -sp.Rational(223, 1024),
        (10, 12): sp.Rational(439, 1024),
        (10, 13): -sp.Rational(35, 64),
        (11, 13): -sp.Rational(357, 1024),
        (11, 14): sp.Rational(123, 1024),
        (12, 14): sp.Rational(153, 1024),
        (13, 15): -sp.Rational(27, 1024),
    },
    cost_three={
        (10, 14): sp.Rational(27, 8192),
        (12, 14): -sp.Rational(27, 8192),
    },
    zero_grade_coefficient=-sp.Rational(27, 1024),
    core_terminal=sp.Rational(729, 262144),
    held_out_depth_twelve=-sp.Rational(
        16884595808465322118653,
        22183885503994014526192306094080,
    ),
)


CASES = (PQ2, PQ3)


def _grade(
    case: LowMixedCase,
    exponent: Exponent,
    cost: int,
) -> tuple[int, int]:
    return (
        2 * exponent[0] - case.slope * cost - 2,
        2 * exponent[1] - case.slope * cost - 6,
    )


def _project(
    case: LowMixedCase,
    value: Sparse,
    cost: int,
) -> Sparse:
    return {
        exponent: sp.factor(coefficient)
        for exponent, coefficient in value.items()
        if (
            coefficient != 0
            and all(
                component >= terminal
                for component, terminal in zip(
                    _grade(case, exponent, cost),
                    case.terminal_grade,
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
    case: LowMixedCase,
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
                case,
                _add(
                    result[order],
                    _bracket(left_value, right_value, 2),
                ),
                order + 1,
            )
    return result


def _known_forward_velocity(
    case: LowMixedCase,
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
            case,
            logarithm,
            nested,
            maximum_velocity_order,
        )
        coefficient = forward[depth]
        if coefficient:
            result = _project(
                case,
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
    case: LowMixedCase,
    cost: int,
    multiplier_weight: int,
) -> tuple[tuple[int, int], Sparse] | None:
    multiplier = _canonical_c_multiplier(multiplier_weight + 2)
    if multiplier is None:
        return None
    p_exponent, q_exponent = multiplier
    amplitude_degree = (cost - 1) // 2
    weight_offset = (
        multiplier_weight - case.slope * amplitude_degree
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
    return multiplier, _project(case, value, cost)


def _solve_row(
    case: LowMixedCase,
    known_velocity: Sparse,
    cost: int,
) -> tuple[sp.Expr, list[dict[str, object]], int]:
    amplitude_degree = (cost - 1) // 2
    terminal_exponent = (
        case.slope * amplitude_degree - 2,
        case.slope * amplitude_degree + 2,
    )
    columns = []
    for offset in range(-4, 1):
        multiplier_weight = (
            case.slope * amplitude_degree + offset
        )
        column = _c_seed_column(
            case,
            cost,
            multiplier_weight,
        )
        if column is not None:
            columns.append((
                offset,
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
            for _offset, _weight, _multiplier, column in columns
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
                _offset,
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
            f"{case.name} lower row {cost} has no unique solve"
        )
    solution = tuple(next(iter(solution_set)))
    if solution[-1].free_symbols:
        raise AssertionError(
            f"{case.name} terminal row {cost} retains freedom"
        )
    free_parameters = sorted({
        str(symbol)
        for value in solution[:-1]
        for symbol in value.free_symbols
    })
    return sp.factor(solution[-1]), [
        {
            "offset": offset,
            "multiplier_weight": weight,
            "multiplier_p_exponent": multiplier[0],
            "multiplier_q_exponent": multiplier[1],
            "coefficient": str(sp.factor(coefficient)),
        }
        for (
            offset,
            weight,
            multiplier,
            _column,
        ), coefficient in zip(
            columns,
            solution[:-1],
            strict=True,
        )
    ], len(free_parameters)


def _adjoint_factor(
    case: LowMixedCase,
    depth: int | sp.Expr,
) -> sp.Expr:
    return sp.factor(
        case.zero_grade_coefficient
        * 2
        * (case.slope * depth - 4)
    )


def _orbit(
    case: LowMixedCase,
    depth: int,
) -> sp.Expr:
    return sp.factor(sp.prod(
        _adjoint_factor(case, index)
        for index in range(depth)
    ))


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


def _normalized_response(
    case: LowMixedCase,
    maximum_depth: int,
) -> list[sp.Expr]:
    response = []
    for depth in range(maximum_depth + 1):
        forcing = sp.factor(
            sp.Rational((-1) ** depth, factorial(depth + 2))
            * case.core_terminal
            / (2 * depth + 5)
        )
        response.append(sp.factor(
            forcing
            + sum(
                _feedback_kernel(depth, earlier_depth)
                * response[earlier_depth]
                for earlier_depth in range(depth)
            )
        ))
    return response


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


def _imaginary_pole_certificate(
    truncation_order: int = 50,
) -> dict[str, object]:
    pi_lower, pi_upper = _pi_bounds()
    radius_lower = 2 * pi_lower
    radius_upper = 2 * pi_upper
    partial_lower = Fraction(0)
    partial_upper = Fraction(0)
    for order in range(1, truncation_order, 2):
        coefficient = Fraction(
            order + 1,
            (2 * order + 5) * factorial(order + 2),
        )
        coefficient *= (-1) ** ((order - 1) // 2)
        lower_power = radius_lower**order
        upper_power = radius_upper**order
        if coefficient >= 0:
            partial_lower += coefficient * lower_power
            partial_upper += coefficient * upper_power
        else:
            partial_lower += coefficient * upper_power
            partial_upper += coefficient * lower_power

    # For all n, (n+1)/(2*n+5) < 1/2 and 2*pi < 7.
    first_omitted_majorant = Fraction(
        7**truncation_order,
        2 * factorial(truncation_order + 2),
    )
    ratio_bound = Fraction(7, truncation_order + 3)
    tail_bound = (
        first_omitted_majorant / (1 - ratio_bound)
    )
    assert partial_lower - tail_bound > Fraction(1, 200)
    return {
        "evaluation_point": "2*pi*i",
        "normalized_function": "J/core_terminal",
        "coefficient": "(n+1)/((2*n+5)*(n+2)!)",
        "truncation_order": truncation_order,
        "pi_enclosure": (
            "Machin: pi=16*atan(1/5)-4*atan(1/239), "
            "alternating rational remainders"
        ),
        "tail_majorant": (
            "7^N/(2*(N+2)!)/(1-7/(N+3))"
        ),
        "certified_imaginary_part_lower_bound": "1/200",
        "nonremovable_response_pole": True,
    }


def _two_state_certificate(
    case: LowMixedCase,
) -> dict[str, object]:
    depth = sp.symbols("n", integer=True, nonnegative=True)
    source_amplitude = depth + 2
    terminal = (
        case.slope * source_amplitude - 2,
        case.slope * source_amplitude + 2,
    )
    companion = (
        case.slope * source_amplitude,
        case.slope * source_amplitude + 2,
    )
    next_terminal = (
        case.slope * (source_amplitude + 1) - 2,
        case.slope * (source_amplitude + 1) + 2,
    )
    next_companion = (
        case.slope * (source_amplitude + 1),
        case.slope * (source_amplitude + 1) + 2,
    )

    def symbolic_bracket_image(
        source: tuple[sp.Expr, sp.Expr],
    ) -> dict[tuple[int, int], sp.Expr]:
        result: dict[tuple[int, int], sp.Expr] = {}
        for (
            left_x,
            left_y,
        ), coefficient in case.cost_two.items():
            exponent = (
                sp.expand(left_x + source[0] - 1),
                sp.expand(left_y + source[1] - 3),
            )
            relative = (
                int(sp.expand(
                    exponent[0]
                    - case.slope * (source_amplitude + 1)
                )),
                int(sp.expand(
                    exponent[1]
                    - case.slope * (source_amplitude + 1)
                )),
            )
            if relative[0] < -2 or relative[1] < 2:
                continue
            multiplier = sp.expand(
                left_y * source[0] - left_x * source[1]
            )
            result[relative] = sp.factor(
                result.get(relative, 0)
                + coefficient * multiplier
            )
        return result

    terminal_image = symbolic_bracket_image(terminal)
    companion_image = symbolic_bracket_image(companion)
    expected_terminal_factor = _adjoint_factor(case, depth)
    assert terminal_image == {
        (-2, 2): expected_terminal_factor,
    }
    assert set(companion_image) == {(0, 2)}
    assert all(
        _adjoint_factor(case, integer_depth) != 0
        for integer_depth in range(100)
    )
    assert sp.solve(
        sp.Eq(expected_terminal_factor, 0),
        depth,
    ) == []
    unrestricted_depth = sp.symbols("x")
    assert sp.solve(
        sp.Eq(
            _adjoint_factor(case, unrestricted_depth),
            0,
        ),
        unrestricted_depth,
    ) == [sp.Rational(4, case.slope)]

    core = _project(
        case,
        _bracket(case.cost_two, case.cost_three, 2),
        5,
    )
    assert core[(
        2 * case.slope - 2,
        2 * case.slope + 2,
    )] == case.core_terminal
    assert set(core) == {
        (2 * case.slope - 2, 2 * case.slope + 2),
        (2 * case.slope, 2 * case.slope + 2),
    }

    # The column support proves quotient independence at every depth:
    # offsets -4,-3 are below the projection; offset -2 contains only
    # the companion state; offsets -1,0 have nonzero higher pivots and
    # therefore vanish before the terminal equation is reached.
    for amplitude in range(2, 11):
        cost = 2 * amplitude + 1
        columns = {
            offset: _c_seed_column(
                case,
                cost,
                case.slope * amplitude + offset,
            )
            for offset in range(-4, 1)
        }
        assert all(
            columns[offset] is not None
            and not columns[offset][1]
            for offset in (-4, -3)
        )
        assert (
            columns[-2] is not None
            and set(columns[-2][1]) == {
                (
                    case.slope * amplitude,
                    case.slope * amplitude + 2,
                )
            }
        )
        for offset in (-1, 0):
            assert columns[offset] is not None
            pivot = (
                case.slope * amplitude + offset + 2,
                case.slope * amplitude + offset + 4,
            )
            assert columns[offset][1].get(pivot, 0) != 0

    return {
        "states": {
            "terminal": (
                f"u^({case.slope}*(n+2)-2)"
                f"*z^({case.slope}*(n+2)+2)"
            ),
            "companion": (
                f"u^({case.slope}*(n+2))"
                f"*z^({case.slope}*(n+2)+2)"
            ),
        },
        "terminal_transition": str(expected_terminal_factor),
        "companion_transition": str(
            companion_image[(0, 2)]
        ),
        "zero_of_terminal_transition": str(
            sp.Rational(4, case.slope)
        ),
        "core_terminal": str(case.core_terminal),
        "current_column_pivots": {
            "affine_invisible_offsets": [-4, -3],
            "companion_offset": -2,
            "forced_zero_offsets": [-1, 0],
            "terminal_independent": True,
        },
        "symbolic_next_terminal": [
            str(next_terminal[0]),
            str(next_terminal[1]),
        ],
        "symbolic_next_companion": [
            str(next_companion[0]),
            str(next_companion[1]),
        ],
    }


def _run_case(
    case: LowMixedCase,
    maximum_depth: int,
) -> dict[str, object]:
    maximum_cost = 5 + 2 * maximum_depth
    logarithm = [{} for _ in range(maximum_cost + 1)]
    logarithm[2] = case.cost_two
    logarithm[3] = case.cost_three
    rows = []
    for depth in range(maximum_depth + 1):
        cost = 5 + 2 * depth
        known_velocity = _known_forward_velocity(
            case,
            logarithm,
            cost,
        )
        terminal, controls, affine_dimension = _solve_row(
            case,
            known_velocity,
            cost,
        )
        exponent = (
            case.slope * (depth + 2) - 2,
            case.slope * (depth + 2) + 2,
        )
        logarithm[cost] = {exponent: terminal}
        rows.append({
            "depth": depth,
            "cost": cost,
            "exponent": list(exponent),
            "coefficient": str(terminal),
            "normalized_coefficient": str(
                sp.factor(terminal / _orbit(case, depth))
            ),
            "nonzero": terminal != 0,
            "affine_dimension": affine_dimension,
            "current_controls": controls,
        })

    normalized = _normalized_response(case, maximum_depth)
    assert [
        sp.Rational(row["normalized_coefficient"])
        for row in rows
    ] == normalized
    assert all(row["affine_dimension"] == 2 for row in rows)
    assert (
        sp.Rational(rows[12]["coefficient"])
        == case.held_out_depth_twelve
    )
    expected_prefix = (
        [
            sp.Rational(3159, 1310720),
            sp.Rational(28431, 587202560),
            sp.Rational(255879, 7516192768),
        ]
        if case is PQ2
        else [
            sp.Rational(729, 2621440),
            -sp.Rational(6561, 4697620480),
            sp.Rational(59049, 150323855360),
        ]
    )
    assert [
        sp.Rational(row["coefficient"])
        for row in rows[:3]
    ] == expected_prefix
    return {
        "prefix": case.prefix,
        "slope": case.slope,
        "terminal_grade": list(case.terminal_grade),
        "maximum_depth": maximum_depth,
        "maximum_cost": maximum_cost,
        "first_zero_depth": next(
            (
                row["depth"]
                for row in rows
                if not row["nonzero"]
            ),
            None,
        ),
        "two_state_quotient": _two_state_certificate(case),
        "forcing": (
            f"(-1)^n*({case.core_terminal})/(n+2)!"
        ),
        "response_numerator_coefficient": (
            f"({case.core_terminal})*(n+1)"
            "/((2*n+5)*(n+2)!)"
        ),
        "held_out_depth_twelve_matches": True,
        "complete_five_column_recurrence_matches_scalar_response": True,
        "rows": rows,
    }


def run(maximum_depth: int = 40) -> dict[str, object]:
    if maximum_depth < 12:
        raise ValueError("the held-out depth-twelve row is required")
    cases = [
        _run_case(case, maximum_depth)
        for case in CASES
    ]
    return {
        "schema": (
            "axiompack.jacobian_cone_low_mixed_"
            "lower_terminal_recurrence.v1"
        ),
        "cases": cases,
        "common_response": {
            "ode": (
                "2*x*f(x)*E'(x)+(2+3*f(x))*E(x)=H(x), "
                "f(x)=(1-exp(-x))/x"
            ),
            "forcing": (
                "H(x)=q*(exp(-x)-1+x)/x^2"
            ),
            "solution": (
                "E(x)=x*J(x)/(exp(x)-1)"
            ),
            "normalized_numerator_coefficient": (
                "[x^n](J/q)=(n+1)/((2*n+5)*(n+2)!)"
            ),
            "pole_certificate": _imaginary_pole_certificate(),
        },
        "claim_boundary": (
            "All-order nontermination of one lower source ray for "
            "each exceptional mixed representative P*Q^2*C and "
            "P*Q^3*C. This completes the one-C quotient modulo the "
            "cusp discriminant, but does not yet propagate through "
            "positive discriminant-adic depth or higher powers of C."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
