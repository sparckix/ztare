from pathlib import Path
import importlib.util
import json
import shutil
import subprocess
import sys


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "src/ztare/research_director/pde_estimate_workbench.py"
SCRIPT_PATH = SCRIPT.resolve()
AVISC_WITNESS_SCRIPT_PATH = Path(
    "projects/ns_millennium_hunt/scripts/avisc_traceless_tensor_cancellation_witness.py"
).resolve()
PRESSURE_MISMATCH_WITNESS_SCRIPT_PATH = Path(
    "projects/ns_millennium_hunt/scripts/pressure_cutoff_carrier_mismatch_witness.py"
).resolve()
ANGULAR_TOMOGRAPHY_WITNESS_SCRIPT_PATH = Path(
    "projects/ns_millennium_hunt/scripts/angular_pressure_tomography_witness.py"
).resolve()
PRESUMMED_ANGULAR_OWNER_WITNESS_SCRIPT_PATH = Path(
    "projects/ns_millennium_hunt/scripts/presummed_angular_owner_budget_witness.py"
).resolve()
TRACEFREE_DINI_WITNESS_SCRIPT_PATH = Path(
    "projects/ns_millennium_hunt/scripts/tracefree_dini_square_linear_witness.py"
).resolve()
CONE_OVERFLOW_WITNESS_SCRIPT_PATH = Path(
    "projects/ns_millennium_hunt/scripts/cone_overflow_total_variation_witness.py"
).resolve()
RIESZ_PROJECTION_L1_WITNESS_SCRIPT_PATH = Path(
    "projects/ns_millennium_hunt/scripts/riesz_projection_l1_failure_witness.py"
).resolve()


