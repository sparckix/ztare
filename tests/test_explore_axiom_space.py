from __future__ import annotations

import importlib
from itertools import combinations
import json
import re

import pytest

from ztare.leanmill.axiom_pack import priority_uncrossed_order_blueprint
from ztare.leanmill.common import read_json, write_json_atomic
from ztare.leanmill.deterministic_frontier_campaign import (
    run_deterministic_frontier_campaign,
)
from ztare.leanmill.frontier_campaign_actions import (
    frontier_campaign_status,
    inspect_frontier_campaign,
    replay_frontier_campaign,
    request_frontier_campaign_stop,
    retire_frontier_campaign,
)
from ztare.leanmill.explore_axiom_space import (
    _resolve_workbench_evidence_receipts,
    _workbench_evidence_binding,
    execute_frontier_boundaries,
    explore_axiom_space,
    freeze_frontier_formula_successor_request,
)
from ztare.leanmill.lean_consequence_bridge import execute_governed_lean_consequence
from ztare.leanmill.solver.sledgehammer import execute_isabelle_theory_task
from ztare.leanmill.formal_verification_provider import generate_keypair
from ztare.leanmill.frontier_blueprint import FrontierExplorationBrief
from ztare.leanmill.frontier_campaign import sign_frontier_campaign
from ztare.leanmill.frontier_campaign_definition import FrontierCampaignDefinition
from ztare.leanmill.finite_theory_context import load_formal_theory_context
from ztare.leanmill.evidence_theory_context import EvidenceObjectRecord
from ztare.leanmill.exploration_budget import (
    ExplorationBudgetLedger,
    budget_preset,
)
from ztare.leanmill.magma_law_universe import anonymous_magma_signature
from ztare.leanmill.theory_campaign_journal import TheoryCampaignJournal
from ztare.leanmill.theory_interest import theory_residual_information_yield
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.theory_navigator import run_interactive_theory_navigator
from ztare.leanmill.ratification_policy import (
    TARGET_GOVERNANCE_AUTHORITIES,
    TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256,
)
from ztare.leanmill.solver.closed_artifact import finalize_solver_validation


def _draft(adapter_id="magma_equational.v1"):
    return {
        "mode": "anonymous_signature_census",
        "eigenquestion": "Which anonymous pairs form nontrivial joint closures?",
        "signature": anonymous_magma_signature().to_json(),
        "primitive_semantics": {
            "operation_bindings": {"op0": "total finite binary operation table"},
            "relation_bindings": {},
        },
        "base_axioms": (), "base_theory_status": "explicit_empty",
        "adapter_id": adapter_id,
        "adapter_config": {"max_total_operation_order": 2},
        "formula_grammar": {"kind": "canonical equations", "max_order": 2},
        "model_or_observation_strata": ({"carrier_size": 2},),
        "pack_arity": 2, "collapse_controls": (),
        "visible_evidence_manifest": {},
        "sealed_evidence_manifest_digest": "sha256:" + "0" * 64,
        "deanchoring_policy": {"cold_after_compilation": True},
        "navigator_contract": {
            "adapter_id": "axiompack",
            "selection_mode": "compact_axiom_pack",
        },
        "query_budget": {"max_finalists": 3, "max_ranked_queries": 4},
        "stop_rule": {"freeze_after_finalists": 3},
        "verification_plan": {"larger_carriers": [3], "conditional_lean": True},
        "codec_versions": {"formula": "magma-postfix-v1"},
        "authority_refs": ("campaign-authority",),
    }


def _signer():
    private, _public = generate_keypair()
    return lambda packet: sign_frontier_campaign(
        packet, private_key_pem=private, signer_ref="campaign-authority"
    )


def test_language_evidence_resolves_governed_trace_receipts(tmp_path):
    workbench_core = {
        "schema": "leanmill.axiompack_workbench_receipt.v1",
        "capability_id": "inspect_presentation_extent",
        "authority": "deterministic_host",
        "output_summary": {"status": "inspected"},
    }
    workbench = {
        **workbench_core,
        "receipt_id": "sha256:" + content_hash(workbench_core),
    }
    boundary_core = {
        "schema": "leanmill.boundary_search_feedback.v1",
        "authority": "host_boundary_outcome_replay",
        "route": "continue_search",
    }
    boundary = {
        **boundary_core,
        "receipt_sha256": content_hash(boundary_core),
    }
    navigation = {
        "trace": [
            {"decision": "request", "receipt": workbench},
            {"decision": "objective_feedback", "receipt": boundary},
        ]
    }

    receipts = _resolve_workbench_evidence_receipts(
        tmp_path,
        navigation,
        [workbench["receipt_id"], boundary["receipt_sha256"]],
    )
    binding = _workbench_evidence_binding(receipts)

    assert binding["schema"] == "leanmill.governed_trace_evidence_binding.v1"
    assert binding["receipt_ids"] == [
        workbench["receipt_id"],
        boundary["receipt_sha256"],
    ]
    assert [row["schema"] for row in binding["evidence"]] == [
        workbench["schema"],
        boundary["schema"],
    ]


def test_language_evidence_rejects_unbound_or_tampered_trace_receipts(tmp_path):
    core = {
        "schema": "leanmill.boundary_search_feedback.v1",
        "authority": "host_boundary_outcome_replay",
        "route": "continue_search",
    }
    tampered = {**core, "receipt_sha256": "0" * 64}
    navigation = {
        "trace": [{"decision": "objective_feedback", "receipt": tampered}]
    }
    with pytest.raises(ValueError, match="governed trace receipts"):
        _resolve_workbench_evidence_receipts(
            tmp_path, navigation, [tampered["receipt_sha256"]]
        )


def test_language_evidence_binds_trace_and_frozen_context_artifacts(tmp_path):
    trace_core = {
        "schema": "leanmill.axiompack_workbench_receipt.v1",
        "capability_id": "inspect_presentation_extent",
        "authority": "deterministic_host",
        "output_summary": {"status": "inspected"},
    }
    trace = {
        **trace_core,
        "receipt_id": "sha256:" + content_hash(trace_core),
    }
    digest = "1" * 64
    context = type(
        "FrozenEvidenceContext",
        (),
        {
            "context_hash": "context:frozen",
            "object_records": (
                EvidenceObjectRecord(
                    model_id="control:one",
                    stratum_id="positive",
                    payload={
                        "artifact_ref": "control.json#matrix",
                        "artifact_sha256": digest,
                    },
                ),
            ),
        },
    )()
    refs = [trace["receipt_id"], "control.json#matrix", "sha256:" + digest]

    evidence = _resolve_workbench_evidence_receipts(
        tmp_path,
        {"trace": [{"receipt": trace}]},
        refs,
        context=context,
    )
    binding = _workbench_evidence_binding(evidence)

    assert binding["schema"] == "leanmill.governed_mixed_evidence_binding.v1"
    assert binding["receipt_ids"] == refs
    assert [row["authority"] for row in binding["evidence"]] == [
        "deterministic_host",
        "frozen_context_snapshot",
        "frozen_context_snapshot",
    ]


