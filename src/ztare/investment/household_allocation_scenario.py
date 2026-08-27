"""Assumption-labeled household sleeve scenarios over the allocation kernel."""

from __future__ import annotations

from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import require_finite
from .household_allocation import (
    HOUSEHOLD_MANDATE_SCHEMA,
    compile_household_allocation_frontier,
    compile_household_mandate,
)
from .household_goal_surface import HOUSEHOLD_GOAL_SURFACE_SCHEMA
from .instrument_portfolio_admission import (
    INSTRUMENT_PORTFOLIO_ADMISSION_SCHEMA,
    WORKSPACE_INSTRUMENT_PORTFOLIO_ADMISSIONS_SCHEMA,
)
from .portfolio_policy import PORTFOLIO_POLICY_STATUS_SCHEMA
from .public_capital_market_basis import PUBLIC_BASIS_ACQUISITION_SCHEMA
from .public_capital_market_basis import public_sleeve_proxies


HOUSEHOLD_ALLOCATION_SCENARIO_INPUT_SCHEMA = (
    "jaggedthoughts-household-allocation-scenario-input-v1"
)
HOUSEHOLD_ALLOCATION_SCENARIO_SCHEMA = "jaggedthoughts-household-allocation-scenario-v1"

_INPUT_FIELDS = {
    "schema", "annual_contribution", "horizon_years", "target_wealth",
    "liquidity_reserve", "max_risky_weight", "max_one_year_loss",
    "max_effective_equity_exposure", "minimum_success_probability",
    "annual_return_haircuts", "weight_step",
}


