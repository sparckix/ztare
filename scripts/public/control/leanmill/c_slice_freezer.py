#!/usr/bin/env python3
"""Freeze a LeanMill C-discriminating candidate slice before Path-C execution."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from leanmill_paths import DATA_DIR

DEFAULT_SELECTION = f"{DATA_DIR}/evaluation_harness_c_discriminating_slice.json"
DEFAULT_ROW_CONTEXT = f"{DATA_DIR}/evaluation_harness_c_discriminating_row_context.json"
DEFAULT_OUT = f"{DATA_DIR}/evaluation_harness_c_discriminating_slice_frozen.json"
STRICT_NO_SIGNAL_EXITS = {"tested_no_positive_signal"}


def _read_json(path: str | Path) -> Any:
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"missing required file: {path}")
    return json.loads(p.read_text(errors="ignore"))


def _sha_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha_obj(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def freeze(args: argparse.Namespace) -> dict[str, Any]:
    selection = _read_json(args.selection)
    row_context = _read_json(args.row_context)
    selected = selection.get("selected_rows") or []
    row_ids = [str(row.get("row_id") or "") for row in selected if str(row.get("row_id") or "")]
    if len(row_ids) < int(args.min_rows) and not args.allow_under_min:
        raise SystemExit(f"refusing to freeze under-min slice: {len(row_ids)} < {args.min_rows}")
    if selection.get("status") != "ready" and not args.allow_not_ready:
        raise SystemExit(f"refusing to freeze non-ready selection: {selection.get('status')}")
    missing_evidence = []
    for row in selected:
        if not row.get("matched_families"):
            missing_evidence.append({"row_id": row.get("row_id"), "reason": "missing_matched_families"})
        static = row.get("static_tools_result") or {}
        if static.get("status") != "failed_or_no_positive_signal":
            missing_evidence.append({"row_id": row.get("row_id"), "reason": "static_not_failed", "static": static})
        present_arms = set(static.get("present_arms") or [])
        required_static_arms = {"public_tool_static", "governed_public_tool_static"}
        if present_arms != required_static_arms:
            missing_evidence.append({
                "row_id": row.get("row_id"),
                "reason": "static_sweep_incomplete",
                "present_arms": sorted(present_arms),
                "required_arms": sorted(required_static_arms),
            })
        static_exits = [static.get("public_exit"), static.get("governed_exit")]
        static_exits = [str(x) for x in static_exits if x]
        if not static_exits or any(exit_kind not in STRICT_NO_SIGNAL_EXITS for exit_kind in static_exits):
            missing_evidence.append({
                "row_id": row.get("row_id"),
                "reason": "static_not_strict_no_signal",
                "public_exit": static.get("public_exit"),
                "governed_exit": static.get("governed_exit"),
            })
        if row.get("c_discriminating_evidence_status") != "c_discriminating_probe_verified":
            missing_evidence.append({"row_id": row.get("row_id"), "reason": "c_discriminating_probe_not_verified", "status": row.get("c_discriminating_evidence_status")})
        if row.get("static_sweep_required_before_c_credit"):
            missing_evidence.append({"row_id": row.get("row_id"), "reason": "static_sweep_required_before_c_credit"})
        if row.get("family_spec_probe_required_before_c_credit"):
            missing_evidence.append({"row_id": row.get("row_id"), "reason": "family_spec_probe_required_before_c_credit"})
        if not row.get("target_resolution_ok"):
            missing_evidence.append({"row_id": row.get("row_id"), "reason": "target_not_executable"})
    if missing_evidence and not args.allow_not_ready:
        raise SystemExit("refusing to freeze rows with missing evidence: " + json.dumps(missing_evidence[:5], sort_keys=True))
    payload = {
        "schema": "leanmill-c-discriminating-slice-frozen-v1",
        "status": "frozen",
        "freeze_label": args.label,
        "selection_path": args.selection,
        "selection_sha256": _sha_file(args.selection),
        "row_context_path": args.row_context,
        "row_context_sha256": _sha_file(args.row_context),
        "row_ids": row_ids,
        "row_count": len(row_ids),
        "selection_status": selection.get("status"),
        "source_checkpoint": selection.get("checkpoint"),
        "source_run_id": selection.get("run_id"),
        "freeze_rule": "Rows selected from static-fail + family-template + matched-negative evidence before any credited Path-C run; changing rows requires a new freeze artifact.",
        "primary_metric": "useful_outcome_at_budget: ratified_closure | exact_gap | valid_falsifier | tested_retirement",
        "non_laundering_assertions": {
            "path_c_not_run_for_selection": True,
            "static_failure_required": True,
            "matched_negative_control_required": True,
            "target_executable_required": True,
            "row_context_content_hashed": True,
        },
        "rows": selected,
        "row_context_schema": row_context.get("schema") if isinstance(row_context, dict) else None,
    }
    payload["freeze_sha256"] = _sha_obj(payload)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_c_freezer_") as td:
        root = Path(td)
        sel = root / "sel.json"
        rows = root / "rows.json"
        sel.write_text(json.dumps({
            "status": "ready",
            "checkpoint": "ck",
            "run_id": "run",
            "selected_rows": [{
                "row_id": "r1",
                "matched_families": ["fam"],
                "target_resolution_ok": True,
                "static_tools_result": {"status": "failed_or_no_positive_signal", "public_exit": "tested_no_positive_signal", "governed_exit": "tested_no_positive_signal", "present_arms": ["public_tool_static", "governed_public_tool_static"]},
                "c_discriminating_evidence_status": "c_discriminating_probe_verified",
                "static_sweep_required_before_c_credit": False,
                "family_spec_probe_required_before_c_credit": False,
            }],
        }) + "\n")
        rows.write_text(json.dumps({"schema": "rows", "rows": [{"row_id": "r1"}]}) + "\n")
        payload = freeze(argparse.Namespace(selection=str(sel), row_context=str(rows), out=None, label="test", min_rows=1, allow_under_min=False, allow_not_ready=False))
        assert payload["row_count"] == 1, payload
        assert payload["freeze_sha256"], payload
        bad_sel = root / "bad_sel.json"
        bad_sel.write_text(json.dumps({
            "status": "ready",
            "checkpoint": "ck",
            "run_id": "run",
            "selected_rows": [{
                "row_id": "r2",
                "matched_families": ["fam"],
                "target_resolution_ok": True,
                "static_tools_result": {"status": "unknown_not_run", "public_exit": None, "governed_exit": None, "present_arms": []},
                "c_discriminating_evidence_status": "unverified_static_sweep_required",
                "static_sweep_required_before_c_credit": True,
            }],
        }) + "\n")
        try:
            freeze(argparse.Namespace(selection=str(bad_sel), row_context=str(rows), out=None, label="bad", min_rows=1, allow_under_min=False, allow_not_ready=False))
            raise AssertionError("expected unverified C-supply freeze to fail")
        except SystemExit as exc:
            assert "missing evidence" in str(exc) or "static_not_failed" in str(exc), exc

        infra_sel = root / "infra_sel.json"
        infra_sel.write_text(json.dumps({
            "status": "ready",
            "checkpoint": "ck",
            "run_id": "run",
            "selected_rows": [{
                "row_id": "r3",
                "matched_families": ["fam"],
                "target_resolution_ok": True,
                "static_tools_result": {"status": "failed_or_no_positive_signal", "public_exit": "harness_candidate_build_failure", "present_arms": ["public_tool_static"]},
                "c_discriminating_evidence_status": "c_discriminating_supply_verified",
                "static_sweep_required_before_c_credit": False,
            }],
        }) + "\n")
        try:
            freeze(argparse.Namespace(selection=str(infra_sel), row_context=str(rows), out=None, label="infra", min_rows=1, allow_under_min=False, allow_not_ready=False))
            raise AssertionError("expected candidate build failure C-supply freeze to fail")
        except SystemExit as exc:
            assert "static_not_strict_no_signal" in str(exc), exc
    print("leanmill_c_slice_freezer self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selection", default=DEFAULT_SELECTION)
    ap.add_argument("--row-context", default=DEFAULT_ROW_CONTEXT)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--label", default="c_discriminating_slice")
    ap.add_argument("--min-rows", type=int, default=20)
    ap.add_argument("--allow-under-min", action="store_true")
    ap.add_argument("--allow-not-ready", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = freeze(args)
    print(json.dumps({
        "out": args.out,
        "status": payload["status"],
        "row_count": payload["row_count"],
        "freeze_sha256": payload["freeze_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
