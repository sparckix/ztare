"""Dynamic-rubric path + committee-digest helpers (Phase 4g, 2026-05-06 PM).

Two small helpers extracted from autoresearch_loop:

  - ``dynamic_rubric_path(project, rubrics_dir)`` — return the
    canonical path to the project's dynamic rubric file
  - ``load_current_committee_digest(project, rubrics_dir)`` — read
    the committee_digest from the rubric's instantiation_record;
    returns "" on missing file / malformed json

Both take ``rubrics_dir`` as an explicit argument rather than reading
the module-level ``RUBRICS_DIR`` global. The autoresearch_loop side
keeps thin wrappers that fill in the global so call sites are
unchanged.

Behaviour preserved verbatim from the prior inline implementation
(autoresearch_loop.py 2026-05-05 git history).
"""
from __future__ import annotations

import json
from pathlib import Path


def dynamic_rubric_path(project: str, rubrics_dir: Path) -> Path:
    """Canonical path to ``rubrics/dynamic_<project>.json``."""
    return Path(rubrics_dir) / f"dynamic_{project}.json"


def load_current_committee_digest(project: str, rubrics_dir: Path) -> str:
    """Read the committee_digest field from the dynamic rubric's
    metadata.instantiation_record.

    Returns "" on:
      - missing dynamic rubric file
      - malformed json
      - missing metadata / instantiation_record / committee_digest
      - non-string committee_digest value
    """
    rubric_path = dynamic_rubric_path(project, rubrics_dir)
    if not rubric_path.exists():
        return ""
    try:
        payload = json.loads(rubric_path.read_text())
    except Exception:
        return ""
    metadata = payload.get("metadata", {})
    instantiation_record = metadata.get("instantiation_record", {})
    digest = instantiation_record.get("committee_digest", "")
    return digest if isinstance(digest, str) else ""
