#!/usr/bin/env python3
"""Exact negative controls for finite-fiber-to-elimination promotion.

An empty saturated fiber over ``F = 0`` does not imply that the projection
to the visible endpoint is algebraically finite.  A dominant component may
approach either an equilibrium or infinity over that divisor.  The replay
checks the elimination ideals and the two monomial boundary models exactly.
"""

from __future__ import annotations

import hashlib
import json

import sympy as sp


def _sha256(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _elimination_row(
    name: str,
    equations: tuple[sp.Expr, ...],
    *,
    endpoint: sp.Symbol,
    hidden: sp.Symbol,
    inverse: sp.Symbol,
) -> dict[str, object]:
    basis = sp.groebner(
        equations,
        hidden,
        inverse,
        endpoint,
        order="lex",
    )
    endpoint_only = tuple(
        polynomial.as_expr()
        for polynomial in basis.polys
        if not polynomial.as_expr().has(hidden, inverse)
    )
    specialized = sp.groebner(
        tuple(
            sp.expand(equation.subs(endpoint, 0))
            for equation in equations
        ),
        hidden,
        inverse,
        order="lex",
    )
    assert endpoint_only == ()
    assert specialized.contains(sp.Integer(1))
    return {
        "name": name,
        "equations": [str(equation) for equation in equations],
        "lex_groebner_basis": [
            str(polynomial.as_expr()) for polynomial in basis.polys
        ],
        "endpoint_elimination_generators": [],
        "special_fiber_groebner_basis": [
            str(polynomial.as_expr()) for polynomial in specialized.polys
        ],
        "special_fiber_is_empty": True,
        "visible_projection_is_zariski_dense": True,
    }


def build_certificate() -> dict[str, object]:
    endpoint, hidden, inverse = sp.symbols("F Y Z")

    bare_equations = (
        endpoint * hidden - 1,
        inverse * hidden - 1,
    )
    equilibrium_equations = (
        endpoint**2 - hidden,
        inverse * hidden - 1,
    )
    infinity_equations = bare_equations

    bare = _elimination_row(
        "dominant_reciprocal_component",
        bare_equations,
        endpoint=endpoint,
        hidden=hidden,
        inverse=inverse,
    )
    equilibrium = _elimination_row(
        "coupled_monomial_equilibrium_limit_r2_s3",
        equilibrium_equations,
        endpoint=endpoint,
        hidden=hidden,
        inverse=inverse,
    )
    infinity = _elimination_row(
        "coupled_monomial_infinity_limit_r3_s2",
        infinity_equations,
        endpoint=endpoint,
        hidden=hidden,
        inverse=inverse,
    )

    probe = sp.symbols("f", nonzero=True)
    assert sp.expand(
        bare_equations[0].subs({endpoint: probe, hidden: 1 / probe})
    ) == 0
    assert sp.expand(
        equilibrium_equations[0].subs(
            {endpoint: probe, hidden: probe**2}
        )
    ) == 0
    assert sp.expand(
        infinity_equations[0].subs(
            {endpoint: probe, hidden: 1 / probe}
        )
    ) == 0

    core: dict[str, object] = {
        "schema": "axiompack.coupled_julia_projection_fallacy.v1",
        "models": [bare, equilibrium, infinity],
        "coupled_monomial_normal_form": {
            "relation_before_saturation": "F^(s-1)*Y^r-a*Y^s",
            "equilibrium_case": {
                "exponents": {"r": 2, "s": 3},
                "saturated_relation_at_a_one": "F^2-Y",
                "punctured_solution": "Y=F^2",
                "boundary": "Y tends to the equilibrium 0 as F tends to 0",
            },
            "infinity_case": {
                "exponents": {"r": 3, "s": 2},
                "saturated_relation_at_a_one": "F*Y-1",
                "punctured_solution": "Y=1/F",
                "boundary": "Y tends to infinity as F tends to 0",
            },
        },
        "logical_verdict": {
            "empty_regular_fiber_implies_endpoint_eliminant": False,
            "required_replacement": (
                "endpoint eliminant or dominant invariant component; "
                "normalize a dominant component and classify its boundary "
                "as equilibrium, infinity, or proportional"
            ),
        },
        "claim_boundary": (
            "The exact Groebner replays refute promotion from an empty "
            "saturated fiber at F=0 to a nonzero endpoint eliminant. They do "
            "not prove that the critical coupled-Julia differential ideal "
            "has a dominant component, normalize such a component, or "
            "exclude any selected two-flow factorization."
        ),
    }
    return {**core, "certificate_sha256": _sha256(core)}


if __name__ == "__main__":
    print(json.dumps(build_certificate(), indent=2, sort_keys=True))
