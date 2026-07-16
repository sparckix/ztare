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
from ztare.worldmodel.transition_identity import authoritative_boundary


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


_COMPONENT_ORBIT_KIND = "colored_component_orbit_v1"
_REACTIVE_FIELD_KIND = "localized_reactive_field_v1"


def _component_image(grid, component):
    """Return ``(origin, normalized colored shape)`` for one component.

    The origin is a presentation coordinate.  The normalized colored shape is
    the component identity tested for transport.  Keeping these separate is
    what prevents palette membership from becoming object identity.
    """
    y0 = min(y for y, _x in component)
    x0 = min(x for _y, x in component)
    shape = tuple(sorted(
        (y - y0, x - x0, int(grid[y][x])) for y, x in component
    ))
    return (y0, x0), shape


def _component_images(grid, colors):
    images: "dict[tuple, list[tuple[int, int]]]" = defaultdict(list)
    for component in _components(grid, colors):
        origin, shape = _component_image(grid, component)
        images[shape].append(origin)
    return images


def _translated_component_orbits(rows, colors, *, min_support: int = 2):
    """Induce component identities from witnessed translation orbits.

    Colors only define the candidate observation chart.  A member is admitted
    when an entire normalized colored component disappears at one origin and
    appears at another under a within-epoch intervention.  This is stricter
    than declaring every cell of a frequently moved color to be the mover.
    """
    if not colors:
        return []
    support: "dict[tuple, Counter]" = defaultdict(Counter)
    for tr in rows:
        if tr.identity is not None and tr.identity.is_authoritative \
                and tr.identity.is_boundary:
            continue
        before = _component_images(tr.s, set(colors))
        after = _component_images(tr.s_next, set(colors))
        for shape in before.keys() & after.keys():
            lost = list((Counter(before[shape]) - Counter(after[shape])).elements())
            gained = list((Counter(after[shape]) - Counter(before[shape])).elements())
            # Ambiguous fission/fusion or multiple simultaneous copies do not
            # establish a particular object's transport identity.
            if len(lost) != 1 or len(gained) != 1:
                continue
            dy = int(gained[0][0] - lost[0][0])
            dx = int(gained[0][1] - lost[0][1])
            if (dy, dx) == (0, 0):
                continue
            height = 1 + max(cell[0] for cell in shape)
            width = 1 + max(cell[1] for cell in shape)
            # Reject episode-scale teleport coincidences.  The bound is
            # relative to the observed entity, so no grid size or game step is
            # encoded here.
            if max(abs(dy), abs(dx)) > 2 * max(height, width):
                continue
            support[shape][(int(tr.a), dy, dx)] += 1

    members = []
    for shape, motion_counts in support.items():
        total = sum(motion_counts.values())
        if total < min_support:
            continue
        members.append({
            "kind": _COMPONENT_ORBIT_KIND,
            "shape": [list(cell) for cell in shape],
            "action_displacements": [
                [action, dy, dx, count]
                for (action, dy, dx), count in sorted(motion_counts.items())
            ],
            "support": total,
        })
    members.sort(key=lambda row: (-int(row["support"]), row["shape"]))
    return members


def _component_orbit_members(role) -> list[dict]:
    return [
        member for member in getattr(role, "members", [])
        if isinstance(member, dict)
        and member.get("kind") == _COMPONENT_ORBIT_KIND
        and isinstance(member.get("shape"), list)
    ]


def _reactive_field_members(role) -> list[dict]:
    return [
        member for member in getattr(role, "members", [])
        if isinstance(member, dict)
        and member.get("kind") == _REACTIVE_FIELD_KIND
        and isinstance(member.get("baseline"), list)
    ]


