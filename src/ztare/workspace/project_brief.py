"""Project-brief edit operations shared by CLI and D4."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from ztare.common.paths import REPO_ROOT


INTAKE_EDIT_SCHEMA = "ztare-forensic-workbench-intake-edit-receipt-v1"
INTAKE_EDIT_FIELDS = ("bounded_claim", "next_falsifier", "notes", "non_claims", "source_refs", "evidence_refs")
INTAKE_LIST_FIELDS = {"non_claims", "source_refs", "evidence_refs"}


def repo_rel(path: Path, *, root: Path = REPO_ROOT) -> str:
    return Path(path).resolve().relative_to(root.resolve()).as_posix()


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


def path_under(path: Path, root: Path) -> bool:
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def project_intake_path(project: str, intake: str | None = None, *, root: Path = REPO_ROOT) -> Path:
    slug = validate_project_slug(project)
    raw = str(intake or default_intake_for_project(slug)).strip()
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    project_root = (root / "projects" / slug).resolve()
    if not path_under(path, project_root):
        raise ValueError("project brief must live under the project folder")
    if not path.exists():
        raise FileNotFoundError(f"project brief does not exist: {repo_rel(path, root=root)}")
    return path


def case_key(project: str, intake: str | None) -> str:
    intake_value = str(intake or "").strip()
    return f"{project}::{intake_value}" if intake_value else project


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


def _read_json_object(path: Path, storage: Any = None) -> dict[str, Any]:
    payload = json.loads(_read_bytes(path, storage).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("project brief must contain a JSON object")
    return payload


def normalize_intake_patch(raw_patch: Any) -> dict[str, Any]:
    if not isinstance(raw_patch, dict):
        raise ValueError("fields must be a JSON object")
    patch: dict[str, Any] = {}
    for key in INTAKE_EDIT_FIELDS:
        if key not in raw_patch:
            continue
        value = raw_patch[key]
        if key in INTAKE_LIST_FIELDS:
            if isinstance(value, str):
                value = [line.strip() for line in value.splitlines() if line.strip()]
            if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
                raise ValueError(f"{key} must be a list of non-empty strings")
            patch[key] = [item.strip() for item in value]
            continue
        if key == "notes":
            if not isinstance(value, str):
                raise ValueError("notes must be a string")
            patch[key] = value.strip()
            continue
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a non-empty string")
        patch[key] = value.strip()
    if not patch:
        raise ValueError("no editable project-brief fields supplied")
    return patch


def canonical_intake_value(payload: dict[str, Any], key: str) -> Any:
    value = payload.get(key)
    if key in INTAKE_LIST_FIELDS:
        return [str(item).strip() for item in (value or []) if str(item).strip()]
    if key == "notes":
        return str(value or "").strip()
    return str(value or "").strip()


def edit_project_brief(
    *,
    project: str,
    raw_patch: Any,
    intake: str | None = None,
    rubric: str | None = None,
    root: Path = REPO_ROOT,
    storage: Any = None,
) -> dict[str, Any]:
    slug = validate_project_slug(project)
    rubric = rubric or slug
    path = project_intake_path(slug, intake, root=root)
    before_bytes = _read_bytes(path, storage)
    payload = _read_json_object(path, storage)
    if payload.get("project") and payload.get("project") != slug:
        raise ValueError(f"project brief mismatch: expected {slug!r}, got {payload.get('project')!r}")
    patch = normalize_intake_patch(raw_patch)
    changed_patch = {
        key: value
        for key, value in patch.items()
        if canonical_intake_value(payload, key) != value
    }
    if not changed_patch:
        raise ValueError("project brief edit has no changed fields")
    intake_rel = repo_rel(path, root=root)
    before_values = {key: canonical_intake_value(payload, key) for key in changed_patch}
    payload.update(changed_patch)
    after_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    after_bytes = after_text.encode("utf-8")
    _write_bytes(path, after_bytes, storage)
    workspace = root.resolve() / "projects" / slug / "workspace"
    ledger_path = workspace / "forensic_workbench_intake_edits.jsonl"
    latest_path = workspace / "forensic_workbench_latest_intake_edit.json"
    receipt = add_project_context(
        {
            "schema": INTAKE_EDIT_SCHEMA,
            "applied_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "project": slug,
            "intake_path": intake_rel,
            "updated_fields": sorted(changed_patch),
            "before_sha256": sha256(before_bytes).hexdigest(),
            "after_sha256": sha256(after_bytes).hexdigest(),
            "before_values": before_values,
            "after_values": {key: payload.get(key) for key in changed_patch},
        },
        project=slug,
        rubric=rubric,
        intake=intake_rel,
    )
    _append_jsonl(ledger_path, receipt, storage)
    _write_text(latest_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n", storage)
    return {
        "ok": True,
        "project": slug,
        "rubric": rubric,
        "intake_path": intake_rel,
        "updated_fields": sorted(changed_patch),
        "ledger": repo_rel(ledger_path, root=root),
        "latest": repo_rel(latest_path, root=root),
        "receipt_path": repo_rel(ledger_path, root=root),
        "latest_path": repo_rel(latest_path, root=root),
        "write_paths": [intake_rel, repo_rel(ledger_path, root=root), repo_rel(latest_path, root=root)],
        "receipt": receipt,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Edit a project brief and save a receipt.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--rubric")
    parser.add_argument("--intake")
    parser.add_argument("--field", action="append", default=[], help="Set a scalar field as key=value.")
    parser.add_argument("--list-field", action="append", default=[], help="Set a list field as key=item1|item2 or key=<newline text>.")
    parser.add_argument("--patch-json", help="JSON object with project-brief fields.")
    parser.add_argument("--patch-file", type=Path, help="Path to a JSON patch object.")
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true")
    return parser


def _patch_from_args(args: argparse.Namespace) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    if args.patch_file:
        patch.update(json.loads(args.patch_file.read_text(encoding="utf-8")))
    if args.patch_json:
        patch.update(json.loads(args.patch_json))
    for raw in args.field:
        key, sep, value = raw.partition("=")
        if not sep:
            raise ValueError("--field must use key=value")
        patch[key.strip()] = value
    for raw in args.list_field:
        key, sep, value = raw.partition("=")
        if not sep:
            raise ValueError("--list-field must use key=value")
        patch[key.strip()] = [part.strip() for part in value.replace("|", "\n").splitlines() if part.strip()]
    return patch


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = edit_project_brief(
            project=args.project,
            rubric=args.rubric,
            intake=args.intake,
            raw_patch=_patch_from_args(args),
            root=args.repo,
        )
    except Exception as exc:  # noqa: BLE001 - concise CLI failure.
        print(f"ztare project brief-edit: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Updated project brief: {payload['intake_path']}")
        print(f"Fields: {', '.join(payload['updated_fields'])}")
        print(f"Receipt: {payload['latest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
