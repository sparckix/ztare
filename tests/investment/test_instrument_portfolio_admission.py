from __future__ import annotations

from datetime import date, timedelta
import json
from typing import Any

from ztare.common.equivariance import stable_sha256
from ztare.investment import instrument_portfolio_admission as admission_module
from ztare.investment.factor_analysis import (
    FACTOR_ANALYSIS_SCHEMA,
    PricePoint,
    RETURN_COVARIANCE_SCHEMA,
)
from ztare.investment.instrument_portfolio_admission import (
    INSTRUMENT_PORTFOLIO_ADMISSION_SCHEMA,
    compile_instrument_portfolio_admission,
    compile_workspace_instrument_portfolio_admissions,
)
from ztare.investment.sleeve_implementation import (
    IMPLEMENTATION_CANDIDATE_SCHEMA,
    SLEEVE_IMPLEMENTATION_FRONTIER_SCHEMA,
)


NOW = "2026-08-12T00:00:00Z"


def _seal(body: dict[str, Any], field: str) -> dict[str, Any]:
    return {**body, field: stable_sha256(body)}


def _inputs(entity: str, kind: str, fee: float) -> tuple[dict[str, Any], ...]:
    factor_body = {
        "schema": FACTOR_ANALYSIS_SCHEMA,
        "analysis_id": f"factor:{entity}",
        "candidate_entity_id": entity,
        "as_of": NOW,
        "available_at": NOW,
        "observed_period": {"start": "2023-01-01", "end": "2026-08-11"},
        "coefficients": {"betas": {"market": 0.9, "value": 0.4}},
        "historical": {
            "maximum_drawdown": -0.31,
            "residual_alpha_annualized": 0.12,
        },
        "assumption_implied": {
            "risk_free_rate": 0.04,
            "factor_contributions": {"market": 0.04, "value": 0.01},
            "return_without_residual_alpha": 0.09,
        },
    }
    factor = _seal(factor_body, "analysis_sha256")
    evidence = {
        "candidate_leaf": f"leaf:{entity}",
        "candidate_sha256": stable_sha256({"entity": entity}),
        "dossier_leaf": f"dossier:{entity}",
        "dossier_sha256": stable_sha256({"dossier": entity}),
        "factor_analysis_sha256": factor["analysis_sha256"],
        "fund_valuation_sha256": stable_sha256({"fund": entity}),
        "fund_holdings_graph_sha256": stable_sha256({"holdings": entity}),
        "valuation_envelope_sha256": stable_sha256({"valuation": entity}),
        "state_price_result_sha256": stable_sha256({"states": entity}),
    }
    decision_body = {
        "schema": f"jaggedthoughts-{kind.replace('_', '-')}-paper-decision-v1",
        "decision_id": f"paper:{entity}",
        "proposal_sha256": stable_sha256({"proposal": entity}),
        "activated_at": NOW,
        "entity": {"entity_id": entity, "entity_kind": kind},
        "lifecycle": {"data_class": "operator", "stage": "active"},
        "evidence": evidence,
        "research": {"thesis": {"confidence": 0.7}},
        "research_obligations": ["state_price_fit_diagnostic_only"],
        "underwriting_coordinates": {
            "factor": {"factor_analysis_sha256": factor["analysis_sha256"]},
            "valuation": {"return_coordinates": [{"horizon_years": 5, "irr": 0.11}]},
        },
        "paper_policy": {
            "target_weight": 0.0,
            "cash_default": True,
            "allocation_allowed": False,
            "order_routing_allowed": False,
        },
        "capital_authority": False,
        "brokerage_authority": False,
    }
    decision = _seal(decision_body, "decision_sha256")
    decision.update({"transition": {"to_state": "active_paper"}, "decision_path": "paper.json"})
    identity = {
        "subject_id": entity,
        "subject_kind": "public_security",
        "entity_kind": kind,
        "security_kind": "common_equity" if kind == "public_equity" else "exchange_traded_fund",
        "implementation_epoch": NOW,
    }
    implementation_body = {
        "schema": IMPLEMENTATION_CANDIDATE_SCHEMA,
        "identity": identity,
        "as_of": NOW,
        "lineage": {
            "proposal_sha256": decision["proposal_sha256"],
            "fund_choice_frontier_sha256": stable_sha256({"frontier": entity}),
            "alternative_sha256": stable_sha256({"alternative": entity}),
        },
        "proposal_sha256": decision["proposal_sha256"],
        "paper_decision_id": decision["decision_id"],
        "paper_decision_sha256": decision["decision_sha256"],
        "status": "admitted_to_implementation_review",
        "implementation_review_admitted": True,
        "current_target_weight": 0.0,
        "capital_authority": False,
        "brokerage_authority": False,
        "order_routing_allowed": False,
    }
    implementation = _seal(implementation_body, "implementation_candidate_sha256")
    sleeve_body = {
        "schema": SLEEVE_IMPLEMENTATION_FRONTIER_SCHEMA,
        "as_of": NOW,
        "policy_consumed": False,
        "implementation_blockers": ["household_allocation_frontier_absent"],
        "sleeves": [{
            "sleeve_id": "us_equity",
            "eligible_instruments": [{
                "identity": identity,
                "basis_proxy": False,
                "fees": {"expense_ratio": fee},
                "liquidity": {"median_bid_ask_spread": 0.0004},
                "implementation_candidate": implementation,
            }],
        }],
        "capital_authority": False,
        "brokerage_authority": False,
    }
    sleeve = _seal(sleeve_body, "sleeve_implementation_sha256")
    covariance = _seal({
        "schema": RETURN_COVARIANCE_SCHEMA,
        "as_of": NOW,
        "entity_ids": [entity],
        "annualized_volatility": {entity: 0.18},
        "window_start": "2023-01-01",
        "window_end": "2026-08-11",
        "return_count": 800,
    }, "return_covariance_sha256")
    return decision, sleeve, factor, covariance


