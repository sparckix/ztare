"""Join typed valuation, factor, and market-state evidence for underwriting."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, timestamp_key
from .discovery import DISCOVERY_CANDIDATE_SCHEMA, DISCOVERY_RUN_SCHEMA
from .factor_analysis import FACTOR_ANALYSIS_SCHEMA


UNDERWRITING_INDEX_SCHEMA = "jaggedthoughts-underwriting-opportunity-index-v1"
MARKET_STATE_SCHEMA = "jaggedthoughts-market-state-snapshot-artifact-v1"
MARKET_STATE_SCHEMAS = {MARKET_STATE_SCHEMA, "jaggedthoughts-market-state-snapshot-artifact-v2"}
VALUATION_ENVELOPE_SCHEMA = "jaggedthoughts-valuation-envelope-v1"
MODELED_PAYOFF_GRID_SCHEMA = "jaggedthoughts-modeled-payoff-grid-v1"
PAYOFF_FORECAST_RESULT_SCHEMA = "jaggedthoughts-candidate-payoff-forecast-result-v1"


def _market_coordinates(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if snapshot.get("schema") not in MARKET_STATE_SCHEMAS:
        raise ValueError(f"underwriting adapter requires one of {sorted(MARKET_STATE_SCHEMAS)}")
    point = dict(snapshot.get("point_in_time_snapshot") or {})
    observations = {
        str(row["metric_id"]): dict(row)
        for row in point.get("observations") or ()
        if isinstance(row, Mapping) and row.get("metric_id")
    }
    required = {"implied_equity_risk_premium", "risk_free_rate"}
    if required - observations.keys():
        raise ValueError("market-state snapshot lacks required ERP or risk-free identity")
    state = dict(snapshot.get("state") or {})
    primary = observations["implied_equity_risk_premium"]
    variants = [
        {"metric_id": metric_id, "value": row["value"], "observation_id": row["observation_id"],
         "source_ref": row["source_ref"], "method_class": "cash_flow_implied_erp"}
        for metric_id, row in sorted(observations.items())
        if metric_id == "implied_equity_risk_premium" or metric_id.startswith("implied_erp_")
    ]
    spread_inputs = {
        "forward_earnings_yield_minus_nominal_10y": [
            "sp500_forward_earnings_yield", "treasury_10y_real_yield", "breakeven_inflation_10y",
        ],
        "trailing_earnings_yield_minus_tips_diagnostic": ["sp500_trailing_earnings_yield", "treasury_10y_real_yield"],
        "dividend_yield_minus_tips_income_diagnostic": ["sp500_trailing_dividend_yield", "treasury_10y_real_yield"],
    }
    spreads = []
    for metric_id, value in (state.get("valuation_spreads") or {}).items():
        inputs = spread_inputs.get(str(metric_id), [])
        if value is None or any(key not in observations for key in inputs):
            continue
        spreads.append({
            "metric_id": metric_id, "value": value, "method_class": "yield_spread_diagnostic",
            "input_observation_ids": [observations[key]["observation_id"] for key in inputs],
            "source_refs": sorted({str(observations[key]["source_ref"]) for key in inputs}),
            "expected_return_claim": False,
        })
    return {
        "as_of": canonical_timestamp(point.get("as_of"), "market-state as_of"),
        "snapshot_artifact_sha256": snapshot.get("snapshot_artifact_sha256"),
        "primary_cash_flow_implied_erp": {
            "metric_id": "implied_equity_risk_premium", "value": primary["value"],
            "observation_id": primary["observation_id"], "source_ref": primary["source_ref"],
            "method_class": "cash_flow_implied_market_erp", "expected_return_claim": False,
        },
        "cash_flow_implied_erp_variants": variants,
        "yield_spread_diagnostics": spreads,
        "implied_nominal_market_return": state.get("implied_nominal_equity_return"),
        "state_price_kernel": {
            "status": "unidentified",
            "reason": "current public priced claims do not identify market state prices",
        },
    }


def _conditional_payoff(
    candidate: Mapping[str, Any], artifact: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if artifact is None:
        return None
    if artifact.get("schema") != MODELED_PAYOFF_GRID_SCHEMA:
        raise ValueError(f"conditional payoff analysis requires {MODELED_PAYOFF_GRID_SCHEMA}")
    body = {key: value for key, value in artifact.items() if key != "modeled_grid_sha256"}
    if stable_sha256(body) != artifact.get("modeled_grid_sha256"):
        raise ValueError("conditional payoff artifact content hash mismatch")
    proposal = dict(artifact.get("compiled_proposal") or {})
    result = dict(proposal.get("state_price_result") or {})
    if (
        artifact.get("entity_id") != candidate.get("entity_id")
        or proposal.get("candidate_sha256") != candidate.get("candidate_sha256")
        or artifact.get("scope_boundary") != "conditional_model_grid_not_physical_world_distribution"
    ):
        raise ValueError("conditional payoff artifact crossed candidate identity or scope")
    return {
        "schema": "jaggedthoughts-conditional-payoff-analysis-v1",
        "identity": "conditional_scenario_price_consistency",
        "status": (
            "observed_price_consistent_with_declared_grid"
            if result.get("no_arbitrage_certificate")
            else "observed_price_inconsistent_with_declared_grid"
        ),
        "modeled_grid_sha256": artifact["modeled_grid_sha256"],
        "pricing_result_sha256": result.get("result_sha256"),
        "declared_grid_price_rank_complete": bool(result.get("market_complete")),
        "market_state_prices_identified": False,
        "physical_probability_claim": False,
        "expected_return_claim": False,
        "capital_authority": False,
    }


def _payoff_forecast(
    candidate: Mapping[str, Any], artifact: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if artifact is None:
        return None
    body = {key: value for key, value in artifact.items() if key != "forecast_result_sha256"}
    if (
        artifact.get("schema") != PAYOFF_FORECAST_RESULT_SCHEMA
        or stable_sha256(body) != artifact.get("forecast_result_sha256")
        or artifact.get("candidate_sha256") != candidate.get("candidate_sha256")
        or str(artifact.get("entity_id") or "").upper()
        != str(candidate.get("entity_id") or "").upper()
        or artifact.get("expected_return_identity")
        != "forecast_interval_conditional_on_authored_worlds"
        or artifact.get("market_state_prices_identified") is not False
        or artifact.get("capital_authority") is not False
    ):
        raise ValueError("candidate payoff forecast crossed identity or authority")
    return {
        "forecast_result_sha256": artifact["forecast_result_sha256"],
        "contract_sha256": artifact["contract_sha256"],
        "information_cutoff": artifact["information_cutoff"],
        "horizon_at": artifact["horizon_at"],
        "horizon_days": artifact["horizon_days"],
        "comparator_entity_id": artifact["comparator_entity_id"],
        "expected_active_return_interval": artifact["expected_active_return_interval"],
        "underperformance_probability_interval": artifact[
            "underperformance_probability_interval"
        ],
        "worst_case_active_return": artifact["worst_case_active_return"],
        "uncertainty_diagnostics": artifact.get("uncertainty_diagnostics"),
        "expected_return_identity": artifact["expected_return_identity"],
        "market_state_prices_identified": False,
        "capital_authority": False,
    }


def _equity_valuation(candidate: Mapping[str, Any], artifact: Mapping[str, Any]) -> dict[str, Any]:
    if artifact.get("schema") != VALUATION_ENVELOPE_SCHEMA:
        raise ValueError(f"equity valuation requires {VALUATION_ENVELOPE_SCHEMA}")
    if (
        artifact.get("envelope_sha256") != (candidate.get("valuation") or {}).get("envelope_sha256")
        or artifact.get("entity_id") != candidate.get("entity_id")
        or artifact.get("evidence_epoch") != candidate.get("as_of")
    ):
        raise ValueError("valuation artifact crossed candidate identity or evidence epoch")
    summary = dict(artifact.get("summary") or {})
    assumptions = {
        str(row["assumption_type"]): dict(row)
        for row in artifact.get("assumptions") or () if isinstance(row, Mapping)
    }
    risk_free = float(assumptions["RiskFreeRate"]["value"])
    implied_return = float(summary["implied_required_return_median"])
    excess = float(summary["price_implied_excess_return"])
    if abs((implied_return - risk_free) - excess) > 1e-10:
        raise ValueError("valuation excess return does not reconcile to its risk-free assumption")
    return {
        "valuation_kind": "cash_flow_expectations_frontier",
        "valuation_sha256": artifact["envelope_sha256"],
        "implied_growth": float(summary["implied_growth_median"]),
        "earnings_power_margin": float(summary["earnings_power_margin_of_safety"]),
        "return_coordinates": [{
            "metric_id": "cash_flow_implied_required_return", "value": implied_return,
            "method_class": "security_cash_flow_implied_irr", "expected_realized_return_claim": False,
        }, {
            "metric_id": "price_implied_excess_return", "value": excess,
            "baseline_metric_id": "risk_free_rate", "baseline_value": risk_free,
            "method_class": "security_cash_flow_implied_irr_minus_nominal_treasury",
            "expected_realized_return_claim": False,
        }],
        "source_refs": sorted({
            str(ref) for row in artifact.get("assumptions") or () for ref in row.get("source_refs") or ()
        }),
    }


def _fund_valuation(candidate: Mapping[str, Any]) -> dict[str, Any] | None:
    valuation = candidate.get("valuation")
    if not isinstance(valuation, Mapping) or not valuation.get("source_refs"):
        return None
    implied_return = (candidate.get("metrics") or {}).get("factor_implied_return")
    if implied_return is None or abs(float(valuation["required_return"]) - float(implied_return)) > 1e-10:
        raise ValueError("fund valuation required return crossed factor-return identity")
    return {
        "valuation_kind": str(valuation.get("valuation_kind") or "aggregate_expectations_proxy"),
        "valuation_sha256": stable_sha256(valuation),
        "implied_growth": float(valuation["implied_growth_median"]),
        "earnings_power_margin": float(valuation["earnings_power_margin"]),
        "return_coordinates": [{
            "metric_id": "factor_required_return", "value": float(implied_return),
            "method_class": "declared_factor_premium_required_return",
            "expected_realized_return_claim": False,
        }],
        "source_refs": sorted(map(str, valuation.get("source_refs") or ())),
    }


def _factor(candidate: Mapping[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    if candidate.get("entity_kind") == "public_equity":
        receipt = candidate.get("beta_receipt") or {}
        analysis = receipt.get("analysis") if isinstance(receipt, Mapping) else None
        if not isinstance(analysis, Mapping) or analysis.get("schema") != FACTOR_ANALYSIS_SCHEMA:
            return None, ["typed_factor_analysis_absent"]
        if analysis.get("candidate_entity_id") != candidate.get("entity_id"):
            raise ValueError("factor analysis crossed candidate identity")
        premiums = [float(row.get("expected_annual_premium", 0)) for row in analysis.get("factors") or ()]
        observation_ids = list(analysis.get("source_observation_ids") or ())
        return ({
            "factor_analysis_sha256": analysis.get("analysis_sha256"),
            "status": "exposure_only" if not any(premiums) else "factor_required_return_available",
            "betas": dict((analysis.get("coefficients") or {}).get("betas") or {}),
            "fit": dict(analysis.get("fit") or {}),
            "historical_residual_alpha": (analysis.get("historical") or {}).get("residual_alpha_annualized"),
            "assumption_implied_return": (
                (analysis.get("assumption_implied") or {}).get("return_without_residual_alpha")
                if any(premiums) else None
            ),
            "source_observation_count": len(observation_ids),
            "source_observation_ids_sha256": stable_sha256(observation_ids),
            "source_refs": list(analysis.get("source_refs") or ()),
        }, ["factor_expected_return_unavailable_beta_only"] if not any(premiums) else [])
    sha = str(candidate.get("factor_analysis_sha256") or "")
    if len(sha) != 64:
        return None, ["typed_factor_analysis_absent"]
    return ({
        "factor_analysis_sha256": sha, "status": "candidate_projection_only",
        "assumption_implied_return": (candidate.get("metrics") or {}).get("factor_implied_return"),
        "historical_residual_alpha": (candidate.get("metrics") or {}).get("residual_alpha"),
        "source_observation_ids": [], "source_refs": list(candidate.get("source_refs") or ()),
    }, ["factor_source_observation_ids_not_projected_into_discovery_candidate"])


def compile_underwriting_opportunity_index(
    discovery: Mapping[str, Any], market_snapshot: Mapping[str, Any], *,
    valuation_artifacts: Mapping[str, Mapping[str, Any]] | None = None,
    conditional_payoff_artifacts: Mapping[str, Mapping[str, Any]] | None = None,
    payoff_forecast_results: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Qualify the existing research-priority ranking using non-substitutable coordinates."""
    if discovery.get("schema") != DISCOVERY_RUN_SCHEMA:
        raise ValueError(f"underwriting adapter requires {DISCOVERY_RUN_SCHEMA}")
    run_body = {key: value for key, value in discovery.items() if key != "run_sha256"}
    if discovery.get("run_sha256") and stable_sha256(run_body) != discovery["run_sha256"]:
        raise ValueError("discovery run content hash mismatch")
    rank_input = dict(discovery.get("rank_program_input") or {})
    rank_body = {
        key: value for key, value in rank_input.items()
        if key != "rank_program_input_sha256"
    }
    if (
        rank_input.get("schema") != "jaggedthoughts-rank-program-input-v1"
        or stable_sha256(rank_body) != rank_input.get("rank_program_input_sha256")
        or rank_input.get("discovery_run_id") != discovery.get("run_id")
    ):
        raise ValueError("underwriting adapter requires the signed current rank-program input")
    rank_eligibility: dict[str, bool] = {}
    for lane in rank_input.get("lanes") or ():
        for row in lane.get("candidates") or ():
            candidate_id = str(row.get("candidate_id") or "")
            eligible = row.get("rank_program_eligible")
            if not candidate_id or candidate_id in rank_eligibility or not isinstance(eligible, bool):
                raise ValueError("rank-program input has an invalid candidate identity or eligibility")
            rank_eligibility[candidate_id] = eligible
    valuation_artifacts = valuation_artifacts or {}
    conditional_payoff_artifacts = conditional_payoff_artifacts or {}
    payoff_forecast_results = payoff_forecast_results or {}
    market = _market_coordinates(market_snapshot)
    rows = []
    for raw in discovery.get("candidates") or ():
        if not isinstance(raw, Mapping) or raw.get("schema") != DISCOVERY_CANDIDATE_SCHEMA:
            continue
        candidate = dict(raw)
        candidate_body = {key: value for key, value in candidate.items() if key != "candidate_sha256"}
        if stable_sha256(candidate_body) != candidate.get("candidate_sha256"):
            raise ValueError("discovery candidate content hash mismatch")
        as_of = canonical_timestamp(candidate.get("as_of"), "candidate as_of")
        gaps = []
        if timestamp_key(market["as_of"]) > timestamp_key(as_of):
            gaps.append("compatible_prior_market_state_absent")
        if candidate.get("entity_kind") == "public_equity":
            valuation = _equity_valuation(candidate, valuation_artifacts[str(candidate["candidate_id"])]) \
                if str(candidate["candidate_id"]) in valuation_artifacts else None
            if valuation is None:
                gaps.append("typed_valuation_envelope_absent")
        else:
            valuation = _fund_valuation(candidate)
            if valuation is None:
                gaps.append("aggregate_valuation_evidence_absent")
        factor, factor_gaps = _factor(candidate)
        gaps.extend(factor_gaps)
        conditional_payoff = _conditional_payoff(
            candidate, conditional_payoff_artifacts.get(str(candidate["candidate_id"])),
        )
        payoff_forecast = _payoff_forecast(
            candidate, payoff_forecast_results.get(str(candidate["candidate_id"])),
        )
        underwriting_coordinates_complete = bool(
            valuation and factor and "compatible_prior_market_state_absent" not in gaps
            and candidate.get("rank") is not None and candidate.get("rank_score") is not None
        )
        candidate_id = str(candidate["candidate_id"])
        if candidate_id not in rank_eligibility:
            raise ValueError(f"rank-program row missing for candidate {candidate_id}")
        rank_eligible = rank_eligibility[candidate_id]
        body = {
            "candidate_id": candidate["candidate_id"], "candidate_sha256": candidate["candidate_sha256"],
            "entity_id": candidate["entity_id"], "entity_kind": candidate["entity_kind"], "as_of": as_of,
            "valuation": valuation, "factor": factor,
            "market_context_sha256": market["snapshot_artifact_sha256"],
            "ranking": {
                "eligible": rank_eligible, "rank": candidate.get("rank") if rank_eligible else None,
                "research_priority_score": candidate.get("rank_score") if rank_eligible else None,
                "research_priority_is_expected_return": False,
                "underwriting_coordinates_complete": underwriting_coordinates_complete,
                "eligibility_source_sha256": rank_input["rank_program_input_sha256"],
                "coordinate_contract": (
                    "Candidate-kind-specific valuation and factor coordinates remain separate; "
                    "the existing discovery score orders research, not forecast return."
                ),
            },
            "conditional_payoff_analysis": conditional_payoff,
            "conditional_payoff_aware": conditional_payoff is not None,
            "payoff_forecast": payoff_forecast,
            "forecast_return_aware": payoff_forecast is not None,
            "state_price_aware": False,
            "gaps": sorted(set(gaps + ["market_state_prices_unidentified_from_current_public_claims"])),
            "source_refs": sorted(set(
                list(candidate.get("source_refs") or ())
                + list((valuation or {}).get("source_refs") or ())
                + list((factor or {}).get("source_refs") or ())
            )),
            "capital_authority": False,
        }
        rows.append({**body, "underwriting_row_sha256": stable_sha256(body)})
    body = {
        "schema": UNDERWRITING_INDEX_SCHEMA,
        "generated_at": discovery.get("completed_at"), "discovery_run_sha256": discovery.get("run_sha256"),
        "market_context": market, "candidate_count": len(rows),
        "ranking_eligible_count": sum(row["ranking"]["eligible"] for row in rows),
        "underwriting_coordinate_complete_count": sum(
            row["ranking"]["underwriting_coordinates_complete"] for row in rows
        ),
        "rank_program_input_sha256": rank_input["rank_program_input_sha256"],
        "conditional_payoff_aware_count": sum(row["conditional_payoff_aware"] for row in rows),
        "forecast_return_aware_count": sum(row["forecast_return_aware"] for row in rows),
        "state_price_aware_count": 0,
        "candidates": sorted(rows, key=lambda row: (
            not row["ranking"]["eligible"], row["ranking"]["rank"] or 10**9, row["candidate_id"]
        )),
        "authority": "underwriting_research_priority_only", "capital_authority": False,
    }
    return {**body, "underwriting_index_sha256": stable_sha256(body)}


