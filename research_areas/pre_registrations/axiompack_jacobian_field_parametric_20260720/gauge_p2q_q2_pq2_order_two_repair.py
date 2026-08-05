#!/usr/bin/env python3
"""Exact order-two ``P*Q^2`` cone repair and its Newton quotient."""

from __future__ import annotations

from fractions import Fraction
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

from gauge_controlled_global_magnus_hamiltonian import (  # noqa: E402
    SparseHamiltonian,
    _add,
    _bracket,
    _scale,
    _source_velocity,
)
from gauge_p2q_source_newton_modules import _to_sparse  # noqa: E402
from gauge_regular_singular_connection import (  # noqa: E402
    source_only_connection,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    VelocityPlacement,
    forward_dexp_coefficients,
    inverse_dexp_coefficients,
)


MAXIMUM_INPUT_COST = 6
MINIMUM_NEWTON_GRADE = -12
TERMINAL_INITIAL = sp.Rational(
    18769, 202035261603840
)


def _newton_grade(
    exponent: tuple[int, int],
    cost: int,
) -> int:
    """Twice the slope-7/2 Hamiltonian excess."""
    return 2 * sum(exponent) - 7 * cost - 8


def _project(
    value: SparseHamiltonian,
    cost: int,
) -> SparseHamiltonian:
    return {
        exponent: coefficient
        for exponent, coefficient in value.items()
        if _newton_grade(exponent, cost) >= MINIMUM_NEWTON_GRADE
    }


def _series_bracket(
    left: list[SparseHamiltonian],
    right: list[SparseHamiltonian],
    maximum_order: int,
) -> list[SparseHamiltonian]:
    result = [{} for _ in range(maximum_order + 1)]
    for left_order, left_value in enumerate(
        left[: maximum_order + 1]
    ):
        if not left_value:
            continue
        for right_order, right_value in enumerate(
            right[: maximum_order + 1 - left_order]
        ):
            if not right_value:
                continue
            order = left_order + right_order
            result[order] = _add(
                result[order],
                _project(
                    _bracket(left_value, right_value, 2),
                    order + 1,
                ),
            )
    return result


