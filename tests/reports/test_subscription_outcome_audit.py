from __future__ import annotations

import json

from src.ztare.reports.subscription_outcome_audit import (
    audit_subscription_outcomes,
    render_text,
)


def _write_eval_history(project_dir, rows: list[dict]) -> None:
    workspace = project_dir / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "eval_history.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _write_rubric(path, *, mode: str = "kepler", extra: dict | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "rubric_mode": mode,
        "dimensions": [
            {"name": "Correctness", "weight": 100},
        ],
    }
    if extra:
        body.update(extra)
    path.write_text(
        json.dumps(body, sort_keys=True),
        encoding="utf-8",
    )


def test_subscription_outcome_audit_compares_api_and_subscription_rows(tmp_path):
    project = tmp_path / "projects" / "demo"
    _write_eval_history(
        project,
        [
            {
                "iteration": 1,
                "score": 10,
                "weakest_point": "baseline",
                "transport": "api",
                "held_out": {"passed": True},
            },
            {
                "iteration": 2,
                "score": 8,
                "weakest_point": "worse",
                "transport": "subscription_cli",
            },
            {
                "iteration": 3,
                "score": 25,
                "weakest_point": "better",
                "transport": "subscription_cli",
                "held_out": {"passed": True},
            },
        ],
    )

    report = audit_subscription_outcomes(repo=tmp_path, project="demo")

    assert report["status"] == "comparable"
    assert report["ok"] is True
    assert report["summary"]["transport_counts"] == {"api": 1, "subscription_cli": 2}
    assert report["by_transport"]["api"]["admitted_count"] == 1
    assert report["by_transport"]["subscription_cli"]["admitted_count"] == 1
    assert report["by_transport"]["subscription_cli"]["gate_failure_count"] == 0
    assert report["by_transport"]["subscription_cli"]["failed_gate_ids"] == []
    assert report["comparison"]["subscription_minus_api_mean_score"] == 6.5
    assert report["comparison"]["subscription_minus_api_best_score"] == 15.0
    assert "Observational" in report["comparison"]["caveat"]
    assert "status=comparable" in render_text(report)
    assert report["summary"]["matched_run_plan_count"] == 0
    assert report["summary"]["matched_run_group_count"] == 0


def test_subscription_outcome_audit_reports_missing_subscription_evidence(tmp_path):
    project = tmp_path / "projects" / "api_only"
    project.mkdir(parents=True)
    _write_rubric(tmp_path / "rubrics" / "api_only.json")
    _write_eval_history(
        project,
        [
            {
                "iteration": 1,
                "score": 11,
                "weakest_point": "baseline",
                "transport": "api",
            }
        ],
    )

    report = audit_subscription_outcomes(repo=tmp_path, project="api_only")

    assert report["status"] == "insufficient_subscription_evidence"
    assert report["ok"] is False
    assert report["summary"]["api_rows"] == 1
    assert report["summary"]["subscription_rows"] == 0
    assert report["action"].startswith("run a bounded subscription-backed")
    text = render_text(report)
    assert "model_calls=none" in text
    assert report["summary"]["matched_run_plan_count"] == 1
    candidate = report["matched_run_plan"][0]
    assert candidate["project"] == "api_only"
    assert candidate["rubric"] == "api_only"
    assert candidate["matched_run_id"] == "pair_api_only_001"
    assert candidate["matched_pair_command"] == (
        "make autoresearch-matched-transport-pair PROJECT=api_only "
        "RUBRIC=api_only ITERS=1 MATCHED_RUN_ID=pair_api_only_001 "
        "AGENT_TIMEOUT=240"
    )
    assert candidate["api_command"] == (
        "make experiment-loop PROJECT=api_only RUBRIC=api_only ITERS=1 "
        "MATCHED_RUN_ID=pair_api_only_001 MATCHED_RUN_ROLE=api"
    )
    assert "AGENT_MUTATOR=1" in candidate["subscription_command"]
    assert "AGENT_TIMEOUT=240" in candidate["subscription_command"]
    assert "MATCHED_RUN_ID=pair_api_only_001 MATCHED_RUN_ROLE=subscription" in (
        candidate["subscription_command"]
    )
    assert candidate["audit_command"] == (
        "make autoresearch-subscription-outcome-audit PROJECT=api_only JSON=1"
    )
    assert candidate["suitability_score"] > 0
    assert "no_project_test_model" in candidate["risk_flags"]
    assert "  matched-pair: make autoresearch-matched-transport-pair PROJECT=api_only" in text
    assert "  api: make experiment-loop PROJECT=api_only RUBRIC=api_only" in text
    assert "  subscription: make experiment-loop PROJECT=api_only RUBRIC=api_only" in text
    assert "  audit: make autoresearch-subscription-outcome-audit PROJECT=api_only JSON=1" in text
    assert "  caution: Run the pair under the same project/rubric/iteration budget" in text


