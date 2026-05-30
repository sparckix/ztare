#!/usr/bin/env python3
"""Freeze a substrate's current artifacts into a timestamped frozen_<ts>/ dir.

Inverse of scripts/public/reset_substrate_for_cross_family.py:
  reset = move artifacts INTO archive (clears live state for fresh run)
  freeze = COPY artifacts into frozen snapshot (preserves live state too)

Use freeze when you want to lock the current run's evidence (champion,
debate logs, history) but keep the substrate live so you can reference
or re-rerun without re-launching.

Usage:
    python scripts/public/freeze_substrate_artifacts.py <slug> [<slug> ...]
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PROJECTS_DIR = REPO / "projects"

# Files + dirs to snapshot (copy not move)
SNAPSHOT_FILES = [
    "test_model.py",
    "champion_eval_results.json",
    "champion_probability_dag.json",
    "champion_evidence_gaps.json",
    "latest_eval_results.json",
    "latest_probability_dag.json",
    "latest_evidence_gaps.json",
    "verified_axioms.json",
    "derived_constraints.json",
    "thesis.md",
    "current_iteration.md",
    "last_prompt_debug.txt",
]

SNAPSHOT_GLOBS = [
    "debate_log_iter_*.md",
]

SNAPSHOT_DIRS = [
    "history",
    "workspace",
]


def freeze(slug: str) -> bool:
    proj = PROJECTS_DIR / slug
    if not proj.exists():
        print(f"  ❌ project not found: {proj}")
        return False

    ts = int(time.time())
    frozen = proj / f"frozen_{ts}"
    frozen.mkdir(exist_ok=True)
    print(f"  freezing {slug} → {frozen.name}/")

    n_files = 0
    n_dirs = 0

    for fname in SNAPSHOT_FILES:
        src = proj / fname
        if src.exists() and src.is_file():
            shutil.copy2(str(src), str(frozen / fname))
            n_files += 1

    for glob in SNAPSHOT_GLOBS:
        for src in proj.glob(glob):
            if src.is_file():
                shutil.copy2(str(src), str(frozen / src.name))
                n_files += 1

    for dname in SNAPSHOT_DIRS:
        src = proj / dname
        if src.exists() and src.is_dir():
            tgt = frozen / dname
            if tgt.exists():
                shutil.rmtree(tgt)
            shutil.copytree(str(src), str(tgt))
            n_dirs += 1

    # Also snapshot the substrate inputs in case they change later
    for fname in ("evidence.txt", "evidence_holdout.txt", "features.py",
                  "gate_harness.py", "project_charter.md"):
        src = proj / fname
        if src.exists() and src.is_file():
            shutil.copy2(str(src), str(frozen / fname))
            n_files += 1

    # Write a freeze marker
    marker = frozen / "FREEZE_MARKER.txt"
    marker.write_text(
        f"Frozen at {time.ctime(ts)} (epoch {ts}).\n"
        f"Source: {proj}\n"
        f"Files snapshotted: {n_files}\n"
        f"Dirs snapshotted: {n_dirs}\n"
        f"\n"
        f"This snapshot preserves the run's artifacts as-of freeze time.\n"
        f"The live substrate continues to exist — to use this snapshot\n"
        f"as a baseline for comparison after a re-run, reference paths\n"
        f"under {frozen.name}/ (which will not be overwritten).\n",
        encoding="utf-8",
    )

    print(f"  ✅ {slug}: {n_files} files + {n_dirs} dirs frozen")
    return True


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    slugs = sys.argv[1:]
    print(f"Freezing {len(slugs)} substrate(s)")
    print()
    n_ok = sum(1 for s in slugs if freeze(s))
    print()
    print(f"Summary: {n_ok}/{len(slugs)} frozen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
