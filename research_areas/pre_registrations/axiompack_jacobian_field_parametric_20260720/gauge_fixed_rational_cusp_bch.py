#!/usr/bin/env python3
"""Exact fixed-rational cusp-stabilizer BCH probe.

The calculation is deliberately a prefix discriminator.  It checks a
rational amplitude at which the second Hamiltonian degenerates to a single
monomial and records the maximal ordinary-degree coefficient of every BCH
term.  It does not extrapolate nonvanishing beyond ``depth``.
"""

from __future__ import annotations

import json
import sys
from fractions import Fraction
from math import factorial
from pathlib import Path

import sympy as sp


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from ztare.common.formal_lie_series import (  # noqa: E402
    FormalLieOps,
    VelocityPlacement,
    magnus_from_velocity,
)


def _bracket(
    first: sp.Expr,
    second: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> sp.Expr:
    """Hamiltonian bracket with ``[X_f,X_g]=X_[f,g]``."""

    return sp.expand(
        sp.diff(first, q) * sp.diff(second, p)
        - sp.diff(first, p) * sp.diff(second, q)
    )


def _top_term(
    value: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> tuple[tuple[int, int], sp.Rational]:
    polynomial = sp.Poly(value, p, q)
    degree = polynomial.total_degree()
    terms = [
        (monomial, coefficient)
        for monomial, coefficient in polynomial.terms()
        if sum(monomial) == degree
    ]
    assert len(terms) == 1
    monomial, coefficient = terms[0]
    return monomial, sp.Rational(coefficient)


def run(depth: int = 20) -> dict[str, object]:
    if depth < 2:
        raise ValueError("depth must be at least two")

    p, q = sp.symbols("P Q")
    cusp = 4 * p**3 + 27 * q**2
    normal = -(p**3 + 9 * q**2) / 36

    # This rational specialization removes the cubic part of C + mu*B.
    amplitude = sp.Integer(144)
    specialized = sp.expand(cusp + amplitude * normal)
    assert specialized == -9 * q**2

    operations = FormalLieOps[sp.Expr](
        zero=lambda: sp.Integer(0),
        add=lambda left, right: sp.expand(left + right),
        scale=lambda value, scalar: sp.expand(
            value
            * sp.Rational(scalar.numerator, scalar.denominator)
        ),
        bracket=lambda left, right: _bracket(left, right, p, q),
    )

    # For g(t)=exp(-t X_C) exp(t X_(C+mu B)),
    #
    #   g' g^-1 = mu exp(-t ad_C) B.
    #
    # Feeding this exact left velocity to the shared inverse-dexp recursion
    # computes the BCH logarithm without a separate word enumerator.
    velocity: list[sp.Expr] = []
    iterate = normal
    for index in range(depth):
        velocity.append(
            sp.expand(
                amplitude
                * (-1) ** index
                * iterate
                / factorial(index)
            )
        )
        iterate = _bracket(cusp, iterate, p, q)

    logarithm = magnus_from_velocity(
        velocity=velocity,
        maximum_order=depth,
        ops=operations,
        placement=VelocityPlacement.LEFT_MULTIPLY,
    )

    rows: list[dict[str, object]] = []
    top_coefficients: dict[int, sp.Rational] = {}
    for order in range(1, depth + 1):
        monomial, coefficient = _top_term(
            logarithm[order], p, q
        )
        expected_monomial = (
            ((order + 5) // 2, 0)
            if order % 2 == 1
            else ((order + 2) // 2, 1)
        )
        assert monomial == expected_monomial
        assert coefficient < 0
        top_coefficients[order] = coefficient
        rows.append({
            "order": order,
            "monomial": {
                "P": monomial[0],
                "Q": monomial[1],
            },
            "ordinary_hamiltonian_degree": sum(monomial),
            "coefficient": str(coefficient),
            "negative": True,
        })

    adjacent_ratios: list[dict[str, object]] = []
    for half_order in range(1, depth // 2 + 1):
        odd = 2 * half_order - 1
        even = 2 * half_order
        ratio = sp.factor(
            top_coefficients[even] / top_coefficients[odd]
        )
        expected = 9 * (half_order + 2)
        assert ratio == expected
        adjacent_ratios.append({
            "odd_order": odd,
            "even_order": even,
            "ratio": str(ratio),
        })

    return {
        "schema": "axiompack.jacobian_fixed_rational_cusp_bch.v1",
        "amplitude": str(amplitude),
        "specialized_second_hamiltonian": str(specialized),
        "velocity_equation": (
            "g' * g^-1 = mu * exp(-t ad_C)(B)"
        ),
        "checked_through_order": depth,
        "all_checked_top_coefficients_negative": True,
        "top_degree_rule": "floor((n+5)/2)",
        "adjacent_ratio_rule_checked": (
            "a_(2k) / a_(2k-1) = 9*(k+2)"
        ),
        "rows": rows,
        "adjacent_ratios": adjacent_ratios,
        "claim_boundary": (
            "Exact fixed-rational prefix evidence only. An all-order "
            "nonvanishing argument for the odd subsequence is still needed."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
