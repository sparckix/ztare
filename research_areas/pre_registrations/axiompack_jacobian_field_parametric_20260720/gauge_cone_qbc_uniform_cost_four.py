#!/usr/bin/env python3
"""Uniform cost-four source transfer for the prefixes ``Q^b*C``.

The calculation is performed with a symbolic integer ``b``.  Source
monomials are represented in the fixed chart

    r = u*z

relative to the common factor ``(-1/4)^b*r^(3*b)``.  Only radial offsets
at least two and normal orders at most three can feed the terminal
cost-four slot.  Generalized binomial coefficients therefore give an
exact finite quotient rather than a numerical interpolation in ``b``.
"""

from __future__ import annotations

from math import factorial
import json
from pathlib import Path
import sys
from typing import TypeAlias

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_cone_radial_triangular_staircase import (  # noqa: E402
    _canonical_c_multiplier,
    _canonical_cone_monomial,
)
from gauge_regular_singular_connection import (  # noqa: E402
    source_only_connection,
)


B = sp.symbols("b", integer=True, positive=True)
P, Q, S = sp.symbols("P Q s")
R, Z = sp.symbols("r z")

FixedSource: TypeAlias = dict[tuple[int, int], sp.Expr]
ParametricSource: TypeAlias = dict[tuple[int, int], sp.Expr]
TargetTerm: TypeAlias = tuple[int, int, sp.Expr]
TargetExpression: TypeAlias = dict[tuple[int, int], sp.Expr]

MINIMUM_RADIAL_OFFSET = 1
MAXIMUM_NORMAL_ORDER = 3
MAXIMUM_Q_DEFICIT = 12


def _clean(value: dict[tuple[int, int], sp.Expr]) -> dict[
    tuple[int, int], sp.Expr
]:
    return {
        exponent: coefficient
        for exponent, raw in value.items()
        if (coefficient := sp.factor(raw)) != 0
    }


def _add(
    left: dict[tuple[int, int], sp.Expr],
    right: dict[tuple[int, int], sp.Expr],
) -> dict[tuple[int, int], sp.Expr]:
    result = dict(left)
    for exponent, coefficient in right.items():
        result[exponent] = (
            result.get(exponent, sp.Integer(0)) + coefficient
        )
    return _clean(result)


def _scale(
    value: dict[tuple[int, int], sp.Expr],
    scalar: sp.Expr,
) -> dict[tuple[int, int], sp.Expr]:
    return _clean({
        exponent: scalar * coefficient
        for exponent, coefficient in value.items()
    })


def _multiply_fixed(
    left: FixedSource,
    right: FixedSource,
) -> FixedSource:
    result: FixedSource = {}
    for (left_r, left_z), left_coefficient in left.items():
        for (right_r, right_z), right_coefficient in right.items():
            exponent = (left_r + right_r, left_z + right_z)
            result[exponent] = (
                result.get(exponent, sp.Integer(0))
                + left_coefficient * right_coefficient
            )
    return _clean(result)


def _multiply_parametric_fixed(
    left: ParametricSource,
    right: FixedSource,
) -> ParametricSource:
    result: ParametricSource = {}
    for (left_r, left_z), left_coefficient in left.items():
        for (right_r, right_z), right_coefficient in right.items():
            exponent = (left_r + right_r, left_z + right_z)
            if (
                exponent[0] < MINIMUM_RADIAL_OFFSET - 16
                or exponent[1] > MAXIMUM_NORMAL_ORDER
            ):
                continue
            result[exponent] = (
                result.get(exponent, sp.Integer(0))
                + left_coefficient * right_coefficient
            )
    return _clean(result)


def _trim_parametric(
    value: ParametricSource,
) -> ParametricSource:
    return {
        exponent: coefficient
        for exponent, coefficient in value.items()
        if (
            exponent[0] >= MINIMUM_RADIAL_OFFSET
            and exponent[1] <= MAXIMUM_NORMAL_ORDER
        )
    }


def _fixed_power(value: FixedSource, power: int) -> FixedSource:
    if power < 0:
        raise ValueError("fixed powers must be nonnegative")
    result: FixedSource = {(0, 0): sp.Integer(1)}
    for _ in range(power):
        result = _multiply_fixed(result, value)
    return result


