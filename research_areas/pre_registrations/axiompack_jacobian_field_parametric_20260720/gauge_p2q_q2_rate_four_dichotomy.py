#!/usr/bin/env python3
"""Exact low-weight order-one radial tradeoff and its exceptional replay."""

from __future__ import annotations

from fractions import Fraction
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_controlled_global_magnus_hamiltonian import (  # noqa: E402
    SparseHamiltonian,
    _add,
    _scale,
)
from gauge_p2q_source_newton_modules import (  # noqa: E402
    _excess,
    _project,
    _projected_magnus,
    _to_sparse,
    _translated_velocity,
)
from gauge_regular_singular_connection import (  # noqa: E402
    source_only_connection,
)


MAXIMUM_INPUT_COST = 6
SPECIAL_Q2_COEFFICIENT = sp.Rational(325, 1344)
SOURCE_Q2_COEFFICIENT = 8 * SPECIAL_Q2_COEFFICIENT
TARGET_GRADE = (-14, -7)
FIRST_PAIR = frozenset({(-10, -5), (-4, -2)})
DOMINANT_PAIR = frozenset({(-8, -4), (-6, -3)})


def _grade(
    exponent: tuple[int, int],
    cost: int,
) -> tuple[int, int]:
    return (
        3 * exponent[0] - 7 * cost - 3,
        3 * exponent[1] - 5 * cost - 9,
    )


def _subtract(
    left: SparseHamiltonian,
    right: SparseHamiltonian,
) -> SparseHamiltonian:
    return _add(left, _scale(right, Fraction(-1)))


def _perturbation_coefficients(
    expression: sp.Expr,
    s: sp.Symbol,
    u: sp.Symbol,
    z: sp.Symbol,
) -> list[SparseHamiltonian]:
    polynomial = sp.series(
        expression, s, 0, MAXIMUM_INPUT_COST
    ).removeO().expand()
    return [
        _to_sparse(
            sp.cancel(polynomial.coeff(s, order)),
            u,
            z,
        )
        for order in range(MAXIMUM_INPUT_COST)
    ]


def _connection_data() -> tuple[
    list[SparseHamiltonian],
    list[SparseHamiltonian],
    list[SparseHamiltonian],
    list[SparseHamiltonian],
]:
    data = source_only_connection()
    p2q_velocity = _translated_velocity(data)
    s, v, t, _unused = data["symbols"]
    family_p, family_q = data["family"]
    u, z = sp.symbols("u z")
    substitution = {
        v: u - 1,
        t: (z - 2 + 3 * (u - 1)) / 2,
    }
    p = sp.factor(family_p.subs(substitution))
    q = sp.factor(family_q.subs(substitution))
    pq_unit = _perturbation_coefficients(
        8 * s * p * q, s, u, z
    )
    q2_unit = _perturbation_coefficients(
        8 * s * q**2, s, u, z
    )
    q2_raw = _perturbation_coefficients(
        s * q**2, s, u, z
    )
    special_velocity = [
        _project(
            _add(
                p2q_velocity[order],
                {
                    exponent: sp.factor(
                        SOURCE_Q2_COEFFICIENT * coefficient
                    )
                    for exponent, coefficient
                    in q2_raw[order].items()
                },
            ),
            order + 1,
        )
        for order in range(MAXIMUM_INPUT_COST)
    ]
    return special_velocity, p2q_velocity, pq_unit, q2_unit


def _terminal_sequence(
    logarithm: list[SparseHamiltonian],
    maximum_depth: int,
) -> list[sp.Expr]:
    multiplier = sp.Integer(1)
    result = []
    for depth in range(maximum_depth + 1):
        order = 2 + 3 * depth
        exponent = (
            1 + 7 * depth,
            4 + 5 * depth,
        )
        result.append(sp.factor(
            logarithm[order].get(exponent, 0)
            / multiplier
        ))
        multiplier = sp.factor(
            multiplier
            * (-sp.Rational(1, 5376))
            * (2 * depth - 3)
        )
    return result


