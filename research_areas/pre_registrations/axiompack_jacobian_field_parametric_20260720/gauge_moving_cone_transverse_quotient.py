#!/usr/bin/env python3
"""Exact transverse-line quotient for the carried moving cone family.

The quotient comes from the pencil obstruction

    V = -1,  F_0(V,G) = (G+1, 0).

On this line the second component of every cone Hamiltonian field vanishes.
A source field of component degree at most B contributes second-component
degree at most B+2 because

    d_V Q_0 = (G+1)^2,  d_G Q_0 = 0.

At each instantaneous order this replay carries the complete affine kernel
from all preceding orders, restricts the residual before the new target and
source coefficients are added, and asks whether those lower affine
parameters can kill every G coefficient above B+2.

This is a necessary quotient test.  Its vanishing does not certify the full
contact equation at cap B.
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

from gauge_minimized_third_jet import _particular_solution  # noqa: E402
from gauge_moving_lie_cone_admissibility import _decode  # noqa: E402
from gauge_moving_section_affine_extension import (  # noqa: E402
    EXPECTED_CAPS,
    Pair,
    Prefix,
    _Family,
    _add_scaled_prefix,
    _joint_system,
)


def _line_polynomial(
    value: sp.Expr,
    family: _Family,
    g: sp.Symbol,
) -> sp.Poly:
    """Restrict to V=-1 in the linear coordinates G=t-3v/2."""

    restricted = sp.expand(
        value.subs(
            {family.t: g + sp.Rational(3, 2) * family.v},
            simultaneous=True,
        ).subs(family.v, -1)
    )
    return sp.Poly(restricted, g, domain=sp.QQ)


def _primitive_left_obstruction(
    matrix: sp.Matrix,
    rhs: sp.Matrix,
    degrees: list[int],
) -> dict[str, object] | None:
    """Return one normalized semantic left obstruction when inconsistent."""

    for vector in matrix.T.nullspace():
        evaluation = sp.expand((vector.T * rhs)[0])
        if evaluation == 0:
            continue
        denominators = [
            int(sp.denom(value)) for value in vector if value != 0
        ]
        if not denominators:
            common_denominator = 1
        elif len(denominators) == 1:
            common_denominator = denominators[0]
        else:
            common_denominator = int(sp.ilcm(*denominators))
        integers = [
            int(sp.Rational(value) * common_denominator)
            for value in vector
        ]
        nonzero = [abs(value) for value in integers if value]
        common_factor = int(sp.gcd_list(nonzero)) if nonzero else 1
        integers = [value // common_factor for value in integers]
        if next((value for value in integers if value), 1) < 0:
            integers = [-value for value in integers]
        integer_evaluation = sp.expand(sum(
            coefficient * rhs[index, 0]
            for index, coefficient in enumerate(integers)
        ))
        support = [
            {"G_degree": degree, "coefficient": coefficient}
            for degree, coefficient in zip(
                degrees, integers, strict=True
            )
            if coefficient
        ]
        return {
            "support": support,
            "evaluation": str(integer_evaluation),
            "support_sha256": hashlib.sha256(
                json.dumps(
                    support, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest(),
        }
    return None


def _quotient_at_cap(
    residual: Pair,
    deltas: list[Pair],
    source_cap: int,
    family: _Family,
    g: sp.Symbol,
) -> dict[str, object]:
    """Test whether lower affine parameters kill Lambda_B(residual)."""

    base = _line_polynomial(residual[1], family, g)
    directions = [
        _line_polynomial(delta[1], family, g)
        for delta in deltas
    ]
    threshold = source_cap + 2
    degrees = sorted({
        degree[0]
        for polynomial in [base, *directions]
        for degree in polynomial.monoms()
        if degree[0] > threshold
    })
    matrix = sp.Matrix([
        [
            polynomial.coeff_monomial(g**degree)
            for polynomial in directions
        ]
        for degree in degrees
    ])
    rhs = sp.Matrix([
        -base.coeff_monomial(g**degree)
        for degree in degrees
    ])
    rank = matrix.rank()
    augmented_rank = matrix.row_join(rhs).rank()
    avoidable = rank == augmented_rank
    result: dict[str, object] = {
        "source_cap": source_cap,
        "quotient_threshold_G_degree": threshold,
        "row_G_degrees": degrees,
        "matrix_shape": list(matrix.shape),
        "rank": rank,
        "augmented_rank": augmented_rank,
        "avoidable_by_lower_affine_parameters": avoidable,
    }
    if avoidable:
        if directions:
            solution = _particular_solution(
                DomainMatrix.from_Matrix(matrix).to_field(),
                DomainMatrix.from_Matrix(rhs).to_field(),
            )
            result["one_lower_parameter_solution"] = [
                str(value) for value in solution
            ]
            result["remaining_lower_parameter_dimension"] = (
                len(directions) - rank
            )
        else:
            result["one_lower_parameter_solution"] = []
            result["remaining_lower_parameter_dimension"] = 0
    else:
        obstruction = _primitive_left_obstruction(
            matrix, rhs, degrees
        )
        assert obstruction is not None
        result["primitive_obstruction"] = obstruction
    return result


def _audit_order(
    order: int,
    residual: Pair,
    deltas: list[Pair],
    selected_cap: int | None,
    family: _Family,
    g: sp.Symbol,
) -> dict[str, object]:
    base_line = _line_polynomial(residual[1], family, g)
    delta_lines = [
        _line_polynomial(delta[1], family, g)
        for delta in deltas
    ]
    maximum_degree = max(
        [
            base_line.degree(),
            *(polynomial.degree() for polynomial in delta_lines),
        ],
        default=-1,
    )
    maximum_degree = int(maximum_degree) if maximum_degree != -sp.oo else -1
    caps = set(range(max(0, maximum_degree - 2) + 1))
    caps.update({11, 23})
    if selected_cap is not None:
        caps.update({selected_cap - 1, selected_cap})
    checks = {
        str(cap): _quotient_at_cap(
            residual, deltas, cap, family, g
        )
        for cap in sorted(cap for cap in caps if cap >= 0)
    }
    avoidable_caps = [
        int(cap)
        for cap, record in checks.items()
        if record["avoidable_by_lower_affine_parameters"]
    ]
    fixed = {
        str(cap): checks[str(cap)]
        for cap in sorted({
            11,
            23,
            *(
                ()
                if selected_cap is None
                else (selected_cap - 1, selected_cap)
            ),
        })
        if cap >= 0
    }
    return {
        "instantaneous_order": order,
        "lower_affine_dimension": len(deltas),
        "base_residual_Q_on_line": str(base_line.as_expr()),
        "base_residual_Q_line_degree": (
            int(base_line.degree())
            if base_line.degree() != -sp.oo
            else -1
        ),
        "delta_Q_line_degrees": [
            (
                int(polynomial.degree())
                if polynomial.degree() != -sp.oo
                else -1
            )
            for polynomial in delta_lines
        ],
        "minimum_source_cap_not_excluded_by_Lambda": (
            min(avoidable_caps) if avoidable_caps else None
        ),
        "declared_cap": selected_cap,
        "fixed_checks": fixed,
        "all_cap_checks": checks,
    }


def run() -> dict[str, object]:
    caps = EXPECTED_CAPS["cone"]
    # One extra family order supplies the order-seven lookahead residual
    # after the complete affine prefix through order six has been carried.
    family = _Family(len(caps))
    g = sp.Symbol("G")
    base: Prefix = ({}, {})
    directions: list[Prefix] = []
    audits: list[dict[str, object]] = []

    for order, selected_cap in enumerate(caps):
        residual = family.residual(order, base)
        deltas = [
            family.delta_residual(order, direction)
            for direction in directions
        ]
        audits.append(_audit_order(
            order,
            residual,
            deltas,
            selected_cap,
            family,
            g,
        ))

        matrix, rhs, _row_keys, metadata = _joint_system(
            family=family,
            category="cone",
            order=order,
            source_cap=selected_cap,
            residual=residual,
            lower_deltas=deltas,
        )
        assert matrix.rank() == DomainMatrix.hstack(
            matrix, rhs
        ).rank()
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

    lookahead_order = len(caps)
    lookahead_residual = family.residual(lookahead_order, base)
    lookahead_deltas = [
        family.delta_residual(lookahead_order, direction)
        for direction in directions
    ]
    audits.append(_audit_order(
        lookahead_order,
        lookahead_residual,
        lookahead_deltas,
        None,
        family,
        g,
    ))

    expected_degrees = [2, 2, 3, 3, 4, 4, 5, 5]
    expected_minimum_caps = [0, 0, 1, 1, 2, 2, 3, 3]
    assert [
        item["base_residual_Q_line_degree"] for item in audits
    ] == expected_degrees
    assert [
        item["minimum_source_cap_not_excluded_by_Lambda"]
        for item in audits
    ] == expected_minimum_caps
    assert len(directions) == 14
    assert all(
        item["fixed_checks"][str(cap)][
            "avoidable_by_lower_affine_parameters"
        ]
        for item in audits
        for cap in (11, 23)
    )
    assert all(
        item["all_cap_checks"][str(minimum_cap - 1)][
            "avoidable_by_lower_affine_parameters"
        ] is False
        for item, minimum_cap in zip(
            audits, expected_minimum_caps, strict=True
        )
        if minimum_cap > 0
    )

    return {
        "schema": "axiompack.jacobian_cone_transverse_quotient.v1",
        "quotient": (
            "restrict Q residual to V=-1 in G=t-3V/2; "
            "project G degrees > B+2"
        ),
        "carried_cone_caps_through_order_six": list(caps),
        "complete_affine_dimension_after_order_six": len(directions),
        "orders": audits,
        "finite_claim": (
            "Lambda_B is a necessary semantic quotient for the exact "
            "carried affine prefix; passing it does not imply full-system "
            "consistency at cap B."
        ),
        "claim_boundary": (
            "Orders zero through six use the complete affine cone family. "
            "Order seven is a residual lookahead before solving its full "
            "contact system. No all-order conclusion follows."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
