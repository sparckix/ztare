#!/usr/bin/env python3
"""Sparse-path rational degree-eight witness through order six."""
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

from gauge_bound_four_extension import build_through_four  # noqa: E402
from gauge_minimized_fifth_obstruction import (  # noqa: E402
    _decode_generator,
    _source_degree,
    _source_target_image,
    _target_lift_ideals,
)
from gauge_minimized_fourth_jet import _family_jets, _pair_system  # noqa: E402
from gauge_minimized_recursive_prefix import _composed_series  # noqa: E402
from gauge_minimized_third_jet import (  # noqa: E402
    _hamiltonian_field,
    _particular_solution,
)


Pair = tuple[sp.Expr, sp.Expr]


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(str(sp.expand(value)).encode("utf-8")).hexdigest()


def _top_in_v_l(
    value: sp.Expr,
    v: sp.Symbol,
    t: sp.Symbol,
    ell: sp.Symbol,
) -> sp.Expr:
    polynomial = sp.Poly(sp.expand(value), v, t)
    degree = polynomial.total_degree()
    top = sum(
        coefficient * v**monomial[0] * t**monomial[1]
        for monomial, coefficient in polynomial.terms()
        if sum(monomial) == degree
    )
    return sp.factor(sp.expand(top.subs(t, (ell + 3 * v) / 2)))


