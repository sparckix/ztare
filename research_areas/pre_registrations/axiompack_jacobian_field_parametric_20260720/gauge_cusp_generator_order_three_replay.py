#!/usr/bin/env python3
"""Solve the corrected cusp contact at order three in Rees velocity form."""
from __future__ import annotations

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
    _coefficient_system,
    _hamiltonian_field,
    _hamiltonian_field_window,
    _monomials,
    _particular_solution,
    _substitute,
    run as run_third,
)


Pair = tuple[sp.Expr, sp.Expr]


def _degree(
    value: sp.Expr, v: sp.Symbol, t: sp.Symbol
) -> int:
    if value == 0:
        return -1
    return int(
        sp.Poly(value, v, t, domain=sp.QQ).total_degree()
    )


def _pade_jet(
    order: int,
    x: sp.Expr,
    gamma: sp.Expr,
) -> sp.Expr:
    """Return the derivative-normalized projective Padé coefficient."""

    s, y = sp.symbols("s y")
    if order < 1:
        raise ValueError("the positive Padé coefficient is required")
    d = sp.sqrt(3 * s**2 + 12 * s + 36)
    alpha = (s + 6 - d) / (2 * s)
    xi = y - alpha
    exact_phi = (
        xi
        * sp.sqrt(d / 6)
        * sp.sqrt(1 - 2 * s * xi / (3 * d))
    )
    phi_series = sp.series(
        exact_phi, s, 0, order + 1
    ).removeO().expand()
    phi = [
        sp.expand(phi_series.coeff(s, index))
        for index in range(order + 1)
    ]
    endpoint_a = [
        component.subs(y, -1) for component in phi
    ]
    endpoint_b = [
        component.subs(y, 2) for component in phi
    ]
    phi_polynomial = sum(
        s**index * component
        for index, component in enumerate(phi)
    )
    endpoint_a_polynomial = sum(
        s**index * component
        for index, component in enumerate(endpoint_a)
    )
    endpoint_b_polynomial = sum(
        s**index * component
        for index, component in enumerate(endpoint_b)
    )
    kappa_polynomial = sp.series(
        (1 - s / 6)
        * (endpoint_b_polynomial - endpoint_a_polynomial)
        / (
            3
            * sp.diff(phi_polynomial, y).subs(y, 2)
        ),
        s,
        0,
        order + 1,
    ).removeO().expand()
    kappa = [
        sp.expand(kappa_polynomial.coeff(s, index))
        for index in range(order + 1)
    ]

    def multiply(
        left: list[sp.Expr], right: list[sp.Expr]
    ) -> list[sp.Expr]:
        return [
            sp.expand(sum(
                left[index] * right[degree - index]
                for index in range(degree + 1)
            ))
            for degree in range(order + 1)
        ]

    eta_minus_a = [
        sp.expand(phi[order] - endpoint_a[order])
        for order in range(order + 1)
    ]
    eta_minus_b = [
        sp.expand(phi[order] - endpoint_b[order])
        for order in range(order + 1)
    ]
    kappa_eta_minus_b = multiply(kappa, eta_minus_b)
    numerator = [
        sp.expand(
            2 * eta_minus_a[order]
            + kappa_eta_minus_b[order]
        )
        for order in range(order + 1)
    ]
    denominator = [
        sp.expand(
            eta_minus_a[order]
            - kappa_eta_minus_b[order]
        )
        for order in range(order + 1)
    ]
    projective: list[sp.Expr] = []
    for degree in range(order + 1):
        projective.append(sp.factor(
            (
                numerator[degree]
                - sum(
                    denominator[index]
                    * projective[degree - index]
                    for index in range(1, degree + 1)
                )
            )
            / denominator[0]
        ))
    assert sp.expand(projective[0] - y) == 0
    if order >= 1:
        assert sp.expand(
            projective[1] + (y - 2) * (y + 1) / 18
        ) == 0
    if order >= 2:
        assert sp.expand(
            projective[2]
            + (y - 2) ** 2 * (y + 1) / 648
        ) == 0
    if order >= 3:
        assert sp.expand(
            projective[3]
            + (y - 4) * (y - 2) ** 2 * (y + 1)
            / 11664
        ) == 0

    delta1 = gamma / 4 - (x + 1) / 12
    family_x_series = (
        x
        + sum(
            s**degree * delta1 / 6 ** (degree - 1)
            for degree in range(1, order + 1)
        )
    )
    composed = sp.expand(sum(
        s**degree
        * projective[degree].subs(y, family_x_series)
        for degree in range(order + 1)
    ))
    ordinary_coefficient = sp.expand(composed).coeff(s, order)
    return sp.factor(
        sp.factorial(order) * ordinary_coefficient
    )


