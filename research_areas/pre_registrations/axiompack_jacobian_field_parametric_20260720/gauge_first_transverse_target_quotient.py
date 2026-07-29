#!/usr/bin/env python3
"""Exact first transverse target quotient for the normalized contact path."""
from __future__ import annotations

import hashlib
import itertools
import json
import sys
from pathlib import Path

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_regular_singular_connection import (  # noqa: E402
    _inverse_action,
    source_only_connection,
)
from gauge_target_divisor_image import (  # noqa: E402
    _source_lift,
    _spatially_polynomial,
    _target_lift,
    _weighted_divergence,
)


Pair = tuple[sp.Expr, sp.Expr]


def _pullback(
    hamiltonian: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
    family: Pair,
    jacobian: sp.Matrix,
    determinant: sp.Expr,
) -> Pair:
    target = (
        sp.diff(hamiltonian, q).subs({p: family[0], q: family[1]}),
        -sp.diff(hamiltonian, p).subs({p: family[0], q: family[1]}),
    )
    return _inverse_action(jacobian, determinant, target)


def _hamiltonian_pullback_layers(
    hamiltonian: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
    family_components: Pair,
    y: sp.Symbol,
    g: sp.Symbol,
    maximum_layer: int,
) -> list[Pair]:
    """Return exact exceptional layers without expanding an inverse matrix.

    In the exceptional chart the pulled-back area form is
    ``g^2/2 * dy∧dg``.  Hence the source pullback of ``X_H`` is the
    weighted Hamiltonian field of ``-2 * H(F)``:

        f = -2/g^2 * ∂g(H(F)),
        n =  2/g^2 * ∂y(H(F)).

    Layer ``m`` depends only on ``[g^(m+3)] H(F)``.  Extracting that scalar
    coefficient before constructing the field avoids expanding irrelevant
    higher normal layers and avoids asking SymPy to rediscover the
    determinant cancellation separately for every Hamiltonian.
    """

    pulled_hamiltonian = hamiltonian.subs(
        {p: family_components[0], q: family_components[1]},
        simultaneous=True,
    )
    result: list[Pair] = []
    for layer in range(maximum_layer + 1):
        order = layer + 3
        coefficient = sp.factor(
            sp.diff(pulled_hamiltonian, g, order).subs(g, 0)
            / sp.factorial(order)
        )
        tangential = sp.factor(-2 * order * coefficient)
        normal = sp.factor(2 * sp.diff(coefficient, y))
        assert sp.factor(
            normal + sp.diff(tangential, y) / order
        ) == 0
        result.append((tangential, normal))
    return result


def _first_jet(
    field: Pair,
    v: sp.Symbol,
    t: sp.Symbol,
    y: sp.Symbol,
    g: sp.Symbol,
) -> tuple[sp.Expr, Pair]:
    substitution = {
        v: (y - 3) / 2,
        t: g - 1 + 3 * (y - 3) / 4,
    }
    dy = sp.cancel((2 * field[0]).subs(substitution))
    dg = sp.cancel(
        (field[1] - sp.Rational(3, 2) * field[0]).subs(substitution)
    )
    divisor = sp.factor(dy.subs(g, 0))
    assert sp.factor(dg.subs(g, 0)) == 0
    divisor_normal = sp.factor(sp.diff(dg, g).subs(g, 0))
    assert sp.factor(divisor_normal + sp.diff(divisor, y) / 3) == 0
    tangential = sp.factor(sp.diff(dy, g).subs(g, 0))
    normal = sp.factor(sp.diff(dg, g, 2).subs(g, 0) / 2)
    assert sp.factor(normal + sp.diff(tangential, y) / 4) == 0
    return divisor, (tangential, normal)


def _degree(expr: sp.Expr, y: sp.Symbol) -> int:
    value = sp.cancel(expr)
    if value == 0:
        return -1
    assert y not in sp.denom(value).free_symbols
    return int(sp.Poly(sp.numer(value), y).degree())


def _coordinates(pair: Pair, y: sp.Symbol, degree: int) -> sp.Matrix:
    rows: list[sp.Expr] = []
    for item in pair:
        polynomial = sp.Poly(sp.cancel(item), y)
        rows.extend(polynomial.coeff_monomial(y**index) for index in range(degree + 1))
    return sp.Matrix(rows)


