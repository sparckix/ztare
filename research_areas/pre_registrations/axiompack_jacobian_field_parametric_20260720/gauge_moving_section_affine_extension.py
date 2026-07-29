#!/usr/bin/env python3
"""Exact natural-weight moving-contact replay with complete affine carry.

This is a thin scientific extension of ``gauge_moving_lie_cone_admissibility``.
It changes no solver semantics.  At each order it carries the complete
homogeneous prefix kernel, tests the preceding source cap, and records a
primitive cokernel functional before selecting one affine base point.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Callable
from functools import cache
from pathlib import Path

import sympy as sp
from sympy.polys.matrices import DomainMatrix


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_minimized_fourth_jet import _family_jets  # noqa: E402
from gauge_minimized_fourth_obstruction import _quotient_duals  # noqa: E402
from gauge_minimized_third_jet import (  # noqa: E402
    _coefficient_system,
    _hamiltonian_field,
    _hamiltonian_field_window,
    _monomials,
    _particular_solution,
    _substitute,
)
from gauge_moving_lie_cone_admissibility import (  # noqa: E402
    _decode,
    _degree,
    _restrict_polynomial_span,
    _sha,
    _target_lift_support,
)
from gauge_rees_velocity_prefix import (  # noqa: E402
    _field_at_family_series,
    _source_response_series,
)


Pair = tuple[sp.Expr, sp.Expr]
Prefix = tuple[dict[int, sp.Expr], dict[int, Pair]]
Exponent = tuple[int, int]
SupportPredicate = Callable[[Exponent], bool]


def _cone(exponent: Exponent) -> bool:
    a, b = exponent
    return exponent == (0, 0) or (b >= 1 and a <= 2 * b)


def _parity(exponent: Exponent) -> bool:
    a, b = exponent
    return (
        exponent == (0, 0)
        or (b == 0 and a >= 3)
        or (b == 1 and a >= 1)
    )


CATEGORIES: dict[str, SupportPredicate] = {
    "cone": _cone,
    "parity": _parity,
}

EXPECTED_CAPS = {
    "cone": (5, 5, 7, 9, 11, 13, 14),
    "parity": (5, 5, 7, 9, 11, 13, 15),
}


@cache
def _target_basis(
    category: str,
    order: int,
    p: sp.Symbol,
    q: sp.Symbol,
) -> list[tuple[sp.Expr, Pair]]:
    """Complete C-normal target span inside the natural weight window."""

    offset = 2 * max(0, order - 1)
    raw, _first, _second = _hamiltonian_field_window(
        8 + offset, 10 + offset, p, q
    )
    predicate = CATEGORIES[category]

    def allowed(exponent: Exponent) -> bool:
        return (
            _target_lift_support(exponent)
            and predicate(exponent)
            and 2 * exponent[0] + 3 * exponent[1] <= order + 6
        )

    hamiltonians, _removed, _rank = _restrict_polynomial_span(
        [item[0] for item in raw], p, q, allowed
    )
    expected = {
        (a, b)
        for a in range((order + 6) // 2 + 1)
        for b in range((order + 6) // 3 + 1)
        if (a, b) != (0, 0)
        and allowed((a, b))
    }
    # The C-normal window is complete for the declared natural-weight
    # polynomial space, rather than merely a convenient subspace.
    assert len(hamiltonians) == len(expected)
    return [
        (hamiltonian, _hamiltonian_field(hamiltonian, p, q))
        for hamiltonian in hamiltonians
    ]


class _Family:
    def __init__(self, maximum_order: int) -> None:
        self.data = _family_jets(maximum_order + 2)
        self.v, self.t = self.data["symbols"]
        self.p, self.q = sp.symbols("P Q")
        self.p0 = self.data["P"][0]
        self.q0 = self.data["Q"][0]
        self.gamma = self.data["gamma"]
        self.jacobian = sp.Matrix([self.p0, self.q0]).jacobian(
            [self.v, self.t]
        )
        self.p_series = [
            sp.cancel(self.data["P"][order] / sp.factorial(order))
            for order in range(maximum_order + 2)
        ]
        self.q_series = [
            sp.cancel(self.data["Q"][order] / sp.factorial(order))
            for order in range(maximum_order + 2)
        ]
        self.jacobian_series = [
            [
                [
                    sp.diff(
                        (self.p_series, self.q_series)[component][order],
                        variable,
                    )
                    for order in range(maximum_order + 2)
                ]
                for variable in (self.v, self.t)
            ]
            for component in range(2)
        ]

    def contribution(self, order: int, prefix: Prefix) -> Pair:
        """Ordinary s^order coefficient contributed by a prefix."""

        hamiltonians, sources = prefix
        result = [sp.Integer(0), sp.Integer(0)]
        for field_order, hamiltonian in hamiltonians.items():
            if field_order >= order:
                continue
            relative = order - field_order
            value = _field_at_family_series(
                _hamiltonian_field(
                    hamiltonian, self.p, self.q
                ),
                self.p,
                self.q,
                self.p_series,
                self.q_series,
                relative,
            )[relative]
            for component in range(2):
                result[component] += (
                    value[component] / sp.factorial(field_order)
                )
        for field_order, source in sources.items():
            if field_order >= order:
                continue
            relative = order - field_order
            value = _source_response_series(
                source, self.jacobian_series, relative
            )[relative]
            for component in range(2):
                result[component] += (
                    value[component] / sp.factorial(field_order)
                )
        return sp.expand(result[0]), sp.expand(result[1])

    def residual(self, order: int, prefix: Prefix) -> Pair:
        known = self.contribution(order, prefix)
        scale = sp.factorial(order)
        return (
            sp.expand(self.data["P"][order + 1] - scale * known[0]),
            sp.expand(self.data["Q"][order + 1] - scale * known[1]),
        )

    def delta_residual(self, order: int, direction: Prefix) -> Pair:
        contribution = self.contribution(order, direction)
        scale = -sp.factorial(order)
        return (
            sp.expand(scale * contribution[0]),
            sp.expand(scale * contribution[1]),
        )


def _joint_system(
    *,
    family: _Family,
    category: str,
    order: int,
    source_cap: int,
    residual: Pair,
    lower_deltas: list[Pair],
) -> tuple[
    DomainMatrix,
    DomainMatrix,
    list[tuple[int, int, int]],
    list[dict[str, object]],
]:
    columns: list[tuple[sp.Expr, sp.Expr, sp.Expr, sp.Expr]] = []
    metadata: list[dict[str, object]] = []
    for component in range(2):
        forbidden = (
            {(0, 0)}
            if component == 0
            else {(0, 0), (1, 0)}
        )
        for first_power, second_power in _monomials(source_cap):
            if (first_power, second_power) in forbidden:
                continue
            monomial = (
                family.v**first_power * family.t**second_power
            )
            image = family.jacobian[:, component] * monomial
            divergence = sp.diff(
                family.gamma**2 * monomial,
                family.v if component == 0 else family.t,
            )
            columns.append((
                sp.expand(image[0]),
                sp.expand(image[1]),
                sp.expand(divergence),
                sp.Integer(0),
            ))
            metadata.append({
                "kind": "source",
                "component": component,
                "first_power": first_power,
                "second_power": second_power,
            })
    for hamiltonian, field in _target_basis(
        category, order, family.p, family.q
    ):
        value = _substitute(
            field,
            family.p,
            family.q,
            family.p0,
            family.q0,
        )
        columns.append((
            value[0], value[1], sp.Integer(0), sp.Integer(0)
        ))
        metadata.append({
            "kind": "target",
            "hamiltonian": hamiltonian,
        })
    for delta in lower_deltas:
        # M*x = R(base) + lambda*dR becomes [M,-dR]*(x,lambda)=R.
        columns.append((
            -delta[0], -delta[1], sp.Integer(0), sp.Integer(0)
        ))
    matrix, rhs, row_keys = _coefficient_system(
        columns,
        (residual[0], residual[1], sp.Integer(0), sp.Integer(0)),
        family.v,
        family.t,
    )
    return matrix, rhs, row_keys, metadata


def _add_scaled_prefix(
    target: Prefix,
    direction: Prefix,
    scalar: sp.Expr,
) -> None:
    target_hamiltonians, target_sources = target
    hamiltonians, sources = direction
    for order, value in hamiltonians.items():
        target_hamiltonians[order] = sp.expand(
            target_hamiltonians.get(order, 0) + scalar * value
        )
    for order, value in sources.items():
        old = target_sources.get(order, (sp.Integer(0), sp.Integer(0)))
        target_sources[order] = (
            sp.expand(old[0] + scalar * value[0]),
            sp.expand(old[1] + scalar * value[1]),
        )


def _primitive_cokernel(
    matrix: DomainMatrix,
    rhs: DomainMatrix,
    row_keys: list[tuple[int, int, int]],
) -> dict[str, object]:
    duals, _rank, _augmented, _chosen = _quotient_duals(matrix, rhs)
    assert duals
    dual = duals[0]
    denominators = [
        int(sp.denom(value)) for value in dual if value != 0
    ]
    if not denominators:
        common_denominator = 1
    elif len(denominators) == 1:
        common_denominator = denominators[0]
    else:
        common_denominator = sp.ilcm(*denominators)
    integers = [
        int(sp.Rational(value) * common_denominator)
        for value in dual
    ]
    nonzero = [abs(value) for value in integers if value]
    common_factor = int(sp.gcd_list(nonzero)) if nonzero else 1
    integers = [value // common_factor for value in integers]
    if next((value for value in integers if value), 1) < 0:
        integers = [-value for value in integers]
    support = [
        {
            "slot": row_keys[index][0],
            "v": row_keys[index][1],
            "t": row_keys[index][2],
            "c": coefficient,
        }
        for index, coefficient in enumerate(integers)
        if coefficient
    ]
    evaluation = sp.expand(sum(
        integers[index] * rhs.to_Matrix()[index, 0]
        for index in range(len(integers))
    ))
    top_support: dict[str, list[dict[str, int]]] = {}
    for slot in sorted({item["slot"] for item in support}):
        maximum = max(
            item["v"] + item["t"]
            for item in support
            if item["slot"] == slot
        )
        top_support[str(slot)] = [
            item
            for item in support
            if item["slot"] == slot
            and item["v"] + item["t"] == maximum
        ]
    return {
        "support_size": len(support),
        "support_sha256": hashlib.sha256(
            json.dumps(support, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "evaluation_on_residual": str(evaluation),
        "top_semantic_support": top_support,
    }


def solve_category(
    category: str,
) -> tuple[dict[str, object], dict[int, sp.Expr], dict[int, Pair]]:
    """Return a selected base point and the complete affine-rank receipt."""

    caps = EXPECTED_CAPS[category]
    family = _Family(len(caps) - 1)
    base: Prefix = ({}, {})
    directions: list[Prefix] = []
    records: list[dict[str, object]] = []

    for order, selected_cap in enumerate(caps):
        residual = family.residual(order, base)
        deltas = [
            family.delta_residual(order, direction)
            for direction in directions
        ]
        previous, previous_rhs, previous_keys, _metadata = (
            _joint_system(
                family=family,
                category=category,
                order=order,
                source_cap=selected_cap - 1,
                residual=residual,
                lower_deltas=deltas,
            )
        )
        previous_rank = previous.rank()
        previous_augmented = DomainMatrix.hstack(
            previous, previous_rhs
        ).rank()
        assert previous_rank < previous_augmented
        cokernel = _primitive_cokernel(
            previous, previous_rhs, previous_keys
        )

        matrix, rhs, _row_keys, metadata = _joint_system(
            family=family,
            category=category,
            order=order,
            source_cap=selected_cap,
            residual=residual,
            lower_deltas=deltas,
        )
        rank = matrix.rank()
        augmented_rank = DomainMatrix.hstack(matrix, rhs).rank()
        assert rank == augmented_rank
        solution = _particular_solution(matrix, rhs)
        current_count = len(metadata)
        hamiltonian, source = _decode(
            sp.Matrix(solution[:current_count, :]),
            metadata,
            family.v,
            family.t,
        )
        for scalar, direction in zip(
            list(solution[current_count:, 0]),
            directions,
            strict=True,
        ):
            _add_scaled_prefix(base, direction, scalar)
        base[0][order] = hamiltonian
        base[1][order] = source

        next_directions: list[Prefix] = []
        for vector in matrix.to_Matrix().nullspace():
            direction: Prefix = ({}, {})
            for scalar, lower in zip(
                list(vector[current_count:, 0]),
                directions,
                strict=True,
            ):
                _add_scaled_prefix(direction, lower, scalar)
            direction_hamiltonian, direction_source = _decode(
                sp.Matrix(vector[:current_count, :]),
                metadata,
                family.v,
                family.t,
            )
            direction[0][order] = direction_hamiltonian
            direction[1][order] = direction_source
            next_directions.append(direction)
        directions = next_directions

        records.append({
            "instantaneous_order": order,
            "natural_target_weight": order + 6,
            "target_dimension": len(_target_basis(
                category, order, family.p, family.q
            )),
            "lower_affine_dimension_in": len(deltas),
            "previous_cap": selected_cap - 1,
            "previous_matrix_shape": list(previous.shape),
            "previous_rank": previous_rank,
            "previous_augmented_rank": previous_augmented,
            "selected_cap": selected_cap,
            "selected_matrix_shape": list(matrix.shape),
            "selected_rank": rank,
            "selected_augmented_rank": augmented_rank,
            "complete_affine_dimension_out": len(directions),
            "cokernel": cokernel,
            "selected_hamiltonian": str(hamiltonian),
            "selected_hamiltonian_sha256": _sha(hamiltonian),
            "selected_source_degrees": [
                _degree(component, family.v, family.t)
                for component in source
            ],
            "selected_source_sha256": [
                _sha(component) for component in source
            ],
        })

    return ({
        "category": category,
        "source_cap_profile": list(caps),
        "orders": records,
        "complete_affine_carry": True,
    }, base[0], base[1])


def run() -> dict[str, object]:
    sections = {}
    for category in CATEGORIES:
        record, _hamiltonians, _sources = solve_category(category)
        sections[category] = record
    return {
        "schema": "axiompack.jacobian_moving_section_affine.v1",
        "instantaneous_convention": (
            "dF_s/ds=X_{K_s}(F_s)+dF_s V_s; "
            "K_s=sum s^j K_j/j!, V_s=sum s^j V_j/j!"
        ),
        "target_window": "natural cusp weight wt(K_j)<=j+6",
        "sections": sections,
        "finite_claim": (
            "After carrying the complete lower affine family, the cone "
            "profile is (5,5,7,9,11,13,14) and the parity profile is "
            "(5,5,7,9,11,13,15)."
        ),
        "claim_boundary": (
            "Exact through instantaneous order six only.  These velocity "
            "caps are not logarithmic degrees and imply no tail rate."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
