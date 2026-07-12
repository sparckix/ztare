from __future__ import annotations

from ztare.common.leaf_workbench_environment import resolve_leaf_workbench_environment
from ztare.leanmill.axiompack_leaf_workbench import decode_frontier_formula_proposal
from ztare.leanmill.explore_axiom_space import explore_axiom_space
from ztare.leanmill.frontier_blueprint import FrontierExplorationBrief
from ztare.leanmill.frontier_blueprint import frontier_objective_contract
from ztare.leanmill.theory_lineage_synthesis import (
    formula_lineage_request_id,
    lineage_synthesis_input,
    validate_lineage_synthesis_decision,
)
from ztare.leanmill.theory_navigator import run_interactive_theory_navigator

from test_explore_axiom_space import _draft, _signer


def test_late_objective_review_reopens_search_before_boundary(tmp_path):
    calls = []

    def navigator(context, blueprint, journal, *, budget_ledger):
        del journal, budget_ledger
        calls.append(context.context_hash)
        program = {
            "program_id": f"theory-program:{len(calls)}",
            "context_hash": context.context_hash,
        }
        aggregate = {
            "context_hash": context.context_hash,
            "context_epoch": 0,
            "finalists": [
                {
                    "node_id": f"node:{len(calls)}",
                    "theory_program": program,
                }
            ],
            "finalist_node_ids": [f"node:{len(calls)}"],
            "expansion_proposals": [],
            "theory_language_expansion_requests": [],
            "provider_calls": 0,
            "cold_view": True,
        }
        synthesis_input = lineage_synthesis_input(
            aggregate,
            objective_contract=frontier_objective_contract(blueprint),
        )
        route = "continue_search" if len(calls) == 1 else "proceed_boundary"
        synthesis = validate_lineage_synthesis_decision(
            synthesis_input,
            {
                "route": route,
                "selected_request_ids": [],
                "deferred_request_ids": [],
                "program_ids": [program["program_id"]],
                "next_discriminator_request_ids": [],
                "rationale": "The first program is a control; the second earns a boundary test.",
                "next_discriminator": "Author a coordinate outside the seed chart.",
                "kill_condition": "The next program remains seed-chart recoverable.",
            },
        )
        return {**aggregate, "lineage_synthesis": synthesis}

    navigator.accepts_budget_ledger = True
    draft = _draft()
    draft["navigator_contract"] = {
        **draft["navigator_contract"],
        "selection_mode": "theory_program",
    }
    instruction = "Continue until an authored coordinate changes the prediction frontier."
    draft["stop_rule"] = {
        **draft["stop_rule"],
        "user_instruction": instruction,
        "executable_condition": {"kind": "late_lineage_objective_review"},
    }

    run = explore_axiom_space(
        FrontierExplorationBrief(
            direction=instruction,
            source_mode="structure_first",
        ),
        attempt_dir=tmp_path / "attempt-objective-loop",
        typed_draft=draft,
        packet_signer=_signer(),
        navigator_fn=navigator,
        budget="smoke_20m",
    )

    assert len(calls) == 2
    assert run.status == "frontier_candidates_frozen_awaiting_boundary_approval"
    assert len(run.navigation["objective_review_history"]) == 1


def _formula_request(context, *, name, variables, lhs, rhs, lineage_id):
    env = resolve_leaf_workbench_environment(
        "axiompack",
        context=context,
        context_epoch=0,
        selection_mode="theory_program",
        max_presentation_size=2,
    )
    inputs = {
        "structural_conjecture": f"Test {name}.",
        "axiom_name": name,
        "variables": [
            {"name": variable, "sort": "sort_0"} for variable in variables
        ],
        "lhs_tokens": lhs,
        "rhs_tokens": rhs,
        "nl_intent": f"Test {name}.",
        "kill_condition": "A frozen finite structure refutes the coordinate.",
    }
    receipt = env["action_handlers"]["propose_frontier_formula"](
        ".", {"input_refs": inputs}, None, env["contract"]
    )
    proposal = decode_frontier_formula_proposal(context, inputs)
    expansion = {
        "source_context_hash": context.context_hash,
        "source_epoch": 0,
        "workbench_receipt_id": receipt["receipt_id"],
        "typed_axiom_proposal": proposal.to_json(),
        "typed_proposal_sha256": proposal.content_hash,
        "formula_id": receipt["output_summary"]["formula_id"],
        "navigator_rationale": f"Lineage proposed {name}.",
    }
    row = {"lineage_id": lineage_id, "proposal": expansion}
    return {**row, "request_id": formula_lineage_request_id(row)}


