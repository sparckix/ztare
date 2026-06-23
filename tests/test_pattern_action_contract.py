from dataclasses import replace
from pathlib import Path
from ztare.common.kernel_action_schema import validate_kernel_action_schema
from ztare.research_director import primitive_operator_cards
from ztare.research_director.pattern_action_contract import (
    build_pattern_action_contract,
    main,
)
from ztare.research_director.primitive_operator_cards import route_operator_cards


def test_hard_pde_formal_contract_forces_action_slots():
    contract = build_pattern_action_contract(
        scope="ns",
        goal="hard mathematical residual formal frontier PDE Duhamel estimate",
    )

    assert "hard_mathematical_residual" in contract.problem_surfaces
    assert "pde_estimate_or_carrier_residual" in contract.problem_surfaces
    assert "formal_frontier" in contract.problem_surfaces
    assert "OP-HRD-01:hard_residual_research_contract" in contract.pattern_chain
    assert "OP-PDE-01:pde_estimate_or_carrier_contract" in contract.pattern_chain
    assert "PATTERN-028:recursive_tool_depth_loop" in contract.pattern_chain
    assert "ANTI-PATTERN-018:tool_underuse_formal_satisficing" in contract.anti_patterns
    assert "ANTI-PATTERN-014:premature_settled_negative" in contract.anti_patterns
    assert "ANTI-PATTERN-013:lean_closure_laundering" in contract.anti_patterns

    required_slots = {
        carrier.artifact_slot
        for carrier in contract.evidence_carriers
        if carrier.required
    }
    assert {
        "orientation_artifact",
        "stress_test_artifact",
        "operator_receipt_gate_artifact",
        "anti_pattern_guard_artifact",
        "artifact_ref",
        "verification_artifact",
        "tool_pass_artifact",
        "estimate_attempt_artifact",
        "positive_constructor_attempt_artifact",
    } <= required_slots
    assert any("nearest confuser" in test for test in contract.route_tests)
    assert {
        "OP-HRD-01",
        "OP-PDE-01",
    } <= {route["card_id"] for route in contract.operator_card_routes}
    assert "V54/MM-V7/V55/MM-V8" in contract.evidence_basis
    assert "epistemic-generation/research_log.md" in contract.evidence_basis


def test_pattern_contract_exports_common_action_schemas_for_required_carriers():
    contract = build_pattern_action_contract(
        scope="general external residual",
        goal=(
            "use analogy and nearest-confuser checks to escape a stale "
            "thesis without only rewriting the wording"
        ),
    )

    required_carrier_count = sum(
        1 for carrier in contract.evidence_carriers if carrier.required
    )
    assert len(contract.kernel_action_schemas) == required_carrier_count

    analogy_action = next(
        action
        for action in contract.kernel_action_schemas
        if action["verification_artifact"] == "analogy_receipt_artifact"
    )
    ok, missing = validate_kernel_action_schema(analogy_action)
    assert ok is True
    assert missing == []
    assert analogy_action["source_kind"] == "pattern_action_contract"
    assert analogy_action["action_family"] == "pattern_contract"
    assert analogy_action["action_name"] == "analogy_mapping_receipt"
    assert "target-side" in analogy_action["source_summary"]
    assert "nearest confuser" in analogy_action["nearest_confuser"].lower()


def test_general_contract_is_lightweight_when_no_hard_surface():
    contract = build_pattern_action_contract(
        scope="apparatus",
        goal="small mechanical documentation cleanup",
    )

    assert contract.problem_surfaces == ["general_research_task"]
    assert contract.evidence_carriers[0].required is False
    assert contract.kernel_action_schemas == []


