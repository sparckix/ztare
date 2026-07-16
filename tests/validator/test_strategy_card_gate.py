from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ztare.common.operator_proposal_contract import write_proposal_cards
from ztare.validator.core.strategy_card_gate import (
    blocked_eval_from_strategy_card_gate,
    evaluate_strategy_card_gate,
    extract_strategy_card_discharges,
    has_valid_blocked_strategy_card_discharge,
)


def _write_strategy_card(project: Path) -> dict:
    card = {
        "schema": "strategy-experiment-v1",
        "kind": "search_control_residue_repair",
        "failure_family": "family-a",
        "rationale": "planner exhausted without information gain",
        "falsifiable_prediction": "produce narrower receipt",
        "action_plan": {
            "residue_quotient": {
                "residue_class": "closed_dynamics_no_terminal_progress",
            },
            "routing_class": "target_synthesis_or_discriminating_probe",
            "required_next_gate": {
                "command": "arc3_play_loop",
                "spends_external_actions": True,
                "success_status": "terminal_event_or_new_evidence",
            },
        },
        "kill_condition": "same residue repeats",
        "disposition": "open",
    }
    written = write_proposal_cards(project / "workspace" / "strategy_experiments.jsonl", [card])
    assert written
    return written[0]


def test_strategy_card_gate_blocks_silent_candidate(tmp_path: Path) -> None:
    card = _write_strategy_card(tmp_path)

    result = evaluate_strategy_card_gate(
        project_dir=tmp_path,
        thesis_text="This thesis discusses old evidence only.",
        candidate_source="def step(grid, action, t): return grid",
    )

    assert result.ran is True
    assert result.passed is False
    assert result.payload["missing"][0]["failure_family_sha"] == card["failure_family_sha"]
    blocked = blocked_eval_from_strategy_card_gate(result)
    assert blocked["score"] == 0
    assert blocked["strategy_card_gate_fired"] is True


def test_strategy_card_gate_does_not_block_on_meta_hardening_cards(tmp_path: Path) -> None:
    card = {
        "schema": "strategy-experiment-v1",
        "kind": "tool_synthesis",
        "failure_family": "tool-backlog",
        "rationale": "queued instrument improvement",
        "falsifiable_prediction": "implement tool and pass evaluator",
        "action_plan": {
            "target_artifact": "src/ztare/worldmodel/leaf_workbench.py",
            "mutable_surface": "mutable_sensor",
            "required_next_gate": {
                "command": "tool_synthesis_gate",
                "success_status": "compiled_tool_receipt_plus_regression_pass",
            },
        },
        "disposition": "open",
    }
    write_proposal_cards(tmp_path / "workspace" / "strategy_experiments.jsonl", [card])

    result = evaluate_strategy_card_gate(
        project_dir=tmp_path,
        thesis_text="Candidate cites visible evidence and submits executable code.",
        candidate_source="def PATCH_DELTA(base_next, state, action):\n    return base_next\n",
    )

    assert result.ran is False
    assert result.passed is False
    assert result.payload["verdict"] == "no_blocking_cards"
    assert result.payload["control_receipt"]["fallback_taken"] == "no_blocking_cards"
    assert result.payload["all_open_cards"] == 1
    assert result.payload["run_lane"] == "skill_acquisition"
    assert len(result.payload["nonblocking_cards"]) == 1
    assert result.payload["nonblocking_cards"][0]["role"]["lane"] == "meta_hardening"


def test_strategy_card_gate_blocks_object_card_even_with_meta_card_present(tmp_path: Path) -> None:
    object_card = _write_strategy_card(tmp_path)
    meta_card = {
        "schema": "strategy-experiment-v1",
        "kind": "tool_synthesis",
        "failure_family": "tool-backlog",
        "rationale": "queued instrument improvement",
        "falsifiable_prediction": "implement tool and pass evaluator",
        "action_plan": {
            "target_artifact": "src/ztare/worldmodel/leaf_workbench.py",
            "mutable_surface": "mutable_sensor",
            "required_next_gate": {
                "command": "tool_synthesis_gate",
                "success_status": "compiled_tool_receipt_plus_regression_pass",
            },
        },
        "disposition": "open",
    }
    write_proposal_cards(tmp_path / "workspace" / "strategy_experiments.jsonl", [meta_card])

    result = evaluate_strategy_card_gate(
        project_dir=tmp_path,
        thesis_text="Candidate omits object card discharge.",
        candidate_source="def PATCH_DELTA(base_next, state, action):\n    return base_next\n",
    )

    assert result.ran is True
    assert result.passed is False
    assert result.payload["missing"] == [
        {
            "failure_family_sha": object_card["failure_family_sha"],
            "kind": object_card["kind"],
        }
    ]
    assert len(result.payload["nonblocking_cards"]) == 1
    assert result.payload["nonblocking_cards"][0]["role"]["lane"] == "meta_hardening"


