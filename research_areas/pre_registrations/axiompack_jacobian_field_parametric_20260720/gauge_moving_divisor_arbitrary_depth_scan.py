#!/usr/bin/env python3
"""Exact scan of the iterated moving-divisor radial correction.

This is an orientation adapter for the arbitrary-contact-depth induction.
It keeps every normal layer after subtracting the fixed linear radial
section ``T**m``; no quotient or selected-coordinate projection is applied.
"""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_moving_divisor_normal_transition import (  # noqa: E402
    _leak_preimages,
)
from gauge_moving_pullback_normal_semigroup import _exact_family  # noqa: E402


def _coefficient(value: sp.Expr, variable: sp.Symbol, order: int) -> sp.Expr:
    """Return an ordinary power-series coefficient at the origin."""

    return sp.factor(
        sp.diff(value, variable, order).subs(variable, 0)
        / sp.factorial(order)
    )


def _radial_section(
    value: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> sp.Expr:
    """Apply the declared monomial section of the lift ideal once."""

    preimages = _leak_preimages(p, q)

    @lru_cache(maxsize=None)
    def monomial(a: int, b: int) -> sp.Expr:
        if a >= 3:
            return p ** (a - 3) * q**b * preimages["P3"]
        if a >= 1 and b >= 1:
            return p ** (a - 1) * q ** (b - 1) * preimages["PQ"]
        if a == 0 and b >= 2:
            return q ** (b - 2) * preimages["Q2"]
        raise AssertionError(f"monomial P^{a}Q^{b} is outside the lift ideal")

    result = sp.Integer(0)
    for (a, b), coefficient in sp.Poly(
        sp.expand(value), p, q, domain=sp.QQ
    ).terms():
        if coefficient:
            result += coefficient * monomial(a, b)
    return sp.factor(result)


def _iterate_radial_section(
    value: sp.Expr,
    depth: int,
    p: sp.Symbol,
    q: sp.Symbol,
) -> sp.Expr:
    result = value
    for _step in range(depth):
        result = _radial_section(result, p, q)
    return result


def _canonical_symbol(weight: int, p: sp.Expr, q: sp.Expr) -> sp.Expr:
    if weight < 5:
        raise ValueError("weight must be at least five")
    if weight % 2 == 0:
        return p ** (weight // 2)
    return p ** ((weight - 3) // 2) * q


def run(
    minimum_depth: int = 1,
    maximum_depth: int = 4,
    maximum_weight: int = 12,
) -> dict[str, object]:
    if minimum_depth < 1 or maximum_depth < minimum_depth:
        raise ValueError("depth interval must be nonempty and positive")
    if maximum_weight < 6:
        raise ValueError("maximum_weight must be at least six")

    (parameter, u, z), family_p, family_q = _exact_family()
    r, target_p, target_q = sp.symbols("r P Q")
    family_p_rz = sp.factor(family_p.subs(u, r / z))
    family_q_rz = sp.factor(family_q.subs(u, r / z))
    seed_p_rz = sp.factor(family_p_rz.subs(parameter, 0))
    seed_q_rz = sp.factor(family_q_rz.subs(parameter, 0))
    fixed_contact_rz = sp.factor(
        4 * family_p_rz**3
        - family_p_rz**2
        - 18 * family_p_rz * family_q_rz
        + 27 * family_q_rz**2
        + 4 * family_q_rz
    )

    rows = []
    conjecture_passes = True
    for depth in range(minimum_depth, maximum_depth + 1):
        for weight in range(5, maximum_weight + 1):
            target_symbol = _canonical_symbol(weight, target_p, target_q)
            moving_symbol = _canonical_symbol(
                weight, family_p_rz, family_q_rz
            )
            moving_coefficient = _coefficient(
                moving_symbol * fixed_contact_rz**depth,
                parameter,
                depth,
            )
            correction = _iterate_radial_section(
                target_symbol, depth, target_p, target_q
            ).subs({target_p: seed_p_rz, target_q: seed_q_rz})
            residual = sp.factor(moving_coefficient - correction)
            direct_layers: dict[int, sp.Expr] = {}
            for (normal_order, radial_degree), coefficient in sp.Poly(
                sp.expand(residual), z, r, domain=sp.QQ
            ).terms():
                direct_layers[normal_order] = sp.expand(
                    direct_layers.get(normal_order, 0)
                    + coefficient * r**radial_degree
                )
            direct_layers = {
                order: sp.factor(profile)
                for order, profile in direct_layers.items()
                if profile != 0
            }
            orders = sorted(direct_layers)
            odd_orders = [order for order in orders if order % 2 == 1]
            first_order = orders[0] if orders else None
            first_odd_order = odd_orders[0] if odd_orders else None
            odd_profile = (
                direct_layers[first_odd_order]
                if first_odd_order is not None
                else sp.Integer(0)
            )
            odd_polynomial = (
                sp.Poly(odd_profile, r, domain=sp.QQ)
                if odd_profile != 0
                else None
            )
            expected_first_odd = 2 * depth + 1
            row_passes = first_odd_order == expected_first_odd
            conjecture_passes = conjecture_passes and row_passes
            rows.append({
                "contact_depth": depth,
                "weight": weight,
                "normal_orders": orders,
                "first_normal_order": first_order,
                "first_odd_normal_order": first_odd_order,
                "predicted_first_odd_order": expected_first_odd,
                "odd_order_prediction_passes": row_passes,
                "first_odd_radial_degree": (
                    odd_polynomial.degree() if odd_polynomial else None
                ),
                "first_odd_top_coefficient": (
                    str(odd_polynomial.LC()) if odd_polynomial else None
                ),
            })

    return {
        "schema": "axiompack.jacobian_moving_divisor_arbitrary_depth_scan.v1",
        "radial_section": {
            "linear_monomial_section": True,
            "iterate_count_equals_contact_depth": True,
            "complete_normal_remainder_retained": True,
        },
        "hypothesis": {
            "first_odd_normal_order": "2*m+1",
            "passes_orientation_window": conjecture_passes,
        },
        "rows": rows,
        "claim_boundary": (
            "Finite exact orientation scan only. It can falsify the proposed "
            "normal-depth law but cannot establish the all-depth coefficient "
            "recurrence or adapter completeness."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
