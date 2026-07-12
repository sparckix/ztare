from __future__ import annotations

import json
from pathlib import Path

import pytest

from ztare.common.harness_weakness import (
    append_weakness_classifier_row,
    classify_harness_weakness,
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