def _reactive_field(rows, orbit_members) -> "dict | None":
    """Infer the sparse field exposed or covered by translated components."""
    baseline_votes: "dict[tuple[int, int], Counter]" = defaultdict(Counter)
    mover_values = {
        int(cell[2])
        for member in orbit_members
        for cell in member.get("shape", [])
    }
    for tr in rows:
        if tr.identity is not None and tr.identity.is_authoritative \
                and tr.identity.is_boundary:
            continue
        for member in orbit_members:
            shape = tuple(tuple(int(value) for value in cell)
                          for cell in member["shape"])
            colors = {cell[2] for cell in shape}
            before = _component_images(tr.s, colors).get(shape, [])
            after = _component_images(tr.s_next, colors).get(shape, [])
            lost = list((Counter(before) - Counter(after)).elements())
            gained = list((Counter(after) - Counter(before)).elements())
            if len(lost) != 1 or len(gained) != 1:
                continue
            for origin, grid in ((lost[0], tr.s_next), (gained[0], tr.s)):
                for dy, dx, _value in shape:
                    y, x = origin[0] + dy, origin[1] + dx
                    observed = int(grid[y][x])
                    if observed not in mover_values:
                        baseline_votes[(y, x)][observed] += 1
    if not baseline_votes:
        return None
    baseline = [
        [y, x, votes.most_common(1)[0][0]]
        for (y, x), votes in sorted(baseline_votes.items())
    ]
    return {
        "kind": _REACTIVE_FIELD_KIND,
        "baseline": baseline,
        "feature_values": sorted({value for _y, _x, value in baseline}),
        "support": sum(sum(votes.values()) for votes in baseline_votes.values()),
    }


def _lifecycle_segments(rows) -> list[list[int]]:
    """Return within-lifecycle row indices under the strongest authority present.

    Adapter-attested epoch identity owns segmentation when available.  The
    clock is only a legacy presentation fallback for banks that contain no
    authoritative epoch coordinate at all.
    """
    has_epoch_authority = any(
        row.identity is not None
        and row.identity.is_authoritative
        and row.identity.source_epoch is not None
        for row in rows
    )
    if has_epoch_authority:
        segments: list[list[int]] = []
        active: list[int] = []
        active_epoch = object()
        for index, row in enumerate(rows):
            identity = row.identity
            if (
                identity is None
                or not identity.is_authoritative
                or identity.is_boundary
                or identity.source_epoch is None
                or identity.target_epoch not in (None, identity.source_epoch)
            ):
                if active:
                    segments.append(active)
                    active = []
                active_epoch = object()
                continue
            if active and identity.source_epoch != active_epoch:
                segments.append(active)
                active = []
            active_epoch = identity.source_epoch
            active.append(index)
        if active:
            segments.append(active)
        return segments

    segments = []
    active = []
    prior_time = None
    for index, row in enumerate(rows):
        if active and prior_time is not None and row.t <= prior_time:
            segments.append(active)
            active = []
        active.append(index)
        prior_time = row.t
    if active:
        segments.append(active)
    return segments


