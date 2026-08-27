#!/usr/bin/env python3
"""Tail-minimax composition audit for the normalized Jacobian family.

Every coefficientwise-polynomial target schedule has exactly one of two
contact-depth profiles after the exact parity/divisor factorization:

* all positive-contact coefficients vanish; or
* a least positive-contact occurrence exists.

The first branch is reduced by the split tensor-density polar induction to a
zero-positive-face terminal.  At that terminal the target critical support
is either finite, where the regular Rees two-flow exclusion applies once its
schedule carrier is constructed, or infinite, where the actual finite source
Lie pair must be composed with the semidirect exponential transfer.  The
transferred group-module coordinate is generally nonpolynomial, so the older
finite-polynomial density-clock carrier does not follow from finite source
Lie support.
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

    pure_certificate = pure["positive_face_descent_certificate"]
    least_positive_certificate = least_positive[
        "asymptotic_rate_transfer"
    ]["compiler_certificate"]
    assert pure_certificate[
        "finite_positive_prefix_induction_closed"
    ] is True
    assert pure_certificate["critical_terminal_excluded"] is False
    assert least_positive_certificate["minimum_certified_rate"] == "2"
    assert least_positive_certificate["no_rebilling_verified"] is True
    assert least_positive[
        "unconditional_induction_closure"
    ]["least_positive_contact_symmetric_limsup_at_least_two"] is True
    assert staircase["target_logarithmic_rate_bound"] == "1"
    assert staircase["source_forward_dexp_roundtrip"] is True
    assert staircase["target_forward_dexp_roundtrip"] is True

    pure_digest = str(pure_certificate["certificate_sha256"])
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
    return {
        "schema": "axiompack.jacobian_unrestricted_tail_minimax.v7",
        "schedule_category": category,
        "branch_partition": {
            "pure_contact_zero": {
                "lower_bound": None,
                "conditional_lower_bound": None,
                "positive_face_induction_all_order": True,
                "selected_critical_terminal_excluded": False,
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
        "conditional_filtered_obstruction_compiler": None,
        "result": {
            "unrestricted_lower_bound": None,
            "conditional_unrestricted_lower_bound": None,
            "unrestricted_upper_bound": "2",
            "sigma_ct": None,
            "missing_proposition": (
                "derive the exhaustive finite/infinite target-critical "
                "dichotomy from every strict-subthreshold pure "
                "zero-positive-face schedule; construct the regular Rees "
                "carrier in the finite branch and, in the infinite branch, "
                "bind the finite polynomial Lie pair (A,J) to the exact "
                "target-left semidirect transfer "
                "(1-exp(-rho(A)))/rho(A), then exclude that transferred "
                "orbit without assuming its group-module coordinate is "
                "polynomial"
            ),
            "target_critical_rate_gap": {
                "ordinary_rate_implies_finite_critical_support": False,
                "counterfamily_scope": (
                    "exact infinite critical diagonal with strict ordinary "
                    "target rate; not itself a coupled gauge schedule"
                ),
                "kernel_owner": (
                    "AxiomPackJacobianTargetCriticalRateGap."
                    "target_critical_rate_gap_terminal_certificate"
                ),
            },
            "equilibrium_transition_local_collision_sha256": (
                pure["critical_terminal"]["equilibrium_transition_countermodel"]
                ["certificate_sha256"]
            ),
            "critical_infinite_monodromy_sha256": (
                pure["critical_terminal"]["critical_infinite_monodromy"]
                ["certificate_sha256"]
            ),
            "finite_regular_monodromy_countermodels_sha256": (
                pure["critical_terminal"]
                ["finite_regular_monodromy_countermodels"]
                ["certificate_sha256"]
            ),
            "coupled_julia_elimination_governed_record_sha256": (
                "9a0b93843527fc75cb9c0121b79d9c89f726f2de29caaf341485bc56610785c2"
            ),
        },
        "claim_boundary": (
            "The radial staircase proves sigma_ct <= 2. The matching lower "
            "bound remains open at the schedule-level finite/infinite "
            "target-critical dichotomy and its two carrier constructions; "
            "the infinite branch must retain semidirect exponential "
            "transfer rather than infer polynomial group-module support. "
            "No conclusion about the planar Jacobian "
            "conjecture or historical priority follows."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
