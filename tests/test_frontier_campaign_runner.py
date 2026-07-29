from __future__ import annotations

from dataclasses import replace
from itertools import combinations
import json
from pathlib import Path
import re

import pytest

from ztare.leanmill.exploration_budget import ExplorationBudgetLedger, budget_preset
from ztare.leanmill.adapter_forge import (
    ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT,
    AdapterGap,
    adapter_forge_gap_directory,
)
from ztare.leanmill.external_science_admission import _campaign_packet_for_request
from ztare.leanmill.common import read_json, write_json_atomic, write_text_atomic
from ztare.leanmill.explore_axiom_space import (
    _archive_incomplete_boundary,
    _boundary_completion_stop_reason,
    _adjudicate_theory_program_tasks,
    drive_frontier_navigation,
    finish_frontier_navigation,
    packet_for_frontier_context,
)
from ztare.leanmill.finite_theory_context import save_formal_theory_context
from ztare.leanmill.formal_verification_provider import generate_keypair
from ztare.leanmill.frontier_campaign import sign_frontier_campaign
from ztare.leanmill.frontier_campaign_actions import (
    frontier_campaign_status,
    replay_frontier_campaign,
)
from ztare.leanmill.frontier_campaign_definition import FrontierCampaignDefinition
from ztare.leanmill.frontier_boundary import run_frontier_boundaries
from ztare.leanmill.deterministic_frontier_campaign import select_diverse_theory_nodes
from ztare.leanmill.frontier_campaign_runner import (
    _admit_campaign_workbench_successor,
    _active_objective_finalists,
    _archive_stale_evaluation_candidates,
    _archive_cross_context_active_candidates,
    _boundary_search_feedback,
    _consume_theory_task_discharge,
    _lineage_synthesis_retry_required,
    _bind_language_feedback_to_search_wave,
    _language_feedback_wave_binding,
    _objective_feedback_trace_rows,
    _make_campaign_theory_navigator,
    _objective_navigation_phase,
    _objective_resume_has_turn_capacity,
    _objective_continuation_budget_exhausted,
    _pending_durable_lineage_synthesis,
    _post_freeze_lineage_binding,
    _prepend_predecessor_synthesis,
    _registered_formal_task_executor_required,
    _materialize_boundary_budget_stop,
    _pending_extended_boundary,
    _reopen_extended_boundary,
    _reopen_extended_adapter_gap,
    _reopen_extended_navigation,
    _reopen_superseded_adapter_gap,
    _restore_nested_objective_feedback_history,
    _frontier_lifecycle_marker,
    drive_frontier_campaign,
    materialize_frontier_navigation_from_journal,
    next_frontier_campaign_action,
    run_frontier_campaign_definition,
)
from ztare.leanmill.explore_axiom_space import (
    _adjudicate_theory_program_tasks,
    _boundary_completion_covers,
)
from ztare.common.task_discharge import TaskDischargeContract, TaskDischargeReceipt
from ztare.leanmill.theory_program import (
    THEORY_PROGRAM_V1,
    THEORY_PROGRAM_V2,
    TheoryProgram,
)
from ztare.leanmill.theory_campaign_journal import (
    TheoryCampaignEvent,
    TheoryCampaignJournal,
)
from ztare.leanmill.theory_navigator import run_interactive_theory_navigator
from ztare.leanmill.theory_interest import theory_program_information_yield
from ztare.leanmill.theory_interest import CHEAP_CONSEQUENCE_EVALUATOR_REF
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.theory_lineage_synthesis import (
    validate_lineage_synthesis_decision,
)
from ztare.leanmill.reviewed_construction_campaign import (
    RECOVERED_BOUNDARY_FEEDBACK_SCHEMA,
)
from ztare.leanmill.formal_task_boundary import (
    GOVERNED_FORMAL_COUNTEREXAMPLE_ADJUDICATOR,
)

from test_theory_navigator import _context_and_blueprint
from test_adapter_forge import _typed_host_rejection_completion


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


def test_campaign_signer_is_persisted_before_provider_work(
    monkeypatch, tmp_path
) -> None:
    output_root = tmp_path / "runs"
    observed: dict[str, Path] = {}

    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.frontier_agent_role",
        lambda *_args, **_kwargs: type(
            "Role", (), {"agent_id": "test-role"}
        )(),
    )
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.make_subscription_frontier_compiler_roles",
        lambda **_kwargs: (lambda _payload: {}, lambda _payload: {}),
    )
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner._make_campaign_theory_navigator",
        lambda *_args, **_kwargs: (lambda *_nav_args, **_nav_kwargs: {}),
    )

    def stop_after_initialization(
        _definition, *, attempt_dir, attempt_initializer, **_kwargs
    ):
        attempt = Path(attempt_dir)
        attempt.mkdir(parents=True, exist_ok=False)
        attempt_initializer(attempt)
        private = attempt / "private" / "campaign_signer.pem"
        public = attempt / "campaign_signer_public.pem"
        assert private.is_file()
        assert public.is_file()
        assert private.stat().st_mode & 0o777 == 0o600
        assert "BEGIN PRIVATE KEY" in private.read_text(encoding="utf-8")
        assert "BEGIN PUBLIC KEY" in public.read_text(encoding="utf-8")
        observed["attempt"] = attempt
        raise RuntimeError("stop before provider work")

    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.explore_axiom_space",
        stop_after_initialization,
    )
    definition = FrontierCampaignDefinition(
        direction="Exercise crash-safe campaign identity.",
        source_mode="structure_first",
        budget=budget_preset("smoke_20m"),
    )

    with pytest.raises(RuntimeError, match="stop before provider work"):
        run_frontier_campaign_definition(
            definition,
            output_root=output_root,
            repo=tmp_path,
        )

    assert observed["attempt"].parent == output_root


def test_navigation_low_yield_cannot_cancel_frozen_boundary_obligation(
    tmp_path,
) -> None:
    context, blueprint = _context_and_blueprint()
    chosen = select_diverse_theory_nodes(context, max_finalists=1)[0]
    pair = next(
        row
        for row in chosen.minimal_generators
        if len(row) == 2 and context.synergy_ids(row)
    )
    decisions = iter([
        {
            "decision": "freeze",
            "formula_ids": list(pair),
            "rationale": "Freeze one exact bounded discriminator.",
        },
        {"decision": "finish", "rationale": "Boundary now owns adjudication."},
    ])
    navigation = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "navigation.events.jsonl"),
        agent_fn=lambda _prompt: next(decisions),
        attempt_id="attempt:terminal-obligation",
        campaign_id="campaign:terminal-obligation",
        max_rounds=2,
        max_finalists=1,
    )
    budget = budget_preset("smoke_20m")
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget,
        attempt_id="attempt:terminal-obligation",
    )
    for index in range(budget.stop_rule.low_yield_patience):
        ledger.observe_information(
            action_id=f"navigation:low-yield:{index}",
            marginal_information_per_cost_ppm=0,
            coverage_ppm=0,
        )
    assert ledger.soft_stop_reason(allow_coverage_target=False) == (
        "marginal_yield_below_threshold"
    )

    boundary = run_frontier_boundaries(
        context,
        blueprint,
        navigation,
        TheoryCampaignJournal(tmp_path / "boundary.events.jsonl"),
        ledger,
        attempt_id="attempt:terminal-obligation",
        campaign_id="campaign:terminal-obligation",
    )

    assert boundary.query_results
    assert boundary.stop_reason != "marginal_yield_below_threshold"
    assert _boundary_completion_stop_reason(ledger, boundary) == "campaign_finished"
    assert boundary.to_json()["stop_policy"] == (
        "leanmill.frozen_boundary_stop_policy.v2"
    )


