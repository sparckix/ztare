"""Compact grid codec and state interner for BFS frontier bookkeeping (GP-250).

Replaces ~94KB/state JSON rows (visited_*.jsonl) with ~1-2 bytes/cell npz.

Design:
- Grid codec: tuple-of-tuples <-> np.uint8 2D array <-> compact bytes key.
- StateInterner: bytes-key -> int-id arena plus an independent visited-id set;
  maintains a growing (N, H*W) uint8 matrix (amortized doubling) for batch ops.
- Batch novelty: vectorized hamming against visited rows only, matching
  _novelty semantics from planner.py exactly (min distance; early-exit when
  best==1; returns 0 if visited empty or grid already visited).
- Persistence: save/load via npz (~1-2 bytes/cell vs ~94KB/state JSON).

Semantic contract: batch_novelty(grid, interner) == planner._novelty(grid,
visited_set) for all inputs — proven by the 500-grid equivalence test in
tests/test_frontier_codec.py.
"""

from __future__ import annotations

import io
import struct
from pathlib import Path
from typing import Tuple

import numpy as np

# Grid is tuple[tuple[int, ...], ...]
Grid = Tuple[Tuple[int, ...], ...]


# ---------------------------------------------------------------------------
# Grid codec
# ---------------------------------------------------------------------------

def grid_to_array(grid: Grid) -> np.ndarray:
    """Convert tuple-of-tuples to np.uint8 2D array. O(H*W)."""
    return np.array(grid, dtype=np.uint8)


def array_to_grid(arr: np.ndarray) -> Grid:
    """Convert np.uint8 2D array to tuple-of-tuples. Round-trip exact."""
    return tuple(tuple(int(c) for c in row) for row in arr)


def grid_to_key(grid: Grid) -> bytes:
    """Compact bytes key: 2-byte shape header (H, W) + packed uint8 values.

    For a 64x64 grid: 2 + 4096 = 4098 bytes vs ~94KB JSON. Round-trip exact.
    """
    arr = grid_to_array(grid)
    h, w = arr.shape
    # ponytail: struct pack for shape, then raw bytes for values
    return struct.pack(">HH", h, w) + arr.tobytes()


def key_to_grid(key: bytes) -> Grid:
    """Decode bytes key back to tuple-of-tuples. Exact inverse of grid_to_key."""
    h, w = struct.unpack(">HH", key[:4])
    arr = np.frombuffer(key[4:], dtype=np.uint8).reshape(h, w)
    return array_to_grid(arr)


# ---------------------------------------------------------------------------
# StateInterner
# ---------------------------------------------------------------------------

