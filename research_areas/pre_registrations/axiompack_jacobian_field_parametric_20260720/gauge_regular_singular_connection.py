#!/usr/bin/env python3
"""Exact punctured-parameter contact connection for the normalized family.

The probe compares the regular source-only infinitesimal connection with the
lower-degree connection obtained from the target scaling Hamiltonian ``P*Q``.
The latter has a forced pole at the distinguished parameter value ``s = 0``.
"""
from __future__ import annotations

import hashlib
import json

import sympy as sp


Pair = tuple[sp.Expr, sp.Expr]


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(
        str(sp.expand(value)).encode("utf-8")
    ).hexdigest()


def _degree(value: sp.Expr, first: sp.Symbol, second: sp.Symbol) -> int:
    if value == 0:
        return -1
    return int(sp.Poly(value, first, second).total_degree())


def _inverse_action(
    jacobian: sp.Matrix,
    determinant: sp.Expr,
    value: Pair,
) -> Pair:
    return (
        sp.cancel(
            (
                jacobian[1, 1] * value[0]
                - jacobian[0, 1] * value[1]
            )
            / determinant
        ),
        sp.cancel(
            (
                -jacobian[1, 0] * value[0]
                + jacobian[0, 0] * value[1]
            )
            / determinant
        ),
    )


def source_only_connection() -> dict[str, object]:
    """Return the exact family and its regular source-only connection."""
    s, v, t, z = sp.symbols("s v t z")
    gamma = 1 - sp.Rational(3, 2) * v + t
    mu = 3 * (s - 4) / (2 * (s - 6))
    lam = -(s - 4) / 4
    w = (1 + mu * v) * gamma
    p = (
        (2 + s / 2) * z
        + (-3 - 3 * s / 2) * z**2
        + s * z**3
    )
    q = (
        (1 + s / 4) * z**2
        - (2 + s) * z**3
        + 3 * s * z**4 / 4
    )
    family: Pair = (
        sp.cancel(
            gamma
            * lam
            / mu
            * (1 + p.subs(z, w) / gamma)
        ),
        sp.cancel(
            gamma**2
            * (1 + mu * v + q.subs(z, w) / gamma**2)
            / lam
        ),
    )
    jacobian = sp.Matrix([
        [sp.diff(item, variable) for variable in (v, t)]
        for item in family
    ])
    determinant = sp.factor(jacobian.det())
    assert sp.factor(determinant + gamma**2) == 0

    derivative: Pair = tuple(
        sp.diff(item, s) for item in family
    )  # type: ignore[assignment]
    source_only = _inverse_action(
        jacobian, determinant, derivative
    )
    scaling_pullback = _inverse_action(
        jacobian,
        determinant,
        (family[0], -family[1]),
    )

    return {
        "symbols": (s, v, t, z),
        "gamma": gamma,
        "family": family,
        "jacobian": jacobian,
        "determinant": determinant,
        "derivative": derivative,
        "source_only": source_only,
        "scaling_pullback": scaling_pullback,
    }