def test_legacy_soft_stop_boundary_is_superseded_before_replay(tmp_path) -> None:
    context, blueprint = _context_and_blueprint()
    chosen = select_diverse_theory_nodes(context, max_finalists=1)[0]
    pair = next(
        row
        for row in chosen.minimal_generators
        if len(row) == 2 and context.synergy_ids(row)
    )
    navigation = {
        "context_epoch": 0,
        "search_wave": 4,
        "finalists": [{
            "node_id": chosen.node_id,
            "formula_ids": list(pair),
            "boundary_target_ids": [context.synergy_ids(pair)[0]],
        }],
    }
    run_core = {
        "status": "frontier_candidates_frozen_awaiting_boundary_approval",
        "context_hash": context.context_hash,
        "context_summary": {"context_epoch": 0},
        "navigation": navigation,
    }
    run = {**run_core, "run_digest": content_hash(run_core)}
    write_json_atomic(tmp_path / "run.json", run)
    write_json_atomic(tmp_path / "blueprint.json", blueprint.to_json())
    boundary_core = {
        "schema": "leanmill.frontier_boundary_result.v1",
        "context_hash": context.context_hash,
        "query_results": [],
        "stop_reason": "marginal_yield_below_threshold",
        "next_epoch_proposal": None,
    }
    boundary = {**boundary_core, "result_sha256": content_hash(boundary_core)}
    write_json_atomic(tmp_path / "boundary_result.json", boundary)
    budget = budget_preset("smoke_20m")
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget,
        attempt_id=tmp_path.name,
    )
    stop = ledger.stop_receipt(
        "marginal_yield_below_threshold",
        context_hash=context.context_hash,
    ).to_json()
    write_json_atomic(tmp_path / "budget_stop_receipt.json", stop)
    completion_core = {
        "schema": "leanmill.frontier_boundary_completion.v1",
        "status": "campaign_stopped",
        "attempt_dir": str(tmp_path),
        "context_hash": context.context_hash,
        "boundary_result": boundary,
        "theory_task_discharge": {},
        "budget_stop_receipt": stop,
        "provider_calls": 0,
    }
    completion = {
        **completion_core,
        "completion_sha256": content_hash(completion_core),
    }
    write_json_atomic(tmp_path / "boundary_completion.json", completion)
    write_json_atomic(
        tmp_path / "campaign_closure_gate.json",
        {"schema": "derived_projection", "ready": True},
    )

    assert next_frontier_campaign_action(tmp_path) == "verify_boundary"
    _archive_incomplete_boundary(tmp_path, completion)

    assert not (tmp_path / "boundary_completion.json").exists()
    assert not (tmp_path / "boundary_result.json").exists()
    assert not (tmp_path / "budget_stop_receipt.json").exists()
    assert not (tmp_path / "campaign_closure_gate.json").exists()
    archive = (
        tmp_path / "boundary_attempts" / completion["completion_sha256"][:16]
    )
    assert read_json(archive / "boundary_result.json", {}) == boundary
    receipt = read_json(archive / "boundary_attempt_supersession.json", {})
    assert receipt["supersession_kind"] == (
        "navigation_soft_stop_cannot_cancel_frozen_boundary"
    )
    assert receipt["prior_stop_policy"] == "legacy_unversioned"
    assert receipt["current_stop_policy"] == (
        "leanmill.frozen_boundary_stop_policy.v2"
    )
    receipt_core = {
        key: value for key, value in receipt.items() if key != "receipt_sha256"
    }
    assert receipt["receipt_sha256"] == content_hash(receipt_core)
    status = frontier_campaign_status(tmp_path)
    assert status["boundary_attempt_supersession"]["receipt_sha256"] == (
        receipt["receipt_sha256"]
    )
    assert next_frontier_campaign_action(tmp_path) == "verify_boundary"


def test_boundary_hard_stop_is_resumable_only_after_matching_extension(
    tmp_path,
) -> None:
    context, blueprint = _context_and_blueprint()
    navigation = {
        "context_epoch": 0,
        "finalists": [{
            "formula_ids": [context.formula_ids[0]],
            "boundary_target_ids": [context.formula_ids[1]],
        }],
    }
    run_core = {
        "status": "frontier_candidates_frozen_awaiting_boundary_approval",
        "context_hash": context.context_hash,
        "context_summary": {"context_epoch": 0},
        "navigation": navigation,
    }
    run = {**run_core, "run_digest": content_hash(run_core)}
    write_json_atomic(tmp_path / "run.json", run)
    write_json_atomic(tmp_path / "blueprint.json", blueprint.to_json())
    budget = budget_preset("smoke_20m")
    write_json_atomic(tmp_path / "budget.json", budget.to_json())
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget,
        attempt_id=tmp_path.name,
    )
    stop = ledger.stop_receipt(
        "blocked_before_action:smt_calls",
        context_hash=context.context_hash,
    ).to_json()
    boundary_core = {
        "schema": "leanmill.frontier_boundary_result.v1",
        "context_hash": context.context_hash,
        "query_results": [{
            "premise_formula_ids": [context.formula_ids[0]],
            "target_formula_id": context.formula_ids[1],
            "countermodel_searches": [],
        }],
        "stop_reason": "blocked_before_action:smt_calls",
        "stop_policy": "leanmill.frozen_boundary_stop_policy.v2",
        "next_epoch_proposal": None,
    }
    boundary = {**boundary_core, "result_sha256": content_hash(boundary_core)}
    completion_core = {
        "schema": "leanmill.frontier_boundary_completion.v1",
        "status": "campaign_stopped",
        "attempt_dir": str(tmp_path),
        "context_hash": context.context_hash,
        "stop_policy": "leanmill.frozen_boundary_stop_policy.v2",
        "boundary_result": boundary,
        "theory_task_discharge": {},
        "budget_stop_receipt": stop,
        "provider_calls": 0,
    }
    completion = {
        **completion_core,
        "completion_sha256": content_hash(completion_core),
    }
    write_json_atomic(tmp_path / "boundary_result.json", boundary)
    write_json_atomic(tmp_path / "boundary_completion.json", completion)
    write_json_atomic(tmp_path / "budget_stop_receipt.json", stop)

    stopped = _materialize_boundary_budget_stop(
        tmp_path, run, completion
    )
    assert stopped["status"] == "budget_stopped"
    assert _pending_extended_boundary(tmp_path, stopped) is None

    ledger.extend_resources(
        phase="boundary",
        resources={"smt_calls": 1},
        authority_ref="user:continue:test",
        reason="resume the exact frozen boundary",
    )
    assert next_frontier_campaign_action(tmp_path) == "reopen_extended_boundary"
    _reopen_extended_boundary(tmp_path)
    reopened = read_json(tmp_path / "run.json", {})
    assert reopened["status"] == (
        "frontier_candidates_frozen_awaiting_boundary_approval"
    )
    assert reopened["budget_stop_receipt"] is None
    assert next_frontier_campaign_action(tmp_path) == "verify_boundary"


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


