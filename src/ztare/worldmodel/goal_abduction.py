"""Dynamic goal abduction for the grid world-model (GP-250).

The reachability sweep needs a goal predicate, but a sealed agent is handed no
goal. This module abduces candidate goals from evidence alone, two-phase:

  PRE-SUCCESS (no level-complete witnessed yet) — structural hypotheses about
    what the environment is FOR, read straight off the spec + roles:
      (a) DORMANT EVENTS: a region_event rule whose learned write has never been
          observed firing in the log — making it fire is a candidate goal;
      (b) NEVER-VISITED INDICATOR STATES: indicator-role cells (covered/uncovered
          or static mirrors) that are rule write-targets yet never changed in
          evidence — changing them is a candidate goal.

  POST-SUCCESS (level-complete discontinuities present) — a completion is an
    env frame whose s_next shows a monotone-resource REFILL. Take the K frames
    before each completion, and intersect which regions changed-vs-episode-start
    consistently in EVERY pre-completion window; that intersection is the
    recurring goal region.

All shapes are substrate-general: regions, roles, and monotone facts are derived
from the evidence — no ls20 (or any level) constants.
"""
from __future__ import annotations

DEFAULT_K = 3


# ── role / spec normalisation (tolerant of AbstractState, list, or dict) ──────

def _role_seq(roles):
    if roles is None:
        return []
    return getattr(roles, "roles", roles) or []


def _role_members(roles, *names):
    got: set[int] = set()
    for r in _role_seq(roles):
        name = getattr(r, "name", None)
        members = getattr(r, "members", None)
        if name is None and isinstance(r, dict):
            name, members = r.get("name"), r.get("members")
        if name not in names or not members:
            continue
        for m in members:
            if isinstance(m, bool):
                continue
            if isinstance(m, int):
                got.add(int(m))
            elif isinstance(m, (list, tuple)):        # e.g. a mirror color signature
                got.update(int(x) for x in m if isinstance(x, int))
    return sorted(got)


def _norm_spec(spec):
    if isinstance(spec, dict):
        return spec
    inner = getattr(spec, "spec", None)
    return inner if isinstance(inner, dict) else {}


def _all_rules(spec):
    out = []
    for rules in (spec.get("actions") or {}).values():
        out.extend(rules or [])
    out.extend(spec.get("always") or [])
    return out


def _in(g, y, x):
    return 0 <= y < len(g) and 0 <= x < len(g[0])


# ── completion detection (defensive import of gates.env_frame_indices) ────────

def _res_count(grid, resource):
    rc = set(resource)
    return sum(1 for row in grid for c in row if c in rc)


def _color_counts(grid):
    from collections import Counter
    c = Counter()
    for row in grid:
        c.update(row)
    return c


def _horizon_resource(rows):
    """The horizon resource: the color that DECREMENTS in more than half the
    transitions (same rule the gates use to find the timer bar). One color or
    None — evidence-derived, no constants."""
    from collections import Counter
    down: Counter = Counter()
    for tr in rows:
        cs, cn = _color_counts(tr.s), _color_counts(tr.s_next)
        for c in set(cs) | set(cn):
            if cn[c] - cs[c] < 0:
                down[c] += 1
    if not down:
        return None
    cand, n = down.most_common(1)[0]
    return cand if n > len(rows) / 2 else None


def _completions(rows, resource):
    """Indices whose s_next shows a monotone-resource refill (count increases) —
    a level-complete/level-up. Corroborated with the gates' discontinuity set
    when that import is available and non-empty; else refill alone."""
    refill = [i for i, tr in enumerate(rows)
              if _res_count(tr.s_next, resource) > _res_count(tr.s, resource)]
    env = set()
    try:
        from ztare.worldmodel.episode_log import EpisodeLog
        from ztare.worldmodel.gates import env_frame_indices
        env = set(env_frame_indices(EpisodeLog(list(rows))))
    except Exception:  # noqa: BLE001 — gates API in flux; refill signal stands
        env = set()
    if env:
        both = [i for i in refill if i in env]
        if both:
            return both
    return refill


# ── entry point ──────────────────────────────────────────────────────────────