def _load_module():
    spec = importlib.util.spec_from_file_location("pde_estimate_workbench", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_avisc_witness_module():
    spec = importlib.util.spec_from_file_location(
        "avisc_traceless_tensor_cancellation_witness",
        AVISC_WITNESS_SCRIPT_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_pressure_mismatch_witness_module():
    spec = importlib.util.spec_from_file_location(
        "pressure_cutoff_carrier_mismatch_witness",
        PRESSURE_MISMATCH_WITNESS_SCRIPT_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_angular_tomography_witness_module():
    spec = importlib.util.spec_from_file_location(
        "angular_pressure_tomography_witness",
        ANGULAR_TOMOGRAPHY_WITNESS_SCRIPT_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_presummed_angular_owner_witness_module():
    spec = importlib.util.spec_from_file_location(
        "presummed_angular_owner_budget_witness",
        PRESUMMED_ANGULAR_OWNER_WITNESS_SCRIPT_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_tracefree_dini_witness_module():
    spec = importlib.util.spec_from_file_location(
        "tracefree_dini_square_linear_witness",
        TRACEFREE_DINI_WITNESS_SCRIPT_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_cone_overflow_witness_module():
    spec = importlib.util.spec_from_file_location(
        "cone_overflow_total_variation_witness",
        CONE_OVERFLOW_WITNESS_SCRIPT_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_riesz_projection_l1_witness_module():
    spec = importlib.util.spec_from_file_location(
        "riesz_projection_l1_failure_witness",
        RIESZ_PROJECTION_L1_WITNESS_SCRIPT_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tail_language_routes_to_distribution_tail_upgrade() -> None:
    module = _load_module()
    ops = module.suggest_pde_craft_ops(
        gap_type="UNKNOWN",
        target="GenericEstimateCarrier",
        field=None,
        inequalities=[
            "signed average control implies weak Lq tail for positive part",
        ],
    )
    ids = {op["op_id"] for op in ops}
    assert "pec_h" in ids


def test_workbench_estimate_skeletons_surface_coarea_and_cutoff_routes() -> None:
    module = _load_module()
    skeletons = module.generate_pde_estimate_skeletons(
        target="AngularCoareaCollarSelectionSource",
        field="coareaCharge_le_totalInvoice",
        gap_type="AUXILIARY",
        context={"doc": "coarea collar cutoff boundary"},
        inequalities=[],
    )

    ids = {item["id"] for item in skeletons}
    assert "coarea_threshold_charge" in ids
    assert "cutoff_commutator_invoice" in ids


def test_execution_contract_is_ns_plug_over_generic_shapes() -> None:
    module = _load_module()
    contract = module.build_pde_execution_contract(
        [{"op_id": "pec_h", "name": "Distribution / Tail Upgrade"}],
        min_work_units=3,
        hostile_suite="ns_default",
        target_currency="radius_sum",
    )

    assert contract["mode"] == "pde-execution"
    assert "pec_h" in contract["gp219_execution_templates"]["pde_execution_hints"]
    packet_ids = {
        packet["id"]
        for packet in contract["hostile_packet_suite"]["packets"]
    }
    assert "sparse_cubic_ghost" in packet_ids
    assert (
        contract["no_early_stop_rule"]["receipt_strength_linter"]
        == "src/ztare/research_director/receipt_strength_audit.py"
    )
    assert contract["theorem_applicability_db"]["profile"] == "ns_millennium_hunt"
    assert "KRZ_one_component" in contract["theorem_applicability_db"]["theorems"]
    assert (
        "avisc_same_source_pushforward_bound"
        in contract["theorem_applicability_db"]["theorems"]
    )
    assert (
        "avisc_marked_source_variance"
        in contract["theorem_applicability_db"]["theorems"]
    )
    assert (
        "pressure_cutoff_carrier_identity_for_avisc"
        in contract["theorem_applicability_db"]["theorems"]
    )
    assert (
        "pressure_cutoff_fresh_annular_invoice_morphology"
        in contract["theorem_applicability_db"]["theorems"]
    )
    assert (
        "local_model_to_global_cutoff_invoice"
        in contract["currency_ledger_template"]["exchange_rate_obligations"]
    )
    assert "finite_energy_cutoff_invoice" in contract["currency_ledger_template"]["produced_currency"]
    assert (
        "selected_c7_longitudinal_pressure_visible_subclass"
        in contract["theorem_applicability_db"]["theorems"]
    )
    assert (
        "angular_pressure_tomography_selected_packet_morphology"
        in contract["theorem_applicability_db"]["theorems"]
    )
    assert (
        "selected_c7_angular_frame_no_sheath_cancellation"
        in contract["theorem_applicability_db"]["theorems"]
    )
    assert (
        "selected_c7_fixed_window_cone_mass_rigidity_source"
        in contract["theorem_applicability_db"]["theorems"]
    )
    assert (
        "selected_c7_oriented_cone_asymmetry_gate"
        in contract["theorem_applicability_db"]["theorems"]
    )
    assert (
        "pre_summed_angular_packet_owner_carrier"
        in contract["theorem_applicability_db"]["theorems"]
    )
    assert (
        "angular_sample_owner_preimage_exchange"
        in contract["theorem_applicability_db"]["theorems"]
    )
    assert (
        "tracefree_variation_owner_section_interpretation"
        in contract["theorem_applicability_db"]["theorems"]
    )
    assert (
        "balanced_core_sheath_total_cone_gate"
        in contract["theorem_applicability_db"]["theorems"]
    )
    assert (
        "balanced_core_sheath_dynamic_transversality_gate"
        in contract["theorem_applicability_db"]["theorems"]
    )


def test_avisc_pushforward_theorem_accepts_source_bound_not_morphology() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "avisc_same_source_pushforward_bound",
        {
            "localized_Avisc_surplus": True,
            "strict_local_subcritical_exponents": True,
            "strict_tail_exponent": True,
            "exact_invoice_fiber_source_binding": True,
            "observable_carrier_is_separated_source": True,
            "no_proxy_carrier_substitution": True,
            "pressure_transport_reserves_single_spent": True,
            "same_separated_source": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["C7AViscSameSourcePushforwardBoundReceipt"] is True
    assert "total_fresh_annular_carrier_morphology_proof" not in match["requires"]


def test_avisc_pushforward_theorem_rejects_same_source_label_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "avisc_same_source_pushforward_bound",
        {
            "localized_Avisc_surplus": True,
            "strict_local_subcritical_exponents": True,
            "strict_tail_exponent": True,
            "same_source_label_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "same_source_label_only" in match["rejected_substitutes"]


def test_avisc_marked_source_variance_requires_pre_scalar_marked_law() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "avisc_marked_source_variance",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["C7AViscMarkedSourceVarianceReceipt"] is True
    assert match["concludes"]["C7AViscTensorMomentSameSourceMorphologyReceipt"] is True


def test_avisc_marked_source_variance_rejects_scalar_pushforward_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "avisc_marked_source_variance",
        {
            "C7AViscSameSourcePushforwardBoundReceipt": True,
            "positive_part_pushforward_only": True,
            "scalar_masses_only": True,
            "same_separated_source": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "positive_part_pushforward_only" in match["rejected_substitutes"]
    assert "scalar_masses_only" in match["rejected_substitutes"]


def test_avisc_marked_source_variance_rejects_scalar_marked_variance_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "avisc_marked_source_variance",
        {
            "C7AViscSameSourcePushforwardBoundReceipt": True,
            "marked_source_law_on_invoice_fiber": True,
            "variance_lower_bound_before_scalarization": True,
            "scalar_pushforward_noninjectivity_excluded": True,
            "scalar_marked_variance_only": True,
            "same_separated_source": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "scalar_marked_variance_only" in match["rejected_substitutes"]
    assert "traceless_tensor_non_cancellation" in match["missing_fields"]


def test_pressure_cutoff_carrier_identity_rejects_angular_moment_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "pressure_cutoff_carrier_identity_for_avisc",
        {
            "pressure_angular_moment_available": True,
            "pressure_angular_moment_available_only": True,
            "same_window_core_sheath_cancellation": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "pressure_angular_moment_available_only" in match["rejected_substitutes"]
    assert "same_window_core_sheath_cancellation" in match["rejected_substitutes"]
    assert "pressure_carrier_equals_Avisc_invoice_fiber" in match["missing_fields"]


def test_pressure_cutoff_carrier_identity_matches_only_typed_identity_rows() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "pressure_cutoff_carrier_identity_for_avisc",
        {
            "pressure_angular_moment_available": True,
            "pressure_carrier_equals_Avisc_invoice_fiber": True,
            "cutoff_matches_Avisc_invoice_fiber": True,
            "eigenframe_selection_acts_before_payoff": True,
            "eigenframe_selection_forces_Avisc_tensor_non_cancellation": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert (
        match["concludes"]["PressureCutoffCarrierIdentityForAViscInvoiceFiber"]
        is True
    )


def test_pressure_cutoff_fresh_annular_morphology_rejects_avisc_only_identity() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "pressure_cutoff_fresh_annular_invoice_morphology",
        {
            "pressure_angular_moment_available": True,
            "pressure_carrier_equals_Avisc_invoice_fiber_only": True,
            "localized_Avisc_surplus": True,
            "isotropic_orientation_mixture": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert (
        "pressure_carrier_equals_Avisc_invoice_fiber_only"
        in match["rejected_substitutes"]
    )
    assert "isotropic_orientation_mixture" in match["rejected_substitutes"]
    assert (
        "pressure_carrier_equals_fresh_annular_invoice_fiber"
        in match["missing_fields"]
    )


def test_selected_c7_longitudinal_subclass_rejects_leray_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "selected_c7_longitudinal_pressure_visible_subclass",
        {
            "owner_preimage_owns_pre_pressure_tensor_packets": True,
            "selected_packets_fixed_before_pressure_projection": True,
            "divergence_free_Leray_constraint_only": True,
            "tangential_pressure_null_plane_wave_admissible": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "divergence_free_Leray_constraint_only" in match["rejected_substitutes"]
    assert (
        "tangential_pressure_null_plane_wave_admissible"
        in match["rejected_substitutes"]
    )
    assert (
        "selected_C7_owned_packets_are_pressure_visible_longitudinal_subclass"
        in match["missing_fields"]
    )


def test_selected_c7_longitudinal_subclass_matches_cf_free_coercive_packet_class() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "selected_c7_longitudinal_pressure_visible_subclass",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert (
        match["concludes"]["SelectedC7LongitudinalPressureVisibleSubclassReceipt"]
        is True
    )
    assert (
        match["concludes"]["OwnedPrePressureProjectionFreshAnnularMorphologyReceipt"]
        is True
    )


def test_angular_pressure_tomography_rejects_l2_label_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "angular_pressure_tomography_selected_packet_morphology",
        {
            "selected_packets_owned_before_angular_projection": True,
            "pressure_l2_carrier_label_only": True,
            "same_window_sheath_cancellation_admissible": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "pressure_l2_carrier_label_only" in match["rejected_substitutes"]
    assert (
        "same_window_sheath_cancellation_admissible"
        in match["rejected_substitutes"]
    )
    assert "angular_frame_fixed_before_payoff" in match["missing_fields"]


def test_angular_pressure_tomography_rejects_pointwise_frame_without_owner_prefix() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "angular_pressure_tomography_selected_packet_morphology",
        {
            "selected_packets_owned_before_angular_projection": True,
            "angular_frame_fixed_before_payoff": True,
            "angular_frame_spans_trace_free_tensor_morphology": True,
            "stable_tomographic_inversion_constant": True,
            "pointwise_tomography_without_cofinal_owner_prefix_budget": True,
            "five_frame_owner_fiber_prefix_overflow": True,
            "owner_preimage_receipt_missing": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert (
        "pointwise_tomography_without_cofinal_owner_prefix_budget"
        in match["rejected_substitutes"]
    )
    assert "five_frame_owner_fiber_prefix_overflow" in match["rejected_substitutes"]
    assert "owner_preimage_receipt_missing" in match["rejected_substitutes"]


def test_angular_pressure_tomography_matches_same_source_stable_frame() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "angular_pressure_tomography_selected_packet_morphology",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert (
        match["concludes"]["AngularPressureTomographySelectedPacketReceipt"]
        is True
    )
    assert (
        match["concludes"]["OwnedPrePressureProjectionFreshAnnularMorphologyReceipt"]
        is True
    )


def test_selected_c7_angular_no_sheath_rejects_ownership_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "selected_c7_angular_frame_no_sheath_cancellation",
        {
            "selected_C7_frame_fixed_before_payoff": True,
            "C7_owner_geometry_only": True,
            "fresh_annular_anti_laundering_only": True,
            "same_window_sheath_cancellation_admissible": True,
            "scalar_projected_moment_total_variation_cancellation": True,
            "signed_projected_moment_used_as_total_variation": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "C7_owner_geometry_only" in match["rejected_substitutes"]
    assert "fresh_annular_anti_laundering_only" in match["rejected_substitutes"]
    assert (
        "same_window_sheath_cancellation_admissible"
        in match["rejected_substitutes"]
    )
    assert (
        "scalar_projected_moment_total_variation_cancellation"
        in match["rejected_substitutes"]
    )
    assert (
        "signed_projected_moment_used_as_total_variation"
        in match["rejected_substitutes"]
    )
    assert "strict_angular_dominance_on_selected_frame" in match["missing_fields"]


def test_selected_c7_angular_no_sheath_matches_strict_dominance_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "selected_c7_angular_frame_no_sheath_cancellation",
        {
            "pressure_l2_formula_source_fixed": True,
            "selected_C7_frame_fixed_before_payoff": True,
            "selected_C7_source_is_same_formula_source": True,
            "opposite_trace_free_sheath_excluded_before_payoff": True,
            "strict_angular_dominance_on_selected_frame": True,
            "dominance_not_chosen_from_final_carrier_magnitude": True,
            "no_CF_or_other_Clay_equivalent_input_used": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert (
        match["concludes"]["SelectedC7AngularFrameNoSheathCancellationReceipt"]
        is True
    )
    assert match["concludes"]["noSameWindowSheathCancellationOnAngularFrame"] is True


def test_selected_c7_cone_mass_rigidity_rejects_assumed_dominance() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "selected_c7_fixed_window_cone_mass_rigidity_source",
        {
            "pressure_l2_formula_source_fixed": True,
            "selected_C7_frame_fixed_before_payoff": True,
            "strict_angular_dominance_assumed_not_produced": True,
            "same_window_sheath_cancellation_admissible": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert (
        "strict_angular_dominance_assumed_not_produced"
        in match["rejected_substitutes"]
    )
    assert (
        "same_window_sheath_cancellation_admissible"
        in match["rejected_substitutes"]
    )
    assert (
        "overflow_to_same_window_sheath_cancellation_packet"
        in match["missing_fields"]
    )


def test_selected_c7_cone_mass_rigidity_matches_no_escape_source() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "selected_c7_fixed_window_cone_mass_rigidity_source",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["FixedWindowStressConeMassRigiditySource"] is True
    assert (
        match["concludes"]["SelectedC7AngularFrameNoSheathCancellationReceipt"]
        is True
    )


def test_selected_c7_oriented_cone_asymmetry_rejects_sign_blind_packet() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "selected_c7_oriented_cone_asymmetry_gate",
        {
            "pressure_l2_formula_source_fixed": True,
            "selected_C7_frame_fixed_before_payoff": True,
            "selected_C7_source_is_same_formula_source": True,
            "core_positive_cone_mass_measured_before_summation": True,
            "sheath_opposite_cone_mass_measured_before_summation": True,
            "pressure_symbol_membership_only": True,
            "PSD_preimage_available_after_orientation_choice": True,
            "replay_invariant_five_shadow_visibility_only": True,
            "tracefree_orientation_flip_not_distinguished": True,
            "diagonal_sign_blind_core_sheath_equal_mass_packet": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "hypotheses_distinguish_tracefree_orientation_flip" in match["missing_fields"]
    assert "opposite_cone_mass_strictly_below_core_before_payoff" in match["missing_fields"]
    assert "diagonal_sign_blind_core_sheath_equal_mass_packet" in match["rejected_substitutes"]


def test_selected_c7_oriented_cone_asymmetry_matches_presummed_owner_asymmetry() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "selected_c7_oriented_cone_asymmetry_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert (
        match["concludes"]["SelectedC7OppositeTraceFreeSheathInadmissibleBeforePayoff"]
        is True
    )
    assert (
        match["concludes"]["same_window_sheath_cancellation_forbidden_on_selected_C7_class"]
        is True
    )


def test_presummed_angular_packet_owner_carrier_rejects_final_carrier_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "pre_summed_angular_packet_owner_carrier",
        {
            "final_angular_samples_only": True,
            "owner_budget_label_only": True,
            "single_spend_channels_prop_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "final_angular_samples_only" in match["rejected_substitutes"]
    assert "owner_budget_label_only" in match["rejected_substitutes"]
    assert "single_spend_channels_prop_only" in match["rejected_substitutes"]
    assert (
        "packet_owner_pays_presummed_angular_tracefree_morphology"
        in match["missing_fields"]
    )


def test_presummed_angular_packet_owner_carrier_matches_typed_spend_surface() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "pre_summed_angular_packet_owner_carrier",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["PreSummedAngularPacketOwnerCarrierReceipt"] is True
    assert match["concludes"]["sameWindowSheathCancellationDoesNotEraseCarrier"] is True


def test_angular_sample_owner_preimage_exchange_rejects_label_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "angular_sample_owner_preimage_exchange",
        {
            "owner_budget_label_only": True,
            "bounded_multiplicity_label_only": True,
            "event_pay_label_equal_only": True,
            "same_formula_source_syntax_only": True,
            "angular_quotient_proxy_not_invoice_fiber": True,
            "owner_packet_budget_energy_currency_only": True,
            "final_angular_samples_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "owner_budget_label_only" in match["rejected_substitutes"]
    assert "event_pay_label_equal_only" in match["rejected_substitutes"]
    assert "same_formula_source_syntax_only" in match["rejected_substitutes"]
    assert (
        "angular_quotient_proxy_not_invoice_fiber"
        in match["rejected_substitutes"]
    )
    assert (
        "event_pay_is_angular_tracefree_sample_spend"
        in match["missing_fields"]
    )
    assert (
        "pointwise_angular_sample_to_owner_charge_bound"
        in match["missing_fields"]
    )


def test_angular_sample_owner_preimage_exchange_matches_numeric_surface() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "angular_sample_owner_preimage_exchange",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["AngularSampleOwnerPreimageExchangeReceipt"] is True
    assert match["concludes"]["PreSummedAngularPacketOwnerCarrierReceipt"] is True


def test_tracefree_variation_owner_section_rejects_target_defined_budget() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_owner_section_interpretation",
        {
            "owner_packet_label_only": True,
            "owner_packet_budget_defined_as_angularTracefreeSpend": True,
            "prefix_order_rechosen_by_angular_affordability": True,
            "positive_part_budget": True,
            "product_L2_or_global_L4_disguise": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert (
        "owner_packet_budget_defined_as_angularTracefreeSpend"
        in match["rejected_substitutes"]
    )
    assert (
        "owner_is_tracefree_variation_disintegration_section"
        in match["missing_fields"]
    )


def test_tracefree_variation_owner_section_matches_interpretation_surface() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_owner_section_interpretation",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert (
        match["concludes"]["TraceFreeVariationOwnerSectionInterpretation"]
        is True
    )
    assert match["concludes"]["AngularSampleOwnerPreimageExchangeReceipt"] is True


def test_tracefree_variation_cofinal_budget_rejects_single_prefix() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_c7_cofinal_owner_prefix_budget",
        {
            "angular_event_pay_is_tracefree_variation_atom": True,
            "owner_is_tracefree_variation_disintegration_section": True,
            "one_chosen_prefix_only": True,
            "sparse_prefix_overflow_still_admissible": True,
            "product_L2_or_global_L4_disguise": True,
            "pre_summed_pressure_total_variation_only": True,
            "leray_stress_L1_or_energy_budget_only": True,
            "besov_B0_1_1_or_BV_hidden_input": True,
            "same_tree_incidence_ordering_only": True,
            "owner_fibers_bounded_by_invoice_fibers_missing": True,
            "identity_owner_map_only": True,
            "owner_fibers_bounded_but_variation_unsummable": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "one_chosen_prefix_only" in match["rejected_substitutes"]
    assert (
        "sparse_prefix_overflow_still_admissible"
        in match["rejected_substitutes"]
    )
    assert (
        "pre_summed_pressure_total_variation_only"
        in match["rejected_substitutes"]
    )
    assert (
        "leray_stress_L1_or_energy_budget_only"
        in match["rejected_substitutes"]
    )
    assert "besov_B0_1_1_or_BV_hidden_input" in match["rejected_substitutes"]
    assert "same_tree_incidence_ordering_only" in match["rejected_substitutes"]
    assert (
        "owner_fibers_bounded_by_invoice_fibers_missing"
        in match["rejected_substitutes"]
    )
    assert "identity_owner_map_only" in match["rejected_substitutes"]
    assert (
        "owner_fibers_bounded_but_variation_unsummable"
        in match["rejected_substitutes"]
    )
    assert (
        "uniform_C7_prefix_tracefree_variation_budget"
        in match["missing_fields"]
    )


def test_tracefree_variation_cofinal_budget_matches_prefix_family() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_c7_cofinal_owner_prefix_budget",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert (
        match["concludes"]["TraceFreeVariationC7CofinalOwnerPrefixBudget"]
        is True
    )
    assert match["concludes"]["AngularSampleOwnerPreimageExchangeReceipt"] is True


def test_annular_owner_fiber_disintegration_rejects_source_substitutes() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "annular_owner_fiber_tracefree_disintegration",
        {
            "tracefree_variation_c7_cofinal_owner_prefix_budget": True,
            "pre_summed_pressure_total_variation_only": True,
            "leray_stress_L1_or_energy_budget_only": True,
            "same_tree_incidence_ordering_only": True,
            "owner_fibers_bounded_by_invoice_fibers_missing": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert (
        "owner_fibers_bounded_by_invoice_fibers_missing"
        in match["rejected_substitutes"]
    )
    assert "owner_fibers_bounded_by_invoice_fibers" in match["missing_fields"]


def test_annular_owner_fiber_disintegration_matches_exact_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "annular_owner_fiber_tracefree_disintegration",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert (
        match["concludes"]["AnnularOwnerFiberTraceFreeDisintegrationReceipt"]
        is True
    )
    assert (
        match["concludes"]["TraceFreeVariationC7CofinalOwnerPrefixBudget"]
        is True
    )


def test_tracefree_same_carrier_carleson_rejects_label_and_hidden_inputs() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_same_carrier_fresh_no_reuse_carleson",
        {
            "tracefree_variation_c7_cofinal_owner_prefix_budget": True,
            "same_carrier_fresh_no_reuse_label_only": True,
            "numeric_event_to_owner_prefix_inequality_missing": True,
            "besov_B0_1_1_or_BV_hidden_input": True,
            "owner_fibers_bounded_by_invoice_fibers_only": True,
            "owner_fibers_bounded_but_variation_unsummable": True,
            "strict_margin_or_CF_global_extension_import": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert (
        "same_carrier_fresh_no_reuse_label_only"
        in match["rejected_substitutes"]
    )
    assert (
        "numeric_event_to_owner_prefix_inequality_missing"
        in match["rejected_substitutes"]
    )
    assert "besov_B0_1_1_or_BV_hidden_input" in match["rejected_substitutes"]
    assert (
        "owner_fibers_bounded_but_variation_unsummable"
        in match["rejected_substitutes"]
    )
    assert (
        "tracefree_carleson_budget_independent_of_angular_spend"
        in match["missing_fields"]
    )


def test_tracefree_same_carrier_carleson_matches_exact_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_same_carrier_fresh_no_reuse_carleson",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert (
        match["concludes"][
            "TraceFreeVariationSameCarrierFreshNoReuseCarlesonReceipt"
        ]
        is True
    )
    assert (
        match["concludes"]["TraceFreeVariationC7CofinalOwnerPrefixBudget"]
        is True
    )


def test_tracefree_pointwise_same_carrier_payment_rejects_square_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_pointwise_same_carrier_payment",
        {
            "beta_square_carleson_available_only": True,
            "same_tree_beta_carleson_incidence_only": True,
            "dini_square_carleson_but_L1_diverges": True,
            "payment_only_in_square_currency": True,
            "fresh_charge_chosen_from_angular_event_pay": True,
            "pointwise_payment_tautological": True,
            "linear_tracefree_currency_pays_pointwise_only": True,
            "beta_square_currency_pays_finite_budget_only": True,
            "no_independent_fourth_currency": True,
            "same_carrier_identity_owner_only": True,
            "no_descendant_reuse_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert (
        "dini_square_carleson_but_L1_diverges"
        in match["rejected_substitutes"]
    )
    assert "payment_only_in_square_currency" in match["rejected_substitutes"]
    assert (
        "pointwise_tracefree_variation_payment" in match["missing_fields"]
    )
    assert (
        "fresh_charge_chosen_from_angular_event_pay"
        in match["rejected_substitutes"]
    )
    assert "no_independent_fourth_currency" in match["rejected_substitutes"]


def test_tracefree_pointwise_same_carrier_payment_matches_numeric_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_pointwise_same_carrier_payment",
        {
            "pointwise_tracefree_variation_payment": True,
            "finite_prefix_fresh_carrier_budget": True,
            "tracefree_atoms_are_same_carrier_fresh_charge": True,
            "payment_currency_is_tracefree_variation_not_beta_square": True,
            "payment_fixed_before_angular_spend_payoff": True,
            "no_product_L2_or_besov_proxy_in_payment": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert (
        match["concludes"]["TraceFreeVariationPointwiseSameCarrierPaymentReceipt"]
        is True
    )
    assert (
        match["concludes"][
            "TraceFreeVariationSameCarrierFreshNoReuseCarlesonReceipt"
        ]
        is True
    )


def test_tracefree_heat_lag_geometric_payment_rejects_linear_stub() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_heat_lag_geometric_payment",
        {
            "heat_lag_dimensionless_monomial_only": True,
            "heat_lag_bounded_on_selected_parabolic_scale": True,
            "no_prefix_growing_geometric_decay": True,
            "linear_semigroup_geometric_stub_only": True,
            "duhamel_bilinear_remainder_requires_forbidden_currency": True,
            "bilinear_reduces_to_caloric_gevrey_or_paraproduct_or_CF_or_target_reflux": True,
            "linear_stub_does_not_pay_full_nonlinear_receipt": True,
            "heat_lag_chosen_from_angular_prefix_growth": True,
            "selected_C7_finite_overlap_without_amplitude_summability": True,
            "amplitude_summability_missing": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert (
        "duhamel_bilinear_remainder_requires_forbidden_currency"
        in match["rejected_substitutes"]
    )
    assert (
        "heat_lag_bounded_on_selected_parabolic_scale"
        in match["rejected_substitutes"]
    )
    assert "amplitude_summability_missing" in match["rejected_substitutes"]
    assert (
        "heat_lag_grows_across_selected_C7_prefixes" in match["missing_fields"]
    )


def test_tracefree_heat_lag_geometric_payment_matches_full_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_heat_lag_geometric_payment",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert (
        match["concludes"]["TraceFreeVariationHeatLagGeometricPaymentReceipt"]
        is True
    )
    assert (
        match["concludes"]["TraceFreeVariationPointwiseSameCarrierPaymentReceipt"]
        is True
    )


def test_tracefree_hardy_tent_atomic_payment_rejects_signed_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_hardy_tent_atomic_payment",
        {
            "finite_signed_hardy_tent_norm_available_only": True,
            "selected_packet_unconditional_L1_embedding_missing": True,
            "atomic_decomposition_not_tied_to_preselected_C7_packets": True,
            "endpoint_paraproduct_besov_or_target_defined_budget_required": True,
            "atoms_chosen_from_selected_coefficient_overflow": True,
            "signed_commutator_cancellation_available_only": True,
            "absolute_tracefree_variation_payment_missing": True,
            "square_or_signed_currency_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert (
        "selected_packet_unconditional_L1_embedding_missing"
        in match["rejected_substitutes"]
    )
    assert (
        "endpoint_paraproduct_besov_or_target_defined_budget_required"
        in match["rejected_substitutes"]
    )
    assert "tracefree_variation_pointwise_same_carrier_payment" in match[
        "missing_fields"
    ]


def test_tracefree_hardy_tent_atomic_payment_matches_full_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_hardy_tent_atomic_payment",
        {
            "tracefree_variation_pointwise_same_carrier_payment": True,
            "selected_C7_packets_form_pre_payoff_unconditional_atoms": True,
            "atomic_coefficient_L1_pays_tracefree_variation": True,
            "duhamel_remainder_preserves_atomic_currency": True,
            "not_target_defined_atomic_decomposition": True,
            "no_besov_paraproduct_or_CF_import": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert (
        match["concludes"]["TraceFreeVariationHardyTentAtomicPaymentReceipt"]
        is True
    )
    assert (
        match["concludes"]["TraceFreeVariationPointwiseSameCarrierPaymentReceipt"]
        is True
    )


def test_tracefree_cone_leakage_payment_rejects_overflow_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_cone_leakage_pointwise_payment",
        {
            "pressureRieszConeCharge_pays_overflowExcess": True,
            "selected_c7_fixed_window_cone_mass_rigidity_source": True,
            "fixed_window_overflow_visible_or_invisible_profile_only": True,
            "no_sameWindowSheathCancellation": True,
            "CF_or_direction_coherence": True,
            "total_cone_tracefree_variation_payment_missing": True,
            "pressure_riesz_degree_zero_carrier_only": True,
            "same_stream_fresh_cone_budget_missing": True,
            "homogeneity_zero_obstruction_still_admissible": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert (
        "pressureRieszConeCharge_pays_overflowExcess"
        in match["rejected_substitutes"]
    )
    assert (
        "total_cone_tracefree_variation_payment_missing"
        in match["rejected_substitutes"]
    )
    assert "tracefree_variation_pointwise_same_carrier_payment" in match[
        "missing_fields"
    ]


def test_tracefree_cone_leakage_payment_matches_full_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_cone_leakage_pointwise_payment",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert (
        match["concludes"][
            "TraceFreeVariationConeLeakagePointwisePaymentReceipt"
        ]
        is True
    )
    assert (
        match["concludes"]["TraceFreeVariationPointwiseSameCarrierPaymentReceipt"]
        is True
    )


def test_fixed_window_total_cone_variation_source_rejects_overflow_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "fixed_window_total_cone_variation_charge_source",
        {
            "pressureRieszConeCharge_pays_overflowExcess": True,
            "overflow_excess_only": True,
            "visible_overflow_charge_only": True,
            "fixed_window_overflow_visible_or_invisible_profile_only": True,
            "total_cone_tracefree_variation_payment_missing": True,
            "core_plus_sheath_not_paid": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "overflow_excess_only" in match["rejected_substitutes"]
    assert "core_plus_sheath_not_paid" in match["rejected_substitutes"]
    assert "total_cone_variation_is_core_plus_sheath" in match["missing_fields"]


def test_fixed_window_total_cone_variation_source_rejects_balanced_dini_ladder() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "fixed_window_total_cone_variation_charge_source",
        {
            "balanced_core_sheath_dini_ladder_admissible": True,
            "overflow_summable_total_cone_dini_divergent": True,
            "pressureRieszConeCharge_pays_overflowExcess": True,
            "shardC_charges_use_same_selected_C7_stream": True,
            "no_final_carrier_magnitude_input": True,
            "no_sheath_cancellation_or_CF_import": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "balanced_core_sheath_dini_ladder_admissible" in match["rejected_substitutes"]
    assert "overflow_summable_total_cone_dini_divergent" in match["rejected_substitutes"]
    assert (
        "total_cone_variation_le_pressure_riesz_cone_charge_plus_shardC_charges"
        in match["missing_fields"]
    )


def test_fixed_window_total_cone_variation_source_matches_full_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "fixed_window_total_cone_variation_charge_source",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["FixedWindowTotalConeVariationChargeSource"] is True
    assert (
        match["concludes"][
            "TraceFreeVariationConeLeakagePointwisePaymentReceipt"
        ]
        is True
    )


def test_balanced_core_sheath_total_cone_gate_rejects_overflow_only_ladder() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "balanced_core_sheath_total_cone_gate",
        {
            "core_stream_fixed_before_payoff": True,
            "sheath_stream_fixed_before_payoff": True,
            "overflow_stream_identified": True,
            "same_selected_prefix_map": True,
            "owner_map_fixed_before_payoff": True,
            "overflow_excess_only": True,
            "sum_overflow_finite_only": True,
            "sum_core_plus_sheath_diverges": True,
            "balanced_core_sheath_dini_ladder_admissible": True,
            "owner_preimage_prefix_inequality_missing": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "owner_charge_pays_core_plus_sheath" in match["missing_fields"]
    assert "owner_preimage_prefix_inequality" in match["missing_fields"]
    assert "balanced_core_sheath_dini_ladder_admissible" in match["rejected_substitutes"]
    assert "owner_preimage_prefix_inequality_missing" in match["rejected_substitutes"]


def test_balanced_core_sheath_total_cone_gate_matches_owner_preimage_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "balanced_core_sheath_total_cone_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["TotalConeSelectedPrefixOwnerPreimageReceipt"] is True
    assert match["concludes"]["FixedWindowTotalConeVariationChargeSource"] is True


def test_balanced_core_sheath_dynamic_transversality_rejects_sample_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "balanced_core_sheath_dynamic_transversality_gate",
        {
            "balanced_core_sheath_dini_ladder_packet": True,
            "packet_encodes_near_stealth_balanced_cone": True,
            "single_sample_phase5at_only": True,
            "directional_derivative_audit_only": True,
            "dwell_time_not_bound_to_selected_prefix": True,
            "higher_jet_retuning_still_admissible": True,
            "higher_jet_tangency_reset_confuser": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "ns_vector_field_transverse_to_stealth_manifold" in match["missing_fields"]
    assert "exposure_time_less_than_selected_reset_dwell" in match["missing_fields"]
    assert "higher_jet_retuning_still_admissible" in match["rejected_substitutes"]
    assert "higher_jet_tangency_reset_confuser" in match["rejected_substitutes"]
    assert (
        "uniform_same_owner_full_jet_transversality_modulo_ns_constraints"
        in match["missing_fields"]
    )


def test_balanced_core_sheath_trace_zero_positive_net_budget_confuser_rejects_wrong_trajectory() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "balanced_core_sheath_trace_zero_positive_net_budget_confuser_gate",
        {
            "balanced_core_sheath_dini_ladder_packet": True,
            "trace_zero_strain": True,
            "stretching_eigenvalue_positive": True,
            "budget_from_different_trajectory": True,
            "eta_positive": True,
            "A_positive": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "same_owner_selected_stream" in match["missing_fields"]
    assert "production_equals_one_plus_eta_times_A" in match["missing_fields"]
    assert "budget_from_different_trajectory" in match["rejected_substitutes"]


def test_balanced_core_sheath_trace_zero_positive_net_budget_confuser_matches_local_jet() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "balanced_core_sheath_trace_zero_positive_net_budget_confuser_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["TraceZeroStrainPositiveNetBudgetJet"] is True
    assert match["concludes"]["BalancedCoreSheathSignedBudgetGapConfuser"] is True
    assert match["concludes"]["positive_same_trajectory_net_budget"] is True


def test_local_affine_trace_zero_positive_stretching_confuser_rejects_static_or_finite_energy_claims() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "local_affine_trace_zero_positive_stretching_confuser_gate",
        {
            "stationary_affine_jet": True,
            "trace_zero_strain": True,
            "vorticity_aligned_with_positive_strain_eigenvector": True,
            "local_vorticity_diffusion_zero": True,
            "finite_energy_c7_tent_claim": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "time_dependent_local_affine_jet" in match["missing_fields"]
    assert "skew_time_derivative_pays_affine_equation" in match["missing_fields"]
    assert "finite_energy_cutoff_invoice_unpaid" in match["missing_fields"]
    assert "stationary_affine_jet" in match["rejected_substitutes"]
    assert "finite_energy_c7_tent_claim" in match["rejected_substitutes"]


def test_local_affine_trace_zero_positive_stretching_confuser_matches_time_dependent_local_jet() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "local_affine_trace_zero_positive_stretching_confuser_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["LocalAffineTraceZeroPositiveStretchingJet"] is True
    assert match["concludes"]["TraceZeroStrainPositiveNetBudgetJet"] is True
    assert match["concludes"]["purely_local_dynamic_inadmissibility_killed"] is True


def test_localized_c7_tent_cutoff_invoice_dominance_rejects_local_or_ratio_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "localized_c7_tent_cutoff_invoice_dominates_positive_stretching_gate",
        {
            "time_dependent_local_affine_jet": True,
            "local_affine_trace_zero_positive_stretching_only": True,
            "dimensionless_ratio_only": True,
            "positive_net_budget_leak_packet": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "same_owner_selected_c7_tent" in match["missing_fields"]
    assert "finite_energy_cutoff_constructed_before_payoff" in match["missing_fields"]
    assert "invoice_sum_dominates_surplus" in match["missing_fields"]
    assert "local_affine_trace_zero_positive_stretching_only" in match["rejected_substitutes"]
    assert "dimensionless_ratio_only" in match["rejected_substitutes"]
    assert "positive_net_budget_leak_packet" in match["rejected_substitutes"]


def test_localized_c7_tent_cutoff_invoice_dominance_matches_paid_nonlocal_invoice() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "localized_c7_tent_cutoff_invoice_dominates_positive_stretching_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["LocalizedC7TentCutoffInvoiceDominatesPositiveStretching"] is True
    assert match["concludes"]["finite_energy_cutoff_invoice_paid"] is True
    assert match["concludes"]["purely_local_affine_confuser_not_enough"] is True


def test_localized_c7_scaling_leak_certificate_matches_only_strict_fraction_breaker() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "localized_c7_tent_scaling_leak_certificate_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["LocalizedC7TentScalingLeakCertificate"] is True
    assert match["concludes"]["LocalizedC7TentCutoffInvoiceLeakPacket"] is True


def test_localized_c7_scaling_leak_certificate_rejects_ratio_or_dominance() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "localized_c7_tent_scaling_leak_certificate_gate",
        {
            "time_dependent_local_affine_jet": True,
            "same_owner_selected_c7_tent": True,
            "dimensionless_ratio_only": True,
            "invoice_sum_dominates_surplus": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "finite_energy_high_pi_regime" in match["missing_fields"]
    assert "dimensionless_ratio_only" in match["rejected_substitutes"]
    assert "invoice_sum_dominates_surplus" in match["rejected_substitutes"]


def test_parabolic_cutoff_invoice_underpaid_leak_model_matches_strict_fraction_case() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "parabolic_cutoff_invoice_underpaid_leak_model_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["ParabolicCutoffInvoiceUnderpaidLeakModel"] is True
    assert match["concludes"]["LocalizedC7TentScalingLeakCertificate"] is True


def test_parabolic_cutoff_invoice_underpaid_leak_model_rejects_positive_payment_substitute() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "parabolic_cutoff_invoice_underpaid_leak_model_gate",
        {
            "time_dependent_local_affine_jet": True,
            "same_owner_selected_c7_tent": True,
            "eta_le_cutoff_constant": True,
            "invoice_sum_dominates_surplus": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "finite_energy_high_pi_regime" in match["missing_fields"]
    assert "eta_le_cutoff_constant" in match["rejected_substitutes"]
    assert "invoice_sum_dominates_surplus" in match["rejected_substitutes"]


def test_parabolic_cutoff_invoice_model_matches_normalized_small_surplus_case() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "parabolic_cutoff_invoice_pays_affine_surplus_model_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["ParabolicCutoffInvoicePaysAffineSurplusModel"] is True
    assert match["concludes"]["ParabolicFiniteEnergyInvoiceLowerBoundForLocalizedAffineTent"] is True


def test_parabolic_cutoff_invoice_model_rejects_missing_normalization() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "parabolic_cutoff_invoice_pays_affine_surplus_model_gate",
        {
            "time_dependent_local_affine_jet": True,
            "same_owner_selected_c7_tent": True,
            "dimensionless_ratio_only": True,
            "cutoff_invoice_paid_by_declaration": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "active_scale_normalization_A_equals_cutoff_unit" in match["missing_fields"]
    assert "dimensionless_ratio_only" in match["rejected_substitutes"]
    assert "cutoff_invoice_paid_by_declaration" in match["rejected_substitutes"]












def test_proxy_section_absolute_interface_variation_packet_matches_section_mismatch() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "proxy_section_absolute_interface_variation_packet_gate",
        {
            "signed_transport_commutator_cancellation_packet": True,
            "absolute_interface_variation_exists": True,
            "absolute_variation_on_proxy_section": True,
            "selected_prefix_absolute_variation_missing": True,
            "section_fixed_before_payoff_for_selected_prefix_missing": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["ProxySectionAbsoluteInterfaceVariationPacket"] is True
    assert match["concludes"]["selected_section_binding_required"] is True


def test_proxy_section_absolute_interface_variation_rejects_same_section_binding() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "proxy_section_absolute_interface_variation_packet_gate",
        {
            "absolute_interface_variation_on_same_selected_owner_prefix": True,
            "section_fixed_before_payoff_for_selected_prefix": True,
            "absolute_variation_exists_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "absolute_variation_on_proxy_section" in match["missing_fields"]
    assert "selected_prefix_absolute_variation_missing" in match["missing_fields"]
    assert "absolute_interface_variation_on_same_selected_owner_prefix" in match["rejected_substitutes"]
    assert "absolute_variation_exists_only" in match["rejected_substitutes"]


def test_section_fixed_absolute_interface_variation_payment_source_matches_positive_target() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "section_fixed_absolute_interface_variation_payment_source_gate",
        {
            "localized_affine_euler_core_high_pi_interface_payment_source": True,
            "absolute_interface_variation_nonnegative": True,
            "absolute_interface_variation_fixed_before_payoff": True,
            "absolute_interface_variation_on_same_selected_owner_prefix": True,
            "reynolds_excess_le_absolute_interface_variation": True,
            "absolute_interface_variation_le_transport_cutoff_commutator_coefficient": True,
            "no_positive_part_chosen_after_payoff": True,
            "no_descendant_rebilling_for_interface_variation": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["SectionFixedAbsoluteInterfaceVariationPaymentSource"] is True
    assert match["concludes"]["ParabolicChannelCoefficientEstimateSource"] is True


def test_section_fixed_absolute_interface_variation_rejects_post_payoff_positive_part() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "section_fixed_absolute_interface_variation_payment_source_gate",
        {
            "signed_final_commutator_payment_only": True,
            "positive_part_chosen_after_payoff": True,
            "absolute_variation_on_proxy_owner": True,
            "descendant_rebilling_for_interface_variation": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "absolute_interface_variation_fixed_before_payoff" in match["missing_fields"]
    assert "absolute_interface_variation_on_same_selected_owner_prefix" in match["missing_fields"]
    assert "positive_part_chosen_after_payoff" in match["rejected_substitutes"]
    assert "absolute_variation_on_proxy_owner" in match["rejected_substitutes"]


def test_post_payoff_section_repair_packet_matches_late_repair_confuser() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "post_payoff_section_repair_packet_gate",
        {
            "proxy_section_absolute_interface_variation_packet": True,
            "proxy_section_repaired_after_payoff": True,
            "selected_section_identity_fixed_before_payoff_missing": True,
            "selected_absolute_variation_lower_bound_missing": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["PostPayoffSectionRepairPacket"] is True
    assert match["concludes"]["pre_payoff_selected_section_identity_required"] is True


def test_post_payoff_section_repair_rejects_prepaid_selected_identity() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "post_payoff_section_repair_packet_gate",
        {
            "selected_section_identity_fixed_before_payoff": True,
            "selected_section_equals_localized_packet_interface_section": True,
            "reynolds_excess_le_selected_absolute_variation": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "proxy_section_repaired_after_payoff" in match["missing_fields"]
    assert "selected_section_identity_fixed_before_payoff_missing" in match["missing_fields"]
    assert "selected_section_identity_fixed_before_payoff" in match["rejected_substitutes"]


def test_selected_section_absolute_interface_variation_identity_source_matches_positive_target() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "selected_section_absolute_interface_variation_identity_source_gate",
        {
            "section_fixed_absolute_interface_variation_payment_source": True,
            "selected_section_identity_fixed_before_payoff": True,
            "selected_section_equals_localized_packet_interface_section": True,
            "proxy_section_excluded_or_mapped_to_selected_prefix": True,
            "selected_absolute_variation_eq_absolute_interface_variation": True,
            "reynolds_excess_le_selected_absolute_variation": True,
            "owner_preimage_pays_selected_absolute_variation": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["SelectedSectionAbsoluteInterfaceVariationIdentitySource"] is True
    assert match["concludes"]["selected_section_binding_paid_before_payoff"] is True


def test_angular_cone_cutoff_boundary_invoice_unpaid_packet_matches_boundary_confuser() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "angular_cone_cutoff_boundary_invoice_unpaid_packet_gate",
        {
            "raw_positive_eigencone_loss_unpaid_packet": True,
            "selected_spatial_support_inside_positive_eigencone": True,
            "angular_cone_cutoff_introduces_boundary_invoice": True,
            "angular_boundary_invoice_paid_missing": True,
            "posthoc_cone_rotation_would_pay_only_after_selection": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["AngularConeCutoffBoundaryInvoiceUnpaidPacket"] is True
    assert match["concludes"]["angular_cutoff_boundary_invoice_required"] is True


def test_angular_cone_cutoff_boundary_invoice_unpaid_rejects_support_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "angular_cone_cutoff_boundary_invoice_unpaid_packet_gate",
        {
            "spatial_cone_support_only": True,
            "angular_cutoff_invoice_ignored": True,
            "posthoc_cone_rotation": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "angular_boundary_invoice_paid_missing" in match["missing_fields"]
    assert "posthoc_cone_rotation_would_pay_only_after_selection" in match["missing_fields"]
    assert "angular_cutoff_invoice_ignored" in match["rejected_substitutes"]


def test_cone_localized_affine_packet_geometry_source_matches_paid_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "cone_localized_affine_packet_geometry_source_gate",
        {
            "localized_affine_eigenframe_section_binding_source": True,
            "selected_spatial_support_is_positive_eigencone_cutoff": True,
            "cone_aperture_fixed_by_eigenframe_before_payoff": True,
            "angular_cutoff_fixed_before_payoff": True,
            "angular_cone_cutoff_boundary_invoice_nonnegative": True,
            "angular_cutoff_boundary_invoice_paid": True,
            "selected_support_cone_receipt_no_posthoc_rotation": True,
            "no_angular_boundary_rebilling": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["ConeLocalizedAffinePacketGeometrySource"] is True
    assert match["concludes"]["spatial_support_cone_receipt_paid"] is True


def test_cone_localized_affine_packet_geometry_source_rejects_boundary_ignored() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "cone_localized_affine_packet_geometry_source_gate",
        {
            "spatial_cone_support_only": True,
            "angular_cutoff_invoice_ignored": True,
            "selected_support_label_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "angular_cutoff_boundary_invoice_paid" in match["missing_fields"]
    assert "no_angular_boundary_rebilling" in match["missing_fields"]
    assert "spatial_cone_support_only" in match["rejected_substitutes"]


def test_angular_cone_cutoff_boundary_invoice_payment_source_matches_same_owner_payment() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "angular_cone_cutoff_boundary_invoice_payment_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["AngularConeCutoffBoundaryInvoicePaymentSource"] is True
    assert match["concludes"]["same_owner_angular_boundary_invoice_paid"] is True


def test_angular_cone_cutoff_boundary_invoice_payment_source_rejects_declaration_payment() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "angular_cone_cutoff_boundary_invoice_payment_source_gate",
        {
            "cone_localized_affine_packet_geometry_source": True,
            "boundary_invoice_paid_by_declaration": True,
            "post_projection_boundary_payment": True,
            "same_owner_label_without_invoice_channel": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "angular_cutoff_boundary_to_same_owner_invoice_exchange" in match["missing_fields"]
    assert "angular_boundary_invoice_billed_to_same_selected_prefix" in match["missing_fields"]
    assert "angular_boundary_invoice_channel_separated" in match["missing_fields"]
    assert "angular_boundary_partition_single_spend" in match["missing_fields"]
    assert "no_reuse_angular_boundary_spend" in match["missing_fields"]
    assert "boundary_invoice_paid_by_declaration" in match["rejected_substitutes"]
    assert "post_projection_boundary_payment" in match["rejected_substitutes"]


def test_thin_angular_collar_boundary_amplification_packet_matches_overspend() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "thin_angular_collar_boundary_amplification_packet_gate",
        {
            "angular_cone_cutoff_boundary_invoice_unpaid_packet": True,
            "selected_spatial_support_inside_positive_eigencone": True,
            "angular_collar_width_positive": True,
            "angular_derivative_scale_inverse_width": True,
            "angular_boundary_invoice_nonnegative": True,
            "total_invoice_lt_angular_boundary_invoice": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["ThinAngularCollarBoundaryAmplificationPacket"] is True
    assert match["concludes"]["angular_boundary_invoice_le_total_invoice_required"] is True


def test_thin_angular_collar_boundary_amplification_rejects_width_label() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "thin_angular_collar_boundary_amplification_packet_gate",
        {
            "dimensionless_collar_label_only": True,
            "angular_width_without_derivative_scale": True,
            "boundary_invoice_paid_by_total_label": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "angular_derivative_scale_inverse_width" in match["missing_fields"]
    assert "total_invoice_lt_angular_boundary_invoice" in match["missing_fields"]
    assert "dimensionless_collar_label_only" in match["rejected_substitutes"]


def test_fixed_profile_angular_collar_charge_source_matches_profile_bound() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "fixed_profile_angular_collar_charge_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["FixedProfileAngularCollarChargeSource"] is True
    assert match["concludes"]["AngularConeCutoffBoundaryInvoicePaymentSource"] is True


def test_fixed_profile_angular_collar_charge_source_rejects_profile_label() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "fixed_profile_angular_collar_charge_source_gate",
        {
            "cone_localized_affine_packet_geometry_source": True,
            "fixed_profile_label_without_norm": True,
            "collar_mass_not_same_prefix": True,
            "collar_mass_reused_as_main_surplus": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "angular_boundary_invoice_eq_profile_constant_times_collar_mass" in match["missing_fields"]
    assert "profile_constant_times_collar_mass_le_total_invoice" in match["missing_fields"]
    assert "same_prefix_angular_collar_mass_charge" in match["missing_fields"]
    assert "angular_collar_production_spend_eq_boundary_invoice" in match["missing_fields"]
    assert "angular_collar_spend_sum_le_boundary_invoice" in match["missing_fields"]
    assert "fixed_profile_label_without_norm" in match["rejected_substitutes"]


def test_angular_coarea_collar_selection_source_matches_pre_payoff_selection() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "angular_coarea_collar_selection_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["AngularCoareaCollarSelectionSource"] is True
    assert match["concludes"]["dimensionless_angular_collar_spike_excluded_by_coarea_selection"] is True


def test_angular_coarea_collar_selection_source_rejects_posthoc_threshold() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "angular_coarea_collar_selection_source_gate",
        {
            "fixed_profile_angular_collar_charge_source": True,
            "posthoc_threshold_rotation": True,
            "coarea_average_label_only": True,
            "threshold_selected_after_payoff": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "threshold_selected_by_pre_payoff_coarea" in match["missing_fields"]
    assert "selected_threshold_preserves_eigencone_lower_bound" in match["missing_fields"]
    assert "coarea_charge_le_total_invoice" in match["missing_fields"]
    assert "posthoc_threshold_rotation" in match["rejected_substitutes"]


def test_owner_preimage_coarea_collar_charge_source_matches_owner_prefix() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "owner_preimage_coarea_collar_charge_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["OwnerPreimageCoareaCollarChargeSource"] is True
    assert match["concludes"]["coarea_charge_le_total_invoice_from_owner_prefix"] is True


def test_owner_preimage_coarea_collar_charge_source_rejects_owner_label() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "owner_preimage_coarea_collar_charge_source_gate",
        {
            "angular_coarea_collar_selection_source": True,
            "owner_label_without_preimage_budget": True,
            "prefix_budget_without_selected_threshold_membership": True,
            "coarea_charge_local_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "threshold_owner_map_fixed_before_payoff" in match["missing_fields"]
    assert "selected_threshold_charge_le_owner_root_budget" in match["missing_fields"]
    assert "owner_root_budget_le_total_invoice" in match["missing_fields"]
    assert "owner_label_without_preimage_budget" in match["rejected_substitutes"]
    assert "prefix_budget_without_selected_threshold_membership" in match["rejected_substitutes"]


def test_preprojection_projected_collar_exchange_source_matches_tail_paid() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "preprojection_projected_collar_exchange_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["PreprojectionProjectedCollarExchangeSource"] is True
    assert match["concludes"]["projected_payment_le_two_total_invoice"] is True


def test_preprojection_projected_collar_exchange_source_rejects_projection_label() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "preprojection_projected_collar_exchange_source_gate",
        {
            "owner_preimage_coarea_collar_charge_source": True,
            "preprojection_payment_spent_as_projected_target": True,
            "same_source_window_label_without_tail_invoice": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "projection_tail_reserve_nonnegative" in match["missing_fields"]
    assert "projected_payment_le_preprojection_plus_tail" in match["missing_fields"]
    assert "preprojection_payment_spent_as_projected_target" in match["rejected_substitutes"]


def test_projection_tail_reserve_unpaid_packet_matches_tail_gap() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "projection_tail_reserve_unpaid_packet_gate",
        {
            "owner_preimage_coarea_collar_charge_source": True,
            "projected_angular_boundary_payment_nonnegative": True,
            "preprojection_collar_paid": True,
            "projection_tail_reserve_missing": True,
            "projected_payment_exceeds_preprojection_collar_charge": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["ProjectionTailReserveUnpaidPacket"] is True
    assert match["concludes"]["projection_tail_reserve_required"] is True


def test_shared_partition_projected_collar_invoice_source_matches_single_budget() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "shared_partition_projected_collar_invoice_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["SharedPartitionProjectedCollarInvoiceSource"] is True
    assert match["concludes"]["factor_two_projection_loss_removed"] is True


def test_two_invoice_projection_loss_packet_matches_factor_two_gap() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "two_invoice_projection_loss_packet_gate",
        {
            "preprojection_projected_collar_exchange_source": True,
            "collar_and_tail_each_use_separate_total_invoice": True,
            "shared_partition_missing": True,
            "total_invoice_lt_projected_payment": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["TwoInvoiceProjectionLossPacket"] is True
    assert match["concludes"]["shared_partition_required"] is True


def test_joint_owner_root_collar_tail_partition_source_requires_owner_root_channel() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "joint_owner_root_collar_tail_partition_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["JointOwnerRootCollarTailPartitionSource"] is True
    assert match["concludes"]["projected_payment_le_owner_root_budget"] is True
    assert match["concludes"]["tail_plus_existing_reserves_le_owner_root_budget"] is True


def test_collar_tail_overlap_rebilling_packet_blocks_joint_owner_root_channel() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "collar_tail_overlap_rebilling_packet_gate",
        {
            "preprojection_projected_collar_exchange_source": True,
            "collar_tail_overlap_same_cutoff_reserve": True,
            "projection_tail_overlaps_existing_collar_reserve": True,
            "joint_owner_root_channel_missing": True,
            "owner_root_budget_lt_projected_payment": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["CollarTailOverlapRebillingPacket"] is True
    assert match["concludes"]["joint_owner_root_channel_required"] is True


def test_finite_projected_window_no_overlap_assignment_source_matches_limit_route() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "finite_projected_window_no_overlap_assignment_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["FiniteProjectedWindowNoOverlapAssignmentSource"] is True
    assert match["concludes"]["projection_tail_plus_existing_reserve_no_overlap_bound_from_assignment"] is True


def test_projection_window_no_overlap_persistence_failure_packet_matches_limit_confuser() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "projection_window_no_overlap_persistence_failure_packet_gate",
        {
            "joint_owner_root_collar_tail_partition_source": True,
            "finite_assignment_before_projection": True,
            "no_overlap_holds_before_projection": True,
            "no_overlap_persistence_lemma_missing": True,
            "projected_window_reintroduces_overlap": True,
            "owner_root_budget_lt_tail_plus_existing_reserve": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["ProjectionWindowNoOverlapPersistenceFailurePacket"] is True
    assert match["concludes"]["projection_window_persistence_lemma_required"] is True


def test_paid_overlap_projected_window_assignment_source_matches_repair_route() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "paid_overlap_projected_window_assignment_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["PaidOverlapProjectedWindowAssignmentSource"] is True
    assert match["concludes"]["projected_payment_le_owner_root_budget"] is True


def test_finite_projected_window_paid_nonzero_overlap_reserve_source_matches_repair_route() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "finite_projected_window_paid_nonzero_overlap_reserve_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["FiniteProjectedWindowPaidNonzeroOverlapReserveSource"] is True
    assert match["concludes"]["tail_plus_existing_reserves_le_owner_root_budget"] is True


def test_four_way_owner_root_subpartition_source_matches_no_rebilling_route() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "four_way_owner_root_subpartition_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["FourWayOwnerRootSubpartitionSource"] is True
    assert match["concludes"]["joint_paid_overlap_main_surplus_le_owner_root_budget_from_subpartition"] is True
    assert match["concludes"]["tail_plus_existing_reserves_le_owner_root_budget"] is True
    assert match["concludes"]["projected_payment_le_owner_root_budget"] is True
    assert match["concludes"]["PrePayoffOverlapPreimageSource"] is True
    assert match["concludes"]["paid_overlap_reserve_le_owner_root_budget_via_preimage"] is True


def test_four_way_owner_root_rebilling_packet_blocks_subpartition_source() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "four_way_owner_root_rebilling_packet_gate",
        {
            "preprojection_projected_collar_exchange_source": True,
            "overlap_reserve_reuses_collar_tail_or_main_spend": True,
            "four_way_subpartition_missing": True,
            "owner_root_budget_lt_joint_paid_overlap_main_surplus": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["FourWayOwnerRootRebillingPacket"] is True
    assert match["concludes"]["four_way_owner_root_subpartition_required"] is True



def test_pre_payoff_overlap_preimage_source_matches_owner_geometry_route() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "pre_payoff_overlap_preimage_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["PrePayoffOverlapPreimageSource"] is True
    assert match["concludes"]["paid_overlap_reserve_le_owner_root_budget"] is True


def test_selected_interface_variation_coarea_overlap_lower_payment_source_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "selected_interface_variation_coarea_overlap_lower_payment_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["SelectedInterfaceVariationCoareaOverlapLowerPaymentSource"] is True
    assert match["concludes"]["CoareaCollarLowerPaymentToPositiveTVSource"] is True


def test_markov_paley_zygmund_size_sum_coarea_source_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "markov_paley_zygmund_size_sum_coarea_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["MarkovPaleyZygmundSizeSumCoareaSource"] is True
    assert match["concludes"]["lower_bounds_force_threshold_size_sum_surplus"] is True


def test_high_interface_second_moment_known_basin_boundary_blocks_borrowed_label() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "high_interface_second_moment_known_basin_boundary_gate",
        {
            "paley_zygmund_high_interface_debt_packet": True,
            "borrowed_selected_tent_anti_concentration_label": True,
            "same_threshold_family_second_moment_missing": True,
            "strict_tail_or_sparse_high_high_basin_recurrence": True,
            "not_a_new_coarea_interface_second_moment_receipt": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["HighInterfaceSecondMomentKnownBasinBoundary"] is True
    assert match["concludes"]["same_threshold_second_moment_required_not_old_basin_label"] is True


def test_fixed_profile_threshold_interface_amplitude_cap_source_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "fixed_profile_threshold_interface_amplitude_cap_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["FixedProfileThresholdInterfaceAmplitudeCapSource"] is True
    assert match["concludes"]["same_threshold_amplitude_cap_source_paid"] is True


def test_fixed_profile_threshold_interface_amplitude_cap_source_rejects_label_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "fixed_profile_threshold_interface_amplitude_cap_source_gate",
        {
            "fixed_profile_label_without_pointwise_bound": True,
            "amplitude_cap_on_proxy_threshold_family": True,
            "interface_first_moment_without_prefix_payment": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "threshold_interface_payment_le_cap_mul_support_weight" in match["missing_fields"]
    assert "high_interface_set_measure_eq_prefix_support_weight" in match["missing_fields"]
    assert "fixed_profile_label_without_pointwise_bound" in match["rejected_substitutes"]


def test_same_prefix_interface_second_moment_cap_size_sum_source_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "same_prefix_interface_second_moment_cap_size_sum_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["SamePrefixInterfaceSecondMomentCapSizeSumSource"] is True
    assert match["concludes"]["same_threshold_anti_spike_receipt_from_second_moment_cap"] is True


def test_same_prefix_interface_second_moment_cap_rejects_proxy_energy() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "same_prefix_interface_second_moment_cap_size_sum_source_gate",
        {
            "global_l2_energy_as_same_prefix_second_moment": True,
            "proxy_carrier_second_moment_cap": True,
            "post_payoff_second_moment_cap_choice": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "same_prefix_second_moment_cap_on_coarea_interface_threshold_family" in match["missing_fields"]
    assert "first_moment_sq_le_second_moment_cap_mul_high_interface_set_measure" in match["missing_fields"]
    assert "global_l2_energy_as_same_prefix_second_moment" in match["rejected_substitutes"]


def test_proxy_second_moment_cap_not_same_prefix_packet_blocks_source() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "proxy_second_moment_cap_not_same_prefix_packet_gate",
        {
            "second_moment_cap_available_on_proxy_carrier": True,
            "same_prefix_identity_between_proxy_and_threshold_family_missing": True,
            "prefix_support_measure_identity_missing": True,
            "post_projection_or_global_energy_billed_as_local_cap": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["ProxySecondMomentCapNotSamePrefixPacket"] is True
    assert match["concludes"]["same_prefix_second_moment_cap_required_not_proxy_energy"] is True


def test_same_prefix_quadratic_coarea_energy_cap_source_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "same_prefix_quadratic_coarea_energy_cap_source_gate",
        {
            "same_prefix_interface_second_moment_cap_size_sum_source": True,
            "threshold_interface_payment_family": True,
            "selected_quadratic_prefix_length_fixed": True,
            "prefix_second_moment_cap_eq_interface_second_moment_cap": True,
            "threshold_interface_second_moment_prefix_le_cap": True,
            "quadratic_coarea_energy_cap_on_same_threshold_family": True,
            "quadratic_cap_fixed_before_payoff": True,
            "quadratic_cap_not_linear_owner_budget_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["SamePrefixQuadraticCoareaEnergyCapSource"] is True
    assert match["concludes"]["quadratic_coarea_energy_cap_supplies_anti_spike_receipt"] is True


def test_same_prefix_quadratic_coarea_energy_cap_rejects_linear_budget_label() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "same_prefix_quadratic_coarea_energy_cap_source_gate",
        {
            "linear_owner_budget_as_quadratic_cap": True,
            "threshold_interface_payment_family_label_only": True,
            "post_payoff_quadratic_prefix_choice": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "threshold_interface_second_moment_prefix_le_cap" in match["missing_fields"]
    assert "quadratic_cap_not_linear_owner_budget_only" in match["missing_fields"]
    assert "linear_owner_budget_as_quadratic_cap" in match["rejected_substitutes"]


def test_owner_prefix_first_moment_budget_no_second_moment_cap_packet_blocks_source() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "owner_prefix_first_moment_budget_no_second_moment_cap_packet_gate",
        {
            "interface_second_moment_concentration_spike_packet": True,
            "owner_prefix_first_moment_budget_available": True,
            "owner_root_budget_controls_linear_interface_charge": True,
            "threshold_spike_keeps_linear_charge_within_owner_budget": True,
            "quadratic_owner_budget_or_second_moment_cap_missing": True,
            "linear_budget_not_same_prefix_quadratic_cap": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["OwnerPrefixFirstMomentBudgetNoSecondMomentCapPacket"] is True
    assert match["concludes"]["owner_first_moment_budget_not_second_moment_cap"] is True


def test_owner_prefix_first_moment_budget_rejects_linear_budget_as_quadratic_cap() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "owner_prefix_first_moment_budget_no_second_moment_cap_packet_gate",
        {
            "owner_root_budget_as_second_moment_cap": True,
            "linear_coarea_charge_as_quadratic_threshold_moment": True,
            "selected_prefix_budget_label_without_second_moment_receipt": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "quadratic_owner_budget_or_second_moment_cap_missing" in match["missing_fields"]
    assert "linear_budget_not_same_prefix_quadratic_cap" in match["missing_fields"]
    assert "owner_root_budget_as_second_moment_cap" in match["rejected_substitutes"]


def test_fixed_profile_amplitude_cap_anti_spike_size_sum_source_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "fixed_profile_amplitude_cap_anti_spike_size_sum_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["FixedProfileAmplitudeCapAntiSpikeSizeSumSource"] is True
    assert match["concludes"]["same_threshold_anti_spike_receipt_from_amplitude_cap"] is True


def test_fixed_profile_weight_only_no_amplitude_cap_packet_blocks_source() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "fixed_profile_weight_only_no_amplitude_cap_packet_gate",
        {
            "fixed_profile_amplitude_cap_missing_spike_packet": True,
            "fixed_angular_profile_weight_bound_available": True,
            "physical_interface_amplitude_unbounded_on_selected_prefix": True,
            "cutoff_weight_bound_does_not_bound_strain_amplitude": True,
            "pointwise_threshold_interface_payment_cap_missing": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["FixedProfileWeightOnlyNoAmplitudeCapPacket"] is True
    assert match["concludes"]["physical_amplitude_cap_required_not_profile_weight_only"] is True


def test_fixed_profile_weight_only_no_amplitude_cap_rejects_weight_as_cap() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "fixed_profile_weight_only_no_amplitude_cap_packet_gate",
        {
            "fixed_profile_weight_bound_as_interface_amplitude_cap": True,
            "cutoff_derivative_bound_without_strain_amplitude_bound": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "physical_interface_amplitude_unbounded_on_selected_prefix" in match["missing_fields"]
    assert "pointwise_threshold_interface_payment_cap_missing" in match["missing_fields"]
    assert "fixed_profile_weight_bound_as_interface_amplitude_cap" in match["rejected_substitutes"]


def test_fixed_profile_amplitude_cap_missing_spike_packet_blocks_source() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "fixed_profile_amplitude_cap_missing_spike_packet_gate",
        {
            "interface_second_moment_concentration_spike_packet": True,
            "fixed_profile_amplitude_cap_missing": True,
            "amplitude_cap_proxy_billed_or_post_payoff": True,
            "layer_cake_first_moment_misread_as_amplitude_cap": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["FixedProfileAmplitudeCapMissingSpikePacket"] is True
    assert match["concludes"]["fixed_profile_amplitude_cap_required"] is True


def test_interface_second_moment_concentration_spike_packet_blocks_pz_source() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "interface_second_moment_concentration_spike_packet_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["InterfaceSecondMomentConcentrationSpikePacket"] is True
    assert match["concludes"]["same_threshold_anti_spike_receipt_required"] is True


def test_paley_zygmund_high_interface_debt_packet_blocks_markov_pz_source() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "paley_zygmund_high_interface_debt_packet_gate",
        {
            "high_low_size_sum_intersection_debt_packet": True,
            "cheap_boundary_lower_bound_available": True,
            "high_interface_anti_concentration_missing": True,
            "interface_second_moment_receipt_missing": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["PaleyZygmundHighInterfaceDebtPacket"] is True
    assert match["concludes"]["high_interface_second_moment_receipt_required"] is True


def test_size_sum_correlated_coarea_high_low_slice_source_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "size_sum_correlated_coarea_high_low_slice_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["SizeSumCorrelatedCoareaHighLowSliceSource"] is True
    assert match["concludes"]["threshold_size_sum_forces_intersection"] is True


def test_high_low_size_sum_intersection_debt_packet_blocks_size_sum_source() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "high_low_size_sum_intersection_debt_packet_gate",
        {
            "preprojection_projected_collar_exchange_source": True,
            "low_plus_high_measure_le_threshold_space_measure": True,
            "positive_correlation_or_size_sum_receipt_missing": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["HighLowSizeSumIntersectionDebtPacket"] is True
    assert match["concludes"]["size_sum_or_correlation_receipt_required"] is True


def test_payment_biased_coarea_slice_source_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "payment_biased_coarea_slice_source_gate",
        {
            "correlated_coarea_high_low_interface_slice_source": True,
            "interface_weighted_threshold_measure": True,
            "payment_biased_selection_fixed_before_payoff": True,
            "weighted_boundary_pays_interface_floor": True,
            "payment_bias_uses_source_interface_family": True,
            "not_uniform_threshold_size_sum_route": True,
            "not_post_payoff_payment_bias": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["PaymentBiasedCoareaSliceSource"] is True
    assert match["concludes"]["payment_biased_coarea_bypasses_uniform_threshold_pz_bottleneck"] is True


def test_payment_biased_coarea_slice_rejects_post_payoff_bias() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "payment_biased_coarea_slice_source_gate",
        {
            "payment_bias_chosen_after_projected_deficit": True,
            "target_deficit_weighted_threshold_selection": True,
            "interface_weight_from_proxy_family": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "payment_biased_selection_fixed_before_payoff" in match["missing_fields"]
    assert "payment_bias_uses_source_interface_family" in match["missing_fields"]
    assert "payment_bias_chosen_after_projected_deficit" in match["rejected_substitutes"]


def test_correlated_coarea_high_low_interface_slice_source_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "correlated_coarea_high_low_interface_slice_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["CorrelatedCoareaHighLowInterfaceSliceSource"] is True
    assert match["concludes"]["paid_overlap_reserve_le_coarea_collar_charge_via_slice"] is True


def test_quadratic_ratio_size_sum_surplus_certificate_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "quadratic_ratio_size_sum_surplus_certificate_gate",
        {
            "same_prefix_quadratic_coarea_energy_cap_source": True,
            "quadratic_ratio_pays_threshold_deficit": True,
            "ratio_lower_bound_mul_cap_le_first_moment_sq": True,
            "ratio_lower_bound_creates_overfill": True,
            "ratio_certificate_on_same_prefix": True,
            "not_just_finite_quadratic_cap": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["QuadraticRatioSizeSumSurplusCertificate"] is True
    assert match["concludes"]["m2_over_q_size_sum_surplus_paid"] is True


def test_quadratic_ratio_certificate_rejects_finite_cap_without_ratio() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "quadratic_ratio_size_sum_surplus_certificate_gate",
        {
            "finite_quadratic_cap_without_ratio": True,
            "m2_over_q_on_proxy_prefix": True,
            "cheap_boundary_deficit_unpaid": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "quadratic_ratio_pays_threshold_deficit" in match["missing_fields"]
    assert "ratio_certificate_on_same_prefix" in match["missing_fields"]
    assert "finite_quadratic_cap_without_ratio" in match["rejected_substitutes"]


def test_quadratic_cap_too_large_no_size_sum_surplus_packet_blocks_source() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "quadratic_cap_too_large_no_size_sum_surplus_packet_gate",
        {
            "paley_zygmund_high_interface_debt_packet": True,
            "finite_same_prefix_quadratic_cap_available": True,
            "high_interface_lower_bound_from_quadratic_cap_too_small": True,
            "cheap_plus_quadratic_cap_lower_bound_no_overfill": True,
            "strict_size_sum_surplus_missing": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["QuadraticCapTooLargeNoSizeSumSurplusPacket"] is True
    assert match["concludes"]["finite_quadratic_cap_not_enough_without_surplus"] is True


def test_quadratic_cap_too_large_rejects_finite_cap_as_surplus() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "quadratic_cap_too_large_no_size_sum_surplus_packet_gate",
        {
            "finite_second_moment_cap_as_size_sum_surplus": True,
            "quadratic_cap_without_m2_over_q_lower_bound": True,
            "same_prefix_quadratic_cap_label_without_overfill": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "cheap_plus_quadratic_cap_lower_bound_no_overfill" in match["missing_fields"]
    assert "strict_size_sum_surplus_missing" in match["missing_fields"]
    assert "finite_second_moment_cap_as_size_sum_surplus" in match["rejected_substitutes"]


def test_coarea_low_slice_high_overlap_disjoint_packet_blocks_correlated_slice() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "coarea_low_slice_high_overlap_disjoint_packet_gate",
        {
            "coarea_low_slice_interface_underpayment_packet": True,
            "low_boundary_set": True,
            "high_interface_set": True,
            "threshold_space_nonempty": True,
            "cheap_boundary_and_high_interface_sets_disjoint": True,
            "selected_threshold_in_low_boundary_set": True,
            "high_interface_set_avoids_selected_threshold": True,
            "rearranged_anticorrelation_witness": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["CoareaLowSliceHighOverlapDisjointPacket"] is True
    assert match["concludes"]["high_low_intersection_receipt_required"] is True


def test_coarea_low_slice_interface_underpayment_packet_blocks_bridge() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "coarea_low_slice_interface_underpayment_packet_gate",
        {
            "preprojection_projected_collar_exchange_source": True,
            "selected_extensional_interface_variation_available": True,
            "coarea_slice_chosen_for_low_boundary_invoice": True,
            "interface_variation_same_owner_but_not_slice_dominated": True,
            "coarea_collar_charge_lt_interface_variation_measure": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["CoareaLowSliceInterfaceUnderpaymentPacket"] is True
    assert match["concludes"]["high_low_correlated_coarea_slice_required"] is True


def test_interface_variation_coarea_overlap_unlinked_packet_blocks_bridge() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "interface_variation_coarea_overlap_unlinked_packet_gate",
        {
            "coarea_collar_paid_but_overlap_underpaid_packet": True,
            "selected_section_extensional_interface_variation_measure_available": True,
            "selected_absolute_variation_eq_interface_variation_measure": True,
            "interface_variation_measure_constructed_from_cutoff_formula": True,
            "interface_variation_not_mapped_to_same_coarea_collar_event": True,
            "selected_interface_variation_does_not_pay_overlap_reserve": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["InterfaceVariationCoareaOverlapUnlinkedPacket"] is True
    assert match["concludes"]["interface_to_coarea_domination_receipt_required"] is True


def test_coarea_collar_lower_payment_to_positive_tv_source_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "coarea_collar_lower_payment_to_positive_tv_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["CoareaCollarLowerPaymentToPositiveTVSource"] is True
    assert match["concludes"]["CoareaPositiveKernelTVMinorantSource"] is True


def test_coarea_collar_paid_but_overlap_underpaid_packet_blocks_bridge() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "coarea_collar_paid_but_overlap_underpaid_packet_gate",
        {
            "preprojection_projected_collar_exchange_source": True,
            "owner_preimage_coarea_collar_charge_paid": True,
            "coarea_collar_charge_maps_to_owner_budget": True,
            "overlap_reserve_lower_bound_missing": True,
            "coarea_collar_charge_lt_paid_overlap_reserve": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["CoareaCollarPaidButOverlapUnderpaidPacket"] is True
    assert match["concludes"]["overlap_lower_bound_receipt_required"] is True


def test_coarea_positive_kernel_tv_minorant_source_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "coarea_positive_kernel_tv_minorant_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["CoareaPositiveKernelTVMinorantSource"] is True
    assert match["concludes"]["PositiveLocalizedKernelTVCouplingSource"] is True


def test_coarea_upper_only_no_positive_minorant_packet_blocks_shortcut() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "coarea_upper_only_no_positive_minorant_packet_gate",
        {
            "preprojection_projected_collar_exchange_source": True,
            "nonadaptive_coarea_threshold_selected": True,
            "local_energy_or_coarea_upper_control_available": True,
            "coarea_lower_payment_missing": True,
            "positive_tv_minorant_missing_before_projection": True,
            "owner_root_budget_lt_paid_overlap_reserve": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["CoareaUpperOnlyNoPositiveMinorantPacket"] is True
    assert match["concludes"]["coarea_lower_payment_required"] is True


def test_positive_localized_kernel_tv_coupling_source_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "positive_localized_kernel_tv_coupling_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["PositiveLocalizedKernelTVCouplingSource"] is True
    assert match["concludes"]["SameOwnerLocalizedSchurTransportSource"] is True


def test_signed_pressure_no_positive_tv_minorant_packet_blocks_false_source() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "signed_pressure_no_positive_tv_minorant_packet_gate",
        {
            "preprojection_projected_collar_exchange_source": True,
            "signed_pressure_or_riesz_moment_visible": True,
            "signed_moment_not_positive_measure": True,
            "core_sheath_or_tangential_null_stress_cancellation": True,
            "positive_tv_minorant_missing_before_payoff": True,
            "owner_root_budget_lt_paid_overlap_reserve": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["SignedPressureNoPositiveTVMinorantPacket"] is True
    assert match["concludes"]["positive_tv_minorant_required"] is True


def test_same_owner_localized_schur_transport_source_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "same_owner_localized_schur_transport_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["SameOwnerLocalizedSchurTransportSource"] is True
    assert match["concludes"]["OwnerRootCapacitatedTransportCouplingSource"] is True


def test_cross_owner_schur_leakage_packet_blocks_global_l1_shortcut() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "cross_owner_schur_leakage_packet_gate",
        {
            "preprojection_projected_collar_exchange_source": True,
            "global_annular_l1_schur_bound_available": True,
            "cross_owner_kernel_tail_contributes_to_selected_overlap": True,
            "same_owner_localized_schur_bound_missing": True,
            "cutoff_boundary_invoice_unpaid": True,
            "pressure_leray_tail_leakage_unpaid": True,
            "owner_root_budget_lt_paid_overlap_reserve": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["CrossOwnerSchurLeakagePacket"] is True
    assert match["concludes"]["same_owner_localized_schur_receipt_required"] is True


def test_owner_root_capacitated_transport_coupling_source_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "owner_root_capacitated_transport_coupling_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["OwnerRootCapacitatedTransportCouplingSource"] is True
    assert match["concludes"]["PrePayoffOverlapPreimageSource"] is True


def test_capacitated_transport_hall_defect_packet_requires_cut_capacity() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "capacitated_transport_hall_defect_packet_gate",
        {
            "preprojection_projected_collar_exchange_source": True,
            "requested_coupling_mass_nonnegative": True,
            "paid_overlap_reserve_le_requested_coupling_mass": True,
            "kernel_relation_support_available": True,
            "hall_cut_capacity_defect": True,
            "no_marginal_dominated_coupling_of_requested_mass": True,
            "complete_bipartite_support_not_a_coupling_receipt": True,
            "owner_root_budget_lt_paid_overlap_reserve": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["CapacitatedTransportHallDefectPacket"] is True
    assert match["concludes"]["hall_or_max_flow_capacity_receipt_required"] is True


def test_complete_bipartite_kernel_pair_multiplicity_packet_requires_owner_sparse_selection() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "complete_bipartite_kernel_pair_multiplicity_packet_gate",
        {
            "preprojection_projected_collar_exchange_source": True,
            "pair_multiplicity_charge_nonnegative": True,
            "paid_overlap_reserve_le_pair_multiplicity_charge": True,
            "complete_bipartite_pairing_before_projection": True,
            "owner_root_aligned_sparse_selection_missing": True,
            "pair_multiplicity_not_bounded_by_owner_atoms": True,
            "owner_root_budget_lt_paid_overlap_reserve": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["CompleteBipartiteKernelPairMultiplicityPacket"] is True
    assert match["concludes"]["owner_root_aligned_sparse_selection_required"] is True



def test_kernel_relation_not_owner_preimage_packet_requires_sparse_domination() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "kernel_relation_not_owner_preimage_packet_gate",
        {
            "preprojection_projected_collar_exchange_source": True,
            "kernel_relation_charge_nonnegative": True,
            "paid_overlap_reserve_le_kernel_relation_charge": True,
            "kernel_relation_charge_is_pair_currency": True,
            "pair_to_owner_sparse_domination_missing": True,
            "pair_multiplicity_can_exceed_owner_budget": True,
            "owner_root_budget_lt_paid_overlap_reserve": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["KernelRelationNotOwnerPreimagePacket"] is True
    assert match["concludes"]["kernel_relation_sparse_domination_required"] is True



def test_annular_kernel_l1_overlap_preimage_gap_packet_blocks_false_payment() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "annular_kernel_l1_overlap_preimage_gap_packet_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["AnnularKernelL1OverlapPreimageGapPacket"] is True
    assert match["concludes"]["annular_l1_sizes_but_does_not_source_overlap_preimage"] is True



def test_post_projection_overlap_only_packet_blocks_pre_payoff_overlap_source() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "post_projection_overlap_only_packet_gate",
        {
            "preprojection_projected_collar_exchange_source": True,
            "projected_window_creates_overlap": True,
            "source_overlap_preimage_missing_before_projection": True,
            "overlap_reserve_defined_from_projected_deficit": True,
            "owner_root_budget_lt_paid_overlap_reserve": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["PostProjectionOverlapOnlyPacket"] is True
    assert match["concludes"]["pre_payoff_overlap_preimage_required"] is True



def test_paid_nonzero_overlap_reserve_underpaid_packet_blocks_finite_paid_source() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "paid_nonzero_overlap_reserve_underpaid_packet_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["PaidNonzeroOverlapReserveUnderpaidPacket"] is True
    assert match["concludes"]["paid_nonzero_overlap_reserve_required"] is True



def test_unpaid_projected_overlap_reserve_packet_blocks_paid_overlap_source() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "unpaid_projected_overlap_reserve_packet_gate",
        {
            "preprojection_projected_collar_exchange_source": True,
            "existing_collar_reserve_spend_nonnegative": True,
            "projected_window_overlap_present": True,
            "paid_projected_overlap_reserve_missing": True,
            "overlap_reserve_would_need_same_owner_root": True,
            "overlap_reserve_would_need_pre_projection_timing": True,
            "owner_root_budget_lt_projected_payment": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["UnpaidProjectedOverlapReservePacket"] is True
    assert match["concludes"]["paid_overlap_reserve_required"] is True



def test_spatial_support_eigencone_mismatch_packet_matches_geometry_confuser() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "spatial_support_eigencone_mismatch_packet_gate",
        {
            "eigenframe_label_without_selected_cone_inclusion_packet": True,
            "positive_stretching_eigenvector_exists": True,
            "selected_spatial_support_outside_positive_eigencone": True,
            "tangent_eigenvector_not_spatial_support_receipt": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["SpatialSupportEigenconeMismatchPacket"] is True
    assert match["concludes"]["spatial_support_cone_receipt_required"] is True


def test_spatial_support_eigencone_mismatch_rejects_direction_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "spatial_support_eigencone_mismatch_packet_gate",
        {
            "positive_stretching_direction_only": True,
            "vorticity_alignment_only": True,
            "eigenvector_label_as_spatial_support": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "selected_spatial_support_outside_positive_eigencone" in match["missing_fields"]
    assert "tangent_eigenvector_not_spatial_support_receipt" in match["missing_fields"]
    assert "vorticity_alignment_only" in match["rejected_substitutes"]


def test_eigenframe_label_without_selected_cone_inclusion_packet_matches_confuser() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "eigenframe_label_without_selected_cone_inclusion_packet_gate",
        {
            "raw_positive_eigencone_loss_unpaid_packet": True,
            "affine_eigenframe_label_exists": True,
            "positive_eigenvalue_label_exists": True,
            "selected_cone_inclusion_missing": True,
            "active_scale_eigenvalue_equality_missing": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["EigenframeLabelWithoutSelectedConeInclusionPacket"] is True
    assert match["concludes"]["selected_cone_inclusion_required"] is True


def test_eigenframe_label_without_selected_cone_inclusion_rejects_labels_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "eigenframe_label_without_selected_cone_inclusion_packet_gate",
        {
            "eigenframe_label_only": True,
            "positive_eigenvalue_label_only": True,
            "selected_cone_label_without_inclusion": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "selected_cone_inclusion_missing" in match["missing_fields"]
    assert "active_scale_eigenvalue_equality_missing" in match["missing_fields"]
    assert "eigenframe_label_only" in match["rejected_substitutes"]


def test_localized_affine_eigenframe_section_binding_source_matches_consumer() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "localized_affine_eigenframe_section_binding_source_gate",
        {
            "affine_positive_eigencone_loss_paid_interface_variation_source": True,
            "positive_eigenvalue_nonnegative": True,
            "trace_zero_eigenvalue_sum": True,
            "remaining_eigenvalue_le_positive_eigenvalue": True,
            "selected_direction_in_fixed_cone": True,
            "selected_direction_cos_sq_le_one": True,
            "active_scale_strain_eq_positive_eigenvalue": True,
            "selected_section_cone_inclusion_from_packet_geometry": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["LocalizedAffineEigenframeSectionBindingSource"] is True
    assert match["concludes"]["finite_dimensional_cone_lower_bound_available"] is True


def test_localized_affine_eigenframe_section_binding_rejects_labels_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "localized_affine_eigenframe_section_binding_source_gate",
        {
            "eigenframe_label_only": True,
            "selected_cone_label_without_inclusion": True,
            "active_scale_label_without_eigenvalue_equality": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "trace_zero_eigenvalue_sum" in match["missing_fields"]
    assert "selected_direction_in_fixed_cone" in match["missing_fields"]
    assert "eigenframe_label_only" in match["rejected_substitutes"]


def test_raw_positive_eigencone_loss_unpaid_packet_matches_geometric_loss_confuser() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "raw_positive_eigencone_loss_unpaid_packet_gate",
        {
            "section_label_only_interface_variation_oracle_ambiguity_packet": True,
            "positive_eigencone_exists": True,
            "raw_cone_variation_pays_only_geometric_fraction": True,
            "cone_loss_paid_before_projection_missing": True,
            "raw_cone_interface_variation_lt_reynolds_excess": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["RawPositiveEigenconeLossUnpaidPacket"] is True
    assert match["concludes"]["cone_loss_payment_required"] is True


def test_raw_positive_eigencone_loss_unpaid_rejects_paid_loss() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "raw_positive_eigencone_loss_unpaid_packet_gate",
        {
            "raw_cone_variation_only": True,
            "cone_constant_ignored": True,
            "normalized_after_projection": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "cone_loss_paid_before_projection_missing" in match["missing_fields"]
    assert "raw_cone_interface_variation_lt_reynolds_excess" in match["missing_fields"]
    assert "raw_cone_variation_only" in match["rejected_substitutes"]


def test_affine_positive_eigencone_loss_paid_interface_variation_source_matches_target() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "affine_positive_eigencone_loss_paid_interface_variation_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["AffinePositiveEigenconeLossPaidInterfaceVariationSource"] is True
    assert match["concludes"]["raw_cone_loss_paid_before_projection"] is True


def test_affine_positive_eigencone_loss_paid_rejects_raw_cone_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "affine_positive_eigencone_loss_paid_interface_variation_source_gate",
        {
            "raw_cone_variation_only": True,
            "cone_constant_ignored": True,
            "dimensionless_pi_without_physical_ratio": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "cone_loss_paid_before_projection" in match["missing_fields"]
    assert "active_scale_pi_pinned_as_sR2_over_nu" in match["missing_fields"]
    assert "dimensionless_pi_without_physical_ratio" in match["rejected_substitutes"]


def test_section_label_only_interface_variation_oracle_ambiguity_matches_old_wall() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "section_label_only_interface_variation_oracle_ambiguity_packet_gate",
        {
            "post_payoff_section_repair_packet": True,
            "same_section_identity_labels_fixed": True,
            "lower_envelope_or_scalar_data_fixed": True,
            "extensional_interface_variation_measure_missing": True,
            "two_compatible_selected_variation_values": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["SectionLabelOnlyInterfaceVariationOracleAmbiguityPacket"] is True
    assert match["concludes"]["extensional_interface_measure_required"] is True


def test_section_label_only_interface_variation_oracle_rejects_extensional_measure() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "section_label_only_interface_variation_oracle_ambiguity_packet_gate",
        {
            "section_identity_label_only": True,
            "lower_envelope_scalar_only": True,
            "selected_absolute_variation_asserted_without_measure": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "extensional_interface_variation_measure_missing" in match["missing_fields"]
    assert "two_compatible_selected_variation_values" in match["missing_fields"]
    assert "section_identity_label_only" in match["rejected_substitutes"]


def test_selected_section_extensional_interface_variation_measure_source_matches_positive_target() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "selected_section_extensional_interface_variation_measure_source_gate",
        {
            "selected_section_absolute_interface_variation_identity_source": True,
            "interface_variation_measure_nonnegative": True,
            "selected_absolute_variation_eq_interface_variation_measure": True,
            "interface_variation_measure_constructed_from_cutoff_formula": True,
            "extensional_measure_fixed_before_section_repair": True,
            "not_determined_by_section_label_or_lower_envelope_only": True,
            "reynolds_excess_le_selected_absolute_variation": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["SelectedSectionExtensionalInterfaceVariationMeasureSource"] is True
    assert match["concludes"]["oracle_ambiguity_avoided_by_extensional_measure"] is True


def test_selected_section_extensional_interface_variation_rejects_scalar_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "selected_section_extensional_interface_variation_measure_source_gate",
        {
            "section_identity_label_only": True,
            "lower_envelope_scalar_only": True,
            "selected_absolute_variation_asserted_without_measure": True,
            "post_payoff_measure_repair": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "interface_variation_measure_constructed_from_cutoff_formula" in match["missing_fields"]
    assert "not_determined_by_section_label_or_lower_envelope_only" in match["missing_fields"]
    assert "lower_envelope_scalar_only" in match["rejected_substitutes"]


def test_selected_section_absolute_interface_variation_rejects_label_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "selected_section_absolute_interface_variation_identity_source_gate",
        {
            "proxy_section_repaired_after_payoff": True,
            "selected_section_label_only": True,
            "absolute_variation_exists_only": True,
            "owner_label_without_preimage_payment": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "selected_section_identity_fixed_before_payoff" in match["missing_fields"]
    assert "reynolds_excess_le_selected_absolute_variation" in match["missing_fields"]
    assert "selected_section_label_only" in match["rejected_substitutes"]
    assert "owner_label_without_preimage_payment" in match["rejected_substitutes"]


def test_signed_transport_commutator_cancellation_packet_matches_positive_variation_gap() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "signed_transport_commutator_cancellation_packet_gate",
        {
            "proxy_owner_transport_commutator_underpayment_packet": True,
            "same_localized_packet_owner_includes_interface": True,
            "signed_transport_commutator_cancels_on_selected_prefix": True,
            "absolute_interface_variation_payment_missing": True,
            "signed_final_commutator_lt_reynolds_excess": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["SignedTransportCommutatorCancellationPacket"] is True
    assert match["concludes"]["absolute_interface_variation_payment_required"] is True


def test_signed_transport_commutator_cancellation_rejects_signed_payment_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "signed_transport_commutator_cancellation_packet_gate",
        {
            "signed_final_commutator_payment_only": True,
            "same_owner_label_without_absolute_variation": True,
            "positive_part_chosen_after_payoff": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "absolute_interface_variation_payment_missing" in match["missing_fields"]
    assert "signed_transport_commutator_cancels_on_selected_prefix" in match["missing_fields"]
    assert "signed_final_commutator_payment_only" in match["rejected_substitutes"]
    assert "positive_part_chosen_after_payoff" in match["rejected_substitutes"]


def test_proxy_owner_transport_commutator_underpayment_packet_matches_owner_mismatch() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "proxy_owner_transport_commutator_underpayment_packet_gate",
        {
            "localized_affine_euler_core_high_pi_underpayment_packet": True,
            "transport_cutoff_commutator_exists_with_high_pi_scaling": True,
            "commutator_charged_to_proxy_owner": True,
            "selected_c7_surplus_owner_unpaid_by_proxy_commutator": True,
            "same_selected_prefix_map_missing": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["ProxyOwnerTransportCommutatorUnderpaymentPacket"] is True
    assert match["concludes"]["same_selected_prefix_map_is_required"] is True


def test_proxy_owner_transport_commutator_underpayment_rejects_same_prefix_repair() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "proxy_owner_transport_commutator_underpayment_packet_gate",
        {
            "transport_cutoff_commutator_charged_to_same_selected_owner": True,
            "same_selected_prefix_map_proved": True,
            "final_pressure_carrier_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "commutator_charged_to_proxy_owner" in match["missing_fields"]
    assert "same_selected_prefix_map_missing" in match["missing_fields"]
    assert "transport_cutoff_commutator_charged_to_same_selected_owner" in match["rejected_substitutes"]
    assert "same_selected_prefix_map_proved" in match["rejected_substitutes"]


def test_localized_affine_euler_core_high_pi_interface_payment_source_matches_commutator_payer() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "localized_affine_euler_core_high_pi_interface_payment_source_gate",
        {
            "parabolic_channel_coefficient_estimate_source": True,
            "transport_cutoff_commutator_generated_before_payoff": True,
            "transport_cutoff_commutator_charged_to_same_selected_owner": True,
            "transport_cutoff_commutator_pays_reynolds_excess": True,
            "effective_coefficient_splits_transport_interface": True,
            "not_final_pressure_or_square_overflow_budget": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["LocalizedAffineEulerCoreHighPiInterfacePaymentSource"] is True
    assert match["concludes"]["ParabolicChannelCoefficientEstimateSource"] is True


def test_localized_affine_euler_core_high_pi_interface_payment_rejects_proxy_commutator() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "localized_affine_euler_core_high_pi_interface_payment_source_gate",
        {
            "transport_commutator_exists_but_proxy_owner": True,
            "commutator_charged_after_payoff": True,
            "final_pressure_carrier_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "transport_cutoff_commutator_charged_to_same_selected_owner" in match["missing_fields"]
    assert "transport_cutoff_commutator_pays_reynolds_excess" in match["missing_fields"]
    assert "transport_commutator_exists_but_proxy_owner" in match["rejected_substitutes"]
    assert "commutator_charged_after_payoff" in match["rejected_substitutes"]


def test_localized_affine_euler_core_high_pi_underpayment_packet_matches_scaling_obstruction() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "localized_affine_euler_core_high_pi_underpayment_packet_gate",
        {
            "parabolic_effective_invoice_underpaid_channel_packet": True,
            "active_reynolds_ratio_eq_sR2_over_nu": True,
            "core_affine_equation_paid_by_pressure_and_time_derivative": True,
            "cutoff_shell_coefficient_does_not_scale_with_pi": True,
            "localization_interface_is_only_possible_high_pi_payment": True,
            "effective_invoice_coefficient_lt_reynolds_excess": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["LocalizedAffineEulerCoreHighPiUnderpaymentPacket"] is True
    assert match["concludes"]["positive_route_must_extract_high_pi_interface_payment"] is True


def test_localized_affine_euler_core_high_pi_underpayment_rejects_cutoff_shell_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "localized_affine_euler_core_high_pi_underpayment_packet_gate",
        {
            "cutoff_shell_invoice_only": True,
            "core_affine_pressure_cancellation_as_payment": True,
            "dimensionless_ratio_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "parabolic_effective_invoice_underpaid_channel_packet" in match["missing_fields"]
    assert "localization_interface_is_only_possible_high_pi_payment" in match["missing_fields"]
    assert "cutoff_shell_invoice_only" in match["rejected_substitutes"]
    assert "core_affine_pressure_cancellation_as_payment" in match["rejected_substitutes"]


def test_parabolic_effective_invoice_underpaid_channel_packet_matches_gap() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "parabolic_effective_invoice_underpaid_channel_packet_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["ParabolicEffectiveInvoiceCoefficientUnderpaidChannelPacket"] is True
    assert match["concludes"]["channel_decomposition_alone_does_not_pay_high_pi"] is True


def test_parabolic_effective_invoice_underpaid_channel_packet_rejects_channel_estimate() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "parabolic_effective_invoice_underpaid_channel_packet_gate",
        {
            "time_dependent_local_affine_jet": True,
            "same_owner_selected_c7_tent": True,
            "reynolds_excess_le_effective_invoice_coefficient": True,
            "reynolds_excess_le_effectiveInvoiceCoefficient_from_channel_estimates": True,
            "dimensionless_ratio_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "effective_invoice_coefficient_lt_reynolds_excess" in match["missing_fields"]
    assert "effective_invoice_coefficient_eq_sum_prepaid_channel_coefficients" in match["missing_fields"]
    assert "reynolds_excess_le_effective_invoice_coefficient" in match["rejected_substitutes"]
    assert "reynolds_excess_le_effectiveInvoiceCoefficient_from_channel_estimates" in match["rejected_substitutes"]



def test_parabolic_channel_coefficient_estimate_source_matches_exact_consumer() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "parabolic_channel_coefficient_estimate_source_gate",
        {
            "parabolic_effective_invoice_coefficient_pays_affine_surplus": True,
            "effective_invoice_coefficient_eq_sum_prepaid_channel_coefficients": True,
            "each_channel_coefficient_fixed_before_payoff": True,
            "each_channel_coefficient_paid_by_same_owner_invoice": True,
            "reynolds_excess_le_effectiveInvoiceCoefficient_from_channel_estimates": True,
            "coefficient_not_recovered_from_totalInvoice_or_surplus_conclusion": True,
            "channel_coefficient_estimate_is_only_open_pde_input": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["ParabolicChannelCoefficientEstimateSource"] is True
    assert match["concludes"]["ParabolicFiniteEnergyInvoiceLowerBoundForLocalizedAffineTent"] is True


def test_parabolic_channel_coefficient_estimate_source_rejects_underpaid_gap() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "parabolic_channel_coefficient_estimate_source_gate",
        {
            "effective_invoice_coefficient_lt_reynolds_excess": True,
            "channel_decomposition_only": True,
            "coefficient_labels_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "reynolds_excess_le_effectiveInvoiceCoefficient_from_channel_estimates" in match["missing_fields"]
    assert "effective_invoice_coefficient_lt_reynolds_excess" in match["rejected_substitutes"]
    assert "channel_decomposition_only" in match["rejected_substitutes"]


def test_parabolic_effective_invoice_coefficient_matches_sourced_dynamic_budget() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "parabolic_effective_invoice_coefficient_pays_affine_surplus_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["ParabolicEffectiveInvoiceCoefficientPaysAffineSurplus"] is True
    assert match["concludes"]["ParabolicFiniteEnergyInvoiceLowerBoundForLocalizedAffineTent"] is True


def test_parabolic_effective_invoice_coefficient_rejects_tautological_coefficient() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "parabolic_effective_invoice_coefficient_pays_affine_surplus_gate",
        {
            "time_dependent_local_affine_jet": True,
            "same_owner_selected_c7_tent": True,
            "effective_invoice_coefficient_defined_as_total_invoice_over_A": True,
            "coefficient_chosen_after_payoff": True,
            "fixed_cutoff_constant_only": True,
            "dimensionless_ratio_only": True,
            "chosen_after_eta": True,
            "chosen_after_totalInvoice": True,
            "conclusion_divided_by_A": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "effective_invoice_coefficient_fixed_before_payoff" in match["missing_fields"]
    assert "effective_invoice_coefficient_eq_sum_prepaid_channel_coefficients" in match["missing_fields"]
    assert "each_channel_coefficient_fixed_before_payoff" in match["missing_fields"]
    assert "reynolds_excess_le_effective_invoice_coefficient" in match["missing_fields"]
    assert "effective_invoice_coefficient_times_A_le_total_invoice" in match["missing_fields"]
    assert "effective_invoice_coefficient_defined_as_total_invoice_over_A" in match["rejected_substitutes"]
    assert "coefficient_chosen_after_payoff" in match["rejected_substitutes"]
    assert "conclusion_divided_by_A" in match["rejected_substitutes"]


def test_parabolic_pi_lock_owner_label_only_confuser_matches_missing_source_contract() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "parabolic_pi_lock_owner_label_only_confuser_gate",
        {
            "time_dependent_local_affine_jet": True,
            "same_owner_selected_c7_tent": True,
            "owner_label_fixed_before_payoff": True,
            "selected_c7_owner_label": True,
            "ratio_source_contract_missing": True,
            "eta_gt_cutoff_constant": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["ParabolicPiLockOwnerLabelOnlyConfuser"] is True
    assert match["concludes"]["owner_label_only_does_not_source_pi_lock"] is True


def test_parabolic_pi_lock_owner_label_only_confuser_rejects_actual_source_contract() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "parabolic_pi_lock_owner_label_only_confuser_gate",
        {
            "time_dependent_local_affine_jet": True,
            "same_owner_selected_c7_tent": True,
            "owner_label_fixed_before_payoff": True,
            "selected_c7_owner_label": True,
            "affine_reynolds_ratio_eq_sR2_over_nu": True,
            "ratio_fixed_before_payoff": True,
            "eta_le_reynolds_excess_from_affine_packet_geometry": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "ratio_source_contract_missing" in match["missing_fields"]
    assert "eta_gt_cutoff_constant" in match["missing_fields"]
    assert "affine_reynolds_ratio_eq_sR2_over_nu" in match["rejected_substitutes"]
    assert "ratio_fixed_before_payoff" in match["rejected_substitutes"]


def test_parabolic_active_scale_pi_lock_matches_reynolds_deficit_bridge() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "parabolic_active_scale_pi_lock_for_cutoff_payment_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["ParabolicActiveScalePiLockForCutoffPayment"] is True
    assert match["concludes"]["ParabolicCutoffInvoicePaysAffineSurplusModel"] is True
    assert match["concludes"]["eta_le_cutoff_constant_from_pi_lock"] is True


def test_parabolic_active_scale_pi_lock_rejects_ownership_or_ratio_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "parabolic_active_scale_pi_lock_for_cutoff_payment_gate",
        {
            "time_dependent_local_affine_jet": True,
            "same_owner_selected_c7_tent": True,
            "ownership_only": True,
            "dimensionless_ratio_only": True,
            "finite_energy_high_pi_regime_only": True,
            "reynolds_bound_missing": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "affine_reynolds_ratio_defined" in match["missing_fields"]
    assert "affine_reynolds_ratio_eq_sR2_over_nu" in match["missing_fields"]
    assert "ratio_fixed_before_payoff" in match["missing_fields"]
    assert "eta_le_reynolds_excess" in match["missing_fields"]
    assert "eta_le_reynolds_excess_from_affine_packet_geometry" in match["missing_fields"]
    assert "reynolds_le_one_plus_cutoff_constant" in match["missing_fields"]
    assert "reynolds_le_one_plus_cutoff_constant_from_finite_energy_cutoff" in match["missing_fields"]
    assert "ownership_only" in match["rejected_substitutes"]
    assert "dimensionless_ratio_only" in match["rejected_substitutes"]
    assert "reynolds_bound_missing" in match["rejected_substitutes"]


def test_parabolic_finite_energy_invoice_lower_bound_rejects_final_carrier_substitutes() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "parabolic_finite_energy_invoice_lower_bound_for_localized_affine_tent_gate",
        {
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
            "final_carrier_only_pressure": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "final_carrier_only_pressure" in match["rejected_substitutes"]


def test_parabolic_finite_energy_invoice_lower_bound_matches_full_same_owner_payment() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "parabolic_finite_energy_invoice_lower_bound_for_localized_affine_tent_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["ParabolicFiniteEnergyInvoiceLowerBoundForLocalizedAffineTent"] is True
    assert match["concludes"]["LocalizedC7TentCutoffInvoiceLeakPacket_excluded"] is True


def test_balanced_core_sheath_trace_zero_positive_net_budget_exclusion_rejects_scalar_stealth() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "balanced_core_sheath_trace_zero_positive_net_budget_exclusion_gate",
        {
            "balanced_core_sheath_dini_ladder_packet": True,
            "same_trajectory_NS_jet_compatibility": True,
            "scalar_pressure_stealth_only": True,
            "single_direction_pressure_sample": True,
            "positive_net_budget_confuser": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "pressure_samples_on_same_fresh_annular_source" in match["missing_fields"]
    assert "source_to_strain_production_coercivity" in match["missing_fields"]
    assert "framePressureStealth_to_sameTrajectoryProductionBound" in match["missing_fields"]
    assert "pressure_and_retuning_errors_below_eta_A_gap" in match["missing_fields"]
    assert "scalar_pressure_stealth_only" in match["rejected_substitutes"]
    assert "positive_net_budget_confuser" in match["rejected_substitutes"]


def test_balanced_core_sheath_trace_zero_positive_net_budget_exclusion_matches_fixed_frame_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "balanced_core_sheath_trace_zero_positive_net_budget_exclusion_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"][
        "TraceZeroPositiveNetBudgetQuantitativeExclusionReceipt"
    ] is True
    assert match["concludes"][
        "no_TraceZeroStrainPositiveNetBudgetJet_of_quantitativePressureProductionBound"
    ] is True


def test_pressure_hessian_l2_frame_self_tax_budget_source_rejects_proxy_carrier() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "pressure_hessian_l2_frame_self_tax_budget_source_gate",
        {
            "pressure_hessian_l2_controls_frame_self_tax": True,
            "pressure_l2_visibility_only": True,
            "pressure_carrier_proxy": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "pressure_l2_cap_pays_viscous_error" in match["missing_fields"]
    assert "same_source_pressure_l2_carrier" in match["missing_fields"]
    assert "pressure_carrier_proxy" in match["rejected_substitutes"]


def test_pressure_hessian_l2_frame_self_tax_budget_source_matches_cap() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "pressure_hessian_l2_frame_self_tax_budget_source_gate",
        {
            "pressure_hessian_l2_controls_frame_self_tax": True,
            "renormalized_pressure_l2_cap": True,
            "pressure_l2_cap_pays_viscous_error": True,
            "same_source_pressure_l2_carrier": True,
            "commutator_and_transport_remainder_accounted": True,
            "no_proxy_pressure_carrier": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["PressureHessianL2FrameSelfTaxBudgetSource"] is True
    assert match["concludes"][
        "frameSelfTaxPrice_le_viscous_plus_two_error_of_pressureHessianL2Source"
    ] is True



def test_same_window_presummed_pressure_frame_self_tax_rejects_final_carrier() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "same_window_presummed_pressure_frame_self_tax_estimate_gate",
        {
            "presummed_absolute_pressure_frame_charge": True,
            "final_signed_l2_carrier": True,
            "pressure_l2_visibility_only": True,
            "same_window_core_sheath_cancellation_still_admissible": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "presummed_frame_charge_fixed_before_payoff" in match["missing_fields"]
    assert "presummed_absolute_not_final_signed_carrier" in match["missing_fields"]
    assert "final_signed_l2_carrier" in match["rejected_substitutes"]


def test_same_window_presummed_pressure_frame_self_tax_matches_paid_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "same_window_presummed_pressure_frame_self_tax_estimate_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["SameWindowPreSummedPressureFrameSelfTaxEstimate"] is True
    assert match["concludes"]["TraceZeroPositiveNetBudgetDualPriceFrameReceipt"] is True

def test_pressure_l2_cap_pays_same_source_frame_self_tax_rejects_null_stress() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "pressure_l2_cap_pays_same_source_frame_self_tax_gate",
        {
            "same_source_pressure_l2_carrier": True,
            "pressure_l2_visibility_only": True,
            "tangential_divdiv_null_stress_still_admissible": True,
            "production_sq_bound_on_proxy_window": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "no_tangential_divdiv_null_stress_on_production_frame" in match["missing_fields"]
    assert "production_sq_le_viscous_times_frame_self_tax_same_window" in match["missing_fields"]
    assert "tangential_divdiv_null_stress_still_admissible" in match["rejected_substitutes"]


def test_pressure_l2_cap_pays_same_source_frame_self_tax_matches_same_window_dual_price() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "pressure_l2_cap_pays_same_source_frame_self_tax_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["PressureL2CapPaysSameSourceFrameSelfTax"] is True
    assert match["concludes"]["TraceZeroPositiveNetBudgetDualPriceFrameReceipt"] is True



def test_pressure_l2_cap_pays_same_source_frame_self_tax_rejects_underseparated_channels() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "pressure_l2_cap_pays_same_source_frame_self_tax_gate",
        {
            "same_source_pressure_l2_carrier": True,
            "no_tangential_divdiv_null_stress_on_production_frame": True,
            "no_same_window_core_sheath_cancellation_for_l2_frame": True,
            "transport_commutator_remainder_billed_to_same_owner_window": True,
            "no_higher_jet_retuning_of_l2_residual_over_dwell": True,
            "pressure_l2_controls_frame_self_tax_on_same_window": True,
            "pressure_l2_cap_pays_viscous_error": True,
            "production_sq_le_viscous_times_frame_self_tax_same_window": True,
            "invoice_channel_missing": True,
            "no_reuse_channel_missing": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "production_invoice_channel_separated" in match["missing_fields"]
    assert "no_reuse_channel_separated_for_l2_frame_self_tax" in match["missing_fields"]
    assert "invoice_channel_missing" in match["rejected_substitutes"]
    assert "no_reuse_channel_missing" in match["rejected_substitutes"]

def test_balanced_core_sheath_dual_price_frame_exclusion_rejects_rank_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "balanced_core_sheath_dual_price_frame_exclusion_gate",
        {
            "balanced_core_sheath_dini_ladder_packet": True,
            "same_trajectory_NS_jet_compatibility": True,
            "pressure_samples_on_same_fresh_annular_source": True,
            "rank5_tomography_without_dual_product_bound": True,
            "frame_self_tax_price_unbounded": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "dual_price_bound_from_frame_pressure" in match["missing_fields"]
    assert "production_sq_le_viscous_times_frame_self_tax" in match["missing_fields"]
    assert "error_reserve_below_eta_A_gap" in match["missing_fields"]
    assert "rank5_tomography_without_dual_product_bound" in match["rejected_substitutes"]


def test_balanced_core_sheath_dual_price_frame_exclusion_matches_dual_product() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "balanced_core_sheath_dual_price_frame_exclusion_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["TraceZeroPositiveNetBudgetDualPriceFrameReceipt"] is True
    assert match["concludes"][
        "no_TraceZeroStrainPositiveNetBudgetJet_of_dualPriceFrameReceipt"
    ] is True



def test_selected_balanced_cone_signed_global_budget_rejects_pressure_visibility() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "selected_balanced_cone_signed_global_budget_gate",
        {
            "packet_encodes_near_stealth_balanced_cone": True,
            "same_owner_selected_stream": True,
            "pressure_l2_visibility_only": True,
            "positive_net_budget_confuser": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "signed_budget_nonpositive" in match["missing_fields"]
    assert "budget_not_from_pressure_visibility_only" in match["missing_fields"]
    assert "production_channel_separated" in match["missing_fields"]
    assert "no_reuse_channel_separated_for_signed_budget" in match["missing_fields"]
    assert "pressure_l2_visibility_only" in match["rejected_substitutes"]
    assert "positive_net_budget_confuser" in match["rejected_substitutes"]


def test_selected_balanced_cone_signed_global_budget_matches_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "selected_balanced_cone_signed_global_budget_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["SelectedBalancedConeSignedGlobalBudgetReceipt"] is True
    assert match["concludes"]["BalancedCoreSheathSignedGrowthSterilityReceipt"] is True

def test_balanced_core_sheath_sos_gap_certificate_rejects_numeric_sdp_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "balanced_core_sheath_sos_gap_certificate_gate",
        {
            "balanced_core_sheath_dini_ladder_packet": True,
            "packet_encodes_near_stealth_balanced_cone": True,
            "same_owner_selected_stream": True,
            "numeric_sdp_float_certificate_only": True,
            "zero_slack_certificate": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "exact_dissipation_minus_production_sos_identity" in match["missing_fields"]
    assert "positive_slack" in match["missing_fields"]
    assert "numeric_sdp_float_certificate_only" in match["rejected_substitutes"]


def test_balanced_core_sheath_sos_gap_certificate_matches_exact_source() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "balanced_core_sheath_sos_gap_certificate_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["BalancedCoreSheathSosGapCertificateSource"] is True
    assert match["concludes"]["BalancedCoreSheathSignedGrowthSterilityReceipt"] is True


def test_balanced_core_sheath_signed_growth_sterility_rejects_local_pockets() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "balanced_core_sheath_signed_growth_sterility_gate",
        {
            "balanced_core_sheath_dini_ladder_packet": True,
            "packet_encodes_near_stealth_balanced_cone": True,
            "same_owner_selected_stream": True,
            "local_positive_pockets_only": True,
            "pointwise_torque_only": True,
            "unsigned_production_budget": True,
            "positive_net_budget_confuser": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "stealth_growth_sterile" in match["missing_fields"]
    assert "enstrophy_budget_consistent" in match["missing_fields"]
    assert "local_positive_pockets_only" in match["rejected_substitutes"]
    assert "positive_net_budget_confuser" in match["rejected_substitutes"]


def test_balanced_core_sheath_signed_growth_sterility_matches_same_trajectory_budget() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "balanced_core_sheath_signed_growth_sterility_gate",
        {
            "balanced_core_sheath_dini_ladder_packet": True,
            "packet_encodes_near_stealth_balanced_cone": True,
            "same_owner_selected_stream": True,
            "selected_packet_would_need_growth_bearing_segment": True,
            "enstrophy_budget_consistent": True,
            "stealth_growth_sterile": True,
            "signed_budget_fixed_before_blowup_claim": True,
            "signed_global_budget_not_local_pockets": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["BalancedCoreSheathSignedGrowthSterilityReceipt"] is True


def test_balanced_core_sheath_dynamic_transversality_matches_uniform_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "balanced_core_sheath_dynamic_transversality_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert (
        match["concludes"]["BalancedCoreSheathDiniDynamicTransversalityReceipt"]
        is True
    )
    assert (
        match["concludes"]["balanced_core_sheath_dini_ladder_excluded_or_paid"]
        is True
    )


def test_tracefree_dimensional_length_payment_rejects_free_pi_group() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_dimensional_length_payment",
        {
            "macro_length_ratio_available_only": True,
            "free_pi_group_without_physical_constraint": True,
            "local_blowup_rescaling_removes_macro_length": True,
            "DSS_limit_trivializes_external_length": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "free_pi_group_without_physical_constraint" in match[
        "rejected_substitutes"
    ]
    assert "macro_length_survives_local_blowup_rescaling" in match[
        "missing_fields"
    ]


def test_tracefree_dimensional_length_payment_matches_full_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_dimensional_length_payment",
        {
            "tracefree_variation_pointwise_same_carrier_payment": True,
            "macro_length_fixed_before_payoff": True,
            "geometric_decay_from_external_scale": True,
            "macro_length_survives_local_blowup_rescaling": True,
            "local_payment_not_boundary_or_low_mode_only": True,
            "not_nu_parabolic_scale": True,
            "not_target_defined_length": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert (
        match["concludes"]["TraceFreeVariationDimensionalLengthPaymentReceipt"]
        is True
    )
    assert (
        match["concludes"]["TraceFreeVariationPointwiseSameCarrierPaymentReceipt"]
        is True
    )


def test_tracefree_commutator_nullform_payment_rejects_signed_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_commutator_nullform_pointwise_payment",
        {
            "signed_commutator_cancellation_available_only": True,
            "square_or_signed_currency_only": True,
            "degree_zero_riesz_symbol_only": True,
            "homogeneity_zero_obstruction_still_admissible": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "signed_commutator_cancellation_available_only" in match[
        "rejected_substitutes"
    ]
    assert "positive_cone_minorant_not_signed_cancellation" in match[
        "missing_fields"
    ]


def test_tracefree_cz_endpoint_payment_rejects_weak_endpoint_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_CZ_endpoint_pointwise_payment",
        {
            "CZ_endpoint_signed_or_weak_only": True,
            "BMO_endpoint_dual_only": True,
            "selected_packet_unconditional_L1_embedding_missing": True,
            "pressure_riesz_degree_zero_carrier_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "CZ_endpoint_signed_or_weak_only" in match["rejected_substitutes"]
    assert "selected_packet_unconditional_L1_embedding" in match[
        "missing_fields"
    ]


def test_tracefree_psd_matrix_defect_payment_rejects_preprojection_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_psd_matrix_defect_payment",
        {
            "PSD_trace_pays_preprojection_only": True,
            "projected_angular_target_after_Leray_Riesz": True,
            "Leray_Riesz_projection_L1_payment_missing": True,
            "positive_trace_measure_only": True,
            "CZ_measure_L1_variation_unpaid": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "PSD_trace_pays_preprojection_only" in match["rejected_substitutes"]
    assert "Leray_Riesz_projection_L1_payment_or_not_needed" in match[
        "missing_fields"
    ]


def test_tracefree_projected_target_preprojection_identity_rejects_missing_identity() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_projected_target_preprojection_identity",
        {
            "selected_target_still_projected_riesz_angular_moment": True,
            "preprojection_identity_missing": True,
            "moving_target_changes_equation_identity": True,
            "PSD_trace_pays_preprojection_only": True,
            "Leray_Riesz_projection_L1_payment_missing": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "preprojection_identity_missing" in match["rejected_substitutes"]
    assert "selected_C7_projected_target_is_preprojection_PSD_fiber" in match[
        "missing_fields"
    ]


def test_tracefree_projected_target_preprojection_identity_matches_full_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_projected_target_preprojection_identity",
        {
            "tracefree_variation_psd_matrix_defect_payment": True,
            "selected_C7_projected_target_is_preprojection_PSD_fiber": True,
            "selected_C7_reads_preprojection_stress": True,
            "owner_preimage_no_reuse": True,
            "projection_kernel_fixed_before_payoff": True,
            "no_Leray_Riesz_L1_payment_hidden_in_identity": True,
            "not_CF_direction_coherence_import": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert (
        match["concludes"][
            "TraceFreeVariationProjectedTargetPreprojectionIdentityReceipt"
        ]
        is True
    )
    assert (
        match["concludes"]["TraceFreeVariationPointwiseSameCarrierPaymentReceipt"]
        is True
    )


def test_tracefree_beta_square_transfer_rejects_square_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tracefree_variation_beta_square_carleson_transfer",
        {
            "tracefree_variation_same_carrier_fresh_no_reuse_carleson": True,
            "beta_square_carleson_available_only": True,
            "same_tree_beta_carleson_incidence_only": True,
            "square_budget_finite_but_linear_prefix_overflows": True,
            "diagonal_dini_tracefree_stream_still_admissible": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert (
        "square_budget_finite_but_linear_prefix_overflows"
        in match["rejected_substitutes"]
    )
    assert (
        "absolute_tracefree_prefix_dominated_by_beta_square_event_budget"
        in match["missing_fields"]
    )


def test_tracefree_dini_witness_has_finite_square_and_growing_linear_prefix() -> None:
    module = _load_tracefree_dini_witness_module()
    witness = module.build_witness([10, 100, 1000])

    assert witness.finite_square_budget is True
    assert witness.linear_prefix_exceeds_every_test_budget_seen is True
    assert witness.rows[-1].square_prefix <= witness.rows[-1].square_budget_upper_bound
    assert witness.rows[-1].linear_prefix > witness.rows[0].linear_prefix
    assert "product_L2_to_absolute_tracefree_variation" in witness.killed_routes


def test_cone_overflow_witness_separates_total_variation_from_overflow() -> None:
    module = _load_cone_overflow_witness_module()
    rows = module.build_rows()

    assert abs(rows[0].overflow_excess - rows[-1].overflow_excess) < 1e-9
    assert rows[-1].total_cone_variation > rows[0].total_cone_variation
    assert rows[-1].total_to_overflow_ratio > rows[0].total_to_overflow_ratio
    assert rows[-1].total_to_overflow_ratio > 10000


def test_riesz_projection_l1_witness_blocks_psd_trace_exchange() -> None:
    module = _load_riesz_projection_l1_witness_module()
    witness = module.build_witness(shells=8, constant=4.0)

    assert witness["source_trace_mass"] == 1.0
    assert witness["first_violation"]["shell"] == 5
    assert witness["projected_absolute_prefix_at_N"] == 8.0
    assert (
        witness["blocked_exchange_rate"]
        == "psd_defect_trace_to_projected_tracefree_payment"
    )


def test_avisc_traceless_tensor_cancellation_witness_has_positive_scalar_variance() -> None:
    module = _load_avisc_witness_module()
    witness = module.build_witness()

    assert witness["scalar_mass_positive"] is True
    assert witness["scalar_marked_variance_positive"] is True
    assert witness["local_divergence_free_strain_jets"] is True
    assert witness["traceless_tensor_cancels"] is True
    assert witness["traceless_tensor_frobenius_norm"] == 0.0


def test_pressure_cutoff_carrier_mismatch_witness_is_pressure_invisible() -> None:
    module = _load_pressure_mismatch_witness_module()
    witness = module.build_witness()

    plane_wave = witness["divergence_free_plane_wave_self_stress"]
    longitudinal = witness["longitudinal_pressure_visible_stress"]
    tangent = witness["tangential_div_div_null_stress"]
    core_sheath = witness["same_window_core_sheath_cancellation"]

    assert plane_wave["k_dot_amplitude"] == 0.0
    assert plane_wave["same_pressure_as_baseline"] is True
    assert plane_wave["divergence_free_packet_pressure_invisible"] is True
    assert longitudinal["pressure_controls_morphology_in_one_dimensional_subclass"] is True
    assert longitudinal["compatible_with_divergence_free_plane_wave_self_stress"] is False
    assert tangent["same_pressure_as_baseline"] is True
    assert tangent["changes_morphology_while_pressure_invisible"] is True
    assert core_sheath["same_final_pressure_as_baseline"] is True
    assert core_sheath["final_pressure_loses_pre_summed_carrier"] is True


def test_angular_pressure_tomography_witness_separates_frame_from_sheath_cancel() -> None:
    module = _load_angular_tomography_witness_module()
    witness = module.build_witness()

    assert witness["determinant"] == 1
    assert witness["angular_frame_spans_tracefree_tensor_morphology"] is True
    assert (
        witness["same_window_sheath_cancellation"]["final_samples_all_zero"]
        is True
    )
    assert (
        witness["same_window_sheath_cancellation"]["pre_summed_samples_positive"]
        is True
    )
    assert (
        witness["strict_angular_dominance_failure"][
            "no_positive_epsilon_possible"
        ]
        is True
    )
    assert "pressure_l2_carrier_label_only" in witness["kills"]
    assert "strict_angular_dominance_from_C7_ownership_only" in witness["kills"]


def test_presummed_angular_owner_budget_witness_separates_labels_from_bound() -> None:
    module = _load_presummed_angular_owner_witness_module()
    witness = module.build_witness(amplitude=16, owner_budget=1, C=4)

    assert witness["packet"]["same_source_owner_label"] is True
    assert witness["packet"]["bounded_owner_multiplicity_label"] is True
    assert witness["packet"]["pointwise_sample_to_owner_charge_bound"] is False
    assert witness["budget_inequality"]["violates_budget"] is True
    assert witness["budget_inequality"]["gap_factor"] == 12
    assert witness["angular_samples"]["final_samples_all_zero"] is True
    assert "owner_budget_label_only" in witness["kills"]


def test_limit_passage_gate_runs_for_limit_passage_gap() -> None:
    module = _load_module()
    gate = module.run_limit_passage_audit(
        "LIMIT_PASSAGE",
        [{
            "name": "finite_assignment_to_projected_window",
            "sequence_described": "finite owner-root atom assignments under projected windows",
            "inheritance_lemma": "direct/elementary",
            "property_inherited": "no-overlap assignment persists for the fixed finite window",
        }],
        finite_prefix_results=True,
    )

    assert gate is not None
    assert gate["passed"] is True
    assert gate["n_complete_steps"] == 1


def test_workbench_receipt_strength_audit_flags_weak_shared_partition_source() -> None:
    module = _load_module()
    context = module.load_target_context("SharedPartitionProjectedCollarInvoiceSource", None)
    fields = module.single_spend_fields_from_context(context)
    audit = module.run_receipt_strength_audit_from_fields(fields)

    assert audit is not None
    assert audit["passed"] is False
    assert "no_overlap_or_disjointness" in audit["missing_receipts"]
    assert "payoff_independence" in audit["weak_receipts"]


def test_workbench_receipt_strength_audit_accepts_numeric_joint_owner_root_receipts() -> None:
    module = _load_module()
    context = module.load_target_context("JointOwnerRootCollarTailPartitionSource", None)
    fields = module.single_spend_fields_from_context(context)
    audit = module.run_receipt_strength_audit_from_fields(fields)

    assert audit is not None
    assert audit["passed"] is True
    assert not audit["weak_receipts"]
    assert not audit["missing_receipts"]


def test_execution_contract_renders_in_markdown() -> None:
    module = _load_module()
    pack = {
        "target": "GenericEstimateCarrier",
        "field": None,
        "target_context": {
            "found": True,
            "target_file": "example.lean",
            "n_downstream_users": 0,
            "priority": None,
        },
        "gap_classification": {"gap_type": "UNKNOWN", "confidence": "low"},
        "mathlib_lemmas": [],
        "auxiliary_families": [],
        "pde_craft_ops": [{"op_id": "pec_h", "name": "Distribution / Tail Upgrade", "rationale": "tail", "gate_mechanization": None}],
        "pde_execution_contract": module.build_pde_execution_contract(
            [{"op_id": "pec_h"}],
            target_currency="radius_sum",
        ),
        "residual_normal_form": None,
        "limit_passage_gate": None,
        "pi_group_checks": [],
        "single_spend_audit": None,
        "owner_preimage_prefix_gate": None,
        "scaled_transfer_numeric_receipt_gate": None,
        "owner_geometry_core_receipt_gate": None,
        "fresh_annular_anti_laundering_gate": None,
        "fresh_annular_non_disguise_gate": None,
        "fresh_annular_innovation_gate": None,
        "section_fixed_unsigned_variation_gate": None,
        "inequality_checks": [],
        "curriculum_variants": [],
    }

    rendered = module.render_markdown(pack)

    assert "## PDE Execution Contract" in rendered
    assert "sparse_cubic_ghost" in rendered
    assert "KRZ_one_component" in rendered


def test_critical_source_square_routes_to_tail_upgrade() -> None:
    module = _load_module()
    ops = module.suggest_pde_craft_ops(
        gap_type="UNKNOWN",
        target="AnnularRenewalBudget",
        field=None,
        inequalities=[
            "finite Leray energy does not give the critical source-square "
            "or same-carrier source Carleson budget for P_N div(u tensor u)",
        ],
    )
    ids = {op["op_id"] for op in ops}
    assert "pec_h" in ids


def test_type_i_envelope_routes_to_regime_scoping() -> None:
    module = _load_module()
    ops = module.suggest_pde_craft_ops(
        gap_type="UNKNOWN",
        target="TypeIEnvelopeCriticalSourceSquareSource",
        field="amplitudeFrequencyRatioSquare",
        inequalities=[
            "the Type-I amplitude envelope M/N bounds the source square by dissipation",
        ],
    )
    ids = {op["op_id"] for op in ops}
    assert "pec_b" in ids


def test_nonadaptive_source_selection_routes_to_receipt_primitive() -> None:
    module = _load_module()
    ops = module.suggest_pde_craft_ops(
        gap_type="LIMIT_PASSAGE",
        target="C7RouteActiveTailEventBetaSquareIdentification",
        field="routeTailFixedBeforeEventPayoff",
        inequalities=[
            "nonadaptive event source selection fixed before payoff with no post hoc radius-sum tuning",
        ],
    )
    ids = {op["op_id"] for op in ops}
    assert "pec_i" in ids


def test_same_carrier_no_reuse_routes_to_packing_injection_receipt() -> None:
    module = _load_module()
    ops = module.suggest_pde_craft_ops(
        gap_type="COERCIVITY",
        target="FreshAnnularFinitePrefixMatchingCertificate fresh-capacity",
        field="same-carrier fresh-capacity no-descendant capacity reuse",
        inequalities=[
            "local radius payments inject into disjoint fresh annular capacity with bounded overlap",
        ],
    )
    ids = {op["op_id"] for op in ops}
    assert "pec_j" in ids


def test_phase_space_packet_ownership_routes_to_owner_preimage_receipt() -> None:
    module = _load_module()
    ops = module.suggest_pde_craft_ops(
        gap_type="COERCIVITY",
        target="NonadaptiveAnnularC7SourceSelection",
        field="ownedEventPrefixBudget",
        inequalities=[
            (
                "selected residual-fresh events have a pre-payoff phase-space "
                "owner atom map and a global selected-tree owner preimage "
                "bounded multiplicity event prefix budget"
            ),
        ],
    )
    ids = {op["op_id"] for op in ops}
    assert "pec_k" in ids
    pec_k = next(op for op in ops if op["op_id"] == "pec_k")
    assert pec_k["gate_mechanization"] == "src/ztare/gates/owner_preimage_prefix_gate.py"



def test_event_pay_prefix_exchange_routes_to_owner_preimage_and_cancellation_ops() -> None:
    module = _load_module()
    ops = module.suggest_pde_craft_ops(
        gap_type="LIMIT_PASSAGE",
        target="eventRadiusPayment_eq_five_frame_tracefree_angular_event_pay_or_bounded_comparison_before_payoff",
        field="route_tail_to_five_frame_currency_exchange",
        inequalities=[
            (
                "five_frame_tracefree_angular_event_pay <= C * eventRadiusPayment "
                "with same selected prefix map fixed before payoff"
            ),
        ],
    )
    ids = {op["op_id"] for op in ops}
    assert "pec_i" in ids
    assert "pec_k" in ids
    assert "pec_l" in ids


def test_owner_preimage_prefix_gate_runs_when_pec_k_selected() -> None:
    module = _load_module()
    gate = module.run_owner_preimage_prefix_audit(
        [{"op_id": "pec_k"}],
        [{
            "name": "pointwise_only",
            "owner_map": "ownerOfEvent",
            "pointwise_payment": "eventPay e <= atomCharge (ownerOfEvent e)",
            "finite_atom_budget": "prefix atomCharge <= B",
        }],
    )

    assert gate is not None
    assert gate["passed"] is True
    assert gate["n_complete_receipts"] == 0
    assert any(
        "owner_preimage_prefix_inequality" in v.get("missing_fields", [])
        for v in gate["violations"]
    )


def test_owner_preimage_prefix_gate_runs_when_receipt_supplied_without_pec_k() -> None:
    module = _load_module()
    gate = module.run_owner_preimage_prefix_audit(
        [],
        [{
            "name": "pointwise_only_without_router",
            "owner_map": "ownerOfEvent",
            "pointwise_payment": "eventPay e <= atomCharge (ownerOfEvent e)",
            "finite_atom_budget": "prefix atomCharge <= B",
        }],
    )

    assert gate is not None
    assert gate["n_complete_receipts"] == 0
    assert any(
        "owner_preimage_prefix_inequality" in v.get("missing_fields", [])
        for v in gate["violations"]
    )


def test_owner_preimage_prefix_gate_renders_receipt_violation() -> None:
    module = _load_module()
    pack = {
        "target": "NonadaptiveAnnularC7SourceSelection",
        "field": None,
        "target_context": {
            "found": True,
            "target_file": "example.lean",
            "n_downstream_users": 0,
            "priority": None,
        },
        "gap_classification": {"gap_type": "UNKNOWN", "confidence": "low"},
        "mathlib_lemmas": [],
        "auxiliary_families": [],
        "pde_craft_ops": [{"op_id": "pec_k", "name": "Phase-Space Packet Ownership Receipt", "rationale": "owner preimage", "gate_mechanization": "src/ztare/gates/owner_preimage_prefix_gate.py"}],
        "residual_normal_form": None,
        "limit_passage_gate": None,
        "pi_group_checks": [],
        "single_spend_audit": None,
        "owner_preimage_prefix_gate": module.run_owner_preimage_prefix_audit(
            [{"op_id": "pec_k"}],
            [{
                "name": "pointwise_only",
                "owner_map": "ownerOfEvent",
                "pointwise_payment": "eventPay e <= atomCharge (ownerOfEvent e)",
            }],
        ),
        "inequality_checks": [],
        "curriculum_variants": [],
    }
    rendered = module.render_markdown(pack)

    assert "## Owner-Preimage Prefix Gate" in rendered
    assert "owner_preimage_receipt_incomplete" in rendered
    assert "owner_preimage_prefix_inequality" in rendered


def test_scaled_transfer_numeric_gate_runs_for_route_tail_edge() -> None:
    module = _load_module()
    gate = module.run_scaled_transfer_numeric_audit(
        "C7RouteActiveTailNonnegativeReceipt.ofPointwiseEventNodeRadiusNonnegative",
        None,
        {"fields": []},
        [{
            "name": "prop_only_radius",
            "nodeRadiusPositiveOnSelected": "Prop",
            "prop_membership_input": "eventToBadNode lands in selected nodes",
        }],
    )

    assert gate is not None
    assert gate["passed"] is True
    assert gate["n_complete_receipts"] == 0
    assert any(
        "pointwise_numeric_statement" in v.get("missing_fields", [])
        for v in gate["violations"]
    )


def test_scaled_transfer_numeric_gate_renders_receipt_violation() -> None:
    module = _load_module()
    pack = {
        "target": "C7RouteActiveTailNonnegativeReceipt",
        "field": None,
        "target_context": {
            "found": True,
            "target_file": "example.lean",
            "n_downstream_users": 0,
            "priority": None,
        },
        "gap_classification": {"gap_type": "UNKNOWN", "confidence": "low"},
        "mathlib_lemmas": [],
        "auxiliary_families": [],
        "pde_craft_ops": [],
        "residual_normal_form": None,
        "limit_passage_gate": None,
        "pi_group_checks": [],
        "single_spend_audit": None,
        "owner_preimage_prefix_gate": None,
        "scaled_transfer_numeric_receipt_gate":
            module.run_scaled_transfer_numeric_audit(
                "C7RouteActiveTailNonnegativeReceipt",
                None,
                {"fields": []},
                [{
                    "name": "prop_only_radius",
                    "nodeRadiusPositiveOnSelected": "Prop",
                }],
            ),
        "inequality_checks": [],
        "curriculum_variants": [],
    }
    rendered = module.render_markdown(pack)

    assert "## Scaled-Transfer Numeric Receipt Gate" in rendered
    assert "scaled_transfer_numeric_receipt_incomplete" in rendered
    assert "pointwise_numeric_statement" in rendered


def test_owner_geometry_core_gate_runs_for_reduced_owner_core_edge() -> None:
    module = _load_module()
    gate = module.run_owner_geometry_core_audit(
        "C7OwnerPreimageGeometryCoreReceipt",
        None,
        {"fields": []},
        [{
            "name": "completion_only",
            "productionSourceFixedBeforeOwnerMap": True,
            "pressureReserveSeparatedFromOwnerBudget": True,
        }],
    )

    assert gate is not None
    assert gate["passed"] is True
    assert gate["n_complete_receipts"] == 0
    assert any(
        "selected_prefix_preimage" in v.get("missing_fields", [])
        for v in gate["violations"]
    )


def test_owner_geometry_core_gate_runs_for_residual_after_transfer_edge() -> None:
    module = _load_module()
    gate = module.run_owner_geometry_core_audit(
        "C7OwnerGeometryResidualAfterScaledTransfer",
        None,
        {"fields": []},
        [],
    )

    assert gate is not None
    assert gate["passed"] is True
    assert any(
        v["type"] == "owner_geometry_core_receipt_missing"
        for v in gate["violations"]
    )


def test_owner_geometry_core_gate_renders_receipt_violation() -> None:
    module = _load_module()
    pack = {
        "target": "C7OwnerPreimageGeometryCoreReceipt",
        "field": None,
        "target_context": {
            "found": True,
            "target_file": "example.lean",
            "n_downstream_users": 0,
            "priority": None,
        },
        "gap_classification": {"gap_type": "UNKNOWN", "confidence": "low"},
        "mathlib_lemmas": [],
        "auxiliary_families": [],
        "pde_craft_ops": [],
        "residual_normal_form": None,
        "limit_passage_gate": None,
        "pi_group_checks": [],
        "single_spend_audit": None,
        "owner_preimage_prefix_gate": None,
        "scaled_transfer_numeric_receipt_gate": None,
        "owner_geometry_core_receipt_gate":
            module.run_owner_geometry_core_audit(
                "C7OwnerPreimageGeometryCoreReceipt",
                None,
                {"fields": []},
                [{
                    "name": "completion_only",
                    "productionSourceFixedBeforeOwnerMap": True,
                }],
            ),
        "inequality_checks": [],
        "curriculum_variants": [],
    }
    rendered = module.render_markdown(pack)

    assert "## Owner-Geometry Core Receipt Gate" in rendered
    assert "owner_geometry_core_receipt_incomplete" in rendered
    assert "selected_prefix_preimage" in rendered


def test_fresh_annular_anti_laundering_gate_runs_for_bridge_edge() -> None:
    module = _load_module()
    gate = module.run_fresh_annular_anti_laundering_audit(
        "C7OwnerGeometryResidualBridgeFromFreshAnnularChargeSeparatedSource."
        "ofCarrierRadiusPositiveIdentityAndAntiLaundering",
        None,
        {"fields": []},
        [{
            "name": "substrate_only",
            "FreshAnnularChargeSeparatedSourceFromIndexedCarrier": True,
            "fresh_charge_prefix_budget": True,
        }],
    )

    assert gate is not None
    assert gate["passed"] is True
    assert gate["n_complete_receipts"] == 0
    assert any(
        "not_monotone_tail" in v.get("missing_fields", [])
        for v in gate["violations"]
    )


def test_fresh_annular_anti_laundering_gate_rejects_identity_laundering() -> None:
    module = _load_module()
    gate = module.run_fresh_annular_anti_laundering_audit(
        "C7FreshAnnularAntiLaunderingReceiptFromSeparatedSource",
        None,
        {"fields": []},
        [{
            "name": "identity_only",
            "not_monotone_tail": "not a monotone tail",
            "not_scalar_measure": "not a scalar measure",
            "not_uniform_enstrophy_disguise": "not enstrophy",
            "same_separated_source": "same source",
            "C7IdentityOwnerTransferProvenance": True,
            "consumed_by": (
                "C7OwnerGeometryResidualBridgeFromFreshAnnularChargeSeparatedSource."
                "ofCarrierRadiusPositiveIdentityAndAntiLaundering"
            ),
        }],
    )

    assert gate is not None
    assert any(
        v["type"] == "fresh_annular_anti_laundering_receipt_incomplete"
        and "source_selection_not_declaration_only" in v["missing_fields"]
        for v in gate["violations"]
    )


def test_fresh_annular_anti_laundering_gate_accepts_complete_receipt() -> None:
    module = _load_module()
    gate = module.run_fresh_annular_anti_laundering_audit(
        "C7FreshAnnularAntiLaunderingReceiptFromSeparatedSource",
        None,
        {"fields": []},
        [{
            "name": "same_source_non_disguise",
            "not_monotone_tail": "non-monotone annular source witness",
            "not_scalar_measure": "not reducible to scalar measure",
            "not_uniform_enstrophy_disguise": "no uniform enstrophy input",
            "source_selection_not_declaration_only": "constructive selector",
            "same_separated_source": "same separated source id",
            "consumed_by": (
                "C7OwnerGeometryResidualBridgeFromFreshAnnularChargeSeparatedSource."
                "ofCarrierRadiusPositiveIdentityAndAntiLaundering"
            ),
        }],
    )

    assert gate is not None
    assert gate["n_complete_receipts"] == 1
    assert gate["violations"] == []


def test_fresh_annular_anti_laundering_gate_accepts_same_tree_invoice_consumer() -> None:
    module = _load_module()
    gate = module.run_fresh_annular_anti_laundering_audit(
        "C7OwnerGeometryResidualBridgeFromFreshAnnularChargeSeparatedSource."
        "ofCarrierRadiusPositiveIdentitySameTreeInvoiceAndAntiLaundering",
        None,
        {"fields": []},
        [{
            "name": "same_tree_invoice_same_source_non_disguise",
            "not_monotone_tail": "non-monotone annular source witness",
            "not_scalar_measure": "not reducible to scalar measure",
            "not_uniform_enstrophy_disguise": "no uniform enstrophy input",
            "source_selection_not_declaration_only": "constructive selector",
            "same_separated_source": "same separated source id",
            "consumed_by": (
                "C7OwnerGeometryResidualBridgeFromFreshAnnularChargeSeparatedSource."
                "ofCarrierRadiusPositiveIdentitySameTreeInvoiceAndAntiLaundering"
            ),
        }],
    )

    assert gate is not None
    assert gate["n_complete_receipts"] == 1
    assert gate["violations"] == []


def test_fresh_annular_non_disguise_gate_rejects_scalar_tail_confuser() -> None:
    module = _load_module()
    gate = module.run_fresh_annular_non_disguise_audit(
        "C7FreshAnnularNonDisguiseReceiptFromSeparatedSource",
        None,
        {"fields": []},
        [{
            "name": "scalar_tail_only",
            "tail_bound": "monotone tail estimate",
            "scalar_measure": "finite scalar measure",
            "same_separated_source": "same source",
            "consumed_by": (
                "C7FreshAnnularAntiLaunderingReceiptFromSeparatedSource."
                "ofNonDisguiseAndSourceNondeclaration"
            ),
        }],
    )

    assert gate is not None
    assert gate["n_complete_receipts"] == 0
    assert any(
        "not_monotone_tail" in v.get("missing_fields", [])
        for v in gate["violations"]
    )


def test_fresh_annular_non_disguise_gate_rejects_anisotropy_proxy_laundering() -> None:
    module = _load_module()
    gate = module.run_fresh_annular_non_disguise_audit(
        "C7FreshAnnularNonDisguiseReceiptFromSeparatedSource",
        None,
        {"fields": []},
        [{
            "name": "old_Avisc_proxy",
            "anisotropic_non_scalar_proxy": "localized A_visc surplus proxy",
            "localized_Avisc_surplus": "strict subcritical CV candidate",
            "level_set_gain": "LocalizedViscousAlignmentSurplusLevelSetGain",
            "not_monotone_tail": "separate CV level-set route is non-tail",
            "not_scalar_measure": "borrowed from the old CV proxy",
            "not_uniform_enstrophy_disguise":
                "proxy is not a uniform enstrophy budget",
            "same_separated_source": "asserted by label only",
            "consumed_by": (
                "C7FreshAnnularAntiLaunderingReceiptFromSeparatedSource."
                "ofNonDisguiseAndSourceNondeclaration"
            ),
        }],
    )

    assert gate is not None
    assert gate["n_complete_receipts"] == 0
    assert any(
        v["type"] == "anisotropy_proxy_laundering"
        for v in gate["violations"]
    )
    assert any(
        "total_fresh_annular_carrier_morphology_proof"
        in v.get("unless_present_missing", [])
        for v in gate["violations"]
    )


def test_fresh_annular_non_disguise_gate_rejects_transfer_label_laundering() -> None:
    module = _load_module()
    gate = module.run_fresh_annular_non_disguise_audit(
        "C7FreshAnnularSameSourceMorphologyTransferReceipt",
        None,
        {"fields": []},
        [{
            "name": "old_observable_label_transfer",
            "old_observable_bound_on_this_separated_source":
                "localized A_visc proxy relabelled to source",
            "observable_carrier_is_separated_source": "asserted by label",
            "no_proxy_carrier_substitution": "asserted by label",
            "not_monotone_tail": "borrowed from old observable",
            "not_scalar_measure": "borrowed from old observable",
            "not_uniform_enstrophy_disguise": "borrowed from old observable",
            "same_separated_source": "same source by name",
            "consumed_by": (
                "C7FreshAnnularNonDisguiseReceiptFromSeparatedSource."
                "ofSameSourceMorphologyTransfer"
            ),
        }],
    )

    assert gate is not None
    assert gate["n_complete_receipts"] == 0
    assert any(
        v["type"] == "same_source_morphology_transfer_label_laundering"
        for v in gate["violations"]
    )


def test_fresh_annular_non_disguise_gate_accepts_morphology_receipt() -> None:
    module = _load_module()
    gate = module.run_fresh_annular_non_disguise_audit(
        "C7FreshAnnularNonDisguiseReceiptFromSeparatedSource",
        None,
        {"fields": []},
        [{
            "name": "same_source_morphology",
            "not_monotone_tail": "annular packet is not a monotone tail",
            "not_scalar_measure": "same-source vector/tent structure",
            "not_uniform_enstrophy_disguise": "critical source-square witness",
            "same_separated_source": "same separated source id",
            "consumed_by": (
                "C7FreshAnnularAntiLaunderingReceiptFromSeparatedSource."
                "ofNonDisguiseAndSourceNondeclaration"
            ),
        }],
    )

    assert gate is not None
    assert gate["n_complete_receipts"] == 1
    assert gate["violations"] == []


def test_fresh_annular_non_disguise_gate_accepts_same_source_transfer_receipt() -> None:
    module = _load_module()
    gate = module.run_fresh_annular_non_disguise_audit(
        "C7FreshAnnularSameSourceMorphologyTransferReceipt",
        None,
        {"fields": []},
        [{
            "name": "same_source_observable_morphology_transfer",
            "old_observable_bound_on_this_separated_source":
                "observable inequality proved on the invoice-fiber source",
            "observable_carrier_is_separated_source":
                "carrier identity proof object",
            "no_proxy_carrier_substitution":
                "no replay/CV/De Giorgi carrier substitution",
            "total_fresh_annular_carrier_morphology_proof":
                "total carrier morphology proof object",
            "not_monotone_tail": "annular packet is not a monotone tail",
            "not_scalar_measure": "same-source vector/tent structure",
            "not_uniform_enstrophy_disguise": "critical source-square witness",
            "same_separated_source": "same separated source id",
            "consumed_by": (
                "C7FreshAnnularNonDisguiseReceiptFromSeparatedSource."
                "ofSameSourceMorphologyTransfer"
            ),
        }],
    )

    assert gate is not None
    assert gate["n_complete_receipts"] == 1
    assert gate["violations"] == []


def test_fresh_annular_innovation_gate_rejects_prefix_budget_laundering() -> None:
    module = _load_module()
    gate = module.run_fresh_annular_innovation_audit(
        "FreshAnnularInnovationAntiLaunderingReceipt",
        None,
        {"fields": []},
        [{
            "name": "prefix_budget_only",
            "fresh_charge_prefix_budget": "geometric prefix budget",
            "FreshAnnularChargeSeparatedSourceFromIndexedCarrier": True,
            "invoice_filtration": "invoice fixed before payoff",
            "coarse_predictable_part": "monotone scalar envelope",
            "innovation_mass_lower_bound": "selected mass lower bound",
            "same_source_binding": "same separated source",
            "nondeclaration_binding": "nonadaptive selector",
            "consumed_by": (
                "C7FreshAnnularAntiLaunderingReceiptFromSeparatedSource"
            ),
        }],
    )

    assert gate is not None
    assert gate["n_complete_receipts"] == 0
    assert any(
        v["type"] == "fresh_annular_innovation_receipt_incomplete"
        and "innovation_part" in v["missing_fields"]
        for v in gate["violations"]
    )


def test_fresh_annular_innovation_gate_accepts_complete_receipt() -> None:
    module = _load_module()
    gate = module.run_fresh_annular_innovation_audit(
        "FreshAnnularInnovationAntiLaunderingReceipt",
        None,
        {"fields": []},
        [{
            "name": "same_source_innovation",
            "invoice_filtration": "invoice sigma algebra fixed before payoff",
            "coarse_predictable_part": "monotone scalar enstrophy envelope",
            "innovation_part": "orthogonal residual fresh-annular source",
            "innovation_mass_lower_bound": "positive selected-event mass",
            "same_source_binding": "same separated source id",
            "nondeclaration_binding": "source selected before radius payoff",
            "non_disguise_morphology_consequence":
                "constructs the non-tail/non-scalar/non-enstrophy fields",
            "source_nondeclaration_timing_consequence":
                "constructs sourceSelectionNotDeclarationOnly proof",
            "consumed_by": (
                "C7OwnerGeometryResidualBridgeFromFreshAnnularChargeSeparatedSource"
            ),
        }],
    )

    assert gate is not None
    assert gate["n_complete_receipts"] == 1
    assert gate["violations"] == []


def test_fresh_annular_innovation_gate_rejects_label_only_consequences() -> None:
    module = _load_module()
    gate = module.run_fresh_annular_innovation_audit(
        "FreshAnnularInnovationAntiLaunderingReceipt",
        None,
        {"fields": []},
        [{
            "name": "decorated_innovation_label",
            "invoice_filtration": "invoice sigma algebra fixed before payoff",
            "coarse_predictable_part": "monotone scalar enstrophy envelope",
            "innovation_part": "orthogonal residual fresh-annular source",
            "innovation_mass_lower_bound": "positive selected-event mass",
            "same_source_binding": "same separated source id",
            "nondeclaration_binding": "source selected before radius payoff",
            "consumed_by": (
                "C7OwnerGeometryResidualBridgeFromFreshAnnularChargeSeparatedSource"
            ),
        }],
    )

    assert gate is not None
    assert gate["n_complete_receipts"] == 0
    assert any(
        v["type"] == "fresh_annular_innovation_receipt_incomplete"
        and "non_disguise_morphology_consequence" in v["missing_fields"]
        and "source_nondeclaration_timing_consequence" in v["missing_fields"]
        for v in gate["violations"]
    )


def test_section_fixed_unsigned_variation_gate_rejects_scalar_laundering() -> None:
    module = _load_module()
    gate = module.run_section_fixed_unsigned_variation_audit(
        "DuhamelSectionFixedUnsignedCrownMeasureReceipt",
        None,
        {"fields": []},
        [{
            "name": "scalar_only",
            "lower_envelope_uses_section": "same section identity",
            "parent_crown_fixed_by_section": "parent crown labels fixed",
            "unshadowed_crown_fixed_by_section": "unshadowed labels fixed",
            "child_shadow_crown_fixed_by_section": "child labels fixed",
            "variation_measure_fixed_before_payoff": "before payoff",
            "positive_variation_before_route_budget": "before route budget",
            "no_parent_invoice_positive_part_selection": "not invoice",
            "child_shadow_not_from_parent_deficit": "not parent deficit",
            "unshadowed_mass_pays_production": "production channel",
            "child_shadow_mass_pays_inherited_reserve": "inherited reserve",
            "same_event_stream_binding": "same event stream",
            "ResidualFreshSameLedgerDuhamelLowerEnvelopeSource": True,
            "quadratic_reserve": True,
            "consumed_by": "DuhamelSectionFixedUnsignedCrownMeasureReceipt",
        }],
    )

    assert gate is not None
    assert gate["n_complete_receipts"] == 0
    assert any(
        v["type"] == "section_fixed_unsigned_variation_receipt_incomplete"
        and "localized_unsigned_variation_measure" in v["missing_fields"]
        for v in gate["violations"]
    )


def test_section_fixed_unsigned_variation_gate_accepts_complete_receipt() -> None:
    module = _load_module()
    gate = module.run_section_fixed_unsigned_variation_audit(
        "UnsignedLocalizedCrownSourceFromDuhamelSection",
        "crownMeasureSplit",
        {"fields": []},
        [{
            "name": "section_fixed_unsigned_measure",
            "lower_envelope_uses_section": "hLower.sectionIdentity = hSection",
            "parent_crown_fixed_by_section": "parent crown from section",
            "unshadowed_crown_fixed_by_section": "unshadowed crown from section",
            "child_shadow_crown_fixed_by_section": "child crown from section",
            "localized_unsigned_variation_measure":
                "positive variation measure on fixed crowns",
            "variation_measure_fixed_before_payoff": "fixed before payoff",
            "positive_variation_before_route_budget": "before route budget",
            "no_parent_invoice_positive_part_selection":
                "not selected from parent invoice",
            "child_shadow_not_from_parent_deficit":
                "not selected from parent deficit",
            "unshadowed_mass_pays_production": "heat lower bound to production",
            "child_shadow_mass_pays_inherited_reserve":
                "heat lower bound to inherited reserve",
            "same_event_stream_binding": "fresh packet event stream",
            "not_determinacy_shortcut":
                "constructs measure, does not assert determinacy",
            "consumed_by": "UnsignedLocalizedCrownSourceFromDuhamelSection",
        }],
    )

    assert gate is not None
    assert gate["n_complete_receipts"] == 1
    assert gate["violations"] == []


def test_fresh_annular_anti_laundering_gate_renders_receipt_violation() -> None:
    module = _load_module()
    pack = {
        "target": "C7FreshAnnularAntiLaunderingReceiptFromSeparatedSource",
        "field": None,
        "target_context": {
            "found": True,
            "target_file": "example.lean",
            "n_downstream_users": 0,
            "priority": None,
        },
        "gap_classification": {"gap_type": "UNKNOWN", "confidence": "low"},
        "mathlib_lemmas": [],
        "auxiliary_families": [],
        "pde_craft_ops": [],
        "residual_normal_form": None,
        "limit_passage_gate": None,
        "pi_group_checks": [],
        "single_spend_audit": None,
        "owner_preimage_prefix_gate": None,
        "scaled_transfer_numeric_receipt_gate": None,
        "owner_geometry_core_receipt_gate": None,
        "fresh_annular_anti_laundering_gate":
            module.run_fresh_annular_anti_laundering_audit(
                "C7FreshAnnularAntiLaunderingReceiptFromSeparatedSource",
                None,
                {"fields": []},
                [{
                    "name": "substrate_only",
                    "FreshAnnularChargeSeparatedSourceFromIndexedCarrier": True,
                }],
            ),
        "inequality_checks": [],
        "curriculum_variants": [],
    }
    rendered = module.render_markdown(pack)

    assert "## Fresh-Annular Anti-Laundering Gate" in rendered
    assert "fresh_annular_anti_laundering_receipt_incomplete" in rendered
    assert "not_monotone_tail" in rendered


def test_factor_reuse_routes_to_phase_space_packet_ownership_receipt() -> None:
    module = _load_module()
    ops = module.suggest_pde_craft_ops(
        gap_type="UNKNOWN",
        target="LowHighCatalystRebillingPacket",
        field=None,
        inequalities=[
            (
                "low-high catalyst factor reuse is not full output-scale "
                "bilinear packet ownership"
            ),
        ],
    )
    ids = {op["op_id"] for op in ops}
    assert "pec_k" in ids


def test_null_form_language_routes_to_symbol_cancellation_audit() -> None:
    module = _load_module()
    ops = module.suggest_pde_craft_ops(
        gap_type="UNKNOWN",
        target="HighHighSourceSquare",
        field=None,
        inequalities=[
            (
                "energy skew-symmetry and Leray projection cancellation must "
                "supply a signed-to-positive null-form estimate for the "
                "positive source square"
            ),
        ],
    )
    ids = {op["op_id"] for op in ops}
    assert "pec_l" in ids


def test_positive_variation_language_routes_to_symbol_cancellation_audit() -> None:
    module = _load_module()
    ops = module.suggest_pde_craft_ops(
        gap_type="COERCIVITY",
        target="FixedCutoffLocalEnergySignedMeasureIdentitySource",
        field="positiveVariationDomination",
        inequalities=[
            (
                "signed identity positive variation should pay a "
                "section-fixed unsigned Duhamel crown source"
            ),
        ],
    )
    ids = {op["op_id"] for op in ops}
    assert "pec_l" in ids


def test_live_context_fields_route_exact_target_to_receipt_primitives() -> None:
    module = _load_module()
    context = {
        "fields": [
            {
                "name": "freshCapacitySelectionFixedBeforeMatching_proof",
                "type": "fresh capacity selected before matching",
            },
            {
                "name": "noSameCapacityDescendantRebilling_proof",
                "type": "no same capacity descendant rebilling",
            },
            {
                "name": "ownedEventPrefixBudget",
                "type": "global selected-tree phase-space owner preimage budget",
            },
        ]
    }
    ops = module.suggest_pde_craft_ops(
        gap_type="UNKNOWN",
        target="ExactLeanDeclarationName",
        field=None,
        inequalities=[],
        context=context,
    )
    ids = {op["op_id"] for op in ops}
    assert "pec_i" in ids
    assert "pec_j" in ids
    assert "pec_k" in ids


def test_live_lean_fallback_finds_modified_noncomputable_def() -> None:
    module = _load_module()
    live = module._find_live_lean_decl(
        "Route1FiniteTailAmortizedStrictness.ofC7PackingAndSameCarrierTailControl"
    )
    assert live is not None
    assert live["kind"] == "def"
    assert live["source"] == "live_lean_fallback"


def test_live_context_doc_routes_exact_target_to_receipt_primitives() -> None:
    module = _load_module()
    ops = module.suggest_pde_craft_ops(
        gap_type="UNKNOWN",
        target="ExactLeanDeclarationName",
        field=None,
        inequalities=[],
        context={
            "doc": (
                "Nonadaptive source completion with same-carrier no-reuse "
                "and no same capacity descendant rebilling."
            ),
            "fields": [],
        },
    )
    ids = {op["op_id"] for op in ops}
    assert "pec_i" in ids
    assert "pec_j" in ids


def test_unparsed_inequality_keeps_original_candidate_in_report() -> None:
    module = _load_module()
    pack = {
        "target": "GenericEstimateCarrier",
        "field": None,
        "target_context": {
            "found": True,
            "target_file": "example.lean",
            "n_downstream_users": 0,
            "priority": None,
        },
        "gap_classification": {"gap_type": "UNKNOWN", "confidence": "low"},
        "mathlib_lemmas": [],
        "auxiliary_families": [],
        "pde_craft_ops": [],
        "residual_normal_form": None,
        "limit_passage_gate": None,
        "pi_group_checks": [],
        "single_spend_audit": None,
        "inequality_checks": [
            {
                "passed": False,
                "candidate_inequality": "average control implies tail control",
                "reason": "could not parse inequality structure",
                "violations": [],
            }
        ],
        "curriculum_variants": [],
    }
    rendered = module.render_markdown(pack)
    assert "`average control implies tail control`" in rendered
    assert "could not parse inequality structure" in rendered


def test_residual_normal_form_renders_packet_hit() -> None:
    module = _load_module()
    result = module.run_residual_normal_form(
        Path("projects/ns_millennium_hunt/config/residual_normal_forms.json"),
        "unshadowed positive Duhamel source",
        None,
        [
            "signed average plus quadratic reserve should imply q > 5/2 weak-Lq tail",
        ],
    )
    assert result is not None
    assert result["classification"] == "COUNTERMODEL_HIT"
    assert result["packet_hits"]

    pack = {
        "target": "unshadowed positive Duhamel source",
        "field": None,
        "target_context": {
            "found": True,
            "target_file": "example.lean",
            "n_downstream_users": 0,
            "priority": None,
        },
        "gap_classification": {"gap_type": "UNKNOWN", "confidence": "low"},
        "mathlib_lemmas": [],
        "auxiliary_families": [],
        "pde_craft_ops": [],
        "residual_normal_form": result,
        "pi_group_checks": [],
        "single_spend_audit": None,
        "inequality_checks": [],
        "curriculum_variants": [],
    }
    rendered = module.render_markdown(pack)
    assert "## Residual Normal Form" in rendered
    assert "COUNTERMODEL_HIT" in rendered
    assert "Two-packet positive spike" in rendered


def test_residual_normal_form_hits_parent_child_shadow_swap() -> None:
    module = _load_module()
    result = module.run_residual_normal_form(
        Path("projects/ns_millennium_hunt/config/residual_normal_forms.json"),
        "same Duhamel section unshadowed positive Duhamel source",
        None,
        [
            "same signed event ledger and same quadratic reserve should determine the parent crown positive production tail",
        ],
    )
    assert result is not None
    assert result["classification"] == "COUNTERMODEL_HIT"
    assert any(
        hit["packet_id"] == "same_event_reserve_parent_child_shadow"
        for hit in result["packet_hits"]
    )


def test_residual_normal_form_routes_c7_angular_sheath_gap() -> None:
    module = _load_module()
    result = module.run_residual_normal_form(
        Path("projects/ns_millennium_hunt/config/residual_normal_forms.json"),
        "C7SameSourceAngularNoSheathGap",
        "sameWindowSheathCancellationStillAdmissibleOnAngularFrame",
        [
            (
                "pre_summed_trace_free_morphology <= C * "
                "final_angular_sample_norm on selected_same_source_C7_frame"
            ),
        ],
    )
    assert result is not None
    assert result["classification"] == "COUNTERMODEL_HIT"
    assert result["best_match"]["canonical_name"] == "AngularPressureSheathCancellation"
    assert result["best_match"]["score"] == 1.0
    assert any(
        hit["packet_id"] == "angular_tracefree_same_window_sheath"
        for hit in result["packet_hits"]
    )
    assert any(
        hit["rule_id"] == "pre_summed_tracefree_vs_final_angular"
        for hit in result["currency_mismatches"]
    )



def test_residual_normal_form_routes_selected_c7_no_sheath_field_names() -> None:
    module = _load_module()
    result = module.run_residual_normal_form(
        Path("projects/ns_millennium_hunt/config/residual_normal_forms.json"),
        "SelectedC7AngularFrameNoSheathCancellationReceipt",
        "oppositeTraceFreeSheathExcludedBeforePayoff",
        [
            (
                "opposite_sheath_cone_mass <= (1 - epsilon) * "
                "core_positive_cone_mass on selected same-source C7 angular frame; "
                "diagonal packet has equal core and opposite sheath"
            ),
        ],
    )
    assert result is not None
    assert result["classification"] == "COUNTERMODEL_HIT"
    assert result["best_match"]["canonical_name"] == "AngularPressureSheathCancellation"
    assert any(
        hit["packet_id"] == "angular_tracefree_same_window_sheath"
        for hit in result["packet_hits"]
    )


def test_residual_normal_form_routes_selected_c7_cone_noescape_gap() -> None:
    module = _load_module()
    result = module.run_residual_normal_form(
        Path("projects/ns_millennium_hunt/config/residual_normal_forms.json"),
        "SelectedC7FixedWindowConeMassRigiditySource",
        "sameWindowSheathCancellationForbiddenOnSelectedC7Class",
        [
            (
                "sheath_opposite_cone_mass <= (1 - epsilon) * "
                "core_positive_cone_mass for selected_same_source_C7_frame; "
                "overflow creates forbidden same_window_sheath_cancellation "
                "before payoff"
            ),
        ],
    )
    assert result is not None
    assert result["classification"] == "COUNTERMODEL_HIT"
    assert result["best_match"]["canonical_name"] == "AngularPressureSheathCancellation"
    assert any(
        hit["packet_id"] == "angular_tracefree_same_window_sheath"
        for hit in result["packet_hits"]
    )


def test_residual_normal_form_routes_selected_c7_oriented_cone_asymmetry_gate() -> None:
    module = _load_module()
    result = module.run_residual_normal_form(
        Path("projects/ns_millennium_hunt/config/residual_normal_forms.json"),
        "selected_c7_oriented_cone_asymmetry_gate",
        "tracefree_orientation_flip_not_distinguished",
        [
            (
                "selected C7 fixed window data must distinguish tracefree "
                "orientation flip A -> -A before payoff; diagonal sign blind "
                "core sheath equal mass packet keeps same window sheath "
                "cancellation admissible unless a pre-summed owner carrier pays "
                "opposite trace-free sheath exclusion"
            ),
        ],
    )
    assert result is not None
    assert result["classification"] == "COUNTERMODEL_HIT"
    assert result["best_match"]["canonical_name"] == "AngularPressureSheathCancellation"
    assert any(
        hit["packet_id"] == "angular_tracefree_same_window_sheath"
        for hit in result["packet_hits"]
    )



def test_residual_normal_form_routes_five_frame_route_tail_exchange_gap() -> None:
    module = _load_module()
    result = module.run_residual_normal_form(
        Path("projects/ns_millennium_hunt/config/residual_normal_forms.json"),
        "eventRadiusPayment_eq_five_frame_tracefree_angular_event_pay_or_bounded_comparison_before_payoff",
        "route_tail_to_five_frame_currency_exchange",
        [
            (
                "routeActiveTail / eventRadiusPayment is spent on five-frame "
                "trace-free angular event pay without a currency exchange; "
                "need bounded comparison on the same selected prefix map before payoff"
            ),
        ],
    )
    assert result is not None
    assert result["classification"] == "COUNTERMODEL_HIT"
    assert result["best_match"]["canonical_name"] == "FiveFrameRouteTailCurrencyMismatch"
    assert any(
        hit["packet_id"] == "route_tail_finite_five_frame_harmonic"
        for hit in result["packet_hits"]
    )
    assert any(
        hit["rule_id"] == "five_frame_event_pay_vs_route_tail"
        for hit in result["currency_mismatches"]
    )


def test_residual_normal_form_uses_live_context_fields() -> None:
    module = _load_module()
    result = module.run_residual_normal_form(
        Path("projects/ns_millennium_hunt/config/residual_normal_forms.json"),
        "ExactLeanDeclarationName",
        None,
        [],
        context={
            "fields": [
                {
                    "name": "noSameCapacityDescendantRebilling_proof",
                    "type": "same-carrier fresh capacity no-reuse injection",
                }
            ]
        },
    )
    assert result is not None
    assert result["classification"] in {"STRICTLY_NARROWER", "ALIAS"}


def test_five_frame_route_tail_exchange_requires_same_prefix_comparison() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "five_frame_route_tail_exchange",
        {
            "nonadaptive_annular_C7_source_selection": True,
            "five_frame_samples_same_annular_output_packet": True,
            "routeActiveTail_budget_spent_on_five_frame_event_pay_without_exchange": True,
            "five_frame_event_pay_bounded_comparison_missing": True,
            "harmonic_five_frame_event_pay_with_summable_route_tail": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "eventRadiusPayment_eq_or_controls_fiveFrameTracefreeAngularPay" in match["missing_fields"]
    assert "same_selected_prefix_map_fixed_before_payoff" in match["missing_fields"]
    assert (
        "harmonic_five_frame_event_pay_with_summable_route_tail"
        in match["rejected_substitutes"]
    )


def test_five_frame_route_tail_exchange_matches_full_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "five_frame_route_tail_exchange",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["FiveFrameRouteTailExchangeTheorem"] is True


def test_annular_bandlimited_riesz_l1_psd_trace_payment_rejects_raw_target() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "annular_bandlimited_riesz_l1_psd_trace_payment",
        {
            "raw_unlocalized_Riesz_measure_target": True,
            "annular_output_packet_identity_missing": True,
            "annular_event_stream_not_locked_to_C7_route_stream": True,
            "annular_bandlimit_chosen_after_payoff": True,
            "cutoff_commutator_tail_payment_missing": True,
            "one_PSD_trace_packet_reused_by_many_selected_invoices": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "annular_output_packet_identity_missing" in match["rejected_substitutes"]
    assert "annular_event_stream_not_locked_to_C7_route_stream" in match["rejected_substitutes"]
    assert "selected_target_uses_annular_bandlimited_output_packet" in match["missing_fields"]
    assert "annular_event_pay_eq_prior_nonadaptive_event_stream" in match["missing_fields"]


def test_annular_bandlimited_riesz_l1_rejects_route_tail_spent_on_five_frame_pay() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "annular_bandlimited_riesz_l1_psd_trace_payment",
        {
            "tracefree_variation_pointwise_same_carrier_payment": True,
            "selected_target_uses_annular_bandlimited_output_packet": True,
            "annular_projected_packet_identified_with_nonadaptive_event_stream": True,
            "eventRadiusPayment_not_five_frame_tracefree_angular_event_pay": True,
            "routeActiveTail_budget_spent_on_five_frame_event_pay_without_exchange": True,
            "five_frame_event_pay_bounded_comparison_missing": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert (
        "eventRadiusPayment_not_five_frame_tracefree_angular_event_pay"
        in match["rejected_substitutes"]
    )
    assert (
        "routeActiveTail_budget_spent_on_five_frame_event_pay_without_exchange"
        in match["rejected_substitutes"]
    )
    assert "annular_event_pay_eq_prior_nonadaptive_event_stream" in match["missing_fields"]


def test_annular_bandlimited_riesz_l1_psd_trace_payment_matches_full_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "annular_bandlimited_riesz_l1_psd_trace_payment",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["AnnularBandlimitedRieszL1PSDTracePaymentReceipt"] is True
    assert match["concludes"]["TraceFreeVariationPointwiseSameCarrierPaymentReceipt"] is True



def test_route1_annular_output_packet_source_rejects_downstream_receipt_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "route1_annular_output_packet_tracefree_identity_source",
        {
            "route1_projected_formula_source": True,
            "Route1AnnularOutputEventStreamIdentityReceipt": True,
            "downstream_identity_receipt_assumed_without_source_certificate": True,
            "action_target_source_supplied_by_check_menu": True,
            "rank_one_scalar_functional_used_for_five_dimensional_tensor_target": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "action_target_source_inferred_from_route1_packet_facts" in match["missing_fields"]
    assert "route1_packet_carries_full_tracefree_tensor_output_data" in match["missing_fields"]
    assert "downstream_identity_receipt_assumed_without_source_certificate" in match["rejected_substitutes"]


def test_route1_annular_output_packet_source_matches_full_source_certificate() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "route1_annular_output_packet_tracefree_identity_source",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["Route1AnnularOutputPacketTracefreeIdentitySource"] is True
    assert match["concludes"]["Route1AnnularOutputEventStreamIdentityReceipt"] is True


def test_route1_annular_output_identity_rejects_scalar_moment_confuser() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "route1_annular_output_event_stream_identity",
        {
            "route1_projected_formula_source": True,
            "route1_formula_only_provides_scalar_projected_moment": True,
            "scalar_projected_moment_used_as_total_variation": True,
            "signed_projected_moment_used_as_total_variation": True,
            "annular_output_packet_identity_missing": True,
            "harmonic_five_frame_event_pay_with_summable_route_tail": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "eventRadiusPayment_eq_projectedTracefreeAnnularOutputVariation" in match["missing_fields"]
    assert "route1_formula_only_provides_scalar_projected_moment" in match["rejected_substitutes"]
    assert "scalar_projected_moment_used_as_total_variation" in match["rejected_substitutes"]


def test_route1_annular_output_identity_matches_full_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "route1_annular_output_event_stream_identity",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["Route1AnnularOutputEventStreamIdentityReceipt"] is True
    assert match["concludes"]["FiveFrameRouteTailExchangeReceipt"] is True
    assert match["concludes"]["FiveFrameRouteTailExchangeTheorem"] is True

def test_linear_observable_coercivity_check_rejects_rank_defect(tmp_path):
    out = REPO / "tmp" / f"pde_workbench_linear_observable_{tmp_path.name}"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--target",
            "TraceFreeOutputIdentity",
            "--out-dir",
            str(out),
            "--linear-observable-coercivity-json",
            json.dumps({
                "label": "rank_one_scalar_vs_tracefree_tensor",
                "target_dimension": 5,
                "observable_rank": 1,
                "kernel_witness_present": True,
                "dimensionally_compatible": True,
            }),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "linear_observable_coercivity_checks: 1" in result.stdout
    pack_path = next(out.glob("*/pack.json"))
    pack = json.loads(pack_path.read_text())
    check = pack["linear_observable_coercivity_checks"][0]
    assert check["result"]["passed"] is False
    assert check["result"]["violations"][0]["kind"] == "observable_rank_defect"
    assert "Linear Observable Coercivity" in pack_path.with_suffix(".md").read_text()



def test_tick647_wall_scope_log_gate_rejects_bkm_label_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tick647_wall_scope_non_pure_power_log_gate",
        {
            "log_corrected_asymptotic_declared": True,
            "bkm_log_label_only": True,
            "parabolic_slaving_unchecked": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "bkm_log_label_only" in match["rejected_substitutes"]
    assert "log_correction_not_reparametrized_pure_power" in match["missing_fields"]
    assert "parabolic_slaving_receipt_absent_or_refuted" in match["missing_fields"]


def test_tick647_wall_scope_log_gate_matches_paid_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tick647_wall_scope_non_pure_power_log_gate",
        {
            "log_corrected_asymptotic_declared": True,
            "exact_norm_and_log_denominator_declared": True,
            "solution_binding_declared": True,
            "blowup_necessary_direction_declared": True,
            "log_correction_not_reparametrized_pure_power": True,
            "parabolic_slaving_receipt_absent_or_refuted": True,
            "no_bkm_log_circularity": True,
            "no_clay_equivalent_input_used": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["LogCorrectedAsymptoticScopeReceipt"] is True
    assert match["concludes"]["tick647_wall_scope_failure_not_regularity_discharge"] is True


def test_tick647_wall_scope_topology_gate_rejects_helicity_label_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tick647_wall_scope_non_degree_zero_topology_gate",
        {
            "vortex_topology_input_declared": True,
            "helicity_label_only": True,
            "lagrangian_deformation_cocycle_alias": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert "helicity_label_only" in match["rejected_substitutes"]
    assert "lagrangian_deformation_cocycle_alias" in match["rejected_substitutes"]
    assert "topology_extraction_not_local_eulerian_riesz" in match["missing_fields"]


def test_tick647_wall_scope_topology_gate_matches_paid_receipt() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )

    module = _load_module()
    match = match_theorem_applicability(
        "tick647_wall_scope_non_degree_zero_topology_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["VortexTopologyInputScopeReceipt"] is True
    assert match["concludes"]["tick647_wall_scope_failure_not_regularity_discharge"] is True


def test_tick647_wall_scope_terms_surface_action_cards() -> None:
    module = _load_module()
    ops = module.suggest_pde_craft_ops(
        gap_type="UNKNOWN",
        target="Kozono-Taniuchi log-corrected BKM tick647 wall scope",
        field="non-pure-power parabolic slaving",
        inequalities=["log denominator must not be pure power relabel"],
    )
    ids = {op["op_id"] for op in ops}
    assert "pec_b" in ids
    assert "pec_e" in ids

    ops = module.suggest_pde_craft_ops(
        gap_type="UNKNOWN",
        target="vortex topology helicity reconnection owner-preimage",
        field="topological vortex input",
        inequalities=["fixed topology before payoff"],
    )
    ids = {op["op_id"] for op in ops}
    assert "pec_i" in ids
    assert "pec_k" in ids
    assert "pec_e" in ids

def test_pde_execution_consumes_moment_ratio_surplus_gate(tmp_path: Path) -> None:
    out = REPO / "tmp" / f"moment_ratio_pack_{tmp_path.name}"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--target",
            "QuadraticRatioSizeSumSurplusCertificate",
            "--field",
            "m2OverQSizeSumSurplus",
            "--mode",
            "pde-execution",
            "--target-currency",
            "same_prefix_second_moment_cap",
            "--candidate-inequality",
            "thresholdSpaceMeasure < cheapBoundaryMeasureLowerBound + firstMomentSqOverCapLowerBoundNumerator",
            "--moment-ratio-surplus-json",
            json.dumps({
                "label": "sparse_threshold_ghost",
                "first_moment_sq": "1",
                "second_moment_cap": "100",
                "cheap_boundary_lower_bound": "9/10",
                "threshold_space_measure": "1",
            }),
            "--moment-ratio-surplus-json",
            json.dumps({
                "label": "passing_toy_ratio",
                "first_moment_sq": "1",
                "second_moment_cap": "4",
                "cheap_boundary_lower_bound": "4/5",
                "threshold_space_measure": "1",
            }),
            "--out-dir",
            str(out),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "moment_ratio_surplus_checks: 2" in result.stdout
    pack_path = next(out.glob("*/pack.json"))
    pack = json.loads(pack_path.read_text())
    checks = pack["moment_ratio_surplus_checks"]
    assert checks[0]["result"]["passed"] is False
    assert checks[0]["result"]["ratio_lower_bound"] == "1/100"
    assert checks[1]["result"]["passed"] is True
    assert "Moment Ratio Surplus" in pack_path.with_suffix(".md").read_text()




def test_pde_execution_consumes_bounded_ratio_support_gate(tmp_path: Path) -> None:
    out = REPO / "tmp" / f"bounded_ratio_support_pack_{tmp_path.name}"
    if out.exists():
        shutil.rmtree(out)
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--target",
            "BoundedBoundaryInterfaceRatioSource",
            "--field",
            "ratioUpperBoundFixedBeforePayoff",
            "--mode",
            "pde-execution",
            "--target-currency",
            "bounded_boundary_interface_ratio",
            "--candidate-inequality",
            "thresholdSpaceMeasure < companionLowerBound + meanSurplus / (ratioUpperBound - 1)",
            "--bounded-ratio-support-json",
            json.dumps({
                "label": "passing_bounded_ratio",
                "mean_surplus": "1/2",
                "ratio_upper_bound": "3",
                "companion_lower_bound": "4/5",
                "threshold_space_measure": "1",
            }),
            "--bounded-ratio-support-json",
            json.dumps({
                "label": "sparse_high_rho_kill",
                "mean_surplus": "1/2",
                "ratio_upper_bound": "101",
                "companion_lower_bound": "9/10",
                "threshold_space_measure": "1",
            }),
            "--out-dir",
            str(out),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "bounded_ratio_support_checks: 2" in result.stdout
    pack_path = next(out.glob("*/pack.json"))
    pack = json.loads(pack_path.read_text())
    checks = pack["bounded_ratio_support_checks"]
    assert checks[0]["result"]["passed"] is True
    assert checks[0]["result"]["support_lower_bound"] == "1/4"
    assert checks[1]["result"]["passed"] is False
    assert checks[1]["result"]["support_lower_bound"] == "1/200"
    assert "Bounded Ratio Support" in pack_path.with_suffix(".md").read_text()



def test_pde_execution_consumes_finite_prefix_selection_gate(tmp_path: Path) -> None:
    out = REPO / "tmp" / f"finite_prefix_selection_pack_{tmp_path.name}"
    if out.exists():
        shutil.rmtree(out)
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--target",
            "PaymentBiasedCoareaSliceSource",
            "--field",
            "finitePrefixBoundaryPaysInterfaceSelection",
            "--mode",
            "pde-execution",
            "--target-currency",
            "same_source_boundary_interface_prefix",
            "--candidate-inequality",
            "prefixInterfaceSum <= prefixBoundarySum",
            "--finite-prefix-selection-json",
            json.dumps({
                "label": "paid_prefix_selection",
                "boundary": ["1/4", "3/4"],
                "interface": ["1/2", "1/2"],
                "same_source_family": True,
                "prefix_fixed_before_payoff": True,
                "boundary_interface_units_aligned": True,
                "no_post_payoff_selection": True,
                "interface_floor": "1/2",
            }),
            "--finite-prefix-selection-json",
            json.dumps({
                "label": "post_payoff_bias_confuser",
                "boundary": ["1/4", "3/4"],
                "interface": ["1/2", "1/2"],
                "same_source_family": True,
                "prefix_fixed_before_payoff": False,
                "boundary_interface_units_aligned": True,
                "no_post_payoff_selection": False,
                "interface_floor": "1/2",
            }),
            "--out-dir",
            str(out),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "finite_prefix_selection_checks: 2" in result.stdout
    pack_path = next(out.glob("*/pack.json"))
    pack = json.loads(pack_path.read_text())
    checks = pack["finite_prefix_selection_checks"]
    assert checks[0]["result"]["passed"] is True
    assert checks[0]["result"]["witness_indices"] == [1]
    assert checks[0]["result"]["payment_floor_witness_indices"] == [1]
    assert checks[1]["result"]["passed"] is False
    assert "no_post_payoff_selection" in checks[1]["result"]["missing_receipts"]
    assert "Finite Prefix Selection" in pack_path.with_suffix(".md").read_text()



def test_pde_execution_consumes_event_family_binding_gate(tmp_path: Path) -> None:
    out = REPO / "tmp" / f"event_family_binding_pack_{tmp_path.name}"
    if out.exists():
        shutil.rmtree(out)
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--target",
            "SuitableDefectBackedHighInterfaceMeasureSplitCore",
            "--field",
            "domination_from_suitableDefect",
            "--mode",
            "pde-execution",
            "--target-currency",
            "event_family_binding",
            "--candidate-inequality",
            "muA_H <= muT_H + muQP_H + muC_H + muI_H",
            "--allowed-endpoint",
            "muA_H",
            "--allowed-endpoint",
            "muT_H",
            "--allowed-endpoint",
            "muQP_H",
            "--allowed-endpoint",
            "muC_H",
            "--allowed-endpoint",
            "muI_H",
            "--event-family-binding-json",
            json.dumps({
                "label": "paid_event_binding",
                "target_event_family": "H-prefix events",
                "source_event_family": "suitable LEI event tents",
                "event_identity": "H_event n = LEI_event n for n<N",
                "pre_payoff_timing": "fixed before payoff",
                "same_carrier": "same local-energy carrier",
                "same_owner_or_source": "same owner-root prefix",
                "index_map": "n maps to n",
                "index_map_total_on_prefix": "all n<N covered",
                "no_proxy_family": "not threshold proxy",
                "no_post_payoff_selection": "not deficit-selected",
            }),
            "--event-family-binding-json",
            json.dumps({
                "label": "label_only_proxy",
                "target_event_family": "H-prefix events",
                "source_event_family": "suitable LEI event tents",
                "same_label": "local high-interface events",
                "both_finite_prefix": True,
            }),
            "--out-dir",
            str(out),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "event_family_binding_checks: 2" in result.stdout
    pack_path = next(out.glob("*/pack.json"))
    pack = json.loads(pack_path.read_text())
    checks = pack["event_family_binding_checks"]
    assert checks[0]["result"]["complete"] is True
    assert checks[1]["result"]["complete"] is False
    assert "event_identity" in checks[1]["result"]["missing_fields"]
    assert "Event Family Binding" in pack_path.with_suffix(".md").read_text()


def test_pde_execution_consumes_positive_variation_bridge_gate(tmp_path: Path) -> None:
    out = REPO / "tmp" / f"positive_variation_bridge_pack_{tmp_path.name}"
    if out.exists():
        shutil.rmtree(out)
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--target",
            "LEINativeHighInterfaceEventTentPrefixSource.selected_active_floor_from_tick538_positiveVariation",
            "--field",
            "tick668_positive_variation_bridge",
            "--mode",
            "pde-execution",
            "--target-currency",
            "selected_LEI_muA_floor",
            "--candidate-inequality",
            "interfacePaymentFloor <= suitableDefectSource.muA(E_star)",
            "--allowed-endpoint",
            "interfacePaymentFloor",
            "--allowed-endpoint",
            "suitableDefectSource.muA",
            "--allowed-endpoint",
            "E_star",
            "--positive-variation-bridge-json",
            json.dumps({
                "label": "paid_alpha_to_mu",
                "signed_source": "alphaA",
                "positive_variation_source": "muA",
                "same_carrier": "same event carrier",
                "numeric_domination": "alphaA(E) <= muA(E)",
                "event_scope": "all selected events",
                "fixed_before_payoff": "pre-payoff",
                "no_post_payoff_positive_part": "not posthoc",
                "no_target_deficit_definition": "not target deficit",
            }),
            "--positive-variation-bridge-json",
            json.dumps({
                "label": "label_only",
                "signed_source": "alphaA",
                "positive_variation_source": "muA",
                "positive_variation_label": "muA label",
            }),
            "--out-dir",
            str(out),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "positive_variation_bridge_checks: 2" in result.stdout
    pack_path = next(out.glob("*/pack.json"))
    pack = json.loads(pack_path.read_text())
    checks = pack["positive_variation_bridge_checks"]
    assert checks[0]["result"]["complete"] is True
    assert checks[1]["result"]["complete"] is False
    assert "numeric_domination" in checks[1]["result"]["missing_fields"]
    assert "Positive Variation Bridge" in pack_path.with_suffix(".md").read_text()


def test_pde_execution_consumes_positive_variation_quotient_wash_gate(tmp_path: Path) -> None:
    out = REPO / "tmp" / f"positive_variation_quotient_wash_pack_{tmp_path.name}"
    if out.exists():
        shutil.rmtree(out)
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--target",
            "no_bounded_hofstadter_transaction_carrier_without_no_wash_law_gate",
            "--field",
            "tick668_positive_variation_quotient_wash",
            "--mode",
            "pde-execution",
            "--target-currency",
            "positive_transaction_variation",
            "--candidate-inequality",
            "PositiveTransactionVariation <= C * NetBudget",
            "--positive-variation-quotient-wash-json",
            json.dumps({
                "label": "complete_no_wash",
                "net_or_quotient_source_law": "same quotient source",
                "positive_variation_or_turnover_currency": "gross positive variation",
                "same_source_or_owner_binding": "same owner",
                "pre_payoff_representative_fixed": "fixed",
                "no_wash_cycle_law": "no wash",
                "no_null_cycle_growth": "no null growth",
                "bounded_positive_variation_from_net_budget": "PV <= C*B",
                "no_post_payoff_grossing": "predeclared grossing",
            }),
            "--positive-variation-quotient-wash-json",
            json.dumps({
                "label": "wash_confuser",
                "net_or_quotient_source_law": "same quotient source",
                "positive_variation_or_turnover_currency": "gross positive variation",
                "same_source_or_owner_binding": "same owner",
                "pressure_visibility_only": "visible net source",
                "core_sheath_wash_cycle": "N A plus -N A + G",
            }),
            "--out-dir",
            str(out),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "positive_variation_quotient_wash_checks: 2" in result.stdout
    pack_path = next(out.glob("*/pack.json"))
    pack = json.loads(pack_path.read_text())
    checks = pack["positive_variation_quotient_wash_checks"]
    assert checks[0]["result"]["complete"] is True
    assert checks[0]["result"]["passed"] is True
    assert checks[1]["result"]["complete"] is False
    assert "no_wash_cycle_law" in checks[1]["result"]["missing_fields"]
    assert "core_sheath_wash_cycle" in checks[1]["result"]["wash_confusers"]
    assert "Positive Variation Quotient Wash" in pack_path.with_suffix(".md").read_text()


def test_pde_execution_consumes_quotient_minimal_carrier_payment_gate(tmp_path: Path) -> None:
    out = REPO / "tmp" / f"quotient_minimal_carrier_payment_pack_{tmp_path.name}"
    if out.exists():
        shutil.rmtree(out)
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--target",
            "quotient_minimal_transaction_norm_payment_gate",
            "--field",
            "tick668_quotient_minimal_transaction_norm",
            "--mode",
            "pde-execution",
            "--target-currency",
            "minimal_positive_transaction_variation",
            "--candidate-inequality",
            "SelectedHH <= C * MPV(NetSource)",
            "--quotient-minimal-carrier-payment-json",
            json.dumps({
                "label": "complete_representative_preservation",
                "quotient_source_law": "same net source",
                "minimal_carrier_definition": "MPV = inf PV over representatives",
                "selected_production_functional": "selected high-high production",
                "pre_payoff_representative_selector": "canonical selector",
                "selector_independent_of_target_deficit": "source-only selector",
                "production_preserved_by_selector": "HH(actual) <= C HH(selector)",
                "kernel_cycles_zero_selected_production": "ker cycles have zero selected HH",
                "minimal_carrier_bounds_selected_production": "HH <= C MPV",
            }),
            "--quotient-minimal-carrier-payment-json",
            json.dumps({
                "label": "underpayment_confuser",
                "quotient_source_law": "same net source",
                "minimal_carrier_definition": "MPV = inf PV over representatives",
                "selected_production_functional": "selected high-high production",
                "net_budget_bound_only": "MPV bounded by net",
                "kernel_cycle_carries_selected_production": "S k = 0 but HH(k) > 0",
                "actual_packet_not_minimizer": "dynamics produces x, not selector",
            }),
            "--out-dir",
            str(out),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "quotient_minimal_carrier_payment_checks: 2" in result.stdout
    pack_path = next(out.glob("*/pack.json"))
    pack = json.loads(pack_path.read_text())
    checks = pack["quotient_minimal_carrier_payment_checks"]
    assert checks[0]["result"]["complete"] is True
    assert checks[0]["result"]["passed"] is True
    assert checks[1]["result"]["complete"] is False
    assert "production_preserved_by_selector" in checks[1]["result"]["missing_fields"]
    assert "kernel_cycle_carries_selected_production" in checks[1]["result"]["underpayment_confusers"]
    assert "Quotient Minimal Carrier Payment" in pack_path.with_suffix(".md").read_text()


def test_pde_execution_consumes_quadratic_quotient_descent_gate(tmp_path: Path) -> None:
    out = REPO / "tmp" / f"quadratic_quotient_descent_pack_{tmp_path.name}"
    if out.exists():
        shutil.rmtree(out)
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--target",
            "selected_source_kernel_hh_annihilation_gate",
            "--field",
            "tick668_quadratic_quotient_descent",
            "--mode",
            "pde-execution",
            "--target-currency",
            "selected_high_high_quadratic_descent",
            "--candidate-inequality",
            "Q <= C * MPV",
            "--allowed-endpoint",
            "Q",
            "--allowed-endpoint",
            "C",
            "--allowed-endpoint",
            "MPV",
            "--quadratic-quotient-descent-json",
            json.dumps({
                "label": "complete_quadratic_descent",
                "source_map_or_equivalence": "Sx = source quotient",
                "quadratic_functional": "selected HH quadratic",
                "polarized_bilinear_form": "B_Q",
                "source_kernel_definition": "k in ker S",
                "representative_selector": "R(Sx)",
                "selector_fixed_before_payoff": "fixed",
                "kernel_square_zero_or_nonpositive": "Q(k) <= 0",
                "kernel_cross_zero_or_nonpositive": "B_Q(R,k) <= 0",
                "quotient_descent_or_bound": "Q(x) <= C MPV(Sx)",
                "not_defined_by_target_deficit": "source-only",
            }),
            "--quadratic-quotient-descent-json",
            json.dumps({
                "label": "kernel_square_confuser",
                "source_map_or_equivalence": "Sx = source quotient",
                "quadratic_functional": "selected HH quadratic",
                "representative_selector": "energy minimizer",
                "energy_minimality_only": "orthogonal in E",
                "kernel_square_positive": "Q(k)>0",
            }),
            "--out-dir",
            str(out),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "quadratic_quotient_descent_checks: 2" in result.stdout
    pack_path = next(out.glob("*/pack.json"))
    pack = json.loads(pack_path.read_text())
    checks = pack["quadratic_quotient_descent_checks"]
    assert checks[0]["result"]["passed"] is True
    assert checks[1]["result"]["passed"] is False
    assert "energy_minimality_only" in checks[1]["result"]["weak_substitutes"]
    assert "kernel_square_positive" in checks[1]["result"]["quadratic_confusers"]
    assert "Quadratic Quotient Descent" in pack_path.with_suffix(".md").read_text()


def test_pde_execution_consumes_nonadaptive_source_selection_gate(tmp_path: Path) -> None:
    out = REPO / "tmp" / f"nonadaptive_source_selection_pack_{tmp_path.name}"
    if out.exists():
        shutil.rmtree(out)
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--target",
            "LEINativeSelectedTopologyFreshCostSource.selected_depth_bounded",
            "--field",
            "tick668_selected_topology_fresh_cost_source",
            "--mode",
            "pde-execution",
            "--target-currency",
            "selected_depth_bounded_from_topology_fresh_cost",
            "--candidate-inequality",
            "1 <= cost_n",
            "--allowed-endpoint",
            "cost_n",
            "--nonadaptive-source-selection-json",
            json.dumps({
                "label": "topology_extractor_fixed",
                "source_object": "vortex topology event extractor",
                "extractor_or_selection_rule": "tau(level)=event",
                "source_family": "selected LEI stream",
                "owner_or_carrier_binding": "same owner root",
                "index_or_selection_map": "total on selected prefix",
                "fixed_before_payoff": "pre-payoff",
                "selection_rule_declared_before_target": "declared before target",
                "target_not_used_to_define_source": "independent",
                "timing_receipt": "timestamp",
                "no_post_payoff_selection": "no posthoc",
            }),
            "--nonadaptive-source-selection-json",
            json.dumps({
                "label": "label_only",
                "source_label": "topology",
                "natural_candidate": "vortex lines",
            }),
            "--out-dir",
            str(out),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "nonadaptive_source_selection_checks: 2" in result.stdout
    pack_path = next(out.glob("*/pack.json"))
    pack = json.loads(pack_path.read_text())
    checks = pack["nonadaptive_source_selection_checks"]
    assert checks[0]["result"]["complete"] is True
    assert checks[1]["result"]["complete"] is False
    assert "source_object" in checks[1]["result"]["missing_fields"]
    assert "Nonadaptive Source Selection" in pack_path.with_suffix(".md").read_text()


def test_pde_execution_consumes_no_rebilling_freshness_gate(tmp_path: Path) -> None:
    out = REPO / "tmp" / f"no_rebilling_freshness_pack_{tmp_path.name}"
    if out.exists():
        shutil.rmtree(out)
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--target",
            "LEINativeSelectedTopologyFreshCostSource.selected_depth_bounded",
            "--field",
            "tick668_selected_topology_fresh_cost_source",
            "--mode",
            "pde-execution",
            "--target-currency",
            "selected_depth_bounded_from_topology_fresh_cost",
            "--candidate-inequality",
            "1 <= cost_n",
            "--allowed-endpoint",
            "cost_n",
            "--no-rebilling-freshness-json",
            json.dumps({
                "label": "selected_level_distinct_events",
                "selected_units": "selected levels",
                "payment_atoms": "topology events",
                "assignment_map": "n -> tau(n)",
                "assignment_total_on_prefix": "total on prefix",
                "distinctness_or_disjointness": "injective",
                "no_rebilling_same_atom": "no same event reused",
                "prefix_budget_bound": "sum costs <= budget",
                "fixed_before_payoff": "pre-payoff",
                "same_owner_or_source": "same owner",
                "overlap_or_multiplicity_bound": "multiplicity <= 1",
            }),
            "--no-rebilling-freshness-json",
            json.dumps({
                "label": "budget_label_only",
                "finite_budget_label": "finite budget",
                "freshness_label": "fresh",
            }),
            "--out-dir",
            str(out),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "no_rebilling_freshness_checks: 2" in result.stdout
    pack_path = next(out.glob("*/pack.json"))
    pack = json.loads(pack_path.read_text())
    checks = pack["no_rebilling_freshness_checks"]
    assert checks[0]["result"]["complete"] is True
    assert checks[1]["result"]["complete"] is False
    assert "assignment_map" in checks[1]["result"]["missing_fields"]
    assert "No-Rebilling Freshness" in pack_path.with_suffix(".md").read_text()


def test_pde_execution_consumes_same_carrier_packing_gate(tmp_path: Path) -> None:
    out = REPO / "tmp" / f"same_carrier_packing_pack_{tmp_path.name}"
    if out.exists():
        shutil.rmtree(out)
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--target",
            "LEINativeSelectedTopologyMetricTentBesicovitchNoReusePressureExceptionSource",
            "--field",
            "tick668_metric_tent_besicovitch_source",
            "--mode",
            "pde-execution",
            "--target-currency",
            "same_carrier_packing",
            "--candidate-inequality",
            "selectedDebit <= overlap * atomBudget",
            "--allowed-endpoint",
            "selectedDebit",
            "--allowed-endpoint",
            "overlap",
            "--allowed-endpoint",
            "atomBudget",
            "--same-carrier-packing-json",
            json.dumps({
                "label": "metric_tent_packing_paid",
                "source_carrier": "metric reconnection tents",
                "target_payment_family": "fresh-frequency tent atoms",
                "assignment_or_injection_map": "n maps to packed atom j(n)",
                "assignment_total_on_prefix": "all n<K assigned",
                "same_carrier_binding": "same pressure/Duhamel carrier",
                "overlap_or_multiplicity_bound": "overlap <= M",
                "finite_prefix_budget": "M * atomBudget <= freshBudget",
                "pre_payoff_timing": "packing fixed before payoff",
                "no_nested_reuse": "nested chains charged once",
                "no_rebilling_same_atom": "no atom reused beyond M",
            }),
            "--same-carrier-packing-json",
            json.dumps({
                "label": "packing_label_only",
                "source_carrier": "metric tents",
                "target_payment_family": "fresh atoms",
                "packing_label": "Besicovitch",
                "finite_budget_label": "finite budget",
            }),
            "--out-dir",
            str(out),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "same_carrier_packing_checks: 2" in result.stdout
    pack_path = next(out.glob("*/pack.json"))
    pack = json.loads(pack_path.read_text())
    checks = pack["same_carrier_packing_checks"]
    assert checks[0]["result"]["complete"] is True
    assert checks[1]["result"]["complete"] is False
    assert "assignment_or_injection_map" in checks[1]["result"]["missing_fields"]
    assert "Same-Carrier Packing" in pack_path.with_suffix(".md").read_text()



def test_pde_execution_consumes_metric_covering_selection_gate(tmp_path: Path) -> None:
    out = REPO / "tmp" / f"metric_covering_selection_pack_{tmp_path.name}"
    if out.exists():
        shutil.rmtree(out)
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--target",
            "LerayTopologyReconnectionVitaliPackingSource",
            "--field",
            "tick668_metric_covering_source",
            "--mode",
            "pde-execution",
            "--target-currency",
            "metric_covering_selection",
            "--candidate-inequality",
            "selectedDebit <= B * atomBudget + omittedError",
            "--allowed-endpoint",
            "selectedDebit",
            "--allowed-endpoint",
            "atomBudget",
            "--allowed-endpoint",
            "omittedError",
            "--metric-covering-selection-json",
            json.dumps({
                "label": "vitali_whitney_covering_paid",
                "ambient_metric_or_quasi_metric": "parabolic metric",
                "source_family": "topology reconnection tents",
                "scale_or_radius_function": "extractor radius r(Q)",
                "doubling_or_besicovitch_constant": "uniform B",
                "bounded_eccentricity_or_engulfing": "Whitney 5Q engulfing",
                "selection_rule": "maximal disjoint subfamily",
                "selection_totality_or_paid_omission": "covered or omitted children paid",
                "pre_payoff_selection_timing": "fixed before target debit payoff",
                "same_carrier_binding": "same pressure/Duhamel carrier",
                "bounded_overlap_conclusion": "overlap <= B",
                "nested_children_policy": "parent pays nested children once",
                "discarded_or_nested_error_budget": "omitted children <= viscous error",
            }),
            "--metric-covering-selection-json",
            json.dumps({
                "label": "besicovitch_label_only",
                "source_family": "topology reconnection tents",
                "besicovitch_label": "Besicovitch",
                "topology_label": "vortex topology",
            }),
            "--out-dir",
            str(out),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "metric_covering_selection_checks: 2" in result.stdout
    pack_path = next(out.glob("*/pack.json"))
    pack = json.loads(pack_path.read_text())
    checks = pack["metric_covering_selection_checks"]
    assert checks[0]["result"]["complete"] is True
    assert checks[1]["result"]["complete"] is False
    assert "ambient_metric_or_quasi_metric" in checks[1]["result"]["missing_fields"]
    assert "Metric Covering Selection" in pack_path.with_suffix(".md").read_text()


def test_heat_scale_carleson_bar_budget_source_gate_matches_and_rejects_substitutes() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "heat_scale_carleson_bar_budget_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )
    assert match["verdict"] == "MATCH"
    assert match["concludes"]["HeatScaleCarlesonBarBudgetSource"] is True

    rejected = match_theorem_applicability(
        "heat_scale_carleson_bar_budget_source_gate",
        {
            "heat_scale_persistent_topology_extractor_source_gate": True,
            "heat_square_function_paid_by_leray_dissipation": True,
            "persistence_stability_only": True,
            "heat_smoothing_only": True,
            "barcode_deaths_not_mapped_to_heat_square_function_atoms": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )
    assert rejected["verdict"] == "NO_MATCH"
    assert "persistence_stability_only" in rejected["rejected_substitutes"]
    assert "barcode_deaths_not_mapped_to_heat_square_function_atoms" in rejected["rejected_substitutes"]


def test_pde_execution_consumes_persistence_budget_exponent_gate(tmp_path: Path) -> None:
    out = REPO / "tmp" / f"persistence_budget_exponent_pack_{tmp_path.name}"
    if out.exists():
        shutil.rmtree(out)
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--target",
            "HeatScaleCarlesonBarBudgetSource",
            "--field",
            "barcodeDeathsMappedToHeatSquareFunctionAtoms",
            "--mode",
            "pde-execution",
            "--persistence-budget-exponent-json",
            json.dumps({
                "label": "l2_in_3d",
                "dimension": 3,
                "persistence_exponent": 2,
                "same_carrier_receipt": True,
            }),
            "--persistence-budget-exponent-json",
            json.dumps({
                "label": "p4_in_3d",
                "dimension": 3,
                "persistence_exponent": 4,
                "same_carrier_receipt": True,
            }),
            "--out-dir",
            str(out),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "persistence_budget_exponent_checks: 2" in result.stdout
    pack_path = next(out.glob("*/pack.json"))
    pack = json.loads(pack_path.read_text())
    checks = pack["persistence_budget_exponent_checks"]
    assert checks[0]["result"]["passed"] is False
    assert checks[0]["result"]["violations"][0]["kind"] == "subcritical_persistence_exponent"
    assert checks[1]["result"]["passed"] is True

def test_finite_prefix_boundary_interface_selection_gate_matches_paid_source_contract() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "finite_prefix_boundary_interface_selection_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["finite_prefix_selection_event_exists"] is True
    assert match["concludes"]["boundary_pays_interface_floor"] is True


def test_finite_prefix_boundary_interface_selection_gate_rejects_proxy_prefix() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "finite_prefix_boundary_interface_selection_gate",
        {
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
            "proxy_boundary_sum": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert match["rejected_substitutes"] == ["proxy_boundary_sum"]



def test_interface_weighted_boundary_paid_floor_correlation_source_gate() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "interface_weighted_boundary_paid_floor_correlation_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["weighted_floor_correlation_selector_paid"] is True

    confuser = match_theorem_applicability(
        "interface_weighted_boundary_paid_floor_correlation_source_gate",
        {
            "payment_biased_coarea_slice_source": True,
            "source_interface_law_fixed_before_payoff": True,
            "selected_event_has_positive_source_interface_weight": True,
            "selected_event_pays_interface_floor_from_source_law": True,
            "selected_event_boundary_pays_interface_from_same_law": True,
            "selected_boundary_pays_floor_not_just_prefix_sum": True,
            "zero_interface_sink_excluded_by_weight_law": True,
            "same_owner_root_for_boundary_and_interface_slice": True,
            "source_contract_alignment_check_passed": True,
            "finite_prefix_sum_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert confuser["verdict"] == "NO_MATCH"
    assert confuser["rejected_substitutes"] == ["finite_prefix_sum_only"]


def test_selected_prefix_nonnegative_channel_collapse_gate_matches_paid_source() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "selected_prefix_nonnegative_channel_collapse_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"]["SelectedPrefixNonnegativeChannelCollapseSource"] is True
    assert match["concludes"]["target_prefix_le_constant_times_channel_budget"] is True


def test_selected_prefix_nonnegative_channel_collapse_gate_rejects_signed_misclassification() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "selected_prefix_nonnegative_channel_collapse_source_gate",
        {
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
            "signed_cancellation_channel_misclassified_as_nonnegative": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert match["rejected_substitutes"] == [
        "signed_cancellation_channel_misclassified_as_nonnegative"
    ]


def test_selected_prefix_unbounded_debit_channel_confuser_gate_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "selected_prefix_unbounded_debit_channel_confuser_gate",
        {
            "channel_budget_nonnegative": True,
            "constant_nonnegative": True,
            "target_prefix_unbounded": True,
            "nonnegative_channel_label_only": True,
            "signed_or_coalescent_escape_not_supplied": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"][
        "SelectedPrefixNonnegativeChannelCollapseSource_excluded"
    ] is True


def test_selected_coalescent_current_quotient_debit_gate_matches_paid_source() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "selected_coalescent_current_support_quotient_debit_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"][
        "SelectedCoalescentCurrentSupportQuotientDebitSource"
    ] is True
    assert match["concludes"]["SelectedPrefixNonnegativeChannelCollapseSource"] is True


def test_selected_coalescent_current_quotient_debit_gate_rejects_unpaid_omission() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "selected_coalescent_current_support_quotient_debit_source_gate",
        {
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
            "omitted_child_debit_unpaid": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert match["rejected_substitutes"] == ["omitted_child_debit_unpaid"]


def test_many_endpoint_one_current_class_underpaid_confuser_gate_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "many_endpoint_one_current_class_underpaid_confuser_gate",
        {
            "coalescent_budget_nonnegative": True,
            "constant_nonnegative": True,
            "underpaid_selected_prefix": True,
            "many_selected_endpoints_share_one_current_class": True,
            "omitted_endpoint_debit_unpaid_before_quotient": True,
            "quotient_label_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"][
        "SelectedCoalescentCurrentSupportQuotientDebitSource_excluded"
    ] is True



def test_pre_positive_current_annihilation_or_paid_omitted_endpoint_debit_gate_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "pre_positive_current_annihilation_or_paid_omitted_endpoint_debit_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"][
        "PrePositiveDebitCurrentAnnihilationOrPaidOmittedEndpointDebit"
    ] is True
    assert match["concludes"]["only_two_current_exits_allowed"] is True


def test_pre_positive_current_annihilation_gate_rejects_positive_relabel() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "pre_positive_current_annihilation_or_paid_omitted_endpoint_debit_gate",
        {
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
            "positive_debit_relabel_as_annihilation": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert match["rejected_substitutes"] == [
        "positive_debit_relabel_as_annihilation"
    ]


def test_pre_positive_current_no_annihilation_underpaid_confuser_gate_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "pre_positive_current_no_annihilation_underpaid_confuser_gate",
        {
            "coalescent_budget_nonnegative": True,
            "constant_nonnegative": True,
            "underpaid_selected_prefix": True,
            "many_selected_endpoints_share_one_current_class": True,
            "omitted_endpoint_debit_unpaid_before_quotient": True,
            "pre_positive_current_annihilation_absent": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"][
        "PrePositiveDebitCurrentAnnihilationOrPaidOmittedEndpointDebit_excluded_without_annihilation"
    ] is True



def test_positive_scalar_endpoint_debit_current_annihilation_confuser_gate_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "positive_scalar_endpoint_debit_current_annihilation_confuser_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"][
        "PrePositiveDebitCurrentAnnihilationOrPaidOmittedEndpointDebit_excluded_for_positive_scalar_endpoint"
    ] is True


def test_positive_scalar_endpoint_debit_current_annihilation_confuser_gate_keeps_pre_scalar_escape() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "positive_scalar_endpoint_debit_current_annihilation_confuser_gate",
        {
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
            "genuine_pre_scalar_current_reduction_supplied": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert match["rejected_substitutes"] == [
        "genuine_pre_scalar_current_reduction_supplied"
    ]



def test_lei_native_high_interface_boundary_no_reuse_budget_source_gate_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "lei_native_high_interface_boundary_no_reuse_budget_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"][
        "LEINativeSelectedHighInterfaceBoundaryNoReuseBudgetSource"
    ] is True
    assert match["concludes"]["LEINativeSelectedIntermittentFiniteBudgetSource"] is True


def test_lei_native_high_interface_boundary_no_reuse_budget_source_gate_rejects_label_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "lei_native_high_interface_boundary_no_reuse_budget_source_gate",
        {
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
            "same_carrier_boundary_label_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert match["rejected_substitutes"] == ["same_carrier_boundary_label_only"]


def test_high_interface_boundary_no_reuse_finite_budget_confuser_gate_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "high_interface_boundary_no_reuse_finite_budget_confuser_gate",
        {
            "finite_boundary_budget_label": True,
            "same_carrier_boundary_label": True,
            "nested_selected_levels_reuse_one_boundary_atom": True,
            "boundary_charge_chosen_after_target_deficit": True,
            "uniform_selected_payment_lower_bound_missing": True,
            "no_no_rebilling_freshness_receipt": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"][
        "LEINativeSelectedHighInterfaceBoundaryNoReuseBudgetSource_excluded"
    ] is True


def test_coherent_finite_prefix_high_interface_boundary_invoice_source_gate_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "coherent_finite_prefix_high_interface_boundary_invoice_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"][
        "CoherentFinitePrefixHighInterfaceBoundaryInvoiceSource"
    ] is True
    assert match["concludes"][
        "LEINativeSelectedHighInterfaceBoundaryNoReuseBudgetSource"
    ] is True


def test_coherent_finite_prefix_high_interface_boundary_invoice_source_gate_rejects_prefixwise_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "coherent_finite_prefix_high_interface_boundary_invoice_source_gate",
        {
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
            "finite_prefix_invoice_exists_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert match["rejected_substitutes"] == ["finite_prefix_invoice_exists_only"]


def test_finite_prefix_high_interface_boundary_invoice_without_coherence_confuser_gate_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "finite_prefix_high_interface_boundary_invoice_without_coherence_confuser_gate",
        {
            "every_finite_prefix_has_some_boundary_invoice": True,
            "prefix_invoices_not_same_selected_stream": True,
            "boundary_charge_depends_on_prefix_index": True,
            "diagonal_nested_reuse_packet_still_admissible": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"][
        "CoherentFinitePrefixHighInterfaceBoundaryInvoiceSource_excluded"
    ] is True
    assert match["concludes"][
        "LEINativeSelectedHighInterfaceBoundaryNoReuseBudgetSource_excluded"
    ] is True


def test_high_interface_boundary_metric_covering_prefix_coherence_source_gate_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "high_interface_boundary_metric_covering_prefix_coherence_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"][
        "HighInterfaceBoundaryMetricCoveringPrefixCoherenceSource"
    ] is True
    assert match["concludes"][
        "CoherentFinitePrefixHighInterfaceBoundaryInvoiceSource"
    ] is True


def test_high_interface_boundary_metric_covering_prefix_coherence_source_gate_rejects_label_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "high_interface_boundary_metric_covering_prefix_coherence_source_gate",
        {
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
            "besicovitch_label_without_covering_hypotheses": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert match["rejected_substitutes"] == [
        "besicovitch_label_without_covering_hypotheses"
    ]


def test_high_interface_boundary_nonwhitney_nested_cascade_confuser_gate_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "high_interface_boundary_nonwhitney_nested_cascade_confuser_gate",
        {
            "high_interface_boundary_tent_labels_present": True,
            "dyadic_boundary_cascade_same_center": True,
            "selected_prefix_counts_nested_children": True,
            "vitali_subcover_discards_unpaid_children": True,
            "bounded_overlap_not_uniform_in_selected_prefix": True,
            "same_boundary_atom_reused_across_scales": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"][
        "HighInterfaceBoundaryMetricCoveringPrefixCoherenceSource_excluded"
    ] is True


def test_high_interface_boundary_carleson_packing_selection_source_gate_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "high_interface_boundary_carleson_packing_selection_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"][
        "HighInterfaceBoundaryCarlesonPackingSelectionSource"
    ] is True
    assert match["concludes"][
        "LEINativeSelectedHighInterfaceBoundaryNoReuseBudgetSource"
    ] is True


def test_high_interface_boundary_carleson_packing_selection_source_gate_rejects_finite_measure_only() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "high_interface_boundary_carleson_packing_selection_source_gate",
        {
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
            "finite_boundary_measure_label_only": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert match["rejected_substitutes"] == [
        "finite_boundary_measure_label_only"
    ]


def test_finite_boundary_measure_nested_mass_reuse_confuser_gate_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "finite_boundary_measure_nested_mass_reuse_confuser_gate",
        {
            "finite_boundary_measure_label": True,
            "vitali_whitney_covering_label": True,
            "nested_selected_tents_same_boundary_mass": True,
            "total_boundary_measure_finite_but_prefix_mass_unbounded": True,
            "discarded_children_not_paid_before_payoff": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"][
        "HighInterfaceBoundaryCarlesonPackingSelectionSource_excluded"
    ] is True


def test_high_interface_boundary_stopping_tree_energy_decrement_source_gate_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "high_interface_boundary_stopping_tree_energy_decrement_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"][
        "HighInterfaceBoundaryStoppingTreeEnergyDecrementSource"
    ] is True
    assert match["concludes"][
        "HighInterfaceBoundaryCarlesonPackingSelectionSource"
    ] is True


def test_high_interface_boundary_stopping_tree_energy_decrement_source_gate_rejects_energy_label() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "high_interface_boundary_stopping_tree_energy_decrement_source_gate",
        {
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
            "finite_energy_or_boundary_budget_label": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert match["rejected_substitutes"] == [
        "finite_energy_or_boundary_budget_label"
    ]


def test_boundary_carleson_without_stopping_decrement_confuser_gate_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "boundary_carleson_without_stopping_decrement_confuser_gate",
        {
            "finite_energy_or_boundary_budget_label": True,
            "high_interface_boundary_tent_family_label": True,
            "selected_tents_do_not_consume_monotone_energy_drop": True,
            "same_energy_reservoir_rebilled_down_nested_chain": True,
            "energy_drop_defined_from_target_deficit_or_after_payoff": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"][
        "HighInterfaceBoundaryStoppingTreeEnergyDecrementSource_excluded"
    ] is True

def test_channel_separated_stopping_tree_decrement_reserve_source_gate_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "channel_separated_stopping_tree_decrement_reserve_source_gate",
        {
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
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"][
        "ChannelSeparatedStoppingTreeDecrementReserveSource"
    ] is True
    assert match["concludes"][
        "HighInterfaceBoundaryStoppingTreeEnergyDecrementSource"
    ] is True


def test_channel_separated_stopping_tree_decrement_reserve_source_gate_rejects_refill_label() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "channel_separated_stopping_tree_decrement_reserve_source_gate",
        {
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
            "pressure_duhamel_inherited_refill_unpaid": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "NO_MATCH"
    assert match["rejected_substitutes"] == [
        "pressure_duhamel_inherited_refill_unpaid"
    ]


def test_stopping_tree_decrement_reserve_refill_confuser_gate_matches() -> None:
    from ztare.research_director.theorem_applicability_db import (
        match_theorem_applicability,
    )
    module = _load_module()

    match = match_theorem_applicability(
        "stopping_tree_decrement_reserve_refill_confuser_gate",
        {
            "stopping_tree_energy_drop_label": True,
            "pressure_duhamel_inherited_refill_unpaid": True,
            "child_invoice_omitted_or_post_payoff": True,
            "channel_partition_missing_before_payoff": True,
            "same_reserve_rebilled_across_nested_tents": True,
            "channel_drop_prefix_bound_missing": True,
        },
        module.NS_THEOREM_APPLICABILITY_DB,
    )

    assert match["verdict"] == "MATCH"
    assert match["concludes"][
        "ChannelSeparatedStoppingTreeDecrementReserveSource_excluded"
    ] is True

