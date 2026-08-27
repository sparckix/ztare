"""Risk/cost comparison of public funds before portfolio authority exists."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_finite, timestamp_key
from .factor_analysis import PricePoint, compile_return_covariance, load_price_points
from .fund_lookthrough_optimizer import run_minimum_call_cover
from .household_allocation import CAPITAL_MARKET_BASIS_SCHEMA
from .sleeve_implementation import (
    IMPLEMENTATION_CANDIDATE_SCHEMA,
    SLEEVE_IMPLEMENTATION_FRONTIER_SCHEMA,
    compile_workspace_sleeve_implementation_frontier,
)


FUND_SLEEVE_COMPARISON_SCHEMA = "jaggedthoughts-fund-sleeve-comparison-v1"
FUND_PROGRAM_TOURNAMENT_INPUT_SCHEMA = (
    "jaggedthoughts-fund-program-tournament-input-v1"
)
FUND_LOOKTHROUGH_ACQUISITION_PLAN_SCHEMA = (
    "jaggedthoughts-fund-lookthrough-acquisition-plan-v1"
)
PORTFOLIO_EVIDENCE_ACQUISITION_SCHEMA = (
    "jaggedthoughts-portfolio-evidence-acquisition-contract-v1"
)
_US_HOLDING_SUFFIXES = ("@NYSE", "@NASDAQ", "@CBOE BZX", "@NYSE MKT LLC")


def canonical_public_issuer_id(identifier: Any) -> str:
    """Normalize provider-decorated US holding identifiers without guessing ADRs."""
    value = str(identifier or "").strip().upper()
    for suffix in _US_HOLDING_SUFFIXES:
        if value.endswith(suffix):
            return value[:-len(suffix)]
    return value


def _sealed(
    raw: Mapping[str, Any], *, schema: str, digest_field: str, label: str,
) -> dict[str, Any]:
    payload = dict(raw)
    if payload.get("schema") != schema:
        raise ValueError(f"{label} schema must be {schema}")
    digest = str(payload.pop(digest_field, ""))
    if len(digest) != 64 or stable_sha256(payload) != digest:
        raise ValueError(f"{label} content hash mismatch")
    return {**payload, digest_field: digest}


def _price_series(
    points: Iterable[PricePoint], entity_ids: set[str], as_of: str,
) -> tuple[dict[str, dict[str, float]], dict[str, list[str]]]:
    cutoff = timestamp_key(as_of)
    latest: dict[tuple[str, str], PricePoint] = {}
    for point in points:
        entity = point.entity_id.upper()
        if (
            entity not in entity_ids
            or timestamp_key(point.available_at) > cutoff
            or timestamp_key(point.observed_at) > cutoff
        ):
            continue
        key = (entity, point.date_key)
        current = latest.get(key)
        if current is None or (
            point.available_at, point.observed_at, point.observation_id
        ) > (current.available_at, current.observed_at, current.observation_id):
            latest[key] = point
    series = {entity: {} for entity in sorted(entity_ids)}
    refs = {entity: [] for entity in sorted(entity_ids)}
    for (entity, day), point in sorted(latest.items()):
        series[entity][day] = point.value
        refs[entity].extend((point.observation_id, point.source_ref))
    return series, {key: sorted(set(value)) for key, value in refs.items()}


def _dominates(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    maximize = ("factor_implied_return_less_expense",)
    minimize = (
        "annualized_volatility", "drawdown_severity", "expense_ratio",
        "half_spread_entry_cost_proxy",
    )
    a, b = left["comparison_metrics"], right["comparison_metrics"]
    no_worse = (
        all(float(a[key]) >= float(b[key]) - 1e-12 for key in maximize)
        and all(float(a[key]) <= float(b[key]) + 1e-12 for key in minimize)
    )
    better = (
        any(float(a[key]) > float(b[key]) + 1e-12 for key in maximize)
        or any(float(a[key]) < float(b[key]) - 1e-12 for key in minimize)
    )
    return no_worse and better


def _cash_hurdle(
    raw: Mapping[str, Any] | None, *, implementation: Mapping[str, Any], as_of: str | None,
) -> dict[str, Any]:
    if raw is None:
        return {"status": "absent", "blocker": "public_cash_hurdle_absent"}
    basis = _sealed(
        raw, schema=CAPITAL_MARKET_BASIS_SCHEMA, digest_field="basis_sha256",
        label="capital-market basis",
    )
    if basis["basis_sha256"] != implementation.get("basis_sha256"):
        raise ValueError("fund comparison and cash hurdle use different capital-market bases")
    if as_of and timestamp_key(str(basis.get("as_of") or "")) > timestamp_key(as_of):
        raise ValueError("cash hurdle was unavailable at the fund comparison epoch")
    scenarios = [
        dict(row) for row in basis.get("return_scenarios") or ()
        if row.get("scenario_id") == "current_source_anchor"
    ]
    if len(scenarios) != 1:
        raise ValueError("capital-market basis requires one current_source_anchor scenario")
    scenario = scenarios[0]
    expected_return = require_finite(
        (scenario.get("expected_returns") or {}).get("cash"),
        "public cash expected return",
    )
    body = {
        "status": "available",
        "sleeve_id": "cash",
        "expected_annual_return": expected_return,
        "scenario_id": "current_source_anchor",
        "basis_sha256": basis["basis_sha256"],
        "source_refs": list(scenario.get("source_refs") or ()),
        "historical_mean_used_as_forecast": False,
        "expected_return_claim": False,
    }
    return {**body, "cash_hurdle_sha256": stable_sha256(body)}


def _portfolio_evidence_acquisition_contract(
    *, implementation: Mapping[str, Any], sleeves: Iterable[Mapping[str, Any]],
    risk_basis: Mapping[str, Any] | None, as_of: str | None,
) -> dict[str, Any]:
    programs = [
        row for sleeve in sleeves for row in sleeve.get("programs") or ()
    ]
    missing: dict[tuple[str, str], dict[str, set[str]]] = {}

    def add(domain: str, gap: str, program: Mapping[str, Any]) -> None:
        bucket = missing.setdefault((domain, str(gap)), {
            "program_ids": set(), "subject_ids": set(),
        })
        bucket["program_ids"].add(str(program["program_id"]))
        bucket["subject_ids"].add(str(program["identity"]["subject_id"]))

    for program in programs:
        evidence = program["portfolio_evidence"]
        for gap in evidence["core_gaps"]:
            add("comparison_core", gap, program)
        for gap in evidence["lookthrough_gaps"]:
            add("fund_lookthrough", gap, program)
        for gap in evidence["tax_currency_gaps"]:
            add("tax_currency", gap, program)
        if not program["implementation_review_admitted"]:
            add("implementation_review", "implementation_review_not_admitted", program)

    unassigned_equities = [
        row for row in implementation.get("unassigned_evidence") or ()
        if (row.get("identity") or {}).get("entity_kind") == "public_equity"
    ]
    if unassigned_equities:
        missing[("equity_sleeve_identity", "broad_sleeve_fit_unbound")] = {
            "program_ids": set(),
            "subject_ids": {
                str(row["identity"]["subject_id"]) for row in unassigned_equities
            },
        }

    owners = {
        "comparison_core": (
            "ztare.investment.workspace.refresh_workspace_sources",
            "periodic_discovery_poll", "implemented",
        ),
        "fund_lookthrough": (
            "ztare.investment.workspace.run_workspace_fund_lookthrough_acquisition",
            "periodic_discovery_poll", "implemented",
        ),
        "tax_currency": (
            "compile_instrument_return_downside_tax_currency_contract",
            None, "adapter_absent",
        ),
        "implementation_review": (
            "paper_watch_and_operator_review",
            "paper_watch_transition", "human_gate_required",
        ),
        "equity_sleeve_identity": (
            "compile_source_bound_broad_sleeve_fit",
            None, "adapter_absent",
        ),
    }
    requirements = []
    for (domain, gap), subjects in sorted(missing.items()):
        owner, activation, adapter_status = owners[domain]
        requirements.append({
            "requirement_id": f"{domain}:{gap}",
            "domain": domain,
            "missing_field": gap,
            "subject_ids": sorted(subjects["subject_ids"]),
            "program_ids": sorted(subjects["program_ids"]),
            "acquisition_owner": owner,
            "activation": activation,
            "adapter_status": adapter_status,
        })

    private_requirements = []
    if not implementation.get("policy_consumed"):
        private_requirements.append({
            "requirement_id": "operator_private:capital_mandate",
            "owner": "operator_private_policy",
            "status": "absent",
        })
    private_requirements.append({
        "requirement_id": "operator_private:current_portfolio_state",
        "owner": "operator_private_book",
        "status": "absent",
    })
    complete_ids = sorted(
        row["program_id"] for row in programs
        if row["portfolio_evidence"]["portfolio_policy_evidence_complete"]
        and row["implementation_review_admitted"]
    )
    machine_fillable = [
        row["requirement_id"] for row in requirements
        if row["adapter_status"] == "implemented"
    ]
    next_public_activation = next(({
        "requirement_id": row["requirement_id"],
        "owner": row["acquisition_owner"],
        "activation": row["activation"],
        "subject_ids": row["subject_ids"],
    } for domain in ("fund_lookthrough", "comparison_core")
        for row in requirements if row["domain"] == domain), None)
    body = {
        "schema": PORTFOLIO_EVIDENCE_ACQUISITION_SCHEMA,
        "as_of": as_of,
        "population": {
            "fund_program_ids": sorted(row["program_id"] for row in programs),
            "unassigned_public_equity_ids": sorted(
                str(row["identity"]["subject_id"]) for row in unassigned_equities
            ),
        },
        "kernel_ready": {
            "risk_basis_sha256": (risk_basis or {}).get("return_covariance_sha256"),
            "risk_basis_entity_ids": list((risk_basis or {}).get("entity_ids") or ()),
            "factor_decomposition_program_count": sum(
                bool(row["portfolio_evidence"]["factor_decomposition"])
                for row in programs
            ),
            "fee_liquidity_program_count": sum(
                row["portfolio_evidence"]["fees_liquidity"]["expense_ratio"] is not None
                and row["portfolio_evidence"]["fees_liquidity"]["median_bid_ask_spread"] is not None
                for row in programs
            ),
            "unsupported_residual_alpha_credit": False,
        },
        "public_evidence_requirements": requirements,
        "operator_private_requirements": private_requirements,
        "machine_fillable_requirement_ids": machine_fillable,
        "adapter_gap_requirement_ids": [
            row["requirement_id"] for row in requirements
            if row["adapter_status"] == "adapter_absent"
        ],
        "portfolio_evidence_complete_program_ids": complete_ids,
        "next_public_activation": next_public_activation,
        "construction_ready": bool(
            complete_ids and implementation.get("policy_consumed")
            and not private_requirements
        ),
        "capital_authority": False,
    }
    return {**body, "acquisition_contract_sha256": stable_sha256(body)}


def compile_fund_sleeve_comparison(
    *,
    sleeve_implementation: Mapping[str, Any],
    price_points: Iterable[PricePoint],
    min_returns: int = 120,
    lookback_returns: int = 756,
    diagonal_shrinkage: float = 0.25,
    holdings_quality: Mapping[str, Mapping[str, Any]] | None = None,
    capital_market_basis: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare one-for-one fund implementations; do not choose portfolio weights."""
    implementation = _sealed(
        sleeve_implementation, schema=SLEEVE_IMPLEMENTATION_FRONTIER_SCHEMA,
        digest_field="sleeve_implementation_sha256", label="sleeve implementation",
    )
    instruments: list[tuple[str, dict[str, Any]]] = []
    epochs = [str(implementation.get("as_of") or "")]
    seen: set[str] = set()
    for sleeve in implementation.get("sleeves") or ():
        sleeve_id = str(sleeve.get("sleeve_id") or "")
        for raw in sleeve.get("eligible_instruments") or ():
            if raw.get("basis_proxy"):
                continue
            row = dict(raw)
            entity_kind = str((row.get("identity") or {}).get("entity_kind") or "")
            if entity_kind == "public_equity":
                continue
            if entity_kind != "public_fund":
                raise ValueError(f"unsupported sleeve instrument identity: {entity_kind}")
            entity = str((row.get("identity") or {}).get("subject_id") or "").upper()
            if not entity or entity in seen:
                raise ValueError("fund comparison requires unique nonempty fund identities")
            seen.add(entity)
            candidate = _sealed(
                dict(row.get("implementation_candidate") or {}),
                schema=IMPLEMENTATION_CANDIDATE_SCHEMA,
                digest_field="implementation_candidate_sha256",
                label=f"implementation candidate {entity}",
            )
            if candidate.get("identity") != row.get("identity"):
                raise ValueError(f"implementation candidate identity differs for {entity}")
            row["implementation_candidate"] = candidate
            instruments.append((sleeve_id, row))
            epochs.extend((str(candidate.get("as_of") or ""), str(
                (candidate.get("identity") or {}).get("implementation_epoch") or ""
            )))
    valid_epochs = [canonical_timestamp(value, "fund comparison evidence epoch")
                    for value in epochs if value]
    as_of = max(valid_epochs, key=timestamp_key) if valid_epochs else None
    cash_hurdle = _cash_hurdle(
        capital_market_basis, implementation=implementation, as_of=as_of,
    )

    entity_ids = {str(row["identity"]["subject_id"]).upper() for _, row in instruments}
    series: dict[str, dict[str, float]] = {}
    evidence_refs: dict[str, list[str]] = {}
    risk_basis = None
    risk_error = None
    if entity_ids and as_of:
        series, evidence_refs = _price_series(price_points, entity_ids, as_of)
        risk_entities = {
            entity for entity, prices in series.items() if len(prices) >= min_returns + 1
        }
        if risk_entities:
            try:
                risk_basis = compile_return_covariance(
                    price_series={key: series[key] for key in sorted(risk_entities)},
                    as_of=as_of,
                    min_returns=min_returns,
                    lookback_returns=lookback_returns,
                    diagonal_shrinkage=diagonal_shrinkage,
                )
            except ValueError as error:
                risk_error = str(error)

    risk_ids = set((risk_basis or {}).get("entity_ids") or ())
    volatilities = dict((risk_basis or {}).get("annualized_volatility") or {})
    correlations = dict((risk_basis or {}).get("correlations") or {})
    by_sleeve: dict[str, list[dict[str, Any]]] = {
        str(row.get("sleeve_id") or ""): []
        for row in implementation.get("sleeves") or ()
    }
    for sleeve_id, instrument in instruments:
        entity = str(instrument["identity"]["subject_id"]).upper()
        candidate = instrument["implementation_candidate"]
        economics = dict(instrument.get("economic_coordinates") or {})
        tax_currency = dict(instrument.get("tax_currency_coordinates") or {})
        lookthrough_quality = dict((holdings_quality or {}).get(entity) or {})
        fees = dict(instrument.get("fees") or {})
        liquidity = dict(instrument.get("liquidity") or {})
        expense = fees.get("expense_ratio")
        implied = economics.get("factor_implied_return")
        spread = liquidity.get("median_bid_ask_spread")
        drawdown = economics.get("drawdown_resilience")
        blockers = list(map(str, candidate.get("evidence_gaps") or ()))
        for missing, value in (
            ("return_covariance_absent", volatilities.get(entity)),
            ("factor_implied_return_absent", implied),
            ("expense_ratio_absent", expense),
            ("median_bid_ask_spread_absent", spread),
            ("maximum_drawdown_absent", drawdown),
        ):
            if value is None:
                blockers.append(missing)
        ready = not any(value is None for value in (
            volatilities.get(entity), implied, expense, spread, drawdown,
        ))
        peer_overlap = list(instrument.get("overlap") or ())
        metrics = ({
            "factor_implied_return_less_expense": float(implied) - float(expense),
            "annualized_volatility": float(volatilities[entity]),
            "drawdown_severity": abs(min(0.0, float(drawdown))),
            "expense_ratio": float(expense),
            "half_spread_entry_cost_proxy": float(spread) / 2.0,
        } if ready else None)
        core_gaps = []
        if not instrument.get("factor_fit", {}).get("exposures"):
            core_gaps.append("factor_decomposition_absent")
        for field in ("earnings_power_margin", "implied_growth"):
            if economics.get(field) is None:
                core_gaps.append(f"current_valuation_{field}_absent")
        if not ready:
            core_gaps.append("risk_cost_comparison_incomplete")
        lookthrough_gaps = []
        if lookthrough_quality.get("status") != "sufficient_for_cross_fund_comparison":
            lookthrough_gaps.append(
                str(lookthrough_quality.get("status") or "holdings_weighted_earnings_power_absent")
            )
        tax_currency_gaps = [
            f"{field}_absent" for field in (
                "distribution_tax_character", "foreign_withholding_tax_rate",
                "trading_currency", "underlying_currency_exposure",
            ) if tax_currency.get(field) is None
        ]
        if fees.get("portfolio_turnover") is None:
            tax_currency_gaps.append("portfolio_turnover_absent")
        core_ready = not core_gaps
        cash_excess = (
            float(metrics["factor_implied_return_less_expense"])
            - float(cash_hurdle["expected_annual_return"])
            if core_ready and metrics is not None
            and cash_hurdle.get("status") == "available" else None
        )
        lookthrough_ready = core_ready and not lookthrough_gaps
        portfolio_ready = lookthrough_ready and not tax_currency_gaps
        body = {
            "program_id": f"fund-sleeve:{sleeve_id}:{entity}:{as_of}",
            "identity": instrument["identity"],
            "sleeve_id": sleeve_id,
            "comparison_unit": {
                "kind": "one_for_one_sleeve_substitution",
                "normalized_implementation_fraction": 1.0,
                "portfolio_weight": None,
            },
            "comparison_metrics": metrics,
            "cash_comparison": {
                "status": (
                    "positive_factor_assumption_spread" if cash_excess is not None and cash_excess > 0
                    else "cash_hurdle_not_cleared" if cash_excess is not None
                    else "evidence_blocked"
                ),
                "expected_excess_return": cash_excess,
                "cash_hurdle_sha256": cash_hurdle.get("cash_hurdle_sha256"),
                "residual_alpha_credit": 0.0,
                "expected_return_claim": False,
            },
            "factor_exposures": dict((instrument.get("factor_fit") or {}).get("exposures") or {}),
            "factor_uncertainty": dict(
                (instrument.get("factor_fit") or {}).get(
                    "residual_alpha_uncertainty"
                ) or {}
            ),
            "holdings": {
                **dict(instrument.get("holdings_coordinates") or {}),
                "peer_overlap": peer_overlap,
                "maximum_disclosed_peer_overlap": max(
                    (float(row.get("weighted_overlap") or 0) for row in peer_overlap),
                    default=None,
                ),
            },
            "portfolio_evidence": {
                "factor_decomposition": dict(
                    (instrument.get("factor_fit") or {}).get("exposures") or {}
                ),
                "residual_alpha_uncertainty": dict(
                    (instrument.get("factor_fit") or {}).get(
                        "residual_alpha_uncertainty"
                    ) or {}
                ),
                "current_valuation": {
                    "earnings_power_margin": economics.get("earnings_power_margin"),
                    "implied_growth": economics.get("implied_growth"),
                    "factor_implied_return": economics.get("factor_implied_return"),
                    "expected_return_claim": False,
                },
                "holdings_weighted_earnings_power": lookthrough_quality,
                "fees_liquidity": {
                    "expense_ratio": expense,
                    "portfolio_turnover": fees.get("portfolio_turnover"),
                    "median_bid_ask_spread": spread,
                    "average_daily_volume_30d": liquidity.get("average_daily_volume_30d"),
                    "fund_net_assets": liquidity.get("fund_net_assets"),
                },
                "tax_currency": tax_currency,
                "same_information_core_ready": core_ready,
                "lookthrough_quality_ready": lookthrough_ready,
                "portfolio_policy_evidence_complete": portfolio_ready,
                "core_gaps": sorted(set(core_gaps)),
                "lookthrough_gaps": sorted(set(lookthrough_gaps)),
                "tax_currency_gaps": sorted(set(tax_currency_gaps)),
            },
            "liquidity": liquidity,
            "internal_portfolio_turnover": fees.get("portfolio_turnover"),
            "correlations_to_compared_funds": dict(correlations.get(entity) or {}),
            "price_evidence_refs": evidence_refs.get(entity, []),
            "fund_choice_frontier_status": instrument.get("fund_frontier_status"),
            "comparison_eligible": ready,
            "implementation_review_admitted": bool(
                candidate.get("implementation_review_admitted")
            ),
            "portfolio_candidate": bool(candidate.get("portfolio_candidate")),
            "blockers": sorted(set(blockers)),
            "implementation_candidate_sha256": candidate["implementation_candidate_sha256"],
            "capital_authority": False,
        }
        by_sleeve.setdefault(sleeve_id, []).append(body)

    sleeves = []
    admitted_frontier_ids: list[str] = []
    for source in implementation.get("sleeves") or ():
        sleeve_id = str(source.get("sleeve_id") or "")
        rows = sorted(by_sleeve.get(sleeve_id, ()), key=lambda row: row["program_id"])
        eligible = [row for row in rows if row["comparison_eligible"]]
        frontier_ids = sorted(
            row["program_id"] for row in eligible
            if not any(_dominates(other, row) for other in eligible if other is not row)
        )
        for row in rows:
            row["risk_cost_frontier_status"] = (
                "frontier" if row["program_id"] in frontier_ids else
                "dominated" if row["comparison_eligible"] else "evidence_blocked"
            )
            row["dominated_by_program_ids"] = sorted(
                other["program_id"] for other in eligible
                if other is not row and _dominates(other, row)
            ) if row["comparison_eligible"] else []
            row["program_sha256"] = stable_sha256(row)
        admitted = [
            row for row in eligible if row["implementation_review_admitted"]
        ]
        admitted_ids = sorted(
            row["program_id"] for row in admitted
            if not any(_dominates(other, row) for other in admitted if other is not row)
        )
        admitted_frontier_ids.extend(admitted_ids)
        sleeves.append({
            "sleeve_id": sleeve_id,
            "comparison_status": (
                "implementation_review_ready" if admitted_ids else
                "research_comparison_only" if frontier_ids else
                "risk_cost_evidence_blocked"
            ),
            "programs": rows,
            "risk_cost_frontier_program_ids": frontier_ids,
            "implementation_review_frontier_program_ids": admitted_ids,
        })

    tournament_sleeves = []
    for sleeve in sleeves:
        programs = [{
            "program_id": row["program_id"],
            "program_sha256": row["program_sha256"],
            "entity_id": row["identity"]["subject_id"],
            "same_information_core_ready": row["portfolio_evidence"][
                "same_information_core_ready"
            ],
            "lookthrough_quality_ready": row["portfolio_evidence"][
                "lookthrough_quality_ready"
            ],
            "portfolio_policy_evidence_complete": row["portfolio_evidence"][
                "portfolio_policy_evidence_complete"
            ],
            "risk_cost_frontier_status": row["risk_cost_frontier_status"],
            "ranking_coordinates": {
                "factor_implied_return_less_expense": (
                    row.get("comparison_metrics") or {}
                ).get("factor_implied_return_less_expense"),
                "aggregate_earnings_power_margin": row["portfolio_evidence"][
                    "current_valuation"
                ].get("earnings_power_margin"),
                "holdings_weighted_durable_earnings_power": row["portfolio_evidence"][
                    "holdings_weighted_earnings_power"
                ].get("durable_earnings_power"),
                "factor_expected_excess_return_vs_cash": row[
                    "cash_comparison"
                ].get("expected_excess_return"),
            },
            "evidence_gaps": sorted(set(
                row["portfolio_evidence"]["core_gaps"]
                + row["portfolio_evidence"]["lookthrough_gaps"]
                + row["portfolio_evidence"]["tax_currency_gaps"]
            )),
        } for row in sleeve["programs"]]
        tournament_sleeves.append({
            "sleeve_id": sleeve["sleeve_id"],
            "programs": programs,
            "core_candidate_program_ids": [
                row["program_id"] for row in programs
                if row["same_information_core_ready"]
            ],
            "lookthrough_candidate_program_ids": [
                row["program_id"] for row in programs
                if row["lookthrough_quality_ready"]
            ],
            "portfolio_policy_candidate_program_ids": [
                row["program_id"] for row in programs
                if row["portfolio_policy_evidence_complete"]
            ],
            "cash_hurdle_candidate_program_ids": [
                row["program_id"] for row in programs
                if row["same_information_core_ready"]
                and row["risk_cost_frontier_status"] == "frontier"
                and (row["ranking_coordinates"].get(
                    "factor_expected_excess_return_vs_cash"
                ) or 0.0) > 0
            ],
        })
    program_count = sum(len(row["programs"]) for row in tournament_sleeves)
    core_candidate_count = sum(
        len(row["core_candidate_program_ids"]) for row in tournament_sleeves
    )
    lookthrough_candidate_count = sum(
        len(row["lookthrough_candidate_program_ids"]) for row in tournament_sleeves
    )
    portfolio_candidate_count = sum(
        len(row["portfolio_policy_candidate_program_ids"])
        for row in tournament_sleeves
    )
    cash_candidate_ids = sorted(
        program_id for row in tournament_sleeves
        for program_id in row["cash_hurdle_candidate_program_ids"]
    )
    cash_activation_rows = []
    for sleeve in sleeves:
        candidates = sorted(
            (
                row for row in sleeve["programs"]
                if row["risk_cost_frontier_status"] == "frontier"
                and (row["cash_comparison"].get("expected_excess_return") or 0.0) > 0
            ),
            key=lambda row: (
                -float(row["cash_comparison"]["expected_excess_return"]),
                str(row["identity"]["subject_id"]),
            ),
        )
        cash_activation_rows.extend({
            "research_priority_rank_within_sleeve": rank,
            "sleeve_id": sleeve["sleeve_id"],
            "entity_id": row["identity"]["subject_id"],
            "program_id": row["program_id"],
            "expected_excess_return_vs_cash": row["cash_comparison"][
                "expected_excess_return"
            ],
            "ranking_semantics": "factor_assumption_spread_research_priority",
        } for rank, row in enumerate(candidates, 1))
    prospective_ranking_ticket_count = sum(
        2 if len(row["core_candidate_program_ids"]) >= 2 else 0
        for row in tournament_sleeves
    ) + sum(
        1 if len(row["lookthrough_candidate_program_ids"]) >= 2 else 0
        for row in tournament_sleeves
    )
    tournament_body = {
        "schema": FUND_PROGRAM_TOURNAMENT_INPUT_SCHEMA,
        "as_of": as_of,
        "sleeve_implementation_sha256": implementation[
            "sleeve_implementation_sha256"
        ],
        "program_count": program_count,
        "same_information_core_candidate_count": core_candidate_count,
        "lookthrough_quality_candidate_count": lookthrough_candidate_count,
        "portfolio_policy_candidate_count": portfolio_candidate_count,
        "cash_hurdle_candidate_count": len(cash_candidate_ids),
        "cash_hurdle_candidate_program_ids": cash_candidate_ids,
        "prospective_ranking_ticket_count": prospective_ranking_ticket_count,
        "sleeves": tournament_sleeves,
        "selection_claims": [
            {
                "claim_id": "factor_net_expense",
                "coordinate": "factor_implied_return_less_expense",
                "direction": "maximize",
                "semantics": "factor_assumption_control_not_expected_alpha",
            },
            {
                "claim_id": "aggregate_earnings_power",
                "coordinate": "aggregate_earnings_power_margin",
                "direction": "maximize",
                "semantics": "aggregate_expectations_proxy_not_holdings_underwriting",
            },
            {
                "claim_id": "lookthrough_durable_earnings_power",
                "coordinate": "holdings_weighted_durable_earnings_power",
                "direction": "maximize",
                "semantics": "covered_holdings_only_until_declared_coverage_threshold",
            },
        ],
        "status": (
            "research_tournament_input_ready"
            if prospective_ranking_ticket_count else "evidence_blocked"
        ),
        "portfolio_policy_status": (
            "evidence_complete_not_activated"
            if portfolio_candidate_count else "evidence_blocked"
        ),
        "allocation_selected": False,
        "expected_alpha_claim": False,
        "capital_authority": False,
    }
    tournament_input = {
        **tournament_body,
        "tournament_input_sha256": stable_sha256(tournament_body),
    }

    comparison_count = sum(
        row["comparison_eligible"] for sleeve in sleeves for row in sleeve["programs"]
    )
    admitted_count = sum(
        row["implementation_review_admitted"]
        for sleeve in sleeves for row in sleeve["programs"]
    )
    portfolio_blockers = [
        "portfolio_mandate_absent",
        "current_portfolio_state_absent",
        "implementation_candidates_are_not_portfolio_candidates",
    ]
    if not admitted_count:
        portfolio_blockers.insert(0, "no_implementation_review_admitted_fund")
    acquisition_contract = _portfolio_evidence_acquisition_contract(
        implementation=implementation, sleeves=sleeves,
        risk_basis=risk_basis, as_of=as_of,
    )
    body = {
        "schema": FUND_SLEEVE_COMPARISON_SCHEMA,
        "as_of": as_of,
        "source_evidence_epochs": sorted(set(valid_epochs), key=timestamp_key),
        "sleeve_implementation_sha256": implementation["sleeve_implementation_sha256"],
        "risk_basis": risk_basis,
        "risk_basis_error": risk_error,
        "cash_hurdle": cash_hurdle,
        "objective_contract": [
            {"metric_id": "factor_implied_return_less_expense", "direction": "maximize"},
            {"metric_id": "annualized_volatility", "direction": "minimize"},
            {"metric_id": "drawdown_severity", "direction": "minimize"},
            {"metric_id": "expense_ratio", "direction": "minimize"},
            {"metric_id": "half_spread_entry_cost_proxy", "direction": "minimize"},
        ],
        "sleeves": sleeves,
        "comparison_eligible_count": comparison_count,
        "implementation_review_admitted_count": admitted_count,
        "status": (
            "implementation_review_ready" if admitted_frontier_ids else
            "research_comparison_only" if comparison_count else "evidence_blocked"
        ),
        "portfolio_handoff": {
            "status": "blocked",
            "compatible_compiler": "ztare.investment.portfolio.compile_portfolio_assembly",
            "required_candidate_schema": "jaggedthoughts-investment-decision-v1",
            "blockers": portfolio_blockers,
            "candidate_program_ids": admitted_frontier_ids,
            "evidence_acquisition": acquisition_contract,
        },
        "portfolio_policy_tournament_input": tournament_input,
        "allocation_selected": False,
        "expected_return_claim": False,
        "invest_vs_cash_activation": {
            "status": "research_candidates_ready" if cash_candidate_ids else "evidence_blocked",
            "candidate_program_ids": cash_candidate_ids,
            "ranked_research_candidates": cash_activation_rows,
            "required_next_transition": (
                "compile_comparison_bound_fund_implementation_research_request"
                if cash_candidate_ids else "close_public_cash_or_fund_evidence"
            ),
            "automatic_paper_watch_activation": False,
            "capital_authority": False,
        },
        "authority": "normalized_paper_comparison_only",
        "capital_authority": False,
        "brokerage_authority": False,
        "use_boundary": (
            "Each program replaces one normalized sleeve unit with one fund. The frontier compares "
            "factor-implied return less observed expense, price risk, drawdown, and quoted-spread "
            "cost while preserving factor and holdings evidence. It neither supplies cross-sleeve "
            "weights nor bypasses portfolio underwriting and mandate constraints."
        ),
    }
    return {**body, "fund_sleeve_comparison_sha256": stable_sha256(body)}


