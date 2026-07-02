"""Project raw-source file add/edit operations shared by CLI and D4."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from ztare.common.paths import REPO_ROOT
from ztare.scaffold.source_check import check_source_project
from ztare.workspace.compile_evidence import SOURCE_TYPE_MAP_FILENAME, SOURCE_TYPE_VALUES


SOURCE_IMPORT_SCHEMA = "ztare-forensic-workbench-source-import-v1"
SOURCE_EDIT_SCHEMA = "ztare-forensic-workbench-source-edit-v1"
SOURCE_IMPORT_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}\.(md|txt)$")
SOURCE_IMPORT_TYPES = set(SOURCE_TYPE_VALUES)
SOURCE_ARTIFACT_KINDS = {
    "project_note",
    "agent_notes",
    "source_summary",
    "computation_output",
    "script_or_code",
    "report_draft",
    "proof_note",
    "search_summary",
    "raw_evidence",
}


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


def project_paths(project: str, *, root: Path = REPO_ROOT) -> dict[str, Path]:
    slug = validate_project_slug(project)
    project_root = root.resolve() / "projects" / slug
    return {
        "project_root": project_root,
        "raw_dir": project_root / "raw",
        "workspace": project_root / "workspace",
        "source_type_map": project_root / "raw" / SOURCE_TYPE_MAP_FILENAME,
    }


def path_under(path: Path, root: Path) -> bool:
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def _read_text(path: Path, storage: Any = None) -> str:
    if storage is not None and hasattr(storage, "read_text"):
        return storage.read_text(path)
    return path.read_text(encoding="utf-8")


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


def _read_json_object(path: Path, *, root: Path, storage: Any = None) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = json.loads(_read_text(path, storage))
    if not isinstance(raw, dict):
        raise ValueError(f"{repo_rel(path, root=root)} must contain a JSON object")
    return raw


def _write_json(path: Path, payload: dict[str, Any], storage: Any = None) -> None:
    _write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n", storage)


def frontmatter_value(value: str, *, limit: int = 120) -> str:
    return re.sub(r"[\r\n]+", " ", str(value or "").strip())[:limit]


def validate_import_filename(filename: str) -> str:
    filename = str(filename or "").strip()
    if not SOURCE_IMPORT_FILENAME_RE.fullmatch(filename):
        raise ValueError("filename must be a flat .md or .txt name using letters, numbers, dot, dash, or underscore")
    return filename


def unsafe_local_ref_reason(ref: str) -> str | None:
    raw = str(ref or "").strip().replace("\\", "/")
    if not raw:
        return "empty path"
    if raw.startswith("/"):
        return "absolute path"
    parts = PurePosixPath(raw).parts
    if any(part in {"", ".", ".."} for part in parts):
        return "unsafe path segment"
    return None


def validate_raw_source_relative(value: str) -> str:
    value = str(value or "").strip().replace("\\", "/")
    unsafe_reason = unsafe_local_ref_reason(value)
    if unsafe_reason is not None:
        raise ValueError(f"invalid source file path: {unsafe_reason}")
    path = PurePosixPath(value)
    if path.name == SOURCE_TYPE_MAP_FILENAME:
        raise ValueError(f"{SOURCE_TYPE_MAP_FILENAME} is edited as source metadata, not as a source")
    if path.suffix.lower() not in {".md", ".txt"}:
        raise ValueError("source file path must end in .md or .txt")
    return path.as_posix()


def raw_source_path(project: str, relative_path: str, *, root: Path = REPO_ROOT) -> Path:
    paths = project_paths(project, root=root)
    relative_path = validate_raw_source_relative(relative_path)
    path = (paths["raw_dir"] / relative_path).resolve()
    if not path_under(path, paths["raw_dir"]):
        raise ValueError("source path escapes the project source file directory")
    return path


def split_source_frontmatter(text: str, *, fallback_source_type: str = "untyped") -> tuple[str, str]:
    source_type = fallback_source_type if fallback_source_type in SOURCE_IMPORT_TYPES else "untyped"
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            for line in text[4:end].splitlines():
                key, sep, value = line.partition(":")
                if sep and key.strip() == "source_type" and value.strip() in SOURCE_IMPORT_TYPES:
                    source_type = value.strip()
            body = text[end + len("\n---\n") :]
            if body.startswith("\n"):
                body = body[1:]
            if body.endswith("\n"):
                body = body[:-1]
            return source_type, body
    if text.endswith("\n"):
        text = text[:-1]
    return source_type, text


def source_frontmatter_metadata(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    metadata: dict[str, str] = {}
    for line in text[4:end].splitlines():
        key, sep, value = line.partition(":")
        if sep:
            metadata[key.strip()] = value.strip()
    return metadata


def _render_source_text(
    *,
    source_type: str,
    body: str,
    artifact_kind: str = "",
    created_by: str = "",
) -> str:
    frontmatter = ["---", f"source_type: {source_type}"]
    if artifact_kind:
        frontmatter.append(f"artifact_kind: {artifact_kind}")
    if created_by:
        frontmatter.append(f"created_by: {frontmatter_value(created_by)}")
    frontmatter.append("---")
    return "\n".join(frontmatter) + f"\n\n{body}\n"


def _source_check_payload(project: str, *, root: Path) -> dict[str, Any]:
    try:
        return check_source_project(project=project, repo=root)
    except Exception as exc:  # noqa: BLE001 - write receipt should remain inspectable.
        return {"ok": False, "error": str(exc)}


def source_write_paths(project: str, source_path: Path, *, kind: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    slug = validate_project_slug(project)
    paths = project_paths(slug, root=root)
    if kind == "import":
        receipt = paths["workspace"] / "forensic_workbench_source_imports.jsonl"
        latest = paths["workspace"] / "forensic_workbench_latest_source_import.json"
    elif kind == "edit":
        receipt = paths["workspace"] / "forensic_workbench_source_edits.jsonl"
        latest = paths["workspace"] / "forensic_workbench_latest_source_edit.json"
    else:
        raise ValueError("kind must be import or edit")
    write_paths = [
        repo_rel(source_path, root=root),
        repo_rel(paths["source_type_map"], root=root),
        repo_rel(receipt, root=root),
        repo_rel(latest, root=root),
    ]
    return {"receipt_path": repo_rel(receipt, root=root), "latest_path": repo_rel(latest, root=root), "write_paths": write_paths}


def add_source_file(
    *,
    project: str,
    filename: str,
    source_type: str,
    body: str,
    artifact_kind: str = "project_note",
    created_by: str = "",
    rubric: str | None = None,
    intake: str | None = None,
    root: Path = REPO_ROOT,
    storage: Any = None,
) -> dict[str, Any]:
    slug = validate_project_slug(project)
    rubric = rubric or slug
    intake = intake or default_intake_for_project(slug)
    filename = validate_import_filename(filename)
    if source_type not in SOURCE_IMPORT_TYPES:
        raise ValueError(f"source_type must be one of: {', '.join(sorted(SOURCE_IMPORT_TYPES))}")
    artifact_kind = str(artifact_kind or "project_note").strip()
    if artifact_kind not in SOURCE_ARTIFACT_KINDS:
        raise ValueError(f"kind must be one of: {', '.join(sorted(SOURCE_ARTIFACT_KINDS))}")
    body = str(body or "")
    if not body.strip():
        raise ValueError("source body is required")
    paths = project_paths(slug, root=root)
    raw_dir = paths["raw_dir"]
    if not raw_dir.exists():
        raise FileNotFoundError(f"source file directory does not exist: {repo_rel(raw_dir, root=root)}")
    source_path = (raw_dir / filename).resolve()
    if not path_under(source_path, raw_dir):
        raise ValueError("source path escapes the project source file directory")
    if source_path.exists():
        raise ValueError(f"source file already exists: {repo_rel(source_path, root=root)}")
    created_by = frontmatter_value(created_by)
    source_text = _render_source_text(
        source_type=source_type,
        artifact_kind=artifact_kind,
        created_by=created_by,
        body=body,
    )
    _write_text(source_path, source_text, storage)
    source_type_map = _read_json_object(paths["source_type_map"], root=root, storage=storage)
    source_type_map[filename] = source_type
    _write_json(paths["source_type_map"], source_type_map, storage)
    write_paths = source_write_paths(slug, source_path, kind="import", root=root)
    receipt = add_project_context(
        {
            "schema": SOURCE_IMPORT_SCHEMA,
            "applied_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "project": slug,
            "source_path": repo_rel(source_path, root=root),
            "source_type": source_type,
            "artifact_kind": artifact_kind,
            "created_by": created_by,
            "chars": len(body),
            "sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
            "source_type_map": repo_rel(paths["source_type_map"], root=root),
        },
        project=slug,
        rubric=rubric,
        intake=intake,
    )
    receipt_path = paths["workspace"] / "forensic_workbench_source_imports.jsonl"
    latest_path = paths["workspace"] / "forensic_workbench_latest_source_import.json"
    _append_jsonl(receipt_path, receipt, storage)
    _write_json(latest_path, receipt, storage)
    source_check = _source_check_payload(slug, root=root)
    return {
        "schema": SOURCE_IMPORT_SCHEMA,
        "served_from": "ztare_source_files",
        "ok": True,
        "project": slug,
        "rubric": rubric,
        "intake": intake,
        "source_path": repo_rel(source_path, root=root),
        "source_type": source_type,
        "artifact_kind": artifact_kind,
        "created_by": created_by,
        "source_type_map": repo_rel(paths["source_type_map"], root=root),
        "receipt": receipt,
        "receipt_path": write_paths["receipt_path"],
        "latest": write_paths["latest_path"],
        "write_paths": write_paths["write_paths"],
        "source_check": source_check,
    }


def edit_source_file(
    *,
    project: str,
    relative_path: str,
    source_type: str,
    body: str,
    artifact_kind: str | None = None,
    created_by: str | None = None,
    rubric: str | None = None,
    intake: str | None = None,
    root: Path = REPO_ROOT,
    storage: Any = None,
) -> dict[str, Any]:
    slug = validate_project_slug(project)
    rubric = rubric or slug
    intake = intake or default_intake_for_project(slug)
    if source_type not in SOURCE_IMPORT_TYPES:
        raise ValueError(f"source_type must be one of: {', '.join(sorted(SOURCE_IMPORT_TYPES))}")
    body = str(body or "")
    if not body.strip():
        raise ValueError("source body is required")
    paths = project_paths(slug, root=root)
    path = raw_source_path(slug, relative_path, root=root)
    if not path.exists():
        raise FileNotFoundError(f"source file does not exist: {repo_rel(path, root=root)}")
    relative_path = path.relative_to(paths["raw_dir"].resolve()).as_posix()
    before_text = _read_text(path, storage)
    source_type_map = _read_json_object(paths["source_type_map"], root=root, storage=storage)
    fallback_type = str(source_type_map.get(relative_path) or source_type_map.get(path.name) or "untyped")
    existing_source_type, existing_body = split_source_frontmatter(before_text, fallback_source_type=fallback_type)
    existing_metadata = source_frontmatter_metadata(before_text)
    existing_artifact_kind = existing_metadata.get("artifact_kind") if existing_metadata.get("artifact_kind") in SOURCE_ARTIFACT_KINDS else ""
    existing_created_by = frontmatter_value(existing_metadata.get("created_by") or "")
    if artifact_kind:
        artifact_kind = str(artifact_kind).strip()
        if artifact_kind not in SOURCE_ARTIFACT_KINDS:
            raise ValueError(f"kind must be one of: {', '.join(sorted(SOURCE_ARTIFACT_KINDS))}")
    else:
        artifact_kind = existing_artifact_kind
    created_by = existing_created_by if created_by is None else frontmatter_value(created_by)
    if (
        existing_source_type == source_type
        and existing_body == body
        and existing_artifact_kind == artifact_kind
        and existing_created_by == created_by
    ):
        raise ValueError("file edit has no changed fields")
    source_text = _render_source_text(
        source_type=source_type,
        artifact_kind=artifact_kind,
        created_by=created_by,
        body=body,
    )
    _write_text(path, source_text, storage)
    source_type_map[relative_path] = source_type
    _write_json(paths["source_type_map"], source_type_map, storage)
    write_paths = source_write_paths(slug, path, kind="edit", root=root)
    receipt = add_project_context(
        {
            "schema": SOURCE_EDIT_SCHEMA,
            "applied_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "project": slug,
            "source_path": repo_rel(path, root=root),
            "relative_raw_path": relative_path,
            "source_type": source_type,
            "artifact_kind": artifact_kind,
            "created_by": created_by,
            "chars": len(body),
            "sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
            "source_type_map": repo_rel(paths["source_type_map"], root=root),
        },
        project=slug,
        rubric=rubric,
        intake=intake,
    )
    receipt_path = paths["workspace"] / "forensic_workbench_source_edits.jsonl"
    latest_path = paths["workspace"] / "forensic_workbench_latest_source_edit.json"
    _append_jsonl(receipt_path, receipt, storage)
    _write_json(latest_path, receipt, storage)
    source_check = _source_check_payload(slug, root=root)
    return {
        "schema": SOURCE_EDIT_SCHEMA,
        "served_from": "ztare_source_files",
        "ok": True,
        "project": slug,
        "rubric": rubric,
        "intake": intake,
        "source_path": repo_rel(path, root=root),
        "relative_raw_path": relative_path,
        "source_type": source_type,
        "artifact_kind": artifact_kind,
        "created_by": created_by,
        "receipt": receipt,
        "receipt_path": write_paths["receipt_path"],
        "latest": write_paths["latest_path"],
        "write_paths": write_paths["write_paths"],
        "source_check": source_check,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Add or edit project raw source files.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add", help="Add a new raw source file.")
    add.add_argument("--project", required=True)
    add.add_argument("--rubric")
    add.add_argument("--intake")
    add.add_argument("--filename", required=True)
    add.add_argument("--source-type", required=True, choices=sorted(SOURCE_IMPORT_TYPES))
    add.add_argument("--kind", default="project_note", choices=sorted(SOURCE_ARTIFACT_KINDS))
    add.add_argument("--created-by", default="")
    add.add_argument("--body", default="")
    add.add_argument("--body-file", type=Path)
    add.add_argument("--repo", type=Path, default=REPO_ROOT)
    add.add_argument("--json", action="store_true")
    edit = sub.add_parser("edit", help="Edit an existing raw source file.")
    edit.add_argument("--project", required=True)
    edit.add_argument("--rubric")
    edit.add_argument("--intake")
    edit.add_argument("--relative", required=True)
    edit.add_argument("--source-type", required=True, choices=sorted(SOURCE_IMPORT_TYPES))
    edit.add_argument("--kind", choices=sorted(SOURCE_ARTIFACT_KINDS))
    edit.add_argument("--created-by")
    edit.add_argument("--body", default="")
    edit.add_argument("--body-file", type=Path)
    edit.add_argument("--repo", type=Path, default=REPO_ROOT)
    edit.add_argument("--json", action="store_true")
    return parser


def _body_from_args(args: argparse.Namespace) -> str:
    if args.body_file:
        return args.body_file.read_text(encoding="utf-8")
    if args.body:
        return args.body
    return sys.stdin.read()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "add":
            payload = add_source_file(
                project=args.project,
                rubric=args.rubric,
                intake=args.intake,
                filename=args.filename,
                source_type=args.source_type,
                artifact_kind=args.kind,
                created_by=args.created_by,
                body=_body_from_args(args),
                root=args.repo,
            )
        else:
            payload = edit_source_file(
                project=args.project,
                rubric=args.rubric,
                intake=args.intake,
                relative_path=args.relative,
                source_type=args.source_type,
                artifact_kind=args.kind,
                created_by=args.created_by,
                body=_body_from_args(args),
                root=args.repo,
            )
    except Exception as exc:  # noqa: BLE001 - concise CLI failure.
        print(f"ztare project source-file {args.cmd}: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        action = "Added" if args.cmd == "add" else "Updated"
        print(f"{action} source file: {payload.get('source_path')}")
        print(f"Receipt: {payload.get('latest')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
