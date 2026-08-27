"""Acquire a public, source-bound risk basis for broad USD sleeves."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_finite
from .factor_analysis import compile_return_covariance
from .household_allocation import CAPITAL_MARKET_BASIS_SCHEMA, compile_capital_market_basis
from .sources import consume_public_sources


PUBLIC_BASIS_ACQUISITION_SCHEMA = "jaggedthoughts-public-capital-market-basis-acquisition-v1"

_SLEEVES = (
    ("cash", "BIL", "cash", "yahoo_bil_adjusted_daily"),
    ("us_equity", "SPY", "risky", "yahoo_spy_adjusted_daily"),
    ("international_equity", "VXUS", "risky", "yahoo_vxus_adjusted_daily"),
    ("usd_bonds", "BND", "defensive", "yahoo_bnd_adjusted_daily"),
    ("us_tips", "TIP", "defensive", "yahoo_tip_adjusted_daily"),
)
PUBLIC_SLEEVE_IDS = tuple(row[0] for row in _SLEEVES)
PUBLIC_BASIS_SOURCE_IDS = (
    *(row[3] for row in _SLEEVES),
    "nyu_us_implied_erp",
    "fred_public_market_state",
)

_ERP_METHOD_METRICS = (
    ("current_source_anchor", "implied_equity_risk_premium"),
    ("erp_method_ttm_cash_yield", "implied_erp_ttm_cash_yield"),
    ("erp_method_10y_average_cash_flow_yield", "implied_erp_10y_average_cash_flow_yield"),
    ("erp_method_net_cash_yield", "implied_erp_net_cash_yield"),
    ("erp_method_normalized_earnings_payout", "implied_erp_normalized_earnings_payout"),
)


def public_sleeve_proxies() -> list[dict[str, str]]:
    """Expose the exact public sleeve/proxy identity without leaking allocation policy."""
    return [
        {
            "sleeve_id": sleeve_id, "symbol": symbol,
            "risk_bucket": risk_bucket, "source_id": source_id,
        }
        for sleeve_id, symbol, risk_bucket, source_id in _SLEEVES
    ]


def _row(value: Any) -> dict[str, Any]:
    return value.to_dict() if hasattr(value, "to_dict") else dict(value)


def _receipt_index(source_receipts: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for source in source_receipts:
        row = dict(source)
        source_id = str(row.get("source_id") or "")
        if source_id in result:
            raise ValueError(f"duplicate source receipt: {source_id}")
        digest = str(row.get("receipt_sha256") or "")
        if len(digest) != 64:
            raise ValueError(f"source receipt lacks a SHA-256 digest: {source_id}")
        result[source_id] = row
    missing = sorted(set(PUBLIC_BASIS_SOURCE_IDS) - set(result))
    if missing:
        raise ValueError("capital-market basis lacks current source receipts: " + ", ".join(missing))
    return result


def _current_rows(
    observations: Iterable[Mapping[str, Any]], receipts: Mapping[str, Mapping[str, Any]], as_of: str,
) -> list[dict[str, Any]]:
    for source_id, receipt in receipts.items():
        if str(receipt.get("retrieved_at") or "") > as_of:
            raise ValueError(f"source receipt is later than the basis epoch: {source_id}")
    rows = []
    for source in observations:
        row = _row(source)
        receipt = receipts.get(str(row.get("source_ref") or ""))
        if receipt and str(row.get("available_at") or "") <= str(receipt.get("retrieved_at") or ""):
            rows.append(row)
    return rows


def _latest_metric(
    rows: Iterable[Mapping[str, Any]], *, source_id: str, entity_id: str, metric_id: str,
) -> tuple[float, dict[str, Any]]:
    matches = [dict(row) for row in rows if (
        row.get("source_ref") == source_id
        and row.get("entity_id") == entity_id
        and row.get("metric_id") == metric_id
    )]
    if not matches:
        raise ValueError(f"capital-market basis lacks {source_id}:{entity_id}.{metric_id}")
    selected = max(matches, key=lambda row: (
        str(row.get("observed_at") or ""), str(row.get("available_at") or ""),
        str(row.get("observation_id") or ""),
    ))
    return require_finite(selected.get("value"), metric_id), selected


def _adjusted_prices(
    rows: Iterable[Mapping[str, Any]], *, source_id: str, entity_id: str,
) -> dict[str, float]:
    latest_by_day: dict[str, dict[str, Any]] = {}
    for source in rows:
        row = dict(source)
        if (
            row.get("source_ref") != source_id
            or row.get("entity_id") != entity_id
            or row.get("metric_id") != "adjusted_price"
        ):
            continue
        day = str(row.get("observed_at") or "")[:10]
        current = latest_by_day.get(day)
        if current is None or str(row.get("available_at") or "") > str(current.get("available_at") or ""):
            latest_by_day[day] = row
    prices = {day: require_finite(row.get("value"), f"{entity_id} adjusted price")
              for day, row in latest_by_day.items()}
    if any(value <= 0 for value in prices.values()):
        raise ValueError(f"{entity_id} adjusted prices must be positive")
    return prices


def compile_public_capital_market_basis_input(
    *,
    as_of: str,
    observations: Iterable[Mapping[str, Any]],
    source_receipts: Iterable[Mapping[str, Any]],
    scenario_adjustments: Mapping[str, Mapping[str, float]] | None = None,
    lookback_returns: int = 756,
    diagonal_shrinkage: float = 0.25,
) -> dict[str, Any]:
    """Compile risk evidence and source-anchored assumptions for the household basis."""
    epoch = canonical_timestamp(as_of, "capital-market basis as_of")
    if lookback_returns < 252:
        raise ValueError("capital-market risk basis requires at least 252 daily returns")
    shrinkage = require_finite(diagonal_shrinkage, "diagonal_shrinkage")
    if not 0 <= shrinkage <= 1:
        raise ValueError("diagonal_shrinkage must be in [0, 1]")
    receipts = _receipt_index(source_receipts)
    rows = _current_rows(observations, receipts, epoch)

    prices = {
        asset_id: _adjusted_prices(rows, source_id=source_id, entity_id=symbol)
        for asset_id, symbol, _, source_id in _SLEEVES
    }
    try:
        risk = compile_return_covariance(
            price_series=prices,
            as_of=epoch,
            min_returns=252,
            lookback_returns=lookback_returns,
            diagonal_shrinkage=diagonal_shrinkage,
        )
    except ValueError as error:
        availability = {asset_id: len(series) for asset_id, series in prices.items()}
        raise ValueError(
            f"capital-market basis lacks 252 aligned returns: {availability}"
        ) from error

    cash, cash_row = _latest_metric(
        rows, source_id="fred_public_market_state", entity_id="US-MACRO",
        metric_id="treasury_3m_yield",
    )
    risk_free, risk_free_row = _latest_metric(
        rows, source_id="nyu_us_implied_erp", entity_id="US-MARKET",
        metric_id="risk_free_rate",
    )
    erp, erp_row = _latest_metric(
        rows, source_id="nyu_us_implied_erp", entity_id="US-MARKET",
        metric_id="implied_equity_risk_premium",
    )
    real_yield, real_row = _latest_metric(
        rows, source_id="fred_public_market_state", entity_id="US-MACRO",
        metric_id="treasury_10y_real_yield",
    )
    breakeven, breakeven_row = _latest_metric(
        rows, source_id="fred_public_market_state", entity_id="US-MACRO",
        metric_id="breakeven_inflation_10y",
    )
    anchors = {
        "cash": cash,
        "us_equity": risk_free + erp,
        "international_equity": risk_free + erp,
        "usd_bonds": risk_free,
        "us_tips": (1.0 + real_yield) * (1.0 + breakeven) - 1.0,
    }
    asset_ids = [row[0] for row in _SLEEVES]
    erp_methods: list[tuple[str, str, float, dict[str, Any]]] = []
    erp_method_blockers = []
    if scenario_adjustments is None:
        for scenario_id, metric_id in _ERP_METHOD_METRICS:
            try:
                value, observation = _latest_metric(
                    rows, source_id="nyu_us_implied_erp", entity_id="US-MARKET",
                    metric_id=metric_id,
                )
            except ValueError:
                erp_method_blockers.append(f"missing_source_metric:{metric_id}")
                continue
            erp_methods.append((scenario_id, metric_id, value, observation))
    method_epochs = {
        (str(row.get("observed_at") or ""), str(row.get("available_at") or ""))
        for _scenario_id, _metric_id, _value, row in erp_methods
    }
    complete_method_set = (
        len(erp_methods) == len(_ERP_METHOD_METRICS)
        and len(method_epochs) == 1
        and next(iter(method_epochs))[1]
        == str(receipts["nyu_us_implied_erp"].get("retrieved_at") or "")
    )
    if len(erp_methods) == len(_ERP_METHOD_METRICS) and not complete_method_set:
        erp_method_blockers.append("erp_methods_do_not_share_one_source_epoch")
    adjustments = scenario_adjustments or {
        scenario_id: {
            asset_id: (
                method_erp - erp if asset_id in {"us_equity", "international_equity"}
                else 0.0
            )
            for asset_id in asset_ids
        }
        for scenario_id, _metric_id, method_erp, _observation in (
            erp_methods if complete_method_set else [(
                "current_source_anchor", "implied_equity_risk_premium", erp, erp_row,
            )]
        )
    }
    scenarios = []
    for scenario_id, raw_adjustments in sorted(adjustments.items()):
        if set(raw_adjustments) != set(asset_ids):
            raise ValueError(f"scenario {scenario_id} adjustments must cover the exact sleeve universe")
        values = {
            asset_id: anchors[asset_id] + require_finite(raw_adjustments[asset_id], f"{scenario_id}.{asset_id}")
            for asset_id in asset_ids
        }
        scenarios.append({
            "scenario_id": scenario_id,
            "expected_returns": values,
            "source_refs": [
                receipts["nyu_us_implied_erp"]["receipt_sha256"],
                receipts["fred_public_market_state"]["receipt_sha256"],
            ],
        })

    price_refs = [receipts[row[3]]["receipt_sha256"] for row in _SLEEVES]
    market_refs = [
        receipts["nyu_us_implied_erp"]["receipt_sha256"],
        receipts["fred_public_market_state"]["receipt_sha256"],
    ]
    correlation_rows = risk["correlations"]
    body = {
        "schema": CAPITAL_MARKET_BASIS_SCHEMA,
        "basis_id": "public-usd-broad-sleeves",
        "as_of": epoch,
        "asset_classes": [{
            "asset_id": asset_id,
            "risk_bucket": risk_bucket,
            "currency": "USD",
            "volatility": float(risk["annualized_volatility"][asset_id]),
            "minimum_weight": 0.0,
            "maximum_weight": 1.0,
        } for index, (asset_id, _, risk_bucket, _) in enumerate(_SLEEVES)],
        "correlations": correlation_rows,
        "return_scenarios": scenarios,
        "source_refs": sorted(set(price_refs + market_refs)),
        "risk_evidence": {
            **{
                key: value for key, value in risk.items()
                if key not in {
                    "schema", "as_of", "entity_ids", "annualized_volatility",
                    "correlations", "return_covariance_sha256",
                }
            },
            "return_covariance_sha256": risk["return_covariance_sha256"],
            "price_sources": [{
                "asset_id": asset_id, "proxy": symbol, "metric_id": "adjusted_price",
                "observation_count": len(prices[asset_id]),
                "receipt_sha256": receipts[source_id]["receipt_sha256"],
            } for asset_id, symbol, _, source_id in _SLEEVES],
            "historical_mean_used_as_forecast": False,
        },
        "return_scenario_inputs": {
            "anchor_formulas": {
                "cash": "treasury_3m_yield",
                "us_equity": "risk_free_rate + implied_equity_risk_premium",
                "international_equity": "risk_free_rate + implied_equity_risk_premium + explicit_adjustment",
                "usd_bonds": "risk_free_rate + explicit_adjustment",
                "us_tips": "(1 + treasury_10y_real_yield) * (1 + breakeven_inflation_10y) - 1 + explicit_adjustment",
            },
            "observations": [
                cash_row, risk_free_row, real_row, breakeven_row,
                *(
                    [row for _scenario_id, _metric_id, _value, row in erp_methods]
                    if complete_method_set else [erp_row]
                ),
            ],
            "uncertainty_set": {
                "mode": (
                    "source_bound_erp_method_worlds"
                    if scenario_adjustments is None and complete_method_set else
                    "caller_declared_adjustments" if scenario_adjustments is not None else
                    "single_source_anchor"
                ),
                "scenario_count": len(scenarios),
                "probability_interpretation": False,
                "shared_method_epoch": (
                    {
                        "observed_at": next(iter(method_epochs))[0],
                        "available_at": next(iter(method_epochs))[1],
                        "source_receipt_sha256": receipts["nyu_us_implied_erp"][
                            "receipt_sha256"
                        ],
                    }
                    if scenario_adjustments is None and complete_method_set else None
                ),
                "method_worlds": [
                    {
                        "scenario_id": scenario_id,
                        "erp_metric_id": metric_id,
                        "erp_value": value,
                        "observation_id": observation["observation_id"],
                        "source_ref": observation["source_ref"],
                    }
                    for scenario_id, metric_id, value, observation in erp_methods
                ] if scenario_adjustments is None and complete_method_set else [],
                "blockers": erp_method_blockers,
                "excluded_return_models": {
                    "historical_mean": "risk_evidence_only_not_an_expected_return_forecast",
                    "state_prices": "current_public_priced_claims_do_not_identify_state_prices",
                    "earnings_and_dividend_yield_spreads": "valuation_diagnostics_not_total_return_models",
                },
            },
            "historical_mean_used_as_forecast": False,
            "expected_return_claim": False,
        },
        "capital_authority": False,
    }
    return {**body, "acquisition_sha256": stable_sha256(body)}


def acquire_public_capital_market_basis(
    workspace: str | Path, *,
    scenario_adjustments: Mapping[str, Mapping[str, float]] | None = None,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    """Fetch the seven public inputs and return a validated household basis."""
    root = Path(workspace).expanduser().resolve()
    source_run = consume_public_sources(
        root / "sources.yaml", workspace=root, source_ids=PUBLIC_BASIS_SOURCE_IDS,
        derive_metrics=False, retrieved_at=retrieved_at,
        receipt_dir=root / "household" / "capital_market_basis",
    )
    with (root / "data" / "observations.csv").open(encoding="utf-8", newline="") as handle:
        observations = list(csv.DictReader(handle))
    basis_input = compile_public_capital_market_basis_input(
        as_of=source_run["as_of"], observations=observations,
        source_receipts=source_run["source_receipts"],
        scenario_adjustments=scenario_adjustments,
    )
    basis = compile_capital_market_basis(basis_input)
    body = {
        "schema": PUBLIC_BASIS_ACQUISITION_SCHEMA,
        "as_of": source_run["as_of"],
        "source_run_sha256": source_run["run_sha256"],
        "source_statuses": source_run["source_statuses"],
        "capital_market_basis_input": basis_input,
        "capital_market_basis": basis,
        "data_availability": {
            "sleeves": [row[0] for row in _SLEEVES],
            "source_count": len(source_run["source_receipts"]),
            "all_required_inputs_available": True,
        },
        "allocation_coverage": {
            "asset_class_currencies": ["USD"],
            "after_tax_return_haircuts_included": False,
            "non_usd_liability_currency_covered": False,
            "gaps": [
                "exact_per_sleeve_annual_tax_haircuts_are_private_mandate_inputs",
                "non_usd_liability_requires_a_matching_sleeve_or_currency_hedge",
            ],
        },
        "authority": "public_evidence_acquisition",
        "capital_authority": False,
    }
    result = {**body, "artifact_sha256": stable_sha256(body)}
    destination = root / "household" / "capital_market_basis" / "latest.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    os.replace(temporary, destination)
    return result


__all__ = [
    "PUBLIC_BASIS_ACQUISITION_SCHEMA",
    "PUBLIC_BASIS_SOURCE_IDS",
    "PUBLIC_SLEEVE_IDS",
    "acquire_public_capital_market_basis",
    "compile_public_capital_market_basis_input",
    "public_sleeve_proxies",
]