def abduce_goal_candidates(log, spec, roles) -> dict:
    rows = list(log)
    spec = _norm_spec(spec)
    resource = _role_members(roles, "monotone_depleting")
    completions = _completions(rows, resource) if (resource and rows) else []
    if completions:
        return _post_success(rows, resource, completions)
    return _pre_success(rows, spec, roles)


# ── pre-success ──────────────────────────────────────────────────────────────

def _event_fired(rows, cells):
    """Did the write ever land — all write cells at their write color in some
    s_next, and not already so in that s (a real crossing write)?"""
    for tr in rows:
        landed = all(_in(tr.s_next, y, x) and tr.s_next[y][x] == c for (y, x, c) in cells)
        changed = any(not _in(tr.s, y, x) or tr.s[y][x] != c for (y, x, c) in cells)
        if landed and changed:
            return True
    return False


def _constant_positions(rows):
    changed = set()
    for tr in rows:
        for y in range(len(tr.s)):
            for x in range(len(tr.s[0])):
                if tr.s[y][x] != tr.s_next[y][x]:
                    changed.add((y, x))
    H, W = len(rows[0].s), len(rows[0].s[0])
    return {(y, x) for y in range(H) for x in range(W)} - changed


def _event_write_cells(rule) -> "list[tuple]":
    """(y, x, colour) triples a region_event can write: the fixed/toggle `writes`
    plus, for a content_states REGION-STATE MACHINE, every per-state cell value of
    its region — so state-machine displays stay visible to goal abduction (copy
    regions, indicators, dormancy) exactly like written cells."""
    out = [(int(y), int(x), int(c))
           for c, cs in (rule.get("writes") or []) for (y, x) in cs]
    states = rule.get("content_states")
    if states:
        y0, x0, y1, x1 = (int(v) for v in rule["region"])
        cells = [(y, x) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]
        for st in states:
            out += [(y, x, int(c)) for (y, x), c in zip(cells, st)]
    return out


def _write_target_positions(rows, spec):
    pos = set()
    start = rows[0].s
    H, W = len(start), len(start[0])
    for rule in _all_rules(spec):
        op = rule.get("op")
        if op == "region_event":
            pos.update((y, x) for (y, x, _c) in _event_write_cells(rule))
        elif op == "recolor_map":
            froms = {int(k) for k in (rule.get("mapping") or {})}
            pos.update((y, x) for y in range(H) for x in range(W) if start[y][x] in froms)
        elif op == "consume_extremal":
            col = int(rule.get("color", -1))
            pos.update((y, x) for y in range(H) for x in range(W) if start[y][x] == col)
    return pos


def _region(positions):
    ys = [y for y, x in positions]
    xs = [x for y, x in positions]
    return [min(ys), min(xs), max(ys), max(xs)]


def _pre_success(rows, spec, roles) -> dict:
    candidates: list[dict] = []
    # (a) dormant region_events
    for rule in _all_rules(spec):
        if rule.get("op") != "region_event":
            continue
        cells = _event_write_cells(rule)
        if not cells or _event_fired(rows, cells):
            continue
        candidates.append({
            "kind": "dormant_region_event",
            "predicate_spec": {"region": _region([(y, x) for (y, x, _c) in cells]),
                               "differs_from_start": True},
            "rationale": "a region_event write never observed firing in evidence; "
                         "making it fire is a candidate goal",
        })
    # (b) never-visited indicator states that are rule write-targets
    indicator = set(_role_members(roles, "covered_uncovered", "static_structural_mirror"))
    if indicator and rows:
        start = rows[0].s
        cand_pos = sorted(p for p in (_constant_positions(rows) & _write_target_positions(rows, spec))
                          if _in(start, p[0], p[1]) and start[p[0]][p[1]] in indicator)
        if cand_pos:
            candidates.append({
                "kind": "never_visited_indicator",
                "predicate_spec": {"region": _region(cand_pos), "differs_from_start": True},
                "rationale": "indicator-role cells that are rule write-targets never "
                             "changed in evidence; changing them is a candidate goal",
            })
    # (c) dormant conjunctions: indicator regions each witnessed active alone but
    # never simultaneously — co-activating them is a candidate goal
    candidates.extend(_conjunction_candidates(rows, spec))
    # (d) depletion-config goals (linear-logic correspondence: completion = a
    # flag configuration AT resource exhaustion)
    candidates.extend(_depletion_config_candidates(rows, spec))
    # (e) template/copy goals: a static framed pattern box + an agent-mutable copy
    # of the same palette => make the copy match the template (core-knowledge prior)
    candidates.extend(_template_copy_candidates(rows, spec, roles))
    return {"mode": "pre_success", "candidates": candidates}


