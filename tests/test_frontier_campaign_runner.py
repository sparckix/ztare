from __future__ import annotations

from dataclasses import replace
from itertools import combinations
import json

from ztare.leanmill.exploration_budget import ExplorationBudgetLedger, budget_preset
from ztare.leanmill.common import read_json, write_json_atomic, write_text_atomic
from ztare.leanmill.explore_axiom_space import (
    finish_frontier_navigation,
    packet_for_frontier_context,
)
from ztare.leanmill.finite_theory_context import save_formal_theory_context
from ztare.leanmill.formal_verification_provider import generate_keypair
from ztare.leanmill.frontier_campaign import sign_frontier_campaign
from ztare.leanmill.frontier_campaign_actions import replay_frontier_campaign
from ztare.leanmill.frontier_campaign_definition import FrontierCampaignDefinition
from ztare.leanmill.frontier_campaign_runner import (
    _make_campaign_theory_navigator,
    materialize_frontier_navigation_from_journal,
)
from ztare.leanmill.theory_campaign_journal import TheoryCampaignJournal
from ztare.leanmill.theory_interest import theory_program_information_yield
from ztare.leanmill.theory_ir import content_hash

from test_theory_navigator import _context_and_blueprint


def test_outer_objective_blocks_boundary_status_when_late_leaf_requests_more_search(
    tmp_path,
):
    context, blueprint = _context_and_blueprint()
    instruction = "Invent a coordinate whose prediction leaves the seed chart."
    blueprint = replace(
        blueprint,
        stop_rule={
            **blueprint.stop_rule,
            "user_instruction": instruction,
            "executable_condition": {
                "kind": "late_lineage_objective_review"
            },
        },
    )

    run = finish_frontier_navigation(
        tmp_path,
        brief_id=blueprint.brief_digest,
        blueprint=blueprint,
        context=context,
        context_epoch=0,
        campaign_id="campaign:test",
        packet_digest="packet:test",
        navigation={
            "context_hash": context.context_hash,
            "context_epoch": 0,
            "finalists": [{"node_id": "node:control"}],
            "lineage_synthesis": {
                "route": "continue_search",
                "program_ids": ["theory-program:control"],
                "next_discriminator_request_ids": [],
            },
        },
        provider_calls=3,
        preparation_provider_calls=0,
        budget_digest="budget:test",
        formula_proposal_count=0,
        semantically_new_formula_count=0,
        labeled_object_count=len(context.object_ids),
    )

    assert run.status == "frontier_objective_unmet"
    assert read_json(tmp_path / "run.json", {})["status"] == "frontier_objective_unmet"


def test_objective_unmet_terminal_receipts_replay_without_a_finalist(tmp_path):
    context, blueprint = _context_and_blueprint()
    blueprint = replace(
        blueprint,
        stop_rule={
            **blueprint.stop_rule,
            "user_instruction": "Require a composed authored-coordinate prediction.",
            "executable_condition": {"kind": "late_lineage_objective_review"},
        },
    )
    objective = {
        "schema": "leanmill.frontier_objective_contract.v1",
        "instruction": "Require a composed authored-coordinate prediction.",
        "review_stage": "post_lineage_freeze_pre_boundary",
        "authority": "independent_leaf_choice_host_receipt_validation",
    }
    review_core = {
        "schema": "leanmill.lineage_synthesis_decision.v1",
        "context_hash": context.context_hash,
        "context_epoch": 0,
        "route": "continue_search",
        "objective_contract": objective,
    }
    review = {**review_core, "receipt_sha256": content_hash(review_core)}
    stop_core = {
        "schema": "leanmill.lineage_synthesis_budget_stop.v1",
        "context_hash": context.context_hash,
        "context_epoch": 0,
        "reason": "blocked_before_action:navigation:provider_calls",
    }
    stop = {**stop_core, "receipt_sha256": content_hash(stop_core)}
    exhausted_core = {
        "schema": "leanmill.host_isolated_navigation_exhausted.v1",
        "context_hash": context.context_hash,
        "context_epoch": 0,
        "lineage_count": 2,
    }
    exhausted = {
        **exhausted_core,
        "receipt_sha256": content_hash(exhausted_core),
    }
    save_formal_theory_context(context, tmp_path / "formal_context.json")
    write_json_atomic(tmp_path / "blueprint.json", blueprint.to_json())
    finish_frontier_navigation(
        tmp_path,
        brief_id=blueprint.brief_digest,
        blueprint=blueprint,
        context=context,
        context_epoch=0,
        campaign_id="campaign:test",
        packet_digest="packet:test",
        navigation={
            "context_hash": context.context_hash,
            "context_epoch": 0,
            "finalists": [],
            "objective_review_history": [review],
            "lineage_synthesis_budget_stop": stop,
            "navigation_exhausted_receipt": exhausted,
        },
        provider_calls=3,
        preparation_provider_calls=0,
        budget_digest="budget:test",
        formula_proposal_count=0,
        semantically_new_formula_count=0,
        labeled_object_count=len(context.object_ids),
    )

    replay = replay_frontier_campaign(tmp_path)

    assert replay["ok"] is True
    assert replay["objective_unmet_check"]["review_count"] == 1


