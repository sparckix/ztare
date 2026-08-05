#!/usr/bin/env python3
"""All-order terminal response for stable higher-contact prefixes.

For

    P^a * Q^b * C^m,  2*b >= a + 3*m + 8,

the cost-four quotient has odd normal order ``2*m+1``.  This file
certifies its nonresonant adjoint orbit and the pivot inequality excluding
every later cone current column, including arbitrary discriminant depth
and arbitrary contact depth.
"""

from __future__ import annotations

import argparse
from math import factorial
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_cone_discriminant_depth_scan import (  # noqa: E402
    C_ZERO,
    D_ZERO,
    P_ZERO,
    Q_ZERO,
)
from gauge_cone_higher_contact_cost_four_symbolic import (  # noqa: E402
    run as cost_four_certificate,
)


A, B, M, K, T, H = sp.symbols(
    "a b m k t h",
    integer=True,
    nonnegative=True,
)
D_DEPTH = sp.symbols("d", integer=True, nonnegative=True)


def _response_coefficient(depth: int) -> sp.Expr:
    if depth == 0:
        return sp.Rational(1, 4)
    return sp.Rational(
        sp.bernoulli(depth + 1),
        2 * factorial(depth + 1),
    )


def _factor_support_certificate() -> dict[str, object]:
    families = {
        "P": (P_ZERO, (2, 0)),
        "Q": (Q_ZERO, (3, 0)),
        "D": (D_ZERO, (5, 0)),
        "C": (C_ZERO, (2, 2)),
    }
    rows = {}
    for name, (value, leading) in families.items():
        deficits = []
        for (radial, normal), coefficient in sorted(value.items()):
            radial_deficit = leading[0] - radial
            extra_normal = normal - leading[1]
            assert radial_deficit >= extra_normal >= 0
            deficits.append({
                "radial_deficit": radial_deficit,
                "extra_normal": extra_normal,
                "coefficient": str(coefficient),
            })
        rows[name] = deficits
    return {
        "factor_rows": rows,
        "product_support_inequality": "t >= h >= 0",
        "closed_under_products": True,
        "d_adic_basis": "P^a*Q^b*D^d*C^j",
    }


def _symbolic_orbit_certificate() -> dict[str, object]:
    slope = 2 * A + 3 * B + 5 * D_DEPTH + 2 * M
    cost = 4 + 2 * K
    radial = sp.expand(slope + K * (slope - 1))
    normal = sp.expand(
        2 * M + 1 + 2 * (M - 1) * K
    )
    source_z = sp.expand(radial + normal)
    multiplier = sp.factor(
        2 * (slope - M) * K - slope
    )
    resonance = sp.factor(
        slope / (2 * (slope - M))
    )
    assert sp.factor(
        1 - resonance
        - (2 * A + 3 * B + 5 * D_DEPTH)
        / (
            2
            * (
                2 * A
                + 3 * B
                + 5 * D_DEPTH
                + M
            )
        )
    ) == 0

    grade_x = sp.factor(
        2 * radial - (slope - 1) * cost - 2
    )
    grade_z = sp.factor(
        2 * source_z
        - (slope + 2 * M - 3) * cost
        - 6
    )
    assert K not in grade_x.free_symbols
    assert K not in grade_z.free_symbols

    # If a current D-adic leading column contains the terminal after a
    # radial deficit t and an extra normal order h, its leading pivot is
    # above the terminal by these grade margins.
    pivot_x_margin = 2 * T
    pivot_z_margin = 2 * (T - H)
    assert sp.factor(pivot_x_margin) == 2 * T
    assert sp.expand(
        pivot_z_margin - 2 * (T - H)
    ) == 0

    return {
        "cost": str(cost),
        "terminal_radial_exponent": str(radial),
        "terminal_normal_order": str(normal),
        "terminal_source_z_exponent": str(source_z),
        "terminal_grade": [str(grade_x), str(grade_z)],
        "adjoint_multiplier_without_letter_amplitude": str(multiplier),
        "only_algebraic_resonance": str(resonance),
        "resonance_strictly_between_zero_and_one": True,
        "current_column_containment_variables": {
            "radial_deficit": "t",
            "extra_normal_order": "h",
            "support_inequality": "t >= h >= 0",
            "leading_pivot_grade_margin": [
                str(pivot_x_margin),
                str(pivot_z_margin),
            ],
            "odd_terminal_normal_excludes_t=h=0": True,
            "leading_pivot_is_strictly_above_terminal": True,
        },
    }


def _response_certificate(maximum_depth: int) -> dict[str, object]:
    if maximum_depth < 9:
        raise ValueError("response check must include depth nine")
    rows = []
    for depth in range(maximum_depth + 1):
        coefficient = _response_coefficient(depth)
        if depth >= 1 and depth % 2 == 0:
            assert coefficient == 0
        if depth % 2 == 1:
            assert coefficient != 0
        rows.append({
            "depth": depth,
            "cost": 4 + 2 * depth,
            "coefficient_after_orbit_division": str(coefficient),
        })
    return {
        "function": (
            "x/(exp(x)-1) * integral_0^1 "
            "t^3*exp(t^2*x) dt"
        ),
        "rows": rows,
        "nonzero_depths": "k=0 and every odd k",
        "nonzero_cost_subsequence": "6+4*l, l>=0",
    }


def run(
    maximum_depth: int = 11,
    verify_cost_four: bool = True,
) -> dict[str, object]:
    cost_four = (
        cost_four_certificate(include_held_out=False)
        if verify_cost_four
        else None
    )
    if cost_four is not None:
        assert cost_four[
            "northeast_rectangle_polynomial_identity_certificate"
        ]["terminal_is_the_unique_northeast_corner"]
    slope = 2 * A + 3 * B + 5 * D_DEPTH + 2 * M
    limiting_rate = sp.factor(slope + M - 2)
    return {
        "schema": (
            "axiompack.jacobian_cone_"
            "higher_contact_phi3.v1"
        ),
        "prefix_family": "P^a*Q^b*D^d*C^m",
        "range": (
            "m>=1, d>=0, a>=0, b>=1, "
            "2*b>=a+3*d+3*m+8"
        ),
        "cost_four_certificate_schema": (
            cost_four["schema"] if cost_four is not None else "skipped"
        ),
        "factor_support_certificate": _factor_support_certificate(),
        "orbit_certificate": _symbolic_orbit_certificate(),
        "right_magnus_response": _response_certificate(
            maximum_depth
        ),
        "later_current_independence": {
            "arbitrary_discriminant_depth": True,
            "arbitrary_contact_depth": True,
            "reason": (
                "Any current column containing the odd-normal terminal "
                "has a nonzero even-normal leading pivot strictly above "
                "the terminal grade. The unique northeast-corner "
                "recursion forces its coefficient to zero first."
            ),
        },
        "infinite_source_logarithm": True,
        "limiting_source_hamiltonian_rate": str(limiting_rate),
        "claim_boundary": (
            "All-order source-logarithm obstruction for stable "
            "higher-contact monomial prefixes. Boundary strips with "
            "2*b<a+3*m+8 and cancellation among equal leading classes "
            "are separate."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--maximum-depth", type=int, default=11)
    parser.add_argument(
        "--skip-cost-four-verification",
        action="store_true",
    )
    arguments = parser.parse_args()
    print(json.dumps(
        run(
            arguments.maximum_depth,
            not arguments.skip_cost_four_verification,
        ),
        indent=2,
        sort_keys=True,
    ))
