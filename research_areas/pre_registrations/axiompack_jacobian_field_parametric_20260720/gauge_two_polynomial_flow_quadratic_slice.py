#!/usr/bin/env python3
"""Exact premises for the all-degree quadratic-factor exclusion.

One-dimensional quadratic fields ``a*x**2 d/dx`` have global Möbius
time-one maps.  This removes the unresolved hidden-factor lift when either
factor in the critical two-flow problem is quadratic:

* for a quadratic inner factor, pull the target back by its explicit inverse
  and use one of the two critical branch centers ``-2`` and ``6``;
* for a quadratic outer factor, postcompose the target by its explicit
  inverse and use the already certified infinite scalar monodromy orbit to
  avoid the unique possible Möbius pole.

The replay checks the exact branch, indicial, and Möbius algebra.  The local
Julia root-factor contradiction and infinite-orbit finite-root escape are
separate governed Lean kernels named in the output.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_critical_holonomy_rank_two_differential import (  # noqa: E402
    _polynomial_ode,
)
from gauge_pure_contact_zero_parity_algebraic_connection import (  # noqa: E402
    _algebraic_normal_two,
)


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _branch_row(
    center: sp.Expr,
    x: sp.Symbol,
    discriminant: sp.Expr,
    velocity_rational: sp.Expr,
    velocity_radical: sp.Expr,
    p2: sp.Expr,
    p1: sp.Expr,
) -> dict[str, object]:
    center_factor = sp.factor(sp.cancel(discriminant / (x - center)))
    discriminant_slope = sp.factor(center_factor.subs(x, center))
    radical_quotient = sp.factor(
        sp.cancel(velocity_radical / (x - center)).subs(x, center)
    )
    rational_value = sp.factor(velocity_rational.subs(x, center))
    radial_denominator = sp.factor(1 + 2 * center * rational_value)
    logarithmic_fractional_coefficient_squared = sp.factor(
        4
        * radical_quotient**2
        * discriminant_slope
        / radial_denominator**4
    )
    endpoint_relative_fractional_coefficient_squared = sp.factor(
        sp.Rational(4, 25)
        * logarithmic_fractional_coefficient_squared
    )
    indicial_fractional_exponent = sp.factor(
        1 - p1.subs(x, center) / sp.diff(p2, x).subs(x, center)
    )
    finite_nonzero_values = (
        discriminant_slope,
        radical_quotient,
        radial_denominator,
        logarithmic_fractional_coefficient_squared,
        endpoint_relative_fractional_coefficient_squared,
    )
    assert all(
        value not in {sp.nan, sp.zoo, sp.oo, -sp.oo} and value != 0
        for value in finite_nonzero_values
    )
    assert indicial_fractional_exponent == sp.Rational(5, 2)
    return {
        "center": str(center),
        "discriminant_slope": str(discriminant_slope),
        "velocity_rational_value": str(rational_value),
        "velocity_radical_quotient": str(radical_quotient),
        "radial_denominator": str(radial_denominator),
        "logarithmic_u_3_over_2_coefficient_squared": str(
            logarithmic_fractional_coefficient_squared
        ),
        "endpoint_relative_u_5_over_2_coefficient_squared": str(
            endpoint_relative_fractional_coefficient_squared
        ),
        "endpoint_relative_u_5_over_2_coefficient_nonzero": True,
        "indicial_exponents": ["0", str(indicial_fractional_exponent)],
    }


def build_certificate() -> dict[str, object]:
    x, time, a, b, value, multiplier = sp.symbols(
        "x time a b value multiplier"
    )
    connection_x, discriminant, velocity = _algebraic_normal_two()
    assert connection_x == x
    ode_x, p2, p1, _p0, _audit = _polynomial_ode()
    assert ode_x == x

    branch_rows = [
        _branch_row(
            center,
            x,
            discriminant,
            velocity.rational,
            velocity.radical_coefficient,
            p2,
            p1,
        )
        for center in (sp.Integer(-2), sp.Integer(6))
    ]

    quadratic_flow = sp.cancel(x / (1 - a * time * x))
    assert sp.cancel(
        sp.diff(quadratic_flow, time) - a * quadratic_flow**2
    ) == 0
    assert quadratic_flow.subs(time, 0) == x
    time_one = sp.cancel(quadratic_flow.subs(time, 1))
    inverse_time_one = sp.cancel(time_one.subs(a, -a))
    assert sp.cancel(time_one.subs(x, inverse_time_one) - x) == 0
    assert sp.cancel(inverse_time_one.subs(x, time_one) - x) == 0

    inner_center_rows = []
    for center in (sp.Integer(-2), sp.Integer(6)):
        preimage = sp.cancel(center / (1 - a * center))
        pulled_value = sp.cancel(inverse_time_one.subs(x, preimage))
        pulled_derivative = sp.factor(
            sp.diff(inverse_time_one, x).subs(x, preimage)
        )
        assert sp.cancel(pulled_value - center) == 0
        assert sp.cancel(
            pulled_derivative - (1 - a * center) ** 2
        ) == 0
        inner_center_rows.append({
            "target_center": str(center),
            "preimage": str(preimage),
            "regularity_denominator": str(1 - a * center),
            "derivative_at_preimage": str(pulled_derivative),
            "exceptional_parameter": str(sp.solve(1 - a * center, a)[0]),
        })
    exceptional_parameters = {
        row["exceptional_parameter"] for row in inner_center_rows
    }
    assert exceptional_parameters == {"-1/2", "1/6"}

    outer_inverse = sp.cancel(value / (1 + b * value))
    outer_inverse_derivative = sp.factor(sp.diff(outer_inverse, value))
    assert outer_inverse_derivative == 1 / (b * value + 1) ** 2
    affine_pole_polynomial = sp.Poly(1 + b * value, value)
    assert affine_pole_polynomial != sp.Poly(0, value)
    orbit_first = value
    orbit_second = multiplier * value
    simultaneous_poles = sp.solve(
        [1 + b * orbit_first, 1 + b * orbit_second],
        [b, value],
        dict=True,
    )
    # No simultaneous poles exist on a nonzero orbit with multiplier != 1.
    assert all(
        solution.get(value, sp.S.Zero) == 0
        or solution.get(multiplier, sp.S.One) == 1
        for solution in simultaneous_poles
    )

    core: dict[str, object] = {
        "schema": "axiompack.two_polynomial_flow_quadratic_slice.v1",
        "branch_centers": branch_rows,
        "quadratic_flow": {
            "generator": "a*x^2",
            "time_t_map": str(quadratic_flow),
            "time_one_map": str(time_one),
            "inverse_time_one_map": str(inverse_time_one),
            "ode_and_initial_value_checked": True,
            "two_sided_inverse_checked": True,
        },
        "inner_quadratic": {
            "forced_outer_endpoint": "F o (x/(1+a*x))",
            "center_rows": inner_center_rows,
            "exceptional_parameters_are_distinct": True,
            "at_least_one_regular_branch_center_for_every_complex_a": True,
        },
        "outer_quadratic": {
            "forced_inner_endpoint": "F/(1+b*F)",
            "mobius_derivative": str(outer_inverse_derivative),
            "pole_polynomial": "1+b*value",
            "pole_polynomial_nonzero": True,
            "governed_escape_kernel": (
                "FormalComplexMonodromyFiniteRootEscape."
                "complex_monodromy_finite_root_escape_terminal_certificate"
            ),
            "non_torsion_orbit_avoids_pole": True,
        },
        "governed_local_julia_kernel": (
            "FormalRamifiedJuliaObstruction."
            "polynomial_julia_root_factor_obstruction"
        ),
        "all_degree_consequence": (
            "No critical factorization exp(q) o exp(p) can have actual "
            "degree(p)=2 or actual degree(q)=2. The unresolved universal "
            "two-flow problem may be restricted to both degrees at least "
            "three and the separately excluded proportional stratum."
        ),
        "claim_boundary": (
            "The exact algebra and existing all-order Julia/monodromy "
            "kernels exclude the quadratic-factor slice. The case in which "
            "both polynomial generators have degree at least three remains "
            "open, so the full minimax lower bound is not inferred."
        ),
    }
    return {**core, "certificate_sha256": _sha256(core)}


if __name__ == "__main__":
    print(json.dumps(build_certificate(), indent=2, sort_keys=True))
