#!/usr/bin/env python3
"""Exact layer-two target quotient after divisor and layer-one normalization."""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_first_transverse_target_quotient import (  # noqa: E402
    _degree,
    _hamiltonian_pullback_layers,
    _regular_zero_at_seed,
)
from gauge_regular_singular_connection import source_only_connection  # noqa: E402
from gauge_target_divisor_image import _target_lift  # noqa: E402


Pair = tuple[sp.Expr, sp.Expr]


def _coordinate_components(
    field: Pair,
    v: sp.Symbol,
    t: sp.Symbol,
    y: sp.Symbol,
    g: sp.Symbol,
) -> Pair:
    substitution = {
        v: (y - 3) / 2,
        t: g - 1 + 3 * (y - 3) / 4,
    }
    return (
        sp.cancel((2 * field[0]).subs(substitution)),
        sp.cancel(
            (field[1] - sp.Rational(3, 2) * field[0]).subs(substitution)
        ),
    )


def _layer(
    components: Pair,
    m: int,
    y: sp.Symbol,
    g: sp.Symbol,
) -> Pair:
    tangential = sp.factor(
        sp.diff(components[0], g, m).subs(g, 0) / sp.factorial(m)
    )
    normal = sp.factor(
        sp.diff(components[1], g, m + 1).subs(g, 0)
        / sp.factorial(m + 1)
    )
    assert sp.factor(normal + sp.diff(tangential, y) / (m + 3)) == 0
    return tangential, normal


def _vector(polynomial: sp.Expr, y: sp.Symbol, degree: int) -> sp.Matrix:
    value = sp.Poly(sp.cancel(polynomial), y)
    return sp.Matrix([
        value.coeff_monomial(y**index) for index in range(degree + 1)
    ])


