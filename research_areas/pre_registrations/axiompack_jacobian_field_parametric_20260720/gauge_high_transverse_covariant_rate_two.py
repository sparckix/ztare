#!/usr/bin/env python3
"""Covariant contact-zero terminal after the cost-two Q2C resonance.

The exceptional contact-zero schedule removes the old difference-two letter.
Its full cost-two Hamiltonian is still a target pullback.  This adapter proves
that the cost-three defect has a nonzero northeast orbit, while every
row-one contact-zero counterterm remains a target pullback and therefore has
nonnegative source normal order.  Exact surplus-projection certificates test
the finite base window; the all-weight conclusion uses the pullback Lie-map
identity and the symbolic northeast induction.
"""

from __future__ import annotations

import json
from math import factorial
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
SRC_ROOT = HERE.parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gauge_cone_q2c_terminal_recurrence import L_THREE, L_TWO  # noqa: E402
from gauge_controlled_global_magnus_hamiltonian import (  # noqa: E402
    _bracket,
    _ops,
)
from gauge_q2c_backbone_resonance import (  # noqa: E402
    _difference_two_cancellation,
    _source_symbol,
)
from gauge_q2c_contact_zero_product_grade import (  # noqa: E402
    _canonical_contact_zero_symbol,
    _source_data,
)
from gauge_p2q_source_newton_modules import _to_sparse  # noqa: E402
from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredBasisVector,
    FilteredSurplusProjectionProblem,
    FilteredSymbolMap,
    compile_filtered_surplus_projection,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    VelocityPlacement,
    velocity_from_magnus,
)


Exponent = tuple[int, int]
Sparse = dict[Exponent, sp.Expr]


def _advance(actor: Sparse, value: Sparse, depth: int) -> Sparse:
    result = dict(value)
    for _ in range(depth):
        result = _bracket(actor, result, 2)
    return result


def _unique_northeast(value: Sparse) -> tuple[Exponent, sp.Expr]:
    corners = [
        (exponent, coefficient)
        for exponent, coefficient in value.items()
        if not any(
            other != exponent
            and other[0] >= exponent[0]
            and other[1] >= exponent[1]
            for other in value
        )
    ]
    if len(corners) != 1:
        raise AssertionError(f"expected one northeast corner, got {corners}")
    return corners[0]


def _target_actor(
    coefficients: dict[int, sp.Expr],
    *,
    p: sp.Symbol,
    q: sp.Symbol,
) -> sp.Expr:
    cusp = 4 * p**3 - p**2 - 18 * p * q + 27 * q**2 + 4 * q
    return sp.factor(
        sp.Rational(1, 2) * q**2 * cusp
        + sum(
            coefficient * _canonical_contact_zero_symbol(weight, p, q)
            for weight, coefficient in coefficients.items()
        )
    )


def _orbit_certificate(actor: Sparse) -> dict[str, object]:
    rows = []
    current = dict(L_THREE)
    base_coefficient = None
    for depth in range(13):
        exponent, coefficient = _unique_northeast(current)
        if depth == 0:
            expected_exponent = (9, 11)
        elif depth == 1:
            expected_exponent = (20, 20)
        elif depth == 2:
            expected_exponent = (27, 27)
        else:
            expected_exponent = (11 * depth + 5, 9 * depth + 8)
        assert exponent == expected_exponent
        if depth == 3:
            assert coefficient == -sp.Rational(
                114614109,
                4194304000,
            )
            base_coefficient = coefficient
        if depth >= 4:
            assert base_coefficient is not None
            expected = sp.factor(
                base_coefficient
                * sp.prod(
                    sp.Rational(81 * (2 * index - 3), 320)
                    for index in range(3, depth)
                )
            )
            assert coefficient == expected
        cost = 2 * depth + 3
        rows.append({
            "depth": depth,
            "cost": cost,
            "northeast_exponent": list(exponent),
            "coefficient": str(coefficient),
            "normal_order": exponent[1] - exponent[0],
            "hamiltonian_degree": sum(exponent),
            "derivation_degree": sum(exponent) - 3,
        })
        current = _bracket(actor, current, 2)
    return {
        "base_depth": 3,
        "base_terminal": "u^38*z^35",
        "base_coefficient": "-114614109/4194304000",
        "terminal_for_depth_k_at_least_3": "u^(11*k+5)*z^(9*k+8)",
        "coefficient_recurrence": "c_(k+1)=81*(2*k-3)*c_k/320",
        "multiplier_nonzero_for_k_at_least_3": True,
        "cost": "2*k+3",
        "hamiltonian_degree": "20*k+13",
        "derivation_degree": "10*cost-20",
        "limiting_derivation_rate": 10,
        "rows": rows,
    }


