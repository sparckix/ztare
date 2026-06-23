"""Offline source-ingest preflight for project userland.

This checks raw source files and source_type declarations before the
LLM-backed evidence compiler runs. It does not compile evidence, launch
autoresearch, or enqueue work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from ztare.scaffold.source_project import REPO, project_dir_for
from ztare.workspace.compile_evidence import (
    SOURCE_TYPE_MAP_FILENAME,
    SOURCE_TYPE_UNTYPED,
    SOURCE_TYPE_VALUES,
    TEXT_EXTENSIONS,
    load_source_type_map_with_warnings,
    read_typed_source,
)


def _rel(path: Path, repo: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo.resolve()))
    except ValueError:
        return str(path)


def _mapped_source_type(source_type_map: dict[str, str], relative_path: str) -> str | None:
    filename = Path(relative_path).name
    for key in (relative_path, filename):
        value = source_type_map.get(key)
        if value and value != SOURCE_TYPE_UNTYPED:
            return value
    return None


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_source_project(
    *,
    project: str,
    repo: Path = REPO,
) -> dict[str, Any]:
    repo = repo.resolve()
    project_dir = project_dir_for(repo, project)
    raw_dir = project_dir / "raw"
    source_type_map_path = raw_dir / SOURCE_TYPE_MAP_FILENAME
    source_type_map, map_warnings = load_source_type_map_with_warnings(raw_dir)

    blocking: list[str] = []
    warnings: list[str] = list(map_warnings)
    source_rows: list[dict[str, Any]] = []
    unsupported_files: list[str] = []
    empty_files: list[str] = []

    if not project_dir.exists():
        blocking.append("project directory is missing")
    if not raw_dir.exists():
        blocking.append("raw source directory is missing")
    if map_warnings:
        blocking.append(f"{SOURCE_TYPE_MAP_FILENAME} has invalid entries")

    if raw_dir.exists():
        all_files = sorted(path for path in raw_dir.rglob("*") if path.is_file())
        supported_files = [
            path
            for path in all_files
            if path.suffix.lower() in TEXT_EXTENSIONS and path.name != SOURCE_TYPE_MAP_FILENAME
        ]
        unsupported_files = [
            _rel(path, repo)
            for path in all_files
            if path.suffix.lower() not in TEXT_EXTENSIONS
        ]

        for path in supported_files:
            relative_path = str(path.relative_to(raw_dir))
            raw_text, source_type, had_invalid_type = read_typed_source(path)
            raw_text = raw_text.strip()
            if not raw_text:
                empty_files.append(_rel(path, repo))
                continue

            type_source = "frontmatter"
            invalid_declaration = had_invalid_type
            if source_type == SOURCE_TYPE_UNTYPED:
                mapped = _mapped_source_type(source_type_map, relative_path)
                if mapped:
                    source_type = mapped
                    type_source = SOURCE_TYPE_MAP_FILENAME
                else:
                    type_source = "default_untyped"

            source_rows.append(
                {
                    "path": _rel(path, repo),
                    "relative_raw_path": relative_path,
                    "source_type": source_type,
                    "source_type_source": type_source,
                    "invalid_source_type_declaration": invalid_declaration,
                    "sha256": _sha256_text(raw_text),
                    "chars": len(raw_text),
                }
            )

        if not supported_files:
            blocking.append("no supported text-like source files found under raw")
        elif not source_rows:
            blocking.append("no non-empty supported source files found under raw")

    invalid_rows = [row for row in source_rows if row["invalid_source_type_declaration"]]
    untyped_rows = [row for row in source_rows if row["source_type"] == SOURCE_TYPE_UNTYPED]
    evidence_rows = [row for row in source_rows if row["source_type"] == "source_evidence"]

    if invalid_rows:
        blocking.append("one or more sources declare an invalid source_type")
    if empty_files:
        warnings.append(f"empty source files ignored: {len(empty_files)}")
    if unsupported_files:
        warnings.append(f"unsupported non-text source files ignored: {len(unsupported_files)}")
    if untyped_rows:
        warnings.append("untyped sources are excluded from immutable facts and constraints")
    if source_rows and not evidence_rows:
        blocking.append("no source_evidence file is present")

    ok = not blocking
    status = "ready_for_evidence_prepare" if ok else "blocked"
    next_commands: list[str] = []
    next_steps: list[str] = []
    if not project_dir.exists() or not raw_dir.exists():
        next_commands.append(f"ztare project source-init --project {project_dir.name}")
    if raw_dir.exists() and not source_rows:
        next_steps.append(f"Put text-like source files under {_rel(raw_dir, repo)}.")
    if invalid_rows:
        next_steps.append("Fix invalid source_type declarations or source_type_map entries.")
    if source_rows and not evidence_rows:
        next_steps.append(
            "Type at least one raw source as source_evidence before compiling evidence."
        )
    if untyped_rows:
        next_steps.append("Type untyped sources with source_type frontmatter or raw/source_type_map.json.")
    if ok:
        next_steps.append("Compile the source/evidence chain before routing into the loop.")
        next_commands.append(f"make evidence-prepare PROJECT={project_dir.name} MODEL=gemini")

    return {
        "schema": "ztare-source-check-v1",
        "ok": ok,
        "status": status,
        "project": project,
        "project_slug": project_dir.name,
        "project_dir": _rel(project_dir, repo),
        "raw_dir": _rel(raw_dir, repo),
        "source_type_map": _rel(source_type_map_path, repo),
        "source_type_values": sorted(SOURCE_TYPE_VALUES),
        "source_count": len(source_rows),
        "source_evidence_count": len(evidence_rows),
        "untyped_source_count": len(untyped_rows),
        "unsupported_file_count": len(unsupported_files),
        "empty_file_count": len(empty_files),
        "blocking": blocking,
        "warnings": warnings,
        "sources": source_rows,
        "unsupported_files": unsupported_files,
        "empty_files": empty_files,
        "next_steps": next_steps,
        "next_commands": next_commands,
        "non_actions": [
            "does not call an LLM",
            "does not compile evidence",
            "does not launch autoresearch",
            "does not enqueue out-of-loop work",
        ],
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "ZTARE source check",
        "",
        f"project: {report['project_slug']}",
        f"status: {report['status']}",
        f"sources: {report['source_count']} ({report['source_evidence_count']} source_evidence, {report['untyped_source_count']} untyped)",
    ]
    if report["blocking"]:
        lines.append("Blocking issues:")
        lines.extend(f"  - {item}" for item in report["blocking"])
    if report["warnings"]:
        lines.append("Warnings:")
        lines.extend(f"  - {item}" for item in report["warnings"])
    if report["sources"]:
        lines.append("Sources:")
        for row in report["sources"]:
            lines.append(
                "  - "
                f"{row['relative_raw_path']} [{row['source_type']} via {row['source_type_source']}]"
            )
    if report["next_steps"]:
        lines.append("Next steps:")
        lines.extend(f"  - {step}" for step in report["next_steps"])
    if report["next_commands"]:
        lines.append("Next commands:")
        lines.extend(f"  {command}" for command in report["next_commands"])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Project slug or repo-relative projects/<slug> path.")
    parser.add_argument("--repo", type=Path, default=REPO, help="Repo root for tests or alternate checkouts.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument(
        "--no-fail",
        action="store_true",
        help="Exit 0 even when the report is blocked.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = check_source_project(project=args.project, repo=args.repo)
    except ValueError as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0 if args.no_fail or report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
