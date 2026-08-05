#!/usr/bin/env python3
"""Stable cost-four identity for ``P^a*Q^b*D^d*C^m``.

Here ``D=4*P^3+27*Q^2``.  Its target weight is six, but its first
nonzero fixed-source radial symbol has degree five.  The cost-four
transfer therefore sees ``15*d`` rather than the preregistered
target-weight guess ``18*d``.

The normalized terminal is a polynomial of total degree at most two in
``(a,b,d,m)``: the source coefficient has parameter order two, the two
covariant brackets select at most two factors, and the stable triangular
solve is linear with parameter-independent normalized pivots.  Fifteen
unisolvent exact rows determine that polynomial; held-out rows are not
used in the solve.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_cone_higher_contact_cost_four_scan import (  # noqa: E402
    NumericSourcePullback,
    _fixed_target_coefficients,
    _one_case,
)


A, B, D, M, K = sp.symbols(
    "a b d m k",
    integer=True,
    nonnegative=True,
)
VARIABLES = (A, B, D, M)
QUADRATIC_MONOMIALS = (
    sp.Integer(1),
    *VARIABLES,
    *(
        VARIABLES[left] * VARIABLES[right]
        for left in range(len(VARIABLES))
        for right in range(left, len(VARIABLES))
    ),
)
DETERMINING_POINTS = (
    (0, 6, 0, 1),
    (0, 7, 0, 1),
    (0, 8, 0, 1),
    (1, 6, 0, 1),
    (1, 7, 0, 1),
    (2, 7, 0, 1),
    (0, 7, 1, 1),
    (0, 8, 1, 1),
    (1, 8, 1, 1),
    (0, 9, 2, 1),
    (0, 7, 0, 2),
    (0, 8, 0, 2),
    (1, 8, 0, 2),
    (0, 9, 1, 2),
    (0, 9, 0, 3),
)
HELD_OUT_POINTS = (
    (2, 10, 1, 2),
    (1, 12, 2, 2),
    (0, 13, 2, 3),
)


def _substitution(point: tuple[int, int, int, int]) -> dict[sp.Symbol, int]:
    return dict(zip(VARIABLES, point, strict=True))


def _normalized_terminal(
    point: tuple[int, int, int, int],
    pullback: NumericSourcePullback,
    background: list[dict[tuple[int, int], sp.Expr]],
) -> tuple[sp.Expr, dict[str, object]]:
    a, b, d, m = point
    result = _one_case(
        b,
        m,
        p_exponent=a,
        pullback=pullback,
        background=background,
        discriminant_depth=d,
    )
    assert result["cost_three_residual_vanished"]
    leading = result["cost_four_leading_rows"]
    source_slope = 2 * a + 3 * b + 5 * d + 2 * m
    matching = [
        row
        for row in leading
        if row["key_r_normal"] == [
            source_slope,
            2 * m + 1,
        ]
    ]
    assert len(matching) == 1
    coefficient = sp.Rational(matching[0]["coefficient"])
    leading_scale = (
        (-sp.Rational(3, 4)) ** a
        * (-sp.Rational(1, 4)) ** b
        * (sp.Rational(27, 8)) ** d
        * (-sp.Rational(9, 16)) ** m
    )
    return sp.factor(coefficient / leading_scale), result


def run(include_held_out: bool = True) -> dict[str, object]:
    matrix = sp.Matrix([
        [
            monomial.subs(_substitution(point))
            for monomial in QUADRATIC_MONOMIALS
        ]
        for point in DETERMINING_POINTS
    ])
    assert matrix.det() == -16

    pullback = NumericSourcePullback()
    background = _fixed_target_coefficients(1)
    values = []
    determining_rows = []
    for point in DETERMINING_POINTS:
        value, result = _normalized_terminal(
            point,
            pullback,
            background,
        )
        values.append(value)
        determining_rows.append({
            "point_a_b_d_m": list(point),
            "normalized_terminal": str(value),
            "target_rows_are_cone_compatible": result[
                "target_rows_are_cone_compatible"
            ],
        })

    coefficients = tuple(matrix.inv() * sp.Matrix(values))
    polynomial = sp.factor(sum(
        coefficient * monomial
        for coefficient, monomial in zip(
            coefficients,
            QUADRATIC_MONOMIALS,
            strict=True,
        )
    ))
    expected = -(
        6 * A + 9 * B + 15 * D + 4 * M
    ) / 18
    assert sp.factor(polynomial - expected) == 0
    assert all(
        coefficient == 0
        for coefficient in coefficients[5:]
    )

    held_out_rows = []
    if include_held_out:
        for point in HELD_OUT_POINTS:
            value, result = _normalized_terminal(
                point,
                pullback,
                background,
            )
            assert value == expected.subs(_substitution(point))
            held_out_rows.append({
                "point_a_b_d_m": list(point),
                "normalized_terminal": str(value),
                "target_rows_are_cone_compatible": result[
                    "target_rows_are_cone_compatible"
                ],
            })

    source_slope = 2 * A + 3 * B + 5 * D + 2 * M
    adjoint_multiplier = sp.factor(
        2 * (source_slope - M) * K - source_slope
    )
    resonance = sp.factor(
        source_slope / (2 * (source_slope - M))
    )
    assert sp.factor(
        1 - resonance
        - (2 * A + 3 * B + 5 * D)
        / (
            2
            * (
                2 * A
                + 3 * B
                + 5 * D
                + M
            )
        )
    ) == 0

    return {
        "schema": (
            "axiompack.jacobian_cone_higher_contact_"
            "discriminant_polynomial_certificate.v1"
        ),
        "prefix_family": "P^a*Q^b*D^d*C^m",
        "stable_range": "2*b >= a+3*d+3*m+8",
        "source_radial_slope": str(source_slope),
        "degree_bound_certificate": {
            "source_parameter_order": 2,
            "maximum_factor_selections": 2,
            "maximum_covariant_differentiations": 2,
            "normalized_pivot_parameter_degree": 0,
            "total_degree_bound": 2,
        },
        "quadratic_basis": [
            str(monomial) for monomial in QUADRATIC_MONOMIALS
        ],
        "unisolvent_matrix_determinant": str(matrix.det()),
        "determining_rows": determining_rows,
        "solved_coefficients": [
            str(coefficient) for coefficient in coefficients
        ],
        "held_out_rows": (
            held_out_rows if include_held_out else "skipped"
        ),
        "normalized_terminal": str(polynomial),
        "restored_terminal_velocity": (
            "(-3/4)^a*(-1/4)^b*(27/8)^d*(-9/16)^(m-1)"
            "*(6*a+9*b+15*d+4*m)/32"
        ),
        "terminal_key_r_normal": [
            str(source_slope),
            str(2 * M + 1),
        ],
        "preregistered_target_weight_prediction_18d_falsified": True,
        "correct_discriminant_contribution": "15*d",
        "adjoint_multiplier_without_letter_amplitude": str(
            adjoint_multiplier
        ),
        "only_algebraic_resonance": str(resonance),
        "resonance_strictly_between_zero_and_one": True,
        "claim_boundary": (
            "Stable cost-four polynomial identity for the displayed "
            "D-adic monomial basis. Boundary radial gaps and arbitrary "
            "affine cancellation are handled by the separate current-"
            "support and valuation argument."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-held-out", action="store_true")
    arguments = parser.parse_args()
    print(json.dumps(
        run(not arguments.skip_held_out),
        indent=2,
        sort_keys=True,
    ))
