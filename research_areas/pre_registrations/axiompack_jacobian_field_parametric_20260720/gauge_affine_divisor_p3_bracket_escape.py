#!/usr/bin/env python3
"""Bracket escape for the regular affine-divisor ``P^3`` control."""

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
from gauge_finite_lie_orbit_bracket_escape import (  # noqa: E402
    _assert_top_hamiltonian,
    _coefficient,
)
from gauge_regular_singular_connection import (  # noqa: E402
    _inverse_action,
    source_only_connection,
)


Pair = tuple[sp.Expr, sp.Expr]


def run() -> dict[str, object]:
    data = source_only_connection()
    s, v, t, _ = data["symbols"]
    family_p, _family_q = data["family"]
    pullback_p3 = _inverse_action(
        data["jacobian"],
        data["determinant"],
        (sp.Integer(0), -3 * family_p**2),
    )
    scalar = sp.factor(
        -192
        * (s**2 - 3 * s - 8)
        / (
            (s - 6) ** 3
            * (s - 4) ** 2
            * (s + 4) ** 2
        )
    )
    field: Pair = tuple(
        sp.cancel(
            data["source_only"][index]
            - scalar * pullback_p3[index]
        )
        for index in range(2)
    )  # type: ignore[assignment]

    y = sp.symbols("y")
    divisor_restriction = sp.factor(
        2
        * field[0]
        .subs(t, -1 + sp.Rational(3, 2) * v)
        .subs(v, (y - 3) / 2)
    )
    expected_divisor = sp.factor(
        s
        * (
            9 * s**2 * y
            - 15 * s**2
            - 144 * y
            + 160
        )
        / (3 * (s - 4) ** 2 * (s + 4) ** 2)
    )
    assert sp.factor(divisor_restriction - expected_divisor) == 0
    assert sp.Poly(
        sp.together(divisor_restriction).as_numer_denom()[0],
        y,
    ).degree() == 1

    first = _coefficient(field, s, 0)
    second = _coefficient(field, s, 1)
    g = sp.symbols("g")
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

    first_bracket = _bracket(first, second, v, t)
    radial_bracket_hamiltonian = (v * g) ** 8 / 32
    assert _degree(first_bracket, v, t) == 13
    _assert_top_hamiltonian(
        first_bracket,
        radial_bracket_hamiltonian,
        v,
        t,
        g,
    )

    seed = _bracket(first, first_bracket, v, t)
    seed_coefficient = -sp.Rational(3, 128)
    seed_hamiltonian = seed_coefficient * v**11 * g**10
    assert _degree(seed, v, t) == 18
    _assert_top_hamiltonian(seed, seed_hamiltonian, v, t, g)

    # Once the asymmetric seed appears, its leading bracket with the radial
    # top shell of V_0 attains the maximal bracket degree. The weighted
    # monomial law therefore iterates without needing lower shells.
    next_shell = _bracket(
        _top_homogeneous(first, v, t),
        _top_homogeneous(seed, v, t),
        v,
        t,
    )
    next_hamiltonian = (
        seed_coefficient
        * sp.Rational(3, 4)
        * v**16
        * g**13
    )
    assert _degree(next_shell, v, t) == 26
    expected_next = _field_from_weighted_hamiltonian(
        next_hamiltonian,
        v,
        t,
        g,
    )
    assert all(
        sp.expand(next_shell[index] - expected_next[index]) == 0
        for index in range(2)
    )

    j = sp.symbols("j", integer=True, nonnegative=True)
    symbolic_multiplier = sp.factor(
        sp.Rational(1, 8)
        * (
            6 * (11 + 5 * j)
            - 6 * (10 + 3 * j)
        )
    )
    assert sp.factor(
        symbolic_multiplier
        - sp.Rational(3, 4) * (2 * j + 1)
    ) == 0

    return {
        "schema": (
            "axiompack.jacobian_affine_divisor_p3_bracket_escape.v1"
        ),
        "target_control": {
            "hamiltonian": "a(s)*P^3",
            "a(s)": str(scalar),
            "target_lie_dimension": 1,
            "target_lie_algebra": "abelian",
        },
        "divisor_source_connection": {
            "field": str(divisor_restriction),
            "degree": 1,
            "lie_algebra": "span{d/dy,y*d/dy}",
        },
        "source_connection": {
            "first_two_degrees": [9, 11],
            "first_two_weighted_hamiltonians": [
                str(first_hamiltonian),
                str(second_hamiltonian),
            ],
            "first_bracket": {
                "degree": 13,
                "weighted_hamiltonian": str(
                    radial_bracket_hamiltonian
                ),
            },
        },
        "escaping_seed": {
            "word": "ad_V0^2(V1)",
            "source_degree": 18,
            "weighted_hamiltonian": str(seed_hamiltonian),
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
        "claim_boundary": (
            "The regular P^3 control has finite target and divisor Lie "
            "algebras, but its full source projection has "
            "infinite-dimensional Lie closure. Higher-normal and "
            "higher-isotropy target controls remain separate cases."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
