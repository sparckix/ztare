#!/usr/bin/env python3
"""Recover external-scout source-search tasks retired by stale source holds."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_factory_config import FACTORY_POLICY as DEFAULT_FACTORY_POLICY, priority_value


DEFAULT_OUT = "analytics/public/leanmill/dashboard_data/external_source_search_recovery.json"


def _queue_priority(args: argparse.Namespace, key: str, fallback: int) -> int:
    return priority_value(
        path=getattr(args, "factory_policy", DEFAULT_FACTORY_POLICY),
        namespace="work_queue",
        key=key,
        fallback=fallback,
    )


def _is_external_source_search(payload: dict[str, Any], work_id: str) -> bool:
    parent = str(payload.get("parent_work_id") or "")
    proposal = str(payload.get("proposal_path") or "")
    return (
        str(payload.get("source_scout_mode") or "") == "subscription_public_external"
        or "external_source_scout" in work_id
        or "external_source_scout" in parent
        or "external_source_scout" in proposal
    )


def recover(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    rows = cx.execute(
        """
        SELECT work_id, kind, priority, payload_json
        FROM work_items
        WHERE kind='source_search_task'
          AND status='retired'
          AND payload_json LIKE '%external_source_scout%'
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (int(args.limit),),
    ).fetchall()
    recovered: list[dict[str, Any]] = []
    skipped = 0
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            skipped += 1
            continue
        work_id = str(row["work_id"])
        if not _is_external_source_search(payload, work_id):
            skipped += 1
            continue
        if str(payload.get("exit_kind") or "") == "retired_source_strategy_repair_required":
            skipped += 1
            continue
        payload["source_scout_mode"] = "subscription_public_external"
        payload["recovered_at_epoch"] = int(time.time())
        payload["recovery_reason"] = "external_source_search_retired_by_stale_source_binding_hold"
        work_queue.enqueue(
            cx,
            kind="source_search_task",
            priority=int(args.priority or row["priority"] or 92),
            payload=payload,
            max_attempts=args.max_attempts,
        )
        work_queue.append_event(args.events, {
            "event_type": "external_source_search_recovered",
            "work_id": work_id,
            "payload": {
                "family": payload.get("family"),
                "parent_work_id": payload.get("parent_work_id"),
                "query_count": len(payload.get("queries") or []),
                "target_row_count": len(payload.get("target_row_ids") or []),
            },
            "artifact_paths": [str(payload.get("proposal_path") or "")],
        })
        recovered.append({
            "work_id": work_id,
            "family": payload.get("family"),
            "query_count": len(payload.get("queries") or []),
            "target_row_count": len(payload.get("target_row_ids") or []),
        })
    result = {
        "schema": "leanmill-external-source-search-recovery-v1",
        "generated_at_epoch": int(time.time()),
        "recovered": len(recovered),
        "skipped": skipped,
        "recovered_items": recovered,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_external_source_recovery_") as td:
        db = str(Path(td) / "q.sqlite")
        events = str(Path(td) / "events.jsonl")
        out = str(Path(td) / "out.json")
        cx = work_queue.connect(db)
        work_queue.record_terminal_item(
            cx,
            kind="source_search_task",
            status="retired",
            priority=1,
            payload={
                "work_id": "source_search:fam:external_source_scout_fam:0",
                "family": "fam",
                "parent_work_id": "agent_output_review:fam:external_source_scout:fam:codex:test",
                "queries": ["A.b", "C.d", "E.f"],
                "target_row_ids": ["R"],
            },
        )
        result = recover(argparse.Namespace(queue_db=db, events=events, out=out, limit=10, priority=92, max_attempts=2))
        assert result["recovered"] == 1
        row = cx.execute("SELECT status, payload_json FROM work_items WHERE kind='source_search_task'").fetchone()
        assert row["status"] == "queued"
        assert json.loads(row["payload_json"])["source_scout_mode"] == "subscription_public_external"
    print("leanmill_external_source_search_recovery self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--priority", type=int, default=92)
    ap.add_argument("--factory-policy", default=DEFAULT_FACTORY_POLICY)
    ap.add_argument("--max-attempts", type=int, default=2)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if int(args.priority) == 92:
        args.priority = _queue_priority(args, "external_source_search_recovery", 92)
    result = recover(args)
    print(json.dumps({"recovered": result["recovered"], "skipped": result["skipped"], "out": args.out}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
