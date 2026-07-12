"""Canonical helpers for LeanMill workers and tools.

Replaces the ~98 near-duplicate ``_read_json`` helpers, ~252 ``_run``
subprocess wrappers, and ~77 ad-hoc SQLite open patterns scattered across
the operator scripts.

Design goals:

1. **Atomicity for JSON writes.** ``write_json_atomic`` writes to a
   sibling temp file in the same directory and ``os.replace``s it onto the
   target. On POSIX this is atomic on the same filesystem, which gives
   downstream readers an all-or-nothing guarantee.

2. **Lenient JSON reads.** ``read_json`` returns ``default`` on any of
   missing-file, JSON-decode-error, or non-dict-when-dict-was-expected.
   Callers that need to distinguish these conditions should read the
   file by hand; for the 90% case, the lenient default is what the
   existing scripts already do (via 47 copies of the same pattern).

3. **Subprocess discipline.** ``run`` always uses a list (never shell),
   always honours timeouts, and always returns a structured dict that
   includes the command (with the host's Python collapsed to
   ``"<python>"`` for log readability), the returncode, and the
   stdout/stderr tails. On timeout the returncode is set to 124
   (the POSIX convention) and ``timed_out: True`` is recorded.

4. **SQLite discipline.** ``sqlite_open`` always sets WAL mode and a
   5-second busy_timeout, both of which the queue and several other
   workers reach for independently today.

This module has no LeanMill-specific knowledge; it is pure
infrastructure. The boundary rule (kernel must not import scripts) is
respected by construction.
"""
from __future__ import annotations

import json
import os
import hashlib
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable


def read_json(path: str | Path | None, default: Any = None) -> Any:
    """Read JSON from ``path`` with lenient fallback semantics.

    Returns ``default`` if the path is empty/None, the file does not
    exist, the file is not a regular file, or the JSON cannot be
    decoded. This matches the behaviour of the ~98 ``_read_json``
    helpers it replaces.
    """
    if not path:
        return default
    p = Path(path)
    if not p.exists() or not p.is_file():
        return default
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return default


