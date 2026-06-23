from __future__ import annotations

from ztare.forecasting.prediction_contract import (
    PredictionContractDefaults,
    normalize_prediction_contract,
    score_binary_prediction_contract,
    summarize_prediction_contract_rows,
    validate_prediction_contract,
)


def test_prediction_contract_accepts_forecast_pool_provenance() -> None:
    row = {
        "prediction_id": "FP-001",
        "contract_id": "forecast-demo-contract",
        "forecasted_at": "2026-06-19T00:00:00Z",
        "agent_id": "forecast_pool:aggregate",
        "predicted_at": "2026-06-19T00:00:00Z",
        "predictor": "forecast_pool:aggregate",
        "subject": "autoresearch:demo",
        "event": "next iteration improves score",
        "p_success": 0.7,
        "horizon": "next iteration",
        "resolution_rule": "actual_success if score improves",
        "tier": 2,
        "sealed_at": "2026-06-19T00:00:01Z",
        "source_context_sha256": "f" * 64,
        "provenance": {
            "source_surface": "forecast_pool",
            "mode": "forecast_pool",
            "producer": "forecast_pool:aggregate",
            "certified": True,
            "can_satisfy_membrane": True,
        },
    }

    assert validate_prediction_contract(row) == []
    normalized = normalize_prediction_contract(row)
    assert normalized["provenance"]["source_surface"] == "forecast_pool"
    assert normalized["provenance"]["mode"] == "forecast_pool"
    summary = summarize_prediction_contract_rows([row])
    assert summary["certified_count"] == 1
    assert summary["membrane_eligible_count"] == 0
    assert summary["authority"] == {
        "score_authority": "not_scoreable_yet",
        "calibration_authority": "certified_forecast_pool_rows",
        "membrane_authority": "not_membrane_evidence",
        "routing_authority": "none_trace_does_not_route_work",
        "decision_use_required_for_routing": True,
    }


def test_resolved_certified_forecast_pool_row_can_count_for_membrane() -> None:
    row = {
        "prediction_id": "FP-closed",
        "contract_id": "forecast-demo-contract",
        "forecasted_at": "2026-06-19T00:00:00Z",
        "agent_id": "forecast_pool:aggregate",
        "predicted_at": "2026-06-19T00:00:00Z",
        "predictor": "forecast_pool:aggregate",
        "subject": "autoresearch:demo",
        "event": "next iteration improves score",
        "p_success": 0.7,
        "horizon": "next iteration",
        "resolution_rule": "actual_success if score improves",
        "tier": 2,
        "sealed_at": "2026-06-19T00:00:01Z",
        "source_context_sha256": "f" * 64,
        "resolved_at": "2026-06-19T00:20:00Z",
        "actual_success": True,
        "provenance": {
            "source_surface": "forecast_pool",
            "mode": "forecast_pool",
            "producer": "forecast_pool:aggregate",
            "certified": True,
            "can_satisfy_membrane": True,
        },
    }

    summary = summarize_prediction_contract_rows([row])

    assert validate_prediction_contract(row) == []
    assert summary["certified_count"] == 1
    assert summary["membrane_eligible_count"] == 1
    assert summary["authority"] == {
        "score_authority": "scoreable_binary_brier_rows",
        "calibration_authority": "certified_forecast_pool_rows",
        "membrane_authority": "resolved_certified_forecast_pool_rows",
        "routing_authority": "none_trace_does_not_route_work",
        "decision_use_required_for_routing": True,
    }


