#!/usr/bin/env python3
"""Dedicated upstream source-scout worker.

Live source-scout runtime choices come from ``profile.runner`` in the factory
policy. This station only claims ``source_scout_task`` work.
"""
from __future__ import annotations

import argparse
import json
import time
from argparse import Namespace
from typing import Any

import leanmill_agent_repair_worker as agent_worker
import leanmill_work_queue as work_queue
from leanmill_factory_config import FACTORY_POLICY as DEFAULT_FACTORY_POLICY, read_policy


def _runner_policy(args: argparse.Namespace) -> dict[str, Any]:
    profile_name = str(getattr(args, "policy_profile", "") or "")
    policy = read_policy(getattr(args, "factory_policy", DEFAULT_FACTORY_POLICY))
    profile = ((policy.get("profiles") or {}).get(profile_name) or {}) if profile_name else {}
    runner = profile.get("runner") if isinstance(profile, dict) else {}
    return runner if isinstance(runner, dict) else {}


def _int_value(obj: dict[str, Any], key: str, fallback: int) -> int:
    try:
        return int(obj.get(key) if obj.get(key) is not None else fallback)
    except (TypeError, ValueError):
        return int(fallback)


def _bool_value(obj: dict[str, Any], key: str, fallback: bool) -> bool:
    value = obj.get(key)
    if value is None:
        return fallback
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _agent_args(args: argparse.Namespace) -> Namespace:
    runner = _runner_policy(args)
    runtime = str(runner.get("source_agent_runtime") or runner.get("agent_default_runtime") or "codex")
    model = str(runner.get("source_agent_codex_model") or runner.get("agent_default_codex_model") or "gpt-5.4-mini")
    return Namespace(
        queue_db=args.queue_db,
        events=args.events,
        worker_id=args.worker_id,
        claim_kind=["source_scout_task"],
        claim_patch_mode=None,
        claim_work_id=None,
        claim_scan_limit=_int_value(runner, "source_scout_claim_scan_limit", 1000),
        claim_payload_eq=None,
        lease_s=_int_value(runner, "source_scout_lease_s", 1800),
        max_iterations=_int_value(runner, "source_agent_max_iterations", _int_value(runner, "agent_max_iterations", 3)),
        max_wall_time_s=_int_value(runner, "source_agent_max_wall_time_s", _int_value(runner, "agent_max_wall_time_s", 1200)),
        contract_dir=agent_worker.DEFAULT_CONTRACT_DIR,
        output_dir=agent_worker.DEFAULT_OUTPUT_DIR,
        session_dir=agent_worker.DEFAULT_SESSION_DIR,
        quarantine_dir=agent_worker.DEFAULT_QUARANTINE_DIR,
        family_activation_dir=agent_worker.DEFAULT_FAMILY_ACTIVATION_DIR,
        allocator=agent_worker.DEFAULT_ALLOCATOR,
        use_warm_session=True,
        warm_max_tasks=_int_value(runner, "source_agent_warm_max_tasks", 20),
        warm_max_age_s=_int_value(runner, "source_agent_warm_max_age_s", 6 * 60 * 60),
        allow_agent_launch=_bool_value(runner, "allow_agent_launch", False),
        default_runtime=runtime,
        default_codex_model=model,
        family_spec_patch_codex_model=str(runner.get("agent_family_spec_patch_codex_model") or "gpt-5.5"),
    )


def work_once(args: argparse.Namespace) -> dict[str, Any]:
    return agent_worker.work_once(_agent_args(args))


def daemon_loop(args: argparse.Namespace) -> dict[str, Any]:
    completed = 0
    idle_ticks = 0
    last: dict[str, Any] = {}
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

    original = agent_worker.work_once
    try:
        with tempfile.TemporaryDirectory(prefix="leanmill_source_scout_worker_") as td:
            policy = Path(td) / "policy.json"
            policy.write_text(json.dumps({
                "profiles": {
                    "p": {
                        "runner": {
                            "allow_agent_launch": True,
                            "source_agent_runtime": "codex",
                            "source_agent_codex_model": "gpt-5.4-mini",
                            "source_agent_max_iterations": 2,
                            "source_agent_max_wall_time_s": 30,
                        }
                    }
                }
            }) + "\n")
            seen: dict[str, Any] = {}

            def fake_work_once(ns: Namespace) -> dict[str, Any]:
                seen.update(vars(ns))
                return {"claimed": False}

            agent_worker.work_once = fake_work_once
            result = work_once(argparse.Namespace(
                queue_db=str(Path(td) / "queue.sqlite"),
                events=str(Path(td) / "events.jsonl"),
                worker_id="source-scout-test",
                factory_policy=str(policy),
                policy_profile="p",
            ))
            assert result["claimed"] is False
            assert seen["claim_kind"] == ["source_scout_task"], seen
            assert seen["allow_agent_launch"] is True, seen
            assert seen["max_iterations"] == 2 and seen["max_wall_time_s"] == 30, seen
            result2 = daemon_loop(argparse.Namespace(
                queue_db=str(Path(td) / "queue.sqlite"),
                events=str(Path(td) / "events.jsonl"),
                worker_id="source-scout-daemon-test",
                factory_policy=str(policy),
                policy_profile="p",
                max_tasks=0,
                max_idle_ticks=1,
                idle_sleep_s=1,
            ))
            assert result2["completed_tasks"] == 0, result2
    finally:
        agent_worker.work_once = original
    print("leanmill_source_scout_worker self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--worker-id", default="leanmill-source-scout-worker")
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
