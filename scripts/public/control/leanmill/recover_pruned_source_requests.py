#!/usr/bin/env python3
"""Recover source-search work lost to over-strict mixed-query gating.

The LLM/agent proposal lane can produce a source_request that mixes useful
theorem-shaped queries with weak lines. Older workers dropped the whole request
if any query failed the gate. This recovery pass replays saved proposal
artifacts from the event ledger and enqueues source_search_task work when at
least three accepted queries remain after pruning.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_source_query_contract import source_queries_from_proposal
from leanmill_source_search_integrator import _queries_pass_gate


DEFAULT_DB = "analytics/public/leanmill/dashboard_data/leanmill_work_queue.sqlite"
DEFAULT_EVENTS = "analytics/public/leanmill/dashboard_data/leanmill_events.jsonl"


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value).strip("_") or "item"


def _read_json(path: str | Path) -> Any:
    try:
        return json.loads(Path(path).read_text(errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return None


def _iter_events(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in p.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            events.append(obj)
    return events


def _source_queries_from_proposal(obj: dict[str, Any]) -> list[Any]:
    return source_queries_from_proposal(obj)


def _target_rows_from_proposal(obj: dict[str, Any]) -> list[str]:
    raw = obj.get("target_row_ids") or obj.get("target_rows") or []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    rows: list[str] = []
    for item in raw:
        row_id = " ".join(str(item or "").split())
        if row_id and row_id not in rows:
            rows.append(row_id[:160])
    return rows[:20]


def _accepted_quality(quality: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [q for q in quality if isinstance(q, dict) and bool(q.get("accepted"))]


def _rejected_quality(quality: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [q for q in quality if isinstance(q, dict) and not bool(q.get("accepted"))]


def _existing_work(cx: sqlite3.Connection, work_id: str) -> dict[str, Any] | None:
    row = cx.execute("SELECT status, payload_json FROM work_items WHERE work_id=? LIMIT 1", (work_id,)).fetchone()
    if row is None:
        return None
    try:
        payload = json.loads(row["payload_json"] or "{}")
    except json.JSONDecodeError:
        payload = {}
    return {"status": row["status"], "payload": payload if isinstance(payload, dict) else {}}


def _can_requeue_stale_low_quality_source_search(existing: dict[str, Any] | None) -> bool:
    if not existing or str(existing.get("status") or "") != "failed":
        return False
    payload = existing.get("payload") if isinstance(existing.get("payload"), dict) else {}
    return str(payload.get("exit_kind") or "") == "source_search_rejected_low_quality_queries"


def _failed_source_request_proposal_rows(cx: sqlite3.Connection, *, since_epoch: int, limit: int) -> list[dict[str, Any]]:
    rows = cx.execute(
        """
        SELECT work_id, payload_json, family, updated_at
        FROM work_items
        WHERE status='failed'
          AND kind IN ('llm_proposal_validate', 'source_request_propose', 'decomposition_propose', 'canary_propose')
          AND updated_at >= ?
          AND json_extract(payload_json, '$.exit_kind')='proposal_rejected'
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (int(since_epoch), max(1, int(limit))),
    ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        proposal_path = str(payload.get("proposal_path") or (payload.get("model") or {}).get("proposal_path") or "")
        if not proposal_path:
            for path in payload.get("artifact_paths") or []:
                if str(path).endswith("_proposal.json"):
                    proposal_path = str(path)
                    break
        if proposal_path:
            out.append({
                "work_id": row["work_id"],
                "family": row["family"] or payload.get("family") or "",
                "proposal_path": proposal_path,
                "source": "failed_proposal_row",
            })
    return out


