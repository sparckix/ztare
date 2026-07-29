#!/usr/bin/env python3
"""Exact cusp/Padé identities behind the gauge-minimized contact problem."""
from __future__ import annotations

import json

import sympy as sp


def run() -> dict[str, object]:
    s, g, w, x, y, z, xi = sp.symbols("s g w x y z xi")
    a = 1 - s / 6
    ell = 1 - s / 4
    mu = sp.cancel(ell / a)
    w_s = sp.cancel(mu * w + (1 - mu) * g)
    x_s = sp.factor(3 * w_s - 1)
    expected_x_s = sp.cancel(
        (ell * x - s * (1 - 3 * g) / 12) / a
    )
    assert sp.cancel(x_s.subs(w, (x + 1) / 3) - expected_x_s) == 0

    raw_p = (
        (2 + s / 2) * z
        + (-3 - 3 * s / 2) * z**2
        + s * z**3
    )
    raw_q = (
        (1 + s / 4) * z**2
        - (2 + s) * z**3
        + 3 * s * z**4 / 4
    )
    p_in_x = sp.expand(raw_p.subs(z, (y + 1) / 3))
    q_in_x = sp.expand(raw_q.subs(z, (y + 1) / 3))
    derivative_factor = (
        2 * s * y**2 - (2 * s + 12) * y - s
    ) / 18
    assert sp.expand(sp.diff(p_in_x, y) - derivative_factor) == 0
    assert sp.expand(
        sp.diff(q_in_x, y) - (y + 1) * derivative_factor / 3
    ) == 0

    d = sp.Symbol("d", positive=True)
    alpha = (s + 6 - d) / (2 * s)
    kappa = s / d
    factored_derivative = -d * xi * (1 - kappa * xi) / 9
    critical_difference = sp.factor(
        derivative_factor.subs(y, xi + alpha)
        - factored_derivative
    )
    assert sp.factor(
        sp.together(critical_difference).as_numer_denom()[0].subs(
            d**2, 3 * s**2 + 12 * s + 36
        )
    ) == 0

    eta_squared = d * xi**2 * (1 - 2 * kappa * xi / 3) / 6
    assert sp.factor(
        -sp.diff(eta_squared, xi) / 3 - factored_derivative
    ) == 0
    shifted_p = sp.expand(p_in_x.subs(y, xi + alpha))
    shifted_q = sp.expand(q_in_x.subs(y, xi + alpha))
    critical_p = sp.expand(shifted_p.subs(xi, 0))
    critical_q = sp.expand(shifted_q.subs(xi, 0))
    tangent_slope = (alpha + 1) / 3

    def reduce_d_relation(value: sp.Expr) -> sp.Expr:
        numerator, denominator = sp.fraction(sp.cancel(value))
        relation = sp.Poly(
            d**2 - (3 * s**2 + 12 * s + 36), d
        )
        reduced_numerator = sp.rem(
            sp.Poly(numerator, d), relation
        ).as_expr()
        reduced_denominator = sp.rem(
            sp.Poly(denominator, d), relation
        ).as_expr()
        return sp.factor(reduced_numerator / reduced_denominator)

    quadratic_normal_form = reduce_d_relation(
        shifted_p - critical_p + eta_squared / 3
    )
    assert quadratic_normal_form == 0
    tangent_remainder = reduce_d_relation(
        shifted_q
        - critical_q
        - tangent_slope * (shifted_p - critical_p)
    )
    expected_tangent_remainder = (
        xi**3 * (-4 * d + 3 * s * xi) / 324
    )
    assert reduce_d_relation(
        tangent_remainder - expected_tangent_remainder
    ) == 0

    u = sp.symbols("u")
    seed_x = u**2 - (u + 1) * z
    seed_y = u**3 - sp.Rational(3, 2) * u * (u + 1) * z
    compactified_jacobian = sp.factor(
        sp.diff(seed_x, z) * sp.diff(seed_y, u)
        - sp.diff(seed_x, u) * sp.diff(seed_y, z)
    )
    assert compactified_jacobian == (
        sp.Rational(3, 2) * z * (u + 1) ** 2
    )

    # Pull a generic target Hamiltonian vector (K_Y,-K_X) back through the
    # compactified seed.  Its simple-pole residues are not independent.
    k_x, k_y = sp.symbols("K_X K_Y")
    target_vector = sp.Matrix([k_y, -k_x])
    seed_jacobian = sp.Matrix([
        [sp.diff(seed_x, z), sp.diff(seed_x, u)],
        [sp.diff(seed_y, z), sp.diff(seed_y, u)],
    ])
    pulled_vector = [
        sp.cancel(item)
        for item in seed_jacobian.inv() * target_vector
    ]
    target_z_residue = sp.factor(
        sp.cancel(z * pulled_vector[0]).subs(z, 0)
    )
    target_u_residue = sp.factor(
        sp.cancel(z * pulled_vector[1]).subs(z, 0)
    )
    joint_residue = sp.factor(
        (u + 1) * target_z_residue
        - 2 * u * target_u_residue
    )
    assert joint_residue == 0

    cusp_parameter = sp.Symbol("r")
    target_x, target_y = sp.symbols("X Y")
    discriminant = target_y**2 - target_x**3
    kx, ky = sp.symbols("K_X K_Y")
    discriminant_x = sp.diff(discriminant, target_x).subs({
        target_x: cusp_parameter**2,
        target_y: cusp_parameter**3,
    })
    discriminant_y = sp.diff(discriminant, target_y).subs({
        target_x: cusp_parameter**2,
        target_y: cusp_parameter**3,
    })
    poisson_generic = sp.expand(discriminant_x * ky - discriminant_y * kx)
    restricted_derivative = (
        2 * cusp_parameter * kx
        + 3 * cusp_parameter**2 * ky
    )
    assert sp.expand(
        poisson_generic
        + cusp_parameter**2 * restricted_derivative
    ) == 0

    n = sp.symbols("n", integer=True, nonnegative=True)
    predicted_coefficient = (
        sp.binomial(sp.Rational(1, 2), n)
        * (-sp.Rational(1, 9)) ** n
    )
    first_coefficients = [
        sp.simplify(predicted_coefficient.subs(n, index))
        for index in range(1, 9)
    ]
    assert all(item != 0 for item in first_coefficients)

    return {
        "schema": "axiompack.jacobian_cusp_pade_mechanism.v1",
        "normalization_coordinate": {
            "a": str(a),
            "ell": str(ell),
            "mu": str(mu),
            "x_s": str(expected_x_s),
        },
        "critical_derivative": str(derivative_factor),
        "critical_factorization_mod_d_relation": str(
            factored_derivative
        ),
        "eta_squared": str(eta_squared),
        "integrated_cusp_normal_form": {
            "p_minus_critical": "-eta_squared/3",
            "tangent_slope": str(tangent_slope),
            "q_tangent_remainder": str(
                expected_tangent_remainder
            ),
            "parameter_coefficient_degree_mechanism": (
                "eta=xi*sqrt(d/6)*sqrt(1-2*s*xi/(3*d)); "
                "its coefficient of s^n has xi-degree at most n+1"
            ),
        },
        "compactified_seed": {
            "X": str(seed_x),
            "Y": str(seed_y),
            "jacobian": str(compactified_jacobian),
        },
        "target_simple_pole_residues": {
            "z_times_dz_at_z0": str(target_z_residue),
            "z_times_du_at_z0": str(target_u_residue),
            "joint_invariant": (
                "(u+1)*Res(dz)-2*u*Res(du)=0"
            ),
        },
        "cusp_poisson_identity": (
            "{Y^2-X^3,K}|cusp = -r^2*d(K(r^2,r^3))/dr"
        ),
        "normalization_top_coefficient_formula": (
            "binomial(1/2,n)*(-1/9)^n"
        ),
        "normalization_top_coefficients_n1_to_n8": [
            str(item) for item in first_coefficients
        ],
        "order_seven_derivative_convention_prediction": str(
            sp.factorial(7) * first_coefficients[6]
        ),
        "triangularity_boundary": (
            "the exact identities do not yet prove that the normalization "
            "top coefficient survives the full Hamiltonian/source BCH "
            "quotient at every order"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