def test_theory_task_discharge_accepts_duplicate_matching_boundary_archives(
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
    for label in ("predecessor-a", "predecessor-b"):
        write_json_atomic(
            tmp_path / "boundary_attempts" / label / "boundary_result.json",
            first,
        )
    second_core = {
        **first_core,
        "query_results": [{"query_id": "successor-boundary"}],
    }
    second = {**second_core, "result_sha256": content_hash(second_core)}

    _adjudicate_theory_program_tasks(
        tmp_path,
        adapter_id="generic_fol_finite.v1",
        navigation={},
        boundary_result=second,
    )

    for label in ("predecessor-a", "predecessor-b"):
        assert read_json(
            tmp_path
            / "boundary_attempts"
            / label
            / "theory_task_discharge.json",
            {},
        ) == first_discharge


def test_boundary_archive_preserves_newer_root_artifact_on_recovery(tmp_path) -> None:
    old_boundary_core = {
        "schema": "leanmill.frontier_boundary_result.v1",
        "context_hash": "context:test",
        "query_results": [],
        "stop_reason": "blocked_before_action:boundary_queries",
    }
    old_boundary = {
        **old_boundary_core,
        "result_sha256": content_hash(old_boundary_core),
    }
    completion_core = {
        "schema": "leanmill.frontier_boundary_completion.v1",
        "context_hash": "context:test",
        "boundary_result": old_boundary,
        "theory_task_discharge": {},
        "budget_stop_receipt": {},
    }
    completion = {
        **completion_core,
        "completion_sha256": content_hash(completion_core),
    }
    new_boundary_core = {
        **old_boundary_core,
        "query_results": [{"query_id": "new-partial-attempt"}],
    }
    new_boundary = {
        **new_boundary_core,
        "result_sha256": content_hash(new_boundary_core),
    }
    write_json_atomic(tmp_path / "boundary_completion.json", completion)
    write_json_atomic(tmp_path / "boundary_result.json", new_boundary)

    _archive_incomplete_boundary(tmp_path, completion)

    archive = tmp_path / "boundary_attempts" / completion["completion_sha256"][:16]
    assert read_json(archive / "boundary_result.json", {}) == old_boundary
    assert read_json(tmp_path / "boundary_result.json", {}) == new_boundary
    assert not (tmp_path / "boundary_completion.json").exists()


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


def _write_recovered_boundary_dispositions(
    directory: Path,
    *,
    context_hash: str,
    program_ids: list[str],
    stage: str = "complete",
    status: str = "witness_rejected",
    coordinate_context_hash: str | None = None,
    persist_feedback: bool = True,
) -> list[dict]:
    rows: list[dict] = []
    coordinates: dict[str, dict] = {}
    for program_id in program_ids:
        coordinate_core = {
            "schema": "leanmill.witness_construction_execution_coordinate.v1",
            "context_hash": coordinate_context_hash or context_hash,
            "adapter_id": "fixture_adapter.v1",
            **{
                field: content_hash({"program_id": program_id, "field": field})
                for field in (
                    "interface_sha256",
                    "target_config_sha256",
                    "artifact_sha256",
                    "predicate_sha256",
                    "witness_schema_sha256",
                    "normalizer_sha256",
                    "verifier_sha256",
                )
            },
        }
        coordinate = {
            **coordinate_core,
            "coordinate_sha256": content_hash(coordinate_core),
        }
        coordinates[program_id] = coordinate
        row_core = {
            "candidate_kind": "theory_task",
            "program_id": program_id,
            "execution_coordinate": coordinate,
            "execution_coordinate_sha256": coordinate["coordinate_sha256"],
            "status": status,
            "stage": stage,
        }
        rows.append({**row_core, "receipt_sha256": content_hash(row_core)})
    boundary_core = {
        "schema": "leanmill.frontier_boundary_result.v1",
        "context_hash": context_hash,
        "query_results": rows,
        "stop_reason": "campaign_finished",
    }
    boundary = {
        **boundary_core,
        "result_sha256": content_hash(boundary_core),
    }
    completion_core = {
        "schema": "leanmill.frontier_boundary_completion.v1",
        "status": "campaign_completed",
        "context_hash": context_hash,
        "boundary_result": boundary,
    }
    write_json_atomic(
        directory / "boundary_completion.json",
        {
            **completion_core,
            "completion_sha256": content_hash(completion_core),
        },
    )
    disposition = {
        "witness_rejected": ("rejected", "revise_construction"),
        "witness_verified": ("verified", "ratify_verified_construction"),
        "capability_unavailable": ("unavailable", "retry_registered_capability"),
    }[status]
    feedback_rows: list[dict] = []
    for program_id, boundary_row in zip(program_ids, rows, strict=True):
        feedback_core = {
            "schema": RECOVERED_BOUNDARY_FEEDBACK_SCHEMA,
            "context_hash": context_hash,
            "context_epoch": 0,
            "program_id": program_id,
            "contract_id": "contract:" + program_id,
            "execution_coordinate": coordinates[program_id],
            "execution_coordinate_sha256": coordinates[program_id][
                "coordinate_sha256"
            ],
            "boundary_result_sha256": boundary["result_sha256"],
            "boundary_row_receipt_sha256": boundary_row["receipt_sha256"],
            "status": status,
            "stage": stage,
            "reason_code": "predicate_rejected",
            "outcome": disposition[0],
            "observed": {"reason": "fixture_miss"},
            "route": disposition[1],
            "authority": "exact_execution_coordinate_replay",
            "claim_boundary": "one exact governed execution",
        }
        feedback = {
            **feedback_core,
            "receipt_sha256": content_hash(feedback_core),
        }
        feedback_rows.append(feedback)
        if persist_feedback:
            write_json_atomic(
                directory
                / (
                    "recovered_boundary_artifact_feedback."
                    f"{feedback['receipt_sha256'][:16]}.json"
                ),
                feedback,
            )
    return feedback_rows


def _write_budget_stopped_recovered_run(
    directory: Path,
    *,
    context_hash: str,
    program_ids: list[str],
    feedback_rows: list[dict],
) -> ExplorationBudgetLedger:
    budget = budget_preset("local_only")
    write_json_atomic(directory / "budget.json", budget.to_json())
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl",
        budget,
        attempt_id=directory.name,
    )
    stop = ledger.stop_receipt(
        "blocked_before_action:expansion:provider_calls",
        context_hash=context_hash,
    ).to_json()
    write_json_atomic(directory / "budget_stop_receipt.json", stop)
    navigation = {
        "recovered_from_durable_results": True,
        "finalists": [
            {"theory_program_id": program_id} for program_id in program_ids
        ],
        "objective_review_history": feedback_rows,
    }
    core = {
        "status": "budget_stopped",
        "context_hash": context_hash,
        "budget_digest": budget.digest,
        "provider_calls": 0,
        "budget_stop_receipt": stop,
        "navigation": navigation,
    }
    write_json_atomic(
        directory / "run.json",
        {**core, "run_digest": content_hash(core)},
    )
    return ledger


@pytest.mark.parametrize(
    "covered_count,expected_action",
    ((3, "complete"), (2, "resume_navigation")),
)
def test_recovered_finalists_require_synthesis_only_for_undisposed_programs(
    tmp_path: Path,
    covered_count: int,
    expected_action: str,
) -> None:
    context_hash = "context:recovered-dispositions"
    program_ids = [f"theory-program:recovered-{index}" for index in range(3)]
    feedback_rows = _write_recovered_boundary_dispositions(
        tmp_path,
        context_hash=context_hash,
        program_ids=program_ids[:covered_count],
    )
    ledger = _write_budget_stopped_recovered_run(
        tmp_path,
        context_hash=context_hash,
        program_ids=program_ids,
        feedback_rows=feedback_rows,
    )

    assert ledger.remaining_capacity("expansion", "provider_calls") == 0
    assert next_frontier_campaign_action(tmp_path) == expected_action


@pytest.mark.parametrize(
    "case",
    ("normalization_stage", "foreign_coordinate", "unavailable", "unfrozen"),
)
def test_recovered_feedback_false_positive_does_not_discharge_synthesis(
    tmp_path: Path,
    case: str,
) -> None:
    context_hash = "context:recovered-false-positive"
    program_ids = ["theory-program:recovered-false-positive"]
    feedback_rows = _write_recovered_boundary_dispositions(
        tmp_path,
        context_hash=context_hash,
        program_ids=program_ids,
        stage=(
            "normalization"
            if case == "normalization_stage"
            else "verification"
            if case == "unavailable"
            else "complete"
        ),
        status=(
            "capability_unavailable"
            if case == "unavailable"
            else "witness_rejected"
        ),
        coordinate_context_hash=(
            "context:foreign-coordinate"
            if case == "foreign_coordinate"
            else None
        ),
        persist_feedback=case != "unfrozen",
    )
    _write_budget_stopped_recovered_run(
        tmp_path,
        context_hash=context_hash,
        program_ids=program_ids,
        feedback_rows=feedback_rows,
    )

    assert next_frontier_campaign_action(tmp_path) == "resume_navigation"


def test_duplicate_recovered_disposition_does_not_discharge_synthesis(
    tmp_path: Path,
) -> None:
    context_hash = "context:duplicate-recovered-disposition"
    program_ids = [f"theory-program:duplicate-{index}" for index in range(3)]
    feedback_rows = _write_recovered_boundary_dispositions(
        tmp_path,
        context_hash=context_hash,
        program_ids=program_ids,
    )
    _write_budget_stopped_recovered_run(
        tmp_path,
        context_hash=context_hash,
        program_ids=program_ids,
        feedback_rows=[*feedback_rows, feedback_rows[0]],
    )

    assert next_frontier_campaign_action(tmp_path) == "resume_navigation"


