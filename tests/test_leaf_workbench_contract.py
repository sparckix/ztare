from __future__ import annotations

import json

import pytest

from ztare.common.leaf_workbench_proposals import (
    pending_leaf_workbench_tool_synthesis_proposals,
    review_leaf_workbench_capability_proposals,
    sync_leaf_workbench_capability_proposals,
)
from ztare.common.leaf_workbench_python import run_visible_json_probe
from ztare.common.leaf_workbench_contract import (
    DEFAULT_LEAF_WORKBENCH_CONTRACT,
    leaf_workbench_action_request_object,
    render_leaf_workbench_mutator_surface,
    render_leaf_workbench_control_rules,
    render_leaf_workbench_contract_prompt,
    validate_leaf_workbench_capability_proposal,
    validate_leaf_workbench_receipt,
)
from ztare.worldmodel.leaf_workbench import render_worldmodel_leaf_workbench_prompt
from ztare.common.operator_proposal_contract import (
    open_cards,
    operator_proposal_card,
    record_disposition,
    set_disposition,
    write_proposal_cards,
)
from ztare.common.tool_synthesis_contract import classify_tool_target


def test_leaf_workbench_contract_is_substrate_neutral_prompt_surface() -> None:
    prompt = render_leaf_workbench_contract_prompt()

    assert DEFAULT_LEAF_WORKBENCH_CONTRACT.fingerprint() in prompt
    assert "Python carrier is sovereign" in prompt
    assert "compute_residual_quotient" in prompt
    assert "score_candidate_delta" in prompt
    assert "LEAF_WORKBENCH_CAPABILITY_PROPOSAL" in prompt
    assert "proposals are not evidence" in prompt
    assert "kernel output" in prompt
    assert "do not author them from prose" in prompt
    assert "Registered tools are conveniences" in prompt


def test_mutator_surface_prompt_snapshot() -> None:
    prompt = render_leaf_workbench_mutator_surface(
        query_rounds_left=3,
        query_menu="- thesis_excerpt: Return the first 1200 characters of the current thesis text.",
        query_menu_json='[{"name":"thesis_excerpt"}]',
        scratchpad_text="carry me verbatim",
    )

    assert "Python carrier is sovereign" in prompt
    assert "Registered tools are conveniences" in prompt
    assert "continue(query, mode=None), commit(candidate), stuck(diagnosis, friction)." in prompt
    assert "repair, re_represent, analogy_query" in prompt
    assert "Remaining query budget: 3" in prompt
    assert "carry me verbatim" in prompt
    assert "thesis_excerpt" in prompt
    assert "expected outcome" not in prompt
    assert "LOWERABILITY_BLOCKED" not in prompt


def test_worldmodel_leaf_workbench_prompt_exposes_join_surface() -> None:
    prompt = render_worldmodel_leaf_workbench_prompt()

    assert "join_lowerable_selectors" in prompt
    assert "partial-function coproduct" in prompt


def test_join_lowerable_selectors_coproduct_and_conflict(tmp_path) -> None:
    from ztare.worldmodel.leaf_workbench import join_lowerable_selectors

    project = tmp_path
    left = project / "left.json"
    right = project / "right.json"
    conflict = project / "conflict.json"
    left.write_text(
        json.dumps(
            {
                "selector_map": [
                    {"key": "A", "value": 1, "when_phase": [2, 0]},
                    {"key": "B", "value": 2, "when_action": [1]},
                ]
            }
        ),
        encoding="utf-8",
    )
    right.write_text(
        json.dumps(
            {
                "selector_map": [
                    {"key": "A", "value": 9, "when_phase": [2, 1]},
                    {"key": "C", "value": 3, "when_region": [0, 0, 1, 1, [8]]},
                ]
            }
        ),
        encoding="utf-8",
    )
    conflict.write_text(
        json.dumps({"selector_map": [{"key": "B", "value": 2}]}),
        encoding="utf-8",
    )

    merged = json.loads(
        join_lowerable_selectors(project, selector_a_ref="left.json", selector_b_ref="right.json")
    )
    refused = json.loads(
        join_lowerable_selectors(project, selector_a_ref="left.json", selector_b_ref="conflict.json")
    )

    assert merged["candidate_delta_admissible"] is True
    assert merged["join_status"] == "candidate_selectors_found"
    assert merged["joined_predicates"] == [
        {
            "key": "A",
            "value": 1,
            "guard": {"when_phase": [2, 0]},
            "lowering_scope": "guarded_partial_function_coproduct",
            "source": "selector_a_ref",
        },
        {
            "key": "A",
            "value": 9,
            "guard": {"when_phase": [2, 1]},
            "lowering_scope": "guarded_partial_function_coproduct",
            "source": "selector_b_ref",
        },
        {
            "key": "B",
            "value": 2,
            "guard": {"when_action": [1]},
            "lowering_scope": "guarded_partial_function_coproduct",
            "source": "selector_a_ref",
        },
        {
            "key": "C",
            "value": 3,
            "guard": {"when_region": [0, 0, 1, 1, [8]]},
            "lowering_scope": "guarded_partial_function_coproduct",
            "source": "selector_b_ref",
        },
    ]
    assert refused["candidate_delta_admissible"] is False
    assert refused["join_status"] == "conflict"
    assert refused["conflicting_keys"] == ["B"]
    assert refused["conflicting_guard_pairs"] == [
        {
            "selector_key": "B",
            "overlap_kind": "unguarded_duplicate_selector",
            "left_guard": {"when_action": [1]},
            "right_guard": {},
        }
    ]
    assert "B" in refused["inadmissibility_reason"]


