#!/usr/bin/env python3
"""SAFE Lean test runner — operator-mandated resource limits.

Use this instead of ad-hoc parallel bash loops to avoid system overload.

Principles:
  1. Max 2 parallel workers by default (not 10)
  2. Per-test timeout default 60s (not 240s); only B1 hammer gets 120s
  3. Check system load between batches; sleep if load > N_CORES * 1.5
  4. Use `nice -n 10` for lower priority
  5. Kill grandchildren on timeout (process group)

Usage:
  safe_lean_runner.py --files V30eKfold/K*.lean [--workers 2] [--timeout 60]
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
SANDBOX = ROOT / "analytics/public/leanmill/external_benchmarks/sandboxes/v28A_carleson_baseline/carleson"

def now(): return time.strftime("%H:%M:%S")


def get_load():
    try:
        return os.getloadavg()[0]
    except OSError:
        return 0.0


def n_cores():
    try:
        return os.cpu_count() or 4
    except Exception:
        return 4


def wait_for_load_to_drop(threshold_mult=1.5):
    """Block until 1-min load avg < N_CORES * threshold_mult."""
    threshold = n_cores() * threshold_mult
    while True:
        load = get_load()
        if load < threshold:
            return
        print(f"  [{now()}] load={load:.2f} > {threshold:.0f}, sleeping 10s...")
        time.sleep(10)


def run_lean_safe(file_rel, timeout=60):
    """Run lake env lean with nice + process group kill on timeout."""
    started = time.time()
    try:
        # Start new process group so we can kill grandchildren (lean, zipperposition)
        proc = subprocess.Popen(
            ["nice", "-n", "10", "lake", "env", "lean", file_rel],
            cwd=SANDBOX, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            elapsed = round(time.time() - started, 2)
            out = stdout + "\n" + stderr
            err = bool(re.search(r"^\S*\.lean:\d+:\d+: error:", out, re.MULTILINE))
            return {
                "compiled": (proc.returncode == 0 and not err),
                "elapsed": elapsed,
                "stdout_tail": out[-400:],
                "rc": proc.returncode,
            }
        except subprocess.TimeoutExpired:
            # Kill entire process group (kills lean + zipperposition grandchildren)
            try:
                os.killpg(os.getpgid(proc.pid), 9)
            except ProcessLookupError:
                pass
            proc.wait(timeout=5)
            return {"compiled": False, "elapsed": timeout, "timed_out": True, "stdout_tail": "", "rc": None}
    except Exception as e:
        return {"compiled": False, "elapsed": 0, "error": str(e), "stdout_tail": ""}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="+", required=True)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--load-threshold-mult", type=float, default=1.5)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    files = [Path(f) for f in args.files]
    # Convert to relative paths under SANDBOX
    rels = []
    for f in files:
        try:
            rels.append(str(f.relative_to(SANDBOX)))
        except ValueError:
            rels.append(str(f))

    print(f"[safe_lean] {len(rels)} files, {args.workers} workers, {args.timeout}s timeout, nice +10")

    results = []
    # Process in chunks; wait for load to drop between chunks
    chunk_size = args.workers
    for i in range(0, len(rels), chunk_size):
        chunk = rels[i:i + chunk_size]
        wait_for_load_to_drop(args.load_threshold_mult)
        print(f"  [{now()}] chunk {i//chunk_size + 1}/{(len(rels)+chunk_size-1)//chunk_size}: {[Path(r).stem for r in chunk]}")
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
            futures = {ex.submit(run_lean_safe, r, args.timeout): r for r in chunk}
            for fut in concurrent.futures.as_completed(futures):
                r = futures[fut]
                res = fut.result()
                results.append({"file": r, **res})
                mark = "✓" if res["compiled"] else ("⏱" if res.get("timed_out") else "·")
                print(f"    [{now()}] {mark} {Path(r).stem} compiled={res['compiled']} elapsed={res['elapsed']}s")

    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=2, sort_keys=True))
        print(f"\nwrote {args.out}")

    compiled = sum(1 for r in results if r["compiled"])
    print(f"\n=== SUMMARY: {compiled}/{len(results)} compiled ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
