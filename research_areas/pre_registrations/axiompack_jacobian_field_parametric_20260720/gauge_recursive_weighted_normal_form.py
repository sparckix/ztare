#!/usr/bin/env python3
"""Recursive gamma-adic target normal form in the canonical (A,D) chart.

This is the campaign generator.  The full inverse-Jacobian replays certify
the weighted target law once; this script then applies that law recursively
using truncated exceptional-coordinate series.
"""
from __future__ import annotations

import argparse
import json

import sympy as sp


Pair = tuple[sp.Expr, sp.Expr]


def _truncate(value: sp.Expr, g: sp.Symbol, order: int) -> sp.Expr:
    return sp.expand(sp.series(value, g, 0, order).removeO())


def _degree(value: sp.Expr, variable: sp.Symbol) -> int:
    reduced = sp.cancel(value)
    if reduced == 0:
        return -1
    assert variable not in sp.denom(reduced).free_symbols
    return int(sp.Poly(sp.numer(reduced), variable).degree())


def _regular(value: sp.Expr, s: sp.Symbol) -> bool:
    return sp.denom(sp.cancel(value)).subs(s, 0) != 0


def _family() -> dict[str, object]:
    s, y, g, z = sp.symbols("s y g z")
    v = (y - 3) / 2
    mu = 3 * (s - 4) / (2 * (s - 6))
    lam = -(s - 4) / 4
    w = (1 + mu * v) * g
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
    family = (
        sp.cancel(g * lam / mu * (1 + p.subs(z, w) / g)),
        sp.cancel(
            g**2 * (1 + mu * v + q.subs(z, w) / g**2) / lam
        ),
    )
    jacobian = sp.Matrix([
        [sp.diff(item, variable) for variable in (y, g)]
        for item in family
    ])
    determinant = sp.factor(jacobian.det())
    assert sp.factor(determinant + g**2 / 2) == 0
    return {
        "symbols": (s, y, g),
        "family": family,
        "jacobian": jacobian,
        "determinant": determinant,
    }


def _inverse_action_truncated(
    jacobian: sp.Matrix,
    value: Pair,
    g: sp.Symbol,
    maximum_layer: int,
) -> Pair:
    # The determinant is exactly -g^2/2.  Keep only the numerator precision
    # that can survive division into the requested gamma layers.
    numerator_order = maximum_layer + 3
    first = _truncate(
        jacobian[1, 1] * value[0] - jacobian[0, 1] * value[1],
        g,
        numerator_order,
    )
    second = _truncate(
        -jacobian[1, 0] * value[0] + jacobian[0, 0] * value[1],
        g,
        numerator_order,
    )
    result = (
        _truncate(-2 * first / g**2, g, maximum_layer + 1),
        _truncate(-2 * second / g**2, g, maximum_layer + 2),
    )
    assert all(not item.has(sp.zoo, sp.nan) for item in result)
    return result


def _pullback(
    hamiltonian: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
    family: Pair,
    jacobian: sp.Matrix,
    g: sp.Symbol,
    maximum_layer: int,
) -> Pair:
    value = (
        _truncate(
            sp.diff(hamiltonian, q).subs({p: family[0], q: family[1]}),
            g,
            maximum_layer + 3,
        ),
        _truncate(
            -sp.diff(hamiltonian, p).subs({p: family[0], q: family[1]}),
            g,
            maximum_layer + 3,
        ),
    )
    return _inverse_action_truncated(
        jacobian, value, g, maximum_layer
    )


def _parity_part(
    polynomial: sp.Expr,
    coordinate: sp.Symbol,
    parity: int,
) -> sp.Expr:
    reflected = polynomial.subs(coordinate, -coordinate)
    return sp.factor(
        (polynomial + reflected) / 2
        if parity == 0
        else (polynomial - reflected) / 2
    )


