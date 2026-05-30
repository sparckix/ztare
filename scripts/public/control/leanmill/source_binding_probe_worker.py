#!/usr/bin/env python3
"""Dedicated source-binding probe worker.

This station spends heavy Lean only on ``repair_canary_probe`` items whose
payload declares ``probe_lane=source_binding``. Runtime choices come from the
factory policy profile; the live launcher passes only plumbing paths.
"""
from __future__ import annotations

import argparse
import json
import time
from argparse import Namespace
from typing import Any

import leanmill_probe_worker as probe_worker
import leanmill_work_queue as work_queue
from leanmill_factory_config import FACTORY_POLICY as DEFAULT_FACTORY_POLICY, read_policy


def _profile_sections(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    profile_name = str(getattr(args, "policy_profile", "") or "")
    policy = read_policy(getattr(args, "factory_policy", DEFAULT_FACTORY_POLICY))
    profile = ((policy.get("profiles") or {}).get(profile_name) or {}) if profile_name else {}
    if not isinstance(profile, dict):
        profile = {}
    runner = profile.get("runner") if isinstance(profile.get("runner"), dict) else {}
    probe = profile.get("probe_worker") if isinstance(profile.get("probe_worker"), dict) else {}
    return runner, probe


def _int_value(*objs: dict[str, Any], key: str, fallback: int) -> int:
    for obj in objs:
        if not isinstance(obj, dict) or obj.get(key) is None:
            continue
        try:
            return int(obj.get(key))
        except (TypeError, ValueError):
            continue
    return int(fallback)


def _bool_value(*objs: dict[str, Any], key: str, fallback: bool) -> bool:
    for obj in objs:
        if not isinstance(obj, dict) or obj.get(key) is None:
            continue
        value = obj.get(key)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
    return bool(fallback)


def _str_value(*objs: dict[str, Any], key: str, fallback: str) -> str:
    for obj in objs:
        if isinstance(obj, dict) and obj.get(key) is not None:
            return str(obj.get(key))
    return str(fallback)


def _probe_args(args: argparse.Namespace) -> Namespace:
    runner, probe = _profile_sections(args)
    source_binding_enabled = _int_value(runner, key="source_binding_probe_worker_passes", fallback=0) > 0
    allow_heavy = _bool_value(runner, key="allow_heavy_lean", fallback=False) and source_binding_enabled
    allow_heavy = _bool_value(runner, key="source_binding_probe_allow_heavy_lean", fallback=allow_heavy)
    return Namespace(
        factory_policy=args.factory_policy,
        policy_profile=args.policy_profile,
        queue_db=args.queue_db,
        events=args.events,
        worker_id=args.worker_id,
        lease_s=_int_value(runner, key="source_binding_probe_lease_s", fallback=3600),
        claim_station_residual=False,
        probe_lane=["source_binding"],
        family_spec_selection="",
        exclude_probe_lane=[],
        claim_work_id=None,
        claim_scan_limit=_int_value(runner, key="source_binding_probe_claim_scan_limit", fallback=1000),
        allow_heavy_lean=allow_heavy,
        backend=_str_value(runner, probe, key="source_binding_probe_backend", fallback=_str_value(probe, key="backend", fallback="repl_file")),
        timeout=_int_value(runner, probe, key="source_binding_probe_timeout", fallback=_int_value(probe, key="timeout", fallback=120)),
        test_wall_timeout=_int_value(runner, probe, key="source_binding_probe_test_wall_timeout", fallback=_int_value(probe, key="test_wall_timeout", fallback=180)),
        command_timeout_s=_int_value(runner, probe, key="source_binding_probe_command_timeout_s", fallback=_int_value(probe, key="command_timeout_s", fallback=1200)),
        max_candidates=_int_value(runner, probe, key="source_binding_probe_max_candidates", fallback=_int_value(probe, key="max_candidates", fallback=1)),
        max_actions=_int_value(runner, probe, key="source_binding_probe_max_actions", fallback=_int_value(probe, key="max_actions", fallback=1)),
        limit=_int_value(runner, probe, key="source_binding_probe_limit", fallback=_int_value(probe, key="limit", fallback=1)),
        govern_winners=_bool_value(runner, probe, key="source_binding_probe_govern_winners", fallback=_bool_value(probe, key="govern_winners", fallback=True)),
        scoreboard="/tmp/rung1/leanmill_source_binding_probe_scoreboard.json",
        cache_dir=_str_value(runner, probe, key="source_binding_probe_cache_dir", fallback=_str_value(probe, key="cache_dir", fallback="/tmp/rung1/leanmill_canary_result_cache")),
        no_cache=_bool_value(runner, probe, key="source_binding_probe_no_cache", fallback=_bool_value(probe, key="no_cache", fallback=False)),
        lean_slot_lock=_str_value(runner, probe, key="source_binding_probe_lean_slot_lock", fallback=_str_value(probe, key="lean_slot_lock", fallback="/tmp/rung1/leanmill_heavy_lean.lock")),
        no_lean_slot_lock=_bool_value(runner, probe, key="source_binding_probe_no_lean_slot_lock", fallback=_bool_value(probe, key="no_lean_slot_lock", fallback=False)),
        warm_repl_inline=_bool_value(runner, probe, key="source_binding_probe_warm_repl_inline", fallback=_bool_value(probe, key="warm_repl_inline", fallback=True)),
        daemon=False,
        idle_sleep_s=15,
        max_tasks=0,
        max_idle_ticks=0,
    )


def work_once(args: argparse.Namespace) -> dict[str, Any]:
    return probe_worker.work_once(_probe_args(args))


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

    original = probe_worker.work_once
    try:
        with tempfile.TemporaryDirectory(prefix="leanmill_source_binding_probe_worker_") as td:
            policy = Path(td) / "policy.json"
            policy.write_text(json.dumps({
                "profiles": {
                    "p": {
                        "runner": {
                            "allow_heavy_lean": True,
                            "source_binding_probe_worker_passes": 1,
                            "source_binding_probe_claim_scan_limit": 77,
                            "source_binding_probe_govern_winners": True,
                        },
                        "probe_worker": {
                            "backend": "repl_file",
                            "limit": 2,
                            "warm_repl_inline": True,
                        },
                    }
                }
            }) + "\n")
            seen: dict[str, Any] = {}

            def fake_work_once(ns: Namespace) -> dict[str, Any]:
                seen.update(vars(ns))
                return {"claimed": False}

            probe_worker.work_once = fake_work_once
            result = work_once(argparse.Namespace(
                queue_db=str(Path(td) / "queue.sqlite"),
                events=str(Path(td) / "events.jsonl"),
                worker_id="source-binding-probe-test",
                factory_policy=str(policy),
                policy_profile="p",
            ))
            assert result["claimed"] is False
            assert seen["probe_lane"] == ["source_binding"], seen
            assert seen["allow_heavy_lean"] is True, seen
            assert seen["claim_scan_limit"] == 77, seen
            assert seen["govern_winners"] is True, seen
            idle_result = daemon_loop(argparse.Namespace(
                queue_db=str(Path(td) / "queue.sqlite"),
                events=str(Path(td) / "events.jsonl"),
                worker_id="source-binding-probe-daemon-test",
                factory_policy=str(policy),
                policy_profile="p",
                max_tasks=0,
                max_idle_ticks=1,
                idle_sleep_s=1,
            ))
            assert idle_result["completed_tasks"] == 0, idle_result
    finally:
        probe_worker.work_once = original
    print("leanmill_source_binding_probe_worker self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--worker-id", default="leanmill-source-binding-probe-worker")
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
