#!/usr/bin/env python3
"""Faster Lean compile via `lake env lean <file>` (vs `lake build <module>`).

`lake build` runs the full build system per call: index loading, dependency
walking, cache update. For our use case (compile a single candidate file
many times in a closed-loop verifier) most of that is overhead.

`lake env lean <file>` runs the compiler directly in lake's environment —
no build-system traversal, no cache update. On NS Track B's spine size
this is typically 3-5x faster per call.

# When to use this vs lake build

  Use lake_fast_compile when:
    - Compiling a single candidate file repeatedly (closed-loop verifier)
    - You don't need the build cache updated
    - You want fast turnaround on the SAME file with mutations

  Use compile_lean (lake build) when:
    - Adding the file as a permanent module of the project
    - You want the build cache to reflect the result
    - You're checking if a file integrates into the project's dependency graph

# Honest scope

  - This bypasses lake's dependency caching. If the candidate references
    declarations from project modules that haven't been built yet, those
    will be built lazily; once built they're cached for the next call.
  - Output format: same dict shape as compile_lean (compiled, stdout,
    stderr, exit_code, duration_s) so it's a drop-in replacement.

Usage in scripts:
    from lean_fast_compile import compile_lean_fast
    result = compile_lean_fast(lean_path, ztare_proofs_root)
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any


def compile_lean_fast(
    lean_path: Path,
    ztare_proofs_root: Path,
    timeout_seconds: int = 90,
) -> dict[str, Any]:
    """Compile a single Lean file via `lake env lean <file>`.

    Drop-in replacement for `compile_lean` (in `src/ztare/gates/lean_proof_gate.py`)
    when you only care about whether THIS file compiles, not whether it
    integrates into the project's build cache.
    """
    cmd = ["lake", "env", "lean", str(lean_path)]
    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd, cwd=str(ztare_proofs_root),
            capture_output=True, text=True,
            timeout=timeout_seconds, check=False,
        )
        duration = time.monotonic() - started
        return {
            "compiled": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
            "duration_s": duration,
            "compile_method": "lake env lean",
        }
    except FileNotFoundError:
        return {
            "compiled": False,
            "stdout": "",
            "stderr": "lake not found in PATH",
            "exit_code": 127,
            "duration_s": time.monotonic() - started,
            "compile_method": "lake env lean",
        }
    except subprocess.TimeoutExpired:
        return {
            "compiled": False,
            "stdout": "",
            "stderr": f"timeout after {timeout_seconds}s",
            "exit_code": 124,
            "duration_s": timeout_seconds,
            "compile_method": "lake env lean",
        }


def compile_lean_fast_combined_output(
    lean_path: Path,
    ztare_proofs_root: Path,
    timeout_seconds: int = 90,
) -> dict[str, Any]:
    """Same as compile_lean_fast but combines stdout+stderr.

    Solves the apparatus gap surfaced 2026-05-06: lake's build errors
    appear in STDOUT not STDERR. Stage 4 categorize_failure was missing
    them. By combining outputs, downstream classifiers see the real error.
    """
    result = compile_lean_fast(lean_path, ztare_proofs_root, timeout_seconds)
    combined = (result.get("stdout") or "") + "\n" + (result.get("stderr") or "")
    result["combined_output"] = combined
    # Overwrite stderr with combined so legacy callers see the real error
    if not result.get("stderr") and result.get("stdout"):
        result["stderr"] = combined
    return result


def benchmark(lean_path: Path, ztare_proofs_root: Path,
                n_runs: int = 3) -> dict[str, Any]:
    """Compare lake env lean vs lake build on the same file."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from src.ztare.gates.lean_proof_gate import compile_lean

    fast_durations = []
    for _ in range(n_runs):
        r = compile_lean_fast(lean_path, ztare_proofs_root)
        fast_durations.append(r["duration_s"])

    build_durations = []
    for _ in range(n_runs):
        r = compile_lean(lean_path, ztare_proofs_root)
        build_durations.append(r["duration_s"])

    return {
        "lake_env_lean_avg_s": sum(fast_durations) / max(len(fast_durations), 1),
        "lake_build_avg_s": sum(build_durations) / max(len(build_durations), 1),
        "speedup": (sum(build_durations) / max(sum(fast_durations), 0.001)),
        "fast_durations": fast_durations,
        "build_durations": build_durations,
    }


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", type=Path,
                    help="benchmark fast vs build on this Lean file")
    ap.add_argument("--proofs-root", type=Path,
                    default=Path(__file__).resolve().parents[1] / "ztare_proofs")
    ap.add_argument("--n-runs", type=int, default=3)
    args = ap.parse_args()
    if args.benchmark:
        r = benchmark(args.benchmark, args.proofs_root, args.n_runs)
        print(json.dumps(r, indent=2))
    else:
        ap.print_help()
