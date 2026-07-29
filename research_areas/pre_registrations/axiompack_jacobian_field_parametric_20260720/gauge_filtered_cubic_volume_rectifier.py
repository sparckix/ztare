#!/usr/bin/env python3
"""Exact replay for the filtered inverse-cubic volume right inverse."""
from __future__ import annotations

import json

import sympy as sp


def run() -> dict[str, object]:
    p, q, w = sp.symbols("P Q W")
    b, c = sp.symbols("b c")
    cubic = w**3 - w**2 + p * w - q

    # Trace zero in the cubic algebra.
    a = -(b + (1 - 2 * p) * c) / 3
    delta_u = a + b * w + c * w**2
    linearized = sp.rem(
        sp.Poly((3 * w**2 - 2 * w + p) * delta_u, w),
        sp.Poly(cubic, w),
    ).as_expr()
    e1 = ((6 * p - 2) / 3, (9 * q - p) / 3)
    e2 = (
        (7 * p - 9 * q - 2) / 3,
        (2 * p**2 - p + 3 * q) / 3,
    )
    delta_p = sp.expand(b * e1[0] + c * e2[0])
    delta_q = sp.expand(b * e1[1] + c * e2[1])
    assert sp.expand(linearized + delta_p * w - delta_q) == 0

    def field_action(
        field: tuple[sp.Expr, sp.Expr], value: sp.Expr
    ) -> sp.Expr:
        return sp.expand(
            field[0] * sp.diff(value, p)
            + field[1] * sp.diff(value, q)
        )

    assert sp.diff(e1[0], p) + sp.diff(e1[1], q) == 5
    assert sp.diff(e2[0], p) + sp.diff(e2[1], q) == sp.Rational(10, 3)

    shifted_p = p - sp.Rational(1, 3)
    shifted_q = q - p / 3 + sp.Rational(2, 27)
    assert field_action(e1, shifted_p) == 2 * shifted_p
    assert field_action(e1, shifted_q) == 3 * shifted_q

    def right_inverse(value: sp.Expr) -> tuple[sp.Expr, sp.Expr]:
        x, y = sp.symbols("x y")
        in_shifted = sp.Poly(
            sp.expand(value.subs({
                p: x + sp.Rational(1, 3),
                q: y + x / 3 + sp.Rational(1, 27),
            })),
            x,
            y,
        )
        u_shifted = sum(
            coefficient * x**i * y**j / (2 * i + 3 * j + 5)
            for (i, j), coefficient in in_shifted.terms()
        )
        u = sp.expand(u_shifted.subs({
            x: shifted_p,
            y: shifted_q,
        }))
        k = sp.expand(u.subs({p: 0, q: 0}))
        return sp.expand(u + 2 * k), sp.expand(-3 * k)

    test_density = (
        3 * p**4 * q + 5 * p**2 + 7 * p * q + 11 * q**2
        - 13 * p + 17
    )
    test_b, test_c = right_inverse(test_density)
    recovered = sp.expand(
        field_action(e1, test_b) + 5 * test_b
        + field_action(e2, test_c) + sp.Rational(10, 3) * test_c
    )
    assert recovered == test_density
    assert (test_b + test_c).subs({p: 0, q: 0}) == 0

    # The first Weierstrass defect selects the zero-source Hamiltonian
    # coefficient, rather than the degree-seven triangular shell.
    first_b, first_c = right_inverse(sp.Rational(5, 12))
    assert first_b == sp.Rational(1, 4)
    assert first_c == -sp.Rational(1, 4)
    correction = (
        sp.expand(first_b * e1[0] + first_c * e2[0]),
        sp.expand(first_b * e1[1] + first_c * e2[1]),
    )
    cubic_first = (
        (p - 3 * q) / 12,
        (p**2 - 6 * q) / 12,
    )
    h1 = tuple(
        sp.expand(cubic_first[index] + correction[index])
        for index in range(2)
    )
    assert h1 == (q / 2, -p**2 / 12)
    assert sp.diff(h1[0], p) + sp.diff(h1[1], q) == 0

    s, v, t, z = sp.symbols("s v t z")
    gamma = 1 - sp.Rational(3, 2) * v + t
    mu = 3 * (s - 4) / (2 * (s - 6))
    lam = -(s - 4) / 4
    family_w = (1 + mu * v) * gamma
    p_poly = (
        (2 + s / 2) * z
        + (-3 - 3 * s / 2) * z**2
        + s * z**3
    )
    q_poly = (
        (1 + s / 4) * z**2
        - (2 + s) * z**3
        + 3 * s * z**4 / 4
    )
    family_p = sp.cancel(
        lam / mu * (gamma + p_poly.subs(z, family_w))
    )
    family_q = sp.cancel(
        (
            gamma**2 * (1 + mu * v)
            + q_poly.subs(z, family_w)
        )
        / lam
    )
    inverse_w = sp.Symbol("inverse_w")
    inverse_a = s / (2 * (s + 2))
    inverse_b = (s + 4) / (2 * (s + 2))
    inverse_c = 12 / ((s - 6) * (s + 2))
    inverse_d = -(s - 4) / (2 * (s + 2))
    inverse_relation = (
        inverse_w**3
        - inverse_a * inverse_w**4
        - inverse_b * inverse_w**2
        - inverse_c * p * inverse_w
        - inverse_d * q
    )
    pulled_derivative = sp.factor(sp.cancel(
        sp.diff(inverse_relation, inverse_w).subs({
            inverse_w: family_w,
            p: family_p,
            q: family_q,
        })
    ))
    assert pulled_derivative == 2 * gamma / (s + 2)
    assert sp.cancel(inverse_a + inverse_b) == 1
    small_root_at_origin = sp.cancel(inverse_a / inverse_b)
    assert sp.cancel(
        small_root_at_origin
        - inverse_a
        - inverse_b * small_root_at_origin**2
    ) == 0
    assert sp.cancel(
        -(small_root_at_origin / inverse_a) * inverse_b
    ) == -1

    p0, q0 = family_p.subs(s, 0), family_q.subs(s, 0)
    p1 = sp.diff(family_p, s).subs(s, 0)
    q1 = sp.diff(family_q, s).subs(s, 0)
    assert sp.factor(p1 + h1[0].subs({p: p0, q: q0})) == 0
    assert sp.factor(q1 + h1[1].subs({p: p0, q: q0})) == 0

    return {
        "schema": "axiompack.jacobian_filtered_cubic_rectifier.v1",
        "trace_zero_control": str(delta_u),
        "target_generators": {
            "E1": [str(item) for item in e1],
            "E2": [str(item) for item in e2],
        },
        "diagonal_coordinates": {
            "p": str(shifted_p),
            "r": str(shifted_q),
            "E1_p": "2*p",
            "E1_r": "3*r",
        },
        "right_inverse_replay": {
            "mixed_density_recovered": True,
            "affine_lift_boundary": True,
        },
        "first_order": {
            "b": str(first_b),
            "c": str(first_c),
            "target_correction": [str(item) for item in correction],
            "final_target_coefficient": [str(item) for item in h1],
            "source_coefficient": ["0", "0"],
        },
        "uncorrected_source_mechanism": {
            "inverse_relation_derivative_at_family_root": (
                "2*gamma/(s+2)"
            ),
            "theta": "4*z/(s*(1-z*W))",
            "root_shift_in_target_maximal_ideal": True,
            "source_formula": (
                "V+1=((W+h)/gamma)*theta^-1; "
                "T=gamma*theta-1+3*V/2"
            ),
        },
        "claim_boundary": (
            "the differentiated finite-branch factorization supplies the "
            "uncorrected 2*n+1 source bound, and the inverse-cubic volume "
            "rectifier preserves it coefficientwise; historical priority "
            "and kernel formalization remain separate"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
