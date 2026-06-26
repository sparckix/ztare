#!/usr/bin/env python3
"""Local API for the D4 forensic workbench."""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import shlex
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import parse_qs, urlparse

import forensic_workbench_snapshot as snapshot
import forensic_workbench_review as review


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_DEV_ORIGIN = "http://127.0.0.1:5174"
MAX_PREVIEW_BYTES = 200_000
WORKBENCH_ROOT = snapshot.REPO / "forensic-workbench"
WORKBENCH_DIST = WORKBENCH_ROOT / "dist"
WORKBENCH_PUBLIC = WORKBENCH_ROOT / "public"
FILE_PREVIEW_ALLOWED_ROOTS = (
    "analytics/public",
    "docs",
    "examples",
    "forensic-workbench",
    "projects",
    "rubrics",
)
FILE_PREVIEW_ALLOWED_FILES = {
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "README.md",
    "RELEASE_CHECKLIST.md",
    "SECURITY.md",
    "priority_roadmap.md",
}
FILE_PREVIEW_BLOCKED_PARTS = {".git", ".agents", ".codex", "internal", "research_areas"}
INTAKE_EDIT_SCHEMA = "ztare-forensic-workbench-intake-edit-receipt-v1"
RECEIPT_HISTORY_SCHEMA = "ztare-forensic-workbench-receipt-history-v1"
REPORT_CONTRACT_SCHEMA = "ztare-forensic-workbench-report-contract-v1"
PREFLIGHT_SCHEMA = "ztare-forensic-workbench-preflight-v1"
BOUNDED_RUN_SCHEMA = "ztare-forensic-workbench-bounded-run-v1"
RUN_HISTORY_SCHEMA = "ztare-forensic-workbench-run-history-v1"
CLAIM_SUPPORT_SCHEMA = "ztare-forensic-workbench-claim-support-v1"
SOURCE_ACTION_SCHEMA = "ztare-forensic-workbench-source-action-v1"
PROJECT_CREATE_SCHEMA = "ztare-forensic-workbench-project-create-v1"
SOURCE_IMPORT_SCHEMA = "ztare-forensic-workbench-source-import-v1"
SOURCE_LIST_SCHEMA = "ztare-forensic-workbench-source-list-v1"
SOURCE_FILE_SCHEMA = "ztare-forensic-workbench-source-file-v1"
SOURCE_EDIT_SCHEMA = "ztare-forensic-workbench-source-edit-v1"
SOURCE_ACTION_RECEIPT_SCHEMA = "ztare-forensic-workbench-source-action-receipt-v1"
CASE_FILE_SCHEMA = "ztare-forensic-workbench-case-file-v1"
CASE_FILE_WRITE_SCHEMA = "ztare-forensic-workbench-case-file-write-receipt-v1"
SERVER_STATUS_SCHEMA = "ztare-forensic-workbench-server-status-v1"
WORKFLOW_SCHEMA = "ztare-forensic-workbench-workflow-v1"
ACTION_INTELLIGENCE_STATE_DIR = Path("analytics/public/action_intelligence/state")
SERVER_PYTHON = str(snapshot.REPO / "venv" / "bin" / "python") if (snapshot.REPO / "venv" / "bin" / "python").exists() else snapshot.PYTHON
INTAKE_EDIT_FIELDS = ("bounded_claim", "next_falsifier", "notes", "non_claims", "source_refs", "evidence_refs")
INTAKE_LIST_FIELDS = {"non_claims", "source_refs", "evidence_refs"}
EXTERNAL_REF_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
SOURCE_IMPORT_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}\.(md|txt)$")
SOURCE_IMPORT_TYPES = {"source_evidence", "seed_hypothesis", "research_question", "collection_todo", "untyped"}
LOCAL_DEV_ORIGIN_RE = re.compile(r"^http://(127\.0\.0\.1|localhost):51(7[3-9]|8[0-9])$")
WRITE_POST_ENDPOINTS = {
    "/api/review",
    "/api/intake",
    "/api/item-action",
    "/api/next-step",
    "/api/row-action",
    "/api/preflight",
    "/api/run",
    "/api/source-action",
    "/api/project-create",
    "/api/source-import",
    "/api/source-edit",
    "/api/project-file",
    "/api/case-file",
}
SOURCE_ACTIONS = {
    "source_check": {
        "label": "Check source files",
        "args": ["project", "source-check", "--project", "{project}", "--json"],
        "display": "ztare project source-check --project {project} --json",
        "timeout": 90,
        "writes": False,
        "write_path_templates": [],
    },
    "source_index": {
        "label": "Refresh file index",
        "args": ["project", "source-index", "--project", "{project}", "--index-only", "--json"],
        "display": "ztare project source-index --project {project} --index-only --json",
        "timeout": 120,
        "writes": True,
        "write_path_templates": [
            "projects/{project}/workspace/source_index.json",
            "projects/{project}/workspace/workspace_meta.json",
            "projects/{project}/workspace/source_index_receipt.json",
            "projects/{project}/workspace/forensic_workbench_source_actions.jsonl",
            "projects/{project}/workspace/forensic_workbench_latest_source_action.json",
        ],
    },
    "evidence_replay": {
        "label": "Check evidence files",
        "args": ["project", "evidence-replay", "--project", "{project}", "--json"],
        "display": "ztare project evidence-replay --project {project} --json",
        "timeout": 90,
        "writes": False,
        "write_path_templates": [],
    },
    "evidence_bind": {
        "label": "Connect evidence files",
        "args": ["project", "evidence-bind", "--project", "{project}", "--json"],
        "display": "ztare project evidence-bind --project {project} --json",
        "timeout": 90,
        "writes": True,
        "write_path_templates": [
            "projects/{project}/workspace/evidence_output_binding_receipt.json",
            "projects/{project}/workspace/forensic_workbench_source_actions.jsonl",
            "projects/{project}/workspace/forensic_workbench_latest_source_action.json",
        ],
    },
}


def json_bytes(payload: dict[str, Any], status: int = 200) -> tuple[int, bytes]:
    return status, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def first_param(params: dict[str, list[str]], key: str, default: str) -> str:
    values = params.get(key)
    if not values:
        return default
    return values[0] or default


def repo_rel(path: Path) -> str:
    return str(path.resolve().relative_to(snapshot.REPO.resolve()))


def display_path(value: Any) -> str:
    raw = str(value or "")
    if not raw:
        return ""
    path = Path(raw)
    if path.is_absolute():
        try:
            return repo_rel(path)
        except ValueError:
            return raw
    return raw


def display_text(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    repo = str(snapshot.REPO.resolve())
    return text.replace(repo + "/", "").replace(repo, ".")


def project_display_label(project: Any) -> str:
    text = str(project or "").strip()
    if not text:
        return "Local project"
    text = re.sub(r"^_+", "", text)
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return str(project)
    phrase_replacements = {
        "load bearing": "key",
    }
    for raw, rendered in phrase_replacements.items():
        text = re.sub(rf"\b{raw}\b", rendered, text, flags=re.IGNORECASE)
    replacements = {
        "operator": "system",
        "packet": "intake",
        "case": "project",
    }
    for raw, rendered in replacements.items():
        text = re.sub(rf"\b{raw}\b", rendered, text, flags=re.IGNORECASE)
    return text[:1].upper() + text[1:]


def project_status_label(status: Any, *, intake_source: Any = "") -> str:
    raw = str(status or "")
    if raw == "case_ready":
        return "intake ready"
    if raw == "needs_intake":
        return "needs intake"
    if str(intake_source or "") == "public_example_intake":
        return "example intake"
    if str(intake_source or "") == "project_local_intake":
        return "project intake"
    return display_value(raw or "project")


def project_status_value(status: Any) -> str:
    raw = str(status or "")
    if raw == "case_ready":
        return "intake_ready"
    return raw or "project"


def background_project_folder(project: Any) -> bool:
    text = str(project or "")
    return (
        text.startswith("_")
        or text.startswith("backtest_")
        or text.startswith("recursive_bayesian_")
        or text.startswith("simulation_god_")
        or text.startswith("tsmc_fragility_")
    )


def display_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): display_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [display_data(item) for item in value]
    if isinstance(value, str):
        return display_text(value)
    return value


def safe_child_path(root: Path, request_path: str) -> Path:
    normalized = request_path.strip("/")
    pure = PurePosixPath(normalized)
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("static path is not allowed")
    resolved = (root / Path(*pure.parts)).resolve()
    if not path_under(resolved, root):
        raise ValueError("static path escapes workbench root")
    return resolved


def static_workbench_path(request_path: str) -> Path | None:
    if request_path in {"", "/", "/index.html"}:
        return WORKBENCH_DIST / "index.html"
    if request_path == "/workbench_snapshot.json":
        return WORKBENCH_PUBLIC / "workbench_snapshot.json"
    if request_path.startswith("/assets/"):
        return safe_child_path(WORKBENCH_DIST, request_path)
    return None


def persist_live_row_payload(*, project: str, row: str, kind: str, payload: dict[str, Any]) -> tuple[str, bytes]:
    project = snapshot.validate_project_slug(project)
    if not re.fullmatch(r"[a-z0-9_]+", row):
        raise ValueError(f"invalid item slug: {row!r}")
    if kind not in {"review", "action"}:
        raise ValueError(f"invalid live row payload kind: {kind!r}")
    payload_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    payload_bytes = payload_text.encode("utf-8")
    digest = hashlib.sha256(payload_bytes).hexdigest()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    workspace = snapshot.REPO / "projects" / project / "workspace" / "forensic_workbench_applied"
    stem = f"{stamp}_{row}_{kind}_{digest[:12]}"
    path = workspace / f"{stem}.json"
    suffix = 1
    while path.exists():
        path = workspace / f"{stem}_{suffix}.json"
        suffix += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload_bytes)
    return repo_rel(path), payload_bytes


def live_row_payload_with_case(
    payload: dict[str, Any],
    *,
    project: str,
    rubric: str | None,
    intake: str | None,
) -> dict[str, Any]:
    scoped_payload = dict(payload)
    if str(scoped_payload.get("project") or "") != project:
        raise ValueError("project-check file project must match request project")

    existing_rubric = str(scoped_payload.get("rubric") or "").strip()
    if rubric and existing_rubric and existing_rubric != rubric:
        raise ValueError("project-check file rubric must match request rubric")
    if rubric and not existing_rubric:
        scoped_payload["rubric"] = rubric

    if intake:
        expected_case_key = case_key(project, intake)
        existing_intake = str(scoped_payload.get("intake") or "").strip()
        if existing_intake and existing_intake != intake:
            raise ValueError("project-check file intake must match request intake")
        existing_project_key = str(scoped_payload.get("project_key") or "").strip()
        if existing_project_key and existing_project_key != expected_case_key:
            raise ValueError("project-check file project key must match request project intake")
        existing_case_key = str(scoped_payload.get("case_key") or "").strip()
        if existing_case_key and existing_case_key != expected_case_key:
            raise ValueError("project-check file compatibility key must match request project intake")
        scoped_payload["intake"] = intake
        scoped_payload["project_key"] = expected_case_key
        scoped_payload["case_key"] = expected_case_key
    return scoped_payload


def live_project_check_payload(payload: dict[str, Any], *, slug: str) -> dict[str, Any]:
    scoped_payload = dict(payload)
    check_slug = str(slug or "").strip()
    check_label = receipt_check_label(
        str(scoped_payload.get("project_check_label") or scoped_payload.get("item_label") or ""),
        check_slug,
        str(scoped_payload.get("row") or ""),
    )
    if check_slug:
        for key in ("project_check_slug", "item_slug", "row_slug"):
            if not str(scoped_payload.get(key) or "").strip():
                scoped_payload[key] = check_slug
    if check_label:
        for key in ("project_check_label", "item_label"):
            if not str(scoped_payload.get(key) or "").strip():
                scoped_payload[key] = check_label
    return scoped_payload


def case_file_payload_with_case(
    payload: dict[str, Any],
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
) -> dict[str, Any]:
    scoped_payload = dict(payload)
    if str(scoped_payload.get("project") or "") != project:
        raise ValueError("project_file project must match request project")

    rubric_value = str(rubric or scoped_payload.get("rubric") or "").strip()
    existing_rubric = str(scoped_payload.get("rubric") or "").strip()
    if rubric and existing_rubric and existing_rubric != rubric:
        raise ValueError("project_file rubric must match request rubric")
    if rubric_value:
        scoped_payload["rubric"] = rubric_value

    intake_value = str(intake or scoped_payload.get("intake") or "").strip()
    existing_intake = str(scoped_payload.get("intake") or "").strip()
    if intake and existing_intake and existing_intake != intake:
        raise ValueError("project_file intake must match request intake")
    if intake_value:
        expected_case_key = case_key(project, intake_value)
        existing_project_key = str(scoped_payload.get("project_key") or "").strip()
        if existing_project_key and existing_project_key != expected_case_key:
            raise ValueError("project_file project key must match request project intake")
        existing_case_key = str(scoped_payload.get("case_key") or "").strip()
        if existing_case_key and existing_case_key != expected_case_key:
            raise ValueError("project_file compatibility key must match request project intake")
        scoped_payload["intake"] = intake_value
        scoped_payload["project_key"] = expected_case_key
        scoped_payload["case_key"] = expected_case_key
    return scoped_payload


def path_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def preview_path_allowed(path: str) -> bool:
    normalized = PurePosixPath(path)
    parts = normalized.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return False
    if any(part in FILE_PREVIEW_BLOCKED_PARTS for part in parts):
        return False
    if len(parts) == 1 and parts[0] in FILE_PREVIEW_ALLOWED_FILES:
        return True
    preview_root = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
    return preview_root in FILE_PREVIEW_ALLOWED_ROOTS or parts[0] in FILE_PREVIEW_ALLOWED_ROOTS


def file_preview_payload(path: str) -> dict[str, Any]:
    if not path:
        raise ValueError("path is required")
    candidate = Path(path)
    if candidate.is_absolute():
        raise ValueError("path must be relative to the repository")
    normalized = PurePosixPath(path).as_posix()
    if not preview_path_allowed(normalized):
        raise ValueError("path is outside the workbench preview roots")
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
        "ok": True,
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


def read_optional_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_json_object(path, repo_rel(path))


def read_jsonl_objects(path: Path, *, limit: int = 100) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows[-limit:]


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
        "ok": True,
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
        "ok": True,
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
    entries = snapshot.list_project_entries()
    for entry in entries:
        row = dict(entry)
        row["status"] = str(row.get("status") or "case_ready")
        row["project_status"] = project_status_value(row.get("status"))
        row["display_label"] = project_display_label(row.get("display_label") or row.get("project"))
        row["status_label"] = project_status_label(row.get("status"), intake_source=row.get("intake_source"))
        row["display_status"] = row["status_label"]
        row["latest_project_check"] = str(row.get("latest_project_check") or row.get("latest_item_action") or row.get("latest_row_action") or "")
        row["latest_project_file_write"] = str(row.get("latest_project_file_write") or row.get("latest_case_file_write") or "")
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
            row["intake_error"] = display_text(exc)
        projects.append(row)
    project_folders = snapshot.list_project_folders(entries)
    for folder in project_folders:
        folder["display_label"] = project_display_label(folder.get("display_label") or folder.get("project"))
        folder["project_status"] = project_status_value(folder.get("status"))
        folder["status_label"] = project_status_label(folder.get("status"), intake_source=folder.get("intake_source"))
        folder["display_status"] = folder["status_label"]
        folder["hidden_by_default"] = background_project_folder(folder.get("project"))
        folder["latest_project_check"] = str(folder.get("latest_project_check") or folder.get("latest_item_action") or folder.get("latest_row_action") or "")
        folder["latest_project_file_write"] = str(folder.get("latest_project_file_write") or folder.get("latest_case_file_write") or "")
        folder["has_project_files"] = bool(
            folder.get("raw_exists")
            or folder.get("workspace_exists")
            or folder.get("source_type_map_exists")
            or folder.get("intake_count")
        )
        folder["has_case_material"] = folder["has_project_files"]
    openable_projects = {str(row.get("project") or "") for row in projects if row.get("project")}
    entries_by_project = {str(row.get("project") or ""): row for row in projects if row.get("project")}
    for folder in project_folders:
        project = str(folder.get("project") or "")
        ready_entry = entries_by_project.get(project)
        folder["openable"] = project in openable_projects
        if ready_entry:
            for key in (
                "intake",
                "intake_source",
                "intake_editable",
                "intake_ref_summary",
                "intake_error",
                "latest_review",
                "latest_project_check",
                "latest_item_action",
                "latest_row_action",
                "latest_intake_edit",
                "latest_source_import",
                "latest_source_edit",
                "latest_source_action",
                "latest_project_file_write",
                "latest_case_file_write",
                "report_contract",
            ):
                if key in ready_entry:
                    folder[key] = ready_entry.get(key)
    project_folders.sort(key=lambda row: project_inventory_sort_key(row, openable_projects=openable_projects))
    pending_project_folders = [
        row
        for row in project_folders
        if str(row.get("project") or "") not in openable_projects
    ]
    folder_summary = project_folder_summary(project_folders, openable_projects=openable_projects)
    return {
        "schema": "ztare-forensic-workbench-project-index-v1",
        "ok": True,
        "default_project": snapshot.DEFAULT_PROJECT,
        "project_inventory_scope": "all_projects_directory",
        "inventory_root": "projects/",
        "inventory_includes_all_project_folders": True,
        "ready_count": len(projects),
        "intake_ready_count": len(projects),
        "project_count": len(project_folders),
        "folder_count": len(project_folders),
        "pending_folder_count": len(pending_project_folders),
        "folder_summary": folder_summary,
        "project_folder_summary": folder_summary,
        "intake_ready_projects": projects,
        "projects": projects,
        "all_project_folders": project_folders,
        "project_folders": [compact_project_folder(row) for row in project_folders],
        "project_folders_compact": True,
        "project_folder_detail_field": "all_project_folders",
    }


