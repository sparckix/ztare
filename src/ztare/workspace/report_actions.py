"""Report-readiness actions shared by CLI and D4."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ztare.common.paths import REPO_ROOT
from ztare.workspace import workbench_settings
from ztare.workspace.project_brief import add_project_context, default_intake_for_project, validate_project_slug


REPORT_CONTRACT_REFRESH_RECEIPT_SCHEMA = "ztare-forensic-workbench-report-contract-refresh-receipt-v1"
REPORT_SYNTHESIS_SCHEMA = "ztare-forensic-workbench-report-synthesis-v1"
DEFAULT_RENDERER = "decision_brief"


def repo_rel(path: Path, *, root: Path = REPO_ROOT) -> str:
    return Path(path).resolve().relative_to(root.resolve()).as_posix()


def display_path(path_value: str | Path, *, root: Path = REPO_ROOT) -> str:
    path = Path(path_value)
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        try:
            return repo_rel(path, root=root)
        except ValueError:
            return str(path_value)


def _write_text(path: Path, text: str, storage: Any = None) -> None:
    if storage is not None and hasattr(storage, "write_text"):
        storage.write_text(path, text)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _append_jsonl(path: Path, row: dict[str, Any], storage: Any = None) -> None:
    if storage is not None and hasattr(storage, "append_jsonl"):
        storage.append_jsonl(path, row)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def _read_bytes(path: Path, storage: Any = None) -> bytes:
    if storage is not None and hasattr(storage, "read_bytes"):
        return storage.read_bytes(path)
    return path.read_bytes()


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


def report_model(*, root: Path = REPO_ROOT, storage: Any = None) -> str:
    values = workbench_settings.workbench_settings_values(root=root, storage=storage)
    return values["ZTARE_WORKBENCH_REPORT_MODEL"] or values["ZTARE_WORKBENCH_MODEL"]


def check_readiness_command(project: str, renderer: str, python_executable: str) -> tuple[list[str], str]:
    command = ["make", "synth-contract", f"PROJECT={project}", f"RENDERER={renderer}", f"PYTHON={python_executable}"]
    display = (
        "ztare forensic-workbench report-action "
        f"--project {project} --action check_readiness --renderer {renderer} --confirmed --json"
    )
    return command, display


def refresh_inputs_command(
    project: str,
    renderer: str,
    *,
    root: Path = REPO_ROOT,
    storage: Any = None,
    python_executable: str | None = None,
) -> tuple[list[str], str, str]:
    model = report_model(root=root, storage=storage)
    py = python_executable or sys.executable
    command = [py, "-m", "src.ztare.synthesis.synthesize", "--project", project, "--renderer-type", renderer]
    display_parts = ["python", "-m", "src.ztare.synthesis.synthesize", "--project", project, "--renderer-type", renderer]
    if model:
        command.extend(["--model", model])
        display_parts.extend(["--model", model])
    return command, " ".join(shlex.quote(part) for part in display_parts), model


def check_readiness_write_paths(project: str) -> list[str]:
    return [
        f"projects/{project}/synthesis/report_support_contract.json",
        f"projects/{project}/workspace/forensic_workbench_report_support_checks.jsonl",
        f"projects/{project}/workspace/forensic_workbench_latest_report_support_check.json",
    ]


def refresh_inputs_write_paths(project: str, renderer: str) -> list[str]:
    return [
        f"projects/{project}/synthesis/context.json",
        f"projects/{project}/synthesis/context.{renderer}.json",
        f"projects/{project}/synthesis/history_summary.json",
        f"projects/{project}/synthesis/ledger.json",
        f"projects/{project}/synthesis/brief.{renderer}.json",
        f"projects/{project}/synthesis/Report.{renderer}.candidate.md",
        f"projects/{project}/synthesis/qa.{renderer}.json",
        f"projects/{project}/synthesis/autoresearch_review_context.json",
        f"projects/{project}/synthesis/report_support_contract.json",
        f"projects/{project}/workspace/forensic_workbench_report_synthesis.jsonl",
        f"projects/{project}/workspace/forensic_workbench_latest_report_synthesis.json",
    ]


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


def run_report_action(
    *,
    project: str,
    action: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str = DEFAULT_RENDERER,
    confirmed: bool = False,
    root: Path = REPO_ROOT,
    storage: Any = None,
    python_executable: str | None = None,
    instructions: str = "",
) -> dict[str, Any]:
    slug = validate_project_slug(project)
    rubric = rubric or slug
    intake = intake or default_intake_for_project(slug)
    renderer = renderer or DEFAULT_RENDERER
    workspace = root.resolve() / "projects" / slug / "workspace"
    py = python_executable or sys.executable
    if action == "check_readiness":
        command, command_display = check_readiness_command(slug, renderer, py)
        write_paths = check_readiness_write_paths(slug)
        ledger_path = workspace / "forensic_workbench_report_support_checks.jsonl"
        latest_path = workspace / "forensic_workbench_latest_report_support_check.json"
        label = "Check report readiness"
        timeout = 180
        schema = REPORT_CONTRACT_REFRESH_RECEIPT_SCHEMA
        model = ""
    elif action == "refresh_inputs":
        command, command_display, model = refresh_inputs_command(
            slug,
            renderer,
            root=root,
            storage=storage,
            python_executable=py,
        )
        write_paths = refresh_inputs_write_paths(slug, renderer)
        ledger_path = workspace / "forensic_workbench_report_synthesis.jsonl"
        latest_path = workspace / "forensic_workbench_latest_report_synthesis.json"
        label = "Refresh report inputs"
        timeout = 900
        schema = REPORT_SYNTHESIS_SCHEMA
    else:
        raise ValueError("action must be check_readiness or refresh_inputs")
    if not confirmed:
        return {
            "schema": schema,
            "served_from": "ztare_report_actions",
            "project": slug,
            "rubric": rubric,
            "intake": intake,
            "renderer": renderer,
            "model": model,
            "action": action,
            "label": label,
            "command": command_display,
            "requires_confirmation": True,
            "writes": True,
            "accepted": False,
            "ok": True,
            "status": "needs_confirmation",
            "returncode": None,
            "stdout_tail": "",
            "stderr_tail": "",
            "write_paths": write_paths,
            "receipt_path": repo_rel(ledger_path, root=root),
            "latest": repo_rel(latest_path, root=root),
        }
    env = workbench_settings.load_workbench_env(root=root, storage=storage)
    if instructions.strip():
        # User direction for report synthesis — read by `ztare synth` (ZTARE_REPORT_INSTRUCTIONS).
        env["ZTARE_REPORT_INSTRUCTIONS"] = instructions.strip()
    proc = run_command(
        command,
        root=root,
        env=env,
        timeout=timeout,
    )
    parsed = extract_last_json_object(proc.stdout)
    if parsed.get("report_support_contract"):
        parsed = {
            **parsed,
            "report_support_contract": display_path(str(parsed.get("report_support_contract") or ""), root=root),
        }
    contract_path = str(parsed.get("report_support_contract") or f"projects/{slug}/synthesis/report_support_contract.json")
    status_reasons = parsed.get("status_reasons") if isinstance(parsed.get("status_reasons"), list) else []
    synthesis_input_binding = (
        parsed.get("synthesis_input_binding") if isinstance(parsed.get("synthesis_input_binding"), dict) else {}
    )
    receipt = add_project_context(
        {
            "schema": schema,
            "applied_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "project": slug,
            "command": command_display,
            "renderer": renderer,
            "returncode": proc.returncode,
            "accepted": proc.returncode == 0,
            "report_support_contract": contract_path,
            "report_support_sha256": file_sha256(contract_path, root=root, storage=storage),
            "status": str(parsed.get("status") or ""),
            "status_reasons": status_reasons,
            "synthesis_input_binding": synthesis_input_binding,
        },
        project=slug,
        rubric=rubric,
        intake=intake,
    )
    if action == "refresh_inputs":
        receipt["model"] = model
    _append_jsonl(ledger_path, receipt, storage)
    _write_text(latest_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n", storage)
    return {
        "schema": schema,
        "served_from": "ztare_report_actions",
        "project": slug,
        "rubric": rubric,
        "intake": intake,
        "renderer": renderer,
        "model": model,
        "action": action,
        "label": label,
        "command": command_display,
        "requires_confirmation": True,
        "writes": True,
        "accepted": proc.returncode == 0,
        "ok": proc.returncode == 0,
        "status": str(parsed.get("status") or ""),
        "status_reasons": status_reasons,
        "synthesis_input_binding": synthesis_input_binding,
        "returncode": proc.returncode,
        "stdout_tail": command_tail(proc.stdout, root=root),
        "stderr_tail": command_tail(proc.stderr, root=root),
        "parsed_output": parsed,
        "receipt": receipt,
        "receipt_path": repo_rel(ledger_path, root=root),
        "latest": repo_rel(latest_path, root=root),
        "write_paths": write_paths,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a Project Workbench report action.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--action", required=True, choices=["check_readiness", "refresh_inputs"])
    parser.add_argument("--rubric")
    parser.add_argument("--intake")
    parser.add_argument("--renderer", default=DEFAULT_RENDERER)
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = run_report_action(
            project=args.project,
            action=args.action,
            rubric=args.rubric,
            intake=args.intake,
            renderer=args.renderer,
            confirmed=args.confirmed,
            root=args.repo,
        )
    except Exception as exc:  # noqa: BLE001 - concise CLI failure.
        print(f"ztare forensic-workbench report-action: {exc}", file=sys.stderr)
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
