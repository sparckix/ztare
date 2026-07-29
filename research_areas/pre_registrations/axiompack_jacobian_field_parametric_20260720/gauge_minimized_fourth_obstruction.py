#!/usr/bin/env python3
"""Reduce degree-five fourth-order compatibility to its exact obstruction."""
from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path

import sympy as sp
from sympy.polys.matrices import DomainMatrix


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_minimized_fourth_jet import (  # noqa: E402
    _family_jets,
    _pair_system,
    _source_act_pair,
)
from gauge_minimized_third_jet import (  # noqa: E402
    _add,
    _compose,
    _hamiltonian_field,
    _monomials,
    _scale,
    _substitute,
    run as run_third,
)


Pair = tuple[sp.Expr, sp.Expr]


def _primitive_dual_support(
    dual: sp.Matrix,
    row_keys: list[tuple[int, int, int]],
) -> dict[str, object]:
    denominators = [
        int(sp.denom(value)) for value in dual if value != 0
    ]
    common_denominator = (
        sp.ilcm(*denominators) if denominators else 1
    )
    integers = [
        int(sp.Rational(value) * common_denominator)
        for value in dual
    ]
    nonzero = [abs(value) for value in integers if value]
    common_factor = int(sp.gcd_list(nonzero)) if nonzero else 1
    integers = [value // common_factor for value in integers]
    first = next((value for value in integers if value), 1)
    if first < 0:
        integers = [-value for value in integers]
    support = [
        {
            "component": row_keys[index][0],
            "v_degree": row_keys[index][1],
            "t_degree": row_keys[index][2],
            "coefficient": coefficient,
        }
        for index, coefficient in enumerate(integers)
        if coefficient
    ]
    return {
        "support_size": len(support),
        "support": support,
        "sha256": hashlib.sha256(
            json.dumps(support, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }


def _normal_scalar_basis(
    degree_bound: int,
    p: sp.Symbol,
    q: sp.Symbol,
    c: sp.Expr,
) -> list[sp.Expr]:
    basis: list[sp.Expr] = []
    for c_power in range(degree_bound // 6 + 1):
        for p_power in range(degree_bound // 4 + 1):
            if 4 * p_power + 6 * c_power <= degree_bound:
                basis.append(p**p_power * c**c_power)
            if 6 + 4 * p_power + 6 * c_power <= degree_bound:
                basis.append(q * p**p_power * c**c_power)
    return basis


def _hamiltonian_field_window(
    first_component_degree: int,
    second_component_degree: int,
    p: sp.Symbol,
    q: sp.Symbol,
) -> tuple[list[Pair], list[sp.Expr], list[sp.Expr]]:
    c = 4 * p**3 - p**2 - 18 * p * q + 27 * q**2 + 4 * q
    first_basis = _normal_scalar_basis(
        first_component_degree, p, q, c
    )
    second_basis = _normal_scalar_basis(
        second_component_degree, p, q, c
    )
    divergence_columns = [
        sp.Poly(sp.diff(item, p), p, q, domain=sp.QQ)
        for item in first_basis
    ] + [
        sp.Poly(sp.diff(item, q), p, q, domain=sp.QQ)
        for item in second_basis
    ]
    row_monomials = sorted({
        monomial
        for polynomial in divergence_columns
        for monomial in polynomial.monoms()
    })
    matrix = sp.Matrix([
        [
            polynomial.coeff_monomial(p**i * q**j)
            for polynomial in divergence_columns
        ]
        for i, j in row_monomials
    ])
    fields: list[Pair] = []
    for vector in matrix.nullspace():
        first = sp.expand(sum(
            vector[index] * item
            for index, item in enumerate(first_basis)
        ))
        second = sp.expand(sum(
            vector[len(first_basis) + index] * item
            for index, item in enumerate(second_basis)
        ))
        assert sp.expand(sp.diff(first, p) + sp.diff(second, q)) == 0
        fields.append((first, second))
    return fields, first_basis, second_basis


def _parse_pair(
    values: list[str], locals_: dict[str, sp.Symbol]
) -> Pair:
    return tuple(
        sp.sympify(value, locals=locals_) for value in values
    )  # type: ignore[return-value]


def _residual_coefficients(
    residual: Pair, a: sp.Symbol, b: sp.Symbol
) -> list[Pair]:
    substitutions = {a: 0, b: 0}
    return [
        tuple(sp.expand(item.subs(substitutions)) for item in residual),
        tuple(
            sp.expand(sp.diff(item, a).subs(substitutions))
            for item in residual
        ),
        tuple(
            sp.expand(sp.diff(item, b).subs(substitutions))
            for item in residual
        ),
        tuple(
            sp.expand(sp.diff(item, a, 2).subs(substitutions) / 2)
            for item in residual
        ),
        tuple(
            sp.expand(sp.diff(item, a, b).subs(substitutions))
            for item in residual
        ),
        tuple(
            sp.expand(sp.diff(item, b, 2).subs(substitutions) / 2)
            for item in residual
        ),
    ]  # type: ignore[return-value]


def _quotient_duals(
    matrix: DomainMatrix,
    residual_columns: DomainMatrix,
) -> tuple[list[sp.Matrix], int, int, list[int]]:
    rank = matrix.rank()
    independent_matrix_columns = list(matrix.rref()[1])
    assert len(independent_matrix_columns) == rank
    basis = matrix.extract(
        list(range(matrix.shape[0])), independent_matrix_columns
    )
    combined = DomainMatrix.hstack(basis, residual_columns)
    combined_pivots = list(combined.rref()[1])
    assert combined_pivots[:rank] == list(range(rank))
    chosen_residuals = [
        pivot - rank
        for pivot in combined_pivots[rank:]
    ]
    if not chosen_residuals:
        return [], rank, rank, []
    basis = combined.extract(
        list(range(combined.shape[0])),
        [
            *range(rank),
            *(rank + index for index in chosen_residuals),
        ],
    )
    augmented_rank = len(combined_pivots)
    assert augmented_rank == rank + len(chosen_residuals)
    _rref, independent_rows = basis.transpose().rref()
    selected_rows = list(independent_rows)
    assert len(selected_rows) == augmented_rank
    square = basis.extract(
        selected_rows, list(range(augmented_rank))
    ).to_Matrix()
    inverse_transpose = square.transpose().inv()
    duals: list[sp.Matrix] = []
    for offset in range(len(chosen_residuals)):
        dual_selected = inverse_transpose * sp.eye(
            augmented_rank
        )[:, rank + offset]
        dual = sp.zeros(matrix.shape[0], 1)
        for row, value in zip(
            selected_rows, dual_selected, strict=True
        ):
            dual[row] = sp.Rational(value)
        assert matrix.to_Matrix().transpose() * dual == sp.zeros(
            matrix.shape[1], 1
        )
        duals.append(dual)
    return duals, rank, augmented_rank, chosen_residuals


def run(
    maximum_fourth_hamiltonian_degree: int = 4,
    *,
    all_degree_target_window: bool = True,
    source_degree_bound: int = 5,
) -> dict[str, object]:
    prefix = run_third(
        maximum_source_degree=5,
        maximum_third_hamiltonian_degree=1,
        all_degree_target_window=True,
    )
    assert prefix["solution_affine_dimension"] == 2
    witness = prefix["witness"]
    directions = prefix["homogeneous_directions"]

    data = _family_jets(4)
    v, t = data["symbols"]
    p, q = sp.symbols("P Q")
    a, b = sp.symbols("a b")
    p0, q0 = data["P"][0], data["Q"][0]
    f4: Pair = data["P"][4], data["Q"][4]
    target_locals = {"P": p, "Q": q}
    source_locals = {"v": v, "t": t}

    k2 = sp.sympify(witness["K2"], locals=target_locals)
    k3 = sp.sympify(witness["K3"], locals=target_locals)
    y2 = _parse_pair(witness["Y2"], source_locals)
    y3 = _parse_pair(witness["Y3"], source_locals)
    parameters = [a, b]
    for parameter, direction in zip(parameters, directions, strict=True):
        k2 += parameter * sp.sympify(
            direction["K2"], locals=target_locals
        )
        k3 += parameter * sp.sympify(
            direction["K3"], locals=target_locals
        )
        direction_y2 = _parse_pair(direction["Y2"], source_locals)
        direction_y3 = _parse_pair(direction["Y3"], source_locals)
        y2 = _add(y2, _scale(direction_y2, parameter))
        y3 = _add(y3, _scale(direction_y3, parameter))

    x1: Pair = (-q / 2, p**2 / 12)
    x2 = _hamiltonian_field(k2, p, q)
    x3 = _hamiltonian_field(k3, p, q)
    x1_squared = _compose(x1, x1, p, q)
    x1_cubed = _compose(x1, x1_squared, p, q)
    x1_fourth = _compose(x1, x1_cubed, p, q)
    target_second = _add(x1_squared, x2)
    target_fourth_without_x4 = _add(
        x1_fourth,
        _scale(
            _add(
                _compose(x1, _compose(x1, x2, p, q), p, q),
                _compose(x1, _compose(x2, x1, p, q), p, q),
                _compose(x2, x1_squared, p, q),
            ),
            2,
        ),
        _scale(_compose(x2, x2, p, q), 3),
        _scale(
            _add(
                _compose(x1, x3, p, q),
                _compose(x3, x1, p, q),
            ),
            2,
        ),
    )
    target_fourth_at = _substitute(
        target_fourth_without_x4, p, q, p0, q0
    )
    target_second_at = _substitute(
        target_second, p, q, p0, q0
    )
    x1_at = _substitute(x1, p, q, p0, q0)
    source_cross = _add(
        _scale(_source_act_pair(y2, target_second_at, v, t), 6),
        _scale(_source_act_pair(y3, x1_at, v, t), 4),
        _scale(
            _source_act_pair(
                y2,
                _source_act_pair(y2, (p0, q0), v, t),
                v,
                t,
            ),
            3,
        ),
    )
    residual = _add(
        f4,
        _scale(target_fourth_at, -1),
        _scale(source_cross, -1),
    )
    residual_coefficients = _residual_coefficients(residual, a, b)
    assert all(
        sp.Poly(item, a, b).total_degree() <= 2 for item in residual
    )
    residual_component_degrees = [
        int(sp.Poly(item, v, t).total_degree()) for item in residual
    ]
    residual_basis_component_degrees = [
        [
            -1 if item == 0 else int(sp.Poly(item, v, t).total_degree())
            for item in pair
        ]
        for pair in residual_coefficients
    ]

    jacobian = sp.Matrix([
        [sp.diff(p0, v), sp.diff(p0, t)],
        [sp.diff(q0, v), sp.diff(q0, t)],
    ])
    columns: list[Pair] = []
    for component in range(2):
        forbidden = (
            {(0, 0)} if component == 0 else {(0, 0), (1, 0)}
        )
        for i, j in _monomials(source_degree_bound):
            if (i, j) in forbidden:
                continue
            monomial = v**i * t**j
            columns.append((
                sp.expand(jacobian[0, component] * monomial),
                sp.expand(jacobian[1, component] * monomial),
            ))
    first_target_degree = max(
        source_degree_bound + 3, residual_component_degrees[0]
    )
    second_target_degree = max(
        source_degree_bound + 5, residual_component_degrees[1]
    )
    target_fields: list[Pair]
    first_scalar_basis: list[sp.Expr] = []
    second_scalar_basis: list[sp.Expr] = []
    if all_degree_target_window:
        target_fields, first_scalar_basis, second_scalar_basis = (
            _hamiltonian_field_window(
                first_target_degree,
                second_target_degree,
                p,
                q,
            )
        )
    else:
        target_fields = []
        for total in range(1, maximum_fourth_hamiltonian_degree + 1):
            for i in range(total + 1):
                hamiltonian = p**i * q ** (total - i)
                target_fields.append(
                    _hamiltonian_field(hamiltonian, p, q)
                )
    for field in target_fields:
        columns.append(_substitute(field, p, q, p0, q0))

    all_columns = columns + residual_coefficients
    full_matrix, _zero, row_keys = _pair_system(
        all_columns, (sp.Integer(0), sp.Integer(0)), v, t
    )
    image_count = len(columns)
    image = full_matrix.extract(
        list(range(full_matrix.shape[0])), list(range(image_count))
    )
    residual_matrix = full_matrix.extract(
        list(range(full_matrix.shape[0])),
        list(range(image_count, full_matrix.shape[1])),
    )
    duals, image_rank, quotient_rank, chosen_residuals = (
        _quotient_duals(image, residual_matrix)
    )
    all_residual_rank = DomainMatrix.hstack(
        image, residual_matrix
    ).rank()
    pairings = [
        [
            sp.cancel(
                (
                    residual_matrix.to_Matrix()[:, index].transpose()
                    * dual
                )[0]
            )
            for index in range(residual_matrix.shape[1])
        ]
        for dual in duals
    ]
    obstructions = [
        sp.factor(
            row[0]
            + row[1] * a
            + row[2] * b
            + row[3] * a**2
            + row[4] * a * b
            + row[5] * b**2
        )
        for row in pairings
    ]
    solutions = sp.solve(obstructions, (a, b), dict=True)
    return {
        "schema": "axiompack.jacobian_degree_five_fourth_obstruction.v1",
        "lower_prefix_affine_dimension": 2,
        "source_degree_bound": source_degree_bound,
        "maximum_fourth_hamiltonian_degree_tested": (
            maximum_fourth_hamiltonian_degree
        ),
        "target_basis_mode": (
            "all_degree_C_normal_form"
            if all_degree_target_window
            else "raw_hamiltonian_degree_cutoff"
        ),
        "target_component_degree_window": [
            first_target_degree,
            second_target_degree,
        ],
        "first_scalar_normal_basis": [
            str(item) for item in first_scalar_basis
        ],
        "second_scalar_normal_basis": [
            str(item) for item in second_scalar_basis
        ],
        "hamiltonian_field_window_dimension": len(target_fields),
        "fourth_image_column_count": image.shape[1],
        "fourth_image_rank": image_rank,
        "image_plus_residual_span_rank": all_residual_rank,
        "quotient_rank": quotient_rank - image_rank,
        "chosen_residual_coefficients": chosen_residuals,
        "residual_basis": ["1", "a", "b", "a^2", "a*b", "b^2"],
        "residual_component_degrees": residual_component_degrees,
        "residual_basis_component_degrees": (
            residual_basis_component_degrees
        ),
        "dual_pairings": [
            [str(item) for item in row] for row in pairings
        ],
        "dual_certificates": [
            _primitive_dual_support(dual, row_keys) for dual in duals
        ],
        "compatibility_obstructions": [
            str(item) for item in obstructions
        ],
        "obstruction_factorizations": [
            str(sp.factor(item)) for item in obstructions
        ],
        "solutions": [
            {str(key): str(value) for key, value in solution.items()}
            for solution in solutions
        ],
        "row_count": image.shape[0],
        "row_key_count": len(row_keys),
        "claim_boundary": (
            "the degree-five order-four obstruction for the complete "
            "two-parameter order-three solution family, against source "
            "degree five and the all-degree C-normal-form Hamiltonian window"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
