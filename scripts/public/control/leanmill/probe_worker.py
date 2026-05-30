#!/usr/bin/env python3
"""Queue wrapper for bounded LeanMill proof probes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
import leanmill_family_specs as family_specs
import leanmill_learning_feedback_contract as learning_feedback
from leanmill_factory_config import FACTORY_POLICY, apply_profile_section


def _probe_signature(family: str, lane: str, tests: list[dict[str, Any]]) -> str:
    rows = []
    for test in tests:
        body = test.get("extra_body")
        if body is None:
            body = test.get("body_lines")
        if body is None and str(test.get("body") or ""):
            body = str(test.get("body") or "").splitlines()
        rows.append({
            "row_id": str(test.get("row_id") or ""),
            "candidate_name": str(test.get("candidate_name") or ""),
            "action_family": str(test.get("action_family") or ""),
            "test_kind": str(test.get("test_kind") or ""),
            "target_theorem_name": str(test.get("target_theorem_name") or ""),
            "target_line": int(test.get("target_line") or 0),
            "body_hash": hashlib.sha256("\n".join(str(x) for x in (body or [])).encode()).hexdigest()[:16],
        })
    material = json.dumps({"family": family, "lane": lane, "tests": sorted(rows, key=lambda r: json.dumps(r, sort_keys=True))}, sort_keys=True)
    return hashlib.sha256(material.encode()).hexdigest()


def _packet_tests_for_row(packet: dict[str, Any], *, family: str, row_id: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for pack in packet.get("packets") or []:
        if not isinstance(pack, dict):
            continue
        pack_family = str(pack.get("repair_family") or packet.get("repair_family") or "")
        if family and pack_family and pack_family != family:
            continue
        for test in pack.get("tests") or []:
            if not isinstance(test, dict):
                continue
            if str(test.get("row_id") or "") == row_id:
                out.append(test)
    return out


def _current_family_spec_fingerprints(payload: dict[str, Any]) -> dict[str, str]:
    packet = _read_json(str(payload.get("packet") or ""))
    if not packet:
        return {}
    family = str(payload.get("family") or packet.get("repair_family") or "")
    expected = payload.get("family_spec_template_fingerprints") or {}
    if not isinstance(expected, dict):
        return {}
    spec_path = Path(str(packet.get("parent_spec") or payload.get("family_spec_path") or ""))
    spec = family_specs._read_yaml(spec_path) if spec_path.exists() and spec_path.is_file() else {}
    templates = spec.get("templates") if isinstance(spec, dict) else []
    if not isinstance(templates, list):
        return {}
    expected_rows = {str(row_id or "") for row_id in expected if str(row_id or "")}
    tests_by_row: dict[str, list[dict[str, Any]]] = {}
    for template in templates:
        if not isinstance(template, dict):
            continue
        row_id = str(template.get("row_id") or "")
        if row_id not in expected_rows:
            continue
        tests_by_row.setdefault(row_id, []).append({
            "row_id": row_id,
            "candidate_name": "",
            "action_family": "manual_extra",
            "test_kind": str(template.get("test_kind") or ""),
            "extra_body": family_specs._template_body(template),
        })
    return {row_id: _probe_signature(family, "family_spec", tests) for row_id, tests in tests_by_row.items() if tests}


def _stale_family_spec_packet(payload: dict[str, Any]) -> dict[str, Any]:
    if _probe_lane(payload) != "family_spec":
        return {}
    expected = payload.get("family_spec_template_fingerprints") or {}
    if not isinstance(expected, dict) or not expected:
        return {}
    current = _current_family_spec_fingerprints(payload)
    stale_rows = []
    missing_rows = []
    for row_id, expected_fp in expected.items():
        row_id_s = str(row_id or "")
        if not row_id_s:
            continue
        actual_fp = str(current.get(row_id_s) or "")
        if not actual_fp:
            missing_rows.append(row_id_s)
        elif actual_fp != str(expected_fp or ""):
            stale_rows.append({"row_id": row_id_s, "expected": str(expected_fp or ""), "actual": actual_fp})
    if not stale_rows and not missing_rows:
        return {}
    return {
        "ok": True,
        "exit_kind": "stale_family_spec_probe_packet",
        "learning_unit_exit": "stale_family_spec_probe_packet",
        "heavy_lean_launched": False,
        "reason": "family_spec_template_fingerprint_mismatch",
        "stale_rows": stale_rows,
        "missing_rows": missing_rows,
        "required_resolution": "regenerate_probe_packet_from_current_family_spec",
    }


def _target_bound_family_spec_packet(payload: dict[str, Any]) -> dict[str, Any]:
    """Fail closed before heavy Lean when an old family-spec packet lacks a
    concrete target theorem binding.

    Target binding is part of the executable learning-unit identity. A
    pre-target-bound packet can otherwise run against the wrong theorem in a
    multi-theorem file and create false no-signal evidence.
    """
    if _probe_lane(payload) != "family_spec":
        return {}
    meta = payload.get("probe_corpus_meta") if isinstance(payload.get("probe_corpus_meta"), dict) else {}
    selected_targets = meta.get("selected_row_targets") if isinstance(meta.get("selected_row_targets"), dict) else {}
    if not selected_targets:
        return {
            "ok": True,
            "exit_kind": "target_resolution_debt_pre_probe",
            "learning_unit_exit": "target_resolution_debt_pre_probe",
            "heavy_lean_launched": False,
            "reason": "family_spec_probe_missing_selected_row_targets",
            "required_resolution": "regenerate_family_spec_probe_with_target_bound_seeder",
            "selected_row_ids": meta.get("selected_row_ids") or [],
            "family_spec_shard": payload.get("family_spec_shard") or {},
        }
    shard = payload.get("family_spec_shard") if isinstance(payload.get("family_spec_shard"), dict) else {}
    shard_rows: list[str] = []
    if str(shard.get("row_id") or ""):
        shard_rows.append(str(shard.get("row_id") or ""))
    raw_rows = shard.get("row_ids") or []
    if isinstance(raw_rows, str):
        shard_rows.append(raw_rows)
    elif isinstance(raw_rows, list):
        shard_rows.extend(str(row_id) for row_id in raw_rows if str(row_id or ""))
    if not shard_rows:
        packet = _read_json(str(payload.get("packet") or ""))
        family = str(payload.get("family") or packet.get("repair_family") or "")
        shard_rows = sorted({str(test.get("row_id") or "") for test in _packet_tests_for_row(packet, family=family, row_id="") if str(test.get("row_id") or "")})
    missing = []
    weak = []
    for row_id in shard_rows:
        target = selected_targets.get(row_id)
        if not isinstance(target, dict):
            missing.append(row_id)
            continue
        if not str(target.get("target_theorem_name") or "") or int(target.get("target_line") or 0) <= 0:
            weak.append({"row_id": row_id, "target": target})
    if not missing and not weak:
        return {}
    return {
        "ok": True,
        "exit_kind": "target_resolution_debt_pre_probe",
        "learning_unit_exit": "target_resolution_debt_pre_probe",
        "heavy_lean_launched": False,
        "reason": "family_spec_probe_incomplete_target_binding",
        "required_resolution": "regenerate_family_spec_probe_with_target_bound_seeder",
        "missing_target_rows": missing,
        "weak_target_rows": weak,
        "family_spec_shard": shard,
    }


def _probe_lane(payload: dict[str, Any]) -> str:
    return str(payload.get("probe_lane") or payload.get("lane") or "legacy")


def _lane_allowed(args: argparse.Namespace, payload: dict[str, Any]) -> bool:
    lane = _probe_lane(payload)
    include = set(args.probe_lane or [])
    exclude = set(args.exclude_probe_lane or [])
    if include and lane not in include:
        return False
    if exclude and lane in exclude:
        return False
    return True


def _claim_work_ids(args: argparse.Namespace) -> set[str]:
    work_ids = []
    for raw in getattr(args, "claim_work_id", None) or []:
        work_ids.extend(str(raw).split(","))
    return {work_id.strip() for work_id in work_ids if work_id.strip()}


def _selection_pairs(path: str) -> set[tuple[str, str]]:
    p = Path(path) if path else Path()
    if not path or not p.exists():
        return set()
    try:
        obj = json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return set()
    rows = obj.get("selected_rows") or obj.get("rows") or [] if isinstance(obj, dict) else []
    pairs: set[tuple[str, str]] = set()
    if not isinstance(rows, list):
        return pairs
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_id = str(row.get("row_id") or row.get("id") or row.get("target_id") or "")
        families = row.get("matched_families") or row.get("families") or []
        if isinstance(families, str):
            families = [families]
        for family in families:
            family_s = str(family or "")
            if row_id and family_s:
                pairs.add((family_s, row_id))
    return pairs


def _selection_allowed(args: argparse.Namespace, payload: dict[str, Any]) -> bool:
    pairs = _selection_pairs(getattr(args, "family_spec_selection", ""))
    if not pairs:
        return True
    if _probe_lane(payload) != "family_spec":
        return False
    family = str(payload.get("family") or "")
    shard = payload.get("family_spec_shard") or {}
    if not isinstance(shard, dict):
        return False
    row_ids = []
    if str(shard.get("row_id") or ""):
        row_ids.append(str(shard.get("row_id") or ""))
    rows_value = shard.get("row_ids") or []
    if isinstance(rows_value, str):
        row_ids.append(rows_value)
    elif isinstance(rows_value, list):
        row_ids.extend(str(x) for x in rows_value if str(x or ""))
    return any((family, row_id) in pairs for row_id in row_ids)


def _claim_allowed(args: argparse.Namespace, item: dict[str, Any]) -> bool:
    work_ids = _claim_work_ids(args)
    if work_ids and str(item.get("work_id") or "") not in work_ids:
        return False
    payload = item.get("payload") or {}
    return _lane_allowed(args, payload) and _selection_allowed(args, payload)


def _display_cmd(cmd: list[str]) -> list[str]:
    if cmd and Path(cmd[0]).resolve() == Path(sys.executable).resolve():
        return ["<python>", *cmd[1:]]
    return cmd


def _runtime_flag(payload: dict[str, Any], args: argparse.Namespace, payload_key: str, arg_name: str) -> bool:
    # Queue payloads are durable intent, but runtime/operator flags may safely
    # tighten execution for stale queued work. A stale false must not disable a
    # current true for speed/safety flags such as warm_repl_inline or no_cache.
    return bool(getattr(args, arg_name, False)) or bool(payload.get(payload_key))


def _runtime_int_floor(payload: dict[str, Any], args: argparse.Namespace, payload_key: str, arg_name: str) -> int:
    # Time budgets are safety/correctness floors: stale queued values may not
    # lower the live policy budget, but larger per-item budgets are preserved.
    vals = []
    for value in (payload.get(payload_key), getattr(args, arg_name, None)):
        try:
            vals.append(int(value))
        except (TypeError, ValueError):
            pass
    return max(vals) if vals else 0


def _runtime_int_cap(payload: dict[str, Any], args: argparse.Namespace, payload_key: str, arg_name: str) -> int:
    # Work-width knobs are cost caps: live policy can lower stale queued width.
    vals = []
    for value in (payload.get(payload_key), getattr(args, arg_name, None)):
        try:
            iv = int(value)
        except (TypeError, ValueError):
            continue
        if iv > 0:
            vals.append(iv)
    return min(vals) if vals else 0


def _run(cmd: list[str], *, timeout_s: int) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=max(1, int(timeout_s)))
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": _display_cmd(cmd),
            "returncode": 124,
            "stdout_tail": str(exc.stdout or "")[-3000:],
            "stderr_tail": (str(exc.stderr or "") + f"\nprobe command timed out after {timeout_s}s")[-3000:],
            "timed_out": True,
        }
    return {
        "cmd": _display_cmd(cmd),
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-3000:],
        "stderr_tail": proc.stderr[-3000:],
        "timed_out": False,
    }


def _required_probe_fields(payload: dict[str, Any]) -> list[str]:
    return [k for k in ("packet", "root", "corpus", "static_filter") if not str(payload.get(k) or "")]


def _read_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {}
    try:
        obj = json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _json_from_stdout_tail(text: str) -> dict[str, Any]:
    for line in reversed(str(text or "").splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return {}


def _probe_learning_exit(returncode: int, scoreboard_obj: dict[str, Any]) -> str:
    return learning_feedback.learning_exit_from_counts(scoreboard_obj, returncode=returncode)


def _scoreboard_path(payload: dict[str, Any], args: argparse.Namespace) -> str:
    explicit = str(payload.get("scoreboard") or "")
    if explicit:
        return explicit
    root = str(payload.get("root") or "")
    if root:
        return str(Path(root) / "scoreboard.json")
    return str(args.scoreboard)


def _fresh_json(path: str | Path, *, not_before: float) -> dict[str, Any]:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {}
    try:
        if p.stat().st_mtime < not_before - 1:
            return {}
    except OSError:
        return {}
    return _read_json(p)


def _scoreboard_file_exists(path: str | Path) -> bool:
    """Whether the scoreboard file is present on disk *at all*, regardless of
    freshness. Used to distinguish 'Lean wrote a stale scoreboard' (file
    present) from 'Lean crashed before writing' (file absent). The stdout
    fallback is honest only in the former case; in the latter, falling back
    to stdout risks misreading a partial mid-crash dump as the probe result.
    """
    p = Path(path)
    return p.exists() and p.is_file()


def probe(args: argparse.Namespace, payload: dict[str, Any]) -> dict[str, Any]:
    missing = _required_probe_fields(payload)
    if missing:
        return {
            "ok": True,
            "exit_kind": "operator_required",
            "reason": "probe_payload_missing_required_fields",
            "missing": missing,
            "heavy_lean_launched": False,
        }
    if not args.allow_heavy_lean:
        return {
            "ok": True,
            "exit_kind": "probe_ready_requires_explicit_heavy_lean",
            "reason": "rerun with --allow-heavy-lean to execute leansearch_repair_canary_drain.py",
            "heavy_lean_launched": False,
            "required_fields_present": True,
        }
    stale = _stale_family_spec_packet(payload)
    if stale:
        return stale
    target_debt = _target_bound_family_spec_packet(payload)
    if target_debt:
        return target_debt
    scoreboard = _scoreboard_path(payload, args)
    cmd = [
        sys.executable,
        "scripts/public/control/leanmill/search/repair_canary_drain.py",
        "--packet", str(payload["packet"]),
        "--root", str(payload["root"]),
        "--corpus", str(payload["corpus"]),
        "--static-filter", str(payload["static_filter"]),
        "--backend", str(payload.get("backend") or args.backend),
        "--timeout", str(_runtime_int_floor(payload, args, "timeout", "timeout")),
        "--test-wall-timeout", str(_runtime_int_floor(payload, args, "test_wall_timeout", "test_wall_timeout")),
        "--max-candidates", str(_runtime_int_cap(payload, args, "max_candidates", "max_candidates")),
        "--max-actions", str(_runtime_int_cap(payload, args, "max_actions", "max_actions")),
        "--scoreboard", scoreboard,
        "--limit", str(_runtime_int_floor(payload, args, "limit", "limit")),
        "--cache-dir", str(payload.get("cache_dir") or args.cache_dir),
        "--lean-slot-lock", str(payload.get("lean_slot_lock") or args.lean_slot_lock),
    ]
    if _runtime_flag(payload, args, "no_cache", "no_cache"):
        cmd.append("--no-cache")
    if bool(args.no_lean_slot_lock):
        cmd.append("--no-lean-slot-lock")
    if _runtime_flag(payload, args, "warm_repl_inline", "warm_repl_inline"):
        cmd.append("--warm-repl-inline")
    governance_required = bool(payload.get("governance_required")) or _probe_lane(payload) == "family_spec"
    if governance_required or _runtime_flag(payload, args, "govern_winners", "govern_winners"):
        cmd.append("--govern-winners")
    launch_started = time.time()
    result = _run(cmd, timeout_s=_runtime_int_floor(payload, args, "command_timeout_s", "command_timeout_s"))
    scoreboard_obj = _fresh_json(scoreboard, not_before=launch_started)
    scoreboard_source = "fresh_file"
    if not scoreboard_obj:
        # 2026-05-23 tightening: distinguish "stale scoreboard on disk" (file
        # present, mtime older than launch) from "no scoreboard at all" (file
        # absent — Lean likely crashed before writing). In the second case,
        # falling back to stdout may misclassify a partial mid-crash dump as
        # the probe result. Only honour stdout fallback when the scoreboard
        # file actually exists on disk; otherwise return an empty scoreboard
        # and let the exit classifier interpret the result honestly.
        if _scoreboard_file_exists(scoreboard):
            scoreboard_obj = _json_from_stdout_tail(result.get("stdout_tail") or "")
            scoreboard_source = "stdout_fallback_after_stale_file"
        else:
            scoreboard_obj = {}
            scoreboard_source = "absent_no_fallback"
    scoreboard_summary = {
        key: scoreboard_obj.get(key)
        for key in (
            "score",
            "completed",
            "skipped",
            "tests_total",
            "ratified_closure_count",
            "exact_gap_candidate_count",
            "valid_falsifier_count",
            "negative_control_fail_count",
            "negative_control_unexpected_pass_count",
            "compile_candidate_count",
            "cache_hit_count",
            "row_outcomes",
        )
        if key in scoreboard_obj
    }
    learning_exit = _probe_learning_exit(result["returncode"], scoreboard_obj)
    return {
        "ok": result["returncode"] == 0,
        "exit_kind": learning_exit,
        "learning_unit_exit": learning_exit,
        "heavy_lean_launched": True,
        "result": result,
        "scoreboard": scoreboard,
        "scoreboard_source": scoreboard_source,
        **scoreboard_summary,
    }


def work_once(args: argparse.Namespace) -> dict[str, Any]:
    if not args.allow_heavy_lean:
        return {
            "claimed": False,
            "reason": "probe_worker_requires_allow_heavy_lean_before_claim",
            "heavy_lean_launched": False,
        }
    cx = work_queue.connect(args.queue_db)
    kinds = ["repair_canary_probe", "proof_probe"]
    if args.claim_station_residual:
        kinds.append("station:residual_curriculum")
    scan_limit = int(args.claim_scan_limit or 100)
    if _claim_work_ids(args):
        scan_limit = max(scan_limit, 10000)
    item = work_queue.claim_matching(
        cx,
        worker_id=args.worker_id,
        kinds=kinds,
        lease_s=args.lease_s,
        scan_limit=scan_limit,
        predicate=lambda obj: _claim_allowed(args, obj),
    )
    if not item:
        return {"claimed": False}
    work_queue.update_status(cx, work_id=item["work_id"], status="running")
    work_queue.append_event(args.events, {"event_type": "probe_worker_started", "work_id": item["work_id"], "payload": item})
    try:
        result = probe(args, item.get("payload") or {})
    except Exception as exc:  # noqa: BLE001 - queue workers must terminalize exceptions.
        result = {
            "ok": False,
            "exit_kind": "probe_worker_exception",
            "learning_unit_exit": "probe_worker_exception",
            "heavy_lean_launched": False,
            "exception_type": type(exc).__name__,
            "exception": str(exc)[-1000:],
        }
    status = "done" if result["ok"] else "failed"
    work_queue.update_status(cx, work_id=item["work_id"], status=status, payload_update=result)
    artifacts = [result.get("scoreboard")] if result.get("scoreboard") else []
    work_queue.append_event(args.events, {
        "event_type": f"probe_worker_{status}",
        "work_id": item["work_id"],
        "payload": result,
        "artifact_paths": artifacts,
    })
    return {
        "claimed": True,
        "work_id": item["work_id"],
        "status": status,
        "ok": result["ok"],
        "probe_lane": _probe_lane(item.get("payload") or {}),
        "heavy_lean_launched": result.get("heavy_lean_launched"),
    }


def daemon_loop(args: argparse.Namespace) -> dict[str, Any]:
    import time
    cx = work_queue.connect(args.queue_db)
    reclaimed = work_queue.reclaim_worker_claims(cx, worker_id=args.worker_id)
    if reclaimed:
        work_queue.append_event(args.events, {
            "event_type": "probe_worker_startup_reclaimed_own_claims",
            "worker_id": args.worker_id,
            "payload": {"reclaimed_count": reclaimed},
        })
    completed = 0
    idle_ticks = 0
    while True:
        if args.max_tasks and completed >= args.max_tasks:
            break
        result = work_once(args)
        if result.get("claimed"):
            completed += 1
            idle_ticks = 0
            print(json.dumps({"daemon": args.worker_id, "task_result": result}, sort_keys=True), flush=True)
            continue
        idle_ticks += 1
        print(json.dumps({"daemon": args.worker_id, "idle": True, "idle_ticks": idle_ticks}, sort_keys=True), flush=True)
        if args.max_idle_ticks and idle_ticks >= args.max_idle_ticks:
            break
        time.sleep(max(1, int(args.idle_sleep_s)))
    return {"daemon": args.worker_id, "completed_tasks": completed}


def _self_test() -> int:
    assert _required_probe_fields({"packet": "p"}) == ["root", "corpus", "static_filter"]
    assert _read_json("/path/that/does/not/exist") == {}
    assert _json_from_stdout_tail('x\n{"score": 1}\n')["score"] == 1
    assert _probe_learning_exit(1, {}) == "probe_failed"
    assert _probe_learning_exit(0, {"negative_control_unexpected_pass_count": 1}) == "failed_negative_control"
    assert _probe_learning_exit(0, {"negative_control_invalid_fail_count": 1, "ratified_closure_count": 1}) == "invalid_negative_control"
    assert _probe_learning_exit(0, {"ratified_closure_count": 1, "negative_control_fail_count": 1}) == "ratified_closure"
    assert _probe_learning_exit(0, {"exact_gap_candidate_count": 1}) == "exact_gap_candidate"
    assert _probe_learning_exit(0, {"valid_falsifier_count": 1}) == "valid_falsifier"
    assert _probe_learning_exit(0, {"negative_control_fail_count": 1}) == "tested_no_positive_signal"
    assert _scoreboard_path({"root": "/tmp/leanmill-root"}, argparse.Namespace(scoreboard="/tmp/shared.json")) == "/tmp/leanmill-root/scoreboard.json"
    ns = argparse.Namespace(probe_lane=["family_spec"], exclude_probe_lane=[], claim_scan_limit=10, family_spec_selection="", claim_work_id=None)
    assert _lane_allowed(ns, {"probe_lane": "family_spec"})
    assert not _lane_allowed(ns, {"probe_lane": "source_shape"})
    ns = argparse.Namespace(probe_lane=[], exclude_probe_lane=["source_shape"], claim_scan_limit=10, family_spec_selection="", claim_work_id=None)
    assert _lane_allowed(ns, {"probe_lane": "family_spec"})
    assert not _lane_allowed(ns, {"probe_lane": "source_shape"})
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_probe_worker_selection_") as td:
        sel = Path(td) / "selection.json"
        sel.write_text(json.dumps({"selected_rows": [{"row_id": "r1", "matched_families": ["fam"]}]}) + "\n")
        sns = argparse.Namespace(family_spec_selection=str(sel))
        assert _selection_allowed(sns, {"probe_lane": "family_spec", "family": "fam", "family_spec_shard": {"row_id": "r1"}})
        assert _selection_allowed(sns, {"probe_lane": "family_spec", "family": "fam", "family_spec_shard": {"mode": "rows", "row_ids": ["r0", "r1"]}})
        assert not _selection_allowed(sns, {"probe_lane": "family_spec", "family": "fam", "family_spec_shard": {"row_id": "r2"}})
        assert not _selection_allowed(sns, {"probe_lane": "source_shape", "family": "fam", "family_spec_shard": {"row_id": "r1"}})
        qns = argparse.Namespace(probe_lane=["family_spec"], exclude_probe_lane=[], claim_scan_limit=10, family_spec_selection=str(sel), claim_work_id=None)
        assert _claim_allowed(qns, {"work_id": "w1", "payload": {"probe_lane": "family_spec", "family": "fam", "family_spec_shard": {"row_id": "r1"}}})
        assert not _claim_allowed(qns, {"work_id": "w2", "payload": {"probe_lane": "family_spec", "family": "fam", "family_spec_shard": {"row_id": "r2"}}})
        qns_exact = argparse.Namespace(probe_lane=["family_spec"], exclude_probe_lane=[], claim_scan_limit=10, family_spec_selection="", claim_work_id=["w1,w3"])
        assert _claim_allowed(qns_exact, {"work_id": "w1", "payload": {"probe_lane": "family_spec"}})
        assert not _claim_allowed(qns_exact, {"work_id": "w2", "payload": {"probe_lane": "family_spec"}})
        spec = Path(td) / "fam.yaml"
        spec.write_text("""family: fam
