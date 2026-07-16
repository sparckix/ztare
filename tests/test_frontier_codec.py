"""Tests for frontier_codec and phase_timing; includes equivalence proof.

Three sections:
  1. frontier_codec unit tests (round-trip, interner, persistence).
  2. 500-grid exact equivalence proof: batch_novelty == planner._novelty.
  3. Benchmark: pure-Python vs vectorized; JSON vs npz persistence.
  4. phase_timing smoke test.
"""

from __future__ import annotations

import io
import json
import random
import struct
import tempfile
import time
from pathlib import Path

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------

from ztare.worldmodel.frontier_codec import (
    StateInterner,
    array_to_grid,
    batch_novelty,
    grid_to_array,
    grid_to_key,
    key_to_grid,
)
from ztare.worldmodel.planner import _novelty  # read-only import


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rand_grid(h: int = 4, w: int = 4, seed: int | None = None) -> tuple:
    rng = random.Random(seed)
    return tuple(tuple(rng.randint(0, 15) for _ in range(w)) for _ in range(h))


def _rand_grid_np(h: int, w: int, rng: np.random.Generator) -> tuple:
    arr = rng.integers(0, 16, (h, w), dtype=np.uint8)
    return array_to_grid(arr)


# ---------------------------------------------------------------------------
# 1. Grid codec round-trip
# ---------------------------------------------------------------------------

class TestGridCodec:
    def test_small_round_trip(self):
        g = _rand_grid(3, 3, seed=0)
        assert key_to_grid(grid_to_key(g)) == g

    def test_large_round_trip(self):
        g = _rand_grid(64, 64, seed=1)
        assert key_to_grid(grid_to_key(g)) == g

    def test_array_round_trip(self):
        g = _rand_grid(8, 8, seed=2)
        assert array_to_grid(grid_to_array(g)) == g

    def test_key_size(self):
        g = _rand_grid(64, 64, seed=3)
        key = grid_to_key(g)
        # 4 bytes header + 64*64 = 4100 bytes — well under 94KB JSON
        assert len(key) == 4 + 64 * 64

    def test_key_encodes_shape(self):
        g = _rand_grid(5, 7, seed=4)
        key = grid_to_key(g)
        h, w = struct.unpack(">HH", key[:4])
        assert (h, w) == (5, 7)

    def test_different_grids_different_keys(self):
        g1 = _rand_grid(4, 4, seed=5)
        g2 = _rand_grid(4, 4, seed=6)
        assert grid_to_key(g1) != grid_to_key(g2)

    def test_same_grid_same_key(self):
        g = _rand_grid(4, 4, seed=7)
        assert grid_to_key(g) == grid_to_key(g)


# ---------------------------------------------------------------------------
# 2. StateInterner
# ---------------------------------------------------------------------------

class TestStateInterner:
    def test_basic_intern(self):
        si = StateInterner()
        g = _rand_grid(4, 4, seed=10)
        id0 = si.intern(g)
        id1 = si.intern(g)
        assert id0 == id1 == 0
        assert g not in si
        assert len(si) == 0
        assert si.mark_visited(g) == id0
        assert len(si) == 1

    def test_two_states(self):
        si = StateInterner()
        g1, g2 = _rand_grid(4, 4, seed=11), _rand_grid(4, 4, seed=12)
        assert si.intern(g1) == 0
        assert si.intern(g2) == 1
        assert si.matrix.shape == (2, 16)
        si.mark_visited(g2)
        assert len(si) == 1
        assert g1 not in si and g2 in si

    def test_contains(self):
        si = StateInterner()
        g = _rand_grid(4, 4, seed=13)
        assert g not in si
        si.intern(g)
        assert g not in si
        si.mark_visited(g)
        assert g in si

    def test_matrix_shape(self):
        si = StateInterner()
        for i in range(10):
            si.intern(_rand_grid(4, 4, seed=i + 100))
        mat = si.matrix
        assert mat.shape == (10, 16)
        assert mat.dtype == np.uint8

    def test_matrix_values(self):
        si = StateInterner()
        g = _rand_grid(3, 3, seed=20)
        si.intern(g)
        expected = grid_to_array(g).ravel()
        np.testing.assert_array_equal(si.matrix[0], expected)

    def test_amortized_growth(self):
        """Intern 200 states (triggers several doublings)."""
        si = StateInterner()
        grids = [_rand_grid(8, 8, seed=i) for i in range(200)]
        for g in grids:
            si.intern(g)
        assert len(si) == 0
        assert si.matrix.shape == (200, 64)

    def test_save_load_round_trip(self):
        si = StateInterner()
        grids = [_rand_grid(4, 4, seed=i + 300) for i in range(50)]
        for g in grids:
            si.intern(g)
        for g in grids[::2]:
            si.mark_visited(g)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "interner.npz"
            si.save(p)
            si2 = StateInterner.load(p)
        assert len(si2) == 25
        np.testing.assert_array_equal(si.matrix, si2.matrix)
        for index, g in enumerate(grids):
            assert (g in si2) is (index % 2 == 0)
        # check IDs match
        for g in grids:
            assert si.get_id(g) == si2.get_id(g)

    def test_size_ratio_vs_json(self, capsys):
        """Paste size ratio — not a correctness assertion, just a report."""
        n_states = 500
        h, w = 64, 64
        rng = np.random.default_rng(42)
        grids = [array_to_grid(rng.integers(0, 16, (h, w), dtype=np.uint8))
                 for _ in range(n_states)]
        # JSON encoding (per-state row, like visited_*.jsonl)
        json_buf = io.StringIO()
        for g in grids:
            json_buf.write(json.dumps({"grid": [list(r) for r in g]}) + "\n")
        json_bytes = len(json_buf.getvalue().encode())

        # npz encoding
        si = StateInterner()
        for g in grids:
            si.intern(g)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.npz"
            si.save(p)
            npz_bytes = p.stat().st_size

        ratio = json_bytes / npz_bytes
        # Print for benchmark table
        print(f"\n[size] JSON={json_bytes/1024:.1f}KB  npz={npz_bytes/1024:.1f}KB  ratio={ratio:.1f}x")
        # ponytail: random 0-15 data compresses poorly (npz also zlib-compresses);
        # real game grids with structure see higher ratios. Assert >2x as lower bound.
        # Live visited_*.jsonl sees ~23x (94KB/state vs ~4KB key).
        assert ratio > 2, f"expected >2x vs JSON, got {ratio:.1f}x"


