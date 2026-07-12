from __future__ import annotations

from dataclasses import replace
from itertools import combinations
import json

import pytest

from ztare.common.leaf_workbench_environment import resolve_leaf_workbench_environment
from ztare.common.science_output_policy import INVESTIGATED_STAGNATION_K
from ztare.leanmill.deterministic_frontier_campaign import select_diverse_theory_nodes
from ztare.leanmill.finite_model_census import enumerate_magma_model_universe
from ztare.leanmill.finite_theory_context import build_formal_theory_context
from ztare.leanmill.frontier_blueprint import FrontierExplorationBrief
from ztare.leanmill.frontier_blueprint_compiler import compile_structure_first_blueprint
from ztare.leanmill.frontier_boundary import run_frontier_boundaries
from ztare.leanmill.exploration_budget import ExplorationBudgetLedger, budget_preset
from ztare.leanmill.magma_law_universe import anonymous_magma_signature, magma_laws_through_order
from ztare.leanmill.theory_campaign_journal import TheoryCampaignJournal
from ztare.leanmill.theory_navigator import (
    _prompt_trace_projection,
    prompt_trace_max_bytes,
    run_interactive_theory_navigator,
)
from ztare.leanmill.theory_interest import (
    theory_program_information_yield,
    theory_residual_information_yield,
)
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.typed_axiom_proposal import TypedAxiomProposal


def _context_and_blueprint():
    signature = anonymous_magma_signature()
    laws = magma_laws_through_order(2)
    context = build_formal_theory_context(
        signature=signature,
        formulas=tuple(row.axiom for row in laws),
        universe=enumerate_magma_model_universe(signature, carrier_sizes=(2,)),
    )
    draft = {
        "mode": "anonymous_signature_census", "eigenquestion": "Which pairs form joint closures?",
        "signature": signature.to_json(),
        "primitive_semantics": {"operation_bindings": {"op0": "finite table"}, "relation_bindings": {}},
        "base_axioms": (), "base_theory_status": "explicit_empty",
        "adapter_id": "magma_equational.v1", "adapter_config": {"max_total_operation_order": 2},
        "formula_grammar": {"max_order": 2},
        "model_or_observation_strata": ({"carrier_size": 2},), "pack_arity": 2,
        "collapse_controls": (), "visible_evidence_manifest": {},
        "sealed_evidence_manifest_digest": "sha256:" + "0" * 64,
        "deanchoring_policy": {"cold": True},
        "navigator_contract": {"selection_mode": "compact_axiom_pack"},
        "query_budget": {"max_finalists": 2}, "stop_rule": {}, "verification_plan": {},
        "codec_versions": {}, "authority_refs": ("authority",),
    }
    blueprint = compile_structure_first_blueprint(
        FrontierExplorationBrief(direction="Explore.", source_mode="structure_first"), draft
    )
    return context, blueprint


def test_interactive_navigator_uses_workbench_then_freezes(tmp_path):
    context, blueprint = _context_and_blueprint()
    chosen = select_diverse_theory_nodes(context, max_finalists=1)[0]
    pair = next(row for row in chosen.minimal_generators if len(row) == 2 and context.synergy_ids(row))
    decisions = iter(
        [
            {"decision": "request", "capability_id": "list_theory_nodes@v1", "input_refs": {"offset": 0, "limit": 8}, "rationale": "inspect the broad topology"},
            {"decision": "request", "capability_id": "inspect_formula_profiles", "input_refs": {"formula_ids": list(pair)}, "rationale": "inspect the proposed basis structure"},
            {"decision": "freeze", "formula_ids": list(pair), "rationale": "independent pair with conjunction-only closure"},
            {"decision": "finish", "rationale": "one calibrated finalist is enough for this bounded run"},
        ]
    )
    result = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "events.jsonl"),
        agent_fn=lambda _prompt: next(decisions),
        attempt_id="attempt-1",
        campaign_id="campaign-1",
        max_rounds=6,
        max_finalists=2,
    )
    assert result["cold_view"] is True
    assert result["finalists"][0]["formula_ids"] == sorted(pair)
    assert result["finalists"][0]["joint_only_consequence_ids"]
    assert result["finalists"][0]["residual_joint_only_consequence_ids"]
    assert result["provider_calls"] == 4


def test_navigator_ranks_boundary_questions_and_host_preserves_that_choice(tmp_path):
    context, blueprint = _context_and_blueprint()
    pair, signal = next(
        (row, signal)
        for row in combinations(context.formula_ids, 2)
        if len(
            (signal := theory_residual_information_yield(context, row)).residual_consequence_ids
        )
        >= 2
        and context.incidence.extent_bits(row).bit_count() >= 2
        and all(
            context.independence_witness(row, formula) is not None
            for formula in row
        )
    )
    ranked_targets = list(reversed(signal.residual_consequence_ids[:2]))
    decisions = iter(
        [
            {
                "decision": "request",
                "capability_id": "select_theory_presentation",
                "input_refs": {"formula_ids": list(pair)},
                "formula_ids": None,
                "boundary_target_ids": None,
                "rationale": "Preview the residual questions before choosing spend.",
            },
            {
                "decision": "freeze",
                "capability_id": None,
                "input_refs": {},
                "formula_ids": list(pair),
                "boundary_target_ids": ranked_targets,
                "rationale": "Test these two residual questions in this order.",
            },
            {
                "decision": "finish",
                "capability_id": None,
                "input_refs": {},
                "formula_ids": None,
                "boundary_target_ids": None,
                "rationale": "The ranked finalist is frozen.",
            },
        ]
    )
    navigation = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "ranked.events.jsonl"),
        agent_fn=lambda _prompt: next(decisions),
        attempt_id="attempt-ranked",
        campaign_id="campaign-ranked",
        max_rounds=4,
    )
    finalist = navigation["finalists"][0]
    assert finalist["boundary_target_ids"] == ranked_targets
    assert finalist["boundary_selection_authority"] == "anonymous_theory_navigator"

    result = run_frontier_boundaries(
        context,
        blueprint,
        navigation,
        TheoryCampaignJournal(tmp_path / "ranked-boundary.events.jsonl"),
        ExplorationBudgetLedger(
            tmp_path / "ranked-budget.events.jsonl",
            budget_preset("smoke_20m"),
            attempt_id="attempt-ranked",
        ),
        attempt_id="attempt-ranked",
        campaign_id="campaign-ranked",
    )
    assert [row["target_formula_id"] for row in result.query_results] == ranked_targets


