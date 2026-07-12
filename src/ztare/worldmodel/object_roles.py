"""Grid object-role induction: an ARC AbstractionFunctor plugin (GP-250).

Induces behavioral ROLES from the episode log's transition statistics alone
(sealed-safe — no game docs, no semantic labels):

  moves_under_actions       features whose connected components translate under
                            action-conditioned transitions
  monotone_depleting        a feature whose global count is non-increasing and
                            strictly decreases inside episodes
  never_changes             features that never change anywhere in a transition
  covered_uncovered         features that change only by being covered/vacated
                            by a moving component
  static_structural_mirror  static components sharing a mover signature

Roles feed: schema specs (laws over roles), object-space planning (the
search-collapse), and cross-game schema transfer. Verification stays at the
raw level via the existing gates — the AbstractionFunctor contract.

These are ARC-grid role names, not kernel ontology. The kernel only requires an
alpha map from raw evidence to behavioral roles plus a lowering back to raw
predictions. A non-grid substrate should provide its own role vocabulary and
signature function instead of inheriting these names.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from ztare.common.abstraction_functor import AbstractState, Role
from ztare.worldmodel.episode_log import EpisodeLog


def _components(g, colors):
    h, w = len(g), len(g[0])
    seen = [[False] * w for _ in range(h)]
    comps = []
    for y0 in range(h):
        for x0 in range(w):
            if g[y0][x0] not in colors or seen[y0][x0]:
                continue
            comp, stack = [], [(y0, x0)]
            seen[y0][x0] = True
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for ny, nx in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
                    if 0 <= ny < h and 0 <= nx < w and not seen[ny][nx] \
                            and g[ny][nx] in colors:
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            comps.append(comp)
    return comps


def induce_roles(log: EpisodeLog, action_arity: int) -> AbstractState:
    rows = list(log)
    if not rows:
        return AbstractState(roles=[], detail="no evidence")
    all_colors = {c for tr in rows for row in tr.s for c in row}

    # per-color statistics over the whole log
    ever_changed: "set[int]" = set()
    counts_by_color: "dict[int, list[int]]" = defaultdict(list)
    moved_colors: Counter = Counter()      # colors seen rigidly displacing
    covered_uncovered: Counter = Counter() # colors that vanish/reappear under movers
    for tr in rows:
        diff = [(y, x, tr.s[y][x], tr.s_next[y][x])
                for y in range(len(tr.s)) for x in range(len(tr.s[0]))
                if tr.s[y][x] != tr.s_next[y][x]]
        lost, gained = defaultdict(list), defaultdict(list)
        for (y, x, a, b) in diff:
            ever_changed.add(a)
            ever_changed.add(b)
            lost[a].append((y, x))
            gained[b].append((y, x))
        for c in all_colors:
            counts_by_color[c].append(sum(1 for row in tr.s for v in row if v == c))
        for c, src in lost.items():
            dst = gained.get(c)
            if dst and len(dst) == len(src):
                offs = {(d[0]-s0[0], d[1]-s0[1]) for s0, d in zip(sorted(src), sorted(dst))}
                if len(offs) == 1 and next(iter(offs)) != (0, 0):
                    moved_colors[c] += 1
        # covered/uncovered: color lost exactly where a mover color gained
        mover_gain_cells = {p for c in moved_colors for p in gained.get(c, [])}
        for c, cells in lost.items():
            if c not in moved_colors and all(p in mover_gain_cells for p in cells):
                covered_uncovered[c] += 1

    agent_colors = sorted(c for c, n in moved_colors.items() if n >= 2)
    boundary = sorted(all_colors - ever_changed)
    # monotone depletion is judged PER EPISODE (t==0 marks a reset; a bar
    # refilling across resets is still a resource)
    episode_bounds = [i for i, tr in enumerate(rows) if tr.t == 0] + [len(rows)]
    def _monotone_depleting(c):
        depleted = False
        for a0, a1 in zip(episode_bounds, episode_bounds[1:]):
            seg = counts_by_color[c][a0:a1]
            if any(x < y for x, y in zip(seg, seg[1:])):
                pass
            if not all(x >= y for x, y in zip(seg, seg[1:])):
                return False
            if len(set(seg)) > 1:
                depleted = True
        return depleted
    resource = sorted(c for c in all_colors
                      if c not in agent_colors and _monotone_depleting(c))
    terrain = sorted(c for c, n in covered_uncovered.items() if n >= 2)

    roles = []
    if agent_colors:
        roles.append(Role("moves_under_actions", agent_colors,
                          f"rigid displacement in {sum(moved_colors.values())} transitions"))
    if resource:
        roles.append(Role("monotone_depleting", resource,
                          "global count strictly non-increasing with decreases"))
    if boundary:
        roles.append(Role("never_changes", boundary, "unchanged in every transition"))
    if terrain:
        roles.append(Role("covered_uncovered", terrain,
                          "changes only under arriving/vacating mover cells"))

    # indicator: static components with the agent's color signature
    if agent_colors:
        g0 = rows[0].s
        agent_sig = tuple(sorted(agent_colors))
        static_mirrors = 0
        for comp in _components(g0, set(agent_colors)):
            cells = {(y, x) for (y, x) in comp}
            moved_any = any((y, x, g0[y][x]) not in
                            {(yy, xx, tr.s[yy][xx]) for tr in rows[:1] for (yy, xx) in cells}
                            for (y, x) in comp)
            # a component is a mirror if its cells never changed across the log
            if all(tr.s[y][x] == g0[y][x] and tr.s_next[y][x] == g0[y][x]
                   for tr in rows for (y, x) in comp):
                static_mirrors += 1
        if static_mirrors:
            roles.append(Role("static_structural_mirror", [agent_sig],
                              f"{static_mirrors} immobile components share the mover's "
                              "color signature (goal-hypothesis source)"))
    return AbstractState(roles=roles,
                         detail=f"{len(rows)} transitions, {len(all_colors)} colors")


def object_signature(grid, roles) -> tuple:
    """Hashable ABSTRACT state for memoization (external-review fix: the sweep
    must dedup on object-state, not the raw 64x64 grid — that collapse is what
    turns 4^1500 into a ~1e5-node graph). Sound-by-refinement: coarse to start
    (small, fast); if the bounded object-space exhausts without the goal, the
    CEGAR classifier decides model-incompleteness vs too-coarse -> role split.

      controlled support -> frozenset of mover-cell positions
      monotone quantity  -> per-feature global counts
      reactive support   -> exact cells of covered/uncovered features
      invariant support  -> dropped (never changes; carries no state)
    """
    role_by_name = {r.name: r for r in roles}
    agent = frozenset()
    if "moves_under_actions" in role_by_name:
        ac = set(role_by_name["moves_under_actions"].members)
        agent = frozenset((y, x) for y in range(len(grid)) for x in range(len(grid[0]))
                          if grid[y][x] in ac)
    resource = ()
    if "monotone_depleting" in role_by_name:
        resource = tuple(sorted(
            (c, sum(1 for row in grid for v in row if v == c))
            for c in role_by_name["monotone_depleting"].members))
    reactive = frozenset()
    if "covered_uncovered" in role_by_name:
        rc = set(role_by_name["covered_uncovered"].members)
        reactive = frozenset((y, x, grid[y][x])
                             for y in range(len(grid)) for x in range(len(grid[0]))
                             if grid[y][x] in rc)
    return (agent, resource, reactive)


def control_signature(signature):
    """Projection used by coverage planners over an object signature.

    `object_signature` keeps all state needed for transition memoization. This
    projection selects the shortest action-controllable coordinate as the
    novelty carrier. It is deliberately a caller-supplied abstraction hook, not
    a rule embedded in reachability search.
    """
    if isinstance(signature, tuple) and len(signature) == 3:
        agent, _resource, reactive = signature
        if isinstance(agent, frozenset) and isinstance(reactive, frozenset):
            return ("agent", agent) if agent else ("reactive", reactive)
    return signature


def volatile_positions(log) -> "frozenset":
    """Cell POSITIONS whose value changes in >=1 transition — the minimal
    state-bearing set (a cell constant across the whole log is droppable even
    if its color varies elsewhere). A target the agent reaches becomes an
    agent-cell at that position, so goal-relevant positions ARE volatile ->
    aliasing-free (external-review #1 fix, tightened to positions)."""
    vp = set()
    for tr in log:
        for y in range(len(tr.s)):
            for x in range(len(tr.s[0])):
                if tr.s[y][x] != tr.s_next[y][x]:
                    vp.add((y, x))
    return frozenset(vp)


def sound_signature(grid, volatile_pos) -> tuple:
    """Aliasing-FREE minimal abstract key: (row, col, color) for every
    ever-changing position; constant cells dropped. Cannot merge two raw
    states differing in any state-bearing cell (never hides a goal); reachable
    set stays dynamics-bounded, not key-bounded."""
    return frozenset((y, x, grid[y][x]) for (y, x) in volatile_pos)