def test_strategy_card_gate_binds_only_newest_frontier_work_order(tmp_path: Path) -> None:
    older = _write_strategy_card(tmp_path)
    newer = dict(older)
    newer["failure_family"] = "family-b"
    newer.pop("failure_family_sha", None)
    written = write_proposal_cards(
        tmp_path / "workspace" / "strategy_experiments.jsonl",
        [newer],
    )
    assert written

    result = evaluate_strategy_card_gate(
        project_dir=tmp_path,
        thesis_text="candidate without a frontier discharge",
        candidate_source="def step(grid, action, t): return grid",
    )

    assert result.payload["open_cards"] == 1
    assert result.payload["all_open_cards"] == 2
    assert result.payload["missing"] == [
        {
            "failure_family_sha": written[0]["failure_family_sha"],
            "kind": newer["kind"],
        }
    ]
    assert len(result.payload["nonblocking_cards"]) == 1
    assert result.payload["nonblocking_cards"][0]["failure_family_sha"] == (
        older["failure_family_sha"]
    )


def test_identity_bound_workbench_task_supersedes_unbound_strategy_backlog(
    tmp_path: Path,
) -> None:
    older = _write_strategy_card(tmp_path)
    source = "def step(grid, action, t): return grid\n"
    (tmp_path / "test_model.py").write_text(source, encoding="utf-8")
    candidate_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    weakness = {
        "active_frontier": {"candidate_sha": candidate_sha},
        "candidate_sha": candidate_sha,
        "workbench_task": {
            "task_id": "task-current",
            "source_ref": "test_model.py",
            "admissible_capability_ids": ["inspect_worldmodel_counterexample_context"],
        },
    }
    workspace = tmp_path / "workspace"
    (workspace / "latest_harness_weakness.json").write_text(
        json.dumps(weakness),
        encoding="utf-8",
    )

    superseded = evaluate_strategy_card_gate(
        project_dir=tmp_path,
        thesis_text="current task owns the evidence frontier",
        candidate_source=source,
    )
    assert superseded.ran is False
    assert superseded.payload["verdict"] == "no_blocking_cards"

    bound = dict(older)
    bound["failure_family"] = "family-bound-to-current-carrier"
    bound.pop("failure_family_sha", None)
    bound["active_frontier"] = {"candidate_sha": candidate_sha}
    written = write_proposal_cards(
        workspace / "strategy_experiments.jsonl",
        [bound],
    )
    current = evaluate_strategy_card_gate(
        project_dir=tmp_path,
        thesis_text="candidate omits the bound Strategy discharge",
        candidate_source=source,
    )
    assert current.ran is True
    assert current.payload["missing"][0]["failure_family_sha"] == (
        written[0]["failure_family_sha"]
    )


def test_strategy_card_gate_rejects_thin_blocked_repair_receipt(tmp_path: Path) -> None:
    card = _write_strategy_card(tmp_path)
    receipt = {
        "failure_family_sha": card["failure_family_sha"],
        "outcome": "blocked",
        "observed_status": "target_specification_gap",
        "evidence_refs": ["workspace/strategy_probe.json"],
    }

    result = evaluate_strategy_card_gate(
        project_dir=tmp_path,
        thesis_text=f"STRATEGY_CARD_DISCHARGE: {json.dumps(receipt)}",
        candidate_source="",
    )

    assert result.ran is True
    assert result.passed is False
    assert result.payload["invalid"][0]["reason"] == "blocked_repair_missing_blocker_kind"


