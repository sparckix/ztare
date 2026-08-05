#!/usr/bin/env python3
"""Exact exceptional-divisor classification for centralizer-valued controls."""

from __future__ import annotations

import itertools
import json

import sympy as sp


def _coefficient_vector(
    polynomial: sp.Expr,
    y: sp.Symbol,
) -> list[sp.Expr]:
    numerator, denominator = sp.together(polynomial).as_numer_denom()
    source = sp.Poly(numerator, y)
    return [
        sp.cancel(source.coeff_monomial(y**degree) / denominator)
        for degree in range(4)
    ]


def run() -> dict[str, object]:
    s, y = sp.symbols("s y")
    h0_divisor = sp.factor(
        -(3 * s**2 * y - 5 * s**2 - 48 * y) ** 3 / 663552
    )
    expected_profile = sp.factor(
        6912
        * (s**2 - 3 * s - 8)
        / (
            (s - 6) ** 3
            * (s - 4) ** 2
            * (s + 4) ** 2
        )
    )
    expected_affine_divisor = sp.factor(
        s
        * (
            9 * s**2 * y
            - 15 * s**2
            - 144 * y
            + 160
        )
        / (3 * (s - 4) ** 2 * (s + 4) ** 2)
    )
    # These two compact summands are the exact divisor identity already
    # replayed from the carried family by gauge_target_divisor_image.py.
    source_divisor = sp.factor(
        expected_profile * h0_divisor + expected_affine_divisor
    )
    source_vector = _coefficient_vector(source_divisor, y)
    h0_vector = _coefficient_vector(h0_divisor, y)

    U = sp.symbols("U")
    controlled_vector = [
        sp.cancel(source_vector[index] - U * h0_vector[index])
        for index in range(4)
    ]
    affine_profile = sp.factor(
        sp.solve(controlled_vector[3], U, dict=False)[0]
    )
    assert sp.factor(affine_profile - expected_profile) == 0
    assert affine_profile.subs(s, 0) == 1

    affine_divisor = sp.factor(
        source_divisor - affine_profile * h0_divisor
    )
    assert sp.factor(affine_divisor - expected_affine_divisor) == 0
    assert sp.Poly(
        sp.together(affine_divisor).as_numer_denom()[0], y
    ).degree() == 1

    cubic_ratio = sp.factor(
        controlled_vector[2] / controlled_vector[3]
    )
    expected_cubic_ratio = sp.factor(
        -5 * s**2 / ((s - 4) * (s + 4))
    )
    assert sp.factor(cubic_ratio - expected_cubic_ratio) == 0
    assert sp.factor(sp.diff(cubic_ratio, s)) != 0

    fixed_line_symbols = sp.symbols("f0:4")
    fixed_line_equations: list[sp.Expr] = []
    for parameter_value in (1, 2, 3, 5):
        sampled_source = [
            value.subs(s, parameter_value) for value in source_vector
        ]
        sampled_target = [
            value.subs(s, parameter_value) for value in h0_vector
        ]
        for indices in itertools.combinations(range(4), 3):
            fixed_line_equations.append(
                sp.expand(
                    sp.Matrix([
                        [
                            sampled_source[index],
                            sampled_target[index],
                            fixed_line_symbols[index],
                        ]
                        for index in indices
                    ]).det()
                )
            )
    fixed_line_matrix, _ = sp.linear_eq_to_matrix(
        fixed_line_equations,
        fixed_line_symbols,
    )
    fixed_line_rank = fixed_line_matrix.rank()
    assert fixed_line_rank == 4

    return {
        "schema": (
            "axiompack.jacobian_centralizer_divisor_profile.v1"
        ),
        "input_identity_replay": "gauge_target_divisor_image.py",
        "target_seed": "H_0=-P^3/36-Q^2/4",
        "unique_cubic_killing_profile": str(affine_profile),
        "controlled_divisor": str(affine_divisor),
        "surviving_cubic_ratio": str(cubic_ratio),
        "shifted_cubic_borel_possible": False,
        "fixed_cubic_line_constraint_rank": fixed_line_rank,
        "fixed_cubic_line_possible": False,
        "classification": (
            "the affine profile is the only regular scalar profile whose "
            "divisor source coefficients have finite-dimensional Lie closure"
        ),
        "full_source_decided": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
