"""Source/evidence actions shared by CLI and D4."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ztare.common.paths import REPO_ROOT
from ztare.workspace import workbench_settings
from ztare.workspace.project_brief import add_project_context, default_intake_for_project, validate_project_slug


SOURCE_ACTION_SCHEMA = "ztare-forensic-workbench-source-action-v1"
SOURCE_ACTION_RECEIPT_SCHEMA = "ztare-forensic-workbench-source-action-receipt-v1"

SOURCE_ACTIONS: dict[str, dict[str, Any]] = {
    "source_check": {
        "label": "Check files",
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
        "label": "Inspect evidence readiness",
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
    "evidence_prepare": {
        "label": "Prepare evidence",
        "command": [
            "make",
            "evidence-prepare",
            "PROJECT={project}",
            "MODEL={model}",
            "MODEL_FALLBACK={model_fallback}",
            "EVIDENCE_LLM_TIMEOUT={evidence_llm_timeout}",
            "EVIDENCE_LLM_RETRIES={evidence_llm_retries}",
        ],
        "display": (
            "make evidence-prepare PROJECT={project} MODEL={model} MODEL_FALLBACK={model_fallback} "
            "EVIDENCE_LLM_TIMEOUT={evidence_llm_timeout} EVIDENCE_LLM_RETRIES={evidence_llm_retries}"
        ),
        "timeout": 300,
        "writes": True,
        "requires_confirmation": True,
        "loads_workbench_env": True,
        "primary_path_template": "projects/{project}/evidence.txt",
        "receipt_path_template": "projects/{project}/compiled_evidence_provenance.json",
        "write_path_templates": [
            "projects/{project}/workspace/source_index.json",
            "projects/{project}/workspace/source_index_receipt.json",
            "projects/{project}/compiled_evidence_provenance.json",
            "projects/{project}/compiled_evidence_packet.json",
            "projects/{project}/compiled_evidence_replay_manifest.json",
            "projects/{project}/evidence.txt",
            "projects/{project}/workspace/forensic_workbench_source_actions.jsonl",
            "projects/{project}/workspace/forensic_workbench_latest_source_action.json",
        ],
    },
}


def repo_rel(path: Path, *, root: Path = REPO_ROOT) -> str:
    return Path(path).resolve().relative_to(root.resolve()).as_posix()


def _write_text(path: Path, text: str, storage: Any = None) -> None:
    if storage is not None and hasattr(storage, "write_text"):
        storage.write_text(path, text)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_bytes(path: Path, storage: Any = None) -> bytes:
    if storage is not None and hasattr(storage, "read_bytes"):
        return storage.read_bytes(path)
    return path.read_bytes()


def _append_jsonl(path: Path, row: dict[str, Any], storage: Any = None) -> None:
    if storage is not None and hasattr(storage, "append_jsonl"):
        storage.append_jsonl(path, row)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def command_context(project: str, rubric: str | None = None, *, root: Path = REPO_ROOT, storage: Any = None) -> dict[str, str]:
    values = workbench_settings.workbench_settings_values(root=root, storage=storage)
    auto_compile = values["ZTARE_WORKBENCH_AUTO_COMPILE"]
    return {
        "project": project,
        "rubric": rubric or project,
        "model": values["ZTARE_WORKBENCH_MODEL"],
        "model_fallback": values["ZTARE_WORKBENCH_MODEL_FALLBACK"],
        "evidence_llm_timeout": values["ZTARE_WORKBENCH_EVIDENCE_LLM_TIMEOUT"],
        "evidence_llm_retries": values["ZTARE_WORKBENCH_EVIDENCE_LLM_RETRIES"],
        "evidence_search_backend": values["ZTARE_EVIDENCE_SEARCH_BACKEND"],
        "fetch_severity": values["ZTARE_WORKBENCH_FETCH_SEVERITY"],
        "max_fetches": values["ZTARE_WORKBENCH_MAX_FETCHES"],
        "auto_compile": auto_compile,
    }


def empty_make_assignment(part: str) -> bool:
    return "=" in part and part.endswith("=") and part.split("=", 1)[0].replace("_", "").isalnum()


def command_from_template(parts: list[str], context: dict[str, str]) -> list[str]:
    command: list[str] = []
    for part in parts:
        formatted = str(part).format(**context)
        if formatted and not empty_make_assignment(formatted):
            command.append(formatted)
    return command


def display_command(parts: list[str]) -> str:
    return " ".join(str(part) for part in parts)


def source_action_write_paths(project: str, action: str) -> dict[str, Any]:
    spec = SOURCE_ACTIONS.get(action) or {}
    write_paths = [
        str(path).format(project=project, rubric=project)
        for path in spec.get("write_path_templates") or []
        if path
    ]
    receipt_path = next(
        (path for path in write_paths if "forensic_workbench_source_actions" in path),
        str(spec.get("receipt_path_template") or "").format(project=project, rubric=project),
    )
    latest_path = next((path for path in write_paths if "latest" in path.lower()), "")
    return {"write_paths": write_paths, "receipt_path": receipt_path, "latest_path": latest_path}


def file_sha256(path_value: Any, *, root: Path = REPO_ROOT, storage: Any = None) -> str:
    text = str(path_value or "").strip()
    if not text:
        return ""
    path = Path(text)
    if not path.is_absolute():
        path = root / path
    try:
        resolved = path.resolve()
        if not resolved.is_file() or root.resolve() not in resolved.parents:
            return ""
        return hashlib.sha256(_read_bytes(resolved, storage)).hexdigest()
    except (OSError, ValueError):
        return ""


def command_tail(text: str, *, root: Path = REPO_ROOT) -> str:
    return (text or "").replace(str(root.resolve()), ".")[-4000:]


def extract_last_json_object(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text or "")
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    best: tuple[int, dict[str, Any]] | None = None
    for index, char in enumerate(text or ""):
        if char != "{":
            continue
        try:
            payload, end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            absolute_end = index + end
            if best is None or absolute_end > best[0]:
                best = (absolute_end, payload)
    return best[1] if best else {}


def first_bound_artifact(receipt: dict[str, Any]) -> tuple[str, str]:
    for artifact in receipt.get("artifacts") or []:
        if isinstance(artifact, dict) and artifact.get("path"):
            return str(artifact.get("path") or ""), str(artifact.get("sha256") or "")
    return "", ""


def source_action_artifact_paths(parsed_output: dict[str, Any], *, root: Path = REPO_ROOT, storage: Any = None) -> tuple[str, str, str, str]:
    nested_receipt = parsed_output.get("receipt") if isinstance(parsed_output.get("receipt"), dict) else {}
    bound_artifact_path, bound_artifact_sha256 = first_bound_artifact(nested_receipt)
    source_receipt_path = str(
        parsed_output.get("source_index_receipt")
        or parsed_output.get("receipt_path")
        or parsed_output.get("path")
        or ""
    )
    source_path = str(
        parsed_output.get("source_index")
        or parsed_output.get("workspace_meta")
        or bound_artifact_path
        or parsed_output.get("provenance_path")
        or nested_receipt.get("provenance_path")
        or parsed_output.get("path")
        or ""
    )
    return (
        source_receipt_path,
        source_path,
        bound_artifact_sha256 or file_sha256(source_path, root=root, storage=storage),
        file_sha256(source_receipt_path, root=root, storage=storage),
    )


def run_command(command: list[str], *, root: Path, env: dict[str, str], timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=root,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return subprocess.CompletedProcess(
            args=command,
            returncode=124,
            stdout=stdout,
            stderr=(stderr + f"\ncommand timed out after {timeout}s").strip(),
        )


def run_source_action(
    *,
    project: str,
    action: str,
    rubric: str | None = None,
    intake: str | None = None,
    confirmed: bool = False,
    root: Path = REPO_ROOT,
    storage: Any = None,
    python_executable: str | None = None,
    context: dict[str, str] | None = None,
) -> dict[str, Any]:
    slug = validate_project_slug(project)
    spec = SOURCE_ACTIONS.get(action)
    if spec is None:
        raise ValueError(f"unknown file/evidence action: {action}")
    rubric = rubric or slug
    intake = intake or default_intake_for_project(slug)
    context = dict(context or command_context(slug, rubric, root=root, storage=storage))
    context.update({"project": slug, "rubric": rubric})
    if "command" in spec:
        command = command_from_template(list(spec["command"]), context)
        command_display = display_command(command)
    else:
        command_args = [str(part).format(**context) for part in spec["args"]]
        command = [python_executable or sys.executable, "-m", "src.ztare.cli", *command_args]
        command_display = str(spec["display"]).format(**context)
    effective_settings = {
        "model": context.get("model", ""),
        "model_fallback": context.get("model_fallback", ""),
        "evidence_llm_timeout": context.get("evidence_llm_timeout", ""),
        "evidence_llm_retries": context.get("evidence_llm_retries", ""),
        "evidence_search_backend": context.get("evidence_search_backend", ""),
    }
    requires_confirmation = bool(spec.get("requires_confirmation"))
    paths = source_action_write_paths(slug, action)
    if requires_confirmation and not confirmed:
        return {
            "schema": SOURCE_ACTION_SCHEMA,
            "served_from": "ztare_source_actions",
            "project": slug,
            "rubric": rubric,
            "intake": intake,
            "action": action,
            "label": str(spec["label"]),
            "writes": bool(spec["writes"]),
            "requires_confirmation": True,
            "status": "needs_confirmation",
            "command": command_display,
            "effective_settings": effective_settings,
            "returncode": None,
            "accepted": False,
            "ok": False,
            "stdout_tail": "",
            "stderr_tail": "",
            "parsed_output": {},
            "write_paths": paths["write_paths"],
            "receipt_path": paths["receipt_path"],
            "latest": paths["latest_path"],
        }
    env = workbench_settings.load_workbench_env(root=root, storage=storage) if spec.get("loads_workbench_env") else os.environ.copy()
    proc = run_command(command, root=root, env=env, timeout=int(spec["timeout"]))
    parsed_output = extract_last_json_object(proc.stdout)
    payload: dict[str, Any] = {
        "schema": SOURCE_ACTION_SCHEMA,
        "served_from": "ztare_source_actions",
        "project": slug,
        "rubric": rubric,
        "intake": intake,
        "action": action,
        "label": str(spec["label"]),
        "writes": bool(spec["writes"]),
        "requires_confirmation": requires_confirmation,
        "command": command_display,
        "effective_settings": effective_settings,
        "returncode": proc.returncode,
        "accepted": proc.returncode == 0,
        "ok": proc.returncode == 0,
        "stdout_tail": command_tail(proc.stdout, root=root),
        "stderr_tail": command_tail(proc.stderr, root=root),
        "parsed_output": parsed_output,
    }
    if not spec["writes"]:
        return payload
    source_receipt_path, source_path, source_sha256, source_receipt_sha256 = source_action_artifact_paths(
        parsed_output,
        root=root,
        storage=storage,
    )
    if not source_receipt_path and spec.get("receipt_path_template"):
        source_receipt_path = str(spec["receipt_path_template"]).format(project=slug, rubric=rubric)
        source_receipt_sha256 = file_sha256(source_receipt_path, root=root, storage=storage)
    if not source_path and spec.get("primary_path_template"):
        source_path = str(spec["primary_path_template"]).format(project=slug, rubric=rubric)
        source_sha256 = file_sha256(source_path, root=root, storage=storage)
    workspace = root.resolve() / "projects" / slug / "workspace"
    ledger_path = workspace / "forensic_workbench_source_actions.jsonl"
    latest_path = workspace / "forensic_workbench_latest_source_action.json"
    receipt = add_project_context(
        {
            "schema": SOURCE_ACTION_RECEIPT_SCHEMA,
            "applied_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "project": slug,
            "action": action,
            "label": str(spec["label"]),
            "command": command_display,
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
        project=slug,
        rubric=rubric,
        intake=intake,
    )
    _append_jsonl(ledger_path, receipt, storage)
    _write_text(latest_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n", storage)
    payload.update(
        {
            "receipt_path": repo_rel(ledger_path, root=root),
            "latest": repo_rel(latest_path, root=root),
            "receipt": receipt,
            "write_paths": [
                *paths["write_paths"],
                source_path,
                source_receipt_path,
                repo_rel(ledger_path, root=root),
                repo_rel(latest_path, root=root),
            ],
        }
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a Project Workbench source/evidence action.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--action", required=True, choices=sorted(SOURCE_ACTIONS))
    parser.add_argument("--rubric")
    parser.add_argument("--intake")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = run_source_action(
            project=args.project,
            action=args.action,
            rubric=args.rubric,
            intake=args.intake,
            confirmed=args.confirmed,
            root=args.repo,
        )
    except Exception as exc:  # noqa: BLE001 - concise CLI failure.
        print(f"ztare forensic-workbench source-action: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"{payload.get('label')}: {payload.get('status') or ('accepted' if payload.get('accepted') else 'failed')}")
        print(payload.get("command") or "")
        if payload.get("latest"):
            print(f"Receipt: {payload.get('latest')}")
    return 0 if payload.get("ok") or payload.get("status") == "needs_confirmation" else 1


if __name__ == "__main__":
    raise SystemExit(main())