def test_join_lowerable_selectors_conflicts_without_provable_guard_disjointness(tmp_path) -> None:
    from ztare.worldmodel.leaf_workbench import join_lowerable_selectors

    project = tmp_path
    left = project / "left.json"
    right = project / "right.json"
    left.write_text(
        json.dumps({"selector_map": [{"key": "A", "value": 1, "when_phase": [2, 0]}]}),
        encoding="utf-8",
    )
    right.write_text(
        json.dumps({"selector_map": [{"key": "A", "value": 1}]}),
        encoding="utf-8",
    )

    refused = json.loads(join_lowerable_selectors(project, selector_a_ref="left.json", selector_b_ref="right.json"))

    assert refused["candidate_delta_admissible"] is False
    assert refused["join_status"] == "conflict"
    assert refused["conflicting_keys"] == ["A"]
    assert refused["conflicting_guard_pairs"][0]["overlap_kind"] == "unguarded_duplicate_selector"


def test_leaf_workbench_control_rules_are_single_receipt_boundary() -> None:
    request = leaf_workbench_action_request_object(
        capability_id="run_visible_json_probe",
        input_refs={"artifact_refs": ["workspace/probe.json"]},
        claim_bindings=["inspect visible aggregate"],
    )

    prompt = render_leaf_workbench_control_rules(action_request=request)

    assert "LEAF WORKBENCH CONTROL RULES" in prompt
    assert "LEAF_WORKBENCH_RECEIPT` is produced by the kernel executor only" in prompt
    assert "LEAF_WORKBENCH_ACTION_REQUEST" in prompt
    assert '"capability_id":"run_visible_json_probe"' in prompt
    assert "submit `LEAF_WORKBENCH_ACTION_REQUEST` instead of authoring a receipt" in prompt


def test_tool_synthesis_contract_classifies_recursive_sensor_surfaces() -> None:
    assert classify_tool_target("src/ztare/common/briefing_pack.py") == "mutable_sensor"
    assert classify_tool_target("src/ztare/common/ask_spec.py") == "mutable_sensor"
    assert classify_tool_target("src/ztare/common/leaf_workbench_executor.py") == "mutable_sensor"
    assert classify_tool_target("src/ztare/orchestrator/retry_contract.py") == "mutable_sensor"
    assert classify_tool_target("src/ztare/worldmodel/retry_surface.py") == "mutable_sensor"
    assert classify_tool_target("src/ztare/common/control_work_items.py") == "immutable_axiom"


def test_leaf_workbench_receipt_requires_registered_capability_and_claim_binding() -> None:
    receipt = validate_leaf_workbench_receipt(
        {
            "capability_id": "run_deterministic_probe",
            "input_hashes": {"candidate_ref": "sha256:abc", "evidence_ref": "sha256:def"},
            "output_ref": "workspace/probe.json",
            "claim_bindings": ["candidate improves frozen replay metric"],
        }
    )

    assert receipt["capability_id"] == "run_deterministic_probe"
    assert receipt["contract_sha256"] == DEFAULT_LEAF_WORKBENCH_CONTRACT.fingerprint()


