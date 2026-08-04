"""Per-carrier row-correctness bitmaps over episode logs (membrane compression).

Design contract (never-delete-the-fiber):
  Raw evidence stays where it is — the existing episode JSONL files are the
  cold tier, content-addressed. This module builds a VIEW over them: for each
  carrier × episode pair, a compact per-transition correctness record. The
  bitmap IS the compression: a champion that predicts row i exactly "explains"
  that row — the champion IS the colimit. Only the residual (wrong rows) needs
  further explanation.

Reconsolidation phase:
  Bitmaps are keyed by (carrier_sha256, episode_content_hash,
  evaluator_sha256, lowering_config_sha256). Any evidence
  append changes episode_content_hash → new key → automatic recompute on next
  call. A champion swap changes carrier_sha256 → new key → automatic recompute.
  A gate, transition-identity, or bitmap implementation change alters the
  evaluator digest and cannot reuse a judgment made under old semantics.
  Neither operation requires explicit invalidation: content addressing makes
  reconsolidation fall out of cache lookup. This is the "pull raw back, recompute
  quotient" reconsolidation phase: the bitmap files are ephemeral projections of
  the cold-tier JSONL evidence; deleting workspace/row_bitmaps/ is always safe.

Schema: workspace/row_bitmaps/<carrier>_<episode>_<evaluator>_<config>.json
  {
    "schema": "ztare-row-bitmap-v1",
    "carrier_sha256": str,          # sha256 of carrier source text
    "episode_hash": str,            # EpisodeLog.content_hash()
    "evaluator_sha256": str,        # code identity of bitmap/gate semantics
    "lowering_config_sha256": str,  # non-code lowering-policy identity
    "episode_path": str,            # absolute path for human reference only
    "total_rows": int,
    "env_frame_indices": [int],     # rows excluded by env_frame_indices()
    "exact_count": int,             # rows where carrier predicts s_next exactly
    "wrong_rows": [int],            # row indices where prediction != s_next (not env)
    "bits": [bool]                  # per-row: True = exact match (incl. env=excluded)
  }

Usage:
  bitmap = build_row_bitmap(carrier_path, episode_path, project_dir=project_dir)
  residual = residual_view(bitmap)   # indices champion got wrong → unexplained
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from ztare.common.worldmodel_carrier_purity import project_dynamics_assumption
from ztare.worldmodel.carrier_loader import (
    load_carrier_from_source as _load_carrier_from_source,
)
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.gates import (
    as_predictor,
    env_frame_indices,
    evaluator_implementation_identity,
)


_ROW_BITMAP_EVALUATOR_SHA256 = str(evaluator_implementation_identity()["sha256"])


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _row_bitmap_evaluator_sha256() -> str:
    """Identity of the evaluator implementation loaded into this process."""

    return _ROW_BITMAP_EVALUATOR_SHA256


def _row_bitmap_config_sha256(project_dir: Path) -> str:
    """Identity of lowering inputs not carried by candidate or evaluator bytes."""

    payload = {
        "dynamics_assumption_env": os.environ.get("ZTARE_DYNAMICS_ASSUMPTION"),
        "dynamics_assumption_project": project_dynamics_assumption(project_dir),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def resolve_episode_paths(project_dir: "str | Path") -> "dict[str, Path | None]":
    """Return {"visible": Path|None, "holdout": Path|None} for a project.

    Resolution order:
      (a) MANIFEST.json: episode_roles.visible / episode_roles.holdout
          OR top-level visible_episode / holdout_episode keys.
      (b) rubrics/<project_name>.json: same key names.
      (c) Fallback convention (legacy): sorted raw/episodes/*.jsonl —
          first file is visible, second is holdout.  This matches the
          original episode_001/episode_002 layout.
    Returns None for any role that cannot be resolved.
    """
    project_dir = Path(project_dir).resolve()
    repo = project_dir.parents[1]

    def _path_or_none(raw: "str | None", base: Path) -> "Path | None":
        if not raw:
            return None
        p = Path(raw)
        if not p.is_absolute():
            p = base / p
        return p if p.exists() else None

    # (a) MANIFEST.json
    manifest = project_dir / "MANIFEST.json"
    if manifest.exists():
        try:
            m = json.loads(manifest.read_text())
        except (OSError, ValueError, TypeError) as exc:
            raise ValueError(f"unreadable episode-role manifest: {manifest}") from exc
        roles = m.get("episode_roles") or {}
        has_role_declaration = bool(
            roles.get("visible")
            or roles.get("holdout")
            or m.get("visible_episode")
            or m.get("holdout_episode")
        )
        if has_role_declaration:
            vis = _path_or_none(
                roles.get("visible") or m.get("visible_episode"), project_dir
            )
            hld = _path_or_none(
                roles.get("holdout") or m.get("holdout_episode"), project_dir
            )
            if vis is not None or hld is not None:
                return {"visible": vis, "holdout": hld}
            raise ValueError(
                f"episode-role manifest names no existing evidence: {manifest}"
            )

    # (b) rubric json
    rubric = repo / "rubrics" / f"{project_dir.name}.json"
    if rubric.exists():
        try:
            r = json.loads(rubric.read_text())
            roles = r.get("episode_roles") or {}
            vis = _path_or_none(roles.get("visible") or r.get("visible_episode"), project_dir)
            hld = _path_or_none(roles.get("holdout") or r.get("holdout_episode"), project_dir)
            if vis is not None or hld is not None:
                return {"visible": vis, "holdout": hld}
        except Exception:  # noqa: BLE001
            pass

    # (c) fallback convention: sorted raw/episodes/*.jsonl
    ep_dir = project_dir / "raw" / "episodes"
    eps = sorted(ep_dir.glob("*.jsonl")) if ep_dir.is_dir() else []
    return {
        "visible": eps[0] if len(eps) >= 1 else None,
        "holdout": eps[1] if len(eps) >= 2 else None,
    }


def build_row_bitmap(
    carrier_path: "str | Path",
    episode_path: "str | Path",
    *,
    project_dir: "str | Path | None" = None,
    persist_dir: "str | Path | None" = None,
) -> dict:
    """Build (and optionally persist) a per-row correctness bitmap.

    Parameters
    ----------
    carrier_path:
        Path to the candidate .py file.
    episode_path:
        Path to the episode JSONL (e.g. episode_001.jsonl).
    project_dir:
        Project root for PATCH_BASE resolution and rubric lookup. Inferred
        from carrier_path parent hierarchy if omitted.
    persist_dir:
        Directory to write the bitmap JSON. Defaults to
        <project_dir>/workspace/row_bitmaps/. Pass None to skip persistence.

    Returns the bitmap dict (same schema as the persisted JSON).
    """
    carrier_path = Path(carrier_path).resolve()
    episode_path = Path(episode_path).resolve()

    if project_dir is None:
        # Heuristic: walk up until we find a gate_harness.py or MANIFEST.json
        p = carrier_path.parent
        while p != p.parent:
            if (p / "gate_harness.py").exists() or (p / "MANIFEST.json").exists():
                project_dir = p
                break
            p = p.parent
        if project_dir is None:
            project_dir = carrier_path.parent
    project_dir = Path(project_dir).resolve()

    source = carrier_path.read_text()
    carrier_sha = _sha256_text(source)

    log = EpisodeLog.read_jsonl(episode_path)
    episode_hash = log.content_hash()
    evaluator_sha = _row_bitmap_evaluator_sha256()
    config_sha = _row_bitmap_config_sha256(project_dir)

    # Check cache first
    bitmap_file = None
    if persist_dir is not False:
        _persist_dir = Path(persist_dir) if persist_dir else (project_dir / "workspace" / "row_bitmaps")
        _persist_dir.mkdir(parents=True, exist_ok=True)
        bitmap_file = _persist_dir / (
            f"{carrier_sha[:16]}_{episode_hash[:16]}_{evaluator_sha[:16]}_"
            f"{config_sha[:16]}.json"
        )
        if bitmap_file.exists():
            try:
                cached = json.loads(bitmap_file.read_text())
                if (
                    cached.get("schema") == "ztare-row-bitmap-v1"
                    and cached.get("carrier_sha256") == carrier_sha
                    and cached.get("episode_hash") == episode_hash
                    and cached.get("evaluator_sha256") == evaluator_sha
                    and cached.get("lowering_config_sha256") == config_sha
                    and not cached.get("load_error")
                ):
                    return cached
            except Exception:  # noqa: BLE001
                pass  # recompute on corrupt cache

    try:
        program = _load_carrier_from_source(
            source,
            str(carrier_path),
            project_dir,
            attach_projection=False,
        )
        load_err = None
    except Exception as exc:  # noqa: BLE001
        load_err = str(exc)[:200]
        program = None

    rows = list(log)
    env_idx = env_frame_indices(log) if program is not None else set()

    bits: list[bool] = []
    wrong_rows: list[int] = []
    exact_count = 0

    if program is not None:
        from ztare.worldmodel.gates import _memoized_predictor
        predict = _memoized_predictor(as_predictor(program))
        for i, tr in enumerate(rows):
            if i in env_idx:
                bits.append(True)  # env frames are excluded, not wrong
                continue
            predicted = predict(tr.s, tr.a, tr.t)
            ok = predicted is not None and predicted == tr.s_next
            bits.append(ok)
            if ok:
                exact_count += 1
            else:
                wrong_rows.append(i)
    else:
        bits = [False] * len(rows)
        wrong_rows = list(range(len(rows)))

    bitmap = {
        "schema": "ztare-row-bitmap-v1",
        "carrier_sha256": carrier_sha,
        "episode_hash": episode_hash,
        "evaluator_sha256": evaluator_sha,
        "lowering_config_sha256": config_sha,
        "episode_path": str(episode_path),
        "total_rows": len(rows),
        "env_frame_indices": sorted(env_idx),
        "exact_count": exact_count,
        "wrong_rows": wrong_rows,
        "bits": bits,
    }
    if load_err:
        bitmap["load_error"] = load_err

    if bitmap_file is not None and load_err is None:
        try:
            bitmap_file.write_text(json.dumps(bitmap))
        except Exception:  # noqa: BLE001
            pass  # persistence is best-effort; the in-memory bitmap is the truth

    return bitmap


def residual_view(bitmap: dict) -> list[int]:
    """Return the residual row indices: rows the champion predicted wrong.

    These are the 'unexplained episodic residue' — the rows the champion
    (as colimit) does NOT compress. They are the only rows where a new carrier
    can offer an improvement; explained rows are covered by the champion.

    Env-frame rows are excluded from wrong_rows by build_row_bitmap (they are
    excluded from replay, so they are neither explained nor unexplained — they
    are outside the physics the gate can evaluate).
    """
    return list(bitmap.get("wrong_rows", []))


if __name__ == "__main__":
    # ponytail: minimal self-check — fails if the bitmap logic breaks
    import tempfile, os
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.grid_dsl import Grid

    # Build a tiny synthetic episode: identity law s_next = s
    g1: Grid = ((1, 2), (3, 4))
    g2: Grid = ((2, 2), (3, 4))
    log = EpisodeLog()
    log.append(g1, 0, g1, t=0)   # exact: identity predicts s_next=s correctly
    log.append(g2, 1, g1, t=1)   # wrong: identity predicts g2, but s_next=g1

    with tempfile.TemporaryDirectory() as td:
        ep_path = os.path.join(td, "ep.jsonl")
        log.write_jsonl(ep_path)

        # Write a carrier that is identity (returns s unchanged)
        carrier_src = "def step(s, a, t):\n    return s\n"
        carrier_path = os.path.join(td, "identity.py")
        with open(carrier_path, "w") as f:
            f.write(carrier_src)

        bitmap = build_row_bitmap(carrier_path, ep_path, persist_dir=td)
        assert bitmap["total_rows"] == 2, f"expected 2 rows, got {bitmap['total_rows']}"
        assert bitmap["exact_count"] == 1, f"expected 1 exact, got {bitmap['exact_count']}"
        assert bitmap["wrong_rows"] == [1], f"expected wrong=[1], got {bitmap['wrong_rows']}"

        residual = residual_view(bitmap)
        assert residual == [1], f"residual mismatch: {residual}"

        # Test cache hit: second call should return from disk without recompute
        bitmap2 = build_row_bitmap(carrier_path, ep_path, persist_dir=td)
        assert bitmap2["exact_count"] == bitmap["exact_count"], "cache returned different result"

        # Test reconsolidation: append a row → new episode hash → different cache file
        log.append(g1, 2, g1, t=2)
        ep_path2 = os.path.join(td, "ep2.jsonl")
        log.write_jsonl(ep_path2)
        bitmap3 = build_row_bitmap(carrier_path, ep_path2, persist_dir=td)
        assert bitmap3["total_rows"] == 3, "reconsolidation: should recompute for new episode"
        assert bitmap3["episode_hash"] != bitmap["episode_hash"], "new hash for appended episode"

    print("evidence_consolidation: all self-checks PASSED")
