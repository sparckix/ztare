#!/usr/bin/env python3
"""Exact Hamiltonian replay of the globally controlled Magnus logarithms.

The adapted source coordinate ``z = 2 + 2*t - 3*v`` makes the invariant
density exactly ``z**2``.  Polynomial Hamiltonians then obey a closed sparse
monomial bracket, so the order-nine source calculation does not use a
degree filter or a fitted recurrence.
"""

from __future__ import annotations

from fractions import Fraction
import json
from pathlib import Path
import sys
from typing import TypeAlias

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
SRC_ROOT = HERE.parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gauge_regular_singular_connection import (  # noqa: E402
    _inverse_action,
    source_only_connection,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    FormalLieOps,
    VelocityPlacement,
    magnus_from_velocity,
    velocity_from_magnus,
)


Exponent: TypeAlias = tuple[int, int]
SparseHamiltonian: TypeAlias = dict[Exponent, sp.Expr]


def _add(
    left: SparseHamiltonian,
    right: SparseHamiltonian,
) -> SparseHamiltonian:
    result = dict(left)
    for exponent, coefficient in right.items():
        result[exponent] = sp.cancel(
            result.get(exponent, sp.Integer(0)) + coefficient
        )
    return {
        exponent: coefficient
        for exponent, coefficient in result.items()
        if coefficient != 0
    }


def _scale(
    value: SparseHamiltonian,
    scalar: Fraction,
) -> SparseHamiltonian:
    rational = sp.Rational(scalar.numerator, scalar.denominator)
    return {
        exponent: sp.cancel(rational * coefficient)
        for exponent, coefficient in value.items()
        if coefficient != 0
    }


def _bracket(
    left: SparseHamiltonian,
    right: SparseHamiltonian,
    density_power: int,
) -> SparseHamiltonian:
    """Hamiltonian of the vector-field bracket for density ``y**p``."""
    result: SparseHamiltonian = {}
    for (left_x, left_y), left_coefficient in left.items():
        for (right_x, right_y), right_coefficient in right.items():
            multiplier = left_y * right_x - left_x * right_y
            if multiplier == 0:
                continue
            exponent = (
                left_x + right_x - 1,
                left_y + right_y - density_power - 1,
            )
            if min(exponent) < 0:
                raise AssertionError(
                    "Hamiltonian bracket left the polynomial cone"
                )
            result[exponent] = (
                result.get(exponent, sp.Integer(0))
                + multiplier * left_coefficient * right_coefficient
            )
    return {
        exponent: coefficient
        for exponent, raw_coefficient in result.items()
        if (coefficient := sp.cancel(raw_coefficient)) != 0
    }


def _ops(density_power: int) -> FormalLieOps[SparseHamiltonian]:
    return FormalLieOps(
        zero=dict,
        add=_add,
        scale=_scale,
        bracket=lambda left, right: _bracket(
            left, right, density_power
        ),
    )


def _to_sparse(
    value: sp.Expr,
    first: sp.Symbol,
    second: sp.Symbol,
) -> SparseHamiltonian:
    return {
        exponent: sp.cancel(coefficient)
        for exponent, coefficient in sp.Poly(
            sp.expand(value), first, second
        ).terms()
        if coefficient != 0 and exponent != (0, 0)
    }


def _controlled_connection(
    connection_data: dict[str, object] | None = None,
) -> tuple[
    sp.Symbol,
    sp.Symbol,
    sp.Symbol,
    tuple[sp.Expr, sp.Expr],
    sp.Expr,
    sp.Expr,
]:
    data = (
        source_only_connection()
        if connection_data is None
        else connection_data
    )
    s, v, t, _ = data["symbols"]
    family_p, family_q = data["family"]
    jacobian = data["jacobian"]
    determinant = data["determinant"]
    source_only = data["source_only"]
    pullback_p3 = _inverse_action(
        jacobian,
        determinant,
        (sp.Integer(0), -3 * family_p**2),
    )
    pullback_pq = _inverse_action(
        jacobian,
        determinant,
        (family_p, -family_q),
    )
    pullback_q2 = _inverse_action(
        jacobian,
        determinant,
        (2 * family_q, sp.Integer(0)),
    )
    coefficient_p3 = sp.factor(
        96
        * (s**2 - 12 * s + 16)
        / (
            (s - 6) ** 3
            * (s - 4) ** 2
            * (s + 4) ** 2
        )
    )
    coefficient_pq = sp.factor(
        2 * s / ((s - 4) * (s + 4))
    )
    source = tuple(
        sp.cancel(
            source_only[index]
            - coefficient_p3 * pullback_p3[index]
            - coefficient_pq * pullback_pq[index]
            + sp.Rational(1, 4) * pullback_q2[index]
        )
        for index in range(2)
    )
    assert all(component.subs(s, 0) == 0 for component in source)
    return (
        s,
        v,
        t,
        source,  # type: ignore[arg-type]
        coefficient_p3,
        coefficient_pq,
    )


