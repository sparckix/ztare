# SPDX-License-Identifier: MIT
"""Authorization hook: enforce role write-scope structurally, not advisorily.

Loads the active role's authorized_paths / forbidden_paths (from the
org/roles/ YAML) and checks any path against them. Intended to be called
BEFORE a write, so writes outside scope fail loud rather than produce
silent mandate violations.

Read access is permitted by default unless a path is in forbidden_paths.
Write access requires the path to be inside at least one authorized_paths
prefix AND NOT inside any forbidden_paths prefix.

Hole 5 fix: reviewer role has `authorized_paths: []` + `forbidden_paths:
["*"]` — which (before this module) meant "can't read anything." We fix
that semantics: `forbidden_paths` applies to WRITES, not reads, so a
reviewer can READ the whole repo but WRITE to none of it, which is
the correct semantics for a read-only reviewer.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from src.ztare.common.paths import REPO_ROOT
from src.ztare.roles.loader import Role

log = logging.getLogger(__name__)


def _normalize(path: Path | str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    else:
        p = p.resolve()
    return p


def _path_matches(path: Path, pattern: str) -> bool:
    """Match path against an authorized/forbidden pattern.

    Supported: literal prefix match + "*" wildcard for whole-repo.
    Patterns are repo-relative except when they start with "~".
    """
    pattern = pattern.strip()
    if pattern == "*":
        return True
    if pattern.startswith("~"):
        pat = Path(pattern).expanduser().resolve()
        try:
            path.relative_to(pat)
            return True
        except ValueError:
            return False
    # Repo-relative prefix
    pat = (REPO_ROOT / pattern.rstrip("/")).resolve()
    try:
        path.relative_to(pat)
        return True
    except ValueError:
        return False


def check_write_authorized(path: Path | str, role: Role) -> tuple[bool, str]:
    """Return (allowed, reason) for a write at `path` by `role`.

    allowed=True iff path is inside at least one authorized_paths AND
    not inside any forbidden_paths. reason is empty on allow; names the
    matching rule on deny.
    """
    p = _normalize(path)

    # Check forbidden_paths first (writes only — see module doc)
    for pattern in role.forbidden_paths:
        if _path_matches(p, pattern):
            return False, f"forbidden_paths rule matched: {pattern}"

    # Empty authorized_paths = no write access at all (e.g. reviewer)
    if not role.authorized_paths:
        return False, "role has no authorized write paths (read-only)"

    # Star shorthand — role can write anywhere not in forbidden
    for pattern in role.authorized_paths:
        if pattern.strip() == "*":
            return True, ""

    for pattern in role.authorized_paths:
        if _path_matches(p, pattern):
            return True, ""

    return False, (
        f"path {p.relative_to(REPO_ROOT) if p.is_relative_to(REPO_ROOT) else p} "
        f"not in role {role.role_id}'s authorized_paths"
    )


def check_read_authorized(path: Path | str, role: Role) -> tuple[bool, str]:
    """Return (allowed, reason) for a read at `path` by `role`.

    Read access is permitted EXCEPT for explicit mandate/session
    sequestration (other roles' mandates, other roles' session artifacts).
    We implement this via a small read-specific forbidden list carried on
    the role (future: add role.forbidden_read_paths). For now, read is
    permitted unless the role itself is sequestered from that path.
    """
    p = _normalize(path)

    # Explicit sequestration rules that apply to reads:
    # Hole 5 fix semantics — forbidden_paths applies to WRITES, with two
    # exceptions that the mandate can mark as read-sequestered:
    for pattern in role.forbidden_paths:
        pat = pattern.strip()
        # Sensitive personal-context directories that should be read-
        # sequestered for roles that explicitly list them
        if pat.startswith("org/mandates"):
            if _path_matches(p, pat):
                return False, f"forbidden_paths sequesters mandate: {pat}"
        if pat.startswith("org/sessions"):
            if _path_matches(p, pat):
                return False, f"forbidden_paths sequesters sessions: {pat}"
        if pat.startswith(".ip_protected"):
            if _path_matches(p, pat):
                return False, f"forbidden_paths sequesters IP: {pat}"

    return True, ""


def enforce_write(path: Path | str, role: Role) -> None:
    """Raise PermissionError if `role` is not authorized to write `path`.

    Intended to be called before any write. Callers that can't use this
    (e.g. direct shell invocations) should document the gap.
    """
    allowed, reason = check_write_authorized(path, role)
    if not allowed:
        raise PermissionError(
            f"role {role.role_id} blocked from writing {path}: {reason}"
        )


def enforce_read(path: Path | str, role: Role) -> None:
    """Raise PermissionError if `role` is not authorized to read `path`."""
    allowed, reason = check_read_authorized(path, role)
    if not allowed:
        raise PermissionError(
            f"role {role.role_id} blocked from reading {path}: {reason}"
        )