def test_prediction_contract_defaults_mark_scratch_contract_provenance() -> None:
    row = {
        "prediction_id": "SCR-001",
        "predicted_at": "2026-06-19T00:00:00Z",
        "predictor": "codex:rd",
        "event": "source chain closes",
        "p_success": 0.2,
        "horizon": "next prep pass",
        "resolution_rule": "actual_success if no active evidence gaps remain",
        "tier": 1,
        "sealed_at": "2026-06-19T00:00:01Z",
        "prediction_artifact_sha256": "c" * 64,
        "resolved_at": "2026-06-19T00:10:00Z",
        "actual_outcome": "failure",
    }
    defaults = PredictionContractDefaults(
        subject="autoresearch:demo",
        source_surface="scratch_contract",
        provenance_mode="out_of_loop",
        producer="codex:rd",
    )

    summary = summarize_prediction_contract_rows([row], defaults=defaults)

    assert summary["status"] == "scoreable_measurement_lane"
    assert summary["source_surfaces"] == {"scratch_contract": 1}
    assert summary["provenance_modes"] == {"out_of_loop": 1}
    assert summary["producers"] == {"codex:rd": 1}
    assert summary["mean_brier"] == 0.04
    assert score_binary_prediction_contract(normalize_prediction_contract(row, defaults=defaults))[
        "actual_success"
    ] is False


def test_prediction_contract_normalizes_forecast_pool_scratch_mirror_shape() -> None:
    row = {
        "prediction_id": "PL-SCRATCH-abc123",
        "predicted_at": "2026-06-19T00:00:00Z",
        "predictor": "codex:RD",
        "substrate": "autoresearch_demo",
        "question": "Will the next loop close the source-chain gap?",
        "p_success": 0.35,
        "tier": 2,
        "pre_registered_thresholds": "TRUE iff latest evidence gaps are empty",
        "prediction_artifact_path": "analytics/public/forecast_pool/scratch/demo.json",
        "linked_scratch_id": "scratch_abc123",
        "forecast_pool_semantics": {
            "source": "forecast_pool scratch-forecast",
            "certified": False,
            "excluded_from_calibration": True,
            "can_satisfy_membrane": False,
            "not_a_gp230_contract": True,
        },
        "resolved_at": "2026-06-19T00:30:00Z",
        "actual_outcome": "success",
        "actual_outcome_bucket": "event_1_success",
    }

    normalized = normalize_prediction_contract(row)
    issues = validate_prediction_contract(row)
    summary = summarize_prediction_contract_rows([row])

    assert normalized["prediction_id"] == "PL-SCRATCH-abc123"
    assert normalized["subject"] == "autoresearch_demo"
    assert normalized["event"] == "Will the next loop close the source-chain gap?"
    assert normalized["horizon"] == "TRUE iff latest evidence gaps are empty"
    assert normalized["resolution_rule"] == "TRUE iff latest evidence gaps are empty"
    assert normalized["provenance"] == {
        "source_surface": "scratch_contract",
        "mode": "out_of_loop",
        "producer": "codex:RD",
        "certified": False,
        "excluded_from_calibration": True,
        "can_satisfy_membrane": False,
    }
    assert issues == []
    assert summary["source_surfaces"] == {"scratch_contract": 1}
    assert summary["status"] == "resolved_no_calibration_rows"
    assert summary["scoreable_count"] == 0
    assert summary["mean_brier"] is None
    assert summary["excluded_from_calibration_count"] == 1
    assert summary["certified_count"] == 0
    assert summary["authority"] == {
        "score_authority": "not_scoreable_yet",
        "calibration_authority": "not_calibration_authority",
        "membrane_authority": "not_membrane_evidence",
        "routing_authority": "none_trace_does_not_route_work",
        "decision_use_required_for_routing": True,
    }


def test_prediction_summary_does_not_score_excluded_rows() -> None:
    row = {
        "prediction_id": "excluded",
        "predicted_at": "2026-06-19T00:00:00Z",
        "predictor": "codex:rd",
        "subject": "autoresearch:demo",
        "event": "evidence gap closes",
        "p_success": 0.9,
        "horizon": "next prep pass",
        "resolution_rule": "actual_success iff active gaps are empty",
        "tier": 2,
        "sealed_at": "2026-06-19T00:00:01Z",
        "prediction_artifact_sha256": "d" * 64,
        "provenance": {
            "source_surface": "scratch_contract",
            "mode": "out_of_loop",
            "producer": "codex:rd",
            "excluded_from_calibration": True,
        },
        "resolved_at": "2026-06-19T00:10:00Z",
        "actual_success": True,
    }

    summary = summarize_prediction_contract_rows([row])

    assert summary["status"] == "resolved_no_calibration_rows"
    assert summary["resolved_count"] == 1
    assert summary["scoreable_count"] == 0
    assert summary["mean_brier"] is None
    assert summary["excluded_from_calibration_count"] == 1


