"""Currency-ledger templates for PDE execution mode."""
from __future__ import annotations

from typing import Any


DEFAULT_EXCHANGE_RATES = {
    "r2_to_r": "missing unless an estimate proves radius-square payment buys radius payment",
    "signed_to_positive": "missing unless cancellation is converted into positive mass",
    "final_to_presummed": "missing unless final carrier controls pre-summed stress",
    "final_angular_to_presummed_tracefree": (
        "missing unless same-window sheath cancellation is excluded or the "
        "carrier is moved to pre-summed angular packet ownership"
    ),
    "presummed_tracefree_to_owner_charge": (
        "missing unless angular trace-free samples are the paid event currency "
        "in an owner-preimage prefix budget"
    ),
    "owner_charge_to_cofinal_tracefree_prefix_family": (
        "missing unless the owner trace-free variation budget controls every "
        "C7-cofinal prefix, not only one selected prefix"
    ),
    "same_carrier_no_reuse_to_tracefree_carleson": (
        "missing unless same-carrier fresh no-reuse gives a numeric "
        "trace-free Carleson/all-prefix budget independent of target spend"
    ),
    "cone_leakage_to_tracefree_pointwise_payment": (
        "missing unless fixed-window pressure/Riesz cone plus Shard-C leakage "
        "pays total selected C7 trace-free variation, not only overflow excess"
    ),
    "psd_defect_trace_to_projected_tracefree_payment": (
        "missing unless the selected target is genuinely preprojection or a "
        "Leray/Riesz L1 payment theorem moves PSD trace through projection"
    ),
    "l2_to_l3": "missing unless interpolation/scale bounds pay critical cubic mass",
    "reused_to_fresh": "missing unless no-reuse or fresh-carrier injection is proved",
    "static_packet_to_dynamic_reset_obstruction": (
        "missing unless the static bad packet is tied to the same PDE "
        "trajectory/reset state with a selected dwell-time lower bound"
    ),
    "sample_transversality_to_uniform_exposure_bound": (
        "missing unless pointwise or sampled transverse evidence is upgraded "
        "to a uniform material-derivative or second-order exposure bound"
    ),
    "near_stealth_to_signed_growth_sterility": (
        "missing unless the near-stealth segment carries a signed global "
        "budget proving it cannot fund the target growth"
    ),
    "local_model_to_global_cutoff_invoice": (
        "missing unless a local model is localized into the admissible PDE "
        "class with finite-energy cutoff, projection/tail, same-carrier, "
        "and no-reuse invoices paid before using the local surplus globally"
    ),
    "angular_cutoff_boundary_to_same_owner_invoice": (
        "missing unless an angular or spatial-direction cutoff created for "
        "localization has its boundary/commutator invoice paid on the same "
        "owner prefix before the localized surplus is projected or re-spent"
    ),
    "coarea_low_slice_to_lower_payment": (
        "missing unless a coarea/threshold slice selected for small boundary "
        "cost is also proved to carry the required positive lower-payment "
        "currency on the same event; ordinary averaging gives upper control, "
        "not this high-low correlation"
    ),
    "linear_moment_budget_to_quadratic_cap": (
        "missing unless a same-carrier quadratic/second-moment receipt is "
        "proved; a first-moment or owner-root linear budget can coexist with "
        "arbitrarily concentrated spikes and cannot be spent as an anti-spike "
        "cap without an amplitude bound, support floor, or explicit quadratic "
        "budget"
    ),
    "nonnegative_selected_channel_to_prefix_budget": (
        "missing unless the channel is fixed before payoff, pays the same "
        "selected target prefix by a numeric lower-payment map, and has a "
        "finite all-prefix budget; signed/current-theoretic cancellation or "
        "forced endpoint coalescence must be declared as a separate channel "
        "rather than smuggled into nonnegative accounting"
    ),
    "coalescent_quotient_to_original_endpoint_debit": (
        "missing unless the quotient/current map is fixed before payoff and "
        "the original omitted endpoint debits are paid or annihilated before "
        "class aggregation; otherwise many endpoints can be hidden in one "
        "class and the route recurs to omitted-child/no-null debit"
    ),
    "boundary_invoice_to_selected_no_reuse_budget": (
        "missing unless the boundary/local-energy invoice pays the same "
        "selected stream with a uniform lower-cost line, finite all-prefix "
        "budget, fixed-before-payoff assignment, same carrier/source binding, "
        "bounded overlap, and no nested rebilling; a finite boundary label "
        "alone can be reused across selected levels"
    ),
}


