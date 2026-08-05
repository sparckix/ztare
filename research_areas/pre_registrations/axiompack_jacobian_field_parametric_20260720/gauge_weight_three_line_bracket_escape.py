#!/usr/bin/env python3
"""Uniform bracket escape for affine-normalized weight-three target lines.

The line

    H_lambda = -Q^2/4 - P^3/36 + lambda*K_star

contains the normalized target slice and every first-order seed-isotropy
shift.  Except at two explicit parameter values, there is a unique regular
scalar profile that removes the cubic exceptional-divisor term.  This replay
checks its first transverse bracket and records the all-order leading-shell
recurrence.
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
        sp.factor(left[0] - right[0]),
        sp.factor(left[1] - right[1]),
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


def _leading_bracket(
    left: Pair,
    right: Pair,
    v: sp.Symbol,
    t: sp.Symbol,
) -> Pair:
    """Return the first nonzero homogeneous shell of a polynomial bracket."""

    def shells(field: Pair) -> dict[int, Pair]:
        by_degree: dict[int, list[sp.Expr]] = {}
        for component_index, component in enumerate(field):
            for monomial, coefficient in sp.Poly(
                component, v, t
            ).terms():
                degree = sum(monomial)
                if degree not in by_degree:
                    by_degree[degree] = [
                        sp.Integer(0),
                        sp.Integer(0),
                    ]
                by_degree[degree][component_index] += (
                    coefficient * v ** monomial[0] * t ** monomial[1]
                )
        return {
            degree: (sp.expand(parts[0]), sp.expand(parts[1]))
            for degree, parts in by_degree.items()
        }

    left_shells = shells(left)
    right_shells = shells(right)
    candidate_degrees = sorted(
        {
            left_degree + right_degree - 1
            for left_degree in left_shells
            for right_degree in right_shells
        },
        reverse=True,
    )
    for candidate_degree in candidate_degrees:
        shell: Pair = (sp.Integer(0), sp.Integer(0))
        for left_degree, left_shell in left_shells.items():
            right_degree = candidate_degree + 1 - left_degree
            right_shell = right_shells.get(right_degree)
            if right_shell is None:
                continue
            contribution = _bracket(
                left_shell,
                right_shell,
                v,
                t,
            )
            shell = (
                sp.expand(shell[0] + contribution[0]),
                sp.expand(shell[1] + contribution[1]),
            )
        shell = (
            sp.cancel(shell[0]),
            sp.cancel(shell[1]),
        )
        if shell != (0, 0):
            assert _degree(shell, v, t) == candidate_degree
            return shell
    return sp.Integer(0), sp.Integer(0)


def run() -> dict[str, object]:
    data = source_only_connection()
    s, v, t, _ = data["symbols"]
    family_p, family_q = data["family"]
    jacobian = data["jacobian"]
    determinant = data["determinant"]
    source_only = data["source_only"]
    ell = sp.symbols("lambda")

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
    pullback_q2 = _inverse_action(
        jacobian,
        determinant,
        (2 * family_q, sp.Integer(0)),
    )

    # K_star=-(4P^3-18PQ+27Q^2)/12.
    coefficient_p3 = -sp.Rational(1, 36) - ell / 3
    coefficient_pq = 3 * ell / 2
    coefficient_q2 = -sp.Rational(1, 4) - 9 * ell / 4
    pullback: Pair = tuple(
        sp.cancel(
            coefficient_p3 * pullback_p3[index]
            + coefficient_pq * pullback_pq[index]
            + coefficient_q2 * pullback_q2[index]
        )
        for index in range(2)
    )  # type: ignore[assignment]

    profile_polynomial = (
        12 * ell * s**4
        - 144 * ell * s**3
        + 240 * ell * s**2
        + 2304 * ell * s
        + 864 * ell
        + s**4
        - 12 * s**3
        + 20 * s**2
        + 192 * s
        - 576
    )
    scalar = sp.factor(
        6912
        * (s**2 - 3 * s - 8)
        / (
            (s - 6)
            * (s - 4)
            * (s + 4)
            * profile_polynomial
        )
    )
    assert sp.expand(
        profile_polynomial.subs(s, 0) - 288 * (3 * ell - 2)
    ) == 0

    y = sp.symbols("y")

    def divisor_restriction(field: Pair) -> sp.Expr:
        return sp.factor(
            2
            * field[0]
            .subs(t, -1 + sp.Rational(3, 2) * v)
            .subs(v, (y - 3) / 2)
        )

    source_divisor = divisor_restriction(source_only)
    pullback_divisor = divisor_restriction(pullback)
    source_cubic = sp.Poly(
        source_divisor, y
    ).coeff_monomial(y**3)
    pullback_cubic = sp.Poly(
        pullback_divisor, y
    ).coeff_monomial(y**3)
    assert sp.factor(source_cubic - scalar * pullback_cubic) == 0
    assert sp.factor(pullback_cubic.subs({
        s: 0,
        ell: sp.Rational(2, 3),
    })) == 0
    assert source_cubic.subs(s, 0) != 0

    field: Pair = tuple(
        sp.cancel(
            source_only[index] - scalar * pullback[index]
        )
        for index in range(2)
    )  # type: ignore[assignment]
    first = _coefficient(field, s, 0)
    third = _coefficient(field, s, 2)

    g = sp.symbols("g")
    first_coefficient = sp.factor(
        3 * ell / (32 * (3 * ell - 2))
    )
    first_hamiltonian = first_coefficient * (v * g) ** 6
    assert _degree(first, v, t) == 9
    _assert_top_hamiltonian(
        first, first_hamiltonian, v, t, g
    )

    seed = _leading_bracket(first, third, v, t)
    seed_coefficient = sp.factor(
        27 * ell**2 / (4096 * (3 * ell - 2) ** 2)
    )
    seed_hamiltonian = seed_coefficient * v**11 * g**10
    assert _degree(seed, v, t) == 18
    _assert_top_hamiltonian(seed, seed_hamiltonian, v, t, g)

    next_ray = _leading_bracket(first, seed, v, t)
    recurrence_multiplier = sp.factor(
        9 * ell / (16 * (3 * ell - 2))
    )
    next_hamiltonian = (
        seed_coefficient
        * recurrence_multiplier
        * v**16
        * g**13
    )
    assert _degree(next_ray, v, t) == 26
    _assert_top_hamiltonian(
        next_ray, next_hamiltonian, v, t, g
    )

    j = sp.symbols("j", integer=True, nonnegative=True)
    symbolic_multiplier = sp.factor(
        first_coefficient
        * (
            6 * (11 + 5 * j)
            - 6 * (10 + 3 * j)
        )
    )
    assert sp.factor(
        symbolic_multiplier
        - recurrence_multiplier * (2 * j + 1)
    ) == 0

    return {
        "schema": (
            "axiompack.jacobian_weight_three_line_bracket_escape.v1"
        ),
        "target_line": (
            "H_lambda=-Q^2/4-P^3/36+lambda*K_star"
        ),
        "affine_divisor_profile": str(scalar),
        "profile_regular_when": "lambda != 2/3",
        "generic_case": {
            "parameter_condition": "lambda != 0 and lambda != 2/3",
            "first_source_degree": 9,
            "first_weighted_hamiltonian": str(first_hamiltonian),
            "escaping_seed": {
                "word": "[V_0,V_2]",
                "weighted_hamiltonian": str(seed_hamiltonian),
                "source_degree": 18,
            },
            "all_order_ray": {
                "weighted_hamiltonian": (
                    "c_j*v^(11+5*j)*g^(10+3*j)"
                ),
                "coefficient_initial": str(seed_coefficient),
                "coefficient_recurrence": (
                    "c_(j+1)="
                    "9*lambda*(2*j+1)/(16*(3*lambda-2))*c_j"
                ),
                "source_degree": "18+8*j",
                "nonzero_for_every_j": True,
            },
        },
        "exceptional_cases": {
            "lambda=0": (
                "handled by gauge_finite_abelian_orbit_bracket_escape.py"
            ),
            "lambda=2/3": (
                "the target divisor cubic coefficient vanishes at s=0 "
                "while the source cubic coefficient does not, so no "
                "regular scalar profile gives the affine normalization"
            ),
        },
        "claim_boundary": (
            "Every affine-normalized weight-three line has been excluded "
            "from a finite-dimensional source Lie algebra. Target controls "
            "using higher seed-isotropy weights or a non-affine divisor "
            "profile remain outside this classification."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
