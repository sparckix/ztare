#!/usr/bin/env python3
"""Complete fixed-bound formal-contact families, beginning through order three."""
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

from gauge_minimized_fourth_jet import _family_jets  # noqa: E402
from gauge_minimized_third_jet import (  # noqa: E402
    _add,
    _coefficient_system,
    _compose,
    _hamiltonian_field_window,
    _monomials,
    _particular_solution,
    _scale,
    _substitute,
)


Pair = tuple[sp.Expr, sp.Expr]
JetColumn = tuple[sp.Expr, sp.Expr, sp.Expr, sp.Expr]


def _degree(value: sp.Expr, v: sp.Symbol, t: sp.Symbol) -> int:
    if value == 0:
        return -1
    return int(sp.Poly(value, v, t).total_degree())


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(str(sp.expand(value)).encode("utf-8")).hexdigest()


def build_through_three(bound: int) -> dict[str, object]:
    data = _family_jets(3)
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

    source_monomials = _monomials(bound)
    source_images: dict[tuple[int, int, int], Pair] = {}
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
            source_images[(component, i, j)] = (
                sp.expand(jacobian[0, component] * monomial),
                sp.expand(jacobian[1, component] * monomial),
            )

    def component_window(
        floor: tuple[int, int], pairs: list[Pair]
    ) -> tuple[int, int]:
        return tuple(
            max(
                floor[component],
                *(
                    _degree(pair[component], v, t)
                    for pair in pairs
                ),
            )
            for component in range(2)
        )  # type: ignore[return-value]

    # The target windows are derived from every term that can occur in the
    # corresponding coefficient equation.  This keeps the normal-form basis
    # exhaustive when the source bound grows; fixed offsets happened to be
    # sufficient only through bound eight.
    k2_window = component_window(
        (8, 10), [r2, *source_images.values()]
    )
    k2_basis, k2_first, k2_second = _hamiltonian_field_window(
        *k2_window, p, q
    )

    source_crosses = [
        tuple(
            sp.expand(3 * item)
            for item in x1_jacobian * sp.Matrix(image)
        )
        for image in source_images.values()
    ]
    k2_mixed: list[tuple[sp.Expr, Pair, Pair]] = []
    for hamiltonian, field in k2_basis:
        mixed = _scale(
            _add(
                _compose(x1, field, p, q),
                _compose(field, x1, p, q),
            ),
            sp.Rational(3, 2),
        )
        mixed_at = _substitute(mixed, p, q, p0, q0)
        k2_mixed.append((hamiltonian, field, mixed_at))
    k3_window = component_window(
        (10, 12),
        [
            r3,
            *source_images.values(),
            *source_crosses,
            *(mixed_at for _hamiltonian, _field, mixed_at in k2_mixed),
        ],
    )
    k3_basis, k3_first, k3_second = _hamiltonian_field_window(
        *k3_window, p, q
    )

    columns: list[JetColumn] = []
    metadata: list[dict[str, object]] = []

    def add_source(order: int) -> None:
        for (component, i, j), image in source_images.items():
            if order == 2:
                cross = tuple(
                    sp.expand(3 * item)
                    for item in x1_jacobian * sp.Matrix(image)
                )
                column: JetColumn = (
                    image[0], image[1], cross[0], cross[1]
                )
            else:
                column = (
                    sp.Integer(0),
                    sp.Integer(0),
                    image[0],
                    image[1],
                )
            columns.append(column)
            metadata.append({
                "kind": f"Y{order}",
                "component": component,
                "monomial": [i, j],
            })

    add_source(2)
    for hamiltonian, field, mixed_at in k2_mixed:
        field_at = _substitute(field, p, q, p0, q0)
        columns.append((
            field_at[0], field_at[1], mixed_at[0], mixed_at[1]
        ))
        metadata.append({
            "kind": "K2",
            "hamiltonian": hamiltonian,
        })
    add_source(3)
    for hamiltonian, field in k3_basis:
        field_at = _substitute(field, p, q, p0, q0)
        columns.append((
            sp.Integer(0),
            sp.Integer(0),
            field_at[0],
            field_at[1],
        ))
        metadata.append({
            "kind": "K3",
            "hamiltonian": hamiltonian,
        })

    matrix, rhs, row_keys = _coefficient_system(
        columns, (r2[0], r2[1], r3[0], r3[1]), v, t
    )
    rank = matrix.rank()
    augmented_rank = DomainMatrix.hstack(matrix, rhs).rank()
    if rank != augmented_rank:
        raise ValueError(f"bound {bound} has no prefix through order three")
    particular = _particular_solution(matrix, rhs)
    nullspace = matrix.to_Matrix().nullspace()

    def decode(vector: sp.Matrix) -> dict[str, object]:
        source = {
            2: [sp.Integer(0), sp.Integer(0)],
            3: [sp.Integer(0), sp.Integer(0)],
        }
        hamiltonians = {2: sp.Integer(0), 3: sp.Integer(0)}
        for coefficient, item in zip(vector, metadata, strict=True):
            if item["kind"] in {"Y2", "Y3"}:
                order = int(str(item["kind"])[1:])
                i, j = item["monomial"]
                source[order][int(item["component"])] += (
                    coefficient * v**int(i) * t**int(j)
                )
            else:
                order = int(str(item["kind"])[1:])
                hamiltonians[order] += (
                    coefficient * item["hamiltonian"]
                )
        return {
            "K2": sp.expand(hamiltonians[2]),
            "K3": sp.expand(hamiltonians[3]),
            "Y2": (
                sp.expand(source[2][0]),
                sp.expand(source[2][1]),
            ),
            "Y3": (
                sp.expand(source[3][0]),
                sp.expand(source[3][1]),
            ),
        }

    return {
        "bound": bound,
        "symbols": {
            "source": (v, t),
            "target": (p, q),
        },
        "data": data,
        "jacobian": jacobian,
        "x1": x1,
        "first_order_slice": {
            "Y1": (sp.Integer(0), sp.Integer(0)),
            "X1": x1,
            "order_one_isotropy_included": False,
        },
        "particular": decode(particular),
        "directions": [decode(vector) for vector in nullspace],
        "matrix": matrix,
        "rhs": rhs,
        "row_keys": row_keys,
        "rank": rank,
        "nullity": len(nullspace),
        "k2_window": k2_window,
        "k3_window": k3_window,
        "k2_basis_dimension": len(k2_basis),
        "k3_basis_dimension": len(k3_basis),
        "k2_scalar_bases": (k2_first, k2_second),
        "k3_scalar_bases": (k3_first, k3_second),
    }


