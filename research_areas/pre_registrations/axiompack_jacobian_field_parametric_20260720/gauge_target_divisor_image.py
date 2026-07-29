#!/usr/bin/env python3
"""Exact admissible target image on the exceptional divisor.

The replay has two parts.  At the seed it computes the complete divisor
restriction of polynomial Hamiltonians satisfying the quotient target-lift
ideals.  For the full parameter family it constructs a regular target
Hamiltonian whose relative source connection restricts to translations.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_inverse_cubic_target_module import (  # noqa: E402
    run as inverse_cubic_module,
)
from gauge_regular_singular_connection import (  # noqa: E402
    _inverse_action,
    source_only_connection,
)


Pair = tuple[sp.Expr, sp.Expr]


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(
        str(sp.expand(value)).encode("utf-8")
    ).hexdigest()


def _target_lift(field: Pair, p: sp.Symbol, q: sp.Symbol) -> bool:
    first = sp.Poly(sp.expand(field[0]), p, q)
    second = sp.Poly(sp.expand(field[1]), p, q)
    return (
        first.coeff_monomial(1) == 0
        and second.coeff_monomial(1) == 0
        and second.coeff_monomial(p) == 0
    )


def _source_lift(
    field: Pair,
    v: sp.Symbol,
    t: sp.Symbol,
) -> bool:
    second_axis = sp.cancel(field[1].subs(t, 0))
    return (
        sp.cancel(field[0].subs({v: 0, t: 0})) == 0
        and sp.cancel(second_axis.subs(v, 0)) == 0
        and sp.cancel(sp.diff(second_axis, v).subs(v, 0)) == 0
    )


def _divisor_field(
    field: Pair,
    v: sp.Symbol,
    t: sp.Symbol,
    y: sp.Symbol,
) -> sp.Expr:
    """Coefficient in the coordinate y=2v+3 on gamma=0."""
    return sp.factor(
        2
        * field[0]
        .subs(t, -1 + sp.Rational(3, 2) * v)
        .subs(v, (y - 3) / 2)
    )


def _spatially_polynomial(
    field: Pair,
    spatial: tuple[sp.Symbol, sp.Symbol],
) -> bool:
    return all(
        not (set(spatial) & sp.denom(sp.cancel(item)).free_symbols)
        for item in field
    )


def _weighted_divergence(
    field: Pair,
    gamma: sp.Expr,
    v: sp.Symbol,
    t: sp.Symbol,
) -> sp.Expr:
    return sp.factor(
        sp.diff(gamma**2 * field[0], v)
        + sp.diff(gamma**2 * field[1], t)
    )


def run() -> dict[str, object]:
    module = inverse_cubic_module()
    assert module["descent_module"]["basis"] == ["1", "w", "w^2"]
    assert module["target_C_normal_module"]["scalar_basis"] == ["1", "Q"]

    p, q, c = sp.symbols("P Q C")
    c_polynomial = (
        4 * p**3 - p**2 - 18 * p * q + 27 * q**2 + 4 * q
    )

    # The low C-normal jet obeying the three target-lift conditions.
    a = sp.symbols("a")
    lifted_low_jet = sp.expand(
        a * (c_polynomial + p**2 - 4 * q)
    )
    assert sp.expand(
        lifted_low_jet
        - a * (4 * p**3 - 18 * p * q + 27 * q**2)
    ) == 0
    assert _target_lift(
        (
            sp.diff(lifted_low_jet, q),
            -sp.diff(lifted_low_jet, p),
        ),
        p,
        q,
    )

    # Seed blow-up chart.
    r, g, y = sp.symbols("r g y")
    seed_p = g * (1 + 2 * r) - 3 * r**2 * g**2
    seed_q = g**2 * r * (1 + r) - 2 * r**3 * g**3
    seed_jacobian = sp.Matrix([
        [sp.diff(seed_p, variable) for variable in (r, g)],
        [sp.diff(seed_q, variable) for variable in (r, g)],
    ])
    assert sp.factor(seed_jacobian.det() + g**2) == 0
    assert sp.expand(
        seed_p.subs(r, (y - 1) / 2)
        - (
            y * g
            - sp.Rational(3, 4) * (y - 1) ** 2 * g**2
        )
    ) == 0
    assert sp.expand(
        seed_q.subs(r, (y - 1) / 2)
        - (
            sp.Rational(1, 4) * (y**2 - 1) * g**2
            - sp.Rational(1, 4) * (y - 1) ** 3 * g**3
        )
    ) == 0

    def seed_pullback(hamiltonian: sp.Expr) -> Pair:
        target = (
            sp.diff(hamiltonian, q),
            -sp.diff(hamiltonian, p),
        )
        value = tuple(
            item.subs({p: seed_p, q: seed_q})
            for item in target
        )
        result = seed_jacobian.inv() * sp.Matrix(value)
        return sp.cancel(result[0]), sp.cancel(result[1])

    seed_p3 = seed_pullback(p**3)
    seed_pq = seed_pullback(p * q)
    seed_q2 = seed_pullback(q**2)
    assert all(
        _spatially_polynomial(field, (r, g))
        for field in (seed_p3, seed_pq, seed_q2)
    )
    p3_restriction = sp.factor(
        2 * seed_p3[0].subs(g, 0).subs(r, (y - 1) / 2)
    )
    pq_restriction = sp.factor(
        2 * seed_pq[0].subs(g, 0).subs(r, (y - 1) / 2)
    )
    q2_restriction = sp.factor(
        2 * seed_q2[0].subs(g, 0).subs(r, (y - 1) / 2)
    )
    assert sp.expand(p3_restriction + 6 * y**3) == 0
    assert sp.expand(
        pq_restriction
        + sp.Rational(3, 2) * (y**3 - y)
    ) == 0
    assert sp.expand(q2_restriction) == 0
    image_matrix = sp.Matrix([
        [-6, -sp.Rational(3, 2)],
        [0, sp.Rational(3, 2)],
    ])
    assert image_matrix.det() == -9

    # Full family and the compatible regular target control.
    data = source_only_connection()
    s, v, t, _ = data["symbols"]
    gamma = data["gamma"]
    family_p, family_q = data["family"]
    jacobian = data["jacobian"]
    determinant = data["determinant"]
    source_only = data["source_only"]
    pullback_p3 = _inverse_action(
        jacobian,
        determinant,
        (sp.Integer(0), -3 * family_p**2),
    )
    pullback_pq = _inverse_action(
        jacobian,
        determinant,
        (family_p, -family_q),
    )
    pullback_q2 = _inverse_action(
        jacobian,
        determinant,
        (2 * family_q, sp.Integer(0)),
    )
    affine_coefficient_p3 = sp.factor(
        -192
        * (s**2 - 3 * s - 8)
        / (
            (s - 6) ** 3
            * (s - 4) ** 2
            * (s + 4) ** 2
        )
    )
    affine_controlled = tuple(
        sp.cancel(
            source_only[index]
            - affine_coefficient_p3 * pullback_p3[index]
        )
        for index in range(2)
    )
    coefficient_p3 = sp.factor(
        96
        * (s**2 - 12 * s + 16)
        / (
            (s - 6) ** 3
            * (s - 4) ** 2
            * (s + 4) ** 2
        )
    )
    coefficient_pq = sp.factor(
        2 * s / ((s - 4) * (s + 4))
    )
    controlled = tuple(
        sp.cancel(
            source_only[index]
            - coefficient_p3 * pullback_p3[index]
            - coefficient_pq * pullback_pq[index]
        )
        for index in range(2)
    )
    fixed_slice_controlled = tuple(
        sp.cancel(
            controlled[index]
            + sp.Rational(1, 4) * pullback_q2[index]
        )
        for index in range(2)
    )

    for field in (
        pullback_p3,
        pullback_pq,
        pullback_q2,
        affine_controlled,
        controlled,
        fixed_slice_controlled,
    ):
        assert _spatially_polynomial(field, (v, t))
        assert _source_lift(field, v, t)
        assert _weighted_divergence(field, gamma, v, t) == 0
        normal = sp.factor(
            field[1] - sp.Rational(3, 2) * field[0]
        )
        assert sp.factor(
            normal.subs(t, -1 + sp.Rational(3, 2) * v)
        ) == 0

    # Divisor preservation is weaker than fixing gamma pointwise.
    assert sp.factor(
        pullback_p3[1]
        - sp.Rational(3, 2) * pullback_p3[0]
    ) != 0
    assert sp.factor(
        pullback_pq[1]
        - sp.Rational(3, 2) * pullback_pq[0]
    ) != 0

    controlled_restriction = _divisor_field(
        controlled, v, t, y
    )
    fixed_slice_restriction = _divisor_field(
        fixed_slice_controlled, v, t, y
    )
    assert _divisor_field(pullback_q2, v, t, y) == 0
    affine_restriction = _divisor_field(
        affine_controlled, v, t, y
    )
    expected_affine = sp.factor(
        s
        * (
            9 * s**2 * y
            - 15 * s**2
            - 144 * y
            + 160
        )
        / (
            3
            * (s - 4) ** 2
            * (s + 4) ** 2
        )
    )
    assert sp.factor(affine_restriction - expected_affine) == 0
    translation = sp.factor(
        160
        * s
        / (
            3
            * (s - 4) ** 2
            * (s + 4) ** 2
        )
    )
    assert sp.factor(controlled_restriction - translation) == 0
    assert sp.factor(fixed_slice_restriction - translation) == 0
    assert all(
        sp.factor(item.subs(s, 0)) == 0
        for item in fixed_slice_controlled
    )
    assert (
        affine_coefficient_p3.subs(s, 0)
        == -sp.Rational(1, 36)
    )
    assert coefficient_p3.subs(s, 0) == -sp.Rational(1, 36)
    assert coefficient_pq.subs(s, 0) == 0
    assert all(
        sp.denom(value).subs(s, 0) != 0
        for value in (
            coefficient_p3,
            coefficient_pq,
            affine_coefficient_p3,
            translation,
        )
    )

    return {
        "schema": "axiompack.jacobian_target_divisor_image.v1",
        "inverse_cubic_basis": module["descent_module"]["basis"],
        "target_C_normal_scalar_basis": (
            module["target_C_normal_module"]["scalar_basis"]
        ),
        "target_lift_low_jet": str(lifted_low_jet),
        "seed_restriction": {
            "P^3": str(p3_restriction),
            "P*Q": str(pq_restriction),
            "Q^2": str(q2_restriction),
            "image_witt_basis": ["e_0=y*d/dy", "e_2=y^3*d/dy"],
            "image_matrix_determinant": str(image_matrix.det()),
            "cubic_cokernel_basis": [
                "e_-1=d/dy",
                "e_1=y^2*d/dy",
            ],
        },
        "regular_control": {
            "P3_only": {
                "a(s)": str(affine_coefficient_p3),
                "divisor_source_connection": str(
                    affine_restriction
                ),
                "divisor_lie_algebra": (
                    "span{d/dy,y*d/dy}"
                ),
            },
            "hamiltonian": "a(s)*P^3+b(s)*P*Q",
            "a(s)": str(coefficient_p3),
            "b(s)": str(coefficient_pq),
            "a(0)": str(coefficient_p3.subs(s, 0)),
            "b(0)": str(coefficient_pq.subs(s, 0)),
            "divisor_source_connection": str(translation),
            "divisor_lie_algebra": "QQ[[s]]*d/dy",
            "source_sha256": [_sha(item) for item in controlled],
            "fixed_first_slice": {
                "hamiltonian": (
                    "a(s)*P^3+b(s)*P*Q-Q^2/4"
                ),
                "K(0)": "-P^3/36-Q^2/4",
                "source_connection_at_s_zero": ["0", "0"],
                "divisor_source_connection": str(
                    fixed_slice_restriction
                ),
                "source_sha256": [
                    _sha(item) for item in fixed_slice_controlled
                ],
            },
        },
        "checks": {
            "all_pullbacks_spatially_polynomial": True,
            "full_source_lift_ideals": True,
            "pulled_back_volume_identity": True,
            "divisor_ideal_preserved": True,
            "gamma_coordinate_fixed_pointwise": False,
            "control_regular_at_s_zero": True,
        },
        "verdict": (
            "the source-only Bernoulli-Witt cascade is removed by a "
            "regular admissible target gauge; the controlled divisor "
            "connection is translation-valued at every parameter"
        ),
        "claim_boundary": (
            "this kills the exceptional-divisor Magnus route to a "
            "gauge-independent lower bound; it does not settle the "
            "symmetric source-target degree minimax"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
