"""LeanMill Workbench launch actions.

This module is the shared boundary between the browser, CLI wrappers, and the
existing LeanMill solver commands. It starts long-running work as file-backed
jobs so the UI can launch work without blocking on a proof search.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ACTION_SCHEMA = "ztare-leanmill-workbench-action-v1"
JOB_SCHEMA = "ztare-leanmill-workbench-job-v1"
HISTORY_SCHEMA = "ztare-leanmill-workbench-job-history-v1"
REPO = Path(__file__).resolve().parents[3]
PROJECT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,120}$")
NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_'.]*$")
MODE_CHOICES = {"cascade", "dag_search"}
AXIOM_PACK_TRIAL_PREPARATION_SCHEMA = "leanmill.axiom_pack_trial_preparation.v1"


# Storage is the shared common provider (S3/DB-swappable). Aliased to the historical names so the type hints
# (`storage: ActionStorage`) and constructor (`FileActionStorage(repo)`) below are unchanged — and the
# duplicated resolve/write_text/append_jsonl bodies (previously shared with workbench_target) now live in ONE
# place. append_jsonl formatting is byte-identical (sort_keys=True).
from ztare.common.storage import FileStorage as FileActionStorage  # noqa: E402
from ztare.common.storage import StorageProvider as ActionStorage  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_ref_bytes(data: bytes) -> str:
    return "sha256:" + sha256_bytes(data)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def job_root(*, repo: Path = REPO) -> Path:
    return repo / "analytics" / "public" / "leanmill" / "workbench" / "jobs"


def history_path(*, repo: Path = REPO) -> Path:
    return repo / "analytics" / "public" / "leanmill" / "workbench" / "leanmill_action_history.jsonl"


def latest_path(*, repo: Path = REPO) -> Path:
    return repo / "analytics" / "public" / "leanmill" / "workbench" / "latest_leanmill_action.json"


def normalize_project(raw: Any) -> str:
    project = str(raw or "").strip()
    if project and not PROJECT_RE.fullmatch(project):
        raise ValueError("project must use letters, numbers, underscores, or hyphens")
    return project


def normalize_target_name(raw: Any) -> str:
    name = str(raw or "").strip()
    if not name:
        raise ValueError("target name is required")
    if not NAME_RE.fullmatch(name):
        raise ValueError("target name must look like a Lean declaration name")
    return name


def repo_env(repo: Path) -> dict[str, str]:
    env = os.environ.copy()
    src = str((repo / "src").resolve())
    current = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src if not current else f"{src}{os.pathsep}{current}"
    return env


def project_leanmill_root(project: str, *, repo: Path = REPO) -> Path:
    return repo / "projects" / project / "leanmill"


def axiom_pack_trial_root(*, project: str = "", repo: Path = REPO) -> Path:
    if project:
        return project_leanmill_root(project, repo=repo) / "axiom_pack_trials"
    return repo / "analytics" / "public" / "leanmill" / "workbench" / "axiom_pack_trials"


def action_paths(action: str, *, project: str = "", repo: Path = REPO) -> dict[str, Path]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    raw = f"{action}:{project}:{stamp}:{os.getpid()}".encode("utf-8")
    job_id = f"lm_{stamp}_{sha256_bytes(raw)[:10]}"
    root = project_leanmill_root(project, repo=repo) / "jobs" if project else job_root(repo=repo)
    return {
        "root": root,
        "job": root / f"{job_id}.json",
        "result": root / f"{job_id}_result.json",
        "stdout": root / f"{job_id}.stdout.log",
        "stderr": root / f"{job_id}.stderr.log",
    }


def latest_jobs(*, repo: Path = REPO, limit: int = 8) -> list[dict[str, Any]]:
    root = job_root(repo=repo)
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("lm_*.json"), reverse=True):
        if path.name.endswith("_result.json"):
            continue
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(row, dict):
                rows.append(row)
        except Exception:
            continue
        if len(rows) >= limit:
            break
    return rows


def _base_job(action: str, request: dict[str, Any], *, repo: Path, storage: ActionStorage) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ValueError("LeanMill action request must be an object")
    project = normalize_project(request.get("project"))
    paths = action_paths(action, project=project, repo=repo)
    return {
        "schema": JOB_SCHEMA,
        "action": action,
        "project": project,
        "created_at": utc_now(),
        "status": "preview",
        "paths": {key: storage.rel(path) for key, path in paths.items() if key != "root"},
        "storage": storage.metadata(),
    }


def notes_job(request: dict[str, Any], *, repo: Path, storage: ActionStorage) -> dict[str, Any]:
    job = _base_job("autoformalize_notes", request, repo=repo, storage=storage)
    notes_path_raw = str(request.get("notes_path") or request.get("target_path") or "").strip()
    if not notes_path_raw:
        raise ValueError("notes_path is required")
    notes_path = storage.resolve(notes_path_raw)
    if not notes_path.exists():
        raise ValueError(f"notes file not found: {storage.rel(notes_path)}")
    if not notes_path.is_file():
        raise ValueError(f"notes path is not a file: {storage.rel(notes_path)}")
    timeout_s = int(request.get("timeout_s") or request.get("timeout") or 0)
    if timeout_s < 0:
        raise ValueError("timeout_s must be non-negative")
    command = [
        sys.executable,
        "-m",
        "src.ztare.cli",
        "leanmill",
        "autoformalize-notes",
        storage.rel(notes_path),
    ]
    job.update(
        {
            "label": "Autoformalize from notes",
            "notes_path": storage.rel(notes_path),
            "notes_sha256": sha256_bytes(storage.read_bytes(notes_path)),
            "expected_artifact": storage.rel(notes_path.with_suffix(".autoformalize_result.json")),
            "timeout_s": timeout_s,
            "command": command,
        }
    )
    return job


def adhoc_job(request: dict[str, Any], *, repo: Path, storage: ActionStorage) -> dict[str, Any]:
    job = _base_job("solve_adhoc", request, repo=repo, storage=storage)
    target_name = normalize_target_name(request.get("target_name") or request.get("target"))
    source_raw = str(request.get("source_file") or "").strip()
    if not source_raw:
        raise ValueError("source_file is required")
    source_path = storage.resolve(source_raw)
    if not source_path.exists() or not source_path.is_file():
        raise ValueError(f"source file not found: {storage.rel(source_path)}")
    mode = str(request.get("mode") or "dag_search").strip()
    if mode not in MODE_CHOICES:
        raise ValueError(f"mode must be one of {sorted(MODE_CHOICES)}")
    timeout_s = int(request.get("timeout_s") or request.get("timeout") or 500)
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    command = [
        sys.executable,
        "-m",
        "src.ztare.cli",
        "leanmill",
        "solve-adhoc",
        "--target",
        target_name,
        "--source-file",
        storage.rel(source_path),
        "--mode",
        mode,
        "--timeout",
        str(timeout_s),
    ]
    provider = str(request.get("provider") or "").strip()
    if provider:
        command.extend(["--provider", provider])
    goal = str(request.get("goal") or "").strip()
    if goal:
        command.extend(["--goal", goal])
    substrate = str(request.get("substrate") or "").strip()
    if substrate:
        command.extend(["--substrate", storage.rel(storage.resolve(substrate))])
    notes_path_raw = str(request.get("notes_path") or "").strip()
    if notes_path_raw:
        notes_path = storage.resolve(notes_path_raw)
        if not notes_path.exists() or not notes_path.is_file():
            raise ValueError(f"notes file not found: {storage.rel(notes_path)}")
        command.extend(["--notes", storage.rel(notes_path)])
        job["notes_path"] = storage.rel(notes_path)
        job["notes_sha256"] = sha256_bytes(storage.read_bytes(notes_path))
    job.update(
        {
            "label": "Solve ad hoc target",
            "target_name": target_name,
            "source_file": storage.rel(source_path),
            "source_sha256": sha256_bytes(storage.read_bytes(source_path)),
            "mode": mode,
            "timeout_s": timeout_s,
            "provider": provider,
            "goal": goal,
            "command": command,
        }
    )
    return job


def ratify_job(request: dict[str, Any], *, repo: Path, storage: ActionStorage) -> dict[str, Any]:
    """Kernel-ratify a finished Lean proof — L1 compile + L2 axiom-allowlist + L3 anti-laundering — as a
    background job (proofs are slow, so it must not block the request). Delegates to the canonical
    `proof-audit` CLI; the receipt lands in `expected_artifact`. Read-only: grants NO proof credit, only a
    verdict."""
    job = _base_job("proof_audit", request, repo=repo, storage=storage)
    source_raw = str(request.get("source_file") or request.get("target") or "").strip()
    if not source_raw:
        raise ValueError("source_file is required")
    source_path = storage.resolve(source_raw)
    if not source_path.exists() or not source_path.is_file():
        raise ValueError(f"source file not found: {storage.rel(source_path)}")
    if source_path.suffix != ".lean":
        raise ValueError("ratify target must be a .lean file")
    # --target-name is optional for proof-audit (omit ⇒ audit the whole file's decls); only normalize if given.
    target_name_raw = str(request.get("target_name") or "").strip()
    target_name = normalize_target_name(target_name_raw) if target_name_raw else ""
    audit_timeout_s = int(request.get("timeout_s") or request.get("timeout") or 300)
    if audit_timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    receipt_rel = storage.rel(source_path.with_suffix(".proof_audit_receipt.json"))
    command = [
        sys.executable, "-m", "src.ztare.cli", "leanmill", "proof-audit",
        "--target", storage.rel(source_path),
        "--out", receipt_rel,
        "--timeout-s", str(audit_timeout_s),
    ]
    if target_name:
        command.extend(["--target-name", target_name])
    job.update(
        {
            "label": "Ratify a proof",
            "target_name": target_name,
            "source_file": storage.rel(source_path),
            "source_sha256": sha256_bytes(storage.read_bytes(source_path)),
            # outer subprocess kill runs BEYOND proof-audit's own --timeout-s so the audit finishes cleanly.
            "timeout_s": audit_timeout_s + 60,
            "audit_timeout_s": audit_timeout_s,
            "expected_artifact": receipt_rel,
            "command": command,
        }
    )
    return job


def campaign_run_job(request: dict[str, Any], *, repo: Path, storage: ActionStorage) -> dict[str, Any]:
    """Launch a LeanMill campaign (formalize or AxiomPack frontier) via the existing
    `ztare.leanmill.cli campaign` entry point — the SAME orchestration `arc3_play_loop.py` already shells
    out to. This job only tracks whether the background process is alive; campaign STATE (status, budget,
    journal) lives entirely in the attempt_dir the CLI writes, read back through
    `frontier_campaign_actions.frontier_campaign_status` — never duplicated here."""
    job = _base_job("campaign_run", request, repo=repo, storage=storage)
    blueprint_raw = str(request.get("blueprint") or "").strip()
    if not blueprint_raw:
        raise ValueError("blueprint is required")
    blueprint_path = storage.resolve(blueprint_raw)
    if not blueprint_path.exists() or not blueprint_path.is_file():
        raise ValueError(f"blueprint not found: {storage.rel(blueprint_path)}")
    command = [
        sys.executable, "-m", "ztare.leanmill.cli", "campaign", storage.rel(blueprint_path),
    ]
    job.update(
        {
            "label": "Run a LeanMill campaign",
            "blueprint_path": storage.rel(blueprint_path),
            "blueprint_sha256": sha256_bytes(storage.read_bytes(blueprint_path)),
            # ponytail: 0 = no outer kill. The campaign's OWN exploration_budget wall-clock is the real
            # cap (GP-251 §13.2) — killing the wrapper subprocess early would skip its BudgetStopReceipt
            # and journal finalization, which is worse than letting it run to its own stop condition.
            "timeout_s": 0,
            "command": command,
        }
    )
    return job


def _receipt_bundle(receipt_bundle_bytes: bytes) -> list[dict[str, Any]]:
    from ztare.leanmill.contracts.proof_gap import PROOF_GAP_RECEIPT_BUNDLE_SCHEMA

    try:
        bundle = json.loads(receipt_bundle_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("receipt bundle must be UTF-8 JSON") from exc
    if not isinstance(bundle, dict):
        raise ValueError("receipt bundle must be a JSON object")
    if set(bundle) != {"schema", "receipts"}:
        raise ValueError("receipt bundle fields must be exactly schema and receipts")
    if bundle.get("schema") != PROOF_GAP_RECEIPT_BUNDLE_SCHEMA:
        raise ValueError("unsupported proof-gap receipt bundle schema")
    receipts = bundle.get("receipts")
    if not isinstance(receipts, list):
        raise ValueError("receipt bundle receipts must be a list")
    if not all(isinstance(receipt, dict) for receipt in receipts):
        raise ValueError("every bundled receipt must be a JSON object")
    return receipts


def build_axiom_pack_trial_preparation(
    receipt_bundle_bytes: bytes,
    *,
    receipt_bundle_path: str,
) -> dict[str, Any]:
    """Replay repeated-gap eligibility into a deterministic quarantine packet."""

    from ztare.leanmill.contracts.proof_gap import evaluate_axiom_pack_escalation

    receipts = _receipt_bundle(receipt_bundle_bytes)
    evaluation = evaluate_axiom_pack_escalation(receipts)
    evaluation_digest = sha256_ref_bytes(canonical_json_bytes(evaluation))
    core = {
        "schema": AXIOM_PACK_TRIAL_PREPARATION_SCHEMA,
        "action": "prepare_axiom_pack_trial",
        "promotion_status": "quarantined",
        "routing_only": True,
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
        "theory_mutation_allowed": False,
        "family_inferred": False,
        "discovery_started": False,
        "receipt_bundle_path": receipt_bundle_path,
        "receipt_bundle_sha256": sha256_ref_bytes(receipt_bundle_bytes),
        "receipt_count": len(receipts),
        "evaluation": evaluation,
        "evaluation_packet_digest": evaluation_digest,
    }
    return {
        **core,
        "preparation_artifact_digest": sha256_ref_bytes(canonical_json_bytes(core)),
    }


def axiom_pack_trial_artifact_path(
    packet: dict[str, Any], *, project: str = "", repo: Path = REPO
) -> Path:
    project = normalize_project(project)
    digest = str(packet.get("preparation_artifact_digest") or "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("preparation packet has no canonical artifact digest")
    return axiom_pack_trial_root(project=project, repo=repo) / (
        f"axiom_pack_trial_{digest.removeprefix('sha256:')}.json"
    )


def prepare_axiom_pack_trial_file(
    receipt_bundle_path: str | Path,
    *,
    expected_input_sha256: str,
    project: str = "",
    repo: Path = REPO,
    storage: ActionStorage | None = None,
) -> dict[str, Any]:
    """Verify frozen input bytes, replay the evaluator, and write one packet."""

    storage = storage or FileActionStorage(repo)
    source = storage.resolve(receipt_bundle_path)
    if not source.exists() or not source.is_file():
        raise ValueError(f"receipt bundle not found: {storage.rel(source)}")
    raw = storage.read_bytes(source)
    observed_digest = sha256_ref_bytes(raw)
    if expected_input_sha256 != observed_digest:
        raise ValueError("receipt bundle bytes changed after action preview")
    packet = build_axiom_pack_trial_preparation(
        raw,
        receipt_bundle_path=storage.rel(source),
    )
    output = storage.resolve(axiom_pack_trial_artifact_path(packet, project=project, repo=repo))
    if source == output:
        raise ValueError("preparation output must not overwrite the receipt bundle")
    storage.write_text(output, json.dumps(packet, indent=2, sort_keys=True) + "\n")
    return packet


def axiom_pack_trial_job(
    request: dict[str, Any], *, repo: Path, storage: ActionStorage
) -> dict[str, Any]:
    job = _base_job("prepare_axiom_pack_trial", request, repo=repo, storage=storage)
    source_raw = str(
        request.get("receipt_bundle_path") or request.get("receipt_bundle") or ""
    ).strip()
    if not source_raw:
        raise ValueError("receipt_bundle_path is required")
    source = storage.resolve(source_raw)
    if not source.exists() or not source.is_file():
        raise ValueError(f"receipt bundle not found: {storage.rel(source)}")
    raw = storage.read_bytes(source)
    preview = build_axiom_pack_trial_preparation(
        raw,
        receipt_bundle_path=storage.rel(source),
    )
    input_digest = preview["receipt_bundle_sha256"]
    output = axiom_pack_trial_artifact_path(preview, project=job["project"], repo=repo)
    output_rel = storage.rel(output)
    command = [
        sys.executable,
        "-m",
        "ztare.leanmill.workbench_actions",
        "execute-axiom-pack-trial",
        storage.rel(source),
        "--expected-input-sha256",
        input_digest,
    ]
    if job["project"]:
        command.extend(["--project", job["project"]])
    job.update(
        {
            "label": "Prepare quarantined AxiomPack trial",
            "receipt_bundle_path": storage.rel(source),
            "receipt_bundle_sha256": input_digest,
            "receipt_count": preview["receipt_count"],
            "preview_eligible": preview["evaluation"]["eligible"],
            "preview_evaluation_packet_digest": preview["evaluation_packet_digest"],
            "expected_preparation_artifact_digest": preview["preparation_artifact_digest"],
            "expected_artifact": output_rel,
            "artifact_promotion_status": "quarantined",
            "timeout_s": 60,
            "command": command,
        }
    )
    return job


def build_job(action: str, request: dict[str, Any], *, repo: Path = REPO,
              storage: ActionStorage | None = None) -> dict[str, Any]:
    storage = storage or FileActionStorage(repo)
    if action == "autoformalize_notes":
        return notes_job(request, repo=repo, storage=storage)
    if action == "solve_adhoc":
        return adhoc_job(request, repo=repo, storage=storage)
    if action == "proof_audit":
        return ratify_job(request, repo=repo, storage=storage)
    if action == "prepare_axiom_pack_trial":
        return axiom_pack_trial_job(request, repo=repo, storage=storage)
    if action == "campaign_run":
        return campaign_run_job(request, repo=repo, storage=storage)
    raise ValueError(f"unknown LeanMill action: {action}")


def write_job(job: dict[str, Any], *, storage: ActionStorage) -> None:
    storage.write_text(job["paths"]["job"], json.dumps(job, indent=2, sort_keys=True) + "\n")


def append_history(job: dict[str, Any], *, repo: Path, storage: ActionStorage) -> dict[str, Any]:
    row = {
        "schema": HISTORY_SCHEMA,
        "recorded_at": utc_now(),
        "action": job.get("action"),
        "label": job.get("label"),
        "status": job.get("status"),
        "project": job.get("project"),
        "job_path": job.get("paths", {}).get("job"),
        "result_path": job.get("paths", {}).get("result"),
        "stdout_path": job.get("paths", {}).get("stdout"),
        "stderr_path": job.get("paths", {}).get("stderr"),
        "target_name": job.get("target_name", ""),
        "notes_path": job.get("notes_path", ""),
        "source_file": job.get("source_file", ""),
        "receipt_bundle_path": job.get("receipt_bundle_path", ""),
        "expected_artifact": job.get("expected_artifact", ""),
    }
    storage.append_jsonl(history_path(repo=repo), row)
    storage.write_text(latest_path(repo=repo), json.dumps(row, indent=2, sort_keys=True) + "\n")
    return row


def start_action(action: str, request: dict[str, Any], *, repo: Path = REPO,
                 storage: ActionStorage | None = None) -> dict[str, Any]:
    storage = storage or FileActionStorage(repo)
    confirmed = request.get("confirmed") is True
    job = build_job(action, request, repo=repo, storage=storage)
    job["requires_confirmation"] = not confirmed
    if not confirmed:
        return {
            "schema": ACTION_SCHEMA,
            "ok": True,
            "status": "needs_confirmation",
            "accepted": False,
            "requires_confirmation": True,
            "job": job,
            "write_boundary": action_write_boundary(job, repo=repo, storage=storage),
        }
    job["status"] = "starting"
    write_job(job, storage=storage)
    runner_cmd = [sys.executable, "-m", "ztare.leanmill.workbench_actions", "run-job", job["paths"]["job"]]
    process = subprocess.Popen(
        runner_cmd,
        cwd=str(repo),
        env=repo_env(repo),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    job["status"] = "running"
    job["started_at"] = utc_now()
    job["pid"] = process.pid
    job["runner_command"] = runner_cmd
    write_job(job, storage=storage)
    history = append_history(job, repo=repo, storage=storage)
    return {
        "schema": ACTION_SCHEMA,
        "ok": True,
        "status": "started",
        "accepted": True,
        "requires_confirmation": False,
        "job": job,
        "history": history,
        "write_boundary": action_write_boundary(job, repo=repo, storage=storage),
    }


def action_write_boundary(job: dict[str, Any], *, repo: Path = REPO, storage: ActionStorage) -> dict[str, Any]:
    paths = job.get("paths", {})
    write_paths = [str(paths.get(key) or "") for key in ("job", "result", "stdout", "stderr") if paths.get(key)]
    write_paths.extend([
        storage.rel(history_path(repo=repo)),
        storage.rel(latest_path(repo=repo)),
    ])
    if job.get("expected_artifact"):
        write_paths.append(str(job["expected_artifact"]))
    return {
        "writes_repo_files": True,
        "writes_project_files": bool(job.get("project")),
        "browser_writes": False,
        "storage": storage.metadata(),
        "write_paths": write_paths,
        "primary_path": paths.get("job"),
        "result_path": paths.get("result"),
        "stdout_path": paths.get("stdout"),
        "stderr_path": paths.get("stderr"),
        "domain_artifact_path": job.get("expected_artifact", ""),
    }


def run_job_file(job_file: str | Path, *, repo: Path = REPO,
                 storage: ActionStorage | None = None) -> int:
    storage = storage or FileActionStorage(repo)
    job_path = storage.resolve(job_file)
    job = json.loads(job_path.read_text(encoding="utf-8"))
    if not isinstance(job, dict):
        raise ValueError("job file must contain an object")
    stdout_path = storage.resolve(job["paths"]["stdout"])
    stderr_path = storage.resolve(job["paths"]["stderr"])
    result_path = storage.resolve(job["paths"]["result"])
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    job["status"] = "running"
    job["runner_started_at"] = utc_now()
    write_job(job, storage=storage)
    started = datetime.now(timezone.utc)
    command = [str(part) for part in job.get("command") or []]
    timeout_s = int(job.get("timeout_s") or 0) or None
    result: dict[str, Any]
    try:
        completed = subprocess.run(
            command,
            cwd=str(repo),
            env=repo_env(repo),
            text=True,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
        stdout_path.write_text(completed.stdout or "", encoding="utf-8")
        stderr_path.write_text(completed.stderr or "", encoding="utf-8")
        status = "completed" if completed.returncode == 0 else "failed"
        result = {
            "schema": ACTION_SCHEMA,
            "ok": completed.returncode == 0,
            "status": status,
            "returncode": completed.returncode,
            "action": job.get("action"),
            "label": job.get("label"),
            "command": command,
            "started_at": started.isoformat(),
            "finished_at": utc_now(),
            "stdout_path": storage.rel(stdout_path),
            "stderr_path": storage.rel(stderr_path),
            "job_path": storage.rel(job_path),
            "artifact_path": job.get("expected_artifact", ""),
        }
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text(exc.stdout or "", encoding="utf-8")
        stderr_path.write_text(exc.stderr or "", encoding="utf-8")
        result = {
            "schema": ACTION_SCHEMA,
            "ok": False,
            "status": "timed_out",
            "returncode": None,
            "action": job.get("action"),
            "label": job.get("label"),
            "command": command,
            "started_at": started.isoformat(),
            "finished_at": utc_now(),
            "stdout_path": storage.rel(stdout_path),
            "stderr_path": storage.rel(stderr_path),
            "job_path": storage.rel(job_path),
            "error": f"timed out after {timeout_s}s",
            "artifact_path": job.get("expected_artifact", ""),
        }
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    job["status"] = str(result["status"])
    job["finished_at"] = result["finished_at"]
    job["returncode"] = result.get("returncode")
    job["result_path"] = storage.rel(result_path)
    write_job(job, storage=storage)
    append_history(job, repo=repo, storage=storage)
    return 0 if result.get("ok") else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ztare leanmill workbench-action",
        description="Start or inspect LeanMill Workbench actions.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    notes = sub.add_parser("autoformalize-notes", help="start autoformalization from a saved notes file")
    notes.add_argument("notes_path")
    notes.add_argument("--project", default="")
    notes.add_argument("--timeout", type=int, default=0, help="0 means use the solver's own wall-clock policy")
    notes.add_argument("--save", action="store_true", help="start the background job")
    notes.add_argument("--json", action="store_true")
    adhoc = sub.add_parser("solve-adhoc", help="start a governed proof attempt for one Lean target")
    adhoc.add_argument("--target", required=True)
    adhoc.add_argument("--source-file", required=True)
    adhoc.add_argument("--project", default="")
    adhoc.add_argument("--goal", default="")
    adhoc.add_argument("--provider", default="")
    adhoc.add_argument("--notes-path", default="")
    adhoc.add_argument("--substrate", default="")
    adhoc.add_argument("--mode", choices=sorted(MODE_CHOICES), default="dag_search")
    adhoc.add_argument("--timeout", type=int, default=500)
    adhoc.add_argument("--save", action="store_true", help="start the background job")
    adhoc.add_argument("--json", action="store_true")
    trial = sub.add_parser(
        "prepare-axiom-pack-trial",
        help="prepare a quarantined AxiomPack trial from proof-gap receipts",
    )
    trial.add_argument("receipt_bundle")
    trial.add_argument("--project", default="")
    trial.add_argument("--save", action="store_true", help="start the background preparation job")
    trial.add_argument("--json", action="store_true")
    execute_trial = sub.add_parser(
        "execute-axiom-pack-trial",
        help="execute a frozen AxiomPack preparation job",
    )
    execute_trial.add_argument("receipt_bundle")
    execute_trial.add_argument("--expected-input-sha256", required=True)
    execute_trial.add_argument("--project", default="")
    runner = sub.add_parser("run-job", help="run a saved job file")
    runner.add_argument("job_file")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "run-job":
        return run_job_file(args.job_file)
    if args.cmd == "execute-axiom-pack-trial":
        packet = prepare_axiom_pack_trial_file(
            args.receipt_bundle,
            expected_input_sha256=args.expected_input_sha256,
            project=args.project,
        )
        print(json.dumps(packet, indent=2, sort_keys=True))
        return 0
    if args.cmd == "autoformalize-notes":
        payload = start_action(
            "autoformalize_notes",
            {
                "project": args.project,
                "notes_path": args.notes_path,
                "timeout_s": args.timeout,
                "confirmed": args.save,
            },
        )
    elif args.cmd == "solve-adhoc":
        payload = start_action(
            "solve_adhoc",
            {
                "project": args.project,
                "target_name": args.target,
                "source_file": args.source_file,
                "goal": args.goal,
                "provider": args.provider,
                "notes_path": args.notes_path,
                "substrate": args.substrate,
                "mode": args.mode,
                "timeout_s": args.timeout,
                "confirmed": args.save,
            },
        )
    else:
        payload = start_action(
            "prepare_axiom_pack_trial",
            {
                "project": args.project,
                "receipt_bundle_path": args.receipt_bundle,
                "confirmed": args.save,
            },
        )
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        job = payload["job"]
        print(payload["status"])
        print(f"job: {job['paths']['job']}")
        print(f"result: {job['paths']['result']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
