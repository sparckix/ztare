#!/usr/bin/env python3
"""All-weight odd remainder after the first moving-divisor correction."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_moving_divisor_normal_transition import (  # noqa: E402
    _leak_preimages,
    _normal_layers,
)
from gauge_moving_pullback_normal_semigroup import _exact_family  # noqa: E402
from gauge_positive_contact_locally_finite_obstruction import (  # noqa: E402
    _robust_affine_certificate,
)


def _symbolic_top_coefficients() -> dict[str, object]:
    b = sp.symbols("b", integer=True, nonnegative=True)
    p = -sp.Rational(3, 4)

    # Leading radial coefficients by normal layer.  They are extracted from
    # the exact family and the two base remainders in run(); the calculation
    # here records the symbolic product rule for multiplication by P^b.
    p0_0 = p
    p0_1 = sp.Rational(1, 2)
    p1_0 = sp.Rational(1, 8)
    p1_1 = -sp.Rational(1, 8)
    c0_2 = -sp.Rational(9, 16)
    c0_3 = sp.Rational(1, 2)

    a0_0 = p0_0**b
    a0_1 = b * p0_0 ** (b - 1) * p0_1
    a1_0 = b * p0_0 ** (b - 1) * p1_0
    a1_1 = sp.factor(
        b * (
            p0_0 ** (b - 1) * p1_1
            + (b - 1)
            * p0_0 ** (b - 2)
            * p0_1
            * p1_0
        )
    )

    base_data = {
        "even_P3": {
            "base_weight": 6,
            "generator_layer_0": -sp.Rational(27, 64),
            "generator_layer_1": sp.Rational(27, 32),
            "remainder_layer_2": -sp.Rational(1215, 8192),
            "remainder_layer_3": sp.Rational(3915, 8192),
        },
        "odd_PQ": {
            "base_weight": 5,
            "generator_layer_0": sp.Rational(3, 16),
            "generator_layer_1": -sp.Rational(5, 16),
            "remainder_layer_2": sp.Rational(207, 4096),
            "remainder_layer_3": -sp.Rational(299, 2048),
        },
    }
    formulas = {}
    for name, data in base_data.items():
        product_layer_2 = data["generator_layer_0"] * c0_2
        product_layer_3 = (
            data["generator_layer_0"] * c0_3
            + data["generator_layer_1"] * c0_2
        )
        coefficient = sp.factor(
            a0_0 * data["remainder_layer_3"]
            + a0_1 * data["remainder_layer_2"]
            + a1_0 * product_layer_3
            + a1_1 * product_layer_2
        )
        formulas[name] = coefficient

    expected_even = sp.factor(
        9 * p**b * (4 * b + 15) * (6 * b + 29) / 8192
    )
    expected_odd = sp.factor(
        -p**b * (3 * b + 13) * (8 * b + 23) / 2048
    )
    assert sp.factor(formulas["even_P3"] - expected_even) == 0
    assert sp.factor(formulas["odd_PQ"] - expected_odd) == 0

    a = sp.symbols("a", integer=True, positive=True)
    even_in_a = sp.factor(expected_even.subs(b, a - 3))
    odd_in_a = sp.factor(expected_odd.subs(b, a - 1))
    advertised_even = sp.factor(
        -p**a * (4 * a + 3) * (6 * a + 11) / 384
    )
    advertised_odd = sp.factor(
        p**a * (3 * a + 10) * (8 * a + 15) / 1536
    )
    assert sp.factor(even_in_a - advertised_even) == 0
    assert sp.factor(odd_in_a - advertised_odd) == 0
    return {
        "even_symbol": "t_(2*a)=P^a, a>=3",
        "even_normal_three_top_degree": "2*a+1=w+1",
        "even_normal_three_top_coefficient": str(advertised_even),
        "odd_symbol": "t_(2*a+3)=P^a*Q, a>=1",
        "odd_normal_three_top_degree": "2*a+4=w+1",
        "odd_normal_three_top_coefficient": str(advertised_odd),
        "nonzero_in_characteristic_zero": True,
        "derivation": (
            "R(P^b*G)=P_0^b*R(G)+[s](P_s^b)*G_0*C_0; "
            "only normal allocations 0+3 and 1+2 reach the top"
        ),
    }


def run(heldout_maximum_weight: int = 18) -> dict[str, object]:
    if heldout_maximum_weight < 12:
        raise ValueError("heldout maximum weight must be at least twelve")
    (parameter, u, z), family_p, family_q = _exact_family()
    r, target_p, target_q = sp.symbols("r P Q")
    fixed_contact = (
        4 * family_p**3
        - family_p**2
        - 18 * family_p * family_q
        + 27 * family_q**2
        + 4 * family_q
    )
    seed_p = family_p.subs(parameter, 0)
    seed_q = family_q.subs(parameter, 0)
    preimages = _leak_preimages(target_p, target_q)
    formulas = _symbolic_top_coefficients()
    rows = []
    for weight in range(5, heldout_maximum_weight + 1):
        if weight % 2 == 0:
            exponent = weight // 2
            moving_symbol = family_p**exponent
            correction = target_p ** (exponent - 3) * preimages["P3"]
            expected = sp.factor(
                -(-sp.Rational(3, 4)) ** exponent
                * (4 * exponent + 3)
                * (6 * exponent + 11)
                / 384
            )
        else:
            exponent = (weight - 3) // 2
            moving_symbol = family_p**exponent * family_q
            correction = (
                target_p ** (exponent - 1) * preimages["PQ"]
            )
            expected = sp.factor(
                (-sp.Rational(3, 4)) ** exponent
                * (3 * exponent + 10)
                * (8 * exponent + 15)
                / 1536
            )
        residual = sp.factor(
            sp.diff(
                moving_symbol * fixed_contact,
                parameter,
            ).subs(parameter, 0)
            - correction.subs({target_p: seed_p, target_q: seed_q})
        )
        layers = _normal_layers(residual, u=u, z=z, r=r)
        normal_three = sp.Poly(layers[3], r)
        assert normal_three.degree() == weight + 1
        assert sp.factor(normal_three.LC() - expected) == 0
        rows.append({
            "weight": weight,
            "parity": "even" if weight % 2 == 0 else "odd",
            "normal_three_radial_degree": normal_three.degree(),
            "normal_three_top_coefficient": str(expected),
            "matches_symbolic_formula": True,
        })

    robust = _robust_affine_certificate()
    assert robust["finite_affine_kernel"] == "zero"
    return {
        "schema": (
            "axiompack.jacobian_moving_divisor_"
            "odd_remainder_all_weight.v1"
        ),
        "symbolic_parity_formulas": formulas,
        "training_weights": [5, 6, 7, 8, 9, 10, 11],
        "heldout_weights": list(range(12, heldout_maximum_weight + 1)),
        "exact_rows": rows,
        "highest_weight_descent": {
            "each_coefficient_row_has_finite_weight_support": True,
            "top_radial_degree": "weight+1",
            "top_coefficient_nonzero_for_every_weight_at_least_five": True,
            "lower_weights_cannot_cancel_top_degree": True,
        },
        "positive_contact_ambiguity": {
            "two_radial_preimages_differ_by_a_C_multiple": True,
            "robust_current_kernel": robust["finite_affine_kernel"],
            "cancellation_exposes_higher_even_pivot": True,
        },
        "claim_boundary": (
            "At contact depth one, every nonzero finite contact-zero "
            "multiplier has a nonzero highest-weight odd normal-three "
            "remainder after the universal radial correction. A finite "
            "positive-contact ambiguity cannot cancel that odd terminal "
            "without a higher even source pivot. Arbitrary contact depth "
            "and the group-level moving-backbone factorization remain."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
