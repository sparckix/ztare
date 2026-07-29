#!/usr/bin/env python3
"""Compressed exact shell replay for the fixed-rational cusp BCH product.

At amplitude 144 the two Hamiltonians are combinations of ``P^3`` and
``Q^2``.  Every evaluated Lie word with ``r`` cubic leaves and ``s``
quadratic leaves lies on one monomial shell.  Working in that quotient avoids
the large intermediate polynomials produced by a direct BCH expansion.

The replay remains a finite discriminator.  It checks the fixed amplitude
through a substantially longer exact prefix and records the all-order shell
bracket law; it does not infer nonvanishing after the checked depth.
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


Shell = tuple[int, int]
Element = dict[Shell, Fraction]


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
        result[shell] = result.get(shell, Fraction(0)) + coefficient
        if result[shell] == 0:
            del result[shell]
    return result


def _scale(value: Element, scalar: Fraction) -> Element:
    if scalar == 0:
        return {}
    return {
        shell: scalar * coefficient
        for shell, coefficient in value.items()
        if scalar * coefficient
    }


def _bracket(left: Element, right: Element) -> Element:
    result: Element = {}
    for first, first_coefficient in left.items():
        for second, second_coefficient in right.items():
            scalar = _shell_bracket_coefficient(first, second)
            if scalar == 0:
                continue
            shell = (first[0] + second[0], first[1] + second[1])
            coefficient = (
                first_coefficient * second_coefficient * scalar
            )
            result[shell] = result.get(shell, Fraction(0)) + coefficient
            if result[shell] == 0:
                del result[shell]
    return result


def _direct_hamiltonian(shell: Shell) -> sp.Expr:
    p, q = sp.symbols("P Q")
    r, s = shell
    return p ** (2 * r - s + 1) * q ** (s - r + 1)


def _direct_bracket(first: sp.Expr, second: sp.Expr) -> sp.Expr:
    p, q = sp.symbols("P Q")
    return sp.expand(
        sp.diff(first, q) * sp.diff(second, p)
        - sp.diff(first, p) * sp.diff(second, q)
    )


def _verify_shell_law() -> None:
    for r in range(4):
        for s in range(max(0, r - 1), 5):
            first = (r, s)
            first_hamiltonian = _direct_hamiltonian(first)
            for u in range(4):
                for w in range(max(0, u - 1), 5):
                    second = (u, w)
                    coefficient = _shell_bracket_coefficient(
                        first, second
                    )
                    expected = (
                        coefficient
                        * _direct_hamiltonian((r + u, s + w))
                    )
                    assert sp.expand(
                        _direct_bracket(
                            first_hamiltonian,
                            _direct_hamiltonian(second),
                        )
                        - expected
                    ) == 0


def run(depth: int = 41) -> dict[str, object]:
    if depth < 3:
        raise ValueError("depth must be at least three")
    _verify_shell_law()

    x: Element = {(1, 0): Fraction(1)}
    y: Element = {(0, 1): Fraction(1)}
    first_factor = _add(_scale(x, Fraction(-4)), _scale(y, Fraction(-27)))
    second_factor = _scale(y, Fraction(-9))

    # For g(t)=exp(t*A)exp(t*D),
    #
    #   g' g^-1 = A + exp(t ad_A)D.
    velocity: list[Element] = []
    iterate = second_factor
    for order in range(depth):
        value = _scale(iterate, Fraction(1, factorial(order)))
        if order == 0:
            value = _add(first_factor, value)
        velocity.append(value)
        iterate = _bracket(first_factor, iterate)

    operations = FormalLieOps[Element](
        zero=dict,
        add=_add,
        scale=lambda value, scalar: _scale(value, scalar),
        bracket=_bracket,
    )
    logarithm = magnus_from_velocity(
        velocity=velocity,
        maximum_order=depth,
        ops=operations,
        placement=VelocityPlacement.LEFT_MULTIPLY,
    )

    rows: list[dict[str, object]] = []
    coefficients: dict[int, Fraction] = {}
    for order in range(1, depth + 1):
        if order % 2:
            half = (order + 1) // 2
            shell = (half, half - 1)
        else:
            half = order // 2
            shell = (half, half)
        coefficient = logarithm[order].get(shell, Fraction(0))
        assert coefficient < 0
        coefficients[order] = coefficient
        rows.append({
            "order": order,
            "shell": list(shell),
            "monomial": str(_direct_hamiltonian(shell)),
            "coefficient": str(coefficient),
            "negative": True,
        })

    adjacent_rows = []
    for half in range(1, depth // 2 + 1):
        odd = 2 * half - 1
        even = 2 * half
        ratio = coefficients[even] / coefficients[odd]
        expected = Fraction(9 * (half + 2))
        assert ratio == expected
        adjacent_rows.append({
            "odd_order": odd,
            "even_order": even,
            "ratio": str(ratio),
        })

    return {
        "schema": (
            "axiompack.jacobian_fixed_rational_cusp_shell_recurrence.v1"
        ),
        "amplitude": "144",
        "evaluated_shell_basis": (
            "H_(r,s)=P^(2*r-s+1)*Q^(s-r+1)"
        ),
        "shell_bracket": (
            "[H_(r,s),H_(u,w)]="
            "(u*s+3*u-w*r-2*w-3*r+2*s)*H_(r+u,s+w)"
        ),
        "checked_through_order": depth,
        "all_checked_critical_coefficients_negative": True,
        "rows": rows,
        "adjacent_ratios": adjacent_rows,
        "claim_boundary": (
            "Exact fixed-amplitude shell replay through the declared "
            "order. The shell law is all-order, but nonvanishing of the "
            "odd critical coefficient after the prefix remains open."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
