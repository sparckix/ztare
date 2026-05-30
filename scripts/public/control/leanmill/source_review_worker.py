#!/usr/bin/env python3
"""Dedicated upstream source-review worker.

This station converts completed source-scout transcripts into typed
source_request proposals. It intentionally claims only source-review work so
upstream sourcing breadth is not starved by generic proposal/decomposition
backlog. Live enablement and budgets come from the runner policy profile.
"""
from __future__ import annotations

import json
import argparse
import time
from argparse import Namespace

import leanmill_llm_proposal_worker as proposal_worker
import leanmill_work_queue as work_queue
from leanmill_factory_config import FACTORY_POLICY as DEFAULT_FACTORY_POLICY, apply_profile_section


def _proposal_args(args: argparse.Namespace) -> Namespace:
    runtime = Namespace(
        queue_db=args.queue_db,
        events=args.events,
        worker_id=args.worker_id,
        lease_s=600,
        gate_out=proposal_worker.DEFAULT_PROPOSAL_GATE,
        trace_dir=proposal_worker.DEFAULT_TRACE_DIR,
        allocator=proposal_worker.DEFAULT_ALLOCATOR,
        factory_policy=args.factory_policy,
        policy_profile=args.policy_profile,
        allow_paid_llm=False,
        llm_max_total_cost_usd=0.0,
        llm_model_family="gpt4.1-mini",
        llm_max_output_tokens=1200,
        llm_timeout_s=180,
        llm_retries=1,
        allow_llm_codex_cli_fallback=False,
        llm_codex_cli_fallback_model="gpt-5.4-mini",
        llm_codex_cli_fallback_timeout_s=240,
        role_id="research_director",
        llm_session_id="leanmill_source_review",
    )
    apply_profile_section(runtime, section="runner")
    return Namespace(
        queue_db=runtime.queue_db,
        events=runtime.events,
        worker_id=runtime.worker_id,
        lease_s=runtime.lease_s,
        gate_out=runtime.gate_out,
        trace_dir=runtime.trace_dir,
        allocator=runtime.allocator,
        factory_policy=runtime.factory_policy,
        allow_paid_llm=bool(runtime.allow_paid_llm),
        max_total_cost_usd=float(runtime.llm_max_total_cost_usd or 0.0),
        model_family=str(runtime.llm_model_family or "gpt4.1-mini"),
        max_output_tokens=int(runtime.llm_max_output_tokens or 1200),
        timeout_s=int(runtime.llm_timeout_s or 180),
        retries=int(runtime.llm_retries or 1),
        allow_codex_cli_fallback=bool(runtime.allow_llm_codex_cli_fallback),
        codex_cli_fallback_model=str(runtime.llm_codex_cli_fallback_model or "gpt-5.4-mini"),
        codex_cli_fallback_timeout_s=int(runtime.llm_codex_cli_fallback_timeout_s or 240),
        role_id=str(runtime.role_id or "research_director"),
        session_id=str(runtime.llm_session_id or "leanmill_source_review"),
    )


def work_once(args: argparse.Namespace) -> dict[str, object]:
    return proposal_worker.work_once_source_review(_proposal_args(args))


def daemon_loop(args: argparse.Namespace) -> dict[str, object]:
    completed = 0
    idle_ticks = 0
    last: dict[str, object] = {}
    while True:
        if args.max_tasks and completed >= args.max_tasks:
            break
        result = work_once(args)
        last = result
        if result.get("claimed"):
            completed += 1
            idle_ticks = 0
            print(json.dumps({"daemon": args.worker_id, "task_result": result}, sort_keys=True), flush=True)
            continue
        idle_ticks += 1
        print(json.dumps({"daemon": args.worker_id, "idle": True, "idle_ticks": idle_ticks}, sort_keys=True), flush=True)
        if args.max_idle_ticks and idle_ticks >= args.max_idle_ticks:
            break
        time.sleep(max(1, int(args.idle_sleep_s)))
    return {"daemon": args.worker_id, "completed_tasks": completed, "last_result": last}


def _self_test() -> int:
    import tempfile
    from pathlib import Path

    original_gate = proposal_worker.proposal_gate
    try:
        with tempfile.TemporaryDirectory(prefix="leanmill_source_review_worker_") as td:
            root = Path(td)
            cx = work_queue.connect(str(root / "queue.sqlite"))
            work_queue.enqueue(cx, kind="decomposition_propose", priority=999, payload={"expected_outcome": "hold"})
            source_wid = work_queue.enqueue(cx, kind="llm_proposal_validate", priority=1, payload={
                "expected_outcome": "source_request",
                "source_agent_work_id": "source_scout",
                "allowed_proposal_types": ["source_request", "decomposition"],
            })

            def fake_gate(_args: argparse.Namespace, _payload: dict, _work_id: str) -> dict[str, object]:
                return {"ok": True, "model_called": False, "artifact_paths": [], "source_search_enqueued": []}

            proposal_worker.proposal_gate = fake_gate
            result = work_once(argparse.Namespace(
                queue_db=str(root / "queue.sqlite"),
                events=str(root / "events.jsonl"),
                worker_id="source-review-test",
                factory_policy=str(root / "policy.json"),
                policy_profile="",
            ))
            assert result["claimed"] is True and result["work_id"] == source_wid, result
            row = cx.execute("SELECT status FROM work_items WHERE work_id=?", (source_wid,)).fetchone()
            assert row and row["status"] == "done", row
            idle_result = daemon_loop(argparse.Namespace(
                queue_db=str(root / "queue.sqlite"),
                events=str(root / "events.jsonl"),
                worker_id="source-review-daemon-test",
                factory_policy=str(root / "policy.json"),
                policy_profile="",
                max_tasks=0,
                max_idle_ticks=1,
                idle_sleep_s=1,
            ))
            assert idle_result["completed_tasks"] == 0, idle_result
    finally:
        proposal_worker.proposal_gate = original_gate
    print("leanmill_source_review_worker self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--worker-id", default="leanmill-source-review-worker")
    ap.add_argument("--factory-policy", default=DEFAULT_FACTORY_POLICY)
    ap.add_argument("--policy-profile", default="")
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--idle-sleep-s", type=int, default=15)
    ap.add_argument("--max-tasks", type=int, default=0)
    ap.add_argument("--max-idle-ticks", type=int, default=0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    result = daemon_loop(args) if args.daemon else work_once(args)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok", True) is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
