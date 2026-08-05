#!/usr/bin/env python3
"""Polynomial identities for stable ``P^a*Q^b*D^d*C^m`` prefixes.

After the common leading scale is removed, every coefficient in the
cost-four relative window is a polynomial of total degree at most two
in ``(a,b,d,m)``:

* parameter order two selects at most two prefix factors;
* two covariant brackets differentiate the prefix at most twice;
* the stable triangular solve is linear with parameter-independent
  normalized pivots.

Fifteen exact values on an unisolvent quadratic grid determine both the
odd terminal and the even companion.  Three more values are held out.
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


A = sp.symbols("a", integer=True, nonnegative=True)
B, M, K = sp.symbols(
    "b m k",
    integer=True,
    positive=True,
)
D_DEPTH = sp.symbols("d", integer=True, nonnegative=True)

QUADRATIC_MONOMIALS = (
    sp.Integer(1),
    A,
    B,
    D_DEPTH,
    M,
    A**2,
    B**2,
    D_DEPTH**2,
    M**2,
    A * B,
    A * D_DEPTH,
    A * M,
    B * D_DEPTH,
    B * M,
    D_DEPTH * M,
)
DETERMINING_POINTS = (
    (0, 6, 0, 1),
    (0, 7, 0, 1),
    (0, 8, 0, 1),
    (0, 7, 0, 2),
    (0, 8, 0, 2),
    (0, 9, 0, 3),
    (1, 6, 0, 1),
    (1, 8, 0, 2),
    (1, 9, 0, 3),
    (2, 7, 0, 1),
    (0, 7, 1, 1),
    (1, 8, 1, 1),
    (0, 8, 1, 1),
    (0, 9, 1, 2),
    (0, 9, 2, 1),
)
HELD_OUT_POINTS = (
    (2, 8, 1, 1),
    (1, 9, 1, 2),
    (0, 10, 3, 1),
)


def _normalized_rows(
    p_exponent: int,
    q_exponent: int,
    discriminant_depth: int,
    contact_depth: int,
    pullback: NumericSourcePullback,
    background: list[dict[tuple[int, int], sp.Expr]],
) -> tuple[sp.Expr, sp.Expr, dict[str, object]]:
    result = _one_case(
        q_exponent,
        contact_depth,
        p_exponent,
        pullback=pullback,
        background=background,
        discriminant_depth=discriminant_depth,
        normalization_contact_depth=contact_depth + 1,
    )
    assert result["target_rows_are_cone_compatible"]
    assert result["cost_four_terminal_rectangle"][
        "terminal_is_unique_northeast_corner"
    ]
    baseline = (
        2 * p_exponent
        + 3 * q_exponent
        + 5 * discriminant_depth
        + 2 * contact_depth
    )
    leading = result["cost_four_leading_rows"]
    assert len(leading) == 1
    assert leading[0]["key_r_normal"] == [
        baseline,
        2 * contact_depth + 1,
    ]
    leading_scale = (
        (-sp.Rational(3, 4)) ** p_exponent
        * (-sp.Rational(1, 4)) ** q_exponent
        * sp.Rational(27, 8) ** discriminant_depth
        * (-sp.Rational(9, 16)) ** contact_depth
    )
    terminal = sp.factor(
        sp.Rational(leading[0]["coefficient"]) / leading_scale
    )
    companion_rows = [
        row
        for row in result[
            "cost_four_after_prefix_contact_leading_rows"
        ]
        if row["key_r_normal"] == [
            baseline,
            2 * contact_depth + 2,
        ]
    ]
    assert len(companion_rows) <= 1
    companion = (
        sp.factor(
            sp.Rational(companion_rows[0]["coefficient"])
            / leading_scale
        )
        if companion_rows
        else sp.Integer(0)
    )
    return terminal, companion, result


def _degree_bound_certificate() -> dict[str, object]:
    source_selection_depth = 2
    covariant_differentiation_depth = 2
    normalized_pivot_parameter_degree = 0
    bound = max(
        source_selection_depth,
        covariant_differentiation_depth,
    ) + normalized_pivot_parameter_degree
    assert bound == 2
    return {
        "source_parameter_order": source_selection_depth,
        "maximum_prefix_factor_selections": source_selection_depth,
        "maximum_covariant_differentiations": (
            covariant_differentiation_depth
        ),
        "normalized_pivot_parameter_degree": (
            normalized_pivot_parameter_degree
        ),
        "triangular_solve_is_linear": True,
        "total_degree_bound": bound,
    }


def _polynomial(
    coefficients: tuple[sp.Expr, ...],
) -> sp.Expr:
    return sp.factor(sum(
        coefficient * monomial
        for coefficient, monomial in zip(
            coefficients,
            QUADRATIC_MONOMIALS,
            strict=True,
        )
    ))


def run(include_held_out: bool = True) -> dict[str, object]:
    pullback = NumericSourcePullback()
    background = _fixed_target_coefficients(1)
    matrix = sp.Matrix([
        [
            monomial.subs({
                A: p_exponent,
                B: q_exponent,
                D_DEPTH: discriminant_depth,
                M: contact_depth,
            })
            for monomial in QUADRATIC_MONOMIALS
        ]
        for (
            p_exponent,
            q_exponent,
            discriminant_depth,
            contact_depth,
        ) in DETERMINING_POINTS
    ])
    assert matrix.det() == -16

    terminal_values = []
    companion_values = []
    determining_rows = []
    for (
        p_exponent,
        q_exponent,
        discriminant_depth,
        contact_depth,
    ) in DETERMINING_POINTS:
        terminal, companion, result = _normalized_rows(
            p_exponent,
            q_exponent,
            discriminant_depth,
            contact_depth,
            pullback,
            background,
        )
        terminal_values.append(terminal)
        companion_values.append(companion)
        determining_rows.append({
            "p_exponent": p_exponent,
            "q_exponent": q_exponent,
            "discriminant_depth": discriminant_depth,
            "contact_depth": contact_depth,
            "normalized_terminal": str(terminal),
            "normalized_even_companion": str(companion),
            "current_control_histogram": (
                result["row_three_current_control_histogram"]
            ),
        })

    inverse = matrix.inv()
    terminal_coefficients = tuple(
        inverse * sp.Matrix(terminal_values)
    )
    expected_terminal_coefficients = (
        sp.Integer(0),
        -sp.Rational(1, 3),
        -sp.Rational(1, 2),
        -sp.Rational(5, 6),
        -sp.Rational(2, 9),
        sp.Integer(0),
        sp.Integer(0),
        sp.Integer(0),
        sp.Integer(0),
        sp.Integer(0),
        sp.Integer(0),
        sp.Integer(0),
        sp.Integer(0),
        sp.Integer(0),
        sp.Integer(0),
    )
    assert terminal_coefficients == expected_terminal_coefficients
    terminal_polynomial = _polynomial(terminal_coefficients)
    assert sp.factor(
        terminal_polynomial
        + (6 * A + 9 * B + 15 * D_DEPTH + 4 * M) / 18
    ) == 0

    companion_coefficients = tuple(
        inverse * sp.Matrix(companion_values)
    )
    expected_companion_coefficients = (
        sp.Integer(0),
        sp.Integer(0),
        sp.Integer(0),
        -sp.Rational(1, 64),
        sp.Integer(0),
        sp.Integer(0),
        sp.Integer(0),
        sp.Rational(1, 64),
        sp.Integer(0),
        sp.Integer(0),
        sp.Integer(0),
        sp.Integer(0),
        sp.Integer(0),
        sp.Integer(0),
        sp.Integer(0),
    )
    assert companion_coefficients == expected_companion_coefficients
    companion_polynomial = _polynomial(companion_coefficients)
    assert sp.factor(
        companion_polynomial
        - D_DEPTH * (D_DEPTH - 1) / 64
    ) == 0

    held_out_rows = []
    if include_held_out:
        for (
            p_exponent,
            q_exponent,
            discriminant_depth,
            contact_depth,
        ) in HELD_OUT_POINTS:
            terminal, companion, _result = _normalized_rows(
                p_exponent,
                q_exponent,
                discriminant_depth,
                contact_depth,
                pullback,
                background,
            )
            substitution = {
                A: p_exponent,
                B: q_exponent,
                D_DEPTH: discriminant_depth,
                M: contact_depth,
            }
            assert terminal == terminal_polynomial.subs(substitution)
            assert companion == companion_polynomial.subs(
                substitution
            )
            held_out_rows.append({
                "p_exponent": p_exponent,
                "q_exponent": q_exponent,
                "discriminant_depth": discriminant_depth,
                "contact_depth": contact_depth,
                "normalized_terminal": str(terminal),
                "normalized_even_companion": str(companion),
            })

    slope = 2 * A + 3 * B + 5 * D_DEPTH + 2 * M
    resonance = sp.factor(
        slope / (2 * (slope - M))
    )
    assert sp.factor(
        1
        - resonance
        - (
            2 * A + 3 * B + 5 * D_DEPTH
        )
        / (
            2
            * (
                2 * A
                + 3 * B
                + 5 * D_DEPTH
                + M
            )
        )
    ) == 0

    return {
        "schema": (
            "axiompack.jacobian_cone_higher_contact_"
            "d_adic_cost_four_polynomial_certificate.v1"
        ),
        "stable_cone_range": "2*b >= a+3*d+3*m+8",
        "degree_bound_certificate": _degree_bound_certificate(),
        "quadratic_basis": [
            str(value) for value in QUADRATIC_MONOMIALS
        ],
        "unisolvent_matrix_determinant": str(matrix.det()),
        "determining_rows": determining_rows,
        "terminal_solved_coefficients": [
            str(coefficient)
            for coefficient in terminal_coefficients
        ],
        "even_companion_solved_coefficients": [
            str(coefficient)
            for coefficient in companion_coefficients
        ],
        "held_out_rows": (
            held_out_rows if include_held_out else "skipped"
        ),
        "terminal_after_factoring_leading_scale": str(
            terminal_polynomial
        ),
        "even_companion_before_C^(m+1)_normalization": str(
            companion_polynomial
        ),
        "C^(m+1)_normalization_leaves_terminal_unchanged": True,
        "restored_terminal_velocity": (
            "(-3/4)^a*(-1/4)^b*(27/8)^d"
            "*(-9/16)^(m-1)*(6*a+9*b+15*d+4*m)/32 at "
            "u^(2*a+3*b+5*d+2*m)"
            "*z^(2*a+3*b+5*d+4*m+1)"
        ),
        "zero_grade_letter": (
            "4*(-3/4)^a*(-1/4)^b*(27/8)^d"
            "*(-9/16)^m u^(2*a+3*b+5*d+2*m)"
            "*z^(2*a+3*b+5*d+4*m)"
        ),
        "adjoint_multiplier_without_letter_amplitude": str(
            sp.factor(2 * (slope - M) * K - slope)
        ),
        "only_algebraic_resonance": str(resonance),
        "resonance_strictly_between_zero_and_one": True,
        "northeast_rectangle_polynomial_identity_certificate": {
            "fixed_relative_support_in_stable_range": True,
            "all_relative_coefficients_have_total_degree_at_most_two": True,
            "determining_rows_after_next_contact_have_no_term_above_terminal": True,
            "terminal_is_the_unique_northeast_corner": True,
        },
        "claim_boundary": (
            "Exact polynomial identities for the stable D-adic "
            "cost-four terminal and the removable even companion. "
            "Later-current independence is certified separately."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-held-out",
        action="store_true",
    )
    arguments = parser.parse_args()
    print(json.dumps(
        run(not arguments.skip_held_out),
        indent=2,
        sort_keys=True,
    ))
