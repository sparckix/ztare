"""Pure hitting-set enumeration — domain-agnostic brute-force up to max_size.

Extracted from ztare.scenarios.argument_kernel.minimal_cores so multiple consumers
can reuse the identical algorithm without copying it. argument_kernel.minimal_cores
is now a two-line wrapper over this function; its public behavior is byte-identical.

ponytail: brute-force (exponential in max_size); exact for small universes.
Upgrade to QuickXplain or a prime-implicant enumerator if the universe grows past a
few dozen elements.
"""
from __future__ import annotations

from itertools import combinations
from typing import Callable


def minimal_hitting_sets(
    universe: list[str],
    is_hitting: "Callable[[frozenset[str]], bool]",
    max_size: int = 3,
) -> "list[frozenset[str]]":
    """Return the minimal subsets of *universe* for which *is_hitting* returns True,
    up to *max_size* elements.  Supersets of a known minimal set are skipped — only
    strictly minimal sets are returned."""
    cores: "list[frozenset[str]]" = []
    for size in range(1, max_size + 1):
        for combo in combinations(universe, size):
            cs = frozenset(combo)
            if any(c <= cs for c in cores):
                continue  # superset of a known minimal set — not minimal
            if is_hitting(cs):
                cores.append(cs)
    return cores
