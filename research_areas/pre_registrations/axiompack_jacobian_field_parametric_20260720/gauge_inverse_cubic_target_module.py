#!/usr/bin/env python3
"""Exact inverse-cubic descent and finite C-normal target module."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_minimized_third_jet import (  # noqa: E402
    _hamiltonian_field,
    _hamiltonian_field_window,
)


def run() -> dict[str, object]:
    p, q, c, w, z = sp.symbols("P Q C w z")
    c_polynomial = (
        4 * p**3
        - p**2
        - 18 * p * q
        + 27 * q**2
        + 4 * q
    )
    quadratic_relation = (
        27 * q**2
        - c_polynomial
        - (18 * p - 4) * q
        + 4 * p**3
        - p**2
    )
    assert sp.expand(quadratic_relation) == 0

    # The source function-field extension is monic of rank three.
    inverse_cubic = w**3 - w**2 + p * w - q
    cubic_polynomial = sp.Poly(inverse_cubic, w)
    coefficient_vectors: list[tuple[sp.Expr, sp.Expr, sp.Expr]] = [
        (sp.Integer(1), sp.Integer(0), sp.Integer(0)),
        (sp.Integer(0), sp.Integer(1), sp.Integer(0)),
        (sp.Integer(0), sp.Integer(0), sp.Integer(1)),
    ]
    for power in range(3, 13):
        older = coefficient_vectors[power - 3]
        middle = coefficient_vectors[power - 2]
        newer = coefficient_vectors[power - 1]
        recurrence = tuple(
            sp.expand(
                newer[index]
                - p * middle[index]
                + q * older[index]
            )
            for index in range(3)
        )
        coefficient_vectors.append(recurrence)
    for power, vector in enumerate(coefficient_vectors):
        remainder = sp.rem(
            sp.Poly(w**power, w),
            cubic_polynomial,
        ).as_expr()
        expected = vector[0] + vector[1] * w + vector[2] * w**2
        assert sp.expand(remainder - expected) == 0

    denominator = 1 - z + p * z**2 - q * z**3
    vector_generating_function = (
        (
            1 - z + p * z**2
            + (z - z**2) * w
            + z**2 * w**2
        )
        / denominator
    )
    truncated_generating_function = sum(
        z**power
        * (
            vector[0]
            + vector[1] * w
            + vector[2] * w**2
        )
        for power, vector in enumerate(coefficient_vectors)
    )
    assert all(
        sp.expand(
            sp.series(
                vector_generating_function,
                z,
                0,
                13,
            ).removeO().coeff(z, power)
            - truncated_generating_function.coeff(z, power)
        )
        == 0
        for power in range(13)
    )

    multiplication_companion = sp.Matrix([
        [0, 0, q],
        [1, 0, -p],
        [0, 1, 1],
    ])
    for power in range(12):
        current = sp.Matrix(coefficient_vectors[power])
        following = sp.Matrix(coefficient_vectors[power + 1])
        assert all(
            sp.expand(component) == 0
            for component in (
                multiplication_companion * current - following
            )
        )

    # A concrete generic C-normal pair verifies the five-generator
    # Hamiltonian module identity.  The displayed formula then follows for
    # arbitrary A(P,C), B(P,C) by the polynomial chain and product rules.
    coefficients = sp.symbols("a0:6 b0:6")
    normal_monomials = [1, p, c, p**2, p * c, c**2]
    normal_a = sum(
        coefficient * monomial
        for coefficient, monomial in zip(
            coefficients[:6], normal_monomials, strict=True
        )
    )
    normal_b = sum(
        coefficient * monomial
        for coefficient, monomial in zip(
            coefficients[6:], normal_monomials, strict=True
        )
    )
    hamiltonian = (
        normal_a.subs(c, c_polynomial)
        + q * normal_b.subs(c, c_polynomial)
    )
    x_p = _hamiltonian_field(p, p, q)
    x_q = _hamiltonian_field(q, p, q)
    x_c = _hamiltonian_field(c_polynomial, p, q)
    a_p = sp.diff(normal_a, p).subs(c, c_polynomial)
    a_c = sp.diff(normal_a, c).subs(c, c_polynomial)
    b_p = sp.diff(normal_b, p).subs(c, c_polynomial)
    b_c = sp.diff(normal_b, c).subs(c, c_polynomial)
    b_value = normal_b.subs(c, c_polynomial)
    module_reconstruction = tuple(
        sp.expand(
            a_p * x_p[index]
            + a_c * x_c[index]
            + b_value * x_q[index]
            + q * b_p * x_p[index]
            + q * b_c * x_c[index]
        )
        for index in range(2)
    )
    direct_field = _hamiltonian_field(
        hamiltonian, p, q
    )
    assert all(
        sp.expand(left - right) == 0
        for left, right in zip(
            module_reconstruction, direct_field, strict=True
        )
    )

    # Exact finite-window dimensions expose the cumulative Hilbert
    # recurrence associated with P-weight two and C-weight three in the
    # Rees index.
    dimensions: list[int] = []
    for rees_index in range(9):
        first_bound = 2 * rees_index + 6
        fields, _first_basis, _second_basis = (
            _hamiltonian_field_window(
                first_bound, first_bound + 2, p, q
            )
        )
        dimensions.append(len(fields))
    assert dimensions == [6, 7, 9, 12, 14, 17, 21, 24, 28]
    for index in range(6, len(dimensions)):
        assert dimensions[index] == (
            dimensions[index - 1]
            + dimensions[index - 2]
            - dimensions[index - 4]
            - dimensions[index - 5]
            + dimensions[index - 6]
        )
    hilbert_numerator = (
        6 + z - 4 * z**2 - 4 * z**3 - z**4 + 4 * z**5
    )
    hilbert_denominator = (
        (1 - z) * (1 - z**2) * (1 - z**3)
    )
    hilbert_series = hilbert_numerator / hilbert_denominator
    assert all(
        sp.series(
            hilbert_series, z, 0, len(dimensions)
        ).removeO().coeff(z, index)
        == dimensions[index]
        for index in range(len(dimensions))
    )

    return {
        "schema": (
            "axiompack.jacobian_inverse_cubic_target_module.v1"
        ),
        "inverse_cubic": str(inverse_cubic),
        "descent_module": {
            "base_ring": "QQ[P,Q]",
            "basis": ["1", "w", "w^2"],
            "rank": 3,
            "descent_obstruction_coordinates": ["w", "w^2"],
            "multiplication_by_w_companion": [
                [str(item) for item in row]
                for row in multiplication_companion.tolist()
            ],
            "power_recurrence": (
                "w^(n+3)=w^(n+2)-P*w^(n+1)+Q*w^n"
            ),
            "generating_function": str(
                vector_generating_function
            ),
        },
        "target_C_normal_module": {
            "base_ring": "QQ[P,C]",
            "scalar_basis": ["1", "Q"],
            "hamiltonian_field_generators": [
                "X_P", "X_Q", "X_C", "Q*X_P", "Q*X_C"
            ],
            "generic_polynomial_identity_replay": True,
        },
        "filtered_target_dimensions": dimensions,
        "candidate_cumulative_hilbert_series": str(
            hilbert_series
        ),
        "claim_boundary": (
            "target descent is reduced to two inverse-cubic module "
            "coordinates and target enumeration to a finite C-normal "
            "module; all-order vanishing of those two obstruction "
            "coordinates for the Jacobian family remains unproved"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
