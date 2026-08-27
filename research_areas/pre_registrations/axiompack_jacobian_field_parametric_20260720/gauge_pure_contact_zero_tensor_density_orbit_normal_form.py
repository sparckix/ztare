#!/usr/bin/env python3
"""Critical tensor-density orbit normal form for the July family.

The split critical source residual is row-indexed as ``K=x*C``, where ``C``
is a standard weight-3/2 tensor density.  If ``K=c*x*v`` with ``v(0)=1``,
the corrected target action sends the finite representative ``c*x`` to
``K`` as soon as ``phi'=v**(-2/3)``.  The reusable primitive constructs this
formal diffeomorphism and checks the squared action identity exactly.

This closes the critical-quotient orbit question.  It does not lift the
conjugator through the full normal/contact filtration.
"""

from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
SRC_ROOT = HERE.parents[2] / "src"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gauge_pure_contact_zero_tensor_density_holonomy import (  # noqa: E402
    run as holonomy_run,
)
from ztare.common.formal_tensor_density import (  # noqa: E402
    normalize_split_tensor_residual,
)
from ztare.common.formal_power_series import iterative_logarithm  # noqa: E402


def _fraction(value: sp.Expr) -> Fraction:
    rational = sp.Rational(value)
    return Fraction(int(rational.p), int(rational.q))


def _display(values: tuple[Fraction, ...]) -> list[str]:
    return [str(value) for value in values]


def run(verification_rows: int = 8) -> dict[str, object]:
    if verification_rows < 6:
        raise ValueError("orbit replay needs at least six critical rows")

    holonomy = holonomy_run(verification_rows)
    x = sp.symbols("x")
    residual = sp.expand(sp.sympify(
        holonomy["abelian_source_residual"]["series_prefix"]
    ))
    coefficients = tuple(
        _fraction(residual.coeff(x, order))
        for order in range(verification_rows + 1)
    )
    normal_form = normalize_split_tensor_residual(
        coefficients,
        verification_rows,
    )
    assert normal_form.leading_coefficient == Fraction(-1, 144)
    assert normal_form.diffeomorphism[0] == 0
    assert normal_form.diffeomorphism[1] == 1
    assert normal_form.verified
    dlog = iterative_logarithm(
        normal_form.diffeomorphism,
        verification_rows,
    )
    assert dlog.verified

    # Verify that C=K/x converts the exact row-indexed action to the standard
    # weight-3/2 Lie derivative.
    actor = sp.Function("A")(x)
    module = sp.Function("K")(x)
    vector = 2 * x * actor
    density = module / x
    row_action = (
        2 * x * actor * sp.diff(module, x)
        - 3 * x * sp.diff(actor, x) * module
        - 5 * actor * module
    )
    standard_action = (
        vector * sp.diff(density, x)
        - sp.Rational(3, 2) * sp.diff(vector, x) * density
    )
    assert sp.simplify(standard_action - row_action / x) == 0

    payload = {
        "schema": (
            "axiompack.jacobian_pure_contact_zero_"
            "tensor_density_orbit_normal_form.v1"
        ),
        "critical_residual": {
            "leading_coefficient": str(normal_form.leading_coefficient),
            "valuation": 1,
            "coefficients": _display(normal_form.residual),
        },
        "density_identification": {
            "standard_density": "C=K/x",
            "witt_vector": "f=2*x*A",
            "standard_action": "f*C'-(3/2)*f'*C",
            "row_action": "2*x*A*K'-3*x*A'*K-5*A*K",
            "infinitesimal_conversion_verified": True,
        },
        "corrected_finite_action": (
            "T_phi(K)=x*K(phi)/(phi*(phi')^(3/2))"
        ),
        "normal_form": {
            "finite_representative": "(-1/144)*x",
            "unit_power": "v^(-2/3)",
            "diffeomorphism_equation": "phi'=v^(-2/3), phi(0)=0",
            "diffeomorphism_coefficients": _display(
                normal_form.diffeomorphism
            ),
            "squared_orbit_identity": "K^2*(phi')^3=c^2*x^2",
            "squared_orbit_residual": _display(
                normal_form.squared_orbit_residual
            ),
            "typed_replay_rows": verification_rows,
            "all_order_denominators": (
                "positive integers from rational-power recurrence and "
                "coefficientwise integration"
            ),
            "verified": True,
        },
        "iterative_logarithm_diagnostic": {
            "coefficients": _display(dlog.generator),
            "last_nonzero_replay_order": (
                dlog.last_nonzero_generator_order
            ),
            "time_one_roundtrip": True,
            "polynomiality_decided": False,
        },
        "consequence": {
            "critical_residual_has_formal_linear_normal_form": True,
            "finite_target_critical_support_required": False,
            "polynomial_source_factor_constructed": False,
            "full_contact_schedule_constructed": False,
            "next_obligation": (
                "decide whether the normalizing diffeomorphism has a finite "
                "polynomial iterative logarithm, then classify all finite "
                "polynomial tensor-residual representatives"
            ),
        },
        "claim_boundary": (
            "The complete critical tensor-density residual is formally in "
            "the orbit of its linear monomial under a tangent formal "
            "diffeomorphism. The conjugator is not asserted to have a "
            "polynomial iterative logarithm, so no polynomial source factor, "
            "full contact, or minimax value is asserted."
        ),
    }
    payload["certificate_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
