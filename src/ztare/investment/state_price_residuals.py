"""Typed research residuals for modeled state-price grids."""

from __future__ import annotations

from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import require_finite, require_text
from .state_price_authoring import MODELED_GRID_SCHEMA


STATE_PRICE_EVIDENCE_REQUEST_SCHEMA = "jaggedthoughts-state-price-evidence-request-v1"
STATE_PRICE_RESIDUAL_SET_SCHEMA = "jaggedthoughts-state-price-residual-set-v1"

_REQUESTS = {
    "missing_state": {
        "question": (
            "Which source-bound business state omitted from the declared grid has a distinct "
            "horizon payoff and implementation mechanism?"
        ),
        "acceptance": [
            "state identity and description", "horizon payoff in the contract unit",
            "payoff mechanism", "availability-dated source references",
        ],
    },
    "overly_narrow_payoff_support": {
        "question": (
            "Do source-bound boundary cases support horizon payoffs outside the current modeled range?"
        ),
        "acceptance": [
            "lower and upper boundary case identities", "typed payoff assumptions",
            "recomputed horizon payoffs", "availability-dated source references",
        ],
    },
    "numeraire_mismatch": {
        "question": (
            "Are the numeraire price, payoff unit, maturity, and compounding convention aligned "
            "with the equity payoff horizon?"
        ),
        "acceptance": [
            "numeraire asset identity", "point-in-time price observation",
            "horizon payoff terms", "unit and compounding convention",
        ],
    },
    "model_misspecification": {
        "question": (
            "Which source-bound payoff mechanism omitted or distorted by the current formula changes "
            "the state-contingent horizon payoff map?"
        ),
        "acceptance": [
            "rival payoff mechanism", "typed assumptions and units",
            "state-by-state payoff comparison", "decisive observation or falsifier",
        ],
    },
}


def _verified(payload: Mapping[str, Any], field: str, schema: str, label: str) -> str:
    if payload.get("schema") != schema:
        raise ValueError(f"{label} requires {schema}")
    claimed = require_text(payload.get(field), f"{label}.{field}")
    if claimed != stable_sha256({key: value for key, value in payload.items() if key != field}):
        raise ValueError(f"{label} digest does not match its payload")
    return claimed


def compile_state_price_evidence_requests(
    modeled_grid: Mapping[str, Any], *, near_zero_probability: float = 1e-6,
) -> dict[str, Any]:
    """Route deterministic grid diagnostics into rival evidence requests."""

    threshold = require_finite(near_zero_probability, "near_zero_probability")
    if not 0 < threshold < 1:
        raise ValueError("near_zero_probability must be in (0, 1)")
    grid_sha = _verified(
        modeled_grid, "modeled_grid_sha256", MODELED_GRID_SCHEMA, "modeled grid",
    )
    proposal = modeled_grid.get("compiled_proposal")
    if not isinstance(proposal, Mapping):
        raise ValueError("modeled grid compiled_proposal must be an object")
    result = proposal.get("state_price_result")
    if not isinstance(result, Mapping):
        raise ValueError("modeled grid state_price_result must be an object")
    result_sha = _verified(
        result, "result_sha256", "jaggedthoughts-state-price-result-v1", "state-price result",
    )
    entity_id = require_text(modeled_grid.get("entity_id"), "modeled grid entity_id").upper()
    if str(proposal.get("entity_id") or "").upper() != entity_id:
        raise ValueError("modeled grid and proposal entity identities differ")
    candidate_sha = require_text(proposal.get("candidate_sha256"), "proposal candidate_sha256")
    declaration = modeled_grid.get("declaration")
    if not isinstance(declaration, Mapping) or declaration.get("candidate_sha256") != candidate_sha:
        raise ValueError("modeled grid declaration is not candidate-bound")
    states = [
        str(row.get("state_id") or "")
        for row in declaration.get("states") or () if isinstance(row, Mapping)
    ]
    if not states or any(not state for state in states):
        raise ValueError("modeled grid states are missing")
    bounds = ((modeled_grid.get("diagnostics") or {}).get("state_probability_bounds"))
    trigger = None
    affected_states: list[str] = []
    trigger_values: dict[str, Any] = {}
    if result.get("status") == "infeasible_positive_state_prices":
        trigger = "infeasible_positive_state_prices"
        affected_states = sorted(states)
        trigger_values = {
            "closest_positive_asset_residuals": dict(
                (result.get("residuals") or {}).get("closest_positive_asset_residuals") or {}
            ),
        }
    elif isinstance(bounds, Mapping):
        near_zero = {
            str(state): float(bound[0])
            for state, bound in bounds.items()
            if isinstance(bound, (list, tuple)) and len(bound) == 2
            and require_finite(bound[0], f"{state} lower probability bound") <= threshold
        }
        if near_zero:
            trigger = "near_zero_state_probability_bounds"
            affected_states = sorted(near_zero)
            trigger_values = {"lower_bounds": dict(sorted(near_zero.items()))}
    support = [
        require_finite(row.get("equity_payoff_at_horizon"), "state horizon payoff")
        for row in declaration.get("states") or () if isinstance(row, Mapping)
    ]
    requests = []
    if trigger:
        trigger_identity = {
            "candidate_sha256": candidate_sha,
            "modeled_grid_sha256": grid_sha,
            "state_price_result_sha256": result_sha,
            "trigger": trigger,
            "affected_state_ids": affected_states,
            "near_zero_probability_threshold": threshold,
        }
        trigger_sha = stable_sha256(trigger_identity)
        for residual_kind, contract in _REQUESTS.items():
            body = {
                "schema": STATE_PRICE_EVIDENCE_REQUEST_SCHEMA,
                "request_id": f"state-price:{entity_id}:{residual_kind}:{trigger_sha[:16]}",
                "entity_id": entity_id,
                "candidate_sha256": candidate_sha,
                "modeled_grid_sha256": grid_sha,
                "state_price_result_sha256": result_sha,
                "trigger_sha256": trigger_sha,
                "trigger": trigger,
                "trigger_values": trigger_values,
                "affected_state_ids": affected_states,
                "residual_kind": residual_kind,
                "evidence_question": contract["question"],
                "acceptance_fields": contract["acceptance"],
                "current_payoff_support": {"minimum": min(support), "maximum": max(support)},
                "status": "open_research_residual",
                "agent_call_authorized": False,
                "physical_probability_claim": False,
                "expected_return_claim": False,
                "capital_authority": False,
            }
            requests.append({**body, "request_sha256": stable_sha256(body)})
    body = {
        "schema": STATE_PRICE_RESIDUAL_SET_SCHEMA,
        "entity_id": entity_id,
        "candidate_sha256": candidate_sha,
        "modeled_grid_sha256": grid_sha,
        "state_price_result_sha256": result_sha,
        "near_zero_probability_threshold": threshold,
        "trigger": trigger,
        "request_count": len(requests),
        "requests": requests,
        "agent_calls_made": 0,
        "physical_probability_claim": False,
        "expected_return_claim": False,
        "capital_authority": False,
    }
    return {**body, "residual_set_sha256": stable_sha256(body)}


__all__ = [
    "STATE_PRICE_EVIDENCE_REQUEST_SCHEMA",
    "STATE_PRICE_RESIDUAL_SET_SCHEMA",
    "compile_state_price_evidence_requests",
]
