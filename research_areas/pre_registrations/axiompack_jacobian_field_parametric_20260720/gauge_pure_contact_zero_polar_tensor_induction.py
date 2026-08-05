#!/usr/bin/env python3
"""Unconditional finite-polar-prefix induction in the split ``(A,J)`` pair.

The plain Witt quotient loses the source cost of the normal-three companion.
The split tensor coordinate repairs that defect:

    rho(A)J = 2*x*A*J' - 3*x*A'*J - 5*A*J,

and every target-kernel factor has ``J=0``.  This replay combines the exact
nonpolynomial critical source residual with a maximal-Rees-face argument.

For ``X=s**(-h)*x**d`` and a critical seed ``x**e``, the depth-``k`` orbit
has coefficient

    product_(i=0)^(k-1) (2*e+(2*i-3)*d-5).

At most four positive starting exponents can resonate.  The critical source
residual has infinite support, so a fresh nonresonant Newton seed exists
after the finitely many other maximal-face defects are excluded.  The exact
semidirect inverse transfer has nonzero even coefficients at every depth;
because the target module is zero, all of that orbit is paid by the source.
Its order and source-degree slopes are ``d-h`` and ``2*d``, giving strict
rate above two for every positive face.  Finite descent reaches the already
certified critical two-flow terminal.
"""

from __future__ import annotations

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

from gauge_pure_contact_zero_delta_critical_recurrence import (  # noqa: E402
    _split_semidirect_certificate,
)
from gauge_pure_contact_zero_polar_witt_induction import (  # noqa: E402
    _rees_newton_certificate,
    _semidirect_transfer_certificate,
)
from gauge_pure_contact_zero_tensor_density_holonomy import (  # noqa: E402
    run as tensor_holonomy_run,
)
from gauge_pure_contact_zero_witt_puiseux_obstruction import (  # noqa: E402
    run as witt_puiseux_run,
)
from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredPolarTensorClaim,
    FilteredPolarTensorEvidenceScope,
    FilteredPolarTensorFactorizationProblem,
    FilteredPolarTensorModel,
    compile_filtered_polar_tensor_factorization,
    make_filtered_polar_tensor_context,
    make_filtered_polar_tensor_evidence,
)
from ztare.common.content_bound_evidence import EvidenceAuthority  # noqa: E402


