from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ztare.common.harness_weakness import (
    append_weakness_classifier_row,
    build_harness_weakness_receipt,
    classify_harness_weakness,
    write_harness_weakness_receipt,
    write_lowerability_harness_weakness_receipt,
    _load_ledger_weakness_classifiers,
    _validate_predicate_spec,
)
from ztare.research_director import strategy_office as so


def test_seed_registry_matches_existing_branch_behavior(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    workspace = project / "workspace"
    workspace.mkdir()
    (workspace / "strategy_experiments.jsonl").write_text(
        json.dumps(
            {
                "failure_family": "gate",
                "action_plan": {"required_next_gate": {"command": "run_declared_strategy_gate"}},
                "disposition": "open",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    cases = [
        (
            {
                "candidate_relation": "hard_gate_failure",
                "quotient_comparison": {"relation": "hard_gate_failure_without_visible_quotient"},
                "best_prior_submission": "workspace/submissions/base.py",
            },
            {"first_mismatch": "", "checked_rows": 24, "exact_rows": 24, "wrong_cell_count": 0, "failed_gates": ["holdout transfer failure"]},
            ("boundary_evidence_missing", "run_or_return_substrate_boundary_gate"),
        ),
        (
            {
                "candidate_relation": "hard_gate_failure",
                "quotient_comparison": {
                    "relation": "changed_support",
                    "candidate_top_quotient": {"bbox": [1, 2, 3, 4], "first_row": 1},
                    "best_prior_top_quotient": {"bbox": [1, 2, 3, 4], "first_row": 2},
                },
            },
            {"first_mismatch": "trace", "checked_rows": 1, "exact_rows": 1, "wrong_cell_count": 0},
            ("unquotiented_counterexample_chart_missing", "request_counterexample_context_then_refine_abstraction"),
        ),
        (
            {
                "candidate_relation": "hard_gate_failure",
                "quotient_comparison": {"relation": "changed_support"},
            },
            {"first_mismatch": "trace", "checked_rows": 1, "exact_rows": 1, "wrong_cell_count": 0},
            ("visible_counterexample_trace_unfactored", "inspect_visible_regression_trace_then_refine_or_propose_capability"),
        ),
        (
            {
                "candidate_relation": "hard_gate_failure",
                "quotient_comparison": {"relation": "hard_gate_failure_without_visible_quotient"},
            },
            {"first_mismatch": "", "checked_rows": 1, "exact_rows": 1, "wrong_cell_count": 0},
            ("declared_gate_obligation_open", "run_declared_strategy_gate_before_new_visible_probe"),
        ),
        (
            {
                "candidate_relation": "candidate_quality_failure",
                "best_prior_submission": "workspace/other/base.py",
            },
            {"first_mismatch": "", "checked_rows": 1, "exact_rows": 1, "wrong_cell_count": 0},
            ("mutable_prior_identity_leak", "select_immutable_content_addressed_prior"),
        ),
        (
            {
                "candidate_relation": "candidate_quality_failure",
                "quotient_comparison": {"relation": "changed_support"},
                "candidate_exact_rows": 4,
                "best_prior_exact_rows": 7,
            },
            {"first_mismatch": "", "checked_rows": 1, "exact_rows": 1, "wrong_cell_count": 0},
            ("local_receipt_overgeneralized", "request_counterexample_context_then_factor_delta_by_residual_quotient"),
        ),
        (
            {
                "candidate_relation": "candidate_quality_failure",
                "quotient_comparison": {"relation": "same_support_changed_pairs"},
                "candidate_exact_rows": 3,
                "best_prior_exact_rows": 5,
            },
            {"first_mismatch": "", "checked_rows": 1, "exact_rows": 1, "wrong_cell_count": 0},
            ("quotient_context_missing", "request_counterexample_context_then_separate_same_support_cases"),
        ),
        (
            {
                "candidate_relation": "no_strict_improvement",
            },
            {"first_mismatch": "", "checked_rows": 1, "exact_rows": 1, "wrong_cell_count": 0},
            ("plateau_without_information_gain", "request_discriminator_or_capability_proposal"),
        ),
    ]

    for regression_receipt, trace, expected in cases:
        out = classify_harness_weakness(
            project_dir=project,
            regression_receipt=regression_receipt,
            counterexample_trace=trace,
        )
        assert (out["class_name"], out["route"]) == expected

    fallback = classify_harness_weakness(
        project_dir=project,
        regression_receipt={"candidate_relation": "something_else"},
        counterexample_trace={"first_mismatch": "", "checked_rows": 1, "exact_rows": 1, "wrong_cell_count": 0},
    )
    assert fallback["class_name"] == "unclassifiable_carrier_or_gate_failure"
    assert fallback["route"] == "repair_carrier_contract_or_request_workbench_capability"


def test_regressed_candidate_routes_workbench_to_best_prior_frontier(tmp_path: Path) -> None:
    project = tmp_path / "project"
    submissions = project / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    prior = submissions / "prior.py"
    prior.write_text("def step(grid, action, t):\n    return grid\n", encoding="utf-8")
    episode = project / "raw" / "episodes" / "episode_001.jsonl"
    episode.parent.mkdir(parents=True)
    episode.write_text('{"state":[[0]],"action":0,"next_state":[[0]],"t":0}\n')
    (project / "workspace" / "candidate_memory.json").write_text(
        json.dumps(
            {
                "schema": "ztare-candidate-memory-v1",
                "records": [
                    {
                        "source_type": "deterministic_near_miss",
                        "submission": "workspace/submissions/prior.py",
                        "sha": "prior-sha",
                        "visible_exact_rows": 10,
                        "visible_checked_rows": 11,
                        "counterexample_trace": {
                            "first_mismatch": "prior residual t=71 action=0",
                            "evidence_ref": "raw/episodes/episode_001.jsonl",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    regression = {
        "candidate_relation": "regression",
        "candidate_sha": "failed-sha",
        "candidate_exact_rows": 4,
        "best_prior_sha": "prior-sha",
        "best_prior_exact_rows": 10,
        "best_prior_submission": "workspace/submissions/prior.py",
        "quotient_comparison": {"relation": "changed_support"},
    }
    receipt = build_harness_weakness_receipt(
        project_dir=project,
        source_ref="latest_eval_results.json:pre_judge_gate_block",
        regression_receipt=regression,
        counterexample_trace={"first_mismatch": "failed candidate residual"},
    )

    assert receipt["active_frontier"]["role"] == "best_admissible_prior"
    assert receipt["active_frontier"]["first_mismatch"] == "prior residual t=71 action=0"
    task = receipt["workbench_task"]
    assert task["source_ref"] == "workspace/submissions/prior.py"
    assert task["first_counterexample"] == "prior residual t=71 action=0"
    assert "raw/episodes/episode_001.jsonl" in task["visible_artifact_refs"]
    assert len(task["evidence_epoch_sha256"]) == 64
    episode.write_text(episode.read_text() + '{"state":[[1]],"action":0,"next_state":[[1]],"t":1}\n')
    successor = build_harness_weakness_receipt(
        project_dir=project,
        source_ref="latest_eval_results.json:pre_judge_gate_block",
        regression_receipt=regression,
        counterexample_trace={"first_mismatch": "failed candidate residual"},
    )
    assert successor["workbench_task"]["task_id"] != task["task_id"]


def test_frontier_task_carries_full_artifact_identity_from_legacy_display_sha(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    submissions = project / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    prior = submissions / "prior.py"
    prior.write_text("def step(state, action):\n    return state\n", encoding="utf-8")
    full_sha = hashlib.sha256(prior.read_bytes()).hexdigest()
    (project / "workspace" / "candidate_memory.json").write_text(
        json.dumps(
            {
                "schema": "ztare-candidate-memory-v1",
                "records": [
                    {
                        "source_type": "deterministic_near_miss",
                        "submission": "workspace/submissions/prior.py",
                        "sha": full_sha[:12],
                        "visible_exact_rows": 10,
                        "visible_checked_rows": 11,
                        "counterexample_trace": {
                            "first_mismatch": "prior residual",
                            "evidence_ref": "raw/episodes/episode_001.jsonl",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    receipt = build_harness_weakness_receipt(
        project_dir=project,
        source_ref="latest_eval_results.json:pre_judge_gate_block",
        regression_receipt={
            "candidate_relation": "regression",
            "candidate_sha": "f" * 64,
            "candidate_exact_rows": 4,
            "best_prior_sha": full_sha[:12],
            "best_prior_exact_rows": 10,
            "best_prior_submission": "workspace/submissions/prior.py",
            "quotient_comparison": {"relation": "same_support_changed_pairs"},
        },
        counterexample_trace={"first_mismatch": "failed proposal"},
    )

    assert receipt["active_frontier"]["candidate_sha"] == full_sha
    assert receipt["workbench_task"]["source_sha256"] == full_sha


def test_gate_trace_preserves_candidate_identity_and_selects_typed_context(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    receipt = build_harness_weakness_receipt(
        project_dir=project,
        source_ref="latest_eval_results.json:pre_judge_gate_block",
        regression_receipt={
            "schema": "ztare-pre-judge-block-v1",
            "gated_file": "workspace/submissions/candidate.py",
            "gated_sha256": "candidate-sha",
        },
        counterexample_trace={
            "gated_file": "workspace/submissions/candidate.py",
            "gated_sha256": "candidate-sha",
            "failed_gates": ["visible_replay_exact"],
            "first_mismatch": "typed transition witness",
            "evidence_ref": "raw/episodes/episode_001.jsonl",
            "mismatch_classes": [
                {
                    "first_row": 7,
                    "t": 3,
                    "action": "advance",
                    "signature": {"bbox": [1, 2, 3, 4]},
                }
            ],
        },
    )

    assert receipt["candidate_sha"] == "candidate-sha"
    assert receipt["active_frontier"]["candidate_sha"] == "candidate-sha"
    assert receipt["weakness_class"] == "unquotiented_counterexample_chart_missing"
    assert receipt["recommended_capability_id"] == "inspect_worldmodel_counterexample_context"
    assert receipt["workbench_task"]["source_ref"] == "workspace/submissions/candidate.py"
    assert receipt["workbench_task"]["admissible_capability_ids"] == [
        "inspect_worldmodel_counterexample_context",
        "mine_worldmodel_lowerable_selectors",
    ]
    assert receipt["workbench_task"]["morphism_sequence"] == [
        "inspect_worldmodel_counterexample_context",
        "mine_worldmodel_lowerable_selectors",
    ]
    assert receipt["workbench_task"]["obligation_id"] == receipt["workbench_task"]["task_id"]
    assert len(receipt["workbench_task"]["program_id"]) == 64


def test_weakness_writer_refreshes_one_task_epoch_row(tmp_path: Path) -> None:
    project = tmp_path / "project"
    episode = project / "raw" / "episodes" / "episode_001.jsonl"
    episode.parent.mkdir(parents=True)
    episode.write_text('{"state":[[0]],"action":0,"next_state":[[0]],"t":0}\n')
    regression = {
        "candidate_relation": "hard_gate_failure",
        "gated_file": "workspace/submissions/candidate.py",
        "gated_sha256": "candidate-sha",
    }
    trace = {
        "gated_file": "workspace/submissions/candidate.py",
        "gated_sha256": "candidate-sha",
        "failed_gates": ["visible_replay_exact"],
        "first_mismatch": "same typed witness",
    }

    first = write_harness_weakness_receipt(
        project_dir=project,
        source_ref="latest_eval_results.json:pre_judge_gate_block",
        regression_receipt=regression,
        counterexample_trace=trace,
    )
    second = write_harness_weakness_receipt(
        project_dir=project,
        source_ref="latest_eval_results.json:pre_judge_gate_block",
        regression_receipt=regression,
        counterexample_trace=trace,
    )

    rows = [
        json.loads(line)
        for line in (project / "workspace" / "harness_weakness_receipts.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert first["workbench_task"]["task_id"] == second["workbench_task"]["task_id"]
    assert len(rows) == 1
    assert rows[0]["occurrence_count"] == 2
    assert rows[0]["first_seen_at_utc"] == first["first_seen_at_utc"]
    assert rows[0]["last_seen_at_utc"] == second["last_seen_at_utc"]

    episode.write_text(episode.read_text() + '{"state":[[1]],"action":0,"next_state":[[1]],"t":1}\n')
    successor = write_harness_weakness_receipt(
        project_dir=project,
        source_ref="latest_eval_results.json:pre_judge_gate_block",
        regression_receipt=regression,
        counterexample_trace=trace,
    )
    assert successor["workbench_task"]["evidence_epoch_sha256"] != second["workbench_task"]["evidence_epoch_sha256"]
    assert len(
        (project / "workspace" / "harness_weakness_receipts.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ) == 2


def test_lowerability_weakness_uses_same_convergence_door(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    blocker = {
        "visible_command_errors": [
            {"capability_id": "probe", "error": "instrument unavailable"}
        ]
    }

    first = write_lowerability_harness_weakness_receipt(
        project_dir=project,
        blocker_payload=blocker,
    )
    second = write_lowerability_harness_weakness_receipt(
        project_dir=project,
        blocker_payload=blocker,
    )

    assert first is not None and second is not None
    assert first["workbench_task"]["task_id"] == second["workbench_task"]["task_id"]
    rows = (project / "workspace" / "harness_weakness_receipts.jsonl").read_text().splitlines()
    assert len(rows) == 1
    assert json.loads(rows[0])["occurrence_count"] == 2


def test_ledger_grown_entry_is_loaded_before_terminal(tmp_path: Path) -> None:
    project = tmp_path / "project"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "strategy_experiments.jsonl").write_text(
        json.dumps(
            {
                "failure_family": "gate",
                "action_plan": {"required_next_gate": {"command": "run_declared_strategy_gate"}},
                "disposition": "open",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    row = {
        "class_name": "novel_geometry_classifier",
        "predicate_spec": {"field": "geometry_kind", "relation": "eq", "value": "novel_geometry"},
        "route": "inspect_novel_geometry_then_refine",
        "provenance": "office",
            "admissibility": {
                "schema": "ztare-kernel-change-admissibility-v1",
                "change_class": "provenance",
                "math_anchors": ["content_addressed_provenance", "raw_gate_authority"],
                "raw_evidence_refs": ["workspace/seed.jsonl"],
                "verification_refs": ["validate_kernel_change_admissibility"],
                "preserves_raw_fiber": True,
                "raw_gates_unchanged": True,
                "candidate_promotion_authority": False,
                "introduces_substrate_specific_rule": False,
                "content_addressed_refs": ["workspace/seed.jsonl"],
            },
        }
    (workspace / "weakness_classifiers.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

    registry = _load_ledger_weakness_classifiers(project)
    assert registry and registry[0]["class_name"] == "novel_geometry_classifier"

    out = classify_harness_weakness(
        project_dir=project,
        regression_receipt={"candidate_relation": "candidate_quality_failure", "geometry_kind": "novel_geometry"},
        counterexample_trace={"first_mismatch": "", "checked_rows": 1, "exact_rows": 1, "wrong_cell_count": 0},
    )
    assert out["class_name"] == "novel_geometry_classifier"
    assert out["route"] == "inspect_novel_geometry_then_refine"


def test_invalid_predicate_spec_is_rejected(tmp_path: Path) -> None:
    project = tmp_path / "project"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)

    admissibility = {
        "schema": "ztare-kernel-change-admissibility-v1",
        "change_class": "provenance",
        "math_anchors": ["content_addressed_provenance", "raw_gate_authority"],
        "raw_evidence_refs": ["workspace/seed.jsonl"],
        "verification_refs": ["validate_kernel_change_admissibility"],
        "preserves_raw_fiber": True,
        "raw_gates_unchanged": True,
        "candidate_promotion_authority": False,
        "introduces_substrate_specific_rule": False,
        "content_addressed_refs": ["workspace/seed.jsonl"],
    }
    with pytest.raises(ValueError):
        append_weakness_classifier_row(
            project_dir=project,
            class_name="bad",
            predicate_spec={"field": "geometry_kind", "relation": "regex", "value": ".*"},
            route="inspect",
            admissibility_receipt=admissibility,
    )
    assert _validate_predicate_spec({"field": "geometry_kind", "relation": "regex", "value": ".*"}) is False


def test_approved_weakness_classifier_proposal_appends_overlay_row(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)

    ledger = workspace / "leaf_proposals.jsonl"
    proposal = {
        "kind": "weakness_classifier",
        "proposed_change": {
            "class_name": "novel_geometry_classifier",
            "predicate_spec": {"field": "geometry_kind", "relation": "eq", "value": "novel_geometry"},
            "route": "inspect_novel_geometry_then_refine",
        },
        "expected_number_moved": {},
        "certifier_touched": False,
    }
    ledger.write_text(
        json.dumps({"proposal": proposal, "proposal_signature": "sig", "disposition": "open"}) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(so, "_sealed_leaf_adjudicator", lambda *_: (lambda *_a, **_k: {"accepted": True, "rule_citations": ["Rule 2"], "reason": "classifier tightens weakness routing"}))
    monkeypatch.setattr(so, "_sealed_leaf_dissent_adjudicator", lambda *_: (lambda *_a, **_k: {"accepted": True, "rule_citations": [], "reason": "no dissent: counter-case fails"}))
    receipt = so.adjudicate_leaf_proposals(project, sealed_leaf_model="gpt-4o", judge_model="gpt-4o", mutator_model="claude-3.5")

    assert receipt["approved"] == 1
    rows = [json.loads(line) for line in (workspace / "weakness_classifiers.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows[0]["class_name"] == "novel_geometry_classifier"
    assert rows[0]["predicate_spec"]["field"] == "geometry_kind"
