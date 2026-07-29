#!/usr/bin/env python3
"""Bounded exact replay of the fixed-slice global Magnus ray.

The calculation certifies only logarithmic orders six through eight for one
explicit target-relative source connection.  It does not assert an
all-order recurrence or a minimax lower bound.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
SRC_ROOT = HERE.parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gauge_regular_singular_connection import (  # noqa: E402
    _inverse_action,
    source_only_connection,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    FormalLieOps,
    VelocityPlacement,
    magnus_from_velocity,
    velocity_from_magnus,
)


Pair = tuple[sp.Expr, sp.Expr]


def _degree(field: Pair, v: sp.Symbol, t: sp.Symbol) -> int:
    return max(
        -1 if item == 0 else int(sp.Poly(item, v, t).total_degree())
        for item in field
    )


def _top_homogeneous(
    field: Pair,
    v: sp.Symbol,
    t: sp.Symbol,
) -> Pair:
    degree = _degree(field, v, t)
    if degree < 0:
        return field
    result = []
    for item in field:
        polynomial = sp.Poly(item, v, t)
        result.append(
            sp.Add(*[
                coefficient * v ** monomial[0] * t ** monomial[1]
                for monomial, coefficient in polynomial.terms()
                if sum(monomial) == degree
            ])
        )
    return sp.expand(result[0]), sp.expand(result[1])


def _bracket(
    left: Pair,
    right: Pair,
    v: sp.Symbol,
    t: sp.Symbol,
) -> Pair:
    return tuple(
        sp.expand(
            left[0] * sp.diff(right[index], v)
            + left[1] * sp.diff(right[index], t)
            - right[0] * sp.diff(left[index], v)
            - right[1] * sp.diff(left[index], t)
        )
        for index in range(2)
    )  # type: ignore[return-value]


def _field_from_weighted_hamiltonian(
    hamiltonian: sp.Expr,
    v: sp.Symbol,
    t: sp.Symbol,
    g: sp.Symbol,
) -> Pair:
    v_component = sp.cancel(sp.diff(hamiltonian, g) / g**2)
    g_component = sp.cancel(-sp.diff(hamiltonian, v) / g**2)
    t_component = sp.cancel(
        (g_component + 3 * v_component) / 2
    )
    substitution = {g: 2 * t - 3 * v}
    return (
        sp.expand(v_component.subs(substitution)),
        sp.expand(t_component.subs(substitution)),
    )


def _sha(field: Pair) -> list[str]:
    return [
        hashlib.sha256(
            str(sp.expand(item)).encode("utf-8")
        ).hexdigest()
        for item in field
    ]


def run() -> dict[str, object]:
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
    pullback_q2 = _inverse_action(
        jacobian,
        determinant,
        (2 * family_q, sp.Integer(0)),
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
    velocity_field: Pair = tuple(
        sp.cancel(
            source_only[index]
            - coefficient_p3 * pullback_p3[index]
            - coefficient_pq * pullback_pq[index]
            + sp.Rational(1, 4) * pullback_q2[index]
        )
        for index in range(2)
    )  # type: ignore[assignment]
    assert all(
        sp.factor(item.subs(s, 0)) == 0
        for item in velocity_field
    )

    maximum_order = 8
    expanded_series = [
        sp.series(item, s, 0, maximum_order)
        .removeO()
        .expand()
        for item in velocity_field
    ]
    velocity: list[Pair] = [
        tuple(
            sp.expand(expanded_series[index].coeff(s, order))
            for index in range(2)
        )
        for order in range(maximum_order)
    ]  # type: ignore[assignment]
    ops = FormalLieOps[Pair](
        zero=lambda: (sp.Integer(0), sp.Integer(0)),
        add=lambda left, right: (
            sp.expand(left[0] + right[0]),
            sp.expand(left[1] + right[1]),
        ),
        scale=lambda value, scalar: (
            sp.expand(
                sp.Rational(scalar.numerator, scalar.denominator) * value[0]
            ),
            sp.expand(
                sp.Rational(scalar.numerator, scalar.denominator) * value[1]
            ),
        ),
        bracket=lambda left, right: _bracket(left, right, v, t),
    )
    logarithm = magnus_from_velocity(
        velocity,
        maximum_order,
        ops,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    replay = velocity_from_magnus(
        logarithm,
        maximum_order,
        ops,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    assert all(
        all(
            sp.expand(replay[order][component] - velocity[order][component])
            == 0
            for component in range(2)
        )
        for order in range(maximum_order)
    )

    velocity_degrees = [
        _degree(item, v, t) for item in velocity
    ]
    logarithm_degrees = [
        _degree(logarithm[order], v, t)
        for order in range(1, maximum_order + 1)
    ]
    assert velocity_degrees == [-1, 11, 13, 15, 15, 15, 15, 15]
    assert logarithm_degrees == [-1, 11, 13, 15, 17, 22, 24, 26]

    g = sp.symbols("g")
    ray_hamiltonians = {
        6: sp.Rational(1, 1048576) * v**13 * g**12,
        7: -sp.Rational(619, 1321205760) * v**14 * g**13,
        8: sp.Rational(343, 6794772480) * v**15 * g**14,
    }
    rows = {}
    for order, hamiltonian in ray_hamiltonians.items():
        top = _top_homogeneous(logarithm[order], v, t)
        expected = _field_from_weighted_hamiltonian(
            hamiltonian,
            v,
            t,
            g,
        )
        assert tuple(
            sp.expand(top[index] - expected[index])
            for index in range(2)
        ) == (0, 0)
        rows[str(order)] = {
            "degree": _degree(top, v, t),
            "top_field": [str(sp.factor(item)) for item in top],
            "weighted_hamiltonian": str(hamiltonian),
            "sha256": _sha(top),
        }

    return {
        "schema": "axiompack.jacobian_controlled_global_magnus.v2",
        "connection": {
            "target_hamiltonian": "a(s)*P^3+b(s)*P*Q-Q^2/4",
            "a(s)": str(coefficient_p3),
            "b(s)": str(coefficient_pq),
            "source_velocity_at_s_zero": ["0", "0"],
        },
        "source_magnus": {
            "flow_equation": "psi_prime = Dpsi * velocity",
            "velocity_placement": (
                VelocityPlacement.RIGHT_MULTIPLY.value
            ),
            "velocity_degrees_parameter_orders_0_to_7": velocity_degrees,
            "logarithm_degrees_orders_1_to_8": logarithm_degrees,
            "ray_orders_6_to_8": rows,
            "forward_dexp_roundtrip": True,
        },
        "finite_claim": (
            "For this explicit connection, the top homogeneous fields "
            "at logarithmic orders 6, 7, and 8 are exactly the three "
            "nonzero weighted-Hamiltonian rays recorded above."
        ),
        "all_order_kill_condition": (
            "At any exact order n>=9, the proposed recurrence is false "
            "if deg(Omega_n) differs from 2*n+10, if its top projection "
            "leaves the ray X_{v^(n+7)g^(n+6)}, or if that ray "
            "coefficient vanishes."
        ),
        "conclusion": (
            "Diagnostic only. Three finite coefficients give no "
            "asymptotic result, and even persistence for this one gauge "
            "would not prove a minimax lower bound beyond the established "
            "sigma_ct <= 2 upper bound."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
