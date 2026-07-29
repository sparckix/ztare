#!/usr/bin/env python3
"""Exact bracket escape for the divisor-affine one-dimensional target line.

The scalar control along

    H_0 = -P^3/36 - Q^2/4

is the strongest abelian candidate exposed by the exceptional-divisor
normalization: its exact source connection vanishes at parameter zero and is
affine on the divisor.  The full source fields nevertheless generate a
nonzero leading bracket ray of unbounded degree.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_controlled_global_magnus import (  # noqa: E402
    _bracket,
    _degree,
    _field_from_weighted_hamiltonian,
    _top_homogeneous,
)
from gauge_regular_singular_connection import (  # noqa: E402
    _inverse_action,
    source_only_connection,
)


Pair = tuple[sp.Expr, sp.Expr]


def _subtract(left: Pair, right: Pair) -> Pair:
    return (
        sp.expand(left[0] - right[0]),
        sp.expand(left[1] - right[1]),
    )


def _coefficient(field: Pair, parameter: sp.Symbol, order: int) -> Pair:
    return tuple(
        sp.series(component, parameter, 0, order + 1)
        .removeO()
        .expand()
        .coeff(parameter, order)
        for component in field
    )  # type: ignore[return-value]


def _assert_top_hamiltonian(
    field: Pair,
    hamiltonian: sp.Expr,
    v: sp.Symbol,
    t: sp.Symbol,
    g: sp.Symbol,
) -> None:
    top = _top_homogeneous(field, v, t)
    expected = _field_from_weighted_hamiltonian(
        hamiltonian,
        v,
        t,
        g,
    )
    assert _subtract(top, expected) == (0, 0)


def run(regression_depth: int = 4) -> dict[str, object]:
    if regression_depth < 1:
        raise ValueError("regression_depth must be positive")

    data = source_only_connection()
    s, v, t, _ = data["symbols"]
    family_p, family_q = data["family"]
    jacobian = data["jacobian"]
    determinant = data["determinant"]
    source_only = data["source_only"]
    pullback_p3 = _inverse_action(
        jacobian,
        determinant,
        (sp.Integer(0), -3 * family_p**2),
    )
    pullback_q2 = _inverse_action(
        jacobian,
        determinant,
        (2 * family_q, sp.Integer(0)),
    )

    scalar = sp.factor(
        6912
        * (s**2 - 3 * s - 8)
        / (
            (s - 6) ** 3
            * (s - 4) ** 2
            * (s + 4) ** 2
        )
    )
    # X_H0 = -(1/36)X_(P^3) -(1/4)X_(Q^2).
    field: Pair = tuple(
        sp.cancel(
            source_only[index]
            + scalar * pullback_p3[index] / 36
            + scalar * pullback_q2[index] / 4
        )
        for index in range(2)
    )  # type: ignore[assignment]
    assert all(sp.factor(component.subs(s, 0)) == 0 for component in field)

    y = sp.symbols("y")
    divisor_restriction = sp.factor(
        2
        * field[0]
        .subs(t, -1 + sp.Rational(3, 2) * v)
        .subs(v, (y - 3) / 2)
    )
    assert sp.Poly(
        sp.together(divisor_restriction).as_numer_denom()[0],
        y,
    ).degree() == 1

    g = sp.symbols("g")
    first = _coefficient(field, s, 1)
    second = _coefficient(field, s, 2)
    first_hamiltonian = -3 * (v * g) ** 7 / 448
    second_hamiltonian = 7 * (v * g) ** 8 / 2048
    assert _degree(first, v, t) == 11
    assert _degree(second, v, t) == 13
    _assert_top_hamiltonian(
        first, first_hamiltonian, v, t, g
    )
    _assert_top_hamiltonian(
        second, second_hamiltonian, v, t, g
    )

    seed = _bracket(
        first,
        _bracket(first, second, v, t),
        v,
        t,
    )
    seed_coefficient = -sp.Rational(23, 262144)
    seed_hamiltonian = seed_coefficient * v**14 * g**13
    assert _degree(seed, v, t) == 24
    _assert_top_hamiltonian(seed, seed_hamiltonian, v, t, g)

    # For h_A=-(3/448)*v^7*g^7 and
    # h_j=c_j*v^(14+6j)*g^(13+4j), the weighted Hamiltonian bracket
    # multiplies c_j by -(3/64)*(2j+1).
    j = sp.symbols("j", integer=True, nonnegative=True)
    symbolic_multiplier = sp.factor(
        -sp.Rational(3, 448)
        * (
            7 * (14 + 6 * j)
            - 7 * (13 + 4 * j)
        )
    )
    assert sp.expand(
        symbolic_multiplier
        + sp.Rational(3, 64) * (2 * j + 1)
    ) == 0

    rows: list[dict[str, object]] = []
    iterate = seed
    coefficient = seed_coefficient
    for index in range(regression_depth):
        hamiltonian = (
            coefficient
            * v ** (14 + 6 * index)
            * g ** (13 + 4 * index)
        )
        expected_degree = 24 + 10 * index
        assert _degree(iterate, v, t) == expected_degree
        _assert_top_hamiltonian(iterate, hamiltonian, v, t, g)
        rows.append({
            "adjoint_depth_after_seed": index,
            "source_degree": expected_degree,
            "weighted_hamiltonian": str(hamiltonian),
            "coefficient": str(coefficient),
        })
        iterate = _bracket(first, iterate, v, t)
        coefficient = sp.factor(
            -coefficient
            * sp.Rational(3, 64)
            * (2 * index + 1)
        )

    return {
        "schema": (
            "axiompack.jacobian_finite_abelian_orbit_bracket_escape.v1"
        ),
        "target_control": {
            "hamiltonian": "-P^3/36-Q^2/4",
            "scalar": str(scalar),
            "dimension": 1,
            "abelian": True,
        },
        "source_connection": {
            "vanishes_at_parameter_zero": True,
            "divisor_restriction": str(divisor_restriction),
            "divisor_degree": 1,
            "first_two_coefficient_degrees": [11, 13],
            "leading_weighted_hamiltonians": [
                str(first_hamiltonian),
                str(second_hamiltonian),
            ],
        },
        "escaping_seed": {
            "word": "ad_A^2(B)",
            "weighted_hamiltonian": str(seed_hamiltonian),
            "source_degree": 24,
        },
        "all_order_ray": {
            "weighted_hamiltonian": (
                "c_j*v^(14+6*j)*g^(13+4*j)"
            ),
            "coefficient_initial": "-23/262144",
            "coefficient_recurrence": (
                "c_(j+1)=-(3/64)*(2*j+1)*c_j"
            ),
            "source_degree": "24+10*j",
            "nonzero_for_every_j": True,
        },
        "regression_rows": rows,
        "claim_boundary": (
            "The source projection of this divisor-affine abelian "
            "connection has infinite-dimensional Lie closure. Other "
            "isotropy-shifted target lines and higher target algebras "
            "remain separate cases."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
