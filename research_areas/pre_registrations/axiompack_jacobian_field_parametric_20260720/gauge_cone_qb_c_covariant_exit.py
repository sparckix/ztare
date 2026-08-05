#!/usr/bin/env python3
"""Exact cone-exit depth of the target prefixes ``Q^b*C``.

For the normalized seed Hamiltonian

    H0 = -P^3/36 - Q^2/4,

the ``P^3`` branch of ``ad_H0`` maps ``P^a*Q^q`` to

    (q/12) * P^(a+2) * Q^(q-1).

Starting from the unique largest-P monomial ``4*P^3*Q^b`` in ``Q^b*C``
there is therefore a unique all-``P^3`` branch.  Its cone margin detects
the first covariant derivative that cannot be supplied by a later
cone-valued target row.
"""

from __future__ import annotations

from math import factorial
import json

import sympy as sp


P, Q = sp.symbols("P Q")
H_ZERO = -P**3 / 36 - Q**2 / 4
CUSP_KERNEL = (
    4 * P**3
    - P**2
    - 18 * P * Q
    + 27 * Q**2
    + 4 * Q
)


def _bracket(left: sp.Expr, right: sp.Expr) -> sp.Expr:
    return sp.expand(
        sp.diff(left, Q) * sp.diff(right, P)
        - sp.diff(left, P) * sp.diff(right, Q)
    )


def _falling(value: int, depth: int) -> sp.Integer:
    if depth > value:
        return sp.Integer(0)
    return sp.Integer(
        factorial(value) // factorial(value - depth)
    )


def _outside_cone(value: sp.Expr) -> dict[tuple[int, int], sp.Expr]:
    return {
        exponent: coefficient
        for exponent, coefficient in sp.Poly(
            value,
            P,
            Q,
        ).terms()
        if (
            coefficient != 0
            and (
                exponent[1] == 0
                or exponent[0] > 2 * exponent[1]
                or exponent == (0, 1)
            )
        )
    }


def run(maximum_q_exponent: int = 20) -> dict[str, object]:
    if maximum_q_exponent < 6:
        raise ValueError("the replay needs Q exponents through six")
    rows = []
    for q_exponent in range(2, maximum_q_exponent + 1):
        exit_depth = q_exponent // 2
        value = sp.expand(Q**q_exponent * CUSP_KERNEL)
        prefixes = []
        for depth in range(exit_depth + 1):
            if depth:
                value = _bracket(H_ZERO, value)
            expected_exponent = (
                3 + 2 * depth,
                q_exponent - depth,
            )
            expected_coefficient = sp.Rational(
                4 * _falling(q_exponent, depth),
                12**depth,
            )
            actual_coefficient = sp.Poly(
                value,
                P,
                Q,
            ).coeff_monomial(
                P ** expected_exponent[0]
                * Q ** expected_exponent[1]
            )
            assert actual_coefficient == expected_coefficient
            cone_margin = (
                2 * expected_exponent[1]
                - expected_exponent[0]
            )
            outside = _outside_cone(value)
            if depth < exit_depth:
                assert cone_margin >= 1
                assert not outside
            else:
                assert cone_margin < 0
                assert expected_exponent in outside
            prefixes.append({
                "depth": depth,
                "witness_exponent": list(expected_exponent),
                "witness_coefficient": str(
                    expected_coefficient
                ),
                "witness_cone_margin": cone_margin,
                "outside_cone": bool(outside),
            })
        rows.append({
            "q_exponent": q_exponent,
            "first_cone_exit_depth": exit_depth,
            "depth_rows": prefixes,
        })

    return {
        "schema": (
            "axiompack.jacobian_cone_qb_c_"
            "covariant_exit.v1"
        ),
        "seed_hamiltonian": "-P^3/36-Q^2/4",
        "prefix_family": "Q^b*C, b>=2",
        "cone_condition": "P exponent <= 2*Q exponent",
        "all_p3_branch": {
            "exponent_at_depth_n": "(3+2*n,b-n)",
            "coefficient": "4*(b)_n/12^n",
            "cone_margin": "2*b-3-4*n",
        },
        "first_cone_exit_depth": "floor(b/2)",
        "maximum_checked_q_exponent": maximum_q_exponent,
        "rows": rows,
        "claim_boundary": (
            "Exact target cone-exit depth for the pure-Q one-C "
            "prefix family. Transfer of the first target exit to a "
            "nonzero source-Magnus ray is a separate quotient theorem."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
