"""Module-load-time startup recovery hooks (Phase 4g, 2026-05-06 PM).

Three bootstrap helpers extracted from autoresearch_loop. Each runs
ONCE at module load and was previously deleted from the namespace
after use. Moving them out of the engine entry point makes them
testable in isolation + frees ~150 lines from the helper section.

  - ``load_v4_stage_index(project_name)`` — read
    ``meta_runner_state.json`` for v4-family projects; returns the
    current stage index or None
  - ``axiom_restore_from_bak(axiom_path)`` — defense-in-depth: when
    the live ``verified_axioms.json`` is empty/missing AND the
    ``.bak`` is populated, restore from .bak. Catches the failure
    mode where a hard crash leaves the live file gone but .bak intact.
  - ``baseline_restore_and_champion_archive(project_dir)`` —
    opt-in via ``test_model_baseline.py``. Copies baseline →
    ``test_model.py`` (clearing prior-iter contamination) and
    archives prior champion files to a timestamped dir, so a new
    run starts with a clean champion slate.

All three take their inputs as explicit args. Behaviour preserved
verbatim from the prior inline implementation
(autoresearch_loop.py 2026-05-05 git history).
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

# Imported once here so the v4 stage check is self-contained.
# `is_v4_family_project` is a substrate-naming convention helper
# the loop already uses elsewhere.
from ztare.validator.utilities.v4_family import is_v4_family_project


def load_v4_stage_index(project_name: str) -> int | None:
    """Return the current_stage of a v4-family project's meta_runner state.

    Returns None for non-v4 projects, missing state files, or malformed
    json. Used at startup to resume a v4 multi-stage run.
    """
    if not is_v4_family_project(project_name):
        return None
    state_path = Path("projects") / project_name / "meta_runner_state.json"
    if not state_path.exists():
        return None
    try:
        return json.loads(state_path.read_text()).get("current_stage")
    except Exception:  # noqa: BLE001 — best-effort read
        return None


def axiom_restore_from_bak(axiom_path: str | Path) -> None:
    """Restore ``axiom_path`` from ``{axiom_path}.bak`` when the live
    file is empty/missing AND the .bak is populated.

    This is defense-in-depth for the failure mode where a hard crash
    leaves the live ``verified_axioms.json`` gone but the ``.bak``
    populated (the merge-after-emergency-pivot dance is interrupted
    mid-write). T14b + T17 catch mid-iter wipes; this hook covers
    the post-crash restart case.

    No-op when:
      - .bak doesn't exist
      - live file exists AND has populated axioms (dict.axioms or
        non-empty list)
      - .bak parses but has no axioms / is empty list
    """
    axiom_path = str(axiom_path)
    bak = f"{axiom_path}.bak"
    if not os.path.exists(bak):
        return

    # Determine if live file is "empty" (missing, empty list, empty
    # dict-axioms). Corrupt → treat as empty.
    live_empty = True
    if os.path.exists(axiom_path):
        try:
            with open(axiom_path, "r") as fh:
                live = json.load(fh)
            if isinstance(live, dict) and live.get("axioms"):
                live_empty = False
            elif isinstance(live, list) and live:
                live_empty = False
        except Exception:  # noqa: BLE001
            live_empty = True
    if not live_empty:
        return

    try:
        with open(bak, "r") as fh:
            bak_data = json.load(fh)
    except Exception:  # noqa: BLE001
        return

    bak_populated = (
        (isinstance(bak_data, dict) and bool(bak_data.get("axioms")))
        or (isinstance(bak_data, list) and bool(bak_data))
    )
    if not bak_populated:
        return

    try:
        shutil.copy(bak, axiom_path)
        n_axioms = len(
            bak_data.get("axioms") if isinstance(bak_data, dict) else bak_data
        )
        print(
            f"🛡️  startup axiom restore: {axiom_path} was empty; "
            f"restored from {bak} ({n_axioms} axiom(s))."
        )
    except Exception as exc:  # noqa: BLE001
        print(f"🛡️  startup axiom restore failed: {exc}")


def baseline_restore_and_champion_archive(project_dir: str | Path) -> None:
    """Mechanize the manual reset dance: when the substrate has an
    immutable ``test_model_baseline.py`` declared, copy it over
    ``test_model.py`` AND archive any prior champion artifacts to a
    timestamped dir.

    Closes the iter-0-bypass-cage gap: the previous run's iter-N
    submission overwrites ``test_model.py`` and contaminates the
    next run's iter-0 baseline (yielding score=100 from a form the
    cage would have capped at 50). Auto-restoring the baseline at
    startup eliminates that contamination class.

    Opt-in via ``test_model_baseline.py``. When absent, both hooks
    no-op (legacy substrate behavior preserved).
    """
    project_dir = str(project_dir)
    baseline_path = f"{project_dir}/test_model_baseline.py"
    test_model_path = f"{project_dir}/test_model.py"

    if not os.path.exists(baseline_path):
        return  # opt-in: no baseline declared → legacy behavior

    # (a) baseline auto-restore
    try:
        shutil.copy(baseline_path, test_model_path)
        print(
            "🛡️  startup baseline auto-restore: copied "
            "test_model_baseline.py -> test_model.py "
            "(prior-iter contamination cleared)"
        )
    except Exception as exc:  # noqa: BLE001
        print(f"🛡️  startup baseline auto-restore failed: {exc}")
        return  # if we can't restore baseline, skip archive too

    # (b) champion archive — only if any champion file exists
    archive_targets = [
        (f"{project_dir}/champion_eval_results.json", "champion_eval_results.json"),
        (f"{project_dir}/champion_probability_dag.json", "champion_probability_dag.json"),
        (
            f"{project_dir}/workspace/champion_evidence_gaps.json",
            "workspace_champion_evidence_gaps.json",
        ),
    ]
    extant = [(src, name) for (src, name) in archive_targets if os.path.exists(src)]
    if not extant:
        return  # no prior champion → nothing to archive

    archive_dir = f"{project_dir}/_run_archive_{int(time.time())}"
    try:
        os.makedirs(archive_dir, exist_ok=True)
        for src, name in extant:
            shutil.move(src, f"{archive_dir}/{name}")
        print(
            f"🛡️  champion archive: moved "
            f"{len(extant)} prior-champion file(s) -> {archive_dir}"
        )
    except Exception as exc:  # noqa: BLE001
        print(f"🛡️  champion archive failed: {exc}")