def test_language_evidence_accepts_content_bound_predecessor_transport(tmp_path):
    receipt_core = {
        "schema": "leanmill.axiompack_workbench_receipt.v1",
        "capability_id": "inspect_presentation_extent",
        "authority": "deterministic_host",
        "output_summary": {"status": "inspected"},
    }
    receipt = {
        **receipt_core,
        "receipt_id": "sha256:" + content_hash(receipt_core),
    }
    navigation = {
        "carried_evidence_receipts": [
            {"evidence_ref": receipt["receipt_id"], "receipt": receipt}
        ]
    }

    resolved = _resolve_workbench_evidence_receipts(
        tmp_path, navigation, [receipt["receipt_id"]]
    )

    assert resolved == [receipt]

    navigation["carried_evidence_receipts"][0]["receipt"]["authority"] = "changed"
    with pytest.raises(ValueError, match="do not resolve"):
        _resolve_workbench_evidence_receipts(
            tmp_path, navigation, [receipt["receipt_id"]]
        )


def test_successor_formula_request_preserves_source_finalist_identity(tmp_path):
    navigation = {
        "context_hash": "context:source",
        "context_epoch": 3,
        "finalists": [
            {
                "node_id": "theory:one",
                "context_hash": "context:source",
                "context_epoch": 3,
            }
        ],
        "expansion_proposal": {
            "source_context_hash": "context:source",
            "source_epoch": 3,
            "formula_id": "formula:new",
        },
    }

    frozen = freeze_frontier_formula_successor_request(tmp_path, navigation)

    transition = frozen["epoch_transition"]
    request = read_json(tmp_path / transition["request_ref"], {})
    assert request["source_context_hash"] == "context:source"
    assert request["source_epoch"] == 3
    assert request["target_epoch"] == 4
    assert request["source_finalist_node_ids"] == ["theory:one"]
    assert frozen["finalists"] == navigation["finalists"]

    crossed = {**navigation, "context_hash": "context:other"}
    with pytest.raises(ValueError, match="context identity"):
        freeze_frontier_formula_successor_request(tmp_path, crossed)


def _rejecting_navigator():
    def navigator(context, blueprint, journal, *, budget_ledger):
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
        decisions = iter(
            [
                {
                    "decision": "freeze",
                    "formula_ids": list(pair),
                    "rationale": "Test the candidate against the visible baseline.",
                },
                {
                    "decision": "reject_all",
                    "rationale": "The host receipt reports zero residual information.",
                },
            ]
        )
        return run_interactive_theory_navigator(
            context,
            blueprint,
            journal,
            agent_fn=lambda _prompt: next(decisions),
            attempt_id="attempt-no-candidate",
            campaign_id="campaign:" + blueprint.blueprint_id.split(":", 1)[1][:24],
            budget_ledger=budget_ledger,
        )

    navigator.accepts_budget_ledger = True
    return navigator


def test_single_public_inlet_builds_and_navigates_structure_first(
    tmp_path, monkeypatch
):
    phase_ledger = tmp_path / "phase_timings.jsonl"
    monkeypatch.setenv("ZTARE_LEANMILL_PHASE_TIMING_LEDGER", str(phase_ledger))
    brief = FrontierExplorationBrief(
        direction="Explore anonymous finite binary-operation theories.",
        source_mode="structure_first",
    )
    run = explore_axiom_space(
        brief,
        attempt_dir=tmp_path / "attempt-1",
        typed_draft=_draft(),
        packet_signer=_signer(),
        campaign_manifest={
            "schema": "leanmill.campaign.v1",
            "campaign_id": "leanmill-campaign:test",
            "lane": "axiompack",
        },
    )
    assert run.status == "frontier_candidates_frozen_awaiting_boundary_approval"
    assert run.provider_calls == 0
    assert run.navigation and run.navigation["finalists"]
    assert (tmp_path / "attempt-1" / "cold_navigator_manifest.json").is_file()
    status = frontier_campaign_status(tmp_path / "attempt-1")
    assert status["status"] == run.status
    assert status["campaign_id"] == "leanmill-campaign:test"
    inspection = inspect_frontier_campaign(tmp_path / "attempt-1")
    assert inspection["sealed_evidence_visible"] is False
    assert inspection["campaign_manifest_ref"] == "campaign_manifest.json"
    assert replay_frontier_campaign(tmp_path / "attempt-1")["ok"] is True
    phase_rows = [
        json.loads(line)
        for line in phase_ledger.read_text(encoding="utf-8").splitlines()
    ]
    launch_rows = [row for row in phase_rows if row.get("phase") == "campaign"]
    assert len(launch_rows) == 1
    assert launch_rows[0]["run_tag"] == "attempt-1"
    frozen_brief = read_json(tmp_path / "attempt-1" / "brief.json", {})
    assert launch_rows[0]["tags"] == {
        "target": frozen_brief["brief_id"],
        "domain": "axiompack-frontier",
    }


def test_attempt_initializer_owns_first_write_after_directory_creation(tmp_path):
    attempt = tmp_path / "attempt-initialized"
    observed = []

    def initialize(directory):
        assert directory == attempt
        assert directory.is_dir()
        assert list(directory.iterdir()) == []
        (directory / "identity.marker").write_text("frozen", encoding="utf-8")
        observed.append(directory)

    def sign_after_initialization(packet):
        assert (attempt / "identity.marker").read_text(encoding="utf-8") == "frozen"
        return _signer()(packet)

    run = explore_axiom_space(
        FrontierExplorationBrief(
            direction="Exercise attempt initialization ordering.",
            source_mode="structure_first",
        ),
        attempt_dir=attempt,
        typed_draft=_draft(),
        packet_signer=sign_after_initialization,
        attempt_initializer=initialize,
    )

    assert observed == [attempt]
    assert run.provider_calls == 0


