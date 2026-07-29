"""Shared identity checks for LeanMill protocol records."""
from __future__ import annotations

from typing import Any, Callable, Mapping

from ztare.leanmill.theory_ir import content_hash


def require_exact_fields(
    value: Mapping[str, Any],
    required: set[str],
    *,
    context: str,
) -> None:
    """Require a mapping to carry exactly the fields owned by its schema."""

    missing = required - set(value)
    unknown = set(value) - required
    if missing or unknown:
        raise ValueError(
            f"{context} field mismatch: missing={sorted(missing)}, "
            f"unknown={sorted(unknown)}"
        )


def require_sha256_digest(value: Any, *, context: str) -> str:
    """Return one bare lowercase SHA-256 digest or reject it."""

    digest = str(value or "")
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError(f"{context} digest is malformed")
    return digest


def validate_content_bound_row(
    value: Mapping[str, Any],
    *,
    schema: str,
    digest_field: str,
    required: set[str],
    context: str,
    copy_json: Callable[..., Any],
) -> dict[str, Any]:
    """Replay the schema, field-set, and content digest of one protocol row."""

    row = copy_json(value, context=context)
    if not isinstance(row, dict) or set(row) != required | {digest_field}:
        raise ValueError(f"{context} fields changed identity")
    core = {key: item for key, item in row.items() if key != digest_field}
    if row.get("schema") != schema or row.get(digest_field) != content_hash(core):
        raise ValueError(f"{context} digest mismatch")
    return row


__all__ = [
    "require_exact_fields",
    "require_sha256_digest",
    "validate_content_bound_row",
]
