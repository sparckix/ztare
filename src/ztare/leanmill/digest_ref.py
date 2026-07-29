"""Canonical validation for SHA-256 references used by LeanMill receipts."""
from __future__ import annotations

from typing import Any


def is_sha256_digest(value: Any) -> bool:
    """Accept lowercase raw digests and the existing ``sha256:`` encoding."""

    if not isinstance(value, str):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(
        character in "0123456789abcdef" for character in digest
    )


__all__ = ["is_sha256_digest"]
