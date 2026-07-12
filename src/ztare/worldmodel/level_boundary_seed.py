"""Replayable level-boundary seed receipts.

A boundary seed is evidence for a transfer probe: a from-reset action sequence
that reaches a known boundary. Probe/harvest receipts must bind the exact seed
bytes, otherwise the follow-up cannot be regenerated after scratch cleanup.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sequence_from_seed(seed: dict[str, Any]) -> list[int]:
    seq = seed.get("full_sequence_from_reset") or seed.get("action_sequence") or seed.get("sequence")
    if not isinstance(seq, list) or not all(isinstance(a, int) for a in seq):
        raise RuntimeError(
            "seed must contain full_sequence_from_reset/action_sequence/sequence as list[int]"
        )
    return [int(a) for a in seq]


def load_seed(seed_path: str | Path) -> tuple[dict[str, Any], list[int], bytes, str]:
    path = Path(seed_path)
    raw = path.read_bytes()
    seed = json.loads(raw.decode("utf-8"))
    if not isinstance(seed, dict):
        raise RuntimeError("seed must be a JSON object")
    sequence = sequence_from_seed(seed)
    return seed, sequence, raw, hashlib.sha256(raw).hexdigest()


def snapshot_seed(project: str | Path, raw_seed: bytes, seed_sha256: str) -> str:
    root = Path(project)
    rel = Path("workspace") / "level_boundary_seeds" / f"{seed_sha256}.json"
    dst = root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists() or dst.read_bytes() != raw_seed:
        dst.write_bytes(raw_seed)
    return rel.as_posix()


def seed_receipt_fields(
    *,
    project: str | Path,
    seed_path: str | Path,
    raw_seed: bytes,
    seed_sha256: str,
) -> dict[str, Any]:
    return {
        "seed_path": str(seed_path),
        "seed_sha256": seed_sha256,
        "seed_snapshot_ref": snapshot_seed(project, raw_seed, seed_sha256),
    }
