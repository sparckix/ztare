"""Parse role-mandate frontmatter (GP-128 mandate × GP-129 orientation).

Mandate files are markdown with a leading YAML frontmatter block:

    ---
    mandate_version: 1.1
    role_id: manager
    orientation: mixed
    ...
    ---
    # Title
    (prose follows)

This module extracts the frontmatter. If a mandate has no frontmatter,
we log a warning (the mandate is still usable; the warning flags
drift from the newer schema).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

log = logging.getLogger(__name__)

VALID_ORIENTATIONS = {"intent", "procedure", "mixed"}


@dataclass(frozen=True)
class MandateFrontmatter:
    path: Path
    mandate_version: Optional[str]
    role_id: Optional[str]
    orientation: Optional[str]            # intent | procedure | mixed
    opened_date: Optional[str]
    last_revised_date: Optional[str]
    intent_procedure_ratio_target: Optional[str]
    signs_gates: tuple[str, ...]
    raw: dict = field(default_factory=dict)


def parse_mandate(path: Path) -> MandateFrontmatter:
    text = path.read_text(encoding="utf-8")
    data: dict = {}
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            block = text[4:end]
            try:
                parsed = yaml.safe_load(block) or {}
                if isinstance(parsed, dict):
                    data = parsed
            except yaml.YAMLError as exc:
                log.warning("mandate %s has malformed frontmatter: %s", path, exc)
        else:
            log.warning("mandate %s starts with --- but has no closing ---", path)
    else:
        log.warning(
            "mandate %s has no YAML frontmatter — "
            "consider adding mandate_version + orientation fields",
            path,
        )

    orientation = data.get("orientation")
    if orientation is not None and orientation not in VALID_ORIENTATIONS:
        log.warning(
            "mandate %s orientation=%r not in %s",
            path, orientation, sorted(VALID_ORIENTATIONS),
        )

    signs_raw: Any = data.get("signs_gates", []) or []
    if isinstance(signs_raw, str):
        signs_raw = [signs_raw]

    return MandateFrontmatter(
        path=path,
        mandate_version=str(data["mandate_version"]) if "mandate_version" in data else None,
        role_id=data.get("role_id"),
        orientation=orientation,
        opened_date=data.get("opened_date"),
        last_revised_date=data.get("last_revised_date"),
        intent_procedure_ratio_target=data.get("intent_procedure_ratio_target"),
        signs_gates=tuple(signs_raw),
        raw=data,
    )