def test_bootstrap_adapter_gap_stops_before_context_owned_language_expansion(
    tmp_path,
) -> None:
    gap = AdapterGap(
        brief_digest="brief:bootstrap",
        proposed_adapter_id="unreviewed_frontier_adapter.v1",
        primitive_semantics_contract={"requested_from": "campaign_compilation"},
        raw_fixture_refs=("sha256:fixture",),
        required_context_kind="exact",
        required_operations=("compile",),
        required_receipts=("review",),
        forbidden_authorities=("live_registry_mutation",),
        acceptance_tests=("registered adapter preflight passes",),
        gap_kind="adapter_missing",
    )
    write_json_atomic(tmp_path / "adapter_gap.json", gap.to_json())
    run_core = {
        "status": "blocked_adapter_gap",
        "blueprint_id": "",
        "context_hash": "",
        "navigation": {},
        "adapter_gap": gap.to_json(),
    }
    write_json_atomic(
        tmp_path / "run.json",
        {**run_core, "run_digest": content_hash(run_core)},
    )

    assert next_frontier_campaign_action(tmp_path) == (
        "bootstrap_adapter_authority_required"
    )
    assert drive_frontier_campaign(tmp_path) == tmp_path


def test_evaluator_upgrade_archives_program_selected_under_prior_baseline(
    tmp_path,
) -> None:
    stale = {
        "node_id": "node:stale-evaluator",
        "theory_program_id": "theory-program:stale-evaluator",
        "theory_program": {"schema": "leanmill.theory_program.v1"},
        "residual_information_yield": {
            "baseline_ref": "leanmill.bidirectional_equational_deduction.v8"
        },
    }
    current = {
        "node_id": "node:current-evaluator",
        "theory_program_id": "theory-program:current-evaluator",
        "theory_program": {"schema": "leanmill.theory_program.v1"},
        "baseline_evaluator_ref": CHEAP_CONSEQUENCE_EVALUATOR_REF,
        "residual_information_yield": {
            "baseline_ref": "leanmill.first_order_logical_deduction.v9"
        },
    }
    core = {
        "status": "frontier_leaf_decision_pending",
        "context_hash": "context:evaluator-upgrade",
        "context_summary": {"context_epoch": 3},
        "navigation": {
            "context_epoch": 3,
            "finalists": [stale, current],
            "objective_survivors": [stale],
            "lineage_synthesis": {"status": "selected"},
        },
    }
    run = {**core, "run_digest": content_hash(core)}
    write_json_atomic(tmp_path / "run.json", run)

    updated = _archive_stale_evaluation_candidates(tmp_path, run)

    assert updated["status"] == "frontier_objective_unmet"
    assert updated["navigation"]["finalists"] == [current]
    assert updated["navigation"]["objective_survivors"] == []
    assert "lineage_synthesis" not in updated["navigation"]
    history = updated["navigation"]["objective_review_history"]
    assert history[-1]["schema"] == (
        "leanmill.candidate_evaluation_contract_supersession.v1"
    )
    assert history[-1]["current_evaluator_ref"] == (
        CHEAP_CONSEQUENCE_EVALUATOR_REF
    )
    archived = history[-1]["archived_candidates"]
    assert {row["collection"] for row in archived} == {
        "finalists",
        "objective_survivors",
    }
    replay = _archive_stale_evaluation_candidates(tmp_path, updated)
    assert replay == updated


def test_budget_extension_reopens_unconsumed_gap_by_identity(
    tmp_path,
) -> None:
    context_hash = "context:current"
    request_id = "theory-language-request:current"
    gap = AdapterGap(
        brief_digest="brief:current",
        proposed_adapter_id="generic_fol_finite.v1",
        primitive_semantics_contract={
            "source_adapter_id": "generic_fol_finite.v1",
            "theory_language_request": {
                "request_id": request_id,
                "source_context_hash": context_hash,
            },
        },
        raw_fixture_refs=("sha256:fixture",),
        required_context_kind="exact",
        required_operations=("lower_theory_language_request", "build_context"),
        required_receipts=("determinism",),
        forbidden_authorities=("live_registry_mutation",),
        acceptance_tests=("separate the frozen pair",),
        gap_kind="capability_missing",
        missing_capabilities=("theory_language:quotient_or_coordinate_change",),
    ).to_json()
    write_json_atomic(tmp_path / "adapter_gap.json", gap)
    stale_gap_id = "adapter-gap:historical"
    completion_core = {
        "schema": "leanmill.adapter_forge_completion.v1",
        "gap_id": stale_gap_id,
        "status": "adapter_proposal_rejected_return_to_search",
        "reason": "historical_gap_rejection",
        "evidence_refs": ["receipt:historical"],
    }
    write_json_atomic(
        tmp_path / "adapter_forge_completion.json",
        {
            **completion_core,
            "completion_sha256": content_hash(completion_core),
        },
    )
    forge_receipt_core = {
        "schema": "leanmill.adapter_forge_quarantine_receipt.v1",
        "gap_id": stale_gap_id,
        "status": "quarantined_capability_rejected",
    }
    forge_receipt = {
        **forge_receipt_core,
        "receipt_sha256": content_hash(forge_receipt_core),
    }
    write_json_atomic(tmp_path / "adapter_forge_receipt.json", forge_receipt)
    feedback_core = {
        "schema": "leanmill.theory_language_compilation_feedback.v1",
        "request_id": request_id,
        "context_hash": context_hash,
        "outcome": "rejected",
        "reason": "host conformance rejected the proposal before review",
        "evidence_refs": [forge_receipt["receipt_sha256"]],
    }
    feedback = {
        **feedback_core,
        "receipt_sha256": content_hash(feedback_core),
    }
    write_json_atomic(
        tmp_path / "theory_language_compilation_feedback.json", feedback
    )
    budget = budget_preset("smoke_20m")
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget,
        attempt_id=tmp_path.name,
    )
    stop = ledger.stop_receipt("blocked_before_action:expansion:provider_calls")
    ledger.extend_resources(
        phase="expansion",
        resources={"provider_calls": 1},
        authority_ref="user:continue:test",
        reason="retry the current gap",
    )
    navigation = {"objective_review_history": [feedback]}
    run_core = {
        "status": "budget_stopped",
        "context_hash": context_hash,
        "navigation": navigation,
        "budget_stop_receipt": stop.to_json(),
        "adapter_gap": None,
    }
    write_json_atomic(
        tmp_path / "run.json",
        {**run_core, "run_digest": content_hash(run_core)},
    )

    assert next_frontier_campaign_action(tmp_path) == (
        "reopen_extended_adapter_gap"
    )
    _reopen_extended_adapter_gap(tmp_path)
    repaired = read_json(tmp_path / "run.json", {})
    assert repaired["status"] == "blocked_adapter_gap"
    assert repaired["adapter_gap"]["gap_id"] == gap["gap_id"]
    assert repaired["budget_stop_receipt"] is None
    assert next_frontier_campaign_action(tmp_path) == "advance_language"
    assert len(list(tmp_path.glob("budget_extension_reopen.*.json"))) == 1
    assert read_json(tmp_path / "adapter_forge_completion.json", {})["gap_id"] == (
        stale_gap_id
    )


def test_budget_extension_reopens_stopped_navigation_by_context(
    tmp_path,
) -> None:
    budget = budget_preset("smoke_20m")
    write_json_atomic(tmp_path / "budget.json", budget.to_json())
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget,
        attempt_id=tmp_path.name,
    )
    stop = ledger.stop_receipt(
        "blocked_before_action:navigation:provider_calls",
        context_hash="context:successor",
    )
    navigation = {"context_epoch": 1, "trace": [{"decision": "budget_stop"}]}
    run_core = {
        "status": "budget_stopped",
        "context_hash": "context:successor",
        "navigation": navigation,
        "budget_stop_receipt": stop.to_json(),
    }
    write_json_atomic(
        tmp_path / "run.json",
        {**run_core, "run_digest": content_hash(run_core)},
    )
    ledger.extend_resources(
        phase="navigation",
        resources={"provider_calls": 2},
        authority_ref="principal:test",
        reason="inspect the admitted successor context",
    )

    assert next_frontier_campaign_action(tmp_path) == (
        "reopen_extended_navigation"
    )
    _reopen_extended_navigation(tmp_path)
    reopened = read_json(tmp_path / "run.json", {})
    assert reopened["status"] == "frontier_objective_unmet"
    assert reopened["budget_stop_receipt"] is None
    receipt = reopened["navigation"]["navigation_budget_extension_reopen"]
    assert receipt["context_hash"] == "context:successor"
    assert receipt["superseded_budget_stop_receipt"] == stop.to_json()