def write_json_atomic(
    path: str | Path,
    obj: Any,
    *,
    indent: int | None = 2,
    sort_keys: bool = True,
    ensure_dir: bool = True,
) -> Path:
    """Write JSON to ``path`` atomically via temp file + os.replace.

    On POSIX, ``os.replace`` on the same filesystem is atomic — no reader
    will see a half-written file. Callers that currently use
    ``path.write_text(json.dumps(...))`` should migrate to this helper to
    eliminate the "crash mid-write produces partial JSON" failure mode
    (~21 call sites in the operator scripts).

    Returns the resolved target Path.
    """
    target = Path(path)
    if ensure_dir:
        target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(obj, indent=indent, sort_keys=sort_keys)
    if not payload.endswith("\n"):
        payload += "\n"
    # Write to a unique temp file in the same directory so the rename is
    # an atomic same-filesystem op. NamedTemporaryFile + delete=False so
    # we keep the file across the close() and rename below.
    fd, tmp_name = tempfile.mkstemp(
        prefix=target.name + ".",
        suffix=".tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, target)
    except Exception:
        # Best-effort cleanup of the stray temp file; never mask the
        # original exception.
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return target


def write_text_atomic(
    path: str | Path,
    text: str,
    *,
    ensure_dir: bool = True,
    encoding: str = "utf-8",
) -> Path:
    """Write text to ``path`` atomically via temp file + os.replace."""
    target = Path(path)
    if ensure_dir:
        target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=target.name + ".",
        suffix=".tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding) as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, target)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return target


def write_jsonl_atomic(
    path: str | Path,
    rows: Iterable[dict[str, Any]],
    *,
    sort_keys: bool = True,
) -> Path:
    """Write JSONL rows atomically.

    JSONL read models are consumed by long-running workers and dashboards;
    using the same replace boundary as JSON prevents partial-line readers
    after an interrupted writer.
    """
    return write_text_atomic(
        path,
        "".join(json.dumps(row, sort_keys=sort_keys) + "\n" for row in rows),
    )


def append_jsonl_locked(path: str | Path, rec: dict[str, Any], *, ensure_ascii: bool = False) -> bool:
    """Cross-process-safe APPEND of one JSON record + newline to a SHARED ``.jsonl``, serialized by an exclusive
    ``flock`` so two concurrent workers cannot INTERLEAVE a multi-``write()`` large record — a torn line the
    reader then silently ``except: continue``-drops, losing BOTH adjacent records (the reuse-loss / artifact-
    corruption class from the 2026-07-05 shared-resource audit). THE single door for the large-record shared
    ledgers (proof-cache, closure-certs, bank-events, cot) that exceed the ~4 KB ``PIPE_BUF`` atomic-append
    guarantee. Best-effort: on any lock/IO error it falls back to a plain append (degrades to the prior torn
    risk, NEVER raises into the caller — a telemetry/ledger write must never break a closure). Returns True on a
    locked write. ``flock`` is advisory + local-FS; every writer to a given path MUST route through here for the
    guarantee to hold (same network-FS caveat the sqlite helper documents)."""
    line = json.dumps(rec, ensure_ascii=ensure_ascii) + "\n"
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        import fcntl                                     # POSIX (Linux VPS + macOS); ImportError ⇒ plain-append fallback
        with open(p, "a", encoding="utf-8") as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)   # block until we own the exclusive lock
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return True
    except Exception:  # noqa: BLE001 — lock/fs/platform failure ⇒ plain append (never break the caller)
        try:
            with open(p, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:  # noqa: BLE001
            pass
        return False


def sha256_file(path: str | Path) -> str | None:
    """Return sha256 for a regular file, or None when unavailable."""
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_ref(path: str | Path, *, root: str | Path | None = None) -> dict[str, Any]:
    """Small source-reference record for distributed read models.

    This is metadata only; it does not imply authority or proof credit.
    """
    p = Path(path)
    display = str(p)
    if root is not None:
        try:
            display = str(p.resolve().relative_to(Path(root).resolve()))
        except (OSError, ValueError):
            display = str(p)
    exists = p.exists() and p.is_file()
    return {
        "path": display,
        "exists": exists,
        "size_bytes": p.stat().st_size if exists else None,
        "sha256": sha256_file(p) if exists else None,
    }


def public_path(value, repo: "str | Path | None" = None) -> str:
    """Repo-relative path for public artifacts; no local home-directory leaks. THE canonical home (2026-06-22
    de-duplication): `solver_core._public_path` and `typed_exit._public_path` were byte-identical copies (the
    forgotten-sibling shape) and now both delegate here. `repo` defaults to this checkout's root."""
    if value is None:
        return ""
    s = str(value)
    if not s:
        return ""
    _repo = Path(repo) if repo is not None else Path(__file__).resolve().parents[3]
    try:
        p = Path(s)
        if not p.is_absolute():
            return s
        try:
            return str(p.resolve().relative_to(_repo))
        except Exception:
            pass
        try:
            return f"<home>/{p.resolve().relative_to(Path.home())}"
        except Exception:
            pass
        return f"<external>/{p.name}"
    except Exception:
        return s


def display_cmd(cmd: Iterable[str]) -> list[str]:
    """Collapse the host's Python in ``cmd[0]`` to ``"<python>"`` so logs
    are readable across hosts and venvs. Other arguments are returned
    verbatim."""
    cmd = list(cmd)
    if cmd and Path(cmd[0]).resolve() == Path(sys.executable).resolve():
        return ["<python>", *cmd[1:]]
    return cmd


def run(
    cmd: list[str],
    *,
    timeout_s: int | None = None,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
    stdout_tail_chars: int = 4000,
    stderr_tail_chars: int = 4000,
) -> dict[str, Any]:
    """Run ``cmd`` as a subprocess with explicit timeout handling.

    Returns a structured dict:

        {
          "cmd": <list, with host python collapsed>,
          "returncode": <int; 124 on timeout>,
          "timed_out": <bool>,
          "stdout_tail": <str, last N chars>,
          "stderr_tail": <str, last N chars>,
        }

    Never raises ``CalledProcessError``; callers branch on returncode.
    Subprocess is invoked with ``shell=False`` always (the cmd is a
    list). Operator scripts use this pattern in ~252 places today;
    migrating them to this helper is the cleanest dedup target after the
    queue/event-ledger primitives.
    """
    display = display_cmd(cmd)
    try:
        proc = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=timeout_s if timeout_s and timeout_s > 0 else None,
            cwd=str(cwd) if cwd else None,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": display,
            "returncode": 124,
            "timed_out": True,
            "stdout_tail": (exc.stdout or "")[-stdout_tail_chars:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-stderr_tail_chars:] if isinstance(exc.stderr, str) else "",
        }
    return {
        "cmd": display,
        "returncode": int(proc.returncode),
        "timed_out": False,
        "stdout_tail": (proc.stdout or "")[-stdout_tail_chars:],
        "stderr_tail": (proc.stderr or "")[-stderr_tail_chars:],
    }