def test_subscription_outcome_audit_counts_call_site_subscription_metadata(tmp_path):
    project = tmp_path / "projects" / "mixed_worker"
    _write_eval_history(
        project,
        [
            {
                "iteration": 1,
                "score": 10,
                "weakest_point": "api baseline",
                "worker_metadata_by_call_site": {
                    "mutator": {"transport": "api", "worker_capability": "llm"},
                    "judge": {"transport": "api", "worker_capability": "llm"},
                },
            },
            {
                "iteration": 2,
                "score": 12,
                "weakest_point": "subscription judge",
                "worker_metadata_by_call_site": {
                    "mutator": {"transport": "api", "worker_capability": "llm"},
                    "judge": {"transport": "subscription_cli", "worker_capability": "agent"},
                },
            },
        ],
    )

    report = audit_subscription_outcomes(repo=tmp_path, project="mixed_worker")

    assert report["status"] == "comparable"
    assert report["summary"]["transport_counts"] == {"api": 1, "subscription_cli": 1}
    assert report["summary"]["subscription_rows"] == 1


def test_subscription_outcome_audit_surfaces_gate_zeroed_transport_rows(tmp_path):
    project = tmp_path / "projects" / "gate_zeroed"
    _write_eval_history(
        project,
        [
            {
                "iteration": 1,
                "score": 35,
                "transport": "api",
                "matched_run_id": "pair_gate_zeroed",
                "matched_run_role": "api",
            },
            {
                "iteration": 1,
                "score": 0,
                "transport": "subscription_cli",
                "matched_run_id": "pair_gate_zeroed",
                "matched_run_role": "subscription",
                "gate_failure_count": 1,
                "failed_gate_ids": ["global_project_sweep_definitional_tautology"],
                "worker_dispatch_receipts": [
                    {
                        "call_site": "judge",
                        "transport": "subscription_cli",
                        "worker_capability": "agent",
                        "completed": True,
                    }
                ],
            },
        ],
    )

    report = audit_subscription_outcomes(repo=tmp_path, project="gate_zeroed")

    assert report["status"] == "comparable"
    assert report["by_transport"]["subscription_cli"]["gate_failure_count"] == 1
    assert report["by_transport"]["subscription_cli"]["failed_gate_ids"] == [
        "global_project_sweep_definitional_tautology"
    ]
    assert report["matched_run_groups"][0]["evidence_grade"] == "clean"
    assert report["matched_run_groups"][0]["gate_failure_count"] == 1


def test_subscription_outcome_audit_counts_completed_subscription_receipts(tmp_path):
    project = tmp_path / "projects" / "receipt_worker"
    _write_eval_history(
        project,
        [
            {
                "iteration": 1,
                "score": 10,
                "weakest_point": "api baseline",
                "worker_dispatch_receipts": [
                    {
                        "call_site": "mutator",
                        "transport": "api",
                        "worker_capability": "llm",
                        "completed": True,
                    }
                ],
            },
            {
                "iteration": 2,
                "score": 12,
                "weakest_point": "subscription mutator",
                "worker_dispatch_receipts": [
                    {
                        "call_site": "mutator",
                        "transport": "subscription_cli",
                        "worker_capability": "agent",
                        "completed": True,
                    }
                ],
            },
        ],
    )

    report = audit_subscription_outcomes(repo=tmp_path, project="receipt_worker")

    assert report["status"] == "comparable"
    assert report["summary"]["worker_dispatch_receipt_count"] == 2
    assert report["summary"]["completed_subscription_receipt_count"] == 1
    assert report["summary"]["transport_counts"] == {"api": 1, "subscription_cli": 1}


def test_subscription_outcome_audit_reports_stamped_matched_run_groups(tmp_path):
    project = tmp_path / "projects" / "paired"
    _write_eval_history(
        project,
        [
            {
                "iteration": 1,
                "score": 10,
                "transport": "api",
                "matched_run_id": "pair_paired",
                "matched_run_role": "api",
            },
            {
                "iteration": 2,
                "score": 12,
                "transport": "subscription_cli",
                "matched_run_id": "pair_paired",
                "matched_run_role": "subscription",
                "gate_failure_count": 1,
                "failed_gate_ids": ["global_project_sweep_definitional_tautology"],
            },
        ],
    )

    report = audit_subscription_outcomes(repo=tmp_path, project="paired")

    assert report["summary"]["matched_run_group_count"] == 1
    assert report["summary"]["comparable_matched_run_group_count"] == 1
    group = report["matched_run_groups"][0]
    assert group["matched_run_id"] == "pair_paired"
    assert group["transport_counts"] == {"api": 1, "subscription_cli": 1}
    assert group["role_counts"] == {"api": 1, "subscription": 1}
    assert group["comparable"] is True
    assert group["evidence_grade"] == "weak"
    assert group["issue_flags"] == ["missing_completed_subscription_receipt"]
    assert group["completed_subscription_receipt_count"] == 0
    assert group["gate_failure_count"] == 1
    assert group["failed_gate_ids"] == ["global_project_sweep_definitional_tautology"]
    assert "matched_run_group=" in render_text(report)