def test_budget_stop_replay_retains_verified_outer_objective_finalists(tmp_path):
    attempt = tmp_path / "attempt-objective-budget-stop"
    run = explore_axiom_space(
        FrontierExplorationBrief(
            direction="Explore anonymous finite binary-operation theories.",
            source_mode="structure_first",
        ),
        attempt_dir=attempt,
        typed_draft=_draft(),
        packet_signer=_signer(),
    )
    assert run.navigation and run.navigation["finalists"]

    frozen_run = read_json(attempt / "run.json", {})
    stop_core = {
        "schema": "leanmill.exploration_budget_stop.v1",
        "reason": "blocked_before_action:expansion:provider_calls",
        "context_hash": frozen_run["context_hash"],
        "budget_digest": frozen_run["budget_digest"],
    }
    stop = {**stop_core, "receipt_sha256": content_hash(stop_core)}
    run_core = {
        **{key: value for key, value in frozen_run.items() if key != "run_digest"},
        "status": "budget_stopped",
        "budget_stop_receipt": stop,
    }
    write_json_atomic(
        attempt / "run.json",
        {**run_core, "run_digest": content_hash(run_core)},
    )
    (attempt / "replay.json").unlink(missing_ok=True)
    ordinary_replay = replay_frontier_campaign(attempt)
    assert ordinary_replay["ok"] is False
    assert ordinary_replay["budget_stop_check"]["outer_objective_active"] is False

    blueprint = read_json(attempt / "blueprint.json", {})
    blueprint.pop("blueprint_id", None)
    blueprint["stop_rule"] = {
        **blueprint["stop_rule"],
        "user_instruction": "Invent a representation beyond the frozen finalists.",
        "executable_condition": {"kind": "late_lineage_objective_review"},
    }
    write_json_atomic(attempt / "blueprint.json", blueprint)
    (attempt / "replay.json").unlink(missing_ok=True)

    replay = replay_frontier_campaign(attempt)

    assert replay["ok"] is True
    assert replay["budget_stop_check"] == {
        "ok": True,
        "reason": "blocked_before_action:expansion:provider_calls",
        "receipt_sha256": stop["receipt_sha256"],
        "outer_objective_active": True,
        "retained_evidence_check_count": len(run.navigation["finalists"]),
    }
    assert all(row["ok"] is True for row in replay["finalist_checks"])
    closure_gate = {
        "ready": True,
        "missing_lineage_disposition_ids": [],
        "unadjudicated_generalization_residual_ids": [],
        "receipt_sha256": "closure:fixture",
    }
    write_json_atomic(attempt / "campaign_closure_gate.json", closure_gate)
    status = frontier_campaign_status(attempt)
    assert status["cold_replay"] == {
        "schema": "leanmill.frontier_campaign_replay.v5",
        "ok": True,
        "receipt_sha256": replay["receipt_sha256"],
        "provider_calls": 0,
        "budget_stop_ok": True,
        "retained_evidence_check_count": len(run.navigation["finalists"]),
    }
    assert status["campaign_closure_gate"] == closure_gate


def test_public_inlet_surfaces_language_expansion_as_next_campaign_work(tmp_path):
    def navigator(context, blueprint, journal, *, budget_ledger):
        epoch = int(getattr(navigator, "epoch", 0))
        calls = 0

        def decide(prompt):
            nonlocal calls
            calls += 1
            if calls == 1:
                return {
                    "decision": "request",
                    "capability_id": "inspect_presentation_extent",
                    "input_refs": {"formula_ids": [], "offset": 0, "limit": 2},
                    "rationale": "Receipt the aliased source objects before changing language.",
                }
            evidence = re.findall(r'"receipt_id":"(sha256:[0-9a-f]{64})"', prompt)
            assert evidence
            return {
                "decision": "request",
                "capability_id": "propose_theory_language_expansion",
                "input_refs": {
                    "change_kind": "new_relation",
                    "blind_spot": "The frozen operation language aliases a witnessed pair.",
                    "proposed_interface": "A binary relation with executable finite semantics.",
                    "evidence_refs": [evidence[-1]],
                    "discriminating_test": "The relation splits the witnessed object class.",
                    "kill_condition": "The compiled relation fails to split that class.",
                },
                "rationale": "Move the language boundary instead of forcing an equation.",
            }

        return run_interactive_theory_navigator(
            context,
            blueprint,
            journal,
            agent_fn=decide,
            attempt_id="attempt-language",
            campaign_id="campaign:" + blueprint.blueprint_id.split(":", 1)[1][:24],
            budget_ledger=budget_ledger,
            epoch=epoch,
            max_rounds=2,
        )

    navigator.accepts_budget_ledger = True
    run = explore_axiom_space(
        FrontierExplorationBrief(
            direction="Explore anonymous finite operation theories.",
            source_mode="structure_first",
        ),
        attempt_dir=tmp_path / "attempt-language",
        typed_draft=_draft(),
        packet_signer=_signer(),
        navigator_fn=navigator,
    )

    assert run.status == "frontier_language_expansion_requested"
    assert run.navigation["language_expansion_request"]["change_kind"] == (
        "new_relation"
    )
    assert (
        tmp_path
        / "attempt-language"
        / "theory_language_expansion_request.epoch-000.json"
    ).is_file()
    assert not run.navigation.get("reject_all_receipt")
    replay = replay_frontier_campaign(tmp_path / "attempt-language")
    assert replay["ok"] is True
    assert replay["language_expansion_request_check"] == {
        "ok": True,
        "request_id": run.navigation["language_expansion_request"]["request_id"],
    }

    artifact_path = (
        tmp_path
        / "attempt-language"
        / "theory_language_expansion_request.epoch-000.json"
    )
    artifact = read_json(artifact_path, {})
    artifact["blind_spot"] = "tampered after freeze"
    write_json_atomic(artifact_path, artifact)
    (tmp_path / "attempt-language" / "replay.json").unlink()
    assert replay_frontier_campaign(tmp_path / "attempt-language")["ok"] is False