def compact_project_folder(row: dict[str, Any]) -> dict[str, Any]:
    """Compatibility project-folder row without heavy preview arrays."""

    keys = [
        "project",
        "project_dir",
        "display_label",
        "status",
        "status_label",
        "display_status",
        "project_status",
        "openable",
        "hidden_by_default",
        "has_project_files",
        "has_case_material",
        "intake_count",
        "latest_review",
        "latest_project_check",
        "latest_project_file_write",
        "raw_exists",
        "workspace_exists",
        "source_type_map_exists",
    ]
    return {key: row.get(key) for key in keys if key in row}


def project_inventory_sort_key(row: dict[str, Any], *, openable_projects: set[str]) -> tuple[int, int, int, int, str]:
    project = str(row.get("project") or "")
    openable = project in openable_projects or bool(row.get("openable") or row.get("intake_count"))
    hidden = bool(row.get("hidden_by_default") or background_project_folder(project))
    has_files = bool(row.get("has_project_files") or row.get("has_case_material"))
    default_rank = 0 if project == snapshot.DEFAULT_PROJECT else 1
    return (
        0 if openable else 1,
        default_rank,
        1 if hidden else 0,
        0 if has_files else 1,
        project,
    )


def project_folder_summary(project_folders: list[dict[str, Any]], *, openable_projects: set[str] | None = None) -> dict[str, Any]:
    openable_projects = openable_projects or set()
    pending = [
        row
        for row in project_folders
        if str(row.get("project") or "") not in openable_projects
    ]
    with_material = [
        row
        for row in pending
        if row.get("has_project_files")
        or row.get("has_case_material")
        or row.get("raw_exists")
        or row.get("workspace_exists")
        or row.get("source_type_map_exists")
        or row.get("intake_count")
    ]
    generated = [row for row in pending if row.get("hidden_by_default") or background_project_folder(row.get("project"))]
    return {
        "total": len(project_folders),
        "openable": len(openable_projects),
        "needs_intake": len(pending),
        "needs_intake_with_files": len(with_material),
        "needs_intake_empty": max(0, len(pending) - len(with_material)),
        "generated_hidden_by_default": len(generated),
    }


def server_status_payload() -> dict[str, Any]:
    app_built = (WORKBENCH_DIST / "index.html").exists()
    snapshot_path = WORKBENCH_PUBLIC / "workbench_snapshot.json"
    snapshot_available = snapshot_path.exists()
    project_error = ""
    projects: list[dict[str, Any]] = []
    project_folders: list[dict[str, Any]] = []
    project_folder_summary_payload: dict[str, Any] = {}
    pending_folder_count = 0
    default_project = snapshot.DEFAULT_PROJECT
    try:
        project_index = project_index_payload()
        projects = list(project_index.get("projects") or [])
        project_folders = list(project_index.get("project_folders") or [])
        project_folder_summary_payload = dict(project_index.get("project_folder_summary") or {})
        pending_folder_count = int(project_index.get("pending_folder_count") or 0)
        default_project = str(project_index.get("default_project") or default_project)
    except Exception as exc:  # noqa: BLE001 - status should report readiness, not crash.
        project_error = display_text(exc)
    checks = {
        "api_ready": bool(project_folders),
        "app_built": app_built,
        "snapshot_available": snapshot_available,
        "projects_available": bool(project_folders),
    }
    primary_endpoints = [
        "GET /api/status",
        "GET /api/projects",
        "GET /api/snapshot",
        "GET /api/health",
        "GET /api/trace",
        "GET /api/workflow",
        "GET /api/report-contract",
        "GET /api/intake",
        "GET /api/sources",
        "GET /api/source-file",
        "GET /api/receipts",
        "GET /api/run-history",
        "GET /api/evidence-support",
        "GET /api/file",
        "POST /api/project-create",
        "POST /api/source-import",
        "POST /api/source-edit",
        "POST /api/source-action",
        "POST /api/intake",
        "POST /api/preflight",
        "POST /api/run",
        "POST /api/project-file",
        "POST /api/review",
        "POST /api/next-step",
    ]
    compatibility_endpoints = [
        "GET /api/claim-support",
        "POST /api/case-file",
        "POST /api/item-action",
        "POST /api/row-action",
    ]
    action_contracts = {
        "project_inventory": {
            "label": "Projects",
            "route": "GET /api/projects",
            "mode": "read-only",
            "writes_project_files": False,
            "requires_confirmation": False,
            "browser_writes": False,
        },
        "snapshot": {
            "label": "Project data",
            "route": "GET /api/snapshot",
            "mode": "read-only",
            "writes_project_files": False,
            "requires_confirmation": False,
            "browser_writes": False,
        },
        "workflow": {
            "label": "Project steps",
            "route": "GET /api/workflow",
            "mode": "read-only",
            "writes_project_files": False,
            "requires_confirmation": False,
            "browser_writes": False,
        },
        "evidence_support": {
            "label": "Support audit",
            "route": "GET /api/evidence-support",
            "mode": "read-only",
            "writes_project_files": False,
            "requires_confirmation": False,
            "browser_writes": False,
        },
        "project_create": {
            "label": "Create project or add intake",
            "route": "POST /api/project-create",
            "mode": "writes project files",
            "write_path_templates": [
                "projects/{project}",
                "projects/{project}/raw",
                "projects/{project}/workspace",
                "projects/{project}/raw/source_type_map.json",
                "projects/{project}/{project}_intake.json",
            ],
            "writes_project_files": True,
            "requires_confirmation": False,
            "browser_writes": False,
        },
        "intake_edit": {
            "label": "Intake save",
            "route": "POST /api/intake",
            "mode": "writes project files",
            "write_path_templates": [
                "{intake}",
                "projects/{project}/workspace/forensic_workbench_intake_edits.jsonl",
                "projects/{project}/workspace/forensic_workbench_latest_intake_edit.json",
            ],
            "writes_project_files": True,
            "requires_confirmation": False,
            "browser_writes": False,
        },
        "source_import": {
            "label": "Add source",
            "route": "POST /api/source-import",
            "mode": "writes project files",
            "write_path_templates": [
                "projects/{project}/raw/{filename}",
                "projects/{project}/raw/source_type_map.json",
                "projects/{project}/workspace/forensic_workbench_source_imports.jsonl",
                "projects/{project}/workspace/forensic_workbench_latest_source_import.json",
            ],
            "writes_project_files": True,
            "requires_confirmation": False,
            "browser_writes": False,
        },
        "source_edit": {
            "label": "Save source",
            "route": "POST /api/source-edit",
            "mode": "writes project files",
            "write_path_templates": [
                "projects/{project}/raw/{relative}",
                "projects/{project}/raw/source_type_map.json",
                "projects/{project}/workspace/forensic_workbench_source_edits.jsonl",
                "projects/{project}/workspace/forensic_workbench_latest_source_edit.json",
            ],
            "writes_project_files": True,
            "requires_confirmation": False,
            "browser_writes": False,
        },
        "source_check": {
            "label": SOURCE_ACTIONS["source_check"]["label"],
            "route": "POST /api/source-action",
            "action": "source_check",
            "command_template": SOURCE_ACTIONS["source_check"]["display"],
            "write_path_templates": SOURCE_ACTIONS["source_check"]["write_path_templates"],
            "mode": "read-only",
            "writes_project_files": False,
            "requires_confirmation": False,
            "browser_writes": False,
        },
        "source_index": {
            "label": SOURCE_ACTIONS["source_index"]["label"],
            "route": "POST /api/source-action",
            "action": "source_index",
            "command_template": SOURCE_ACTIONS["source_index"]["display"],
            "write_path_templates": SOURCE_ACTIONS["source_index"]["write_path_templates"],
            "mode": "writes file index",
            "writes_project_files": True,
            "requires_confirmation": False,
            "browser_writes": False,
        },
        "evidence_bind": {
            "label": SOURCE_ACTIONS["evidence_bind"]["label"],
            "route": "POST /api/source-action",
            "action": "evidence_bind",
            "command_template": SOURCE_ACTIONS["evidence_bind"]["display"],
            "write_path_templates": SOURCE_ACTIONS["evidence_bind"]["write_path_templates"],
            "mode": "saves evidence connection",
            "writes_project_files": True,
            "requires_confirmation": False,
            "browser_writes": False,
        },
        "evidence_replay": {
            "label": SOURCE_ACTIONS["evidence_replay"]["label"],
            "route": "POST /api/source-action",
            "action": "evidence_replay",
            "command_template": SOURCE_ACTIONS["evidence_replay"]["display"],
            "write_path_templates": SOURCE_ACTIONS["evidence_replay"]["write_path_templates"],
            "mode": "read-only",
            "writes_project_files": False,
            "requires_confirmation": False,
            "browser_writes": False,
        },
        "preflight": {
            "label": "Preflight",
            "route": "POST /api/preflight",
            "mode": "writes receipt",
            "write_path_templates": [
                "projects/{project}/workspace/iteration_telemetry.jsonl",
            ],
            "writes_project_files": True,
            "requires_confirmation": False,
            "browser_writes": False,
        },
        "run_preview_and_confirm": {
            "label": "Run",
            "route": "POST /api/run",
            "mode": "asks before writing",
            "write_path_templates": [
                "projects/{project}/workspace/iteration_telemetry.jsonl",
                "projects/{project}/latest_eval_results.json",
                "projects/{project}/eval_results.jsonl",
            ],
            "writes_project_files": True,
            "requires_confirmation": True,
            "browser_writes": False,
        },
        "review": {
            "label": "Save review",
            "route": "POST /api/review",
            "mode": "writes receipt",
            "write_path_templates": [
                "projects/{project}/workspace/forensic_workbench_applied/<timestamp>_{project_check_slug}_review_<hash>.json",
                "projects/{project}/workspace/forensic_workbench_reviews.jsonl",
                "projects/{project}/workspace/forensic_workbench_latest_review.json",
            ],
            "writes_project_files": True,
            "requires_confirmation": False,
            "browser_writes": False,
        },
        "next_step": {
            "label": "Save next step",
            "route": "POST /api/next-step",
            "mode": "writes receipt",
            "write_path_templates": [
                "projects/{project}/workspace/forensic_workbench_applied/<timestamp>_{project_check_slug}_action_<hash>.json",
                "projects/{project}/workspace/forensic_workbench_row_actions.jsonl",
                "projects/{project}/workspace/forensic_workbench_latest_row_action.json",
            ],
            "writes_project_files": True,
            "requires_confirmation": False,
            "browser_writes": False,
        },
        "project_file": {
            "label": "Project file",
            "route": "POST /api/project-file",
            "mode": "writes project file",
            "write_path_templates": [
                "projects/{project}/workspace/forensic_workbench_case_file_{project_file_digest}.json",
                "projects/{project}/workspace/forensic_workbench_case_files.jsonl",
                "projects/{project}/workspace/forensic_workbench_latest_case_file_write.json",
            ],
            "writes_project_files": True,
            "requires_confirmation": False,
            "browser_writes": False,
        },
    }
    def action_behavior(contract: dict[str, Any]) -> str:
        if contract.get("requires_confirmation"):
            return "asks before writing"
        if contract.get("writes_project_files"):
            return "writes files or receipts"
        return "read-only"

    for contract in action_contracts.values():
        contract["behavior"] = action_behavior(contract)
        templates = contract.get("write_path_templates")
        if isinstance(templates, list):
            contract["display_write_path_templates"] = [
                display_write_path_template(template)
                for template in templates
                if template
            ]
    read_only_actions = [row["label"] for row in action_contracts.values() if not row["writes_project_files"]]
    write_actions = [
        row["label"]
        for row in action_contracts.values()
        if row["writes_project_files"] and not row["requires_confirmation"]
    ]
    confirmation_actions = [row["label"] for row in action_contracts.values() if row["requires_confirmation"]]
    file_change_summary = {
        "read_only_count": len(read_only_actions),
        "write_count": len(write_actions),
        "ask_first_count": len(confirmation_actions),
        "read_only_steps": read_only_actions,
        "write_steps": write_actions,
        "ask_first_steps": confirmation_actions,
        "browser_writes": False,
    }
    payload: dict[str, Any] = {
        "schema": SERVER_STATUS_SCHEMA,
        "ok": checks["api_ready"],
        "app_name": "Project Workbench",
        "workflow_label": "Project steps",
        "project_inventory_scope": "all_projects_directory",
        "inventory_root": "projects/",
        "inventory_includes_all_project_folders": True,
        "project_count": len(project_folders),
        "intake_ready_count": len(projects),
        "pending_folder_count": pending_folder_count,
        "default_project": default_project,
        "server": {
            "name": "Project Workbench",
            "version": "0.1",
            "implementation": "React/Vite + local Python API",
        },
        "api_ready": checks["api_ready"],
        "app_built": checks["app_built"],
        "snapshot_available": checks["snapshot_available"],
        "projects_available": checks["projects_available"],
        "checks": checks,
        "app": {
            "url_path": "/",
            "index_path": display_path(WORKBENCH_DIST / "index.html"),
        },
        "snapshot": {
            "url_path": "/workbench_snapshot.json",
            "path": display_path(snapshot_path),
        },
        "api": {
            "primary_route_count": len(primary_endpoints),
            "compatibility_route_count": len(compatibility_endpoints),
            "project_inventory_scope": "all_projects_directory",
            "inventory_root": "projects/",
            "inventory_includes_all_project_folders": True,
            "project_count": len(project_folders),
            "intake_ready_count": len(projects),
            "pending_folder_count": pending_folder_count,
            "folder_summary": project_folder_summary_payload,
            "primary_live_routes": {
                "project_inventory": "GET /api/projects",
                "snapshot": "GET /api/snapshot",
                "workflow": "GET /api/workflow",
                "evidence_support": "GET /api/evidence-support",
                "intake_edit": "POST /api/intake",
                "source_import": "POST /api/source-import",
                "source_edit": "POST /api/source-edit",
                "source_check": "POST /api/source-action",
                "source_index": "POST /api/source-action",
                "evidence_bind": "POST /api/source-action",
                "evidence_replay": "POST /api/source-action",
                "preflight": "POST /api/preflight",
                "run_preview_and_confirm": "POST /api/run",
                "review": "POST /api/review",
                "next_step": "POST /api/next-step",
                "project_file": "POST /api/project-file",
                "project_create": "POST /api/project-create",
            },
            "action_contracts": action_contracts,
            "action_summary": {
                "read_only_count": len(read_only_actions),
                "write_without_confirmation_count": len(write_actions),
                "confirmation_required_count": len(confirmation_actions),
                "read_only_actions": read_only_actions,
                "write_without_confirmation_actions": write_actions,
                "confirmation_required_actions": confirmation_actions,
            },
            "file_change_summary": file_change_summary,
            "write_contract": {
                "browser_writes": False,
                "requires_explicit_server_write": True,
                "action_count": len(action_contracts),
                "write_action_count": sum(1 for row in action_contracts.values() if row["writes_project_files"]),
                "write_without_confirmation_count": sum(
                    1
                    for row in action_contracts.values()
                    if row["writes_project_files"] and not row["requires_confirmation"]
                ),
                "read_only_action_count": sum(1 for row in action_contracts.values() if not row["writes_project_files"]),
                "confirmation_required_count": sum(1 for row in action_contracts.values() if row["requires_confirmation"]),
            },
            "file_preview": {
                "mode": "bounded repo preview",
                "max_preview_bytes": MAX_PREVIEW_BYTES,
                "allowed_roots": list(FILE_PREVIEW_ALLOWED_ROOTS),
                "allowed_root_files": sorted(FILE_PREVIEW_ALLOWED_FILES),
                "blocked_path_parts": sorted(FILE_PREVIEW_BLOCKED_PARTS),
            },
            "endpoints": primary_endpoints,
            "compatibility_endpoints": compatibility_endpoints,
        },
        "projects": {
            "project_count": len(project_folders),
            "project_inventory_scope": "all_projects_directory",
            "inventory_root": "projects/",
            "inventory_includes_all_project_folders": True,
            "ready_count": len(projects),
            "intake_ready_count": len(projects),
            "count": len(project_folders),
            "folder_count": len(project_folders),
            "pending_folder_count": pending_folder_count,
            "folder_summary": project_folder_summary_payload,
            "default_project": default_project,
        },
    }
    if project_error:
        payload["projects"]["error"] = project_error
    return payload


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


