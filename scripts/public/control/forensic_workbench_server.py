#!/usr/bin/env python3
"""Local API for the forensic workbench prototype."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import forensic_workbench_snapshot as snapshot
import forensic_workbench_review as review


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MAX_PREVIEW_BYTES = 200_000
INTAKE_EDIT_SCHEMA = "ztare-forensic-workbench-intake-edit-receipt-v1"
INTAKE_EDIT_FIELDS = ("bounded_claim", "next_falsifier", "notes", "non_claims")


def json_bytes(payload: dict[str, Any], status: int = 200) -> tuple[int, bytes]:
    return status, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def first_param(params: dict[str, list[str]], key: str, default: str) -> str:
    values = params.get(key)
    if not values:
        return default
    return values[0] or default


def repo_rel(path: Path) -> str:
    return str(path.resolve().relative_to(snapshot.REPO.resolve()))


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


def project_intake_path(project: str, intake: str | None = None) -> Path:
    project = snapshot.validate_project_slug(project)
    intake_path = intake or snapshot.default_intake_for_project(project)
    candidate = Path(intake_path)
    if candidate.is_absolute():
        raise ValueError("intake path must be relative to the repository")
    resolved = (snapshot.REPO / candidate).resolve()
    project_root = (snapshot.REPO / "projects" / project).resolve()
    if resolved != project_root and project_root not in resolved.parents:
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


def intake_payload_for_project(project: str, intake: str | None = None) -> dict[str, Any]:
    path = project_intake_path(project, intake)
    payload = read_json_object(path, "project intake")
    return {
        "schema": "ztare-forensic-workbench-intake-v1",
        "served_from": "local_api",
        "project": project,
        "path": repo_rel(path),
        "editable_fields": {
            "bounded_claim": str(payload.get("bounded_claim") or ""),
            "next_falsifier": str(payload.get("next_falsifier") or ""),
            "notes": str(payload.get("notes") or ""),
            "non_claims": [str(item) for item in payload.get("non_claims") or []],
        },
    }


def normalize_intake_patch(raw_patch: Any) -> dict[str, Any]:
    if not isinstance(raw_patch, dict):
        raise ValueError("fields must be a JSON object")
    patch: dict[str, Any] = {}
    for key in INTAKE_EDIT_FIELDS:
        if key not in raw_patch:
            continue
        value = raw_patch[key]
        if key == "non_claims":
            if isinstance(value, str):
                value = [line.strip() for line in value.splitlines() if line.strip()]
            if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
                raise ValueError("non_claims must be a list of non-empty strings")
            patch[key] = [item.strip() for item in value]
            continue
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a non-empty string")
        patch[key] = value.strip()
    if not patch:
        raise ValueError("no editable intake fields supplied")
    return patch


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def apply_intake_edit(*, project: str, intake: str | None, raw_patch: Any) -> dict[str, Any]:
    path = project_intake_path(project, intake)
    before_bytes = path.read_bytes()
    payload = read_json_object(path, "project intake")
    if payload.get("project") and payload.get("project") != project:
        raise ValueError(f"intake project mismatch: expected {project!r}, got {payload.get('project')!r}")
    patch = normalize_intake_patch(raw_patch)
    intake_rel = repo_rel(path)
    before_values = {key: payload.get(key) for key in patch}
    payload.update(patch)
    after_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    after_bytes = after_text.encode("utf-8")
    path.write_bytes(after_bytes)

    workspace = snapshot.REPO / "projects" / project / "workspace"
    receipt = {
        "schema": INTAKE_EDIT_SCHEMA,
        "applied_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "project": project,
        "intake_path": intake_rel,
        "updated_fields": sorted(patch),
        "before_sha256": hashlib.sha256(before_bytes).hexdigest(),
        "after_sha256": hashlib.sha256(after_bytes).hexdigest(),
        "before_values": before_values,
        "after_values": {key: payload.get(key) for key in patch},
    }
    ledger_path = workspace / "forensic_workbench_intake_edits.jsonl"
    latest_path = workspace / "forensic_workbench_latest_intake_edit.json"
    append_jsonl(ledger_path, receipt)
    latest_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "intake": intake_payload_for_project(project, intake_rel),
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
    )
    payload["served_from"] = "local_api"
    return payload


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
                projects = snapshot.list_project_entries()
                self.send_json(
                    {
                        "schema": "ztare-forensic-workbench-project-index-v1",
                        "default_project": snapshot.DEFAULT_PROJECT,
                        "projects": projects,
                    }
                )
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
            if parsed.path == "/api/file":
                params = parse_qs(parsed.query)
                path = first_param(params, "path", "")
                self.send_json(file_preview_payload(path))
                return
            if parsed.path == "/api/intake":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                intake = first_param(params, "intake", snapshot.default_intake_for_project(project))
                self.send_json(intake_payload_for_project(project, intake))
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
