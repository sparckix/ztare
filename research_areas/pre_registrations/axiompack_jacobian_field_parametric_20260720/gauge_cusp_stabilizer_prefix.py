#!/usr/bin/env python3
"""Exact cusp-stabilizer and finite-prefix BCH replay.

The replay checks the algebraic inputs to
``gauge_cusp_stabilizer_prefix_pencil.md``.  It does not infer the
unrestricted contact minimax from a finite truncation.
"""
from __future__ import annotations

import hashlib
import json
from math import ceil, factorial

import sympy as sp

from gauge_regular_singular_connection import (
    _degree,
    _inverse_action,
    source_only_connection,
)


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(
        str(sp.expand(value)).encode("utf-8")
    ).hexdigest()


def _hamiltonian_bracket(
    first: sp.Expr,
    second: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> sp.Expr:
    """Bracket satisfying [X_first, X_second] = X_result."""
    return sp.expand(
        sp.diff(first, q) * sp.diff(second, p)
        - sp.diff(first, p) * sp.diff(second, q)
    )


def _weighted_degree(
    value: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> int:
    weights = {
        2 * p_degree + 3 * q_degree
        for (p_degree, q_degree), coefficient
        in sp.Poly(value, p, q).terms()
        if coefficient != 0
    }
    assert len(weights) == 1
    return weights.pop()


def _seed_lift(
    hamiltonian: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> dict[str, object]:
    data = source_only_connection()
    s, v, t, _ = data["symbols"]
    gamma = data["gamma"]
    family = tuple(
        sp.factor(component.subs(s, 0))
        for component in data["family"]
    )
    jacobian = data["jacobian"].subs(s, 0)
    determinant = data["determinant"].subs(s, 0)
    target_field = (
        sp.diff(hamiltonian, q),
        -sp.diff(hamiltonian, p),
    )
    target_on_seed = tuple(
        sp.expand(
            component.subs({p: family[0], q: family[1]})
        )
        for component in target_field
    )
    source_field = tuple(
        sp.factor(component)
        for component in _inverse_action(
            jacobian,
            determinant,
            target_on_seed,
        )
    )
    residual = tuple(
        sp.factor(
            target_on_seed[index]
            - sum(
                jacobian[index, column] * source_field[column]
                for column in range(2)
            )
        )
        for index in range(2)
    )
    assert residual == (0, 0)
    assert all(
        not ({v, t} & sp.denom(component).free_symbols)
        for component in source_field
    )
    assert source_field[0].subs({v: 0, t: 0}) == 0
    assert source_field[1].subs({v: 0, t: 0}) == 0
    assert (
        sp.diff(source_field[1].subs(t, 0), v).subs(v, 0)
        == 0
    )
    weighted_divergence = sp.factor(
        sp.diff(gamma**2 * source_field[0], v)
        + sp.diff(gamma**2 * source_field[1], t)
    )
    assert weighted_divergence == 0
    return {
        "source_degrees": [
            _degree(sp.fraction(component)[0], v, t)
            for component in source_field
        ],
        "source_sha256": [
            _sha(component) for component in source_field
        ],
        "contact_residual": [str(item) for item in residual],
        "weighted_divergence": str(weighted_divergence),
        "source_lift_ideals": True,
    }


def run(depth: int = 10) -> dict[str, object]:
    p, q, r = sp.symbols("P Q r")
    cusp = 4 * p**3 + 27 * q**2
    seed = {p: -3 * r**2, q: -2 * r**3}
    seed_pair = sp.Matrix([seed[p], seed[q]])
    seed_derivative = seed_pair.diff(r)

    euler = sp.Matrix([2 * p, 3 * q])
    cusp_field = sp.Matrix([
        sp.diff(cusp, q),
        -sp.diff(cusp, p),
    ])
    assert sp.expand(cusp.subs(seed)) == 0
    assert sp.expand(
        2 * p * sp.diff(cusp, p)
        + 3 * q * sp.diff(cusp, q)
        - 6 * cusp
    ) == 0
    assert (
        sp.diff(euler[0], p) + sp.diff(euler[1], q)
        == 5
    )
    assert (
        sp.diff(cusp_field[0], p)
        + sp.diff(cusp_field[1], q)
        == 0
    )
    assert sp.factor(
        sp.Matrix.hstack(euler, cusp_field).det() + 6 * cusp
    ) == 0
    assert (
        cusp_field.subs(seed) - 18 * r**2 * seed_derivative
    ) == sp.zeros(2, 1)

    normal = -(p**3 + 9 * q**2) / 36
    assert sp.factor(normal.subs(seed) + r**6 / 4) == 0

    iterates: list[dict[str, object]] = []
    current = normal
    rising = 1
    for index in range(depth + 1):
        if index > 0:
            rising *= 5 + index
        expected_restriction = (
            -sp.Rational(1, 4)
            * 18**index
            * rising
            * r ** (6 + index)
        )
        restriction = sp.factor(current.subs(seed))
        assert sp.factor(
            restriction - expected_restriction
        ) == 0
        weight = _weighted_degree(current, p, q)
        assert weight == 6 + index
        ordinary_degree = _degree(current, p, q)
        assert ordinary_degree == 3 + index // 2
        assert ordinary_degree >= ceil(weight / 3)
        # The linear normal BCH coefficient after removing exp(tau X_C).
        bch_scalar = sp.Rational((-1) ** index, factorial(index + 1))
        iterates.append({
            "index": index,
            "weighted_degree_2_3": weight,
            "weighted_degree_4_6": 2 * weight,
            "ordinary_hamiltonian_degree": ordinary_degree,
            "ordinary_degree_floor": ceil(weight / 3),
            "restriction": str(restriction),
            "bch_scalar": str(bch_scalar),
            "sha256": _sha(current),
        })
        current = _hamiltonian_bracket(
            cusp, current, p, q
        )

    # Critical-face arithmetic.  At logarithmic order n=k+1, each
    # Hamiltonian has full Rees weight 2(6+k)=2n+10.
    assert all(
        row["weighted_degree_4_6"]
        == 2 * (row["index"] + 1) + 10
        for row in iterates
    )

    # An independent template checks X_(C L) = L X_C + C X_L.
    coefficients = sp.symbols("l0:6")
    template = (
        coefficients[0]
        + coefficients[1] * p
        + coefficients[2] * q
        + coefficients[3] * p**2
        + coefficients[4] * p * q
        + coefficients[5] * q**2
    )
    left = sp.Matrix([
        sp.diff(cusp * template, q),
        -sp.diff(cusp * template, p),
    ])
    template_field = sp.Matrix([
        sp.diff(template, q),
        -sp.diff(template, p),
    ])
    assert sp.expand(
        left - template * cusp_field - cusp * template_field
    ) == sp.zeros(2, 1)

    return {
        "schema": "axiompack.jacobian_cusp_stabilizer_prefix.v1",
        "cusp": str(cusp),
        "seed_parameterization": [
            str(seed[p]),
            str(seed[q]),
        ],
        "logarithmic_basis": {
            "euler_derivative_of_cusp": "6*C",
            "euler_divergence": 5,
            "hamiltonian_divergence": 0,
            "basis_determinant": "-6*C",
        },
        "hamiltonian_stabilizer": "constants + C*Q[P,Q]",
        "nonzero_normalization_action_locally_nilpotent": False,
        "normal_hamiltonian": str(normal),
        "seed_contact_lifts": {
            "cusp_stabilizer": _seed_lift(cusp, p, q),
            "normal_direction": _seed_lift(normal, p, q),
        },
        "bch_linear_normal_component": {
            "factorization": (
                "log(exp(-tau*X_C)"
                "*exp(tau*X_(C+mu*B))) modulo mu^2"
            ),
            "coefficient_rule": (
                "(-1)^k*tau^(k+1)/(k+1)! * ad_C^k(B)"
            ),
            "checked_depth": depth,
            "iterates": iterates,
            "critical_rees_face": True,
            "weight_only_ordinary_tail_slope_lower_bound": "1/3",
            "exact_ordinary_tail_slope": "1/2",
        },
        "generic_amplitude_cascade": {
            "coefficient_ring": "Q[mu]",
            "order_n_linear_coefficient": (
                "(-1)^(n-1)/n! * ad_C^(n-1)(B)"
            ),
            "linear_coefficient_nonzero_at_every_order": True,
            "nonzero_after_base_change_to": "Q(mu)",
            "critical_rees_face": True,
            "exact_ordinary_tail_slope": "1/2",
            "prescribed_nonzero_rational_amplitude": "open",
        },
        "critical_face_dexp_identity": (
            "dexp_Btau(dBtau/dtau) = tau^-6 "
            "dexp_Bbar((2p*d_p+3q*d_q-5)Bbar)"
        ),
        "claim_boundary": (
            "The linear normal coefficient is exact at every order, which "
            "also proves a nonlinear all-order cascade over Q(mu). This "
            "disproves cost-free finite-prefix normalization but does not "
            "settle simultaneous cancellation at a prescribed rational "
            "amplitude, classify arbitrary source prefixes, or determine "
            "the unrestricted minimax."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