def test_leaf_workbench_receipt_accepts_matching_version_suffix() -> None:
    receipt = validate_leaf_workbench_receipt(
        {
            "capability_id": "run_deterministic_probe@v1",
            "input_hashes": {"candidate_ref": "sha256:abc", "evidence_ref": "sha256:def"},
            "output_ref": "workspace/probe.json",
            "claim_bindings": ["candidate improves frozen replay metric"],
        }
    )

    assert receipt["capability_id"] == "run_deterministic_probe"
    assert receipt["capability_version"] == "v1"


def test_leaf_workbench_receipt_normalizes_common_kernel_aliases() -> None:
    receipt = validate_leaf_workbench_receipt(
        {
            "capability": "run_deterministic_probe",
            "input_refs": {
                "artifact_ref": "workspace/probe-input.json",
                "artifact_sha256": "abc",
            },
            "result": {"status": "blocked"},
            "supports": "candidate needs another diagnostic",
        }
    )

    assert receipt["capability_id"] == "run_deterministic_probe"
    assert receipt["input_hashes"]["artifact_ref"] == "workspace/probe-input.json"
    assert receipt["claim_bindings"] == ["candidate needs another diagnostic"]
    assert '"status": "blocked"' in receipt["output_summary"]


def test_leaf_workbench_receipt_rejects_unknown_capability() -> None:
    with pytest.raises(ValueError, match="unknown capability_id"):
        validate_leaf_workbench_receipt(
            {
                "capability_id": "peek_hidden_target",
                "input_hashes": {"target": "sha256:hidden"},
                "output_summary": "peeked",
                "claim_bindings": ["claim"],
            }
        )


def test_leaf_workbench_capability_proposal_is_second_order_not_evidence() -> None:
    proposal = validate_leaf_workbench_capability_proposal(
        {
            "proposed_capability_id": "profile_source_conflict",
            "gap_statement": "the diligence substrate needs a bounded source-conflict detector",
            "input_contract": ["source_a_ref", "source_b_ref", "claim_ref"],
            "output_contract": ["conflict_summary", "source_refs"],
            "evaluator": "fixed rubric over known conflicting and non-conflicting source pairs",
            "secret_policy": "public_only",
            "safety_invariant": "never infer beyond cited source fields",
            "rollback_condition": "any false positive on the no-conflict fixture",
        }
    )

    assert proposal["proposed_capability_id"] == "profile_source_conflict"


def test_leaf_workbench_capability_proposal_accepts_structured_contracts() -> None:
    proposal = validate_leaf_workbench_capability_proposal(
        {
            "proposed_capability_id": "patch_base_improvement_precheck_repair",
            "gap_statement": "repair a candidate regression against a named executable prior",
            "input_contract": {
                "required_fields": ["rejection_ref", "base_source_ref", "candidate_carrier_kind"],
                "candidate_carrier_kind": "PATCH_BASE plus PATCH_DELTA",
            },
            "output_contract": {
                "required_fields": ["patch_base", "patch_delta_scope", "rollback_condition"],
                "patch_delta_scope": "bounded structural predicate over visible state/base_next/action/t",
            },
            "evaluator": {
                "type": "deterministic_replay_prejudge",
                "pass_condition": "strict verifier-tuple improvement over the preserved base",
            },
            "secret_policy": {
                "uses_secret_data": False,
                "policy": "No hidden labels, held-out answers, or private evaluator traces are embedded.",
            },
            "safety_invariant": "may not alter deterministic gates or hidden evaluator surfaces",
            "rollback_condition": "discard if replay regresses against the preserved base",
        }
    )

    assert proposal["secret_policy"] == "public_only"
    assert proposal["input_contract"]["candidate_carrier_kind"] == "PATCH_BASE plus PATCH_DELTA"


def test_leaf_workbench_capability_proposal_normalizes_needed_observation() -> None:
    proposal = validate_leaf_workbench_capability_proposal(
        {
            "capability_id": "mine_global_selector",
            "needed_observation": "lowerability witness for a boundary residue",
            "blocked_by": "current probes expose only chart-scoped predicates",
            "claim_bindings": ["produce a typed selector-mining receipt"],
        }
    )

    assert proposal["proposed_capability_id"] == "mine_global_selector"
    assert proposal["gap_statement"] == "lowerability witness for a boundary residue"
    assert proposal["input_contract"]["source"] == "proposal claim_bindings"
    assert proposal["output_contract"]["source"] == "proposal claim_bindings"


