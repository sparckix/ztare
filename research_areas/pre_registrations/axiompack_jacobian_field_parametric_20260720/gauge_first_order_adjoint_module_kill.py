#!/usr/bin/env python3
"""Exact kill for the proposed first-order Jordan-module identification.

The canonical transverse recurrence has a three-state coefficient-shift
realization with eigenvalue 3/2.  This replay checks whether the tempting
three-dimensional cap-seven homogeneous contact fiber is preserved by an
adjoint action.  It is not.

The calculation is finite and diagnostic.  It does not exclude every
finite-dimensional nonlinear formal contact orbit.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_minimized_fifth_obstruction import (  # noqa: E402
    _source_target_image,
)
from gauge_minimized_fourth_jet import (  # noqa: E402
    _family_jets,
    _pair_system,
)
from gauge_minimized_third_jet import (  # noqa: E402
    _hamiltonian_field,
)


Pair = tuple[sp.Expr, sp.Expr]


def _degree(value: sp.Expr, v: sp.Symbol, t: sp.Symbol) -> int:
    if value == 0:
        return -1
    return int(sp.Poly(value, v, t, domain=sp.QQ).total_degree())


def _bracket(
    left: sp.Expr,
    right: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> sp.Expr:
    """Hamiltonian bracket satisfying [X_H,X_K]=X_[H,K]."""

    return sp.expand(
        sp.diff(left, q) * sp.diff(right, p)
        - sp.diff(left, p) * sp.diff(right, q)
    )


def _source_lift(
    hamiltonian: sp.Expr,
    *,
    p0: sp.Expr,
    q0: sp.Expr,
    jacobian: sp.Matrix,
    p: sp.Symbol,
    q: sp.Symbol,
    v: sp.Symbol,
    t: sp.Symbol,
) -> Pair:
    target = _hamiltonian_field(hamiltonian, p, q)
    pullback = sp.Matrix([
        sp.expand(target[0].subs({p: p0, q: q0})),
        sp.expand(target[1].subs({p: p0, q: q0})),
    ])
    source = tuple(
        sp.factor(sp.cancel(value))
        for value in (-jacobian.inv() * pullback)
    )
    assert all(sp.denom(value).free_symbols == set() for value in source)
    replay = jacobian * sp.Matrix(source) + pullback
    assert all(
        sp.expand(sp.cancel(value)) == 0 for value in replay
    )
    return source  # type: ignore[return-value]


def _coefficient_matrix(
    polynomials: list[sp.Expr],
    p: sp.Symbol,
    q: sp.Symbol,
) -> sp.Matrix:
    expanded = [
        sp.Poly(value, p, q, domain=sp.QQ)
        for value in polynomials
    ]
    monomials = sorted({
        monomial
        for polynomial in expanded
        for monomial in polynomial.monoms()
    })
    return sp.Matrix([
        [
            polynomial.coeff_monomial(monomial)
            for polynomial in expanded
        ]
        for monomial in monomials
    ])


def _quotient_constraints(
    basis: list[sp.Expr],
    candidates: list[sp.Expr],
    p: sp.Symbol,
    q: sp.Symbol,
) -> sp.Matrix:
    matrix = _coefficient_matrix(basis + candidates, p, q)
    basis_matrix = matrix[:, : len(basis)]
    candidate_matrix = matrix[:, len(basis) :]
    left_nullspace = basis_matrix.transpose().nullspace()
    if not left_nullspace:
        return sp.zeros(0, len(candidates))
    return sp.Matrix.vstack(*[
        vector.transpose() * candidate_matrix
        for vector in left_nullspace
    ])


def _kernel_nullity(
    bound: int,
    *,
    data: dict[str, object],
    jacobian: sp.Matrix,
    p: sp.Symbol,
    q: sp.Symbol,
    v: sp.Symbol,
    t: sp.Symbol,
) -> tuple[int, int, list[int]]:
    p0, q0 = data["P"][0], data["Q"][0]
    residual = data["P"][1], data["Q"][1]
    residual_degrees = [_degree(value, v, t) for value in residual]
    columns, _metadata, target_window = _source_target_image(
        source_order=1,
        source_degree_bound=bound,
        first_target_degree=max(bound + 3, residual_degrees[0]),
        second_target_degree=max(bound + 5, residual_degrees[1]),
        v=v,
        t=t,
        p=p,
        q=q,
        p0=p0,
        q0=q0,
        jacobian=jacobian,
    )
    matrix, _rhs, _row_keys = _pair_system(
        columns,
        (sp.Integer(0), sp.Integer(0)),
        v,
        t,
    )
    rank = matrix.rank()
    return rank, matrix.shape[1] - rank, target_window


def run() -> dict[str, object]:
    p, q = sp.symbols("P Q")
    data = _family_jets(1)
    v, t = data["symbols"]
    p0, q0 = data["P"][0], data["Q"][0]
    jacobian = sp.Matrix([p0, q0]).jacobian([v, t])

    cap_rows = []
    expected_nullities = [0, 1, 1, 3, 3, 6, 6, 8, 8, 11, 11, 15]
    for bound, expected in zip(
        range(4, 16), expected_nullities, strict=True
    ):
        rank, nullity, target_window = _kernel_nullity(
            bound,
            data=data,
            jacobian=jacobian,
            p=p,
            q=q,
            v=v,
            t=t,
        )
        assert nullity == expected
        cap_rows.append({
            "source_cap": bound,
            "rank": rank,
            "nullity": nullity,
            "target_window": target_window,
        })

    h0 = -p * q
    h1 = -(4 * p**3 + 27 * q**2) / 12
    h2 = -(
        24 * p**4
        - 2 * p**3
        - 108 * p**2 * q
        + 162 * p * q**2
        + 24 * p * q
        + 27 * q**2
    ) / 6
    basis = [sp.expand(h0), sp.expand(h1), sp.expand(h2)]
    assert _coefficient_matrix(basis, p, q).rank() == 3

    basis_lifts = [
        _source_lift(
            hamiltonian,
            p0=p0,
            q0=q0,
            jacobian=jacobian,
            p=p,
            q=q,
            v=v,
            t=t,
        )
        for hamiltonian in basis
    ]
    basis_lift_degrees = [
        max(_degree(component, v, t) for component in source)
        for source in basis_lifts
    ]
    assert all(degree <= 7 for degree in basis_lift_degrees)

    brackets = {
        "H0_H1": _bracket(h0, h1, p, q),
        "H0_H2": _bracket(h0, h2, p, q),
        "H1_H2": _bracket(h1, h2, p, q),
    }
    bracket_lift_degrees = {}
    for label, hamiltonian in brackets.items():
        assert _coefficient_matrix(
            basis + [hamiltonian], p, q
        ).rank() == 4
        source = _source_lift(
            hamiltonian,
            p0=p0,
            q0=q0,
            jacobian=jacobian,
            p=p,
            q=q,
            v=v,
            t=t,
        )
        bracket_lift_degrees[label] = max(
            _degree(component, v, t) for component in source
        )
    assert list(bracket_lift_degrees.values()) == [9, 13, 13]

    adjoint_constraints = []
    for right in basis:
        candidates = [
            _bracket(left, right, p, q) for left in basis
        ]
        adjoint_constraints.append(
            _quotient_constraints(basis, candidates, p, q)
        )
    adjoint_matrix = sp.Matrix.vstack(*adjoint_constraints)
    assert adjoint_matrix.rank() == 3

    particular = -q**2 / 4 - p**3 / 36
    affine_matrices = []
    affine_rhs = []
    for right in basis:
        constraints = _quotient_constraints(
            basis,
            [
                *[_bracket(left, right, p, q) for left in basis],
                _bracket(particular, right, p, q),
            ],
            p,
            q,
        )
        affine_matrices.append(constraints[:, :3])
        affine_rhs.append(-constraints[:, 3])
    affine_matrix = sp.Matrix.vstack(*affine_matrices)
    affine_target = sp.Matrix.vstack(*affine_rhs)
    assert affine_matrix.rank() < affine_matrix.row_join(
        affine_target
    ).rank()

    stabilizer = -(
        4 * p**3 - 18 * p * q + 27 * q**2
    ) / 12
    assert sp.expand(h1 - sp.Rational(3, 2) * h0 - stabilizer) == 0

    stabilizer_source = _source_lift(
        stabilizer,
        p0=p0,
        q0=q0,
        jacobian=jacobian,
        p=p,
        q=q,
        v=v,
        t=t,
    )
    stabilizer_pullback = sp.expand(stabilizer.subs({p: p0, q: q0}))
    isotropy_rows = []
    # Three exact rows are enough to guard the chain-rule implementation.
    # The all-order family follows symbolically from
    # X_(K^(m+1)/(m+1)) = K^m X_K.
    for power in range(3):
        hamiltonian = sp.expand(
            stabilizer ** (power + 1) / (power + 1)
        )
        expected_source = tuple(
            sp.expand(stabilizer_pullback**power * component)
            for component in stabilizer_source
        )
        actual_source = _source_lift(
            hamiltonian,
            p0=p0,
            q0=q0,
            jacobian=jacobian,
            p=p,
            q=q,
            v=v,
            t=t,
        )
        assert all(
            sp.expand(sp.cancel(actual - expected)) == 0
            for actual, expected in zip(
                actual_source, expected_source, strict=True
            )
        )
        isotropy_rows.append({
            "power": power,
            "hamiltonian_degree": int(
                sp.Poly(hamiltonian, p, q).total_degree()
            ),
            "source_degree": max(
                _degree(component, v, t)
                for component in actual_source
            ),
        })

    return {
        "schema": "axiompack.jacobian_first_order_adjoint_kill.v1",
        "cap_kernel_rows": cap_rows,
        "cap_seven_basis": [str(value) for value in basis],
        "cap_seven_basis_source_degrees": basis_lift_degrees,
        "pairwise_brackets": {
            label: {
                "hamiltonian": str(value),
                "source_lift_degree": bracket_lift_degrees[label],
                "outside_cap_seven_span": True,
            }
            for label, value in brackets.items()
        },
        "nonzero_adjoint_preserving_cap_seven": False,
        "affine_particular_preserving_cap_seven": False,
        "three_halves_identity": "K_star = H1 - (3/2)*H0",
        "isotropy_power_replay": isotropy_rows,
        "coefficient_shift_category": (
            "The size-three Jordan block acts on the canonical recurrence "
            "space spanned by (3/2)^m, m(3/2)^m, and m^2(3/2)^m. "
            "It is not an adjoint endomorphism of the cap-seven contact "
            "fiber."
        ),
        "claim_boundary": (
            "This excludes the proposed first-order-fiber/Jordan "
            "identification. It does not exclude every nonlinear "
            "finite-dimensional formal-flow mechanism."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
