#!/usr/bin/env python3
"""All-order terminal response for the delayed row-one ``Q^4*C`` prefix.

The first prefix-dependent logarithmic row is canceled exactly at cost
three.  In the deeper grading

    (2*a - 13*cost - 2, 2*b - 13*cost - 6),

the surviving cost-four velocity has terminal grade ``(-26,-24)``.  The
only grade-zero logarithmic letter acts by a nonvanishing monomial
recurrence.  No later instantaneous input occurs in this quotient, so the
right-Magnus response is the standard cost-four function ``phi_3``.
"""

from __future__ import annotations

from math import factorial
import json

import sympy as sp


ZERO_GRADE_COEFFICIENT = -sp.Rational(9, 1024)
TERMINAL_VELOCITY_COEFFICIENT = sp.Rational(5, 1024)
TERMINAL_GRADE = (-26, -24)


def _adjoint_multiplier(depth: int) -> sp.Rational:
    """Multiplier in ``[A,E_depth] = alpha_depth*E_(depth+1)``."""

    return sp.Rational(9 * (7 - 13 * depth), 512)


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


def run(maximum_depth: int = 12) -> dict[str, object]:
    if maximum_depth < 5:
        raise ValueError("at least six response rows are required")
    rows = []
    for depth in range(maximum_depth + 1):
        coefficient = _terminal_coefficient(depth)
        exponent = (
            14 + 13 * depth,
            17 + 13 * depth,
        )
        rows.append({
            "depth": depth,
            "cost": 4 + 2 * depth,
            "exponent": list(exponent),
            "coefficient": str(coefficient),
            "nonzero": coefficient != 0,
        })

    expected = {
        0: sp.Rational(5, 4096),
        1: sp.Rational(105, 4194304),
        2: sp.Integer(0),
        3: -sp.Rational(32319, 2199023255552),
        5: sp.Rational(
            5609655,
            36028797018963968,
        ),
    }
    for depth, coefficient in expected.items():
        assert _terminal_coefficient(depth) == coefficient

    # For odd depth 2*m+1, the Bernoulli index 2*m+2 is positive and even.
    # The orbit multiplier never vanishes because 13*j=7 has no integral
    # solution.  The finite loop checks the executable specialization.
    assert all(
        _terminal_coefficient(depth) != 0
        for depth in range(1, maximum_depth + 1, 2)
    )
    assert all(
        _terminal_coefficient(depth) == 0
        for depth in range(2, maximum_depth + 1, 2)
    )
    response_prefix = [
        _response_coefficient(depth)
        for depth in range(maximum_depth + 1)
    ]
    assert response_prefix[:4] == [
        sp.Rational(1, 4),
        sp.Rational(1, 24),
        sp.Integer(0),
        -sp.Rational(1, 1440),
    ]

    return {
        "schema": (
            "axiompack.jacobian_cone_q4c_"
            "terminal_response.v1"
        ),
        "prefix": "Q^4*C",
        "grading": "(2*a-13*cost-2,2*b-13*cost-6)",
        "terminal_grade": list(TERMINAL_GRADE),
        "zero_grade_logarithm": {
            "cost": 2,
            "exponent": [14, 16],
            "coefficient": str(ZERO_GRADE_COEFFICIENT),
        },
        "terminal_velocity_seed": {
            "cost": 4,
            "exponent": [14, 17],
            "coefficient": str(
                TERMINAL_VELOCITY_COEFFICIENT
            ),
        },
        "cost_three_prefix_component_zero": True,
        "later_terminal_velocity_inputs_zero": True,
        "adjoint_multiplier": "9*(7-13*k)/512",
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
        "maximum_checked_depth": maximum_depth,
        "rows": rows,
        "all_order_nonzero_subsequence": "odd depths k=2*m+1",
        "limiting_spatial_rate": "13",
        "claim_boundary": (
            "All-order leading-amplitude terminal ray for the "
            "single delayed row-one Q^4*C prefix. This does not "
            "classify arbitrary one-C combinations."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