def _proposal_event_records(events: list[dict[str, Any]], *, since_epoch: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for event in events:
        if int(event.get("timestamp") or 0) < int(since_epoch):
            continue
        if str(event.get("event_type") or "") != "source_search_task_not_enqueued_query_gate":
            continue
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        proposal_path = str(payload.get("proposal_path") or "")
        if proposal_path:
            records.append({
                "work_id": str(event.get("work_id") or f"recovered:{_slug(proposal_path)}"),
                "family": payload.get("family") or "",
                "proposal_path": proposal_path,
                "source": "source_query_gate_event",
            })
    return records


def recover(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    seen_paths: set[str] = set()
    reviewed = 0
    enqueued: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    event_records = _proposal_event_records(_iter_events(args.events), since_epoch=int(args.since_epoch))
    failed_records = _failed_source_request_proposal_rows(
        cx,
        since_epoch=int(args.since_epoch),
        limit=max(int(args.limit) * 5, int(args.limit) + 20),
    )
    for record in [*event_records, *failed_records]:
        proposal_path = str(record.get("proposal_path") or "")
        if not proposal_path or proposal_path in seen_paths:
            continue
        seen_paths.add(proposal_path)
        proposal_obj = _read_json(proposal_path)
        proposals = proposal_obj if isinstance(proposal_obj, list) else [proposal_obj]
        for idx, proposal in enumerate(proposals):
            if len(enqueued) >= int(args.limit):
                break
            if not isinstance(proposal, dict):
                continue
            reviewed += 1
            if str(proposal.get("proposal_type") or "") != "source_request":
                skipped.append({"proposal_path": proposal_path, "reason": "not_source_request"})
                continue
            family = str(proposal.get("family") or record.get("family") or "unknown_family")
            queries = _source_queries_from_proposal(proposal)
            target_row_ids = _target_rows_from_proposal(proposal)
            _ok, quality = _queries_pass_gate(queries, family)
            accepted_quality = _accepted_quality(quality)
            rejected_quality = _rejected_quality(quality)
            accepted_queries = [str(q.get("normalized_query") or q.get("query") or "") for q in accepted_quality if str(q.get("normalized_query") or q.get("query") or "")]
            if len(accepted_queries) < 3 or not target_row_ids:
                skipped.append({
                    "proposal_path": proposal_path,
                    "family": family,
                    "reason": "insufficient_accepted_queries_or_targets",
                    "accepted_query_count": len(accepted_queries),
                    "target_row_count": len(target_row_ids),
                })
                continue
            parent_work_id = str(record.get("work_id") or f"recovered:{_slug(proposal_path)}")
            work_id = f"source_search:{_slug(family)}:{_slug(parent_work_id)}:recovered:{idx}"
            item = {
                "work_id": work_id,
                "station": "source_qualification",
                "family": family,
                "queries": accepted_queries,
                "target_row_ids": target_row_ids,
                "query_quality": accepted_quality,
                "rejected_query_quality": rejected_quality,
                "original_query_count": len(queries),
                "parent_work_id": parent_work_id,
                "proposal_path": proposal_path,
                "expected_exit": "qualified_source_or_rejected_with_reason",
                "recovery_reason": "pruned_mixed_quality_source_request",
                "credit_boundary": {
                    "source_search_has_no_proof_credit": True,
                    "proof_credit_authority": "governance_gate",
                },
            }
            existing = _existing_work(cx, work_id)
            requeue_stale = _can_requeue_stale_low_quality_source_search(existing)
            if existing and not requeue_stale:
                skipped.append({
                    "proposal_path": proposal_path,
                    "family": family,
                    "reason": "work_already_exists",
                    "work_id": work_id,
                    "existing_status": existing.get("status"),
                })
                continue
            if not args.dry_run:
                if requeue_stale:
                    item["recovery_reason"] = "requeue_after_source_query_contract_fix"
                work_queue.enqueue(cx, kind="source_search_task", priority=int(args.priority), payload=item, max_attempts=2)
                work_queue.append_event(args.events, {
                    "event_type": "source_search_task_requeued_after_query_contract_fix" if requeue_stale else "source_search_task_recovered_from_pruned_query_gate",
                    "work_id": work_id,
                    "payload": {
                        "family": family,
                        "parent_work_id": parent_work_id,
                        "query_count": len(accepted_queries),
                        "raw_query_count": len(queries),
                        "rejected_query_count": len(rejected_quality),
                        "target_row_count": len(target_row_ids),
                        "inserted": True,
                        "recovery_source": record.get("source"),
                        "requeued_stale_low_quality_source_search": bool(requeue_stale),
                    },
                    "artifact_paths": [proposal_path],
                })
            enqueued.append({
                "work_id": work_id,
                "family": family,
                "query_count": len(accepted_queries),
                "raw_query_count": len(queries),
                "rejected_query_count": len(rejected_quality),
                "target_row_count": len(target_row_ids),
                "recovery_source": record.get("source"),
                "requeued_stale_low_quality_source_search": bool(requeue_stale),
            })
        if len(enqueued) >= int(args.limit):
            break
    return {
        "schema": "leanmill-recover-pruned-source-requests-v1",
        "dry_run": bool(args.dry_run),
        "since_epoch": int(args.since_epoch),
        "reviewed": reviewed,
        "enqueued_count": len(enqueued),
        "enqueued": enqueued,
        "skipped_count": len(skipped),
        "skipped": skipped[:20],
    }


def _self_test() -> int:
    quality = [
        {"query": "bad", "accepted": False},
        {"query": "Matrix gram PosDef LinearIndependent", "accepted": True},
    ]
    assert _accepted_quality(quality) == [quality[1]]
    assert _rejected_quality(quality) == [quality[0]]
    assert _source_queries_from_proposal({"source_query": ["a", "a", "b"]}) == ["a", "b"]
    assert _target_rows_from_proposal({"target_row_ids": ["MCB_1", "MCB_1"]}) == ["MCB_1"]
    print("leanmill_recover_pruned_source_requests self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=DEFAULT_DB)
    ap.add_argument("--events", default=DEFAULT_EVENTS)
    ap.add_argument("--since-epoch", type=int, default=0)
    ap.add_argument("--lookback-s", type=int, default=0)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--priority", type=int, default=94)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if int(args.since_epoch) <= 0 and int(args.lookback_s) > 0:
        args.since_epoch = int(time.time()) - int(args.lookback_s)
    result = recover(args)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