def _full_research_run(
    decision: dict[str, Any], *, horizon_days: int = 90, run_id: str = "full-research-run",
) -> dict[str, Any]:
    forecast = _seal({
        "schema": "jaggedthoughts-closed-book-candidate-forecast-v1",
        "candidate_id": "underwriting_typed_plus_full_research",
        "predicted_values": {"active_return": 0.02, "underperformance_event": 0.35},
        "explanation": {"evidence_arm": "typed_plus_full_research"},
    }, "forecast_sha256")
    subject = {"subject_sha256": decision["decision_sha256"]}
    return _seal({
        "schema": "jaggedthoughts-closed-book-forecast-run-v1",
        "run_id": run_id,
        "sealed_at": NOW,
        "horizon_days": horizon_days,
        "subject": subject,
        "evidence_packet": {
            "subject": subject,
            "benchmark": {"entity_id": "SPY"},
            "packet_sha256": "a" * 64,
        },
        "candidate_forecasts": [forecast],
    }, "run_sha256")


def test_equity_and_fund_admission_preserve_research_account_boundaries() -> None:
    for entity, kind, fee in (("ACME", "public_equity", 0.0), ("FUND", "public_fund", 0.005)):
        decision, sleeve, factor, covariance = _inputs(entity, kind, fee)
        runs = [
            _full_research_run(decision),
            _full_research_run(decision, horizon_days=365, run_id="full-research-run-365"),
        ] if kind == "public_equity" else []
        result = compile_instrument_portfolio_admission(
            paper_watch_decision=decision,
            sleeve_implementation=sleeve,
            factor_analysis=factor,
            return_covariance=covariance,
            closed_book_runs=runs,
            compiled_at=NOW,
            cash_expected_return=0.03 if kind == "public_fund" else None,
            cash_hurdle_source_sha256="c" * 64 if kind == "public_fund" else None,
        )

        assert result["schema"] == INSTRUMENT_PORTFOLIO_ADMISSION_SCHEMA
        assert result["eligibility"]["status"] == "admitted_to_research_paper_portfolio"
        assert result["personalized_account_implementation"]["status"] == "blocked_private_account_context"
        assert result["personalized_account_implementation"]["research_paper_admission_blocked"] is False
        assert result["economic_basis"]["historical_residual_alpha_weight"] == 0.0
        assert result["diagnostics"]["state_prices_used_as_probabilities"] is False
        assert result["diagnostics"]["valuation_implied_return_used_as_expected_return"] is False
        assert result["portfolio_projection"]["downside_risk"] >= 0.31
        assert result["capital_authority"] is result["brokerage_authority"] is False
        body = {key: value for key, value in result.items() if key != "admission_sha256"}
        assert result["admission_sha256"] == stable_sha256(body)

        if kind == "public_equity":
            assert result["economic_basis"]["return_basis"] == "declared_factor_premiums_zero_residual_alpha"
            assert result["forecast_binding"]["claims"][0]["run_id"] == "full-research-run"
            assert result["forecast_binding"]["used_as_expected_active_return_claims"] is True
            claim = result["portfolio_projection"]["expected_active_return_claims"][0]
            assert claim["benchmark_entity_id"] == "SPY"
            assert claim["horizon_days"] == 90
            assert [row["horizon_days"] for row in result["portfolio_projection"]["expected_active_return_claims"]] == [90, 365]
        else:
            assert result["economic_basis"]["return_basis"] == (
                "factor_total_return_zero_alpha_less_fee_vs_public_cash"
            )
            assert abs(
                result["portfolio_projection"]["required_return_hurdle"]["annualized_excess"]
                - 0.055
            ) < 1e-12
            assert result["portfolio_projection"]["expected_active_return_claims"] == []
            assert result["economic_basis"]["required_excess_return_vs_factor_risk_free"] == 0.045
            assert result["economic_basis"]["historical_residual_alpha_weight"] == 0.0
            assert result["research_identity"]["fund_choice_frontier_sha256"]


