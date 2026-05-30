#!/usr/bin/env python3
"""Deterministic source-inventory worker for LeanMill."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue


DEFAULT_INVENTORY = "analytics/public/leanmill/dashboard_data/source_inventory.json"
DEFAULT_INVENTORY_MD = "analytics/public/leanmill/dashboard_data/source_inventory.md"


def _display_cmd(cmd: list[str]) -> list[str]:
    if cmd and Path(cmd[0]).resolve() == Path(sys.executable).resolve():
        return ["<python>", *cmd[1:]]
    return cmd


def _run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    return {
        "cmd": _display_cmd(cmd),
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def refresh_inventory(args: argparse.Namespace) -> dict[str, Any]:
    py = sys.executable
    cmd = [
        py,
        "scripts/public/control/leanmill/source_inventory.py",
        "--out", args.inventory,
        "--md", args.inventory_md,
    ]
    if args.max_files:
        cmd.extend(["--max-files", str(args.max_files)])
    result = _run(cmd)
    ok = result["returncode"] == 0
    summary: dict[str, Any] = {}
    if ok and Path(args.inventory).exists():
        try:
            summary = json.loads(Path(args.inventory).read_text(errors="ignore")).get("summary") or {}
        except json.JSONDecodeError:
            summary = {}
    return {"ok": ok, "result": result, "summary": summary}


def work_once(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    reclaimed = work_queue.reclaim_worker_claims(cx, worker_id=args.worker_id)
    if reclaimed:
        work_queue.append_event(args.events, {
            "event_type": "source_worker_startup_reclaimed_own_claims",
            "work_id": f"{args.worker_id}:startup_reclaim",
            "payload": {"reclaimed_count": reclaimed},
        })
    kinds = ["source_inventory_refresh"]
    if args.claim_station_source:
        kinds.append("station:source_qualification")
    item = work_queue.claim(cx, worker_id=args.worker_id, kinds=kinds, lease_s=args.lease_s)
    if not item:
        return {"claimed": False}
    work_queue.update_status(cx, work_id=item["work_id"], status="running")
    work_queue.append_event(args.events, {"event_type": "source_worker_started", "work_id": item["work_id"], "payload": item})
    result = refresh_inventory(args)
    status = "done" if result["ok"] else "failed"
    payload_update = {
        "result": result,
        "exit_kind": "qualified_source_inventory" if result["ok"] else "source_inventory_failed",
    }
    if item["kind"] == "station:source_qualification" and result["ok"]:
        payload_update["operator_required"] = "source pipeline requires corpus/root/intake-db tranche arguments"
    work_queue.update_status(cx, work_id=item["work_id"], status=status, payload_update=payload_update)
    work_queue.append_event(
        args.events,
        {
            "event_type": f"source_worker_{status}",
            "work_id": item["work_id"],
            "payload": payload_update,
            "artifact_paths": [args.inventory, args.inventory_md],
        },
    )
    return {"claimed": True, "work_id": item["work_id"], "status": status, "ok": result["ok"]}


def _self_test() -> int:
    assert DEFAULT_INVENTORY.endswith(".json")
    print("leanmill_source_worker self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--worker-id", default="source-worker-local")
    ap.add_argument("--lease-s", type=int, default=600)
    ap.add_argument("--inventory", default=DEFAULT_INVENTORY)
    ap.add_argument("--inventory-md", default=DEFAULT_INVENTORY_MD)
    ap.add_argument("--max-files", type=int, default=0)
    ap.add_argument("--claim-station-source", action="store_true")
    ap.add_argument("--refresh-only", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    result = refresh_inventory(args) if args.refresh_only else work_once(args)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok", True) is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
