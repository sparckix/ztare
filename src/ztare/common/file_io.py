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

# ---------------------------------------------------------------------------
# Storage provider hook (2026-07-01). These 5 primitives are the >50-call-site
# chokepoint for the loop's writes, so routing THEM through a StorageProvider makes
# the whole engine storage-agnostic (local FS today, S3/object-store tomorrow) via
# ONE switch — `configure_storage(provider)` at startup. Serialization stays here
# (exact JSONL/JSON formatting); the provider only does raw read/write/append.
#
# Default is None ⇒ every primitive keeps its ORIGINAL direct-filesystem behavior
# byte-for-byte, so the existing call sites are unchanged until a provider is set.
_provider: Any = None


def configure_storage(provider: Any) -> None:
    """Route these primitives through `provider` (a ztare.common.storage.StorageProvider). Pass None to
    restore direct-filesystem behavior. Set once at process startup; not thread-safe by design (one loop)."""
    global _provider
    _provider = provider


def active_storage() -> Any:
    return _provider


def read_file(filepath: str | Path) -> str:
    """Read a text file in text mode, default encoding."""
    if _provider is not None:
        return _provider.read_text(filepath)
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
    if _provider is not None:
        _provider.write_text(filepath, content)   # provider mode: parent auto-created (moot on S3)
        return
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
    if _provider is not None:
        try:
            if not _provider.exists(filepath):
                return None
            return json.loads(_provider.read_text(filepath))
        except Exception:  # noqa: BLE001 — best-effort read by design
            return None
    path = Path(filepath)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:  # noqa: BLE001 — best-effort read by design
        return None


def write_json(filepath: str | Path, payload: dict) -> None:
    """Write JSON to ``filepath`` with indent=2, parent-dir auto-created."""
    text = json.dumps(payload, indent=2)
    if _provider is not None:
        _provider.write_text(filepath, text)
        return
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def append_jsonl(filepath: str | Path, payload: dict) -> None:
    """Append one JSON line to ``filepath`` (jsonl), parent-dir auto-created.

    ``ensure_ascii=True`` is intentional — telemetry files are read
    by greppable tools, and Unicode in payloads has caused
    workspace-side decoding issues historically.
    """
    line = json.dumps(payload, ensure_ascii=True) + "\n"   # serialization owned here (not the provider)
    if _provider is not None:
        _provider.append_text(filepath, line)
        return
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def _selfcheck() -> None:
    import tempfile
    from ztare.common.storage import FileStorage
    payload = {"z": 1, "a": [1, 2], "unicode": "café"}
    # Default (no provider) vs provider-routed must produce BYTE-IDENTICAL files — the whole point.
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        configure_storage(None)                                   # direct-FS
        write_json(Path(d1) / "j.json", payload)
        append_jsonl(Path(d1) / "l.jsonl", payload); append_jsonl(Path(d1) / "l.jsonl", {"k": 2})
        write_file(Path(d1) / "t.txt", "hello")
        try:
            configure_storage(FileStorage(d2))                    # provider-routed
            write_json("j.json", payload)
            append_jsonl("l.jsonl", payload); append_jsonl("l.jsonl", {"k": 2})
            write_file("t.txt", "hello")
        finally:
            configure_storage(None)
        for name in ("j.json", "l.jsonl", "t.txt"):
            a = (Path(d1) / name).read_bytes()
            b = (Path(d2) / name).read_bytes()
            assert a == b, f"provider mode diverged from direct-FS for {name}:\n{a!r}\n{b!r}"
        assert read_json(Path(d1) / "j.json") == payload
        assert read_json(Path(d1) / "missing.json") is None       # swallow-and-return-None contract
    print("common.file_io selfcheck: OK (provider mode byte-identical to direct-FS)")


if __name__ == "__main__":
    _selfcheck()
