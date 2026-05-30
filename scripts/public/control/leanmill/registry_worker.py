#!/usr/bin/env python3
"""Deterministic worker for registry/dashboard refresh WorkItems."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import leanmill_work_queue as work_queue
from leanmill_paths import REPAIR_FAMILY_REGISTRY as DEFAULT_REGISTRY
from leanmill_paths import SCRATCH_DISCOVER_ROOT


DEFAULT_CONTRACT = "analytics/public/leanmill/dashboard_data/station_action_contract.json"
DEFAULT_SPEC_GATE = "analytics/public/leanmill/dashboard_data/family_spec_gate.json"
DEFAULT_REGRESSION_GATE = "analytics/public/leanmill/dashboard_data/regression_gate.json"
DEFAULT_LIFECYCLE = "analytics/public/leanmill/dashboard_data/residual_lifecycle.json"
DEFAULT_ALLOCATOR = "analytics/public/leanmill/dashboard_data/source_family_allocator.json"
DEFAULT_SOURCE_QUALITY = "analytics/public/leanmill/dashboard_data/source_quality_feedback.json"
DEFAULT_CONVERGENCE_RECEIPT = "analytics/public/leanmill/dashboard_data/repair_family_registry_convergence_receipt.json"
DEFAULT_REGISTRY_IMPORT = "analytics/public/leanmill/dashboard_data/repair_family_registry_import.json"


def _display_cmd(cmd: list[str]) -> list[str]:
    if cmd and Path(cmd[0]).resolve() == Path(sys.executable).resolve():
        return ["<python>", *cmd[1:]]
    return cmd


def _run(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    return {
        "cmd": _display_cmd(cmd),
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def refresh(args: argparse.Namespace) -> dict:
    py = sys.executable
    commands = [
        [py, "scripts/public/control/leanmill/search/repair_family_registry.py", "--discover-root", SCRATCH_DISCOVER_ROOT, "--out", args.registry],
    ]
    merge_registries = list(args.merge_registry or [])
    registry_import = Path(args.registry_import) if args.registry_import else None
    if registry_import and registry_import.exists():
        merge_registries.append(str(registry_import))
    if merge_registries:
        convergence_cmd = [
            py,
            "scripts/public/control/leanmill/registry_converger.py",
            "--registry",
            args.registry,
        ]
        for merge_registry in merge_registries:
            convergence_cmd.extend(["--registry", merge_registry])
        convergence_cmd.extend(["--out", args.registry, "--receipt", args.registry_convergence_receipt, "--quiet"])
        commands.append(convergence_cmd)
    commands.extend([
        [py, "scripts/public/control/leanmill/family_spec_gate.py", "--registry", args.registry, "--out", args.family_spec_gate],
        [py, "scripts/public/control/leanmill/regression_gate.py", "--registry", args.registry, "--out", args.regression_gate],
        [py, "scripts/public/control/leanmill/residual_lifecycle.py", "--out", args.lifecycle],
        [py, "scripts/public/control/leanmill/source_quality_feedback.py", "--queue-db", args.queue_db, "--out", args.source_quality],
        [py, "scripts/public/control/leanmill/source_family_allocator.py", "--registry", args.registry, "--source-quality", args.source_quality, "--out", args.allocator],
        [py, "scripts/public/control/leanmill/station_action_contract.py", "--out", args.contract],
    ])
    results = [_run(cmd) for cmd in commands]
    ok = all(r["returncode"] == 0 for r in results)
    return {"ok": ok, "results": results}


def work_once(args: argparse.Namespace) -> dict:
    cx = work_queue.connect(args.queue_db)
    item = work_queue.claim(cx, worker_id=args.worker_id, kinds=["station:repair_registry", "registry_refresh"], lease_s=args.lease_s)
    if not item:
        return {"claimed": False}
    work_queue.update_status(cx, work_id=item["work_id"], status="running")
    work_queue.append_event(args.events, {"event_type": "registry_worker_started", "work_id": item["work_id"], "payload": item})
    result = refresh(args)
    status = "done" if result["ok"] else "failed"
    work_queue.update_status(cx, work_id=item["work_id"], status=status, payload_update={"result": result})
    work_queue.append_event(
        args.events,
        {
            "event_type": f"registry_worker_{status}",
            "work_id": item["work_id"],
            "payload": result,
            "artifact_paths": [
                args.registry,
                args.family_spec_gate,
                args.regression_gate,
                args.lifecycle,
                args.source_quality,
                args.allocator,
                args.contract,
                args.registry_convergence_receipt,
                args.registry_import,
            ],
        },
    )
    return {"claimed": True, "work_id": item["work_id"], "status": status, "ok": result["ok"]}


def _self_test() -> int:
    assert DEFAULT_REGISTRY
    print("leanmill_registry_worker self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--worker-id", default="registry-worker-local")
    ap.add_argument("--lease-s", type=int, default=600)
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--contract", default=DEFAULT_CONTRACT)
    ap.add_argument("--family-spec-gate", default=DEFAULT_SPEC_GATE)
    ap.add_argument("--regression-gate", default=DEFAULT_REGRESSION_GATE)
    ap.add_argument("--lifecycle", default=DEFAULT_LIFECYCLE)
    ap.add_argument("--allocator", default=DEFAULT_ALLOCATOR)
    ap.add_argument("--source-quality", default=DEFAULT_SOURCE_QUALITY)
    ap.add_argument("--merge-registry", action="append", default=[])
    ap.add_argument("--registry-convergence-receipt", default=DEFAULT_CONVERGENCE_RECEIPT)
    ap.add_argument("--registry-import", default=DEFAULT_REGISTRY_IMPORT)
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
