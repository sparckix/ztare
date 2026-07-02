"""Saved research-map writer shared by CLI and D4."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ztare.common.paths import REPO_ROOT
from ztare.workspace.project_file import validate_project_slug


RESEARCH_MAP_SCHEMA = "ztare-forensic-workbench-research-map-v1"
RESEARCH_MAP_RECEIPT_SCHEMA = "ztare-forensic-workbench-research-map-receipt-v1"


def safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _rows(value: Any) -> list[dict[str, Any]]:
    return [row for row in value or [] if isinstance(row, dict)]


def _section(sections: list[dict[str, Any]], section_id: str) -> dict[str, Any]:
    return next((row for row in sections if str(row.get("id") or "") == section_id), {})


def _count_details(section: dict[str, Any]) -> int:
    return len([item for item in section.get("details") or [] if str(item).strip()])


def enrich_research_map_payload(research_map: dict[str, Any]) -> dict[str, Any]:
    """Add stable compiler-facing fields to a prepared research-map payload."""

    payload = dict(research_map)
    sections = _rows(payload.get("sections"))
    orientation = _section(sections, "orientation")
    support = _section(sections, "strongest_support")
    tensions = _section(sections, "tensions")
    branches = _section(sections, "branches")
    project_work = _section(sections, "project_work")
    synthesis = _section(sections, "synthesis")
    next_action = payload.get("next_action") if isinstance(payload.get("next_action"), dict) else {}

    tension_count = safe_int(payload.get("tension_count")) or _count_details(tensions)
    branch_count = safe_int(payload.get("branch_count")) or _count_details(branches)
    supported_point_count = safe_int(payload.get("supported_point_count")) or _count_details(support)
    project_work_file_count = safe_int(payload.get("project_work_file_count")) or len(project_work.get("files") or [])
    attention_sections = [
        row
        for row in sections
        if any(token in f"{row.get('status') or ''} {row.get('summary') or ''}".lower() for token in ("need", "missing", "blocked", "warning", "tension", "attention"))
    ]
    output_objects = [
        str(payload.get("target_path") or ""),
        str(payload.get("json_path") or ""),
        str(payload.get("ledger_path") or ""),
        str(payload.get("latest_path") or ""),
    ]

    payload.update(
        {
            "section_count": len(sections),
            "tension_count": tension_count,
            "branch_count": branch_count,
            "supported_point_count": supported_point_count,
            "project_work_file_count": project_work_file_count,
            "attention_section_count": len(attention_sections),
            "next_action": {
                "label": str(next_action.get("label") or ""),
                "detail": str(next_action.get("detail") or ""),
                "workspace": str(next_action.get("workspace") or ""),
                "subsection": str(next_action.get("subsection") or ""),
            },
            "project_meaning": {
                "thesis": str(orientation.get("summary") or ""),
                "support": str(support.get("summary") or ""),
                "limits": str(tensions.get("summary") or ""),
                "next": str(branches.get("summary") or ""),
                "report_state": str(synthesis.get("summary") or ""),
            },
            "compiler_contract": {
                "input_object": "project files, project brief, source/evidence state, run history, and report readiness",
                "check_or_transform": "research map projection over current project state",
                "output_objects": [path for path in output_objects if path],
                "falsifier": "If linked sections lack backing files, next action, or saved history, the map is only an orientation aid.",
            },
        }
    )
    if not str(payload.get("summary") or "").strip():
        payload["summary"] = (
            f"{tension_count} tension(s), {branch_count} branch(es), "
            f"{supported_point_count} supported point(s), {project_work_file_count} project work file(s)."
        )
    return payload


def map_paths(project: str, *, root: Path = REPO_ROOT) -> dict[str, Path]:
    slug = validate_project_slug(project)
    workspace = root.resolve() / "projects" / slug / "workspace"
    return {
        "markdown": workspace / "research_map.md",
        "json": workspace / "research_map.json",
        "ledger": workspace / "forensic_workbench_research_maps.jsonl",
        "latest": workspace / "forensic_workbench_latest_research_map.json",
    }


def repo_rel(path: Path, *, root: Path = REPO_ROOT) -> str:
    return Path(path).resolve().relative_to(root.resolve()).as_posix()


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


def save_prepared_research_map(
    *,
    project: str,
    research_map: dict[str, Any],
    rubric: str | None = None,
    intake: str | None = None,
    root: Path = REPO_ROOT,
    storage: Any = None,
) -> dict[str, Any]:
    slug = validate_project_slug(project)
    if not isinstance(research_map, dict):
        raise ValueError("research_map must be a JSON object")
    if str(research_map.get("schema") or "") != RESEARCH_MAP_SCHEMA:
        raise ValueError("research_map schema is not compatible with this workbench")
    project_root = root.resolve() / "projects" / slug
    if not project_root.exists():
        raise FileNotFoundError(f"project does not exist: projects/{slug}")
    paths = map_paths(slug, root=root)
    json_payload = {key: value for key, value in research_map.items() if key not in {"markdown", "write_boundary"}}
    _write_text(paths["markdown"], str(research_map.get("markdown") or ""), storage)
    _write_text(paths["json"], json.dumps(json_payload, indent=2, sort_keys=True) + "\n", storage)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    receipt = {
        "schema": RESEARCH_MAP_RECEIPT_SCHEMA,
        "kind": "research_map",
        "project": slug,
        "rubric": str(research_map.get("rubric") or rubric or ""),
        "intake": str(research_map.get("intake") or intake or ""),
        "applied_at": now,
        "summary": str(research_map.get("summary") or ""),
        "path": repo_rel(paths["ledger"], root=root),
        "markdown_path": repo_rel(paths["markdown"], root=root),
        "json_path": repo_rel(paths["json"], root=root),
        "latest_path": repo_rel(paths["latest"], root=root),
        "section_count": len(research_map.get("sections") or []),
        "graph_summary_count": safe_int(research_map.get("graph_summary_count")),
        "write_boundary": research_map.get("write_boundary") if isinstance(research_map.get("write_boundary"), dict) else {},
    }
    _append_jsonl(paths["ledger"], receipt, storage)
    _write_text(paths["latest"], json.dumps(receipt, indent=2, sort_keys=True) + "\n", storage)
    return {
        "ok": True,
        "accepted": True,
        "schema": RESEARCH_MAP_RECEIPT_SCHEMA,
        "served_from": "ztare_research_map",
        "project": slug,
        "research_map": research_map,
        "receipt": receipt,
        "write_paths": [receipt["markdown_path"], receipt["json_path"], receipt["path"], receipt["latest_path"]],
        "write_boundary": research_map.get("write_boundary"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Save a prepared Project Workbench research map.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--rubric")
    parser.add_argument("--intake")
    parser.add_argument("--from", dest="map_path", required=True, help="Prepared research-map JSON.")
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = json.loads(Path(args.map_path).read_text(encoding="utf-8"))
        result = save_prepared_research_map(
            project=args.project,
            rubric=args.rubric,
            intake=args.intake,
            research_map=payload,
            root=args.repo,
        )
    except Exception as exc:  # noqa: BLE001 - concise CLI failure.
        print(f"ztare forensic-workbench save-research-map: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Saved research map: {result['receipt']['markdown_path']}")
        print(f"Receipt: {result['receipt']['latest_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