def _depletion_config_candidates(rows, spec) -> list:
    """Theory-backed pre-success goals: a linear-logic reading predicts a level
    completes when the flag configuration reaches a specific pattern AT the
    moment the horizon resource is exhausted. Emit one candidate per non-trivial
    indicator configuration (each indicator differs-or-matches episode start,
    excluding the all-unchanged config) conjoined with resource==0. Evidence-
    derived: the resource and the indicator regions both come from the log."""
    import itertools
    if not rows:
        return []
    resource = _horizon_resource(rows)
    regions = _indicator_regions(spec)
    # ponytail: cap the config fan-out (2^k - 1); k tiny in practice, bound it
    if resource is None or not regions or len(regions) > 6:
        return []
    out = []
    for combo in itertools.product((True, False), repeat=len(regions)):
        if not any(combo):                             # exclude all-unchanged
            continue
        sub = [{"region": _region(list(cells)), "differs_from_start": changed}
               for cells, changed in zip(regions, combo)]
        sub.append({"resource_zero": int(resource)})
        out.append({
            "kind": "depletion_config",
            "predicate_spec": {"conjunction": sub},
            "rationale": "linear-logic correspondence: completion = this flag "
                         "configuration at resource exhaustion",
        })
    return out


def _indicator_regions(spec):
    """Write-target cell-sets, one per region_event rule (deduped) — the distinct
    indicators the environment can toggle."""
    seen, out = set(), []
    for rule in _all_rules(spec):
        if rule.get("op") != "region_event":
            continue
        cells = tuple(sorted({(y, x) for (y, x, _c) in _event_write_cells(rule)}))
        if cells and cells not in seen:
            seen.add(cells)
            out.append(cells)
    return out


# ── template/copy candidates (core-knowledge: template matching) ──────────────

def _field_colors(grid, min_area=None) -> set:
    """Colours whose largest 4-connected component is a FIELD — big enough to be
    background/frame, not a glyph. Evidence-derived: the threshold scales with the
    grid, so voids, floors, and long bars fall out as background while small
    structured glyphs remain foreground. No colour is hard-coded as background."""
    from ztare.worldmodel.object_roles import _components
    H, W = len(grid), len(grid[0]) if grid else 0
    if min_area is None:
        min_area = 2 * max(H, W) if H else 1
    out: set = set()
    for c in {grid[y][x] for y in range(H) for x in range(W)}:
        comps = _components(grid, {c})
        if comps and max(len(cp) for cp in comps) >= min_area:
            out.add(c)
    return out


def _nonbg_components(grid, bg) -> list:
    """4-connected components of non-background cells (colours adjacent across the
    palette merge — a two-colour glyph is one region)."""
    from ztare.worldmodel.object_roles import _components
    nonbg = {grid[y][x] for y in range(len(grid)) for x in range(len(grid[0]))} - set(bg)
    return _components(grid, nonbg)


def _isolated(grid, cells, frame) -> bool:
    """Every out-of-component 4-neighbour is a frame/background colour (or the grid
    edge) — the region is spatially isolated, not embedded in other structure."""
    H, W = len(grid), len(grid[0])
    for (y, x) in cells:
        for (ny, nx) in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if (ny, nx) in cells:
                continue
            if 0 <= ny < H and 0 <= nx < W and grid[ny][nx] not in frame:
                return False
    return True


def _norm_pattern(grid, rect, bg) -> frozenset:
    """The non-background contents of `rect`, as {(dy, dx, colour)} normalised to
    the content's own top-left — so equality is tolerant to the region's frame /
    offset (a copy in a wider box aligns to the same normalised pattern)."""
    y0, x0, y1, x1 = (int(v) for v in rect)
    H, W = len(grid), len(grid[0]) if grid else 0
    cells = [(y, x) for y in range(max(0, y0), min(H - 1, y1) + 1)
             for x in range(max(0, x0), min(W - 1, x1) + 1) if grid[y][x] not in bg]
    if not cells:
        return frozenset()
    my, mx = min(y for y, x in cells), min(x for y, x in cells)
    return frozenset((y - my, x - mx, grid[y][x]) for (y, x) in cells)


