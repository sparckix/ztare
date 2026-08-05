#!/usr/bin/env python3
"""All-depth leading quotient for positive discriminant valuation.

The fixed-chart leading factors are

    P_0 = (-3/4) r^2 * Pbar,
    Q_0 = (-1/4) r^3 * Qbar,
    D_0 = (27/8) r^5 * Dbar,
    C_0 = (-9/16) r^2 * Cbar.

This replay uses generalized multinomial coefficients for the symbolic
powers ``Qbar^b`` and ``Dbar^d``.  It retains exactly the radial
deficits and normal orders that can feed the leading normal-four
quotient, then applies the canonical radial and one-``C`` normalizers.
The three cases ``d mod 3`` account for the canonical cone-control
residue.  The calculation is repeated for ``P`` residue ``a=0,1,2``.
"""

from __future__ import annotations

from functools import lru_cache
from math import factorial
import json
from pathlib import Path
import sys
from typing import TypeAlias

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


RelativeSparse: TypeAlias = dict[tuple[int, int], sp.Expr]

B, N = sp.symbols("b n", integer=True, positive=True)
MINIMUM_RADIAL_OFFSET = -8
MAXIMUM_NORMAL_ORDER = 4
MAXIMUM_CHOSEN_DEFICIT_TERMS = 8

# Normalized fixed-chart factors.  Keys are
# (radial offset from the leading monomial, normal order).
P_NORMALIZED: RelativeSparse = {
    (0, 0): sp.Integer(1),
    (-1, 0): -sp.Rational(4, 3),
    (-2, 1): -sp.Rational(2, 3),
}
Q_DEFICITS: RelativeSparse = {
    (-1, 0): -sp.Integer(1),
    (-2, 1): -sp.Integer(1),
}
D_DEFICITS: RelativeSparse = {
    (-1, 0): -sp.Rational(13, 6),
    (-2, 1): -sp.Rational(5, 3),
    (-2, 0): sp.Rational(32, 27),
    (-3, 2): -sp.Rational(1, 6),
    (-3, 1): sp.Rational(16, 9),
    (-4, 2): sp.Rational(8, 9),
    (-5, 3): sp.Rational(4, 27),
}
C_NORMALIZED: RelativeSparse = {
    (0, 2): sp.Integer(1),
    (-1, 2): -sp.Rational(4, 3),
    (-2, 3): -sp.Rational(8, 9),
    (-2, 2): sp.Rational(4, 9),
}

# First parameter coefficients divided by the corresponding zero-order
# leading scale.  P/Q/D keys carry relative normal order; C keys carry
# the absolute normal order because C itself is replaced.
P_ONE_RELATIVE: RelativeSparse = {
    (1, 0): -sp.Rational(1, 6),
    (0, 0): sp.Rational(1, 6),
    (-1, 1): sp.Rational(1, 6),
}
Q_ONE_RELATIVE: RelativeSparse = {
    (1, 0): -sp.Rational(3, 16),
    (0, 0): sp.Rational(1, 2),
    (-1, 1): sp.Rational(1, 4),
    (-1, 0): -sp.Rational(1, 3),
    (-2, 1): -sp.Rational(1, 3),
    (-3, 2): -sp.Rational(1, 12),
}
D_ONE_RELATIVE: RelativeSparse = {
    (2, 0): sp.Rational(1, 16),
    (1, 0): -sp.Rational(11, 48),
    (0, 1): -sp.Rational(7, 48),
    (0, 0): sp.Rational(5, 18),
    (-1, 1): sp.Rational(13, 36),
    (-1, 0): -sp.Rational(1, 9),
    (-2, 2): sp.Rational(1, 9),
    (-2, 1): -sp.Rational(2, 9),
    (-3, 2): -sp.Rational(5, 36),
    (-4, 3): -sp.Rational(1, 36),
}
C_ONE_RELATIVE: RelativeSparse = {
    (5, 0): -sp.Rational(3, 8),
    (4, 0): -sp.Rational(3, 4),
    (3, 1): sp.Rational(7, 8),
    (3, 0): sp.Rational(9, 2),
    (2, 1): sp.Rational(25, 12),
    (2, 0): -sp.Rational(53, 9),
    (1, 2): -sp.Rational(2, 3),
    (1, 1): -sp.Rational(55, 9),
    (1, 0): sp.Rational(28, 9),
    (0, 2): -sp.Rational(5, 3),
    (0, 1): sp.Rational(34, 9),
    (0, 0): -sp.Rational(16, 27),
    (-1, 3): sp.Rational(1, 6),
    (-1, 2): sp.Rational(16, 9),
    (-1, 1): -sp.Rational(16, 27),
    (-2, 3): sp.Rational(1, 3),
    (-2, 2): -sp.Rational(4, 27),
}


