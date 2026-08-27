#!/usr/bin/env python3
"""Exact irrational-residue certificate for the critical scalar holonomy.

The certificate proves that the rationalized logarithmic differential has
an algebraic irrational residue.  The standard complex-exponential kernel
then gives an infinite-order monodromy multiplier.  Transfer of that loop to
the two factor branches remains a separate continuation theorem.
"""

from __future__ import annotations

import hashlib
import json

import sympy as sp


def build_certificate() -> dict[str, object]:
    x, t, residue = sp.symbols("x t residue")

    discriminant = 36 + 12 * x - 3 * x**2
    rational_velocity = (
        21 * x**6
        - 124 * x**5
        + 456 * x**4
        - 2048 * x**3
        - 6768 * x**2
        + 22464 * x
        + 44928
    ) / (896 * x**3 * (x - 4) * (x**2 - 4 * x - 8))
    radical_velocity = (
        (x - 6)
        * (x + 2)
        * (7 * x**3 - 42 * x**2 + 624)
    ) / (896 * x**3 * (x - 4) * (x**2 - 4 * x - 8))

    x_of_t = 6 * (t**2 - 1) / (t**2 + 3)
    radical_of_t = 24 * t / (t**2 + 3)
    assert sp.cancel(
        discriminant.subs(x, x_of_t) - radical_of_t**2
    ) == 0
    assert sp.cancel(x_of_t.subs(t, 1)) == 0
    assert sp.cancel(x_of_t.subs(t, 0)) == -2

    velocity_of_t = sp.cancel(
        rational_velocity.subs(x, x_of_t)
        + radical_velocity.subs(x, x_of_t) * radical_of_t
    )
    logarithmic_differential = sp.cancel(
        sp.diff(x_of_t, t)
        / (x_of_t * (1 + 2 * x_of_t * velocity_of_t))
    )

    pole_polynomial = (
        199 * t**7
        - 1393 * t**6
        + 67 * t**5
        + 219 * t**4
        + 5973 * t**3
        + 10125 * t**2
        + 10593 * t
        + 2889
    )
    numerator = 896 * t * (t - 3) * (t + 1) * (t**2 - 6 * t - 3)
    expected_differential = sp.cancel(
        numerator / ((t - 1) * pole_polynomial)
    )
    assert sp.cancel(logarithmic_differential - expected_differential) == 0
    assert sp.gcd(pole_polynomial, sp.diff(pole_polynomial, t)) == 1
    assert sp.gcd(pole_polynomial, numerator) == 1
    assert sp.gcd(pole_polynomial, t - 1) == 1

    pole_mod_17 = sp.factor_list(pole_polynomial, modulus=17)
    assert pole_mod_17 == (
        -5,
        [
            (
                t**7
                - 7 * t**6
                + 7 * t**5
                - 3 * t**4
                - 8 * t**3
                - 2 * t**2
                + 3 * t
                + 7,
                1,
            )
        ],
    )
    assert sp.Poly(pole_polynomial, t, domain=sp.QQ).is_irreducible

    # At a root a of Q, the residue is N(a)/((a-1)Q'(a)).
    # Elimination of a gives the following primitive polynomial for rho.
    residue_polynomial = (
        -5328693312 * residue**7
        - 5328693312 * residue**6
        + 4562281392 * residue**5
        + 2967370224 * residue**4
        - 2078539001 * residue**3
        - 227127817 * residue**2
        + 19332313 * residue
        - 77175
    )
    resultant = sp.resultant(
        pole_polynomial,
        numerator - residue * (t - 1) * sp.diff(pole_polynomial, t),
        t,
    )
    resultant_scale = sp.Integer(
        1812753999073575238461334898444686671740928
    )
    assert sp.expand(resultant - resultant_scale * residue_polynomial) == 0

    residue_mod_17 = sp.factor_list(residue_polynomial, modulus=17)
    assert residue_mod_17 == (
        4,
        [
            (
                residue**7
                + residue**6
                + 7 * residue**5
                + 7 * residue**4
                + 4 * residue**3
                + 5 * residue**2
                + 8 * residue
                - 3,
                1,
            )
        ],
    )
    assert sp.Poly(
        residue_polynomial, residue, domain=sp.QQ
    ).is_irreducible
    assert sp.degree(residue_polynomial, residue) == 7

    certificate: dict[str, object] = {
        "schema": "axiompack.critical_monodromy_residue.v1",
        "claim_boundary": (
            "infinite-order scalar-holonomy monodromy; factor-continuation "
            "loop transfer remains open"
        ),
        "quadratic_sheet": "w^2=36+12*x-3*x^2",
        "rational_parameterization": {
            "x": str(x_of_t),
            "w": str(radical_of_t),
            "normalization_t": 1,
            "critical_t": 0,
        },
        "logarithmic_differential": str(sp.factor(logarithmic_differential)),
        "degree_seven_pole_polynomial": str(pole_polynomial),
        "pole_squarefree": True,
        "pole_coprime_to_numerator_and_endpoints": True,
        "pole_irreducible_over_Q": True,
        "pole_irreducibility_prime": 17,
        "pole_mod_17_monic_factor": str(pole_mod_17[1][0][0]),
        "residue_polynomial": str(residue_polynomial),
        "residue_resultant_scale": str(resultant_scale),
        "residue_polynomial_degree": 7,
        "residue_irreducible_over_Q": True,
        "residue_irreducibility_prime": 17,
        "residue_mod_17_monic_factor": str(residue_mod_17[1][0][0]),
        "residue_is_algebraic_irrational": True,
        "monodromy_multiplier": "exp(2*pi*i*residue)",
        "monodromy_multiplier_has_infinite_order": True,
        "monodromy_argument": (
            "a positive torsion power would put the residue in Q by the "
            "kernel of complex exp, contradicting degree-seven "
            "irreducibility"
        ),
        "global_residual": (
            "lift repeated scalar loops through an arbitrary selected "
            "two-flow factorization; finite iterates enter a fixed finite "
            "equilibrium set, while any nonfinite iterate enters the "
            "ratified ramified-cross-carrier sink"
        ),
    }
    payload = json.dumps(certificate, sort_keys=True, separators=(",", ":"))
    certificate["certificate_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
    return certificate


if __name__ == "__main__":
    print(json.dumps(build_certificate(), indent=2, sort_keys=True))
