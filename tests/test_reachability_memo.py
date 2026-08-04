"""Frontier projections are recomputed from the current store identity."""


def _fresh_store(*keys):
    return set(keys)


def test_frontier_projection_observes_store_growth():
    """Adding a visited carrier changes the next sweep immediately."""
    from ztare.worldmodel.reachability import reachability_sweep

    alt = ((9,),)

    def champion(grid, _action, _step):
        return alt if grid != alt else grid

    start = ((0,),)
    visited_store = {start}
    first = reachability_sweep(
        champion,
        start,
        1,
        abstract_fn=lambda grid: grid,
        visited_store=visited_store,
        max_depth=2,
    )
    assert first.paths == [[0]]

    visited_store.add(alt)
    second = reachability_sweep(
        champion,
        start,
        1,
        abstract_fn=lambda grid: grid,
        visited_store=visited_store,
        max_depth=2,
    )
    assert second.saturated


def test_equal_size_frontiers_do_not_share_projected_membership():
    """Cardinality is not a valid identity for two frontier stores."""
    from ztare.worldmodel.reachability import reachability_sweep

    alt = ((9,),)

    def champion(grid, _action, _step):
        return alt if grid != alt else grid

    start = ((0,),)
    kwargs = {
        "abstract_fn": lambda grid: grid,
        "coverage_fn": lambda identity: identity,
        "max_depth": 2,
    }
    start_seen = reachability_sweep(
        champion,
        start,
        1,
        visited_store={start},
        **kwargs,
    )
    alt_seen = reachability_sweep(
        champion,
        start,
        1,
        visited_store={alt},
        **kwargs,
    )

    assert len({start}) == len({alt})
    assert start_seen.paths == [[0]]
    assert alt_seen.paths == []
    assert not start_seen.saturated
    assert not alt_seen.saturated


def test_cache_fresh_set_returned_after_mutation():
    """The set returned to the sweep reflects the NEW visited_store contents after mutation."""
    from ztare.worldmodel.reachability import reachability_sweep

    # Champion that generates one new state
    alt = ((9, 9), (9, 9))

    def champion(grid, action, step):
        return alt if grid != alt else grid

    start = ((0, 0), (0, 0))
    abstract_fn = lambda g: frozenset((r, c, v) for r, row in enumerate(g) for c, v in enumerate(row))

    visited_store = {abstract_fn(start)}

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
