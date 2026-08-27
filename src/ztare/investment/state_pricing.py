"""Finite-state, source-bound state-price feasibility and bounds."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
from scipy.optimize import linprog

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_finite, require_text, timestamp_key
from .observation_index import load_observation_rows


STATE_PRICE_CONTRACT_SCHEMA = "jaggedthoughts-state-price-contract-v1"
STATE_PRICE_RESULT_SCHEMA = "jaggedthoughts-state-price-result-v1"


def _price_observation(raw: Mapping[str, Any], *, as_of: str, asset_id: str) -> dict[str, Any]:
    observed = canonical_timestamp(raw.get("observed_at"), f"{asset_id} price observed_at")
    available = canonical_timestamp(raw.get("available_at"), f"{asset_id} price available_at")
    if timestamp_key(observed) > timestamp_key(available) or timestamp_key(available) > timestamp_key(as_of):
        raise ValueError("asset price observation crosses its availability epoch")
    value = require_finite(raw.get("value"), f"{asset_id} observed price")
    if value < 0:
        raise ValueError("observed asset prices must be nonnegative")
    return {
        "observation_id": require_text(raw.get("observation_id"), f"{asset_id} price observation_id"),
        "value": value, "unit": require_text(raw.get("unit"), f"{asset_id} price unit"),
        "observed_at": observed, "available_at": available,
        "source_ref": require_text(raw.get("source_ref"), f"{asset_id} price source_ref"),
    }


def compile_state_price_contract(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the identity of one finite payoff-state market."""
    if payload.get("schema") != STATE_PRICE_CONTRACT_SCHEMA:
        raise ValueError(f"state pricing requires {STATE_PRICE_CONTRACT_SCHEMA}")
    as_of = canonical_timestamp(payload.get("as_of"), "state-price as_of")
    horizon_at = canonical_timestamp(payload.get("horizon_at"), "state-price horizon_at")
    if timestamp_key(horizon_at) <= timestamp_key(as_of):
        raise ValueError("state-price horizon must be later than as_of")
    states = []
    for raw in payload.get("states") or ():
        if not isinstance(raw, Mapping):
            raise ValueError("payoff states must be objects")
        states.append({
            "state_id": require_text(raw.get("state_id"), "state_id"),
            "description": require_text(raw.get("description"), "state description"),
        })
    state_ids = [row["state_id"] for row in states]
    if len(state_ids) < 2 or len(state_ids) != len(set(state_ids)):
        raise ValueError("state pricing requires at least two unique payoff states")
    probability = dict(payload.get("probability_contract") or {"kind": "admissible_simplex"})
    probability_kind = require_text(probability.get("kind"), "probability contract kind")
    if probability_kind not in {"admissible_simplex", "declared_scenario_weights"}:
        raise ValueError("probabilities must be an admissible simplex or declared scenario weights")
    weights = None
    if probability_kind == "declared_scenario_weights":
        source_kind = require_text(probability.get("source_kind"), "probability source_kind")
        source_refs = sorted({
            require_text(ref, "probability source ref") for ref in probability.get("source_refs") or ()
        })
        if source_kind == "historical_frequency":
            raise ValueError("historical frequencies cannot become payoff-state probabilities")
        if not source_refs:
            raise ValueError("declared scenario probabilities require a source or authored-scenario identity")
        raw_weights = probability.get("weights") or {}
        if set(raw_weights) != set(state_ids):
            raise ValueError("declared probabilities must cover exactly the payoff states")
        weights = {state: require_finite(raw_weights[state], f"probability {state}") for state in state_ids}
        if any(value <= 0 for value in weights.values()) or abs(sum(weights.values()) - 1.0) > 1e-10:
            raise ValueError("declared payoff-state probabilities must be positive and sum to one")
    assets = []
    for raw in payload.get("assets") or ():
        if not isinstance(raw, Mapping):
            raise ValueError("state-price assets must be objects")
        asset_id = require_text(raw.get("asset_id"), "state-price asset_id")
        payoff_map = raw.get("payoffs") or {}
        if set(payoff_map) != set(state_ids):
            raise ValueError(f"asset {asset_id} payoffs must cover exactly the payoff states")
        price = _price_observation(dict(raw.get("price_observation") or {}), as_of=as_of, asset_id=asset_id)
        payoffs = {state: require_finite(payoff_map[state], f"{asset_id} payoff {state}") for state in state_ids}
        assets.append({
            "asset_id": asset_id, "price_observation": price, "payoffs": payoffs,
            "payoff_source_refs": sorted({
                require_text(ref, f"{asset_id} payoff source ref") for ref in raw.get("payoff_source_refs") or ()
            }),
        })
    asset_ids = [row["asset_id"] for row in assets]
    if len(asset_ids) < 2 or len(asset_ids) != len(set(asset_ids)):
        raise ValueError("state pricing requires at least two unique priced assets")
    if any(not row["payoff_source_refs"] for row in assets):
        raise ValueError("every payoff row requires a source or declared-scenario identity")
    units = {row["price_observation"]["unit"] for row in assets}
    if len(units) != 1:
        raise ValueError("state-price asset prices must share one unit")
    numeraire = require_text(payload.get("numeraire_asset_id"), "numeraire_asset_id")
    if numeraire not in asset_ids:
        raise ValueError("numeraire asset is absent from payoff matrix")
    numeraire_row = assets[asset_ids.index(numeraire)]
    if any(abs(value - 1.0) > 1e-12 for value in numeraire_row["payoffs"].values()):
        raise ValueError("numeraire asset must pay exactly one unit in every state")
    floor = require_finite(payload.get("minimum_state_price"), "minimum_state_price")
    tolerance = require_finite(payload.get("residual_tolerance", 1e-8), "residual_tolerance")
    if floor <= 0 or tolerance <= 0:
        raise ValueError("state-price positivity floor and residual tolerance must be positive")
    body = {
        "schema": STATE_PRICE_CONTRACT_SCHEMA,
        "contract_id": require_text(payload.get("contract_id"), "state-price contract_id"),
        "as_of": as_of, "horizon_at": horizon_at, "states": states,
        "probability_contract": {
            "kind": probability_kind, "weights": weights,
            "source_kind": probability.get("source_kind"),
            "source_refs": sorted(map(str, probability.get("source_refs") or ())),
        },
        "assets": assets, "numeraire_asset_id": numeraire,
        "minimum_state_price": floor, "residual_tolerance": tolerance,
        "authority": "research_pricing_certificate_only", "capital_authority": False,
    }
    return {**body, "contract_sha256": stable_sha256(body)}


