#!/usr/bin/env python3
"""GP-226 charter-commit — apply an advisory-mode charter-critic patch
candidate.

Usage:
    python scripts/public/control/charter_commit.py <project_slug> --run <run_id>
    python scripts/public/control/charter_commit.py <project_slug> --run <run_id> --patches 1,3

Reads ``projects/<slug>/workspace/charter_patch_candidate_<run_id>.md``
along with the structured ledger entries in ``charter_patches.jsonl``
that have ``mode=advisory`` and ``committed=false``, applies each
selected patch to its target file, and updates the ledger.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.ztare.orchestrator.charter_critic import (  # noqa: E402
    AUTO_PATCH_LEDGER,
    CharterPatch,
    _apply_patch,
)


def _load_pending_for_run(project_dir: Path, run_id: str) -> list[dict]:
    ledger = project_dir / "workspace" / AUTO_PATCH_LEDGER
    if not ledger.exists():
        return []
    out = []
    for raw in ledger.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if (
            entry.get("created_run_id") == run_id
            and entry.get("mode") == "advisory"
            and entry.get("committed") is False
        ):
            out.append(entry)
    return out


def _rewrite_ledger_committed(project_dir: Path, run_id: str, committed_shas: set[str]) -> None:
    ledger = project_dir / "workspace" / AUTO_PATCH_LEDGER
    if not ledger.exists():
        return
    lines: list[str] = []
    for raw in ledger.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            lines.append(raw)
            continue
        body = entry.get("body", "")
        import hashlib
        sha = hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]
        if (
            entry.get("created_run_id") == run_id
            and entry.get("mode") == "advisory"
            and sha in committed_shas
        ):
            entry["committed"] = True
        lines.append(json.dumps(entry))
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply advisory charter patches.")
    parser.add_argument("project", help="project slug (under projects/)")
    parser.add_argument("--run", required=True, help="run_id from the candidate filename")
    parser.add_argument("--patches", default="all",
                        help="comma-separated 1-indexed patch numbers, or 'all' (default)")
    parser.add_argument("--dry-run", action="store_true",
                        help="show what would be applied without writing")
    args = parser.parse_args()

    project_dir = REPO_ROOT / "projects" / args.project
    if not project_dir.exists():
        print(f"ERROR: project dir not found: {project_dir}", file=sys.stderr)
        return 1

    pending = _load_pending_for_run(project_dir, args.run)
    if not pending:
        print(f"No pending advisory patches for run={args.run} in {project_dir}")
        return 0

    print(f"Found {len(pending)} pending patch(es) for run={args.run}:")
    for i, entry in enumerate(pending, 1):
        print(f"  [{i}] {entry.get('reframe_type')} -> {entry.get('target')}")

    if args.patches == "all":
        selected_indices = list(range(1, len(pending) + 1))
    else:
        try:
            selected_indices = [int(s.strip()) for s in args.patches.split(",") if s.strip()]
        except ValueError:
            print(f"ERROR: --patches must be 'all' or comma-separated 1-indexed integers", file=sys.stderr)
            return 1

    committed_shas: set[str] = set()
    for idx in selected_indices:
        if idx < 1 or idx > len(pending):
            print(f"  skip: index {idx} out of range", file=sys.stderr)
            continue
        entry = pending[idx - 1]
        patch = CharterPatch(
            target=entry["target"],
            section_id=entry["section_id"],
            operation=entry["operation"],
            body=entry["body"],
            reframe_type=entry["reframe_type"],
            expiry_runs=entry["expiry_runs"],
            fingerprint_match=entry["fingerprint_match"],
            sanitation_checks_passed=entry["sanitation_checks_passed"],
            created_run_id=entry["created_run_id"],
            created_utc=entry["created_utc"],
        )
        if args.dry_run:
            print(f"  [dry-run] would apply [{idx}] {patch.reframe_type} -> {patch.target}")
            continue
        try:
            applied_path = _apply_patch(project_dir, patch)
            print(f"  applied [{idx}] {patch.reframe_type} -> {applied_path.relative_to(project_dir)}")
            committed_shas.add(patch.body_sha)
        except Exception as exc:
            print(f"  ERROR applying [{idx}] {patch.reframe_type}: {exc}", file=sys.stderr)

    if not args.dry_run and committed_shas:
        _rewrite_ledger_committed(project_dir, args.run, committed_shas)
        print(f"Marked {len(committed_shas)} patch(es) as committed in ledger.")

        # Post-commit validation — re-run validate_rubric.py to catch any
        # rubric/charter malformation introduced by the patches.
        try:
            import subprocess as _sp
            rubric_path = REPO_ROOT / "rubrics" / f"{args.project}.json"
            if rubric_path.exists():
                print("\n--- Post-commit pre-flight validation ---")
                proc = _sp.run(
                    [sys.executable,
                     str(REPO_ROOT / "scripts" / "validate_rubric.py"),
                     args.project, "--rubric", str(rubric_path)],
                    cwd=str(REPO_ROOT),
                )
                if proc.returncode != 0:
                    print("\n⚠️  Post-commit validation FAILED — review the patches.")
                    return 2
        except Exception as exc:
            print(f"(post-commit validation skipped: {exc})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
