#!/usr/bin/env python3
"""Drain executable repair-canary packets.

This is the Residual Compiler work executor. It reads packet/test records,
runs bounded Lean action smokes, and separates positive repair tests from
negative controls. Compile-only wins are routed to governance; only Governance
Gate-ratified closures count as score.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import multiprocessing as mp
import os
import shutil
import signal
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import leansearch_action_smoke as smoke
import leanmill_learning_feedback_contract as learning_feedback


DEFAULT_CORPUS = "/tmp/rung1/mcb_corpus_v2.json"
DEFAULT_PACKET = "analytics/public/leanmill/dashboard_data/residual_family_canary_packets.json"
DEFAULT_CACHE_DIR = "/tmp/rung1/leanmill_canary_result_cache"
DEFAULT_LEAN_SLOT_LOCK = "/tmp/rung1/leanmill_heavy_lean.lock"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(errors="ignore"))


def _append_jsonl(path: Path, rec: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha_file(path: str) -> str:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _cache_key(payload: dict[str, Any], wall_timeout: int) -> str:
    key_obj = {
        "schema": "leanmill-canary-cache-key-v1",
        "row_id": payload.get("row_id"),
        "corpus": payload.get("corpus"),
        "corpus_sha256": _sha_file(str(payload.get("corpus") or "")),
        "static_filter": payload.get("static_filter"),
        "static_filter_sha256": _sha_file(str(payload.get("static_filter") or "")),
        "backend": payload.get("backend"),
        "timeout": payload.get("timeout"),
        "wall_timeout": wall_timeout,
        "max_candidates": payload.get("max_candidates"),
        "max_actions": payload.get("max_actions"),
        "govern_winners": payload.get("govern_winners"),
        "extra_body": payload.get("extra_body") or [],
        "action_family": payload.get("action_family") or [],
        "candidate_name": payload.get("candidate_name") or [],
        "test_kind": payload.get("test_kind"),
        "source_credit_eligible": payload.get("source_credit_eligible"),
        "clean_solver_credit_eligible": payload.get("clean_solver_credit_eligible"),
        "credit_type": payload.get("credit_type"),
        "score_candidates": payload.get("score_candidates"),
        "require_positive_source_action": payload.get("require_positive_source_action"),
    }
    return hashlib.sha256(_stable_json(key_obj).encode("utf-8")).hexdigest()


@contextlib.contextmanager
def _heavy_lean_slot(lock_path: str | None):
    if not lock_path:
        yield
        return
    p = Path(lock_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


OPERATIONAL_ERROR_CLASSES = {"worker_exception", "outer_wall_timeout"}
OPERATIONAL_EXCEPTION_MARKERS = {"KeyboardInterrupt", "SystemExit"}


def _is_cacheable_result(obj: dict[str, Any]) -> bool:
    """Return false for harness/process failures that need a fresh retry."""
    if obj.get("worker_exception") or obj.get("worker_missing_result") or obj.get("outer_wall_timeout"):
        return False
    for result in obj.get("results") or []:
        if not isinstance(result, dict):
            continue
        if str(result.get("error_class") or "") in OPERATIONAL_ERROR_CLASSES:
            return False
        tails = "\n".join(str(result.get(k) or "") for k in ("stdout_tail", "stderr_tail"))
        if any(marker in tails for marker in OPERATIONAL_EXCEPTION_MARKERS):
            return False
    return True


def _load_cached_result(cache_dir: str | None, key: str, out: Path) -> dict[str, Any] | None:
    if not cache_dir:
        return None
    cache_path = Path(cache_dir) / f"{key}.json"
    if not cache_path.exists():
        return None
    obj = json.loads(cache_path.read_text(errors="ignore"))
    if not _is_cacheable_result(obj):
        cache_path.unlink(missing_ok=True)
        return None
    obj["cache_hit"] = True
    obj["cache_key"] = key
    obj["cache_path"] = str(cache_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    return obj


def _store_cached_result(cache_dir: str | None, key: str, source_path: Path) -> None:
    if not cache_dir or not source_path.exists():
        return
    obj = json.loads(source_path.read_text(errors="ignore"))
    if not _is_cacheable_result(obj):
        return
    cache_path = Path(cache_dir) / f"{key}.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        return
    shutil.copyfile(source_path, cache_path)


def _overwrite_cached_result(cache_dir: str | None, key: str, source_path: Path) -> None:
    if not cache_dir or not source_path.exists():
        return
    obj = json.loads(source_path.read_text(errors="ignore"))
    if not _is_cacheable_result(obj):
        return
    cache_path = Path(cache_dir) / f"{key}.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, cache_path)


def _smoke_worker(payload: dict[str, Any], q: mp.Queue) -> None:
    try:
        if hasattr(os, "setsid"):
            os.setsid()
        obj = smoke.run(
            str(payload["row_id"]),
            Path(str(payload["corpus"])),
            Path(str(payload["static_filter"])),
            Path(str(payload["out"])),
            int(payload["timeout"]),
            int(payload["max_candidates"]),
            int(payload["max_actions"]),
            Path(str(payload["drivers_dir"])),
            bool(payload["govern_winners"]),
            list(payload.get("extra_body") or []),
            list(payload.get("action_family") or []),
            list(payload.get("candidate_name") or []),
            str(payload["backend"]),
            bool(payload["score_candidates"]),
            bool(payload["require_positive_source_action"]),
        )
        q.put({"ok": True, "obj": obj})
    except BaseException as exc:  # noqa: BLE001 - child failure must become a residual, not kill the drain.
        q.put({"ok": False, "error": repr(exc)})


def _run_smoke_inline(payload: dict[str, Any], persistent_repl: Any | None = None) -> dict[str, Any]:
    try:
        obj = smoke.run(
            str(payload["row_id"]),
            Path(str(payload["corpus"])),
            Path(str(payload["static_filter"])),
            Path(str(payload["out"])),
            int(payload["timeout"]),
            int(payload["max_candidates"]),
            int(payload["max_actions"]),
            Path(str(payload["drivers_dir"])),
            bool(payload["govern_winners"]),
            list(payload.get("extra_body") or []),
            list(payload.get("action_family") or []),
            list(payload.get("candidate_name") or []),
            str(payload["backend"]),
            bool(payload["score_candidates"]),
            bool(payload["require_positive_source_action"]),
            persistent_repl=persistent_repl,
        )
        return dict(obj or {})
    except BaseException as exc:  # noqa: BLE001
        obj = {
            "schema": "leansearch-action-smoke-v1",
            "row_id": payload["row_id"],
            "corpus": payload["corpus"],
            "static_filter": payload["static_filter"],
            "backend": payload["backend"],
            "results": [{
                "row_id": payload["row_id"],
                "candidate": None,
                "action_family": (payload.get("action_family") or [""])[0],
                "closed": False,
                "timed_out": False,
                "error_class": "worker_exception",
                "seconds": 0,
                "stdout_tail": repr(exc)[-3000:],
                "stderr_tail": "",
            }],
            "closed_candidates": [],
            "ratified_candidates": [],
            "n_closed": 0,
            "n_ratified": 0,
            "worker_exception": repr(exc),
        }
        Path(str(payload["out"])).parent.mkdir(parents=True, exist_ok=True)
        Path(str(payload["out"])).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
        return obj


def _run_smoke_bounded(payload: dict[str, Any], wall_timeout: int) -> dict[str, Any]:
    q: mp.Queue = mp.Queue(maxsize=1)
    proc = mp.Process(target=_smoke_worker, args=(payload, q))
    proc.start()
    proc.join(max(1, wall_timeout))
    if proc.is_alive():
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except Exception:
            proc.terminate()
        proc.join(5)
        if proc.is_alive():
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                proc.kill()
            proc.join(5)
        obj = {
            "schema": "leansearch-action-smoke-v1",
            "row_id": payload["row_id"],
            "corpus": payload["corpus"],
            "static_filter": payload["static_filter"],
            "backend": payload["backend"],
            "timeout": payload["timeout"],
            "max_candidates": payload["max_candidates"],
            "max_actions": payload["max_actions"],
            "action_family_filter": payload.get("action_family") or [],
            "candidate_name_filter": payload.get("candidate_name") or [],
            "results": [{
                "row_id": payload["row_id"],
                "candidate": payload.get("candidate_name", [None])[0] if payload.get("candidate_name") else None,
                "action_family": (payload.get("action_family") or [""])[0],
                "closed": False,
                "timed_out": True,
                "error_class": "outer_wall_timeout",
                "seconds": wall_timeout,
                "stdout_tail": f"repair-canary outer wall timeout after {wall_timeout}s",
                "stderr_tail": "",
            }],
            "closed_candidates": [],
            "ratified_candidates": [],
            "n_closed": 0,
            "n_ratified": 0,
            "outer_wall_timeout": True,
        }
        Path(str(payload["out"])).parent.mkdir(parents=True, exist_ok=True)
        Path(str(payload["out"])).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
        return obj
    if not q.empty():
        rec = q.get()
        if rec.get("ok"):
            return dict(rec.get("obj") or {})
        obj = {
            "schema": "leansearch-action-smoke-v1",
            "row_id": payload["row_id"],
            "corpus": payload["corpus"],
            "static_filter": payload["static_filter"],
            "backend": payload["backend"],
            "results": [{
                "row_id": payload["row_id"],
                "candidate": None,
                "action_family": (payload.get("action_family") or [""])[0],
                "closed": False,
                "timed_out": False,
                "error_class": "worker_exception",
                "seconds": 0,
                "stdout_tail": str(rec.get("error") or "")[-3000:],
                "stderr_tail": "",
            }],
            "closed_candidates": [],
            "ratified_candidates": [],
            "n_closed": 0,
            "n_ratified": 0,
            "worker_exception": rec.get("error"),
        }
        Path(str(payload["out"])).parent.mkdir(parents=True, exist_ok=True)
        Path(str(payload["out"])).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
        return obj
    obj = {
        "schema": "leansearch-action-smoke-v1",
        "row_id": payload["row_id"],
        "corpus": payload["corpus"],
        "static_filter": payload["static_filter"],
        "backend": payload["backend"],
        "results": [],
        "closed_candidates": [],
        "ratified_candidates": [],
        "n_closed": 0,
        "n_ratified": 0,
        "worker_missing_result": True,
    }
    Path(str(payload["out"])).parent.mkdir(parents=True, exist_ok=True)
    Path(str(payload["out"])).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    return obj


def _tests_from_packets(obj: dict[str, Any], default_static_filter: str) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    for packet in obj.get("packets") or []:
        family = str(packet.get("repair_family") or "")
        if packet.get("tests"):
            for t in packet.get("tests") or []:
                tests.append({**t, "repair_family": t.get("repair_family") or family})
            continue
        for row in packet.get("selected_rows") or []:
            rid = str(row.get("row_id") or "")
            for name in row.get("candidate_names") or []:
                tests.append({
                    "packet_id": f"{family}:{rid}:{name}:direct_apply",
                    "repair_family": family,
                    "row_id": rid,
                    "candidate_name": str(name),
                    "action_family": "apply_easy",
                    "test_kind": "positive",
                    "expected_outcome": "closure_or_typed_residual",
                    "source_credit_eligible": False,
                    "clean_solver_credit_eligible": False,
                    "credit_type": "repair_canary_probe",
                    "static_filter": default_static_filter,
                })
    return tests


def _event_base(args: argparse.Namespace, test: dict[str, Any], result: dict[str, Any], elapsed: float) -> dict[str, Any]:
    return {
        "schema": "leanmill-repair-canary-event-v1",
        "created_at": _now_iso(),
        "packet_id": test.get("packet_id"),
        "repair_family": test.get("repair_family"),
        "row_id": test.get("row_id"),
        "candidate_name": test.get("candidate_name"),
        "action_family": test.get("action_family"),
        "test_kind": test.get("test_kind", "positive"),
        "expected_outcome": test.get("expected_outcome"),
        "source_credit_eligible": bool(test.get("source_credit_eligible")),
        "clean_solver_credit_eligible": bool(test.get("clean_solver_credit_eligible")),
        "result_path": result.get("out"),
        "cycle_s": round(elapsed, 3),
    }


def _apply_test_credit_boundary(obj: dict[str, Any], test: dict[str, Any]) -> bool:
    expected_source_credit = bool(test.get("source_credit_eligible"))
    expected_credit_kind = str(test.get("credit_type") or ("source_action" if expected_source_credit else "repair_canary_probe"))
    changed = False
    for result in obj.get("results") or []:
        if not isinstance(result, dict):
            continue
        if bool(result.get("source_credit_eligible")) != expected_source_credit:
            result["source_credit_eligible"] = expected_source_credit
            changed = True
        if not expected_source_credit and result.get("credit_kind") == "source_action":
            result["credit_kind"] = expected_credit_kind
            changed = True
    return changed


def run(args: argparse.Namespace) -> dict[str, Any]:
    packet = _read_json(Path(args.packet))
    root = Path(args.root)
    events = root / "events"
    results_dir = root / "rows"
    checkpoint = root / "checkpoint.jsonl"
    root.mkdir(parents=True, exist_ok=True)
    done: set[str] = set()
    if args.resume and checkpoint.exists():
        for line in checkpoint.read_text(errors="ignore").splitlines():
            if line.strip():
                rec = json.loads(line)
                if rec.get("status") == "done":
                    done.add(str(rec.get("test_id")))
    tests = _tests_from_packets(packet, args.static_filter)
    if args.limit is not None:
        tests = tests[: args.limit]

    completed = skipped = ratified = compile_closed = negative_expected_fail = negative_unexpected_pass = 0
    negative_invalid_fail = 0
    exact_gap_candidates = 0
    row_outcomes: dict[str, dict[str, Any]] = {}
    backend_artifact_reclassified = 0
    cache_hits = 0
    shared_repl = None
    warm_repl_enabled = args.warm_repl_inline and args.backend in {"repl", "repl_file", "repl_step"}
    with contextlib.ExitStack() as lean_stack:
        if warm_repl_enabled and not args.no_lean_slot_lock:
            lean_stack.enter_context(_heavy_lean_slot(args.lean_slot_lock))
        if warm_repl_enabled:
            sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
            from src.ztare.formal.lean_persistent import PersistentLean
            shared_repl = PersistentLean(smoke._lean_cwd())  # noqa: SLF001 - same harness module owns the cwd helper.
        for i, test in enumerate(tests, start=1):
            tid = str(test.get("packet_id") or f"test_{i}")
            if tid in done:
                skipped += 1
                continue
            row_id = str(test.get("row_id") or "")
            row_outcome = row_outcomes.setdefault(row_id, {
                "row_id": row_id,
                "completed": 0,
                "ratified_closure_count": 0,
                "compile_candidate_count": 0,
                "negative_control_fail_count": 0,
                "negative_control_unexpected_pass_count": 0,
                "negative_control_invalid_fail_count": 0,
                "exact_gap_candidate_count": 0,
            })
            out = results_dir / f"{i:04d}_{row_id}.json"
            family = str(test.get("action_family") or "")
            t0 = time.monotonic()
            inner_timeout = int(test.get("timeout") or args.timeout)
            wall_timeout = int(test.get("wall_timeout") or args.test_wall_timeout or max(inner_timeout + 45, 90))
            governance_required = (
                str(test.get("test_kind") or "") != "negative_control"
                and str(test.get("credit_type") or "") == "repair_family_spec_probe"
            )
            smoke_payload = {
                "row_id": row_id,
                "corpus": args.corpus,
                "static_filter": str(test.get("static_filter") or args.static_filter),
                "out": str(out),
                "timeout": inner_timeout,
                "max_candidates": int(test.get("max_candidates") or args.max_candidates),
                "max_actions": int(test.get("max_actions") or args.max_actions),
                "drivers_dir": str(results_dir / "drivers"),
                "govern_winners": bool((args.govern_winners or governance_required) and test.get("test_kind") != "negative_control"),
                "extra_body": list(test.get("extra_body") or []),
                "action_family": [family] if family else [],
                "candidate_name": [str(test.get("candidate_name"))] if test.get("candidate_name") else [],
                "backend": str(test.get("backend") or args.backend),
                "score_candidates": bool(args.score_candidates or test.get("score_candidates")),
                "require_positive_source_action": bool(args.require_positive_source_action or test.get("require_positive_source_action")),
                "test_kind": str(test.get("test_kind") or ""),
                "source_credit_eligible": bool(test.get("source_credit_eligible")),
                "clean_solver_credit_eligible": bool(test.get("clean_solver_credit_eligible")),
                "credit_type": str(test.get("credit_type") or ""),
            }
            key = _cache_key(smoke_payload, wall_timeout)
            obj = _load_cached_result(args.cache_dir if not args.no_cache else None, key, out)
            if obj is not None:
                cache_hits += 1
            else:
                per_row_lock_path = None if (args.no_lean_slot_lock or warm_repl_enabled) else args.lean_slot_lock
                with _heavy_lean_slot(per_row_lock_path):
                    if args.warm_repl_inline:
                        obj = _run_smoke_inline(smoke_payload, persistent_repl=shared_repl)
                    else:
                        obj = _run_smoke_bounded(smoke_payload, wall_timeout)
                obj["cache_key"] = key
                obj["cache_hit"] = False
                Path(str(smoke_payload["out"])).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
                _store_cached_result(args.cache_dir if not args.no_cache else None, key, out)
            if _apply_test_credit_boundary(obj, test):
                Path(str(smoke_payload["out"])).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
                _overwrite_cached_result(args.cache_dir if not args.no_cache else None, key, out)
            elapsed = time.monotonic() - t0
            base = _event_base(args, test, {"out": str(out)}, elapsed)
            n_closed = int(obj.get("n_closed") or 0)
            n_ratified = int(obj.get("n_ratified") or 0)
            is_negative = str(test.get("test_kind") or "") == "negative_control"
            is_exact_gap_candidate = str(test.get("candidate_kind") or "") == "exact_gap_candidate"
            if is_negative:
                if n_closed or n_ratified:
                    negative_unexpected_pass += 1
                    row_outcome["negative_control_unexpected_pass_count"] += 1
                    _append_jsonl(events / "negative_controls.jsonl", {**base, "event": "negative_control_unexpected_pass"})
                elif learning_feedback.negative_control_invalid_failure(obj):
                    negative_invalid_fail += 1
                    row_outcome["negative_control_invalid_fail_count"] += 1
                    _append_jsonl(events / "negative_controls.jsonl", {**base, "event": "negative_control_invalid_fail", "reason": "malformed_negative_control_failure"})
                else:
                    negative_expected_fail += 1
                    row_outcome["negative_control_fail_count"] += 1
                    _append_jsonl(events / "negative_controls.jsonl", {**base, "event": "negative_control_expected_fail"})
            elif is_exact_gap_candidate:
                exact_gap_candidates += 1
                row_outcome["exact_gap_candidate_count"] += 1
                _append_jsonl(events / "exact_gap_candidates.jsonl", {
                    **base,
                    "event": "exact_gap_candidate",
                    "validated": False,
                    "canary_spec": test.get("canary_spec"),
                    "note": "Candidate exact gaps require separate formal statement/falsifier validation before value credit.",
                })
            elif n_ratified:
                ratified += n_ratified
                row_outcome["ratified_closure_count"] += n_ratified
                _append_jsonl(events / "closed.jsonl", {**base, "event": "ratified_closure", "ratified_candidates": obj.get("ratified_candidates", [])})
            elif n_closed:
                compile_closed += n_closed
                row_outcome["compile_candidate_count"] += n_closed
                _append_jsonl(events / "to_govern.jsonl", {**base, "event": "compile_closed_needs_governance", "closed_candidates": obj.get("closed_candidates", [])})
            else:
                if any(r.get("repl_step_file_fallback_used") for r in obj.get("results") or []):
                    backend_artifact_reclassified += 1
                residual_event = {**base, "event": "residual_compiler_residual", "legacy_event": "path_c_residual"}
                _append_jsonl(events / "residual_compiler_residuals.jsonl", residual_event)
                _append_jsonl(events / "path_c_residuals.jsonl", residual_event)
            row_outcome["completed"] += 1
            rec = {"status": "done", "test_id": tid, "row_id": row_id, "out": str(out), "n_closed": n_closed, "n_ratified": n_ratified}
            _append_jsonl(checkpoint, rec)
            completed += 1
        if shared_repl is not None:
            shared_repl.close()

    for outcome in row_outcomes.values():
        exit_kind = learning_feedback.learning_exit_from_counts(outcome)
        outcome["learning_unit_exit"] = "probe_finished_no_tests" if exit_kind == "unknown" else exit_kind

    scoreboard = {
        "schema": "leanmill-repair-canary-scoreboard-v1",
        "packet": args.packet,
        "root": str(root),
        "tests_total": len(tests),
        "completed": completed,
        "skipped": skipped,
        "ratified_closure_count": ratified,
        "compile_candidate_count": compile_closed,
        "negative_control_fail_count": negative_expected_fail,
        "negative_control_unexpected_pass_count": negative_unexpected_pass,
        "negative_control_invalid_fail_count": negative_invalid_fail,
        "exact_gap_candidate_count": exact_gap_candidates,
        "backend_artifact_reclassified_count": backend_artifact_reclassified,
        "cache_hit_count": cache_hits,
        "warm_repl_inline": bool(args.warm_repl_inline),
        "row_outcomes": [row_outcomes[key] for key in sorted(row_outcomes)],
        "score": ratified,
        "science_rule": "Only ratified closures score; compile-only goes to governance; negative-control pass is a failure.",
    }
    if args.scoreboard:
        Path(args.scoreboard).parent.mkdir(parents=True, exist_ok=True)
        Path(args.scoreboard).write_text(json.dumps(scoreboard, indent=2, sort_keys=True) + "\n")
    return scoreboard


def _self_test() -> int:
    obj = {
        "packets": [{
            "repair_family": "x",
            "selected_rows": [{"row_id": "r", "candidate_names": ["A.b"]}],
        }]
    }
    tests = _tests_from_packets(obj, "f.json")
    assert tests[0]["row_id"] == "r"
    assert tests[0]["candidate_name"] == "A.b"
    assert tests[0]["test_kind"] == "positive"
    result_obj = {"results": [{"credit_kind": "source_action", "source_credit_eligible": True}]}
    assert _apply_test_credit_boundary(result_obj, {"source_credit_eligible": False, "credit_type": "repair_canary_probe"})
    assert result_obj["results"][0]["source_credit_eligible"] is False
    assert result_obj["results"][0]["credit_kind"] == "repair_canary_probe"
    key1 = _cache_key({"row_id": "r", "corpus": "missing", "static_filter": "missing", "backend": "repl_file"}, 90)
    key2 = _cache_key({"row_id": "r", "corpus": "missing", "static_filter": "missing", "backend": "repl_file"}, 90)
    assert key1 == key2 and len(key1) == 64
    with tempfile.TemporaryDirectory(prefix="leanmill_cache_selftest_") as td:
        root = Path(td)
        source = root / "source.json"
        out = root / "out.json"
        source.write_text(json.dumps({"n_closed": 1, "n_ratified": 0}) + "\n")
        _store_cached_result(td, "abc", source)
        cached = _load_cached_result(td, "abc", out)
        assert cached and cached["cache_hit"] and out.exists()
        bad_source = root / "bad_source.json"
        bad_out = root / "bad_out.json"
        bad_source.write_text(json.dumps({
            "worker_exception": "KeyboardInterrupt()",
            "results": [{"error_class": "worker_exception", "stdout_tail": "KeyboardInterrupt()"}],
        }) + "\n")
        _store_cached_result(td, "bad", bad_source)
        assert not (root / "bad.json").exists()
        (root / "bad.json").write_text(bad_source.read_text())
        assert _load_cached_result(td, "bad", bad_out) is None
        assert not (root / "bad.json").exists()
    print("leansearch_repair_canary_drain self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet", default=DEFAULT_PACKET)
    ap.add_argument("--root", default="/tmp/rung1/leanmill_repair_canaries")
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--static-filter")
    ap.add_argument("--backend", choices=["subprocess", "repl", "repl_step", "repl_file"], default="repl_step")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--test-wall-timeout", type=int, default=0,
                    help="Outer wall-clock cap per canary test; 0 means max(inner timeout + 45s, 90s).")
    ap.add_argument("--max-candidates", type=int, default=4)
    ap.add_argument("--max-actions", type=int, default=1)
    ap.add_argument("--govern-winners", action="store_true")
    ap.add_argument("--score-candidates", action="store_true")
    ap.add_argument("--require-positive-source-action", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--scoreboard")
    ap.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR,
                    help="Deterministic result cache for identical canary payloads; set empty with --no-cache to disable.")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--lean-slot-lock", default=DEFAULT_LEAN_SLOT_LOCK,
                    help="Process-wide heavy-Lean slot lock. Use --no-lean-slot-lock only for debugging.")
    ap.add_argument("--no-lean-slot-lock", action="store_true")
    ap.add_argument("--warm-repl-inline", action="store_true",
                    help="Run canaries inline against one shared PersistentLean process. Faster, but less isolated than the default per-test child process.")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if not args.static_filter:
        raise SystemExit("--static-filter is required unless --self-test is used")
    obj = run(args)
    print(json.dumps(obj, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