def run(maximum_layer: int = 8) -> dict[str, object]:
    data = _family()
    s, y, g = data["symbols"]
    family = data["family"]
    jacobian = data["jacobian"]
    p, q, x = sp.symbols("P Q A")

    derivative = (
        sp.diff(family[0], s),
        sp.diff(family[1], s),
    )
    current = _inverse_action_truncated(
        jacobian, derivative, g, maximum_layer
    )

    # Fixed first target slice.  Its Q^2 term begins at layer one.
    seed_hamiltonian = -q**2 / 4
    seed_pullback = _pullback(
        seed_hamiltonian,
        p,
        q,
        family,
        jacobian,
        g,
        maximum_layer,
    )
    current = tuple(
        _truncate(
            current[index] - seed_pullback[index],
            g,
            maximum_layer + 1 + index,
        )
        for index in range(2)
    )

    leading_a = sp.factor(sp.diff(family[0], g).subs(g, 0))
    leading_d = sp.factor(
        sp.diff(family[1], g, 2).subs(g, 0) / 2
    )
    slope = sp.factor(sp.diff(leading_a, y))
    intercept = sp.factor(leading_a.subs(y, 0))
    assert sp.factor(leading_a - (slope * y + intercept)) == 0
    assert slope.subs(s, 0) == 1
    assert sp.factor(
        leading_a * sp.diff(leading_d, y)
        - 2 * slope * leading_d
        - sp.Rational(1, 2)
    ) == 0
    d_in_a = sp.factor(
        leading_d.subs(y, (x - intercept) / slope)
    )
    assert _degree(d_in_a, x) == 2
    assert sp.Poly(d_in_a, x).coeff_monomial(x) == 0

    records: list[dict[str, object]] = []
    controls: list[sp.Expr] = [seed_hamiltonian]
    for m in range(maximum_layer + 1):
        d = m + 3
        tangential_y = sp.factor(current[0].coeff(g, m))
        normal_y = sp.factor(current[1].coeff(g, m + 1))
        assert sp.factor(
            normal_y + sp.diff(tangential_y, y) / d
        ) == 0
        tangential_a = sp.factor(
            tangential_y.subs(y, (x - intercept) / slope)
        )
        removable = _parity_part(tangential_a, x, d % 2)
        residual_before = sp.factor(tangential_a - removable)
        removable_degree = _degree(removable, x)
        if removable_degree > d:
            records.append({
                "layer": m,
                "weight": d,
                "status": "target_image_degree_exceeded",
                "removable_degree": removable_degree,
                "target_degree": d,
            })
            break

        monomials = [
            p ** (d - 2 * j) * q**j
            for j in range(d // 2 + 1)
        ]
        images = [
            sp.factor(
                -2
                * d
                * monomial.subs({p: x, q: d_in_a})
            )
            for monomial in monomials
        ]
        parity_indices = list(range(d % 2, d + 1, 2))
        matrix = sp.Matrix([
            [
                sp.Poly(image, x).coeff_monomial(x**index)
                for image in images
            ]
            for index in parity_indices
        ])
        rhs = sp.Matrix([
            sp.Poly(removable, x).coeff_monomial(x**index)
            for index in parity_indices
        ])
        determinant = sp.factor(matrix.det())
        assert determinant.subs(s, 0) != 0
        coefficients = tuple(
            sp.factor(value) for value in matrix.inv() * rhs
        )
        assert all(_regular(value, s) for value in coefficients)
        if m >= 1:
            assert all(value.subs(s, 0) == 0 for value in coefficients)

        layer_hamiltonian = sp.expand(sum(
            coefficients[index] * monomial
            for index, monomial in enumerate(monomials)
        ))
        layer_pullback = _pullback(
            layer_hamiltonian,
            p,
            q,
            family,
            jacobian,
            g,
            maximum_layer,
        )
        pulled_leading_a = sp.factor(
            layer_pullback[0].coeff(g, m).subs(
                y, (x - intercept) / slope
            )
        )
        assert sp.factor(pulled_leading_a - removable) == 0
        current = tuple(
            _truncate(
                current[index] - layer_pullback[index],
                g,
                maximum_layer + 1 + index,
            )
            for index in range(2)
        )
        residual_y = sp.factor(current[0].coeff(g, m))
        residual_a = sp.factor(
            residual_y.subs(y, (x - intercept) / slope)
        )
        assert sp.factor(
            _parity_part(residual_a, x, d % 2)
        ) == 0
        assert sp.factor(residual_a - residual_before) == 0
        controls.append(layer_hamiltonian)
        records.append({
            "layer": m,
            "weight": d,
            "input_degree_A": _degree(tangential_a, x),
            "target_image_parity": d % 2,
            "target_image_rank": len(monomials),
            "target_unit_determinant": str(determinant),
            "control_coefficients": [str(value) for value in coefficients],
            "residual_A": str(residual_a),
            "residual_degree_A": _degree(residual_a, x),
            "residual_leading_coefficient": str(
                sp.Poly(residual_a, x).LC()
                if residual_a != 0 else 0
            ),
            "regular": True,
            "seed_zero_after_first_layer": (
                m == 0
                or all(value.subs(s, 0) == 0 for value in coefficients)
            ),
        })

    completed = len(records)
    degree_sequence = [
        row.get("residual_degree_A")
        for row in records
        if row.get("status") is None
    ]
    return {
        "schema": "axiompack.jacobian_recursive_weighted_normal_form.v1",
        "maximum_requested_layer": maximum_layer,
        "completed_layers": completed,
        "exceptional_coordinates": {
            "A": str(leading_a),
            "D_in_A": str(d_in_a),
            "A_slope": str(slope),
            "A_intercept": str(intercept),
            "jacobian_identity": "A*D'-2*A'*D=1/2",
        },
        "fixed_seed_hamiltonian": "-Q^2/4",
        "layers": records,
        "residual_degree_sequence": degree_sequence,
        "degree_equals_layer_on_completed_prefix": all(
            degree == index
            for index, degree in enumerate(degree_sequence)
        ),
        "claim_boundary": (
            "this is an exact finite gamma-adic prefix generated by the "
            "all-layer target-image theorem; an asymptotic claim requires "
            "a proved recurrence or closed normal form"
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Compute an exact finite prefix of the canonical weighted "
            "exceptional normal form."
        )
    )
    parser.add_argument(
        "maximum_layer",
        nargs="?",
        type=int,
        default=8,
        help="largest gamma layer to compute (default: 8)",
    )
    arguments = parser.parse_args()
    if arguments.maximum_layer < 0:
        parser.error("maximum_layer must be nonnegative")
    print(json.dumps(
        run(arguments.maximum_layer),
        indent=2,
        sort_keys=True,
    ))