def test_pattern_contract_records_operator_card_route_provenance(monkeypatch):
    semantic_card = replace(
        primitive_operator_cards.CARDS[0],
        score=91.0,
        matched_terms=("semantic:0.9100",),
    )
    monkeypatch.setattr(
        primitive_operator_cards,
        "route_operator_cards_semantic",
        lambda **_: [semantic_card],
    )

    contract = build_pattern_action_contract(
        scope="claim boundary",
        goal="narrow a broad claim with explicit answer object and success criterion",
    )

    assert contract.operator_card_routes == [
        {
            "card_id": semantic_card.card_id,
            "name": semantic_card.name,
            "score": 91.0,
            "matched_terms": ["semantic:0.9100"],
            "route_mode": "semantic_atlas",
        }
    ]
    gate = next(
        carrier
        for carrier in contract.evidence_carriers
        if carrier.artifact_slot == "operator_receipt_gate_artifact"
    )
    assert "operator_card_route_provenance" in gate.required_fields
    assert any(
        "semantic_atlas vs lexical_fallback" in test
        for test in contract.route_tests
    )


def test_cli_out_prints_compact_receipt_not_full_payload(tmp_path, capsys):
    out = tmp_path / "contract.json"

    rc = main([
        "--goal",
        "claim-boundary split with explicit answer object and success criterion",
        "--out",
        str(out),
    ])

    captured = capsys.readouterr()
    assert rc == 0
    assert out.exists()
    assert "wrote pattern action contract:" in captured.out
    assert "problem_surfaces=" in captured.out
    assert "operator_card_routes=" in captured.out
    assert "OP-CBM-01" in captured.out
    assert "evidence_basis" not in captured.out


def test_cli_print_json_preserves_full_payload(tmp_path, capsys):
    out = tmp_path / "contract.json"

    rc = main([
        "--goal",
        "hard residual with stale repeated branches",
        "--out",
        str(out),
        "--print-json",
    ])

    captured = capsys.readouterr()
    assert rc == 0
    assert out.exists()
    assert '"evidence_basis"' in captured.out


def test_autoresearch_workbench_surface_uses_typed_card_and_contract():
    cards = route_operator_cards(
        context=(
            "Research Director deciding in-loop autoresearch workbench vs "
            "out-of-loop subscription agent for a bounded claim with rubric surface"
        ),
        top_n=1,
    )

    assert cards
    assert cards[0].card_id == "OP-AWR-01"

    contract = build_pattern_action_contract(
        scope="agentic workbench boundary",
        goal=(
            "route RD manual agent work against autoresearch workbench with "
            "hypothesis projection and action intelligence logging"
        ),
    )

    assert "autoresearch_workbench_routing" in contract.problem_surfaces
    assert "OP-AWR-01:autoresearch_workbench_routing" in contract.pattern_chain
    carrier = next(
        carrier
        for carrier in contract.evidence_carriers
        if carrier.artifact_slot == "autoresearch_workbench_routing_artifact"
    )
    assert carrier.required is True
    assert {
        "workbench_router_decision",
        "worker_metadata",
        "route_json_ref",
        "action_impact_ref",
        "workbench_evidence_ref",
    } <= set(carrier.required_fields)


def test_reflexive_mining_surface_requires_measurement_receipt():
    cards = route_operator_cards(
        context=(
            "Use reflexive mining, primitive ROI, bifurcation, and operations "
            "intelligence to decide whether abandoned projects or kernel work "
            "deserve attention."
        ),
        top_n=1,
    )

    assert cards
    assert cards[0].card_id == "OP-RMI-01"

    contract = build_pattern_action_contract(
        scope="reflexive mining portfolio audit",
        goal=(
            "inspect primitive ROI, in-loop share, out-of-loop share, P0 metrics, "
            "and operations intelligence before deciding the kernel roadmap"
        ),
    )

    assert "reflexive_mining_instrument_check" in contract.problem_surfaces
    assert "autoresearch_workbench_routing" not in contract.problem_surfaces
    assert "OP-RMI-01:reflexive_mining_instrument_check" in contract.pattern_chain
    assert "OP-AWR-01:autoresearch_workbench_routing" not in contract.pattern_chain
    carrier = next(
        carrier
        for carrier in contract.evidence_carriers
        if carrier.artifact_slot == "reflexive_mining_instrument_artifact"
    )
    assert {
        "portfolio_question",
        "source_refs",
        "metric_name",
        "metric_value",
        "freshness_or_scope_note",
        "decision_consequence",
        "falsifier",
        "next_action",
    } <= set(carrier.required_fields)
    assert "activity volume alone" in carrier.acceptance_check


