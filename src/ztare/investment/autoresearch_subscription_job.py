"""Durable subscription-only autoresearch project jobs."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.leanmill import work_queue


AUTORESEARCH_PROJECT_JOB_KIND = "jaggedthoughts_autoresearch_project"
AUTORESEARCH_PROJECT_JOB_SCHEMA = "jaggedthoughts-autoresearch-project-job-v1"
AUTORESEARCH_PROJECT_REQUEST_SCHEMA = "jaggedthoughts-autoresearch-project-request-v1"


class AutoresearchProjectSuperseded(ValueError):
    """The frozen request no longer names the current project inputs."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _project_inputs(repo: Path, project: str, rubric: str) -> dict[str, Any]:
    project_root = (repo / "projects" / project).resolve()
    rubric_path = (repo / "rubrics" / f"{rubric}.json").resolve()
    project_root.relative_to(repo / "projects")
    rubric_path.relative_to(repo / "rubrics")
    files = {
        "evidence_receipt": project_root / "evidence_source_receipt.json",
        "candidate_seed": project_root / "test_model.py",
        "gate_harness": project_root / "gate_harness.py",
        "rubric": rubric_path,
    }
    missing = [name for name, path in files.items() if not path.is_file()]
    if missing:
        raise ValueError(f"autoresearch project inputs are missing: {missing}")
    return {
        "project_root": project_root,
        "rubric_path": rubric_path,
        "file_sha256": {name: _sha256(path) for name, path in files.items()},
    }


def validate_autoresearch_project_request(request: Mapping[str, Any]) -> dict[str, Any]:
    if request.get("schema") != AUTORESEARCH_PROJECT_REQUEST_SCHEMA:
        raise ValueError("unsupported autoresearch project request schema")
    declared = str(request.get("request_sha256") or "")
    body = {key: value for key, value in request.items() if key != "request_sha256"}
    if declared != stable_sha256(body):
        raise ValueError("autoresearch project request content hash mismatch")
    if request.get("runtime") != "codex" or request.get("transport") != "operator_subscription_cli":
        raise ValueError("autoresearch project jobs require the Codex subscription runtime")
    if int(request.get("iters") or 0) != 1:
        raise ValueError("autoresearch project jobs are bounded to one iteration")
    current = _project_inputs(_repo_root(), str(request["project"]), str(request["rubric"]))
    if request.get("input_file_sha256") != current["file_sha256"]:
        raise AutoresearchProjectSuperseded(
            "autoresearch project inputs changed after the request was frozen"
        )
    return current


