from __future__ import annotations

from dataclasses import replace
from itertools import combinations
import json
from pathlib import Path
import re

import pytest

from ztare.leanmill.exploration_budget import ExplorationBudgetLedger, budget_preset
from ztare.leanmill.external_science_admission import _campaign_packet_for_request
from ztare.leanmill.common import read_json, write_json_atomic, write_text_atomic
from ztare.leanmill.explore_axiom_space import (
    _adjudicate_theory_program_tasks,
    drive_frontier_navigation,
    finish_frontier_navigation,
    packet_for_frontier_context,
)
from ztare.leanmill.finite_theory_context import save_formal_theory_context
from ztare.leanmill.formal_verification_provider import generate_keypair
from ztare.leanmill.frontier_campaign import sign_frontier_campaign
from ztare.leanmill.frontier_campaign_actions import replay_frontier_campaign
from ztare.leanmill.frontier_campaign_definition import FrontierCampaignDefinition
from ztare.leanmill.frontier_boundary import run_frontier_boundaries
from ztare.leanmill.frontier_campaign_runner import (
    _admit_campaign_workbench_successor,
    _active_objective_finalists,
    _archive_cross_context_active_candidates,
    _boundary_search_feedback,
    _consume_theory_task_discharge,
    _lineage_synthesis_retry_required,
    _make_campaign_theory_navigator,
    _objective_navigation_phase,
    _objective_synthesis_budget_exhausted,
    _post_freeze_lineage_binding,
    _prepend_predecessor_synthesis,
    _registered_formal_task_executor_required,
    _restore_nested_objective_feedback_history,
    _frontier_lifecycle_marker,
    drive_frontier_campaign,
    materialize_frontier_navigation_from_journal,
    next_frontier_campaign_action,
)
from ztare.leanmill.explore_axiom_space import (
    _adjudicate_theory_program_tasks,
    _boundary_completion_covers,
)
from ztare.common.task_discharge import TaskDischargeContract, TaskDischargeReceipt
from ztare.leanmill.theory_program import THEORY_PROGRAM_V2, TheoryProgram
from ztare.leanmill.theory_campaign_journal import TheoryCampaignJournal
from ztare.leanmill.theory_navigator import run_interactive_theory_navigator
from ztare.leanmill.theory_interest import theory_program_information_yield
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.formal_task_boundary import (
    GOVERNED_FORMAL_COUNTEREXAMPLE_ADJUDICATOR,
)

from test_theory_navigator import _context_and_blueprint


_V9_WORKBENCH = {
    "schema": "leanmill-axiompack-leaf-workbench-v9",
    "fingerprint": "46b89dd61e29d18b7b335b52a4b87e87dc332b8893d4c270ff490499b6d814f9",
    "capability_ids": [
        "list_theory_nodes",
        "list_compound_dependencies",
        "inspect_formula_profiles",
        "inspect_theory_node",
        "compare_theory_nodes",
        "show_separation_models",
        "show_indistinguishable_objects",
        "propose_frontier_formula",
        "select_theory_presentation",
        "propose_theory_language_expansion",
    ],
}


def test_campaign_workbench_successor_is_typed_authority_bound_and_replayable(
    tmp_path,
) -> None:
    context, blueprint = _context_and_blueprint()
    target = packet_for_frontier_context(
        blueprint, context, campaign_id="campaign:workbench-successor"
    )
    private_key, public_key = generate_keypair()
    source = replace(target, navigator_contract=_V9_WORKBENCH)
    campaign = sign_frontier_campaign(
        source,
        private_key_pem=private_key,
        signer_ref="test-authority",
    ).to_json()
    write_json_atomic(tmp_path / "campaign.epoch-000.json", campaign)
    write_text_atomic(tmp_path / "private" / "campaign_signer.pem", private_key)
    write_text_atomic(tmp_path / "campaign_signer_public.pem", public_key)
    checkpoint = {
        "schema": "leanmill.frontier_navigation_epoch_checkpoint.v1",
        "context_hash": context.context_hash,
        "context_epoch": 0,
        "trace": [],
        "provider_calls": 0,
        "typed_formula_proposal_sha256s": [],
    }
    write_json_atomic(tmp_path / "navigation_epoch_checkpoint.json", checkpoint)

    assert _admit_campaign_workbench_successor(
        tmp_path,
        campaign=campaign,
        target_packet=target,
        context_epoch=0,
        authority_ref="",
    ) is None
    required = read_json(
        tmp_path / "campaign_workbench_successor_authorization_required.json", {}
    )
    assert required["status"] == "authority_required"
    assert not (tmp_path / "campaign.json").exists()

    admitted = _admit_campaign_workbench_successor(
        tmp_path,
        campaign=campaign,
        target_packet=target,
        context_epoch=0,
        authority_ref="user:continue-maximally:test",
    )
    assert admitted.digest == target.digest
    active = read_json(tmp_path / "campaign.json", {})
    assert active["packet_digest"] == target.digest
    assert active["signer_ref"] == "test-authority"
    assert not (tmp_path / "campaign_workbench_successor_authorization_required.json").exists()
    transitions = list(tmp_path.glob("campaign_workbench_successor.*.json"))
    assert len(transitions) == 1
    assert read_json(transitions[0], {})["authority_ref"] == (
        "user:continue-maximally:test"
    )
    trace = read_json(tmp_path / "navigation_epoch_checkpoint.json", {})["trace"]
    assert [row["decision"] for row in trace] == [
        "campaign_workbench_successor_admitted"
    ]
    request_packet = _campaign_packet_for_request(
        tmp_path,
        blueprint_id=blueprint.blueprint_id,
        context_hash=context.context_hash,
        expected_packet_digest=source.digest,
    )
    assert request_packet == source.to_json()

    replayed = _admit_campaign_workbench_successor(
        tmp_path,
        campaign=campaign,
        target_packet=target,
        context_epoch=0,
        authority_ref="user:continue-maximally:test",
    )
    assert replayed.digest == target.digest
    assert len(list(tmp_path.glob("campaign_workbench_successor.*.json"))) == 1