def solve_state_prices(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Solve or bound strictly positive Arrow prices for a declared market."""
    contract = compile_state_price_contract(payload)
    states = [row["state_id"] for row in contract["states"]]
    assets = contract["assets"]
    payoff_matrix = np.array([[row["payoffs"][state] for state in states] for row in assets], dtype=float)
    prices = np.array([row["price_observation"]["value"] for row in assets], dtype=float)
    floor = float(contract["minimum_state_price"])
    tolerance = float(contract["residual_tolerance"])
    bounds = [(floor, None)] * len(states)
    feasible = linprog(
        np.zeros(len(states)), A_eq=payoff_matrix, b_eq=prices,
        bounds=bounds, method="highs",
    )
    rank = int(np.linalg.matrix_rank(payoff_matrix, tol=tolerance))
    common = {
        "schema": STATE_PRICE_RESULT_SCHEMA, "contract_id": contract["contract_id"],
        "contract_sha256": contract["contract_sha256"], "as_of": contract["as_of"],
        "horizon_at": contract["horizon_at"], "payoff_matrix_rank": rank,
        "state_count": len(states), "asset_count": len(assets),
        "market_complete": rank == len(states),
        "solver": {"name": "scipy.optimize.linprog", "method": "highs"},
        "authority": "research_pricing_certificate_only", "capital_authority": False,
    }
    if not feasible.success:
        # Minimize the maximum price residual under the same positivity floor.
        # This linear certificate is faster and less fragile than bounded
        # nonlinear least squares on widely scaled payoff grids.
        assets_count, states_count = payoff_matrix.shape
        residual_objective = np.zeros(states_count + 1); residual_objective[-1] = 1.0
        residual_ub = np.vstack((
            np.column_stack((payoff_matrix, -np.ones(assets_count))),
            np.column_stack((-payoff_matrix, -np.ones(assets_count))),
        ))
        residual_rhs = np.concatenate((prices, -prices))
        closest = linprog(
            residual_objective, A_ub=residual_ub, b_ub=residual_rhs,
            bounds=[*bounds, (0.0, None)], method="highs",
        )
        closest_prices = (
            np.array(closest.x[:-1], dtype=float)
            if closest.success else np.full(states_count, floor, dtype=float)
        )
        residuals = payoff_matrix @ closest_prices - prices
        body = {
            **common, "status": "infeasible_positive_state_prices",
            "no_arbitrage_certificate": False, "representative_state_prices": None,
            "state_price_bounds": None, "risk_neutral_probabilities": None,
            "stochastic_discount_kernel": None,
            "residuals": {
                "closest_positive_max_abs_price_residual": float(np.max(np.abs(residuals))),
                "closest_positive_asset_residuals": {
                    assets[index]["asset_id"]: float(value) for index, value in enumerate(residuals)
                },
                "solver_message": feasible.message,
                "closest_positive_solver_message": closest.message,
            },
            "eligibility": {"state_price_bounds": False, "pricing_kernel": False},
            "gaps": ["declared_prices_and_payoffs_reject_a_strictly_positive_state_price_vector"],
        }
        return {**body, "result_sha256": stable_sha256(body)}
    representative = np.array(feasible.x, dtype=float)
    price_residuals = payoff_matrix @ representative - prices
    state_bounds = {}
    for index, state in enumerate(states):
        objective = np.zeros(len(states)); objective[index] = 1.0
        lower = linprog(objective, A_eq=payoff_matrix, b_eq=prices, bounds=bounds, method="highs")
        upper = linprog(-objective, A_eq=payoff_matrix, b_eq=prices, bounds=bounds, method="highs")
        if not lower.success or not upper.success:
            raise RuntimeError("feasible state-price set produced an unbounded coordinate")
        state_bounds[state] = [float(lower.fun), float(-upper.fun)]
    discount = float(representative.sum())
    risk_neutral = {state: float(representative[index] / discount) for index, state in enumerate(states)}
    weights = contract["probability_contract"]["weights"]
    sdf = (
        {state: float(representative[index] / weights[state]) for index, state in enumerate(states)}
        if weights else None
    )
    numeraire = next(row for row in assets if row["asset_id"] == contract["numeraire_asset_id"])
    max_residual = float(np.max(np.abs(price_residuals)))
    certificate = bool(
        np.all(representative >= floor * 0.5)
        and all(values[0] >= floor * 0.5 for values in state_bounds.values())
        and max_residual <= tolerance
    )
    body = {
        **common, "status": "positive_state_prices_feasible" if certificate else "numerical_residual_exceeds_tolerance",
        "no_arbitrage_certificate": certificate,
        "representative_state_prices": {
            state: float(representative[index]) for index, state in enumerate(states)
        },
        "state_price_bounds": state_bounds,
        "discount_factor": discount,
        "risk_neutral_probabilities": {
            "identity": "normalized_state_prices_not_physical_forecast_probabilities",
            "values": risk_neutral,
        },
        "stochastic_discount_kernel": ({
            "identity": "state_price_divided_by_declared_scenario_probability",
            "values": sdf,
        } if sdf else None),
        "residuals": {
            "max_abs_price_residual": max_residual,
            "asset_price_residuals": {
                assets[index]["asset_id"]: float(value) for index, value in enumerate(price_residuals)
            },
            "normalization_residual": discount - float(numeraire["price_observation"]["value"]),
        },
        "eligibility": {
            "state_price_bounds": certificate,
            "pricing_kernel": certificate and weights is not None,
        },
        "gaps": ([] if weights else ["physical_or_declared_scenario_probabilities_absent_sdf_unidentified"]),
    }
    return {**body, "result_sha256": stable_sha256(body)}


def audit_workspace_state_price_readiness(
    workspace: str | Path,
    *,
    latest_observations: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Report what public evidence exists without fabricating payoff states."""
    root = Path(workspace).expanduser().resolve()
    source_run = json.loads((root / "data" / "latest_source_run.json").read_text(encoding="utf-8"))
    as_of = canonical_timestamp(source_run.get("as_of"), "source run as_of")
    if latest_observations is None:
        latest_observations = load_observation_rows(
            root / "data" / "observations.csv", as_of=as_of,
            metric_ids=("price",), latest_per_metric=True,
        )
    prices = {
        str(row["entity_id"]): row
        for row in latest_observations if row.get("metric_id") == "price"
    }
    discovery = json.loads((root / "discovery" / "latest.json").read_text(encoding="utf-8"))
    factor_count = sum(
        bool((row.get("beta_receipt") or {}).get("analysis") or row.get("factor_analysis_sha256"))
        for row in discovery.get("candidates") or () if isinstance(row, Mapping)
    )
    contract_paths = sorted((root / "state_pricing" / "contracts").glob("*.json"))
    results, failures = [], []
    for path in contract_paths:
        try:
            results.append(solve_state_prices(json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, ValueError, json.JSONDecodeError) as error:
            failures.append({"path": path.relative_to(root).as_posix(), "error": str(error)})
    body = {
        "schema": "jaggedthoughts-state-price-workspace-readiness-v1", "as_of": as_of,
        "public_price_entity_count": len(prices), "factor_context_candidate_count": factor_count,
        "payoff_state_contract_count": len(contract_paths), "eligible_contract_count": sum(
            bool(row["eligibility"]["state_price_bounds"]) for row in results
        ),
        "results": results, "failures": failures,
        "can_populate": ["observed spot-price identities", "factor-exposure context", "market ERP context"],
        "cannot_populate": [
            "future state-contingent payoffs", "exhaustive payoff-state identity",
            "physical probabilities from historical frequencies",
        ],
        "next_activation": (
            "Review the compiled state-price certificates."
            if results else
            "Author one source-bound horizon/payoff-state contract under state_pricing/contracts/."
        ),
        "authority": "research_pricing_certificate_only", "capital_authority": False,
    }
    return {**body, "readiness_sha256": stable_sha256(body)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", nargs="?")
    parser.add_argument("--contract")
    args = parser.parse_args(argv)
    if args.contract:
        result = solve_state_prices(json.loads(Path(args.contract).read_text(encoding="utf-8")))
    elif args.workspace:
        result = audit_workspace_state_price_readiness(args.workspace)
    else:
        parser.error("provide a workspace or --contract")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "STATE_PRICE_CONTRACT_SCHEMA", "STATE_PRICE_RESULT_SCHEMA",
    "audit_workspace_state_price_readiness", "compile_state_price_contract", "solve_state_prices",
]
