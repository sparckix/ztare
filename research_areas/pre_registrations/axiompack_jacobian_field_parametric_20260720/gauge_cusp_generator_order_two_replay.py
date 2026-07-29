#!/usr/bin/env python3
"""Replay the corrected cusp/Padé contact at parameter order two."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_minimized_fourth_jet import _family_jets  # noqa: E402
from gauge_minimized_third_jet import (  # noqa: E402
    _compose,
    _hamiltonian_field,
    _substitute,
    run as run_third,
)


def _degree(
    value: sp.Expr, v: sp.Symbol, t: sp.Symbol
) -> int:
    if value == 0:
        return -1
    return int(
        sp.Poly(value, v, t, domain=sp.QQ).total_degree()
    )


def run() -> dict[str, object]:
    v, t, p, q = sp.symbols("v t P Q")
    gamma = 1 - sp.Rational(3, 2) * v + t
    x = 3 * (1 + v) * gamma - 1

    prefix = run_third(
        maximum_source_degree=5,
        maximum_third_hamiltonian_degree=4,
    )
    witness = prefix["witness"]
    y2 = tuple(
        sp.sympify(component, locals={"v": v, "t": t})
        for component in witness["Y2"]
    )
    k2 = sp.sympify(
        witness["K2"], locals={"P": p, "Q": q}
    )
    assert max(_degree(component, v, t) for component in y2) == 5

    # Derivative-normalized coefficient d^2/ds^2 at s=0 of the exact
    # projective Padé coordinate after composition with x_s.
    cusp_u2 = -(
        (x - 2) * (18 * gamma + x**2 - 7 * x - 8)
    ) / 324

    y2_gamma = sp.expand(
        -sp.Rational(3, 2) * y2[0] + y2[1]
    )
    y2_x = sp.expand(
        y2[0] * sp.diff(x, v)
        + y2[1] * sp.diff(x, t)
    )
    difference = sp.expand(y2_x - cusp_u2)
    assert sp.expand(
        difference.subs(t, sp.Rational(3, 2) * v - 1)
    ) == 0
    correction_a2 = sp.factor(sp.cancel(difference / gamma))
    assert sp.denom(correction_a2).is_number
    assert _degree(correction_a2, v, t) == 5
    assert sp.expand(
        cusp_u2 + gamma * correction_a2 - y2_x
    ) == 0

    # The source logarithm starts at s^2 Y2/2, so at this order its map
    # and instantaneous coefficients coincide.  The weighted-area
    # companion is R2=Y2(gamma^2/2)=gamma*Y2(gamma).
    r2 = sp.expand(gamma * y2_gamma)
    weighted_divergence = sp.expand(
        sp.diff(gamma**2 * y2[0], v)
        + sp.diff(gamma**2 * y2[1], t)
    )
    assert weighted_divergence == 0

    recovered_v2 = sp.cancel(
        y2_x / (3 * gamma)
        - (1 + v) * y2_gamma / gamma
    )
    recovered_t2 = sp.cancel(
        y2_gamma + sp.Rational(3, 2) * recovered_v2
    )
    assert sp.expand(recovered_v2 - y2[0]) == 0
    assert sp.expand(recovered_t2 - y2[1]) == 0

    # Shifted Rees linearization of the contact equation:
    # F2 = X1^2(F0) + X2(F0) + dF0 Y2.
    data = _family_jets(2)
    p0, q0 = data["P"][0], data["Q"][0]
    family2 = data["P"][2], data["Q"][2]
    jacobian0 = sp.Matrix([
        [sp.diff(p0, v), sp.diff(p0, t)],
        [sp.diff(q0, v), sp.diff(q0, t)],
    ])
    x1 = (-q / 2, p**2 / 12)
    x2 = _hamiltonian_field(k2, p, q)
    x1_squared_at = _substitute(
        _compose(x1, x1, p, q), p, q, p0, q0
    )
    x2_at = _substitute(x2, p, q, p0, q0)
    source_at = tuple(
        sp.expand(component)
        for component in jacobian0 * sp.Matrix(y2)
    )
    predicted2 = tuple(
        sp.expand(
            x1_squared_at[index]
            + x2_at[index]
            + source_at[index]
        )
        for index in range(2)
    )
    assert all(
        sp.expand(actual - predicted) == 0
        for actual, predicted in zip(
            family2, predicted2, strict=True
        )
    )

    return {
        "schema": (
            "axiompack.jacobian_cusp_generator_order_two_replay.v1"
        ),
        "filtration": {
            "logarithm_order": 2,
            "instantaneous_parameter_power": 1,
            "allowed_degree": 5,
            "actual_Y2_degrees": [
                _degree(component, v, t)
                for component in y2
            ],
        },
        "pade_correction": {
            "cusp_U2": str(sp.factor(cusp_u2)),
            "A2": str(correction_a2),
            "A2_degree": _degree(correction_a2, v, t),
            "difference_divisible_by_gamma": True,
            "corrected_U2_equals_Y2_x": True,
        },
        "weighted_area": {
            "R2": str(sp.factor(r2)),
            "weighted_divergence": str(weighted_divergence),
            "recovers_Y2": True,
        },
        "target_descent": {
            "K2": str(k2),
            "linear_infinitesimal_equation_replay": True,
        },
        "next_boundary": (
            "derive the general shifted-Rees recursion for A_n and test "
            "whether gamma divisibility and polynomial target descent "
            "persist at arbitrary order"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
