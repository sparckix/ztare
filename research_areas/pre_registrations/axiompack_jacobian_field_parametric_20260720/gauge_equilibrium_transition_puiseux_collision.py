#!/usr/bin/env python3
"""Exact local equilibrium-transition collision with the critical 5/2 shell.

This replay checks a local selected-Julia mechanism only.  It does not
construct a global time-one factorization of the Jacobian critical holonomy.
"""

from __future__ import annotations

import hashlib
import json

import sympy as sp


def _coefficients_zero(
    expression: sp.Expr,
    variable: sp.Symbol,
    first: int,
    stop: int,
) -> bool:
    expanded = sp.expand(expression)
    return all(expanded.coeff(variable, order) == 0 for order in range(first, stop))


def build_certificate() -> dict[str, object]:
    t, z = sp.symbols("t z")

    # Both generators belong to x^2 Q[x].  The extra rational root controls
    # the derivative ratio between the two selected simple equilibria.
    inner_generator = sp.expand(z**2 * (z - 1) * (z - 2) * (11 * z - 19))
    outer_generator = sp.expand(z**2 * (z - 2) * (z - 3) * (35 * z - 97))

    inner_ratio = sp.cancel(
        sp.diff(inner_generator, z).subs(z, 2)
        / sp.diff(inner_generator, z).subs(z, 1)
    )
    outer_ratio = sp.cancel(
        sp.diff(outer_generator, z).subs(z, 3)
        / sp.diff(outer_generator, z).subs(z, 2)
    )
    assert inner_ratio == sp.Rational(3, 2)
    assert outer_ratio == sp.Rational(2, 3)
    assert sp.rem(inner_generator, z**2, z) == 0
    assert sp.rem(outer_generator, z**2, z) == 0

    # The common uniformizer is u=t^2.  The inner branch moves from the
    # equilibrium 1 to the equilibrium 2 and starts with t^3=u^(3/2).
    source = 1 + t**2
    hidden = (
        2
        + t**3
        + sp.Rational(9, 16) * t**5
        + sp.Rational(17, 3) * t**6
        + sp.Rational(1047, 512) * t**7
    )
    inner_julia_residual = sp.series(
        sp.diff(hidden, t) * inner_generator.subs(z, source)
        - sp.diff(source, t) * inner_generator.subs(z, hidden),
        t,
        0,
        9,
    ).removeO()
    assert _coefficients_zero(inner_julia_residual, t, 4, 9)

    # The outer branch moves from the shared equilibrium 2 to 3.  Solving its
    # parameterized Julia identity on the carried hidden branch gives a
    # composition with a linear u term and first odd t shell at t^5=u^(5/2).
    endpoint = (
        3
        + t**2
        + sp.Rational(77, 12) * t**4
        + sp.Rational(376, 81) * t**5
        + sp.Rational(2227, 48) * t**6
    )
    outer_julia_residual = sp.series(
        sp.diff(endpoint, t) * outer_generator.subs(z, hidden)
        - sp.diff(hidden, t) * outer_generator.subs(z, endpoint),
        t,
        0,
        9,
    ).removeO()
    assert _coefficients_zero(outer_julia_residual, t, 4, 9)

    endpoint_displacement = sp.expand(endpoint - 3)
    assert endpoint_displacement.coeff(t, 2) == 1
    assert endpoint_displacement.coeff(t, 3) == 0
    assert endpoint_displacement.coeff(t, 5) == sp.Rational(376, 81)

    certificate: dict[str, object] = {
        "schema": "axiompack.equilibrium_transition_puiseux_collision.v1",
        "claim_boundary": (
            "exact local selected-Julia adversary; no global time-one "
            "factorization or Jacobian endpoint arithmetic"
        ),
        "inner_generator": str(sp.factor(inner_generator)),
        "outer_generator": str(sp.factor(outer_generator)),
        "generators_divisible_by_x_squared": True,
        "inner_equilibria": [1, 2],
        "outer_equilibria": [2, 3],
        "inner_derivative_ratio": str(inner_ratio),
        "outer_derivative_ratio": str(outer_ratio),
        "ratio_product": str(sp.cancel(inner_ratio * outer_ratio)),
        "uniformizer": "u=t^2",
        "inner_branch_displacement": str(sp.expand(hidden - 2)),
        "composed_endpoint_displacement": str(endpoint_displacement),
        "composed_linear_coefficient": str(endpoint_displacement.coeff(t, 2)),
        "lower_fractional_u_3_over_2_coefficient": str(
            endpoint_displacement.coeff(t, 3)
        ),
        "first_fractional_exponent": "5/2",
        "first_fractional_coefficient": str(endpoint_displacement.coeff(t, 5)),
        "inner_julia_checked_through_t_order": 8,
        "outer_julia_checked_through_t_order": 8,
        "consequence": (
            "the linear-plus-5/2 Puiseux signature does not by itself "
            "exclude two finite equilibrium-transition branches"
        ),
    }
    payload = json.dumps(certificate, sort_keys=True, separators=(",", ":"))
    certificate["certificate_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
    return certificate


if __name__ == "__main__":
    print(json.dumps(build_certificate(), indent=2, sort_keys=True))
