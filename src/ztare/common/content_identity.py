"""Canonical content identities shared by common and LeanMill protocols.

The repository historically used the same JSON/SHA-256 convention in several
subsystems.  This module owns that convention so lower-level certificate
compilers do not need to import a LeanMill theory representation merely to
name immutable content.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> str:
    """Return the repository's deterministic JSON representation."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def content_sha256(value: Any) -> str:
    """Return a bare lowercase SHA-256 digest of canonical JSON content."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def require_sha256_digest(value: Any, *, context: str) -> str:
    """Validate and return one bare lowercase SHA-256 digest."""

    digest = str(value or "")
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError(f"{context} must be a lowercase SHA-256 digest")
    return digest


__all__ = ["canonical_json", "content_sha256", "require_sha256_digest"]

