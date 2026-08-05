#!/usr/bin/env python3
"""Uniform mixed-residue response modulo ``4*P^3+27*Q^2``.

The two non-pure residue classes are represented by ``P*Q^b*C`` and
``P^2*Q^b*C``.  A symbolic normal-layer quotient derives their
cost-three transfer coefficients.  Their terminal logarithms then follow
the same nonpolynomial ``phi_2`` response.
"""

from __future__ import annotations

from math import factorial
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gauge_cone_qbc_uniform_cost_four as quotient  # noqa: E402


def _phi_two_coefficient(depth: int) -> sp.Expr:
    """Coefficient of x^depth in x/(e^x-1)*integral t^2*e^(t^2*x)."""

    return sp.factor(sum(
        # The dexp convention uses the first Bernoulli number
        # B_1=-1/2.  SymPy's one-argument form returns the alternate
        # convention, while the Bernoulli-polynomial value at zero has
        # the required sign.
        sp.bernoulli(depth - power, 0)
        / (
            factorial(depth - power)
            * factorial(power)
            * (2 * power + 3)
        )
        for power in range(depth + 1)
    ))


def _symbolic_transfer() -> dict[int, sp.Expr]:
    previous_minimum = quotient.MINIMUM_RADIAL_OFFSET
    previous_normal = quotient.MAXIMUM_NORMAL_ORDER
    quotient.MINIMUM_RADIAL_OFFSET = 1
    quotient.MAXIMUM_NORMAL_ORDER = 4
    try:
        pullback = quotient.SourcePullback()
        result = {}
        for p_exponent, terminal_key in (
            (1, (1, 4)),
            (2, (3, 4)),
        ):
            prefix = quotient._c_multiple(p_exponent, 0)
            residual = quotient._row_residual(
                [prefix],
                2,
                pullback,
            )
            residual, _controls = quotient._normalize_row(
                residual,
                {},
                pullback,
            )
            result[p_exponent] = sp.factor(
                residual[terminal_key] / 3
            )
    finally:
        quotient.MINIMUM_RADIAL_OFFSET = previous_minimum
        quotient.MAXIMUM_NORMAL_ORDER = previous_normal
    assert result == {
        1: -sp.Rational(9, 128) * quotient.B,
        2: sp.Rational(27, 512) * quotient.B,
    }
    return result


def _zero_grade_coefficient(
    p_exponent: int,
    q_exponent: int,
) -> sp.Rational:
    return sp.Rational(
        (-1) ** (p_exponent + q_exponent + 1)
        * 9
        * 3**p_exponent,
        2 ** (2 * p_exponent + 2 * q_exponent + 2),
    )


def _logarithmic_seed(
    p_exponent: int,
    q_exponent: int,
) -> sp.Rational:
    if p_exponent == 1:
        return sp.Rational(
            (-1) ** (q_exponent + 1)
            * 9
            * q_exponent,
            2 ** (2 * q_exponent + 7),
        )
    if p_exponent == 2:
        return sp.Rational(
            (-1) ** q_exponent
            * 27
            * q_exponent,
            2 ** (2 * q_exponent + 9),
        )
    raise ValueError("only the two mixed residues are supported")


def _orbit_multiplier(
    p_exponent: int,
    q_exponent: int,
    depth: int,
) -> sp.Expr:
    zero_grade = _zero_grade_coefficient(
        p_exponent,
        q_exponent,
    )
    if p_exponent == 1:
        monomial_multiplier = 2 * (
            3 * (q_exponent + 1) * depth
            - (3 * q_exponent + 7)
        )
    elif p_exponent == 2:
        monomial_multiplier = 2 * (
            (3 * q_exponent + 5) * depth
            - 3 * (q_exponent + 3)
        )
    else:
        raise ValueError("only the two mixed residues are supported")
    return sp.factor(zero_grade * monomial_multiplier)


def _terminal_coefficient(
    p_exponent: int,
    q_exponent: int,
    depth: int,
) -> sp.Expr:
    velocity_seed = 3 * _logarithmic_seed(
        p_exponent,
        q_exponent,
    )
    orbit = sp.prod(
        _orbit_multiplier(
            p_exponent,
            q_exponent,
            index,
        )
        for index in range(depth)
    )
    return sp.factor(
        velocity_seed
        * _phi_two_coefficient(depth)
        * orbit
    )