def _forward_dexp_checks(actor: Sparse) -> list[dict[str, object]]:
    alpha, beta = sp.symbols("alpha beta")
    rows = []
    for depth in range(1, 4):
        cost = 2 * depth + 3
        logarithm = [{} for _ in range(cost + 1)]
        logarithm[2] = {
            exponent: alpha * coefficient
            for exponent, coefficient in actor.items()
        }
        logarithm[3] = {
            exponent: beta * coefficient
            for exponent, coefficient in L_THREE.items()
        }
        velocity = velocity_from_magnus(
            logarithm,
            cost,
            _ops(2),
            VelocityPlacement.RIGHT_MULTIPLY,
        )
        orbit = _advance(actor, L_THREE, depth)
        terminal, orbit_coefficient = _unique_northeast(orbit)
        actual = sp.factor(
            sp.expand(velocity[cost - 1].get(terminal, 0))
            .coeff(alpha, depth)
            .coeff(beta, 1)
        )
        expected = sp.factor(
            sp.Rational((-1) ** depth, factorial(depth + 1))
            * orbit_coefficient
        )
        assert actual == expected
        rows.append({
            "depth": depth,
            "cost": cost,
            "terminal": list(terminal),
            "coefficient": str(actual),
            "expected_scalar": f"(-1)^{depth}/{factorial(depth + 1)}",
            "matches": True,
        })
    return rows


def _surplus_certificate(
    actor: Sparse,
    *,
    depth: int,
    maximum_weight: int,
    p: sp.Symbol,
    q: sp.Symbol,
    p0: sp.Expr,
    q0: sp.Expr,
    u: sp.Symbol,
    z: sp.Symbol,
    negative_control: bool = False,
) -> dict[str, object]:
    terminal = (11 * depth + 5, 9 * depth + 8)
    forcing = _advance(actor, L_THREE, depth)[terminal]
    terminal_key = (sum(terminal), terminal[0], terminal[1])
    columns = {
        f"row_one_weight_{weight}": _advance(
            actor,
            _source_symbol(
                weight,
                p=p,
                q=q,
                p0=p0,
                q0=q0,
                u=u,
                z=z,
            ),
            depth + 1,
        )
        for weight in range(5, maximum_weight + 1)
    }
    assert all(terminal not in column for column in columns.values())
    surplus_exponents = sorted({
        exponent
        for column in columns.values()
        for exponent in column
        if (sum(exponent), exponent[0], exponent[1]) > terminal_key
    })
    if not surplus_exponents:
        raise AssertionError("surplus projection unexpectedly empty")
    domain_names = list(columns)
    if negative_control:
        domain_names.append("synthetic_terminal_control")
    surplus_names = {
        exponent: f"u{exponent[0]}z{exponent[1]}"
        for exponent in surplus_exponents
    }
    surplus_columns = {
        name: {
            surplus_names[exponent]: str(coefficient)
            for exponent, coefficient in column.items()
            if exponent in surplus_names
        }
        for name, column in columns.items()
    }
    terminal_columns = {
        name: {} for name in columns
    }
    if negative_control:
        surplus_columns["synthetic_terminal_control"] = {}
        terminal_columns["synthetic_terminal_control"] = {
            "terminal": str(forcing)
        }
    problem = FilteredSurplusProjectionProblem(
        name=(
            f"q2c_contact_zero_covariant_depth_{depth}_"
            f"weight_{maximum_weight}"
        ),
        domain_basis=tuple(
            FilteredBasisVector(name, 0) for name in domain_names
        ),
        domain_relations=(),
        surplus_basis=tuple(
            FilteredBasisVector(name, 1)
            for name in surplus_names.values()
        ),
        surplus_relations=(),
        terminal_basis=(FilteredBasisVector("terminal", 0),),
        terminal_relations=(),
        surplus_map=FilteredSymbolMap(
            "strictly_higher_source_projection",
            1,
            surplus_columns,
        ),
        terminal_map=FilteredSymbolMap(
            "terminal_projection",
            0,
            terminal_columns,
        ),
        distinguished_terminal={"terminal": str(forcing)},
    )
    return compile_filtered_surplus_projection(problem).to_dict()