def test_host_contract_supersession_reopens_exact_rejected_gap(tmp_path) -> None:
    context_hash = "context:current"
    request_id = "theory-language-request:current"
    gap = AdapterGap(
        brief_digest="brief:current",
        proposed_adapter_id="generic_fol_finite.v1",
        primitive_semantics_contract={
            "source_adapter_id": "generic_fol_finite.v1",
            "theory_language_request": {
                "request_id": request_id,
                "source_context_hash": context_hash,
            },
        },
        raw_fixture_refs=("sha256:fixture",),
        required_context_kind="exact",
        required_operations=("lower_theory_language_request", "build_context"),
        required_receipts=("determinism",),
        forbidden_authorities=("live_registry_mutation",),
        acceptance_tests=("separate the frozen pair",),
        gap_kind="capability_missing",
        missing_capabilities=("theory_language:quotient_or_coordinate_change",),
    )
    write_json_atomic(tmp_path / "adapter_gap.json", gap.to_json())
    old_contract = "leanmill.adapter_forge.host_conformance.precontract.v0"
    old_completion = _typed_host_rejection_completion(
        tmp_path,
        gap,
        ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT,
    )
    old_host = dict(old_completion["quarantine_receipt"]["host_conformance"])
    old_host["host_conformance_contract"] = old_contract
    old_host_core = {
        key: value for key, value in old_host.items() if key != "receipt_sha256"
    }
    old_host["receipt_sha256"] = content_hash(old_host_core)
    old_review = dict(
        old_completion["quarantine_receipt"]["independent_review"]
    )
    old_review["host_rejection_receipt_sha256"] = old_host["receipt_sha256"]
    old_quarantine = dict(old_completion["quarantine_receipt"])
    old_quarantine["host_conformance"] = old_host
    old_quarantine["independent_review"] = old_review
    old_quarantine_core = {
        key: value
        for key, value in old_quarantine.items()
        if key != "receipt_sha256"
    }
    old_quarantine["receipt_sha256"] = content_hash(old_quarantine_core)
    completion_core = {
        **{
            key: value
            for key, value in old_completion.items()
            if key != "completion_sha256"
        },
        "host_conformance_contract": old_contract,
        "quarantine_receipt": old_quarantine,
        "evidence_refs": [old_quarantine["receipt_sha256"]],
    }
    old_completion = {
        **completion_core,
        "completion_sha256": content_hash(completion_core),
    }
    old_receipt = old_quarantine["receipt_sha256"]
    old_path = (
        adapter_forge_gap_directory(tmp_path, gap.gap_id, create=True)
        / "adapter_forge_completion.json"
    )
    write_json_atomic(old_path, old_completion)
    feedback_core = {
        "schema": "leanmill.theory_language_compilation_feedback.v1",
        "request_id": request_id,
        "context_hash": context_hash,
        "outcome": "rejected",
        "reason": "host conformance rejected the proposal before review",
        "evidence_refs": [old_receipt],
    }
    feedback = {
        **feedback_core,
        "receipt_sha256": content_hash(feedback_core),
    }
    write_json_atomic(
        tmp_path / "theory_language_compilation_feedback.json", feedback
    )
    run_core = {
        "status": "frontier_objective_unmet",
        "context_hash": context_hash,
        "navigation": {"objective_review_history": [feedback]},
        "adapter_gap": None,
    }
    write_json_atomic(
        tmp_path / "run.json",
        {**run_core, "run_digest": content_hash(run_core)},
    )

    assert next_frontier_campaign_action(tmp_path) == (
        "reopen_superseded_adapter_gap"
    )
    _reopen_superseded_adapter_gap(tmp_path)
    repaired = read_json(tmp_path / "run.json", {})
    assert repaired["status"] == "blocked_adapter_gap"
    assert repaired["adapter_gap"]["gap_id"] == gap.gap_id
    assert repaired["navigation"]["objective_review_history"][-1]["schema"] == (
        "leanmill.adapter_forge_host_contract_supersession.v1"
    )
    assert read_json(old_path, {}) == old_completion
    assert next_frontier_campaign_action(tmp_path) == "advance_language"


def test_language_feedback_owns_a_crash_replayable_search_wave(tmp_path) -> None:
    feedback_core = {
        "schema": "leanmill.theory_language_compilation_feedback.v1",
        "request_id": "theory-language-request:current",
        "context_hash": "context:current",
        "outcome": "rejected",
        "reason": "coordinate retained source identity",
        "evidence_refs": ["receipt:host"],
        "route": "continue_search",
        "program_ids": [],
        "repeat_requires_new_evidence": True,
        "authority": "host_language_compiler",
    }
    feedback = {
        **feedback_core,
        "receipt_sha256": content_hash(feedback_core),
    }

    binding = _bind_language_feedback_to_search_wave(
        tmp_path,
        feedback=feedback,
        context_hash="context:current",
        context_epoch=2,
        search_wave=15,
    )

    assert binding["search_wave"] == 15
    assert _language_feedback_wave_binding(tmp_path, feedback) == binding
    assert _bind_language_feedback_to_search_wave(
        tmp_path,
        feedback=feedback,
        context_hash="context:current",
        context_epoch=2,
        search_wave=15,
    ) == binding
    with pytest.raises(ValueError, match="cannot bind"):
        _bind_language_feedback_to_search_wave(
            tmp_path,
            feedback=feedback,
            context_hash="context:other",
            context_epoch=2,
            search_wave=16,
        )


def test_execution_feedback_carries_typed_receipt_into_navigation_wave(
    tmp_path,
) -> None:
    execution_core = {
        "schema": "leanmill.finite_family_execution.v1",
        "request_id": "theory-language-request:execution",
        "status": "exhausted_without_witness",
    }
    execution = {
        **execution_core,
        "receipt_sha256": content_hash(execution_core),
    }
    feedback_core = {
        "schema": "leanmill.theory_language_execution_feedback.v1",
        "request_id": "theory-language-request:execution",
        "context_hash": "context:execution",
        "outcome": "exhausted",
        "reason": "the reviewed finite family produced no target witness",
        "evidence_refs": [execution["receipt_sha256"]],
        "route": "continue_search",
        "program_ids": [],
        "repeat_requires_new_evidence": True,
        "authority": "host_language_executor",
    }
    feedback = {
        **feedback_core,
        "receipt_sha256": content_hash(feedback_core),
    }
    navigation = {
        "carried_evidence_receipts": [
            {
                "evidence_ref": execution["receipt_sha256"],
                "receipt": execution,
            }
        ]
    }

    rows = _objective_feedback_trace_rows(
        navigation,
        feedback,
        context_hash="context:execution",
    )
    binding = _bind_language_feedback_to_search_wave(
        tmp_path,
        feedback=feedback,
        context_hash="context:execution",
        context_epoch=3,
        search_wave=4,
    )

    assert rows[0]["decision"] == "objective_feedback"
    assert rows[1] == {
        "decision": "objective_feedback_evidence",
        "evidence_ref": execution["receipt_sha256"],
        "receipt": execution,
        "source_feedback_receipt_sha256": feedback["receipt_sha256"],
        "host_finalized": True,
    }
    assert binding["request_id"] == feedback["request_id"]
    assert binding["search_wave"] == 4

    corrupted = dict(execution)
    corrupted["status"] = "fabricated_witness"
    with pytest.raises(ValueError, match="receipt_sha256 does not replay"):
        _objective_feedback_trace_rows(
            {
                "carried_evidence_receipts": [
                    {
                        "evidence_ref": execution["receipt_sha256"],
                        "receipt": corrupted,
                    }
                ]
            },
            feedback,
            context_hash="context:execution",
        )


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


@pytest.mark.parametrize(
    "status",
    ["frontier_leaf_decision_pending", "frontier_objective_unmet"],
)
def test_frontier_lifecycle_finalizes_exhausted_objective_continuation(
    tmp_path, monkeypatch, status
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
        "status": status,
        "context_hash": "context:test",
        "navigation": {"lineage_synthesis_budget_stop": stop},
    }
    write_json_atomic(
        tmp_path / "run.json", {**core, "run_digest": content_hash(core)}
    )
    monkeypatch.setattr(
        runner,
        "_objective_continuation_budget_exhausted",
        lambda _directory, _run: True,
    )

    assert next_frontier_campaign_action(tmp_path) == "finalize_budget_stop"