def test_subscription_outcome_audit_grades_clean_matched_run_group(tmp_path):
    project = tmp_path / "projects" / "paired_clean"
    _write_eval_history(
        project,
        [
            {
                "iteration": 1,
                "score": 10,
                "transport": "api",
                "matched_run_id": "pair_clean",
                "matched_run_role": "api",
                "worker_dispatch_receipts": [
                    {
                        "call_site": "mutator",
                        "transport": "api",
                        "worker_capability": "llm",
                        "completed": True,
                    }
                ],
            },
            {
                "iteration": 2,
                "score": 12,
                "transport": "subscription_cli",
                "matched_run_id": "pair_clean",
                "matched_run_role": "subscription",
                "worker_dispatch_receipts": [
                    {
                        "call_site": "mutator",
                        "transport": "subscription_cli",
                        "worker_capability": "agent",
                        "completed": True,
                    }
                ],
            },
        ],
    )

    report = audit_subscription_outcomes(repo=tmp_path, project="paired_clean")

    assert report["summary"]["clean_matched_run_group_count"] == 1
    assert report["summary"]["weak_matched_run_group_count"] == 0
    group = report["matched_run_groups"][0]
    assert group["evidence_grade"] == "clean"
    assert group["issue_flags"] == []
    assert group["role_transport_mismatch_count"] == 0
    assert group["completed_subscription_receipt_count"] == 1
    assert group["gate_failure_count"] == 0
    assert group["failed_gate_ids"] == []


def test_subscription_outcome_audit_flags_role_transport_mismatch(tmp_path):
    project = tmp_path / "projects" / "paired_mismatch"
    _write_eval_history(
        project,
        [
            {
                "iteration": 1,
                "score": 10,
                "transport": "api",
                "matched_run_id": "pair_mismatch",
                "matched_run_role": "subscription",
            },
            {
                "iteration": 2,
                "score": 12,
                "transport": "subscription_cli",
                "matched_run_id": "pair_mismatch",
                "matched_run_role": "api",
            },
        ],
    )

    report = audit_subscription_outcomes(repo=tmp_path, project="paired_mismatch")

    group = report["matched_run_groups"][0]
    assert group["comparable"] is True
    assert group["evidence_grade"] == "weak"
    assert "role_transport_mismatch" in group["issue_flags"]
    assert group["role_transport_mismatch_count"] == 2


def test_subscription_outcome_audit_plan_avoids_reusing_existing_pair_ids(tmp_path):
    project = tmp_path / "projects" / "repeat_pair"
    project.mkdir(parents=True)
    _write_rubric(tmp_path / "rubrics" / "repeat_pair.json")
    _write_eval_history(
        project,
        [
            {
                "iteration": 1,
                "score": 10,
                "transport": "api",
                "matched_run_id": "pair_repeat_pair_001",
                "matched_run_role": "api",
            },
            {
                "iteration": 2,
                "score": 12,
                "transport": "subscription_cli",
                "matched_run_id": "pair_repeat_pair_001",
                "matched_run_role": "subscription",
            },
        ],
    )

    report = audit_subscription_outcomes(repo=tmp_path, project="repeat_pair")

    candidate = report["matched_run_plan"][0]
    assert candidate["matched_run_id"] == "pair_repeat_pair_002"
    assert "MATCHED_RUN_ID=pair_repeat_pair_002" in candidate["api_command"]
    assert "matched_run_id=pair_repeat_pair_002" in render_text(report)


def test_subscription_outcome_audit_plan_uses_ok_rubrics_only(tmp_path):
    ready = tmp_path / "projects" / "ready_project"
    missing = tmp_path / "projects" / "missing_project"
    ready.mkdir(parents=True)
    missing.mkdir(parents=True)
    _write_rubric(tmp_path / "rubrics" / "ready_project.json")
    _write_rubric(tmp_path / "rubrics" / "missing_project.json", mode="newton")

    report = audit_subscription_outcomes(repo=tmp_path)

    assert report["summary"]["matched_run_plan_count"] == 1
    assert report["matched_run_plan"][0]["project"] == "ready_project"


