#!/usr/bin/env python3
"""Exact low-weight target Hamiltonian Lie-algebra classification replay."""

from __future__ import annotations

import json

import sympy as sp


X, Y, delta, r = sp.symbols("X Y delta r")


def bracket(left: sp.Expr, right: sp.Expr) -> sp.Expr:
    """Campaign Poisson convention: H_Y K_X - H_X K_Y."""

    return sp.expand(
        sp.diff(left, Y) * sp.diff(right, X)
        - sp.diff(left, X) * sp.diff(right, Y)
    )


def spectral_project(
    value: sp.Expr,
    eigenvalue: int,
    spectrum: tuple[int, ...],
) -> sp.Expr:
    """Lagrange projector for ad_(XY) at one eigenvalue."""

    result = value
    denominator = sp.Integer(1)
    generator = X * Y
    for other in spectrum:
        if other == eigenvalue:
            continue
        result = sp.expand(bracket(generator, result) - other * result)
        denominator *= eigenvalue - other
    return sp.factor(result / denominator)


def main() -> None:
    spectrum = (3, 1, -1, -2, -3)
    mixed = sp.expand((X - delta * Y) ** 3 + r * Y**2)
    diagonal = X * Y

    # The shear X=P+delta*Q, Y=Q is symplectic in the campaign convention.
    assert bracket(X, Y) == -1
    assert bracket(diagonal, X**4 * Y**2) == 2 * X**4 * Y**2

    cubic_projection = spectral_project(mixed, 3, spectrum)
    quadratic_projection = spectral_project(mixed, -2, spectrum)
    assert sp.expand(cubic_projection - X**3) == 0
    assert sp.expand(quadratic_projection - r * Y**2) == 0

    x3 = cubic_projection
    y2 = sp.cancel(quadratic_projection / r)
    first = bracket(x3, y2)
    x4 = sp.cancel(bracket(x3, first) / 18)
    x3y = sp.cancel(-bracket(x4, y2) / 8)
    assert sp.expand(first + 6 * X**2 * Y) == 0
    assert sp.expand(x4 - X**4) == 0
    assert sp.expand(x3y - X**3 * Y) == 0

    ray = x4
    ray_rows: list[dict[str, object]] = []
    coefficient = sp.Integer(1)
    for index in range(9):
        expected = sp.expand(coefficient * X ** (4 + 2 * index))
        assert sp.expand(ray - expected) == 0
        ray_rows.append(
            {
                "adjoint_depth": index,
                "coefficient": str(coefficient),
                "ordinary_degree": 4 + 2 * index,
            }
        )
        ray = bracket(x3y, ray)
        coefficient *= 4 + 2 * index

    # If the second direction has b=0, it is Q^2 modulo the mixed line,
    # and P^3 is recovered by direct subtraction.
    direct_second = Y**2
    assert sp.expand(mixed.subs(delta, 0) - r * direct_second - X**3) == 0

    # The excluded r=0 boundary contains the finite Borel plane at delta=0.
    assert bracket(X * Y, X**3) == 3 * X**3

    print(
        json.dumps(
            {
                "schema": (
                    "axiompack.jacobian_low_weight_target_lie_classification.v1"
                ),
                "claim": (
                    "a mixed P^3+rQ^2 line with r nonzero and any independent "
                    "second direction in span(P^3,PQ,Q^2) generates an "
                    "infinite-dimensional target Hamiltonian Lie algebra"
                ),
                "symplectic_shear": {
                    "X": "P + delta*Q",
                    "Y": "Q",
                    "second_generator": "X*Y",
                },
                "spectral_projectors": {
                    "spectrum": list(spectrum),
                    "weight_3": str(cubic_projection),
                    "weight_minus_2": str(quadratic_projection),
                },
                "derived_generators": {
                    "X_cubed": str(x3),
                    "Y_squared": str(y2),
                    "X_fourth": str(x4),
                    "X_cubed_Y": str(x3y),
                },
                "all_order_ray": {
                    "formula": "ad_(X^3*Y)^j(X^4)=c_j*X^(4+2*j)",
                    "recurrence": "c_(j+1)=(4+2*j)*c_j",
                    "checked_prefix": ray_rows,
                    "nonzero_in_characteristic_zero": True,
                },
                "boundary": {
                    "r_zero_delta_zero": "span(P^3,PQ) is the finite Borel plane",
                    "higher_weight_extensions": "not classified",
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