def run(bound: int = 7) -> dict[str, object]:
    family = build_through_three(bound)

    def encode(item: dict[str, object]) -> dict[str, object]:
        return {
            "K2": str(item["K2"]),
            "K3": str(item["K3"]),
            "Y2_degrees": [
                _degree(value, *family["symbols"]["source"])
                for value in item["Y2"]
            ],
            "Y3_degrees": [
                _degree(value, *family["symbols"]["source"])
                for value in item["Y3"]
            ],
            "sha256": {
                "K2": _sha(item["K2"]),
                "K3": _sha(item["K3"]),
                "Y2": [_sha(value) for value in item["Y2"]],
                "Y3": [_sha(value) for value in item["Y3"]],
            },
        }

    return {
        "schema": "axiompack.jacobian_fixed_bound_prefix.v1",
        "bound": bound,
        "first_order_slice": {
            "Y1": [
                str(item)
                for item in family["first_order_slice"]["Y1"]
            ],
            "X1": [
                str(item)
                for item in family["first_order_slice"]["X1"]
            ],
            "order_one_isotropy_included": family[
                "first_order_slice"
            ]["order_one_isotropy_included"],
        },
        "rank": family["rank"],
        "nullity": family["nullity"],
        "k2_component_window": list(family["k2_window"]),
        "k3_component_window": list(family["k3_window"]),
        "k2_field_dimension": family["k2_basis_dimension"],
        "k3_field_dimension": family["k3_basis_dimension"],
        "particular": encode(family["particular"]),
        "direction_count": len(family["directions"]),
        "direction_sha256": [
            encode(item)["sha256"] for item in family["directions"]
        ],
        "row_key_sha256": hashlib.sha256(
            json.dumps(
                family["row_keys"], separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest(),
    }


if __name__ == "__main__":
    selected_bound = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    print(json.dumps(run(selected_bound), indent=2, sort_keys=True))
