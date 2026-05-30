#!/usr/bin/env python3
"""Build a compact live-state JSON for the static factory dashboard.

This is presentation/control-plane only. It reads already-materialized factory
artifacts and emits a small packet-flow model that the HTML can animate without
any backend process.
"""
from __future__ import annotations

import argparse
import json
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


def _stage(label: str, count: int | float | None, state: str = "idle") -> dict[str, Any]:
    value = None if count is None else int(count)
    return {"label": label, "count": value, "state": state}


def _machine_label(value: Any, default: str = "Remote") -> str:
    label = str(value or default)
    return label.replace("VPS", "Remote")


def _source_flow(name: str, quality: dict[str, Any]) -> dict[str, Any]:
    if not quality:
        return {
            "name": name,
            "bottleneck": "mechanized data unavailable",
            "canary_ready_per_100_raw": None,
            "stages": [
                _stage("Raw", None),
                _stage("Safe", None),
                _stage("Resolved", None),
                _stage("Action", None),
                _stage("Target", None),
                _stage("Canary", None),
            ],
        }
    totals = quality.get("totals") or {}
    bottleneck = str(quality.get("bottleneck") or "unknown")
    stages = [
        _stage("Raw", totals.get("raw_sources"), "complete"),
        _stage("Safe", totals.get("source_safe_sources"), "complete"),
        _stage("Resolved", totals.get("name_resolved_sources"), "blocked" if bottleneck == "name_resolution" else "complete"),
        _stage("Action", totals.get("action_compatible_sources"), "blocked" if bottleneck == "action_compatibility" else "complete"),
        _stage("Target", totals.get("target_compatible_sources"), "blocked" if bottleneck == "target_context_compatibility" else "complete"),
        _stage("Canary", totals.get("canary_ready_rows"), "ready" if totals.get("canary_ready_rows") else "blocked"),
    ]
    return {
        "name": name,
        "bottleneck": bottleneck,
        "canary_ready_per_100_raw": (quality.get("rates") or {}).get("canary_ready_rows_per_100_raw_sources"),
        "stages": stages,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    data = Path(args.data_dir)
    p0 = _read(data / "p0_rollup_final.json")
    status = _read(data / "status_final.json")
    mcb_quality = _read(data / "source_quality_mcb_remaining.json")
    all40_quality = _read(data / "source_quality_all40_failed.json")
    family_plan = _read(data / "residual_family_source_plan.json")
    mcb_expand = _read(data / "mcb_expansion_status.json")
    source_conveyor = _read(data / "source_conveyor_status.json")
    latest_source_buffer = _read(data / "latest_source_buffer.json")
    if latest_source_buffer.get("root") and latest_source_buffer.get("source_packet"):
        latest_root = str(latest_source_buffer.get("root") or "")
        conveyor_root = str(source_conveyor.get("root") or "")
        latest_rows = int((latest_source_buffer.get("source_packet") or {}).get("row_count") or 0)
        conveyor_rows = int((source_conveyor.get("source_packet") or {}).get("row_count") or 0)
        if (not conveyor_root) or (latest_root != conveyor_root and latest_rows >= conveyor_rows):
            source_conveyor = {
                "state": "running" if (latest_source_buffer.get("row_context_filter") or {}).get("state") == "running" else latest_source_buffer.get("state", "present"),
                "phase": "row_context_filter" if latest_source_buffer.get("row_context_filter") or latest_source_buffer.get("row_context_partial") else "source_qualification",
                "root": latest_root,
                "source_packet": latest_source_buffer.get("source_packet"),
                "static_filter_fallback": latest_source_buffer.get("static_filter"),
                "row_context_fallback": latest_source_buffer.get("row_context_partial") or latest_source_buffer.get("row_context_filter"),
                "updated_epoch": latest_source_buffer.get("updated_epoch"),
                "next_handoff": "intake_buffer_then_bounded_mill_if_ready_rows_exist",
            }
    if source_conveyor.get("root") and source_conveyor.get("source_packet"):
        latest_source_buffer = {
            **latest_source_buffer,
            "state": "present",
            "root": source_conveyor.get("root"),
            "source_packet": source_conveyor.get("source_packet"),
            "static_filter": source_conveyor.get("static_filter_fallback") or latest_source_buffer.get("static_filter"),
            "row_context_filter": source_conveyor.get("row_context_fallback") or latest_source_buffer.get("row_context_filter"),
            "updated_epoch": source_conveyor.get("updated_epoch") or latest_source_buffer.get("updated_epoch"),
        }
    current_run = _read(data / "current_leanmill_run.json")

    h = p0.get("headline") or {}
    proof = p0.get("proof_execution") or p0.get("path_a_execution") or {}
    governance = p0.get("governance_gate") or p0.get("path_b_governance") or {}
    residual = p0.get("residual_compiler") or p0.get("path_c_curriculum") or {}
    intake = status.get("intake") or {}
    mill = status.get("mill") or {}
    bottleneck = status.get("bottleneck") or {}

    station_flow = [
        _stage("Intake", intake.get("ready_total"), "ready" if intake.get("ready_total") else "idle"),
        _stage("Proof Execution", mill.get("path_a_active_count"), "active" if mill.get("path_a_active_count") else "idle"),
        _stage("To Gate", proof.get("compile_closed_to_govern"), "complete" if proof.get("compile_closed_to_govern") else "idle"),
        _stage("Governance Gate", governance.get("pending"), "active" if governance.get("pending") else "idle"),
        _stage("Ratified", governance.get("ratified_proof_closures"), "complete" if governance.get("ratified_proof_closures") else "idle"),
        _stage("Residual Compiler", residual.get("residual_events"), "ready" if residual.get("residual_events") else "idle"),
    ]
    lanes = []
    for packet in family_plan.get("packets") or []:
        lanes.append({
            "name": packet.get("repair_family"),
            "seed_rows": len(packet.get("seed_rows") or []),
            "seed_rows_with_leads": len(packet.get("seed_rows_with_leads") or []),
            "lead_count": int(packet.get("lead_count") or 0),
            "next_action": packet.get("next_action"),
            "state": "ready" if packet.get("lead_count") else "needs_sources",
        })

    payload = {
        "schema": "leansearch-factory-live-state-v1",
        "generated_at_epoch": int(time.time()),
        "current_bottleneck": bottleneck.get("current_bottleneck"),
        "recommended_next_action": bottleneck.get("recommended_next_action"),
        "headline": {
            "rows_processed": h.get("rows_processed"),
            "verified_value_rows": h.get("verified_value_rows"),
            "residual_compiler_learning_rows": h.get("residual_compiler_learning_rows") or h.get("path_c_learning_rows"),
            "pending_governance": h.get("pending_governance"),
        },
        "source_flows": [
            _source_flow("MCB remaining", mcb_quality),
            _source_flow("All-40 LeanSearch", all40_quality),
        ],
        "station_flow": station_flow,
        "residual_lanes": lanes,
        "mcb_expansion": {
            "state": mcb_expand.get("state") or "unknown",
            "pid": mcb_expand.get("pid"),
            "elapsed": mcb_expand.get("elapsed"),
            "n": mcb_expand.get("n"),
            "target_n": mcb_expand.get("target_n"),
        },
        "latest_source_buffer": latest_source_buffer,
        "active_work": _active_work(mcb_expand, source_conveyor, status, current_run, latest_source_buffer),
        "recent_repair_canaries": _recent_repair_canaries(),
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _active_work(mcb_expand: dict[str, Any], source_conveyor: dict[str, Any],
                 status: dict[str, Any], current_run: dict[str, Any] | None = None,
                 latest_source_buffer: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    if not any([mcb_expand, source_conveyor, status, current_run, latest_source_buffer]):
        return [{
            "name": "Live state unavailable",
            "machine": "file-backed dashboard",
            "state": "unavailable",
            "phase": "mechanized data unavailable",
            "elapsed": "",
            "progress": "mechanized data unavailable",
            "next_handoff": "refresh file-backed dashboard artifacts",
        }]
    intake = status.get("intake") or {}
    mill = status.get("mill") or {}
    if current_run and current_run.get("state") in {"running", "waiting", "stopped", "complete", "failed"}:
        current_root = str(current_run.get("root") or "")
        status_root = str(status.get("root") or "")
        inferred_complete = (
            current_run.get("state") == "running"
            and current_root
            and current_root == status_root
            and not (int(intake.get("ready_total") or 0) or int(intake.get("claimed_total") or 0))
            and not int(mill.get("path_a_active_count") or 0)
        )
        if not inferred_complete and current_run.get("phase") == "source_expansion":
            accepted = mcb_expand.get("n")
            target = mcb_expand.get("target_n")
            inferred_complete = bool(
                accepted is not None
                and target is not None
                and int(accepted) >= int(target)
                and str(mcb_expand.get("state") or "") != "running"
            )
        started = current_run.get("started_epoch")
        elapsed = ""
        if started:
            try:
                elapsed = f"{int(time.time() - float(started))}s"
            except (TypeError, ValueError):
                elapsed = ""
        jobs.append({
            "name": current_run.get("name") or "LeanMill run",
            "machine": _machine_label(current_run.get("machine")),
            "state": "complete" if inferred_complete else (current_run.get("state") or "running"),
            "phase": "completed proof drain" if inferred_complete else (current_run.get("phase") or "active"),
            "elapsed": elapsed,
            "progress": (
                f"{mill.get('path_a_done') or 0} rows drained; {status.get('bottleneck', {}).get('residual_compiler_residuals') or status.get('bottleneck', {}).get('path_c_residuals') or 0} residuals"
                if inferred_complete else (current_run.get("progress") or "running")
            ),
            "next_handoff": (
                status.get("bottleneck", {}).get("recommended_next_action")
                if inferred_complete else (current_run.get("next_handoff") or "wait for completion")
            ),
            "root": current_run.get("root") or "",
        })
    mcb_state = str(mcb_expand.get("state") or "unknown")
    if mcb_state == "running":
        jobs.append({
            "name": "MCB corpus expansion",
            "machine": "Remote",
            "state": "running",
            "phase": "building leak-tight candidate rows",
            "elapsed": mcb_expand.get("elapsed") or "",
            "progress": f"{mcb_expand.get('n') or 0}/{mcb_expand.get('target_n') or '?'} accepted",
            "next_handoff": "source qualification conveyor",
        })
    elif mcb_expand.get("n") is not None:
        jobs.append({
            "name": "MCB corpus expansion",
            "machine": "Remote",
            "state": "complete",
            "phase": "corpus emitted",
            "elapsed": mcb_expand.get("elapsed") or "",
            "progress": f"{mcb_expand.get('n')}/{mcb_expand.get('target_n') or '?'} accepted",
            "next_handoff": "source qualification conveyor",
        })
    if source_conveyor:
        packet = source_conveyor.get("source_packet") or {}
        summary = source_conveyor.get("pipeline_summary") or {}
        fallback = source_conveyor.get("static_filter_fallback") or {}
        context = source_conveyor.get("row_context_fallback") or {}
        if source_conveyor.get("phase") == "row_context_filter":
            checked = context.get("row_count")
            ready = context.get("row_context_ready_total")
            prefix = (
                f"{ready} target-site-ready / {checked} checked"
                if checked is not None and ready is not None
                else "target-site filter running"
            )
            progress = (
                f"{prefix}"
                f"{' on ' + str(context.get('current_file')) if context.get('current_file') else ''}; "
                f"{fallback.get('canary_ready_total', 0)} static canary candidates"
            )
            next_handoff = "intake buffer if row-context-ready rows exist"
        elif context:
            progress = (
                f"{context.get('row_context_ready_total', 0)} target-site-ready candidates; "
                f"{context.get('row_count', 0)} rows checked"
            )
            next_handoff = "intake buffer then bounded mill"
        elif source_conveyor.get("phase") == "static_filter_fallback" or fallback.get("state") == "running":
            mode = str(fallback.get("mode") or "per-row fallback")
            probe = fallback.get("current_probe_index")
            progress = (
                f"{mode} running"
                f"{' at probe ' + str(probe) if probe is not None else ''}; "
                f"{packet.get('usable_candidate_total', 0)} usable candidates"
            )
            next_handoff = "static filter result then row-context filter"
        elif fallback:
            progress = (
                f"{fallback.get('canary_ready_total', 0)} canary-ready after fallback; "
                f"{fallback.get('attempts', 0)} row probes"
            )
            next_handoff = "row-context filter then intake buffer"
        else:
            progress = (
                f"{summary.get('intake_ready_total', packet.get('row_count', 0))} intake-ready / "
                f"{packet.get('usable_candidate_total', 0)} usable candidates"
            )
            next_handoff = source_conveyor.get("next_handoff") or "intake buffer"
        jobs.append({
            "name": "Source qualification conveyor",
            "machine": "Remote",
            "state": "running" if fallback.get("state") == "running" or context.get("state") == "running" else (source_conveyor.get("state") or "unknown"),
            "phase": "static qualification" if fallback.get("state") == "running" else (source_conveyor.get("phase") or "source qualification"),
            "elapsed": "",
            "progress": progress,
            "next_handoff": next_handoff,
        })
    if latest_source_buffer and latest_source_buffer.get("state") == "present":
        sp = latest_source_buffer.get("source_packet") or {}
        rc = latest_source_buffer.get("row_context_filter") or latest_source_buffer.get("row_context_partial") or {}
        sf = latest_source_buffer.get("static_filter") or {}
        if rc:
            phase = "target-context qualification"
            progress = (
                f"{rc.get('row_context_ready_total', 0)} target-ready / "
                f"{rc.get('row_count', 0)} rows"
            )
            next_handoff = "intake buffer then proof execution"
            state = "ready" if rc.get("row_context_ready_total") else "blocked"
        elif sf:
            phase = "static qualification"
            progress = f"{sf.get('canary_ready_total', 0)} static canary candidates"
            next_handoff = "target-context qualification"
            state = "ready" if sf.get("canary_ready_total") else "blocked"
        elif sp:
            phase = "source buffer"
            progress = (
                f"{sp.get('usable_candidate_total', 0)} usable sources / "
                f"{sp.get('row_count', latest_source_buffer.get('queue_count', 0))} rows"
            )
            next_handoff = "static qualification when Lean slot is free"
            state = "ready" if sp.get("usable_candidate_total") else "blocked"
        else:
            phase = "source buffer"
            progress = f"{latest_source_buffer.get('queue_count', 0)} queued rows"
            next_handoff = "source acquisition"
            state = "ready" if latest_source_buffer.get("queue_count") else "idle"
        jobs.append({
            "name": "Latest source buffer",
            "machine": "Remote",
            "state": state,
            "phase": phase,
            "elapsed": "",
            "progress": progress,
            "next_handoff": next_handoff,
            "root": latest_source_buffer.get("root") or "",
        })
    if intake.get("ready_total") or mill.get("path_a_active_count"):
        jobs.append({
            "name": "Bounded proof mill",
            "machine": "Remote",
            "state": "running" if mill.get("path_a_active_count") else "ready",
            "phase": "proof execution and governance",
            "elapsed": "",
            "progress": f"{intake.get('ready_total') or 0} ready, {mill.get('path_a_active_count') or 0} active",
            "next_handoff": "governance gate or residual compiler",
        })
    if not jobs:
        jobs.append({
            "name": "No active run detected",
            "machine": "local/Remote",
            "state": "idle",
            "phase": "waiting for next qualified buffer",
            "elapsed": "",
            "progress": "0 active jobs",
            "next_handoff": "source or residual-family canary build",
        })
    return jobs


def _recent_repair_canaries(limit: int = 8) -> list[dict[str, Any]]:
    roots = []
    for pattern in (
        "/tmp/rung1/path_c*canary_drain*/scoreboard.json",
        "/tmp/rung1/path_c*canary_drain*/scoreboard_final.json",
        "/tmp/rung1/*repair*canary*drain*/scoreboard.json",
        "/tmp/rung1/*repair*canary*drain*/scoreboard_final.json",
        "/tmp/rung1/**/*.repair*/scoreboard_final.json",
        "/tmp/rung1/**/*repair*/scoreboard_final.json",
    ):
        roots.extend(Path("/").glob(pattern.lstrip("/")))
    unique = {str(path): path for path in roots}
    rows: list[dict[str, Any]] = []
    for scoreboard in unique.values():
        try:
            obj = json.loads(scoreboard.read_text(errors="ignore"))
        except (OSError, json.JSONDecodeError):
            continue
        schema = str(obj.get("schema") or "")
        if "repair-canary-scoreboard" not in schema:
            continue
        root = Path(str(obj.get("root") or scoreboard.parent))
        rows.append({
            "root": str(root),
            "packet": obj.get("packet") or "",
            "tests_total": int(obj.get("tests_total") or 0),
            "completed": int(obj.get("completed") or 0),
            "ratified_closure_count": int(obj.get("ratified_closure_count") or 0),
            "negative_control_fail_count": int(obj.get("negative_control_fail_count") or 0),
            "negative_control_unexpected_pass_count": int(obj.get("negative_control_unexpected_pass_count") or 0),
            "exact_gap_candidate_count": int(obj.get("exact_gap_candidate_count") or 0),
            "backend_artifact_reclassified_count": int(obj.get("backend_artifact_reclassified_count") or 0),
            "mtime_epoch": int(scoreboard.stat().st_mtime),
            "state": "passed" if int(obj.get("negative_control_unexpected_pass_count") or 0) == 0 else "failed_control",
        })
    rows.sort(key=lambda r: r["mtime_epoch"], reverse=True)
    return rows[:limit]


def _self_test() -> int:
    payload = build(argparse.Namespace(data_dir="/tmp/no_such_dir", out=None))
    assert payload["schema"] == "leansearch-factory-live-state-v1"
    assert len(payload["source_flows"]) == 2
    assert len(payload["station_flow"]) == 6
    assert payload["active_work"][0]["progress"] == "mechanized data unavailable"
    assert isinstance(payload["recent_repair_canaries"], list)
    print("leansearch_factory_live_state self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    obj = build(args)
    print(json.dumps({
        "out": args.out,
        "current_bottleneck": obj.get("current_bottleneck"),
        "mcb_expansion": obj.get("mcb_expansion"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
