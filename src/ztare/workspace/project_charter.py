"""Project-charter writer shared by CLI and D4."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ztare.common.paths import REPO_ROOT
from ztare.common.scaffold_project_charter import render_charter_from_fields
from ztare.workspace.project_file import validate_project_slug


CHARTER_EDIT_SCHEMA = "ztare-forensic-workbench-charter-edit-receipt-v1"


def repo_rel(path: Path, *, root: Path = REPO_ROOT) -> str:
    return Path(path).resolve().relative_to(root.resolve()).as_posix()


def charter_rel(project: str) -> str:
    return f"projects/{validate_project_slug(project)}/project_charter.md"


def charter_path(project: str, *, root: Path = REPO_ROOT) -> Path:
    return root.resolve() / charter_rel(project)


def _read_bytes(path: Path, storage: Any = None) -> bytes:
    if storage is not None and hasattr(storage, "read_bytes"):
        return storage.read_bytes(path)
    return path.read_bytes()


def _read_text(path: Path, storage: Any = None) -> str:
    if storage is not None and hasattr(storage, "read_text"):
        return storage.read_text(path, errors="replace")
    return path.read_text(encoding="utf-8", errors="replace")


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


def section_present(text: str, names: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?im)^##+\s+{re.escape(name)}\s*$", text) for name in names)


def validation_payload(path: Path, *, root: Path = REPO_ROOT, storage: Any = None) -> dict[str, Any]:
    rel_path = repo_rel(path, root=root)
    if not path.exists():
        return {
            "ok": False,
            "path": rel_path,
            "status": "missing",
            "issues": ["project_charter.md is missing"],
        }
    text = _read_text(path, storage)
    checks = {
        "project_question": section_present(text, ("Project Question", "Core Question", "Task", "Eigenquestion", "Observable")),
        "working_thesis": section_present(text, ("Working Thesis", "Bounded Claim", "Thesis", "Claim")),
        "change_test": section_present(text, ("What Would Change It", "Next Falsifier", "Falsifier", "Farther-Tail Contract")),
        "scope_limits": section_present(text, ("Scope Limits", "Non-Claims", "Non Claims", "Grammar Constraint", "Interface Contract (MANDATORY)")),
        "run_contract": section_present(text, ("Run Contract", "Execution Boundary", "Grading Protocol", "Deterministic Gates", "Interface Contract (MANDATORY)")),
    }
    issues = [key for key, ok in checks.items() if not ok]
    if len([line for line in text.splitlines() if line.strip()]) < 8:
        issues.append("charter is very short")
    return {
        "ok": not issues,
        "path": rel_path,
        "status": "usable" if not issues else "needs_review",
        "checks": checks,
        "issues": issues,
        "line_count": len(text.splitlines()),
    }


def ensure_charter(
    *,
    project: str,
    title: str | None = None,
    task: str,
    bounded_claim: str,
    next_falsifier: str,
    notes: str = "",
    source_refs: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    non_claims: list[str] | None = None,
    root: Path = REPO_ROOT,
    storage: Any = None,
) -> str | None:
    path = charter_path(project, root=root)
    if path.exists():
        return None
    _write_text(
        path,
        render_charter_from_fields(
            title=title or validate_project_slug(project).replace("_", " ").replace("-", " ").title(),
            task=task,
            bounded_claim=bounded_claim,
            next_falsifier=next_falsifier,
            notes=notes,
            source_refs=source_refs,
            evidence_refs=evidence_refs,
            non_claims=non_claims,
        ),
        storage,
    )
    return repo_rel(path, root=root)


def apply_charter_edit(
    *,
    project: str,
    text: str,
    rubric: str | None = None,
    intake: str | None = None,
    root: Path = REPO_ROOT,
    storage: Any = None,
) -> dict[str, Any]:
    slug = validate_project_slug(project)
    project_root = root.resolve() / "projects" / slug
    if not project_root.exists():
        raise FileNotFoundError(f"project does not exist: projects/{slug}")
    path = charter_path(slug, root=root)
    before_bytes = _read_bytes(path, storage) if path.exists() else b""
    normalized_text = str(text or "").replace("\r\n", "\n").replace("\r", "\n").rstrip() + "\n"
    if not normalized_text.strip():
        raise ValueError("charter text is required")
    after_bytes = normalized_text.encode("utf-8")
    if before_bytes == after_bytes:
        raise ValueError("charter edit has no changed text")
    _write_bytes(path, after_bytes, storage)
    validation = validation_payload(path, root=root, storage=storage)
    workspace = project_root / "workspace"
    ledger_path = workspace / "forensic_workbench_charter_edits.jsonl"
    latest_path = workspace / "forensic_workbench_latest_charter_edit.json"
    intake_value = str(intake or "").strip()
    key = f"{slug}::{intake_value}" if intake_value else slug
    receipt = {
        "schema": CHARTER_EDIT_SCHEMA,
        "applied_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "project": slug,
        "rubric": str(rubric or slug),
        "intake": intake_value,
        "project_key": key,
        "case_key": key,
        "charter_path": repo_rel(path, root=root),
        "before_sha256": hashlib.sha256(before_bytes).hexdigest(),
        "after_sha256": hashlib.sha256(after_bytes).hexdigest(),
        "validation_status": validation.get("status"),
        "validation_issues": validation.get("issues") or [],
    }
    _append_jsonl(ledger_path, receipt, storage)
    _write_text(latest_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n", storage)
    return {
        "ok": True,
        "project": slug,
        "ledger": repo_rel(ledger_path, root=root),
        "latest": repo_rel(latest_path, root=root),
        "receipt": receipt,
        "validation": validation,
        "write_paths": [repo_rel(path, root=root), repo_rel(ledger_path, root=root), repo_rel(latest_path, root=root)],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Save a Project Workbench project charter.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--rubric")
    parser.add_argument("--intake")
    parser.add_argument("--from", dest="text_path", required=True, help="Project-charter Markdown file.")
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = apply_charter_edit(
            project=args.project,
            rubric=args.rubric,
            intake=args.intake,
            text=Path(args.text_path).read_text(encoding="utf-8"),
            root=args.repo,
        )
    except Exception as exc:  # noqa: BLE001 - concise CLI failure.
        print(f"ztare forensic-workbench save-charter: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Saved project charter: {result['write_paths'][0]}")
        print(f"Receipt: {result['latest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