# ---------------------------------------------------------------------------
# 3. Exact equivalence proof: batch_novelty == planner._novelty (500 grids)
# ---------------------------------------------------------------------------

class TestEquivalence:
    """Non-negotiable artifact: vectorized novelty must match pure-Python exactly."""

    def test_500_grid_equivalence(self):
        rng = np.random.default_rng(2025)
        h, w = 8, 8

        # Build a visited set of 50 states (both as tuple-set and interner)
        visited_grids = [
            array_to_grid(rng.integers(0, 16, (h, w), dtype=np.uint8))
            for _ in range(50)
        ]
        visited_set: set = set(visited_grids)
        si = StateInterner()
        for g in visited_grids:
            si.mark_visited(g)

        # 500 probe grids (mix of fresh + some from visited)
        probe_grids = [
            array_to_grid(rng.integers(0, 16, (h, w), dtype=np.uint8))
            for _ in range(450)
        ] + list(visited_grids[:50])

        failures = []
        for i, g in enumerate(probe_grids):
            expected = _novelty(g, visited_set)
            got = batch_novelty(g, si)
            if expected != got:
                failures.append((i, expected, got))

        assert not failures, (
            f"{len(failures)}/500 mismatches: {failures[:5]}"
        )

    def test_empty_visited(self):
        si = StateInterner()
        g = _rand_grid(4, 4, seed=99)
        assert batch_novelty(g, si) == 0
        assert _novelty(g, set()) == 0

    def test_grid_in_visited(self):
        rng = np.random.default_rng(7)
        grids = [array_to_grid(rng.integers(0, 16, (4, 4), dtype=np.uint8)) for _ in range(5)]
        visited_set = set(grids)
        si = StateInterner()
        for g in grids:
            si.mark_visited(g)
        for g in grids:
            assert batch_novelty(g, si) == 0
            assert _novelty(g, visited_set) == 0

    def test_min_distance_correct(self):
        """Single-cell difference should give novelty 1."""
        base = tuple(tuple(0 for _ in range(4)) for _ in range(4))
        # one cell differs
        modified = tuple(
            tuple(1 if (r == 0 and c == 0) else 0 for c in range(4))
            for r in range(4)
        )
        visited_set = {base}
        si = StateInterner()
        si.mark_visited(base)
        assert _novelty(modified, visited_set) == 1
        assert batch_novelty(modified, si) == 1

    def test_simulated_arena_order_cannot_change_novelty(self):
        """Interned search states are identity rows, not visited evidence."""
        visited = ((0, 0), (0, 0))
        probe = ((1, 1), (0, 0))
        simulated = [probe, ((2, 0), (0, 0)), ((3, 3), (3, 3))]

        scores = []
        for arena_order in (simulated, list(reversed(simulated))):
            si = StateInterner()
            for grid in arena_order:
                si.intern(grid)
            si.mark_visited(visited)
            assert probe not in si
            scores.append(batch_novelty(probe, si))

        assert scores == [_novelty(probe, {visited})] * 2
        assert scores[0] > 0


# ---------------------------------------------------------------------------
# 4. Benchmark (captured for reporting, not a correctness gate)
# ---------------------------------------------------------------------------

