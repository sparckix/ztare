#!/usr/bin/env python3
"""Substrate reset for clean cross-family validation (Bug #45, 2026-04-25 night).

Per user observation: a "cross-family rerun" that inherits the existing
champion's test_model.py is methodologically void — the new mutator
family rubber-stamps the previous family's discovery rather than
independently exploring.

This script archives ALL champion-derived artifacts and restores the
substrate to its pre-mutator state, so a fresh `make experiment-loop`
under any mutator/judge pairing genuinely starts from scratch.

What gets ARCHIVED (moved to archive_<timestamp>/, not deleted):
  - test_model.py (current state, often contains champion form)
  - champion_eval_results.json + champion_probability_dag.json
  - latest_eval_results.json + latest_probability_dag.json
  - history/ (all per-iter snapshots)
  - workspace/ (per-iter telemetry, fit results)
  - debate_log_iter_*.md (judge debate transcripts)
  - verified_axioms.json + derived_constraints (if present)
  - _fit_stub.py (residual from sidecar guard)

What is PRESERVED:
  - features.py (substrate physics — never reset)
  - evidence.txt + evidence_holdout.txt (substrate data — never reset)
  - gate_harness.py (deterministic gates — never reset)
  - project_charter.md (substrate task — never reset)
  - rubric file (lives in rubrics/ — never touched)
  - raw/ (substrate-input CSVs the features.py reads — never reset)

After reset, test_model.py is restored to a minimal placeholder:
  PARAMETRIC_FORM = "0.0"; PARAMETER_NAMES = []; MODEL_PARAMS = {}
  def I_model(features, params=None): return float("nan")

This matches the canonical pre-mutator state — the mutator's first
iter will overwrite it, gate_harness will get NaN until then.

Usage:
    python scripts/reset_substrate_for_cross_family.py <project_slug> [<project_slug>...]
    python scripts/reset_substrate_for_cross_family.py --dry-run gp159_retrieval_trap
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
PROJECTS_DIR = REPO / "projects"

PLACEHOLDER_TEST_MODEL = '''"""Substrate placeholder — pre-mutator state.

Reset by scripts/reset_substrate_for_cross_family.py for clean cross-family
validation. Replaced on iter 1 by the mutator's submitted form.

Returns a finite constant so `make seal` smoke-tests pass pre-mutator.
NaN on every row would trigger the GP-156 silent-crash bypass and
surface as a harness defect, which is correct for in-flight runs but
wrong for the deliberate placeholder state.
"""
import math


PARAMETRIC_FORM = "0.5"
PARAMETER_NAMES = []
MODEL_PARAMS = {}


def I_model(features, params=None):
    return 0.5


def f(x):
    return 0.5


# Canonical aliases
model = I_model
'''

# Patterns to ARCHIVE (move into archive_<ts>/) — preserves audit trail
ARCHIVE_PATTERNS = [
    "champion_eval_results.json",
    "champion_probability_dag.json",
    "champion_evidence_gaps.json",
    "latest_eval_results.json",
    "latest_probability_dag.json",
    "latest_evidence_gaps.json",
    "verified_axioms.json",
    "derived_constraints.json",
    "_fit_stub.py",
    "current_iteration.md",
    # NOTE: thesis.md is NOT archived here — validate_rubric requires it at
    # launch time (rubric_authoring_map §2). After archiving the substantive
    # thesis content, we restore a placeholder thesis.md at the end.
    "last_prompt_debug.txt",
]

# Files COPIED to archive but NOT removed (kept in live dir for pre-flight)
COPY_BUT_PRESERVE = [
    "thesis.md",
]

# Directories that must EXIST after reset (recreated empty if archived)
REQUIRED_DIRS_AFTER_RESET = ["raw"]

PLACEHOLDER_THESIS = """# Initial thesis (substrate placeholder)