def _solve_new_order(
    *,
    order: int,
    bound: int,
    residual: Pair,
    family: dict[str, object],
    data: dict[str, object],
    v: sp.Symbol,
    t: sp.Symbol,
    p: sp.Symbol,
    q: sp.Symbol,
) -> tuple[Pair, sp.Expr, dict[str, object]]:
    residual_degrees = [
        _source_degree(item, v, t) for item in residual
    ]
    columns, metadata, target_window = _source_target_image(
        source_order=order,
        source_degree_bound=bound,
        first_target_degree=max(bound + 3, residual_degrees[0]),
        second_target_degree=max(bound + 5, residual_degrees[1]),
        v=v,
        t=t,
        p=p,
        q=q,
        p0=data["P"][0],
        q0=data["Q"][0],
        jacobian=family["jacobian"],
    )
    matrix, rhs, row_keys = _pair_system(
        columns, residual, v, t
    )
    rank = matrix.rank()
    augmented_rank = DomainMatrix.hstack(matrix, rhs).rank()
    if rank != augmented_rank:
        raise ValueError(
            f"degree {bound} is incompatible at order {order}"
        )
    vector = _particular_solution(matrix, rhs)
    source, hamiltonian = _decode_generator(
        vector, metadata, order, v, t, p, q
    )
    return source, hamiltonian, {
        "rank": rank,
        "column_count": matrix.shape[1],
        "nullity": matrix.shape[1] - rank,
        "residual_component_degrees": residual_degrees,
        "target_window": target_window,
        "row_key_sha256": hashlib.sha256(
            json.dumps(row_keys, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }


def run(bound: int = 8) -> dict[str, object]:
    if bound != 8:
        raise ValueError("this witness is specialized to the exact bound 8")
    family = build_through_four(bound)
    data = _family_jets(6)
    v, t = data["symbols"]
    p, q = family["symbols"]["target"]
    parameter_values_by_name = {
        "a0": sp.Rational(11341, 80640),
        "a1": sp.Rational(1229, 20736),
        "a2": -sp.Rational(4729, 40320),
        "a3": sp.Integer(0),
        "a4": sp.Rational(2291, 36288),
        "a5": sp.Rational(733, 145152),
        "b0": sp.Integer(0),
        "b1": sp.Integer(0),
        "b2": sp.Integer(0),
    }
    parameters = family["complete_parameters_through_four"]
    if {str(item) for item in parameters} != set(
        parameter_values_by_name
    ):
        raise ValueError(
            f"unexpected degree-eight family coordinates: {parameters}"
        )
    substitution = {
        parameter: parameter_values_by_name[str(parameter)]
        for parameter in parameters
    }
    target_fields = {
        order: tuple(
            sp.expand(item.subs(substitution))
            for item in field
        )
        for order, field in family["target_fields"].items()
    }
    source_fields = {
        order: tuple(
            sp.expand(item.subs(substitution))
            for item in field
        )
        for order, field in family["source_fields"].items()
    }

    through_four = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=data["P"][0],
        q0=data["Q"][0],
        maximum_order=5,
    )
    residual_five = (
        sp.expand(data["P"][5] - 120 * through_four[5][0]),
        sp.expand(data["Q"][5] - 120 * through_four[5][1]),
    )
    y5, k5, fifth_receipt = _solve_new_order(
        order=5,
        bound=bound,
        residual=residual_five,
        family=family,
        data=data,
        v=v,
        t=t,
        p=p,
        q=q,
    )
    target_fields[5] = _hamiltonian_field(k5, p, q)
    source_fields[5] = y5

    through_five = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=data["P"][0],
        q0=data["Q"][0],
        maximum_order=6,
    )
    residual_six = (
        sp.expand(data["P"][6] - 720 * through_five[6][0]),
        sp.expand(data["Q"][6] - 720 * through_five[6][1]),
    )
    y6, k6, sixth_receipt = _solve_new_order(
        order=6,
        bound=bound,
        residual=residual_six,
        family=family,
        data=data,
        v=v,
        t=t,
        p=p,
        q=q,
    )
    target_fields[6] = _hamiltonian_field(k6, p, q)
    source_fields[6] = y6

    target_lift_checks = {
        str(order): _target_lift_ideals(field, p, q)
        for order, field in target_fields.items()
    }
    assert all(target_lift_checks.values())

    completed = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=data["P"][0],
        q0=data["Q"][0],
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
                completed[order], actual, strict=True
            )
        )
    ell = sp.Symbol("L")
    source_top_shells = {}
    z = sp.Symbol("z")
    u = sp.Symbol("u")
    compactification_substitution = {
        v: 1 / z - 1,
        t: sp.Rational(3, 2) / z
        + (u + 1) * z / 3
        - sp.Rational(5, 2),
    }
    source_cusp_residues = {}
    for order, field in source_fields.items():
        u_top = _top_in_v_l(field[0], v, t, ell)
        ell_top = _top_in_v_l(
            2 * field[1] - 3 * field[0], v, t, ell
        )
        source_top_shells[str(order)] = {
            "v_component": str(u_top),
            "L_component": str(ell_top),
        }
        affine_u = sp.cancel(
            field[0].subs(compactification_substitution)
        )
        affine_v = sp.cancel(
            field[1].subs(compactification_substitution)
        )
        local_z = sp.cancel(-z**2 * affine_u)
        local_u = sp.cancel(
            3 * (affine_v - sp.Rational(3, 2) * affine_u) / z
            + (u + 1) * z * affine_u
        )
        z_residue = sp.factor(
            sp.cancel(z * local_z).subs(z, 0)
        )
        u_residue = sp.factor(
            sp.cancel(z * local_u).subs(z, 0)
        )
        source_cusp_residues[str(order)] = {
            "z_times_dz_at_z0": str(z_residue),
            "z_times_du_at_z0": str(u_residue),
            "z_residue_degree_in_u": (
                -1
                if z_residue == 0
                else int(sp.Poly(z_residue, u).degree())
            ),
            "u_residue_degree_in_u": (
                -1
                if u_residue == 0
                else int(sp.Poly(u_residue, u).degree())
            ),
        }
    return {
        "schema": "axiompack.jacobian_fixed_bound_six_witness.v1",
        "bound": bound,
        "sixth_compatibility_coordinate": {
            key: str(value)
            for key, value in parameter_values_by_name.items()
        },
        "fifth_solve": fifth_receipt,
        "sixth_solve": sixth_receipt,
        "source_field_degrees": {
            str(order): [
                _source_degree(item, v, t) for item in field
            ]
            for order, field in source_fields.items()
        },
        "target_field_sha256": {
            str(order): [_sha(item) for item in field]
            for order, field in target_fields.items()
        },
        "source_field_sha256": {
            str(order): [_sha(item) for item in field]
            for order, field in source_fields.items()
        },
        "target_three_variable_lift_ideals": target_lift_checks,
        "source_top_shells_in_v_L": source_top_shells,
        "source_cusp_residues": source_cusp_residues,
        "full_prefix_replay": True,
        "claim": "a rational source-degree-eight prefix reaches order six",
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
