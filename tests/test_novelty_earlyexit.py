"""Property test + timing for _hamming early-exit and _novelty equivalence (FIX 1)."""
import random
import time


def _make_grid(rows=4, cols=4, seed=None):
    rng = random.Random(seed)
    return tuple(tuple(rng.randint(0, 9) for _ in range(cols)) for _ in range(rows))


def _hamming_naive(a, b):
    return sum(1 for ra, rb in zip(a, b) for ca, cb in zip(ra, rb) if ca != cb)


def _novelty_naive(grid, visited):
    if not visited or grid in visited:
        return 0
    return min(_hamming_naive(grid, v) for v in visited)


def test_hamming_earlyexit_identical_to_naive():
    from ztare.worldmodel.planner import _hamming
    rng = random.Random(42)
    for _ in range(200):
        a = _make_grid(seed=rng.randint(0, 10**6))
        b = _make_grid(seed=rng.randint(0, 10**6))
        naive = _hamming_naive(a, b)
        # with limit=0 (no early exit)
        assert _hamming(a, b) == naive, "limit=0 mismatch"
        # with limit=naive (exact threshold)
        assert _hamming(a, b, limit=naive) == naive, "limit=naive mismatch"
        # with limit=1 (aggressive exit)
        result = _hamming(a, b, limit=1)
        if naive >= 1:
            assert result >= 1
        else:
            assert result == 0


def test_novelty_identical_to_naive():
    from ztare.worldmodel.planner import _novelty
    rng = random.Random(99)
    for _ in range(200):
        n_visited = rng.randint(0, 15)
        visited = {_make_grid(seed=rng.randint(0, 10**6)) for _ in range(n_visited)}
        grid = _make_grid(seed=rng.randint(0, 10**6))
        expected = _novelty_naive(grid, visited)
        got = _novelty(grid, visited)
        assert got == expected, f"novelty mismatch: got {got}, expected {expected}"


def test_novelty_timing():
    from ztare.worldmodel.planner import _novelty
    rng = random.Random(7)
    visited = {_make_grid(seed=rng.randint(0, 10**6)) for _ in range(500)}
    queries = [_make_grid(seed=rng.randint(0, 10**6)) for _ in range(2000)]

    t0 = time.perf_counter()
    for g in queries:
        _novelty_naive(g, visited)
    naive_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    for g in queries:
        _novelty(g, visited)
    fast_s = time.perf_counter() - t0

    print(f"\n_novelty timing — naive: {naive_s:.3f}s  early-exit: {fast_s:.3f}s  "
          f"speedup: {naive_s/fast_s:.2f}x  (500 visited, 2000 calls, 4×4 grids)")
    # no hard timing assertion — just ensure it finishes and is not catastrophically slower
    assert fast_s < naive_s * 3, "early-exit unexpectedly slower than naive"
