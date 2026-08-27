"""Join public sleeve research to the private household paper-policy boundary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import yaml

from ztare.common.equivariance import stable_sha256

from .fund_sleeve_comparison import FUND_SLEEVE_COMPARISON_SCHEMA
from .household_allocation import HOUSEHOLD_ALLOCATION_SCHEMA
from .household_allocation_scenario import HOUSEHOLD_ALLOCATION_SCENARIO_SCHEMA
from .portfolio import PORTFOLIO_ASSEMBLY_SCHEMA
from .portfolio_policy import PORTFOLIO_POLICY_STATUS_SCHEMA, portfolio_policy_status
from .public_capital_market_basis import (
    PUBLIC_BASIS_ACQUISITION_SCHEMA,
    PUBLIC_SLEEVE_IDS,
    public_sleeve_proxies,
)
from .sleeve_implementation import SLEEVE_IMPLEMENTATION_FRONTIER_SCHEMA


PAPER_POLICY_PATH_SCHEMA = "jaggedthoughts-household-paper-policy-path-v1"

_PRIVATE_MANDATE_INPUTS = (
    "person.age",
    "tax_residence",
    "accounts[]",
    "assets[]",
    "liabilities[]",
    "human_capital.after_tax_income_contract",
    "goal.target_wealth",
    "goal.horizon_years",
    "goal.annual_contribution",
    "goal.wealth_basis",
    "constraints.liquidity_reserve",
    "constraints.max_risky_weight",
    "constraints.max_one_year_loss",
    "tax_policy.annual_return_haircuts",
    "currency_policy.minimum_asset_weights",
)

_PRIVATE_BLOCKER_FIELDS = {
    "age": "person.age",
    "tax_residence": "tax_residence",
    "brokerage_and_retirement_account_inventory": "accounts[]",
    "after_tax_return_policy": "tax_policy.annual_return_haircuts",
    "liability_currency_policy": "currency_policy.minimum_asset_weights",
    "mortgaged_property_value": "assets[].mortgaged_property",
    "nonportfolio_terminal_value_for_net_worth_goal": "goal.nonportfolio_terminal_value",
    "after_tax_human_capital_contract": "human_capital.after_tax_income_contract",
}


def _verified(raw: Mapping[str, Any], schema: str, digest_field: str) -> dict[str, Any]:
    row = dict(raw)
    digest = str(row.pop(digest_field, ""))
    if row.get("schema") != schema or len(digest) != 64 or stable_sha256(row) != digest:
        raise ValueError(f"invalid {schema} artifact")
    return {**row, digest_field: digest}


def compile_household_paper_policy_path(
    *,
    public_basis_acquisition: Mapping[str, Any],
    sleeve_implementation: Mapping[str, Any],
    fund_sleeve_comparison: Mapping[str, Any],
    portfolio_policy: Mapping[str, Any],
    planning_scenario: Mapping[str, Any] | None = None,
    household_allocation: Mapping[str, Any] | None = None,
    portfolio_assembly: Mapping[str, Any] | None = None,
    patient_capital_policy: Mapping[str, Any] | None = None,
    state_pricing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile one read-only route from broad sleeves to prospective selection."""
    acquired = dict(public_basis_acquisition)
    if acquired.get("schema") != PUBLIC_BASIS_ACQUISITION_SCHEMA:
        raise ValueError(f"public basis must be {PUBLIC_BASIS_ACQUISITION_SCHEMA}")
    basis = dict(acquired.get("capital_market_basis") or {})
    basis = _verified(basis, "jaggedthoughts-capital-market-basis-v1", "basis_sha256")
    sleeve = _verified(
        sleeve_implementation,
        SLEEVE_IMPLEMENTATION_FRONTIER_SCHEMA,
        "sleeve_implementation_sha256",
    )
    comparison = _verified(
        fund_sleeve_comparison,
        FUND_SLEEVE_COMPARISON_SCHEMA,
        "fund_sleeve_comparison_sha256",
    )
    if sleeve.get("basis_sha256") != basis["basis_sha256"]:
        raise ValueError("sleeve implementation crossed the public basis identity")
    if comparison.get("sleeve_implementation_sha256") != sleeve["sleeve_implementation_sha256"]:
        raise ValueError("fund comparison crossed the sleeve implementation identity")
    if portfolio_policy.get("schema") != PORTFOLIO_POLICY_STATUS_SCHEMA:
        raise ValueError(f"portfolio policy must be {PORTFOLIO_POLICY_STATUS_SCHEMA}")

    allocation = None
    if household_allocation is not None:
        allocation = _verified(
            household_allocation, HOUSEHOLD_ALLOCATION_SCHEMA, "allocation_sha256",
        )
        if allocation.get("basis_sha256") != basis["basis_sha256"]:
            raise ValueError("household allocation crossed the public basis identity")
    planning = None
    if planning_scenario is not None:
        planning = _verified(
            planning_scenario,
            HOUSEHOLD_ALLOCATION_SCENARIO_SCHEMA,
            "scenario_sha256",
        )
        if planning.get("basis_sha256") != basis["basis_sha256"]:
            raise ValueError("household planning scenario crossed the public basis identity")
    assembly = None
    if portfolio_assembly is not None:
        assembly = _verified(
            portfolio_assembly, PORTFOLIO_ASSEMBLY_SCHEMA, "portfolio_assembly_sha256",
        )

    declared_proxies = {row["sleeve_id"]: row for row in public_sleeve_proxies()}
    basis_ids = {str(row["asset_id"]) for row in basis.get("asset_classes") or ()}
    sleeve_rows = {str(row["sleeve_id"]): row for row in sleeve.get("sleeves") or ()}
    compared = {str(row["sleeve_id"]): row for row in comparison.get("sleeves") or ()}
    if basis_ids != set(PUBLIC_SLEEVE_IDS) or set(sleeve_rows) != set(PUBLIC_SLEEVE_IDS):
        raise ValueError("paper-policy path requires the exact public sleeve universe")

    selected_weights = dict((allocation or {}).get("selected_policy", {}).get("weights") or {})
    sleeves = []
    for sleeve_id in PUBLIC_SLEEVE_IDS:
        implementation = sleeve_rows[sleeve_id]
        proxy = declared_proxies[sleeve_id]
        if str((implementation.get("basis_proxy") or {}).get("subject_id")) != proxy["symbol"]:
            raise ValueError(f"broad proxy identity differs for {sleeve_id}")
        programs = list((compared.get(sleeve_id) or {}).get("programs") or ())
        challengers = [{
            "entity_id": str((row.get("identity") or {}).get("subject_id") or ""),
            "program_id": row.get("program_id"),
            "comparison_eligible": bool(row.get("comparison_eligible")),
            "risk_cost_frontier_status": row.get("risk_cost_frontier_status"),
            "implementation_review_admitted": bool(row.get("implementation_review_admitted")),
            "portfolio_policy_evidence_complete": bool(
                (row.get("portfolio_evidence") or {}).get("portfolio_policy_evidence_complete")
            ),
            "public_evidence_gaps": sorted(set(map(str, row.get("blockers") or ())) | set(
                map(str, (row.get("portfolio_evidence") or {}).get("lookthrough_gaps") or ())
            ) | set(map(
                str, (row.get("portfolio_evidence") or {}).get("tax_currency_gaps") or (),
            ))),
        } for row in programs]
        sleeves.append({
            "sleeve_id": sleeve_id,
            "baseline_proxy": proxy["symbol"],
            "baseline_role": "retained_until_same_sleeve_replacement_earns_admission",
            "selected_weight": selected_weights.get(sleeve_id),
            "challengers": challengers,
            "comparison_scope": "same_sleeve_only",
        })

    private_blockers = (
        list(map(str, allocation.get("blockers") or ()))
        if allocation is not None else ["household_capital_mandate_absent"]
    )
    public_gaps = sorted({
        gap for row in sleeves for challenger in row["challengers"]
        for gap in challenger["public_evidence_gaps"]
    })
    patient = dict(patient_capital_policy or {})
    patient_declared = all(patient.get(field) is not None for field in (
        "minimum_after_cost_return_edge", "impairment_return_floor",
        "impairment_confidence_floor",
    ))
    allocation_ready = bool(
        allocation
        and allocation.get("status") == "paper_policy_ready"
        and allocation.get("selected_policy")
    )
    replacement_ready = any(
        challenger["implementation_review_admitted"]
        and challenger["portfolio_policy_evidence_complete"]
        for row in sleeves for challenger in row["challengers"]
    )
    required_private_fields = (
        list(_PRIVATE_MANDATE_INPUTS) if allocation is None else sorted({
            _PRIVATE_BLOCKER_FIELDS.get(code, code) for code in private_blockers
        })
    )
    stages = [
        {"stage": "public_broad_sleeve_basis", "status": "ready"},
        {"stage": "household_planning_scenario", "status": (
            "ready" if planning and planning.get("selected_policy") else "not_compiled"
        )},
        {"stage": "household_asset_allocation", "status": (
            "ready" if allocation_ready else "blocked_private_inputs"
        )},
        {"stage": "within_sleeve_fund_comparison", "status": comparison.get("status")},
        {"stage": "same_sleeve_proxy_replacement", "status": (
            "paper_review_ready" if allocation_ready and replacement_ready else
            "public_evidence_incomplete" if any(row["challengers"] for row in sleeves)
            else "no_challenger"
        )},
        {"stage": "patient_capital_replacement", "status": (
            "evaluated" if assembly and assembly.get("patient_capital") else
            "blocked_current_portfolio" if patient_declared else "blocked_policy_declaration"
        )},
        {"stage": "prospective_complete_policy_tournament", "status": (
            "learning" if int(portfolio_policy.get("pending_count") or 0) else
            "settled" if int(portfolio_policy.get("settled_count") or 0) else "not_open"
        )},
    ]
    comparison_ready = bool(
        (portfolio_policy.get("scoreboard") or {}).get("comparison_ready")
    )
    allocation_rivals = list((allocation or {}).get("policy_rivals") or ())
    if not allocation_rivals:
        allocation_rivals = [{
            "rival_id": rival_id,
            "status": "blocked_household_mandate",
            "program": None,
        } for rival_id in (
            "goal_selected", "minimum_variance", "maximum_robust_sharpe",
            "risk_budget",
        )]
    activation_points = [
        {
            "activation_id": "household_mandate",
            "status": "ready" if allocation_ready else "blocked_private_inputs",
            "owner": "operator_private_policy",
            "unlocks": "cross_sleeve_weights_and_complete_policy_rivals",
            "blockers": required_private_fields if not allocation_ready else [],
            "next_action": (
                "review compiled allocation rivals" if allocation_ready else
                "bind remaining household mandate fields"
            ),
        },
        {
            "activation_id": "fund_implementation_evidence",
            "status": "ready" if replacement_ready else "public_evidence_incomplete",
            "owner": "autonomous_public_research",
            "unlocks": "same_sleeve_replacement_review",
            "blockers": [] if replacement_ready else public_gaps,
            "next_action": (
                "review admitted same-sleeve replacements" if replacement_ready else
                "close public fund evidence gaps"
            ),
        },
        {
            "activation_id": "current_portfolio_binding",
            "status": "ready" if assembly else "blocked_current_portfolio",
            "owner": "operator_private_policy",
            "unlocks": "tax_cost_and_patient_capital_comparison",
            "blockers": [] if assembly else [
                "positions[].entity_id", "positions[].market_value",
                "accounts[].tax_lots", "estimated_trade_costs",
            ],
            "next_action": (
                "review replacement costs and incumbent posture" if assembly else
                "bind current positions tax lots and estimated trade costs"
            ),
        },
        {
            "activation_id": "prospective_policy_settlement",
            "status": "ready" if comparison_ready else (
                "learning" if int(portfolio_policy.get("pending_count") or 0)
                else "not_open"
            ),
            "owner": "prospective_policy_tournament",
            "unlocks": "policy_comparison_with_out_of_sample_receipts",
            "blockers": [] if comparison_ready else [
                str((portfolio_policy.get("scoreboard") or {}).get("next_activation")
                    or "open_and_settle_complete_policy_forecasts")
            ],
            "next_action": (
                "compare settled complete policies" if comparison_ready else
                str((portfolio_policy.get("scoreboard") or {}).get("next_activation")
                    or "open complete-policy forecasts")
            ),
        },
    ]
    activation_points.append({
        "activation_id": "paper_policy_review",
        "status": "ready" if allocation_ready else "blocked_upstream",
        "owner": "operator",
        "unlocks": "paper_policy_decision_only",
        "blockers": [] if allocation_ready else ["household_mandate"],
        "next_action": (
            "review and freeze a paper policy; no order routing"
            if allocation_ready else "complete the household mandate"
        ),
    })
    next_activation = next(
        (row for row in activation_points if row["status"] != "ready"),
        activation_points[-1],
    )
    body = {
        "schema": PAPER_POLICY_PATH_SCHEMA,
        "as_of": basis["as_of"],
        "basis_sha256": basis["basis_sha256"],
        "sleeve_implementation_sha256": sleeve["sleeve_implementation_sha256"],
        "fund_sleeve_comparison_sha256": comparison["fund_sleeve_comparison_sha256"],
        "allocation_sha256": (allocation or {}).get("allocation_sha256"),
        "planning_scenario_sha256": (planning or {}).get("scenario_sha256"),
        "portfolio_assembly_sha256": (assembly or {}).get("portfolio_assembly_sha256"),
        "stages": stages,
        "activation_points": activation_points,
        "next_activation": next_activation,
        "allocation_policy_rivals": allocation_rivals,
        "planning_projection": {
            "status": (
                "assumption_labeled_ready"
                if planning and planning.get("selected_policy") else "not_compiled"
            ),
            "selected_sleeve_weights": dict(
                ((planning or {}).get("selected_policy") or {}).get("weights") or {}
            ),
            "policy_authority": False,
            "capital_authority": False,
        },
        "scope_separation": {
            "cross_sleeve_weight_owner": "household_allocation_frontier",
            "within_sleeve_instrument_owner": "fund_sleeve_comparison",
            "current_research_cohort_selects_cross_sleeve_weights": False,
            "broad_sleeve_universe": list(PUBLIC_SLEEVE_IDS),
        },
        "sleeves": sleeves,
        "public_evidence": {
            "basis_ready": bool((acquired.get("data_availability") or {}).get("all_required_inputs_available")),
            "fund_comparison_gap_codes": public_gaps,
            "state_price_status": (state_pricing or {}).get("status"),
            "state_price_use": "scenario_price_consistency_not_return_forecast_or_weight",
            "factor_use": "fund_comparison_control_not_expected_alpha",
        },
        "private_inputs": {
            "blockers": sorted(set(private_blockers)),
            "required_mandate_fields": required_private_fields,
            "current_portfolio_fields": (
                ["positions[].entity_id", "positions[].market_value", "accounts[].tax_lots", "estimated_trade_costs"]
                if assembly is None else []
            ),
        },
        "patient_capital": {
            "declared": patient_declared,
            "policy": patient if patient_declared else None,
            "use": "hold_incumbent_unless_impaired_or_superior_after_cost_replacement_exists",
        },
        "portfolio_policy_learning": {
            "scope": "research_security_allocation_not_household_mandate",
            "run_count": int(portfolio_policy.get("run_count") or 0),
            "settled_count": int(portfolio_policy.get("settled_count") or 0),
            "pending_count": int(portfolio_policy.get("pending_count") or 0),
            "comparison_ready": comparison_ready,
            "next_activation": (portfolio_policy.get("scoreboard") or {}).get("next_activation"),
        },
        "status": (
            "paper_policy_ready" if allocation_ready and assembly else
            "public_research_active_private_policy_blocked"
        ),
        "authority": "read_only_paper_policy_projection",
        "allocation_selected": allocation_ready,
        "capital_authority": False,
        "brokerage_authority": False,
    }
    return {**body, "paper_policy_path_sha256": stable_sha256(body)}