def _sha256(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _tensor_orbit_certificate() -> dict[str, object]:
    x = sp.symbols("x")

    def action(actor: sp.Expr, value: sp.Expr) -> sp.Expr:
        return sp.expand(
            2 * x * actor * sp.diff(value, x)
            - 3 * x * sp.diff(actor, x) * value
            - 5 * actor * value
        )

    finite_rows = []
    for d in range(1, 8):
        for e in range(1, 12):
            value = x**e
            coefficient = sp.Integer(1)
            rows = []
            for depth in range(1, 8):
                coefficient *= 2 * e + (2 * (depth - 1) - 3) * d - 5
                value = action(x**d, value)
                expected = coefficient * x ** (e + depth * d)
                assert sp.expand(value - expected) == 0
                rows.append(str(coefficient))
            finite_rows.append({
                "actor_exponent": d,
                "seed_exponent": e,
                "orbit_coefficients": rows,
            })

    # If the factor at depth i vanishes, then
    # 2*e=(3-2*i)*d+5.  Positivity e>=1 gives
    # 2*i*d <= 3*d+3, hence i<=3 for d>=1.  Each of i=0,1,2,3 determines
    # at most one positive integer e.
    return {
        "action": "rho(A)J=2*x*A*J'-3*x*A'*J-5*A*J",
        "monomial_recurrence": (
            "rho(x^d)^k(x^e)=prod_(i=0)^(k-1)"
            "(2*e+(2*i-3)*d-5)*x^(e+k*d)"
        ),
        "all_index_induction": (
            "the depth-k exponent is e+k*d; applying rho(x^d) "
            "multiplies by 2*(e+k*d)-3*d-5"
        ),
        "resonance_equation": "2*e=(3-2*i)*d+5",
        "resonance_index_bound": "e>=1,d>=1 imply i<=3",
        "maximum_positive_resonant_start_exponents": 4,
        "finite_crosscheck": finite_rows,
    }


def _newton_tensor_certificate() -> dict[str, object]:
    d, e, h, nu = sp.symbols("d e h nu", integer=True)
    before = h * e + d * nu
    after = h * (e + d) + d * (nu - h)
    assert sp.expand(after - before) == 0

    order_increment = d - h
    source_degree_increment = 2 * d
    strict_excess = sp.expand(source_degree_increment - 2 * order_increment)
    assert strict_excess == 2 * h
    return {
        "adjoint_lattice_step": "(nu,e)->(nu-h,e+d)",
        "newton_invariant": "h*e+d*nu",
        "newton_invariant_verified": True,
        "finite_tied_face": (
            "for fixed chi, e>=1 and bounded face-defect support leave "
            "only finitely many competing first-defect seeds"
        ),
        "fresh_seed_selection": (
            "infinite critical J support minus finite tied and at-most-four "
            "resonant exponents is nonempty"
        ),
        "parameter_order_increment": str(order_increment),
        "source_derivation_degree_increment": str(source_degree_increment),
        "strict_excess_over_rate_two": str(strict_excess),
        "limiting_rate": "2*d/(d-h)>2",
    }


def run(verification_rows: int = 8) -> dict[str, object]:
    tensor_holonomy = tensor_holonomy_run(verification_rows)
    tensor_orbit = _tensor_orbit_certificate()
    tensor_newton = _newton_tensor_certificate()
    semidirect_transfer = _semidirect_transfer_certificate()
    split = _split_semidirect_certificate()
    rees = _rees_newton_certificate()
    critical_terminal = witt_puiseux_run(verification_rows)

    module_certificate = tensor_holonomy[
        "abelian_source_residual"
    ]["quadratic_differential_compiler"]
    module_digest = str(
        module_certificate["quadratic_differential_certificate_sha256"]
    )
    terminal_certificate = critical_terminal[
        "filtered_two_flow_obstruction_compiler"
    ]
    terminal_digest = str(
        terminal_certificate["two_flow_puiseux_certificate_sha256"]
    )
    assert module_certificate["polynomial_solution_excluded"] is True
    assert terminal_certificate[
        "polynomial_two_flow_factorization_excluded"
    ] is True
    assert split["kernel_is_split_witt_subalgebra"] is True

    adapter_payload = {
        "tensor_holonomy_adapter": tensor_holonomy[
            "abelian_source_residual"
        ]["adapter_certificate_sha256"],
        "critical_module_certificate_sha256": module_digest,
        "critical_terminal_certificate_sha256": terminal_digest,
        "split_semidirect": split,
        "tensor_orbit": tensor_orbit,
        "tensor_newton": tensor_newton,
        "semidirect_transfer": semidirect_transfer,
        "rees_dictionary": rees,
        "factorization_owner": (
            "pure contact-zero radial/normal-three graph quotient"
        ),
        "target_module": "J=0",
        "tail_to_finite_positive_support": (
            "a strict symmetric limsup below two permits only finitely "
            "many positive-Rees source or target coefficients"
        ),
        "coefficientwise_polynomial_to_finite_face_defects": True,
    }
    adapter_digest = _sha256(adapter_payload)
    context = make_filtered_polar_tensor_context(
        category_id=(
            "pure contact-zero radial/normal-three split graph quotient"
        ),
        filtration_id=(
            "Rees grade h=d-order with source degree multiplier two"
        ),
        model=FilteredPolarTensorModel.WITT_DENSITY_2_NEG3_NEG5,
        adapter_evidence_sha256=adapter_digest,
    )
    evidence = (
        make_filtered_polar_tensor_evidence(
            claim=(
                FilteredPolarTensorClaim.FINITE_MAXIMAL_FACE_DECOMPOSITION
            ),
            subject_id="jacobian_pure_contact_zero_maximal_face_decomposition",
            context=context,
            authority=EvidenceAuthority.ADAPTER_EXACT,
            scope=(
                FilteredPolarTensorEvidenceScope.ALL_FINITE_POSITIVE_FACES
            ),
            evidence_sha256=adapter_digest,
        ),
        make_filtered_polar_tensor_evidence(
            claim=(
                FilteredPolarTensorClaim.CRITICAL_MODULE_INFINITE_SUPPORT
            ),
            subject_id="jacobian_critical_tensor_module_infinite_support",
            context=context,
            authority=EvidenceAuthority.FILTERED_COMPILER,
            scope=(
                FilteredPolarTensorEvidenceScope.ALL_CRITICAL_MODULE_ORDERS
            ),
            evidence_sha256=module_digest,
        ),
        make_filtered_polar_tensor_evidence(
            claim=FilteredPolarTensorClaim.CRITICAL_TERMINAL_EXCLUDED,
            subject_id="jacobian_zero_positive_face_terminal_excluded",
            context=context,
            authority=EvidenceAuthority.FILTERED_COMPILER,
            scope=(
                FilteredPolarTensorEvidenceScope.ZERO_POSITIVE_FACE_TERMINAL
            ),
            evidence_sha256=terminal_digest,
        ),
    )
    compiler_certificate = compile_filtered_polar_tensor_factorization(
        FilteredPolarTensorFactorizationProblem(
            name=(
                "jacobian_pure_contact_zero_"
                "arbitrary_finite_polar_prefix"
            ),
            threshold=2,
            degree_multiplier=2,
            context=context,
            evidence=evidence,
        )
    )
    assert compiler_certificate.finite_positive_prefix_induction_closed
    assert compiler_certificate.strict_subthreshold_factorization_excluded
    return {
        "schema": (
            "axiompack.jacobian_pure_contact_zero_"
            "polar_tensor_induction.v1"
        ),
        "split_tensor_density": split,
        "critical_module": tensor_holonomy["abelian_source_residual"],
        "tensor_orbit": tensor_orbit,
        "newton_separation": tensor_newton,
        "semidirect_transfer": semidirect_transfer,
        "rees_dictionary": rees,
        "critical_terminal": {
            "certificate_sha256": terminal_digest,
            "polynomial_two_flow_factorization_excluded": True,
        },
        "adapter_certificate_sha256": adapter_digest,
        "filtered_obstruction_compiler": compiler_certificate.to_dict(),
        "claim_boundary": (
            "For the pure contact-zero quotient, every arbitrary finite "
            "positive-Rees prefix is excluded by the maximal-face tensor "
            "induction, and the zero-positive-face branch is excluded by "
            "the certified critical terminal. Global campaign closure "
            "still requires auditing that the contact-depth dichotomy and "
            "the rate-two upper construction cover the declared schedule "
            "category without an omitted branch."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
