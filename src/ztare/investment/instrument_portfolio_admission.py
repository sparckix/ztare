"""Admit researched public securities to a zero-authority paper portfolio."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_finite, timestamp_key
from .factor_analysis import (
    FACTOR_ANALYSIS_SCHEMA,
    RETURN_COVARIANCE_SCHEMA,
    FactorDefinition,
    PricePoint,
    analyze_factor_exposure,
    compile_return_covariance,
    load_price_points,
)
from .fund_implementation_review import DECISION_SCHEMA as FUND_IMPLEMENTATION_REVIEW_DECISION_SCHEMA
from .paper_watch import paper_watch_decisions, verify_paper_watch_decision
from .sleeve_implementation import (
    IMPLEMENTATION_CANDIDATE_SCHEMA,
    SLEEVE_IMPLEMENTATION_FRONTIER_SCHEMA,
)
from .underwriting_adapter import MARKET_STATE_SCHEMAS
from .watchlist import WATCHLIST_RESULT_SCHEMA


INSTRUMENT_PORTFOLIO_ADMISSION_SCHEMA = (
    "jaggedthoughts-instrument-portfolio-admission-v1"
)
WORKSPACE_INSTRUMENT_PORTFOLIO_ADMISSIONS_SCHEMA = (
    "jaggedthoughts-workspace-instrument-portfolio-admissions-v1"
)
_CLOSED_BOOK_RUN_SCHEMA = "jaggedthoughts-closed-book-forecast-run-v1"
_FULL_RESEARCH_ARM = "typed_plus_full_research"
_ACTIVE_RETURN_CLAIM_SCHEMA = "jaggedthoughts-prospective-active-return-claim-v1"


def _sealed(
    raw: Mapping[str, Any], *, schema: str, digest_field: str, label: str,
) -> dict[str, Any]:
    row = dict(raw)
    if row.get("schema") != schema:
        raise ValueError(f"{label} schema must be {schema}")
    claimed = str(row.pop(digest_field, ""))
    if len(claimed) != 64 or stable_sha256(row) != claimed:
        raise ValueError(f"{label} content hash mismatch")
    return {**row, digest_field: claimed}


def _implementation(
    sleeve: Mapping[str, Any], watch: Mapping[str, Any],
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    entity = str((watch.get("entity") or {}).get("entity_id") or "").upper()
    decision_sha = str(watch.get("decision_sha256") or "")
    matches: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for sleeve_row in sleeve.get("sleeves") or ():
        sleeve_id = str(sleeve_row.get("sleeve_id") or "")
        for raw in sleeve_row.get("eligible_instruments") or ():
            instrument = dict(raw)
            if instrument.get("basis_proxy"):
                continue
            identity = dict(instrument.get("identity") or {})
            candidate = dict(instrument.get("implementation_candidate") or {})
            if (
                str(identity.get("subject_id") or "").upper() == entity
                and candidate.get("paper_decision_sha256") == decision_sha
            ):
                matches.append((sleeve_id, instrument, candidate))
    if len(matches) != 1:
        raise ValueError("paper watch must bind exactly one sleeve implementation candidate")
    sleeve_id, instrument, candidate = matches[0]
    verified = _sealed(
        candidate, schema=IMPLEMENTATION_CANDIDATE_SCHEMA,
        digest_field="implementation_candidate_sha256", label="implementation candidate",
    )
    if (
        verified.get("identity") != instrument.get("identity")
        or verified.get("paper_decision_id") != watch.get("decision_id")
        or (
            verified.get("paper_watch_proposal_sha256")
            or verified.get("proposal_sha256")
        ) != watch.get("proposal_sha256")
    ):
        raise ValueError("implementation candidate crossed paper-watch identity")
    return sleeve_id, instrument, verified


def _annualized_active_return(value: Any, horizon_days: Any) -> float:
    forecast = require_finite(value, "forecast active_return")
    horizon = int(require_finite(horizon_days, "forecast horizon_days"))
    if horizon < 1 or forecast <= -1:
        raise ValueError("forecast horizon must be positive and active return greater than -1")
    return (1.0 + forecast) ** (365.25 / horizon) - 1.0


def _latest_full_research_forecasts(
    runs: Iterable[Mapping[str, Any]], *, decision_sha256: str, compiled_at: str,
) -> tuple[dict[str, Any], ...]:
    matches: list[dict[str, Any]] = []
    cutoff = timestamp_key(compiled_at)
    for raw in runs:
        run = _sealed(
            raw, schema=_CLOSED_BOOK_RUN_SCHEMA, digest_field="run_sha256",
            label="closed-book run",
        )
        subject = dict(run.get("subject") or {})
        packet = dict(run.get("evidence_packet") or {})
        packet_subject = dict(packet.get("subject") or {})
        if (
            subject.get("subject_sha256") != decision_sha256
            or packet_subject.get("subject_sha256") != decision_sha256
        ):
            continue
        sealed_at = canonical_timestamp(run.get("sealed_at"), "closed-book sealed_at")
        if timestamp_key(sealed_at) > cutoff:
            raise ValueError("closed-book forecast is later than admission compilation")
        for raw_forecast in run.get("candidate_forecasts") or ():
            forecast = dict(raw_forecast)
            if (
                (forecast.get("explanation") or {}).get("evidence_arm") != _FULL_RESEARCH_ARM
                and forecast.get("candidate_id") != "underwriting_typed_plus_full_research"
            ):
                continue
            forecast_sha = str(forecast.pop("forecast_sha256", ""))
            if len(forecast_sha) != 64 or stable_sha256(forecast) != forecast_sha:
                raise ValueError("closed-book candidate forecast content hash mismatch")
            predicted = dict(forecast.get("predicted_values") or {})
            matches.append({
                "run_id": run.get("run_id"),
                "run_sha256": run["run_sha256"],
                "packet_sha256": packet.get("packet_sha256"),
                "forecast_id": forecast.get("candidate_id"),
                "forecast_sha256": forecast_sha,
                "sealed_at": sealed_at,
                "benchmark_entity_id": str(
                    (packet.get("benchmark") or {}).get("entity_id") or ""
                ).upper(),
                "horizon_days": int(run.get("horizon_days") or packet.get("horizon_days") or 0),
                "annualized_active_return": _annualized_active_return(
                    predicted.get("active_return"),
                    run.get("horizon_days") or packet.get("horizon_days"),
                ),
                "underperformance_probability": require_finite(
                    predicted.get("underperformance_event"),
                    "forecast underperformance_probability",
                ),
            })
    latest: dict[tuple[str, int], dict[str, Any]] = {}
    for result in matches:
        if not 0 <= result["underperformance_probability"] <= 1:
            raise ValueError("forecast underperformance_probability must be in [0, 1]")
        key = (result["benchmark_entity_id"], result["horizon_days"])
        current = latest.get(key)
        if current is None or (str(result["sealed_at"]), str(result["run_id"])) > (
            str(current["sealed_at"]), str(current["run_id"]),
        ):
            latest[key] = result
    return tuple(latest[key] for key in sorted(latest))


def _research_identity(
    watch: Mapping[str, Any], candidate: Mapping[str, Any],
) -> dict[str, Any]:
    evidence = dict(watch.get("evidence") or {})
    kind = str((watch.get("entity") or {}).get("entity_kind") or "")
    common = {
        "kind": kind,
        "candidate_leaf": evidence.get("candidate_leaf"),
        "candidate_sha256": evidence.get("candidate_sha256"),
        "dossier_leaf": evidence.get("dossier_leaf"),
        "dossier_sha256": evidence.get("dossier_sha256"),
        "factor_analysis_sha256": evidence.get("factor_analysis_sha256"),
        "underwriting_factor_analysis_sha256": evidence.get("factor_analysis_sha256"),
    }
    if kind == "public_equity":
        factor = dict((watch.get("underwriting_coordinates") or {}).get("factor") or {})
        common.update({
            "factor_analysis_sha256": factor.get("factor_analysis_sha256"),
            "underwriting_factor_analysis_sha256": factor.get(
                "factor_analysis_sha256"
            ),
            "underwriting_index_sha256": evidence.get("underwriting_index_sha256"),
            "underwriting_row_sha256": evidence.get("underwriting_row_sha256"),
            "valuation_envelope_sha256": evidence.get("valuation_envelope_sha256"),
            "business_fingerprint_sha256": evidence.get("business_fingerprint_sha256"),
            "strategy_frontier_sha256": evidence.get("strategy_frontier_sha256"),
            "modeled_grid_sha256": evidence.get("modeled_grid_sha256"),
            "state_price_result_sha256": evidence.get("state_price_result_sha256"),
        })
    elif kind == "public_fund":
        lineage = dict(candidate.get("lineage") or {})
        common.update({
            "fund_valuation_sha256": evidence.get("fund_valuation_sha256"),
            "fund_holdings_graph_sha256": evidence.get("fund_holdings_graph_sha256"),
            "fund_choice_frontier_sha256": lineage.get("fund_choice_frontier_sha256"),
            "alternative_sha256": lineage.get("alternative_sha256"),
        })
    else:
        raise ValueError("instrument admission supports public equities and public funds only")
    return common


def compile_instrument_portfolio_admission(
    *,
    paper_watch_decision: Mapping[str, Any],
    sleeve_implementation: Mapping[str, Any],
    factor_analysis: Mapping[str, Any],
    return_covariance: Mapping[str, Any],
    compiled_at: str,
    closed_book_runs: Iterable[Mapping[str, Any]] = (),
    maximum_weight: float = 0.10,
    transaction_cost_bps: float = 10.0,
    cash_expected_return: float | None = None,
    cash_hurdle_source_sha256: str | None = None,
) -> dict[str, Any]:
    """Compile a researched security into a paper-portfolio candidate."""
    watch_source = dict(paper_watch_decision)
    watch_source.pop("decision_path", None)
    if watch_source.get("schema") == FUND_IMPLEMENTATION_REVIEW_DECISION_SCHEMA:
        raise ValueError("implementation-review decisions cannot enter portfolio admission")
    watch = verify_paper_watch_decision(watch_source)
    sleeve = _sealed(
        sleeve_implementation, schema=SLEEVE_IMPLEMENTATION_FRONTIER_SCHEMA,
        digest_field="sleeve_implementation_sha256", label="sleeve implementation",
    )
    factor = _sealed(
        factor_analysis, schema=FACTOR_ANALYSIS_SCHEMA,
        digest_field="analysis_sha256", label="factor analysis",
    )
    covariance = _sealed(
        return_covariance, schema=RETURN_COVARIANCE_SCHEMA,
        digest_field="return_covariance_sha256", label="return covariance",
    )
    compiled = canonical_timestamp(compiled_at, "instrument admission compiled_at")
    entity = str((watch.get("entity") or {}).get("entity_id") or "").upper()
    kind = str((watch.get("entity") or {}).get("entity_kind") or "")
    if factor.get("candidate_entity_id") != entity:
        raise ValueError("factor analysis crossed paper-watch subject")
    expected_factor_sha = (
        ((watch.get("underwriting_coordinates") or {}).get("factor") or {}).get(
            "factor_analysis_sha256"
        )
        if kind == "public_equity" else
        (watch.get("evidence") or {}).get("factor_analysis_sha256")
    )
    if entity not in set(map(str, covariance.get("entity_ids") or ())):
        raise ValueError("return covariance does not include the paper-watch subject")
    for value, label in (
        (watch.get("activated_at"), "paper-watch activation"),
        (factor.get("as_of"), "factor analysis"),
        (factor.get("available_at"), "factor availability"),
        (covariance.get("as_of"), "return covariance"),
    ):
        if value and timestamp_key(canonical_timestamp(value, label)) > timestamp_key(compiled):
            raise ValueError(f"{label} is later than instrument admission")

    sleeve_id, instrument, candidate = _implementation(sleeve, watch)
    cap = require_finite(maximum_weight, "maximum_weight")
    costs = require_finite(transaction_cost_bps, "transaction_cost_bps")
    if not 0 < cap <= 1 or not 0 <= costs <= 1_000:
        raise ValueError("maximum weight or transaction cost is outside its allowed range")

    assumption = dict(factor.get("assumption_implied") or {})
    risk_free = assumption.get("risk_free_rate")
    factor_total = assumption.get("return_without_residual_alpha")
    factor_excess = (
        require_finite(factor_total, "factor total return")
        - require_finite(risk_free, "factor risk-free rate")
        if factor_total is not None and risk_free is not None else None
    )
    fee = (instrument.get("fees") or {}).get("expense_ratio")
    annual_fee = require_finite(fee, "expense_ratio") if fee is not None else 0.0
    if annual_fee < 0:
        raise ValueError("expense ratio cannot be negative")
    factor_net = factor_excess - annual_fee if factor_excess is not None else None
    cash_return = (
        require_finite(cash_expected_return, "cash expected return")
        if cash_expected_return is not None else None
    )
    cash_source = str(cash_hurdle_source_sha256 or "")
    if cash_return is not None and len(cash_source) != 64:
        raise ValueError("cash hurdle source must be a SHA-256 digest")
    if cash_return is not None:
        try:
            int(cash_source, 16)
        except ValueError as error:
            raise ValueError("cash hurdle source must be a SHA-256 digest") from error
    expected_total_after_fee = (
        require_finite(factor_total, "factor total return") - annual_fee
        if factor_total is not None else None
    )
    cash_excess = (
        expected_total_after_fee - cash_return
        if expected_total_after_fee is not None and cash_return is not None else None
    )

    forecasts = _latest_full_research_forecasts(
        closed_book_runs, decision_sha256=str(watch["decision_sha256"]),
        compiled_at=compiled,
    )
    hurdle_scenarios = []
    required_excess = cash_excess if kind == "public_fund" else factor_net
    if required_excess is not None:
        hurdle_scenarios.append({
            "scenario_id": (
                "factor_total_return_zero_alpha_less_fee_vs_public_cash"
                if kind == "public_fund" else "factor_required_return_zero_alpha"
            ),
            "required_excess_return_hurdle": required_excess,
            "source_sha256": factor["analysis_sha256"],
            "cash_hurdle_source_sha256": (
                cash_source if kind == "public_fund" else None
            ),
            "expected_realized_return_claim": False,
        })
    active_return_claims = []
    for forecast in forecasts:
        if not forecast["benchmark_entity_id"]:
            raise ValueError("closed-book forecast benchmark identity is absent")
        claim_body = {
            "schema": _ACTIVE_RETURN_CLAIM_SCHEMA,
            "estimand": "annualized_active_return",
            "subject_entity_id": entity,
            "benchmark_entity_id": forecast["benchmark_entity_id"],
            "value": forecast["annualized_active_return"],
            "horizon_days": forecast["horizon_days"],
            "underperformance_probability": forecast["underperformance_probability"],
            "sealed_at": forecast["sealed_at"],
            "forecast_sha256": forecast["forecast_sha256"],
            "run_sha256": forecast["run_sha256"],
            "packet_sha256": forecast["packet_sha256"],
            "paper_decision_sha256": watch["decision_sha256"],
            "candidate_sha256": (watch.get("evidence") or {}).get("candidate_sha256"),
            "dossier_sha256": (watch.get("evidence") or {}).get("dossier_sha256"),
            "authority": "prospective_shadow",
            "capital_authority": False,
        }
        active_return_claims.append({
            **claim_body, "claim_sha256": stable_sha256(claim_body),
        })
    historical = dict(factor.get("historical") or {})
    volatility = require_finite(
        (covariance.get("annualized_volatility") or {}).get(entity),
        "annualized volatility",
    )
    drawdown = require_finite(historical.get("maximum_drawdown"), "maximum drawdown")
    if volatility < 0 or not -1 <= drawdown <= 0:
        raise ValueError("historical downside inputs are invalid")
    normal_loss = min(1.0, 2.326347874 * volatility)
    downside = min(1.0, max(abs(min(0.0, drawdown)), normal_loss))

    thesis = dict((watch.get("research") or {}).get("thesis") or {})
    confidence = thesis.get("confidence")
    blockers = []
    if not candidate.get("implementation_review_admitted"):
        blockers.append("implementation_review_not_admitted")
    if not hurdle_scenarios:
        blockers.append("required_return_hurdle_absent")
    if kind == "public_fund" and cash_return is None:
        blockers.append("public_cash_hurdle_absent")
    if confidence is None:
        thesis_confidence = 0.0
        blockers.append("thesis_confidence_absent")
    else:
        thesis_confidence = require_finite(confidence, "thesis confidence")
        if not 0 <= thesis_confidence <= 1:
            raise ValueError("thesis confidence must be in [0, 1]")
    for row in hurdle_scenarios:
        row.update({
            "downside_risk": downside,
            "thesis_confidence": thesis_confidence,
        })

    spread = (instrument.get("liquidity") or {}).get("median_bid_ask_spread")
    half_spread = require_finite(spread, "median bid-ask spread") / 2 if spread is not None else 0.0
    one_way_cost = max(costs / 10_000.0, half_spread)
    valuation = dict((watch.get("underwriting_coordinates") or {}).get("valuation") or {})
    return_coordinates = list(valuation.get("return_coordinates") or ())
    state_price_sha = (watch.get("evidence") or {}).get("state_price_result_sha256")
    status = "admitted_to_research_paper_portfolio" if not blockers else "blocked"
    body = {
        "schema": INSTRUMENT_PORTFOLIO_ADMISSION_SCHEMA,
        "admission_id": f"instrument-admission:{entity}:{watch['decision_sha256'][:16]}",
        "compiled_at": compiled,
        "as_of": candidate.get("as_of") or sleeve.get("as_of"),
        "subject": {
            **dict(candidate.get("identity") or {}),
            "implementation_sleeve_id": sleeve_id,
        },
        "lineage": {
            "paper_decision_schema": watch.get("schema"),
            "paper_decision_id": watch.get("decision_id"),
            "paper_decision_sha256": watch.get("decision_sha256"),
            "proposal_sha256": watch.get("proposal_sha256"),
            "implementation_candidate_sha256": candidate[
                "implementation_candidate_sha256"
            ],
            "sleeve_implementation_sha256": sleeve[
                "sleeve_implementation_sha256"
            ],
            "underwriting_factor_analysis_sha256": expected_factor_sha,
            "allocation_factor_analysis_sha256": factor["analysis_sha256"],
            "return_covariance_sha256": covariance["return_covariance_sha256"],
        },
        "research_identity": _research_identity(watch, candidate),
        "portfolio_projection": {
            "current_weight": 0.0,
            "target_weight_cap": cap,
            "required_return_hurdle": {
                "annualized_total_after_fee": expected_total_after_fee,
                "annualized_excess": required_excess,
                "comparator": (
                    "public_cash_90_day_yield" if kind == "public_fund"
                    else "factor_risk_free_rate"
                ),
                "source_sha256": factor["analysis_sha256"],
                "expected_realized_return_claim": False,
            },
            "expected_active_return_claims": active_return_claims,
            "downside_risk": downside,
            "thesis_confidence": thesis_confidence,
            "estimated_cost_weight": cap * one_way_cost,
            "hurdle_scenarios": hurdle_scenarios,
            "factor_exposures": dict((factor.get("coefficients") or {}).get("betas") or {}),
        },
        "economic_basis": {
            "return_basis": (
                "factor_total_return_zero_alpha_less_fee_vs_public_cash"
                if kind == "public_fund" and cash_excess is not None else
                "declared_factor_premiums_zero_residual_alpha"
                if factor_net is not None else "unavailable"
            ),
            "risk_free_rate": risk_free,
            "cash_expected_return": cash_return,
            "cash_hurdle_source_sha256": cash_source or None,
            "required_total_return_after_fee": expected_total_after_fee,
            "required_excess_return_vs_factor_risk_free": factor_net,
            "required_excess_return_vs_cash": cash_excess,
            "required_return_comparator": (
                "public_cash_90_day_yield" if kind == "public_fund"
                else "factor_risk_free_rate"
            ),
            "factor_contributions": dict(assumption.get("factor_contributions") or {}),
            "historical_residual_alpha_observed": historical.get(
                "residual_alpha_annualized"
            ),
            "historical_residual_alpha_weight": 0.0,
            "annual_fee_drag": annual_fee,
            "one_way_transaction_cost": one_way_cost,
            "return_unit": "annualized_decimal",
            "required_return_hurdle_is_expected_return_claim": False,
        },
        "downside_basis": {
            "annualized_volatility": volatility,
            "historical_maximum_drawdown": drawdown,
            "normal_loss_99_proxy": normal_loss,
            "selected_downside_risk": downside,
            "history_used_as_expected_return": False,
            "factor_analysis_sha256": factor["analysis_sha256"],
            "return_covariance_sha256": covariance["return_covariance_sha256"],
            "observed_period": dict(factor.get("observed_period") or {}),
            "covariance_window": {
                "start": covariance.get("window_start"),
                "end": covariance.get("window_end"),
                "return_count": covariance.get("return_count"),
            },
        },
        "forecast_binding": (
            {
                "status": "bound_prospective_active_return_claims",
                "claim_count": len(active_return_claims),
                "horizon_days": sorted({row["horizon_days"] for row in active_return_claims}),
                "claims": [{
                    **forecast,
                    "expected_active_return_claim_sha256": claim["claim_sha256"],
                } for forecast, claim in zip(forecasts, active_return_claims, strict=True)],
                "used_as_expected_active_return_claims": True,
            }
            if forecasts else {"status": "full_research_forecast_absent"}
        ),
        "diagnostics": {
            "factor_epoch_binding": {
                "underwriting_factor_analysis_sha256": expected_factor_sha,
                "allocation_factor_analysis_sha256": factor["analysis_sha256"],
                "same_epoch": expected_factor_sha == factor["analysis_sha256"],
                "allocation_uses_current_factor_epoch": True,
            },
            "valuation_implied_return_coordinates": return_coordinates,
            "valuation_implied_return_used_as_expected_return": False,
            "state_price_result_sha256": state_price_sha,
            "state_prices_used_as_probabilities": False,
            "state_prices_used_as_expected_returns": False,
            "state_price_status_blocks_research_paper_admission": False,
            "upstream_research_residuals": list(
                watch.get("research_obligations") or ()
            ),
        },
        "eligibility": {
            "status": status,
            "blockers": sorted(set(blockers)),
            "research_paper_portfolio_candidate": not blockers,
            "paper_allocation_allowed": not blockers,
            "required_next_transition": (
                "compile_research_paper_portfolio" if not blockers
                else "close_instrument_admission_evidence"
            ),
        },
        "personalized_account_implementation": {
            "status": "blocked_private_account_context",
            "blockers": [
                "operator_household_mandate_absent",
                "account_inventory_absent",
                "current_positions_and_tax_lots_absent",
                "personal_tax_and_currency_policy_absent",
            ],
            "research_paper_admission_blocked": False,
        },
        "authority": "research_paper_portfolio_only",
        "capital_authority": False,
        "brokerage_authority": False,
        "order_routing_allowed": False,
    }
    return {**body, "admission_sha256": stable_sha256(body)}


def _json_rows(directory: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(directory.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _latest_market_basis(root: Path, compiled_at: str) -> dict[str, Any]:
    cutoff = timestamp_key(compiled_at)
    rows = [
        row for row in _json_rows(root / "market_state" / "snapshots")
        if row.get("schema") in MARKET_STATE_SCHEMAS
        and timestamp_key(canonical_timestamp(
            (row.get("point_in_time_snapshot") or {}).get("as_of"),
            "market-state as_of",
        )) <= cutoff
    ]
    if not rows:
        raise FileNotFoundError("current market-state snapshot absent")
    raw = max(rows, key=lambda row: (
        str((row.get("point_in_time_snapshot") or {}).get("as_of") or ""),
        str(row.get("snapshot_artifact_sha256") or ""),
    ))
    snapshot = _sealed(
        raw, schema=str(raw["schema"]), digest_field="snapshot_artifact_sha256",
        label="market-state snapshot",
    )
    state = dict(snapshot.get("state") or {})
    nominal = require_finite(
        state.get("implied_nominal_equity_return"), "implied nominal equity return",
    )
    erp = require_finite(
        state.get("nominal_implied_equity_risk_premium", state.get(
            "implied_equity_risk_premium"
        )), "implied equity risk premium",
    )
    return {
        "as_of": (snapshot.get("point_in_time_snapshot") or {}).get("as_of"),
        "snapshot_artifact_sha256": snapshot["snapshot_artifact_sha256"],
        "implied_nominal_equity_return": nominal,
        "implied_equity_risk_premium": erp,
        "risk_free_rate": nominal - erp,
        "risk_free_derivation": "implied_nominal_equity_return - implied_equity_risk_premium",
        "cash_expected_return": require_finite(
            (snapshot.get("cash_yields") or {}).get("90"),
            "90-day public cash yield",
        ),
        "cash_hurdle_source_sha256": snapshot["snapshot_artifact_sha256"],
    }


def _current_fund_factors(
    root: Path, compiled_at: str,
) -> dict[str, tuple[dict[str, Any], str]]:
    cutoff = timestamp_key(compiled_at)
    matches: dict[str, tuple[str, str, dict[str, Any], str]] = {}
    for raw in _json_rows(root / "watchlists" / "results"):
        if raw.get("schema") != WATCHLIST_RESULT_SCHEMA:
            continue
        as_of = canonical_timestamp(raw.get("as_of"), "fund watchlist as_of")
        if timestamp_key(as_of) > cutoff:
            continue
        watchlist = _sealed(
            raw, schema=WATCHLIST_RESULT_SCHEMA, digest_field="watchlist_sha256",
            label="fund watchlist",
        )
        for candidate in watchlist.get("candidates") or ():
            entity = str(candidate.get("entity_id") or "").upper()
            analysis = candidate.get("analysis")
            if not entity or not isinstance(analysis, Mapping):
                continue
            factor = _sealed(
                analysis, schema=FACTOR_ANALYSIS_SCHEMA, digest_field="analysis_sha256",
                label=f"fund factor analysis {entity}",
            )
            if str(factor.get("candidate_entity_id") or "").upper() != entity:
                raise ValueError("fund factor analysis crossed watchlist identity")
            value = (as_of, str(watchlist.get("watchlist_id") or ""), factor,
                     watchlist["watchlist_sha256"])
            if entity not in matches or value[:2] > matches[entity][:2]:
                matches[entity] = value
    return {entity: (row[2], row[3]) for entity, row in matches.items()}


def _price_series(
    points: Iterable[PricePoint], entity_ids: Iterable[str],
) -> dict[str, dict[str, float]]:
    wanted = tuple(sorted(set(entity_ids)))
    rows: dict[str, dict[str, tuple[tuple[str, str, str], float]]] = {
        entity: {} for entity in wanted
    }
    for point in points:
        entity = point.entity_id.upper()
        if entity not in rows:
            continue
        rank = (point.available_at, point.observed_at, point.observation_id)
        current = rows[entity].get(point.date_key)
        if current is None or rank > current[0]:
            rows[entity][point.date_key] = (rank, point.value)
    return {
        entity: {day: value for day, (_rank, value) in sorted(series.items())}
        for entity, series in rows.items()
    }


def _watch_error(
    watch: Mapping[str, Any], *, stage: str, error: Exception,
) -> dict[str, Any]:
    return {
        "schema": "jaggedthoughts-instrument-portfolio-admission-error-v1",
        "decision_id": watch.get("decision_id"),
        "decision_sha256": watch.get("decision_sha256"),
        "entity_id": (watch.get("entity") or {}).get("entity_id"),
        "entity_kind": (watch.get("entity") or {}).get("entity_kind"),
        "stage": stage,
        "error_type": type(error).__name__,
        "message": str(error),
    }


def compile_workspace_instrument_portfolio_admissions(
    root: str | Path,
    sleeve_implementation: Mapping[str, Any],
    compiled_at: str,
) -> dict[str, Any]:
    """Reprice current paper watches into one source-bound paper candidate set."""
    workspace = Path(root).expanduser().resolve()
    compiled = canonical_timestamp(compiled_at, "workspace admissions compiled_at")
    watches = paper_watch_decisions(workspace)
    entity_ids = tuple(sorted({
        str((watch.get("entity") or {}).get("entity_id") or "").upper()
        for watch in watches
    } - {""}))
    errors: list[dict[str, Any]] = []
    admissions: list[dict[str, Any]] = []

    try:
        points = load_price_points(
            workspace / "data" / "observations.csv", as_of=compiled,
            metric_id="adjusted_price", entity_ids=(*entity_ids, "SPY"),
        )
        covariance = compile_return_covariance(
            price_series=_price_series(points, entity_ids), as_of=compiled,
        )
        used_points = [
            point for point in points
            if point.entity_id.upper() in entity_ids
            and covariance["window_start"] <= point.date_key <= covariance["window_end"]
        ]
        price_history = {
            "metric_id": "adjusted_price",
            "observation_count": len(used_points),
            "observation_tuples_sha256": stable_sha256(sorted(
                (point.entity_id, point.observed_at, point.available_at, point.value,
                 point.observation_id, point.source_ref)
                for point in used_points
            )),
            "source_refs": sorted({point.source_ref for point in used_points}),
        }
        covariance_error = None
    except (FileNotFoundError, KeyError, TypeError, ValueError) as error:
        points, covariance, price_history, covariance_error = (), None, None, error

    try:
        market_basis, market_error = _latest_market_basis(workspace, compiled), None
    except (FileNotFoundError, KeyError, TypeError, ValueError) as error:
        market_basis, market_error = None, error
    try:
        fund_factors, fund_error = _current_fund_factors(workspace, compiled), None
    except (FileNotFoundError, KeyError, TypeError, ValueError) as error:
        fund_factors, fund_error = {}, error
    runs = _json_rows(workspace / "closed_book" / "runs")
    factor_sources = []

    for watch in watches:
        entity = str((watch.get("entity") or {}).get("entity_id") or "").upper()
        kind = str((watch.get("entity") or {}).get("entity_kind") or "")
        if covariance_error is not None:
            errors.append(_watch_error(
                watch, stage="shared_return_covariance", error=covariance_error,
            ))
            continue
        try:
            if kind == "public_equity":
                if market_error is not None:
                    raise market_error
                if market_basis is None:
                    raise ValueError("current equity CAPM basis absent")
                factor = analyze_factor_exposure(
                    analysis_id=f"allocation-capm:{entity}:{compiled[:10]}",
                    candidate_entity_id=entity,
                    factors=(FactorDefinition(
                        factor_id="market", long_entity_id="SPY",
                        expected_annual_premium=market_basis[
                            "implied_equity_risk_premium"
                        ],
                    ),),
                    price_points=points,
                    as_of=compiled,
                    risk_free_rate=market_basis["risk_free_rate"],
                    alpha_persistence_weight=0.0,
                )
                factor_source = market_basis["snapshot_artifact_sha256"]
            else:
                if fund_error is not None:
                    raise fund_error
                factor, factor_source = fund_factors[entity]
            exact_runs = [
                run for run in runs
                if (run.get("subject") or {}).get("subject_sha256")
                == watch.get("decision_sha256")
            ]
            admission = compile_instrument_portfolio_admission(
                paper_watch_decision=watch,
                sleeve_implementation=sleeve_implementation,
                factor_analysis=factor,
                return_covariance=covariance,
                compiled_at=compiled,
                closed_book_runs=exact_runs,
                cash_expected_return=(market_basis or {}).get("cash_expected_return"),
                cash_hurdle_source_sha256=(market_basis or {}).get(
                    "cash_hurdle_source_sha256"
                ),
            )
            admissions.append(admission)
            factor_sources.append({
                "entity_id": entity,
                "entity_kind": kind,
                "allocation_factor_analysis_sha256": factor["analysis_sha256"],
                "source_artifact_sha256": factor_source,
            })
        except (AssertionError, FileNotFoundError, KeyError, TypeError, ValueError) as error:
            errors.append(_watch_error(watch, stage="allocation_factor_or_admission", error=error))

    admitted = sum(
        row["eligibility"]["status"] == "admitted_to_research_paper_portfolio"
        for row in admissions
    )
    body = {
        "schema": WORKSPACE_INSTRUMENT_PORTFOLIO_ADMISSIONS_SCHEMA,
        "compiled_at": compiled,
        "watch_count": len(watches),
        "admitted_count": admitted,
        "blocked_count": len(watches) - admitted,
        "error_count": len(errors),
        "shared_return_covariance_sha256": (
            covariance.get("return_covariance_sha256") if covariance else None
        ),
        "adjusted_price_history": price_history,
        "equity_capm_basis": market_basis,
        "allocation_factor_sources": sorted(factor_sources, key=lambda row: row["entity_id"]),
        "admissions": sorted(admissions, key=lambda row: str(row["subject"]["subject_id"])),
        "errors": sorted(errors, key=lambda row: str(row.get("entity_id") or "")),
        "authority": "research_paper_portfolio_only",
        "capital_authority": False,
        "brokerage_authority": False,
        "order_routing_allowed": False,
    }
    return {**body, "workspace_admissions_sha256": stable_sha256(body)}


__all__ = [
    "INSTRUMENT_PORTFOLIO_ADMISSION_SCHEMA",
    "WORKSPACE_INSTRUMENT_PORTFOLIO_ADMISSIONS_SCHEMA",
    "compile_instrument_portfolio_admission",
    "compile_workspace_instrument_portfolio_admissions",
]
