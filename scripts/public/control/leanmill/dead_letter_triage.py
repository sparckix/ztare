#!/usr/bin/env python3
"""Bounded dead-letter triage for LeanMill WorkItems.

This worker does not interpret proof value. It only decides whether a terminal
queue item is operationally retryable under the current control-plane contract.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue


DEFAULT_OUT = "analytics/public/leanmill/dashboard_data/dead_letter_triage_status.json"
RETRYABLE_KINDS = {"llm_proposal_validate", "agent_repair_task", "source_scout_task"}
NONRETRYABLE_EXIT_KIND = "dead_letter_triaged_nonretryable"



def _now() -> int:
    return int(time.time())


def _payload(row: Any) -> dict[str, Any]:
    try:
        obj = json.loads(row["payload_json"] or "{}")
    except json.JSONDecodeError:
        obj = {}
    return obj if isinstance(obj, dict) else {}


def _is_retryable(row: Any, payload: dict[str, Any], *, max_requeues: int) -> tuple[bool, str]:
    kind = str(row["kind"] or "")
    if kind not in RETRYABLE_KINDS:
        return False, "kind_not_retryable"
    if int(payload.get("dead_letter_requeue_count") or 0) >= max_requeues:
        return False, "requeue_budget_exhausted"
    if kind == "llm_proposal_validate":
        if payload.get("llm_proposal_status") in {"accepted", "rejected", "operator_required"}:
            return False, "already_has_terminal_llm_status"
        if not (payload.get("prompt") and payload.get("proposal_type")):
            return False, "missing_proposal_contract"
        return True, "retryable_llm_proposal_validate"
    exit_kind = str(payload.get("exit_kind") or "")
    if payload.get("output_path") or (exit_kind and exit_kind != "dead_letter_unclassified"):
        return False, "already_has_terminal_agent_output"
    if not (payload.get("task") and payload.get("runtime")):
        return False, "missing_agent_contract"
    return True, "retryable_subscription_agent_no_output"


def build(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    rows = cx.execute(
        """
        SELECT *
        FROM work_items
        WHERE status='dead_letter'
        ORDER BY updated_at ASC
        LIMIT ?
        """,
        (max(1, int(args.limit)),),
    ).fetchall()
    reviewed: list[dict[str, Any]] = []
    requeued = 0
    for row in rows:
        payload = _payload(row)
        retryable, reason = _is_retryable(row, payload, max_requeues=args.max_requeues)
        rec = {
            "work_id": row["work_id"],
            "kind": row["kind"],
            "family": row["family"] or payload.get("family") or "",
            "retryable": retryable,
            "reason": reason,
        }
        if retryable and args.enqueue:
            count = int(payload.get("dead_letter_requeue_count") or 0) + 1
            payload.update({
                "dead_letter_requeue_count": count,
                "dead_letter_requeued_at": _now(),
                "dead_letter_requeue_reason": reason,
            })
            work_queue.enqueue(
                cx,
                kind=row["kind"],
                priority=int(row["priority"]),
                payload=payload,
                max_attempts=max(1, int(args.max_attempts)),
            )
            work_queue.append_event(args.events, {
                "event_type": "dead_letter_requeued",
                "work_id": row["work_id"],
                "payload": {
                    "kind": row["kind"],
                    "family": rec["family"],
                    "reason": reason,
                    "dead_letter_requeue_count": count,
                },
            })
            requeued += 1
            rec["requeued"] = True
        elif args.enqueue and args.retire_nonretryable:
            work_queue.update_status(cx, work_id=row["work_id"], status="retired", payload_update={
                "exit_kind": str(payload.get("exit_kind") or NONRETRYABLE_EXIT_KIND),
                "ops_exit_kind": NONRETRYABLE_EXIT_KIND,
                "dead_letter_triaged_at": _now(),
                "dead_letter_triage_reason": reason,
                "dead_letter_terminal_status_before_triage": "dead_letter",
                "dead_letter_retired_by": "leanmill_dead_letter_triage",
            })
            work_queue.append_event(args.events, {
                "event_type": "dead_letter_retired_nonretryable",
                "work_id": row["work_id"],
                "payload": {
                    "kind": row["kind"],
                    "family": rec["family"],
                    "reason": reason,
                    "exit_kind": NONRETRYABLE_EXIT_KIND,
                },
            })
            rec["retired"] = True
        reviewed.append(rec)
    result = {
        "schema": "leanmill-dead-letter-triage-v1",
        "generated_at_epoch": _now(),
        "dry_run": not bool(args.enqueue),
        "reviewed": reviewed,
        "reviewed_count": len(reviewed),
        "requeued": requeued,
        "retired_nonretryable": sum(1 for rec in reviewed if rec.get("retired")),
    }
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_dead_letter_triage_") as td:
        root = Path(td)
        db = str(root / "q.sqlite")
        events = str(root / "events.jsonl")
        cx = work_queue.connect(db)
        wid = work_queue.enqueue(cx, kind="llm_proposal_validate", priority=5, max_attempts=1, payload={
            "work_id": "w1",
            "family": "fam",
            "prompt": "emit json",
            "proposal_type": "source_request",
        })
        work_queue.update_status(cx, work_id=wid, status="dead_letter")
        dry = build(argparse.Namespace(
            queue_db=db,
            events=events,
            out=str(root / "dry.json"),
            limit=10,
            max_requeues=1,
            max_attempts=2,
            enqueue=False,
        ))
        assert dry["requeued"] == 0
        live = build(argparse.Namespace(
            queue_db=db,
            events=events,
            out=str(root / "live.json"),
            limit=10,
            max_requeues=1,
            max_attempts=2,
            enqueue=True,
            retire_nonretryable=True,
        ))
        assert live["requeued"] == 1
        row = cx.execute("SELECT status, attempts, max_attempts, payload_json FROM work_items WHERE work_id=?", (wid,)).fetchone()
        assert row["status"] == "queued"
        assert row["attempts"] == 0
        assert row["max_attempts"] == 2
        payload = json.loads(row["payload_json"])
        assert payload["dead_letter_requeue_count"] == 1
        awid = work_queue.enqueue(cx, kind="agent_repair_task", priority=5, max_attempts=1, payload={
            "work_id": "a1",
            "family": "fam",
            "runtime": "codex",
            "task": "bounded repair task",
        })
        work_queue.update_status(cx, work_id=awid, status="dead_letter")
        agent_live = build(argparse.Namespace(
            queue_db=db,
            events=events,
            out=str(root / "agent_live.json"),
            limit=10,
            max_requeues=1,
            max_attempts=2,
            enqueue=True,
            retire_nonretryable=True,
        ))
        assert agent_live["requeued"] == 1
        nid = work_queue.enqueue(cx, kind="repair_canary_probe", priority=5, max_attempts=1, payload={
            "work_id": "probe-nonretryable",
            "family": "fam",
        })
        work_queue.update_status(cx, work_id=nid, status="dead_letter")
        retired = build(argparse.Namespace(
            queue_db=db,
            events=events,
            out=str(root / "retired.json"),
            limit=10,
            max_requeues=1,
            max_attempts=2,
            enqueue=True,
            retire_nonretryable=True,
        ))
        assert retired["retired_nonretryable"] >= 1
        row = cx.execute("SELECT status, payload_json FROM work_items WHERE work_id=?", (nid,)).fetchone()
        assert row["status"] == "retired"
        assert json.loads(row["payload_json"])["ops_exit_kind"] == NONRETRYABLE_EXIT_KIND
    print("leanmill_dead_letter_triage self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--max-requeues", type=int, default=1)
    ap.add_argument("--max-attempts", type=int, default=2)
    ap.add_argument("--enqueue", action="store_true")
    ap.add_argument("--retire-nonretryable", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    result = build(args)
    print(json.dumps({
        "dry_run": result["dry_run"],
        "out": args.out,
        "reviewed_count": result["reviewed_count"],
        "requeued": result["requeued"],
        "retired_nonretryable": result.get("retired_nonretryable", 0),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
