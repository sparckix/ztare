#!/usr/bin/env python3
"""Extend the compatible degree-five formal contact through order four."""
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

from gauge_minimized_third_jet import (  # noqa: E402
    _act,
    _add,
    _compose,
    _hamiltonian_field,
    _monomials,
    _particular_solution,
    _scale,
    _substitute,
    run as run_third,
)


Pair = tuple[sp.Expr, sp.Expr]


def _family_jets(maximum_order: int) -> dict[str, object]:
    s, v, t, z = sp.symbols("s v t z")
    gamma = 1 - sp.Rational(3, 2) * v + t
    mu = 3 * (s - 4) / (2 * (s - 6))
    lam = -(s - 4) / 4
    w = (1 + mu * v) * gamma
    p = (2 + s / 2) * z + (-3 - 3 * s / 2) * z**2 + s * z**3
    q = (1 + s / 4) * z**2 - (2 + s) * z**3 + 3 * s * z**4 / 4
    beta = sp.cancel(lam / mu * (1 + p.subs(z, w) / gamma))
    alpha = sp.cancel((1 + mu * v + q.subs(z, w) / gamma**2) / lam)
    p_jets = [
        sp.cancel(gamma * sp.diff(beta, s, order).subs(s, 0))
        for order in range(maximum_order + 1)
    ]
    q_jets = [
        sp.cancel(gamma**2 * sp.diff(alpha, s, order).subs(s, 0))
        for order in range(maximum_order + 1)
    ]
    assert all(
        not ({v, t} & sp.denom(value).free_symbols)
        for value in p_jets + q_jets
    )
    return {
        "symbols": (v, t),
        "gamma": gamma,
        "P": p_jets,
        "Q": q_jets,
    }


def _source_act(
    field: Pair, value: sp.Expr, v: sp.Symbol, t: sp.Symbol
) -> sp.Expr:
    return sp.expand(
        field[0] * sp.diff(value, v) + field[1] * sp.diff(value, t)
    )


def _source_act_pair(
    field: Pair, pair: Pair, v: sp.Symbol, t: sp.Symbol
) -> Pair:
    return (
        _source_act(field, pair[0], v, t),
        _source_act(field, pair[1], v, t),
    )


def _pair_system(
    columns: list[Pair],
    rhs: Pair,
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
        (component, i, j)
        for component in range(2)
        for polynomial in (
            [column[component] for column in polynomial_columns]
            + [rhs_polynomials[component]]
        )
        for i, j in polynomial.monoms()
    })
    row_index = {key: index for index, key in enumerate(row_keys)}
    entries: dict[int, dict[int, sp.Rational]] = {}
    for column_index, column in enumerate(polynomial_columns):
        for component, polynomial in enumerate(column):
            for (i, j), coefficient in polynomial.terms():
                if coefficient:
                    entries.setdefault(
                        row_index[(component, i, j)], {}
                    )[column_index] = sp.Rational(coefficient)
    rhs_entries: dict[int, dict[int, sp.Rational]] = {}
    for component, polynomial in enumerate(rhs_polynomials):
        for (i, j), coefficient in polynomial.terms():
            if coefficient:
                rhs_entries.setdefault(
                    row_index[(component, i, j)], {}
                )[0] = sp.Rational(coefficient)
    return (
        DomainMatrix.from_dict_sympy(
            len(row_keys), len(columns), entries
        ).to_field(),
        DomainMatrix.from_dict_sympy(
            len(row_keys), 1, rhs_entries
        ).to_field(),
        row_keys,
    )


