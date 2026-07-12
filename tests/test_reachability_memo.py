"""Memo freshness test: _visited_control_cache invalidates after visited_store grows (FIX 2)."""
import pytest


def _fresh_store(*keys):
    return set(keys)


def test_cache_miss_on_growth():
    """After adding an element, cache invalidates and returns updated set."""
    from ztare.worldmodel.reachability import _visited_control_cache, reachability_sweep

    # Minimal champion: identity (state never changes → no reachable transitions)
    def champion(grid, action, step):
        return grid

    start = ((0, 1), (2, 3))
    abstract_fn = lambda g: frozenset((r, c, v) for r, row in enumerate(g) for c, v in enumerate(row))

    visited_store = {abstract_fn(start)}

    # First call — populates cache
    _visited_control_cache.clear()
    r1 = reachability_sweep(champion, start, 1, goal_fn=None,
                            abstract_fn=abstract_fn,
                            visited_store=visited_store, max_depth=1)
    assert r1.saturated  # only one reachable state and it's already visited

    size_before = len(visited_store)
    assert size_before in _visited_control_cache

    # Mutate visited_store — cache key (size) changes
    new_key = frozenset([(9, 9, 5)])
    visited_store.add(new_key)
    assert len(visited_store) == size_before + 1

    # Second call — must recompute (old key no longer in cache after clear+rebuild)
    r2 = reachability_sweep(champion, start, 1, goal_fn=None,
                            abstract_fn=abstract_fn,
                            visited_store=visited_store, max_depth=1)

    # New size should now be cached, old size should not
    assert len(visited_store) in _visited_control_cache
    assert size_before not in _visited_control_cache


def test_cache_hit_on_same_size():
    """Same visited_store size → cache is reused (no rebuild)."""
    from ztare.worldmodel.reachability import _visited_control_cache, reachability_sweep

    def champion(grid, action, step):
        return grid

    start = ((1, 2), (3, 4))
    abstract_fn = lambda g: frozenset((r, c, v) for r, row in enumerate(g) for c, v in enumerate(row))
    visited_store = {abstract_fn(start)}

    _visited_control_cache.clear()
    reachability_sweep(champion, start, 1, goal_fn=None,
                       abstract_fn=abstract_fn,
                       visited_store=visited_store, max_depth=1)

    # Record the cached object identity
    cached_set = _visited_control_cache.get(len(visited_store))
    assert cached_set is not None

    reachability_sweep(champion, start, 1, goal_fn=None,
                       abstract_fn=abstract_fn,
                       visited_store=visited_store, max_depth=1)

    # Same size → same cached set object (not rebuilt)
    assert _visited_control_cache.get(len(visited_store)) is cached_set


def test_cache_fresh_set_returned_after_mutation():
    """The set returned to the sweep reflects the NEW visited_store contents after mutation."""
    from ztare.worldmodel.reachability import _visited_control_cache, reachability_sweep

    # Champion that generates one new state
    alt = ((9, 9), (9, 9))

    def champion(grid, action, step):
        return alt if grid != alt else grid

    start = ((0, 0), (0, 0))
    abstract_fn = lambda g: frozenset((r, c, v) for r, row in enumerate(g) for c, v in enumerate(row))

    visited_store = {abstract_fn(start)}
    _visited_control_cache.clear()

    r1 = reachability_sweep(champion, start, 1, goal_fn=None,
                            abstract_fn=abstract_fn,
                            visited_store=visited_store, max_depth=2)
    # alt is not in visited_store yet → novel path exists → not saturated
    assert not r1.saturated

    # Now add alt to visited_store (simulating live execution)
    visited_store.add(abstract_fn(alt))

    r2 = reachability_sweep(champion, start, 1, goal_fn=None,
                            abstract_fn=abstract_fn,
                            visited_store=visited_store, max_depth=2)
    # Both reachable states now in visited → saturated
    assert r2.saturated