class StateInterner:
    """Maps grids to integer IDs; maintains a flat uint8 matrix for batch ops.

    visited sets become sets[int] — membership is O(1) int comparison vs
    O(H*W) tuple hash. The flat matrix enables vectorized hamming (numpy
    broadcasting) for batch novelty scoring.

    Amortized-doubling matrix: no per-add reallocation.
    """

    def __init__(self) -> None:
        self._key_to_id: dict[bytes, int] = {}
        self._visited: set[int] = set()
        # matrix: rows = interned states, cols = flattened cells
        # _mat is over-allocated; _n is the live count
        self._mat: np.ndarray | None = None  # shape (capacity, H*W) uint8
        self._n: int = 0
        self._cell_size: int = 0  # H*W, set on first intern
        self._shapes: list[tuple[int, int]] = []  # (H, W) per state

    # ------------------------------------------------------------------
    # Core intern
    # ------------------------------------------------------------------

    def intern(self, grid: Grid) -> int:
        """Return the integer ID for `grid`, adding it if new.

        Returns existing ID without mutation if already interned. Interning is
        arena bookkeeping only; call mark_visited() after a live observation.
        """
        key = grid_to_key(grid)
        if key in self._key_to_id:
            return self._key_to_id[key]

        arr = grid_to_array(grid)
        h, w = arr.shape
        flat = arr.ravel()
        cell_size = h * w

        if self._mat is None:
            # first intern — allocate initial capacity of 64
            self._cell_size = cell_size
            capacity = 64
            self._mat = np.empty((capacity, cell_size), dtype=np.uint8)
        elif cell_size != self._cell_size:
            raise ValueError(
                f"StateInterner: mixed grid sizes not supported "
                f"(got {cell_size}, expected {self._cell_size})"
            )

        if self._n >= len(self._mat):
            # amortized double
            new_cap = max(len(self._mat) * 2, 64)
            new_mat = np.empty((new_cap, self._cell_size), dtype=np.uint8)
            new_mat[:self._n] = self._mat[:self._n]
            self._mat = new_mat

        self._mat[self._n] = flat
        new_id = self._n
        self._key_to_id[key] = new_id
        self._shapes.append((h, w))
        self._n += 1
        return new_id

    def mark_visited(self, grid: Grid) -> int:
        """Intern `grid`, mark its ID visited, and return that ID."""
        state_id = self.intern(grid)
        self._visited.add(state_id)
        return state_id

    def is_visited(self, grid: Grid) -> bool:
        """True only for a live-observed state, not a simulated arena row."""
        state_id = self._key_to_id.get(grid_to_key(grid))
        return state_id is not None and state_id in self._visited

    def __contains__(self, grid: Grid) -> bool:
        return self.is_visited(grid)

    def __len__(self) -> int:
        return len(self._visited)

    @property
    def matrix(self) -> np.ndarray:
        """Live (N, H*W) uint8 view of all interned states. No copy."""
        if self._mat is None or self._n == 0:
            return np.empty((0, 0), dtype=np.uint8)
        return self._mat[:self._n]

    @property
    def visited_matrix(self) -> np.ndarray:
        """Rows marked visited; simulated search states stay outside novelty."""
        if not self._visited:
            return np.empty((0, self._cell_size), dtype=np.uint8)
        if len(self._visited) == self._n:
            return self.matrix
        visited_ids = np.fromiter(
            self._visited, dtype=np.intp, count=len(self._visited)
        )
        return self.matrix[visited_ids]

    def get_id(self, grid: Grid) -> int | None:
        """Return ID if interned, else None."""
        return self._key_to_id.get(grid_to_key(grid))

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: "str | Path") -> None:
        """Save interner to .npz — ~1-2 bytes/cell for uint8 grids."""
        path = Path(path)
        mat = self.matrix
        keys = list(self._key_to_id.keys())
        ids = np.array([self._key_to_id[k] for k in keys], dtype=np.int32)
        # store keys as a single bytes blob with uint32 length-prefix per key
        buf = io.BytesIO()
        for k in keys:
            buf.write(struct.pack(">I", len(k)))
            buf.write(k)
        key_blob = np.frombuffer(buf.getvalue(), dtype=np.uint8)
        np.savez_compressed(
            path,
            matrix=mat,
            key_blob=key_blob,
            ids=ids,
            visited=np.array(sorted(self._visited), dtype=np.int32),
            cell_size=np.array([self._cell_size], dtype=np.int32),
            n=np.array([self._n], dtype=np.int32),
        )

    @classmethod
    def load(cls, path: "str | Path") -> "StateInterner":
        """Load interner saved by .save(). Round-trip identity guaranteed."""
        path = Path(path)
        data = np.load(path, allow_pickle=False)
        obj = cls()
        obj._n = int(data["n"][0])
        obj._cell_size = int(data["cell_size"][0])
        mat_stored = data["matrix"]
        # restore amortized matrix (exact size is fine for loaded data)
        obj._mat = np.empty((max(obj._n, 64), obj._cell_size), dtype=np.uint8)
        if obj._n > 0:
            obj._mat[:obj._n] = mat_stored[:obj._n]
        # decode keys
        ids = data["ids"]
        blob = data["key_blob"].tobytes()
        offset = 0
        for i, rid in enumerate(ids):
            klen = struct.unpack(">I", blob[offset:offset + 4])[0]
            offset += 4
            k = blob[offset:offset + klen]
            offset += klen
            obj._key_to_id[k] = int(rid)
            h, w = struct.unpack(">HH", k[:4])
            obj._shapes.append((h, w))
        # Legacy files predate the arena/visited split and therefore treated
        # every interned row as visited.
        obj._visited = (
            {int(state_id) for state_id in data["visited"]}
            if "visited" in data.files
            else set(range(obj._n))
        )
        return obj


# ---------------------------------------------------------------------------
# Batch novelty  (semantic match to planner._novelty)
# ---------------------------------------------------------------------------