def _clean(value: RelativeSparse) -> RelativeSparse:
    return {
        exponent: sp.cancel(coefficient)
        for exponent, coefficient in value.items()
        if (
            coefficient != 0
            and exponent[0] >= MINIMUM_RADIAL_OFFSET
            and exponent[1] <= MAXIMUM_NORMAL_ORDER
        )
    }


def _multiply(
    left: RelativeSparse,
    right: RelativeSparse,
) -> RelativeSparse:
    result: RelativeSparse = {}
    for (left_r, left_n), left_coefficient in left.items():
        for (right_r, right_n), right_coefficient in right.items():
            exponent = (left_r + right_r, left_n + right_n)
            if (
                exponent[0] < MINIMUM_RADIAL_OFFSET
                or exponent[1] > MAXIMUM_NORMAL_ORDER
            ):
                continue
            result[exponent] = (
                result.get(exponent, 0)
                + left_coefficient * right_coefficient
            )
    return _clean(result)


def _add_shifted(
    left: RelativeSparse,
    right: RelativeSparse,
    scalar: sp.Expr = sp.Integer(1),
    radial_shift: int = 0,
) -> RelativeSparse:
    result = dict(left)
    for (radial, normal), coefficient in right.items():
        exponent = (radial + radial_shift, normal)
        result[exponent] = (
            result.get(exponent, 0) + scalar * coefficient
        )
    return _clean(result)


@lru_cache(maxsize=None)
def _fixed_p_power(exponent: int) -> RelativeSparse:
    result: RelativeSparse = {(0, 0): sp.Integer(1)}
    for _ in range(exponent):
        result = _multiply(result, P_NORMALIZED)
    return result


def _falling(value: sp.Expr, depth: int) -> sp.Expr:
    return sp.prod(value - index for index in range(depth))


@lru_cache(maxsize=None)
def _generalized_power(
    family: str,
    exponent: sp.Expr,
) -> RelativeSparse:
    deficits = {
        "Q": Q_DEFICITS,
        "D": D_DEFICITS,
    }[family]
    items = list(deficits.items())
    result: RelativeSparse = {(0, 0): sp.Integer(1)}

    def enumerate_counts(
        item_index: int,
        remaining_count: int,
        radial: int,
        normal: int,
        coefficient: sp.Expr,
        chosen: int,
        denominator: int,
    ) -> None:
        if item_index == len(items):
            if chosen:
                key = (radial, normal)
                result[key] = (
                    result.get(key, 0)
                    + _falling(exponent, chosen)
                    * coefficient
                    / denominator
                )
            return
        (delta_radial, delta_normal), item_coefficient = (
            items[item_index]
        )
        maximum_count = remaining_count
        if delta_radial < 0:
            maximum_count = min(
                maximum_count,
                (
                    -MINIMUM_RADIAL_OFFSET + radial
                ) // (-delta_radial),
            )
        if delta_normal > 0:
            maximum_count = min(
                maximum_count,
                (
                    MAXIMUM_NORMAL_ORDER - normal
                ) // delta_normal,
            )
        for count in range(maximum_count + 1):
            enumerate_counts(
                item_index + 1,
                remaining_count - count,
                radial + count * delta_radial,
                normal + count * delta_normal,
                coefficient * item_coefficient**count,
                chosen + count,
                denominator * factorial(count),
            )

    enumerate_counts(
        0,
        MAXIMUM_CHOSEN_DEFICIT_TERMS,
        0,
        0,
        sp.Integer(1),
        0,
        1,
    )
    return _clean(result)


def _product(values: list[RelativeSparse]) -> RelativeSparse:
    result: RelativeSparse = {(0, 0): sp.Integer(1)}
    for value in values:
        result = _multiply(result, value)
    return result


def _canonical_p_exponent(weight_residue: int) -> int:
    return {0: 0, 1: 2, 2: 1}[weight_residue % 3]