def test_strategy_card_gate_accepts_typed_blocked_repair_receipt(tmp_path: Path) -> None:
    card = _write_strategy_card(tmp_path)
    receipt = {
        "failure_family_sha": card["failure_family_sha"],
        "outcome": "blocked",
        "observed_status": "target_specification_gap",
        "blocker_kind": "attempted_repair_failed",
        "attempted_repair": "candidate kept sibling quotient exact but failed holdout",
        "next_action": "route sibling-spillover counterexample to refinement ladder",
        "evidence_refs": ["workspace/strategy_probe.json"],
    }

    result = evaluate_strategy_card_gate(
        project_dir=tmp_path,
        thesis_text=f"STRATEGY_CARD_DISCHARGE: {json.dumps(receipt)}",
        candidate_source="",
    )

    assert result.ran is True
    assert result.passed is True
    assert has_valid_blocked_strategy_card_discharge(
        project_dir=tmp_path,
        thesis_text=f"STRATEGY_CARD_DISCHARGE: {json.dumps(receipt)}",
        candidate_source="",
    )


def test_strategy_card_blocked_discharge_helper_rejects_satisfied_receipt(
    tmp_path: Path,
) -> None:
    card = _write_strategy_card(tmp_path)
    receipt = {
        "failure_family_sha": card["failure_family_sha"],
        "outcome": "satisfied",
        "observed_status": "terminal_event_or_new_evidence",
        "evidence_refs": ["workspace/strategy_probe.json"],
    }

    assert not has_valid_blocked_strategy_card_discharge(
        project_dir=tmp_path,
        thesis_text=f"STRATEGY_CARD_DISCHARGE: {json.dumps(receipt)}",
        candidate_source="",
    )


def test_strategy_card_extractor_accepts_raw_typed_control_receipts() -> None:
    payload = {
        "control_receipts": [
            {
                "type": "STRATEGY_CARD_DISCHARGE",
                "payload": {
                    "failure_family_sha": "abc123",
                    "kind": "compressed_counterexample_repair",
                    "outcome": "blocked",
                    "blocker_kind": "underdetermined_by_current_log",
                    "evidence_refs": ["workspace/candidate_memory.json"],
                    "new_evidence_refs": ["same carrier has no visible residual"],
                    "next_action": "run the next discriminating probe",
                },
            }
        ],
        "thesis_markdown": "body",
        "test_model_py": (
            "def PATCH_DELTA(base_next, state, action, t):\n"
            "    return base_next\n"
        ),
    }

    receipts = extract_strategy_card_discharges(json.dumps(payload))
    assert receipts == [payload["control_receipts"][0]["payload"]]


def test_strategy_card_extractor_accepts_colon_marker_receipt() -> None:
    receipt = {
        "failure_family_sha": "abc123",
        "outcome": "blocked",
        "blocker_kind": "requires_external_actions",
        "evidence_refs": ["workspace/candidate_memory.json"],
        "next_action": "run the next discriminating probe",
    }

    receipts = extract_strategy_card_discharges(
        "STRATEGY_CARD_DISCHARGE: " + json.dumps(receipt)
    )

    assert receipts == [receipt]


def test_strategy_card_gate_accepts_receipt_alias(tmp_path: Path) -> None:
    card = _write_strategy_card(tmp_path)
    receipt = {
        "failure_family_sha": card["failure_family_sha"],
        "outcome": "blocked",
        "observed_status": "target_specification_gap",
        "blocker_kind": "attempted_repair_failed",
        "attempted_probe": "candidate scored against frozen replay and preserved residue",
        "next_action": "route residue to the next discriminating probe",
        "evidence_refs": ["workspace/strategy_probe.json"],
    }

    result = evaluate_strategy_card_gate(
        project_dir=tmp_path,
        thesis_text=f"STRATEGY_CARD_RECEIPT: {json.dumps(receipt)}",
        candidate_source="",
    )

    assert result.ran is True
    assert result.passed is True