def _matrix_sha(matrix: DomainMatrix) -> str:
    return hashlib.sha256(
        json.dumps(
            [
                [str(item) for item in row]
                for row in matrix.to_Matrix().tolist()
            ],
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(str(sp.expand(value)).encode("utf-8")).hexdigest()


def _degree(value: sp.Expr, v: sp.Symbol, t: sp.Symbol) -> int:
    if value == 0:
        return -1
    return int(sp.Poly(value, v, t, domain=sp.QQ).total_degree())


def run(
    *,
    source_degree_bound: int = 6,
    maximum_fourth_hamiltonian_degree: int = 4,
) -> dict[str, object]:
    if source_degree_bound < 5:
        raise ValueError("the certified second-jet lower bound is five")

    prefix = run_third(
        maximum_source_degree=source_degree_bound,
        maximum_third_hamiltonian_degree=4,
    )
    witness = prefix["witness"]

    data = _family_jets(4)
    v, t = data["symbols"]
    p, q = sp.symbols("P Q")
    p0, q0 = data["P"][0], data["Q"][0]
    f4 = data["P"][4], data["Q"][4]
    jacobian = sp.Matrix([
        [sp.diff(p0, v), sp.diff(p0, t)],
        [sp.diff(q0, v), sp.diff(q0, t)],
    ])

    locals_target = {"P": p, "Q": q}
    locals_source = {"v": v, "t": t}
    k2 = sp.sympify(witness["K2"], locals=locals_target)
    k3 = sp.sympify(witness["K3"], locals=locals_target)
    y2: Pair = tuple(
        sp.sympify(item, locals=locals_source) for item in witness["Y2"]
    )  # type: ignore[assignment]
    y3: Pair = tuple(
        sp.sympify(item, locals=locals_source) for item in witness["Y3"]
    )  # type: ignore[assignment]

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

    columns: list[Pair] = []
    metadata: list[dict[str, object]] = []
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
            metadata.append({
                "kind": "Y4",
                "component": component,
                "monomial": [i, j],
            })

    for total in range(1, maximum_fourth_hamiltonian_degree + 1):
        for i in range(total + 1):
            hamiltonian = p**i * q ** (total - i)
            columns.append(_substitute(
                _hamiltonian_field(hamiltonian, p, q),
                p,
                q,
                p0,
                q0,
            ))
            metadata.append({
                "kind": "K4",
                "hamiltonian": str(hamiltonian),
                "target_degree": total,
            })

    matrix, rhs, row_keys = _pair_system(columns, residual, v, t)
    cap_checks: dict[str, dict[str, object]] = {}
    first_consistent: tuple[int, list[int], DomainMatrix] | None = None
    for cap in range(1, maximum_fourth_hamiltonian_degree + 1):
        indices = [
            index
            for index, item in enumerate(metadata)
            if (
                item["kind"] == "Y4"
                or int(item["target_degree"]) <= cap
            )
        ]
        selected = matrix.extract(list(range(matrix.shape[0])), indices)
        rank = selected.rank()
        augmented_rank = DomainMatrix.hstack(selected, rhs).rank()
        consistent = rank == augmented_rank
        cap_checks[str(cap)] = {
            "column_count": len(indices),
            "rank": rank,
            "augmented_rank": augmented_rank,
            "consistent": consistent,
        }
        if consistent and first_consistent is None:
            first_consistent = cap, indices, selected
    if first_consistent is None:
        return {
            "schema": "axiompack.jacobian_gauge_minimized_fourth_jet.v1",
            "prefix_source_degree": source_degree_bound,
            "prefix_K2_sha256": witness["K2_sha256"],
            "prefix_K3_sha256": witness["K3_sha256"],
            "maximum_fourth_hamiltonian_degree_tested": (
                maximum_fourth_hamiltonian_degree
            ),
            "cap_checks": cap_checks,
            "extended": False,
            "claim_boundary": (
                "this particular degree-five third-order prefix did not "
                "extend inside the tested K4 window"
            ),
        }

    cap, indices, selected = first_consistent
    solution = _particular_solution(selected, rhs)
    y4 = [sp.Integer(0), sp.Integer(0)]
    k4 = sp.Integer(0)
    for coefficient, index in zip(solution, indices, strict=True):
        item = metadata[index]
        if item["kind"] == "Y4":
            i, j = item["monomial"]
            y4[int(item["component"])] += (
                coefficient * v**int(i) * t**int(j)
            )
        else:
            k4 += coefficient * sp.sympify(
                item["hamiltonian"], locals=locals_target
            )
    y4_pair = sp.expand(y4[0]), sp.expand(y4[1])
    k4 = sp.expand(k4)
    x4_at = _substitute(
        _hamiltonian_field(k4, p, q), p, q, p0, q0
    )
    jy4 = tuple(sp.expand(item) for item in jacobian * sp.Matrix(y4_pair))
    assert all(
        sp.expand(left + right - target) == 0
        for left, right, target in zip(jy4, x4_at, residual, strict=True)
    )
    assert y4_pair[0].subs({v: 0, t: 0}) == 0
    assert y4_pair[1].subs({v: 0, t: 0}) == 0
    assert sp.diff(y4_pair[1].subs(t, 0), v).subs(v, 0) == 0

    return {
        "schema": "axiompack.jacobian_gauge_minimized_fourth_jet.v1",
        "formal_contact_convention": prefix["formal_contact_convention"],
        "compatible_prefix_source_degree_bound_through_order_four": (
            source_degree_bound
        ),
        "first_consistent_fourth_hamiltonian_degree": cap,
        "maximum_fourth_hamiltonian_degree_tested": (
            maximum_fourth_hamiltonian_degree
        ),
        "cap_checks": cap_checks,
        "extended": True,
        "prefix": {
            "K2": witness["K2"],
            "K3": witness["K3"],
            "Y2_sha256": witness["Y2_sha256"],
            "Y3_sha256": witness["Y3_sha256"],
        },
        "witness": {
            "K4": str(k4),
            "Y4": [str(item) for item in y4_pair],
            "K4_sha256": _sha(k4),
            "Y4_sha256": [_sha(item) for item in y4_pair],
            "Y4_degrees": [_degree(item, v, t) for item in y4_pair],
            "fourth_equation_replay": True,
        },
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
            "one explicit compatible logarithmic prefix through order four; "
            "combined with the separate all-degree obstruction against every "
            "degree-five prefix, it proves the prefix minimum is six"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