def test_campaign_workbench_successor_rejects_unreviewed_packet_drift(
    tmp_path,
) -> None:
    context, blueprint = _context_and_blueprint()
    target = packet_for_frontier_context(
        blueprint, context, campaign_id="campaign:workbench-successor"
    )
    source_packet = {**target.to_json(), "navigator_contract": _V9_WORKBENCH}
    source_packet["eigenquestion"] = "changed outside the workbench"
    campaign = {
        "packet": source_packet,
        "packet_digest": "sha256:" + content_hash(source_packet),
        "signature": "source-signature-validated-by-loader",
        "signer_ref": "test-authority",
    }
    private_key, _public_key = generate_keypair()
    write_text_atomic(tmp_path / "private" / "campaign_signer.pem", private_key)

    with pytest.raises(ValueError, match="outside the workbench contract"):
        _admit_campaign_workbench_successor(
            tmp_path,
            campaign=campaign,
            target_packet=target,
            context_epoch=0,
            authority_ref="user:test",
        )


def test_theory_task_discharge_rolls_to_an_archived_predecessor_boundary(
    tmp_path,
) -> None:
    first_core = {
        "schema": "leanmill.frontier_boundary_result.v1",
        "context_hash": "context:test",
        "query_results": [],
    }
    first = {**first_core, "result_sha256": content_hash(first_core)}
    first_discharge = _adjudicate_theory_program_tasks(
        tmp_path,
        adapter_id="generic_fol_finite.v1",
        navigation={},
        boundary_result=first,
    )
    write_json_atomic(
        tmp_path / "boundary_attempts" / "predecessor" / "boundary_result.json",
        first,
    )
    second_core = {
        **first_core,
        "query_results": [{"query_id": "new-boundary"}],
    }
    second = {**second_core, "result_sha256": content_hash(second_core)}

    second_discharge = _adjudicate_theory_program_tasks(
        tmp_path,
        adapter_id="generic_fol_finite.v1",
        navigation={},
        boundary_result=second,
    )

    assert second_discharge["boundary_result_sha256"] == second["result_sha256"]
    assert read_json(
        tmp_path
        / "boundary_attempts"
        / "predecessor"
        / "theory_task_discharge.json",
        {},
    ) == first_discharge


def test_frontier_lifecycle_routes_by_live_identity_not_stale_artifacts(
    tmp_path,
) -> None:
    def write_run(status: str, navigation: dict | None = None) -> None:
        core = {
            "status": status,
            "context_hash": "context:test",
            "navigation": navigation or {},
        }
        write_json_atomic(
            tmp_path / "run.json",
            {**core, "run_digest": content_hash(core)},
        )

    write_json_atomic(
        tmp_path / "adapter_forge_completion.json",
        {"status": "stale_forge_artifact"},
    )
    write_run("frontier_leaf_decision_pending")
    assert next_frontier_campaign_action(tmp_path) == "resume_navigation"
    write_run("frontier_language_expansion_requested")
    assert next_frontier_campaign_action(tmp_path) == "advance_language"
    write_run(
        "frontier_candidates_frozen_awaiting_boundary_approval",
        {"epoch_transition": {"status": "successor_epoch_required"}},
    )
    assert next_frontier_campaign_action(tmp_path) == "continue_epoch"
    write_run("frontier_navigation_exhausted")
    assert next_frontier_campaign_action(tmp_path) == "complete"

    before_admission = _frontier_lifecycle_marker(tmp_path, "resume_navigation")
    admission = tmp_path / "external_science_resume_admission.fixture.json"
    write_json_atomic(
        admission,
        {"lineage_id": "theory-lineage:fixture", "admission_sha256": "admit"},
    )
    assert next_frontier_campaign_action(tmp_path) == "resume_navigation"
    assert (
        _frontier_lifecycle_marker(tmp_path, "resume_navigation")
        != before_admission
    )

    admission.unlink()
    negative = tmp_path / "external_science_negative_disposition.fixture.json"
    write_json_atomic(negative, {"receipt_sha256": "reject"})
    assert next_frontier_campaign_action(tmp_path) == "resume_navigation"
    negative.unlink()
    write_run("unexpected_status")
    with pytest.raises(ValueError, match="unknown run status"):
        next_frontier_campaign_action(tmp_path)


def test_stale_boundary_disposition_routes_to_navigation_not_deferred_language(
    tmp_path,
) -> None:
    navigation = {
        "finalists": [],
        "objective_survivors": [{"theory_program_id": "theory-program:carried"}],
        "theory_language_expansion_requests": [
            {"request_id": "theory-language-request:deferred"}
        ],
        "lineage_synthesis": {
            "route": "proceed_boundary",
            "selected_requests": [],
            "deferred_request_ids": ["theory-language-request:deferred"],
        },
    }
    core = {
        "status": "frontier_language_expansion_requested",
        "context_hash": "context:test",
        "navigation": navigation,
    }
    write_json_atomic(
        tmp_path / "run.json", {**core, "run_digest": content_hash(core)}
    )

    assert next_frontier_campaign_action(tmp_path) == "resume_navigation"


def test_nested_survivor_feedback_restores_causal_review_history(tmp_path) -> None:
    feedback_core = {
        "schema": "leanmill.boundary_search_feedback.v1",
        "program_ids": ["theory-program:carried"],
        "prediction_outcomes": [],
        "route": "continue_search",
    }
    feedback = {
        **feedback_core,
        "receipt_sha256": content_hash(feedback_core),
    }
    core = {
        "status": "frontier_objective_unmet",
        "context_hash": "context:test",
        "navigation": {
            "objective_survivors": [{
                "theory_program_id": "theory-program:carried",
                "objective_feedback": feedback,
            }],
            "objective_review_history": [],
        },
    }
    run = {**core, "run_digest": content_hash(core)}
    write_json_atomic(tmp_path / "run.json", run)

    repaired = _restore_nested_objective_feedback_history(tmp_path, run)
    assert repaired is not None
    assert repaired["navigation"]["objective_review_history"] == [feedback]
    assert _restore_nested_objective_feedback_history(tmp_path, repaired) == repaired