def test_strategy_card_gate_accepts_blocked_repair_new_evidence_refs(
    tmp_path: Path,
) -> None:
    card = _write_strategy_card(tmp_path)
    receipt = {
        "failure_family_sha": card["failure_family_sha"],
        "outcome": "blocked",
        "observed_status": "target_specification_gap",
        "blocker_kind": "underdetermined_by_current_log",
        "next_action": "collect one discriminator witness",
        "new_evidence_refs": ["workspace/latest_replay_diagnostics_after_abduce.json"],
    }

    result = evaluate_strategy_card_gate(
        project_dir=tmp_path,
        thesis_text=f"STRATEGY_CARD_DISCHARGE: {json.dumps(receipt)}",
        candidate_source="",
    )

    assert result.ran is True
    assert result.passed is True


def test_strategy_card_gate_accepts_blocked_repair_without_attempt_for_missing_seed(
    tmp_path: Path,
) -> None:
    card = _write_strategy_card(tmp_path)
    receipt = {
        "failure_family_sha": card["failure_family_sha"],
        "outcome": "blocked",
        "observed_status": "seed artifact absent",
        "blocker_kind": "missing_seed",
        "next_action": "regenerate boundary seed through sealed play before repair",
        "evidence_refs": ["workspace/seed_audit.json"],
    }

    result = evaluate_strategy_card_gate(
        project_dir=tmp_path,
        thesis_text=f"STRATEGY_CARD_DISCHARGE: {json.dumps(receipt)}",
        candidate_source="",
    )

    assert result.ran is True
    assert result.passed is True


def test_strategy_card_gate_rejects_external_action_blocker_for_offline_gate(
    tmp_path: Path,
) -> None:
    card = {
        "schema": "strategy-experiment-v1",
        "kind": "compressed_counterexample_repair",
        "failure_family": "offline-transfer-probe",
        "rationale": "bounded transfer residue",
        "falsifiable_prediction": "rerun the offline transfer probe",
        "action_plan": {
            "residue_quotient": {"residue_class": "boundary_update"},
            "required_next_gate": {
                "command": "arc3_level_transfer_probe",
                "success_status": "exact_local_transfer_depth",
            },
            "repair_certificate": {"repair_class": "quotient_repair"},
        },
        "kill_condition": "probe refutes the repair",
        "disposition": "open",
    }
    written = write_proposal_cards(
        tmp_path / "workspace" / "strategy_experiments.jsonl",
        [card],
    )
    receipt = {
        "failure_family_sha": written[0]["failure_family_sha"],
        "outcome": "blocked",
        "observed_status": "bounded_mismatch",
        "blocker_kind": "requires_external_actions",
        "next_action": "rerun the transfer probe after repair",
        "evidence_refs": ["workspace/latest_level_transfer_probe.json"],
    }

    result = evaluate_strategy_card_gate(
        project_dir=tmp_path,
        thesis_text=f"STRATEGY_CARD_DISCHARGE: {json.dumps(receipt)}",
        candidate_source="",
    )

    assert result.ran is True
    assert result.passed is False
    assert (
        result.payload["invalid"][0]["reason"]
        == "blocked_repair_requires_external_actions_not_supported_by_required_gate"
    )


def test_strategy_card_gate_accepts_external_action_blocker_for_declared_gate(
    tmp_path: Path,
) -> None:
    card = _write_strategy_card(tmp_path)
    receipt = {
        "failure_family_sha": card["failure_family_sha"],
        "outcome": "blocked",
        "observed_status": "plan_exhausted",
        "blocker_kind": "requires_external_actions",
        "next_action": "run the live play loop to collect terminal evidence",
        "evidence_refs": ["workspace/arc3_play_loop_report.json"],
    }

    result = evaluate_strategy_card_gate(
        project_dir=tmp_path,
        thesis_text=f"STRATEGY_CARD_DISCHARGE: {json.dumps(receipt)}",
        candidate_source="",
    )

    assert result.ran is True
    assert result.passed is True