def currency_ledger_template(target_currency: str | None = None) -> dict[str, Any]:
    """Return the ledger fields an RD agent must fill for a PDE attempt."""
    return {
        "target_currency": target_currency or "declare exact target, e.g. radius_sum",
        "produced_currency": {
            "ckn_mass": "sum r_Q^2 or local L3 mass",
            "signed_flux": "signed local-energy flux",
            "final_pressure_magnitude": "absolute final pressure carrier",
            "final_angular_sample_norm": "final angular pressure/tensor sample carrier",
            "presummed_tracefree_morphology": (
                "pre-summed trace-free tensor morphology before projection"
            ),
            "owner_preimage_event_charge": (
                "selected owner atom charge with finite active-prefix budget"
            ),
            "cofinal_tracefree_owner_prefix_budget": (
                "uniform C7-prefix trace-free variation owner budget"
            ),
            "same_carrier_tracefree_carleson_budget": (
                "selected-stream trace-free Carleson budget from fresh no-reuse"
            ),
            "cone_leakage_tracefree_payment": (
                "linear selected C7 trace-free payment from pressure/Riesz cone "
                "charge plus Shard-C leakage on the same stream"
            ),
            "psd_defect_trace_payment": (
                "PSD matrix-defect trace payment before projection, requiring "
                "a separate exchange to projected trace-free variation"
            ),
            "energy_defect": "L2/enstrophy defect",
            "cubic_mass": "critical L3 mass",
            "positive_flux": "positive total variation or cutoff flux",
            "dynamic_reset_dwell_certificate": (
                "same-trajectory reset/dwell data needed to convert a static "
                "packet into a dynamic admissibility obstruction"
            ),
            "uniform_transversality_exposure_bound": (
                "uniform first- or second-order exposure bound along the "
                "selected PDE trajectory, not a point sample"
            ),
            "signed_growth_sterility_budget": (
                "signed global budget showing a near-stealth segment is "
                "sterile for the claimed growth channel"
            ),
            "local_model_surplus": (
                "surplus proved only on a local/formal model before "
                "finite-energy localization and projection invoices"
            ),
            "finite_energy_cutoff_invoice": (
                "cutoff, projection/tail, same-carrier, and no-reuse costs "
                "paid to transfer a local model into the admissible PDE class"
            ),
            "same_owner_angular_boundary_invoice": (
                "boundary/commutator cost created by angular or directional "
                "cutoff localization, billed to the same owner prefix before "
                "projection or downstream spend"
            ),
            "correlated_coarea_slice_payment": (
                "one preselected coarea/threshold event that is simultaneously "
                "cheap for boundary cost and large enough to pay the target "
                "positive lower-bound currency"
            ),
            "same_carrier_quadratic_moment_cap": (
                "quadratic/second-moment control on the same carrier as the "
                "target first-moment payment, fixed before payoff and not a "
                "proxy/global budget"
            ),
            "nonnegative_selected_channel_payment": (
                "a same-prefix nonnegative channel payment with a finite "
                "budget and pointwise lower-payment map to the target debit"
            ),
            "signed_or_coalescent_channel_escape": (
                "a genuinely signed/current-theoretic or forced-coalescence "
                "mechanism that is outside nonnegative prefix accounting"
            ),
            "coalescent_quotient_debit": (
                "class-level current/coalescence debit after omitted endpoint "
                "children are paid or annihilated before payoff"
            ),
            "omitted_endpoint_debit": (
                "original selected endpoint debit that must not disappear when "
                "passing to a quotient/current support representation"
            ),
            "same_stream_boundary_no_reuse_budget": (
                "boundary or local-energy invoice budget that is assigned to "
                "the same selected stream with total prefix assignment, bounded "
                "overlap, and no rebilling of boundary atoms"
            ),
        },
        "exchange_rate_obligations": DEFAULT_EXCHANGE_RATES,
        "rule": (
            "If a required exchange rate is missing, the next work unit must "
            "either prove it or kill it with a hostile packet."
        ),
    }