def _template_copy_candidates(rows, spec, roles) -> list:
    """Detect (a) TEMPLATE regions — static, isolated, small, structured non-bg
    glyphs — and (b) COPY regions — cell-sets an event rule mutates — and pair any
    copy/template sharing a palette into a `template_match` goal. Everything
    (background, palettes, geometry) is read from the evidence; no level constants.
    """
    from collections import Counter
    if not rows:
        return []
    start = rows[0].s
    bg = _field_colors(start)
    frame = bg | set(_role_members(roles, "never_changes"))
    consts = _constant_positions(rows)
    templates = []
    for comp in _nonbg_components(start, bg):
        cells = set(comp)
        if not cells <= consts:                        # must be static across evidence
            continue
        ys = [y for y, x in cells]
        xs = [x for y, x in cells]
        if (max(ys) - min(ys) + 1) > 12 or (max(xs) - min(xs) + 1) > 12:
            continue                                   # small
        pal = Counter(start[y][x] for (y, x) in cells)
        if not (len(pal) >= 2 or any(n >= 4 for n in pal.values())):
            continue                                   # structured
        if not _isolated(start, cells, frame):
            continue
        templates.append((cells, set(pal)))
    if not templates:
        return []
    copies = []
    for rule in _all_rules(spec):
        if rule.get("op") != "region_event":
            continue
        triples = _event_write_cells(rule)
        cells = {(y, x) for (y, x, _c) in triples}
        if not cells:
            continue
        pal = {c for (_y, _x, c) in triples}
        pal |= {start[y][x] for (y, x) in cells if _in(start, y, x)}
        pal -= bg
        copies.append((cells, pal))
    out, seen = [], set()
    for (ccells, cpal) in copies:
        for (tcells, tpal) in templates:
            if ccells == tcells or not (cpal & tpal):
                continue
            crect, trect = tuple(_region(sorted(ccells))), tuple(_region(sorted(tcells)))
            if (crect, trect) in seen:
                continue
            seen.add((crect, trect))
            # already-matched at start => nothing to achieve => not a goal (drops a
            # copy sub-shape that coincidentally equals a template)
            if _norm_pattern(start, crect, bg) == _norm_pattern(start, trect, bg):
                continue
            out.append({
                "kind": "template_match",
                "predicate_spec": {"copy_region": list(crect), "template_region": list(trect),
                                   "relation": "content_equal_up_to_alignment",
                                   "background": sorted(bg)},
                "rationale": "static template + agent-mutable copy of same palette => "
                             "goal: make copy match template (core-knowledge prior)",
            })
    return out


def _region_changed(grid, start, cells):
    return any(_in(grid, y, x) and grid[y][x] != start[y][x] for (y, x) in cells)


def _conjunction_candidates(rows, spec) -> list:
    """Indicator regions each witnessed CHANGED-from-start somewhere, but no
    single frame shows a pair (or triple, when <=3 indicators) simultaneously
    changed -> a dormant conjunction goal. Evidence-derived, no level constants."""
    import itertools
    if not rows:
        return []
    start = rows[0].s
    grids = [start] + [tr.s_next for tr in rows]
    witnessed = [cells for cells in _indicator_regions(spec)
                 if any(_region_changed(g, start, cells) for g in grids)]
    if len(witnessed) < 2:
        return []
    combos = list(itertools.combinations(witnessed, 2))
    if len(witnessed) <= 3:
        combos += list(itertools.combinations(witnessed, 3))
    out = []
    for combo in combos:
        if any(all(_region_changed(g, start, cells) for cells in combo) for g in grids):
            continue                                   # co-witnessed -> not dormant
        out.append({
            "kind": "dormant_conjunction",
            "predicate_spec": {"conjunction": [
                {"region": _region(list(cells)), "differs_from_start": True}
                for cells in combo]},
            "rationale": "events witnessed individually, never co-active",
        })
    return out


# ── post-success ─────────────────────────────────────────────────────────────