def test_workspace_admission_reprices_equity_at_current_market_epoch(tmp_path, monkeypatch) -> None:
    decision, sleeve, _old_factor, _covariance = _inputs("ACME", "public_equity", 0.0)
    fund_decision, fund_sleeve, fund_factor, _ = _inputs("FUND", "public_fund", 0.005)
    for watch in (decision, fund_decision):
        decision_path = (
            tmp_path / "paper_decisions" / watch["entity"]["entity_kind"]
            / f"{watch['entity']['entity_id'].lower()}.json"
        )
        decision_path.parent.mkdir(parents=True, exist_ok=True)
        decision_path.write_text(json.dumps({
            key: value for key, value in watch.items()
            if key not in {"transition", "decision_path"}
        }))
    sleeve_body = {key: value for key, value in sleeve.items() if key != "sleeve_implementation_sha256"}
    sleeve_body["sleeves"][0]["eligible_instruments"].extend(
        fund_sleeve["sleeves"][0]["eligible_instruments"]
    )
    sleeve = _seal(sleeve_body, "sleeve_implementation_sha256")
    watchlist = _seal({
        "schema": "jaggedthoughts-opportunity-watchlist-result-v1",
        "watchlist_id": "current-funds", "as_of": NOW,
        "candidates": [{"entity_id": "FUND", "analysis": fund_factor}],
    }, "watchlist_sha256")
    watchlist_path = tmp_path / "watchlists" / "results" / "funds.json"
    watchlist_path.parent.mkdir(parents=True)
    watchlist_path.write_text(json.dumps(watchlist))
    run_path = tmp_path / "closed_book" / "runs" / "run.json"
    run_path.parent.mkdir(parents=True)
    run_path.write_text(json.dumps(_full_research_run(decision)))
    market = _seal({
        "schema": "jaggedthoughts-market-state-snapshot-artifact-v2",
        "point_in_time_snapshot": {"as_of": NOW},
        "cash_yields": {"90": 0.03, "365": 0.035},
        "state": {
            "implied_nominal_equity_return": 0.09,
            "nominal_implied_equity_risk_premium": 0.05,
        },
        "capital_authority": False,
    }, "snapshot_artifact_sha256")
    market_path = tmp_path / "market_state" / "snapshots" / "latest.json"
    market_path.parent.mkdir(parents=True)
    market_path.write_text(json.dumps(market))

    prices = {"SPY": 100.0, "ACME": 50.0, "FUND": 75.0}
    points = []
    for index in range(130):
        day = (date(2026, 1, 1) + timedelta(days=index)).isoformat()
        if index:
            market_return = 0.0002 + 0.0001 * (index % 7)
            prices["SPY"] *= 1 + market_return
            prices["ACME"] *= 1 + 0.0001 + 1.2 * market_return
            prices["FUND"] *= 1 + 0.00005 + 0.9 * market_return
        for entity in prices:
            points.append(PricePoint(
                entity_id=entity, observed_at=f"{day}T00:00:00Z",
                available_at=f"{day}T00:00:00Z", value=prices[entity],
                observation_id=f"{entity}:{day}", source_ref=f"public:{entity}",
            ))
    monkeypatch.setattr(admission_module, "load_price_points", lambda *_args, **_kwargs: tuple(points))

    result = compile_workspace_instrument_portfolio_admissions(tmp_path, sleeve, NOW)

    assert (result["watch_count"], result["admitted_count"], result["blocked_count"]) == (2, 2, 0)
    assert abs(result["equity_capm_basis"]["risk_free_rate"] - 0.04) < 1e-12
    admission = next(row for row in result["admissions"] if row["subject"]["subject_id"] == "ACME")
    epochs = admission["diagnostics"]["factor_epoch_binding"]
    assert epochs["same_epoch"] is False
    assert epochs["underwriting_factor_analysis_sha256"] != epochs["allocation_factor_analysis_sha256"]
    assert admission["economic_basis"]["historical_residual_alpha_weight"] == 0.0
    assert admission["forecast_binding"]["claims"][0]["run_id"] == "full-research-run"
    fund_admission = next(
        row for row in result["admissions"] if row["subject"]["subject_id"] == "FUND"
    )
    assert abs(
        fund_admission["portfolio_projection"]["required_return_hurdle"]["annualized_excess"]
        - 0.055
    ) < 1e-12
    assert fund_admission["economic_basis"]["cash_hurdle_source_sha256"] == market[
        "snapshot_artifact_sha256"
    ]
    fund_source = next(row for row in result["allocation_factor_sources"] if row["entity_id"] == "FUND")
    assert fund_source["allocation_factor_analysis_sha256"] == fund_factor["analysis_sha256"]
    assert fund_source["source_artifact_sha256"] == watchlist["watchlist_sha256"]
    assert result["capital_authority"] is result["brokerage_authority"] is False