def _source_velocity(
    maximum_order: int,
    connection_data: dict[str, object] | None = None,
) -> tuple[
    list[SparseHamiltonian],
    tuple[sp.Symbol, sp.Symbol, sp.Symbol],
    sp.Expr,
    sp.Expr,
]:
    s, v, t, source, coefficient_p3, coefficient_pq = (
        _controlled_connection(connection_data)
    )
    z = sp.symbols("z")
    substitution = {t: (z - 2 + 3 * v) / 2}
    source_v = sp.cancel(source[0].subs(substitution))
    source_z = sp.cancel(
        (2 * source[1] - 3 * source[0]).subs(substitution)
    )
    assert sp.factor(
        sp.diff(z**2 * source_v, v)
        + sp.diff(z**2 * source_z, z)
    ) == 0
    # These exact rational functions have scalar spatial denominators.
    # Integrating either Hamilton equation therefore bounds every
    # nonconstant Hamiltonian monomial by v**a*z**b with a,b <= 9,
    # uniformly over all parameter orders.
    for component, derivative_index in (
        (z**2 * source_v, 1),
        (-z**2 * source_z, 0),
    ):
        numerator, denominator = sp.together(component).as_numer_denom()
        assert not ({v, z} & denominator.free_symbols)
        for exponent, coefficient in sp.Poly(
            numerator, v, z
        ).terms():
            if coefficient == 0:
                continue
            integrated_exponent = list(exponent)
            integrated_exponent[derivative_index] += 1
            assert max(integrated_exponent) <= 9
    expanded = [
        sp.series(component, s, 0, maximum_order)
        .removeO()
        .expand()
        for component in (source_v, source_z)
    ]
    velocity: list[SparseHamiltonian] = []
    for order in range(maximum_order):
        v_coefficient = expanded[0].coeff(s, order)
        z_coefficient = expanded[1].coeff(s, order)
        primitive = sp.integrate(z**2 * v_coefficient, z)
        residual = sp.expand(
            -sp.diff(primitive, v) - z**2 * z_coefficient
        )
        assert z not in residual.free_symbols
        hamiltonian = sp.expand(
            primitive + sp.integrate(residual, v)
        )
        hamiltonian = sp.expand(
            hamiltonian - hamiltonian.subs({v: 0, z: 0})
        )
        assert sp.expand(
            sp.diff(hamiltonian, z) - z**2 * v_coefficient
        ) == 0
        assert sp.expand(
            -sp.diff(hamiltonian, v) - z**2 * z_coefficient
        ) == 0
        velocity.append(_to_sparse(hamiltonian, v, z))
    return (
        velocity,
        (s, v, z),
        coefficient_p3,
        coefficient_pq,
    )


def _target_velocity(
    maximum_order: int,
    coefficient_p3: sp.Expr,
    coefficient_pq: sp.Expr,
    s: sp.Symbol,
) -> tuple[
    list[SparseHamiltonian],
    tuple[sp.Symbol, sp.Symbol],
]:
    p, q = sp.symbols("P Q")
    hamiltonian = (
        coefficient_p3 * p**3
        + coefficient_pq * p * q
        - sp.Rational(1, 4) * q**2
    )
    expanded = sp.series(
        hamiltonian, s, 0, maximum_order
    ).removeO().expand()
    return (
        [
            _to_sparse(expanded.coeff(s, order), p, q)
            for order in range(maximum_order)
        ],
        (p, q),
    )


