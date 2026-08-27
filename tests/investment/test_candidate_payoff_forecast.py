import json

import pytest

from ztare.common.equivariance import stable_sha256
from ztare.investment.candidate_payoff_forecast import (
    compile_candidate_payoff_forecast,
    due_candidate_payoff_forecast_requests,
)


def _sealed(body, field):
    return {**body, field: stable_sha256(body)}


def test_candidate_payoff_forecast_bounds_authored_world_mixture():
    valuation = _sealed({
        "schema": "jaggedthoughts-valuation-envelope-v1", "entity_id": "ABC",
        "evidence_epoch": "2026-01-01T00:00:00Z",
        "assumptions": [{
            "assumption_type": "MarketPrice", "value": 100.0,
            "source_refs": ["price-source"],
        }],
        "scenarios": [
            {"scenario_id": state_id, "source_refs": [f"{state_id}-valuation"]}
            for state_id in ("thesis", "rival", "residual")
        ],
    }, "envelope_sha256")
    candidate = _sealed({
        "schema": "jaggedthoughts-discovery-candidate-v1", "candidate_id": "equity:ABC",
        "entity_id": "ABC", "entity_kind": "public_equity",
        "as_of": "2026-01-01T00:00:00Z",
        "valuation": {"envelope_sha256": valuation["envelope_sha256"]},
    }, "candidate_sha256")
    admission = _sealed({
        "schema": "jaggedthoughts-instrument-portfolio-admission-v1",
        "compiled_at": "2026-01-02T00:00:00Z", "subject": {"subject_id": "ABC"},
        "research_identity": {
            "candidate_leaf": "leaf-abc", "candidate_sha256": candidate["candidate_sha256"],
            "dossier_sha256": "d" * 64,
            "valuation_envelope_sha256": valuation["envelope_sha256"],
        },
        "eligibility": {"status": "admitted_to_research_paper_portfolio"},
    }, "admission_sha256")
    states = [
        ("thesis", 0.3, 0.5, 0.2, 0.6, False),
        ("rival", 0.2, 0.4, -0.2, 0.1, False),
        ("residual", 0.1, 0.4, -0.6, -0.3, True),
    ]
    payload = {
        "schema": "jaggedthoughts-candidate-payoff-forecast-v1",
        "contract_id": "candidate-payoff:ABC:one", "entity_id": "ABC",
        "candidate_leaf": "leaf-abc", "candidate_sha256": candidate["candidate_sha256"],
        "instrument_admission_sha256": admission["admission_sha256"],
        "valuation_envelope_sha256": valuation["envelope_sha256"],
        "dossier_sha256": "d" * 64, "information_cutoff": "2026-01-02T00:00:00Z",
        "horizon_at": "2027-01-02T00:00:00Z", "horizon_days": 365,
        "spot_price_observation": {
            "observation_id": "spot-abc", "value": 100.0, "unit": "currency/share",
            "observed_at": "2026-01-01T00:00:00Z", "available_at": "2026-01-01T00:00:00Z",
            "source_ref": "price-source",
        },
        "comparator": {
            "kind": "benchmark_total_return", "entity_id": "SPY",
            "horizon_return": {"low": -0.1, "high": 0.2, "unit": "decimal"},
            "source_refs": ["benchmark-forecast"],
        },
        "scope": {
            "kind": "ordered_thesis_rival_residual_partition",
            "residual_state_id": "residual", "exhaustive_within_authored_scope": True,
        },
        "states": [{
            "state_id": state_id,
            "outcome_predicate": {
                "metric_ids": ["owner_earnings"], "settlement_rule": f"settle {state_id}",
                "is_residual_catch_all": catch_all,
            },
            "probability": {
                "low": p_low, "high": p_high, "unit": "probability_decimal",
                "identity": "authored_forecast_interval",
                "source_refs": [f"{state_id}-evidence"],
            },
            "candidate_horizon_total_return": {
                "low": r_low, "high": r_high, "unit": "decimal",
                "valuation_scenario_ids": [state_id], "source_refs": [f"{state_id}-valuation"],
            },
        } for state_id, p_low, p_high, r_low, r_high, catch_all in states],
    }

    compiled = compile_candidate_payoff_forecast(
        candidate=candidate, admission=admission, valuation=valuation, forecast=payload,
    )
    result = compiled["forecast_result"]

    assert result["expected_active_return_interval"] == pytest.approx({"low": -0.44, "high": 0.41})
    assert result["underperformance_probability_interval"] == pytest.approx({"low": 0.1, "high": 0.7})
    assert result["worst_case_active_return"] == pytest.approx(-0.8)
    diagnostics = result["uncertainty_diagnostics"]
    assert diagnostics["total_expected_active_return_width"] == pytest.approx(0.85)
    assert diagnostics["dominant_component"] in {
        "probability_intervals", "candidate_return_intervals", "comparator_return_interval",
    }
    assert diagnostics["decision_authority"] is False
    assert result["market_state_prices_identified"] is False
    assert result["capital_authority"] is False


def test_due_forecast_tracks_research_epoch_not_recompiled_admission(tmp_path):
    candidate_sha, valuation_sha, dossier_sha = "c" * 64, "v" * 64, "d" * 64
    discovery = {"candidates": [{
        "candidate_id": "equity:ABC", "entity_id": "ABC",
        "entity_kind": "public_equity", "screen_status": "qualified", "research_rank": 2,
        "candidate_sha256": candidate_sha,
        "valuation": {"envelope_sha256": valuation_sha},
    }]}
    admission = {
        "admission_sha256": "a" * 64, "subject": {"subject_id": "ABC"},
        "eligibility": {"status": "admitted_to_research_paper_portfolio"},
        "research_identity": {
            "candidate_leaf": "leaf", "candidate_sha256": candidate_sha,
            "valuation_envelope_sha256": valuation_sha, "dossier_sha256": dossier_sha,
        },
    }
    for path, payload in (
        (tmp_path / "discovery/latest.json", discovery),
        (tmp_path / "portfolio/instrument_admissions/latest.json", {"admissions": [admission]}),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
    assert [row["entity_id"] for row in due_candidate_payoff_forecast_requests(tmp_path)] == ["ABC"]

    result_path = tmp_path / "underwriting/payoff_forecasts/results/abc.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_text(json.dumps({
        "schema": "jaggedthoughts-candidate-payoff-forecast-result-v1",
        "candidate_sha256": candidate_sha, "valuation_envelope_sha256": valuation_sha,
        "dossier_sha256": dossier_sha, "instrument_admission_sha256": "old-admission",
    }), encoding="utf-8")
    assert due_candidate_payoff_forecast_requests(tmp_path) == []
