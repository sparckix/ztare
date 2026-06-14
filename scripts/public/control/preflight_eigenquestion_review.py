#!/usr/bin/env python3
"""Preflight visibility for advisory eigenquestion proposals.

Eigenquestion generation is advisory by design: it writes
``projects/<slug>/proposed_eigenquestion_*.md`` and never edits
``project_charter.md``. That is the right authority boundary, but it creates a
launch risk: an autoresearch run can start from an older charter while a newer
proposal is waiting for review.

This preflight makes that state visible on every launch path. It does not
rewrite the charter. Default mode warns and exits 0; strict mode exits 1 when a
proposal is newer than the charter.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class EigenquestionProposal:
    path: str
    mtime: str
    status: str


@dataclass(frozen=True)
class EigenquestionPreflight:
    project: str
    project_dir: str
    charter: str
    charter_exists: bool
    charter_mtime: str | None
    proposal_count: int
    pending_count: int
    status: str
    proposals: list[EigenquestionProposal]
    review_command: str
    strict: bool = False

    @property
    def ok(self) -> bool:
        return not (self.strict and self.pending_count > 0)


def _iso_from_mtime(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    except OSError:
        return None


def _rel(repo: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def inspect_eigenquestion_review(
    project: str,
    *,
    repo: Path = REPO,
    strict: bool = False,
) -> EigenquestionPreflight:
    project_dir = repo / "projects" / project
    charter = project_dir / "project_charter.md"
    charter_exists = charter.exists()
    charter_mtime = charter.stat().st_mtime if charter_exists else None
    proposals: list[EigenquestionProposal] = []
    if project_dir.exists():
        for proposal in sorted(project_dir.glob("proposed_eigenquestion_*.md")):
            try:
                mtime = proposal.stat().st_mtime
            except OSError:
                continue
            pending = (not charter_exists) or (charter_mtime is not None and mtime > charter_mtime)
            proposals.append(
                EigenquestionProposal(
                    path=_rel(repo, proposal),
                    mtime=datetime.fromtimestamp(mtime, timezone.utc).isoformat(),
                    status="pending_review" if pending else "older_than_charter",
                )
            )
    pending_count = sum(1 for proposal in proposals if proposal.status == "pending_review")
    if not project_dir.exists():
        status = "missing_project"
    elif pending_count:
        status = "pending_review"
    else:
        status = "ok"
    return EigenquestionPreflight(
        project=project,
        project_dir=_rel(repo, project_dir),
        charter=_rel(repo, charter),
        charter_exists=charter_exists,
        charter_mtime=_iso_from_mtime(charter),
        proposal_count=len(proposals),
        pending_count=pending_count,
        status=status,
        proposals=proposals,
        review_command=f"ztare eigenquestion validate --project {project}",
        strict=strict,
    )


def render_text(result: EigenquestionPreflight) -> str:
    lines = [
        f"eigenquestion_preflight_status={result.status}",
        f"project={result.project}",
        f"charter={result.charter}",
        f"pending_newer_than_charter={result.pending_count}",
        f"proposal_count={result.proposal_count}",
    ]
    if result.pending_count:
        lines.extend([
            "WARNING: advisory eigenquestion proposal(s) are newer than the charter.",
            "Review before relying on the charter as the current project question.",
            f"review_command={result.review_command}",
            "rule=merge, reject, or supersede manually; never auto-rewrite project_charter.md",
        ])
        for proposal in result.proposals[:5]:
            if proposal.status == "pending_review":
                lines.append(f"pending={proposal.path} mtime={proposal.mtime}")
    elif result.status == "missing_project":
        lines.append(f"ERROR: project dir not found at {result.project_dir}")
    else:
        lines.append("ok: no advisory eigenquestion proposal is newer than the charter")
    if result.strict:
        lines.append("mode=strict")
    else:
        lines.append("mode=warn")
    return "\n".join(lines)


def _payload(result: EigenquestionPreflight) -> dict[str, Any]:
    return asdict(result) | {
        "ok": result.ok,
        "proposals": [asdict(proposal) for proposal in result.proposals],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Warn or fail when advisory eigenquestion proposals are newer than project_charter.md."
    )
    parser.add_argument("project")
    parser.add_argument("--strict", action="store_true", help="exit 1 on pending proposals")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)

    result = inspect_eigenquestion_review(args.project, strict=args.strict)
    if args.json:
        print(json.dumps(_payload(result), indent=2, sort_keys=True))
    else:
        print(render_text(result))
    if result.status == "missing_project":
        return 2
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
