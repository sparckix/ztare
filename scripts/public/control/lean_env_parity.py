#!/usr/bin/env python3
"""Lean sandbox parity probe for local/VPS runs.

This is intentionally a probe, not a self-test in sync_parity.sh's
machine-safe set: it invokes Lean. It checks the pinned Carleson
sandbox used by the proof-search harness, not the repo root, because
the repo root may not have a default elan toolchain configured.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))


def _env() -> dict[str, str]:
    env = os.environ.copy()
    elan_bin = Path.home() / ".elan" / "bin"
    if elan_bin.exists():
        env["PATH"] = f"{elan_bin}:{env.get('PATH', '')}"
    return env


def _run(cmd: list[str], cwd: Path, timeout: int) -> dict[str, Any]:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=_env(),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "ok": p.returncode == 0,
            "returncode": p.returncode,
            "stdout": p.stdout.strip()[:2000],
            "stderr": p.stderr.strip()[:2000],
            "cmd": cmd,
        }
    except Exception as e:
        return {"ok": False, "error": repr(e), "cmd": cmd}


def probe(timeout: int) -> dict[str, Any]:
    import coherent_rung1 as cr

    sb = Path(cr.SB)
    toolchain = sb / "lean-toolchain"
    backend_dirs = {
        "Hammer": sb / ".lake/packages/Hammer/.lake/build/lib/lean",
        "Duper": sb / ".lake/packages/Duper/.lake/build/lib/lean",
        "auto": sb / ".lake/packages/auto/.lake/build/lib/lean",
    }
    zipperposition_exe = sb / ".lake/packages/auto/.lake/build/zipperposition.exe"
    eval_file = Path(tempfile.gettempdir()) / "ztare_lean_env_parity_eval.lean"
    eval_file.write_text("#eval (1 + 1 : Nat)\n")
    version = _run(["lake", "env", "lean", "--version"], sb, timeout)
    eval_res = _run(["lake", "env", "lean", str(eval_file)], sb, timeout)
    lake = shutil.which("lake", path=_env().get("PATH"))
    lean = shutil.which("lean", path=_env().get("PATH"))
    rec = {
        "ok": bool(version.get("ok") and eval_res.get("ok")),
        "repo": str(REPO),
        "sandbox": str(sb),
        "sandbox_exists": sb.exists(),
        "lean_toolchain": toolchain.read_text().strip() if toolchain.exists() else None,
        "lake_path": lake,
        "lean_path": lean,
        "backend_build_dirs": {
            name: {"path": str(path), "exists": path.exists()}
            for name, path in backend_dirs.items()
        },
        "zipperposition_exe": {
            "path": str(zipperposition_exe),
            "exists": zipperposition_exe.exists(),
            "executable": os.access(zipperposition_exe, os.X_OK),
        },
        "version": version,
        "eval": eval_res,
    }
    rec["backend_ready"] = bool(
        rec["ok"]
        and all(v["exists"] for v in rec["backend_build_dirs"].values())
        and rec["zipperposition_exe"]["exists"]
        and rec["zipperposition_exe"]["executable"]
    )
    return rec


def self_test() -> int:
    env = _env()
    assert "PATH" in env
    assert REPO.name == "figs_activist_loop"
    print("lean_env_parity self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--require-backends", action="store_true",
                    help="Exit non-zero unless Hammer/Duper/auto and Zipperposition are ready.")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    rec = probe(args.timeout)
    print(json.dumps(rec, indent=1, sort_keys=True))
    if args.require_backends:
        return 0 if rec.get("backend_ready") else 1
    return 0 if rec["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
