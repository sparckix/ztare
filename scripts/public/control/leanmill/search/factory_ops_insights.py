#!/usr/bin/env python3
"""Generate compact operations-science insights for LeanMill.

Read-only. This consumes dashboard JSON artifacts and emits the few operator
decisions that matter: current bottleneck, evidence, next lever, and confidence.
"""
from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Any


DEFAULT_DATA_DIR = "analytics/public/leanmill/dashboard_data"


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}


def _pct(v: float | int | None) -> str:
    if v is None:
        return "n/a"
    return f"{100 * float(v):.1f}%"


def _source_quality(data: Path) -> dict[str, Any]:
    for name in (
        "source_quality_mcb_expand100_final_context.json",
        "source_quality_mcb_expand100_partial_context.json",
        "source_quality_mcb_expand100_static_fallback.json",
        "source_quality_mcb_remaining.json",
    ):
        obj = _read(data / name)
        if obj:
            return obj
    return {}


def build(args: argparse.Namespace) -> dict[str, Any]:
    data = Path(args.data_dir)
    status = _read(data / "status_final.json")
    ops = _read(data / "ops_timeseries.json")
    live = _read(data / "factory_live_state.json")
    source = _source_quality(data)
    p0 = _read(data / "p0_rollup_final.json")

    bottleneck = (status.get("bottleneck") or {}).get("current_bottleneck") or "unknown"
    live_jobs = live.get("active_work") or []
    source_totals = source.get("totals") or {}
    source_rates = source.get("rates") or {}
    ops_summary = ops.get("summary") or {}
    headline = p0.get("headline") or {}

    ready_rows = int(source_totals.get("canary_ready_rows") or 0)
    target_candidates = int(source_totals.get("target_compatible_sources") or 0)
    pending_gov = int(headline.get("pending_governance") or 0)
    verified = int(headline.get("verified_value_rows") or 0)
    residual = int(headline.get("path_c_learning_rows") or 0)
    live_job = next((j for j in live_jobs if j.get("state") == "running"), None)
    complete_jobs = [j for j in live_jobs if j.get("state") == "complete"]

    insights: list[dict[str, Any]] = []
    if live_job:
        phase = str(live_job.get("phase") or "active work")
        if phase == "row_context_filter":
            station = "Source Qualification"
            lever = "Wait for target-site filter to finish; then freeze the intake buffer."
            why = str(live_job.get("progress") or "target-site filter running")
        elif phase == "static_filter_fallback":
            station = "Source Qualification"
            lever = "Wait for per-row static fallback; do not treat previous zero as scientific."
            why = str(live_job.get("progress") or "static fallback running")
        else:
            station = str(live_job.get("name") or "Active work")
            lever = str(live_job.get("next_handoff") or "finish active work")
            why = str(live_job.get("progress") or "active job detected")
        insights.append({
            "kind": "live_bottleneck",
            "station": station,
            "plain_english": f"The active constraint is {station}: {why}.",
            "evidence": why,
            "next_lever": lever,
            "confidence": "high",
        })

    if ready_rows:
        insights.append({
            "kind": "source_conversion",
            "station": "Next Canary Buffer",
            "plain_english": f"Source qualification has recovered {ready_rows} canary-ready rows so far.",
            "evidence": (
                f"{target_candidates} target-site-ready candidates; "
                f"{source_rates.get('canary_ready_rows_per_100_raw_sources', 'n/a')} canary rows per 100 raw sources"
            ),
            "next_lever": "After the context filter completes, build intake from the final packet and run one bounded proof mill.",
            "confidence": "medium" if live_job else "high",
        })
    elif source_totals:
        insights.append({
            "kind": "source_conversion",
            "station": "Source Qualification",
            "plain_english": "Source volume exists, but final canary-ready rows are not yet frozen.",
            "evidence": (
                f"{source_totals.get('name_resolved_sources', 0)} names resolved; "
                f"{source_totals.get('action_compatible_sources', 0)} action-compatible candidates"
            ),
            "next_lever": "Finish target-site row-context filtering before proof execution.",
            "confidence": "medium",
        })

    if pending_gov:
        insights.append({
            "kind": "queue_bottleneck",
            "station": "Governance Gate",
            "plain_english": f"Governance has {pending_gov} pending items.",
            "evidence": "pending_governance > 0",
            "next_lever": "Run governance consumers before starting more proof execution.",
            "confidence": "high",
        })
    elif verified or residual:
        insights.append({
            "kind": "completed_batch",
            "station": "Residual Compiler",
            "plain_english": "The completed batch is no longer governance-bound; the next science lever is qualified intake plus residual repair lanes.",
            "evidence": (
                f"{verified} verified rows, {residual} residual inventory, "
                f"{ops_summary.get('seconds_per_factory_event', 'n/a')} seconds/event in completed batch"
            ),
            "next_lever": "Use the new source-qualified buffer to run a bounded mill; route failures back into residual families.",
            "confidence": "high",
        })

    if complete_jobs and not live_job and not pending_gov:
        latest = complete_jobs[0]
        insights.append({
            "kind": "idle_after_completion",
            "station": "Canary Intake",
            "plain_english": "No station is currently moving work; restart the line by creating a new qualified intake buffer.",
            "evidence": f"{latest.get('name')} is complete; active worker count is zero.",
            "next_lever": "Build or admit the next source-qualified canary buffer, then run a bounded REPL-step mill.",
            "confidence": "high",
        })

    payload = {
        "schema": "leanmill-ops-insights-v1",
        "generated_at_epoch": int(time.time()),
        "completed_batch_bottleneck": bottleneck,
        "current_live_station": (live_job or {}).get("phase") or "idle",
        "headline": {
            "verified_rows": verified,
            "residual_rows": residual,
            "pending_governance": pending_gov,
            "source_canary_ready_rows": ready_rows,
            "source_target_ready_candidates": target_candidates,
        },
        "insights": insights[: args.max_insights],
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "factory_live_state.json").write_text(json.dumps({
            "active_work": [{
                "state": "running",
                "phase": "row_context_filter",
                "progress": "2 target-site-ready / 1 checked",
                "next_handoff": "intake",
            }]
        }))
        obj = build(argparse.Namespace(data_dir=str(root), out=None, max_insights=5))
        assert obj["insights"][0]["kind"] == "live_bottleneck"
    print("leansearch_factory_ops_insights self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--out")
    ap.add_argument("--max-insights", type=int, default=4)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    print(json.dumps(build(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
