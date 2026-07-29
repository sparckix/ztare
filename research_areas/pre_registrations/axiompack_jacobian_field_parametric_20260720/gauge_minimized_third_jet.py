#!/usr/bin/env python3
"""Exact compatible target/source minimization through parameter order three.

Target and source coordinate changes are represented by logarithms

    A_s = s X1 + s^2/2 X2 + s^3/6 X3
    B_s = s^2/2 Y2 + s^3/6 Y3.

The coefficient equations therefore retain the mixed X1/X2 and X1/Y2
composition terms.  All arithmetic is over QQ.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import sympy as sp
from sympy.polys.matrices import DomainMatrix


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from equivariant_full_gauge_third_jet import _family_jets  # noqa: E402


Pair = tuple[sp.Expr, sp.Expr]
JetColumn = tuple[sp.Expr, sp.Expr, sp.Expr, sp.Expr]


def _monomials(maximum_degree: int) -> list[tuple[int, int]]:
    return [
        (i, total - i)
        for total in range(maximum_degree + 1)
        for i in range(total + 1)
    ]


def _act(field: Pair, value: sp.Expr, p: sp.Symbol, q: sp.Symbol) -> sp.Expr:
    return sp.expand(
        field[0] * sp.diff(value, p) + field[1] * sp.diff(value, q)
    )


def _compose(left: Pair, right: Pair, p: sp.Symbol, q: sp.Symbol) -> Pair:
    """Return the pair left(right_i), i.e. composition of derivations."""

    return (
        _act(left, right[0], p, q),
        _act(left, right[1], p, q),
    )


def _scale(pair: Pair, scalar: sp.Rational | int) -> Pair:
    return sp.expand(scalar * pair[0]), sp.expand(scalar * pair[1])


def _add(*pairs: Pair) -> Pair:
    return (
        sp.expand(sum(pair[0] for pair in pairs)),
        sp.expand(sum(pair[1] for pair in pairs)),
    )


def _substitute(pair: Pair, p: sp.Symbol, q: sp.Symbol, p0: sp.Expr, q0: sp.Expr) -> Pair:
    return (
        sp.expand(pair[0].subs({p: p0, q: q0})),
        sp.expand(pair[1].subs({p: p0, q: q0})),
    )


def _hamiltonian_field(
    hamiltonian: sp.Expr, p: sp.Symbol, q: sp.Symbol
) -> Pair:
    return sp.diff(hamiltonian, q), -sp.diff(hamiltonian, p)


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


def _hamiltonian_primitive(
    field: Pair, p: sp.Symbol, q: sp.Symbol
) -> sp.Expr:
    primitive = sp.integrate(field[0], q)
    correction_derivative = sp.expand(
        -field[1] - sp.diff(primitive, p)
    )
    assert q not in correction_derivative.free_symbols
    primitive = sp.expand(
        primitive + sp.integrate(correction_derivative, p)
    )
    assert all(
        sp.expand(left - right) == 0
        for left, right in zip(
            _hamiltonian_field(primitive, p, q),
            field,
            strict=True,
        )
    )
    return primitive


def _hamiltonian_field_window(
    first_component_degree: int,
    second_component_degree: int,
    p: sp.Symbol,
    q: sp.Symbol,
) -> tuple[list[tuple[sp.Expr, Pair]], list[sp.Expr], list[sp.Expr]]:
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
    result: list[tuple[sp.Expr, Pair]] = []
    for vector in matrix.nullspace():
        field = (
            sp.expand(sum(
                vector[index] * item
                for index, item in enumerate(first_basis)
            )),
            sp.expand(sum(
                vector[len(first_basis) + index] * item
                for index, item in enumerate(second_basis)
            )),
        )
        result.append((_hamiltonian_primitive(field, p, q), field))
    return result, first_basis, second_basis


def _coefficient_system(
    columns: list[JetColumn],
    rhs: JetColumn,
    v: sp.Symbol,
    t: sp.Symbol,
) -> tuple[DomainMatrix, DomainMatrix, list[tuple[int, int, int]]]:
    polynomial_columns = [
        tuple(sp.Poly(item, v, t, domain=sp.QQ) for item in column)
        for column in columns
    ]
    rhs_polynomials = tuple(
        sp.Poly(item, v, t, domain=sp.QQ) for item in rhs
    )
    row_keys = sorted({
        (slot, i, j)
        for slot in range(4)
        for polynomial in (
            [column[slot] for column in polynomial_columns]
            + [rhs_polynomials[slot]]
        )
        for i, j in polynomial.monoms()
    })
    row_index = {key: index for index, key in enumerate(row_keys)}
    entries: dict[int, dict[int, sp.Rational]] = {}
    for column_index, column in enumerate(polynomial_columns):
        for slot, polynomial in enumerate(column):
            for (i, j), coefficient in polynomial.terms():
                if coefficient:
                    entries.setdefault(row_index[(slot, i, j)], {})[
                        column_index
                    ] = sp.Rational(coefficient)
    rhs_entries: dict[int, dict[int, sp.Rational]] = {}
    for slot, polynomial in enumerate(rhs_polynomials):
        for (i, j), coefficient in polynomial.terms():
            if coefficient:
                rhs_entries.setdefault(row_index[(slot, i, j)], {})[
                    0
                ] = sp.Rational(coefficient)
    matrix = DomainMatrix.from_dict_sympy(
        len(row_keys), len(columns), entries
    ).to_field()
    rhs_matrix = DomainMatrix.from_dict_sympy(
        len(row_keys), 1, rhs_entries
    ).to_field()
    return matrix, rhs_matrix, row_keys


def _matrix_sha(matrix: DomainMatrix) -> str:
    rows = matrix.to_Matrix().tolist()
    payload = json.dumps(
        [[str(item) for item in row] for row in rows],
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _particular_solution(
    matrix: DomainMatrix, rhs: DomainMatrix
) -> sp.Matrix:
    dense = matrix.to_Matrix()
    dense_rhs = rhs.to_Matrix()
    solution_set = sp.linsolve((dense, dense_rhs))
    if solution_set is sp.EmptySet:
        raise ValueError("inconsistent system")
    solution = next(iter(solution_set))
    free = sorted(
        set().union(*(item.free_symbols for item in solution)),
        key=str,
    )
    return sp.Matrix([
        sp.cancel(item.subs({parameter: 0 for parameter in free}))
        for item in solution
    ])


def _degree(value: sp.Expr, v: sp.Symbol, t: sp.Symbol) -> int:
    if value == 0:
        return -1
    return int(sp.Poly(value, v, t, domain=sp.QQ).total_degree())


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(str(sp.expand(value)).encode("utf-8")).hexdigest()


def run(
    *,
    maximum_source_degree: int = 8,
    maximum_third_hamiltonian_degree: int = 8,
    all_degree_target_window: bool = False,
) -> dict[str, object]:
    data = _family_jets()
    v, t = data["symbols"]
    p, q = sp.symbols("P Q")
    p0, p2, p3 = data["P"][0], data["P"][2], data["P"][3]
    q0, q2, q3 = data["Q"][0], data["Q"][2], data["Q"][3]
    jacobian = sp.Matrix([
        [sp.diff(p0, v), sp.diff(p0, t)],
        [sp.diff(q0, v), sp.diff(q0, t)],
    ])

    x1: Pair = (-q / 2, p**2 / 12)
    x1_squared = _compose(x1, x1, p, q)
    x1_cubed = _compose(x1, x1_squared, p, q)
    x1_jacobian = sp.Matrix([
        [sp.diff(x1[0], p), sp.diff(x1[0], q)],
        [sp.diff(x1[1], p), sp.diff(x1[1], q)],
    ]).subs({p: p0, q: q0})

    r2 = _add(
        (p2, q2),
        _scale(_substitute(x1_squared, p, q, p0, q0), -1),
    )
    r3 = _add(
        (p3, q3),
        _scale(_substitute(x1_cubed, p, q, p0, q0), -1),
    )

    second_hamiltonian_basis = [
        p, q, p**2, p * q, q**2, p**3, p**2 * q
    ]
    third_field_basis: list[tuple[sp.Expr, Pair]]
    third_first_scalar_basis: list[sp.Expr] = []
    third_second_scalar_basis: list[sp.Expr] = []
    if all_degree_target_window:
        (
            third_field_basis,
            third_first_scalar_basis,
            third_second_scalar_basis,
        ) = _hamiltonian_field_window(10, 12, p, q)
    else:
        third_field_basis = [
            (
                p**i * q**j,
                _hamiltonian_field(p**i * q**j, p, q),
            )
            for total in range(1, maximum_third_hamiltonian_degree + 1)
            for i in range(total + 1)
            for j in [total - i]
        ]

    columns: list[JetColumn] = []
    metadata: list[dict[str, object]] = []
    source_monomials = _monomials(maximum_source_degree)

    def add_source_columns(order: int) -> None:
        for component in range(2):
            forbidden = (
                {(0, 0)}
                if component == 0
                else {(0, 0), (1, 0)}
            )
            for i, j in source_monomials:
                if (i, j) in forbidden:
                    continue
                monomial = v**i * t**j
                image = (
                    sp.expand(jacobian[0, component] * monomial),
                    sp.expand(jacobian[1, component] * monomial),
                )
                if order == 2:
                    cross = tuple(
                        sp.expand(3 * item)
                        for item in x1_jacobian * sp.Matrix(image)
                    )
                    column: JetColumn = (
                        image[0], image[1], cross[0], cross[1]
                    )
                else:
                    column = (sp.Integer(0), sp.Integer(0), image[0], image[1])
                columns.append(column)
                metadata.append({
                    "kind": f"Y{order}",
                    "component": component,
                    "monomial": [i, j],
                    "source_degree": i + j,
                })

    add_source_columns(2)

    for hamiltonian in second_hamiltonian_basis:
        x2 = _hamiltonian_field(hamiltonian, p, q)
        mixed = _scale(
            _add(
                _compose(x1, x2, p, q),
                _compose(x2, x1, p, q),
            ),
            sp.Rational(3, 2),
        )
        x2_at = _substitute(x2, p, q, p0, q0)
        mixed_at = _substitute(mixed, p, q, p0, q0)
        columns.append((
            x2_at[0], x2_at[1], mixed_at[0], mixed_at[1]
        ))
        metadata.append({
            "kind": "K2",
            "hamiltonian": str(hamiltonian),
            "target_degree": int(sp.Poly(hamiltonian, p, q).total_degree()),
        })

    add_source_columns(3)

    for hamiltonian, field in third_field_basis:
        x3_at = _substitute(
            field,
            p,
            q,
            p0,
            q0,
        )
        columns.append((
            sp.Integer(0), sp.Integer(0), x3_at[0], x3_at[1]
        ))
        metadata.append({
            "kind": "K3",
            "hamiltonian": str(hamiltonian),
            "target_degree": int(sp.Poly(hamiltonian, p, q).total_degree()),
            "all_degree_window_member": all_degree_target_window,
        })

    matrix, rhs, row_keys = _coefficient_system(
        columns,
        (r2[0], r2[1], r3[0], r3[1]),
        v,
        t,
    )

    checks: dict[str, dict[str, dict[str, object]]] = {}
    first_consistent: tuple[int, int, list[int], DomainMatrix] | None = None
    for source_degree in range(2, maximum_source_degree + 1):
        checks[str(source_degree)] = {}
        for target_degree in range(1, maximum_third_hamiltonian_degree + 1):
            indices = [
                index
                for index, item in enumerate(metadata)
                if (
                    item["kind"] == "K2"
                    or (
                        item["kind"] in {"Y2", "Y3"}
                        and int(item["source_degree"]) <= source_degree
                    )
                    or (
                        item["kind"] == "K3"
                        and (
                            all_degree_target_window
                            or int(item["target_degree"]) <= target_degree
                        )
                    )
                )
            ]
            selected = matrix.extract(
                list(range(matrix.shape[0])), indices
            )
            rank = selected.rank()
            augmented_rank = DomainMatrix.hstack(selected, rhs).rank()
            consistent = rank == augmented_rank
            checks[str(source_degree)][str(target_degree)] = {
                "column_count": len(indices),
                "rank": rank,
                "augmented_rank": augmented_rank,
                "consistent": consistent,
            }
            if (
                consistent
                and (
                    first_consistent is None
                    or (source_degree, target_degree)
                    < (first_consistent[0], first_consistent[1])
                )
            ):
                first_consistent = (
                    source_degree,
                    target_degree,
                    indices,
                    selected,
                )

    if first_consistent is None:
        raise RuntimeError("no compatible prefix inside the declared bounds")
    source_degree, target_degree, indices, selected = first_consistent
    solution = _particular_solution(selected, rhs)

    def decode(
        vector: sp.Matrix,
    ) -> tuple[Pair, Pair, sp.Expr, sp.Expr]:
        y2 = [sp.Integer(0), sp.Integer(0)]
        y3 = [sp.Integer(0), sp.Integer(0)]
        k2 = sp.Integer(0)
        k3 = sp.Integer(0)
        for coefficient, index in zip(vector, indices, strict=True):
            item = metadata[index]
            kind = item["kind"]
            if kind in {"Y2", "Y3"}:
                i, j = item["monomial"]
                destination = y2 if kind == "Y2" else y3
                destination[int(item["component"])] += (
                    coefficient * v**int(i) * t**int(j)
                )
            elif kind == "K2":
                k2 += coefficient * sp.sympify(
                    item["hamiltonian"], locals={"P": p, "Q": q}
                )
            else:
                k3 += coefficient * sp.sympify(
                    item["hamiltonian"], locals={"P": p, "Q": q}
                )
        return (
            (sp.expand(y2[0]), sp.expand(y2[1])),
            (sp.expand(y3[0]), sp.expand(y3[1])),
            sp.expand(k2),
            sp.expand(k3),
        )

    y2_pair, y3_pair, k2, k3 = decode(solution)
    nullspace = selected.to_Matrix().nullspace()
    homogeneous_directions = []
    for vector in nullspace:
        direction_y2, direction_y3, direction_k2, direction_k3 = decode(
            vector
        )
        homogeneous_directions.append({
            "K2": str(direction_k2),
            "K3": str(direction_k3),
            "Y2": [str(item) for item in direction_y2],
            "Y3": [str(item) for item in direction_y3],
            "K2_sha256": _sha(direction_k2),
            "K3_sha256": _sha(direction_k3),
            "Y2_sha256": [_sha(item) for item in direction_y2],
            "Y3_sha256": [_sha(item) for item in direction_y3],
        })

    x2 = _hamiltonian_field(k2, p, q)
    x3 = _hamiltonian_field(k3, p, q)
    x2_at = _substitute(x2, p, q, p0, q0)
    x3_at = _substitute(x3, p, q, p0, q0)
    jy2 = tuple(sp.expand(item) for item in jacobian * sp.Matrix(y2_pair))
    jy3 = tuple(sp.expand(item) for item in jacobian * sp.Matrix(y3_pair))
    mixed = _scale(
        _add(
            _compose(x1, x2, p, q),
            _compose(x2, x1, p, q),
        ),
        sp.Rational(3, 2),
    )
    mixed_at = _substitute(mixed, p, q, p0, q0)
    source_cross = tuple(
        sp.expand(3 * item)
        for item in x1_jacobian * sp.Matrix(jy2)
    )
    second_lhs = _add(jy2, x2_at)
    third_lhs = _add(jy3, x3_at, mixed_at, source_cross)
    assert all(
        sp.expand(left - right) == 0
        for left, right in zip(second_lhs, r2, strict=True)
    )
    assert all(
        sp.expand(left - right) == 0
        for left, right in zip(third_lhs, r3, strict=True)
    )
    assert y2_pair[0].subs({v: 0, t: 0}) == 0
    assert y2_pair[1].subs({v: 0, t: 0}) == 0
    assert sp.diff(y2_pair[1].subs(t, 0), v).subs(v, 0) == 0
    assert y3_pair[0].subs({v: 0, t: 0}) == 0
    assert y3_pair[1].subs({v: 0, t: 0}) == 0
    assert sp.diff(y3_pair[1].subs(t, 0), v).subs(v, 0) == 0

    final_cap_records = {
        str(degree): checks[str(degree)][
            str(maximum_third_hamiltonian_degree)
        ]
        for degree in range(2, maximum_source_degree + 1)
    }
    target_cap_records = {
        str(cap): checks[str(source_degree)][str(cap)]
        for cap in range(1, maximum_third_hamiltonian_degree + 1)
    }
    return {
        "schema": "axiompack.jacobian_gauge_minimized_third_jet.v1",
        "formal_contact_convention": {
            "target_logarithm": (
                "A_s=s*X1+s^2/2*X2+s^3/6*X3"
            ),
            "source_logarithm": "B_s=s^2/2*Y2+s^3/6*Y3",
            "target_map": "exp(A_s)",
            "source_map": "exp(B_s)",
        },
        "source_lift_ideals": ["U in (v,t)", "V in (t,v^2)"],
        "second_hamiltonian_basis": [
            str(item) for item in second_hamiltonian_basis
        ],
        "maximum_third_hamiltonian_degree_tested": (
            maximum_third_hamiltonian_degree
        ),
        "third_target_basis_mode": (
            "all_degree_C_normal_form"
            if all_degree_target_window
            else "raw_hamiltonian_degree_cutoff"
        ),
        "third_target_component_degree_window": [10, 12],
        "third_first_scalar_normal_basis": [
            str(item) for item in third_first_scalar_basis
        ],
        "third_second_scalar_normal_basis": [
            str(item) for item in third_second_scalar_basis
        ],
        "third_hamiltonian_field_window_dimension": len(
            third_field_basis
        ),
        "minimum_prefix_source_degree": source_degree,
        "first_consistent_third_hamiltonian_degree": target_degree,
        "source_bound_checks_at_final_target_cap": final_cap_records,
        "target_cap_checks_at_minimum_source_bound": target_cap_records,
        "witness": {
            "K2": str(k2),
            "K3": str(k3),
            "Y2": [str(item) for item in y2_pair],
            "Y3": [str(item) for item in y3_pair],
            "K2_sha256": _sha(k2),
            "K3_sha256": _sha(k3),
            "Y2_sha256": [_sha(item) for item in y2_pair],
            "Y3_sha256": [_sha(item) for item in y3_pair],
            "Y2_degrees": [_degree(item, v, t) for item in y2_pair],
            "Y3_degrees": [_degree(item, v, t) for item in y3_pair],
            "second_equation_replay": True,
            "third_equation_replay": True,
        },
        "solution_affine_dimension": len(nullspace),
        "homogeneous_directions": homogeneous_directions,
        "coefficient_system": {
            "row_count": matrix.shape[0],
            "full_column_count": matrix.shape[1],
            "selected_column_count": selected.shape[1],
            "selected_matrix_sha256": _matrix_sha(selected),
            "rhs_sha256": _matrix_sha(rhs),
            "row_key_sha256": hashlib.sha256(
                json.dumps(row_keys, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        },
        "claim_boundary": (
            "exact compatible prefix through order three; finite target-cap "
            "stabilization is diagnostic until the C-normal-form window is "
            "proved for the third-order component bounds"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