def test_replay_revalidates_isolated_language_request_receipt(tmp_path):
    attempt = tmp_path / "attempt-isolated-requests"
    explore_axiom_space(
        FrontierExplorationBrief(
            direction="Explore anonymous finite operation theories.",
            source_mode="structure_first",
        ),
        attempt_dir=attempt,
        typed_draft=_draft(),
        packet_signer=_signer(),
    )
    run = read_json(attempt / "run.json", {})
    formula_requests = [{"lineage_id": "lineage:a", "request_id": "formula:a"}]
    language_requests = [{"lineage_id": "lineage:b", "request_id": "language:b"}]
    run["navigation"]["expansion_proposals"] = formula_requests
    run["navigation"]["theory_language_expansion_requests"] = language_requests
    write_json_atomic(attempt / "run.json", run)
    core = {
        "schema": "leanmill.isolated_lineage_language_requests.v1",
        "source_context_hash": run["context_hash"],
        "source_epoch": 0,
        "formula_requests": formula_requests,
        "theory_language_requests": language_requests,
        "status": "outbound_requests_require_reviewed_successor_context",
        "authority": "proposal_only",
    }
    artifact_path = attempt / "isolated_lineage_language_requests.epoch-000.json"
    write_json_atomic(
        artifact_path,
        {**core, "receipt_sha256": content_hash(core)},
    )

    replay = replay_frontier_campaign(attempt)
    assert replay["ok"] is True
    assert replay["isolated_language_requests_check"]["ok"] is True

    artifact = read_json(artifact_path, {})
    artifact["formula_requests"] = []
    write_json_atomic(artifact_path, artifact)
    (attempt / "replay.json").unlink()
    assert replay_frontier_campaign(attempt)["ok"] is False

    write_json_atomic(artifact_path, ["malformed"])
    (attempt / "replay.json").unlink()
    assert replay_frontier_campaign(attempt)["ok"] is False


def test_public_inlet_composes_typed_formula_proposal_into_a_new_context_epoch(
    tmp_path,
):
    def navigator(context, blueprint, journal, *, budget_ledger):
        epoch = int(getattr(navigator, "epoch", 0))
        if epoch == 0:
            return run_interactive_theory_navigator(
                context,
                blueprint,
                journal,
                agent_fn=lambda _prompt: {
                    "decision": "request",
                    "capability_id": "propose_frontier_formula",
                    "input_refs": {
                        "structural_conjecture": (
                            "The seed band omits the two four-variable bracketing extremes."
                        ),
                        "axiom_name": "fourfold_bracketing_candidate",
                        "variables": [
                            {"name": f"x{index}", "sort": "sort_0"}
                            for index in range(4)
                        ],
                        "lhs_tokens": [
                            "x0", "x1", "op_0", "x2", "op_0", "x3", "op_0"
                        ],
                        "rhs_tokens": [
                            "x0", "x1", "x2", "x3", "op_0", "op_0", "op_0"
                        ],
                        "nl_intent": "The extreme fourfold bracketings agree.",
                        "kill_condition": "A finite table separates the bracketings.",
                    },
                    "rationale": "Open a typed semantic distinction outside the seed chart.",
                },
                attempt_id="attempt-epoch",
                campaign_id="campaign:" + blueprint.blueprint_id.split(":", 1)[1][:24],
                budget_ledger=budget_ledger,
                epoch=epoch,
                max_rounds=4,
            )
        return run_deterministic_frontier_campaign(
            context,
            campaign_id="campaign:" + blueprint.blueprint_id.split(":", 1)[1][:24],
            attempt_id="attempt-epoch",
            journal=journal,
            max_finalists=1,
            max_ranked_queries=1,
            epoch=epoch,
        ).to_json()

    navigator.accepts_budget_ledger = True
    attempt = tmp_path / "attempt-epoch"
    run = explore_axiom_space(
        FrontierExplorationBrief(
            direction="Explore beyond the initial anonymous equation chart.",
            source_mode="structure_first",
        ),
        attempt_dir=attempt,
        typed_draft=_draft(),
        packet_signer=_signer(),
        navigator_fn=navigator,
    )

    epoch_zero = load_formal_theory_context(
        attempt / "formal_context.epoch-000.json"
    )
    epoch_one = load_formal_theory_context(
        attempt / "formal_context.epoch-001.json"
    )
    assert len(epoch_one.formula_ids) == len(epoch_zero.formula_ids) + 1
    assert epoch_one.context_hash == run.context_hash
    assert run.context_summary["context_epoch"] == 1
    assert run.context_summary["agent_proposed_formula_count"] == 1
    admission = read_json(
        attempt / "frontier_formula_epoch_admission.epoch-001.json", {}
    )
    assert admission["formula_identity_new"] is True
    assert run.context_summary["agent_proposed_semantic_profile_count"] == int(
        admission["bounded_semantic_profile_new"]
    )
    checkpoint = read_json(attempt / "navigation_epoch_checkpoint.json", {})
    assert checkpoint["trace"][-1]["decision"] == "context_epoch_admitted"
    assert checkpoint["trace"][-1]["admission"] == admission
    assert (attempt / "campaign.epoch-000.json").is_file()
    assert (attempt / "campaign.epoch-001.json").is_file()
    campaign = read_json(attempt / "campaign.json", {})
    assert campaign["packet"]["formula_grammar"]["schema"] == (
        "leanmill.frontier_formula_epoch.v1"
    )
    assert any(
        event.event_type == "evidence_promoted_to_next_epoch" and event.epoch == 1
        for event in TheoryCampaignJournal(attempt / "events.jsonl").replay()
    )

    def reject_before_spend(premises, target):
        core = {
            "schema": "leanmill.source_single_premise_ablation.v1",
            "status": "refuted_by_known_single_premise",
            "premise_formula_ids": list(premises),
            "target_formula_id": target,
            "premise_checks": [
                {"premise_formula_id": premises[0], "proved_implies": True}
            ],
        }
        return {**core, "receipt_sha256": content_hash(core)}

    execute_frontier_boundaries(
        attempt,
        single_premise_audit_fn=reject_before_spend,
    )
    boundary_events = [
        event
        for event in TheoryCampaignJournal(attempt / "events.jsonl").replay()
        if event.event_type == "boundary_query_completed"
        and event.context_hash == epoch_one.context_hash
    ]
    assert boundary_events
    assert all(event.epoch == 1 for event in boundary_events)


