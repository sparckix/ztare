#!/usr/bin/env python3
"""Build a LeanMill station health dashboard from queue, contract, and events."""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue


DEFAULT_DATA_DIR = "analytics/public/leanmill/dashboard_data"
DEFAULT_CONTRACT = f"{DEFAULT_DATA_DIR}/station_action_contract.json"
DEFAULT_OUT = f"{DEFAULT_DATA_DIR}/station_health_dashboard.json"


STATION_KIND_MAP = {
    "source_qualification": ["station:source_qualification", "source_inventory_refresh"],
    "intake_buffer": ["station:intake_buffer"],
    "proof_execution": ["repair_canary_probe", "proof_probe", "station:proof_execution"],
    "governance_gate": ["governance_refresh", "govern_closure_candidate", "govern_exact_gap", "govern_falsifier", "station:governance_gate"],
    "residual_curriculum": ["station:residual_curriculum", "canary_validation_refresh", "canary_validate", "llm_proposal_validate", "canary_propose"],
    "repair_registry": ["station:repair_registry", "registry_refresh", "agent_repair_task"],
}


def _p95(values: list[int]) -> int:
    if not values:
        return 0
    vals = sorted(values)
    idx = min(len(vals) - 1, int(round((len(vals) - 1) * 0.95)))
    return vals[idx]


def _read_contract(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}


def _event_counts(events: str) -> dict[str, int]:
    p = Path(events)
    counts: dict[str, int] = {}
    if not p.exists():
        return counts
    for line in p.read_text(errors="ignore").splitlines()[-2000:]:
        if not line.strip():
            continue
        try:
            event_type = str(json.loads(line).get("event_type") or "")
        except json.JSONDecodeError:
            continue
        if event_type:
            counts[event_type] = counts.get(event_type, 0) + 1
    return counts


def build(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    rows = cx.execute("SELECT * FROM work_items").fetchall()
    items = [work_queue.row_to_dict(r) for r in rows]
    stats = work_queue.stats(cx)
    open_queue = work_queue.open_stats(cx)
    contract = _read_contract(args.contract)
    contract_by_station = {str(s.get("station")): s for s in contract.get("station_contracts") or []}
    now = int(time.time())

    station_rows: list[dict[str, Any]] = []
    for station, kinds in STATION_KIND_MAP.items():
        station_items = [it for it in items if it["kind"] in kinds]
        status_counts: dict[str, int] = {}
        done_durations = []
        for item in station_items:
            status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1
            if item["status"] in {"done", "failed", "retired", "dead_letter"}:
                done_durations.append(int(item["updated_at"]) - int(item["created_at"]))
        backlog = sum(status_counts.get(s, 0) for s in ("queued", "claimed", "running"))
        contract_row = contract_by_station.get(station) or {}
        station_rows.append({
            "station": station,
            "queue_kinds": kinds,
            "contract_state": contract_row.get("state", "unknown"),
            "contract_wip_count": int(contract_row.get("wip_count") or 0),
            "backlog": backlog,
            "status_counts": status_counts,
            "p95_time_to_terminal_s": _p95(done_durations),
            "throughput_terminal_items": len(done_durations),
            "sla_blocker": _blocker(station, status_counts, contract_row),
        })

    payload = {
        "schema": "leanmill-station-health-dashboard-v1",
        "generated_at_epoch": now,
        "queue": stats,
        "open_queue": open_queue,
        "current_bottleneck": contract.get("current_bottleneck"),
        "recommended_next_action": contract.get("recommended_next_action"),
        "stations": station_rows,
        "event_counts_tail": _event_counts(args.events),
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _blocker(station: str, status_counts: dict[str, int], contract_row: dict[str, Any]) -> str:
    if status_counts.get("dead_letter"):
        return "dead_letter_review"
    if status_counts.get("failed"):
        return "failed_work_review"
    if sum(status_counts.get(s, 0) for s in ("done", "retired")):
        return "none"
    if contract_row.get("state") in {"ready", "needs_static_filter"} and not status_counts.get("queued"):
        return "scheduler_or_work_order_missing"
    if station == "governance_gate" and contract_row.get("state") == "idle":
        return "none"
    return "none"


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        db = str(Path(td) / "q.sqlite")
        events = str(Path(td) / "events.jsonl")
        out = str(Path(td) / "dash.json")
        cx = work_queue.connect(db)
        work_queue.enqueue(cx, kind="registry_refresh", priority=1, payload={"work_id": "w"}, max_attempts=1)
        payload = build(argparse.Namespace(queue_db=db, events=events, contract="/tmp/no-contract.json", out=out))
        assert payload["schema"] == "leanmill-station-health-dashboard-v1"
        assert Path(out).exists()
    print("leanmill_station_health_dashboard self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--contract", default=DEFAULT_CONTRACT)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = build(args)
    print(json.dumps({
        "out": args.out,
        "station_count": len(payload["stations"]),
        "current_bottleneck": payload.get("current_bottleneck"),
        "queue": payload.get("queue"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
