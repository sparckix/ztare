from __future__ import annotations

from dataclasses import replace
from itertools import combinations
import json

from ztare.leanmill.common import write_json_atomic
from ztare.leanmill.exploration_budget import ExplorationBudgetLedger, budget_preset
from ztare.leanmill.theory_interest import theory_program_information_yield
from ztare.leanmill.theory_lineage_runner import run_host_isolated_theory_lineages
from ztare.leanmill.theory_program import derive_context_lineage_id
from test_theory_navigator import _context_and_blueprint


def _freezing_agent(presentation, target):
    decisions = iter(
        [
            {
                "decision": "freeze",
                "formula_ids": list(presentation),
                "boundary_target_ids": [target],
                "rationale": "Freeze this lineage's residual prediction.",
            },
            {"decision": "finish", "rationale": "This lineage is complete."},
        ]
    )
    return lambda _prompt: next(decisions)


class _DurableFreezingAgent:
    def __init__(self, artifact_dir, agent_id, presentation, target):
        self.artifact_dir = artifact_dir
        self.agent_id = agent_id
        self.presentation = presentation
        self.target = target
        self.call_count = 0
        self.provider_call_count = 0

    def __call__(self, _prompt):
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        result_path = self.artifact_dir / "000.result.json"
        call_path = self.artifact_dir / "000.call.json"
        if result_path.is_file():
            return json.loads(result_path.read_text(encoding="utf-8"))
        result = {
            "decision": "freeze",
            "formula_ids": list(self.presentation),
            "boundary_target_ids": [self.target],
            "rationale": "Freeze this durable isolated theory program.",
        }
        write_json_atomic(result_path, result)
        write_json_atomic(call_path, {"returncode": 0})
        self.call_count += 1
        self.provider_call_count += 1
        return result


def test_host_isolated_lineages_compare_only_after_freeze(tmp_path):
    context, blueprint = _context_and_blueprint()
    blueprint = replace(
        blueprint,
        navigator_contract={
            **blueprint.navigator_contract,
            "selection_mode": "theory_program",
            "presentation_size": {"minimum": 1, "maximum": 2},
        },
    )
    candidates = []
    for size in (1, 2):
        for row in combinations(context.formula_ids, size):
            program = theory_program_information_yield(context, row)
            if (
                program.residual_prediction_ids
                and program.coordinates.identification_bits > 0
                and context.incidence.extent_bits(row).bit_count() > 0
            ):
                candidates.append((row, program.residual_prediction_ids[0]))
            if len(candidates) == 2:
                break
        if len(candidates) == 2:
            break
    left, right = candidates

    result = run_host_isolated_theory_lineages(
        context,
        blueprint,
        agent_fns=(
            _freezing_agent(*left),
            _freezing_agent(*right),
        ),
        journal_root=tmp_path / "lineages",
        attempt_id="attempt-isolated",
        campaign_id="campaign-isolated",
        max_rounds=3,
        max_finalists_per_lineage=1,
        budget_ledger=ExplorationBudgetLedger(
            tmp_path / "budget.events.jsonl",
            budget_preset("smoke_20m"),
            attempt_id="attempt-isolated",
        ),
    )

    assert result["status"] == "programs_frozen"
    assert result["lineage_count"] == 2
    assert len(result["theory_program_ids"]) == 2
    assert len(result["host_isolated_program_comparisons"]) == 1
    assert result["isolation_receipt"]["withheld_between_lineages"] == [
        "action_trace",
        "candidate_presentations",
        "formula_or_language_requests",
        "navigator_rationales",
    ]
    first_trace = result["lineages"][0]["navigation"]["trace"]
    second_trace = result["lineages"][1]["navigation"]["trace"]
    assert all("lineage-" not in str(row) for row in first_trace)
    assert all("lineage-" not in str(row) for row in second_trace)

    converged = run_host_isolated_theory_lineages(
        context,
        blueprint,
        agent_fns=(_freezing_agent(*left), _freezing_agent(*left)),
        journal_root=tmp_path / "converged-lineages",
        attempt_id="attempt-converged",
        campaign_id="campaign-converged",
        max_rounds=3,
        max_finalists_per_lineage=1,
        budget_ledger=ExplorationBudgetLedger(
            tmp_path / "converged-budget.events.jsonl",
            budget_preset("smoke_20m"),
            attempt_id="attempt-converged",
        ),
    )
    assert len(converged["theory_program_ids"]) == 2
    assert converged["finalist_node_ids"] == [converged["finalists"][0]["node_id"]]