def test_public_inlet_supports_recursive_pre_freeze_formula_epochs(tmp_path):
    proposals = (
        {
            "structural_conjecture": "Compare extreme fourfold bracketings.",
            "axiom_name": "fourfold_candidate",
            "variables": [
                {"name": f"x{index}", "sort": "sort_0"} for index in range(4)
            ],
            "lhs_tokens": ["x0", "x1", "op_0", "x2", "op_0", "x3", "op_0"],
            "rhs_tokens": ["x0", "x1", "x2", "x3", "op_0", "op_0", "op_0"],
            "nl_intent": "The extreme fourfold bracketings agree.",
            "kill_condition": "A finite table separates the terms.",
        },
        {
            "structural_conjecture": "Compare crossed pairings of four inputs.",
            "axiom_name": "medial_candidate",
            "variables": [
                {"name": f"x{index}", "sort": "sort_0"} for index in range(4)
            ],
            "lhs_tokens": ["x0", "x1", "op_0", "x2", "x3", "op_0", "op_0"],
            "rhs_tokens": ["x0", "x2", "op_0", "x1", "x3", "op_0", "op_0"],
            "nl_intent": "The two crossed binary pairings agree.",
            "kill_condition": "A finite table separates the pairings.",
        },
    )

    def navigator(context, blueprint, journal, *, budget_ledger):
        epoch = int(getattr(navigator, "epoch", 0))
        if epoch < len(proposals):
            return run_interactive_theory_navigator(
                context,
                blueprint,
                journal,
                agent_fn=lambda _prompt: {
                    "decision": "request",
                    "capability_id": "propose_frontier_formula",
                    "input_refs": proposals[epoch],
                    "rationale": "Refine the language before freezing a presentation.",
                },
                attempt_id="attempt-recursive-epochs",
                campaign_id="campaign:" + blueprint.blueprint_id.split(":", 1)[1][:24],
                budget_ledger=budget_ledger,
                epoch=epoch,
                max_rounds=3,
            )
        return run_deterministic_frontier_campaign(
            context,
            campaign_id="campaign:" + blueprint.blueprint_id.split(":", 1)[1][:24],
            attempt_id="attempt-recursive-epochs",
            journal=journal,
            max_finalists=1,
            max_ranked_queries=1,
            epoch=epoch,
        ).to_json()

    navigator.accepts_budget_ledger = True
    attempt = tmp_path / "attempt-recursive-epochs"
    run = explore_axiom_space(
        FrontierExplorationBrief(
            direction="Learn several anonymous coordinates before nomination.",
            source_mode="structure_first",
        ),
        attempt_dir=attempt,
        typed_draft=_draft(),
        packet_signer=_signer(),
        navigator_fn=navigator,
    )

    epoch_zero = load_formal_theory_context(attempt / "formal_context.epoch-000.json")
    epoch_two = load_formal_theory_context(attempt / "formal_context.epoch-002.json")
    assert len(epoch_two.formula_ids) == len(epoch_zero.formula_ids) + 2
    assert run.context_summary["context_epoch"] == 2
    assert run.context_summary["agent_proposed_formula_count"] == 2
    assert len(tuple(attempt.glob("frontier_formula_epoch_admission.epoch-*.json"))) == 2
    assert [
        event.epoch
        for event in TheoryCampaignJournal(attempt / "events.jsonl").replay()
        if event.event_type == "evidence_promoted_to_next_epoch"
    ] == [1, 2]


def test_continue_epoch_archives_source_identity_before_admission(
    tmp_path, monkeypatch
):
    import ztare.leanmill.frontier_campaign_runner as runner

    private, public = generate_keypair()

    def navigator(context, blueprint, journal, *, budget_ledger):
        pair = next(
            row
            for row in combinations(context.formula_ids, 2)
            if (
                (signal := theory_residual_information_yield(context, row))
                and signal.residual_consequence_ids
                and context.incidence.extent_bits(row).bit_count() >= 2
                and all(
                    context.independence_witness(row, formula) is not None
                    for formula in row
                )
            )
        )
        decisions = iter(
            [
                {
                    "decision": "freeze",
                    "formula_ids": list(pair),
                    "rationale": "Freeze the source context candidate.",
                },
                {
                    "decision": "request",
                    "capability_id": "propose_frontier_formula",
                    "input_refs": {
                        "structural_conjecture": "Compare extreme fourfold bracketings.",
                        "axiom_name": "successor_fourfold_candidate",
                        "variables": [
                            {"name": f"x{index}", "sort": "sort_0"}
                            for index in range(4)
                        ],
                        "lhs_tokens": [
                            "x0", "x1", "op_0", "x2", "op_0", "x3", "op_0"
                        ],
                        "rhs_tokens": [
                            "x0", "x1", "x2", "x3", "op_0", "op_0", "op_0"
                        ],
                        "nl_intent": "The extreme fourfold bracketings agree.",
                        "kill_condition": "A finite table separates the terms.",
                    },
                    "rationale": "Freeze a coordinate for a successor context.",
                },
            ]
        )
        return run_interactive_theory_navigator(
            context,
            blueprint,
            journal,
            agent_fn=lambda _prompt: next(decisions),
            attempt_id="attempt-successor",
            campaign_id="campaign:" + blueprint.blueprint_id.split(":", 1)[1][:24],
            budget_ledger=budget_ledger,
            max_rounds=3,
        )

    navigator.accepts_budget_ledger = True
    definition = FrontierCampaignDefinition(
        direction="Explore a successor formula context.",
        source_mode="structure_first",
        requested_mode="anonymous_signature_census",
        budget=budget_preset("smoke_20m"),
    )
    attempt = tmp_path / "attempt-successor"
    source_run = explore_axiom_space(
        definition,
        attempt_dir=attempt,
        typed_draft=_draft(),
        packet_signer=lambda packet: sign_frontier_campaign(
            packet,
            private_key_pem=private,
            signer_ref="campaign-authority",
        ),
        navigator_fn=navigator,
    )
    assert source_run.navigation["epoch_transition"]["status"] == (
        "successor_epoch_required"
    )
    source_replay = replay_frontier_campaign(attempt)
    assert source_replay["context_hash"] == source_run.context_hash
    signer_path = attempt / "private" / "campaign_signer.pem"
    signer_path.parent.mkdir()
    signer_path.write_text(private, encoding="utf-8")
    (attempt / "campaign_signer_public.pem").write_text(public, encoding="utf-8")
    call_dir = attempt / "agent_calls" / "navigator"
    call_dir.mkdir(parents=True)
    (call_dir / "000.prompt.txt").write_text("source prompt", encoding="utf-8")
    monkeypatch.setattr(
        runner,
        "resume_frontier_campaign_navigation",
        lambda directory, repo=None, _attempt_lease=None: directory,
    )

    returned = runner.continue_frontier_campaign_epoch(attempt)

    assert returned == attempt
    assert not (attempt / "run.json").exists()
    assert (attempt / "run.epoch-000.json").is_file()
    assert (attempt / "replay.epoch-000.json").is_file()
    assert (attempt / "agent_calls/navigator.epoch-000/000.prompt.txt").is_file()
    source = load_formal_theory_context(attempt / "formal_context.epoch-000.json")
    target = load_formal_theory_context(attempt / "formal_context.epoch-001.json")
    assert len(target.formula_ids) == len(source.formula_ids) + 1
    assert target.context_hash != source.context_hash
    checkpoint = read_json(attempt / "navigation_epoch_checkpoint.json", {})
    assert checkpoint["context_epoch"] == 1
    assert checkpoint["provider_calls"] == 0
    assert checkpoint["trace"][0]["decision"] == "successor_epoch_admitted"
    assert "finalists" not in checkpoint
    consumption = read_json(
        attempt / "frontier_formula_successor_consumption.epoch-001.json", {}
    )
    assert consumption["source_finalist_disposition"] == (
        "archived_source_epoch_only"
    )
    assert consumption["source_context_hash"] == source.context_hash
    assert consumption["target_context_hash"] == target.context_hash

    runner.materialize_frontier_navigation_from_journal(
        attempt,
        budget_stop_reason="blocked_before_action:navigation:provider_calls",
    )
    stopped = read_json(attempt / "run.json", {})
    assert stopped["status"] == "budget_stopped"
    assert stopped["navigation"]["finalists"] == []
    assert "reject_all_receipt" not in stopped["navigation"]
    assert stopped["budget_stop_receipt"]["reason"] == (
        "blocked_before_action:navigation:provider_calls"
    )
    current_replay = replay_frontier_campaign(attempt)
    assert current_replay["schema"] == "leanmill.frontier_campaign_replay.v5"
    assert current_replay["context_hash"] == target.context_hash
    assert current_replay["context_epoch"] == 1
    assert current_replay["budget_stop_check"]["ok"] is True
    assert current_replay["finalist_checks"] == []


