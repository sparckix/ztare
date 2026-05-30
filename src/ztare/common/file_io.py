"""Common file IO primitives — extracted from autoresearch_loop (Phase 4g, 2026-05-06).

Five small helpers used >50 times across the engine entry point:

  - ``read_file(filepath)`` / ``write_file(filepath, content)``
    plain text read/write, no encoding gymnastics
  - ``read_json(filepath) -> dict | None``
    best-effort json read; returns None on missing file or parse error
    (callers depend on this — do NOT raise)
  - ``write_json(filepath, payload)``
    json write with parent-dir creation, indented + utf-8
  - ``append_jsonl(filepath, payload)``
    append one ascii-safe json line to a jsonl file with parent-dir
    creation. ``ensure_ascii=True`` is intentional — telemetry files
    are read by greppable tools, and Unicode in payloads has caused
    workspace-side decoding issues historically.

These were defined inline at autoresearch_loop.py:534-565. Moving
them out of the engine entry point makes them reusable from sibling
orchestrator modules (the previous duplication: a private
``_append_json_dict`` in ``orchestrator/iteration_telemetry.py``
reimplements append_jsonl because importing back from
autoresearch_loop would create a circular dependency).

Behaviour preserved verbatim from the prior inline implementation
(autoresearch_loop.py 2026-05-05 git history). Signatures unchanged
so the existing 51 call sites remain valid through a re-aliased
import.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_file(filepath: str | Path) -> str:
    """Read a text file in text mode, default encoding."""
    with open(filepath, "r") as f:
        return f.read()


def write_file(filepath: str | Path, content: str) -> None:
    """Write text content to ``filepath``, default encoding.

    Note: this does NOT create parent directories. The original
    autoresearch_loop helper did not, and several call sites depend
    on the missing-parent error surfacing as a real exception
    (rather than silently succeeding via mkdir). Don't change this
    without auditing the call sites.
    """
    with open(filepath, "w") as f:
        f.write(content)


def read_json(filepath: str | Path) -> dict | None:
    """Read JSON from ``filepath``, returning None on missing file or parse error.

    Callers depend on the swallow-and-return-None contract — do NOT
    raise. If a malformed json is observed downstream, the place to
    surface it is the consumer (which has context to produce a
    useful error), not the read primitive (which would crash the
    iter loop on a transient FS state).
    """
    path = Path(filepath)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:  # noqa: BLE001 — best-effort read by design
        return None


def write_json(filepath: str | Path, payload: dict) -> None:
    """Write JSON to ``filepath`` with indent=2, parent-dir auto-created."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_jsonl(filepath: str | Path, payload: dict) -> None:
    """Append one JSON line to ``filepath`` (jsonl), parent-dir auto-created.

    ``ensure_ascii=True`` is intentional — telemetry files are read
    by greppable tools, and Unicode in payloads has caused
    workspace-side decoding issues historically.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
