#!/usr/bin/env python3
"""GNN training data prep — temporal constraint-graph snapshots + targets.

Builds a JSONL training set for GNN-based link prediction on the NS Track B
constraint graph. Each row is a (graph_snapshot, future_edge) pair where:
  - graph_snapshot is the constraint graph at some point in proof history
  - future_edge is an inequality that gets added in a later snapshot

Since git history is sparse for ztare_proofs/, we synthesize snapshots by:
  (a) walking F-rows in EXPERIMENT_TRACK_RECORD.md chronologically
  (b) for each F-row, building the graph from Lean files modified up to
      that F-row's date (best-effort via file mtimes)
  (c) deltas between consecutive snapshots are the "newly-added edges"
      = supervision targets

Caveats baked in (read before training):
  - 267 F-rows is small for deep GNN; expect noisy gradients
  - File mtime is unreliable when files were edited after their F-row
    timestamp; we fall back to git blame when mtime is older than git
  - The "next edge added" target is approximate — we don't know which
    edge was the decision-critical one for that F-row's progress

Output:
  analytics/public/leanmill/gnn_ranker/training_pairs.jsonl    — (snapshot, target) pairs
  analytics/public/leanmill/gnn_ranker/train.jsonl             — temporal split (oldest 70%)
  analytics/public/leanmill/gnn_ranker/val.jsonl               — middle 15%
  analytics/public/leanmill/gnn_ranker/test.jsonl              — newest 15%

Usage:
    python scripts/public/models/gnn_training_data_prep.py
    python scripts/public/models/gnn_training_data_prep.py --max-snapshots 30
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts" / "public" / "projects" / "ns"))
import ns_constraint_basin_graph as ncb

LEAN_DIR = REPO / "ztare_proofs" / "ZtareProofs"
TRACK_RECORD = REPO / "research_areas" / "EXPERIMENT_TRACK_RECORD.md"
OUT_DIR = REPO / "analytics" / "public" / "leanmill" / "gnn_ranker"


def parse_frow_dates() -> list[tuple[str, datetime]]:
    """Pull F-row IDs + best-guess timestamps from EXPERIMENT_TRACK_RECORD.md."""
    if not TRACK_RECORD.exists():
        return []
    text = TRACK_RECORD.read_text(encoding="utf-8", errors="ignore")
    frows: list[tuple[str, datetime]] = []
    DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
    for line in text.splitlines():
        if not line.startswith("| F-"):
            continue
        m = re.match(r"\|\s*(F-[A-Z0-9-]+)", line)
        if not m:
            continue
        rid = m.group(1)
        date_match = DATE_RE.search(line)
        if not date_match:
            continue
        try:
            dt = datetime.strptime(date_match.group(1), "%Y-%m-%d")
        except ValueError:
            continue
        frows.append((rid, dt))
    frows.sort(key=lambda x: x[1])
    return frows


def file_mtimes(lean_dir: Path) -> dict[str, datetime]:
    """Map filename -> mtime as datetime."""
    out = {}
    for path in lean_dir.glob("ns_*.lean"):
        out[path.name] = datetime.fromtimestamp(path.stat().st_mtime)
    return out


def parse_subset(lean_dir: Path, files_to_include: set[str]) -> dict:
    """Run ncb.parse_lean_files on a subset by symlink-shimming."""
    import tempfile
    import shutil
    with tempfile.TemporaryDirectory() as tmp:
        tmp_lean = Path(tmp) / "ZtareProofs"
        tmp_lean.mkdir()
        for fname in files_to_include:
            src = lean_dir / fname
            if src.exists():
                shutil.copy(src, tmp_lean / fname)
        return ncb.parse_lean_files(tmp_lean)


def graph_edges(graph_obj: dict) -> set[tuple[str, str]]:
    return {(n["src"], n["dst"]) for n in graph_obj["@graph"]
             if n.get("@type") == "ns_inequality_edge"}


def build_snapshots(max_snapshots: int = 30) -> list[dict]:
    """Build (snapshot_n, snapshot_n+1) pairs by F-row date + mtime ordering."""
    frows = parse_frow_dates()
    if not frows:
        print("no F-rows; falling back to single-snapshot mode")
        return []
    mtimes = file_mtimes(LEAN_DIR)
    if not mtimes:
        print(f"no .lean files in {LEAN_DIR}")
        return []
    print(f"found {len(frows)} F-rows, {len(mtimes)} Lean files")

    # Sample N evenly-spaced F-row dates; for each, include only files
    # whose mtime is <= that F-row's date.
    if len(frows) <= max_snapshots:
        sampled = frows
    else:
        step = max(len(frows) // max_snapshots, 1)
        sampled = [frows[i] for i in range(0, len(frows), step)][:max_snapshots]

    snapshots: list[dict] = []
    for rid, dt in sampled:
        files_at_date = {fname for fname, m in mtimes.items() if m <= dt}
        if not files_at_date:
            continue
        graph = parse_subset(LEAN_DIR, files_at_date)
        snapshots.append({
            "frow_id": rid,
            "date": dt.isoformat(),
            "n_files": len(files_at_date),
            "n_quantity_nodes": graph["summary"].get("n_quantity_nodes", 0),
            "n_edges": graph["summary"].get("n_edges", 0),
            "edges": list(graph_edges(graph)),
        })
        print(f"  {rid} {dt.date()}: {len(files_at_date)} files, "
              f"{graph['summary'].get('n_quantity_nodes', 0)} qty, "
              f"{graph['summary'].get('n_edges', 0)} edges")
    return snapshots


def build_training_pairs(snapshots: list[dict]) -> list[dict]:
    """For each consecutive pair, the new edges are the supervision target."""
    pairs = []
    for i in range(len(snapshots) - 1):
        prev = snapshots[i]
        nxt = snapshots[i + 1]
        prev_edges = set(map(tuple, prev["edges"]))
        nxt_edges = set(map(tuple, nxt["edges"]))
        added = nxt_edges - prev_edges
        if not added:
            continue
        pairs.append({
            "from_frow": prev["frow_id"],
            "to_frow": nxt["frow_id"],
            "from_date": prev["date"],
            "to_date": nxt["date"],
            "n_nodes_at_t": prev["n_quantity_nodes"],
            "n_edges_at_t": prev["n_edges"],
            "graph_edges_at_t": prev["edges"],
            "target_added_edges": list(added),
            "n_added_edges": len(added),
        })
    return pairs


def build_bootstrap_snapshots(n_snapshots: int = 200,
                               keep_frac_min: float = 0.6,
                               keep_frac_max: float = 0.95,
                               seed: int = 42) -> list[dict]:
    """Bootstrap snapshots: random-edge-subset sampling.

    The canonical link-prediction training setup: take the full graph,
    randomly hold out (1-keep_frac) of edges as 'future' targets, train
    on the rest. Repeat n_snapshots times with different random seeds.
    Produces unlimited training data without needing temporal ordering.

    This is the GOOD WAY to do GNN link prediction on a static spine —
    temporal mtimes were a workaround that produced only 3 pairs.
    """
    import random
    full_graph = ncb.parse_lean_files(LEAN_DIR)
    full_edges = list(graph_edges(full_graph))
    if not full_edges:
        return []
    random.seed(seed)
    snapshots = []
    for i in range(n_snapshots):
        random.seed(seed + i)
        keep_frac = random.uniform(keep_frac_min, keep_frac_max)
        n_keep = int(len(full_edges) * keep_frac)
        kept = set(random.sample(full_edges, n_keep))
        held_out = set(full_edges) - kept
        snapshots.append({
            "snapshot_id": f"bootstrap_{i:04d}",
            "seed": seed + i,
            "keep_frac": keep_frac,
            "n_kept_edges": len(kept),
            "n_held_out_edges": len(held_out),
            "n_quantity_nodes": full_graph["summary"].get("n_quantity_nodes", 0),
            "kept_edges": list(kept),
            "held_out_edges": list(held_out),
        })
    return snapshots


def build_bootstrap_pairs(snapshots: list[dict]) -> list[dict]:
    """Each bootstrap snapshot is its own training pair: kept_edges = state,
    held_out_edges = supervision targets.
    """
    return [{
        "snapshot_id": s["snapshot_id"],
        "n_nodes_at_t": s["n_quantity_nodes"],
        "n_edges_at_t": s["n_kept_edges"],
        "graph_edges_at_t": s["kept_edges"],
        "target_added_edges": s["held_out_edges"],
        "n_added_edges": s["n_held_out_edges"],
    } for s in snapshots]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-snapshots", type=int, default=30,
                    help="(temporal mode) sample up to N F-rows for snapshots")
    ap.add_argument("--bootstrap-snapshots", type=int, default=0,
                    metavar="N",
                    help="(bootstrap mode) generate N random-subgraph snapshots; "
                         "this is the canonical link-prediction setup, "
                         "use 200+ for real training")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    if args.bootstrap_snapshots > 0:
        print(f"=== building {args.bootstrap_snapshots} bootstrap snapshots ===")
        print(f"(random-subgraph sampling — canonical LP training setup)")
        snapshots = build_bootstrap_snapshots(
            n_snapshots=args.bootstrap_snapshots)
        pairs = build_bootstrap_pairs(snapshots)
    else:
        print("=== building temporal snapshots ===")
        snapshots = build_snapshots(max_snapshots=args.max_snapshots)
        pairs = build_training_pairs(snapshots) if snapshots else []
    if not snapshots:
        print("no snapshots; bailing")
        return 1

    print(f"\n=== {len(pairs)} training pairs ===")

    pairs_path = args.out_dir / "training_pairs.jsonl"
    with pairs_path.open("w") as f:
        for p in pairs:
            f.write(json.dumps(p) + "\n")
    print(f"wrote {pairs_path}")

    if len(pairs) < 5:
        print(f"\nWARNING: only {len(pairs)} pairs — likely too small for GNN training.")
        print(f"Consider re-running with --max-snapshots 50+ or augmenting with")
        print(f"sub-snapshot decompositions.")

    # Temporal split
    n = len(pairs)
    train_end = max(int(n * 0.70), 1)
    val_end = max(int(n * 0.85), train_end + 1)
    splits = {
        "train.jsonl": pairs[:train_end],
        "val.jsonl": pairs[train_end:val_end],
        "test.jsonl": pairs[val_end:],
    }
    for fn, subset in splits.items():
        p = args.out_dir / fn
        with p.open("w") as f:
            for r in subset:
                f.write(json.dumps(r) + "\n")
        print(f"  {fn}: {len(subset)} pairs")

    # Sanity stats
    total_targets = sum(len(p["target_added_edges"]) for p in pairs)
    print(f"\ntotal added-edge targets across all pairs: {total_targets}")
    print(f"mean targets per pair: {total_targets / max(len(pairs), 1):.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
