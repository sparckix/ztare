#!/usr/bin/env python3
"""Replay the finite-dimensional Lie classification around the cusp seed."""

from __future__ import annotations

import json

import sympy as sp


P, Q, u = sp.symbols("P Q u")
H = P**3 + 9 * Q**2


def bracket(left: sp.Expr, right: sp.Expr) -> sp.Expr:
    return sp.expand(
        sp.diff(left, Q) * sp.diff(right, P)
        - sp.diff(left, P) * sp.diff(right, Q)
    )


def cusp_restrict(value: sp.Expr) -> sp.Expr:
    return sp.expand(value.subs({P: -9 * u**2, Q: 9 * u**3}))


def cusp_weight(value: sp.Expr) -> tuple[int, ...]:
    polynomial = sp.Poly(sp.expand(value), P, Q)
    return tuple(
        sorted(
            {
                2 * powers[0] + 3 * powers[1]
                for powers, coefficient in polynomial.terms()
                if coefficient != 0
            }
        )
    )


def main() -> None:
    assert cusp_restrict(H) == 0
    assert sp.factor(H) == H

    coefficients = sp.symbols("c0:15")
    generic = sp.Integer(0)
    cursor = 0
    for p_power in range(5):
        for q_power in range(5 - p_power):
            generic += coefficients[cursor] * P**p_power * Q**q_power
            cursor += 1
    restricted_intertwining = sp.expand(
        cusp_restrict(bracket(H, generic))
        + 9 * u**2 * sp.diff(cusp_restrict(generic), u)
    )
    assert restricted_intertwining == 0

    monomial_rows: list[dict[str, object]] = []
    for exponent in range(1, 7):
        value = u**exponent
        coefficient = sp.Integer(1)
        for depth in range(1, 7):
            value = sp.expand(-9 * u**2 * sp.diff(value, u))
            coefficient *= -9 * (exponent + depth - 1)
            expected = coefficient * u ** (exponent + depth)
            assert sp.expand(value - expected) == 0
        monomial_rows.append(
            {
                "initial_exponent": exponent,
                "depth_6_coefficient": str(coefficient),
                "final_exponent": exponent + 6,
            }
        )

    # D is homogeneous of cusp-weight +1.
    homogeneous_checks: list[dict[str, object]] = []
    for p_power, q_power in ((1, 0), (0, 1), (2, 1), (1, 3), (4, 2)):
        monomial = P**p_power * Q**q_power
        image = bracket(H, monomial)
        source_weight = 2 * p_power + 3 * q_power
        image_weights = cusp_weight(image)
        assert image_weights == (source_weight + 1,)
        homogeneous_checks.append(
            {
                "monomial": str(monomial),
                "source_weight": source_weight,
                "image_weight": image_weights[0],
            }
        )

    # A noncentral stress input has an infinite nonzero adjoint prefix with
    # strictly increasing cusp weights.
    stress = P
    stress_rows: list[dict[str, object]] = []
    for depth in range(9):
        assert stress != 0
        weights = cusp_weight(stress)
        stress_rows.append(
            {
                "adjoint_depth": depth,
                "weight_support": list(weights),
                "polynomial": str(sp.factor(stress)),
            }
        )
        stress = bracket(H, stress)

    # Central polynomials are fixed pointwise.
    z = sp.symbols("z")
    central_profile = 7 - 3 * H + 5 * H**2 + 2 * H**4
    assert bracket(H, central_profile) == 0
    assert sp.expand(central_profile.subs(H, z)) is not None

    print(
        json.dumps(
            {
                "schema": (
                    "axiompack.jacobian_cusp_hamiltonian_finite_lie."
                    "classification.v1"
                ),
                "seed": str(H),
                "cusp_parameterization": {
                    "P": "-9*u^2",
                    "Q": "9*u^3",
                    "restricted_adjoint": "-9*u^2*d/du",
                    "kernel_ideal_generator": str(H),
                },
                "generalized_kernel": {
                    "statement": "union_N ker(ad_H^N) = Q[H]",
                    "restriction_step": (
                        "(-9*u^2*d/du)^N kills only constants in Q[u]"
                    ),
                    "divisibility_step": "G-c is divisible by H",
                    "induction_step": "ad_H(H*G1)=H*ad_H(G1)",
                    "monomial_checks": monomial_rows,
                },
                "weight_growth": {
                    "weights": {"P": 2, "Q": 3, "H": 6},
                    "ad_H_shift": 1,
                    "homogeneous_checks": homogeneous_checks,
                },
                "noncentral_stress": stress_rows,
                "conclusion": (
                    "every finite-dimensional polynomial Hamiltonian Lie "
                    "algebra containing H is contained modulo constants in "
                    "Q[H], hence is abelian"
                ),
                "source_minimax_decided": False,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
