"""Read-only runtime status for strategy-control subscription research."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.leanmill import work_queue

from .research_agent import STRATEGY_COHORT_JOB_KIND, research_agent_status
from .strategy_control_research import STRATEGY_CONTROL_RESEARCH_REQUEST_SCHEMA


STRATEGY_CONTROL_STATUS_SCHEMA = "jaggedthoughts-strategy-control-runtime-status-v1"
_CLASSIFICATIONS = {
    "phenotype_adoption_found", "family_adoption_only",
    "no_family_adoption_found", "insufficient_source_coverage",
}


def _typed_result(
    row: Mapping[str, Any], result: Mapping[str, Any] | None,
) -> str | None:
    payload = row.get("payload") or {}
    if row.get("status") != "done" or payload.get("stage") != "classified" or not result:
        return None
    body = dict(result)
    declared = str(body.pop("result_sha256", ""))
    classification = str(result.get("classification") or "")
    if (
        declared != stable_sha256(body)
        or declared != payload.get("result_sha256")
        or result.get("request_sha256") != payload.get("request_sha256")
        or classification not in _CLASSIFICATIONS
    ):
        return None
    return classification


def _runtime_state(
    row: Mapping[str, Any], classification: str | None,
    last_event: Mapping[str, Any] | None, service: Mapping[str, Any],
) -> str:
    payload = row.get("payload") or {}
    status = str(row.get("status") or "unknown")
    if classification == "insufficient_source_coverage":
        return "terminal_source_gap"
    if classification:
        return "typed_completion"
    if status in {"claimed", "running"}:
        return "dispatching" if (
            service.get("last_work_id") == row.get("work_id")
            and str(service.get("status") or "").startswith("dispatching")
        ) else "leased"
    if status == "queued" and (
        payload.get("stage") == "retry_queued"
        or (last_event or {}).get("event_type") == "investment_subscription_research_retry_queued"
    ):
        return "retry"
    if status == "queued":
        return "queued"
    if status in {"dead_letter", "failed", "retired"}:
        return "terminal_source_gap" if "source" in str(payload.get("error") or "").lower() else "terminal_failure"
    return "unknown"


def _consequence(state: str, classification: str | None, adapter: Mapping[str, Any]) -> str:
    if classification == "no_family_adoption_found":
        return (
            "control_candidate_ready_for_frontier_recompile"
            if (adapter.get("information_yield") or {}).get("immediate_control_admission_if_negative")
            else "control_candidate_waiting_outcome_history"
        )
    if classification == "family_adoption_only":
        return "control_excluded_related_family_adoption"
    if classification == "phenotype_adoption_found":
        return "control_excluded_exact_phenotype_adoption"
    if state == "terminal_source_gap":
        return "control_unresolved_source_gap"
    if state == "terminal_failure":
        return "control_unresolved_runtime_failure"
    return "control_pending_classification"


def compile_strategy_control_runtime_status(
    queue_rows: Iterable[Mapping[str, Any]], adapters: Iterable[Mapping[str, Any]],
    frontier: Mapping[str, Any], service_status: Mapping[str, Any], *,
    results: Mapping[str, Mapping[str, Any]] | None = None,
    events: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Join queue, event, result, service, and frontier state without mutation."""
    adapter_by_cohort = {
        str(row["cohort_request_sha256"]): dict(row)
        for row in adapters if row.get("schema") == STRATEGY_CONTROL_RESEARCH_REQUEST_SCHEMA
        and row.get("control_frontier_sha256") == frontier.get("control_frontier_sha256")
    }
    last_events: dict[str, dict[str, Any]] = {}
    for event in events:
        payload = event.get("payload") or {}
        work_id = str(payload.get("work_id") or event.get("work_id") or "")
        if work_id and work_id in {
            f"investment-strategy-cohort:{sha[:24]}" for sha in adapter_by_cohort
        }:
            prior = last_events.get(work_id)
            if prior is None or int(event.get("timestamp") or 0) >= int(prior.get("timestamp") or 0):
                last_events[work_id] = dict(event)
    frontier_rows = {
        str(row["request_sha256"]): dict(row)
        for row in frontier.get("peer_eligibility") or ()
    }
    rows_by_request: dict[str, list[dict[str, Any]]] = {}
    for row in queue_rows:
        if row.get("kind") == STRATEGY_COHORT_JOB_KIND:
            request_sha = str((row.get("payload") or {}).get("request_sha256") or "")
            rows_by_request.setdefault(request_sha, []).append(dict(row))
    budget = dict(service_status.get("daily_dispatch_budget") or {})
    budget_exhausted = bool(budget.get("exhausted"))
    service = dict(service_status.get("service") or {})
    jobs = []
    for cohort_sha, adapter in adapter_by_cohort.items():
        matches = [
            row for row in rows_by_request.get(cohort_sha, ())
            if (row.get("payload") or {}).get("control_admission_request_sha256")
            == adapter.get("request_sha256")
        ]
        if not matches:
            raise ValueError("strategy control adapter has no subscription queue job")
        row = max(matches, key=lambda value: (
            value.get("status") in {"queued", "claimed", "running"},
            int(value.get("updated_at") or 0), str(value.get("work_id") or ""),
        ))
        payload = row.get("payload") or {}
        work_id = str(row["work_id"])
        result = (results or {}).get(cohort_sha)
        classification = _typed_result(row, result)
        state = _runtime_state(
            row, classification, last_events.get(work_id), service,
        )
        frontier_row = frontier_rows.get(cohort_sha, {})
        if state in {"queued", "retry"}:
            next_transition = (
                "service_poll_rechecks_exhausted_daily_budget"
                if budget_exhausted else "subscription_worker_claims_eligible_job"
            )
        elif state == "leased":
            next_transition = "subscription_runtime_enters_dispatch"
        elif state == "dispatching":
            next_transition = "typed_result_validation_or_retry"
        elif state == "typed_completion":
            next_transition = "institutional_learning_recompiles_control_frontier"
        elif state == "terminal_source_gap":
            next_transition = "institutional_learning_records_source_gap_exclusion"
        else:
            next_transition = "operator_or_retry_policy_required"
        jobs.append({
            "work_id": work_id,
            "peer_entity_id": adapter["peer_entity_id"],
            "cohort_request_sha256": cohort_sha,
            "control_admission_request_sha256": adapter["request_sha256"],
            "priority": int(row.get("priority") or 0),
            "queue_status": row.get("status"),
            "attempts": int(row.get("attempts") or 0),
            "max_attempts": int(row.get("max_attempts") or 0),
            "lease": {
                "claimed_by": row.get("claimed_by"),
                "lease_until": row.get("lease_until"),
            },
            "runtime_state": state,
            "classification": classification,
            "last_event_type": (last_events.get(work_id) or {}).get("event_type"),
            "control_frontier": {
                "frontier_sha256": adapter["control_frontier_sha256"],
                "current_stage": frontier_row.get("frontier_stage"),
                "currently_admissible": bool(frontier_row.get("admissible_control")),
                "consequence": _consequence(state, classification, adapter),
            },
            "next_automatic_transition": next_transition,
            "capital_authority": False,
        })
    jobs.sort(key=lambda row: (-row["priority"], row["peer_entity_id"]))
    counts = Counter(row["runtime_state"] for row in jobs)
    claimable = [row for row in jobs if row["runtime_state"] in {"queued", "retry"}]
    highest_priority = max((row["priority"] for row in claimable), default=None)
    claim_frontier = [
        row["work_id"] for row in claimable if row["priority"] == highest_priority
    ]
    next_epoch = None
    checked_at = str(service.get("checked_at") or "")
    if budget_exhausted and checked_at:
        checked = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
        next_epoch = (checked.astimezone(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0,
        ) + timedelta(days=1)).isoformat(timespec="seconds").replace("+00:00", "Z")
    body = {
        "schema": STRATEGY_CONTROL_STATUS_SCHEMA,
        "control_frontier_sha256": frontier.get("control_frontier_sha256"),
        "job_count": len(jobs),
        "runtime_state_counts": dict(sorted(counts.items())),
        "jobs": jobs,
        "service": {
            "enabled": service_status.get("enabled"),
            "status": service.get("status"),
            "last_action": service.get("last_action"),
            "checked_at": service.get("checked_at"),
            "poll_seconds": service.get("poll_seconds"),
            "daily_dispatch_budget": budget,
        },
        "automatic_transition": {
            "next": (
                "service_poll_budget_check_no_queue_change"
                if budget_exhausted else "highest_priority_eligible_job_queued_to_claimed"
            ),
            "claim_frontier_work_ids": claim_frontier,
            "claim_not_before": next_epoch,
            "after_budget_reset": (
                "highest_priority_eligible_job_queued_to_claimed" if budget_exhausted else None
            ),
        },
        "capital_authority": False,
    }
    return {**body, "status_sha256": stable_sha256(body)}