class _ScriptedRole:
    def __init__(self, agent_id: str, decision: dict) -> None:
        self.agent_id = agent_id
        self._decision = decision
        self.call_count = 0
        self.provider_call_count = 0
        self.budget_ledger = None

    def __call__(self, _prompt: str) -> dict:
        self.call_count += 1
        self.provider_call_count += 1
        return dict(self._decision)


def test_objective_continuation_opens_a_fresh_agent_call_wave(monkeypatch, tmp_path):
    instances = []

    def fake_role(_definition, *, role_name, repo, artifact_dir, instance_id=""):
        del role_name, repo, artifact_dir
        instances.append(instance_id)
        return _ScriptedRole(f"role:{instance_id}", {})

    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.frontier_agent_role",
        fake_role,
    )
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.make_subscription_theory_navigator",
        lambda role, *, attempt_id: (role, attempt_id),
    )
    definition = FrontierCampaignDefinition(
        direction="Explore fresh conjectural lineages.",
        source_mode="structure_first",
        budget=budget_preset("smoke_20m"),
    )
    navigator = _make_campaign_theory_navigator(
        definition,
        directory=tmp_path,
        repo=tmp_path,
        attempt_id=tmp_path.name,
    )

    navigator.begin_search_wave()

    assert instances == ["", "wave-001"]
    assert navigator.search_wave == 1


