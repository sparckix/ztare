"""Household balance-sheet and goal-aware strategic allocation.

The security engine ranks funds and companies.  This module owns the slower
decision above it: how much household capital may be exposed to each sleeve
after currencies, liabilities, liquidity, human capital, and a dated wealth
goal are represented.  It emits paper policy coordinates, never orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import math
from typing import Any, Iterable, Mapping

import numpy as np

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_finite, require_refs, require_text, timestamp_key


HOUSEHOLD_MANDATE_SCHEMA = "jaggedthoughts-household-capital-mandate-v1"
CAPITAL_MARKET_BASIS_SCHEMA = "jaggedthoughts-capital-market-basis-v1"
HOUSEHOLD_ALLOCATION_SCHEMA = "jaggedthoughts-household-allocation-frontier-v1"


def _digest(value: Any, label: str) -> str:
    digest = require_text(value, label)
    if len(digest) != 64:
        raise ValueError(f"{label} must be a SHA-256 digest")
    try:
        int(digest, 16)
    except ValueError as error:
        raise ValueError(f"{label} must be a SHA-256 digest") from error
    return digest


def _sealed(raw: Mapping[str, Any], *, schema: str, field: str) -> dict[str, Any]:
    body = dict(raw)
    if body.get("schema") != schema:
        raise ValueError(f"expected {schema}")
    claimed = _digest(body.pop(field, ""), field)
    if stable_sha256(body) != claimed:
        raise ValueError(f"{schema} content hash mismatch")
    return {**body, field: claimed}


def _money(value: Any, label: str) -> float:
    amount = require_finite(value, label)
    if amount < 0:
        raise ValueError(f"{label} cannot be negative")
    return amount


def _fx(currency: Any, base: str, rates: Mapping[str, Any]) -> float:
    code = require_text(currency, "currency").upper()
    if code == base:
        return 1.0
    rate = require_finite(rates.get(code), f"fx_to_base.{code}")
    if rate <= 0:
        raise ValueError(f"fx_to_base.{code} must be positive")
    return rate


def _simplex_units(parts: int, total: int) -> Iterable[tuple[int, ...]]:
    """Enumerate integer simplex points without permutations or recursion state."""
    if parts == 1:
        yield (total,)
        return
    # Stars-and-bars: separator positions determine every ordered composition.
    for separators in combinations(range(total + parts - 1), parts - 1):
        points = (-1, *separators, total + parts - 1)
        yield tuple(points[index + 1] - points[index] - 1 for index in range(parts))


@dataclass(frozen=True, slots=True)
class _AssetClass:
    asset_id: str
    risk_bucket: str
    currency: str
    volatility: float
    minimum_weight: float
    maximum_weight: float


def compile_household_mandate(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a source-bound household mandate and expose missing decisions."""
    if raw.get("schema") != HOUSEHOLD_MANDATE_SCHEMA:
        raise ValueError(f"household mandate schema must be {HOUSEHOLD_MANDATE_SCHEMA}")
    mandate_id = require_text(raw.get("mandate_id"), "mandate_id")
    mandate_purpose = str(raw.get("mandate_purpose") or "operator_policy")
    if mandate_purpose not in {"operator_policy", "planning_scenario"}:
        raise ValueError("mandate_purpose must be operator_policy or planning_scenario")
    as_of = canonical_timestamp(raw.get("as_of"), "household mandate as_of")
    base = require_text(raw.get("base_currency"), "base_currency").upper()
    fx_rates = dict(raw.get("fx_to_base") or {})
    source_refs = require_refs(raw.get("source_refs") or (), "household source_refs")

    assets: list[dict[str, Any]] = []
    asset_ids: set[str] = set()
    for source in raw.get("assets") or ():
        row = dict(source)
        asset_id = require_text(row.get("asset_id"), "asset.asset_id")
        if asset_id in asset_ids:
            raise ValueError(f"duplicate household asset: {asset_id}")
        asset_ids.add(asset_id)
        amount = _money(row.get("value"), f"asset.{asset_id}.value")
        rate = _fx(row.get("currency"), base, fx_rates)
        assets.append({
            "asset_id": asset_id,
            "kind": require_text(row.get("kind"), f"asset.{asset_id}.kind"),
            "currency": require_text(row.get("currency"), f"asset.{asset_id}.currency").upper(),
            "value": amount,
            "value_base": amount * rate,
            "liquid": bool(row.get("liquid")),
            "investable": bool(row.get("investable")),
            "source_ref": require_text(row.get("source_ref"), f"asset.{asset_id}.source_ref"),
        })

    liabilities: list[dict[str, Any]] = []
    liability_ids: set[str] = set()
    for source in raw.get("liabilities") or ():
        row = dict(source)
        liability_id = require_text(row.get("liability_id"), "liability.liability_id")
        if liability_id in liability_ids:
            raise ValueError(f"duplicate household liability: {liability_id}")
        liability_ids.add(liability_id)
        balance = _money(row.get("balance"), f"liability.{liability_id}.balance")
        annual_rate = require_finite(
            row.get("annual_rate"), f"liability.{liability_id}.annual_rate",
        )
        if annual_rate < 0:
            raise ValueError("liability annual_rate cannot be negative")
        currency = require_text(row.get("currency"), f"liability.{liability_id}.currency").upper()
        liabilities.append({
            "liability_id": liability_id,
            "kind": require_text(row.get("kind"), f"liability.{liability_id}.kind"),
            "currency": currency,
            "balance": balance,
            "balance_base": balance * _fx(currency, base, fx_rates),
            "annual_rate": annual_rate,
            "rate_kind": require_text(row.get("rate_kind") or "unknown", "liability.rate_kind"),
            "years_remaining": (
                require_finite(row["years_remaining"], f"liability.{liability_id}.years_remaining")
                if row.get("years_remaining") is not None else None
            ),
            "secured_by_asset_id": row.get("secured_by_asset_id"),
            "source_ref": require_text(
                row.get("source_ref"), f"liability.{liability_id}.source_ref",
            ),
        })

    goal = dict(raw.get("goal") or {})
    target = _money(goal.get("target_wealth"), "goal.target_wealth")
    horizon = int(require_finite(goal.get("horizon_years"), "goal.horizon_years"))
    if horizon < 1:
        raise ValueError("goal.horizon_years must be a positive integer")
    contribution = _money(goal.get("annual_contribution"), "goal.annual_contribution")
    goal_basis = require_text(goal.get("wealth_basis"), "goal.wealth_basis")
    if goal_basis not in {"net_worth", "investable_wealth"}:
        raise ValueError("goal.wealth_basis must be net_worth or investable_wealth")
    minimum_goal_probability = require_finite(
        goal.get("minimum_success_probability", 0.8),
        "goal.minimum_success_probability",
    )
    if not 0 <= minimum_goal_probability <= 1:
        raise ValueError("goal.minimum_success_probability must be in [0, 1]")
    nonportfolio_terminal = None
    if goal.get("nonportfolio_terminal_value") is not None:
        nonportfolio_terminal = _money(
            goal["nonportfolio_terminal_value"], "goal.nonportfolio_terminal_value",
        ) * _fx(
            goal.get("nonportfolio_terminal_currency") or goal.get("currency"),
            base,
            fx_rates,
        )

    constraints = dict(raw.get("constraints") or {})
    liquidity_reserve = _money(
        constraints.get("liquidity_reserve"), "constraints.liquidity_reserve",
    )
    max_risky = require_finite(constraints.get("max_risky_weight"), "max_risky_weight")
    max_loss = require_finite(constraints.get("max_one_year_loss"), "max_one_year_loss")
    max_effective_equity = require_finite(
        constraints.get("max_effective_equity_exposure", 1.0),
        "max_effective_equity_exposure",
    )
    if (
        not 0 <= max_risky <= 1
        or not 0 <= max_loss <= 1
        or not 0 <= max_effective_equity <= 1
    ):
        raise ValueError("household risk constraints must be in [0, 1]")

    priced_assets = sum(row["value_base"] for row in assets)
    liquid_assets = sum(row["value_base"] for row in assets if row["liquid"])
    investable_assets = sum(row["value_base"] for row in assets if row["investable"])
    debt = sum(row["balance_base"] for row in liabilities)
    allocatable = max(0.0, investable_assets - liquidity_reserve)
    net_worth = priced_assets - debt
    starting_wealth = allocatable

    missing: list[str] = []
    person = dict(raw.get("person") or {})
    if mandate_purpose == "operator_policy":
        if person.get("age") is None:
            missing.append("age")
        if not raw.get("tax_residence"):
            missing.append("tax_residence")
        if not raw.get("accounts"):
            missing.append("brokerage_and_retirement_account_inventory")
    tax_policy = dict(raw.get("tax_policy") or {})
    if not tax_policy.get("annual_return_haircuts"):
        missing.append("after_tax_return_policy")
    currency_policy = dict(raw.get("currency_policy") or {})
    minimum_currency_weights = dict(currency_policy.get("minimum_asset_weights") or {})
    for currency, value in minimum_currency_weights.items():
        weight = require_finite(value, f"currency_policy.minimum_asset_weights.{currency}")
        if not 0 <= weight <= 1:
            raise ValueError("minimum currency weights must be in [0, 1]")
    if (
        mandate_purpose == "operator_policy"
        and any(row["currency"] != base for row in liabilities)
        and not minimum_currency_weights
        and currency_policy.get("liability_currency_treatment")
        != "unhedged_liability_currency_risk_reviewed"
    ):
        missing.append("liability_currency_policy")
    if any(row["kind"] == "mortgage" and row.get("secured_by_asset_id") not in asset_ids
           for row in liabilities):
        missing.append("mortgaged_property_value")
    if goal_basis == "net_worth" and nonportfolio_terminal is None:
        missing.append("nonportfolio_terminal_value_for_net_worth_goal")

    human = dict(raw.get("human_capital") or {})
    human_capital: dict[str, Any] = {"present_value_base": None, "market_beta": None}
    if human and human.get("included", True):
        income = _money(human.get("annual_net_income"), "human_capital.annual_net_income")
        years = int(require_finite(human.get("years"), "human_capital.years"))
        growth = require_finite(human.get("annual_growth"), "human_capital.annual_growth")
        discount = require_finite(human.get("discount_rate"), "human_capital.discount_rate")
        if years < 1 or discount <= -1 or growth <= -1:
            raise ValueError("invalid human-capital horizon or rates")
        income_base = income * _fx(human.get("currency"), base, fx_rates)
        pv = sum(income_base * (1 + growth) ** year / (1 + discount) ** (year + 1)
                 for year in range(years))
        human_capital = {
            "present_value_base": pv,
            "market_beta": require_finite(human.get("market_beta"), "human_capital.market_beta"),
            "years": years,
            "income_source_ref": require_text(
                human.get("source_ref"), "human_capital.source_ref",
            ),
        }
    elif (
        mandate_purpose == "operator_policy"
        and human.get("included") is False
        and human.get("exclusion_attestation") == "exclude_from_paper_policy_reviewed"
    ):
        human_capital = {
            "included": False,
            "present_value_base": 0.0,
            "market_beta": 0.0,
            "exclusion_attestation": human["exclusion_attestation"],
        }
    elif mandate_purpose == "operator_policy":
        missing.append("after_tax_human_capital_contract")
    else:
        human_capital = {
            "included": False,
            "present_value_base": 0.0,
            "market_beta": 0.0,
        }

    body = {
        "schema": HOUSEHOLD_MANDATE_SCHEMA,
        "mandate_id": mandate_id,
        "mandate_purpose": mandate_purpose,
        "as_of": as_of,
        "base_currency": base,
        "person": person,
        "tax_residence": raw.get("tax_residence"),
        "assets": sorted(assets, key=lambda row: row["asset_id"]),
        "liabilities": sorted(liabilities, key=lambda row: row["liability_id"]),
        "accounts": list(raw.get("accounts") or ()),
        "tax_policy": tax_policy,
        "currency_policy": {
            **currency_policy,
            "minimum_asset_weights": {
                str(currency).upper(): require_finite(value, "minimum currency weight")
                for currency, value in minimum_currency_weights.items()
            },
        },
        "goal": {
            "target_wealth_base": target * _fx(goal.get("currency"), base, fx_rates),
            "target_currency": require_text(goal.get("currency"), "goal.currency").upper(),
            "horizon_years": horizon,
            "annual_contribution_base": contribution * _fx(
                goal.get("contribution_currency") or goal.get("currency"), base, fx_rates,
            ),
            "wealth_basis": goal_basis,
            "minimum_success_probability": minimum_goal_probability,
            "nonportfolio_terminal_value_base": nonportfolio_terminal,
        },
        "constraints": {
            "liquidity_reserve_base": liquidity_reserve,
            "max_risky_weight": max_risky,
            "max_one_year_loss": max_loss,
            "max_effective_equity_exposure": max_effective_equity,
            "weight_step": require_finite(constraints.get("weight_step", 0.1), "weight_step"),
            "max_programs": int(require_finite(
                constraints.get("max_programs", 50_000), "max_programs",
            )),
        },
        "balance_sheet": {
            "priced_assets_base": priced_assets,
            "liquid_assets_base": liquid_assets,
            "investable_assets_base": investable_assets,
            "liabilities_base": debt,
            "priced_net_worth_base": net_worth,
            "allocatable_wealth_base": allocatable,
            "portfolio_starting_wealth_base": starting_wealth,
        },
        "human_capital": human_capital,
        "readiness": {
            "complete": not missing,
            "missing": sorted(set(missing)),
        },
        "source_refs": list(source_refs),
        "authority": (
            "private_planning_input" if mandate_purpose == "operator_policy"
            else "private_assumption_labeled_scenario_input"
        ),
        "policy_authority": mandate_purpose == "operator_policy",
        "capital_authority": False,
        "brokerage_authority": False,
    }
    return {**body, "mandate_sha256": stable_sha256(body)}


