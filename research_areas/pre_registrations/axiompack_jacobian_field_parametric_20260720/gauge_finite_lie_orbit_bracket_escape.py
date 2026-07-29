#!/usr/bin/env python3
"""Exact bracket-growth obstruction for the lowest-weight target normal form.

The target controls ``P^3`` and ``P*Q`` form a two-dimensional solvable Lie
algebra.  This replay constructs the corresponding exact source connection,
checks its first two coefficient fields, and verifies the leading bracket
ray.  The all-order step is the displayed monomial bracket identity, not an
extrapolation from the finite regression range.
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


def _source_connection() -> tuple[
    sp.Symbol,
    sp.Symbol,
    sp.Symbol,
    Pair,
]:
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
    pullback_pq = _inverse_action(
        jacobian,
        determinant,
        (family_p, -family_q),
    )
    coefficient_p3 = sp.factor(
        96
        * (s**2 - 12 * s + 16)
        / (
            (s - 6) ** 3
            * (s - 4) ** 2
            * (s + 4) ** 2
        )
    )
    coefficient_pq = sp.factor(
        2 * s / ((s - 4) * (s + 4))
    )
    field = tuple(
        sp.cancel(
            source_only[index]
            - coefficient_p3 * pullback_p3[index]
            - coefficient_pq * pullback_pq[index]
        )
        for index in range(2)
    )
    return s, v, t, field  # type: ignore[return-value]


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


def run(regression_depth: int = 5) -> dict[str, object]:
    if regression_depth < 1:
        raise ValueError("regression_depth must be positive")

    s, v, t, field = _source_connection()
    g = sp.symbols("g")
    first = _coefficient(field, s, 0)
    second = _coefficient(field, s, 1)

    first_hamiltonian = (v * g) ** 6 / 8
    second_hamiltonian = -3 * (v * g) ** 7 / 56
    assert _degree(first, v, t) == 9
    assert _degree(second, v, t) == 11
    _assert_top_hamiltonian(
        first, first_hamiltonian, v, t, g
    )
    _assert_top_hamiltonian(
        second, second_hamiltonian, v, t, g
    )

    # The first nonzero seed on the escaping ray is ad_first^2(second).
    seed = _bracket(
        first,
        _bracket(first, second, v, t),
        v,
        t,
    )
    seed_coefficient = -sp.Rational(3, 128)
    seed_hamiltonian = seed_coefficient * v**11 * g**10
    assert _degree(seed, v, t) == 18
    _assert_top_hamiltonian(seed, seed_hamiltonian, v, t, g)

    # For weighted Hamiltonians
    #
    #   h=c*v^a*g^b, k=d*v^A*g^B,
    #
    # the leading Hamiltonian of [X_h,X_k] is
    #
    #   c*d*(b*A-a*B)*v^(a+A-1)*g^(b+B-3).
    #
    # Substituting h=(v*g)^6/8 and the j-th ray gives the nonzero
    # multiplier (3/4)*(2*j+1).
    j = sp.symbols("j", integer=True, nonnegative=True)
    symbolic_multiplier = sp.factor(
        sp.Rational(1, 8)
        * (
            6 * (11 + 5 * j)
            - 6 * (10 + 3 * j)
        )
    )
    assert sp.expand(
        symbolic_multiplier - sp.Rational(3, 4) * (2 * j + 1)
    ) == 0

    rows: list[dict[str, object]] = []
    iterate = seed
    coefficient = seed_coefficient
    for index in range(regression_depth):
        hamiltonian = (
            coefficient
            * v ** (11 + 5 * index)
            * g ** (10 + 3 * index)
        )
        expected_degree = 18 + 8 * index
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
            coefficient
            * sp.Rational(3, 4)
            * (2 * index + 1)
        )

    return {
        "schema": (
            "axiompack.jacobian_finite_lie_orbit_bracket_escape.v1"
        ),
        "target_control_algebra": {
            "basis": ["P^3", "P*Q"],
            "bracket": "[P*Q,P^3]=-3*P^3",
            "dimension": 2,
        },
        "source_connection_coefficient_degrees": [9, 11],
        "leading_weighted_hamiltonians": [
            str(first_hamiltonian),
            str(second_hamiltonian),
        ],
        "escaping_seed": {
            "word": "ad_A^2(B)",
            "weighted_hamiltonian": str(seed_hamiltonian),
            "source_degree": 18,
        },
        "all_order_ray": {
            "weighted_hamiltonian": (
                "c_j*v^(11+5*j)*g^(10+3*j)"
            ),
            "coefficient_initial": "-3/128",
            "coefficient_recurrence": (
                "c_(j+1)=(3/4)*(2*j+1)*c_j"
            ),
            "source_degree": "18+8*j",
            "nonzero_for_every_j": True,
        },
        "regression_rows": rows,
        "claim_boundary": (
            "The source projection of the exact P^3/PQ connection has "
            "infinite-dimensional Lie closure. This excludes a "
            "finite-dimensional formal orbit containing this normalized "
            "connection, not every possible nonlinear target gauge."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
