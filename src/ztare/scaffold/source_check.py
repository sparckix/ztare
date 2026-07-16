"""Offline source-ingest preflight for project userland.

This checks raw source files and source_type declarations before the
LLM-backed evidence compiler runs. It does not compile evidence, launch
autoresearch, or enqueue work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


_TRANSITION_CARRIER_CLASSES = {
    "grid_world",
    "interactive_environment",
    "worldmodel",
}
_CANONICAL_EPISODE_RE = re.compile(r"episode_[0-9]{3}\.jsonl$")


def _rubric_payload(
    *,
    rubric: str | Path | dict[str, Any] | None,
    project_dir: Path,
    repo: Path,
) -> dict[str, Any]:
    if isinstance(rubric, dict):
        return dict(rubric)
    candidates: list[Path] = []
    if rubric:
        raw = Path(str(rubric))
        candidates.extend(
            [
                raw,
                repo / raw,
                repo / "rubrics" / raw,
                repo / "rubrics" / f"{raw}.json",
            ]
        )
    candidates.append(repo / "rubrics" / f"{project_dir.name}.json")
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def _first_transition_row(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    return None, "first transition is not a JSON object"
                missing = sorted({"t", "s", "a", "s_next"} - set(payload))
                if missing:
                    return None, f"first transition lacks fields: {', '.join(missing)}"
                return payload, None
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"could not read first transition: {type(exc).__name__}: {exc}"
    return None, "episode contains no transition rows"


def _check_transition_project(
    *,
    project: str,
    project_dir: Path,
    repo: Path,
    rubric_data: dict[str, Any],
) -> dict[str, Any]:
    """Validate the transition-stream carrier without compiling it as prose.

    Only canonical episode logs belong to this carrier. Evaluation slices and
    fleet scratch logs are downstream or provisional artifacts, so their
    presence cannot create source-typing debt or satisfy admission.
    """
    raw_dir = project_dir / "raw"
    episode_dir = raw_dir / "episodes"
    blocking: list[str] = []
    warnings: list[str] = []
    rows: list[dict[str, Any]] = []
    if not project_dir.exists():
        blocking.append("project directory is missing")
    if not episode_dir.is_dir():
        blocking.append("canonical episode directory is missing")
        episodes: list[Path] = []
    else:
        episodes = sorted(
            path
            for path in episode_dir.iterdir()
            if path.is_file() and _CANONICAL_EPISODE_RE.fullmatch(path.name)
        )
        if not episodes:
            blocking.append("no canonical episode logs are present")

    for path in episodes:
        first, error = _first_transition_row(path)
        if error:
            blocking.append(f"{_rel(path, repo)}: {error}")
            continue
        byte_sha256 = _sha256_file(path)
        sidecar = path.with_name(f"{path.stem}.identity.json")
        identity_status = "not_declared"
        if sidecar.is_file():
            try:
                sidecar_payload = json.loads(sidecar.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                blocking.append(
                    f"{_rel(sidecar, repo)} is unreadable: {type(exc).__name__}: {exc}"
                )
                sidecar_payload = {}
            declared_sha = str(sidecar_payload.get("episode_sha256") or "")
            if sidecar_payload.get("schema") != "ztare-episode-identity-sidecar-v1":
                blocking.append(f"{_rel(sidecar, repo)} has an unsupported schema")
                identity_status = "invalid"
            elif declared_sha != byte_sha256:
                blocking.append(f"{_rel(sidecar, repo)} does not bind the episode bytes")
                identity_status = "stale"
            else:
                identity_status = "bound"
        rows.append(
            {
                "path": _rel(path, repo),
                "relative_raw_path": path.relative_to(raw_dir).as_posix(),
                "source_type": "source_evidence",
                "source_type_source": "transition_carrier_contract",
                "invalid_source_type_declaration": False,
                "sha256": byte_sha256,
                "bytes": path.stat().st_size,
                "identity_status": identity_status,
                "first_transition": {
                    "t": first.get("t") if first else None,
                    "action_kind": type(first.get("a")).__name__ if first else None,
                    "state_kind": type(first.get("s")).__name__ if first else None,
                },
            }
        )

    ok = not blocking
    return {
        "schema": "ztare-evidence-carrier-admission-v1",
        "ok": ok,
        "status": "ready_for_kernel" if ok else "blocked",
        "project": project,
        "project_slug": project_dir.name,
        "project_dir": _rel(project_dir, repo),
        "raw_dir": _rel(raw_dir, repo),
        "carrier_kind": "transition_stream",
        "substrate_class": str(rubric_data.get("substrate_class") or ""),
        "requires_source_index": False,
        "requires_compiled_evidence": False,
        "source_count": len(rows),
        "source_evidence_count": len(rows),
        "untyped_source_count": 0,
        "unsupported_file_count": 0,
        "empty_file_count": 0,
        "blocking": blocking,
        "warnings": warnings,
        "sources": rows,
        "next_steps": [] if ok else ["Repair the canonical transition carrier before launch."],
        "next_commands": [],
        "non_actions": [
            "does not call an LLM",
            "does not compile transition rows as prose",
            "does not inspect evaluation slices as admission evidence",
            "does not launch autoresearch",
        ],
    }


def check_evidence_project(
    *,
    project: str,
    repo: Path = REPO,
    rubric: str | Path | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dispatch evidence admission by the carrier's governing identity."""
    repo = repo.resolve()
    project_dir = project_dir_for(repo, project)
    rubric_data = _rubric_payload(
        rubric=rubric,
        project_dir=project_dir,
        repo=repo,
    )
    carrier_kind = str(rubric_data.get("evidence_carrier_kind") or "").strip()
    substrate_class = str(rubric_data.get("substrate_class") or "").strip().lower()
    if carrier_kind == "transition_stream" or substrate_class in _TRANSITION_CARRIER_CLASSES:
        return _check_transition_project(
            project=project,
            project_dir=project_dir,
            repo=repo,
            rubric_data=rubric_data,
        )
    report = check_source_project(project=project, repo=repo)
    report["carrier_kind"] = "source_documents"
    report["substrate_class"] = substrate_class
    report["requires_source_index"] = True
    report["requires_compiled_evidence"] = True
    return report


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
        model_hint = os.environ.get("ZTARE_MODEL", "")
        model_part = f" MODEL={model_hint}" if model_hint else ""
        next_commands.append(f"make evidence-prepare PROJECT={project_dir.name}{model_part}")

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
    parser.add_argument(
        "--rubric",
        help=(
            "Optional rubric name/path. When supplied, admission is dispatched "
            "to the rubric's evidence-carrier contract."
        ),
    )
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
        report = (
            check_evidence_project(
                project=args.project,
                repo=args.repo,
                rubric=args.rubric,
            )
            if args.rubric
            else check_source_project(project=args.project, repo=args.repo)
        )
    except ValueError as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0 if args.no_fail or report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
