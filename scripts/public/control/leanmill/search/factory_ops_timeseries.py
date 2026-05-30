#!/usr/bin/env python3
"""Time-bucketed operations-science view for the LeanSearch factory.

Reports throughput, cycle time, lead time, WIP, and bottleneck by time bucket
from existing append-only factory artifacts. Read-only; no Lean execution.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
    if not s:
        return None
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


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    vals = sorted(values)
    if len(vals) == 1:
        return vals[0]
    rank = (p / 100.0) * (len(vals) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(vals) - 1)
    frac = rank - lo
    return round(vals[lo] + frac * (vals[hi] - vals[lo]), 3)


def _stats(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "mean": round(statistics.mean(values), 3) if values else None,
        "p50": _percentile(values, 50),
        "p90": _percentile(values, 90),
        "max": round(max(values), 3) if values else None,
    }


def _lanes(root: Path) -> list[str]:
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if (p / "events").is_dir())


def _bucket(ts: float, start: float, bucket_seconds: int) -> int:
    return int((ts - start) // bucket_seconds)


def _intake_snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    con = sqlite3.connect(str(path), timeout=30.0)
    return {
        str(status): int(n)
        for status, n in con.execute(
            "SELECT status, COUNT(*) FROM intake_queue GROUP BY status"
        ).fetchall()
    }


def _collect_events(root: Path, lanes: list[str]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for lane in lanes:
        event_dir = root / lane / "events"
        for stream in STREAMS:
            for rec in _read_jsonl(event_dir / f"{stream}.jsonl"):
                ts = _parse_ts(rec.get("created_at"))
                if ts is None:
                    continue
                events.append({
                    "ts": ts,
                    "lane": lane,
                    "stream": stream,
                    "row_id": rec.get("row_id"),
                    "cycle_s": rec.get("cycle_s"),
                    "lead_s": rec.get("lead_s"),
                    "event": rec.get("event"),
                })
    return events


def _collect_path_a(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    starts: dict[str, dict[str, Any]] = {}
    dones: list[dict[str, Any]] = []
    for rec in _read_jsonl(root / "mill_events.jsonl"):
        key = f"{rec.get('lane')}::{rec.get('row_id')}"
        if rec.get("phase") == "path_a_start":
            starts[key] = rec
        elif rec.get("phase") == "path_a_done":
            start = starts.get(key, {})
            dones.append({
                "lane": rec.get("lane"),
                "row_id": rec.get("row_id"),
                "start_ts": _parse_ts(start.get("ts")),
                "done_ts": _parse_ts(rec.get("ts")),
                "elapsed_s": rec.get("elapsed_s"),
            })
    return list(starts.values()), dones


def build_timeseries(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root)
    lanes = args.lane or _lanes(root)
    stream_events = _collect_events(root, lanes)
    starts, path_a_dones = _collect_path_a(root)
    all_ts = [e["ts"] for e in stream_events]
    all_ts += [float(d["done_ts"]) for d in path_a_dones if d.get("done_ts") is not None]
    all_ts += [float(s["ts"]) for s in starts if s.get("ts") is not None]
    if not all_ts:
        payload = {
            "schema": "leansearch-factory-ops-timeseries-v1",
            "root": str(root),
            "lanes": lanes,
            "bucket_seconds": args.bucket_seconds,
            "buckets": [],
            "summary": {"events": 0},
            "intake_snapshot": _intake_snapshot(Path(args.intake_db)) if args.intake_db else {},
        }
        if args.out:
            Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return payload

    start_ts = min(all_ts)
    end_ts = max(max(all_ts), time.time() if args.include_now else max(all_ts))
    bucket_count = max(1, _bucket(end_ts, start_ts, args.bucket_seconds) + 1)
    buckets: list[dict[str, Any]] = []
    cumulative = {"path_a_done": 0, "to_govern": 0, "closed": 0, "path_c_residuals": 0}

    for i in range(bucket_count):
        b0 = start_ts + i * args.bucket_seconds
        b1 = b0 + args.bucket_seconds
        evs = [e for e in stream_events if b0 <= e["ts"] < b1]
        a_done = [d for d in path_a_dones if d.get("done_ts") is not None and b0 <= float(d["done_ts"]) < b1]
        a_started = [s for s in starts if s.get("ts") is not None and b0 <= float(s["ts"]) < b1]
        for key in ("to_govern", "closed", "path_c_residuals"):
            cumulative[key] += sum(1 for e in evs if e["stream"] == key)
        cumulative["path_a_done"] += len(a_done)
        a_cycle = [float(d["elapsed_s"]) for d in a_done if d.get("elapsed_s") is not None]
        event_cycle = [float(e["cycle_s"]) for e in evs if e.get("cycle_s") is not None]
        event_lead = [float(e["lead_s"]) for e in evs if e.get("lead_s") is not None]
        throughput_events = len(evs)
        throughput_per_hour = round(throughput_events * 3600.0 / args.bucket_seconds, 3)
        seconds_per_event = round(args.bucket_seconds / throughput_events, 3) if throughput_events else None
        wip_a = 0
        for s in starts:
            s_ts = _parse_ts(s.get("ts"))
            if s_ts is None or s_ts >= b1:
                continue
            key = f"{s.get('lane')}::{s.get('row_id')}"
            done_ts = None
            for d in path_a_dones:
                if f"{d.get('lane')}::{d.get('row_id')}" == key:
                    done_ts = d.get("done_ts")
                    break
            if done_ts is None or float(done_ts) >= b0:
                wip_a += 1
        station_counts = {
            "path_a_done": len(a_done),
            "to_govern": sum(1 for e in evs if e["stream"] == "to_govern"),
            "path_b_closed": sum(1 for e in evs if e["stream"] == "closed"),
            "path_c_residuals": sum(1 for e in evs if e["stream"] == "path_c_residuals"),
        }
        if wip_a:
            bottleneck = "path_a_lean"
        elif station_counts["to_govern"] > station_counts["path_b_closed"]:
            bottleneck = "path_b_governance"
        elif station_counts["path_c_residuals"]:
            bottleneck = "path_c_repair_compiler"
        else:
            bottleneck = "source_or_idle"
        buckets.append({
            "bucket_index": i,
            "start": _iso(b0),
            "end": _iso(b1),
            "counts": station_counts,
            "cumulative": dict(cumulative),
            "throughput_events_per_hour": throughput_per_hour,
            "seconds_per_event_inverse_throughput": seconds_per_event,
            "path_a_wip_estimate": wip_a,
            "path_a_started": len(a_started),
            "path_a_cycle_s": _stats(a_cycle),
            "event_cycle_s": _stats(event_cycle),
            "event_lead_s": _stats(event_lead),
            "bottleneck_guess": bottleneck,
        })

    span_s = max(1.0, end_ts - start_ts)
    payload = {
        "schema": "leansearch-factory-ops-timeseries-v1",
        "root": str(root),
        "lanes": lanes,
        "bucket_seconds": args.bucket_seconds,
        "time_window": {"start": _iso(start_ts), "end": _iso(end_ts), "span_s": round(span_s, 3)},
        "summary": {
            "path_a_done": len(path_a_dones),
            "factory_events": len(stream_events),
            "to_govern": sum(1 for e in stream_events if e["stream"] == "to_govern"),
            "ratified_closed": sum(1 for e in stream_events if e["stream"] == "closed"),
            "path_c_residuals": sum(1 for e in stream_events if e["stream"] == "path_c_residuals"),
            "factory_events_per_hour": round(len(stream_events) * 3600.0 / span_s, 3),
            "seconds_per_factory_event": round(span_s / len(stream_events), 3) if stream_events else None,
            "path_a_cycle_s": _stats([float(d["elapsed_s"]) for d in path_a_dones if d.get("elapsed_s") is not None]),
            "event_lead_s": _stats([float(e["lead_s"]) for e in stream_events if e.get("lead_s") is not None]),
        },
        "intake_snapshot": _intake_snapshot(Path(args.intake_db)) if args.intake_db else {},
        "buckets": buckets,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    assert _parse_ts("2026-05-20T00:00:00Z") is not None
    assert _stats([1.0, 3.0])["mean"] == 2.0
    print("leansearch_factory_ops_timeseries self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/tmp/rung1/leansearch_factory_mill")
    ap.add_argument("--intake-db", default="")
    ap.add_argument("--lane", action="append")
    ap.add_argument("--bucket-seconds", type=int, default=300)
    ap.add_argument("--include-now", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--watch-seconds", type=int)
    ap.add_argument("--watch-iterations", type=int, default=0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if args.watch_seconds:
        n = 0
        while True:
            payload = build_timeseries(args)
            summary = payload.get("summary") or {}
            snap = {
                "schema": "leansearch-factory-ops-watch-v1",
                "observed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "root": payload.get("root"),
                "summary": summary,
                "intake_snapshot": payload.get("intake_snapshot"),
                "latest_bucket": (payload.get("buckets") or [{}])[-1],
            }
            print(json.dumps(snap, sort_keys=True), flush=True)
            n += 1
            if args.watch_iterations and n >= args.watch_iterations:
                break
            time.sleep(args.watch_seconds)
        return 0
    print(json.dumps(build_timeseries(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
