#!/usr/bin/env python3
"""GP-243 action-intelligence read model.

This script binds existing ZTARE evidence surfaces into advisory action-impact
rows. It does not allocate work, execute ticks, or mutate GP-230 market
artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
FORECAST_POOL = REPO / "analytics/public/forecast_pool"
MARKET_STATE = FORECAST_POOL / "market_state"
MARKET_STATE_CONTRACTS = MARKET_STATE / "contracts"
DECISION_USE_LEDGER = FORECAST_POOL / "decision_use" / "decision_use_ledger.jsonl"
AGGREGATES = FORECAST_POOL / "aggregates"
SCORES = FORECAST_POOL / "scores"
OUTCOMES = FORECAST_POOL / "outcomes"

ACTION_LEDGER_DIR = REPO / "analytics/public/ledgers/action_intelligence"
ACTION_IMPACT_LEDGER = ACTION_LEDGER_DIR / "action_impact_ledger.jsonl"
SURFACING_EVENT_LEDGER = ACTION_LEDGER_DIR / "surfacing_event_ledger.jsonl"
STATE_DIR = REPO / "analytics/public/action_intelligence/state"
ACTION_STATE = STATE_DIR / "action_intelligence.json"
SHADOW_RECOMMENDATIONS = STATE_DIR / "shadow_recommendations.json"
SOURCE_HEALTH = STATE_DIR / "source_health.json"

GP233_LEDGER = (
    REPO
    / "analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md"
)
CATCH_LEDGER = REPO / "analytics/public/ledgers/catch/catch_ledger.jsonl"
TRAJECTORY_ARCHIVE = (
    REPO / "analytics/public/ledgers/trajectory/trajectory_archive.jsonl"
)
TRAJECTORY_ARCHIVE_ENRICHED = (
    REPO / "analytics/public/ledgers/trajectory/trajectory_archive_enriched.jsonl"
)
PRIMITIVE_SURFACE = REPO / "analytics/public/queries/rd/rd_tick_primitive_surface.json"
PRIMITIVE_MISS_QUEUE = REPO / "analytics/public/queries/primitive_amnesia_miss_queue.jsonl"
RECURSIVE_GAIN = REPO / "analytics/public/queries/trajectory/recursive_gain_candidates.json"
CLOSURE_PATTERNS = REPO / "analytics/public/queries/reflexive/closure_patterns.json"
BIFURCATION_REPORT = REPO / "analytics/public/ledgers/reflexive/bifurcation_report.json"

FORECAST_ACTIONS = [
    "run_now",
    "split_contract",
    "ask_another_independent_agent",
    "defer",
    "kill_branch",
    "ignore_forecast",
    "override_forecast",
    "repair_source_emitter",
]
SURFACING_ACTIONS = [
    "surface_pattern",
    "surface_anti_pattern",
    "surface_trajectory_cluster",
    "surface_gp233_next_lever",
    "surface_catch_preconditioner",
    "surface_primitive_promotion_review",
    "suppress_surface_as_low_voi",
    "repair_source_emitter",
]
AGENTIC_WORKBENCH_ACTIONS = [
    "invoke_autoresearch",
    "prepare_autoresearch_surface",
    "run_out_of_loop_agent",
    "stay_out_of_loop",
    "record_negative_constraint",
    "repair_source_emitter",
]
SURFACE_KIND_TO_ACTION = {
    "pattern": "surface_pattern",
    "anti_pattern": "surface_anti_pattern",
    "trajectory_cluster": "surface_trajectory_cluster",
    "gp233_next_lever": "surface_gp233_next_lever",
    "catch_preconditioner": "surface_catch_preconditioner",
    "primitive_promotion_review": "surface_primitive_promotion_review",
}
GP230_USED_FOR_TO_GP243 = {
    "run": "run_now",
    "split": "split_contract",
    "ask_more": "ask_another_independent_agent",
    "defer": "defer",
    "kill": "kill_branch",
    "ignore": "ignore_forecast",
    "override": "override_forecast",
}
LEGACY_CONSEQUENTIAL_CATCH_KEY = "load" + "_bearing"
ROUTER_DECISION_TO_AGENTIC_ACTION = {
    "invoke_autoresearch": "invoke_autoresearch",
    "prepare_autoresearch_surface": "prepare_autoresearch_surface",
    "stay_out_of_loop": "stay_out_of_loop",
    "not_evaluated": "run_out_of_loop_agent",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"malformed JSON in {path}: {exc}") from exc


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"malformed JSONL in {path}:{lineno}: {exc}") from exc
        if isinstance(row, dict):
            rows.append(row)
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def relpath(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def stable_id(prefix: str, payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def recommendation_id(payload: dict[str, Any]) -> str:
    """Stable identity for an advisory recommendation across rematerializations."""

    stable_payload = {
        key: value
        for key, value in payload.items()
        if key not in {"generated_at", "recommendation_id"}
    }
    return stable_id("sr", stable_payload)


def display_surface(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    overrides = {
        "missing_decision_use": "forecast decisions are missing",
        "weak_gp233_linkage": "evidence links need repair",
        "missing_source": "source archive is missing",
        "stale_trajectory_output": "run-history archive is stale",
        "unconsumed_surface": "work log is missing",
        "unmaterialized_surfacing_consumption": "accepted work is not in the action record",
        "missing_workbench_router_decision": "workbench route choice is missing",
        "invalid_agentic_workbench_rows": "workbench action rows need repair",
        "missing_agentic_workbench_decision_rows": "workbench decisions are missing",
        "repair_source_emitter": "repair source logs",
        "trajectory_surfacing": "run-history surfacing",
        "forecast_ops": "forecast records",
        "agentic_workbench": "workbench actions",
        "catch": "catch ledger",
        "gp233": "evidence ledger",
        "warning": "warning",
        "blocking": "blocking",
        "info": "info",
    }
    if raw in overrides:
        return overrides[raw]
    return raw.replace("_", " ").replace("-", " ").strip()


def display_source_health_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    replacements = {
        "markdown-only GP-233 linkage": "doc-only evidence-ledger linkage",
        "GP-233": "evidence ledger",
        "gp233": "evidence ledger",
        "GP-230": "forecast record",
        "gp230": "forecast record",
        "trajectory outputs": "run-history outputs",
        "trajectory archive": "run-history archive",
        "trajectory/primitives surfacing": "run-history surfacing",
        "surfacing event rows": "work-log rows",
        "surfacing consumption action-impact rows": "accepted-work rows",
        "materialized surfacing action-impact rows": "accepted-work rows in the action record",
        "action-impact rows": "action-record rows",
        "forecast_ops": "forecast records",
        "agentic-workbench": "workbench",
        "RD/agent": "research/agent",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def display_source_health_recommended_action(issue_type: Any, recommended_action: Any) -> str:
    issue_overrides = {
        "weak_gp233_linkage": "repair evidence links",
        "stale_trajectory_output": "refresh run-history archive",
        "unconsumed_surface": "record work-log use",
    }
    raw_issue = str(issue_type or "")
    if raw_issue in issue_overrides:
        return issue_overrides[raw_issue]
    return display_surface(recommended_action)


def as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_json_list(text: str | None, field: str) -> list[str]:
    if text is None or text == "":
        return []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{field} must be a JSON list") from exc
    if not isinstance(payload, list):
        raise SystemExit(f"{field} must be a JSON list")
    return [str(item) for item in payload]


def score_path(contract_id: str) -> Path:
    return SCORES / f"{contract_id}.json"


def aggregate_path(contract_id: str) -> Path:
    return AGGREGATES / f"{contract_id}.json"


def outcome_path(contract_id: str) -> Path:
    return OUTCOMES / f"{contract_id}.json"


def top_failure_mode(summary: dict[str, Any]) -> str | None:
    modes = summary.get("top_failure_modes")
    if isinstance(modes, list) and modes:
        first = modes[0]
        if isinstance(first, dict):
            return str(first.get("mode") or "") or None
        return str(first)
    return None


def forecast_spread_from_recommendation(allocation: dict[str, Any]) -> float | None:
    return as_float(allocation.get("forecast_spread"))


def selected_action_from_decision_use(row: dict[str, Any]) -> str:
    used_for = str(row.get("used_for") or "")
    mapped = GP230_USED_FOR_TO_GP243.get(used_for)
    if mapped:
        return mapped
    raw_new = str(row.get("new_action") or "").strip()
    if raw_new in FORECAST_ACTIONS:
        return raw_new
    return "repair_source_emitter"


def validate_action_impact(row: dict[str, Any], *, live: bool = True) -> list[str]:
    errors: list[str] = []
    candidate_actions = row.get("candidate_actions")
    if not isinstance(candidate_actions, list):
        errors.append("candidate_actions must be a list")
        candidate_actions = []
    selected = row.get("selected_action")
    if selected not in candidate_actions:
        errors.append("selected_action must be present in candidate_actions")
    policy_source = row.get("policy_source")
    if live and policy_source == "shadow_policy":
        errors.append("live rows may not use policy_source=shadow_policy")
    if selected in {"ignore_forecast", "override_forecast"}:
        notes = ((row.get("counterfactual") or {}).get("notes") or "").strip()
        if not notes:
            errors.append("ignore/override rows require counterfactual.notes")
    return errors


def action_impact_from_decision_use(row: dict[str, Any]) -> dict[str, Any]:
    contract_id = str(row.get("contract_id") or "")
    decision_use_id = str(row.get("decision_use_id") or stable_id("du_missing", row))
    aggregate_summary = row.get("aggregate_summary")
    if not isinstance(aggregate_summary, dict):
        aggregate_summary = {}
    allocation = aggregate_summary.get("allocation_recommendation")
    if not isinstance(allocation, dict):
        allocation = {}
    selected_action = selected_action_from_decision_use(row)
    outcome = read_json(outcome_path(contract_id), {}) if contract_id else {}
    score = read_json(score_path(contract_id), {}) if contract_id else {}
    known = isinstance(outcome, dict) and bool(outcome)
    decision_id = decision_use_id
    impact = {
        "schema_version": 1,
        "action_impact_id": stable_id("ai", {"decision_use_id": decision_use_id}),
        "recorded_at": row.get("recorded_at") or now_iso(),
        "decision_point": {
            "decision_id": decision_id,
            "tick_id": row.get("tick_id"),
            "project_id": None,
            "domain": "forecast_ops",
            "stage": row.get("decision_stage") or "manual",
        },
        "candidate_actions": FORECAST_ACTIONS,
        "selected_action": selected_action,
        "policy_source": "forecast_market",
        "logged_policy": {
            "logging_policy": "gp230_allocation",
            "propensity_or_selection_rule": "gp230_allocation_recommendation",
            "eligible_actions": FORECAST_ACTIONS,
            "why_selected": row.get("forecast_delta"),
            "why_not_selected": {},
        },
        "source_refs": {
            "forecast_contract_id": contract_id or None,
            "decision_use_id": decision_use_id,
            "forecast_aggregate_path": relpath(aggregate_path(contract_id)) if contract_id else None,
            "forecast_score_path": relpath(score_path(contract_id)) if contract_id and score_path(contract_id).exists() else None,
            "gp233_evidence_ref": None,
            "catch_ids": [],
            "trajectory_refs": [],
            "prediction_ids": [],
        },
        "context_features": {
            "p_success": aggregate_summary.get("p_success"),
            "expected_cost_agent_minutes": aggregate_summary.get("expected_cost_agent_minutes"),
            "forecast_spread": forecast_spread_from_recommendation(allocation),
            "top_failure_mode": top_failure_mode(aggregate_summary),
            "current_bottleneck": None,
            "next_lever": None,
            "surface_kind": None,
            "gp230_allocation_action": allocation.get("action") or allocation.get("recommendation"),
            "gp230_allocation_reason": allocation.get("reason"),
        },
        "outcome": {
            "known": known,
            "success_bool": outcome.get("success_bool") if isinstance(outcome, dict) else None,
            "decision_impact": outcome.get("decision_impact") if isinstance(outcome, dict) else None,
            "yield_signal": None,
            "actual_cost_agent_minutes": outcome.get("actual_cost_agent_minutes") if isinstance(outcome, dict) else None,
            "negative_externality_tags": outcome.get("negative_externality_tags") if isinstance(outcome, dict) else [],
            "catch_ids_realized": [],
            "score_mean_brier": score.get("mean_brier") if isinstance(score, dict) else None,
        },
        "counterfactual": {
            "baseline_action": row.get("old_action"),
            "counterfactual_action": row.get("new_action"),
            "counterfactual_value_bucket": None,
            "notes": row.get("ignored_forecast_reason") or row.get("notes"),
        },
    }
    errors = validate_action_impact(impact)
    if errors:
        impact["validation_errors"] = errors
    return impact


def validate_surfacing_event(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if row.get("surface_kind") not in SURFACE_KIND_TO_ACTION:
        errors.append("surface_kind must be one of: " + ", ".join(sorted(SURFACE_KIND_TO_ACTION)))
    if not str(row.get("surface_payload_ref") or "").strip():
        errors.append("surface_payload_ref is required")
    if not str(row.get("project_family") or "").strip():
        errors.append("project_family is required")
    rank = row.get("rank")
    if not isinstance(rank, int) or rank < 1:
        errors.append("rank must be an integer >= 1")
    if not isinstance(row.get("consumed_bool"), bool):
        errors.append("consumed_bool must be boolean")
    if row.get("consumed_bool") and not row.get("consumed_by_tick"):
        errors.append("consumed surfacing events require consumed_by_tick")
    tags = row.get("negative_externality_tags")
    if tags is not None and not isinstance(tags, list):
        errors.append("negative_externality_tags must be a list")
    selected = row.get("selected_action")
    if selected is not None and selected not in SURFACING_ACTIONS:
        errors.append("selected_action must be a trajectory/primitives surfacing action")
    return errors


def surfacing_event_from_args(args: argparse.Namespace) -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "surface_kind": args.surface_kind,
        "surface_payload_ref": args.surface_payload_ref,
        "project_family": args.project_family,
        "target_decision_id": args.target_decision_id,
        "shown_at": args.shown_at or now_iso(),
        "rank": args.rank,
        "consumed_bool": bool(args.consumed_bool),
        "consumed_at": args.consumed_at,
        "consumed_by_tick": args.consumed_by_tick,
        "suppressed_reason": args.suppressed_reason,
        "negative_externality_tags": parse_json_list(
            args.negative_externality_tags_json,
            "--negative-externality-tags-json",
        ),
        "selected_action": args.selected_action,
        "policy_source": args.policy_source,
        "decision_impact": args.decision_impact,
        "yield_signal": args.yield_signal,
        "outcome_known": bool(args.outcome_known),
        "notes": args.notes,
    }
    payload["surface_id"] = args.surface_id or stable_id("sf", {
        "surface_kind": payload["surface_kind"],
        "surface_payload_ref": payload["surface_payload_ref"],
        "project_family": payload["project_family"],
        "target_decision_id": payload["target_decision_id"],
        "shown_at": payload["shown_at"],
        "rank": payload["rank"],
    })
    if payload["consumed_bool"] and not payload["consumed_at"]:
        payload["consumed_at"] = now_iso()
    if payload["selected_action"] is None:
        payload["selected_action"] = SURFACE_KIND_TO_ACTION.get(str(payload["surface_kind"]))
    return payload


def surfacing_event_to_action_impact(row: dict[str, Any]) -> dict[str, Any] | None:
    consumed = row.get("consumed_bool") is True
    suppressed = bool(row.get("suppressed_reason"))
    if not consumed and not suppressed:
        return None
    surface_id = str(row.get("surface_id") or stable_id("sf_missing", row))
    selected = str(row.get("selected_action") or "")
    if selected not in SURFACING_ACTIONS:
        selected = "suppress_surface_as_low_voi" if suppressed else SURFACE_KIND_TO_ACTION.get(str(row.get("surface_kind")), "repair_source_emitter")
    surface_kind = row.get("surface_kind")
    surface_payload_ref = row.get("surface_payload_ref")
    trajectory_refs = (
        [surface_payload_ref]
        if surface_kind in {
            "trajectory_cluster",
            "pattern",
            "anti_pattern",
            "primitive_promotion_review",
        }
        and surface_payload_ref
        else []
    )
    impact = {
        "schema_version": 1,
        "action_impact_id": stable_id("ai", {"surface_id": surface_id}),
        "recorded_at": row.get("consumed_at") or row.get("shown_at") or now_iso(),
        "decision_point": {
            "decision_id": row.get("target_decision_id") or surface_id,
            "tick_id": row.get("consumed_by_tick"),
            "project_id": None,
            "domain": "trajectory_surfacing",
            "stage": "pretick",
        },
        "candidate_actions": SURFACING_ACTIONS,
        "selected_action": selected,
        "policy_source": row.get("policy_source") or "trajectory_miner",
        "logged_policy": {
            "logging_policy": "trajectory_surface",
            "propensity_or_selection_rule": "shown_rank_then_consumed",
            "eligible_actions": SURFACING_ACTIONS,
            "why_selected": row.get("notes") or row.get("suppressed_reason"),
            "why_not_selected": {},
        },
        "source_refs": {
            "forecast_contract_id": None,
            "decision_use_id": None,
            "surface_event_id": surface_id,
            "surfacing_event_path": relpath(SURFACING_EVENT_LEDGER),
            "forecast_aggregate_path": None,
            "forecast_score_path": None,
            "gp233_evidence_ref": surface_payload_ref if surface_kind == "gp233_next_lever" else None,
            "catch_ids": [surface_payload_ref] if surface_kind == "catch_preconditioner" else [],
            "trajectory_refs": trajectory_refs,
            "prediction_ids": [],
            "source_refs": [surface_payload_ref] if surface_payload_ref else [],
        },
        "context_features": {
            "p_success": None,
            "expected_cost_agent_minutes": None,
            "forecast_spread": None,
            "top_failure_mode": None,
            "current_bottleneck": None,
            "next_lever": None,
            "surface_kind": surface_kind,
            "surface_rank": row.get("rank"),
            "project_family": row.get("project_family"),
            "promotion_decision": row.get("promotion_decision"),
            "typed_carrier": row.get("typed_carrier"),
            "nearest_confuser": row.get("nearest_confuser"),
        },
        "outcome": {
            "known": bool(row.get("outcome_known")),
            "success_bool": None,
            "decision_impact": row.get("decision_impact"),
            "yield_signal": row.get("yield_signal"),
            "actual_cost_agent_minutes": None,
            "negative_externality_tags": row.get("negative_externality_tags") or [],
            "catch_ids_realized": [],
        },
        "counterfactual": {
            "baseline_action": None,
            "counterfactual_action": "suppress_surface_as_low_voi" if consumed else None,
            "counterfactual_value_bucket": None,
            "notes": row.get("notes") or row.get("suppressed_reason"),
        },
    }
    errors = validate_action_impact(impact)
    if errors:
        impact["validation_errors"] = errors
    return impact


def validate_agentic_workbench_impact(row: dict[str, Any]) -> list[str]:
    errors = validate_action_impact(row)
    if (row.get("decision_point") or {}).get("domain") != "agentic_workbench":
        errors.append("decision_point.domain must be agentic_workbench")
    selected = row.get("selected_action")
    if selected not in AGENTIC_WORKBENCH_ACTIONS:
        errors.append("selected_action must be an agentic workbench action")
    context = row.get("context_features")
    if not isinstance(context, dict):
        errors.append("context_features must be an object")
        context = {}
    router_decision = context.get("workbench_router_decision")
    if router_decision not in {
        "invoke_autoresearch",
        "prepare_autoresearch_surface",
        "stay_out_of_loop",
        "not_evaluated",
    }:
        errors.append(
            "context_features.workbench_router_decision must be invoke_autoresearch, "
            "prepare_autoresearch_surface, stay_out_of_loop, or not_evaluated"
        )
    bypassed_ready_workbench = (
        router_decision == "invoke_autoresearch"
        and selected != "invoke_autoresearch"
    )
    explicit_out_of_loop = selected in {"run_out_of_loop_agent", "stay_out_of_loop"}
    if (bypassed_ready_workbench or explicit_out_of_loop) and not str(context.get("why_not_autoresearch") or "").strip():
        errors.append(f"{selected} requires context_features.why_not_autoresearch")
    operator_card_routes = context.get("operator_card_routes")
    if operator_card_routes is not None:
        if not isinstance(operator_card_routes, list):
            errors.append("context_features.operator_card_routes must be a list when present")
        else:
            for idx, route in enumerate(operator_card_routes, start=1):
                if not isinstance(route, dict):
                    errors.append(f"context_features.operator_card_routes[{idx}] must be an object")
                    continue
                if not str(route.get("card_id") or "").strip():
                    errors.append(f"context_features.operator_card_routes[{idx}] missing card_id")
                if not str(route.get("route_mode") or "").strip():
                    errors.append(f"context_features.operator_card_routes[{idx}] missing route_mode")
    operator_card_ids = context.get("operator_card_ids")
    if operator_card_ids is not None and not isinstance(operator_card_ids, list):
        errors.append("context_features.operator_card_ids must be a list when present")
    source_refs = (row.get("source_refs") or {}).get("source_refs")
    if not isinstance(source_refs, list):
        source_refs = []
    has_route_ref = any(
        "route" in str(ref).lower() and str(ref).lower().endswith(".json")
        for ref in source_refs
    )
    if not has_route_ref:
        errors.append("agentic workbench rows require a route JSON source ref")
    return errors


def agentic_workbench_impact_from_args(args: argparse.Namespace) -> dict[str, Any]:
    source_refs = parse_json_list(args.source_refs_json, "--source-refs-json")
    route_json_ref = str(getattr(args, "route_json_ref", "") or "").strip()
    if route_json_ref and route_json_ref not in source_refs:
        source_refs = [route_json_ref, *source_refs]
    catch_ids = parse_json_list(args.catch_ids_json, "--catch-ids-json")
    negative_tags = parse_json_list(
        args.negative_externality_tags_json,
        "--negative-externality-tags-json",
    )
    worker = {
        "worker_archetype": args.worker_archetype,
        "worker_capability": args.worker_capability,
        "worker_state": args.worker_state,
        "worker_identity": args.worker_identity,
        "transport": args.transport,
    }
    operator_card_routes = _operator_card_routes_from_args(args)
    payload = {
        "schema_version": 1,
        "action_impact_id": args.action_impact_id,
        "recorded_at": args.recorded_at or now_iso(),
        "decision_point": {
            "decision_id": args.decision_id,
            "tick_id": args.tick_id,
            "project_id": args.project_id,
            "domain": "agentic_workbench",
            "stage": args.stage,
        },
        "candidate_actions": AGENTIC_WORKBENCH_ACTIONS,
        "selected_action": args.selected_action,
        "policy_source": args.policy_source,
        "logged_policy": {
            "logging_policy": "rd_workbench_router",
            "propensity_or_selection_rule": args.selection_rule,
            "eligible_actions": AGENTIC_WORKBENCH_ACTIONS,
            "why_selected": args.why_selected,
            "why_not_selected": {},
        },
        "source_refs": {
            "forecast_contract_id": args.forecast_contract_id,
            "decision_use_id": None,
            "surface_event_id": None,
            "surfacing_event_path": None,
            "forecast_aggregate_path": None,
            "forecast_score_path": None,
            "gp233_evidence_ref": args.gp233_evidence_ref,
            "catch_ids": catch_ids,
            "trajectory_refs": source_refs,
            "prediction_ids": parse_json_list(args.prediction_ids_json, "--prediction-ids-json"),
            "source_refs": source_refs,
        },
        "context_features": {
            "task": args.task,
            "project_family": args.project_family,
            "workbench_router_decision": args.workbench_router_decision,
            "why_not_autoresearch": args.why_not_autoresearch,
            "bounded_claim": args.bounded_claim,
            "stable_evaluator": args.stable_evaluator,
            "rubric_ready": args.rubric_ready,
            "artifact_surface": args.artifact_surface,
            "worker": worker,
            "operator_card_routes": operator_card_routes,
            "operator_card_ids": _operator_card_ids(operator_card_routes),
        },
        "outcome": {
            "known": bool(args.outcome_known),
            "success_bool": args.success_bool,
            "decision_impact": args.decision_impact,
            "yield_signal": args.yield_signal,
            "actual_cost_agent_minutes": args.actual_cost_agent_minutes,
            "negative_externality_tags": negative_tags,
            "catch_ids_realized": catch_ids,
        },
        "counterfactual": {
            "baseline_action": args.baseline_action,
            "counterfactual_action": args.counterfactual_action,
            "counterfactual_value_bucket": args.counterfactual_value_bucket,
            "notes": args.notes,
        },
    }
    if not payload["action_impact_id"]:
        payload["action_impact_id"] = stable_id("ai", {
            "domain": "agentic_workbench",
            "decision_id": payload["decision_point"]["decision_id"],
            "task": args.task,
            "recorded_at": payload["recorded_at"],
        })
    errors = validate_agentic_workbench_impact(payload)
    if errors:
        payload["validation_errors"] = errors
    return payload


def _route_missing_reason(route: dict[str, Any]) -> str:
    missing = route.get("missing")
    if isinstance(missing, list) and missing:
        return "router missing prerequisites: " + ", ".join(str(item) for item in missing)
    suggestion = str(route.get("suggested_next_step") or "").strip()
    if suggestion:
        return "router suggested next step: " + suggestion
    return "router did not mark the autoresearch surface ready"


def _worker_defaults_for_agentic_route(
    selected_action: str,
    subscription_worker_available: bool,
) -> dict[str, str]:
    if selected_action == "invoke_autoresearch":
        return {
            "worker_archetype": "fungible_agent_worker" if subscription_worker_available else "fungible_llm_call",
            "worker_capability": "tool_using_agent" if subscription_worker_available else "bare_llm_call",
            "worker_state": "stateless",
            "worker_identity": "fungible",
            "transport": "subscription_cli" if subscription_worker_available else "api",
        }
    return {
        "worker_archetype": "persistent_agent",
        "worker_capability": "tool_using_agent",
        "worker_state": "stateful",
        "worker_identity": "persistent",
        "transport": "subscription_cli",
    }


def _worker_metadata_from_route(route: dict[str, Any], fallback: dict[str, str]) -> dict[str, str]:
    metadata = route.get("worker_metadata")
    if not isinstance(metadata, dict):
        return fallback
    resolved = dict(fallback)
    for key in (
        "worker_archetype",
        "worker_capability",
        "worker_state",
        "worker_identity",
        "transport",
    ):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            resolved[key] = value.strip()
    return resolved


def _operator_card_routes_from_args(args: argparse.Namespace) -> list[dict[str, Any]]:
    raw = getattr(args, "operator_card_routes", None)
    if isinstance(raw, list):
        return [row for row in raw if isinstance(row, dict)]
    raw_json = getattr(args, "operator_card_routes_json", None)
    if isinstance(raw_json, str) and raw_json.strip():
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise SystemExit("--operator-card-routes-json must be a JSON list") from exc
        if not isinstance(payload, list):
            raise SystemExit("--operator-card-routes-json must be a JSON list")
        return [row for row in payload if isinstance(row, dict)]
    return []


def _operator_card_ids(routes: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for route in routes:
        card_id = str(route.get("card_id") or "").strip()
        if card_id and card_id not in ids:
            ids.append(card_id)
    return ids


ROUTE_PREREQUISITE_FIELDS = (
    "bounded_claim",
    "stable_evaluator",
    "rubric_ready",
    "artifact_surface",
)


def validate_agentic_route_json_contract(route: dict[str, Any]) -> list[str]:
    """Validate the source route JSON before it becomes an action row."""

    errors: list[str] = []
    decision = str(route.get("decision") or "not_evaluated")
    if decision not in ROUTER_DECISION_TO_AGENTIC_ACTION:
        errors.append(f"unknown route decision: {decision!r}")
    for field in ROUTE_PREREQUISITE_FIELDS:
        if field not in route:
            errors.append(f"route JSON missing {field}")
        elif not isinstance(route.get(field), bool):
            errors.append(f"route JSON {field} must be boolean")
    if errors:
        return errors

    ready = all(bool(route.get(field)) for field in ROUTE_PREREQUISITE_FIELDS)
    any_partial_surface = any(
        bool(route.get(field))
        for field in ("bounded_claim", "stable_evaluator", "rubric_ready")
    )
    missing = route.get("missing")
    missing_count = len(missing) if isinstance(missing, list) else 0

    if decision == "invoke_autoresearch":
        if not ready:
            errors.append(
                "route decision invoke_autoresearch requires bounded_claim, "
                "stable_evaluator, rubric_ready, and artifact_surface all true"
            )
        if missing_count:
            errors.append("route decision invoke_autoresearch requires empty missing list")
    elif decision == "prepare_autoresearch_surface":
        if ready:
            errors.append("ready route should use invoke_autoresearch, not prepare_autoresearch_surface")
        if not any_partial_surface:
            errors.append(
                "prepare_autoresearch_surface requires at least one bounded/evaluator/rubric surface"
            )
        if missing_count == 0:
            errors.append("prepare_autoresearch_surface requires non-empty missing list")
    elif decision == "stay_out_of_loop":
        if ready:
            errors.append("ready route should use invoke_autoresearch, not stay_out_of_loop")
        if missing_count == 0:
            errors.append("stay_out_of_loop requires non-empty missing list")
    return errors


def agentic_workbench_impact_from_route_args(args: argparse.Namespace) -> dict[str, Any]:
    route = read_json(args.route_json, None)
    if not isinstance(route, dict):
        raise SystemExit("--route-json must point to a router JSON object")
    route_errors = validate_agentic_route_json_contract(route)
    if route_errors:
        raise SystemExit("invalid agentic route JSON: " + "; ".join(route_errors))
    decision = str(route.get("decision") or "not_evaluated")
    if decision not in ROUTER_DECISION_TO_AGENTIC_ACTION:
        raise SystemExit(f"unknown route decision in {args.route_json}: {decision!r}")

    selected_action = args.selected_action or ROUTER_DECISION_TO_AGENTIC_ACTION[decision]
    subscription_worker_available = bool(route.get("subscription_worker_available"))
    worker_defaults = _worker_defaults_for_agentic_route(
        selected_action,
        subscription_worker_available,
    )
    worker_defaults = _worker_metadata_from_route(route, worker_defaults)
    route_ref = relpath(args.route_json)
    extra_refs = parse_json_list(args.source_refs_json, "--source-refs-json")
    source_refs = [route_ref, *extra_refs]

    why_not = args.why_not_autoresearch
    if selected_action in {"run_out_of_loop_agent", "stay_out_of_loop"} and not why_not:
        why_not = _route_missing_reason(route)

    why_selected = args.why_selected
    if not why_selected:
        why_selected = f"router decision {decision}; selected {selected_action}"

    project = str(route.get("project") or "").strip()
    ns = argparse.Namespace(
        action_impact_id=args.action_impact_id,
        recorded_at=args.recorded_at,
        decision_id=args.decision_id,
        tick_id=args.tick_id,
        project_id=args.project_id or project or None,
        project_family=args.project_family or project or "unknown",
        stage=args.stage,
        task=args.task or str(route.get("task") or ""),
        selected_action=selected_action,
        policy_source=args.policy_source,
        selection_rule=args.selection_rule,
        why_selected=why_selected,
        workbench_router_decision=decision,
        why_not_autoresearch=why_not,
        bounded_claim=bool(route.get("bounded_claim")),
        stable_evaluator=bool(route.get("stable_evaluator")),
        rubric_ready=bool(route.get("rubric_ready")),
        artifact_surface=bool(route.get("artifact_surface")),
        worker_archetype=args.worker_archetype or worker_defaults["worker_archetype"],
        worker_capability=args.worker_capability or worker_defaults["worker_capability"],
        worker_state=args.worker_state or worker_defaults["worker_state"],
        worker_identity=args.worker_identity or worker_defaults["worker_identity"],
        transport=args.transport or worker_defaults["transport"],
        operator_card_routes=route.get("operator_card_routes")
        if isinstance(route.get("operator_card_routes"), list)
        else [],
        forecast_contract_id=args.forecast_contract_id,
        gp233_evidence_ref=args.gp233_evidence_ref,
        route_json_ref=None,
        source_refs_json=json.dumps(source_refs),
        prediction_ids_json=args.prediction_ids_json,
        catch_ids_json=args.catch_ids_json,
        outcome_known=args.outcome_known,
        success_bool=args.success_bool,
        decision_impact=args.decision_impact,
        yield_signal=args.yield_signal,
        actual_cost_agent_minutes=args.actual_cost_agent_minutes,
        negative_externality_tags_json=args.negative_externality_tags_json,
        baseline_action=args.baseline_action,
        counterfactual_action=args.counterfactual_action,
        counterfactual_value_bucket=args.counterfactual_value_bucket,
        notes=args.notes,
    )
    if not ns.task:
        raise SystemExit("route JSON does not contain task; pass --task")
    return agentic_workbench_impact_from_args(ns)


def gp233_rows() -> list[dict[str, Any]]:
    if not GP233_LEDGER.exists():
        return []
    rows: list[dict[str, Any]] = []
    lines = GP233_LEDGER.read_text(encoding="utf-8", errors="ignore").splitlines()
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped or "Date" in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 6:
            continue
        text = " ".join(cells)
        stable_refs = re.findall(r"\b(?:tick|GP-|gp)\d+[A-Za-z0-9_.-]*\b", text)
        rows.append({
            "line": idx,
            "date": cells[0],
            "lane": cells[1],
            "evidence_pointer": cells[2],
            "bottleneck": cells[3],
            "decision_changed": cells[4],
            "verdict": cells[5],
            "has_structured_link": bool(stable_refs),
            "stable_refs": sorted(set(stable_refs))[:10],
        })
    return rows


def latest_existing(paths: list[Path]) -> Path | None:
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime)


def source_health_model(action_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    action_rows = action_rows or []
    issues: list[dict[str, Any]] = []

    def add_issue(
        *,
        severity: str,
        scope: str,
        issue_type: str,
        expected_count: int,
        observed_count: int,
        denominator: str,
        blocking_rule: str,
        evidence_refs: list[str],
        domain: str | None = None,
        freshness_window_days: int = 14,
        affected_domains: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "severity": severity,
            "scope": scope,
            "domain": domain,
            "issue_type": issue_type,
            "expected_count": expected_count,
            "observed_count": observed_count,
            "denominator": denominator,
            "freshness_window_days": freshness_window_days,
            "affected_domains": affected_domains or [],
            "blocking_rule": blocking_rule,
            "recommended_action": "repair_source_emitter",
            "evidence_refs": evidence_refs,
        }
        if details:
            payload["details"] = details
        payload["issue_id"] = stable_id("sh", payload)
        payload.update({
            "display_severity": display_surface(severity),
            "display_scope": display_surface(scope),
            "display_domain": display_surface(domain),
            "display_issue_type": display_surface(issue_type),
            "display_denominator": display_source_health_text(denominator),
            "display_blocking_rule": display_source_health_text(blocking_rule),
            "display_recommended_action": display_source_health_recommended_action(
                issue_type,
                payload["recommended_action"],
            ),
            "display_affected_domains": [
                display_surface(item) for item in (affected_domains or [])
            ],
        })
        issues.append(payload)

    aggregate_count = len(list(AGGREGATES.glob("*.json"))) if AGGREGATES.exists() else 0
    decision_rows = read_jsonl(DECISION_USE_LEDGER)
    if aggregate_count and len(decision_rows) == 0:
        add_issue(
            severity="blocking",
            scope="forecast_ops",
            issue_type="missing_decision_use",
            expected_count=aggregate_count,
            observed_count=0,
            denominator="forecast aggregates",
            blocking_rule="forecast_ops recommendations remain diagnostic until decision-use rows exist",
            evidence_refs=[relpath(AGGREGATES), relpath(DECISION_USE_LEDGER)],
            affected_domains=["forecast_ops"],
        )

    gp233 = gp233_rows()
    weak_gp233 = [row for row in gp233 if not row["has_structured_link"]]
    if gp233 and weak_gp233:
        add_issue(
            severity="warning",
            scope="gp233",
            issue_type="weak_gp233_linkage",
            expected_count=len(gp233),
            observed_count=len(gp233) - len(weak_gp233),
            denominator="GP-233 markdown rows with stable refs",
            blocking_rule="markdown-only GP-233 linkage cannot support non-diagnostic recommendations",
            evidence_refs=[relpath(GP233_LEDGER)],
            affected_domains=["trajectory_surfacing", "forecast_ops"],
        )

    trajectory_source = latest_existing([TRAJECTORY_ARCHIVE_ENRICHED, TRAJECTORY_ARCHIVE])
    if trajectory_source is None:
        add_issue(
            severity="blocking",
            scope="trajectory_surfacing",
            issue_type="missing_source",
            expected_count=1,
            observed_count=0,
            denominator="trajectory archive",
            blocking_rule="trajectory surfacing disabled without trajectory archive",
            evidence_refs=[relpath(TRAJECTORY_ARCHIVE_ENRICHED), relpath(TRAJECTORY_ARCHIVE)],
            affected_domains=["trajectory_surfacing"],
        )
    else:
        age_days = (datetime.now(timezone.utc).timestamp() - trajectory_source.stat().st_mtime) / 86400.0
        if age_days > 14:
            add_issue(
                severity="warning",
                scope="trajectory_surfacing",
                issue_type="stale_trajectory_output",
                expected_count=1,
                observed_count=0,
                denominator="trajectory archive freshness <=14d",
                freshness_window_days=14,
                blocking_rule="stale trajectory outputs force diagnostic-only surfacing",
                evidence_refs=[relpath(trajectory_source)],
                affected_domains=["trajectory_surfacing"],
            )

    surfacing_events = read_jsonl(SURFACING_EVENT_LEDGER)
    consumed_surfacing_events = [row for row in surfacing_events if row.get("consumed_bool") is True]
    surfacing_rows = [
        row for row in action_rows
        if ((row.get("decision_point") or {}).get("domain") == "trajectory_surfacing")
    ]
    if trajectory_source is not None and not surfacing_events:
        add_issue(
            severity="warning",
            scope="trajectory_surfacing",
            issue_type="unconsumed_surface",
            expected_count=1,
            observed_count=0,
            denominator="surfacing event rows",
            blocking_rule="trajectory/primitives surfacing remains diagnostic until shown surfaces are logged",
            evidence_refs=[relpath(SURFACING_EVENT_LEDGER)],
            affected_domains=["trajectory_surfacing"],
        )
    elif not consumed_surfacing_events:
        add_issue(
            severity="warning",
            scope="trajectory_surfacing",
            issue_type="unconsumed_surface",
            expected_count=1,
            observed_count=0,
            denominator="surfacing consumption action-impact rows",
            blocking_rule="trajectory/primitives surfacing recommendations are diagnostic until at least one surfacing event is consumed or suppressed",
            evidence_refs=[relpath(SURFACING_EVENT_LEDGER), relpath(ACTION_IMPACT_LEDGER)],
            affected_domains=["trajectory_surfacing"],
        )
    elif not surfacing_rows:
        add_issue(
            severity="warning",
            scope="trajectory_surfacing",
            issue_type="unmaterialized_surfacing_consumption",
            expected_count=len(consumed_surfacing_events),
            observed_count=0,
            denominator="materialized surfacing action-impact rows",
            blocking_rule="consumed surfacing events remain diagnostic until action-impact rows are materialized",
            evidence_refs=[relpath(SURFACING_EVENT_LEDGER), relpath(ACTION_IMPACT_LEDGER)],
            affected_domains=["trajectory_surfacing"],
        )

    agentic_rows = [
        row for row in action_rows
        if ((row.get("decision_point") or {}).get("domain") == "agentic_workbench")
    ]
    unevaluated_agentic = [
        row for row in agentic_rows
        if ((row.get("context_features") or {}).get("workbench_router_decision") in {None, "", "not_evaluated"})
    ]
    if agentic_rows and unevaluated_agentic:
        add_issue(
            severity="warning",
            scope="agentic_workbench",
            issue_type="missing_workbench_router_decision",
            expected_count=len(agentic_rows),
            observed_count=len(agentic_rows) - len(unevaluated_agentic),
            denominator="out-of-loop agent action-impact rows with router decision",
            blocking_rule=(
                "manual agent work remains diagnostic until each row records whether "
                "autoresearch was invoked, prepared, or bypassed with a reason"
            ),
            evidence_refs=[relpath(ACTION_IMPACT_LEDGER)],
            affected_domains=["agentic_workbench"],
        )
    invalid_agentic: list[tuple[dict[str, Any], list[str]]] = []
    for row in agentic_rows:
        errors = validate_agentic_workbench_impact(row)
        if errors:
            invalid_agentic.append((row, errors))
    if agentic_rows and invalid_agentic:
        add_issue(
            severity="warning",
            scope="agentic_workbench",
            issue_type="invalid_agentic_workbench_rows",
            expected_count=len(agentic_rows),
            observed_count=len(agentic_rows) - len(invalid_agentic),
            denominator="agentic-workbench action-impact rows passing schema and router checks",
            blocking_rule=(
                "workbench coverage is diagnostic until route rows carry valid selected action, "
                "router decision, and bypass rationale fields"
            ),
            evidence_refs=[relpath(ACTION_IMPACT_LEDGER)],
            affected_domains=["agentic_workbench"],
            details={
                "invalid_rows": [
                    {
                        "action_impact_id": row.get("action_impact_id"),
                        "decision_id": (row.get("decision_point") or {}).get("decision_id"),
                        "selected_action": row.get("selected_action"),
                        "workbench_router_decision": (
                            row.get("context_features") or {}
                        ).get("workbench_router_decision"),
                        "validation_errors": errors,
                    }
                    for row, errors in invalid_agentic[:5]
                ],
                "invalid_row_count": len(invalid_agentic),
            },
        )
    bifurcation = read_json(BIFURCATION_REPORT, {})
    agent_work_share = (bifurcation.get("bifurcation") or {}).get("agent_work_share")
    if isinstance(agent_work_share, (int, float)) and agent_work_share >= 0.5 and not agentic_rows:
        add_issue(
            severity="warning",
            scope="agentic_workbench",
            issue_type="missing_agentic_workbench_decision_rows",
            expected_count=1,
            observed_count=0,
            denominator="bifurcation report with out-of-loop majority and agentic-workbench action rows",
            blocking_rule=(
                "reflexive mining already shows out-of-loop work dominates; "
                "decision-level workbench rows are needed to explain which RD/agent tasks "
                "invoked autoresearch, prepared missing surfaces, or stayed out of loop"
            ),
            evidence_refs=[relpath(BIFURCATION_REPORT), relpath(ACTION_IMPACT_LEDGER)],
            affected_domains=["agentic_workbench"],
        )
    consequential_catches = [
        row for row in read_jsonl(CATCH_LEDGER)
        if row.get(LEGACY_CONSEQUENTIAL_CATCH_KEY) is True or row.get("consequential") is True
    ]
    if consequential_catches and not action_rows:
        add_issue(
            severity="warning",
            scope="catch",
            issue_type="unconsumed_surface",
            expected_count=len(consequential_catches),
            observed_count=0,
            denominator="consequential catch rows linked to action-impact rows",
            blocking_rule="catch preconditioners remain diagnostic until action consumption is recorded",
            evidence_refs=[relpath(CATCH_LEDGER), relpath(ACTION_IMPACT_LEDGER)],
            affected_domains=["trajectory_surfacing"],
        )

    counts = Counter(issue["severity"] for issue in issues)
    return {
        "schema_version": 1,
        "generated_at": now_iso(),
        "source_paths": {
            "decision_use": relpath(DECISION_USE_LEDGER),
            "surfacing_events": relpath(SURFACING_EVENT_LEDGER),
            "aggregates": relpath(AGGREGATES),
            "gp233": relpath(GP233_LEDGER),
            "catch": relpath(CATCH_LEDGER),
            "trajectory": relpath(trajectory_source) if trajectory_source else None,
            "bifurcation_report": relpath(BIFURCATION_REPORT),
        },
        "counts": {
            "issues": len(issues),
            "blocking": counts.get("blocking", 0),
            "warning": counts.get("warning", 0),
            "info": counts.get("info", 0),
            "aggregates": aggregate_count,
            "decision_use_rows": len(decision_rows),
            "action_impact_rows": len(action_rows),
            "agentic_workbench_rows": len(agentic_rows),
            "surfacing_event_rows": len(surfacing_events),
            "consumed_surfacing_events": len(consumed_surfacing_events),
            "gp233_rows": len(gp233),
        },
        "issues": issues,
    }


def scope_has_blocker(health: dict[str, Any], scope: str) -> bool:
    for issue in health.get("issues") or []:
        if issue.get("severity") != "blocking":
            continue
        if issue.get("scope") in {"global", scope}:
            return True
    return False


def repair_recommendation(scope: str, issue: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "domain": scope,
        "decision_id": issue.get("issue_id"),
        "recommended_action": "repair_source_emitter",
        "confidence": "diagnostic_only",
        "rationale": issue.get("blocking_rule") or issue.get("issue_type"),
        "evidence_refs": issue.get("evidence_refs") or [],
        "externality_checks": {
            "negative_externality_risk": "unknown",
            "goodhart_risk": "medium",
            "sample_size": 0,
            "min_sample_size_met": False,
            "confidence_interval": None,
            "uncertainty_note": "source-health defect blocks stronger recommendation",
        },
        "blocking_checks": [issue.get("issue_type") or "source_compilation_defect"],
        "execution_authority": "none_advisory_only",
    }
    payload["recommendation_id"] = recommendation_id(payload)
    return payload


def forecast_ops_recommendations(
    *,
    action_rows: list[dict[str, Any]],
    health: dict[str, Any],
    limit: int = 25,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for issue in health.get("issues") or []:
        if issue.get("severity") == "blocking" and issue.get("scope") in {"global", "forecast_ops"}:
            rows.append(repair_recommendation("forecast_ops", issue))

    sample_size = len([row for row in action_rows if (row.get("decision_point") or {}).get("domain") == "forecast_ops"])
    force_diag = sample_size < 20 or scope_has_blocker(health, "forecast_ops")
    for path in sorted(MARKET_STATE_CONTRACTS.glob("*.json")) if MARKET_STATE_CONTRACTS.exists() else []:
        model = read_json(path, {})
        if not isinstance(model, dict) or model.get("malformed"):
            continue
        fast = model.get("rd_fast_read")
        if not isinstance(fast, dict):
            continue
        allocation = fast.get("allocation_recommendation")
        if not isinstance(allocation, dict):
            continue
        action = allocation.get("action") or allocation.get("recommendation")
        if action not in FORECAST_ACTIONS:
            continue
        lifecycle = model.get("lifecycle") if isinstance(model.get("lifecycle"), dict) else {}
        if lifecycle.get("state") not in {"forecast_fulfilled", "aggregate_ready", "resolved_unscored"}:
            continue
        artifact_paths = model.get("artifact_paths") if isinstance(model.get("artifact_paths"), dict) else {}
        evidence_refs = [relpath(path)]
        for key in ("aggregate", "contract"):
            if artifact_paths.get(key):
                evidence_refs.append(str(artifact_paths[key]))
        rec = {
            "schema_version": 1,
            "generated_at": now_iso(),
            "domain": "forecast_ops",
            "decision_id": str(model.get("contract_id") or path.stem),
            "recommended_action": action,
            "confidence": "diagnostic_only" if force_diag else "low",
            "rationale": allocation.get("reason") or "GP-230 allocation recommendation consumed as read model",
            "evidence_refs": sorted(set(evidence_refs)),
            "externality_checks": {
                "negative_externality_risk": "unknown",
                "goodhart_risk": "medium",
                "sample_size": sample_size,
                "min_sample_size_met": sample_size >= 20,
                "confidence_interval": None,
                "uncertainty_note": (
                    "diagnostic-only until decision-use/action-impact sample is populated"
                    if force_diag else None
                ),
            },
            "blocking_checks": ["source_compilation_defect"] if force_diag else [],
            "execution_authority": "none_advisory_only",
            "source": "gp230_read_model",
            "gp230": {
                "p_success": fast.get("p_success"),
                "expected_cost_agent_minutes": fast.get("expected_cost_agent_minutes"),
                "effective_n": fast.get("effective_n"),
                "meets_two_independent_agents": fast.get("meets_two_independent_agents"),
            },
        }
        rec["recommendation_id"] = recommendation_id(rec)
        rows.append(rec)
        if len(rows) >= limit:
            break
    return rows


def trajectory_rows(limit: int = 500) -> list[dict[str, Any]]:
    path = TRAJECTORY_ARCHIVE_ENRICHED if TRAJECTORY_ARCHIVE_ENRICHED.exists() else TRAJECTORY_ARCHIVE
    rows = read_jsonl(path)
    return rows[-limit:] if limit and len(rows) > limit else rows


def primitive_miss_queue_status(path: Path | None = None) -> dict[str, Any]:
    """Read primitive-amnesia promotion reviews through the canonical classifier."""

    queue_path = path or PRIMITIVE_MISS_QUEUE
    try:
        from ztare.research_director.primitive_amnesia import miss_queue_status
    except ModuleNotFoundError:
        src_path = str(REPO / "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        from ztare.research_director.primitive_amnesia import miss_queue_status
    return miss_queue_status(queue_path)


def primitive_promotion_recommendations(
    *,
    action_rows: list[dict[str, Any]],
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Surface open primitive-amnesia reviews as diagnostic action recommendations.

    This is deliberately not a promotion path. The recommendation is only a
    downstream consumer for the review row; a later surfacing event must record
    whether the review was consumed, suppressed, or closed as a non-promotion.
    """

    try:
        status = primitive_miss_queue_status()
    except Exception as exc:
        rec = {
            "schema_version": 1,
            "generated_at": now_iso(),
            "domain": "trajectory_surfacing",
            "decision_id": stable_id("primitive_miss_queue_unreadable", str(exc)),
            "recommended_action": "repair_source_emitter",
            "confidence": "diagnostic_only",
            "rationale": f"primitive-amnesia miss queue unreadable: {type(exc).__name__}: {str(exc)[:160]}",
            "evidence_refs": [relpath(PRIMITIVE_MISS_QUEUE)],
            "externality_checks": {
                "negative_externality_risk": "unknown",
                "goodhart_risk": "medium",
                "sample_size": 0,
                "min_sample_size_met": False,
                "confidence_interval": None,
                "uncertainty_note": "repair queue source before consuming primitive-promotion reviews",
            },
            "blocking_checks": ["primitive_amnesia_miss_queue_unreadable"],
            "execution_authority": "none_advisory_only",
            "source": "primitive_amnesia_miss_queue",
        }
        rec["recommendation_id"] = recommendation_id(rec)
        return [rec]

    latest_open = [
        row for row in (status.get("latest_open") or [])
        if isinstance(row, dict) and isinstance(row.get("promotion_review"), dict)
    ]
    if not latest_open:
        return []
    sample_size = len([
        row for row in action_rows
        if (
            (row.get("decision_point") or {}).get("domain") == "trajectory_surfacing"
            and (row.get("context_features") or {}).get("surface_kind") == "primitive_promotion_review"
        )
    ])
    rows: list[dict[str, Any]] = []
    for row in latest_open[:limit]:
        review = row["promotion_review"]
        miss_id = str(review.get("miss_id") or row.get("miss_id") or "")
        payload_ref = f"{relpath(PRIMITIVE_MISS_QUEUE)}#{miss_id}" if miss_id else relpath(PRIMITIVE_MISS_QUEUE)
        promotion_decision = str(review.get("promotion_decision") or "review_only")
        selected_action = "surface_primitive_promotion_review"
        if promotion_decision == "close_as_catalog_retrieval_repair":
            selected_action = "repair_source_emitter"
        rationale_parts = [
            promotion_decision,
            str(review.get("non_claim") or "").strip(),
            str(review.get("kill_criterion") or "").strip(),
        ]
        rec = {
            "schema_version": 1,
            "generated_at": now_iso(),
            "domain": "trajectory_surfacing",
            "decision_id": stable_id("primitive_review", {"miss_id": miss_id, "decision": promotion_decision}),
            "recommended_action": selected_action,
            "confidence": "diagnostic_only",
            "rationale": " | ".join(part for part in rationale_parts if part),
            "evidence_refs": [relpath(PRIMITIVE_MISS_QUEUE)],
            "externality_checks": {
                "negative_externality_risk": "medium",
                "goodhart_risk": "medium",
                "sample_size": sample_size,
                "min_sample_size_met": False,
                "confidence_interval": None,
                "uncertainty_note": (
                    "primitive-amnesia reviews are advisory until a surfacing "
                    "event records consumption, suppression, or closure"
                ),
            },
            "blocking_checks": ["primitive_promotion_review_unconsumed"],
            "execution_authority": "none_advisory_only",
            "source": "primitive_amnesia_miss_queue",
            "surface": {
                "surface_kind": "primitive_promotion_review",
                "surface_payload_ref": payload_ref,
                "miss_id": miss_id,
                "case_id": review.get("case_id"),
                "promotion_decision": promotion_decision,
                "typed_carrier": review.get("typed_carrier"),
                "nearest_existing_surface": review.get("nearest_existing_surface"),
                "nearest_confuser": review.get("nearest_confuser"),
            },
        }
        rec["recommendation_id"] = recommendation_id(rec)
        rows.append(rec)
    return rows


