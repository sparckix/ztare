#!/usr/bin/env python3
"""Exact local scan of positive discriminant depth.

For a prefix

    P^a * Q^b * (4*P^3 + 27*Q^2)^d * C,

the coupled cost-three row depends only on the first two coefficients of
the fixed-chart pullbacks of ``P`` and ``Q``.  This replay performs that
calculation in a sparse ``(r, normal_order)`` algebra, applies the same
radial and one-``C`` triangular normalizers as the full staircase, and
reports the leading normal-four quotient.

The scan is finite evidence in ``d``.  It is not an all-depth theorem.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import TypeAlias

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_cone_radial_triangular_staircase import (  # noqa: E402
    _canonical_c_multiplier,
    _canonical_cone_monomial,
)


Sparse: TypeAlias = dict[tuple[int, int], sp.Rational]

MAXIMUM_NORMAL_ORDER = 4
MAXIMUM_RADIAL_DEFICIT = 18

P_ZERO: Sparse = {
    (2, 0): -sp.Rational(3, 4),
    (1, 0): sp.Integer(1),
    (0, 1): sp.Rational(1, 2),
}
P_ONE: Sparse = {
    (3, 0): sp.Rational(1, 8),
    (2, 0): -sp.Rational(1, 8),
    (1, 1): -sp.Rational(1, 8),
}
Q_ZERO: Sparse = {
    (3, 0): -sp.Rational(1, 4),
    (2, 0): sp.Rational(1, 4),
    (1, 1): sp.Rational(1, 4),
}
Q_ONE: Sparse = {
    (4, 0): sp.Rational(3, 64),
    (3, 0): -sp.Rational(1, 8),
    (2, 1): -sp.Rational(1, 16),
    (2, 0): sp.Rational(1, 12),
    (1, 1): sp.Rational(1, 12),
    (0, 2): sp.Rational(1, 48),
}
D_ZERO: Sparse = {
    (5, 0): sp.Rational(27, 8),
    (4, 0): -sp.Rational(117, 16),
    (3, 1): -sp.Rational(45, 8),
    (3, 0): sp.Integer(4),
    (2, 2): -sp.Rational(9, 16),
    (2, 1): sp.Integer(6),
    (1, 2): sp.Integer(3),
    (0, 3): sp.Rational(1, 2),
}
D_ONE: Sparse = {
    (7, 0): sp.Rational(27, 128),
    (6, 0): -sp.Rational(99, 128),
    (5, 1): -sp.Rational(63, 128),
    (5, 0): sp.Rational(15, 16),
    (4, 1): sp.Rational(39, 32),
    (4, 0): -sp.Rational(3, 8),
    (3, 2): sp.Rational(3, 8),
    (3, 1): -sp.Rational(3, 4),
    (2, 2): -sp.Rational(15, 32),
    (1, 3): -sp.Rational(3, 32),
}
C_ZERO: Sparse = {
    (2, 2): -sp.Rational(9, 16),
    (1, 2): sp.Rational(3, 4),
    (0, 3): sp.Rational(1, 2),
    (0, 2): -sp.Rational(1, 4),
}
C_ONE: Sparse = {
    (7, 0): sp.Rational(27, 128),
    (6, 0): sp.Rational(27, 64),
    (5, 1): -sp.Rational(63, 128),
    (5, 0): -sp.Rational(81, 32),
    (4, 1): -sp.Rational(75, 64),
    (4, 0): sp.Rational(53, 16),
    (3, 2): sp.Rational(3, 8),
    (3, 1): sp.Rational(55, 16),
    (3, 0): -sp.Rational(7, 4),
    (2, 2): sp.Rational(15, 16),
    (2, 1): -sp.Rational(17, 8),
    (2, 0): sp.Rational(1, 3),
    (1, 3): -sp.Rational(3, 32),
    (1, 2): -sp.Integer(1),
    (1, 1): sp.Rational(1, 3),
    (0, 3): -sp.Rational(3, 16),
    (0, 2): sp.Rational(1, 12),
}


def _clean(value: Sparse) -> Sparse:
    return {
        exponent: sp.factor(coefficient)
        for exponent, coefficient in value.items()
        if coefficient != 0
    }


def _add(left: Sparse, right: Sparse) -> Sparse:
    result = dict(left)
    for exponent, coefficient in right.items():
        result[exponent] = result.get(exponent, 0) + coefficient
    return _clean(result)


def _scale(value: Sparse, scalar: sp.Expr) -> Sparse:
    return _clean({
        exponent: sp.factor(scalar * coefficient)
        for exponent, coefficient in value.items()
    })


def _multiply(
    left: Sparse,
    right: Sparse,
    minimum_radial_degree: int,
) -> Sparse:
    result: Sparse = {}
    for (left_r, left_n), left_coefficient in left.items():
        for (right_r, right_n), right_coefficient in right.items():
            exponent = (left_r + right_r, left_n + right_n)
            if (
                exponent[0] < minimum_radial_degree
                or exponent[1] > MAXIMUM_NORMAL_ORDER
            ):
                continue
            result[exponent] = (
                result.get(exponent, 0)
                + left_coefficient * right_coefficient
            )
    return _clean(result)


def _power(
    value: Sparse,
    exponent: int,
    maximum_radial_degree: int,
) -> Sparse:
    if exponent < 0:
        raise ValueError("powers must be nonnegative")
    result: Sparse = {(0, 0): sp.Integer(1)}
    for index in range(exponent):
        result = _multiply(
            result,
            value,
            max(
                0,
                maximum_radial_degree * (index + 1)
                - MAXIMUM_RADIAL_DEFICIT,
            ),
        )
    return result


def _product(
    values: list[Sparse],
    minimum_radial_degree: int,
) -> Sparse:
    result: Sparse = {(0, 0): sp.Integer(1)}
    for value in values:
        # Postpone the final radial cut until all factors have supplied
        # their leading degree.
        result = _multiply(result, value, 0)
    return {
        exponent: coefficient
        for exponent, coefficient in result.items()
        if exponent[0] >= minimum_radial_degree
    }


def _monomial_seed(
    p_exponent: int,
    q_exponent: int,
    minimum_radial_degree: int,
) -> Sparse:
    return _product(
        [
            _power(P_ZERO, p_exponent, 2),
            _power(Q_ZERO, q_exponent, 3),
        ],
        minimum_radial_degree,
    )


def _prefix_first_coefficient(
    a: int,
    b: int,
    depth: int,
    minimum_radial_degree: int,
) -> Sparse:
    p_power = _power(P_ZERO, a, 2)
    q_power = _power(Q_ZERO, b, 3)
    d_power = _power(D_ZERO, depth, 5)
    terms: list[Sparse] = []
    if a:
        terms.append(_scale(_product([
            _power(P_ZERO, a - 1, 2),
            P_ONE,
            q_power,
            d_power,
            C_ZERO,
        ], minimum_radial_degree), a))
    if b:
        terms.append(_scale(_product([
            p_power,
            _power(Q_ZERO, b - 1, 3),
            Q_ONE,
            d_power,
            C_ZERO,
        ], minimum_radial_degree), b))
    if depth:
        terms.append(_scale(_product([
            p_power,
            q_power,
            _power(D_ZERO, depth - 1, 5),
            D_ONE,
            C_ZERO,
        ], minimum_radial_degree), depth))
    terms.append(_product([
        p_power,
        q_power,
        d_power,
        C_ONE,
    ], minimum_radial_degree))
    result: Sparse = {}
    for term in terms:
        result = _add(result, term)
    return _scale(result, 8)


def _normalize(
    residual: Sparse,
    minimum_radial_degree: int,
) -> Sparse:
    result = dict(residual)
    while True:
        radial_degrees = [
            radial
            for (radial, normal), coefficient in result.items()
            if (
                normal == 0
                and coefficient != 0
                and _canonical_cone_monomial(radial) is not None
            )
        ]
        if not radial_degrees:
            break
        radial = max(radial_degrees)
        p_exponent, q_exponent = _canonical_cone_monomial(radial)
        seed = _scale(
            _monomial_seed(
                p_exponent,
                q_exponent,
                minimum_radial_degree,
            ),
            8,
        )
        coefficient = -result[(radial, 0)] / seed[(radial, 0)]
        result = _add(result, _scale(seed, coefficient))

    while True:
        radial_degrees = [
            radial
            for (radial, normal), coefficient in result.items()
            if (
                normal == 2
                and coefficient != 0
                and _canonical_c_multiplier(radial) is not None
            )
        ]
        if not radial_degrees:
            break
        radial = max(radial_degrees)
        p_exponent, q_exponent = _canonical_c_multiplier(radial)
        seed = _scale(_product([
            _power(P_ZERO, p_exponent, 2),
            _power(Q_ZERO, q_exponent, 3),
            C_ZERO,
        ], minimum_radial_degree), 8)
        coefficient = -result[(radial, 2)] / seed[(radial, 2)]
        result = _add(result, _scale(seed, coefficient))
    return _clean(result)


def _one_case(a: int, b: int, depth: int) -> dict[str, object]:
    if a not in {0, 1, 2}:
        raise ValueError("a must be a discriminant residue 0, 1, or 2")
    if depth < 1:
        raise ValueError("the discriminant depth must be positive")
    if a + 3 * depth + 3 > 2 * b:
        raise ValueError("the all-P^3 prefix branch is outside the cone")
    baseline = 2 * a + 3 * b + 5 * depth
    minimum = max(0, baseline - MAXIMUM_RADIAL_DEFICIT)
    residual = _normalize(
        _prefix_first_coefficient(a, b, depth, minimum),
        minimum,
    )
    normal_four = {
        exponent: sp.factor(coefficient / 3)
        for exponent, coefficient in residual.items()
        if exponent[1] == 4 and coefficient != 0
    }
    if not normal_four:
        raise AssertionError("the retained normal-four quotient vanished")
    terminal = max(normal_four, key=lambda exponent: exponent[0])
    return {
        "a": a,
        "b": b,
        "discriminant_depth": depth,
        "terminal_key_r_normal": list(terminal),
        "terminal_exponent_u_z": [
            terminal[0],
            terminal[0] + terminal[1],
        ],
        "terminal_coefficient": str(normal_four[terminal]),
        "terminal_coefficient_after_removing_Q_scale": str(sp.factor(
            normal_four[terminal]
            / (-sp.Rational(1, 4)) ** b
        )),
    }


def run(maximum_depth: int = 8) -> dict[str, object]:
    if maximum_depth < 2:
        raise ValueError("the scan must include depths one and two")
    rows = []
    for depth in range(1, maximum_depth + 1):
        for a in range(3):
            minimum_b = (a + 3 * depth + 4) // 2
            row = _one_case(a, minimum_b, depth)
            rows.append(row)

    expected = {
        (1, 0): ("14,18", "243/32768"),
        (1, 1): ("19,23", "189/65536"),
        (1, 2): ("21,25", "-81/32768"),
        (2, 0): ("26,30", "-2187/4194304"),
        (2, 1): ("28,32", "6561/16777216"),
        (2, 2): ("33,37", "19683/268435456"),
    }
    for row in rows:
        key = (row["discriminant_depth"], row["a"])
        if key not in expected:
            continue
        exponent = ",".join(
            str(value) for value in row["terminal_exponent_u_z"]
        )
        assert (
            exponent,
            row["terminal_coefficient"],
        ) == expected[key]

    return {
        "schema": "axiompack.jacobian_cone_discriminant_depth_scan.v1",
        "maximum_depth": maximum_depth,
        "full_staircase_controls_reproduced_at_depths": [1, 2],
        "all_scanned_terminal_coefficients_nonzero": all(
            row["terminal_coefficient"] != "0" for row in rows
        ),
        "rows": rows,
        "claim_boundary": (
            "Finite exact local scan of the first coupled quotient at "
            "positive discriminant depth. No all-depth recurrence or "
            "all-order Magnus nontermination is claimed."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
