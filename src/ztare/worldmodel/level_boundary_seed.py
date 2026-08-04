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


def _replay_latest_seed(
    project: str | Path,
    adapter,
    *,
    capture_transitions: bool,
) -> tuple[dict[str, Any], tuple[Any, ...]]:
    """Replay the deepest stored boundary and optionally retain its trace."""
    root = Path(project)
    path = root / "workspace" / "latest_level_boundary_seed.json"
    if not path.is_file():
        return {
            "schema": "ztare-level-boundary-seed-replay-v1",
            "status": "no_seed",
            "actions": [],
            "observed_epoch": int(getattr(adapter, "levels_completed", 0) or 0),
        }, ()
    transitions: list[Any] = []
    try:
        seed, sequence, _raw, seed_sha256 = load_seed(path)
        declared_epoch = int(seed.get("completed_level"))
        if declared_epoch < 1:
            raise ValueError("completed_level must be positive")
        for action in sequence:
            if action < 0 or action >= int(getattr(adapter, "action_arity", 0) or 0):
                raise ValueError(f"seed intervention outside adapter domain: {action}")
            if capture_transitions:
                from ztare.worldmodel.episode_log import Transition
                from ztare.worldmodel.transition_identity import (
                    TransitionIdentity,
                )

                source = adapter.state
                time_value = int(getattr(adapter, "t", 0) or 0)
                successor = adapter.step(action)
                identity = getattr(adapter, "last_transition_identity", None)
                transitions.append(Transition(
                    t=time_value,
                    s=source,
                    a=action,
                    s_next=successor,
                    identity=(
                        identity
                        if isinstance(identity, TransitionIdentity)
                        else None
                    ),
                ))
            else:
                adapter.step(action)
        observed_epoch = int(getattr(adapter, "levels_completed", 0) or 0)
        status = "verified" if observed_epoch == declared_epoch else "epoch_mismatch"
        if status != "verified":
            adapter.reset()
            transitions = []
        segments = seed.get("execution_segments")
        if not isinstance(segments, list) or not segments:
            segments = [{
                "segment_id": "legacy-origin",
                "segment_kind": "verified_origin",
                "source_ref": "workspace/latest_level_boundary_seed.json",
                "authority": "environment_verified_replay",
                "start_index": 0,
                "end_index_exclusive": len(sequence),
                "actions": sequence,
            }]
        receipt = {
            "schema": "ztare-level-boundary-seed-replay-v1",
            "status": status,
            "seed_ref": "workspace/latest_level_boundary_seed.json",
            "seed_sha256": seed_sha256,
            "declared_epoch": declared_epoch,
            "observed_epoch": observed_epoch,
            "active_epoch": int(getattr(adapter, "levels_completed", 0) or 0),
            "actions": sequence if status == "verified" else [],
            "execution_segments": segments if status == "verified" else [],
            "interventions_executed": len(sequence),
        }
    except Exception as exc:  # noqa: BLE001
        transitions = []
        try:
            adapter.reset()
        except Exception:  # noqa: BLE001
            pass
        receipt = {
            "schema": "ztare-level-boundary-seed-replay-v1",
            "status": "invalid_or_unreplayable",
            "seed_ref": "workspace/latest_level_boundary_seed.json",
            "observed_epoch": int(getattr(adapter, "levels_completed", 0) or 0),
            "active_epoch": int(getattr(adapter, "levels_completed", 0) or 0),
            "actions": [],
            "execution_segments": [],
            "error": f"{type(exc).__name__}: {exc}",
        }
    ledger = root / "workspace" / "level_boundary_seed_replays.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, sort_keys=True) + "\n")
    return receipt, tuple(transitions)


def replay_latest_seed(project: str | Path, adapter) -> dict[str, Any]:
    """Replay the deepest stored boundary and trust only the observed epoch."""
    receipt, _transitions = _replay_latest_seed(
        project,
        adapter,
        capture_transitions=False,
    )
    return receipt


def replay_latest_seed_trace(
    project: str | Path,
    adapter,
) -> tuple[dict[str, Any], tuple[Any, ...]]:
    """Replay a seed and return its ordered observed transition section."""
    return _replay_latest_seed(
        project,
        adapter,
        capture_transitions=True,
    )
