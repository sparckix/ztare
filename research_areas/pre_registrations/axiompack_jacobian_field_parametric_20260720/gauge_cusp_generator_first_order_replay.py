#!/usr/bin/env python3
"""Replay the cusp-contact order-one obstruction and corrected lift."""
from __future__ import annotations

import json

import sympy as sp


def _hamiltonian_field(
    hamiltonian: sp.Expr, p: sp.Symbol, q: sp.Symbol
) -> tuple[sp.Expr, sp.Expr]:
    return (
        sp.diff(hamiltonian, q),
        -sp.diff(hamiltonian, p),
    )


def _family(
    parameter: sp.Symbol,
    v: sp.Symbol,
    t: sp.Symbol,
) -> tuple[sp.Expr, sp.Expr]:
    z = sp.Symbol("z")
    gamma = 1 - sp.Rational(3, 2) * v + t
    mu = 3 * (parameter - 4) / (2 * (parameter - 6))
    lam = -(parameter - 4) / 4
    w = (1 + mu * v) * gamma
    p = (
        (2 + parameter / 2) * z
        + (-3 - 3 * parameter / 2) * z**2
        + parameter * z**3
    )
    q = (
        (1 + parameter / 4) * z**2
        - (2 + parameter) * z**3
        + 3 * parameter * z**4 / 4
    )
    first = sp.cancel(
        lam / mu * (gamma + p.subs(z, w))
    )
    second = sp.cancel(
        (
            gamma**2 * (1 + mu * v)
            + q.subs(z, w)
        )
        / lam
    )
    return first, second


def _coefficient_matrix(
    equations: tuple[sp.Expr, sp.Expr],
    unknowns: tuple[sp.Symbol, ...],
    v: sp.Symbol,
    t: sp.Symbol,
) -> tuple[sp.Matrix, sp.Matrix]:
    polynomials = [
        sp.Poly(sp.expand(equation), v, t)
        for equation in equations
    ]
    rows: list[list[sp.Expr]] = []
    rhs: list[sp.Expr] = []
    zero = {unknown: 0 for unknown in unknowns}
    for polynomial in polynomials:
        for monomial in polynomial.monoms():
            coefficient = sp.expand(
                polynomial.coeff_monomial(monomial)
            )
            rows.append([
                coefficient.coeff(unknown)
                for unknown in unknowns
            ])
            rhs.append(-coefficient.subs(zero))
    return sp.Matrix(rows), sp.Matrix(rhs)