def test_objective_budget_stop_precedes_pending_leaf_status(tmp_path) -> None:
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
            "pending_leaf_decisions": [{"request_id": "leaf:pending"}],
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
    predecessor = TheoryProgram(
        campaign_id="campaign:axiompack",
        lineage_id="lineage:axiompack",
        context_hash=context.context_hash,
        context_epoch=0,
        presentation_formula_ids=context.formula_ids[:1],
        prediction_formula_ids=context.formula_ids[1:2],
        selection_receipt_id="selection:axiompack",
        schema=THEORY_PROGRAM_V1,
    )
    navigation = {
        "finalists": [
            {
                "candidate_kind": "theory_program",
                "theory_program_id": program.program_id,
                "theory_program": program.to_json(),
            }
        ],
        # A same-lineage predecessor may remain as an objective survivor, but
        # it cannot hide a formal obligation owned by the selected successor.
        "objective_survivors": [
            {
                "candidate_kind": "theory_program",
                "theory_program_id": predecessor.program_id,
                "theory_program": predecessor.to_json(),
            }
        ],
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
    pair = (
        "formula:6a860f4453a684d98cdc0bcb4525ad891fba32e4079b5b9a8712c47764a75f63",
    )
    assert pair[0] in context.formula_ids
    selection_prediction = theory_program_information_yield(
        context, pair
    ).residual_prediction_ids[0]

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
                "rationale": "Select the presentation under the current evaluator first.",
                "capability_id": "select_theory_presentation",
                "input_refs": {
                    "formula_ids": list(pair),
                    "prediction_formula_ids": [selection_prediction],
                },
                "formula_ids": None,
                "boundary_target_ids": None,
            }
        if calls == 2:
            receipt_ids = re.findall(r'"receipt_id":"(sha256:[0-9a-f]{64})"', prompt)
            assert receipt_ids
            return {
                "decision": "request",
                "rationale": "Ask the adapter to classify this presentation extent.",
                "capability_id": "propose_theory_task",
                "input_refs": {
                    "formula_ids": list(pair),
                    "goal": "Classify whether the selected presentation has a model.",
                    "observable": "cardinality of the frozen finite extent",
                    "adjudicator_capability": "presentation_extent",
                    "evidence_refs": [receipt_ids[-1]],
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
        max_rounds=3,
        max_finalists=1,
    )
    assert navigation["finalists"], json.dumps(navigation, indent=2, sort_keys=True)
    program = TheoryProgram.from_json(navigation["finalists"][0]["theory_program"])
    assert program.schema == THEORY_PROGRAM_V2
    assert not program.prediction_formula_ids
    assert len(program.task_discharge_contracts) == 1

    save_formal_theory_context(context, tmp_path / "formal_context.json")
    write_json_atomic(tmp_path / "blueprint.json", blueprint.to_json())
    frozen = finish_frontier_navigation(
        tmp_path,
        brief_id=blueprint.brief_digest,
        blueprint=blueprint,
        context=context,
        context_epoch=0,
        campaign_id="campaign:task-e2e",
        packet_digest="packet:task-e2e",
        navigation=navigation,
        provider_calls=3,
        preparation_provider_calls=0,
        budget_digest="budget:task-e2e",
        formula_proposal_count=0,
        semantically_new_formula_count=0,
        labeled_object_count=len(context.object_ids),
    ).to_json()
    assert replay_frontier_campaign(tmp_path)["ok"] is True

    # Replay binds the separately projected contract IDs to the contracts
    # inside the frozen program; changing either projection invalidates it.
    tampered_core = {
        key: value for key, value in frozen.items() if key != "run_digest"
    }
    tampered_navigation = dict(tampered_core["navigation"])
    tampered_finalists = [dict(row) for row in tampered_navigation["finalists"]]
    tampered_finalists[0]["task_contract_ids"] = ["theory-task:" + "0" * 64]
    tampered_navigation["finalists"] = tampered_finalists
    tampered_core["navigation"] = tampered_navigation
    write_json_atomic(
        tmp_path / "run.json",
        {**tampered_core, "run_digest": content_hash(tampered_core)},
    )
    (tmp_path / "replay.json").unlink(missing_ok=True)
    assert replay_frontier_campaign(tmp_path)["ok"] is False
    write_json_atomic(tmp_path / "run.json", frozen)
    (tmp_path / "replay.json").unlink(missing_ok=True)

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
    # An unavailable executor may yield a complete typed negative for the
    # current invocation, but that completion cannot mask the formal work when
    # the executor becomes available on a later resume.
    assert not _boundary_completion_covers(
        {"boundary_result": boundary, "theory_task_discharge": bundle},
        blueprint.verification_plan,
        navigation,
        lean_requested=False,
        isabelle_requested=False,
        theory_task_requested=True,
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


def test_failed_governance_recheck_demotes_saved_boundary_proof() -> None:
    governed_core = {
        "schema": "leanmill.governed_consequence_attempt.v1",
        "task_id": "lean-consequence:test",
        "status": "proved_attributed",
        "proof_text": "exact True.intro",
    }
    governed = {
        **governed_core,
        "receipt_sha256": content_hash(governed_core),
    }
    row = {
        "candidate_kind": "theory_program",
        "premise_formula_ids": ["formula:premise"],
        "target_formula_id": "formula:target",
        "program_prediction_status": "kernel_verified_attributed",
        "countermodel_searches": [],
        "lean": {"governed_attempt": governed},
    }
    boundary_core = {
        "schema": "leanmill.frontier_boundary_result.v1",
        "context_hash": "context:test",
        "query_results": [row],
    }
    boundary = {
        **boundary_core,
        "result_sha256": content_hash(boundary_core),
    }
    completion = {"boundary_result": boundary}
    rejected_core = {
        "schema": "leanmill.governed_consequence_attempt.v1",
        "task_id": "lean-consequence:test",
        "status": "proof_rejected_by_kernel",
        "proof_text": "exact True.intro",
    }
    rejected = {
        **rejected_core,
        "receipt_sha256": content_hash(rejected_core),
    }
    recheck_row = {
        "premise_formula_ids": ["formula:premise"],
        "target_formula_id": "formula:target",
        "proof_digest": content_hash({"proof_text": "exact True.intro"}),
        "recheck": rejected,
    }
    recheck_core = {
        "schema": "leanmill.frontier_boundary_governance_recheck.v1",
        "boundary_result_sha256": boundary["result_sha256"],
        "query_rechecks": [recheck_row],
    }
    recheck = {
        **recheck_core,
        "receipt_sha256": content_hash(recheck_core),
    }
    run = {
        "status": "frontier_candidates_frozen_awaiting_boundary_approval",
        "context_hash": "context:test",
        "run_digest": "run:test",
        "navigation": {
            "finalists": [{
                "formula_ids": ["formula:premise"],
                "boundary_target_ids": ["formula:target"],
                "theory_program_id": "theory-program:test",
            }],
        },
    }

    feedback = _boundary_search_feedback(
        run, completion, governance_recheck=recheck
    )

    assert feedback is not None
    assert feedback["prediction_outcomes"][0]["status"] == (
        "proof_rejected_by_governance"
    )
    assert feedback["failed_predictions"] == feedback["prediction_outcomes"]
    assert recheck["receipt_sha256"] in (
        feedback["prediction_outcomes"][0]["evidence_refs"]
    )


def test_boundary_survivor_identity_crosses_search_waves(tmp_path):
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
    assert _objective_navigation_phase({
        "navigation": {
            "objective_review_history": [{
                "schema": (
                    "leanmill.candidate_evaluation_contract_supersession.v1"
                ),
                "route": "continue_search",
            }]
        }
    }) == "navigation"
    assert _objective_navigation_phase({"navigation": {}}) == "navigation"

    class Capacity:
        def __init__(self, provider_calls, agent_turns):
            self.values = {
                ("expansion", "provider_calls"): provider_calls,
                ("expansion", "agent_turns"): agent_turns,
            }

        def remaining_capacity(self, phase, resource):
            return self.values.get((phase, resource), 0)

    objective_run = {
        "status": "frontier_objective_unmet",
        "navigation": {"objective_review_history": [positive]},
    }
    assert not _objective_resume_has_turn_capacity(Capacity(0, 2), objective_run)
    assert _objective_resume_has_turn_capacity(Capacity(1, 2), objective_run)
    assert _objective_resume_has_turn_capacity(
        Capacity(0, 0),
        {"status": "frontier_candidates_frozen_awaiting_boundary_approval"},
    )
    assert _lineage_synthesis_retry_required(tmp_path, {
        "status": "frontier_objective_unmet",
        "navigation": {
            "objective_review_history": [positive],
            "lineage_synthesis_budget_stop": {"reason": "budget"},
        },
    })
    assert not _lineage_synthesis_retry_required(tmp_path, {
        "status": "frontier_objective_unmet",
        "navigation": {
            "lineage_synthesis": {
                "schema": "leanmill.lineage_synthesis_decision.v1",
                "route": "proceed_boundary",
            },
            "lineage_synthesis_budget_stop": {"reason": "superseded"},
        },
    })

    objective = {
        "schema": "leanmill.frontier_objective_contract.v1",
        "instruction": "Select a residual program for boundary adjudication.",
        "review_stage": "post_lineage_freeze_pre_boundary",
        "authority": "independent_leaf_choice_host_receipt_validation",
    }
    synthesis_input_core = {
        "schema": "leanmill.lineage_synthesis_input.v1",
        "context_hash": "context:durable",
        "context_epoch": 3,
        "formula_requests": [],
        "theory_language_requests": [
            {"request_id": "theory-language-request:deferred"}
        ],
        "frozen_programs": [{
            "program_id": "theory-program:selected",
            "prediction_profile": {
                "predictions": [{"chart_status": "holds_on_complete_context"}]
            },
        }],
        "objective_contract": objective,
    }
    synthesis_input = {
        **synthesis_input_core,
        "input_sha256": content_hash(synthesis_input_core),
    }
    synthesis = validate_lineage_synthesis_decision(
        synthesis_input,
        {
            "route": "proceed_boundary",
            "selected_request_ids": [],
            "deferred_request_ids": ["theory-language-request:deferred"],
            "rationale": "The selected program retains a residual prediction.",
            "next_discriminator": "Run the governed proof-or-countermodel boundary.",
            "kill_condition": "A checked countermodel refutes the candidate.",
            "program_ids": ["theory-program:selected"],
            "next_discriminator_request_ids": [],
        },
    )
    write_json_atomic(
        tmp_path / "lineage_synthesis_input.epoch-003.wave-007.json",
        synthesis_input,
    )
    write_json_atomic(
        tmp_path / "lineage_synthesis.epoch-003.wave-007.json",
        synthesis,
    )
    durable_run_core = {
        "status": "frontier_objective_unmet",
        "context_hash": "context:durable",
        "context_summary": {"context_epoch": 3},
        "navigation": {
            "context_epoch": 3,
            "finalists": [{
                "theory_program_id": "theory-program:selected",
            }],
            "theory_language_expansion_requests": [{
                "request_id": "theory-language-request:deferred",
            }],
            "lineage_synthesis_budget_stop": {"reason": "superseded"},
        },
    }
    durable_run = {
        **durable_run_core,
        "run_digest": content_hash(durable_run_core),
    }
    write_json_atomic(tmp_path / "run.json", durable_run)
    pending = _pending_durable_lineage_synthesis(tmp_path, durable_run)
    assert pending is not None
    assert pending["search_wave"] == 7
    assert next_frontier_campaign_action(tmp_path) == "recover_lineage_synthesis"

    current_wave_run = {
        **durable_run,
        "navigation": {
            **durable_run["navigation"],
            "search_wave": 7,
        },
    }
    assert _pending_durable_lineage_synthesis(
        tmp_path, current_wave_run
    ) is not None

    write_json_atomic(
        tmp_path / "lineage_synthesis_input.epoch-003.wave-008.json",
        synthesis_input,
    )
    assert _pending_durable_lineage_synthesis(tmp_path, durable_run) is None

    successor_stop_core = {
        "schema": "leanmill.lineage_synthesis_budget_stop.v1",
        "context_hash": "context:durable",
        "context_epoch": 3,
        "reason": "blocked_before_action:expansion:provider_calls",
        "claim_boundary": "no synthesis decision was selected",
        "authority": "host_budget_ledger",
    }
    successor_stop = {
        **successor_stop_core,
        "receipt_sha256": content_hash(successor_stop_core),
    }
    write_json_atomic(
        tmp_path / "lineage_synthesis_budget_stop.epoch-003.wave-008.json",
        successor_stop,
    )
    stale_navigation = {
        **durable_run["navigation"],
        "search_wave": 8,
        "lineage_synthesis": synthesis,
        "lineage_synthesis_search_wave": 7,
        "lineage_synthesis_frozen_program_ids": ["theory-program:selected"],
    }
    stale_run_core = {
        **durable_run_core,
        "navigation": stale_navigation,
    }
    stale_run = {
        **stale_run_core,
        "run_digest": content_hash(stale_run_core),
    }
    write_json_atomic(tmp_path / "run.json", stale_run)
    assert next_frontier_campaign_action(tmp_path) == (
        "unwind_stale_synthesis_projection"
    )

    advanced_navigation = {
        **durable_run_core["navigation"],
        "search_wave": 8,
    }
    advanced_run_core = {
        **durable_run_core,
        "navigation": advanced_navigation,
    }
    advanced_run = {
        **advanced_run_core,
        "run_digest": content_hash(advanced_run_core),
    }
    assert _pending_durable_lineage_synthesis(tmp_path, advanced_run) is None

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


def test_boundary_route_projects_only_synthesis_selected_programs(tmp_path):
    context, blueprint = _context_and_blueprint()
    selected = {
        "node_id": "node:selected",
        "theory_program_id": "theory-program:selected",
    }
    deferred = {
        "node_id": "node:deferred",
        "theory_program_id": "theory-program:deferred",
    }
    synthesis = {
        "route": "proceed_boundary",
        "program_ids": [selected["theory_program_id"]],
        "receipt_sha256": "synthesis:selection",
    }

    run = finish_frontier_navigation(
        tmp_path,
        brief_id=blueprint.brief_digest,
        blueprint=blueprint,
        context=context,
        context_epoch=2,
        campaign_id="campaign:selection",
        packet_digest="packet:selection",
        navigation={
            "context_hash": context.context_hash,
            "context_epoch": 2,
            "search_wave": 7,
            "finalists": [deferred, selected],
            "lineage_synthesis": synthesis,
        },
        provider_calls=3,
        preparation_provider_calls=0,
        budget_digest="budget:selection",
        formula_proposal_count=0,
        semantically_new_formula_count=0,
        labeled_object_count=len(context.object_ids),
    )

    assert run.status == "frontier_candidates_frozen_awaiting_boundary_approval"
    assert run.navigation["finalists"] == [selected]
    assert run.navigation["deferred_finalists"] == [deferred]
    receipt = run.navigation["lineage_synthesis_program_selection"]
    assert receipt["selected_program_ids"] == ["theory-program:selected"]
    assert receipt["deferred_program_ids"] == ["theory-program:deferred"]
    assert read_json(
        tmp_path
        / "lineage_synthesis_program_selection.epoch-002.wave-007.json",
        {},
    ) == receipt


def test_boundary_route_can_select_frozen_objective_survivor(tmp_path):
    context, blueprint = _context_and_blueprint()
    successor = {
        "node_id": "node:same-lineage",
        "theory_program_id": "theory-program:task-successor",
    }
    survivor = {
        "node_id": "node:same-lineage",
        "theory_program_id": "theory-program:boundary-survivor",
    }

    run = finish_frontier_navigation(
        tmp_path,
        brief_id=blueprint.brief_digest,
        blueprint=blueprint,
        context=context,
        context_epoch=2,
        campaign_id="campaign:survivor-selection",
        packet_digest="packet:survivor-selection",
        navigation={
            "context_hash": context.context_hash,
            "context_epoch": 2,
            "search_wave": 8,
            "finalists": [successor],
            "objective_survivors": [survivor],
            "lineage_synthesis": {
                "route": "proceed_boundary",
                "program_ids": [
                    successor["theory_program_id"],
                    survivor["theory_program_id"],
                ],
                "receipt_sha256": "synthesis:survivor-selection",
            },
        },
        provider_calls=3,
        preparation_provider_calls=0,
        budget_digest="budget:survivor-selection",
        formula_proposal_count=0,
        semantically_new_formula_count=0,
        labeled_object_count=len(context.object_ids),
    )

    assert run.status == "frontier_candidates_frozen_awaiting_boundary_approval"
    assert [row["theory_program_id"] for row in run.navigation["finalists"]] == [
        "theory-program:task-successor",
        "theory-program:boundary-survivor",
    ]


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


def test_terminal_projection_preserves_single_lineage_pending_leaf(tmp_path):
    context, blueprint = _context_and_blueprint()
    blueprint = replace(
        blueprint,
        stop_rule={
            **blueprint.stop_rule,
            "user_instruction": "Invent a representation or stop unresolved.",
            "executable_condition": {"kind": "late_lineage_objective_review"},
        },
    )
    pending = {
        "schema": "leanmill.pending_leaf_decision.v1",
        "context_hash": context.context_hash,
        "context_epoch": 0,
        "reason": "host_action_completed_after_leaf_turn",
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
            "pending_leaf_decision": pending,
        },
        provider_calls=4,
        preparation_provider_calls=0,
        budget_digest="budget:test",
        formula_proposal_count=0,
        semantically_new_formula_count=0,
        labeled_object_count=len(context.object_ids),
    )

    assert run.status == "frontier_leaf_decision_pending"
    assert run.navigation["pending_leaf_decision"] == pending


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
        del repo
        instances.append((role_name, instance_id))
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
        lambda role, *, attempt_id, **_kwargs: (role, attempt_id),
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
    assert instances == [
        ("navigator", ""),
        ("witness_constructor", ""),
        ("navigator", "wave-001"),
        ("witness_constructor", "wave-001"),
        ("navigator", "wave-002"),
        ("witness_constructor", "wave-002"),
    ]
    assert navigator.search_wave == 2


def test_single_lineage_wave_receives_feedback_trace_and_replay(
    monkeypatch, tmp_path
):
    context, blueprint = _context_and_blueprint()
    seen = []

    def fake_role(_definition, *, role_name, repo, artifact_dir, instance_id=""):
        del repo
        role = _ScriptedRole(f"{role_name}:{instance_id}", {})
        role.artifact_dir = artifact_dir / (
            role_name if not instance_id else f"{role_name}.{instance_id}"
        )
        role.calls = []
        return role

    def fake_navigator(role, *, attempt_id, **_kwargs):
        del attempt_id

        def inner(_context, _blueprint, _journal, *, budget_ledger):
            del _context, _blueprint, _journal, budget_ledger
            seen.append(
                {
                    "role": role.agent_id,
                    "initial_trace": getattr(inner, "initial_trace", ()),
                    "replay_decisions": getattr(inner, "replay_decisions", ()),
                }
            )
            return {"context_hash": context.context_hash}

        return inner

    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.frontier_agent_role",
        fake_role,
    )
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.make_subscription_theory_navigator",
        fake_navigator,
    )
    definition = FrontierCampaignDefinition(
        direction="Continue one feedback-bound lineage.",
        source_mode="structure_first",
        budget=budget_preset("smoke_20m"),
    )
    navigator = _make_campaign_theory_navigator(
        definition,
        directory=tmp_path,
        repo=tmp_path,
        attempt_id=tmp_path.name,
    )
    feedback_trace = (
        {
            "decision": "objective_feedback_evidence",
            "evidence_ref": "receipt:execution",
        },
    )
    replay = ({"decision": "request", "request": "next"},)
    navigator.initial_trace = feedback_trace
    navigator.replay_decisions = replay
    navigator.begin_search_wave()
    navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "events.jsonl"),
        budget_ledger=None,
    )

    assert seen == [
        {
            "role": "navigator:wave-001",
            "initial_trace": feedback_trace,
            "replay_decisions": replay,
        }
    ]
    assert navigator.call_role.agent_id == "navigator:wave-001"