def test_scratch_rows_cannot_self_certify_or_claim_membrane() -> None:
    row = {
        "prediction_id": "scratch-self-certified",
        "predicted_at": "2026-06-19T00:00:00Z",
        "predictor": "codex:rd",
        "subject": "autoresearch:demo",
        "event": "evidence gap closes",
        "p_success": 0.9,
        "horizon": "next prep pass",
        "resolution_rule": "actual_success iff active gaps are empty",
        "tier": 2,
        "sealed_at": "2026-06-19T00:00:01Z",
        "prediction_artifact_sha256": "d" * 64,
        "provenance": {
            "source_surface": "scratch_contract",
            "mode": "out_of_loop",
            "producer": "codex:rd",
            "certified": True,
            "can_satisfy_membrane": True,
        },
        "resolved_at": "2026-06-19T00:10:00Z",
        "actual_success": True,
    }

    issues = validate_prediction_contract(row)
    summary = summarize_prediction_contract_rows([row])

    assert {issue.code for issue in issues} == {
        "invalid_certification_claim",
        "invalid_membrane_claim",
    }
    assert summary["status"] == "needs_attention"
    assert summary["valid_count"] == 0
    assert summary["scoreable_count"] == 0
    assert summary["certified_count"] == 0
    assert summary["membrane_eligible_count"] == 0
    assert summary["authority"]["routing_authority"] == "none_trace_does_not_route_work"


def test_forecast_pool_certification_requires_pool_authority_anchor() -> None:
    row = {
        "prediction_id": "surface-only",
        "predicted_at": "2026-06-19T00:00:00Z",
        "predictor": "codex:rd",
        "subject": "autoresearch:demo",
        "event": "evidence gap closes",
        "p_success": 0.9,
        "horizon": "next prep pass",
        "resolution_rule": "actual_success iff active gaps are empty",
        "tier": 2,
        "sealed_at": "2026-06-19T00:00:01Z",
        "prediction_artifact_sha256": "d" * 64,
        "provenance": {
            "source_surface": "forecast_pool",
            "mode": "forecast_pool",
            "producer": "codex:rd",
            "certified": True,
            "can_satisfy_membrane": True,
        },
        "resolved_at": "2026-06-19T00:10:00Z",
        "actual_success": True,
    }

    issues = validate_prediction_contract(row)
    summary = summarize_prediction_contract_rows([row])

    assert {issue.code for issue in issues} == {
        "missing_forecast_pool_authority_anchor",
        "invalid_certification_claim",
        "invalid_membrane_claim",
    }
    assert summary["status"] == "needs_attention"
    assert summary["certified_count"] == 0
    assert summary["membrane_eligible_count"] == 0


