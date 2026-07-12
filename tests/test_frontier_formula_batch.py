from __future__ import annotations

from ztare.common.leaf_workbench_environment import resolve_leaf_workbench_environment
from ztare.leanmill.axiompack_leaf_workbench import decode_frontier_formula_proposal
from ztare.leanmill.exploration_budget import ExplorationBudgetLedger, budget_preset
from ztare.leanmill.explore_axiom_space import admit_frontier_formula_epoch_batch
from ztare.leanmill.theory_campaign_journal import TheoryCampaignJournal

from test_theory_navigator import _context_and_blueprint


def _expansion(context, env, *, name, variables, lhs, rhs):
    inputs = {
        "structural_conjecture": f"Test anonymous coordinate {name}.",
        "axiom_name": name,
        "variables": [
            {"name": variable, "sort": "sort_0"} for variable in variables
        ],
        "lhs_tokens": lhs,
        "rhs_tokens": rhs,
        "nl_intent": f"Test anonymous coordinate {name}.",
        "kill_condition": "A frozen finite structure refutes it.",
    }
    receipt = env["action_handlers"]["propose_frontier_formula"](
        ".", {"input_refs": inputs}, None, env["contract"]
    )
    proposal = decode_frontier_formula_proposal(context, inputs)
    summary = receipt["output_summary"]
    assert summary["status"] == "proposed_new_formula"
    return {
        "source_context_hash": context.context_hash,
        "source_epoch": 0,
        "workbench_receipt_id": receipt["receipt_id"],
        "typed_axiom_proposal": proposal.to_json(),
        "typed_proposal_sha256": proposal.content_hash,
        "formula_id": summary["formula_id"],
        "navigator_rationale": f"Admit {name} after late synthesis.",
    }


def test_agent_selected_formula_batch_mints_one_context_epoch(tmp_path):
    context, _blueprint = _context_and_blueprint()
    env = resolve_leaf_workbench_environment(
        "axiompack",
        context=context,
        context_epoch=0,
        selection_mode="theory_program",
        max_presentation_size=2,
    )
    assoc = _expansion(
        context,
        env,
        name="assoc_candidate",
        variables=("x0", "x1", "x2"),
        lhs=["x0", "x1", "op_0", "x2", "op_0"],
        rhs=["x0", "x1", "x2", "op_0", "op_0"],
    )
    medial = _expansion(
        context,
        env,
        name="medial_candidate",
        variables=("x0", "x1", "x2", "x3"),
        lhs=["x0", "x1", "op_0", "x2", "x3", "op_0", "op_0"],
        rhs=["x0", "x2", "op_0", "x1", "x3", "op_0", "op_0"],
    )
    journal = TheoryCampaignJournal(tmp_path / "events.jsonl")
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget_preset("smoke_20m"),
        attempt_id="attempt-batch",
    )

    rebuilt, proposals, epoch, admissions = admit_frontier_formula_epoch_batch(
        context,
        (assoc, medial),
        journal=journal,
        budget_ledger=ledger,
        directory=tmp_path,
        campaign_id="campaign-batch",
        attempt_id="attempt-batch",
        current_epoch=0,
    )

    assert epoch == 1
    assert len(proposals) == len(admissions) == 2
    assert len(rebuilt.formula_ids) == len(context.formula_ids) + 2
    assert len(tuple(tmp_path.glob("typed_formula_proposal.epoch-001.*.json"))) == 2
    assert len(
        tuple(tmp_path.glob("frontier_formula_epoch_admission.epoch-001.*.json"))
    ) == 2
    assert [event.event_type for event in journal.replay()] == [
        "context_epoch_proposed",
        "evidence_promoted_to_next_epoch",
    ]
    assert ledger.state()["usage"]["truth_cells"] == 2 * len(context.object_ids)