def _terminal_exponent(
    p_exponent: int,
    q_exponent: int,
    depth: int,
) -> tuple[int, int]:
    slope = 2 * p_exponent + 3 * q_exponent + 1
    if p_exponent == 1:
        seed = (3 * q_exponent + 1, 3 * q_exponent + 5)
    elif p_exponent == 2:
        seed = (3 * q_exponent + 3, 3 * q_exponent + 7)
    else:
        raise ValueError("only the two mixed residues are supported")
    return (
        seed[0] + slope * depth,
        seed[1] + slope * depth,
    )


def run(maximum_depth: int = 10) -> dict[str, object]:
    if maximum_depth < 3:
        raise ValueError("at least four response rows are required")
    symbolic_transfer = _symbolic_transfer()
    assert [
        _phi_two_coefficient(depth)
        for depth in range(3)
    ] == [
        sp.Rational(1, 3),
        sp.Rational(1, 30),
        -sp.Rational(1, 1260),
    ]

    representatives = []
    expected = {
        (1, 4, 1): sp.Rational(4617, 167772160),
        (1, 4, 2): sp.Rational(41553, 1202590842880),
        (2, 3, 1): sp.Rational(59049, 335544320),
        (2, 3, 2): sp.Rational(1594323, 2405181685760),
    }
    for p_exponent, q_exponent in ((1, 4), (2, 3)):
        rows = []
        for depth in range(maximum_depth + 1):
            coefficient = _terminal_coefficient(
                p_exponent,
                q_exponent,
                depth,
            )
            if (p_exponent, q_exponent, depth) in expected:
                assert (
                    coefficient
                    == expected[(p_exponent, q_exponent, depth)]
                )
            rows.append({
                "depth": depth,
                "cost": 3 + 2 * depth,
                "exponent": list(_terminal_exponent(
                    p_exponent,
                    q_exponent,
                    depth,
                )),
                "coefficient": str(coefficient),
            })
        representatives.append({
            "p_exponent": p_exponent,
            "q_exponent": q_exponent,
            "slope": (
                2 * p_exponent + 3 * q_exponent + 1
            ),
            "rows": rows,
        })

    # A zero multiplier would require an integer strictly between one
    # and two to equal the bracket depth.
    assert all(
        1
        < sp.Rational(3 * q_exponent + 7, 3 * (q_exponent + 1))
        < 2
        for q_exponent in range(4, 40)
    )
    assert all(
        1
        < sp.Rational(3 * (q_exponent + 3), 3 * q_exponent + 5)
        < 2
        for q_exponent in range(3, 40)
    )

    return {
        "schema": (
            "axiompack.jacobian_cone_mixed_residue_phi2.v1"
        ),
        "fixed_weight_discriminant": "D=4*P^3+27*Q^2",
        "residue_classes_modulo_D": ["Q^b", "P*Q^b", "P^2*Q^b"],
        "symbolic_cost_three_transfer_after_factoring_(-1/4)^b": {
            "P*Q^b*C": str(symbolic_transfer[1]),
            "P^2*Q^b*C": str(symbolic_transfer[2]),
        },
        "restored_cost_three_logarithm": {
            "P*Q^b*C_b>=4": (
                "(-1)^(b+1)*9*b/2^(2*b+7)"
            ),
            "P^2*Q^b*C_b>=3": (
                "(-1)^b*27*b/2^(2*b+9)"
            ),
        },
        "right_magnus_response": {
            "function": (
                "x/(exp(x)-1) * integral_0^1 "
                "t^2*exp(t^2*x) dt"
            ),
            "first_coefficients": ["1/3", "1/30", "-1/1260"],
            "nonpolynomial_certificate": (
                "At x=2*pi*i, I_2=(1-I_0)/(4*pi*i) "
                "and Re(I_0)<1 because cos(2*pi*t^2)<1 "
                "on a set of positive measure."
            ),
        },
        "adjoint_multiplier_nonzero_for_all_integral_depths": True,
        "representative_rows": representatives,
        "claim_boundary": (
            "All-order terminal response for P*Q^b*C with b>=4 "
            "and P^2*Q^b*C with b>=3, modulo the fixed-weight "
            "discriminant D. The low P*Q^2*C and P*Q^3*C cases "
            "and positive D-adic depth are excluded."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
