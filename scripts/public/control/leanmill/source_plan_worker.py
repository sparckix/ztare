#!/usr/bin/env python3
"""Refresh residual-family source plans and canary packet inventory.

This worker turns a drained Residual Compiler station into fresh bounded work
inputs. It does not run Lean and it does not grant proof credit.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue


DEFAULT_DATA_DIR = "analytics/public/leanmill/dashboard_data"
DEFAULT_SOURCE_PLAN = f"{DEFAULT_DATA_DIR}/residual_family_source_plan.json"
DEFAULT_SOURCE_PLAN_MD = f"{DEFAULT_DATA_DIR}/residual_family_source_plan.md"
DEFAULT_CANARY_PACKETS = f"{DEFAULT_DATA_DIR}/residual_family_canary_packets.json"
DEFAULT_CONTRACT = f"{DEFAULT_DATA_DIR}/station_action_contract.json"


def _display_cmd(cmd: list[str]) -> list[str]:
    if cmd and Path(cmd[0]).resolve() == Path(sys.executable).resolve():
        return ["<python>", *cmd[1:]]
    return cmd


def _run(cmd: list[str], *, timeout_s: int) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=max(1, int(timeout_s)))
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": _display_cmd(cmd),
            "returncode": 124,
            "timed_out": True,
            "stdout_tail": (exc.stdout or "")[-2000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-2000:] if isinstance(exc.stderr, str) else "",
        }
    return {
        "cmd": _display_cmd(cmd),
        "returncode": proc.returncode,
        "timed_out": False,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def _read_json(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        obj = json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def refresh(args: argparse.Namespace) -> dict[str, Any]:
    py = sys.executable
    commands = [
        [
            py,
            "scripts/public/control/leanmill/search/residual_family_source_planner.py",
            "--out", args.source_plan,
            "--markdown", args.source_plan_md,
            "--canary-out", args.canary_packets,
            "--min-score", str(args.min_score),
            "--top-leads", str(args.top_leads),
            "--max-canary-rows", str(args.max_canary_rows),
            "--max-canary-leads", str(args.max_canary_leads),
        ],
        [
            py,
            "scripts/public/control/leanmill/station_action_contract.py",
            "--out", args.contract,
        ],
    ]
    results = [_run(cmd, timeout_s=args.command_timeout_s) for cmd in commands]
    ok = all(r["returncode"] == 0 for r in results)
    source_plan = _read_json(args.source_plan)
    canary = _read_json(args.canary_packets)
    return {
        "ok": ok,
        "results": results,
        "summary": {
            "families_with_leads": int(source_plan.get("families_with_leads") or 0),
            "total_leads": int((source_plan.get("summary") or {}).get("total_leads") or 0),
            "ready_packet_count": int(canary.get("ready_packet_count") or 0),
            "packet_count": int(canary.get("packet_count") or 0),
        },
    }


def work_once(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    item = work_queue.claim(
        cx,
        worker_id=args.worker_id,
        kinds=["residual_source_plan_refresh", "station:residual_curriculum"],
        lease_s=args.lease_s,
    )
    if not item:
        return {"claimed": False}
    work_queue.update_status(cx, work_id=item["work_id"], status="running")
    work_queue.append_event(args.events, {
        "event_type": "source_plan_worker_started",
        "work_id": item["work_id"],
        "payload": item,
    })
    result = refresh(args)
    status = "done" if result["ok"] else "failed"
    payload_update = {
        "result": result,
        "exit_kind": "residual_source_plan_refreshed" if result["ok"] else "residual_source_plan_refresh_failed",
        "expected_exit": "fresh_residual_family_source_plan",
    }
    work_queue.update_status(cx, work_id=item["work_id"], status=status, payload_update=payload_update)
    work_queue.append_event(args.events, {
        "event_type": f"source_plan_worker_{status}",
        "work_id": item["work_id"],
        "payload": payload_update,
        "artifact_paths": [args.source_plan, args.source_plan_md, args.canary_packets, args.contract],
    })
    return {"claimed": True, "work_id": item["work_id"], "status": status, "ok": result["ok"], "summary": result["summary"]}


def _self_test() -> int:
    assert DEFAULT_SOURCE_PLAN.endswith(".json")
    assert DEFAULT_CANARY_PACKETS.endswith(".json")
    print("leanmill_source_plan_worker self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--worker-id", default="source-plan-worker-local")
    ap.add_argument("--lease-s", type=int, default=600)
    ap.add_argument("--source-plan", default=DEFAULT_SOURCE_PLAN)
    ap.add_argument("--source-plan-md", default=DEFAULT_SOURCE_PLAN_MD)
    ap.add_argument("--canary-packets", default=DEFAULT_CANARY_PACKETS)
    ap.add_argument("--contract", default=DEFAULT_CONTRACT)
    ap.add_argument("--min-score", type=int, default=12)
    ap.add_argument("--top-leads", type=int, default=8)
    ap.add_argument("--max-canary-rows", type=int, default=3)
    ap.add_argument("--max-canary-leads", type=int, default=3)
    ap.add_argument("--command-timeout-s", type=int, default=180)
    ap.add_argument("--refresh-only", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    result = refresh(args) if args.refresh_only else work_once(args)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok", True) is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
