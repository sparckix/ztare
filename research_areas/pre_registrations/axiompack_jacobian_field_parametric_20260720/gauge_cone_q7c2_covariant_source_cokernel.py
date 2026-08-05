#!/usr/bin/env python3
"""Held-out full projection for the first stable ``Q^7*C^2`` ray.

The fast path constructs the completely normalized covariant rows through
cost four and checks the symbolic terminal and all-order ``phi_3`` orbit.
``--verify-full-projection`` injects those exact rows into the global
source staircase and checks the cost-six velocity and Magnus coefficient
in the anisotropic higher-contact grading.
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

import gauge_cone_higher_contact_cost_four_scan as local  # noqa: E402
from gauge_cone_radial_triangular_staircase import (  # noqa: E402
    run as staircase,
)


LAMBDA = sp.symbols("lambda")
Q_EXPONENT = 7
CONTACT_DEPTH = 2
SLOPE = 25
SOURCE_SLOPES = (24, 26)
TERMINAL_GRADE = (-48, -50)
ZERO_LETTER = -sp.Rational(81, 1048576)
TERMINAL_VELOCITY = sp.Rational(639, 8388608)


def _normalized_covariant_rows() -> tuple[
    local.Target,
    local.Target,
    local.Target,
]:
    pullback = local.NumericSourcePullback()
    background = local._fixed_target_coefficients(1)
    prefix = local._target_shift(
        local._target_power(local.CUSP, CONTACT_DEPTH),
        0,
        Q_EXPONENT,
    )
    first = local._scale(
        local._target_bracket(background[0], prefix),
        -1,
    )
    second = local._scale(
        local._add(
            local._target_bracket(background[0], first),
            local._target_bracket(background[1], prefix),
        ),
        -sp.Rational(1, 2),
    )

    residual = local._row_residual(
        [prefix, first],
        2,
        pullback,
    )
    residual, first, _controls, _snapshots = local._normalize_row(
        residual,
        first,
        CONTACT_DEPTH,
        pullback,
    )
    assert not residual

    residual = local._row_residual(
        [prefix, first, second],
        3,
        pullback,
    )
    residual, second, _controls, _snapshots = local._normalize_row(
        residual,
        second,
        CONTACT_DEPTH,
        pullback,
    )
    assert local._leading_rows(residual) == [{
        "key_r_normal": [25, 5],
        "exponent_u_z": [25, 30],
        "coefficient": str(TERMINAL_VELOCITY),
    }]
    for row in (prefix, first, second):
        assert all(
            p_exponent <= 2 * q_exponent
            and (p_exponent, q_exponent) != (0, 1)
            for (p_exponent, q_exponent), coefficient in row.items()
            if coefficient != 0
        )
    return prefix, first, second


def _adjoint_multiplier(depth: int) -> sp.Expr:
    return sp.factor(
        ZERO_LETTER * (46 * depth - 25)
    )


def _response_coefficient(depth: int) -> sp.Expr:
    if depth == 0:
        return sp.Rational(1, 4)
    return sp.Rational(
        sp.bernoulli(depth + 1),
        2 * factorial(depth + 1),
    )


def _logarithm_coefficient(depth: int) -> sp.Expr:
    orbit = sp.prod(
        _adjoint_multiplier(index)
        for index in range(depth)
    )
    return sp.factor(
        TERMINAL_VELOCITY
        * _response_coefficient(depth)
        * orbit
    )


def _terminal_rows(
    rows: list[list[list[object]]],
    *,
    require_lambda: bool = True,
) -> list[list[object]]:
    return [
        [cost, row]
        for cost, values in enumerate(rows, 1)
        for row in values
        if (
            row[0] == list(TERMINAL_GRADE)
            and (
                not require_lambda
                or "lambda" in str(row[2])
            )
        )
    ]


def _full_projection(
    rows: tuple[local.Target, local.Target, local.Target],
) -> dict[str, object]:
    _prefix, first, second = rows
    multiplier = local._target_shift(
        local._target_power(local.CUSP, CONTACT_DEPTH - 1),
        0,
        Q_EXPONENT,
    )
    delayed = [
        (
            p_exponent,
            q_exponent,
            LAMBDA * coefficient,
        )
        for (p_exponent, q_exponent), coefficient
        in multiplier.items()
    ]
    prescribed = [
        (
            target_order,
            p_exponent,
            q_exponent,
            LAMBDA * coefficient,
        )
        for target_order, row in ((2, first), (3, second))
        for (p_exponent, q_exponent), coefficient in row.items()
    ]
    result = staircase(
        maximum_target_order=5,
        cancel_second_normal=True,
        verify_roundtrips=False,
        compute_logarithms=True,
        normalization_objective="logarithm",
        delayed_c_prefix_terms=delayed,
        prescribed_target_terms=prescribed,
        project_to_prefix_ray=True,
        prefix_terminal_grade_override=TERMINAL_GRADE,
        prefix_slope_override=SOURCE_SLOPES[0],
        prefix_weight_override=23,
        prefix_source_slopes_override=SOURCE_SLOPES,
    )
    projection = result["prefix_candidate_ray_projection"]
    velocity = _terminal_rows(projection["source_velocity"])
    logarithm = _terminal_rows(projection["source_logarithm"])
    assert velocity == [[
        4,
        [
            list(TERMINAL_GRADE),
            [25, 30],
            "639*lambda/8388608",
        ],
    ]]
    assert logarithm == [
        [
            4,
            [
                list(TERMINAL_GRADE),
                [25, 30],
                "639*lambda/33554432",
            ],
        ],
        [
            6,
            [
                list(TERMINAL_GRADE),
                [49, 56],
                (
                    "431325*lambda**2/"
                    "70368744177664"
                ),
            ],
        ],
    ]
    return {
        "verified": True,
        "source_velocity_terminal_rows": velocity,
        "source_logarithm_terminal_rows": logarithm,
        "source_slopes": list(SOURCE_SLOPES),
    }


def run(
    maximum_depth: int = 11,
    verify_full_projection: bool = False,
) -> dict[str, object]:
    if maximum_depth < 9:
        raise ValueError("maximum_depth must be at least nine")
    rows = _normalized_covariant_rows()
    response = []
    for depth in range(maximum_depth + 1):
        coefficient = _logarithm_coefficient(depth)
        if depth >= 1 and depth % 2 == 0:
            assert coefficient == 0
        if depth % 2 == 1:
            assert coefficient != 0
        response.append({
            "depth": depth,
            "cost": 4 + 2 * depth,
            "exponent_u_z": [
                25 + 24 * depth,
                30 + 26 * depth,
            ],
            "coefficient_without_lambda": str(coefficient),
            "lambda_power": depth + 1,
        })
    assert response[0]["coefficient_without_lambda"] == (
        "639/33554432"
    )
    assert response[1]["coefficient_without_lambda"] == (
        "431325/70368744177664"
    )

    return {
        "schema": (
            "axiompack.jacobian_cone_q7c2_"
            "covariant_source_cokernel.v1"
        ),
        "prefix": "Q^7*C^2",
        "normalized_covariant_target_row_support_sizes": [
            len(row) for row in rows
        ],
        "target_rows_are_cone_compatible": True,
        "zero_grade_letter": {
            "cost": 2,
            "exponent_u_z": [25, 29],
            "coefficient_without_lambda": str(ZERO_LETTER),
        },
        "terminal_velocity": {
            "cost": 4,
            "exponent_u_z": [25, 30],
            "coefficient_without_lambda": str(
                TERMINAL_VELOCITY
            ),
        },
        "adjoint_multiplier": (
            "-81*(46*k-25)/1048576"
        ),
        "right_magnus_response": (
            "phi_3(x)=x/(exp(x)-1)*integral_0^1 "
            "t^3*exp(t^2*x)dt"
        ),
        "response_rows": response,
        "nonzero_subsequence": "every odd adjoint depth",
        "limiting_source_hamiltonian_rate": 25,
        "full_projection": (
            _full_projection(rows)
            if verify_full_projection
            else {
                "verified": False,
                "replay_flag": "--verify-full-projection",
            }
        ),
        "claim_boundary": (
            "Held-out stable higher-contact monomial and its "
            "leading-amplitude orbit. The global affine theorem uses "
            "the separate D-adic transfer and contact-valuation "
            "certificates."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--maximum-depth", type=int, default=11)
    parser.add_argument(
        "--verify-full-projection",
        action="store_true",
    )
    arguments = parser.parse_args()
    print(json.dumps(
        run(
            arguments.maximum_depth,
            arguments.verify_full_projection,
        ),
        indent=2,
        sort_keys=True,
    ))