def default_household_allocation_scenario_inputs(
    goal_surface: Mapping[str, Any], capital_market_basis: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the shared, assumption-labeled starting controls for planning."""

    matrix = [dict(row) for row in goal_surface.get("hurdle_matrix") or ()]
    horizons = sorted({int(row["horizon_years"]) for row in matrix})
    contributions = sorted({
        require_finite(row["annual_contribution_base"], "annual_contribution_base")
        for row in matrix
    })
    if not horizons or not contributions:
        raise ValueError("household goal surface requires a nonempty hurdle matrix")
    budget_default = (
        (goal_surface.get("budget_evidence") or {})
        .get("contribution_capacity_summary", {})
        .get("default_scenario_contribution")
    )
    contribution = require_finite(
        budget_default if budget_default is not None
        else contributions[(len(contributions) - 1) // 2],
        "default annual contribution",
    )
    liquidity = require_finite(
        (goal_surface.get("known_balance_sheet") or {}).get(
            "known_investable_liquidity_base"
        ),
        "known investable liquidity",
    )
    haircuts = {}
    for row in capital_market_basis.get("asset_classes") or ():
        asset_id = str(row.get("asset_id") or "")
        risk_bucket = str(row.get("risk_bucket") or "")
        if not asset_id or risk_bucket not in {"cash", "risky", "defensive"}:
            raise ValueError("capital-market basis requires typed asset risk buckets")
        haircuts[asset_id] = 0.0 if risk_bucket == "cash" else 0.01 if risk_bucket == "risky" else 0.005
    if not haircuts:
        raise ValueError("capital-market basis requires asset classes")
    return {
        "schema": HOUSEHOLD_ALLOCATION_SCENARIO_INPUT_SCHEMA,
        "annual_contribution": contribution,
        "horizon_years": horizons[(len(horizons) - 1) // 2],
        "target_wealth": require_finite(
            (goal_surface.get("goal") or {}).get("target_base"), "target wealth",
        ),
        "liquidity_reserve": int(liquidity * 0.25 / 1_000 + 0.5) * 1_000,
        "max_risky_weight": 0.8,
        "max_one_year_loss": 0.4,
        "max_effective_equity_exposure": 0.8,
        "minimum_success_probability": 0.8,
        "annual_return_haircuts": haircuts,
        "weight_step": 0.1,
    }


def _verified(raw: Mapping[str, Any], schema: str, digest_field: str) -> dict[str, Any]:
    row = dict(raw)
    digest = str(row.pop(digest_field, ""))
    if row.get("schema") != schema or len(digest) != 64 or stable_sha256(row) != digest:
        raise ValueError(f"invalid {schema} artifact")
    return {**row, digest_field: digest}


def _fraction(value: Any, label: str) -> float:
    number = require_finite(value, label)
    if not 0 <= number <= 1:
        raise ValueError(f"{label} must be in [0, 1]")
    return number


def _paper_implementation(
    *, selected_policy: Mapping[str, Any], goal: Mapping[str, Any],
    inputs: Mapping[str, Any], debt_frontier: list[dict[str, Any]],
    instrument_admissions: Mapping[str, Any], opportunity_book: Mapping[str, Any],
    portfolio_policy: Mapping[str, Any], capital_market_basis: Mapping[str, Any],
    operator_policy_blockers: list[str],
) -> dict[str, Any]:
    """Lower sleeve weights into bounded, unselected paper implementation rivals."""
    admissions = _verified(
        instrument_admissions, WORKSPACE_INSTRUMENT_PORTFOLIO_ADMISSIONS_SCHEMA,
        "workspace_admissions_sha256",
    )
    book = _verified(opportunity_book, "jaggedthoughts-opportunity-book-v1", "book_sha256")
    if portfolio_policy.get("schema") != PORTFOLIO_POLICY_STATUS_SCHEMA:
        raise ValueError(f"portfolio policy must be {PORTFOLIO_POLICY_STATUS_SCHEMA}")
    latest_run = dict(portfolio_policy.get("latest_run") or {})
    if latest_run:
        latest_run = _verified(
            latest_run, "jaggedthoughts-portfolio-policy-run-v1", "run_sha256",
        )

    proxies = {row["sleeve_id"]: row for row in public_sleeve_proxies()}
    sleeve_weights = {
        str(key): require_finite(value, f"selected_policy.weights.{key}")
        for key, value in (selected_policy.get("weights") or {}).items()
    }
    if set(sleeve_weights) != set(proxies):
        raise ValueError("selected policy must cover the exact public sleeve universe")
    return_scenarios = []
    for raw in capital_market_basis.get("return_scenarios") or ():
        scenario = dict(raw)
        expected = dict(scenario.get("expected_returns") or {})
        if set(expected) != set(proxies) or not str(scenario.get("scenario_id") or ""):
            raise ValueError("capital-market return scenario must cover the exact sleeve universe")
        return_scenarios.append({
            "scenario_id": str(scenario["scenario_id"]),
            "expected_returns": {
                sleeve_id: require_finite(value, f"{scenario['scenario_id']}.{sleeve_id}")
                for sleeve_id, value in expected.items()
            },
            "source_refs": list(map(str, scenario.get("source_refs") or ())),
            "expected_return_claim": scenario.get("expected_return_claim") is True,
        })
    if not return_scenarios:
        raise ValueError("capital-market basis requires at least one return scenario")
    starting_wealth = require_finite(
        goal.get("portfolio_starting_wealth_base"), "portfolio_starting_wealth_base",
    )
    ranks = {
        (str(row.get("entity_kind") or ""), str(row.get("entity_id") or "").upper()): row
        for row in book.get("candidates") or ()
    }
    admitted: list[dict[str, Any]] = []
    for raw in admissions.get("admissions") or ():
        admission = _verified(
            raw, INSTRUMENT_PORTFOLIO_ADMISSION_SCHEMA, "admission_sha256",
        )
        eligibility = dict(admission.get("eligibility") or {})
        if eligibility.get("research_paper_portfolio_candidate") is not True:
            continue
        subject = dict(admission.get("subject") or {})
        projection = dict(admission.get("portfolio_projection") or {})
        economics = dict(admission.get("economic_basis") or {})
        diagnostics = dict(admission.get("diagnostics") or {})
        entity_id = str(subject.get("subject_id") or "").upper()
        entity_kind = str(subject.get("entity_kind") or "")
        sleeve_id = str(subject.get("implementation_sleeve_id") or "")
        if entity_kind not in {"public_equity", "public_fund"} or sleeve_id not in proxies:
            continue
        cap = _fraction(projection.get("target_weight_cap"), f"{entity_id}.target_weight_cap")
        rank = ranks.get((entity_kind, entity_id), {})
        factor_total = require_finite(
            economics.get("expected_total_return_after_fee"),
            f"{entity_id}.factor_total_return_assumption",
        )
        cash_flow_coordinates = [
            dict(row) for row in diagnostics.get("valuation_implied_return_coordinates") or ()
            if row.get("metric_id") == "cash_flow_implied_required_return"
            and row.get("expected_realized_return_claim") is False
        ]
        cash_flow_implied = (
            require_finite(cash_flow_coordinates[0].get("value"), f"{entity_id}.cash_flow_implied_return")
            if len(cash_flow_coordinates) == 1 else None
        )
        sleeve_comparisons = [{
            "scenario_id": scenario["scenario_id"],
            "broad_sleeve_return_assumption": scenario["expected_returns"][sleeve_id],
            "factor_total_return_assumption": factor_total,
            "factor_incremental_return_vs_broad_sleeve": (
                factor_total - scenario["expected_returns"][sleeve_id]
            ),
            "cash_flow_implied_return_coordinate": cash_flow_implied,
            "cash_flow_implied_incremental_vs_broad_sleeve": (
                cash_flow_implied - scenario["expected_returns"][sleeve_id]
                if cash_flow_implied is not None else None
            ),
            "source_refs": scenario["source_refs"],
            "expected_realized_return_claim": False,
        } for scenario in return_scenarios]
        admitted.append({
            "entity_id": entity_id, "entity_kind": entity_kind, "sleeve_id": sleeve_id,
            "target_weight_cap": cap,
            "required_return_hurdle": dict(projection.get("required_return_hurdle") or {}),
            "expected_active_return_claims": list(
                projection.get("expected_active_return_claims") or ()
            ),
            "factor_total_return_assumption": factor_total,
            "factor_incremental_return_vs_broad_sleeve": min(
                row["factor_incremental_return_vs_broad_sleeve"]
                for row in sleeve_comparisons
            ),
            "cash_flow_implied_return_coordinate": cash_flow_implied,
            "cash_flow_implied_incremental_vs_broad_sleeve": (
                min(row["cash_flow_implied_incremental_vs_broad_sleeve"] for row in sleeve_comparisons)
                if cash_flow_implied is not None else None
            ),
            "broad_sleeve_comparisons": sleeve_comparisons,
            "downside_risk": require_finite(
                projection.get("downside_risk"), f"{entity_id}.downside_risk",
            ),
            "thesis_confidence": _fraction(
                projection.get("thesis_confidence"), f"{entity_id}.thesis_confidence",
            ),
            "hurdle_scenarios": list(projection.get("hurdle_scenarios") or ()),
            "research_rank": rank.get("research_rank"),
            "candidate_sha256": rank.get("candidate_sha256"),
            "admission_sha256": admission["admission_sha256"],
        })

    def proposal(
        proposal_id: str, method: str, candidate_weights: Mapping[str, float],
        *, source_refs: list[str], signal_field: str | None = None,
        signal_class: str | None = None,
    ) -> dict[str, Any]:
        candidates = {row["entity_id"]: row for row in admitted}
        by_sleeve: dict[str, float] = {sleeve_id: 0.0 for sleeve_id in proxies}
        for entity_id, weight in candidate_weights.items():
            by_sleeve[candidates[entity_id]["sleeve_id"]] += weight
        positions = []
        for sleeve_id, weight in sleeve_weights.items():
            residual = weight - by_sleeve[sleeve_id]
            if residual < -1e-10:
                raise ValueError(f"candidate weights exceed household sleeve {sleeve_id}")
            if residual > 1e-12:
                positions.append({
                    "entity_id": proxies[sleeve_id]["symbol"],
                    "entity_kind": "broad_sleeve_proxy", "sleeve_id": sleeve_id,
                    "target_weight": residual,
                    "paper_amount_base": residual * starting_wealth,
                })
        for entity_id, weight in sorted(candidate_weights.items()):
            if weight <= 1e-12:
                continue
            row = candidates[entity_id]
            positions.append({
                "entity_id": entity_id, "entity_kind": row["entity_kind"],
                "sleeve_id": row["sleeve_id"], "target_weight": weight,
                "paper_amount_base": weight * starting_wealth,
                "target_weight_cap": row["target_weight_cap"],
                "research_rank": row["research_rank"],
                "admission_sha256": row["admission_sha256"],
                "selection_signal_value": (
                    row.get(signal_field) if signal_field else None
                ),
            })
        decision_equivalence_id = stable_sha256({
            str(row["entity_id"]): row["target_weight"] for row in positions
        })
        body = {
            "proposal_id": proposal_id, "method": method,
            "policy_rule_version": "same-sleeve-signal-v1",
            "starting_investable_wealth_base": starting_wealth,
            "positions": positions,
            "decision_equivalence_id": decision_equivalence_id,
            "total_weight": sum(row["target_weight"] for row in positions),
            "source_refs": sorted(set(filter(None, source_refs))),
            "selection_signal": ({
                "signal_class": signal_class,
                "candidate_metric": signal_field,
                "comparison": "same_sleeve_broad_proxy",
                "current_action": (
                    "replace_broad_proxy_with_selected_security"
                    if any(row["entity_kind"] != "broad_sleeve_proxy" for row in positions)
                    else "abstain_to_broad_proxy"
                ),
                "expected_realized_return_claim": False,
            } if signal_field and signal_class else None),
            "expected_return_claim": False,
            "selection_status": "unselected_paper_rival",
            "order_routing_allowed": False,
        }
        return {**body, "proposal_sha256": stable_sha256(body)}

    baseline = proposal(
        "broad_sleeve_control", "household_sleeves_via_declared_broad_proxies", {},
        source_refs=[],
    )
    proposals = [baseline]
    equities = {row["entity_id"]: row for row in admitted if row["entity_kind"] == "public_equity"}
    score_sets = (
        ("equal_weight", {key: 1.0 for key in equities}, None,
         "admitted_equity_equal_weight_control"),
        ("factor_incremental_vs_broad_sleeve", {
            key: max(0.0, row["factor_incremental_return_vs_broad_sleeve"])
            for key, row in equities.items()
        }, "factor_incremental_return_vs_broad_sleeve",
         "zero_alpha_factor_total_return_spread"),
        ("factor_incremental_to_downside", {
            key: max(0.0, row["factor_incremental_return_vs_broad_sleeve"])
            / max(row["downside_risk"], 1e-6)
            for key, row in equities.items()
        }, "factor_incremental_return_vs_broad_sleeve",
         "zero_alpha_factor_total_return_spread_to_downside"),
        ("cash_flow_implied_incremental_vs_broad_sleeve", {
            key: max(0.0, row["cash_flow_implied_incremental_vs_broad_sleeve"] or 0.0)
            for key, row in equities.items()
        }, "cash_flow_implied_incremental_vs_broad_sleeve",
         "cash_flow_implied_return_spread"),
        ("cash_flow_implied_incremental_to_downside", {
            key: max(0.0, row["cash_flow_implied_incremental_vs_broad_sleeve"] or 0.0)
            / max(row["downside_risk"], 1e-6)
            for key, row in equities.items()
        }, "cash_flow_implied_incremental_vs_broad_sleeve",
         "cash_flow_implied_return_spread_to_downside"),
    )
    for rule_id, scores, signal_field, signal_class in score_sets:
        candidate_weights: dict[str, float] = {}
        for sleeve_id, sleeve_weight in sleeve_weights.items():
            members = {key: value for key, value in scores.items()
                       if equities[key]["sleeve_id"] == sleeve_id}
            total = sum(members.values())
            if total <= 0:
                continue
            for entity_id, weight in members.items():
                candidate_weights[entity_id] = min(
                    equities[entity_id]["target_weight_cap"],
                    sleeve_weight * weight / total,
                )
        compiled = proposal(
            f"admitted_equity_satellite:{rule_id}",
            f"existing_portfolio_policy_rule:{rule_id}_within_household_sleeves",
            candidate_weights,
            source_refs=[
                admissions["workspace_admissions_sha256"],
                str(capital_market_basis["basis_sha256"]),
            ],
            signal_field=signal_field, signal_class=signal_class,
        )
        proposals.append(compiled)
    projected_policy_ids = {
        "equity_discovery_priority",
        "equity_learned_law_priority",
        "equity_minimum_variance",
        "equity_walk_forward_ridge_minimum_variance",
    }
    for policy in latest_run.get("policies") or ():
        policy_id = str(policy.get("policy_id") or "")
        if policy_id not in projected_policy_ids:
            continue
        policy_weights = {
            str(key).upper(): max(0.0, require_finite(value, f"{policy_id}.{key}"))
            for key, value in (policy.get("weights") or {}).items()
        }
        candidate_weights = {}
        for sleeve_id, sleeve_weight in sleeve_weights.items():
            members = {
                entity_id: policy_weights.get(entity_id, 0.0)
                for entity_id, row in equities.items() if row["sleeve_id"] == sleeve_id
            }
            total = sum(members.values())
            if total <= 0:
                continue
            for entity_id, weight in members.items():
                candidate_weights[entity_id] = min(
                    equities[entity_id]["target_weight_cap"],
                    sleeve_weight * weight / total,
                )
        proposals.append(proposal(
            f"portfolio_policy_projection:{policy_id}",
            f"verified_portfolio_policy_weights_within_household_sleeves:{policy_id}",
            candidate_weights,
            source_refs=[
                admissions["workspace_admissions_sha256"], latest_run["run_sha256"],
                str(capital_market_basis["basis_sha256"]),
            ],
        ))
    for fund in (row for row in admitted if row["entity_kind"] == "public_fund"):
        weight = min(sleeve_weights[fund["sleeve_id"]], fund["target_weight_cap"])
        compiled = proposal(
            f"admitted_fund_challenger:{fund['entity_id']}",
            "capped_single_fund_same_sleeve_challenger", {fund["entity_id"]: weight},
            source_refs=[
                admissions["workspace_admissions_sha256"], fund["admission_sha256"],
                str(capital_market_basis["basis_sha256"]),
            ],
            signal_field="factor_incremental_return_vs_broad_sleeve",
            signal_class="same_sleeve_fund_return_assumption_diagnostic",
        )
        proposals.append(compiled)

    equivalence: dict[str, list[str]] = {}
    for row in proposals:
        equivalence.setdefault(str(row["decision_equivalence_id"]), []).append(
            str(row["proposal_id"])
        )
    decision_equivalence_classes = [{
        "decision_equivalence_id": equivalence_id,
        "representative_proposal_id": proposal_ids[0],
        "proposal_ids": proposal_ids,
    } for equivalence_id, proposal_ids in equivalence.items()]

    admitted_ids = {(row["entity_kind"], row["entity_id"]) for row in admitted}
    ranked = sorted(
        book.get("candidates") or (),
        key=lambda row: (int(row.get("research_rank") or 10**9), str(row.get("candidate_id") or "")),
    )
    abstentions = [{
        "entity_id": str(row.get("entity_id") or "").upper(),
        "entity_kind": str(row.get("entity_kind") or ""),
        "research_rank": row.get("research_rank"),
        "reason": "research_rank_does_not_grant_instrument_admission",
    } for row in ranked if (
        str(row.get("entity_kind") or ""), str(row.get("entity_id") or "").upper()
    ) not in admitted_ids][:10]
    cash_return = next(iter(selected_policy.get("scenario_outcomes") or ()), {}).get(
        "cash_return_assumption"
    )
    debt_rivals = [{
        **row,
        "maximum_scenario_paydown_base": min(
            starting_wealth, require_finite(row.get("balance_base"), "debt balance"),
        ) if row.get("posture") != "preserve_zero_cost_option" else 0.0,
        "cash_return_assumption": cash_return,
        "remaining_investable_base": starting_wealth - (
            min(starting_wealth, require_finite(row.get("balance_base"), "debt balance"))
            if row.get("posture") != "preserve_zero_cost_option" else 0.0
        ),
        "selection_status": "comparison_only_tax_and_terms_unresolved",
    } for row in debt_frontier]
    body = {
        "schema": "jaggedthoughts-household-paper-implementation-rivals-v1",
        "status": "paper_rivals_ready_operator_selection_blocked",
        "selected_household_program_id": selected_policy.get("program_id"),
        "liquidity_reserve_base": require_finite(
            inputs.get("liquidity_reserve"), "liquidity_reserve",
        ),
        "admitted_instrument_count": len(admitted),
        "ranked_candidate_count": len(ranked),
        "admitted_instruments": admitted,
        "proposals": proposals,
        "display_proposal_ids": [
            row["representative_proposal_id"] for row in decision_equivalence_classes
        ],
        "decision_equivalence_classes": decision_equivalence_classes,
        "enumerated_rule_count": len(proposals),
        "decision_distinct_count": len(decision_equivalence_classes),
        "prospective_tournament_ready": len(decision_equivalence_classes) >= 2,
        "debt_rivals": debt_rivals,
        "ranked_abstentions": abstentions,
        "goal_test": {
            "required_constant_return": goal.get("required_constant_return"),
            "selected_robust_goal_probability": goal.get("selected_robust_goal_probability"),
            "minimum_success_probability": goal.get("minimum_success_probability"),
            "target_meets_declared_probability": goal.get(
                "target_meets_declared_probability"
            ),
        },
        "operator_policy_blockers": operator_policy_blockers,
        "operator_action": "abstain_until_private_policy_selection",
        "uncertainty": {
            "household_policy": "user_tunable_scenario_not_operator_mandate",
            "portfolio_policy_status": latest_run.get("status") or "not_open",
            "portfolio_policy_settled_episode_count": int(
                portfolio_policy.get("settled_count") or 0
            ),
            "research_rank_is_expected_return": False,
            "admission_return_basis": "declared_zero_alpha_factor_scenario",
            "cash_flow_implied_return_is_forecast": False,
            "candidate_signal_comparator": "same_sleeve_broad_proxy",
            "tax_lot_and_account_location_modeled": False,
        },
        "authority": "private_assumption_labeled_paper_rivals_only",
        "policy_authority": False, "capital_authority": False,
        "brokerage_authority": False, "order_routing_allowed": False,
    }
    return {**body, "implementation_sha256": stable_sha256(body)}


def compile_household_allocation_scenario(
    inputs: Mapping[str, Any], *, goal_surface: Mapping[str, Any],
    public_basis_acquisition: Mapping[str, Any], simulation_paths: int = 256,
    simulation_seed_identity: str | None = None,
    instrument_admissions: Mapping[str, Any] | None = None,
    opportunity_book: Mapping[str, Any] | None = None,
    portfolio_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Enumerate a sleeve frontier without claiming the operator's policy is known."""
    if set(inputs) != _INPUT_FIELDS:
        raise ValueError("household allocation scenario requires its exact input fields")
    if inputs.get("schema") != HOUSEHOLD_ALLOCATION_SCENARIO_INPUT_SCHEMA:
        raise ValueError(
            f"scenario schema must be {HOUSEHOLD_ALLOCATION_SCENARIO_INPUT_SCHEMA}"
        )
    surface = _verified(goal_surface, HOUSEHOLD_GOAL_SURFACE_SCHEMA, "surface_sha256")
    acquired = dict(public_basis_acquisition)
    if acquired.get("schema") != PUBLIC_BASIS_ACQUISITION_SCHEMA:
        raise ValueError(f"public basis must be {PUBLIC_BASIS_ACQUISITION_SCHEMA}")
    basis = _verified(
        dict(acquired.get("capital_market_basis") or {}),
        "jaggedthoughts-capital-market-basis-v1", "basis_sha256",
    )
    asset_ids = [str(row["asset_id"]) for row in basis["asset_classes"]]
    haircuts = dict(inputs.get("annual_return_haircuts") or {})
    if set(haircuts) != set(asset_ids):
        raise ValueError("annual return haircuts must cover the exact public sleeve universe")
    annual_haircuts = {
        asset_id: _fraction(haircuts[asset_id], f"annual_return_haircuts.{asset_id}")
        for asset_id in asset_ids
    }
    horizon_raw = require_finite(inputs.get("horizon_years"), "horizon_years")
    horizon = int(horizon_raw)
    if horizon_raw != horizon or not 1 <= horizon <= 100:
        raise ValueError("horizon_years must be an integer in [1, 100]")
    target = require_finite(inputs.get("target_wealth"), "target_wealth")
    contribution = require_finite(inputs.get("annual_contribution"), "annual_contribution")
    reserve = require_finite(inputs.get("liquidity_reserve"), "liquidity_reserve")
    if target <= 0 or contribution < 0 or reserve < 0:
        raise ValueError("target must be positive; contribution and reserve cannot be negative")
    max_risky = _fraction(inputs.get("max_risky_weight"), "max_risky_weight")
    max_loss = _fraction(inputs.get("max_one_year_loss"), "max_one_year_loss")
    max_effective = _fraction(
        inputs.get("max_effective_equity_exposure"), "max_effective_equity_exposure",
    )
    min_success = _fraction(
        inputs.get("minimum_success_probability"), "minimum_success_probability",
    )
    weight_step = require_finite(inputs.get("weight_step"), "weight_step")

    balance = dict(surface.get("known_balance_sheet") or {})
    scenario_ref = f"household-intake:{surface['intake_sha256']}"
    assets = []
    for source in balance.get("assets") or ():
        row = dict(source)
        kind = str(row.get("kind") or "unknown")
        assets.append({
            "asset_id": str(row.get("asset_id") or ""), "kind": kind,
            "value": require_finite(row.get("value_base"), "asset.value_base"),
            "currency": str(surface["base_currency"]),
            "liquid": kind == "liquidity", "investable": kind == "liquidity",
            "source_ref": scenario_ref,
        })
    property_ids = [row["asset_id"] for row in assets if row["kind"] == "property"]
    liabilities, excluded_liabilities = [], []
    for source in balance.get("liabilities") or ():
        row = dict(source)
        if row.get("annual_rate") is None:
            excluded_liabilities.append(str(row.get("liability_id") or ""))
            continue
        liabilities.append({
            "liability_id": str(row.get("liability_id") or ""),
            "kind": str(row.get("kind") or "unknown"),
            "balance": require_finite(row.get("balance_base"), "liability.balance_base"),
            "currency": str(surface["base_currency"]),
            "annual_rate": require_finite(row.get("annual_rate"), "liability.annual_rate"),
            "rate_kind": "unresolved",
            "secured_by_asset_id": (
                property_ids[0] if str(row.get("kind") or "") == "mortgage" and property_ids
                else None
            ),
            "source_ref": scenario_ref,
        })
    source_refs = sorted(set(
        [scenario_ref, *map(str, surface.get("fx_source_refs") or ())]
    ))
    mandate = compile_household_mandate({
        "schema": HOUSEHOLD_MANDATE_SCHEMA,
        "mandate_id": f"planning-scenario:{stable_sha256(dict(inputs))[:16]}",
        "mandate_purpose": "planning_scenario",
        "as_of": basis["as_of"], "base_currency": surface["base_currency"],
        "fx_to_base": {}, "person": {}, "tax_residence": None,
        "assets": assets, "liabilities": liabilities, "accounts": [],
        "tax_policy": {"annual_return_haircuts": annual_haircuts},
        "currency_policy": {
            "minimum_asset_weights": {},
            "exposure_treatment": "base_currency_conversion_only",
        },
        "goal": {
            "target_wealth": target, "currency": surface["base_currency"],
            "horizon_years": horizon, "annual_contribution": contribution,
            "wealth_basis": "investable_wealth",
            "minimum_success_probability": min_success,
        },
        "constraints": {
            "liquidity_reserve": reserve, "max_risky_weight": max_risky,
            "max_one_year_loss": max_loss,
            "max_effective_equity_exposure": max_effective,
            "weight_step": weight_step,
        },
        "human_capital": {"included": False}, "source_refs": source_refs,
    })
    allocation = compile_household_allocation_frontier(
        mandate=mandate, capital_market_basis=basis, simulation_paths=simulation_paths,
        simulation_seed_identity=simulation_seed_identity,
    )
    body = {
        "schema": HOUSEHOLD_ALLOCATION_SCENARIO_SCHEMA,
        "base_currency": surface["base_currency"],
        "as_of": basis["as_of"], "goal_surface_sha256": surface["surface_sha256"],
        "basis_sha256": basis["basis_sha256"], "mandate_sha256": mandate["mandate_sha256"],
        "inputs": dict(inputs), "status": allocation["status"],
        "budget_evidence": surface.get("budget_evidence"),
        "selected_policy": allocation.get("selected_policy"),
        "selected_wealth_paths": allocation.get("selected_wealth_paths") or [],
        "policy_rivals": allocation.get("policy_rivals") or [],
        "return_model_decision_closure": (
            allocation.get("return_model_decision_closure") or {}
        ),
        "debt_paydown_frontier": allocation.get("debt_paydown_frontier") or [],
        "enumeration": allocation.get("enumeration") or {},
        "goal": allocation.get("goal") or {},
        "simulation": allocation.get("simulation") or {},
        "assumption_register": [
            {"field": "starting_investable_wealth", "basis": "known_intake_liquidity"},
            {"field": "annual_contribution", "basis": "user_tunable_scenario"},
            {"field": "goal_horizon_and_target", "basis": "user_tunable_scenario"},
            {"field": "risk_limits_and_tax_haircuts", "basis": "user_tunable_scenario"},
            {"field": "returns", "basis": "current_public_source_scenario"},
            {"field": "covariance", "basis": "point_in_time_public_adjusted_prices"},
            {"field": "human_capital", "basis": "excluded"},
            {"field": "currency_exposure", "basis": "converted_to_base_not_hedged"},
        ],
        "operator_policy_blockers": list(surface.get("readiness", {}).get("missing") or ()),
        "excluded_liabilities_without_rate": excluded_liabilities,
        "boundary": (
            "This interactive result answers what the current public sleeve assumptions imply "
            "under the displayed controls. It is not the operator mandate, an account/tax-lot "
            "plan, a fund recommendation, or an order instruction."
        ),
        "authority": "private_assumption_labeled_scenario_only",
        "policy_authority": False, "capital_authority": False,
        "brokerage_authority": False,
    }
    if instrument_admissions and opportunity_book and portfolio_policy:
        body["paper_implementation"] = _paper_implementation(
            selected_policy=allocation["selected_policy"], goal=allocation["goal"],
            inputs=inputs, debt_frontier=allocation.get("debt_paydown_frontier") or [],
            instrument_admissions=instrument_admissions,
            opportunity_book=opportunity_book, portfolio_policy=portfolio_policy,
            capital_market_basis=basis,
            operator_policy_blockers=list(surface.get("readiness", {}).get("missing") or ()),
        )
    return {**body, "scenario_sha256": stable_sha256(body)}


__all__ = [
    "HOUSEHOLD_ALLOCATION_SCENARIO_INPUT_SCHEMA",
    "HOUSEHOLD_ALLOCATION_SCENARIO_SCHEMA",
    "default_household_allocation_scenario_inputs",
    "compile_household_allocation_scenario",
]
