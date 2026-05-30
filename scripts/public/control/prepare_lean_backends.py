#!/usr/bin/env python3
"""Prepare local Lean backend artifacts for the governed proof harness.

This is the reproducible server-side setup for Hammer/Duper/auto:
it builds the pinned sandbox backend oleans and ensures the
Zipperposition executable used by lean-auto/Hammer exists. It avoids a
hard dependency on the OS `unzip` package by using Python stdlib when
the package post-update hook leaves the zip behind.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))

ZIPPER_URL = (
    "https://github.com/sneeuwballen/zipperposition/releases/download/2.1/"
    "zipperposition-bin-ubuntu-latest-4.12.x.exe.zip"
)


def _env() -> dict[str, str]:
    env = os.environ.copy()
    elan_bin = Path.home() / ".elan" / "bin"
    if elan_bin.exists():
        env["PATH"] = f"{elan_bin}:{env.get('PATH', '')}"
    return env


def _run(cmd: list[str], cwd: Path, timeout: int) -> dict[str, Any]:
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=_env(),
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    return {
        "cmd": cmd,
        "ok": p.returncode == 0,
        "returncode": p.returncode,
        "stdout": p.stdout.strip()[-4000:],
        "stderr": p.stderr.strip()[-4000:],
    }


def _chmod_exec(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def prepare(timeout: int, download: bool) -> dict[str, Any]:
    import coherent_rung1 as cr

    sb = Path(cr.SB)
    if not sb.exists():
        return {"ok": False, "reason": "sandbox_missing", "sandbox": str(sb)}
    if not shutil.which("lake", path=_env().get("PATH")):
        return {"ok": False, "reason": "lake_missing", "sandbox": str(sb)}

    auto_build = sb / ".lake/packages/auto/.lake/build"
    zip_path = auto_build / "zipperposition-bin-ubuntu-latest-4.12.x.exe.zip"
    exe = auto_build / "zipperposition.exe"
    events: list[dict[str, Any]] = []

    events.append(_run(["lake", "build", "Hammer"], sb, timeout))
    if not events[-1]["ok"]:
        return {"ok": False, "reason": "lake_build_hammer_failed",
                "sandbox": str(sb), "events": events}

    if not exe.exists():
        upd = _run(["lake", "update", "Hammer"], sb, timeout)
        events.append(upd)

    if not exe.exists() and download and not zip_path.exists():
        auto_build.mkdir(parents=True, exist_ok=True)
        try:
            urllib.request.urlretrieve(ZIPPER_URL, zip_path)
            events.append({"cmd": ["download", ZIPPER_URL], "ok": True,
                           "path": str(zip_path)})
        except Exception as e:
            events.append({"cmd": ["download", ZIPPER_URL], "ok": False,
                           "error": repr(e)})

    if not exe.exists() and zip_path.exists():
        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(auto_build)
            events.append({"cmd": ["python_zipfile_extract", str(zip_path)],
                           "ok": True})
        except Exception as e:
            events.append({"cmd": ["python_zipfile_extract", str(zip_path)],
                           "ok": False, "error": repr(e)})

    if exe.exists():
        _chmod_exec(exe)

    backend_dirs = {
        "Hammer": sb / ".lake/packages/Hammer/.lake/build/lib/lean",
        "Duper": sb / ".lake/packages/Duper/.lake/build/lib/lean",
        "auto": sb / ".lake/packages/auto/.lake/build/lib/lean",
    }
    rec = {
        "ok": bool(exe.exists() and os.access(exe, os.X_OK)
                   and all(p.exists() for p in backend_dirs.values())),
        "sandbox": str(sb),
        "backend_build_dirs": {
            k: {"path": str(v), "exists": v.exists()}
            for k, v in backend_dirs.items()
        },
        "zipperposition_exe": {
            "path": str(exe),
            "exists": exe.exists(),
            "executable": os.access(exe, os.X_OK),
        },
        "events": events,
    }
    if not rec["ok"]:
        rec["reason"] = "backend_artifacts_incomplete"
    return rec


def self_test() -> int:
    assert ZIPPER_URL.endswith(".zip")
    assert REPO.name == "figs_activist_loop"
    print("prepare_lean_backends self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--no-download", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    rec = prepare(args.timeout, download=not args.no_download)
    print(json.dumps(rec, indent=1, sort_keys=True))
    return 0 if rec["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