def _falling(value: sp.Expr, depth: int) -> sp.Expr:
    return sp.prod(value - index for index in range(depth))


def _response_coefficient(depth: int) -> sp.Expr:
    if depth == 0:
        return sp.Rational(1, 4)
    return sp.Rational(
        sp.bernoulli(depth + 1),
        2 * factorial(depth + 1),
    )


def _numeric_adjoint_multiplier(
    q_exponent: int,
    depth: int,
) -> sp.Expr:
    return sp.Rational(
        (-1) ** q_exponent
        * 9
        * (
            3 * q_exponent
            + 2
            - 2 * (3 * q_exponent + 1) * depth
        ),
        2 ** (2 * q_exponent + 2),
    )


def _numeric_terminal_coefficient(
    q_exponent: int,
    depth: int,
) -> sp.Expr:
    velocity_seed = sp.Rational(
        (-1) ** q_exponent * (9 * q_exponent + 4),
        2 ** (2 * q_exponent + 5),
    )
    orbit = sp.prod(
        _numeric_adjoint_multiplier(q_exponent, index)
        for index in range(depth)
    )
    return sp.factor(
        velocity_seed * _response_coefficient(depth) * orbit
    )


def _q_zero_power(q_shift: int) -> ParametricSource:
    """Expansion of ``Q_0^(b+q_shift)`` after factoring ``(-1/4)^b``."""

    exponent = B + q_shift
    result: ParametricSource = {}
    fixed_scale = (-sp.Rational(1, 4)) ** q_shift
    for first_deficit in range(MAXIMUM_Q_DEFICIT + 1):
        for second_deficit in range(
            MAXIMUM_Q_DEFICIT + 1 - first_deficit
        ):
            chosen = first_deficit + second_deficit
            radial_offset = (
                3 * q_shift
                - first_deficit
                - 2 * second_deficit
            )
            normal_order = second_deficit
            if (
                radial_offset < MINIMUM_RADIAL_OFFSET - 16
                or normal_order > MAXIMUM_NORMAL_ORDER
            ):
                continue
            coefficient = (
                fixed_scale
                * _falling(exponent, chosen)
                * (-1) ** chosen
                / (
                    sp.factorial(first_deficit)
                    * sp.factorial(second_deficit)
                )
            )
            key = (radial_offset, normal_order)
            result[key] = (
                result.get(key, sp.Integer(0)) + coefficient
            )
    return _clean(result)


def _fixed_coefficients() -> tuple[
    list[FixedSource], list[FixedSource]
]:
    data = source_only_connection()
    parameter, family_v, family_t, _unused = data["symbols"]
    family_p, family_q = data["family"]
    u = sp.symbols("u")
    substitution = {
        family_v: u - 1,
        family_t: (Z - 2 + 3 * (u - 1)) / 2,
    }
    result = []
    for family_value in (family_p, family_q):
        fixed = sp.cancel(family_value.subs(substitution))
        series = sp.series(
            fixed,
            parameter,
            0,
            3,
        ).removeO().expand()
        coefficients = []
        for order in range(3):
            value = sp.cancel(
                series.coeff(parameter, order).subs(u, R / Z)
            )
            polynomial = sp.Poly(sp.expand(value), R, Z)
            coefficients.append({
                exponent: sp.factor(coefficient)
                for exponent, coefficient in polynomial.terms()
                if coefficient != 0
            })
        result.append(coefficients)
    return result[0], result[1]


