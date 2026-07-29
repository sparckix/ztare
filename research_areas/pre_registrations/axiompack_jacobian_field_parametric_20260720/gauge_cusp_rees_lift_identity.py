#!/usr/bin/env python3
"""Generic weighted-area and gamma-divisibility identities for the cusp lift."""
from __future__ import annotations

import json

import sympy as sp


def run() -> dict[str, object]:
    v, gamma, s, x = sp.symbols("v gamma s x")
    source_v = sp.Function("source_v")(v, gamma)
    source_gamma = sp.Function("source_gamma")(v, gamma)
    divergence = (
        sp.diff(source_v, v)
        + sp.diff(source_gamma, gamma)
    )
    weighted_constraint = sp.expand(
        2 * source_gamma + gamma * divergence
    )

    source_x = sp.expand(
        3 * gamma * source_v
        + 3 * (1 + v) * source_gamma
    )
    source_r = sp.expand(gamma * source_gamma)

    # Here d/dx|gamma=(3 gamma)^-1 d/dv|gamma and
    # d/dgamma|x=d/dgamma|v-(1+v)/gamma d/dv|gamma.
    gamma_source_x_x = sp.expand(
        sp.diff(source_x, v) / 3
    )
    source_r_gamma_at_x = sp.expand(
        sp.diff(source_r, gamma)
        - (1 + v) * sp.diff(source_r, v) / gamma
    )
    linear_area = sp.simplify(
        gamma_source_x_x + source_r_gamma_at_x
    )
    assert sp.expand(linear_area - weighted_constraint) == 0

    weighted_divergence = sp.expand(
        gamma**2 * sp.diff(source_v, v)
        + sp.diff(gamma**2 * source_gamma, gamma)
    )
    assert sp.expand(
        weighted_divergence
        - gamma * weighted_constraint
    ) == 0

    tangent_x_quotient = (
        3 * source_v
        - sp.Rational(3, 2) * (1 + v) * divergence
    )
    assert sp.expand(
        source_x
        - gamma * tangent_x_quotient
        - sp.Rational(3, 2)
        * (1 + v)
        * weighted_constraint
    ) == 0

    tangent_r_quotient = -divergence / 2
    assert sp.expand(
        source_r
        - gamma**2 * tangent_r_quotient
        - gamma * weighted_constraint / 2
    ) == 0

    a = 1 - s / 6
    ell = 1 - s / 4
    family_x = sp.cancel(
        (
            ell * x
            - s * (1 - 3 * gamma) / 12
        )
        / a
    )
    exceptional_restriction = sp.cancel(
        family_x.subs({x: -1, gamma: 0})
    )
    assert exceptional_restriction == -1

    return {
        "schema": "axiompack.jacobian_cusp_rees_lift_identity.v1",
        "weighted_divergence_factorization": (
            "div(gamma^2 V)=gamma*(2 V(gamma)+gamma div(V))"
        ),
        "linear_canonical_area_identity": (
            "r_gamma|x + gamma*u_x|gamma "
            "= 2 V(gamma)+gamma div(V)"
        ),
        "under_weighted_divergence_zero": {
            "V_x": (
                "gamma*(3 V_v - 3*(1+v)*div(V)/2)"
            ),
            "V_R": "-gamma^2*div(V)/2",
            "gamma_tangency": True,
            "weighted_area_companion_polynomial": True,
        },
        "family_x_on_exceptional_divisor": str(
            exceptional_restriction
        ),
        "all_order_consequence": (
            "each polynomial shifted-Rees source velocity admits a "
            "polynomial gamma-divisible correction of the cusp coordinate; "
            "the remaining obstruction is polynomial target descent"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
