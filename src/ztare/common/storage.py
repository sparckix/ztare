"""One storage-provider interface for every workbench/loop write, so the repo-backed default can be swapped
for an object store (S3) or a database WITHOUT touching call sites. A path handed to a provider is
PROVIDER-RELATIVE (never a raw host path); the file backend resolves it under a root and refuses to escape
that root — the same guard that is the security boundary.

Consolidates two byte-identical copies that grew independently — the workbench-projects store
(`FileWorkbenchStorage`) and LeanMill's `ActionStorage`/`FileActionStorage`. Consumers: the workbench server
(`WORKBENCH_STORE`), LeanMill actions, and — incrementally — the autoresearch loop's telemetry/history/eval
writes. Zero-dependency, pure stdlib.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

STORAGE_SCHEMA = "ztare-storage-provider-v1"


@runtime_checkable
class StorageProvider(Protocol):
    """The read/write surface every backend implements. `resolve` makes a provider-relative path concrete;
    `rel` is its inverse. A non-file backend (S3/DB) implements the read/write/append methods against its
    store; `resolve` may return a synthetic Path it interprets. `backend` names the implementation."""

    backend: str

    def metadata(self) -> dict[str, Any]: ...
    def resolve(self, path: Path | str) -> Path: ...
    def rel(self, path: Path | str) -> str: ...
    def exists(self, path: Path | str) -> bool: ...
    def is_file(self, path: Path | str) -> bool: ...
    def ensure_dir(self, path: Path | str) -> None: ...
    def read_bytes(self, path: Path | str) -> bytes: ...
    def read_text(self, path: Path | str, *, errors: str | None = None) -> str: ...
    def write_bytes(self, path: Path | str, data: bytes) -> None: ...
    def write_text(self, path: Path | str, text: str) -> None: ...
    def append_text(self, path: Path | str, text: str) -> None: ...
    def append_jsonl(self, path: Path | str, row: dict[str, Any]) -> None: ...


class FileStorage:
    """Repo-rooted filesystem backend — the local default. A path resolves under `root` and may not escape it
    (the provider + security boundary). Swap for S3/DB by implementing StorageProvider; call sites don't change."""

    backend = "file"

    def __init__(self, root: "Path | str | Callable[[], Path | str]", *, schema: str = STORAGE_SCHEMA) -> None:
        # `root` may be a value OR a zero-arg callable resolved on each access — the latter keeps a dynamic
        # root (e.g. a monkeypatchable module REPO) working, which several tests + reconfigurable setups rely on.
        self._root = root
        self._schema = schema           # callers that shipped a schema string keep it (back-compat)

    @property
    def root(self) -> Path:
        raw = self._root() if callable(self._root) else self._root
        return Path(raw).resolve()

    def metadata(self) -> dict[str, Any]:
        return {
            "schema": self._schema,
            "backend": self.backend,
            "root": ".",
            "detachable": True,
            "write_mode": "local_filesystem",
            "future_backends": ["object_store", "database"],
            "secret_storage": "env_only",
        }

    def resolve(self, path: Path | str) -> Path:
        candidate = Path(path)
        resolved = candidate.resolve() if candidate.is_absolute() else (self.root / candidate).resolve()
        if resolved != self.root and self.root not in resolved.parents:
            raise ValueError("storage path escapes the storage root")
        return resolved

    def rel(self, path: Path | str) -> str:
        return self.resolve(path).relative_to(self.root).as_posix()

    def exists(self, path: Path | str) -> bool:
        return self.resolve(path).exists()

    def is_file(self, path: Path | str) -> bool:
        return self.resolve(path).is_file()

    def ensure_dir(self, path: Path | str) -> None:
        self.resolve(path).mkdir(parents=True, exist_ok=True)

    def read_bytes(self, path: Path | str) -> bytes:
        return self.resolve(path).read_bytes()

    def read_text(self, path: Path | str, *, errors: str | None = None) -> str:
        kwargs: dict[str, str] = {"encoding": "utf-8"}
        if errors is not None:
            kwargs["errors"] = errors
        return self.resolve(path).read_text(**kwargs)

    def write_bytes(self, path: Path | str, data: bytes) -> None:
        resolved = self.resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_bytes(data)

    def write_text(self, path: Path | str, text: str) -> None:
        resolved = self.resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(text, encoding="utf-8")

    def append_text(self, path: Path | str, text: str) -> None:
        """Low-level append — the caller owns serialization (so file_io keeps its exact JSONL formatting)."""
        resolved = self.resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        with resolved.open("a", encoding="utf-8") as handle:
            handle.write(text)

    def append_jsonl(self, path: Path | str, row: dict[str, Any]) -> None:
        self.append_text(path, json.dumps(row, sort_keys=True) + "\n")


def _selfcheck() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        s = FileStorage(d)
        assert isinstance(s, StorageProvider), "FileStorage must satisfy the StorageProvider Protocol"
        s.write_text("a/b.txt", "hello")
        assert s.read_text("a/b.txt") == "hello"
        assert s.exists("a/b.txt") and s.is_file("a/b.txt")
        assert s.rel(Path(d) / "a" / "b.txt") == "a/b.txt"        # rel is the inverse of resolve
        s.append_jsonl("log.jsonl", {"n": 1})
        s.append_jsonl("log.jsonl", {"n": 2})
        assert s.read_text("log.jsonl").count("\n") == 2
        s.write_bytes("raw.bin", b"\x00\x01")
        assert s.read_bytes("raw.bin") == b"\x00\x01"
        for escape in ("../evil", "/etc/passwd"):
            try:
                s.resolve(escape); raise AssertionError(f"escape not caught: {escape}")
            except ValueError:
                pass
    print("common.storage selfcheck: OK")


if __name__ == "__main__":
    _selfcheck()
