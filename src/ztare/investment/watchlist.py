"""Opportunity watchlists compiled from public observations and declared plays."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from statistics import median
from typing import Any, Mapping

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.motion.set_distance import jaccard_distance

from .contracts import (
    canonical_timestamp, require_finite, require_refs, require_text, timestamp_key,
)
from .factor_analysis import FactorDefinition, analyze_factor_exposure, load_price_points
from .public_capital_market_basis import PUBLIC_SLEEVE_IDS


WATCHLIST_SCHEMA = "jaggedthoughts-opportunity-watchlist-v1"
WATCHLIST_RESULT_SCHEMA = "jaggedthoughts-opportunity-watchlist-result-v1"
FUND_CHOICE_FRONTIER_SCHEMA = "jaggedthoughts-fund-choice-frontier-v1"
FUND_HOLDINGS_GRAPH_SCHEMA = "jaggedthoughts-fund-holdings-graph-v1"
FUND_EVIDENCE_VOTE_RECEIPT_SCHEMA = "jaggedthoughts-fund-evidence-vote-receipt-v1"
_WATCHLIST_ENGINE_VERSION = "2026-08-23.holdings-availability-v8"
_WATCHLIST_ENGINE_AVAILABLE_AT = "2026-08-23T08:42:28Z"

_FUND_POTENTIAL_FAMILIES = {
    "valuation": (
        0.50,
        ("earnings_yield", "book_to_price"),
    ),
    "factor_return_and_risk": (
        0.40,
        ("factor_return_per_volatility", "drawdown_resilience"),
    ),
    "implementation_cost": (0.10, ("fee_efficiency",)),
}

_FUND_EVIDENCE_METRICS = (
    "fund_net_assets", "median_bid_ask_spread", "average_daily_volume_30d",
    "portfolio_holdings_count", "portfolio_top10_concentration",
    "portfolio_max_holding_weight", "portfolio_holdings_hhi",
    "portfolio_sector_hhi", "portfolio_top_sector_weight", "portfolio_turnover",
)

_FUND_VALUATION_COORDINATES = (
    "earnings_yield", "book_to_price", "earnings_power_margin",
    "expense_ratio", "implied_growth_median", "net_earnings_yield",
    "required_return",
)


def _load_yaml(path: Path) -> Mapping[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or payload.get("schema") != WATCHLIST_SCHEMA:
        raise ValueError(f"watchlist schema must be {WATCHLIST_SCHEMA}")
    return payload


def fund_potential_family_score(
    component_scores: Mapping[str, float],
) -> tuple[float, dict[str, float]]:
    """Weight semantic families once; algebraic diagnostics receive no extra vote."""
    required = {
        name for _weight, members in _FUND_POTENTIAL_FAMILIES.values()
        for name in members
    }
    missing = sorted(required - set(component_scores))
    if missing:
        raise ValueError(
            "fund potential lacks semantic-family components: " + ", ".join(missing)
        )
    family_scores = {
        family: sum(float(component_scores[name]) for name in members) / len(members)
        for family, (_, members) in _FUND_POTENTIAL_FAMILIES.items()
    }
    return sum(
        _FUND_POTENTIAL_FAMILIES[family][0] * value
        for family, value in family_scores.items()
    ), family_scores


def fund_evidence_vote_receipt(
    component_scores: Mapping[str, float], *, analysis_sha256: str | None = None,
    valuation_source_refs: tuple[str, ...] | list[str] = (),
) -> dict[str, Any]:
    """State which shared evidence carriers receive one additive vote."""
    body = {
        "schema": FUND_EVIDENCE_VOTE_RECEIPT_SCHEMA,
        "rule_id": "one-additive-vote-per-semantic-evidence-family-v2",
        "additive_families": {
            family: {"weight": weight, "components": list(members)}
            for family, (weight, members) in _FUND_POTENTIAL_FAMILIES.items()
        },
        "diagnostic_only": [
            "factor_fit_coverage", "factor_return_after_fee", "net_earnings_yield",
        ],
        "shared_carrier_controls": {
            "aligned_return_panel": {
                "additive_family": "factor_return_and_risk",
                "diagnostic_only": ["factor_fit_coverage"],
                "analysis_sha256": analysis_sha256,
            },
            "expense_ratio": {
                "additive_family": "implementation_cost",
                "excluded_derived_votes": ["net_earnings_yield", "factor_return_after_fee"],
                "source_refs": sorted({str(ref) for ref in valuation_source_refs if ref}),
            },
        },
        "observed_components": sorted(str(name) for name in component_scores),
    }
    return {**body, "receipt_sha256": stable_sha256(body)}


def verify_fund_evidence_vote_receipt(receipt: Any) -> bool:
    if not isinstance(receipt, Mapping):
        return False
    body = dict(receipt)
    digest = body.pop("receipt_sha256", None)
    return bool(
        receipt.get("schema") == FUND_EVIDENCE_VOTE_RECEIPT_SCHEMA
        and receipt.get("rule_id") == "one-additive-vote-per-semantic-evidence-family-v2"
        and digest == stable_sha256(body)
    )


def bound_fund_valuation_coordinates(
    valuation: Any,
) -> tuple[dict[str, float] | None, tuple[str, ...]]:
    """Read only the complete, source-bound aggregate valuation identity."""
    if not isinstance(valuation, Mapping):
        return None, ("aggregate_valuation_absent",)
    blockers = []
    if valuation.get("valuation_kind") != "aggregate_expectations_proxy":
        blockers.append("valuation_kind_incompatible")
    source_refs = valuation.get("source_refs")
    if not isinstance(source_refs, (list, tuple)) or not tuple(
        ref for ref in source_refs if str(ref).strip()
    ):
        blockers.append("valuation_source_refs_absent")
    coordinates: dict[str, float] = {}
    for name in _FUND_VALUATION_COORDINATES:
        value = valuation.get(name)
        if isinstance(value, bool) or value is None:
            blockers.append(f"valuation_coordinate_absent:{name}")
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            blockers.append(f"valuation_coordinate_invalid:{name}")
            continue
        if not math.isfinite(number):
            blockers.append(f"valuation_coordinate_invalid:{name}")
            continue
        coordinates[name] = number
    return (None, tuple(sorted(set(blockers)))) if blockers else (coordinates, ())


def _latest_values(path: Path, as_of: str) -> dict[tuple[str, str], tuple[float, str]]:
    cutoff = canonical_timestamp(as_of, "watchlist as_of")
    latest: dict[tuple[str, str], tuple[tuple[Any, ...], float, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                available = str(row["available_at"])
                if available > cutoff:
                    continue
                key = (str(row["entity_id"]), str(row["metric_id"]))
                rank = (available, str(row["observed_at"]), str(row["observation_id"]))
                if key not in latest or rank > latest[key][0]:
                    latest[key] = (rank, float(row["value"]), str(row["source_ref"]))
            except (KeyError, TypeError, ValueError):
                continue
    return {key: (row[1], row[2]) for key, row in latest.items()}


def _resolved_premium(row: Mapping[str, Any], latest: Mapping[tuple[str, str], tuple[float, str]]) -> tuple[float, list[str]]:
    metric = row.get("expected_premium_metric")
    if isinstance(metric, Mapping):
        key = (str(metric.get("entity_id") or ""), str(metric.get("metric_id") or ""))
        if key not in latest:
            raise ValueError(f"missing watchlist factor-premium metric: {key[0]}.{key[1]}")
        value, source_ref = latest[key]
        return value, [source_ref]
    return require_finite(row.get("expected_annual_premium", 0), "expected factor premium"), []


def _criterion(value: float, raw: Mapping[str, Any]) -> dict[str, Any]:
    criterion_id = require_text(raw.get("id"), "watchlist criterion id")
    operator = require_text(raw.get("operator"), f"criterion {criterion_id} operator")
    threshold = require_finite(raw.get("value"), f"criterion {criterion_id} value")
    if operator == "ge":
        passed = value >= threshold
    elif operator == "gt":
        passed = value > threshold
    elif operator == "le":
        passed = value <= threshold
    elif operator == "lt":
        passed = value < threshold
    else:
        raise ValueError(f"unsupported watchlist criterion operator: {operator}")
    return {"criterion_id": criterion_id, "operator": operator, "threshold": threshold, "observed": value, "passed": passed}


def _fund_valuation(
    *,
    evidence: list[dict[str, Any]],
    required_return: float,
    payout_ratio_assumptions: Any,
) -> dict[str, Any] | None:
    """Compile transparent aggregate earnings-power and expectations proxies."""
    values = {str(row["metric_id"]): float(row["value"]) for row in evidence}
    refs = sorted({str(row["source_ref"]) for row in evidence})
    price_to_earnings = values.get("portfolio_price_to_earnings")
    price_to_book = values.get("portfolio_price_to_book")
    expense_ratio = values.get("expense_ratio")
    earnings_yield = values.get("portfolio_earnings_yield")
    if earnings_yield is None and price_to_earnings and price_to_earnings > 0:
        earnings_yield = 1.0 / price_to_earnings
    book_to_price = values.get("portfolio_book_to_price")
    if book_to_price is None and price_to_book and price_to_book > 0:
        book_to_price = 1.0 / price_to_book
    net_earnings_yield = values.get("portfolio_net_earnings_yield")
    if net_earnings_yield is None and earnings_yield is not None and expense_ratio is not None:
        net_earnings_yield = earnings_yield - expense_ratio
    if (
        earnings_yield is None or book_to_price is None or expense_ratio is None
        or net_earnings_yield is None or required_return <= 0
    ):
        return None
    raw_payouts = payout_ratio_assumptions or [0.35, 0.50, 0.65]
    if not isinstance(raw_payouts, list) or not raw_payouts:
        raise ValueError("fund payout_ratio_assumptions must be a nonempty list")
    payouts = sorted({require_finite(value, "fund payout-ratio assumption") for value in raw_payouts})
    if any(value <= 0 or value > 1 for value in payouts):
        raise ValueError("fund payout-ratio assumptions must be in (0, 1]")
    implied_growth = [required_return - payout * earnings_yield + expense_ratio for payout in payouts]
    earnings_power_margin = net_earnings_yield / required_return - 1.0
    implied_roe = earnings_yield / book_to_price if book_to_price and book_to_price > 0 else None
    return {
        "valuation_kind": "aggregate_expectations_proxy",
        "earnings_yield": earnings_yield,
        "book_to_price": book_to_price,
        "price_to_earnings": price_to_earnings,
        "price_to_book": price_to_book,
        "expense_ratio": expense_ratio,
        "net_earnings_yield": net_earnings_yield,
        "required_return": required_return,
        "earnings_power_margin": earnings_power_margin,
        "implied_growth_low": min(implied_growth),
        "implied_growth_median": median(implied_growth),
        "implied_growth_high": max(implied_growth),
        "implied_roe": implied_roe,
        "payout_ratio_assumptions": payouts,
        "formulas": {
            "net_earnings_yield": "portfolio_earnings_yield - expense_ratio",
            "earnings_power_margin": "net_earnings_yield / factor_required_return - 1",
            "implied_growth": "factor_required_return - payout_ratio * portfolio_earnings_yield + expense_ratio",
            "implied_roe": "portfolio_earnings_yield / portfolio_book_to_price",
        },
        "source_refs": refs,
        "use_boundary": (
            "Aggregate P/E and P/B exclude loss-making holdings and do not substitute for holdings-level "
            "cash-flow underwriting. Implied growth varies with the declared payout-ratio grid."
        ),
    }


def _fund_choice_frontier(
    *, watchlist_id: str, as_of: str, candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Retain non-dominated fund substitutes without inventing a utility function."""
    objectives = (
        ("factor_implied_return", "maximize"),
        ("earnings_power_margin", "maximize"),
        ("implied_growth", "minimize"),
        ("expense_ratio", "minimize"),
        ("drawdown_resilience", "maximize"),
    )
    rows: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for candidate in candidates:
        valuation = candidate.get("valuation")
        valuation_coordinates, valuation_blockers = bound_fund_valuation_coordinates(
            valuation
        )
        if valuation_coordinates is None:
            excluded.append({
                "entity_id": candidate["entity_id"],
                "reason": (
                    "aggregate_valuation_unavailable"
                    if not isinstance(valuation, Mapping)
                    else "aggregate_valuation_lineage_incompatible"
                ),
                "missing_metrics": sorted(set(
                    map(str, candidate.get("missing_valuation_metrics") or ())
                ) | set(valuation_blockers)),
            })
            continue
        analysis = candidate["analysis"]
        betas = analysis["coefficients"]["betas"]
        implied = dict(analysis.get("assumption_implied") or {})
        historical = dict(analysis.get("historical") or {})
        factor_return = float(implied["return_without_residual_alpha"])
        values = {
            "factor_implied_return": factor_return,
            "earnings_power_margin": valuation_coordinates["earnings_power_margin"],
            "implied_growth": valuation_coordinates["implied_growth_median"],
            "expense_ratio": valuation_coordinates["expense_ratio"],
            "drawdown_resilience": float(analysis["historical"]["maximum_drawdown"]),
        }
        rows.append({
            "entity_id": candidate["entity_id"], "name": candidate["name"],
            "category": candidate["category"],
            "vehicle_kind": candidate.get("vehicle_kind") or "public_fund",
            "implementation_sleeve_id": candidate.get("implementation_sleeve_id"),
            "implementation_sleeve_source_refs": list(
                candidate.get("implementation_sleeve_source_refs") or ()
            ),
            "objective_values": values,
            "investment_potential": dict(candidate.get("investment_potential") or {}),
            "factor_exposures": {key: float(value) for key, value in sorted(betas.items())},
            "residual_alpha_uncertainty": {
                **dict(historical.get("residual_alpha_uncertainty") or {}),
                "historical_residual_alpha_annualized": historical.get(
                    "residual_alpha_annualized"
                ),
                "historical_residual_tracking_error": historical.get(
                    "residual_tracking_error"
                ),
                "historical_information_ratio": historical.get("information_ratio"),
                "profile_alpha_persistence_weight": float(
                    implied.get("alpha_persistence_weight", 0.0)
                ),
                "factor_frontier_alpha_credit": 0.0,
                "factor_implied_return_without_residual_alpha": factor_return,
                "sample_precision_status": (
                    "sample_interval_includes_zero"
                    if (historical.get("residual_alpha_uncertainty") or {}).get(
                        "interval_includes_zero", True
                    ) else "sample_interval_excludes_zero"
                ),
                "precision_status": "prospective_record_required",
                "activation": (
                    "settled prospective abnormal-return forecast record with "
                    "declared benchmark and epoch"
                ),
            },
            "fund_evidence": dict(candidate.get("fund_evidence") or {}),
            "source_refs": sorted(set(
                list(analysis.get("source_refs") or ())
                + list(valuation.get("source_refs") or ())
                + list((candidate.get("fund_evidence") or {}).get("source_refs") or ())
            )),
        })

    rows.sort(key=lambda row: row["entity_id"])
    excluded.sort(key=lambda row: row["entity_id"])

    directions = dict(objectives)

    def dominates(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
        if left.get("implementation_sleeve_id") != right.get("implementation_sleeve_id"):
            return False
        a, b = left["objective_values"], right["objective_values"]
        no_worse = all(
            a[key] >= b[key] - 1e-12 if direction == "maximize"
            else a[key] <= b[key] + 1e-12
            for key, direction in objectives
        )
        better = any(
            a[key] > b[key] + 1e-12 if directions[key] == "maximize"
            else a[key] < b[key] - 1e-12
            for key, _direction in objectives
        )
        return no_worse and better

    frontier_ids = sorted(
        row["entity_id"] for row in rows
        if not any(dominates(other, row) for other in rows if other is not row)
    )
    domination_witnesses = {
        row["entity_id"]: sorted(
            other["entity_id"] for other in rows if other is not row and dominates(other, row)
        )[0]
        for row in rows if row["entity_id"] not in frontier_ids
    }

    def distance(left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
        keys = sorted(set(left["factor_exposures"]) & set(right["factor_exposures"]))
        return math.sqrt(sum(
            (left["factor_exposures"][key] - right["factor_exposures"][key]) ** 2
            for key in keys
        ) / len(keys)) if keys else math.inf

    for row in rows:
        row["frontier_status"] = "frontier" if row["entity_id"] in frontier_ids else "dominated"
        substitutes = [
            other for other in rows if other is not row
            and other.get("implementation_sleeve_id") == row.get("implementation_sleeve_id")
        ]
        row["nearest_substitutes"] = [
            {
                "entity_id": other["entity_id"],
                "factor_distance": distance(row, other),
                "frontier_status": "frontier" if other["entity_id"] in frontier_ids else "dominated",
            }
            for other in sorted(
                substitutes,
                key=lambda other: (distance(row, other), other["entity_id"]),
            )[:5]
        ]
    rows.sort(key=lambda row: (
        int((row.get("investment_potential") or {}).get("rank") or 10**9),
        row["entity_id"],
    ))
    coverage = {
        metric_id: sum(metric_id in (row.get("fund_evidence") or {}).get("metrics", {}) for row in rows)
        for metric_id in _FUND_EVIDENCE_METRICS
    }
    body = {
        "schema": FUND_CHOICE_FRONTIER_SCHEMA,
        "frontier_id": f"{watchlist_id}:{as_of}",
        "watchlist_id": watchlist_id, "as_of": as_of,
        "implementation_sleeve_ids": sorted({
            str(row["implementation_sleeve_id"]) for row in rows
            if row.get("implementation_sleeve_id")
        }),
        "unbound_implementation_entity_ids": sorted(
            row["entity_id"] for row in rows if not row.get("implementation_sleeve_id")
        ),
        "objective_contract": [
            {"metric_id": metric_id, "direction": direction} for metric_id, direction in objectives
        ],
        "eligible_count": len(rows), "excluded": excluded,
        "alternatives": rows, "frontier_entity_ids": frontier_ids,
        "domination_witnesses": domination_witnesses,
        "evidence_coverage": coverage,
        "scope_closed": not excluded,
        "representation_residuals": [
            "Holdings concentration, spread, assets, turnover, and tax fit remain evidence coordinates until every compared fund has compatible issuer or regulatory observations.",
            "The frontier retains tradeoffs; an account-specific tax and portfolio-fit utility is required to choose one fund.",
        ],
        "use_boundary": (
            "The frontier compares frozen factor and aggregate-valuation coordinates. "
            "Historical residual alpha is excluded, and no fund or capital action is selected."
        ),
    }
    return {**body, "fund_choice_frontier_sha256": stable_sha256(body)}


def compile_fund_holdings_graph(
    *, root: Path, as_of: str, fund_entity_ids: set[str], target_entity_id: str,
) -> dict[str, Any]:
    """Compile comparable-fund overlap and the next issuer-evidence frontier."""
    snapshot_dir = root / "data" / "fund_holdings"
    snapshots: list[dict[str, Any]] = []
    for path in sorted(snapshot_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        entity_id = str(payload.get("entity_id") or "").upper()
        if (
            payload.get("schema") != "jaggedthoughts-fund-holdings-snapshot-v1"
            or entity_id not in fund_entity_ids
        ):
            continue
        weights = {
            str(row.get("identifier") or "").upper(): float(row["weight"])
            for row in payload.get("holdings") or ()
            if isinstance(row, Mapping) and row.get("identifier") and float(row.get("weight") or 0) > 0
        }
        snapshots.append({
            "entity_id": entity_id, "as_of": payload.get("as_of"),
            "available_at": payload.get("available_at"),
            "snapshot_path": path.relative_to(root).as_posix(),
            "snapshot_sha256": payload.get("snapshot_sha256"),
            "source_id": payload.get("source_id"),
            "disclosed_weight": float(payload.get("disclosed_weight") or sum(weights.values())),
            "position_count": len(weights), "weights": weights,
            "holdings": payload.get("holdings") or [],
        })
    snapshots.sort(key=lambda row: row["entity_id"])
    pairs: list[dict[str, Any]] = []
    for index, left in enumerate(snapshots):
        for right in snapshots[index + 1:]:
            left_keys, right_keys = set(left["weights"]), set(right["weights"])
            shared = sorted(left_keys & right_keys)
            weighted_overlap = sum(min(left["weights"][key], right["weights"][key]) for key in shared)
            pairs.append({
                "left_entity_id": left["entity_id"], "right_entity_id": right["entity_id"],
                "shared_holding_count": len(shared),
                "holding_jaccard_similarity": 1.0 - jaccard_distance(left_keys, right_keys),
                "weighted_overlap": weighted_overlap,
                "disclosed_active_share": 1.0 - weighted_overlap,
                "left_shared_weight": sum(left["weights"][key] for key in shared),
                "right_shared_weight": sum(right["weights"][key] for key in shared),
                "shared_identifiers": shared,
            })
    pairs.sort(key=lambda row: (
        -float(row["weighted_overlap"]), row["left_entity_id"], row["right_entity_id"],
    ))
    manifest = yaml.safe_load((root / "sources.yaml").read_text(encoding="utf-8"))
    enrolled = {
        str(row.get("entity_id") or "").upper()
        for row in (manifest.get("sources") or ())
        if isinstance(row, Mapping) and row.get("adapter") == "sec_companyfacts"
    }
    membership: dict[str, list[dict[str, Any]]] = {}
    names: dict[str, str] = {}
    for snapshot in snapshots:
        for holding in snapshot["holdings"]:
            if not isinstance(holding, Mapping) or not holding.get("identifier"):
                continue
            ticker = str(holding["identifier"]).upper()
            weight = float(holding.get("weight") or 0)
            if weight <= 0:
                continue
            membership.setdefault(ticker, []).append({
                "fund_entity_id": snapshot["entity_id"], "weight": weight,
            })
            names.setdefault(ticker, str(holding.get("security_name") or ticker))
    target = next((row for row in snapshots if row["entity_id"] == target_entity_id), None)
    target_weights = dict(target["weights"]) if target else {}
    acquisition_rows: list[dict[str, Any]] = []
    for ticker, positions in sorted(membership.items()):
        if ticker not in target_weights:
            continue
        quality_path = root / "quality" / f"{ticker.lower()}.json"
        quality_available = quality_path.is_file()
        acquisition_rows.append({
            "entity_id": ticker, "name": names[ticker],
            "target_fund_weight": target_weights[ticker],
            "aggregate_disclosed_weight": sum(float(row["weight"]) for row in positions),
            "fund_count": len(positions),
            "fund_memberships": sorted(positions, key=lambda row: row["fund_entity_id"]),
            "sec_source_enrolled": ticker in enrolled,
            "company_quality_available": quality_available,
            "quality_path": quality_path.relative_to(root).as_posix() if quality_available else None,
            "next_action": (
                "covered" if quality_available else
                "repair_metric_coverage" if ticker in enrolled else "enroll_public_equity"
            ),
        })
    unresolved = [row for row in acquisition_rows if not row["company_quality_available"]]

    def dominates(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
        keys = ("target_fund_weight", "aggregate_disclosed_weight", "fund_count")
        return (
            all(float(left[key]) >= float(right[key]) - 1e-12 for key in keys)
            and any(float(left[key]) > float(right[key]) + 1e-12 for key in keys)
        )

    frontier_ids = sorted(
        row["entity_id"] for row in unresolved
        if not any(dominates(other, row) for other in unresolved if other is not row)
    )
    for row in acquisition_rows:
        row["frontier_status"] = (
            "covered" if row["company_quality_available"] else
            "frontier" if row["entity_id"] in frontier_ids else "dominated"
        )
    acquisition_rows.sort(key=lambda row: (
        row["company_quality_available"], -float(row["target_fund_weight"]),
        -int(row["fund_count"]), -float(row["aggregate_disclosed_weight"]), row["entity_id"],
    ))
    target_disclosed_weight = sum(target_weights.values())
    enrolled_weight = sum(
        float(row["target_fund_weight"]) for row in acquisition_rows if row["sec_source_enrolled"]
    )
    quality_weight = sum(
        float(row["target_fund_weight"]) for row in acquisition_rows if row["company_quality_available"]
    )
    available_ids = {row["entity_id"] for row in snapshots}
    body = {
        "schema": FUND_HOLDINGS_GRAPH_SCHEMA, "as_of": as_of,
        "available_at": max(
            (as_of, *(str(row["available_at"]) for row in snapshots)),
            key=timestamp_key,
        ),
        "target_entity_id": target_entity_id,
        "fund_snapshot_count": len(snapshots),
        "fund_snapshot_entity_ids": sorted(available_ids),
        "missing_fund_entity_ids": sorted(fund_entity_ids - available_ids),
        "snapshots": [{key: value for key, value in row.items() if key not in {"weights", "holdings"}} for row in snapshots],
        "pairwise_overlap": pairs,
        "target_coverage": {
            "target_position_count": len(target_weights),
            "target_disclosed_weight": target_disclosed_weight,
            "sec_enrolled_position_count": sum(row["sec_source_enrolled"] for row in acquisition_rows),
            "sec_enrolled_weight": enrolled_weight,
            "company_quality_position_count": sum(row["company_quality_available"] for row in acquisition_rows),
            "company_quality_weight": quality_weight,
            "uncovered_weight": max(0.0, target_disclosed_weight - quality_weight),
        },
        "acquisition_objectives": [
            {"metric_id": "target_fund_weight", "direction": "maximize"},
            {"metric_id": "aggregate_disclosed_weight", "direction": "maximize"},
            {"metric_id": "fund_count", "direction": "maximize"},
        ],
        "acquisition_frontier_entity_ids": frontier_ids,
        "acquisition_queue": acquisition_rows,
        "scope_closed": not (fund_entity_ids - available_ids),
        "use_boundary": (
            "Overlap is computed from provider-disclosed equity weights at their recorded epochs. "
            "The acquisition queue orders evidence coverage, not expected return or a trade action."
        ),
    }
    return {**body, "fund_holdings_graph_sha256": stable_sha256(body)}


def compile_fund_watchlist(
    profile_path: str | Path, *, workspace: str | Path
) -> dict[str, Any]:
    """Compile fund candidates into exposure analyses and a qualified queue."""
    root = Path(workspace).expanduser().resolve()
    path = Path(profile_path).expanduser().resolve()
    profile = _load_yaml(path)
    source_run_path = root / "data" / "latest_source_run.json"
    if not source_run_path.is_file():
        raise ValueError("watchlist compilation requires a public-source run")
    source_run = json.loads(source_run_path.read_text(encoding="utf-8"))
    as_of = canonical_timestamp(source_run.get("as_of"), "watchlist source as_of")
    observations_path = root / "data" / "observations.csv"
    latest = _latest_values(observations_path, as_of)
    risk_free_metric = profile.get("risk_free_metric") or {}
    if not isinstance(risk_free_metric, Mapping):
        raise ValueError("watchlist risk_free_metric must be a mapping")
    risk_free_key = (str(risk_free_metric.get("entity_id") or ""), str(risk_free_metric.get("metric_id") or ""))
    if risk_free_key not in latest:
        raise ValueError(f"missing watchlist risk-free metric: {risk_free_key[0]}.{risk_free_key[1]}")
    risk_free, risk_free_ref = latest[risk_free_key]
    raw_factors = profile.get("factors")
    if not isinstance(raw_factors, list) or not raw_factors:
        raise ValueError("watchlist factors must be a nonempty list")
    factors: list[FactorDefinition] = []
    premium_refs: set[str] = {risk_free_ref}
    for raw in raw_factors:
        if not isinstance(raw, Mapping):
            raise ValueError("watchlist factor must be a mapping")
        premium, refs = _resolved_premium(raw, latest)
        premium_refs.update(refs)
        factors.append(FactorDefinition(
            factor_id=str(raw.get("id") or ""),
            long_entity_id=str(raw.get("long_entity_id") or ""),
            short_entity_id=str(raw.get("short_entity_id") or ""),
            expected_annual_premium=premium,
        ))
    raw_candidates = profile.get("candidates")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise ValueError("watchlist candidates must be a nonempty list")
    price_entity_ids = {
        str(raw.get("entity_id") or "").upper()
        for raw in raw_candidates if isinstance(raw, Mapping)
    }
    price_entity_ids.update(
        entity_id.upper()
        for factor in factors
        for entity_id in (factor.long_entity_id, factor.short_entity_id)
        if entity_id
    )
    points = load_price_points(
        observations_path, as_of=as_of, metric_id="adjusted_price",
        entity_ids=price_entity_ids,
    )
    results: list[dict[str, Any]] = []
    for raw in raw_candidates:
        if not isinstance(raw, Mapping):
            raise ValueError("watchlist candidate must be a mapping")
        entity_id = require_text(raw.get("entity_id"), "watchlist candidate entity_id")
        implementation_sleeve_id = raw.get("implementation_sleeve_id")
        implementation_sleeve_source_refs: tuple[str, ...] = ()
        if implementation_sleeve_id is not None:
            implementation_sleeve_id = require_text(
                implementation_sleeve_id, f"{entity_id} implementation_sleeve_id",
            )
            if implementation_sleeve_id not in PUBLIC_SLEEVE_IDS:
                raise ValueError(
                    f"{entity_id} implementation_sleeve_id must be one of "
                    f"{', '.join(PUBLIC_SLEEVE_IDS)}"
                )
            implementation_sleeve_source_refs = require_refs(
                raw.get("implementation_sleeve_source_refs") or (),
                f"{entity_id} implementation_sleeve_source_refs",
            )
        analysis = analyze_factor_exposure(
            analysis_id=f"{profile['watchlist_id']}:{entity_id}:{as_of}",
            candidate_entity_id=entity_id,
            factors=factors,
            price_points=points,
            as_of=as_of,
            risk_free_rate=risk_free,
            alpha_persistence_weight=float(raw.get("alpha_persistence_weight", 0)),
            min_observations=int(profile.get("min_observations", 120)),
        )
        paths: dict[str, float] = {
            "factor.leave_one_out_r2": float(analysis["fit"]["leave_one_out_r2"]),
            "factor.residual_alpha": float(analysis["historical"]["residual_alpha_annualized"]),
            "factor.tracking_error": float(analysis["historical"]["residual_tracking_error"]),
            "factor.maximum_drawdown": float(analysis["historical"]["maximum_drawdown"]),
            "factor.implied_return": float(analysis["assumption_implied"]["return_without_residual_alpha"]),
            **{f"factor.beta.{name}": float(value) for name, value in analysis["coefficients"]["betas"].items()},
        }
        raw_criteria = raw.get("criteria") or profile.get("criteria") or []
        if not isinstance(raw_criteria, list):
            raise ValueError("watchlist criteria must be a list")
        criteria: list[dict[str, Any]] = []
        for criterion in raw_criteria:
            if not isinstance(criterion, Mapping):
                raise ValueError("watchlist criterion must be a mapping")
            path_id = require_text(criterion.get("path"), "watchlist criterion path")
            if path_id not in paths:
                raise ValueError(f"watchlist criterion references unknown path: {path_id}")
            criteria.append({"path": path_id, **_criterion(paths[path_id], criterion)})
        valuation_inputs = raw.get("valuation_inputs") or []
        if not isinstance(valuation_inputs, list):
            raise ValueError("candidate valuation_inputs must be a list")
        missing_valuation = []
        valuation_evidence: list[dict[str, Any]] = []
        for metric in valuation_inputs:
            metric_id = str(metric)
            key = (entity_id, metric_id)
            if key not in latest:
                missing_valuation.append(metric_id)
            else:
                value, source_ref = latest[key]
                valuation_evidence.append({"metric_id": metric_id, "value": value, "source_ref": source_ref})
        required_passes = all(row["passed"] for row in criteria)
        valuation_ready = bool(valuation_inputs) and not missing_valuation
        valuation = _fund_valuation(
            evidence=valuation_evidence,
            required_return=float(analysis["assumption_implied"]["return_without_residual_alpha"]),
            payout_ratio_assumptions=raw.get("payout_ratio_assumptions"),
        ) if valuation_ready else None
        if valuation is not None:
            paths.update({
                "valuation.earnings_power_margin": float(valuation["earnings_power_margin"]),
                "valuation.implied_growth": float(valuation["implied_growth_median"]),
                "valuation.net_earnings_yield": float(valuation["net_earnings_yield"]),
            })
        fund_metrics: dict[str, float] = {}
        fund_refs: set[str] = set()
        for metric_id in _FUND_EVIDENCE_METRICS:
            observed = latest.get((entity_id, metric_id))
            if observed is not None:
                fund_metrics[metric_id] = float(observed[0])
                fund_refs.add(str(observed[1]))
        holdings_path = root / "data" / "fund_holdings" / f"{entity_id.lower()}.json"
        results.append({
            "candidate_id": str(raw.get("id") or entity_id),
            "entity_id": entity_id,
            "name": str(raw.get("name") or entity_id),
            "vehicle_kind": str(raw.get("vehicle_kind") or "public_fund"),
            "category": str(raw.get("category") or ""),
            "implementation_sleeve_id": implementation_sleeve_id,
            "implementation_sleeve_source_refs": list(
                implementation_sleeve_source_refs
            ),
            "thesis_prompt": str(raw.get("thesis_prompt") or ""),
            "analysis": analysis,
            "criteria": criteria,
            "screen_status": "qualified" if required_passes else "monitor",
            "valuation_evidence": valuation_evidence,
            "valuation": valuation,
            "missing_valuation_metrics": missing_valuation,
            "valuation_claim_allowed": valuation is not None,
            "fund_evidence": {
                "metrics": fund_metrics, "source_refs": sorted(fund_refs),
                "holdings_snapshot_path": (
                    holdings_path.relative_to(root).as_posix() if holdings_path.is_file() else None
                ),
            },
            "opportunity_kind": "valued_fund_candidate" if valuation is not None and required_passes else "factor_exposure_candidate",
            "screen_expected_return_basis": "risk_free_plus_declared_factor_premiums_without_residual_alpha",
            "next_evidence_request": (
                "Compare aggregate holdings valuation and earnings quality with category peers."
                if not valuation_ready else "Review holdings concentration, rebalance policy, fees, liquidity, and tax fit."
            ),
        })
    peer_groups: dict[str, list[dict[str, Any]]] = {}
    for row in results:
        peer_groups.setdefault(str(row.get("implementation_sleeve_id") or "unbound"), []).append(row)

    def potential_coordinates(row: dict[str, Any]) -> dict[str, float] | None:
        valuation, blockers = bound_fund_valuation_coordinates(row.get("valuation"))
        if blockers:
            row["valuation_coordinate_blockers"] = list(blockers)
            return None
        if not row.get("implementation_sleeve_id"):
            return None
        analysis = row["analysis"]
        volatility = float(analysis["historical"]["candidate_annualized_volatility"])
        if volatility <= 0:
            row["valuation_coordinate_blockers"] = ["candidate_volatility_nonpositive"]
            return None
        return {
            "earnings_yield": float(valuation["earnings_yield"]),
            "book_to_price": float(valuation["book_to_price"]),
            "earnings_power_margin": float(valuation["earnings_power_margin"]),
            "factor_return_after_fee": float(
                analysis["assumption_implied"]["return_without_residual_alpha"]
            ) - float(valuation["expense_ratio"]),
            "factor_return_per_volatility": float(
                analysis["assumption_implied"]["return_without_residual_alpha"]
            ) / volatility,
            "drawdown_resilience": float(analysis["historical"]["maximum_drawdown"]),
            "fee_efficiency": -float(valuation["expense_ratio"]),
            "factor_fit_coverage": float(analysis["fit"]["leave_one_out_r2"]),
        }

    coordinates_by_id = {
        str(row["candidate_id"]): potential_coordinates(row) for row in results
    }

    def percentile(values: list[float], value: float) -> float:
        values = sorted(values)
        if not values:
            return 0.0
        below = sum(candidate < value for candidate in values)
        equal = sum(candidate == value for candidate in values)
        return (below + 0.5 * equal) / len(values)

    for row in results:
        coordinates = coordinates_by_id[str(row["candidate_id"])]
        if coordinates is None:
            coordinate_blockers = list(row.pop("valuation_coordinate_blockers", []))
            row["investment_potential"] = {
                "status": (
                    "blocked_missing_implementation_sleeve"
                    if not coordinate_blockers and row.get("valuation")
                    and not row.get("implementation_sleeve_id")
                    else "blocked_incompatible_valuation_lineage"
                    if coordinate_blockers != ["aggregate_valuation_absent"]
                    else "blocked_missing_aggregate_valuation"
                ),
                "score": None,
                "blockers": coordinate_blockers,
                "is_expected_alpha": False,
            }
            continue
        peers = peer_groups[str(row.get("implementation_sleeve_id") or "unbound")]
        component_scores = {
            name: percentile([
                peer_coordinates[name]
                for peer in peers
                if (peer_coordinates := coordinates_by_id[str(peer["candidate_id"])]) is not None
            ], value)
            for name, value in coordinates.items()
        }
        score, family_scores = fund_potential_family_score(component_scores)
        row["investment_potential"] = {
            "status": "ranked_for_research",
            "score": score,
            "peer_group": str(row.get("implementation_sleeve_id") or "unbound"),
            "component_scores": component_scores,
            "family_scores": family_scores,
            "family_weights": {
                family: weight for family, (weight, _) in _FUND_POTENTIAL_FAMILIES.items()
            },
            "evidence_vote_receipt": fund_evidence_vote_receipt(
                component_scores,
                analysis_sha256=str(row["analysis"].get("analysis_sha256") or "") or None,
                valuation_source_refs=list((row.get("valuation") or {}).get("source_refs") or ()),
            ),
            "coordinates": coordinates,
            "residual_alpha_credit": 0.0,
            "is_expected_alpha": False,
            "use_boundary": (
                "Cross-sectional research priority within the implementation sleeve; "
                "not expected alpha, a buy signal, or portfolio utility."
            ),
        }

    for peer_group, peers in peer_groups.items():
        ranked_peers = sorted(
            (
                row for row in peers
                if row["investment_potential"]["score"] is not None
            ),
            key=lambda row: (
                -float(row["investment_potential"]["score"]), row["entity_id"],
            ),
        )
        for rank, row in enumerate(ranked_peers, start=1):
            row["investment_potential"].update({
                "rank": rank, "ranked_count": len(ranked_peers),
                "rank_scope": f"implementation_sleeve:{peer_group}",
            })
    results.sort(key=lambda row: (
        row["screen_status"] != "qualified",
        row["investment_potential"]["score"] is None,
        int(row["investment_potential"].get("rank") or 10**9),
        str(row["investment_potential"].get("peer_group") or "unbound"),
        row["entity_id"],
    ))
    watchlist_id = require_text(profile.get("watchlist_id"), "watchlist_id")
    if profile.get("implementation_sleeve_id") is not None:
        raise ValueError(
            "implementation_sleeve_id belongs to each fund candidate, not the watchlist"
        )
    choice_frontier = _fund_choice_frontier(
        watchlist_id=watchlist_id, as_of=as_of, candidates=results,
    )
    holdings_graph = compile_fund_holdings_graph(
        root=root, as_of=as_of,
        fund_entity_ids={str(row["entity_id"]).upper() for row in results},
        target_entity_id=str(profile.get("lookthrough_target_entity_id") or "FNK").upper(),
    )
    body: dict[str, Any] = {
        "schema": WATCHLIST_RESULT_SCHEMA,
        "compiler_version": _WATCHLIST_ENGINE_VERSION,
        "compiler_available_at": _WATCHLIST_ENGINE_AVAILABLE_AT,
        "watchlist_id": watchlist_id,
        "implementation_sleeve_ids": choice_frontier["implementation_sleeve_ids"],
        "as_of": as_of,
        "profile_path": path.relative_to(root).as_posix(),
        "profile_sha256": stable_sha256(profile),
        "candidate_count": len(results),
        "qualified_count": sum(row["screen_status"] == "qualified" for row in results),
        "candidates": results,
        "fund_choice_frontier": choice_frontier,
        "fund_holdings_graph": holdings_graph,
        "factor_premium_source_refs": sorted(premium_refs),
        "use_boundary": (
            "The queue can automate evidence triage and conditional benchmarking. "
            "It cannot label a fund undervalued until the configured holdings-level or aggregate valuation inputs exist."
        ),
    }
    return {**body, "watchlist_sha256": stable_sha256(body)}


__all__ = [
    "FUND_CHOICE_FRONTIER_SCHEMA", "FUND_EVIDENCE_VOTE_RECEIPT_SCHEMA",
    "FUND_HOLDINGS_GRAPH_SCHEMA",
    "WATCHLIST_RESULT_SCHEMA", "WATCHLIST_SCHEMA",
    "bound_fund_valuation_coordinates", "compile_fund_holdings_graph", "compile_fund_watchlist",
    "fund_evidence_vote_receipt", "fund_potential_family_score",
    "verify_fund_evidence_vote_receipt",
]
