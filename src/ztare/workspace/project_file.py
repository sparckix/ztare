"""Saved Project Workbench file writer shared by CLI and D4."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ztare.common.paths import REPO_ROOT
from ztare.workspace.recent_changes import finalize_recent_changes


CASE_FILE_SCHEMA = "ztare-forensic-workbench-case-file-v1"
PROJECT_FILE_SCHEMA = "ztare-forensic-workbench-project-file-v1"
PROJECT_FILE_WRITE_SCHEMA = "ztare-forensic-workbench-project-file-write-receipt-v1"


def safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def repo_rel(path: Path, *, root: Path = REPO_ROOT) -> str:
    return Path(path).resolve().relative_to(root.resolve()).as_posix()


def unique_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def validate_project_slug(project: str) -> str:
    slug = str(project or "").strip()
    if not slug:
        raise ValueError("project is required")
    if "/" in slug or "\\" in slug or slug in {".", ".."} or ".." in slug:
        raise ValueError(f"invalid project slug: {project!r}")
    return slug


def case_key(project: str, intake: str | None) -> str:
    intake_value = str(intake or "").strip()
    return f"{project}::{intake_value}" if intake_value else project


def case_file_stem(project: str, intake: str | None) -> str:
    digest = hashlib.sha256(case_key(project, intake).encode("utf-8")).hexdigest()[:12]
    return f"forensic_workbench_project_file_{digest}"


def add_project_context(
    receipt: dict[str, Any],
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
) -> dict[str, Any]:
    rubric_value = str(rubric or "").strip()
    intake_value = str(intake or "").strip()
    if rubric_value:
        receipt["rubric"] = rubric_value
    if intake_value:
        receipt["intake"] = intake_value
    key = case_key(project, intake_value)
    receipt["project_key"] = key
    receipt["project_file_key"] = key
    receipt["case_key"] = key
    return receipt


def _read_bytes(path: Path, storage: Any = None) -> bytes:
    if storage is not None and hasattr(storage, "read_bytes"):
        return storage.read_bytes(path)
    return path.read_bytes()


def _write_bytes(path: Path, body: bytes, storage: Any = None) -> None:
    if storage is not None and hasattr(storage, "write_bytes"):
        storage.write_bytes(path, body)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


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


def _sha256_if_exists(path: Path, storage: Any = None) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(_read_bytes(path, storage)).hexdigest()


def project_file_paths(project: str, *, intake: str | None = None, root: Path = REPO_ROOT) -> dict[str, Path]:
    slug = validate_project_slug(project)
    workspace = root.resolve() / "projects" / slug / "workspace"
    case_path = workspace / f"{case_file_stem(slug, intake)}.json"
    return {
        "workspace": workspace,
        "project_file": case_path,
        "ledger": workspace / "forensic_workbench_project_files.jsonl",
        "latest": workspace / "forensic_workbench_latest_project_file_write.json",
    }


def saved_project_summary_text(project_file: dict[str, Any]) -> str:
    summary = project_file.get("project_summary") if isinstance(project_file.get("project_summary"), dict) else {}
    next_action = summary.get("next_action") if isinstance(summary.get("next_action"), dict) else {}
    action_count = safe_int(summary.get("open_action_count"))
    repair_count = safe_int(summary.get("open_project_repair_count"))
    advisory_count = safe_int(summary.get("open_advisory_count"))
    file_inventory = summary.get("file_inventory") if isinstance(summary.get("file_inventory"), dict) else {}
    file_count = safe_int(file_inventory.get("item_count"))
    previewable_count = safe_int(file_inventory.get("previewable_count"))
    missing_count = safe_int(file_inventory.get("missing_count"))
    return (
        f"Project file saved; next action {next_action.get('label') or 'not loaded'}; "
        f"{action_count} open actions, {repair_count} repairs, {advisory_count} guidance items, "
        f"{file_count} files ({previewable_count} previewable, {missing_count} missing)"
    )


def attach_current_project_file_summary(
    project_file: dict[str, Any],
    *,
    project_file_path: Path,
    ledger_path: Path,
    latest_path: Path,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    stamped = dict(project_file)
    summary = stamped.get("project_summary")
    if not isinstance(summary, dict):
        return stamped
    summary = dict(summary)
    recent_changes = summary.get("recent_changes")
    recent_changes = dict(recent_changes) if isinstance(recent_changes, dict) else {}
    saved_summary = saved_project_summary_text(stamped)
    project_file_rel = repo_rel(project_file_path, root=root)
    ledger_rel = repo_rel(ledger_path, root=root)
    latest_rel = repo_rel(latest_path, root=root)
    latest_project_file = {
        "label": "Latest project file",
        "status": "recorded",
        "summary": saved_summary,
        "receipt_path": ledger_rel,
        "artifact_path": project_file_rel,
        "latest_path": latest_rel,
        "applied_at": "",
        "kind": "project_file",
        "target": "",
    }
    recent_changes = finalize_recent_changes(
        recent_changes,
        latest_project_file=latest_project_file,
        latest_receipt_path=ledger_rel,
        saved_summary=saved_summary,
    )
    summary["recent_changes"] = recent_changes
    substantive_preview = ""
    if isinstance(recent_changes.get("substantive_inspection"), dict):
        substantive_preview = str(recent_changes["substantive_inspection"].get("preview_path") or "")
    proof_paths = unique_values(
        [
            project_file_rel,
            ledger_rel,
            latest_rel,
            *[str(path) for path in summary.get("proof_paths") or [] if path],
            substantive_preview,
        ]
    )
    summary["proof_paths"] = proof_paths[:20]
    summary["proof_path_count"] = len(proof_paths)
    stamped["project_summary"] = summary
    live_context = stamped.get("live_context")
    if isinstance(live_context, dict):
        live_context = dict(live_context)
        project_state = live_context.get("project_state")
        if isinstance(project_state, dict):
            project_state = dict(project_state)
            state_recent_changes = project_state.get("recent_changes")
            if isinstance(state_recent_changes, dict):
                project_state["recent_changes"] = finalize_recent_changes(
                    state_recent_changes,
                    latest_project_file=latest_project_file,
                    latest_receipt_path=ledger_rel,
                    saved_summary=saved_summary,
                )
            volatile_paths = {project_file_rel, ledger_rel, latest_rel}
            files_state = project_state.get("files")
            if isinstance(files_state, dict) and isinstance(files_state.get("items"), list):
                files_state = dict(files_state)
                normalized_items = []
                for item in files_state["items"]:
                    if not isinstance(item, dict):
                        normalized_items.append(item)
                        continue
                    normalized_item = dict(item)
                    if normalized_item.get("path") in volatile_paths:
                        normalized_item["bytes"] = 0
                        normalized_item["sha256"] = ""
                    normalized_items.append(normalized_item)
                files_state["items"] = normalized_items
                project_state["files"] = files_state
            review_state = project_state.get("review")
            if isinstance(review_state, dict):
                review_state = dict(review_state)
                review_state["receipt_count"] = safe_int(review_state.get("saved_review_count")) + safe_int(
                    review_state.get("saved_next_step_count")
                )
                project_state["review"] = review_state
            live_context["project_state"] = project_state
            stamped["live_context"] = live_context
    return stamped


def project_file_receipt(
    *,
    project: str,
    project_file: dict[str, Any],
    project_file_path: Path,
    ledger_path: Path,
    latest_path: Path,
    previous_sha256: str,
    current_sha256: str,
    root: Path = REPO_ROOT,
    rubric: str | None = None,
    intake: str | None = None,
) -> dict[str, Any]:
    items = project_file.get("items")
    if not isinstance(items, list):
        items = project_file.get("rows")
    if not isinstance(items, list):
        items = project_file.get("project_checks")
    if not isinstance(items, list):
        items = []
    commands = project_file.get("audit_commands")
    if not isinstance(commands, list):
        commands = project_file.get("command_queue")
    if not isinstance(commands, list):
        commands = []
    live_context = project_file.get("live_context") if isinstance(project_file.get("live_context"), dict) else {}
    project_state = live_context.get("project_state") if isinstance(live_context.get("project_state"), dict) else {}
    project_object_contract = live_context.get("project_object_contract") if isinstance(live_context.get("project_object_contract"), dict) else {}
    next_action = project_state.get("next_action") if isinstance(project_state.get("next_action"), dict) else {}
    state_actions = project_state.get("actions") if isinstance(project_state.get("actions"), list) else []
    action_summary = project_state.get("action_summary") if isinstance(project_state.get("action_summary"), dict) else {}
    file_inventory = project_state.get("files") if isinstance(project_state.get("files"), dict) else {}
    project_file_summary = project_file.get("project_summary") if isinstance(project_file.get("project_summary"), dict) else {}
    thesis_audit = project_file_summary.get("project_to_thesis_audit") if isinstance(project_file_summary.get("project_to_thesis_audit"), dict) else {}
    content_changed = previous_sha256 != current_sha256
    return add_project_context(
        {
            "schema": PROJECT_FILE_WRITE_SCHEMA,
            "kind": "project_file",
            "applied_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "project": project,
            "project_file_path": repo_rel(project_file_path, root=root),
            "project_file_sha256": current_sha256,
            "project_file_previous_sha256": previous_sha256,
            "project_file_content_changed": content_changed,
            "case_file_path": repo_rel(project_file_path, root=root),
            "case_file_sha256": current_sha256,
            "case_file_previous_sha256": previous_sha256,
            "case_file_content_changed": content_changed,
            "item_count": len(items),
            "row_count": len(items),
            "command_count": len(commands),
            "receipt_count": len(project_file.get("recent_receipts") or []),
            "project_state_schema": str(project_state.get("schema") or ""),
            "project_state_next_action": str(next_action.get("label") or ""),
            "project_state_action_count": safe_int(action_summary.get("total_count")) if action_summary else len(state_actions),
            "project_state_project_repair_count": safe_int(action_summary.get("project_repair_count")),
            "project_state_project_inspect_count": safe_int(action_summary.get("project_inspect_count")),
            "project_state_advisory_count": safe_int(action_summary.get("advisory_count")),
            "project_file_inventory_count": safe_int(file_inventory.get("item_count")),
            "project_file_previewable_count": safe_int(file_inventory.get("previewable_count")),
            "project_file_missing_count": safe_int(file_inventory.get("missing_count")),
            "project_object_contract_ok": bool(project_object_contract.get("ok")),
            "project_object_contract_failed_count": safe_int(project_object_contract.get("failed_count")),
            "project_object_contract_failed_checks": (
                project_object_contract.get("failed_checks")
                if isinstance(project_object_contract.get("failed_checks"), list)
                else []
            ),
            "project_to_thesis_audit_ok": bool(thesis_audit.get("ok")),
            "project_to_thesis_audit_failed_count": safe_int(thesis_audit.get("failed_count")),
            "project_to_thesis_audit_summary": str(thesis_audit.get("summary") or ""),
        },
        project=project,
        rubric=str(project_file.get("rubric") or rubric or ""),
        intake=str(project_file.get("intake") or intake or ""),
    )


def save_prepared_project_file(
    *,
    project: str,
    project_file: dict[str, Any],
    rubric: str | None = None,
    intake: str | None = None,
    root: Path = REPO_ROOT,
    storage: Any = None,
) -> dict[str, Any]:
    slug = validate_project_slug(project)
    if not isinstance(project_file, dict):
        raise ValueError("project_file must be a JSON object")
    if str(project_file.get("schema") or "") not in {PROJECT_FILE_SCHEMA, CASE_FILE_SCHEMA}:
        raise ValueError("project_file schema is not compatible with this workbench")
    project_root = root.resolve() / "projects" / slug
    if not project_root.exists():
        raise FileNotFoundError(f"project does not exist: projects/{slug}")
    project_file = {**project_file, "schema": PROJECT_FILE_SCHEMA}
    case_intake = str(project_file.get("intake") or intake or "")
    paths = project_file_paths(slug, intake=case_intake, root=root)
    paths["workspace"].mkdir(parents=True, exist_ok=True)
    project_file = attach_current_project_file_summary(
        project_file,
        project_file_path=paths["project_file"],
        ledger_path=paths["ledger"],
        latest_path=paths["latest"],
        root=root,
    )
    summary = project_file.get("project_summary") if isinstance(project_file.get("project_summary"), dict) else {}
    thesis_audit = summary.get("project_to_thesis_audit") if isinstance(summary.get("project_to_thesis_audit"), dict) else {}
    if thesis_audit:
        project_file["project_to_thesis_audit"] = thesis_audit
    body = (json.dumps(project_file, indent=2, sort_keys=True) + "\n").encode("utf-8")
    current_sha256 = hashlib.sha256(body).hexdigest()
    previous_sha256 = _sha256_if_exists(paths["project_file"], storage)
    _write_bytes(paths["project_file"], body, storage)
    receipt = project_file_receipt(
        project=slug,
        project_file=project_file,
        project_file_path=paths["project_file"],
        ledger_path=paths["ledger"],
        latest_path=paths["latest"],
        previous_sha256=previous_sha256,
        current_sha256=current_sha256,
        root=root,
        rubric=rubric,
        intake=intake,
    )
    _append_jsonl(paths["ledger"], receipt, storage)
    _write_text(paths["latest"], json.dumps(receipt, indent=2, sort_keys=True) + "\n", storage)
    write_paths = [repo_rel(paths["project_file"], root=root), repo_rel(paths["ledger"], root=root), repo_rel(paths["latest"], root=root)]
    return {
        "schema": PROJECT_FILE_WRITE_SCHEMA,
        "served_from": "ztare_project_file",
        "ok": True,
        "project": slug,
        "path": write_paths[0],
        "project_file_path": write_paths[0],
        "project_file_sha256": current_sha256,
        "project_file_previous_sha256": previous_sha256,
        "project_file_content_changed": previous_sha256 != current_sha256,
        "content_changed": previous_sha256 != current_sha256,
        "project_file_key": receipt["project_file_key"],
        "receipt": receipt,
        "receipt_path": write_paths[1],
        "latest": write_paths[2],
        "write_paths": write_paths,
        **{key: receipt[key] for key in (
            "project_state_schema",
            "project_state_next_action",
            "project_state_action_count",
            "project_state_project_repair_count",
            "project_state_project_inspect_count",
            "project_state_advisory_count",
            "project_file_inventory_count",
            "project_file_previewable_count",
            "project_file_missing_count",
            "project_object_contract_ok",
            "project_object_contract_failed_count",
            "project_object_contract_failed_checks",
            "project_to_thesis_audit_ok",
            "project_to_thesis_audit_failed_count",
            "project_to_thesis_audit_summary",
            "item_count",
            "receipt_count",
        )},
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Save a prepared Project Workbench project file.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--rubric")
    parser.add_argument("--intake")
    parser.add_argument("--from", dest="project_file_path", required=True, help="Prepared project-file JSON.")
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = json.loads(Path(args.project_file_path).read_text(encoding="utf-8"))
        result = save_prepared_project_file(
            project=args.project,
            rubric=args.rubric,
            intake=args.intake,
            project_file=payload,
            root=args.repo,
        )
    except Exception as exc:  # noqa: BLE001 - concise CLI failure.
        print(f"ztare forensic-workbench save-project-file: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Saved project file: {result['project_file_path']}")
        print(f"Receipt: {result['latest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