def test_request_only_wave_can_reject_then_open_fresh_program_wave(
    monkeypatch, tmp_path
):
    context, blueprint = _context_and_blueprint()
    blueprint = replace(
        blueprint,
        navigator_contract={
            **blueprint.navigator_contract,
            "selection_mode": "theory_program",
            "host_isolated_lineages": 2,
        },
        query_budget={
            **blueprint.query_budget,
            "navigator_rounds": 4,
            "max_finalists": 2,
        },
        stop_rule={
            **blueprint.stop_rule,
            "user_instruction": "Require two authored coordinates and a new prediction.",
            "executable_condition": {"kind": "late_lineage_objective_review"},
        },
    )
    instances = []

    class AdaptiveRole(_ScriptedRole):
        def __call__(self, prompt: str) -> dict:
            self.call_count += 1
            self.provider_call_count += 1
            self.calls = getattr(self, "calls", [])
            self.calls.append({"returncode": 0})
            synthesis_input = json.loads(
                prompt.split("FROZEN LINEAGE REQUESTS:\n", 1)[1]
            )
            request_ids = [
                row["request_id"]
                for key in ("formula_requests", "theory_language_requests")
                for row in synthesis_input[key]
            ]
            programs = [
                row["program_id"] for row in synthesis_input["frozen_programs"]
            ]
            return {
                "route": "proceed_boundary" if programs else "continue_search",
                "selected_request_ids": [],
                "deferred_request_ids": request_ids,
                "program_ids": programs,
                "next_discriminator_request_ids": [],
                "rationale": "The request-only wave lacks a compositional program.",
                "next_discriminator": "Freeze a program in a fresh search wave.",
                "kill_condition": "The fresh wave repeats the same coordinate.",
            }

    def fake_role(_definition, *, role_name, repo, artifact_dir, instance_id=""):
        del repo
        instances.append((role_name, instance_id))
        if role_name == "lineage_synthesizer":
            role = AdaptiveRole(f"{role_name}:{instance_id}", {})
            role.calls = []
            role.artifact_dir = artifact_dir / (
                role_name if not instance_id else f"{role_name}.{instance_id}"
            )
            return role
        return _ScriptedRole(f"{role_name}:{instance_id}", {})

    def fake_lineages(*_args, agent_fns, **_kwargs):
        fresh = any("wave-001" in role.agent_id for role in agent_fns)
        if fresh:
            return {
                "context_hash": context.context_hash,
                "context_epoch": 0,
                    "finalists": [{
                        "theory_program": {
                            "program_id": "theory-program:fresh",
                            "context_hash": context.context_hash,
                        },
                        "prediction_profile": {
                            "predictions": [
                                {
                                    "prediction_formula_id": "formula:target",
                                    "chart_status": "supported_in_context",
                                }
                            ]
                        },
                    }],
                "expansion_proposals": [],
                "theory_language_expansion_requests": [],
                "provider_calls": 0,
            }
        return {
            "context_hash": context.context_hash,
            "context_epoch": 0,
            "finalists": [],
            "expansion_proposals": [
                {"lineage_id": "lineage:a", "proposal": {"formula_id": "formula:a"}},
                {"lineage_id": "lineage:b", "proposal": {"formula_id": "formula:a"}},
            ],
            "theory_language_expansion_requests": [],
            "provider_calls": 0,
        }

    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.frontier_agent_role", fake_role
    )
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.run_host_isolated_theory_lineages",
        fake_lineages,
    )
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner._record_host_isolated_navigation",
        lambda *_args, **_kwargs: None,
    )
    definition = FrontierCampaignDefinition(
        direction="Explore recursive conjectural lineages.",
        source_mode="structure_first",
        budget=budget_preset("smoke_20m"),
    )
    navigator = _make_campaign_theory_navigator(
        definition,
        directory=tmp_path,
        repo=tmp_path,
        attempt_id=tmp_path.name,
    )
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        definition.budget,
        attempt_id=tmp_path.name,
    )
    first = navigator(context, blueprint, TheoryCampaignJournal(tmp_path / "events.jsonl"), budget_ledger=ledger)
    assert first["lineage_synthesis"]["route"] == "continue_search"

    navigator.begin_search_wave()
    second = navigator(context, blueprint, TheoryCampaignJournal(tmp_path / "events.jsonl"), budget_ledger=ledger)

    assert second["lineage_synthesis"]["route"] == "proceed_boundary"
    assert ("navigator", "lineage-000.wave-001") in instances
    assert ("lineage_synthesizer", "wave-001") in instances
    assert (tmp_path / "lineage_synthesis_input.epoch-000.json").is_file()
    assert (
        tmp_path / "lineage_synthesis_input.epoch-000.wave-001.json"
    ).is_file()


