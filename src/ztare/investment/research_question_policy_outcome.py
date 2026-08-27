"""Prospective economic outcomes for randomized research-question policies."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Mapping, Sequence

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_text, timestamp_key
from .prospective_return_window import compile_prospective_return_window


OUTCOME_CONTRACT_SCHEMA = "jaggedthoughts-research-question-policy-outcome-contract-v1"
ACTION_RECEIPT_SCHEMA = "jaggedthoughts-research-question-policy-action-receipt-v1"
OUTCOME_SETTLEMENT_SCHEMA = "jaggedthoughts-research-question-policy-outcome-settlement-v1"
_FORECAST_ID = "underwriting_typed_plus_full_research"


def _valid_hash(payload: Mapping[str, Any], field: str) -> bool:
    claimed = str(payload.get(field) or "")
    return bool(claimed) and claimed == stable_sha256({
        key: value for key, value in payload.items() if key != field
    })


def compile_research_question_policy_outcome_contract(
    *, assignment: Mapping[str, Any], request_basis_sha256: str,
    candidate_leaf: str, entity_id: str, benchmark_id: str | None,
    decision_cutoff_days: int = 30, probe_weight: float = 0.05,
    transaction_cost_bps: float = 15.0,
) -> dict[str, Any]:
    """Freeze the action cutoff and fixed terminal for one randomized unit."""
    assignment_sha = require_text(
        assignment.get("assignment_sha256"), "outcome assignment_sha256"
    )
    if not _valid_hash(assignment, "assignment_sha256"):
        raise ValueError("research-question assignment hash is invalid")
    if not 7 <= int(decision_cutoff_days) <= 90:
        raise ValueError("decision_cutoff_days must be in [7, 90]")
    weight = float(probe_weight)
    cost = float(transaction_cost_bps)
    if not 0 < weight <= 0.25 or not 0 <= cost <= 1_000:
        raise ValueError("probe weight or transaction cost is outside its admissible range")
    assigned_at = canonical_timestamp(
        assignment.get("assigned_at"), "outcome assigned_at"
    )
    outcome_due_at = canonical_timestamp(
        assignment.get("outcome_due_at"), "outcome due_at"
    )
    cutoff_at = (
        timestamp_key(assigned_at) + timedelta(days=int(decision_cutoff_days))
    ).isoformat(timespec="seconds").replace("+00:00", "Z")
    remaining_days = (timestamp_key(outcome_due_at) - timestamp_key(cutoff_at)).days
    benchmark = str(benchmark_id or "").upper()
    eligible = bool(assignment.get("eligible")) and bool(benchmark and benchmark != "UNBOUND")
    entity = require_text(entity_id, "outcome entity_id").upper()
    return_window = (
        compile_prospective_return_window(
            sealed_at=cutoff_at, horizon_days=remaining_days,
            entity_ids=(entity, benchmark), transaction_cost_bps=0.0,
        )
        if eligible else None
    )
    body = {
        "schema": OUTCOME_CONTRACT_SCHEMA,
        "experiment_id": assignment.get("experiment_id"),
        "assignment_unit_id": assignment.get("assignment_unit_id"),
        "assignment_sha256": assignment_sha,
        "request_basis_sha256": require_text(
            request_basis_sha256, "outcome request_basis_sha256"
        ),
        "candidate_leaf": require_text(candidate_leaf, "outcome candidate_leaf"),
        "entity_id": entity,
        "benchmark_id": benchmark or None,
        "assigned_at": assigned_at,
        "decision_cutoff_at": cutoff_at,
        "outcome_due_at": outcome_due_at,
        "eligible": eligible,
        "ineligible_reason": None if eligible else "typed_benchmark_unbound",
        "action_rule": (
            "first exact assignment-bound full-research closed-book forecast available "
            "by cutoff; fixed probe when expected active return is positive, otherwise abstain"
        ),
        "forecast_candidate_id": _FORECAST_ID,
        "probe_weight": weight,
        "round_trip_transaction_cost_bps": 2.0 * cost,
        "economic_outcome": "incremental_return_vs_no_action",
        "diagnostic_outcome": "candidate_active_return_before_cost",
        "return_window": return_window,
        "capital_authority": False,
    }
    return {**body, "outcome_contract_sha256": stable_sha256(body)}


def freeze_research_question_policy_action(
    contract: Mapping[str, Any], *, closed_book_runs: Sequence[Mapping[str, Any]],
    frozen_at: str,
) -> dict[str, Any]:
    """Freeze the first admissible pre-cutoff full-research forecast or abstain."""
    if contract.get("schema") != OUTCOME_CONTRACT_SCHEMA or not _valid_hash(
        contract, "outcome_contract_sha256"
    ):
        raise ValueError("research-question outcome contract is invalid")
    evaluated_at = canonical_timestamp(frozen_at, "outcome action frozen_at")
    if timestamp_key(evaluated_at) < timestamp_key(str(contract["decision_cutoff_at"])):
        raise ValueError("research-question action cannot freeze before its cutoff")
    matches = []
    for run in closed_book_runs:
        run_body = {
            key: value for key, value in run.items() if key != "run_sha256"
        } if isinstance(run, Mapping) else {}
        if stable_sha256(run_body) != run.get("run_sha256"):
            continue
        packet = run.get("evidence_packet") if isinstance(run, Mapping) else None
        packet = packet if isinstance(packet, Mapping) else {}
        subject = packet.get("subject") if isinstance(packet.get("subject"), Mapping) else {}
        program = (
            ((packet.get("research_snapshot") or {}).get("research_program") or {})
            if isinstance(packet.get("research_snapshot"), Mapping) else {}
        )
        if (
            run.get("schema") != "jaggedthoughts-closed-book-forecast-run-v1"
            or str(subject.get("kind") or "") != "paper_watch_decision"
            or str(subject.get("candidate_leaf") or "") != contract["candidate_leaf"]
            or str(program.get("assignment_unit_id") or "")
            != str(contract["assignment_unit_id"])
            or timestamp_key(str(run.get("opened_at") or ""))
            > timestamp_key(str(contract["decision_cutoff_at"]))
        ):
            continue
        forecast = next((
            row for row in run.get("candidate_forecasts") or ()
            if isinstance(row, Mapping)
            and row.get("candidate_id") == contract["forecast_candidate_id"]
            and _valid_hash(row, "forecast_sha256")
        ), None)
        if forecast is not None:
            matches.append((str(run["opened_at"]), str(run["run_id"]), run, forecast))
    matches.sort(key=lambda row: row[:2])
    selected = matches[0] if matches else None
    expected_active = (
        float((selected[3].get("predicted_values") or {})["active_return"])
        if selected else None
    )
    weight = float(contract["probe_weight"]) if expected_active is not None and expected_active > 0 else 0.0
    body = {
        "schema": ACTION_RECEIPT_SCHEMA,
        "outcome_contract_sha256": contract["outcome_contract_sha256"],
        "assignment_unit_id": contract["assignment_unit_id"],
        "frozen_at": evaluated_at,
        "status": "shadow_probe" if weight else "abstain",
        "target_weight": weight,
        "expected_active_return": expected_active,
        "source_run_id": selected[2].get("run_id") if selected else None,
        "source_run_sha256": selected[2].get("run_sha256") if selected else None,
        "source_forecast_sha256": selected[3].get("forecast_sha256") if selected else None,
        "capital_authority": False,
    }
    return {**body, "action_receipt_sha256": stable_sha256(body)}


def settle_research_question_policy_outcome(
    contract: Mapping[str, Any], action: Mapping[str, Any], *,
    return_window_settlement: Mapping[str, Any] | None, settled_at: str,
) -> dict[str, Any]:
    """Settle the fixed probe contribution, or zero for a frozen abstention."""
    if (
        contract.get("schema") != OUTCOME_CONTRACT_SCHEMA
        or action.get("schema") != ACTION_RECEIPT_SCHEMA
        or not _valid_hash(contract, "outcome_contract_sha256")
        or not _valid_hash(action, "action_receipt_sha256")
        or action.get("outcome_contract_sha256")
        != contract.get("outcome_contract_sha256")
    ):
        raise ValueError("research-question outcome lineage is invalid")
    evaluated_at = canonical_timestamp(settled_at, "outcome settled_at")
    if timestamp_key(evaluated_at) < timestamp_key(str(contract["outcome_due_at"])):
        raise ValueError("research-question outcome is not due")
    weight = float(action.get("target_weight") or 0.0)
    window = dict(return_window_settlement or {})
    if window and (
        window.get("schema")
        != "jaggedthoughts-prospective-return-window-settlement-v1"
        or not _valid_hash(window, "window_settlement_sha256")
        or window.get("return_window_sha256")
        != (contract.get("return_window") or {}).get("return_window_sha256")
    ):
        raise ValueError("research-question return-window settlement is invalid")
    if weight and window.get("status") != "settled":
        body = {
            "schema": OUTCOME_SETTLEMENT_SCHEMA,
            "outcome_contract_sha256": contract["outcome_contract_sha256"],
            "action_receipt_sha256": action["action_receipt_sha256"],
            "status": "due_censored",
            "settled_at": evaluated_at,
            "incremental_return_vs_no_action": None,
            "candidate_active_return_before_cost": None,
            "return_window_settlement_sha256": window.get("window_settlement_sha256"),
            "capital_authority": False,
        }
    else:
        active = None
        incremental = 0.0
        if weight:
            gross = window.get("gross_returns") or {}
            active = float(gross[contract["entity_id"]]) - float(gross[contract["benchmark_id"]])
            cost = float(contract["round_trip_transaction_cost_bps"]) / 10_000.0
            incremental = weight * (active - cost)
        body = {
            "schema": OUTCOME_SETTLEMENT_SCHEMA,
            "outcome_contract_sha256": contract["outcome_contract_sha256"],
            "action_receipt_sha256": action["action_receipt_sha256"],
            "status": "settled_action" if weight else "settled_abstention",
            "settled_at": evaluated_at,
            "incremental_return_vs_no_action": incremental,
            "candidate_active_return_before_cost": active,
            "return_window_settlement_sha256": window.get("window_settlement_sha256"),
            "capital_authority": False,
        }
    return {**body, "outcome_settlement_sha256": stable_sha256(body)}


__all__ = [
    "ACTION_RECEIPT_SCHEMA", "OUTCOME_CONTRACT_SCHEMA", "OUTCOME_SETTLEMENT_SCHEMA",
    "compile_research_question_policy_outcome_contract",
    "freeze_research_question_policy_action", "settle_research_question_policy_outcome",
]
