#!/usr/bin/env python3
"""Keep the external source-scout queue at the policy floor.

This is a producer daemon only. It emits source_scout_task inventory work via
the existing external-source seeder; it grants no proof, benchmark, governance,
or C credit.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import leanmill_external_source_scout_seeder as seeder
import leanmill_work_queue as work_queue
from leanmill_factory_config import FACTORY_POLICY, read_policy
from leanmill_paths import DATA_DIR


DEFAULT_OUT = f"{DATA_DIR}/external_source_scout_release_daemon.json"
DEFAULT_SEED_PLAN = f"{DATA_DIR}/external_source_scout_seed_plan.json"
DEFAULT_ANDON = f"{DATA_DIR}/leanmill_andon_cord.json"


def _read_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {}
    try:
        obj = json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _int_value(obj: dict[str, Any], key: str, default: int) -> int:
    try:
        return int(obj.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def _runner_policy(args: argparse.Namespace) -> dict[str, Any]:
    profile_name = str(getattr(args, "policy_profile", "") or "")
    policy = read_policy(getattr(args, "factory_policy", FACTORY_POLICY))
    profile = ((policy.get("profiles") or {}).get(profile_name) or {}) if isinstance(policy.get("profiles"), dict) else {}
    runner = profile.get("runner") if isinstance(profile, dict) else {}
    runner = runner if isinstance(runner, dict) else {}
    return {
        "schema": "leanmill-external-source-release-policy-v1",
        "source": "factory_policy.profile.runner",
        "policy_profile": profile_name,
        "enabled": bool(runner.get("external_source_scout_release_daemon", runner.get("seed_external_source_scouts", True))),
        "seed_external_source_scouts": bool(runner.get("seed_external_source_scouts", True)),
        "external_source_scout_floor": max(0, _int_value(runner, "external_source_scout_floor", 4)),
        "external_source_scout_max_enqueued": max(0, _int_value(runner, "external_source_scout_max_enqueued", 4)),
        "external_source_scout_avoid_open_family_duplicates": bool(runner.get("external_source_scout_avoid_open_family_duplicates", True)),
        "idle_sleep_s": max(1, _int_value(runner, "external_source_scout_release_idle_s", int(getattr(args, "idle_sleep_s", 60)))),
        "credit_boundary": "Maintains source_scout_task inventory only; downstream source search, probes, and governance own truth.",
    }


def _open_source_scout_count(queue_db: str | Path) -> int:
    cx = work_queue.connect(str(queue_db))
    try:
        row = cx.execute(
            "SELECT COUNT(*) AS n FROM work_items WHERE kind='source_scout_task' AND status IN ('queued','running')"
        ).fetchone()
        return int(row["n"] if row is not None else 0)
    finally:
        cx.close()


def _paused_by_andon(andon_path: str | Path) -> bool:
    andon = _read_json(andon_path)
    containment = andon.get("containment") if isinstance(andon.get("containment"), dict) else {}
    return bool(
        andon.get("pause_external_source_scouts")
        or containment.get("pause_external_source_scouts")
    )


def run_once(args: argparse.Namespace) -> dict[str, Any]:
    policy = _runner_policy(args)
    paused = _paused_by_andon(args.andon_cord)
    open_before = _open_source_scout_count(args.queue_db)
    target = 0 if paused else int(policy["external_source_scout_floor"])
    needed = max(0, target - open_before)
    max_enqueued = min(int(policy["external_source_scout_max_enqueued"]), needed)
    result: dict[str, Any] = {
        "schema": "leanmill-external-source-scout-release-daemon-v1",
        "generated_at_epoch": int(time.time()),
        "worker_id": args.worker_id,
        "policy": policy,
        "paused_by_andon": paused,
        "open_before": open_before,
        "target": target,
        "needed": needed,
        "max_enqueued": max_enqueued,
        "seed_result": {"skipped": True, "reason": "not_needed"},
        "proof_credit": "none_source_inventory_only",
    }
    if not policy["enabled"] or not policy["seed_external_source_scouts"]:
        result["seed_result"] = {"skipped": True, "reason": "policy_disabled"}
    elif paused:
        result["seed_result"] = {"skipped": True, "reason": "andon_pause_external_source_scouts"}
    elif max_enqueued > 0:
        seed_args = argparse.Namespace(
            allocator=args.allocator,
            source_plan=args.source_plan,
            benchmark_prep=args.benchmark_prep,
            corpus=args.corpus,
            extra_corpus=list(args.extra_corpus or []),
            out=args.seed_plan_out,
            queue_db=args.queue_db,
            events=args.events,
            run_id=f"{args.run_id_prefix}_{int(time.time())}",
            runtimes=args.runtimes,
            max_families=args.max_families,
            tasks_per_family=args.tasks_per_family,
            max_target_rows=args.max_target_rows,
            priority=args.priority,
            factory_policy=args.factory_policy,
            policy_profile=args.policy_profile,
            enqueue=True,
            max_enqueued=max_enqueued,
            agent_max_iterations=args.agent_max_iterations,
            agent_max_wall_time_s=args.agent_max_wall_time_s,
            avoid_open_family_duplicates=bool(policy["external_source_scout_avoid_open_family_duplicates"]),
        )
        seeder._apply_policy_profile(seed_args)
        if int(seed_args.priority) == 160:
            seed_args.priority = seeder._queue_priority(seed_args, "external_source_scout_seed", 160)
        seed = seeder.build(seed_args)
        result["seed_result"] = {
            "skipped": False,
            "out": args.seed_plan_out,
            "job_count": seed.get("job_count"),
            "enqueued": seed.get("enqueued", 0),
            "skipped_existing": seed.get("skipped_existing", 0),
            "enqueued_jobs": seed.get("enqueued_jobs", []),
            "anti_laundering_rule": seed.get("anti_laundering_rule"),
        }
    result["open_after"] = _open_source_scout_count(args.queue_db)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    cx = work_queue.connect(args.queue_db)
    try:
        work_queue.record_worker_heartbeat(
            cx,
            worker_id=args.worker_id,
            worker_kind="external_source_scout_release_daemon",
            policy_profile=str(args.policy_profile or ""),
            payload={
                "open_before": result["open_before"],
                "open_after": result["open_after"],
                "needed": result["needed"],
                "seed_result": result["seed_result"],
            },
        )
    finally:
        cx.close()
    return result


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_source_release_") as td:
        root = Path(td)
        allocator = root / "allocator.json"
        source_plan = root / "source_plan.json"
        benchmark = root / "benchmark.json"
        corpus = root / "corpus.json"
        policy = root / "policy.json"
        db = root / "q.sqlite"
        events = root / "events.jsonl"
        out = root / "release.json"
        seed = root / "seed.json"
        andon = root / "andon.json"
        allocator.write_text(json.dumps({"allocations": [{"family": "ennreal_tsum_condensation_planner", "yield_score": 10}]}) + "\n")
        source_plan.write_text(json.dumps({"packets": [{"repair_family": "ennreal_tsum_condensation_planner", "rows": ["MCB_A"]}]}) + "\n")
        benchmark.write_text(json.dumps({"tiers": {}}) + "\n")
        corpus.write_text(json.dumps({"rows": [{"row_id": "MCB_A", "goal": "ENNReal tsum", "source_file": "active.lean"}]}) + "\n")
        policy.write_text(json.dumps({
            "profiles": {
                "unit": {
                    "runner": {
                        "external_source_scout_release_daemon": True,
                        "seed_external_source_scouts": True,
                        "external_source_scout_floor": 2,
                        "external_source_scout_max_enqueued": 2,
                        "external_source_scout_max_families": 1,
                        "external_source_scout_runtimes": "codex,claude",
                        "external_source_scout_tasks_per_family": 2,
                    }
                }
            }
        }) + "\n")
        ns = argparse.Namespace(
            allocator=str(allocator),
            source_plan=str(source_plan),
            benchmark_prep=str(benchmark),
            corpus=str(corpus),
            extra_corpus=[],
            out=str(out),
            seed_plan_out=str(seed),
            queue_db=str(db),
            events=str(events),
            andon_cord=str(andon),
            factory_policy=str(policy),
            policy_profile="unit",
            worker_id="unit-release",
            run_id_prefix="unit",
            runtimes="codex,claude",
            max_families=8,
            tasks_per_family=2,
            max_target_rows=8,
            priority=160,
            agent_max_iterations=3,
            agent_max_wall_time_s=1200,
            avoid_open_family_duplicates=True,
            idle_sleep_s=60,
        )
        first = run_once(ns)
        assert first["seed_result"]["enqueued"] == 2, first
        second = run_once(ns)
        assert second["seed_result"]["reason"] == "not_needed", second
        andon.write_text(json.dumps({"containment": {"pause_external_source_scouts": True}}) + "\n")
        third = run_once(ns)
        assert third["seed_result"]["reason"] == "andon_pause_external_source_scouts", third
    print("leanmill_external_source_scout_release_daemon self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--allocator", default=seeder.DEFAULT_ALLOCATOR)
    ap.add_argument("--source-plan", default=seeder.DEFAULT_SOURCE_PLAN)
    ap.add_argument("--benchmark-prep", default=seeder.DEFAULT_BENCHMARK_PREP)
    ap.add_argument("--corpus", default=seeder.DEFAULT_CORPUS)
    ap.add_argument("--extra-corpus", action="append", default=list(seeder.DEFAULT_EXTRA_CORPUS))
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--seed-plan-out", default=DEFAULT_SEED_PLAN)
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--andon-cord", default=DEFAULT_ANDON)
    ap.add_argument("--factory-policy", default=FACTORY_POLICY)
    ap.add_argument("--policy-profile", default="")
    ap.add_argument("--worker-id", default="leanmill-source-release-daemon")
    ap.add_argument("--run-id-prefix", default="source_release")
    ap.add_argument("--runtimes", default="codex,claude")
    ap.add_argument("--max-families", type=int, default=8)
    ap.add_argument("--tasks-per-family", type=int, default=2)
    ap.add_argument("--max-target-rows", type=int, default=8)
    ap.add_argument("--avoid-open-family-duplicates", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--priority", type=int, default=160)
    ap.add_argument("--agent-max-iterations", type=int, default=3)
    ap.add_argument("--agent-max-wall-time-s", type=int, default=1200)
    ap.add_argument("--idle-sleep-s", type=int, default=60)
    ap.add_argument("--max-cycles", type=int, default=0)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    cycle = 0
    while True:
        result = run_once(args)
        print(json.dumps({
            "open_before": result["open_before"],
            "open_after": result["open_after"],
            "needed": result["needed"],
            "seed_result": result["seed_result"],
            "out": args.out,
        }, sort_keys=True), flush=True)
        cycle += 1
        if not args.daemon or (args.max_cycles and cycle >= args.max_cycles):
            break
        time.sleep(max(1, int(_runner_policy(args)["idle_sleep_s"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