def test_scratch_mirror_cannot_certify_by_spoofing_forecast_pool_surface() -> None:
    row = {
        "prediction_id": "scratch-spoof",
        "contract_id": "not-a-contract",
        "forecasted_at": "2026-06-19T00:00:00Z",
        "agent_id": "codex:rd",
        "predictor": "codex:rd",
        "subject": "autoresearch:demo",
        "question": "Will source recovery close?",
        "p_success": 0.7,
        "pre_registered_thresholds": "TRUE iff active evidence gaps are empty",
        "tier": 2,
        "prediction_artifact_path": "analytics/public/forecast_pool/scratch/demo.json",
        "linked_scratch_id": "scratch_demo",
        "forecast_pool_semantics": {
            "source": "forecast_pool scratch-forecast",
            "certified": True,
            "excluded_from_calibration": False,
            "can_satisfy_membrane": True,
            "not_a_gp230_contract": True,
        },
        "provenance": {
            "source_surface": "forecast_pool",
            "mode": "forecast_pool",
            "producer": "codex:rd",
            "certified": True,
            "can_satisfy_membrane": True,
        },
        "resolved_at": "2026-06-19T00:10:00Z",
        "actual_success": True,
    }

    issues = validate_prediction_contract(row)
    summary = summarize_prediction_contract_rows([row])

    assert {issue.code for issue in issues} == {
        "invalid_scratch_certification_claim",
        "invalid_certification_claim",
        "invalid_membrane_claim",
    }
    assert summary["valid_count"] == 0
    assert summary["certified_count"] == 0
    assert summary["membrane_eligible_count"] == 0


def test_prediction_rows_cannot_claim_routing_or_waive_decision_use() -> None:
    row = {
        "prediction_id": "route-spoof",
        "predicted_at": "2026-06-19T00:00:00Z",
        "predictor": "codex:rd",
        "subject": "autoresearch:demo",
        "event": "evidence gap closes",
        "p_success": 0.9,
        "horizon": "next prep pass",
        "resolution_rule": "actual_success iff active gaps are empty",
        "tier": 2,
        "sealed_at": "2026-06-19T00:00:01Z",
        "prediction_artifact_sha256": "d" * 64,
        "routing_authority": "invoke_autoresearch",
        "route_autoresearch": True,
        "decision_use_required_for_routing": False,
        "provenance": {
            "source_surface": "autoresearch_workspace",
            "mode": "in_loop",
            "producer": "codex:rd",
        },
        "resolved_at": "2026-06-19T00:10:00Z",
        "actual_success": True,
    }

    issues = validate_prediction_contract(row)
    summary = summarize_prediction_contract_rows([row])

    assert {issue.code for issue in issues} == {
        "invalid_routing_authority_claim",
        "invalid_decision_use_bypass_claim",
    }
    assert summary["status"] == "needs_attention"
    assert summary["valid_count"] == 0
    assert summary["scoreable_count"] == 0
    assert summary["authority"] == {
        "score_authority": "not_scoreable_yet",
        "calibration_authority": "not_calibration_authority",
        "membrane_authority": "not_membrane_evidence",
        "routing_authority": "none_trace_does_not_route_work",
        "decision_use_required_for_routing": True,
    }


def test_prediction_summary_does_not_score_unsealed_rows() -> None:
    row = {
        "prediction_id": "unsealed",
        "predicted_at": "2026-06-19T00:00:00Z",
        "predictor": "codex:rd",
        "subject": "autoresearch:demo",
        "event": "evidence gap closes",
        "p_success": 0.9,
        "horizon": "next prep pass",
        "resolution_rule": "actual_success iff active gaps are empty",
        "tier": 2,
        "resolved_at": "2026-06-19T00:10:00Z",
        "actual_success": True,
        "provenance": {
            "source_surface": "autoresearch_workspace",
            "mode": "in_loop",
            "producer": "autoresearch_loop",
        },
    }

    summary = summarize_prediction_contract_rows([row])

    assert summary["status"] == "resolved_no_calibration_rows"
    assert summary["sealed_count"] == 0
    assert summary["scoreable_count"] == 0
    assert summary["mean_brier"] is None
    assert summary["issues"][0]["code"] == "unsealed_prediction"


