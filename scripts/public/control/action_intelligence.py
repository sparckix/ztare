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
RECURSIVE_GAIN = REPO / "analytics/public/queries/trajectory/recursive_gain_candidates.json"
CLOSURE_PATTERNS = REPO / "analytics/public/queries/reflexive/closure_patterns.json"

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
    "suppress_surface_as_low_voi",
    "repair_source_emitter",
]
SURFACE_KIND_TO_ACTION = {
    "pattern": "surface_pattern",
    "anti_pattern": "surface_anti_pattern",
    "trajectory_cluster": "surface_trajectory_cluster",
    "gp233_next_lever": "surface_gp233_next_lever",
    "catch_preconditioner": "surface_catch_preconditioner",
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
            "gp233_evidence_ref": row.get("surface_payload_ref") if row.get("surface_kind") == "gp233_next_lever" else None,
            "catch_ids": [row.get("surface_payload_ref")] if row.get("surface_kind") == "catch_preconditioner" else [],
            "trajectory_refs": [row.get("surface_payload_ref")] if row.get("surface_kind") in {"trajectory_cluster", "pattern", "anti_pattern"} else [],
            "prediction_ids": [],
        },
        "context_features": {
            "p_success": None,
            "expected_cost_agent_minutes": None,
            "forecast_spread": None,
            "top_failure_mode": None,
            "current_bottleneck": None,
            "next_lever": None,
            "surface_kind": row.get("surface_kind"),
            "surface_rank": row.get("rank"),
            "project_family": row.get("project_family"),
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
        payload["issue_id"] = stable_id("sh", payload)
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
    if not surfacing_rows:
        add_issue(
            severity="warning",
            scope="trajectory_surfacing",
            issue_type="unconsumed_surface",
            expected_count=1,
            observed_count=len(consumed_surfacing_events),
            denominator="surfacing consumption action-impact rows",
            blocking_rule="trajectory/primitives surfacing recommendations are diagnostic until consumption is recorded",
            evidence_refs=[relpath(SURFACING_EVENT_LEDGER), relpath(ACTION_IMPACT_LEDGER)],
            affected_domains=["trajectory_surfacing"],
        )

    load_bearing_catches = [
        row for row in read_jsonl(CATCH_LEDGER)
        if row.get("load_bearing") is True
    ]
    if load_bearing_catches and not action_rows:
        add_issue(
            severity="warning",
            scope="catch",
            issue_type="unconsumed_surface",
            expected_count=len(load_bearing_catches),
            observed_count=0,
            denominator="load-bearing catch rows linked to action-impact rows",
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
        },
        "counts": {
            "issues": len(issues),
            "blocking": counts.get("blocking", 0),
            "warning": counts.get("warning", 0),
            "info": counts.get("info", 0),
            "aggregates": aggregate_count,
            "decision_use_rows": len(decision_rows),
            "action_impact_rows": len(action_rows),
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
    payload["recommendation_id"] = stable_id("sr", payload)
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
        rec["recommendation_id"] = stable_id("sr", rec)
        rows.append(rec)
        if len(rows) >= limit:
            break
    return rows


def trajectory_rows(limit: int = 500) -> list[dict[str, Any]]:
    path = TRAJECTORY_ARCHIVE_ENRICHED if TRAJECTORY_ARCHIVE_ENRICHED.exists() else TRAJECTORY_ARCHIVE
    rows = read_jsonl(path)
    return rows[-limit:] if limit and len(rows) > limit else rows


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
        rec["recommendation_id"] = stable_id("sr", rec)
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
        rec["recommendation_id"] = stable_id("sr", rec)
        rows.append(rec)

    catches = [
        row for row in read_jsonl(CATCH_LEDGER)
        if row.get("load_bearing") is True
    ][-5:]
    for catch in catches:
        rec = {
            "schema_version": 1,
            "generated_at": now_iso(),
            "domain": "trajectory_surfacing",
            "decision_id": str(catch.get("catch_id") or stable_id("catch", catch)),
            "recommended_action": "surface_catch_preconditioner",
            "confidence": "diagnostic_only",
            "rationale": str(catch.get("title") or "load-bearing catch preconditioner available"),
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
        rec["recommendation_id"] = stable_id("sr", rec)
        rows.append(rec)

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
            "forecast_ops_rows": len([
                row for row in action_rows
                if (row.get("decision_point") or {}).get("domain") == "forecast_ops"
            ]),
            "trajectory_surfacing_rows": len([
                row for row in action_rows
                if (row.get("decision_point") or {}).get("domain") == "trajectory_surfacing"
            ]),
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

    p = sub.add_parser("shadow-recommend")
    p.add_argument("--write", action="store_true")
    p.set_defaults(func=cmd_shadow_recommend)

    p = sub.add_parser("health")
    p.add_argument("--write", action="store_true")
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