def test_theory_program_mode_does_not_require_joint_only_pack_synergy(tmp_path):
    context, blueprint = _context_and_blueprint()
    blueprint = replace(
        blueprint,
        navigator_contract={
            **blueprint.navigator_contract,
            "selection_mode": "theory_program",
            "presentation_size": {"minimum": 2, "maximum": 2},
        },
    )
    pair, program = next(
        (row, program)
        for row in combinations(context.formula_ids, 2)
        if not theory_residual_information_yield(
            context, row
        ).residual_consequence_ids
        and (program := theory_program_information_yield(context, row)).residual_prediction_ids
        and context.incidence.extent_bits(row).bit_count() > 0
    )
    target = program.residual_prediction_ids[0]
    decisions = iter(
        [
            {
                "decision": "request",
                "capability_id": "select_theory_presentation",
                "input_refs": {"formula_ids": list(pair)},
                "rationale": "Preview all consequences of this theory program.",
            },
            {
                "decision": "freeze",
                "formula_ids": list(pair),
                "boundary_target_ids": [target],
                "rationale": "Test a residual prediction without requiring every premise.",
            },
            {"decision": "finish", "rationale": "The theory program is frozen."},
        ]
    )

    result = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "program.events.jsonl"),
        agent_fn=lambda _prompt: next(decisions),
        attempt_id="attempt-program",
        campaign_id="campaign-program",
        max_rounds=4,
    )

    finalist = result["finalists"][0]
    assert finalist["candidate_kind"] == "theory_program"
    assert finalist["boundary_target_ids"] == [target]
    assert target in finalist["residual_prediction_formula_ids"]
    assert target not in finalist["residual_joint_only_consequence_ids"]
    ablation = finalist["prediction_profile"]["predictions"][0][
        "premise_ablation"
    ]
    assert {row["removed_formula_id"] for row in ablation} == set(pair)
    assert all(row["status"].endswith("_without_premise") for row in ablation)

    boundary = run_frontier_boundaries(
        context,
        blueprint,
        result,
        TheoryCampaignJournal(tmp_path / "program-boundary.events.jsonl"),
        ExplorationBudgetLedger(
            tmp_path / "program-budget.events.jsonl",
            budget_preset("smoke_20m"),
            attempt_id="attempt-program",
        ),
        attempt_id="attempt-program",
        campaign_id="campaign-program",
    )
    assert boundary.query_results[0]["target_formula_id"] == target
    assert boundary.query_results[0]["candidate_kind"] == "theory_program"
    assert boundary.query_results[0]["pack_synergy_status"] == (
        "not_claimed_theory_program"
    )


def test_seed_counterexample_returns_theory_program_to_search(
    tmp_path,
):
    context, blueprint = _context_and_blueprint()
    blueprint = replace(
        blueprint,
        navigator_contract={
            **blueprint.navigator_contract,
            "selection_mode": "theory_program",
            "presentation_size": {"minimum": 1, "maximum": 2},
        },
    )
    presentation, target = next(
        ((formula_id,), target_id)
        for formula_id in context.formula_ids
        for target_id in context.formula_ids
        if target_id != formula_id
        and not theory_program_information_yield(
            context, (formula_id,)
        ).residual_prediction_ids
        and target_id not in context.closure_ids((formula_id,))
    )
    decisions = iter(
        [
            {
                "decision": "freeze",
                "formula_ids": list(presentation),
                "boundary_target_ids": [target],
                "rationale": "Freeze a falsifiable prediction rather than a chart-selected consequence.",
            },
            {
                "decision": "reject_all",
                "rationale": "The exact chart already refutes the inspected program.",
            },
        ]
    )

    navigation = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "agent-prediction.events.jsonl"),
        agent_fn=lambda _prompt: next(decisions),
        attempt_id="attempt-agent-prediction",
        campaign_id="campaign-agent-prediction",
        max_rounds=3,
    )
    assert navigation["finalists"] == []
    rejected = navigation["reject_all_receipt"]["rejected_candidates"][0]
    assert rejected["reason"] == "theory_program_prediction_refuted_in_context"
    assert rejected["prediction_profile"]["predictions"][0]["chart_status"] == (
        "refuted_in_context"
    )


def test_theory_program_refusal_is_agent_owned_and_host_assessed(tmp_path):
    context, blueprint = _context_and_blueprint()
    blueprint = replace(
        blueprint,
        navigator_contract={
            **blueprint.navigator_contract,
            "selection_mode": "theory_program",
            "presentation_size": {"minimum": 1, "maximum": 2},
        },
    )
    presentation = (context.formula_ids[0],)
    target = next(row for row in context.formula_ids if row not in presentation)
    decisions = iter(
        [
            {
                "decision": "reject_candidate",
                "formula_ids": list(presentation),
                "boundary_target_ids": [target],
                "rationale": "The nominated prediction fails on an existing anonymous witness.",
            },
            {
                "decision": "reject_all",
                "rationale": "No inspected program survives its named discriminator.",
            },
        ]
    )

    result = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "program-refusal.events.jsonl"),
        agent_fn=lambda _prompt: next(decisions),
        attempt_id="attempt-program-refusal",
        campaign_id="campaign-program-refusal",
        max_rounds=3,
    )
    receipt = result["reject_all_receipt"]
    assert receipt["schema"] == "leanmill.receipted_reject_all.v2"
    rejected = receipt["rejected_candidates"][0]
    assert rejected["rejection_authority"] == "anonymous_theory_navigator"
    assert rejected["prediction_profile"]["authority"] == (
        "host_semantic_diagnostic_only"
    )


