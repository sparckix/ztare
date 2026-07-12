#!/usr/bin/env python3
"""collision_table.py — (s, a, t)-collision table across all episodes.

Builds the canonical collision table for a project's visible + holdout episodes:
rows sharing identical (state, action, timestep) triples, their next-state
hashes, and crude history-divergence metadata.  Writes the result to
``workspace/collision_table.json`` and prints a summary.

A collision is a pair of rows from possibly-different episodes that share the
same (s, a, t) key but differ in next-state (s_next).  A history-divergent
collision additionally has a different preceding-row hash — evidence that the
differing outcomes may reflect different hidden history rather than genuine
non-determinism.

**Verdict language:** the output uses "support-local Markov consistency" language.
Absence of collisions *supports* the Markov assumption locally; it does not prove
it.  The distinction is deliberate and must not be softened.

Usage:
    PYTHONPATH=src python scripts/public/validators/collision_table.py \\
        --project projects/arc3_ls20_gov

Output:
    workspace/collision_table.json  (also printed as summary to stdout)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# Hashing helpers
# ---------------------------------------------------------------------------

def _state_hash(s: object) -> str:
    return hashlib.md5(json.dumps(s, sort_keys=True).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Episode loader
# ---------------------------------------------------------------------------

def _iter_episode_files(project_dir: Path):
    """Yield all episode JSONL files under raw/episodes (visible + holdout)."""
    ep_root = project_dir / "raw" / "episodes"
    if not ep_root.exists():
        return
    for f in sorted(ep_root.rglob("*.jsonl")):
        yield f


def _load_rows(ep_file: Path) -> list[dict]:
    rows = []
    with ep_file.open() as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


# ---------------------------------------------------------------------------
# Core table builder
# ---------------------------------------------------------------------------

def build_collision_table(project_dir: Path) -> dict:
    """Build and return the collision table dict.

    Keys in the returned dict:
        n_rows: total episode rows read
        n_collisions: rows sharing (s,a,t) but with different s_next hash
        n_history_divergent_collisions: subset where preceding-row hash also differs
        verdict: support/consistency language (NEVER "proven")
        episodes: list of episode file names processed
        collisions: list of collision records (capped at 500 for file size)
    """
    # key → list of row metadata dicts
    sat_index: dict[tuple, list[dict]] = defaultdict(list)
    total_rows = 0
    episode_names = []

    for ep_file in _iter_episode_files(project_dir):
        episode_names.append(ep_file.name)
        rows = _load_rows(ep_file)
        prev_hash = None
        for idx, row in enumerate(rows):
            s = row.get("s")
            a = row.get("a")
            t = row.get("t")
            s_next = row.get("s_next")
            if s is None or a is None or t is None or s_next is None:
                prev_hash = None
                continue
            s_hash = _state_hash(s)
            s_next_hash = _state_hash(s_next)
            sat_key = (s_hash, str(a), int(t) if isinstance(t, (int, float)) else str(t))
            sat_index[sat_key].append({
                "episode": ep_file.name,
                "row_idx": idx,
                "s_next_hash": s_next_hash,
                "prev_row_hash": prev_hash,
            })
            prev_hash = hashlib.md5(f"{s_hash}|{a}|{t}|{s_next_hash}".encode()).hexdigest()
            total_rows += 1

    # Identify collisions
    collisions = []
    n_collisions = 0
    n_history_divergent = 0

    for sat_key, entries in sat_index.items():
        if len(entries) < 2:
            continue
        # check if any pair has differing s_next
        hashes = {e["s_next_hash"] for e in entries}
        if len(hashes) == 1:
            continue  # all agree — consistent

        n_collisions += len(entries)
        # check history divergence: any pair has differing prev_row_hash?
        prev_hashes = {e["prev_row_hash"] for e in entries if e["prev_row_hash"] is not None}
        hist_divergent = len(prev_hashes) > 1
        if hist_divergent:
            n_history_divergent += len(entries)

        if len(collisions) < 500:
            collisions.append({
                "sat_key": list(sat_key),
                "n_entries": len(entries),
                "distinct_s_next_hashes": list(hashes),
                "history_divergent": hist_divergent,
                "entries": entries[:10],  # cap per-collision detail
            })

    if n_collisions == 0:
        verdict = (
            "support-local Markov consistency: no (s,a,t)-collisions with differing "
            "next-state found across all episodes; this is consistent with a "
            "deterministic Markov law but does not prove it"
        )
    else:
        verdict = (
            f"local Markov consistency not supported: {n_collisions} row(s) share "
            f"identical (s,a,t) but differ in next-state; "
            f"{n_history_divergent} involve history-divergent preceding rows "
            f"(differing contexts may explain some mismatches)"
        )

    return {
        "n_rows": total_rows,
        "n_collisions": n_collisions,
        "n_history_divergent_collisions": n_history_divergent,
        "verdict": verdict,
        "episodes": episode_names,
        "collisions": collisions,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--project", required=True,
                        help="Path to project root (e.g. projects/arc3_ls20_gov)")
    args = parser.parse_args(argv)

    project_dir = _REPO_ROOT / args.project if not Path(args.project).is_absolute() else Path(args.project)
    if not project_dir.exists():
        print(f"ERROR: project dir not found: {project_dir}", file=sys.stderr)
        sys.exit(1)

    result = build_collision_table(project_dir)

    workspace = project_dir / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    out_path = workspace / "collision_table.json"
    with out_path.open("w") as f:
        json.dump(result, f, indent=2)

    # Print summary (without the full collision list)
    summary = {k: v for k, v in result.items() if k != "collisions"}
    print(json.dumps(summary, indent=2))
    print(f"\nFull table written to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
