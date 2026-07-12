#!/usr/bin/env python3
"""Harvest post-boundary ARC-AGI-3 transitions from a replayable seed.

This is an evidence move, not a model patch: replay a known sequence to a
level boundary, branch over actions for a bounded local depth, and persist the
observed transitions as a normal EpisodeLog plus a receipt that records branch
provenance. The same script applies to any ARC game/seed pair.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from ztare.substrates.arc_agi3 import ArcAgi3Adapter, list_games  # noqa: E402
from ztare.worldmodel.episode_log import EpisodeLog  # noqa: E402
from ztare.worldmodel.level_boundary_seed import (  # noqa: E402
    load_seed,
    seed_receipt_fields,
)


def _resolve_game_id(game: str) -> str | None:
    game = str(game or "").strip()
    if "-" in game:
        return game
    return next((g for g in list_games() if g.startswith(game)), None)


def _sequence_from_seed(seed: dict[str, Any]) -> list[int]:
    seq = seed.get("full_sequence_from_reset") or seed.get("action_sequence") or seed.get("sequence")
    if not isinstance(seq, list) or not all(isinstance(a, int) for a in seq):
        raise RuntimeError("seed must contain full_sequence_from_reset/action_sequence/sequence as list[int]")
    return [int(a) for a in seq]


def harvest(game: str, seed_path: Path, post_depth: int, episode: int, out_dir: Path) -> dict[str, Any]:
    game_id = _resolve_game_id(game)
    if game_id is None:
        raise RuntimeError(f"game {game!r} not found")
    _seed, sequence, raw_seed, seed_sha256 = load_seed(seed_path)
    action_arity = ArcAgi3Adapter(game_id).action_arity
    depth = max(1, int(post_depth))
    log = EpisodeLog()
    branches = []

    for initial_action in range(action_arity):
        adapter = ArcAgi3Adapter(game_id)
        adapter.reset()
        levels_before = int(getattr(adapter, "levels_completed", 0) or 0)
        for action in sequence:
            adapter.step(action)
        boundary_t = int(getattr(adapter, "t", 0))
        boundary_levels = int(getattr(adapter, "levels_completed", 0) or 0)
        row_start = len(log)
        trace = []
        for post_step in range(1, depth + 1):
            action = (initial_action + post_step - 1) % action_arity
            before = adapter.state
            t = int(getattr(adapter, "t", len(log)))
            observed = adapter.step(action)
            log.append(before, action, observed, t=t)
            trace.append({
                "post_step": post_step,
                "action": action,
                "t": t,
                "levels_after": int(getattr(adapter, "levels_completed", 0) or 0),
                "state": str(getattr(adapter, "state_name", getattr(adapter, "state", "")))[:80],
            })
        branches.append({
            "initial_action": initial_action,
            "row_start": row_start,
            "row_end_exclusive": len(log),
            "levels_before_replay": levels_before,
            "levels_at_boundary": boundary_levels,
            "boundary_t": boundary_t,
            "trace": trace,
        })

    episode_path = out_dir / "raw" / "episodes" / f"episode_{int(episode):03d}.jsonl"
    log.write_jsonl(episode_path)
    receipt = {
        "schema": "ztare-arc3-level-boundary-harvest-v1",
        "game": game_id,
        **seed_receipt_fields(
            project=out_dir,
            seed_path=seed_path,
            raw_seed=raw_seed,
            seed_sha256=seed_sha256,
        ),
        "replay_sequence_len": len(sequence),
        "post_depth": depth,
        "action_arity": action_arity,
        "episode_path": str(episode_path),
        "transitions": len(log),
        "content_hash": log.content_hash(),
        "branches": branches,
        "authority": "observed transitions only; no model adoption or solve claim",
    }
    receipt_path = out_dir / "workspace" / f"level_boundary_harvest_episode_{int(episode):03d}.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True)
    ap.add_argument("--project", default=None)
    ap.add_argument("--seed-path", required=True)
    ap.add_argument("--post-depth", type=int, default=4)
    ap.add_argument("--episode", type=int, default=2)
    args = ap.parse_args(argv)
    project = Path(args.project) if args.project else REPO / "projects" / f"arc3_{args.game}_gov"
    receipt = harvest(args.game, Path(args.seed_path), args.post_depth, args.episode, project)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
