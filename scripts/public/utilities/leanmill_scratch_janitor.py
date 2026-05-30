#!/usr/bin/env python3
"""LeanMill scratch janitor.

Purges aged per-probe-run subdirectories and stray scratch files under
/tmp/rung1 (or another configured scratch root). Operational housekeeping
only — never touches durable state (SQLite queue, event ledger, registries,
repair-family specs, factory_dashboard_data).

Design intent (per architecture review 2026-05-23):
- /tmp/rung1 grows ~3.6 GB/month at current cadence with no automatic cleanup.
- Per-probe-run directories under /tmp/rung1/leanmill_24x7_learning/ are
  consumed by the probe worker and the post-probe triage; once a follow-up
  WorkItem has been enqueued, the directory has no live reader.
- Default TTL is conservative (14 days) so that any in-flight retry that
  resurrects an old probe still finds its artifacts.
- The janitor is read-only on directories newer than the TTL and write-only
  (rm) on directories older than the TTL. It never touches files in
  /tmp/rung1/ that are not part of a recognised LeanMill subtree.

Recognised LeanMill scratch subtrees:
  /tmp/rung1/leanmill_24x7_learning/             (per-probe-run dirs)
  /tmp/rung1/leanmill_evaluation_harness/        (per-run dirs from the harness)
  /tmp/rung1/leanmill_canary_result_cache/       (probe result deduplication)
  /tmp/rung1/mcb_expand100/                      (corpus expansion staging)
  /tmp/rung1/mcb_refill_dedup_after_expand100/   (corpus refill staging)

Run with --dry-run first; then add --apply to actually delete.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any


RECOGNISED_SUBTREES = (
    "leanmill_24x7_learning",
    "leanmill_evaluation_harness",
    "leanmill_canary_result_cache",
    "mcb_expand100",
    "mcb_refill_dedup_after_expand100",
)

# Locks the janitor must never delete (heavy-Lean serialisation).
PROTECTED_NAMES = frozenset({
    "leanmill_heavy_lean.lock",
})


def _now() -> int:
    return int(time.time())


def _dir_size_bytes(path: Path) -> int:
    total = 0
    try:
        for child in path.rglob("*"):
            if child.is_file():
                try:
                    total += child.stat().st_size
                except OSError:
                    continue
    except OSError:
        pass
    return total


def _humanise(n_bytes: int) -> str:
    n = float(n_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def _candidates(root: Path, ttl_s: int) -> list[dict[str, Any]]:
    now = _now()
    found: list[dict[str, Any]] = []
    if not root.exists() or not root.is_dir():
        return found
    for subtree_name in RECOGNISED_SUBTREES:
        subtree = root / subtree_name
        if not subtree.exists() or not subtree.is_dir():
            continue
        for child in subtree.iterdir():
            if child.name in PROTECTED_NAMES:
                continue
            try:
                mtime = int(child.stat().st_mtime)
            except OSError:
                continue
            age_s = now - mtime
            if age_s < ttl_s:
                continue
            size = _dir_size_bytes(child) if child.is_dir() else child.stat().st_size
            found.append({
                "path": str(child),
                "subtree": subtree_name,
                "mtime": mtime,
                "age_s": age_s,
                "size_bytes": size,
                "is_dir": child.is_dir(),
            })
    return found


def _delete(target: Path) -> dict[str, Any]:
    try:
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        return {"path": str(target), "deleted": True}
    except OSError as exc:
        return {"path": str(target), "deleted": False, "error": str(exc)}


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root)
    ttl_s = int(args.ttl_days) * 86_400
    candidates = _candidates(root, ttl_s)
    candidates.sort(key=lambda c: c["age_s"], reverse=True)
    total_bytes = sum(c["size_bytes"] for c in candidates)
    if args.max_delete and len(candidates) > args.max_delete:
        candidates = candidates[: args.max_delete]
    deletions: list[dict[str, Any]] = []
    if args.apply:
        for cand in candidates:
            deletions.append(_delete(Path(cand["path"])))
    return {
        "schema": "leanmill-scratch-janitor-v1",
        "root": str(root),
        "ttl_days": int(args.ttl_days),
        "recognised_subtrees": list(RECOGNISED_SUBTREES),
        "candidates_count": len(candidates),
        "total_candidate_bytes": total_bytes,
        "total_candidate_human": _humanise(total_bytes),
        "dry_run": not args.apply,
        "candidates": candidates,
        "deletions": deletions,
    }


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_janitor_") as td:
        root = Path(td)
        # build a recognised subtree with one old and one fresh entry
        subtree = root / "leanmill_24x7_learning"
        old = subtree / "probe_run_old"
        fresh = subtree / "probe_run_fresh"
        old.mkdir(parents=True)
        fresh.mkdir(parents=True)
        (old / "scoreboard.json").write_text("{}\n")
        (fresh / "scoreboard.json").write_text("{}\n")
        # Backdate old entry by 30 days.
        old_age = _now() - 30 * 86_400
        for p in (old, old / "scoreboard.json"):
            import os
            os.utime(p, (old_age, old_age))
        cands = _candidates(root, ttl_s=14 * 86_400)
        names = {Path(c["path"]).name for c in cands}
        assert "probe_run_old" in names, f"expected old run in candidates, got {names}"
        assert "probe_run_fresh" not in names, f"fresh run must not be in candidates, got {names}"
        # An unrecognised subtree must not be touched.
        rogue = root / "not_a_leanmill_subtree"
        rogue.mkdir()
        (rogue / "stuff.txt").write_text("x")
        for p in (rogue, rogue / "stuff.txt"):
            import os
            os.utime(p, (old_age, old_age))
        cands2 = _candidates(root, ttl_s=14 * 86_400)
        assert all(Path(c["path"]).name != "stuff.txt" for c in cands2)
    print("leanmill_scratch_janitor self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Purge aged LeanMill scratch under /tmp/rung1")
    ap.add_argument("--root", default="/tmp/rung1", help="scratch root (default /tmp/rung1)")
    ap.add_argument("--ttl-days", type=int, default=14, help="age threshold; files older than this are eligible")
    ap.add_argument("--max-delete", type=int, default=0, help="cap on number of deletions per run; 0 = no cap")
    ap.add_argument("--apply", action="store_true", help="actually delete; default is dry-run")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    result = run(args)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
