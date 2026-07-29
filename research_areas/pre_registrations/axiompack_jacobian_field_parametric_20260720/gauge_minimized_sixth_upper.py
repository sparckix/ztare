#!/usr/bin/env python3
"""Extend one exact c5=8 prefix through order six."""
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

from gauge_minimized_fifth_obstruction import run as run_fifth  # noqa: E402
from gauge_minimized_fourth_jet import (  # noqa: E402
    _family_jets,
    _matrix_sha,
    _pair_system,
)
from gauge_minimized_recursive_prefix import _composed_series  # noqa: E402
from gauge_minimized_third_jet import (  # noqa: E402
    _hamiltonian_field,
    _monomials,
    _particular_solution,
    _substitute,
)


Pair = tuple[sp.Expr, sp.Expr]


def _parse_pair(
    values: list[str], locals_: dict[str, sp.Symbol]
) -> Pair:
    return tuple(
        sp.sympify(value, locals=locals_) for value in values
    )  # type: ignore[return-value]


def _degree(value: sp.Expr, v: sp.Symbol, t: sp.Symbol) -> int:
    if value == 0:
        return -1
    return int(sp.Poly(value, v, t, domain=sp.QQ).total_degree())


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(str(sp.expand(value)).encode("utf-8")).hexdigest()


def run(
    *,
    maximum_source_degree: int = 10,
    maximum_hamiltonian_degree: int = 7,
) -> dict[str, object]:
    fifth = run_fifth(8)
    carried = fifth["carried_prefix"]
    data = _family_jets(6)
    v, t = data["symbols"]
    p, q = sp.symbols("P Q")
    p0, q0 = data["P"][0], data["Q"][0]
    target_locals = {"P": p, "Q": q}
    source_locals = {"v": v, "t": t}
    target_fields = {
        1: _hamiltonian_field(
            -q**2 / 4 - p**3 / 36, p, q
        )
    }
    source_fields: dict[int, Pair] = {}
    for order in range(2, 6):
        hamiltonian = sp.sympify(
            carried["hamiltonians"][str(order)],
            locals=target_locals,
        )
        target_fields[order] = _hamiltonian_field(
            hamiltonian, p, q
        )
        source_fields[order] = _parse_pair(
            carried["source_fields"][str(order)],
            source_locals,
        )

    completed_five = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=p0,
        q0=q0,
        maximum_order=5,
    )
    for order in range(6):
        actual = (
            data["P"][order] / sp.factorial(order),
            data["Q"][order] / sp.factorial(order),
        )
        assert all(
            sp.expand(left - right) == 0
            for left, right in zip(
                completed_five[order], actual, strict=True
            )
        )
    predicted_six = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=p0,
        q0=q0,
        maximum_order=6,
    )
    residual = (
        sp.expand(data["P"][6] - 720 * predicted_six[6][0]),
        sp.expand(data["Q"][6] - 720 * predicted_six[6][1]),
    )
    jacobian = sp.Matrix([
        [sp.diff(p0, v), sp.diff(p0, t)],
        [sp.diff(q0, v), sp.diff(q0, t)],
    ])
    columns: list[Pair] = []
    metadata: list[dict[str, object]] = []
    for component in range(2):
        forbidden = (
            {(0, 0)} if component == 0 else {(0, 0), (1, 0)}
        )
        for i, j in _monomials(maximum_source_degree):
            if (i, j) in forbidden:
                continue
            monomial = v**i * t**j
            columns.append((
                sp.expand(jacobian[0, component] * monomial),
                sp.expand(jacobian[1, component] * monomial),
            ))
            metadata.append({
                "kind": "Y6",
                "component": component,
                "monomial": [i, j],
                "source_degree": i + j,
            })
    for total in range(1, maximum_hamiltonian_degree + 1):
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
                "kind": "K6",
                "hamiltonian": str(hamiltonian),
                "target_degree": total,
            })
    matrix, rhs, row_keys = _pair_system(columns, residual, v, t)
    checks: dict[str, dict[str, dict[str, object]]] = {}
    first_consistent: (
        tuple[int, int, list[int], DomainMatrix] | None
    ) = None
    for source_degree in range(6, maximum_source_degree + 1):
        checks[str(source_degree)] = {}
        for target_degree in range(1, maximum_hamiltonian_degree + 1):
            indices = [
                index
                for index, item in enumerate(metadata)
                if (
                    (
                        item["kind"] == "Y6"
                        and int(item["source_degree"]) <= source_degree
                    )
                    or (
                        item["kind"] == "K6"
                        and int(item["target_degree"]) <= target_degree
                    )
                )
            ]
            selected = matrix.extract(
                list(range(matrix.shape[0])), indices
            )
            rank = selected.rank()
            augmented_rank = DomainMatrix.hstack(
                selected, rhs
            ).rank()
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
        return {
            "schema": "axiompack.jacobian_sixth_upper.v1",
            "extended": False,
            "residual_component_degrees": [
                _degree(item, v, t) for item in residual
            ],
            "checks": checks,
        }
    source_degree, target_degree, indices, selected = first_consistent
    solution = _particular_solution(selected, rhs)
    y6 = [sp.Integer(0), sp.Integer(0)]
    k6 = sp.Integer(0)
    for coefficient, index in zip(solution, indices, strict=True):
        item = metadata[index]
        if item["kind"] == "Y6":
            i, j = item["monomial"]
            y6[int(item["component"])] += (
                coefficient * v**int(i) * t**int(j)
            )
        else:
            k6 += coefficient * sp.sympify(
                item["hamiltonian"], locals=target_locals
            )
    y6_pair = sp.expand(y6[0]), sp.expand(y6[1])
    k6 = sp.expand(k6)
    target_fields[6] = _hamiltonian_field(k6, p, q)
    source_fields[6] = y6_pair
    completed_six = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=p0,
        q0=q0,
        maximum_order=6,
    )
    for order in range(7):
        actual = (
            data["P"][order] / sp.factorial(order),
            data["Q"][order] / sp.factorial(order),
        )
        assert all(
            sp.expand(left - right) == 0
            for left, right in zip(
                completed_six[order], actual, strict=True
            )
        )
    return {
        "schema": "axiompack.jacobian_sixth_upper.v1",
        "extended": True,
        "source_degree_for_this_prefix": source_degree,
        "first_consistent_hamiltonian_degree": target_degree,
        "residual_component_degrees": [
            _degree(item, v, t) for item in residual
        ],
        "checks": checks,
        "witness": {
            "K6": str(k6),
            "Y6": [str(item) for item in y6_pair],
            "K6_sha256": _sha(k6),
            "Y6_sha256": [_sha(item) for item in y6_pair],
            "Y6_degrees": [
                _degree(item, v, t) for item in y6_pair
            ],
            "full_prefix_replay": True,
        },
        "coefficient_system": {
            "row_count": matrix.shape[0],
            "selected_column_count": selected.shape[1],
            "selected_matrix_sha256": _matrix_sha(selected),
            "rhs_sha256": _matrix_sha(rhs),
            "row_key_sha256": hashlib.sha256(
                json.dumps(row_keys, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        },
        "claim_boundary": (
            "upper bound for one c5-optimal prefix; a global c6 lower bound "
            "requires the complete degree-eight prefix family"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
