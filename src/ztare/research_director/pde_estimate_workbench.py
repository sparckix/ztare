#!/usr/bin/env python3
"""RD-side PDE estimate workbench.

This is a thin RD caller over existing ZTARE primitives. It does not call an
LLM and does not edit Lean. It is not a second workbench; ZTARE remains the
general-purpose thesis-hardening workbench. This script exists to compose
already-shipped pieces for one proof-director move.

Use it when a typed endpoint needs analytical work and Codex wants one compact
packet before choosing a patch route:

  * workmap field/type context from `typed_endpoint_pack.py`,
  * local gap typing + Mathlib shelf from `gap_typed_prompter.py`,
  * auxiliary-object families from `auxiliary_object_catalog.py`,
  * GP-219 PDE estimate-craft op suggestions from `src/ztare`,
  * optional pi-group forcing anti-laundering checks,
  * optional single-spend carrier audit for multi-channel PDE carriers,
  * optional dimensional/endpoint checks for candidate inequalities,
  * optional toy-case variant emission through `curriculum_generator.py`.

Clean split:
  - ZTARE core/autoresearch: general theory-building primitives, falsifiers,
    framer/Lagrangian derivation, deterministic gates, and bounded briefing
    artifacts.
  - RD/Codex turn: choose a concrete proof target, inspect Lean, run local
    scouts/curriculum packs, and edit theorem files when warranted.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Kernel-location bootstrap (2026-05-25 hoist from
# projects/ns_millennium_hunt/scripts/). The workbench is general-purpose —
# callable by any PDE substrate — and now lives alongside the other RD kernel
# primitives. The residual band-aid below adds the two helper directories to
# sys.path because the helpers in scripts/public/{lean,utilities}/ are not
# yet proper Python packages (no __init__.py). Tracked separately: convert
# scripts/public/*/ into namespace packages so this bootstrap can disappear.
REPO = Path(__file__).resolve().parents[3]
for _hd in (
    REPO,
    REPO / "src",  # canonical kernel root: enables `from ztare.X import ...`
    REPO / "scripts" / "public" / "lean",
    REPO / "scripts" / "public" / "utilities",
):
    _hs = str(_hd)
    if _hs not in sys.path:
        sys.path.insert(0, _hs)

from ztare.research_director.source_currency_discriminator import (  # noqa: E402
    classify_source_currency,
)

DEFAULT_OUT_DIR = (
    REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
    / "pde_workbench"
)
DEFAULT_RESIDUAL_NORMAL_FORM_PROFILE = (
    REPO / "projects" / "ns_millennium_hunt" / "config"
    / "residual_normal_forms.json"
)
LEAN_ROOT = REPO / "ztare_proofs" / "ZtareProofs"

NS_HOSTILE_PACKET_SUITES: dict[str, list[dict[str, Any]]] = {
    "ns_default": [
        {
            "id": "dini_flat_cascade",
            "packet": "A_n = 1/(n+1), A_n -> 0, sum A_n diverges",
            "tests": ["Dini vs vanishing amplitude", "summability from flatness"],
        },
        {
            "id": "diagonal_ckn",
            "packet": "choose r_n with sum r_n^2 finite and sum r_n divergent",
            "tests": ["CKN mass currency", "radius-sum exchange"],
        },
        {
            "id": "nested_dirac_reuse",
            "packet": "finite scalar measure concentrated on nested regions",
            "tests": ["fresh annular charge", "same-carrier no-reuse"],
        },
        {
            "id": "same_window_core_sheath_cancellation",
            "packet": "core and sheath cancel in final pressure carrier",
            "tests": ["final carrier vs pre-summed stress"],
        },
        {
            "id": "tangential_div_div_null_stress",
            "packet": "R = tau tensor tau times line measure with div div R = 0",
            "tests": ["trace defect visibility", "pressure-only detection"],
        },
        {
            "id": "helicity_dark_plane_wave",
            "packet": "high-frequency plane wave with near-zero helicity signal",
            "tests": ["helicity observability", "stress survives hidden signal"],
        },
        {
            "id": "sparse_cubic_ghost",
            "packet": "amplitude M_n/r_n on volume M_n^-3 r_n^5",
            "tests": ["cubic badness", "energy and stress invisibility"],
        },
        {
            "id": "positive_cutoff_flux_reuse",
            "packet": "one positive packet crosses infinitely many nested cutoffs",
            "tests": ["fresh positive flux", "cutoff invoice reuse"],
        },
        {
            "id": "commutator_only_type_i",
            "packet": "alpha_A = alpha_C with other channels zero",
            "tests": ["commutator-only payment", "channel separation"],
        },
        {
            "id": "critical_kato_hardy_potential",
            "packet": "V_+ comparable to r^-2 with Kato norm order one",
            "tests": ["critical potential smallness", "Hardy/Kato exchange"],
        },
    ],
}

NS_THEOREM_APPLICABILITY_DB: dict[str, dict[str, Any]] = {
    "avisc_same_source_pushforward_bound": {
        "requires": {
            "localized_Avisc_surplus": True,
            "strict_local_subcritical_exponents": True,
            "strict_tail_exponent": True,
            "exact_invoice_fiber_source_binding": True,
            "observable_carrier_is_separated_source": True,
            "no_proxy_carrier_substitution": True,
            "pressure_transport_reserves_single_spent": True,
            "same_separated_source": True,
        },
        "concludes": {
            "C7AViscSameSourcePushforwardBoundReceipt": True,
            "oldObservableBoundOnThisSeparatedSource": True,
        },
        "does_not_accept": [
            "TrackB_level_set_window_label_only",
            "same_source_label_only",
            "morphology_label_as_old_observable_bound",
            "proxy_carrier_may_differ_from_separated_source",
        ],
    },
    "avisc_marked_source_variance": {
        "requires": {
            "C7AViscSameSourcePushforwardBoundReceipt": True,
            "marked_source_law_on_invoice_fiber": True,
            "variance_lower_bound_before_scalarization": True,
            "marked_law_bound_to_total_fresh_annular_carrier": True,
            "scalar_pushforward_noninjectivity_excluded": True,
            "traceless_tensor_law_on_invoice_fiber": True,
            "traceless_tensor_non_cancellation": True,
            "isotropic_orientation_mixture_excluded": True,
            "traceless_tensor_forces_total_carrier_morphology": True,
            "same_separated_source": True,
        },
        "concludes": {
            "C7AViscMarkedSourceVarianceReceipt": True,
            "C7AViscTensorMomentSameSourceMorphologyReceipt": True,
        },
        "does_not_accept": [
            "scalar_masses_only",
            "first_moment_only",
            "isotropic_orientation_mixture",
            "same_source_label_only",
            "morphology_label_as_variance",
            "positive_part_pushforward_only",
            "scalar_marked_variance_only",
        ],
    },
    "pressure_cutoff_carrier_identity_for_avisc": {
        "requires": {
            "pressure_angular_moment_available": True,
            "pressure_carrier_equals_Avisc_invoice_fiber": True,
            "cutoff_matches_Avisc_invoice_fiber": True,
            "eigenframe_selection_acts_before_payoff": True,
            "eigenframe_selection_forces_Avisc_tensor_non_cancellation": True,
        },
        "concludes": {
            "PressureCutoffCarrierIdentityForAViscInvoiceFiber": True,
            "PressureCutoffEigenframeSelectionForAViscInvoiceFiber": True,
        },
        "does_not_accept": [
            "pressure_angular_moment_available_only",
            "pressure_carrier_may_differ_from_Avisc_invoice_fiber",
            "cutoff_may_differ_from_Avisc_invoice_fiber",
            "same_window_core_sheath_cancellation",
            "tangential_div_div_null_stress",
            "post_payoff_eigenframe_selection",
        ],
    },
    "pressure_cutoff_fresh_annular_invoice_morphology": {
        "requires": {
            "pressure_angular_moment_available": True,
            "pressure_carrier_equals_fresh_annular_invoice_fiber": True,
            "cutoff_matches_fresh_annular_invoice_fiber": True,
            "eigenframe_selection_acts_before_payoff": True,
            "anti_isotropic_cancellation_on_invoice_fiber": True,
            "total_fresh_annular_carrier_morphology_proof": True,
            "not_monotone_tail": True,
            "not_scalar_measure": True,
            "not_uniform_enstrophy_disguise": True,
            "same_separated_source": True,
        },
        "concludes": {
            "PressureCutoffFreshAnnularInvoiceFiberMorphologyReceipt": True,
            "C7FreshAnnularSameSourceMorphologyTransferReceipt": True,
        },
        "does_not_accept": [
            "pressure_angular_moment_available_only",
            "pressure_carrier_equals_Avisc_invoice_fiber_only",
            "pressure_carrier_may_differ_from_fresh_annular_invoice_fiber",
            "cutoff_may_differ_from_fresh_annular_invoice_fiber",
            "same_window_core_sheath_cancellation",
            "tangential_div_div_null_stress",
            "isotropic_orientation_mixture",
            "localized_Avisc_surplus",
            "scalar_marked_variance_only",
        ],
    },
    "selected_c7_longitudinal_pressure_visible_subclass": {
        "requires": {
            "owner_preimage_owns_pre_pressure_tensor_packets": True,
            "selected_packets_fixed_before_pressure_projection": True,
            "selected_C7_owned_packets_are_pressure_visible_longitudinal_subclass": True,
            "longitudinal_projection_coercive_on_selected_packets": True,
            "excludes_tangential_pressure_null_plane_wave_on_selected_packets": True,
            "excludes_same_window_core_sheath_cancellation_on_selected_packets": True,
            "same_source_fresh_annular_morphology_lower_bound": True,
            "projection_pays_morphology_before_payoff": True,
            "no_CF_or_other_Clay_equivalent_input_used": True,
        },
        "concludes": {
            "SelectedC7LongitudinalPressureVisibleSubclassReceipt": True,
            "OwnedPrePressureProjectionFreshAnnularMorphologyReceipt": True,
        },
        "does_not_accept": [
            "owner_preimage_ownership_only",
            "divergence_free_Leray_constraint_only",
            "pressure_angular_moment_available_only",
            "tangential_pressure_null_plane_wave_admissible",
            "same_window_core_sheath_cancellation",
            "direction_lipschitz_or_CF_coherence",
            "post_payoff_packet_selection",
        ],
    },
    "angular_pressure_tomography_selected_packet_morphology": {
        "requires": {
            "selected_packets_owned_before_angular_projection": True,
            "angular_frame_fixed_before_payoff": True,
            "angular_frame_spans_trace_free_tensor_morphology": True,
            "pressure_samples_on_same_fresh_annular_source": True,
            "stable_tomographic_inversion_constant": True,
            "no_same_window_sheath_cancellation_on_angular_frame": True,
            "no_tangential_pressure_null_loss_after_angular_frame": True,
            "same_source_fresh_annular_morphology_lower_bound": True,
            "projection_pays_morphology_before_payoff": True,
            "no_CF_or_other_Clay_equivalent_input_used": True,
        },
        "concludes": {
            "AngularPressureTomographySelectedPacketReceipt": True,
            "OwnedPrePressureProjectionFreshAnnularMorphologyReceipt": True,
        },
        "does_not_accept": [
            "single_direction_pressure_symbol_only",
            "pressure_l2_carrier_label_only",
            "angular_frame_post_payoff",
            "same_window_sheath_cancellation_admissible",
            "pressure_samples_on_proxy_carrier",
            "pointwise_tomography_without_cofinal_owner_prefix_budget",
            "five_frame_owner_fiber_prefix_overflow",
            "owner_preimage_receipt_missing",
            "direction_lipschitz_or_CF_coherence",
        ],
    },
    "selected_c7_angular_frame_no_sheath_cancellation": {
        "requires": {
            "pressure_l2_formula_source_fixed": True,
            "selected_C7_frame_fixed_before_payoff": True,
            "selected_C7_source_is_same_formula_source": True,
            "opposite_trace_free_sheath_excluded_before_payoff": True,
            "strict_angular_dominance_on_selected_frame": True,
            "dominance_not_chosen_from_final_carrier_magnitude": True,
            "no_CF_or_other_Clay_equivalent_input_used": True,
        },
        "concludes": {
            "SelectedC7AngularFrameNoSheathCancellationReceipt": True,
            "noSameWindowSheathCancellationOnAngularFrame": True,
        },
        "does_not_accept": [
            "C7_owner_geometry_only",
            "fresh_annular_anti_laundering_only",
            "pressure_l2_carrier_label_only",
            "same_window_sheath_cancellation_admissible",
            "scalar_projected_moment_total_variation_cancellation",
            "signed_projected_moment_used_as_total_variation",
            "final_angular_samples_only",
            "post_payoff_frame_or_packet_selection",
            "direction_lipschitz_or_CF_coherence",
        ],
    },
    "selected_c7_fixed_window_cone_mass_rigidity_source": {
        "requires": {
            "pressure_l2_formula_source_fixed": True,
            "selected_C7_frame_fixed_before_payoff": True,
            "selected_C7_source_is_same_formula_source": True,
            "core_positive_cone_mass_measured_before_summation": True,
            "sheath_opposite_cone_mass_measured_before_summation": True,
            "overflow_to_same_window_sheath_cancellation_packet": True,
            "same_window_sheath_cancellation_forbidden_on_selected_C7_class": True,
            "cone_masses_not_defined_from_final_carrier_magnitude": True,
            "no_CF_or_other_Clay_equivalent_input_used": True,
        },
        "concludes": {
            "FixedWindowStressConeMassRigiditySource": True,
            "SelectedC7AngularFrameNoSheathCancellationReceipt": True,
        },
        "does_not_accept": [
            "C7_owner_geometry_only",
            "fresh_annular_anti_laundering_only",
            "strict_angular_dominance_assumed_not_produced",
            "pressure_l2_carrier_label_only",
            "same_window_sheath_cancellation_admissible",
            "final_angular_samples_only",
            "post_payoff_frame_or_packet_selection",
            "direction_lipschitz_or_CF_coherence",
        ],
    },
    "selected_c7_oriented_cone_asymmetry_gate": {
        "requires": {
            "pressure_l2_formula_source_fixed": True,
            "selected_C7_frame_fixed_before_payoff": True,
            "selected_C7_source_is_same_formula_source": True,
            "core_positive_cone_mass_measured_before_summation": True,
            "sheath_opposite_cone_mass_measured_before_summation": True,
            "hypotheses_distinguish_tracefree_orientation_flip": True,
            "opposite_cone_mass_strictly_below_core_before_payoff": True,
            "asymmetry_paid_by_pre_summed_owner_carrier": True,
            "not_defined_by_final_carrier_magnitude": True,
            "no_CF_or_other_Clay_equivalent_input_used": True,
        },
        "concludes": {
            "SelectedC7OppositeTraceFreeSheathInadmissibleBeforePayoff": True,
            "same_window_sheath_cancellation_forbidden_on_selected_C7_class": True,
        },
        "does_not_accept": [
            "C7_owner_geometry_only",
            "fresh_annular_anti_laundering_only",
            "pressure_symbol_membership_only",
            "PSD_preimage_available_after_orientation_choice",
            "replay_invariant_five_shadow_visibility_only",
            "tracefree_orientation_flip_not_distinguished",
            "diagonal_sign_blind_core_sheath_equal_mass_packet",
            "same_window_sheath_cancellation_admissible",
            "final_angular_samples_only",
            "post_payoff_frame_or_packet_selection",
            "direction_lipschitz_or_CF_coherence",
        ],
    },
    "pre_summed_angular_packet_owner_carrier": {
        "requires": {
            "angular_tracefree_spend_nonnegative": True,
            "owner_packet_budget_nonnegative": True,
            "packet_owner_pays_presummed_angular_tracefree_morphology": True,
            "typed_single_spend_channels": True,
            "total_budget_partition": True,
            "section_identity_binds_same_formula_source": True,
            "selected_packet_partition_fixed_before_payoff": True,
            "pressure_reserve_single_spent": True,
            "duhamel_reserve_separated_from_pressure_carrier": True,
            "inherited_reserve_not_reused_for_angular_carrier": True,
            "no_descendant_rebilling_for_presummed_angular_packets": True,
            "carrier_is_presummed_not_final_angular_samples": True,
            "no_CF_or_other_Clay_equivalent_input_used": True,
        },
        "concludes": {
            "PreSummedAngularPacketOwnerCarrierReceipt": True,
            "sameWindowSheathCancellationDoesNotEraseCarrier": True,
        },
        "does_not_accept": [
            "final_angular_samples_only",
            "single_spend_channels_prop_only",
            "owner_budget_label_only",
            "pressure_l2_carrier_label_only",
            "post_payoff_packet_selection",
            "direction_lipschitz_or_CF_coherence",
        ],
    },
    "angular_sample_owner_preimage_exchange": {
        "requires": {
            "angular_tracefree_spend_nonnegative": True,
            "angular_event_prefix_spend_nonnegative": True,
            "owner_charge_prefix_budget_nonnegative": True,
            "owner_packet_budget_nonnegative": True,
            "event_pay_is_angular_tracefree_sample_spend": True,
            "angular_events_fixed_before_payoff": True,
            "pointwise_angular_sample_to_owner_charge_bound": True,
            "owner_preimage_prefix_pays_angular_events": True,
            "owner_charge_prefix_budget_finite_for_angular_charge": True,
            "angular_tracefree_spend_le_event_prefix_spend": True,
            "angular_event_prefix_spend_le_owner_charge_prefix": True,
            "owner_charge_prefix_budget_le_owner_packet_budget": True,
            "composed_angular_owner_budget_bound": True,
            "angular_event_prefix_spend_le_owner_packet_budget_all_C7_truncations": True,
            "angular_sample_lives_on_exact_invoice_fiber": True,
            "same_formula_source_is_same_input_carrier": True,
            "selected_prefix_cofinal_with_C7_scale_truncations": True,
            "atom_charge_is_tracefree_total_variation_on_owner_packet": True,
            "owner_packet_budget_is_tracefree_total_variation_currency": True,
            "no_positive_part_or_isotropic_scalarization": True,
            "section_identity_binds_same_formula_source": True,
            "selected_packet_partition_fixed_before_payoff": True,
            "no_descendant_rebilling_for_angular_events": True,
            "carrier_is_presummed_not_final_angular_samples": True,
            "no_CF_or_other_Clay_equivalent_input_used": True,
        },
        "concludes": {
            "AngularSampleOwnerPreimageExchangeReceipt": True,
            "PreSummedAngularPacketOwnerCarrierReceipt": True,
        },
        "does_not_accept": [
            "owner_budget_label_only",
            "bounded_multiplicity_label_only",
            "event_pay_label_equal_only",
            "owner_preimage_for_beta_events_only",
            "atom_charge_defined_as_angular_spend_without_budget",
            "same_formula_source_syntax_only",
            "angular_quotient_proxy_not_invoice_fiber",
            "prefix_order_rechosen_by_angular_affordability",
            "one_chosen_prefix_only",
            "positive_part_or_isotropic_scalarization",
            "owner_packet_budget_energy_currency_only",
            "final_angular_samples_only",
            "single_spend_channels_prop_only",
            "post_payoff_packet_selection",
            "direction_lipschitz_or_CF_coherence",
        ],
    },
    "tracefree_variation_owner_section_interpretation": {
        "requires": {
            "angular_sample_owner_preimage_exchange_receipt": True,
            "owner_is_tracefree_variation_disintegration_section": True,
            "angular_events_are_variation_atoms_on_exact_invoice_fiber": True,
            "C7_prefix_reads_variation_disintegration_prefix": True,
            "owner_charge_is_noncircular_tracefree_variation_measure": True,
            "uniform_C7_prefix_tracefree_variation_budget": True,
            "total_variation_budget_independent_of_target_spend": True,
            "tracefree_variation_budget_not_product_L2_or_global_L4_disguise": True,
            "sparse_high_high_ghost_accounted_or_excluded_for_variation_budget": True,
            "no_signed_moment_or_positive_part_budget": True,
        },
        "concludes": {
            "TraceFreeVariationOwnerSectionInterpretation": True,
            "AngularSampleOwnerPreimageExchangeReceipt": True,
        },
        "does_not_accept": [
            "owner_packet_label_only",
            "event_is_bad_scale_packet_only",
            "owner_packet_budget_defined_as_angularTracefreeSpend",
            "atom_charge_defined_as_angular_spend_without_budget",
            "prefix_order_rechosen_by_angular_affordability",
            "same_formula_source_syntax_only",
            "signed_moment_budget",
            "positive_part_budget",
            "energy_or_source_budget_currency",
            "product_L2_or_global_L4_disguise",
            "sparse_high_high_ghost_still_admissible",
            "sparse_prefix_overflow_still_admissible",
            "one_chosen_prefix_only",
        ],
    },
    "tracefree_variation_c7_cofinal_owner_prefix_budget": {
        "requires": {
            "target_charge_identified_with_angular_event_pay": True,
            "angular_event_pay_is_tracefree_variation_atom": True,
            "owner_is_tracefree_variation_disintegration_section": True,
            "exact_invoice_fiber": True,
            "same_input_carrier": True,
            "C7_prefix_reads_variation_disintegration_prefix": True,
            "pointwise_angular_event_pay_to_owner_charge": True,
            "uniform_C7_prefix_tracefree_variation_budget": True,
            "owner_tracefree_variation_prefix_budget_all_C7_truncations": True,
            "target_prefix_le_owner_TV_budget_all_C7_truncations": True,
            "total_variation_budget_independent_of_target_spend": True,
            "tracefree_variation_budget_not_product_L2_or_global_L4_disguise": True,
            "sparse_high_high_ghost_accounted_or_excluded_for_variation_budget": True,
            "no_signed_moment_or_positive_part_budget": True,
            "selected_packet_partition_fixed_before_payoff": True,
            "no_descendant_rebilling_for_angular_events": True,
            "carrier_is_presummed_not_final_angular_samples": True,
            "no_CF_or_other_Clay_equivalent_input_used": True,
        },
        "concludes": {
            "TraceFreeVariationC7CofinalOwnerPrefixBudget": True,
            "AngularSampleOwnerPreimageExchangeReceipt": True,
            "TraceFreeVariationOwnerSectionInterpretation": True,
        },
        "does_not_accept": [
            "one_chosen_prefix_only",
            "owner_packet_budget_defined_as_angularTracefreeSpend",
            "atom_charge_defined_as_angular_spend_without_budget",
            "prefix_order_rechosen_by_angular_affordability",
            "same_formula_source_syntax_only",
            "angular_quotient_proxy_not_invoice_fiber",
            "signed_moment_budget",
            "positive_part_budget",
            "energy_or_source_budget_currency",
            "product_L2_or_global_L4_disguise",
            "sparse_high_high_ghost_still_admissible",
            "sparse_prefix_overflow_still_admissible",
            "post_payoff_packet_selection",
            "direction_lipschitz_or_CF_coherence",
            "pre_summed_pressure_total_variation_only",
            "single_visibility_carrier_not_cofinal_owner_prefix_family",
            "leray_stress_L1_or_energy_budget_only",
            "single_projected_stress_TV_carrier_only",
            "besov_B0_1_1_or_BV_hidden_input",
            "same_tree_incidence_ordering_only",
            "owner_fibers_bounded_by_invoice_fibers_missing",
            "selected_prefix_preimage_packing_missing",
            "identity_owner_map_only",
            "owner_fibers_bounded_but_variation_unsummable",
        ],
    },
    "annular_owner_fiber_tracefree_disintegration": {
        "requires": {
            "tracefree_variation_c7_cofinal_owner_prefix_budget": True,
            "tracefree_variation_atoms_refine_annular_owner_invoice_fibers": True,
            "owner_fibers_bounded_by_invoice_fibers": True,
            "selected_prefix_preimage_packing": True,
            "bounded_multiplicity_for_every_C7_prefix": True,
            "owner_fiber_map_fixed_before_payoff": True,
            "not_pressure_total_variation_carrier_only": True,
            "not_leray_stress_or_energy_budget_only": True,
            "not_same_tree_incidence_only": True,
            "no_besov_BV_or_product_L2_hidden_input": True,
        },
        "concludes": {
            "AnnularOwnerFiberTraceFreeDisintegrationReceipt": True,
            "TraceFreeVariationC7CofinalOwnerPrefixBudget": True,
            "AngularSampleOwnerPreimageExchangeReceipt": True,
        },
        "does_not_accept": [
            "pre_summed_pressure_total_variation_only",
            "leray_stress_L1_or_energy_budget_only",
            "same_tree_incidence_ordering_only",
            "owner_fibers_bounded_by_invoice_fibers_missing",
            "selected_prefix_preimage_packing_missing",
            "one_chosen_prefix_only",
            "identity_owner_map_only",
            "owner_fibers_bounded_but_variation_unsummable",
            "product_L2_or_global_L4_disguise",
            "sparse_prefix_overflow_still_admissible",
            "besov_B0_1_1_or_BV_hidden_input",
            "post_payoff_packet_selection",
        ],
    },
    "tracefree_variation_same_carrier_fresh_no_reuse_carleson": {
        "requires": {
            "tracefree_variation_c7_cofinal_owner_prefix_budget": True,
            "tracefree_carleson_budget_independent_of_angular_spend": True,
            "same_carrier_fresh_no_reuse_for_tracefree_atoms": True,
            "selected_C7_tracefree_prefix_cofinal_map": True,
            "owner_atom_charge_not_besov_BV_proxy": True,
            "owner_atom_charge_not_product_L2_or_global_L4_proxy": True,
            "sparse_high_high_tracefree_prefix_overflow_excluded_by_mechanism": True,
            "bounded_multiplicity_does_not_define_budget": True,
            "identity_owner_summable_variation_receipt": True,
            "no_CF_coherence_or_strict_margin_imported": True,
        },
        "concludes": {
            "TraceFreeVariationSameCarrierFreshNoReuseCarlesonReceipt": True,
            "TraceFreeVariationC7CofinalOwnerPrefixBudget": True,
            "AngularSampleOwnerPreimageExchangeReceipt": True,
        },
        "does_not_accept": [
            "same_carrier_fresh_no_reuse_label_only",
            "numeric_event_to_owner_prefix_inequality_missing",
            "carleson_prefix_budget_missing",
            "tracefree_carleson_budget_chosen_from_angular_spend",
            "owner_atom_charge_chosen_from_angular_spend",
            "besov_B0_1_1_or_BV_hidden_input",
            "owner_atom_charge_is_frequency_variation_norm",
            "product_L2_or_global_L4_disguise",
            "sparse_prefix_overflow_still_admissible",
            "owner_fibers_bounded_by_invoice_fibers_only",
            "owner_fibers_bounded_but_variation_unsummable",
            "identity_owner_map_only",
            "direction_lipschitz_or_CF_coherence",
            "strict_margin_or_CF_global_extension_import",
        ],
    },
    "tracefree_variation_pointwise_same_carrier_payment": {
        "requires": {
            "pointwise_tracefree_variation_payment": True,
            "finite_prefix_fresh_carrier_budget": True,
            "tracefree_atoms_are_same_carrier_fresh_charge": True,
            "payment_currency_is_tracefree_variation_not_beta_square": True,
            "payment_fixed_before_angular_spend_payoff": True,
            "no_product_L2_or_besov_proxy_in_payment": True,
        },
        "concludes": {
            "TraceFreeVariationPointwiseSameCarrierPaymentReceipt": True,
            "TraceFreeVariationSameCarrierFreshNoReuseCarlesonReceipt": True,
            "TraceFreeVariationC7CofinalOwnerPrefixBudget": True,
        },
        "does_not_accept": [
            "beta_square_carleson_available_only",
            "same_tree_beta_carleson_incidence_only",
            "square_budget_finite_but_linear_prefix_overflows",
            "dini_square_carleson_but_L1_diverges",
            "payment_only_in_square_currency",
            "fresh_charge_chosen_from_angular_event_pay",
            "finite_budget_chosen_from_angular_prefix_supremum",
            "pointwise_payment_tautological",
            "linear_tracefree_currency_pays_pointwise_only",
            "beta_square_currency_pays_finite_budget_only",
            "coherence_currency_imports_CF_or_BV_atom",
            "no_independent_fourth_currency",
            "pointwise_and_finite_budget_use_different_currencies",
            "same_carrier_identity_owner_only",
            "no_descendant_reuse_only",
            "product_L2_or_global_L4_disguise",
            "besov_B0_1_1_or_BV_hidden_input",
            "direction_lipschitz_or_CF_coherence",
        ],
    },
    "tracefree_variation_heat_lag_geometric_payment": {
        "requires": {
            "tracefree_variation_pointwise_same_carrier_payment": True,
            "heat_lag_fixed_before_payoff": True,
            "heat_lag_same_carrier_duhamel_semigroup_lag": True,
            "heat_lag_grows_across_selected_C7_prefixes": True,
            "geometric_decay_pays_linear_tracefree_variation": True,
            "not_parabolic_matched_constant_heat_lag": True,
            "not_target_defined_heat_lag": True,
            "duhamel_bilinear_remainder_paid_without_forbidden_currency": True,
            "no_gevrey_or_caloric_capacity_recurrence": True,
            "no_paraproduct_besov_or_CF_coherence_import": True,
        },
        "concludes": {
            "TraceFreeVariationHeatLagGeometricPaymentReceipt": True,
            "TraceFreeVariationPointwiseSameCarrierPaymentReceipt": True,
            "TraceFreeVariationC7CofinalOwnerPrefixBudget": True,
        },
        "does_not_accept": [
            "heat_lag_dimensionless_monomial_only",
            "heat_lag_bounded_on_selected_parabolic_scale",
            "no_prefix_growing_geometric_decay",
            "linear_semigroup_geometric_stub_only",
            "duhamel_bilinear_remainder_requires_forbidden_currency",
            "bilinear_reduces_to_caloric_gevrey_or_paraproduct_or_CF_or_target_reflux",
            "linear_stub_does_not_pay_full_nonlinear_receipt",
            "heat_lag_chosen_from_angular_prefix_growth",
            "heat_lag_chosen_after_spend_outcome",
            "target_defined_energy_reflux",
            "selected_C7_finite_overlap_without_amplitude_summability",
            "amplitude_summability_missing",
            "dini_square_carleson_but_L1_diverges",
            "payment_only_in_square_currency",
            "coherence_currency_imports_CF_or_BV_atom",
            "pointwise_payment_tautological",
        ],
    },
    "tracefree_variation_hardy_tent_atomic_payment": {
        "requires": {
            "tracefree_variation_pointwise_same_carrier_payment": True,
            "selected_C7_packets_form_pre_payoff_unconditional_atoms": True,
            "atomic_coefficient_L1_pays_tracefree_variation": True,
            "duhamel_remainder_preserves_atomic_currency": True,
            "not_target_defined_atomic_decomposition": True,
            "no_besov_paraproduct_or_CF_import": True,
        },
        "concludes": {
            "TraceFreeVariationHardyTentAtomicPaymentReceipt": True,
            "TraceFreeVariationPointwiseSameCarrierPaymentReceipt": True,
            "TraceFreeVariationC7CofinalOwnerPrefixBudget": True,
        },
        "does_not_accept": [
            "finite_signed_hardy_tent_norm_available_only",
            "selected_packet_unconditional_L1_embedding_missing",
            "atomic_decomposition_not_tied_to_preselected_C7_packets",
            "endpoint_paraproduct_besov_or_target_defined_budget_required",
            "atoms_chosen_from_selected_coefficient_overflow",
            "atomic_budget_chosen_after_payoff",
            "signed_commutator_cancellation_available_only",
            "absolute_tracefree_variation_payment_missing",
            "square_or_signed_currency_only",
            "duhamel_bilinear_remainder_requires_forbidden_currency",
            "bilinear_reduces_to_caloric_gevrey_or_paraproduct_or_CF_or_target_reflux",
            "dini_square_carleson_but_L1_diverges",
            "payment_only_in_square_currency",
            "coherence_currency_imports_CF_or_BV_atom",
        ],
    },
    "tracefree_variation_cone_leakage_pointwise_payment": {
        "requires": {
            "tracefree_variation_pointwise_same_carrier_payment": True,
            "same_projected_riesz_angular_formula_source_fixed_before_payoff": True,
            "total_cone_tracefree_variation_le_pressure_riesz_cone_charge_plus_shardC_charges": True,
            "shardC_leakage_charges_on_same_selected_C7_stream": True,
            "all_prefix_cone_leakage_budget": True,
            "not_overflow_excess_only": True,
            "no_sheath_cancellation_not_imported": True,
            "no_pressure_riesz_degree_zero_only": True,
            "no_CF_direction_coherence_import": True,
        },
        "concludes": {
            "TraceFreeVariationConeLeakagePointwisePaymentReceipt": True,
            "TraceFreeVariationPointwiseSameCarrierPaymentReceipt": True,
            "TraceFreeVariationC7CofinalOwnerPrefixBudget": True,
        },
        "does_not_accept": [
            "pressureRieszConeCharge_pays_overflowExcess",
            "selected_c7_fixed_window_cone_mass_rigidity_source",
            "fixed_window_overflow_visible_or_invisible_profile_only",
            "no_sameWindowSheathCancellation",
            "pressure_l2_carrier_label_only",
            "same_window_sheath_cancellation_forbidden_only",
            "CF_or_direction_coherence",
            "final_carrier_magnitude",
            "total_cone_tracefree_variation_payment_missing",
            "pressure_riesz_degree_zero_carrier_only",
            "same_stream_fresh_cone_budget_missing",
            "homogeneity_zero_obstruction_still_admissible",
        ],
    },
    "fixed_window_total_cone_variation_charge_source": {
        "requires": {
            "core_positive_cone_mass_measured_before_summation": True,
            "sheath_opposite_cone_mass_measured_before_summation": True,
            "total_cone_variation_is_core_plus_sheath": True,
            "total_cone_variation_le_pressure_riesz_cone_charge_plus_shardC_charges": True,
            "pressure_riesz_cone_charge_uses_same_projected_kernel": True,
            "shardC_charges_use_same_selected_C7_stream": True,
            "all_prefix_total_cone_variation_budget": True,
            "no_final_carrier_magnitude_input": True,
            "no_sheath_cancellation_or_CF_import": True,
            "not_homogeneity_zero_pressure_riesz_only": True,
        },
        "concludes": {
            "FixedWindowTotalConeVariationChargeSource": True,
            "TraceFreeVariationConeLeakagePointwisePaymentReceipt": True,
            "TraceFreeVariationPointwiseSameCarrierPaymentReceipt": True,
        },
        "does_not_accept": [
            "pressureRieszConeCharge_pays_overflowExcess",
            "overflow_excess_only",
            "visible_overflow_charge_only",
            "selected_c7_fixed_window_cone_mass_rigidity_source",
            "fixed_window_overflow_visible_or_invisible_profile_only",
            "total_cone_tracefree_variation_payment_missing",
            "core_plus_sheath_not_paid",
            "same_window_sheath_cancellation_forbidden_only",
            "CF_or_direction_coherence",
            "pressure_riesz_degree_zero_carrier_only",
            "homogeneity_zero_obstruction_still_admissible",
            "final_carrier_magnitude",
            "balanced_core_sheath_dini_ladder_admissible",
            "overflow_summable_total_cone_dini_divergent",
        ],
    },
    "balanced_core_sheath_total_cone_gate": {
        "requires": {
            "core_stream_fixed_before_payoff": True,
            "sheath_stream_fixed_before_payoff": True,
            "overflow_stream_identified": True,
            "same_selected_prefix_map": True,
            "owner_map_fixed_before_payoff": True,
            "full_output_scale_cone_shardC_owner": True,
            "owner_charge_pays_core_plus_sheath": True,
            "owner_preimage_prefix_inequality": True,
            "not_overflow_only_budget": True,
            "balanced_core_sheath_dini_ladder_excluded_or_paid": True,
        },
        "concludes": {
            "TotalConeSelectedPrefixOwnerPreimageReceipt": True,
            "FixedWindowTotalConeVariationChargeSource": True,
        },
        "does_not_accept": [
            "overflow_excess_only",
            "visible_overflow_charge_only",
            "sum_overflow_finite_only",
            "sum_core_plus_sheath_diverges",
            "balanced_core_sheath_dini_ladder_admissible",
            "overflow_summable_total_cone_dini_divergent",
            "owner_map_label_only",
            "same_selected_prefix_label_only",
            "full_output_scale_owner_missing",
            "multiplicity_bound_missing",
            "owner_preimage_prefix_inequality_missing",
            "projected_visibility_reuse_without_owner_preimage",
            "square_or_signed_currency_only",
            "final_carrier_magnitude",
            "same_window_sheath_cancellation_forbidden_only",
            "CF_or_direction_coherence",
        ],
    },
    "balanced_core_sheath_dynamic_transversality_gate": {
        "requires": {
            "balanced_core_sheath_dini_ladder_packet": True,
            "packet_encodes_near_stealth_balanced_cone": True,
            "ns_vector_field_transverse_to_stealth_manifold": True,
            "exposure_time_less_than_selected_reset_dwell": True,
            "selected_prefix_requires_reset_dwell": True,
            "transversality_fixed_before_owner_budget": True,
            "no_retuning_higher_jets_after_payoff": True,
            "uniform_same_owner_full_jet_transversality_modulo_ns_constraints": True,
            "not_static_geometry_only": True,
        },
        "concludes": {
            "BalancedCoreSheathDiniDynamicTransversalityReceipt": True,
            "balanced_core_sheath_dini_ladder_excluded_or_paid": True,
        },
        "does_not_accept": [
            "static_cone_geometry_only",
            "single_sample_phase5at_only",
            "directional_derivative_audit_only",
            "transversality_not_uniform",
            "dwell_time_not_bound_to_selected_prefix",
            "higher_jet_retuning_still_admissible",
            "higher_jet_tangency_reset_confuser",
            "full_jet_transversality_missing",
            "material_derivative_lower_bound_missing",
            "second_order_transversality_missing",
            "balanced_core_sheath_dini_ladder_admissible",
            "CF_or_direction_coherence",
            "final_carrier_magnitude",
        ],
    },
    "balanced_core_sheath_trace_zero_positive_net_budget_confuser_gate": {
        "requires": {
            "balanced_core_sheath_dini_ladder_packet": True,
            "trace_zero_strain": True,
            "stretching_eigenvalue_positive": True,
            "transverse_compensation": True,
            "same_owner_selected_stream": True,
            "production_equals_one_plus_eta_times_A": True,
            "dissipation_equals_A": True,
            "eta_positive": True,
            "A_positive": True,
        },
        "concludes": {
            "TraceZeroStrainPositiveNetBudgetJet": True,
            "BalancedCoreSheathSignedBudgetGapConfuser": True,
            "positive_same_trajectory_net_budget": True,
        },
        "does_not_accept": [
            "trace_not_zero",
            "stretching_not_same_trajectory",
            "production_not_signed_global",
            "dissipation_not_same_segment",
            "eta_nonpositive",
            "A_nonpositive",
            "budget_from_different_trajectory",
        ],
    },
    "local_affine_trace_zero_positive_stretching_confuser_gate": {
        "requires": {
            "time_dependent_local_affine_jet": True,
            "trace_zero_strain": True,
            "vorticity_aligned_with_positive_strain_eigenvector": True,
            "local_vorticity_gradient_zero": True,
            "local_vorticity_diffusion_zero": True,
            "skew_time_derivative_pays_affine_equation": True,
            "pressure_hessian_pays_symmetric_affine_equation": True,
            "production_equals_one_plus_eta_times_A": True,
            "dissipation_equals_A": True,
            "eta_positive": True,
            "A_positive": True,
            "finite_energy_cutoff_invoice_unpaid": True,
        },
        "concludes": {
            "LocalAffineTraceZeroPositiveStretchingJet": True,
            "TraceZeroStrainPositiveNetBudgetJet": True,
            "purely_local_dynamic_inadmissibility_killed": True,
        },
        "does_not_accept": [
            "stationary_affine_jet",
            "frozen_affine_pressure_compatibility",
            "finite_energy_c7_tent_claim",
            "cutoff_invoice_paid_by_declaration",
            "pressure_visibility_only",
            "rank5_tomography_without_global_budget",
            "CF_or_direction_coherence",
        ],
    },
    "localized_c7_tent_cutoff_invoice_dominates_positive_stretching_gate": {
        "requires": {
            "time_dependent_local_affine_jet": True,
            "same_owner_selected_c7_tent": True,
            "finite_energy_cutoff_constructed_before_payoff": True,
            "cutoff_invoice_nonnegative": True,
            "leray_projection_invoice_nonnegative": True,
            "pressure_tail_invoice_nonnegative": True,
            "no_reuse_invoice_nonnegative": True,
            "pressure_leray_tail_charged_to_same_tent": True,
            "section_identity_fixed_before_invoice": True,
            "no_reuse_across_nested_selected_tents": True,
            "surplus_equals_eta_times_A": True,
            "invoice_sum_dominates_surplus": True,
            "no_CF_or_other_Clay_equivalent_input_used": True,
        },
        "concludes": {
            "LocalizedC7TentCutoffInvoiceDominatesPositiveStretching": True,
            "finite_energy_cutoff_invoice_paid": True,
            "purely_local_affine_confuser_not_enough": True,
        },
        "does_not_accept": [
            "local_affine_trace_zero_positive_stretching_only",
            "stationary_affine_jet",
            "dimensionless_ratio_only",
            "cutoff_invoice_paid_by_declaration",
            "pressure_tail_on_proxy_tent",
            "leray_projection_l1_payment_missing",
            "nested_selected_tent_reuse",
            "section_identity_missing",
            "positive_net_budget_leak_packet",
            "CF_or_direction_coherence",
        ],
    },
    "localized_c7_tent_scaling_leak_certificate_gate": {
        "requires": {
            "time_dependent_local_affine_jet": True,
            "same_owner_selected_c7_tent": True,
            "finite_energy_high_pi_regime": True,
            "surplus_equals_eta_times_A": True,
            "theta_nonnegative": True,
            "theta_strictly_below_one": True,
            "total_invoice_equals_cutoff_leray_pressure_no_reuse_sum": True,
            "total_invoice_le_theta_surplus": True,
            "cutoff_leray_pressure_no_reuse_invoices_on_same_tent": True,
            "source_contract_aligned_to_affine_tent": True,
        },
        "concludes": {
            "LocalizedC7TentScalingLeakCertificate": True,
            "LocalizedC7TentCutoffInvoiceLeakPacket": True,
            "localized_c7_invoice_dominance_killed_for_same_invoice": True,
        },
        "does_not_accept": [
            "dimensionless_ratio_only",
            "local_affine_trace_zero_positive_stretching_only",
            "pressure_visibility_only",
            "profile_schur_carleson_envelope_label_only",
            "different_owner_invoice",
            "theta_chosen_after_payoff",
            "invoice_sum_dominates_surplus",
        ],
    },
    "parabolic_cutoff_invoice_underpaid_leak_model_gate": {
        "requires": {
            "time_dependent_local_affine_jet": True,
            "same_owner_selected_c7_tent": True,
            "parabolic_active_scale_owner_stream": True,
            "finite_energy_high_pi_regime": True,
            "active_scale_normalization_A_equals_cutoff_unit": True,
            "cutoff_invoice_equals_c_cut_times_A": True,
            "total_invoice_equals_cutoff_invoice": True,
            "theta_nonnegative": True,
            "theta_strictly_below_one": True,
            "cutoff_constant_le_theta_eta": True,
            "cutoff_leray_pressure_no_reuse_invoices_on_same_tent": True,
            "source_contract_aligned_to_affine_tent": True,
        },
        "concludes": {
            "ParabolicCutoffInvoiceUnderpaidLeakModel": True,
            "LocalizedC7TentScalingLeakCertificate": True,
            "eta_bound_missing_kills_cutoff_payment_route": True,
        },
        "does_not_accept": [
            "eta_le_cutoff_constant",
            "invoice_sum_dominates_surplus",
            "theta_chosen_after_payoff",
            "different_owner_invoice",
            "cutoff_invoice_paid_by_declaration",
        ],
    },
    "parabolic_cutoff_invoice_pays_affine_surplus_model_gate": {
        "requires": {
            "time_dependent_local_affine_jet": True,
            "same_owner_selected_c7_tent": True,
            "parabolic_active_scale_owner_stream": True,
            "finite_energy_cutoff_constructed_before_payoff": True,
            "active_scale_normalization_A_equals_cutoff_unit": True,
            "cutoff_invoice_equals_c_cut_times_A": True,
            "eta_le_cutoff_constant": True,
            "cutoff_invoice_le_total_invoice": True,
            "duhamel_reserve_separated_before_invoice": True,
            "inherited_reserve_separated_before_invoice": True,
            "selected_partition_fixed_before_invoice": True,
            "section_identity_fixed_before_invoice": True,
            "no_reuse_all_prefix_linear_budget": True,
            "rejects_final_carrier_only_pressure": True,
            "rejects_overflow_only_or_square_budget_payment": True,
            "no_CF_or_other_Clay_equivalent_input_used": True,
        },
        "concludes": {
            "ParabolicCutoffInvoicePaysAffineSurplusModel": True,
            "ParabolicFiniteEnergyInvoiceLowerBoundForLocalizedAffineTent": True,
            "strict_fraction_scaling_leak_excluded_in_normalized_small_surplus_case": True,
        },
        "does_not_accept": [
            "dimensionless_ratio_only",
            "eta_chosen_after_cutoff_constant",
            "active_scale_normalization_missing",
            "cutoff_invoice_paid_by_declaration",
            "final_carrier_only_pressure",
            "overflow_only_payment",
            "square_budget_only_payment",
            "CF_or_direction_coherence",
            "different_owner_invoice",
        ],
    },
    "proxy_section_absolute_interface_variation_packet_gate": {
        "requires": {
            "signed_transport_commutator_cancellation_packet": True,
            "absolute_interface_variation_exists": True,
            "absolute_variation_on_proxy_section": True,
            "selected_prefix_absolute_variation_missing": True,
            "section_fixed_before_payoff_for_selected_prefix_missing": True,
        },
        "concludes": {
            "ProxySectionAbsoluteInterfaceVariationPacket": True,
            "SectionFixedAbsoluteInterfaceVariationPaymentSource_excluded_for_same_data": True,
            "selected_section_binding_required": True,
        },
        "does_not_accept": [
            "absolute_interface_variation_on_same_selected_owner_prefix",
            "section_fixed_before_payoff_for_selected_prefix",
            "absolute_variation_exists_only",
            "proxy_section_repaired_after_payoff",
        ],
    },
    "post_payoff_section_repair_packet_gate": {
        "requires": {
            "proxy_section_absolute_interface_variation_packet": True,
            "proxy_section_repaired_after_payoff": True,
            "selected_section_identity_fixed_before_payoff_missing": True,
            "selected_absolute_variation_lower_bound_missing": True,
        },
        "concludes": {
            "PostPayoffSectionRepairPacket": True,
            "SelectedSectionAbsoluteInterfaceVariationIdentitySource_excluded_for_same_data": True,
            "pre_payoff_selected_section_identity_required": True,
        },
        "does_not_accept": [
            "selected_section_identity_fixed_before_payoff",
            "selected_section_equals_localized_packet_interface_section",
            "reynolds_excess_le_selected_absolute_variation",
            "owner_preimage_pays_selected_absolute_variation",
        ],
    },
    "selected_section_absolute_interface_variation_identity_source_gate": {
        "requires": {
            "section_fixed_absolute_interface_variation_payment_source": True,
            "selected_section_identity_fixed_before_payoff": True,
            "selected_section_equals_localized_packet_interface_section": True,
            "proxy_section_excluded_or_mapped_to_selected_prefix": True,
            "selected_absolute_variation_eq_absolute_interface_variation": True,
            "reynolds_excess_le_selected_absolute_variation": True,
            "owner_preimage_pays_selected_absolute_variation": True,
        },
        "concludes": {
            "SelectedSectionAbsoluteInterfaceVariationIdentitySource": True,
            "SectionFixedAbsoluteInterfaceVariationPaymentSource": True,
            "LocalizedAffineEulerCoreHighPiInterfacePaymentSource": True,
            "selected_section_binding_paid_before_payoff": True,
        },
        "does_not_accept": [
            "proxy_section_repaired_after_payoff",
            "selected_section_label_only",
            "absolute_variation_exists_only",
            "owner_label_without_preimage_payment",
            "selected_absolute_variation_bound_after_payoff",
        ],
    },
    "section_label_only_interface_variation_oracle_ambiguity_packet_gate": {
        "requires": {
            "post_payoff_section_repair_packet": True,
            "same_section_identity_labels_fixed": True,
            "lower_envelope_or_scalar_data_fixed": True,
            "extensional_interface_variation_measure_missing": True,
            "two_compatible_selected_variation_values": True,
        },
        "concludes": {
            "SectionLabelOnlyInterfaceVariationOracleAmbiguityPacket": True,
            "SelectedSectionExtensionalInterfaceVariationMeasureSource_excluded_for_same_data": True,
            "extensional_interface_measure_required": True,
        },
        "does_not_accept": [
            "section_identity_label_only",
            "lower_envelope_scalar_only",
            "selected_absolute_variation_asserted_without_measure",
            "post_payoff_measure_repair",
        ],
    },
    "selected_section_extensional_interface_variation_measure_source_gate": {
        "requires": {
            "selected_section_absolute_interface_variation_identity_source": True,
            "interface_variation_measure_nonnegative": True,
            "selected_absolute_variation_eq_interface_variation_measure": True,
            "interface_variation_measure_constructed_from_cutoff_formula": True,
            "extensional_measure_fixed_before_section_repair": True,
            "not_determined_by_section_label_or_lower_envelope_only": True,
            "reynolds_excess_le_selected_absolute_variation": True,
        },
        "concludes": {
            "SelectedSectionExtensionalInterfaceVariationMeasureSource": True,
            "SelectedSectionAbsoluteInterfaceVariationIdentitySource": True,
            "SectionFixedAbsoluteInterfaceVariationPaymentSource": True,
            "oracle_ambiguity_avoided_by_extensional_measure": True,
        },
        "does_not_accept": [
            "section_identity_label_only",
            "lower_envelope_scalar_only",
            "extensional_interface_variation_measure_missing",
            "selected_absolute_variation_asserted_without_measure",
            "post_payoff_measure_repair",
        ],
    },
    "raw_positive_eigencone_loss_unpaid_packet_gate": {
        "requires": {
            "section_label_only_interface_variation_oracle_ambiguity_packet": True,
            "positive_eigencone_exists": True,
            "raw_cone_variation_pays_only_geometric_fraction": True,
            "cone_loss_paid_before_projection_missing": True,
            "raw_cone_interface_variation_lt_reynolds_excess": True,
        },
        "concludes": {
            "RawPositiveEigenconeLossUnpaidPacket": True,
            "AffinePositiveEigenconeLossPaidInterfaceVariationSource_excluded_for_same_data": True,
            "cone_loss_payment_required": True,
        },
        "does_not_accept": [
            "raw_cone_variation_only",
            "cone_constant_ignored",
            "normalized_after_projection",
            "angular_lower_bound_without_loss_payment",
        ],
    },
    "affine_positive_eigencone_loss_paid_interface_variation_source_gate": {
        "requires": {
            "selected_section_extensional_interface_variation_measure_source": True,
            "cone_constant_positive": True,
            "raw_cone_interface_variation_nonnegative": True,
            "positive_eigencone_fixed_before_payoff": True,
            "selected_section_contained_in_positive_eigencone": True,
            "radial_strain_abs_lower_bound_on_cone": True,
            "active_scale_pi_pinned_as_sR2_over_nu": True,
            "raw_cone_variation_pays_geometric_fraction": True,
            "cone_loss_paid_before_projection": True,
            "selected_absolute_variation_eq_cone_normalized_variation": True,
        },
        "concludes": {
            "AffinePositiveEigenconeLossPaidInterfaceVariationSource": True,
            "SelectedSectionExtensionalInterfaceVariationMeasureSource": True,
            "SelectedSectionAbsoluteInterfaceVariationIdentitySource": True,
            "raw_cone_loss_paid_before_projection": True,
        },
        "does_not_accept": [
            "raw_cone_variation_only",
            "cone_constant_ignored",
            "normalized_after_projection",
            "positive_eigencone_label_only",
            "dimensionless_pi_without_physical_ratio",
        ],
    },
    "localized_affine_eigenframe_section_binding_source_gate": {
        "requires": {
            "affine_positive_eigencone_loss_paid_interface_variation_source": True,
            "positive_eigenvalue_nonnegative": True,
            "trace_zero_eigenvalue_sum": True,
            "remaining_eigenvalue_le_positive_eigenvalue": True,
            "selected_direction_in_fixed_cone": True,
            "selected_direction_cos_sq_le_one": True,
            "active_scale_strain_eq_positive_eigenvalue": True,
            "selected_section_cone_inclusion_from_packet_geometry": True,
        },
        "concludes": {
            "LocalizedAffineEigenframeSectionBindingSource": True,
            "AffinePositiveEigenconeLossPaidInterfaceVariationSource": True,
            "finite_dimensional_cone_lower_bound_available": True,
        },
        "does_not_accept": [
            "eigenframe_label_only",
            "selected_cone_label_without_inclusion",
            "active_scale_label_without_eigenvalue_equality",
            "trace_zero_missing",
            "max_eigenvalue_ordering_missing",
        ],
    },
    "eigenframe_label_without_selected_cone_inclusion_packet_gate": {
        "requires": {
            "raw_positive_eigencone_loss_unpaid_packet": True,
            "affine_eigenframe_label_exists": True,
            "positive_eigenvalue_label_exists": True,
            "selected_cone_inclusion_missing": True,
            "active_scale_eigenvalue_equality_missing": True,
        },
        "concludes": {
            "EigenframeLabelWithoutSelectedConeInclusionPacket": True,
            "LocalizedAffineEigenframeSectionBindingSource_excluded_for_same_data": True,
            "selected_cone_inclusion_required": True,
        },
        "does_not_accept": [
            "eigenframe_label_only",
            "positive_eigenvalue_label_only",
            "selected_cone_label_without_inclusion",
            "active_scale_label_without_eigenvalue_equality",
        ],
    },
    "spatial_support_eigencone_mismatch_packet_gate": {
        "requires": {
            "eigenframe_label_without_selected_cone_inclusion_packet": True,
            "positive_stretching_eigenvector_exists": True,
            "selected_spatial_support_outside_positive_eigencone": True,
            "tangent_eigenvector_not_spatial_support_receipt": True,
        },
        "concludes": {
            "SpatialSupportEigenconeMismatchPacket": True,
            "LocalizedAffineEigenframeSectionBindingSource_excluded_for_same_data": True,
            "spatial_support_cone_receipt_required": True,
        },
        "does_not_accept": [
            "positive_stretching_direction_only",
            "vorticity_alignment_only",
            "eigenvector_label_as_spatial_support",
            "selected_section_label_without_spatial_inclusion",
        ],
    },
    "angular_cone_cutoff_boundary_invoice_unpaid_packet_gate": {
        "requires": {
            "raw_positive_eigencone_loss_unpaid_packet": True,
            "selected_spatial_support_inside_positive_eigencone": True,
            "angular_cone_cutoff_introduces_boundary_invoice": True,
            "angular_boundary_invoice_paid_missing": True,
            "posthoc_cone_rotation_would_pay_only_after_selection": True,
        },
        "concludes": {
            "AngularConeCutoffBoundaryInvoiceUnpaidPacket": True,
            "ConeLocalizedAffinePacketGeometrySource_excluded_for_same_data": True,
            "angular_cutoff_boundary_invoice_required": True,
        },
        "does_not_accept": [
            "spatial_cone_support_only",
            "angular_cutoff_invoice_ignored",
            "posthoc_cone_rotation",
            "cone_selection_without_boundary_invoice",
        ],
    },
    "cone_localized_affine_packet_geometry_source_gate": {
        "requires": {
            "localized_affine_eigenframe_section_binding_source": True,
            "selected_spatial_support_is_positive_eigencone_cutoff": True,
            "cone_aperture_fixed_by_eigenframe_before_payoff": True,
            "angular_cutoff_fixed_before_payoff": True,
            "angular_cone_cutoff_boundary_invoice_nonnegative": True,
            "angular_cutoff_boundary_invoice_paid": True,
            "selected_support_cone_receipt_no_posthoc_rotation": True,
            "no_angular_boundary_rebilling": True,
        },
        "concludes": {
            "ConeLocalizedAffinePacketGeometrySource": True,
            "LocalizedAffineEigenframeSectionBindingSource": True,
            "spatial_support_cone_receipt_paid": True,
        },
        "does_not_accept": [
            "spatial_cone_support_only",
            "angular_cutoff_invoice_ignored",
            "posthoc_cone_rotation",
            "cone_selection_without_boundary_invoice",
            "selected_support_label_only",
        ],
    },
    "angular_cone_cutoff_boundary_invoice_payment_source_gate": {
        "requires": {
            "cone_localized_affine_packet_geometry_source": True,
            "angular_cutoff_boundary_to_same_owner_invoice_exchange": True,
            "angular_boundary_invoice_billed_to_same_selected_prefix": True,
            "angular_boundary_invoice_fixed_before_projection": True,
            "angular_boundary_invoice_le_total_invoice": True,
            "angular_boundary_production_spend_nonnegative": True,
            "angular_boundary_pressure_reserve_spend_nonnegative": True,
            "angular_boundary_duhamel_reserve_spend_nonnegative": True,
            "angular_boundary_inherited_reserve_spend_nonnegative": True,
            "angular_boundary_partition_single_spend": True,
            "angular_boundary_section_identity_fixed_before_projection": True,
            "angular_boundary_invoice_channel_separated": True,
            "no_reuse_angular_boundary_spend": True,
            "angular_boundary_spend_sum_le_invoice": True,
            "no_angular_boundary_double_spend": True,
        },
        "concludes": {
            "AngularConeCutoffBoundaryInvoicePaymentSource": True,
            "ConeLocalizedAffinePacketGeometrySource": True,
            "same_owner_angular_boundary_invoice_paid": True,
        },
        "does_not_accept": [
            "angular_cutoff_invoice_ignored",
            "boundary_invoice_paid_by_declaration",
            "post_projection_boundary_payment",
            "same_owner_label_without_invoice_channel",
            "angular_boundary_reused_as_main_surplus",
        ],
    },
    "thin_angular_collar_boundary_amplification_packet_gate": {
        "requires": {
            "angular_cone_cutoff_boundary_invoice_unpaid_packet": True,
            "selected_spatial_support_inside_positive_eigencone": True,
            "angular_collar_width_positive": True,
            "angular_derivative_scale_inverse_width": True,
            "angular_boundary_invoice_nonnegative": True,
            "total_invoice_lt_angular_boundary_invoice": True,
        },
        "concludes": {
            "ThinAngularCollarBoundaryAmplificationPacket": True,
            "AngularConeCutoffBoundaryInvoicePaymentSource_excluded_for_same_data": True,
            "angular_boundary_invoice_le_total_invoice_required": True,
        },
        "does_not_accept": [
            "dimensionless_collar_label_only",
            "angular_width_without_derivative_scale",
            "boundary_invoice_paid_by_total_label",
            "total_invoice_ge_boundary_invoice",
        ],
    },
    "fixed_profile_angular_collar_charge_source_gate": {
        "requires": {
            "cone_localized_affine_packet_geometry_source": True,
            "fixed_angular_profile_before_projection": True,
            "angular_profile_constant_nonnegative": True,
            "angular_collar_mass_nonnegative": True,
            "angular_boundary_invoice_eq_profile_constant_times_collar_mass": True,
            "profile_constant_times_collar_mass_le_total_invoice": True,
            "same_prefix_angular_collar_mass_charge": True,
            "angular_collar_production_spend_nonnegative": True,
            "angular_collar_production_spend_eq_boundary_invoice": True,
            "angular_collar_pressure_reserve_spend_nonnegative": True,
            "angular_collar_duhamel_reserve_spend_nonnegative": True,
            "angular_collar_inherited_reserve_spend_nonnegative": True,
            "angular_collar_partition_single_spend": True,
            "angular_collar_section_identity_fixed_before_projection": True,
            "angular_collar_mass_separated_from_main_surplus": True,
            "angular_collar_spend_sum_le_boundary_invoice": True,
            "no_reuse_angular_collar_mass": True,
        },
        "concludes": {
            "FixedProfileAngularCollarChargeSource": True,
            "AngularConeCutoffBoundaryInvoicePaymentSource": True,
            "thin_angular_collar_spike_excluded_by_profile_bound": True,
        },
        "does_not_accept": [
            "dimensionless_collar_label_only",
            "fixed_profile_label_without_norm",
            "collar_mass_not_same_prefix",
            "profile_bound_after_projection",
            "collar_mass_reused_as_main_surplus",
        ],
    },
    "angular_coarea_collar_selection_source_gate": {
        "requires": {
            "fixed_profile_angular_collar_charge_source": True,
            "aperture_interval_length_positive": True,
            "angular_collar_width_positive": True,
            "total_angular_cone_mass_nonnegative": True,
            "coarea_collar_charge_nonnegative": True,
            "threshold_selected_by_pre_payoff_coarea": True,
            "selected_threshold_preserves_eigencone_lower_bound": True,
            "coarea_average_controls_collar_mass": True,
            "profile_constant_times_collar_mass_le_coarea_charge": True,
            "coarea_charge_le_total_invoice": True,
            "no_posthoc_threshold_rotation": True,
        },
        "concludes": {
            "AngularCoareaCollarSelectionSource": True,
            "FixedProfileAngularCollarChargeSource": True,
            "dimensionless_angular_collar_spike_excluded_by_coarea_selection": True,
        },
        "does_not_accept": [
            "posthoc_threshold_rotation",
            "coarea_average_label_only",
            "threshold_selected_after_payoff",
            "eigencone_lower_bound_lost_by_threshold_choice",
            "coarea_charge_not_billed_to_total_invoice",
        ],
    },
    "owner_preimage_coarea_collar_charge_source_gate": {
        "requires": {
            "angular_coarea_collar_selection_source": True,
            "threshold_owner_map_fixed_before_payoff": True,
            "threshold_collar_charge_nonnegative": True,
            "owner_collar_budget_nonnegative": True,
            "selected_threshold_charge_eq_coarea_charge": True,
            "pointwise_threshold_charge_le_owner_budget": True,
            "selected_prefix_owner_collar_budget": True,
            "selected_threshold_charge_le_owner_root_budget": True,
            "owner_root_budget_le_total_invoice": True,
            "bounded_threshold_owner_multiplicity": True,
            "selected_threshold_owner_same_prefix": True,
            "no_reuse_owner_collar_budget": True,
        },
        "concludes": {
            "OwnerPreimageCoareaCollarChargeSource": True,
            "AngularCoareaCollarSelectionSource": True,
            "coarea_charge_le_total_invoice_from_owner_prefix": True,
        },
        "does_not_accept": [
            "owner_label_without_preimage_budget",
            "prefix_budget_without_selected_threshold_membership",
            "threshold_owner_map_after_payoff",
            "owner_budget_reused_as_main_surplus",
            "coarea_charge_local_only",
        ],
    },
    "preprojection_projected_collar_exchange_source_gate": {
        "requires": {
            "owner_preimage_coarea_collar_charge_source": True,
            "projected_angular_boundary_payment_nonnegative": True,
            "projection_tail_reserve_nonnegative": True,
            "projected_payment_le_preprojection_plus_tail": True,
            "projection_tail_reserve_le_total_invoice": True,
            "projection_tail_reserve_paid_on_same_source_window": True,
            "preprojection_collar_identity_before_projection": True,
            "no_projected_spend_without_tail_reserve": True,
            "projected_collar_no_reuse": True,
        },
        "concludes": {
            "PreprojectionProjectedCollarExchangeSource": True,
            "projected_payment_le_two_total_invoice": True,
            "projection_tail_reserve_paid": True,
        },
        "does_not_accept": [
            "preprojection_payment_spent_as_projected_target",
            "projection_tail_reserve_missing",
            "same_source_window_label_without_tail_invoice",
            "projected_payment_declared_after_projection",
        ],
    },
    "projection_tail_reserve_unpaid_packet_gate": {
        "requires": {
            "owner_preimage_coarea_collar_charge_source": True,
            "projected_angular_boundary_payment_nonnegative": True,
            "preprojection_collar_paid": True,
            "projection_tail_reserve_missing": True,
            "projected_payment_exceeds_preprojection_collar_charge": True,
        },
        "concludes": {
            "ProjectionTailReserveUnpaidPacket": True,
            "PreprojectionProjectedCollarExchangeSource_excluded_for_same_data": True,
            "projection_tail_reserve_required": True,
        },
        "does_not_accept": [
            "owner_preimage_payment_only",
            "tail_reserve_label_only",
            "projected_payment_le_preprojection_plus_tail",
            "same_source_window_label_without_tail_invoice",
        ],
    },
    "shared_partition_projected_collar_invoice_source_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "collar_invoice_channel_nonnegative": True,
            "tail_reserve_invoice_channel_nonnegative": True,
            "coarea_collar_charge_le_collar_channel": True,
            "projection_tail_reserve_le_tail_channel": True,
            "collar_tail_channels_le_total_invoice": True,
            "collar_tail_partition_fixed_before_projection": True,
            "collar_tail_channels_same_owner_prefix": True,
            "collar_tail_no_reuse_as_main_surplus": True,
        },
        "concludes": {
            "SharedPartitionProjectedCollarInvoiceSource": True,
            "projected_payment_le_total_invoice": True,
            "factor_two_projection_loss_removed": True,
        },
        "does_not_accept": [
            "collar_and_tail_each_use_separate_total_invoice",
            "shared_partition_missing",
            "tail_reserve_paid_by_second_budget",
            "collar_tail_no_reuse_label_only",
        ],
    },
    "two_invoice_projection_loss_packet_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "collar_and_tail_each_use_separate_total_invoice": True,
            "shared_partition_missing": True,
            "total_invoice_lt_projected_payment": True,
        },
        "concludes": {
            "TwoInvoiceProjectionLossPacket": True,
            "SharedPartitionProjectedCollarInvoiceSource_excluded_for_same_data": True,
            "shared_partition_required": True,
        },
        "does_not_accept": [
            "factor_two_bound_only",
            "collar_tail_channels_le_total_invoice",
            "single_budget_label_without_channel_split",
        ],
    },
    "joint_owner_root_collar_tail_partition_source_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "joint_collar_tail_channel_nonnegative": True,
            "collar_plus_tail_le_joint_channel": True,
            "joint_channel_le_owner_root_budget": True,
            "existing_collar_reserve_spend_nonnegative": True,
            "existing_collar_reserve_spend_eq_pressure_duhamel_inherited": True,
            "projection_tail_plus_existing_reserve_no_overlap_bound": True,
            "joint_channel_declared_before_payoff_step_lt_projected_payoff_step": True,
            "same_owner_joint_channel_le_owner_root_budget": True,
            "main_surplus_spend_nonnegative": True,
            "joint_channel_no_reuse_with_main_surplus_spend": True,
            "joint_channel_fixed_before_projection": True,
            "joint_channel_refines_owner_preimage": True,
            "joint_channel_no_overlap_with_existing_collar_reserves": True,
            "joint_channel_not_defined_from_payoff": True,
        },
        "concludes": {
            "JointOwnerRootCollarTailPartitionSource": True,
            "projected_payment_le_owner_root_budget": True,
            "projected_payment_le_total_invoice": True,
            "tail_plus_existing_reserves_le_owner_root_budget": True,
            "joint_plus_main_surplus_le_owner_root_budget": True,
        },
        "does_not_accept": [
            "collar_tail_channels_le_total_invoice_only",
            "owner_prefix_prop_without_owner_root_channel_bound",
            "projection_tail_overlaps_existing_collar_reserve",
            "joint_channel_defined_from_payoff",
            "no_overlap_prop_without_numeric_overlap_reserve_bound",
            "no_reuse_prop_without_main_surplus_sum_bound",
        ],
    },
    "collar_tail_overlap_rebilling_packet_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "collar_tail_overlap_same_cutoff_reserve": True,
            "projection_tail_overlaps_existing_collar_reserve": True,
            "joint_owner_root_channel_missing": True,
            "owner_root_budget_lt_projected_payment": True,
        },
        "concludes": {
            "CollarTailOverlapRebillingPacket": True,
            "JointOwnerRootCollarTailPartitionSource_excluded_for_same_data": True,
            "joint_owner_root_channel_required": True,
        },
        "does_not_accept": [
            "same_source_window_label_only",
            "collar_tail_no_reuse_as_main_surplus_only",
            "tail_reserve_paid_by_second_owner_budget",
            "overlap_named_without_owner_root_gap",
        ],
    },
    "finite_projected_window_no_overlap_assignment_source_gate": {
        "requires": {
            "joint_owner_root_collar_tail_partition_source": True,
            "tail_prefix_charge_nonnegative": True,
            "reserve_prefix_charge_nonnegative": True,
            "assignment_overlap_reserve_nonnegative": True,
            "projection_tail_reserve_le_tail_prefix_charge": True,
            "existing_reserve_spend_le_reserve_prefix_charge": True,
            "finite_tail_reserve_prefixes_le_joint_channel_plus_overlap": True,
            "assignment_overlap_reserve_eq_zero": True,
            "assignment_fixed_before_projection": True,
            "tail_reserve_assignment_same_carrier": True,
            "no_overlap_assignment_persists_to_projected_window": True,
            "limit_passage_inheritance_lemma_named": True,
        },
        "concludes": {
            "FiniteProjectedWindowNoOverlapAssignmentSource": True,
            "projection_tail_plus_existing_reserve_no_overlap_bound_from_assignment": True,
            "tail_plus_existing_reserves_le_owner_root_budget_from_assignment": True,
        },
        "does_not_accept": [
            "finite_assignment_without_projection_persistence",
            "overlap_reserve_positive_unpaid",
            "same_carrier_label_without_assignment_map",
            "limit_passage_lemma_missing",
        ],
    },
    "projection_window_no_overlap_persistence_failure_packet_gate": {
        "requires": {
            "joint_owner_root_collar_tail_partition_source": True,
            "finite_assignment_before_projection": True,
            "no_overlap_holds_before_projection": True,
            "no_overlap_persistence_lemma_missing": True,
            "projected_window_reintroduces_overlap": True,
            "owner_root_budget_lt_tail_plus_existing_reserve": True,
        },
        "concludes": {
            "ProjectionWindowNoOverlapPersistenceFailurePacket": True,
            "FiniteProjectedWindowNoOverlapAssignmentSource_excluded_for_same_data": True,
            "projection_window_persistence_lemma_required": True,
        },
        "does_not_accept": [
            "finite_no_overlap_only",
            "projection_window_label_without_inheritance",
            "assignment_map_no_limit_passage",
        ],
    },
    "paid_overlap_projected_window_assignment_source_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "joint_collar_tail_channel_nonnegative": True,
            "existing_collar_reserve_spend_nonnegative": True,
            "existing_collar_reserve_spend_eq_pressure_duhamel_inherited": True,
            "paid_projected_overlap_reserve_nonnegative": True,
            "collar_plus_tail_le_joint_plus_paid_overlap": True,
            "tail_plus_existing_reserve_le_joint_plus_paid_overlap": True,
            "joint_plus_paid_overlap_le_owner_root_budget": True,
            "joint_channel_declared_before_payoff_step_lt_projected_payoff_step": True,
            "paid_overlap_declared_before_payoff_step_lt_projected_payoff_step": True,
            "main_surplus_spend_nonnegative": True,
            "joint_paid_overlap_no_reuse_with_main_surplus_spend": True,
            "paid_overlap_reserve_fixed_before_projection": True,
            "paid_overlap_reserve_same_owner_root": True,
            "paid_overlap_reserve_refines_projected_window_overlap": True,
            "paid_overlap_reserve_not_defined_from_payoff": True,
        },
        "concludes": {
            "PaidOverlapProjectedWindowAssignmentSource": True,
            "projected_payment_le_owner_root_budget": True,
            "tail_plus_existing_reserves_le_owner_root_budget": True,
            "joint_paid_overlap_main_surplus_le_owner_root_budget": True,
        },
        "does_not_accept": [
            "zero_overlap_source_reused_as_paid_overlap_source",
            "overlap_reserve_positive_unpaid",
            "paid_overlap_defined_after_projected_payoff",
            "overlap_reserve_from_second_owner_budget",
            "same_owner_label_without_joint_plus_paid_numeric_bound",
        ],
    },
    "finite_projected_window_paid_nonzero_overlap_reserve_source_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "joint_collar_tail_channel_nonnegative": True,
            "paid_overlap_reserve_nonnegative": True,
            "paid_overlap_reserve_positive": True,
            "collar_plus_tail_le_joint_channel": True,
            "joint_plus_paid_overlap_le_owner_root_budget": True,
            "same_owner_paid_overlap_reserve_le_owner_root_budget": True,
            "existing_collar_reserve_spend_nonnegative": True,
            "existing_collar_reserve_spend_eq_pressure_duhamel_inherited": True,
            "tail_prefix_charge_nonnegative": True,
            "reserve_prefix_charge_nonnegative": True,
            "projection_tail_reserve_le_tail_prefix_charge": True,
            "existing_reserve_spend_le_reserve_prefix_charge": True,
            "finite_tail_reserve_prefixes_le_joint_channel_plus_paid_overlap": True,
            "joint_channel_declared_before_payoff_step_lt_projected_payoff_step": True,
            "paid_overlap_declared_before_payoff_step_lt_projected_payoff_step": True,
            "paid_overlap_reserve_fixed_before_projection": True,
            "paid_overlap_reserve_paid_on_same_owner_root_preimage": True,
            "paid_overlap_reserve_not_defined_from_payoff": True,
            "tail_reserve_assignment_same_carrier": True,
            "paid_overlap_assignment_persists_to_projected_window": True,
            "limit_passage_paid_overlap_reserve_inheritance_lemma_named": True,
            "main_surplus_spend_nonnegative": True,
            "joint_plus_paid_overlap_no_reuse_with_main_surplus": True,
        },
        "concludes": {
            "FiniteProjectedWindowPaidNonzeroOverlapReserveSource": True,
            "projected_payment_le_owner_root_budget": True,
            "tail_plus_existing_reserves_le_owner_root_budget": True,
            "joint_paid_overlap_main_surplus_le_owner_root_budget": True,
        },
        "does_not_accept": [
            "zero_overlap_source_substitution",
            "overlap_reserve_positive_unpaid",
            "paid_overlap_reserve_defined_from_payoff",
            "tail_reserve_paid_by_second_owner_budget",
            "paid_overlap_without_finite_assignment",
            "limit_passage_lemma_missing",
        ],
    },
    "four_way_owner_root_subpartition_source_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "joint_collar_tail_channel_nonnegative": True,
            "paid_overlap_reserve_nonnegative": True,
            "paid_overlap_reserve_positive": True,
            "existing_collar_reserve_spend_nonnegative": True,
            "existing_collar_reserve_spend_eq_pressure_duhamel_inherited": True,
            "tail_prefix_charge_nonnegative": True,
            "reserve_prefix_charge_nonnegative": True,
            "projection_tail_reserve_le_tail_prefix_charge": True,
            "existing_reserve_spend_le_reserve_prefix_charge": True,
            "finite_tail_reserve_prefixes_le_joint_channel_plus_paid_overlap": True,
            "collar_subchannel_nonnegative": True,
            "tail_subchannel_nonnegative": True,
            "overlap_subchannel_nonnegative": True,
            "main_surplus_subchannel_nonnegative": True,
            "coarea_collar_charge_le_collar_subchannel": True,
            "projection_tail_reserve_le_tail_subchannel": True,
            "paid_overlap_reserve_le_overlap_subchannel": True,
            "main_surplus_spend_nonnegative": True,
            "main_surplus_spend_le_main_surplus_subchannel": True,
            "joint_channel_le_collar_plus_tail_subchannels": True,
            "four_way_subchannels_le_owner_root_budget": True,
            "no_reuse_four_way_subchannels_le_owner_root_budget": True,
            "joint_channel_declared_before_payoff_step_lt_projected_payoff_step": True,
            "paid_overlap_declared_before_payoff_step_lt_projected_payoff_step": True,
            "four_way_subpartition_declared_before_payoff_step_lt_projected_payoff_step": True,
            "same_owner_paid_overlap_reserve_le_owner_root_budget": True,
            "four_way_subpartition_fixed_before_payoff": True,
            "four_way_subchannels_same_owner_root": True,
            "overlap_subchannel_not_reused_by_collar_tail_or_main": True,
            "paid_overlap_reserve_not_defined_from_payoff": True,
            "tail_reserve_assignment_same_carrier": True,
            "paid_overlap_assignment_persists_to_projected_window": True,
            "limit_passage_paid_overlap_reserve_inheritance_lemma_named": True,
        },
        "concludes": {
            "FourWayOwnerRootSubpartitionSource": True,
            "joint_paid_overlap_main_surplus_le_owner_root_budget_from_subpartition": True,
            "tail_plus_existing_reserves_le_owner_root_budget": True,
            "projected_payment_le_owner_root_budget": True,
            "PrePayoffOverlapPreimageSource": True,
            "paid_overlap_reserve_le_owner_root_budget_via_preimage": True,
        },
        "does_not_accept": [
            "angular_cutoff_invoice_used_as_one_blob",
            "overlap_subchannel_reuses_collar_tail_or_main",
            "four_way_partition_after_payoff",
            "same_owner_prop_without_subchannel_sum_bound",
        ],
    },
    "four_way_owner_root_rebilling_packet_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "overlap_reserve_reuses_collar_tail_or_main_spend": True,
            "four_way_subpartition_missing": True,
            "owner_root_budget_lt_joint_paid_overlap_main_surplus": True,
        },
        "concludes": {
            "FourWayOwnerRootRebillingPacket": True,
            "FourWayOwnerRootSubpartitionSource_excluded_for_same_data": True,
            "four_way_owner_root_subpartition_required": True,
        },
        "does_not_accept": [
            "bounded_overlap_without_subchannels",
            "overlap_reserve_from_ambient_total_invoice",
            "late_four_way_split",
        ],
    },
    "pre_payoff_overlap_preimage_source_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "paid_overlap_reserve_nonnegative": True,
            "source_overlap_charge_nonnegative": True,
            "paid_overlap_reserve_le_source_overlap_charge": True,
            "source_overlap_charge_le_owner_root_budget": True,
            "same_owner_source_overlap_charge_le_owner_root_budget": True,
            "no_reuse_source_overlap_charge_le_owner_root_budget": True,
            "overlap_preimage_declared_before_projection_step_lt_projected_payoff_step": True,
            "overlap_preimage_declared_before_payoff_step_lt_projected_payoff_step": True,
            "overlap_preimage_same_owner_root": True,
            "overlap_preimage_disjoint_from_collar_tail_and_main": True,
            "overlap_preimage_not_defined_from_projected_deficit": True,
        },
        "concludes": {
            "PrePayoffOverlapPreimageSource": True,
            "paid_overlap_reserve_le_owner_root_budget": True,
        },
        "does_not_accept": [
            "overlap_defined_after_projection",
            "overlap_reserve_defined_from_projected_deficit",
            "source_overlap_off_owner_root",
            "source_overlap_reuses_collar_tail_or_main",
        ],
    },
    "selected_interface_variation_coarea_overlap_lower_payment_source_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "paid_overlap_reserve_nonnegative": True,
            "selected_absolute_variation_nonnegative": True,
            "interface_variation_measure_nonnegative": True,
            "positive_kernel_tv_coupling_mass_nonnegative": True,
            "localized_schur_owner_charge_nonnegative": True,
            "selected_absolute_variation_eq_interface_variation_measure": True,
            "paid_overlap_reserve_le_interface_variation_measure": True,
            "interface_variation_measure_le_coarea_collar_charge": True,
            "coarea_collar_charge_le_positive_kernel_tv_coupling_mass": True,
            "positive_kernel_tv_coupling_mass_le_localized_schur_owner_charge": True,
            "localized_schur_owner_charge_le_owner_root_budget": True,
            "interface_lower_payment_declared_before_projection_step_lt_projected_payoff_step": True,
            "interface_lower_payment_declared_before_payoff_step_lt_projected_payoff_step": True,
            "selected_section_identity_fixed_before_payoff": True,
            "selected_section_equals_localized_packet_interface_section": True,
            "interface_variation_measure_constructed_from_cutoff_formula": True,
            "extensional_measure_fixed_before_section_repair": True,
            "interface_variation_maps_to_same_coarea_collar_event": True,
            "interface_variation_payment_disjoint_from_prior_invoices": True,
            "interface_lower_payment_not_defined_from_projected_deficit": True,
            "signed_pressure_riesz_cancellation_excluded": True,
            "localized_tv_row_column_schur_bound": True,
            "cutoff_boundary_invoice_paid_by_same_owner": True,
            "pressure_leray_tail_leakage_paid_or_excluded": True,
            "cross_owner_tv_edges_excluded_or_separately_paid": True,
        },
        "concludes": {
            "SelectedInterfaceVariationCoareaOverlapLowerPaymentSource": True,
            "CoareaCollarLowerPaymentToPositiveTVSource": True,
            "CoareaPositiveKernelTVMinorantSource": True,
            "PositiveLocalizedKernelTVCouplingSource": True,
            "PrePayoffOverlapPreimageSource": True,
            "paid_overlap_reserve_le_owner_root_budget": True,
        },
        "does_not_accept": [
            "selected_interface_variation_without_coarea_mapping",
            "selected_absolute_variation_as_overlap_payment_without_domination",
            "interface_variation_after_section_repair",
            "coarea_collar_charge_upper_control_only",
        ],
    },
    "payment_biased_coarea_slice_source_gate": {
        "requires": {
            "correlated_coarea_high_low_interface_slice_source": True,
            "interface_weighted_threshold_measure": True,
            "payment_biased_selection_fixed_before_payoff": True,
            "weighted_boundary_pays_interface_floor": True,
            "payment_bias_uses_source_interface_family": True,
            "not_uniform_threshold_size_sum_route": True,
            "not_post_payoff_payment_bias": True,
        },
        "concludes": {
            "PaymentBiasedCoareaSliceSource": True,
            "CorrelatedCoareaHighLowInterfaceSliceSource": True,
            "payment_biased_coarea_bypasses_uniform_threshold_pz_bottleneck": True,
        },
        "does_not_accept": [
            "payment_bias_chosen_after_projected_deficit",
            "target_deficit_weighted_threshold_selection",
            "uniform_threshold_size_sum_label_reused",
            "interface_weight_from_proxy_family",
            "payment_bias_without_source_family_timing",
        ],
    },
    "interface_weighted_boundary_paid_floor_correlation_source_gate": {
        "requires": {
            "payment_biased_coarea_slice_source": True,
            "source_interface_law_fixed_before_payoff": True,
            "selected_event_has_positive_source_interface_weight": True,
            "selected_event_pays_interface_floor_from_source_law": True,
            "selected_event_boundary_pays_interface_from_same_law": True,
            "selected_boundary_pays_floor_not_just_prefix_sum": True,
            "zero_interface_sink_excluded_by_weight_law": True,
            "same_owner_root_for_boundary_and_interface_slice": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "InterfaceWeightedBoundaryPaidFloorCorrelationSource": True,
            "PaymentBiasedCoareaSliceSource": True,
            "boundary_pays_interface_floor": True,
            "weighted_floor_correlation_selector_paid": True,
        },
        "does_not_accept": [
            "finite_prefix_sum_only",
            "zero_interface_boundary_sink",
            "boundary_surplus_on_low_interface_events",
            "selected_event_from_target_deficit",
            "proxy_interface_weight_law",
        ],
    },
    "high_interface_conditional_boundary_share_source_gate": {
        "requires": {
            "restricted_high_interface_boundary_payment_source": True,
            "conditional_high_interface_law_fixed_before_payoff": True,
            "conditional_law_has_positive_mass": True,
            "conditional_boundary_share_defined_as_B_over_BplusI": True,
            "conditional_boundary_share_threshold_lt_one": True,
            "conditional_boundary_share_mean_surplus_nonnegative": True,
            "conditional_support_lower_bound_mul_share_slack_le_mean_surplus": True,
            "conditional_share_mean_surplus_le_share_slack_mul_boundary_paid_high_interface_support": True,
            "conditional_share_mean_not_target_selected": True,
            "conditional_boundary_share_produces_restricted_selected_event": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "HighInterfaceConditionalBoundaryShareSource": True,
            "RestrictedHighInterfaceBoundaryPaymentSource": True,
            "InterfaceWeightedBoundaryPaidFloorCorrelationSource": True,
        },
        "does_not_accept": [
            "global_boundary_share_only",
            "conditional_law_missing_or_target_selected",
            "low_interface_boundary_share_surplus",
            "high_interface_measure_zero",
            "proxy_conditional_share_law",
        ],
    },
    "high_interface_conditional_average_boundary_dominance_source_gate": {
        "requires": {
            "restricted_high_interface_boundary_payment_source": True,
            "conditional_high_interface_law_fixed_before_payoff": True,
            "conditional_high_interface_law_has_positive_mass": True,
            "conditional_boundary_interface_same_source_family": True,
            "conditional_boundary_average_dominates_interface_average": True,
            "selected_event_from_conditional_finite_pigeonhole": True,
            "conditional_dominance_not_global_prefix_only": True,
            "conditional_dominance_not_signed_pressure_visibility": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "HighInterfaceConditionalAverageBoundaryDominanceSource": True,
            "RestrictedHighInterfaceBoundaryPaymentSource": True,
            "InterfaceWeightedBoundaryPaidFloorCorrelationSource": True,
        },
        "does_not_accept": [
            "global_boundary_dominance_only",
            "conditional_average_missing",
            "signed_pressure_visibility_only",
            "target_selected_high_interface_law",
        ],
    },
    "high_interface_finite_prefix_average_boundary_dominance_source_gate": {
        "requires": {
            "high_interface_conditional_average_boundary_dominance_source": True,
            "high_interface_prefix_length_positive": True,
            "selected_high_interface_prefix_index_lt_prefix": True,
            "finite_prefix_high_interface_payment_le_boundary_charge": True,
            "selected_high_interface_payment_pays_floor": True,
            "selected_high_boundary_pays_interface": True,
            "high_interface_prefix_family_fixed_before_payoff": True,
            "boundary_and_interface_charges_same_high_interface_law": True,
            "selected_prefix_witness_matches_restricted_event": True,
            "finite_prefix_dominance_not_global_boundary_surplus": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "HighInterfaceFinitePrefixAverageBoundaryDominanceSource": True,
            "HighInterfaceConditionalAverageBoundaryDominanceSource": True,
            "RestrictedHighInterfaceBoundaryPaymentSource": True,
            "high_interface_boundary_floor_paid_by_finite_prefix_witness": True,
        },
        "does_not_accept": [
            "global_boundary_dominance_only",
            "finite_prefix_sum_without_floor_witness",
            "boundary_surplus_on_low_interface_events",
            "proxy_high_interface_prefix_family",
            "post_payoff_prefix_choice",
            "signed_pressure_visibility_only",
        ],
    },
    "local_energy_invoice_high_interface_dominance_source_gate": {
        "requires": {
            "high_interface_conditional_average_boundary_dominance_source": True,
            "local_energy_invoice_eq_visible_boundary_plus_residual": True,
            "pointwise_high_interface_payment_le_local_energy_invoice": True,
            "visible_boundary_charge_nonnegative": True,
            "residual_reserve_charge_nonnegative": True,
            "local_energy_identity_fixed_before_payoff": True,
            "residual_reserve_independently_generated": True,
            "visible_boundary_and_residual_same_owner_prefix": True,
            "residual_reserve_not_defined_from_boundary_deficit": True,
            "local_energy_invoice_not_signed_pressure_visibility": True,
            "selected_high_interface_payment_pays_floor": True,
            "high_interface_boundary_partition_single_spend": True,
            "same_owner_high_interface_boundary_budget_le_owner_root_budget": True,
            "no_reuse_high_interface_boundary_budget_le_owner_root_budget": True,
            "owner_preimage_prefix_inequality": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LocalEnergyInvoiceHighInterfaceDominanceSource": True,
            "HighInterfaceFinitePrefixAverageBoundaryDominanceSource": True,
            "HighInterfaceConditionalAverageBoundaryDominanceSource": True,
            "RestrictedHighInterfaceBoundaryPaymentSource": True,
        },
        "does_not_accept": [
            "signed_local_energy_split_only",
            "interface_le_boundary_plus_unpaid_residual",
            "residual_reserve_defined_from_boundary_deficit",
            "positive_boundary_invoice_missing",
            "same_owner_prop_without_numeric_budget",
        ],
    },
    "lei_native_high_interface_event_tent_prefix_source_gate": {
        "requires": {
            "suitable_defect_backed_high_interface_measure_split_core": True,
            "event_family_binding_paid_by_definition": True,
            "high_interface_events_are_suitable_defect_event_tents": True,
            "selected_LEI_event_active_floor": True,
            "selected_high_interface_prefix_index_lt_prefix": True,
            "high_interface_payment_eq_active_measure": True,
            "active_measure_eq_defect_active_on_H": True,
            "owner_preimage_prefix_inequality": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeHighInterfaceEventTentPrefixSource": True,
            "SuitableDefectBackedHighInterfaceMeasureSplitCore": True,
            "event_family_binding_paid_not_transferred": True,
            "selected_payment_floor_from_LEI_active": True,
        },
        "does_not_accept": [
            "external_H_prefix_transferred_after_payoff",
            "proxy_threshold_family_not_LEI_event_tents",
            "active_floor_missing_on_selected_LEI_event",
            "CKN_or_CF_input_hidden_as_active_floor",
        ],
    },
    "lei_high_interface_log_discount_transaction_channel_source_gate": {
        "requires": {
            "lei_native_high_interface_event_tent_prefix_source": True,
            "log_discount_transaction_channel_source_gate": True,
            "selected_LEI_invoice_pays_finite_log_criterion": True,
            "same_selected_LEI_event_stream_as_log_channel": True,
            "lei_invoice_to_log_criterion_fixed_before_payoff": True,
            "no_signed_local_energy_visibility_as_criterion_payment": True,
            "no_raw_BKM_CF_or_pressure_null_import": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEIHighInterfaceLogDiscountTransactionChannelSource": True,
            "continuation_from_LEI_paid_log_channel": True,
            "LEI_invoice_is_source_payment_not_continuation_label": True,
        },
        "does_not_accept": [
            "LEI_invoice_label_without_finite_log_criterion_payment",
            "same_selected_event_stream_missing",
            "signed_local_energy_visibility_only",
            "hidden_BKM_CF_or_pressure_null_input",
            "log_scope_only_without_paid_transaction_channel",
        ],
    },
    "lei_high_interface_log_discount_numeric_payment_source_gate": {
        "requires": {
            "lei_high_interface_log_discount_transaction_channel_source_gate": True,
            "finite_log_criterion_debit_nonnegative": True,
            "LEI_invoice_source_budget_nonnegative": True,
            "finite_log_criterion_debit_le_LEI_invoice_source_budget": True,
            "numeric_criterion_debit_represents_log_channel": True,
            "LEI_invoice_budget_fixed_before_payoff": True,
            "no_endpoint_oscillation_spike_unpaid_by_LEI": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEIHighInterfaceLogDiscountNumericPaymentSource": True,
            "continuation_from_numeric_LEI_paid_log_channel": True,
            "finite_log_debit_paid_by_LEI_invoice_budget": True,
        },
        "does_not_accept": [
            "finite_log_criterion_debit_exceeds_LEI_budget",
            "endpoint_oscillation_spike_unpaid_by_LEI",
            "numeric_debit_not_bound_to_log_channel",
            "LEI_budget_chosen_after_payoff",
        ],
    },
    "lei_endpoint_oscillation_spike_confuser_gate": {
        "requires": {
            "finite_log_criterion_debit": True,
            "LEI_invoice_source_budget_nonnegative": True,
            "LEI_invoice_source_budget_lt_finite_log_criterion_debit": True,
            "endpoint_oscillation_spike_visible": True,
            "local_energy_invoice_finite_but_endpoint_debit_large": True,
            "signed_local_energy_does_not_control_BMO_log_endpoint": True,
            "no_hidden_BKM_or_CF_endpoint_input": True,
        },
        "concludes": {
            "LEIEndpointOscillationSpikeConfuser": True,
            "LEIHighInterfaceLogDiscountNumericPaymentSource_excluded": True,
            "endpoint_spike_blocks_LEI_log_payment": True,
        },
        "does_not_accept": [
            "finite_log_criterion_debit_le_LEI_invoice_source_budget",
            "LEI_invoice_pays_endpoint_oscillation",
            "hidden_endpoint_regularization_input",
        ],
    },
    "lei_interpolation_serrin_gap_confuser_gate": {
        "requires": {
            "lei_native_energy_class_visible": True,
            "energy_interpolation_LpLq_finite": True,
            "energy_interpolation_scaling_eq_3_halves": True,
            "prodi_serrin_scaling_requires_le_one": True,
            "no_extra_endpoint_gain_from_selection": True,
            "no_hidden_ESS_BKM_or_CF_input": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEIInterpolationSerrinGapConfuser": True,
            "ProdiSerrinCriterionData_excluded_on_same_exponents": True,
            "LEI_energy_interpolation_not_continuation_payment": True,
            "endpoint_gain_theorem_required": True,
        },
        "does_not_accept": [
            "LEI_energy_class_label_as_PSL_payment",
            "energy_line_3_halves_treated_as_Serrin_line",
            "hidden_ESS_BKM_CF_endpoint_input",
            "post_payoff_endpoint_gain",
        ],
    },
    "lei_ckn_exception_set_endpoint_gain_source_gate": {
        "requires": {
            "ckn_singular_set_dim_le_one": True,
            "endpoint_debit_on_singular_set_nonnegative": True,
            "endpoint_debit_on_singular_set_eq_zero": True,
            "selected_endpoint_debit_avoids_singular_set": True,
            "same_selected_LEI_stream_as_CKN_regular_region": True,
            "no_hidden_ESS_BKM_or_CF_input": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEICKNExceptionSetEndpointGainSource": True,
            "CKN_partial_regular_region_can_pay_endpoint_gain_only_off_singular_set": True,
            "endpoint_gain_requires_zero_singular_debit": True,
        },
        "does_not_accept": [
            "CKN_partial_regular_off_set_as_global_continuation",
            "endpoint_debit_may_concentrate_on_singular_set",
            "singular_set_support_unpaid",
            "hidden_ESS_BKM_CF_endpoint_input",
        ],
    },
    "lei_ckn_exception_set_sink_confuser_gate": {
        "requires": {
            "ckn_singular_set_dim_le_one": True,
            "endpoint_debit_on_singular_set_positive": True,
            "selected_endpoint_debit_may_concentrate_on_singular_set": True,
            "no_off_singular_support_receipt": True,
            "no_hidden_ESS_BKM_or_CF_input": True,
        },
        "concludes": {
            "LEICKNExceptionSetSinkConfuser": True,
            "LEICKNExceptionSetEndpointGainSource_excluded": True,
            "CKN_exception_set_blocks_LEI_endpoint_gain": True,
        },
        "does_not_accept": [
            "endpoint_debit_on_singular_set_eq_zero",
            "selected_endpoint_debit_avoids_singular_set",
            "global_endpoint_gain_from_partial_regular_region_only",
        ],
    },
    "lei_ckn_singular_collar_endpoint_gain_source_gate": {
        "requires": {
            "lei_ckn_exception_set_endpoint_gain_source_gate": True,
            "singular_collar_endpoint_debit_nonnegative": True,
            "regular_region_endpoint_budget_nonnegative": True,
            "singular_collar_endpoint_debit_le_regular_region_endpoint_budget": True,
            "collar_debit_vanishes_at_critical_endpoint": True,
            "parabolic_dimension_pays_critical_collar_integral": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEICKNSingularCollarEndpointGainSource": True,
            "CKN_collar_endpoint_gain_paid": True,
            "zero_on_set_upgraded_to_collar_control": True,
        },
        "does_not_accept": [
            "zero_on_singular_set_without_collar_control",
            "critical_collar_debit_exceeds_regular_budget",
            "dimension_bound_used_as_integrability_bound_without_receipt",
        ],
    },
    "lei_ckn_singular_collar_leak_confuser_gate": {
        "requires": {
            "ckn_singular_set_dim_le_one": True,
            "endpoint_debit_on_singular_set_eq_zero": True,
            "regular_region_endpoint_budget_nonnegative": True,
            "regular_region_endpoint_budget_lt_singular_collar_endpoint_debit": True,
            "endpoint_debit_concentrates_in_shrinking_collars": True,
            "parabolic_dimension_one_does_not_pay_critical_collar_integral": True,
            "no_hidden_ESS_BKM_or_CF_input": True,
        },
        "concludes": {
            "LEICKNSingularCollarLeakConfuser": True,
            "LEICKNSingularCollarEndpointGainSource_excluded": True,
            "zero_on_set_not_enough_for_endpoint_gain": True,
        },
        "does_not_accept": [
            "singular_collar_endpoint_debit_le_regular_region_endpoint_budget",
            "dimension_one_bound_as_critical_collar_integrability",
            "hidden_endpoint_regularization_input",
        ],
    },
    "lei_ckn_singular_collar_minkowski_packing_source_gate": {
        "requires": {
            "lei_ckn_singular_collar_endpoint_gain_source_gate": True,
            "collar_cover_radius_sum_nonnegative": True,
            "minkowski_packing_budget_nonnegative": True,
            "collar_cover_radius_sum_le_minkowski_packing_budget": True,
            "parabolic_minkowski_content_finite_receipt": True,
            "hausdorff_zero_not_spent_as_minkowski": True,
            "regularity_scale_packing_produced": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEICKNSingularCollarMinkowskiPackingSource": True,
            "critical_collar_control_requires_minkowski_packing": True,
            "tick496_prerequisite_paid": True,
        },
        "does_not_accept": [
            "hausdorff_zero_as_minkowski_packing",
            "collar_cover_radius_sum_exceeds_budget",
            "qualitative_CKN_support_as_regular_scale_packing",
        ],
    },
    "lei_ckn_hausdorff_only_collar_packing_confuser_gate": {
        "requires": {
            "hausdorff_zero_CKN": True,
            "minkowski_packing_budget_nonnegative": True,
            "minkowski_packing_budget_lt_collar_cover_radius_sum": True,
            "minkowski_content_receipt_missing": True,
            "hausdorff_zero_does_not_bound_collar_packing": True,
        },
        "concludes": {
            "LEICKNHausdorffOnlyCollarPackingConfuser": True,
            "LEICKNSingularCollarMinkowskiPackingSource_excluded": True,
            "CKN_Hausdorff_only_does_not_pay_collar_endpoint_control": True,
        },
        "does_not_accept": [
            "parabolic_minkowski_content_finite_receipt",
            "collar_cover_radius_sum_le_minkowski_packing_budget",
            "qualitative_dimension_bound_as_quantitative_covering_budget",
        ],
    },
    "lei_ckn_capacity_trace_endpoint_gain_source_gate": {
        "requires": {
            "lei_ckn_singular_collar_endpoint_gain_source_gate": True,
            "capacity_trace_debit_nonnegative": True,
            "capacity_budget_nonnegative": True,
            "singular_collar_endpoint_debit_le_capacity_trace_debit": True,
            "capacity_trace_debit_le_capacity_budget": True,
            "capacity_or_carleson_channel_fixed_before_payoff": True,
            "same_selected_collar_family_as_endpoint_debit": True,
            "capacity_trace_not_defined_from_endpoint_deficit": True,
            "hausdorff_zero_not_spent_as_capacity_trace": True,
            "no_hidden_ESS_BKM_CF_TypeI_or_minkowski_input": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEICKNCapacityTraceEndpointGainSource": True,
            "CKN_capacity_or_carleson_channel_pays_selected_collar_debit": True,
            "capacity_trace_is_transaction_channel_not_label": True,
        },
        "does_not_accept": [
            "capacity_label_only",
            "hausdorff_zero_as_capacity_trace",
            "capacity_trace_defined_from_endpoint_deficit",
            "hidden_finite_minkowski_or_no_null_endpoint_input",
            "post_payoff_collar_selection",
        ],
    },
    "lei_ckn_tiny_capacity_collar_endpoint_debit_confuser_gate": {
        "requires": {
            "ckn_singular_set_dim_le_one": True,
            "capacity_budget_nonnegative": True,
            "capacity_budget_lt_singular_collar_endpoint_debit": True,
            "endpoint_debit_lives_on_capacity_null_or_tiny_collars": True,
            "capacity_trace_domination_receipt_missing": True,
            "capacity_channel_would_need_no_null_or_packing_theorem": True,
        },
        "concludes": {
            "LEICKNTinyCapacityCollarEndpointDebitConfuser": True,
            "LEICKNCapacityTraceEndpointGainSource_excluded": True,
            "capacity_reinterpretation_reduces_to_packing_or_no_null_wall": True,
        },
        "does_not_accept": [
            "singular_collar_endpoint_debit_le_capacity_trace_debit",
            "capacity_trace_debit_le_capacity_budget",
            "capacity_trace_domination_receipt_present",
            "same_stream_capacity_payment",
        ],
    },
    "selected_prefix_nonnegative_channel_collapse_source_gate": {
        "requires": {
            "target_debit_nonnegative": True,
            "channel_payment_nonnegative": True,
            "channel_budget_nonnegative": True,
            "constant_nonnegative": True,
            "target_prefix_le_constant_times_channel_prefix": True,
            "channel_prefix_le_channel_budget": True,
            "channel_fixed_before_payoff": True,
            "same_selected_prefix_stream": True,
            "channel_payment_not_defined_from_target_deficit": True,
            "nonnegative_monotone_channel_not_signed_cancellation": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "SelectedPrefixNonnegativeChannelCollapseSource": True,
            "target_prefix_le_constant_times_channel_budget": True,
            "nonnegative_channel_reduces_to_all_prefix_budget": True,
        },
        "does_not_accept": [
            "channel_label_only",
            "terminal_budget_without_prefix_payment",
            "target_deficit_defined_channel_payment",
            "different_selected_prefix_stream",
            "signed_cancellation_channel_misclassified_as_nonnegative",
            "coalescence_escape_retired_without_receipt",
        ],
    },
    "selected_prefix_unbounded_debit_channel_confuser_gate": {
        "requires": {
            "channel_budget_nonnegative": True,
            "constant_nonnegative": True,
            "target_prefix_unbounded": True,
            "nonnegative_channel_label_only": True,
            "signed_or_coalescent_escape_not_supplied": True,
        },
        "concludes": {
            "SelectedPrefixUnboundedDebitChannelConfuser": True,
            "SelectedPrefixNonnegativeChannelCollapseSource_excluded": True,
            "nonnegative_channel_label_does_not_pay_unbounded_selected_debit": True,
        },
        "does_not_accept": [
            "target_prefix_le_constant_times_channel_prefix",
            "channel_prefix_le_channel_budget",
            "signed_current_cancellation_receipt_present",
            "forced_endpoint_coalescence_receipt_present",
        ],
    },
    "selected_coalescent_current_support_quotient_debit_source_gate": {
        "requires": {
            "endpoint_debit_nonnegative": True,
            "coalescent_class_debit_nonnegative": True,
            "coalescent_budget_nonnegative": True,
            "constant_nonnegative": True,
            "endpoint_prefix_le_constant_times_coalescent_class_prefix": True,
            "coalescent_class_prefix_le_budget": True,
            "current_support_relation_fixed_before_payoff": True,
            "coalescent_class_map_fixed_before_payoff": True,
            "omitted_endpoint_debit_paid_before_quotient": True,
            "quotient_debit_not_defined_from_target_deficit": True,
            "signed_cancellation_not_spent_as_positive_debit": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "SelectedCoalescentCurrentSupportQuotientDebitSource": True,
            "SelectedPrefixNonnegativeChannelCollapseSource": True,
            "coalescent_quotient_pays_original_endpoint_prefix_only_if_omitted_children_paid": True,
        },
        "does_not_accept": [
            "current_label_only",
            "coalescent_class_map_after_payoff",
            "omitted_child_debit_unpaid",
            "many_endpoints_one_class_without_debit_sum",
            "signed_cancellation_spent_as_positive_debit",
            "target_defined_quotient_debit",
            "hidden_no_null_or_minkowski_input",
        ],
    },
    "many_endpoint_one_current_class_underpaid_confuser_gate": {
        "requires": {
            "coalescent_budget_nonnegative": True,
            "constant_nonnegative": True,
            "underpaid_selected_prefix": True,
            "many_selected_endpoints_share_one_current_class": True,
            "omitted_endpoint_debit_unpaid_before_quotient": True,
            "quotient_label_only": True,
        },
        "concludes": {
            "ManyEndpointOneCurrentClassUnderpaidConfuser": True,
            "SelectedCoalescentCurrentSupportQuotientDebitSource_excluded": True,
            "coalescence_without_omitted_debit_payment_recurs_to_barcode_no_null_wall": True,
        },
        "does_not_accept": [
            "omitted_endpoint_debit_paid_before_quotient",
            "endpoint_prefix_le_constant_times_coalescent_class_prefix",
            "signed_current_cancellation_receipt_present",
            "coalescent_class_debit_sums_all_children",
        ],
    },
    "pre_positive_current_annihilation_or_paid_omitted_endpoint_debit_gate": {
        "requires": {
            "endpoint_debit_nonnegative": True,
            "coalescent_class_debit_nonnegative": True,
            "coalescent_budget_nonnegative": True,
            "constant_nonnegative": True,
            "current_support_relation_fixed_before_payoff": True,
            "selected_endpoint_debit_formed_after_current_reduction": True,
            "admissible_current_exit": True,
            "quotient_debit_not_defined_from_target_deficit": True,
            "annihilation_receipt_not_positive_payment_relabel": True,
            "no_hidden_no_null_minkowski_ESS_BKM_or_CF_input": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "PrePositiveDebitCurrentAnnihilationOrPaidOmittedEndpointDebit": True,
            "only_two_current_exits_allowed": True,
            "ckn_current_socket_discriminated_without_continuation_claim": True,
        },
        "does_not_accept": [
            "current_label_only",
            "coalescent_class_count_only",
            "positive_debit_relabel_as_annihilation",
            "paid_omitted_endpoint_debit_missing",
            "admissible_exit_chosen_after_payoff",
            "target_defined_quotient_debit",
            "hidden_no_null_or_minkowski_input",
            "hidden_ESS_BKM_or_CF_input",
        ],
    },
    "pre_positive_current_no_annihilation_underpaid_confuser_gate": {
        "requires": {
            "coalescent_budget_nonnegative": True,
            "constant_nonnegative": True,
            "underpaid_selected_prefix": True,
            "many_selected_endpoints_share_one_current_class": True,
            "omitted_endpoint_debit_unpaid_before_quotient": True,
            "pre_positive_current_annihilation_absent": True,
        },
        "concludes": {
            "PrePositiveDebitCurrentAnnihilationOrPaidOmittedEndpointDebit_excluded_without_annihilation": True,
            "paid_omitted_exit_reduces_to_finite_prefix_budget": True,
            "surviving_CKN_socket_requires_pre_positive_annihilation_receipt": True,
        },
        "does_not_accept": [
            "pre_positive_current_annihilation_receipt_present",
            "omitted_endpoint_debit_paid_before_quotient",
            "coalescent_class_debit_sums_all_children",
            "endpoint_prefix_le_constant_times_coalescent_class_prefix",
        ],
    },
    "positive_scalar_endpoint_debit_current_annihilation_confuser_gate": {
        "requires": {
            "coalescent_budget_nonnegative": True,
            "constant_nonnegative": True,
            "underpaid_selected_prefix": True,
            "many_selected_endpoints_share_one_current_class": True,
            "omitted_endpoint_debit_unpaid_before_quotient": True,
            "endpoint_debit_already_positive_scalar": True,
            "positive_scalarization_precedes_current_quotient": True,
            "oriented_current_cancellation_only_pre_scalar": True,
            "endpoint_debit_invariant_under_post_scalar_current_cancellation": True,
            "genuine_pre_scalar_current_reduction_not_supplied": True,
        },
        "concludes": {
            "PositiveScalarEndpointDebitCurrentAnnihilationConfuser": True,
            "PrePositiveDebitCurrentAnnihilationOrPaidOmittedEndpointDebit_excluded_for_positive_scalar_endpoint": True,
            "CKN_current_socket_survives_only_pre_scalar": True,
        },
        "does_not_accept": [
            "genuine_pre_scalar_current_reduction_supplied",
            "pre_positive_current_annihilation_receipt_present",
            "endpoint_debit_not_yet_scalarized",
            "signed_current_cancellation_spent_after_positive_part",
            "omitted_endpoint_debit_paid_before_quotient",
            "coalescent_class_debit_sums_all_children",
        ],
    },
    "lei_native_high_interface_boundary_no_reuse_budget_source_gate": {
        "requires": {
            "lei_native_selected_asymptotic_intermittent_survivor": True,
            "selected_payment_lower_bound_delta": True,
            "selected_payment_le_boundary_charge": True,
            "boundary_charge_prefix_le_critical_budget": True,
            "high_interface_boundary_events_same_selected_LEI_stream": True,
            "boundary_invoice_fixed_before_payoff": True,
            "boundary_assignment_total_on_selected_prefix": True,
            "same_carrier_boundary_packing": True,
            "no_nested_boundary_reuse_or_rebilling": True,
            "no_hidden_uniform_enstrophy_ESS_CF_import": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeSelectedHighInterfaceBoundaryNoReuseBudgetSource": True,
            "LEINativeSelectedIntermittentFiniteBudgetSource": True,
            "native_boundary_invoice_is_finite_depth_source_only_with_no_reuse": True,
        },
        "does_not_accept": [
            "finite_boundary_budget_label_only",
            "same_carrier_boundary_label_only",
            "freshness_label_only",
            "boundary_charge_chosen_after_target_deficit",
            "nested_selected_levels_reuse_one_boundary_atom",
            "uniform_selected_payment_lower_bound_missing",
            "hidden_uniform_enstrophy_ESS_CF_import",
        ],
    },
    "high_interface_boundary_no_reuse_finite_budget_confuser_gate": {
        "requires": {
            "finite_boundary_budget_label": True,
            "same_carrier_boundary_label": True,
            "nested_selected_levels_reuse_one_boundary_atom": True,
            "boundary_charge_chosen_after_target_deficit": True,
            "uniform_selected_payment_lower_bound_missing": True,
            "no_no_rebilling_freshness_receipt": True,
        },
        "concludes": {
            "HighInterfaceBoundaryNoReuseFiniteBudgetConfuser": True,
            "LEINativeSelectedHighInterfaceBoundaryNoReuseBudgetSource_excluded": True,
            "boundary_invoice_recurs_to_selected_finite_budget_freshness_atom": True,
        },
        "does_not_accept": [
            "no_nested_boundary_reuse_or_rebilling",
            "boundary_assignment_total_on_selected_prefix",
            "selected_payment_lower_bound_delta",
            "boundary_charge_prefix_le_critical_budget",
            "same_carrier_packing_receipt_present",
        ],
    },
    "coherent_finite_prefix_high_interface_boundary_invoice_source_gate": {
        "requires": {
            "finite_prefix_invoices_exist_for_all_prefixes": True,
            "selected_payment_lower_bound_delta": True,
            "selected_payment_le_boundary_charge": True,
            "boundary_charge_prefix_le_critical_budget": True,
            "prefix_invoices_use_same_selected_LEI_stream": True,
            "prefix_invoices_fixed_before_payoff": True,
            "boundary_charge_independent_of_prefix_index": True,
            "same_carrier_coherent_boundary_packing": True,
            "no_nested_boundary_reuse_across_prefixes": True,
            "no_hidden_uniform_enstrophy_ESS_CF_import": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "CoherentFinitePrefixHighInterfaceBoundaryInvoiceSource": True,
            "LEINativeSelectedHighInterfaceBoundaryNoReuseBudgetSource": True,
            "LEINativeSelectedIntermittentFiniteBudgetSource": True,
            "finite_prefix_invoices_promote_to_all_prefix_budget_only_with_coherence": True,
        },
        "does_not_accept": [
            "finite_prefix_invoice_exists_only",
            "prefix_dependent_boundary_charge",
            "same_carrier_boundary_label_only",
            "post_payoff_prefix_diagonal_selection",
            "nested_boundary_reuse_packet",
        ],
    },
    "finite_prefix_high_interface_boundary_invoice_without_coherence_confuser_gate": {
        "requires": {
            "every_finite_prefix_has_some_boundary_invoice": True,
            "prefix_invoices_not_same_selected_stream": True,
            "boundary_charge_depends_on_prefix_index": True,
            "diagonal_nested_reuse_packet_still_admissible": True,
        },
        "concludes": {
            "FinitePrefixHighInterfaceBoundaryInvoiceWithoutCoherenceConfuser": True,
            "CoherentFinitePrefixHighInterfaceBoundaryInvoiceSource_excluded": True,
            "LEINativeSelectedHighInterfaceBoundaryNoReuseBudgetSource_excluded": True,
            "finite_prefix_invoice_without_coherence_recurs_to_selected_finite_budget_atom": True,
        },
        "does_not_accept": [
            "prefix_invoices_use_same_selected_LEI_stream",
            "boundary_charge_independent_of_prefix_index",
            "same_carrier_coherent_boundary_packing",
            "no_nested_boundary_reuse_across_prefixes",
        ],
    },
    "high_interface_boundary_metric_covering_prefix_coherence_source_gate": {
        "requires": {
            "coherent_finite_prefix_high_interface_boundary_invoice_source_gate": True,
            "high_interface_boundary_tent_family": True,
            "ambient_parabolic_metric_or_quasi_metric": True,
            "boundary_scale_radius_fixed_before_payoff": True,
            "doubling_or_besicovitch_constant_uniform": True,
            "bounded_eccentricity_or_engulfing": True,
            "vitali_or_whitney_selection_fixed_before_payoff": True,
            "selected_prefix_coverage_or_paid_omission": True,
            "same_boundary_carrier_after_selection": True,
            "bounded_overlap_uniform_in_prefix": True,
            "nested_children_paid_by_parent_or_error_budget": True,
            "metric_covering_selection_receipt": True,
            "no_post_payoff_subcover_or_unpaid_children": True,
            "boundary_charge_prefix_le_metric_invoice": True,
            "metric_invoice_and_omission_le_critical_budget": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "HighInterfaceBoundaryMetricCoveringPrefixCoherenceSource": True,
            "CoherentFinitePrefixHighInterfaceBoundaryInvoiceSource": True,
            "LEINativeSelectedHighInterfaceBoundaryNoReuseBudgetSource": True,
            "boundary_prefix_coherence_reduces_to_metric_covering_no_reuse": True,
        },
        "does_not_accept": [
            "besicovitch_label_without_covering_hypotheses",
            "post_payoff_vitali_selection",
            "vitali_subcover_discards_unpaid_children",
            "bounded_overlap_not_uniform_in_selected_prefix",
            "metric_covering_without_numeric_invoice",
        ],
    },
    "high_interface_boundary_nonwhitney_nested_cascade_confuser_gate": {
        "requires": {
            "high_interface_boundary_tent_labels_present": True,
            "dyadic_boundary_cascade_same_center": True,
            "selected_prefix_counts_nested_children": True,
            "vitali_subcover_discards_unpaid_children": True,
            "bounded_overlap_not_uniform_in_selected_prefix": True,
            "same_boundary_atom_reused_across_scales": True,
        },
        "concludes": {
            "HighInterfaceBoundaryNonWhitneyNestedCascadeConfuser": True,
            "HighInterfaceBoundaryMetricCoveringPrefixCoherenceSource_excluded": True,
            "metric_covering_selection_receipt_required_for_boundary_prefix_coherence": True,
        },
        "does_not_accept": [
            "bounded_overlap_uniform_in_prefix",
            "selected_prefix_coverage_or_paid_omission",
            "nested_children_paid_by_parent_or_error_budget",
            "same_boundary_carrier_after_selection",
        ],
    },
    "high_interface_boundary_carleson_packing_selection_source_gate": {
        "requires": {
            "high_interface_boundary_metric_covering_prefix_coherence_source_gate": True,
            "boundary_charge_eq_boundary_measure_on_selected_tent": True,
            "selected_boundary_carleson_packing_bound": True,
            "high_interface_boundary_tent_family": True,
            "selected_tent_family_fixed_before_payoff": True,
            "carleson_packing_not_finite_measure_only": True,
            "discarded_nested_children_paid_before_payoff": True,
            "same_boundary_carrier_across_selected_tents": True,
            "no_nested_boundary_mass_reuse": True,
            "selected_payment_lower_bound_delta": True,
            "selected_payment_le_boundary_charge": True,
            "no_hidden_uniform_enstrophy_ESS_CF_import": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "HighInterfaceBoundaryCarlesonPackingSelectionSource": True,
            "LEINativeSelectedHighInterfaceBoundaryNoReuseBudgetSource": True,
            "finite_measure_vitali_only_is_insufficient": True,
            "carleson_or_paid_child_source_required": True,
        },
        "does_not_accept": [
            "finite_boundary_measure_label_only",
            "vitali_whitney_covering_label_only",
            "nested_selected_tents_same_boundary_mass",
            "discarded_children_unpaid",
            "carleson_bound_defined_from_target_prefix",
        ],
    },
    "finite_boundary_measure_nested_mass_reuse_confuser_gate": {
        "requires": {
            "finite_boundary_measure_label": True,
            "vitali_whitney_covering_label": True,
            "nested_selected_tents_same_boundary_mass": True,
            "total_boundary_measure_finite_but_prefix_mass_unbounded": True,
            "discarded_children_not_paid_before_payoff": True,
        },
        "concludes": {
            "FiniteBoundaryMeasureNestedMassReuseConfuser": True,
            "HighInterfaceBoundaryCarlesonPackingSelectionSource_excluded": True,
            "finite_measure_vitali_only_does_not_pay_selected_prefix_sum": True,
        },
        "does_not_accept": [
            "selected_boundary_carleson_packing_bound",
            "discarded_nested_children_paid_before_payoff",
            "no_nested_boundary_mass_reuse",
        ],
    },
    "high_interface_boundary_stopping_tree_energy_decrement_source_gate": {
        "requires": {
            "high_interface_boundary_carleson_packing_selection_source_gate": True,
            "boundary_charge_eq_boundary_measure_on_selected_tent": True,
            "boundary_measure_le_energy_drop": True,
            "energy_drop_prefix_le_critical_budget": True,
            "high_interface_boundary_tent_family": True,
            "selected_tent_family_fixed_before_payoff": True,
            "stopping_tree_potential_decreases_on_selected_tents": True,
            "energy_drop_not_defined_from_target_deficit": True,
            "discarded_nested_children_paid_before_payoff": True,
            "same_boundary_carrier_across_selected_tents": True,
            "no_nested_boundary_mass_reuse": True,
            "selected_payment_lower_bound_delta": True,
            "selected_payment_le_boundary_charge": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "HighInterfaceBoundaryStoppingTreeEnergyDecrementSource": True,
            "HighInterfaceBoundaryCarlesonPackingSelectionSource": True,
            "LEINativeSelectedHighInterfaceBoundaryNoReuseBudgetSource": True,
            "carleson_packing_paid_by_monotone_decrement": True,
        },
        "does_not_accept": [
            "finite_energy_or_boundary_budget_label",
            "selected_tents_do_not_consume_monotone_energy_drop",
            "same_energy_reservoir_rebilled_down_nested_chain",
            "energy_drop_defined_from_target_deficit_or_after_payoff",
        ],
    },
    "boundary_carleson_without_stopping_decrement_confuser_gate": {
        "requires": {
            "finite_energy_or_boundary_budget_label": True,
            "high_interface_boundary_tent_family_label": True,
            "selected_tents_do_not_consume_monotone_energy_drop": True,
            "same_energy_reservoir_rebilled_down_nested_chain": True,
            "energy_drop_defined_from_target_deficit_or_after_payoff": True,
        },
        "concludes": {
            "BoundaryCarlesonWithoutStoppingDecrementConfuser": True,
            "HighInterfaceBoundaryStoppingTreeEnergyDecrementSource_excluded": True,
            "finite_energy_label_does_not_pay_selected_carleson_packing": True,
        },
        "does_not_accept": [
            "boundary_measure_le_energy_drop",
            "energy_drop_prefix_le_critical_budget",
            "stopping_tree_potential_decreases_on_selected_tents",
            "energy_drop_not_defined_from_target_deficit",
        ],
    },
    "channel_separated_stopping_tree_decrement_reserve_source_gate": {
        "requires": {
            "boundary_charge_eq_boundary_measure_on_selected_tent": True,
            "boundary_measure_le_channel_drop": True,
            "channel_drop_prefix_le_critical_budget": True,
            "production_drop_nonnegative": True,
            "pressure_reserve_nonnegative": True,
            "duhamel_reserve_nonnegative": True,
            "inherited_reserve_nonnegative": True,
            "paid_child_invoice_nonnegative": True,
            "high_interface_boundary_tent_family": True,
            "selected_tent_family_fixed_before_payoff": True,
            "channel_partition_fixed_before_payoff": True,
            "pressure_duhamel_inherited_refill_paid_separately": True,
            "channels_not_defined_from_target_deficit": True,
            "discarded_nested_children_paid_before_payoff": True,
            "same_boundary_carrier_across_selected_tents": True,
            "no_nested_boundary_mass_reuse": True,
            "no_reserve_refill_rebilling": True,
            "selected_payment_lower_bound_delta": True,
            "selected_payment_le_boundary_charge": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "ChannelSeparatedStoppingTreeDecrementReserveSource": True,
            "HighInterfaceBoundaryStoppingTreeEnergyDecrementSource": True,
            "HighInterfaceBoundaryCarlesonPackingSelectionSource": True,
            "LEINativeSelectedHighInterfaceBoundaryNoReuseBudgetSource": True,
            "ambient_decrement_split_into_paid_channels": True,
        },
        "does_not_accept": [
            "ambient_energy_drop_label_only",
            "pressure_duhamel_inherited_refill_unpaid",
            "child_invoice_omitted_or_post_payoff",
            "channel_partition_missing_before_payoff",
            "same_reserve_rebilled_across_nested_tents",
            "channel_drop_prefix_bound_missing",
        ],
    },
    "stopping_tree_decrement_reserve_refill_confuser_gate": {
        "requires": {
            "stopping_tree_energy_drop_label": True,
            "pressure_duhamel_inherited_refill_unpaid": True,
            "child_invoice_omitted_or_post_payoff": True,
            "channel_partition_missing_before_payoff": True,
            "same_reserve_rebilled_across_nested_tents": True,
            "channel_drop_prefix_bound_missing": True,
        },
        "concludes": {
            "StoppingTreeDecrementReserveRefillConfuser": True,
            "ChannelSeparatedStoppingTreeDecrementReserveSource_excluded": True,
            "ambient_decrement_label_does_not_pay_selected_boundary_mass": True,
        },
        "does_not_accept": [
            "boundary_measure_le_channel_drop",
            "channel_drop_prefix_le_critical_budget",
            "pressure_duhamel_inherited_refill_paid_separately",
            "channel_partition_fixed_before_payoff",
            "no_reserve_refill_rebilling",
        ],
    },
    "lei_high_interface_log_transaction_unpaid_criterion_confuser_gate": {
        "requires": {
            "lei_native_source_visible": True,
            "log_discount_scope_visible": True,
            "finite_criterion_not_paid_from_LEI_invoice": True,
            "same_selected_event_stream_missing": True,
            "signed_local_energy_visibility_only": True,
            "hidden_BKM_CF_or_pressure_null_input": True,
        },
        "concludes": {
            "LEIHighInterfaceLogTransactionUnpaidCriterionConfuser": True,
            "LEIHighInterfaceLogDiscountTransactionChannelSource_excluded": True,
            "finite_log_criterion_must_be_paid_from_LEI_invoice": True,
        },
        "does_not_accept": [
            "selected_LEI_invoice_pays_finite_log_criterion",
            "same_selected_LEI_event_stream_as_log_channel",
            "no_raw_BKM_CF_or_pressure_null_import",
        ],
    },
    "lei_native_tick538_selected_active_floor_bridge_gate": {
        "requires": {
            "lei_native_high_interface_event_tent_prefix_source": True,
            "tick538_typeI_density_lower_corrected": True,
            "selected_event_in_tick538_branch": True,
            "tick538_alphaA_radius_receipt_corrected": True,
            "selected_floor_below_tick538_radius_receipt": True,
            "alphaA_to_muA_on_same_selected_event": True,
            "event_family_binding_paid_by_definition": True,
            "no_superTypeI_intermittent_branch_assumed_away": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "selected_active_floor_from_tick538_alpha_bridge": True,
            "selected_LEI_event_active_floor_conditional": True,
            "nonintermittent_tick538_branch_only": True,
        },
        "does_not_accept": [
            "tick538_alphaA_receipt_treated_as_muA_floor",
            "selected_event_branch_membership_missing",
            "alphaA_to_muA_bridge_missing",
            "superTypeI_intermittency_suppressed",
            "post_payoff_selected_event_choice",
            "CKN_or_TypeI_assumption_hidden_as_general_LEI_geometry",
        ],
    },
    "active_positive_variation_dominates_signed_active_source_gate": {
        "requires": {
            "suitable_local_energy_defect_measure_source": True,
            "active_positive_variation_of_alphaA": True,
            "same_active_carrier": True,
            "alphaA_le_muA_all_events": True,
            "bridge_fixed_before_payoff": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "ActivePositiveVariationDominatesSignedActiveSource": True,
            "alphaA_le_muA_of_activePositiveVariationDominatesSignedActive": True,
            "alphaA_to_muA_currency_exchange_paid": True,
        },
        "does_not_accept": [
            "positive_variation_label_without_numeric_domination",
            "different_active_carrier",
            "post_payoff_positive_part_selection",
            "muA_floor_defined_from_target_deficit",
        ],
    },
    "lei_native_tick538_positive_variation_bridge_gate": {
        "requires": {
            "lei_native_tick538_selected_active_floor_bridge_gate": True,
            "active_positive_variation_dominates_signed_active_source_gate": True,
            "selected_event_in_tick538_branch": True,
            "selected_floor_below_tick538_radius_receipt": True,
            "no_superTypeI_intermittent_branch_assumed_away": True,
        },
        "concludes": {
            "selected_active_floor_from_tick538_positiveVariation": True,
            "alphaA_to_muA_bridge_paid_by_positive_variation_source": True,
            "remaining_residual_is_selected_event_branch_membership_or_intermittency": True,
        },
        "does_not_accept": [
            "selected_event_branch_membership_missing",
            "superTypeI_intermittency_suppressed",
            "positive_variation_bridge_used_after_payoff",
        ],
    },
    "lei_native_tick538_positive_variation_branch_source_gate": {
        "requires": {
            "suitable_defect_backed_high_interface_measure_split_core": True,
            "event_family_binding_paid_by_definition": True,
            "high_interface_events_are_suitable_defect_event_tents": True,
            "tick538_typeI_density_lower_corrected": True,
            "selected_event_in_tick538_branch": True,
            "active_positive_variation_dominates_signed_active_source_gate": True,
            "selected_floor_below_tick538_radius_receipt": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeTick538PositiveVariationBranchSource": True,
            "selectedLEIEventActiveFloor_derived": True,
            "LEINativeHighInterfaceEventTentPrefixSource_ofTick538PositiveVariationBranch": True,
        },
        "does_not_accept": [
            "selectedLEIEventActiveFloor_assumed_directly",
            "selected_event_branch_membership_missing",
            "positive_variation_label_without_numeric_domination",
            "superTypeI_intermittency_suppressed",
            "post_payoff_selected_event_choice",
        ],
    },
    "lei_native_selected_active_floor_tick538_residual_confuser_gate": {
        "requires": {
            "suitable_defect_backed_high_interface_measure_split_core": True,
            "event_family_binding_paid": True,
            "tick538_corrected_density_available": True,
            "selected_event_branch_receipt_missing": True,
            "alphaA_to_muA_on_selected_event_missing": True,
            "superTypeI_intermittent_branch_still_open": True,
        },
        "concludes": {
            "LEINativeSelectedActiveFloorTick538ResidualConfuser": True,
            "unconditional_LEINativeHighInterfaceEventTentPrefixSource_excluded": True,
            "tick538_bridge_receipts_required": True,
        },
        "does_not_accept": [
            "selected_event_in_tick538_branch_paid",
            "alphaA_to_muA_on_same_event_paid",
            "nonintermittent_branch_exhausts_all_selected_events",
        ],
    },
    "lei_native_selected_asymptotic_intermittent_survivor_gate": {
        "requires": {
            "suitable_defect_backed_high_interface_measure_split_core": True,
            "event_family_binding_paid": True,
            "active_positive_variation_dominates_signed_active_source_gate": True,
            "asymptotic_superTypeI_sparse_cascade": True,
            "selected_LEI_events_follow_residual_stream": True,
            "no_selected_intermittent_visibility": True,
            "no_finite_budget_level_consumption": True,
        },
        "concludes": {
            "LEINativeSelectedAsymptoticIntermittentSurvivor": True,
            "LEINativeTick538PositiveVariationBranchSource_excluded": True,
            "selected_stream_visibility_or_budget_consumption_required": True,
        },
        "does_not_accept": [
            "selected_event_in_tick538_branch_paid",
            "selected_intermittent_visibility_paid",
            "finite_budget_level_consumption_paid",
            "literal_superTypeI_vacuity_used_on_asymptotic_stream",
        ],
    },
    "lei_native_selected_finite_budget_cost_confuser_gate": {
        "requires": {
            "lei_native_selected_asymptotic_intermittent_survivor_gate": True,
            "finite_scalar_budget_label": True,
            "same_stream_no_reuse_freshness_receipt_missing": True,
            "uniform_selected_cost_lower_bound_missing": True,
            "no_hidden_uniform_enstrophy_ESS_CF_import": True,
            "positive_cutoff_flux_reuse_packet_still_admissible": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeSelectedFiniteBudgetCostConfuser": True,
            "LEINativeSelectedIntermittentFiniteBudgetSource_excluded": True,
            "selected_stream_uniform_cost_lower_bound_or_visibility_required": True,
        },
        "does_not_accept": [
            "finite_budget_label_spent_as_level_cost",
            "nested_cutoff_reuse_without_freshness_receipt",
            "tick540_quartic_visibility_used_as_finite_budget",
            "uniform_enstrophy_ESS_CF_import_hidden_as_cost_lower_bound",
            "cost_n_defined_after_bad_level_selection",
        ],
    },
    "lei_native_selected_topology_fresh_cost_source_gate": {
        "requires": {
            "lei_native_selected_asymptotic_intermittent_survivor_gate": True,
            "fixed_topology_before_payoff": True,
            "topology_extraction_not_local_eulerian_riesz": True,
            "selected_level_topology_event_map_fixed": True,
            "selected_levels_inject_into_topology_events": True,
            "finite_owner_preimage_multiplicity": True,
            "helicity_dark_packet_tested": True,
            "reconnection_error_bounded_on_selected_stream": True,
            "no_hidden_uniform_enstrophy_ESS_CF_import": True,
            "topology_event_cost_lower_bound": True,
            "topology_prefix_budget": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyFreshCostSource": True,
            "RecursiveSuperTypeISparseCancellationConsumesCriticalBudget": True,
            "selected_depth_bounded_from_topology_fresh_cost": True,
        },
        "does_not_accept": [
            "helicity_label_only",
            "topological_name_without_extractor",
            "selected_level_map_chosen_after_payoff",
            "reconnection_count_without_viscous_error",
            "owner_preimage_receipt_missing",
            "helicity_dark_plane_wave_untested",
            "dimensionless_topology_count_without_physical_normalization",
            "uniform_enstrophy_ESS_CF_import_hidden_as_topology_cost",
        ],
    },
    "lei_native_selected_topology_owner_preimage_prefix_receipt_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "topology_event_owner_map_fixed_before_payoff": True,
            "pointwise_topology_event_payment": True,
            "finite_topology_atom_budget": True,
            "topology_event_multiplicity_bound": True,
            "same_selected_owner_source_binding": True,
            "owner_preimage_prefix_inequality": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyOwnerPreimagePrefixReceipt": True,
            "pec_k_paid_for_topology_fresh_cost_source": True,
            "topology_event_owner_preimage_prefix_inequality_paid": True,
        },
        "does_not_accept": [
            "pointwise_payment_without_prefix_inequality",
            "finite_atom_budget_without_owner_map",
            "multiplicity_label_without_prefix_bound",
            "same_owner_label_without_numeric_preimage_inequality",
            "owner_map_chosen_after_payoff",
        ],
    },
    "lei_native_selected_topology_dual_channel_prefix_source_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "event_cost_is_cost_sequence": True,
            "topology_owner_budget_is_max_bound": True,
            "cost_sequence_nonnegative": True,
            "reserve_sequence_nonnegative": True,
            "geometric_multiplicity_channel_or_analytic_reserve_drop": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyDualChannelPrefixSource": True,
            "tick553_prefix_bound_reused": True,
            "topology_owner_preimage_prefix_inequality_candidate": True,
        },
        "does_not_accept": [
            "freshness_from_either_channel_without_topology_extractor",
            "besicovitch_label_without_event_tent_geometry",
            "reserve_drop_label_without_scale_uniform_debit",
            "nested_reuse_non_besicovitch_family",
            "gamma_n_to_zero_reserve_drop_failure",
        ],
    },
    "lei_native_selected_topology_besicovitch_multiplicity_source_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "selected_topology_events_have_controlled_eccentricity": True,
            "selected_topology_events_have_engulfing_control": True,
            "selected_topology_event_family_fixed_before_payoff": True,
            "nested_non_besicovitch_reuse_excluded": True,
            "cost_sequence_nonnegative": True,
            "geometric_prefix_bound": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyBesicovitchMultiplicitySource": True,
            "geometric_channel_paid_for_tick553": True,
            "selected_topology_event_prefix_bound": True,
        },
        "does_not_accept": [
            "besicovitch_label_without_controlled_geometry",
            "selected_event_family_chosen_after_payoff",
            "nested_non_besicovitch_reuse_still_admissible",
            "bounded_multiplicity_label_without_prefix_bound",
        ],
    },
    "lei_native_selected_topology_nested_reuse_confuser_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "selected_topology_event_family_label": True,
            "controlled_eccentricity_missing": True,
            "engulfing_control_missing": True,
            "nested_reuse_packet_still_admissible": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyNestedReuseConfuser": True,
            "LEINativeSelectedTopologyBesicovitchMultiplicitySource_excluded": True,
            "controlled_geometry_or_engulfing_required": True,
        },
        "does_not_accept": [
            "controlled_eccentricity_paid",
            "engulfing_control_paid",
            "nested_reuse_excluded_before_payoff",
        ],
    },
    "lei_native_selected_topology_analytic_reserve_drop_source_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "same_selected_stream_reserve": True,
            "scale_uniform_reserve_debit": True,
            "repair_error_prefix_bounded": True,
            "no_hidden_strict_margin_import": True,
            "cost_sequence_nonnegative": True,
            "reserve_sequence_nonnegative": True,
            "reserve_drop_pays_cost": True,
            "repair_error_prefix_budget": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyAnalyticReserveDropSource": True,
            "analytic_channel_paid_for_tick553": True,
            "selected_topology_event_prefix_bound": True,
        },
        "does_not_accept": [
            "reserve_drop_label_without_same_selected_stream",
            "gamma_n_to_zero_scale_debit",
            "repair_error_prefix_unbounded",
            "strict_margin_import_hidden_as_reserve_drop",
        ],
    },
    "lei_native_selected_topology_vanishing_debit_confuser_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "reserve_drop_label": True,
            "gamma_n_to_zero": True,
            "same_selected_stream_reserve_missing": True,
            "repair_error_prefix_may_be_unbounded": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyVanishingDebitConfuser": True,
            "LEINativeSelectedTopologyAnalyticReserveDropSource_excluded": True,
            "scale_uniform_same_stream_debit_required": True,
        },
        "does_not_accept": [
            "scale_uniform_debit_paid",
            "same_selected_stream_reserve_paid",
            "repair_error_prefix_bound_paid",
        ],
    },
    "lei_native_selected_topology_orientation_capacity_prefix_source_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "clean_volume_accounting_for_selected_stream": True,
            "selected_cost_creates_orientation_pollution": True,
            "finite_orientation_capacity_converted_to_budget": True,
            "same_selected_topology_event_stream": True,
            "pollution_bridge_fixed_before_payoff": True,
            "no_hidden_capacity_only_bookkeeping": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyOrientationCapacityPrefixSource": True,
            "selected_topology_prefix_bound_from_orientation_capacity": True,
            "capacity_route_requires_same_stream_pollution_bridge": True,
        },
        "does_not_accept": [
            "finite_orientation_volume_label_only",
            "capacity_budget_disjoint_from_selected_cost",
            "pollution_bridge_chosen_after_payoff",
            "dimensionless_topology_count_without_physical_normalization",
            "clean_relay_keeps_selected_cost_dark",
        ],
    },
    "lei_native_selected_topology_capacity_only_confuser_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "finite_orientation_volume_label": True,
            "selected_cost_to_pollution_bridge_missing": True,
            "capacity_budget_can_be_disjoint_from_selected_cost": True,
            "clean_relay_can_keep_selected_cost_dark": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyCapacityOnlyConfuser": True,
            "LEINativeSelectedTopologyOrientationCapacityPrefixSource_excluded": True,
            "same_stream_pollution_bridge_required": True,
        },
        "does_not_accept": [
            "selected_cost_creates_orientation_pollution_paid",
            "same_selected_topology_event_stream_paid",
            "pollution_bridge_fixed_before_payoff_paid",
        ],
    },
    "lei_native_selected_topology_projected_pressure_prefix_no_null_lock_source_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "positive_no_null_floor": True,
            "prefix_no_null_average_lower_bound": True,
            "selected_topology_stream_linked_to_pressure_sequence": True,
            "pressure_bridge_fixed_before_payoff": True,
            "no_CF_BV_ESS_or_raw_CZ_import": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyProjectedPressurePrefixNoNullLockSource": True,
            "typed_prefix_no_null_lock_source_paid": True,
            "zero_projected_pressure_prefix_confuser_excluded": True,
        },
        "does_not_accept": [
            "no_null_lock_label_only",
            "pointwise_nonnull_without_prefix_average",
            "raw_CZ_or_CF_BV_import_hidden_as_no_null_lock",
            "pressure_sequence_chosen_after_payoff",
            "projected_pressure_abs_sum_zero_prefix",
        ],
    },
    "lei_native_selected_topology_pointwise_transversality_no_null_lock_source_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "positive_no_null_floor": True,
            "pointwise_projected_pressure_floor_on_selected_prefix": True,
            "selected_topology_stream_linked_to_pressure_sequence": True,
            "pointwise_transversality_fixed_before_payoff": True,
            "no_CF_BV_ESS_or_raw_CZ_import": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyPointwiseTransversalityNoNullLockSource": True,
            "LEINativeSelectedTopologyProjectedPressurePrefixNoNullLockSource": True,
            "typed_prefix_no_null_lock_source_paid": True,
            "pointwise_transversality_is_sufficient_not_necessary": True,
        },
        "does_not_accept": [
            "pointwise_transversality_label_only",
            "prefix_average_without_pointwise_floor",
            "raw_CZ_or_CF_BV_import_hidden_as_transversality",
            "pressure_sequence_chosen_after_payoff",
            "sum_of_squares_pressure_magnitude_without_signed_projection",
        ],
    },
    "lei_native_selected_topology_no_null_lock_pollution_bridge_source_gate": {
        "requires": {
            "lei_native_selected_topology_projected_pressure_prefix_no_null_lock_source_gate": True,
            "selected_topology_stream_linked_to_pressure_sequence": True,
            "pressure_controls_selected_cost_prefix": True,
            "pressure_sequence_creates_pollution_prefix": True,
            "same_selected_topology_event_stream": True,
            "pressure_bridge_fixed_before_payoff": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyNoNullLockPollutionBridgeSource": True,
            "selected_cost_creates_orientation_pollution": True,
            "physical_normalization_candidate_for_orientation_capacity": True,
        },
        "does_not_accept": [
            "pressure_magnitude_without_projected_sequence",
            "pointwise_nonnull_without_prefix_no_null_lock",
            "selected_topology_events_can_sit_in_CZ_nulls",
            "pressure_sequence_chosen_after_payoff",
        ],
    },
    "lei_native_selected_topology_pressure_exception_debit_capacity_source_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "pressure_plus_exception_controls_selected_cost_prefix": True,
            "pressure_sequence_creates_pollution_prefix": True,
            "exception_debit_prefix_budget": True,
            "clean_volume_accounting_for_selected_stream": True,
            "finite_orientation_capacity_and_exception_converted_to_budget": True,
            "same_selected_topology_event_stream": True,
            "exception_debit_same_selected_stream": True,
            "pressure_and_exception_bridge_fixed_before_payoff": True,
            "no_hidden_strict_margin_or_CF_import": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyPressureExceptionDebitCapacitySource": True,
            "selected_topology_prefix_bound_from_pressure_plus_exception_debit": True,
            "average_debit_route_avoids_pointwise_transversality_as_necessary": True,
        },
        "does_not_accept": [
            "exception_debit_label_only",
            "exception_debit_chosen_after_payoff",
            "exception_debit_not_same_selected_stream",
            "pressure_visibility_without_null_direction_debit",
            "strict_margin_or_CF_import_hidden_as_exception_budget",
        ],
    },
    "lei_native_selected_topology_benign_pressure_null_transaction_source_gate": {
        "requires": {
            "lei_native_selected_topology_pressure_exception_debit_capacity_source_gate": True,
            "selected_cost_prefix_nonnegative": True,
            "pressure_null_prefixes_have_zero_exception_debit": True,
            "null_transaction_channel_fixed_before_payoff": True,
            "selected_topology_cost_is_pressure_exception_defined": True,
            "no_topology_cost_outside_pressure_exception_channel": True,
            "no_post_payoff_benign_null_selection": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyBenignPressureNullTransactionSource": True,
            "cost_prefix_eq_zero_on_pressureNull": True,
            "pressure_null_lock_benign_only_for_paid_transaction_channel": True,
        },
        "does_not_accept": [
            "projected_pressure_null_prefix_with_positive_topology_cost",
            "selected_cost_not_pressure_exception_defined",
            "exception_debit_not_forced_zero_on_null_prefix",
            "benign_null_channel_chosen_after_seeing_null_prefix",
            "topology_cost_outside_pressure_exception_channel",
        ],
    },
    "lei_native_selected_topology_benign_null_laundering_confuser_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "projected_pressure_abs_sum_zero": True,
            "positive_topology_cost_on_null_prefix": True,
            "selected_cost_not_pressure_exception_defined": True,
            "exception_debit_not_forced_zero_on_null_prefix": True,
            "benign_null_channel_chosen_after_seeing_null_prefix": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyBenignNullLaunderingConfuser": True,
            "LEINativeSelectedTopologyBenignPressureNullTransactionSource_excluded": True,
            "benign_null_requires_pressure_exception_defined_cost": True,
        },
        "does_not_accept": [
            "selected_topology_cost_is_pressure_exception_defined",
            "pressure_null_prefixes_have_zero_exception_debit",
            "null_transaction_channel_fixed_before_payoff",
        ],
    },
    "lei_native_selected_topology_unpaid_exception_debit_confuser_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "projected_pressure_null_directions_present": True,
            "exception_debit_same_selected_stream_missing": True,
            "exception_debit_prefix_budget_missing": True,
            "exception_debit_chosen_after_payoff": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyUnpaidExceptionDebitConfuser": True,
            "LEINativeSelectedTopologyPressureExceptionDebitCapacitySource_excluded": True,
            "paid_exception_debit_required": True,
        },
        "does_not_accept": [
            "exception_debit_prefix_budget_paid",
            "same_selected_stream_exception_debit_paid",
            "bridge_fixed_before_payoff_paid",
        ],
    },
    "lei_native_selected_topology_fresh_frequency_exception_debit_bridge_source_gate": {
        "requires": {
            "lei_native_selected_topology_pressure_exception_debit_capacity_source_gate": True,
            "fresh_frequency_event_same_tree_lock_available": True,
            "fresh_frequency_prefix_domination_from_subprimitives": True,
            "selected_topology_events_identified_with_fresh_frequency_events": True,
            "pressure_duhamel_same_carrier_lock_transfers_to_exception_debit": True,
            "bounded_fanout_no_log_reuse_transfers_to_selected_topology": True,
            "not_shell_only_duhamel_reserve": True,
            "no_bad_center_proxy_without_topology_identity": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyFreshFrequencyExceptionDebitBridgeSource": True,
            "fresh_frequency_same_tree_lock_can_source_exception_debit_conditionally": True,
            "selected_topology_to_fresh_frequency_identity_is_next_pde_theorem": True,
        },
        "does_not_accept": [
            "duhamel_reserve_shell_only",
            "bad_center_proxy_without_selected_topology_identity",
            "pressure_duhamel_carrier_mismatch",
            "bounded_fanout_label_without_no_log_reuse",
        ],
    },
    "lei_native_selected_topology_fresh_frequency_shell_only_confuser_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "fresh_frequency_or_duhamel_reserve_available": True,
            "selected_topology_to_fresh_frequency_identity_missing": True,
            "pressure_duhamel_same_carrier_lock_missing": True,
            "bounded_fanout_no_log_reuse_missing": True,
            "reserve_may_be_shell_or_process_section": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyFreshFrequencyShellOnlyConfuser": True,
            "LEINativeSelectedTopologyFreshFrequencyExceptionDebitBridgeSource_excluded": True,
            "selected_topology_identity_and_same_carrier_lock_required": True,
        },
        "does_not_accept": [
            "selected_topology_to_fresh_frequency_identity_paid",
            "pressure_duhamel_same_carrier_lock_paid",
            "bounded_fanout_no_log_reuse_paid",
            "not_shell_only_duhamel_reserve_paid",
        ],
    },
    "lei_native_selected_topology_localized_reconnection_tent_pressure_exception_capacity_source_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "pressure_plus_exception_controls_selected_cost_prefix": True,
            "pressure_sequence_creates_pollution_prefix": True,
            "clean_volume_accounting_for_selected_stream": True,
            "finite_orientation_capacity_and_exception_converted_to_budget": True,
            "same_selected_topology_event_stream": True,
            "exception_debit_same_selected_stream": True,
            "pressure_and_exception_bridge_fixed_before_payoff": True,
            "no_hidden_strict_margin_or_CF_import": True,
            "localized_reconnection_tent_family": True,
            "topology_extractor_produces_metric_tent_scale": True,
            "tent_map_fixed_before_payoff": True,
            "selected_event_covered_by_fresh_tent_or_paid_reconnection_error": True,
            "tent_index_map_cofinal_on_selected_prefixes": True,
            "same_owner_tree_section_scale_on_tents": True,
            "pressure_duhamel_same_carrier_on_tents": True,
            "bounded_tent_fanout_no_log_reuse": True,
            "selected_topology_exception_debit_dominated_by_tents": True,
            "fresh_frequency_plus_reconnection_fits_exception_budget": True,
            "exception_debit_prefix_matches_tent_debit": True,
            "no_bad_center_proxy_without_metric_tent_extraction": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyLocalizedReconnectionTentPressureExceptionCapacitySource": True,
            "LEINativeSelectedTopologyPressureExceptionDebitCapacitySource": True,
            "selected_topology_prefix_bound_from_metric_reconnection_tents": True,
            "exception_debit_prefix_budget_derived_not_assumed": True,
        },
        "does_not_accept": [
            "topology_label_without_metric_tent_scale",
            "reconnection_count_without_viscous_error_budget",
            "bad_center_shell_proxy_without_metric_tent_extraction",
            "tent_map_chosen_after_payoff",
            "pressure_duhamel_carrier_mismatch_on_tents",
            "combined_fresh_frequency_and_reconnection_budget_unpaid",
        ],
    },
    "selected_topology_localized_reconnection_tent_metric_scale_confuser_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "genuine_topology_or_reconnection_labels": True,
            "reconnection_count_or_shell_incidence_available": True,
            "metric_tent_scale_missing": True,
            "localized_tent_family_missing": True,
            "tent_map_may_be_post_payoff_or_bad_center_proxy": True,
            "same_pressure_duhamel_carrier_on_tents_missing": True,
            "combined_fresh_frequency_reconnection_budget_missing": True,
        },
        "concludes": {
            "SelectedTopologyLocalizedReconnectionTentMetricScaleConfuser": True,
            "LEINativeSelectedTopologyLocalizedReconnectionTentPressureExceptionCapacitySource_excluded": True,
            "metric_tent_localization_and_paid_error_required": True,
        },
        "does_not_accept": [
            "metric_tent_scale_paid",
            "localized_reconnection_tent_family_paid",
            "tent_map_fixed_before_payoff_paid",
            "same_pressure_duhamel_carrier_on_tents_paid",
            "combined_fresh_frequency_reconnection_budget_paid",
        ],
    },
    "lei_native_selected_topology_metric_tent_besicovitch_no_reuse_pressure_exception_source_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "localized_reconnection_tent_family": True,
            "topology_extractor_produces_metric_tent_scale": True,
            "metric_tent_besicovitch_engulfing": True,
            "metric_tent_same_carrier_packing": True,
            "tent_map_fixed_before_payoff": True,
            "tent_index_map_cofinal_on_selected_prefixes": True,
            "same_owner_tree_section_scale_on_tents": True,
            "pressure_duhamel_same_carrier_on_tents": True,
            "metric_tent_bounded_fanout_no_log_reuse": True,
            "selected_tent_debit_dominated_by_multiplicity": True,
            "multiplicity_invoice_paid_by_fresh_frequency_budget": True,
            "fresh_frequency_plus_reconnection_fits_exception_budget": True,
            "exception_debit_prefix_matches_tent_debit": True,
            "no_bad_center_proxy_without_metric_tent_extraction": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyMetricTentBesicovitchNoReusePressureExceptionSource": True,
            "LEINativeSelectedTopologyLocalizedReconnectionTentPressureExceptionCapacitySource": True,
            "selected_topology_prefix_bound_from_metric_tent_no_reuse": True,
            "bounded_tent_fanout_derived_from_metric_packing": True,
        },
        "does_not_accept": [
            "metric_tent_label_without_besicovitch_engulfing",
            "nested_tent_reuse_across_selected_prefixes",
            "same_carrier_packing_missing",
            "multiplicity_invoice_unpaid",
            "bad_center_shell_proxy_without_metric_tent_extraction",
        ],
    },
    "selected_topology_metric_tent_nested_reuse_confuser_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "localized_metric_tent_labels_present": True,
            "tent_family_nested_across_selected_prefixes": True,
            "unbounded_tent_overlap_or_log_reuse": True,
            "same_carrier_packing_missing": True,
            "multiplicity_invoice_not_paid_by_fresh_frequency_budget": True,
        },
        "concludes": {
            "SelectedTopologyMetricTentNestedReuseConfuser": True,
            "LEINativeSelectedTopologyMetricTentBesicovitchNoReusePressureExceptionSource_excluded": True,
            "same_carrier_metric_packing_and_multiplicity_invoice_required": True,
        },
        "does_not_accept": [
            "metric_tent_besicovitch_engulfing_paid",
            "bounded_tent_fanout_no_log_reuse_paid",
            "same_carrier_packing_paid",
            "multiplicity_invoice_paid_by_fresh_frequency_budget",
        ],
    },
    "leray_topology_reconnection_vitali_packing_source_gate": {
        "requires": {
            "lei_native_selected_topology_metric_tent_besicovitch_no_reuse_pressure_exception_source_gate": True,
            "ambient_parabolic_metric_or_quasi_metric": True,
            "leray_stable_topology_reconnection_extractor": True,
            "scale_radius_fixed_by_extractor": True,
            "doubling_or_besicovitch_constant_uniform": True,
            "bounded_eccentricity_or_engulfing": True,
            "vitali_or_whitney_selection_fixed_before_payoff": True,
            "selected_prefix_coverage_or_paid_omission": True,
            "same_pressure_duhamel_carrier_after_selection": True,
            "bounded_overlap_uniform_in_prefix": True,
            "nested_children_paid_by_parent_or_error_budget": True,
            "metric_covering_selection_receipt_passed": True,
            "same_carrier_packing_receipt_passed": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LerayTopologyReconnectionVitaliPackingSource": True,
            "LEINativeSelectedTopologyMetricTentBesicovitchNoReusePressureExceptionSource": True,
            "same_carrier_metric_packing_derived_from_covering_source": True,
        },
        "does_not_accept": [
            "besicovitch_label_without_covering_hypotheses",
            "topology_reconnection_label_without_leray_stable_extractor",
            "post_payoff_vitali_selection",
            "selected_prefix_omissions_unpaid",
            "same_carrier_packing_missing",
            "nested_children_rebilled_across_prefixes",
        ],
    },
    "selected_topology_nonwhitney_nested_cascade_confuser_gate": {
        "requires": {
            "localized_metric_tent_labels_present": True,
            "dyadic_reconnection_cascade_same_center": True,
            "selected_prefix_counts_nested_children": True,
            "vitali_subcover_discards_unpaid_children": True,
            "bounded_overlap_not_uniform_in_selected_prefix": True,
            "same_carrier_atom_reused_across_scales": True,
        },
        "concludes": {
            "SelectedTopologyNonWhitneyNestedCascadeConfuser": True,
            "LerayTopologyReconnectionVitaliPackingSource_excluded": True,
            "parent_pays_children_or_paid_omission_required": True,
        },
        "does_not_accept": [
            "selected_prefix_coverage_or_paid_omission",
            "nested_children_paid_by_parent_or_error_budget",
            "bounded_overlap_uniform_in_prefix",
        ],
    },
    "heat_scale_persistent_topology_extractor_source_gate": {
        "requires": {
            "leray_topology_reconnection_vitali_packing_source_gate": True,
            "heat_mollification_scale_fixed_before_payoff": True,
            "persistent_barcode_extractor_leray_stable": True,
            "superlevel_topology_features_canonical_away_from_zero_set": True,
            "barcode_features_produce_parabolic_tents": True,
            "persistence_lifetime_gives_scale_radius": True,
            "persistence_threshold_declared_before_target": True,
            "barcode_vitali_whitney_selection_fixed_before_payoff": True,
            "barcode_selection_covers_prefix_or_pays_deaths": True,
            "barcode_carrier_matches_pressure_duhamel_carrier": True,
            "barcode_overlap_uniform_in_prefix": True,
            "bar_death_pays_nested_or_omitted_children": True,
            "persistent_selected_debit_dominated_by_covering": True,
            "multiplicity_invoice_paid_by_fresh_frequency_budget": True,
            "no_raw_vortex_line_topology_substitution": True,
            "metric_covering_selection_receipt_passed": True,
            "same_carrier_packing_receipt_passed": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "HeatScalePersistentTopologyExtractorSource": True,
            "LerayTopologyReconnectionVitaliPackingSource": True,
            "LEINativeSelectedTopologyMetricTentBesicovitchNoReusePressureExceptionSource": True,
            "selected_prefix_bound_from_heat_scale_persistence": True,
        },
        "does_not_accept": [
            "raw_vortex_line_topology_label_only",
            "persistence_threshold_chosen_after_target",
            "bar_death_budget_not_same_carrier",
            "stable_barcode_without_debit_inequality",
            "heat_smoothing_topology_not_tied_to_exception_debit",
        ],
    },
    "heat_scale_persistent_topology_instability_confuser_gate": {
        "requires": {
            "raw_vortex_line_topology_label_present": True,
            "vorticity_zero_set_topology_undefined": True,
            "leray_limit_barcode_instability": True,
            "persistence_threshold_chosen_after_target": True,
            "bar_death_budget_not_same_carrier": True,
        },
        "concludes": {
            "HeatScalePersistentTopologyInstabilityConfuser": True,
            "HeatScalePersistentTopologyExtractorSource_excluded": True,
            "bar_death_same_carrier_budget_required": True,
        },
        "does_not_accept": [
            "persistent_barcode_extractor_leray_stable",
            "persistence_threshold_declared_before_target",
            "bar_death_pays_nested_or_omitted_children",
            "barcode_carrier_matches_pressure_duhamel_carrier",
        ],
    },
    "heat_scale_total_persistence_regularity_budget_source_gate": {
        "requires": {
            "heat_scale_persistent_bar_death_leray_budget_source_gate": True,
            "total_persistence_requires_lipschitz_or_equivalent_regularity": True,
            "heat_mollified_vorticity_lipschitz_budget_same_carrier": True,
            "heat_scale_lipschitz_controls_persistence_regularity": True,
            "persistence_regularity_controls_total_persistence": True,
            "heat_scale_lipschitz_budget_fits_leray_dissipation": True,
            "regularity_input_no_stronger_than_leray": True,
            "no_fixed_scale_smoothness_as_uniform_scale_summability": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "HeatScaleTotalPersistenceRegularityBudgetSource": True,
            "HeatScalePersistentBarDeathLerayBudgetSource": True,
            "selected_prefix_bound_from_scale_summable_persistence_regularity": True,
        },
        "does_not_accept": [
            "fixed_scale_smoothness_only",
            "ordinary_persistence_stability_only",
            "lipschitz_budget_blows_along_cascade",
            "supercritical_regular_input_hidden",
        ],
    },
    "heat_scale_lipschitz_blowup_total_persistence_confuser_gate": {
        "requires": {
            "fixed_scale_mollified_vorticity_smooth": True,
            "lipschitz_constant_blows_along_cascade": True,
            "total_persistence_theorem_needs_scale_regularity": True,
            "leray_budget_only_energy_level_not_scale_summable_lipschitz": True,
            "fixed_scale_smoothness_mistaken_for_uniform_budget": True,
        },
        "concludes": {
            "HeatScaleLipschitzBlowupTotalPersistenceConfuser": True,
            "HeatScaleTotalPersistenceRegularityBudgetSource_excluded": True,
            "leray_paid_heat_scale_carleson_bar_budget_required": True,
        },
        "does_not_accept": [
            "heat_scale_lipschitz_budget_fits_leray_dissipation",
            "regularity_input_no_stronger_than_leray",
            "fixed_scale_smoothness_only",
        ],
    },
    "persistent_topology_bar_death_budget_dichotomy_gate": {
        "requires": {
            "heat_scale_total_persistence_regularity_budget_source_gate": True,
            "ordinary_bottleneck_stability_not_total_debit_budget": True,
            "quantitative_regularity_or_carleson_budget_dichotomy": True,
            "has_uniform_lipschitz_or_bv_or_w1p_or_degree_bound": True,
            "has_leray_paid_heat_scale_carleson_bar_budget": True,
        },
        "concludes": {
            "PersistentTopologyBarDeathBudgetDichotomy": True,
            "ordinary_persistence_stability_not_enough": True,
        },
        "does_not_accept": [
            "bottleneck_stability_only",
            "total_bar_debit_budget_missing",
            "no_leray_paid_heat_scale_carleson_bar_budget",
        ],
    },
    "persistent_stability_without_budget_confuser_gate": {
        "requires": {
            "bottleneck_stability_available": True,
            "total_bar_debit_budget_missing": True,
            "no_uniform_lipschitz_bv_w1p_degree_bound": True,
            "no_leray_paid_heat_scale_carleson_bar_budget": True,
        },
        "concludes": {
            "PersistentStabilityWithoutBudgetConfuser": True,
            "PersistentTopologyBarDeathBudgetDichotomy_excluded": True,
            "ordinary_persistence_stability_not_total_debit_budget": True,
        },
        "does_not_accept": [
            "has_uniform_lipschitz_or_bv_or_w1p_or_degree_bound",
            "has_leray_paid_heat_scale_carleson_bar_budget",
        ],
    },
    "heat_scale_carleson_bar_budget_source_gate": {
        "requires": {
            "heat_scale_persistent_topology_extractor_source_gate": True,
            "heat_square_function_paid_by_leray_dissipation": True,
            "elder_rule_barcode_tree_same_carrier": True,
            "barcode_deaths_mapped_to_heat_square_function_atoms": True,
            "barcode_death_debit_controlled_by_square_function": True,
            "selected_omission_debit_equals_elder_rule_death_debit": True,
            "no_persistence_stability_substitution": True,
            "no_heat_smoothing_only_substitution": True,
            "owner_preimage_receipt_passed": True,
            "no_rebilling_freshness_receipt_passed": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "HeatScaleCarlesonBarBudgetSource": True,
            "HeatScalePersistentTopologyExtractorSource": True,
            "heat_scale_bar_death_budget_paid_by_square_function": True,
        },
        "does_not_accept": [
            "persistence_stability_only",
            "heat_smoothing_only",
            "barcode_deaths_not_mapped_to_heat_square_function_atoms",
            "elder_rule_tree_not_same_pressure_carrier",
            "bar_death_debit_without_square_function_control",
            "owner_preimage_receipt_missing",
            "no_rebilling_freshness_receipt_missing",
        ],
    },
    "barcode_death_square_function_counting_source_gate": {
        "requires": {
            "heat_scale_carleson_bar_budget_source_gate": True,
            "heat_square_function_controls_coarea_perimeter": True,
            "coarea_perimeter_controls_topology_with_thickness": True,
            "barcode_death_debit_controlled_by_topological_counting": True,
            "thickness_reach_or_morse_complexity_receipt_passed": True,
            "barcode_counting_carrier_matches_heat_square_function_carrier": True,
            "no_raw_coarea_as_betti_count": True,
            "no_unpaid_thin_handle_topology": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "BarcodeDeathSquareFunctionCountingSource": True,
            "HeatScaleCarlesonBarBudgetSource": True,
            "unweighted_barcode_counting_requires_thickness_receipt": True,
        },
        "does_not_accept": [
            "bare_coarea_as_betti_count",
            "thin_handle_topology_without_thickness",
            "square_function_without_bar_counting",
            "topology_event_count_without_complexity_receipt",
        ],
    },
    "thin_handle_barcode_counting_confuser_gate": {
        "requires": {
            "heat_square_function_budget_available": True,
            "coarea_perimeter_budget_available": True,
            "many_thin_handles_create_barcode_deaths": True,
            "no_thickness_reach_or_morse_complexity_receipt": True,
            "topology_count_not_controlled_by_perimeter_alone": True,
        },
        "concludes": {
            "ThinHandleBarcodeCountingConfuser": True,
            "BarcodeDeathSquareFunctionCountingSource_excluded": True,
            "weighted_or_complexity_receipt_required": True,
        },
        "does_not_accept": [
            "thickness_reach_or_morse_complexity_receipt_passed",
            "coarea_perimeter_controls_topology_with_thickness",
            "barcode_death_debit_controlled_by_topological_counting",
        ],
    },
    "weighted_heat_scale_barcode_death_square_function_source_gate": {
        "requires": {
            "heat_scale_carleson_bar_budget_source_gate": True,
            "weighted_death_debit_matches_exception_debit": True,
            "weighted_barcode_death_controlled_by_square_function": True,
            "heat_square_function_budget_paid_by_viscous_error": True,
            "persistence_capacity_weight_declared_before_payoff": True,
            "same_carrier_weighted_death_collars": True,
            "bounded_overlap_weighted_collars": True,
            "no_raw_topology_count_substitution": True,
            "owner_preimage_receipt_passed": True,
            "no_rebilling_freshness_receipt_passed": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "WeightedHeatScaleBarcodeDeathSquareFunctionSource": True,
            "HeatScaleCarlesonBarBudgetSource": True,
            "weighted_persistence_capacity_currency_pays_selected_omissions": True,
        },
        "does_not_accept": [
            "raw_barcode_event_count_used_as_exception_debit",
            "thin_handle_events_have_tiny_persistence_weight",
            "weighted_death_debit_does_not_match_exception_debit",
            "post_payoff_weight_selection",
            "weighted_collars_without_same_carrier_overlap",
        ],
    },
    "raw_topology_count_not_weighted_debit_confuser_gate": {
        "requires": {
            "weighted_square_function_budget_available": True,
            "raw_barcode_event_count_used_as_exception_debit": True,
            "thin_handle_events_have_tiny_persistence_weight": True,
            "weighted_death_debit_does_not_match_exception_debit": True,
        },
        "concludes": {
            "RawTopologyCountNotWeightedDebitConfuser": True,
            "WeightedHeatScaleBarcodeDeathSquareFunctionSource_excluded": True,
            "exception_debit_must_be_weighted_not_raw_count": True,
        },
        "does_not_accept": [
            "weighted_death_debit_matches_exception_debit",
            "no_raw_topology_count_substitution",
            "same_carrier_weighted_death_collars",
        ],
    },
    "weighted_omission_debit_identity_source_gate": {
        "requires": {
            "weighted_heat_scale_barcode_death_square_function_source_gate": True,
            "omitted_child_debit_bounded_by_weighted_bars": True,
            "weighted_barcode_death_controlled_by_square_function": True,
            "heat_square_function_budget_paid_by_viscous_error": True,
            "omitted_child_map_fixed_before_payoff": True,
            "omitted_children_same_carrier_as_weighted_bars": True,
            "omitted_child_weight_not_raw_count": True,
            "no_hidden_reach_lipschitz_or_bv_input": True,
            "owner_preimage_receipt_passed": True,
            "no_rebilling_freshness_receipt_passed": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "WeightedOmissionDebitIdentitySource": True,
            "WeightedHeatScaleBarcodeDeathSquareFunctionSource": True,
            "omitted_child_debit_identity_is_the_level308_residual": True,
        },
        "does_not_accept": [
            "raw_omitted_children_count_used_as_debit",
            "tiny_persistence_omitted_children_survive_selection",
            "weighted_debit_finite_but_raw_omission_debit_large",
            "hidden_reach_lipschitz_or_bv_input",
            "post_payoff_omitted_child_weighting",
        ],
    },
    "raw_omission_debit_not_weighted_confuser_gate": {
        "requires": {
            "raw_omitted_children_count_used_as_debit": True,
            "tiny_persistence_omitted_children_survive_selection": True,
            "weighted_debit_finite_but_raw_omission_debit_large": True,
            "no_pre_payoff_weight_lower_bound_for_omitted_children": True,
        },
        "concludes": {
            "RawOmissionDebitNotWeightedConfuser": True,
            "WeightedOmissionDebitIdentitySource_excluded": True,
            "level307_weighted_route_reduces_to_raw_omission_debit_trap": True,
        },
        "does_not_accept": [
            "omitted_child_debit_bounded_by_weighted_bars",
            "omitted_child_weight_not_raw_count",
            "omitted_children_same_carrier_as_weighted_bars",
        ],
    },
    "analytic_collar_weighted_omission_debit_source_gate": {
        "requires": {
            "weighted_omission_debit_identity_source_gate": True,
            "omitted_child_debit_controlled_by_analytic_collar": True,
            "analytic_collar_weight_controlled_by_heat_square_function": True,
            "heat_square_function_budget_paid_by_viscous_error": True,
            "analytic_collar_weight_fixed_before_payoff": True,
            "analytic_collar_weight_not_defined_from_target_debit": True,
            "same_carrier_pressure_duhamel_collar": True,
            "no_hidden_cz_endpoint_or_regular_input": True,
            "owner_preimage_receipt_passed": True,
            "no_rebilling_freshness_receipt_passed": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "AnalyticCollarWeightedOmissionDebitSource": True,
            "WeightedOmissionDebitIdentitySource": True,
            "analytic_collar_source_is_level309_residual": True,
        },
        "does_not_accept": [
            "collar_weight_defined_from_target_debit",
            "pressure_endpoint_positivity_needed",
            "heat_square_function_does_not_control_pressure_collar",
            "same_carrier_or_pre_payoff_binding_missing",
            "hidden_reach_lipschitz_or_bv_input",
        ],
    },
    "target_defined_analytic_collar_weight_confuser_gate": {
        "requires": {
            "collar_weight_defined_from_target_debit": True,
            "pressure_endpoint_positivity_needed": True,
            "heat_square_function_does_not_control_pressure_collar": True,
            "same_carrier_or_pre_payoff_binding_missing": True,
        },
        "concludes": {
            "TargetDefinedAnalyticCollarWeightConfuser": True,
            "AnalyticCollarWeightedOmissionDebitSource_excluded": True,
            "analytic_collar_weight_route_is_tautological_or_endpoint_blocked": True,
        },
        "does_not_accept": [
            "analytic_collar_weight_not_defined_from_target_debit",
            "analytic_collar_weight_controlled_by_heat_square_function",
            "same_carrier_pressure_duhamel_collar",
            "analytic_collar_weight_fixed_before_payoff",
        ],
    },
    "analytic_collar_exception_debit_retyping_source_gate": {
        "requires": {
            "lei_native_selected_topology_localized_reconnection_tent_pressure_exception_capacity_source_gate": True,
            "analytic_collar_weighted_omission_debit_source_gate": True,
            "exception_debit_prefix_dominated_by_analytic_collar": True,
            "analytic_collar_fits_exception_budget": True,
            "same_selected_stream_retyping": True,
            "retyping_fixed_before_payoff": True,
            "no_target_defined_exception_debit_retyping": True,
            "no_hidden_no_null_or_cz_endpoint_input": True,
            "owner_preimage_receipt_passed": True,
            "no_rebilling_freshness_receipt_passed": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "AnalyticCollarExceptionDebitRetypingSource": True,
            "LEINativeSelectedTopologyPressureExceptionDebitCapacitySource": True,
            "selected_exception_debit_currency_retyped_to_analytic_collar": True,
        },
        "does_not_accept": [
            "pressure_plus_exception_needs_original_debit_seq",
            "analytic_collar_mass_not_lower_bound_for_exception_debit_seq",
            "retyping_defined_after_seeing_exception_debit",
            "no_null_or_cz_endpoint_needed_for_domination",
            "exception_debit_label_only",
        ],
    },
    "analytic_collar_retyping_does_not_pay_exception_debit_confuser_gate": {
        "requires": {
            "pressure_plus_exception_needs_original_debit_seq": True,
            "analytic_collar_mass_not_lower_bound_for_exception_debit_seq": True,
            "retyping_defined_after_seeing_exception_debit": True,
            "no_null_or_cz_endpoint_needed_for_domination": True,
        },
        "concludes": {
            "AnalyticCollarRetypingDoesNotPayExceptionDebitConfuser": True,
            "AnalyticCollarExceptionDebitRetypingSource_excluded": True,
            "analytic_collar_branch_does_not_pay_upstream_exception_debit": True,
        },
        "does_not_accept": [
            "exception_debit_prefix_dominated_by_analytic_collar",
            "same_selected_stream_retyping",
            "retyping_fixed_before_payoff",
            "no_target_defined_exception_debit_retyping",
        ],
    },
    "pressure_exception_to_heat_collar_injection_source_gate": {
        "requires": {
            "analytic_collar_exception_debit_retyping_source_gate": True,
            "exception_debit_seq_prefix_matches_atoms": True,
            "pointwise_exception_debit_dominated_by_collar_mass": True,
            "collar_preimage_multiplicity_controls_prefix": True,
            "collar_weight_fits_exception_budget": True,
            "injection_fixed_before_payoff": True,
            "same_pressure_duhamel_heat_collar_carrier": True,
            "no_hidden_no_null_or_endpoint_positivity": True,
            "owner_preimage_receipt_passed": True,
            "same_carrier_packing_receipt_passed": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "PressureExceptionToHeatCollarInjectionSource": True,
            "AnalyticCollarExceptionDebitRetypingSource": True,
            "exception_debit_prefix_paid_by_heat_collar_injection": True,
        },
        "does_not_accept": [
            "pressure_null_exception_atoms_present_without_heat_lower_bound",
            "pointwise_debit_domination_requires_no_null_or_endpoint",
            "nested_exception_atoms_reuse_one_heat_collar",
            "assignment_target_defined_after_payoff",
        ],
    },
    "pressure_null_exception_no_heat_collar_lower_bound_confuser_gate": {
        "requires": {
            "pressure_null_exception_atoms_present": True,
            "heat_square_collar_mass_can_be_arbitrarily_small": True,
            "pointwise_debit_domination_requires_no_null_or_endpoint": True,
            "nested_exception_atoms_reuse_one_heat_collar": True,
        },
        "concludes": {
            "PressureNullExceptionNoHeatCollarLowerBoundConfuser": True,
            "PressureExceptionToHeatCollarInjectionSource_excluded": True,
            "exception_to_heat_collar_injection_reduces_to_no_null_endpoint_wall": True,
        },
        "does_not_accept": [
            "pointwise_exception_debit_dominated_by_collar_mass",
            "same_pressure_duhamel_heat_collar_carrier",
            "injection_fixed_before_payoff",
            "collar_preimage_multiplicity_controls_prefix",
        ],
    },
    "heat_null_exception_debit_compatibility_source_gate": {
        "requires": {
            "analytic_collar_exception_debit_retyping_source_gate": True,
            "exception_debit_seq_prefix_matches_atoms": True,
            "heat_null_implies_zero_exception_debit": True,
            "quantitative_heat_collar_debit_compatibility": True,
            "collar_preimage_multiplicity_controls_prefix": True,
            "collar_weight_fits_exception_budget": True,
            "compatibility_fixed_before_payoff": True,
            "same_selected_stream_heat_collar_carrier": True,
            "no_hidden_no_null_or_cz_endpoint_input": True,
            "same_carrier_packing_receipt_passed": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "HeatNullExceptionDebitCompatibilitySource": True,
            "PressureExceptionToHeatCollarInjectionSource": True,
            "heat_null_compatibility_pays_original_exception_debit": True,
        },
        "does_not_accept": [
            "exception_debit_redefined_as_heat_mass",
            "positive_exception_debit_on_heat_null_atom",
            "hidden_cz_endpoint_or_no_null_input",
            "surrogate_omitted_child_debit_only",
        ],
    },
    "heat_null_positive_exception_debit_confuser_gate": {
        "requires": {
            "heat_null_positive_exception_atom_present": True,
            "bad_atom_heat_collar_mass_zero": True,
            "bad_atom_exception_debit_positive": True,
            "quantitative_domination_would_use_no_null_endpoint": True,
        },
        "concludes": {
            "HeatNullPositiveExceptionDebitConfuser": True,
            "HeatNullExceptionDebitCompatibilitySource_excluded": True,
            "analytic_collar_weighted_barcode_branch_retires": True,
        },
        "does_not_accept": [
            "heat_null_implies_zero_exception_debit",
            "quantitative_heat_collar_debit_compatibility",
            "no_hidden_no_null_or_cz_endpoint_input",
        ],
    },
    "lei_native_selected_topology_fresh_frequency_dominated_exception_debit_source_gate": {
        "requires": {
            "lei_native_selected_topology_pressure_exception_debit_capacity_source_gate": True,
            "pre_payoff_injection_to_fresh_frequency_events": True,
            "cofinal_on_selected_prefixes": True,
            "same_owner_tree_section_scale": True,
            "pressure_duhamel_same_carrier_lock_transfers": True,
            "bounded_fanout_no_log_reuse_transfers": True,
            "selected_topology_exception_debit_dominated": True,
            "fresh_frequency_plus_reconnection_fits_exception_budget": True,
            "exception_debit_prefix_matches_source": True,
            "no_bad_center_proxy_without_topology_extraction": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyFreshFrequencyDominatedExceptionDebitSource": True,
            "selected_topology_exception_debit_prefix_budget_paid_conditionally": True,
            "identity_weakened_to_dominated_transfer_plus_reconnection_error": True,
        },
        "does_not_accept": [
            "literal_identity_label_without_injection",
            "bad_center_shell_proxy_without_topology_extraction",
            "duhamel_section_mismatch",
            "pressure_carrier_mismatch",
            "combined_fresh_frequency_and_reconnection_budget_unpaid",
        ],
    },
    "selected_topology_fresh_frequency_identity_stress_packet_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "genuine_topology_or_reconnection_labels": True,
            "matching_bad_center_shells": True,
            "duhamel_section_mismatched": True,
            "pressure_carrier_mismatched": True,
            "pre_payoff_injection_or_cofinality_missing": True,
        },
        "concludes": {
            "SelectedTopologyFreshFrequencyIdentityStressPacket": True,
            "LEINativeSelectedTopologyFreshFrequencyDominatedExceptionDebitSource_excluded": True,
            "pre_payoff_injection_and_same_carrier_transfer_required": True,
        },
        "does_not_accept": [
            "pre_payoff_injection_paid",
            "same_pressure_carrier_paid",
            "same_duhamel_section_paid",
            "viscous_reconnection_error_paid",
        ],
    },
    "lei_native_selected_topology_null_locked_subsequence_confuser_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "positive_topology_prefix_cost": True,
            "selected_topology_stream_linked_to_pressure_sequence": True,
            "projected_pressure_abs_sum_zero_or_sublinear_on_selected_prefix": True,
            "null_locked_subsequence_fixed_before_payoff": True,
            "no_CF_BV_ESS_or_raw_CZ_import": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyNullLockedSubsequenceConfuser": True,
            "LEINativeSelectedTopologyPointwiseTransversalityNoNullLockSource_excluded": True,
            "LEINativeSelectedTopologyNoNullLockPollutionBridgeSource_excluded_unless_average_or_exception_debit_paid": True,
            "average_no_null_lock_or_exception_debit_theorem_required": True,
        },
        "does_not_accept": [
            "pressure_magnitude_without_signed_projection",
            "sum_of_squares_pressure_visibility",
            "post_payoff_null_subsequence_selection",
            "strict_margin_or_CF_import_hidden_as_transversality",
        ],
    },
    "lei_native_selected_topology_pressure_null_lock_confuser_gate": {
        "requires": {
            "lei_native_selected_topology_fresh_cost_source_gate": True,
            "projected_pressure_magnitude_available": True,
            "selected_topology_stream_to_pressure_sequence_missing": True,
            "no_null_lock_missing_on_selected_prefixes": True,
            "selected_topology_events_may_sit_in_CZ_nulls": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyPressureNullLockConfuser": True,
            "LEINativeSelectedTopologyNoNullLockPollutionBridgeSource_excluded": True,
            "sequence_no_null_lock_required": True,
        },
        "does_not_accept": [
            "selected_topology_stream_linked_to_pressure_sequence_paid",
            "no_null_lock_on_selected_topology_prefixes_paid",
            "pressure_bridge_fixed_before_payoff_paid",
        ],
    },
    "lei_native_selected_topology_no_null_lock_orientation_capacity_source_gate": {
        "requires": {
            "lei_native_selected_topology_no_null_lock_pollution_bridge_source_gate": True,
            "clean_volume_accounting_for_selected_stream": True,
            "finite_orientation_capacity_converted_to_budget": True,
            "no_hidden_capacity_only_bookkeeping": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LEINativeSelectedTopologyNoNullLockOrientationCapacitySource": True,
            "selected_topology_prefix_bound_from_no_null_lock_capacity": True,
            "composite_positive_constructor_candidate": True,
        },
        "does_not_accept": [
            "no_null_lock_without_capacity_accounting",
            "capacity_accounting_without_no_null_lock_pollution",
            "finite_capacity_label_only",
            "pressure_magnitude_without_selected_sequence",
        ],
    },
    "suitable_defect_backed_high_interface_measure_split_core_gate": {
        "requires": {
            "local_energy_invoice_high_interface_dominance_source": True,
            "suitable_local_energy_defect_measure_source": True,
            "high_interface_event_set_fixed_before_payoff": True,
            "high_interface_payment_eq_active_measure": True,
            "high_interface_boundary_charge_eq_visible_plus_residual": True,
            "active_measure_eq_defect_active_on_H": True,
            "visible_boundary_measure_eq_defect_transport_pressure_commutator_on_H": True,
            "residual_reserve_measure_eq_defect_residual_on_H": True,
            "suitable_defect_positive_variation_domination": True,
            "residual_reserve_backed_by_suitable_defect": True,
            "no_posthoc_residual_backed_by_suitable_defect": True,
            "measure_split_not_whole_space_scalar_only": True,
            "owner_preimage_prefix_inequality": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "SuitableDefectBackedHighInterfaceMeasureSplitCore": True,
            "LocalEnergyMeasureSplitHighInterfaceInvoiceSource": True,
            "LocalEnergyInvoiceHighInterfaceDominanceSource": True,
            "residual_reserve_not_target_deficit": True,
        },
        "does_not_accept": [
            "already_assumed_local_energy_measure_domination",
            "local_energy_measure_split_without_suitable_defect_source",
            "residual_reserve_defined_from_boundary_deficit",
            "signed_local_energy_identity_without_positive_variation_domination",
            "whole_space_scalar_defect_measure",
            "post_payoff_H_event_binding",
        ],
    },
    "suitable_defect_backed_high_interface_measure_split_source_gate": {
        "requires": {
            "local_energy_measure_split_high_interface_invoice_source": True,
            "suitable_local_energy_defect_measure_source": True,
            "active_measure_eq_defect_active_on_H": True,
            "visible_boundary_measure_eq_defect_transport_pressure_commutator_on_H": True,
            "residual_reserve_measure_eq_defect_residual_on_H": True,
            "suitable_defect_positive_variation_domination": True,
            "residual_reserve_backed_by_suitable_defect": True,
            "no_posthoc_residual_backed_by_suitable_defect": True,
            "high_interface_event_set_fixed_before_payoff": True,
            "owner_preimage_prefix_inequality": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "SuitableDefectBackedHighInterfaceMeasureSplitSource": True,
            "LocalEnergyMeasureSplitHighInterfaceInvoiceSource": True,
            "LocalEnergyInvoiceHighInterfaceDominanceSource": True,
            "residual_reserve_not_target_deficit": True,
        },
        "does_not_accept": [
            "local_energy_measure_split_without_suitable_defect_source",
            "residual_reserve_defined_from_boundary_deficit",
            "signed_local_energy_identity_without_positive_variation_domination",
            "whole_space_scalar_defect_measure",
            "post_payoff_H_event_binding",
        ],
    },
    "local_energy_measure_split_high_interface_invoice_source_gate": {
        "requires": {
            "local_energy_invoice_high_interface_dominance_source": True,
            "high_interface_event_set_fixed_before_payoff": True,
            "high_interface_payment_eq_active_measure": True,
            "high_interface_boundary_charge_eq_visible_plus_residual": True,
            "local_energy_measure_domination_on_high_interface_prefix": True,
            "measure_split_not_whole_space_scalar_only": True,
            "residual_reserve_independently_generated": True,
            "visible_boundary_and_residual_same_owner_prefix": True,
            "residual_reserve_not_defined_from_boundary_deficit": True,
            "owner_preimage_prefix_inequality": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LocalEnergyMeasureSplitHighInterfaceInvoiceSource": True,
            "LocalEnergyInvoiceHighInterfaceDominanceSource": True,
            "HighInterfaceFinitePrefixAverageBoundaryDominanceSource": True,
            "high_interface_payment_le_boundary_charge_from_measure_split": True,
        },
        "does_not_accept": [
            "whole_space_scalar_measure_split",
            "signed_local_energy_split_only",
            "unpaid_residual_reserve",
            "residual_reserve_defined_from_boundary_deficit",
            "post_payoff_high_interface_event_set",
        ],
    },
    "suitable_defect_event_family_binding_confuser_gate": {
        "requires": {
            "high_interface_prefix_family_visible": True,
            "suitable_defect_source_visible": True,
            "same_vocabulary_or_finite_prefix_only": True,
            "event_identity_missing": True,
            "pre_payoff_same_carrier_binding_missing": True,
            "proxy_family_may_differ_from_LEI_event_tents": True,
        },
        "concludes": {
            "SuitableDefectEventFamilyBindingConfuser": True,
            "SuitableDefectBackedHighInterfaceMeasureSplitCore_excluded": True,
            "event_family_binding_receipt_required": True,
        },
        "does_not_accept": [
            "event_identity_paid",
            "same_carrier_H_to_LEI_binding_paid",
            "pre_payoff_total_prefix_index_map_paid",
        ],
    },
    "local_energy_invoice_dominance_confuser_gate": {
        "requires": {
            "interface_weighted_boundary_paid_floor_correlation_confuser": True,
            "signed_local_energy_split_visible": True,
            "interface_le_boundary_plus_unpaid_residual_only": True,
            "residual_reserve_unpaid_or_defined_from_deficit": True,
            "positive_local_energy_invoice_dominance_missing": True,
        },
        "concludes": {
            "LocalEnergyInvoiceDominanceConfuser": True,
            "LocalEnergyInvoiceHighInterfaceDominanceSource_excluded": True,
            "residual_reserve_payment_required": True,
        },
        "does_not_accept": [
            "paid_residual_reserve_present",
            "local_energy_invoice_positive_and_same_owner",
            "residual_reserve_independently_generated",
        ],
    },
    "bounded_boundary_interface_ratio_source_gate": {
        "requires": {
            "boundary_paid_high_interface_size_sum_source": True,
            "boundary_paid_measure_lower_bound_nonnegative": True,
            "ratio_mean_surplus_nonnegative": True,
            "ratio_upper_bound_gt_one": True,
            "lower_bound_mul_ratio_slack_le_mean_surplus": True,
            "ratio_mean_surplus_le_ratio_slack_mul_boundary_paid_set_measure": True,
            "lower_bound_plus_high_interface_overfills_threshold": True,
            "rho_defined_on_same_source_law": True,
            "ratio_upper_bound_fixed_before_payoff": True,
            "ratio_upper_bound_same_prefix": True,
            "ratio_cap_not_from_target_deficit": True,
            "source_law_measure_converts_to_threshold_measure": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "BoundedBoundaryInterfaceRatioSource": True,
            "BoundaryPaidHighInterfaceSizeSumSource": True,
            "boundary_paid_measure_lower_bound_paid_by_bounded_ratio": True,
        },
        "does_not_accept": [
            "ratio_mean_only",
            "unsourced_ratio_upper_bound",
            "ratio_upper_bound_chosen_after_payoff",
            "proxy_ratio_cap",
            "source_law_to_threshold_measure_conversion_missing",
            "sparse_high_rho_support",
        ],
    },

    "boundary_interface_rn_density_cap_source_gate": {
        "requires": {
            "bounded_boundary_interface_ratio_source": True,
            "boundary_measure_ac_wrt_interface_measure": True,
            "rn_density_upper_bound_equals_ratio_upper_bound": True,
            "no_boundary_charge_on_interface_null_set": True,
            "density_cap_sourced_before_threshold_deficit_known": True,
            "finite_energy_amplitude_cap_not_used_as_density_cap": True,
            "rho_defined_on_same_source_law": True,
            "ratio_upper_bound_fixed_before_payoff": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "BoundaryInterfaceRNDensityCapSource": True,
            "BoundedBoundaryInterfaceRatioSource": True,
        },
        "does_not_accept": [
            "finite_energy_amplitude_cap_only",
            "boundary_charge_on_interface_null_set",
            "proxy_density_cap",
            "post_payoff_density_cap",
            "pressure_visibility_as_positive_density_cap",
        ],
    },
    "boundary_share_mean_overfill_source_gate": {
        "requires": {
            "boundary_paid_high_interface_size_sum_source": True,
            "boundary_share_defined_as_B_over_BplusI_on_same_law": True,
            "boundary_share_threshold_lt_one": True,
            "boundary_share_mean_surplus_nonnegative": True,
            "lower_bound_mul_share_slack_le_mean_surplus": True,
            "share_mean_surplus_le_share_slack_mul_boundary_paid_set_measure": True,
            "lower_bound_plus_high_interface_overfills_threshold": True,
            "share_threshold_fixed_before_payoff": True,
            "source_law_measure_converts_to_threshold_measure": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "BoundaryShareMeanOverfillSource": True,
            "BoundaryPaidHighInterfaceSizeSumSource": True,
            "bounded_share_support_lower_bound_paid": True,
        },
        "does_not_accept": [
            "B_over_I_unbounded_ratio_reused",
            "mean_share_from_target_deficit",
            "low_interface_boundary_share_surplus",
            "source_law_to_threshold_measure_conversion_missing",
        ],
    },
    "boundary_singular_interface_needle_packet_gate": {
        "requires": {
            "boundary_charge_on_interface_null_or_tiny_set": True,
            "finite_energy_amplitude_cap_compatible_with_needle": True,
            "no_rn_density_cap_on_selected_law": True,
            "sparse_high_rho_support": True,
            "matching_threshold_boundary_high_interface_measures": True,
        },
        "concludes": {
            "BoundarySingularInterfaceNeedlePacket": True,
            "BoundaryInterfaceRNDensityCapSource_excluded_for_matching_measures": True,
            "BoundedBoundaryInterfaceRatioSource_excluded_for_matching_measures": True,
        },
        "does_not_accept": [
            "absolute_continuity_receipt_present",
            "uniform_density_cap_present",
            "cap_fixed_on_same_source_law",
        ],
    },

    "boundary_share_low_interface_surplus_packet_gate": {
        "requires": {
            "boundary_share_surplus_on_low_interface_set": True,
            "high_interface_companion_underfills_threshold": True,
            "share_mean_does_not_source_high_interface_intersection": True,
            "matching_threshold_boundary_high_interface_measures": True,
        },
        "concludes": {
            "BoundaryShareLowInterfaceSurplusPacket": True,
            "BoundaryShareMeanOverfillSource_excluded_for_matching_measures": True,
        },
        "does_not_accept": [
            "high_interface_intersection_receipt_present",
            "restricted_high_interface_boundary_payment_source_present",
        ],
    },

    "high_interface_conditional_share_confuser_gate": {
        "requires": {
            "conditional_high_interface_law_missing_or_target_selected": True,
            "global_boundary_share_surplus_does_not_condition_to_high_interface": True,
            "high_interface_conditional_mean_share_surplus_missing": True,
            "high_interface_floor_events_all_boundary_underpaid": True,
        },
        "concludes": {
            "HighInterfaceConditionalShareConfuser": True,
            "HighInterfaceConditionalBoundaryShareSource_excluded": True,
        },
        "does_not_accept": [
            "conditional_law_fixed_before_payoff",
            "conditional_share_mean_surplus_receipt",
            "restricted_high_interface_boundary_payment_source_present",
        ],
    },

    "high_interface_conditional_average_dominance_confuser_gate": {
        "requires": {
            "global_boundary_dominance_does_not_condition_to_high_interface": True,
            "conditional_boundary_average_dominance_missing": True,
            "signed_pressure_visibility_not_positive_boundary_payment": True,
            "high_interface_floor_events_all_boundary_underpaid": True,
        },
        "concludes": {
            "HighInterfaceConditionalAverageDominanceConfuser": True,
            "HighInterfaceConditionalAverageBoundaryDominanceSource_excluded": True,
        },
        "does_not_accept": [
            "conditional_boundary_average_dominance_receipt",
            "positive_boundary_payment_on_high_interface_law",
            "restricted_high_interface_boundary_payment_source_present",
        ],
    },

    "boundary_paid_ratio_overfill_certificate_gate": {
        "requires": {
            "boundary_interface_ratio_anti_concentration_source": True,
            "rho_defined_as_boundary_over_interface_on_source_law": True,
            "ratio_positive_part_first_moment_lower_bound": True,
            "ratio_positive_part_second_moment_cap": True,
            "source_law_measure_converts_to_threshold_measure": True,
            "ratio_overfill_not_mean_only": True,
            "no_low_interface_ratio_surplus_laundering": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "BoundaryPaidRatioOverfillCertificate": True,
            "BoundaryInterfaceRatioAntiConcentrationSource": True,
            "BoundaryPaidHighInterfaceSizeSumSource": True,
            "boundary_paid_ratio_overfill_paid": True,
        },
        "does_not_accept": [
            "rho_mean_at_least_one_only",
            "rho_spike_without_second_moment_cap",
            "source_law_to_threshold_measure_conversion_missing",
            "ratio_mass_carried_by_low_interface_surplus",
            "proxy_ratio_law",
        ],
    },

    "boundary_interface_ratio_anti_concentration_source_gate": {
        "requires": {
            "boundary_paid_high_interface_size_sum_source": True,
            "boundary_paid_measure_lower_bound_nonnegative": True,
            "ratio_first_moment_sq_nonnegative": True,
            "ratio_second_moment_cap_positive": True,
            "boundary_paid_measure_lower_bound_mul_ratio_second_moment_cap_le_first_moment_sq": True,
            "ratio_first_moment_sq_le_second_moment_cap_mul_boundary_paid_set_measure": True,
            "lower_bound_plus_high_interface_overfills_threshold": True,
            "ratio_law_bound_to_same_source_interface_law": True,
            "ratio_second_moment_cap_same_prefix": True,
            "ratio_mass_not_carried_by_low_interface_surplus": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "BoundaryInterfaceRatioAntiConcentrationSource": True,
            "BoundaryPaidHighInterfaceSizeSumSource": True,
            "boundary_paid_measure_lower_bound_paid": True,
        },
        "does_not_accept": [
            "ratio_mean_only",
            "ratio_second_moment_cap_on_proxy_law_only",
            "ratio_mass_carried_by_low_interface_surplus",
            "high_interface_boundary_ratio_below_one",
            "overfill_margin_missing",
        ],
    },

    "boundary_paid_high_interface_size_sum_source_gate": {
        "requires": {
            "restricted_high_interface_boundary_payment_source": True,
            "threshold_space_measure_nonnegative": True,
            "boundary_paid_set_measure_nonnegative": True,
            "high_interface_floor_set_measure_nonnegative": True,
            "boundary_paid_set_measure_le_threshold_space_measure": True,
            "high_interface_floor_set_measure_le_threshold_space_measure": True,
            "boundary_paid_plus_high_interface_gt_threshold_space": True,
            "disjoint_boundary_paid_high_interface_force_upper_bound": True,
            "boundary_paid_measure_from_source_law": True,
            "high_interface_floor_measure_from_source_law": True,
            "selected_event_in_boundary_paid_high_interface_intersection": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "BoundaryPaidHighInterfaceSizeSumSource": True,
            "RestrictedHighInterfaceBoundaryPaymentSource": True,
            "InterfaceWeightedBoundaryPaidFloorCorrelationSource": True,
            "boundary_paid_high_interface_intersection_paid": True,
        },
        "does_not_accept": [
            "cheap_boundary_high_interface_size_sum_only",
            "boundary_paid_measure_without_same_source_law",
            "high_interface_measure_without_floor_payment",
            "marginal_bounds_that_do_not_overfill_threshold_space",
            "low_interface_boundary_surplus",
            "finite_prefix_sum_only",
        ],
    },

    "finite_prefix_boundary_interface_selection_gate": {
        "requires": {
            "finite_prefix_interface_sum_le_boundary_sum": True,
            "positive_prefix_length": True,
            "same_source_boundary_interface_family": True,
            "prefix_fixed_before_payoff": True,
            "boundary_interface_units_aligned": True,
            "no_post_payoff_selection": True,
            "action_target_source_names_prefix_comparison": True,
            "source_contract_alignment_check_passed": True,
            "selected_interface_pays_floor": True,
            "selected_boundary_pays_interface": True,
            "selected_event_from_source_interface_law": True,
        },
        "concludes": {
            "finite_prefix_selection_event_exists": True,
            "some_boundary_event_pays_interface_event": True,
            "boundary_pays_interface_floor": True,
            "payment_biased_selection_arithmetic_paid": True,
        },
        "does_not_accept": [
            "post_payoff_prefix_choice",
            "boundary_family_not_same_as_interface_family",
            "proxy_boundary_sum",
            "proxy_interface_sum",
            "target_deficit_selected_prefix",
            "source_contract_alignment_missing",
            "zero_interface_boundary_sink",
        ],
    },
    "correlated_coarea_high_low_interface_slice_source_gate": {
        "requires": {
            "selected_interface_variation_coarea_overlap_lower_payment_source": True,
            "threshold_boundary_charge_family": True,
            "threshold_interface_payment_family": True,
            "boundary_cost_cap_nonnegative": True,
            "interface_payment_floor_nonnegative": True,
            "selected_boundary_charge_eq_coarea_collar_charge": True,
            "selected_interface_payment_eq_interface_variation_measure": True,
            "selected_threshold_boundary_cheap": True,
            "selected_threshold_interface_high": True,
            "paid_overlap_reserve_le_interface_payment_floor": True,
            "interface_payment_floor_le_selected_boundary_charge": True,
            "low_boundary_set_intersects_high_interface_set": True,
            "same_owner_root_for_boundary_and_interface_slice": True,
            "threshold_event_fixed_before_payoff": True,
            "high_low_correlation_not_post_selected": True,
        },
        "concludes": {
            "CorrelatedCoareaHighLowInterfaceSliceSource": True,
            "SelectedInterfaceVariationCoareaOverlapLowerPaymentSource": True,
            "CoareaCollarLowerPaymentToPositiveTVSource": True,
            "CoareaPositiveKernelTVMinorantSource": True,
            "paid_overlap_reserve_le_coarea_collar_charge_via_slice": True,
        },
        "does_not_accept": [
            "ordinary_coarea_average_control_only",
            "cheap_boundary_slice_without_high_interface_intersection",
            "high_interface_slice_without_boundary_cost_control",
            "post_selected_threshold_correlation",
        ],
    },
    "size_sum_correlated_coarea_high_low_slice_source_gate": {
        "requires": {
            "correlated_coarea_high_low_interface_slice_source": True,
            "threshold_space_measure_nonnegative": True,
            "low_boundary_set_measure_nonnegative": True,
            "high_interface_set_measure_nonnegative": True,
            "low_boundary_set_measure_le_threshold_space_measure": True,
            "high_interface_set_measure_le_threshold_space_measure": True,
            "low_plus_high_measure_gt_threshold_space_measure": True,
            "disjoint_high_low_sets_force_measure_upper_bound": True,
            "low_boundary_measure_from_coarea_average": True,
            "high_interface_measure_from_anti_concentration": True,
        },
        "concludes": {
            "SizeSumCorrelatedCoareaHighLowSliceSource": True,
            "CorrelatedCoareaHighLowInterfaceSliceSource": True,
            "SelectedInterfaceVariationCoareaOverlapLowerPaymentSource": True,
            "threshold_size_sum_forces_intersection": True,
        },
        "does_not_accept": [
            "low_boundary_measure_without_high_interface_measure",
            "high_interface_measure_without_low_boundary_measure",
            "marginal_bounds_that_do_not_overfill_threshold_space",
            "disjoint_sets_without_measure_upper_bound",
        ],
    },
    "markov_paley_zygmund_size_sum_coarea_source_gate": {
        "requires": {
            "size_sum_correlated_coarea_high_low_slice_source": True,
            "cheap_boundary_measure_lower_bound_nonnegative": True,
            "high_interface_measure_lower_bound_nonnegative": True,
            "cheap_boundary_measure_lower_bound_le_low_boundary_set_measure": True,
            "high_interface_measure_lower_bound_le_high_interface_set_measure": True,
            "lower_bounds_overfill_threshold_space": True,
            "cheap_boundary_lower_bound_from_markov_coarea_average": True,
            "high_interface_lower_bound_from_paley_zygmund": True,
            "interface_second_moment_receipt": True,
            "paley_zygmund_threshold_fixed_before_payoff": True,
        },
        "concludes": {
            "MarkovPaleyZygmundSizeSumCoareaSource": True,
            "SizeSumCorrelatedCoareaHighLowSliceSource": True,
            "CorrelatedCoareaHighLowInterfaceSliceSource": True,
            "lower_bounds_force_threshold_size_sum_surplus": True,
        },
        "does_not_accept": [
            "markov_cheap_boundary_only",
            "paley_zygmund_without_second_moment_receipt",
            "lower_bounds_without_strict_surplus",
            "threshold_chosen_after_payoff",
        ],
    },
    "high_interface_second_moment_known_basin_boundary_gate": {
        "requires": {
            "paley_zygmund_high_interface_debt_packet": True,
            "borrowed_selected_tent_anti_concentration_label": True,
            "same_threshold_family_second_moment_missing": True,
            "strict_tail_or_sparse_high_high_basin_recurrence": True,
            "not_a_new_coarea_interface_second_moment_receipt": True,
        },
        "concludes": {
            "HighInterfaceSecondMomentKnownBasinBoundary": True,
            "MarkovPaleyZygmundSizeSumCoareaSource_excluded_for_matching_measures": True,
            "same_threshold_second_moment_required_not_old_basin_label": True,
        },
        "does_not_accept": [
            "borrowed_strict_tail_gate_as_new_coarea_receipt",
            "selected_tent_anti_concentration_without_threshold_identity",
            "sparse_high_high_ghost_rediscovery",
        ],
    },
    "fixed_profile_threshold_interface_amplitude_cap_source_gate": {
        "requires": {
            "size_sum_correlated_coarea_high_low_slice_source": True,
            "cheap_boundary_measure_lower_bound_nonnegative": True,
            "high_interface_measure_lower_bound_nonnegative": True,
            "cheap_boundary_measure_lower_bound_le_low_boundary_set_measure": True,
            "lower_bounds_overfill_threshold_space": True,
            "interface_first_moment_lower_bound_nonnegative": True,
            "interface_amplitude_cap_positive": True,
            "interface_first_moment_lower_bound_le_interface_first_moment": True,
            "high_interface_lower_bound_mul_cap_le_first_moment_lower_bound": True,
            "threshold_interface_payment_le_cap_mul_support_weight": True,
            "interface_first_moment_le_prefix_interface_payment": True,
            "high_interface_set_measure_eq_prefix_support_weight": True,
            "cheap_boundary_lower_bound_from_markov_coarea_average": True,
            "high_interface_lower_bound_from_amplitude_cap": True,
            "fixed_profile_amplitude_cap_from_angular_collar": True,
            "same_threshold_family_as_coarea_interface_payment": True,
            "amplitude_cap_fixed_before_payoff": True,
            "pointwise_cap_not_proxy_threshold_family": True,
            "not_layer_cake_first_moment_only": True,
            "interface_second_moment_receipt_from_amplitude_cap": True,
        },
        "concludes": {
            "FixedProfileThresholdInterfaceAmplitudeCapSource": True,
            "FixedProfileAmplitudeCapAntiSpikeSizeSumSource": True,
            "prefix_sum_pointwise_cap_forces_first_moment_cap": True,
            "same_threshold_amplitude_cap_source_paid": True,
        },
        "does_not_accept": [
            "fixed_profile_label_without_pointwise_bound",
            "amplitude_cap_on_proxy_threshold_family",
            "interface_first_moment_without_prefix_payment",
            "support_measure_not_same_prefix",
            "post_payoff_cap_choice",
        ],
    },
    "same_prefix_interface_second_moment_cap_size_sum_source_gate": {
        "requires": {
            "size_sum_correlated_coarea_high_low_slice_source": True,
            "cheap_boundary_measure_lower_bound_nonnegative": True,
            "high_interface_measure_lower_bound_nonnegative": True,
            "cheap_boundary_measure_lower_bound_le_low_boundary_set_measure": True,
            "lower_bounds_overfill_threshold_space": True,
            "interface_first_moment_lower_bound_nonnegative": True,
            "interface_second_moment_cap_positive": True,
            "interface_first_moment_lower_bound_le_interface_first_moment": True,
            "high_interface_lower_bound_mul_second_moment_cap_le_first_moment_sq": True,
            "first_moment_sq_le_second_moment_cap_mul_high_interface_set_measure": True,
            "cheap_boundary_lower_bound_from_markov_coarea_average": True,
            "high_interface_lower_bound_from_second_moment_cap": True,
            "same_prefix_second_moment_cap_on_coarea_interface_threshold_family": True,
            "same_threshold_family_as_coarea_interface_payment": True,
            "second_moment_cap_fixed_before_payoff": True,
            "not_global_or_proxy_energy_second_moment": True,
            "not_layer_cake_first_moment_only": True,
        },
        "concludes": {
            "SamePrefixInterfaceSecondMomentCapSizeSumSource": True,
            "MarkovPaleyZygmundSizeSumCoareaSource": True,
            "same_prefix_second_moment_cap_forces_high_interface_support": True,
            "same_threshold_anti_spike_receipt_from_second_moment_cap": True,
        },
        "does_not_accept": [
            "global_l2_energy_as_same_prefix_second_moment",
            "proxy_carrier_second_moment_cap",
            "post_payoff_second_moment_cap_choice",
            "first_moment_only_layer_cake_as_second_moment",
            "old_selected_tent_anti_concentration_label",
        ],
    },
    "proxy_second_moment_cap_not_same_prefix_packet_gate": {
        "requires": {
            "second_moment_cap_available_on_proxy_carrier": True,
            "same_prefix_identity_between_proxy_and_threshold_family_missing": True,
            "prefix_support_measure_identity_missing": True,
            "post_projection_or_global_energy_billed_as_local_cap": True,
        },
        "concludes": {
            "ProxySecondMomentCapNotSamePrefixPacket": True,
            "SamePrefixInterfaceSecondMomentCapSizeSumSource_excluded_for_matching_measures": True,
            "same_prefix_second_moment_cap_required_not_proxy_energy": True,
        },
        "does_not_accept": [
            "global_l2_energy_bound",
            "proxy_second_moment_without_prefix_identity",
            "post_projection_second_moment_bound",
            "energy_enstrophy_budget_without_threshold_carrier_identity",
        ],
    },
    "same_prefix_quadratic_coarea_energy_cap_source_gate": {
        "requires": {
            "same_prefix_interface_second_moment_cap_size_sum_source": True,
            "threshold_interface_payment_family": True,
            "selected_quadratic_prefix_length_fixed": True,
            "prefix_second_moment_cap_eq_interface_second_moment_cap": True,
            "threshold_interface_second_moment_prefix_le_cap": True,
            "quadratic_coarea_energy_cap_on_same_threshold_family": True,
            "quadratic_cap_fixed_before_payoff": True,
            "quadratic_cap_not_linear_owner_budget_only": True,
        },
        "concludes": {
            "SamePrefixQuadraticCoareaEnergyCapSource": True,
            "SamePrefixInterfaceSecondMomentCapSizeSumSource": True,
            "MarkovPaleyZygmundSizeSumCoareaSource": True,
            "quadratic_coarea_energy_cap_supplies_anti_spike_receipt": True,
        },
        "does_not_accept": [
            "linear_owner_budget_as_quadratic_cap",
            "global_energy_without_threshold_prefix_identity",
            "proxy_quadratic_energy_cap",
            "post_payoff_quadratic_prefix_choice",
            "threshold_interface_payment_family_label_only",
        ],
    },
    "owner_prefix_first_moment_budget_no_second_moment_cap_packet_gate": {
        "requires": {
            "interface_second_moment_concentration_spike_packet": True,
            "owner_prefix_first_moment_budget_available": True,
            "owner_root_budget_controls_linear_interface_charge": True,
            "threshold_spike_keeps_linear_charge_within_owner_budget": True,
            "quadratic_owner_budget_or_second_moment_cap_missing": True,
            "linear_budget_not_same_prefix_quadratic_cap": True,
        },
        "concludes": {
            "OwnerPrefixFirstMomentBudgetNoSecondMomentCapPacket": True,
            "SamePrefixInterfaceSecondMomentCapSizeSumSource_excluded_for_matching_measures": True,
            "owner_first_moment_budget_not_second_moment_cap": True,
        },
        "does_not_accept": [
            "owner_root_budget_as_second_moment_cap",
            "linear_coarea_charge_as_quadratic_threshold_moment",
            "first_moment_owner_budget_without_quadratic_budget",
            "selected_prefix_budget_label_without_second_moment_receipt",
        ],
    },
    "fixed_profile_amplitude_cap_anti_spike_size_sum_source_gate": {
        "requires": {
            "size_sum_correlated_coarea_high_low_slice_source": True,
            "cheap_boundary_measure_lower_bound_nonnegative": True,
            "high_interface_measure_lower_bound_nonnegative": True,
            "cheap_boundary_measure_lower_bound_le_low_boundary_set_measure": True,
            "lower_bounds_overfill_threshold_space": True,
            "interface_first_moment_lower_bound_nonnegative": True,
            "interface_amplitude_cap_positive": True,
            "interface_first_moment_lower_bound_le_interface_first_moment": True,
            "interface_first_moment_le_cap_mul_high_interface_set_measure": True,
            "high_interface_lower_bound_mul_cap_le_first_moment_lower_bound": True,
            "cheap_boundary_lower_bound_from_markov_coarea_average": True,
            "high_interface_lower_bound_from_amplitude_cap": True,
            "fixed_profile_amplitude_cap_from_angular_collar": True,
            "same_threshold_family_as_coarea_interface_payment": True,
            "amplitude_cap_fixed_before_payoff": True,
            "not_layer_cake_first_moment_only": True,
            "interface_second_moment_receipt_from_amplitude_cap": True,
        },
        "concludes": {
            "FixedProfileAmplitudeCapAntiSpikeSizeSumSource": True,
            "MarkovPaleyZygmundSizeSumCoareaSource": True,
            "fixed_profile_amplitude_cap_forces_high_interface_support": True,
            "same_threshold_anti_spike_receipt_from_amplitude_cap": True,
        },
        "does_not_accept": [
            "layer_cake_first_moment_as_support_bound",
            "positive_interface_mass_without_amplitude_cap",
            "amplitude_cap_on_proxy_threshold_family",
            "amplitude_cap_chosen_after_payoff",
            "fixed_profile_label_without_numeric_cap",
        ],
    },
    "fixed_profile_weight_only_no_amplitude_cap_packet_gate": {
        "requires": {
            "fixed_profile_amplitude_cap_missing_spike_packet": True,
            "fixed_angular_profile_weight_bound_available": True,
            "physical_interface_amplitude_unbounded_on_selected_prefix": True,
            "cutoff_weight_bound_does_not_bound_strain_amplitude": True,
            "pointwise_threshold_interface_payment_cap_missing": True,
        },
        "concludes": {
            "FixedProfileWeightOnlyNoAmplitudeCapPacket": True,
            "FixedProfileThresholdInterfaceAmplitudeCapSource_excluded_for_matching_measures": True,
            "physical_amplitude_cap_required_not_profile_weight_only": True,
        },
        "does_not_accept": [
            "fixed_profile_weight_bound_as_interface_amplitude_cap",
            "cutoff_derivative_bound_without_strain_amplitude_bound",
            "angular_profile_linf_without_physical_payment_cap",
        ],
    },
    "fixed_profile_amplitude_cap_missing_spike_packet_gate": {
        "requires": {
            "interface_second_moment_concentration_spike_packet": True,
            "fixed_profile_amplitude_cap_missing": True,
            "amplitude_cap_proxy_billed_or_post_payoff": True,
            "layer_cake_first_moment_misread_as_amplitude_cap": True,
        },
        "concludes": {
            "FixedProfileAmplitudeCapMissingSpikePacket": True,
            "FixedProfileAmplitudeCapAntiSpikeSizeSumSource_excluded_for_matching_measures": True,
            "fixed_profile_amplitude_cap_required": True,
        },
        "does_not_accept": [
            "layer_cake_first_moment_available",
            "same_threshold_family_label_only",
            "amplitude_cap_without_numeric_bound",
            "old_selected_tent_anti_concentration_label",
        ],
    },
    "interface_second_moment_concentration_spike_packet_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "threshold_support_measure_nonnegative": True,
            "interface_first_moment_eq_support_mul_amplitude": True,
            "interface_second_moment_eq_support_mul_amplitude_sq": True,
            "low_plus_high_measure_le_threshold_space_measure": True,
            "cheap_boundary_lower_bound_available": True,
            "layer_cake_first_moment_available": True,
            "interface_second_moment_too_large_for_pz": True,
            "high_interface_anti_concentration_missing": True,
        },
        "concludes": {
            "InterfaceSecondMomentConcentrationSpikePacket": True,
            "MarkovPaleyZygmundSizeSumCoareaSource_excluded_for_matching_measures": True,
            "threshold_spike_second_moment_identity": True,
            "same_threshold_anti_spike_receipt_required": True,
        },
        "does_not_accept": [
            "layer_cake_first_moment_as_pz_receipt",
            "positive_interface_mass_without_second_moment_ceiling",
            "high_interface_support_label_without_measure_lower_bound",
        ],
    },
    "paley_zygmund_high_interface_debt_packet_gate": {
        "requires": {
            "high_low_size_sum_intersection_debt_packet": True,
            "cheap_boundary_lower_bound_available": True,
            "high_interface_anti_concentration_missing": True,
            "interface_second_moment_receipt_missing": True,
        },
        "concludes": {
            "PaleyZygmundHighInterfaceDebtPacket": True,
            "MarkovPaleyZygmundSizeSumCoareaSource_excluded_for_matching_measures": True,
            "high_interface_second_moment_receipt_required": True,
        },
        "does_not_accept": [
            "generic_anti_concentration_label",
            "layer_cake_tail_identity_without_second_moment",
            "cheap_boundary_markov_bound_only",
        ],
    },
    "high_low_size_sum_intersection_debt_packet_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "low_plus_high_measure_le_threshold_space_measure": True,
            "positive_correlation_or_size_sum_receipt_missing": True,
        },
        "concludes": {
            "HighLowSizeSumIntersectionDebtPacket": True,
            "SizeSumCorrelatedCoareaHighLowSliceSource_excluded_for_matching_measures": True,
            "size_sum_or_correlation_receipt_required": True,
        },
        "does_not_accept": [
            "paley_zygmund_high_set_only",
            "markov_low_set_only",
            "one_marginal_measure_bound",
        ],
    },
    "quadratic_ratio_size_sum_surplus_certificate_gate": {
        "requires": {
            "same_prefix_quadratic_coarea_energy_cap_source": True,
            "quadratic_ratio_pays_threshold_deficit": True,
            "ratio_lower_bound_mul_cap_le_first_moment_sq": True,
            "ratio_lower_bound_creates_overfill": True,
            "ratio_certificate_on_same_prefix": True,
            "not_just_finite_quadratic_cap": True,
        },
        "concludes": {
            "QuadraticRatioSizeSumSurplusCertificate": True,
            "SamePrefixQuadraticCoareaEnergyCapSource": True,
            "MarkovPaleyZygmundSizeSumCoareaSource": True,
            "m2_over_q_size_sum_surplus_paid": True,
        },
        "does_not_accept": [
            "finite_quadratic_cap_without_ratio",
            "m2_over_q_on_proxy_prefix",
            "cheap_boundary_deficit_unpaid",
            "ratio_chosen_after_payoff",
        ],
    },
    "quadratic_cap_too_large_no_size_sum_surplus_packet_gate": {
        "requires": {
            "paley_zygmund_high_interface_debt_packet": True,
            "finite_same_prefix_quadratic_cap_available": True,
            "high_interface_lower_bound_from_quadratic_cap_too_small": True,
            "cheap_plus_quadratic_cap_lower_bound_no_overfill": True,
            "strict_size_sum_surplus_missing": True,
        },
        "concludes": {
            "QuadraticCapTooLargeNoSizeSumSurplusPacket": True,
            "SamePrefixQuadraticCoareaEnergyCapSource_excluded_for_matching_measures": True,
            "finite_quadratic_cap_not_enough_without_surplus": True,
        },
        "does_not_accept": [
            "finite_second_moment_cap_as_size_sum_surplus",
            "quadratic_cap_without_m2_over_q_lower_bound",
            "cheap_boundary_plus_tiny_high_interface_lower_bound",
            "same_prefix_quadratic_cap_label_without_overfill",
        ],
    },
    "coarea_low_slice_high_overlap_disjoint_packet_gate": {
        "requires": {
            "coarea_low_slice_interface_underpayment_packet": True,
            "low_boundary_set": True,
            "high_interface_set": True,
            "threshold_space_nonempty": True,
            "cheap_boundary_and_high_interface_sets_disjoint": True,
            "selected_threshold_in_low_boundary_set": True,
            "high_interface_set_avoids_selected_threshold": True,
            "rearranged_anticorrelation_witness": True,
        },
        "concludes": {
            "CoareaLowSliceHighOverlapDisjointPacket": True,
            "CorrelatedCoareaHighLowInterfaceSliceSource_excluded_for_same_data": True,
            "high_low_intersection_receipt_required": True,
        },
        "does_not_accept": [
            "one_marginal_coarea_bound",
            "layer_cake_without_intersection",
            "paley_zygmund_without_cheap_boundary_overlap",
            "same_owner_labels_without_correlation",
        ],
    },
    "coarea_low_slice_interface_underpayment_packet_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "selected_extensional_interface_variation_available": True,
            "coarea_slice_chosen_for_low_boundary_invoice": True,
            "interface_variation_same_owner_but_not_slice_dominated": True,
            "coarea_collar_charge_lt_interface_variation_measure": True,
        },
        "concludes": {
            "CoareaLowSliceInterfaceUnderpaymentPacket": True,
            "SelectedInterfaceVariationCoareaOverlapLowerPaymentSource_excluded_for_same_data": True,
            "high_low_correlated_coarea_slice_required": True,
        },
        "does_not_accept": [
            "ordinary_coarea_low_slice_as_overlap_payment",
            "coarea_average_control_as_lower_bound",
            "interface_variation_integral_paid_by_one_small_threshold",
        ],
    },
    "interface_variation_coarea_overlap_unlinked_packet_gate": {
        "requires": {
            "coarea_collar_paid_but_overlap_underpaid_packet": True,
            "selected_section_extensional_interface_variation_measure_available": True,
            "selected_absolute_variation_eq_interface_variation_measure": True,
            "interface_variation_measure_constructed_from_cutoff_formula": True,
            "interface_variation_not_mapped_to_same_coarea_collar_event": True,
            "selected_interface_variation_does_not_pay_overlap_reserve": True,
        },
        "concludes": {
            "InterfaceVariationCoareaOverlapUnlinkedPacket": True,
            "SelectedInterfaceVariationCoareaOverlapLowerPaymentSource_excluded_for_same_data": True,
            "interface_to_coarea_domination_receipt_required": True,
        },
        "does_not_accept": [
            "extensional_interface_variation_as_automatic_overlap_lower_bound",
            "selected_section_identity_without_collar_event_map",
            "cutoff_formula_without_overlap_reserve_domination",
        ],
    },
    "coarea_collar_lower_payment_to_positive_tv_source_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "paid_overlap_reserve_nonnegative": True,
            "positive_kernel_tv_coupling_mass_nonnegative": True,
            "localized_schur_owner_charge_nonnegative": True,
            "paid_overlap_reserve_le_coarea_collar_charge": True,
            "coarea_collar_charge_le_positive_kernel_tv_coupling_mass": True,
            "positive_kernel_tv_coupling_mass_le_localized_schur_owner_charge": True,
            "localized_schur_owner_charge_le_owner_root_budget": True,
            "coarea_lower_payment_declared_before_projection_step_lt_projected_payoff_step": True,
            "coarea_lower_payment_declared_before_payoff_step_lt_projected_payoff_step": True,
            "coarea_collar_maps_to_positive_tv_minorant": True,
            "coarea_collar_payment_disjoint_from_prior_invoices": True,
            "coarea_collar_lower_payment_not_defined_from_projected_deficit": True,
            "signed_pressure_riesz_cancellation_excluded": True,
            "localized_tv_row_column_schur_bound": True,
            "cutoff_boundary_invoice_paid_by_same_owner": True,
            "pressure_leray_tail_leakage_paid_or_excluded": True,
            "cross_owner_tv_edges_excluded_or_separately_paid": True,
        },
        "concludes": {
            "CoareaCollarLowerPaymentToPositiveTVSource": True,
            "CoareaPositiveKernelTVMinorantSource": True,
            "PositiveLocalizedKernelTVCouplingSource": True,
            "PrePayoffOverlapPreimageSource": True,
            "paid_overlap_reserve_le_owner_root_budget": True,
        },
        "does_not_accept": [
            "paid_coarea_collar_without_overlap_lower_bound",
            "coarea_collar_upper_budget_only",
            "implicit_timing_inherited_from_downstream_source",
        ],
    },
    "coarea_collar_paid_but_overlap_underpaid_packet_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "owner_preimage_coarea_collar_charge_paid": True,
            "coarea_collar_charge_maps_to_owner_budget": True,
            "overlap_reserve_lower_bound_missing": True,
            "coarea_collar_charge_lt_paid_overlap_reserve": True,
        },
        "concludes": {
            "CoareaCollarPaidButOverlapUnderpaidPacket": True,
            "CoareaCollarLowerPaymentToPositiveTVSource_excluded_for_same_data": True,
            "overlap_lower_bound_receipt_required": True,
        },
        "does_not_accept": [
            "coarea_owner_preimage_as_overlap_lower_bound",
            "paid_collar_charge_as_automatic_paid_overlap_reserve",
        ],
    },
    "coarea_positive_kernel_tv_minorant_source_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "paid_overlap_reserve_nonnegative": True,
            "coarea_lower_payment_mass_nonnegative": True,
            "positive_kernel_tv_coupling_mass_nonnegative": True,
            "localized_schur_owner_charge_nonnegative": True,
            "paid_overlap_reserve_le_coarea_lower_payment_mass": True,
            "coarea_lower_payment_mass_le_positive_kernel_tv_coupling_mass": True,
            "positive_kernel_tv_coupling_mass_le_localized_schur_owner_charge": True,
            "localized_schur_owner_charge_le_owner_root_budget": True,
            "same_owner_coarea_source_budget_le_owner_root_budget": True,
            "no_reuse_coarea_lower_payment_mass_le_owner_root_budget": True,
            "coarea_payment_declared_before_projection_step_lt_projected_payoff_step": True,
            "coarea_payment_declared_before_payoff_step_lt_projected_payoff_step": True,
            "nonadaptive_coarea_threshold_fixed_before_payoff": True,
            "coarea_event_carries_positive_lower_payment": True,
            "coarea_lower_payment_maps_to_positive_tv_minorant": True,
            "coarea_payment_same_owner_root": True,
            "coarea_payment_disjoint_from_prior_invoices": True,
            "coarea_payment_not_defined_from_projected_deficit": True,
            "signed_pressure_riesz_cancellation_excluded": True,
            "localized_tv_row_column_schur_bound": True,
            "cutoff_boundary_invoice_paid_by_same_owner": True,
            "pressure_leray_tail_leakage_paid_or_excluded": True,
            "cross_owner_tv_edges_excluded_or_separately_paid": True,
        },
        "concludes": {
            "CoareaPositiveKernelTVMinorantSource": True,
            "PositiveLocalizedKernelTVCouplingSource": True,
            "SameOwnerLocalizedSchurTransportSource": True,
            "PrePayoffOverlapPreimageSource": True,
            "paid_overlap_reserve_le_owner_root_budget": True,
        },
        "does_not_accept": [
            "coarea_threshold_upper_control_only",
            "local_energy_upper_budget_as_lower_payment",
            "post_payoff_threshold_selection",
            "collar_cost_control_without_positive_event",
        ],
    },
    "coarea_upper_only_no_positive_minorant_packet_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "nonadaptive_coarea_threshold_selected": True,
            "local_energy_or_coarea_upper_control_available": True,
            "coarea_lower_payment_missing": True,
            "positive_tv_minorant_missing_before_projection": True,
            "owner_root_budget_lt_paid_overlap_reserve": True,
        },
        "concludes": {
            "CoareaUpperOnlyNoPositiveMinorantPacket": True,
            "CoareaPositiveKernelTVMinorantSource_excluded_for_same_data": True,
            "PrePayoffOverlapPreimageSource_excluded_for_same_data": True,
            "coarea_lower_payment_required": True,
        },
        "does_not_accept": [
            "threshold_selected_but_no_lower_payment",
            "controlled_boundary_cost_as_positive_reserve",
            "local_energy_upper_control_as_overlap_payment",
        ],
    },
    "positive_localized_kernel_tv_coupling_source_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "paid_overlap_reserve_nonnegative": True,
            "positive_kernel_tv_coupling_mass_nonnegative": True,
            "localized_schur_owner_charge_nonnegative": True,
            "paid_overlap_reserve_le_positive_kernel_tv_coupling_mass": True,
            "positive_kernel_tv_coupling_mass_le_localized_schur_owner_charge": True,
            "localized_schur_owner_charge_le_owner_root_budget": True,
            "same_owner_positive_tv_budget_le_owner_root_budget": True,
            "no_reuse_positive_kernel_tv_coupling_mass_le_owner_root_budget": True,
            "positive_tv_coupling_declared_before_projection_step_lt_projected_payoff_step": True,
            "positive_tv_coupling_declared_before_payoff_step_lt_projected_payoff_step": True,
            "positive_tv_minorant_fixed_before_payoff": True,
            "signed_pressure_riesz_cancellation_excluded": True,
            "localized_tv_row_column_schur_bound": True,
            "cutoff_boundary_invoice_paid_by_same_owner": True,
            "pressure_leray_tail_leakage_paid_or_excluded": True,
            "cross_owner_tv_edges_excluded_or_separately_paid": True,
            "positive_tv_coupling_same_owner_root": True,
            "positive_tv_coupling_not_defined_from_projected_deficit": True,
        },
        "concludes": {
            "PositiveLocalizedKernelTVCouplingSource": True,
            "SameOwnerLocalizedSchurTransportSource": True,
            "OwnerRootCapacitatedTransportCouplingSource": True,
            "PrePayoffOverlapPreimageSource": True,
            "paid_overlap_reserve_le_owner_root_budget": True,
        },
        "does_not_accept": [
            "signed_pressure_or_riesz_moment_only",
            "absolute_kernel_size_without_positive_tv_minorant",
            "core_sheath_cancellation_unexcluded",
            "tangential_div_div_null_stress_visible_pressure_only",
        ],
    },
    "signed_pressure_no_positive_tv_minorant_packet_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "signed_pressure_or_riesz_moment_visible": True,
            "signed_moment_not_positive_measure": True,
            "core_sheath_or_tangential_null_stress_cancellation": True,
            "positive_tv_minorant_missing_before_payoff": True,
            "owner_root_budget_lt_paid_overlap_reserve": True,
        },
        "concludes": {
            "SignedPressureNoPositiveTVMinorantPacket": True,
            "PositiveLocalizedKernelTVCouplingSource_excluded_for_same_data": True,
            "PrePayoffOverlapPreimageSource_excluded_for_same_data": True,
            "positive_tv_minorant_required": True,
        },
        "does_not_accept": [
            "pressure_visibility_as_positive_payment",
            "signed_riesz_moment_as_total_variation",
            "cancellation_blind_kernel_transport",
        ],
    },
    "same_owner_localized_schur_transport_source_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "paid_overlap_reserve_nonnegative": True,
            "kernel_coupling_mass_nonnegative": True,
            "schur_owner_charge_nonnegative": True,
            "paid_overlap_reserve_le_kernel_coupling_mass": True,
            "kernel_coupling_mass_le_schur_owner_charge": True,
            "schur_owner_charge_le_owner_root_budget": True,
            "same_owner_kernel_source_budget_le_owner_root_budget": True,
            "no_reuse_kernel_coupling_mass_le_owner_root_budget": True,
            "schur_coupling_declared_before_projection_step_lt_projected_payoff_step": True,
            "schur_coupling_declared_before_payoff_step_lt_projected_payoff_step": True,
            "localized_absolute_kernel_majorant_fixed_before_payoff": True,
            "same_owner_localized_row_column_schur_bound": True,
            "cutoff_boundary_invoice_paid_by_same_owner": True,
            "pressure_leray_tail_leakage_paid_or_excluded": True,
            "cross_owner_edges_excluded_or_separately_paid": True,
            "schur_coupling_not_global_l1_only": True,
            "schur_coupling_same_owner_root": True,
            "schur_coupling_not_defined_from_projected_deficit": True,
        },
        "concludes": {
            "SameOwnerLocalizedSchurTransportSource": True,
            "OwnerRootCapacitatedTransportCouplingSource": True,
            "PrePayoffOverlapPreimageSource": True,
            "paid_overlap_reserve_le_owner_root_budget": True,
        },
        "does_not_accept": [
            "global_annular_l1_bound_only",
            "cross_owner_tail_unpaid",
            "cutoff_boundary_invoice_unpaid",
            "signed_riesz_cancellation_as_positive_coupling",
        ],
    },
    "cross_owner_schur_leakage_packet_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "global_annular_l1_schur_bound_available": True,
            "cross_owner_kernel_tail_contributes_to_selected_overlap": True,
            "same_owner_localized_schur_bound_missing": True,
            "cutoff_boundary_invoice_unpaid": True,
            "pressure_leray_tail_leakage_unpaid": True,
            "owner_root_budget_lt_paid_overlap_reserve": True,
        },
        "concludes": {
            "CrossOwnerSchurLeakagePacket": True,
            "SameOwnerLocalizedSchurTransportSource_excluded_for_same_data": True,
            "PrePayoffOverlapPreimageSource_excluded_for_same_data": True,
            "same_owner_localized_schur_receipt_required": True,
        },
        "does_not_accept": [
            "global_schur_as_same_owner_source",
            "kernel_tail_without_owner_transfer_invoice",
            "pressure_visibility_as_positive_source_measure",
        ],
    },
    "owner_root_capacitated_transport_coupling_source_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "paid_overlap_reserve_nonnegative": True,
            "transport_coupling_mass_nonnegative": True,
            "sparse_owner_charge_nonnegative": True,
            "paid_overlap_reserve_le_transport_coupling_mass": True,
            "transport_coupling_mass_le_sparse_owner_charge": True,
            "sparse_owner_charge_le_owner_root_budget": True,
            "same_owner_source_binding_budget_le_owner_root_budget": True,
            "source_overlap_disjoint_numeric_reserve_le_owner_root_budget": True,
            "no_reuse_transport_coupling_mass_le_owner_root_budget": True,
            "transport_coupling_declared_before_projection_step_lt_projected_payoff_step": True,
            "transport_coupling_declared_before_payoff_step_lt_projected_payoff_step": True,
            "coupling_supported_on_kernel_relation": True,
            "coupling_marginals_dominated_by_owner_root_capacities": True,
            "hall_cut_capacity_condition_pays_coupling_mass": True,
            "discarded_pairs_uncharged_or_separately_paid": True,
            "coupling_not_all_edge_pair_sum": True,
            "coupling_same_owner_root": True,
            "coupling_not_defined_from_projected_deficit": True,
        },
        "concludes": {
            "OwnerRootCapacitatedTransportCouplingSource": True,
            "PrePayoffOverlapPreimageSource": True,
            "paid_overlap_reserve_le_owner_root_budget": True,
        },
        "does_not_accept": [
            "all_edge_pair_sum_as_coupling_mass",
            "kernel_relation_support_as_owner_payment",
            "complete_bipartite_support_without_hall_capacity",
            "discarded_pairs_unpaid_but_counted",
        ],
    },
    "capacitated_transport_hall_defect_packet_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "requested_coupling_mass_nonnegative": True,
            "paid_overlap_reserve_le_requested_coupling_mass": True,
            "kernel_relation_support_available": True,
            "hall_cut_capacity_defect": True,
            "no_marginal_dominated_coupling_of_requested_mass": True,
            "complete_bipartite_support_not_a_coupling_receipt": True,
            "owner_root_budget_lt_paid_overlap_reserve": True,
        },
        "concludes": {
            "CapacitatedTransportHallDefectPacket": True,
            "OwnerRootCapacitatedTransportCouplingSource_excluded_for_same_data": True,
            "PrePayoffOverlapPreimageSource_excluded_for_same_data": True,
            "hall_or_max_flow_capacity_receipt_required": True,
        },
        "does_not_accept": [
            "relation_support_only",
            "complete_bipartite_support_as_feasible_flow",
            "same_owner_label_without_cut_capacity",
        ],
    },
    "complete_bipartite_kernel_pair_multiplicity_packet_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "pair_multiplicity_charge_nonnegative": True,
            "paid_overlap_reserve_le_pair_multiplicity_charge": True,
            "complete_bipartite_pairing_before_projection": True,
            "owner_root_aligned_sparse_selection_missing": True,
            "pair_multiplicity_not_bounded_by_owner_atoms": True,
            "owner_root_budget_lt_paid_overlap_reserve": True,
        },
        "concludes": {
            "CompleteBipartiteKernelPairMultiplicityPacket": True,
            "PrePayoffOverlapPreimageSource_excluded_for_same_data": True,
            "owner_root_aligned_sparse_selection_required": True,
        },
        "does_not_accept": [
            "ambient_sparse_domination_without_owner_alignment",
            "pair_count_hidden_as_linear_owner_charge",
            "annular_geometry_as_uniform_multiplicity",
        ],
    },
    "kernel_relation_not_owner_preimage_packet_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "kernel_relation_charge_nonnegative": True,
            "paid_overlap_reserve_le_kernel_relation_charge": True,
            "kernel_relation_charge_is_pair_currency": True,
            "pair_to_owner_sparse_domination_missing": True,
            "pair_multiplicity_can_exceed_owner_budget": True,
            "owner_root_budget_lt_paid_overlap_reserve": True,
        },
        "concludes": {
            "KernelRelationNotOwnerPreimagePacket": True,
            "PrePayoffOverlapPreimageSource_excluded_for_same_data": True,
            "kernel_relation_sparse_domination_required": True,
        },
        "does_not_accept": [
            "pair_charge_treated_as_owner_measure",
            "schur_bound_as_carleson_packing",
            "multiplicity_hidden_in_owner_atom",
        ],
    },
    "annular_kernel_l1_overlap_preimage_gap_packet_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "annular_riesz_kernel_has_uniform_l1_norm": True,
            "annular_kernel_sizes_projected_overlap": True,
            "source_overlap_preimage_missing_before_projection": True,
            "source_overlap_preimage_deadline_step_lt_projected_overlap_observed_step": True,
            "same_owner_preimage_missing_budget_gap": True,
            "no_reuse_overlap_reserve_missing_budget_gap": True,
            "not_defined_from_payoff_violation": True,
            "overlap_reserve_defined_from_projected_deficit": True,
            "owner_root_budget_lt_paid_overlap_reserve": True,
        },
        "concludes": {
            "AnnularKernelL1OverlapPreimageGapPacket": True,
            "PrePayoffOverlapPreimageSource_excluded_for_same_data": True,
            "annular_l1_sizes_but_does_not_source_overlap_preimage": True,
        },
        "does_not_accept": [
            "bandlimited_l1_bound_as_source_preimage",
            "projected_overlap_without_prepayoff_owner_map",
            "kernel_smoothing_as_payment",
        ],
    },
    "post_projection_overlap_only_packet_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "projected_window_creates_overlap": True,
            "source_overlap_preimage_missing_before_projection": True,
            "overlap_reserve_defined_from_projected_deficit": True,
            "owner_root_budget_lt_paid_overlap_reserve": True,
        },
        "concludes": {
            "PostProjectionOverlapOnlyPacket": True,
            "PrePayoffOverlapPreimageSource_excluded_for_same_data": True,
            "pre_payoff_overlap_preimage_required": True,
        },
        "does_not_accept": [
            "annular_kernel_smoothing_as_payment",
            "projected_overlap_without_source_preimage",
            "post_payoff_overlap_reserve",
        ],
    },
    "paid_nonzero_overlap_reserve_underpaid_packet_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "existing_collar_reserve_spend_nonnegative": True,
            "assignment_overlap_reserve_positive": True,
            "finite_assignment_before_projection": True,
            "projected_window_reintroduces_overlap": True,
            "paid_overlap_reserve_missing": True,
            "overlap_reserve_defined_after_payoff": True,
            "overlap_reserve_not_on_same_owner_root_preimage": True,
            "owner_root_budget_lt_tail_plus_existing_reserve": True,
        },
        "concludes": {
            "PaidNonzeroOverlapReserveUnderpaidPacket": True,
            "FiniteProjectedWindowPaidNonzeroOverlapReserveSource_excluded_for_same_data": True,
            "paid_nonzero_overlap_reserve_required": True,
        },
        "does_not_accept": [
            "positive_overlap_named_without_payment",
            "overlap_reserve_post_payoff",
            "overlap_reserve_from_ambient_total_invoice",
        ],
    },
    "unpaid_projected_overlap_reserve_packet_gate": {
        "requires": {
            "preprojection_projected_collar_exchange_source": True,
            "existing_collar_reserve_spend_nonnegative": True,
            "projected_window_overlap_present": True,
            "paid_projected_overlap_reserve_missing": True,
            "overlap_reserve_would_need_same_owner_root": True,
            "overlap_reserve_would_need_pre_projection_timing": True,
            "owner_root_budget_lt_projected_payment": True,
        },
        "concludes": {
            "UnpaidProjectedOverlapReservePacket": True,
            "PaidOverlapProjectedWindowAssignmentSource_excluded_for_same_data": True,
            "paid_overlap_reserve_required": True,
        },
        "does_not_accept": [
            "overlap_named_without_owner_root_gap",
            "late_overlap_reserve_after_projection",
            "paid_overlap_from_ambient_total_invoice",
        ],
    },
    "section_fixed_absolute_interface_variation_payment_source_gate": {
        "requires": {
            "localized_affine_euler_core_high_pi_interface_payment_source": True,
            "absolute_interface_variation_nonnegative": True,
            "absolute_interface_variation_fixed_before_payoff": True,
            "absolute_interface_variation_on_same_selected_owner_prefix": True,
            "reynolds_excess_le_absolute_interface_variation": True,
            "absolute_interface_variation_le_transport_cutoff_commutator_coefficient": True,
            "no_positive_part_chosen_after_payoff": True,
            "no_descendant_rebilling_for_interface_variation": True,
        },
        "concludes": {
            "SectionFixedAbsoluteInterfaceVariationPaymentSource": True,
            "LocalizedAffineEulerCoreHighPiInterfacePaymentSource": True,
            "ParabolicChannelCoefficientEstimateSource": True,
        },
        "does_not_accept": [
            "signed_final_commutator_payment_only",
            "positive_part_chosen_after_payoff",
            "absolute_variation_on_proxy_owner",
            "descendant_rebilling_for_interface_variation",
            "same_owner_label_without_absolute_variation",
        ],
    },
    "signed_transport_commutator_cancellation_packet_gate": {
        "requires": {
            "proxy_owner_transport_commutator_underpayment_packet": True,
            "same_localized_packet_owner_includes_interface": True,
            "signed_transport_commutator_cancels_on_selected_prefix": True,
            "absolute_interface_variation_payment_missing": True,
            "signed_final_commutator_lt_reynolds_excess": True,
        },
        "concludes": {
            "SignedTransportCommutatorCancellationPacket": True,
            "signed_commutator_not_positive_interface_invoice": True,
            "absolute_interface_variation_payment_required": True,
        },
        "does_not_accept": [
            "signed_final_commutator_payment_only",
            "same_owner_label_without_absolute_variation",
            "positive_part_chosen_after_payoff",
            "final_pressure_carrier_only",
        ],
    },
    "proxy_owner_transport_commutator_underpayment_packet_gate": {
        "requires": {
            "localized_affine_euler_core_high_pi_underpayment_packet": True,
            "transport_cutoff_commutator_exists_with_high_pi_scaling": True,
            "commutator_charged_to_proxy_owner": True,
            "selected_c7_surplus_owner_unpaid_by_proxy_commutator": True,
            "same_selected_prefix_map_missing": True,
        },
        "concludes": {
            "ProxyOwnerTransportCommutatorUnderpaymentPacket": True,
            "LocalizedAffineEulerCoreHighPiInterfacePaymentSource_excluded_for_same_data": True,
            "same_selected_prefix_map_is_required": True,
        },
        "does_not_accept": [
            "transport_cutoff_commutator_charged_to_same_selected_owner",
            "same_selected_prefix_map_proved",
            "proxy_owner_label_repaired_after_payoff",
            "final_pressure_carrier_only",
        ],
    },
    "localized_affine_euler_core_high_pi_interface_payment_source_gate": {
        "requires": {
            "parabolic_channel_coefficient_estimate_source": True,
            "transport_cutoff_commutator_generated_before_payoff": True,
            "transport_cutoff_commutator_charged_to_same_selected_owner": True,
            "transport_cutoff_commutator_pays_reynolds_excess": True,
            "effective_coefficient_splits_transport_interface": True,
            "not_final_pressure_or_square_overflow_budget": True,
        },
        "concludes": {
            "LocalizedAffineEulerCoreHighPiInterfacePaymentSource": True,
            "ParabolicChannelCoefficientEstimateSource": True,
            "ParabolicEffectiveInvoiceCoefficientPaysAffineSurplus": True,
        },
        "does_not_accept": [
            "transport_commutator_exists_but_proxy_owner",
            "commutator_charged_after_payoff",
            "final_pressure_carrier_only",
            "square_budget_only_payment",
            "overflow_only_payment",
            "cutoff_shell_invoice_only",
            "core_affine_pressure_cancellation_as_payment",
        ],
    },
    "localized_affine_euler_core_high_pi_underpayment_packet_gate": {
        "requires": {
            "parabolic_effective_invoice_underpaid_channel_packet": True,
            "active_reynolds_ratio_eq_sR2_over_nu": True,
            "core_affine_equation_paid_by_pressure_and_time_derivative": True,
            "cutoff_shell_coefficient_does_not_scale_with_pi": True,
            "localization_interface_is_only_possible_high_pi_payment": True,
            "effective_invoice_coefficient_lt_reynolds_excess": True,
        },
        "concludes": {
            "LocalizedAffineEulerCoreHighPiUnderpaymentPacket": True,
            "ParabolicChannelCoefficientEstimateSource_excluded_for_same_data": True,
            "positive_route_must_extract_high_pi_interface_payment": True,
        },
        "does_not_accept": [
            "cutoff_shell_invoice_only",
            "core_affine_pressure_cancellation_as_payment",
            "dimensionless_ratio_only",
            "owner_label_only",
            "final_pressure_carrier_only",
            "reynolds_excess_le_effective_invoice_coefficient",
        ],
    },
    "parabolic_effective_invoice_underpaid_channel_packet_gate": {
        "requires": {
            "time_dependent_local_affine_jet": True,
            "same_owner_selected_c7_tent": True,
            "effective_invoice_coefficient_eq_sum_prepaid_channel_coefficients": True,
            "each_channel_coefficient_fixed_before_payoff": True,
            "each_channel_coefficient_paid_by_same_owner_invoice": True,
            "coefficient_not_recovered_from_totalInvoice_or_surplus_conclusion": True,
            "eta_le_reynolds_excess": True,
            "effective_invoice_coefficient_times_A_le_total_invoice": True,
            "effective_invoice_coefficient_lt_reynolds_excess": True,
        },
        "concludes": {
            "ParabolicEffectiveInvoiceCoefficientUnderpaidChannelPacket": True,
            "ParabolicEffectiveInvoiceCoefficientPaysAffineSurplus_excluded_for_same_data": True,
            "channel_decomposition_alone_does_not_pay_high_pi": True,
        },
        "does_not_accept": [
            "reynolds_excess_le_effective_invoice_coefficient",
            "reynolds_excess_le_effectiveInvoiceCoefficient_from_channel_estimates",
            "effective_invoice_coefficient_defined_as_total_invoice_over_A",
            "coefficient_chosen_after_payoff",
            "ownership_only",
            "dimensionless_ratio_only",
        ],
    },
    "parabolic_channel_coefficient_estimate_source_gate": {
        "requires": {
            "parabolic_effective_invoice_coefficient_pays_affine_surplus": True,
            "effective_invoice_coefficient_eq_sum_prepaid_channel_coefficients": True,
            "each_channel_coefficient_fixed_before_payoff": True,
            "each_channel_coefficient_paid_by_same_owner_invoice": True,
            "reynolds_excess_le_effectiveInvoiceCoefficient_from_channel_estimates": True,
            "coefficient_not_recovered_from_totalInvoice_or_surplus_conclusion": True,
            "channel_coefficient_estimate_is_only_open_pde_input": True,
        },
        "concludes": {
            "ParabolicChannelCoefficientEstimateSource": True,
            "ParabolicEffectiveInvoiceCoefficientPaysAffineSurplus": True,
            "ParabolicFiniteEnergyInvoiceLowerBoundForLocalizedAffineTent": True,
        },
        "does_not_accept": [
            "effective_invoice_coefficient_lt_reynolds_excess",
            "channel_decomposition_only",
            "coefficient_labels_only",
            "conclusion_divided_by_A",
            "ownership_only",
            "dimensionless_ratio_only",
        ],
    },
    "parabolic_effective_invoice_coefficient_pays_affine_surplus_gate": {
        "requires": {
            "time_dependent_local_affine_jet": True,
            "same_owner_selected_c7_tent": True,
            "parabolic_active_scale_owner_stream": True,
            "effective_invoice_coefficient_fixed_before_payoff": True,
            "effective_invoice_coefficient_not_defined_as_total_invoice_after_payoff": True,
            "effective_invoice_coefficient_eq_sum_prepaid_channel_coefficients": True,
            "each_channel_coefficient_fixed_before_payoff": True,
            "each_channel_coefficient_paid_by_same_owner_invoice": True,
            "coefficient_not_recovered_from_totalInvoice_or_surplus_conclusion": True,
            "eta_le_reynolds_excess": True,
            "reynolds_excess_le_effective_invoice_coefficient": True,
            "reynolds_excess_le_effectiveInvoiceCoefficient_from_channel_estimates": True,
            "effective_coefficient_le_physical_invoice_density": True,
            "effective_invoice_coefficient_times_A_le_total_invoice": True,
            "finite_energy_cutoff_constructed_before_payoff": True,
            "leray_projection_charged_before_payoff": True,
            "pre_summed_pressure_tail_charged_before_payoff": True,
            "duhamel_reserve_separated_before_invoice": True,
            "inherited_reserve_separated_before_invoice": True,
            "selected_partition_fixed_before_invoice": True,
            "section_identity_fixed_before_invoice": True,
            "no_reuse_all_prefix_linear_budget": True,
            "rejects_final_carrier_only_pressure": True,
            "rejects_overflow_only_or_square_budget_payment": True,
            "no_CF_or_other_Clay_equivalent_input_used": True,
        },
        "concludes": {
            "ParabolicEffectiveInvoiceCoefficientPaysAffineSurplus": True,
            "ParabolicFiniteEnergyInvoiceLowerBoundForLocalizedAffineTent": True,
            "dynamic_high_pi_invoice_paid_if_coefficient_is_sourced": True,
        },
        "does_not_accept": [
            "effective_invoice_coefficient_defined_as_total_invoice_over_A",
            "coefficient_chosen_after_payoff",
            "chosen_after_eta",
            "chosen_after_totalInvoice",
            "conclusion_divided_by_A",
            "channel_coefficients_missing",
            "fixed_cutoff_constant_only",
            "dimensionless_ratio_only",
            "ownership_only",
            "final_carrier_only_pressure",
            "overflow_only_payment",
            "square_budget_only_payment",
            "CF_or_direction_coherence",
        ],
    },
    "parabolic_pi_lock_owner_label_only_confuser_gate": {
        "requires": {
            "time_dependent_local_affine_jet": True,
            "same_owner_selected_c7_tent": True,
            "owner_label_fixed_before_payoff": True,
            "selected_c7_owner_label": True,
            "ratio_source_contract_missing": True,
            "eta_gt_cutoff_constant": True,
        },
        "concludes": {
            "ParabolicPiLockOwnerLabelOnlyConfuser": True,
            "ParabolicActiveScalePiLockForCutoffPayment_excluded_for_same_jet_and_constant": True,
            "owner_label_only_does_not_source_pi_lock": True,
        },
        "does_not_accept": [
            "affine_reynolds_ratio_eq_sR2_over_nu",
            "ratio_fixed_before_payoff",
            "eta_le_reynolds_excess_from_affine_packet_geometry",
            "reynolds_le_one_plus_cutoff_constant_from_finite_energy_cutoff",
            "eta_le_cutoff_constant",
            "dimensionless_ratio_only",
        ],
    },
    "parabolic_active_scale_pi_lock_for_cutoff_payment_gate": {
        "requires": {
            "time_dependent_local_affine_jet": True,
            "same_owner_selected_c7_tent": True,
            "parabolic_active_scale_owner_stream": True,
            "active_scale_normalization_A_equals_cutoff_unit": True,
            "affine_reynolds_ratio_defined": True,
            "affine_reynolds_ratio_eq_sR2_over_nu": True,
            "nu_pos": True,
            "selected_c7_radius_eq_R": True,
            "active_scale_strain_eq_s": True,
            "ratio_fixed_before_payoff": True,
            "eta_le_reynolds_excess": True,
            "eta_le_reynolds_excess_from_affine_packet_geometry": True,
            "reynolds_le_one_plus_cutoff_constant": True,
            "reynolds_le_one_plus_cutoff_constant_from_finite_energy_cutoff": True,
            "cutoff_invoice_equals_c_cut_times_A": True,
            "cutoff_invoice_le_total_invoice": True,
            "duhamel_reserve_separated_before_invoice": True,
            "inherited_reserve_separated_before_invoice": True,
            "selected_partition_fixed_before_invoice": True,
            "section_identity_fixed_before_invoice": True,
            "no_reuse_all_prefix_linear_budget": True,
            "rejects_final_carrier_only_pressure": True,
            "rejects_overflow_only_or_square_budget_payment": True,
            "no_CF_or_other_Clay_equivalent_input_used": True,
        },
        "concludes": {
            "ParabolicActiveScalePiLockForCutoffPayment": True,
            "ParabolicCutoffInvoicePaysAffineSurplusModel": True,
            "ParabolicFiniteEnergyInvoiceLowerBoundForLocalizedAffineTent": True,
            "eta_le_cutoff_constant_from_pi_lock": True,
        },
        "does_not_accept": [
            "ownership_only",
            "dimensionless_ratio_only",
            "finite_energy_high_pi_regime_only",
            "affineReynoldsRatio_chosen_after_eta",
            "cutoffConstant_chosen_after_eta",
            "eta_chosen_after_cutoff_constant",
            "sR2_over_nu_binding_missing",
            "ratio_fixed_after_payoff",
            "reynolds_bound_missing",
            "active_scale_normalization_missing",
            "cutoff_invoice_paid_by_declaration",
            "final_carrier_only_pressure",
            "overflow_only_payment",
            "square_budget_only_payment",
            "CF_or_direction_coherence",
        ],
    },
    "parabolic_finite_energy_invoice_lower_bound_for_localized_affine_tent_gate": {
        "requires": {
            "time_dependent_local_affine_jet": True,
            "same_owner_selected_c7_tent": True,
            "parabolic_active_scale_owner_stream": True,
            "finite_energy_cutoff_constructed_before_payoff": True,
            "leray_projection_charged_before_payoff": True,
            "pre_summed_pressure_tail_charged_before_payoff": True,
            "duhamel_reserve_separated_before_invoice": True,
            "inherited_reserve_separated_before_invoice": True,
            "selected_partition_fixed_before_invoice": True,
            "section_identity_fixed_before_invoice": True,
            "no_reuse_all_prefix_linear_budget": True,
            "surplus_equals_eta_times_A": True,
            "total_invoice_ge_surplus": True,
            "rejects_final_carrier_only_pressure": True,
            "rejects_overflow_only_or_square_budget_payment": True,
            "no_CF_or_other_Clay_equivalent_input_used": True,
        },
        "concludes": {
            "ParabolicFiniteEnergyInvoiceLowerBoundForLocalizedAffineTent": True,
            "LocalizedC7TentCutoffInvoiceLeakPacket_excluded": True,
            "strict_fraction_scaling_leak_excluded_on_selected_parabolic_stream": True,
        },
        "does_not_accept": [
            "dimensionless_ratio_only",
            "local_affine_trace_zero_positive_stretching_only",
            "final_carrier_only_pressure",
            "overflow_only_payment",
            "square_budget_only_payment",
            "pressure_visibility_only",
            "profile_schur_carleson_envelope_label_only",
            "different_owner_invoice",
            "theta_chosen_after_payoff",
            "CF_or_direction_coherence",
        ],
    },
    "balanced_core_sheath_trace_zero_positive_net_budget_exclusion_gate": {
        "requires": {
            "balanced_core_sheath_dini_ladder_packet": True,
            "same_trajectory_NS_jet_compatibility": True,
            "angular_frame_fixed_before_payoff": True,
            "pressure_samples_on_same_fresh_annular_source": True,
            "angular_frame_spans_tracefree_tensor_morphology": True,
            "source_to_strain_production_coercivity": True,
            "no_same_window_sheath_cancellation_on_angular_frame": True,
            "no_tangential_pressure_null_production": True,
            "no_higher_jet_retuning_over_dwell": True,
            "owner_prefix_budget_for_all_five_shadow_measures": True,
            "five_frame_pressure_residual_nonnegative": True,
            "retuning_error_nonnegative": True,
            "framePressureStealth_to_sameTrajectoryProductionBound": True,
            "pressure_and_retuning_errors_below_eta_A_gap": True,
            "constraint_fixed_before_SOS_search": True,
            "no_CF_or_other_Clay_equivalent_input_used": True,
        },
        "concludes": {
            "TraceZeroPositiveNetBudgetQuantitativeExclusionReceipt": True,
            "no_TraceZeroStrainPositiveNetBudgetJet_of_quantitativePressureProductionBound": True,
        },
        "does_not_accept": [
            "scalar_pressure_stealth_only",
            "single_direction_pressure_sample",
            "frame_selected_after_payoff",
            "pressure_samples_on_proxy_carrier",
            "same_window_sheath_cancellation_still_admissible",
            "tangential_pressure_null_loss_unpaid",
            "source_to_production_coercivity_missing",
            "tomography_rank_receipt_missing",
            "linear_observable_coercivity_receipt_missing",
            "dimension_or_pi_group_unchecked",
            "higher_jet_retuning_still_admissible",
            "positive_net_budget_confuser",
            "dissipation_production_gap_assumed_directly",
            "CF_or_direction_coherence",
            "numeric_SOS_search_without_fixed_frame_constraint",
        ],
    },
    "pressure_hessian_l2_frame_self_tax_budget_source_gate": {
        "requires": {
            "pressure_hessian_l2_controls_frame_self_tax": True,
            "renormalized_pressure_l2_cap": True,
            "pressure_l2_cap_pays_viscous_error": True,
            "same_source_pressure_l2_carrier": True,
            "commutator_and_transport_remainder_accounted": True,
            "no_proxy_pressure_carrier": True,
        },
        "concludes": {
            "PressureHessianL2FrameSelfTaxBudgetSource": True,
            "frameSelfTaxPrice_le_viscous_plus_two_error_of_pressureHessianL2Source": True,
        },
        "does_not_accept": [
            "pressure_l2_visibility_only",
            "pressure_carrier_proxy",
            "commutator_remainder_unpaid",
            "transport_remainder_unpaid",
            "pressure_l2_cap_not_compared_to_viscous_error",
            "same_window_sheath_cancellation_still_admissible",
            "tangential_pressure_null_loss_unpaid",
        ],
    },
    "same_window_presummed_pressure_frame_self_tax_estimate_gate": {
        "requires": {
            "presummed_absolute_pressure_frame_charge": True,
            "presummed_frame_charge_fixed_before_payoff": True,
            "presummed_absolute_not_final_signed_carrier": True,
            "no_tangential_divdiv_null_stress_on_production_frame": True,
            "no_same_window_core_sheath_cancellation_for_presummed_frame": True,
            "transport_commutator_remainder_billed_to_same_owner_window": True,
            "no_higher_jet_retuning_of_presummed_frame_over_dwell": True,
            "production_invoice_channel_separated": True,
            "inherited_reserve_channel_separated": True,
            "pressure_frame_partition_fixed_before_spend": True,
            "section_identity_fixed_before_frame_self_tax": True,
            "no_reuse_channel_separated_for_presummed_frame_self_tax": True,
            "production_sq_le_viscous_times_frame_self_tax_same_window": True,
            "frame_self_tax_le_presummed_charge_plus_remainder": True,
            "presummed_charge_plus_remainder_le_viscous_plus_two_error": True,
            "no_CF_or_other_Clay_equivalent_input_used": True,
        },
        "concludes": {
            "SameWindowPreSummedPressureFrameSelfTaxEstimate": True,
            "TraceZeroPositiveNetBudgetDualPriceFrameReceipt": True,
        },
        "does_not_accept": [
            "final_signed_l2_carrier",
            "pressure_l2_visibility_only",
            "rank5_tomography_without_dual_product_bound",
            "same_window_core_sheath_cancellation_still_admissible",
            "tangential_divdiv_null_stress_still_admissible",
            "higher_jet_retuning_still_admissible",
            "frame_self_tax_chosen_after_payoff",
            "invoice_channel_missing",
            "inherited_reserve_channel_missing",
            "partition_not_fixed_before_spend",
            "section_identity_not_fixed_before_frame_self_tax",
            "no_reuse_channel_missing",
            "CF_or_direction_coherence",
        ],
    },
    "no_bounded_hofstadter_transaction_carrier_without_no_wash_law_gate": {
        "requires": {
            "net_or_quotient_source_law": True,
            "positive_transaction_variation_currency": True,
            "same_selected_owner_window": True,
            "pre_payoff_representative_fixed": True,
            "no_wash_cycle_law": True,
            "no_null_cycle_growth": True,
            "bounded_positive_variation_from_net_budget": True,
            "no_post_payoff_grossing": True,
        },
        "concludes": {
            "SelectedTransactionNoWashLaw": True,
            "BoundedSelectableTransactionCarrier": True,
        },
        "does_not_accept": [
            "net_identity_only",
            "same_window_label",
            "pressure_visibility_only",
            "rank5_tomography_without_no_wash",
            "pre_summed_label_only",
            "core_sheath_wash_cycle_still_admissible",
            "unbounded_turnover_same_net",
            "post_payoff_positive_grossing",
        ],
    },
    "quotient_minimal_transaction_norm_payment_gate": {
        "requires": {
            "quotient_source_law": True,
            "minimal_positive_transaction_variation_defined": True,
            "selected_high_high_production_functional": True,
            "pre_payoff_representative_selector": True,
            "selector_independent_of_target_deficit": True,
            "production_preserved_by_selector": True,
            "kernel_cycles_zero_selected_high_high": True,
            "minimal_carrier_bounds_selected_high_high": True,
        },
        "concludes": {
            "SelectedQuotientRepresentativeLaw": True,
            "QuotientMinimalTransactionCarrierPaysSelectedHighHigh": True,
        },
        "does_not_accept": [
            "infimum_exists_only",
            "net_budget_bound_only",
            "same_source_label_only",
            "wash_eliminated_only",
            "canonical_representative_label_only",
            "kernel_cycle_carries_selected_high_high",
            "selected_high_high_not_quotient_invariant",
            "actual_packet_not_minimizer",
            "post_payoff_minimizer_selection",
        ],
    },
    "pressure_l2_cap_pays_same_source_frame_self_tax_gate": {
        "requires": {
            "same_source_pressure_l2_carrier": True,
            "no_tangential_divdiv_null_stress_on_production_frame": True,
            "no_same_window_core_sheath_cancellation_for_l2_frame": True,
            "transport_commutator_remainder_billed_to_same_owner_window": True,
            "no_higher_jet_retuning_of_l2_residual_over_dwell": True,
            "production_invoice_channel_separated": True,
            "inherited_reserve_channel_separated": True,
            "pressure_frame_partition_fixed_before_spend": True,
            "section_identity_fixed_before_frame_self_tax": True,
            "no_reuse_channel_separated_for_l2_frame_self_tax": True,
            "pressure_l2_controls_frame_self_tax_on_same_window": True,
            "pressure_l2_cap_pays_viscous_error": True,
            "production_sq_le_viscous_times_frame_self_tax_same_window": True,
        },
        "concludes": {
            "PressureL2CapPaysSameSourceFrameSelfTax": True,
            "TraceZeroPositiveNetBudgetDualPriceFrameReceipt": True,
        },
        "does_not_accept": [
            "pressure_l2_visibility_only",
            "rank5_tomography_without_dual_product_bound",
            "tangential_divdiv_null_stress_still_admissible",
            "same_window_core_sheath_cancellation_still_admissible",
            "transport_commutator_remainder_unbilled",
            "higher_jet_retuning_still_admissible",
            "invoice_channel_missing",
            "inherited_reserve_channel_missing",
            "partition_not_fixed_before_spend",
            "section_identity_not_fixed_before_frame_self_tax",
            "no_reuse_channel_missing",
            "frame_self_tax_not_same_source",
            "production_sq_bound_on_proxy_window",
            "CF_or_direction_coherence",
        ],
    },
    "balanced_core_sheath_dual_price_frame_exclusion_gate": {
        "requires": {
            "balanced_core_sheath_dini_ladder_packet": True,
            "same_trajectory_NS_jet_compatibility": True,
            "pressure_samples_on_same_fresh_annular_source": True,
            "angular_frame_spans_tracefree_tensor_morphology": True,
            "dual_price_bound_from_frame_pressure": True,
            "production_sq_le_viscous_times_frame_self_tax": True,
            "frame_self_tax_price_le_viscous_plus_two_error": True,
            "error_reserve_below_eta_A_gap": True,
            "no_same_window_sheath_cancellation_on_angular_frame": True,
            "no_tangential_pressure_null_production": True,
            "no_higher_jet_retuning_over_dwell": True,
            "owner_prefix_budget_for_all_five_shadow_measures": True,
            "constraint_fixed_before_SOS_search": True,
            "no_CF_or_other_Clay_equivalent_input_used": True,
        },
        "concludes": {
            "TraceZeroPositiveNetBudgetDualPriceFrameReceipt": True,
            "signedProduction_le_viscous_plus_error_of_dualPriceFrameReceipt": True,
            "no_TraceZeroStrainPositiveNetBudgetJet_of_dualPriceFrameReceipt": True,
        },
        "does_not_accept": [
            "direct_pressure_residual_bound_only",
            "scalar_pressure_stealth_only",
            "rank5_tomography_without_dual_product_bound",
            "frame_self_tax_not_same_source",
            "frame_self_tax_price_unbounded",
            "error_reserve_not_below_eta_A",
            "same_window_sheath_cancellation_still_admissible",
            "tangential_pressure_null_loss_unpaid",
            "higher_jet_retuning_still_admissible",
            "positive_net_budget_confuser",
            "CF_or_direction_coherence",
        ],
    },
    "tick647_wall_scope_non_pure_power_log_gate": {
        "requires": {
            "log_corrected_asymptotic_declared": True,
            "exact_norm_and_log_denominator_declared": True,
            "solution_binding_declared": True,
            "blowup_necessary_direction_declared": True,
            "log_correction_not_reparametrized_pure_power": True,
            "parabolic_slaving_receipt_absent_or_refuted": True,
            "no_bkm_log_circularity": True,
            "no_clay_equivalent_input_used": True,
        },
        "concludes": {
            "LogCorrectedAsymptoticScopeReceipt": True,
            "tick647_wall_scope_failure_not_regularity_discharge": True,
        },
        "does_not_accept": [
            "generic_log_improvement_label",
            "bkm_log_label_only",
            "log_denominator_without_solution_binding",
            "pure_power_with_log_not_separated",
            "parabolic_slaving_unchecked",
            "log_bkm_as_active_length_without_receipt",
            "closure_claim_from_scope_failure",
            "KT_or_Merle_Raphael_analogy_without_NS_receipt",
        ],
    },
    "log_discount_transaction_channel_source_gate": {
        "requires": {
            "tick647_wall_scope_non_pure_power_log_gate": True,
            "raw_channel_declared": True,
            "log_discounted_channel_declared": True,
            "discount_denominator_ge_one": True,
            "channel_identity_raw_equals_discounted_times_denominator": True,
            "finite_log_discount_criterion_declared": True,
            "source_pays_finite_log_discount_criterion": True,
            "continuation_from_finite_log_discount_criterion": True,
            "discount_channel_fixed_before_payoff": True,
            "no_raw_bkm_or_cf_input_hidden_in_source_payment": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "LogDiscountTransactionChannelSource": True,
            "LogCorrectedAsymptoticScopeReceipt": True,
            "tick647_wall_scope_failure_not_regularity_discharge": True,
            "paid_log_discount_channel_continuation_source": True,
        },
        "does_not_accept": [
            "generic_log_improvement_label",
            "outside_wall_scope_without_channel_payment",
            "bkm_log_label_only",
            "source_bound_is_raw_bkm_or_cf_input",
            "discount_denominator_chosen_after_payoff",
            "finite_criterion_not_source_paid",
        ],
    },
    "log_scope_without_paid_transaction_channel_confuser_gate": {
        "requires": {
            "tick647_wall_scope_non_pure_power_log_gate": True,
            "log_scope_only": True,
            "finite_criterion_not_source_paid": True,
            "raw_bkm_log_circularity_risk": True,
        },
        "concludes": {
            "LogScopeWithoutPaidTransactionChannelConfuser": True,
            "LogDiscountTransactionChannelSource_excluded": True,
            "outside_wall_scope_does_not_pay_log_channel": True,
        },
        "does_not_accept": [
            "source_pays_finite_log_discount_criterion",
            "continuation_from_scope_failure_only",
            "source_bound_is_raw_bkm_or_cf_input",
        ],
    },
    "kt_bmo_log_finite_from_ns_sources_gate": {
        "requires": {
            "log_discount_transaction_channel_source_gate": True,
            "exact_norm_and_log_denominator_declared": True,
            "solution_binding_declared": True,
            "smooth_open_window_cothread": True,
            "finite_kt_bmo_log_bound": True,
            "finite_kt_bmo_log_bound_from_ns_sources": True,
            "no_bkm_log_circularity": True,
            "no_cf_direction_import": True,
            "no_clay_equivalent_input_used": True,
            "source_contract_alignment_check_passed": True,
        },
        "concludes": {
            "KTBMOLogFiniteFromNSSources": True,
            "LogDiscountTransactionChannelSource": True,
            "faithful_kt_bmo_log_continuation_surface": True,
        },
        "does_not_accept": [
            "bkm_log_label_only",
            "finite_criterion_bound_not_derived",
            "only_tick647_scope_failure",
            "hidden_bkm_or_cf_input",
            "bmo_endpoint_dual_only",
            "no_selected_c7_payment",
        ],
    },
    "kt_bmo_log_bound_confuser_gate": {
        "requires": {
            "bkm_log_label_only": True,
            "finite_criterion_bound_not_derived": True,
            "only_tick647_scope_failure": True,
            "hidden_bkm_or_cf_input": True,
            "bmo_endpoint_dual_only": True,
            "no_selected_c7_payment": True,
        },
        "concludes": {
            "KTBMOLogBoundConfuser": True,
            "KTBMOLogFiniteFromNSSources_excluded": True,
            "kt_bmo_log_surface_not_positive_without_source_bound": True,
        },
        "does_not_accept": [
            "finite_kt_bmo_log_bound_from_ns_sources",
            "source_pays_finite_log_discount_criterion",
            "continuation_from_scope_failure_only",
        ],
    },
    "tick647_wall_scope_non_degree_zero_topology_gate": {
        "requires": {
            "fixed_topology_before_payoff": True,
            "vortex_topology_input_declared": True,
            "topology_extraction_not_local_eulerian_riesz": True,
            "topological_quantity_solution_bound": True,
            "helicity_dark_packet_tested": True,
            "reconnection_error_term_declared": True,
            "finite_owner_preimage_multiplicity": True,
            "no_lagrangian_cocycle_alias": True,
            "no_helicity_coercivity_assumed": True,
        },
        "concludes": {
            "VortexTopologyInputScopeReceipt": True,
            "tick647_wall_scope_failure_not_regularity_discharge": True,
        },
        "does_not_accept": [
            "helicity_label_only",
            "topological_name_without_extractor",
            "lagrangian_deformation_cocycle_alias",
            "degree_zero_riesz_eulerian_object",
            "fixed_topology_after_payoff",
            "helicity_dark_plane_wave_untested",
            "reconnection_count_without_viscous_error",
            "owner_preimage_receipt_missing",
            "closure_claim_from_scope_failure",
        ],
    },
    "selected_balanced_cone_signed_global_budget_gate": {
        "requires": {
            "packet_encodes_near_stealth_balanced_cone": True,
            "same_owner_selected_stream": True,
            "selected_packet_would_need_growth_bearing_segment": True,
            "enstrophy_budget_consistent": True,
            "signed_global_budget_fixed_before_blowup_claim": True,
            "signed_budget_nonpositive": True,
            "production_channel_separated": True,
            "invoice_channel_separated": True,
            "inherited_reserve_channel_separated": True,
            "selected_budget_partition_fixed_before_spend": True,
            "section_identity_fixed_before_signed_budget": True,
            "no_reuse_channel_separated_for_signed_budget": True,
            "budget_not_from_pressure_visibility_only": True,
            "budget_not_from_final_carrier_magnitude": True,
            "no_CF_or_other_Clay_equivalent_input_used": True,
        },
        "concludes": {
            "SelectedBalancedConeSignedGlobalBudgetReceipt": True,
            "BalancedCoreSheathSignedGrowthSterilityReceipt": True,
        },
        "does_not_accept": [
            "pressure_l2_visibility_only",
            "final_signed_l2_carrier",
            "rank5_tomography_without_dual_product_bound",
            "local_positive_pockets_only",
            "unsigned_production_budget",
            "positive_net_budget_confuser",
            "signed_budget_after_blowup_claim",
            "production_channel_missing",
            "invoice_channel_missing",
            "inherited_reserve_channel_missing",
            "partition_not_fixed_before_spend",
            "section_identity_not_fixed_before_signed_budget",
            "no_reuse_channel_missing",
            "CF_or_direction_coherence",
        ],
    },
    "balanced_core_sheath_sos_gap_certificate_gate": {
        "requires": {
            "balanced_core_sheath_dini_ladder_packet": True,
            "packet_encodes_near_stealth_balanced_cone": True,
            "same_owner_selected_stream": True,
            "selected_packet_would_need_growth_bearing_segment": True,
            "enstrophy_budget_consistent": True,
            "exact_dissipation_minus_production_sos_identity": True,
            "positive_slack": True,
            "certificate_fixed_before_blowup_claim": True,
            "not_numeric_sdp_only": True,
        },
        "concludes": {
            "BalancedCoreSheathSosGapCertificateSource": True,
            "BalancedCoreSheathSignedGrowthSterilityReceipt": True,
        },
        "does_not_accept": [
            "numeric_sdp_float_certificate_only",
            "inequality_without_exact_identity",
            "zero_slack_certificate",
            "certificate_not_same_trajectory",
            "local_positive_pockets_only",
            "unsigned_production_budget",
            "positive_net_budget_confuser",
            "signed_budget_after_blowup_claim",
        ],
    },
    "balanced_core_sheath_signed_growth_sterility_gate": {
        "requires": {
            "balanced_core_sheath_dini_ladder_packet": True,
            "packet_encodes_near_stealth_balanced_cone": True,
            "same_owner_selected_stream": True,
            "selected_packet_would_need_growth_bearing_segment": True,
            "enstrophy_budget_consistent": True,
            "stealth_growth_sterile": True,
            "signed_budget_fixed_before_blowup_claim": True,
            "signed_global_budget_not_local_pockets": True,
        },
        "concludes": {
            "BalancedCoreSheathSignedGrowthSterilityReceipt": True,
            "balanced_core_sheath_ladder_not_growth_engine": True,
        },
        "does_not_accept": [
            "local_positive_pockets_only",
            "pointwise_torque_only",
            "pressure_stealth_empty_claim",
            "transversality_only",
            "unsigned_production_budget",
            "positive_net_budget_confuser",
            "signed_net_budget_missing",
            "enstrophy_budget_not_same_trajectory",
            "signed_budget_after_blowup_claim",
            "final_carrier_magnitude",
            "CF_or_direction_coherence",
        ],
    },
    "tracefree_variation_dimensional_length_payment": {
        "requires": {
            "tracefree_variation_pointwise_same_carrier_payment": True,
            "macro_length_fixed_before_payoff": True,
            "geometric_decay_from_external_scale": True,
            "macro_length_survives_local_blowup_rescaling": True,
            "local_payment_not_boundary_or_low_mode_only": True,
            "not_nu_parabolic_scale": True,
            "not_target_defined_length": True,
        },
        "concludes": {
            "TraceFreeVariationDimensionalLengthPaymentReceipt": True,
            "TraceFreeVariationPointwiseSameCarrierPaymentReceipt": True,
            "TraceFreeVariationC7CofinalOwnerPrefixBudget": True,
        },
        "does_not_accept": [
            "macro_length_ratio_available_only",
            "free_pi_group_without_physical_constraint",
            "local_blowup_rescaling_removes_macro_length",
            "boundary_or_low_mode_only_after_rescaling",
            "length_chosen_from_selected_prefix_growth",
            "length_chosen_after_angular_spend",
            "nu_parabolic_scale_only",
            "DSS_limit_trivializes_external_length",
            "target_defined_geometric_decay",
        ],
    },
    "tracefree_commutator_nullform_pointwise_payment": {
        "requires": {
            "tracefree_variation_pointwise_same_carrier_payment": True,
            "commutator_currency_pays_absolute_tracefree_variation": True,
            "positive_cone_minorant_not_signed_cancellation": True,
            "non_degree_zero_symbol_gain": True,
            "not_homogeneity_zero_riesz_commutator": True,
            "not_square_or_signed_currency_only": True,
        },
        "concludes": {
            "TraceFreeVariationPointwiseSameCarrierPaymentReceipt": True,
        },
        "does_not_accept": [
            "signed_commutator_cancellation_available_only",
            "absolute_tracefree_variation_payment_missing",
            "square_or_signed_currency_only",
            "degree_zero_riesz_symbol_only",
            "homogeneity_zero_obstruction_still_admissible",
            "commutator_upper_bound_only",
            "null_form_cancellation_only",
        ],
    },
    "tracefree_CZ_endpoint_pointwise_payment": {
        "requires": {
            "tracefree_variation_pointwise_same_carrier_payment": True,
            "selected_packet_unconditional_L1_embedding": True,
            "CZ_endpoint_pays_preselected_absolute_coefficients": True,
            "not_BMO_or_weak_endpoint_only": True,
            "not_besov_paraproduct_or_CF_import": True,
        },
        "concludes": {
            "TraceFreeVariationPointwiseSameCarrierPaymentReceipt": True,
        },
        "does_not_accept": [
            "CZ_endpoint_signed_or_weak_only",
            "BMO_endpoint_dual_only",
            "selected_packet_unconditional_L1_embedding_missing",
            "endpoint_paraproduct_besov_or_target_defined_budget_required",
            "pressure_riesz_degree_zero_carrier_only",
            "CF_or_direction_coherence",
        ],
    },
    "five_frame_route_tail_exchange": {
        "requires": {
            "nonadaptive_annular_C7_source_selection": True,
            "five_frame_samples_same_annular_output_packet": True,
            "annular_projected_packet_identified_with_nonadaptive_event_stream": True,
            "eventRadiusPayment_eq_or_controls_fiveFrameTracefreeAngularPay": True,
            "same_selected_prefix_map_fixed_before_payoff": True,
            "tracefree_tensor_total_variation_not_signed_moment": True,
            "cutoff_low_high_tails_paid_same_stream": True,
            "no_target_defined_comparison_constant": True,
            "not_besov_BV_productL2_or_CF_import": True,
        },
        "concludes": {
            "FiveFrameRouteTailExchangeTheorem": True,
            "fiveFrameEventPayCanConsumeNonadaptiveRouteTailBudget": True,
        },
        "does_not_accept": [
            "eventRadiusPayment_not_five_frame_tracefree_angular_event_pay",
            "routeActiveTail_budget_spent_on_five_frame_event_pay_without_exchange",
            "five_frame_event_pay_bounded_comparison_missing",
            "five_frame_samples_on_proxy_carrier",
            "selected_prefix_map_changed_after_payoff",
            "signed_moment_used_as_total_variation",
            "cutoff_low_high_tails_unpaid",
            "target_defined_comparison_constant",
            "product_L2_or_BV_or_CF_import",
            "harmonic_five_frame_event_pay_with_summable_route_tail",
        ],
    },
    "annular_bandlimited_riesz_l1_psd_trace_payment": {
        "requires": {
            "tracefree_variation_pointwise_same_carrier_payment": True,
            "selected_target_uses_annular_bandlimited_output_packet": True,
            "annular_projected_packet_identified_with_nonadaptive_event_stream": True,
            "annular_event_pay_eq_prior_nonadaptive_event_stream": True,
            "annular_bandlimit_fixed_before_payoff": True,
            "output_packet_support_same_annular_carrier": True,
            "tracefree_tensor_total_variation_not_signed_moment": True,
            "no_low_high_leakage_after_projection": True,
            "annular_riesz_kernel_uniform_L1_norm": True,
            "PSD_trace_pays_annular_projected_packet": True,
            "cutoff_commutator_tails_paid_by_same_stream_ShardC": True,
            "selected_PSD_trace_owner_prefix_budget": True,
            "not_raw_CZ_measure_L1": True,
            "not_besov_BV_or_CF_import": True,
        },
        "concludes": {
            "AnnularBandlimitedRieszL1PSDTracePaymentReceipt": True,
            "TraceFreeVariationPointwiseSameCarrierPaymentReceipt": True,
        },
        "does_not_accept": [
            "raw_unlocalized_Riesz_measure_target",
            "annular_output_packet_identity_missing",
            "annular_event_stream_not_locked_to_C7_route_stream",
            "eventRadiusPayment_not_five_frame_tracefree_angular_event_pay",
            "routeActiveTail_budget_spent_on_five_frame_event_pay_without_exchange",
            "five_frame_event_pay_bounded_comparison_missing",
            "annular_bandlimit_chosen_after_payoff",
            "output_packet_support_not_same_annular_carrier",
            "signed_moment_used_as_total_variation",
            "low_high_leakage_after_projection_unpaid",
            "cutoff_commutator_tail_payment_missing",
            "selected_projected_riesz_psd_trace_owner_preimage_prefix_inequality_missing",
            "one_PSD_trace_packet_reused_by_many_selected_invoices",
            "CZ_measure_L1_variation_unpaid",
            "Besov_BV_or_CF_import",
            "target_defined_annular_atoms",
        ],
    },
    "route1_annular_output_packet_tracefree_identity_source": {
        "requires": {
            "route1_projected_formula_source": True,
            "action_target_source_inferred_from_route1_packet_facts": True,
            "route1_packet_carries_full_tracefree_tensor_output_data": True,
            "scalar_projected_moment_not_used_as_tensor_total_variation": True,
            "eventRadiusPayment_eq_projectedTracefreeAnnularOutputVariation": True,
            "same_selected_prefix_map_fixed_before_payoff": True,
            "annular_projected_packet_identified_with_nonadaptive_event_stream": True,
            "selected_target_uses_annular_bandlimited_output_packet": True,
            "tracefree_tensor_total_variation_not_signed_moment": True,
            "cutoff_low_high_tails_paid_same_stream": True,
            "no_target_defined_output_packet": True,
            "not_besov_BV_productL2_or_CF_import": True,
        },
        "concludes": {
            "Route1AnnularOutputPacketTracefreeIdentitySource": True,
            "Route1AnnularOutputEventStreamIdentityReceipt": True,
            "FiveFrameRouteTailExchangeReceipt": True,
            "FiveFrameRouteTailExchangeTheorem": True,
        },
        "does_not_accept": [
            "downstream_identity_receipt_assumed_without_source_certificate",
            "action_target_source_supplied_by_check_menu",
            "route1_formula_only_provides_scalar_projected_moment",
            "scalar_projected_moment_used_as_total_variation",
            "signed_projected_moment_used_as_total_variation",
            "rank_one_scalar_functional_used_for_five_dimensional_tensor_target",
            "linear_observable_coercivity_receipt_missing",
            "annular_output_packet_identity_missing",
            "annular_event_stream_not_locked_to_C7_route_stream",
            "target_defined_annular_output_packet",
            "post_payoff_prefix_map",
            "Besov_BV_productL2_or_CF_import",
        ],
    },
    "route1_annular_output_event_stream_identity": {
        "requires": {
            "route1_projected_formula_source": True,
            "eventRadiusPayment_eq_projectedTracefreeAnnularOutputVariation": True,
            "same_selected_prefix_map_fixed_before_payoff": True,
            "annular_projected_packet_identified_with_nonadaptive_event_stream": True,
            "selected_target_uses_annular_bandlimited_output_packet": True,
            "tracefree_tensor_total_variation_not_signed_moment": True,
            "cutoff_low_high_tails_paid_same_stream": True,
            "no_target_defined_output_packet": True,
            "not_besov_BV_productL2_or_CF_import": True,
        },
        "concludes": {
            "Route1AnnularOutputEventStreamIdentityReceipt": True,
            "FiveFrameRouteTailExchangeReceipt": True,
            "FiveFrameRouteTailExchangeTheorem": True,
        },
        "does_not_accept": [
            "route1_formula_only_provides_scalar_projected_moment",
            "scalar_projected_moment_used_as_total_variation",
            "signed_projected_moment_used_as_total_variation",
            "annular_output_packet_identity_missing",
            "annular_event_stream_not_locked_to_C7_route_stream",
            "eventRadiusPayment_not_five_frame_tracefree_angular_event_pay",
            "routeActiveTail_budget_spent_on_five_frame_event_pay_without_exchange",
            "five_frame_event_pay_bounded_comparison_missing",
            "harmonic_five_frame_event_pay_with_summable_route_tail",
            "target_defined_annular_output_packet",
            "post_payoff_prefix_map",
            "Besov_BV_productL2_or_CF_import",
        ],
    },
    "tracefree_variation_psd_matrix_defect_payment": {
        "requires": {
            "preprojection_PSD_matrix_defect": True,
            "trace_dominates_tracefree_matrix_variation": True,
            "selected_C7_reads_preprojection_stress": True,
            "owner_preimage_no_reuse": True,
            "Leray_Riesz_projection_L1_payment_or_not_needed": True,
            "not_scalar_energy_defect_disguise": True,
            "not_CF_direction_coherence_import": True,
        },
        "concludes": {
            "TraceFreeVariationPSDMatrixDefectPaymentReceipt": True,
            "TraceFreeVariationPointwiseSameCarrierPaymentReceipt": True,
        },
        "does_not_accept": [
            "PSD_trace_pays_preprojection_only",
            "projected_angular_target_after_Leray_Riesz",
            "Leray_Riesz_projection_L1_payment_missing",
            "positive_trace_measure_only",
            "CZ_measure_L1_variation_unpaid",
            "target_moved_before_projection_without_identity",
            "scalar_energy_defect_disguise",
            "CF_or_direction_coherence",
            "H_measure_wave_cone_only",
        ],
    },
    "tracefree_variation_projected_target_preprojection_identity": {
        "requires": {
            "tracefree_variation_psd_matrix_defect_payment": True,
            "selected_C7_projected_target_is_preprojection_PSD_fiber": True,
            "selected_C7_reads_preprojection_stress": True,
            "owner_preimage_no_reuse": True,
            "projection_kernel_fixed_before_payoff": True,
            "no_Leray_Riesz_L1_payment_hidden_in_identity": True,
            "not_CF_direction_coherence_import": True,
        },
        "concludes": {
            "TraceFreeVariationProjectedTargetPreprojectionIdentityReceipt": True,
            "TraceFreeVariationPSDMatrixDefectPaymentReceipt": True,
            "TraceFreeVariationPointwiseSameCarrierPaymentReceipt": True,
        },
        "does_not_accept": [
            "selected_target_still_projected_riesz_angular_moment",
            "preprojection_identity_missing",
            "moving_target_changes_equation_identity",
            "PSD_trace_pays_preprojection_only",
            "Leray_Riesz_projection_L1_payment_missing",
            "target_moved_before_projection_without_identity",
            "pressure_riesz_degree_zero_carrier_only",
            "CF_or_direction_coherence",
        ],
    },
    "tracefree_variation_beta_square_carleson_transfer": {
        "requires": {
            "tracefree_variation_same_carrier_fresh_no_reuse_carleson": True,
            "beta_square_carleson_available_on_same_carrier": True,
            "same_bad_center_tree_matches_selected_C7_tracefree_stream": True,
            "tracefree_atoms_identified_with_beta_event_prices": True,
            "absolute_tracefree_prefix_dominated_by_beta_square_event_budget": True,
            "no_square_to_linear_summability_laundering": True,
            "diagonal_dini_tracefree_stream_excluded_by_mechanism": True,
            "not_only_same_tree_beta_carleson_incidence": True,
        },
        "concludes": {
            "TraceFreeVariationBetaSquareCarlesonTransferReceipt": True,
            "TraceFreeVariationSameCarrierFreshNoReuseCarlesonReceipt": True,
            "TraceFreeVariationC7CofinalOwnerPrefixBudget": True,
        },
        "does_not_accept": [
            "beta_square_carleson_available_only",
            "same_tree_beta_carleson_incidence_only",
            "square_budget_finite_but_linear_prefix_overflows",
            "dini_square_carleson_but_L1_diverges",
            "absolute_variation_not_dominated_by_beta_square_budget",
            "diagonal_dini_tracefree_stream_still_admissible",
            "besov_B0_1_1_or_BV_hidden_input",
            "product_L2_or_global_L4_disguise",
        ],
    },
    "fresh_annular_same_source_morphology_transfer": {
        "requires": {
            "old_observable_bound_on_this_separated_source": True,
            "observable_carrier_is_separated_source": True,
            "no_proxy_carrier_substitution": True,
            "total_fresh_annular_carrier_morphology_proof": True,
            "not_monotone_tail": True,
            "not_scalar_measure": True,
            "not_uniform_enstrophy_disguise": True,
            "same_separated_source": True,
        },
        "concludes": {
            "C7FreshAnnularSameSourceMorphologyTransferReceipt": True,
            "C7FreshAnnularNonDisguiseReceiptFromSeparatedSource": True,
        },
        "does_not_accept": [
            "anisotropic_non_scalar_proxy",
            "localized_Avisc_surplus",
            "level_set_gain",
            "coherent_stretch_depletion",
            "proxy_carrier_may_differ_from_separated_source",
            "same_source_label_only",
        ],
    },
    "KRZ_one_component": {
        "requires": {
            "suitable_weak_solution": True,
            "full_CKN_bound_M": True,
            "one_component_smallness": "r^-2 integral |u3|^3 <= eps(M)",
        },
        "concludes": {"regular_at_center": True},
        "does_not_accept": [
            "amplitude_ratio_only",
            "CKN_lower_bound_only",
            "pointwise_TypeI_only",
        ],
    },
    "ESS": {
        "requires": {
            "global_Linfty_t_L3_x_bound": True,
        },
        "concludes": {"regularity_from_l3_endpoint": True},
        "does_not_accept": [
            "local_L3_bound_on_shrinking_balls",
            "TypeI_amplitude_only",
        ],
    },
    "NRS": {
        "requires": {
            "exact_backward_self_similar_profile": True,
        },
        "concludes": {"rules_out_backward_self_similar_blowup": True},
        "does_not_accept": [
            "amplitude_TypeI_only",
            "Dini_self_similar_like",
        ],
    },
}

OWNER_GEOMETRY_CORE_PROFILE = {
    "receipt_key": "owner_geometry_core_receipts",
    "receipt_label": "owner_geometry_core",
    "required_fields": [
        "owner_map_timing",
        "output_scale_owner",
        "selected_prefix_preimage",
        "bounded_projection_multiplicity",
        "same_carrier_owner_budget",
        "anti_laundering",
        "consumed_by",
    ],
    "expected_consumers": [
        "C7CarrierRadiusCanonicalOwnerSeparationReceipt."
        "ofOwnerPreimageGeometryCore",
        "NonadaptiveAnnularC7SourceSelection."
        "ofCoronaDuhamelCompletionAndOwnerPreimageGeometryCore",
        "NonadaptiveAnnularC7SourceSelection."
        "ofCoronaDuhamelCompletionAndScaledTransferResidual",
        "SparseHighHighGhostNonParabolicSelectedC7Mechanism."
        "ofCoronaDuhamelCompletionAndOwnerPreimageGeometryCore",
    ],
    "incomplete_reason": (
        "owner-geometry core requires the owner map, output-scale ownership, "
        "selected-prefix preimage, projection multiplicity, same-carrier owner "
        "budget, and anti-laundering payload"
    ),
    "wrong_consumer_reason": (
        "owner-geometry receipt is not bound to the reduced TICK668 "
        "owner-core consumer edge"
    ),
    "confuser_sets": [
        {
            "type": "completion_backed_channel_laundering",
            "fields": [
                "productionSourceFixedBeforeOwnerMap",
                "pressureReserveSeparatedFromOwnerBudget",
                "partitionFixedBeforeOwnerPreimage",
                "sectionIdentityFixedBeforeOwnerPreimage",
                "noReuseSeparatedFromOwnerBudget",
                "C7CompletionBackedChannelSeparationReceipt",
            ],
            "unless_present": ["selected_prefix_preimage"],
            "reason": (
                "completion-backed channel separation does not supply the "
                "owner-preimage geometry core"
            ),
        },
        {
            "type": "upstream_numeric_or_currency_laundering",
            "fields": [
                "routeActiveTail_nonnegative",
                "selectedNodeRadius_nonnegative",
                "atomChargeNormalizesPackingCurrency",
                "atomBudgetNormalizesPackingCurrency",
                "scaled_transfer_numeric_receipt",
            ],
            "unless_present": ["owner_map_timing"],
            "reason": (
                "radius nonnegativity and scaled currency are upstream of the "
                "owner-geometry core and cannot discharge it"
            ),
        },
    ],
}

FRESH_ANNULAR_ANTI_LAUNDERING_PROFILE = {
    "receipt_key": "fresh_annular_anti_laundering_receipts",
    "receipt_label": "fresh_annular_anti_laundering",
    "required_fields": [
        "not_monotone_tail",
        "not_scalar_measure",
        "not_uniform_enstrophy_disguise",
        "source_selection_not_declaration_only",
        "same_separated_source",
        "consumed_by",
    ],
    "expected_consumers": [
        "C7AnnularSelectionScaledCurrencyBridgeWithSameSourceAntiLaundering",
        "C7OwnerGeometryResidualBridgeFromFreshAnnularChargeSeparatedSource."
        "ofOwnerLineageAndAntiLaundering",
        "C7OwnerGeometryResidualBridgeFromFreshAnnularChargeSeparatedSource."
        "ofCarrierRadiusPositiveIdentityAndAntiLaundering",
        "C7OwnerGeometryResidualBridgeFromFreshAnnularChargeSeparatedSource."
        "ofCarrierRadiusPositiveIdentitySameTreeInvoiceAndAntiLaundering",
    ],
    "incomplete_reason": (
        "fresh-annular anti-laundering requires non-monotone-tail, "
        "non-scalar-measure, non-uniform-enstrophy, non-declaration evidence "
        "on the same separated source"
    ),
    "wrong_consumer_reason": (
        "anti-laundering receipt is not bound to the fresh-annular owner "
        "residual bridge consumer edge"
    ),
    "confuser_sets": [
        {
            "type": "separated_source_substrate_laundering",
            "fields": [
                "FreshAnnularChargeSeparatedSourceFromIndexedCarrier",
                "fresh_annular_extraction",
                "fresh_charge_prefix_budget",
                "same_tree_invoice",
            ],
            "unless_present": ["not_monotone_tail"],
            "reason": (
                "fresh-annular extraction is the substrate; it does not by "
                "itself prove anti-laundering/non-disguise"
            ),
        },
        {
            "type": "identity_owner_provenance_laundering",
            "fields": [
                "C7IdentityOwnerTransferProvenance",
                "ownerOfEvent_eq_id",
                "bounded_owner_multiplicity",
            ],
            "unless_present": ["source_selection_not_declaration_only"],
            "reason": (
                "identity owner provenance pays owner fibers, not source "
                "nondeclaration or anti-laundering"
            ),
        },
    ],
}

FRESH_ANNULAR_NON_DISGUISE_PROFILE = {
    "receipt_key": "fresh_annular_non_disguise_receipts",
    "receipt_label": "fresh_annular_non_disguise",
    "required_fields": [
        "not_monotone_tail",
        "not_scalar_measure",
        "not_uniform_enstrophy_disguise",
        "same_separated_source",
        "consumed_by",
    ],
    "expected_consumers": [
        "C7FreshAnnularAntiLaunderingReceiptFromSeparatedSource."
        "ofNonDisguiseAndSourceNondeclaration",
        "C7FreshAnnularNonDisguiseReceiptFromSeparatedSource."
        "ofNonadaptiveAnnularC7SourceSelection",
        "C7FreshAnnularNonDisguiseReceiptFromSeparatedSource."
        "ofSameSourceMorphologyTransfer",
    ],
    "incomplete_reason": (
        "fresh-annular non-disguise morphology requires non-monotone-tail, "
        "non-scalar-measure, and non-uniform-enstrophy evidence on the same "
        "separated source"
    ),
    "wrong_consumer_reason": (
        "non-disguise morphology receipt is not bound to the fresh-annular "
        "anti-laundering split consumer edge"
    ),
    "confuser_sets": [
        {
            "type": "monotone_tail_laundering",
            "fields": [
                "tail_bound",
                "monotone_tail",
                "decaying_tail_budget",
            ],
            "unless_present": ["not_monotone_tail"],
            "reason": (
                "a monotone tail estimate can be the opposite of the "
                "fresh-annular non-disguise morphology receipt"
            ),
        },
        {
            "type": "scalar_measure_laundering",
            "fields": [
                "scalar_measure",
                "finite_measure",
                "mass_budget",
            ],
            "unless_present": ["not_scalar_measure"],
            "reason": (
                "scalar measure or finite budget language does not certify "
                "same-source fresh-annular morphology"
            ),
        },
        {
            "type": "uniform_enstrophy_laundering",
            "fields": [
                "uniform_enstrophy",
                "energy_budget",
                "dissipation_bound",
            ],
            "unless_present": ["not_uniform_enstrophy_disguise"],
            "reason": (
                "uniform enstrophy or energy budget control is a confuser "
                "unless the non-disguise field is paid explicitly"
            ),
        },
        {
            "type": "anisotropy_proxy_laundering",
            "fields": [
                "anisotropic_non_scalar_proxy",
                "localized_Avisc_surplus",
                "level_set_gain",
                "coherent_stretch_depletion",
            ],
            "unless_present": [
                "total_fresh_annular_carrier_morphology_proof",
            ],
            "reason": (
                "a non-scalar anisotropy proxy on another carrier does not "
                "certify non-scalar morphology of the total same separated "
                "fresh-annular source"
            ),
        },
        {
            "type": "same_source_morphology_transfer_label_laundering",
            "fields": [
                "old_observable_bound_on_this_separated_source",
                "observable_carrier_is_separated_source",
                "no_proxy_carrier_substitution",
                "same_source_label_only",
            ],
            "unless_present": [
                "total_fresh_annular_carrier_morphology_proof",
            ],
            "reason": (
                "same-source transfer labels do not certify morphology unless "
                "the total fresh-annular carrier morphology proof is paid"
            ),
        },
    ],
}

FRESH_ANNULAR_INNOVATION_PROFILE = {
    "receipt_key": "fresh_annular_innovation_receipts",
    "receipt_label": "fresh_annular_innovation",
    "required_fields": [
        "invoice_filtration",
        "coarse_predictable_part",
        "innovation_part",
        "innovation_mass_lower_bound",
        "same_source_binding",
        "nondeclaration_binding",
        "non_disguise_morphology_consequence",
        "source_nondeclaration_timing_consequence",
        "consumed_by",
    ],
    "expected_consumers": [
        "C7FreshAnnularAntiLaunderingReceiptFromSeparatedSource",
        "C7OwnerGeometryResidualBridgeFromFreshAnnularChargeSeparatedSource",
    ],
    "incomplete_reason": (
        "fresh-annular innovation requires a fixed invoice filtration, a "
        "coarse predictable envelope, a residual innovation part, a positive "
        "selected-event lower bound, same-source binding, nondeclaration "
        "timing, and the anti-laundering consequences it is meant to pay"
    ),
    "wrong_consumer_reason": (
        "fresh-annular innovation receipt is not bound to the anti-laundering "
        "or owner-residual bridge consumer edge"
    ),
    "confuser_sets": [
        {
            "type": "prefix_budget_laundering",
            "fields": [
                "fresh_charge_prefix_budget",
                "FreshAnnularChargeSeparatedSourceFromIndexedCarrier",
                "same_tree_invoice",
            ],
            "unless_present": ["innovation_part"],
            "reason": (
                "the separated-source prefix budget is compatible with a "
                "monotone scalar tail; it is not an innovation certificate"
            ),
        },
        {
            "type": "post_payoff_innovation_laundering",
            "fields": [
                "realized_radius_sum",
                "post_payoff_selection",
                "selected_after_payoff",
            ],
            "unless_present": ["invoice_filtration"],
            "reason": (
                "an innovation chosen after the selected payoff does not pay "
                "the nonadaptive anti-laundering edge"
            ),
        },
        {
            "type": "same_source_missing_innovation",
            "fields": [
                "innovation_mass_lower_bound",
                "orthogonal_residual",
            ],
            "unless_present": ["same_source_binding"],
            "reason": (
                "innovation on a different source cannot feed the same-source "
                "owner-lineage bridge"
            ),
        },
    ],
}

SECTION_FIXED_UNSIGNED_VARIATION_PROFILE = {
    "receipt_key": "section_fixed_unsigned_variation_receipts",
    "receipt_label": "section_fixed_unsigned_variation",
    "required_fields": [
        "lower_envelope_uses_section",
        "parent_crown_fixed_by_section",
        "unshadowed_crown_fixed_by_section",
        "child_shadow_crown_fixed_by_section",
        "localized_unsigned_variation_measure",
        "variation_measure_fixed_before_payoff",
        "positive_variation_before_route_budget",
        "no_parent_invoice_positive_part_selection",
        "child_shadow_not_from_parent_deficit",
        "unshadowed_mass_pays_production",
        "child_shadow_mass_pays_inherited_reserve",
        "same_event_stream_binding",
        "consumed_by",
    ],
    "expected_consumers": [
        "DuhamelSectionFixedUnsignedCrownMeasureReceipt",
        "UnsignedLocalizedCrownSourceFromDuhamelSection",
        "CoronaDuhamelCrownMeasureSplitSource.ofSectionFixedUnsignedReceipt",
    ],
    "incomplete_reason": (
        "section-fixed unsigned variation requires extensional localized "
        "unsigned measure data on parent/unshadowed/child crowns, fixed by "
        "the Duhamel section before payoff, plus production/inherited-reserve "
        "payment and same-event-stream binding"
    ),
    "wrong_consumer_reason": (
        "section-fixed unsigned variation receipt is not bound to the "
        "Duhamel section unsigned-crown consumer edge"
    ),
    "confuser_sets": [
        {
            "type": "scalar_lower_envelope_laundering",
            "fields": [
                "ResidualFreshSameLedgerDuhamelLowerEnvelopeSource",
                "event_lower_envelope",
                "same_signed_event_ledger",
                "quadratic_reserve",
                "lowerEnvelopeSourceUsesSectionIdentity",
            ],
            "unless_present": ["localized_unsigned_variation_measure"],
            "reason": (
                "signed scalar lower-envelope and reserve data do not "
                "determine the localized unsigned parent/child mass"
            ),
        },
        {
            "type": "determinacy_shortcut_laundering",
            "fields": [
                "DuhamelLowerEnvelopeUnsignedVariationRealization",
                "SectionFixedUnsignedParentMassDeterminedByLowerEnvelope",
                "parent_mass_determined_by_section",
                "canonical_parent_mass",
            ],
            "unless_present": ["not_determinacy_shortcut"],
            "reason": (
                "the existing oracle ambiguity kills determinacy from lower "
                "envelope and section identity alone"
            ),
        },
        {
            "type": "crown_label_only_laundering",
            "fields": [
                "parentCrownFromSectionIncidence",
                "unshadowedChildSplitFromSectionIncidence",
                "crown_sets_fixed",
            ],
            "unless_present": ["localized_unsigned_variation_measure"],
            "reason": (
                "fixed crown labels are not a localized unsigned variation "
                "measure"
            ),
        },
        {
            "type": "parent_invoice_positive_part_laundering",
            "fields": [
                "parent_invoice",
                "parent_deficit",
                "posthoc_positive_part_selection",
                "selected_after_payoff",
            ],
            "unless_present": ["no_parent_invoice_positive_part_selection"],
            "reason": (
                "parent-invoice or post-payoff positive-part selection cannot "
                "construct the section-fixed unsigned source"
            ),
        },
    ],
}

NS_SCALED_TRANSFER_NUMERIC_PROFILE = {
    "expected_source_quantity": "hCarrier.nodeRadius",
    "expected_event_index_map": "hEvents.eventToBadNode",
    "expected_consumers": [
        "C7RouteActiveTailNonnegativeReceipt."
        "ofPointwiseEventNodeRadiusNonnegative"
    ],
    "prop_only_fields": [
        "nodeRadiusPositiveOnSelected",
        "prop_membership_input",
        "eventToBadNodeLandsInSelectedNodes",
        "betaNonnegative",
        "beta_square_nonnegative",
    ],
    "wrong_edge_reason": (
        "numeric receipt is not bound to the event-node radius edge consumed "
        "by route-tail nonnegativity"
    ),
}

PDE_SINGLE_SPEND_PROFILE = {
    "channel_keywords": {
        "production": ("production", "source", "gain", "local"),
        "invoice": ("invoice", "radius", "carleson", "charge"),
        "pressure_reserve": ("pressure", "collar", "harmonic", "moment"),
        "duhamel_reserve": ("duhamel", "heat", "forcing"),
        "inherited_reserve": ("inherited", "descendant", "child"),
        "partition": (
            "partition",
            "totalbudget",
            "total_budget",
            "single_spend",
            "singlespend",
        ),
        "section_identity": (
            "sectionidentity",
            "section_identity",
            "sectionincidence",
            "section_incidence",
            "sectionindex",
            "section_index",
        ),
        "timing": ("timing", "before", "fixed", "preselected", "precommitted", "auditindex"),
        "no_reuse": (
            "norepeated",
            "no_repeated",
            "noncharge",
            "nonchargeability",
            "noreuse",
            "rebill",
        ),
    },
    "spend_variable_keywords": {
        "production": ("productionspend", "production_spend"),
        "invoice": (
            "invoicespend",
            "invoice_spend",
            "parentradiusinvoicespend",
            "parent_radius_invoice_spend",
        ),
        "pressure_reserve": ("pressurereservespend", "pressure_reserve_spend"),
        "duhamel_reserve": ("duhamelreservespend", "duhamel_reserve_spend"),
        "inherited_reserve": ("inheritedreservespend", "inherited_reserve_spend"),
    },
    "blocking_channels": (
        "production",
        "invoice",
        "pressure_reserve",
        "duhamel_reserve",
        "inherited_reserve",
        "partition",
        "section_identity",
    ),
}

TRANSFORM_HINTS = {
    "LIMIT_PASSAGE": ["REGULAR", "TIME_FINITE"],
    "COMMUTATOR": ["LINEARIZE", "DISCRETE"],
    "SOBOLEV": ["REGULAR", "DIMENSION_REDUCE"],
    "INTERPOLATION": ["SCALAR_RESTRICT", "DIMENSION_REDUCE"],
    "COERCIVITY": ["LINEARIZE", "SCALAR_RESTRICT"],
    "PROPAGATION": ["TIME_FINITE", "LINEARIZE"],
    "HOLDER": ["SCALAR_RESTRICT", "DIMENSION_REDUCE"],
    "PACKING": ["DISCRETE", "DIMENSION_REDUCE", "TIME_FINITE"],
    "AUXILIARY": ["DIMENSION_REDUCE", "LINEARIZE", "DISCRETE"],
    "UNKNOWN": ["DIMENSION_REDUCE", "LINEARIZE"],
}


def safe_slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", text).strip("_")[:120]


def _json_or_file(raw: str | Path | None) -> Any:
    """Parse a JSON literal or a path containing JSON."""
    if raw is None:
        return None
    text = str(raw)
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return json.loads(stripped)
    return json.loads(Path(text).read_text(encoding="utf-8"))


def _find_live_lean_decl(target: str) -> dict[str, Any] | None:
    """Best-effort source-truth fallback when the workmap is stale.

    This intentionally stays shallow: it finds the declaration line and, for
    structures/classes, extracts displayed field names and type snippets.  It is
    a context aid, not a parser or theorem prover.
    """
    decl_modifiers = r"(?:(?:noncomputable|private|protected|unsafe|partial)\s+)*"
    decl_re = re.compile(
        rf"^\s*{decl_modifiers}(structure|class|theorem|def|lemma|abbrev)\s+"
        rf"{re.escape(target)}\b"
    )
    next_decl_re = re.compile(
        rf"^\s*{decl_modifiers}"
        r"(structure|class|theorem|def|lemma|abbrev|opaque|axiom|inductive)\s+"
    )
    field_re = re.compile(r"^\s{2,}([A-Za-z_][A-Za-z0-9_']*)\s*:\s*(.*)$")

    def preceding_doc_comment(lines: list[str], decl_idx: int) -> str:
        j = decl_idx - 1
        while j >= 0 and not lines[j].strip():
            j -= 1
        if j < 0 or not lines[j].strip().endswith("-/"):
            return ""
        parts: list[str] = []
        while j >= 0:
            parts.append(lines[j])
            if "/--" in lines[j]:
                return "\n".join(reversed(parts))
            j -= 1
        return ""

    for path in LEAN_ROOT.glob("*.lean"):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for i, line in enumerate(lines):
            match = decl_re.match(line)
            if not match:
                continue
            kind = match.group(1)
            block: list[str] = []
            for later in lines[i + 1:]:
                if next_decl_re.match(later) and not later.startswith("  "):
                    break
                block.append(later)
            fields: list[dict[str, str]] = []
            current: dict[str, str] | None = None
            for raw in block:
                field_match = field_re.match(raw)
                if field_match:
                    if current:
                        fields.append(current)
                    current = {
                        "name": field_match.group(1),
                        "type": field_match.group(2).strip(),
                    }
                    continue
                if current and raw.startswith("    "):
                    current["type"] = (current["type"] + " " + raw.strip()).strip()
            if current:
                fields.append(current)
            header_text = " ".join([line] + block[:4])
            parent_fields: list[dict[str, str]] = []
            parent_match = re.search(
                r"\bextends\s+([A-Za-z_][A-Za-z0-9_'.]*)", header_text
            )
            if parent_match:
                parent_name = parent_match.group(1).split(".")[-1]
                if parent_name and parent_name != target:
                    parent_ctx = _find_live_lean_decl(parent_name)
                    if parent_ctx:
                        for parent_field in parent_ctx.get("fields", []):
                            if isinstance(parent_field, dict):
                                copied = dict(parent_field)
                                copied.setdefault("inherited_from", parent_name)
                                parent_fields.append(copied)
            combined_fields = fields + parent_fields
            return {
                "found": True,
                "source": "live_lean_fallback",
                "target": target,
                "kind": kind,
                "doc": preceding_doc_comment(lines, i),
                "file": str(path.relative_to(REPO)),
                "line": i + 1,
                "n_fields": len(combined_fields),
                "fields": combined_fields[:160],
            }
    return None


def load_target_context(target: str, field: str | None) -> dict[str, Any]:
    from typed_endpoint_pack import (
        find_theorems_using_field,
        find_type_constructors,
        find_type_producers,
        load_decl_index,
        load_workmap_target,
        resolve_field,
    )

    live = _find_live_lean_decl(target)
    target_obj = load_workmap_target(target)
    if not target_obj:
        if live:
            return {
                "found": True,
                "target": target,
                "field": field,
                "target_file": live.get("file"),
                "source": live.get("source"),
                "kind": live.get("kind"),
                "doc": live.get("doc") or "",
                "line": live.get("line"),
                "n_fields": live.get("n_fields"),
                "fields": live.get("fields") or [],
                "field_info": None,
                "constructors": [],
                "type_producers": [],
                "nearby_theorems": [],
            }
        return {
            "found": False,
            "target": target,
            "field": field,
            "reason": "target not found in workmap",
        }
    field_info = resolve_field(target_obj, field) if field else None
    decl_index = load_decl_index()
    constructors: list[dict[str, Any]] = []
    type_producers: list[dict[str, Any]] = []
    nearby: list[dict[str, Any]] = []
    if field_info:
        constructors = find_type_constructors(field_info["type_head"], decl_index)
        type_producers = find_type_producers(field_info["type_head"], top_n=10)
        nearby = find_theorems_using_field(
            field_info["field_name"], field_info["type_head"], top_n=10)
    return {
        "found": True,
        "target": target,
        "field": field,
        "target_file": (live or {}).get("file") or target_obj.get("file"),
        "source": "workmap+live_lean" if live else "workmap",
        "kind": (live or {}).get("kind"),
        "doc": (live or {}).get("doc") or target_obj.get("doc") or "",
        "line": (live or {}).get("line"),
        "endpoint_exposure": target_obj.get("endpoint_exposure"),
        "n_downstream_users": target_obj.get("n_downstream_users"),
        "priority": target_obj.get("closure_priority_score")
            or target_obj.get("leverage_score")
            or target_obj.get("priority"),
        "n_fields": (live or {}).get("n_fields") or target_obj.get("n_fields"),
        "fields": ((live or {}).get("fields") or target_obj.get("fields") or [])[:160],
        "field_info": field_info,
        "constructors": constructors[:5],
        "type_producers": type_producers[:10],
        "nearby_theorems": nearby[:10],
    }


def classify_gap_local(target: str, field: str | None) -> dict[str, Any]:
    if not field:
        return {
            "gap_type": "UNKNOWN",
            "confidence": "low",
            "rationale": "No field supplied.",
            "classifier": "pde_estimate_workbench",
        }
    from gap_typed_prompter import classify_gap
    return classify_gap(target, field, dry_run=True)


def _compact_query_fragment(value: Any, *, budget: int = 900) -> str:
    """Small deterministic stringifier for semantic-query side information."""
    try:
        raw = json.dumps(value, sort_keys=True, ensure_ascii=True)
    except TypeError:
        raw = str(value)
    return raw[:budget]


def _apn_query_text(
    target_name: str,
    field: str | None,
    *,
    context: dict[str, Any] | None = None,
    gap: dict[str, Any] | None = None,
    basin_context: dict[str, Any] | None = None,
    pde_ops: list[dict[str, Any]] | None = None,
    candidate_inequalities: list[str] | None = None,
    target_currency: str | None = None,
) -> str:
    """Build a semantic APN query from the actual PDE packet, not names alone."""
    terms: list[str] = [target_name, field or "", target_currency or ""]
    if gap:
        terms.append(str(gap.get("gap_type") or ""))
        terms.append(str(gap.get("rationale") or ""))
    if context:
        terms.append(str(context.get("doc") or ""))
        for item in context.get("fields", [])[:20]:
            if isinstance(item, dict):
                terms.append(str(item.get("name") or ""))
                terms.append(str(item.get("type") or ""))
        for item in context.get("constructors", [])[:8]:
            if isinstance(item, dict):
                terms.append(str(item.get("type_head") or ""))
    if basin_context:
        preferred = (
            "tag_fingerprint",
            "typed_failure_log",
            "manifest_aliases",
            "nearby_refutations",
            "open_obligation_proximity",
        )
        used = False
        for key in preferred:
            if key in basin_context:
                terms.append(_compact_query_fragment({key: basin_context.get(key)}))
                used = True
        if not used:
            terms.append(_compact_query_fragment(basin_context))
    for op in pde_ops or []:
        terms.append(str(op.get("name") or op.get("op_id") or ""))
        terms.append(str(op.get("rationale") or ""))
        terms.append(str(op.get("gate_mechanization") or ""))
    terms.extend(str(x) for x in candidate_inequalities or [])
    query = " ".join(t for t in terms if t).strip()
    return query[:1800]


def _load_apn_semantic_for_target(
    target_name: str,
    field: str | None,
    *,
    context: dict[str, Any] | None = None,
    gap: dict[str, Any] | None = None,
    basin_context: dict[str, Any] | None = None,
    pde_ops: list[dict[str, Any]] | None = None,
    candidate_inequalities: list[str] | None = None,
    target_currency: str | None = None,
    threshold: float = 0.55,
    top_k: int = 5,
) -> dict | None:
    """Workbench consumer of the APN cross-corpus bridge.

    Builds a free-text query from the PDE packet and returns both nearest APN
    declarations and explicit ``ns_apn_bridge`` edges. Graceful degradation —
    never raises into the workbench.
    """
    try:
        from ztare.research_director.apn_semantic import apn_semantic_neighbours
    except Exception:
        return {"available": False, "skip_reason": "apn_semantic module not importable"}
    query = _apn_query_text(
        target_name, field, context=context, gap=gap, basin_context=basin_context,
        pde_ops=pde_ops, candidate_inequalities=candidate_inequalities,
        target_currency=target_currency,
    )
    if not query:
        return {"available": False, "skip_reason": "empty target/field"}
    try:
        hits, corpus_size, filtered_size, skip_reason = apn_semantic_neighbours(
            query, threshold=threshold, top_k=top_k,
        )
    except Exception as e:
        return {"available": False, "skip_reason": f"apn lookup failed: {e!r}"}
    hit_rows = [
        {
            "id": h.id, "name": h.name, "kind": h.kind, "domain": h.domain,
            "file": h.file, "variant_tag": h.variant_tag,
            "cosine": h.cosine, "snippet": h.snippet,
        }
        for h in hits
    ]
    bridge_edges = [
        {
            "@type": "ns_apn_bridge",
            "src": target_name,
            "src_field": field,
            "dst_apn": h["id"],
            "cosine": h["cosine"],
            "apn_name": h["name"],
            "apn_kind": h["kind"],
            "apn_domain": h["domain"],
            "apn_file": h["file"],
            "apn_variant_tag": h["variant_tag"],
        }
        for h in hit_rows
    ]
    return {
        "available": True,
        "query": query,
        "threshold": threshold,
        "top_k": top_k,
        "corpus_size": corpus_size,
        "filtered_size": filtered_size,
        "skip_reason": skip_reason,
        "hits": hit_rows,
        "bridge_edges": bridge_edges,
    }


def _load_basin_context_for_target(target_name: str) -> dict | None:
    """Workbench consumer of the enriched-basin signals (2026-05-26 turbocharge).

    Defers to enrich_basin_with_proof_history.summarize_basin_context_for_target
    when present. Returns None if the enriched basin or the helper is unavailable
    (graceful degradation — never raises into the workbench's deterministic flow).
    """
    try:
        import importlib.util
        helper_path = REPO / "projects" / "ns_millennium_hunt" / "scripts" / "enrich_basin_with_proof_history.py"
        if not helper_path.exists():
            return None
        spec = importlib.util.spec_from_file_location("_basin_history_helper", helper_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "summarize_basin_context_for_target"):
            return mod.summarize_basin_context_for_target(target_name)
    except Exception:
        return None
    return None


def fetch_lemmas(gap_type: str, top: int) -> list[dict[str, Any]]:
    from gap_typed_prompter import fetch_gap_specific_lemmas
    lemmas = fetch_gap_specific_lemmas(gap_type, top_n=top)
    return [
        {
            "name": lemma.get("name"),
            "file": lemma.get("file"),
            "shapes": lemma.get("shapes", []),
            "preview": (lemma.get("preview") or "")[:240],
        }
        for lemma in lemmas
    ]


AUXILIARY_FAMILY_FALLBACKS: list[dict[str, Any]] = [
    {
        "family": "exponential_majorant",
        "mathematical_form": "B(x) = C1 exp(C2 phi(x)) for a convex phi",
        "gap_types": ["PROPAGATION", "COERCIVITY", "AUXILIARY"],
        "source_mathematician": ["maximum principle", "barrier method"],
        "typical_use_pattern": "turn local growth into a propagated envelope",
        "ns_track_b_relevance": "pressure or cutoff growth envelopes that must be paid outside the target spend",
    },
    {
        "family": "cutoff_partition",
        "mathematical_form": "psi in C_c^infty, 0 <= psi <= 1, psi = 1 on K",
        "gap_types": ["LOCALIZATION", "COMMUTATOR", "AUXILIARY", "PROPAGATION"],
        "source_mathematician": ["Caccioppoli", "local energy method"],
        "typical_use_pattern": "separate interior payment from boundary leakage",
        "ns_track_b_relevance": "annular owner fibers, cutoff pressure leakage, and C7 prefix invoices",
    },
    {
        "family": "energy_with_correction",
        "mathematical_form": "E_tilde(t) = E(t) + delta F(t)",
        "gap_types": ["PROPAGATION", "COERCIVITY", "COMMUTATOR"],
        "source_mathematician": ["modified energy", "normal form"],
        "typical_use_pattern": "absorb sign-indefinite terms into a coercive corrected quantity",
        "ns_track_b_relevance": "tests whether signed pressure cancellation can be converted to a positive receipt",
    },
    {
        "family": "monotone_quantity",
        "mathematical_form": "M(t) monotone after choosing the right test object",
        "gap_types": ["PROPAGATION", "LIMIT_PASSAGE", "AUXILIARY"],
        "source_mathematician": ["monotonicity formula"],
        "typical_use_pattern": "replace pointwise control by a one-directional ledger",
        "ns_track_b_relevance": "candidate carrier-local variation budgets that must survive prefix refinement",
    },
    {
        "family": "blowup_profile_renormalization",
        "mathematical_form": "U_hat(s,y) = lambda(t)^alpha U(t, x(t) + lambda(t)y)",
        "gap_types": ["PROPAGATION", "COMPACTNESS", "AUXILIARY"],
        "source_mathematician": ["blowup analysis", "renormalization"],
        "typical_use_pattern": "move a scale-critical failure into a fixed-window profile",
        "ns_track_b_relevance": "tests whether a hostile packet is excluded by profile rigidity rather than hidden CF/BV input",
    },
]


def _fallback_auxiliary_families(gap_type: str, keyword: str | None) -> list[dict[str, Any]]:
    gap = gap_type.upper()
    key = (keyword or "").lower()
    rows = []
    for item in AUXILIARY_FAMILY_FALLBACKS:
        gap_match = gap in {str(x).upper() for x in item.get("gap_types", [])} or gap == "AUXILIARY"
        haystack = " ".join(str(v) for v in item.values()).lower()
        keyword_match = not key or key in haystack
        if gap_match and keyword_match:
            rows.append(item)
    if not rows and gap != "AUXILIARY":
        rows = _fallback_auxiliary_families("AUXILIARY", keyword)
    return rows


def fetch_auxiliary_families(gap_type: str, keyword: str | None, top: int) -> list[dict[str, Any]]:
    try:
        from auxiliary_object_catalog import query_catalog
        families = query_catalog(gap_type=gap_type, keyword=keyword)
        if not families and gap_type != "AUXILIARY":
            families = query_catalog(gap_type="AUXILIARY", keyword=keyword)
    except ModuleNotFoundError:
        families = _fallback_auxiliary_families(gap_type, keyword)
    return [
        {
            "family": item.get("family"),
            "mathematical_form": item.get("mathematical_form"),
            "gap_types": item.get("gap_types", []),
            "source_mathematician": item.get("source_mathematician", []),
            "typical_use_pattern": item.get("typical_use_pattern", ""),
            "ns_track_b_relevance": item.get("ns_track_b_relevance", ""),
        }
        for item in families[:top]
    ]


def suggest_pde_craft_ops(
    gap_type: str,
    target: str,
    field: str | None,
    inequalities: list[str],
    context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Recommend ZTARE PDE estimate-craft primitives for the current surface."""
    from ztare.research_director.pde_estimate_craft_ops import get

    context_terms: list[str] = []
    if context:
        doc = str(context.get("doc", ""))
        if doc:
            context_terms.append(doc)
        for item in context.get("fields", []):
            name = str(item.get("name", ""))
            ftype = str(item.get("type", ""))
            context_terms.append(f"{name} {ftype}")

    raw_haystack = " ".join([
        target,
        field or "",
        *inequalities,
        *context_terms,
    ]).lower()
    haystack = f"{raw_haystack} {raw_haystack.replace('-', '_')}"
    op_ids: list[tuple[str, str]] = []

    if gap_type in {"AUXILIARY", "UNKNOWN", "COERCIVITY"} or any(
        token in haystack
        for token in ("carrier", "localiz", "freshregion", "fresh_region",
                      "eventtent", "event_tent", "gauge", "collar")
    ):
        op_ids.append((
            "pec_a",
            "construct the missing carrier/test object explicitly before proving estimates",
        ))
    if gap_type in {"COERCIVITY", "UNKNOWN"} or any(
        token in haystack
        for token in ("rebill", "endpoint", "sharp", "failure", "counter")
    ):
        op_ids.append((
            "pec_e",
            "build the hostile witness or sharpness model before accepting the route",
        ))
    if gap_type in {"LIMIT_PASSAGE", "PROPAGATION"} or any(
        token in haystack
        for token in ("prefix", "finite", "limit", "inherit", "propagation")
    ):
        op_ids.append((
            "pec_d",
            "name the finite-to-limit or persistence lemma instead of assuming inheritance",
        ))
    if any(
        token in haystack
        for token in (
            "nonadaptive", "non-adaptive", "predeclared", "preselected",
            "fixed before", "fixedbefore", "before payoff", "beforepayoff",
            "before radius", "no post hoc", "noposthoc", "posthoc",
            "source selection", "sourceselection", "selected before",
            "chosen before", "auditindex", "audit index",
        )
    ):
        op_ids.append((
            "pec_i",
            "prove the source/event/window/schedule selection is fixed before payoff",
        ))
    if gap_type == "PACKING" or any(
        token in haystack
        for token in (
            "same-carrier", "same_carrier", "fresh capacity", "fresh_capacity",
            "fresh annular", "fresh_annular", "no reuse", "no_reuse",
            "noreuse", "nonreuse", "rebilling", "rebill", "injection",
            "injective", "packing", "bounded overlap", "bounded_overlap",
            "disjoint", "capacity packet", "monotone reserve",
            "reserve drop", "same capacity", "same_capacity",
        )
    ):
        op_ids.append((
            "pec_j",
            "prove same-carrier fresh packing/no-reuse injection before accepting the route",
        ))
    if any(
        token in haystack
        for token in (
            "phase-space", "phase_space", "phase space", "microlocal",
            "littlewood-paley", "littlewood_paley", "lp tile", "lp_tile",
            "bony tile", "bony_tile", "packet", "tile", "tube",
            "owner map", "ownermap", "owner atom", "owner_atom",
            "ownership", "preimage", "owner preimage", "owner_preimage",
            "event-to-packet", "event_to_packet", "event-to-atom",
            "event_to_atom", "owned event", "owned_event",
            "owned event prefix", "owned_event_prefix",
            "event prefix budget", "event_prefix_budget",
            "event pay", "event_pay", "event stream", "event_stream",
            "selected prefix map", "selected_prefix_map",
            "same selected prefix map", "same_selected_prefix_map",
            "bounded multiplicity", "bounded_multiplicity",
            "material tube", "material_tube", "transported tube",
            "global selected-tree", "global_selected_tree",
            "output-scale", "output_scale", "output packet",
            "output_packet", "full packet", "full_packet",
            "product tile", "product_tile", "bilinear packet",
            "bilinear_packet", "factor reuse", "factor_reuse",
            "factor owner", "factor_owner", "catalyst",
            "low-high", "low_high", "pressure sheath",
            "pressure_sheath",
        )
    ):
        op_ids.append((
            "pec_k",
            "prove pre-payoff phase-space/material ownership plus a numerical owner-preimage or prefix budget",
        ))
    if any(
        token in haystack
        for token in ("regime", "class", "same-tree", "same_tree",
                      "subcritical", "endpoint", "type-i", "type_i",
                      "type i", "typei", "amplitude envelope",
                      "amplitude_envelope")
    ):
        op_ids.append((
            "pec_b",
            "scope the regime precisely so later estimates cannot use deferred cases",
        ))
    if any(
        token in haystack
        for token in (
            "weak l", "weak-l", "weak_l", "weakl", "tail",
            "distribution", "reverse holder", "reverse-holder",
            "anti-concentration", "anticoncentration", "level-set",
            "level set", "positive part", "signed average",
            "conditional average", "integrability",
            "critical source square", "critical_source_square",
            "source-square", "source square", "source_square",
            "source carleson", "source-carleson", "source_carleson",
            "annular renewal budget", "annular_renewal_budget",
            "duhamel source square", "duhamel_source_square",
            "paraproduct source", "paraproduct_source",
        )
    ):
        op_ids.append((
            "pec_h",
            "upgrade average/integral control to a local distribution tail or reverse Holder estimate",
        ))
    if any(
        token in haystack
        for token in (
            "skew", "skew-symmetry", "skew_symmetry",
            "energy cancellation", "energy_cancellation",
            "signed cancellation", "signed_cancellation",
            "null-form", "null_form", "null form",
            "symbol vanishing", "symbol_vanishing",
            "bilinear cancellation", "bilinear_cancellation",
            "projection cancellation", "projection_cancellation",
            "leray projection cancellation", "leray_projection_cancellation",
            "commutator cancellation", "commutator_cancellation",
            "signed-to-positive", "signed_to_positive",
            "signed identity", "signed_identity",
            "signed measure", "signed_measure",
            "trace-free", "trace_free", "tracefree",
            "positive variation", "positive_variation",
            "total variation", "total_variation",
            "positive source square", "positive_source_square",
            "dual price", "dual_price", "dual product", "dual_product",
            "self-tax", "self_tax", "selftax", "production_sq",
            "production^2", "production squared", "frame self tax",
            "frame_self_tax",
            "high-high", "high_high",
        )
    ):
        op_ids.append((
            "pec_l",
            "audit that the claimed signed/symbol cancellation pays the positive target quantity",
        ))
    if any(
        token in haystack
        for token in ("coordinate", "representation", "gauge", "section",
                      "duhamel", "pressure")
    ):
        op_ids.append((
            "cand_g",
            "try a same-system representation change if the current carrier hides structure",
        ))

    if any(
        token in haystack
        for token in (
            "log-corrected", "log_corrected", "log log", "log-log",
            "kozono", "taniuchi", "log bkm", "log-bkm",
            "non-pure-power", "non_pure_power", "pure power",
            "parabolic slaving", "parabolic_slaving", "tick647",
        )
    ):
        op_ids.append((
            "pec_b",
            "classify the asymptotic regime before using or bypassing the parabolic-slaving wall",
        ))
        op_ids.append((
            "pec_e",
            "test whether the log correction is a genuine non-pure-power receipt or a BKM-log relabel",
        ))
    if any(
        token in haystack
        for token in (
            "topological", "topology", "vortex link", "vortex-line",
            "vortex line", "helicity", "reconnection", "linking",
            "moffatt", "ricca", "vortex topology",
        )
    ):
        op_ids.append((
            "pec_i",
            "fix the topology/extractor before payoff so a topological label cannot be selected after seeing the route",
        ))
        op_ids.append((
            "pec_k",
            "prove finite owner-preimage multiplicity for topology/reconnection events before treating them as controllable",
        ))
        op_ids.append((
            "pec_e",
            "run the helicity-dark/topology-dark hostile packet before accepting the candidate",
        ))

    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for op_id, rationale in op_ids:
        if op_id in seen:
            continue
        seen.add(op_id)
        op = get(op_id)
        if op is None:
            continue
        out.append({
            "op_id": op.op_id,
            "name": op.name,
            "tier": op.tier,
            "rationale": rationale,
            "gate_mechanization": op.gate_mechanization,
            "boundary_collapse_risk": op.boundary_collapse_risk,
        })
    return out


def build_pde_execution_contract(
    pde_ops: list[dict[str, Any]],
    *,
    min_work_units: int = 3,
    hostile_suite: str = "ns_default",
    target_currency: str | None = None,
) -> dict[str, Any]:
    """Build the execution-mode contract for an RD PDE estimate attempt."""
    from ztare.research_director.hostile_packet_suite import (
        build_hostile_packet_suite,
    )
    from ztare.research_director.pde_currency_ledger import (
        currency_ledger_template,
    )
    from ztare.research_director.pde_estimate_craft_ops import (
        execution_template_for_ops,
    )

    op_ids = [str(op.get("op_id")) for op in pde_ops if op.get("op_id")]
    hostile_packets = NS_HOSTILE_PACKET_SUITES.get(hostile_suite)
    if hostile_packets is None:
        hostile_packets = []
    return {
        "mode": "pde-execution",
        "minimum_work_units": min_work_units,
        "gp219_execution_templates": execution_template_for_ops(op_ids),
        "hostile_packet_suite": build_hostile_packet_suite(
            hostile_suite,
            hostile_packets,
        ),
        "theorem_applicability_db": {
            "profile": "ns_millennium_hunt",
            "theorems": NS_THEOREM_APPLICABILITY_DB,
            "matcher": "src/ztare/research_director/theorem_applicability_db.py",
        },
        "currency_ledger_template": currency_ledger_template(target_currency),
        "no_early_stop_rule": {
            "terminal_gap_verdicts": [
                "MISSING_HYPOTHESIS",
                "OPEN",
                "NO_CLOSE",
                "THEOREM_OR_DOMAIN_GAP",
                "NEW_PDE_WORK_NEEDED",
            ],
            "required_before_terminal_gap": {
                "estimate_derivation_min": 2,
                "falsifier_packet_min": 1,
                "requires_one_of": ["smaller_theorem", "literature_match"],
            },
            "constructive_turn_rule": {
                "trigger": (
                    "conditional/source law plus bounded or selectable target "
                    "carrier is visible and no immediate packet kill is declared"
                ),
                "required_before_more_obstruction_only_work": [
                    "positive_constructor_attempt"
                ],
                "work_unit_fields": [
                    "source_law",
                    "target_carrier",
                    "bounded_or_selectable_variable",
                    "constructor_map",
                    "nearest_confuser",
                    "first_failed_line_or_success",
                    "conclusion",
                ],
            },
            "linter": "src/ztare/research_director/pde_work_unit_gate.py",
            "linter_cli": "python -m src.ztare.research_director.pde_work_unit_gate <payload.json>",
            "receipt_strength_linter": "src/ztare/research_director/receipt_strength_audit.py",
            "receipt_strength_rule": (
                "Prop-only proofs of no-overlap, same-owner/source, no-reuse, "
                "or payoff-independence do not discharge the PDE receipt; "
                "supply typed/numeric backing or record the exact missing receipt."
            ),
        },
        "prompt_contract": [
            "Normalize variables.",
            "Write one target inequality.",
            "Attempt the estimate and name the first failed line.",
            "Test at least one hostile packet.",
            "If a conditional source law and bounded/selectable carrier are visible, attempt the positive constructor before adding another obstruction layer.",
            "Run receipt-strength audit when using no-overlap, same-owner/source, no-reuse, or payoff-independence fields.",
            "Either repair the theorem, shrink the residual, or prove an exact theorem match.",
        ],
        "notebook_templates": [
            "normalization.md",
            "estimate_attempt_1.md",
            "estimate_attempt_2.md",
            "positive_constructor_attempt.md",
            "hostile_packet_1.md",
            "first_failed_line.md",
            "corrected_theorem.md",
            "theorem_applicability_match.md",
        ],
    }


def run_moment_ratio_surplus_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-MOMENT-RATIO-SURPLUS checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.moment_ratio_surplus_gate import run_gate

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"moment_ratio_check_{i}")
        result = run_gate(
            first_moment_sq=check.get("first_moment_sq"),
            second_moment_cap=check.get("second_moment_cap"),
            cheap_boundary_lower_bound=check.get("cheap_boundary_lower_bound"),
            threshold_space_measure=check.get("threshold_space_measure"),
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_bounded_ratio_support_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-BOUNDED-RATIO-SUPPORT checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.bounded_ratio_support_gate import run_gate

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"bounded_ratio_support_check_{i}")
        result = run_gate(
            mean_surplus=check.get("mean_surplus"),
            ratio_upper_bound=check.get("ratio_upper_bound"),
            companion_lower_bound=check.get("companion_lower_bound"),
            threshold_space_measure=check.get("threshold_space_measure"),
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_finite_prefix_selection_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-FINITE-PREFIX-SELECTION checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.finite_prefix_selection_gate import run_gate

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"finite_prefix_selection_check_{i}")
        result = run_gate(
            boundary=check.get("boundary"),
            interface=check.get("interface"),
            prefix_length=check.get("prefix_length"),
            same_source_family=bool(check.get("same_source_family")),
            prefix_fixed_before_payoff=bool(check.get("prefix_fixed_before_payoff")),
            boundary_interface_units_aligned=bool(
                check.get("boundary_interface_units_aligned")
            ),
            no_post_payoff_selection=bool(check.get("no_post_payoff_selection")),
            interface_floor=check.get("interface_floor"),
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_event_family_binding_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-EVENT-FAMILY-BINDING checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.event_family_binding_gate import (
        run_event_family_binding_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"event_family_binding_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_event_family_binding_gate(check, enforce_block=enforce_block)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_analogical_transfer_receipt_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-ANALOGICAL-TRANSFER-RECEIPT checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.analogical_transfer_receipt_gate import (
        run_analogical_transfer_receipt_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"analogical_transfer_receipt_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_analogical_transfer_receipt_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_prefix_count_bridge_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-PREFIX-COUNT-BRIDGE checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.prefix_count_bridge_gate import (
        run_prefix_count_bridge_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"prefix_count_bridge_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_prefix_count_bridge_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_source_prefix_budget_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SOURCE-PREFIX-BUDGET checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.source_prefix_budget_gate import (
        run_source_prefix_budget_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"source_prefix_budget_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_source_prefix_budget_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_final_slot_indexed_source_budget_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-FINAL-SLOT-INDEXED-SOURCE-BUDGET checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.final_slot_indexed_source_budget_gate import (
        run_final_slot_indexed_source_budget_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"final_slot_indexed_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_final_slot_indexed_source_budget_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_target_indexed_event_assignment_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-TARGET-INDEXED-EVENT-ASSIGNMENT-PROVENANCE checks."""
    if not checks:
        return []
    from ztare.gates.target_indexed_event_assignment_gate import (
        run_target_indexed_event_assignment_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"target_indexed_assignment_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_target_indexed_event_assignment_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_incidence_derived_finite_injection_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-INCIDENCE-DERIVED-FINITE-INJECTION checks."""
    if not checks:
        return []
    from ztare.gates.incidence_derived_finite_injection_gate import (
        run_incidence_derived_finite_injection_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"incidence_injection_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_incidence_derived_finite_injection_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_bounded_incident_existence_eventdata_horizon_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-BOUNDED-INCIDENT-EXISTENCE-EVENTDATA-HORIZON checks."""
    if not checks:
        return []
    from ztare.gates.bounded_incident_existence_eventdata_horizon_gate import (
        run_bounded_incident_existence_eventdata_horizon_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"bounded_incident_eventdata_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_bounded_incident_existence_eventdata_horizon_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_target_event_candidate_cover_selection_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-TARGET-EVENT-CANDIDATE-COVER-SELECTION checks."""
    if not checks:
        return []
    from ztare.gates.target_event_candidate_cover_selection_gate import (
        run_target_event_candidate_cover_selection_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"target_event_cover_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_target_event_candidate_cover_selection_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_target_cover_eventdata_incidence_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-TARGET-COVER-EVENTDATA-INCIDENCE checks."""
    if not checks:
        return []
    from ztare.gates.target_cover_eventdata_incidence_gate import (
        run_target_cover_eventdata_incidence_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"target_cover_eventdata_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_target_cover_eventdata_incidence_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_cover_event_selector_finalslot_assignment_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-COVER-EVENT-SELECTOR-FINALSLOT-ASSIGNMENT checks."""
    if not checks:
        return []
    from ztare.gates.cover_event_selector_finalslot_assignment_gate import (
        run_cover_event_selector_finalslot_assignment_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"cover_selector_assignment_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_cover_event_selector_finalslot_assignment_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_target_slot_bounded_incidence_least_hit_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-TARGET-SLOT-BOUNDED-INCIDENCE-LEAST-HIT checks."""
    if not checks:
        return []
    from ztare.gates.target_slot_bounded_incidence_least_hit_gate import (
        run_target_slot_bounded_incidence_least_hit_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"target_slot_least_hit_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_target_slot_bounded_incidence_least_hit_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_bounded_incident_existence_sametree_eventdata_index_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-BOUNDED-INCIDENT-EXISTENCE-SAMETREE-EVENTDATA-INDEX checks."""
    if not checks:
        return []
    from ztare.gates.bounded_incident_existence_sametree_eventdata_index_gate import (
        run_bounded_incident_existence_sametree_eventdata_index_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"same_tree_eventdata_index_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_bounded_incident_existence_sametree_eventdata_index_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_target_eventdata_index_prefix_cover_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-TARGET-EVENTDATA-INDEX-PREFIX-COVER checks."""
    if not checks:
        return []
    from ztare.gates.target_eventdata_index_prefix_cover_gate import (
        run_target_eventdata_index_prefix_cover_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"target_eventdata_prefix_cover_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_target_eventdata_index_prefix_cover_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_finite_scale_cofinality_prefix_cover_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-FINITE-SCALE-COFINALITY-PREFIX-COVER checks."""
    if not checks:
        return []
    from ztare.gates.finite_scale_cofinality_prefix_cover_gate import (
        run_finite_scale_cofinality_prefix_cover_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"finite_scale_cofinality_cover_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_finite_scale_cofinality_prefix_cover_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_event_to_badnode_selected_index_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-EVENT-TO-BADNODE-SELECTED-INDEX checks."""
    if not checks:
        return []
    from ztare.gates.event_to_badnode_selected_index_gate import (
        run_event_to_badnode_selected_index_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"event_to_badnode_index_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_event_to_badnode_selected_index_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_event_prefix_coverage_selected_index_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-EVENT-PREFIX-COVERAGE-SELECTED-INDEX checks."""
    if not checks:
        return []
    from ztare.gates.event_prefix_coverage_selected_index_gate import (
        run_event_prefix_coverage_selected_index_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"event_prefix_coverage_index_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_event_prefix_coverage_selected_index_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_coverage_choice_finite_selector_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-COVERAGE-CHOICE-FINITE-SELECTOR checks."""
    if not checks:
        return []
    from ztare.gates.coverage_choice_finite_selector_gate import (
        run_coverage_choice_finite_selector_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"coverage_choice_selector_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_coverage_choice_finite_selector_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_typed_appearance_coverage_choice_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-TYPED-APPEARANCE-COVERAGE-CHOICE checks."""
    if not checks:
        return []
    from ztare.gates.typed_appearance_coverage_choice_gate import (
        run_typed_appearance_coverage_choice_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"typed_appearance_choice_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_typed_appearance_coverage_choice_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_typed_coverage_packet_appearance_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-TYPED-COVERAGE-PACKET-APPEARANCE checks."""
    if not checks:
        return []
    from ztare.gates.typed_coverage_packet_appearance_gate import (
        run_typed_coverage_packet_appearance_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"typed_coverage_packet_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_typed_coverage_packet_appearance_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_event_prefix_enumeration_packet_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-EVENT-PREFIX-ENUMERATION-PACKET checks."""
    if not checks:
        return []
    from ztare.gates.event_prefix_enumeration_packet_gate import (
        run_event_prefix_enumeration_packet_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"event_prefix_enumeration_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_event_prefix_enumeration_packet_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_bounded_natural_event_enumeration_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-BOUNDED-NATURAL-EVENT-ENUMERATION checks."""
    if not checks:
        return []
    from ztare.gates.bounded_natural_event_enumeration_gate import (
        run_bounded_natural_event_enumeration_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"bounded_nat_event_enum_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_bounded_natural_event_enumeration_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_unbounded_event_witness_prefix_bound_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-UNBOUNDED-EVENT-WITNESS-PREFIX-BOUND checks."""
    if not checks:
        return []
    from ztare.gates.unbounded_event_witness_prefix_bound_gate import (
        run_unbounded_event_witness_prefix_bound_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"unbounded_event_witness_bound_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_unbounded_event_witness_prefix_bound_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_cofinal_incidence_witness_bound_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-COFINAL-INCIDENCE-WITNESS-BOUND checks."""
    if not checks:
        return []
    from ztare.gates.cofinal_incidence_witness_bound_gate import (
        run_cofinal_incidence_witness_bound_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"cofinal_incidence_witness_bound_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_cofinal_incidence_witness_bound_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_explicit_cofinal_event_witness_bound_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-EXPLICIT-COFINAL-EVENT-WITNESS-BOUND checks."""
    if not checks:
        return []
    from ztare.gates.explicit_cofinal_event_witness_bound_gate import (
        run_explicit_cofinal_event_witness_bound_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(
            check.get("label") or
            f"explicit_cofinal_event_witness_bound_check_{i}"
        )
        enforce_block = bool(check.get("enforce_block"))
        result = run_explicit_cofinal_event_witness_bound_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_cofinal_event_selector_final_prefix_bound_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-COFINAL-EVENT-SELECTOR-FINAL-PREFIX-BOUND checks."""
    if not checks:
        return []
    from ztare.gates.cofinal_event_selector_final_prefix_bound_gate import (
        run_cofinal_event_selector_final_prefix_bound_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(
            check.get("label") or
            f"cofinal_event_selector_final_prefix_bound_check_{i}"
        )
        enforce_block = bool(check.get("enforce_block"))
        result = run_cofinal_event_selector_final_prefix_bound_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_finite_cofinal_event_selector_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-FINITE-COFINAL-EVENT-SELECTOR checks."""
    if not checks:
        return []
    from ztare.gates.finite_cofinal_event_selector_gate import (
        run_finite_cofinal_event_selector_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"finite_cofinal_event_selector_check_{i}")
        enforce_block = bool(check.get("enforce_block"))
        result = run_finite_cofinal_event_selector_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_positive_variation_bridge_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-POSITIVE-VARIATION-BRIDGE checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.positive_variation_bridge_gate import (
        run_positive_variation_bridge_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"positive_variation_bridge_check_{i}")
        result = run_positive_variation_bridge_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_positive_variation_quotient_wash_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-POSITIVE-VARIATION-QUOTIENT-WASH checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.positive_variation_quotient_wash_gate import (
        run_positive_variation_quotient_wash_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"positive_variation_quotient_wash_check_{i}")
        result = run_positive_variation_quotient_wash_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_quotient_minimal_carrier_payment_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-QUOTIENT-MINIMAL-CARRIER-PAYMENT checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.quotient_minimal_carrier_payment_gate import (
        run_quotient_minimal_carrier_payment_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"quotient_minimal_carrier_payment_check_{i}")
        result = run_quotient_minimal_carrier_payment_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_quadratic_quotient_descent_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-QUADRATIC-QUOTIENT-DESCENT checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.quadratic_quotient_descent_gate import (
        run_quadratic_quotient_descent_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"quadratic_quotient_descent_check_{i}")
        result = run_quadratic_quotient_descent_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_nonadaptive_source_selection_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-NONADAPTIVE-SOURCE-SELECTION checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.nonadaptive_source_selection_gate import (
        run_nonadaptive_source_selection_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"nonadaptive_source_selection_check_{i}")
        result = run_nonadaptive_source_selection_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_law_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-LAW checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.support_index_law_gate import (
        run_support_index_law_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_law_check_{i}")
        result = run_support_index_law_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_injectivity_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-INJECTIVITY checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.support_index_injectivity_gate import (
        run_support_index_injectivity_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_injectivity_check_{i}")
        result = run_support_index_injectivity_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_affine_order_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-AFFINE-ORDER checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.support_index_affine_order_gate import (
        run_support_index_affine_order_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_affine_order_check_{i}")
        result = run_support_index_affine_order_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_fixed_step_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-FIXED-STEP checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.support_index_fixed_step_gate import (
        run_support_index_fixed_step_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_fixed_step_check_{i}")
        result = run_support_index_fixed_step_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_adjacent_gap_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-ADJACENT-GAP checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.support_index_adjacent_gap_gate import (
        run_support_index_adjacent_gap_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_adjacent_gap_check_{i}")
        result = run_support_index_adjacent_gap_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_unit_gap_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-UNIT-GAP checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.support_index_unit_gap_gate import (
        run_support_index_unit_gap_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_unit_gap_check_{i}")
        result = run_support_index_unit_gap_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_no_hole_unit_gap_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-NO-HOLE-UNIT-GAP checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.support_index_no_hole_unit_gap_gate import (
        run_support_index_no_hole_unit_gap_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_no_hole_unit_gap_check_{i}")
        result = run_support_index_no_hole_unit_gap_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_endpoint_tight_no_hole_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-ENDPOINT-TIGHT-NO-HOLE checks."""
    if not checks:
        return []
    from ztare.gates.support_index_endpoint_tight_no_hole_gate import (
        run_support_index_endpoint_tight_no_hole_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(
            check.get("label")
            or f"support_index_endpoint_tight_no_hole_check_{i}"
        )
        result = run_support_index_endpoint_tight_no_hole_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_base_anchored_strict_lower_bound_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-BASE-ANCHORED-STRICT-LOWER-BOUND checks."""
    if not checks:
        return []
    from ztare.gates.support_index_base_strict_lower_endpoint_gate import (
        run_support_index_base_strict_lower_endpoint_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(
            check.get("label")
            or f"support_index_base_anchored_strict_lower_bound_check_{i}"
        )
        result = run_support_index_base_strict_lower_endpoint_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_final_endpoint_capacity_upper_bound_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-FINAL-ENDPOINT-CAPACITY-UPPER-BOUND checks."""
    if not checks:
        return []
    from ztare.gates.support_index_tail_capacity_upper_endpoint_gate import (
        run_support_index_tail_capacity_upper_endpoint_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(
            check.get("label")
            or f"support_index_final_endpoint_capacity_upper_bound_check_{i}"
        )
        result = run_support_index_tail_capacity_upper_endpoint_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_final_slot_upper_bound_tail_capacity_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-FINAL-SLOT-UPPER-BOUND-TAIL-CAPACITY checks."""
    if not checks:
        return []
    from ztare.gates.support_index_final_slot_upper_bound_tail_capacity_gate import (
        run_support_index_final_slot_upper_bound_tail_capacity_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(
            check.get("label")
            or f"support_index_final_slot_upper_bound_tail_capacity_check_{i}"
        )
        result = run_support_index_final_slot_upper_bound_tail_capacity_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_tail_capacity_failure_witness_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-TAIL-CAPACITY-FAILURE-WITNESS checks."""
    if not checks:
        return []
    from ztare.gates.support_index_tail_capacity_failure_witness_gate import (
        run_support_index_tail_capacity_failure_witness_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(
            check.get("label")
            or f"support_index_tail_capacity_failure_witness_check_{i}"
        )
        result = run_support_index_tail_capacity_failure_witness_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_skipped_slot_hostile_witness_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-SKIPPED-SLOT-HOSTILE-WITNESS checks."""
    if not checks:
        return []
    from ztare.gates.support_index_skipped_slot_hostile_witness_gate import (
        run_support_index_skipped_slot_hostile_witness_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(
            check.get("label")
            or f"support_index_skipped_slot_hostile_witness_check_{i}"
        )
        result = run_support_index_skipped_slot_hostile_witness_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_interval_image_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-INTERVAL-IMAGE checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.support_index_interval_image_gate import (
        run_support_index_interval_image_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_interval_image_check_{i}")
        result = run_support_index_interval_image_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_interval_preimage_selector_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-INTERVAL-PREIMAGE-SELECTOR checks."""
    if not checks:
        return []
    from ztare.gates.support_index_interval_preimage_selector_gate import (
        run_support_index_interval_preimage_selector_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_interval_preimage_selector_check_{i}")
        result = run_support_index_interval_preimage_selector_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_least_interval_preimage_selector_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-LEAST-INTERVAL-PREIMAGE-SELECTOR checks."""
    if not checks:
        return []
    from ztare.gates.support_index_least_interval_preimage_selector_gate import (
        run_support_index_least_interval_preimage_selector_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_least_interval_preimage_selector_check_{i}")
        result = run_support_index_least_interval_preimage_selector_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_first_hit_interval_preimage_selector_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-FIRST-HIT-INTERVAL-PREIMAGE-SELECTOR checks."""
    if not checks:
        return []
    from ztare.gates.support_index_first_hit_interval_preimage_selector_gate import (
        run_support_index_first_hit_interval_preimage_selector_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_first_hit_interval_preimage_selector_check_{i}")
        result = run_support_index_first_hit_interval_preimage_selector_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_support_index_vacuous_first_hit_adapter_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SUPPORT-INDEX-VACUOUS-FIRST-HIT-ADAPTER checks."""
    if not checks:
        return []
    from ztare.gates.support_index_vacuous_first_hit_adapter_gate import (
        run_support_index_vacuous_first_hit_adapter_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"support_index_vacuous_first_hit_adapter_check_{i}")
        result = run_support_index_vacuous_first_hit_adapter_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_finite_support_extraction_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-FINITE-SUPPORT-EXTRACTION checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.finite_support_extraction_gate import (
        run_finite_support_extraction_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"finite_support_extraction_check_{i}")
        enforce_block = bool(check.get("enforce_block", True))
        result = run_finite_support_extraction_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_finite_image_support_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-FINITE-IMAGE-SUPPORT checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.finite_image_support_gate import (
        run_finite_image_support_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"finite_image_support_check_{i}")
        enforce_block = bool(check.get("enforce_block", True))
        result = run_finite_image_support_gate(
            check,
            enforce_block=enforce_block,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_no_rebilling_freshness_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-NO-REBILLING-FRESHNESS checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.no_rebilling_freshness_gate import (
        run_no_rebilling_freshness_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"no_rebilling_freshness_check_{i}")
        result = run_no_rebilling_freshness_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_same_carrier_packing_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-SAME-CARRIER-PACKING checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.same_carrier_packing_gate import (
        run_same_carrier_packing_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"same_carrier_packing_check_{i}")
        result = run_same_carrier_packing_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_metric_covering_selection_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-METRIC-COVERING-SELECTION checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.metric_covering_selection_gate import (
        run_metric_covering_selection_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"metric_covering_selection_check_{i}")
        result = run_metric_covering_selection_gate(check)
        results.append({
            "label": label,
            "input": check,
            "result": result,
        })
    return results


def run_pi_group_checks(
    pi_checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-PI-GROUP-FORCING checks supplied by the caller."""
    if not pi_checks:
        return []
    from ztare.gates.pi_group_forcing import (
        format_forcing_report,
        run_pi_group_forcing,
    )

    results = []
    for i, check in enumerate(pi_checks):
        label = str(check.get("label") or f"pi_check_{i}")
        result = run_pi_group_forcing(
            quantity_dim=check.get("quantity_dim") or {},
            subset_dims=check.get("subset_dims") or {},
        )
        results.append({
            "label": label,
            "quantity_dim": check.get("quantity_dim") or {},
            "subset_dims": check.get("subset_dims") or {},
            "result": result,
            "report": format_forcing_report(result),
        })
    return results


def run_ambiguous_pi_pinning_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-AMBIGUOUS-PI-PINNING checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.ambiguous_pi_pinning_gate import (
        format_report,
        run_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"ambiguous_pi_pinning_{i}")
        result = run_gate(
            pi_group_result=check.get("pi_group_result"),
            ambiguous=check.get("ambiguous"),
            receipts=check.get("receipts") or {},
            label=label,
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
            "report": format_report(result),
        })
    return results


def run_dimensionless_exponent_source_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run analytic-source checks for dimensionless exponents."""
    if not checks:
        return []
    from ztare.gates.dimensionless_exponent_source_gate import (
        format_report,
        run_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"dimensionless_exponent_{i}")
        result = run_gate(
            expression=str(check.get("expression") or ""),
            dimensionless_variables=check.get("dimensionless_variables") or {},
            receipts=check.get("receipts") or {},
            label=label,
        )
        results.append({
            "label": label,
            "expression": check.get("expression") or "",
            "result": result,
            "report": format_report(result),
        })
    return results


def run_persistence_budget_exponent_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run persistence exponent/thickness anti-laundering checks."""
    if not checks:
        return []
    from ztare.gates.persistence_budget_exponent_gate import (
        format_persistence_budget_exponent_report,
        run_persistence_budget_exponent_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"persistence_budget_{i}")
        result = run_persistence_budget_exponent_gate(
            dimension=float(check.get("dimension", 0)),
            persistence_exponent=float(check.get("persistence_exponent", 0)),
            thickness_or_reach_receipt=bool(
                check.get("thickness_or_reach_receipt")
            ),
            uniform_complexity_receipt=bool(
                check.get("uniform_complexity_receipt")
            ),
            same_carrier_receipt=bool(check.get("same_carrier_receipt")),
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
            "report": format_persistence_budget_exponent_report(result),
        })
    return results

def generate_pde_estimate_skeletons(
    *,
    target: str,
    field: str | None,
    gap_type: str,
    context: dict[str, Any],
    inequalities: list[str],
) -> list[dict[str, Any]]:
    """Generate substrate-neutral analytic estimate skeletons."""
    from ztare.research_director.pde_estimate_skeleton import (
        generate_estimate_skeletons,
    )

    return generate_estimate_skeletons(
        target=target,
        field=field,
        gap_type=gap_type,
        context=context,
        inequalities=inequalities,
    )


def run_limit_passage_audit(
    gap_type: str,
    steps: list[dict[str, Any]],
    *,
    finite_prefix_results: bool = False,
) -> dict[str, Any] | None:
    """Run the existing pec_d limit-passage inheritance gate when applicable."""
    if gap_type != "LIMIT_PASSAGE" and not steps and not finite_prefix_results:
        return None
    from ztare.gates.limit_passage_inheritance_lemma_gate import (
        run_limit_passage_gate,
    )
    return run_limit_passage_gate({
        "finite_prefix_results": finite_prefix_results or gap_type == "LIMIT_PASSAGE",
        "limit_passage_steps": steps,
    })


def run_linear_observable_coercivity_checks(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run G-LINEAR-OBS-COERCIVITY checks supplied by the caller."""
    if not checks:
        return []
    from ztare.gates.linear_observable_coercivity_gate import (
        format_report,
        run_gate,
    )

    results = []
    for i, check in enumerate(checks):
        label = str(check.get("label") or f"linear_observable_check_{i}")
        result = run_gate(
            target_dimension=check.get("target_dimension", 0),
            observable_rank=check.get("observable_rank", 0),
            full_reconstruction_receipt=bool(
                check.get("full_reconstruction_receipt", False)
            ),
            coercivity_receipt=bool(check.get("coercivity_receipt", False)),
            kernel_quotient_dimension=check.get("kernel_quotient_dimension"),
            kernel_quotient_receipt=bool(
                check.get("kernel_quotient_receipt", False)
            ),
            kernel_witness_present=bool(check.get("kernel_witness_present", False)),
            dimensionally_compatible=check.get("dimensionally_compatible"),
            labels=check.get("labels") or {},
        )
        results.append({
            "label": label,
            "input": check,
            "result": result,
            "report": format_report(result),
        })
    return results


def run_residual_normal_form(
    profile_path: Path | None,
    target: str,
    field: str | None,
    candidates: list[str],
    context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Classify the proposed estimate against a substrate normal-form profile."""
    if profile_path is None:
        return None
    if not profile_path.exists():
        return {
            "classification": "UNAVAILABLE",
            "reason": f"profile not found: {profile_path}",
        }
    from ztare.research_director.residual_normal_form import (
        compile_residual_normal_form,
        load_profile,
    )
    profile = load_profile(profile_path)
    context_terms: list[str] = []
    if context:
        doc = str(context.get("doc", ""))
        if doc:
            context_terms.append(doc)
        for item in context.get("fields", []):
            name = str(item.get("name", ""))
            ftype = str(item.get("type", ""))
            context_terms.append(f"{name}: {ftype}")
    text = "\n".join([target, field or "", *candidates, *context_terms])
    return compile_residual_normal_form(text, profile)


def run_single_spend_audit(fields: list[str]) -> dict[str, Any] | None:
    """Run the RD single-spend carrier audit if fields were supplied."""
    if not fields:
        return None
    from ztare.research_director.single_spend_carrier_audit import (
        run_single_spend_carrier_audit,
    )
    return run_single_spend_carrier_audit(
        fields,
        profile=PDE_SINGLE_SPEND_PROFILE,
    )


def run_receipt_strength_audit_from_fields(fields: list[str]) -> dict[str, Any] | None:
    """Run the general receipt-strength audit over extracted carrier fields."""
    if not fields:
        return None
    from ztare.research_director.receipt_strength_audit import (
        run_receipt_strength_audit,
    )
    return run_receipt_strength_audit(fields)


def run_owner_preimage_prefix_audit(
    pde_ops: list[dict[str, Any]],
    owner_preimage_receipts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Run the owner-preimage prefix gate when selected or receipts are supplied."""
    if not owner_preimage_receipts and not any(
        op.get("op_id") == "pec_k" for op in pde_ops
    ):
        return None
    from ztare.gates.owner_preimage_prefix_gate import (
        run_owner_preimage_prefix_gate,
    )

    return run_owner_preimage_prefix_gate(
        {"owner_preimage_receipts": owner_preimage_receipts},
        expect_receipt=True,
    )


def run_scaled_transfer_numeric_audit(
    target: str,
    field: str | None,
    context: dict[str, Any],
    scaled_transfer_numeric_receipts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Run the scaled-transfer numeric receipt gate for route-tail edges."""
    context_terms = [target, field or "", str(context.get("doc") or "")]
    for item in context.get("fields", []):
        if isinstance(item, dict):
            context_terms.append(str(item.get("name") or ""))
            context_terms.append(str(item.get("type") or ""))
    text = "\n".join(context_terms)
    selected = (
        bool(scaled_transfer_numeric_receipts)
        or "C7RouteActiveTailNonnegativeReceipt" in text
        or "C7SelectedEventNodeRadiusNonnegativeReceipt" in text
        or "eventNodeRadius_nonnegative" in text
        or "selectedNodeRadius_nonnegative" in text
    )
    if not selected:
        return None

    from ztare.gates.scaled_transfer_numeric_receipt_gate import (
        run_scaled_transfer_numeric_receipt_gate,
    )

    return run_scaled_transfer_numeric_receipt_gate(
        {"scaled_transfer_numeric_receipts": scaled_transfer_numeric_receipts},
        profile=NS_SCALED_TRANSFER_NUMERIC_PROFILE,
        expect_receipt=True,
    )


def run_owner_geometry_core_audit(
    target: str,
    field: str | None,
    context: dict[str, Any],
    owner_geometry_core_receipts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Run the owner-geometry-core gate for reduced TICK668 edges."""
    context_terms = [target, field or "", str(context.get("doc") or "")]
    for item in context.get("fields", []):
        if isinstance(item, dict):
            context_terms.append(str(item.get("name") or ""))
            context_terms.append(str(item.get("type") or ""))
    text = "\n".join(context_terms)
    selected = (
        bool(owner_geometry_core_receipts)
        or "C7OwnerPreimageGeometryCoreReceipt" in text
        or "C7OwnerGeometryResidualAfterScaledTransfer" in text
        or "ofOwnerPreimageGeometryCore" in text
    )
    if not selected:
        return None

    from ztare.gates.residual_core_receipt_gate import (
        run_residual_core_receipt_gate,
    )

    return run_residual_core_receipt_gate(
        {"owner_geometry_core_receipts": owner_geometry_core_receipts},
        profile=OWNER_GEOMETRY_CORE_PROFILE,
        expect_receipt=True,
    )


def run_fresh_annular_anti_laundering_audit(
    target: str,
    field: str | None,
    context: dict[str, Any],
    fresh_annular_anti_laundering_receipts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Run the anti-laundering gate for the fresh-annular bridge edge."""
    context_terms = [target, field or "", str(context.get("doc") or "")]
    for item in context.get("fields", []):
        if isinstance(item, dict):
            context_terms.append(str(item.get("name") or ""))
            context_terms.append(str(item.get("type") or ""))
    text = "\n".join(context_terms)
    selected = (
        bool(fresh_annular_anti_laundering_receipts)
        or "C7FreshAnnularAntiLaunderingReceiptFromSeparatedSource" in text
        or "ofOwnerLineageAndAntiLaundering" in text
        or "ofCarrierRadiusPositiveIdentityAndAntiLaundering" in text
    )
    if not selected:
        return None

    from ztare.gates.residual_core_receipt_gate import (
        run_residual_core_receipt_gate,
    )

    return run_residual_core_receipt_gate(
        {
            "fresh_annular_anti_laundering_receipts":
                fresh_annular_anti_laundering_receipts
        },
        profile=FRESH_ANNULAR_ANTI_LAUNDERING_PROFILE,
        expect_receipt=True,
    )

def run_fresh_annular_non_disguise_audit(
    target: str,
    field: str | None,
    context: dict[str, Any],
    fresh_annular_non_disguise_receipts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Run the non-disguise morphology gate for the fresh-annular split edge."""
    context_terms = [target, field or "", str(context.get("doc") or "")]
    for item in context.get("fields", []):
        if isinstance(item, dict):
            context_terms.append(str(item.get("name") or ""))
            context_terms.append(str(item.get("type") or ""))
    text = "\n".join(context_terms)
    selected = (
        bool(fresh_annular_non_disguise_receipts)
        or "C7FreshAnnularNonDisguiseReceiptFromSeparatedSource" in text
        or "ofNonDisguiseAndSourceNondeclaration" in text
    )
    if not selected:
        return None

    from ztare.gates.residual_core_receipt_gate import (
        run_residual_core_receipt_gate,
    )

    return run_residual_core_receipt_gate(
        {
            "fresh_annular_non_disguise_receipts":
                fresh_annular_non_disguise_receipts
        },
        profile=FRESH_ANNULAR_NON_DISGUISE_PROFILE,
        expect_receipt=True,
    )


def run_fresh_annular_innovation_audit(
    target: str,
    field: str | None,
    context: dict[str, Any],
    fresh_annular_innovation_receipts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Run the innovation gate for the fresh-annular anti-laundering route."""
    context_terms = [target, field or "", str(context.get("doc") or "")]
    for item in context.get("fields", []):
        if isinstance(item, dict):
            context_terms.append(str(item.get("name") or ""))
            context_terms.append(str(item.get("type") or ""))
    text = "\n".join(context_terms)
    selected = (
        bool(fresh_annular_innovation_receipts)
        or "FreshAnnularInnovationAntiLaunderingReceipt" in text
        or "innovation" in text.lower()
    )
    if not selected:
        return None

    from ztare.gates.residual_core_receipt_gate import (
        run_residual_core_receipt_gate,
    )

    return run_residual_core_receipt_gate(
        {
            "fresh_annular_innovation_receipts":
                fresh_annular_innovation_receipts
        },
        profile=FRESH_ANNULAR_INNOVATION_PROFILE,
        expect_receipt=True,
    )


def run_section_fixed_unsigned_variation_audit(
    target: str,
    field: str | None,
    context: dict[str, Any],
    section_fixed_unsigned_variation_receipts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Run the section-fixed unsigned variation gate for the crown route."""
    context_terms = [target, field or "", str(context.get("doc") or "")]
    for item in context.get("fields", []):
        if isinstance(item, dict):
            context_terms.append(str(item.get("name") or ""))
            context_terms.append(str(item.get("type") or ""))
    text = "\n".join(context_terms)
    selected = (
        bool(section_fixed_unsigned_variation_receipts)
        or "DuhamelSectionFixedUnsignedCrownMeasureReceipt" in text
        or "SectionFixedUnsignedLocalizedCrownMass" in text
        or "UnsignedLocalizedCrownSourceFromDuhamelSection" in text
        or "unsigned variation" in text.lower()
        or "unsigned-variation" in text.lower()
    )
    if not selected:
        return None

    from ztare.gates.residual_core_receipt_gate import (
        run_residual_core_receipt_gate,
    )

    return run_residual_core_receipt_gate(
        {
            "section_fixed_unsigned_variation_receipts":
                section_fixed_unsigned_variation_receipts
        },
        profile=SECTION_FIXED_UNSIGNED_VARIATION_PROFILE,
        expect_receipt=True,
    )


def single_spend_fields_from_context(context: dict[str, Any]) -> list[str]:
    """Convert source-truth context fields into audit inputs."""
    fields: list[str] = []
    for item in context.get("fields", []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        ftype = str(item.get("type") or "").strip()
        if not name:
            continue
        fields.append(f"{name}:{ftype}" if ftype else name)
    return fields


def allowed_endpoints_from_context(context: dict[str, Any]) -> set[str]:
    allowed = {str(context.get("target") or "")}
    field = context.get("field")
    if field:
        allowed.add(str(field))
    for item in context.get("fields", []):
        if isinstance(item, dict):
            allowed.add(str(item.get("name") or ""))
            ftype = str(item.get("type") or "")
            for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", ftype):
                if token and token[0].isupper():
                    allowed.add(token)
    for item in context.get("constructors", []):
        allowed.add(str(item.get("type_head") or ""))
    return {x for x in allowed if x}


def check_inequalities(
    inequalities: list[str],
    context: dict[str, Any],
    dims_path: Path | None,
    extra_allowed: set[str] | None = None,
) -> list[dict[str, Any]]:
    if not inequalities:
        return []
    from ztare.gates.pde_inequality_dimensional_gate import run_gate
    dimensional_features: dict[str, str] = {}
    if dims_path:
        dims_arg = str(dims_path)
        if dims_arg.lstrip().startswith("{"):
            dimensional_features = json.loads(dims_arg)
        else:
            dimensional_features = json.loads(dims_path.read_text(encoding="utf-8"))
    allowed = allowed_endpoints_from_context(context)
    allowed.update(str(name) for name in dimensional_features.keys())
    if extra_allowed:
        allowed.update(extra_allowed)
    results = []
    for ineq in inequalities:
        result = run_gate(
            candidate_inequality=ineq,
            dimensional_features=dimensional_features,
            allowed_endpoints=allowed,
        )
        result["candidate_inequality"] = ineq
        results.append(result)
    return results


def emit_curriculum_variants(
    target: str,
    transforms: list[str],
    out_dir: Path,
) -> list[dict[str, Any]]:
    if not transforms:
        return []
    from curriculum_generator import apply_transformation, load_obligation_source, load_workmap_target
    target_obj = load_workmap_target(target)
    if not target_obj:
        return [{"error": "target not found in workmap", "target": target}]
    source = load_obligation_source(target_obj)
    if not source:
        return [{"error": "could not load obligation source", "target": target}]
    variant_dir = out_dir / "curriculum_variants"
    variant_dir.mkdir(parents=True, exist_ok=True)
    emitted = []
    for transform in transforms:
        result = apply_transformation(source, target, transform)
        if "error" in result:
            emitted.append(result)
            continue
        base = variant_dir / f"{target}_{transform.lower()}"
        json_path = base.with_suffix(".json")
        lean_path = base.with_suffix(".lean")
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "original_target": target,
            "original_file": target_obj.get("file", ""),
            **result,
        }
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        import_line = (
            f"import ZtareProofs.{target_obj.get('file')}\n\n"
            if target_obj.get("file") else ""
        )
        lean_path.write_text(
            f"-- Curriculum variant: {target} -> {result['new_target_name']}\n"
            f"-- Transform: {transform} ({result['transform_description']})\n"
            f"-- HONEST CAVEAT: template-based; may be ill-typed.\n\n"
            f"{import_line}"
            "namespace ZtareProofs.NS\n\n"
            f"{result['transformed_source']}\n\n"
            "end ZtareProofs.NS\n",
            encoding="utf-8",
        )
        emitted.append({
            "transform": transform,
            "new_target_name": result["new_target_name"],
            "json_path": str(json_path.relative_to(REPO)),
            "lean_path": str(lean_path.relative_to(REPO)),
            "caveat": result["honest_caveat"],
        })
    return emitted


def render_markdown(pack: dict[str, Any]) -> str:
    ctx = pack["target_context"]
    lines = [
        "# PDE Estimate Workbench Pack",
        "",
        f"- Target: `{pack['target']}`",
        f"- Field: `{pack.get('field') or ''}`",
        f"- Scope: RD caller over existing ZTARE primitives; not a replacement workbench",
        f"- Gap type: `{pack['gap_classification'].get('gap_type')}` "
        f"({pack['gap_classification'].get('confidence', '?')})",
        "",
        "## Target Context",
        "",
        f"- Found in workmap: `{ctx.get('found')}`",
        f"- File: `{ctx.get('target_file')}`",
        f"- Downstream users: `{ctx.get('n_downstream_users')}`",
        f"- Priority: `{ctx.get('priority')}`",
        "",
        "## Mathlib Shelf",
        "",
    ]
    if pack["mathlib_lemmas"]:
        for lemma in pack["mathlib_lemmas"][:10]:
            lines.append(f"- `{lemma['name']}` ({lemma['file']})")
    else:
        lines.append("- (none found; this is a thin-zone warning)")
    apn = pack.get("apn_semantic_neighbors") or {}
    lines.extend(["", "## APN Semantic Bridges", ""])
    if apn.get("available"):
        lines.append(
            f"- Corpus/filtered: `{apn.get('corpus_size')}` / "
            f"`{apn.get('filtered_size')}`; threshold=`{apn.get('threshold')}`"
        )
        lines.append(f"- Bridge edges: `{len(apn.get('bridge_edges') or [])}`")
        hits = apn.get("hits") or []
        if hits:
            try:
                from ztare.research_director.apn_semantic import (
                    APNSemanticHit,
                    render_text as render_apn_text,
                )
                rendered_hits = [
                    APNSemanticHit(
                        id=str(hit.get("id") or ""),
                        name=str(hit.get("name") or "?"),
                        kind=str(hit.get("kind") or ""),
                        domain=str(hit.get("domain") or ""),
                        file=str(hit.get("file") or ""),
                        variant_tag=hit.get("variant_tag"),
                        cosine=float(hit.get("cosine") or 0.0),
                        snippet=str(hit.get("snippet") or ""),
                    )
                    for hit in hits[:5]
                ]
                lines.extend(
                    render_apn_text(
                        rendered_hits, header="APN semantic neighbours"
                    ).splitlines()
                )
            except Exception:
                for hit in hits[:5]:
                    lines.append(
                        f"- `{hit.get('name')}` ({hit.get('domain')}/{hit.get('file')}, "
                        f"cos={hit.get('cosine')}): {hit.get('snippet')}"
                    )
        elif apn.get("skip_reason"):
            lines.append(f"- Skip: {apn.get('skip_reason')}")
        else:
            lines.append("- (none above threshold)")
    elif apn:
        lines.append(f"- unavailable: {apn.get('skip_reason')}")
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Auxiliary Families", ""])
    if pack["auxiliary_families"]:
        for item in pack["auxiliary_families"]:
            lines.append(f"- `{item['family']}`: {item['mathematical_form']}")
    else:
        lines.append("- (none selected)")
    lines.extend(["", "## ZTARE Primitive Suggestions", ""])
    if pack.get("pde_craft_ops"):
        for item in pack["pde_craft_ops"]:
            gate = item.get("gate_mechanization") or "no shipped gate"
            lines.append(
                f"- `{item['op_id']}` {item['name']}: "
                f"{item['rationale']} ({gate})"
            )
    else:
        lines.append("- (none selected)")
    if pack.get("estimate_skeletons"):
        lines.extend(["", "## Estimate Skeletons", ""])
        for skeleton in pack["estimate_skeletons"]:
            lines.append(
                f"- `{skeleton.get('id')}` {skeleton.get('route')}: "
                f"{skeleton.get('target_inequality')}"
            )
            receipts = skeleton.get("required_receipts") or []
            if receipts:
                lines.append(f"  - required receipts: `{', '.join(receipts)}`")
            hostile = skeleton.get("hostile_packet") or {}
            if hostile:
                lines.append(
                    f"  - hostile packet: `{hostile.get('name')}` kills "
                    f"{hostile.get('kills')}"
                )
    else:
        lines.extend(["", "## Estimate Skeletons", "", "- (none selected)"])
    if pack.get("pde_execution_contract"):
        contract = pack["pde_execution_contract"]
        lines.extend(["", "## PDE Execution Contract", ""])
        lines.append(f"- Mode: `{contract.get('mode')}`")
        lines.append(
            f"- Minimum work units: `{contract.get('minimum_work_units')}`"
        )
        rule = contract.get("no_early_stop_rule", {})
        required = rule.get("required_before_terminal_gap", {})
        lines.append(
            "- Terminal gap verdicts require "
            f"`{required.get('estimate_derivation_min')}` estimate derivations, "
            f"`{required.get('falsifier_packet_min')}` falsifier packet, and "
            f"one of `{', '.join(required.get('requires_one_of', []))}`."
        )
        constructive = rule.get("constructive_turn_rule", {})
        if constructive:
            lines.append(
                "- Constructive turn: when "
                f"{constructive.get('trigger')}, require "
                f"`{', '.join(constructive.get('required_before_more_obstruction_only_work', []))}`."
            )
        hints = (
            contract.get("gp219_execution_templates", {})
            .get("pde_execution_hints", {})
        )
        if hints:
            lines.append("- Selected GP-219 execution hints:")
            for op_id, hint in hints.items():
                lines.append(
                    f"  - `{op_id}` {hint.get('name')}: "
                    f"{', '.join(hint.get('fields', []))}"
                )
        packets = contract.get("hostile_packet_suite", {}).get("packets", [])
        if packets:
            lines.append("- Hostile packets to test:")
            for packet in packets[:10]:
                lines.append(
                    f"  - `{packet.get('id')}`: {packet.get('packet')}"
                )
        theorem_db = contract.get("theorem_applicability_db", {})
        theorem_ids = sorted((theorem_db.get("theorems") or {}).keys())
        if theorem_ids:
            lines.append(
                "- Theorem applicability profile: "
                f"`{theorem_db.get('profile')}`; "
                f"templates `{', '.join(theorem_ids)}`"
            )
        lines.append("- Currency ledger:")
        for key in (
            contract.get("currency_ledger_template", {})
            .get("exchange_rate_obligations", {})
        ):
            lines.append(f"  - `{key}`")
    lines.extend(["", "## Residual Normal Form", ""])
    normal_form = pack.get("residual_normal_form")
    if normal_form:
        lines.append(f"- Classification: `{normal_form.get('classification')}`")
        if normal_form.get("reason"):
            lines.append(f"- Reason: {normal_form['reason']}")
        best = normal_form.get("best_match") or {}
        if best:
            lines.append(
                f"- Best match: `{best.get('canonical_name')}` "
                f"(score `{best.get('score')}`)"
            )
        if normal_form.get("required_next_move"):
            lines.append(
                f"- Required next move: {normal_form['required_next_move']}"
            )
        if normal_form.get("packet_hits"):
            lines.append("- Packet hits:")
            for hit in normal_form["packet_hits"]:
                lines.append(
                    f"  - `{hit['packet_id']}` {hit['name']}: "
                    f"{hit.get('required_escape')}"
                )
        if normal_form.get("currency_mismatches"):
            lines.append("- Currency mismatches:")
            for hit in normal_form["currency_mismatches"]:
                lines.append(
                    f"  - `{hit['rule_id']}` {hit['verdict']}: "
                    f"{hit.get('missing_exchange_rate')}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Limit-Passage Gate", ""])
    if pack.get("limit_passage_gate"):
        gate = pack["limit_passage_gate"]
        lines.append(
            f"- `{gate['summary']}`; passed=`{gate['passed']}`; "
            f"complete={gate['n_complete_steps']}/{gate['n_steps_declared']}"
        )
        for warning in gate.get("advisory_warnings", []):
            lines.append(f"- warning: {warning}")
        for violation in gate.get("violations", []):
            lines.append(
                f"- violation: `{violation.get('type')}` "
                f"{violation.get('missing_fields', '')}"
            )
    else:
        lines.append("- (not selected)")
    lines.extend(["", "## Moment Ratio Surplus", ""])
    if pack.get("moment_ratio_surplus_checks"):
        for item in pack["moment_ratio_surplus_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"ratio=`{res.get('ratio_lower_bound')}` "
                f"margin=`{res.get('overfill_margin')}`; {res.get('reason')}"
            )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Bounded Ratio Support", ""])
    if pack.get("bounded_ratio_support_checks"):
        for item in pack["bounded_ratio_support_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"support=`{res.get('support_lower_bound')}` "
                f"margin=`{res.get('overfill_margin')}`; {res.get('reason')}"
            )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Finite Prefix Selection", ""])
    if pack.get("finite_prefix_selection_checks"):
        for item in pack["finite_prefix_selection_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"boundary_sum=`{res.get('boundary_prefix_sum')}` "
                f"interface_sum=`{res.get('interface_prefix_sum')}` "
                f"witnesses=`{res.get('witness_indices')}` "
                f"floor_witnesses=`{res.get('payment_floor_witness_indices')}`; "
                f"{res.get('reason')}"
            )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Event Family Binding", ""])
    if pack.get("event_family_binding_checks"):
        for item in pack["event_family_binding_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Analogical Transfer Receipt", ""])
    if pack.get("analogical_transfer_receipt_checks"):
        for item in pack["analogical_transfer_receipt_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Prefix Count Bridge", ""])
    if pack.get("prefix_count_bridge_checks"):
        for item in pack["prefix_count_bridge_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            if res.get("numeric_check") is not None:
                lines.append(f"- numeric_check: `{res.get('numeric_check')}`")
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Source Prefix Budget", ""])
    if pack.get("source_prefix_budget_checks"):
        for item in pack["source_prefix_budget_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            if res.get("numeric_check") is not None:
                lines.append(f"- numeric_check: `{res.get('numeric_check')}`")
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Final-Slot Indexed Source Budget", ""])
    if pack.get("final_slot_indexed_source_budget_checks"):
        for item in pack["final_slot_indexed_source_budget_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            if res.get("numeric_check") is not None:
                lines.append(f"- numeric_check: `{res.get('numeric_check')}`")
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Target Indexed Event Assignment", ""])
    if pack.get("target_indexed_event_assignment_checks"):
        for item in pack["target_indexed_event_assignment_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` mode=`{res.get('mode')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            if res.get("numeric_check") is not None:
                lines.append(f"- numeric_check: `{res.get('numeric_check')}`")
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Incidence-Derived Finite Injection", ""])
    if pack.get("incidence_derived_finite_injection_checks"):
        for item in pack["incidence_derived_finite_injection_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Bounded Incident EventData/Horizon", ""])
    if pack.get("bounded_incident_existence_eventdata_horizon_checks"):
        for item in pack["bounded_incident_existence_eventdata_horizon_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Target Event Candidate Cover Selection", ""])
    if pack.get("target_event_candidate_cover_selection_checks"):
        for item in pack["target_event_candidate_cover_selection_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Target Cover EventData/Incidence", ""])
    if pack.get("target_cover_eventdata_incidence_checks"):
        for item in pack["target_cover_eventdata_incidence_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Cover Event Selector Final-Slot Assignment", ""])
    if pack.get("cover_event_selector_finalslot_assignment_checks"):
        for item in pack["cover_event_selector_finalslot_assignment_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Target Slot Bounded-Incidence Least-Hit", ""])
    if pack.get("target_slot_bounded_incidence_least_hit_checks"):
        for item in pack["target_slot_bounded_incidence_least_hit_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Bounded Incident Existence Same-Tree EventData Index", ""])
    if pack.get("bounded_incident_existence_sametree_eventdata_index_checks"):
        for item in pack["bounded_incident_existence_sametree_eventdata_index_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Target EventData Index Prefix Cover", ""])
    if pack.get("target_eventdata_index_prefix_cover_checks"):
        for item in pack["target_eventdata_index_prefix_cover_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Finite Scale/Cofinality Prefix Cover", ""])
    if pack.get("finite_scale_cofinality_prefix_cover_checks"):
        for item in pack["finite_scale_cofinality_prefix_cover_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Event-to-BadNode Selected Index", ""])
    if pack.get("event_to_badnode_selected_index_checks"):
        for item in pack["event_to_badnode_selected_index_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Event-Prefix Coverage Selected Index", ""])
    if pack.get("event_prefix_coverage_selected_index_checks"):
        for item in pack["event_prefix_coverage_selected_index_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Coverage Choice Finite Selector", ""])
    if pack.get("coverage_choice_finite_selector_checks"):
        for item in pack["coverage_choice_finite_selector_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Typed Appearance Coverage Choice", ""])
    if pack.get("typed_appearance_coverage_choice_checks"):
        for item in pack["typed_appearance_coverage_choice_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Typed Coverage Packet Appearance", ""])
    if pack.get("typed_coverage_packet_appearance_checks"):
        for item in pack["typed_coverage_packet_appearance_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Event-Prefix Enumeration Packet", ""])
    if pack.get("event_prefix_enumeration_packet_checks"):
        for item in pack["event_prefix_enumeration_packet_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Bounded Natural Event Enumeration", ""])
    if pack.get("bounded_natural_event_enumeration_checks"):
        for item in pack["bounded_natural_event_enumeration_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Unbounded Event Witness Prefix Bound", ""])
    if pack.get("unbounded_event_witness_prefix_bound_checks"):
        for item in pack["unbounded_event_witness_prefix_bound_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Cofinal Incidence Witness Bound", ""])
    if pack.get("cofinal_incidence_witness_bound_checks"):
        for item in pack["cofinal_incidence_witness_bound_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Explicit Cofinal Event Witness Bound", ""])
    if pack.get("explicit_cofinal_event_witness_bound_checks"):
        for item in pack["explicit_cofinal_event_witness_bound_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Cofinal Event Selector Final Prefix Bound", ""])
    if pack.get("cofinal_event_selector_final_prefix_bound_checks"):
        for item in pack["cofinal_event_selector_final_prefix_bound_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Finite Cofinal Event Selector", ""])
    if pack.get("finite_cofinal_event_selector_checks"):
        for item in pack["finite_cofinal_event_selector_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', violation.get('fields', '')))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Positive Variation Bridge", ""])
    if pack.get("positive_variation_bridge_checks"):
        for item in pack["positive_variation_bridge_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; "
                f"weak={res.get('weak_substitutes')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('fields', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Positive Variation Quotient Wash", ""])
    if pack.get("positive_variation_quotient_wash_checks"):
        for item in pack["positive_variation_quotient_wash_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; "
                f"weak={res.get('weak_substitutes')}; "
                f"wash={res.get('wash_confusers')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('fields', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Quotient Minimal Carrier Payment", ""])
    if pack.get("quotient_minimal_carrier_payment_checks"):
        for item in pack["quotient_minimal_carrier_payment_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; "
                f"weak={res.get('weak_substitutes')}; "
                f"underpay={res.get('underpayment_confusers')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('fields', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Quadratic Quotient Descent", ""])
    if pack.get("quadratic_quotient_descent_checks"):
        for item in pack["quadratic_quotient_descent_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; "
                f"weak={res.get('weak_substitutes')}; "
                f"confusers={res.get('quadratic_confusers')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('fields', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Nonadaptive Source Selection", ""])
    if pack.get("nonadaptive_source_selection_checks"):
        for item in pack["nonadaptive_source_selection_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; "
                f"weak={res.get('weak_substitutes')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('fields', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Law", ""])
    if pack.get("support_index_law_checks"):
        for item in pack["support_index_law_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Injectivity", ""])
    if pack.get("support_index_injectivity_checks"):
        for item in pack["support_index_injectivity_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Affine Order", ""])
    if pack.get("support_index_affine_order_checks"):
        for item in pack["support_index_affine_order_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index First-Hit Interval Preimage Selector", ""])
    if pack.get("support_index_first_hit_interval_preimage_selector_checks"):
        for item in pack["support_index_first_hit_interval_preimage_selector_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Vacuous First-Hit Adapter", ""])
    if pack.get("support_index_vacuous_first_hit_adapter_checks"):
        for item in pack["support_index_vacuous_first_hit_adapter_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Least Interval Preimage Selector", ""])
    if pack.get("support_index_least_interval_preimage_selector_checks"):
        for item in pack["support_index_least_interval_preimage_selector_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Interval Preimage Selector", ""])
    if pack.get("support_index_interval_preimage_selector_checks"):
        for item in pack["support_index_interval_preimage_selector_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Interval Image", ""])
    if pack.get("support_index_interval_image_checks"):
        for item in pack["support_index_interval_image_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Base-Anchored Strict Lower Bound", ""])
    if pack.get("support_index_base_anchored_strict_lower_bound_checks"):
        for item in pack["support_index_base_anchored_strict_lower_bound_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Final-Slot Upper Bound Tail Capacity", ""])
    if pack.get("support_index_final_slot_upper_bound_tail_capacity_checks"):
        for item in pack["support_index_final_slot_upper_bound_tail_capacity_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Final-Endpoint Capacity Upper Bound", ""])
    if pack.get("support_index_final_endpoint_capacity_upper_bound_checks"):
        for item in pack["support_index_final_endpoint_capacity_upper_bound_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Tail-Capacity Failure Witness", ""])
    if pack.get("support_index_tail_capacity_failure_witness_checks"):
        for item in pack["support_index_tail_capacity_failure_witness_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            computed = res.get("computed") or {}
            if computed:
                lines.append(
                    f"- computed: tail_capacity_failure="
                    f"`{computed.get('tail_capacity_failure_holds')}` "
                    f"upper_endpoint_failure="
                    f"`{computed.get('upper_endpoint_failure_holds')}`"
                )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('forbidden_shortcuts', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Endpoint-Tight No-Hole", ""])
    if pack.get("support_index_endpoint_tight_no_hole_checks"):
        for item in pack["support_index_endpoint_tight_no_hole_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Skipped-Slot Hostile Witness", ""])
    if pack.get("support_index_skipped_slot_hostile_witness_checks"):
        for item in pack["support_index_skipped_slot_hostile_witness_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('forbidden_shortcuts', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index No-Hole Unit Gap", ""])
    if pack.get("support_index_no_hole_unit_gap_checks"):
        for item in pack["support_index_no_hole_unit_gap_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Unit Gap", ""])
    if pack.get("support_index_unit_gap_checks"):
        for item in pack["support_index_unit_gap_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Adjacent Gap", ""])
    if pack.get("support_index_adjacent_gap_checks"):
        for item in pack["support_index_adjacent_gap_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Support Index Fixed Step", ""])
    if pack.get("support_index_fixed_step_checks"):
        for item in pack["support_index_fixed_step_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Finite Support Extraction", ""])
    if pack.get("finite_support_extraction_checks"):
        for item in pack["finite_support_extraction_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Finite Image Support", ""])
    if pack.get("finite_image_support_checks"):
        for item in pack["finite_image_support_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## No-Rebilling Freshness", ""])
    if pack.get("no_rebilling_freshness_checks"):
        for item in pack["no_rebilling_freshness_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; "
                f"weak={res.get('weak_substitutes')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('fields', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Same-Carrier Packing", ""])
    if pack.get("same_carrier_packing_checks"):
        for item in pack["same_carrier_packing_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Metric Covering Selection", ""])
    if pack.get("metric_covering_selection_checks"):
        for item in pack["metric_covering_selection_checks"]:
            res = item["result"]
            lines.append(
                f"- `{item['label']}`: passed=`{res.get('passed')}` "
                f"complete=`{res.get('complete')}` "
                f"missing={res.get('missing_fields')}; {res.get('summary')}"
            )
            for violation in res.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('weak_substitutes', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Pi-Group Forcing", ""])
    if pack.get("pi_group_checks"):
        for item in pack["pi_group_checks"]:
            lines.append(f"- `{item['label']}`: {item['report']}")
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Ambiguous Pi Pinning", ""])
    if pack.get("ambiguous_pi_pinning_checks"):
        for item in pack["ambiguous_pi_pinning_checks"]:
            result = item.get("result") or {}
            lines.append(f"- `{item['label']}`: {item['report']}")
            for violation in result.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get('type')}` "
                    f"{violation.get('missing_fields', violation.get('fields', ''))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Dimensionless Exponent Source", ""])
    if pack.get("dimensionless_exponent_source_checks"):
        for item in pack["dimensionless_exponent_source_checks"]:
            result = item.get("result") or {}
            lines.append(f"- `{item["label"]}`: {item["report"]}")
            for violation in result.get("violations", []):
                lines.append(
                    f"- violation: `{violation.get("type")}` "
                    f"{violation.get("missing_fields", violation.get("fields", ""))}"
                )
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Linear Observable Coercivity", ""])
    if pack.get("linear_observable_coercivity_checks"):
        for item in pack["linear_observable_coercivity_checks"]:
            lines.append(f"- `{item['label']}`: {item['report']}")
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Single-Spend Carrier Audit", ""])
    if pack.get("single_spend_audit"):
        audit = pack["single_spend_audit"]
        lines.append(
            f"- `{audit['summary']}`; passed=`{audit['passed']}`; "
            f"missing={audit['missing_channels']}; "
            f"prop_only={audit.get('prop_only_blocking_channels', audit.get('prop_only_payment_channels', []))}"
        )
        for warning in audit.get("warnings", []):
            lines.append(f"- warning: {warning}")
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Receipt Strength Audit", ""])
    if pack.get("receipt_strength_audit"):
        audit = pack["receipt_strength_audit"]
        lines.append(
            f"- `{audit['summary']}`; passed=`{audit['passed']}`; "
            f"missing={audit['missing_receipts']}; weak={audit['weak_receipts']}"
        )
        for warning in audit.get("warnings", []):
            lines.append(f"- warning: {warning}")
    else:
        lines.append("- (not requested)")
    lines.extend(["", "## Owner-Preimage Prefix Gate", ""])
    if pack.get("owner_preimage_prefix_gate"):
        gate = pack["owner_preimage_prefix_gate"]
        lines.append(
            f"- `{gate['summary']}`; passed=`{gate['passed']}`; "
            f"complete={gate['n_complete_receipts']}/"
            f"{gate['n_receipts_declared']}"
        )
        for warning in gate.get("advisory_warnings", []):
            lines.append(f"- warning: {warning}")
        for violation in gate.get("violations", []):
            lines.append(
                f"- violation: `{violation.get('type')}` "
                f"{violation.get('missing_fields', '')}"
            )
    else:
        lines.append("- (not selected)")
    lines.extend(["", "## Scaled-Transfer Numeric Receipt Gate", ""])
    if pack.get("scaled_transfer_numeric_receipt_gate"):
        gate = pack["scaled_transfer_numeric_receipt_gate"]
        lines.append(
            f"- `{gate['summary']}`; passed=`{gate['passed']}`; "
            f"complete={gate['n_complete_receipts']}/"
            f"{gate['n_receipts_declared']}"
        )
        for warning in gate.get("advisory_warnings", []):
            lines.append(f"- warning: {warning}")
        for violation in gate.get("violations", []):
            lines.append(
                f"- violation: `{violation.get('type')}` "
                f"{violation.get('missing_fields', violation.get('fields', ''))}"
            )
    else:
        lines.append("- (not selected)")
    lines.extend(["", "## Owner-Geometry Core Receipt Gate", ""])
    if pack.get("owner_geometry_core_receipt_gate"):
        gate = pack["owner_geometry_core_receipt_gate"]
        lines.append(
            f"- `{gate['summary']}`; passed=`{gate['passed']}`; "
            f"complete={gate['n_complete_receipts']}/"
            f"{gate['n_receipts_declared']}"
        )
        for warning in gate.get("advisory_warnings", []):
            lines.append(f"- warning: {warning}")
        for violation in gate.get("violations", []):
            lines.append(
                f"- violation: `{violation.get('type')}` "
                f"{violation.get('missing_fields', violation.get('fields', ''))}"
            )
    else:
        lines.append("- (not selected)")
    lines.extend(["", "## Fresh-Annular Anti-Laundering Gate", ""])
    if pack.get("fresh_annular_anti_laundering_gate"):
        gate = pack["fresh_annular_anti_laundering_gate"]
        lines.append(
            f"- `{gate['summary']}`; passed=`{gate['passed']}`; "
            f"complete={gate['n_complete_receipts']}/"
            f"{gate['n_receipts_declared']}"
        )
        for warning in gate.get("advisory_warnings", []):
            lines.append(f"- warning: {warning}")
        for violation in gate.get("violations", []):
            lines.append(
                f"- violation: `{violation.get('type')}` "
                f"{violation.get('missing_fields', violation.get('fields', ''))}"
            )
    else:
        lines.append("- (not selected)")
    lines.extend(["", "## Fresh-Annular Non-Disguise Gate", ""])
    if pack.get("fresh_annular_non_disguise_gate"):
        gate = pack["fresh_annular_non_disguise_gate"]
        lines.append(
            f"- `{gate['summary']}`; passed=`{gate['passed']}`; "
            f"complete={gate['n_complete_receipts']}/"
            f"{gate['n_receipts_declared']}"
        )
        for warning in gate.get("advisory_warnings", []):
            lines.append(f"- warning: {warning}")
        for violation in gate.get("violations", []):
            lines.append(
                f"- violation: `{violation.get('type')}` "
                f"{violation.get('missing_fields', violation.get('fields', ''))}"
            )
    else:
        lines.append("- (not selected)")
    lines.extend(["", "## Fresh-Annular Innovation Gate", ""])
    if pack.get("fresh_annular_innovation_gate"):
        gate = pack["fresh_annular_innovation_gate"]
        lines.append(
            f"- `{gate['summary']}`; passed=`{gate['passed']}`; "
            f"complete={gate['n_complete_receipts']}/"
            f"{gate['n_receipts_declared']}"
        )
        for warning in gate.get("advisory_warnings", []):
            lines.append(f"- warning: {warning}")
        for violation in gate.get("violations", []):
            lines.append(
                f"- violation: `{violation.get('type')}` "
                f"{violation.get('missing_fields', violation.get('fields', ''))}"
            )
    else:
        lines.append("- (not selected)")
    lines.extend(["", "## Section-Fixed Unsigned Variation Gate", ""])
    if pack.get("section_fixed_unsigned_variation_gate"):
        gate = pack["section_fixed_unsigned_variation_gate"]
        lines.append(
            f"- `{gate['summary']}`; passed=`{gate['passed']}`; "
            f"complete={gate['n_complete_receipts']}/"
            f"{gate['n_receipts_declared']}"
        )
        for warning in gate.get("advisory_warnings", []):
            lines.append(f"- warning: {warning}")
        for violation in gate.get("violations", []):
            lines.append(
                f"- violation: `{violation.get('type')}` "
                f"{violation.get('missing_fields', violation.get('fields', ''))}"
            )
    else:
        lines.append("- (not selected)")
    lines.extend(["", "## Inequality Prefilter", ""])
    if pack["inequality_checks"]:
        for check in pack["inequality_checks"]:
            if check.get("lhs") is not None:
                label = f"{check.get('lhs')} {check.get('op')} {check.get('rhs')}"
            else:
                label = check.get("candidate_inequality") or "<unparsed>"
            detail = check.get("violations", [])
            if check.get("reason"):
                detail = [*detail, {"reason": check.get("reason")}]
            lines.append(
                f"- `{label}`: `passed={check.get('passed')}` {detail}"
            )
    else:
        lines.append("- (no candidate inequalities supplied)")
    lines.extend(["", "## Curriculum", ""])
    if pack["curriculum_variants"]:
        for item in pack["curriculum_variants"]:
            if "error" in item:
                lines.append(f"- ERROR: {item['error']}")
            else:
                lines.append(f"- `{item['transform']}` -> `{item['lean_path']}`")
    else:
        hints = TRANSFORM_HINTS.get(pack["gap_classification"].get("gap_type"), [])
        lines.append(f"- Suggested transforms: {', '.join(hints) if hints else '(none)'}")
    lines.extend([
        "",
        "## Anti-Tautology Notes",
        "",
        "- This pack nominates context only; it does not prove a theorem.",
        "- If a rubric already enables GP-180 / framer / in-loop falsifiers, use those core ZTARE mechanisms rather than duplicating them here.",
        "- Treat `Prop` fields as declarations unless paired with paid proof fields.",
        "- Promote only compiler-checked Lean, concrete falsifiers, or named missing primitives.",
    ])
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build an RD caller pack over existing ZTARE PDE/scout primitives")
    ap.add_argument("--target", required=True)
    ap.add_argument("--field")
    ap.add_argument(
        "--mode",
        choices=["audit", "pde-execution"],
        default="audit",
        help=(
            "audit builds the existing context pack; pde-execution also emits "
            "required estimate/falsifier/theorem-match work-unit templates."
        ),
    )
    ap.add_argument(
        "--min-work-units",
        type=int,
        default=3,
        help="Minimum work-unit count requested in pde-execution mode.",
    )
    ap.add_argument(
        "--hostile-packet-suite",
        default="ns_default",
        help="Hostile packet suite to include in pde-execution mode.",
    )
    ap.add_argument(
        "--target-currency",
        help="Target proof currency for the pde-execution currency ledger.",
    )
    ap.add_argument("--candidate-inequality", action="append", default=[])
    ap.add_argument("--dimensional-features-json", type=Path)
    ap.add_argument(
        "--allowed-endpoint",
        action="append",
        default=[],
        help="Identifier allowed in candidate inequalities; repeatable.",
    )
    ap.add_argument(
        "--allowed-json",
        type=Path,
        help="JSON list of identifiers allowed in candidate inequalities.",
    )
    ap.add_argument("--aux-keyword")
    ap.add_argument("--top-lemmas", type=int, default=12)
    ap.add_argument("--top-aux", type=int, default=5)
    ap.add_argument("--emit-curriculum", action="store_true")
    ap.add_argument("--curriculum-transform", action="append", default=[])
    ap.add_argument(
        "--pi-group-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-PI-GROUP-FORCING check. "
            "Shape: {label, quantity_dim, subset_dims}."
        ),
    )
    ap.add_argument(
        "--dimensionless-exponent-source-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-DIMENSIONLESS-EXPONENT-SOURCE. "
            "Shape: {label, expression, dimensionless_variables, receipts}."
        ),
    )
    ap.add_argument(
        "--ambiguous-pi-pinning-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-AMBIGUOUS-PI-PINNING. "
            "Shape: {label, pi_group_result|ambiguous, receipts}."
        ),
    )
    ap.add_argument(
        "--persistence-budget-exponent-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-PERSISTENCE-BUDGET-EXPONENT. "
            "Shape: {label, dimension, persistence_exponent, "
            "thickness_or_reach_receipt, uniform_complexity_receipt, "
            "same_carrier_receipt}."
        ),
    )
    ap.add_argument(
        "--moment-ratio-surplus-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-MOMENT-RATIO-SURPLUS check. "
            "Shape: {label, first_moment_sq, second_moment_cap, "
            "cheap_boundary_lower_bound, threshold_space_measure}."
        ),
    )
    ap.add_argument(
        "--bounded-ratio-support-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-BOUNDED-RATIO-SUPPORT check. "
            "Shape: {label, mean_surplus, ratio_upper_bound, "
            "companion_lower_bound, threshold_space_measure}."
        ),
    )
    ap.add_argument(
        "--finite-prefix-selection-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-FINITE-PREFIX-SELECTION check. "
            "Shape: {label, boundary, interface, prefix_length, "
            "same_source_family, prefix_fixed_before_payoff, "
            "boundary_interface_units_aligned, no_post_payoff_selection, "
            "interface_floor}."
        ),
    )
    ap.add_argument(
        "--event-family-binding-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-EVENT-FAMILY-BINDING check. "
            "Shape: {label, target_event_family, source_event_family, "
            "event_identity, pre_payoff_timing, same_carrier, "
            "same_owner_or_source, index_map, index_map_total_on_prefix, "
            "no_proxy_family, no_post_payoff_selection}."
        ),
    )
    ap.add_argument(
        "--analogical-transfer-receipt-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a "
            "G-ANALOGICAL-TRANSFER-RECEIPT check. Shape: {label, "
            "donor_domain, donor_pattern, donor_invariant, target_domain, "
            "target_obligation, mapping, preserved_structure, loss_budget, "
            "target_receipt_or_gate, nearest_confuser, confuser_distinction, "
            "falsifier_or_kill_condition, concrete_next_check}."
        ),
    )
    ap.add_argument(
        "--prefix-count-bridge-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-PREFIX-COUNT-BRIDGE check. "
            "Shape: {label, target_prefix_family, source_prefix_family, "
            "target_count, source_count, source_budget, prefix_index_map, "
            "map_total_on_target_prefix, pointwise_assignment_or_injection, "
            "target_count_le_source_count, source_count_le_budget, "
            "target_count_le_budget_conclusion, fixed_before_payoff, "
            "not_target_defined, no_post_payoff_selection, "
            "no_rebilling_same_source_atom, no_endpoint_restatement, "
            "nearest_confuser, confuser_distinction}."
        ),
    )
    ap.add_argument(
        "--source-prefix-budget-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-SOURCE-PREFIX-BUDGET check. "
            "Shape: {label, source_prefix_family, budget_family, "
            "source_count, budget_count, budget_index, prefix_to_budget_map, "
            "map_total_on_source_prefix, pointwise_budget_assignment, "
            "source_count_le_budget, fixed_before_payoff, "
            "same_owner_or_source, bounded_fanout_or_multiplicity, "
            "no_logarithmic_reuse, no_rebilling_same_source_atom, "
            "not_target_defined, no_post_payoff_selection, "
            "no_endpoint_restatement, nearest_confuser, confuser_distinction}."
        ),
    )
    ap.add_argument(
        "--final-slot-indexed-source-budget-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a "
            "G-FINAL-SLOT-INDEXED-SOURCE-BUDGET check. Shape: {label, "
            "source_prefix_family, source_prefix_definition, event_stream, "
            "final_slot_index, source_count, budget_count, source_slot_map, "
            "identity_on_final_slot_prefix, map_total_on_indexed_prefix, "
            "source_slot_injective, event_data_binding, same_tree_lock_binding, "
            "displayed_fanout_or_no_log_reuse, fixed_before_payoff, "
            "not_target_defined, no_post_payoff_slot_truncation, "
            "no_rebilling_same_source_atom, no_endpoint_capacity_restatement, "
            "remaining_target_assignment_obligation, nearest_confuser, "
            "confuser_distinction}."
        ),
    )
    ap.add_argument(
        "--target-indexed-event-assignment-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-TARGET-INDEXED-EVENT-ASSIGNMENT-PROVENANCE. Shape: {label, "
            "mode, target_prefix_family, target_prefix_definition, "
            "target_count, indexed_event_stream, "
            "indexed_event_prefix_definition, event_prefix_index, "
            "event_count, incidence_geometry, same_tree_or_carrier_binding, "
            "fixed_before_payoff, not_target_defined, "
            "no_post_payoff_assignment_pruning, "
            "no_endpoint_capacity_restatement, nearest_confuser, "
            "confuser_distinction, plus mode-specific construction, "
            "reduction, or refutation fields}."
        ),
    )
    ap.add_argument(
        "--incidence-derived-finite-injection-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-INCIDENCE-DERIVED-FINITE-INJECTION. Shape: {label, "
            "incidence_source, domain_predicate, codomain_event_family, "
            "map_extraction_rule, totality_derivation, "
            "uniqueness_or_collision_exclusion, injectivity_derivation, "
            "same_event_family_binding, finite_domain, finite_codomain, "
            "no_post_payoff_choice, not_cardinality_as_injectivity, "
            "not_label_only_incidence, nearest_confuser, "
            "downstream_cardinality_bridge}."
        ),
    )
    ap.add_argument(
        "--bounded-incident-existence-eventdata-horizon-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-BOUNDED-INCIDENT-EXISTENCE-EVENTDATA-HORIZON. Shape: "
            "{label, target_family, target_event_candidate, "
            "candidate_event_selector, eventdata_binding, horizon_bound, "
            "incidence_witness, bounded_existence_derivation, "
            "prefix_domination_binding, same_tree_binding, "
            "fixed_before_payoff, no_post_payoff_choice, "
            "not_target_deficit_selected, not_label_only_eventdata, "
            "not_label_only_incidence, downstream_no_reuse_collision_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--target-event-candidate-cover-selection-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-TARGET-EVENT-CANDIDATE-COVER-SELECTION. Shape: {label, "
            "target_family, cover_relation, cover_selector, "
            "selector_totality, horizon_from_cover, incidence_from_cover, "
            "eventdata_binding, prefix_domination_binding, same_tree_binding, "
            "fixed_before_payoff, no_post_payoff_selection, "
            "not_target_deficit_selected, not_label_only_cover, "
            "not_label_only_eventdata, downstream_eventdata_horizon_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--target-cover-eventdata-incidence-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-TARGET-COVER-EVENTDATA-INCIDENCE. Shape: {label, "
            "target_family, eventdata_source, target_node_source, "
            "cover_event_selector, cover_relation_definition, "
            "selector_totality, cover_relation_is_selector_graph, "
            "selector_below_final_slot, selector_incident_to_target, "
            "cover_to_horizon_law, cover_to_incidence_law, "
            "same_tree_binding, prefix_domination_binding, "
            "incidence_geometry_binding, fixed_before_payoff, "
            "no_post_payoff_cover_choice, not_target_deficit_selected, "
            "not_label_only_eventdata, not_label_only_incidence, "
            "not_label_only_cover, downstream_cover_selection_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--cover-event-selector-finalslot-assignment-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-COVER-EVENT-SELECTOR-FINALSLOT-ASSIGNMENT. Shape: {label, "
            "target_family, final_slot_assignment, assignment_codomain, "
            "cover_event_selector_definition, selector_is_assignment_value, "
            "selector_below_final_slot, assignment_incidence_law, "
            "selector_incidence_transport, eventdata_binding, "
            "same_tree_binding, prefix_domination_binding, "
            "incidence_geometry_binding, assignment_totality, "
            "assignment_fixed_before_payoff, not_target_deficit_selected, "
            "no_post_payoff_assignment, not_endpoint_capacity_only, "
            "not_label_only_assignment, not_label_only_eventdata, "
            "not_label_only_incidence, downstream_eventdata_incidence_cover_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--target-slot-bounded-incidence-least-hit-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-TARGET-SLOT-BOUNDED-INCIDENCE-LEAST-HIT. Shape: {label, "
            "target_family, incidence_relation, bounded_incident_existence_theorem, "
            "least_hit_target_slot_rule, target_slot_codomain, "
            "target_slot_bound_derivation, target_slot_incidence_law, "
            "same_tree_eventdata_binding, prefix_domination_binding, "
            "fanout_no_reuse_binding, assignment_totality, "
            "assignment_fixed_before_payoff, no_post_payoff_least_hit_choice, "
            "no_post_payoff_existence_choice, not_target_deficit_selected, "
            "not_endpoint_capacity_only, not_cardinality_as_injectivity, "
            "not_label_only_assignment, not_label_only_eventdata, "
            "not_label_only_incidence, downstream_finalslot_assignment_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--bounded-incident-existence-sametree-eventdata-index-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-BOUNDED-INCIDENT-EXISTENCE-SAMETREE-EVENTDATA-INDEX. Shape: "
            "{label, target_family, same_tree_eventdata_stream, "
            "target_eventdata_index, target_eventdata_codomain, "
            "eventdata_binding, index_below_final_slot, displayed_incidence_law, "
            "bounded_existence_witness_rule, same_tree_binding, "
            "prefix_domination_binding, fanout_no_reuse_binding, "
            "fixed_before_payoff, no_post_payoff_index_choice, "
            "not_target_deficit_selected, not_endpoint_capacity_only, "
            "not_label_only_eventdata, not_label_only_incidence, "
            "downstream_least_hit_targetslot_source, nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--target-eventdata-index-prefix-cover-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-TARGET-EVENTDATA-INDEX-PREFIX-COVER. Shape: {label, "
            "target_family, prefix_cover_relation, selected_eventdata_index, "
            "selected_index_codomain, selected_index_covers_target, "
            "eventdata_binding_rule, cover_to_incidence_law, "
            "same_tree_binding, prefix_domination_binding, "
            "incidence_geometry_binding, cover_relation_total_before_payoff, "
            "selected_index_fixed_before_payoff, not_target_deficit_selected, "
            "not_endpoint_capacity_only, not_label_only_cover, "
            "not_label_only_eventdata, not_label_only_incidence, "
            "downstream_sametree_eventdata_index_source, nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--finite-scale-cofinality-prefix-cover-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-FINITE-SCALE-COFINALITY-PREFIX-COVER. Shape: {label, "
            "target_family, finite_scale_prefix_comparison, "
            "event_prefix_cofinality, selected_eventdata_index, "
            "selected_index_codomain, cover_relation_definition, "
            "cover_relation_is_guarded_graph, selected_index_cover_membership, "
            "selected_index_incidence_law, cover_to_incidence_transport, "
            "same_tree_binding, prefix_domination_primitive_binding, "
            "incidence_geometry_binding, selected_index_fixed_before_payoff, "
            "not_arbitrary_cover_relation, not_endpoint_capacity_only, "
            "not_label_only_prefix_domination, not_post_payoff_selection, "
            "downstream_prefix_cover_source, nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--event-to-badnode-selected-index-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-EVENT-TO-BADNODE-SELECTED-INDEX. Shape: {label, "
            "target_family, finite_event_prefix_index, selected_index_codomain, "
            "event_to_badnode_map, target_node_event_to_badnode_equality, "
            "event_prefix_membership_source, displayed_incidence_refinement, "
            "selected_index_incidence_transport, same_tree_binding, "
            "prefix_domination_primitive_binding, incidence_geometry_binding, "
            "event_node_identification_binding, selected_index_fixed_before_payoff, "
            "not_arbitrary_selected_index, not_endpoint_capacity_only, "
            "not_event_to_badnode_label_only, not_incidence_label_only, "
            "not_post_payoff_selection, downstream_finite_scale_cofinality_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--event-prefix-coverage-selected-index-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-EVENT-PREFIX-COVERAGE-SELECTED-INDEX. Shape: {label, "
            "target_family, coverage_packet, selected_prefix_event_index, "
            "selected_index_codomain, event_prefixes_exhaust_selected_bad_nodes, "
            "every_selected_bad_node_appears_in_some_prefix, "
            "prefix_dominates_finite_selected_bad_tree_beta_sum, "
            "duplicate_events_charge_multiplicity, "
            "no_shell_only_enumeration_shortcut, "
            "no_adaptive_stopping_from_beta_sum, "
            "target_node_event_to_badnode_equality, "
            "displayed_incidence_refinement, selected_index_incidence_transport, "
            "same_tree_binding, event_node_identification_binding, "
            "selected_index_fixed_before_payoff, not_coverage_label_only, "
            "not_arbitrary_selected_index, not_endpoint_capacity_only, "
            "not_post_payoff_selection, "
            "downstream_event_to_badnode_selected_index_source, nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--coverage-choice-finite-selector-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-COVERAGE-CHOICE-FINITE-SELECTOR. Shape: {label, "
            "target_family, coverage_packet, coverage_choice_witness, "
            "selected_index_definition, selected_index_codomain, "
            "target_node_selected_bad_membership, choice_from_appearance_field, "
            "choice_uses_target_membership, event_to_badnode_target_equality, "
            "displayed_incidence_refinement, selected_index_incidence_transport, "
            "same_tree_binding, event_node_identification_binding, "
            "event_prefixes_exhaust_selected_bad_nodes, "
            "every_selected_bad_node_appears_in_some_prefix, "
            "prefix_dominates_finite_selected_bad_tree_beta_sum, "
            "duplicate_events_charge_multiplicity, "
            "no_shell_only_enumeration_shortcut, "
            "no_adaptive_stopping_from_beta_sum, "
            "coverage_choice_fixed_before_payoff, "
            "not_classical_choice_from_bare_appearance, "
            "not_endpoint_capacity_only, not_post_payoff_selection, "
            "downstream_event_prefix_coverage_selected_index_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--typed-appearance-coverage-choice-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-TYPED-APPEARANCE-COVERAGE-CHOICE. Shape: {label, "
            "target_family, typed_selected_bad_node_appearance, "
            "target_node_selected_bad_membership, coverage_choice_specialization, "
            "selected_index_codomain, event_to_badnode_target_equality, "
            "coverage_packet, appearance_refines_coverage, "
            "appearance_uses_target_membership, displayed_incidence_refinement, "
            "same_tree_binding, event_node_identification_binding, "
            "event_prefixes_exhaust_selected_bad_nodes, "
            "every_selected_bad_node_appears_in_some_prefix, "
            "prefix_dominates_finite_selected_bad_tree_beta_sum, "
            "duplicate_events_charge_multiplicity, "
            "no_shell_only_enumeration_shortcut, "
            "no_adaptive_stopping_from_beta_sum, "
            "typed_appearance_fixed_before_payoff, "
            "not_classical_choice_from_bare_appearance, "
            "not_endpoint_capacity_only, not_post_payoff_selection, "
            "downstream_coverage_choice_finite_selector_source, nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--typed-coverage-packet-appearance-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-TYPED-COVERAGE-PACKET-APPEARANCE. Shape: {label, "
            "target_family, ordinary_coverage_packet, typed_coverage_packet, "
            "typed_selected_bad_node_appearance, "
            "coverage_packet_forwards_exhaustion, "
            "coverage_packet_forwards_prop_appearance, "
            "coverage_packet_forwards_beta_domination, "
            "coverage_packet_forwards_multiplicity, "
            "coverage_packet_forwards_no_shell_only, "
            "coverage_packet_forwards_no_adaptive_beta_sum, "
            "target_node_selected_bad_membership, "
            "target_membership_specialization, "
            "event_to_badnode_target_equality, displayed_incidence_refinement, "
            "same_tree_binding, typed_appearance_fixed_before_payoff, "
            "not_bare_prop_choice, not_endpoint_capacity_only, "
            "not_post_payoff_selection, "
            "downstream_typed_appearance_coverage_choice_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--event-prefix-enumeration-packet-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-EVENT-PREFIX-ENUMERATION-PACKET. Shape: {label, "
            "target_family, ordinary_coverage_packet, "
            "selected_bad_node_event_prefix_enumeration, enumeration_codomain, "
            "enumeration_refines_coverage_appearance, "
            "enumeration_bounded_by_final_event_prefix, "
            "enumeration_uses_same_bad_center_event_nodes, "
            "enumeration_uses_event_to_badnode, event_to_badnode_target_equality, "
            "coverage_packet_forwards_exhaustion, "
            "coverage_packet_forwards_prop_appearance, "
            "coverage_packet_forwards_beta_domination, "
            "coverage_packet_forwards_multiplicity, "
            "coverage_packet_forwards_no_shell_only, "
            "coverage_packet_forwards_no_adaptive_beta_sum, "
            "enumeration_fixed_before_payoff, not_bare_prop_choice, "
            "not_endpoint_capacity_only, not_shell_only_enumeration, "
            "not_post_payoff_selection, downstream_typed_coverage_packet, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--bounded-natural-event-enumeration-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-BOUNDED-NATURAL-EVENT-ENUMERATION. Shape: {label, "
            "target_family, ordinary_coverage_packet, "
            "selected_bad_node_natural_event_enumeration, "
            "natural_index_codomain, strict_prefix_bound, "
            "event_to_badnode_target_equality, "
            "natural_enumeration_refines_coverage_appearance, "
            "natural_enumeration_uses_same_bad_center_event_nodes, "
            "natural_enumeration_uses_event_to_badnode, "
            "coverage_packet_forwards_exhaustion, "
            "coverage_packet_forwards_prop_appearance, "
            "coverage_packet_forwards_beta_domination, "
            "coverage_packet_forwards_multiplicity, "
            "coverage_packet_forwards_no_shell_only, "
            "coverage_packet_forwards_no_adaptive_beta_sum, "
            "natural_enumeration_fixed_before_payoff, "
            "not_bare_prop_choice, not_endpoint_capacity_only, "
            "not_shell_only_enumeration, not_post_payoff_selection, "
            "downstream_event_prefix_enumeration_source, nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--unbounded-event-witness-prefix-bound-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-UNBOUNDED-EVENT-WITNESS-PREFIX-BOUND. Shape: {label, "
            "target_family, ordinary_coverage_packet, "
            "selected_bad_node_natural_event_witness, "
            "event_to_badnode_target_equality, same_witness_prefix_bound, "
            "strict_prefix_bound, witness_refines_cofinal_selected_tree_incidence, "
            "prefix_bound_comes_from_final_event_prefix, "
            "witness_uses_same_bad_center_event_nodes, "
            "witness_uses_event_to_badnode, coverage_packet_forwards_exhaustion, "
            "coverage_packet_forwards_prop_appearance, "
            "coverage_packet_forwards_beta_domination, "
            "coverage_packet_forwards_multiplicity, "
            "coverage_packet_forwards_no_shell_only, "
            "coverage_packet_forwards_no_adaptive_beta_sum, "
            "witness_and_bound_fixed_before_payoff, not_bare_prop_choice, "
            "not_endpoint_capacity_only, not_shell_only_enumeration, "
            "not_post_payoff_selection, "
            "downstream_bounded_natural_event_enumeration_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--cofinal-incidence-witness-bound-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-COFINAL-INCIDENCE-WITNESS-BOUND. Shape: {label, "
            "target_family, ordinary_coverage_packet, "
            "cofinal_selected_tree_incidence_receipt, selected_bad_node_has_event, "
            "chosen_event_witness, chosen_event_to_badnode_equality, "
            "same_chosen_witness_prefix_bound, strict_prefix_bound, "
            "cofinal_incidence_refines_coverage_appearance, "
            "prefix_bound_comes_from_final_event_prefix, "
            "cofinal_incidence_uses_same_bad_center_event_nodes, "
            "cofinal_witness_uses_event_to_badnode, "
            "coverage_packet_forwards_exhaustion, "
            "coverage_packet_forwards_prop_appearance, "
            "coverage_packet_forwards_beta_domination, "
            "coverage_packet_forwards_multiplicity, "
            "coverage_packet_forwards_no_shell_only, "
            "coverage_packet_forwards_no_adaptive_beta_sum, "
            "cofinal_witness_and_bound_fixed_before_payoff, "
            "not_bare_prop_choice_beyond_cofinal_receipt, "
            "not_endpoint_capacity_only, not_shell_only_enumeration, "
            "not_post_payoff_selection, "
            "downstream_unbounded_event_witness_prefix_bound_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--explicit-cofinal-event-witness-bound-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-EXPLICIT-COFINAL-EVENT-WITNESS-BOUND. Shape: {label, "
            "target_family, ordinary_coverage_packet, "
            "cofinal_selected_tree_incidence_receipt, "
            "explicit_cofinal_event_witness, explicit_event_to_badnode_equality, "
            "same_explicit_witness_prefix_bound, strict_prefix_bound, "
            "explicit_witness_refines_cofinal_incidence, "
            "prefix_bound_comes_from_final_event_prefix, "
            "explicit_witness_uses_same_bad_center_event_nodes, "
            "explicit_witness_uses_event_to_badnode, "
            "coverage_packet_forwards_exhaustion, "
            "coverage_packet_forwards_prop_appearance, "
            "coverage_packet_forwards_beta_domination, "
            "coverage_packet_forwards_multiplicity, "
            "coverage_packet_forwards_no_shell_only, "
            "coverage_packet_forwards_no_adaptive_beta_sum, "
            "explicit_witness_and_bound_fixed_before_payoff, "
            "not_bare_prop_choice_for_explicit_witness, "
            "not_endpoint_capacity_only, not_shell_only_enumeration, "
            "not_post_payoff_selection, "
            "downstream_unbounded_event_witness_prefix_bound_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--cofinal-event-selector-final-prefix-bound-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-COFINAL-EVENT-SELECTOR-FINAL-PREFIX-BOUND. Shape: {label, "
            "target_family, ordinary_coverage_packet, "
            "cofinal_selected_tree_incidence_receipt, cofinal_event_selector, "
            "selector_event_to_badnode_equality, "
            "same_selector_final_prefix_bound, strict_prefix_bound, "
            "selector_refines_cofinal_incidence, "
            "selector_bound_comes_from_final_event_prefix, "
            "selector_uses_same_bad_center_event_nodes, "
            "selector_uses_event_to_badnode, coverage_packet_forwards_exhaustion, "
            "coverage_packet_forwards_prop_appearance, "
            "coverage_packet_forwards_beta_domination, "
            "coverage_packet_forwards_multiplicity, "
            "coverage_packet_forwards_no_shell_only, "
            "coverage_packet_forwards_no_adaptive_beta_sum, "
            "selector_and_bound_fixed_before_payoff, "
            "not_bare_prop_choice_for_selector, not_endpoint_capacity_only, "
            "not_shell_only_enumeration, not_post_payoff_selection, "
            "downstream_explicit_cofinal_event_witness_bound_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--finite-cofinal-event-selector-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-FINITE-COFINAL-EVENT-SELECTOR. Shape: {label, target_family, "
            "ordinary_coverage_packet, cofinal_selected_tree_incidence_receipt, "
            "finite_cofinal_event_selector, finite_selector_codomain, "
            "finite_selector_event_to_badnode_equality, "
            "strict_prefix_bound_from_fin_codomain, "
            "finite_selector_refines_cofinal_incidence, "
            "finite_selector_codomain_is_final_event_prefix, "
            "finite_selector_uses_same_bad_center_event_nodes, "
            "finite_selector_uses_event_to_badnode, "
            "coverage_packet_forwards_exhaustion, "
            "coverage_packet_forwards_prop_appearance, "
            "coverage_packet_forwards_beta_domination, "
            "coverage_packet_forwards_multiplicity, "
            "coverage_packet_forwards_no_shell_only, "
            "coverage_packet_forwards_no_adaptive_beta_sum, "
            "finite_selector_fixed_before_payoff, "
            "not_bare_prop_choice_for_finite_selector, "
            "not_endpoint_capacity_only, not_shell_only_enumeration, "
            "not_post_payoff_selection, "
            "downstream_cofinal_event_selector_final_prefix_bound_source, "
            "nearest_confuser}."
        ),
    )
    ap.add_argument(
        "--positive-variation-bridge-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-POSITIVE-VARIATION-BRIDGE "
            "check. Shape: {label, signed_source, positive_variation_source, "
            "same_carrier, numeric_domination, event_scope, "
            "fixed_before_payoff, no_post_payoff_positive_part, "
            "no_target_deficit_definition}."
        ),
    )
    ap.add_argument(
        "--positive-variation-quotient-wash-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-POSITIVE-VARIATION-QUOTIENT-WASH "
            "check. Shape: {label, net_or_quotient_source_law, "
            "positive_variation_or_turnover_currency, same_source_or_owner_binding, "
            "pre_payoff_representative_fixed, no_wash_cycle_law, "
            "no_null_cycle_growth, bounded_positive_variation_from_net_budget, "
            "no_post_payoff_grossing}."
        ),
    )
    ap.add_argument(
        "--quotient-minimal-carrier-payment-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-QUOTIENT-MINIMAL-CARRIER-PAYMENT "
            "check. Shape: {label, quotient_source_law, "
            "minimal_carrier_definition, selected_production_functional, "
            "pre_payoff_representative_selector, "
            "selector_independent_of_target_deficit, "
            "production_preserved_by_selector, "
            "kernel_cycles_zero_selected_production, "
            "minimal_carrier_bounds_selected_production}."
        ),
    )
    ap.add_argument(
        "--quadratic-quotient-descent-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-QUADRATIC-QUOTIENT-DESCENT "
            "check. Shape: {label, source_map_or_equivalence, "
            "quadratic_functional, polarized_bilinear_form, "
            "source_kernel_definition, representative_selector, "
            "selector_fixed_before_payoff, kernel_square_zero_or_nonpositive, "
            "kernel_cross_zero_or_nonpositive, quotient_descent_or_bound, "
            "not_defined_by_target_deficit}."
        ),
    )
    ap.add_argument(
        "--nonadaptive-source-selection-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-NONADAPTIVE-SOURCE-SELECTION "
            "check. Shape: {label, source_object, extractor_or_selection_rule, "
            "source_family, owner_or_carrier_binding, index_or_selection_map, "
            "fixed_before_payoff, selection_rule_declared_before_target, "
            "target_not_used_to_define_source, timing_receipt, "
            "no_post_payoff_selection}."
        ),
    )
    ap.add_argument(
        "--support-index-law-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-SUPPORT-INDEX-LAW. Shape: "
            "{label, support_index_map, support_domain, membership_law, "
            "restricted_prefix_law, injectivity_law, totality_law, "
            "pointwise_lower_transfer_law, boundary_payment_transfer_law, "
            "fixed_before_payoff, not_target_defined, no_post_payoff_pruning}."
        ),
    )
    ap.add_argument(
        "--support-index-injectivity-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-SUPPORT-INDEX-INJECTIVITY. "
            "Shape: {label, support_index_map, support_domain, "
            "order_or_separation_law, collision_exclusion_derivation, "
            "equality_reflection_law, injectivity_scope, fixed_before_payoff, "
            "not_target_defined, no_post_payoff_reindexing, "
            "no_cardinality_label_as_injectivity, no_packing_label_as_injectivity}."
        ),
    )
    ap.add_argument(
        "--support-index-affine-order-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-SUPPORT-INDEX-AFFINE-ORDER. "
            "Shape: {label, support_index_map, support_domain, affine_base, "
            "affine_stride, positive_stride, affine_formula_on_domain, "
            "strict_order_derivation, fixed_before_payoff, not_target_defined, "
            "no_post_payoff_reindexing, no_cardinality_label_as_order, "
            "no_packing_label_as_order}."
        ),
    )
    ap.add_argument(
        "--support-index-fixed-step-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-SUPPORT-INDEX-FIXED-STEP. "
            "Shape: {label, support_index_map, support_domain, base_at_zero, "
            "step_stride, positive_stride, successor_step_law, "
            "induction_derivation, fixed_before_payoff, not_target_defined, "
            "no_post_payoff_reindexing, no_cardinality_label_as_step, "
            "no_packing_label_as_step, no_selected_event_as_step}."
        ),
    )
    ap.add_argument(
        "--support-index-adjacent-gap-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-SUPPORT-INDEX-ADJACENT-GAP. "
            "Shape: {label, support_index_map, adjacent_pair_domain, "
            "owner_or_carrier_binding, base_at_zero, adjacent_gap_map, "
            "gap_stride, positive_stride, support_index_succ_eq_add_gap, "
            "adjacent_gap_eq_stride_on_prefix, successor_step_derivation, "
            "same_owner_adjacent_step_receipt, fixed_before_payoff, "
            "not_target_defined, no_post_payoff_pair_selection, "
            "no_strict_order_label_as_gap, no_cardinality_label_as_gap, "
            "no_packing_label_as_gap, no_selected_event_as_gap}."
        ),
    )
    ap.add_argument(
        "--support-index-unit-gap-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-SUPPORT-INDEX-UNIT-GAP. "
            "Shape: {label, support_index_map, adjacent_pair_domain, "
            "owner_or_carrier_binding, base_at_zero, unit_gap_law, "
            "unit_gap_positive, support_index_succ_eq_succ, "
            "adjacent_gap_constructor, stride_one_derivation, "
            "fixed_before_payoff, not_target_defined, "
            "no_post_payoff_pair_selection, "
            "no_strict_order_label_as_unit_gap, "
            "no_cardinality_label_as_unit_gap, "
            "no_packing_label_as_unit_gap, no_selected_event_as_unit_gap}."
        ),
    )
    ap.add_argument(
        "--support-index-no-hole-unit-gap-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-SUPPORT-INDEX-NO-HOLE-UNIT-GAP. "
            "Shape: {label, support_index_map, adjacent_pair_domain, "
            "owner_or_carrier_binding, base_at_zero, strict_successor_order, "
            "no_between_adjacent_support_index, nat_successor_derivation, "
            "unit_gap_constructor, fixed_before_payoff, not_target_defined, "
            "no_post_payoff_pair_selection, no_strict_order_only_as_no_hole, "
            "no_cardinality_label_as_no_hole, no_packing_label_as_no_hole, "
            "no_selected_event_as_no_hole}."
        ),
    )
    ap.add_argument(
        "--support-index-endpoint-tight-no-hole-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-SUPPORT-INDEX-ENDPOINT-TIGHT-NO-HOLE. Shape: "
            "{label, support_index_map, support_length, prefix_domain, "
            "base_index, base_anchor_at_zero, endpoint_lower_bound_on_prefix, "
            "endpoint_upper_bound_on_prefix, "
            "pointwise_eq_base_plus_k_derived_from_bounds, "
            "strict_order_on_prefix_holds_or_derived, "
            "adjacent_endpoint_eq_left, adjacent_endpoint_eq_right, "
            "nat_no_between_successive_endpoints, no_hole_constructor, "
            "level475_skipped_slot_rejected_by_upper_bound, "
            "not_level464_no_hole_assumed, not_unit_gap_assumed, "
            "not_affine_stride_one_assumed_without_bounds}."
        ),
    )
    ap.add_argument(
        "--support-index-base-anchored-strict-lower-bound-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-SUPPORT-INDEX-BASE-ANCHORED-STRICT-LOWER-BOUND. Shape: "
            "{label, support_index_map, support_length, prefix_domain, "
            "base_index, base_anchor_at_zero, strict_order_on_prefix, "
            "same_owner_base_and_support_index, nonempty_zero_domain_guard, "
            "predecessor_prefix_closure, nat_strict_step_implies_successor_le, "
            "lower_bound_induction_base, lower_bound_induction_step, "
            "derived_endpoint_lower_bound_on_prefix, "
            "upper_endpoint_bound_live_debt, "
            "level475_skipped_slot_still_admitted}."
        ),
    )
    ap.add_argument(
        "--support-index-final-endpoint-capacity-upper-bound-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-SUPPORT-INDEX-FINAL-ENDPOINT-CAPACITY-UPPER-BOUND. Shape: "
            "{label, support_index_map, support_length, prefix_domain, "
            "base_index, final_slot, support_length_eq_succ_final_slot, "
            "strict_order_on_prefix, tail_step_count_from_strict_order, "
            "final_endpoint_capacity_bound, nat_tail_capacity_cancellation, "
            "derived_endpoint_upper_bound_on_prefix, "
            "level475_skipped_slot_rejected_by_final_capacity}."
        ),
    )
    ap.add_argument(
        "--support-index-final-slot-upper-bound-tail-capacity-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-SUPPORT-INDEX-FINAL-SLOT-UPPER-BOUND-TAIL-CAPACITY. Shape: "
            "{label, support_index_map, support_length, prefix_domain, "
            "base_index, final_slot, support_length_eq_succ_final_slot, "
            "strict_order_on_prefix, tail_step_count_from_strict_order, "
            "final_slot_upper_bound_tail_capacity, "
            "nat_tail_capacity_cancellation, "
            "derived_endpoint_upper_bound_on_prefix, "
            "level475_skipped_slot_rejected_by_final_capacity}."
        ),
    )
    ap.add_argument(
        "--support-index-tail-capacity-failure-witness-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-SUPPORT-INDEX-TAIL-CAPACITY-FAILURE-WITNESS. Shape: "
            "{label, support_index_map, support_index_values, support_length, "
            "prefix_domain, base_index, final_slot, "
            "support_length_eq_succ_final_slot, capacity_failure_index, "
            "base_anchor_at_zero_holds, strict_order_on_prefix_holds, "
            "lower_endpoint_bound_on_prefix_holds, "
            "final_endpoint_capacity_bound_fails, "
            "tail_capacity_inequality_fails, "
            "derived_upper_endpoint_bound_fails, "
            "level477_lower_bound_still_holds}."
        ),
    )
    ap.add_argument(
        "--support-index-skipped-slot-hostile-witness-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-SUPPORT-INDEX-SKIPPED-SLOT-HOSTILE-WITNESS. Shape: "
            "{label, support_index_map, support_index_values, support_length, "
            "prefix_domain, adjacent_pair_index, adjacent_pair_domain, "
            "strict_order_on_prefix_holds, injectivity_on_prefix_holds, "
            "finite_image_cardinality_eq_support_length_holds, "
            "skipped_slot_witness, skipped_slot_between_adjacent_values, "
            "no_prefix_preimage_for_skipped_slot, "
            "no_between_adjacent_support_index_fails, "
            "unit_successor_law_fails, interval_image_totality_fails, "
            "not_empty_domain_vacuity, fixed_before_payoff, "
            "not_target_defined, nearest_confuser_level474_distinction, "
            "nearest_confuser_level465_distinction}."
        ),
    )
    ap.add_argument(
        "--support-index-interval-image-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-SUPPORT-INDEX-INTERVAL-IMAGE. "
            "Shape: {label, support_index_map, prefix_domain, "
            "owner_or_carrier_binding, base_at_zero, strict_order_on_prefix, "
            "adjacent_interval_totality, strict_order_collision_exclusion, "
            "no_hole_constructor, fixed_before_payoff, not_target_defined, "
            "no_post_payoff_interval_filling, "
            "no_strict_order_only_as_interval_image, "
            "no_cardinality_label_as_interval_image, "
            "no_packing_label_as_interval_image, "
            "no_selected_event_as_interval_image}."
        ),
    )
    ap.add_argument(
        "--support-index-interval-preimage-selector-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-SUPPORT-INDEX-INTERVAL-PREIMAGE-SELECTOR. "
            "Shape: {label, support_index_map, prefix_domain, "
            "owner_or_carrier_binding, base_at_zero, strict_order_on_prefix, "
            "interval_preimage_selector, selector_domain_totality, "
            "selector_prefix_membership, selector_maps_to_requested_nat, "
            "selector_not_skolemized_from_interval_image_totality, "
            "interval_image_constructor, fixed_before_payoff, "
            "not_target_defined, no_post_payoff_selector_filling, "
            "no_exists_label_only_as_selector, no_strict_order_only_as_selector, "
            "no_cardinality_label_as_selector, no_packing_label_as_selector, "
            "no_selected_event_as_selector}."
        ),
    )
    ap.add_argument(
        "--support-index-least-interval-preimage-selector-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-SUPPORT-INDEX-LEAST-INTERVAL-PREIMAGE-SELECTOR. "
            "Shape: {label, support_index_map, prefix_domain, "
            "same_support_index_same_prefix, owner_or_carrier_binding, "
            "base_at_zero, strict_order_on_prefix, least_selector_function, "
            "bounded_search_domain, candidate_predicate_exact, "
            "bounded_search_provenance, search_success_certificate, "
            "search_success_not_from_interval_image_totality, "
            "search_success_not_from_level467_selector, "
            "no_classical_choice_or_nat_find_from_existential, "
            "least_prefix_membership, least_maps_to_requested_nat, "
            "least_minimality_law, interval_preimage_selector_constructor, "
            "fixed_before_payoff, not_target_defined, no_post_payoff_search, "
            "no_least_label_only, no_minimal_label_only, "
            "no_bounded_search_label_only, no_packing_label_as_least_selector, "
            "no_selected_event_as_least_selector}."
        ),
    )
    ap.add_argument(
        "--support-index-first-hit-interval-preimage-selector-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-SUPPORT-INDEX-FIRST-HIT-INTERVAL-PREIMAGE-SELECTOR. "
            "Shape: {label, support_index_map, prefix_domain, "
            "same_support_index_same_prefix, owner_or_carrier_binding, "
            "base_at_zero, strict_order_on_prefix, first_hit_function, "
            "bounded_search_domain, candidate_predicate_exact, "
            "bounded_search_provenance, first_hit_success_certificate, "
            "success_not_from_interval_image_totality, "
            "success_not_from_level467_selector, "
            "success_not_from_level469_least_selector, "
            "no_classical_choice_or_nat_find_from_existential, "
            "first_hit_prefix_membership, first_hit_maps_to_requested_nat, "
            "no_prior_candidate_law, least_selector_constructor, "
            "fixed_before_payoff, not_target_defined, no_post_payoff_search, "
            "no_first_hit_label_only, no_bounded_search_label_only, "
            "no_packing_label_as_first_hit_selector, "
            "no_selected_event_as_first_hit_selector}."
        ),
    )
    ap.add_argument(
        "--support-index-vacuous-first-hit-adapter-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for "
            "G-SUPPORT-INDEX-VACUOUS-FIRST-HIT-ADAPTER. Shape: "
            "{label, support_index_map, prefix_domain, source_no_hole_receipt, "
            "skipped_slot_domain_empty_by_no_hole, no_hole_source_field, "
            "dummy_first_hit_function, first_hit_membership_from_false, "
            "first_hit_image_equality_from_false, no_prior_candidate_from_false, "
            "strict_source_constructor_chain, "
            "not_independent_bounded_search_certificate, "
            "not_new_source_mechanism, next_lever_returns_to_no_hole_geometry, "
            "no_level465_interval_image_import, no_level467_selector_import, "
            "no_level469_least_selector_import, no_classical_choice_or_nat_find, "
            "fixed_before_payoff, not_target_defined, "
            "no_packing_label_as_vacuity, no_selected_event_as_vacuity}."
        ),
    )
    ap.add_argument(
        "--finite-support-extraction-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-FINITE-SUPPORT-EXTRACTION. "
            "Shape: {label, finite_support_object, support_predicate, "
            "membership_equivalence, cardinality_length_alignment, "
            "enumeration_map, enumeration_totality, selected_membership_law, "
            "restricted_prefix_membership, fixed_before_payoff, "
            "not_target_defined, no_measure_only_extraction, no_label_only_packing}."
        ),
    )
    ap.add_argument(
        "--finite-image-support-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for G-FINITE-IMAGE-SUPPORT. Shape: "
            "{label, domain_finset, image_map, image_support_object, "
            "support_object_is_image, membership_iff_exists_domain, "
            "selected_membership_from_domain, totality_from_image_membership, "
            "injective_on_domain, card_image_eq_domain_card, "
            "domain_card_eq_length, restricted_prefix_on_image, "
            "fixed_before_payoff, not_target_defined, "
            "no_post_payoff_domain_pruning}."
        ),
    )
    ap.add_argument(
        "--no-rebilling-freshness-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-NO-REBILLING-FRESHNESS check. "
            "Shape: {label, selected_units, payment_atoms, assignment_map, "
            "assignment_total_on_prefix, distinctness_or_disjointness, "
            "no_rebilling_same_atom, prefix_budget_bound, fixed_before_payoff, "
            "same_owner_or_source, overlap_or_multiplicity_bound}."
        ),
    )
    ap.add_argument(
        "--same-carrier-packing-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-SAME-CARRIER-PACKING check. "
            "Shape: {label, source_carrier, target_payment_family, "
            "assignment_or_injection_map, assignment_total_on_prefix, "
            "same_carrier_binding, overlap_or_multiplicity_bound, "
            "finite_prefix_budget, pre_payoff_timing, no_nested_reuse, "
            "no_rebilling_same_atom}."
        ),
    )
    ap.add_argument(
        "--metric-covering-selection-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-METRIC-COVERING-SELECTION "
            "check. Shape: {label, ambient_metric_or_quasi_metric, "
            "source_family, scale_or_radius_function, "
            "doubling_or_besicovitch_constant, "
            "bounded_eccentricity_or_engulfing, selection_rule, "
            "selection_totality_or_paid_omission, "
            "pre_payoff_selection_timing, same_carrier_binding, "
            "bounded_overlap_conclusion, nested_children_policy, "
            "discarded_or_nested_error_budget}."
        ),
    )
    ap.add_argument(
        "--linear-observable-coercivity-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a G-LINEAR-OBS-COERCIVITY check. "
            "Shape: {label, target_dimension, observable_rank, receipts...}."
        ),
    )
    ap.add_argument(
        "--residual-normal-form-profile",
        type=Path,
        default=DEFAULT_RESIDUAL_NORMAL_FORM_PROFILE,
        help=(
            "JSON residual normal-form profile. Pass an empty string to disable."
        ),
    )
    ap.add_argument(
        "--single-spend-field",
        action="append",
        default=[],
        help=(
            "Field name or name:type pair for the RD single-spend carrier "
            "audit; repeatable."
        ),
    )
    ap.add_argument(
        "--single-spend-from-target",
        action="store_true",
        help=(
            "Also run the single-spend audit over fields extracted from the "
            "target declaration in the workmap or live Lean source."
        ),
    )
    ap.add_argument(
        "--owner-preimage-receipt-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a pec_k owner-preimage receipt. "
            "Each receipt should include owner_map, pre_payoff_timing, "
            "full_output_scale_owner, pointwise_payment, finite_atom_budget, "
            "multiplicity_bound, and owner_preimage_prefix_inequality."
        ),
    )
    ap.add_argument(
        "--scaled-transfer-numeric-receipt-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a scaled-transfer numeric receipt. "
            "Each receipt should include source_quantity, event_index_map, "
            "pointwise_numeric_statement, prop_to_numeric_bridge, consumed_by, "
            "and downstream_receipt."
        ),
    )
    ap.add_argument(
        "--owner-geometry-core-receipt-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a TICK668 owner-geometry-core "
            "receipt. Each receipt should include owner_map_timing, "
            "output_scale_owner, selected_prefix_preimage, "
            "bounded_projection_multiplicity, same_carrier_owner_budget, "
            "anti_laundering, and consumed_by."
        ),
    )
    ap.add_argument(
        "--fresh-annular-anti-laundering-receipt-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a fresh-annular anti-laundering "
            "receipt. Each receipt should include not_monotone_tail, "
            "not_scalar_measure, not_uniform_enstrophy_disguise, "
            "source_selection_not_declaration_only, same_separated_source, "
            "and consumed_by."
        ),
    )
    ap.add_argument(
        "--fresh-annular-non-disguise-receipt-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a fresh-annular non-disguise "
            "morphology receipt. Each receipt should include "
            "not_monotone_tail, not_scalar_measure, "
            "not_uniform_enstrophy_disguise, same_separated_source, "
            "and consumed_by."
        ),
    )
    ap.add_argument(
        "--fresh-annular-innovation-receipt-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a fresh-annular innovation "
            "anti-laundering receipt. Each receipt should include "
            "invoice_filtration, coarse_predictable_part, innovation_part, "
            "innovation_mass_lower_bound, same_source_binding, "
            "nondeclaration_binding, non_disguise_morphology_consequence, "
            "source_nondeclaration_timing_consequence, and consumed_by."
        ),
    )
    ap.add_argument(
        "--section-fixed-unsigned-variation-receipt-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a section-fixed unsigned "
            "variation receipt. Each receipt should include "
            "lower_envelope_uses_section, parent_crown_fixed_by_section, "
            "unshadowed_crown_fixed_by_section, "
            "child_shadow_crown_fixed_by_section, "
            "localized_unsigned_variation_measure, "
            "variation_measure_fixed_before_payoff, "
            "positive_variation_before_route_budget, "
            "no_parent_invoice_positive_part_selection, "
            "child_shadow_not_from_parent_deficit, "
            "unshadowed_mass_pays_production, "
            "child_shadow_mass_pays_inherited_reserve, "
            "same_event_stream_binding, and consumed_by."
        ),
    )
    ap.add_argument(
        "--limit-passage-step-json",
        action="append",
        default=[],
        help=(
            "JSON literal or file path for a limit-passage step. Each step "
            "should include name, sequence_described, inheritance_lemma, "
            "and property_inherited."
        ),
    )
    ap.add_argument(
        "--finite-prefix-results",
        action="store_true",
        help="Declare finite-prefix results that require a limit-passage check.",
    )
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument(
        "--semantic-mathlib-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "When the shape-tagged Mathlib shelf returns 0 hits, also query "
            "the gemini-embedding-001 Mathlib atlas for vocabulary-invariant "
            "neighbours. Additive fallback only; never replaces the tag-typed "
            "shelf. Atlas: scripts/public/lean/build_mathlib_atlas_embeddings.py. "
            "Default ON (post-2026-05-25 calibration); pass "
            "--no-semantic-mathlib-fallback to disable."
        ),
    )
    ap.add_argument(
        "--semantic-mathlib-threshold",
        type=float,
        default=0.55,
        help="Cosine threshold for the Mathlib semantic fallback (default 0.55).",
    )
    ap.add_argument(
        "--semantic-mathlib-top-k",
        type=int,
        default=8,
        help="Top-K hits to surface in the semantic fallback (default 8).",
    )
    ap.add_argument(
        "--semantic-mathlib-untagged-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Restrict the semantic fallback to lemmas with empty shape-tag "
            "lists (the 61%% of Mathlib entries the shape-tagged shelf cannot "
            "see). Default ON — cleanest information gain, disjoint from the "
            "tag-typed shelf. Pass --no-semantic-mathlib-untagged-only to "
            "query the full 46K atlas."
        ),
    )
    ap.add_argument(
        "--include-basin-context",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Include NS enriched-basin signals for the typed --target in the "
            "pack JSON: tag fingerprint, refutation edges, atlas-bridge "
            "open-obligation proximity. Default ON. Silently empty if the "
            "enriched basin file isn't built yet."
        ),
    )
    ap.add_argument(
        "--semantic-apn-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Query the AlphaProof Nexus (APN) corpus for cross-repo lemma "
            "matches. APN includes monotone-operator iterate-convergence "
            "machinery (Ryu-Yuan-Yin) directly applicable to NS Leray-Hopf "
            "sequence analysis. Default ON. Filtered to NS-relevant domains "
            "(optimization, additive_combinatorics, graphs)."
        ),
    )
    ap.add_argument(
        "--semantic-apn-threshold",
        type=float, default=0.55,
        help="Cosine threshold for APN bridges (default 0.55).",
    )
    ap.add_argument(
        "--semantic-apn-top-k",
        type=int, default=5,
        help="Top-K APN matches per target (default 5).",
    )
    args = ap.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = safe_slug(f"{args.target}_{args.field or 'target'}")
    out_root = args.out_dir if args.out_dir.is_absolute() else REPO / args.out_dir
    out_dir = out_root / f"{stamp}_{slug}"
    out_dir.mkdir(parents=True, exist_ok=True)

    context = load_target_context(args.target, args.field)
    gap = classify_gap_local(args.target, args.field)
    gap_type = str(gap.get("gap_type") or "UNKNOWN")
    transforms = list(args.curriculum_transform)
    if args.emit_curriculum and not transforms:
        transforms = TRANSFORM_HINTS.get(gap_type, [])[:2]
    extra_allowed = set(str(x) for x in args.allowed_endpoint)
    if args.allowed_json:
        raw_allowed = _json_or_file(args.allowed_json)
        if not isinstance(raw_allowed, list):
            raise SystemExit("--allowed-json must be a JSON list or a path to one")
        extra_allowed.update(str(x) for x in raw_allowed)
    single_spend_fields = list(args.single_spend_field)
    single_spend_source = "manual"
    if args.single_spend_from_target:
        extracted = single_spend_fields_from_context(context)
        single_spend_fields.extend(extracted)
        single_spend_source = (
            "manual+target" if args.single_spend_field else "target"
        )
    owner_preimage_receipts = [
        _json_or_file(raw) for raw in args.owner_preimage_receipt_json
    ]
    for i, receipt in enumerate(owner_preimage_receipts):
        if not isinstance(receipt, dict):
            raise SystemExit(
                f"--owner-preimage-receipt-json entry {i} must be a JSON object"
            )
    scaled_transfer_numeric_receipts = [
        _json_or_file(raw) for raw in args.scaled_transfer_numeric_receipt_json
    ]
    for i, receipt in enumerate(scaled_transfer_numeric_receipts):
        if not isinstance(receipt, dict):
            raise SystemExit(
                "--scaled-transfer-numeric-receipt-json entry "
                f"{i} must be a JSON object"
            )
    owner_geometry_core_receipts = [
        _json_or_file(raw) for raw in args.owner_geometry_core_receipt_json
    ]
    for i, receipt in enumerate(owner_geometry_core_receipts):
        if not isinstance(receipt, dict):
            raise SystemExit(
                "--owner-geometry-core-receipt-json entry "
                f"{i} must be a JSON object"
            )
    fresh_annular_anti_laundering_receipts = [
        _json_or_file(raw)
        for raw in args.fresh_annular_anti_laundering_receipt_json
    ]
    for i, receipt in enumerate(fresh_annular_anti_laundering_receipts):
        if not isinstance(receipt, dict):
            raise SystemExit(
                "--fresh-annular-anti-laundering-receipt-json entry "
                f"{i} must be a JSON object"
            )
    fresh_annular_non_disguise_receipts = [
        _json_or_file(raw)
        for raw in args.fresh_annular_non_disguise_receipt_json
    ]
    for i, receipt in enumerate(fresh_annular_non_disguise_receipts):
        if not isinstance(receipt, dict):
            raise SystemExit(
                "--fresh-annular-non-disguise-receipt-json entry "
                f"{i} must be a JSON object"
            )
    fresh_annular_innovation_receipts = [
        _json_or_file(raw)
        for raw in args.fresh_annular_innovation_receipt_json
    ]
    for i, receipt in enumerate(fresh_annular_innovation_receipts):
        if not isinstance(receipt, dict):
            raise SystemExit(
                "--fresh-annular-innovation-receipt-json entry "
                f"{i} must be a JSON object"
            )
    section_fixed_unsigned_variation_receipts = [
        _json_or_file(raw)
        for raw in args.section_fixed_unsigned_variation_receipt_json
    ]
    for i, receipt in enumerate(section_fixed_unsigned_variation_receipts):
        if not isinstance(receipt, dict):
            raise SystemExit(
                "--section-fixed-unsigned-variation-receipt-json entry "
                f"{i} must be a JSON object"
            )
    limit_passage_steps = [
        _json_or_file(raw) for raw in args.limit_passage_step_json
    ]
    for i, step in enumerate(limit_passage_steps):
        if not isinstance(step, dict):
            raise SystemExit(
                f"--limit-passage-step-json entry {i} must be a JSON object"
            )
    pde_ops = suggest_pde_craft_ops(
        gap_type,
        args.target,
        args.field,
        args.candidate_inequality,
        context=context,
    )
    mathlib_lemmas = fetch_lemmas(gap_type, top=args.top_lemmas)
    mathlib_semantic_fallback: dict[str, Any] | None = None
    if args.semantic_mathlib_fallback and not mathlib_lemmas:
        # Additive fallback: only fires when the shape-tagged shelf returned
        # 0 hits. Preserves the 0-hit information signal in the main slot
        # while surfacing semantic neighbours in a clearly-labelled secondary
        # field.
        try:
            from ztare.research_director.mathlib_semantic import (
                mathlib_semantic_neighbours,
                MathlibSemanticHit,
            )
        except Exception as exc:
            mathlib_semantic_fallback = {
                "enabled": True,
                "fired": False,
                "skip_reason": f"mathlib_semantic import failed: {exc}",
                "hits": [],
            }
        else:
            rationale = (gap.get("rationale") or "") if isinstance(gap, dict) else ""
            query = " ".join(
                p for p in (args.target, args.field, gap_type, rationale) if p
            ).strip()
            hits, corpus_size, filtered_size, skip_reason = mathlib_semantic_neighbours(
                query,
                top_k=args.semantic_mathlib_top_k,
                threshold=args.semantic_mathlib_threshold,
                untagged_only=args.semantic_mathlib_untagged_only,
            )
            mathlib_semantic_fallback = {
                "enabled": True,
                "fired": skip_reason is None,
                "query": query,
                "threshold": args.semantic_mathlib_threshold,
                "top_k": args.semantic_mathlib_top_k,
                "untagged_only": args.semantic_mathlib_untagged_only,
                "corpus_size": corpus_size,
                "filtered_size": filtered_size,
                "skip_reason": skip_reason,
                "hits": [
                    {
                        "name": h.name,
                        "kind": h.kind,
                        "file": h.file,
                        "cosine": h.cosine,
                        "preview": h.preview,
                        "shapes": h.shapes,
                    }
                    for h in hits
                ],
                "note": (
                    "Additive fallback (shape-tagged shelf was empty for "
                    "this gap_type). Treat as candidate lemmas to verify, "
                    "NOT as a typed shelf — the 0-hit on the main shelf "
                    "still carries information."
                ),
            }
    basin_context = (
        _load_basin_context_for_target(args.target)
        if args.include_basin_context else None
    )

    pack = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "target": args.target,
        "field": args.field,
        "tool_scope": (
            "RD caller over existing ZTARE primitives; not a second "
            "autoresearch loop or replacement workbench"
        ),
        "target_context": context,
        "gap_classification": gap,
        "source_currency_discriminator": classify_source_currency(
            args.target,
            args.field,
            args.target_currency,
            context.get("doc") if isinstance(context, dict) else None,
            gap.get("gap_type") if isinstance(gap, dict) else None,
            gap.get("rationale") if isinstance(gap, dict) else None,
        ),
        "mathlib_lemmas": mathlib_lemmas,
        "mathlib_semantic_fallback": mathlib_semantic_fallback,
        "basin_context": basin_context,
        "apn_semantic_neighbors": (
            _load_apn_semantic_for_target(
                args.target, args.field,
                context=context,
                gap=gap,
                basin_context=basin_context,
                pde_ops=pde_ops,
                candidate_inequalities=args.candidate_inequality,
                target_currency=args.target_currency,
                threshold=args.semantic_apn_threshold,
                top_k=args.semantic_apn_top_k,
            ) if args.semantic_apn_fallback else None
        ),
        "auxiliary_families": fetch_auxiliary_families(
            gap_type, keyword=args.aux_keyword, top=args.top_aux),
        "pde_craft_ops": pde_ops,
        "pde_execution_contract": (
            build_pde_execution_contract(
                pde_ops,
                min_work_units=args.min_work_units,
                hostile_suite=args.hostile_packet_suite,
                target_currency=args.target_currency,
            )
            if args.mode == "pde-execution"
            else None
        ),
        "estimate_skeletons": generate_pde_estimate_skeletons(
            target=args.target,
            field=args.field,
            gap_type=gap_type,
            context=context,
            inequalities=args.candidate_inequality,
        ),
        "residual_normal_form": run_residual_normal_form(
            None
            if str(args.residual_normal_form_profile) == ""
            else args.residual_normal_form_profile,
            args.target,
            args.field,
            args.candidate_inequality,
            context=context,
        ),
        "limit_passage_gate": run_limit_passage_audit(
            gap_type,
            limit_passage_steps,
            finite_prefix_results=args.finite_prefix_results,
        ),
        "moment_ratio_surplus_checks": run_moment_ratio_surplus_checks([
            _json_or_file(raw) for raw in args.moment_ratio_surplus_json
        ]),
        "bounded_ratio_support_checks": run_bounded_ratio_support_checks([
            _json_or_file(raw) for raw in args.bounded_ratio_support_json
        ]),
        "finite_prefix_selection_checks": run_finite_prefix_selection_checks([
            _json_or_file(raw) for raw in args.finite_prefix_selection_json
        ]),
        "event_family_binding_checks": run_event_family_binding_checks([
            _json_or_file(raw) for raw in args.event_family_binding_json
        ]),
        "analogical_transfer_receipt_checks": run_analogical_transfer_receipt_checks([
            _json_or_file(raw) for raw in args.analogical_transfer_receipt_json
        ]),
        "prefix_count_bridge_checks": run_prefix_count_bridge_checks([
            _json_or_file(raw) for raw in args.prefix_count_bridge_json
        ]),
        "source_prefix_budget_checks": run_source_prefix_budget_checks([
            _json_or_file(raw) for raw in args.source_prefix_budget_json
        ]),
        "final_slot_indexed_source_budget_checks":
            run_final_slot_indexed_source_budget_checks([
                _json_or_file(raw)
                for raw in args.final_slot_indexed_source_budget_json
            ]),
        "target_indexed_event_assignment_checks":
            run_target_indexed_event_assignment_checks([
                _json_or_file(raw)
                for raw in args.target_indexed_event_assignment_json
            ]),
        "incidence_derived_finite_injection_checks":
            run_incidence_derived_finite_injection_checks([
                _json_or_file(raw)
                for raw in args.incidence_derived_finite_injection_json
            ]),
        "bounded_incident_existence_eventdata_horizon_checks":
            run_bounded_incident_existence_eventdata_horizon_checks([
                _json_or_file(raw)
                for raw in args.bounded_incident_existence_eventdata_horizon_json
            ]),
        "target_event_candidate_cover_selection_checks":
            run_target_event_candidate_cover_selection_checks([
                _json_or_file(raw)
                for raw in args.target_event_candidate_cover_selection_json
            ]),
        "target_cover_eventdata_incidence_checks":
            run_target_cover_eventdata_incidence_checks([
                _json_or_file(raw)
                for raw in args.target_cover_eventdata_incidence_json
            ]),
        "cover_event_selector_finalslot_assignment_checks":
            run_cover_event_selector_finalslot_assignment_checks([
                _json_or_file(raw)
                for raw in args.cover_event_selector_finalslot_assignment_json
            ]),
        "target_slot_bounded_incidence_least_hit_checks":
            run_target_slot_bounded_incidence_least_hit_checks([
                _json_or_file(raw)
                for raw in args.target_slot_bounded_incidence_least_hit_json
            ]),
        "bounded_incident_existence_sametree_eventdata_index_checks":
            run_bounded_incident_existence_sametree_eventdata_index_checks([
                _json_or_file(raw)
                for raw in args.bounded_incident_existence_sametree_eventdata_index_json
            ]),
        "target_eventdata_index_prefix_cover_checks":
            run_target_eventdata_index_prefix_cover_checks([
                _json_or_file(raw)
                for raw in args.target_eventdata_index_prefix_cover_json
            ]),
        "finite_scale_cofinality_prefix_cover_checks":
            run_finite_scale_cofinality_prefix_cover_checks([
                _json_or_file(raw)
                for raw in args.finite_scale_cofinality_prefix_cover_json
            ]),
        "event_to_badnode_selected_index_checks":
            run_event_to_badnode_selected_index_checks([
                _json_or_file(raw)
                for raw in args.event_to_badnode_selected_index_json
            ]),
        "event_prefix_coverage_selected_index_checks":
            run_event_prefix_coverage_selected_index_checks([
                _json_or_file(raw)
                for raw in args.event_prefix_coverage_selected_index_json
            ]),
        "coverage_choice_finite_selector_checks":
            run_coverage_choice_finite_selector_checks([
                _json_or_file(raw)
                for raw in args.coverage_choice_finite_selector_json
            ]),
        "typed_appearance_coverage_choice_checks":
            run_typed_appearance_coverage_choice_checks([
                _json_or_file(raw)
                for raw in args.typed_appearance_coverage_choice_json
            ]),
        "typed_coverage_packet_appearance_checks":
            run_typed_coverage_packet_appearance_checks([
                _json_or_file(raw)
                for raw in args.typed_coverage_packet_appearance_json
            ]),
        "event_prefix_enumeration_packet_checks":
            run_event_prefix_enumeration_packet_checks([
                _json_or_file(raw)
                for raw in args.event_prefix_enumeration_packet_json
            ]),
        "bounded_natural_event_enumeration_checks":
            run_bounded_natural_event_enumeration_checks([
                _json_or_file(raw)
                for raw in args.bounded_natural_event_enumeration_json
            ]),
        "unbounded_event_witness_prefix_bound_checks":
            run_unbounded_event_witness_prefix_bound_checks([
                _json_or_file(raw)
                for raw in args.unbounded_event_witness_prefix_bound_json
            ]),
        "cofinal_incidence_witness_bound_checks":
            run_cofinal_incidence_witness_bound_checks([
                _json_or_file(raw)
                for raw in args.cofinal_incidence_witness_bound_json
            ]),
        "explicit_cofinal_event_witness_bound_checks":
            run_explicit_cofinal_event_witness_bound_checks([
                _json_or_file(raw)
                for raw in args.explicit_cofinal_event_witness_bound_json
            ]),
        "cofinal_event_selector_final_prefix_bound_checks":
            run_cofinal_event_selector_final_prefix_bound_checks([
                _json_or_file(raw)
                for raw in args.cofinal_event_selector_final_prefix_bound_json
            ]),
        "finite_cofinal_event_selector_checks":
            run_finite_cofinal_event_selector_checks([
                _json_or_file(raw)
                for raw in args.finite_cofinal_event_selector_json
            ]),
        "positive_variation_bridge_checks": run_positive_variation_bridge_checks([
            _json_or_file(raw) for raw in args.positive_variation_bridge_json
        ]),
        "positive_variation_quotient_wash_checks":
            run_positive_variation_quotient_wash_checks([
                _json_or_file(raw)
                for raw in args.positive_variation_quotient_wash_json
            ]),
        "quotient_minimal_carrier_payment_checks":
            run_quotient_minimal_carrier_payment_checks([
                _json_or_file(raw)
                for raw in args.quotient_minimal_carrier_payment_json
            ]),
        "quadratic_quotient_descent_checks":
            run_quadratic_quotient_descent_checks([
                _json_or_file(raw)
                for raw in args.quadratic_quotient_descent_json
            ]),
        "nonadaptive_source_selection_checks": run_nonadaptive_source_selection_checks([
            _json_or_file(raw) for raw in args.nonadaptive_source_selection_json
        ]),
        "support_index_law_checks": run_support_index_law_checks([
            _json_or_file(raw) for raw in args.support_index_law_json
        ]),
        "support_index_injectivity_checks": run_support_index_injectivity_checks([
            _json_or_file(raw) for raw in args.support_index_injectivity_json
        ]),
        "support_index_affine_order_checks": run_support_index_affine_order_checks([
            _json_or_file(raw) for raw in args.support_index_affine_order_json
        ]),
        "support_index_fixed_step_checks": run_support_index_fixed_step_checks([
            _json_or_file(raw) for raw in args.support_index_fixed_step_json
        ]),
        "support_index_adjacent_gap_checks": run_support_index_adjacent_gap_checks([
            _json_or_file(raw) for raw in args.support_index_adjacent_gap_json
        ]),
        "support_index_unit_gap_checks": run_support_index_unit_gap_checks([
            _json_or_file(raw) for raw in args.support_index_unit_gap_json
        ]),
        "support_index_no_hole_unit_gap_checks": run_support_index_no_hole_unit_gap_checks([
            _json_or_file(raw) for raw in args.support_index_no_hole_unit_gap_json
        ]),
        "support_index_endpoint_tight_no_hole_checks":
            run_support_index_endpoint_tight_no_hole_checks([
                _json_or_file(raw)
                for raw in args.support_index_endpoint_tight_no_hole_json
            ]),
        "support_index_base_anchored_strict_lower_bound_checks":
            run_support_index_base_anchored_strict_lower_bound_checks([
                _json_or_file(raw)
                for raw in args.support_index_base_anchored_strict_lower_bound_json
            ]),
        "support_index_final_endpoint_capacity_upper_bound_checks":
            run_support_index_final_endpoint_capacity_upper_bound_checks([
                _json_or_file(raw)
                for raw in args.support_index_final_endpoint_capacity_upper_bound_json
            ]),
        "support_index_final_slot_upper_bound_tail_capacity_checks":
            run_support_index_final_slot_upper_bound_tail_capacity_checks([
                _json_or_file(raw)
                for raw in args.support_index_final_slot_upper_bound_tail_capacity_json
            ]),
        "support_index_tail_capacity_failure_witness_checks":
            run_support_index_tail_capacity_failure_witness_checks([
                _json_or_file(raw)
                for raw in args.support_index_tail_capacity_failure_witness_json
            ]),
        "support_index_skipped_slot_hostile_witness_checks":
            run_support_index_skipped_slot_hostile_witness_checks([
                _json_or_file(raw)
                for raw in args.support_index_skipped_slot_hostile_witness_json
            ]),
        "support_index_interval_image_checks": run_support_index_interval_image_checks([
            _json_or_file(raw) for raw in args.support_index_interval_image_json
        ]),
        "support_index_interval_preimage_selector_checks": run_support_index_interval_preimage_selector_checks([
            _json_or_file(raw) for raw in args.support_index_interval_preimage_selector_json
        ]),
        "support_index_least_interval_preimage_selector_checks":
            run_support_index_least_interval_preimage_selector_checks([
                _json_or_file(raw)
                for raw in args.support_index_least_interval_preimage_selector_json
            ]),
        "support_index_first_hit_interval_preimage_selector_checks":
            run_support_index_first_hit_interval_preimage_selector_checks([
                _json_or_file(raw)
                for raw in args.support_index_first_hit_interval_preimage_selector_json
            ]),
        "support_index_vacuous_first_hit_adapter_checks":
            run_support_index_vacuous_first_hit_adapter_checks([
                _json_or_file(raw)
                for raw in args.support_index_vacuous_first_hit_adapter_json
            ]),
        "finite_support_extraction_checks": run_finite_support_extraction_checks([
            _json_or_file(raw) for raw in args.finite_support_extraction_json
        ]),
        "finite_image_support_checks": run_finite_image_support_checks([
            _json_or_file(raw) for raw in args.finite_image_support_json
        ]),
        "no_rebilling_freshness_checks": run_no_rebilling_freshness_checks([
            _json_or_file(raw) for raw in args.no_rebilling_freshness_json
        ]),
        "same_carrier_packing_checks": run_same_carrier_packing_checks([
            _json_or_file(raw) for raw in args.same_carrier_packing_json
        ]),
        "metric_covering_selection_checks": run_metric_covering_selection_checks([
            _json_or_file(raw) for raw in args.metric_covering_selection_json
        ]),
        "pi_group_checks": run_pi_group_checks([
            _json_or_file(raw) for raw in args.pi_group_json
        ]),
        "ambiguous_pi_pinning_checks": run_ambiguous_pi_pinning_checks([
            _json_or_file(raw) for raw in args.ambiguous_pi_pinning_json
        ]),
        "dimensionless_exponent_source_checks":
            run_dimensionless_exponent_source_checks([
                _json_or_file(raw)
                for raw in args.dimensionless_exponent_source_json
            ]),
        "persistence_budget_exponent_checks":
            run_persistence_budget_exponent_checks([
                _json_or_file(raw)
                for raw in args.persistence_budget_exponent_json
            ]),
        "linear_observable_coercivity_checks":
            run_linear_observable_coercivity_checks([
                _json_or_file(raw)
                for raw in args.linear_observable_coercivity_json
            ]),
        "single_spend_audit": run_single_spend_audit(single_spend_fields),
        "single_spend_source": single_spend_source,
        "receipt_strength_audit": run_receipt_strength_audit_from_fields(
            single_spend_fields
        ),
        "owner_preimage_prefix_gate": run_owner_preimage_prefix_audit(
            pde_ops,
            owner_preimage_receipts,
        ),
        "scaled_transfer_numeric_receipt_gate":
            run_scaled_transfer_numeric_audit(
                args.target,
                args.field,
                context,
                scaled_transfer_numeric_receipts,
            ),
        "owner_geometry_core_receipt_gate":
            run_owner_geometry_core_audit(
                args.target,
                args.field,
                context,
                owner_geometry_core_receipts,
            ),
        "fresh_annular_anti_laundering_gate":
            run_fresh_annular_anti_laundering_audit(
                args.target,
                args.field,
                context,
                fresh_annular_anti_laundering_receipts,
            ),
        "fresh_annular_non_disguise_gate":
            run_fresh_annular_non_disguise_audit(
                args.target,
                args.field,
                context,
                fresh_annular_non_disguise_receipts,
            ),
        "fresh_annular_innovation_gate":
            run_fresh_annular_innovation_audit(
                args.target,
                args.field,
                context,
                fresh_annular_innovation_receipts,
            ),
        "section_fixed_unsigned_variation_gate":
            run_section_fixed_unsigned_variation_audit(
                args.target,
                args.field,
                context,
                section_fixed_unsigned_variation_receipts,
            ),
        "inequality_checks": check_inequalities(
            args.candidate_inequality,
            context,
            args.dimensional_features_json,
            extra_allowed=extra_allowed,
        ),
        "curriculum_variants": emit_curriculum_variants(
            args.target, transforms, out_dir) if args.emit_curriculum else [],
        "next_step_rule": (
            "Codex chooses a patch/falsifier route. Feed only verified snippets "
            "or summarized failure categories back into ZTARE briefing memory."
        ),
    }
    json_path = out_dir / "pack.json"
    md_path = out_dir / "pack.md"
    json_path.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(pack), encoding="utf-8")
    print(f"wrote: {json_path.relative_to(REPO)}")
    print(f"wrote: {md_path.relative_to(REPO)}")
    print(f"gap_type: {gap_type}")
    print(
        "source_currency_class: "
        f"{pack['source_currency_discriminator']['source_currency_class']}"
    )
    print(f"mathlib_lemmas: {len(pack['mathlib_lemmas'])}")
    print(f"auxiliary_families: {len(pack['auxiliary_families'])}")
    print(f"pde_craft_ops: {len(pack['pde_craft_ops'])}")
    print(f"estimate_skeletons: {len(pack['estimate_skeletons'])}")
    print(f"pde_execution_contract: {bool(pack.get('pde_execution_contract'))}")
    print(f"residual_normal_form: {bool(pack.get('residual_normal_form'))}")
    print(f"limit_passage_gate: {bool(pack.get('limit_passage_gate'))}")
    print(
        "moment_ratio_surplus_checks: "
        f"{len(pack['moment_ratio_surplus_checks'])}"
    )
    print(
        "bounded_ratio_support_checks: "
        f"{len(pack['bounded_ratio_support_checks'])}"
    )
    print(
        "finite_prefix_selection_checks: "
        f"{len(pack['finite_prefix_selection_checks'])}"
    )
    print(
        "event_family_binding_checks: "
        f"{len(pack['event_family_binding_checks'])}"
    )
    print(
        "analogical_transfer_receipt_checks: "
        f"{len(pack['analogical_transfer_receipt_checks'])}"
    )
    print(
        "prefix_count_bridge_checks: "
        f"{len(pack['prefix_count_bridge_checks'])}"
    )
    print(
        "source_prefix_budget_checks: "
        f"{len(pack['source_prefix_budget_checks'])}"
    )
    print(
        "final_slot_indexed_source_budget_checks: "
        f"{len(pack['final_slot_indexed_source_budget_checks'])}"
    )
    print(
        "target_indexed_event_assignment_checks: "
        f"{len(pack['target_indexed_event_assignment_checks'])}"
    )
    print(
        "incidence_derived_finite_injection_checks: "
        f"{len(pack['incidence_derived_finite_injection_checks'])}"
    )
    print(
        "bounded_incident_existence_eventdata_horizon_checks: "
        f"{len(pack['bounded_incident_existence_eventdata_horizon_checks'])}"
    )
    print(
        "target_event_candidate_cover_selection_checks: "
        f"{len(pack['target_event_candidate_cover_selection_checks'])}"
    )
    print(
        "target_cover_eventdata_incidence_checks: "
        f"{len(pack['target_cover_eventdata_incidence_checks'])}"
    )
    print(
        "cover_event_selector_finalslot_assignment_checks: "
        f"{len(pack['cover_event_selector_finalslot_assignment_checks'])}"
    )
    print(
        "target_slot_bounded_incidence_least_hit_checks: "
        f"{len(pack['target_slot_bounded_incidence_least_hit_checks'])}"
    )
    print(
        "bounded_incident_existence_sametree_eventdata_index_checks: "
        f"{len(pack['bounded_incident_existence_sametree_eventdata_index_checks'])}"
    )
    print(
        "target_eventdata_index_prefix_cover_checks: "
        f"{len(pack['target_eventdata_index_prefix_cover_checks'])}"
    )
    print(
        "finite_scale_cofinality_prefix_cover_checks: "
        f"{len(pack['finite_scale_cofinality_prefix_cover_checks'])}"
    )
    print(
        "event_to_badnode_selected_index_checks: "
        f"{len(pack['event_to_badnode_selected_index_checks'])}"
    )
    print(
        "event_prefix_coverage_selected_index_checks: "
        f"{len(pack['event_prefix_coverage_selected_index_checks'])}"
    )
    print(
        "coverage_choice_finite_selector_checks: "
        f"{len(pack['coverage_choice_finite_selector_checks'])}"
    )
    print(
        "typed_appearance_coverage_choice_checks: "
        f"{len(pack['typed_appearance_coverage_choice_checks'])}"
    )
    print(
        "typed_coverage_packet_appearance_checks: "
        f"{len(pack['typed_coverage_packet_appearance_checks'])}"
    )
    print(
        "event_prefix_enumeration_packet_checks: "
        f"{len(pack['event_prefix_enumeration_packet_checks'])}"
    )
    print(
        "bounded_natural_event_enumeration_checks: "
        f"{len(pack['bounded_natural_event_enumeration_checks'])}"
    )
    print(
        "unbounded_event_witness_prefix_bound_checks: "
        f"{len(pack['unbounded_event_witness_prefix_bound_checks'])}"
    )
    print(
        "cofinal_incidence_witness_bound_checks: "
        f"{len(pack['cofinal_incidence_witness_bound_checks'])}"
    )
    print(
        "explicit_cofinal_event_witness_bound_checks: "
        f"{len(pack['explicit_cofinal_event_witness_bound_checks'])}"
    )
    print(
        "cofinal_event_selector_final_prefix_bound_checks: "
        f"{len(pack['cofinal_event_selector_final_prefix_bound_checks'])}"
    )
    print(
        "finite_cofinal_event_selector_checks: "
        f"{len(pack['finite_cofinal_event_selector_checks'])}"
    )
    print(
        "positive_variation_bridge_checks: "
        f"{len(pack['positive_variation_bridge_checks'])}"
    )
    print(
        "positive_variation_quotient_wash_checks: "
        f"{len(pack['positive_variation_quotient_wash_checks'])}"
    )
    print(
        "quotient_minimal_carrier_payment_checks: "
        f"{len(pack['quotient_minimal_carrier_payment_checks'])}"
    )
    print(
        "quadratic_quotient_descent_checks: "
        f"{len(pack['quadratic_quotient_descent_checks'])}"
    )
    print(
        "nonadaptive_source_selection_checks: "
        f"{len(pack['nonadaptive_source_selection_checks'])}"
    )
    print(
        "support_index_law_checks: "
        f"{len(pack['support_index_law_checks'])}"
    )
    print(
        "support_index_injectivity_checks: "
        f"{len(pack['support_index_injectivity_checks'])}"
    )
    print(
        "support_index_affine_order_checks: "
        f"{len(pack['support_index_affine_order_checks'])}"
    )
    print(
        "support_index_fixed_step_checks: "
        f"{len(pack['support_index_fixed_step_checks'])}"
    )
    print(
        "support_index_adjacent_gap_checks: "
        f"{len(pack['support_index_adjacent_gap_checks'])}"
    )
    print(
        "support_index_unit_gap_checks: "
        f"{len(pack['support_index_unit_gap_checks'])}"
    )
    print(
        "support_index_no_hole_unit_gap_checks: "
        f"{len(pack['support_index_no_hole_unit_gap_checks'])}"
    )
    print(
        "support_index_endpoint_tight_no_hole_checks: "
        f"{len(pack['support_index_endpoint_tight_no_hole_checks'])}"
    )
    print(
        "support_index_base_anchored_strict_lower_bound_checks: "
        f"{len(pack['support_index_base_anchored_strict_lower_bound_checks'])}"
    )
    print(
        "support_index_final_endpoint_capacity_upper_bound_checks: "
        f"{len(pack['support_index_final_endpoint_capacity_upper_bound_checks'])}"
    )
    print(
        "support_index_final_slot_upper_bound_tail_capacity_checks: "
        f"{len(pack['support_index_final_slot_upper_bound_tail_capacity_checks'])}"
    )
    print(
        "support_index_tail_capacity_failure_witness_checks: "
        f"{len(pack['support_index_tail_capacity_failure_witness_checks'])}"
    )
    print(
        "support_index_skipped_slot_hostile_witness_checks: "
        f"{len(pack['support_index_skipped_slot_hostile_witness_checks'])}"
    )
    print(
        "support_index_interval_image_checks: "
        f"{len(pack['support_index_interval_image_checks'])}"
    )
    print(
        "support_index_interval_preimage_selector_checks: "
        f"{len(pack['support_index_interval_preimage_selector_checks'])}"
    )
    print(
        "support_index_least_interval_preimage_selector_checks: "
        f"{len(pack['support_index_least_interval_preimage_selector_checks'])}"
    )
    print(
        "support_index_first_hit_interval_preimage_selector_checks: "
        f"{len(pack['support_index_first_hit_interval_preimage_selector_checks'])}"
    )
    print(
        "support_index_vacuous_first_hit_adapter_checks: "
        f"{len(pack['support_index_vacuous_first_hit_adapter_checks'])}"
    )
    print(
        "finite_support_extraction_checks: "
        f"{len(pack['finite_support_extraction_checks'])}"
    )
    print(
        "finite_image_support_checks: "
        f"{len(pack['finite_image_support_checks'])}"
    )
    print(
        "no_rebilling_freshness_checks: "
        f"{len(pack['no_rebilling_freshness_checks'])}"
    )
    print(
        "same_carrier_packing_checks: "
        f"{len(pack['same_carrier_packing_checks'])}"
    )
    print(
        "metric_covering_selection_checks: "
        f"{len(pack['metric_covering_selection_checks'])}"
    )
    print(f"pi_group_checks: {len(pack['pi_group_checks'])}")
    print(
        "ambiguous_pi_pinning_checks: "
        f"{len(pack['ambiguous_pi_pinning_checks'])}"
    )
    print(
        "dimensionless_exponent_source_checks: "
        f"{len(pack["dimensionless_exponent_source_checks"])}"
    )
    print(
        "persistence_budget_exponent_checks: "
        f"{len(pack['persistence_budget_exponent_checks'])}"
    )
    print(
        "linear_observable_coercivity_checks: "
        f"{len(pack['linear_observable_coercivity_checks'])}"
    )
    print(f"single_spend_audit: {bool(pack['single_spend_audit'])}")
    print(f"receipt_strength_audit: {bool(pack['receipt_strength_audit'])}")
    print(
        "scaled_transfer_numeric_receipt_gate: "
        f"{bool(pack.get('scaled_transfer_numeric_receipt_gate'))}"
    )
    print(
        "owner_geometry_core_receipt_gate: "
        f"{bool(pack.get('owner_geometry_core_receipt_gate'))}"
    )
    print(
        "fresh_annular_anti_laundering_gate: "
        f"{bool(pack.get('fresh_annular_anti_laundering_gate'))}"
    )
    print(
        "fresh_annular_innovation_gate: "
        f"{bool(pack.get('fresh_annular_innovation_gate'))}"
    )
    print(
        "section_fixed_unsigned_variation_gate: "
        f"{bool(pack.get('section_fixed_unsigned_variation_gate'))}"
    )
    print(f"inequality_checks: {len(pack['inequality_checks'])}")
    print(f"curriculum_variants: {len(pack['curriculum_variants'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
