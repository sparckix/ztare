"""Dispatcher-shaped wrappers over the world-model gates (GP-250 P1).

The kernel gate dispatcher calls `run(substrate, candidate)`; these wrappers
adapt that contract onto the pure gates in `ztare.worldmodel.gates`, which
read only the episode log. Registered in `gates/registry.py` for
`substrate.meta['class'] == "interactive_environment"` via `_engages_on`.

Contract:
- the substrate's meta (or the project layout) names the episode log:
  `meta["episode_log_path"]`, else `<project_dir>/raw/episodes/episode_001.jsonl`;
  a held-out log may be named as `meta["holdout_log_path"]`.
- the candidate carries a transition program under `transition_program`
  (a `grid_dsl` frozen AST, JSON-decoded lists are normalized to tuples).

Fail-closed throughout: a missing log, missing program, or undefined
evaluation is a gate failure with a named reason, never a silent pass.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.gates import replay_consistency_gate, rollout_diagnostics, rollout_depth

DEFAULT_MIN_ROLLOUT_DEPTH = 10


def _to_program(node: Any) -> tuple:
    """Normalize a JSON-decoded AST (lists) back to the frozen tuple form."""
    if isinstance(node, list):
        return tuple(_to_program(child) for child in node)
    if isinstance(node, tuple):
        return tuple(_to_program(child) for child in node)
    return node


def _resolve(substrate: Any, candidate: Any) -> "tuple[tuple | None, EpisodeLog | None, EpisodeLog | None, str]":
    meta = getattr(substrate, "meta", None) or {}
    program = None
    if isinstance(candidate, dict):
        program = candidate.get("transition_program")
    if program is None:
        return None, None, None, "candidate carries no transition_program"
    program = _to_program(program)

    project_dir = meta.get("project_dir") or getattr(substrate, "project_dir", None)
    log_path = meta.get("episode_log_path")
    if log_path is None and project_dir is not None:
        log_path = Path(project_dir) / "raw" / "episodes" / "episode_001.jsonl"
    if log_path is None or not Path(log_path).exists():
        return program, None, None, f"episode log not found: {log_path}"
    log = EpisodeLog.read_jsonl(log_path)

    holdout = None
    holdout_path = meta.get("holdout_log_path")
    if holdout_path and Path(holdout_path).exists():
        holdout = EpisodeLog.read_jsonl(holdout_path)
    return program, log, holdout, ""


def run_replay_gate(substrate: Any, candidate: Any) -> dict:
    program, log, _holdout, err = _resolve(substrate, candidate)
    if err:
        return {"gate": "worldmodel_replay", "ok": False, "detail": err}
    result = replay_consistency_gate(program, log)
    return {"gate": "worldmodel_replay", "ok": result.ok, "detail": result.detail,
            "evidence_hash": log.content_hash()}


def run_rollout_gate(substrate: Any, candidate: Any) -> dict:
    program, log, holdout, err = _resolve(substrate, candidate)
    if err:
        return {"gate": "worldmodel_rollout", "ok": False, "detail": err}
    if holdout is None:
        return {"gate": "worldmodel_rollout", "ok": False,
                "detail": "no held-out episode named (meta.holdout_log_path); rollout depth unmeasurable"}
    meta = getattr(substrate, "meta", None) or {}
    min_depth = int(meta.get("min_rollout_depth", DEFAULT_MIN_ROLLOUT_DEPTH))
    diagnostics = rollout_diagnostics(program, holdout)
    depth = int(diagnostics.get("rollout_depth") or 0)
    ok = depth >= min_depth
    payload = {
        "gate": "worldmodel_rollout",
        "ok": ok,
        "rollout_depth": depth,
        "min_rollout_depth": min_depth,
        "detail": f"rollout depth {depth} over {len(holdout)} held-out steps (required {min_depth})",
    }
    if not ok and diagnostics.get("holdout_witness"):
        payload["holdout_witness"] = diagnostics["holdout_witness"]
    return payload
