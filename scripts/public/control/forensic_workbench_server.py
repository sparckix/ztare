#!/usr/bin/env python3
"""Local API for the forensic workbench prototype."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import parse_qs, urlparse

import forensic_workbench_snapshot as snapshot
import forensic_workbench_review as review


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MAX_PREVIEW_BYTES = 200_000
INTAKE_EDIT_SCHEMA = "ztare-forensic-workbench-intake-edit-receipt-v1"
RECEIPT_HISTORY_SCHEMA = "ztare-forensic-workbench-receipt-history-v1"
REPORT_CONTRACT_SCHEMA = "ztare-forensic-workbench-report-contract-v1"
PREFLIGHT_SCHEMA = "ztare-forensic-workbench-preflight-v1"
INTAKE_EDIT_FIELDS = ("bounded_claim", "next_falsifier", "notes", "non_claims", "source_refs", "evidence_refs")
INTAKE_LIST_FIELDS = {"non_claims", "source_refs", "evidence_refs"}
EXTERNAL_REF_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")


def json_bytes(payload: dict[str, Any], status: int = 200) -> tuple[int, bytes]:
    return status, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def first_param(params: dict[str, list[str]], key: str, default: str) -> str:
    values = params.get(key)
    if not values:
        return default
    return values[0] or default


def repo_rel(path: Path) -> str:
    return str(path.resolve().relative_to(snapshot.REPO.resolve()))


def path_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def file_preview_payload(path: str) -> dict[str, Any]:
    if not path:
        raise ValueError("path is required")
    candidate = Path(path)
    if candidate.is_absolute():
        raise ValueError("path must be relative to the repository")
    resolved = (snapshot.REPO / candidate).resolve()
    repo = snapshot.REPO.resolve()
    if resolved != repo and repo not in resolved.parents:
        raise ValueError("path escapes the repository")
    if not resolved.exists():
        raise FileNotFoundError(f"path does not exist: {path}")
    if not resolved.is_file():
        raise ValueError(f"path is not a file: {path}")
    raw = resolved.read_bytes()
    truncated = len(raw) > MAX_PREVIEW_BYTES
    preview_bytes = raw[:MAX_PREVIEW_BYTES]
    try:
        text = preview_bytes.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        text = preview_bytes.decode("utf-8", errors="replace")
        encoding = "utf-8-replacement"
    return {
        "schema": "ztare-forensic-workbench-file-preview-v1",
        "served_from": "local_api",
        "path": snapshot.rel(resolved),
        "bytes": len(raw),
        "truncated": truncated,
        "encoding": encoding,
        "text": text,
    }


def project_intake_path(project: str, intake: str | None = None, *, allow_examples: bool = False) -> Path:
    project = snapshot.validate_project_slug(project)
    intake_path = intake or snapshot.default_intake_for_project(project)
    candidate = Path(intake_path)
    if candidate.is_absolute():
        raise ValueError("intake path must be relative to the repository")
    resolved = (snapshot.REPO / candidate).resolve()
    project_root = (snapshot.REPO / "projects" / project).resolve()
    examples_root = (snapshot.REPO / "examples" / "project_packets").resolve()
    if not path_under(resolved, project_root):
        if not allow_examples or not path_under(resolved, examples_root):
            raise ValueError("intake path must stay inside the selected project")
    if not resolved.exists():
        raise FileNotFoundError(f"intake path does not exist: {intake_path}")
    if not resolved.is_file():
        raise ValueError(f"intake path is not a file: {intake_path}")
    return resolved


def read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def unsafe_local_ref_reason(ref: str) -> str | None:
    raw = str(ref or "").strip().replace("\\", "/")
    if not raw:
        return "empty reference"
    path = PurePosixPath(raw)
    if path.is_absolute():
        return "absolute paths are not allowed"
    if any(part in {"", ".", ".."} for part in path.parts):
        return "path traversal or empty path segment is not allowed"
    return None


def inside_any_root(path: Path, roots: list[Path]) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for root in roots:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def intake_ref_status(ref: str, *, key: str, index: int, intake_path: Path) -> dict[str, Any]:
    ref = str(ref or "").strip()
    row: dict[str, Any] = {
        "key": key,
        "index": index,
        "ref": ref,
        "kind": "local",
        "status": "missing",
        "previewable": False,
        "preview_path": "",
        "reason": "",
    }
    if EXTERNAL_REF_RE.match(ref):
        row.update({"kind": "external", "status": "external", "reason": "external reference"})
        return row
    unsafe_reason = unsafe_local_ref_reason(ref)
    if unsafe_reason is not None:
        row.update({"status": "unsafe", "reason": unsafe_reason})
        return row
    raw = Path(ref)
    candidates = [intake_path.parent / raw, snapshot.REPO / raw]
    roots = [intake_path.parent.resolve(), snapshot.REPO.resolve()]
    for candidate in candidates:
        if not candidate.exists():
            continue
        if not inside_any_root(candidate, roots):
            row.update({"status": "unsafe", "reason": "resolved path escapes allowed roots"})
            return row
        row.update(
            {
                "status": "present",
                "previewable": candidate.is_file(),
                "preview_path": repo_rel(candidate) if candidate.is_file() else "",
                "reason": "file found" if candidate.is_file() else "path is not a file",
            }
        )
        return row
    row.update({"reason": "local path does not exist"})
    return row


def intake_reference_status(payload: dict[str, Any], *, intake_path: Path) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for key in ("source_refs", "evidence_refs"):
        refs = [str(item) for item in payload.get(key) or []]
        groups[key] = [
            intake_ref_status(ref, key=key, index=index, intake_path=intake_path)
            for index, ref in enumerate(refs, start=1)
        ]
    rows = [row for group in groups.values() for row in group]
    return {
        "schema": "ztare-forensic-workbench-intake-ref-status-v1",
        "source_refs": groups["source_refs"],
        "evidence_refs": groups["evidence_refs"],
        "summary": {
            "total": len(rows),
            "present": sum(1 for row in rows if row["status"] == "present"),
            "missing": sum(1 for row in rows if row["status"] == "missing"),
            "external": sum(1 for row in rows if row["status"] == "external"),
            "unsafe": sum(1 for row in rows if row["status"] == "unsafe"),
        },
    }


def intake_payload_for_project(project: str, intake: str | None = None, *, allow_examples: bool = True) -> dict[str, Any]:
    path = project_intake_path(project, intake, allow_examples=allow_examples)
    payload = read_json_object(path, "project intake")
    if payload.get("project") and payload.get("project") != project:
        raise ValueError(f"intake project mismatch: expected {project!r}, got {payload.get('project')!r}")
    editable = path_under(path, snapshot.REPO / "projects" / project)
    return {
        "schema": "ztare-forensic-workbench-intake-v1",
        "served_from": "local_api",
        "project": project,
        "path": repo_rel(path),
        "editable": editable,
        "editable_fields": {
            "bounded_claim": str(payload.get("bounded_claim") or ""),
            "next_falsifier": str(payload.get("next_falsifier") or ""),
            "notes": str(payload.get("notes") or ""),
            "non_claims": [str(item) for item in payload.get("non_claims") or []],
            "source_refs": [str(item) for item in payload.get("source_refs") or []],
            "evidence_refs": [str(item) for item in payload.get("evidence_refs") or []],
        },
        "reference_status": intake_reference_status(payload, intake_path=path),
    }


def project_index_payload() -> dict[str, Any]:
    projects = []
    for entry in snapshot.list_project_entries():
        row = dict(entry)
        try:
            intake_payload = intake_payload_for_project(
                str(row.get("project") or ""),
                str(row.get("intake") or "") or None,
                allow_examples=True,
            )
            row["intake_editable"] = bool(intake_payload.get("editable"))
            row["intake_ref_summary"] = (intake_payload.get("reference_status") or {}).get("summary") or {}
        except Exception as exc:  # noqa: BLE001 - project index should surface per-project errors.
            row["intake_editable"] = False
            row["intake_ref_summary"] = {}
            row["intake_error"] = str(exc)
        projects.append(row)
    return {
        "schema": "ztare-forensic-workbench-project-index-v1",
        "default_project": snapshot.DEFAULT_PROJECT,
        "projects": projects,
    }


def normalize_intake_patch(raw_patch: Any) -> dict[str, Any]:
    if not isinstance(raw_patch, dict):
        raise ValueError("fields must be a JSON object")
    patch: dict[str, Any] = {}
    for key in INTAKE_EDIT_FIELDS:
        if key not in raw_patch:
            continue
        value = raw_patch[key]
        if key in INTAKE_LIST_FIELDS:
            if isinstance(value, str):
                value = [line.strip() for line in value.splitlines() if line.strip()]
            if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
                raise ValueError(f"{key} must be a list of non-empty strings")
            patch[key] = [item.strip() for item in value]
            continue
        if key == "notes":
            if not isinstance(value, str):
                raise ValueError("notes must be a string")
            patch[key] = value.strip()
            continue
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a non-empty string")
        patch[key] = value.strip()
    if not patch:
        raise ValueError("no editable intake fields supplied")
    return patch


def canonical_intake_value(payload: dict[str, Any], key: str) -> Any:
    value = payload.get(key)
    if key in INTAKE_LIST_FIELDS:
        return [str(item).strip() for item in (value or []) if str(item).strip()]
    if key == "notes":
        return str(value or "").strip()
    return str(value or "").strip()


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def read_receipt_ledger(path: Path, *, kind: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    rel_path = repo_rel(path)
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            rows.append(
                {
                    "kind": "unreadable",
                    "source_kind": kind,
                    "applied_at": "",
                    "path": rel_path,
                    "line": line_number,
                    "summary": f"Unreadable receipt line: {exc}",
                }
            )
            continue
        if not isinstance(payload, dict):
            rows.append(
                {
                    "kind": "unreadable",
                    "source_kind": kind,
                    "applied_at": "",
                    "path": rel_path,
                    "line": line_number,
                    "summary": "Receipt line is not a JSON object.",
                }
            )
            continue
        rows.append(normalize_receipt_row(payload, kind=kind, path=rel_path, line=line_number))
    return rows


def normalize_receipt_row(payload: dict[str, Any], *, kind: str, path: str, line: int) -> dict[str, Any]:
    row: dict[str, Any] = {
        "kind": kind,
        "schema": str(payload.get("schema") or ""),
        "applied_at": str(payload.get("applied_at") or ""),
        "project": str(payload.get("project") or ""),
        "path": path,
        "line": line,
        "summary": "",
    }
    if kind == "review":
        row.update(
            {
                "row": str(payload.get("row") or ""),
                "row_slug": str(payload.get("row_slug") or ""),
                "decision": str(payload.get("decision") or ""),
                "note": str(payload.get("note") or ""),
                "evidence_ref_count": safe_int(payload.get("evidence_ref_count")),
                "sha256": str(payload.get("review_file_sha256") or ""),
            }
        )
        row["summary"] = f"{display_value(row['decision'])} on {row['row'] or row['row_slug'] or 'row'}"
    elif kind == "row_action":
        row.update(
            {
                "row": str(payload.get("row") or ""),
                "row_slug": str(payload.get("row_slug") or ""),
                "action": str(payload.get("action") or ""),
                "note": str(payload.get("note") or ""),
                "evidence_ref_count": safe_int(payload.get("evidence_ref_count")),
                "sha256": str(payload.get("action_file_sha256") or ""),
            }
        )
        row["summary"] = f"{display_value(row['action'])} on {row['row'] or row['row_slug'] or 'row'}"
    elif kind == "intake_edit":
        fields = [str(item) for item in payload.get("updated_fields") or []]
        row.update(
            {
                "intake_path": str(payload.get("intake_path") or ""),
                "updated_fields": fields,
                "sha256": str(payload.get("after_sha256") or ""),
            }
        )
        row["summary"] = f"Updated {', '.join(fields) if fields else 'intake'}"
    else:
        row["summary"] = kind.replace("_", " ")
    return row


def display_value(value: Any) -> str:
    return str(value or "recorded").replace("_", " ")


def safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def tail_text(value: str, *, max_chars: int = 4000) -> str:
    value = value or ""
    if len(value) <= max_chars:
        return value
    return value[-max_chars:]


def receipt_history_payload(*, project: str, limit: int = 12) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    limit = max(1, min(limit, 50))
    workspace = snapshot.REPO / "projects" / project / "workspace"
    ledgers = {
        "review": workspace / "forensic_workbench_reviews.jsonl",
        "row_action": workspace / "forensic_workbench_row_actions.jsonl",
        "intake_edit": workspace / "forensic_workbench_intake_edits.jsonl",
    }
    receipts: list[dict[str, Any]] = []
    for kind, path in ledgers.items():
        receipts.extend(read_receipt_ledger(path, kind=kind))
    receipts.sort(key=lambda row: (str(row.get("applied_at") or ""), str(row.get("kind") or ""), int(row.get("line") or 0)), reverse=True)
    return {
        "schema": RECEIPT_HISTORY_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "limit": limit,
        "receipt_count": len(receipts),
        "receipts": receipts[:limit],
        "paths": {kind: repo_rel(path) for kind, path in ledgers.items()},
    }


def apply_intake_edit(*, project: str, intake: str | None, raw_patch: Any) -> dict[str, Any]:
    path = project_intake_path(project, intake, allow_examples=False)
    before_bytes = path.read_bytes()
    payload = read_json_object(path, "project intake")
    if payload.get("project") and payload.get("project") != project:
        raise ValueError(f"intake project mismatch: expected {project!r}, got {payload.get('project')!r}")
    patch = normalize_intake_patch(raw_patch)
    changed_patch = {
        key: value
        for key, value in patch.items()
        if canonical_intake_value(payload, key) != value
    }
    if not changed_patch:
        raise ValueError("intake edit has no changed fields")
    intake_rel = repo_rel(path)
    before_values = {key: canonical_intake_value(payload, key) for key in changed_patch}
    payload.update(changed_patch)
    after_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    after_bytes = after_text.encode("utf-8")
    path.write_bytes(after_bytes)

    workspace = snapshot.REPO / "projects" / project / "workspace"
    receipt = {
        "schema": INTAKE_EDIT_SCHEMA,
        "applied_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "project": project,
        "intake_path": intake_rel,
        "updated_fields": sorted(changed_patch),
        "before_sha256": hashlib.sha256(before_bytes).hexdigest(),
        "after_sha256": hashlib.sha256(after_bytes).hexdigest(),
        "before_values": before_values,
        "after_values": {key: payload.get(key) for key in changed_patch},
    }
    ledger_path = workspace / "forensic_workbench_intake_edits.jsonl"
    latest_path = workspace / "forensic_workbench_latest_intake_edit.json"
    append_jsonl(ledger_path, receipt)
    latest_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "intake": intake_payload_for_project(project, intake_rel, allow_examples=False),
        "ledger": repo_rel(ledger_path),
        "latest": repo_rel(latest_path),
        "receipt": receipt,
    }


def snapshot_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    renderer = renderer or snapshot.DEFAULT_RENDERER
    output_path = snapshot.REPO / snapshot.DEFAULT_OUT
    (
        _html,
        rows,
        trace,
        report_contract,
        latest_review,
        latest_review_path,
        latest_action,
        latest_action_path,
        latest_intake_edit,
        latest_intake_edit_path,
    ) = snapshot.build_snapshot(
        project,
        rubric,
        intake,
        renderer,
        output_path,
    )
    payload = snapshot.snapshot_payload(
        trace,
        report_contract,
        rows,
        output_path=output_path,
        latest_review=latest_review,
        latest_review_artifact_path=latest_review_path,
        latest_action=latest_action,
        latest_action_artifact_path=latest_action_path,
        latest_intake_edit=latest_intake_edit,
        latest_intake_edit_artifact_path=latest_intake_edit_path,
    )
    payload["served_from"] = "local_api"
    return payload


def report_contract_payload_for_project(
    *,
    project: str,
    renderer: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    renderer = renderer or snapshot.DEFAULT_RENDERER
    payload, command = snapshot.collect_report_contract(project, renderer)
    binding = payload.get("synthesis_input_binding") or {}
    reasons = [str(reason) for reason in payload.get("status_reasons") or []]
    report_path = snapshot.rel(payload.get("report_support_contract"))
    return {
        "schema": REPORT_CONTRACT_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "renderer": renderer,
        "command": command,
        "ok": bool(payload.get("ok")),
        "status": payload.get("status") or "unknown",
        "status_reasons": reasons,
        "report_support_contract": report_path,
        "synthesis_input_binding": {
            "schema": binding.get("schema"),
            "ok": bool(binding.get("ok")),
            "status": binding.get("status") or "unknown",
            "reason": binding.get("reason") or "",
            "artifact_count": binding.get("artifact_count"),
            "current_digest": binding.get("current_digest"),
            "ledger_digest": binding.get("ledger_digest"),
        },
    }


def trace_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    trace, trace_command = snapshot.collect_trace(project, rubric, intake)
    kernel = trace.get("kernel_entry") or {}
    plan = trace.get("plan_preview") or {}
    surfaces = trace.get("surfaces") or {}
    readiness = surfaces.get("evidence_readiness") or {}
    source_receipt = surfaces.get("source_index_receipt") or {}
    prediction = trace.get("prediction_summary") or {}
    return {
        "schema": "ztare-forensic-workbench-trace-v1",
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "trace_command": trace_command,
        "readiness": trace.get("readiness_canonical") or trace.get("readiness") or "unknown",
        "blocking_missing": trace.get("blocking_missing") or trace.get("missing") or [],
        "next_commands": trace.get("next_commands") or [],
        "carrier_chain": [
            {
                "surface": row.get("surface"),
                "status": row.get("status"),
                "blocking": bool(row.get("blocking")),
                "next_command": row.get("next_command"),
                "count": row.get("count"),
                "receipt_count": row.get("receipt_count"),
            }
            for row in trace.get("carrier_chain", [])
            if isinstance(row, dict)
        ],
        "kernel_entry": {
            "schema": kernel.get("schema"),
            "status": kernel.get("status"),
            "can_enter_kernel": kernel.get("can_enter_kernel"),
            "readiness": kernel.get("readiness_canonical") or kernel.get("readiness"),
            "entry_surface": kernel.get("entry_surface"),
            "preflight_command": kernel.get("preflight_command"),
            "run_command": kernel.get("run_command"),
            "inspection_command": kernel.get("inspection_command"),
            "blockers": kernel.get("blockers") or [],
            "allowed_work_modes": kernel.get("allowed_work_modes") or [],
            "disallowed_work_modes": kernel.get("disallowed_work_modes") or [],
        },
        "plan_preview": {
            "schema": plan.get("schema"),
            "status": plan.get("status"),
            "available": bool(plan.get("available")),
            "recommended_first_command": plan.get("recommended_first_command"),
            "model_calls_before_confirmation": plan.get("model_calls_before_confirmation"),
            "largest_quality_drop_risk": plan.get("largest_quality_drop_risk"),
            "risk_reason": plan.get("risk_reason"),
            "worker_count": plan.get("worker_count"),
            "dependency_order": [
                {
                    "id": row.get("id"),
                    "status": row.get("status"),
                    "model_calls": bool(row.get("model_calls")),
                    "command": row.get("command"),
                    "description": row.get("description"),
                }
                for row in plan.get("dependency_order", [])
                if isinstance(row, dict)
            ],
        },
        "loop_admission": trace.get("loop_admission") or {},
        "recent_loop": trace.get("recent_loop") or {},
        "surfaces": {
            "source_preflight_status": surfaces.get("source_preflight_status"),
            "raw_file_count": surfaces.get("raw_file_count"),
            "source_index_status": readiness.get("source_index_status"),
            "evidence_status": readiness.get("status"),
            "output_binding_status": readiness.get("output_binding_status"),
            "replay_status": readiness.get("replay_status"),
            "source_index_receipt_path": source_receipt.get("path"),
            "compile_provenance_path": snapshot.rel(surfaces.get("compile_provenance_path")),
        },
        "graph_carriers": [
            {
                "graph_id": row.get("graph_id"),
                "graph_kind": row.get("graph_kind"),
                "node_count": row.get("node_count"),
                "edge_count": row.get("edge_count"),
                "source_artifacts": [snapshot.rel(path) for path in (row.get("source_artifacts") or [])],
                "validation_ok": (row.get("validation") or {}).get("ok"),
            }
            for row in trace.get("graph_carriers", [])
            if isinstance(row, dict)
        ],
        "prediction_summary": {
            "available": bool(prediction.get("available")),
            "status": prediction.get("status"),
            "row_count": prediction.get("row_count"),
            "scoreable_count": prediction.get("scoreable_count"),
            "measurement_policy": prediction.get("measurement_policy"),
        },
    }


def health_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    kernel_command = [
        "make",
        "autoresearch-kernel-health",
        f"PROJECT={project}",
        f"RUBRIC={rubric}",
        f"INTAKE={intake}",
        "JSON=1",
    ]
    kernel_proc = snapshot.run(kernel_command)
    if kernel_proc.returncode != 0:
        raise SystemExit(
            "kernel health command failed\n"
            f"command: {snapshot.shell_join(kernel_command)}\n"
            f"STDOUT:\n{kernel_proc.stdout}\nSTDERR:\n{kernel_proc.stderr}"
        )
    kernel_payload = snapshot.extract_last_json_object(kernel_proc.stdout)

    action_command = [
        snapshot.PYTHON,
        "scripts/public/control/action_intelligence.py",
        "health",
        "--json",
    ]
    action_proc = snapshot.run(action_command)
    if action_proc.returncode != 0:
        raise SystemExit(
            "action-intelligence health command failed\n"
            f"command: {snapshot.shell_join(action_command)}\n"
            f"STDOUT:\n{action_proc.stdout}\nSTDERR:\n{action_proc.stderr}"
        )
    action_payload = snapshot.extract_last_json_object(action_proc.stdout)

    attention_components = [
        {
            "component": row.get("component"),
            "status": row.get("status"),
            "action": row.get("action"),
            "next_command": row.get("next_command"),
        }
        for row in kernel_payload.get("components", [])
        if row.get("status") != "ok"
    ]
    action_issues = [
        {
            "issue_type": issue.get("issue_type"),
            "severity": issue.get("severity"),
            "scope": issue.get("scope"),
            "recommended_action": issue.get("recommended_action"),
        }
        for issue in action_payload.get("issues", [])
    ]
    return {
        "schema": "ztare-forensic-workbench-health-v1",
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "kernel": {
            "summary": kernel_payload.get("summary") or {},
            "attention_components": attention_components,
            "component_count": len(kernel_payload.get("components", [])),
        },
        "action_intelligence": {
            "counts": action_payload.get("counts") or {},
            "issues": action_issues,
            "source_paths": action_payload.get("source_paths") or {},
        },
    }


def preflight_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    project_intake_path(project, intake, allow_examples=True)
    command = [
        snapshot.PYTHON,
        "-m",
        "src.ztare.cli",
        "autoresearch",
        "run",
        "--project",
        project,
        "--rubric",
        rubric,
        "--intake",
        intake,
        "--preflight-only",
    ]
    display_command = (
        "ztare autoresearch run "
        f"--project {project} --rubric {rubric} --intake {intake} --preflight-only"
    )
    proc = snapshot.run(command, timeout=120)
    accepted = proc.returncode == 0 and "autoresearch preflight-only" in proc.stdout
    payload: dict[str, Any] = {
        "schema": PREFLIGHT_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "command": display_command,
        "returncode": proc.returncode,
        "accepted": accepted,
        "stdout_tail": tail_text(proc.stdout),
        "stderr_tail": tail_text(proc.stderr),
        "trace": None,
        "snapshot": None,
    }
    try:
        payload["trace"] = trace_payload_for_project(project=project, rubric=rubric, intake=intake)
    except SystemExit as exc:
        payload["trace_error"] = str(exc)
    except Exception as exc:  # noqa: BLE001 - preflight result should still be inspectable.
        payload["trace_error"] = str(exc)
    try:
        payload["snapshot"] = snapshot_payload_for_project(
            project=project,
            rubric=rubric,
            intake=intake,
            renderer=renderer,
        )
    except SystemExit as exc:
        payload["snapshot_error"] = str(exc)
    except Exception as exc:  # noqa: BLE001 - preflight result should still be inspectable.
        payload["snapshot_error"] = str(exc)
    return payload


class WorkbenchHandler(BaseHTTPRequestHandler):
    server_version = "ZTAREForensicWorkbench/0.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        code, body = json_bytes(payload, status)
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:5174")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            raise ValueError("request body is empty")
        body = self.rfile.read(length)
        payload = json.loads(body.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/projects":
                self.send_json(project_index_payload())
                return
            if parsed.path == "/api/snapshot":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                rubric = first_param(params, "rubric", project)
                intake = first_param(params, "intake", snapshot.default_intake_for_project(project))
                renderer = first_param(params, "renderer", snapshot.DEFAULT_RENDERER)
                payload = snapshot_payload_for_project(
                    project=project,
                    rubric=rubric,
                    intake=intake,
                    renderer=renderer,
                )
                self.send_json(payload)
                return
            if parsed.path == "/api/health":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                rubric = first_param(params, "rubric", project)
                intake = first_param(params, "intake", snapshot.default_intake_for_project(project))
                payload = health_payload_for_project(project=project, rubric=rubric, intake=intake)
                self.send_json(payload)
                return
            if parsed.path == "/api/trace":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                rubric = first_param(params, "rubric", project)
                intake = first_param(params, "intake", snapshot.default_intake_for_project(project))
                payload = trace_payload_for_project(project=project, rubric=rubric, intake=intake)
                self.send_json(payload)
                return
            if parsed.path == "/api/report-contract":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                renderer = first_param(params, "renderer", snapshot.DEFAULT_RENDERER)
                payload = report_contract_payload_for_project(project=project, renderer=renderer)
                self.send_json(payload)
                return
            if parsed.path == "/api/file":
                params = parse_qs(parsed.query)
                path = first_param(params, "path", "")
                self.send_json(file_preview_payload(path))
                return
            if parsed.path == "/api/intake":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                intake = first_param(params, "intake", snapshot.default_intake_for_project(project))
                self.send_json(intake_payload_for_project(project, intake, allow_examples=True))
                return
            if parsed.path == "/api/receipts":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                limit = int(first_param(params, "limit", "12"))
                self.send_json(receipt_history_payload(project=project, limit=limit))
                return
            self.send_json({"ok": False, "error": "unknown endpoint"}, status=404)
        except SystemExit as exc:
            self.send_json({"ok": False, "error": str(exc)}, status=400)
        except Exception as exc:  # noqa: BLE001 - API should return inspectable JSON errors.
            self.send_json({"ok": False, "error": str(exc)}, status=400)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/review":
                request = self.read_json_body()
                project = str(request.get("project") or "")
                rubric = str(request.get("rubric") or "") or None
                intake = str(request.get("intake") or "") or None
                row = str(request.get("row_slug") or "")
                review_file = request.get("review_file")
                if not isinstance(review_file, dict):
                    raise ValueError("review_file must be a JSON object")
                review_result = review.apply_review_payload(
                    review_file,
                    project=project,
                    row=row,
                    review_file_path=f"local-api:{project}/{row}",
                )
                response = {
                    "ok": True,
                    "review": review_result,
                    "snapshot": None,
                }
                try:
                    response["snapshot"] = snapshot_payload_for_project(project=project, rubric=rubric, intake=intake)
                except SystemExit as exc:
                    response["snapshot_error"] = str(exc)
                except Exception as exc:  # noqa: BLE001 - receipt write already succeeded.
                    response["snapshot_error"] = str(exc)
                self.send_json(response)
                return
            if parsed.path == "/api/intake":
                request = self.read_json_body()
                project = str(request.get("project") or "")
                rubric = str(request.get("rubric") or "") or None
                intake = str(request.get("intake") or "") or None
                edit_result = apply_intake_edit(
                    project=project,
                    intake=intake,
                    raw_patch=request.get("fields"),
                )
                response = {
                    "ok": True,
                    "edit": edit_result,
                    "intake": edit_result.get("intake"),
                    "snapshot": None,
                }
                try:
                    response["snapshot"] = snapshot_payload_for_project(project=project, rubric=rubric, intake=intake)
                except SystemExit as exc:
                    response["snapshot_error"] = str(exc)
                except Exception as exc:  # noqa: BLE001 - intake write already succeeded.
                    response["snapshot_error"] = str(exc)
                self.send_json(response)
                return
            if parsed.path == "/api/row-action":
                request = self.read_json_body()
                project = str(request.get("project") or "")
                rubric = str(request.get("rubric") or "") or None
                intake = str(request.get("intake") or "") or None
                row = str(request.get("row_slug") or "")
                action_file = request.get("action_file")
                if not isinstance(action_file, dict):
                    raise ValueError("action_file must be a JSON object")
                action_result = review.apply_action_payload(
                    action_file,
                    project=project,
                    row=row,
                    action_file_path=f"local-api:{project}/{row}",
                )
                response = {
                    "ok": True,
                    "action": action_result,
                    "snapshot": None,
                }
                try:
                    response["snapshot"] = snapshot_payload_for_project(project=project, rubric=rubric, intake=intake)
                except SystemExit as exc:
                    response["snapshot_error"] = str(exc)
                except Exception as exc:  # noqa: BLE001 - receipt write already succeeded.
                    response["snapshot_error"] = str(exc)
                self.send_json(response)
                return
            if parsed.path == "/api/preflight":
                request = self.read_json_body()
                project = str(request.get("project") or "")
                rubric = str(request.get("rubric") or "") or None
                intake = str(request.get("intake") or "") or None
                renderer = str(request.get("renderer") or "") or None
                response = preflight_payload_for_project(
                    project=project,
                    rubric=rubric,
                    intake=intake,
                    renderer=renderer,
                )
                self.send_json(response, status=200 if response.get("returncode") == 0 else 400)
                return
            self.send_json({"ok": False, "error": "unknown endpoint"}, status=404)
        except SystemExit as exc:
            self.send_json({"ok": False, "error": str(exc)}, status=400)
        except Exception as exc:  # noqa: BLE001 - API should return inspectable JSON errors.
            self.send_json({"ok": False, "error": str(exc)}, status=400)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), WorkbenchHandler)
    print(f"forensic workbench API listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