def test_leaf_workbench_capability_proposal_derives_gap_from_claim_bindings() -> None:
    proposal = validate_leaf_workbench_capability_proposal(
        {
            "capability_id": "mine_carrier_selector",
            "claim_bindings": [
                "synthesize a visible selector for a quotient-chart separator",
                "exclude hidden or identity-only features",
            ],
            "input_refs": {
                "episode_log_ref": "raw/episodes/episode_001.jsonl",
                "diagnostic_receipt_ref": "workspace/receipt.json",
            },
        }
    )

    assert proposal["proposed_capability_id"] == "mine_carrier_selector"
    assert "visible selector" in proposal["gap_statement"]
    assert "identity-only features" in proposal["gap_statement"]
    assert proposal["secret_policy"] == "public_only"


def test_leaf_workbench_capability_proposal_accepts_no_secret_holdout_policy() -> None:
    proposal = validate_leaf_workbench_capability_proposal(
        {
            "proposed_capability_id": "patch_base_improvement_precheck_repair",
            "gap_statement": "repair a candidate regression against a named executable prior",
            "input_contract": {"base_source_ref": "workspace/submissions/best.py"},
            "output_contract": {"carrier_form": "PATCH_BASE plus PATCH_DELTA"},
            "evaluator": {"name": "deterministic_replay_prejudge"},
            "secret_policy": {
                "uses_secret_holdout": False,
                "holdout_access": "none",
                "policy": "derived only from visible replay diagnostics",
            },
            "safety_invariant": "may not alter deterministic gates or hidden evaluator surfaces",
            "rollback_condition": "discard if replay regresses against the preserved base",
        }
    )

    assert proposal["secret_policy"] == "public_only"


def test_leaf_workbench_capability_proposal_accepts_allowed_forbidden_policy() -> None:
    proposal = validate_leaf_workbench_capability_proposal(
        {
            "proposed_capability_id": "observable_local_transition_predicate_miner",
            "gap_statement": "mine lowerable visible predicates for an open quotient",
            "input_contract": {"required_refs": ["episode_log_ref", "latest_regression_ref"]},
            "output_contract": {"required_fields": ["candidate_predicates"]},
            "evaluator": {"method": "deterministic_visible_replay_probe"},
            "secret_policy": {
                "allowed_data": [
                    "visible workspace artifacts referenced by input_contract",
                    "kernel-returned receipt metadata and hashes",
                ],
                "forbidden_data": [
                    "hidden holdout grids",
                    "sealed verifier internals",
                    "network or secrets",
                ],
            },
            "safety_invariant": "predicates must lower to visible carrier inputs",
            "rollback_condition": "reject if any hidden identifier is used",
        }
    )

    assert proposal["secret_policy"] == "public_only"


def test_leaf_workbench_capability_proposal_accepts_allowed_forbidden_input_aliases() -> None:
    proposal = validate_leaf_workbench_capability_proposal(
        {
            "proposed_capability_id": "lowerable_observation_selector_miner",
            "gap_statement": "mine a lowerable visible selector for an unresolved boundary",
            "input_contract": {"required_refs": ["visible_log_ref", "diagnostic_receipt_ref"]},
            "output_contract": {"required_fields": ["candidate_predicates", "confusion_matrices"]},
            "evaluator": {"method": "deterministic visible replay probe"},
            "secret_policy": {
                "allowed_inputs": "Only visible workspace artifacts and kernel-returned receipts.",
                "forbidden_inputs": "No hidden fibers, holdout labels, secrets, or network resources.",
            },
            "safety_invariant": "may not weaken evaluator boundaries",
            "rollback_condition": "reject if any forbidden input appears in the output",
        }
    )

    assert proposal["secret_policy"] == "public_only"


def test_leaf_workbench_capability_proposal_accepts_visible_artifacts_policy_token() -> None:
    proposal = validate_leaf_workbench_capability_proposal(
        {
            "proposed_capability_id": "visible_receipt_probe",
            "gap_statement": "run a bounded probe over visible artifacts",
            "input_contract": {"required_refs": ["visible_artifact_ref"]},
            "output_contract": {"required_fields": ["typed_receipt"]},
            "evaluator": {"method": "deterministic local fixture"},
            "secret_policy": "visible_workspace_artifacts_and_kernel_receipts_only",
            "safety_invariant": "does not inspect hidden evaluator state",
            "rollback_condition": "discard if probe output lacks input hashes",
        }
    )

    assert proposal["secret_policy"] == "public_only"


