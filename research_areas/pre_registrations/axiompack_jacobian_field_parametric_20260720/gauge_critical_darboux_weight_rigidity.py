#!/usr/bin/env python3
"""Exact stress tests for the critical Darboux-weight obstruction.

The proposed all-degree argument classifies persistent factors for the total
derivation

    D = d/dt + c(t) p(Y) d/dY + L(t) F d/dF.

Two distinct ``F`` weights in one Darboux factor would give a rational
eigenratio ``D0(r) = k L r``.  Because ``Y**2`` divides ``p``, removing the
``Y`` valuation and specializing at ``Y=0`` gives a rational logarithmic
derivative ``s'/s = k L``.  The certified irrational residue of ``L`` rules
this out for every nonzero integer ``k``.

This replay checks the exact critical input, the generic low-degree
saturation algebra, the finite multiplicity drop, and two sharp negative
controls.  The universal factor theorem remains a mathematical/Lean theorem;
the finite symbolic rows below are adversarial tests rather than its proof.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_critical_monodromy_residue import (  # noqa: E402
    build_certificate as build_residue_certificate,
)


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _coefficient_gcd_in_hidden(
    expression: sp.Expr,
    visible: sp.Symbol,
    hidden: sp.Symbol,
    domain: sp.Domain,
) -> sp.Expr:
    coefficients = sp.Poly(expression, visible).all_coeffs()
    result = sp.Poly(coefficients[0], hidden, domain=domain)
    for coefficient in coefficients[1:]:
        result = sp.gcd(
            result,
            sp.Poly(coefficient, hidden, domain=domain),
        )
    return sp.factor(result.monic().as_expr())


def _finite_multiplicity_descent() -> dict[str, object]:
    visible, hidden = sp.symbols("F Y")
    relation = (hidden - visible) ** 3 * (hidden + 1) ** 2

    def derivation(expression: sp.Expr) -> sp.Expr:
        return sp.expand(
            visible * sp.diff(expression, visible)
            + hidden**2 * sp.diff(expression, hidden)
        )

    coefficient_field = sp.QQ.frac_field(visible)
    running_gcd = sp.Poly(relation, hidden, domain=coefficient_field)
    iterate = relation
    rows = []
    for order in range(1, 4):
        iterate = derivation(iterate)
        running_gcd = sp.gcd(
            running_gcd,
            sp.Poly(iterate, hidden, domain=coefficient_field),
        )
        rows.append(
            {
                "order": order,
                "gcd": str(sp.factor(running_gcd.monic().as_expr())),
                "hidden_degree": int(running_gcd.degree()),
            }
        )
    assert [row["hidden_degree"] for row in rows] == [3, 1, 0]
    assert running_gcd.degree() == 0
    return {
        "relation": str(sp.factor(relation)),
        "derivation": "F*d/dF + Y^2*d/dY",
        "rows": rows,
        "gcd_one_by_max_factor_multiplicity": True,
    }


def build_certificate() -> dict[str, object]:
    t, residue = sp.symbols("t residue")
    visible, hidden = sp.symbols("F Y")
    a2, a3, b2, b3, b4, driver, log_velocity = sp.symbols(
        "a2 a3 b2 b3 b4 c L"
    )

    residue_certificate = build_residue_certificate()
    pole_polynomial = sp.sympify(
        residue_certificate["degree_seven_pole_polynomial"],
        locals={"t": t},
    )
    residue_polynomial = sp.sympify(
        residue_certificate["residue_polynomial"],
        locals={"residue": residue},
    )
    assert sp.Poly(pole_polynomial, t, domain=sp.QQ).is_irreducible
    assert sp.Poly(
        residue_polynomial, residue, domain=sp.QQ
    ).is_irreducible
    assert sp.degree(residue_polynomial, residue) == 7

    # Generic tangent generators.  The coefficient gcd of the raw separated
    # relation is exactly their forced common Y^2 equilibrium factor; after
    # cancellation no F-independent hidden divisor remains.
    inner = hidden**2 * (a2 + a3 * hidden)
    outer = hidden**2 * (b2 + b3 * hidden + b4 * hidden**2)
    outer_visible = sp.expand(outer.subs(hidden, visible))
    relation = sp.expand(
        driver * outer_visible * inner
        - log_velocity * visible * outer
    )
    coefficient_domain = sp.QQ.frac_field(
        a2, a3, b2, b3, b4, driver, log_velocity
    )
    raw_common = _coefficient_gcd_in_hidden(
        relation, visible, hidden, coefficient_domain
    )
    saturated_relation = sp.cancel(relation / hidden**2)
    saturated_common = _coefficient_gcd_in_hidden(
        saturated_relation, visible, hidden, coefficient_domain
    )
    assert raw_common == hidden**2
    assert saturated_common == 1

    # Nonproportional common-factor adversary.  Persistence belongs to the
    # common-equilibrium saturation, not to a proportionality conclusion.
    adversary_inner = hidden**2 * (hidden - 1)
    adversary_outer = hidden**2 * (hidden - 1) * (hidden - 2)
    adversary_outer_visible = adversary_outer.subs(hidden, visible)
    adversary_relation = sp.expand(
        driver * adversary_outer_visible * adversary_inner
        - log_velocity * visible * adversary_outer
    )
    adversary_domain = sp.QQ.frac_field(driver, log_velocity)
    adversary_common = _coefficient_gcd_in_hidden(
        adversary_relation, visible, hidden, adversary_domain
    )
    assert adversary_common == hidden**2 * (hidden - 1)
    assert sp.cancel(adversary_inner / adversary_outer) == 1 / (hidden - 2)

    # Negative control 1: rational residue.  With rho=1/2 and weight k=2,
    # s=t is an exact rational eigenfunction.
    rational_residue = sp.Rational(1, 2)
    rational_weight = 2
    rational_solution = t
    assert sp.cancel(
        sp.diff(rational_solution, t) / rational_solution
        - rational_weight * rational_residue / t
    ) == 0

    # Negative control 2: if the invariant divisor has only a simple zero,
    # the Y-specialization argument fails.  The rational eigenfunction r=Y
    # survives for D0=d/dt+(rho/t)Y*d/dY.
    simple_zero_eigenfunction = hidden
    simple_zero_residual = sp.cancel(
        sp.diff(simple_zero_eigenfunction, t)
        + residue / t * hidden
        * sp.diff(simple_zero_eigenfunction, hidden)
        - residue / t * simple_zero_eigenfunction
    )
    assert simple_zero_residual == 0

    descent = _finite_multiplicity_descent()
    core: dict[str, object] = {
        "schema": "axiompack.critical_darboux_weight_rigidity.v1",
        "total_derivation": (
            "D=d/dt+c(t)*p(Y)*d/dY+L(t)*F*d/dF"
        ),
        "critical_residue_certificate_sha256": residue_certificate[
            "certificate_sha256"
        ],
        "critical_residue_minimal_polynomial_degree": 7,
        "critical_residue_irrational": True,
        "rational_logarithmic_derivative_residues_integral": True,
        "nonzero_integer_weight_times_residue_not_integral": True,
        "candidate_eigenratio_equation": "D0(r)=(j-i)*L*r",
        "invariant_divisor": "Y=0",
        "double_zero_specialization": (
            "after removing ord_Y(r), p(Y)/Y vanishes at Y=0 and "
            "the unit s(t)=r/Y^ord_Y(r)|_(Y=0) obeys "
            "s'/s=(j-i)L"
        ),
        "generic_tangent_saturation": {
            "inner_degree": 3,
            "outer_degree": 4,
            "raw_F_coefficient_gcd_in_Y": str(raw_common),
            "saturated_F_coefficient_gcd_in_Y": str(saturated_common),
            "only_forced_common_divisor_removed": True,
        },
        "nonproportional_common_factor_adversary": {
            "inner": str(sp.factor(adversary_inner)),
            "outer": str(sp.factor(adversary_outer)),
            "ratio": str(
                sp.cancel(adversary_inner / adversary_outer)
            ),
            "persistent_common_divisor": str(adversary_common),
            "proportionality_inference_rejected": True,
        },
        "finite_multiplicity_descent": descent,
        "negative_controls": {
            "rational_residue": {
                "residue": str(rational_residue),
                "weight": rational_weight,
                "solution": str(rational_solution),
                "eigen_equation_verified": True,
            },
            "simple_zero_generator": {
                "generator": "p(Y)=Y",
                "eigenfunction": str(simple_zero_eigenfunction),
                "eigen_equation_verified": True,
            },
        },
        "universal_consequence": (
            "A persistent irreducible factor with two visible weights would "
            "create a forbidden rational eigenratio. Every surviving "
            "F-independent factor of the coupled relation divides both "
            "generators and belongs to common-equilibrium saturation."
        ),
        "claim_boundary": (
            "Exact critical-input and adversarial stress replay for the "
            "Darboux-weight mechanism. The universal factor theorem, "
            "selected-branch saturation cancellation, finite Bezout "
            "eliminant, and monodromy binding still require proof."
        ),
    }
    return {**core, "certificate_sha256": _sha256(core)}


if __name__ == "__main__":
    print(json.dumps(build_certificate(), indent=2, sort_keys=True))