def trajectory_recommendations(
    *,
    action_rows: list[dict[str, Any]],
    health: dict[str, Any],
    limit: int = 25,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for issue in health.get("issues") or []:
        if issue.get("severity") == "blocking" and issue.get("scope") in {"global", "trajectory_surfacing"}:
            rows.append(repair_recommendation("trajectory_surfacing", issue))

    sample_size = len([
        row for row in action_rows
        if (row.get("decision_point") or {}).get("domain") == "trajectory_surfacing"
    ])
    force_diag = True
    evidence_refs = [relpath(TRAJECTORY_ARCHIVE_ENRICHED if TRAJECTORY_ARCHIVE_ENRICHED.exists() else TRAJECTORY_ARCHIVE)]
    recent = trajectory_rows()
    weak_points = Counter()
    project_scores: dict[str, list[float]] = {}
    for row in recent:
        project = str(row.get("project") or "unknown")
        score = as_float(row.get("score"))
        if score is not None:
            project_scores.setdefault(project, []).append(score)
        weakest = str(row.get("weakest_point") or "").strip()
        if weakest:
            token = re.sub(r"\s+", " ", weakest[:120]).lower()
            weak_points[token] += 1
    for weakest, count in weak_points.most_common(3):
        if count < 3:
            continue
        rec = {
            "schema_version": 1,
            "generated_at": now_iso(),
            "domain": "trajectory_surfacing",
            "decision_id": stable_id("trajectory_cluster", {"weakest": weakest}),
            "recommended_action": "surface_trajectory_cluster",
            "confidence": "diagnostic_only",
            "rationale": f"repeated weakest-point cluster appears {count} times in recent trajectory archive",
            "evidence_refs": evidence_refs,
            "externality_checks": {
                "negative_externality_risk": "unknown",
                "goodhart_risk": "medium",
                "sample_size": sample_size,
                "min_sample_size_met": False,
                "confidence_interval": None,
                "uncertainty_note": "trajectory surfacing consumption sample is below threshold",
            },
            "blocking_checks": ["unconsumed_surface"] if force_diag else [],
            "execution_authority": "none_advisory_only",
            "surface": {
                "surface_kind": "trajectory_cluster",
                "surface_payload_ref": weakest,
                "support_count": count,
            },
        }
        rec["recommendation_id"] = recommendation_id(rec)
        rows.append(rec)

    gp233 = gp233_rows()
    for gp_row in gp233[-5:]:
        rec = {
            "schema_version": 1,
            "generated_at": now_iso(),
            "domain": "trajectory_surfacing",
            "decision_id": stable_id("gp233_surface", gp_row),
            "recommended_action": "surface_gp233_next_lever",
            "confidence": "diagnostic_only",
            "rationale": "GP-233 next-lever row is available but markdown linkage keeps it diagnostic",
            "evidence_refs": [relpath(GP233_LEDGER)],
            "externality_checks": {
                "negative_externality_risk": "unknown",
                "goodhart_risk": "medium",
                "sample_size": sample_size,
                "min_sample_size_met": False,
                "confidence_interval": None,
                "uncertainty_note": "structured GP-233 identifiers required for stronger claims",
            },
            "blocking_checks": ["weak_gp233_linkage"] if not gp_row.get("has_structured_link") else ["unconsumed_surface"],
            "execution_authority": "none_advisory_only",
            "surface": {
                "surface_kind": "gp233_next_lever",
                "surface_payload_ref": f"{relpath(GP233_LEDGER)}:{gp_row['line']}",
                "bottleneck": gp_row.get("bottleneck"),
                "decision_changed": gp_row.get("decision_changed"),
            },
        }
        rec["recommendation_id"] = recommendation_id(rec)
        rows.append(rec)

    catches = [
        row for row in read_jsonl(CATCH_LEDGER)
        if row.get(LEGACY_CONSEQUENTIAL_CATCH_KEY) is True or row.get("consequential") is True
    ][-5:]
    for catch in catches:
        rec = {
            "schema_version": 1,
            "generated_at": now_iso(),
            "domain": "trajectory_surfacing",
            "decision_id": str(catch.get("catch_id") or stable_id("catch", catch)),
            "recommended_action": "surface_catch_preconditioner",
            "confidence": "diagnostic_only",
            "rationale": str(catch.get("title") or "consequential catch preconditioner available"),
            "evidence_refs": [relpath(CATCH_LEDGER)] + [str(p) for p in catch.get("workpaper_paths") or []],
            "externality_checks": {
                "negative_externality_risk": "medium",
                "goodhart_risk": "medium",
                "sample_size": sample_size,
                "min_sample_size_met": False,
                "confidence_interval": None,
                "uncertainty_note": "catch consumption is not yet linked to action-impact rows",
            },
            "blocking_checks": ["unconsumed_surface"],
            "execution_authority": "none_advisory_only",
            "surface": {
                "surface_kind": "catch_preconditioner",
                "surface_payload_ref": catch.get("catch_id"),
                "category": catch.get("category"),
            },
        }
        rec["recommendation_id"] = recommendation_id(rec)
        rows.append(rec)

    rows.extend(primitive_promotion_recommendations(action_rows=action_rows, limit=limit))
    return rows[:limit]


def materialize_models(write: bool = True) -> dict[str, Any]:
    decision_rows = read_jsonl(DECISION_USE_LEDGER)
    derived_rows = [action_impact_from_decision_use(row) for row in decision_rows]
    surfacing_events = read_jsonl(SURFACING_EVENT_LEDGER)
    derived_surface_rows = [
        row for row in (surfacing_event_to_action_impact(event) for event in surfacing_events)
        if row is not None
    ]
    existing = read_jsonl(ACTION_IMPACT_LEDGER)
    manual_rows = [
        row for row in existing
        if not (
            ((row.get("source_refs") or {}).get("decision_use_id"))
            or ((row.get("source_refs") or {}).get("surface_event_id"))
        )
    ]
    merged: dict[str, dict[str, Any]] = {}
    for row in manual_rows + derived_rows + derived_surface_rows:
        merged[str(row.get("action_impact_id") or stable_id("ai", row))] = row
    action_rows = list(merged.values())
    forecast_ops_rows = [
        row for row in action_rows
        if (row.get("decision_point") or {}).get("domain") == "forecast_ops"
    ]
    trajectory_surfacing_rows = [
        row for row in action_rows
        if (row.get("decision_point") or {}).get("domain") == "trajectory_surfacing"
    ]
    agentic_workbench_rows = [
        row for row in action_rows
        if (row.get("decision_point") or {}).get("domain") == "agentic_workbench"
    ]
    health = source_health_model(action_rows)
    recommendations = (
        forecast_ops_recommendations(action_rows=action_rows, health=health)
        + trajectory_recommendations(action_rows=action_rows, health=health)
    )
    action_state = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "summary": {
            "action_impact_rows": len(action_rows),
            "forecast_ops_rows": len(forecast_ops_rows),
            "trajectory_surfacing_rows": len(trajectory_surfacing_rows),
            "agentic_workbench_rows": len(agentic_workbench_rows),
            "surfacing_event_rows": len(surfacing_events),
            "consumed_surfacing_events": len(derived_surface_rows),
            "shadow_recommendations": len(recommendations),
            "blocking_source_health_issues": health["counts"]["blocking"],
        },
        "ledger_path": relpath(ACTION_IMPACT_LEDGER),
        "state_paths": {
            "action_intelligence": relpath(ACTION_STATE),
            "shadow_recommendations": relpath(SHADOW_RECOMMENDATIONS),
            "source_health": relpath(SOURCE_HEALTH),
        },
        "recent_action_impact_rows": action_rows[-10:],
    }
    rec_payload = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "recommendations": recommendations,
        "counts": dict(Counter(row.get("domain") for row in recommendations)),
    }
    if write:
        write_jsonl(ACTION_IMPACT_LEDGER, action_rows)
        write_json(ACTION_STATE, action_state)
        write_json(SHADOW_RECOMMENDATIONS, rec_payload)
        write_json(SOURCE_HEALTH, health)
    return {
        "action_intelligence": action_state,
        "shadow_recommendations": rec_payload,
        "source_health": health,
    }