def test_leaf_workbench_capability_proposal_accepts_public_policy_sentence() -> None:
    proposal = validate_leaf_workbench_capability_proposal(
        {
            "proposed_capability_id": "visible_probe_gap",
            "gap_statement": "the substrate needs a bounded visible-evidence diagnostic",
            "input_contract": {"candidate_ref": "public candidate ref"},
            "output_contract": {"summary": "public diagnostic summary"},
            "evaluator": {"name": "deterministic visible replay"},
            "secret_policy": (
                "No hidden parameters, no learned constants beyond the "
                "gate-reported visible residual, no external files read by the delta."
            ),
            "safety_invariant": "side-effect free and evaluator-preserving",
            "rollback_condition": "discard on deterministic regression",
        }
    )

    assert proposal["secret_policy"] == "public_only"


def test_leaf_workbench_capability_proposal_accepts_source_policy_aliases() -> None:
    proposal = validate_leaf_workbench_capability_proposal(
        {
            "proposed_capability_id": "mine_visible_boundary",
            "gap_statement": "need a visible lowerability witness",
            "input_contract": {"required_fields": ["episode_log_ref"]},
            "output_contract": {"required_fields": ["candidate_predicates"]},
            "evaluator": {"type": "deterministic_probe"},
            "secret_policy": {
                "allowed_sources": ["visible episode logs", "visible receipt"],
                "disallowed_sources": ["hidden holdout rollouts", "sealed evaluator internals"],
            },
            "safety_invariant": "no hidden sources",
            "rollback_condition": "any hidden-source dependency",
        }
    )

    assert proposal["secret_policy"] == "public_only"


def test_leaf_workbench_capability_proposal_sync_writes_deduped_card(tmp_path) -> None:
    text = (
        'LEAF_WORKBENCH_CAPABILITY_PROPOSAL: {"proposed_capability_id":"profile_source_conflict",'
        '"gap_statement":"the diligence substrate needs a bounded source-conflict detector",'
        '"input_contract":["source_a_ref","source_b_ref","claim_ref"],'
        '"output_contract":["conflict_summary","source_refs"],'
        '"evaluator":"fixed rubric over known conflicting and non-conflicting source pairs",'
        '"secret_policy":"public_only",'
        '"safety_invariant":"never infer beyond cited source fields",'
        '"rollback_condition":"any false positive on the no-conflict fixture"}'
    )

    first = sync_leaf_workbench_capability_proposals(tmp_path, text, source_ref="test")
    second = sync_leaf_workbench_capability_proposals(tmp_path, text, source_ref="test")

    ledger = tmp_path / "workspace" / "leaf_workbench_capability_proposals.jsonl"
    assert len(first) == 1
    assert second == []
    assert ledger.exists()
    assert first[0]["status"] == "queued"
    assert first[0]["proposal"]["proposed_capability_id"] == "profile_source_conflict"
    assert "cannot support candidate adoption" in first[0]["authority"]


def test_leaf_workbench_capability_proposal_sync_accepts_multiline_json(tmp_path) -> None:
    text = """
The candidate cannot support this current patch.
LEAF_WORKBENCH_CAPABILITY_PROPOSAL: {
  "proposed_capability_id": "inspect_multiline_context",
  "gap_statement": "need a bounded context diagnostic",
  "input_contract": {
    "required_fields": ["diagnostics_ref", "episode_log_ref"]
  },
  "output_contract": {
    "required_fields": ["context_delta"]
  },
  "evaluator": {
    "type": "fixture_replay",
    "pass_condition": "stable context delta"
  },
  "secret_policy": {
    "uses_secret_data": false,
    "policy": "No hidden data is read."
  },
  "safety_invariant": "visible artifacts only",
  "rollback_condition": "nondeterministic output or failed fixture"
}
Trailing prose must not be consumed.
"""

    rows = sync_leaf_workbench_capability_proposals(tmp_path, text, source_ref="test")

    assert len(rows) == 1
    assert rows[0]["proposal"]["proposed_capability_id"] == "inspect_multiline_context"
    assert rows[0]["proposal"]["secret_policy"] == "public_only"


