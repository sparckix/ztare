from __future__ import annotations

import json
from pathlib import Path

from ztare.validator.autoresearch_prediction_contract import (
    score_prediction_row,
    summarize_prediction_contracts,
    validate_prediction_row,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_prediction_contract_summary_scores_resolved_rows(tmp_path: Path) -> None:
    project = tmp_path / "projects" / "demo"
    workspace = project / "workspace"
    _write_jsonl(
        workspace / "iteration_predictions.jsonl",
        [
            {
                "prediction_id": "P-001",
                "predicted_at": "2026-06-19T00:00:00Z",
                "predictor": "rd",
                "iteration": 2,
                "event": "iteration score improves",
                "p_success": 0.8,
                "horizon": "next iteration",
                "resolution_rule": "actual_success is true if score improves",
                "tier": 2,
                "sealed_at": "2026-06-19T00:00:01Z",
                "sealed_inputs_sha256": "a" * 64,
                "provenance": {
                    "source_surface": "scratch_contract",
                    "mode": "out_of_loop",
                    "producer": "codex:rd",
                },
                "resolved_at": "2026-06-19T00:05:00Z",
                "actual_success": True,
            },
            {
                "prediction_id": "P-002",
                "predicted_at": "2026-06-19T00:10:00Z",
                "predictor": "rd",
                "iteration": 3,
                "event": "evidence gap closes",
                "p_success": 0.4,
                "horizon": "next iteration",
                "resolution_rule": "actual_success is true if no active evidence gaps remain",
                "tier": 2,
                "sealed_at": "2026-06-19T00:10:01Z",
                "source_context_sha256": "b" * 64,
            },
        ],
    )

    summary = summarize_prediction_contracts(
        project_dir=project,
        workspace_dir=workspace,
        repo=tmp_path,
    )

    assert summary["available"] is True
    assert summary["status"] == "scoreable_measurement_lane"
    assert summary["source_artifact"] == "projects/demo/workspace/iteration_predictions.jsonl"
    assert summary["row_count"] == 2
    assert summary["valid_count"] == 2
    assert summary["invalid_count"] == 0
    assert summary["sealed_count"] == 2
    assert summary["resolved_count"] == 1
    assert summary["unresolved_count"] == 1
    assert summary["scoreable_count"] == 1
    assert summary["mean_brier"] == 0.04
    assert summary["mean_uniform_brier"] == 0.25
    assert summary["beats_uniform_baseline"] is True
    assert summary["measurement_policy"] == "score_only_no_routing"
    assert summary["source_surfaces"] == {
        "autoresearch_workspace": 1,
        "scratch_contract": 1,
    }
    assert summary["provenance_modes"] == {
        "in_loop": 1,
        "out_of_loop": 1,
    }
    assert summary["producers"] == {
        "autoresearch_loop": 1,
        "codex:rd": 1,
    }
    assert summary["certified_count"] == 0
    assert summary["excluded_from_calibration_count"] == 0
    assert summary["membrane_eligible_count"] == 0
    assert summary["authority"] == {
        "score_authority": "scoreable_binary_brier_rows",
        "calibration_authority": "not_calibration_authority",
        "membrane_authority": "not_membrane_evidence",
        "routing_authority": "none_trace_does_not_route_work",
        "decision_use_required_for_routing": True,
    }
    assert summary["issues"] == []


def test_prediction_contract_validation_rejects_bad_probability() -> None:
    issues = validate_prediction_row(
        {
            "prediction_id": "P-bad",
            "predicted_at": "2026-06-19T00:00:00Z",
            "predictor": "rd",
            "iteration": 1,
            "event": "score improves",
            "p_success": 1.3,
            "horizon": "next iteration",
            "resolution_rule": "actual_success",
            "tier": 2,
        }
    )

    by_code = {issue.code for issue in issues}
    assert "invalid_probability" in by_code
    assert "unsealed_prediction" in by_code


def test_autoresearch_rows_cannot_self_promote_to_membrane_evidence(tmp_path: Path) -> None:
    project = tmp_path / "projects" / "demo"
    workspace = project / "workspace"
    _write_jsonl(
        workspace / "iteration_predictions.jsonl",
        [
            {
                "prediction_id": "P-self-promoted",
                "predicted_at": "2026-06-19T00:00:00Z",
                "predictor": "autoresearch_loop",
                "event": "iteration score improves",
                "p_success": 0.8,
                "horizon": "next iteration",
                "resolution_rule": "actual_success iff score improves",
                "tier": 2,
                "sealed_at": "2026-06-19T00:00:01Z",
                "sealed_inputs_sha256": "a" * 64,
                "resolved_at": "2026-06-19T00:05:00Z",
                "actual_success": True,
                "certified": True,
                "can_satisfy_membrane": True,
            }
        ],
    )

    summary = summarize_prediction_contracts(
        project_dir=project,
        workspace_dir=workspace,
        repo=tmp_path,
    )

    assert summary["status"] == "needs_attention"
    assert summary["valid_count"] == 0
    assert summary["scoreable_count"] == 0
    assert summary["certified_count"] == 0
    assert summary["membrane_eligible_count"] == 0
    assert summary["authority"] == {
        "score_authority": "not_scoreable_yet",
        "calibration_authority": "not_calibration_authority",
        "membrane_authority": "not_membrane_evidence",
        "routing_authority": "none_trace_does_not_route_work",
        "decision_use_required_for_routing": True,
    }
    assert {issue["code"] for issue in summary["issues"]} == {
        "invalid_certification_claim",
        "invalid_membrane_claim",
    }


def test_prediction_row_score_accepts_string_outcomes() -> None:
    score = score_prediction_row(
        {
            "prediction_id": "P-003",
            "p_success": 0.1,
            "actual_outcome": "failure",
        }
    )

    assert score == {
        "prediction_id": "P-003",
        "p_success": 0.1,
        "actual_success": False,
        "brier": 0.010000000000000002,
        "uniform_brier": 0.25,
    }


def test_autoresearch_summary_rejects_posthoc_prediction_rows(tmp_path: Path) -> None:
    project = tmp_path / "projects" / "demo"
    workspace = project / "workspace"
    _write_jsonl(
        workspace / "iteration_predictions.jsonl",
        [
            {
                "prediction_id": "P-posthoc",
                "predicted_at": "2026-06-19T00:05:00Z",
                "predictor": "autoresearch_loop",
                "event": "iteration score improves",
                "p_success": 0.8,
                "horizon": "next iteration",
                "resolution_rule": "actual_success iff score improves",
                "tier": 2,
                "sealed_at": "2026-06-19T00:05:01Z",
                "sealed_inputs_sha256": "a" * 64,
                "resolved_at": "2026-06-19T00:05:00Z",
                "actual_success": True,
            }
        ],
    )

    summary = summarize_prediction_contracts(
        project_dir=project,
        workspace_dir=workspace,
        repo=tmp_path,
    )

    assert summary["status"] == "needs_attention"
    assert summary["valid_count"] == 0
    assert summary["scoreable_count"] == 0
    assert {issue["code"] for issue in summary["issues"]} == {
        "noncausal_resolution_order",
        "noncausal_seal_resolution_order",
    }