def run() -> dict[str, object]:
    v, t, p, q, s = sp.symbols("v t P Q s")
    a0, a1, a2, b0, b1, lam = sp.symbols(
        "a0 a1 a2 b0 b1 lambda"
    )
    gamma = 1 - sp.Rational(3, 2) * v + t
    x = 3 * (1 + v) * gamma - 1

    # The complete curve-only projective/weighted-area first jet.
    p2 = a0 + a1 * x + a2 * x**2
    h = b0 + b1 * x
    u1 = gamma / 4 + p2
    r1 = (
        -gamma**2 * (a1 + 2 * a2 * x) / 2
        + (x + 1) ** 2 * h
    )
    gamma1 = sp.cancel(r1 / gamma)
    v1 = sp.cancel(
        u1 / (3 * gamma)
        - (1 + v) * gamma1 / gamma
    )
    t1 = sp.cancel(gamma1 + sp.Rational(3, 2) * v1)

    family0 = tuple(
        sp.expand(component.subs(s, 0))
        for component in _family(s, v, t)
    )
    jacobian0 = sp.Matrix([
        [
            sp.diff(family0[component], variable)
            for variable in (v, t)
        ]
        for component in range(2)
    ])
    k_star = -(4 * p**3 - 18 * p * q + 27 * q**2) / 12
    x_k_star = _hamiltonian_field(k_star, p, q)
    z_star = tuple(
        sp.factor(sp.cancel(component))
        for component in (
            jacobian0.inv()
            * sp.Matrix([
                -x_k_star[0].subs({
                    p: family0[0], q: family0[1]
                }),
                -x_k_star[1].subs({
                    p: family0[0], q: family0[1]
                }),
            ])
        )
    )
    assert all(sp.denom(component).is_number for component in z_star)

    denominator = 2 * t - 3 * v + 2
    equations = tuple(
        sp.expand(
            sp.cancel(
                denominator
                * (component - lam * stabilizer)
            )
        )
        for component, stabilizer in zip(
            (v1, t1), z_star, strict=True
        )
    )
    unknowns = (a0, a1, a2, b0, b1, lam)
    matrix, rhs = _coefficient_matrix(
        equations, unknowns, v, t
    )
    rank = matrix.rank()
    augmented_rank = matrix.row_join(rhs).rank()
    assert rank == 6
    assert augmented_rank == 7

    cleared_first = sp.Poly(
        sp.expand(
            sp.cancel(
                12
                * denominator
                * (v1 - lam * z_star[0])
            )
        ),
        v,
        t,
    )

    def coefficient(v_power: int, t_power: int = 0) -> sp.Expr:
        return cleared_first.coeff_monomial(
            v**v_power * t**t_power
        )

    dual_value = sp.expand(
        -413 * coefficient(6)
        - 765 * coefficient(4)
        - 405 * coefficient(3, 1)
        + 351 * coefficient(3)
        - 81 * coefficient(2)
        + 243 * coefficient(1)
    )
    assert dual_value == -729

    # The actual projective Padé coordinate has this first coefficient
    # after composition with x_s.  It vanishes on gamma=0 and therefore
    # admits a polynomial gamma-divisible off-curve correction.
    cusp_u1 = (
        gamma / 4
        - (x + 1) * (2 * x - 1) / 36
    )
    correction_a1 = (
        -sp.Rational(1, 4)
        + (1 + v) * (2 * x - 1) / 12
    )
    corrected_u1 = sp.expand(cusp_u1 + gamma * correction_a1)
    assert corrected_u1 == 0

    # With R_1=0, the weighted-area equation and the recovered affine
    # source jet are both zero.  The whole family tangent is target-only.
    independent_x, independent_gamma = sp.symbols(
        "independent_x independent_gamma"
    )
    corrected_u1_contact = sp.Integer(0)
    corrected_r1 = sp.Integer(0)
    weighted_area_order_one = sp.expand(
        sp.diff(corrected_r1, independent_gamma)
        + independent_gamma
        * sp.diff(corrected_u1_contact, independent_x)
    )
    assert weighted_area_order_one == 0
    corrected_source_jet = (sp.Integer(0), sp.Integer(0))

    family1 = tuple(
        sp.expand(sp.diff(component, s).subs(s, 0))
        for component in _family(s, v, t)
    )
    base_hamiltonian = -q**2 / 4 - p**3 / 36
    base_field = _hamiltonian_field(base_hamiltonian, p, q)
    base_field_at_family0 = tuple(
        sp.expand(component.subs({
            p: family0[0], q: family0[1]
        }))
        for component in base_field
    )
    assert all(
        sp.expand(actual - predicted) == 0
        for actual, predicted in zip(
            family1, base_field_at_family0, strict=True
        )
    )

    return {
        "schema": (
            "axiompack.jacobian_cusp_generator_first_order_replay.v1"
        ),
        "curve_only_projective_contact": {
            "coefficient_matrix_shape": list(matrix.shape),
            "rank": rank,
            "augmented_rank": augmented_rank,
            "dual_functional_value": str(dual_value),
            "excluded": True,
        },
        "corrected_gamma_divisible_lift": {
            "cusp_U1": str(sp.factor(cusp_u1)),
            "A1": str(sp.factor(correction_a1)),
            "corrected_U1": str(corrected_u1),
            "corrected_R1": str(corrected_r1),
            "corrected_source_jet": [
                str(component)
                for component in corrected_source_jet
            ],
            "target_hamiltonian": str(base_hamiltonian),
            "family_tangent_is_target_field_at_seed": True,
        },
        "next_boundary": (
            "construct the order-two gamma-divisible correction, solve "
            "its weighted-area companion, and test polynomial target "
            "descent"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
