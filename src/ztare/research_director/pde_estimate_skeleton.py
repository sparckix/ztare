"""General estimate skeletons for PDE execution mode.

This module proposes analytic proof shapes before a domain-specific workbench
fills in substrate vocabulary.  It is deliberately heuristic: the output is an
inspectable estimate plan plus hostile packet, not a theorem verdict.
"""
from __future__ import annotations

from typing import Any


def _tokens(*values: str | None) -> str:
    return " ".join(str(v or "").lower() for v in values)


def generate_estimate_skeletons(
    *,
    target: str,
    field: str | None = None,
    gap_type: str | None = None,
    context: dict[str, Any] | None = None,
    inequalities: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return candidate PDE estimate skeletons for a target surface.

    The skeletons are intentionally substrate-neutral.  Callers may plug the
    suggested fields into NS, MHD, NLS, or other PDE-specific profiles.
    """
    text = _tokens(
        target,
        field,
        gap_type,
        " ".join(inequalities or []),
        (context or {}).get("doc"),
    )
    skeletons: list[dict[str, Any]] = []

    if any(word in text for word in ("coarea", "collar", "threshold", "aperture")):
        skeletons.append({
            "id": "coarea_threshold_charge",
            "route": "coarea/threshold selection",
            "normalized_variables": [
                "preselected aperture interval I with |I| > 0",
                "threshold tau chosen before payoff",
                "collar width delta > 0",
                "collar charge M_collar(tau)",
                "owner-prefix invoice I_owner",
            ],
            "target_inequality": (
                "profile_constant * M_collar(tau) <= coarea_charge(tau) "
                "<= owner_prefix_invoice"
            ),
            "proof_steps": [
                "freeze the aperture interval and admissible threshold set before payoff",
                "apply coarea/averaging to find a threshold with controlled collar charge",
                "verify the selected threshold preserves the geometric lower-bound margin",
                "bind the selected collar charge to the same owner-prefix invoice",
            ],
            "required_receipts": [
                "nonadaptive_threshold_selection",
                "margin_preservation",
                "same_owner_prefix_charge",
                "bounded_projection_multiplicity",
                "no_collar_mass_reuse",
            ],
            "hostile_packet": {
                "name": "good_threshold_bad_owner_prefix",
                "kills": "coarea threshold with no owner-preimage billing",
                "survives": [
                    "pre-payoff threshold",
                    "local coarea bound",
                    "geometric margin",
                ],
            },
            "smaller_theorem": (
                "owner-preimage coarea collar charge for one preselected "
                "threshold family"
            ),
        })

    if any(word in text for word in ("cutoff", "commutator", "boundary", "collar")):
        skeletons.append({
            "id": "cutoff_commutator_invoice",
            "route": "cutoff/commutator invoice",
            "normalized_variables": [
                "cutoff profile chi fixed before payoff",
                "profile norm C_chi",
                "boundary/collar mass M_boundary",
                "separated production/pressure/Duhamel/inherited channels",
                "total invoice I_total",
            ],
            "target_inequality": (
                "production + pressure_reserve + duhamel_reserve + "
                "inherited_reserve <= C_chi * M_boundary <= I_total"
            ),
            "proof_steps": [
                "differentiate the cutoff and isolate every boundary term",
                "assign each term to a named spend channel before projection",
                "prove the sum of channels is bounded by the profile norm times collar mass",
                "charge that collar mass to the same invoice without reuse",
            ],
            "required_receipts": [
                "profile_fixed_before_payoff",
                "typed_spend_channels",
                "same_invoice_channel_binding",
                "no_post_projection_payment",
                "no_reuse",
            ],
            "hostile_packet": {
                "name": "unpaid_cutoff_boundary_invoice",
                "kills": "free localization or declaration-only cutoff payment",
                "survives": ["local model", "fixed profile label", "formal support inclusion"],
            },
            "smaller_theorem": (
                "fixed-profile same-owner boundary invoice payment"
            ),
        })

    if any(word in text for word in ("projection", "riesz", "pressure", "leray")):
        skeletons.append({
            "id": "projection_tail_invoice",
            "route": "projection/tail invoice",
            "normalized_variables": [
                "preprojection carrier",
                "projected target",
                "tail or pressure reserve",
                "same source window",
            ],
            "target_inequality": (
                "projected_target <= preprojection_payment + tail_reserve"
            ),
            "proof_steps": [
                "prove the estimate before projection where the carrier is visible",
                "bound the projection/tail error on the same source window",
                "separate pressure reserve from the main positive spend",
            ],
            "required_receipts": [
                "preprojection_identity",
                "tail_reserve_paid",
                "same_source_window",
            ],
            "hostile_packet": {
                "name": "projection_tail_unpaid_packet",
                "kills": "preprojection payment spent as projected target",
                "survives": ["preprojection bound"],
            },
            "smaller_theorem": "preprojection-to-projected exchange with tail invoice",
        })

    return skeletons[:5]