def _magnus(
    velocity: list[SparseHamiltonian],
    maximum_order: int,
) -> list[SparseHamiltonian]:
    padded_velocity = [
        _project(value, order + 1)
        for order, value in enumerate(velocity)
    ] + [
        {} for _ in range(maximum_order - len(velocity))
    ]
    logarithm = [
        {} for _ in range(maximum_order + 1)
    ]
    inverse = inverse_dexp_coefficients(
        maximum_order,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    for derivative_order in range(maximum_order):
        result = padded_velocity[derivative_order]
        nested = padded_velocity[: derivative_order + 1]
        prefix = logarithm[: derivative_order + 1]
        for depth in range(1, derivative_order + 1):
            nested = _series_bracket(
                prefix, nested, derivative_order
            )
            if inverse[depth]:
                result = _add(
                    result,
                    _scale(
                        nested[derivative_order],
                        inverse[depth],
                    ),
                )
        logarithm[derivative_order + 1] = _scale(
            result,
            Fraction(1, derivative_order + 1),
        )
    return logarithm


def _velocity_from_magnus(
    logarithm: list[SparseHamiltonian],
    maximum_order: int,
) -> list[SparseHamiltonian]:
    derivative = [
        _scale(
            logarithm[order + 1],
            Fraction(order + 1),
        )
        for order in range(maximum_order)
    ] + [{}]
    result = list(derivative)
    nested = derivative
    forward = forward_dexp_coefficients(
        maximum_order,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    for depth in range(1, maximum_order + 1):
        nested = _series_bracket(
            logarithm, nested, maximum_order
        )
        for order in range(maximum_order):
            if forward[depth]:
                result[order] = _add(
                    result[order],
                    _scale(nested[order], forward[depth]),
                )
    return result


def _connection_velocity(
    maximum_input_cost: int = MAXIMUM_INPUT_COST,
    include_order_three_q3: bool = False,
) -> tuple[
    list[SparseHamiltonian],
    dict[str, int],
]:
    data = source_only_connection()
    base_velocity, (_s, v, z), _p3, _pq = _source_velocity(
        maximum_input_cost,
        data,
    )
    s, family_v, family_t, _unused = data["symbols"]
    family_p, family_q = data["family"]
    u = sp.symbols("u")
    substitution = {
        family_v: u - 1,
        family_t: (z - 2 + 3 * (u - 1)) / 2,
    }
    p = sp.factor(family_p.subs(substitution))
    q = sp.factor(family_q.subs(substitution))
    perturbation = sp.series(
        -s * p**2 * q / 21
        + sp.Rational(325, 168) * s * q**2
        - s**2 * p * q**2 / 672,
        s,
        0,
        maximum_input_cost,
    ).removeO().expand()
    if include_order_three_q3:
        perturbation = sp.expand(
            perturbation
            + sp.series(
                sp.Rational(137, 16128) * s**3 * q**3,
                s,
                0,
                maximum_input_cost,
            ).removeO()
        )

    velocity = []
    for order, base in enumerate(base_velocity):
        base_expression = sum(
            (
                coefficient
                * v**exponent[0]
                * z**exponent[1]
                for exponent, coefficient in base.items()
            ),
            sp.Integer(0),
        ).subs(v, u - 1).expand()
        velocity.append(_to_sparse(
            base_expression
            + perturbation.coeff(s, order),
            u,
            z,
        ))

    uniform_degrees = {}
    for name, expression in (
        ("P", p),
        ("Q", q),
        ("P2Q", p**2 * q),
        ("Q2", q**2),
        ("PQ2", p * q**2),
    ):
        numerator, denominator = sp.together(
            expression
        ).as_numer_denom()
        assert not denominator.has(u, z)
        uniform_degrees[name] = max(
            sum(exponent)
            for exponent, coefficient in sp.Poly(
                numerator, u, z
            ).terms()
            if coefficient != 0
        )
    if include_order_three_q3:
        numerator, denominator = sp.together(q**3).as_numer_denom()
        assert not denominator.has(u, z)
        uniform_degrees["Q3"] = max(
            sum(exponent)
            for exponent, coefficient in sp.Poly(
                numerator, u, z
            ).terms()
            if coefficient != 0
        )
    return velocity, uniform_degrees


def _terminal_sequence(
    logarithm: list[SparseHamiltonian],
    maximum_order: int,
) -> list[sp.Expr]:
    multiplier = sp.Integer(1)
    result = []
    depth = 0
    while (order := 10 + 4 * depth) <= maximum_order:
        exponent = (
            17 + 8 * depth,
            16 + 6 * depth,
        )
        result.append(sp.factor(
            logarithm[order].get(exponent, 0)
            / multiplier
        ))
        multiplier = sp.factor(
            multiplier
            * sp.Rational(137, 458752)
            * (2 * depth + 1)
        )
        depth += 1
    return result


def _bernoulli(order: int) -> sp.Rational:
    if order == 1:
        return -sp.Rational(1, 2)
    return sp.Rational(sp.bernoulli(order))


def _terminal_moment(depth: int) -> sp.Expr:
    return sp.Rational(
        10 * (2 * depth + 9),
        (
            3
            * (depth + 2)
            * (depth + 3)
            * (2 * depth + 5)
        ),
    )


def _terminal_closed_sequence(
    maximum_depth: int,
) -> list[sp.Expr]:
    return [
        sp.factor(
            TERMINAL_INITIAL
            * sum(
                (
                    _bernoulli(index)
                    / sp.factorial(index)
                    * _terminal_moment(depth - index)
                    / sp.factorial(depth - index)
                )
                for index in range(depth + 1)
            )
        )
        for depth in range(maximum_depth + 1)
    ]


def run(maximum_order: int = 36) -> dict[str, object]:
    if maximum_order < 24:
        raise ValueError("replay needs a held-out tail")
    velocity, uniform_degrees = _connection_velocity()
    degree_profile = [
        max((sum(exponent) for exponent in value), default=None)
        for value in velocity
    ]
    assert degree_profile == [None, 10, 14, 18, 20, 22]
    assert uniform_degrees == {
        "P": 6,
        "Q": 8,
        "P2Q": 20,
        "Q2": 16,
        "PQ2": 22,
    }
    assert (8, 8) not in velocity[2]
    assert [
        (cost, exponent, coefficient)
        for cost, value in enumerate(velocity, 1)
        for exponent, coefficient in value.items()
        if _newton_grade(exponent, cost) == 0
    ] == [
        (4, (9, 9), sp.Rational(137, 1032192))
    ]
    assert all(
        _newton_grade(exponent, cost) <= 0
        for cost, value in enumerate(velocity, 1)
        for exponent in value
    )
    # At costs seven and above the uniform Hamiltonian degree is at most
    # twenty-two, hence the Newton grade is at most -13.
    assert 2 * 22 - 7 * 7 - 8 < MINIMUM_NEWTON_GRADE

    logarithm = _magnus(velocity, maximum_order)
    replay = _velocity_from_magnus(logarithm, maximum_order)
    projected_velocity = [
        _project(
            velocity[order] if order < len(velocity) else {},
            order + 1,
        )
        for order in range(maximum_order)
    ]
    assert replay[:maximum_order] == projected_velocity
    terminal = _terminal_sequence(logarithm, maximum_order)
    assert all(coefficient != 0 for coefficient in terminal)
    terminal_closed = _terminal_closed_sequence(
        len(terminal) - 1
    )
    assert terminal == terminal_closed
    terminal_divided_power = [
        sp.factor(
            sp.factorial(depth)
            * coefficient
            / TERMINAL_INITIAL
        )
        for depth, coefficient in enumerate(terminal)
    ]
    for depth in range(1, len(terminal)):
        assert sp.factor(
            sum(
                sp.binomial(depth, index)
                * terminal_divided_power[index]
                for index in range(depth)
            )
            - depth * _terminal_moment(depth - 1)
        ) == 0

    rows = []
    for order in range(1, maximum_order + 1):
        value = logarithm[order]
        maximum_degree = max(
            (sum(exponent) for exponent in value),
            default=None,
        )
        maximum_grade = max(
            (
                _newton_grade(exponent, order)
                for exponent in value
            ),
            default=None,
        )
        rows.append({
            "logarithmic_order": order,
            "maximum_hamiltonian_degree": maximum_degree,
            "maximum_newton_grade": maximum_grade,
            "top_terms": [
                [list(exponent), str(coefficient)]
                for exponent, coefficient in value.items()
                if (
                    maximum_degree is not None
                    and sum(exponent) == maximum_degree
                )
            ],
        })

    return {
        "schema": (
            "axiompack.jacobian_p2q_q2_pq2_"
            "order_two_repair.v1"
        ),
        "target_connection_additions": [
            "-s*P^2*Q/168",
            "325*s*Q^2/1344",
            "-s^2*P*Q^2/5376",
        ],
        "source_hamiltonian_additions": [
            "-s*P_s^2*Q_s/21",
            "325*s*Q_s^2/168",
            "-s^2*P_s*Q_s^2/672",
        ],
        "instantaneous_degree_profile_costs_1_to_6": degree_profile,
        "uniform_spatial_degrees": uniform_degrees,
        "newton_grade": "2*(a+b)-7*q-8",
        "unique_zero_grade_velocity": {
            "cost": 4,
            "exponent": [9, 9],
            "coefficient": "137/1032192",
        },
        "source_logarithmic_upper_rate": "7/2",
        "terminal_orbit": {
            "newton_grade": MINIMUM_NEWTON_GRADE,
            "logarithmic_order": "10+4*k",
            "hamiltonian_exponent": "(17+8*k,16+6*k)",
            "adjoint_multiplier": "137*(2*k+1)/458752",
            "normalized_coefficients": [
                str(coefficient) for coefficient in terminal
            ],
            "closed_response": {
                "bernoulli_convention": "B_1=-1/2",
                "D_0": str(TERMINAL_INITIAL),
                "moment": (
                    "A_k=10*(2*k+9)"
                    "/(3*(k+2)*(k+3)*(2*k+5))"
                ),
                "generating_function": (
                    "D(x)=D_0*x/(exp(x)-1)"
                    "*integral_0^1 w(t)*exp(x*t) dt"
                ),
                "weight": (
                    "w(t)=10*t^2+50*t/3-80*t^(3/2)/3"
                ),
                "divided_power_recurrence": (
                    "sum_{j=0}^{k-1} binomial(k,j)*U_j"
                    "=k*A_(k-1)"
                ),
                "even_sign": "sign(U_(2*m))=(-1)^m",
            },
            "all_checked_nonzero": True,
            "source_derivation_degree": "7*n/2-5",
        },
        "exact_source_logarithmic_rate": "7/2",
        "forward_dexp_roundtrip": True,
        "logarithmic_rows": rows,
        "claim_boundary": (
            "Exact cone-compatible order-two radial cancellation, "
            "complete source Newton upper bound 7/2, a closed "
            "terminal Bernoulli-moment response, and all-order "
            "even-depth noncancellation. This classifies one "
            "three-coefficient staircase prefix, not the unrestricted "
            "later-coefficient minimax."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