def test_route_row_coverage_gap_is_reflexive_instrument_not_workbench_route():
    contract = build_pattern_action_contract(
        scope="operations intelligence portfolio audit",
        goal=(
            "high out-of-loop share with missing agentic-workbench route rows; "
            "decide whether to backfill route rows or continue kernel work"
        ),
    )

    assert "reflexive_mining_instrument_check" in contract.problem_surfaces
    assert "autoresearch_workbench_routing" not in contract.problem_surfaces
    assert "OP-RMI-01:reflexive_mining_instrument_check" in contract.pattern_chain


def test_graph_context_requires_graph_carrier_and_action_lowering():
    contract = build_pattern_action_contract(
        scope="graph diagnostic carrier",
        goal=(
            "use a context graph with PageRank, min-cut, graph disagreement, "
            "and probability DAG steering to select the next artifact"
        ),
    )

    assert "graph_diagnostic_carrier" in contract.problem_surfaces
    assert "OP-GDC-01:graph_diagnostic_carrier" in contract.pattern_chain
    carrier = next(
        carrier
        for carrier in contract.evidence_carriers
        if carrier.artifact_slot == "graph_carrier_artifact"
    )
    assert {
        "graph_id",
        "graph_kind",
        "diagnostics",
        "decision_receipt",
        "selected_action_card_or_gate",
        "non_use_or_retraction",
    } <= set(carrier.required_fields)
    assert any("standard-library" in test for test in contract.route_tests)


def test_pde_only_contract_still_requires_receipt_gate():
    contract = build_pattern_action_contract(
        scope="ns",
        goal="nonadaptive source selection receipt for reserve matching",
    )

    assert "pde_estimate_or_carrier_residual" in contract.problem_surfaces
    assert any(
        carrier.artifact_slot == "operator_receipt_gate_artifact"
        for carrier in contract.evidence_carriers
    )


def test_surplus_lift_projection_surface_requires_certificate():
    contract = build_pattern_action_contract(
        scope="hard mathematical residual",
        goal=(
            "use a high-dimensional ambient lift with entropy surplus over "
            "quotient loss, then project back with injective multiplicity"
        ),
    )

    assert "surplus_loss_projection_certificate" in contract.problem_surfaces
    assert "broad_07:dimensional_lifting" in contract.pattern_chain
    assert any(
        carrier.artifact_slot == "surplus_projection_artifact"
        for carrier in contract.evidence_carriers
    )
    assert any("constants and selection rules fixed" in test for test in contract.route_tests)
    assert any("target-size" in test for test in contract.route_tests)
    assert "unit-distance proof read" in contract.evidence_basis


def test_claim_boundary_surface_requires_action_constraint_rows():
    contract = build_pattern_action_contract(
        scope="primitive catalog refinement",
        goal=(
            "claim-boundary split for an overclaim: broad claim may fail but a "
            "narrow claim survives only with explicit answer object and success criterion"
        ),
    )

    assert "claim_boundary_schema_receipt" in contract.problem_surfaces
    assert "OP-CBM-01:claim_boundary_mutation" in contract.pattern_chain
    assert any(
        route["card_id"] == "OP-CBM-01"
        for route in contract.operator_card_routes
    )
    assert any(
        carrier.artifact_slot == "claim_boundary_schema_artifact"
        for carrier in contract.evidence_carriers
    )
    assert any("action-constraint broad/narrow claim rows" in test for test in contract.route_tests)
    carrier = next(
        carrier
        for carrier in contract.evidence_carriers
        if carrier.artifact_slot == "claim_boundary_schema_artifact"
    )
    assert {
        "claim_kind",
        "answer_object",
        "success_criterion",
        "permitted_status",
        "pass_fail_boundary",
    } <= set(carrier.required_fields)
    assert carrier.schema_mode == "artifact_ref_or_action_constraint_fields"
    assert "answer_object" in carrier.acceptance_check
    assert "success_criterion" in carrier.acceptance_check
    assert "broad row is BLOCKED" in carrier.acceptance_check
    assert "narrow row is PERMITTED" in carrier.acceptance_check
    assert "V98/V99" in contract.evidence_basis