def test_public_inlet_closes_cleanly_with_receipted_no_candidate(tmp_path):
    attempt = tmp_path / "attempt-no-candidate"
    run = explore_axiom_space(
        FrontierExplorationBrief(direction="Explore.", source_mode="structure_first"),
        attempt_dir=attempt,
        typed_draft=_draft(),
        packet_signer=_signer(),
        navigator_fn=_rejecting_navigator(),
    )

    assert run.status == "frontier_no_candidate"
    assert run.navigation["finalists"] == []
    assert run.navigation["reject_all_receipt"]["rejected_candidate_count"] == 1
    replay = replay_frontier_campaign(attempt)
    assert replay["ok"] is True
    assert replay["rejection_checks"][0]["identification_bits"] == 0.0
    completion = execute_frontier_boundaries(attempt)
    assert completion["status"] == "campaign_completed_no_candidate"
    assert completion["reject_all_receipt"]["receipt_id"].startswith("reject-all:")


def test_three_consecutive_receipted_reject_all_attempts_surface_pressure(tmp_path):
    runs = tmp_path / "runs"
    counts = []
    for index in range(3):
        run = explore_axiom_space(
            FrontierExplorationBrief(direction="Explore.", source_mode="structure_first"),
            attempt_dir=runs / f"attempt-{index}",
            typed_draft=_draft(),
            packet_signer=_signer(),
            navigator_fn=_rejecting_navigator(),
        )
        sequence = run.navigation["reject_all_sequence_receipt"]
        counts.append(sequence["consecutive_reject_all_count"])
    assert counts == [1, 2, 3]
    assert run.navigation["stagnation_pressure"] is True
    assert (runs / "theory_conflicts.jsonl").is_file()
    first_memory = read_json(
        runs / "attempt-0" / "theory_conflict_memory.epoch-000.json", {}
    )
    second_memory = read_json(
        runs / "attempt-1" / "theory_conflict_memory.epoch-000.json", {}
    )
    assert first_memory["conflict_count"] == 0
    assert second_memory["conflict_count"] >= 1


def test_public_inlet_rejects_unreceipted_no_candidate(tmp_path):
    def empty_navigator(_context, _blueprint, _journal, *, budget_ledger):
        assert budget_ledger is not None
        return {"finalists": [], "trace": []}

    empty_navigator.accepts_budget_ledger = True
    with pytest.raises(ValueError, match="without a finalist, request, refusal"):
        explore_axiom_space(
            FrontierExplorationBrief(direction="Explore.", source_mode="structure_first"),
            attempt_dir=tmp_path / "unreceipted",
            typed_draft=_draft(),
            packet_signer=_signer(),
            navigator_fn=empty_navigator,
        )


def test_completed_public_attempt_is_idempotent(tmp_path):
    directory = tmp_path / "attempt"
    first = explore_axiom_space(
        FrontierExplorationBrief(direction="Explore.", source_mode="structure_first"),
        attempt_dir=directory,
        typed_draft=_draft(),
        packet_signer=_signer(),
    )
    second = explore_axiom_space(
        "must not be compiled",
        attempt_dir=directory,
        draft_fn=lambda _brief: (_ for _ in ()).throw(AssertionError("called")),
    )
    assert second.run_digest if hasattr(second, "run_digest") else second.to_json()["run_digest"]
    assert second.to_json() == first.to_json()


def test_complete_context_snapshot_is_reused_without_reenumeration(tmp_path, monkeypatch):
    source_dir = tmp_path / "source"
    first = explore_axiom_space(
        FrontierExplorationBrief(direction="Explore.", source_mode="structure_first"),
        attempt_dir=source_dir,
        typed_draft=_draft(),
        packet_signer=_signer(),
    )
    snapshot_path = source_dir / "formal_context.json"
    snapshot = read_json(snapshot_path, {})
    inlet = importlib.import_module("ztare.leanmill.explore_axiom_space")
    monkeypatch.setattr(
        inlet,
        "_context_from_blueprint",
        lambda _blueprint: (_ for _ in ()).throw(AssertionError("context rebuilt")),
    )
    second_dir = tmp_path / "reused"
    second = explore_axiom_space(
        FrontierExplorationBrief(direction="Explore.", source_mode="structure_first"),
        attempt_dir=second_dir,
        typed_draft=_draft(),
        packet_signer=_signer(),
        frozen_context_ref={
            "path": str(snapshot_path),
            "context_hash": str(snapshot["context_hash"]),
            "snapshot_sha256": str(snapshot["snapshot_sha256"]),
        },
    )
    assert second.context_hash == first.context_hash
    assert read_json(second_dir / "context_reuse_receipt.json", {})["provider_calls"] == 0