def compile_workspace_underwriting_index(workspace: str | Path) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    discovery = json.loads((root / "discovery" / "latest.json").read_text(encoding="utf-8"))
    candidate_as_of = min(
        canonical_timestamp(row["as_of"], "candidate as_of")
        for row in discovery.get("candidates") or () if isinstance(row, Mapping)
    )
    snapshots = []
    for path in (root / "market_state" / "snapshots").glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != MARKET_STATE_SCHEMA:
            continue
        as_of = canonical_timestamp((payload.get("point_in_time_snapshot") or {}).get("as_of"), "market snapshot as_of")
        if timestamp_key(as_of) <= timestamp_key(candidate_as_of):
            snapshots.append((as_of, path.name, payload))
    if not snapshots:
        raise FileNotFoundError("no market-state snapshot predates the discovery candidates")
    market = max(snapshots, key=lambda row: (row[0], row[1]))[2]
    artifacts = {}
    conditional_payoffs = {}
    payoff_forecasts = {}
    for candidate in discovery.get("candidates") or ():
        valuation = candidate.get("valuation") if isinstance(candidate, Mapping) else None
        relative = (valuation or {}).get("artifact_path")
        if relative:
            path = (root / str(relative)).resolve()
            path.relative_to(root)
            artifacts[str(candidate["candidate_id"])] = json.loads(path.read_text(encoding="utf-8"))
    audit_path = root / "state_pricing" / "modeled-grid-audit.json"
    if audit_path.is_file():
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        if audit.get("discovery_run_sha256") == discovery.get("run_sha256"):
            candidate_ids = {
                str(row.get("candidate_sha256")): str(row.get("candidate_id"))
                for row in discovery.get("candidates") or () if isinstance(row, Mapping)
            }
            for row in audit.get("rows") or ():
                relative = row.get("artifact_path") if isinstance(row, Mapping) else None
                candidate_id = candidate_ids.get(str(row.get("candidate_sha256"))) if isinstance(row, Mapping) else None
                if relative and candidate_id:
                    path = (root / str(relative)).resolve()
                    path.relative_to(root)
                    conditional_payoffs[candidate_id] = json.loads(path.read_text(encoding="utf-8"))
    candidate_ids = {
        str(row.get("candidate_sha256")): str(row.get("candidate_id"))
        for row in discovery.get("candidates") or () if isinstance(row, Mapping)
    }
    for path in sorted((root / "underwriting" / "payoff_forecasts" / "results").glob("*.json")):
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        candidate_id = candidate_ids.get(str(artifact.get("candidate_sha256")))
        if candidate_id:
            current = payoff_forecasts.get(candidate_id)
            if current is None or timestamp_key(str(artifact.get("information_cutoff"))) > timestamp_key(
                str(current.get("information_cutoff"))
            ):
                payoff_forecasts[candidate_id] = artifact
    return compile_underwriting_opportunity_index(
        discovery, market, valuation_artifacts=artifacts,
        conditional_payoff_artifacts=conditional_payoffs,
        payoff_forecast_results=payoff_forecasts,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace")
    args = parser.parse_args(argv)
    print(json.dumps(compile_workspace_underwriting_index(args.workspace), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["UNDERWRITING_INDEX_SCHEMA", "compile_underwriting_opportunity_index", "compile_workspace_underwriting_index"]