def test_meta_language_surface_requires_edge_carrier_not_label():
    contract = build_pattern_action_contract(
        scope="mm_02 mm_03 research arm",
        goal=(
            "quotient surface wording to an evidence-path graph, then promote "
            "the live residual into the causal edge that selects the required check"
        ),
    )

    assert "meta_language_edge_carrier" in contract.problem_surfaces
    assert "OP-MME-01:meta_language_edge_carrier" in contract.pattern_chain
    assert "mm_02:surface_quotient_to_evidence_path_graph" in contract.pattern_chain
    assert "mm_03:promote_live_residual_edge" in contract.pattern_chain
    assert any(
        route["card_id"] == "OP-MME-01"
        for route in contract.operator_card_routes
    )
    assert any(
        carrier.artifact_slot == "meta_language_edge_artifact"
        for carrier in contract.evidence_carriers
    )
    assert any("causal edge" in test for test in contract.route_tests)
    carrier = next(
        carrier
        for carrier in contract.evidence_carriers
        if carrier.artifact_slot == "meta_language_edge_artifact"
    )
    assert {
        "observed_state",
        "candidate_edge",
        "required_check",
        "forbidden_sibling",
        "stop_rule",
    } <= set(carrier.required_fields)
    assert "observed_state" in carrier.acceptance_check
    assert "required_check" in carrier.acceptance_check
    assert "forbidden_sibling" in carrier.acceptance_check
    assert "mm label alone" in carrier.acceptance_check
    assert "hard_mathematical_residual" not in contract.problem_surfaces
    assert "MM-V19/MM-V20" in contract.evidence_basis


def test_portable_estimate_receipt_surface_is_schema_not_pde_only():
    contract = build_pattern_action_contract(
        scope="general external residual",
        goal=(
            "use a pec_a auxiliary object or pec_e failure witness outside "
            "PDE, then reject the nearest confuser with typed receipt fields"
        ),
    )

    assert "portable_estimate_receipt_schema" in contract.problem_surfaces
    assert "OP-PER-01:portable_estimate_receipt_schema" in contract.pattern_chain
    assert any(
        route["card_id"] == "OP-PER-01"
        for route in contract.operator_card_routes
    )
    carrier = next(
        carrier
        for carrier in contract.evidence_carriers
        if carrier.artifact_slot == "portable_estimate_receipt_artifact"
    )
    assert {
        "selected_receipt_family",
        "action_constraint_fields",
        "typed_fields_filled",
        "nearest_confuser",
        "decision_consequence",
    } <= set(carrier.required_fields)
    assert any("portable receipt form" in test for test in contract.route_tests)
    assert any("action-constraint content" in test for test in contract.route_tests)
    assert "action-constraint fields" in carrier.acceptance_check
    assert "artifact existence" in carrier.acceptance_check
    assert "V111 portable-receipt causal triad" in contract.evidence_basis
    assert "V177/V177R" in contract.evidence_basis
    assert "action-constraint content" in contract.evidence_basis
    assert "ANTI-PATTERN-003:vocabulary_smuggling" in contract.anti_patterns
    assert "ANTI-PATTERN-016:vocabulary_smuggling" not in contract.anti_patterns