def case_key(project: str, intake: str | None) -> str:
    intake_value = str(intake or "").strip()
    return f"{project}::{intake_value}" if intake_value else project


def case_file_stem(project: str, intake: str | None) -> str:
    digest = hashlib.sha256(case_key(project, intake).encode("utf-8")).hexdigest()[:12]
    return f"forensic_workbench_case_file_{digest}"


def add_case_context(
    receipt: dict[str, Any],
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
) -> dict[str, Any]:
    rubric_value = str(rubric or "").strip()
    intake_value = str(intake or "").strip()
    if rubric_value:
        receipt["rubric"] = rubric_value
    if intake_value:
        receipt["intake"] = intake_value
    key = case_key(project, intake_value)
    receipt["project_key"] = key
    receipt["case_key"] = key
    return receipt


def write_boundary_payload(
    *,
    writes_project_files: bool,
    write_paths: list[str] | None = None,
    receipt_path: str = "",
    latest_path: str = "",
    read_only_actions: list[str] | None = None,
) -> dict[str, Any]:
    clean_write_paths: list[str] = []
    for path in write_paths or []:
        if path and path not in clean_write_paths:
            clean_write_paths.append(path)
    return {
        "schema": "ztare-forensic-workbench-write-boundary-v1",
        "writes_project_files": bool(writes_project_files),
        "browser_writes": False,
        "write_paths": clean_write_paths,
        "receipt_path": receipt_path,
        "latest_path": latest_path,
        "read_only_actions": read_only_actions or ["preview", "copy", "download"],
    }


def post_error_payload(path: str, exc: BaseException) -> dict[str, Any]:
    payload: dict[str, Any] = {"ok": False, "error": display_text(exc)}
    if path in WRITE_POST_ENDPOINTS:
        payload["write_boundary"] = write_boundary_payload(
            writes_project_files=False,
            read_only_actions=["inspect error", "preview", "copy"],
        )
    return payload


def preflight_telemetry_path(project: str) -> str:
    return f"projects/{project}/workspace/iteration_telemetry.jsonl"


def preflight_write_paths(trace_payload: dict[str, Any] | None) -> list[str]:
    trace_payload = trace_payload or {}
    loop = trace_payload.get("loop_admission") or trace_payload.get("preflight_receipt") or {}
    if not isinstance(loop, dict):
        return []
    paths: list[str] = []
    for key in ("path", "receipt_path", "preflight_receipt_path", "loop_admission_path", "latest", "ledger"):
        value = display_path(loop.get(key))
        if value and value not in paths:
            paths.append(value)
    if loop.get("receipt_count") and trace_payload.get("project"):
        telemetry_path = preflight_telemetry_path(str(trace_payload["project"]))
        if telemetry_path not in paths:
            paths.append(telemetry_path)
    return paths


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


def receipt_check_label(label: str, slug: str = "", row_label: str = "") -> str:
    raw_slug = str(slug or "")
    if raw_slug in {"report_export", "report_support"}:
        return "Report support"
    raw_row_label = snapshot.display_check_label(str(row_label or ""))
    if raw_row_label:
        return raw_row_label
    raw_label = snapshot.display_check_label(str(label or ""))
    if raw_label:
        return raw_label
    return ""


def normalize_receipt_row(payload: dict[str, Any], *, kind: str, path: str, line: int) -> dict[str, Any]:
    display_kind = {
        "review": "review",
        "row_action": "next step",
        "intake_edit": "intake change",
        "source_import": "new source",
        "source_edit": "source edit",
        "source_action": "source check",
        "case_file": "project file",
        "unreadable": "unreadable receipt",
    }.get(kind, display_value(kind))
    project_key = str(payload.get("project_key") or payload.get("case_key") or "")
    compatibility_key = str(payload.get("case_key") or payload.get("project_key") or "")
    row: dict[str, Any] = {
        "kind": kind,
        "display_kind": display_kind,
        "schema": str(payload.get("schema") or ""),
        "applied_at": str(payload.get("applied_at") or ""),
        "project": str(payload.get("project") or ""),
        "rubric": str(payload.get("rubric") or ""),
        "intake": str(payload.get("intake") or payload.get("intake_path") or ""),
        "project_key": project_key,
        "case_key": compatibility_key,
        "path": path,
        "line": line,
        "summary": "",
    }
    if kind == "review":
        item_label = str(payload.get("project_check_label") or payload.get("item_label") or payload.get("row") or "")
        item_slug = str(payload.get("project_check_slug") or payload.get("item_slug") or payload.get("row_slug") or "")
        check_label = receipt_check_label(item_label, item_slug, str(payload.get("row") or ""))
        row.update(
            {
                "project_check_label": str(payload.get("project_check_label") or check_label or item_label),
                "project_check_slug": str(payload.get("project_check_slug") or item_slug),
                "item_label": item_label,
                "item_slug": item_slug,
                "check_label": check_label,
                "display_label": check_label,
                "row": str(payload.get("row") or ""),
                "row_slug": str(payload.get("row_slug") or item_slug),
                "decision": str(payload.get("decision") or ""),
                "display_decision": display_value(payload.get("decision") or ""),
                "note": str(payload.get("note") or ""),
                "review_file_path": display_path(payload.get("review_file_path")),
                "evidence_ref_count": safe_int(payload.get("evidence_ref_count")),
                "sha256": str(payload.get("review_file_sha256") or ""),
            }
        )
        row["summary"] = f"{display_value(row['decision'])} on {check_label or item_slug or 'project check'}"
    elif kind == "row_action":
        item_label = str(payload.get("project_check_label") or payload.get("item_label") or payload.get("row") or "")
        item_slug = str(payload.get("project_check_slug") or payload.get("item_slug") or payload.get("row_slug") or "")
        check_label = receipt_check_label(item_label, item_slug, str(payload.get("row") or ""))
        row.update(
            {
                "project_check_label": str(payload.get("project_check_label") or check_label or item_label),
                "project_check_slug": str(payload.get("project_check_slug") or item_slug),
                "item_label": item_label,
                "item_slug": item_slug,
                "check_label": check_label,
                "display_label": check_label,
                "row": str(payload.get("row") or ""),
                "row_slug": str(payload.get("row_slug") or item_slug),
                "action": str(payload.get("action") or ""),
                "display_action": display_value(payload.get("action") or ""),
                "note": str(payload.get("note") or ""),
                "action_file_path": display_path(payload.get("action_file_path")),
                "evidence_ref_count": safe_int(payload.get("evidence_ref_count")),
                "sha256": str(payload.get("action_file_sha256") or ""),
            }
        )
        row["summary"] = f"{display_value(row['action'])} on {check_label or item_slug or 'check'}"
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
    elif kind in {"source_import", "source_edit"}:
        row.update(
            {
                "source_path": str(payload.get("source_path") or ""),
                "source_type": str(payload.get("source_type") or ""),
                "display_source_type": display_value(payload.get("source_type") or ""),
                "chars": safe_int(payload.get("chars")),
                "sha256": str(payload.get("sha256") or ""),
            }
        )
        verb = "Imported" if kind == "source_import" else "Edited"
        row["summary"] = f"{verb} {row['source_path'] or 'source'} as {display_value(row['source_type'])}"
    elif kind == "source_action":
        row.update(
            {
                "action": str(payload.get("action") or ""),
                "display_action": display_value(payload.get("action") or ""),
                "label": str(payload.get("label") or ""),
                "display_label": display_value(payload.get("label") or payload.get("action") or ""),
                "accepted": bool(payload.get("accepted")),
                "display_status": "accepted" if payload.get("accepted") else "needs attention",
                "returncode": safe_int(payload.get("returncode")),
                "source_path": str(payload.get("source_path") or ""),
                "source_receipt_path": str(payload.get("source_receipt_path") or ""),
                "source_sha256": str(payload.get("source_sha256") or ""),
                "source_receipt_sha256": str(payload.get("source_receipt_sha256") or ""),
                "sha256": str(payload.get("source_sha256") or payload.get("source_receipt_sha256") or ""),
            }
        )
        status = "accepted" if row["accepted"] else "attention"
        row["summary"] = (
            f"{display_value(row['label'] or row['action'])} {status}; "
            f"file={row['source_path'] or row['source_receipt_path'] or 'not loaded'}"
        )
    elif kind == "case_file":
        project_check_count = safe_int(payload.get("project_check_count") or payload.get("item_count") or payload.get("row_count"))
        item_label = "project check" if project_check_count == 1 else "project checks"
        row.update(
            {
                "project_file_path": str(payload.get("project_file_path") or payload.get("case_file_path") or ""),
                "project_file_sha256": str(payload.get("project_file_sha256") or payload.get("case_file_sha256") or ""),
                "case_file_path": str(payload.get("case_file_path") or ""),
                "project_check_count": project_check_count,
                "item_count": project_check_count,
                "row_count": project_check_count,
                "command_count": safe_int(payload.get("command_count")),
                "receipt_count": safe_int(payload.get("receipt_count")),
                "sha256": str(payload.get("project_file_sha256") or payload.get("case_file_sha256") or ""),
            }
        )
        row["summary"] = (
            f"Saved project file with {row['project_check_count']} {item_label}, "
            f"{row['command_count']} command details, {row['receipt_count']} receipts"
        )
    else:
        row["summary"] = kind.replace("_", " ")
    row["display_summary"] = display_guidance_text(row.get("summary") or "")
    return row


def display_value(value: Any) -> str:
    raw = str(value or "recorded")
    overrides = {
        "blocked": "hold report",
        "next_step": "next step",
        "needs_source": "needs source",
        "ready_to_run": "run checks",
        "export_blocker": "fix report support",
    }
    return overrides.get(raw, raw.replace("_", " "))


def display_status(value: Any) -> str:
    raw = str(value or "unknown")
    if raw == "unbound":
        return "not connected"
    if raw == "missing_packet":
        return "missing evidence file"
    return snapshot.display_status(raw)


def display_surface(value: Any) -> str:
    raw = str(value or "")
    surface_overrides = {
        "project_dir": "project folder",
        "raw_sources": "source files",
        "source_preflight": "source check",
        "source_index": "file index",
        "source_index_receipt": "source receipt",
        "compile_provenance": "evidence receipt",
        "evidence_output": "evidence output",
        "evidence_replay": "evidence replay",
        "claim_support": "evidence support",
        "evidence_gaps": "evidence gaps",
        "project_intake": "project intake",
        "project_trace": "project run history",
        "launch_preflight": "preflight",
        "mutator_briefing": "run briefing",
        "prediction_contracts": "forecast records",
        "eval_history": "run history",
    }
    return surface_overrides.get(raw, display_value(raw or "check"))


def display_action_label(value: Any) -> str:
    raw = str(value or "")
    action_overrides = {
        "weak_gp233_linkage": "evidence links need repair",
        "stale_trajectory_output": "run-history archive is stale",
        "unconsumed_surface": "work log is missing",
        "source_compilation_defect": "source compilation needs repair",
        "repair_source_emitter": "repair source logs",
        "split_contract": "split into a smaller question",
        "ask_another_independent_agent": "ask for another independent check",
        "defer": "defer",
        "surface_trajectory_cluster": "surface related run history",
        "diagnostic_only": "diagnostic only",
        "none_advisory_only": "advisory only",
        "gp230_read_model": "forecast record summary",
        "gp233": "evidence ledger",
        "trajectory_surfacing": "run-history surfacing",
        "forecast_ops": "forecast records",
        "warning": "warning",
    }
    return action_overrides.get(raw, display_surface(raw))


def display_guidance_text(value: Any) -> str:
    text = display_text(value)
    replacements = {
        "markdown-only GP-233 linkage": "doc-only evidence-ledger linkage",
        "GP-233": "evidence ledger",
        "gp233": "evidence ledger",
        "GP-230": "forecast record",
        "gp230": "forecast record",
        "trajectory outputs": "run-history outputs",
        "trajectory/primitives surfacing": "run-history and primitive surfacing",
        "surfacing event ledger": "work ledger",
        "surfacing-event ledger": "work ledger",
        "diagnostic-only": "diagnostic only",
        "non-diagnostic": "substantive",
        "R1 declaration": "run declaration",
        "the " + "CHG-142" + " change": "the recorded change",
        "export" + " worker": "report-support worker",
    }
    for raw, rendered in replacements.items():
        text = text.replace(raw, rendered)
    return text


def display_evidence_ref(value: Any) -> dict[str, str]:
    path = display_path(value)
    lower = path.lower()
    if "gp-233_evidence_ledger" in lower or "research_yield_decomposition" in lower:
        label = "Evidence ledger file"
    elif "forecast_pool/aggregates" in lower:
        label = "Forecast summary file"
    elif "forecast_pool/contracts" in lower:
        label = "Forecast question file"
    elif "forecast_pool/market_state" in lower:
        label = "Forecast market file"
    elif "trajectory_archive" in lower:
        label = "Run-history archive"
    elif "surfacing_event_ledger" in lower:
        label = "Work log"
    else:
        label = "Evidence file"
    return {"label": label, "path": path}


def display_write_path_template(value: Any) -> dict[str, str]:
    path = display_path(value)
    lower = path.lower()
    if "_intake.json" in lower:
        label = "Project intake"
    elif "/raw/source_type_map.json" in lower:
        label = "Source role map"
    elif "/raw/" in lower:
        label = "Source file"
    elif "source_index_receipt" in lower:
        label = "File-index receipt"
    elif "source_index.json" in lower:
        label = "File index"
    elif "workspace_meta.json" in lower:
        label = "Workspace metadata"
    elif "evidence_output_binding_receipt" in lower:
        label = "Evidence connection receipt"
    elif "iteration_telemetry" in lower:
        label = "Run telemetry"
    elif "latest_eval_results" in lower:
        label = "Latest run result"
    elif "eval_results" in lower:
        label = "Run result history"
    elif "forensic_workbench_applied" in lower and "_review_" in lower:
        label = "Review handoff file"
    elif "forensic_workbench_reviews" in lower:
        label = "Review ledger"
    elif "forensic_workbench_latest_review" in lower:
        label = "Latest review receipt"
    elif "forensic_workbench_applied" in lower and "_action_" in lower:
        label = "Next-step handoff file"
    elif "forensic_workbench_row_actions" in lower:
        label = "Next-step ledger"
    elif "forensic_workbench_latest_row_action" in lower:
        label = "Latest next-step receipt"
    elif "forensic_workbench_intake_edits" in lower:
        label = "Intake-edit ledger"
    elif "forensic_workbench_latest_intake_edit" in lower:
        label = "Latest intake-edit receipt"
    elif "forensic_workbench_source_imports" in lower:
        label = "Source-add ledger"
    elif "forensic_workbench_latest_source_import" in lower:
        label = "Latest source-add receipt"
    elif "forensic_workbench_source_edits" in lower:
        label = "Source-edit ledger"
    elif "forensic_workbench_latest_source_edit" in lower:
        label = "Latest source-edit receipt"
    elif "forensic_workbench_source_actions" in lower:
        label = "File-check ledger"
    elif "forensic_workbench_latest_source_action" in lower:
        label = "Latest file-check receipt"
    elif "forensic_workbench_case_file_" in lower:
        label = "Project file"
    elif "forensic_workbench_case_files" in lower:
        label = "Project-file ledger"
    elif "forensic_workbench_latest_case_file_write" in lower:
        label = "Latest project-file receipt"
    elif path.endswith("/workspace"):
        label = "Workspace folder"
    elif path.endswith("/raw"):
        label = "Source folder"
    elif path.startswith("projects/") and "/" not in path[len("projects/") :]:
        label = "Project folder"
    else:
        label = "Project file path"
    return {"label": label, "path_template": path}


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


