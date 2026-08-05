#!/usr/bin/env python3
"""Radial/odd-normal Magnus induction for the pure contact-zero branch.

The source instantaneous Hamiltonian of every compatible contact has
nonnegative normal order in the adapted basis

    E_(a,n) = r**a * z**n = u**a * z**(a+n).

This replay isolates the exact two-letter obstruction behind a finite
critical or supercritical radial prefix.  A radial velocity letter at
primitive order ``p`` and an odd-normal letter at primitive order ``q``
create logarithmic descendants at orders ``q + k*p``.  The coefficient
series is computed in the semidirect Lie algebra

    [A, V_k] = V_(k+1),   [V_i, V_j] = 0.

It terminates exactly at the same-carrier resonance ``p == q``.  Outside
that resonance infinitely many coefficients are nonzero.  The replay also
checks the actual order-zero source-only Hamiltonian and identifies its
normal-one polynomial as the lowest odd radial terminal.
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

from gauge_normal_defect_five_causality import (  # noqa: E402
    _source_only_hamiltonian,
)
from gauge_moving_pullback_normal_semigroup import (  # noqa: E402
    _exact_family,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    FormalLieOps,
    VelocityPlacement,
    inverse_dexp_coefficients,
    magnus_from_velocity,
    velocity_from_magnus,
)


BasisLabel: TypeAlias = str | int
ChainVector: TypeAlias = dict[BasisLabel, Fraction]


def _chain_ops() -> FormalLieOps[ChainVector]:
    def add(left: ChainVector, right: ChainVector) -> ChainVector:
        result = dict(left)
        for label, coefficient in right.items():
            result[label] = result.get(label, Fraction(0)) + coefficient
        return {
            label: coefficient
            for label, coefficient in result.items()
            if coefficient
        }

    def scale(value: ChainVector, scalar: Fraction) -> ChainVector:
        return {
            label: scalar * coefficient
            for label, coefficient in value.items()
            if scalar * coefficient
        }

    def bracket(left: ChainVector, right: ChainVector) -> ChainVector:
        result: ChainVector = {}
        for left_label, left_coefficient in left.items():
            for right_label, right_coefficient in right.items():
                if left_label == "A" and isinstance(right_label, int):
                    label = right_label + 1
                    sign = 1
                elif isinstance(left_label, int) and right_label == "A":
                    label = left_label + 1
                    sign = -1
                else:
                    continue
                result[label] = (
                    result.get(label, Fraction(0))
                    + sign * left_coefficient * right_coefficient
                )
        return {
            label: coefficient
            for label, coefficient in result.items()
            if coefficient
        }

    return FormalLieOps(
        zero=dict,
        add=add,
        scale=scale,
        bracket=bracket,
    )


def _source_seed_certificate() -> dict[str, object]:
    (parameter, u, z), hamiltonian, _support = (
        _source_only_hamiltonian()
    )
    radial = sp.symbols("r")
    seed = sp.factor(hamiltonian.subs(parameter, 0))
    seed_radial_normal = sp.expand(seed.subs(u, radial / z))
    expected = {
        0: sp.factor(
            radial**3
            * (9 * radial**3 + 36 * radial**2 - 108 * radial + 64)
            / 288
        ),
        1: sp.factor(
            radial**2 * (-3 * radial**2 - 12 * radial + 16) / 48
        ),
        2: radial / 6,
        3: sp.Rational(1, 36),
    }
    reconstructed = sp.expand(sum(
        coefficient * z**normal
        for normal, coefficient in expected.items()
    ))
    assert sp.expand(seed_radial_normal - reconstructed) == 0
    assert expected[1] != 0
    tangent_factor = 2 - 3 * radial
    assert sp.factor(
        sp.diff(expected[0], radial) - tangent_factor * expected[1]
    ) == 0

    # Normal zero is radial and is killed by one radial bracket.  Normal two
    # is killed after two.  Normal one and normal three are odd and survive
    # every radial adjoint depth; normal one is the unique lowest such layer.
    depth = sp.symbols("k", integer=True, nonnegative=True)
    index = sp.symbols("i", integer=True, nonnegative=True)
    odd_multiplier = sp.product(1 - 2 * index, (index, 0, depth - 1))
    return {
        "source_row_zero_before_normalization": str(seed),
        "radial_normal_layers": {
            str(normal): str(coefficient)
            for normal, coefficient in expected.items()
        },
        "lowest_odd_normal": 1,
        "lowest_odd_polynomial": str(expected[1]),
        "row_zero_tangency": "R_0'=(2-3*r)*N_0",
        "row_zero_defect_one_is_not_an_independent_terminal": True,
        "odd_falling_product": str(odd_multiplier),
        "odd_falling_product_has_no_integer_zero": True,
    }


def _normalized_background_certificate() -> dict[str, object]:
    (parameter, u, z), family_p, family_q = _exact_family()
    (_symbols, source_only, _support) = _source_only_hamiltonian()
    target_p, target_q = sp.symbols("P Q")
    radial = sp.symbols("r")
    normalized_seed = -target_p**3 / 36 - target_q**2 / 4
    normalized = sp.cancel(
        source_only
        + 8 * normalized_seed.subs({
            target_p: family_p,
            target_q: family_q,
        })
    )
    assert sp.cancel(normalized.subs(parameter, 0)) == 0
    row_one = sp.factor(
        sp.diff(normalized, parameter).subs(parameter, 0)
    )
    row_one_radial_normal = sp.expand(row_one.subs(u, radial / z))
    expected_layers = {
        0: (
            sp.Rational(7, 36) * radial**3
            - sp.Rational(7, 16) * radial**4
            + sp.Rational(13, 40) * radial**5
            - sp.Rational(7, 96) * radial**6
            - sp.Rational(3, 448) * radial**7
        ),
        1: (
            sp.Rational(7, 24) * radial**2
            - sp.Rational(7, 16) * radial**3
            + sp.Rational(5, 32) * radial**4
            + sp.Rational(1, 64) * radial**5
        ),
        2: (
            sp.Rational(1, 12) * radial
            - sp.Rational(1, 16) * radial**2
            - sp.Rational(1, 48) * radial**3
        ),
        3: sp.Rational(1, 36),
    }
    assert sp.expand(
        row_one_radial_normal
        - sum(
            coefficient * z**normal
            for normal, coefficient in expected_layers.items()
        )
    ) == 0

    current_control = (
        sp.Rational(29, 420) * target_q**2
        - sp.Rational(19, 840) * target_p * target_q
        - sp.Rational(1, 168) * target_p**2 * target_q
        - sp.Rational(47, 2520) * target_p**3
    )
    current_pullback = sp.expand(current_control.subs({
        target_p: family_p.subs(parameter, 0),
        target_q: family_q.subs(parameter, 0),
    }))
    transferred = sp.factor(row_one + 8 * current_pullback)
    expected_transferred = sp.expand(
        z**2 * (
            -sp.Rational(43, 840) * radial
            + sp.Rational(23, 560) * radial**2
            - sp.Rational(1, 112) * radial**3
        )
        + z**3 * (
            sp.Rational(23, 2520)
            - sp.Rational(1, 336) * radial
        )
    )
    assert sp.expand(
        transferred.subs(u, radial / z) - expected_transferred
    ) == 0
    return {
        "normalized_target_row_zero": "-P^3/36-Q^2/4",
        "normalized_source_row_zero_is_zero": True,
        "row_one_layers": {
            str(normal): str(sp.factor(coefficient))
            for normal, coefficient in expected_layers.items()
        },
        "row_one_lowest_odd_normal": 1,
        "row_one_lowest_odd_top": "r^5*z/64",
        "complete_current_transfer": str(current_control),
        "radial_and_normal_one_cancel": True,
        "transferred_odd_terminal": "z^3*(46-15*r)/5040",
        "transferred_odd_terminal_nonzero": True,
        "interpretation": (
            "The raw row-zero normal-one layer cancels with its tangent "
            "companion. After the exact normalized row-zero cancellation, "
            "the first odd carrier is row one. A current contact-zero row "
            "can move it from normal one to normal three but does not "
            "erase the odd block in this exact transfer."
        ),
    }


def _magnus_chain(
    radial_primitive_order: int,
    odd_primitive_order: int,
    maximum_depth: int,
) -> tuple[list[Fraction], list[ChainVector], list[ChainVector]]:
    p = radial_primitive_order
    q = odd_primitive_order
    maximum_order = q + maximum_depth * p
    velocity: list[ChainVector] = [
        {} for _ in range(maximum_order)
    ]
    # Integrating either isolated letter gives s**p*A or s**q*V_0.
    velocity[p - 1] = {"A": Fraction(p)}
    velocity[q - 1] = {
        **velocity[q - 1],
        0: velocity[q - 1].get(0, Fraction(0)) + Fraction(q),
    }
    logarithm = magnus_from_velocity(
        velocity,
        maximum_order,
        _chain_ops(),
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    replay = velocity_from_magnus(
        logarithm,
        maximum_order,
        _chain_ops(),
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    assert replay[:maximum_order] == velocity
    coefficients = [
        logarithm[q + depth * p].get(depth, Fraction(0))
        for depth in range(maximum_depth + 1)
    ]
    return coefficients, logarithm, velocity


def _coefficient_formula(
    radial_primitive_order: int,
    odd_primitive_order: int,
    maximum_depth: int,
) -> list[Fraction]:
    p = radial_primitive_order
    q = odd_primitive_order
    # C(x)=x/(exp(x)-1) * integral_0^1 q*t^(q-1)*exp(x*t^p) dt.
    bernoulli = list(inverse_dexp_coefficients(
        maximum_depth,
        VelocityPlacement.LEFT_MULTIPLY,
    ))
    return [
        sum(
            bernoulli[index]
            * Fraction(q, q + (depth - index) * p)
            / Fraction(sp.factorial(depth - index))
            for index in range(depth + 1)
        )
        for depth in range(maximum_depth + 1)
    ]


def _two_letter_certificate() -> dict[str, object]:
    cases = ((1, 1), (1, 2), (1, 3), (2, 1), (2, 3), (3, 2))
    maximum_depth = 10
    rows = []
    for p, q in cases:
        coefficients, _logarithm, _velocity = _magnus_chain(
            p, q, maximum_depth
        )
        formula = _coefficient_formula(p, q, maximum_depth)
        assert coefficients == formula
        if p == q:
            assert coefficients == [Fraction(1)] + [
                Fraction(0) for _ in range(maximum_depth)
            ]
        else:
            assert any(
                coefficients[index]
                for index in range(maximum_depth // 2, maximum_depth + 1)
            )
        rows.append({
            "radial_primitive_order": p,
            "odd_primitive_order": q,
            "coefficients_depth_0_to_10": [
                str(coefficient) for coefficient in coefficients
            ],
            "same_carrier_resonance": p == q,
        })

    return {
        "chain_lie_algebra": "[A,V_k]=V_(k+1), [V_i,V_j]=0",
        "descendant_order": "q+k*p",
        "coefficient_generating_series": (
            "C_(p,q)(x)=x/(exp(x)-1)*"
            "integral_0^1 q*t^(q-1)*exp(x*t^p)dt"
        ),
        "moment_identity": (
            "sum_k c_k*(n)_k=n*q/(q+(n-1)*p)"
        ),
        "termination_argument": (
            "If c_k=0 above N, the left side is a polynomial P(n). "
            "Then (q+(n-1)p)P(n)=nq identically. Degree comparison "
            "makes P constant, and coefficient comparison gives p=q."
        ),
        "terminates_if_and_only_if": "p=q",
        "same_carrier_interpretation": (
            "p=q combines the two spatial letters into one velocity "
            "coefficient and must be packed before the Lie transition"
        ),
        "typed_forward_dexp_roundtrip": True,
        "regression_rows": rows,
    }


def _rate_certificate() -> dict[str, object]:
    p, q, radial_degree, odd_radial_degree, odd_normal, depth = sp.symbols(
        "p q d a n k", integer=True, positive=True
    )
    output_radial_degree = sp.expand(
        odd_radial_degree + depth * (radial_degree - 1)
    )
    output_normal = sp.expand(odd_normal - 2 * depth)
    output_hamiltonian_degree = sp.expand(
        2 * output_radial_degree + output_normal
    )
    output_order = sp.expand(q + depth * p)
    assert sp.expand(
        output_hamiltonian_degree
        - (
            2 * odd_radial_degree
            + odd_normal
            + depth * (2 * radial_degree - 4)
        )
    ) == 0
    return {
        "descendant_radial_degree": "a+k*(d-1)",
        "descendant_normal": "n-2*k",
        "descendant_hamiltonian_degree": "2*a+n+k*(2*d-4)",
        "descendant_logarithmic_order": "q+k*p",
        "limiting_source_hamiltonian_rate": "(2*d-4)/p",
        "limiting_source_derivation_rate": "(2*d-4)/p",
        "rate_at_least_two_iff": "d>=p+2",
        "normal_face_is_negative_eventually": True,
    }


def run() -> dict[str, object]:
    return {
        "schema": (
            "axiompack.jacobian_pure_contact_zero_"
            "radial_normal_induction.v1"
        ),
        "source_seed": _source_seed_certificate(),
        "normalized_background": _normalized_background_certificate(),
        "radial_odd_magnus": _two_letter_certificate(),
        "asymptotic_rate": _rate_certificate(),
        "new_induction_edge": {
            "state": "unpacked_radial_odd_pair",
            "uncharged_transition": "pack_equal_parameter_orders",
            "charged_transition": (
                "p!=q and radial d>=p+2 gives infinitely many "
                "source logarithmic descendants of rate at least two"
            ),
            "collision_filter": (
                "after packing the complete row-zero tangent graph, "
                "all-radial words uniquely minimize normal order around "
                "a supplied odd carrier because current letters have "
                "nonnegative normal order"
            ),
        },
        "claim_boundary": (
            "This is an all-order radial/odd-normal Magnus edge, including "
            "the exact same-carrier resonance, the rejected raw row-zero "
            "terminal, and the normalized row-one transfer to normal three. "
            "Unconditional pure-contact-zero closure additionally requires "
            "a proof that every current-row odd transfer either terminates, "
            "pays on one side at rate two, or strictly descends in the "
            "complete radial/normal quotient."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
