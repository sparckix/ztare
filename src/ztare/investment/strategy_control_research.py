"""Bind pending strategy-control searches to the subscription research queue."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.leanmill import work_queue

from .research_agent import STRATEGY_COHORT_JOB_KIND, STRATEGY_COHORT_JOB_SCHEMA
from .strategy_control_eligibility import STRATEGY_CONTROL_ELIGIBILITY_FRONTIER_SCHEMA
from .strategy_learning import STRATEGY_COHORT_PLAN_SCHEMA


STRATEGY_CONTROL_RESEARCH_REQUEST_SCHEMA = (
    "jaggedthoughts-strategy-control-research-request-v1"
)


def _checked_hash(row: Mapping[str, Any], field: str, label: str) -> str:
    body = dict(row)
    declared = str(body.pop(field, ""))
    if declared != stable_sha256(body):
        raise ValueError(f"{label} content hash mismatch")
    return declared


def compile_strategy_control_research_requests(
    frontier: Mapping[str, Any], plan: Mapping[str, Any],
    readiness: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Adapt pending cohort requests without duplicating their research identity."""
    if frontier.get("schema") != STRATEGY_CONTROL_ELIGIBILITY_FRONTIER_SCHEMA:
        raise ValueError("control research requires a control-eligibility frontier")
    if plan.get("schema") != STRATEGY_COHORT_PLAN_SCHEMA:
        raise ValueError("control research requires a strategy cohort plan")
    frontier_sha = _checked_hash(frontier, "control_frontier_sha256", "control frontier")
    plan_sha = _checked_hash(plan, "plan_sha256", "strategy cohort plan")
    if frontier.get("plan_sha256") != plan_sha:
        raise ValueError("control frontier and cohort plan differ")
    requests = {str(row["request_sha256"]): dict(row) for row in plan.get("requests") or ()}
    evidence = {
        str(row["request_sha256"]): dict(row)
        for row in frontier.get("next_source_requests") or ()
    }
    pending = {
        str(row["request_sha256"]): dict(row)
        for row in frontier.get("peer_eligibility") or ()
        if row.get("classification") == "pending"
    }
    history = {
        str(row["entity_id"]).upper(): dict(row)
        for row in readiness.get("history_status") or () if row.get("entity_id")
    }
    compiled = []
    for request_sha, eligibility in sorted(pending.items()):
        request = requests.get(request_sha)
        source_request = evidence.get(request_sha)
        if not request or not source_request:
            raise ValueError("pending control peer lacks its cohort or evidence request")
        _checked_hash(request, "request_sha256", "strategy cohort request")
        entity = str(request["peer_entity_id"]).upper()
        status = history.get(entity, {})
        periods = int(status.get("period_count") or 0)
        immediate = periods >= int(frontier["outcome_contract"]["minimum_pre_periods"])
        priority = 920_000 + min(periods, 99) * 100 if immediate else 900_000
        body = {
            "schema": STRATEGY_CONTROL_RESEARCH_REQUEST_SCHEMA,
            "request_id": f"strategy-control:{frontier_sha[:16]}:{request_sha[:16]}",
            "created_at": frontier["as_of"],
            "control_frontier_sha256": frontier_sha,
            "cohort_plan_sha256": plan_sha,
            "cohort_request_sha256": request_sha,
            "law_id": request["law_id"],
            "peer_entity_id": entity,
            "move_family": {
                "mechanism_signature_sha256": request["mechanism_signature_sha256"],
                "mechanism_signature": request["mechanism_signature"],
            },
            "move_phenotype": {
                "mechanism_phenotype_sha256": request["mechanism_phenotype_sha256"],
                "mechanism_phenotype": request["mechanism_phenotype"],
                "focal_move_sha256s": sorted(
                    str(row["move_sha256"]) for row in request["focal_moves"]
                ),
            },
            "environment": eligibility["environment"],
            "adoption_search_window": {
                "start_at": request["search_start_at"],
                "end_at": request["search_end_at"],
            },
            "treatment_periods": list(frontier["treatment_periods"]),
            "outcome_contract": dict(frontier["outcome_contract"]),
            "evidence_contract": {
                "required_source_classes": list(source_request["required_source_classes"]),
                "required_evidence": list(source_request["required_evidence"]),
                "control_success_classification": "no_family_adoption_found",
                "control_kill_classifications": [
                    "family_adoption_only", "phenotype_adoption_found",
                ],
                "research_block_classification": "insufficient_source_coverage",
            },
            "information_yield": {
                "history_status": status.get("status") or "unknown",
                "period_count": periods,
                "immediate_control_admission_if_negative": immediate,
                "priority": priority,
                "priority_basis": (
                    "negative_classification_can_enter_control_admission_now"
                    if immediate else "negative_classification_still_requires_outcome_history"
                ),
            },
            "required_capability": "subscription_web_research",
            "expected_exit": "typed_adoption_relation_or_source_gap",
            "capital_authority": False,
        }
        compiled.append({**body, "request_sha256": stable_sha256(body)})
    return sorted(
        compiled,
        key=lambda row: (
            -int(row["information_yield"]["priority"]), row["peer_entity_id"],
        ),
    )


