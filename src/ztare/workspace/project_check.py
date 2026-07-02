"""Project-local check runner shared by the CLI and D4 workbench."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from ztare.common.paths import REPO_ROOT


PROJECT_TEST_SCHEMA = "ztare-forensic-workbench-project-test-v1"
PROJECT_TEST_RECEIPT_SCHEMA = "ztare-forensic-workbench-project-test-receipt-v1"


def repo_root() -> Path:
    env_root = os.environ.get("ZTARE_REPO")
    return Path(env_root).resolve() if env_root else REPO_ROOT.resolve()


def repo_rel(path: Path, *, root: Path | None = None) -> str:
    base = (root or repo_root()).resolve()
    return Path(path).resolve().relative_to(base).as_posix()


def safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def tail_text(value: str, *, max_chars: int = 4000) -> str:
    value = value or ""
    return value if len(value) <= max_chars else value[-max_chars:]


def repo_display_text(value: Any, *, root: Path | None = None) -> str:
    text = str(value or "")
    if not text:
        return ""
    base = str((root or repo_root()).resolve())
    return text.replace(base + "/", "").replace(base, ".")


def tail_display_text(value: str, *, root: Path | None = None, max_chars: int = 4000) -> str:
    return repo_display_text(tail_text(value, max_chars=max_chars), root=root)


def validate_project_slug(project: str) -> str:
    slug = str(project or "").strip()
    if not slug:
        raise ValueError("project is required")
    if "/" in slug or "\\" in slug or slug in {".", ".."} or ".." in slug:
        raise ValueError(f"invalid project slug: {project!r}")
    return slug


def default_intake_for_project(project: str) -> str:
    slug = validate_project_slug(project)
    return f"projects/{slug}/{slug}_intake.json"


def project_test_paths(project: str, *, root: Path | None = None) -> dict[str, Path]:
    base = root or repo_root()
    slug = validate_project_slug(project)
    project_root = base / "projects" / slug
    return {
        "project_root": project_root,
        "test_path": project_root / "test_model.py",
        "ledger_path": project_root / "workspace" / "forensic_workbench_project_tests.jsonl",
        "latest_path": project_root / "workspace" / "forensic_workbench_latest_project_test.json",
    }


def project_test_write_paths(project: str) -> dict[str, str]:
    slug = validate_project_slug(project)
    ledger = f"projects/{slug}/workspace/forensic_workbench_project_tests.jsonl"
    latest = f"projects/{slug}/workspace/forensic_workbench_latest_project_test.json"
    return {"receipt_path": ledger, "latest_path": latest, "write_paths": [ledger, latest]}


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def project_test_path_from_command(command: str, *, root: Path | None = None, python_executable: str | None = None) -> str:
    try:
        parts = shlex.split(str(command or ""))
    except ValueError:
        return ""
    allowed_python = {"python", "python3"}
    if python_executable:
        allowed_python.add(python_executable)
    if len(parts) < 2 or parts[0] not in allowed_python:
        return ""
    candidate = PurePosixPath(str(parts[-1] or "")).as_posix()
    if not candidate.endswith("/test_model.py"):
        return ""
    candidate_path = Path(candidate)
    if candidate_path.is_absolute():
        try:
            return repo_rel(candidate_path, root=root)
        except ValueError:
            return ""
    return candidate


def inferred_project_test_command(project: str, label: str, *, root: Path | None = None) -> str:
    slug = str(project or "").strip()
    label_text = str(label or "").lower()
    if not slug or "parameter-space test" not in label_text:
        return ""
    if "cache" not in label_text and "fixture" not in label_text:
        return ""
    test_path = (root or repo_root()) / "projects" / slug / "test_model.py"
    if not test_path.exists():
        return ""
    return f"python projects/{slug}/test_model.py"


def report_action_completion_summary(action: dict[str, Any], receipt: dict[str, Any]) -> str:
    action_label = str(action.get("label") or "")
    receipt_summary = str(receipt.get("display_summary") or receipt.get("summary") or "")
    label_text = action_label.lower()
    accepted = (
        bool(receipt.get("accepted"))
        or str(receipt.get("display_status") or "") == "accepted"
        or safe_int(receipt.get("returncode")) == 0
    )
    if accepted and ("counterexample" in label_text or ("search for" in label_text and "before any" in label_text)):
        return "Project test passed: no counterexample was found by the saved project test."
    if accepted and "parameter" in label_text and "test" in label_text:
        return "Project test passed: the saved parameter-space test did not find a blocking case."
    return receipt_summary or ("Project test passed." if accepted else "Project test needs attention.")


def report_action_completed(action: dict[str, Any]) -> bool:
    return str(action.get("status") or "") == "completed" or bool(action.get("completed_by"))


def passed_project_test_for_action(
    action: dict[str, Any],
    receipt_rows: list[dict[str, Any]],
    *,
    root: Path | None = None,
    python_executable: str | None = None,
) -> dict[str, Any]:
    test_path = project_test_path_from_command(
        str(action.get("command") or ""),
        root=root,
        python_executable=python_executable,
    )
    if not test_path:
        return {}
    for receipt in receipt_rows:
        if not isinstance(receipt, dict) or str(receipt.get("kind") or "") != "project_test":
            continue
        if str(receipt.get("test_path") or "") != test_path:
            continue
        accepted = receipt.get("accepted") or str(receipt.get("display_status") or "") == "accepted" or safe_int(receipt.get("returncode")) == 0
        if accepted:
            return receipt
    return {}


def annotate_completed_report_actions(
    actions: list[dict[str, Any]],
    receipt_rows: list[dict[str, Any]],
    *,
    root: Path | None = None,
    python_executable: str | None = None,
) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        row = dict(action)
        receipt = passed_project_test_for_action(row, receipt_rows, root=root, python_executable=python_executable)
        if receipt:
            row.update(
                {
                    "status": "completed",
                    "display_status": "done",
                    "completed_at": str(receipt.get("applied_at") or ""),
                    "completed_by": str(receipt.get("path") or ""),
                    "completed_summary": report_action_completion_summary(row, receipt),
                    "completed_artifact": str(receipt.get("test_path") or ""),
                    "primary_label": "Open result",
                }
            )
        annotated.append(row)
    return annotated


def completed_report_action_summary_for_change(actions: list[dict[str, Any]], change: dict[str, Any]) -> str:
    test_path = str(change.get("artifact_path") or "")
    receipt_path = str(change.get("receipt_path") or "")
    for action in actions:
        if not isinstance(action, dict) or not report_action_completed(action):
            continue
        if test_path and str(action.get("completed_artifact") or "") == test_path:
            return str(action.get("completed_summary") or "")
        if receipt_path and str(action.get("completed_by") or "") == receipt_path:
            return str(action.get("completed_summary") or "")
    return ""


def enrich_recent_project_check_summary(
    recent_changes: dict[str, Any],
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    if not isinstance(recent_changes, dict):
        return recent_changes
    latest = recent_changes.get("latest_project_check") if isinstance(recent_changes.get("latest_project_check"), dict) else {}
    summary = completed_report_action_summary_for_change(actions, latest)
    if not summary:
        return recent_changes
    enriched = dict(recent_changes)
    latest = {**latest, "summary": summary}
    enriched["latest_project_check"] = latest
    if str(enriched.get("latest_receipt_path") or "") == str(latest.get("receipt_path") or ""):
        enriched["latest_receipt_summary"] = summary
        enriched["summary"] = summary
    for key in ("next_inspection", "substantive_inspection"):
        value = enriched.get(key)
        if isinstance(value, dict) and str(value.get("label") or "") in {"Latest project check", "Latest project test"}:
            enriched[key] = {**value, "summary": summary}
    if isinstance(enriched.get("changes"), list):
        enriched["changes"] = [
            {**row, "summary": summary}
            if isinstance(row, dict) and str(row.get("label") or "") in {"Latest project check", "Latest project test"}
            else row
            for row in enriched["changes"]
        ]
    return enriched


def run_project_check(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    action_id: str | None = None,
    action_label: str | None = None,
    python_executable: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    base = root or repo_root()
    slug = validate_project_slug(project)
    rubric = rubric or slug
    intake = intake or default_intake_for_project(slug)
    test_paths = project_test_paths(slug, root=base)
    test_path = test_paths["test_path"]
    if not test_path.exists():
        raise ValueError(f"project check file is missing: {repo_rel(test_path, root=base)}")
    python_cmd = python_executable or sys.executable
    command = [python_cmd, str(test_path)]
    display_command = f"python {repo_rel(test_path, root=base)}"
    proc = subprocess.run(command, cwd=base, capture_output=True, text=True, timeout=90, check=False)
    accepted = proc.returncode == 0
    applied_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    ledger_path = test_paths["ledger_path"]
    latest_path = test_paths["latest_path"]
    receipt = {
        "schema": PROJECT_TEST_RECEIPT_SCHEMA,
        "project": slug,
        "rubric": rubric,
        "intake": intake,
        "action_id": str(action_id or ""),
        "action_label": str(action_label or ""),
        "test_path": repo_rel(test_path, root=base),
        "command": display_command,
        "status": "accepted" if accepted else "failed",
        "returncode": proc.returncode,
        "stdout_tail": tail_display_text(proc.stdout, root=base),
        "stderr_tail": tail_display_text(proc.stderr, root=base),
        "applied_at": applied_at,
    }
    append_jsonl(ledger_path, receipt)
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path_payload = project_test_write_paths(slug)
    return {
        "schema": PROJECT_TEST_SCHEMA,
        "served_from": "ztare_project_check",
        "project": slug,
        "rubric": rubric,
        "intake": intake,
        "command": display_command,
        "returncode": proc.returncode,
        "accepted": accepted,
        "ok": accepted,
        "stdout_tail": receipt["stdout_tail"],
        "stderr_tail": receipt["stderr_tail"],
        "receipt_path": repo_rel(ledger_path, root=base),
        "latest_path": repo_rel(latest_path, root=base),
        "test_path": repo_rel(test_path, root=base),
        "write_paths": path_payload["write_paths"],
        "receipt": receipt,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a project-local check and save the receipt.")
    parser.add_argument("--project", required=True, help="Project slug under projects/.")
    parser.add_argument("--rubric", help="Rubric name. Defaults to the project slug.")
    parser.add_argument("--intake", help="Project brief path. Defaults to projects/<project>/<project>_intake.json.")
    parser.add_argument("--action-id", default="", help="Optional report action id this check satisfies.")
    parser.add_argument("--action-label", default="", help="Optional report action label this check satisfies.")
    parser.add_argument("--json", action="store_true", help="Print the full JSON payload.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = run_project_check(
            project=args.project,
            rubric=args.rubric,
            intake=args.intake,
            action_id=args.action_id,
            action_label=args.action_label,
        )
    except Exception as exc:  # noqa: BLE001 - CLI should return a concise failure.
        print(f"ztare project check: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        status = "passed" if payload.get("accepted") else "failed"
        print(f"Project test {status}: {payload.get('command')}")
        print(f"Saved history: {payload.get('latest_path')}")
        if payload.get("stderr_tail"):
            print(payload["stderr_tail"], file=sys.stderr)
    return 0 if payload.get("accepted") else 1


if __name__ == "__main__":
    raise SystemExit(main())
