#!/usr/bin/env python3
"""All-finite-prefix polar induction in the tangent Witt quotient.

The pure contact-zero normalization has an exact two-factor identity in its
normal-two Witt quotient.  Under a hypothetical symmetric tail bound below
two, each factor has only finitely many positive Rees faces.  This replay
checks the universal maximal-face calculation used to eliminate them.

For a maximal monomial ``X = s**(-h) * x**d`` and a defect monomial
``s**nu * x**e``, the leading adjoint sends

    (nu, e) -> (nu-h, e+d)

and preserves ``h*e + d*nu``.  On a tied Newton face the exact two-factor
law is semidirect, and solving for the factor defects multiplies the product
defect by ``z/(1-exp(-z))``.  That series times a nonzero polynomial cannot
be polynomial.  Hence a noncentral defect generates infinitely many paid
factor coefficients.  The only terminating branch is the scalar
centralizer of the maximal Witt field, which reduces to the already excluded
single polynomial flow.
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

from gauge_pure_contact_zero_witt_puiseux_obstruction import (  # noqa: E402
    run as witt_puiseux_run,
)
from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredPolarWittClaim,
    FilteredPolarWittEvidenceScope,
    FilteredPolarWittFactorizationProblem,
    FilteredPolarWittModel,
    compile_filtered_polar_witt_factorization,
    make_filtered_polar_witt_context,
    make_filtered_polar_witt_evidence,
)
from ztare.common.content_bound_evidence import (  # noqa: E402
    EvidenceAuthority,
)


def _sha256(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _truncated_matrix_function(
    matrix: sp.Matrix,
    coefficients: list[sp.Expr],
) -> sp.Matrix:
    result = sp.zeros(*matrix.shape)
    power = sp.eye(matrix.rows)
    for coefficient in coefficients:
        result += coefficient * power
        power *= matrix
    return result.applyfunc(sp.expand)


def _semidirect_transfer_certificate(depth: int = 12) -> dict[str, object]:
    if depth < 6:
        raise ValueError("the transfer replay needs depth at least six")

    # D is the nilpotent shift on a finite quotient of one adjoint orbit.
    operator = sp.zeros(depth)
    for index in range(depth - 1):
        operator[index + 1, index] = index + 1

    exponential = _truncated_matrix_function(
        operator,
        [sp.Rational(1, sp.factorial(order)) for order in range(depth)],
    )
    inverse_exponential = _truncated_matrix_function(
        operator,
        [
            sp.Rational((-1) ** order, sp.factorial(order))
            for order in range(depth)
        ],
    )
    phi_positive = _truncated_matrix_function(
        operator,
        [sp.Rational(1, sp.factorial(order + 1)) for order in range(depth)],
    )
    phi_negative = _truncated_matrix_function(
        operator,
        [
            sp.Rational((-1) ** order, sp.factorial(order + 1))
            for order in range(depth)
        ],
    )
    assert inverse_exponential * exponential == sp.eye(depth)
    assert inverse_exponential * phi_positive == phi_negative

    z = sp.symbols("z")
    inverse_series = sp.series(
        z / (1 - sp.exp(-z)),
        z,
        0,
        depth,
    ).removeO().expand()
    inverse_coefficients = [
        sp.expand(inverse_series).coeff(z, order)
        for order in range(depth)
    ]
    psi = _truncated_matrix_function(operator, inverse_coefficients)
    assert psi * phi_negative == sp.eye(depth)

    even_rows = []
    for order in range(2, depth, 2):
        coefficient = sp.factor(inverse_coefficients[order])
        assert coefficient == sp.bernoulli(order) / sp.factorial(order)
        assert coefficient != 0
        even_rows.append({
            "adjoint_depth": order,
            "coefficient": str(coefficient),
        })

    # Exact all-index argument.  If psi(z) P(z)=Q(z) were polynomial, then
    # exp(-z)Q=Q-zP would be polynomial.  For nonzero
    # Q=sum_{j=0}^m q_j z^j, its coefficient above degree m is
    # (-1)^n/n! times the nonzero polynomial
    # sum_j q_j*(-1)^j*n^(falling j), and is nonzero for all but finitely
    # many n.  Therefore exp(-z)Q has infinite support.
    return {
        "semidirect_matrix_model": (
            "M(alpha,u)=[[alpha*D,u],[0,0]]"
        ),
        "exponential_module_coordinate": (
            "phi(alpha*D)u, phi(z)=(exp(z)-1)/z"
        ),
        "opposite_face_product": (
            "phi(-D)C+exp(-D)phi(D)B=phi(-D)(B+C)"
        ),
        "inverse_transfer": "D/(1-exp(-D))",
        "nilpotent_quotient_depth": depth,
        "matrix_identity_verified": True,
        "inverse_identity_verified": True,
        "even_coefficient_rows": even_rows,
        "all_even_bernoulli_coefficients_nonzero": (
            "B_(2k) is nonzero in characteristic zero"
        ),
        "nonpolynomial_seed_theorem": (
            "for nonzero P in QQ[z], z*P/(1-exp(-z)) is not polynomial"
        ),
        "nonpolynomial_seed_proof": (
            "a polynomial Q would make exp(-z)Q polynomial; its tail is "
            "(-1)^n/n! times a nonzero falling-factorial polynomial in n"
        ),
    }


def _witt_least_term_certificate() -> dict[str, object]:
    x = sp.symbols("x")

    def bracket(left: sp.Expr, right: sp.Expr) -> sp.Expr:
        return sp.expand(
            2 * x * (left * sp.diff(right, x) - sp.diff(left, x) * right)
        )

    rows = []
    for d in range(1, 7):
        for e in range(1, 7):
            if e == d:
                continue
            value = x**e
            coefficients = []
            for depth in range(1, 8):
                value = bracket(x**d, value)
                expected = (
                    2**depth
                    * (e - d)
                    * sp.prod(e + index * d for index in range(depth - 1))
                    * x ** (e + depth * d)
                )
                assert sp.expand(value - expected) == 0
                coefficient = sp.expand(value).coeff(
                    x,
                    e + depth * d,
                )
                assert coefficient != 0
                coefficients.append(str(coefficient))
            rows.append({
                "face_least_degree": d,
                "defect_least_degree": e,
                "checked_coefficients": coefficients,
            })

    # The displayed recurrence is all-index: after its first factor e-d,
    # every new factor is e+j*d>0.  A commuting defect satisfies
    # (c/a)'=0 and is a scalar multiple of a.  If ad_a^N(c)=0, the last
    # nonzero predecessor would solve ad_a(y)=lambda*a.  Dividing by a^2
    # forces y to have a nonzero constant term, outside x*QQ[[x]], unless
    # lambda=0.  Backward induction reduces again to the centralizer.
    return {
        "bracket": "[a,c]=2*x*(a*c'-a'*c)",
        "least_term_formula": (
            "2^k*a_d^k*c_e*(e-d)*prod_(j=0)^(k-2)(e+j*d)"
        ),
        "least_degree_after_depth_k": "e+k*d",
        "all_index_nonzero_when_e_not_equal_d": True,
        "finite_crosscheck_rows": rows,
        "centralizer": "ker(ad_a)=QQ*a",
        "local_nilpotence_classification": (
            "ad_a^N(c)=0 iff c belongs to QQ*a in x*QQ[[x]]"
        ),
    }


def _rees_newton_certificate() -> dict[str, object]:
    d, e, h, nu, k = sp.symbols(
        "d e h nu k",
        integer=True,
    )
    newton_before = h * e + d * nu
    newton_after = h * (e + d) + d * (nu - h)
    assert sp.expand(newton_after - newton_before) == 0

    parameter_order = e + nu + k * (d - h)
    source_degree = 2 * (e + k * d) + 1
    excess_over_two = sp.expand(source_degree - 2 * parameter_order)
    assert excess_over_two == 2 * h * k - 2 * nu + 1
    assert sp.expand(
        2 * d - 2 * (d - h)
    ) == 2 * h

    # A fixed Newton face h*e+d*nu=chi with e>=1 and nu>=0 has finitely
    # many lattice points.  The maximal-face adjoint preserves chi, so
    # different faces cannot collide with its least-x orbit.
    return {
        "rees_dictionary": (
            "s^q*r*z^2*x^d = s^(q-d)*r*z^2*x^d; nu=q-d"
        ),
        "positive_face": "h=d-q>0, hence q=d-h>=1 and d>h",
        "adjoint_lattice_step": "(nu,e)->(nu-h,e+d)",
        "newton_invariant": str(newton_before),
        "newton_invariant_verified": True,
        "nonnegative_product_face_is_finite": True,
        "orbit_parameter_order": str(parameter_order),
        "orbit_source_derivation_degree": str(source_degree),
        "excess_over_rate_two": str(excess_over_two),
        "limiting_rate": "2*d/(d-h)",
        "limiting_rate_minus_two": "2*h/(d-h)>0",
        "same_order_payment": True,
    }


def run() -> dict[str, object]:
    semidirect = _semidirect_transfer_certificate()
    witt = _witt_least_term_certificate()
    rees = _rees_newton_certificate()
    critical = witt_puiseux_run()
    critical_certificate = critical["filtered_obstruction_compiler"]
    centralizer_digest = str(
        critical_certificate["puiseux_flow_certificate_sha256"]
    )

    adapter_payload = {
        "semidirect": semidirect,
        "witt": witt,
        "rees": rees,
        "factorization_owner": (
            "canonical radial/normal-two graph quotient of the pure "
            "contact-zero contact identity"
        ),
        "tail_to_finite_positive_support": (
            "an infinite positive face has source excess at least zero "
            "along an unbounded same-order support, contradicting a "
            "strict symmetric tail bound below two"
        ),
        "required_coupled_cost_owner": (
            "the exact normal-two/normal-three compatibility quotient; "
            "the plain normal-two projection does not supply this premise"
        ),
        "critical_centralizer_digest": centralizer_digest,
    }
    adapter_digest = _sha256(adapter_payload)
    # The universal compiler is intentionally fail-closed here.  The plain
    # normal-two target image is not invariant under the displayed Witt
    # bracket after radial normalization: omitted normal-three companions
    # contribute to the bracket.  The exact invariant object is the split
    # (A,J) tensor-density module, not A alone.  Supplying True here would
    # turn a correct universal theorem into an invalid Jacobian adapter.
    compiler_rejection = None
    context = make_filtered_polar_witt_context(
        category_id="jacobian_pure_contact_zero_plain_normal_two_candidate",
        filtration_id="parameter_rees_grade_and_newton_face",
        model=FilteredPolarWittModel.TANGENT_WITT_FIRST_DEFECT_NEWTON,
        adapter_evidence_sha256=adapter_digest,
        centralizer_evidence_sha256=centralizer_digest,
    )
    face_evidence = make_filtered_polar_witt_evidence(
        claim=FilteredPolarWittClaim.FINITE_MAXIMAL_FACE_DECOMPOSITION,
        subject_id="jacobian_plain_witt.maximal_face",
        context=context,
        authority=EvidenceAuthority.ADAPTER_EXACT,
        scope=FilteredPolarWittEvidenceScope.ALL_FINITE_POSITIVE_FACES,
        evidence_sha256=adapter_digest,
    )
    centralizer_evidence = make_filtered_polar_witt_evidence(
        claim=FilteredPolarWittClaim.CENTRALIZER_FLOW_EXCLUDED,
        subject_id="jacobian_plain_witt.centralizer",
        context=context,
        authority=EvidenceAuthority.FILTERED_COMPILER,
        scope=FilteredPolarWittEvidenceScope.SCALAR_CENTRALIZER_BRANCH,
        evidence_sha256=centralizer_digest,
    )
    try:
        compile_filtered_polar_witt_factorization(
            FilteredPolarWittFactorizationProblem(
                name="jacobian_pure_contact_zero_plain_witt_candidate",
                threshold=2,
                degree_multiplier=2,
                context=context,
                evidence=(face_evidence, centralizer_evidence),
            )
        )
    except ValueError as error:
        compiler_rejection = str(error)
    assert compiler_rejection is not None
    assert compiler_rejection.startswith(
        "missing_semidirect_newton_quotient:"
    )
    return {
        "schema": (
            "axiompack.jacobian_pure_contact_zero_"
            "polar_witt_induction.v1"
        ),
        "semidirect_transfer": semidirect,
        "witt_least_term": witt,
        "rees_newton_dictionary": rees,
        "adapter_certificate_sha256": adapter_digest,
        "centralizer_obstruction_sha256": centralizer_digest,
        "filtered_obstruction_compiler": {
            "candidate_rejected": True,
            "error": compiler_rejection,
            "missing_adapter_identity": (
                "the normal-two target image is not an invariant module "
                "without its normal-three companion"
            ),
        },
        "claim_boundary": (
            "The universal maximal-polar-face theorem and its Newton/rate "
            "dictionary are verified, but the plain Witt adapter is "
            "rejected. The Jacobian induction must run in the exact split "
            "tensor-density pair (A,J), where target kernel controls have "
            "J=0 and rho(A)J is the invariant action."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
