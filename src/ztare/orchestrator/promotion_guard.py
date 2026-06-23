"""Promotion readiness guard for discriminator-backed findings.

This is a small deterministic reader for GP-190 queue artifacts. It does not
decide whether a scientific claim is true. It only blocks a common process bug:
promoting an F-row/INS-row from scratchpad, weak, or still-open discriminators.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from ztare.common.paths import PROJECTS_DIR
from ztare.orchestrator.discriminator_queue import QUEUE_FILENAME
from ztare.orchestrator.operator_replay_audit import REPLAY_FILENAME


CLOSED_PASS_STATUSES = {
    "closed_passed",
    "passed",
    "survived",
    "closed_survived",
    "closed_success",
}

OPEN_STATUSES = {
    "proposed",
    "queued",
    "running",
    "open",
    "in_progress",
}


def project_dir_from_slug(project: str | Path) -> Path:
    path = Path(project)
    if path.exists() or "/" in str(project):
        return path
    return PROJECTS_DIR / str(project)


@dataclass(frozen=True)
class PromotionGuardVerdict:
    project: str
    claim_kind: str
    promotion_ready: bool
    blocking_reason: str
    eligible_closed_count: int
    eligible_open_count: int
    eligible_closed_with_evidence_count: int
    weak_or_scratchpad_count: int
    records_scanned: int
    queue_paths: list[str]

    def to_record(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "project": self.project,
            "claim_kind": self.claim_kind,
            "promotion_ready": self.promotion_ready,
            "blocking_reason": self.blocking_reason,
            "eligible_closed_count": self.eligible_closed_count,
            "eligible_open_count": self.eligible_open_count,
            "eligible_closed_with_evidence_count": self.eligible_closed_with_evidence_count,
            "weak_or_scratchpad_count": self.weak_or_scratchpad_count,
            "records_scanned": self.records_scanned,
            "queue_paths": self.queue_paths,
        }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def load_discriminator_records(project_dir: Path) -> tuple[list[dict[str, Any]], list[Path]]:
    paths = [
        project_dir / "workspace" / QUEUE_FILENAME,
        project_dir / "workspace" / REPLAY_FILENAME,
    ]
    records: list[dict[str, Any]] = []
    existing: list[Path] = []
    for path in paths:
        rows = _read_jsonl(path)
        if rows:
            existing.append(path)
            records.extend(rows)
    return records, existing


def _can_support_promotion(row: dict[str, Any]) -> bool:
    return (
        bool(row.get("promotion_blocking", True))
        and row.get("license_stage") == "commit"
        and int(row.get("severity_level") or 0) >= 4
        and bool(row.get("can_support_promotion", True))
    )


def _status(row: dict[str, Any]) -> str:
    return str(row.get("status") or "proposed").strip().lower()


def _has_evidence(row: dict[str, Any]) -> bool:
    metadata = row.get("metadata")
    if isinstance(metadata, dict) and metadata.get("status_evidence_artifacts"):
        return True
    return bool(row.get("evidence_artifacts") or row.get("status_evidence_artifacts"))


def assess_promotion_readiness(
    project_dir: Path,
    *,
    claim_kind: str = "F",
    records: Iterable[dict[str, Any]] | None = None,
) -> PromotionGuardVerdict:
    loaded_paths: list[Path] = []
    if records is None:
        loaded_records, loaded_paths = load_discriminator_records(project_dir)
    else:
        loaded_records = list(records)
    project_name = project_dir.name
    relevant_records = [
        r for r in loaded_records
        if str(r.get("project") or project_name) in {"", project_name}
    ]
    eligible = [r for r in relevant_records if _can_support_promotion(r)]
    eligible_closed = [r for r in eligible if _status(r) in CLOSED_PASS_STATUSES]
    eligible_closed_with_evidence = [r for r in eligible_closed if _has_evidence(r)]
    eligible_open = [r for r in eligible if _status(r) in OPEN_STATUSES]
    weak = [r for r in relevant_records if not _can_support_promotion(r)]

    ready = bool(eligible_closed_with_evidence) and not eligible_open
    if eligible_open:
        reason = "eligible L4/L5 commit-stage discriminator exists but is not closed/passed"
    elif eligible_closed and not eligible_closed_with_evidence:
        reason = "eligible discriminator is closed/passed but lacks explicit evidence artifacts"
    elif ready:
        reason = ""
    elif weak:
        reason = "only weak, scratchpad, or non-promotion discriminator records exist"
    else:
        reason = "no discriminator queue records found"

    return PromotionGuardVerdict(
        project=project_dir.name,
        claim_kind=claim_kind,
        promotion_ready=ready,
        blocking_reason=reason,
        eligible_closed_count=len(eligible_closed),
        eligible_open_count=len(eligible_open),
        eligible_closed_with_evidence_count=len(eligible_closed_with_evidence),
        weak_or_scratchpad_count=len(weak),
        records_scanned=len(relevant_records),
        queue_paths=[str(p) for p in loaded_paths],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether a finding has promotion-grade discriminator support.")
    parser.add_argument("--project", required=True, help="Project slug or project directory.")
    parser.add_argument("--claim-kind", default="F", choices=["F", "INS"], help="Claim class being promoted.")
    parser.add_argument("--json-out", type=Path, default=None, help="Optional output path for the verdict JSON.")
    args = parser.parse_args()

    project_dir = project_dir_from_slug(args.project)
    verdict = assess_promotion_readiness(project_dir, claim_kind=args.claim_kind)
    record = verdict.to_record()
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0 if verdict.promotion_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