def _pair_from_coordinates(
    vector: sp.Matrix,
    y: sp.Symbol,
    degree: int,
) -> Pair:
    width = degree + 1
    return tuple(
        sp.factor(
            sum(vector[offset + index] * y**index for index in range(width))
        )
        for offset in (0, width)
    )  # type: ignore[return-value]


def _regular_zero_at_seed(value: sp.Expr, s: sp.Symbol) -> bool:
    reduced = sp.cancel(value)
    denominator = sp.denom(reduced)
    return denominator.subs(s, 0) != 0 and reduced.subs(s, 0) == 0


def _sha(pair: Pair) -> str:
    payload = "\n".join(str(sp.expand(item)) for item in pair)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run() -> dict[str, object]:
    data = source_only_connection()
    s, v, t, _ = data["symbols"]
    gamma = data["gamma"]
    family = data["family"]
    jacobian = data["jacobian"]
    determinant = data["determinant"]
    source_only = data["source_only"]
    p, q, y, g = sp.symbols("P Q y g")

    pullbacks = {
        "P3": _pullback(p**3, p, q, family, jacobian, determinant),
        "PQ": _pullback(p * q, p, q, family, jacobian, determinant),
        "Q2": _pullback(q**2, p, q, family, jacobian, determinant),
        "P4": _pullback(p**4, p, q, family, jacobian, determinant),
        "P2Q": _pullback(p**2 * q, p, q, family, jacobian, determinant),
    }
    coefficient_p3 = sp.factor(
        96
        * (s**2 - 12 * s + 16)
        / ((s - 6) ** 3 * (s - 4) ** 2 * (s + 4) ** 2)
    )
    coefficient_pq = sp.factor(2 * s / ((s - 4) * (s + 4)))
    normalized = tuple(
        sp.cancel(
            source_only[index]
            - coefficient_p3 * pullbacks["P3"][index]
            - coefficient_pq * pullbacks["PQ"][index]
            + sp.Rational(1, 4) * pullbacks["Q2"][index]
        )
        for index in range(2)
    )

    target_hamiltonians = {
        "P4": p**4,
        "P2Q": p**2 * q,
        "Q2": q**2,
    }
    for name, hamiltonian in target_hamiltonians.items():
        target = (sp.diff(hamiltonian, q), -sp.diff(hamiltonian, p))
        field = pullbacks[name]
        assert _target_lift(target, p, q)
        assert _spatially_polynomial(field, (v, t))
        assert _source_lift(field, v, t)
        assert _weighted_divergence(field, gamma, v, t) == 0

    normalized_divisor, normalized_jet = _first_jet(
        normalized, v, t, y, g
    )
    expected_translation = sp.factor(
        160 * s / (3 * (s - 4) ** 2 * (s + 4) ** 2)
    )
    assert sp.factor(normalized_divisor - expected_translation) == 0
    target_jets: dict[str, Pair] = {}
    for name in target_hamiltonians:
        divisor, jet = _first_jet(pullbacks[name], v, t, y, g)
        assert divisor == 0
        target_jets[name] = jet

    degree = max(
        _degree(item, y)
        for pair in [normalized_jet, *target_jets.values()]
        for item in pair
    )
    target_names = list(target_hamiltonians)
    target_matrix = sp.Matrix.hstack(
        *(_coordinates(target_jets[name], y, degree) for name in target_names)
    )
    normalized_vector = _coordinates(normalized_jet, y, degree)
    target_rank = int(target_matrix.rank())
    augmented_rank = int(target_matrix.row_join(normalized_vector).rank())
    assert target_rank == len(target_names)
    seed_unit_minor = sp.factor(
        target_matrix.extract([0, 2, 4], range(target_rank)).det().subs(s, 0)
    )
    assert seed_unit_minor == -8

    # Search every nonsingular coefficient window.  Each window specifies a
    # canonical target correction; score its remainder by polynomial degree.
    candidates: list[dict[str, object]] = []
    for rows in itertools.combinations(range(target_matrix.rows), target_rank):
        square = target_matrix.extract(rows, range(target_rank))
        if sp.factor(square.det()) == 0:
            continue
        controls = tuple(
            sp.factor(value)
            for value in square.inv() * normalized_vector.extract(rows, [0])
        )
        if not all(_regular_zero_at_seed(value, s) for value in controls):
            continue
        remainder_vector = sp.simplify(
            normalized_vector - target_matrix * sp.Matrix(controls)
        )
        remainder = _pair_from_coordinates(remainder_vector, y, degree)
        degrees = tuple(_degree(item, y) for item in remainder)
        candidates.append({
            "rows": rows,
            "controls": controls,
            "remainder": remainder,
            "degrees": degrees,
            "score": (
                max(degrees),
                sum(max(item, 0) for item in degrees),
                sum(len(str(item)) for item in controls),
            ),
        })
    assert candidates
    best = min(candidates, key=lambda item: item["score"])
    controls = best["controls"]
    remainder = best["remainder"]
    assert isinstance(controls, tuple)
    assert isinstance(remainder, tuple)
    expected_remainder = (
        sp.factor(-16 * s * y / (s + 4) ** 3),
        sp.factor(4 * s / (s + 4) ** 3),
    )
    assert all(
        sp.factor(remainder[index] - expected_remainder[index]) == 0
        for index in range(2)
    )

    left_kernel = target_matrix.T.nullspace()
    quotient_values = [
        sp.factor(functional.dot(normalized_vector))
        for functional in left_kernel
    ]
    nonzero_quotient_values = [
        value for value in quotient_values if value != 0
    ]

    return {
        "schema": "axiompack.jacobian_first_transverse_quotient.v1",
        "coordinate": {
            "divisor": "g=gamma=0",
            "tangent": "y=2*v+3",
            "jet": (
                "D=(f0+g*f1+O(g^2))*d/dy"
                "+(g*n1+g^2*n2+O(g^3))*d/dg; "
                "n1=-f0'/3, n2=-f1'/4"
            ),
        },
        "normalized_divisor_connection": str(normalized_divisor),
        "normalized_jet": {
            "pair": [str(item) for item in normalized_jet],
            "degrees": [_degree(item, y) for item in normalized_jet],
            "sha256": _sha(normalized_jet),
        },
        "complete_weight_four_target_image": {
            name: {
                "pair": [str(item) for item in target_jets[name]],
                "degrees": [_degree(item, y) for item in target_jets[name]],
                "sha256": _sha(target_jets[name]),
            }
            for name in target_names
        },
        "linear_algebra": {
            "coefficient_window_degree": degree,
            "target_rank": target_rank,
            "augmented_rank": augmented_rank,
            "ambient_dimension": target_matrix.rows,
            "cokernel_dimension": len(left_kernel),
            "seed_unit_minor_rows_0_2_4": str(seed_unit_minor),
            "nonzero_normalized_quotient_coordinates": len(
                nonzero_quotient_values
            ),
        },
        "best_regular_fixed_slice_reduction": {
            "pivot_rows": list(best["rows"]),
            "controls": {
                name: str(value)
                for name, value in zip(target_names, controls)
            },
            "controls_vanish_at_s_zero": all(
                _regular_zero_at_seed(value, s) for value in controls
            ),
            "remainder": [str(item) for item in remainder],
            "degrees": list(best["degrees"]),
            "sha256": _sha(remainder),
        },
        "truncated_lie_closure": {
            "first_neighborhood_basis": [
                "T=d/dy",
                "Y=g*y*d/dy mod g^2",
                "C=g*d/dy mod g^2",
            ],
            "brackets": [
                "[T,Y]=C",
                "[T,C]=0",
                "[Y,C]=0 mod g^2",
            ],
            "full_graded_correction": (
                "[D_y^(1),D_1^(1)]=-(5/4)*D_1^(2)"
            ),
        },
        "verdict": (
            "first transverse jet is completely target-removable"
            if augmented_rank == target_rank
            else "a nonzero first transverse target-quotient class survives"
        ),
        "claim_boundary": (
            "this is the complete gamma-adic layer-one target quotient; "
            "finite quotient data alone does not decide all-order global "
            "gauge-minimized logarithmic complexity"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