def test_theory_program_breadth_comes_from_blueprint_not_size_two_default(tmp_path):
    context, blueprint = _context_and_blueprint()
    blueprint = replace(
        blueprint,
        pack_arity=3,
        navigator_contract={
            **blueprint.navigator_contract,
            "selection_mode": "theory_program",
            "presentation_size": {"minimum": 3, "maximum": 3},
        },
    )
    presentation, program = next(
        (row, program)
        for row in combinations(context.formula_ids, 3)
        if (program := theory_program_information_yield(context, row)).residual_prediction_ids
        and context.incidence.extent_bits(row).bit_count() > 0
    )
    target = program.residual_prediction_ids[0]
    decisions = iter(
        [
            {
                "decision": "freeze",
                "formula_ids": list(presentation),
                "boundary_target_ids": [target],
                "rationale": "Freeze the three-formula theory program.",
            },
            {"decision": "finish", "rationale": "The program is frozen."},
        ]
    )

    result = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "wide-program.events.jsonl"),
        agent_fn=lambda _prompt: next(decisions),
        attempt_id="attempt-wide-program",
        campaign_id="campaign-wide-program",
        max_rounds=3,
    )

    assert len(result["finalists"][0]["formula_ids"]) == 3
    assert result["finalists"][0]["boundary_target_ids"] == [target]


def test_optional_verifier_caps_skip_later_target_without_stopping_campaign(tmp_path):
    context, blueprint = _context_and_blueprint()
    pair, signal = next(
        (row, signal)
        for row in combinations(context.formula_ids, 2)
        if len(
            (signal := theory_residual_information_yield(context, row)).residual_consequence_ids
        )
        >= 2
    )
    targets = list(signal.residual_consequence_ids[:2])
    blueprint = replace(
        blueprint,
        verification_plan={
            "conditional_isabelle": True,
            "isabelle_timeout_ms": 1_000,
            "conditional_lean": True,
            "lean_timeout_ms": 1_000,
        },
    )
    calls = {"isabelle": 0, "lean": 0}

    def isabelle_executor(task, *, timeout_s):
        calls["isabelle"] += 1
        core = {
            "schema": "leanmill.isabelle_theory_attempt.v1",
            "task_id": task.task_id,
            "status": "proved",
            "transport_calls": 1,
            "diagnostics": "test peer accepted",
        }
        return {**core, "receipt_sha256": content_hash(core)}

    def lean_executor(task, *, budget_ledger):
        calls["lean"] += 1
        core = {
            "schema": "leanmill.governed_consequence_attempt.v1",
            "task_id": task.task_id,
            "status": "proved_attributed",
            "reason": "test kernel accepted",
        }
        return {**core, "receipt_sha256": content_hash(core)}

    result = run_frontier_boundaries(
        context,
        blueprint,
        {
            "finalists": [
                {
                    "formula_ids": list(pair),
                    "residual_joint_only_consequence_ids": targets,
                    "boundary_target_ids": targets,
                }
            ]
        },
        TheoryCampaignJournal(tmp_path / "optional-cap.events.jsonl"),
        ExplorationBudgetLedger(
            tmp_path / "optional-cap-budget.events.jsonl",
            budget_preset("smoke_20m"),
            attempt_id="attempt-optional-cap",
        ),
        attempt_id="attempt-optional-cap",
        campaign_id="campaign-optional-cap",
        isabelle_executor_fn=isabelle_executor,
        lean_executor_fn=lean_executor,
    )

    assert result.stop_reason == "campaign_finished"
    assert calls == {"isabelle": 1, "lean": 1}
    assert result.query_results[0]["formal_consensus"]["status"] == "corroborated"
    assert result.query_results[1]["isabelle"]["status"] == "skipped_budget_exhausted"
    assert result.query_results[1]["lean"]["status"] == "skipped_budget_exhausted"


def test_navigator_receives_only_replayed_safe_conflict_projection(tmp_path):
    context, blueprint = _context_and_blueprint()
    chosen = select_diverse_theory_nodes(context, max_finalists=1)[0]
    pair = next(
        row
        for row in chosen.minimal_generators
        if len(row) == 2
        and theory_residual_information_yield(context, row).residual_consequence_ids
    )
    prompts_seen = []
    decisions = iter(
        [
            {
                "decision": "freeze",
                "formula_ids": list(pair),
                "rationale": "Freeze a candidate distinct from recalled failures.",
            },
            {"decision": "finish", "rationale": "One finalist is sufficient."},
        ]
    )

    def agent(prompt):
        prompts_seen.append(prompt)
        return next(decisions)

    result = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "conflict-memory.events.jsonl"),
        agent_fn=agent,
        attempt_id="attempt-conflict-memory",
        campaign_id="campaign-conflict-memory",
        max_rounds=3,
        prior_conflict_rows=(
            {
                "candidate_signature": "theory-presentation:deadbeef",
                "context_hash": context.context_hash,
                "witness_ref": "selection:1",
                "witness_summary": "zero residual after bounded baseline",
                "conflict_kind": "zero_residual_presentation",
            },
        ),
    )

    assert result["prior_conflict_count"] == 1
    assert all("prior_witnessed_conflict_memory" in prompt for prompt in prompts_seen)
    assert all("witness_payload" not in prompt for prompt in prompts_seen)