def test_resume_preserves_terminal_sibling_without_calling_it(tmp_path):
    context, blueprint = _context_and_blueprint()
    blueprint = replace(
        blueprint,
        navigator_contract={
            **blueprint.navigator_contract,
            "selection_mode": "theory_program",
        },
    )
    campaign_id = "campaign-preserved"
    attempt_id = "attempt-preserved"
    preserved = {
        "lineage_id": derive_context_lineage_id(
            campaign_id=campaign_id,
            attempt_id=attempt_id,
            context_epoch=0,
            branch=0,
        ),
        "agent_identity": "preserved-agent",
        "navigation": {
            "context_hash": context.context_hash,
            "finalists": [],
            "trace": [{"decision": "reject_all"}],
            "reject_all_receipt": {"receipt_id": "preserved-rejection"},
            "provider_calls": 0,
        },
    }
    calls = []

    def must_not_run(_prompt):
        raise AssertionError("preserved sibling was redispatched")

    def pending_agent(_prompt):
        calls.append(1)
        return {
            "decision": "request",
            "capability_id": "list_theory_nodes",
            "input_refs": {"offset": 0, "limit": 1},
            "rationale": "Inspect one node in this branch only.",
        }

    result = run_host_isolated_theory_lineages(
        context,
        blueprint,
        agent_fns=(must_not_run, pending_agent),
        journal_root=tmp_path / "preserved-lineages",
        attempt_id=attempt_id,
        campaign_id=campaign_id,
        max_rounds=(0, 1),
        preserved_lineage_rows={0: preserved},
    )

    assert result["lineages"][0] == preserved
    assert calls == [1]


def test_isolated_lineage_replay_does_not_recharge_host_actions(tmp_path):
    context, blueprint = _context_and_blueprint()
    blueprint = replace(
        blueprint,
        navigator_contract={
            **blueprint.navigator_contract,
            "selection_mode": "theory_program",
            "presentation_size": {"minimum": 1, "maximum": 2},
        },
    )
    candidates = []
    for size in (1, 2):
        for row in combinations(context.formula_ids, size):
            signal = theory_program_information_yield(context, row)
            if (
                signal.residual_prediction_ids
                and signal.coordinates.identification_bits > 0
                and context.incidence.extent_bits(row).bit_count() > 0
            ):
                candidates.append((row, signal.residual_prediction_ids[0]))
            if len(candidates) == 2:
                break
        if len(candidates) == 2:
            break
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget_preset("smoke_20m"),
        attempt_id="attempt-replay",
    )

    def agents():
        return tuple(
            _DurableFreezingAgent(
                tmp_path / "calls" / f"lineage-{index}",
                f"agent-{index}",
                presentation,
                target,
            )
            for index, (presentation, target) in enumerate(candidates)
        )

    first = run_host_isolated_theory_lineages(
        context,
        blueprint,
        agent_fns=agents(),
        journal_root=tmp_path / "lineages",
        attempt_id="attempt-replay",
        campaign_id="campaign-replay",
        max_rounds=2,
        max_finalists_per_lineage=1,
        budget_ledger=ledger,
    )
    usage_after_first = ledger.state()["usage"]
    information_after_first = len(ledger.state()["information"])
    second = run_host_isolated_theory_lineages(
        context,
        blueprint,
        agent_fns=agents(),
        journal_root=tmp_path / "lineages",
        attempt_id="attempt-replay",
        campaign_id="campaign-replay",
        max_rounds=2,
        max_finalists_per_lineage=1,
        budget_ledger=ledger,
    )
    replay_at_zero_remaining = run_host_isolated_theory_lineages(
        context,
        blueprint,
        agent_fns=agents(),
        journal_root=tmp_path / "lineages",
        attempt_id="attempt-replay",
        campaign_id="campaign-replay",
        max_rounds=(0, 0),
        max_finalists_per_lineage=1,
        budget_ledger=ledger,
    )

    assert second["theory_program_ids"] == first["theory_program_ids"]
    assert replay_at_zero_remaining["theory_program_ids"] == first["theory_program_ids"]
    assert ledger.state()["usage"] == usage_after_first
    assert len(ledger.state()["information"]) == information_after_first