def enqueue_autoresearch_project_job(
    workspace: str | Path, *, project: str, rubric: str,
    max_attempts: int = 3, research_trigger: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Freeze and enqueue one Codex-subscription Newton iteration."""
    root = Path(workspace).expanduser().resolve()
    inputs = _project_inputs(_repo_root(), project, rubric)
    body = {
        "schema": AUTORESEARCH_PROJECT_REQUEST_SCHEMA,
        "request_id": f"autoresearch:{project}:{inputs['file_sha256']['evidence_receipt'][:20]}",
        "created_at": _utc_now(),
        "project": project,
        "rubric": rubric,
        "iters": 1,
        "mutator_model": "gpt-5.6-sol",
        "judge_model": "gpt-5.6-sol",
        "runtime": "codex",
        "transport": "operator_subscription_cli",
        "input_file_sha256": inputs["file_sha256"],
        "expected_subscription_dispatches": 2,
        "expected_exit": "deterministic_gate_result_or_typed_failure",
        "research_trigger": dict(research_trigger or {}),
        "signal_authority": False,
        "capital_authority": False,
    }
    request = {**body, "request_sha256": stable_sha256(body)}
    request_path = (
        root / "research_jobs" / "autoresearch" / "requests"
        / f"{request['request_sha256']}.json"
    )
    _write_json(request_path, request)
    work_id = f"investment-autoresearch:{request['request_sha256'][:24]}"
    job_body = {
        "schema": AUTORESEARCH_PROJECT_JOB_SCHEMA,
        "work_id": work_id,
        "request_sha256": request["request_sha256"],
        "request_path": request_path.relative_to(root).as_posix(),
        "project": project,
        "stage": "queued",
        "required_capability": "subscription_autoresearch",
        "expected_exit": request["expected_exit"],
        "research_trigger": dict(request.get("research_trigger") or {}),
        "signal_authority": False,
        "capital_authority": False,
    }
    job = {**job_body, "job_sha256": stable_sha256(job_body)}
    connection = work_queue.connect(str(root / "state" / "research_jobs.sqlite3"))
    try:
        work_queue.enqueue(
            connection, kind=AUTORESEARCH_PROJECT_JOB_KIND, priority=875_000,
            max_attempts=max_attempts, payload=job,
        )
        connection.execute(
            "UPDATE work_items SET required_capability=? WHERE work_id=?",
            ("subscription_autoresearch", work_id),
        )
        connection.commit()
        work_queue.append_event(
            str(root / "research_jobs" / "agent" / "events.jsonl"),
            {"event_type": "investment_autoresearch_project_enqueued", "payload": job},
        )
    finally:
        connection.close()
    return {
        "schema": "jaggedthoughts-autoresearch-project-enqueue-v1",
        "status": "queued", "work_id": work_id,
        "request_path": request_path.relative_to(root).as_posix(),
        "request_sha256": request["request_sha256"],
        "research_trigger_sha256": (
            stable_sha256(request["research_trigger"])
            if request["research_trigger"] else None
        ),
        "transport": request["transport"],
        "capital_authority": False,
    }


def subscription_autoresearch_command(request: Mapping[str, Any]) -> list[str]:
    return [
        str(_repo_root() / "venv" / "bin" / "ztare"),
        "autoresearch", "run",
        "--project", str(request["project"]),
        "--rubric", str(request["rubric"]),
        "--iters", "1",
        "--mutator", str(request["mutator_model"]),
        "--judge", str(request["judge_model"]),
        "--agent-mutator", "--agent-judge", "--agent-runtime", "codex",
    ]


def run_autoresearch_project_job(
    workspace: str | Path, *, request: Mapping[str, Any], attempt: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    """Execute a frozen request through Codex login, with API-key routes removed."""
    root = Path(workspace).expanduser().resolve()
    inputs = validate_autoresearch_project_request(request)
    artifact_root = (
        root / "research_jobs" / "agent" / "autoresearch_runs"
        / str(request["request_sha256"]) / f"attempt-{max(1, attempt):03d}"
    )
    artifact_root.mkdir(parents=True, exist_ok=True)
    started_epoch = time.time()
    for offset, role in enumerate(("mutator", "judge")):
        _write_json(artifact_root / f"{offset:03d}.{role}.dispatch.json", {
            "schema": "jaggedthoughts-subscription-dispatch-v1",
            "request_sha256": request["request_sha256"],
            "role": role,
            "runtime": "codex",
            "transport": "operator_subscription_cli",
            "started_at_epoch": started_epoch,
        })
    child_env = os.environ.copy()
    for name in (
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
        "OPENROUTER_API_KEY", "CODEX_API_KEY",
    ):
        child_env.pop(name, None)
    command = subscription_autoresearch_command(request)
    completed = subprocess.run(
        command, cwd=_repo_root(), env=child_env, text=True,
        capture_output=True, timeout=timeout_seconds, check=False,
    )
    (artifact_root / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (artifact_root / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    output_files = {}
    for name in ("latest_eval_results.json", "latest_gate_results.json", "test_model.py"):
        path = inputs["project_root"] / name
        if path.is_file():
            output_files[name] = _sha256(path)
    result_body = {
        "schema": "jaggedthoughts-autoresearch-project-result-v1",
        "request_sha256": request["request_sha256"],
        "completed_at": _utc_now(),
        "returncode": completed.returncode,
        "status": "completed" if completed.returncode == 0 else "typed_failure",
        "command": command,
        "transport": "operator_subscription_cli",
        "api_key_environment_removed": True,
        "output_file_sha256": output_files,
        "artifact_path": artifact_root.relative_to(root).as_posix(),
        "signal_authority": False,
        "capital_authority": False,
    }
    result = {**result_body, "result_sha256": stable_sha256(result_body)}
    _write_json(artifact_root / "result.json", result)
    return result


__all__ = [
    "AUTORESEARCH_PROJECT_JOB_KIND", "AUTORESEARCH_PROJECT_JOB_SCHEMA",
    "AUTORESEARCH_PROJECT_REQUEST_SCHEMA", "AutoresearchProjectSuperseded",
    "enqueue_autoresearch_project_job",
    "run_autoresearch_project_job", "subscription_autoresearch_command",
    "validate_autoresearch_project_request",
]