def induce_roles(log: EpisodeLog, action_arity: int) -> AbstractState:
    # An adapter-attested boundary is a lifecycle transition, not a sample of
    # the within-epoch law whose roles are being induced.  Untrusted boundary
    # claims remain ordinary observations and cannot erase evidence.
    rows = [row for row in log if not authoritative_boundary(row.identity)]
    if not rows:
        return AbstractState(roles=[], detail="no evidence")
    all_colors = {c for tr in rows for row in tr.s for c in row}

    # per-color statistics over the whole log
    ever_changed: "set[int]" = set()
    counts_by_color: "dict[int, list[int]]" = defaultdict(list)
    moved_colors: Counter = Counter()      # features seen rigidly displacing
    movement_groups: Counter = Counter()   # co-translated feature charts
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
        state_counts = Counter(value for row in tr.s for value in row)
        for c in all_colors:
            counts_by_color[c].append(state_counts[c])
        rigid_by_vector: "dict[tuple[int, int, int], set[int]]" = defaultdict(set)
        for c, src in lost.items():
            dst = gained.get(c)
            if dst and len(dst) == len(src):
                offs = {(d[0]-s0[0], d[1]-s0[1]) for s0, d in zip(sorted(src), sorted(dst))}
                if len(offs) == 1 and next(iter(offs)) != (0, 0):
                    moved_colors[c] += 1
                    dy, dx = next(iter(offs))
                    rigid_by_vector[(int(tr.a), int(dy), int(dx))].add(int(c))
        for colors in rigid_by_vector.values():
            if colors:
                movement_groups[frozenset(colors)] += 1

    # Palette statistics nominate observation charts; only exact component
    # transport grants mover identity.  The exchanged ambient complement often
    # has the opposite displacement but cannot preserve a normalized component
    # image, so it is rejected without a dominant-background heuristic.
    component_orbits: list[dict] = []
    shapes_seen: set[tuple] = set()
    candidate_groups = sorted(
        ((colors, support) for colors, support in movement_groups.items()
         if support >= 2),
        key=lambda item: (-item[1], -len(item[0]), tuple(sorted(item[0]))),
    )[:6]
    for colors, _support in candidate_groups:
        for member in _translated_component_orbits(rows, colors):
            shape = tuple(tuple(cell) for cell in member["shape"])
            if shape not in shapes_seen:
                shapes_seen.add(shape)
                component_orbits.append(member)
    agent_colors = sorted({
        int(cell[2])
        for member in component_orbits
        for cell in member["shape"]
    })
    reactive_field = _reactive_field(rows, component_orbits)
    boundary = sorted(all_colors - ever_changed)
    # Monotonicity is local to a lifecycle segment.  Epoch identity is supplied
    # by the adapter; clock rollback is retained solely for legacy banks.
    lifecycle_segments = _lifecycle_segments(rows)
    def _monotone_depleting(c):
        depleted = False
        for indices in lifecycle_segments:
            seg = [counts_by_color[c][index] for index in indices]
            if not all(x >= y for x, y in zip(seg, seg[1:])):
                return False
            if len(set(seg)) > 1:
                depleted = True
        return depleted
    resource = sorted(c for c in all_colors
                      if c not in agent_colors and _monotone_depleting(c))
    roles = []
    if component_orbits:
        roles.append(Role(
            "moves_under_actions",
            component_orbits,
            f"{len(component_orbits)} translated component orbit(s); "
            f"feature evidence in {sum(moved_colors[c] for c in agent_colors)} transitions",
        ))
    if resource:
        roles.append(Role("monotone_depleting", resource,
                          "global count strictly non-increasing with decreases"))
    if boundary:
        roles.append(Role("never_changes", boundary, "unchanged in every transition"))
    if reactive_field:
        roles.append(Role(
            "covered_uncovered",
            [reactive_field],
            "evidence-localized field exposed or covered by a translated component",
        ))

    # indicator: static components with the agent's color signature
    if agent_colors:
        g0 = rows[0].s
        agent_sig = tuple(sorted(agent_colors))
        static_mirrors = 0
        for comp in _components(g0, set(agent_colors)):
            cells = {(y, x) for (y, x) in comp}
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

      controlled support -> component-orbit origins (legacy: mover-color cells)
      monotone quantity  -> per-feature global counts
      reactive support   -> exact cells of covered/uncovered features
      invariant support  -> dropped (never changes; carries no state)
    """
    role_by_name = {r.name: r for r in roles}
    agent = frozenset()
    if "moves_under_actions" in role_by_name:
        mover_role = role_by_name["moves_under_actions"]
        orbit_members = _component_orbit_members(mover_role)
        if orbit_members:
            located = []
            for member_index, member in enumerate(orbit_members):
                shape = tuple(tuple(int(value) for value in cell)
                              for cell in member["shape"])
                colors = {cell[2] for cell in shape}
                for observed_shape, origins in _component_images(grid, colors).items():
                    if observed_shape == shape:
                        located.extend(
                            (member_index, int(y), int(x)) for y, x in origins
                        )
            agent = frozenset(located)
        else:
            # Compatibility for substrate adapters and historical receipts that
            # still represent the mover role as a list of scalar features.
            ac = {member for member in mover_role.members
                  if isinstance(member, int) and not isinstance(member, bool)}
            agent = frozenset(
                (y, x) for y in range(len(grid)) for x in range(len(grid[0]))
                if grid[y][x] in ac
            )
    resource = ()
    if "monotone_depleting" in role_by_name:
        resource = tuple(sorted(
            (c, sum(1 for row in grid for v in row if v == c))
            for c in role_by_name["monotone_depleting"].members))
    reactive = frozenset()
    if "covered_uncovered" in role_by_name:
        reactive_role = role_by_name["covered_uncovered"]
        field_members = _reactive_field_members(reactive_role)
        if field_members:
            deviations = []
            for member_index, member in enumerate(field_members):
                for y, x, baseline in member["baseline"]:
                    observed = int(grid[int(y)][int(x)])
                    if observed != int(baseline):
                        deviations.append(
                            (member_index, int(y), int(x), observed)
                        )
            reactive = frozenset(deviations)
        else:
            rc = {member for member in reactive_role.members
                  if isinstance(member, int) and not isinstance(member, bool)}
            reactive = frozenset(
                (y, x, grid[y][x])
                for y in range(len(grid)) for x in range(len(grid[0]))
                if grid[y][x] in rc
            )
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
