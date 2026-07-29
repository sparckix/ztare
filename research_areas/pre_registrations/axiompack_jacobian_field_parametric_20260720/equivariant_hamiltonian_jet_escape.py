#!/usr/bin/env python3
"""Exact second-jet coordinate-orbit test for the normalized cubic lift."""
from __future__ import annotations

import json

import sympy as sp


def _family() -> dict[str, object]:
    s, v, t, z = sp.symbols("s v t z")
    gamma = 1 - sp.Rational(3, 2) * v + t
    mu = 3 * (s - 4) / (2 * (s - 6))
    lam = -(s - 4) / 4
    w = (1 + mu * v) * gamma
    p = (2 + s / 2) * z + (-3 - 3 * s / 2) * z**2 + s * z**3
    q = (1 + s / 4) * z**2 - (2 + s) * z**3 + 3 * s * z**4 / 4
    beta = sp.cancel(lam / mu * (1 + p.subs(z, w) / gamma))
    alpha = sp.cancel((1 + mu * v + q.subs(z, w) / gamma**2) / lam)
    derivatives = {
        f"{name}{order}": sp.cancel(sp.diff(poly, s, order).subs(s, 0))
        for name, poly in (("beta", beta), ("alpha", alpha))
        for order in range(3)
    }
    assert all(
        not ({v, t} & sp.denom(value).free_symbols)
        for value in derivatives.values()
    )
    beta0, alpha0 = derivatives["beta0"], derivatives["alpha0"]
    p0, q0 = sp.expand(gamma * beta0), sp.expand(gamma**2 * alpha0)
    assert sp.cancel(gamma * derivatives["beta1"] + q0 / 2) == 0
    assert sp.cancel(gamma**2 * derivatives["alpha1"] - p0**2 / 12) == 0
    residual = (
        sp.expand(gamma * derivatives["beta2"] + p0**2 / 24),
        sp.expand(gamma**2 * derivatives["alpha2"] + p0 * q0 / 12),
    )
    return {
        "symbols": (v, t),
        "gamma": gamma,
        "beta0": beta0,
        "alpha0": alpha0,
        "p0": p0,
        "q0": q0,
        "residual": residual,
        "second_derivative": (
            derivatives["beta2"], derivatives["alpha2"]
        ),
    }


def _structural_obstruction(family: dict[str, object]) -> dict[str, object]:
    v, t = family["symbols"]
    w, gamma, target_p, target_q, constant = sp.symbols("w gamma P Q c")
    source_coordinates = {
        v: w / gamma - 1,
        t: gamma - 1 + sp.Rational(3, 2) * (w / gamma - 1),
    }
    p0 = sp.cancel(family["p0"].subs(source_coordinates))
    q0 = sp.cancel(family["q0"].subs(source_coordinates))
    residual_p = sp.cancel(family["residual"][0].subs(source_coordinates))
    residual_q = sp.cancel(family["residual"][1].subs(source_coordinates))
    assert p0 == gamma - 3 * w**2 + 2 * w
    assert q0 == w * gamma + w**2 - 2 * w**3

    relation = sp.Poly(w**3 - w**2 + target_p * w - target_q, w)
    eliminate_gamma = {gamma: target_p - 2 * w + 3 * w**2}

    def remainder(value: sp.Expr) -> sp.Expr:
        polynomial = sp.Poly(sp.expand(value.subs(eliminate_gamma)), w)
        return sp.factor(sp.rem(polynomial, relation).as_expr())

    fixed_gamma_p = gamma * (2 - 6 * w)
    fixed_gamma_q = gamma * (gamma + 2 * w - 6 * w**2)
    residual_remainders = (remainder(residual_p), remainder(residual_q))
    constant_source_remainders = (
        remainder(fixed_gamma_p), remainder(fixed_gamma_q)
    )
    constant_obstruction = sp.Poly(
        residual_remainders[0] - constant * constant_source_remainders[0],
        w,
    ).coeff_monomial(w**2)
    assert sp.cancel(
        constant_obstruction + (21 * target_p - 10) / 24
    ) == 0

    # Associated-graded check at P=0.  With weights
    # wt(w)=1, wt(P)=2, wt(Q)=3, the top relation is w^3=Q.
    top_relation = sp.Poly(w**3 - target_q, w)
    top_gamma = 3 * w**2
    top_source = (-6 * w * top_gamma, -3 * w**2 * top_gamma)
    residue_stress = []
    for degree in range(1, 13):
        reduced = [
            sp.rem(sp.Poly(top_gamma**degree * value, w), top_relation).as_expr()
            for value in top_source
        ]
        nonbase = [
            any(sp.Poly(value, w).coeff_monomial(w**power) != 0 for power in (1, 2))
            for value in reduced
        ]
        assert any(nonbase)
        residue_stress.append({
            "source_degree": degree,
            "degree_mod_3": degree % 3,
            "P_component_nonbase": nonbase[0],
            "Q_component_nonbase": nonbase[1],
        })
    return {
        "seed_in_weighted_coordinates": {"P": str(p0), "Q": str(q0)},
        "inverse_relation": str(relation.as_expr()),
        "second_jet_residual_in_w_gamma": [
            str(sp.factor(residual_p)), str(sp.factor(residual_q))
        ],
        "residual_remainders_mod_inverse_relation": [
            str(value) for value in residual_remainders
        ],
        "constant_source_remainders_mod_inverse_relation": [
            str(value) for value in constant_source_remainders
        ],
        "constant_source_w2_obstruction": str(constant_obstruction),
        "positive_degree_source_top_residue_stress": residue_stress,
        "conclusion": (
            "second_jet_not_in_polynomial_target_hamiltonian_plus_"
            "fixed_gamma_polynomial_source_shear_orbit"
        ),
    }


def run() -> dict[str, object]:
    family = _family()
    return {
        "schema": "axiompack.jacobian_hamiltonian_jet_escape.v1",
        "beta0": str(sp.expand(family["beta0"])),
        "alpha0": str(sp.expand(family["alpha0"])),
        "first_derivative_hamiltonian_identity": True,
        "hamiltonian": "-Q^2/4 - P^3/36",
        "lie_square": ["-P^2/24", "-P*Q/12"],
        "second_derivative_beta_alpha": [
            str(sp.expand(value)) for value in family["second_derivative"]
        ],
        "second_jet_residual_degrees": [
            sp.Poly(value, *family["symbols"]).total_degree()
            for value in family["residual"]
        ],
        "structural_obstruction": _structural_obstruction(family),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