def test_strategy_card_gate_accepts_structured_next_action_for_blocked_repair(
    tmp_path: Path,
) -> None:
    card = _write_strategy_card(tmp_path)
    receipt = {
        "failure_family_sha": card["failure_family_sha"],
        "outcome": "blocked",
        "observed_status": "candidate_delta_not_gate_observed",
        "blocker_kind": "underdetermined_by_current_log",
        "next_action": {
            "type": "LEAF_WORKBENCH_ACTION_REQUEST",
            "payload": {
                "capability_id": "run_strategy_required_gate",
                "input_refs": {
                    "failure_family_sha": card["failure_family_sha"],
                    "command": "arc3_level_transfer_probe",
                    "candidate_path": "test_model.py",
                },
            },
        },
        "evidence_refs": ["workspace/latest_level_transfer_probe.json"],
        "new_evidence_refs": ["candidate needs declared gate receipt"],
    }

    result = evaluate_strategy_card_gate(
        project_dir=tmp_path,
        thesis_text=f"STRATEGY_CARD_DISCHARGE: {json.dumps(receipt)}",
        candidate_source="",
    )

    assert result.ran is True
    assert result.passed is True


def test_strategy_card_gate_rejects_external_action_blocker_without_declared_property(
    tmp_path: Path,
) -> None:
    card = {
        "schema": "strategy-experiment-v1",
        "kind": "search_control_residue_repair",
        "failure_family": "label-only-command",
        "rationale": "surface label must not imply evaluator property",
        "falsifiable_prediction": "produce narrower receipt",
        "action_plan": {
            "residue_quotient": {"residue_class": "closed_dynamics_no_progress"},
            "required_next_gate": {
                "command": "arc3_play_loop",
                "success_status": "terminal_event_or_new_evidence",
            },
        },
        "kill_condition": "same residue repeats",
        "disposition": "open",
    }
    written = write_proposal_cards(
        tmp_path / "workspace" / "strategy_experiments.jsonl",
        [card],
    )
    receipt = {
        "failure_family_sha": written[0]["failure_family_sha"],
        "outcome": "blocked",
        "observed_status": "plan_exhausted",
        "blocker_kind": "requires_external_actions",
        "next_action": "run declared gate",
        "evidence_refs": ["workspace/report.json"],
    }

    result = evaluate_strategy_card_gate(
        project_dir=tmp_path,
        thesis_text=f"STRATEGY_CARD_DISCHARGE: {json.dumps(receipt)}",
        candidate_source="",
    )

    assert result.ran is True
    assert result.passed is False
    assert (
        result.payload["invalid"][0]["reason"]
        == "blocked_repair_requires_external_actions_not_supported_by_required_gate"
    )


def test_strategy_card_gate_rejects_satisfied_without_gate_status(tmp_path: Path) -> None:
    card = _write_strategy_card(tmp_path)
    receipt = {
        "failure_family_sha": card["failure_family_sha"],
        "outcome": "satisfied",
        "evidence_refs": ["workspace/probe.json"],
    }

    result = evaluate_strategy_card_gate(
        project_dir=tmp_path,
        thesis_text=f"STRATEGY_CARD_DISCHARGE = {receipt!r}",
        candidate_source="",
    )

    assert result.passed is False
    assert result.payload["invalid"][0]["reason"] == "satisfied_receipt_missing_next_gate_status"


def test_strategy_card_gate_structural_mode_allows_pre_replay_satisfied_receipt(
    tmp_path: Path,
) -> None:
    card = _write_strategy_card(tmp_path)
    receipt = {
        "failure_family_sha": card["failure_family_sha"],
        "outcome": "satisfied",
        "evidence_refs": ["workspace/submissions/iter_001.py"],
    }

    result = evaluate_strategy_card_gate(
        project_dir=tmp_path,
        thesis_text=f"STRATEGY_CARD_DISCHARGE = {receipt!r}",
        candidate_source="",
        semantic_status=False,
    )

    assert result.passed is True


def test_strategy_card_gate_rejects_satisfied_receipt_for_wrong_gate_status(
    tmp_path: Path,
) -> None:
    card = _write_strategy_card(tmp_path)
    receipt = {
        "failure_family_sha": card["failure_family_sha"],
        "outcome": "satisfied",
        "observed_status": "fresh_same_lineage_replay_receipt",
        "evidence_refs": ["workspace/submissions/candidate.py"],
    }

    result = evaluate_strategy_card_gate(
        project_dir=tmp_path,
        thesis_text=f"STRATEGY_CARD_DISCHARGE = {receipt!r}",
        candidate_source="",
    )

    assert result.passed is False
    assert (
        result.payload["invalid"][0]["reason"]
        == "satisfied_receipt_mismatches_required_gate"
    )