def test_context_construction_failure_precedes_navigator_dispatch(
    tmp_path, monkeypatch
):
    inlet = importlib.import_module("ztare.leanmill.explore_axiom_space")
    dispatched = []

    class IncompleteContext(ValueError):
        def failure_receipt(self):
            return {"schema": "test.incomplete_context.v1", "status": "incomplete"}

        def partial_snapshot(self):
            return {"schema": "test.partial_context.v1", "models": ["partial"]}

    def navigator(_context, _blueprint, _journal, *, budget_ledger):
        dispatched.append(True)
        raise AssertionError("navigator dispatched before context admission")

    navigator.accepts_budget_ledger = True
    monkeypatch.setattr(
        inlet,
        "_context_from_blueprint",
        lambda _blueprint: (_ for _ in ()).throw(
            IncompleteContext("exact census incomplete")
        ),
    )

    with pytest.raises(ValueError, match="exact census incomplete"):
        explore_axiom_space(
            FrontierExplorationBrief(
                direction="Explore.", source_mode="structure_first"
            ),
            attempt_dir=tmp_path / "context-failure",
            typed_draft=_draft(),
            packet_signer=_signer(),
            navigator_fn=navigator,
        )

    assert dispatched == []
    assert read_json(
        tmp_path / "context-failure" / "context_construction_failure.json", {}
    )["status"] == "incomplete"
    assert read_json(
        tmp_path / "context-failure" / "partial_model_universe.json", {}
    )["models"] == ["partial"]


def test_unknown_adapter_returns_blocked_gap_through_same_inlet(tmp_path):
    run = explore_axiom_space(
        "Explore a new executable substrate.",
        attempt_dir=tmp_path / "gap-attempt",
        draft_fn=lambda _brief: _draft("unregistered_new_adapter.v1"),
        semantic_review_fn=lambda _payload: {
            "accepted": True, "candidate_law_leakage": False,
            "rationale": "typed direction preserved", "evidence_refs": ["brief"],
        },
        compiler_ref="compiler-a",
        reviewer_ref="reviewer-b",
    )
    assert run.status == "blocked_adapter_gap"
    assert run.adapter_gap["proposed_adapter_id"] == "unregistered_new_adapter.v1"


def test_legacy_candidate_template_blueprint_routes_warm(tmp_path):
    run = explore_axiom_space(
        priority_uncrossed_order_blueprint(),
        attempt_dir=tmp_path / "legacy",
    )
    assert run.status == "legacy_warm_route_required"


def test_campaign_stop_and_retire_are_idempotent_lifecycle_actions(tmp_path):
    attempt = tmp_path / "stoppable"
    explore_axiom_space(
        FrontierExplorationBrief(direction="Explore.", source_mode="structure_first"),
        attempt_dir=attempt,
        typed_draft=_draft(),
        packet_signer=_signer(),
    )
    stop = request_frontier_campaign_stop(attempt, authority_ref="operator")
    assert stop["status"] == "user_stop_requested"
    assert frontier_campaign_status(attempt)["budget"]["soft_stop_reason"] == "user_stop"
    retired = retire_frontier_campaign(
        attempt,
        authority_ref="operator",
        reason="operator ended this calibration campaign",
    )
    assert frontier_campaign_status(attempt)["status"] == "retired"
    assert retire_frontier_campaign(
        attempt,
        authority_ref="operator",
        reason="ignored on replay",
    ) == retired


def test_campaign_status_names_the_outstanding_budget_action(tmp_path):
    attempt = tmp_path / "active"
    attempt.mkdir()
    budget = budget_preset("quick")
    write_json_atomic(attempt / "budget.json", budget.to_json())
    ledger = ExplorationBudgetLedger(
        attempt / "budget.events.jsonl", budget, attempt_id=attempt.name
    )
    ledger.reserve(
        "boundary:formula-a",
        "boundary",
        {"boundary_queries": 1, "smt_calls": 1},
    )

    status = frontier_campaign_status(attempt)

    assert status["status"] == "running"
    assert status["budget"]["outstanding_reservation_count"] == 1
    assert status["budget"]["outstanding_actions"] == [
        {
            "action_id": "boundary:formula-a",
            "phase": "boundary",
            "resources": {"boundary_queries": 1, "smt_calls": 1},
            "reserved_at_ms": status["budget"]["outstanding_actions"][0][
                "reserved_at_ms"
            ],
        }
    ]


def test_boundary_rejects_stale_residual_coordinates_before_spend(tmp_path):
    attempt = tmp_path / "stale-finalist"
    explore_axiom_space(
        FrontierExplorationBrief(direction="Explore.", source_mode="structure_first"),
        attempt_dir=attempt,
        typed_draft=_draft(),
        packet_signer=_signer(),
    )
    frozen = read_json(attempt / "run.json", {})
    frozen["navigation"]["finalists"][0]["residual_information_yield"][
        "baseline_ref"
    ] = "stale.baseline.v0"
    write_json_atomic(attempt / "run.json", frozen)

    with pytest.raises(
        ValueError,
        match="frozen finalist no longer passes deterministic residual replay",
    ):
        execute_frontier_boundaries(
            attempt,
            countermodel_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("boundary spend must not begin")
            ),
        )


