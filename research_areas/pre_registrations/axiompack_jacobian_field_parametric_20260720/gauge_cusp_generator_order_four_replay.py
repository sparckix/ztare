#!/usr/bin/env python3
"""Solve the corrected cusp contact at order four in Rees velocity form."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import sympy as sp
from sympy.polys.matrices import DomainMatrix


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_cusp_generator_order_three_replay import (  # noqa: E402
    _degree,
    _pade_jet,
    run as run_order_three,
)
from gauge_minimized_fourth_jet import _family_jets  # noqa: E402
from gauge_minimized_third_jet import (  # noqa: E402
    _coefficient_system,
    _hamiltonian_field,
    _hamiltonian_field_window,
    _monomials,
    _particular_solution,
    _substitute,
    run as run_logarithmic_three,
)


Pair = tuple[sp.Expr, sp.Expr]


def _act(
    field: Pair,
    value: sp.Expr,
    v: sp.Symbol,
    t: sp.Symbol,
) -> sp.Expr:
    return sp.expand(
        field[0] * sp.diff(value, v)
        + field[1] * sp.diff(value, t)
    )


def _hessian_action(
    field: sp.Matrix,
    left: sp.Matrix,
    right: sp.Matrix,
    p: sp.Symbol,
    q: sp.Symbol,
    at_seed: dict[sp.Symbol, sp.Expr],
) -> sp.Matrix:
    return sp.Matrix([
        sp.expand(
            (
                left.T
                * sp.hessian(field[index], (p, q)).subs(
                    at_seed
                )
                * right
            )[0]
        )
        for index in range(2)
    ])


def _c_normal_form(
    value: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> sp.Expr:
    c = sp.Symbol("C")
    coefficient_ring = sp.QQ.poly_ring(p, c)
    relation = (
        q**2
        - (
            c
            + (18 * p - 4) * q
            - 4 * p**3
            + p**2
        )
        / 27
    )
    return sp.expand(sp.rem(
        sp.Poly(value, q, domain=coefficient_ring),
        sp.Poly(relation, q, domain=coefficient_ring),
    ).as_expr())


def run() -> dict[str, object]:
    v, t, p, q = sp.symbols("v t P Q")
    gamma = 1 - sp.Rational(3, 2) * v + t
    x = 3 * (1 + v) * gamma - 1

    logarithmic_lower = run_logarithmic_three(
        maximum_source_degree=5,
        maximum_third_hamiltonian_degree=4,
    )["witness"]
    velocity1: Pair = tuple(
        sp.sympify(component, locals={"v": v, "t": t})
        for component in logarithmic_lower["Y2"]
    )  # type: ignore[assignment]
    hamiltonian1 = sp.sympify(
        logarithmic_lower["K2"],
        locals={"P": p, "Q": q},
    )

    third = run_order_three()
    velocity2: Pair = tuple(
        sp.sympify(component, locals={"v": v, "t": t})
        for component in third["velocity_solution"]["components"]
    )  # type: ignore[assignment]
    hamiltonian2 = sp.sympify(
        third["velocity_solution"]["target_hamiltonian"],
        locals={"P": p, "Q": q},
    )

    data = _family_jets(4)
    family = [
        sp.Matrix([data["P"][order], data["Q"][order]])
        for order in range(5)
    ]
    p0, q0 = family[0]
    at_seed = {p: p0, q: q0}
    seed_jacobian = family[0].jacobian([v, t])

    target0 = sp.Matrix([-q / 2, p**2 / 12])
    target1 = sp.Matrix(
        _hamiltonian_field(hamiltonian1, p, q)
    )
    target2 = sp.Matrix(
        _hamiltonian_field(hamiltonian2, p, q)
    )
    known_target = (
        target0.jacobian([p, q]).subs(at_seed) * family[3]
        + 3
        * _hessian_action(
            target0,
            family[1],
            family[2],
            p,
            q,
            at_seed,
        )
        + 3
        * target1.jacobian([p, q]).subs(at_seed)
        * family[2]
        + 3
        * _hessian_action(
            target1,
            family[1],
            family[1],
            p,
            q,
            at_seed,
        )
        + 3
        * target2.jacobian([p, q]).subs(at_seed)
        * family[1]
    )
    known_source = (
        3
        * family[2].jacobian([v, t])
        * sp.Matrix(velocity1)
        + 3
        * family[1].jacobian([v, t])
        * sp.Matrix(velocity2)
    )
    residual = tuple(
        sp.expand(
            family[4][index]
            - known_target[index]
            - known_source[index]
        )
        for index in range(2)
    )
    residual_degrees = [
        _degree(component, v, t) for component in residual
    ]
    assert residual_degrees == [12, 14]

    target_fields, first_normal_basis, second_normal_basis = (
        _hamiltonian_field_window(12, 14, p, q)
    )
    columns: list[tuple[sp.Expr, sp.Expr, sp.Expr, sp.Expr]] = []
    metadata: list[dict[str, object]] = []
    for component in range(2):
        forbidden = (
            {(0, 0)}
            if component == 0
            else {(0, 0), (1, 0)}
        )
        for i, j in _monomials(9):
            if (i, j) in forbidden:
                continue
            monomial = v**i * t**j
            image = seed_jacobian[:, component] * monomial
            weighted_divergence = sp.diff(
                gamma**2 * monomial,
                v if component == 0 else t,
            )
            columns.append((
                sp.expand(image[0]),
                sp.expand(image[1]),
                sp.expand(weighted_divergence),
                sp.Integer(0),
            ))
            metadata.append({
                "kind": "source",
                "component": component,
                "i": i,
                "j": j,
                "degree": i + j,
            })
    source_column_count = len(columns)
    for hamiltonian, field in target_fields:
        at = _substitute(field, p, q, p0, q0)
        columns.append((
            at[0], at[1], sp.Integer(0), sp.Integer(0)
        ))
        metadata.append({
            "kind": "target",
            "hamiltonian": hamiltonian,
        })

    matrix, rhs, _row_keys = _coefficient_system(
        columns,
        (
            residual[0],
            residual[1],
            sp.Integer(0),
            sp.Integer(0),
        ),
        v,
        t,
    )
    cap_checks: dict[str, dict[str, object]] = {}
    selected_indices: list[int] | None = None
    selected_matrix: DomainMatrix | None = None
    for cap in range(3, 10):
        indices = [
            index
            for index, item in enumerate(metadata)
            if (
                item["kind"] == "target"
                or int(item["degree"]) <= cap
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
        cap_checks[str(cap)] = {
            "column_count": len(indices),
            "rank": rank,
            "augmented_rank": augmented_rank,
            "consistent": consistent,
        }
        if consistent and selected_indices is None:
            selected_indices = indices
            selected_matrix = selected
    assert selected_indices is not None
    assert selected_matrix is not None
    assert cap_checks["5"]["consistent"] is False
    assert cap_checks["6"]["consistent"] is True

    full_rank = matrix.rank()
    full_augmented_rank = DomainMatrix.hstack(
        matrix, rhs
    ).rank()
    assert matrix.shape == (274, 119)
    assert full_rank == full_augmented_rank == 113
    assert source_column_count == 107
    assert len(target_fields) == 12

    solution = _particular_solution(selected_matrix, rhs)
    velocity = [sp.Integer(0), sp.Integer(0)]
    target_hamiltonian = sp.Integer(0)
    for coefficient, index in zip(
        solution, selected_indices, strict=True
    ):
        item = metadata[index]
        if item["kind"] == "source":
            velocity[int(item["component"])] += (
                coefficient
                * v ** int(item["i"])
                * t ** int(item["j"])
            )
        else:
            target_hamiltonian += (
                coefficient * item["hamiltonian"]
            )
    velocity3: Pair = (
        sp.expand(velocity[0]),
        sp.expand(velocity[1]),
    )
    target_hamiltonian = sp.expand(target_hamiltonian)
    assert [
        _degree(component, v, t) for component in velocity3
    ] == [6, 6]
    weighted_divergence = sp.expand(
        sp.diff(gamma**2 * velocity3[0], v)
        + sp.diff(gamma**2 * velocity3[1], t)
    )
    assert weighted_divergence == 0

    target_at = _substitute(
        _hamiltonian_field(
            target_hamiltonian, p, q
        ),
        p,
        q,
        p0,
        q0,
    )
    source_at = seed_jacobian * sp.Matrix(velocity3)
    assert all(
        sp.expand(
            target_at[index]
            + source_at[index]
            - residual[index]
        )
        == 0
        for index in range(2)
    )

    # The source velocity starts at s*V1.  Therefore the fourth direct-map
    # derivative is V3+3 DV1.V1; applying it to x gives the desired U4.
    velocity1_x = _act(velocity1, x, v, t)
    direct_u4 = sp.expand(
        _act(velocity3, x, v, t)
        + 3 * _act(velocity1, velocity1_x, v, t)
    )
    cusp_u4 = _pade_jet(4, x, gamma)
    expected_cusp_u4 = -(
        243 * gamma**2 * x
        + 729 * gamma**2
        + 72 * gamma * x**3
        - 378 * gamma * x**2
        + 108 * gamma * x
        - 1710 * gamma
        + 5 * x**5
        - 56 * x**4
        + 85 * x**3
        + 98 * x**2
        + 277 * x
        + 325
    ) / 34992
    assert sp.expand(cusp_u4 - expected_cusp_u4) == 0
    correction_numerator = sp.expand(direct_u4 - cusp_u4)
    exceptional_value = sp.expand(
        correction_numerator.subs(
            t, sp.Rational(3, 2) * v - 1
        )
    )
    assert exceptional_value == 0
    correction_a4 = sp.factor(
        sp.cancel(correction_numerator / gamma)
    )
    assert sp.denom(correction_a4).is_number
    assert _degree(correction_a4, v, t) == 9
    assert sp.expand(
        cusp_u4 + gamma * correction_a4 - direct_u4
    ) == 0

    target_normal_form = _c_normal_form(
        target_hamiltonian, p, q
    )
    c = sp.Symbol("C")
    assert sp.Poly(
        target_normal_form, q, domain=sp.QQ.poly_ring(p, c)
    ).degree() <= 1

    return {
        "schema": (
            "axiompack.jacobian_cusp_generator_order_four_replay.v1"
        ),
        "recursion": {
            "form": "linear_instantaneous_Rees_velocity",
            "residual_component_degrees": residual_degrees,
        },
        "complete_window": {
            "matrix_shape": list(matrix.shape),
            "source_column_count": source_column_count,
            "source_degree_cap": 9,
            "target_C_normal_component_window": [12, 14],
            "target_field_dimension": len(target_fields),
            "first_normal_basis_dimension": len(first_normal_basis),
            "second_normal_basis_dimension": len(second_normal_basis),
            "rank": full_rank,
            "augmented_rank": full_augmented_rank,
            "nullity": matrix.shape[1] - full_rank,
            "source_cap_checks": cap_checks,
        },
        "velocity_solution": {
            "minimum_source_degree": 6,
            "component_degrees": [
                _degree(component, v, t)
                for component in velocity3
            ],
            "components": [
                str(component) for component in velocity3
            ],
            "weighted_divergence": str(weighted_divergence),
            "target_hamiltonian": str(target_hamiltonian),
            "target_C_normal_form": str(target_normal_form),
            "contact_replay": True,
        },
        "pade_correction": {
            "cusp_U4": str(sp.factor(cusp_u4)),
            "direct_map_cross_term": "3*V1(V1(x))",
            "critical_curve_difference": str(exceptional_value),
            "A4_degree": _degree(correction_a4, v, t),
            "corrected_U4_equals_direct_source_x": True,
        },
        "claim_boundary": (
            "orders one through four pass; the target Hamiltonian reduces "
            "to the fixed C-normal rank-two scalar module, but an "
            "all-order vanishing theorem for the inverse-cubic descent "
            "obstruction remains open"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
