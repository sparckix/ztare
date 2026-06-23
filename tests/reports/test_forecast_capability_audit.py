from __future__ import annotations

from ztare.reports.forecast_capability_audit import build_forecast_capability_audit


def test_forecast_capability_audit_tracks_lifecycle_surfaces() -> None:
    report = build_forecast_capability_audit()

    assert report["schema"] == "ztare-forecast-capability-audit-v1"
    summary = report["summary"]
    assert "gp230_contract_schema_gate" in summary["ready_receipt_paths"]
    assert "read_only_forecast_emission" in summary["ready_receipt_paths"]
    assert "aggregate_allocation_read_model" in summary["ready_receipt_paths"]
    assert "objective_resolution_scoring" in summary["ready_receipt_paths"]
    assert "calibration_weight_update" in summary["ready_receipt_paths"]
    assert "scratch_forecast_semantics" in summary["ready_receipt_paths"]
    assert "decision_use_logging" in summary["ready_receipt_paths"]
    assert "prediction_contract_read_model" in summary["ready_receipt_paths"]
    assert "operations_intelligence_consumer" in summary["ready_receipt_paths"]
    assert summary["missing_rows"] == []
    assert "docs_rewrite_rows" not in summary


def test_forecast_capability_audit_release_boundary_is_conservative() -> None:
    report = build_forecast_capability_audit()
    verdict = report["verdict"]

    assert verdict["not_hidden_scheduler"] is True
    assert "sealed forecast-pool lifecycle" in verdict["strongest_supported_claim"]
    assert "Scratch forecasts stay uncertified" in verdict["release_boundary"]
    assert "decision-use" in verdict["needs_before_stronger_claim"]