def _scaled_velocity(
    velocity: list[SparseHamiltonian],
    scalar: int,
) -> list[SparseHamiltonian]:
    return [
        {
            exponent: (
                coefficient
                if cost == 3 and exponent == (8, 8)
                else sp.factor(scalar * coefficient)
            )
            for exponent, coefficient in value.items()
        }
        for cost, value in enumerate(velocity, 1)
    ]


def _pair_velocity(
    velocity: list[SparseHamiltonian],
    grades: frozenset[tuple[int, int]],
) -> list[SparseHamiltonian]:
    return [
        {
            exponent: coefficient
            for exponent, coefficient in value.items()
            if (
                (cost == 3 and exponent == (8, 8))
                or _grade(exponent, cost) in grades
            )
        }
        for cost, value in enumerate(velocity, 1)
    ]


def _p_adic_valuation(value: sp.Expr, prime: int) -> int:
    value = sp.factor(value)
    if value == 0:
        return 10**9
    numerator = abs(int(sp.numer(value)))
    denominator = int(sp.denom(value))
    valuation = 0
    while numerator % prime == 0:
        numerator //= prime
        valuation += 1
    while denominator % prime == 0:
        denominator //= prime
        valuation -= 1
    return valuation


def _unit_mod_three(value: sp.Expr) -> int:
    value = sp.factor(value)
    numerator = int(sp.numer(value))
    denominator = int(sp.denom(value))
    while numerator % 3 == 0:
        numerator //= 3
    while denominator % 3 == 0:
        denominator //= 3
    return (
        (numerator % 3)
        * pow(denominator % 3, -1, 3)
    ) % 3


def _first_bernoulli_convention(order: int) -> sp.Rational:
    """Bernoulli number with ``B_1=-1/2``."""
    if order == 1:
        return -sp.Rational(1, 2)
    return sp.Rational(sp.bernoulli(order))


def _dominant_pair_remainder(depth: int) -> sp.Expr:
    """Coefficient before the final ``x/(exp(x)-1)`` operator."""
    if depth == 0:
        return sp.Integer(0)
    return -sp.Rational(
        174 * depth**2 - depth - 164,
        (
            2016
            * sp.factorial(depth)
            * (depth + 1)
            * (3 * depth + 2)
        ),
    )


def _dominant_pair_closed_sequence(
    maximum_depth: int,
) -> list[sp.Expr]:
    remainder = [
        _dominant_pair_remainder(depth)
        for depth in range(maximum_depth + 1)
    ]
    return [
        sp.factor(sum(
            (
                _first_bernoulli_convention(index)
                / sp.factorial(index)
                * remainder[depth - index]
            )
            for index in range(depth + 1)
        ))
        for depth in range(maximum_depth + 1)
    ]


def _dominant_pair_even_unit(depth: int) -> sp.Expr:
    """Closed form for ``27*depth!*D_depth`` at positive even depth."""
    assert depth >= 2 and depth % 2 == 0
    bernoulli_sum = sum(
        (
            sp.binomial(depth, index)
            * _first_bernoulli_convention(depth - index)
            / (3 * index + 2)
        )
        for index in range(1, depth + 1)
    )
    return sp.factor(
        sp.Rational(387, 112) * bernoulli_sum
        - sp.Rational(33, 224)
        * _first_bernoulli_convention(depth)
    )