templates:
  - id: pos
    row_id: r1
    test_kind: positive
    body: exact h
""")
        packet = Path(td) / "packet.json"
        packet.write_text(json.dumps({"repair_family": "fam", "parent_spec": str(spec), "packets": []}) + "\n")
        fp = _probe_signature("fam", "family_spec", [{"row_id": "r1", "candidate_name": "", "action_family": "manual_extra", "test_kind": "positive", "extra_body": ["pos::exact h"]}])
        assert not _stale_family_spec_packet({"probe_lane": "family_spec", "family": "fam", "packet": str(packet), "family_spec_template_fingerprints": {"r1": fp}})
        spec.write_text("""family: fam
templates:
  - id: pos
    row_id: r1
    test_kind: positive
    body: exact h2
""")
        stale = _stale_family_spec_packet({"probe_lane": "family_spec", "family": "fam", "packet": str(packet), "family_spec_template_fingerprints": {"r1": fp}})
        assert stale["exit_kind"] == "stale_family_spec_probe_packet" and stale["heavy_lean_launched"] is False
        target_debt = _target_bound_family_spec_packet({"probe_lane": "family_spec", "family": "fam", "family_spec_shard": {"row_id": "r1"}, "probe_corpus_meta": {"selected_row_ids": ["r1"]}})
        assert target_debt["exit_kind"] == "target_resolution_debt_pre_probe" and target_debt["heavy_lean_launched"] is False
        assert not _target_bound_family_spec_packet({
            "probe_lane": "family_spec",
            "family": "fam",
            "family_spec_shard": {"row_id": "r1"},
            "probe_corpus_meta": {"selected_row_targets": {"r1": {"target_theorem_name": "foo", "target_line": 7}}},
        })
    assert _runtime_flag({"warm_repl_inline": False}, argparse.Namespace(warm_repl_inline=True), "warm_repl_inline", "warm_repl_inline")
    assert _runtime_flag({"warm_repl_inline": True}, argparse.Namespace(warm_repl_inline=False), "warm_repl_inline", "warm_repl_inline")
    assert not _runtime_flag({"warm_repl_inline": False}, argparse.Namespace(warm_repl_inline=False), "warm_repl_inline", "warm_repl_inline")
    assert _runtime_flag({"govern_winners": False}, argparse.Namespace(govern_winners=True), "govern_winners", "govern_winners")
    assert _runtime_int_floor({"command_timeout_s": 900}, argparse.Namespace(command_timeout_s=1200), "command_timeout_s", "command_timeout_s") == 1200
    assert _runtime_int_cap({"max_candidates": 4}, argparse.Namespace(max_candidates=1), "max_candidates", "max_candidates") == 1
    assert _runtime_int_floor({"limit": 8}, argparse.Namespace(limit=2), "limit", "limit") == 8
    print("leanmill_probe_worker self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--factory-policy", default=FACTORY_POLICY)
    ap.add_argument("--policy-profile", default=os.environ.get("LEANMILL_POLICY_PROFILE", "supervised_24x7"))
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--worker-id", default="probe-worker-local")
    ap.add_argument("--lease-s", type=int, default=3600)
    ap.add_argument("--claim-station-residual", action="store_true")
    ap.add_argument("--probe-lane", action="append", default=[], help="Only claim probe work whose payload probe_lane matches this value; repeatable.")
    ap.add_argument("--family-spec-selection", default="", help="Optional C-slice selection JSON; when set, only claim selected family_spec (family,row) probe work.")
    ap.add_argument("--exclude-probe-lane", action="append", default=[], help="Do not claim probe work whose payload probe_lane matches this value; repeatable.")
    ap.add_argument("--claim-work-id", action="append", default=None, help="Only claim these exact work ids; repeatable or comma-separated.")
    ap.add_argument("--claim-scan-limit", type=int, default=100)
    ap.add_argument("--allow-heavy-lean", action="store_true")
    ap.add_argument("--backend", default="repl_file")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--test-wall-timeout", type=int, default=180)
    ap.add_argument("--command-timeout-s", type=int, default=900)
    ap.add_argument("--max-candidates", type=int, default=2)
    ap.add_argument("--max-actions", type=int, default=2)
    ap.add_argument("--limit", type=int, default=1)
    ap.add_argument("--govern-winners", action="store_true")
    ap.add_argument("--scoreboard", default="/tmp/rung1/leanmill_probe_worker_scoreboard.json")
    ap.add_argument("--cache-dir", default="/tmp/rung1/leanmill_canary_result_cache")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--lean-slot-lock", default="/tmp/rung1/leanmill_heavy_lean.lock")
    ap.add_argument("--no-lean-slot-lock", action="store_true")
    ap.add_argument("--warm-repl-inline", action="store_true")
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--idle-sleep-s", type=int, default=15)
    ap.add_argument("--max-tasks", type=int, default=0)
    ap.add_argument("--max-idle-ticks", type=int, default=0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    policy_receipt = apply_profile_section(args, section="probe_worker")
    setattr(args, "policy_receipt", policy_receipt)
    if args.daemon:
        print(json.dumps(daemon_loop(args), sort_keys=True))
        return 0
    result = work_once(args)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok", True) is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
