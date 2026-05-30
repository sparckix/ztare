#!/usr/bin/env python3
"""Queue worker for LeanMill canary/spec validation."""
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
DEFAULT_FAMILY_GATE = f"{DEFAULT_DATA_DIR}/family_spec_gate.json"
DEFAULT_REGRESSION_GATE = f"{DEFAULT_DATA_DIR}/regression_gate.json"


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


def _read_jsonish(path: str) -> Any:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    text = p.read_text(errors="ignore")
    if p.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return json.loads(text)


def _normalize_body(body: Any) -> str:
    """Normalize a template body for comparison.

    Strips leading/trailing whitespace, collapses internal whitespace runs,
    drops single-line ``--`` Lean comments. Used by the matched-negative-control
    substance check to detect copy-paste duplicates between positive and
    negative templates that the anti-laundering invariant relies on being
    different.
    """
    if isinstance(body, list):
        text = "\n".join(str(x) for x in body)
    else:
        text = str(body or "")
    lines = []
    for line in text.splitlines():
        # drop full-line Lean comments; keep code with trailing comments stripped
        if line.lstrip().startswith("--"):
            continue
        # strip trailing inline -- comments (best-effort; ignores -- inside strings)
        cut = line.find("--")
        if cut >= 0:
            line = line[:cut]
        line = " ".join(line.split())
        if line:
            lines.append(line)
    return "\n".join(lines)


def _first_negative_body(row: dict[str, Any]) -> str:
    """Return the first non-empty negative-control body found on the row.

    Accepts either ``negative_control`` (singular, body or list) or the first
    entry of ``negative_controls`` (list of dicts or strings).
    """
    neg = row.get("negative_control")
    if isinstance(neg, str) and neg.strip():
        return neg
    if isinstance(neg, list):
        for item in neg:
            if isinstance(item, dict):
                body = item.get("body") or item.get("proof") or item.get("template")
                if isinstance(body, (str, list)) and (body if isinstance(body, list) else body.strip()):
                    return body  # type: ignore[return-value]
            elif isinstance(item, str) and item.strip():
                return item
    if isinstance(neg, dict):
        body = neg.get("body") or neg.get("proof") or neg.get("template")
        if isinstance(body, (str, list)):
            return body  # type: ignore[return-value]
    negs = row.get("negative_controls")
    if isinstance(negs, list):
        for item in negs:
            if isinstance(item, dict):
                body = item.get("body") or item.get("proof") or item.get("template")
                if isinstance(body, (str, list)) and (body if isinstance(body, list) else body.strip()):
                    return body  # type: ignore[return-value]
            elif isinstance(item, str) and item.strip():
                return item
    return ""


def _validate_packet_shape(path: str) -> dict[str, Any]:
    obj = _read_jsonish(path)
    rows = obj if isinstance(obj, list) else obj.get("tests") or obj.get("canaries") or obj.get("rows") or []
    if not isinstance(rows, list):
        return {"status": "fail", "failure": "packet_rows_not_list", "packet": path}
    failures = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            failures.append({"idx": idx, "failure": "row_not_object"})
            continue
        if not str(row.get("row_id") or row.get("theorem") or row.get("name") or ""):
            failures.append({"idx": idx, "failure": "missing_row_identifier"})
        pos_body_raw = row.get("positive_template") or row.get("proof") or row.get("body") or row.get("actions") or ""
        if not str(pos_body_raw).strip() and not (isinstance(pos_body_raw, list) and pos_body_raw):
            failures.append({"idx": idx, "failure": "missing_positive_surface"})
        if row.get("negative_control") is None and row.get("negative_controls") is None:
            failures.append({"idx": idx, "failure": "missing_negative_control_surface"})
        # Matched-negative-control SUBSTANCE check (anti-laundering 2026-05-23).
        # The apparatus's promise is that a matched negative control fails when
        # the positive succeeds. That promise is violated if the negative is a
        # copy-paste of the positive, an empty body, or has the wrong
        # test_kind / expected_outcome. The shape validator now enforces these
        # invariants at packet-gate time instead of trusting human review.
        neg_body_raw = _first_negative_body(row)
        pos_norm = _normalize_body(pos_body_raw)
        neg_norm = _normalize_body(neg_body_raw)
        if pos_norm and not neg_norm:
            failures.append({"idx": idx, "failure": "negative_control_body_empty"})
        elif pos_norm and neg_norm and pos_norm == neg_norm:
            failures.append({"idx": idx, "failure": "negative_equals_positive"})
        # If the row carries an explicit negative test_kind, it must say so.
        neg_kind = str(row.get("negative_test_kind") or "").lower()
        if neg_kind and neg_kind not in {"negative_control", "negative"}:
            failures.append({"idx": idx, "failure": "negative_wrong_test_kind", "test_kind": neg_kind})
        # If the row carries an explicit negative expected_outcome, it must not
        # claim a closure-class outcome — that would be a "negative" that
        # closes, which violates the anti-laundering invariant by construction.
        neg_outcome = str(row.get("negative_expected_outcome") or "").lower()
        if neg_outcome in {"closure", "ratified_closure", "governed_repair_canary_closure"}:
            failures.append({"idx": idx, "failure": "negative_claims_closure_outcome", "expected_outcome": neg_outcome})
    return {
        "schema": "leanmill-canary-packet-shape-v1",
        "packet": path,
        "row_count": len(rows),
        "failure_count": len(failures),
        "failures": failures,
        "status": "pass" if not failures else "fail",
    }