def compile_workspace_strategy_control_runtime_status(workspace: str | Path) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    frontier = json.loads((
        root / "institutional_learning" / "strategy_cohorts" / "control-eligibility-frontier.json"
    ).read_text(encoding="utf-8"))
    adapters = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / "research_jobs" / "strategy_controls" / "requests").glob("*.json"))
    ]
    connection = work_queue.connect(str(root / "state" / "research_jobs.sqlite3"))
    try:
        rows = work_queue.list_items(connection, limit=10_000)
    finally:
        connection.close()
    results = {}
    for path in sorted((root / "institutional_learning" / "strategy_cohorts" / "results").glob("*.json")):
        result = json.loads(path.read_text(encoding="utf-8"))
        results[str(result.get("request_sha256") or "")] = result
    events = []
    event_path = root / "research_jobs" / "agent" / "events.jsonl"
    if event_path.exists():
        for line in event_path.read_text(encoding="utf-8").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, Mapping):
                events.append(event)
    return compile_strategy_control_runtime_status(
        rows, adapters, frontier, research_agent_status(root),
        results=results, events=events,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace")
    args = parser.parse_args(argv)
    print(json.dumps(
        compile_workspace_strategy_control_runtime_status(args.workspace),
        indent=2, sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "STRATEGY_CONTROL_STATUS_SCHEMA",
    "compile_strategy_control_runtime_status",
    "compile_workspace_strategy_control_runtime_status",
]