def compile_workspace_household_paper_policy_path(
    workspace: str | Path,
    *,
    sleeve_implementation: Mapping[str, Any],
    fund_sleeve_comparison: Mapping[str, Any],
    portfolio_policy: Mapping[str, Any] | None = None,
    planning_scenario: Mapping[str, Any] | None = None,
    portfolio_assembly: Mapping[str, Any] | None = None,
    state_pricing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()

    def read(path: Path) -> dict[str, Any] | None:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    config = yaml.safe_load((root / "workspace.yaml").read_text(encoding="utf-8")) or {}
    return compile_household_paper_policy_path(
        public_basis_acquisition=read(root / "household/capital_market_basis/latest.json") or {},
        planning_scenario=planning_scenario,
        household_allocation=read(root / "household/allocation/latest.json"),
        sleeve_implementation=sleeve_implementation,
        fund_sleeve_comparison=fund_sleeve_comparison,
        portfolio_policy=portfolio_policy or portfolio_policy_status(root),
        portfolio_assembly=portfolio_assembly,
        patient_capital_policy=(config.get("portfolio") or {}).get("patient_capital"),
        state_pricing=state_pricing,
    )


__all__ = [
    "PAPER_POLICY_PATH_SCHEMA",
    "compile_household_paper_policy_path",
    "compile_workspace_household_paper_policy_path",
]
