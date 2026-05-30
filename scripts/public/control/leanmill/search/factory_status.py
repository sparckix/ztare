#!/usr/bin/env python3
"""Report live capacity and bottlenecks for the LeanSearch factory.

This is a read-only control-plane view. It combines the intake queue, factory
event streams, scoreboard, and residual plan into one compact status packet so
the next action is driven by queue state instead of chat memory.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

import leansearch_factory_residual_plan as residual_plan
import leansearch_factory_scoreboard as scoreboard


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(errors="ignore").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def _intake_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "queue_db": str(path),
            "exists": False,
            "by_status": {},
            "by_lane_ready": {},
            "oldest_ready_age_s": None,
            "ready_total": 0,
            "claimed_total": 0,
            "done_total": 0,
            "failed_total": 0,
        }
    con = sqlite3.connect(str(path), timeout=30.0)
    by_status = {
        str(status): int(n)
        for status, n in con.execute(
            "SELECT status, COUNT(*) FROM intake_queue GROUP BY status"
        ).fetchall()
    }
    by_lane_ready = {
        str(lane): int(n)
        for lane, n in con.execute(
            """
            SELECT lane_hint, COUNT(*)
            FROM intake_queue
            WHERE status = 'ready'
            GROUP BY lane_hint
            ORDER BY COUNT(*) DESC, lane_hint ASC
            """
        ).fetchall()
    }
    oldest = con.execute(
        "SELECT MIN(inserted_at) FROM intake_queue WHERE status = 'ready'"
    ).fetchone()[0]
    now = time.time()
    return {
        "queue_db": str(path),
        "exists": True,
        "by_status": by_status,
        "by_lane_ready": by_lane_ready,
        "oldest_ready_age_s": round(now - float(oldest), 3) if oldest else None,
        "ready_total": by_status.get("ready", 0),
        "claimed_total": by_status.get("claimed", 0),
        "done_total": by_status.get("done", 0),
        "failed_total": by_status.get("failed", 0),
    }


def _mill_status(root: Path) -> dict[str, Any]:
    rows = _read_jsonl(root / "mill_events.jsonl")
    starts: dict[str, dict[str, Any]] = {}
    dones: dict[str, dict[str, Any]] = {}
    for rec in rows:
        key = f"{rec.get('lane')}::{rec.get('row_id')}"
        if rec.get("phase") in {"proof_execution_start", "path_a_start"}:
            starts[key] = rec
        elif rec.get("phase") in {"proof_execution_done", "path_a_done"}:
            dones[key] = rec
    active = []
    for key, rec in starts.items():
        if key not in dones:
            active.append({
                "lane": rec.get("lane"),
                "row_id": rec.get("row_id"),
                "age_s": round(time.time() - float(rec.get("ts") or time.time()), 3),
            })
    return {
        "event_log": str(root / "mill_events.jsonl"),
        "proof_execution_started": len(starts),
        "proof_execution_done": len(dones),
        "proof_execution_active": active,
        "path_a_active_count": len(active),
    }


def _queue_status(root: Path) -> dict[str, Any]:
    path = root / "factory_queue.sqlite"
    if not path.exists():
        return {"queue_db": str(path), "exists": False, "by_status": {}, "pending_total": 0}
    con = sqlite3.connect(str(path), timeout=30.0)
    by_status = {
        str(status): int(n)
        for status, n in con.execute(
            "SELECT status, COUNT(*) FROM event_queue GROUP BY status"
        ).fetchall()
    }
    pending = sum(by_status.get(k, 0) for k in ("ready", "claimed"))
    return {
        "queue_db": str(path),
        "exists": True,
        "by_status": by_status,
        "pending_total": pending,
        "done_total": by_status.get("done", 0),
        "residualized_total": by_status.get("residualized", 0),
        "skipped_total": by_status.get("skipped", 0),
    }


def _bottleneck(intake: dict[str, Any], mill: dict[str, Any], score: dict[str, Any]) -> dict[str, Any]:
    ready = int(intake.get("ready_total") or 0)
    active = int(mill.get("path_a_active_count") or 0)
    to_govern = 0
    for row in score.get("by_lane") or []:
        to_govern += int(((row.get("flow") or {}).get("to_govern_events")) or 0)
    residuals = int(((score.get("totals") or {}).get("curriculum") or {}).get("path_c_residuals") or 0)
    closed = int(((score.get("totals") or {}).get("solver") or {}).get("ratified_proof_closure") or 0)
    if active:
        station = "proof_execution_active"
        action = "wait_or_add_another_machine; do not add another heavy Lean worker on this host"
    elif ready:
        station = "proof_execution_idle_with_ready_wip"
        action = "start one mill worker on this host"
    elif to_govern:
        station = "governance_gate"
        action = "run governance consumers until to_govern is empty"
    elif residuals and not closed:
        station = "residual_compiler"
        action = "promote highest-priority residual family into a source-safe repair lane"
    else:
        station = "source_intake"
        action = "add more source packets to the intake buffer"
    return {
        "current_bottleneck": station,
        "recommended_next_action": action,
        "ready_wip": ready,
        "proof_execution_active": active,
        "to_govern_events": to_govern,
        "residual_compiler_residuals": residuals,
        "ratified_closures": closed,
    }


def _bottleneck_with_queue(
    intake: dict[str, Any], mill: dict[str, Any], score: dict[str, Any], queue: dict[str, Any]
) -> dict[str, Any]:
    payload = _bottleneck(intake, mill, score)
    pending_governance = int(queue.get("pending_total") or 0)
    ready = int(intake.get("ready_total") or 0)
    active = int(mill.get("path_a_active_count") or 0)
    residuals = int(((score.get("totals") or {}).get("curriculum") or {}).get("path_c_residuals") or 0)
    closed = int(((score.get("totals") or {}).get("solver") or {}).get("ratified_proof_closure") or 0)
    payload["pending_governance_events"] = pending_governance
    if active:
        payload["current_bottleneck"] = "proof_execution_active"
        payload["recommended_next_action"] = "wait_or_add_another_machine; do not add another heavy Lean worker on this host"
    elif ready:
        payload["current_bottleneck"] = "proof_execution_idle_with_ready_wip"
        payload["recommended_next_action"] = "start one mill worker on this host"
    elif pending_governance:
        payload["current_bottleneck"] = "governance_gate"
        payload["recommended_next_action"] = "run governance consumers until pending governance is empty"
    elif residuals and closed >= 0:
        payload["current_bottleneck"] = "residual_compiler"
        payload["recommended_next_action"] = "promote highest-priority residual family into a source-safe repair lane"
    else:
        payload["current_bottleneck"] = "source_intake"
        payload["recommended_next_action"] = "add more source packets to the intake buffer"
    return payload


def build_status(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root)
    intake = _intake_status(Path(args.intake_db))
    mill = _mill_status(root)
    queue = _queue_status(root)
    score = scoreboard.build_scoreboard(argparse.Namespace(root=str(root), lane=args.lane, out=None))
    plan = residual_plan.build_plan(
        argparse.Namespace(
            root=str(root),
            lane=args.lane,
            out=None,
            promote_threshold=args.promote_threshold,
            max_tails=args.max_tails,
            tail_chars=args.tail_chars,
        )
    )
    payload = {
        "schema": "leansearch-factory-status-v1",
        "root": str(root),
        "intake": intake,
        "mill": mill,
        "governance_queue": queue,
        "scoreboard": score,
        "residual_plan": {
            "residual_events": plan.get("residual_events", 0),
            "cluster_count": plan.get("cluster_count", 0),
            "top_packets": (plan.get("packets") or [])[: args.top_packets],
        },
        "bottleneck": _bottleneck_with_queue(intake, mill, score, queue),
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    payload = _bottleneck(
        {"ready_total": 1},
        {"path_a_active_count": 0},
        {"by_lane": [], "totals": {"curriculum": {"path_c_residuals": 0}, "solver": {"ratified_proof_closure": 0}}},
    )
    assert payload["current_bottleneck"] == "proof_execution_idle_with_ready_wip"
    print("leansearch_factory_status self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/tmp/rung1/leansearch_factory_mill")
    ap.add_argument("--intake-db", default="/tmp/rung1/leansearch_factory_intake.sqlite")
    ap.add_argument("--lane", action="append")
    ap.add_argument("--out")
    ap.add_argument("--promote-threshold", type=int, default=3)
    ap.add_argument("--max-tails", type=int, default=3)
    ap.add_argument("--tail-chars", type=int, default=700)
    ap.add_argument("--top-packets", type=int, default=3)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    print(json.dumps(build_status(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