def test_leaf_workbench_capability_proposal_does_not_auto_open_tool_synthesis_card(tmp_path) -> None:
    text = (
        'LEAF_WORKBENCH_CAPABILITY_PROPOSAL: {"proposed_capability_id":"inspect_context_split",'
        '"gap_statement":"need a bounded context split diagnostic",'
        '"input_contract":["diagnostics_ref","episode_log_ref"],'
        '"output_contract":["context_delta"],'
        '"evaluator":"fixture with two quotients that differ by context feature",'
        '"secret_policy":"derived_no_raw_secret",'
        '"safety_invariant":"reads visible logs only",'
        '"rollback_condition":"any nondeterministic output or regression in briefing tests",'
        '"target_artifact":"src/ztare/worldmodel/leaf_workbench.py"}'
    )

    rows = sync_leaf_workbench_capability_proposals(tmp_path, text, source_ref="test")

    assert len(rows) == 1
    assert rows[0]["tool_synthesis_status"] == "deferred_until_lowerability_obstruction"
    assert "tool_synthesis_card_sha256" not in rows[0]
    assert not (tmp_path / "workspace" / "strategy_experiments.jsonl").exists()


def test_lowerability_backed_capability_proposal_opens_only_with_decision_policy(tmp_path) -> None:
    text = (
        'LOWERABILITY_BLOCKED: {"visible_capabilities_attempted":["probe-json"],'
        '"candidate_family_attempted":"context_split",'
        '"obstruction":"visible records do not contain a gamma-lowerable selector",'
        '"missing_witness_or_sensor":"bounded context split diagnostic",'
        '"next_action":"review proposed mutable sensor",'
        '"evidence_refs":["workspace/visible_cli_receipts/probe.json"],'
        '"visible_receipt_refs":["workspace/visible_cli_receipts/probe.json"]}\n'
        'LEAF_WORKBENCH_CAPABILITY_PROPOSAL: {"proposed_capability_id":"inspect_context_split",'
        '"gap_statement":"need a bounded context split diagnostic",'
        '"input_contract":["diagnostics_ref","episode_log_ref"],'
        '"output_contract":["context_delta"],'
        '"evaluator":"fixture with two quotients that differ by context feature",'
        '"secret_policy":"derived_no_raw_secret",'
        '"safety_invariant":"reads visible logs only",'
        '"rollback_condition":"any nondeterministic output or regression in briefing tests",'
        '"target_artifact":"src/ztare/worldmodel/leaf_workbench.py"}'
    )

    rows = sync_leaf_workbench_capability_proposals(
        tmp_path,
        text,
        source_ref="test",
        decision_policy="direct",
    )

    strategy = tmp_path / "workspace" / "strategy_experiments.jsonl"
    assert len(rows) == 1
    assert rows[0]["tool_synthesis_card_sha256"]
    assert (tmp_path / "workspace" / "strategy_decision_receipts.jsonl").exists()
    card = json.loads(strategy.read_text(encoding="utf-8").splitlines()[0])
    assert card["kind"] == "tool_synthesis"
    assert card["action_plan"]["target_artifact"] == "src/ztare/worldmodel/leaf_workbench.py"
    assert card["action_plan"]["mutable_surface"] == "mutable_sensor"


def test_tool_proposal_batch_rejection_stops_pending_queue(tmp_path) -> None:
    text = (
        'LOWERABILITY_BLOCKED: {"visible_capabilities_attempted":["probe-json"],'
        '"candidate_family_attempted":"context_split",'
        '"obstruction":"visible records do not contain a gamma-lowerable selector",'
        '"missing_witness_or_sensor":"bounded context split diagnostic",'
        '"next_action":"review proposed mutable sensor",'
        '"evidence_refs":["workspace/visible_cli_receipts/probe.json"],'
        '"visible_receipt_refs":["workspace/visible_cli_receipts/probe.json"]}\n'
        'LEAF_WORKBENCH_CAPABILITY_PROPOSAL: {"proposed_capability_id":"inspect_context_split",'
        '"gap_statement":"need a bounded context split diagnostic",'
        '"input_contract":["diagnostics_ref","episode_log_ref"],'
        '"output_contract":["context_delta"],'
        '"evaluator":"fixture with two quotients that differ by context feature",'
        '"secret_policy":"derived_no_raw_secret",'
        '"safety_invariant":"reads visible logs only",'
        '"rollback_condition":"any nondeterministic output or regression in briefing tests",'
        '"target_artifact":"src/ztare/worldmodel/leaf_workbench.py"}'
    )
    rows = sync_leaf_workbench_capability_proposals(tmp_path, text, source_ref="test")
    assert len(rows) == 1
    assert len(pending_leaf_workbench_tool_synthesis_proposals(tmp_path)) == 1

    receipt = review_leaf_workbench_capability_proposals(
        tmp_path,
        decision_policy="single_authority",
        decision_positions=[
            {
                "actor_id": "reviewer",
                "role_id": "role.tool_proposal_reviewer",
                "position": "reject",
                "rationale": "current capabilities suffice",
                "evidence_refs": ["proposal_sha256:" + rows[0]["proposal_sha256"]],
            }
        ],
    )

    assert receipt["recommendation"] == "reject"
    assert pending_leaf_workbench_tool_synthesis_proposals(tmp_path) == []


