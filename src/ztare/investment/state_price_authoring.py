"""Compile source-bound payoff-state proposals from valuation scenarios."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_finite, require_refs, require_text, timestamp_key
from .state_pricing import STATE_PRICE_CONTRACT_SCHEMA, compile_state_price_contract, solve_state_prices


PROPOSAL_SCHEMA = "jaggedthoughts-state-price-proposal-v1"
DECLARATION_SCHEMA = "jaggedthoughts-payoff-state-declaration-v1"
MODELED_GRID_SCHEMA = "jaggedthoughts-modeled-payoff-grid-v1"


def _verified_sha(payload: Mapping[str, Any], field: str, label: str) -> str:
    claimed = require_text(payload.get(field), field)
    body = {key: value for key, value in payload.items() if key != field}
    if stable_sha256(body) != claimed:
        raise ValueError(f"{label} digest does not match its payload")
    return claimed


def _scenario_templates(valuation: Mapping[str, Any]) -> list[dict[str, Any]]:
    assumptions = {str(row["assumption_id"]): row for row in valuation.get("assumptions") or ()}
    intrinsic = [row for row in valuation.get("results") or () if row.get("result_type") == "IntrinsicValue"]
    templates = []
    for scenario in valuation.get("scenarios") or ():
        scenario_id = require_text(scenario.get("scenario_id"), "valuation scenario_id")
        coordinates = [
            {
                "program_id": require_text(row.get("program_id"), "valuation program_id"),
                "result_sha256": require_text(row.get("result_sha256"), "valuation result_sha256"),
                "value": require_finite(row.get("value"), "intrinsic-value coordinate"),
                "unit": require_text(row.get("unit"), "intrinsic-value unit"),
                "assumption_ids": list(row.get("assumption_ids") or ()),
                "identity": "present_value_coordinate_not_horizon_payoff",
            }
            for row in intrinsic if scenario_id in (row.get("scenario_ids") or ())
        ]
        templates.append({
            "valuation_scenario_id": scenario_id,
            "mechanism_id": require_text(scenario.get("mechanism_id"), "valuation mechanism_id"),
            "assumptions": [assumptions[str(identity)] for identity in scenario.get("assumption_ids") or ()],
            "source_refs": list(require_refs(scenario.get("source_refs") or (), "scenario source ref")),
            "valuation_coordinates": coordinates,
            "eligible_as_horizon_payoff": False,
        })
    if len(templates) < 2 or any(not row["valuation_coordinates"] for row in templates):
        raise ValueError("payoff-state authoring requires at least two valued scenario identities")
    return templates


def _valuation_spot(valuation: Mapping[str, Any]) -> dict[str, Any]:
    rows = [
        row for row in valuation.get("assumptions") or ()
        if row.get("assumption_type") == "MarketPrice"
    ]
    if len(rows) != 1:
        raise ValueError("valuation envelope requires exactly one market-price assumption")
    row = rows[0]
    refs = require_refs(row.get("source_refs") or (), "market-price source ref")
    epoch = canonical_timestamp(valuation.get("evidence_epoch"), "valuation evidence_epoch")
    return {
        "observation_id": f"valuation-market-price:{valuation['envelope_sha256'][:20]}",
        "value": require_finite(row.get("value"), "valuation market price"),
        "unit": require_text(row.get("unit"), "valuation market-price unit"),
        "observed_at": epoch,
        "available_at": epoch,
        "source_ref": refs[0],
        "identity": "source_bound_valuation_assumption_at_evidence_epoch",
    }


def _compile_declared_contract(
    proposal: Mapping[str, Any], declaration: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    if declaration.get("schema") != DECLARATION_SCHEMA:
        raise ValueError(f"payoff-state declaration requires {DECLARATION_SCHEMA}")
    for field in ("entity_id", "candidate_sha256", "valuation_envelope_sha256"):
        if declaration.get(field) != proposal.get(field):
            raise ValueError(f"payoff-state declaration {field} is not bound to the proposal")
    if declaration.get("exhaustive_within_declared_scope") is not True:
        raise ValueError("payoff states require an explicit exhaustive-within-scope declaration")
    scope = require_text(declaration.get("exhaustiveness_scope"), "exhaustiveness scope")
    exhaustiveness_refs = require_refs(
        declaration.get("exhaustiveness_source_refs") or (), "exhaustiveness source ref"
    )
    templates = {row["valuation_scenario_id"]: row for row in proposal["scenario_templates"]}
    states, bindings, payoffs, payoff_refs, used = [], [], {}, set(exhaustiveness_refs), set()
    for raw in declaration.get("states") or ():
        if not isinstance(raw, Mapping):
            raise ValueError("declared payoff states must be objects")
        state_id = require_text(raw.get("state_id"), "declared state_id")
        scenario_id = require_text(raw.get("valuation_scenario_id"), "declared valuation_scenario_id")
        if scenario_id not in templates:
            raise ValueError(f"unknown valuation scenario: {scenario_id}")
        if state_id in payoffs or scenario_id in used:
            raise ValueError("state and valuation-scenario bindings must be unique")
        payoff = require_finite(raw.get("equity_payoff_at_horizon"), f"{state_id} equity payoff")
        if payoff < 0:
            raise ValueError("public-equity horizon payoffs must be nonnegative")
        refs = require_refs(raw.get("payoff_source_refs") or (), f"{state_id} payoff source ref")
        states.append({
            "state_id": state_id,
            "description": require_text(raw.get("description"), f"{state_id} description"),
        })
        bindings.append({
            "state_id": state_id, "valuation_scenario_id": scenario_id,
            "equity_payoff_at_horizon": payoff, "payoff_source_refs": list(refs),
        })
        payoffs[state_id] = payoff
        payoff_refs.update(refs)
        payoff_refs.update(templates[scenario_id]["source_refs"])
        used.add(scenario_id)
    if len(states) < 2:
        raise ValueError("an exhaustive payoff-state declaration requires at least two states")
    numeraire = declaration.get("numeraire_asset")
    if not isinstance(numeraire, Mapping):
        raise ValueError("a priced numeraire asset declaration is required")
    numeraire_id = require_text(numeraire.get("asset_id"), "numeraire asset_id")
    probability = declaration.get("probability_contract") or {"kind": "admissible_simplex"}
    if not isinstance(probability, Mapping):
        raise ValueError("probability_contract must be an object")
    horizon_at = canonical_timestamp(declaration.get("horizon_at"), "payoff horizon_at")
    contract_seed = {
        "entity_id": proposal["entity_id"], "horizon_at": horizon_at,
        "states": states, "payoffs": payoffs, "scope": scope,
    }
    contract = {
        "schema": STATE_PRICE_CONTRACT_SCHEMA,
        "contract_id": f"payoff-state:{proposal['entity_id']}:{stable_sha256(contract_seed)[:16]}",
        "as_of": proposal["as_of"], "horizon_at": horizon_at, "states": states,
        "probability_contract": probability,
        "assets": [
            {
                "asset_id": proposal["entity_id"],
                "price_observation": proposal["spot_price_observation"],
                "payoffs": payoffs, "payoff_source_refs": sorted(payoff_refs),
            },
            {
                "asset_id": numeraire_id,
                "price_observation": dict(numeraire.get("price_observation") or {}),
                "payoffs": {row["state_id"]: 1.0 for row in states},
                "payoff_source_refs": list(require_refs(
                    numeraire.get("payoff_source_refs") or (), "numeraire payoff source ref"
                )),
            },
        ],
        "numeraire_asset_id": numeraire_id,
        "minimum_state_price": require_finite(
            declaration.get("minimum_state_price", 1e-9), "minimum_state_price"
        ),
        "residual_tolerance": require_finite(
            declaration.get("residual_tolerance", 1e-8), "residual_tolerance"
        ),
    }
    contract = compile_state_price_contract(contract)
    result = solve_state_prices(contract)
    declaration_receipt = {
        "schema": DECLARATION_SCHEMA, "exhaustiveness_scope": scope,
        "exhaustiveness_source_refs": list(exhaustiveness_refs),
        "state_bindings": bindings,
        "physical_probabilities_declared": probability.get("kind") == "declared_scenario_weights",
        "declaration_sha256": stable_sha256(declaration),
    }
    return contract, {"declaration_receipt": declaration_receipt, "state_price_result": result}


def compile_state_price_proposal(
    *, candidate: Mapping[str, Any], valuation: Mapping[str, Any],
    spot_price_observation: Mapping[str, Any], declaration: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind a candidate to exact valuation states; compile only after authored payoff identity."""
    if candidate.get("schema") != "jaggedthoughts-discovery-candidate-v1":
        raise ValueError("state-price proposals require a typed discovery candidate")
    if valuation.get("schema") != "jaggedthoughts-valuation-envelope-v1":
        raise ValueError("state-price proposals require a typed valuation envelope")
    candidate_sha = _verified_sha(candidate, "candidate_sha256", "candidate")
    envelope_sha = _verified_sha(valuation, "envelope_sha256", "valuation envelope")
    entity = require_text(candidate.get("entity_id"), "candidate entity_id").upper()
    if candidate.get("entity_kind") != "public_equity" or valuation.get("entity_id") != entity:
        raise ValueError("payoff-state authoring currently accepts matching public-equity valuations")
    if (candidate.get("valuation") or {}).get("envelope_sha256") != envelope_sha:
        raise ValueError("candidate and valuation envelope digests disagree")
    as_of = canonical_timestamp(candidate.get("as_of"), "candidate as_of")
    if canonical_timestamp(valuation.get("evidence_epoch"), "valuation evidence_epoch") != as_of:
        raise ValueError("candidate and valuation evidence epochs disagree")
    observed = canonical_timestamp(spot_price_observation.get("observed_at"), "spot observed_at")
    available = canonical_timestamp(spot_price_observation.get("available_at"), "spot available_at")
    if timestamp_key(observed) > timestamp_key(available) or timestamp_key(available) > timestamp_key(as_of):
        raise ValueError("spot-price observation crosses the candidate evidence epoch")
    market_price = next(
        row for row in valuation.get("assumptions") or () if row.get("assumption_type") == "MarketPrice"
    )
    spot_value = require_finite(spot_price_observation.get("value"), "spot price")
    if not math.isclose(spot_value, float(market_price["value"]), rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError("spot observation does not equal the valuation market-price assumption")
    if require_text(spot_price_observation.get("source_ref"), "spot source_ref") not in market_price["source_refs"]:
        raise ValueError("spot observation source is absent from the valuation assumption")
    templates = _scenario_templates(valuation)
    body: dict[str, Any] = {
        "schema": PROPOSAL_SCHEMA, "entity_id": entity, "as_of": as_of,
        "candidate_sha256": candidate_sha, "valuation_envelope_sha256": envelope_sha,
        "spot_price_observation": {
            **dict(spot_price_observation), "value": spot_value,
            "observed_at": observed, "available_at": available,
        },
        "scenario_templates": templates,
        "declaration_contract": {
            "schema": DECLARATION_SCHEMA,
            "bound_fields": {
                "entity_id": entity, "candidate_sha256": candidate_sha,
                "valuation_envelope_sha256": envelope_sha,
            },
            "required_fields": [
                "horizon_at", "exhaustive_within_declared_scope", "exhaustiveness_scope",
                "exhaustiveness_source_refs", "states", "numeraire_asset",
            ],
            "state_required_fields": [
                "state_id", "valuation_scenario_id", "description",
                "equity_payoff_at_horizon", "payoff_source_refs",
            ],
            "probability_default": "admissible_simplex_no_physical_probabilities",
        },
        "status": "awaiting_payoff_state_declaration",
        "gaps": [
            "valuation_present_values_are_not_future_state_payoffs",
            "exhaustive_payoff_state_scope_not_declared",
            "state_contingent_horizon_payoffs_not_declared",
            "priced_numeraire_not_declared",
        ],
        "next_activation": "author_payoff_state_declaration",
        "authority": "research_pricing_proposal_only", "capital_authority": False,
    }
    if declaration is not None:
        contract, compiled = _compile_declared_contract(body, declaration)
        body.update({
            "status": "state_price_certificate_compiled",
            "gaps": compiled["state_price_result"]["gaps"],
            "next_activation": "review_state_price_certificate",
            "compiled_contract": contract, **compiled,
        })
    return {**body, "proposal_sha256": stable_sha256(body)}


def _anniversary(as_of: str, years: int) -> str:
    value = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    try:
        value = value.replace(year=value.year + years)
    except ValueError:  # February 29 on a non-leap anniversary.
        value = value.replace(month=2, day=28, year=value.year + years)
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def compile_modeled_payoff_grid(
    *, candidate: Mapping[str, Any], valuation: Mapping[str, Any],
    spot_price_observation: Mapping[str, Any], horizon_years: int = 10,
) -> dict[str, Any]:
    """Project the valuation grammar into conditional future payoffs, then price it."""
    proposal = compile_state_price_proposal(
        candidate=candidate, valuation=valuation, spot_price_observation=spot_price_observation,
    )
    assumptions = {str(row["assumption_id"]): dict(row) for row in valuation.get("assumptions") or ()}
    by_type = {
        str(row["assumption_type"]): dict(row) for row in valuation.get("assumptions") or ()
        if row.get("assumption_type") in {
            "OwnerEarnings", "EquityBeta", "EquityRiskPremium", "RiskFreeRate",
            "ExcessNetCash", "Shares",
        }
    }
    required = {"OwnerEarnings", "EquityBeta", "EquityRiskPremium", "RiskFreeRate", "ExcessNetCash", "Shares"}
    if set(by_type) != required:
        raise ValueError("modeled payoff grid lacks a required valuation assumption")
    horizons = [
        row for row in valuation.get("assumptions") or ()
        if row.get("assumption_type") == "Horizon" and int(float(row.get("value"))) == horizon_years
    ]
    if len(horizons) != 1:
        raise ValueError("modeled payoff grid requires exactly one matching declared horizon")
    horizon = horizons[0]
    owner_earnings = float(by_type["OwnerEarnings"]["value"])
    discount = (
        float(by_type["RiskFreeRate"]["value"])
        + float(by_type["EquityBeta"]["value"]) * float(by_type["EquityRiskPremium"]["value"])
    )
    excess_cash = float(by_type["ExcessNetCash"]["value"])
    shares = float(by_type["Shares"]["value"])
    if shares <= 0:
        raise ValueError("modeled payoff grid requires positive shares")
    states = []
    all_refs = {
        str(ref) for row in (*by_type.values(), horizon)
        for ref in row.get("source_refs") or ()
    }
    for template in proposal["scenario_templates"]:
        scenario_assumptions = {
            assumptions[str(row["assumption_id"])]["assumption_type"]: assumptions[str(row["assumption_id"])]
            for row in template["assumptions"]
        }
        if set(scenario_assumptions) != {"ForecastGrowth", "TerminalGrowth"}:
            raise ValueError("modeled payoff states require growth and terminal-growth coordinates")
        growth = float(scenario_assumptions["ForecastGrowth"]["value"])
        terminal_growth = float(scenario_assumptions["TerminalGrowth"]["value"])
        if discount <= terminal_growth:
            raise ValueError("modeled terminal payoff requires discount above terminal growth")
        earnings_at_horizon = owner_earnings * (1 + growth) ** horizon_years
        payoff = (
            earnings_at_horizon * (1 + terminal_growth) / (discount - terminal_growth)
            + excess_cash
        ) / shares
        if payoff < 0:
            raise ValueError("modeled public-equity payoff cannot be negative")
        state_refs = sorted({
            *all_refs, *template["source_refs"],
            *(str(ref) for row in scenario_assumptions.values() for ref in row.get("source_refs") or ()),
        })
        states.append({
            "state_id": template["valuation_scenario_id"],
            "valuation_scenario_id": template["valuation_scenario_id"],
            "description": (
                f"Conditional model grid: {growth:.2%} explicit owner-earnings growth and "
                f"{terminal_growth:.2%} terminal growth over {horizon_years} years"
            ),
            "equity_payoff_at_horizon": payoff,
            "payoff_source_refs": state_refs,
        })
    if len(states) != len(proposal["scenario_templates"]):
        raise ValueError("modeled payoff grid did not cover every declared valuation scenario")
    as_of = str(proposal["as_of"])
    risk_free = float(by_type["RiskFreeRate"]["value"])
    discount_factor = 1 / (1 + risk_free) ** horizon_years
    grid_seed = {
        "candidate_sha256": proposal["candidate_sha256"],
        "valuation_envelope_sha256": proposal["valuation_envelope_sha256"],
        "horizon_years": horizon_years,
        "state_ids": [row["state_id"] for row in states],
    }
    grid_ref = f"modeled-payoff-grid:{stable_sha256(grid_seed)}"
    declaration = {
        "schema": DECLARATION_SCHEMA,
        "entity_id": proposal["entity_id"],
        "candidate_sha256": proposal["candidate_sha256"],
        "valuation_envelope_sha256": proposal["valuation_envelope_sha256"],
        "horizon_at": _anniversary(as_of, horizon_years),
        "exhaustive_within_declared_scope": True,
        "exhaustiveness_scope": (
            "conditional valuation-policy Cartesian grid; not an exhaustive set of economic world states"
        ),
        "exhaustiveness_source_refs": [grid_ref, *sorted(all_refs)],
        "states": states,
        "numeraire_asset": {
            "asset_id": f"declared-risk-free-unit-{horizon_years}y",
            "price_observation": {
                "observation_id": f"derived-discount-factor:{stable_sha256(grid_seed)[:16]}",
                "value": discount_factor,
                "unit": spot_price_observation["unit"],
                "observed_at": as_of,
                "available_at": as_of,
                "source_ref": grid_ref,
            },
            "payoff_source_refs": [grid_ref, *by_type["RiskFreeRate"].get("source_refs", ())],
        },
        "probability_contract": {"kind": "admissible_simplex"},
    }
    compiled = compile_state_price_proposal(
        candidate=candidate, valuation=valuation, spot_price_observation=spot_price_observation,
        declaration=declaration,
    )
    state_result = compiled["state_price_result"]
    lowest_state = min(states, key=lambda row: (row["equity_payoff_at_horizon"], row["state_id"]))
    if state_result["no_arbitrage_certificate"]:
        discount_factor = float(state_result["discount_factor"])
        probability_bounds = {
            state: [float(bound[0]) / discount_factor, float(bound[1]) / discount_factor]
            for state, bound in state_result["state_price_bounds"].items()
        }
        lowest_floor = probability_bounds[lowest_state["state_id"]][0]
    else:
        probability_bounds = None
        lowest_floor = None
    body = {
        "schema": MODELED_GRID_SCHEMA,
        "entity_id": proposal["entity_id"],
        "horizon_years": horizon_years,
        "formula": (
            "((owner_earnings*(1+forecast_growth)^horizon)*(1+terminal_growth)"
            "/(cost_of_equity-terminal_growth)+excess_net_cash)/shares"
        ),
        "scope_boundary": "conditional_model_grid_not_physical_world_distribution",
        "declaration": declaration,
        "compiled_proposal": compiled,
        "diagnostics": {
            "identity": "risk_neutral_bounds_conditional_on_declared_model_grid",
            "state_probability_bounds": probability_bounds,
            "lowest_payoff_state_id": lowest_state["state_id"],
            "lowest_payoff": lowest_state["equity_payoff_at_horizon"],
            "lowest_payoff_state_probability_floor": lowest_floor,
            "model_grid_reconciles_with_observed_price": state_result["no_arbitrage_certificate"],
            "physical_probability_claim": False,
            "expected_return_claim": False,
        },
        "authority": "research_pricing_certificate_only",
        "capital_authority": False,
    }
    return {**body, "modeled_grid_sha256": stable_sha256(body)}


def compile_workspace_modeled_grid(
    workspace: str | Path, entity_id: str, *, horizon_years: int = 10,
) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    discovery = json.loads((root / "discovery" / "latest.json").read_text(encoding="utf-8"))
    entity = require_text(entity_id, "entity_id").upper()
    candidate = next(
        (row for row in discovery.get("candidates") or () if row.get("entity_id") == entity), None
    )
    if candidate is None:
        raise ValueError(f"discovery candidate absent: {entity}")
    relative = require_text((candidate.get("valuation") or {}).get("artifact_path"), "valuation artifact_path")
    valuation = json.loads((root / relative).read_text(encoding="utf-8"))
    spot = _valuation_spot(valuation)
    return compile_modeled_payoff_grid(
        candidate=candidate, valuation=valuation, spot_price_observation=spot,
        horizon_years=horizon_years,
    )


def audit_workspace_modeled_grids(
    workspace: str | Path, *, horizon_years: int = 10, materialize_limit: int = 0,
) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    discovery = json.loads((root / "discovery" / "latest.json").read_text(encoding="utf-8"))
    eligible = sorted([
        row for row in discovery.get("candidates") or ()
        if row.get("entity_kind") == "public_equity" and (row.get("valuation") or {}).get("artifact_path")
    ], key=lambda row: (row.get("rank") is None, row.get("rank") or 10**9, row.get("entity_id")))
    from .state_price_residuals import compile_state_price_evidence_requests
    from .valuation_grammar_residual_learning import compile_valuation_grammar_residual_learning

    rows, failures, residual_sets = [], [], []
    for candidate in eligible:
        entity = str(candidate["entity_id"])
        try:
            valuation = json.loads((root / str(candidate["valuation"]["artifact_path"])).read_text(encoding="utf-8"))
            grid = compile_modeled_payoff_grid(
                candidate=candidate, valuation=valuation, spot_price_observation=_valuation_spot(valuation),
                horizon_years=horizon_years,
            )
            result = grid["compiled_proposal"]["state_price_result"]
            residuals = compile_state_price_evidence_requests(grid)
            residual_sets.append(residuals)
            artifact_path = None
            if len([row for row in rows if row.get("artifact_path")]) < materialize_limit:
                relative = Path("state_pricing") / "conditional_payoff_contracts" / (
                    f"{entity.lower()}-{grid['modeled_grid_sha256'][:16]}.json"
                )
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary = destination.with_suffix(".tmp")
                temporary.write_text(json.dumps(grid, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                temporary.replace(destination)
                artifact_path = relative.as_posix()
            rows.append({
                "entity_id": entity, "candidate_sha256": candidate["candidate_sha256"],
                "rank": candidate.get("rank"), "screen_status": candidate.get("screen_status"),
                "modeled_grid_sha256": grid["modeled_grid_sha256"],
                "artifact_path": artifact_path,
                "contract_sha256": result["contract_sha256"],
                "result_sha256": result["result_sha256"],
                "no_arbitrage_certificate": result["no_arbitrage_certificate"],
                "market_complete": result["market_complete"],
                "lowest_payoff_state_probability_floor": (
                    grid["diagnostics"]["lowest_payoff_state_probability_floor"]
                ),
                "residual_trigger": residuals["trigger"],
                "evidence_request_count": residuals["request_count"],
                "residual_set_sha256": residuals["residual_set_sha256"],
            })
        except (KeyError, OSError, TypeError, ValueError) as error:
            failures.append({"entity_id": entity, "error": str(error)})
    rows.sort(key=lambda row: (row["rank"] if row["rank"] is not None else 10**9, row["entity_id"]))
    triggered = [row for row in residual_sets if row.get("trigger")]
    grammar_learning = compile_valuation_grammar_residual_learning(
        triggered,
        compiled_at=canonical_timestamp(discovery.get("completed_at") or discovery.get("as_of"), "discovery completed_at"),
    )
    body = {
        "schema": "jaggedthoughts-modeled-payoff-grid-audit-v1",
        "as_of": canonical_timestamp(discovery.get("as_of"), "discovery as_of"),
        "discovery_run_sha256": require_text(discovery.get("run_sha256"), "discovery run_sha256"),
        "horizon_years": horizon_years,
        "eligible_grid_count": len(rows),
        "conditional_contract_count": sum(bool(row.get("artifact_path")) for row in rows),
        "positive_state_price_count": sum(row["no_arbitrage_certificate"] for row in rows),
        "complete_market_count": sum(row["market_complete"] for row in rows),
        "infeasible_positive_state_price_count": sum(
            row.get("residual_trigger") == "infeasible_positive_state_prices" for row in rows
        ),
        "near_zero_bound_count": sum(
            row.get("residual_trigger") == "near_zero_state_probability_bounds" for row in rows
        ),
        "rows": rows, "failures": failures,
        "residual_sets": triggered,
        "grammar_learning": grammar_learning,
        "scope_boundary": "conditional_valuation_grids_not_physical_world_distributions",
        "physical_probability_claim": False, "expected_return_claim": False,
        "authority": "research_pricing_certificate_only", "capital_authority": False,
    }
    return {**body, "audit_sha256": stable_sha256(body)}


def compile_workspace_proposal(
    workspace: str | Path, entity_id: str, declaration: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    discovery = json.loads((root / "discovery" / "latest.json").read_text(encoding="utf-8"))
    entity = require_text(entity_id, "entity_id").upper()
    candidate = next(
        (row for row in discovery.get("candidates") or () if row.get("entity_id") == entity), None
    )
    if candidate is None:
        raise ValueError(f"discovery candidate absent: {entity}")
    relative = require_text((candidate.get("valuation") or {}).get("artifact_path"), "valuation artifact_path")
    valuation = json.loads((root / relative).read_text(encoding="utf-8"))
    spot = _valuation_spot(valuation)
    return compile_state_price_proposal(
        candidate=candidate, valuation=valuation, spot_price_observation=spot, declaration=declaration,
    )


def audit_workspace_proposals(workspace: str | Path) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    discovery = json.loads((root / "discovery" / "latest.json").read_text(encoding="utf-8"))
    eligible = [
        row for row in discovery.get("candidates") or ()
        if row.get("entity_kind") == "public_equity" and (row.get("valuation") or {}).get("artifact_path")
    ]
    summaries, failures = [], []
    for candidate in eligible:
        entity = str(candidate["entity_id"])
        try:
            valuation = json.loads((root / str(candidate["valuation"]["artifact_path"])).read_text(encoding="utf-8"))
            proposal = compile_state_price_proposal(
                candidate=candidate, valuation=valuation, spot_price_observation=_valuation_spot(valuation),
            )
            summaries.append({
                "entity_id": entity, "screen_status": candidate.get("screen_status"),
                "rank_score": candidate.get("rank_score"),
                "scenario_template_count": len(proposal["scenario_templates"]),
                "proposal_sha256": proposal["proposal_sha256"], "status": proposal["status"],
            })
        except (OSError, ValueError, json.JSONDecodeError) as error:
            failures.append({"entity_id": entity, "error": str(error)})
    summaries.sort(key=lambda row: (-(float(row["rank_score"]) if row["rank_score"] is not None else -1e9), row["entity_id"]))
    body = {
        "schema": "jaggedthoughts-state-price-proposal-audit-v1",
        "as_of": canonical_timestamp(discovery.get("as_of"), "discovery as_of"),
        "discovery_run_sha256": require_text(discovery.get("run_sha256"), "discovery run_sha256"),
        "valid_proposal_count": len(summaries), "solver_eligible_count": 0,
        "proposals": summaries, "failures": failures,
        "remaining_authored_inputs": [
            "exhaustive payoff-state scope", "future equity payoff per state",
            "priced numeraire and its payoff terms",
            "physical scenario weights only when an SDF is requested",
        ],
        "authority": "research_pricing_proposal_only", "capital_authority": False,
    }
    return {**body, "audit_sha256": stable_sha256(body)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace")
    parser.add_argument("--entity")
    parser.add_argument("--declaration")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    declaration = json.loads(Path(args.declaration).read_text(encoding="utf-8")) if args.declaration else None
    result = (
        compile_workspace_proposal(args.workspace, args.entity, declaration)
        if args.entity else audit_workspace_proposals(args.workspace)
    )
    if args.write:
        if not args.entity:
            parser.error("--write requires --entity")
        root = Path(args.workspace).expanduser().resolve()
        destination = root / "state_pricing" / "proposals" / f"{args.entity.lower()}-{result['proposal_sha256'][:16]}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(destination)
        result = {**result, "written_to": destination.relative_to(root).as_posix()}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "DECLARATION_SCHEMA", "MODELED_GRID_SCHEMA", "PROPOSAL_SCHEMA",
    "audit_workspace_modeled_grids", "audit_workspace_proposals",
    "compile_modeled_payoff_grid", "compile_state_price_proposal",
    "compile_workspace_modeled_grid", "compile_workspace_proposal",
]