def run() -> dict[str, object]:
    data = source_only_connection()
    s, v, t, _ = data["symbols"]
    coefficient = sp.symbols("a")
    gamma = data["gamma"]
    family = data["family"]
    jacobian = data["jacobian"]
    determinant = data["determinant"]
    derivative = data["derivative"]
    source_only = data["source_only"]
    scaling_pullback = data["scaling_pullback"]

    # The regular source-only connection is already the admissible polar
    # prefix hidden by the diagonal Rees boundary.  Its exact contact and
    # weighted-divergence identities are checked before extracting that
    # principal part.
    source_only_contact_residual = tuple(
        sp.factor(
            derivative[index]
            - sum(
                jacobian[index, column] * source_only[column]
                for column in range(2)
            )
        )
        for index in range(2)
    )
    assert source_only_contact_residual == (0, 0)
    source_only_weighted_divergence = sp.factor(
        sp.diff(gamma**2 * source_only[0], v)
        + sp.diff(gamma**2 * source_only[1], t)
    )
    assert source_only_weighted_divergence == 0

    epsilon, tau, big_v, big_t = sp.symbols(
        "epsilon tau V T", nonzero=True
    )
    rees_substitution = {
        s: tau * epsilon**2,
        v: big_v / epsilon,
        t: big_t / epsilon,
    }
    rees_source = tuple(
        sp.cancel(
            epsilon**3 * component.subs(rees_substitution)
        )
        for component in source_only
    )
    rees_polar_order = 6
    rees_source_principal = tuple(
        sp.factor(
            sp.limit(
                epsilon**rees_polar_order * component,
                epsilon,
                0,
            )
        )
        for component in rees_source
    )
    assert all(component != 0 for component in rees_source_principal)
    rees_gamma = big_t - sp.Rational(3, 2) * big_v
    rees_principal_weighted_divergence = sp.factor(
        sp.diff(
            rees_gamma**2 * rees_source_principal[0],
            big_v,
        )
        + sp.diff(
            rees_gamma**2 * rees_source_principal[1],
            big_t,
        )
    )
    assert rees_principal_weighted_divergence == 0

    general_scaling_source: Pair = tuple(
        sp.cancel(
            source_only[index]
            - coefficient * scaling_pullback[index]
        )
        for index in range(2)
    )  # type: ignore[assignment]

    # One top-shell coefficient already forces the only scaling coefficient
    # that can lower the source degree from eleven.
    numerator = sp.fraction(general_scaling_source[0])[0]
    top_equation = sp.factor(
        sp.Poly(numerator, v, t).coeff_monomial(v**11)
    )
    solutions = sp.solve(top_equation, coefficient)
    assert len(solutions) == 1
    forced_scaling = sp.factor(solutions[0])
    expected_scaling = sp.factor(
        4
        * (2 * s**2 - 11 * s + 6)
        / (7 * s * (s - 6) * (s - 4))
    )
    assert sp.factor(forced_scaling - expected_scaling) == 0

    punctured_source: Pair = tuple(
        sp.factor(item.subs(coefficient, forced_scaling))
        for item in general_scaling_source
    )  # type: ignore[assignment]
    assert [
        _degree(sp.fraction(item)[0], v, t)
        for item in source_only
    ] == [11, 11]
    assert [
        _degree(sp.fraction(item)[0], v, t)
        for item in punctured_source
    ] == [9, 9]
    assert all(
        not ({v, t} & sp.denom(item).free_symbols)
        for item in source_only + punctured_source
    )

    scaling_residue = sp.factor(
        sp.limit(s * forced_scaling, s, 0)
    )
    assert scaling_residue == sp.Rational(1, 7)
    source_residue: Pair = tuple(
        sp.factor(sp.limit(s * item, s, 0))
        for item in punctured_source
    )  # type: ignore[assignment]
    assert [_degree(item, v, t) for item in source_residue] == [7, 7]

    seed = tuple(sp.cancel(item.subs(s, 0)) for item in family)
    seed_jacobian = jacobian.subs(s, 0)
    pole_cancellation = (
        sp.expand(
            seed_jacobian[0, 0] * source_residue[0]
            + seed_jacobian[0, 1] * source_residue[1]
            + scaling_residue * seed[0]
        ),
        sp.expand(
            seed_jacobian[1, 0] * source_residue[0]
            + seed_jacobian[1, 1] * source_residue[1]
            - scaling_residue * seed[1]
        ),
    )
    assert pole_cancellation == (0, 0)

    # Both source fields obey the quotient lift ideals.
    for field in (source_only, punctured_source, source_residue):
        assert field[0].subs({v: 0, t: 0}) == 0
        second_axis = sp.cancel(field[1].subs(t, 0))
        assert second_axis.subs(v, 0) == 0
        assert sp.diff(second_axis, v).subs(v, 0) == 0

    return {
        "schema": (
            "axiompack.jacobian_regular_singular_connection.v1"
        ),
        "family_source_degrees": [
            _degree(item, v, t) for item in family
        ],
        "quotient_jacobian": str(determinant),
        "regular_source_only_connection": {
            "source_degrees": [
                _degree(sp.fraction(item)[0], v, t)
                for item in source_only
            ],
            "regular_at_s_zero": all(
                sp.denom(item).subs(s, 0) != 0
                for item in source_only
            ),
            "sha256": [_sha(item) for item in source_only],
            "exact_contact_residual": [
                str(item) for item in source_only_contact_residual
            ],
            "weighted_divergence": str(
                source_only_weighted_divergence
            ),
            "rees_polar_order": rees_polar_order,
            "rees_principal": [
                str(item) for item in rees_source_principal
            ],
            "rees_principal_weighted_divergence": str(
                rees_principal_weighted_divergence
            ),
        },
        "punctured_scaling_connection": {
            "hamiltonian": "a(s)*P*Q",
            "forced_scaling": str(forced_scaling),
            "scaling_residue_at_s_zero": str(scaling_residue),
            "source_degrees": [
                _degree(sp.fraction(item)[0], v, t)
                for item in punctured_source
            ],
            "source_has_simple_pole_at_s_zero": all(
                sp.limit(s * item, s, 0) != 0
                for item in punctured_source
            ),
            "source_sha256": [
                _sha(item) for item in punctured_source
            ],
        },
        "pole_residue": {
            "source_degrees": [
                _degree(item, v, t) for item in source_residue
            ],
            "source_sha256": [
                _sha(item) for item in source_residue
            ],
            "seed_contact_stabilizer_identity": True,
        },
        "top_shell_forces_scaling": str(top_equation),
        "all_source_fields_satisfy_quotient_lift_ideals": True,
        "claim_boundary": (
            "The uniqueness statement is within the target scaling lane "
            "K=a(s)*P*Q. The degree-nine decomposition is defined over "
            "Q(s) but is not an s-adically regular formal gauge at s=0. "
            "The regular source-only connection supplies an admissible "
            "order-six polar Rees prefix, so node separation cannot by "
            "itself imply an unrestricted tail-limsup lower bound."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