def run(maximum_order: int = 60) -> dict[str, object]:
    if maximum_order < 60:
        raise ValueError("replay needs the order-sixty held-out tail")
    velocity, p2q_velocity, pq_unit, q2_unit = _connection_data()

    assert [
        max((sum(exponent) for exponent in value), default=None)
        for value in pq_unit
    ] == [None, 10, 12, 14, 14, 14]
    assert [
        max((sum(exponent) for exponent in value), default=None)
        for value in q2_unit
    ] == [None, 12, 14, 16, 16, 16]
    assert q2_unit[1][(6, 6)] == sp.Rational(1, 2)

    assert p2q_velocity[1][(6, 6)] == -sp.Rational(
        325, 2688
    )
    assert (6, 6) not in velocity[1]
    assert velocity[2][(8, 8)] == -sp.Rational(1, 14336)
    assert [
        max((sum(exponent) for exponent in value), default=None)
        for value in velocity
    ] == [None, 10, 16, 18, 20, 20]
    assert all(
        first <= 0 and second <= 0
        for cost, value in enumerate(velocity, 1)
        for exponent in value
        for first, second in [_grade(exponent, cost)]
    )
    assert [
        (cost, exponent, coefficient)
        for cost, value in enumerate(velocity, 1)
        for exponent, coefficient in value.items()
        if _grade(exponent, cost) == (0, 0)
    ] == [
        (3, (8, 8), -sp.Rational(1, 14336))
    ]

    logarithm = _projected_magnus(velocity, maximum_order)
    assert logarithm[3][(8, 8)] == -sp.Rational(1, 43008)
    maximum_depth = (maximum_order - 2) // 3
    terminal = _terminal_sequence(logarithm, maximum_depth)
    assert all(coefficient != 0 for coefficient in terminal)

    minus_logarithm = _projected_magnus(
        _scaled_velocity(velocity, -1),
        maximum_order,
    )
    twice_logarithm = _projected_magnus(
        _scaled_velocity(velocity, 2),
        maximum_order,
    )
    terminal_minus = _terminal_sequence(
        minus_logarithm, maximum_depth
    )
    terminal_twice = _terminal_sequence(
        twice_logarithm, maximum_depth
    )

    marker_components = []
    for depth in range(maximum_depth + 1):
        quadratic = sp.factor(
            (terminal[depth] + terminal_minus[depth]) / 2
        )
        linear_plus_cubic = sp.factor(
            (terminal[depth] - terminal_minus[depth]) / 2
        )
        cubic = sp.factor(
            (
                terminal_twice[depth]
                - 2 * linear_plus_cubic
                - 4 * quadratic
            )
            / 6
        )
        linear = sp.factor(linear_plus_cubic - cubic)
        assert sp.factor(
            linear + quadratic + cubic - terminal[depth]
        ) == 0
        marker_components.append(
            (linear, quadratic, cubic)
        )

    first_pair_logarithm = _projected_magnus(
        _pair_velocity(velocity, FIRST_PAIR),
        maximum_order,
    )
    dominant_pair_logarithm = _projected_magnus(
        _pair_velocity(velocity, DOMINANT_PAIR),
        maximum_order,
    )
    first_pair = _terminal_sequence(
        first_pair_logarithm, maximum_depth
    )
    dominant_pair = _terminal_sequence(
        dominant_pair_logarithm, maximum_depth
    )
    dominant_pair_closed = _dominant_pair_closed_sequence(
        maximum_depth
    )
    assert dominant_pair == dominant_pair_closed
    assert all(
        sp.factor(
            marker_components[depth][1]
            - first_pair[depth]
            - dominant_pair[depth]
        ) == 0
        for depth in range(maximum_depth + 1)
    )

    valuation_rows = []
    for depth in range(2, maximum_depth + 1, 2):
        factorial = sp.factorial(depth)
        linear, quadratic, cubic = marker_components[depth]
        assert _p_adic_valuation(factorial * linear, 3) == -2
        assert _p_adic_valuation(factorial * quadratic, 3) == -3
        assert _p_adic_valuation(factorial * cubic, 3) >= -1
        assert _p_adic_valuation(
            factorial * terminal[depth], 3
        ) == -3
        assert _p_adic_valuation(
            factorial * first_pair[depth], 3
        ) > -3
        assert _p_adic_valuation(
            factorial * dominant_pair[depth], 3
        ) == -3
        unit = sp.factor(
            27 * factorial * dominant_pair[depth]
        )
        assert unit == _dominant_pair_even_unit(depth)
        assert _unit_mod_three(unit) == 1
        order = 2 + 3 * depth
        exponent = (
            1 + 7 * depth,
            4 + 5 * depth,
        )
        assert sum(exponent) - 3 == 4 * order - 6
        valuation_rows.append({
            "orbit_depth": depth,
            "logarithmic_order": order,
            "hamiltonian_exponent": list(exponent),
            "normalized_logarithm": str(terminal[depth]),
            "linear_v3": -2,
            "quadratic_v3": -3,
            "cubic_v3": (
                "infinity"
                if cubic == 0
                else _p_adic_valuation(factorial * cubic, 3)
            ),
            "dominant_pair_unit": str(unit),
            "dominant_pair_unit_mod_3": 1,
            "source_derivation_degree": 4 * order - 6,
        })

    return {
        "schema": (
            "axiompack.jacobian_p2q_q2_"
            "rate_four_dichotomy.v1"
        ),
        "low_weight_target_family": (
            "-P^2*Q/168 + alpha*P*Q + beta*Q^2"
        ),
        "cost_two_radial_velocity_coefficient": (
            "-325/2688 + beta/2"
        ),
        "exceptional_beta": str(SPECIAL_Q2_COEFFICIENT),
        "cost_three_radial_velocity": "-u^8*z^8/14336",
        "cost_three_radial_logarithm": "-u^8*z^8/43008",
        "exceptional_connection": {
            "alpha": "0",
            "beta": str(SPECIAL_Q2_COEFFICIENT),
            "source_hamiltonian_perturbation": (
                "-s*P_s^2*Q_s/21 + 325*s*Q_s^2/168"
            ),
            "anisotropic_grade": (
                "(3*a-7*q-3, 3*b-5*q-9)"
            ),
            "unique_zero_grade_generator": (
                "-u^8*z^8/43008 at logarithmic cost 3"
            ),
            "terminal_grade": list(TARGET_GRADE),
            "terminal_orbit": (
                "q=2+3*k, exponent=(1+7*k,4+5*k)"
            ),
            "adjoint_multiplier": "-(2*k-3)/5376",
            "checked_depths": [0, maximum_depth],
            "all_checked_coefficients_nonzero": True,
        },
        "quadratic_grade_pairs": [
            [list(grade) for grade in sorted(FIRST_PAIR)],
            [list(grade) for grade in sorted(DOMINANT_PAIR)],
        ],
        "dominant_pair": [
            list(grade) for grade in sorted(DOMINANT_PAIR)
        ],
        "even_depth_valuation_rows": valuation_rows,
        "all_order_exceptional_rate": 4,
        "non_dominant_three_local_bounds": {
            "linear": "k!*D_k in 3^-2*Z_(3)",
            "first_quadratic_pair": "k!*D_k in 3^-2*Z_(3)",
            "cubic": "k!*D_k in 3^-2*Z_(3)",
        },
        "dominant_pair_closed_form": {
            "bernoulli_convention": "B_1=-1/2",
            "operator": "C(x)=x/(exp(x)-1)",
            "remainder_divided_power_coefficient": (
                "k!*r_k=-(174*k^2-k-164)"
                "/(2016*(k+1)*(3*k+2))"
            ),
            "partial_fraction": (
                "k!*r_k=-29/1008"
                "+43/(336*(3*k+2))+11/(2016*(k+1))"
            ),
            "even_unit": (
                "27*k!*D_k=(387/112)*sum_{j=1}^k"
                " binomial(k,j)*B_(k-j)/(3*j+2)"
                "-(33/224)*B_k"
            ),
            "all_positive_even_depths_mod_3": 1,
        },
        "claim_boundary": (
            "Exact instantaneous A-or-B radial dichotomy on the "
            "low-weight order-one plane, a complete exceptional "
            "right-Magnus replay through order 60, and a closed "
            "dominant-pair Bernoulli response. The 3-local sector "
            "separation proves exact exceptional source and symmetric "
            "rate four. Higher-weight order-one and later target "
            "coefficients remain outside this classification."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
