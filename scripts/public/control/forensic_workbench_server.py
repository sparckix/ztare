#!/usr/bin/env python3
"""Local API for the D4 forensic workbench."""
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
ACTION_INTELLIGENCE_STATE_DIR = Path("analytics/public/action_intelligence/state")
INTAKE_EDIT_FIELDS = ("bounded_claim", "next_falsifier", "notes", "non_claims", "source_refs", "evidence_refs")
INTAKE_LIST_FIELDS = {"non_claims", "source_refs", "evidence_refs"}
EXTERNAL_REF_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
SOURCE_IMPORT_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}\.(md|txt)$")
SOURCE_IMPORT_TYPES = {"source_evidence", "seed_hypothesis", "research_question", "collection_todo", "untyped"}
SOURCE_ACTIONS = {
    "source_check": {
        "label": "Check sources",
        "args": ["project", "source-check", "--project", "{project}", "--json"],
        "display": "ztare project source-check --project {project} --json",
        "timeout": 90,
        "writes": False,
    },
    "source_index": {
        "label": "Refresh source index",
        "args": ["project", "source-index", "--project", "{project}", "--index-only", "--json"],
        "display": "ztare project source-index --project {project} --index-only --json",
        "timeout": 120,
        "writes": True,
    },
    "evidence_replay": {
        "label": "Check evidence replay",
        "args": ["project", "evidence-replay", "--project", "{project}", "--json"],
        "display": "ztare project evidence-replay --project {project} --json",
        "timeout": 90,
        "writes": False,
    },
    "evidence_bind": {
        "label": "Bind evidence outputs",
        "args": ["project", "evidence-bind", "--project", "{project}", "--json"],
        "display": "ztare project evidence-bind --project {project} --json",
        "timeout": 90,
        "writes": True,
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


def display_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): display_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [display_data(item) for item in value]
    if isinstance(value, str):
        return display_text(value)
    return value


def persist_live_row_payload(*, project: str, row: str, kind: str, payload: dict[str, Any]) -> tuple[str, bytes]:
    project = snapshot.validate_project_slug(project)
    if not re.fullmatch(r"[a-z0-9_]+", row):
        raise ValueError(f"invalid row slug: {row!r}")
    if kind not in {"review", "action"}:
        raise ValueError(f"invalid live row payload kind: {kind!r}")
    payload_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    payload_bytes = payload_text.encode("utf-8")
    digest = hashlib.sha256(payload_bytes).hexdigest()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    workspace = snapshot.REPO / "projects" / project / "workspace" / "forensic_workbench_applied"
    path = workspace / f"{stamp}_{row}_{kind}_{digest[:12]}.json"
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
    if rubric and not scoped_payload.get("rubric"):
        scoped_payload["rubric"] = rubric
    if intake:
        scoped_payload.setdefault("intake", intake)
        scoped_payload.setdefault("case_key", case_key(project, intake))
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
        raise ValueError("case_file project must match request project")

    rubric_value = str(rubric or scoped_payload.get("rubric") or "").strip()
    existing_rubric = str(scoped_payload.get("rubric") or "").strip()
    if rubric and existing_rubric and existing_rubric != rubric:
        raise ValueError("case_file rubric must match request rubric")
    if rubric_value:
        scoped_payload["rubric"] = rubric_value

    intake_value = str(intake or scoped_payload.get("intake") or "").strip()
    existing_intake = str(scoped_payload.get("intake") or "").strip()
    if intake and existing_intake and existing_intake != intake:
        raise ValueError("case_file intake must match request intake")
    if intake_value:
        expected_case_key = case_key(project, intake_value)
        existing_case_key = str(scoped_payload.get("case_key") or "").strip()
        if existing_case_key and existing_case_key != expected_case_key:
            raise ValueError("case_file case_key must match request case")
        scoped_payload["intake"] = intake_value
        scoped_payload["case_key"] = expected_case_key
    return scoped_payload


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
            row["intake_error"] = display_text(exc)
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


def case_key(project: str, intake: str | None) -> str:
    intake_value = str(intake or "").strip()
    return f"{project}::{intake_value}" if intake_value else project


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
    receipt["case_key"] = case_key(project, intake_value)
    return receipt


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
        "rubric": str(payload.get("rubric") or ""),
        "intake": str(payload.get("intake") or payload.get("intake_path") or ""),
        "case_key": str(payload.get("case_key") or ""),
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
                "review_file_path": display_path(payload.get("review_file_path")),
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
                "action_file_path": display_path(payload.get("action_file_path")),
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
    elif kind in {"source_import", "source_edit"}:
        row.update(
            {
                "source_path": str(payload.get("source_path") or ""),
                "source_type": str(payload.get("source_type") or ""),
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
                "label": str(payload.get("label") or ""),
                "accepted": bool(payload.get("accepted")),
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
            f"artifact={row['source_path'] or row['source_receipt_path'] or 'not surfaced'}"
        )
    elif kind == "case_file":
        row.update(
            {
                "case_file_path": str(payload.get("case_file_path") or ""),
                "row_count": safe_int(payload.get("row_count")),
                "command_count": safe_int(payload.get("command_count")),
                "receipt_count": safe_int(payload.get("receipt_count")),
                "sha256": str(payload.get("case_file_sha256") or ""),
            }
        )
        row["summary"] = (
            f"Saved case file with {row['row_count']} rows, "
            f"{row['command_count']} commands, {row['receipt_count']} receipts"
        )
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


def receipt_matches_case(row: dict[str, Any], *, project: str, intake: str | None = None) -> bool:
    if row.get("project") and row.get("project") != project:
        return False
    intake_value = str(intake or "").strip()
    if not intake_value:
        return True
    row_case_key = str(row.get("case_key") or "").strip()
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
    receipts: list[dict[str, Any]] = []
    for kind, path in ledgers.items():
        receipts.extend(read_receipt_ledger(path, kind=kind))
    total_receipt_count = len(receipts)
    receipts = [row for row in receipts if receipt_matches_case(row, project=project, intake=intake)]
    receipts.sort(key=lambda row: (str(row.get("applied_at") or ""), str(row.get("kind") or ""), int(row.get("line") or 0)), reverse=True)
    return {
        "schema": RECEIPT_HISTORY_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "intake": str(intake or ""),
        "limit": limit,
        "receipt_count": len(receipts),
        "total_receipt_count": total_receipt_count,
        "receipts": receipts[:limit],
        "paths": {kind: repo_rel(path) for kind, path in ledgers.items()},
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
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or ""
    if intake:
        project_intake_path(project, intake, allow_examples=True)
    renderer = renderer or snapshot.DEFAULT_RENDERER
    payload, command = snapshot.collect_report_contract(project, renderer)
    binding = payload.get("synthesis_input_binding") or {}
    reasons = [str(reason) for reason in payload.get("status_reasons") or []]
    report_path = snapshot.rel(payload.get("report_support_contract"))
    return {
        "schema": REPORT_CONTRACT_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "case_key": case_key(project, intake),
        "report_scope": "project_report_support",
        "intake_scoped_command": False,
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
                "recommended_action": row.get("recommended_action"),
                "confidence": row.get("confidence"),
                "execution_authority": row.get("execution_authority"),
                "rationale": row.get("rationale"),
                "blocking_checks": row.get("blocking_checks") or [],
                "evidence_refs": row.get("evidence_refs") or [],
                "source": row.get("source"),
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
    recommendation_payload = action_intelligence_recommendations()

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
            "issue_id": issue.get("issue_id"),
            "issue_type": issue.get("issue_type"),
            "severity": issue.get("severity"),
            "scope": issue.get("scope"),
            "domain": issue.get("domain"),
            "affected_domains": issue.get("affected_domains") or [],
            "blocking_rule": issue.get("blocking_rule"),
            "denominator": issue.get("denominator"),
            "observed_count": issue.get("observed_count"),
            "expected_count": issue.get("expected_count"),
            "freshness_window_days": issue.get("freshness_window_days"),
            "evidence_refs": issue.get("evidence_refs") or [],
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
            "recommendations": recommendation_payload.get("recommendations") or [],
            "recommendation_counts": recommendation_payload.get("counts") or {},
            "recommendations_generated_at": recommendation_payload.get("generated_at"),
            "recommendations_source_path": recommendation_payload.get("source_path"),
            "source_paths": action_payload.get("source_paths") or {},
        },
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
    body = str(body or "").strip()
    if not body:
        raise ValueError("source body is required")
    project_root = snapshot.REPO / "projects" / project
    raw_dir = project_root / "raw"
    workspace = project_root / "workspace"
    if not raw_dir.exists():
        raise FileNotFoundError(f"raw source directory does not exist: {repo_rel(raw_dir)}")
    source_path = (raw_dir / filename).resolve()
    if not path_under(source_path, raw_dir):
        raise ValueError("source path escapes raw source directory")
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
    source_check = source_action_payload_for_project(
        project=project,
        action="source_check",
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
        raise ValueError(f"invalid raw source path: {unsafe_reason}")
    path = PurePosixPath(value)
    if path.name == "source_type_map.json":
        raise ValueError("source_type_map.json is edited by the workbench, not as a source")
    if path.suffix.lower() not in {".md", ".txt"}:
        raise ValueError("raw source path must end in .md or .txt")
    return path.as_posix()


def raw_source_path(project: str, relative_path: str) -> Path:
    raw_dir = source_raw_dir(project)
    relative_path = validate_raw_source_relative(relative_path)
    path = (raw_dir / relative_path).resolve()
    if not path_under(path, raw_dir):
        raise ValueError("raw source path escapes the project raw directory")
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
            return source_type, body.strip()
    return source_type, text.strip()


def source_list_payload(*, project: str) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    command = [
        snapshot.PYTHON,
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
    return {
        "schema": SOURCE_LIST_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "raw_dir": repo_rel(raw_dir) if raw_dir.exists() else f"projects/{project}/raw",
        "command": f"ztare project source-check --project {project} --json --no-fail",
        "returncode": proc.returncode,
        "accepted": proc.returncode == 0,
        "stdout_tail": tail_display_text(proc.stdout),
        "stderr_tail": tail_display_text(proc.stderr),
        "source_check": display_data(parsed),
        "sources": display_data(parsed.get("sources")) if isinstance(parsed.get("sources"), list) else [],
    }


def source_file_payload(*, project: str, relative_path: str) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    path = raw_source_path(project, relative_path)
    if not path.exists():
        raise FileNotFoundError(f"raw source does not exist: {repo_rel(path)}")
    raw_dir = source_raw_dir(project)
    type_map = read_source_type_map(raw_dir)
    relative_path = str(path.relative_to(raw_dir))
    fallback_type = str(type_map.get(relative_path) or type_map.get(path.name) or "untyped")
    source_type, body = split_source_frontmatter(path.read_text(encoding="utf-8"), fallback_source_type=fallback_type)
    return {
        "schema": SOURCE_FILE_SCHEMA,
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
    body = str(body or "").strip()
    if not body:
        raise ValueError("source body is required")
    path = raw_source_path(project, relative_path)
    if not path.exists():
        raise FileNotFoundError(f"raw source does not exist: {repo_rel(path)}")
    raw_dir = source_raw_dir(project)
    relative_path = str(path.relative_to(raw_dir))
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
    source_check = source_action_payload_for_project(
        project=project,
        action="source_check",
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
    if project_root.exists():
        raise ValueError(f"project already exists: {project}")
    intake = f"projects/{project}/{project}_intake.json"
    expected_command = (
        "ztare autoresearch run "
        f"--project {project} --rubric {rubric} --intake {intake} --iters 1"
    )
    source_init_command = [
        snapshot.PYTHON,
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
        snapshot.PYTHON,
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
    accepted = source_proc.returncode == 0 and bool(intake_result and intake_result["accepted"])
    payload: dict[str, Any] = {
        "schema": PROJECT_CREATE_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "accepted": accepted,
        "source_init": {
            "command": f"ztare project source-init --project {project} --rubric {rubric} --json",
            **command_result_payload(source_proc),
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
        "stdout_tail": tail_display_text(proc.stdout),
        "stderr_tail": tail_display_text(proc.stderr),
        "trace": None,
        "snapshot": None,
    }
    try:
        payload["trace"] = trace_payload_for_project(project=project, rubric=rubric, intake=intake)
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
    command = [snapshot.PYTHON, "-m", "src.ztare.cli", *command_args]
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
            }
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
        raise ValueError("case_file must be a JSON object")
    if str(case_file.get("schema") or "") != CASE_FILE_SCHEMA:
        raise ValueError(f"case_file schema must be {CASE_FILE_SCHEMA}")
    case_file = case_file_payload_with_case(case_file, project=project, rubric=rubric, intake=intake)
    project_root = snapshot.REPO / "projects" / project
    if not project_root.exists():
        raise FileNotFoundError(f"project does not exist: projects/{project}")
    workspace = project_root / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    case_path = workspace / "forensic_workbench_case_file.json"
    case_bytes = (json.dumps(case_file, indent=2, sort_keys=True) + "\n").encode("utf-8")
    case_path.write_bytes(case_bytes)

    receipt = add_case_context(
        {
            "schema": CASE_FILE_WRITE_SCHEMA,
            "applied_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "project": project,
            "case_file_path": repo_rel(case_path),
            "case_file_sha256": hashlib.sha256(case_bytes).hexdigest(),
            "row_count": len(case_file.get("rows") or []),
            "command_count": len(case_file.get("command_queue") or []),
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
        "receipt": receipt,
        "receipt_path": repo_rel(ledger_path),
        "latest": repo_rel(latest_path),
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
    intake = intake or ""
    if intake:
        project_intake_path(project, intake, allow_examples=True)
    command = [
        snapshot.PYTHON,
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
    return {
        "schema": CLAIM_SUPPORT_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "case_key": case_key(project, intake),
        "support_scope": "project_compiled_evidence",
        "intake_scoped_command": False,
        "command": f"ztare project claim-support --project {project} --json",
        "returncode": proc.returncode,
        "accepted": proc.returncode == 0,
        "ok": bool(parsed.get("ok")),
        "status": str(parsed.get("status") or ("ok" if proc.returncode == 0 else "attention")),
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
    intake = intake or ""
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
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
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
            if parsed.path == "/api/claim-support":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                rubric = first_param(params, "rubric", project)
                intake = first_param(params, "intake", "")
                self.send_json(claim_support_payload_for_project(project=project, rubric=rubric, intake=intake or None))
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
                request = self.read_json_body()
                project = str(request.get("project") or "")
                rubric = str(request.get("rubric") or "") or None
                intake = str(request.get("intake") or "") or None
                row = str(request.get("row_slug") or "")
                review_file = request.get("review_file")
                if not isinstance(review_file, dict):
                    raise ValueError("review_file must be a JSON object")
                review_errors = review.validate_review_file(review_file, project=project, row=row, intake=intake)
                if review_errors:
                    raise ValueError("invalid review file: " + "; ".join(review_errors))
                review_file = live_row_payload_with_case(review_file, project=project, rubric=rubric, intake=intake)
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
                )
                response = {
                    "ok": True,
                    "review": review_result,
                    "snapshot": None,
                }
                try:
                    response["snapshot"] = snapshot_payload_for_project(project=project, rubric=rubric, intake=intake)
                except SystemExit as exc:
                    response["snapshot_error"] = display_text(exc)
                except Exception as exc:  # noqa: BLE001 - receipt write already succeeded.
                    response["snapshot_error"] = display_text(exc)
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
                    rubric=rubric,
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
                    response["snapshot_error"] = display_text(exc)
                except Exception as exc:  # noqa: BLE001 - intake write already succeeded.
                    response["snapshot_error"] = display_text(exc)
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
                action_errors = review.validate_action_file(action_file, project=project, row=row, intake=intake)
                if action_errors:
                    raise ValueError("invalid row action file: " + "; ".join(action_errors))
                action_file = live_row_payload_with_case(action_file, project=project, rubric=rubric, intake=intake)
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
                )
                response = {
                    "ok": True,
                    "action": action_result,
                    "snapshot": None,
                }
                try:
                    response["snapshot"] = snapshot_payload_for_project(project=project, rubric=rubric, intake=intake)
                except SystemExit as exc:
                    response["snapshot_error"] = display_text(exc)
                except Exception as exc:  # noqa: BLE001 - receipt write already succeeded.
                    response["snapshot_error"] = display_text(exc)
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
            if parsed.path == "/api/case-file":
                request = self.read_json_body()
                response = save_case_file_payload(
                    project=str(request.get("project") or ""),
                    rubric=str(request.get("rubric") or "") or None,
                    intake=str(request.get("intake") or "") or None,
                    case_file=request.get("case_file"),
                )
                self.send_json(response)
                return
            self.send_json({"ok": False, "error": "unknown endpoint"}, status=404)
        except SystemExit as exc:
            self.send_json({"ok": False, "error": display_text(exc)}, status=400)
        except Exception as exc:  # noqa: BLE001 - API should return inspectable JSON errors.
            self.send_json({"ok": False, "error": display_text(exc)}, status=400)


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