def test_workbench_output_identity_does_not_masquerade_as_scientific_yield(
    tmp_path,
):
    context, blueprint = _context_and_blueprint()
    chosen = select_diverse_theory_nodes(context, max_finalists=1)[0]
    pair = next(
        row
        for row in chosen.minimal_generators
        if len(row) == 2 and context.synergy_ids(row)
    )
    signal = theory_residual_information_yield(context, pair)
    ledger = ExplorationBudgetLedger(
        tmp_path / "identity-vs-yield.events.jsonl",
        budget_preset("smoke_20m"),
        attempt_id="attempt-identity-vs-yield",
    )
    decisions = iter(
        [
            {
                "decision": "request",
                "capability_id": "list_theory_nodes",
                "input_refs": {"offset": 0, "limit": 8},
                "rationale": "Inspect topology.",
            },
            {
                "decision": "freeze",
                "formula_ids": list(pair),
                "rationale": "Freeze the measured candidate.",
            },
            {"decision": "finish", "rationale": "One finalist is enough."},
        ]
    )

    run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "identity-vs-yield.journal.jsonl"),
        agent_fn=lambda _prompt: next(decisions),
        attempt_id="attempt-identity-vs-yield",
        campaign_id="campaign-identity-vs-yield",
        budget_ledger=ledger,
        max_rounds=4,
    )

    observations = ledger.state()["information"]
    assert len(observations) == 1
    assert observations[0]["action_id"].endswith(":freeze")
    assert observations[0]["marginal_information_per_cost_ppm"] == round(
        signal.coordinates.information_per_cost * 1_000_000
    )


def test_two_law_campaign_cannot_freeze_a_singleton(tmp_path):
    context, blueprint = _context_and_blueprint()
    blueprint = replace(
        blueprint,
        navigator_contract={
            **blueprint.navigator_contract,
            "presentation_size": {"minimum": 2, "maximum": 2},
        },
    )
    singleton = context.formula_ids[0]

    with pytest.raises(ValueError, match="campaign presentation size"):
        run_interactive_theory_navigator(
            context,
            blueprint,
            TheoryCampaignJournal(tmp_path / "arity.events.jsonl"),
            agent_fn=lambda _prompt: {
                "decision": "freeze",
                "formula_ids": [singleton],
                "rationale": "Try a one-law presentation.",
            },
            attempt_id="attempt-arity",
            campaign_id="campaign-arity",
            max_rounds=1,
        )


def test_navigator_can_request_a_typed_formula_epoch_instead_of_forcing_a_nomination(
    tmp_path,
):
    context, blueprint = _context_and_blueprint()

    def propose(prompt):
        assert "formula grammar is an orientation seed" in prompt
        assert "`propose_frontier_formula` is legitimate" in prompt
        assert "`show_indistinguishable_objects`" in prompt
        assert "`contrast_object_ids`" in prompt
        return {
            "decision": "request",
            "capability_id": "propose_frontier_formula",
            "input_refs": {
                "structural_conjecture": "The seed band omits ternary bracketing.",
                "axiom_name": "assoc_candidate",
                "variables": [
                    {"name": "x0", "sort": "sort_0"},
                    {"name": "x1", "sort": "sort_0"},
                    {"name": "x2", "sort": "sort_0"},
                ],
                "lhs_tokens": ["x0", "x1", "op_0", "x2", "op_0"],
                "rhs_tokens": ["x0", "x1", "x2", "op_0", "op_0"],
                "nl_intent": "The binary operation is associative.",
                "kill_condition": "A finite table separates the bracketings.",
            },
            "rationale": "Add one typed distinction instead of selecting a weak seed pair.",
        }

    result = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "formula-epoch.events.jsonl"),
        agent_fn=propose,
        attempt_id="attempt-expand",
        campaign_id="campaign-expand",
        max_rounds=2,
    )

    expansion = result["expansion_proposal"]
    proposal = TypedAxiomProposal.from_json(expansion["typed_axiom_proposal"])
    assert result["finalists"] == []
    assert expansion["formula_id"] not in context.formula_ids
    assert proposal.axiom.name == "assoc_candidate"
    assert any(
        event.event_type == "navigator_action_executed"
        for event in TheoryCampaignJournal(
            tmp_path / "formula-epoch.events.jsonl"
        ).replay()
    )


def test_navigator_continues_after_host_rejects_malformed_formula_move(tmp_path):
    context, blueprint = _context_and_blueprint()
    chosen = select_diverse_theory_nodes(context, max_finalists=1)[0]
    pair = next(
        row
        for row in chosen.minimal_generators
        if len(row) == 2 and context.synergy_ids(row)
    )
    decisions = iter(
        [
            {
                "decision": "request",
                "capability_id": "propose_frontier_formula",
                "input_refs": {
                    "structural_conjecture": "Test the typed action boundary.",
                    "axiom_name": "bad_quantifier_order",
                    "variables": [{"name": "x0", "sort": "sort_0"}],
                    "formula_tokens": ["exists:x0", "x0", "x0", "op_0", "eq"],
                    "nl_intent": "Probe a malformed postfix move.",
                    "kill_condition": "The host rejects the move without changing context.",
                },
                "rationale": "First exercise the host rejection receipt.",
            },
            {
                "decision": "freeze",
                "formula_ids": list(pair),
                "rationale": "Continue with the measured fallback candidate.",
            },
            {"decision": "finish", "rationale": "The fallback candidate is frozen."},
        ]
    )
    result = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "malformed-move.events.jsonl"),
        agent_fn=lambda _prompt: next(decisions),
        attempt_id="attempt-malformed-move",
        campaign_id="campaign-malformed-move",
        max_rounds=4,
    )

    assert len(result["finalists"]) == 1
    assert any(
        row.get("receipt", {}).get("output_summary", {}).get("status")
        == "rejected_invalid_typed_formula"
        for row in result["trace"]
    )