def test_action_target_source_guard_from_evidence_shop_ceiling():
    contract = build_pattern_action_contract(
        scope="primitive catalog refinement",
        goal="pec_a auxiliary object with nearest confuser and action-constraint fields",
    )

    gate = next(
        carrier
        for carrier in contract.evidence_carriers
        if carrier.artifact_slot == "operator_receipt_gate_artifact"
    )
    assert "action_target_source" in gate.required_fields
    assert "source_contract_alignment_check" in gate.required_fields
    assert "downstream_consumer_check" in gate.required_fields
    assert any("action target inferred from source facts" in test for test in contract.route_tests)
    assert any("downstream consumer check" in test for test in contract.route_tests)
    assert any("pull the output toward a nearest-confuser contract" in test for test in contract.route_tests)
    assert "hard evidence-shop endpoint" in contract.evidence_basis
    assert "paired-confuser pattern-contract endpoint" in contract.evidence_basis
    assert "typed=9/9" in contract.evidence_basis

def test_confuser_pressure_does_not_route_to_pde_without_pde_context():
    contract = build_pattern_action_contract(
        scope="causal_primitives",
        goal=(
            "free construction endpoint: infer action target from source facts, "
            "no proposed update, no check menu, compare typed contract vs generic "
            "vs placebo under nearest-confuser pressure"
        ),
    )

    assert "pde_estimate_or_carrier_residual" not in contract.problem_surfaces



