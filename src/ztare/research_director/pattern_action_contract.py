"""Kernel surface for turning patterns into RD action contracts.

The pattern catalogue is useful only when it changes the evidence path. This
module converts common hard-residual surfaces into a compact contract: which
patterns apply, which anti-patterns to guard, and which local artifacts must be
produced before a close is credible.

Compiler/checker terminology used below is operational, not decorative:

* ``requested_residual_class`` is the model or RD frontend proposal.
* source-cue receipts are check bits: they make the class proposal auditable and
  allow a deterministic checker to reject unsafe class choices.
* ``accepted_residual_class`` is the class after those checks.
* deterministic lowering maps an accepted class to an ``action_program``.
* ``current_action_index`` / ``required_next_action`` are the runtime program
  counter.

These fields are intended to be compiler/checker-filled shadow metadata wherever
possible. The RD agent burden should be confirmation, exception handling, and
repair of failed checks, not manual essay-writing for every field. H32-H39 in
the epistemic-generation log are the evidence basis: free-form program synthesis
failed, checked class selection plus deterministic lowering matched
hand-compiled behavior on the held-out packet, compact checked contracts
matched full contracts for controller execution, an open-set refusal path
prevented forcing outside blockers into known menu classes, specific outside
residual classes beat generic outside routing, and source-alignment checks
repaired plausible wrong contracts. H40-H42 extend this: larger outside-class
tests showed flat outside-class expansion can hurt in-menu accuracy, and subtle
wrong-contract tests showed alignment alone is not enough without
program/order/stop checks. The NS PDE failure mode adds one narrow operational
lesson: when a conditional source law and bounded/selectable carrier are
visible, the next program step must include a positive constructor attempt, not
only another obstruction audit.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ztare.common.kernel_action_schema import KernelActionSchema
from ztare.research_director.primitive_operator_cards import (
    operator_card_route_receipts,
    render_operator_card_route_summary,
)


REPO = Path(__file__).resolve().parents[3]
OUT_PATH = REPO / "analytics" / "public" / "queries" / "rd_pattern_action_contract.json"


@dataclass(frozen=True)
class EvidenceCarrier:
    name: str
    required: bool
    artifact_slot: str
    acceptance_check: str
    required_fields: list[str] = field(default_factory=list)
    schema_mode: str = "artifact_ref_or_action_constraint_fields"


@dataclass(frozen=True)
class PatternActionContract:
    generated_at: str
    scope: str | None
    goal_excerpt: str
    problem_surfaces: list[str]
    pattern_chain: list[str]
    anti_patterns: list[str]
    obligation_spine: list[str] = field(default_factory=list)
    operator_card_routes: list[dict] = field(default_factory=list)
    route_tests: list[str] = field(default_factory=list)
    evidence_carriers: list[EvidenceCarrier] = field(default_factory=list)
    stop_rule: str = ""
    decision_rule: str = ""
    evidence_basis: str = ""
    kernel_action_schemas: list[dict] = field(default_factory=list)


def _tokens(text: str | None) -> set[str]:
    raw = (text or "").lower().replace("_", " ").replace("-", " ")
    toks = set(raw.split())
    if "de giorgi" in raw:
        toks.add("de giorgi")
    return toks


def _nearest_confuser_from_tests(route_tests: list[str]) -> str:
    for test in route_tests:
        if "confuser" in test.lower():
            return test
    return (
        "pattern name, primitive vocabulary, or carrier label selected without "
        "the source-bound action fields"
    )


def _kernel_action_schemas_for_contract(
    *,
    scope: str | None,
    goal: str | None,
    problem_surfaces: list[str],
    pattern_chain: list[str],
    route_tests: list[str],
    carriers: list[EvidenceCarrier],
) -> list[dict]:
    actions: list[dict] = []
    for carrier in carriers:
        if not carrier.required:
            continue
        actions.append(
            KernelActionSchema(
                source_kind="pattern_action_contract",
                action_family="pattern_contract",
                action_name=carrier.name,
                source_summary=carrier.acceptance_check,
                target_mapping=(
                    f"fill {carrier.artifact_slot} for "
                    f"{(goal or scope or 'current research task')[:160]}"
                ),
                nearest_confuser=_nearest_confuser_from_tests(route_tests),
                falsifier=(
                    "the artifact is absent, lacks required fields, or follows "
                    "the named confuser instead of the selected action"
                ),
                verification_artifact=carrier.artifact_slot,
                action_constraints=[
                    *carrier.required_fields,
                    carrier.acceptance_check,
                ],
                evidence_basis=(
                    "epistemic-generation: checked carrier fields and "
                    "nearest-confuser rejection beat pattern labels"
                ),
                payload={
                    "scope": scope,
                    "goal_excerpt": (goal or "")[:500],
                    "problem_surfaces": list(problem_surfaces),
                    "pattern_chain": list(pattern_chain),
                    "carrier": asdict(carrier),
                    "route_tests": list(route_tests),
                },
            ).to_dict()
        )
    return actions


def build_pattern_action_contract(
    *,
    scope: str | None = None,
    goal: str | None = None,
) -> PatternActionContract:
    """Build a compact action contract from scope/goal signals."""
    scope_tokens = _tokens(scope)
    goal_tokens = _tokens(goal)
    all_tokens = scope_tokens | goal_tokens
    formal = bool({"lean", "formal", "theorem", "lemma"} & all_tokens)
    context = "\n".join(
        part
        for part in (
            f"area {scope}" if scope else "",
            f"goal {goal}" if goal else "",
        )
        if part
    )
    try:
        from ztare.research_director.primitive_operator_cards import (
            route_operator_cards,
            route_operator_cards_semantic,
            route_obligation_classes,
        )
        obligation_spine = [
            item.class_id for item in route_obligation_classes(
                context=context,
                top_n=2,
            )
        ]
        routed_operator_cards = route_operator_cards_semantic(context=context, top_n=12)
        exact_operator_cards = route_operator_cards(context=context, top_n=12)
    except Exception:  # noqa: BLE001
        obligation_spine = []
        routed_operator_cards = []
        exact_operator_cards = []
    operator_card_routes = operator_card_route_receipts(routed_operator_cards)
    exact_card_ids = {card.card_id for card in exact_operator_cards}
    strong_semantic_card_ids = {
        str(route.get("card_id") or "")
        for route in operator_card_routes
        if str(route.get("route_mode") or "") == "semantic_atlas"
        and float(route.get("score") or 0.0) >= 75.0
    }
    active_card_ids = exact_card_ids | strong_semantic_card_ids
    hard = "OP-HRD-01" in active_card_ids
    pde = "OP-PDE-01" in active_card_ids
    claim_boundary = "OP-CBM-01" in active_card_ids
    surplus_lift = "OP-SLP-01" in active_card_ids
    analogy = "OP-XFT-01" in active_card_ids
    portable_estimate_receipt = "OP-PER-01" in active_card_ids
    meta_language = "OP-MME-01" in active_card_ids
    primary_card_id = (
        exact_operator_cards[0].card_id
        if exact_operator_cards
        else (routed_operator_cards[0].card_id if routed_operator_cards else "")
    )
    reflexive_mining = "OP-RMI-01" in active_card_ids
    autoresearch_workbench = "OP-AWR-01" in active_card_ids
    graph_diagnostic = "OP-GDC-01" in active_card_ids
    if primary_card_id == "OP-AWR-01":
        reflexive_mining = False
    if primary_card_id == "OP-RMI-01":
        autoresearch_workbench = False

    surfaces: list[str] = []
    chain: list[str] = []
    anti: list[str] = []
    carriers: list[EvidenceCarrier] = []
    route_tests = [
        "Does this action force a concrete next check, artifact, gate, or breaker?",
        "Does this action mutate the question when the current question is poorly posed?",
        "Does this action defer or kill the branch when the visible state only renames a known gap?",
        "Does this action avoid treating visible context as proof of the hidden outcome?",
        "Which <=3 operator candidates were considered, which one was selected, and which nearest confuser was rejected?",
        "If the nearest confuser is branch/interface/claim-boundary/source-target, which boundary disambiguator decided the route?",
        "Which action-constraint fields distinguish the selected operator from the nearest polished wrong-path artifact?",
        "Do the selected receipt fields align with source facts, or do they pull the output toward a nearest-confuser contract?",
        "Was the action target inferred from source facts, or spoon-fed by proposed-update/check-menu wording?",
        "If a receipt fails, what exact repair or stop rule follows before more research is allowed?",
        "What downstream consumer check would prove the handoff was executable rather than decorative?",
        "If an anti-pattern is raised, what clean-proceed condition prevents block-everything skepticism?",
        "Which operator-card routes came from semantic_atlas vs lexical_fallback, and what matched terms or scores justify the selected route?",
    ]

    if hard:
        surfaces.append("hard_mathematical_residual")
        chain.extend([
            "OP-HRD-01:hard_residual_research_contract",
            "PATTERN-025:gowers_first_formalize_second",
            "META-PATTERN-022:gowers_first_with_content_layer_composition",
            "PATTERN-011:swarm_dispatch",
            "PATTERN-028:recursive_tool_depth_loop",
            "PATTERN-002:darwin_idea_killer",
        ])
        anti.extend([
            "ANTI-PATTERN-011:scientific_amnesia",
            "ANTI-PATTERN-018:tool_underuse_formal_satisficing",
            "ANTI-PATTERN-012:vocabulary_chain_laundering",
            "ANTI-PATTERN-014:premature_settled_negative",
            "ANTI-PATTERN-016:premature_heuristic_escape",
            "ANTI-PATTERN-017:category_conflation_strawman_shift",
            "ANTI-PATTERN-005:narrative_inflation",
        ])
        carriers.extend([
            EvidenceCarrier(
                name="hard_residual_antipattern_guard",
                required=True,
                artifact_slot="anti_pattern_guard_artifact",
                acceptance_check=(
                    "artifact records prior-overlap/amnesia result, local work "
                    "before terminal negatives or heuristic escape, exact object "
                    "identity for reviewer objections, scoped claim wording, "
                    "minimal preventive artifact, typed boundary state, boundary "
                    "preprocessor card fields, boundary card source-alignment "
                    "check, missing-or-paid preventive receipt, "
                    "source-specific false-reading confuser, "
                    "nearest-confuser rejection, clean-proceed condition, "
                    "paid-clean terminal action, and intervention feedback "
                    "trace across repair/proceed legs"
                ),
                required_fields=[
                    "prior_overlap_check",
                    "local_work_before_terminal_negative",
                    "heuristic_escape_blocker",
                    "object_identity_check",
                    "claim_scope_boundary",
                    "minimal_preventive_artifact",
                    "typed_boundary_state",
                    "boundary_preprocessor_card",
                    "paid_receipt",
                    "unpaid_receipt",
                    "permitted_update",
                    "blocked_update",
                    "next_action_rule",
                    "boundary_card_action_program",
                    "boundary_card_current_action_index",
                    "boundary_card_required_next_action",
                    "boundary_card_program_counter_rule",
                    "boundary_card_source_alignment_check",
                    "boundary_card_source_cue_receipts",
                    "boundary_card_validation_status",
                    "boundary_card_rewrite_or_refusal_rule",
                    "boundary_card_gate_result",
                    "boundary_card_gate_cli",
                    "boundary_card_repair_trace_cli",
                    "missing_or_paid_preventive_receipt",
                    "source_specific_false_reading_confuser",
                    "nearest_confuser_rejection",
                    "clean_proceed_condition",
                    "paid_clean_terminal_action",
                    "intervention_feedback_trace",
                ],
            ),
            EvidenceCarrier(
                name="orientation",
                required=True,
                artifact_slot="orientation_artifact",
                acceptance_check=(
                    "pencil artifact names eigenquestion, candidate "
                    "theorem/obstruction, kill condition, and ops/checks"
                ),
                required_fields=[
                    "eigenquestion",
                    "candidate_theorem_or_obstruction",
                    "kill_condition",
                    "intended_checks",
                ],
            ),
            EvidenceCarrier(
                name="tool_or_primitive_pass",
                required=True,
                artifact_slot="stress_test_artifact",
                acceptance_check=(
                    "class-matched workbench/graph/gate/primitives run, "
                    "or each skipped tool has why_not"
                ),
                required_fields=[
                    "tool_or_primitive",
                    "result",
                    "nearest_confuser",
                    "repair_or_stop",
                ],
            ),
            EvidenceCarrier(
                name="artifact_edit",
                required=True,
                artifact_slot="artifact_ref",
                acceptance_check=(
                    "formal/code/graph/falsifier artifact changed the "
                    "residual surface or cleanly killed it"
                ),
                required_fields=[
                    "artifact_changed",
                    "residual_delta",
                    "claim_boundary",
                ],
            ),
            EvidenceCarrier(
                name="post_edit_stress",
                required=True,
                artifact_slot="verification_artifact",
                acceptance_check=(
                    "patched artifact was rerun through compile/check/tool "
                    "and adversarial critique when applicable"
                ),
                required_fields=[
                    "verification_command_or_gate",
                    "verdict",
                    "remaining_failure_mode",
                ],
            ),
        ])

    if pde:
        surfaces.append("pde_estimate_or_carrier_residual")
        if "OP-PDE-01:pde_estimate_or_carrier_contract" not in chain:
            insert_at = 1 if chain and chain[0] == "OP-HRD-01:hard_residual_research_contract" else 0
            chain.insert(insert_at, "OP-PDE-01:pde_estimate_or_carrier_contract")
        if "GP-219:pde_estimate_craft_ops" not in chain:
            insert_at = (
                chain.index("OP-PDE-01:pde_estimate_or_carrier_contract") + 1
                if "OP-PDE-01:pde_estimate_or_carrier_contract" in chain
                else (1 if chain else 0)
            )
            chain.insert(insert_at, "GP-219:pde_estimate_craft_ops")
        anti.append("ANTI-PATTERN-013:lean_closure_laundering")
        carriers.append(
            EvidenceCarrier(
                name="pde_workbench_or_dimensional_gate",
                required=True,
                artifact_slot="tool_pass_artifact",
                acceptance_check=(
                    "PDE estimate/workbench, dimensional/endpoint, "
                    "single-spend, or pi/Buckingham check run as applicable"
                ),
                required_fields=[
                    "pde_tool_or_gate",
                    "estimate_target",
                    "passed_or_failed",
                    "why_not_if_skipped",
                ],
            )
        )
        carriers.append(
            EvidenceCarrier(
                name="estimate_attempt_or_sharp_witness",
                required=True,
                artifact_slot="estimate_attempt_artifact",
                acceptance_check=(
                    "after the workbench/tool pass, attempt the actual "
                    "PDE estimate route or construct a sharp hostile "
                    "witness; artifact must state theorem/counterexample, "
                    "proof attempt layers, and exact kill condition"
                ),
                required_fields=[
                    "theorem_or_counterexample",
                    "proof_layers",
                    "sharp_witness_or_blocker",
                    "kill_condition",
                ],
            )
        )
        carriers.append(
            EvidenceCarrier(
                name="constructive_turn_check",
                required=True,
                artifact_slot="positive_constructor_attempt_artifact",
                acceptance_check=(
                    "if a conditional source law and bounded/selectable "
                    "carrier are visible, artifact includes a positive "
                    "constructor attempt before obstruction-only continuation; "
                    "if skipped, why_not names an already-tested blocker"
                ),
                required_fields=[
                    "conditional_source_law",
                    "target_carrier",
                    "bounded_or_selectable_variable",
                    "constructor_map_or_why_not",
                    "nearest_confuser",
                    "first_failed_line_or_success",
                ],
            )
        )

    if analogy:
        surfaces.append("analogy_to_receipt_transfer")
        if "PATTERN-018:structural_residual_analogy" not in chain:
            chain.append("PATTERN-018:structural_residual_analogy")
        anti.extend([
            "ANTI-PATTERN-012:vocabulary_chain_laundering",
            "ANTI-PATTERN-005:narrative_inflation",
        ])
        route_tests.append(
            "Did the analogy produce a target-side receipt/falsifier, or only better wording?"
        )
        route_tests.append(
            "What exact decision changes if the mapped target-side receipt passes or fails?"
        )
        carriers.append(
            EvidenceCarrier(
                name="analogy_mapping_receipt",
                required=True,
                artifact_slot="analogy_receipt_artifact",
                acceptance_check=(
                    "source-target mapping compiles to a target-side theorem, "
                    "gate/workbench check, formal field, or explicit missing "
                    "primitive; includes a target-domain falsifier and decision "
                    "consequence"
                ),
                required_fields=[
                    "source_frame",
                    "target_frame",
                    "object_mapping",
                    "preservation_receipt",
                    "target_domain_falsifier",
                    "decision_consequence",
                ],
            )
        )

    if surplus_lift:
        surfaces.append("surplus_loss_projection_certificate")
        for item in (
            "core_06:external_framework_importation",
            "broad_07:dimensional_lifting",
            "core_05:canonical_form_and_invariance",
        ):
            if item not in chain:
                chain.append(item)
        anti.extend([
            "ANTI-PATTERN-012:vocabulary_chain_laundering",
            "ANTI-PATTERN-005:narrative_inflation",
        ])
        route_tests.append(
            "What ambient surplus is created, what fixed loss is paid, and what projection returns it to the target claim?"
        )
        route_tests.append(
            "Are constants and selection rules fixed before the limiting process, or chosen after seeing the payoff?"
        )
        route_tests.append(
            "What target-size, packing, denominator, or multiplicity bound converts the ambient surplus into the target-domain exponent or decision gain?"
        )
        carriers.append(
            EvidenceCarrier(
                name="surplus_loss_projection_certificate",
                required=True,
                artifact_slot="surplus_projection_artifact",
                acceptance_check=(
                    "artifact names the ambient lift, surplus lower bound, "
                    "loss/quotient budget, projection map, injectivity or "
                    "finite-multiplicity receipt, target-size/packing bound, "
                    "constants-before-limit rule, and target-domain falsifier"
                ),
                required_fields=[
                    "target_object",
                    "ambient_lift",
                    "surplus_lower_bound",
                    "loss_or_quotient_budget",
                    "projection_map",
                    "multiplicity_or_injectivity_receipt",
                    "target_size_or_packing_bound",
                    "constants_before_limit_rule",
                    "target_domain_falsifier",
                ],
            )
        )

    if claim_boundary:
        surfaces.append("claim_boundary_schema_receipt")
        if "OP-CBM-01:claim_boundary_mutation" not in chain:
            chain.append("OP-CBM-01:claim_boundary_mutation")
        anti.extend([
            "ANTI-PATTERN-005:narrative_inflation",
            "ANTI-PATTERN-012:vocabulary_chain_laundering",
        ])
        route_tests.append(
            "Does the artifact emit action-constraint broad/narrow claim rows, or only prose about scope?"
        )
        route_tests.append(
            "Are answer_object and success_criterion explicit for both the blocked broad claim and permitted narrow claim?"
        )
        carriers.append(
            EvidenceCarrier(
                name="claim_boundary_typed_rows",
                required=True,
                artifact_slot="claim_boundary_schema_artifact",
                acceptance_check=(
                    "artifact has exactly one broad and one narrow claim row; "
                    "each row includes claim_kind, claim_text, answer_object, "
                    "success_criterion, evidence_available, "
                    "missing_evidence_or_blocker, and permitted_status; broad "
                    "row is BLOCKED, narrow row is PERMITTED, and the pass/fail "
                    "boundary is explicit"
                ),
                required_fields=[
                    "claim_kind",
                    "claim_text",
                    "answer_object",
                    "success_criterion",
                    "evidence_available",
                    "missing_evidence_or_blocker",
                    "permitted_status",
                    "pass_fail_boundary",
                ],
            )
        )

    if meta_language:
        surfaces.append("meta_language_edge_carrier")
        if "OP-MME-01:meta_language_edge_carrier" not in chain:
            chain.append("OP-MME-01:meta_language_edge_carrier")
        for item in (
            "mm_02:surface_quotient_to_evidence_path_graph",
            "mm_03:promote_live_residual_edge",
        ):
            if item not in chain:
                chain.append(item)
        anti.extend([
            "ANTI-PATTERN-005:narrative_inflation",
            "ANTI-PATTERN-012:vocabulary_chain_laundering",
        ])
        route_tests.append(
            "Did the mm surface name a causal edge from observed state to required check, or only a family label?"
        )
        route_tests.append(
            "Which surface wording was quotient-hidden, and which residual/blocker edge selected the next artifact?"
        )
        carriers.append(
            EvidenceCarrier(
                name="meta_language_edge_receipt",
                required=True,
                artifact_slot="meta_language_edge_artifact",
                acceptance_check=(
                    "artifact states observed_state, quotient_hidden_surface, "
                    "evidence_path_graph, live_residual_or_blocker, "
                    "candidate_edge, required_check, forbidden_sibling, "
                    "permitted_update_if_paid, and stop_rule; mm label alone "
                    "does not satisfy the carrier"
                ),
                required_fields=[
                    "observed_state",
                    "quotient_hidden_surface",
                    "evidence_path_graph",
                    "live_residual_or_blocker",
                    "candidate_edge",
                    "required_check",
                    "forbidden_sibling",
                    "permitted_update_if_paid",
                    "stop_rule",
                ],
            )
        )

    if portable_estimate_receipt:
        surfaces.append("portable_estimate_receipt_schema")
        if "OP-PER-01:portable_estimate_receipt_schema" not in chain:
            chain.append("OP-PER-01:portable_estimate_receipt_schema")
        anti.extend([
            "ANTI-PATTERN-003:vocabulary_smuggling",
            "ANTI-PATTERN-012:vocabulary_chain_laundering",
        ])
        route_tests.append(
            "Which portable receipt form is selected: pec_a auxiliary object, pec_b scope contract, pec_e sharpness/failure witness, or cand_g representation reformulation?"
        )
        route_tests.append(
            "What action-constraint fields distinguish the selected receipt from its nearest pec/cand confuser?"
        )
        route_tests.append(
            "Can the close-side validator check the action-constraint content field-by-field, rather than accepting artifact existence?"
        )
        carriers.append(
            EvidenceCarrier(
                name="portable_estimate_receipt_schema",
                required=True,
                artifact_slot="portable_estimate_receipt_artifact",
                acceptance_check=(
                    "artifact names the selected portable receipt family, "
                    "fills its action-constraint fields with checkable content, "
                    "names the nearest confuser, and states the target-domain "
                    "decision consequence; artifact existence or pec/cand "
                    "labels alone do not satisfy the carrier"
                ),
                required_fields=[
                    "selected_receipt_family",
                    "substrate_or_domain",
                    "action_constraint_fields",
                    "typed_fields_filled",
                    "nearest_confuser",
                    "confuser_rejection_reason",
                    "artifact_change",
                    "decision_consequence",
                ],
            )
        )

    if graph_diagnostic:
        surfaces.append("graph_diagnostic_carrier")
        if "OP-GDC-01:graph_diagnostic_carrier" not in chain:
            chain.append("OP-GDC-01:graph_diagnostic_carrier")
        anti.extend([
            "ANTI-PATTERN-005:narrative_inflation",
            "ANTI-PATTERN-012:vocabulary_chain_laundering",
        ])
        route_tests.append(
            "Which graph algorithm is standard-library backed, and which layer is ZTARE-specific extraction, conditioning, disagreement, perturbation, or receipt?"
        )
        route_tests.append(
            "What downstream gate, pattern-action carrier, next artifact slot, or explicit non-use receipt did the graph select?"
        )
        carriers.append(
            EvidenceCarrier(
                name="graph_diagnostic_carrier",
                required=True,
                artifact_slot="graph_carrier_artifact",
                acceptance_check=(
                    "artifact validates against the graph-carrier schema, names "
                    "the standard library or method family for each diagnostic, "
                    "states the substrate-specific extraction/filtering layer, "
                    "and records a decision receipt: strategy_change, "
                    "no_strategy_change, or misleading_or_noise. A metric "
                    "without a selected action card, gate, artifact slot, or "
                    "non-use/retraction reason does not satisfy the carrier"
                ),
                required_fields=[
                    "graph_id",
                    "graph_kind",
                    "producer",
                    "source_artifacts",
                    "consumer",
                    "freshness_rule",
                    "diagnostics",
                    "noise_filter",
                    "decision_receipt",
                    "selected_action_card_or_gate",
                    "non_use_or_retraction",
                ],
            )
        )

    if formal:
        surfaces.append("formal_frontier")
        if "PATTERN-008:three_leg_verification" not in chain:
            chain.append("PATTERN-008:three_leg_verification")
        if "ANTI-PATTERN-013:lean_closure_laundering" not in anti:
            anti.append("ANTI-PATTERN-013:lean_closure_laundering")

    if autoresearch_workbench:
        surfaces.append("autoresearch_workbench_routing")
        if "OP-AWR-01:autoresearch_workbench_routing" not in chain:
            chain.append("OP-AWR-01:autoresearch_workbench_routing")
        carriers.append(
            EvidenceCarrier(
                name="autoresearch_workbench_routing",
                required=True,
                artifact_slot="autoresearch_workbench_routing_artifact",
                acceptance_check=(
                    "record task, project family, bounded-claim/evaluator/rubric/"
                    "artifact booleans, router decision, missing surfaces, "
                    "worker metadata, saved route JSON, action-impact row, and "
                    "a route-specific evidence reference to the autoresearch "
                    "run/projection or prepared/bypassed surface"
                ),
                required_fields=[
                    "task",
                    "project_family",
                    "bounded_claim",
                    "stable_evaluator",
                    "rubric_ready",
                    "artifact_surface",
                    "workbench_router_decision",
                    "why_not_autoresearch",
                    "worker_metadata",
                    "route_json_ref",
                    "action_impact_ref",
                    "workbench_evidence_ref",
                ],
            )
        )

    if reflexive_mining:
        surfaces.append("reflexive_mining_instrument_check")
        if "OP-RMI-01:reflexive_mining_instrument_check" not in chain:
            chain.append("OP-RMI-01:reflexive_mining_instrument_check")
        carriers.append(
            EvidenceCarrier(
                name="reflexive_mining_instrument_check",
                required=True,
                artifact_slot="reflexive_mining_instrument_artifact",
                acceptance_check=(
                    "artifact names the portfolio question, inspected source "
                    "refs, metric name/value, freshness or sample-scope caveat, "
                    "decision consequence, falsifier, and next action; activity "
                    "volume alone is not accepted as yield evidence"
                ),
                required_fields=[
                    "portfolio_question",
                    "source_refs",
                    "metric_name",
                    "metric_value",
                    "freshness_or_scope_note",
                    "decision_consequence",
                    "falsifier",
                    "next_action",
                ],
            )
        )

    if (
        hard or pde or analogy or surplus_lift or claim_boundary
        or meta_language or portable_estimate_receipt or graph_diagnostic or formal
        or autoresearch_workbench or reflexive_mining
    ):
        carriers.insert(
            0,
            EvidenceCarrier(
                name="routed_operator_receipt_gate",
                required=True,
                artifact_slot="operator_receipt_gate_artifact",
                acceptance_check=(
                    "route <=3 candidate operators, select one, name the "
                    "nearest confuser, fill operator-specific action-constraint "
                    "fields, state reject/repair behavior for failed receipts, "
                    "and name the downstream consumer check that would verify "
                    "the handoff was executable"
                ),
                required_fields=[
                    "candidate_operators",
                    "selected_operator",
                    "nearest_confuser",
                    "action_constraint_fields",
                    "operator_card_route_provenance",
                    "action_target_source",
                    "source_contract_alignment_check",
                    "required_receipts",
                    "reject_or_repair_behavior",
                    "downstream_consumer_check",
                ],
            ),
        )

    if not surfaces:
        surfaces.append("general_research_task")
        chain.append("PATTERN-012:prediction_ledger_if_action_gating")
        carriers.append(
            EvidenceCarrier(
                name="decision_boundary",
                required=False,
                artifact_slot="decision_artifact",
                acceptance_check="log only if the action gates a typed commitment",
            )
        )

    carriers.append(
        EvidenceCarrier(
            name="orchestration_shadow_controller_log",
            required=False,
            artifact_slot="orchestration_shadow_log_artifact",
            acceptance_check=(
                "non-blocking instrumentation for Axis B: when the menu or "
                "state policy influences a decision, keep a compact active "
                "controller surface plus shadow audit metadata. Active "
                "execution uses accepted class, cue-check status, action "
                "program, current index, required next action, program "
                "counter, open-set refusal status, source-contract alignment, "
                "specific outside residual class, deterministic lowering result, known-class-first check, program order check, and stop-condition check. Full edge/source-cue receipts stay available for "
                "audit, replay, compiler repair, cost/regret analysis, final "
                "disposition, and later outcome ref"
            ),
            required_fields=[
                "pre_decision_state_id",
                "candidate_action",
                "controller_state_variables",
                "orchestration_active_controller_surface",
                "orchestration_accepted_residual_class",
                "orchestration_source_cue_check_status",
                "orchestration_action_program",
                "orchestration_current_action_index",
                "orchestration_required_next_action",
                "orchestration_program_counter_rule",
                "orchestration_open_set_refusal_status",
                "orchestration_new_residual_class_candidate",
                "orchestration_specific_outside_residual_class",
                "orchestration_known_class_first_check",
                "orchestration_source_contract_alignment_check",
                "orchestration_wrong_contract_repair_or_refusal",
                "orchestration_deterministic_lowering_result",
                "orchestration_program_order_check",
                "orchestration_stop_condition_check",
                "orchestration_audit_surface_ref",
                "orchestration_requested_residual_class",
                "selected_residual_edge",
                "rejected_nearest_confuser_edge",
                "edge_source_evidence",
                "orchestration_source_cue_receipts_ref",
                "orchestration_missing_source_cues_ref",
                "transition_guard",
                "owed_artifact_or_receipt",
                "forbidden_overstep",
                "final_disposition",
                "cost_or_regret_signal",
                "later_outcome_ref",
            ],
        )
    )

    # Preserve order while removing duplicates.
    def dedupe(xs: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for x in xs:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    problem_surfaces = dedupe(surfaces)
    pattern_chain = dedupe(chain)
    anti_patterns = dedupe(anti)
    kernel_action_schemas = _kernel_action_schemas_for_contract(
        scope=scope,
        goal=goal,
        problem_surfaces=problem_surfaces,
        pattern_chain=pattern_chain,
        route_tests=route_tests,
        carriers=carriers,
    )

    return PatternActionContract(
        generated_at=datetime.now(timezone.utc).isoformat(),
        scope=scope,
        goal_excerpt=(goal or "")[:500],
        problem_surfaces=problem_surfaces,
        obligation_spine=obligation_spine,
        operator_card_routes=operator_card_routes,
        pattern_chain=pattern_chain,
        anti_patterns=anti_patterns,
        route_tests=route_tests,
        evidence_carriers=carriers,
        stop_rule=(
            "Do not close on pattern mention, primitive vocabulary, or broad "
            "meta-language alone. Close only after the selected operator's "
            "action constraints separate it from the nearest confuser, or a "
            "decisive repair/kill is recorded with the missing receipt named."
        ),
        decision_rule=(
            "Treat a receipt miss as repair_required or needs_schema_completion "
            "by default. Hard-reject only when the artifact follows a named "
            "wrong-path confuser, or when repair exposes a missing discriminator "
            "that blocks the move. For MM/self-referential surfaces, require "
            "an explicit nearest-confuser rejection before accepting a repair."
        ),
        evidence_basis=(
            "epistemic-generation/research_log.md "
            "V54/MM-V7/V55/MM-V8/V183b/V183b-light: "
            "passive labels and large menus were weak; target primitive/mm "
            "receipt gates rejected polished near-misses, and receipt-guided "
            "repair outperformed generic repair. Use small routed operator "
            "sets, nearest-confuser checks, required receipts, and stop/repair "
            "rules. V183b shows the V128 surface should be a repair trigger, "
            "not a hard accept/reject gate; V183b-light restores positive "
            "recall but is too permissive on MM near-misses without a "
            "nearest-confuser check."
            " The 2026-05-21 unit-distance proof read in the epistemic-generation "
            "research log adds a provisional naturalistic stress case for a "
            "surplus/loss/projection certificate: lift to an auxiliary arithmetic "
            "world, keep split-prime surplus ahead of class-number/denominator/window "
            "losses, then project back only after injectivity and target-size bounds "
            "are paid. Treat as an experimental action surface, not a catalog promotion."
            " V83 latent-factor audit: primitive score dimensions were dominated "
            "by a general artifact-quality factor, while audited label disputes "
            "clustered at branch/interface, branch/claim-boundary, and "
            "source-target/branch; refine disambiguators before adding families."
            " V98/V99 claim-boundary field-gate/schema-ablation: the active "
            "carrier for claim_boundary_split is a typed broad/narrow claim-row "
            "schema; schema-only was incomplete and schema plus the claim-boundary "
            "fine handle paid best. Treat fine handles as routers to typed, "
            "machine-checkable receipt fields."
            " MM-V19/MM-V20 and V70/V72: mm names did not beat full de-labeled "
            "slots, but compressed definitions plus short slots were useful; "
            "the current mm_02+mm_03 operational carrier is a causal "
            "evidence-path edge with an explicit required_check and forbidden "
            "sibling, not a bare label."
            " V111 portable-receipt causal triad: GP-219-style typed receipt "
            "fields are the strongest current action-changing cause; GP-216 "
            "ops are indexing/routing handles, and nearest-confuser rejection "
            "is a necessary guard rather than a standalone cause. Gauss/Locke "
            "readout plus v128a/v128b/v128d: pec_a/pec_b/pec_e remain frozen "
            "portable receipt schemas over GP-216, cand_g is not promoted "
            "while it remains confused with core_01, and machinery should route "
            "on coarse obligation classes rather than a 24-way fine-label "
            "pick. Fine handles remain human recognition/retrieval/confuser "
            "surfaces. R2 on RD patterns is unresolved; do not assume typed "
            "receipts transfer from primitive ops to pattern deployment until "
            "an action/auditability endpoint tests that directly."
            " V177/V177R family-balanced downstream-action tests: GP-216 labels "
            "were weak by themselves; GP-219-style typed fields paid because "
            "they carried source-bound action constraints. Schema slots helped "
            "some, but delabeled action-constraint values matched full typed "
            "fields. Therefore field names are routing support; the "
            "evidence carrier is the action-constraint content plus confuser "
            "separation."
            " The 2026-05-23 hard evidence-shop endpoint is a surface-design "
            "ceiling/null: on the same nine V35 cases, V35 had typed=9/9, "
            "generic=5/9, placebo=2/9, while the evidence-shop prompt moved "
            "all arms to 9/9 by exposing the missing action family through "
            "the proposed-update/check-menu surface. RD briefs must require "
            "the action target to be inferred from source facts, not supplied "
            "by the task wording."
            " The 2026-05-23 paired-confuser pattern-contract endpoint shows the matching failure mode for orchestration patterns and anti-patterns: source-only and two-label-menu rows still ceilinged, but confuser contracts routed `6/6` outputs to the wrong family and `0/6` to the expected family. Wrong receipt fields are active steering surfaces, not harmless labels; require source_contract_alignment_check before accepting the routed operator receipt. The 2026-05-24 execution-artifact endpoint gives the current positive Track 2b result: action-label selection ceilinged, but surfacing the actual contract schema improved required-field coverage from 0.2292 to 1.00 in the artifact-only follow-up. Treat this module as an artifact-field compiler and confuser guard, not proof that the menu beats vanilla first-action routing. The 2026-05-24 anti-pattern pre-mortem pilot adds a separate mechanics-positive result: catalog snippets improved pre-outcome failure-family and preventive-action accuracy from 2/4 to 4/4, with confuser rejection present. Surface anti-patterns as preventive gate/artifact requirements, not decorative warnings. The 2026-05-24 three-axis Track 2b tests split patterns, menu, and anti-patterns: pattern contracts improved downstream consumer execution coverage (0.5583 to 0.9083) and pass rate (0.25 to 1.00), and the harder downstream-consumer handoff plus second-stage consumer tests improved pass rate from 0.00 to 0.6667 and field recovery/coverage from 0.1444 to 1.00 while not improving next-action accuracy; a naturalistic NS trace consumer test then showed contract-plus-evidence recovered RD carrier slots and problem surfaces at 1.00 vs 0.00 for evidence-only while both arms preserved confusers, so routed contracts should include a downstream_consumer_check but should not be sold as action-choice or mathematical-insight improvements; deterministic menu-memory recurrence screening was positive only for memory_plus_menu, but the live transparent-packet and cue-stripped reruns did not show incremental gain over memory or menu-only context; menu surfaces should be treated as sequencing on top of project memory rather than standalone routing, with no live improvement claim and no more short-packet menu tests unless naturalistic traces are available; the hard-negative anti-pattern packet ceilinged on block/proceed while catalog improved family naming (0.80 to 1.00), so anti-pattern guards must include a clean_proceed_condition and minimal preventive artifact to avoid block-everything skepticism. The cue-stripped anti-pattern missing-field test then separated catalog value from generic critique: catalog improved missing-field accuracy from 0.50 to 1.00 and family accuracy from 0.00 to 0.50 with no false-stop increase, so hard-residual anti-pattern guards should require the exact missing-or-paid preventive receipt plus nearest-confuser rejection. The 2026-05-24 naturalistic catch-ledger test did not add a positive Axis C result: catalog context matched evidence-only family accuracy (0.875), only slightly improved repair specificity (0.375 to 0.45), and reduced source-confuser recovery (0.4583 to 0.0) because outputs often rejected a neighboring catalog family rather than the concrete false interpretation in the source. Therefore anti-pattern guards must require a source_specific_false_reading_confuser in addition to any catalog-family confuser. H52 adds a fair bounded boundary-card repair trace after H48/H51: rejected cards repaired with source observation plus non-oracle gate results reached 1.0 downstream action/terminal accuracy with no false proceed/stop on the six-card packet; use boundary_card_repair_trace.py for live repair-loop measurement, not broad auto-execution. H45 validates a deterministic boundary-card gate on the held-out H29 card packet with synthetic mutations: wrong-card catch rate 0.9583 and correct-card false-block rate 0.0. Use `src/ztare/research_director/boundary_card_gate.py` for card shape/action-program validation before downstream action; it is not a semantic verifier for every source phrase. The 2026-05-24 B production-trace readiness audit found 0/131 official transitions ready for a corrected menu shadow-controller test because candidate_action, pre-decision markers, owed-artifact fields, and cost/regret signals were sparse; add only non-blocking orchestration_shadow_controller_log instrumentation, not enforcement. The 2026-05-24 mixed naturalistic anti-pattern test then showed evidence-only already ceilinged on decision, receipt, and source-confuser recovery, so the source-confuser contract is a safety/recording requirement rather than proven incremental model uplift on transparent naturalistic rows. The 2026-05-24 synthetic closed-loop anti-pattern intervention test adds the current stateful Axis C positive: anti-pattern contracts reduced mean episode cost from 8.5714 to 3.5714, improved per-leg action accuracy from 0.375 to 0.875, raised receipt accuracy from 0.6875 to 1.00, eliminated paid-clean overwork (0.25 to 0.00), and prevented repeated wrong moves after feedback (1.00 to 0.00), while source-confuser accuracy tied. Therefore hard-residual anti-pattern guards should record intervention_feedback_trace across repair/proceed legs, but this remains synthetic evidence rather than production uplift. The 2026-05-24 B/C interaction follow-on failed to show incremental value from combining the orchestration menu with the anti-pattern contract on the same closed-loop episodes: combined beat menu-only but underperformed the anti-pattern contract reference. Keep menu instrumentation separate from anti-pattern intervention obligations unless production traces show incremental gain. The H20 neutral/wrong-contract ablation strengthens the Axis C mechanism: the correct H18 anti-pattern contract beat neutral structure and wrong anti-pattern mappings on action accuracy and cost, while neutral structure could still name source confusers. The useful unit is the failure-family-to-preventive-receipt/action/payment mapping plus feedback trace, not generic checklist wording. H21 naturalistic delayed replay gives directional but failed support: the contract improved action, cost, receipt, and confuser metrics on real catch/transition material, but increased false stops on paid-clean rows. Add paid_clean_terminal_action so source narrowing, non-relapse, and defer receipts terminate in proceed rather than repeated verification or downgrade. H22 tested that repair and it failed on the same naturalistic delayed replay: cost and false stops improved, but action/source-confuser/terminal accuracy fell and paid-clean overwork did not improve. Treat paid_clean_terminal_action as a required record field, not a solved behavior; the remaining need is typed paid/unpaid boundary-state extraction. H23 corpus edge-confuser decomposition over the external V70 rows supports the orchestration edge unit under non-internal controls: correct_edge beat neutral/no_carrier by 0.25, wrong_edge trailed correct_edge by 0.5833, and wrong-choice delta was 0.5833. For menu/shadow instrumentation, record selected_residual_edge, rejected_nearest_confuser_edge, and edge_source_evidence; do not surface a menu edge without source-bound confuser separation. H24 external corpus boundary-state replay gives a directional but failed typed-boundary result: typed_boundary_contract improved action accuracy by 0.5714 and reduced cost by 39.06%, but failed safety because false_stop increased by 0.0714 on a paid proxy-benefit case. Record typed_boundary_state, but do not treat prompt-level boundary typing as solved terminal behavior. H25 external corpus boundary-preprocessor card fixes that failure in the same replay: action and terminal accuracy reached 1.00, false proceed and false stop were 0.00, and the CPS1 paid-narrow/unpaid-mechanism split was handled correctly. Surface boundary_preprocessor_card fields (paid_receipt, unpaid_receipt, permitted_update, blocked_update, next_action_rule); this proves action use of a structured card, not automatic extraction from raw sources. H26 then failed automatic extraction: mean field coverage was 0.5918, downstream action accuracy fell to 0.2143, and false proceed rose to 0.1429 because the extractor overused paid_narrow_boundary_with_unpaid_mechanism for unpaid or paid-negative cases. Require boundary_card_source_alignment_check before treating an extracted card as usable. H27 model-only boundary-card validation improved action accuracy from 0.2143 to 0.5714 but failed safety, with false proceed 0.0714 and field coverage 0.7347; a free-form validator is not an enforcement checker. H28 rule-backed validation then reached 0.8571 action accuracy and 0.9592 field coverage but narrowly missed threshold due to a brittle normalized cue. H28R repaired only the term-by-term/term by term source-cue match and recovered H25 performance exactly on the same packet: action accuracy 1.00, terminal accuracy 1.00, false proceed 0.00, false stop 0.00, field coverage 1.00. Therefore boundary cards should be treated as compiler IR: raw model parsing is insufficient, model-only validation is partial, and same-packet deterministic source-cue typechecking is promising but requires held-out cue-family validation before any universal parser claim. H29 then supplied held-out cue-family support across robotics, education, privacy/compliance, hiring fairness, materials discovery, wearable health, social media inference, and software reliability: deterministic rule-compiled cards beat model extraction by +0.4375 action accuracy, cut mean cost by 50%, reached field coverage 1.0, and kept false proceed/stop at 0.0. The remaining H29 misses were backend sequence-order errors despite correct card fields. H30 fixed that by compiling next_action_rule into action_program, current_action_index, required_next_action, and program_counter_rule: action accuracy and terminal accuracy reached 1.0, mean cost fell from 2.875 to 1.25, and false proceed/stop stayed 0.0. For multi-step boundary cards, require executable action-program fields; natural-language next-action rules alone are not enough. H31 tests the same compiler shape on Axis B orchestration menu routing: compiled_menu_program reached 1.0 action accuracy and 1.0 terminal accuracy, while menu_label_only had 0.5 action accuracy and 0.125 terminal accuracy despite high edge accuracy. The mechanism is program-counter execution: labels and source-only outputs often named the edge but repeated prerequisites or swapped terminal actions. Therefore orchestration menu surfaces should record selected_residual_edge, rejected_nearest_confuser_edge, edge_source_evidence, orchestration_action_program, current_action_index, required_next_action, and program_counter_rule; label-only menu prompting is not the active unit. H32-H34 test automatic compilation on a six-case external/synthetic packet. H32 free-form program synthesis failed: action accuracy 0.3333, worse than source-only 0.4167, with program exact rate 0.0. H33 typed residual-class selection plus deterministic lowering improved to 0.6667 but introduced false proceed 0.0833. H34 added source-cue check bits before lowering and matched hand-compiled reference: action and terminal accuracy 1.0, false proceed/stop 0.0, accepted class/program exact 1.0 despite requested class accuracy 0.8333. H35 then ablated controller burden on the same packet: compact checked contracts matched full checked contracts at 1.0 action and terminal accuracy, while class-only contracts fell to 0.4167 action accuracy and 0.0 terminal accuracy. H36 tested ten external-style synthetic rows with four outside-menu blockers: open_set_checked_compiler reached 1.0 accepted-class, program, action, and terminal accuracy, while closed_set_checked_compiler had 0.0 open-set accept accuracy and 0.7 action accuracy. H37 open-set specificity then showed that naming specific outside residual classes beat generic outside routing: open_specific_outside reached 1.0 class accuracy and 1.0 outside-specific accuracy, while closed_known_menu had 0.3571 class accuracy and forced known classes on 0.5 of outside rows. The raw compiler stress associate found typed no-cue compilation transfers better than free-form classing (0.875 vs 0.375 class accuracy) but weakly constrained action-program generation remains unreliable (program exact 0.25), so deterministic lowering remains mandatory. The wrong-contract associate found plausible wrong compact contracts forced the wrong family on 0.375 of rows; adding source-alignment fields reduced forced wrong-family to 0.0 and raised wrong-contract reject/repair to 1.0. H40 corrected end-to-end pipeline was positive: corrected_checked_pipeline reached 1.0 action and terminal accuracy versus 0.1667 source-only and 0.5417 raw free-form program pipeline, while raw free-form still had only 0.25 program exactness. H41 larger outside corpus was not a clean pass: open_specific_outside kept outside-specific accuracy at 1.0 but in-support accuracy fell to 0.75, so outside-specific expansion should be known-class-first/two-stage, not a flat expanded menu. H42 subtle wrong-contract robustness was negative for alignment sufficiency: source alignment increased explicit conflict mentions but did not improve action or repair accuracy over subtle wrong contracts; alignment alone is not enough, so add program-order and stop-condition checks rather than relying on alignment prose alone. Automatic orchestration compilation should therefore log requested_residual_class, accepted_residual_class, source_cue_check_status, source_cue_receipts, missing_source_cues, open_set_refusal_status, specific_outside_residual_class, source_contract_alignment_check, wrong_contract_repair_or_refusal, and deterministic lowering result for audit, but expose compact execution fields to RD agents; free-form program synthesis, class-only control, closed-menu forcing, and unchecked wrong-contract obedience should remain disallowed outside experiments."
        ),
        kernel_action_schemas=kernel_action_schemas,
    )


def write_pattern_action_contract(
    *,
    scope: str | None = None,
    goal: str | None = None,
    out_path: Path = OUT_PATH,
) -> PatternActionContract:
    contract = build_pattern_action_contract(scope=scope, goal=goal)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(asdict(contract), indent=2) + "\n", encoding="utf-8")
    return contract


def render_contract_receipt(contract: PatternActionContract, out_path: Path) -> str:
    required_slots = [
        carrier.artifact_slot
        for carrier in contract.evidence_carriers
        if carrier.required
    ]
    return "\n".join(
        [
            f"wrote pattern action contract: {out_path}",
            f"problem_surfaces={','.join(contract.problem_surfaces) or 'none'}",
            f"pattern_chain={','.join(contract.pattern_chain[:5]) or 'none'}",
            "operator_card_routes="
            f"{render_operator_card_route_summary(contract.operator_card_routes)}",
            f"required_carriers={','.join(required_slots[:8]) or 'none'}",
            f"route_tests={len(contract.route_tests)}",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit a pattern-to-action contract for RD hard-residual work."
    )
    parser.add_argument("--scope", default=None)
    parser.add_argument("--goal", default=None)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="print the full JSON payload to stdout instead of a compact receipt",
    )
    args = parser.parse_args(argv)
    contract = write_pattern_action_contract(
        scope=args.scope,
        goal=args.goal,
        out_path=args.out,
    )
    if args.print_json:
        print(json.dumps(asdict(contract), indent=2))
    else:
        print(render_contract_receipt(contract, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