def run() -> dict[str, object]:
    data = _source_data()
    u, z = data["symbols"]
    p, q = data["target_symbols"]
    p0 = data["P0"]
    q0 = data["Q0"]
    coefficients, actor = _difference_two_cancellation(
        p=p,
        q=q,
        p0=p0,
        q0=q0,
        u=u,
        z=z,
    )
    target_actor = _target_actor(coefficients, p=p, q=q)
    source_actor = _to_sparse(
        sp.expand(8 * target_actor.subs({p: p0, q: q0})),
        u,
        z,
    )
    assert source_actor == actor
    assert _unique_northeast(actor) == ((12, 12), sp.Rational(27, 1280))

    # The pullback is a Lie map: [8P0,8Q0]_{z^2}=8.
    source_p = _to_sparse(sp.expand(8 * p0), u, z)
    source_q = _to_sparse(sp.expand(8 * q0), u, z)
    assert _bracket(source_p, source_q, 2) == {(0, 0): sp.Integer(8)}
    assert all(
        exponent[1] - exponent[0] >= 0
        for exponent in source_p | source_q
    )

    training = _surplus_certificate(
        actor,
        depth=3,
        maximum_weight=18,
        p=p,
        q=q,
        p0=p0,
        q0=q0,
        u=u,
        z=z,
    )
    heldout = _surplus_certificate(
        actor,
        depth=4,
        maximum_weight=24,
        p=p,
        q=q,
        p0=p0,
        q0=q0,
        u=u,
        z=z,
    )
    assert not training["distinguished_cancellable_without_surplus"]
    assert not heldout["distinguished_cancellable_without_surplus"]
    negative = _surplus_certificate(
        actor,
        depth=3,
        maximum_weight=18,
        p=p,
        q=q,
        p0=p0,
        q0=q0,
        u=u,
        z=z,
        negative_control=True,
    )
    assert negative["distinguished_cancellable_without_surplus"]

    return {
        "schema": (
            "axiompack.jacobian_high_transverse_"
            "covariant_rate_two.v1"
        ),
        "cost_two_actor": {
            "target_hamiltonian": str(target_actor),
            "source_hamiltonian_equals_8_pullback": True,
            "term_count": len(actor),
            "unique_northeast": {
                "exponent": [12, 12],
                "coefficient": "27/1280",
            },
            "difference_two_support_absent": True,
        },
        "cost_three_covariant_orbit": _orbit_certificate(actor),
        "right_forward_dexp": {
            "flow_equation": "psi_prime = Dpsi * velocity",
            "word_scalar": "(-1)^k/(k+1)!",
            "checks": _forward_dexp_checks(actor),
        },
        "contact_zero_counterterms": {
            "row_one_leading_amplitude_word": "ad_A^(k+1)(H_1)",
            "target_pullback_lie_map": True,
            "every_pullback_monomial_has_nonnegative_normal_order": True,
            "terminal_normal_order": "3-2*k, negative for k>=2",
            "terminal_pairing_zero_all_weights": True,
            "training_surplus_certificate": training,
            "heldout_surplus_certificate": heldout,
            "synthetic_direct_terminal_control_cancels": True,
        },
        "leading_amplitude_conclusion": {
            "contact_zero_backbone_cancels_terminal": False,
            "nonzero_terminal_depths": "every k>=3",
            "limiting_source_derivation_rate": 10,
        },
        "claim_boundary": (
            "The complete coefficientwise-polynomial contact-zero "
            "associated grade cannot cancel the leading-amplitude terminal "
            "generated by the exceptional cost-two Q2C class. This is an "
            "all-weight symbolic recurrence, but it does not exclude fixed-"
            "amplitude cancellation between different amplitude degrees. "
            "The static -Q^2*C/2 preimage is the negative of the delayed "
            "prefix's own target logarithm, so its complete coupled replay "
            "removes the prefix rather than leaving a cost-three quotient."
        ),
        "next_residual": (
            "Classify the least nonzero positive-contact coefficient over "
            "the complete moving contact-zero backbone, with fixed-amplitude "
            "collisions retained."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
