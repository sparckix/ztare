from __future__ import annotations

import json
from pathlib import Path

from ztare.reports.mechanism_consequence_audit import (
    audit_mechanism_consequences,
    render_text,
)


def _write(path: Path, text: str = "{}\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _row_by_id(report: dict, mechanism_id: str) -> dict:
    return next(row for row in report["rows"] if row["mechanism_id"] == mechanism_id)


def test_audit_classifies_observed_and_unobserved_mechanisms(tmp_path):
    _write(
        tmp_path / "analytics/public/queries/rd/autoresearch_routes/decision_demo.json",
        json.dumps({"decision": "invoke_autoresearch"}) + "\n",
    )
    workspace = tmp_path / "projects/demo/workspace"
    _write(workspace / "iteration_telemetry.jsonl", '{"record_type":"iteration"}\n')
    _write(
        workspace / "latest_mutation_declaration.json",
        json.dumps({"candidate_id": "fixture_candidate", "contract": "mutation_contract"}) + "\n",
    )
    _write(workspace / "latest_eval_results.json")

    report = audit_mechanism_consequences(repo=tmp_path, project="demo")

    assert report["summary"]["intrinsic_decorative_count"] == 0
    assert report["summary"]["consequence_counts"]["block"] >= 1
    assert _row_by_id(report, "workbench_router")["evidence_status"] == "observed"
    mutation = _row_by_id(report, "mutation_r1_contract")
    assert mutation["evidence_status"] == "observed"
    assert mutation["usable_evidence_count"] >= 1
    assert "projects/demo/workspace/latest_mutation_declaration.json" in mutation["evidence_paths"]
    parallel = _row_by_id(report, "parallel_blitz")
    assert parallel["evidence_status"] == "not_triggered"
    assert "parallel_mutator_k=1" in parallel["activation_hint"]


def test_parallel_blitz_unobserved_when_rubric_trigger_fires_without_evidence(tmp_path):
    _write(
        tmp_path / "rubrics/demo.json",
        json.dumps(
            {
                "rubric_mode": "calibration",
                "parallel_mutator_k": 3,
                "parallel_mutator_force": True,
            }
        )
        + "\n",
    )
    (tmp_path / "projects/demo/workspace").mkdir(parents=True, exist_ok=True)

    report = audit_mechanism_consequences(repo=tmp_path, project="demo")

    assert _row_by_id(report, "parallel_blitz")["evidence_status"] == "unobserved_in_scope"


def test_primitive_class_rotation_not_triggered_without_candidate_declaration(tmp_path):
    _write(
        tmp_path / "rubrics/demo.json",
        json.dumps({"enable_primitive_class_rotation": True}) + "\n",
    )
    _write(
        tmp_path / "projects/demo/workspace/submissions/iter_001.md",
        "ordinary candidate without a structural class declaration\n",
    )

    report = audit_mechanism_consequences(repo=tmp_path, project="demo")

    row = _row_by_id(report, "primitive_class_rotation")
    assert row["evidence_status"] == "not_triggered"
    assert "no candidate declared a primitive-class move" in row["activation_hint"]


def test_primitive_class_rotation_unobserved_when_candidate_declaration_has_no_ledger(
    tmp_path,
):
    _write(
        tmp_path / "rubrics/demo.json",
        json.dumps({"enable_primitive_class_rotation": True}) + "\n",
    )
    _write(
        tmp_path / "projects/demo/workspace/submissions/iter_001.md",
        "## Scaling Law: sparse tail curve\n",
    )

    report = audit_mechanism_consequences(repo=tmp_path, project="demo")

    row = _row_by_id(report, "primitive_class_rotation")
    assert row["evidence_status"] == "unobserved_in_scope"
    assert row["activation_hint"] == ""


def test_control_followup_policy_tracks_typed_policy_log(tmp_path):
    _write(
        tmp_path / "rubrics/demo.json",
        json.dumps({"control_followup_window": 3}) + "\n",
    )
    _write(
        tmp_path / "projects/demo/workspace/control_followup_policy.jsonl",
        json.dumps(
            {
                "record_type": "control_followup_policy_decision",
                "decision": "observe_prior_control_followup",
                "allowed": False,
            }
        )
        + "\n",
    )

    report = audit_mechanism_consequences(repo=tmp_path, project="demo")

    row = _row_by_id(report, "control_followup_policy")
    assert row["evidence_status"] == "observed"
    assert row["usable_evidence_count"] == 1
    assert row["evidence_paths"] == (
        "projects/demo/workspace/control_followup_policy.jsonl",
    )


def test_control_followup_policy_not_triggered_when_disabled(tmp_path):
    _write(
        tmp_path / "rubrics/demo.json",
        json.dumps({"control_followup_window": 0}) + "\n",
    )
    (tmp_path / "projects/demo/workspace").mkdir(parents=True, exist_ok=True)

    report = audit_mechanism_consequences(repo=tmp_path, project="demo")

    row = _row_by_id(report, "control_followup_policy")
    assert row["evidence_status"] == "not_triggered"
    assert "no eligible recent pivot/blitz control" in row["activation_hint"]


def test_control_followup_policy_not_triggered_without_prior_control(tmp_path):
    _write(
        tmp_path / "rubrics/demo.json",
        json.dumps({"control_followup_window": 3}) + "\n",
    )
    _write(
        tmp_path / "projects/demo/workspace/iteration_telemetry.jsonl",
        json.dumps(
            {
                "record_type": "iteration",
                "iteration_index": 2,
                "loop_control_action": "normal",
                "stagnation_count": 2,
            }
        )
        + "\n",
    )

    report = audit_mechanism_consequences(repo=tmp_path, project="demo")

    row = _row_by_id(report, "control_followup_policy")
    assert row["evidence_status"] == "not_triggered"
    assert "no eligible recent pivot/blitz control" in row["activation_hint"]


def test_control_followup_policy_unobserved_after_prior_control_without_log(tmp_path):
    _write(
        tmp_path / "rubrics/demo.json",
        json.dumps({"control_followup_window": 3}) + "\n",
    )
    _write(
        tmp_path / "projects/demo/workspace/iteration_telemetry.jsonl",
        json.dumps(
            {
                "record_type": "iteration",
                "iteration_index": 2,
                "loop_control_action": "stagnation_pivot",
                "stagnation_count": 3,
            }
        )
        + "\n",
    )

    report = audit_mechanism_consequences(repo=tmp_path, project="demo")

    assert _row_by_id(report, "control_followup_policy")["evidence_status"] == "unobserved_in_scope"


def test_subscription_dispatch_requires_dispatch_evidence_not_route_only(tmp_path):
    _write(
        tmp_path / "analytics/public/queries/rd/autoresearch_routes/decision_demo.json",
        json.dumps({"decision": "invoke_autoresearch", "recommended_transport": "subscription_cli"})
        + "\n",
    )

    report = audit_mechanism_consequences(repo=tmp_path)

    route = _row_by_id(report, "workbench_router")
    dispatch = _row_by_id(report, "subscription_dispatch")
    assert route["evidence_status"] == "observed"
    assert dispatch["evidence_status"] == "unobserved_in_scope"
    assert dispatch["evidence_count"] == 0


def test_subscription_dispatch_observed_with_dispatch_parity_artifact(tmp_path):
    _write(
        tmp_path
        / "docs/internal/repo_audits/autoresearch_dispatch_parity_live_codex_2026_06_12.json",
        json.dumps({"status": "ok", "transport": "subscription_cli"}) + "\n",
    )

    report = audit_mechanism_consequences(repo=tmp_path)

    row = _row_by_id(report, "subscription_dispatch")
    assert row["evidence_status"] == "observed"
    assert row["usable_evidence_count"] == 1
    assert row["evidence_paths"] == (
        "docs/internal/repo_audits/autoresearch_dispatch_parity_live_codex_2026_06_12.json",
    )


def test_audit_distinguishes_placeholder_only_evidence(tmp_path):
    _write(tmp_path / "analytics/public/queries/rd_pattern_action_contract.json")

    report = audit_mechanism_consequences(repo=tmp_path)

    row = _row_by_id(report, "pattern_action_contract")
    assert row["evidence_status"] == "placeholder_only"
    assert row["evidence_count"] == 1
    assert row["usable_evidence_count"] == 0
    assert row["placeholder_evidence_count"] == 1
    assert row["evidence_paths"] == ()
    assert row["placeholder_evidence_paths"] == (
        "analytics/public/queries/rd_pattern_action_contract.json",
    )
    assert report["summary"]["placeholder_only_count"] >= 1


def test_workspace_scope_strips_duplicate_workspace_prefix(tmp_path):
    workspace = tmp_path / "projects/demo/workspace"
    _write(
        workspace / "latest_information_yield.json",
        json.dumps({"decision": "pivot", "rationale": "fixture"}) + "\n",
    )

    report = audit_mechanism_consequences(repo=tmp_path, workspace=workspace)

    tried_failed = _row_by_id(report, "tried_failed_digest")
    assert tried_failed["evidence_status"] == "observed"
    assert tried_failed["evidence_paths"] == (
        "projects/demo/workspace/latest_information_yield.json",
    )


def test_eigenquestion_preflight_requires_proposal_not_charter_only(tmp_path):
    project = tmp_path / "projects/demo"
    _write(project / "project_charter.md", "## Eigenquestion\n\nold\n")

    report = audit_mechanism_consequences(repo=tmp_path, project="demo")

    row = _row_by_id(report, "eigenquestion_preflight")
    assert row["evidence_status"] == "not_triggered"
    assert row["evidence_count"] == 0
    assert "no proposed_eigenquestion" in row["activation_hint"]


def test_eigenquestion_preflight_observed_when_proposal_exists(tmp_path):
    project = tmp_path / "projects/demo"
    _write(project / "project_charter.md", "## Eigenquestion\n\nold\n")
    _write(project / "proposed_eigenquestion_20260613T000000Z.md", "# Proposed\n\nnew\n")

    report = audit_mechanism_consequences(repo=tmp_path, project="demo")

    row = _row_by_id(report, "eigenquestion_preflight")
    assert row["evidence_status"] == "observed"
    assert row["usable_evidence_count"] == 1
    assert row["evidence_paths"] == (
        "projects/demo/proposed_eigenquestion_20260613T000000Z.md",
    )


def test_render_text_names_consequence_and_counterfactual(tmp_path):
    _write(tmp_path / "analytics/public/index/architecture_index.jsonl", "{}\n")

    report = audit_mechanism_consequences(repo=tmp_path)
    rendered = render_text(report)

    assert "Autoresearch mechanism consequence audit" in rendered
    assert (
        "primitive_amnesia "
        "[route/observed/artifact_present_unverified/risk=medium]"
    ) in rendered
    assert "evidence_quality=" in rendered
    assert "placeholders=" in rendered
    assert "prevents=" in rendered
    assert "activation=" in rendered