def _changed_vs(start, grid):
    return {(y, x) for y in range(len(start)) for x in range(len(start[0]))
            if _in(grid, y, x) and grid[y][x] != start[y][x]}


def _post_success(rows, resource, completions, K=DEFAULT_K) -> dict:
    per_completion: list[set] = []
    prev = 0
    for c in completions:
        start = rows[prev].s                       # this episode's start grid
        window = [rows[i] for i in range(max(prev, c - K), c)]
        prev = c + 1
        if not window:
            continue
        # positions that changed-vs-episode-start in EVERY frame of the window
        sets = [_changed_vs(start, tr.s_next) for tr in window]
        per_completion.append(set.intersection(*sets) if sets else set())
    if not per_completion:
        return {"mode": "post_success", "goal_predicate_spec": None, "support": len(completions)}
    goal_pos = set.intersection(*per_completion)
    # the resource bar empties before EVERY completion; it is the timer axis, not
    # the goal (object_roles drops it from the goal signature) -> exclude it
    start0, rc = rows[0].s, set(resource)
    goal_pos = {(y, x) for (y, x) in goal_pos if not (_in(start0, y, x) and start0[y][x] in rc)}
    if not goal_pos:
        return {"mode": "post_success", "goal_predicate_spec": None, "support": len(completions)}
    return {"mode": "post_success",
            "goal_predicate_spec": {"region": _region(goal_pos), "differs_from_start": True},
            "support": len(completions)}


# ── predicate compilation (usable by reachability_sweep goal_fn) ─────────────

def predicate_from_spec(pspec, start_grid, symmetry_group="dihedral"):
    """Compile a predicate_spec to ``goal_fn(grid) -> bool`` with region-differs-
    from-start semantics. A ``conjunction`` spec compiles to the AND of its
    sub-predicates. Fail-closed: a malformed spec / out-of-range grid -> False.

    `symmetry_group` is the SUBSTRATE's shape-symmetry group (2D grids: 'dihedral';
    a 3D voxel substrate would pass its octahedral group; 'identity' = plain
    translation-tolerant equality). template_match compares copy vs template as
    SHAPES under that group — a Core-Knowledge geometry prior: a glyph and its
    rotations/reflections are one object, so a copy that equals the template only
    after a 90° turn still satisfies the goal (translation-only alignment would
    reject it)."""
    if not pspec:
        return lambda g: False
    if pspec.get("conjunction"):
        subs = [predicate_from_spec(sub, start_grid, symmetry_group)
                for sub in pspec["conjunction"]]
        if not subs:
            return lambda g: False
        return lambda g: all(s(g) for s in subs)
    if pspec.get("relation") == "content_equal_up_to_alignment":
        from ztare.worldmodel.symmetry import canonical_form
        bg = {int(c) for c in (pspec.get("background") or [])}
        trect, crect = pspec.get("template_region"), pspec.get("copy_region")
        if not trect or not crect:
            return lambda g: False
        tpat = _norm_pattern(start_grid, trect, bg)
        if not tpat:                                   # empty template => no goal
            return lambda g: False
        tcanon = canonical_form(tpat, symmetry_group)

        def tm_fn(grid):
            try:
                return canonical_form(_norm_pattern(grid, crect, bg), symmetry_group) == tcanon
            except Exception:  # noqa: BLE001 — fail-closed
                return False
        return tm_fn
    if "resource_zero" in pspec:
        color = int(pspec["resource_zero"])

        def zero_fn(grid):
            try:
                return not any(c == color for row in grid for c in row)
            except Exception:  # noqa: BLE001 — fail-closed
                return False
        return zero_fn
    if pspec.get("region") is None:
        return lambda g: False
    y0, x0, y1, x1 = (int(v) for v in pspec["region"])
    differs = bool(pspec.get("differs_from_start", True))
    H = len(start_grid)
    W = len(start_grid[0]) if H else 0
    base = {(y, x): start_grid[y][x]
            for y in range(max(0, y0), min(H - 1, y1) + 1)
            for x in range(max(0, x0), min(W - 1, x1) + 1)}

    def goal_fn(grid):
        try:
            changed = any(grid[y][x] != v for (y, x), v in base.items())
        except Exception:  # noqa: BLE001 — fail-closed
            return False
        return changed if differs else not changed

    return goal_fn