def _symbolic_quotient(
    a: int,
    depth: sp.Expr,
    depth_residue: int,
    terminal_offset: int,
) -> sp.Expr:
    p_power = _fixed_p_power(a)
    q_power = _generalized_power("Q", B)
    d_power = _generalized_power("D", depth)
    result: RelativeSparse = {}
    if a:
        result = _add_shifted(
            result,
            _product([
                _fixed_p_power(a - 1),
                P_ONE_RELATIVE,
                q_power,
                d_power,
                C_NORMALIZED,
            ]),
            a,
        )
    result = _add_shifted(
        result,
        _product([
            p_power,
            _generalized_power("Q", B - 1),
            Q_ONE_RELATIVE,
            d_power,
            C_NORMALIZED,
        ]),
        B,
    )
    result = _add_shifted(
        result,
        _product([
            p_power,
            q_power,
            _generalized_power("D", depth - 1),
            D_ONE_RELATIVE,
            C_NORMALIZED,
        ]),
        depth,
    )
    result = _add_shifted(
        result,
        _product([
            p_power,
            q_power,
            d_power,
            C_ONE_RELATIVE,
        ]),
    )
    # Restore source lift 8 and logarithmic integration by 1/3.
    result = {
        exponent: sp.cancel(sp.Rational(8, 3) * coefficient)
        for exponent, coefficient in result.items()
    }

    # The common leading radial degree, including the leading C factor.
    leading_degree = 2 * a + 3 * B + 5 * depth + 2
    for offset in range(5, terminal_offset - 1, -1):
        radial_value = result.get((offset, 0), 0)
        if radial_value:
            residue = (
                2 * a + 2 * depth_residue + 2 + offset
            ) % 3
            control_p = _canonical_p_exponent(residue)
            control_q = sp.cancel(
                (leading_degree + offset - 2 * control_p) / 3
            )
            seed = _product([
                _fixed_p_power(control_p),
                _generalized_power("Q", control_q),
            ])
            result = _add_shifted(
                result,
                seed,
                -radial_value,
                offset,
            )

        c_value = result.get((offset, 2), 0)
        if c_value:
            residue = (
                2 * a + 2 * depth_residue + offset
            ) % 3
            control_p = _canonical_p_exponent(residue)
            control_q = sp.cancel(
                (
                    leading_degree
                    + offset
                    - 2
                    - 2 * control_p
                )
                / 3
            )
            seed = _product([
                _fixed_p_power(control_p),
                _generalized_power("Q", control_q),
                C_NORMALIZED,
            ])
            result = _add_shifted(
                result,
                seed,
                -c_value,
                offset,
            )
    return sp.factor(result.get((terminal_offset, 4), 0))


def _symbolic_terminal(
    a: int,
    depth_residue: int,
) -> sp.Expr:
    return _symbolic_quotient(
        a,
        3 * N + depth_residue,
        depth_residue,
        -1,
    )


def run() -> dict[str, object]:
    rows = []
    for a in range(3):
        for depth_residue in range(3):
            depth = 3 * N + depth_residue
            terminal = _symbolic_terminal(a, depth_residue)
            expected = -depth * (depth - 1) / 24
            assert sp.factor(terminal - expected) == 0
            rows.append({
                "p_residue_a": a,
                "depth_mod_3": depth_residue,
                "symbolic_depth": str(depth),
                "terminal_after_removing_all_leading_scales": str(
                    terminal
                ),
            })
    depth_one_rows = []
    for a in range(3):
        terminal = _symbolic_quotient(
            a,
            sp.Integer(1),
            1,
            -2,
        )
        expected = (9 * B + 26 * a - 6 * a * a) / 108
        assert sp.factor(terminal - expected) == 0
        depth_one_rows.append({
            "p_residue_a": a,
            "terminal_after_removing_all_leading_scales": str(
                terminal
            ),
        })
    return {
        "schema": (
            "axiompack.jacobian_cone_"
            "discriminant_depth_symbolic.v1"
        ),
        "symbolic_residue_checks": rows,
        "depth_one_symbolic_checks": depth_one_rows,
        "normalized_terminal_identity": "-binomial(d,2)/12",
        "restored_terminal_logarithm": (
            "(-1/4)^b*(-3/4)^a*(3/64)*binomial(d,2)"
            "*(27/8)^d at "
            "u^(3*b+2*a+5*d+1)*z^(3*b+2*a+5*d+5)"
        ),
        "nonzero_for_every_integer_depth_at_least_two": True,
        "depth_one_restored_terminal_logarithm": (
            "(-1/4)^b*(-3/4)^a"
            "*[-9*(9*b+26*a-6*a^2)/512] at "
            "u^(3*b+2*a+5)*z^(3*b+2*a+9)"
        ),
        "nonzero_for_depth_one_in_the_cone_range": True,
        "claim_boundary": (
            "Exact all-depth identity for the first coupled "
            "normal-four quotient at every positive discriminant "
            "depth. This does not prove that its full Magnus orbit "
            "has infinite support. The d=0 low mixed residues are "
            "separate."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