def compile_capital_market_basis(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate point-in-time asset-class moments and explicit return scenarios."""
    if raw.get("schema") != CAPITAL_MARKET_BASIS_SCHEMA:
        raise ValueError(f"capital-market schema must be {CAPITAL_MARKET_BASIS_SCHEMA}")
    as_of = canonical_timestamp(raw.get("as_of"), "capital-market basis as_of")
    assets: list[_AssetClass] = []
    for source in raw.get("asset_classes") or ():
        row = dict(source)
        volatility = require_finite(row.get("volatility"), "asset_class.volatility")
        minimum = require_finite(row.get("minimum_weight", 0), "asset_class.minimum_weight")
        maximum = require_finite(row.get("maximum_weight", 1), "asset_class.maximum_weight")
        if volatility < 0 or not 0 <= minimum <= maximum <= 1:
            raise ValueError("invalid asset-class volatility or weight corridor")
        assets.append(_AssetClass(
            asset_id=require_text(row.get("asset_id"), "asset_class.asset_id"),
            risk_bucket=require_text(row.get("risk_bucket"), "asset_class.risk_bucket"),
            currency=require_text(row.get("currency"), "asset_class.currency").upper(),
            volatility=volatility,
            minimum_weight=minimum,
            maximum_weight=maximum,
        ))
    if len(assets) < 2 or len({row.asset_id for row in assets}) != len(assets):
        raise ValueError("capital-market basis requires at least two unique asset classes")
    ids = [row.asset_id for row in assets]
    correlations = dict(raw.get("correlations") or {})
    corr = np.eye(len(assets), dtype=float)
    for i, left in enumerate(ids):
        left_row = dict(correlations.get(left) or {})
        for j, right in enumerate(ids):
            if i == j:
                continue
            value = require_finite(left_row.get(right), f"correlations.{left}.{right}")
            if not -1 <= value <= 1:
                raise ValueError("correlations must be in [-1, 1]")
            corr[i, j] = value
    if not np.allclose(corr, corr.T, atol=1e-12):
        raise ValueError("correlation matrix must be symmetric")
    covariance = corr * np.outer(
        np.array([row.volatility for row in assets]),
        np.array([row.volatility for row in assets]),
    )
    eigenvalues = np.linalg.eigvalsh(covariance)
    if float(eigenvalues.min()) < -1e-10:
        raise ValueError("asset-class covariance matrix must be positive semidefinite")

    scenarios = []
    for source in raw.get("return_scenarios") or ():
        row = dict(source)
        returns = dict(row.get("expected_returns") or {})
        if set(returns) != set(ids):
            raise ValueError("each return scenario must cover the exact asset-class universe")
        scenarios.append({
            "scenario_id": require_text(row.get("scenario_id"), "return_scenario.scenario_id"),
            "expected_returns": {key: require_finite(returns[key], f"return.{key}") for key in ids},
            "source_refs": list(require_refs(
                row.get("source_refs") or (), "return_scenario.source_refs",
            )),
            "expected_return_claim": False,
        })
    if not scenarios or len({row["scenario_id"] for row in scenarios}) != len(scenarios):
        raise ValueError("capital-market basis requires unique return scenarios")
    body = {
        "schema": CAPITAL_MARKET_BASIS_SCHEMA,
        "basis_id": require_text(raw.get("basis_id"), "basis_id"),
        "as_of": as_of,
        "asset_classes": [{
            "asset_id": row.asset_id,
            "risk_bucket": row.risk_bucket,
            "currency": row.currency,
            "volatility": row.volatility,
            "minimum_weight": row.minimum_weight,
            "maximum_weight": row.maximum_weight,
        } for row in assets],
        "correlation_matrix": corr.tolist(),
        "covariance_matrix": covariance.tolist(),
        "covariance_min_eigenvalue": float(eigenvalues.min()),
        "return_scenarios": sorted(scenarios, key=lambda row: row["scenario_id"]),
        "source_refs": list(require_refs(raw.get("source_refs") or (), "capital-market source_refs")),
        "boundary": (
            "Returns are explicit capital-market assumptions. Historical means, factor-implied "
            "returns, and research ranks do not become forecasts through this contract."
        ),
        "capital_authority": False,
    }
    return {**body, "basis_sha256": stable_sha256(body)}


def _risk_contributions(weights: np.ndarray, covariance: np.ndarray) -> np.ndarray:
    variance = float(weights @ covariance @ weights)
    if variance <= 1e-18:
        return np.zeros_like(weights)
    return weights * (covariance @ weights) / variance


def _dominates(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    better_or_equal = (
        left["robust_expected_return"] >= right["robust_expected_return"] - 1e-12
        and left["volatility"] <= right["volatility"] + 1e-12
        and left["robust_goal_probability"] >= right["robust_goal_probability"] - 1e-12
    )
    strict = (
        left["robust_expected_return"] > right["robust_expected_return"] + 1e-12
        or left["volatility"] < right["volatility"] - 1e-12
        or left["robust_goal_probability"] > right["robust_goal_probability"] + 1e-12
    )
    return better_or_equal and strict


def _required_return(start: float, contribution: float, target: float, years: int) -> float | None:
    if start + contribution * years >= target:
        return 0.0
    if start <= 0 and contribution <= 0:
        return None

    def terminal(rate: float) -> float:
        wealth = start
        for _ in range(years):
            wealth = wealth * (1 + rate) + contribution
        return wealth

    low, high = 0.0, 1.0
    while terminal(high) < target and high < 16:
        high *= 2
    if terminal(high) < target:
        return None
    for _ in range(100):
        midpoint = (low + high) / 2
        if terminal(midpoint) >= target:
            high = midpoint
        else:
            low = midpoint
    return high


def _return_model_decision_closure(
    *, programs: list[dict[str, Any]], return_scenarios: list[dict[str, Any]],
    minimum_goal_probability: float, robust_selected: Mapping[str, Any],
    simulation_paths: int,
) -> dict[str, Any]:
    """Close exact goal-policy decisions across source-bound return-model worlds."""
    worlds = []
    for scenario in return_scenarios:
        scenario_id = str(scenario["scenario_id"])
        candidates = [
            (program, next(
                row for row in program["scenario_outcomes"]
                if row["scenario_id"] == scenario_id
            ))
            for program in programs
        ]
        satisfying = [
            row for row in candidates
            if row[1]["goal_probability"] >= minimum_goal_probability
        ]
        selected, outcome = (
            min(satisfying, key=lambda row: (
                row[0]["volatility"], -row[1]["expected_return_assumption"],
                row[0]["program_id"],
            ))
            if satisfying else min(candidates, key=lambda row: (
                -row[1]["goal_probability"], row[0]["volatility"],
                -row[1]["expected_return_assumption"], row[0]["program_id"],
            ))
        )
        decision_body = {"selected_sleeve_weights": selected["weights"]}
        world_body = {
            "scenario_id": scenario_id,
            "source_refs": list(scenario["source_refs"]),
            "selected_program_id": selected["program_id"],
            "selected_sleeve_weights": selected["weights"],
            "decision_id": stable_sha256(decision_body),
            "goal_probability": outcome["goal_probability"],
            "expected_return_assumption": outcome["expected_return_assumption"],
            "volatility": selected["volatility"],
        }
        worlds.append({**world_body, "world_sha256": stable_sha256(world_body)})

    grouped: dict[str, list[dict[str, Any]]] = {}
    for world in worlds:
        grouped.setdefault(str(world["decision_id"]), []).append(world)
    classes = [{
        "decision_id": decision_id,
        "selected_sleeve_weights": members[0]["selected_sleeve_weights"],
        "scenario_ids": [row["scenario_id"] for row in members],
        "world_count": len(members),
    } for decision_id, members in sorted(grouped.items())]
    robust_decision_id = stable_sha256({
        "selected_sleeve_weights": robust_selected["weights"],
    })
    sleeve_ids = sorted(robust_selected["weights"])
    weight_ranges = [{
        "sleeve_id": sleeve_id,
        "minimum_weight": min(row["selected_sleeve_weights"][sleeve_id] for row in worlds),
        "maximum_weight": max(row["selected_sleeve_weights"][sleeve_id] for row in worlds),
    } for sleeve_id in sleeve_ids]
    body = {
        "schema": "jaggedthoughts-return-model-decision-closure-v1",
        "world_count": len(worlds),
        "decision_class_count": len(classes),
        "model_worlds": worlds,
        "decision_classes": classes,
        "selected_weight_ranges": weight_ranges,
        "robust_selected_decision_id": robust_decision_id,
        "robust_selected_is_model_world_decision": robust_decision_id in grouped,
        "decision_invariant_across_return_models": len(classes) == 1,
        "scope_exhausted": True,
        "probability_interpretation": False,
        "simulation_path_count": simulation_paths,
        "goal_probability_resolution": 1.0 / simulation_paths,
        "goal_probability_calibrated": False,
        "selection_rule": (
            "lowest_volatility_policy_meeting_goal_else_best_goal_probability_"
            "within_each_source_bound_return_model"
        ),
        "authority": "planning_model_sensitivity_only",
        "policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "closure_sha256": stable_sha256(body)}


def _annual_wealth_quantiles(
    *, start: float, contribution: float, expected_return: float,
    volatility: float, normal_draws: np.ndarray,
) -> list[dict[str, float | int]]:
    """Return the visible path for one selected program, using its frozen draws."""
    wealth = np.full(normal_draws.shape[0], start, dtype=float)
    rows: list[dict[str, float | int]] = [{
        "year": 0, "median_base": start, "p10_base": start,
    }]
    drift = math.log1p(max(-0.999999, expected_return)) - 0.5 * volatility**2
    for year in range(normal_draws.shape[1]):
        growth = (
            np.full(normal_draws.shape[0], 1 + expected_return, dtype=float)
            if volatility <= 1e-15 else
            np.exp(drift + volatility * normal_draws[:, year])
        )
        wealth = wealth * growth + contribution
        rows.append({
            "year": year + 1,
            "median_base": float(np.median(wealth)),
            "p10_base": float(np.quantile(wealth, 0.1)),
        })
    return rows


def compile_household_allocation_frontier(
    *, mandate: Mapping[str, Any], capital_market_basis: Mapping[str, Any],
    simulation_paths: int = 512, simulation_seed_identity: str | None = None,
) -> dict[str, Any]:
    """Enumerate the constrained simplex, close its frontier, and size no security."""
    household = _sealed(
        mandate, schema=HOUSEHOLD_MANDATE_SCHEMA, field="mandate_sha256",
    )
    basis = _sealed(
        capital_market_basis, schema=CAPITAL_MARKET_BASIS_SCHEMA, field="basis_sha256",
    )
    scenario_only = household.get("mandate_purpose") == "planning_scenario"
    if timestamp_key(household["as_of"]) > timestamp_key(basis["as_of"]):
        raise ValueError("household mandate cannot postdate the capital-market basis")
    if simulation_paths < 128:
        raise ValueError("goal simulation requires at least 128 paths")
    if not household["readiness"]["complete"]:
        body = {
            "schema": HOUSEHOLD_ALLOCATION_SCHEMA,
            "as_of": basis["as_of"],
            "mandate_sha256": household["mandate_sha256"],
            "basis_sha256": basis["basis_sha256"],
            "status": "mandate_incomplete",
            "blockers": list(household["readiness"]["missing"]),
            "program_count": 0,
            "frontier": [],
            "selected_policy": None,
            "authority": "private_paper_planning_only",
            "capital_authority": False,
            "brokerage_authority": False,
        }
        return {**body, "allocation_sha256": stable_sha256(body)}

    asset_rows = list(basis["asset_classes"])
    asset_ids = [str(row["asset_id"]) for row in asset_rows]
    tax_haircuts = dict(household["tax_policy"].get("annual_return_haircuts") or {})
    if set(tax_haircuts) != set(asset_ids):
        raise ValueError("after-tax return haircuts must cover the exact asset-class universe")
    haircuts = np.array([
        require_finite(tax_haircuts[asset_id], f"tax_haircut.{asset_id}")
        for asset_id in asset_ids
    ])
    if np.any(haircuts < 0):
        raise ValueError("after-tax return haircuts cannot be negative")
    minimum_currency_weights = dict(
        household["currency_policy"].get("minimum_asset_weights") or {}
    )
    basis_currencies = {str(row["currency"]) for row in asset_rows}
    missing_currencies = sorted(set(minimum_currency_weights) - basis_currencies)
    if missing_currencies:
        body = {
            "schema": HOUSEHOLD_ALLOCATION_SCHEMA,
            "as_of": household["as_of"],
            "mandate_sha256": household["mandate_sha256"],
            "basis_sha256": basis["basis_sha256"],
            "status": "capital_market_basis_incomplete",
            "blockers": [
                f"missing_asset_class_currency:{currency}" for currency in missing_currencies
            ],
            "program_count": 0,
            "frontier": [],
            "selected_policy": None,
            "authority": "private_paper_planning_only",
            "capital_authority": False,
            "brokerage_authority": False,
        }
        return {**body, "allocation_sha256": stable_sha256(body)}
    cash_ids = [
        str(row["asset_id"]) for row in asset_rows if row["risk_bucket"] == "cash"
    ]
    covariance = np.array(basis["covariance_matrix"], dtype=float)
    constraints = household["constraints"]
    step = require_finite(constraints["weight_step"], "weight_step")
    units = round(1 / step)
    if not 0 < step <= 1 or not math.isclose(units * step, 1.0, abs_tol=1e-9):
        raise ValueError("weight_step must divide one exactly")
    maximum_programs = int(constraints["max_programs"])
    theoretical_count = math.comb(units + len(asset_ids) - 1, len(asset_ids) - 1)
    if theoretical_count > maximum_programs:
        raise ValueError(
            f"allocation program count {theoretical_count} exceeds max_programs {maximum_programs}"
        )

    goal = household["goal"]
    start = float(household["balance_sheet"]["portfolio_starting_wealth_base"])
    contribution = float(goal["annual_contribution_base"])
    target = float(goal["target_wealth_base"])
    if goal["wealth_basis"] == "net_worth":
        target = max(0.0, target - float(goal["nonportfolio_terminal_value_base"]))
    years = int(goal["horizon_years"])
    required_return = _required_return(start, contribution, target, years)
    seed_basis = str(simulation_seed_identity or household["mandate_sha256"]).strip()
    if not seed_basis:
        raise ValueError("simulation_seed_identity must be nonempty when supplied")
    seed = int(stable_sha256({
        "simulation_seed_identity": seed_basis,
        "asset_ids": asset_ids,
        "covariance_matrix": basis["covariance_matrix"],
        "paths": simulation_paths,
    })[:16], 16)
    normal_draws = np.random.default_rng(seed).standard_normal((simulation_paths, years))
    human_capital = household["human_capital"]
    human_capital_pv = float(human_capital.get("present_value_base") or 0.0)
    human_capital_beta = max(0.0, float(human_capital.get("market_beta") or 0.0))
    economic_wealth = start + human_capital_pv

    programs: list[dict[str, Any]] = []
    for integer_weights in _simplex_units(len(asset_ids), units):
        weights = np.array(integer_weights, dtype=float) / units
        if any(
            weights[index] < float(row["minimum_weight"]) - 1e-12
            or weights[index] > float(row["maximum_weight"]) + 1e-12
            for index, row in enumerate(asset_rows)
        ):
            continue
        if any(
            sum(
                weights[index] for index, row in enumerate(asset_rows)
                if row["currency"] == currency
            ) < float(minimum_weight) - 1e-12
            for currency, minimum_weight in minimum_currency_weights.items()
        ):
            continue
        risky_weight = sum(
            weights[index] for index, row in enumerate(asset_rows)
            if row["risk_bucket"] == "risky"
        )
        if risky_weight > float(constraints["max_risky_weight"]) + 1e-12:
            continue
        effective_equity_exposure = (
            (float(risky_weight) * start + human_capital_beta * human_capital_pv)
            / economic_wealth
            if economic_wealth > 0 else float(risky_weight)
        )
        if (
            effective_equity_exposure
            > float(constraints["max_effective_equity_exposure"]) + 1e-12
        ):
            continue
        variance = max(0.0, float(weights @ covariance @ weights))
        volatility = math.sqrt(variance)
        risk_contributions = _risk_contributions(weights, covariance)
        scenario_rows = []
        for scenario in basis["return_scenarios"]:
            gross_vector = np.array([
                float(scenario["expected_returns"][asset_id]) for asset_id in asset_ids
            ])
            vector = gross_vector - haircuts
            expected = float(weights @ vector)
            wealth = np.full(simulation_paths, start, dtype=float)
            if volatility <= 1e-15:
                growth = np.full(simulation_paths, 1 + expected, dtype=float)
                for _ in range(years):
                    wealth = wealth * growth + contribution
            else:
                drift = math.log1p(max(-0.999999, expected)) - 0.5 * volatility**2
                for year in range(years):
                    wealth = wealth * np.exp(drift + volatility * normal_draws[:, year]) + contribution
            scenario_rows.append({
                "scenario_id": scenario["scenario_id"],
                "gross_expected_return_assumption": float(weights @ gross_vector),
                "expected_return_assumption": expected,
                "return_basis": "after_tax_policy_haircut",
                "cash_return_assumption": (
                    min(
                        float(scenario["expected_returns"][asset_id])
                        - float(haircuts[asset_ids.index(asset_id)])
                        for asset_id in cash_ids
                    )
                    if cash_ids else 0.0
                ),
                "goal_probability": float(np.mean(wealth >= target)),
                "terminal_median_base": float(np.median(wealth)),
                "terminal_p10_base": float(np.quantile(wealth, 0.1)),
            })
        robust_return = min(row["expected_return_assumption"] for row in scenario_rows)
        robust_excess_return = min(
            row["expected_return_assumption"] - row["cash_return_assumption"]
            for row in scenario_rows
        )
        robust_goal = min(row["goal_probability"] for row in scenario_rows)
        loss_proxy = max(0.0, -(robust_return - 2.326347874 * volatility))
        if loss_proxy > float(constraints["max_one_year_loss"]) + 1e-12:
            continue
        risk_values = [
            risk_contributions[index] for index, row in enumerate(asset_rows)
            if row["risk_bucket"] == "risky" and weights[index] > 0
        ]
        risk_dispersion = float(np.std(risk_values)) if len(risk_values) > 1 else 0.0
        weight_map = {asset_id: float(weights[index]) for index, asset_id in enumerate(asset_ids)}
        program_body = {
            "weights": weight_map,
            "risky_weight": float(risky_weight),
            "effective_equity_exposure_including_human_capital": effective_equity_exposure,
            "robust_expected_return": robust_return,
            "robust_excess_return": robust_excess_return,
            "volatility": volatility,
            "normal_loss_99_proxy": loss_proxy,
            "robust_goal_probability": robust_goal,
            "risk_contributions": {
                asset_id: float(risk_contributions[index])
                for index, asset_id in enumerate(asset_ids)
            },
            "risk_contribution_dispersion": risk_dispersion,
            "scenario_outcomes": scenario_rows,
        }
        programs.append({
            **program_body,
            "program_id": f"household-policy:{stable_sha256(program_body)[:16]}",
        })
    if not programs:
        raise ValueError("household constraints admit no allocation policy")

    frontier = [
        row for row in programs
        if not any(_dominates(other, row) for other in programs if other is not row)
    ]
    frontier.sort(key=lambda row: (
        -row["robust_goal_probability"], -row["robust_expected_return"],
        row["volatility"], row["program_id"],
    ))
    goal_satisfying = [
        row for row in frontier
        if row["robust_goal_probability"] >= goal["minimum_success_probability"]
    ]
    selected = (
        min(goal_satisfying, key=lambda row: (
            row["volatility"], -row["robust_expected_return"], row["program_id"],
        ))
        if goal_satisfying
        else min(frontier, key=lambda row: (
            -row["robust_goal_probability"], row["volatility"],
            -row["robust_expected_return"], row["program_id"],
        ))
    )
    risk_budget_candidates = [
        row for row in programs
        if sum(
            row["weights"][str(asset["asset_id"])] > 0
            for asset in asset_rows if asset["risk_bucket"] == "risky"
        ) >= 2
    ] or programs
    anchors = {
        "goal_selected": selected["program_id"],
        "minimum_variance": min(programs, key=lambda row: (row["volatility"], row["program_id"]))["program_id"],
        "maximum_robust_sharpe": max(
            programs,
            key=lambda row: (
                row["robust_excess_return"] / row["volatility"]
                if row["volatility"] > 1e-15 else -math.inf,
                row["program_id"],
            ),
        )["program_id"],
        "risk_budget": min(
            risk_budget_candidates,
            key=lambda row: (
                row["risk_contribution_dispersion"], -row["robust_goal_probability"],
                row["program_id"],
            ),
        )["program_id"],
    }
    programs_by_id = {row["program_id"]: row for row in programs}
    rival_roles = {
        "goal_selected": "lowest_volatility_policy_meeting_goal_else_best_goal_probability",
        "minimum_variance": "lowest_asset_class_variance",
        "maximum_robust_sharpe": "highest_worst_scenario_excess_return_per_unit_volatility",
        "risk_budget": "most_even_risky_asset_risk_contributions",
    }
    policy_rivals = [{
        "rival_id": rival_id,
        "selection_role": rival_roles[rival_id],
        "selected": program_id == selected["program_id"],
        "program": programs_by_id[program_id],
    } for rival_id, program_id in anchors.items()]
    selected_wealth_paths = [{
        "scenario_id": outcome["scenario_id"],
        "annual_wealth_path": _annual_wealth_quantiles(
            start=start,
            contribution=contribution,
            expected_return=float(outcome["expected_return_assumption"]),
            volatility=float(selected["volatility"]),
            normal_draws=normal_draws,
        ),
    } for outcome in selected["scenario_outcomes"]]
    return_model_decision_closure = _return_model_decision_closure(
        programs=programs,
        return_scenarios=list(basis["return_scenarios"]),
        minimum_goal_probability=float(goal["minimum_success_probability"]),
        robust_selected=selected,
        simulation_paths=simulation_paths,
    )

    cash_returns = [
        min(
            float(scenario["expected_returns"][asset_id])
            - float(haircuts[asset_ids.index(asset_id)])
            for asset_id in cash_ids
        )
        for scenario in basis["return_scenarios"]
    ] if cash_ids else []
    cash_hurdle = min(cash_returns, default=-math.inf)
    debt_frontier = []
    for liability in household["liabilities"]:
        rate = float(liability["annual_rate"])
        if rate <= 0:
            posture = "preserve_zero_cost_option"
        elif cash_hurdle != -math.inf and rate > cash_hurdle:
            posture = "paydown_dominates_cash_before_tax"
        else:
            posture = "compare_after_tax_paydown_with_investment_frontier"
        debt_frontier.append({
            "liability_id": liability["liability_id"],
            "balance_base": liability["balance_base"],
            "guaranteed_nominal_paydown_return": rate,
            "posture": posture,
            "tax_adjusted": False,
        })

    body = {
        "schema": HOUSEHOLD_ALLOCATION_SCHEMA,
        "as_of": basis["as_of"],
        "mandate_sha256": household["mandate_sha256"],
        "basis_sha256": basis["basis_sha256"],
        "status": "planning_scenario_ready" if scenario_only else "paper_policy_ready",
        "goal": {
            **goal,
            "portfolio_starting_wealth_base": start,
            "portfolio_terminal_target_base": target,
            "required_constant_return": required_return,
            "selected_robust_goal_probability": selected["robust_goal_probability"],
            "target_meets_declared_probability": (
                selected["robust_goal_probability"] >= goal["minimum_success_probability"]
            ),
        },
        "enumeration": {
            "weight_step": step,
            "simplex_program_count": theoretical_count,
            "feasible_program_count": len(programs),
            "scope_exhausted": True,
        },
        "frontier": frontier,
        "frontier_program_ids": [row["program_id"] for row in frontier],
        "selected_policy": selected,
        "selected_wealth_paths": selected_wealth_paths,
        "anchor_policies": anchors,
        "policy_rivals": policy_rivals,
        "return_model_decision_closure": return_model_decision_closure,
        "debt_paydown_frontier": debt_frontier,
        "simulation": {
            "paths": simulation_paths,
            "years": years,
            "common_random_numbers": True,
            "return_distribution": "annual lognormal moment approximation",
            "goal_probability_calibrated": False,
            "use": "planning_scenario_comparison",
            "seed_sha256": stable_sha256(seed),
            "seed_scope": (
                "declared_cross_scenario_common_random_numbers"
                if simulation_seed_identity is not None else "mandate_identity"
            ),
        },
        "boundary": (
            "This is an assumption-labeled private planning scenario and cannot enter the paper "
            "policy path. " if scenario_only else
            "This is a private, point-in-time paper policy over asset-class sleeves. "
        ) + (
            "Fund and security selection implement a sleeve only after their own evidence gates; "
            "tax lot selection and order routing remain outside this artifact."
        ),
        "authority": (
            "private_assumption_labeled_scenario_only" if scenario_only
            else "private_paper_planning_only"
        ),
        "policy_authority": not scenario_only,
        "capital_authority": False,
        "brokerage_authority": False,
    }
    return {**body, "allocation_sha256": stable_sha256(body)}


__all__ = [
    "CAPITAL_MARKET_BASIS_SCHEMA",
    "HOUSEHOLD_ALLOCATION_SCHEMA",
    "HOUSEHOLD_MANDATE_SCHEMA",
    "compile_capital_market_basis",
    "compile_household_allocation_frontier",
    "compile_household_mandate",
]
