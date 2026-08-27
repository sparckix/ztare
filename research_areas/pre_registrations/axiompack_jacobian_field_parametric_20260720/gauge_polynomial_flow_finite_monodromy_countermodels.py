#!/usr/bin/env python3
"""Exact negative controls for finite polynomial-flow continuation routes.

The replay checks two one-variable autonomous polynomial flows.  The cubic
model has a two-sheeted finite regular time-one correspondence.  The
quartic model has an Abel coordinate whose time-one equation is the Lambert-W
equation; sampled branches verify the finite regular behavior numerically,
while the exact output keeps the functional equation separate from the
classical infinite-branch fact.
"""

from __future__ import annotations

import hashlib
import json

import sympy as sp


def _sha256(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_certificate(sample_radius: int = 8) -> dict[str, object]:
    if sample_radius < 2:
        raise ValueError("sample_radius must be at least two")

    x, y, Y, w = sp.symbols("x y Y w")

    cubic_generator = y**3
    cubic_endpoint = x / sp.sqrt(1 - 2 * x**2)
    cubic_julia_residual = sp.simplify(
        cubic_endpoint**3
        - sp.diff(cubic_endpoint, x) * cubic_generator.subs(y, x)
    )
    cubic_correspondence_residual = sp.factor(
        Y**2 * (1 - 2 * x**2) - x**2
    )
    x0 = sp.Rational(1, 2)
    cubic_sheets = (
        sp.sqrt(2) / 2,
        -sp.sqrt(2) / 2,
    )
    cubic_rows = []
    for endpoint in cubic_sheets:
        correspondence = sp.simplify(
            cubic_correspondence_residual.subs({x: x0, Y: endpoint})
        )
        generator_value = sp.simplify(cubic_generator.subs(y, endpoint))
        assert correspondence == 0
        assert generator_value != 0
        cubic_rows.append({
            "endpoint": str(endpoint),
            "correspondence_residual": str(correspondence),
            "generator_value": str(generator_value),
        })
    assert cubic_julia_residual == 0

    quartic_generator = y**2 * (1 - y)
    abel_coordinate = sp.log(y / (1 - y)) - 1 / y
    abel_derivative_residual = sp.simplify(
        sp.diff(abel_coordinate, y) - 1 / quartic_generator
    )
    assert abel_derivative_residual == 0

    # At x=1/2 the time-one Abel relation reduces exactly to
    # w*exp(w)=1 with Y=1/(1+w).
    quartic_endpoint = 1 / (1 + w)
    quartic_generator_at_endpoint = sp.factor(
        quartic_generator.subs(y, quartic_endpoint)
    )
    assert quartic_generator_at_endpoint == w / (w + 1) ** 3
    time_one_exponential_residual = sp.factor(
        ((1 / quartic_endpoint) - 1)
        * sp.exp((1 / quartic_endpoint) - 1)
        - 1
    )
    assert sp.simplify(
        time_one_exponential_residual.subs(w * sp.exp(w), 1)
    ) == 0

    sampled_rows = []
    sampled_values: list[complex] = []
    for branch in range(-sample_radius, sample_radius + 1):
        branch_value = sp.N(sp.LambertW(1, branch), 60)
        endpoint_value = sp.N(1 / (1 + branch_value), 50)
        generator_value = sp.N(
            quartic_generator.subs(y, endpoint_value), 40
        )
        defining_residual = sp.N(
            branch_value * sp.exp(branch_value) - 1, 30
        )
        endpoint_complex = complex(endpoint_value)
        assert abs(complex(defining_residual)) < 1e-25
        assert abs(complex(generator_value)) > 1e-12
        assert all(
            abs(endpoint_complex - previous) > 1e-12
            for previous in sampled_values
        )
        sampled_values.append(endpoint_complex)
        sampled_rows.append({
            "branch": branch,
            "endpoint_real": str(sp.re(endpoint_value)),
            "endpoint_imag": str(sp.im(endpoint_value)),
            "generator_abs": str(abs(complex(generator_value))),
            "defining_residual_abs": str(abs(complex(defining_residual))),
        })

    core: dict[str, object] = {
        "schema": "axiompack.polynomial_flow_finite_monodromy_countermodels.v1",
        "cubic_two_sheet_model": {
            "generator": "y^3",
            "time_one_correspondence": "Y^2*(1-2*x^2)=x^2",
            "selected_source": "1/2",
            "julia_residual": str(cubic_julia_residual),
            "sheets": cubic_rows,
            "finite_regular_sheet_exchange": True,
        },
        "quartic_infinite_sheet_model": {
            "generator": "y^2*(1-y)",
            "abel_coordinate": "log(y/(1-y))-1/y",
            "abel_derivative_residual": str(abel_derivative_residual),
            "selected_source": "1/2",
            "time_one_lambert_equation": "w*exp(w)=1",
            "endpoint_formula": "Y_k=1/(1+LambertW_k(1))",
            "generator_at_endpoint": str(quartic_generator_at_endpoint),
            "sampled_branch_radius": sample_radius,
            "sampled_branches": sampled_rows,
            "classical_infinite_branch_fact_formalized": False,
        },
        "claim_boundary": (
            "The exact identities refute any general finite-implies-"
            "equilibrium step for polynomial autonomous time-one maps. The "
            "sampled Lambert-W rows are a stress test, not a formal proof of "
            "the classical infinite-branch theorem and not a factorization "
            "of the critical Jacobian holonomy."
        ),
    }
    return {**core, "certificate_sha256": _sha256(core)}


if __name__ == "__main__":
    print(json.dumps(build_certificate(), indent=2, sort_keys=True))
