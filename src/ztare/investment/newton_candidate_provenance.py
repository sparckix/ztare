"""Classify a scored Newton candidate from content-addressed run artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any


_ITERATION = re.compile(r"^iter_(\d+)_.*\.py$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_newton_candidate_provenance(
    project_root: str | Path, candidate_path: str | Path,
) -> dict[str, Any]:
    """Resolve seed/subscription identity without trusting filenames alone."""

    root = Path(project_root).resolve()
    candidate = Path(candidate_path).resolve()
    candidate_sha = _sha256(candidate)
    workspace = root / "workspace"
    submissions = tuple(sorted((workspace / "submissions").glob("*.py")))
    matches = tuple(path for path in submissions if _sha256(path) == candidate_sha)
    telemetry_path = workspace / "iteration_telemetry.jsonl"
    telemetry = tuple(
        json.loads(line) for line in telemetry_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ) if telemetry_path.is_file() else ()
    iteration_rows = tuple(row for row in telemetry if row.get("record_type") == "iteration")

    body: dict[str, Any] = {
        "schema": "jaggedthoughts-newton-candidate-provenance-v1",
        "candidate_sha256": candidate_sha,
    }
    if len(matches) == 1:
        match = matches[0]
        parsed = _ITERATION.match(match.name)
        iteration = int(parsed.group(1)) if parsed else None
        row = next(
            (item for item in iteration_rows if item.get("iteration_index") == iteration),
            {},
        )
        return {
            **body,
            "status": "resolved",
            "origin": "subscription_newton_submission",
            "submission_path": match.relative_to(root).as_posix(),
            "iteration_index": iteration,
            "run_id": row.get("run_id"),
            "mutator_model": row.get("mutator_model_id"),
            "effective_mutator_models": row.get("mutator_effective_model_ids") or [],
        }
    if iteration_rows or submissions:
        return {
            **body,
            "status": "unresolved",
            "origin": "post_subscription_unattributed_candidate",
            "subscription_run_ids": sorted({row.get("run_id") for row in iteration_rows}),
            "submission_count": len(submissions),
            "matching_submission_count": len(matches),
        }
    return {
        **body,
        "status": "resolved",
        "origin": "declared_project_seed",
        "basis": "no_subscription_iteration_or_submission_artifact",
    }


__all__ = ["resolve_newton_candidate_provenance"]
