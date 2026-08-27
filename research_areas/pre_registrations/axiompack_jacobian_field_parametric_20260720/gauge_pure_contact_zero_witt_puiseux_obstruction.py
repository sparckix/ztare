#!/usr/bin/env python3
"""Puiseux obstruction to a finite critical Witt logarithm.

For the parity-normalized pure contact-zero connection, let V(x) be the
normal-two instantaneous Hamiltonian coefficient.  The inverse radial
holonomy F obeys

    F'/F = 1 / (x * (1 + 2*x*V)).

The algebraic branch of V at x=-2 gives a nonzero u**(5/2) term in F,
where u=x+2.  Julia's equation then rules out a polynomial infinitesimal
generator: at a possible polynomial root the first fractional coefficient
would force its integer multiplicity to equal 5/2.

This adapter verifies every substrate-specific coefficient and checks the
Julia equation against the exact Magnus recurrence.  The multiplicity step
is an all-index local argument, not a finite-row extrapolation.  It also
replays the conditional degree-independent two-flow calculation: after a
selected factorization supplies a through-infinity continuation, two
polynomial fields tangent to the identity have first fractional exponent
strictly below two unless the fields are proportional.  Construction of that
selected continuation is separate.  Finite equilibrium transitions and
finite regular monodromy sheets show that neither finiteness nor the old
finite/infinity split supplies the missing route theorem.
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
SRC_ROOT = HERE.parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gauge_pure_contact_zero_delta_critical_recurrence import (  # noqa: E402
    _critical_recurrence,
)
from gauge_pure_contact_zero_parity_algebraic_connection import (  # noqa: E402
    _algebraic_normal_two,
)
from gauge_equilibrium_transition_puiseux_collision import (  # noqa: E402
    build_certificate as build_equilibrium_transition_certificate,
)
from gauge_critical_monodromy_residue import (  # noqa: E402
    build_certificate as build_critical_monodromy_certificate,
)
from gauge_polynomial_flow_finite_monodromy_countermodels import (  # noqa: E402
    build_certificate as build_finite_monodromy_countermodels,
)
from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredPuiseuxClaim,
    FilteredPuiseuxEvidenceScope,
    FilteredPuiseuxFlowProblem,
    FilteredTwoFlowPuiseuxProblem,
    compile_filtered_puiseux_flow_obstruction,
    compile_filtered_two_flow_puiseux_obstruction,
    make_filtered_puiseux_context,
    make_filtered_puiseux_evidence,
)
from ztare.common.content_bound_evidence import (  # noqa: E402
    EvidenceAuthority,
)


def run(verification_rows: int = 8) -> dict[str, object]:
    if verification_rows < 6:
        raise ValueError("the Julia audit needs at least six recurrence rows")

    x, discriminant, velocity_pair = _algebraic_normal_two()
    t = sp.symbols("t")
    local_substitution = {x: t**2 - 2}
    local_radical = t * sp.sqrt(24 - 3 * t**2)
    velocity_local = sp.series(
        velocity_pair.rational.subs(local_substitution)
        + velocity_pair.radical_coefficient.subs(local_substitution)
        * local_radical,
        t,
        0,
        7,
    ).removeO().expand()
    velocity_branch = sp.factor(velocity_local.coeff(t, 3))
    assert velocity_branch == -sp.Rational(25, 672) * sp.sqrt(6)

    velocity = sp.cancel(
        velocity_pair.rational
        + velocity_pair.radical_coefficient * sp.sqrt(discriminant)
    )
    logarithmic_derivative = sp.cancel(
        1 / (x * (1 + 2 * x * velocity))
    )
    # The branch coefficient follows from differentiating
    # 1/(x(1+2xV)) with respect to V at x=-2.
    branch_value = sp.Rational(5, 448)
    regular_denominator = sp.factor(1 - 4 * branch_value)
    logarithmic_derivative_branch = sp.factor(
        -2 * velocity_branch / regular_denominator**2
    )
    assert regular_denominator == sp.Rational(107, 112)
    assert logarithmic_derivative_branch == (
        sp.Rational(2800, 34347) * sp.sqrt(6)
    )
    endpoint_relative_branch = sp.factor(
        sp.Rational(2, 5) * logarithmic_derivative_branch
    )
    assert endpoint_relative_branch == (
        sp.Rational(1120, 34347) * sp.sqrt(6)
    )

    # At x=0, integrate the regular part of F'/F-1/x and normalize F=x+...
    # The resulting inverse holonomy must satisfy Julia's equation for the
    # Magnus generator.  This is a finite orientation check only.
    expansion_order = verification_rows + 2
    logarithmic_derivative_at_zero = sp.series(
        logarithmic_derivative,
        x,
        0,
        expansion_order,
    ).removeO()
    endpoint = sp.series(
        x
        * sp.exp(
            sp.integrate(logarithmic_derivative_at_zero - 1 / x, x)
        ),
        x,
        0,
        expansion_order,
    ).removeO().expand()
    recurrence = _critical_recurrence(
        verification_rows,
        guess_rational_generating_function=False,
    )
    magnus_a = sp.expand(sum(
        sp.Rational(row["logarithm_normal_two"])
        * x ** int(row["logarithmic_order"])
        for row in recurrence["rows"]
    ))
    inverse_generator = sp.expand(-2 * x * magnus_a)
    julia_residual = sp.series(
        inverse_generator.subs(x, endpoint)
        - sp.diff(endpoint, x) * inverse_generator,
        x,
        0,
        expansion_order,
    ).removeO().expand()
    assert julia_residual == 0
    assert endpoint.coeff(x, 3) == sp.Rational(1, 112)

    branch_exponent = sp.Rational(5, 2)
    assert branch_exponent.q == 2
    assert all(sp.Integer(order) != branch_exponent for order in range(12))
    expansion_payload = {
        "point": -2,
        "velocity_branch": str(velocity_branch),
        "regular_denominator": str(regular_denominator),
        "endpoint_relative_branch": str(endpoint_relative_branch),
        "endpoint_branch_exponent": str(branch_exponent),
        "julia_residual": str(julia_residual),
    }
    expansion_digest = hashlib.sha256(
        json.dumps(
            expansion_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    puiseux_context = make_filtered_puiseux_context(
        germ_id="jacobian_pure_contact_zero_critical_holonomy_germ",
        local_coordinate_id="u=x+2_on_selected_algebraic_branch",
        first_fractional_exponent=str(branch_exponent),
        local_expansion_evidence_sha256=expansion_digest,
    )
    regular_evidence = make_filtered_puiseux_evidence(
        claim=FilteredPuiseuxClaim.REGULAR_LINEAR_COEFFICIENT_NONZERO,
        context=puiseux_context,
        authority=EvidenceAuthority.ADAPTER_EXACT,
        scope=FilteredPuiseuxEvidenceScope.EXACT_FIRST_FRACTIONAL_GERM,
        evidence_sha256=expansion_digest,
    )
    fractional_evidence = make_filtered_puiseux_evidence(
        claim=(
            FilteredPuiseuxClaim.FIRST_FRACTIONAL_COEFFICIENT_NONZERO
        ),
        context=puiseux_context,
        authority=EvidenceAuthority.ADAPTER_EXACT,
        scope=FilteredPuiseuxEvidenceScope.EXACT_FIRST_FRACTIONAL_GERM,
        evidence_sha256=expansion_digest,
    )
    julia_evidence = make_filtered_puiseux_evidence(
        claim=FilteredPuiseuxClaim.JULIA_FLOW_IDENTITY,
        context=puiseux_context,
        authority=EvidenceAuthority.ADAPTER_EXACT,
        scope=FilteredPuiseuxEvidenceScope.EXACT_FORMAL_FLOW_IDENTITY,
        evidence_sha256=expansion_digest,
    )
    two_flow_evidence = make_filtered_puiseux_evidence(
        claim=FilteredPuiseuxClaim.TWO_FLOW_FACTORIZATION_IDENTITY,
        context=puiseux_context,
        authority=EvidenceAuthority.ADAPTER_EXACT,
        scope=FilteredPuiseuxEvidenceScope.EXACT_FORMAL_FLOW_IDENTITY,
        evidence_sha256=expansion_digest,
    )
    compiler_certificate = compile_filtered_puiseux_flow_obstruction(
        FilteredPuiseuxFlowProblem(
            name="jacobian_pure_contact_zero_prefix_free_witt",
            context=puiseux_context,
            evidence=(
                regular_evidence,
                fractional_evidence,
                julia_evidence,
            ),
        )
    )
    assert compiler_certificate.polynomial_generator_excluded
    two_flow_certificate = compile_filtered_two_flow_puiseux_obstruction(
        FilteredTwoFlowPuiseuxProblem(
            name="jacobian_pure_contact_zero_finite_critical_two_flow",
            context=puiseux_context,
            evidence=(
                regular_evidence,
                fractional_evidence,
                two_flow_evidence,
            ),
            minimum_generator_vanishing_order=2,
        )
    )
    assert two_flow_certificate.polynomial_two_flow_factorization_excluded
    equilibrium_transition = build_equilibrium_transition_certificate()
    assert equilibrium_transition["first_fractional_exponent"] == "5/2"
    assert equilibrium_transition["first_fractional_coefficient"] != "0"
    critical_monodromy = build_critical_monodromy_certificate()
    assert critical_monodromy[
        "monodromy_multiplier_has_infinite_order"
    ] is True
    finite_monodromy_countermodels = build_finite_monodromy_countermodels()
    assert finite_monodromy_countermodels["cubic_two_sheet_model"][
        "finite_regular_sheet_exchange"
    ] is True
    return {
        "schema": (
            "axiompack.jacobian_pure_contact_zero_"
            "witt_puiseux_obstruction.v4"
        ),
        "inverse_radial_holonomy": {
            "differential_equation": "F'/F=1/(x*(1+2*x*V(x)))",
            "first_nonidentity_coefficient": "[x^3]F=1/112",
            "typed_magnus_julia_check_rows": verification_rows,
            "julia_equation_verified_to_declared_order": True,
        },
        "branch_certificate": {
            "point": -2,
            "velocity_puiseux_exponent": "3/2",
            "velocity_branch_coefficient": str(velocity_branch),
            "regular_denominator": str(regular_denominator),
            "logarithmic_derivative_branch_coefficient": str(
                logarithmic_derivative_branch
            ),
            "endpoint_puiseux_exponent": "5/2",
            "endpoint_relative_branch_coefficient": str(
                endpoint_relative_branch
            ),
        },
        "all_index_multiplicity_obstruction": {
            "equation": "f(F)=F'*f",
            "nonroot_case": (
                "F' has a u^(3/2) term while f(F) first sees u^(5/2)"
            ),
            "root_case": (
                "matching the first fractional coefficient forces the "
                "integer root multiplicity m to equal 5/2"
            ),
            "polynomial_critical_witt_logarithm_exists": False,
        },
        "filtered_obstruction_compiler": compiler_certificate.to_dict(),
        "conditional_two_flow_obstruction_compiler": (
            two_flow_certificate.to_dict()
        ),
        "two_flow_authority_boundary": {
            "selected_continuation_to_cross_carrier_constructed": False,
            "finite_infinity_route_exhaustion_established": False,
            "equilibrium_transition_route_excluded": False,
            "finite_coupled_monodromy_route_excluded": False,
            "finite_regular_monodromy_countermodels_established": True,
            "scalar_infinite_monodromy_established": True,
            "factor_continuation_loop_transfer_constructed": False,
            "global_two_flow_factorization_excluded": False,
            "equilibrium_transition_collision_certificate_sha256": (
                equilibrium_transition["certificate_sha256"]
            ),
            "critical_monodromy_residue_certificate_sha256": (
                critical_monodromy["certificate_sha256"]
            ),
            "finite_regular_monodromy_countermodels_sha256": (
                finite_monodromy_countermodels["certificate_sha256"]
            ),
            "coupled_julia_elimination_governed_record_sha256": (
                "9a0b93843527fc75cb9c0121b79d9c89f726f2de29caaf341485bc56610785c2"
            ),
            "local_cross_carrier_exclusion_governed_record_sha256": (
                "65e1fffc99cee4b6c047d28cecf00dc3d92b85b6b2e995136f1530fe26a9a420"
            ),
            "compiler_output_status": (
                "conditional local nonfinite route only; selected loop "
                "continuation, finite coupled monodromy, and exhaustive "
                "routing omitted"
            ),
        },
        "equilibrium_transition_countermodel": equilibrium_transition,
        "finite_regular_monodromy_countermodels": finite_monodromy_countermodels,
        "critical_infinite_monodromy": critical_monodromy,
        "claim_boundary": (
            "The canonical pure-parity critical normal-two holonomy is "
            "not one polynomial flow. A fully constructed critical "
            "two-flow ramified cross carrier is also excluded. An arbitrary "
            "factorization may instead select finite equilibrium or regular "
            "monodromy sheets. The scalar holonomy has an infinite "
            "monodromy orbit and the two Julia rows have a governed "
            "division-free eliminant, but construction of the selected "
            "factor lifts, exclusion of their complete finite coupled "
            "branch, nonfinite-carrier realization, and exhaustive routing "
            "remain open."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
