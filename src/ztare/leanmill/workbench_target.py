"""LeanMill workbench target writer.

This is the shared write contract behind the local Workbench and
``ztare leanmill target``. It saves a formalization target plus research notes
without launching proof search.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TARGET_SCHEMA = "ztare-forensic-workbench-leanmill-blueprint-v1"
TARGET_HISTORY_SCHEMA = "ztare-forensic-workbench-leanmill-blueprint-receipt-v1"
SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,80}$")
PROJECT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,120}$")
REPO = Path(__file__).resolve().parents[3]


# Shared common storage provider (S3/DB-swappable), aliased to the historical names so callers
# (`storage: TargetStorage`, `FileTargetStorage(repo)`) are unchanged. Was a byte-identical copy of the
# workbench_actions store — now one place.
from ztare.common.storage import FileStorage as FileTargetStorage  # noqa: E402
from ztare.common.storage import StorageProvider as TargetStorage  # noqa: E402


def repo_rel(path: Path, *, repo: Path = REPO) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def normalize_slug(raw_slug: Any, title: str) -> str:
    slug = str(raw_slug or "").strip()
    if not slug:
        slug = re.sub(r"[^A-Za-z0-9_-]+", "_", title.strip()).strip("_").lower()
    if slug.endswith("_blueprint"):
        slug = slug[: -len("_blueprint")]
    if not SLUG_RE.fullmatch(slug):
        raise ValueError("target slug must use letters, numbers, underscores, or hyphens")
    return slug


def normalize_non_claims(raw_value: Any) -> list[str]:
    if isinstance(raw_value, list):
        values = raw_value
    else:
        values = str(raw_value or "").splitlines()
    return [str(item).strip().lstrip("-").strip() for item in values if str(item).strip().lstrip("-").strip()]


def render_target(*, title: str, target_statement: str, notes: str, non_claims: list[str]) -> str:
    non_claim_lines = "\n".join(f"- {item}" for item in non_claims) if non_claims else "- No limits recorded yet."
    notes_text = notes.strip() or "No research notes recorded yet."
    return (
        f"# {title}\n\n"
        "## Target\n\n"
        f"{target_statement.strip()}\n\n"
        "## Research notes\n\n"
        f"{notes_text}\n\n"
        "## Do not count this as\n\n"
        f"{non_claim_lines}\n\n"
        "## Next work\n\n"
        "- Created by: LeanMill Workbench\n"
        "- Next step: run autoformalization from this file, or solve a Lean file directly.\n"
    )


def render_project_readme(*, project: str) -> str:
    return (
        f"# LeanMill for {project}\n\n"
        "This folder holds formalization work for the project.\n\n"
        "## Folder contract\n\n"
        "- `targets/` stores target statements and research notes.\n"
        "- `lean/` stores Lean files for direct proof attempts.\n"
        "- `notes/` stores extra working notes that can feed autoformalization.\n"
        "- `history/` stores saved work from the browser and CLI.\n\n"
        "Use the Workbench or `ztare leanmill target --project "
        f"{project} ...` to add the next target.\n"
    )


AREA_SCAFFOLD_SCHEMA = "ztare-forensic-workbench-leanmill-area-scaffold-v1"
LEANMILL_AREA_DIRS = ("targets", "lean", "notes", "history")


def leanmill_folder_contract(project: str) -> dict[str, str]:
    """Canonical project-local LeanMill folder layout under projects/<project>/."""
    base = f"projects/{project}/leanmill"
    return {
        "root": base,
        "targets": f"{base}/targets",
        "lean": f"{base}/lean",
        "notes": f"{base}/notes",
        "history": f"{base}/history",
        "jobs": f"{base}/jobs",
        "readme": f"{base}/README.md",
    }


def _latest_iso(paths: list[Path]) -> str:
    times = [p.stat().st_mtime for p in paths if p.exists()]
    if not times:
        return ""
    return datetime.fromtimestamp(max(times), tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def list_project_leanmill_areas(repo: Path = REPO) -> list[dict[str, Any]]:
    """Summarize each projects/<slug>/leanmill area so the Workbench can list
    which user projects already hold formalization work, distinct from the
    curated example showcases under ztare_proofs/leanmill-formalizations."""
    projects_root = repo / "projects"
    if not projects_root.is_dir():
        return []
    areas: list[dict[str, Any]] = []
    for project_dir in sorted(p for p in projects_root.iterdir() if p.is_dir()):
        area = project_dir / "leanmill"
        if not area.is_dir():
            continue
        targets = sorted((area / "targets").glob("*.md")) if (area / "targets").is_dir() else []
        lean_files = sorted((area / "lean").glob("*.lean")) if (area / "lean").is_dir() else []
        results = sorted((area / "jobs").glob("*_result.json")) if (area / "jobs").is_dir() else []
        areas.append(
            {
                "project": project_dir.name,
                "root": repo_rel(area, repo=repo),
                "target_count": len(targets),
                "lean_file_count": len(lean_files),
                "job_count": len(results),
                "has_history": (area / "history").is_dir(),
                "latest_activity": _latest_iso([*targets, *lean_files, *results]),
                "targets": [repo_rel(p, repo=repo) for p in targets[:8]],
            }
        )
    return areas


def scaffold_project_leanmill_area(
    project: str, *, repo: Path = REPO, storage: TargetStorage | None = None
) -> dict[str, Any]:
    """Create projects/<project>/leanmill/{targets,lean,notes,history} + README.

    LeanMill projects live under the canonical autoresearch projects/ tree, so a
    new area is scaffolded against an existing project rather than a free path.
    """
    storage = storage or FileTargetStorage(repo)
    slug = str(project or "").strip()
    if not PROJECT_RE.match(slug):
        raise ValueError("project must use letters, numbers, underscores, or hyphens")
    if not (repo / "projects" / slug).is_dir():
        raise ValueError(f"project does not exist: projects/{slug}")
    contract = leanmill_folder_contract(slug)
    created: list[str] = []
    for key in LEANMILL_AREA_DIRS:
        directory = repo / contract[key]
        existed = directory.is_dir()
        storage.ensure_dir(directory)
        if not existed:
            created.append(contract[key])
    readme_path = repo / contract["readme"]
    if not storage.exists(readme_path):
        storage.write_text(readme_path, render_project_readme(project=slug))
        created.append(contract["readme"])
    return {
        "schema": AREA_SCAFFOLD_SCHEMA,
        "ok": True,
        "project": slug,
        "folder_contract": contract,
        "created_paths": created,
        "already_existed": not created,
        "write_boundary": {
            "writes_repo_files": bool(created),
            "browser_writes": False,
            "write_paths": created,
            "boundary": "Creates the project-local LeanMill folder contract; no proof job is launched.",
        },
    }


def target_payload(request: dict[str, Any], *, repo: Path = REPO, storage: TargetStorage | None = None) -> dict[str, Any]:
    storage = storage or FileTargetStorage(repo)
    if not isinstance(request, dict):
        raise ValueError("LeanMill target request must be an object")
    title = str(request.get("title") or "").strip()
    target_statement = str(request.get("target_statement") or request.get("target") or "").strip()
    notes = str(request.get("notes") or "").strip()
    if not title:
        raise ValueError("target title is required")
    if not target_statement:
        raise ValueError("target statement is required")
    if len(title) > 200:
        raise ValueError("target title is too long")
    if len(target_statement) > 20_000:
        raise ValueError("target statement is too long")
    if len(notes) > 50_000:
        raise ValueError("research notes are too long")

    slug = normalize_slug(request.get("slug"), title)
    project = str(request.get("project") or "").strip()
    if project and not PROJECT_RE.fullmatch(project):
        raise ValueError("project must use letters, numbers, underscores, or hyphens")
    non_claims = normalize_non_claims(request.get("non_claims"))
    confirmed = request.get("confirmed") is True

    folder_contract: dict[str, str] = {}
    if project:
        target_path = repo / "projects" / project / "leanmill" / "targets" / f"{slug}_target.md"
        ledger_path = repo / "projects" / project / "leanmill" / "history" / "leanmill_targets.jsonl"
        latest_path = repo / "projects" / project / "leanmill" / "history" / "latest_leanmill_target.json"
        readme_path = repo / "projects" / project / "leanmill" / "README.md"
        folder_contract = {
            "root": f"projects/{project}/leanmill",
            "targets": f"projects/{project}/leanmill/targets",
            "lean": f"projects/{project}/leanmill/lean",
            "notes": f"projects/{project}/leanmill/notes",
            "history": f"projects/{project}/leanmill/history",
            "readme": f"projects/{project}/leanmill/README.md",
        }
    else:
        formalization_root = repo / "ztare_proofs" / "leanmill-formalizations"
        target_path = formalization_root / "blueprints" / f"{slug}_blueprint.md"
        history_root = repo / "analytics" / "public" / "leanmill" / "workbench"
        ledger_path = history_root / "leanmill_blueprint_receipts.jsonl"
        latest_path = history_root / "latest_leanmill_blueprint.json"
    target_text = render_target(
        title=title,
        target_statement=target_statement,
        notes=notes,
        non_claims=non_claims,
    )
    target_bytes = target_text.encode("utf-8")
    previous_sha256 = hashlib.sha256(storage.read_bytes(target_path)).hexdigest() if storage.exists(target_path) else ""
    target_sha256 = hashlib.sha256(target_bytes).hexdigest()
    content_changed = previous_sha256 != target_sha256
    preview_sha256 = str(request.get("preview_sha256") or "").strip()
    if confirmed and preview_sha256 != target_sha256:
        raise ValueError("confirmed LeanMill target saves must include the matching preview_sha256")

    target_rel = storage.rel(target_path)
    ledger_rel = storage.rel(ledger_path)
    latest_rel = storage.rel(latest_path)
    readme_rel = storage.rel(readme_path) if project else ""
    write_paths = [target_rel, ledger_rel, latest_rel]
    if readme_rel:
        write_paths.append(readme_rel)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    history = {
        "schema": TARGET_HISTORY_SCHEMA,
        "applied_at": now,
        "project": project,
        "slug": slug,
        "title": title,
        "blueprint_path": target_rel,
        "target_path": target_rel,
        "blueprint_sha256": target_sha256,
        "target_sha256": target_sha256,
        "preview_sha256": target_sha256,
        "previous_blueprint_sha256": previous_sha256,
        "previous_target_sha256": previous_sha256,
        "content_changed": content_changed,
        "target_statement_sha256": hashlib.sha256(target_statement.encode("utf-8")).hexdigest(),
        "research_notes_sha256": hashlib.sha256(notes.encode("utf-8")).hexdigest(),
        "non_claim_count": len(non_claims),
        "confirmed": confirmed,
    }
    if confirmed:
        storage.write_text(target_path, target_text)
        if project and not storage.exists(readme_path):
            storage.write_text(readme_path, render_project_readme(project=project))
        if project:
            storage.ensure_dir(repo / "projects" / project / "leanmill" / "lean")
            storage.ensure_dir(repo / "projects" / project / "leanmill" / "notes")
        storage.append_jsonl(ledger_path, history)
        storage.write_text(latest_path, json.dumps(history, indent=2, sort_keys=True) + "\n")

    return {
        "schema": TARGET_SCHEMA,
        "ok": True,
        "status": "saved" if confirmed else "needs_confirmation",
        "requires_confirmation": not confirmed,
        "accepted": confirmed,
        "slug": slug,
        "title": title,
        "path": target_rel,
        "target_and_notes_path": target_rel,
        "blueprint_path": target_rel,
        "target_path": target_rel,
        "blueprint_sha256": target_sha256,
        "target_sha256": target_sha256,
        "preview_sha256": target_sha256,
        "previous_blueprint_sha256": previous_sha256,
        "previous_target_sha256": previous_sha256,
        "content_changed": content_changed,
        "no_change": not content_changed,
        "receipt": history if confirmed else {**history, "confirmed": False},
        "receipt_path": ledger_rel,
        "saved_history_path": ledger_rel,
        "latest": latest_rel,
        "latest_history_path": latest_rel,
        "blueprint_text": target_text,
        "target_text": target_text,
        "write_boundary": {
            "writes_project_files": bool(project),
            "writes_repo_files": not bool(project),
            "browser_writes": False,
            "storage": storage.metadata(),
            "storage_backend": storage.backend,
            "write_paths": write_paths,
            "receipt_path": ledger_rel,
            "latest_path": latest_rel,
            "primary_path": target_rel,
            "previous_sha256": previous_sha256,
            "new_sha256": target_sha256,
            "content_changed": content_changed,
            "no_change": not content_changed,
            "folder_contract": folder_contract,
        },
        "project": project,
        "folder_contract": folder_contract,
        "launch_boundary": "This saves the target and research notes only. It does not launch autoformalization or solving.",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preview or save a LeanMill formalization target with research notes.")
    parser.add_argument("--slug", default="", help="File slug. Letters, numbers, underscores, and hyphens only.")
    parser.add_argument("--project", default="", help="Optional project slug. Saves under projects/<project>/leanmill/.")
    parser.add_argument("--title", required=True, help="Human-readable target title.")
    parser.add_argument("--target", "--target-statement", dest="target_statement", required=True, help="The theorem or formalization target.")
    parser.add_argument("--notes", default="", help="Research notes to save with the target.")
    parser.add_argument("--notes-file", default="", help="Read research notes from a UTF-8 file.")
    parser.add_argument("--non-claim", action="append", default=[], help="Limit to record. Repeatable.")
    parser.add_argument("--save", action="store_true", help="Write the target and saved history.")
    parser.add_argument("--preview-sha256", default="", help="Required when --save is used after a preview.")
    parser.add_argument("--yes", action="store_true", help="Save in one command without copying the preview hash.")
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    notes = args.notes
    if args.notes_file:
        notes = Path(args.notes_file).read_text(encoding="utf-8")
    if args.save and not args.preview_sha256 and not args.yes:
        raise SystemExit("--save requires --preview-sha256 from a preview, or --yes for a one-command explicit save")
    preview_sha256 = args.preview_sha256
    if args.save and args.yes and not preview_sha256:
        preview = target_payload(
            {
                "slug": args.slug,
                "project": args.project,
                "title": args.title,
                "target_statement": args.target_statement,
                "notes": notes,
                "non_claims": args.non_claim,
                "confirmed": False,
            }
        )
        preview_sha256 = str(preview["preview_sha256"])
    payload = target_payload(
        {
            "slug": args.slug,
            "project": args.project,
            "title": args.title,
            "target_statement": args.target_statement,
            "notes": notes,
            "non_claims": args.non_claim,
            "confirmed": args.save,
            "preview_sha256": preview_sha256,
        }
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload["status"])
        print(f"target: {payload['target_path']}")
        print(f"preview_sha256: {payload['preview_sha256']}")
        if payload["accepted"]:
            print(f"saved history: {payload['receipt_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