def test_three_axis_evidence_updates_pattern_menu_antipattern_boundaries():
    contract = build_pattern_action_contract(
        scope="hard research residual",
        goal="avoid recurrence and scientific amnesia while preparing a downstream pattern handoff",
    )

    gate = next(
        carrier
        for carrier in contract.evidence_carriers
        if carrier.artifact_slot == "operator_receipt_gate_artifact"
    )
    anti_guard = next(
        carrier
        for carrier in contract.evidence_carriers
        if carrier.artifact_slot == "anti_pattern_guard_artifact"
    )
    assert "downstream_consumer_check" in gate.required_fields
    assert "clean_proceed_condition" in anti_guard.required_fields
    assert "minimal_preventive_artifact" in anti_guard.required_fields
    assert "missing_or_paid_preventive_receipt" in anti_guard.required_fields
    assert "typed_boundary_state" in anti_guard.required_fields
    assert "boundary_preprocessor_card" in anti_guard.required_fields
    assert "paid_receipt" in anti_guard.required_fields
    assert "unpaid_receipt" in anti_guard.required_fields
    assert "permitted_update" in anti_guard.required_fields
    assert "blocked_update" in anti_guard.required_fields
    assert "next_action_rule" in anti_guard.required_fields
    assert "boundary_card_action_program" in anti_guard.required_fields
    assert "boundary_card_current_action_index" in anti_guard.required_fields
    assert "boundary_card_required_next_action" in anti_guard.required_fields
    assert "boundary_card_program_counter_rule" in anti_guard.required_fields
    assert "boundary_card_source_alignment_check" in anti_guard.required_fields
    assert "boundary_card_source_cue_receipts" in anti_guard.required_fields
    assert "boundary_card_validation_status" in anti_guard.required_fields
    assert "boundary_card_rewrite_or_refusal_rule" in anti_guard.required_fields
    assert "boundary_card_gate_result" in anti_guard.required_fields
    assert "boundary_card_gate_cli" in anti_guard.required_fields
    assert "source_specific_false_reading_confuser" in anti_guard.required_fields
    assert "nearest_confuser_rejection" in anti_guard.required_fields
    assert "intervention_feedback_trace" in anti_guard.required_fields
    assert "paid_clean_terminal_action" in anti_guard.required_fields
    assert "source-specific false-reading confuser" in anti_guard.acceptance_check
    assert "naturalistic catch-ledger test" in contract.evidence_basis
    assert "0.875" in contract.evidence_basis
    assert "source-confuser recovery" in contract.evidence_basis
    assert "memory_plus_menu" in contract.evidence_basis
    assert "live transparent-packet" in contract.evidence_basis
    assert "cue-stripped reruns" in contract.evidence_basis
    assert "no more short-packet menu tests" in contract.evidence_basis
    assert "0.5583 to 0.9083" in contract.evidence_basis
    assert "0.00 to 0.6667" in contract.evidence_basis
    assert "second-stage consumer" in contract.evidence_basis
    assert "naturalistic NS trace consumer" in contract.evidence_basis
    assert "mathematical-insight improvements" in contract.evidence_basis
    assert "not improving next-action accuracy" in contract.evidence_basis
    assert "clean_proceed_condition" in contract.evidence_basis
    assert "missing-field accuracy from 0.50 to 1.00" in contract.evidence_basis
    assert "exact missing-or-paid preventive receipt" in contract.evidence_basis
    shadow = next(
        carrier
        for carrier in contract.evidence_carriers
        if carrier.artifact_slot == "orchestration_shadow_log_artifact"
    )
    assert shadow.required is False
    assert "candidate_action" in shadow.required_fields
    assert "cost_or_regret_signal" in shadow.required_fields
    assert "later_outcome_ref" in shadow.required_fields
    assert "selected_residual_edge" in shadow.required_fields
    assert "rejected_nearest_confuser_edge" in shadow.required_fields
    assert "edge_source_evidence" in shadow.required_fields
    assert "orchestration_active_controller_surface" in shadow.required_fields
    assert "orchestration_action_program" in shadow.required_fields
    assert "orchestration_current_action_index" in shadow.required_fields
    assert "orchestration_required_next_action" in shadow.required_fields
    assert "orchestration_program_counter_rule" in shadow.required_fields
    assert "orchestration_open_set_refusal_status" in shadow.required_fields
    assert "orchestration_new_residual_class_candidate" in shadow.required_fields
    assert "orchestration_specific_outside_residual_class" in shadow.required_fields
    assert "orchestration_known_class_first_check" in shadow.required_fields
    assert "orchestration_source_contract_alignment_check" in shadow.required_fields
    assert "orchestration_wrong_contract_repair_or_refusal" in shadow.required_fields
    assert "orchestration_deterministic_lowering_result" in shadow.required_fields
    assert "orchestration_program_order_check" in shadow.required_fields
    assert "orchestration_stop_condition_check" in shadow.required_fields
    assert "orchestration_requested_residual_class" in shadow.required_fields
    assert "orchestration_accepted_residual_class" in shadow.required_fields
    assert "orchestration_source_cue_check_status" in shadow.required_fields
    assert "orchestration_audit_surface_ref" in shadow.required_fields
    assert "orchestration_source_cue_receipts_ref" in shadow.required_fields
    assert "orchestration_missing_source_cues_ref" in shadow.required_fields
    assert "0/131 official transitions" in contract.evidence_basis
    assert "mixed naturalistic anti-pattern test" in contract.evidence_basis
    assert "synthetic closed-loop anti-pattern intervention test" in contract.evidence_basis
    assert "0.375 to 0.875" in contract.evidence_basis
    assert "paid-clean overwork" in contract.evidence_basis
    assert "B/C interaction follow-on failed" in contract.evidence_basis
    assert "underperformed the anti-pattern contract reference" in contract.evidence_basis
    assert "H20 neutral/wrong-contract ablation" in contract.evidence_basis
    assert "failure-family-to-preventive-receipt" in contract.evidence_basis
    assert "H21 naturalistic delayed replay" in contract.evidence_basis
    assert "paid_clean_terminal_action" in contract.evidence_basis
    assert "H22 tested that repair" in contract.evidence_basis
    assert "typed paid/unpaid boundary-state extraction" in contract.evidence_basis
    assert "H23 corpus edge-confuser decomposition" in contract.evidence_basis
    assert "correct_edge beat neutral/no_carrier by 0.25" in contract.evidence_basis
    assert "wrong_edge trailed correct_edge by 0.5833" in contract.evidence_basis
    assert "H24 external corpus boundary-state replay" in contract.evidence_basis
    assert "false_stop increased by 0.0714" in contract.evidence_basis
    assert "H25 external corpus boundary-preprocessor card" in contract.evidence_basis
    assert "action and terminal accuracy reached 1.00" in contract.evidence_basis
    assert "H26 then failed automatic extraction" in contract.evidence_basis
    assert "mean field coverage was 0.5918" in contract.evidence_basis
    assert "H27 model-only boundary-card validation" in contract.evidence_basis
    assert "field coverage 0.7347" in contract.evidence_basis
    assert "H28R repaired only" in contract.evidence_basis
    assert "action accuracy 1.00" in contract.evidence_basis
    assert "compiler IR" in contract.evidence_basis
    assert "H29 then supplied held-out cue-family support" in contract.evidence_basis
    assert "+0.4375 action accuracy" in contract.evidence_basis
    assert "H30 fixed that" in contract.evidence_basis
    assert "action_program" in contract.evidence_basis
    assert "H31 tests the same compiler shape" in contract.evidence_basis
    assert "menu_label_only had 0.5 action accuracy" in contract.evidence_basis
    assert "program-counter execution" in contract.evidence_basis
    assert "H32-H34 test automatic compilation" in contract.evidence_basis
    assert "free-form program synthesis failed" in contract.evidence_basis
    assert "H34 added source-cue check bits" in contract.evidence_basis
    assert "accepted class/program exact 1.0" in contract.evidence_basis
    assert "H35 then ablated controller burden" in contract.evidence_basis
    assert "compact checked contracts matched full checked contracts" in contract.evidence_basis
    assert "class-only contracts fell to 0.4167 action accuracy" in contract.evidence_basis
    assert "H36 tested ten external-style synthetic rows" in contract.evidence_basis
    assert "open_set_checked_compiler reached 1.0 accepted-class" in contract.evidence_basis
    assert "closed_set_checked_compiler had 0.0 open-set accept accuracy" in contract.evidence_basis
    assert "H37 open-set specificity" in contract.evidence_basis
    assert "open_specific_outside reached 1.0 class accuracy" in contract.evidence_basis
    assert "program exact 0.25" in contract.evidence_basis
    assert "forced the wrong family on 0.375" in contract.evidence_basis
    assert "wrong-contract reject/repair to 1.0" in contract.evidence_basis
    assert "H40 corrected end-to-end pipeline" in contract.evidence_basis
    assert "0.1667 source-only" in contract.evidence_basis
    assert "H41 larger outside corpus" in contract.evidence_basis
    assert "in-support accuracy fell to 0.75" in contract.evidence_basis
    assert "H42 subtle wrong-contract robustness" in contract.evidence_basis
    assert "alignment alone is not enough" in contract.evidence_basis


def test_pde_constructive_turn_slot_records_source_to_action_contract():
    contract = build_pattern_action_contract(
        scope="ns",
        goal="PDE high-interface conditional source law with bounded carrier",
    )

    carrier = next(
        carrier
        for carrier in contract.evidence_carriers
        if carrier.artifact_slot == "positive_constructor_attempt_artifact"
    )
    assert carrier.name == "constructive_turn_check"
    assert "conditional_source_law" in carrier.required_fields
    assert "constructor_map_or_why_not" in carrier.required_fields
    assert "nearest_confuser" in carrier.required_fields


def test_rd_brief_mentions_boundary_card_gate():
    brief = Path("scripts/public/control/rd_tick_brief.py").read_text(encoding="utf-8")

    assert "src.ztare.research_director.boundary_card_gate" in brief