def test_navigator_receipts_unknown_formula_reference_without_campaign_crash(tmp_path):
    context, blueprint = _context_and_blueprint()
    chosen = select_diverse_theory_nodes(context, max_finalists=1)[0]
    pair = next(
        row
        for row in chosen.minimal_generators
        if len(row) == 2 and context.synergy_ids(row)
    )
    decisions = iter(
        [
            {
                "decision": "request",
                "capability_id": "select_theory_presentation",
                "input_refs": {
                    "formula_ids": ["base_formula:" + context.formula_ids[0]],
                    "prediction_formula_ids": [],
                },
                "rationale": "Probe an identifier from the model's external naming view.",
            },
            {
                "decision": "freeze",
                "formula_ids": list(pair),
                "rationale": "Continue with a host-valid fallback presentation.",
            },
            {"decision": "finish", "rationale": "The fallback is frozen."},
        ]
    )
    result = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "unknown-reference.events.jsonl"),
        agent_fn=lambda _prompt: next(decisions),
        attempt_id="attempt-unknown-reference",
        campaign_id="campaign-unknown-reference",
        max_rounds=4,
    )

    assert len(result["finalists"]) == 1
    assert any(
        row.get("receipt", {}).get("output_summary", {}).get("status")
        == "rejected_invalid_action"
        for row in result["trace"]
    )


def test_navigator_continues_after_rejected_language_request(tmp_path):
    context, blueprint = _context_and_blueprint()
    chosen = select_diverse_theory_nodes(context, max_finalists=1)[0]
    pair = next(
        row
        for row in chosen.minimal_generators
        if len(row) == 2 and context.synergy_ids(row)
    )
    decisions = iter(
        [
            {
                "decision": "request",
                "capability_id": "propose_theory_language_expansion",
                "input_refs": {
                    "change_kind": "not_a_registered_change",
                    "blind_spot": "The typed language is insufficient.",
                    "proposed_interface": "A new executable observation.",
                    "evidence_refs": [context.object_ids[0]],
                    "discriminating_test": "Separate the displayed pair.",
                    "kill_condition": "Reject if the observation is not executable.",
                },
                "rationale": "Probe the language-request rejection path.",
            },
            {
                "decision": "freeze",
                "formula_ids": list(pair),
                "rationale": "Continue with a host-valid fallback presentation.",
            },
            {"decision": "finish", "rationale": "The fallback is frozen."},
        ]
    )
    result = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "language-reject.events.jsonl"),
        agent_fn=lambda _prompt: next(decisions),
        attempt_id="attempt-language-reject",
        campaign_id="campaign-language-reject",
        max_rounds=4,
    )

    assert len(result["finalists"]) == 1
    assert any(
        row.get("receipt", {}).get("output_summary", {}).get("status")
        == "rejected_invalid_language_request"
        for row in result["trace"]
    )


def test_navigator_can_request_a_new_theory_language_without_mutating_context(
    tmp_path,
):
    context, blueprint = _context_and_blueprint()
    evidence_ref = context.object_ids[0]

    def request_language(prompt):
        assert "`propose_theory_language_expansion`" in prompt
        return {
            "decision": "request",
            "capability_id": "propose_theory_language_expansion",
            "input_refs": {
                "change_kind": "new_relation",
                "blind_spot": "Current equations alias structures with different orbit reachability.",
                "proposed_interface": "A typed binary reachability relation with executable finite semantics.",
                "evidence_refs": [evidence_ref],
                "discriminating_test": "The relation separates one displayed same-stratum object pair.",
                "kill_condition": "The proposed relation has an old truth profile or cannot be lowered.",
            },
            "rationale": "The distinction is not expressible as an equation in the frozen signature.",
        }

    result = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "language.events.jsonl"),
        agent_fn=request_language,
        attempt_id="attempt-language",
        campaign_id="campaign-language",
        max_rounds=2,
        epoch=0,
    )

    request = result["language_expansion_request"]
    assert result["finalists"] == []
    assert request["source_context_hash"] == context.context_hash
    assert request["source_epoch"] == 0
    assert request["authority"] == "proposal_only"
    assert "reject_all_receipt" not in result


def test_formula_authored_after_freeze_becomes_outbound_epoch_request(tmp_path):
    context, blueprint = _context_and_blueprint()
    pair = next(
        row
        for row in combinations(context.formula_ids, 2)
        if (
            theory_residual_information_yield(context, row).residual_consequence_ids
            and context.incidence.extent_bits(row).bit_count() >= 2
            and all(context.independence_witness(row, formula) for formula in row)
        )
    )
    decisions = iter(
        [
            {
                "decision": "freeze",
                "formula_ids": list(pair),
                "rationale": "Freeze the measured source-epoch finalist.",
            },
            {
                "decision": "request",
                "capability_id": "propose_frontier_formula",
                "input_refs": {
                    "structural_conjecture": "Test the two ternary bracketings.",
                    "axiom_name": "deferred_assoc_candidate",
                    "variables": [
                        {"name": "x0", "sort": "sort_0"},
                        {"name": "x1", "sort": "sort_0"},
                        {"name": "x2", "sort": "sort_0"},
                    ],
                    "lhs_tokens": ["x0", "x1", "op_0", "x2", "op_0"],
                    "rhs_tokens": ["x0", "x1", "x2", "op_0", "op_0"],
                    "nl_intent": "The operation is associative.",
                    "kill_condition": "A finite table separates the bracketings.",
                },
                "rationale": "Receipt the next coordinate for a successor epoch.",
            },
        ]
    )

    result = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "deferred-expansion.events.jsonl"),
        agent_fn=lambda _prompt: next(decisions),
        attempt_id="attempt-deferred-expansion",
        campaign_id="campaign-deferred-expansion",
        max_rounds=2,
    )

    assert result["finalists"][0]["formula_ids"] == sorted(pair)
    assert result["expansion_proposal"]["formula_id"] not in context.formula_ids
    assert result["expansion_proposal"]["source_context_hash"] == context.context_hash


