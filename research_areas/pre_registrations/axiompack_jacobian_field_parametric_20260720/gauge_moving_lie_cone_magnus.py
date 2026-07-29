#!/usr/bin/env python3
"""Exact Magnus replay for the carried moving cone contact.

The moving solver stores derivative-normalized instantaneous coefficients
`V_j`, `K_j`.  This replay converts them to ordinary series coefficients,
uses the equation-appropriate Magnus orientation in the source vector-field
and target Hamiltonian Lie algebras, and checks both forward `dexp` round
trips.
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
SRC_ROOT = HERE.parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gauge_controlled_global_magnus import (  # noqa: E402
    _bracket as _source_bracket,
)
from gauge_minimized_fourth_jet import _family_jets  # noqa: E402
from gauge_moving_lie_cone_admissibility import (  # noqa: E402
    _build_system,
    _decode,
    _instantaneous_residual,
    _target_basis,
)
from gauge_moving_section_affine_extension import (  # noqa: E402
    solve_category,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    FormalLieOps,
    VelocityPlacement,
    magnus_from_velocity,
    velocity_from_magnus,
)


Pair = tuple[sp.Expr, sp.Expr]


def _zero_like(value: object) -> object:
    if isinstance(value, tuple):
        return tuple(sp.Integer(0) for _ in value)
    return sp.Integer(0)


def _add(left: object, right: object) -> object:
    if isinstance(left, tuple):
        assert isinstance(right, tuple)
        return tuple(
            sp.expand(a + b)
            for a, b in zip(left, right, strict=True)
        )
    return sp.expand(left + right)


def _scale(value: object, scalar: sp.Expr) -> object:
    if isinstance(value, tuple):
        return tuple(sp.expand(scalar * item) for item in value)
    return sp.expand(scalar * value)


def _formal_ops(
    example: object,
    bracket: object,
) -> FormalLieOps[object]:
    def rational_scale(value: object, scalar: object) -> object:
        coefficient = sp.Rational(
            scalar.numerator, scalar.denominator  # type: ignore[attr-defined]
        )
        return _scale(value, coefficient)

    return FormalLieOps(
        zero=lambda: _zero_like(example),
        add=_add,
        scale=rational_scale,
        bracket=bracket,  # type: ignore[arg-type]
    )


def _target_bracket(
    left: sp.Expr,
    right: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> sp.Expr:
    # With X_H=(H_Q,-H_P), [X_H,X_K]=X_{H_Q K_P-H_P K_Q}.
    return sp.expand(
        sp.diff(left, q) * sp.diff(right, p)
        - sp.diff(left, p) * sp.diff(right, q)
    )


def _degree(value: object, first: sp.Symbol, second: sp.Symbol) -> int:
    values = value if isinstance(value, tuple) else (value,)
    return max(
        -1
        if sp.expand(item) == 0
        else int(sp.Poly(item, first, second).total_degree())
        for item in values
    )


def _top_shell(
    value: object,
    first: sp.Symbol,
    second: sp.Symbol,
) -> list[str]:
    degree = _degree(value, first, second)
    values = value if isinstance(value, tuple) else (value,)
    if degree < 0:
        return [str(sp.Integer(0)) for _ in values]
    result = []
    for item in values:
        polynomial = sp.Poly(item, first, second)
        result.append(str(sp.expand(sum(
            coefficient * first**exponent[0] * second**exponent[1]
            for exponent, coefficient in polynomial.terms()
            if sum(exponent) == degree
        ))))
    return result


def _sha(value: object) -> list[str]:
    values = value if isinstance(value, tuple) else (value,)
    return [
        hashlib.sha256(str(sp.expand(item)).encode("utf-8")).hexdigest()
        for item in values
    ]


def _equal(left: object, right: object) -> bool:
    if isinstance(left, tuple):
        assert isinstance(right, tuple)
        return all(
            sp.expand(a - b) == 0
            for a, b in zip(left, right, strict=True)
        )
    return bool(sp.expand(left - right) == 0)


def _order_two_log_direction(
    hamiltonians: dict[int, sp.Expr],
    source_fields: dict[int, Pair],
    data: dict[str, object],
    p: sp.Symbol,
    q: sp.Symbol,
    v: sp.Symbol,
    t: sp.Symbol,
    s: sp.Symbol,
) -> dict[str, object]:
    """Test the complete order-two affine freedom against log order three."""

    prefix_hamiltonians = {
        order: value
        for order, value in hamiltonians.items()
        if order < 2
    }
    prefix_sources = {
        order: value
        for order, value in source_fields.items()
        if order < 2
    }
    residual = _instantaneous_residual(
        2,
        prefix_hamiltonians,
        prefix_sources,
        data,
        p,
        q,
        v,
        t,
        s,
    )
    target_basis, _record = _target_basis(
        10, 12, p, q, cone_restricted=True
    )
    p0, q0 = data["P"][0], data["Q"][0]
    jacobian = sp.Matrix([p0, q0]).jacobian([v, t])
    matrix, rhs, metadata, _source_count = _build_system(
        residual,
        7,
        target_basis,
        p0,
        q0,
        jacobian,
        data["gamma"],
        p,
        q,
        v,
        t,
    )
    assert matrix.rank() == DomainMatrix.hstack(matrix, rhs).rank()
    nullspace = matrix.to_Matrix().nullspace()
    assert len(nullspace) == 1
    direction_hamiltonian, direction_source = _decode(
        nullspace[0], metadata, v, t
    )
    parameter = sp.Symbol("lambda")
    varied_sources = dict(source_fields)
    varied_sources[2] = tuple(
        sp.expand(
            source_fields[2][component]
            + parameter * direction_source[component]
        )
        for component in range(2)
    )  # type: ignore[assignment]
    velocity: list[object] = [
        tuple(
            sp.expand(component / sp.factorial(order))
            for component in varied_sources[order]
        )
        for order in range(3)
    ]
    source_bracket = lambda left, right: _source_bracket(
        left, right, v, t
    )
    logarithm = magnus_from_velocity(
        velocity,
        3,
        _formal_ops(velocity[0], source_bracket),
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    top_degree = _degree(logarithm[3], v, t)
    top_coefficients = []
    for component in logarithm[3]:
        polynomial = sp.Poly(
            sp.expand(component), v, t, parameter, domain=sp.QQ
        )
        for (v_power, t_power, parameter_power), coefficient in (
            polynomial.terms()
        ):
            if v_power + t_power == top_degree:
                top_coefficients.append(
                    coefficient * parameter**parameter_power
                )
    solutions = sp.solve(
        [sp.expand(item) for item in top_coefficients],
        [parameter],
        dict=True,
    )
    return {
        "direction_target_hamiltonian": str(direction_hamiltonian),
        "direction_source_degrees": [
            _degree(component, v, t)
            for component in direction_source
        ],
        "log_order_three_degree": top_degree,
        "top_coefficient_equations": sorted({
            str(sp.expand(item)) for item in top_coefficients
        }),
        "parameters_killing_complete_top_shell": [
            {str(key): str(value) for key, value in solution.items()}
            for solution in solutions
        ],
        "top_shell": _top_shell(logarithm[3], v, t),
    }


def run() -> dict[str, object]:
    p, q, v, t, s, x, y = sp.symbols("P Q v t s X Y")
    data = _family_jets(8)
    branch, hamiltonians, source_fields = solve_category("cone")
    maximum_velocity_order = max(hamiltonians)
    maximum_log_order = maximum_velocity_order + 1
    source_velocity: list[object] = [
        tuple(
            sp.expand(component / sp.factorial(order))
            for component in source_fields[order]
        )
        for order in range(maximum_velocity_order + 1)
    ]
    target_velocity: list[object] = [
        sp.expand(hamiltonians[order] / sp.factorial(order))
        for order in range(maximum_velocity_order + 1)
    ]
    source_bracket = lambda left, right: _source_bracket(
        left, right, v, t
    )
    target_bracket = lambda left, right: _target_bracket(
        left, right, p, q
    )
    source_ops = _formal_ops(source_velocity[0], source_bracket)
    target_ops = _formal_ops(target_velocity[0], target_bracket)
    source_log = magnus_from_velocity(
        source_velocity,
        maximum_log_order,
        source_ops,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    target_log = magnus_from_velocity(
        target_velocity,
        maximum_log_order,
        target_ops,
        VelocityPlacement.LEFT_MULTIPLY,
    )
    source_roundtrip = velocity_from_magnus(
        source_log,
        maximum_log_order,
        source_ops,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    target_roundtrip = velocity_from_magnus(
        target_log,
        maximum_log_order,
        target_ops,
        VelocityPlacement.LEFT_MULTIPLY,
    )
    assert all(
        _equal(source_roundtrip[index], source_velocity[index])
        for index in range(maximum_velocity_order + 1)
    )
    assert all(
        _equal(target_roundtrip[index], target_velocity[index])
        for index in range(maximum_velocity_order + 1)
    )

    return {
        "schema": "axiompack.jacobian_moving_lie_cone_magnus.v2",
        "convention": {
            "instantaneous_coefficients": (
                "derivative-normalized inputs converted by V_j/j!, K_j/j!"
            ),
            "target_flow": "A_prime = velocity * A",
            "target_velocity_placement": (
                VelocityPlacement.LEFT_MULTIPLY.value
            ),
            "source_flow": "psi_prime = Dpsi * velocity",
            "source_velocity_placement": (
                VelocityPlacement.RIGHT_MULTIPLY.value
            ),
        },
        "moving_branch": branch,
        "source_logarithm": [
            {
                "parameter_order": order,
                "degree": _degree(source_log[order], v, t),
                "top_shell": _top_shell(source_log[order], v, t),
                "sha256": _sha(source_log[order]),
            }
            for order in range(1, maximum_log_order + 1)
        ],
        "target_logarithm": [
            {
                "parameter_order": order,
                "hamiltonian_degree": _degree(target_log[order], p, q),
                "field_excess_degree": max(
                    0, _degree(target_log[order], p, q) - 1
                ),
                "top_shell": _top_shell(target_log[order], p, q),
                "sha256": _sha(target_log[order]),
            }
            for order in range(1, maximum_log_order + 1)
        ],
        "order_two_affine_log_control": _order_two_log_direction(
            hamiltonians,
            source_fields,
            data,
            p,
            q,
            v,
            t,
            s,
        ),
        "forward_dexp_roundtrip": {
            "source": True,
            "target": True,
        },
        "claim_boundary": (
            "finite logarithmic prefix for one cone-valued connection; "
            "no asymptotic recurrence or minimax value is asserted"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