def test_late_agent_synthesis_admits_multiple_formulas_then_reopens_navigation(
    tmp_path,
):
    epochs = []

    def navigator(context, blueprint, journal, *, budget_ledger):
        epoch = int(getattr(navigator, "epoch", 0))
        if epoch == 0:
            requests = [
                _formula_request(
                    context,
                    name="assoc_candidate",
                    variables=("x0", "x1", "x2"),
                    lhs=["x0", "x1", "op_0", "x2", "op_0"],
                    rhs=["x0", "x1", "x2", "op_0", "op_0"],
                    lineage_id="lineage:a",
                ),
                _formula_request(
                    context,
                    name="medial_candidate",
                    variables=("x0", "x1", "x2", "x3"),
                    lhs=["x0", "x1", "op_0", "x2", "x3", "op_0", "op_0"],
                    rhs=["x0", "x2", "op_0", "x1", "x3", "op_0", "op_0"],
                    lineage_id="lineage:b",
                ),
            ]
            aggregate = {
                "context_hash": context.context_hash,
                "context_epoch": 0,
                "finalists": [],
                "finalist_node_ids": [],
                "expansion_proposals": requests,
                "theory_language_expansion_requests": [],
                "provider_calls": 0,
                "cold_view": True,
            }
            synthesis_input = lineage_synthesis_input(aggregate)
            selected = [row["request_id"] for row in requests]
            synthesis = validate_lineage_synthesis_decision(
                synthesis_input,
                {
                    "route": "admit_formulas",
                    "selected_request_ids": selected,
                    "deferred_request_ids": [],
                    "rationale": "Test the interaction between both coordinates.",
                    "next_discriminator": "Rebuild and inspect their joint closure.",
                    "kill_condition": "Neither coordinate adds a new finite profile.",
                    "program_ids": [],
                    "next_discriminator_request_ids": selected,
                },
            )
            return {**aggregate, "lineage_synthesis": synthesis}
        return run_interactive_theory_navigator(
            context,
            blueprint,
            journal,
            agent_fn=lambda _prompt: {
                "decision": "request",
                "capability_id": "propose_theory_language_expansion",
                "input_refs": {
                    "change_kind": "new_observable",
                    "blind_spot": "The rebuilt formula language still aliases objects.",
                    "proposed_interface": "One executable orbit observable.",
                    "evidence_refs": [context.object_ids[0]],
                    "discriminating_test": "The observable splits one remaining class.",
                    "kill_condition": "The observable duplicates the rebuilt partition.",
                },
                "rationale": "Escalate the remaining representation blind spot.",
            },
            attempt_id="attempt-lineage-synthesis",
            campaign_id="campaign:" + blueprint.blueprint_id.split(":", 1)[1][:24],
            budget_ledger=budget_ledger,
            epoch=epoch,
            max_rounds=2,
        )

    def begin_context_epoch(*, source_epoch, target_epoch):
        epochs.append((source_epoch, target_epoch))
        navigator.epoch = target_epoch

    navigator.accepts_budget_ledger = True
    navigator.begin_context_epoch = begin_context_epoch
    draft = _draft()
    draft["navigator_contract"] = {
        **draft["navigator_contract"],
        "selection_mode": "theory_program",
    }
    attempt = tmp_path / "attempt-lineage-synthesis"

    run = explore_axiom_space(
        FrontierExplorationBrief(
            direction="Invent and synthesize anonymous theory coordinates.",
            source_mode="structure_first",
        ),
        attempt_dir=attempt,
        typed_draft=draft,
        packet_signer=_signer(),
        navigator_fn=navigator,
        budget="smoke_20m",
    )

    assert epochs == [(0, 1)]
    assert run.status == "frontier_language_expansion_requested"
    assert run.context_summary["context_epoch"] == 1
    assert run.context_summary["agent_proposed_formula_count"] == 2
    assert len(tuple(attempt.glob("typed_formula_proposal.epoch-001.*.json"))) == 2
    assert run.navigation["language_expansion_request"]["source_epoch"] == 1