def validate_strategy_control_research_request(
    adapter: Mapping[str, Any], cohort_request: Mapping[str, Any], *,
    expected_request_sha256: str, expected_frontier_sha256: str,
) -> dict[str, Any]:
    """Validate a queue-bound control adapter against its cohort identity."""
    if adapter.get("schema") != STRATEGY_CONTROL_RESEARCH_REQUEST_SCHEMA:
        raise ValueError("strategy cohort job has an unsupported control adapter")
    _checked_hash(adapter, "request_sha256", "strategy control research request")
    expected = {
        "cohort_request_sha256": cohort_request["request_sha256"],
        "peer_entity_id": cohort_request["peer_entity_id"],
        "law_id": cohort_request["law_id"],
        "control_frontier_sha256": expected_frontier_sha256,
    }
    if adapter.get("request_sha256") != expected_request_sha256 or any(
        adapter.get(field) != value for field, value in expected.items()
    ):
        raise ValueError("strategy control adapter crossed its queue or cohort identity")
    if adapter.get("adoption_search_window") != {
        "start_at": cohort_request["search_start_at"],
        "end_at": cohort_request["search_end_at"],
    }:
        raise ValueError("strategy control adapter changed the cohort search window")
    if (
        (adapter.get("move_family") or {}).get("mechanism_signature_sha256")
        != cohort_request["mechanism_signature_sha256"]
        or (adapter.get("move_phenotype") or {}).get("mechanism_phenotype_sha256")
        != cohort_request["mechanism_phenotype_sha256"]
    ):
        raise ValueError("strategy control adapter changed the move identity")
    return dict(adapter)


