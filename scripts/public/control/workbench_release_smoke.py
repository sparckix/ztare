#!/usr/bin/env python3
"""Release smoke for the built Project Workbench and its disclosure boundary."""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
SERVER = REPO / "scripts/public/control/forensic_workbench_server.py"
MANIFEST = REPO / "forensic-workbench/public-projects.json"
DIST_INDEX = REPO / "forensic-workbench/dist/index.html"
SLUG_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
EXPECTED_SCHEMA = "ztare-workbench-public-projects-v1"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request_json(
    base: str,
    path: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    origin: str = "",
    timeout: float = 15.0,
) -> tuple[int, dict[str, str], dict[str, Any]]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if origin:
        headers["Origin"] = origin
    req = urllib.request.Request(f"{base}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return response.status, dict(response.headers.items()), payload
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = {"ok": False, "error": f"HTTP {exc.code}"}
        return exc.code, dict(exc.headers.items()), payload


def request_text(base: str, path: str, *, timeout: float = 15.0) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(f"{base}{path}", timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def load_public_projects() -> list[str]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if payload.get("schema") != EXPECTED_SCHEMA:
        raise ValueError(f"public project manifest must use {EXPECTED_SCHEMA}")
    raw = payload.get("projects")
    if not isinstance(raw, list) or not raw:
        raise ValueError("public project manifest must declare at least one project")
    projects = [str(item).strip() for item in raw]
    if any(not SLUG_RE.fullmatch(item) for item in projects):
        raise ValueError("public project manifest contains an invalid project slug")
    if len(set(projects)) != len(projects):
        raise ValueError("public project manifest contains duplicate project slugs")
    missing = [project for project in projects if not (REPO / "projects" / project).is_dir()]
    if missing:
        raise ValueError(f"public project folders are missing: {', '.join(missing)}")
    return projects


def wait_for_server(base: str, process: subprocess.Popen[str], timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            status, _, _ = request_json(base, "/api/status", timeout=1.0)
            if status == 200:
                return True
        except (OSError, urllib.error.URLError, ValueError):
            pass
        time.sleep(0.1)
    return False


def stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--startup-timeout", type=float, default=20.0)
    args = parser.parse_args(argv)
    failures: list[str] = []

    def check(label: str, condition: bool, detail: str = "") -> None:
        marker = "ok" if condition else "FAIL"
        print(f"  {marker:4} {label}{f' :: {detail}' if detail and not condition else ''}")
        if not condition:
            failures.append(label)

    try:
        projects = load_public_projects()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL public project manifest :: {exc}")
        return 1

    check("built frontend exists", DIST_INDEX.is_file(), "run `make forensic-workbench-build`")
    if not DIST_INDEX.is_file():
        return 1

    hidden = next(
        (
            path.name
            for path in sorted((REPO / "projects").iterdir())
            if path.is_dir() and SLUG_RE.fullmatch(path.name) and path.name not in projects
        ),
        "",
    )
    check("hidden-project canary exists", bool(hidden), "release smoke needs one unlisted local project")
    if not hidden:
        return 1

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(REPO / "src"), str(REPO), env.get("PYTHONPATH", "")])
    command = [
        sys.executable,
        str(SERVER),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--project-scope",
        "public",
    ]
    process = subprocess.Popen(
        command,
        cwd=REPO,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        if not wait_for_server(base, process, args.startup_timeout):
            stop_process(process)
            output = process.stdout.read() if process.stdout else ""
            print(f"FAIL public server startup\n{output[-2000:]}")
            return 1

        status_code, headers, status = request_json(
            base,
            "/api/status",
            origin="https://untrusted.example",
        )
        check("public server reports ready", status_code == 200 and status.get("ok") is True)
        check(
            "server is in public project scope",
            (status.get("project_visibility") or {}).get("scope") == "public",
        )
        allowed_origin = headers.get("Access-Control-Allow-Origin", "")
        check(
            "cross-origin browser writes stay local-only",
            allowed_origin in {"http://127.0.0.1:5174", "http://localhost:5174"},
            allowed_origin,
        )

        index_status, index_html = request_text(base, "/")
        check("built app is served on the API origin", index_status == 200 and 'id="root"' in index_html)

        project_status, _, project_index = request_json(base, "/api/projects")
        disclosed = {
            str(row.get("project") or "")
            for key in ("projects", "project_folders")
            for row in (project_index.get(key) or [])
            if isinstance(row, dict) and row.get("project")
        }
        check("public inventory loads", project_status == 200 and project_index.get("ok") is True)
        check("public inventory matches the manifest", disclosed == set(projects), f"saw {sorted(disclosed)}")

        openable = [row for row in project_index.get("projects") or [] if isinstance(row, dict)]
        check("at least one public project opens", bool(openable))
        if openable:
            project = urllib.parse.quote(str(openable[0].get("project") or ""), safe="")
            allowed_status, _, allowed_payload = request_json(base, f"/api/snapshot?project={project}")
            check("public project snapshot loads", allowed_status == 200 and allowed_payload.get("ok") is True)

        hidden_slug = urllib.parse.quote(hidden, safe="")
        hidden_status, _, hidden_payload = request_json(base, f"/api/snapshot?project={hidden_slug}")
        hidden_error = str(hidden_payload.get("error") or "")
        check(
            "unlisted project reads are refused",
            hidden_status == 400 and hidden_error == "project is not available in this Workbench",
            hidden_error,
        )
        file_status, _, file_payload = request_json(
            base,
            f"/api/file?path={urllib.parse.quote(f'projects/{hidden}/thesis.md', safe='')}",
        )
        check(
            "unlisted project file previews are refused",
            file_status == 400 and file_payload.get("error") == "project is not available in this Workbench",
            str(file_payload.get("error") or ""),
        )
        write_status, _, write_payload = request_json(
            base,
            "/api/source-edit",
            method="POST",
            body={"project": hidden, "relative_raw_path": "raw/noop.md", "body": "must not write"},
        )
        check(
            "unlisted project writes are refused before dispatch",
            write_status == 400 and write_payload.get("error") == "project is not available in this Workbench",
            str(write_payload.get("error") or ""),
        )
    finally:
        stop_process(process)

    print(f"\n{'PASS' if not failures else 'FAIL'} Workbench release smoke ({len(failures)} failure(s))")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
