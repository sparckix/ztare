#!/usr/bin/env python3
"""Local API for the forensic workbench prototype."""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import forensic_workbench_snapshot as snapshot
import forensic_workbench_review as review


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def json_bytes(payload: dict[str, Any], status: int = 200) -> tuple[int, bytes]:
    return status, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def first_param(params: dict[str, list[str]], key: str, default: str) -> str:
    values = params.get(key)
    if not values:
        return default
    return values[0] or default


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