def test_navigator_can_invent_a_coordinate_from_an_anonymous_object_contrast(
    tmp_path,
):
    _full_context, blueprint = _context_and_blueprint()
    signature = anonymous_magma_signature()
    context = build_formal_theory_context(
        signature=signature,
        formulas=tuple(row.axiom for row in magma_laws_through_order(1)),
        universe=enumerate_magma_model_universe(signature, carrier_sizes=(2,)),
    )
    environment = resolve_leaf_workbench_environment("axiompack", context=context)
    pair = environment["action_handlers"]["show_indistinguishable_objects"](
        ".",
        {"input_refs": {"offset": 0, "limit": 1}},
        None,
        environment["contract"],
    )["output_summary"]["pairs"][0]["object_ids"]
    turns = 0

    def refine(prompt):
        nonlocal turns
        turns += 1
        if turns == 1:
            return {
                "decision": "request",
                "capability_id": "show_indistinguishable_objects",
                "input_refs": {"offset": 0, "limit": 1},
                "rationale": "Ask which structures the current language aliases.",
            }
        assert "finite_structure" in prompt
        return {
            "decision": "request",
            "capability_id": "propose_frontier_formula",
            "input_refs": {
                "structural_conjecture": "A diagonal iterate separates the pair.",
                "axiom_name": "contrastive_diagonal_candidate",
                "variables": [{"name": "x0", "sort": "sort_0"}],
                "lhs_tokens": ["x0"],
                "rhs_tokens": ["x0", "x0", "x0", "op_0", "op_0"],
                "nl_intent": "A three-occurrence diagonal iterate fixes each element.",
                "kill_condition": "The displayed objects have the same truth value.",
                "contrast_object_ids": pair,
            },
            "rationale": "Add the shortest visible separator.",
        }

    result = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "contrast.events.jsonl"),
        agent_fn=refine,
        attempt_id="attempt-contrast",
        campaign_id="campaign-contrast",
        max_rounds=3,
    )

    assert result["expansion_proposal"]["contrast_refinement"]["object_ids"] == pair
    assert turns == 2


def test_navigator_can_receipt_reject_all_without_freezing_junk(tmp_path):
    context, blueprint = _context_and_blueprint()
    pair = next(
        row
        for row in combinations(context.formula_ids, 2)
        if (
            (signal := theory_residual_information_yield(context, row))
            and signal.joint_only_consequence_ids
            and not signal.residual_consequence_ids
            and context.incidence.extent_bits(row).bit_count() >= 2
            and all(
                context.independence_witness(row, formula) is not None
                for formula in row
            )
        )
    )
    expected_baseline_ref = theory_residual_information_yield(
        context, pair
    ).coordinates.baseline_ref
    decisions = iter(
        [
            {
                "decision": "freeze",
                "formula_ids": list(pair),
                "rationale": "Test this conjunction against the host baseline.",
            },
            {
                "decision": "reject_all",
                "rationale": "The named baseline exhausts the inspected candidate.",
            },
        ]
    )

    result = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "events.jsonl"),
        agent_fn=lambda _prompt: next(decisions),
        attempt_id="attempt-reject",
        campaign_id="campaign-reject",
        max_rounds=4,
    )

    assert result["finalists"] == []
    receipt = result["reject_all_receipt"]
    assert receipt["rejected_candidate_count"] == 1
    coordinates = receipt["rejected_candidates"][0]["residual_yield"]
    assert coordinates["baseline_ref"] == expected_baseline_ref
    assert coordinates["identification_bits"] == 0.0
    assert coordinates["residual_ids"] == []
    assert result["provider_calls"] == 2
    assert any(
        event.event_type == "navigator_reject_all"
        for event in TheoryCampaignJournal(tmp_path / "events.jsonl").replay()
    )


def test_preview_then_finish_is_recoverable_and_requires_explicit_freeze(tmp_path):
    context, blueprint = _context_and_blueprint()
    chosen = select_diverse_theory_nodes(context, max_finalists=1)[0]
    pair = next(
        row
        for row in chosen.minimal_generators
        if len(row) == 2
        and theory_residual_information_yield(context, row).residual_consequence_ids
    )
    decisions = iter(
        [
            {
                "decision": "request",
                "capability_id": "select_theory_presentation",
                "input_refs": {"formula_ids": list(pair)},
                "rationale": "Preview the host validation before retaining it.",
            },
            {
                "decision": "finish",
                "rationale": "The preview looked acceptable.",
            },
            {
                "decision": "freeze",
                "formula_ids": list(pair),
                "rationale": "Explicitly retain the previewed residual presentation.",
            },
            {
                "decision": "finish",
                "rationale": "One frozen finalist is enough.",
            },
        ]
    )

    result = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "preview.events.jsonl"),
        agent_fn=lambda _prompt: next(decisions),
        attempt_id="attempt-preview",
        campaign_id="campaign-preview",
        max_rounds=6,
    )

    assert len(result["finalists"]) == 1
    assert any(row["decision"] == "finish_rejected" for row in result["trace"])


