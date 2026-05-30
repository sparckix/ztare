#!/usr/bin/env python3
"""Human-facing P0 science rollup for the LeanSearch factory.

This is deliberately different from ops throughput. Events/hour says whether
the line is moving; this report says whether the line is producing scientific
value: ratified closures, exact gaps/falsifiers when available, and reusable
Path-C residual families.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import leansearch_factory_residual_plan as residual_plan


STREAMS = ("to_govern", "closed", "path_c_residuals")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(errors="ignore").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def _parse_ts(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        return None


def _iso(ts: float | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stats(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "mean": round(statistics.mean(values), 3) if values else None,
        "max": round(max(values), 3) if values else None,
    }


def _lanes(root: Path) -> list[str]:
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if (p / "events").is_dir())


def _events(root: Path, lanes: list[str]) -> dict[str, list[dict[str, Any]]]:
    out = {stream: [] for stream in STREAMS}
    for lane in lanes:
        event_dir = root / lane / "events"
        for stream in STREAMS:
            for rec in _read_jsonl(event_dir / f"{stream}.jsonl"):
                out[stream].append({**rec, "_lane": lane})
    return out


def _mill_rows(root: Path) -> tuple[int, list[float], float | None, float | None]:
    started: dict[str, float] = {}
    done_cycles: list[float] = []
    first_ts = None
    last_ts = None
    for rec in _read_jsonl(root / "mill_events.jsonl"):
        ts = _parse_ts(rec.get("ts"))
        if ts is not None:
            first_ts = ts if first_ts is None else min(first_ts, ts)
            last_ts = ts if last_ts is None else max(last_ts, ts)
        key = f"{rec.get('lane')}::{rec.get('row_id')}"
        if rec.get("phase") == "path_a_start" and ts is not None:
            started[key] = ts
        elif rec.get("phase") == "path_a_done":
            if rec.get("elapsed_s") is not None:
                done_cycles.append(float(rec["elapsed_s"]))
    return len(done_cycles), done_cycles, first_ts, last_ts


def _queue(root: Path) -> dict[str, Any]:
    path = root / "factory_queue.sqlite"
    if not path.exists():
        return {"exists": False, "by_status": {}, "pending": 0}
    con = sqlite3.connect(str(path), timeout=30.0)
    by_status = {
        str(status): int(n)
        for status, n in con.execute("SELECT status, COUNT(*) FROM event_queue GROUP BY status").fetchall()
    }
    return {
        "exists": True,
        "by_status": by_status,
        "pending": by_status.get("ready", 0) + by_status.get("claimed", 0),
    }


def _safe_rate(num: int, den: int) -> float | None:
    if den <= 0:
        return None
    return round(num / den, 3)


def build_rollup(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root)
    lanes = args.lane or _lanes(root)
    ev = _events(root, lanes)
    path_a_rows, path_a_cycles, first_ts, last_ts = _mill_rows(root)
    event_ts = [_parse_ts(r.get("created_at")) for rows in ev.values() for r in rows]
    event_ts = [t for t in event_ts if t is not None]
    first_event_ts = min(event_ts) if event_ts else None
    last_event_ts = max(event_ts) if event_ts else None
    first_ts = min([t for t in [first_ts, first_event_ts] if t is not None], default=None)
    last_ts = max([t for t in [last_ts, last_event_ts] if t is not None], default=None)
    span_s = (last_ts - first_ts) if first_ts is not None and last_ts is not None else None
    q = _queue(root)
    to_govern = ev["to_govern"]
    closed = ev["closed"]
    residuals = ev["path_c_residuals"]
    plan = residual_plan.build_plan(
        argparse.Namespace(
            root=str(root),
            lane=lanes,
            out=None,
            promote_threshold=args.promote_threshold,
            max_tails=1,
            tail_chars=300,
        )
    )
    promoted_packets = [p for p in plan.get("packets", []) if p.get("scale_decision") == "promote_to_repair_lane"]
    ratified_rows = sorted({str(r.get("row_id")) for r in closed if r.get("row_id")})
    residual_rows = sorted({str(r.get("row_id")) for r in residuals if r.get("row_id")})
    value_count = len(closed)
    rows_seen = max(path_a_rows, len(ratified_rows) + len(residual_rows), len(to_govern) + len(residuals))
    payload = {
        "schema": "leansearch-factory-p0-rollup-v1",
        "root": str(root),
        "time_window": {
            "start": _iso(first_ts),
            "end": _iso(last_ts),
            "span_s": round(span_s, 3) if span_s is not None else None,
        },
        "headline": {
            "rows_processed": rows_seen,
            "verified_value_rows": value_count,
            "path_c_learning_rows": len(residuals),
            "pending_governance": q["pending"],
            "verified_value_yield_per_row": _safe_rate(value_count, rows_seen),
            "learning_inventory_yield_per_row": _safe_rate(len(residuals), rows_seen),
            "non_tautology_guard": "Residuals count as inventory only; headline value requires Path-B-ratified closure, exact gap, or valid falsifier.",
        },
        "path_a_execution": {
            "rows_done": path_a_rows,
            "compile_closed_to_govern": len(to_govern),
            "direct_residuals_to_path_c": len(residuals),
            "compile_close_rate": _safe_rate(len(to_govern), path_a_rows),
            "residual_rate": _safe_rate(len(residuals), path_a_rows),
            "cycle_s": _stats(path_a_cycles),
        },
        "path_b_governance": {
            "events_received": len(to_govern),
            "ratified_proof_closures": len(closed),
            "exact_gap": 0,
            "valid_falsifier": 0,
            "consequence_exposure": 0,
            "invalid_or_retired": 0,
            "pending": q["pending"],
            "queue_by_status": q["by_status"],
            "ratification_rate_per_governance_event": _safe_rate(len(closed), len(to_govern)),
        },
        "path_c_curriculum": {
            "residual_events": len(residuals),
            "residual_rows": residual_rows,
            "repair_family_clusters": int(plan.get("cluster_count") or 0),
            "promoted_repair_families": [
                {
                    "repair_family": p.get("repair_family"),
                    "row_count": p.get("row_count"),
                    "priority": p.get("priority"),
                    "rows": p.get("rows"),
                }
                for p in promoted_packets[: args.top_packets]
            ],
        },
        "science_interpretation": {
            "good": "high verified_value_yield_per_row with zero false-ratification, or recurring residual families promoted into tested repair lanes",
            "bad_or_tautological": "high events/hour or high residual count without ratified value, exact gaps/falsifiers, or reusable repair-lane promotion",
            "next_decision_rule": "If pending governance is zero, spend on the top promoted Path-C repair family rather than increasing B workers.",
        },
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    assert _safe_rate(1, 2) == 0.5
    assert _safe_rate(1, 0) is None
    print("leansearch_factory_p0_rollup self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/tmp/rung1/leansearch_factory_mill")
    ap.add_argument("--lane", action="append")
    ap.add_argument("--promote-threshold", type=int, default=3)
    ap.add_argument("--top-packets", type=int, default=4)
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    print(json.dumps(build_rollup(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