def tail_display_text(value: str, *, max_chars: int = 4000) -> str:
    return display_text(tail_text(value, max_chars=max_chars))


def text_lines(value: Any, *, limit: int = 20) -> list[str]:
    if isinstance(value, list):
        raw = value
    else:
        raw = str(value or "").splitlines()
    return [str(item).strip() for item in raw if str(item).strip()][:limit]


def display_text_lines(value: Any, *, limit: int = 20) -> list[str]:
    return [display_text(item) for item in text_lines(value, limit=limit)]


def report_issue_text(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("reason") or value.get("label") or value.get("id") or "").strip()
    return str(value or "").strip()


def report_support_issues(payload: dict[str, Any], binding: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    raw_blockers = payload.get("blockers") or []
    raw_status_reasons = payload.get("status_reasons") or []
    for index, raw in enumerate(raw_blockers or raw_status_reasons):
        text = report_issue_text(raw)
        if not text:
            continue
        issue_id = raw.get("id") if isinstance(raw, dict) else f"report_issue_{index + 1}"
        status = raw.get("status") if isinstance(raw, dict) else "needs_support"
        issues.append(
            {
                "id": str(issue_id or f"report_issue_{index + 1}"),
                "status": str(status or "needs_support"),
                "display_status": display_status(status or "needs_support"),
                "reason": text,
                "display_reason": display_status(text),
            }
        )
    if binding.get("status") == "unbound" and binding.get("reason"):
        binding_reason = str(binding.get("reason") or "")
        if not any(issue.get("reason") == binding_reason for issue in issues):
            issues.append(
                {
                    "id": "synthesis_input_binding",
                    "status": "unbound",
                    "display_status": display_status("unbound"),
                    "reason": binding_reason,
                    "display_reason": display_status(binding_reason),
                }
            )
    return issues


def report_workflow_detail(report: dict[str, Any]) -> str:
    support_issues = report.get("support_issues") if isinstance(report.get("support_issues"), list) else []
    for issue in support_issues:
        if not isinstance(issue, dict):
            continue
        reason = str(issue.get("display_reason") or issue.get("reason") or "").strip()
        if reason:
            return display_guidance_text(reason)
    display_reasons = report.get("display_status_reasons") if isinstance(report.get("display_status_reasons"), list) else []
    for reason in display_reasons:
        text = str(reason or "").strip()
        if text:
            return display_guidance_text(text)
    reasons = report.get("status_reasons") if isinstance(report.get("status_reasons"), list) else []
    for reason in reasons:
        text = str(reason or "").strip()
        if text:
            return display_status(text)
    status = str(report.get("status") or "")
    return display_status(status) if status else "report readiness not loaded"


def report_contract_blockers(report_path: str) -> list[Any]:
    if not report_path:
        return []
    try:
        path = (snapshot.REPO / report_path).resolve()
        path.relative_to(snapshot.REPO.resolve())
        payload = read_json_object(path, "report support contract")
    except (OSError, ValueError, json.JSONDecodeError):
        return []
    blockers = payload.get("blockers")
    return blockers if isinstance(blockers, list) else []


def receipt_matches_case(row: dict[str, Any], *, project: str, intake: str | None = None) -> bool:
    if row.get("project") and row.get("project") != project:
        return False
    intake_value = str(intake or "").strip()
    if not intake_value:
        return True
    row_case_key = str(row.get("project_key") or row.get("case_key") or "").strip()
    if row_case_key:
        return row_case_key == case_key(project, intake_value)
    row_intake = str(row.get("intake") or "").strip()
    if row_intake:
        return row_intake == intake_value
    return True


def receipt_history_payload(*, project: str, limit: int = 12, intake: str | None = None) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    limit = max(1, min(limit, 50))
    workspace = snapshot.REPO / "projects" / project / "workspace"
    ledgers = {
        "review": workspace / "forensic_workbench_reviews.jsonl",
        "row_action": workspace / "forensic_workbench_row_actions.jsonl",
        "intake_edit": workspace / "forensic_workbench_intake_edits.jsonl",
        "source_import": workspace / "forensic_workbench_source_imports.jsonl",
        "source_edit": workspace / "forensic_workbench_source_edits.jsonl",
        "source_action": workspace / "forensic_workbench_source_actions.jsonl",
        "case_file": workspace / "forensic_workbench_case_files.jsonl",
    }
    paths = {kind: repo_rel(path) for kind, path in ledgers.items()}
    paths["next_step"] = paths["row_action"]
    paths["project_check"] = paths["row_action"]
    paths["item_action"] = paths["row_action"]
    receipts: list[dict[str, Any]] = []
    for kind, path in ledgers.items():
        receipts.extend(read_receipt_ledger(path, kind=kind))
    total_receipt_count = len(receipts)
    receipts = [row for row in receipts if receipt_matches_case(row, project=project, intake=intake)]
    receipts.sort(key=lambda row: (str(row.get("applied_at") or ""), str(row.get("kind") or ""), int(row.get("line") or 0)), reverse=True)
    return {
        "schema": RECEIPT_HISTORY_SCHEMA,
        "ok": True,
        "served_from": "local_api",
        "project": project,
        "intake": str(intake or ""),
        "limit": limit,
        "receipt_count": len(receipts),
        "total_receipt_count": total_receipt_count,
        "receipts": receipts[:limit],
        "paths": paths,
    }


def apply_intake_edit(*, project: str, intake: str | None, raw_patch: Any, rubric: str | None = None) -> dict[str, Any]:
    path = project_intake_path(project, intake, allow_examples=False)
    rubric = rubric or project
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
    receipt = add_case_context(
        {
            "schema": INTAKE_EDIT_SCHEMA,
            "applied_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "project": project,
            "intake_path": intake_rel,
            "updated_fields": sorted(changed_patch),
            "before_sha256": hashlib.sha256(before_bytes).hexdigest(),
            "after_sha256": hashlib.sha256(after_bytes).hexdigest(),
            "before_values": before_values,
            "after_values": {key: payload.get(key) for key in changed_patch},
        },
        project=project,
        rubric=rubric,
        intake=intake_rel,
    )
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
        "write_boundary": write_boundary_payload(
            writes_project_files=True,
            write_paths=[intake_rel, repo_rel(ledger_path), repo_rel(latest_path)],
            receipt_path=repo_rel(ledger_path),
            latest_path=repo_rel(latest_path),
        ),
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
    payload["ok"] = True
    payload["served_from"] = "local_api"
    return payload


def review_payload_from_request(request: dict[str, Any]) -> dict[str, Any]:
    project = str(request.get("project") or "")
    rubric = str(request.get("rubric") or "") or None
    intake = str(request.get("intake") or "") or None
    row = str(request.get("project_check_slug") or request.get("item_slug") or request.get("row_slug") or "")
    review_file = request.get("review_file")
    if not isinstance(review_file, dict):
        raise ValueError("review_file must be a JSON object")
    review_errors = review.validate_review_file(review_file, project=project, row=row, intake=intake)
    if review_errors:
        raise ValueError("invalid review file: " + "; ".join(review_errors))
    review_file = live_project_check_payload(
        live_row_payload_with_case(review_file, project=project, rubric=rubric, intake=intake),
        slug=row,
    )
    review_file_path, _review_file_bytes = persist_live_row_payload(
        project=project,
        row=row,
        kind="review",
        payload=review_file,
    )
    review_result = review.apply_review_payload(
        review_file,
        project=project,
        row=row,
        review_file_path=review_file_path,
        intake=intake,
    )
    response = {
        "ok": True,
        "review": review_result,
        "endpoint": "/api/review",
        "project_check_label": str(review_file.get("project_check_label") or review_file.get("item_label") or review_file.get("row") or ""),
        "project_check_slug": str(review_file.get("project_check_slug") or review_file.get("item_slug") or row),
        "item_slug": row,
        "row_slug": row,
        "write_boundary": write_boundary_payload(
            writes_project_files=True,
            write_paths=[
                review_file_path,
                str(review_result.get("ledger") or ""),
                str(review_result.get("latest") or ""),
            ],
            receipt_path=str(review_result.get("ledger") or ""),
            latest_path=str(review_result.get("latest") or ""),
        ),
        "snapshot": None,
    }
    try:
        response["snapshot"] = snapshot_payload_for_project(project=project, rubric=rubric, intake=intake)
    except SystemExit as exc:
        response["snapshot_error"] = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - receipt write already succeeded.
        response["snapshot_error"] = display_text(exc)
    return response


def item_action_payload_from_request(request: dict[str, Any]) -> dict[str, Any]:
    project = str(request.get("project") or "")
    rubric = str(request.get("rubric") or "") or None
    intake = str(request.get("intake") or "") or None
    row = str(request.get("project_check_slug") or request.get("item_slug") or request.get("row_slug") or "")
    action_file = request.get("action_file")
    if not isinstance(action_file, dict):
        raise ValueError("action_file must be a JSON object")
    action_errors = review.validate_action_file(action_file, project=project, row=row, intake=intake)
    if action_errors:
        raise ValueError("invalid item action file: " + "; ".join(action_errors))
    action_file = live_project_check_payload(
        live_row_payload_with_case(action_file, project=project, rubric=rubric, intake=intake),
        slug=row,
    )
    action_file_path, _action_file_bytes = persist_live_row_payload(
        project=project,
        row=row,
        kind="action",
        payload=action_file,
    )
    action_result = review.apply_action_payload(
        action_file,
        project=project,
        row=row,
        action_file_path=action_file_path,
        intake=intake,
    )
    response = {
        "ok": True,
        "action": action_result,
        "endpoint": "/api/next-step",
        "project_check_label": str(action_file.get("project_check_label") or action_file.get("item_label") or action_file.get("row") or ""),
        "project_check_slug": str(action_file.get("project_check_slug") or action_file.get("item_slug") or row),
        "item_slug": row,
        "row_slug": row,
        "write_boundary": write_boundary_payload(
            writes_project_files=True,
            write_paths=[
                action_file_path,
                str(action_result.get("ledger") or ""),
                str(action_result.get("latest") or ""),
            ],
            receipt_path=str(action_result.get("ledger") or ""),
            latest_path=str(action_result.get("latest") or ""),
        ),
        "snapshot": None,
    }
    try:
        response["snapshot"] = snapshot_payload_for_project(project=project, rubric=rubric, intake=intake)
    except SystemExit as exc:
        response["snapshot_error"] = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - receipt write already succeeded.
        response["snapshot_error"] = display_text(exc)
    return response


def report_contract_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    if intake:
        project_intake_path(project, intake, allow_examples=True)
    renderer = renderer or snapshot.DEFAULT_RENDERER
    payload, command = snapshot.collect_report_contract(project, renderer)
    binding = payload.get("synthesis_input_binding") or {}
    report_path = snapshot.rel(payload.get("report_support_contract"))
    support_payload = {**payload, "blockers": report_contract_blockers(report_path) or payload.get("blockers") or []}
    support_issues = report_support_issues(support_payload, binding)
    reasons = [str(issue.get("reason") or "") for issue in support_issues if issue.get("reason")]
    status = payload.get("status") or "unknown"
    binding_status = binding.get("status") or "unknown"
    return {
        "schema": REPORT_CONTRACT_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "project_key": case_key(project, intake),
        "case_key": case_key(project, intake),
        "report_scope": "project_report_support",
        "intake_scoped_command": False,
        "renderer": renderer,
        "command": command,
        "ok": bool(payload.get("ok")),
        "status": status,
        "display_status": display_status(status),
        "status_reasons": reasons,
        "display_status_reasons": [display_status(reason) for reason in reasons],
        "support_issues": support_issues,
        "report_support_contract": report_path,
        "backing_files": [
            {"label": "Report contract", "path": report_path}
        ] if report_path else [],
        "synthesis_input_binding": {
            "schema": binding.get("schema"),
            "ok": bool(binding.get("ok")),
            "status": binding_status,
            "display_status": display_status(binding_status),
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
    readiness_checks = [
        {
            "surface": row.get("surface"),
            "display_surface": display_surface(row.get("surface")),
            "status": row.get("status"),
            "display_status": display_status(row.get("status")),
            "blocking": bool(row.get("blocking")),
            "next_command": row.get("next_command"),
            "count": row.get("count"),
            "receipt_count": row.get("receipt_count"),
        }
        for row in trace.get("carrier_chain", [])
        if isinstance(row, dict)
    ]
    graph_summaries = [
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
    ]
    preflight_receipt = trace.get("loop_admission") or {}
    readiness_status = trace.get("readiness_canonical") or trace.get("readiness") or "unknown"
    kernel_status = kernel.get("status") or "unknown"
    kernel_readiness = kernel.get("readiness_canonical") or kernel.get("readiness") or "unknown"
    plan_status = plan.get("status") or "unknown"
    return {
        "schema": "ztare-forensic-workbench-trace-v1",
        "ok": True,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "trace_command": trace_command,
        "readiness": readiness_status,
        "display_readiness": display_status(readiness_status),
        "blocking_missing": trace.get("blocking_missing") or trace.get("missing") or [],
        "next_commands": trace.get("next_commands") or [],
        "readiness_checks": readiness_checks,
        "carrier_chain": readiness_checks,
        "kernel_entry": {
            "schema": kernel.get("schema"),
            "status": kernel_status,
            "display_status": display_status(kernel_status),
            "can_enter_kernel": kernel.get("can_enter_kernel"),
            "readiness": kernel_readiness,
            "display_readiness": display_status(kernel_readiness),
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
            "status": plan_status,
            "display_status": display_status(plan_status),
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
                    "display_status": display_status(row.get("status")),
                    "model_calls": bool(row.get("model_calls")),
                    "command": row.get("command"),
                    "description": row.get("description"),
                }
                for row in plan.get("dependency_order", [])
                if isinstance(row, dict)
            ],
        },
        "preflight_receipt": preflight_receipt,
        "loop_admission": preflight_receipt,
        "recent_loop": trace.get("recent_loop") or {},
        "surfaces": {
            "source_preflight_status": surfaces.get("source_preflight_status"),
            "display_source_preflight_status": display_status(surfaces.get("source_preflight_status")),
            "raw_file_count": surfaces.get("raw_file_count"),
            "source_index_status": readiness.get("source_index_status"),
            "display_source_index_status": display_status(readiness.get("source_index_status")),
            "evidence_status": readiness.get("status"),
            "display_evidence_status": display_status(readiness.get("status")),
            "output_binding_status": readiness.get("output_binding_status"),
            "display_output_binding_status": display_status(readiness.get("output_binding_status")),
            "replay_status": readiness.get("replay_status"),
            "display_replay_status": display_status(readiness.get("replay_status")),
            "source_index_receipt_path": source_receipt.get("path"),
            "compile_provenance_path": snapshot.rel(surfaces.get("compile_provenance_path")),
        },
        "graph_summaries": graph_summaries,
        "graph_carriers": graph_summaries,
        "prediction_summary": {
            "available": bool(prediction.get("available")),
            "status": prediction.get("status"),
            "row_count": prediction.get("row_count"),
            "scoreable_count": prediction.get("scoreable_count"),
            "measurement_policy": prediction.get("measurement_policy"),
        },
    }


def action_intelligence_recommendations(limit: int = 6) -> dict[str, Any]:
    path = snapshot.REPO / ACTION_INTELLIGENCE_STATE_DIR / "shadow_recommendations.json"
    if not path.exists():
        return {"generated_at": None, "counts": {}, "recommendations": [], "source_path": snapshot.rel(path)}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("shadow recommendations read model must be a JSON object")
    rows = payload.get("recommendations") or []
    if not isinstance(rows, list):
        rows = []
    recommendations = []
    for row in rows[:limit]:
        if not isinstance(row, dict):
            continue
        externality = row.get("externality_checks") or {}
        gp230 = row.get("gp230") or {}
        recommendations.append(
            {
                "recommendation_id": row.get("recommendation_id"),
                "decision_id": row.get("decision_id"),
                "domain": row.get("domain"),
                "display_domain": display_action_label(row.get("domain")),
                "recommended_action": row.get("recommended_action"),
                "display_recommended_action": display_action_label(row.get("recommended_action")),
                "confidence": row.get("confidence"),
                "display_confidence": display_action_label(row.get("confidence")),
                "execution_authority": row.get("execution_authority"),
                "display_execution_authority": display_action_label(row.get("execution_authority")),
                "rationale": row.get("rationale"),
                "display_rationale": display_guidance_text(row.get("rationale")),
                "blocking_checks": row.get("blocking_checks") or [],
                "display_blocking_checks": [display_action_label(item) for item in row.get("blocking_checks") or []],
                "evidence_refs": row.get("evidence_refs") or [],
                "display_evidence_refs": [display_evidence_ref(item) for item in row.get("evidence_refs") or []],
                "source": row.get("source"),
                "display_source": display_action_label(row.get("source")),
                "p_success": gp230.get("p_success"),
                "expected_cost_agent_minutes": gp230.get("expected_cost_agent_minutes"),
                "effective_n": gp230.get("effective_n"),
                "goodhart_risk": externality.get("goodhart_risk"),
                "sample_size": externality.get("sample_size"),
            }
        )
    return {
        "generated_at": payload.get("generated_at"),
        "counts": payload.get("counts") or {},
        "recommendations": recommendations,
        "source_path": snapshot.rel(path),
    }


def action_intelligence_health_read_model() -> dict[str, Any]:
    path = snapshot.REPO / ACTION_INTELLIGENCE_STATE_DIR / "source_health.json"
    if not path.exists():
        return {
            "generated_at": None,
            "counts": {},
            "issues": [],
            "source_paths": {},
            "source_path": snapshot.rel(path),
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("source health read model must be a JSON object")
    return {
        "generated_at": payload.get("generated_at"),
        "counts": payload.get("counts") or {},
        "issues": payload.get("issues") or [],
        "source_paths": payload.get("source_paths") or {},
        "source_path": snapshot.rel(path),
    }


def kernel_health_from_trace(*, project: str, rubric: str, intake: str) -> dict[str, Any]:
    recompute_command = (
        "make autoresearch-kernel-health "
        f"PROJECT={project} RUBRIC={rubric} INTAKE={intake} JSON=1"
    )
    try:
        trace = trace_payload_for_project(project=project, rubric=rubric, intake=intake)
    except Exception as exc:  # noqa: BLE001 - health is advisory in the workbench.
        return {
            "summary": {
                "overall_status": "attention",
                "component_status": "attention",
                "component_count": 1,
                "component_counts": {"attention": 1, "ok": 0},
                "source": "trace_read_model",
                "recompute_command": recompute_command,
            },
            "attention_components": [
                {
                    "component": "run_trace",
                    "status": "attention",
                    "action": f"Trace read failed: {display_text(exc)}",
                    "next_command": recompute_command,
                }
            ],
            "component_count": 1,
        }

    attention_components: list[dict[str, Any]] = []
    readiness_checks = [row for row in trace.get("readiness_checks") or [] if isinstance(row, dict)]
    for row in readiness_checks:
        if not row.get("blocking"):
            continue
        attention_components.append(
            {
                "component": row.get("surface") or "readiness",
                "status": row.get("status") or "attention",
                "action": "Inspect readiness blocker.",
                "next_command": row.get("next_command") or recompute_command,
            }
        )

    recent_loop = trace.get("recent_loop") if isinstance(trace.get("recent_loop"), dict) else {}
    pending_action = str(recent_loop.get("latest_pending_loop_action") or "")
    latest_rationale = str(recent_loop.get("latest_information_yield_rationale") or "")
    if pending_action or "failed" in latest_rationale.lower():
        attention_components.append(
            {
                "component": "project_trace",
                "status": "attention",
                "action": latest_rationale or f"Inspect pending run action: {pending_action}",
                "next_command": trace.get("trace_command") or recompute_command,
            }
        )

    status = "attention" if attention_components else "ok"
    component_count = max(len(readiness_checks), 1)
    return {
        "summary": {
            "overall_status": status,
            "component_status": status,
            "component_count": component_count,
            "component_counts": {
                "attention": len(attention_components),
                "ok": max(component_count - len(attention_components), 0),
            },
            "source": "trace_read_model",
            "recompute_command": recompute_command,
        },
        "attention_components": attention_components,
        "component_count": component_count,
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
    kernel_payload = kernel_health_from_trace(project=project, rubric=rubric, intake=intake)
    action_payload = action_intelligence_health_read_model()
    action_source_paths = dict(action_payload.get("source_paths") or {})
    if action_payload.get("source_path"):
        action_source_paths.setdefault("source_health", action_payload.get("source_path"))
    recommendation_payload = action_intelligence_recommendations()

    attention_components = [
        {
            "component": row.get("component"),
            "display_component": display_surface(row.get("component")),
            "status": row.get("status"),
            "display_status": display_status(row.get("status")),
            "action": row.get("action"),
            "display_action": display_guidance_text(row.get("action")),
            "next_command": row.get("next_command"),
        }
        for row in kernel_payload.get("attention_components", [])
    ]
    action_issues = [
        {
            "issue_id": issue.get("issue_id"),
            "issue_type": issue.get("issue_type"),
            "display_issue_type": display_action_label(issue.get("issue_type")),
            "severity": issue.get("severity"),
            "display_severity": display_action_label(issue.get("severity")),
            "scope": issue.get("scope"),
            "display_scope": display_action_label(issue.get("scope")),
            "domain": issue.get("domain"),
            "display_domain": display_action_label(issue.get("domain")),
            "affected_domains": issue.get("affected_domains") or [],
            "display_affected_domains": [display_action_label(item) for item in issue.get("affected_domains") or []],
            "blocking_rule": issue.get("blocking_rule"),
            "display_blocking_rule": display_guidance_text(issue.get("blocking_rule")),
            "denominator": issue.get("denominator"),
            "display_denominator": display_guidance_text(issue.get("denominator")),
            "observed_count": issue.get("observed_count"),
            "expected_count": issue.get("expected_count"),
            "freshness_window_days": issue.get("freshness_window_days"),
            "evidence_refs": issue.get("evidence_refs") or [],
            "display_evidence_refs": [display_evidence_ref(item) for item in issue.get("evidence_refs") or []],
            "recommended_action": issue.get("recommended_action"),
            "display_recommended_action": display_action_label(issue.get("recommended_action")),
        }
        for issue in action_payload.get("issues", [])
    ]
    action_guidance = {
        "counts": action_payload.get("counts") or {},
        "issues": action_issues,
        "recommendations": recommendation_payload.get("recommendations") or [],
        "recommendation_counts": recommendation_payload.get("counts") or {},
        "recommendations_generated_at": recommendation_payload.get("generated_at"),
        "recommendations_source_path": recommendation_payload.get("source_path"),
        "source_paths": action_source_paths,
    }
    return {
        "schema": "ztare-forensic-workbench-health-v1",
        "ok": True,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "kernel": {
            "summary": kernel_payload.get("summary") or {},
            "attention_components": attention_components,
            "component_count": int(kernel_payload.get("component_count") or 0),
        },
        "action_guidance": action_guidance,
        "action_intelligence": action_guidance,
    }


def command_result_payload(proc: Any) -> dict[str, Any]:
    parsed_output: dict[str, Any] = {}
    try:
        parsed_output = snapshot.extract_last_json_object(proc.stdout)
    except Exception:
        parsed_output = {}
    return {
        "returncode": proc.returncode,
        "accepted": proc.returncode == 0,
        "stdout_tail": tail_display_text(proc.stdout),
        "stderr_tail": tail_display_text(proc.stderr),
        "parsed_output": display_data(parsed_output),
    }


def source_check_after_write(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
) -> dict[str, Any]:
    try:
        return source_action_payload_for_project(
            project=project,
            action="source_check",
            rubric=rubric,
            intake=intake,
            renderer=renderer,
        )
    except SystemExit as exc:
        error = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - the source write already succeeded.
        error = display_text(exc)
    return {
        "schema": SOURCE_ACTION_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric or project,
        "intake": intake or "",
        "action": "source_check",
        "label": SOURCE_ACTIONS["source_check"]["label"],
        "writes": False,
        "command": SOURCE_ACTIONS["source_check"]["display"].format(project=project),
        "returncode": None,
        "accepted": False,
        "error": error,
        "stdout_tail": "",
        "stderr_tail": "",
        "parsed_output": {},
        "trace": None,
        "snapshot": None,
    }


def import_source_payload(
    *,
    project: str,
    filename: str,
    source_type: str,
    body: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    project_intake_path(project, intake, allow_examples=True)
    filename = str(filename or "").strip()
    if not SOURCE_IMPORT_FILENAME_RE.fullmatch(filename):
        raise ValueError("filename must be a flat .md or .txt name using letters, numbers, dot, dash, or underscore")
    source_type = str(source_type or "").strip()
    if source_type not in SOURCE_IMPORT_TYPES:
        raise ValueError(f"source_type must be one of: {', '.join(sorted(SOURCE_IMPORT_TYPES))}")
    body = str(body or "")
    if not body.strip():
        raise ValueError("source body is required")
    project_root = snapshot.REPO / "projects" / project
    raw_dir = project_root / "raw"
    workspace = project_root / "workspace"
    if not raw_dir.exists():
        raise FileNotFoundError(f"source file directory does not exist: {repo_rel(raw_dir)}")
    source_path = (raw_dir / filename).resolve()
    if not path_under(source_path, raw_dir):
        raise ValueError("source path escapes the project source file directory")
    if source_path.exists():
        raise ValueError(f"source file already exists: {repo_rel(source_path)}")
    source_text = (
        "---\n"
        f"source_type: {source_type}\n"
        "---\n\n"
        f"{body}\n"
    )
    source_path.write_text(source_text, encoding="utf-8")
    source_type_map_path = raw_dir / "source_type_map.json"
    source_type_map: dict[str, Any] = {}
    if source_type_map_path.exists():
        source_type_map = read_json_object(source_type_map_path, repo_rel(source_type_map_path))
    source_type_map[filename] = source_type
    source_type_map_path.write_text(json.dumps(source_type_map, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sha256 = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    receipt = add_case_context(
        {
            "schema": SOURCE_IMPORT_SCHEMA,
            "applied_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "project": project,
            "source_path": repo_rel(source_path),
            "source_type": source_type,
            "chars": len(body),
            "sha256": sha256,
            "source_type_map": repo_rel(source_type_map_path),
        },
        project=project,
        rubric=rubric,
        intake=intake,
    )
    receipt_path = workspace / "forensic_workbench_source_imports.jsonl"
    latest_path = workspace / "forensic_workbench_latest_source_import.json"
    append_jsonl(receipt_path, receipt)
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    source_check = source_check_after_write(
        project=project,
        rubric=rubric,
        intake=intake,
        renderer=renderer,
    )
    payload: dict[str, Any] = {
        "schema": SOURCE_IMPORT_SCHEMA,
        "served_from": "local_api",
        "ok": True,
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "source_path": repo_rel(source_path),
        "source_type": source_type,
        "source_type_map": repo_rel(source_type_map_path),
        "receipt": receipt,
        "receipt_path": repo_rel(receipt_path),
        "latest": repo_rel(latest_path),
        "write_boundary": write_boundary_payload(
            writes_project_files=True,
            write_paths=[
                repo_rel(source_path),
                repo_rel(source_type_map_path),
                repo_rel(receipt_path),
                repo_rel(latest_path),
            ],
            receipt_path=repo_rel(receipt_path),
            latest_path=repo_rel(latest_path),
        ),
        "source_check": source_check,
        "snapshot": source_check.get("snapshot"),
        "trace": source_check.get("trace"),
    }
    return payload


def source_raw_dir(project: str) -> Path:
    project = snapshot.validate_project_slug(project)
    return snapshot.REPO / "projects" / project / "raw"


def validate_raw_source_relative(value: str) -> str:
    value = str(value or "").strip().replace("\\", "/")
    unsafe_reason = unsafe_local_ref_reason(value)
    if unsafe_reason is not None:
        raise ValueError(f"invalid source file path: {unsafe_reason}")
    path = PurePosixPath(value)
    if path.name == "source_type_map.json":
        raise ValueError("source_type_map.json is edited by the workbench, not as a source")
    if path.suffix.lower() not in {".md", ".txt"}:
        raise ValueError("source file path must end in .md or .txt")
    return path.as_posix()


def raw_source_path(project: str, relative_path: str) -> Path:
    raw_dir = source_raw_dir(project)
    relative_path = validate_raw_source_relative(relative_path)
    path = (raw_dir / relative_path).resolve()
    if not path_under(path, raw_dir):
        raise ValueError("source file path escapes the project source file directory")
    return path


def read_source_type_map(raw_dir: Path) -> dict[str, Any]:
    path = raw_dir / "source_type_map.json"
    if not path.exists():
        return {}
    return read_json_object(path, repo_rel(path))


def write_source_type_map(raw_dir: Path, payload: dict[str, Any]) -> None:
    path = raw_dir / "source_type_map.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def split_source_frontmatter(text: str, *, fallback_source_type: str = "untyped") -> tuple[str, str]:
    source_type = fallback_source_type if fallback_source_type in SOURCE_IMPORT_TYPES else "untyped"
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            frontmatter = text[4:end].splitlines()
            for line in frontmatter:
                key, sep, value = line.partition(":")
                if sep and key.strip() == "source_type" and value.strip() in SOURCE_IMPORT_TYPES:
                    source_type = value.strip()
            body = text[end + len("\n---\n") :]
            if body.startswith("\n"):
                body = body[1:]
            if body.endswith("\n"):
                body = body[:-1]
            return source_type, body
    if text.endswith("\n"):
        text = text[:-1]
    return source_type, text


def source_list_payload(*, project: str) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    command = [
        SERVER_PYTHON,
        "-m",
        "src.ztare.cli",
        "project",
        "source-check",
        "--project",
        project,
        "--json",
        "--no-fail",
    ]
    proc = snapshot.run(command, timeout=90)
    parsed = snapshot.extract_last_json_object(proc.stdout) if proc.stdout.strip() else {}
    raw_dir = source_raw_dir(project)
    sources = display_data(parsed.get("sources")) if isinstance(parsed.get("sources"), list) else []
    source_type_counts: dict[str, int] = {}
    invalid_source_type_count = 0
    for row in sources:
        if not isinstance(row, dict):
            continue
        source_type = str(row.get("source_type") or "untyped")
        source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1
        if row.get("invalid_source_type_declaration"):
            invalid_source_type_count += 1
    return {
        "schema": SOURCE_LIST_SCHEMA,
        "ok": True,
        "served_from": "local_api",
        "project": project,
        "raw_dir": repo_rel(raw_dir) if raw_dir.exists() else f"projects/{project}/raw",
        "source_count": len(sources),
        "source_type_counts": source_type_counts,
        "untyped_source_count": source_type_counts.get("untyped", 0),
        "invalid_source_type_count": invalid_source_type_count,
        "command": f"ztare project source-check --project {project} --json --no-fail",
        "returncode": proc.returncode,
        "accepted": proc.returncode == 0,
        "stdout_tail": tail_display_text(proc.stdout),
        "stderr_tail": tail_display_text(proc.stderr),
        "source_check": display_data(parsed),
        "sources": sources,
    }


def source_file_payload(*, project: str, relative_path: str) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    path = raw_source_path(project, relative_path)
    if not path.exists():
        raise FileNotFoundError(f"source file does not exist: {repo_rel(path)}")
    raw_dir = source_raw_dir(project)
    type_map = read_source_type_map(raw_dir)
    relative_path = str(path.relative_to(raw_dir.resolve()))
    fallback_type = str(type_map.get(relative_path) or type_map.get(path.name) or "untyped")
    source_type, body = split_source_frontmatter(path.read_text(encoding="utf-8"), fallback_source_type=fallback_type)
    return {
        "schema": SOURCE_FILE_SCHEMA,
        "ok": True,
        "served_from": "local_api",
        "project": project,
        "relative_raw_path": relative_path,
        "source_path": repo_rel(path),
        "source_type": source_type,
        "body": body,
    }


def edit_source_payload(
    *,
    project: str,
    relative_path: str,
    source_type: str,
    body: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    project_intake_path(project, intake, allow_examples=True)
    if source_type not in SOURCE_IMPORT_TYPES:
        raise ValueError(f"source_type must be one of: {', '.join(sorted(SOURCE_IMPORT_TYPES))}")
    body = str(body or "")
    if not body.strip():
        raise ValueError("source body is required")
    path = raw_source_path(project, relative_path)
    if not path.exists():
        raise FileNotFoundError(f"source file does not exist: {repo_rel(path)}")
    raw_dir = source_raw_dir(project)
    relative_path = str(path.relative_to(raw_dir.resolve()))
    before_text = path.read_text(encoding="utf-8")
    existing_type_map = read_source_type_map(raw_dir)
    fallback_type = str(existing_type_map.get(relative_path) or existing_type_map.get(path.name) or "untyped")
    existing_source_type, existing_body = split_source_frontmatter(before_text, fallback_source_type=fallback_type)
    if existing_source_type == source_type and existing_body == body:
        raise ValueError("source edit has no changed fields")
    source_text = (
        "---\n"
        f"source_type: {source_type}\n"
        "---\n\n"
        f"{body}\n"
    )
    path.write_text(source_text, encoding="utf-8")
    source_type_map = dict(existing_type_map)
    source_type_map[relative_path] = source_type
    write_source_type_map(raw_dir, source_type_map)
    sha256 = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    workspace = snapshot.REPO / "projects" / project / "workspace"
    receipt = add_case_context(
        {
            "schema": SOURCE_EDIT_SCHEMA,
            "applied_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "project": project,
            "source_path": repo_rel(path),
            "relative_raw_path": relative_path,
            "source_type": source_type,
            "chars": len(body),
            "sha256": sha256,
            "source_type_map": repo_rel(raw_dir / "source_type_map.json"),
        },
        project=project,
        rubric=rubric,
        intake=intake,
    )
    receipt_path = workspace / "forensic_workbench_source_edits.jsonl"
    latest_path = workspace / "forensic_workbench_latest_source_edit.json"
    append_jsonl(receipt_path, receipt)
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    source_check = source_check_after_write(
        project=project,
        rubric=rubric,
        intake=intake,
        renderer=renderer,
    )
    return {
        "schema": SOURCE_EDIT_SCHEMA,
        "served_from": "local_api",
        "ok": True,
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "source_path": repo_rel(path),
        "relative_raw_path": relative_path,
        "source_type": source_type,
        "receipt": receipt,
        "receipt_path": repo_rel(receipt_path),
        "latest": repo_rel(latest_path),
        "write_boundary": write_boundary_payload(
            writes_project_files=True,
            write_paths=[
                repo_rel(path),
                repo_rel(raw_dir / "source_type_map.json"),
                repo_rel(receipt_path),
                repo_rel(latest_path),
            ],
            receipt_path=repo_rel(receipt_path),
            latest_path=repo_rel(latest_path),
        ),
        "source_check": source_check,
        "snapshot": source_check.get("snapshot"),
        "trace": source_check.get("trace"),
    }


def create_project_payload(
    *,
    project: str,
    rubric: str | None = None,
    task: str = "",
    bounded_claim: str = "",
    next_falsifier: str = "",
    notes: str = "",
    source_refs: Any = None,
    evidence_refs: Any = None,
    non_claims: Any = None,
    renderer: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = snapshot.validate_project_slug(rubric or project)
    task = str(task or "").strip()
    bounded_claim = str(bounded_claim or "").strip()
    next_falsifier = str(next_falsifier or "").strip()
    notes = str(notes or "").strip()
    if not task:
        raise ValueError("task is required")
    if not bounded_claim:
        raise ValueError("bounded_claim is required")
    if not next_falsifier:
        raise ValueError("next_falsifier is required")
    project_root = snapshot.REPO / "projects" / project
    project_existed_before = project_root.exists()
    if project_existed_before and snapshot.discover_project_intakes(project):
        raise ValueError(f"project already has an intake: {project}")
    intake = f"projects/{project}/{project}_intake.json"
    expected_command = (
        "ztare autoresearch run "
        f"--project {project} --rubric {rubric} --intake {intake} --iters 1"
    )
    source_init_command = [
        SERVER_PYTHON,
        "-m",
        "src.ztare.cli",
        "project",
        "source-init",
        "--project",
        project,
        "--rubric",
        rubric,
        "--json",
    ]
    intake_command = [
        SERVER_PYTHON,
        "-m",
        "src.ztare.cli",
        "project",
        "intake",
        "create",
        "--path",
        intake,
        "--project",
        project,
        "--rubric",
        rubric,
        "--task",
        task,
        "--bounded-claim",
        bounded_claim,
        "--next-falsifier",
        next_falsifier,
        "--expected-command",
        expected_command,
        "--json",
    ]
    if notes:
        intake_command.extend(["--notes", notes])
    for ref in text_lines(source_refs):
        intake_command.extend(["--source-ref", ref])
    for ref in text_lines(evidence_refs):
        intake_command.extend(["--evidence-ref", ref])
    for item in text_lines(non_claims):
        intake_command.extend(["--non-claim", item])

    source_proc = snapshot.run(source_init_command, timeout=90)
    source_result = command_result_payload(source_proc)
    intake_result: dict[str, Any] | None = None
    if source_proc.returncode == 0:
        intake_proc = snapshot.run(intake_command, timeout=90)
        intake_result = {
            "command": (
                "ztare project intake create "
                f"--path {intake} --project {project} --rubric {rubric} "
                "--task <task> --bounded-claim <claim> --next-falsifier <falsifier> "
                "--expected-command <command> --json"
            ),
            **command_result_payload(intake_proc),
        }
    source_init_accepted = source_proc.returncode == 0
    intake_path_obj = snapshot.REPO / intake
    intake_create_accepted = bool(intake_result and intake_result["accepted"])
    intake_file_exists = intake_path_obj.exists()
    accepted = source_init_accepted and bool(intake_create_accepted or intake_file_exists)
    source_output = source_result.get("parsed_output") if isinstance(source_result.get("parsed_output"), dict) else {}
    source_write_paths = [
        str(path)
        for path in [
            *(source_output.get("created_dirs") or []),
            *(source_output.get("created_files") or []),
        ]
        if path
    ]
    if source_init_accepted and not source_write_paths and not project_existed_before:
        source_write_paths = [
            repo_rel(project_root),
            repo_rel(project_root / "raw"),
            repo_rel(project_root / "workspace"),
        ]
    write_paths = source_write_paths if source_init_accepted else []
    if accepted:
        write_paths.append(intake)
    payload: dict[str, Any] = {
        "schema": PROJECT_CREATE_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "created_mode": "add_intake" if project_existed_before else "create_project",
        "project_existed_before": project_existed_before,
        "ok": accepted,
        "accepted": accepted,
        "creation_complete": accepted,
        "source_init_accepted": source_init_accepted,
        "intake_create_accepted": intake_create_accepted,
        "intake_file_exists": intake_file_exists,
        "created_paths": write_paths,
        "write_boundary": write_boundary_payload(
            writes_project_files=bool(write_paths),
            write_paths=write_paths,
            read_only_actions=["preview", "copy"],
        ),
        "source_init": {
            "command": f"ztare project source-init --project {project} --rubric {rubric} --json",
            **source_result,
        },
        "intake_create": intake_result,
        "project_index": None,
        "snapshot": None,
    }
    if accepted:
        try:
            payload["project_index"] = project_index_payload()
        except Exception as exc:  # noqa: BLE001 - creation result should still be inspectable.
            payload["project_index_error"] = display_text(exc)
        try:
            payload["snapshot"] = snapshot_payload_for_project(
                project=project,
                rubric=rubric,
                intake=intake,
                renderer=renderer,
            )
        except Exception as exc:  # noqa: BLE001 - creation result should still be inspectable.
            payload["snapshot_error"] = display_text(exc)
    return payload


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
        SERVER_PYTHON,
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
        "ok": accepted,
        "stdout_tail": tail_display_text(proc.stdout),
        "stderr_tail": tail_display_text(proc.stderr),
        "write_boundary": write_boundary_payload(
            writes_project_files=accepted,
            write_paths=[preflight_telemetry_path(project)] if accepted else [],
            read_only_actions=["Copy command detail", "Inspect output"],
        ),
        "trace": None,
        "snapshot": None,
    }
    try:
        payload["trace"] = trace_payload_for_project(project=project, rubric=rubric, intake=intake)
        preflight_paths = preflight_write_paths(payload["trace"])
        payload["write_boundary"] = write_boundary_payload(
            writes_project_files=accepted and bool(preflight_paths),
            write_paths=preflight_paths if accepted else [],
            read_only_actions=["Copy command detail", "Inspect output"],
        )
    except SystemExit as exc:
        payload["trace_error"] = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - preflight result should still be inspectable.
        payload["trace_error"] = display_text(exc)
    try:
        payload["snapshot"] = snapshot_payload_for_project(
            project=project,
            rubric=rubric,
            intake=intake,
            renderer=renderer,
        )
    except SystemExit as exc:
        payload["snapshot_error"] = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - preflight result should still be inspectable.
        payload["snapshot_error"] = display_text(exc)
    return payload


def ztare_run_command_from_display(display_command: Any) -> list[str]:
    parts = shlex.split(str(display_command or ""))
    if len(parts) < 3 or parts[:3] != ["ztare", "autoresearch", "run"]:
        raise ValueError("run plan did not surface a bounded autoresearch command")
    return [SERVER_PYTHON, "-m", "src.ztare.cli", *parts[1:]]


def bounded_run_write_paths(project: str) -> list[str]:
    return [
        f"projects/{project}/workspace/iteration_telemetry.jsonl",
        f"projects/{project}/latest_eval_results.json",
        f"projects/{project}/eval_results.jsonl",
    ]


def bounded_run_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    project_intake_path(project, intake, allow_examples=True)
    trace_before = trace_payload_for_project(project=project, rubric=rubric, intake=intake)
    plan = trace_before.get("plan_preview") or {}
    kernel = trace_before.get("kernel_entry") or {}
    display_command = str(kernel.get("run_command") or plan.get("recommended_first_command") or "")
    plan_status = str(plan.get("status") or "")
    can_run = plan_status == "ready_for_bounded_run" and bool(kernel.get("can_enter_kernel"))
    write_boundary = write_boundary_payload(
        writes_project_files=bool(can_run and confirmed),
        write_paths=bounded_run_write_paths(project) if can_run and confirmed else [],
        read_only_actions=["Inspect run plan", "Copy command detail"],
    )
    confirmed_write_boundary = write_boundary_payload(
        writes_project_files=bool(can_run),
        write_paths=bounded_run_write_paths(project) if can_run else [],
        read_only_actions=["Inspect run plan", "Copy command detail"],
    )
    payload: dict[str, Any] = {
        "schema": BOUNDED_RUN_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "project_key": case_key(project, intake),
        "case_key": case_key(project, intake),
        "label": "Project run",
        "command": display_command,
        "plan_status": plan_status,
        "requires_confirmation": bool(can_run and not confirmed),
        "accepted": False,
        "returncode": None,
        "stdout_tail": "",
        "stderr_tail": "",
        "writes": False,
        "trace_before": trace_before,
        "trace": None,
        "run_history": None,
        "snapshot": None,
        "write_boundary": write_boundary,
        "confirmed_write_boundary": confirmed_write_boundary,
    }
    if not can_run:
        payload["ok"] = False
        payload["error"] = "Run plan is not ready for a project run. Run preflight first."
        return payload
    if not confirmed:
        payload["ok"] = True
        payload["status"] = "needs_confirmation"
        payload["display_status"] = "needs confirmation"
        payload["message"] = "Review the project run before starting model-backed work."
        return payload
    command = ztare_run_command_from_display(display_command)
    proc = snapshot.run(command, timeout=1800)
    payload.update(
        {
            "ok": proc.returncode == 0,
            "accepted": proc.returncode == 0,
            "returncode": proc.returncode,
            "writes": True,
            "stdout_tail": tail_display_text(proc.stdout),
            "stderr_tail": tail_display_text(proc.stderr),
        }
    )
    try:
        payload["trace"] = trace_payload_for_project(project=project, rubric=rubric, intake=intake)
    except SystemExit as exc:
        payload["trace_error"] = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - run output should still be inspectable.
        payload["trace_error"] = display_text(exc)
    try:
        payload["run_history"] = run_history_payload_for_project(project=project, rubric=rubric, intake=intake)
    except SystemExit as exc:
        payload["run_history_error"] = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - run output should still be inspectable.
        payload["run_history_error"] = display_text(exc)
    try:
        payload["snapshot"] = snapshot_payload_for_project(
            project=project,
            rubric=rubric,
            intake=intake,
            renderer=renderer,
        )
    except SystemExit as exc:
        payload["snapshot_error"] = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - run output should still be inspectable.
        payload["snapshot_error"] = display_text(exc)
    return payload


def file_sha256_for_display_path(value: Any) -> str:
    path_text = display_path(value)
    if not path_text:
        return ""
    path = Path(path_text)
    if not path.is_absolute():
        path = snapshot.REPO / path
    try:
        resolved = path.resolve()
        if not path_under(resolved, snapshot.REPO.resolve()) or not resolved.is_file():
            return ""
        return hashlib.sha256(resolved.read_bytes()).hexdigest()
    except (OSError, ValueError):
        return ""


def first_bound_artifact(receipt: dict[str, Any]) -> tuple[str, str]:
    artifacts = receipt.get("artifacts") or []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        artifact_path = display_path(artifact.get("path"))
        if artifact_path:
            return artifact_path, str(artifact.get("sha256") or "")
    return "", ""


def source_action_artifact_paths(parsed_output: dict[str, Any]) -> tuple[str, str, str, str]:
    nested_receipt = parsed_output.get("receipt") if isinstance(parsed_output.get("receipt"), dict) else {}
    bound_artifact_path, bound_artifact_sha256 = first_bound_artifact(nested_receipt)
    source_receipt_path = display_path(
        parsed_output.get("source_index_receipt")
        or parsed_output.get("receipt_path")
        or parsed_output.get("path")
    )
    source_path = display_path(
        parsed_output.get("source_index")
        or parsed_output.get("workspace_meta")
        or bound_artifact_path
        or parsed_output.get("provenance_path")
        or nested_receipt.get("provenance_path")
        or parsed_output.get("path")
    )
    source_sha256 = bound_artifact_sha256 or file_sha256_for_display_path(source_path)
    source_receipt_sha256 = file_sha256_for_display_path(source_receipt_path)
    return source_receipt_path, source_path, source_sha256, source_receipt_sha256


def source_action_payload_for_project(
    *,
    project: str,
    action: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    spec = SOURCE_ACTIONS.get(action)
    if spec is None:
        raise ValueError(f"unknown source action: {action}")
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    project_intake_path(project, intake, allow_examples=True)
    command_args = [part.format(project=project) for part in spec["args"]]
    command = [SERVER_PYTHON, "-m", "src.ztare.cli", *command_args]
    proc = snapshot.run(command, timeout=int(spec["timeout"]))
    parsed_output: dict[str, Any] = {}
    try:
        parsed_output = snapshot.extract_last_json_object(proc.stdout)
    except Exception:
        parsed_output = {}
    payload: dict[str, Any] = {
        "schema": SOURCE_ACTION_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "action": action,
        "label": str(spec["label"]),
        "writes": bool(spec["writes"]),
        "command": str(spec["display"]).format(project=project),
        "returncode": proc.returncode,
        "accepted": proc.returncode == 0,
        "ok": proc.returncode == 0,
        "stdout_tail": tail_display_text(proc.stdout),
        "stderr_tail": tail_display_text(proc.stderr),
        "parsed_output": display_data(parsed_output),
        "trace": None,
        "snapshot": None,
    }
    if spec["writes"]:
        source_receipt_path, source_path, source_sha256, source_receipt_sha256 = source_action_artifact_paths(parsed_output)
        workspace = snapshot.REPO / "projects" / project / "workspace"
        ledger_path = workspace / "forensic_workbench_source_actions.jsonl"
        latest_path = workspace / "forensic_workbench_latest_source_action.json"
        receipt = add_case_context(
            {
                "schema": SOURCE_ACTION_RECEIPT_SCHEMA,
                "applied_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "project": project,
                "action": action,
                "label": str(spec["label"]),
                "command": payload["command"],
                "returncode": proc.returncode,
                "accepted": proc.returncode == 0,
                "source_action_schema": SOURCE_ACTION_SCHEMA,
                "source_receipt_path": source_receipt_path,
                "source_receipt_sha256": source_receipt_sha256,
                "source_path": source_path,
                "source_sha256": source_sha256,
                "parsed_schema": str(parsed_output.get("schema") or ""),
                "parsed_status": str(parsed_output.get("status") or ""),
            },
            project=project,
            rubric=rubric,
            intake=intake,
        )
        append_jsonl(ledger_path, receipt)
        latest_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        payload.update(
            {
                "receipt_path": repo_rel(ledger_path),
                "latest": repo_rel(latest_path),
                "receipt": receipt,
                "write_boundary": write_boundary_payload(
                    writes_project_files=True,
                    write_paths=[
                        source_path,
                        source_receipt_path,
                        repo_rel(ledger_path),
                        repo_rel(latest_path),
                    ],
                    receipt_path=repo_rel(ledger_path),
                    latest_path=repo_rel(latest_path),
                ),
            }
        )
    else:
        payload["write_boundary"] = write_boundary_payload(
            writes_project_files=False,
            read_only_actions=["inspect server response", "preview", "copy"],
        )
    try:
        payload["trace"] = trace_payload_for_project(project=project, rubric=rubric, intake=intake)
    except SystemExit as exc:
        payload["trace_error"] = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - action result should still be inspectable.
        payload["trace_error"] = display_text(exc)
    try:
        payload["snapshot"] = snapshot_payload_for_project(
            project=project,
            rubric=rubric,
            intake=intake,
            renderer=renderer,
        )
    except SystemExit as exc:
        payload["snapshot_error"] = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - action result should still be inspectable.
        payload["snapshot_error"] = display_text(exc)
    return payload


def save_case_file_payload(
    *,
    project: str,
    case_file: Any,
    rubric: str | None = None,
    intake: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    if not isinstance(case_file, dict):
        raise ValueError("project_file must be a JSON object")
    if str(case_file.get("schema") or "") != CASE_FILE_SCHEMA:
        raise ValueError("project_file schema is not compatible with this workbench")
    case_file = case_file_payload_with_case(case_file, project=project, rubric=rubric, intake=intake)
    project_root = snapshot.REPO / "projects" / project
    if not project_root.exists():
        raise FileNotFoundError(f"project does not exist: projects/{project}")
    workspace = project_root / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    case_intake = str(case_file.get("intake") or intake or "")
    case_path = workspace / f"{case_file_stem(project, case_intake)}.json"
    case_bytes = (json.dumps(case_file, indent=2, sort_keys=True) + "\n").encode("utf-8")
    case_sha256 = hashlib.sha256(case_bytes).hexdigest()
    case_path.write_bytes(case_bytes)

    case_items = case_file.get("items")
    if not isinstance(case_items, list):
        case_items = case_file.get("rows")
    if not isinstance(case_items, list):
        case_items = []
    case_commands = case_file.get("audit_commands")
    if not isinstance(case_commands, list):
        case_commands = case_file.get("command_queue")
    if not isinstance(case_commands, list):
        case_commands = []
    receipt = add_case_context(
        {
            "schema": CASE_FILE_WRITE_SCHEMA,
            "applied_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "project": project,
            "project_file_path": repo_rel(case_path),
            "project_file_sha256": case_sha256,
            "case_file_path": repo_rel(case_path),
            "case_file_sha256": case_sha256,
            "item_count": len(case_items),
            "row_count": len(case_items),
            "command_count": len(case_commands),
            "receipt_count": len(case_file.get("recent_receipts") or []),
        },
        project=project,
        rubric=str(case_file.get("rubric") or rubric or ""),
        intake=str(case_file.get("intake") or intake or ""),
    )
    ledger_path = workspace / "forensic_workbench_case_files.jsonl"
    latest_path = workspace / "forensic_workbench_latest_case_file_write.json"
    append_jsonl(ledger_path, receipt)
    latest_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "schema": CASE_FILE_WRITE_SCHEMA,
        "served_from": "local_api",
        "ok": True,
        "project": project,
        "path": repo_rel(case_path),
        "project_file_path": repo_rel(case_path),
        "project_file_sha256": case_sha256,
        "receipt": receipt,
        "receipt_path": repo_rel(ledger_path),
        "latest": repo_rel(latest_path),
        "write_boundary": write_boundary_payload(
            writes_project_files=True,
            write_paths=[repo_rel(case_path), repo_rel(ledger_path), repo_rel(latest_path)],
            receipt_path=repo_rel(ledger_path),
            latest_path=repo_rel(latest_path),
        ),
    }


def compact_eval_payload(payload: dict[str, Any]) -> dict[str, Any]:
    gaps = payload.get("evidence_gaps") or []
    if not isinstance(gaps, list):
        gaps = []
    probability = payload.get("probability_dag") or {}
    outcome = probability.get("outcome") if isinstance(probability, dict) else {}
    if not isinstance(outcome, dict):
        outcome = {}
    return {
        "score": payload.get("score"),
        "weakest_point": str(payload.get("weakest_point") or ""),
        "evidence_gap_count": len(gaps),
        "evidence_gaps": [
            {
                "target": str(row.get("target") or ""),
                "severity": str(row.get("severity") or ""),
                "description": str(row.get("description") or ""),
                "required_surface": str(row.get("required_surface") or ""),
            }
            for row in gaps[:5]
            if isinstance(row, dict)
        ],
        "probability_outcome": {
            "label": str(outcome.get("label") or ""),
            "probability": outcome.get("probability"),
        },
    }


def compact_eval_history_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": row.get("run_id"),
        "iteration": row.get("iteration"),
        "score": row.get("score"),
        "timestamp": str(row.get("timestamp") or ""),
        "weakest_point": str(row.get("weakest_point") or ""),
        "gate_failure_count": safe_int(row.get("gate_failure_count")),
        "worker_capabilities": [str(item) for item in row.get("worker_capability_set") or []],
        "worker_transports": [str(item) for item in row.get("worker_transport_set") or []],
        "matched_run_role": str(row.get("matched_run_role") or ""),
        "artifact_refs": [snapshot.rel(path) for path in (row.get("artifact_refs") or [])[:8]],
    }


def compact_claim_support_source(row: dict[str, Any]) -> dict[str, Any]:
    preview = row.get("preview") if isinstance(row.get("preview"), dict) else {}
    return {
        "source_id": str(row.get("source_id") or ""),
        "status": str(row.get("status") or ""),
        "source_type": str(row.get("source_type") or ""),
        "path": display_path(row.get("path")),
        "relative_raw_path": str(row.get("relative_raw_path") or ""),
        "line_count": safe_int(row.get("line_count")),
        "hash_matches_index": row.get("hash_matches_index"),
        "preview": {
            "line_start": safe_int(preview.get("line_start")),
            "line_end": safe_int(preview.get("line_end")),
            "text": str(preview.get("text") or "")[:800],
            "truncated": bool(preview.get("truncated")),
        },
    }


def compact_claim_support_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": str(row.get("claim_id") or row.get("id") or ""),
        "status": str(row.get("status") or ""),
        "source_id": str(row.get("source_id") or ""),
        "support_level": str(row.get("support_level") or ""),
        "issue": str(row.get("issue") or row.get("reason") or ""),
    }


def claim_support_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    if intake:
        project_intake_path(project, intake, allow_examples=True)
    command = [
        SERVER_PYTHON,
        "-m",
        "src.ztare.cli",
        "project",
        "claim-support",
        "--project",
        project,
        "--json",
    ]
    proc = snapshot.run(command, timeout=90)
    parsed: dict[str, Any] = {}
    try:
        parsed = snapshot.extract_last_json_object(proc.stdout)
    except Exception:
        parsed = {}
    source_context = parsed.get("source_context") if isinstance(parsed.get("source_context"), dict) else {}
    evidence_file_path = display_path(parsed.get("packet_path"))
    status = str(parsed.get("status") or ("ok" if proc.returncode == 0 else "attention"))
    return {
        "schema": CLAIM_SUPPORT_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "project_key": case_key(project, intake),
        "case_key": case_key(project, intake),
        "support_scope": "project_compiled_evidence",
        "intake_scoped_command": False,
        "command": f"ztare project claim-support --project {project} --json",
        "returncode": proc.returncode,
        "accepted": proc.returncode == 0,
        "ok": bool(parsed.get("ok")),
        "status": status,
        "display_status": display_status(status),
        "claim_count": safe_int(parsed.get("claim_count")),
        "weak_or_unsourced_count": safe_int(parsed.get("weak_or_unsourced_count")),
        "source_context_blocked_count": safe_int(parsed.get("source_context_blocked_count")),
        "status_counts": parsed.get("status_counts") if isinstance(parsed.get("status_counts"), dict) else {},
        "source_context_status_counts": (
            parsed.get("source_context_status_counts")
            if isinstance(parsed.get("source_context_status_counts"), dict)
            else {}
        ),
        "errors": display_text_lines(parsed.get("errors") or [], limit=8),
        "evidence_support_file_path": evidence_file_path,
        "evidence_file_path": evidence_file_path,
        "packet_path": evidence_file_path,
        "source_index_path": display_path(parsed.get("source_index_path")),
        "rows": [compact_claim_support_row(row) for row in (parsed.get("rows") or [])[:12] if isinstance(row, dict)],
        "source_context": [
            compact_claim_support_source(row)
            for row in list(source_context.values())[:12]
            if isinstance(row, dict)
        ],
        "stdout_tail": tail_display_text(proc.stdout),
        "stderr_tail": tail_display_text(proc.stderr),
    }


def run_history_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    if intake:
        project_intake_path(project, intake, allow_examples=True)
    limit = max(1, min(limit, 25))
    project_root = snapshot.REPO / "projects" / project
    workspace = project_root / "workspace"
    eval_history_path = workspace / "eval_history.jsonl"
    latest_eval_path = project_root / "latest_eval_results.json"
    champion_eval_path = project_root / "champion_eval_results.json"
    synthesis_history_path = project_root / "synthesis" / "history_summary.json"

    rows = [compact_eval_history_row(row) for row in read_jsonl_objects(eval_history_path, limit=limit)]
    latest_eval = compact_eval_payload(read_optional_json_object(latest_eval_path))
    champion_eval = compact_eval_payload(read_optional_json_object(champion_eval_path))
    synthesis_history = read_optional_json_object(synthesis_history_path)
    latest_row = rows[-1] if rows else {}
    score_candidates = [row.get("score") for row in rows if isinstance(row.get("score"), (int, float))]
    if isinstance(champion_eval.get("score"), (int, float)):
        score_candidates.append(champion_eval["score"])
    best_score = max(score_candidates) if score_candidates else None
    return {
        "schema": RUN_HISTORY_SCHEMA,
        "ok": True,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "project_key": case_key(project, intake),
        "case_key": case_key(project, intake),
        "run_scope": "project_run_history",
        "intake_scoped_files": False,
        "limit": limit,
        "paths": {
            "eval_history": repo_rel(eval_history_path),
            "latest_eval": repo_rel(latest_eval_path),
            "champion_eval": repo_rel(champion_eval_path),
            "synthesis_history": repo_rel(synthesis_history_path),
        },
        "summary": {
            "run_rows": len(rows),
            "latest_score": latest_eval.get("score") if latest_eval else latest_row.get("score"),
            "best_score": best_score,
            "latest_run_id": latest_row.get("run_id"),
            "latest_iteration": latest_row.get("iteration"),
            "latest_timestamp": latest_row.get("timestamp"),
            "latest_weakest_point": latest_eval.get("weakest_point") or latest_row.get("weakest_point") or "",
            "latest_evidence_gap_count": latest_eval.get("evidence_gap_count") or 0,
        },
        "latest_eval": latest_eval,
        "champion_eval": champion_eval,
        "recent_runs": rows,
        "synthesis_history": {
            "summary_scope": str(synthesis_history.get("summary_scope") or ""),
            "recurring_failures": [str(item) for item in (synthesis_history.get("recurring_failures") or [])[:5]],
            "major_pivots": [str(item) for item in (synthesis_history.get("major_pivots") or [])[:5]],
            "cross_run_patterns": [str(item) for item in (synthesis_history.get("cross_run_patterns") or [])[:5]],
        },
    }


def project_source_count(project_root: Path) -> int:
    raw_dir = project_root / "raw"
    if not raw_dir.exists():
        return 0
    return sum(
        1
        for path in raw_dir.iterdir()
        if path.is_file() and path.name != "source_type_map.json"
    )


def workflow_step(
    *,
    step_id: str,
    label: str,
    status: str,
    route: str,
    detail: str,
    write_boundary: dict[str, Any] | None = None,
    source_status: str = "",
) -> dict[str, Any]:
    return {
        "id": step_id,
        "label": label,
        "status": status,
        "display_status": display_status(status),
        "route": route,
        "detail": detail,
        "local_step": workflow_local_action(step_id),
        "local_action": workflow_local_action(step_id),
        "ui_destination": workflow_ui_destination(step_id, status),
        "write_boundary": write_boundary or write_boundary_payload(writes_project_files=False),
        "source_status": source_status,
    }


def workflow_local_action(step_id: str) -> str:
    labels = {
        "open_project": "Load project",
        "prepare_files": "Edit intake and source files",
        "preflight": "Run preflight",
        "project_run": "Start or inspect run",
        "review_report": "Review report support",
        "save_project": "Save project file",
    }
    return labels.get(str(step_id or ""), "Open project step")


def workflow_ui_destination(step_id: str, status: str) -> dict[str, str]:
    if step_id == "open_project":
        return {"workspace": "projects", "subsection": "All projects"}
    if step_id == "prepare_files":
        return {"workspace": "sources", "subsection": "Intake" if status == "ready" else "File check"}
    if step_id == "preflight":
        return {"workspace": "run", "subsection": "Preflight"}
    if step_id == "project_run":
        return {"workspace": "run", "subsection": "Results" if status == "done" else "Start run"}
    if step_id == "review_report":
        return {
            "workspace": "review" if status == "ready" else "save",
            "subsection": "Save review" if status == "ready" else "Support check",
        }
    if step_id == "save_project":
        return {"workspace": "save", "subsection": "Project file"}
    return {"workspace": "overview", "subsection": "Status"}


def workflow_next_step(steps: list[dict[str, Any]]) -> dict[str, Any]:
    priority = {
        "needs_attention": 0,
        "failed": 0,
        "blocked": 0,
        "not_run": 1,
        "waiting": 2,
        "ready": 3,
        "not_saved": 4,
        "done": 9,
        "reviewed": 9,
    }
    candidates = [
        step
        for step in steps
        if str(step.get("id") or "") != "open_project"
        and str(step.get("status") or "") not in {"done", "reviewed"}
    ]
    if not candidates:
        return {}
    return min(
        candidates,
        key=lambda step: (
            priority.get(str(step.get("status") or ""), 5),
            steps.index(step),
        ),
    )


def workflow_summary_payload(steps: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = [str(step.get("status") or "") for step in steps]
    next_step = workflow_next_step(steps)
    write_paths = ((next_step.get("write_boundary") or {}).get("write_paths") or []) if next_step else []
    return {
        "step_count": len(steps),
        "ready_count": sum(1 for status in statuses if status in {"ready", "done", "reviewed"}),
        "attention_count": sum(1 for status in statuses if status in {"needs_attention", "failed", "blocked"}),
        "next_step_id": str(next_step.get("id") or ""),
        "next_step_label": str(next_step.get("label") or ""),
        "next_step_status": str(next_step.get("status") or ""),
        "next_step_display_status": str(next_step.get("display_status") or ""),
        "next_step_detail": str(next_step.get("detail") or ""),
        "next_step_local_step": str(next_step.get("local_step") or next_step.get("local_action") or ""),
        "next_step_local_action": str(next_step.get("local_action") or next_step.get("local_step") or ""),
        "next_step_ui_destination": next_step.get("ui_destination") or {},
        "next_step_write_path_count": len([path for path in write_paths if path]),
        "can_start_run": any(step.get("id") == "project_run" and step.get("status") == "ready" for step in steps),
        "project_file_saved": any(step.get("id") == "save_project" and step.get("status") == "done" for step in steps),
    }


def workflow_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
    mode: str = "fast",
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    renderer = renderer or snapshot.DEFAULT_RENDERER
    mode = str(mode or "fast").strip().lower()
    if mode not in {"fast", "full"}:
        raise ValueError("workflow mode must be fast or full")
    intake_path = project_intake_path(project, intake, allow_examples=True)
    project_root = snapshot.REPO / "projects" / project
    workspace = project_root / "workspace"

    errors: list[str] = []
    trace: dict[str, Any] = {}
    report: dict[str, Any] = {}
    receipts: dict[str, Any] = {}

    input_ready = False
    preflight_ready = False
    run_done = False
    report_status = ""
    report_ready = False
    run_can_start = False
    source_count = project_source_count(project_root)

    if mode == "full":
        rows: list[dict[str, Any]] = []
        run_history: dict[str, Any] = {}
        source_list: dict[str, Any] = {}
        try:
            snapshot_payload = snapshot_payload_for_project(project=project, rubric=rubric, intake=intake, renderer=renderer)
            rows = list(snapshot_payload.get("rows") or [])
        except Exception as exc:  # noqa: BLE001 - workflow should still return route/write contracts.
            errors.append(f"project data: {display_text(exc)}")
        try:
            trace = trace_payload_for_project(project=project, rubric=rubric, intake=intake)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"trace: {display_text(exc)}")
        try:
            report = report_contract_payload_for_project(project=project, rubric=rubric, intake=intake, renderer=renderer)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"report: {display_text(exc)}")
        try:
            run_history = run_history_payload_for_project(project=project, rubric=rubric, intake=intake)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"run history: {display_text(exc)}")
        try:
            source_list = source_list_payload(project=project)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"sources: {display_text(exc)}")

        source_row = next((row for row in rows if row.get("label") == "Source readiness"), {})
        evidence_row = next((row for row in rows if row.get("label") == "Evidence readiness"), {})
        input_ready = bool(
            source_row
            and evidence_row
            and source_row.get("kind") != "attention"
            and evidence_row.get("kind") != "attention"
        )
        plan = trace.get("plan_preview") if isinstance(trace.get("plan_preview"), dict) else {}
        preflight_receipt = trace.get("preflight_receipt") or trace.get("loop_admission") or {}
        if not isinstance(preflight_receipt, dict):
            preflight_receipt = {}
        preflight_ready = bool(
            preflight_receipt.get("receipt_count")
            or preflight_receipt.get("available")
            or plan.get("status") == "ready_for_bounded_run"
        )
        run_summary = run_history.get("summary") if isinstance(run_history.get("summary"), dict) else {}
        run_done = bool(safe_int(run_summary.get("run_rows")) or run_summary.get("latest_score") is not None)
        report_status = str(report.get("status") or "")
        report_ready = bool(report_status and report_status != "blocked")
        run_can_start = plan.get("status") == "ready_for_bounded_run"
        source_count = len(source_list.get("sources") or []) if isinstance(source_list.get("sources"), list) else source_count
    else:
        try:
            intake_payload = intake_payload_for_project(project, intake, allow_examples=True)
            ref_summary = ((intake_payload.get("reference_status") or {}).get("summary") or {})
            source_refs = (intake_payload.get("editable_fields") or {}).get("source_refs") or []
            evidence_refs = (intake_payload.get("editable_fields") or {}).get("evidence_refs") or []
            input_ready = bool(
                source_refs
                and evidence_refs
                and safe_int(ref_summary.get("missing")) == 0
                and safe_int(ref_summary.get("unsafe")) == 0
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"intake: {display_text(exc)}")
        preflight_ready = (workspace / "source_index_receipt.json").exists() or (workspace / "iteration_telemetry.jsonl").exists()
        run_done = (project_root / "latest_eval_results.json").exists() or (workspace / "eval_history.jsonl").exists()
        report = read_optional_json_object(project_root / "synthesis" / "report_support_contract.json")
        if report:
            binding = report.get("synthesis_input_binding") if isinstance(report.get("synthesis_input_binding"), dict) else {}
            support_issues = report_support_issues(report, binding)
            report["support_issues"] = support_issues
            report["display_status_reasons"] = [
                str(issue.get("display_reason") or issue.get("reason") or "")
                for issue in support_issues
                if issue.get("display_reason") or issue.get("reason")
            ]
        report_status = str(report.get("status") or ("ready" if report else ""))
        report_ready = bool(report_status and report_status != "blocked")
        run_can_start = input_ready and preflight_ready

    try:
        receipts = receipt_history_payload(project=project, intake=intake)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"receipts: {display_text(exc)}")
    receipt_rows = receipts.get("receipts") if isinstance(receipts.get("receipts"), list) else []
    review_done = any(row.get("kind") == "review" for row in receipt_rows if isinstance(row, dict))
    project_file_done = any(row.get("kind") == "case_file" for row in receipt_rows if isinstance(row, dict))

    project_digest = hashlib.sha256(case_key(project, intake).encode("utf-8")).hexdigest()[:12]
    project_file_paths = [
        repo_rel(workspace / f"forensic_workbench_case_file_{project_digest}.json"),
        repo_rel(workspace / "forensic_workbench_case_files.jsonl"),
        repo_rel(workspace / "forensic_workbench_latest_case_file_write.json"),
    ]

    steps = [
        workflow_step(
            step_id="open_project",
            label="Open project",
            status="ready",
            route="GET /api/projects -> GET /api/snapshot",
            detail="Project inventory and project data are loaded from the local API.",
        ),
        workflow_step(
            step_id="prepare_files",
            label="Prepare files",
            status="ready" if input_ready else "needs_attention",
            route="GET /api/sources, POST /api/intake, POST /api/source-import, POST /api/source-edit",
            detail=f"{source_count} source files loaded; source/evidence state is {'usable' if input_ready else 'not ready'}.",
            write_boundary=write_boundary_payload(
                writes_project_files=True,
                write_paths=[
                    repo_rel(project_intake_path(project, intake, allow_examples=True)),
                    repo_rel(workspace / "forensic_workbench_intake_edits.jsonl"),
                    repo_rel(workspace / "forensic_workbench_latest_intake_edit.json"),
                    repo_rel(project_root / "raw"),
                    repo_rel(workspace / "forensic_workbench_source_imports.jsonl"),
                    repo_rel(workspace / "forensic_workbench_source_edits.jsonl"),
                ],
            ),
            source_status="ready" if input_ready else "needs_attention",
        ),
        workflow_step(
            step_id="preflight",
            label="Preflight",
            status="ready" if preflight_ready else "not_run",
            route="POST /api/preflight",
            detail="Runs local preflight only; it does not start a model run.",
            write_boundary=write_boundary_payload(
                writes_project_files=True,
                write_paths=preflight_write_paths(trace) or [preflight_telemetry_path(project)],
                read_only_actions=["Copy command detail", "Inspect output"],
            ),
        ),
        workflow_step(
            step_id="project_run",
            label="Project run",
            status="done" if run_done else "ready" if run_can_start else "waiting",
            route="POST /api/run",
            detail="First request is a no-write preview; confirmed request may start model-backed work.",
            write_boundary=write_boundary_payload(
                writes_project_files=bool(run_can_start),
                write_paths=bounded_run_write_paths(project) if run_can_start else [],
                read_only_actions=["Inspect run plan", "Copy command detail"],
            ),
        ),
        workflow_step(
            step_id="review_report",
            label="Review report",
            status="ready" if report_ready else "needs_attention",
            route="GET /api/report-contract -> POST /api/review",
            detail=report_workflow_detail(report),
            write_boundary=write_boundary_payload(
                writes_project_files=report_ready,
                write_paths=(
                    [
                        repo_rel(workspace / "forensic_workbench_applied"),
                        repo_rel(workspace / "forensic_workbench_reviews.jsonl"),
                        repo_rel(workspace / "forensic_workbench_latest_review.json"),
                    ]
                    if report_ready
                    else []
                ),
                read_only_actions=["inspect report support", "preview backing files"],
            ),
            source_status="reviewed" if review_done else "",
        ),
        workflow_step(
            step_id="save_project",
            label="Save project",
            status="done" if project_file_done else "not_saved",
            route="POST /api/project-file",
            detail="Saves the project file plus ledger and latest receipt.",
            write_boundary=write_boundary_payload(
                writes_project_files=True,
                write_paths=project_file_paths,
                receipt_path=project_file_paths[1],
                latest_path=project_file_paths[2],
            ),
        ),
    ]
    summary = workflow_summary_payload(steps)
    return {
        "schema": WORKFLOW_SCHEMA,
        "ok": True,
        "served_from": "local_api",
        "mode": mode,
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "project_key": case_key(project, intake),
        "case_key": case_key(project, intake),
        "steps": steps,
        "summary": summary,
        **summary,
        "next_step": workflow_next_step(steps),
        "errors": errors,
    }


def local_dev_origin(origin: str | None) -> str:
    if origin and LOCAL_DEV_ORIGIN_RE.match(origin):
        return origin
    return DEFAULT_DEV_ORIGIN


class WorkbenchHandler(BaseHTTPRequestHandler):
    server_version = "ZTAREProjectWorkbench/0.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def send_json(self, payload: dict[str, Any], status: int = 200, *, include_body: bool = True) -> None:
        code, body = json_bytes(payload, status)
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", local_dev_origin(self.headers.get("Origin")))
        self.send_header("Vary", "Origin")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if include_body:
            self.wfile.write(body)

    def send_static_file(self, path: Path, *, include_body: bool = True) -> None:
        if not path.exists() or not path.is_file():
            if path.name == "index.html":
                self.send_json(
                    {
                        "ok": False,
                        "error": "React app is not built. Run `make forensic-workbench-build`, then reload the workbench server.",
                    },
                    status=404,
                    include_body=include_body,
                )
                return
            self.send_json({"ok": False, "error": f"static file not found: {display_path(path)}"}, status=404, include_body=include_body)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix == ".js":
            content_type = "text/javascript"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store" if path.name == "index.html" else "public, max-age=60")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if include_body:
            self.wfile.write(body)

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/status":
                self.send_json(server_status_payload(), include_body=False)
                return
            static_path = static_workbench_path(parsed.path)
            if static_path is not None:
                self.send_static_file(static_path, include_body=False)
                return
            if not parsed.path.startswith("/api/"):
                self.send_static_file(WORKBENCH_DIST / "index.html", include_body=False)
                return
            self.send_json({"ok": False, "error": f"unknown endpoint: {parsed.path}"}, status=404, include_body=False)
        except Exception as exc:  # noqa: BLE001 - local server should return structured failures.
            self.send_json({"ok": False, "error": display_text(exc)}, status=500, include_body=False)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", local_dev_origin(self.headers.get("Origin")))
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Vary", "Origin")
        self.send_header("Content-Length", "0")
        self.end_headers()

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
            if parsed.path == "/api/status":
                self.send_json(server_status_payload())
                return
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
            if parsed.path == "/api/workflow":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                rubric = first_param(params, "rubric", project)
                intake = first_param(params, "intake", snapshot.default_intake_for_project(project))
                renderer = first_param(params, "renderer", snapshot.DEFAULT_RENDERER)
                mode = first_param(params, "mode", "fast")
                payload = workflow_payload_for_project(
                    project=project,
                    rubric=rubric,
                    intake=intake,
                    renderer=renderer,
                    mode=mode,
                )
                self.send_json(payload)
                return
            if parsed.path == "/api/report-contract":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                rubric = first_param(params, "rubric", project)
                intake = first_param(params, "intake", "")
                renderer = first_param(params, "renderer", snapshot.DEFAULT_RENDERER)
                payload = report_contract_payload_for_project(
                    project=project,
                    rubric=rubric,
                    intake=intake or None,
                    renderer=renderer,
                )
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
                intake = first_param(params, "intake", "")
                limit = int(first_param(params, "limit", "12"))
                self.send_json(receipt_history_payload(project=project, limit=limit, intake=intake or None))
                return
            if parsed.path == "/api/sources":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                self.send_json(source_list_payload(project=project))
                return
            if parsed.path == "/api/source-file":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                relative_path = first_param(params, "relative", "")
                self.send_json(source_file_payload(project=project, relative_path=relative_path))
                return
            if parsed.path == "/api/run-history":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                rubric = first_param(params, "rubric", project)
                intake = first_param(params, "intake", "")
                limit = int(first_param(params, "limit", "8"))
                self.send_json(run_history_payload_for_project(project=project, rubric=rubric, intake=intake or None, limit=limit))
                return
            if parsed.path in {"/api/evidence-support", "/api/claim-support"}:
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                rubric = first_param(params, "rubric", project)
                intake = first_param(params, "intake", "")
                payload = claim_support_payload_for_project(project=project, rubric=rubric, intake=intake or None)
                payload["endpoint"] = parsed.path
                if parsed.path == "/api/claim-support":
                    payload["compatibility_note"] = "Use /api/evidence-support for new clients; /api/claim-support is kept for existing clients."
                self.send_json(payload)
                return
            static_path = static_workbench_path(parsed.path)
            if static_path is not None:
                self.send_static_file(static_path)
                return
            if not parsed.path.startswith("/api/"):
                self.send_static_file(WORKBENCH_DIST / "index.html")
                return
            self.send_json({"ok": False, "error": "unknown endpoint"}, status=404)
        except SystemExit as exc:
            self.send_json({"ok": False, "error": display_text(exc)}, status=400)
        except Exception as exc:  # noqa: BLE001 - API should return inspectable JSON errors.
            self.send_json({"ok": False, "error": display_text(exc)}, status=400)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/review":
                self.send_json(review_payload_from_request(self.read_json_body()))
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
                    rubric=rubric,
                )
                response = {
                    "ok": True,
                    "edit": edit_result,
                    "intake": edit_result.get("intake"),
                    "write_boundary": edit_result.get("write_boundary"),
                    "snapshot": None,
                }
                try:
                    response["snapshot"] = snapshot_payload_for_project(project=project, rubric=rubric, intake=intake)
                except SystemExit as exc:
                    response["snapshot_error"] = display_text(exc)
                except Exception as exc:  # noqa: BLE001 - intake write already succeeded.
                    response["snapshot_error"] = display_text(exc)
                self.send_json(response)
                return
            if parsed.path in {"/api/next-step", "/api/item-action", "/api/row-action"}:
                response = item_action_payload_from_request(self.read_json_body())
                response["endpoint"] = parsed.path
                if parsed.path in {"/api/item-action", "/api/row-action"}:
                    response["compatibility_note"] = "Use /api/next-step for new clients; this route is kept for existing receipts."
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
            if parsed.path == "/api/run":
                request = self.read_json_body()
                project = str(request.get("project") or "")
                rubric = str(request.get("rubric") or "") or None
                intake = str(request.get("intake") or "") or None
                renderer = str(request.get("renderer") or "") or None
                response = bounded_run_payload_for_project(
                    project=project,
                    rubric=rubric,
                    intake=intake,
                    renderer=renderer,
                    confirmed=request.get("confirmed") is True,
                )
                status = 200 if response.get("accepted") or response.get("status") == "needs_confirmation" else 400
                self.send_json(response, status=status)
                return
            if parsed.path == "/api/source-action":
                request = self.read_json_body()
                project = str(request.get("project") or "")
                rubric = str(request.get("rubric") or "") or None
                intake = str(request.get("intake") or "") or None
                renderer = str(request.get("renderer") or "") or None
                action = str(request.get("action") or "")
                response = source_action_payload_for_project(
                    project=project,
                    action=action,
                    rubric=rubric,
                    intake=intake,
                    renderer=renderer,
                )
                self.send_json(response)
                return
            if parsed.path == "/api/project-create":
                request = self.read_json_body()
                response = create_project_payload(
                    project=str(request.get("project") or ""),
                    rubric=str(request.get("rubric") or "") or None,
                    task=str(request.get("task") or ""),
                    bounded_claim=str(request.get("bounded_claim") or ""),
                    next_falsifier=str(request.get("next_falsifier") or ""),
                    notes=str(request.get("notes") or ""),
                    source_refs=request.get("source_refs"),
                    evidence_refs=request.get("evidence_refs"),
                    non_claims=request.get("non_claims"),
                    renderer=str(request.get("renderer") or "") or None,
                )
                self.send_json(response)
                return
            if parsed.path == "/api/source-import":
                request = self.read_json_body()
                response = import_source_payload(
                    project=str(request.get("project") or ""),
                    rubric=str(request.get("rubric") or "") or None,
                    intake=str(request.get("intake") or "") or None,
                    renderer=str(request.get("renderer") or "") or None,
                    filename=str(request.get("filename") or ""),
                    source_type=str(request.get("source_type") or ""),
                    body=str(request.get("body") or ""),
                )
                self.send_json(response)
                return
            if parsed.path == "/api/source-edit":
                request = self.read_json_body()
                response = edit_source_payload(
                    project=str(request.get("project") or ""),
                    rubric=str(request.get("rubric") or "") or None,
                    intake=str(request.get("intake") or "") or None,
                    renderer=str(request.get("renderer") or "") or None,
                    relative_path=str(request.get("relative_raw_path") or request.get("relative") or ""),
                    source_type=str(request.get("source_type") or ""),
                    body=str(request.get("body") or ""),
                )
                self.send_json(response)
                return
            if parsed.path in {"/api/project-file", "/api/case-file"}:
                request = self.read_json_body()
                response = save_case_file_payload(
                    project=str(request.get("project") or ""),
                    rubric=str(request.get("rubric") or "") or None,
                    intake=str(request.get("intake") or "") or None,
                    case_file=request.get("project_file") or request.get("case_file"),
                )
                response["endpoint"] = parsed.path
                if parsed.path == "/api/case-file":
                    response["compatibility_note"] = "Use /api/project-file for new clients; /api/case-file is kept for existing receipts."
                self.send_json(response)
                return
            self.send_json({"ok": False, "error": "unknown endpoint"}, status=404)
        except SystemExit as exc:
            self.send_json(post_error_payload(parsed.path, exc), status=400)
        except Exception as exc:  # noqa: BLE001 - API should return inspectable JSON errors.
            self.send_json(post_error_payload(parsed.path, exc), status=400)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), WorkbenchHandler)
    print(f"Project Workbench server listening on http://{args.host}:{args.port}", flush=True)
    if not (WORKBENCH_DIST / "index.html").exists():
        print("  React app not built yet. Run `make forensic-workbench-build` to serve the UI from this server.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