def test_frontier_lifecycle_finalizes_exhausted_objective_synthesis(
    tmp_path, monkeypatch
) -> None:
    import ztare.leanmill.frontier_campaign_runner as runner

    stop_core = {
        "schema": "leanmill.lineage_synthesis_budget_stop.v1",
        "context_hash": "context:test",
        "context_epoch": 0,
        "reason": "blocked_before_action:expansion:provider_calls",
        "authority": "host_budget_ledger",
    }
    stop = {**stop_core, "receipt_sha256": content_hash(stop_core)}
    core = {
        "status": "frontier_objective_unmet",
        "context_hash": "context:test",
        "navigation": {"lineage_synthesis_budget_stop": stop},
    }
    write_json_atomic(
        tmp_path / "run.json", {**core, "run_digest": content_hash(core)}
    )
    monkeypatch.setattr(
        runner,
        "_objective_synthesis_budget_exhausted",
        lambda _directory, _run: True,
    )

    assert next_frontier_campaign_action(tmp_path) == "finalize_budget_stop"


def test_objective_budget_stop_precedes_unmet_status(tmp_path) -> None:
    context, blueprint = _context_and_blueprint()
    blueprint = replace(
        blueprint,
        stop_rule={
            **blueprint.stop_rule,
            "user_instruction": "Require a late objective review.",
            "executable_condition": {"kind": "late_lineage_objective_review"},
        },
    )
    stop_core = {
        "schema": "leanmill.exploration_budget_stop.v1",
        "reason": "blocked_before_action:expansion:provider_calls",
        "context_hash": context.context_hash,
    }
    stop = {**stop_core, "receipt_sha256": content_hash(stop_core)}
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
            "finalists": [{"node_id": "node:frozen"}],
        },
        provider_calls=3,
        preparation_provider_calls=0,
        budget_digest="budget:test",
        formula_proposal_count=0,
        semantically_new_formula_count=0,
        labeled_object_count=len(context.object_ids),
        budget_stop_receipt=stop,
    )

    assert run.status == "budget_stopped"


def test_frontier_lifecycle_composes_existing_transition_doors(
    tmp_path, monkeypatch
) -> None:
    import ztare.leanmill.frontier_campaign_runner as runner
    from types import SimpleNamespace

    _context, blueprint = _context_and_blueprint()
    write_json_atomic(tmp_path / "blueprint.json", blueprint.to_json())
    actions = iter(
        (
            "continue_epoch",
            "verify_boundary",
            "interpret_boundary",
            "resume_navigation",
            "complete",
        )
    )
    calls: list[object] = []
    monkeypatch.setattr(runner, "next_frontier_campaign_action", lambda _path: next(actions))
    monkeypatch.setattr(
        runner,
        "continue_frontier_campaign_epoch",
        lambda path: calls.append("epoch") or Path(path),
    )
    monkeypatch.setattr(
        runner,
        "execute_frontier_campaign_verification",
        lambda _path, **kwargs: calls.append(("verify", kwargs)) or {},
    )
    monkeypatch.setattr(
        runner,
        "load_frontier_campaign_definition",
        lambda _path: SimpleNamespace(),
    )
    monkeypatch.setattr(
        runner,
        "frontier_agent_role",
        lambda *_args, **_kwargs: SimpleNamespace(
            config=SimpleNamespace(model="campaign-model", reasoning_effort="high")
        ),
    )
    monkeypatch.setattr(
        runner,
        "run_post_freeze_literature_review",
        lambda _path, **kwargs: calls.append(("interpret", kwargs)) or {},
    )
    monkeypatch.setattr(
        runner,
        "resume_frontier_campaign_navigation",
        lambda path, **_kwargs: calls.append("resume") or Path(path),
    )

    assert drive_frontier_campaign(tmp_path) == tmp_path
    assert [row if isinstance(row, str) else row[0] for row in calls] == [
        "epoch", "verify", "interpret", "resume",
    ]
    verify = calls[1][1]
    assert verify["resume_search"] is False
    assert verify["with_lean"] == blueprint.verification_plan.get("conditional_lean", False)
    interpret = calls[2][1]
    assert interpret == {"model": "campaign-model", "reasoning_effort": "high"}


def test_axiompack_formal_task_activates_without_conditional_lean() -> None:
    context, blueprint = _context_and_blueprint()
    # This is the campaign shape that exposed the first-fire gap: Lean is a
    # referee, while prediction-level conditional Lean is absent.
    plan = {
        **blueprint.verification_plan,
        "referees": ["finite_model", "lean"],
    }
    plan.pop("conditional_lean", None)
    contract = TaskDischargeContract(
        contract_id="task:axiompack:formal-counterexample",
        adjudicator_id=GOVERNED_FORMAL_COUNTEREXAMPLE_ADJUDICATOR,
        lifecycle_scope="campaign:axiompack",
        owner="lineage:axiompack",
        parameters={},
    )
    program = TheoryProgram(
        campaign_id="campaign:axiompack",
        lineage_id="lineage:axiompack",
        context_hash=context.context_hash,
        context_epoch=0,
        presentation_formula_ids=context.formula_ids[:1],
        prediction_formula_ids=(),
        selection_receipt_id="selection:axiompack",
        schema=THEORY_PROGRAM_V2,
        task_discharge_contracts=(contract,),
    )
    navigation = {
        "finalists": [
            {
                "candidate_kind": "theory_program",
                "theory_program_id": program.program_id,
                "theory_program": program.to_json(),
            }
        ]
    }
    assert plan.get("conditional_lean") is not True
    assert _registered_formal_task_executor_required(navigation) is True


