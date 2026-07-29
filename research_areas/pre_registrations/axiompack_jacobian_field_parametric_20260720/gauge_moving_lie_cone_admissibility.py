#!/usr/bin/env python3
"""Exact moving-contact test for the minimum-section Hamiltonian cone.

The replay reuses the complete C-normal target windows and source lift
columns from the existing gauge-minimized contact solvers.  Its only new
linear-algebra operation restricts a polynomial span by a monomial-support
predicate; this is needed because filtering basis vectors separately would
miss cancellations between C-normal representatives.

All parameter coefficients use the derivative-normalized instantaneous
equation

    dF_s/ds = X_{K_s}(F_s) + dF_s V_s.

The constrained branch requires every nonconstant monomial P^a Q^b of K_j
to have b >= 1 and a <= 2*b.  Rescaling P=-3X, Q=-2Y does not change these
exponents.  Both constrained and unrestricted controls retain the target
and source lift conditions and weighted source divergence.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Callable
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
)


Pair = tuple[sp.Expr, sp.Expr]
Exponent = tuple[int, int]


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(
        str(sp.expand(value)).encode("utf-8")
    ).hexdigest()


def _degree(
    value: sp.Expr,
    first: sp.Symbol,
    second: sp.Symbol,
) -> int:
    if sp.expand(value) == 0:
        return -1
    return int(
        sp.Poly(value, first, second, domain=sp.QQ).total_degree()
    )


def _minimum_cone_support(exponent: Exponent) -> bool:
    """The constant or a monomial in b>=1, a<=2b."""

    a, b = exponent
    return exponent == (0, 0) or (1 <= b and a <= 2 * b)


def _target_lift_support(exponent: Exponent) -> bool:
    """Hamiltonian monomials compatible with the quotient target lift.

    For X_K=(K_Q,-K_P), liftability excludes Q, P, and P^2.  Higher
    P-only monomials are allowed in the unrestricted control.
    """

    return exponent not in {(0, 1), (1, 0), (2, 0)}


def _restrict_polynomial_span(
    expressions: list[sp.Expr],
    first: sp.Symbol,
    second: sp.Symbol,
    allowed: Callable[[Exponent], bool],
) -> tuple[list[sp.Expr], list[Exponent], int]:
    """Return the complete subspace having only allowed monomial support."""

    polynomials = [
        sp.Poly(sp.expand(value), first, second, domain=sp.QQ)
        for value in expressions
    ]
    removed = sorted({
        exponent
        for polynomial in polynomials
        for exponent in polynomial.monoms()
        if not allowed(exponent)
    })
    constraint = sp.Matrix([
        [
            polynomial.coeff_monomial(exponent)
            for polynomial in polynomials
        ]
        for exponent in removed
    ])
    directions = (
        constraint.nullspace()
        if removed
        else [
            sp.eye(len(expressions))[:, index]
            for index in range(len(expressions))
        ]
    )
    restricted = [
        sp.expand(sum(
            coefficient * expression
            for coefficient, expression in zip(
                direction, expressions, strict=True
            )
        ))
        for direction in directions
    ]
    assert all(
        allowed(exponent)
        for value in restricted
        for exponent in sp.Poly(value, first, second).monoms()
    )
    return restricted, removed, constraint.rank()


def _target_basis(
    first_component_degree: int,
    second_component_degree: int,
    p: sp.Symbol,
    q: sp.Symbol,
    *,
    cone_restricted: bool,
) -> tuple[list[tuple[sp.Expr, Pair]], dict[str, object]]:
    raw, first_scalars, second_scalars = _hamiltonian_field_window(
        first_component_degree,
        second_component_degree,
        p,
        q,
    )
    raw_hamiltonians = [sp.expand(item[0]) for item in raw]

    def allowed(exponent: Exponent) -> bool:
        return (
            _target_lift_support(exponent)
            and (
                not cone_restricted
                or _minimum_cone_support(exponent)
            )
        )

    hamiltonians, removed, restriction_rank = (
        _restrict_polynomial_span(
            raw_hamiltonians, p, q, allowed
        )
    )
    result = [
        (hamiltonian, _hamiltonian_field(hamiltonian, p, q))
        for hamiltonian in hamiltonians
    ]
    support_removed = sorted({
        exponent
        for value in raw_hamiltonians
        for exponent in sp.Poly(value, p, q).monoms()
        if not _minimum_cone_support(exponent)
    })
    lift_removed = sorted({
        exponent
        for value in raw_hamiltonians
        for exponent in sp.Poly(value, p, q).monoms()
        if not _target_lift_support(exponent)
    })
    return result, {
        "component_degree_window": [
            first_component_degree,
            second_component_degree,
        ],
        "raw_target_field_dimension": len(raw),
        "restricted_target_field_dimension": len(result),
        "restriction_rank": restriction_rank,
        "removed_monomials": [list(item) for item in removed],
        "cone_forbidden_monomials_present": [
            list(item) for item in support_removed
        ],
        "target_lift_forbidden_monomials_present": [
            list(item) for item in lift_removed
        ],
        "first_C_normal_scalar_basis_dimension": len(first_scalars),
        "second_C_normal_scalar_basis_dimension": len(second_scalars),
    }


def _strict_source_lift(
    field: Pair,
    v: sp.Symbol,
    t: sp.Symbol,
) -> bool:
    first = sp.Poly(sp.expand(field[0]), v, t, domain=sp.QQ)
    second = sp.Poly(sp.expand(field[1]), v, t, domain=sp.QQ)
    return bool(
        first.coeff_monomial(1) == 0
        and second.coeff_monomial(1) == 0
        and second.coeff_monomial(v) == 0
    )


def _target_lift(
    hamiltonian: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> bool:
    field = _hamiltonian_field(hamiltonian, p, q)
    first = sp.Poly(sp.expand(field[0]), p, q, domain=sp.QQ)
    second = sp.Poly(sp.expand(field[1]), p, q, domain=sp.QQ)
    return bool(
        first.coeff_monomial(1) == 0
        and second.coeff_monomial(1) == 0
        and second.coeff_monomial(p) == 0
    )


def _instantaneous_residual(
    order: int,
    hamiltonians: dict[int, sp.Expr],
    source_fields: dict[int, Pair],
    data: dict[str, object],
    p: sp.Symbol,
    q: sp.Symbol,
    v: sp.Symbol,
    t: sp.Symbol,
    s: sp.Symbol,
) -> Pair:
    p_series = sp.expand(sum(
        data["P"][index] * s**index / sp.factorial(index)
        for index in range(order + 2)
    ))
    q_series = sp.expand(sum(
        data["Q"][index] * s**index / sp.factorial(index)
        for index in range(order + 2)
    ))
    target = sp.zeros(2, 1)
    for field_order, hamiltonian in hamiltonians.items():
        field = _hamiltonian_field(hamiltonian, p, q)
        target += (
            s**field_order
            / sp.factorial(field_order)
            * sp.Matrix([
                sp.expand(component.subs(
                    {p: p_series, q: q_series},
                    simultaneous=True,
                ))
                for component in field
            ])
        )
    source_series = sp.zeros(2, 1)
    for field_order, field in source_fields.items():
        source_series += (
            s**field_order
            / sp.factorial(field_order)
            * sp.Matrix(field)
        )
    source = (
        sp.Matrix([p_series, q_series]).jacobian([v, t])
        * source_series
    )
    known = sp.expand(target + source)
    residual = tuple(
        sp.expand(
            data[coordinate][order + 1]
            - sp.factorial(order)
            * known[component].coeff(s, order)
        )
        for component, coordinate in enumerate(("P", "Q"))
    )
    assert all(
        not ({v, t} & sp.denom(item).free_symbols)
        for item in residual
    )
    return residual  # type: ignore[return-value]


def _build_system(
    residual: Pair,
    source_degree_cap: int,
    target_basis: list[tuple[sp.Expr, Pair]],
    p0: sp.Expr,
    q0: sp.Expr,
    jacobian: sp.Matrix,
    gamma: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
    v: sp.Symbol,
    t: sp.Symbol,
) -> tuple[
    DomainMatrix,
    DomainMatrix,
    list[dict[str, object]],
    int,
]:
    columns: list[tuple[sp.Expr, sp.Expr, sp.Expr, sp.Expr]] = []
    metadata: list[dict[str, object]] = []
    for component in range(2):
        forbidden = (
            {(0, 0)}
            if component == 0
            else {(0, 0), (1, 0)}
        )
        for first_power, second_power in _monomials(
            source_degree_cap
        ):
            if (first_power, second_power) in forbidden:
                continue
            monomial = v**first_power * t**second_power
            image = jacobian[:, component] * monomial
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
                "first_power": first_power,
                "second_power": second_power,
            })
    source_column_count = len(columns)
    for hamiltonian, field in target_basis:
        at_seed = _substitute(field, p, q, p0, q0)
        columns.append((
            at_seed[0],
            at_seed[1],
            sp.Integer(0),
            sp.Integer(0),
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
    return matrix, rhs, metadata, source_column_count


def _decode(
    vector: sp.Matrix,
    metadata: list[dict[str, object]],
    v: sp.Symbol,
    t: sp.Symbol,
) -> tuple[sp.Expr, Pair]:
    hamiltonian = sp.Integer(0)
    source = [sp.Integer(0), sp.Integer(0)]
    for coefficient, item in zip(vector, metadata, strict=True):
        if item["kind"] == "target":
            hamiltonian += coefficient * item["hamiltonian"]
        else:
            source[int(item["component"])] += (
                coefficient
                * v ** int(item["first_power"])
                * t ** int(item["second_power"])
            )
    return (
        sp.expand(hamiltonian),
        (sp.expand(source[0]), sp.expand(source[1])),
    )


def _target_record(
    hamiltonian: sp.Expr,
    order: int,
    p: sp.Symbol,
    q: sp.Symbol,
    x: sp.Symbol,
    y: sp.Symbol,
) -> dict[str, object]:
    normalized = sp.expand(
        hamiltonian.subs({p: -3 * x, q: -2 * y})
    )
    support = sorted(
        sp.Poly(normalized, x, y, domain=sp.QQ).monoms()
    )
    nonconstant = [
        exponent for exponent in support if exponent != (0, 0)
    ]
    weights = [
        2 * first_power + 3 * second_power
        for first_power, second_power in nonconstant
    ]
    assert all(_minimum_cone_support(item) for item in support)
    assert not weights or max(weights) <= order + 6
    field = _hamiltonian_field(hamiltonian, p, q)
    return {
        "hamiltonian_PQ": str(hamiltonian),
        "hamiltonian_XY": str(normalized),
        "support_XY": [list(item) for item in support],
        "ordinary_degree": _degree(normalized, x, y),
        "maximum_cusp_weight": max(weights, default=0),
        "natural_weight_bound": order + 6,
        "field_component_degrees": [
            _degree(component, p, q) for component in field
        ],
        "target_lift": _target_lift(hamiltonian, p, q),
        "sha256": _sha(hamiltonian),
    }


def _solve_branch(
    *,
    cone_restricted: bool,
    data: dict[str, object],
    p: sp.Symbol,
    q: sp.Symbol,
    v: sp.Symbol,
    t: sp.Symbol,
    s: sp.Symbol,
    x: sp.Symbol,
    y: sp.Symbol,
) -> tuple[
    dict[str, object],
    dict[int, sp.Expr],
    dict[int, Pair],
    dict[str, object] | None,
]:
    p0, q0 = data["P"][0], data["Q"][0]
    gamma = data["gamma"]
    jacobian = sp.Matrix([p0, q0]).jacobian([v, t])
    maximum_source_caps = [5, 5, 7, 9]
    target_windows = [(8, 10), (8, 10), (10, 12), (12, 14)]
    hamiltonians: dict[int, sp.Expr] = {}
    source_fields: dict[int, Pair] = {}
    order_records: list[dict[str, object]] = []
    order_two_direction: tuple[sp.Expr, Pair] | None = None

    for order, (maximum_cap, window) in enumerate(zip(
        maximum_source_caps, target_windows, strict=True
    )):
        residual = _instantaneous_residual(
            order,
            hamiltonians,
            source_fields,
            data,
            p,
            q,
            v,
            t,
            s,
        )
        target_basis, target_window_record = _target_basis(
            window[0],
            window[1],
            p,
            q,
            cone_restricted=cone_restricted,
        )
        cap_checks: dict[str, dict[str, object]] = {}
        first_consistent: tuple[
            int,
            DomainMatrix,
            DomainMatrix,
            list[dict[str, object]],
            int,
        ] | None = None
        for cap in range(maximum_cap + 1):
            matrix, rhs, metadata, source_count = _build_system(
                residual,
                cap,
                target_basis,
                p0,
                q0,
                jacobian,
                gamma,
                p,
                q,
                v,
                t,
            )
            rank = matrix.rank()
            augmented_rank = DomainMatrix.hstack(
                matrix, rhs
            ).rank()
            cap_checks[str(cap)] = {
                "matrix_shape": list(matrix.shape),
                "source_column_count": source_count,
                "target_column_count": len(target_basis),
                "rank": rank,
                "augmented_rank": augmented_rank,
                "nullity": matrix.shape[1] - rank,
                "consistent": rank == augmented_rank,
            }
            if rank == augmented_rank and first_consistent is None:
                first_consistent = (
                    cap, matrix, rhs, metadata, source_count
                )
        if first_consistent is None:
            return ({
                "cone_restricted": cone_restricted,
                "completed_through_family_derivative": order,
                "first_inconsistent_instantaneous_order": order,
                "orders": order_records,
                "failed_cap_checks": cap_checks,
            }, hamiltonians, source_fields, None)

        cap, matrix, rhs, metadata, source_count = first_consistent
        solution = _particular_solution(matrix, rhs)
        hamiltonian, source = _decode(
            solution, metadata, v, t
        )
        weighted_divergence = sp.expand(
            sp.diff(gamma**2 * source[0], v)
            + sp.diff(gamma**2 * source[1], t)
        )
        assert weighted_divergence == 0
        assert _strict_source_lift(source, v, t)
        assert _target_lift(hamiltonian, p, q)
        target_at_seed = _substitute(
            _hamiltonian_field(hamiltonian, p, q),
            p,
            q,
            p0,
            q0,
        )
        source_at_seed = jacobian * sp.Matrix(source)
        assert all(
            sp.expand(
                target_at_seed[index]
                + source_at_seed[index]
                - residual[index]
            ) == 0
            for index in range(2)
        )
        hamiltonians[order] = hamiltonian
        source_fields[order] = source

        nullspace = matrix.to_Matrix().nullspace()
        if cone_restricted and order == 2:
            assert len(nullspace) == 1
            order_two_direction = _decode(
                nullspace[0], metadata, v, t
            )

        if cone_restricted:
            target = _target_record(
                hamiltonian, order, p, q, x, y
            )
        else:
            # The unrestricted control may contain P-only support.
            normalized = sp.expand(
                hamiltonian.subs({p: -3 * x, q: -2 * y})
            )
            support = sorted(
                sp.Poly(normalized, x, y, domain=sp.QQ).monoms()
            )
            target = {
                "hamiltonian_PQ": str(hamiltonian),
                "hamiltonian_XY": str(normalized),
                "support_XY": [list(item) for item in support],
                "ordinary_degree": _degree(normalized, x, y),
                "field_component_degrees": [
                    _degree(component, p, q)
                    for component in _hamiltonian_field(
                        hamiltonian, p, q
                    )
                ],
                "target_lift": _target_lift(
                    hamiltonian, p, q
                ),
                "sha256": _sha(hamiltonian),
            }
        order_records.append({
            "instantaneous_order": order,
            "family_derivative_solved": order + 1,
            "residual_component_degrees": [
                _degree(component, v, t)
                for component in residual
            ],
            "target_window": target_window_record,
            "source_cap_checks": cap_checks,
            "minimum_source_degree_for_carried_prefix": cap,
            "selected_system": {
                "matrix_shape": list(matrix.shape),
                "source_column_count": source_count,
                "target_column_count": len(target_basis),
                "rank": matrix.rank(),
                "augmented_rank": DomainMatrix.hstack(
                    matrix, rhs
                ).rank(),
                "nullity": len(nullspace),
            },
            "target": target,
            "source": {
                "component_degrees": [
                    _degree(component, v, t)
                    for component in source
                ],
                "weighted_divergence": str(weighted_divergence),
                "strict_source_lift": True,
                "component_sha256": [
                    _sha(component) for component in source
                ],
            },
            "instantaneous_equation_replay": True,
        })

    lower_direction_control: dict[str, object] | None = None
    if cone_restricted:
        assert order_two_direction is not None
        direction_hamiltonian, direction_source = order_two_direction
        lower_direction_control = _lower_direction_control(
            hamiltonians,
            source_fields,
            direction_hamiltonian,
            direction_source,
            data,
            p,
            q,
            v,
            t,
            s,
        )

    _replay_complete_prefix(
        hamiltonians,
        source_fields,
        data,
        p,
        q,
        v,
        t,
        s,
    )
    return ({
        "cone_restricted": cone_restricted,
        "completed_through_family_derivative": 4,
        "orders": order_records,
        "full_instantaneous_prefix_replay": True,
    }, hamiltonians, source_fields, lower_direction_control)


def _lower_direction_control(
    hamiltonians: dict[int, sp.Expr],
    source_fields: dict[int, Pair],
    direction_hamiltonian: sp.Expr,
    direction_source: Pair,
    data: dict[str, object],
    p: sp.Symbol,
    q: sp.Symbol,
    v: sp.Symbol,
    t: sp.Symbol,
    s: sp.Symbol,
) -> dict[str, object]:
    """Retain the full order-two affine line in the order-three test."""

    parameter = sp.Symbol("lambda")
    varied_hamiltonians = dict(hamiltonians)
    varied_sources = dict(source_fields)
    varied_hamiltonians.pop(3, None)
    varied_sources.pop(3, None)
    varied_hamiltonians[2] = sp.expand(
        hamiltonians[2] + parameter * direction_hamiltonian
    )
    varied_sources[2] = tuple(
        sp.expand(
            source_fields[2][index]
            + parameter * direction_source[index]
        )
        for index in range(2)
    )  # type: ignore[assignment]
    symbolic_residual = _instantaneous_residual(
        3,
        varied_hamiltonians,
        varied_sources,
        data,
        p,
        q,
        v,
        t,
        s,
    )
    assert all(
        sp.Poly(item, parameter).degree() <= 1
        for item in symbolic_residual
    )
    residual_zero = tuple(
        sp.expand(item.subs(parameter, 0))
        for item in symbolic_residual
    )
    residual_direction = tuple(
        sp.expand(sp.diff(item, parameter))
        for item in symbolic_residual
    )
    p0, q0 = data["P"][0], data["Q"][0]
    gamma = data["gamma"]
    jacobian = sp.Matrix([p0, q0]).jacobian([v, t])
    target_basis, _record = _target_basis(
        12, 14, p, q, cone_restricted=True
    )
    cap_checks: dict[str, dict[str, object]] = {}
    first_solution: tuple[int, sp.Expr] | None = None
    for cap in range(10):
        matrix, _rhs, metadata, source_count = _build_system(
            residual_zero,
            cap,
            target_basis,
            p0,
            q0,
            jacobian,
            gamma,
            p,
            q,
            v,
            t,
        )
        # Rebuild with the lower affine direction as an extra exact column.
        # The equation image = r0 + lambda*r1 becomes
        # image - lambda*r1 = r0.
        columns: list[
            tuple[sp.Expr, sp.Expr, sp.Expr, sp.Expr]
        ] = []
        metadata_with_parameter: list[dict[str, object]] = []
        for component in range(2):
            forbidden = (
                {(0, 0)}
                if component == 0
                else {(0, 0), (1, 0)}
            )
            for first_power, second_power in _monomials(cap):
                if (first_power, second_power) in forbidden:
                    continue
                monomial = v**first_power * t**second_power
                image = jacobian[:, component] * monomial
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
                metadata_with_parameter.append({
                    "kind": "source",
                    "component": component,
                    "first_power": first_power,
                    "second_power": second_power,
                })
        for hamiltonian, field in target_basis:
            at_seed = _substitute(field, p, q, p0, q0)
            columns.append((
                at_seed[0],
                at_seed[1],
                sp.Integer(0),
                sp.Integer(0),
            ))
            metadata_with_parameter.append({
                "kind": "target",
                "hamiltonian": hamiltonian,
            })
        columns.append((
            -residual_direction[0],
            -residual_direction[1],
            sp.Integer(0),
            sp.Integer(0),
        ))
        metadata_with_parameter.append({"kind": "lower_parameter"})
        joint, rhs, _row_keys = _coefficient_system(
            columns,
            (
                residual_zero[0],
                residual_zero[1],
                sp.Integer(0),
                sp.Integer(0),
            ),
            v,
            t,
        )
        rank = joint.rank()
        augmented_rank = DomainMatrix.hstack(
            joint, rhs
        ).rank()
        cap_checks[str(cap)] = {
            "matrix_shape": list(joint.shape),
            "source_column_count": source_count,
            "target_column_count": len(target_basis),
            "lower_direction_column_count": 1,
            "rank": rank,
            "augmented_rank": augmented_rank,
            "consistent": rank == augmented_rank,
        }
        if rank == augmented_rank and first_solution is None:
            solution = _particular_solution(joint, rhs)
            first_solution = cap, sp.expand(solution[-1])
    assert first_solution is not None
    assert first_solution == (9, sp.Integer(0))
    return {
        "order_two_homogeneous_target_hamiltonian": str(
            direction_hamiltonian
        ),
        "order_two_homogeneous_source_degrees": [
            _degree(component, v, t)
            for component in direction_source
        ],
        "order_three_joint_cap_checks": cap_checks,
        "first_consistent_source_degree": first_solution[0],
        "forced_lower_parameter": str(first_solution[1]),
        "interpretation": (
            "the complete one-dimensional cone-valued order-two "
            "homogeneous freedom does not lower the order-three source "
            "cap; the first consistent joint solve is cap nine and it "
            "sets the carried parameter to zero"
        ),
    }


def _replay_complete_prefix(
    hamiltonians: dict[int, sp.Expr],
    source_fields: dict[int, Pair],
    data: dict[str, object],
    p: sp.Symbol,
    q: sp.Symbol,
    v: sp.Symbol,
    t: sp.Symbol,
    s: sp.Symbol,
) -> None:
    maximum_order = max(hamiltonians)
    p_series = sp.expand(sum(
        data["P"][index] * s**index / sp.factorial(index)
        for index in range(maximum_order + 2)
    ))
    q_series = sp.expand(sum(
        data["Q"][index] * s**index / sp.factorial(index)
        for index in range(maximum_order + 2)
    ))
    target = sp.zeros(2, 1)
    for order, hamiltonian in hamiltonians.items():
        field = _hamiltonian_field(hamiltonian, p, q)
        target += (
            s**order
            / sp.factorial(order)
            * sp.Matrix([
                component.subs(
                    {p: p_series, q: q_series},
                    simultaneous=True,
                )
                for component in field
            ])
        )
    source_series = sp.zeros(2, 1)
    for order, field in source_fields.items():
        source_series += (
            s**order / sp.factorial(order) * sp.Matrix(field)
        )
    right = sp.expand(
        target
        + sp.Matrix([p_series, q_series]).jacobian([v, t])
        * source_series
    )
    left = sp.Matrix([
        sp.diff(p_series, s),
        sp.diff(q_series, s),
    ])
    for order in range(maximum_order + 1):
        assert all(
            sp.expand(
                left[component].coeff(s, order)
                - right[component].coeff(s, order)
            ) == 0
            for component in range(2)
        )


def run() -> dict[str, object]:
    p, q, v, t, s, x, y = sp.symbols(
        "P Q v t s X Y"
    )
    data = _family_jets(4)
    cone, cone_hamiltonians, cone_sources, direction_control = (
        _solve_branch(
            cone_restricted=True,
            data=data,
            p=p,
            q=q,
            v=v,
            t=t,
            s=s,
            x=x,
            y=y,
        )
    )
    unrestricted, _control_hamiltonians, _control_sources, _unused = (
        _solve_branch(
            cone_restricted=False,
            data=data,
            p=p,
            q=q,
            v=v,
            t=t,
            s=s,
            x=x,
            y=y,
        )
    )
    assert cone["completed_through_family_derivative"] == 4
    assert unrestricted["completed_through_family_derivative"] == 4
    assert direction_control is not None

    base_hamiltonian = -q**2 / 4 - p**3 / 36
    moving_stabilizer = -(
        4 * p**3 - 18 * p * q + 27 * q**2
    ) / 12
    shift_amplitude = -sp.Rational(1, 12)
    assert sp.expand(
        base_hamiltonian
        + shift_amplitude * moving_stabilizer
        - cone_hamiltonians[0]
    ) == 0
    assert cone_hamiltonians[0] == -p * q / 8 - q**2 / 16

    return {
        "schema": (
            "axiompack.jacobian_moving_lie_cone_admissibility.v1"
        ),
        "instantaneous_convention": (
            "dF_s/ds = X_{K_s}(F_s) + dF_s V_s; "
            "K_s=sum s^j/j! K_j and V_s=sum s^j/j! V_j"
        ),
        "normalization": {
            "X": "-P/3",
            "Y": "-Q/2",
            "cone": "constant or X^a*Y^b with b>=1 and a<=2*b",
            "target_weight_bound": "wt(K_j)<=j+6",
        },
        "first_order_shift": {
            "base_hamiltonian": str(base_hamiltonian),
            "moving_stabilizer_hamiltonian": str(
                moving_stabilizer
            ),
            "shift_amplitude": str(shift_amplitude),
            "cone_hamiltonian": str(cone_hamiltonians[0]),
            "paired_source_degrees": [
                _degree(component, v, t)
                for component in cone_sources[0]
            ],
            "exact_identity": True,
        },
        "cone_branch": cone,
        "cone_order_two_affine_direction_control": direction_control,
        "unrestricted_positive_control": unrestricted,
        "finite_verdict": (
            "the exact cone-constrained instantaneous contact exists "
            "through family derivative order four; its carried source "
            "degree profile is (5,5,7,9), versus (0,5,5,6) for the "
            "unrestricted positive control"
        ),
        "claim_boundary": (
            "this is an exact finite moving-family prefix.  It proves "
            "coefficientwise cone admissibility only through the maximum "
            "instantaneous order presently supported by the audited "
            "solvers; it does not prove an all-order recurrence, a source "
            "slope bound, or the full symmetric contact statistic"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