def test_subscription_outcome_audit_plan_deprioritizes_hard_research_surfaces(tmp_path):
    easy = tmp_path / "projects" / "easy_project"
    hard = tmp_path / "projects" / "ns_proofsearch_project"
    easy.mkdir(parents=True)
    hard.mkdir(parents=True)
    (easy / "test_model.py").write_text("def I_model(x):\n    return x\n", encoding="utf-8")
    (hard / "test_model.py").write_text("def I_model(x):\n    return x\n", encoding="utf-8")
    (hard / "gate_harness.py").write_text("def run():\n    return True\n", encoding="utf-8")
    _write_rubric(tmp_path / "rubrics" / "easy_project.json", mode="kepler")
    _write_rubric(
        tmp_path / "rubrics" / "ns_proofsearch_project.json",
        mode="kepler",
        extra={
            "description": "Navier-Stokes theorem proofsearch surface",
            "holdout_hard_gate": True,
            "pre_judge_gate_harness": True,
        },
    )
    _write_eval_history(easy, [{"iteration": 1, "score": 10}])
    _write_eval_history(
        hard,
        [
            {"iteration": idx, "score": 10 + idx}
            for idx in range(1, 6)
        ],
    )

    report = audit_subscription_outcomes(repo=tmp_path)

    assert report["matched_run_plan"][0]["project"] == "easy_project"
    hard_candidate = next(
        item for item in report["matched_run_plan"] if item["project"] == "ns_proofsearch_project"
    )
    assert "hard_research_or_proof_surface" in hard_candidate["risk_flags"]
    assert "holdout_hard_gate" in hard_candidate["risk_flags"]
    assert "gate_harness_surface" in hard_candidate["risk_flags"]
    assert hard_candidate["suitability_score"] < report["matched_run_plan"][0]["suitability_score"]


def test_subscription_outcome_audit_plan_deprioritizes_existing_clean_pairs(tmp_path):
    evidenced = tmp_path / "projects" / "already_evidenced"
    fresh = tmp_path / "projects" / "fresh_candidate"
    evidenced.mkdir(parents=True)
    fresh.mkdir(parents=True)
    (evidenced / "test_model.py").write_text("def I_model(x):\n    return x\n", encoding="utf-8")
    _write_rubric(tmp_path / "rubrics" / "already_evidenced.json", mode="kepler")
    _write_rubric(tmp_path / "rubrics" / "fresh_candidate.json", mode="kepler")
    _write_eval_history(
        evidenced,
        [
            {
                "iteration": 1,
                "score": 10,
                "transport": "api",
                "matched_run_id": "pair_already_evidenced_001",
                "matched_run_role": "api",
                "worker_dispatch_receipts": [
                    {
                        "call_site": "mutator",
                        "transport": "api",
                        "worker_capability": "llm",
                        "completed": True,
                    }
                ],
            },
            {
                "iteration": 2,
                "score": 12,
                "transport": "subscription_cli",
                "matched_run_id": "pair_already_evidenced_001",
                "matched_run_role": "subscription",
                "worker_dispatch_receipts": [
                    {
                        "call_site": "mutator",
                        "transport": "subscription_cli",
                        "worker_capability": "agent",
                        "completed": True,
                    }
                ],
            },
        ],
    )

    report = audit_subscription_outcomes(repo=tmp_path)

    assert report["matched_run_plan"][0]["project"] == "fresh_candidate"
    evidenced_candidate = next(
        item for item in report["matched_run_plan"] if item["project"] == "already_evidenced"
    )
    assert "existing_clean_matched_group" in evidenced_candidate["risk_flags"]


def test_subscription_outcome_audit_reports_no_history(tmp_path):
    (tmp_path / "projects" / "empty").mkdir(parents=True)

    report = audit_subscription_outcomes(repo=tmp_path, project="empty")

    assert report["status"] == "no_run_history"
    assert report["summary"]["node_count"] == 0
    assert report["skipped_projects"]


def test_subscription_outcome_audit_distinguishes_unrecorded_legacy_rows(tmp_path):
    project = tmp_path / "projects" / "legacy"
    _write_eval_history(
        project,
        [
            {
                "iteration": 1,
                "score": 17,
                "weakest_point": "legacy row before worker metadata",
            }
        ],
    )

    report = audit_subscription_outcomes(repo=tmp_path, project="legacy")

    assert report["status"] == "transport_metadata_missing"
    assert report["summary"]["transport_counts"] == {"unrecorded": 1}
    assert "legacy unrecorded rows" in report["action"]