def run() -> dict[str, object]:
    data = source_only_connection()
    s, v, t, _ = data["symbols"]
    gamma = data["gamma"]
    family = data["family"]
    source_only = data["source_only"]
    p, q, y, g = sp.symbols("P Q y g")

    family_components: Pair = tuple(
        sp.cancel(
            family[index].subs({
                v: (y - 3) / 2,
                t: g - 1 + 3 * (y - 3) / 4,
            })
        )
        for index in range(2)
    )  # type: ignore[assignment]

    hamiltonians = {
        "P3": p**3,
        "PQ": p * q,
        "Q2": q**2,
        "P4": p**4,
        "P2Q": p**2 * q,
        "P5": p**5,
        "P3Q": p**3 * q,
        "PQ2": p * q**2,
    }
    pullback_layers = {
        name: _hamiltonian_pullback_layers(
            hamiltonian,
            p,
            q,
            family_components,
            y,
            g,
            maximum_layer=2,
        )
        for name, hamiltonian in hamiltonians.items()
    }

    controls = {
        "P3": sp.factor(
            96
            * (s**2 - 12 * s + 16)
            / ((s - 6) ** 3 * (s - 4) ** 2 * (s + 4) ** 2)
        ),
        "PQ": sp.factor(2 * s / ((s - 4) * (s + 4))),
        "Q2_seed": -sp.Rational(1, 4),
        "P4": sp.factor(
            -864
            * s
            * (5 * s - 12)
            / ((s - 6) ** 4 * (s - 4) * (s + 4) ** 3)
        ),
        "P2Q": sp.factor(
            -12
            * s
            * (5 * s**2 + 6 * s - 36)
            / ((s - 6) ** 2 * (s + 4) ** 3)
        ),
        "Q2_layer1": sp.factor(
            -s**2
            * (5 * s**2 - 14 * s - 66)
            / (24 * (s + 4) ** 2)
        ),
    }
    source_only_components = _coordinate_components(
        source_only, v, t, y, g
    )
    source_only_layers = [
        _layer(source_only_components, layer, y, g)
        for layer in range(3)
    ]
    normalized_layers = [
        tuple(
            sp.factor(
                source_only_layers[layer][component]
                - controls["P3"]
                * pullback_layers["P3"][layer][component]
                - controls["PQ"]
                * pullback_layers["PQ"][layer][component]
                - controls["Q2_seed"]
                * pullback_layers["Q2"][layer][component]
                - controls["P4"]
                * pullback_layers["P4"][layer][component]
                - controls["P2Q"]
                * pullback_layers["P2Q"][layer][component]
                - controls["Q2_layer1"]
                * pullback_layers["Q2"][layer][component]
            )
            for component in range(2)
        )
        for layer in range(3)
    ]
    assert all(
        sp.factor(component.subs(s, 0)) == 0
        for layer in normalized_layers
        for component in layer
    )

    for name in ("P5", "P3Q", "PQ2"):
        hamiltonian = hamiltonians[name]
        target = (sp.diff(hamiltonian, q), -sp.diff(hamiltonian, p))
        assert _target_lift(target, p, q)

    layer0, layer1, layer2 = normalized_layers
    assert sp.factor(
        layer0[0]
        - 160 * s / (3 * (s - 4) ** 2 * (s + 4) ** 2)
    ) == 0
    assert sp.factor(layer1[0] + 16 * s * y / (s + 4) ** 3) == 0

    target_names = ["P5", "P3Q", "PQ2"]
    target_layers = {
        name: pullback_layers[name][2]
        for name in target_names
    }

    leading_a = sp.factor(sp.diff(family_components[0], g).subs(g, 0))
    leading_d = sp.factor(
        sp.diff(family_components[1], g, 2).subs(g, 0) / 2
    )
    assert sp.factor(
        leading_a * sp.diff(leading_d, y)
        - 2 * sp.diff(leading_a, y) * leading_d
        - sp.Rational(1, 2)
    ) == 0
    for name in target_names:
        expected = sp.factor(
            -10 * hamiltonians[name].subs({
                p: leading_a,
                q: leading_d,
            })
        )
        assert sp.factor(target_layers[name][0] - expected) == 0

    a_coordinate = sp.Symbol("Abar")
    a_slope = sp.factor(sp.diff(leading_a, y))
    a_offset = sp.factor(leading_a.subs(y, 0))
    assert a_slope.subs(s, 0) != 0
    y_from_a = sp.factor((a_coordinate - a_offset) / a_slope)
    layer_two_in_a = sp.factor(layer2[0].subs(y, y_from_a))
    canonical_even_residue = sp.factor(
        (
            layer_two_in_a
            + layer_two_in_a.subs(a_coordinate, -a_coordinate)
        )
        / 2
    )
    canonical_odd_part = sp.factor(
        layer_two_in_a - canonical_even_residue
    )
    for name in target_names:
        target_in_a = sp.factor(
            target_layers[name][0].subs(y, y_from_a)
        )
        assert sp.factor(
            target_in_a + target_in_a.subs(
                a_coordinate, -a_coordinate
            )
        ) == 0
    assert canonical_even_residue != 0
    linearized_even_residue = sp.factor(
        sp.diff(canonical_even_residue, s).subs(s, 0)
    )

    degree = max(
        _degree(item, y)
        for item in [layer2[0]]
        + [target_layers[name][0] for name in target_names]
    )
    matrix = sp.Matrix.hstack(*[
        _vector(target_layers[name][0], y, degree)
        for name in target_names
    ])
    vector = _vector(layer2[0], y, degree)
    rank = int(matrix.rank())
    augmented_rank = int(matrix.row_join(vector).rank())
    assert rank == 3
    seed_minor = sp.factor(
        matrix.extract([1, 3, 5], range(3)).det().subs(s, 0)
    )
    assert seed_minor != 0
    seed_matrix = matrix.subs(s, 0)
    linearized_vector = vector.diff(s).subs(s, 0)
    linearized_augmented = seed_matrix.row_join(linearized_vector)
    linearized_witness: dict[str, object] | None = None
    for rows in itertools.combinations(
        range(linearized_augmented.rows), 4
    ):
        determinant = sp.factor(
            linearized_augmented.extract(rows, range(4)).det()
        )
        if determinant != 0:
            linearized_witness = {
                "rows": list(rows),
                "matrix": [
                    [
                        str(linearized_augmented[row, column])
                        for column in range(4)
                    ]
                    for row in rows
                ],
                "determinant": str(determinant),
            }
            break
    assert linearized_witness is not None

    candidates: list[dict[str, object]] = []
    for rows in itertools.combinations(range(matrix.rows), rank):
        square = matrix.extract(rows, range(rank))
        if sp.factor(square.det()) == 0:
            continue
        coefficients = tuple(
            sp.factor(value)
            for value in square.inv() * vector.extract(rows, [0])
        )
        if not all(
            _regular_zero_at_seed(value, s) for value in coefficients
        ):
            continue
        remainder = sp.factor(
            layer2[0]
            - sum(
                coefficients[index] * target_layers[name][0]
                for index, name in enumerate(target_names)
            )
        )
        candidates.append({
            "rows": rows,
            "controls": coefficients,
            "remainder": remainder,
            "degree": _degree(remainder, y),
            "score": (
                _degree(remainder, y),
                sum(len(str(value)) for value in coefficients),
            ),
        })
    assert candidates
    best = min(candidates, key=lambda item: item["score"])
    remainder = best["remainder"]
    assert isinstance(remainder, sp.Expr)
    remainder_normal = sp.factor(-sp.diff(remainder, y) / 5)

    return {
        "schema": "axiompack.jacobian_second_transverse_quotient.v1",
        "leading_exceptional_coordinates": {
            "A": str(leading_a),
            "D": str(leading_d),
            "identity": "A*D'-2*A'*D=1/2",
        },
        "complete_weight_five_target_image": {
            name: {
                "tangential": str(target_layers[name][0]),
                "normal": str(target_layers[name][1]),
                "degrees": [
                    _degree(target_layers[name][0], y),
                    _degree(target_layers[name][1], y),
                ],
                "predicted": "-10*H(A,D)",
            }
            for name in target_names
        },
        "linear_algebra": {
            "degree": degree,
            "rank": rank,
            "augmented_rank": augmented_rank,
            "seed_odd_minor_rows_1_3_5": str(seed_minor),
            "linearized_rank_four_witness": linearized_witness,
        },
        "normalized_layer_two": {
            "tangential": str(layer2[0]),
            "normal": str(layer2[1]),
            "degrees": [_degree(layer2[0], y), _degree(layer2[1], y)],
        },
        "canonical_opposite_parity_class": {
            "coordinate": str(leading_a),
            "tangential_residue": str(canonical_even_residue),
            "odd_target_part": str(canonical_odd_part),
            "degree_in_A": _degree(
                canonical_even_residue, a_coordinate
            ),
            "linearized_at_seed": str(linearized_even_residue),
        },
        "best_regular_fixed_slice_reduction": {
            "pivot_rows": list(best["rows"]),
            "controls": {
                name: str(value)
                for name, value in zip(target_names, best["controls"])
            },
            "tangential_remainder": str(remainder),
            "normal_remainder": str(remainder_normal),
            "degree": best["degree"],
        },
        "verdict": (
            "layer two is target-removable"
            if augmented_rank == rank
            else "a nonzero even-parity layer-two quotient class survives"
        ),
        "claim_boundary": (
            "this computes the instantaneous layer-two normal form; "
            "the coupled source-target Magnus invariant still requires "
            "secondary-bracket accounting"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