def test_prediction_summary_does_not_score_invalid_rows() -> None:
    row = {
        "prediction_id": "invalid",
        "predicted_at": "2026-06-19T00:00:00Z",
        "predictor": "codex:rd",
        "subject": "autoresearch:demo",
        "event": "evidence gap closes",
        "p_success": 1.9,
        "horizon": "next prep pass",
        "resolution_rule": "actual_success iff active gaps are empty",
        "tier": 2,
        "sealed_at": "2026-06-19T00:00:01Z",
        "prediction_artifact_sha256": "e" * 64,
        "resolved_at": "2026-06-19T00:10:00Z",
        "actual_success": True,
        "provenance": {
            "source_surface": "autoresearch_workspace",
            "mode": "in_loop",
            "producer": "autoresearch_loop",
        },
    }

    summary = summarize_prediction_contract_rows([row])

    assert summary["status"] == "needs_attention"
    assert summary["invalid_count"] == 1
    assert summary["scoreable_count"] == 0
    assert summary["mean_brier"] is None
    assert any(issue["code"] == "invalid_probability" for issue in summary["issues"])
    assert summary["membrane_eligible_count"] == 0


def test_prediction_contract_rejects_noncausal_resolution_order() -> None:
    row = {
        "prediction_id": "posthoc",
        "predicted_at": "2026-06-19T00:10:00Z",
        "predictor": "codex:rd",
        "subject": "autoresearch:demo",
        "event": "evidence gap closes",
        "p_success": 0.9,
        "horizon": "next prep pass",
        "resolution_rule": "actual_success iff active gaps are empty",
        "tier": 2,
        "sealed_at": "2026-06-19T00:10:01Z",
        "prediction_artifact_sha256": "f" * 64,
        "resolved_at": "2026-06-19T00:10:00Z",
        "actual_success": True,
        "provenance": {
            "source_surface": "autoresearch_workspace",
            "mode": "in_loop",
            "producer": "autoresearch_loop",
        },
    }

    issues = validate_prediction_contract(row)
    summary = summarize_prediction_contract_rows([row])

    assert {issue.code for issue in issues} == {
        "noncausal_resolution_order",
        "noncausal_seal_resolution_order",
    }
    assert summary["status"] == "needs_attention"
    assert summary["valid_count"] == 0
    assert summary["scoreable_count"] == 0


def test_prediction_contract_rejects_forecast_time_mismatch() -> None:
    row = {
        "prediction_id": "time-mismatch",
        "contract_id": "forecast-demo-contract",
        "forecasted_at": "2026-06-19T00:00:00Z",
        "agent_id": "forecast_pool:aggregate",
        "predicted_at": "2026-06-19T00:01:00Z",
        "predictor": "forecast_pool:aggregate",
        "subject": "autoresearch:demo",
        "event": "next iteration improves score",
        "p_success": 0.7,
        "horizon": "next iteration",
        "resolution_rule": "actual_success if score improves",
        "tier": 2,
        "sealed_at": "2026-06-19T00:01:01Z",
        "source_context_sha256": "f" * 64,
        "provenance": {
            "source_surface": "forecast_pool",
            "mode": "forecast_pool",
            "producer": "forecast_pool:aggregate",
            "certified": True,
        },
    }

    issues = validate_prediction_contract(row)

    assert {issue.code for issue in issues} == {
        "prediction_forecast_time_mismatch",
    }


def test_prediction_contract_accepts_naive_iso_timestamps_as_utc() -> None:
    row = {
        "prediction_id": "naive-ok",
        "predicted_at": "2026-06-19T00:00:00",
        "predictor": "codex:rd",
        "subject": "autoresearch:demo",
        "event": "evidence gap closes",
        "p_success": 0.2,
        "horizon": "next prep pass",
        "resolution_rule": "actual_success iff active gaps are empty",
        "tier": 2,
        "sealed_at": "2026-06-19T00:00:01",
        "prediction_artifact_sha256": "a" * 64,
        "resolved_at": "2026-06-19T00:05:00Z",
        "actual_success": False,
        "provenance": {
            "source_surface": "scratch_contract",
            "mode": "out_of_loop",
            "producer": "codex:rd",
        },
    }

    assert validate_prediction_contract(row) == []
    summary = summarize_prediction_contract_rows([row])
    assert summary["status"] == "scoreable_measurement_lane"