def test_campaign_navigator_routes_host_isolated_lineages_without_sibling_trace(
    monkeypatch, tmp_path
):
    context, blueprint = _context_and_blueprint()
    blueprint = replace(
        blueprint,
        navigator_contract={
            **blueprint.navigator_contract,
            "selection_mode": "theory_program",
            "host_isolated_lineages": 2,
            "presentation_size": {"minimum": 1, "maximum": 2},
        },
        query_budget={
            **blueprint.query_budget,
            "navigator_rounds": 4,
            "max_finalists": 2,
        },
    )
    candidates = []
    for size in (1, 2):
        for formulas in combinations(context.formula_ids, size):
            signal = theory_program_information_yield(context, formulas)
            if (
                signal.residual_prediction_ids
                and signal.coordinates.identification_bits > 0
                and context.incidence.extent_bits(formulas).bit_count() > 0
            ):
                candidates.append((formulas, signal.residual_prediction_ids[0]))
            if len(candidates) == 2:
                break
        if len(candidates) == 2:
            break

    def fake_role(_definition, *, role_name, repo, artifact_dir, instance_id=""):
        del repo, artifact_dir
        if not instance_id:
            return _ScriptedRole("unused-single", {})
        index = int(instance_id.rsplit("-", 1)[1])
        formulas, target = candidates[index]
        return _ScriptedRole(
            f"{role_name}-{instance_id}",
            {
                "decision": "freeze",
                "formula_ids": list(formulas),
                "boundary_target_ids": [target],
                "rationale": "Freeze this isolated theory program.",
            },
        )

    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.frontier_agent_role",
        fake_role,
    )
    definition = FrontierCampaignDefinition(
        direction="Explore two isolated theory lineages.",
        source_mode="structure_first",
        budget=budget_preset("smoke_20m"),
    )
    navigator = _make_campaign_theory_navigator(
        definition,
        directory=tmp_path,
        repo=tmp_path,
        attempt_id=tmp_path.name,
    )
    journal = TheoryCampaignJournal(tmp_path / "events.jsonl")
    result = navigator(
        context,
        blueprint,
        journal,
        budget_ledger=ExplorationBudgetLedger(
            tmp_path / "budget.events.jsonl",
            definition.budget,
            attempt_id=tmp_path.name,
        ),
    )

    assert result["status"] == "programs_frozen"
    assert len(result["finalists"]) == 2
    assert len(result["host_isolated_program_comparisons"]) == 1
    assert sum(event.event_type == "finalist_frozen" for event in journal.replay()) == 2
    assert all(
        len(row["navigation"]["trace"]) == 1 for row in result["lineages"]
    )

    write_text_atomic(tmp_path / "campaign_definition.yaml", definition.to_yaml())
    write_json_atomic(tmp_path / "blueprint.json", blueprint.to_json())
    write_json_atomic(tmp_path / "budget.json", definition.budget.to_json())
    save_formal_theory_context(context, tmp_path / "formal_context.json")
    campaign_id = "campaign:" + blueprint.blueprint_id.split(":", 1)[1][:24]
    private, public = generate_keypair()
    write_json_atomic(
        tmp_path / "campaign.json",
        sign_frontier_campaign(
            packet_for_frontier_context(
                blueprint,
                context,
                campaign_id=campaign_id,
            ),
            private_key_pem=private,
            signer_ref="test-authority",
        ).to_json(),
    )
    write_text_atomic(tmp_path / "campaign_signer_public.pem", public)
    for index, lineage in enumerate(result["lineages"]):
        finalist = lineage["navigation"]["finalists"][0]
        call_dir = tmp_path / "agent_calls" / f"navigator.lineage-{index:03d}"
        decision = {
            "decision": "freeze",
            "formula_ids": finalist["formula_ids"],
            "boundary_target_ids": finalist["boundary_target_ids"],
            "rationale": finalist["navigator_rationale"],
        }
        result_text = json.dumps(decision, sort_keys=True, separators=(",", ":"))
        write_text_atomic(call_dir / "000.result.json", result_text)
        write_json_atomic(
            call_dir / "000.call.json",
            {
                "returncode": 0,
                "result_digest": content_hash({"result": result_text}),
            },
        )

    materialize_frontier_navigation_from_journal(tmp_path)
    recovered = read_json(tmp_path / "run.json", {})["navigation"]
    assert len(recovered["finalists"]) == 2
    assert len(recovered["host_isolated_program_comparisons"]) == 1
    assert len(
        {
            row["theory_program"]["lineage_id"]
            for row in recovered["finalists"]
        }
    ) == 2
    assert replay_frontier_campaign(tmp_path)["ok"] is True
