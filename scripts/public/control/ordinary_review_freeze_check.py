#!/usr/bin/env python3
"""Validate a completed D_ordinary_review run before frozen-suite promotion."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE_RUN = REPO / "benchmarks/constraint_memory/runs/20260404_195100"
ORDINARY_REVIEW_CONDITION = "D_ordinary_review"


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise SystemExit(f"ordinary-review freeze check failed: missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"ordinary-review freeze check failed: {message}")


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = REPO / candidate
    return candidate


def _artifact_path(path_value: str | None, run_root: Path) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_absolute():
        path = run_root / path
    return path


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source_specimen_ids(source_run: Path) -> list[str]:
    results_path = source_run / "results.json" if source_run.is_dir() else source_run
    rows = _read_json(results_path)
    _require(isinstance(rows, list), f"source run results must be a list: {results_path}")
    ids = sorted({
        row.get("specimen_id")
        for row in rows
        if isinstance(row, dict) and "error" not in row and isinstance(row.get("specimen_id"), str)
    })
    _require(ids, f"source run has no specimen ids: {results_path}")
    return ids


def _artifact_exists(path_value: str | None, run_root: Path) -> bool:
    path = _artifact_path(path_value, run_root)
    if path is None:
        return False
    return path.exists()


def build_payload(run: str | Path, source_run: str | Path = DEFAULT_SOURCE_RUN) -> dict[str, Any]:
    run_root = _resolve(run)
    source_run_path = _resolve(source_run)
    manifest_path = run_root / "ordinary_review_freeze_manifest.json"
    summary_path = run_root / "metrics_summary.json"
    results_path = run_root / "results.json"

    manifest = _read_json(manifest_path)
    summary = _read_json(summary_path)
    results = _read_json(results_path)
    _require(isinstance(results, list), "ordinary-review results.json must be a list")
    source_ids = _source_specimen_ids(source_run_path)

    _require(manifest.get("arm_id") == ORDINARY_REVIEW_CONDITION, "manifest has wrong arm_id")
    _require(manifest.get("source_run_bound") is True, "manifest is not source-run-bound")
    _require(manifest.get("can_promote_to_frozen_suite") is True, "manifest is not promotion-ready")
    _require(not manifest.get("promotion_blockers"), f"manifest has promotion blockers: {manifest.get('promotion_blockers')}")
    _require(manifest.get("error_count") == 0, "manifest reports ordinary-review errors")

    selected_ids = sorted(manifest.get("selected_specimen_ids") or [])
    expected_ids = sorted(manifest.get("expected_source_specimen_ids") or [])
    _require(selected_ids == source_ids, "selected specimen ids do not match source run")
    _require(expected_ids == source_ids, "manifest expected source ids do not match source run")
    _require(manifest.get("selected_specimen_count") == len(source_ids), "selected specimen count mismatch")
    _require(manifest.get("expected_source_specimen_count") == len(source_ids), "expected specimen count mismatch")
    _require(not manifest.get("missing_source_specimen_ids"), "manifest reports missing source specimens")
    _require(not manifest.get("extra_specimen_ids"), "manifest reports extra specimens")

    condition_summary = (summary.get("conditions") or {}).get(ORDINARY_REVIEW_CONDITION)
    _require(isinstance(condition_summary, dict), "metrics_summary missing D_ordinary_review")
    _require(condition_summary.get("num_specimens") == len(source_ids), "summary specimen count mismatch")
    _require(condition_summary.get("error_count") == 0, "summary reports ordinary-review errors")

    ordinary_rows = [
        row for row in results
        if isinstance(row, dict) and row.get("condition") == ORDINARY_REVIEW_CONDITION
    ]
    _require(len(ordinary_rows) == len(source_ids), "results row count mismatch")
    _require(not [row for row in ordinary_rows if "error" in row], "results contain error rows")
    ordinary_by_id = {
        row["specimen_id"]: row
        for row in ordinary_rows
        if isinstance(row.get("specimen_id"), str)
    }

    row_manifests = manifest.get("rows")
    _require(isinstance(row_manifests, list), "manifest rows missing")
    _require(len(row_manifests) == len(source_ids), "manifest row count mismatch")
    missing_artifacts: list[str] = []
    missing_provenance: list[str] = []
    for row in row_manifests:
        specimen_id = row.get("specimen_id")
        result_row = ordinary_by_id.get(specimen_id)
        if result_row is None:
            missing_provenance.append(f"{specimen_id}: result row")
        if not row.get("prompt_sha256"):
            missing_provenance.append(f"{specimen_id}: prompt_sha256")
        if not row.get("model"):
            missing_provenance.append(f"{specimen_id}: model")
        if not row.get("reviewed_at"):
            missing_provenance.append(f"{specimen_id}: reviewed_at")
        if not row.get("provider_runtime"):
            missing_provenance.append(f"{specimen_id}: provider_runtime")
        if result_row is not None:
            if result_row.get("ordinary_review_reviewed_at") != row.get("reviewed_at"):
                missing_provenance.append(f"{specimen_id}: reviewed_at mismatch")
            if result_row.get("ordinary_review_model") != row.get("model"):
                missing_provenance.append(f"{specimen_id}: model mismatch")
            if result_row.get("ordinary_review_source") != row.get("source"):
                missing_provenance.append(f"{specimen_id}: source mismatch")
        prompt_path = _artifact_path(row.get("prompt_path"), run_root)
        if prompt_path is not None and prompt_path.exists():
            prompt_sha256 = _sha256_text(prompt_path.read_text(encoding="utf-8"))
            if prompt_sha256 != row.get("prompt_sha256"):
                missing_provenance.append(f"{specimen_id}: prompt_sha256 mismatch")
        for key in ("prompt_path", "raw_review_path", "eval_results_path"):
            if not _artifact_exists(row.get(key), run_root):
                missing_artifacts.append(f"{specimen_id}: {key}")
    _require(not missing_provenance, f"missing provenance: {missing_provenance}")
    _require(not missing_artifacts, f"missing row artifacts: {missing_artifacts}")

    return {
        "ok": True,
        "arm_id": ORDINARY_REVIEW_CONDITION,
        "run_root": str(run_root.relative_to(REPO) if run_root.is_relative_to(REPO) else run_root),
        "source_run": str(source_run_path.relative_to(REPO) if source_run_path.is_relative_to(REPO) else source_run_path),
        "specimen_count": len(source_ids),
        "specimen_ids": source_ids,
        "review_sources": manifest.get("review_sources") or [],
        "metrics": condition_summary,
        "promotion_manifest": str(manifest_path.relative_to(REPO) if manifest_path.is_relative_to(REPO) else manifest_path),
        "claim_boundary": "promotion-ready run only; frozen suite metadata still must be updated separately",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", help="Path to a completed benchmark run containing ordinary_review_freeze_manifest.json")
    parser.add_argument(
        "--source-run",
        default=str(DEFAULT_SOURCE_RUN.relative_to(REPO)),
        help="Frozen source run directory or results.json to compare specimen ids against.",
    )
    args = parser.parse_args()
    print(json.dumps(build_payload(args.run, args.source_run), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