def validate(args: argparse.Namespace, payload: dict[str, Any]) -> dict[str, Any]:
    py = sys.executable
    commands = [
        _run([
            py,
            "scripts/public/control/leanmill/family_spec_gate.py",
            "--registry", args.registry,
            "--out", args.family_gate_out,
        ]),
        _run([
            py,
            "scripts/public/control/leanmill/regression_gate.py",
            "--registry", args.registry,
            "--out", args.regression_gate_out,
        ]),
    ]
    packet_result: dict[str, Any] | None = None
    packet = str(payload.get("packet") or payload.get("packet_path") or "")
    if packet:
        packet_result = _validate_packet_shape(packet)
    ok = all(cmd["returncode"] == 0 for cmd in commands)
    if packet_result is not None:
        ok = ok and packet_result.get("status") == "pass"
    return {
        "ok": ok,
        "exit_kind": "canary_spec_validated" if ok else "canary_validation_failed",
        "commands": commands,
        "packet_validation": packet_result,
    }


def work_once(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    kinds = ["canary_validation_refresh", "canary_validate"]
    if args.claim_station_residual:
        kinds.append("station:residual_curriculum")
    item = work_queue.claim(cx, worker_id=args.worker_id, kinds=kinds, lease_s=args.lease_s)
    if not item:
        return {"claimed": False}
    work_queue.update_status(cx, work_id=item["work_id"], status="running")
    work_queue.append_event(args.events, {"event_type": "canary_validator_started", "work_id": item["work_id"], "payload": item})
    result = validate(args, item.get("payload") or {})
    status = "done" if result["ok"] else "failed"
    if item["kind"] == "station:residual_curriculum" and result["ok"]:
        result["operator_required"] = "compile concrete Residual Compiler packet or launch bounded proof probe"
    work_queue.update_status(cx, work_id=item["work_id"], status=status, payload_update=result)
    work_queue.append_event(
        args.events,
        {
            "event_type": f"canary_validator_{status}",
            "work_id": item["work_id"],
            "payload": result,
            "artifact_paths": [args.family_gate_out, args.regression_gate_out],
        },
    )
    return {"claimed": True, "work_id": item["work_id"], "status": status, "ok": result["ok"]}


def _self_test() -> int:
    assert _validate_packet_shape.__name__
    print("leanmill_canary_validator_worker self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--worker-id", default="canary-validator-local")
    ap.add_argument("--lease-s", type=int, default=600)
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--family-gate-out", default=DEFAULT_FAMILY_GATE)
    ap.add_argument("--regression-gate-out", default=DEFAULT_REGRESSION_GATE)
    ap.add_argument("--claim-station-residual", action="store_true")
    ap.add_argument("--refresh-only", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    result = validate(args, {}) if args.refresh_only else work_once(args)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok", True) is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