The mutator will replace this on iteration 1. The substrate is reset
to pre-mutator state; no champion form is inherited.
"""

# Glob patterns to ARCHIVE
ARCHIVE_GLOBS = [
    "debate_log_iter_*.md",
    "*.bak",
]

# Directories to ARCHIVE entirely (move whole dir into archive_<ts>/)
# NOTE: raw/ is INTENTIONALLY EXCLUDED — it holds substrate-input data
# (CSVs the substrate's features.py reads), in the same category as
# evidence.txt and gate_harness.py. Archiving it would break the next
# launch. If a substrate enrichment lands and you want a clean slate of
# raw/ too, do that manually.
ARCHIVE_DIRS = [
    "history",
    "workspace",
    "projects",  # nested projects/ dir from earlier sessions if present
]

# Files to NEVER touch
PRESERVE_FILES = {
    "features.py",
    "evidence.txt",
    "evidence_holdout.txt",
    "gate_harness.py",
    "project_charter.md",
    "EXPERIMENT.md",
    "_holdout_locked",  # directory
}


def reset_substrate(slug: str, dry_run: bool = False) -> bool:
    proj_dir = PROJECTS_DIR / slug
    if not proj_dir.exists():
        print(f"  ❌ project not found: {proj_dir}")
        return False

    archive_dir = proj_dir / f"archive_pre_xfamily_{int(time.time())}"
    print(f"  Archive target: {archive_dir.name}/")
    if not dry_run:
        archive_dir.mkdir(exist_ok=True)

    moved_files = 0
    moved_dirs = 0

    # ── Archive specific files ──
    for pat in ARCHIVE_PATTERNS:
        path = proj_dir / pat
        if path.exists() and path.is_file():
            target = archive_dir / pat
            print(f"    archive file:  {pat}")
            if not dry_run:
                shutil.move(str(path), str(target))
            moved_files += 1

    # ── Archive glob-matched files ──
    for glob in ARCHIVE_GLOBS:
        for path in proj_dir.glob(glob):
            if path.is_file():
                target = archive_dir / path.name
                print(f"    archive glob:  {path.name}")
                if not dry_run:
                    shutil.move(str(path), str(target))
                moved_files += 1

    # ── Archive whole directories ──
    for dirname in ARCHIVE_DIRS:
        path = proj_dir / dirname
        if path.exists() and path.is_dir() and dirname not in PRESERVE_FILES:
            target = archive_dir / dirname
            print(f"    archive dir:   {dirname}/  ({sum(1 for _ in path.rglob('*'))} entries)")
            if not dry_run:
                shutil.move(str(path), str(target))
            moved_dirs += 1

    # ── Replace test_model.py with placeholder ──
    tm_path = proj_dir / "test_model.py"
    if tm_path.exists():
        # First archive the current test_model.py
        archived_tm = archive_dir / "test_model.py.champion"
        print(f"    archive test_model.py (current = champion form) → test_model.py.champion")
        if not dry_run:
            shutil.copy2(str(tm_path), str(archived_tm))
    print(f"    write placeholder: test_model.py")
    if not dry_run:
        tm_path.write_text(PLACEHOLDER_TEST_MODEL, encoding="utf-8")

    # ── Copy-but-preserve files (thesis.md): archive content, write placeholder ──
    for fname in COPY_BUT_PRESERVE:
        src = proj_dir / fname
        if src.exists() and src.is_file():
            archived = archive_dir / fname
            print(f"    copy-archive: {fname} (live dir keeps placeholder)")
            if not dry_run:
                shutil.copy2(str(src), str(archived))
        # Write placeholder to live dir
        if fname == "thesis.md":
            print(f"    write placeholder: thesis.md (validate_rubric requirement)")
            if not dry_run:
                src.write_text(PLACEHOLDER_THESIS, encoding="utf-8")

    # ── Recreate required empty dirs (validate_rubric requirement) ──
    for dname in REQUIRED_DIRS_AFTER_RESET:
        d = proj_dir / dname
        if not d.exists():
            print(f"    recreate empty dir: {dname}/ (validate_rubric requirement)")
            if not dry_run:
                d.mkdir(exist_ok=True)

    print(f"  ✅ {slug}: {moved_files} files + {moved_dirs} dirs archived; test_model.py + thesis.md reset; raw/ ensured")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("slugs", nargs="+", help="project slugs to reset")
    parser.add_argument("--dry-run", action="store_true", help="show actions, don't execute")
    args = parser.parse_args()

    print("═" * 60)
    if args.dry_run:
        print("DRY RUN — no files will be moved")
    print(f"Substrate cross-family reset — {len(args.slugs)} project(s)")
    print("═" * 60)
    print()

    n_ok = 0
    for slug in args.slugs:
        print(f"── {slug} ──")
        if reset_substrate(slug, dry_run=args.dry_run):
            n_ok += 1
        print()

    print("═" * 60)
    print(f"Summary: {n_ok}/{len(args.slugs)} substrates reset")
    if not args.dry_run and n_ok > 0:
        print()
        print("Next step: run `make seal` then `make experiment-loop` with the")
        print("desired cross-family pairing. Each iter 1 will start from the")
        print("placeholder I_model — no champion inheritance.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