def compile_workspace_fund_sleeve_comparison(
    workspace: str | Path,
    *,
    sleeve_implementation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile the current public-fund comparison from workspace evidence."""
    root = Path(workspace).expanduser().resolve()
    implementation = (
        dict(sleeve_implementation) if sleeve_implementation is not None
        else compile_workspace_sleeve_implementation_frontier(root)
    )
    epochs = [str(implementation.get("as_of") or "")]
    epochs.extend(
        str(((row.get("identity") or {}).get("implementation_epoch") or ""))
        for sleeve in implementation.get("sleeves") or ()
        for row in sleeve.get("eligible_instruments") or ()
    )
    valid = [canonical_timestamp(value, "fund comparison workspace epoch")
             for value in epochs if value]
    if not valid:
        raise ValueError("fund comparison requires a point-in-time evidence epoch")
    as_of = max(valid, key=timestamp_key)
    entity_ids = {
        str((row.get("identity") or {}).get("subject_id") or row.get("entity_id") or "").upper()
        for sleeve in implementation.get("sleeves") or ()
        for row in sleeve.get("eligible_instruments") or ()
        if str((row.get("identity") or {}).get("subject_id") or row.get("entity_id") or "")
    }
    return compile_fund_sleeve_comparison(
        sleeve_implementation=implementation,
        price_points=load_price_points(
            root / "data" / "observations.csv", as_of=as_of,
            metric_id="adjusted_price",
            entity_ids=entity_ids,
        ),
        holdings_quality=_workspace_holdings_quality(root, implementation),
        capital_market_basis=(
            (json.loads(
                (root / "household" / "capital_market_basis" / "latest.json").read_text(
                    encoding="utf-8"
                )
            ).get("capital_market_basis"))
            if (root / "household" / "capital_market_basis" / "latest.json").is_file()
            else None
        ),
    )


def _workspace_holdings_quality(
    root: Path, implementation: Mapping[str, Any], *, minimum_coverage: float = 0.50,
) -> dict[str, dict[str, Any]]:
    quality = {}
    for path in (root / "quality").glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        body = {key: value for key, value in payload.items() if key != "quality_report_sha256"}
        if stable_sha256(body) != payload.get("quality_report_sha256"):
            raise ValueError(f"company quality content hash mismatch: {path.name}")
        quality[str(payload["entity_id"]).upper()] = payload
    result = {}
    for sleeve in implementation.get("sleeves") or ():
        for instrument in sleeve.get("eligible_instruments") or ():
            if instrument.get("basis_proxy"):
                continue
            entity = str((instrument.get("identity") or {}).get("subject_id") or "").upper()
            relative = str((instrument.get("lookthrough_fit") or {}).get("snapshot_path") or "")
            if not relative:
                result[entity] = {"status": "holdings_snapshot_absent"}
                continue
            snapshot = json.loads((root / relative).read_text(encoding="utf-8"))
            declared = snapshot.get("snapshot_sha256")
            if stable_sha256({key: value for key, value in snapshot.items()
                              if key != "snapshot_sha256"}) != declared:
                raise ValueError(f"fund holdings content hash mismatch: {entity}")
            covered = [
                (row, quality[canonical_public_issuer_id(row.get("identifier"))])
                for row in snapshot.get("holdings") or ()
                if canonical_public_issuer_id(row.get("identifier")) in quality
            ]
            covered_weight = sum(float(row.get("weight") or 0) for row, _ in covered)
            disclosed_weight = float(snapshot.get("disclosed_weight") or 0)
            coverage = covered_weight / disclosed_weight if disclosed_weight else 0.0
            scores = {
                field: (
                    sum(float(row.get("weight") or 0) * float(report["scores"][field])
                        for row, report in covered) / covered_weight
                    if covered_weight else None
                )
                for field in (
                    "durable_earnings_power", "earnings_quality",
                    "revenue_durability", "balance_sheet_resilience",
                )
            }
            status = (
                "sufficient_for_cross_fund_comparison" if coverage >= minimum_coverage
                else "partial_holdings_quality_coverage" if covered_weight
                else "holdings_weighted_earnings_power_absent"
            )
            result[entity] = {
                "status": status,
                "minimum_coverage": minimum_coverage,
                "covered_position_count": len(covered),
                "covered_weight": covered_weight,
                "disclosed_weight": disclosed_weight,
                "coverage_fraction_of_disclosed": coverage,
                **scores,
                "snapshot_sha256": declared,
                "quality_report_sha256s": sorted(
                    report["quality_report_sha256"] for _, report in covered
                ),
                "scope": "covered_holdings_only",
            }
    return result


def compile_fund_lookthrough_acquisition_plan(
    *, tournament_input: Mapping[str, Any], holdings_snapshots: Iterable[Mapping[str, Any]],
    quality_entity_ids: Iterable[str], enrolled_entity_ids: Iterable[str],
    public_equity_ids: Iterable[str], max_source_calls: int = 10,
) -> dict[str, Any]:
    """Minimize issuer calls to close a same-sleeve evidence threshold."""
    if max_source_calls < 1 or max_source_calls > 100:
        raise ValueError("fund look-through source-call budget must be in [1, 100]")
    evidence = dict(tournament_input)
    declared = str(evidence.pop("tournament_input_sha256", ""))
    if (
        evidence.get("schema") != FUND_PROGRAM_TOURNAMENT_INPUT_SCHEMA
        or stable_sha256(evidence) != declared
    ):
        raise ValueError("fund program tournament input hash is invalid")
    sleeve_funds = {
        str(sleeve["sleeve_id"]): {
            str(program["entity_id"]).upper()
            for program in sleeve.get("programs") or ()
            if program.get("same_information_core_ready")
        }
        for sleeve in evidence.get("sleeves") or ()
    }
    sleeve_funds = {
        sleeve_id: funds for sleeve_id, funds in sleeve_funds.items()
        if len(funds) >= 2
    }
    fund_ids = set().union(*sleeve_funds.values()) if sleeve_funds else set()
    snapshots = {}
    for raw in holdings_snapshots:
        snapshot = dict(raw)
        digest = str(snapshot.get("snapshot_sha256") or "")
        if stable_sha256({
            key: value for key, value in snapshot.items() if key != "snapshot_sha256"
        }) != digest:
            raise ValueError("fund holdings content hash mismatch")
        entity_id = str(snapshot.get("entity_id") or "").upper()
        if entity_id in fund_ids:
            snapshots[entity_id] = snapshot
    quality_ids = {str(value).upper() for value in quality_entity_ids}
    enrolled_ids = {str(value).upper() for value in enrolled_entity_ids}
    eligible_ids = {str(value).upper() for value in public_equity_ids}
    memberships: dict[str, dict[str, float]] = {}
    names: dict[str, str] = {}
    disclosed = {}
    for fund_id, snapshot in snapshots.items():
        disclosed[fund_id] = float(snapshot.get("disclosed_weight") or 0)
        for holding in snapshot.get("holdings") or ():
            issuer_id = canonical_public_issuer_id(holding.get("identifier"))
            weight = float(holding.get("weight") or 0)
            if not issuer_id or weight <= 0:
                continue
            fund_weights = memberships.setdefault(issuer_id, {})
            fund_weights[fund_id] = fund_weights.get(fund_id, 0.0) + weight
            names.setdefault(issuer_id, str(holding.get("security_name") or issuer_id))
    before_weights = {
        fund_id: sum(
            fund_weights.get(fund_id, 0.0)
            for issuer_id, fund_weights in memberships.items()
            if issuer_id in quality_ids
        )
        for fund_id in sorted(fund_ids)
    }
    candidates = []
    repair = []
    unsupported = []
    for issuer_id, fund_weights in memberships.items():
        if issuer_id in quality_ids:
            continue
        row = {
            "entity_id": issuer_id,
            "name": names[issuer_id],
            "fund_count": len(fund_weights),
            "aggregate_marginal_covered_weight": sum(fund_weights.values()),
            "fund_memberships": [
                {"fund_entity_id": fund_id, "weight": weight}
                for fund_id, weight in sorted(fund_weights.items())
            ],
        }
        if issuer_id in enrolled_ids:
            repair.append({**row, "next_action": "repair_metric_coverage"})
        elif issuer_id not in eligible_ids:
            unsupported.append({**row, "next_action": "public_source_identity_unavailable"})
        else:
            candidates.append(row)
    def sleeve_completion(
        weights: Mapping[str, float],
        sleeves: Mapping[str, set[str]],
    ) -> tuple[tuple[float, ...], str | None, list[str]]:
        states = []
        for sleeve_id, funds in sleeves.items():
            completion = sorted(((
                min(1.0, weights[fund_id] / (0.5 * disclosed[fund_id]))
                if disclosed.get(fund_id) else 0.0,
                fund_id,
            ) for fund_id in funds), reverse=True)
            if len(completion) >= 2:
                states.append((
                    (float(sum(value >= 1.0 for value, _ in completion)),
                     completion[1][0], completion[0][0] + completion[1][0]),
                    sleeve_id,
                    [completion[0][1], completion[1][1]],
                ))
        return max(states, default=((0.0, 0.0, 0.0), None, []))

    observed_sleeve_states = {
        sleeve_id: sleeve_completion(before_weights, {sleeve_id: funds})[0]
        for sleeve_id, funds in sleeve_funds.items()
    }
    open_sleeve_funds = {
        sleeve_id: funds for sleeve_id, funds in sleeve_funds.items()
        if observed_sleeve_states[sleeve_id][0] < 2
    }

    def closure_score(row: Mapping[str, Any], weights: Mapping[str, float]) -> tuple[float, ...]:
        projected = dict(weights)
        for membership in row["fund_memberships"]:
            fund_id = str(membership["fund_entity_id"])
            projected[fund_id] += float(membership["weight"])
        same_sleeve = sleeve_completion(projected, open_sleeve_funds)[0]
        return (
            float(same_sleeve[0]), same_sleeve[1], same_sleeve[2],
            float(row["fund_count"]), float(row["aggregate_marginal_covered_weight"]),
        )

    # Every issuer consumes one Company Facts call and a daily batch shares one
    # registry call. This is a binary minimum-cover problem: certify the
    # smallest issuer set that takes two comparable funds over the declared
    # holdings-quality threshold, then order that set for near-term progress.
    candidate_by_id = {str(row["entity_id"]): row for row in candidates}
    optimization = run_minimum_call_cover({
        "issuers": [{
            "entity_id": issuer_id,
            "fund_memberships": {
                str(row["fund_entity_id"]): float(row["weight"])
                for row in candidate["fund_memberships"]
            },
            "aggregate_marginal_covered_weight": float(
                candidate["aggregate_marginal_covered_weight"]
            ),
            "cross_fund_reuse_memberships": max(
                0, int(candidate["fund_count"]) - 1
            ),
        } for issuer_id, candidate in candidate_by_id.items()],
        "funds": {
            fund_id: {
                "before_company_quality_weight": before_weights[fund_id],
                "disclosed_weight": disclosed.get(fund_id, 0.0),
            } for fund_id in sorted(fund_ids)
        },
        "sleeves": {
            sleeve_id: sorted(funds) for sleeve_id, funds in open_sleeve_funds.items()
        },
    })
    exact = ({"issuer_entity_ids": optimization["selected_entity_ids"]}
             if optimization.get("optimal") else None)

    projected_weights = dict(before_weights)
    projected_pool = [
        candidate_by_id[issuer_id]
        for issuer_id in (
            exact["issuer_entity_ids"] if exact else sorted(candidate_by_id)
        )
    ] if open_sleeve_funds else []
    projected_rows = []
    while projected_pool:
        chosen = min(
            projected_pool,
            key=lambda row: tuple(-value for value in closure_score(row, projected_weights)) + (row["entity_id"],),
        )
        projected_rows.append(chosen)
        for membership in chosen["fund_memberships"]:
            projected_weights[str(membership["fund_entity_id"])] += float(membership["weight"])
        projected_pool.remove(chosen)
        if (
            not exact
            and sleeve_completion(projected_weights, open_sleeve_funds)[0][0] >= 2
        ):
            break

    projected_ids = [str(row["entity_id"]) for row in projected_rows]
    issuer_capacity = max(1, max_source_calls - 1)
    selected = projected_rows[:issuer_capacity]
    selected_ids = {str(row["entity_id"]) for row in selected}
    remaining = [row for row in candidates if str(row["entity_id"]) not in selected_ids]
    planning_weights = dict(before_weights)
    for row in selected:
        for membership in row["fund_memberships"]:
            planning_weights[str(membership["fund_entity_id"])] += float(membership["weight"])

    closure_state, closure_sleeve, closure_funds = sleeve_completion(
        projected_weights, open_sleeve_funds or sleeve_funds,
    )
    issuer_capacity = max(1, max_source_calls - 1)
    projected_batches = math.ceil(len(projected_ids) / issuer_capacity) if projected_ids else 0
    closure_projection = {
        "status": (
            "reachable_with_current_eligible_issuer_set"
            if closure_state[0] >= 2 else "unreachable_with_current_eligible_issuer_set"
        ),
        "target_sleeve_id": closure_sleeve,
        "target_fund_entity_ids": closure_funds,
        "observed_closed_sleeve_ids": sorted(
            sleeve_id for sleeve_id, state in observed_sleeve_states.items()
            if state[0] >= 2
        ),
        "target_open_sleeve_ids": sorted(open_sleeve_funds),
        "projected_coverage_fraction": {
            fund_id: (
                projected_weights[fund_id] / disclosed[fund_id]
                if disclosed.get(fund_id) else 0.0
            ) for fund_id in closure_funds
        },
        "issuer_calls_required": len(projected_ids),
        "daily_batches_required": projected_batches,
        "total_source_calls_required": len(projected_ids) + projected_batches,
        "conditional_on_sufficient_companyfacts": True,
        "optimization_certificate": {
            "solver": "scipy.optimize.milp/highs",
            "logic": "binary_mixed_integer_linear_program",
            "objective": "minimum_issuer_calls_for_two_same_sleeve_thresholds",
            "evaluated_fund_pair_count": sum(
                len(funds) * (len(funds) - 1) // 2
                for funds in sleeve_funds.values()
            ),
            "admissible_sleeve_count": optimization.get("admissible_sleeve_count"),
            "minimum_issuer_calls": optimization.get("minimum_issuer_calls"),
            "mip_gap": optimization.get("mip_gap"),
            "message": optimization.get("message"),
            "optimal": exact is not None,
        },
    }
    after_weights = dict(before_weights)
    for row in selected:
        for membership in row["fund_memberships"]:
            fund_id = str(membership["fund_entity_id"])
            after_weights[fund_id] += float(membership["weight"])
    coverage = [{
        "fund_entity_id": fund_id,
        "disclosed_weight": disclosed.get(fund_id),
        "before_company_quality_weight": before_weights.get(fund_id, 0.0),
        "after_company_quality_weight_potential": after_weights.get(fund_id, 0.0),
        "marginal_weight_potential": (
            after_weights.get(fund_id, 0.0) - before_weights.get(fund_id, 0.0)
        ),
        "before_coverage_fraction": (
            before_weights.get(fund_id, 0.0) / disclosed[fund_id]
            if disclosed.get(fund_id) else 0.0
        ),
        "after_coverage_fraction_potential": (
            after_weights.get(fund_id, 0.0) / disclosed[fund_id]
            if disclosed.get(fund_id) else 0.0
        ),
    } for fund_id in sorted(fund_ids)]
    body = {
        "schema": FUND_LOOKTHROUGH_ACQUISITION_PLAN_SCHEMA,
        "as_of": evidence["as_of"],
        "fund_program_tournament_input_sha256": declared,
        "target_fund_entity_ids": sorted(fund_ids),
        "holdings_snapshot_count": len(snapshots),
        "missing_holdings_fund_entity_ids": sorted(fund_ids - snapshots.keys()),
        "selection_policy": {
            "objective": "minimum_call_same_sleeve_threshold_closure_then_cross_fund_coverage",
            "lexicographic_order": [
                "issuer_calls_to_two_same_sleeve_50pct_thresholds_asc",
                "same_sleeve_programs_crossing_50pct_desc",
                "second_program_threshold_completion_desc",
                "top_two_threshold_completion_desc",
                "cross_fund_reuse_desc",
                "aggregate_marginal_covered_weight_desc",
                "source_calls_asc",
            ],
            "reuse_semantics": "one issuer call contributes its weight to every member fund",
            "tie_breakers": ["entity_id_asc"],
        },
        "source_budget": {
            "max_source_calls": max_source_calls,
            "sec_registry_batch_calls": int(bool(selected)),
            "sec_companyfacts_calls": len(selected),
            "estimated_source_calls": len(selected) + int(bool(selected)),
        },
        "same_sleeve_threshold_closure_projection": closure_projection,
        "before_after_coverage_potential": coverage,
        "aggregate_before_company_quality_weight": sum(before_weights.values()),
        "aggregate_after_company_quality_weight_potential": sum(after_weights.values()),
        "aggregate_marginal_weight_potential": sum(
            float(row["aggregate_marginal_covered_weight"]) for row in selected
        ),
        "selected": [
            {**row, "selection_rank": index, "next_action": "enroll_public_equity"}
            for index, row in enumerate(selected, 1)
        ],
        "selected_entity_ids": [row["entity_id"] for row in selected],
        "selected_cross_fund_reuse_memberships": sum(
            max(0, int(row["fund_count"]) - 1) for row in selected
        ),
        "remaining_gaps": {
            "metric_repair_count": len(repair),
            "metric_repair": sorted(repair, key=lambda row: row["entity_id"]),
            "public_source_identity_unavailable_count": len(unsupported),
            "public_source_identity_unavailable_examples": sorted(
                unsupported, key=lambda row: row["entity_id"]
            )[:25],
            "budget_deferred_count": len(candidates) - len(selected_ids),
            "next_budget_deferred": [
                row for row in candidates if row["entity_id"] not in selected_ids
            ][:25],
        },
        "after_is_potential_not_observed": True,
        "allocation_selected": False,
        "capital_authority": False,
    }
    return {**body, "plan_sha256": stable_sha256(body)}


def compile_workspace_fund_lookthrough_acquisition_plan(
    workspace: str | Path, *, max_source_calls: int = 10,
    tournament_input: Mapping[str, Any] | None = None,
    source_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    evidence = (
        dict(tournament_input) if tournament_input is not None
        else compile_workspace_fund_sleeve_comparison(root)[
            "portfolio_policy_tournament_input"
        ]
    )
    snapshots = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / "data" / "fund_holdings").glob("*.json"))
        if not path.name.endswith("-latest.json")
    ]
    manifest = (
        dict(source_manifest) if source_manifest is not None
        else yaml.safe_load((root / "sources.yaml").read_text(encoding="utf-8"))
    )
    catalog = json.loads((root / "universe" / "catalog-latest.json").read_text(
        encoding="utf-8"
    ))
    return compile_fund_lookthrough_acquisition_plan(
        tournament_input=evidence,
        holdings_snapshots=snapshots,
        quality_entity_ids=(path.stem for path in (root / "quality").glob("*.json")),
        enrolled_entity_ids=(
            row.get("entity_id") for row in manifest.get("sources") or ()
            if isinstance(row, Mapping) and row.get("adapter") == "sec_companyfacts"
        ),
        public_equity_ids=(
            row.get("symbol") for row in catalog.get("securities") or ()
            if isinstance(row, Mapping)
            and row.get("entity_kind") == "public_equity"
            and row.get("security_kind") == "common_equity"
        ),
        max_source_calls=max_source_calls,
    )


__all__ = [
    "FUND_SLEEVE_COMPARISON_SCHEMA",
    "FUND_PROGRAM_TOURNAMENT_INPUT_SCHEMA",
    "FUND_LOOKTHROUGH_ACQUISITION_PLAN_SCHEMA",
    "PORTFOLIO_EVIDENCE_ACQUISITION_SCHEMA",
    "canonical_public_issuer_id",
    "compile_fund_sleeve_comparison",
    "compile_fund_lookthrough_acquisition_plan",
    "compile_workspace_fund_lookthrough_acquisition_plan",
    "compile_workspace_fund_sleeve_comparison",
]
