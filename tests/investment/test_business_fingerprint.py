import json
import os

import pytest

from ztare.common.equivariance import stable_sha256
from ztare.investment.business_fingerprint import _latest_dossier, compile_business_fingerprint


def _hashed(body, field):
    return {**body, field: stable_sha256(body)}


def test_latest_dossier_ignores_impossible_future_materialization(tmp_path):
    directory = tmp_path / "research" / "dossiers"
    directory.mkdir(parents=True)
    stale = directory / "ZD-stale.json"
    current = directory / "ZD-current.json"
    stale.write_text(json.dumps({"entity_id": "ZD", "generated_at": "2026-08-14T08:45:00Z"}))
    current.write_text(json.dumps({"entity_id": "ZD", "generated_at": "2026-08-14T08:02:00Z"}))
    os.utime(stale, (1_786_694_600, 1_786_694_600))
    os.utime(current, (1_786_694_600, 1_786_694_600))
    assert _latest_dossier(tmp_path, "ZD")["generated_at"] == "2026-08-14T08:02:00Z"


def test_business_fingerprint_preserves_coordinate_identity_and_comparability_limits():
    quality = _hashed({
        "schema": "jaggedthoughts-company-quality-report-v1",
        "entity_id": "ACME", "as_of": "2026-01-03T00:00:00Z",
        "available_at": "2026-01-02T00:00:00Z",
        "coverage": {"aligned_annual_periods": 3, "status": "sufficient_for_screen"},
        "history": [{
            "observed_at": "2025-12-31T00:00:00Z", "available_at": "2026-01-02T00:00:00Z",
            "revenue": 100, "operating_cash_flow": 20, "capital_expenditure": 5,
            "net_income": 15, "assets": 80, "owner_earnings": 15,
            "observation_ids": ["filing:year"], "source_refs": ["filing"],
        }],
        "metrics": {"revenue_cagr": 0.08, "revenue_growth_volatility": 0.12,
                    "net_debt_to_owner_earnings": 1.5},
        "scores": {"revenue_durability": 0.7, "durable_earnings_power": 0.65},
        "observation_ids": ["filing:year"], "source_refs": ["filing"],
        "residuals": ["pricing power unknown"],
    }, "quality_report_sha256")
    dossier = _hashed({
        "schema": "jaggedthoughts-candidate-research-dossier-v1",
        "entity_id": "ACME", "candidate_leaf": "a" * 64,
        "as_of": "2026-01-03T00:00:00Z", "generated_at": "2026-01-04T00:00:00Z",
        "durable_earnings_bridge": {
            "revenue_durability": "contracted but cancellable revenue",
            "concentration_and_fragility": ["top customer is material"],
        },
        "industry": {"customer_and_supplier_power": "customers can dual source"},
        "strategy": {
            "choices": [{"id": "embed", "description": "embed workflow"}],
            "reinforcing_edges": [], "representation_residuals": ["retention undisclosed"],
        },
        "sources": [{"id": "filing"}],
    }, "dossier_sha256")
    frontier = _hashed({
        "schema": "jaggedthoughts-company-strategy-frontier-v1",
        "company": {"id": "ACME", "candidate_leaf": "a" * 64,
                    "source_dossier_sha256": dossier["dossier_sha256"]},
        "evidence_epoch": "2026-01-04T00:00:00Z", "scope_closed": False,
        "decision_closed": False, "programs": [{"id": "p"}],
        "frontier_program_ids": ["p"], "local_peak_program_ids": ["p"],
        "pressure_to_option_coverage": {"customer_power": ["embed"]},
    }, "strategy_frontier_sha256")

    result = compile_business_fingerprint(
        company_quality=quality, research_dossier=dossier, strategy_frontier=frontier,
        compiled_at="2026-01-05T00:00:00Z",
    )
    observed = next(row for row in result["coordinates"] if row["coordinate_kind"] == "observed")
    assert "owner_earnings" not in observed["value"][0]
    assert result["axis_coverage"]["revenue_concentration"] == {
        "coordinate_kinds": ["qualitative"], "status": "qualitative_only",
    }
    assert result["cross_industry_comparability"]["allowed"] is False
    assert result["capital_authority"] is False
    assert "aggregate_score" not in result and "rank" not in result
    other = _hashed(
        {**{key: value for key, value in dossier.items() if key != "dossier_sha256"},
         "entity_id": "OTHER"},
        "dossier_sha256",
    )
    with pytest.raises(ValueError, match="entities differ"):
        compile_business_fingerprint(
            company_quality=quality, research_dossier=other,
            compiled_at="2026-01-05T00:00:00Z",
        )
