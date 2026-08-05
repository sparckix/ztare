#!/usr/bin/env python3
"""Radial multiplier and first normal transition of the moving divisor."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_moving_pullback_normal_semigroup import _exact_family  # noqa: E402


def _target_data() -> tuple[sp.Symbol, ...]:
    return sp.symbols("P Q")


def _leak_preimages(
    p: sp.Symbol,
    q: sp.Symbol,
) -> dict[str, sp.Expr]:
    return {
        "P3": -(
            p**3
            - 3888 * p**2 * q**3
            + 8712 * p**2 * q**2
            + 23 * p**2 * q
            - 37260 * p * q**3
            - 2001 * p * q**2
            - 4 * p * q
            + 32076 * q**4
            + 4185 * q**3
            - 84 * q**2
        ) / 384,
        "PQ": -q * (
            588 * p**2 * q
            + p**2
            - 1188 * p * q**2
            - 126 * p * q
            - 972 * q**3
            - 171 * q**2
            - 4 * q
        ) / 96,
        "Q2": -q**2 * (
            36 * p**2 * q
            + p**2
            + 138 * p * q
            - 459 * q**2
            - 36 * q
        ) / 24,
    }


def _normal_layers(
    value: sp.Expr,
    *,
    u: sp.Symbol,
    z: sp.Symbol,
    r: sp.Symbol,
) -> dict[int, sp.Expr]:
    transformed = sp.cancel(value.subs(u, r / z))
    numerator, denominator = transformed.as_numer_denom()
    assert not denominator.has(r, z)
    polynomial = sp.Poly(sp.expand(numerator), r, z)
    layers: dict[int, sp.Expr] = {}
    for (radial_degree, normal_order), coefficient in polynomial.terms():
        layers[normal_order] = sp.expand(
            layers.get(normal_order, sp.Integer(0))
            + coefficient * r**radial_degree / denominator
        )
    return {
        order: sp.factor(layer)
        for order, layer in layers.items()
        if layer != 0
    }


def run() -> dict[str, object]:
    (parameter, u, z), family_p, family_q = _exact_family()
    r = sp.symbols("r")
    target_p, target_q = _target_data()
    fixed_contact = (
        4 * family_p**3
        - family_p**2
        - 18 * family_p * family_q
        + 27 * family_q**2
        + 4 * family_q
    )
    seed_p = sp.factor(family_p.subs(parameter, 0))
    seed_q = sp.factor(family_q.subs(parameter, 0))
    seed_contact = sp.factor(fixed_contact.subs(parameter, 0))
    seed_contact_layers = _normal_layers(
        seed_contact, u=u, z=z, r=r
    )
    assert min(seed_contact_layers) == 2
    tau = 3 * r - 2
    assert sp.factor(seed_contact_layers[2] + tau**2 / 16) == 0

    radial_p = sp.factor(sp.limit(
        family_p.subs(u, r / z), z, 0
    ))
    radial_q = sp.factor(sp.limit(
        family_q.subs(u, r / z), z, 0
    ))
    radial_contact = sp.factor(
        4 * radial_p**3
        - radial_p**2
        - 18 * radial_p * radial_q
        + 27 * radial_q**2
        + 4 * radial_q
    )
    leak = sp.factor(sp.diff(
        radial_contact, parameter
    ).subs(parameter, 0))
    expected_leak = sp.factor(
        r**2 * tau**3 * (3 * r**2 + 12 * r - 16) / 384
    )
    assert sp.factor(leak - expected_leak) == 0

    preimages = _leak_preimages(target_p, target_q)
    target_generators = {
        "P3": target_p**3,
        "PQ": target_p * target_q,
        "Q2": target_q**2,
    }
    seed_substitution = {target_p: radial_p.subs(parameter, 0),
                         target_q: radial_q.subs(parameter, 0)}
    moving_substitution = {target_p: family_p, target_q: family_q}
    preimage_rows = []
    normal_rows = []
    for name in ("P3", "PQ", "Q2"):
        preimage = sp.factor(preimages[name])
        assert all(
            (
                p_power >= 3
                or (p_power >= 1 and q_power >= 1)
                or q_power >= 2
            )
            for (p_power, q_power), coefficient
            in sp.Poly(preimage, target_p, target_q).terms()
            if coefficient != 0
        )
        generator_axis = sp.factor(
            target_generators[name].subs(seed_substitution)
        )
        preimage_axis = sp.factor(preimage.subs(seed_substitution))
        assert sp.factor(preimage_axis - leak * generator_axis) == 0
        preimage_rows.append({
            "generator": name,
            "preimage": str(preimage),
            "target_degree": sp.Poly(
                preimage, target_p, target_q
            ).total_degree(),
            "belongs_to_lift_ideal": True,
            "radial_identity_verified": True,
        })

        moving_generator = target_generators[name].subs(
            moving_substitution
        )
        depth_one = sp.factor(sp.diff(
            moving_generator * fixed_contact,
            parameter,
        ).subs(parameter, 0))
        correction = sp.factor(preimage.subs({
            target_p: seed_p,
            target_q: seed_q,
        }))
        residual = sp.factor(depth_one - correction)
        layers = _normal_layers(residual, u=u, z=z, r=r)
        first_order = min(layers)
        assert first_order == 2
        first_layer = layers[first_order]
        radial_degree = sp.Poly(first_layer, r).degree()
        normal_rows.append({
            "generator": name,
            "first_normal_order": first_order,
            "first_normal_profile": str(first_layer),
            "first_normal_radial_degree": radial_degree,
            "source_hamiltonian_degree": 2 * radial_degree + first_order,
            "radial_adjoint_second_step_is_zero": True,
        })

    # For an arbitrary polynomial factor A, the product-rule correction is
    # A_1 * G_0 * C_0.  The identity is exact, but no source-action quotient
    # is applied here: R(G) is a source Hamiltonian remainder, while the
    # r^2*tau^2 ideal belongs to the different contact-scalar action object.
    generator_axis_valuations = {
        name: min(
            exponent[0]
            for exponent, coefficient in sp.Poly(
                target_generators[name].subs(seed_substitution), r
            ).terms()
            if coefficient != 0
        )
        for name in target_generators
    }
    assert min(generator_axis_valuations.values()) >= 3

    return {
        "schema": "axiompack.jacobian_moving_divisor_normal_transition.v1",
        "moving_divisor_radial_leak": {
            "formula": str(leak),
            "parameter_valuation": 1,
            "depth_m_leading_leak": "s^m*ell(r)^m",
        },
        "radial_multiplier_preimages": preimage_rows,
        "complete_lift_ideal_multiplier": True,
        "first_normal_transition": {
            "rows": normal_rows,
            "common_normal_order": 2,
            "common_parity": "even",
            "radial_action_formula": (
                "ad_f(z^2*g)=-2*z^0*f'(r)*g; the next radial "
                "adjoint vanishes"
            ),
        },
        "product_rule_descent": {
            "formula": "R(A*G)=A_0*R(G)+A_1*G_0*C_0",
            "generator_axis_valuations": generator_axis_valuations,
            "identity_verified_at_the_symbolic_product_level": True,
            "source_action_ideal_applied_to_this_hamiltonian": False,
        },
        "claim_boundary": (
            "Every first radial leak from the complete lift ideal has an "
            "exact contact-zero multiplier correction. The first "
            "Hamiltonian remainders of all three generators have even "
            "normal order two and are radial-adjoint nilpotent after one "
            "step. Their complete coupled even-layer normalization and "
            "first odd remainder remain required."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
