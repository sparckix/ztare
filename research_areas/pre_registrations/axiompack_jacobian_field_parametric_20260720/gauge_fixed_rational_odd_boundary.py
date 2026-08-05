#!/usr/bin/env python3
"""Symbolic boundary coefficients for the symmetric fixed-rational BCH."""

from __future__ import annotations

import json
from math import factorial
from pathlib import Path
import sys

import sympy as sp


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from ztare.common.formal_lie_series import (  # noqa: E402
    FormalLieOps,
    VelocityPlacement,
    magnus_from_velocity,
)


Shell = tuple[int, int]
Element = dict[Shell, sp.Expr]


def _shell_bracket_coefficient(
    first: Shell,
    second: Shell,
) -> int:
    r, s = first
    u, w = second
    return (
        u * s
        + 3 * u
        - w * r
        - 2 * w
        - 3 * r
        + 2 * s
    )


def _add(left: Element, right: Element) -> Element:
    result = dict(left)
    for shell, coefficient in right.items():
        value = sp.expand(result.get(shell, 0) + coefficient)
        if value == 0:
            result.pop(shell, None)
        else:
            result[shell] = value
    return result


def _scale(value: Element, scalar: sp.Expr) -> Element:
    if scalar == 0:
        return {}
    return {
        shell: sp.expand(scalar * coefficient)
        for shell, coefficient in value.items()
        if coefficient != 0
    }


def _bracket(left: Element, right: Element) -> Element:
    result: Element = {}
    for first, first_coefficient in left.items():
        for second, second_coefficient in right.items():
            bracket_scalar = _shell_bracket_coefficient(first, second)
            if bracket_scalar == 0:
                continue
            shell = (first[0] + second[0], first[1] + second[1])
            value = sp.expand(
                result.get(shell, 0)
                + bracket_scalar * first_coefficient * second_coefficient
            )
            if value == 0:
                result.pop(shell, None)
            else:
                result[shell] = value
    return result


def run(depth: int = 15) -> dict[str, object]:
    if depth < 7 or depth % 2 == 0:
        raise ValueError("depth must be odd and at least seven")

    e, ell = sp.symbols("e ell")
    outer: Element = {(0, 1): -e / 2}
    middle: Element = {
        (1, 0): sp.Integer(-1),
        (0, 1): -ell,
    }

    ad_outer_middle: list[Element] = [middle]
    for _ in range(1, depth):
        ad_outer_middle.append(
            _bracket(outer, ad_outer_middle[-1])
        )

    ad_middle_outer: list[Element] = [outer]
    for _ in range(1, depth):
        ad_middle_outer.append(
            _bracket(middle, ad_middle_outer[-1])
        )

    transported_outer: dict[tuple[int, int], Element] = {}
    for middle_depth in range(depth):
        value = ad_middle_outer[middle_depth]
        transported_outer[(0, middle_depth)] = value
        for outer_depth in range(1, depth - middle_depth):
            value = _bracket(outer, value)
            transported_outer[(outer_depth, middle_depth)] = value

    velocity: list[Element] = []
    for order in range(depth):
        value: Element = {}
        if order == 0:
            value = _add(value, outer)
        value = _add(
            value,
            _scale(
                ad_outer_middle[order],
                sp.Rational(1, factorial(order)),
            ),
        )
        for outer_depth in range(order + 1):
            middle_depth = order - outer_depth
            value = _add(
                value,
                _scale(
                    transported_outer[(outer_depth, middle_depth)],
                    sp.Rational(
                        1,
                        factorial(outer_depth)
                        * factorial(middle_depth),
                    ),
                ),
            )
        velocity.append(value)

    operations = FormalLieOps[Element](
        zero=dict,
        add=_add,
        scale=lambda value, scalar: _scale(
            value,
            sp.Rational(scalar.numerator, scalar.denominator),
        ),
        bracket=_bracket,
    )
    logarithm = magnus_from_velocity(
        velocity=velocity,
        maximum_order=depth,
        ops=operations,
        placement=VelocityPlacement.LEFT_MULTIPLY,
    )

    expected = {
        1: sp.Integer(1),
        2: sp.Rational(3, 2) * e,
        3: sp.Rational(6, 5) * e * (3 * e + ell),
        4: (
            sp.Rational(3, 35)
            * e
            * (132 * e**2 + 102 * e * ell + 25 * ell**2)
        ),
    }
    rows: list[dict[str, object]] = []
    all_nonnegative = True
    shell_sign_summary: list[dict[str, object]] = []
    for order in range(1, depth + 1, 2):
        buckets: dict[int, dict[str, int]] = {}
        for (r, shell_s), coefficient in logarithm[order].items():
            q_degree = shell_s - r + 1
            assert q_degree >= 0 and q_degree % 2 == 0
            wick_coefficient = sp.expand(
                -coefficient * (-1) ** (q_degree // 2)
            )
            signs = [
                sp.sign(sp.Rational(value))
                for value in sp.Poly(wick_coefficient, e, ell).coeffs()
            ]
            sign_class = (
                "nonnegative"
                if all(value >= 0 for value in signs)
                else (
                    "nonpositive"
                    if all(value <= 0 for value in signs)
                    else "mixed"
                )
            )
            bucket = buckets.setdefault(
                q_degree,
                {"nonnegative": 0, "nonpositive": 0, "mixed": 0},
            )
            bucket[sign_class] += 1
        for q_degree, counts in sorted(buckets.items()):
            shell_sign_summary.append(
                {
                    "order": order,
                    "q_degree_after_wick_rotation": q_degree,
                    **counts,
                }
            )
    for k in range(1, (depth + 1) // 2 + 1):
        order = 2 * k - 1
        boundary = sp.factor(
            -logarithm[order].get((k, k - 1), 0)
        )
        if k in expected:
            assert sp.expand(boundary - expected[k]) == 0
        polynomial = sp.Poly(sp.expand(boundary), e, ell)
        coefficients = [sp.Rational(item) for item in polynomial.coeffs()]
        nonnegative = all(item >= 0 for item in coefficients)
        nonzero = any(item > 0 for item in coefficients)
        all_nonnegative = all_nonnegative and nonnegative and nonzero
        rows.append(
            {
                "k": k,
                "order": order,
                "minus_boundary_polynomial": str(boundary),
                "term_count": len(polynomial.terms()),
                "coefficientwise_nonnegative": nonnegative,
                "nonzero": nonzero,
                "evaluation_e1_ell3": str(boundary.subs({e: 1, ell: 3})),
            }
        )

    return {
        "schema": (
            "axiompack.jacobian_fixed_rational_odd_boundary.v1"
        ),
        "symmetric_product": (
            "exp(-t*e*Y/2)*exp(-t*(X+ell*Y))*exp(-t*e*Y/2)"
        ),
        "checked_through_order": depth,
        "checked_through_boundary_index": (depth + 1) // 2,
        "all_checked_boundary_polynomials_coefficientwise_nonnegative": (
            all_nonnegative
        ),
        "rows": rows,
        "wick_rotated_shell_sign_summary": shell_sign_summary,
        "claim_boundary": (
            "Symbolic finite discriminator for boundary positivity. "
            "An all-order recurrence is still required."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