class SourcePullback:
    def __init__(self) -> None:
        self.p_coefficients, self.q_coefficients = _fixed_coefficients()
        self.p_power_cache: dict[
            int, list[FixedSource]
        ] = {0: [
            {(0, 0): sp.Integer(1)},
            {},
            {},
        ]}
        self.monomial_cache: dict[
            tuple[int, int, int], ParametricSource
        ] = {}

    def p_power(self, power: int) -> list[FixedSource]:
        if power in self.p_power_cache:
            return self.p_power_cache[power]
        parent = self.p_power(power - 1)
        result = []
        for order in range(3):
            value: FixedSource = {}
            for index in range(order + 1):
                value = _add(
                    value,
                    _multiply_fixed(
                        parent[index],
                        self.p_coefficients[order - index],
                    ),
                )
            result.append(value)
        self.p_power_cache[power] = result
        return result

    def q_power(self, q_shift: int) -> list[ParametricSource]:
        exponent = B + q_shift
        q_zero = _q_zero_power(q_shift)
        q_one = _multiply_parametric_fixed(
            _q_zero_power(q_shift - 1),
            self.q_coefficients[1],
        )
        q_two_linear = _multiply_parametric_fixed(
            _q_zero_power(q_shift - 1),
            self.q_coefficients[2],
        )
        q_two_quadratic = _multiply_parametric_fixed(
            _q_zero_power(q_shift - 2),
            _fixed_power(self.q_coefficients[1], 2),
        )
        return [
            q_zero,
            _scale(q_one, exponent),
            _add(
                _scale(q_two_linear, exponent),
                _scale(
                    q_two_quadratic,
                    exponent * (exponent - 1) / 2,
                ),
            ),
        ]

    def monomial(
        self,
        p_exponent: int,
        q_shift: int,
        order: int,
    ) -> ParametricSource:
        key = (p_exponent, q_shift, order)
        if key in self.monomial_cache:
            return self.monomial_cache[key]
        p_series = self.p_power(p_exponent)
        q_series = self.q_power(q_shift)
        result: ParametricSource = {}
        for index in range(order + 1):
            result = _add(
                result,
                _multiply_parametric_fixed(
                    q_series[order - index],
                    p_series[index],
                ),
            )
        result = _trim_parametric(result)
        self.monomial_cache[key] = result
        return result

    def expression(
        self,
        terms: TargetExpression,
        order: int,
    ) -> ParametricSource:
        result: ParametricSource = {}
        for (
            p_exponent,
            q_shift,
        ), coefficient in terms.items():
            result = _add(
                result,
                _scale(
                    self.monomial(
                        p_exponent,
                        q_shift,
                        order,
                    ),
                    coefficient,
                ),
            )
        return result


def _target_add(
    left: TargetExpression,
    right: TargetExpression,
) -> TargetExpression:
    return _add(left, right)


def _target_scale(
    value: TargetExpression,
    scalar: sp.Expr,
) -> TargetExpression:
    return _scale(value, scalar)


def _fixed_target_coefficients(
    maximum_order: int,
) -> list[dict[tuple[int, int], sp.Expr]]:
    cubic = (
        96
        * (S**2 - 12 * S + 16)
        / ((S - 6) ** 3 * (S - 4) ** 2 * (S + 4) ** 2)
    )
    mixed = 2 * S / ((S - 4) * (S + 4))
    background = cubic * P**3 + mixed * P * Q - Q**2 / 4
    series = sp.series(
        background,
        S,
        0,
        maximum_order + 1,
    ).removeO().expand()
    return [
        {
            exponent: sp.factor(coefficient)
            for exponent, coefficient in sp.Poly(
                series.coeff(S, order),
                P,
                Q,
            ).terms()
            if coefficient != 0
        }
        for order in range(maximum_order + 1)
    ]


def _target_bracket_fixed_left(
    left: dict[tuple[int, int], sp.Expr],
    right: TargetExpression,
) -> TargetExpression:
    result: TargetExpression = {}
    for (left_p, left_q), left_coefficient in left.items():
        for (
            right_p,
            right_q_shift,
        ), right_coefficient in right.items():
            multiplier = (
                left_q * right_p
                - left_p * (B + right_q_shift)
            )
            exponent = (
                left_p + right_p - 1,
                left_q + right_q_shift - 1,
            )
            result[exponent] = (
                result.get(exponent, sp.Integer(0))
                + multiplier
                * left_coefficient
                * right_coefficient
            )
    return _clean(result)