def test_leaf_authored_task_reaches_authorized_objective_without_formula_query(
    tmp_path, monkeypatch
):
    from ztare.leanmill.adapters import magma_equational

    context, blueprint = _context_and_blueprint()
    blueprint = replace(
        blueprint,
        navigator_contract={
            **blueprint.navigator_contract,
            "selection_mode": "theory_program",
        },
    )
    pair = next(
        tuple(row)
        for row in combinations(context.formula_ids, 2)
        if context.incidence.extent_bits(row)
    )

    def compile_task(*, request, context, adapter_config):
        formulas = tuple(request["presentation_formula_ids"])
        evidence_core = {
            "context_hash": context.context_hash,
            "presentation_formula_ids": list(formulas),
            "extent_size": context.incidence.extent_bits(formulas).bit_count(),
        }
        return {
            "adjudicator_id": "test.presentation_extent.v1",
            "parameters": {
                "kind": "presentation_extent",
                **evidence_core,
                "evidence_ref": "sha256:" + content_hash(evidence_core),
            },
        }

    def adjudicate(*, contract, boundary_result):
        parameters = dict(contract.parameters)
        return TaskDischargeReceipt(
            contract_sha256=contract.sha256,
            adjudicator_id=contract.adjudicator_id,
            status=("discharged" if int(parameters["extent_size"]) > 0 else "open"),
            authority="test.registered_adapter",
            observed={"extent_size": int(parameters["extent_size"])},
            evidence_refs=(
                str(parameters["evidence_ref"]),
                str(boundary_result["result_sha256"]),
            ),
        )

    monkeypatch.setitem(
        magma_equational.CAPABILITIES, "theory_task_compiler", compile_task
    )
    monkeypatch.setitem(
        magma_equational.CAPABILITIES, "task_discharge_adjudicator", adjudicate
    )

    calls = 0

    def leaf(prompt):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {
                "decision": "request",
                "rationale": "Ask the adapter to classify this presentation extent.",
                "capability_id": "propose_theory_task",
                "input_refs": {
                    "formula_ids": list(pair),
                    "goal": "Classify whether the selected presentation has a model.",
                    "observable": "cardinality of the frozen finite extent",
                    "adjudicator_capability": "presentation_extent",
                    "evidence_refs": [context.context_hash],
                    "kill_condition": "the selected extent is empty",
                },
                "formula_ids": None,
                "boundary_target_ids": None,
            }
        task_id = re.search(r"theory-task:[0-9a-f]{64}", prompt)
        assert task_id is not None
        return {
            "decision": "freeze",
            "rationale": "Freeze the host-compiled classification task.",
            "capability_id": None,
            "input_refs": {},
            "formula_ids": list(pair),
            "boundary_target_ids": None,
            "task_contract_ids": [task_id.group(0)],
        }

    navigation = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "navigator.events.jsonl"),
        agent_fn=leaf,
        attempt_id="attempt:task-e2e",
        campaign_id="campaign:task-e2e",
        max_rounds=2,
        max_finalists=1,
    )
    program = TheoryProgram.from_json(navigation["finalists"][0]["theory_program"])
    assert program.schema == THEORY_PROGRAM_V2
    assert not program.prediction_formula_ids
    assert len(program.task_discharge_contracts) == 1

    boundary = run_frontier_boundaries(
        context,
        blueprint,
        navigation,
        TheoryCampaignJournal(tmp_path / "boundary.events.jsonl"),
        ExplorationBudgetLedger(
            tmp_path / "budget.events.jsonl",
            budget_preset("smoke_20m"),
            attempt_id="attempt:task-e2e",
        ),
        attempt_id="attempt:task-e2e",
        campaign_id="campaign:task-e2e",
    ).to_json()
    assert boundary["query_results"] == []

    bundle = _adjudicate_theory_program_tasks(
        tmp_path,
        adapter_id=blueprint.adapter_id,
        navigation=navigation,
        boundary_result=boundary,
    )
    assert _boundary_completion_covers(
        {"boundary_result": boundary, "theory_task_discharge": bundle},
        blueprint.verification_plan,
        navigation,
        lean_requested=False,
        isabelle_requested=False,
    )
    run = {
        "status": "frontier_candidates_frozen_awaiting_boundary_approval",
        "navigation": {
            **navigation,
            "lineage_synthesis": {
                "route": "proceed_boundary",
                "objective_contract": {
                    "schema": "leanmill.frontier_objective_contract.v1",
                    "instruction": "Classify the selected presentation extent.",
                },
                "program_ids": [program.program_id],
            },
        },
        "run_digest": "run:task-e2e",
    }
    closed = _consume_theory_task_discharge(
        tmp_path,
        run,
        {"boundary_result": boundary, "theory_task_discharge": bundle},
    )
    assert closed["status"] == "frontier_objective_discharged"
    assert bundle["explicit_program_status"] == "discharged"