def test_reject_all_receipt_surfaces_shared_stagnation_bound():
    from ztare.leanmill.theory_navigator import (
        _receipted_reject_all,
        reject_all_sequence_receipt,
    )

    class Context:
        context_hash = "context:test"

    row = {
        "node_id": "node:test",
        "selection_receipt_id": "receipt:test",
        "residual_synergy_formula_ids": [],
        "residual_yield": {
            "baseline_ref": "baseline:test.v1",
            "identification_bits": 0.0,
            "residual_ids": [],
        },
    }
    receipts = [
        _receipted_reject_all(Context(), [row], reason=f"test:{index}")
        for index in range(INVESTIGATED_STAGNATION_K)
    ]
    sequence = reject_all_sequence_receipt(receipts)
    assert sequence["stagnation_k"] == INVESTIGATED_STAGNATION_K
    assert sequence["consecutive_reject_all_count"] == INVESTIGATED_STAGNATION_K
    assert sequence["stagnation_pressure"] is True

    with pytest.raises(ValueError, match="named baseline"):
        _receipted_reject_all(
            Context(),
            [{**row, "residual_yield": {"identification_bits": 0.0, "residual_ids": []}}],
            reason="test",
        )


def test_navigator_prompt_trace_projection_is_bounded_without_mutating_receipts():
    rows = [
        {
            "round": index,
            "decision": "request",
            "receipt": {
                "receipt_id": f"receipt:{index}",
                "output_summary": {
                    "formula_profiles": [
                        {"formula_id": f"formula:{row}", "formula": "x" * 2400}
                        for row in range(80)
                    ]
                },
            },
        }
        for index in range(12)
    ]
    projected = _prompt_trace_projection(rows)
    assert len(json.dumps(projected, sort_keys=True, separators=(",", ":"))) <= prompt_trace_max_bytes()
    assert rows[0]["receipt"]["output_summary"]["formula_profiles"][0]["formula"] == "x" * 2400


def test_completed_call_recovery_replays_host_receipt_without_dispatch(tmp_path):
    from ztare.leanmill.frontier_campaign_runner import (
        _replay_navigator_decisions,
    )

    context, _blueprint = _context_and_blueprint()
    chosen = select_diverse_theory_nodes(context, max_finalists=1)[0]
    pair = next(row for row in chosen.minimal_generators if len(row) == 2)
    role_dir = tmp_path / "navigator"
    role_dir.mkdir()
    results = [
        {
            "decision": "request",
            "capability_id": "select_theory_presentation",
            "input_refs": {"formula_ids": list(pair)},
            "formula_ids": None,
            "rationale": "Preview this presentation.",
        },
        {
            "decision": "finish",
            "capability_id": None,
            "input_refs": {},
            "formula_ids": None,
            "rationale": "The preview is a finalist.",
        },
    ]
    for index, result in enumerate(results):
        result_text = json.dumps(result)
        prefix = role_dir / f"{index:03d}"
        prefix.with_suffix(".result.json").write_text(result_text, encoding="utf-8")
        prefix.with_suffix(".call.json").write_text(
            json.dumps(
                {
                    "returncode": 0,
                    "result_digest": content_hash({"result": result_text}),
                }
            ),
            encoding="utf-8",
        )

    navigation = _replay_navigator_decisions(
        context,
        _blueprint,
        results,
        TheoryCampaignJournal(tmp_path / "events.jsonl"),
        attempt_id=tmp_path.name,
        campaign_id="campaign:test",
        epoch=0,
    )

    assert navigation["trace"][0]["receipt"]["capability_id"] == (
        "select_theory_presentation"
    )
    assert navigation["trace"][1]["decision"] == "finish_rejected"
    assert navigation["navigation_exhausted_receipt"]["reason"] == (
        "round_or_soft_horizon_without_frozen_or_refused_candidate"
    )


def test_completed_formula_proposal_is_recovered_without_redispatch(tmp_path):
    from ztare.leanmill.frontier_campaign_runner import (
        _replay_navigator_decisions,
    )

    context, blueprint = _context_and_blueprint()
    role_dir = tmp_path / "navigator"
    role_dir.mkdir()
    result = {
        "decision": "request",
        "capability_id": "propose_frontier_formula",
        "input_refs": {
            "structural_conjecture": "The seed band omits ternary bracketing.",
            "axiom_name": "assoc_candidate",
            "variables": [
                {"name": "x0", "sort": "sort_0"},
                {"name": "x1", "sort": "sort_0"},
                {"name": "x2", "sort": "sort_0"},
            ],
            "lhs_tokens": ["x0", "x1", "op_0", "x2", "op_0"],
            "rhs_tokens": ["x0", "x1", "x2", "op_0", "op_0"],
            "nl_intent": "The binary operation is associative.",
            "kill_condition": "A finite table separates the bracketings.",
        },
        "formula_ids": None,
        "rationale": "Expand the typed context.",
    }
    result_text = json.dumps(result)
    prefix = role_dir / "000"
    prefix.with_suffix(".result.json").write_text(result_text, encoding="utf-8")
    prefix.with_suffix(".call.json").write_text(
        json.dumps(
            {
                "returncode": 0,
                "result_digest": content_hash({"result": result_text}),
            }
        ),
        encoding="utf-8",
    )

    navigation = _replay_navigator_decisions(
        context,
        blueprint,
        [result],
        TheoryCampaignJournal(tmp_path / "events.jsonl"),
        attempt_id=tmp_path.name,
        campaign_id="campaign:test",
        epoch=0,
    )

    assert navigation["trace"][0]["receipt"]["output_summary"]["status"] == (
        "proposed_new_formula"
    )
    pending_expansion = navigation["expansion_proposal"]
    assert pending_expansion["source_epoch"] == 0
    proposal = TypedAxiomProposal.from_json(
        pending_expansion["typed_axiom_proposal"]
    )
    assert proposal.axiom.name == "assoc_candidate"


