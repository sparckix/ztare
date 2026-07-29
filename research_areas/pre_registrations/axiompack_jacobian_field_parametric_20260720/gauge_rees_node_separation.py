#!/usr/bin/env python3
"""Exact Rees-boundary node separation for the normalized Jacobian family."""
from __future__ import annotations

import hashlib
import json

import sympy as sp

from gauge_regular_singular_connection import source_only_connection


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(
        str(sp.factor(value)).encode("utf-8")
    ).hexdigest()


def run() -> dict[str, object]:
    epsilon, tau, v_cap, t_cap = sp.symbols(
        "epsilon tau V T",
        nonzero=True,
    )
    s = tau * epsilon**2
    v = v_cap / epsilon
    t = t_cap / epsilon
    gamma = 1 - sp.Rational(3, 2) * v + t
    mu = 3 * (s - 4) / (2 * (s - 6))
    lam = -(s - 4) / 4
    w = (1 + mu * v) * gamma
    variable = sp.Symbol("variable")
    family_polynomial_p = (
        (2 + s / 2) * variable
        + (-3 - 3 * s / 2) * variable**2
        + s * variable**3
    )
    family_polynomial_q = (
        (1 + s / 4) * variable**2
        - (2 + s) * variable**3
        + 3 * s * variable**4 / 4
    )
    family_p = sp.cancel(
        lam / mu
        * (gamma + family_polynomial_p.subs(variable, w))
    )
    family_q = sp.cancel(
        (
            gamma**2 * (1 + mu * v)
            + family_polynomial_q.subs(variable, w)
        )
        / lam
    )

    rees_p = sp.factor(sp.limit(epsilon**4 * family_p, epsilon, 0))
    rees_q = sp.factor(sp.limit(epsilon**6 * family_q, epsilon, 0))
    r = v_cap * (t_cap - sp.Rational(3, 2) * v_cap)
    expected_p = sp.factor(tau * r**3 - 3 * r**2)
    expected_q = sp.factor(
        sp.Rational(3, 4) * tau * r**4 - 2 * r**3
    )
    assert sp.factor(rees_p - expected_p) == 0
    assert sp.factor(rees_q - expected_q) == 0

    r_symbol, p, q = sp.symbols("r P Q")
    p_tau = tau * r_symbol**3 - 3 * r_symbol**2
    q_tau = sp.Rational(3, 4) * tau * r_symbol**4 - 2 * r_symbol**3
    p_prime = sp.factor(sp.diff(p_tau, r_symbol))
    q_prime = sp.factor(sp.diff(q_tau, r_symbol))
    assert p_prime == 3 * r_symbol * (tau * r_symbol - 2)
    assert q_prime == r_symbol * p_prime

    second = sp.Matrix([
        sp.diff(p_tau, r_symbol, 2),
        sp.diff(q_tau, r_symbol, 2),
    ])
    third = sp.Matrix([
        sp.diff(p_tau, r_symbol, 3),
        sp.diff(q_tau, r_symbol, 3),
    ])
    cusp_determinant = sp.factor(
        second[0] * third[1] - second[1] * third[0]
    )
    cusp_at_zero = sp.factor(cusp_determinant.subs(r_symbol, 0))
    cusp_at_two = sp.factor(
        cusp_determinant.subs(r_symbol, 2 / tau)
    )
    assert cusp_at_zero == 72
    assert cusp_at_two == 72

    implicit = sp.factor(sp.resultant(p - p_tau, q - q_tau, r_symbol))
    expected_implicit = (
        -tau
        * (
            27 * p**4 * tau**2
            + 64 * p**3
            + 24 * p**2 * q * tau
            + 192 * p * q**2 * tau**2
            - 64 * q**3 * tau**3
            + 432 * q**2
        )
        / 64
    )
    assert sp.factor(implicit - expected_implicit) == 0

    root = sp.sqrt(3)
    r_plus = (1 + root) / tau
    r_minus = (1 - root) / tau
    node_p = -2 / tau**2
    node_q = 1 / tau**3
    for branch in (r_plus, r_minus):
        assert sp.simplify(p_tau.subs(r_symbol, branch) - node_p) == 0
        assert sp.simplify(q_tau.subs(r_symbol, branch) - node_q) == 0
    assert sp.simplify(r_plus - r_minus) != 0

    parameter_velocity = sp.Matrix([
        sp.diff(p_tau, tau),
        sp.diff(q_tau, tau),
    ])
    tangent = sp.Matrix([p_prime, q_prime])
    normal_pairing = sp.factor(
        tangent[0] * parameter_velocity[1]
        - tangent[1] * parameter_velocity[0]
    )
    expected_pairing = -sp.Rational(3, 4) * r_symbol**5 * (
        tau * r_symbol - 2
    )
    assert sp.factor(normal_pairing - expected_pairing) == 0

    hamiltonian_restriction = (
        -r_symbol**6 / 4
        + sp.Rational(3, 28) * tau * r_symbol**7
    )
    assert sp.factor(
        sp.diff(hamiltonian_restriction, r_symbol)
        + normal_pairing
    ) == 0
    node_separation = sp.simplify(
        hamiltonian_restriction.subs(r_symbol, r_plus)
        - hamiltonian_restriction.subs(r_symbol, r_minus)
    )
    assert node_separation == 72 * root / (7 * tau**6)
    assert node_separation != 0

    # A rational identity avoids relying on a particular square-root
    # representation in the kernel endpoint.  If x+y=2 and xy=-2, then
    # hbar(x)-hbar(y)=36/7*(x-y).
    x, y = sp.symbols("x y")
    hbar_x = -x**6 / 4 + sp.Rational(3, 28) * x**7
    hbar_y = -y**6 / 4 + sp.Rational(3, 28) * y**7
    divided_difference = sp.cancel((hbar_x - hbar_y) / (x - y))
    node_relations = sp.groebner(
        [x + y - 2, x * y + 2],
        y,
        x,
        order="lex",
        domain=sp.QQ,
    )
    rational_separation_remainder = node_relations.reduce(
        sp.expand(divided_difference - sp.Rational(36, 7))
    )[1]
    assert rational_separation_remainder == 0

    # The regular source-only connection becomes a finite pole-six Rees
    # cascade.  It is weighted-divergence-free and spans the complete
    # boundary parameter motion, so a tail-limsup argument cannot silently
    # replace the source action by a regular tangent field.
    connection = source_only_connection()
    connection_s, connection_v, connection_t, _ = connection["symbols"]
    scaled_source = sp.Matrix([
        sp.cancel(
            epsilon**3
            * component.subs({
                connection_s: tau * epsilon**2,
                connection_v: v_cap / epsilon,
                connection_t: t_cap / epsilon,
            })
        )
        for component in connection["source_only"]
    ])
    scaled_family = sp.Matrix([
        epsilon**4 * family_p,
        epsilon**6 * family_q,
    ])
    scaled_jacobian = scaled_family.jacobian((v_cap, t_cap))
    scaled_parameter_velocity = scaled_family.diff(tau)
    assert all(
        sp.factor(component) == 0
        for component in (
            scaled_jacobian * scaled_source
            - scaled_parameter_velocity
        )
    )
    scaled_density = (
        t_cap - sp.Rational(3, 2) * v_cap + epsilon
    ) ** 2
    assert sp.factor(
        sp.diff(scaled_density * scaled_source[0], v_cap)
        + sp.diff(scaled_density * scaled_source[1], t_cap)
    ) == 0
    polar_principal = tuple(
        sp.factor(sp.limit(epsilon**6 * component, epsilon, 0))
        for component in scaled_source
    )
    assert all(component != 0 for component in polar_principal)
    assert sp.factor(
        sp.diff(r, v_cap) * polar_principal[0]
        + sp.diff(r, t_cap) * polar_principal[1]
    ) == 0
    special_density = (
        t_cap - sp.Rational(3, 2) * v_cap
    ) ** 2
    assert sp.factor(
        sp.diff(special_density * polar_principal[0], v_cap)
        + sp.diff(special_density * polar_principal[1], t_cap)
    ) == 0

    # Its principal part is exactly the earlier adjugate witness.  The
    # subleading coefficients are what repair that witness's divergence.
    source_normal_seed = sp.Matrix([
        -v_cap**3 * (
            t_cap - sp.Rational(3, 2) * v_cap
        ),
        -sp.Rational(3, 4) * v_cap**4 * (
            t_cap - sp.Rational(3, 2) * v_cap
        ) ** 2,
    ])
    adjugate_polar = (
        epsilon**-6
        * scaled_jacobian.adjugate()
        * source_normal_seed
    )
    adjugate_principal = tuple(
        sp.factor(sp.limit(epsilon**6 * component, epsilon, 0))
        for component in adjugate_polar
    )
    assert polar_principal == adjugate_principal

    return {
        "schema": "axiompack.jacobian_rees_node_separation.v1",
        "boundary": {
            "parameterization": [str(p_tau), str(q_tau)],
            "rank_one_coordinate": str(r),
            "family_binding_sha256": [_sha(rees_p), _sha(rees_q)],
            "implicit_equation": str(expected_implicit),
        },
        "exceptional_set": {
            "cusps": ["r=0", "r=2/tau"],
            "cusp_second_third_determinants": [
                str(cusp_at_zero),
                str(cusp_at_two),
            ],
            "node_branches": [str(r_plus), str(r_minus)],
            "node_image": [str(node_p), str(node_q)],
            "tangent_slopes_distinct": True,
        },
        "hamiltonian_normal_class": {
            "normal_pairing": str(normal_pairing),
            "required_restriction": str(hamiltonian_restriction),
            "node_separation": str(node_separation),
            "rational_divided_difference": "36/7",
        },
        "rees_consequence": {
            "node_valuation": "n-2*i-3*j",
            "strict_subcritical_condition": (
                "4*i+6*j <= (2-delta)*n+C"
            ),
            "conditional_on_regular_source_rees_specialization": True,
            "conditional_instantaneous_weighted_target_rate": "2",
            "conditional_instantaneous_ordinary_target_rate": "1/3",
        },
        "admissible_polar_source": {
            "source_only_contact_replay": True,
            "scaled_weighted_divergence_zero": True,
            "polar_order": 6,
            "principal_part": [
                str(component) for component in polar_principal
            ],
            "principal_part_tangent_to_rank_one_fibers": True,
            "principal_part_matches_adjugate_witness": True,
            "complete_boundary_motion_spanned": True,
        },
        "checks": {
            "exact_normalized_family_binding": True,
            "two_cusps": True,
            "ordinary_node": True,
            "source_tangent_killed_by_determinant": True,
            "node_hamiltonian_descent_fails": True,
            "admissible_polar_source_spans_node_motion": True,
        },
        "claim_boundary": (
            "node separation obstructs a regular source specialization, "
            "but the exact source-only connection has a pole-six "
            "weighted-divergence-free Rees cascade spanning the motion; "
            "only the uniform assembled-map theorem survives"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