def bind_workspace_strategy_control_research(workspace: str | Path) -> dict[str, Any]:
    """Materialize adapters and bind or create their existing cohort queue jobs."""
    root = Path(workspace).expanduser().resolve()
    cohort = root / "institutional_learning" / "strategy_cohorts"
    frontier = json.loads((cohort / "control-eligibility-frontier.json").read_text())
    plan = json.loads((cohort / "latest.json").read_text())
    readiness = json.loads((cohort / "panel-readiness.json").read_text())
    adapters = compile_strategy_control_research_requests(frontier, plan, readiness)
    cohort_by_sha = {str(row["request_sha256"]): row for row in plan["requests"]}
    destination = root / "research_jobs" / "strategy_controls" / "requests"
    db_path = root / "state" / "research_jobs.sqlite3"
    connection = work_queue.connect(str(db_path))
    existing_rows = work_queue.list_items(connection, limit=10_000)
    existing = {str(row["work_id"]): row for row in existing_rows}
    active_by_request = {
        str((row.get("payload") or {}).get("request_sha256")): row
        for row in existing_rows
        if row.get("kind") == STRATEGY_COHORT_JOB_KIND
        and row.get("status") in {"queued", "claimed"}
        and (row.get("payload") or {}).get("request_sha256")
    }
    newly_enqueued, existing_bound, already_bound, deferred_binding = [], [], [], []
    try:
        for adapter in adapters:
            adapter_sha = str(adapter["request_sha256"])
            adapter_path = destination / f"{adapter_sha}.json"
            payload_text = json.dumps(adapter, indent=2, sort_keys=True) + "\n"
            if adapter_path.exists() and adapter_path.read_text(encoding="utf-8") != payload_text:
                raise ValueError("immutable strategy-control request artifact changed")
            if not adapter_path.exists():
                adapter_path.parent.mkdir(parents=True, exist_ok=True)
                adapter_path.write_text(payload_text, encoding="utf-8")
            cohort_sha = str(adapter["cohort_request_sha256"])
            cohort_request = cohort_by_sha[cohort_sha]
            cohort_path = root / "research_jobs" / "strategy_cohorts" / "requests" / f"{cohort_sha}.json"
            base_work_id = f"investment-strategy-cohort:{cohort_sha[:24]}"
            prior = active_by_request.get(cohort_sha) or existing.get(base_work_id)
            work_id = str(prior["work_id"]) if prior else base_work_id
            binding = {
                "control_admission_request_sha256": adapter_sha,
                "control_admission_request_path": adapter_path.relative_to(root).as_posix(),
                "control_frontier_sha256": adapter["control_frontier_sha256"],
                "information_yield_priority": adapter["information_yield"]["priority"],
            }
            if prior:
                prior_payload = dict(prior.get("payload") or {})
                if all(prior_payload.get(key) == value for key, value in binding.items()):
                    already_bound.append(work_id)
                    continue
                if prior.get("kind") != STRATEGY_COHORT_JOB_KIND:
                    raise ValueError("control research cannot cross an existing job kind")
                if prior.get("status") != "queued":
                    deferred_binding.append(work_id)
                    continue
                body = {**prior_payload, **binding}
                body.pop("job_sha256", None)
                payload = {**body, "job_sha256": stable_sha256(body)}
                cursor = connection.execute(
                    "UPDATE work_items SET priority=?, payload_json=?, updated_at=? "
                    "WHERE work_id=? AND kind=? AND status='queued'",
                    (
                        int(adapter["information_yield"]["priority"]),
                        json.dumps(payload, sort_keys=True, separators=(",", ":")),
                        int(time.time()), work_id, STRATEGY_COHORT_JOB_KIND,
                    ),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("queued strategy cohort job changed during binding")
                connection.commit()
                existing_bound.append(work_id)
                continue
            body = {
                "schema": STRATEGY_COHORT_JOB_SCHEMA,
                "work_id": work_id,
                "request_id": cohort_request["request_id"],
                "request_sha256": cohort_sha,
                "request_path": cohort_path.relative_to(root).as_posix(),
                "entity_id": adapter["peer_entity_id"],
                "stage": "queued",
                "required_capability": "subscription_web_research",
                "expected_exit": "typed_equivalent_adoption_classification_or_source_gap",
                **binding,
                "capital_authority": False,
            }
            job = {**body, "job_sha256": stable_sha256(body)}
            work_queue.enqueue(
                connection, kind=STRATEGY_COHORT_JOB_KIND,
                priority=int(adapter["information_yield"]["priority"]), payload=job,
            )
            newly_enqueued.append(work_id)
    finally:
        connection.close()
    body = {
        "schema": "jaggedthoughts-strategy-control-research-binding-v1",
        "control_frontier_sha256": frontier["control_frontier_sha256"],
        "request_count": len(adapters),
        "newly_enqueued_count": len(newly_enqueued),
        "existing_bound_count": len(existing_bound),
        "already_bound_count": len(already_bound),
        "deferred_binding_count": len(deferred_binding),
        "newly_enqueued_work_ids": newly_enqueued,
        "existing_bound_work_ids": existing_bound,
        "already_bound_work_ids": already_bound,
        "deferred_binding_work_ids": deferred_binding,
        "priority_order": [row["peer_entity_id"] for row in adapters],
        "capital_authority": False,
    }
    receipt = {**body, "binding_sha256": stable_sha256(body)}
    receipt_path = root / "research_jobs" / "strategy_controls" / "latest.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace")
    args = parser.parse_args(argv)
    print(json.dumps(bind_workspace_strategy_control_research(args.workspace), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "STRATEGY_CONTROL_RESEARCH_REQUEST_SCHEMA",
    "bind_workspace_strategy_control_research",
    "compile_strategy_control_research_requests",
    "validate_strategy_control_research_request",
]
