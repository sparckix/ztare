"""Source-triggered continuation of bounded strategy-event searches."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, timestamp_key
from .strategy_learning import (
    STRATEGY_COHORT_PLAN_SCHEMA,
    compile_strategy_cohort_research_result,
    strategy_cohort_query_identity,
)


STRATEGY_EVENT_MONITOR_SCHEMA = "jaggedthoughts-strategy-event-monitor-v1"
STRATEGY_EVENT_ACTIVATION_SCHEMA = "jaggedthoughts-strategy-event-activation-v1"


def compile_strategy_event_monitor(
    request: Mapping[str, Any], result: Mapping[str, Any],
    source_receipts: Mapping[str, Mapping[str, Any]], *, recorded_at: str,
    issuer_recheck_days: int = 90,
) -> dict[str, Any]:
    """Freeze the source baseline that can reopen one classified peer search."""
    if issuer_recheck_days < 1:
        raise ValueError("strategy issuer recheck cadence must be positive")
    normalized = compile_strategy_cohort_research_result(result, request)
    if normalized["result_sha256"] != result.get("result_sha256"):
        raise ValueError("strategy event monitor requires the compiled cohort result")
    query = strategy_cohort_query_identity(request)
    covered_through = canonical_timestamp(
        normalized["coverage"]["search_end_at"], "strategy monitor coverage end",
    )
    observed_at = canonical_timestamp(recorded_at, "strategy monitor recorded_at")
    if timestamp_key(observed_at) < timestamp_key(str(normalized["assessed_at"])):
        raise ValueError("strategy event monitor cannot precede its classification")
    source_id = f"sec_{str(request['peer_entity_id']).lower()}_submissions"
    receipt = dict(source_receipts.get(source_id) or {})
    if receipt and receipt.get("adapter") != "sec_submissions":
        raise ValueError("strategy event monitor source is not SEC submissions")
    receipt_retrieved_at = receipt.get("retrieved_at")
    baseline_status = (
        "post_coverage_uncompared"
        if receipt_retrieved_at
        and timestamp_key(str(receipt_retrieved_at)) > timestamp_key(covered_through)
        else "covered_baseline" if receipt else "source_receipt_absent"
    )
    next_recheck = timestamp_key(covered_through) + timedelta(days=issuer_recheck_days)
    body = {
        "schema": STRATEGY_EVENT_MONITOR_SCHEMA,
        "query_sha256": query["query_sha256"],
        "request_sha256": request["request_sha256"],
        "result_sha256": normalized["result_sha256"],
        "peer_entity_id": request["peer_entity_id"],
        "classification": normalized["classification"],
        "covered_through": covered_through,
        "recorded_at": observed_at,
        "sec_submissions_baseline": ({
            "source_id": source_id,
            "content_sha256": receipt.get("content_sha256"),
            "receipt_sha256": receipt.get("receipt_sha256"),
            "retrieved_at": receipt.get("retrieved_at"),
            "status": baseline_status,
        } if receipt else None),
        "next_issuer_recheck_at": next_recheck.isoformat(timespec="seconds").replace(
            "+00:00", "Z",
        ),
        "negative_evidence_boundary": (
            "A bounded no-family result remains not-yet-treated only through covered_through."
        ),
        "authority": "research_reactivation_only",
        "capital_authority": False,
    }
    return {**body, "monitor_sha256": stable_sha256(body)}


def compile_strategy_event_activations(
    plan: Mapping[str, Any], results: Mapping[str, Mapping[str, Any]],
    monitors: list[Mapping[str, Any]],
    source_receipts: Mapping[str, Mapping[str, Any]], *, as_of: str,
) -> dict[str, Any]:
    """Open only SEC-change or due issuer-review deltas for current queries."""
    if plan.get("schema") != STRATEGY_COHORT_PLAN_SCHEMA:
        raise ValueError("strategy event activations require a cohort plan")
    now = canonical_timestamp(as_of, "strategy event activation as_of")
    monitor_by_identity = {}
    for raw in monitors:
        monitor = dict(raw)
        declared = str(monitor.pop("monitor_sha256", ""))
        if monitor.get("schema") != STRATEGY_EVENT_MONITOR_SCHEMA or stable_sha256(monitor) != declared:
            raise ValueError("strategy event monitor content hash mismatch")
        monitor_by_identity[(str(monitor["query_sha256"]), str(monitor["result_sha256"]))] = raw

    activations, blocks = [], []
    for request in plan.get("requests") or ():
        request_sha = str(request["request_sha256"])
        result = results.get(request_sha)
        if not result or result.get("classification") == "phenotype_adoption_found":
            continue
        query_sha = strategy_cohort_query_identity(request)["query_sha256"]
        monitor = monitor_by_identity.get((query_sha, str(result.get("result_sha256") or "")))
        if not monitor:
            blocks.append({
                "query_sha256": query_sha, "peer_entity_id": request["peer_entity_id"],
                "reason": "monitor_baseline_absent",
            })
            continue
        trigger_epochs: list[tuple[str, str]] = []
        if timestamp_key(str(result["coverage"]["search_end_at"])) < timestamp_key(
            str(request["search_end_at"])
        ):
            trigger_epochs.append(("pending_coverage_delta", str(request["search_end_at"])))
        baseline = monitor.get("sec_submissions_baseline") or {}
        source_id = str(baseline.get("source_id") or "")
        current = source_receipts.get(source_id) or {}
        if baseline.get("status") == "post_coverage_uncompared":
            trigger_epochs.append(("sec_source_epoch_uncompared", str(baseline["retrieved_at"])))
        elif (
            baseline.get("content_sha256")
            and current.get("content_sha256")
            and current.get("content_sha256") != baseline.get("content_sha256")
            and timestamp_key(str(current.get("retrieved_at")))
            > timestamp_key(str(monitor["covered_through"]))
            and timestamp_key(str(current.get("retrieved_at"))) <= timestamp_key(now)
        ):
            trigger_epochs.append(("sec_submissions_changed", str(current["retrieved_at"])))
        due_at = str(monitor["next_issuer_recheck_at"])
        if timestamp_key(now) >= timestamp_key(due_at):
            trigger_epochs.append(("issuer_materials_recheck_due", due_at))
        if not trigger_epochs:
            continue
        search_end = max((epoch for _, epoch in trigger_epochs), key=timestamp_key)
        if timestamp_key(search_end) <= timestamp_key(str(result["coverage"]["search_end_at"])):
            continue
        activations.append({
            "query_sha256": query_sha,
            "peer_entity_id": request["peer_entity_id"],
            "prior_result_sha256": result["result_sha256"],
            "prior_coverage_end_at": monitor["covered_through"],
            "search_end_at": search_end,
            "trigger_kinds": sorted(kind for kind, _ in trigger_epochs),
            "required_source_classes": list(request["required_source_classes"]),
            "expected_exit": "typed_equivalent_adoption_classification_or_source_gap",
            "capital_authority": False,
        })
    by_query = {str(row["query_sha256"]): str(row["search_end_at"]) for row in activations}
    body = {
        "schema": STRATEGY_EVENT_ACTIVATION_SCHEMA,
        "as_of": now,
        "plan_sha256": plan.get("plan_sha256"),
        "activation_count": len(activations),
        "activations": sorted(activations, key=lambda row: row["query_sha256"]),
        "blocked_count": len(blocks), "blocks": blocks,
        "search_end_by_query_sha256": dict(sorted(by_query.items())),
        "next_activation": (
            "Reclassify activated query deltas through the existing subscription cohort job."
            if activations else "Refresh enrolled SEC submissions or wait for the next issuer review."
        ),
        "capital_authority": False,
    }
    return {**body, "activation_sha256": stable_sha256(body)}


__all__ = [
    "STRATEGY_EVENT_ACTIVATION_SCHEMA", "STRATEGY_EVENT_MONITOR_SCHEMA",
    "compile_strategy_event_activations", "compile_strategy_event_monitor",
]
