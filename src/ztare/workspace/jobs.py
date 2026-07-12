"""Durable, provider-neutral command jobs for Workbench long-running actions."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import signal


SCHEMA = "ztare-workbench-job-v1"
TERMINAL = {"succeeded", "failed", "canceled", "interrupted"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_dir(root: Path, job_id: str) -> Path:
    return root / job_id


def _write(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def read_job(root: Path, job_id: str) -> dict:
    path = _job_dir(root, job_id) / "job.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") == "running":
        pid = int(payload.get("worker_pid") or 0)
        try:
            alive = pid > 0 and os.kill(pid, 0) is None
        except (OSError, ValueError):
            alive = False
        if not alive:
            payload.update(status="interrupted", finished_at=_now(), interruption="worker exited without a terminal receipt")
            try:
                _write(path, payload)
            except OSError:
                pass
    for stream in ("stdout", "stderr"):
        log = _job_dir(root, job_id) / f"{stream}.log"
        payload[f"{stream}_tail"] = log.read_text(encoding="utf-8", errors="replace")[-8000:] if log.is_file() else ""
    return payload


def cancel_job(root: Path, job_id: str) -> dict:
    path = _job_dir(root, job_id) / "job.json"
    payload = read_job(root, job_id)
    if payload.get("status") in TERMINAL:
        return payload
    pid = int(payload.get("worker_pid") or 0)
    if pid > 0:
        try:
            # The worker starts a fresh session; terminate its process group so a solver/Lean child cannot
            # continue after the Workbench has recorded cancellation.
            os.killpg(pid, signal.SIGTERM)
        except OSError:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
    payload.update(status="canceled", finished_at=_now(), cancellation="canceled by Workbench")
    _write(path, payload)
    return payload


def list_jobs(root: Path, *, project: str = "", limit: int = 20) -> list[dict]:
    if not root.is_dir():
        return []
    rows = []
    for path in root.iterdir():
        try:
            row = read_job(root, path.name)
        except (OSError, ValueError):
            continue
        if not project or row.get("project") == project:
            rows.append(row)
    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return rows[:limit]


def launch_job(*, root: Path, command: list[str], cwd: Path, env: dict[str, str], kind: str,
               project: str = "", label: str = "", context: dict | None = None) -> dict:
    job_id = uuid.uuid4().hex[:16]
    directory = _job_dir(root, job_id)
    directory.mkdir(parents=True, exist_ok=False)
    payload = {
        "schema": SCHEMA, "id": job_id, "kind": kind, "project": project, "label": label or kind,
        "status": "queued", "created_at": _now(), "started_at": None, "finished_at": None,
        "returncode": None, "command": command, "cwd": str(cwd), "context": context or {},
    }
    _write(directory / "job.json", payload)
    spec = {"command": command, "cwd": str(cwd), "env": env}
    _write(directory / "spec.json", spec)
    worker = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "run", str(root), job_id],
        cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    payload["worker_pid"] = worker.pid
    return payload


def run_job(root: Path, job_id: str) -> int:
    directory = _job_dir(root, job_id)
    state = read_job(root, job_id)
    spec = json.loads((directory / "spec.json").read_text(encoding="utf-8"))
    state.update(status="running", started_at=_now(), worker_pid=os.getpid())
    _write(directory / "job.json", state)
    with (directory / "stdout.log").open("w", encoding="utf-8") as stdout, \
         (directory / "stderr.log").open("w", encoding="utf-8") as stderr:
        proc = subprocess.run(spec["command"], cwd=spec["cwd"], env=spec["env"], stdout=stdout, stderr=stderr, check=False)
    state.update(status="succeeded" if proc.returncode == 0 else "failed", returncode=proc.returncode,
                 finished_at=_now())
    _write(directory / "job.json", state)
    return proc.returncode


if __name__ == "__main__" and len(sys.argv) == 4 and sys.argv[1] == "run":
    raise SystemExit(run_job(Path(sys.argv[2]), sys.argv[3]))
