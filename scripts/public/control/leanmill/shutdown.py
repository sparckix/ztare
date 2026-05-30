#!/usr/bin/env python3
"""Stop the local tmux-based LeanMill factory and keep it stopped.

The shutdown path writes a marker before killing sessions. The watchdog honors
that marker and will not restart workers until the marker is cleared.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

import leanmill_watchdog
import leanmill_work_queue as work_queue
from leanmill_factory_config import read_policy
from leanmill_paths import DATA_DIR as LEANMILL_DATA_DIR


DATA_DIR = Path(LEANMILL_DATA_DIR)
DEFAULT_OUT = DATA_DIR / "leanmill_shutdown_status.json"
DEFAULT_MARKER = leanmill_watchdog.DEFAULT_SHUTDOWN_MARKER
DASHBOARD_SESSIONS = ["gp225_factory_dashboard_refresh", "gp225_factory_dashboard_server"]
REPO_ROOT = Path(__file__).resolve().parents[4]
LEAN_REPL_MARKER = str(REPO_ROOT / "vendor" / "lean_repl")


def _run(cmd: list[str], *, timeout_s: int = 30) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": cmd,
            "returncode": 124,
            "timed_out": True,
            "stdout_tail": (exc.stdout or "")[-1000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-1000:] if isinstance(exc.stderr, str) else "",
        }
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "timed_out": False,
        "stdout_tail": proc.stdout[-1000:],
        "stderr_tail": proc.stderr[-1000:],
    }


def _tmux_has_session(name: str) -> bool:
    proc = subprocess.run(["tmux", "has-session", "-t", name], text=True, capture_output=True)
    return proc.returncode == 0


def _tmux_sessions() -> list[str]:
    proc = subprocess.run(["tmux", "ls"], text=True, capture_output=True)
    if proc.returncode != 0:
        return []
    out: list[str] = []
    for line in proc.stdout.splitlines():
        name = line.split(":", 1)[0].strip()
        if name:
            out.append(name)
    return out


def _wait_for_session_stop(name: str, *, grace_s: int) -> bool:
    deadline = time.time() + max(0, int(grace_s))
    while time.time() < deadline:
        if not _tmux_has_session(name):
            return True
        time.sleep(0.5)
    return not _tmux_has_session(name)


def _stop_session(name: str, *, grace_s: int) -> dict[str, Any]:
    graceful = _run(["tmux", "send-keys", "-t", name, "C-c"], timeout_s=5)
    if graceful["returncode"] == 0 and _wait_for_session_stop(name, grace_s=grace_s):
        return {"action": "stopped_gracefully", "graceful_signal": graceful}
    kill = _run(["tmux", "kill-session", "-t", name])
    return {
        "action": "stopped" if kill["returncode"] == 0 else "stop_failed",
        "graceful_signal": graceful,
        "kill_result": kill,
    }


def _session_names(*, include_dashboard: bool) -> list[str]:
    names = ["leanmill_watchdog"]
    policy = read_policy()
    profiles = sorted((policy.get("profiles") or {}).keys())
    if not profiles:
        profiles = [leanmill_watchdog.DEFAULT_POLICY_PROFILE]
    for profile in profiles:
        names.extend(s["name"] for s in leanmill_watchdog._sessions(str(profile)))
    for name in _tmux_sessions():
        if name.startswith("leanmill_"):
            names.append(name)
    if include_dashboard:
        names.extend(DASHBOARD_SESSIONS)
    seen: set[str] = set()
    ordered: list[str] = []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered


def _process_table() -> dict[int, dict[str, Any]]:
    proc = subprocess.run(["ps", "-Ao", "pid=,ppid=,pgid=,sid=,stat=,command="], text=True, capture_output=True)
    if proc.returncode != 0:
        return {}
    rows: dict[int, dict[str, Any]] = {}
    for line in proc.stdout.splitlines():
        parts = line.strip().split(None, 5)
        if len(parts) < 6:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
            pgid = int(parts[2])
            sid = int(parts[3])
        except ValueError:
            continue
        rows[pid] = {"pid": pid, "ppid": ppid, "pgid": pgid, "sid": sid, "stat": parts[4], "command": parts[5]}
    return rows


LEANMILL_LONG_RUNNING_MARKERS = (
    "scripts/public/control/leanmill/c_supply_batch.py",
    "scripts/public/control/leanmill/c_supply_growth_controller.py",
    "scripts/public/control/leanmill/c_static_sweep_backfill.py",
    "scripts/public/control/leanmill/static_failure_miner.py",
    "scripts/public/control/leanmill/c_supply_template_backfill.py",
    "scripts/public/control/leanmill/learning_work_seeder.py",
    "scripts/public/control/leanmill/source_binding_probe_worker.py",
    "/tmp/rung1/leanmill_c_supply_growth_controller/",
)


def _leanmill_process_group_cleanup_candidates(rows: dict[int, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = rows or _process_table()
    current_pid = os.getpid()
    current_pgid = os.getpgrp()
    candidates: dict[int, dict[str, Any]] = {}
    for row in rows.values():
        pid = int(row.get("pid") or 0)
        pgid = int(row.get("pgid") or 0)
        if pid <= 1 or pgid <= 1 or pid == current_pid or pgid == current_pgid:
            continue
        cmd = str(row.get("command") or "")
        if not any(marker in cmd for marker in LEANMILL_LONG_RUNNING_MARKERS):
            continue
        group_rows = [member for member in rows.values() if int(member.get("pgid") or 0) == pgid]
        candidates[pgid] = {
            "pgid": pgid,
            "sample_pid": pid,
            "process_count": len(group_rows),
            "commands": [str(member.get("command") or "") for member in group_rows[:5]],
        }
    return [candidates[pgid] for pgid in sorted(candidates)]


def _cleanup_leanmill_process_groups(*, enabled: bool, dry_run: bool, term_wait_s: float = 1.0) -> dict[str, Any]:
    if not enabled:
        return {"enabled": False, "candidate_group_count": 0, "terminated_group_count": 0, "killed_group_count": 0, "candidates": []}
    candidates = _leanmill_process_group_cleanup_candidates()
    pgids = [int(row["pgid"]) for row in candidates]
    if dry_run or not pgids:
        return {
            "enabled": True,
            "dry_run": bool(dry_run),
            "candidate_group_count": len(candidates),
            "terminated_group_count": 0,
            "killed_group_count": 0,
            "candidates": candidates[:20],
        }
    terminated = 0
    killed = 0
    for pgid in pgids:
        try:
            os.killpg(pgid, signal.SIGTERM)
            terminated += 1
        except (ProcessLookupError, PermissionError):
            continue
    time.sleep(max(0.0, float(term_wait_s)))
    remaining_pgids = {int(row.get("pgid") or 0) for row in _process_table().values()}
    for pgid in pgids:
        if pgid not in remaining_pgids:
            continue
        try:
            os.killpg(pgid, signal.SIGKILL)
            killed += 1
        except (ProcessLookupError, PermissionError):
            continue
    return {
        "enabled": True,
        "dry_run": False,
        "candidate_group_count": len(candidates),
        "terminated_group_count": terminated,
        "killed_group_count": killed,
        "candidates": candidates[:20],
    }


def _leanmill_repl_cleanup_candidates() -> list[dict[str, Any]]:
    rows = _process_table()
    candidates: dict[int, dict[str, Any]] = {}
    for row in rows.values():
        cmd = str(row.get("command") or "")
        if LEAN_REPL_MARKER not in cmd:
            continue
        chain = [int(row["pid"])]
        parent_pid = int(row.get("ppid") or 0)
        while parent_pid > 1 and parent_pid in rows:
            parent = rows[parent_pid]
            parent_cmd = str(parent.get("command") or "")
            if "multiprocessing.spawn" in parent_cmd or "leansearch_repair_canary_drain.py" in parent_cmd or LEAN_REPL_MARKER in parent_cmd:
                chain.append(parent_pid)
                parent_pid = int(parent.get("ppid") or 0)
                continue
            break
        for pid in chain:
            proc_row = rows.get(pid)
            if proc_row:
                candidates[pid] = proc_row
    return [candidates[pid] for pid in sorted(candidates)]


def _cleanup_lean_repl_processes(*, enabled: bool, dry_run: bool, term_wait_s: float = 1.0) -> dict[str, Any]:
    if not enabled:
        return {"enabled": False, "candidate_count": 0, "terminated_count": 0, "killed_count": 0, "candidates": []}
    candidates = _leanmill_repl_cleanup_candidates()
    pids = [int(row["pid"]) for row in candidates]
    if dry_run or not pids:
        return {
            "enabled": True,
            "dry_run": bool(dry_run),
            "candidate_count": len(candidates),
            "terminated_count": 0,
            "killed_count": 0,
            "candidates": candidates[:20],
        }
    terminated = 0
    killed = 0
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            terminated += 1
        except ProcessLookupError:
            continue
        except PermissionError:
            continue
    time.sleep(max(0.0, float(term_wait_s)))
    remaining = _process_table()
    for pid in pids:
        if pid not in remaining:
            continue
        try:
            os.kill(pid, signal.SIGKILL)
            killed += 1
        except (ProcessLookupError, PermissionError):
            continue
    return {
        "enabled": True,
        "dry_run": False,
        "candidate_count": len(candidates),
        "terminated_count": terminated,
        "killed_count": killed,
        "candidates": candidates[:20],
    }


def shutdown(args: argparse.Namespace) -> dict[str, Any]:
    marker = Path(args.marker)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker_payload = {
        "schema": "leanmill-shutdown-request-v1",
        "created_at_epoch": int(time.time()),
        "reason": args.reason,
        "operator": args.operator,
        "dry_run": bool(args.dry_run),
    }
    if not args.dry_run:
        marker.write_text(json.dumps(marker_payload, indent=2, sort_keys=True) + "\n")

    actions: list[dict[str, Any]] = []
    for name in _session_names(include_dashboard=args.include_dashboard):
        alive = _tmux_has_session(name)
        if not alive:
            actions.append({"name": name, "action": "already_stopped"})
            continue
        if args.dry_run:
            actions.append({"name": name, "action": "would_stop"})
            continue
        result = _stop_session(name, grace_s=args.grace_s)
        actions.append({
            "name": name,
            **result,
        })

    cleanup_orphan_repl = args.cleanup_orphan_repl
    if cleanup_orphan_repl is None:
        policy = read_policy()
        ops = policy.get("operations") if isinstance(policy, dict) else {}
        cleanup_orphan_repl = bool((ops if isinstance(ops, dict) else {}).get("shutdown_cleanup_orphan_repl", True))
    cleanup_process_groups = args.cleanup_process_groups
    if cleanup_process_groups is None:
        policy = read_policy()
        ops = policy.get("operations") if isinstance(policy, dict) else {}
        cleanup_process_groups = bool((ops if isinstance(ops, dict) else {}).get("shutdown_cleanup_process_groups", True))
    process_group_cleanup = _cleanup_leanmill_process_groups(enabled=bool(cleanup_process_groups), dry_run=bool(args.dry_run))
    orphan_repl_cleanup = _cleanup_lean_repl_processes(enabled=bool(cleanup_orphan_repl), dry_run=bool(args.dry_run))

    cx = work_queue.connect(args.queue_db)
    reclaimed_open_claims = 0
    if not args.dry_run and args.reclaim_open_claims:
        reclaimed_open_claims = work_queue.reclaim_all_open_claims(
            cx,
            events_path=args.events,
            reason="leanmill_shutdown",
        )
    expired_reclaimed = work_queue.reclaim_expired(cx, events_path=args.events) if not args.dry_run else 0
    queue_stats = work_queue.stats(cx)
    open_stats = work_queue.open_stats(cx)
    status = {
        "schema": "leanmill-shutdown-status-v1",
        "generated_at_epoch": int(time.time()),
        "dry_run": bool(args.dry_run),
        "marker": str(marker),
        "marker_written": marker.exists() if not args.dry_run else False,
        "actions": actions,
        "stopped_count": sum(1 for a in actions if a.get("action") in {"stopped", "stopped_gracefully"}),
        "stopped_gracefully_count": sum(1 for a in actions if a.get("action") == "stopped_gracefully"),
        "failed_stop_count": sum(1 for a in actions if a.get("action") == "stop_failed"),
        "reclaimed_open_claim_count": reclaimed_open_claims,
        "expired_lease_reclaimed_count": expired_reclaimed,
        "process_group_cleanup": process_group_cleanup,
        "orphan_repl_cleanup": orphan_repl_cleanup,
        "queue": queue_stats,
        "open_queue": open_stats,
        "restart_instruction": f"clear marker {marker} before restarting watchdog/factory",
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
    work_queue.append_event(args.events, {
        "event_type": "leanmill_shutdown_requested",
        "payload": {
            "dry_run": bool(args.dry_run),
            "stopped_count": status["stopped_count"],
            "failed_stop_count": status["failed_stop_count"],
            "marker": str(marker),
            "reason": args.reason,
        },
        "artifact_paths": [str(args.out), str(marker)],
    })
    return status


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_shutdown_") as td:
        result = shutdown(argparse.Namespace(
            dry_run=True,
            include_dashboard=False,
            marker=str(Path(td) / "shutdown.json"),
            out=str(Path(td) / "shutdown_status.json"),
            queue_db=str(Path(td) / "q.sqlite"),
            events=str(Path(td) / "events.jsonl"),
            reason="self_test",
            operator="self_test",
            grace_s=0,
            reclaim_open_claims=True,
            cleanup_orphan_repl=False,
            cleanup_process_groups=True,
        ))
        assert result["schema"] == "leanmill-shutdown-status-v1"
        assert result["failed_stop_count"] == 0
        assert Path(result["marker"]).exists() is False
        fake_rows = {
            10: {"pid": 10, "ppid": 1, "pgid": 10, "sid": 10, "stat": "Ss", "command": "/venv/bin/python scripts/public/control/leanmill/c_supply_growth_controller.py --allow-heavy-lean"},
            11: {"pid": 11, "ppid": 10, "pgid": 11, "sid": 11, "stat": "Ss", "command": "/venv/bin/python scripts/public/control/leanmill/c_static_sweep_backfill.py --run-root /tmp/rung1/leanmill_c_supply_growth_controller/x"},
            12: {"pid": 12, "ppid": 11, "pgid": 11, "sid": 11, "stat": "Sl", "command": "lake env lean /tmp/rung1/leanmill_c_supply_growth_controller/x/candidate.lean"},
            13: {"pid": 13, "ppid": 1, "pgid": 13, "sid": 13, "stat": "S", "command": "/venv/bin/python scripts/public/control/leanmill/c_supply_batch.py --run-id self_correct_x"},
            14: {"pid": 14, "ppid": 1, "pgid": 14, "sid": 14, "stat": "S", "command": "unrelated"},
        }
        groups = _leanmill_process_group_cleanup_candidates(fake_rows)
        assert [g["pgid"] for g in groups] == [10, 11, 13], groups
    print("leanmill_shutdown self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--marker", default=str(DEFAULT_MARKER))
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--reason", default="operator_requested")
    ap.add_argument("--operator", default="local_operator")
    ap.add_argument("--include-dashboard", action="store_true")
    ap.add_argument("--grace-s", type=int, default=8)
    ap.add_argument("--reclaim-open-claims", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--cleanup-orphan-repl", action=argparse.BooleanOptionalAction, default=None)
    ap.add_argument("--cleanup-process-groups", action=argparse.BooleanOptionalAction, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    print(json.dumps(shutdown(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
