#!/usr/bin/env python3
"""Queue worker for LeanMill governance receipts."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_paths import REPAIR_FAMILY_REGISTRY as DEFAULT_REGISTRY


DEFAULT_DATA_DIR = "analytics/public/leanmill/dashboard_data"
DEFAULT_REGRESSION_GATE = f"{DEFAULT_DATA_DIR}/governance_regression_gate.json"
DEFAULT_LIFECYCLE = f"{DEFAULT_DATA_DIR}/governance_residual_lifecycle.json"


def _display_cmd(cmd: list[str]) -> list[str]:
    if cmd and Path(cmd[0]).resolve() == Path(sys.executable).resolve():
        return ["<python>", *cmd[1:]]
    return cmd


def _run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    return {
        "cmd": _display_cmd(cmd),
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def _validate_candidate(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"status": "fail", "failure": "candidate_path_missing", "candidate": path}
    obj = json.loads(p.read_text(errors="ignore"))
    failures = []
    for key in ("candidate_kind", "target_kind", "artifact_paths", "expected_outcome"):
        if obj.get(key) in (None, "", []):
            failures.append({"failure": f"missing_{key}"})
    if str(obj.get("candidate_kind") or "") not in {"closure", "exact_gap", "falsifier"}:
        failures.append({"failure": "invalid_candidate_kind", "candidate_kind": obj.get("candidate_kind")})
    candidate_kind = str(obj.get("candidate_kind") or "")
    if candidate_kind in {"exact_gap", "falsifier"}:
        has_statement = bool(str(obj.get("formal_statement") or obj.get("gap_statement") or "").strip())
        has_blocked_edge = bool(str(obj.get("blocked_edge") or "").strip())
        has_evidence = isinstance(obj.get("evidence"), dict) and bool(obj.get("evidence"))
        if not (has_statement or has_blocked_edge):
            failures.append({
                "failure": "missing_gap_or_falsifier_statement",
                "required": "formal_statement, gap_statement, or blocked_edge",
            })
        if not has_evidence:
            failures.append({"failure": "missing_gap_or_falsifier_evidence"})
    artifact_paths = obj.get("artifact_paths") if isinstance(obj.get("artifact_paths"), list) else []
    for artifact in artifact_paths:
        artifact_path = Path(str(artifact))
        if not artifact_path.exists() or not artifact_path.is_file():
            failures.append({"failure": "artifact_path_missing", "artifact_path": str(artifact)})
            continue
        text = artifact_path.read_text(errors="ignore")[:200_000]
        lowered = text.lower()
        if "sorry" in lowered or "axiom " in lowered or "unsafe" in lowered:
            failures.append({"failure": "artifact_contains_forbidden_proof_token", "artifact_path": str(artifact)})
    return {
        "schema": "leanmill-governance-candidate-shape-v1",
        "candidate": path,
        "failure_count": len(failures),
        "failures": failures,
        "status": "pass" if not failures else "fail",
    }


def govern(args: argparse.Namespace, payload: dict[str, Any]) -> dict[str, Any]:
    py = sys.executable
    commands = [
        _run([
            py,
            "scripts/public/control/leanmill/regression_gate.py",
            "--registry", args.registry,
            "--out", args.regression_gate_out,
        ]),
        _run([
            py,
            "scripts/public/control/leanmill/residual_lifecycle.py",
            "--out", args.lifecycle_out,
        ]),
    ]
    candidate_path = str(payload.get("candidate") or payload.get("candidate_path") or "")
    candidate_result = _validate_candidate(candidate_path) if candidate_path else None
    ok = all(cmd["returncode"] == 0 for cmd in commands)
    if candidate_result is not None:
        ok = ok and candidate_result.get("status") == "pass"
    exit_kind = "governance_shape_checked" if candidate_result else "governance_control_refresh"
    if not ok:
        exit_kind = "governance_rejected"
    return {
        "ok": ok,
        "exit_kind": exit_kind,
        "commands": commands,
        "candidate_validation": candidate_result,
        "truth_boundary": "shape/control only; Lean replay remains the ratification authority",
    }


def work_once(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    kinds = ["governance_refresh", "govern_closure_candidate", "govern_exact_gap", "govern_falsifier"]
    if args.claim_station_governance:
        kinds.append("station:governance_gate")
    item = work_queue.claim(cx, worker_id=args.worker_id, kinds=kinds, lease_s=args.lease_s)
    if not item:
        return {"claimed": False}
    work_queue.update_status(cx, work_id=item["work_id"], status="running")
    work_queue.append_event(args.events, {"event_type": "governance_worker_started", "work_id": item["work_id"], "payload": item})
    result = govern(args, item.get("payload") or {})
    status = "done" if result["ok"] else "failed"
    if item["kind"] == "station:governance_gate" and result["ok"]:
        result["operator_required"] = "submit concrete closure/exact-gap/falsifier candidate for full ratification"
    work_queue.update_status(cx, work_id=item["work_id"], status=status, payload_update=result)
    work_queue.append_event(args.events, {
        "event_type": f"governance_worker_{status}",
        "work_id": item["work_id"],
        "payload": result,
        "artifact_paths": [args.regression_gate_out, args.lifecycle_out],
    })
    return {"claimed": True, "work_id": item["work_id"], "status": status, "ok": result["ok"]}


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_governance_worker_") as td:
        root = Path(td)
        bad_artifact = root / "bad.lean"
        bad_artifact.write_text("theorem bad : True := by\n  sorry\n")
        candidate = root / "candidate.json"
        candidate.write_text(json.dumps({
            "candidate_kind": "closure",
            "target_kind": "repair_canary",
            "expected_outcome": "closure",
            "artifact_paths": [str(bad_artifact)],
        }) + "\n")
        result = _validate_candidate(str(candidate))
        assert result["status"] == "fail"
        assert any(f["failure"] == "artifact_contains_forbidden_proof_token" for f in result["failures"])
        vague_gap = root / "vague_gap.json"
        ok_artifact = root / "gap_artifact.json"
        ok_artifact.write_text(json.dumps({"schema": "x", "decision": "exact_gap_candidate"}) + "\n")
        vague_gap.write_text(json.dumps({
            "candidate_kind": "exact_gap",
            "target_kind": "post_probe_next_artifact",
            "expected_outcome": "exact_gap",
            "artifact_paths": [str(ok_artifact)],
        }) + "\n")
        vague_result = _validate_candidate(str(vague_gap))
        assert vague_result["status"] == "fail"
        assert any(f["failure"] == "missing_gap_or_falsifier_statement" for f in vague_result["failures"])
        shaped_gap = root / "shaped_gap.json"
        shaped_gap.write_text(json.dumps({
            "candidate_kind": "exact_gap",
            "target_kind": "post_probe_next_artifact",
            "expected_outcome": "exact_gap",
            "artifact_paths": [str(ok_artifact)],
            "blocked_edge": "requires unavailable finite-sum-to-tsum bridge",
            "evidence": {"scoreboard": "scoreboard.json"},
        }) + "\n")
        assert _validate_candidate(str(shaped_gap))["status"] == "pass"
    print("leanmill_governance_worker self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--worker-id", default="governance-worker-local")
    ap.add_argument("--lease-s", type=int, default=600)
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--regression-gate-out", default=DEFAULT_REGRESSION_GATE)
    ap.add_argument("--lifecycle-out", default=DEFAULT_LIFECYCLE)
    ap.add_argument("--claim-station-governance", action="store_true")
    ap.add_argument("--refresh-only", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    result = govern(args, {}) if args.refresh_only else work_once(args)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok", True) is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