def sqlite_open(
    db_path: str | Path,
    *,
    busy_timeout_ms: int = 5000,
    wal: bool = True,
    foreign_keys: bool = True,
    row_factory: type | None = sqlite3.Row,
) -> sqlite3.Connection:
    """Open a SQLite connection with WAL + busy_timeout + foreign_keys.

    These pragmas are repeated in ~77 places in the operator scripts.
    Centralising them ensures every connection uses the same durability
    and concurrency posture.
    """
    p = Path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    cx = sqlite3.connect(str(p), isolation_level=None, timeout=30.0)
    if wal:
        cx.execute("PRAGMA journal_mode=WAL")
    cx.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
    if foreign_keys:
        cx.execute("PRAGMA foreign_keys=ON")
    if row_factory is not None:
        cx.row_factory = row_factory
    return cx


# Public API ----------------------------------------------------------------

__all__ = [
    "read_json",
    "write_json_atomic",
    "write_text_atomic",
    "write_jsonl_atomic",
    "sha256_file",
    "file_ref",
    "display_cmd",
    "run",
    "sqlite_open",
]


# Self-test --------------------------------------------------------------

def _self_test() -> int:
    import shutil

    # read_json on missing / corrupt / good
    assert read_json("/nonexistent/path", default={"d": 1}) == {"d": 1}
    with tempfile.TemporaryDirectory(prefix="lm_common_test_") as td:
        td_path = Path(td)
        good = td_path / "good.json"
        good.write_text('{"a": 1}')
        assert read_json(good) == {"a": 1}
        bad = td_path / "bad.json"
        bad.write_text("{not json")
        assert read_json(bad, default={}) == {}

        # write_json_atomic round-trip
        target = td_path / "sub" / "out.json"
        write_json_atomic(target, {"hello": "world"})
        assert target.exists()
        assert read_json(target) == {"hello": "world"}

        # write_json_atomic does not leave temp files around on success
        siblings = list(target.parent.iterdir())
        assert all(s.name == "out.json" for s in siblings), siblings

        # write_text_atomic and write_jsonl_atomic round-trip.
        text_target = td_path / "sub" / "out.md"
        write_text_atomic(text_target, "hello\n")
        assert text_target.read_text() == "hello\n"
        jsonl_target = td_path / "sub" / "rows.jsonl"
        write_jsonl_atomic(jsonl_target, [{"b": 2}, {"a": 1}])
        assert jsonl_target.read_text().count("\n") == 2
        assert file_ref(jsonl_target, root=td_path)["sha256"] == sha256_file(jsonl_target)

        # write_json_atomic leaves prior file intact if write fails
        # (simulated by raising from a custom encoder via non-serialisable object)
        try:
            write_json_atomic(target, {"x": object()})  # object() is not JSON-serialisable
        except TypeError:
            pass
        assert read_json(target) == {"hello": "world"}

        # subprocess run: success
        r = run([sys.executable, "-c", "print('hi')"])
        assert r["returncode"] == 0, r
        assert "hi" in r["stdout_tail"]
        assert r["timed_out"] is False

        # subprocess run: nonzero
        r2 = run([sys.executable, "-c", "import sys; sys.exit(7)"])
        assert r2["returncode"] == 7, r2

        # subprocess run: timeout
        r3 = run([sys.executable, "-c", "import time; time.sleep(5)"], timeout_s=1)
        assert r3["timed_out"] is True
        assert r3["returncode"] == 124

        # sqlite_open: WAL + busy_timeout applied
        db = td_path / "t.sqlite"
        cx = sqlite_open(db)
        try:
            mode = cx.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode.upper() == "WAL", mode
            bt = cx.execute("PRAGMA busy_timeout").fetchone()[0]
            assert int(bt) >= 5000, bt
        finally:
            cx.close()
            del cx
            # On macOS WAL leaves -wal/-shm files; cleanup happens with TemporaryDirectory
        shutil.rmtree(target.parent.parent, ignore_errors=True)
    print("ztare.leanmill.common self-test PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(_self_test())
