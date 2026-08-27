from ztare.common.equivariance import stable_sha256
from ztare.investment.research_agent import STRATEGY_COHORT_JOB_KIND
from ztare.investment.strategy_control_research import (
    STRATEGY_CONTROL_RESEARCH_REQUEST_SCHEMA,
)
from ztare.investment.strategy_control_status import (
    compile_strategy_control_runtime_status,
)


def test_control_runtime_projection_distinguishes_transition_states_and_consequences():
    states = [
        ("queued", "queued", None),
        ("leased", "claimed", None),
        ("dispatching", "running", None),
        ("retry", "queued", None),
        ("completed", "done", "no_family_adoption_found"),
        ("gap", "done", "insufficient_source_coverage"),
    ]
    adapters, queue, results, peers = [], [], {}, []
    for index, (entity, status, classification) in enumerate(states):
        cohort_sha = f"{index + 1:x}" * 64
        adapter_body = {
            "schema": STRATEGY_CONTROL_RESEARCH_REQUEST_SCHEMA,
            "cohort_request_sha256": cohort_sha, "peer_entity_id": entity.upper(),
            "control_frontier_sha256": "f" * 64,
            "information_yield": {"immediate_control_admission_if_negative": True},
        }
        adapter = {**adapter_body, "request_sha256": stable_sha256(adapter_body)}
        adapters.append(adapter)
        result = None
        payload = {
            "request_sha256": cohort_sha,
            "control_admission_request_sha256": adapter["request_sha256"],
            "stage": "retry_queued" if entity == "retry" else "dispatching" if entity == "dispatching" else "queued",
        }
        if classification:
            result_body = {"request_sha256": cohort_sha, "classification": classification}
            result = {**result_body, "result_sha256": stable_sha256(result_body)}
            results[cohort_sha] = result
            payload.update({
                "stage": "classified", "result_sha256": result["result_sha256"],
            })
        queue.append({
            "kind": STRATEGY_COHORT_JOB_KIND,
            "work_id": f"investment-strategy-cohort:{cohort_sha[:24]}",
            "status": status, "priority": 100 - index,
            "attempts": 1 if entity == "retry" else 0, "max_attempts": 3,
            "claimed_by": "worker" if status in {"claimed", "running"} else None,
            "lease_until": 999 if status in {"claimed", "running"} else None,
            "payload": payload,
        })
        if index == 0:
            queue.append({
                **queue[-1], "work_id": f"stale:{cohort_sha[:24]}", "status": "done",
                "payload": {"request_sha256": cohort_sha, "stage": "classified"},
            })
        peers.append({
            "request_sha256": cohort_sha, "frontier_stage": "request_bound",
            "admissible_control": False,
        })
    frontier = {"control_frontier_sha256": "f" * 64, "peer_eligibility": peers}
    service = {
        "enabled": True,
        "daily_dispatch_budget": {"exhausted": True, "used": 8, "limit": 8},
        "service": {
            "status": "dispatching_strategy_cohort",
            "last_work_id": next(
                row["work_id"] for row in queue
                if (row.get("payload") or {}).get("stage") == "dispatching"
            ),
            "checked_at": "2026-01-01T20:00:00Z", "poll_seconds": 60,
        },
    }
    projection = compile_strategy_control_runtime_status(
        queue, adapters, frontier, service, results=results,
    )
    by_entity = {row["peer_entity_id"]: row for row in projection["jobs"]}
    assert {entity: by_entity[entity.upper()]["runtime_state"] for entity, _, _ in states} == {
        "queued": "queued", "leased": "leased", "dispatching": "dispatching",
        "retry": "retry", "completed": "typed_completion", "gap": "terminal_source_gap",
    }
    assert by_entity["COMPLETED"]["control_frontier"]["consequence"] == (
        "control_candidate_ready_for_frontier_recompile"
    )
    assert projection["automatic_transition"]["next"] == "service_poll_budget_check_no_queue_change"