def _top_row(
    hamiltonian: SparseHamiltonian,
    density_power: int,
) -> dict[str, object]:
    if not hamiltonian:
        return {
            "hamiltonian_degree": -1,
            "derivation_degree": -1,
            "top_hamiltonian": {},
            "term_count": 0,
        }
    degree = max(sum(exponent) for exponent in hamiltonian)
    top = {
        f"{exponent[0]},{exponent[1]}": str(sp.factor(coefficient))
        for exponent, coefficient in hamiltonian.items()
        if sum(exponent) == degree
    }
    return {
        "hamiltonian_degree": degree,
        "derivation_degree": degree - density_power - 1,
        "top_hamiltonian": top,
        "term_count": len(hamiltonian),
    }


def _magnus_replay(
    velocity: list[SparseHamiltonian],
    maximum_order: int,
    density_power: int,
    placement: VelocityPlacement,
) -> list[SparseHamiltonian]:
    ops = _ops(density_power)
    logarithm = magnus_from_velocity(
        velocity, maximum_order, ops, placement
    )
    replay = velocity_from_magnus(
        logarithm, maximum_order, ops, placement
    )
    assert replay[:maximum_order] == velocity
    return logarithm


def run(
    maximum_source_order: int = 9,
    maximum_target_order: int = 15,
) -> dict[str, object]:
    if maximum_source_order < 9:
        raise ValueError("source replay must include kill order nine")
    (
        source_velocity,
        (s, v, z),
        coefficient_p3,
        coefficient_pq,
    ) = _source_velocity(maximum_source_order)
    target_velocity, (p, q) = _target_velocity(
        maximum_target_order,
        coefficient_p3,
        coefficient_pq,
        s,
    )
    source_logarithm = _magnus_replay(
        source_velocity,
        maximum_source_order,
        2,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    target_logarithm = _magnus_replay(
        target_velocity,
        maximum_target_order,
        0,
        VelocityPlacement.LEFT_MULTIPLY,
    )

    expected_source_top = {
        6: ((13, 12), sp.Rational(1, 1_048_576)),
        7: ((14, 13), -sp.Rational(619, 1_321_205_760)),
        8: ((15, 14), sp.Rational(343, 6_794_772_480)),
        9: ((20, 17), -sp.Rational(23, 42_278_584_320)),
    }
    for order, (exponent, coefficient) in expected_source_top.items():
        degree = max(
            sum(monomial)
            for monomial in source_logarithm[order]
        )
        top = {
            monomial: value
            for monomial, value in source_logarithm[order].items()
            if sum(monomial) == degree
        }
        assert top == {exponent: coefficient}

    source_rows = {
        str(order): _top_row(source_logarithm[order], 2)
        for order in range(1, maximum_source_order + 1)
    }
    source_rows["9"]["former_slope_two_ray_coefficient"] = str(
        sp.factor(source_logarithm[9].get((16, 15), 0))
    )
    target_rows = {
        str(order): _top_row(target_logarithm[order], 0)
        for order in range(1, maximum_target_order + 1)
    }
    return {
        "schema": (
            "axiompack.jacobian_controlled_global_"
            "magnus_hamiltonian.v1"
        ),
        "source": {
            "coordinates": [str(v), str(z)],
            "density": "z^2",
            "flow_equation": "psi_prime = Dpsi * velocity",
            "velocity_placement": (
                VelocityPlacement.RIGHT_MULTIPLY.value
            ),
            "maximum_order": maximum_source_order,
            "forward_dexp_roundtrip": True,
            "rows": source_rows,
            "order_nine_slope_two_conjecture_killed": True,
        },
        "target": {
            "coordinates": [str(p), str(q)],
            "density": "1",
            "flow_equation": "A_prime = velocity * A",
            "velocity_placement": (
                VelocityPlacement.LEFT_MULTIPLY.value
            ),
            "maximum_order": maximum_target_order,
            "forward_dexp_roundtrip": True,
            "rows": target_rows,
        },
        "claim_boundary": (
            "Complete exact finite replay for one rational connection. "
            "The order-nine source shell disproves the proposed slope-two "
            "top-ray continuation. It does not establish an all-order "
            "source recurrence or a minimax lower bound."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
