"""WorldmodelAdapter: exposes ls20/ARC-3 grid observations to the causal compiler.

Implements CausalAdapter for the worldmodel substrate:
  objects()     — connected components per color per frame (flood-fill, capped)
  transitions() — episode rows via EpisodeLog + resolve_episode_paths, with
                  summary features derived from grid census + region occupancy
  collisions()  — identical-(t, a) groups on the visible episode (cheap hash pass)

Variables this adapter realizes for v1:
  - component_count_<color>: number of connected components of that color
  - bbox_row_<color>: bucketed top-row of first component of that color
  - bbox_col_<color>: bucketed left-col of first component of that color
  - census_<color>: total cell count of that color in the grid
  - timer_band_occupancy: count of color-11 cells in receipt-known timer band
    rows 61-62 (evidence_ref: projects/arc3_ls20_gov/workspace/latest_level_transfer_probe.json)
  - slab_band_occupancy: count of color-11 cells in rows 16-18
    (evidence_ref: projects/arc3_ls20_gov/workspace/latest_level_transfer_probe.json —
    second residue class, rows 16-18)

All variables are receipt-derived where possible; coordinates come from
projects/arc3_ls20_gov/workspace/latest_level_transfer_probe.json and
projects/arc3_ls20_gov/workspace/spec_receipts.jsonl.

Flood-fill cap: MAX_OBJECTS_PER_COLOR = 64 components per color per frame to
bound cost on large (64x64) grids with many cells of one color.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.evidence_consolidation import resolve_episode_paths
from ztare.worldmodel.grid_dsl import Grid

# Background color in ls20 grid — wall/empty
_BG_COLOR = 4

# Only track these colors (from spec_receipts + observed census)
# ponytail: hardcoded to ls20 colors; adapter is already substrate-specific
_TRACKED_COLORS = (0, 1, 3, 5, 8, 9, 11, 12)

# Flood-fill cap: stop after this many components per color per frame
MAX_OBJECTS_PER_COLOR = 64

# Receipt-derived band coordinates (from latest_level_transfer_probe.json)
# local_residue_quotient class before=11: rows [61, 62], action-independent
_TIMER_BAND_ROWS = (61, 62)
# Second residue class before=11: rows [16, 17, 18]
_SLAB_BAND_ROWS = (16, 17, 18)
_BAND_COLOR = 11  # TICK color

# Bucket size for bbox coordinates (reduces cardinality)
_BBOX_BUCKET = 8

_EVIDENCE_REFS_BAND = [
    "projects/arc3_ls20_gov/workspace/latest_level_transfer_probe.json",
]
_EVIDENCE_REFS_SPEC = [
    "projects/arc3_ls20_gov/workspace/spec_receipts.jsonl",
]


# ---------------------------------------------------------------------------
# Flood-fill (4-connected, iterative to avoid recursion limit)
# ---------------------------------------------------------------------------

def _flood_fill_components(grid: Grid, color: int) -> "list[list[tuple[int, int]]]":
    """Return connected components of `color` in `grid` (4-connected).

    Caps at MAX_OBJECTS_PER_COLOR components.
    """
    h, w = len(grid), len(grid[0])
    visited: set[tuple[int, int]] = set()
    components: list[list[tuple[int, int]]] = []

    for r0 in range(h):
        for c0 in range(w):
            if grid[r0][c0] != color or (r0, c0) in visited:
                continue
            if len(components) >= MAX_OBJECTS_PER_COLOR:
                break
            # BFS
            component: list[tuple[int, int]] = []
            stack = [(r0, c0)]
            while stack:
                r, c = stack.pop()
                if (r, c) in visited:
                    continue
                visited.add((r, c))
                component.append((r, c))
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == color and (nr, nc) not in visited:
                        stack.append((nr, nc))
            components.append(component)
        if len(components) >= MAX_OBJECTS_PER_COLOR:
            break

    return components


def _grid_features(grid: Grid, frame_id: int) -> "tuple[dict[str, Any], list[dict[str, Any]]]":
    """Extract (features_dict, object_descriptors) from one grid frame.

    features_dict: keyed by variable name, values are ints/floats
    object_descriptors: list of {frame_id, object_id, features}
    """
    h, w = len(grid), len(grid[0])
    features: dict[str, Any] = {}
    objects: list[dict] = []

    # Census per color
    census: dict[int, int] = defaultdict(int)
    for row in grid:
        for v in row:
            census[v] += 1

    for color in _TRACKED_COLORS:
        cnt = census.get(color, 0)
        features[f"census_{color}"] = cnt

        # Connected components
        comps = _flood_fill_components(grid, color)
        features[f"component_count_{color}"] = len(comps)

        # Bbox of first component (bucketed)
        if comps:
            rows_c = [r for r, c in comps[0]]
            cols_c = [c for r, c in comps[0]]
            features[f"bbox_row_{color}"] = min(rows_c) // _BBOX_BUCKET
            features[f"bbox_col_{color}"] = min(cols_c) // _BBOX_BUCKET
        else:
            features[f"bbox_row_{color}"] = -1
            features[f"bbox_col_{color}"] = -1

        for i, comp in enumerate(comps):
            objects.append({
                "frame_id": frame_id,
                "object_id": f"color{color}_comp{i}",
                "features": {
                    "color": color,
                    "size": len(comp),
                    "min_row": min(r for r, c in comp),
                    "min_col": min(c for r, c in comp),
                },
            })

    # Receipt-derived region occupancy
    # Timer band: rows 61-62, color 11
    if h > max(_TIMER_BAND_ROWS):
        timer_count = sum(
            1 for r in _TIMER_BAND_ROWS for c in range(w)
            if grid[r][c] == _BAND_COLOR
        )
        features["timer_band_occupancy"] = timer_count
    else:
        features["timer_band_occupancy"] = None  # grid too small

    # Slab band: rows 16-18, color 11
    if h > max(_SLAB_BAND_ROWS):
        slab_count = sum(
            1 for r in _SLAB_BAND_ROWS for c in range(w)
            if grid[r][c] == _BAND_COLOR
        )
        features["slab_band_occupancy"] = slab_count
    else:
        features["slab_band_occupancy"] = None

    return features, objects


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class WorldmodelAdapter:
    """CausalAdapter over the worldmodel episode logs for a project.

    Reads the visible episode log (episode_001.jsonl) and, if present,
    the holdout log (episode_002.jsonl). Transitions include features
    extracted from both s and s_next grids.
    """

    def __init__(self, project_dir: "Path | str") -> None:
        self._project_dir = Path(project_dir).resolve()
        self._episode_paths = resolve_episode_paths(self._project_dir)
        self._transitions_cache: "list[dict] | None" = None
        self._objects_cache: "list[dict] | None" = None

    def _load_episode(self, role: str) -> "EpisodeLog | None":
        path = self._episode_paths.get(role)
        if path is None or not path.exists():
            return None
        return EpisodeLog.read_jsonl(path)

    def objects(self) -> "list[dict[str, Any]]":
        if self._objects_cache is not None:
            return self._objects_cache
        result: list[dict] = []
        frame_id = 0
        for role in ("visible", "holdout"):
            log = self._load_episode(role)
            if log is None:
                continue
            for tr in log:
                _, obs = _grid_features(tr.s, frame_id)
                result.extend(obs)
                frame_id += 1
        self._objects_cache = result
        return result

    def transitions(self) -> "list[dict[str, Any]]":
        if self._transitions_cache is not None:
            return self._transitions_cache

        result: list[dict] = []
        for role in ("visible", "holdout"):
            path = self._episode_paths.get(role)
            if path is None or not path.exists():
                continue
            source_ref = f"raw/episodes/{path.name}"
            log = EpisodeLog.read_jsonl(path)

            for tr in log:
                features_before, _ = _grid_features(tr.s, tr.t)
                features_after, _ = _grid_features(tr.s_next, tr.t + 1)

                # Filter out None values from band occupancy (grid too small)
                features_before = {k: v for k, v in features_before.items() if v is not None}
                features_after = {k: v for k, v in features_after.items() if v is not None}

                result.append({
                    "t": tr.t,
                    "a": tr.a,
                    "features_before": features_before,
                    "features_after": features_after,
                    "source_ref": source_ref,
                    "evidence_refs": [source_ref] + _EVIDENCE_REFS_BAND + _EVIDENCE_REFS_SPEC,
                })

        self._transitions_cache = result
        return result

    def collisions(self) -> "list[dict[str, Any]]":
        """Identical-(t, a) groups in the visible episode.

        In a deterministic substrate this should always be empty. Non-empty
        groups indicate state aliasing or log corruption.
        """
        log = self._load_episode("visible")
        if log is None:
            return []

        groups: dict[tuple[int, int], list[str]] = defaultdict(list)
        for tr in log:
            key = (tr.t, tr.a)
            groups[key].append(f"t={tr.t},a={tr.a}")

        result = []
        for (t, a), refs in groups.items():
            if len(refs) > 1:
                result.append({
                    "group_key": f"t={t},a={a}",
                    "count": len(refs),
                    "refs": refs,
                })
        return result