def test_nested_leaf_workbench_capability_proposal_can_use_default_target(tmp_path) -> None:
    text = (
        'LEAF_WORKBENCH_CAPABILITY_PROPOSAL: {"capability_id":"propose_selector_miner",'
        '"claim_bindings":["need a lowerable selector miner"],'
        '"proposal":{"requested_capability":"mine_global_carrier_selectors",'
        '"purpose":"expose an admissible lowerability witness from visible context",'
        '"required_inputs":{"episode_log_ref":"raw/episodes/episode_001.jsonl"},'
        '"must_exclude_feature_classes":["absolute_time","hidden_evaluator_field"],'
        '"desired_output_schema":"selector-miner-v1 with candidate_predicates",'
        '"success_condition":"return a zero-error visible predicate or explain underdetermination"}}'
    )

    rows = sync_leaf_workbench_capability_proposals(
        tmp_path,
        text,
        source_ref="test",
        default_target_artifact="src/ztare/worldmodel/leaf_workbench.py",
    )

    assert len(rows) == 1
    assert rows[0]["proposal"]["proposed_capability_id"] == "mine_global_carrier_selectors"
    assert rows[0]["proposal"]["secret_policy"] == "public_only"
    assert rows[0]["tool_synthesis_status"] == "deferred_until_lowerability_obstruction"
    assert not (tmp_path / "workspace" / "strategy_experiments.jsonl").exists()


def test_leaf_workbench_capability_proposal_can_open_mutable_routing_sensor_card(tmp_path) -> None:
    text = (
        'LEAF_WORKBENCH_CAPABILITY_PROPOSAL: {"proposed_capability_id":"route_boundary_gate",'
        '"gap_statement":"visible replay is exact but boundary gate evidence is missing",'
        '"input_contract":["latest_harness_weakness_ref","failed_gates"],'
        '"output_contract":["recommended_capability_id","boundary_gate_ref"],'
        '"evaluator":"fixture with exact visible replay and holdout-only failure",'
        '"secret_policy":"public_only",'
        '"safety_invariant":"does not weaken replay, holdout, or terminal gates",'
        '"rollback_condition":"any candidate promotion without gate receipt",'
        '"target_artifact":"src/ztare/common/harness_weakness.py"}'
    )

    rows = sync_leaf_workbench_capability_proposals(tmp_path, text, source_ref="test")

    assert len(rows) == 1
    assert rows[0]["tool_synthesis_status"] == "deferred_until_lowerability_obstruction"
    assert "tool_synthesis_card_sha256" not in rows[0]
    assert not (tmp_path / "workspace" / "strategy_experiments.jsonl").exists()


def test_leaf_workbench_capability_proposal_does_not_open_hard_kernel_card(tmp_path) -> None:
    text = (
        'LEAF_WORKBENCH_CAPABILITY_PROPOSAL: {"proposed_capability_id":"force_gate_pass",'
        '"gap_statement":"bad request",'
        '"input_contract":["candidate_ref"],'
        '"output_contract":["pass"],'
        '"evaluator":"none",'
        '"secret_policy":"public_only",'
        '"safety_invariant":"none",'
        '"rollback_condition":"none",'
        '"target_artifact":"src/ztare/validator/core/pre_judge_gate.py"}'
    )

    rows = sync_leaf_workbench_capability_proposals(tmp_path, text, source_ref="test")

    assert len(rows) == 1
    assert "tool_synthesis_card_sha256" not in rows[0]
    assert not (tmp_path / "workspace" / "strategy_experiments.jsonl").exists()