def cmd_materialize(args: argparse.Namespace) -> int:
    payload = materialize_models(write=not args.no_write)
    print(json.dumps({
        "written": not args.no_write,
        "action_intelligence": payload["action_intelligence"]["state_paths"]["action_intelligence"],
        "shadow_recommendations": payload["action_intelligence"]["state_paths"]["shadow_recommendations"],
        "source_health": payload["action_intelligence"]["state_paths"]["source_health"],
        "summary": payload["action_intelligence"]["summary"],
    }, indent=2, sort_keys=True))
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    rows = read_jsonl(ACTION_IMPACT_LEDGER)
    payload = source_health_model(rows)
    if args.write:
        write_json(SOURCE_HEALTH, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_shadow_recommend(args: argparse.Namespace) -> int:
    rows = read_jsonl(ACTION_IMPACT_LEDGER)
    health = source_health_model(rows)
    recs = forecast_ops_recommendations(action_rows=rows, health=health)
    recs += trajectory_recommendations(action_rows=rows, health=health)
    payload = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "recommendations": recs,
    }
    if args.write:
        write_json(SHADOW_RECOMMENDATIONS, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_record_impact(args: argparse.Namespace) -> int:
    payload = read_json(args.from_file, None)
    if not isinstance(payload, dict):
        raise SystemExit("--from-file must point to a JSON object")
    payload.setdefault("schema_version", 1)
    payload.setdefault("action_impact_id", f"ai_{uuid.uuid4().hex[:12]}")
    payload.setdefault("recorded_at", now_iso())
    errors = validate_action_impact(payload)
    if errors:
        raise SystemExit("invalid action-impact row: " + "; ".join(errors))
    rows = read_jsonl(ACTION_IMPACT_LEDGER)
    rows.append(payload)
    write_jsonl(ACTION_IMPACT_LEDGER, rows)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_record_surfacing_event(args: argparse.Namespace) -> int:
    payload = surfacing_event_from_args(args)
    errors = validate_surfacing_event(payload)
    if errors:
        raise SystemExit("invalid surfacing event: " + "; ".join(errors))
    rows = read_jsonl(SURFACING_EVENT_LEDGER)
    if args.dedupe:
        for row in rows:
            if str(row.get("surface_id") or "") == str(payload.get("surface_id") or ""):
                print(json.dumps({"deduped": True, "existing": row}, indent=2, sort_keys=True))
                return 0
    rows.append(payload)
    write_jsonl(SURFACING_EVENT_LEDGER, rows)
    if args.materialize:
        materialize_models(write=True)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_record_agentic_work(args: argparse.Namespace) -> int:
    payload = agentic_workbench_impact_from_args(args)
    errors = payload.get("validation_errors") or []
    if errors:
        raise SystemExit("invalid agentic-work impact row: " + "; ".join(errors))
    rows = read_jsonl(ACTION_IMPACT_LEDGER)
    if args.dedupe:
        for row in rows:
            if str(row.get("action_impact_id") or "") == str(payload.get("action_impact_id") or ""):
                print(json.dumps({"deduped": True, "existing": row}, indent=2, sort_keys=True))
                return 0
    rows.append(payload)
    write_jsonl(ACTION_IMPACT_LEDGER, rows)
    if args.materialize:
        materialize_models(write=True)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_record_agentic_route(args: argparse.Namespace) -> int:
    payload = agentic_workbench_impact_from_route_args(args)
    errors = payload.get("validation_errors") or []
    if errors:
        raise SystemExit("invalid agentic-route impact row: " + "; ".join(errors))
    rows = read_jsonl(ACTION_IMPACT_LEDGER)
    if args.dedupe:
        for row in rows:
            if str(row.get("action_impact_id") or "") == str(payload.get("action_impact_id") or ""):
                print(json.dumps({"deduped": True, "existing": row}, indent=2, sort_keys=True))
                return 0
    rows.append(payload)
    write_jsonl(ACTION_IMPACT_LEDGER, rows)
    if args.materialize:
        materialize_models(write=True)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_smoke(_: argparse.Namespace) -> int:
    fixture = {
        "decision_use_id": "du_fixture",
        "recorded_at": "2026-05-19T18:39:32Z",
        "contract_id": "fixture_contract",
        "tick_id": "fixture_tick",
        "owner": "fixture",
        "decision_stage": "pretick",
        "used_for": "ask_more",
        "decision_changed_bool": True,
        "forecast_delta": "fixture selected ask_more",
        "aggregate_summary": {
            "allocation_recommendation": {
                "action": "ask_another_independent_agent",
                "reason": "fixture thin independence",
                "forecast_spread": 0.3,
            },
            "p_success": 0.42,
            "expected_cost_agent_minutes": 12.0,
            "expected_value": 0.1,
            "top_failure_modes": [{"mode": "fixture_failure", "p": 0.4}],
        },
        "artifact_paths": {},
    }
    row = action_impact_from_decision_use(fixture)
    errors = validate_action_impact(row)
    if errors:
        raise SystemExit("fixture action-impact failed validation: " + "; ".join(errors))
    bad = {**row, "policy_source": "shadow_policy"}
    if not validate_action_impact(bad):
        raise SystemExit("shadow_policy live-row rejection fixture failed")
    bad_override = {**row, "selected_action": "override_forecast", "counterfactual": {"notes": ""}}
    if not validate_action_impact(bad_override):
        raise SystemExit("override-without-reason fixture failed")
    event = {
        "schema_version": 1,
        "surface_id": "sf_fixture",
        "surface_kind": "trajectory_cluster",
        "surface_payload_ref": "analytics/public/ledgers/trajectory/trajectory_archive.jsonl#cluster",
        "project_family": "fixture_family",
        "target_decision_id": "fixture_decision",
        "shown_at": "2026-05-19T18:39:32Z",
        "rank": 1,
        "consumed_bool": True,
        "consumed_at": "2026-05-19T18:49:32Z",
        "consumed_by_tick": "fixture_tick",
        "suppressed_reason": None,
        "negative_externality_tags": [],
        "selected_action": "surface_trajectory_cluster",
        "policy_source": "trajectory_miner",
        "decision_impact": "changed_next_probe",
        "yield_signal": "positive",
        "outcome_known": True,
        "notes": "fixture consumed trajectory cluster",
    }
    if validate_surfacing_event(event):
        raise SystemExit("valid surfacing event fixture failed validation")
    surface_row = surfacing_event_to_action_impact(event)
    if not surface_row or (surface_row.get("decision_point") or {}).get("domain") != "trajectory_surfacing":
        raise SystemExit("surfacing event to action-impact fixture failed")
    class _Args:
        action_impact_id = None
        recorded_at = "2026-05-19T18:59:32Z"
        decision_id = "fixture_agentic_decision"
        tick_id = "fixture_tick"
        project_id = "fixture_project"
        stage = "pretick"
        selected_action = "run_out_of_loop_agent"
        policy_source = "rd"
        selection_rule = "rd_workbench_router"
        why_selected = "fixture checks manual out-of-loop path"
        forecast_contract_id = "fixture_contract"
        gp233_evidence_ref = None
        source_refs_json = '["analytics/public/queries/rd/autoresearch_routes/fixture.json"]'
        catch_ids_json = "[]"
        prediction_ids_json = "[]"
        negative_externality_tags_json = "[]"
        task = "fixture bounded task"
        project_family = "fixture_family"
        workbench_router_decision = "prepare_autoresearch_surface"
        why_not_autoresearch = "missing stable evaluator fixture"
        bounded_claim = True
        stable_evaluator = False
        rubric_ready = True
        artifact_surface = True
        worker_archetype = "persistent_agent"
        worker_capability = "tool_using_agent"
        worker_state = "stateful"
        worker_identity = "persistent"
        transport = "subscription_cli"
        outcome_known = True
        success_bool = False
        decision_impact = "prepared_autoresearch_surface"
        yield_signal = "negative_constraint"
        actual_cost_agent_minutes = 7.0
        baseline_action = "invoke_autoresearch"
        counterfactual_action = "run_out_of_loop_agent"
        counterfactual_value_bucket = "diagnostic"
        notes = "fixture"

    agentic_row = agentic_workbench_impact_from_args(_Args())
    if validate_agentic_workbench_impact(agentic_row):
        raise SystemExit("valid agentic workbench fixture failed validation")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "state.json"
        write_json(tmp, {"ok": True})
        assert read_json(tmp, {})["ok"] is True
    print(json.dumps({
        "ok": True,
        "checked": [
            "decision_use_to_action_impact",
            "shadow_policy_live_row_rejection",
            "override_without_reason_rejection",
            "surfacing_event_to_action_impact",
            "agentic_workbench_action_impact",
            "json_io",
        ],
    }, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("materialize")
    p.add_argument("--no-write", action="store_true")
    p.set_defaults(func=cmd_materialize)

    p = sub.add_parser("record-impact")
    p.add_argument("--from-file", type=Path, required=True)
    p.set_defaults(func=cmd_record_impact)

    p = sub.add_parser("record-surfacing-event")
    p.add_argument("--surface-id")
    p.add_argument(
        "--surface-kind",
        choices=sorted(SURFACE_KIND_TO_ACTION),
        required=True,
    )
    p.add_argument("--surface-payload-ref", required=True)
    p.add_argument("--project-family", required=True)
    p.add_argument("--target-decision-id")
    p.add_argument("--shown-at")
    p.add_argument("--rank", type=int, default=1)
    p.add_argument("--consumed-bool", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--consumed-at")
    p.add_argument("--consumed-by-tick")
    p.add_argument("--selected-action", choices=SURFACING_ACTIONS)
    p.add_argument(
        "--policy-source",
        choices=["rd", "trajectory_miner", "manual", "unknown"],
        default="trajectory_miner",
    )
    p.add_argument("--suppressed-reason")
    p.add_argument("--negative-externality-tags-json", default="[]")
    p.add_argument("--outcome-known", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--yield-signal")
    p.add_argument("--decision-impact")
    p.add_argument("--notes")
    p.add_argument("--dedupe", action="store_true")
    p.add_argument("--materialize", action="store_true")
    p.set_defaults(func=cmd_record_surfacing_event)

    p = sub.add_parser("record-agentic-work")
    p.add_argument("--action-impact-id")
    p.add_argument("--recorded-at")
    p.add_argument("--decision-id", required=True)
    p.add_argument("--tick-id")
    p.add_argument("--project-id")
    p.add_argument("--project-family", required=True)
    p.add_argument("--stage", default="pretick")
    p.add_argument("--task", required=True)
    p.add_argument("--selected-action", choices=AGENTIC_WORKBENCH_ACTIONS, required=True)
    p.add_argument(
        "--policy-source",
        choices=["rd", "manual", "forecast_market", "unknown"],
        default="rd",
    )
    p.add_argument("--selection-rule", default="rd_workbench_router")
    p.add_argument("--why-selected")
    p.add_argument(
        "--workbench-router-decision",
        choices=["invoke_autoresearch", "prepare_autoresearch_surface", "stay_out_of_loop", "not_evaluated"],
        default="not_evaluated",
    )
    p.add_argument("--why-not-autoresearch")
    p.add_argument("--bounded-claim", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--stable-evaluator", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--rubric-ready", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--artifact-surface", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--worker-archetype", default="persistent_agent")
    p.add_argument("--worker-capability", default="tool_using_agent")
    p.add_argument("--worker-state", default="stateful")
    p.add_argument("--worker-identity", default="persistent")
    p.add_argument("--transport", default="subscription_cli")
    p.add_argument("--forecast-contract-id")
    p.add_argument("--gp233-evidence-ref")
    p.add_argument(
        "--route-json-ref",
        help=(
            "Path or ref to the saved autoresearch router JSON. "
            "Required for a valid agentic_workbench row; prefer "
            "`ztare autoresearch route --record-decision-id` when possible."
        ),
    )
    p.add_argument("--source-refs-json", default="[]")
    p.add_argument("--prediction-ids-json", default="[]")
    p.add_argument("--catch-ids-json", default="[]")
    p.add_argument("--outcome-known", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--success-bool", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--decision-impact")
    p.add_argument("--yield-signal")
    p.add_argument("--actual-cost-agent-minutes", type=float)
    p.add_argument("--negative-externality-tags-json", default="[]")
    p.add_argument("--baseline-action")
    p.add_argument("--counterfactual-action")
    p.add_argument("--counterfactual-value-bucket")
    p.add_argument("--notes")
    p.add_argument("--dedupe", action="store_true")
    p.add_argument("--materialize", action="store_true")
    p.set_defaults(func=cmd_record_agentic_work)

    p = sub.add_parser("record-agentic-route")
    p.add_argument("--route-json", type=Path, required=True)
    p.add_argument("--action-impact-id")
    p.add_argument("--recorded-at")
    p.add_argument("--decision-id", required=True)
    p.add_argument("--tick-id")
    p.add_argument("--project-id")
    p.add_argument("--project-family")
    p.add_argument("--stage", default="pretick")
    p.add_argument("--task")
    p.add_argument("--selected-action", choices=AGENTIC_WORKBENCH_ACTIONS)
    p.add_argument(
        "--policy-source",
        choices=["rd", "manual", "forecast_market", "unknown"],
        default="rd",
    )
    p.add_argument("--selection-rule", default="rd_workbench_router")
    p.add_argument("--why-selected")
    p.add_argument("--why-not-autoresearch")
    p.add_argument("--worker-archetype")
    p.add_argument("--worker-capability")
    p.add_argument("--worker-state")
    p.add_argument("--worker-identity")
    p.add_argument("--transport")
    p.add_argument("--forecast-contract-id")
    p.add_argument("--gp233-evidence-ref")
    p.add_argument("--source-refs-json", default="[]")
    p.add_argument("--prediction-ids-json", default="[]")
    p.add_argument("--catch-ids-json", default="[]")
    p.add_argument("--outcome-known", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--success-bool", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--decision-impact")
    p.add_argument("--yield-signal")
    p.add_argument("--actual-cost-agent-minutes", type=float)
    p.add_argument("--negative-externality-tags-json", default="[]")
    p.add_argument("--baseline-action")
    p.add_argument("--counterfactual-action")
    p.add_argument("--counterfactual-value-bucket")
    p.add_argument("--notes")
    p.add_argument("--dedupe", action="store_true")
    p.add_argument("--materialize", action="store_true")
    p.set_defaults(func=cmd_record_agentic_route)

    p = sub.add_parser("shadow-recommend")
    p.add_argument("--write", action="store_true")
    p.set_defaults(func=cmd_shadow_recommend)

    p = sub.add_parser("health")
    p.add_argument("--write", action="store_true")
    p.add_argument("--json", action="store_true", help="Accepted for command-surface consistency; output is always JSON.")
    p.set_defaults(func=cmd_health)

    p = sub.add_parser("smoke")
    p.set_defaults(func=cmd_smoke)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
