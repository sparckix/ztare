"""Bounded, link-safe reads for immutable JSON authority slots."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
from typing import Any, Mapping


def read_bounded_json_authority_slot(
    path: Path,
    *,
    max_bytes: int,
    context: str,
) -> tuple[dict[str, Any], int] | None:
    """Read one JSON object through a fixed descriptor and byte ceiling."""

    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError(f"{context} byte ceiling is invalid")
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ValueError(f"{context} authority slot is unavailable") from exc
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"{context} authority slot is not a regular file")
        if metadata.st_size > max_bytes:
            raise ValueError(f"{context} authority slot exceeds its byte ceiling")
        chunks: list[bytes] = []
        observed = 0
        while True:
            chunk = os.read(fd, min(1_048_576, max_bytes + 1 - observed))
            if not chunk:
                break
            chunks.append(chunk)
            observed += len(chunk)
            if observed > max_bytes:
                raise ValueError(
                    f"{context} authority slot exceeds its byte ceiling"
                )
        try:
            raw = json.loads(b"".join(chunks))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{context} authority slot is malformed") from exc
        if not isinstance(raw, Mapping):
            raise ValueError(f"{context} authority slot is not an object")
        return dict(raw), observed
    finally:
        os.close(fd)