def test_existing_boundary_discharge_closes_typed_program_without_model_call(
    tmp_path, monkeypatch
):
    from ztare.leanmill.adapters import generic_fol_finite

    task = TaskDischargeContract(
        contract_id="task:heldout-classification",
        adjudicator_id="test.heldout_classification.v1",
        lifecycle_scope="campaign:test",
        owner="lineage:test",
        parameters={"classification_ref": "partition:test"},
    )
    program = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id="lineage:test",
        context_hash="context:test",
        context_epoch=0,
        presentation_formula_ids=("formula:premise",),
        prediction_formula_ids=(),
        selection_receipt_id="selection:test",
        schema=THEORY_PROGRAM_V2,
        task_discharge_contracts=(task,),
    )
    boundary_core = {
        "schema": "leanmill.frontier_boundary_result.v1",
        "context_hash": "context:test",
        "query_results": [],
        "stop_reason": "campaign_finished",
        "next_epoch_proposal": None,
    }
    boundary = {**boundary_core, "result_sha256": content_hash(boundary_core)}

    def adjudicator(*, contract, boundary_result):
        return TaskDischargeReceipt(
            contract_sha256=contract.sha256,
            adjudicator_id=contract.adjudicator_id,
            status="discharged",
            authority="test.registered_adapter",
            observed={"classification_changed": True},
            evidence_refs=(boundary_result["result_sha256"],),
        )

    monkeypatch.setitem(
        generic_fol_finite.CAPABILITIES,
        "task_discharge_adjudicator",
        adjudicator,
    )
    bundle = _adjudicate_theory_program_tasks(
        tmp_path,
        adapter_id="generic_fol_finite.v1",
        navigation={"finalists": [{"theory_program": program.to_json()}]},
        boundary_result=boundary,
    )
    synthesis = {
        "route": "proceed_boundary",
        "objective_contract": {
            "schema": "leanmill.frontier_objective_contract.v1",
            "instruction": "Change the held-out classification.",
        },
        "program_ids": [program.program_id],
    }
    run = {
        "status": "frontier_candidates_frozen_awaiting_boundary_approval",
        "navigation": {
            "finalists": [{
                "theory_program": program.to_json(),
                "theory_program_id": program.program_id,
            }],
            "lineage_synthesis": synthesis,
        },
        "run_digest": "run:source",
    }
    completion = {
        "boundary_result": boundary,
        "theory_task_discharge": bundle,
    }
    closed = _consume_theory_task_discharge(tmp_path, run, completion)

    assert closed["status"] == "frontier_objective_discharged"
    assert bundle["explicit_program_status"] == "discharged"


    deliveries = [
        json.loads(line)
        for line in (tmp_path / "consequence_delivery.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [row["event"] for row in deliveries] == ["produced", "consumed"]
    assert {row["outcome"] for row in deliveries} == {"discharged"}
    _consume_theory_task_discharge(tmp_path, closed, completion)
    assert len(
        (tmp_path / "consequence_delivery.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ) == 2

    unauthorized = tmp_path / "unauthorized"
    unbound_bundle = _adjudicate_theory_program_tasks(
        unauthorized,
        adapter_id="generic_fol_finite.v1",
        navigation={"finalists": [{"theory_program": program.to_json()}]},
        boundary_result=boundary,
    )
    unbound = _consume_theory_task_discharge(
        unauthorized,
        {
            **run,
            "navigation": {
                "finalists": [{
                    "theory_program": program.to_json(),
                    "theory_program_id": program.program_id,
                }],
            },
        },
        {"boundary_result": boundary, "theory_task_discharge": unbound_bundle},
    )
    assert unbound["status"] == "frontier_candidates_frozen_awaiting_boundary_approval"
    assert unbound["navigation"]["theory_task_discharge"]["objective_status"] == (
        "not_declared"
    )

    wrong_program = TheoryProgram(
        campaign_id=program.campaign_id,
        lineage_id=program.lineage_id,
        context_hash=program.context_hash,
        context_epoch=program.context_epoch,
        presentation_formula_ids=program.presentation_formula_ids,
        prediction_formula_ids=(),
        selection_receipt_id="selection:other",
        schema=THEORY_PROGRAM_V2,
        task_discharge_contracts=(task,),
    )
    with pytest.raises(ValueError, match="not a frozen program output"):
        _consume_theory_task_discharge(
            tmp_path / "cross-program",
            {
                **run,
                "navigation": {
                    "finalists": [{
                        "theory_program": wrong_program.to_json(),
                        "theory_program_id": wrong_program.program_id,
                    }],
                    "lineage_synthesis": synthesis,
                },
            },
            completion,
        )


@pytest.mark.parametrize(
    "search_status",
    ["unknown", "no_premise_model_at_fixed_size"],
)
def test_boundary_completion_consumes_typed_finite_search_outcome(search_status):
    navigation = {
        "finalists": [
            {
                "formula_ids": ["formula:premise"],
                "boundary_target_ids": ["formula:target"],
            }
        ]
    }
    boundary_core = {
        "schema": "leanmill.frontier_boundary_result.v1",
        "context_hash": "context:test",
        "query_results": [
            {
                "candidate_kind": "compact_axiom_pack",
                "premise_formula_ids": ["formula:premise"],
                "target_formula_id": "formula:target",
                "program_prediction_status": "pending",
                "countermodel_searches": [
                    {
                        "status": search_status,
                        "sort_sizes": {"S0": 9},
                        "carrier_size": 9,
                    }
                ],
            }
        ],
        "stop_reason": "campaign_finished",
        "next_epoch_proposal": None,
    }
    boundary = {**boundary_core, "result_sha256": content_hash(boundary_core)}

    assert _boundary_completion_covers(
        {"boundary_result": boundary},
        {"larger_model_strata": [{"sort_sizes": {"S0": 9}}]},
        navigation,
        lean_requested=False,
        isabelle_requested=False,
    )


def test_positive_boundary_evidence_cannot_discharge_outer_objective():
    objective = {
        "schema": "leanmill.frontier_objective_contract.v1",
        "instruction": "Invent a representation that changes a classification question.",
    }
    run = {
        "status": "frontier_candidates_frozen_awaiting_boundary_approval",
        "context_hash": "context:test",
        "run_digest": "run:test",
        "context_summary": {"context_epoch": 0},
        "navigation": {
            "context_epoch": 0,
            "lineage_synthesis": {"objective_contract": objective},
            "finalists": [{
                "formula_ids": ["formula:premise"],
                "boundary_target_ids": ["formula:target"],
                "theory_program_id": "theory-program:test",
            }],
        },
    }
    model_core = {"schema": "test.model_boundary", "status": "no_countermodel"}
    model_receipt = {**model_core, "receipt_sha256": content_hash(model_core)}
    lean_core = {"schema": "test.lean_boundary", "status": "proved_attributed"}
    lean_receipt = {**lean_core, "receipt_sha256": content_hash(lean_core)}
    row = {
        "candidate_kind": "theory_program",
        "premise_formula_ids": ["formula:premise"],
        "target_formula_id": "formula:target",
        "program_prediction_status": "kernel_verified_attributed",
        "countermodel_searches": [model_receipt],
        "lean": {"governed_attempt": lean_receipt},
    }
    completion = {
        "boundary_result": {
            "result_sha256": "boundary:test",
            "query_results": [row],
        }
    }

    feedback = _boundary_search_feedback(run, completion)
    assert feedback is not None
    assert feedback["failed_predictions"] == []
    assert feedback["route"] == "continue_search"
    assert feedback["prediction_outcomes"][0]["evidence_refs"] == [
        model_receipt["receipt_sha256"],
        lean_receipt["receipt_sha256"],
    ]
    assert "outer campaign objective" in feedback["kill_condition"]

    run_without_objective = {
        **run,
        "navigation": {
            **run["navigation"],
            "lineage_synthesis": {"objective_contract": None},
        },
    }
    assert _boundary_search_feedback(run_without_objective, completion) is None

    refuted = {
        **row,
        "program_prediction_status": "refuted_by_larger_model",
    }
    refuted_completion = {
        "boundary_result": {
            "result_sha256": "boundary:refuted",
            "query_results": [refuted],
        }
    }
    assert _boundary_search_feedback(run_without_objective, refuted_completion) is not None


def test_boundary_survivor_identity_crosses_search_waves():
    finalist = {
        "node_id": "node:test",
        "theory_program_id": "theory-program:test",
    }
    positive = {
        "schema": "leanmill.boundary_search_feedback.v1",
        "receipt_sha256": "feedback:positive",
        "program_ids": ["theory-program:test"],
        "prediction_outcomes": [{
            "program_ids": ["theory-program:test"],
            "target_formula_id": "formula:target",
            "status": "pending",
        }],
    }
    survivors = _active_objective_finalists({
        "finalists": [finalist],
        "objective_review_history": [positive],
    })
    assert [row["theory_program_id"] for row in survivors] == [
        "theory-program:test"
    ]
    assert survivors[0]["objective_feedback"] == positive
    assert _objective_navigation_phase({
        "navigation": {"objective_review_history": [positive]}
    }) == "expansion"
    assert _objective_navigation_phase({"navigation": {}}) == "navigation"
    assert _lineage_synthesis_retry_required({
        "status": "frontier_objective_unmet",
        "navigation": {
            "objective_review_history": [positive],
            "lineage_synthesis_budget_stop": {"reason": "budget"},
        },
    })

    refuted = {
        **positive,
        "receipt_sha256": "feedback:refuted",
        "prediction_outcomes": [{
            "program_ids": ["theory-program:test"],
            "target_formula_id": "formula:target",
            "status": "refuted_by_larger_model",
        }],
    }
    assert _active_objective_finalists({
        "objective_survivors": list(survivors),
        "objective_review_history": [positive, refuted],
    }) == ()


def test_source_epoch_candidate_is_archived_before_target_epoch_boundary(tmp_path):
    source = _objective_program_row(
        "source-epoch", "lineage:source-epoch", "formula:source"
    )
    navigation = {
        "context_hash": "context:target",
        "context_epoch": 1,
        "finalists": [source],
        "objective_survivors": [source],
        "lineage_synthesis": {
            "route": "proceed_boundary",
            "program_ids": [source["theory_program_id"]],
        },
    }
    core = {
        "schema": "leanmill.frontier_exploration_run.v1",
        "status": "frontier_candidates_frozen_awaiting_boundary_approval",
        "brief_id": "brief:test",
        "attempt_dir": str(tmp_path),
        "blueprint_id": "blueprint:test",
        "context_hash": "context:target",
        "packet_digest": "packet:test",
        "navigation": navigation,
        "adapter_gap": None,
        "context_summary": {"context_epoch": 1},
        "provider_calls": 0,
        "preparation_provider_calls": 0,
        "budget_digest": "budget:test",
        "budget_stop_receipt": None,
    }
    run = {**core, "run_digest": content_hash(core)}
    write_json_atomic(tmp_path / "run.json", run)

    repaired = _archive_cross_context_active_candidates(tmp_path, run)

    assert repaired["status"] == "frontier_objective_unmet"
    assert repaired["navigation"]["finalists"] == []
    assert repaired["navigation"]["objective_survivors"] == []
    assert "lineage_synthesis" not in repaired["navigation"]
    archive = read_json(
        tmp_path / "cross_context_candidate_archive.epoch-001.json", {}
    )
    assert archive["status"] == "archived_source_epoch_only"
    assert {row["collection"] for row in archive["archived_candidates"]} == {
        "finalists",
        "objective_survivors",
    }
    assert all(
        row["source_context_hash"] == "context:objective-identity"
        and row["source_context_epoch"] == 0
        for row in archive["archived_candidates"]
    )
    assert read_json(tmp_path / "run.json", {}) == repaired


def _objective_program_row(
    label: str,
    lineage_id: str,
    presentation_formula_id: str,
    *,
    selection: str | None = None,
) -> dict:
    program = TheoryProgram(
        campaign_id="campaign:objective-identity",
        lineage_id=lineage_id,
        context_hash="context:objective-identity",
        context_epoch=0,
        presentation_formula_ids=(presentation_formula_id,),
        prediction_formula_ids=(f"formula:target:{label}",),
        selection_receipt_id=selection or f"selection:{label}",
    )
    return {
        "node_id": f"node:{label}",
        "theory_program_id": program.program_id,
        "theory_program": program.to_json(),
    }


def test_refined_survivor_and_disposed_frozen_lineage_both_return():
    finalist_zero = _objective_program_row(
        "zero-old", "lineage:zero", "formula:zero"
    )
    finalist_one = _objective_program_row(
        "one", "lineage:one", "formula:one"
    )
    refined_zero = _objective_program_row(
        "zero-refined",
        "lineage:zero",
        "formula:zero-refined",
    )
    boundary_feedback = {
        "schema": "leanmill.boundary_search_feedback.v1",
        "receipt_sha256": "feedback:zero",
        "program_ids": [finalist_zero["theory_program_id"]],
        "prediction_outcomes": [{
            "program_ids": [finalist_zero["theory_program_id"]],
            "target_formula_id": "formula:target:zero-old",
            "status": "pending",
        }],
    }
    post_freeze_feedback = {
        "schema": "leanmill.post_freeze_research_disposition.v1",
        "receipt_sha256": "feedback:one-disposition",
        "lineage_ids": ["lineage:one"],
        "program_ids": [finalist_one["theory_program_id"]],
        "reviewed_presentation_formula_ids": ["formula:one"],
    }

    active = _active_objective_finalists({
        "finalists": [finalist_zero, finalist_one],
        "objective_survivors": [refined_zero],
        "objective_review_history": [
            boundary_feedback,
            post_freeze_feedback,
        ],
    })

    assert [row["theory_program_id"] for row in active] == [
        refined_zero["theory_program_id"],
        finalist_one["theory_program_id"],
    ]
    assert active[0]["objective_feedback"] == boundary_feedback
    assert active[1]["objective_feedback"] == post_freeze_feedback


def test_same_lineage_deduplicates_and_refined_survivor_wins():
    original = _objective_program_row(
        "same-old", "lineage:same", "formula:same"
    )
    refined = _objective_program_row(
        "same-refined", "lineage:same", "formula:same-refined"
    )
    disposition = {
        "schema": "leanmill.post_freeze_mechanism_feedback.v1",
        "lineage_ids": ["lineage:same"],
        "program_ids": [refined["theory_program_id"]],
    }
    active = _active_objective_finalists({
        "finalists": [original],
        "objective_survivors": [refined],
        "objective_review_history": [disposition],
    })

    assert len(active) == 1
    assert active[0]["theory_program_id"] == refined["theory_program_id"]
    reviewed, lineage_ids, program_ids = _post_freeze_lineage_binding(
        {
            "finalists": [original],
            "objective_survivors": [refined],
        },
        {
            "operational_characterization": {
                "formulas": [
                    {"role": "premise", "formula_id": "formula:same"},
                    {"role": "target", "formula_id": "formula:target"},
                ]
            }
        },
        context_hash="context:objective-identity",
    )
    assert reviewed == ("formula:same",)
    assert lineage_ids == ("lineage:same",)
    assert program_ids == (refined["theory_program_id"],)


def test_post_freeze_presentation_binding_fails_closed_when_unmatched():
    finalist = _objective_program_row(
        "bound", "lineage:bound", "formula:bound"
    )
    with pytest.raises(ValueError, match="matches no frozen theory lineage"):
        _post_freeze_lineage_binding(
            {"finalists": [finalist]},
            {
                "operational_characterization": {
                    "formulas": [
                        {"role": "premise", "formula_id": "formula:other"},
                        {"role": "target", "formula_id": "formula:target"},
                    ]
                }
            },
            context_hash="context:objective-identity",
        )


def test_legacy_post_freeze_feedback_replays_by_exact_program_only():
    original = _objective_program_row(
        "legacy-old", "lineage:legacy", "formula:legacy"
    )
    refined = _objective_program_row(
        "legacy-refined", "lineage:legacy", "formula:legacy-refined"
    )
    legacy = {
        "schema": "leanmill.post_freeze_research_disposition.v1",
        "program_ids": [original["theory_program_id"]],
    }

    assert len(_active_objective_finalists({
        "finalists": [original],
        "objective_review_history": [legacy],
    })) == 1
    assert _active_objective_finalists({
        "finalists": [original],
        "objective_survivors": [refined],
        "objective_review_history": [legacy],
    }) == ()


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


def test_consumed_boundary_route_does_not_activate_deferred_language(tmp_path):
    context, blueprint = _context_and_blueprint()
    blueprint = replace(
        blueprint,
        stop_rule={
            **blueprint.stop_rule,
            "user_instruction": "Require a boundary survivor to advance the objective.",
            "executable_condition": {"kind": "late_lineage_objective_review"},
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
            "finalists": [],
            "theory_language_expansion_requests": [
                {"request_id": "theory-language-request:deferred"}
            ],
            "lineage_synthesis": {
                "route": "proceed_boundary",
                "selected_requests": [],
                "deferred_request_ids": ["theory-language-request:deferred"],
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


def test_stale_selected_formula_returns_to_navigation_without_admission(tmp_path):
    context, blueprint = _context_and_blueprint()
    stale_request = {
        "request_id": "lineage-formula-request:stale",
        "proposal": {
            "source_context_hash": "context:prior",
            "source_epoch": 0,
        },
    }

    def synthesis(route: str, selected: list[dict]) -> dict:
        core = {
            "schema": "leanmill.lineage_synthesis_decision.v1",
            "context_hash": context.context_hash,
            "context_epoch": 0,
            "route": route,
            "selected_requests": selected,
            "receipt_sha256": "",
        }
        core["receipt_sha256"] = content_hash({
            key: value for key, value in core.items() if key != "receipt_sha256"
        })
        return core

    class Navigator:
        accepts_budget_ledger = True
        accepts_theory_conflict_memory = True

        def __init__(self):
            self.calls = 0
            self.waves = 0

        def __call__(self, *_args, **_kwargs):
            self.calls += 1
            row = synthesis(
                "admit_formulas" if self.calls == 1 else "defer_all",
                [stale_request] if self.calls == 1 else [],
            )
            return {
                "context_hash": context.context_hash,
                "context_epoch": 0,
                "search_wave": self.calls,
                "finalists": [],
                "lineage_synthesis": row,
            }

        def begin_search_wave(self):
            self.waves += 1

    navigator = Navigator()
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget_preset("smoke_20m"),
        attempt_id=tmp_path.name,
    )
    packet = packet_for_frontier_context(
        blueprint, context, campaign_id="campaign:stale-request"
    )

    driven = drive_frontier_navigation(
        context,
        blueprint,
        directory=tmp_path,
        campaign_id="campaign:stale-request",
        attempt_id=tmp_path.name,
        journal=TheoryCampaignJournal(tmp_path / "events.jsonl"),
        budget_ledger=ledger,
        navigator_fn=navigator,
        packet_signer=lambda _packet: None,
        packet=packet,
    )

    assert navigator.calls == 2
    assert navigator.waves == 1
    feedback = read_json(
        tmp_path / "stale_lineage_request_feedback.epoch-000.wave-001.json",
        {},
    )
    assert feedback["request_ids"] == [stale_request["request_id"]]
    assert feedback["route"] == "continue_search"
    assert driven.navigation["lineage_synthesis"]["route"] == "defer_all"
    assert driven.navigation["objective_review_history"] == [feedback]


def test_outer_objective_accepts_receipted_terminal_unresolved(tmp_path):
    context, blueprint = _context_and_blueprint()
    blueprint = replace(
        blueprint,
        stop_rule={
            **blueprint.stop_rule,
            "user_instruction": "Invent a representation or stop unresolved.",
            "executable_condition": {"kind": "late_lineage_objective_review"},
        },
    )
    exhausted_core = {
        "schema": "leanmill.host_isolated_navigation_exhausted.v1",
        "context_hash": context.context_hash,
        "context_epoch": 0,
    }
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
            "finalists": [],
            "lineage_synthesis": {"route": "defer_all"},
            "navigation_exhausted_receipt": {
                **exhausted_core,
                "receipt_sha256": content_hash(exhausted_core),
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


def test_predecessor_prefix_forwards_successor_epoch_causal_trace(tmp_path):
    context, blueprint = _context_and_blueprint()
    seen = []

    def navigator(_context, _blueprint, _journal, *, budget_ledger):
        del _context, _blueprint, _journal, budget_ledger
        seen.append(
            {
                "epoch": getattr(navigator, "epoch", None),
                "initial_trace": getattr(navigator, "initial_trace", None),
            }
        )
        return {"status": "successor_called"}

    navigator.begin_context_epoch = lambda **_kwargs: None
    navigator.begin_search_wave = lambda: None
    synthesis_input = {
        "schema": "leanmill.lineage_synthesis_input.v1",
        "context_hash": context.context_hash,
        "context_epoch": 0,
        "formula_requests": [
            {"request_id": "request:a", "proposal": {"formula_id": "formula:a"}}
        ],
        "theory_language_requests": [],
        "frozen_programs": [],
        "objective_contract": None,
        "input_sha256": "input:a",
    }
    role = _ScriptedRole(
        "predecessor",
        {
            "route": "admit_formulas",
            "continuation_mode": "none",
            "selected_request_ids": ["request:a"],
            "deferred_request_ids": [],
            "rationale": "Admit the frozen coordinate.",
            "next_discriminator": "Rebuild and test its composition.",
            "kill_condition": "The coordinate duplicates the chart.",
            "program_ids": [],
            "next_discriminator_request_ids": ["request:a"],
        },
    )
    wrapped = _prepend_predecessor_synthesis(
        navigator, synthesis_input=synthesis_input, synthesis_role=role
    )
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget_preset("smoke_20m"),
        attempt_id=tmp_path.name,
    )
    wrapped(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "events.jsonl"),
        budget_ledger=ledger,
    )
    causal_trace = (
        {
            "decision": "lineage_synthesis_admitted",
            "synthesis_receipt_sha256": "synthesis:a",
        },
    )
    wrapped.epoch = 1
    wrapped.initial_trace = causal_trace

    result = wrapped(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "events.jsonl"),
        budget_ledger=ledger,
    )

    assert result == {"status": "successor_called"}
    assert seen == [{"epoch": 1, "initial_trace": causal_trace}]


def test_wave_and_epoch_transitions_clear_transient_lineage_state(
    monkeypatch, tmp_path
):
    instances = []

    def fake_role(_definition, *, role_name, repo, artifact_dir, instance_id=""):
        del role_name, repo
        instances.append(instance_id)
        role = _ScriptedRole(f"role:{instance_id}", {})
        role.artifact_dir = artifact_dir
        role.calls = []
        return role

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

    transient = {
        "lineage_initial_traces": ((),),
        "preserved_lineage_rows": {0: {}},
        "recovered_lineage_requests": ({},),
        "retry_synthesis": True,
    }
    for name, value in transient.items():
        setattr(navigator, name, value)
    navigator.begin_search_wave()
    assert all(not hasattr(navigator, name) for name in transient)

    for name, value in transient.items():
        setattr(navigator, name, value)
    navigator.begin_context_epoch(source_epoch=0, target_epoch=1)

    assert all(not hasattr(navigator, name) for name in transient)
    assert instances == ["", "wave-001", "wave-002"]
    assert navigator.search_wave == 2


def test_synthesis_only_wave_is_a_durable_search_wave(monkeypatch, tmp_path):
    instances = []

    def fake_role(_definition, *, role_name, repo, artifact_dir, instance_id=""):
        del role_name, repo
        instances.append(instance_id)
        role = _ScriptedRole(f"role:{instance_id}", {})
        role.artifact_dir = artifact_dir
        role.calls = []
        return role

    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.frontier_agent_role",
        fake_role,
    )
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.make_subscription_theory_navigator",
        lambda role, *, attempt_id: (role, attempt_id),
    )
    write_json_atomic(
        tmp_path / "lineage_synthesis_input.epoch-001.wave-008.json",
        {"schema": "leanmill.lineage_synthesis_input.v1"},
    )
    definition = FrontierCampaignDefinition(
        direction="Continue after a synthesis-only wave.",
        source_mode="structure_first",
        budget=budget_preset("smoke_20m"),
    )

    navigator = _make_campaign_theory_navigator(
        definition,
        directory=tmp_path,
        repo=tmp_path,
        attempt_id=tmp_path.name,
    )
    assert navigator.search_wave == 8
    assert instances == ["wave-008"]

    navigator.begin_search_wave()
    assert navigator.search_wave == 9
    assert instances[-1] == "wave-009"


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
            route = "proceed_boundary" if programs else "continue_search"
            return {
                "route": route,
                "continuation_mode": "none" if programs else "current_context",
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
                                    "chart_status": "holds_on_complete_context",
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

    # A later pending segment cannot erase an earlier paid terminal decision.
    pending_dir = tmp_path / "agent_calls" / "navigator.lineage-000.wave-001"
    pending = {
        "decision": "request",
        "capability_id": "list_theory_nodes",
        "input_refs": {"offset": 0, "limit": 1},
        "rationale": "Inspect another node after a materialization retry.",
    }
    pending_text = json.dumps(pending, sort_keys=True, separators=(",", ":"))
    write_text_atomic(pending_dir / "000.result.json", pending_text)
    write_text_atomic(pending_dir / "000.prompt.txt", "prompt\nCURRENT TRACE:\n[]")
    write_json_atomic(
        pending_dir / "000.call.json",
        {
            "returncode": 0,
            "result_digest": content_hash({"result": pending_text}),
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
