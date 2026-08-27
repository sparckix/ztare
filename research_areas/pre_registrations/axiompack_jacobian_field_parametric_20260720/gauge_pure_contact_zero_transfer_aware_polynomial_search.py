#!/usr/bin/env python3
"""Exact degree-capped search against the July target-left transfer.

The fixed residual prefix is supplied by the checked BCH/ODE adapter in
``gauge_pure_contact_zero_tensor_density_holonomy``.  For a candidate
origin-vanishing polynomial actor ``A``, the target-left transfer is

    K = (1-exp(-rho(A))) / rho(A) J.

It is triangular in spatial degree.  We therefore recover the unique formal
module coordinate required by ``A`` as

    J = rho(A) / (1-exp(-rho(A))) K

and impose the degree cap on that recovered series.  Exact Groebner reduction
over ``QQ`` detects the first prefix whose cap equations generate the unit
ideal.  Such a finite failure is mechanism-selection evidence only, never an
all-order exclusion.
"""

from __future__ import annotations

from fractions import Fraction
import json
from pathlib import Path
import sys
from typing import Iterable

import sympy as sp


HERE = Path(__file__).resolve().parent
SRC_ROOT = HERE.parents[2] / "src"
for path in (HERE, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from gauge_pure_contact_zero_delta_critical_recurrence import (  # noqa: E402
    _critical_recurrence,
)
from gauge_pure_contact_zero_tensor_density_holonomy import (  # noqa: E402
    _algebraic_tensor_density_velocity,
    _critical_residual_prefix,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    VelocityPlacement,
    forward_dexp_coefficients,
    inverse_dexp_coefficients,
)


DEFAULT_CAPS = ((1, 1), (1, 2), (2, 2), (2, 3), (3, 3), (3, 4))


def _sympy_rational(value: Fraction) -> sp.Rational:
    return sp.Rational(value.numerator, value.denominator)


def _truncate(value: sp.Expr, x: sp.Symbol, maximum_order: int) -> sp.Expr:
    return sp.Poly(sp.expand(value), x).rem(
        sp.Poly(x ** (maximum_order + 1), x)
    ).as_expr().expand()


def _tensor_action(
    actor: sp.Expr,
    module: sp.Expr,
    x: sp.Symbol,
    maximum_order: int,
) -> sp.Expr:
    return _truncate(
        2 * x * actor * sp.diff(module, x)
        - 3 * x * sp.diff(actor, x) * module
        - 5 * actor * module,
        x,
        maximum_order,
    )


def _operator_series(
    actor: sp.Expr,
    seed: sp.Expr,
    coefficients: Iterable[Fraction],
    x: sp.Symbol,
    maximum_order: int,
) -> sp.Expr:
    result = sp.Integer(0)
    iterate = _truncate(seed, x, maximum_order)
    for coefficient in coefficients:
        result = _truncate(
            result + _sympy_rational(coefficient) * iterate,
            x,
            maximum_order,
        )
        iterate = _tensor_action(actor, iterate, x, maximum_order)
    return result


def _required_module(
    actor: sp.Expr,
    residual: sp.Expr,
    x: sp.Symbol,
    maximum_order: int,
) -> sp.Expr:
    """Invert the target-left Duhamel transfer coefficientwise."""

    return _operator_series(
        actor,
        residual,
        inverse_dexp_coefficients(
            maximum_order - 1,
            VelocityPlacement.RIGHT_MULTIPLY,
        ),
        x,
        maximum_order,
    )


def _target_left_transfer(
    actor: sp.Expr,
    module: sp.Expr,
    x: sp.Symbol,
    maximum_order: int,
) -> sp.Expr:
    return _operator_series(
        actor,
        module,
        forward_dexp_coefficients(
            maximum_order - 1,
            VelocityPlacement.RIGHT_MULTIPLY,
        ),
        x,
        maximum_order,
    )


def _is_unit_ideal(basis: sp.GroebnerBasis) -> bool:
    return len(basis.polys) == 1 and sp.expand(
        basis.polys[0].as_expr()
    ) == 1


def _rational_solutions(
    equations: list[sp.Expr],
    variables: tuple[sp.Symbol, ...],
) -> list[dict[str, str]]:
    if not equations:
        return [{}]
    solutions = sp.solve(
        equations,
        variables,
        dict=True,
        simplify=False,
        check=True,
    )
    rational = []
    for solution in solutions:
        if not all(value.is_Rational is True for value in solution.values()):
            continue
        rational.append({str(key): str(value) for key, value in solution.items()})
    return rational


def _audit_cap(
    residual: sp.Expr,
    x: sp.Symbol,
    actor_degree_cap: int,
    module_degree_cap: int,
    maximum_order: int,
) -> dict[str, object]:
    variables = sp.symbols(f"a1:{actor_degree_cap + 1}")
    actor = sp.expand(sum(
        variables[degree - 1] * x**degree
        for degree in range(1, actor_degree_cap + 1)
    ))
    required = _required_module(actor, residual, x, maximum_order)
    replay = _target_left_transfer(actor, required, x, maximum_order)
    assert _truncate(replay - residual, x, maximum_order) == 0

    cap_equations = [
        sp.factor(required.coeff(x, degree))
        for degree in range(module_degree_cap + 1, maximum_order + 1)
    ]
    first_failure_order = None
    first_failure_basis: list[str] = []
    first_failure_equations: list[str] = []
    previous_equations: list[sp.Expr] = []
    for offset, equation in enumerate(cap_equations):
        spatial_degree = module_degree_cap + 1 + offset
        prefix_equations = cap_equations[: offset + 1]
        basis = sp.groebner(prefix_equations, *variables, order="lex", domain=sp.QQ)
        if _is_unit_ideal(basis):
            first_failure_order = spatial_degree
            first_failure_basis = [str(poly.as_expr()) for poly in basis.polys]
            first_failure_equations = [str(value) for value in prefix_equations]
            break
        previous_equations = prefix_equations

    rational_witnesses = _rational_solutions(previous_equations, variables)
    return {
        "actor_degree_cap": actor_degree_cap,
        "module_degree_cap": module_degree_cap,
        "actor": str(actor),
        "required_module_prefix": str(required),
        "target_left_roundtrip": True,
        "first_inconsistent_spatial_degree": first_failure_order,
        "last_consistent_prefix_over_algebraic_closure": (
            first_failure_order - 1
            if first_failure_order is not None
            else maximum_order
        ),
        "rational_witnesses_for_last_consistent_prefix": rational_witnesses,
        "unit_ideal_certificate": first_failure_basis,
        "constraints_through_first_failure": first_failure_equations,
        "status": (
            "exact_unit_ideal_failure"
            if first_failure_order is not None
            else "unresolved_through_declared_prefix"
        ),
    }


def run(
    maximum_order: int = 14,
    caps: tuple[tuple[int, int], ...] = DEFAULT_CAPS,
) -> dict[str, object]:
    if maximum_order < 8:
        raise ValueError("the transfer-aware search needs at least eight rows")
    if not caps:
        raise ValueError("at least one degree-cap pair is required")
    if any(actor_cap < 1 or module_cap < 1 for actor_cap, module_cap in caps):
        raise ValueError("both polynomial degree caps must be positive")

    x, _discriminant, normal_two, _normal_three, tensor_density = (
        _algebraic_tensor_density_velocity()
    )
    recurrence = _critical_recurrence(
        maximum_order,
        guess_rational_generating_function=False,
    )
    residual = _critical_residual_prefix(
        maximum_order,
        x,
        normal_two,
        tensor_density,
        recurrence,
    )
    rows = [
        _audit_cap(residual, x, actor_cap, module_cap, maximum_order)
        for actor_cap, module_cap in caps
    ]
    all_caps_excluded = all(
        row["status"] == "exact_unit_ideal_failure" for row in rows
    )
    first_failures = [
        int(row["first_inconsistent_spatial_degree"])
        for row in rows
        if row["first_inconsistent_spatial_degree"] is not None
    ]
    return {
        "schema": (
            "axiompack.jacobian_pure_contact_zero."
            "transfer_aware_polynomial_search.v1"
        ),
        "maximum_spatial_order": maximum_order,
        "fixed_residual_prefix": str(residual),
        "fixed_residual_coefficients": {
            str(degree): str(sp.factor(residual.coeff(x, degree)))
            for degree in range(1, maximum_order + 1)
        },
        "tensor_action": "rho(A)J=2*x*A*J'-3*x*A'*J-5*A*J",
        "target_left_transfer": (
            "Psi(A,J)=sum_q>=0 (-1)^q*rho(A)^q(J)/(q+1)!"
        ),
        "inverse_transfer": (
            "J=sum_q>=0 B_q(1)*rho(A)^q(K)/q!"
        ),
        "caps": rows,
        "all_declared_caps_exactly_excluded": all_caps_excluded,
        "first_failure_sequence": first_failures,
        "claim_boundary": (
            "Each unit-ideal certificate excludes only its declared finite "
            "degree cap against the checked residual prefix. The replay does "
            "not quantify over arbitrary finite caps and does not supply the "
            "actual-schedule factorization equality."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