def test_visible_json_probe_runs_over_named_artifacts(tmp_path) -> None:
    artifact = tmp_path / "workspace" / "diagnostics.json"
    artifact.parent.mkdir()
    artifact.write_text(
        '{"mismatch_classes":[{"count":3},{"count":5}]}',
        encoding="utf-8",
    )

    result = run_visible_json_probe(
        project_dir=tmp_path,
        artifact_refs=["workspace/diagnostics.json"],
        probe_py=(
            'rows = ARTIFACTS["workspace/diagnostics.json"]["mismatch_classes"]\n'
            'RESULT = {"total": sum(row["count"] for row in rows), "n": len(rows)}\n'
        ),
    )

    assert result["result"] == {"total": 8, "n": 2}
    assert result["artifact_hashes"]["workspace/diagnostics.json"]
    assert result["probe_sha256"]


def test_visible_json_probe_uses_default_summary_when_probe_is_empty(tmp_path) -> None:
    artifact = tmp_path / "workspace" / "diagnostics.json"
    artifact.parent.mkdir()
    artifact.write_text(
        '{"schema":"demo","relation":"changed_support","candidate_top_quotient":{"bbox":[1,2,3,4]}}',
        encoding="utf-8",
    )

    result = run_visible_json_probe(
        project_dir=tmp_path,
        artifact_refs=["workspace/diagnostics.json"],
        probe_py="",
    )

    summary = result["result"]["workspace/diagnostics.json"]
    assert summary["schema"] == "demo"
    assert summary["relation"] == "changed_support"
    assert summary["candidate_top_quotient"]["bbox"] == [1, 2, 3, 4]


def test_visible_json_probe_default_summary_surfaces_counterexample_trace(tmp_path) -> None:
    artifact = tmp_path / "workspace" / "latest_patch_base_regression.json"
    artifact.parent.mkdir()
    artifact.write_text(
        json.dumps(
            {
                "schema": "ztare-latest-patch-base-regression-v1",
                "candidate_regression_receipt": {
                    "candidate_relation": "regression",
                    "best_prior_exact_rows": 10,
                    "candidate_exact_rows": 8,
                    "quotient_comparison": {
                        "relation": "changed_support",
                        "candidate_top_quotient": {"bbox": [1, 2, 1, 2]},
                        "best_prior_top_quotient": {"bbox": [3, 4, 3, 4]},
                    },
                },
                "counterexample_trace": {
                    "first_mismatch": "replay mismatch",
                    "wrong_cell_count": 2,
                    "mismatch_classes": [
                        {"action": 0, "count": 5, "signature": {"bbox": [1, 2, 1, 2]}},
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    result = run_visible_json_probe(
        project_dir=tmp_path,
        artifact_refs=["workspace/latest_patch_base_regression.json"],
        probe_py="",
    )

    summary = result["result"]["workspace/latest_patch_base_regression.json"]
    assert summary["counterexample_trace"]["first_mismatch"] == "replay mismatch"
    assert summary["counterexample_trace"]["mismatch_classes"][0]["count"] == 5
    receipt = summary["candidate_regression_receipt"]
    assert receipt["candidate_relation"] == "regression"
    assert receipt["quotient_comparison"]["relation"] == "changed_support"


def test_visible_json_probe_rejects_imports_and_path_escape(tmp_path) -> None:
    artifact = tmp_path / "visible.json"
    artifact.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="forbids AST node Import"):
        run_visible_json_probe(
            project_dir=tmp_path,
            artifact_refs=["visible.json"],
            probe_py="import os\nRESULT = 1\n",
        )
    with pytest.raises(ValueError, match="escapes project"):
        run_visible_json_probe(
            project_dir=tmp_path,
            artifact_refs=["../secret.json"],
            probe_py="RESULT = 1\n",
        )


def test_open_cards_uses_latest_disposition_by_failure_family_sha(tmp_path) -> None:
    ledger = tmp_path / "strategy.jsonl"
    card = operator_proposal_card(
        failure_family="same-family",
        evidence_indices=[1],
        spatial_footprint={"n": 1},
        why_existing_ops_fail={"identity": "does not change state"},
        proposed_operator_sketch="new_op",
        acceptance_test="planted fixture",
    )
    assert write_proposal_cards(ledger, [card])
    # Simulate a legacy duplicate append rather than an in-place upsert.
    with ledger.open("a", encoding="utf-8") as f:
        import json

        f.write(json.dumps(set_disposition(card, "rejected")) + "\n")

    assert open_cards(ledger) == []

    reopened = dict(card)
    reopened["rationale"] = "new evidence reopened same family"
    record_disposition(ledger, reopened)

    assert [row["failure_family_sha"] for row in open_cards(ledger)] == [
        card["failure_family_sha"]
    ]