class TestBenchmark:
    def test_benchmark_2000_states(self, capsys):
        """Synthetic workload: 2000 states accumulated, novelty queried at each step.

        Pure-Python _novelty is O(visited * cells) per query; at 64x64 x 2000
        states, O(N^2 * cells) is ~16B ops. We time BOTH but cap the pure-Python
        run at 200 states (still representative of the quadratic blowup) and
        extrapolate. The vectorized path runs the full 2000 to show it stays fast.
        """
        rng = np.random.default_rng(314)
        h, w = 64, 64
        # ~20% duplicates
        unique = [array_to_grid(rng.integers(0, 16, (h, w), dtype=np.uint8)) for _ in range(1600)]
        all_grids = unique + unique[:400]
        random.Random(1).shuffle(all_grids)

        # (a) pure-Python — cap at 200 states to keep test under ~5s
        py_n = 200
        visited_set: set = set()
        t0 = time.perf_counter()
        for g in all_grids[:py_n]:
            _novelty(g, visited_set)
            visited_set.add(g)
        py_time_200 = time.perf_counter() - t0

        # (b) vectorized — full 2000
        si = StateInterner()
        t1 = time.perf_counter()
        for g in all_grids:
            batch_novelty(g, si)
            si.mark_visited(g)
        vec_time_2000 = time.perf_counter() - t1

        # Extrapolate: pure-Python at 2000 states scales O(N^2) from 200
        # (at 200 states, avg visited ~100; at 2000, avg ~1000 — 10x more work per query,
        # 10x more queries = ~100x total)
        py_time_2000_est = py_time_200 * 100

        speedup = py_time_2000_est / vec_time_2000 if vec_time_2000 > 0 else float("inf")

        # JSON vs npz persistence for 500 states
        states_500 = all_grids[:500]
        t2 = time.perf_counter()
        json_buf = io.StringIO()
        for g in states_500:
            json_buf.write(json.dumps({"grid": [list(r) for r in g]}) + "\n")
        json_write_time = time.perf_counter() - t2

        si2 = StateInterner()
        for g in states_500:
            si2.intern(g)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bench.npz"
            t3 = time.perf_counter()
            si2.save(p)
            npz_write_time = time.perf_counter() - t3
            npz_size = p.stat().st_size

        json_size = len(json_buf.getvalue().encode())
        persist_speedup = json_write_time / npz_write_time if npz_write_time > 0 else float("inf")
        size_ratio = json_size / npz_size

        print(
            f"\n=== BENCHMARK ===\n"
            f"(a) pure-Python novelty (200 states measured, 64x64): {py_time_200:.3f}s\n"
            f"    est. for 2000 states (O(N^2) extrap):           {py_time_2000_est:.1f}s\n"
            f"(b) vectorized novelty  (2000 states, 64x64):        {vec_time_2000:.3f}s\n"
            f"    speedup (estimated): {speedup:.0f}x\n"
            f"(c) JSON persistence  (500 states): {json_write_time*1000:.1f}ms "
            f"({json_size/1024:.0f}KB)\n"
            f"(d) npz  persistence  (500 states): {npz_write_time*1000:.1f}ms "
            f"({npz_size/1024:.0f}KB)\n"
            f"    write speedup: {persist_speedup:.1f}x  size ratio: {size_ratio:.0f}x"
        )

        # Loose sanity: vectorized 2000-state run should finish faster than
        # the pure-Python 200-state run (numpy wins at this scale even with interning overhead)
        assert vec_time_2000 < py_time_200 * 20, (
            f"vectorized 2000-state run ({vec_time_2000:.2f}s) unexpectedly slow vs "
            f"py 200-state ({py_time_200:.2f}s)"
        )


# ---------------------------------------------------------------------------
# 5. phase_timing
# ---------------------------------------------------------------------------

class TestPhaseTiming:
    def test_basic_record(self):
        from ztare.common.phase_timing import phase

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            with phase("test_phase", ws):
                pass
            lines = (ws / "phase_timings.jsonl").read_text().splitlines()
            assert len(lines) == 1
            rec = json.loads(lines[0])
            assert rec["schema"] == "ztare.phase_timing.v1"
            assert rec["phase"] == "test_phase"
            assert rec["seconds"] >= 0
            assert rec["depth"] == 0

    def test_nested_depth(self):
        from ztare.common.phase_timing import phase

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            with phase("outer", ws):
                with phase("inner", ws):
                    pass
            lines = (ws / "phase_timings.jsonl").read_text().splitlines()
            assert len(lines) == 2
            inner = json.loads(lines[0])  # inner closes first → written first
            outer = json.loads(lines[1])
            assert inner["phase"] == "inner" and inner["depth"] == 1
            assert outer["phase"] == "outer" and outer["depth"] == 0
