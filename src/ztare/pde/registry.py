"""Canonical registry metadata for PDE subkernel gates.

Each PDE-relevant gate has a declarative entry with its workbench flag, runner,
renderer section, tags, and GP-219 op affinities. The RD workbench consumes this
registry, but does not own it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PDEGateRegistryEntry:
    """Declarative PDE gate metadata for leaf-agent work-order assembly."""

    gate_id: str
    workbench_flag: str
    runner: str
    renderer_section: str
    tags: tuple[str, ...]
    requires_ops: tuple[str, ...] = ()
    input_shape_hint: str = ""


DEFAULT_PDE_GATE_REGISTRY: tuple[PDEGateRegistryEntry, ...] = (
    PDEGateRegistryEntry(
        gate_id="G-PDE-ANALYTIC-SUBSTANCE",
        workbench_flag="--pde-analytic-substance-json",
        runner="ztare.gates.pde_analytic_substance_gate:run_pde_analytic_substance_gate",
        renderer_section="PDE Analytic Substance",
        tags=("analytic_substance", "estimate", "anti_plumbing"),
        requires_ops=("pec_a", "pec_h", "pec_l"),
        input_shape_hint=(
            "{analytic_object, target_estimate, quantitative_inequality, "
            "norm_or_quantity, scale_or_localization, derivation_mechanism, "
            "constants_or_exponents, endpoint_or_limit_handling, "
            "hostile_packet_or_sharpness}"
        ),
    ),
    PDEGateRegistryEntry(
        gate_id="G-PDE-THEOREM-APPLICABILITY",
        workbench_flag="--theorem-applicability-json",
        runner="ztare.research_director.theorem_applicability_db:match_theorem_applicability",
        renderer_section="Theorem Applicability",
        tags=("theorem_match", "profile_match", "confuser_rejection"),
        requires_ops=("pec_b", "pec_d", "pec_l"),
        input_shape_hint="{theorem, available}",
    ),
    PDEGateRegistryEntry(
        gate_id="G-PDE-INEQ-DIM",
        workbench_flag="--candidate-inequality",
        runner="ztare.gates.pde_inequality_dimensional_gate:run_gate",
        renderer_section="Inequality Checks",
        tags=("dimensional_check", "endpoint_check", "scaling"),
        input_shape_hint="{candidate_inequality, dimensional_features, allowed_endpoints}",
    ),
    PDEGateRegistryEntry(
        gate_id="G-PDE-PHYSICAL-ACCOUNTING",
        workbench_flag="--pde-physical-accounting-json",
        runner="ztare.gates.pde_physical_accounting_gate:run_pde_physical_accounting_gate",
        renderer_section="PDE Physical Accounting",
        tags=("physical_accounting", "conservation_law", "dimensional_check", "flux_boundary"),
        requires_ops=("pec_a", "pec_h", "pec_l"),
        input_shape_hint=(
            "{physical_system, governing_law_or_balance, "
            "conserved_or_dissipated_quantity, quantity_dimensions, "
            "target_dimensions, candidate_inequality, dimensional_features, "
            "allowed_endpoints, balance_law_terms, scale_normalization, "
            "flux_or_boundary_terms, localization_region, carrier_or_material_volume, "
            "source_sink_or_forcing_terms, sign_or_positivity_structure, "
            "operator_or_projection_losses, cutoff_commutator_or_tail_terms, "
            "initial_boundary_data, hostile_physical_packet, optional pi_group_forcing}"
        ),
    ),
    PDEGateRegistryEntry(
        gate_id="G-PDE-EQUALITY-PROVENANCE",
        workbench_flag="--pde-equality-provenance-json",
        runner=(
            "ztare.gates.pde_equality_provenance_gate:"
            "run_pde_equality_provenance_gate"
        ),
        renderer_section="PDE Equality Provenance",
        tags=("equality_provenance", "anti_laundering", "source_binding"),
        requires_ops=("pec_i", "pec_l"),
        input_shape_hint=(
            "{equality_target, left_stream, right_stream, provenance_kind, "
            "constructor_or_theorem, generated_fields, source_binding, "
            "constructor_body_assignments, anti_proxy_or_anti_laundering_fields, "
            "hostile_packet_or_confuser, proof_boundary}"
        ),
    ),
    PDEGateRegistryEntry(
        gate_id="G-PDE-OPERATOR-ADMISSIBILITY",
        workbench_flag="--pde-operator-admissibility-json",
        runner=(
            "ztare.gates.pde_operator_admissibility_gate:"
            "run_pde_operator_admissibility_gate"
        ),
        renderer_section="PDE Operator Admissibility",
        tags=("singular_integral", "operator", "cz_riesz", "commutator_tail"),
        requires_ops=("pec_h", "pec_l"),
        input_shape_hint=(
            "{operator_family, kernel_or_multiplier_model, input_output_norms, "
            "scale_or_bandlimit, localization_or_cutoff, carrier_identity, "
            "endpoint_handling, commutator_or_tail_payment, currency_target, "
            "same_stream_binding, hostile_packet_or_counterexample; canonical "
            "canary fields: operator, kernel_or_multiplier, carrier, bandlimit, "
            "support_identity, endpoint, cutoff_commutator, low_high_leakage, "
            "projection_target_identity, same_stream_binding, hostile_packets}"
        ),
    ),
    PDEGateRegistryEntry(
        gate_id="G-PDE-RIGOROUS-NUMERICS",
        workbench_flag="--pde-rigorous-numerics-json",
        runner=(
            "ztare.gates.pde_rigorous_numerics_certificate_gate:"
            "run_pde_rigorous_numerics_certificate_gate"
        ),
        renderer_section="PDE Rigorous Numerics",
        tags=("validated_numerics", "certificate", "interval", "tail_bound"),
        requires_ops=("pec_d", "pec_e"),
        input_shape_hint=(
            "{certificate_type, pde_problem_statement, discretization_or_basis, "
            "interval_arithmetic_or_bounds, residual_bound, truncation_tail_bound, "
            "a_posteriori_argument, reproducibility_artifact, validator, "
            "theorem_linkage, hostile_packet_or_failure_mode}"
        ),
    ),
    PDEGateRegistryEntry(
        gate_id="G-PDE-HOSTILE-WITNESS",
        workbench_flag="--pde-hostile-witness-json",
        runner="ztare.gates.pde_hostile_witness_gate:run_pde_hostile_witness_gate",
        renderer_section="PDE Hostile Witness",
        tags=("hostile_packet", "sharpness", "failure_witness"),
        requires_ops=("pec_e",),
        input_shape_hint=(
            "{witness_family, target_estimate_or_claim, amplitude_scaling, "
            "support_or_localization, frequency_or_scale_regime, "
            "norm_or_quantity_profile, hypotheses_preserved, "
            "conclusion_stressed_or_violated, failure_mechanism, "
            "parameter_limit, claim_boundary_update}"
        ),
    ),
    PDEGateRegistryEntry(
        gate_id="G-SAME-CARRIER-PACKING",
        workbench_flag="--same-carrier-packing-json",
        runner="ztare.gates.same_carrier_packing_gate:run_same_carrier_packing_gate",
        renderer_section="Same-Carrier Packing",
        tags=("same_carrier", "packing", "no_reuse"),
        requires_ops=("pec_j",),
        input_shape_hint=(
            "{source_carrier, target_payment_family, assignment_or_injection_map, "
            "assignment_total_on_prefix, same_carrier_binding, "
            "overlap_or_multiplicity_bound, finite_prefix_budget, "
            "pre_payoff_timing, no_nested_reuse, no_rebilling_same_atom}"
        ),
    ),
    PDEGateRegistryEntry(
        gate_id="G-NO-REBILLING-FRESHNESS",
        workbench_flag="--no-rebilling-freshness-json",
        runner="ztare.gates.no_rebilling_freshness_gate:run_no_rebilling_freshness_gate",
        renderer_section="No-Rebilling Freshness",
        tags=("freshness", "no_rebilling", "single_spend"),
        requires_ops=("pec_j",),
    ),
    PDEGateRegistryEntry(
        gate_id="G-NONADAPTIVE-SOURCE-SELECTION",
        workbench_flag="--nonadaptive-source-selection-json",
        runner="ztare.gates.nonadaptive_source_selection_gate:run_nonadaptive_source_selection_gate",
        renderer_section="Nonadaptive Source Selection",
        tags=("nonadaptive", "pre_payoff", "source_selection"),
        requires_ops=("pec_i",),
    ),
    PDEGateRegistryEntry(
        gate_id="G-OWNER-PREIMAGE-PREFIX",
        workbench_flag="--owner-preimage-receipt-json",
        runner="ztare.gates.owner_preimage_prefix_gate:run_owner_preimage_prefix_gate",
        renderer_section="Owner Preimage Prefix",
        tags=("phase_space", "owner_preimage", "prefix_budget"),
        requires_ops=("pec_k",),
    ),
    PDEGateRegistryEntry(
        gate_id="G-POSITIVE-VARIATION-BRIDGE",
        workbench_flag="--positive-variation-bridge-json",
        runner="ztare.gates.positive_variation_bridge_gate:run_positive_variation_bridge_gate",
        renderer_section="Positive Variation Bridge",
        tags=("signed_to_positive", "variation", "currency_exchange"),
        requires_ops=("pec_l",),
    ),
    PDEGateRegistryEntry(
        gate_id="G-LINEAR-OBS-COERCIVITY",
        workbench_flag="--linear-observable-coercivity-json",
        runner="ztare.gates.linear_observable_coercivity_gate:run_gate",
        renderer_section="Linear Observable Coercivity",
        tags=("coercivity", "rank", "observable"),
        requires_ops=("pec_l",),
    ),
)


def all_pde_gate_entries() -> list[dict[str, Any]]:
    """Return every registered PDE gate entry for workbench packs and leaf agents."""
    return [asdict(entry) for entry in DEFAULT_PDE_GATE_REGISTRY]


def entries_for_op(op_id: str) -> list[dict[str, Any]]:
    """Return PDE gate entries associated with a GP-219 `pec_*` operation."""
    return [
        asdict(entry)
        for entry in DEFAULT_PDE_GATE_REGISTRY
        if op_id in entry.requires_ops
    ]


def entry_by_gate_id(gate_id: str) -> dict[str, Any] | None:
    """Return one PDE gate registry entry by stable gate id."""
    for entry in DEFAULT_PDE_GATE_REGISTRY:
        if entry.gate_id == gate_id:
            return asdict(entry)
    return None
