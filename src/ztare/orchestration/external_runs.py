"""Typed contract and registry helpers for external GPU/API runs.

This is the kernel-facing layer for launch metadata and durable run state.
Project-local launchers can stay project-specific, but they should emit and
update these records so later agents do not need shell-history archaeology.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ztare.common.paths import REPO_ROOT


EXTERNAL_RUNS_ROOT = REPO_ROOT / "ztare_workspace" / "external_runs"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


@dataclass(frozen=True)
class ExternalRunContract:
    run_id: str
    project_slug: str
    run_kind: str
    host: str
    remote_user: str
    remote_dir: str
    launcher_pid: int | None
    label_prefix: str
    launch_command: str
    result_files: list[str]
    artifact_files: list[str]
    progress_hint: str | None = None
    notification_topic: str | None = None
    notification_server: str | None = None
    local_results_root: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_utc: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExternalRunState:
    run_id: str
    status: str
    host: str
    project_slug: str
    run_kind: str
    launcher_pid: int | None
    latest_marker: str | None = None
    gpu_status: str | None = None
    local_results_dir: str | None = None
    summary_file: str | None = None
    artifact_bundle: str | None = None
    notes: str | None = None
    updated_utc: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def new_run_id(project_slug: str, run_kind: str) -> str:
    stem = f"{project_slug}-{run_kind}".replace("/", "-").replace("_", "-")
    return f"{stem}-{utc_now().replace(':', '').replace('-', '')}-{uuid.uuid4().hex[:8]}"


def run_dir(run_id: str) -> Path:
    return EXTERNAL_RUNS_ROOT / run_id


def write_contract(contract: ExternalRunContract) -> Path:
    path = run_dir(contract.run_id) / "contract.json"
    _atomic_write_json(path, contract.to_dict())
    return path


def write_state(state: ExternalRunState) -> Path:
    path = run_dir(state.run_id) / "state.json"
    _atomic_write_json(path, state.to_dict())
    return path


def append_event(run_id: str, *, event: str, payload: dict[str, Any] | None = None) -> Path:
    path = run_dir(run_id) / "events.jsonl"
    record = {
        "timestamp_utc": utc_now(),
        "event": event,
        "payload": payload or {},
    }
    _append_jsonl(path, record)
    return path


def register_run(contract: ExternalRunContract, initial_state: ExternalRunState) -> Path:
    write_contract(contract)
    write_state(initial_state)
    append_event(contract.run_id, event="registered", payload={"status": initial_state.status})
    return run_dir(contract.run_id)
