#!/usr/bin/env python3
"""Convert LeanMill station work orders into an executable scheduler plan.

Dry-run only by default. The plan is a narrow bridge from station contract to
operator/agent action without hiding heavy Lean execution behind a dashboard.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_paths import REPAIR_FAMILY_REGISTRY


DEFAULT_CONTRACT = "analytics/public/leanmill/dashboard_data/station_action_contract.json"


def _read(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}


def _command_for(order: dict[str, Any]) -> dict[str, Any]:
    station = str(order.get("station") or "")
    family = str(order.get("family") or "")
    if station == "residual_curriculum":
        return {
            "mode": "compile_residual_packet",
            "command_template": (
                "./venv/bin/python scripts/public/control/leanmill/search/path_c_residual_compiler.py "
                "--root <residual_jsonl_or_root> --static-filter <static_filter.json> "
                "--out <compiled_canaries.json> --decisions-out <decisions.json>"
            ),
            "requires_operator_fill": ["residual_jsonl_or_root", "static_filter", "compiled_canaries", "decisions"],
        }
    if station == "repair_registry":
        return {
            "mode": "source_sibling_or_hold",
            "command_template": (
                "./venv/bin/python scripts/public/control/leanmill/search/repair_family_registry.py "
                f"--discover-root /tmp/rung1 --out {REPAIR_FAMILY_REGISTRY}"
            ),
            "requires_operator_fill": [],
            "family": family,
        }
    if station == "source_qualification":
        return {
            "mode": "source_qualification",
            "command_template": (
                "./venv/bin/python scripts/public/control/leanmill/search/mcb_source_pipeline.py "
                "--help"
            ),
            "requires_operator_fill": ["source tranche / queue path"],
        }
    if station == "governance_gate":
        return {
            "mode": "governance_drain",
            "command_template": (
                "./venv/bin/python scripts/public/control/leanmill/search/factory_consume.py "
                "--help"
            ),
            "requires_operator_fill": ["factory root", "lane"],
        }
    return {"mode": "manual_review", "command_template": "", "requires_operator_fill": ["station-specific action"]}


def _has_station_work(cx: Any, base_work_id: str, *, terminal: bool) -> bool:
    if not base_work_id:
        return False
    status_clause = "status IN ('done', 'failed', 'retired', 'dead_letter')" if terminal else "status IN ('queued', 'claimed', 'running')"
    row = cx.execute(
        f"""
        SELECT 1
        FROM work_items
        WHERE {status_clause}
          AND (work_id=? OR work_id LIKE ?)
        LIMIT 1
        """,
        (base_work_id, f"{base_work_id}:%"),
    ).fetchone()
    return row is not None


def build(args: argparse.Namespace) -> dict[str, Any]:
    contract = _read(args.contract)
    orders = list(contract.get("work_orders") or [])
    if args.limit:
        orders = orders[: args.limit]
    plan_orders = []
    for order in orders:
        plan_orders.append({
            "work_order_id": order.get("work_order_id"),
            "priority": order.get("priority"),
            "station": order.get("station"),
            "family": order.get("family"),
            "action": order.get("action"),
            "learning_unit_exit": order.get("learning_unit_exit"),
            "success_gate": order.get("success_gate"),
            "required_receipt": order.get("required_receipt"),
            "execution": _command_for(order),
        })
    payload = {
        "schema": "leanmill-station-scheduler-plan-v1",
        "contract": args.contract,
        "dry_run": not args.execute,
        "order_count": len(plan_orders),
        "orders": plan_orders,
        "note": "This plan does not launch heavy Lean by itself; it makes the next station action explicit.",
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.enqueue:
        cx = work_queue.connect(args.queue_db)
        run_id = args.run_id or str(int(time.time()))
        enqueued = 0
        skipped_existing_open = 0
        skipped_existing_terminal = 0
        for order in plan_orders:
            base_work_id = str(order.get("work_order_id") or "")
            if not base_work_id:
                raise ValueError(f"station work order missing work_order_id: {order}")
            if _has_station_work(cx, base_work_id, terminal=False):
                skipped_existing_open += 1
                work_queue.append_event(args.events, {
                    "event_type": "station_work_enqueue_skipped_existing_open",
                    "work_id": base_work_id,
                    "payload": {
                        "station": order.get("station"),
                        "family": order.get("family"),
                        "base_work_order_id": base_work_id,
                    },
                })
                continue
            if not args.retry_terminal_work and _has_station_work(cx, base_work_id, terminal=True):
                skipped_existing_terminal += 1
                work_queue.append_event(args.events, {
                    "event_type": "station_work_enqueue_skipped_existing_terminal",
                    "work_id": base_work_id,
                    "payload": {
                        "station": order.get("station"),
                        "family": order.get("family"),
                        "base_work_order_id": base_work_id,
                        "retry_requires_flag": "--retry-terminal-work",
                    },
                })
                continue
            work_id = f"{base_work_id}:{run_id}"
            queue_priority = max(0, 100 - int(order.get("priority") or 0))
            work_queue.enqueue(
                cx,
                kind=f"station:{order.get('station')}",
                priority=queue_priority,
                payload={"work_id": work_id, "base_work_order_id": base_work_id, "station_order": order},
                max_attempts=1,
            )
            work_queue.append_event(args.events, {
                "event_type": "station_work_enqueued",
                "work_id": work_id,
                "payload": {"station": order.get("station"), "family": order.get("family"), "base_work_order_id": base_work_id},
            })
            enqueued += 1
        payload["enqueued"] = enqueued
        payload["skipped_existing_open"] = skipped_existing_open
        payload["skipped_existing_terminal"] = skipped_existing_terminal
    return payload


def _self_test() -> int:
    payload = build(argparse.Namespace(
        contract="/tmp/no_such_contract.json",
        out=None,
        limit=0,
        execute=False,
        enqueue=False,
        queue_db=work_queue.DEFAULT_DB,
        events=work_queue.DEFAULT_EVENTS,
    ))
    assert payload["order_count"] == 0
    db = "/tmp/leanmill_station_scheduler_selftest.sqlite"
    events = "/tmp/leanmill_station_scheduler_selftest.jsonl"
    cx = work_queue.connect(db)
    work_queue.enqueue(cx, kind="station:residual_curriculum", priority=1, payload={"work_id": "residual_compiler:refresh_source_plan:1"})
    assert _has_station_work(cx, "residual_compiler:refresh_source_plan", terminal=False)
    print("leanmill_station_scheduler self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", default=DEFAULT_CONTRACT)
    ap.add_argument("--out")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--execute", action="store_true", help="Reserved; currently only annotates dry_run=false.")
    ap.add_argument("--enqueue", action="store_true", help="Create WorkItems from the scheduler plan.")
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--retry-terminal-work", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = build(args)
    print(json.dumps({"order_count": payload["order_count"], "dry_run": payload["dry_run"], "out": args.out}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