def test_terminal_durable_trace_replays_finalist_and_successor_request(tmp_path):
    from ztare.leanmill.frontier_campaign_runner import (
        _read_durable_navigator_decisions,
        _replay_navigator_decisions,
    )

    context, blueprint = _context_and_blueprint()
    chosen = select_diverse_theory_nodes(context, max_finalists=1)[0]
    pair = next(
        row
        for row in chosen.minimal_generators
        if len(row) == 2
        and theory_residual_information_yield(context, row).residual_consequence_ids
    )
    decisions = [
        {
            "decision": "freeze",
            "formula_ids": list(pair),
            "rationale": "Freeze the source-epoch finalist.",
        },
        {
            "decision": "request",
            "capability_id": "propose_frontier_formula",
            "input_refs": {
                "structural_conjecture": "The seed band omits ternary bracketing.",
                "axiom_name": "successor_assoc_candidate",
                "variables": [
                    {"name": "x0", "sort": "sort_0"},
                    {"name": "x1", "sort": "sort_0"},
                    {"name": "x2", "sort": "sort_0"},
                ],
                "lhs_tokens": ["x0", "x1", "op_0", "x2", "op_0"],
                "rhs_tokens": ["x0", "x1", "x2", "op_0", "op_0"],
                "nl_intent": "The operation is associative.",
                "kill_condition": "A finite table separates the bracketings.",
            },
            "rationale": "Freeze a successor-epoch coordinate.",
        },
    ]
    role_dir = tmp_path / "agent_calls" / "navigator"
    role_dir.mkdir(parents=True)
    for index, decision in enumerate(decisions):
        result_text = json.dumps(decision)
        prefix = role_dir / f"{index:03d}"
        prefix.with_suffix(".result.json").write_text(result_text, encoding="utf-8")
        prefix.with_suffix(".call.json").write_text(
            json.dumps(
                {
                    "returncode": 0,
                    "provider_call_charge": 1,
                    "result_digest": content_hash({"result": result_text}),
                }
            ),
            encoding="utf-8",
        )

    calls, durable_decisions = _read_durable_navigator_decisions(role_dir)
    navigation = _replay_navigator_decisions(
        context,
        blueprint,
        durable_decisions,
        TheoryCampaignJournal(tmp_path / "events.jsonl"),
        attempt_id=tmp_path.name,
        campaign_id="campaign:test",
        epoch=0,
    )

    assert navigation["finalists"][0]["context_hash"] == context.context_hash
    assert navigation["expansion_proposal"]["source_context_hash"] == context.context_hash
    assert len(calls) == 2
    assert all(row["replayed"] is True for row in calls)


def test_navigator_materializes_a_finalist_when_the_next_turn_hits_its_cap(tmp_path):
    context, blueprint = _context_and_blueprint()
    chosen = select_diverse_theory_nodes(context, max_finalists=1)[0]
    pair = next(
        row
        for row in chosen.minimal_generators
        if len(row) == 2 and context.synergy_ids(row)
    )
    budget = budget_preset("smoke_20m")
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget,
        attempt_id="attempt-capped",
    )
    navigation_provider_cap = sum(
        budget.phase_caps[phase]["provider_calls"]
        for phase in ("compilation", "context", "navigation")
    )
    used = ledger.reserve(
        "prior-provider-use",
        "navigation",
        {"provider_calls": navigation_provider_cap - 1},
    )
    ledger.commit(used)
    decisions = iter(
        [
            {
                "decision": "freeze",
                "formula_ids": list(pair),
                "rationale": "independent pair with conjunction-only closure",
            }
        ]
    )

    result = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "events.jsonl"),
        agent_fn=lambda _prompt: next(decisions),
        attempt_id="attempt-capped",
        campaign_id="campaign-capped",
        max_rounds=4,
        max_finalists=2,
        budget_ledger=ledger,
    )

    assert len(result["finalists"]) == 1
    assert result["trace"][-1]["decision"] == "budget_stop"
    assert "navigation:provider_calls" in result["trace"][-1]["reason"]


def test_failed_agent_call_before_dispatch_consumes_no_provider_budget(tmp_path):
    context, blueprint = _context_and_blueprint()
    ledger = ExplorationBudgetLedger(
        tmp_path / "failed-call-budget.jsonl",
        budget_preset("smoke_20m"),
        attempt_id="attempt-failed-call",
    )

    class FailingAgent:
        call_count = 0

        def __call__(self, _prompt):
            raise ValueError("durable prompt mismatch before dispatch")

    with pytest.raises(ValueError, match="before dispatch"):
        run_interactive_theory_navigator(
            context,
            blueprint,
            TheoryCampaignJournal(tmp_path / "failed-call.events.jsonl"),
            agent_fn=FailingAgent(),
            attempt_id="attempt-failed-call",
            campaign_id="campaign-failed-call",
            budget_ledger=ledger,
        )

    assert ledger.state()["usage"]["provider_calls"] == 0
    assert ledger.state()["usage"]["agent_turns"] == 0


def test_host_action_at_round_horizon_remains_pending_for_leaf_judgment(tmp_path):
    context, blueprint = _context_and_blueprint()
    result = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "pending.events.jsonl"),
        agent_fn=lambda _prompt: {
            "decision": "request",
            "capability_id": "list_theory_nodes",
            "input_refs": {"offset": 0, "limit": 1},
            "rationale": "Inspect one node before choosing the next move.",
        },
        attempt_id="attempt-pending",
        campaign_id="campaign-pending",
        max_rounds=1,
    )

    pending = result["pending_leaf_decision"]
    assert pending["capability_id"] == "list_theory_nodes"
    assert pending["receipt_id"].startswith("sha256:")
    assert result["trace"][-1]["decision"] == "pending_leaf_decision"