def test_synthesis_only_wave_is_a_durable_search_wave(monkeypatch, tmp_path):
    instances = []

    def fake_role(_definition, *, role_name, repo, artifact_dir, instance_id=""):
        del repo
        instances.append((role_name, instance_id))
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
        lambda role, *, attempt_id, **_kwargs: (role, attempt_id),
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
    assert instances == [
        ("navigator", "wave-008"),
        ("witness_constructor", "wave-008"),
    ]

    navigator.begin_search_wave()
    assert navigator.search_wave == 9
    assert instances[-2:] == [
        ("navigator", "wave-009"),
        ("witness_constructor", "wave-009"),
    ]


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
    candidate_presentations = (
        (
            "formula:6a860f4453a684d98cdc0bcb4525ad891fba32e4079b5b9a8712c47764a75f63",
        ),
        (
            "formula:2e105ba93093a4e85201d41350b1bc32edc2b39c965df45d6517838ba962c0a4",
            "formula:4eb72b9af83fce02302ea8383da0459113feac5c2eb03a62aa3ded53bf5c5237",
        ),
    )
    candidates = [
        (
            formulas,
            theory_program_information_yield(
                context, formulas
            ).residual_prediction_ids[0],
        )
        for formulas in candidate_presentations
    ]
    assert len({context.incidence.extent_bits(row[0]) for row in candidates}) == 2

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

    # Recovery events are a sparse projection, not an authoritative epoch
    # sequence. A legacy projection ending at epoch 0 must not prevent the
    # current epoch-2 replay when no navigator action occurred at epoch 1.
    authoritative = TheoryCampaignJournal(tmp_path / "events.jsonl")
    first_event = authoritative.replay()[0]
    authoritative.append(
        TheoryCampaignEvent(
            attempt_id=first_event.attempt_id,
            campaign_id=first_event.campaign_id,
            epoch=1,
            context_hash="context:intermediate-without-navigation",
            event_type="context_epoch_proposed",
            subject_ids=("epoch-1-non-navigation-transition",),
            evidence_status="proposed",
            authority="test_epoch_transition",
        )
    )
    authoritative.append(
        TheoryCampaignEvent(
            attempt_id=first_event.attempt_id,
            campaign_id=first_event.campaign_id,
            epoch=2,
            context_hash=context.context_hash,
            event_type="context_epoch_proposed",
            subject_ids=("epoch-2-current-context",),
            evidence_status="proposed",
            authority="test_epoch_transition",
        )
    )
    TheoryCampaignJournal(
        tmp_path
        / "lineage_journals"
        / "recovery-navigator.lineage-001.events.jsonl"
    ).append(
        TheoryCampaignEvent(
            attempt_id=f"{tmp_path.name}:lineage:1",
            campaign_id=first_event.campaign_id,
            epoch=0,
            context_hash=context.context_hash,
            event_type="navigator_action_executed",
            subject_ids=("legacy-derived-replay",),
            evidence_status="witnessed",
            authority="deterministic_workbench_executor",
        )
    )

    import ztare.leanmill.frontier_campaign_runner as runner

    candidate_memory = {"schema": "fixture.authoritative_candidate_memory.v1"}
    replay_memories: list[object] = []
    replay = runner._replay_navigator_decisions

    monkeypatch.setattr(
        runner,
        "_campaign_construction_candidate_memory",
        lambda *_args, **_kwargs: candidate_memory,
    )

    def replay_with_memory(*args, candidate_outcome_memory=None, **kwargs):
        replay_memories.append(candidate_outcome_memory)
        return replay(
            *args,
            candidate_outcome_memory=None,
            **kwargs,
        )

    monkeypatch.setattr(runner, "_replay_navigator_decisions", replay_with_memory)
    materialize_frontier_navigation_from_journal(tmp_path)
    recovered = read_json(tmp_path / "run.json", {})["navigation"]
    assert replay_memories
    assert all(row is candidate_memory for row in replay_memories)
    assert len(recovered["finalists"]) == 2
    assert len(recovered["host_isolated_program_comparisons"]) == 1
    assert len(
        {
            row["theory_program"]["lineage_id"]
            for row in recovered["finalists"]
        }
    ) == 2
    assert replay_frontier_campaign(tmp_path)["ok"] is True
    assert list((tmp_path / "recovery_journals").glob("*.epoch-002.*.jsonl"))
