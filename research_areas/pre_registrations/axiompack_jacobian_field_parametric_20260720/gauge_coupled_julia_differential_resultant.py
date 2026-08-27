#!/usr/bin/env python3
"""Exact low-degree saturated resultants for the coupled Julia relation.

Both generators carry the universal tangent factor ``Y**2``.  On a selected
nonzero hidden branch the replay removes that factor from the zero-th
relation, differentiates the reduced relation using the two Julia equations,
and eliminates the hidden value.  The output is a degree-two/three
discriminator, not an all-degree resultant theorem.
"""

from __future__ import annotations

import hashlib
import json

import sympy as sp


def _sha256(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _reduced_relation_and_prolongation(
    reduced_p: sp.Expr,
    reduced_q: sp.Expr,
    *,
    hidden: sp.Symbol,
    source: sp.Symbol,
    endpoint: sp.Symbol,
    coefficient: sp.Symbol,
    coefficient_derivative: sp.Symbol,
) -> tuple[sp.Expr, sp.Expr]:
    """Return the saturated relation and its first total prolongation."""

    full_p = sp.expand(hidden**2 * reduced_p)
    full_q = sp.expand(hidden**2 * reduced_q)
    source_p = sp.expand(full_p.subs(hidden, source))
    endpoint_q = sp.expand(full_q.subs(hidden, endpoint))

    relation = sp.expand(
        endpoint_q * reduced_p
        - coefficient * endpoint * source_p * reduced_q
    )
    prolongation = sp.expand(
        coefficient
        * endpoint
        * source_p
        * sp.diff(full_q, hidden).subs(hidden, endpoint)
        * reduced_p
        + endpoint_q * sp.diff(reduced_p, hidden) * full_p
        - (
            coefficient_derivative * endpoint * source_p**2
            + coefficient**2 * endpoint * source_p**2
            + coefficient
            * endpoint
            * source_p
            * sp.diff(full_p, hidden).subs(hidden, source)
        )
        * reduced_q
        - coefficient
        * endpoint
        * source_p
        * sp.diff(reduced_q, hidden)
        * full_p
    )
    return relation, prolongation


def build_certificate() -> dict[str, object]:
    hidden, source, endpoint = sp.symbols("Y X Z")
    coefficient, coefficient_derivative = sp.symbols("A Ad")
    b, c, d = sp.symbols("b c d")

    relation_23, prolongation_23 = _reduced_relation_and_prolongation(
        sp.Integer(1),
        1 + b * hidden,
        hidden=hidden,
        source=source,
        endpoint=endpoint,
        coefficient=coefficient,
        coefficient_derivative=coefficient_derivative,
    )
    resultant_23 = sp.factor(
        sp.resultant(relation_23, prolongation_23, hidden)
    )
    terminal_23 = sp.expand(
        2 * coefficient**2 * source**4 * endpoint * b
        - coefficient**2 * source**4
        - 2 * coefficient * source**3 * endpoint * b
        + 2 * coefficient * source**2 * endpoint
        - coefficient_derivative * source**4 * endpoint * b
        - endpoint**3 * b
        - endpoint**2
    )
    expected_23 = sp.factor(
        coefficient
        * source**2
        * endpoint**3
        * b
        * (endpoint * b + 1)
        * terminal_23
    )
    assert sp.expand(resultant_23 - expected_23) == 0
    assert sp.expand(terminal_23.subs(endpoint, 0)) == (
        -coefficient**2 * source**4
    )

    relation_33, prolongation_33 = _reduced_relation_and_prolongation(
        1 + c * hidden,
        1 + d * hidden,
        hidden=hidden,
        source=source,
        endpoint=endpoint,
        coefficient=coefficient,
        coefficient_derivative=coefficient_derivative,
    )
    resultant_33 = sp.factor(
        sp.resultant(relation_33, prolongation_33, hidden)
    )
    factor_list_33 = sp.factor_list(resultant_33)[1]
    high_factor_33 = max(
        (factor for factor, _multiplicity in factor_list_33),
        key=lambda factor: sp.degree(factor, endpoint),
    )
    high_factor_constant_33 = sp.factor(
        high_factor_33.subs(endpoint, 0)
    )
    expected_high_factor_constant_33 = sp.factor(
        -coefficient**3 * source**4 * (source * c + 1)
    )
    assert high_factor_constant_33 == expected_high_factor_constant_33
    assert sp.degree(resultant_23, endpoint) == 7
    assert sp.degree(resultant_33, endpoint) == 10

    core: dict[str, object] = {
        "schema": "axiompack.coupled_julia_differential_resultant.v1",
        "saturation": {
            "full_generators": "p(Y)=Y^2*P(Y), q(Y)=Y^2*Q(Y)",
            "selected_hidden_branch_condition": "Y != 0",
            "reduced_relation": "q(Z)*P(Y)-A*Z*p(X)*Q(Y)",
            "prolongation_rule": (
                "differentiate the reduced relation along the two Julia "
                "rows and multiply by p(X)"
            ),
        },
        "quadratic_cubic": {
            "reduced_generators": ["P(Y)=1", "Q(Y)=1+b*Y"],
            "resultant_factorization": str(resultant_23),
            "endpoint_degree": int(sp.degree(resultant_23, endpoint)),
            "terminal_constant_coefficient": str(
                sp.factor(terminal_23.subs(endpoint, 0))
            ),
            "nonzero_conditions": ["A != 0", "X != 0", "b != 0"],
            "resultant_nonzero_under_conditions": True,
        },
        "cubic_cubic": {
            "reduced_generators": ["P(Y)=1+c*Y", "Q(Y)=1+d*Y"],
            "resultant_factorization": str(resultant_33),
            "endpoint_degree": int(sp.degree(resultant_33, endpoint)),
            "highest_endpoint_degree_factor_constant_coefficient": str(
                high_factor_constant_33
            ),
            "nonzero_conditions": [
                "A != 0",
                "X != 0",
                "1+X*c != 0",
                "c != d",
            ],
            "resultant_nonzero_under_conditions": True,
        },
        "next_induction_invariant": {
            "operator": "D_p(Q)=p*Q'",
            "root_condition": "p(y) != 0",
            "predicted_multiplicity_law": (
                "rootMultiplicity_y(D_p^[n](Q))="
                "rootMultiplicity_y(Q)-n"
            ),
            "universal_equilibrium_factor_must_be_saturated": True,
        },
        "claim_boundary": (
            "Exact symbolic nonvanishing is established only for the "
            "quadratic-cubic and cubic-cubic saturated families under the "
            "listed conditions. This does not prove all-degree resultant "
            "nonvanishing, classify invariant factors, construct a selected "
            "global lift, or close the Jacobian minimax lower bound."
        ),
    }
    return {**core, "certificate_sha256": _sha256(core)}


if __name__ == "__main__":
    print(json.dumps(build_certificate(), indent=2, sort_keys=True))