def run() -> dict[str, object]:
    v, t, p, q = sp.symbols("v t P Q")
    gamma = 1 - sp.Rational(3, 2) * v + t
    x = 3 * (1 + v) * gamma - 1

    # Only the already-settled lower coefficient is carried.  Y3 from the
    # logarithmic prefix is deliberately not read.
    prefix = run_third(
        maximum_source_degree=5,
        maximum_third_hamiltonian_degree=4,
    )
    lower = prefix["witness"]
    y2 = sp.Matrix([
        sp.sympify(component, locals={"v": v, "t": t})
        for component in lower["Y2"]
    ])
    k2 = sp.sympify(
        lower["K2"], locals={"P": p, "Q": q}
    )

    data = _family_jets(3)
    p0, q0 = data["P"][0], data["Q"][0]
    family1 = sp.Matrix([data["P"][1], data["Q"][1]])
    family2 = sp.Matrix([data["P"][2], data["Q"][2]])
    family3 = sp.Matrix([data["P"][3], data["Q"][3]])
    seed_jacobian = sp.Matrix([p0, q0]).jacobian([v, t])

    x1 = sp.Matrix([-q / 2, p**2 / 12])
    x2 = sp.Matrix(_hamiltonian_field(k2, p, q))
    at_seed = {p: p0, q: q0}
    dx1 = x1.jacobian([p, q]).subs(at_seed)
    dx2 = x2.jacobian([p, q]).subs(at_seed)
    d2x1 = sp.Matrix([
        sp.expand(
            (
                family1.T
                * sp.hessian(x1[component], (p, q)).subs(
                    at_seed
                )
                * family1
            )[0]
        )
        for component in range(2)
    ])
    known_third = (
        2 * dx2 * family1
        + d2x1
        + dx1 * family2
        + 2 * family1.jacobian([v, t]) * y2
    )
    residual = tuple(
        sp.expand(family3[index] - known_third[index])
        for index in range(2)
    )
    residual_degrees = [
        _degree(component, v, t) for component in residual
    ]
    assert residual_degrees == [10, 12]

    target_fields, first_normal_basis, second_normal_basis = (
        _hamiltonian_field_window(10, 12, p, q)
    )
    columns: list[tuple[sp.Expr, sp.Expr, sp.Expr, sp.Expr]] = []
    metadata: list[dict[str, object]] = []
    for component in range(2):
        forbidden = (
            {(0, 0)}
            if component == 0
            else {(0, 0), (1, 0)}
        )
        for i, j in _monomials(7):
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
    for cap in range(2, 8):
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
    assert cap_checks["4"]["consistent"] is False
    assert cap_checks["5"]["consistent"] is True

    full_rank = matrix.rank()
    full_augmented_rank = DomainMatrix.hstack(
        matrix, rhs
    ).rank()
    assert full_rank == full_augmented_rank == 75
    assert matrix.shape == (199, 78)
    assert source_column_count == 69
    assert len(target_fields) == 9

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
    velocity_pair: Pair = (
        sp.expand(velocity[0]),
        sp.expand(velocity[1]),
    )
    target_hamiltonian = sp.expand(target_hamiltonian)
    assert [
        _degree(component, v, t)
        for component in velocity_pair
    ] == [5, 5]

    weighted_divergence = sp.expand(
        sp.diff(gamma**2 * velocity_pair[0], v)
        + sp.diff(gamma**2 * velocity_pair[1], t)
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
    source_at = seed_jacobian * sp.Matrix(velocity_pair)
    assert all(
        sp.expand(
            target_at[index]
            + source_at[index]
            - residual[index]
        )
        == 0
        for index in range(2)
    )

    cusp_u3 = _pade_jet(3, x, gamma)
    expected_cusp_u3 = -(
        81 * gamma**2
        + 27 * gamma * x**2
        - 270 * gamma
        + 2 * x**4
        - 23 * x**3
        + 6 * x**2
        + 80 * x
        + 49
    ) / 3888
    assert sp.expand(cusp_u3 - expected_cusp_u3) == 0
    velocity_x = sp.expand(
        velocity_pair[0] * sp.diff(x, v)
        + velocity_pair[1] * sp.diff(x, t)
    )
    correction_numerator = sp.expand(velocity_x - cusp_u3)
    exceptional_value = sp.expand(
        correction_numerator.subs(
            t, sp.Rational(3, 2) * v - 1
        )
    )
    assert exceptional_value == 0
    correction_a3 = sp.factor(
        sp.cancel(correction_numerator / gamma)
    )
    assert sp.denom(correction_a3).is_number
    assert _degree(correction_a3, v, t) == 7
    assert sp.expand(
        cusp_u3
        + gamma * correction_a3
        - velocity_x
    ) == 0

    velocity_gamma = sp.expand(
        -sp.Rational(3, 2) * velocity_pair[0]
        + velocity_pair[1]
    )
    r3 = sp.expand(gamma * velocity_gamma)
    recovered_v = sp.cancel(
        velocity_x / (3 * gamma)
        - (1 + v) * velocity_gamma / gamma
    )
    recovered_t = sp.cancel(
        velocity_gamma
        + sp.Rational(3, 2) * recovered_v
    )
    assert sp.expand(recovered_v - velocity_pair[0]) == 0
    assert sp.expand(recovered_t - velocity_pair[1]) == 0

    return {
        "schema": (
            "axiompack.jacobian_cusp_generator_order_three_replay.v1"
        ),
        "recursion": {
            "form": "linear_instantaneous_Rees_velocity",
            "uses_carried_logarithmic_Y3": False,
            "residual_component_degrees": residual_degrees,
        },
        "complete_window": {
            "matrix_shape": list(matrix.shape),
            "source_column_count": source_column_count,
            "source_degree_cap": 7,
            "target_C_normal_component_window": [10, 12],
            "target_field_dimension": len(target_fields),
            "first_normal_basis_dimension": len(first_normal_basis),
            "second_normal_basis_dimension": len(second_normal_basis),
            "rank": full_rank,
            "augmented_rank": full_augmented_rank,
            "nullity": matrix.shape[1] - full_rank,
            "source_cap_checks": cap_checks,
        },
        "velocity_solution": {
            "minimum_source_degree": 5,
            "component_degrees": [
                _degree(component, v, t)
                for component in velocity_pair
            ],
            "components": [
                str(component) for component in velocity_pair
            ],
            "weighted_divergence": str(weighted_divergence),
            "target_hamiltonian": str(target_hamiltonian),
            "contact_replay": True,
        },
        "pade_correction": {
            "cusp_U3": str(sp.factor(cusp_u3)),
            "critical_curve_difference": str(exceptional_value),
            "A3": str(correction_a3),
            "A3_degree": _degree(correction_a3, v, t),
            "corrected_U3_equals_velocity_x": True,
            "R3": str(sp.factor(r3)),
            "recovers_velocity": True,
        },
        "claim_boundary": (
            "orders one through three pass; the generic lift identity "
            "settles gamma divisibility and weighted area conditionally "
            "on a shifted-Rees velocity, while arbitrary-order polynomial "
            "target descent remains open"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
