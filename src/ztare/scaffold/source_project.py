"""Initialize a source-ingest project surface for autoresearch prep.

This creates raw/, workspace/, and raw/source_type_map.json before raw source
documents are compiled into evidence. It does not launch autoresearch, create
fake evidence, or enqueue RD work.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
SAFE_PART_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
SOURCE_TYPE_MAP_TEMPLATE: dict[str, str] = {}


def project_dir_for(repo: Path, project: str) -> Path:
    raw = Path(project)
    if raw.is_absolute():
        raise ValueError("--project must be a repo-relative slug or path")
    if not raw.parts:
        raise ValueError("--project must not be empty")
    if any(part == ".." for part in raw.parts):
        raise ValueError("--project must not contain '..'")
    for part in raw.parts:
        if not SAFE_PART_RE.match(part):
            raise ValueError(
                "--project path parts may contain only letters, numbers, dot, dash, and underscore"
            )
    if raw.parts[0] == "projects":
        return (repo / raw).resolve()
    return (repo / "projects" / raw).resolve()


def init_source_project(
    *,
    project: str,
    rubric: str | None = None,
    model: str = "gemini",
    repo: Path = REPO,
    dry_run: bool = False,
) -> dict[str, Any]:
    repo = repo.resolve()
    project_dir = project_dir_for(repo, project)
    raw_dir = project_dir / "raw"
    workspace_dir = project_dir / "workspace"
    source_type_map = raw_dir / "source_type_map.json"
    dirs = [project_dir, raw_dir, workspace_dir]
    existing = [path for path in dirs if path.exists()]
    missing = [path for path in dirs if not path.exists()]
    source_type_map_missing = not source_type_map.exists()
    if not dry_run:
        for path in missing:
            path.mkdir(parents=True, exist_ok=True)
        if source_type_map_missing:
            source_type_map.write_text(
                json.dumps(SOURCE_TYPE_MAP_TEMPLATE, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

    project_slug = project_dir.name
    trace_command = f"ztare autoresearch trace --project {project_slug}"
    if rubric:
        trace_command += f" --rubric {rubric}"
    trace_command += " --json"
    return {
        "schema": "ztare-source-project-surface-v1",
        "ok": True,
        "dry_run": dry_run,
        "project": project,
        "project_slug": project_slug,
        "rubric": rubric,
        "project_dir": _rel(project_dir, repo),
        "raw_dir": _rel(raw_dir, repo),
        "workspace_dir": _rel(workspace_dir, repo),
        "source_type_map": _rel(source_type_map, repo),
        "created_dirs": [] if dry_run else [_rel(path, repo) for path in missing],
        "existing_dirs": [_rel(path, repo) for path in existing],
        "created_files": [] if dry_run or not source_type_map_missing else [_rel(source_type_map, repo)],
        "would_create_files": [_rel(source_type_map, repo)] if dry_run and source_type_map_missing else [],
        "would_create_dirs": [_rel(path, repo) for path in missing] if dry_run else [],
        "next_steps": [
            f"Put source documents under {_rel(raw_dir, repo)}.",
            "Type each source with source_type frontmatter or raw/source_type_map.json.",
            "Compile the source/evidence chain before routing into the loop.",
            "Create or validate project intake before treating the trace as ready.",
        ],
        "next_commands": [
            f"ztare project source-check --project {project_slug} --json",
            f"make evidence-prepare PROJECT={project_slug} MODEL={model}",
            "ztare project intake create --help",
            trace_command,
        ],
        "non_actions": [
            "does not launch autoresearch",
            "does not enqueue out-of-loop work",
            "does not create evidence claims",
        ],
    }


def render_text(report: dict[str, Any]) -> str:
    action = "Would create" if report.get("dry_run") else "Created"
    dirs = report.get("would_create_dirs") if report.get("dry_run") else report.get("created_dirs")
    lines = [
        "ZTARE source project surface",
        "",
        f"project: {report['project_slug']}",
        f"project_dir: {report['project_dir']}",
        f"{action} directories:",
    ]
    if dirs:
        lines.extend(f"  {path}" for path in dirs)
    else:
        lines.append("  none; surface already exists")
    if report.get("existing_dirs"):
        lines.append("Existing directories:")
        lines.extend(f"  {path}" for path in report["existing_dirs"])
    files = report.get("would_create_files") if report.get("dry_run") else report.get("created_files")
    if files:
        file_action = "Would create files:" if report.get("dry_run") else "Created files:"
        lines.append(file_action)
        lines.extend(f"  {path}" for path in files)
    if report.get("source_type_map"):
        lines.append(f"source_type_map: {report['source_type_map']}")
    lines.append("Next steps:")
    lines.extend(f"  {step}" for step in report["next_steps"])
    lines.append("Next commands:")
    lines.extend(f"  {command}" for command in report["next_commands"])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Project slug or repo-relative projects/<slug> path.")
    parser.add_argument("--rubric", help="Optional rubric slug to include in the trace command.")
    parser.add_argument("--model", default="gemini", help="Model label to render in evidence-prepare command.")
    parser.add_argument("--repo", type=Path, default=REPO, help="Repo root for tests or alternate checkouts.")
    parser.add_argument("--dry-run", action="store_true", help="Print the surface that would be created.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = init_source_project(
            project=args.project,
            rubric=args.rubric,
            model=args.model,
            repo=args.repo,
            dry_run=args.dry_run,
        )
    except ValueError as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0


def _rel(path: Path, repo: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo.resolve()))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
