#!/usr/bin/env python3
"""GP-226 charter-patch pre-iter-1 confirmation hook.

Runs as a Makefile prerequisite of `make loop` (after `validate-rubric`,
after `_preflight_leak_audit`). Detects pending advisory-mode patches in
``projects/<slug>/workspace/charter_patches.jsonl`` and confirms them
per the rubric's ``charter_patches_preflight_mode`` setting:

  - "skip" (default): no-op.
  - "interactive": stdin prompt (falls back to skip in non-tty).
  - "auto_confirm": delegate to a cross-family reviewer LLM.

Usage:
    python scripts/public/control/preflight_charter_patches.py <project_slug> --rubric rubrics/<r>.json [--mutator-model <id>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.ztare.orchestrator.charter_critic import (  # noqa: E402
    confirm_pending_advisory_patches,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="GP-226 charter-patch pre-iter-1 preflight.")
    parser.add_argument("project", help="project slug (under projects/)")
    parser.add_argument("--rubric", required=True, help="path to rubric JSON")
    parser.add_argument("--mutator-model", default=None,
                        help="mutator model id (used by reviewer model resolution)")
    parser.add_argument("--run-id", default=None,
                        help="run id (used for reviewer telemetry log)")
    args = parser.parse_args()

    project_dir = REPO_ROOT / "projects" / args.project
    rubric_path = Path(args.rubric)
    if not rubric_path.is_absolute():
        rubric_path = REPO_ROOT / rubric_path
    if not rubric_path.exists() or not project_dir.exists():
        return 0  # fail-graceful

    try:
        rubric_data = json.loads(rubric_path.read_text(encoding="utf-8"))
    except Exception:
        return 0

    if not bool(rubric_data.get("enable_charter_critic", False)):
        return 0  # critic not enabled — no preflight needed
    mode = str(rubric_data.get("charter_patches_preflight_mode") or "skip").lower().strip()
    if mode == "skip":
        return 0  # legacy / opt-out behavior

    summary = confirm_pending_advisory_patches(
        rubric_data=rubric_data,
        project_dir=project_dir,
        run_id=args.run_id or "preflight",
        mutator_model_id=args.mutator_model,
    )

    status = summary.get("status", "?")
    if status == "no_pending_patches":
        return 0  # silent success
    if status == "applied":
        applied = summary.get("applied", [])
        skipped = summary.get("skipped", [])
        source = summary.get("source", "?")
        print(f"📋 charter-patch preflight ({source}): "
              f"applied {len(applied)}, skipped {len(skipped)}")
        for a in applied:
            print(f"   ✓ [{a['index']}] {a['reframe_type']} → {a['target']}")
        for s in skipped:
            err = f" ({s.get('error')})" if s.get('error') else ""
            print(f"   - [{s['index']}] {s['reframe_type']}{err}")
        if summary.get("reviewer_model"):
            print(f"   reviewer: {summary['reviewer_model']}")
        return 0
    if status == "operator_skipped":
        print(f"📋 charter-patch preflight: operator skipped {summary.get('pending_count')} patch(es)")
        return 0
    if status == "skipped:non_tty":
        print(f"📋 charter-patch preflight: {summary.get('pending_count')} pending patch(es); "
              f"non-tty environment — run `make charter-commit` after the run if you want to apply")
        return 0
    if status == "skipped:reviewer_llm_failed":
        print(f"⚠️  charter-patch preflight: reviewer LLM failed; "
              f"{summary.get('pending_count')} patch(es) remain pending")
        return 0
    print(f"📋 charter-patch preflight: {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