def batch_novelty(grid: Grid, interner: StateInterner) -> int:
    """Min hamming distance from `grid` to any visited state.

    Semantics identical to planner._novelty:
    - Returns 0 if the visited set is empty or grid is already visited.
    - Returns min cell-difference count otherwise.
    - Short-circuits when best reaches 1 (can't improve: 0 excluded by the
      already-visited guard above).

    Uses numpy broadcasting: one subtraction+bool over the full matrix, then
    argmin of row sums — O(N * H*W) but in C, not Python loops.
    """
    if len(interner) == 0 or grid in interner:
        return 0

    arr = grid_to_array(grid).ravel().astype(np.uint8)  # (H*W,)
    mat = interner.visited_matrix  # (N_visited, H*W)

    # hamming rows: count of differing cells per state
    diffs = (mat != arr).sum(axis=1)  # (N,) int64
    best = int(diffs.min())
    # short-circuit note: numpy already computed all rows; the early-exit
    # semantics of planner._novelty (break when best==1) only matter for the
    # per-state Python loop — vectorized is faster regardless, so we return
    # the exact same value without emulating the per-row loop ordering.
    return best


def batch_novelty_multi(grids: "list[Grid]", interner: StateInterner) -> "list[int]":
    """Vectorized novelty for a batch of candidate grids against the interner.

    Returns list of int novelty scores (same semantics as batch_novelty per
    element). More cache-friendly than calling batch_novelty in a loop.
    """
    if len(interner) == 0:
        return [0] * len(grids)

    mat = interner.visited_matrix  # (N_visited, H*W)
    results = []
    for grid in grids:
        if grid in interner:
            results.append(0)
            continue
        arr = grid_to_array(grid).ravel().astype(np.uint8)
        diffs = (mat != arr).sum(axis=1)
        results.append(int(diffs.min()))
    return results


# ---------------------------------------------------------------------------
# AbstractCarrierInterner — fast membership for arbitrary hashable carriers
# ---------------------------------------------------------------------------

class AbstractCarrierInterner:
    """Maps arbitrary hashable carriers to integer IDs for O(1) int membership.

    Carrier types in this codebase are frozensets of (y, x, color) triples
    (sound_signature) or nested tuples with frozenset fields (object_signature).
    Both are hashable but expensive to compare: frozenset.__eq__ walks all K
    elements. Interning to ints replaces frozenset-in-set (O(K) hash + O(K)
    equality on collision) with int-in-set (O(1) hash + O(1) equality).

    _abstract_novelty semantics: binary 0/1, NOT hamming distance.
    abstract_novelty(carrier, interner) returns 0 if carrier is in the
    interner's visited set, 1 otherwise.  This matches _abstract_novelty
    exactly (see planner.py:134-146).

    Amortized-doubling: mirrors StateInterner; no per-intern reallocation of
    the visited set (Python set already amortizes internally).

    # ponytail: no numpy needed — carriers are not fixed-width; int IDs suffice
    """

    def __init__(self) -> None:
        self._carrier_to_id: dict = {}   # carrier -> int id
        self._visited: set = set()       # set of int ids marked as visited
        self._n: int = 0                 # total interned (visited + unvisited)

    def intern(self, carrier) -> int:
        """Return integer ID for carrier, adding to the intern table if new.

        Does NOT mark the carrier as visited — call mark_visited() for that.
        """
        cid = self._carrier_to_id.get(carrier)
        if cid is None:
            cid = self._n
            self._carrier_to_id[carrier] = cid
            self._n += 1
        return cid

    def mark_visited(self, carrier) -> int:
        """Intern carrier and mark it visited. Returns its int ID."""
        cid = self.intern(carrier)
        self._visited.add(cid)
        return cid

    def is_visited(self, carrier) -> bool:
        """True if carrier has been marked visited (abstract_novelty == 0)."""
        cid = self._carrier_to_id.get(carrier)
        if cid is None:
            return False
        return cid in self._visited

    def __len__(self) -> int:
        return len(self._visited)

    def __contains__(self, carrier) -> bool:
        """True if carrier is visited — supports `carrier in interner`."""
        return self.is_visited(carrier)


def abstract_novelty(carrier, interner: AbstractCarrierInterner) -> int:
    """Binary novelty for an abstract carrier: 0 if visited, 1 if new.

    Semantic contract: identical to _abstract_novelty(grid, visited, abstract_fn,
    visited_abstract) when visited_abstract is non-None (the O(1) branch at
    planner.py:144). The caller computes carrier = abstract_fn(grid) once and
    passes it here; this function does no grid work.

    Fast path: int-id lookup in a Python set replaces frozenset-in-set (which
    calls frozenset.__hash__ O(K) + frozenset.__eq__ O(K) on collision).
    """
    return 0 if interner.is_visited(carrier) else 1