def _covariant_prefixes() -> list[TargetExpression]:
    cusp = {
        (3, 0): sp.Integer(4),
        (2, 0): -sp.Integer(1),
        (1, 1): -sp.Integer(18),
        (0, 2): sp.Integer(27),
        (0, 1): sp.Integer(4),
    }
    background = _fixed_target_coefficients(1)
    first = _target_scale(
        _target_bracket_fixed_left(background[0], cusp),
        -1,
    )
    second = _target_scale(
        _target_add(
            _target_bracket_fixed_left(background[0], first),
            _target_bracket_fixed_left(background[1], cusp),
        ),
        -sp.Rational(1, 2),
    )
    return [cusp, first, second]


def _stable_radial_control(
    radial_offset: int,
) -> tuple[int, int] | None:
    candidates = []
    for integer_b in range(6, 13):
        value = _canonical_cone_monomial(
            3 * integer_b + radial_offset
        )
        candidates.append(
            None
            if value is None
            else (value[0], value[1] - integer_b)
        )
    if len(set(candidates)) != 1:
        raise AssertionError(
            f"radial control changes with b: {radial_offset}, {candidates}"
        )
    return candidates[0]


def _stable_c_control(
    radial_offset: int,
) -> tuple[int, int] | None:
    candidates = []
    for integer_b in range(6, 13):
        value = _canonical_c_multiplier(
            3 * integer_b + radial_offset
        )
        candidates.append(
            None
            if value is None
            else (value[0], value[1] - integer_b)
        )
    if len(set(candidates)) != 1:
        raise AssertionError(
            f"C control changes with b: {radial_offset}, {candidates}"
        )
    return candidates[0]


def _c_multiple(
    p_exponent: int,
    q_shift: int,
) -> TargetExpression:
    return {
        (p_exponent + 3, q_shift): sp.Integer(4),
        (p_exponent + 2, q_shift): -sp.Integer(1),
        (p_exponent + 1, q_shift + 1): -sp.Integer(18),
        (p_exponent, q_shift + 2): sp.Integer(27),
        (p_exponent, q_shift + 1): sp.Integer(4),
    }


def _normalize_row(
    residual: ParametricSource,
    target_terms: TargetExpression,
    pullback: SourcePullback,
) -> tuple[ParametricSource, TargetExpression]:
    result = dict(residual)
    controls = dict(target_terms)
    while True:
        radial_offsets = [
            radial_offset
            for (radial_offset, normal_order), coefficient
            in result.items()
            if (
                normal_order == 0
                and coefficient != 0
                and _stable_radial_control(radial_offset) is not None
            )
        ]
        if not radial_offsets:
            break
        radial_offset = max(radial_offsets)
        control = _stable_radial_control(radial_offset)
        assert control is not None
        seed = _scale(
            pullback.monomial(control[0], control[1], 0),
            8,
        )
        diagonal = seed[(radial_offset, 0)]
        coefficient = sp.factor(
            -result[(radial_offset, 0)] / diagonal
        )
        term = {control: coefficient}
        controls = _target_add(controls, term)
        result = _add(
            result,
            _scale(pullback.expression(term, 0), 8),
        )

    while True:
        normal_offsets = [
            radial_offset
            for (radial_offset, normal_order), coefficient
            in result.items()
            if (
                normal_order == 2
                and coefficient != 0
                and _stable_c_control(radial_offset) is not None
            )
        ]
        if not normal_offsets:
            break
        radial_offset = max(normal_offsets)
        control = _stable_c_control(radial_offset)
        assert control is not None
        target_seed = _c_multiple(*control)
        source_seed = _scale(
            pullback.expression(target_seed, 0),
            8,
        )
        diagonal = source_seed[(radial_offset, 2)]
        coefficient = sp.factor(
            -result[(radial_offset, 2)] / diagonal
        )
        term = _target_scale(target_seed, coefficient)
        controls = _target_add(controls, term)
        result = _add(
            result,
            _scale(pullback.expression(term, 0), 8),
        )
    return result, controls


def _row_residual(
    target_rows: list[TargetExpression],
    current_order: int,
    pullback: SourcePullback,
) -> ParametricSource:
    result: ParametricSource = {}
    for target_order, terms in enumerate(target_rows, 1):
        if target_order > current_order:
            break
        result = _add(
            result,
            _scale(
                pullback.expression(
                    terms,
                    current_order - target_order,
                ),
                8,
            ),
        )
    return result


