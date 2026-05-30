#!/usr/bin/env python3
"""Requeue retryable LeanMill WorkItems after control-plane fixes.

This is intentionally narrow: it only requeues terminal failures whose payload
shows a known recoverable control-plane failure class. Scientific failures such
as rejected proposals, no-signal probes, and failed negative controls stay
terminal and must exit through the normal triage lanes.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_factory_config import FACTORY_POLICY as DEFAULT_FACTORY_POLICY, priority_value

DEFAULT_OUT = "analytics/public/leanmill/dashboard_data/retryable_failure_recovery.json"


def _queue_priority(args: argparse.Namespace, key: str, fallback: int) -> int:
    return priority_value(
        path=getattr(args, "factory_policy", DEFAULT_FACTORY_POLICY),
        namespace="work_queue",
        key=key,
        fallback=fallback,
    )

RETRYABLE_KINDS = {
    "llm_proposal_validate",
    "decomposition_propose",
    "canary_propose",
    "source_request_propose",
}
RETRYABLE_AGENT_PRELAUNCH_FAILURES = {
    "max_wall_time_exceeds_worker_budget",
}
RETRYABLE_EXIT_KINDS = {
    "proposal_worker_exception",
    "llm_api_unparseable",
    "llm_api_failed",
    "codex_cli_fallback_parse_failed",
    "codex_cli_fallback_failed",
}
RETRYABLE_REASON_FRAGMENTS = (
    "File name too long",
    "model output JSON could not be parsed",
    "model output did not contain JSON",
    "api_output_unparseable",
    "api_runtime_error",
)


STALE_TERMINAL_PAYLOAD_KEYS = (
    "exit_kind",
    "reason",
    "result",
    "model",
    "artifact_paths",
    "status",
    "failures",
    "failure_count",
    "agent_launched",
    "agent_output_ingest_status",
    "agent_output_ingested_at_epoch",
)


def _now() -> int:
    return int(time.time())


def _payload(row: sqlite3.Row) -> dict[str, Any]:
    try:
        obj = json.loads(row["payload_json"] or "{}")
    except json.JSONDecodeError:
        obj = {}
    return obj if isinstance(obj, dict) else {}


def _retryable(row: sqlite3.Row, payload: dict[str, Any], *, max_requeues: int) -> tuple[bool, str]:
    count = int(payload.get("retryable_failure_requeue_count") or 0)
    if count >= max_requeues:
        return False, "requeue_budget_exhausted"
    if str(row["kind"] or "") == "agent_repair_task" and not bool(payload.get("agent_launched")):
        failures = payload.get("failures") if isinstance(payload.get("failures"), list) else []
        for failure in failures:
            if isinstance(failure, dict) and str(failure.get("failure") or "") in RETRYABLE_AGENT_PRELAUNCH_FAILURES:
                return True, str(failure.get("failure"))
    if str(row["kind"] or "") not in RETRYABLE_KINDS:
        return False, "kind_not_retryable"
    exit_kind = str(payload.get("exit_kind") or "")
    reason = str(payload.get("reason") or "")
    if exit_kind in RETRYABLE_EXIT_KINDS:
        return True, exit_kind
    if any(fragment in reason for fragment in RETRYABLE_REASON_FRAGMENTS):
        return True, "retryable_reason_fragment"
    return False, "failure_class_not_retryable"


def _clean_retry_payload(row: sqlite3.Row, payload: dict[str, Any], *, reason: str) -> dict[str, Any]:
    count = int(payload.get("retryable_failure_requeue_count") or 0) + 1
    new_payload = dict(payload)
    for key in STALE_TERMINAL_PAYLOAD_KEYS:
        new_payload.pop(key, None)
    new_payload.update({
        "work_id": row["work_id"],
        "retryable_failure_requeue_count": count,
        "retryable_failure_requeued_at_epoch": _now(),
        "retryable_failure_requeue_reason": reason,
        "retryable_failure_recovered_from_status": row["status"],
    })
    return new_payload


def _update_queued_payload(cx: sqlite3.Connection, row: sqlite3.Row, payload: dict[str, Any]) -> None:
    family = str(payload.get("family") or "")
    station = str(payload.get("station") or "")
    expected_exit = str(payload.get("expected_exit") or payload.get("exit_kind") or "")
    cx.execute(
        """
        UPDATE work_items
        SET family=?, station=?, expected_exit=?, payload_json=?, updated_at=?
        WHERE work_id=? AND status='queued'
        """,
        (family, station, expected_exit, json.dumps(payload, sort_keys=True), _now(), row["work_id"]),
    )
    cx.commit()


def recover(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    rows = cx.execute(
        """
        SELECT *
        FROM work_items
        WHERE status IN ('queued', 'failed', 'dead_letter')
          AND updated_at >= ?
        ORDER BY priority DESC, updated_at DESC
        LIMIT ?
        """,
        (max(0, int(args.since_epoch)), max(1, int(args.limit))),
    ).fetchall()
    inspected = 0
    requeued = 0
    cleaned_queued = 0
    skipped: list[dict[str, Any]] = []
    recovered: list[dict[str, Any]] = []
    for row in rows:
        inspected += 1
        payload = _payload(row)
        ok, reason = _retryable(row, payload, max_requeues=int(args.max_requeues))
        if not ok:
            skipped.append({"work_id": row["work_id"], "kind": row["kind"], "reason": reason})
            continue
        new_payload = _clean_retry_payload(row, payload, reason=reason)
        if args.enqueue:
            if str(row["status"] or "") == "queued":
                _update_queued_payload(cx, row, new_payload)
                event_type = "retryable_failure_queued_payload_cleaned"
                cleaned_queued += 1
            else:
                work_queue.enqueue(
                    cx,
                    kind=str(row["kind"]),
                    priority=int(row["priority"] or args.priority),
                    payload=new_payload,
                    max_attempts=int(args.max_attempts),
                )
                event_type = "retryable_failure_requeued"
                requeued += 1
            work_queue.append_event(args.events, {
                "event_type": event_type,
                "work_id": row["work_id"],
                "payload": {
                    "kind": row["kind"],
                    "family": row["family"],
                    "reason": reason,
                    "retryable_failure_requeue_count": int(new_payload.get("retryable_failure_requeue_count") or 0),
                },
            })
        recovered.append({"work_id": row["work_id"], "kind": row["kind"], "family": row["family"], "reason": reason})
    out = {
        "schema": "leanmill-retryable-failure-recovery-v1",
        "generated_at_epoch": _now(),
        "inspected": inspected,
        "requeued": requeued,
        "cleaned_queued": cleaned_queued,
        "dry_run": not bool(args.enqueue),
        "recovered": recovered[:50],
        "skipped_count": len(skipped),
        "skipped": skipped[:50],
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return out


def _self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="leanmill_retryable_failure_recovery_") as td:
        db = str(Path(td) / "queue.sqlite")
        events = str(Path(td) / "events.jsonl")
        cx = work_queue.connect(db)
        wid = work_queue.enqueue(
            cx,
            kind="decomposition_propose",
            priority=10,
            payload={
                "work_id": "w",
                "family": "fam",
                "proposal_type": "decomposition",
                "reason": "ValueError: model output JSON could not be parsed",
            },
            max_attempts=1,
        )
        work_queue.update_status(cx, work_id=wid, status="failed", payload_update={"exit_kind": "proposal_worker_exception"})
        dry = recover(argparse.Namespace(
            queue_db=db,
            events=events,
            out=str(Path(td) / "out.json"),
            since_epoch=0,
            limit=10,
            max_requeues=1,
            max_attempts=1,
            priority=10,
            enqueue=False,
        ))
        assert dry["requeued"] == 0 and dry["recovered"]
        live = recover(argparse.Namespace(
            queue_db=db,
            events=events,
            out=str(Path(td) / "out.json"),
            since_epoch=0,
            limit=10,
            max_requeues=1,
            max_attempts=1,
            priority=10,
            enqueue=True,
        ))
        assert live["requeued"] == 1
        row = cx.execute("SELECT status, attempts, payload_json FROM work_items WHERE work_id='w'").fetchone()
        assert row["status"] == "queued" and int(row["attempts"]) == 0
        payload = json.loads(row["payload_json"])
        assert payload["retryable_failure_requeue_count"] == 1
        assert "exit_kind" not in payload and "status" not in payload and "failures" not in payload
        agent_wid = work_queue.enqueue(
            cx,
            kind="agent_repair_task",
            priority=10,
            payload={"work_id": "agent-w", "family": "fam", "max_wall_time_s": 1200},
            max_attempts=1,
        )
        work_queue.update_status(cx, work_id=agent_wid, status="failed", payload_update={
            "agent_launched": False,
            "failures": [{"failure": "max_wall_time_exceeds_worker_budget", "limit": 900, "requested": 1200}],
        })
        agent_live = recover(argparse.Namespace(
            queue_db=db,
            events=events,
            out=str(Path(td) / "out.json"),
            since_epoch=0,
            limit=10,
            max_requeues=1,
            max_attempts=1,
            priority=10,
            enqueue=True,
        ))
        assert any(item["work_id"] == "agent-w" for item in agent_live["recovered"])
        agent_row = cx.execute("SELECT status, attempts, payload_json FROM work_items WHERE work_id='agent-w'").fetchone()
        assert agent_row["status"] == "queued" and int(agent_row["attempts"]) == 0
        agent_payload = json.loads(agent_row["payload_json"])
        assert "failures" not in agent_payload and "agent_launched" not in agent_payload
        cx.execute(
            "UPDATE work_items SET payload_json=?, updated_at=? WHERE work_id='agent-w'",
            (
                json.dumps({
                    **agent_payload,
                    "agent_launched": False,
                    "failures": [{"failure": "max_wall_time_exceeds_worker_budget", "limit": 900, "requested": 1200}],
                    "status": "fail",
                }, sort_keys=True),
                _now(),
            ),
        )
        cx.commit()
        queued_live = recover(argparse.Namespace(
            queue_db=db,
            events=events,
            out=str(Path(td) / "out.json"),
            since_epoch=0,
            limit=10,
            max_requeues=3,
            max_attempts=1,
            priority=10,
            enqueue=True,
        ))
        assert queued_live["cleaned_queued"] == 1
        queued_row = cx.execute("SELECT status, attempts, payload_json FROM work_items WHERE work_id='agent-w'").fetchone()
        assert queued_row["status"] == "queued" and int(queued_row["attempts"]) == 0
        queued_payload = json.loads(queued_row["payload_json"])
        assert "failures" not in queued_payload and "agent_launched" not in queued_payload and "status" not in queued_payload
    print("leanmill_retryable_failure_recovery self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--since-epoch", type=int, default=0)
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--max-requeues", type=int, default=1)
    ap.add_argument("--max-attempts", type=int, default=1)
    ap.add_argument("--priority", type=int, default=125)
    ap.add_argument("--factory-policy", default=DEFAULT_FACTORY_POLICY)
    ap.add_argument("--enqueue", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if int(args.priority) == 125:
        args.priority = _queue_priority(args, "retryable_failure_recovery_requeue", 125)
    print(json.dumps(recover(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
