"""Project-state snapshot helpers (Phase 4g, 2026-05-06).

Three pure helpers extracted from autoresearch_loop:

  - ``capture_project_state(paths)`` — read each path's content into a
    snapshot dict; missing files map to None. Used at iter-start to
    capture rollback state.
  - ``restore_project_state(snapshot)`` — inverse: write each entry
    back, deleting files that were absent at capture time.
  - ``latest_debate_log_text(project_dir)`` — read the
    most-recently-modified ``debate_log_iter_*.md`` file in
    ``project_dir``. Returns "" if none exist.

These three are PURE — no apparatus state, no module globals — and
were defined inline at autoresearch_loop.py:844-865. The autoresearch_loop
side keeps `_project_state_paths` (which uses module-global path
constants like THESIS_PATH / WORKING_PATH / EVIDENCE_PATH / AXIOM_PATH)
inline; only the snapshot operators move out.

Behaviour preserved verbatim from the prior inline implementation.
"""
from __future__ import annotations

import os
from pathlib import Path

from src.ztare.common.file_io import read_file, write_file


def capture_project_state(paths: tuple[str, ...]) -> dict[str, str | None]:
    """Read each path's content into a snapshot. Missing files map to None.

    Used by autoresearch_loop at iter boundaries to capture rollback
    state before a candidate mutation. Pair with ``restore_project_state``
    on the failure path.
    """
    snapshot: dict[str, str | None] = {}
    for path in paths:
        snapshot[path] = read_file(path) if os.path.exists(path) else None
    return snapshot


def restore_project_state(snapshot: dict[str, str | None]) -> None:
    """Inverse of ``capture_project_state``. Writes each entry's
    content back to disk; if a path was None at capture time
    (file did not exist) and now exists, deletes it.
    """
    for path, content in snapshot.items():
        if content is None:
            if os.path.exists(path):
                os.remove(path)
            continue
        write_file(path, content)


def latest_debate_log_text(project_dir: str | Path) -> str:
    """Return the text of the most-recent ``debate_log_iter_*.md``
    in ``project_dir``. Returns "" if none exist.

    Sort order is by mtime (filesystem-attested), not lexicographic —
    avoids the failure mode where ``debate_log_iter_9.md`` sorts after
    ``debate_log_iter_10.md`` lexicographically.
    """
    project_path = Path(project_dir)
    candidates = sorted(
        project_path.glob("debate_log_iter_*.md"),
        key=lambda p: p.stat().st_mtime,
    )
    if not candidates:
        return ""
    return candidates[-1].read_text()


def project_state_paths(
    project_dir: str | Path,
    *,
    thesis_path: str | Path,
    working_path: str | Path,
    evidence_path: str | Path,
    axiom_path: str | Path,
) -> tuple[str, ...]:
    """The canonical project-state path tuple snapshot/restore consumes.

    Includes the always-snapshotted core files (thesis, working,
    evidence, axioms) plus two project-relative files (test_model.py
    and workspace/fit_result.json) that round out the iter rollback
    state.

    AXIOM_PATH was missing from this tuple before 2026-04-27 (hotfix);
    its absence meant ``capture_project_state`` snapshots never
    included verified_axioms.json, so subsequent ``restore_project_state``
    calls (on iter rollback / failed promotion) couldn't restore it,
    leaving the file at whatever the merge code wrote (often ``[]``).
    Including it here ensures operator-curated bridge axioms +
    successor_lock survive iter rollbacks.
    """
    project_dir = str(project_dir)
    return (
        str(thesis_path),
        str(working_path),
        f"{project_dir}/test_model.py",
        str(evidence_path),
        f"{project_dir}/workspace/fit_result.json",
        str(axiom_path),
    )
