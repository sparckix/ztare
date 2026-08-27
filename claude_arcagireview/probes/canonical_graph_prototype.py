"""Diagnostic canonical-coordinate prototype for interactive grid substrates.

Status: review artifact, not an adopted world-model abstraction. The measured
129-node result in ``claude_arcagireview/14_canonical_coordinates_reframe.md``
came from a separate substrate-coordinate probe. This implementation does not
reproduce that quotient on the current evidence bank, and its change-rarity
digest overfragments rare transients. Keep it available for counterexamples;
do not wire it into transition equality or frontier-cache identity.

The reframe (claude_arcagireview/14): pixel space is a RENDERING of a small
latent state. This module lifts observations into canonical coordinates —
(regime, controllable-object position, static-world mode) — where the whole
observed game is a small labeled graph (measured on ls20: 16,506 rows -> 129
nodes / 371 edges) and the acquisition frontier is an enumerable set of
unwitnessed (node, action) pairs.

Substrate-general by construction:
- the CONTROLLABLE OBJECT is found as the connected multi-color component
  whose position translates under actions (no shape constants; falls back to
  the largest mover from evidence when a probe pattern is supplied by the
  caller it is ignored — nothing here names colors or coordinates);
- the REGIME cell set and STATIC MASK are derived from change-rarity across
  the bank (cells that almost never change carry world/mode identity; cells
  that churn are dashboard volatiles and excluded);
- MODE = digest of static-mask content: any persistent world alteration (a
  key removed, a door opened) flips the mode with no named mechanic.

Authority: none. This is an evidence projection (steering/novelty/frontier
vocabulary). Replay, holdout, and the sealed adjudicator are untouched.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable


def change_rarity_mask(rows, *, max_change_fraction: float = 0.002) -> "frozenset[tuple[int, int]]":
    """Cells that change in at most `max_change_fraction` of transitions.

    These carry persistent world identity (walls, mode objects); churny cells
    (meters, clocks, the mover itself) are excluded by construction.
    """
    if not rows:
        return frozenset()
    h, w = len(rows[0].s), len(rows[0].s[0])
    changes = [[0] * w for _ in range(h)]
    n = 0
    for tr in rows:
        n += 1
        s, sn = tr.s, tr.s_next
        for y in range(h):
            ry, rny = s[y], sn[y]
            if ry != rny:
                for x in range(w):
                    if ry[x] != rny[x]:
                        changes[y][x] += 1
    cap = max(1, int(max_change_fraction * n))
    return frozenset(
        (y, x) for y in range(h) for x in range(w) if changes[y][x] <= cap
    )


def mover_locator(rows) -> "Callable[[Any], tuple[int, int] | None]":
    """Locate the controllable object: the most-translating connected
    component signature across observed transitions. Returns a function
    grid -> top-left of the best-matching component, or None."""
    # Signature = (relative cell offsets, color per offset) of components that
    # moved rigidly between s and s_next; the most frequent such signature is
    # the mover. No color or shape constants.
    sig_count: Counter = Counter()
    sample = rows[:: max(1, len(rows) // 400)]
    for tr in sample:
        diff = [(y, x) for y in range(len(tr.s)) for x in range(len(tr.s[0]))
                if tr.s[y][x] != tr.s_next[y][x]]
        if not (2 <= len(diff) <= 80):
            continue
        # cells vacated (source of a rigid move)
        vac = [(y, x) for (y, x) in diff]
        ys = [y for y, _ in vac]; xs = [x for _, x in vac]
        y0, x0 = min(ys), min(xs)
        sig = tuple(sorted((y - y0, x - x0, int(tr.s[y][x])) for (y, x) in vac
                           if tr.s[y][x] != tr.s_next[y][x]))
        if sig:
            sig_count[sig] += 1
    if not sig_count:
        return lambda g: None
    # the mover's pre-move footprint appears in half of every move diff; take
    # the top signatures and extract their color multiset as the mover palette
    top = [s for s, _ in sig_count.most_common(8)]
    palettes = Counter()
    for s in top:
        palettes[frozenset(c for _, _, c in s)] += sig_count[s]
    palette = max(palettes, key=palettes.get)

    def _locate(g) -> "tuple[int, int] | None":
        h, w = len(g), len(g[0])
        seen = [[False] * w for _ in range(h)]
        best = None
        for y in range(h):
            for x in range(w):
                if seen[y][x] or g[y][x] not in palette:
                    continue
                comp, stack = [], [(y, x)]
                seen[y][x] = True
                while stack:
                    cy, cx = stack.pop()
                    comp.append((cy, cx))
                    for ny, nx in ((cy-1, cx), (cy+1, cx), (cy, cx-1), (cy, cx+1)):
                        if 0 <= ny < h and 0 <= nx < w and not seen[ny][nx] \
                                and g[ny][nx] in palette:
                            seen[ny][nx] = True
                            stack.append((ny, nx))
                colors = {g[cy][cx] for cy, cx in comp}
                # the controllable object carries the full mover palette
                if colors == palette:
                    top_left = (min(c[0] for c in comp), min(c[1] for c in comp))
                    if best is None or len(comp) > best[0]:
                        best = (len(comp), top_left)
        return best[1] if best else None

    return _locate


def canonical_alpha_factory(rows, *, max_change_fraction: float = 0.002):
    """Build alpha(grid) -> (mode_digest, mover_pos) from bank evidence.

    mode_digest: 12-hex digest of static-mask content — any persistent world
    alteration (key taken, door opened, level relayout) flips it. mover_pos:
    canonical position of the controllable object. Both derived; no substrate
    nouns. Returns (alpha, receipt_dict).
    """
    mask = sorted(change_rarity_mask(rows, max_change_fraction=max_change_fraction))
    locate = mover_locator(rows)

    def alpha(g) -> tuple:
        static = hashlib.sha256(
            json.dumps([int(g[y][x]) for (y, x) in mask]).encode()
        ).hexdigest()[:12]
        return (static, locate(g))

    receipt = {
        "schema": "ztare-canonical-alpha-v1",
        "static_mask_cells": len(mask),
        "max_change_fraction": max_change_fraction,
    }
    return alpha, receipt


def build_canonical_graph(rows, alpha, *, env_indices: "set[int] | None" = None) -> dict:
    """The observed game as a labeled graph in canonical coordinates.

    Returns nodes, deterministic edges, nondeterministic (node, action) pairs
    (the concentrated mystery: latent scalars condition those edges), and the
    per-node unwitnessed action frontier.
    """
    env = env_indices or set()
    edges: "defaultdict[tuple, Counter]" = defaultdict(Counter)
    arity = 0
    for i, tr in enumerate(rows):
        if i in env:
            continue
        arity = max(arity, int(tr.a) + 1)
        a0, a1 = alpha(tr.s), alpha(tr.s_next)
        if a0[1] is None or a1[1] is None:
            continue
        edges[a0][(int(tr.a), a1)] += 1
    nodes = sorted(edges, key=repr)
    nondet, frontier, det = [], [], {}
    for node in nodes:
        by_action: "defaultdict[int, set]" = defaultdict(set)
        for (act, dst), _n in edges[node].items():
            by_action[act].add(dst)
        for act in range(arity):
            dsts = by_action.get(act)
            if not dsts:
                frontier.append((node, act))
            elif len(dsts) > 1:
                nondet.append((node, act, sorted(dsts, key=repr)))
            else:
                det[(node, act)] = next(iter(dsts))
    return {
        "schema": "ztare-canonical-graph-v1",
        "nodes": len(nodes),
        "action_arity": arity,
        "deterministic_edges": len(det),
        "nondeterministic_pairs": len(nondet),
        "frontier_pairs": len(frontier),
        "_nodes": nodes,
        "_det": det,
        "_nondet": nondet,
        "_frontier": frontier,
    }


def frontier_alpha_pairs(graph: dict) -> "set[tuple]":
    """(alpha-node, action) pairs never witnessed — the acquisition targets
    consumed by plan_witness_gap when the planner runs under this alpha."""
    return set(graph["_frontier"]) | {
        (node, act) for (node, act, _d) in graph["_nondet"]
    }
