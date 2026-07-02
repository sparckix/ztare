"""Scoring-guide writer shared by CLI and D4."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ztare.common.paths import REPO_ROOT
from ztare.workspace.project_file import validate_project_slug


SCORING_GUIDE_RECEIPT_SCHEMA = "ztare-forensic-workbench-scoring-guide-receipt-v1"


def repo_rel(path: Path, *, root: Path = REPO_ROOT) -> str:
    return Path(path).resolve().relative_to(root.resolve()).as_posix()


def rubric_path_for_edit(rubric: str, *, root: Path = REPO_ROOT) -> Path:
    name = str(rubric or "").strip()
    if not name:
        raise ValueError("rubric is required")
    candidate = Path(name)
    if candidate.is_absolute():
        raise ValueError("scoring guide path must be relative to the repository")
    if candidate.suffix != ".json":
        candidate = Path("rubrics") / f"{name}.json"
    resolved = (root.resolve() / candidate).resolve()
    rubrics_root = (root.resolve() / "rubrics").resolve()
    if resolved != rubrics_root and rubrics_root not in resolved.parents:
        raise ValueError("scoring guide edits must stay under rubrics/")
    if resolved.suffix != ".json":
        raise ValueError("scoring guide path must be a JSON file")
    return resolved


def _read_text(path: Path, storage: Any = None) -> str:
    if storage is not None and hasattr(storage, "read_text"):
        return storage.read_text(path, errors="replace")
    return path.read_text(encoding="utf-8", errors="replace")


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


def _run_validator(command: list[str], *, root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )


def save_scoring_guide(
    *,
    project: str,
    text: Any,
    rubric: str | None = None,
    intake: str | None = None,
    root: Path = REPO_ROOT,
    storage: Any = None,
    run_command: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    slug = validate_project_slug(project)
    rubric = rubric or slug
    raw_text = str(text or "")
    if not raw_text.strip():
        raise ValueError("scoring guide text is required")
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"scoring guide is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("scoring guide must be a JSON object")
    project_root = root.resolve() / "projects" / slug
    if not project_root.exists():
        raise FileNotFoundError(f"project does not exist: projects/{slug}")
    rubric_path = rubric_path_for_edit(rubric, root=root)
    rel_path = repo_rel(rubric_path, root=root)
    normalized_text = raw_text.rstrip() + "\n"
    before_text = _read_text(rubric_path, storage) if rubric_path.exists() else ""
    if before_text == normalized_text:
        raise ValueError("scoring guide has no changes")
    _write_text(rubric_path, normalized_text, storage)
    command = ["make", "validate-rubric", f"PROJECT={slug}", f"RUBRIC={rel_path}"]
    proc = run_command(command) if run_command is not None else _run_validator(command, root=root.resolve())
    workspace = project_root / "workspace"
    receipt_path = workspace / "forensic_workbench_scoring_guides.jsonl"
    latest_path = workspace / "forensic_workbench_latest_scoring_guide.json"
    sha256 = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    key = f"{slug}::{str(intake or '').strip()}" if str(intake or "").strip() else slug
    receipt = {
        "schema": SCORING_GUIDE_RECEIPT_SCHEMA,
        "applied_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project": slug,
        "rubric": str(rubric),
        "intake": str(intake or ""),
        "project_key": key,
        "case_key": key,
        "rubric_path": rel_path,
        "sha256": sha256,
        "validation_returncode": proc.returncode,
        "validation_accepted": proc.returncode == 0,
    }
    _append_jsonl(receipt_path, receipt, storage)
    _write_text(latest_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n", storage)
    return {
        "ok": True,
        "saved": True,
        "accepted": proc.returncode == 0,
        "schema": SCORING_GUIDE_RECEIPT_SCHEMA,
        "served_from": "ztare_scoring_guide",
        "project": slug,
        "rubric": rubric,
        "intake": str(intake or ""),
        "path": rel_path,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "receipt": receipt,
        "receipt_path": repo_rel(receipt_path, root=root),
        "latest": repo_rel(latest_path, root=root),
        "write_paths": [rel_path, repo_rel(receipt_path, root=root), repo_rel(latest_path, root=root)],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Save a Project Workbench scoring guide.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--rubric")
    parser.add_argument("--intake")
    parser.add_argument("--from", dest="text_path", required=True, help="Scoring-guide JSON file.")
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = save_scoring_guide(
            project=args.project,
            rubric=args.rubric,
            intake=args.intake,
            text=Path(args.text_path).read_text(encoding="utf-8"),
            root=args.repo,
        )
    except Exception as exc:  # noqa: BLE001 - concise CLI failure.
        print(f"ztare forensic-workbench save-scoring-guide: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Saved scoring guide: {result['path']}")
        print(f"Receipt: {result['latest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
