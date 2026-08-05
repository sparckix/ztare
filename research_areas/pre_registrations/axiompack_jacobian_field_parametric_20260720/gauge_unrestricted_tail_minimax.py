#!/usr/bin/env python3
"""Exhaustive tail-minimax composition for the normalized Jacobian family.

Every coefficientwise-polynomial target schedule has exactly one of two
contact-depth profiles after the exact parity/divisor factorization:

* all positive-contact coefficients vanish; or
* a least positive-contact occurrence exists.

The first branch is handled by the split tensor-density polar induction.
The second is handled by the moving-backbone least-positive-contact
induction.  The radial cone staircase supplies a schedule in the same
category with symmetric logarithmic rate at most two.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
SRC_ROOT = HERE.parents[2] / "src"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gauge_cone_radial_triangular_staircase import run as staircase_run  # noqa: E402
from gauge_moving_backbone_unconditional_induction import (  # noqa: E402
    run as least_positive_run,
)
from gauge_pure_contact_zero_polar_tensor_induction import (  # noqa: E402
    run as pure_contact_zero_run,
)
from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredTailClaim,
    FilteredTailEvidenceScope,
    FilteredTailMinimaxCompositionProblem,
    FilteredTailOccurrenceOrder,
    compile_filtered_tail_minimax_composition,
    make_filtered_tail_context,
    make_filtered_tail_evidence,
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


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(verification_rows: int = 8) -> dict[str, object]:
    if verification_rows < 8:
        raise ValueError("the global audit needs eight critical rows")

    pure = pure_contact_zero_run(verification_rows)
    least_positive = least_positive_run()
    staircase = staircase_run(maximum_target_order=5)

    pure_certificate = pure["filtered_obstruction_compiler"]
    least_positive_certificate = least_positive[
        "asymptotic_rate_transfer"
    ]["compiler_certificate"]
    assert pure_certificate[
        "strict_subthreshold_factorization_excluded"
    ] is True
    assert pure_certificate[
        "finite_positive_prefix_induction_closed"
    ] is True
    assert least_positive_certificate["minimum_certified_rate"] == "2"
    assert least_positive_certificate["no_rebilling_verified"] is True
    assert least_positive[
        "unconditional_induction_closure"
    ]["least_positive_contact_symmetric_limsup_at_least_two"] is True
    assert staircase["target_logarithmic_rate_bound"] == "1"
    assert staircase["source_forward_dexp_roundtrip"] is True
    assert staircase["target_forward_dexp_roundtrip"] is True

    pure_digest = str(pure_certificate["polar_tensor_certificate_sha256"])
    least_positive_digest = str(
        least_positive_certificate["asymptotic_certificate_sha256"]
    )
    repository_root = HERE.parents[2]
    upper_result_path = HERE / "gauge_cone_radial_triangular_staircase_result.md"
    upper_lean_path = (
        repository_root
        / "ztare_proofs/ZtareProofs/"
        "AxiomPackJacobianConeRadialStaircaseArithmetic.lean"
    )
    upper_digest = _sha256({
        "schema": staircase["schema"],
        "moving_tangency_identity": staircase["moving_tangency_identity"],
        "radial_semigroup": staircase[
            "seed_cone_target_lift_radial_semigroup"
        ],
        "finite_replay_newton_slope": staircase["tail_slope_bound"],
        "all_order_symmetric_tail_bound": "2",
        "target_logarithmic_rate_bound": staircase[
            "target_logarithmic_rate_bound"
        ],
        "source_forward_dexp_roundtrip": True,
        "target_forward_dexp_roundtrip": True,
        "all_order_owner": (
            "moving two-layer identity, radial semigroup division, "
            "normal-layer Rees induction"
        ),
        "all_order_result_sha256": _file_sha256(upper_result_path),
        "arithmetic_carrier_sha256": _file_sha256(upper_lean_path),
    })
    category = {
        "family": "normalized public Jacobian deformation",
        "target_coefficients": "QQ[P,Q], coefficientwise polynomial",
        "target_lift_algebra": (
            "QQ+(P^3,P*Q,Q^2) plus finite positive divisor depth per row"
        ),
        "source": "coefficientwise polynomial volume-preserving contact",
        "source_logarithm": "right-multiply velocity convention",
        "target_logarithm": "left-multiply velocity convention",
        "statistic": (
            "max of source derivation-excess and target derivation degree, "
            "divided by logarithmic order"
        ),
        "branch_partition": (
            "positive divisor support empty or least positive occurrence"
        ),
        "upper_construction_membership": (
            "P^a*Q^b with b>=1, excluding Q, lies in "
            "(P*Q,Q^2) and hence in the pure contact-zero algebra"
        ),
    }
    adapter_digest = _sha256({
        "category": category,
        "pure_branch_certificate_sha256": pure_digest,
        "least_positive_branch_certificate_sha256": least_positive_digest,
        "upper_construction_certificate_sha256": upper_digest,
    })
    context = make_filtered_tail_context(
        category_id=json.dumps(
            category,
            sort_keys=True,
            separators=(",", ":"),
        ),
        statistic_id=str(category["statistic"]),
        occurrence_order=(
            FilteredTailOccurrenceOrder.NAT_PARAMETER_POSITIVE_GRADE_LEX
        ),
        adapter_evidence_sha256=adapter_digest,
    )
    evidence = (
        make_filtered_tail_evidence(
            claim=FilteredTailClaim.PURE_BRANCH_LOWER,
            subject_id="jacobian_pure_contact_zero_lower_bound",
            context=context,
            bound=2,
            authority=EvidenceAuthority.FILTERED_COMPILER,
            scope=(
                FilteredTailEvidenceScope.ALL_ORDER_FINITE_PREFIX_UNIFORM
            ),
            evidence_sha256=pure_digest,
        ),
        make_filtered_tail_evidence(
            claim=FilteredTailClaim.LEAST_POSITIVE_BRANCH_LOWER,
            subject_id="jacobian_least_positive_contact_lower_bound",
            context=context,
            bound=2,
            authority=EvidenceAuthority.FILTERED_COMPILER,
            scope=(
                FilteredTailEvidenceScope.ALL_ORDER_FINITE_PREFIX_UNIFORM
            ),
            evidence_sha256=least_positive_digest,
        ),
        make_filtered_tail_evidence(
            claim=FilteredTailClaim.ADMISSIBLE_UPPER,
            subject_id="jacobian_radial_staircase_upper_bound",
            context=context,
            bound=2,
            authority=EvidenceAuthority.ADAPTER_EXACT,
            scope=(
                FilteredTailEvidenceScope.ADMISSIBLE_ALL_ORDER_CONSTRUCTION
            ),
            evidence_sha256=upper_digest,
        ),
    )
    compiler_certificate = compile_filtered_tail_minimax_composition(
        FilteredTailMinimaxCompositionProblem(
            name="jacobian_unrestricted_symmetric_tail_minimax",
            threshold=2,
            context=context,
            evidence=evidence,
        )
    )
    assert compiler_certificate.unrestricted_minimax_value == "2"
    return {
        "schema": "axiompack.jacobian_unrestricted_tail_minimax.v1",
        "schedule_category": category,
        "branch_partition": {
            "pure_contact_zero": {
                "lower_bound": "2",
                "all_order": True,
                "arbitrary_finite_polar_prefix": True,
                "certificate_sha256": pure_digest,
            },
            "least_positive_contact": {
                "lower_bound": "2",
                "all_contact_depths": True,
                "arbitrary_moving_contact_zero_backbone": True,
                "least_index_shift_invariant": True,
                "certificate_sha256": least_positive_digest,
            },
        },
        "upper_construction": {
            "symmetric_tail_bound": "2",
            "source_tail_bound": "2",
            "finite_replay_newton_slope": staircase[
                "tail_slope_bound"
            ],
            "target_tail_bound": staircase[
                "target_logarithmic_rate_bound"
            ],
            "admissible_pure_contact_zero_schedule": True,
            "certificate_sha256": upper_digest,
        },
        "adapter_certificate_sha256": adapter_digest,
        "filtered_obstruction_compiler": compiler_certificate.to_dict(),
        "result": {
            "unrestricted_lower_bound": "2",
            "unrestricted_upper_bound": "2",
            "sigma_ct": "2",
        },
        "claim_boundary": (
            "This determines the unrestricted symmetric logarithmic tail "
            "minimax for the normalized public Jacobian family in the "
            "declared coefficientwise-polynomial gauge category. It makes "
            "no claim about the planar Jacobian conjecture or historical "
            "priority."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