def run() -> dict[str, object]:
    pullback = SourcePullback()
    covariant = _covariant_prefixes()

    target_rows = [covariant[0]]
    row_two_terms = dict(covariant[1])
    row_two_residual = _row_residual(
        [target_rows[0], row_two_terms],
        2,
        pullback,
    )
    row_two_residual, row_two_terms = _normalize_row(
        row_two_residual,
        row_two_terms,
        pullback,
    )
    target_rows.append(row_two_terms)

    row_three_terms = dict(covariant[2])
    row_three_residual = _row_residual(
        [*target_rows, row_three_terms],
        3,
        pullback,
    )
    row_three_residual, row_three_terms = _normalize_row(
        row_three_residual,
        row_three_terms,
        pullback,
    )
    target_rows.append(row_three_terms)

    terminal = sp.factor(row_three_residual[(2, 3)])
    expected = sp.factor((9 * B + 4) / 32)
    # Coefficients in this quotient have the common factor (-1/4)^b
    # removed.  Restoring it gives
    # (-1)^b*(9*b+4)/2^(2*b+5).
    assert sp.factor(terminal - expected) == 0, (
        terminal,
        expected,
        sp.factor(terminal - expected),
    )
    assert row_three_residual.get((2, 2), 0) == 0
    assert sp.Poly(-32 * terminal, B).degree() == 1

    instantiated = {}
    response_checks = {}
    for integer_b in range(6, 13):
        restored = sp.factor(
            terminal.subs(B, integer_b)
            * (-sp.Rational(1, 4)) ** integer_b
        )
        expected_value = sp.Rational(
            (-1) ** integer_b * (9 * integer_b + 4),
            2 ** (2 * integer_b + 5),
        )
        assert restored == expected_value
        instantiated[str(integer_b)] = str(restored)
        response = [
            _numeric_terminal_coefficient(integer_b, depth)
            for depth in range(8)
        ]
        assert all(
            response[depth] != 0
            for depth in range(1, 8, 2)
        )
        assert all(
            response[depth] == 0
            for depth in range(2, 8, 2)
        )
        response_checks[str(integer_b)] = {
            "depth_zero": str(response[0]),
            "depth_one": str(response[1]),
            "depth_three": str(response[3]),
        }

    return {
        "schema": (
            "axiompack.jacobian_cone_qbc_"
            "uniform_cost_four.v1"
        ),
        "prefix_family": "Q^b*C, b>=6",
        "symbolic_quotient": {
            "factored_common_scale": "(-1/4)^b",
            "terminal_key_in_r_z": [
                "3*b+2",
                3,
            ],
            "terminal_coefficient_after_factoring": str(terminal),
            "normal_order_two_same_slot": "0",
        },
        "restored_terminal_velocity_coefficient": (
            "(-1)^b*(9*b+4)/2^(2*b+5)"
        ),
        "instantiations_b_6_to_12": instantiated,
        "zero_grade_logarithm_coefficient": (
            "(-1)^(b+1)*9/2^(2*b+2)"
        ),
        "adjoint_multiplier": (
            "(-1)^b*9*(3*b+2-2*(3*b+1)*k)/2^(2*b+2)"
        ),
        "right_magnus_response": {
            "function": (
                "x/(exp(x)-1) * integral_0^1 "
                "t^3*exp(t^2*x) dt"
            ),
            "positive_depth_coefficient": (
                "B_(k+1)/(2*(k+1)!)"
            ),
            "checked_coefficients_b_6_to_12": response_checks,
        },
        "all_order_nonzero_subsequence": "odd depths k=2*m+1",
        "odd_depth_costs": "6+4*m",
        "odd_depth_exponents": (
            "(6*b+3+2*(3*b+1)*m,"
            "6*b+6+2*(3*b+1)*m)"
        ),
        "nonzero_for_integer_b_at_least_six": True,
        "limiting_spatial_rate": "3*b+1",
        "claim_boundary": (
            "Exact symbolic cost-four transfer for the covariantly "
            "completed pure-Q one-C family with b>=6. The exceptional "
            "b=4,5 cases are checked by their finite projected replays. "
            "Mixed one-C prefixes and higher powers of C are excluded."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