def test_frozen_program_does_not_suppress_sibling_representation_request(tmp_path):
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
        ((formula_id,), program.residual_prediction_ids[0])
        for formula_id in context.formula_ids
        if (
            program := theory_program_information_yield(context, (formula_id,))
        ).residual_prediction_ids
    )

    def representation_agent(_prompt):
        return {
            "decision": "request",
            "capability_id": "propose_frontier_formula",
            "input_refs": {
                "structural_conjecture": "Test whether ternary bracketing matters.",
                "axiom_name": "assoc_candidate",
                "variables": [
                    {"name": "x0", "sort": "sort_0"},
                    {"name": "x1", "sort": "sort_0"},
                    {"name": "x2", "sort": "sort_0"},
                ],
                "lhs_tokens": ["x0", "x1", "op_0", "x2", "op_0"],
                "rhs_tokens": ["x0", "x1", "x2", "op_0", "op_0"],
                "nl_intent": "Compare the two bracketings.",
                "kill_condition": "The new coordinate duplicates an existing profile.",
            },
            "rationale": "The current chart omits the distinction this lineage needs.",
        }

    result = run_host_isolated_theory_lineages(
        context,
        blueprint,
        agent_fns=(
            _freezing_agent(presentation, target),
            representation_agent,
        ),
        journal_root=tmp_path / "mixed-lineages",
        attempt_id="attempt-mixed",
        campaign_id="campaign-mixed",
        max_rounds=2,
        max_finalists_per_lineage=1,
    )

    assert result["status"] == "mixed_frozen_outputs"
    assert len(result["finalists"]) == 1
    assert len(result["expansion_proposals"]) == 1


def test_budget_exhausted_sibling_is_represented_as_a_receipt(tmp_path):
    context, blueprint = _context_and_blueprint()
    blueprint = replace(
        blueprint,
        navigator_contract={
            **blueprint.navigator_contract,
            "selection_mode": "theory_program",
        },
    )

    def inspect_forever(_prompt):
        return {
            "decision": "request",
            "capability_id": "list_theory_nodes",
            "input_refs": {"offset": 0, "limit": 1},
            "rationale": "Keep inspecting until the host budget ends this lineage.",
        }

    result = run_host_isolated_theory_lineages(
        context,
        blueprint,
        agent_fns=(inspect_forever, inspect_forever),
        journal_root=tmp_path / "budget-lineages",
        attempt_id="attempt-budget-lineages",
        campaign_id="campaign-budget-lineages",
        max_rounds=10,
        max_finalists_per_lineage=1,
        budget_ledger=ExplorationBudgetLedger(
            tmp_path / "budget-lineages.events.jsonl",
            budget_preset("smoke_20m"),
            attempt_id="attempt-budget-lineages",
        ),
    )

    assert result["lineage_count"] == 2
    assert len(result["pending_leaf_decisions"]) == 1
    assert isinstance(
        result["lineages"][1]["navigation"].get("navigation_exhausted_receipt"),
        dict,
    )
    assert result["status"] == "pending_leaf_decision"
