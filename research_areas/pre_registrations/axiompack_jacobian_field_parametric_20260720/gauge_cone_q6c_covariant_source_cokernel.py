#!/usr/bin/env python3
"""Covariant source-cokernel response of the delayed ``Q^6*C`` prefix.

The target observable is transported through every cone-valued covariant
coefficient.  Its first three coefficients show that the target runway
ends at depth three.  The completed source replay nevertheless retains a
terminal cost-four input.  In the resulting leading-amplitude quotient,
the cost-two zero-grade letter generates an odd Bernoulli ray.

The default replay is fast.  ``--verify-full-projection`` additionally
runs the full logarithm-first radial/one-C staircase through cost six.
"""

from __future__ import annotations

import argparse
from math import factorial
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


P, Q, S = sp.symbols("P Q s")
LAMBDA = sp.symbols("lambda")
CUSP_KERNEL = (
    4 * P**3
    - P**2
    - 18 * P * Q
    + 27 * Q**2
    + 4 * Q
)
ZERO_GRADE_COEFFICIENT = -sp.Rational(9, 16384)
TERMINAL_VELOCITY_COEFFICIENT = sp.Rational(29, 65536)
TERMINAL_GRADE = (-38, -36)


def _target_bracket(left: sp.Expr, right: sp.Expr) -> sp.Expr:
    return sp.expand(
        sp.diff(left, Q) * sp.diff(right, P)
        - sp.diff(left, P) * sp.diff(right, Q)
    )


def _target_background_coefficients(
    maximum_order: int,
) -> list[sp.Expr]:
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
        sp.expand(series.coeff(S, order))
        for order in range(maximum_order + 1)
    ]


def _covariant_prefixes(maximum_depth: int) -> list[sp.Expr]:
    background = _target_background_coefficients(maximum_depth)
    prefixes = [sp.expand(Q**6 * CUSP_KERNEL)]
    for depth in range(maximum_depth):
        coefficient = -sum(
            (
                _target_bracket(
                    background[index],
                    prefixes[depth - index],
                )
                for index in range(depth + 1)
            ),
            sp.Integer(0),
        ) / (depth + 1)
        prefixes.append(sp.expand(coefficient))
    return prefixes


def _outside_cone(
    value: sp.Expr,
) -> dict[tuple[int, int], sp.Expr]:
    return {
        exponent: coefficient
        for exponent, coefficient in sp.Poly(value, P, Q).terms()
        if (
            coefficient != 0
            and (
                exponent[1] == 0
                or exponent[0] > 2 * exponent[1]
                or exponent == (0, 1)
            )
        )
    }


def _adjoint_multiplier(depth: int) -> sp.Rational:
    """Multiplier in ``[A,E_depth] = alpha_depth*E_(depth+1)``."""

    return sp.Rational(9 * (10 - 19 * depth), 8192)


def _response_coefficient(depth: int) -> sp.Expr:
    """Coefficient of ``x^depth`` in the cost-four response ``phi_3``."""

    if depth == 0:
        return sp.Rational(1, 4)
    return sp.Rational(
        sp.bernoulli(depth + 1),
        2 * factorial(depth + 1),
    )


def _terminal_coefficient(depth: int) -> sp.Expr:
    orbit = sp.Integer(1)
    for earlier_depth in range(depth):
        orbit *= _adjoint_multiplier(earlier_depth)
    return sp.factor(
        TERMINAL_VELOCITY_COEFFICIENT
        * _response_coefficient(depth)
        * orbit
    )


def _prescribed_terms(
    prefixes: list[sp.Expr],
) -> list[tuple[int, int, int, sp.Expr]]:
    result = []
    for target_order, value in ((2, prefixes[1]), (3, prefixes[2])):
        for (
            p_exponent,
            q_exponent,
        ), coefficient in sp.Poly(value, P, Q).terms():
            result.append((
                target_order,
                p_exponent,
                q_exponent,
                LAMBDA * coefficient,
            ))
    return result


def _terminal_rows(
    rows: list[list[list[object]]],
    cost: int,
) -> list[list[object]]:
    return [
        row
        for row in rows[cost - 1]
        if row[0] == list(TERMINAL_GRADE)
    ]


def _full_projection_witness(
    prefixes: list[sp.Expr],
) -> dict[str, object]:
    from gauge_cone_radial_triangular_staircase import run as staircase

    result = staircase(
        maximum_target_order=5,
        cancel_second_normal=True,
        verify_roundtrips=False,
        compute_logarithms=True,
        normalization_objective="logarithm",
        delayed_c_prefix_terms=[(0, 6, LAMBDA)],
        prescribed_target_terms=_prescribed_terms(prefixes),
        project_to_prefix_ray=True,
        prefix_terminal_grade_override=TERMINAL_GRADE,
    )
    projection = result["prefix_candidate_ray_projection"]
    velocity_cost_four = _terminal_rows(
        projection["source_velocity"], 4
    )
    velocity_cost_six = _terminal_rows(
        projection["source_velocity"], 6
    )
    logarithm_cost_four = _terminal_rows(
        projection["source_logarithm"], 4
    )
    logarithm_cost_six = _terminal_rows(
        projection["source_logarithm"], 6
    )
    assert velocity_cost_four == [[
        list(TERMINAL_GRADE),
        [20, 23],
        "29*lambda/65536",
    ]]
    assert velocity_cost_six == []
    assert logarithm_cost_four == [[
        list(TERMINAL_GRADE),
        [20, 23],
        "29*lambda/262144",
    ]]
    assert logarithm_cost_six == [[
        list(TERMINAL_GRADE),
        [39, 42],
        "435*lambda**2/2147483648",
    ]]
    return {
        "verified": True,
        "source_velocity_cost_four": velocity_cost_four,
        "source_velocity_cost_six": velocity_cost_six,
        "source_logarithm_cost_four": logarithm_cost_four,
        "source_logarithm_cost_six": logarithm_cost_six,
    }