def test_public_campaign_resumes_through_smt_and_matched_lean_boundary(tmp_path):
    draft = _draft()
    draft["query_budget"] = {
        **draft["query_budget"],
        "larger_model_queries": 1,
    }
    draft["verification_plan"] = {
        "larger_carriers": [3],
        "conditional_isabelle": True,
        "conditional_lean": True,
        "smt_timeout_ms": 1_000,
        "isabelle_timeout_ms": 1_000,
        "lean_timeout_ms": 1_000,
    }
    attempt = tmp_path / "boundary-attempt"
    run = explore_axiom_space(
        FrontierExplorationBrief(
            direction="Explore anonymous finite binary-operation theories.",
            source_mode="structure_first",
        ),
        attempt_dir=attempt,
        typed_draft=draft,
        packet_signer=_signer(),
        budget="smoke_20m",
    )
    assert run.status == "frontier_candidates_frozen_awaiting_boundary_approval"

    class NoCountermodel:
        status = "no_countermodel_at_fixed_size"

        def to_json(self):
            return {
                "schema": "test.fixed_boundary.v1",
                "status": self.status,
                "carrier_size": 3,
                "receipt_sha256": "sha256:no-countermodel",
            }

    compile_outcomes = iter([True, False, False, False])
    calls = {"smt": 0, "isabelle": 0, "solve": 0, "compile": 0}
    boundary_order = []

    def finder(*_args, **_kwargs):
        calls["smt"] += 1
        boundary_order.append("smt")
        return NoCountermodel()

    def isabelle_executor(task, *, timeout_s):
        calls["isabelle"] += 1
        boundary_order.append("isabelle")
        return execute_isabelle_theory_task(
            task,
            timeout_s=timeout_s,
            hammer_fn=lambda *_args, **_kwargs: {
                "proof": "by (metis)",
                "used_facts": [],
            },
            verify_fn=lambda *_args, **_kwargs: (True, "accepted"),
        ).to_json()

    def solve_fn(target_name, source_text, goal, **kwargs):
        calls["solve"] += 1
        assert target_name.startswith("axiompack_consequence_")
        assert "sorry -- AXIOMPACK_PROOF" in source_text
        assert goal == ""
        assert kwargs["substrate"] == tmp_path
        governance = {
            "governance_kernel": {
                "available": True,
                "passed": True,
                "policy_profile": "target_ratification",
                "required_authorities": sorted(
                    TARGET_GOVERNANCE_AUTHORITIES
                ),
                "authority_disposition": {
                    authority: "passed"
                    for authority in TARGET_GOVERNANCE_AUTHORITIES
                },
                "authority_roster_sha256": (
                    TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256
                ),
            },
            "statement_integrity": {"ok": True},
        }
        validation = finalize_solver_validation({
            "credit_ready_at_solver_layer": True,
            "receipts": {
                "kernel_compile_receipt": {"available": True, "passed": True},
                "matched_negative_control_receipt": {
                    "available": True,
                    "passed": True,
                },
                "axiom_allowlist_receipt": {"available": True, "passed": True},
            },
        }, governance)
        return {
            "results": [
                {
                    "outcome": "closed",
                    "proof_text": "by\n  rfl",
                    "contract_validation": validation,
                }
            ],
            "closure_certificate": "test-closure-certificate",
        }

    def compile_fn(source):
        calls["compile"] += 1
        assert "sorry -- AXIOMPACK_PROOF" not in source
        assert "by\n  by\n" not in source
        return next(compile_outcomes)

    def lean_executor(task, *, budget_ledger):
        assert budget_ledger.attempt_id == attempt.name
        boundary_order.append("lean")
        return execute_governed_lean_consequence(
            task,
            substrate=tmp_path,
            timeout_s=1,
            compile_fn=compile_fn,
            solve_fn=solve_fn,
            axiom_audit_fn=lambda _source, _target: (
                True,
                False,
                ("Classical.choice",),
            ),
        ).to_json()

    def certified_single_premise_audit(premises, target):
        core = {
            "schema": "leanmill.source_single_premise_ablation.v1",
            "status": "certified_single_premise_nonimplication",
            "premise_formula_ids": list(premises),
            "target_formula_id": target,
            "premise_checks": [
                {"premise_formula_id": premise, "proved_does_not_imply": True}
                for premise in premises
            ],
        }
        return {**core, "receipt_sha256": content_hash(core)}

    completion = execute_frontier_boundaries(
        attempt,
        isabelle_executor_fn=isabelle_executor,
        lean_executor_fn=lean_executor,
        countermodel_fn=finder,
        single_premise_audit_fn=certified_single_premise_audit,
    )
    assert completion["status"] == "campaign_completed"
    boundary = completion["boundary_result"]["query_results"][0]
    assert boundary["countermodel_searches"][0]["status"] == "no_countermodel_at_fixed_size"
    assert boundary["isabelle"]["status"] == "proved"
    assert boundary["isabelle"]["attempt"]["kernel_checked"] is True
    assert boundary["lean"]["status"] == "proved_attributed"
    assert boundary["formal_consensus"]["status"] == "corroborated"
    assert boundary["formal_consensus"]["agree_ok"] == ["isabelle", "lean"]
    assert boundary["pack_synergy_status"] == "proved_exact_two_synergy"
    assert boundary["lean"]["governed_attempt"]["work_receipt"]["formal_leg"][
        "solver_entry"
    ].endswith("solve_adhoc")
    assert calls == {"smt": 1, "isabelle": 1, "solve": 1, "compile": 4}
    assert boundary_order == ["smt", "isabelle", "lean"]
    assert completion["budget_stop_receipt"]["usage"]["formal_peer_attempts"] == 1
    assert any(
        event.event_type == "conditional_consequence_proved"
        for event in TheoryCampaignJournal(attempt / "events.jsonl").replay()
    )
    assert any(
        event.event_type == "conditional_consequence_proved"
        and event.authority == "isabelle_kernel"
        for event in TheoryCampaignJournal(attempt / "events.jsonl").replay()
    )
    assert execute_frontier_boundaries(attempt) == completion
    assert calls == {"smt": 1, "isabelle": 1, "solve": 1, "compile": 4}


def test_single_premise_oracle_rejects_laundered_pack_before_boundary_spend(tmp_path):
    draft = _draft()
    draft["query_budget"] = {
        **draft["query_budget"],
        "larger_model_queries": 1,
    }
    attempt = tmp_path / "single-premise-rejected"
    run = explore_axiom_space(
        FrontierExplorationBrief(
            direction="Explore anonymous finite binary-operation theories.",
            source_mode="structure_first",
        ),
        attempt_dir=attempt,
        typed_draft=draft,
        packet_signer=_signer(),
        budget="smoke_20m",
    )
    assert run.status == "frontier_candidates_frozen_awaiting_boundary_approval"

    def audit(premises, target):
        core = {
            "schema": "leanmill.source_single_premise_ablation.v1",
            "status": "refuted_by_known_single_premise",
            "premise_formula_ids": list(premises),
            "target_formula_id": target,
            "premise_checks": [
                {
                    "premise_formula_id": premises[0],
                    "proved_implies": True,
                }
            ],
        }
        return {**core, "receipt_sha256": content_hash(core)}

    completion = execute_frontier_boundaries(
        attempt,
        single_premise_audit_fn=audit,
        countermodel_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("known single-premise implication must not spend SMT")
        ),
        lean_executor_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("known single-premise implication must not spend Lean")
        ),
    )
    rows = completion["boundary_result"]["query_results"]
    assert rows
    assert all(row["pack_synergy_status"] == "refuted_known_single_premise" for row in rows)
    assert all(row["lean"]["status"] == "skipped_known_single_premise" for row in rows)
    state = read_json(attempt / "budget_stop_receipt.json", {})
    assert state["usage"]["boundary_queries"] == 0