def run(
    maximum_depth: int = 12,
    verify_full_projection: bool = False,
) -> dict[str, object]:
    if maximum_depth < 7:
        raise ValueError("at least eight response rows are required")

    prefixes = _covariant_prefixes(3)
    outside = [_outside_cone(value) for value in prefixes]
    assert not outside[0]
    assert not outside[1]
    assert not outside[2]
    assert outside[3] == {
        (9, 3): -sp.Rational(5, 108),
        (8, 3): sp.Rational(5, 432),
    }
    assert [
        len(sp.Poly(value, P, Q).terms())
        for value in prefixes
    ] == [5, 7, 12, 16]

    expected = {
        0: sp.Rational(29, 262144),
        1: sp.Rational(435, 2147483648),
        2: sp.Integer(0),
        3: -sp.Rational(
            147987,
            144115188075855872,
        ),
        5: sp.Rational(
            885321657,
            9671406556917033397649408,
        ),
    }
    for depth, coefficient in expected.items():
        assert _terminal_coefficient(depth) == coefficient
    assert all(
        _terminal_coefficient(depth) != 0
        for depth in range(1, maximum_depth + 1, 2)
    )
    assert all(
        _terminal_coefficient(depth) == 0
        for depth in range(2, maximum_depth + 1, 2)
    )

    rows = []
    for depth in range(maximum_depth + 1):
        rows.append({
            "depth": depth,
            "cost": 4 + 2 * depth,
            "exponent": [
                20 + 19 * depth,
                23 + 19 * depth,
            ],
            "lambda_power": depth + 1,
            "coefficient_without_lambda": str(
                _terminal_coefficient(depth)
            ),
            "nonzero": _terminal_coefficient(depth) != 0,
        })

    full_projection = (
        _full_projection_witness(prefixes)
        if verify_full_projection
        else {
            "verified": False,
            "replay_flag": "--verify-full-projection",
            "expected_source_velocity_cost_four": (
                "29*lambda*u^20*z^23/65536"
            ),
            "expected_source_velocity_cost_six": "0",
            "expected_source_logarithm_cost_six": (
                "435*lambda^2*u^39*z^42/2147483648"
            ),
        }
    )

    return {
        "schema": (
            "axiompack.jacobian_cone_q6c_"
            "covariant_source_cokernel.v1"
        ),
        "target_prefix": "Q^6*C",
        "target_background": {
            "P^3_coefficient": (
                "96*(s^2-12*s+16)/"
                "((s-6)^3*(s-4)^2*(s+4)^2)"
            ),
            "P*Q_coefficient": "2*s/((s-4)*(s+4))",
            "Q^2_coefficient": "-1/4",
        },
        "covariant_equation": "G' + {K,G} = 0",
        "covariant_support_sizes_depths_0_to_3": [
            len(sp.Poly(value, P, Q).terms())
            for value in prefixes
        ],
        "cone_membership_depths_0_to_3": [
            not value for value in outside
        ],
        "first_target_exit": {
            "depth": 3,
            "outside_coefficients": {
                f"{exponent[0]},{exponent[1]}": str(coefficient)
                for exponent, coefficient in outside[3].items()
            },
        },
        "source_grading": "(2*a-19*cost-2,2*b-19*cost-6)",
        "terminal_grade": list(TERMINAL_GRADE),
        "zero_grade_logarithm": {
            "cost": 2,
            "exponent": [20, 22],
            "coefficient_without_lambda": str(
                ZERO_GRADE_COEFFICIENT
            ),
        },
        "terminal_velocity_seed": {
            "cost": 4,
            "exponent": [20, 23],
            "coefficient_without_lambda": str(
                TERMINAL_VELOCITY_COEFFICIENT
            ),
        },
        "adjoint_multiplier": "9*(10-19*k)/8192",
        "right_magnus_response": {
            "function": (
                "x/(exp(x)-1) * integral_0^1 "
                "t^3*exp(t^2*x) dt"
            ),
            "constant": "1/4",
            "positive_depth_coefficient": (
                "B_(k+1)/(2*(k+1)!)"
            ),
        },
        "maximum_checked_response_depth": maximum_depth,
        "response_rows": rows,
        "all_order_nonzero_subsequence": "odd depths k=2*m+1",
        "limiting_spatial_rate": "19",
        "full_projected_replay": full_projection,
        "claim_boundary": (
            "All-order leading-amplitude terminal quotient generated "
            "by the covariantly completed Q^6*C prefix. The full "
            "staircase is checked through cost six. This does not "
            "classify arbitrary pure-Q exponents, mixed one-C "
            "prefixes, or higher powers of C."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--maximum-depth",
        type=int,
        default=12,
    )
    parser.add_argument(
        "--verify-full-projection",
        action="store_true",
    )
    arguments = parser.parse_args()
    print(json.dumps(
        run(
            maximum_depth=arguments.maximum_depth,
            verify_full_projection=arguments.verify_full_projection,
        ),
        indent=2,
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
