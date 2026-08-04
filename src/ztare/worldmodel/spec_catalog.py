"""Grid-operation class catalog + deterministic lowering (GP-250).

The third and PREFERRED candidate carrier for interactive substrates:
the mutator SELECTS structural operator classes and parameters (a
WORLD_MODEL_SPEC dict); the KERNEL deterministically lowers the spec to an
executable `step(grid, action, t)`. Evidence basis (epistemic-generation
H32-H39, GP-214/216): free-form program synthesis fails on slips the model's
analysis didn't make; checked class-selection plus deterministic lowering
matched hand-compiled behavior. Applied here: the mutator's failure surface
shrinks to WRONG ANALYSIS (which replay/rollout gates catch cleanly) instead
of right-analysis-buggy-code.

Catalog v1 — only operators witnessed as needed on real evidence (no
speculative ops); names are mathematical operations, never game mechanics:

  translate_block   rigid translation of all cells whose color is in
                    `match_colors` by (dy, dx), iff every destination cell
                    outside the moving set has a color in
                    `require_dest_colors`; vacated cells become `fill_color`;
                    on guard failure the rule is a no-op (refusal)
  recolor_map       global recolor by an explicit color mapping
  consume_extremal  per row (or column) containing `color`, recolor the
                    minimum- or maximum-index cell of that color to
                    `replacement`. Optional "rate": [p, q] consumes
                    floor((t+1)*p/q)-floor(t*p/q) cells on step t. Optional
                    "component_scope" restricts the extremal update to
                    selected 4-connected components.
  accumulate_extremal  the mirror of consume_extremal: per row (or column),
                    fill the minimum- or maximum-index EMPTY cell (value
                    `from`, default background 0) with `color` — a progress
                    bar / counter that GROWS. Behaviorally the transpose of
                    consume_extremal (accumulate color=W from=E == consume
                    color=E replacement=W: both set an extremal cell of one
                    value to another), kept as a distinct name so a filling
                    bar reads as accumulation in specs, briefings, receipts
  region_event      on a mover crossing either an adapter-local rect or any
                    occurrence of a finite trigger pattern, write a learned
                    cell-set to learned colors
  bind_region_value copy one source-state value onto the support selected by
                    an expected current value inside an output region
  identity          explicit no-op

Spec shape (JSON-able; all colors are ints):

  WORLD_MODEL_SPEC = {
    "actions": {"0": [rule, ...], "1": [...], ...},   # rules for the action taken
    "always":  [rule, ...],                            # rules applied every step
  }

Rules run in order (action rules, then always-rules). Any rule may carry
"when_t_mod": [k, r] to fire only when t % k == r. Lowering is fail-closed:
a malformed spec returns (None, error) and never a wrong executable.
"""

from __future__ import annotations

import os

from ztare.worldmodel.grid_dsl import Grid

_ALLOWED_OPS = ("translate_block", "recolor_map", "consume_extremal",
                "accumulate_extremal", "region_event", "bind_region_value",
                "pattern_write", "identity")

# ---- _match_components memo (the abduction floor) ---------------------------
# Component extraction is a PURE function of (grid content, match colours): the
# same content always yields the same components, so a content-keyed cache is
# byte-safe with no staleness — grids are logically immutable at call time and
# the returned comps are only ever read downstream (never mutated). The win is
# cross-candidate reuse: abduce_spec replays every candidate spec over the same
# ~1290 step-start grids, so `step(tr.s, ...)` re-extracts the SAME
# (grid, mover_colours) components thousands of times. Keyed on tr.s's own
# tuple object where possible (no copy), else the tuple-ified mutable grid.
# ponytail: clear-on-overflow bound (dict is simplest; upgrade to LRU only if a
# measured hit-rate drop shows the working set exceeds the cap).
_MC_MEMO: "dict[tuple, list]" = {}
_MC_MEMO_CAP = 200_000
_MC_MEMO_ON = os.environ.get("ZTARE_MC_MEMO", "1") != "0"   # A/B control for equivalence proof
_MC_HITS = 0
_MC_MISS = 0

_PATTERN_RECT_MEMO: "dict[tuple, tuple[tuple[int, int, int, int], ...]]" = {}
_PATTERN_RECT_MEMO_CAP = 100_000
_UNDEFINED_OPERATION_IMAGE = object()


def _match_components(g: "list[list[int]]", match: set) -> "list[list[tuple]]":
    """4-connected components of cells whose color is in `match` — shared by the
    translate apply and the when_dest relational guard. Memoized on grid content
    + match colours (see module note); disable with ZTARE_MC_MEMO=0."""
    global _MC_HITS, _MC_MISS
    if _MC_MEMO_ON:
        key = (g if type(g) is tuple else tuple(map(tuple, g)), frozenset(match))
        hit = _MC_MEMO.get(key)
        if hit is not None:
            _MC_HITS += 1
            return hit
        _MC_MISS += 1
    h, w = len(g), len(g[0])
    is_match = [[g[y][x] in match for x in range(w)] for y in range(h)]
    seen = [[False] * w for _ in range(h)]
    comps = []
    for y0 in range(h):
        for x0 in range(w):
            if not is_match[y0][x0] or seen[y0][x0]:
                continue
            comp, stack = [], [(y0, x0)]
            seen[y0][x0] = True
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for ny, nx in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
                    if 0 <= ny < h and 0 <= nx < w and is_match[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            comps.append(comp)
    if _MC_MEMO_ON:
        if len(_MC_MEMO) >= _MC_MEMO_CAP:
            _MC_MEMO.clear()
        _MC_MEMO[key] = comps
    return comps


def _qualifying_components(g, rule) -> "list[list[tuple]]":
    """Components passing the rule's optional selection predicates (general,
    inferable from diffs): a rule may require the moving component to carry at
    least K distinct colors / cells — e.g. a two-color object moves while
    single-color decorations of the same palette stay."""
    out = []
    for comp in _match_components(g, set(rule["match_colors"])):
        if len(comp) < int(rule.get("component_min_size", 1)):
            continue
        if len({g[y][x] for (y, x) in comp}) < int(rule.get("component_min_colors", 1)):
            continue
        out.append(comp)
    return out


def _dest_holds(g, ref_rule, colors) -> bool:
    """RELATIONAL destination predicate: does any destination cell of the
    referenced translate rule's qualifying components — each cell displaced by
    that rule's OWN (dy, dx), excluding cells inside the component — hold a
    color in `colors`? Anchored to the object's CURRENT location and the
    action's OWN learned displacement: no absolute coordinates, no frame
    index, no environment constants."""
    dy, dx = int(ref_rule["dy"]), int(ref_rule["dx"])
    cs = {int(c) for c in colors}
    h, w = len(g), len(g[0])
    for comp in _qualifying_components(g, ref_rule):
        src = set(comp)
        for (y, x) in comp:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and (ny, nx) not in src and g[ny][nx] in cs:
                return True
    return False


def _apply_translate_block(g: "list[list[int]]", rule: dict) -> "list[list[int]]":
    """Per-connected-component guarded translation: each 4-connected component
    of matching cells moves independently iff every destination cell outside
    the component is an allowed color; a blocked component stays (refusal).
    Component scoping is what lets one moving object coexist with static
    same-colored decorations elsewhere on the grid — the decorations refuse
    because THEIR destinations are not floor."""
    match = set(rule["match_colors"])
    dy, dx = int(rule["dy"]), int(rule["dx"])
    dest_ok = set(rule["require_dest_colors"])
    fill = rule["fill_color"] if rule.get("fill_color") == "surround" else int(rule["fill_color"])
    h, w = len(g), len(g[0])
    out = [row[:] for row in g]
    for comp in _qualifying_components(g, rule):
        src = set(comp)
        ok = True
        for (y, x) in comp:
            ny, nx = y + dy, x + dx
            if not (0 <= ny < h and 0 <= nx < w):
                ok = False
                break
            if (ny, nx) not in src and g[ny][nx] not in dest_ok:
                ok = False
                break
        if not ok:
            continue                                # this component refuses
        for (y, x) in comp:
            if rule.get("fill_color") == "surround":
                # terrain restoration: the vacated cell takes the majority
                # color of its non-moving neighbors (frame-computable, no
                # history) — sprite-over-background worlds restore terrain
                from collections import Counter as _C
                neigh = [g[ny][nx] for ny, nx in
                         ((y-1,x),(y+1,x),(y,x-1),(y,x+1),(y-1,x-1),(y-1,x+1),(y+1,x-1),(y+1,x+1))
                         if 0 <= ny < h and 0 <= nx < w and (ny, nx) not in src
                         and g[ny][nx] not in match]
                out[y][x] = _C(neigh).most_common(1)[0][0] if neigh else 0
            else:
                out[y][x] = fill
        for (y, x) in comp:
            out[y + dy][x + dx] = g[y][x]
    return out


def _apply_recolor_map(g: "list[list[int]]", rule: dict) -> "list[list[int]]":
    mapping = {int(k): int(v) for k, v in rule["mapping"].items()}
    return [[mapping.get(c, c) for c in row] for row in g]


def _rate_count(rule: dict, t: int) -> int:
    if "rate" not in rule:
        return int(rule.get("count", 1))
    p, q = int(rule["rate"][0]), int(rule["rate"][1])
    tt = int(t)
    return ((tt + 1) * p) // q - (tt * p) // q


def _component_box(comp):
    ys = [y for y, _x in comp]
    xs = [x for _y, x in comp]
    return min(ys), min(xs), max(ys), max(xs)


def _selected_component_scope_cells(g, rule, default_colors) -> "set[tuple[int, int]] | None":
    """Optional quotient restriction for extremal rules.

    The rule first quotients the 2D grid into 4-connected components of the
    declared colours, filters by structural predicates, then applies the
    extremal write only inside the selected quotient class(es). This is the
    grid lowering of a substrate-neutral quotient idea: no game names, no level
    constants, and coordinates appear only as this substrate's representation.
    """
    scope = rule.get("component_scope")
    if scope is None:
        return None
    colors = {int(c) for c in scope.get("colors", default_colors)}
    comps = []
    for comp in _match_components(g, colors):
        y0, x0, y1, x1 = _component_box(comp)
        if len(comp) < int(scope.get("min_size", 1)):
            continue
        if (x1 - x0 + 1) < int(scope.get("min_width", 1)):
            continue
        if (y1 - y0 + 1) < int(scope.get("min_height", 1)):
            continue
        if len({g[y][x] for (y, x) in comp}) < int(scope.get("min_colors", 1)):
            continue
        comps.append(comp)
    if not comps:
        return set()
    select = scope.get("select", "all")
    if select == "largest":
        m = max(len(c) for c in comps)
        comps = [c for c in comps if len(c) == m]
    elif select == "widest":
        m = max(_component_box(c)[3] - _component_box(c)[1] + 1 for c in comps)
        comps = [c for c in comps if (_component_box(c)[3] - _component_box(c)[1] + 1) == m]
    elif select != "all":
        raise ValueError(f"bad component_scope select {select!r}")
    return {(y, x) for comp in comps for (y, x) in comp}


def _apply_consume_extremal(g: "list[list[int]]", rule: dict, t: int = 0) -> "list[list[int]]":
    color, repl = int(rule["color"]), int(rule["replacement"])
    axis = rule.get("axis", "row")
    extreme = rule.get("extreme", "min")
    count = _rate_count(rule, t)
    scope = _selected_component_scope_cells(g, rule, {color})
    return _apply_extremal_k(g, color, repl, axis, extreme, count, scope)


def _apply_extremal_k(g, match, write, axis, extreme, count, scope_cells=None):
    out = [row[:] for row in g]
    n = int(count)
    if n <= 0:
        return out
    if axis == "row":
        allowed = None if scope_cells is None else set(scope_cells)
        for y, row in enumerate(out):
            idxs = [x for x, c in enumerate(row)
                    if c == match and (allowed is None or (y, x) in allowed)]
            if idxs:
                for x in (idxs[:n] if extreme == "min" else idxs[-n:]):
                    out[y][x] = write
    else:
        allowed = None if scope_cells is None else set(scope_cells)
        w = len(out[0])
        for x in range(w):
            idxs = [y for y in range(len(out))
                    if out[y][x] == match and (allowed is None or (y, x) in allowed)]
            if idxs:
                for y in (idxs[:n] if extreme == "min" else idxs[-n:]):
                    out[y][x] = write
    return out


def _apply_consume_extremal_once(out, color, repl, axis, extreme):
    if axis == "row":
        for y, row in enumerate(out):
            idxs = [x for x, c in enumerate(row) if c == color]
            if idxs:
                out[y][min(idxs) if extreme == "min" else max(idxs)] = repl
    else:
        w = len(out[0])
        for x in range(w):
            idxs = [y for y in range(len(out)) if out[y][x] == color]
            if idxs:
                out[min(idxs) if extreme == "min" else max(idxs)][x] = repl
    return out


def _apply_accumulate_extremal(g: "list[list[int]]", rule: dict, t: int = 0) -> "list[list[int]]":
    """Mirror of consume_extremal: per row (or column), fill the min/max-index
    EMPTY cell (value `from`, default background 0) with `color`, `count` times
    per firing — a progress bar / counter that grows (the depleting timer's
    mirror). Reuses the same extremal-set primitive with (match, write) swapped:
    accumulate is exactly `set the extremal-index cell of value `from` to
    `color``, so accumulate(color=W, from=E) == consume(color=E, replacement=W)."""
    color, empty = int(rule["color"]), int(rule.get("from", 0))
    axis = rule.get("axis", "row")
    extreme = rule.get("extreme", "min")
    count = _rate_count(rule, t)
    scope = _selected_component_scope_cells(g, rule, {empty})
    return _apply_extremal_k(g, empty, color, axis, extreme, count, scope)


def _overlap(g, cols, rect) -> bool:
    """Any cell of `cols` inside the inclusive rect (clamped to the grid)?"""
    y0, x0, y1, x1 = rect
    h, w = len(g), len(g[0])
    for y in range(max(0, int(y0)), min(h - 1, int(y1)) + 1):
        for x in range(max(0, int(x0)), min(w - 1, int(x1)) + 1):
            if g[y][x] in cols:
                return True
    return False


def _trigger_pattern_rects(g, trigger_pattern):
    """Return every window carrying one finite adapter presentation.

    The pattern is a coordinate-free identity within the grid adapter.  Its
    discovered locations are presentation coordinates used only during this
    execution.  Content-keyed memoization avoids rescanning repeated states.
    """

    shape = trigger_pattern.get("shape")
    values = trigger_pattern.get("values")
    ph, pw = int(shape[0]), int(shape[1])
    pattern_rows = tuple(
        tuple(int(value) for value in values[offset : offset + pw])
        for offset in range(0, len(values), pw)
    )
    grid_key = tuple(tuple(row) for row in g)
    key = (grid_key, ph, pw, pattern_rows)
    cached = _PATTERN_RECT_MEMO.get(key)
    if cached is not None:
        return cached
    height = len(grid_key)
    width = len(grid_key[0]) if height else 0
    rects = tuple(
        (row, col, row + ph - 1, col + pw - 1)
        for row in range(max(0, height - ph + 1))
        for col in range(max(0, width - pw + 1))
        if all(
            grid_key[row + dy][col : col + pw] == pattern_rows[dy]
            for dy in range(ph)
        )
    )
    if len(_PATTERN_RECT_MEMO) >= _PATTERN_RECT_MEMO_CAP:
        _PATTERN_RECT_MEMO.clear()
    _PATTERN_RECT_MEMO[key] = rects
    return rects


def _pattern_overlaps_rect(g, pattern, rect) -> bool:
    y0, x0, y1, x1 = (int(value) for value in rect)
    return any(
        not (py1 < y0 or y1 < py0 or px1 < x0 or x1 < px0)
        for py0, px0, py1, px1 in _trigger_pattern_rects(g, pattern)
    )


def _perm_from_rule(rule) -> dict:
    """Colour permutation map from a toggle/cycle spec. `cycle`: [[c1,c2,c3],...]
    rotates c1->c2->c3->c1; `toggle`: [[c1,c2],...] is the 2-cycle special case
    (both spellings kept). Empty dict => the event is a fixed write, not a
    permutation. Switches, latches, doors, and phase-inverted HUDs are all one
    operator: a colour permutation over a fixed cell-set on crossing."""
    perm: dict = {}
    for cyc in rule.get("cycle", []) or []:
        cyc = [int(c) for c in cyc]
        for i, c in enumerate(cyc):
            perm[c] = cyc[(i + 1) % len(cyc)]
    for pair in rule.get("toggle", []) or []:
        a, b = int(pair[0]), int(pair[1])
        perm[a], perm[b] = b, a
    return perm


def _next_state_index(idx, rule) -> "int | None":
    """Successor state of a content-states region machine. `state_transition`:
    'cycle' advances idx -> (idx+1) mod k (a simple ring); a list of [from, to]
    pairs is the general mined GRAPH form (direction-dependent switches, resets,
    partial maps). An index with no outgoing edge returns None -> the rule
    fail-closes (leaves the region untouched) rather than guessing."""
    tr = rule.get("state_transition", "cycle")
    if tr == "cycle":
        return (idx + 1) % len(rule["content_states"])
    for f, t in tr:
        if int(f) == idx:
            return int(t)
    return None


def region_event_triggered(g0, g, rule) -> bool:
    """Whether one adapter-local crossing relation occurs.

    This is the identity-bearing trigger shared by execution and active
    discrimination.  Its coordinates remain a presentation supplied by the
    interactive-grid adapter; callers may use it to choose an experiment, but
    it grants no carrier or task authority.
    """

    cols = {int(c) for c in rule["mover_colors"]}
    edge = rule.get("edge", "exit")
    trigger_pattern = rule.get("trigger_pattern")
    mover_pattern = rule.get("mover_pattern")

    def mover_overlaps(grid, rect) -> bool:
        if mover_pattern is not None:
            return _pattern_overlaps_rect(grid, mover_pattern, rect)
        return _overlap(grid, cols, rect)

    if trigger_pattern is not None:
        # On arrival the unoccluded presentation is visible at step start; on
        # departure it is visible in the consequence.  This is a partial
        # object transport, not a translation of the entire world or its
        # remote consequence object.
        presentation = g0 if edge == "enter" else g
        rects = _trigger_pattern_rects(presentation, trigger_pattern)
        return any(
            (
                not mover_overlaps(g0, rect)
                and mover_overlaps(g, rect)
            )
            if edge == "enter"
            else (
                mover_overlaps(g0, rect)
                and not mover_overlaps(g, rect)
            )
            for rect in rects
        )
    rect = rule["rect"]
    before, after = mover_overlaps(g0, rect), mover_overlaps(g, rect)
    return (before and not after) if edge == "exit" else ((not before) and after)


def _apply_region_event(g, rule, g0):
    """A region-crossing event: iff the mover crossed the rect between the
    step-start grid `g0` and the current (post-action) grid `g` in the named
    direction, update a target region. Three write families, in MDL order:
    a fixed write (paint learned cell-sets to learned colors), a PERMUTE
    (toggle/cycle a cell-wise colour permutation), or a REGION-STATE MACHINE
    (`content_states`): the target `region`'s whole-content is matched to one of
    k learned glyph patterns and advanced to the next per `state_transition`.
    The state machine is the ONLY family that fits a display whose glyph SHIFTS
    (not recolours) on each crossing — cell-wise functions are provably
    inconsistent there, since one crossing must write different cells by phase.
    `edge`: 'exit' = mover in the rect at step-start but gone after the move
    (terrain restored / plate released); 'enter' = the reverse."""
    if not region_event_triggered(g0, g, rule):
        return g
    states = rule.get("content_states")
    if states is not None:
        # REGION-STATE MACHINE: match the region's CURRENT content to a known
        # glyph, advance, and rewrite. Unknown content or no outgoing edge ->
        # fail-closed (the crossing is real but this machine can't place it).
        ry0, rx0, ry1, rx1 = (int(v) for v in rule["region"])
        h, w = len(g), len(g[0])
        # match the STEP-START content (g0): the glyph advances from the phase it
        # held before this step's rules ran — immune to a superseded fixed-write
        # over the same cells earlier in the chain, and the timing-correct reading
        # of the switch's own state.
        cur = tuple(g0[y][x] for y in range(ry0, ry1 + 1) for x in range(rx0, rx1 + 1)
                    if 0 <= y < h and 0 <= x < w)
        idx = next((k for k, st in enumerate(states) if tuple(st) == cur), None)
        if idx is None:
            return g
        nxt = _next_state_index(idx, rule)
        if nxt is None:
            return _UNDEFINED_OPERATION_IMAGE
        out = [row[:] for row in g]
        st, k = states[nxt], 0
        for y in range(ry0, ry1 + 1):
            for x in range(rx0, rx1 + 1):
                if 0 <= y < h and 0 <= x < w:
                    out[y][x] = int(st[k])
                k += 1
        return out
    out = [row[:] for row in g]
    h, w = len(out), len(out[0])
    perm = _perm_from_rule(rule)
    if perm:
        # toggle/cycle: permute over the event's cell-set (the writes cells);
        # correct on EVERY crossing regardless of current phase — a fixed write
        # is wrong on half the crossings of a state-dependent switch
        for _color, cells in rule["writes"]:
            for (y, x) in cells:
                y, x = int(y), int(x)
                if 0 <= y < h and 0 <= x < w and out[y][x] in perm:
                    out[y][x] = perm[out[y][x]]
        return out
    for color, cells in rule["writes"]:
        for (y, x) in cells:
            if 0 <= int(y) < h and 0 <= int(x) < w:
                out[int(y)][int(x)] = int(color)
    return out


def _apply_bind_region_value(g, rule, g0):
    """Bind a carrier-output value to a source-state value by relation.

    ``target_rect`` is an adapter presentation.  ``source_offset`` is measured
    from its top-left corner, so palette identity is transported without
    embedding the observed color as the write value.  The current-value
    selector preserves the region's complement, so the operation transports a
    sparse mask as well as a dense rectangle.
    """

    y0, x0, y1, x1 = (int(value) for value in rule["target_rect"])
    dy, dx = (int(value) for value in rule["source_offset"])
    expected = int(rule["expected_current"])
    height = len(g)
    width = len(g[0]) if height else 0
    source_y, source_x = y0 + dy, x0 + dx
    if (
        not (0 <= source_y < len(g0) and 0 <= source_x < len(g0[source_y]))
        or y0 < 0
        or x0 < 0
        or y1 >= height
        or x1 >= width
        or y1 < y0
        or x1 < x0
    ):
        return g
    support = tuple(
        (row, col)
        for row in range(y0, y1 + 1)
        for col in range(x0, x1 + 1)
        if g[row][col] == expected
    )
    if not support:
        return g
    bound = g0[source_y][source_x]
    out = [row[:] for row in g]
    for row, col in support:
        out[row][col] = bound
    return out


def _apply_pattern_write(g: "list[list[int]]", rule: dict) -> "list[list[int]]":
    """Write a learned constant pattern to a rect (row-major).

    The RESTORATION family: a bounded region rewrites to remembered content
    (refills, respawns, display resets, terrain restores). The pattern is a
    learned constant — mined from recurring identical diffs — so the carrier
    stays a pure function of (state, action, t). Firing conditions come from
    the generic guard set (when_count / when_region / when_action / ...);
    unguarded, it fires every step, which the assembler's replay check will
    reject unless that is actually the law. MDL: the pattern's cell count is
    the rule's honest description length, so smaller laws still win ties.
    """
    y0, x0, y1, x1 = (int(v) for v in rule["rect"])
    pat = rule["pattern"]
    out = [row[:] for row in g]
    h, w = len(out), len(out[0])
    k = 0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if k >= len(pat):
                return out
            if 0 <= y < h and 0 <= x < w:
                out[y][x] = int(pat[k])
            k += 1
    return out


_APPLY = {
    "translate_block": _apply_translate_block,
    "recolor_map": _apply_recolor_map,
    "consume_extremal": _apply_consume_extremal,
    "accumulate_extremal": _apply_accumulate_extremal,
    "pattern_write": _apply_pattern_write,
    "identity": lambda g, rule: g,
}

_REQUIRED_FIELDS = {
    "translate_block": ("match_colors", "dy", "dx", "require_dest_colors", "fill_color"),
    "recolor_map": ("mapping",),
    "consume_extremal": ("color", "replacement"),
    "accumulate_extremal": ("color",),
    "region_event": ("mover_colors", "edge"),
    "bind_region_value": ("target_rect", "source_offset", "expected_current"),
    "pattern_write": ("rect", "pattern"),
    "identity": (),
}


def _validate_spec(spec, *, require_action_rules: bool) -> "str | None":
    """Validate one catalog presentation without conflating its carrier role."""
    if not isinstance(spec, dict):
        return "spec is not a dict"
    if not isinstance(spec.get("actions"), dict):
        return "spec.actions must be a dict of action_id -> [rules]"
    if require_action_rules and not spec["actions"]:
        return "spec.actions must be a non-empty dict of action_id -> [rules]"
    all_rules = [r for rules in spec["actions"].values() for r in (rules or [])]
    all_rules += list(spec.get("always") or [])
    if not all_rules:
        return "spec carries no rules"
    for r in all_rules:
        if not isinstance(r, dict) or r.get("op") not in _ALLOWED_OPS:
            return f"unknown op in rule: {r!r:.80}"
        missing = [f for f in _REQUIRED_FIELDS[r["op"]] if f not in r]
        if missing:
            return f"rule {r['op']} missing fields {missing}"
        rate = r.get("rate")
        if rate is not None:
            if r["op"] not in ("consume_extremal", "accumulate_extremal"):
                return f"rule {r['op']} has unsupported rate {rate!r}"
            if "count" in r:
                return f"rule {r['op']} cannot carry both count and rate"
            if (not isinstance(rate, (list, tuple)) or len(rate) != 2
                    or not all(isinstance(v, int) for v in rate)
                    or int(rate[0]) < 0 or int(rate[1]) <= 0):
                return f"rule {r['op']} has malformed rate {rate!r}"
        scope = r.get("component_scope")
        if scope is not None:
            if r["op"] not in ("consume_extremal", "accumulate_extremal"):
                return f"rule {r['op']} has unsupported component_scope {scope!r}"
            if not isinstance(scope, dict):
                return f"rule {r['op']} has malformed component_scope {scope!r}"
            colors = scope.get("colors")
            if colors is not None and (not isinstance(colors, (list, tuple)) or not colors
                                       or not all(isinstance(c, int) for c in colors)):
                return f"rule {r['op']} has malformed component_scope colors {colors!r}"
            if scope.get("select", "all") not in ("all", "largest", "widest"):
                return f"rule {r['op']} has bad component_scope select {scope.get('select')!r}"
            for k in ("min_size", "min_width", "min_height", "min_colors"):
                if k in scope and (not isinstance(scope[k], int) or int(scope[k]) <= 0):
                    return f"rule {r['op']} has malformed component_scope {k}={scope[k]!r}"
        wc = r.get("when_count")
        if wc is not None and (not isinstance(wc, (list, tuple)) or len(wc) != 3):
            return f"rule {r['op']} has malformed when_count {wc!r}"
        wo = r.get("when_overlap")
        if wo is not None and (not isinstance(wo, (list, tuple)) or len(wo) not in (5, 6)
                               or not isinstance(wo[0], (list, tuple))
                               or (len(wo) == 6 and not isinstance(wo[5], (list, tuple)))):
            return f"rule {r['op']} has malformed when_overlap {wo!r}"
        wa = r.get("when_action")
        if wa is not None and (not isinstance(wa, (list, tuple)) or not wa
                               or not all(isinstance(a, int) for a in wa)):
            return f"rule {r['op']} has malformed when_action {wa!r}"
        tm = r.get("when_t_mod")
        if tm is not None and (not isinstance(tm, (list, tuple)) or len(tm) != 2
                               or int(tm[0]) <= 0):
            return f"rule {r['op']} has malformed when_t_mod {tm!r}"
        # when_phase [m, r] is a periodic gate identical to when_t_mod (fires iff
        # t % m == r); a second spelling for the blinker/clock family
        wp = r.get("when_phase")
        if wp is not None and (not isinstance(wp, (list, tuple)) or len(wp) != 2
                               or int(wp[0]) <= 0):
            return f"rule {r['op']} has malformed when_phase {wp!r}"
        # when_region [y0, x0, y1, x1, pattern]: fires only when the rect's
        # step-start contents equal the learned pattern (row-major cell values)
        wr = r.get("when_region")
        if wr is not None and (not isinstance(wr, (list, tuple)) or len(wr) != 5
                               or not isinstance(wr[4], (list, tuple))):
            return f"rule {r['op']} has malformed when_region {wr!r}"
        # when_effect [ref_id, True|False]: a RULE-COUPLING gate — this rule
        # fires iff the rule with `id == ref_id` DID (True) / DIDN'T (False) fire
        # (changed the grid) EARLIER this step. `ref_id` must be a str/int id
        # carried by an earlier rule in the chain (action rules run before
        # always-rules); "fired" is the same applied-tracking stop_if_applied uses.
        we = r.get("when_effect")
        if we is not None and (not isinstance(we, (list, tuple)) or len(we) != 2
                               or not isinstance(we[0], (str, int))
                               or not isinstance(we[1], bool)):
            return f"rule {r['op']} has malformed when_effect {we!r}"
        rid = r.get("id")
        if rid is not None and not isinstance(rid, (str, int)):
            return f"rule {r['op']} has malformed id {rid!r}"
        # when_dest [ref_id, colors, True|False]: a RELATIONAL destination gate —
        # this rule fires iff the destination window of the CURRENT ACTION's
        # translate rule carrying `id == ref_id` (its qualifying components each
        # displaced by that rule's own dy/dx) holds any of `colors` == the flag.
        # Object-anchored: no absolute rect, no frame index, no game constants.
        wd = r.get("when_dest")
        if wd is not None and (not isinstance(wd, (list, tuple)) or len(wd) != 3
                               or not isinstance(wd[0], (str, int))
                               or not isinstance(wd[1], (list, tuple)) or not wd[1]
                               or not isinstance(wd[2], bool)):
            return f"rule {r['op']} has malformed when_dest {wd!r}"
        if r["op"] == "region_event":
            rect = r.get("rect")
            trigger_pattern = r.get("trigger_pattern")
            if (rect is None) == (trigger_pattern is None):
                return "region_event needs exactly one of rect or trigger_pattern"
            if rect is not None and (
                not isinstance(rect, (list, tuple)) or len(rect) != 4
            ):
                return f"region_event has malformed rect {rect!r}"
            for pattern_name, pattern in (
                ("trigger_pattern", trigger_pattern),
                ("mover_pattern", r.get("mover_pattern")),
            ):
                if pattern is None:
                    continue
                if not isinstance(pattern, dict):
                    return f"region_event {pattern_name} must be an object"
                shape = pattern.get("shape")
                values = pattern.get("values")
                if (
                    not isinstance(shape, (list, tuple))
                    or len(shape) != 2
                    or any(not isinstance(value, int) or value <= 0 for value in shape)
                    or not isinstance(values, (list, tuple))
                    or len(values) != int(shape[0]) * int(shape[1])
                    or not all(isinstance(value, int) for value in values)
                ):
                    return f"region_event has malformed {pattern_name} {pattern!r}"
            if r.get("edge") not in ("exit", "enter"):
                return f"region_event has bad edge {r.get('edge')!r}"
            cst = r.get("content_states")
            if cst is not None:
                # REGION-STATE MACHINE: k glyph patterns over `region`, each a flat
                # row-major cell list of the region's area; the transition is a
                # ring ('cycle') or an explicit [[from,to],...] graph.
                rg = r.get("region")
                if not isinstance(rg, (list, tuple)) or len(rg) != 4:
                    return f"region_event content_states needs a 4-tuple region {rg!r}"
                area = (int(rg[2]) - int(rg[0]) + 1) * (int(rg[3]) - int(rg[1]) + 1)
                if (not isinstance(cst, (list, tuple)) or len(cst) < 2
                        or not all(isinstance(s, (list, tuple)) and len(s) == area
                                   for s in cst)):
                    return f"region_event has malformed content_states {cst!r:.80}"
                stt = r.get("state_transition", "cycle")
                if stt != "cycle" and (not isinstance(stt, (list, tuple))
                                       or not all(isinstance(p, (list, tuple)) and len(p) == 2
                                                  for p in stt)):
                    return f"region_event has malformed state_transition {stt!r}"
            elif not isinstance(r.get("writes"), (list, tuple)):
                return "region_event needs writes (list of [color, cells]) or content_states"
            tg = r.get("toggle")
            if tg is not None and (not isinstance(tg, (list, tuple)) or not tg
                                   or not all(isinstance(p, (list, tuple)) and len(p) == 2
                                              for p in tg)):
                return f"region_event has malformed toggle {tg!r}"
            cy = r.get("cycle")
            if cy is not None and (not isinstance(cy, (list, tuple)) or not cy
                                   or not all(isinstance(c, (list, tuple)) and len(c) >= 2
                                              for c in cy)):
                return f"region_event has malformed cycle {cy!r}"
        if r["op"] == "bind_region_value":
            target_rect = r.get("target_rect")
            source_offset = r.get("source_offset")
            if (
                not isinstance(target_rect, (list, tuple))
                or len(target_rect) != 4
                or not all(isinstance(value, int) for value in target_rect)
                or int(target_rect[2]) < int(target_rect[0])
                or int(target_rect[3]) < int(target_rect[1])
            ):
                return f"bind_region_value has malformed target_rect {target_rect!r}"
            if (
                not isinstance(source_offset, (list, tuple))
                or len(source_offset) != 2
                or not all(isinstance(value, int) for value in source_offset)
            ):
                return f"bind_region_value has malformed source_offset {source_offset!r}"
            if not isinstance(r.get("expected_current"), int):
                return "bind_region_value expected_current must be an int"
        if r["op"] == "pattern_write":
            rect = r.get("rect")
            if (
                not isinstance(rect, (list, tuple))
                or len(rect) != 4
                or not all(isinstance(v, int) for v in rect)
                or int(rect[2]) < int(rect[0])
                or int(rect[3]) < int(rect[1])
            ):
                return f"pattern_write has malformed rect {rect!r}"
            pat = r.get("pattern")
            area = (int(rect[2]) - int(rect[0]) + 1) * (int(rect[3]) - int(rect[1]) + 1)
            if (
                not isinstance(pat, (list, tuple))
                or not pat
                or len(pat) != area
                or not all(isinstance(v, int) for v in pat)
            ):
                return (
                    f"pattern_write pattern must be {area} ints (rect area), "
                    f"got {type(pat).__name__} of len "
                    f"{len(pat) if isinstance(pat, (list, tuple)) else 'n/a'}"
                )
    return None


def validate_spec(spec) -> "str | None":
    """Validate a standalone transition carrier."""

    return _validate_spec(spec, require_action_rules=True)


def validate_patch_delta_spec(spec) -> "str | None":
    """Validate an operation delta composed over an existing carrier.

    A delta may consist only of ``always`` rules. Requiring an arbitrary
    action bucket here would turn an action-invariant operation identity into
    an action-specific presentation.
    """

    return _validate_spec(spec, require_action_rules=False)


def _lower_spec(spec, *, validator):
    """Deterministically lower a WORLD_MODEL_SPEC to `step(grid, action, t)`.

    Returns (step_fn, "") or (None, error). The lowered function is pure,
    tuple-in/tuple-out, and fail-closed (any internal error -> the input
    grid is returned unchanged rather than a corrupted one — gates then
    catch the mispredict honestly)."""
    err = validator(spec)
    if err:
        return None, err
    actions = {int(k): list(v or []) for k, v in spec["actions"].items()}
    always = list(spec.get("always") or [])
    partial_patch = validator is validate_patch_delta_spec

    def _fires(rule, g0, t, action, fired_ids):
        # when_effect [ref_id, want]: a RULE-COUPLING gate evaluated MID-CHAIN —
        # veto unless the referenced rule's fired-status (it changed the grid
        # earlier this step) matches `want`. Deterministic because _run applies
        # rules in a fixed order and `fired_ids` accumulates as they apply.
        we = rule.get("when_effect")
        if we is not None and (str(we[0]) in fired_ids) != bool(we[1]):
            return False
        # when_dest [ref_id, colors, want]: RELATIONAL destination gate — veto
        # unless "the current action's id'd translate rule has a destination
        # cell holding one of `colors` on the STEP-START grid" matches `want`.
        # No referenced rule under this action -> the predicate is False.
        wd = rule.get("when_dest")
        if wd is not None:
            ref = next((r for r in actions.get(int(action), [])
                        if r.get("op") == "translate_block"
                        and str(r.get("id")) == str(wd[0])), None)
            holds = _dest_holds(g0, ref, wd[1]) if ref is not None else False
            if holds != bool(wd[2]):
                return False
        # when_count conditions on the STEP-START state (g0), never the
        # mid-chain grid — a mechanic paused by an object standing somewhere
        # pauses on the step AFTER arrival, not on the arrival step itself
        tm = rule.get("when_t_mod")
        if tm is not None and int(t) % int(tm[0]) != int(tm[1]):
            return False
        # when_phase [m, r]: periodic gate on step-start t (blinker/clock)
        wp = rule.get("when_phase")
        if wp is not None and int(t) % int(wp[0]) != int(wp[1]):
            return False
        # when_region [y0, x0, y1, x1, pattern]: a STATE gate — the rule fires
        # only while the rect's step-start contents match the learned pattern
        # (row-major); the general form of "legal only while indicator holds X"
        wr = rule.get("when_region")
        if wr is not None:
            y0, x0, y1, x1, pat = (int(wr[0]), int(wr[1]), int(wr[2]),
                                   int(wr[3]), [int(v) for v in wr[4]])
            h, w = len(g0), len(g0[0])
            k, match = 0, True
            for yy in range(y0, y1 + 1):
                for xx in range(x0, x1 + 1):
                    if not (0 <= yy < h and 0 <= xx < w) or k >= len(pat) \
                            or g0[yy][xx] != pat[k]:
                        match = False
                        break
                    k += 1
                if not match:
                    break
            if not match or k != len(pat):
                return False
        # when_action is a POSITIVE gate: the rule fires only when the step's
        # action is in the set (a directional interaction / "use" button — the
        # general form of a mechanic that only some actions trigger). Composes
        # as an AND veto with the other guards.
        wa = rule.get("when_action")
        if wa is not None and int(action) not in {int(a) for a in wa}:
            return False
        wc = rule.get("when_count")
        if wc is not None:
            color, lo, hi = wc
            n = sum(1 for row in g0 for c in row if c == int(color))
            if (lo is not None and n < int(lo)) or (hi is not None and n > int(hi)):
                return False
        # when_overlap is a POSITIONAL PAUSE: [colors, y0, x0, y1, x1]. The
        # overlap predicate is true iff any cell of `colors` lies in the
        # inclusive rect on the step-start grid; an overlap SUPPRESSES the rule
        # (models key-window entry pausing a mechanic — the mover sitting on a
        # region, not a count, gates firing). Composes as an AND with the other
        # guards: the rule fires iff no guard vetoes it.
        wo = rule.get("when_overlap")
        if wo is not None:
            colors, y0, x0, y1, x1 = wo[0], wo[1], wo[2], wo[3], wo[4]
            # optional 6th element: action scope — the positional veto applies
            # ONLY on these actions (a pause triggered by a directed move INTO
            # the region, not by mere presence; the disambiguator when two
            # actions leave the mover in the same key-window cell but only one
            # trips the mechanic — provable only from an action counterexample)
            wo_actions = wo[5] if len(wo) > 5 else None
            if wo_actions is None or int(action) in {int(a) for a in wo_actions}:
                cs = {int(c) for c in colors}
                h, w = len(g0), len(g0[0])
                yy0, yy1 = max(0, int(y0)), min(h - 1, int(y1))
                xx0, xx1 = max(0, int(x0)), min(w - 1, int(x1))
                if any(g0[y][x] in cs for y in range(yy0, yy1 + 1)
                       for x in range(xx0, xx1 + 1)):
                    return False
        return True

    def _execute(g0: Grid, initial: Grid, action: int, t: int = 0) -> Grid:
        """Apply the spec with distinct source and current presentations.

        Standalone specs use the same grid for both.  A declarative patch
        starts from the base carrier's consequence while guards and crossing
        relations retain the source state.  The operation algebra is shared;
        only the carrier composition differs.
        """

        g = [list(row) for row in initial]
        fired_ids: "set[str]" = set()   # ids of rules that CHANGED the grid this step

        def _run(rule, cur):
            # region_event alone needs the step-start grid: its trigger is a
            # crossing (mover in the rect on g0 xor on the current grid)
            if rule["op"] == "region_event":
                return _apply_region_event(cur, rule, g0)
            if rule["op"] == "bind_region_value":
                return _apply_bind_region_value(cur, rule, g0)
            if rule["op"] in ("consume_extremal", "accumulate_extremal"):
                return _APPLY[rule["op"]](cur, rule, t)
            return _APPLY[rule["op"]](cur, rule)

        # action rules in order; a fired stop_if_applied rule shadows the rest.
        # The `g2 != g` firing test is O(cells), so only pay it when a rule needs
        # it (carries an id, or stops-if-applied) — the common guard-free rule skips it.
        for rule in actions.get(int(action), []):
            if not _fires(rule, g0, t, action, fired_ids):
                continue
            try:
                g2 = _run(rule, g)
            except Exception:
                # fail-closed: a raising rule predicts NOTHING, not "no change" —
                # returning the input grid earns replay credit on no-op rows.
                # None is the convention the gates already understand.
                return None
            if g2 is _UNDEFINED_OPERATION_IMAGE:
                if partial_patch:
                    return None
                g2 = g
            rid = rule.get("id")
            if (rid is not None or rule.get("stop_if_applied")) and g2 != g:
                g = g2
                if rid is not None:
                    fired_ids.add(str(rid))
                if rule.get("stop_if_applied"):
                    break
            else:
                g = g2
        # always-rules run unconditionally after the action resolves
        for rule in always:
            if not _fires(rule, g0, t, action, fired_ids):
                continue
            try:
                g2 = _run(rule, g)
            except Exception:
                return None     # fail-closed, same as the action-rule path above
            if g2 is _UNDEFINED_OPERATION_IMAGE:
                if partial_patch:
                    return None
                g2 = g
            rid = rule.get("id")
            if rid is not None and g2 != g:
                fired_ids.add(str(rid))
            g = g2
        return tuple(tuple(row) for row in g)

    def step(grid: Grid, action: int, t: int = 0) -> Grid:
        return _execute(grid, grid, action, t)

    step.__name__ = "step"
    step.lowered_from_spec = True
    step._ztare_world_model_spec = spec
    step._ztare_execute_spec = _execute
    return step, ""


def lower_spec(spec):
    """Lower a standalone catalog transition carrier."""

    return _lower_spec(spec, validator=validate_spec)


def lower_patch_delta_spec(spec):
    """Lower a PATCH_DELTA_SPEC over ``(base_next, state, action, t)``.

    This is the declarative sibling of a hand-written PATCH_DELTA.  It reuses
    the catalog validator and executor while preserving the distinction
    between source state and the base carrier's proposed consequence.
    """

    step, err = _lower_spec(spec, validator=validate_patch_delta_spec)
    if step is None:
        return None, err
    execute = step._ztare_execute_spec

    def patch_delta(base_next, state, action, t=0):
        return execute(state, base_next, action, t)

    patch_delta.__name__ = "patch_delta_spec"
    patch_delta.lowered_from_patch_delta_spec = True
    patch_delta._ztare_patch_delta_spec = spec
    return patch_delta, ""


def render_region_event_contract() -> str:
    """One owner for region-event schema and source/destination semantics."""

    return (
        '{"op": "region_event", "mover_colors": [..], '
        '("rect": [y0,x0,y1,x1] OR '
        '"trigger_pattern": {"shape": [h,w], "values": [..]}), '
        '"edge": "enter"|"exit", '
        '"writes": [[color, [[y,x], ...]], ...]} — compare the step-start '
        "grid with the post-action/base-next grid: enter means the mover arrives "
        "at the named presentation; exit means the reverse; then apply the writes"
    )


def render_catalog_contract() -> str:
    """The mutator-facing catalog text (briefing / evidence injection)."""
    return (
        "PREFERRED CARRIAGE — operator-class spec (lowest failure rate): instead of "
        "free-form code, define WORLD_MODEL_SPEC = {\"actions\": {\"<action_id>\": "
        "[rule, ...]}, \"always\": [rule, ...]} in test_model.py and the apparatus "
        "compiles it deterministically. Rules (in application order; optional "
        "\"when_t_mod\": [k, r] fires only when t%k==r; optional \"when_overlap\": "
        "[[colors], y0, x0, y1, x1] PAUSES the rule while any of those colors sits in "
        "the inclusive rect — a positional gate, not a count):\n"
        "  {\"op\": \"translate_block\", \"match_colors\": [..], \"dy\": int, \"dx\": int, "
        "\"require_dest_colors\": [..], \"fill_color\": int}  — rigid move of all matching "
        "cells iff every destination cell outside the moving set has an allowed color; "
        "else no-op (refusal)\n"
        "  {\"op\": \"recolor_map\", \"mapping\": {\"<from>\": <to>, ...}}  — global recolor\n"
        "  {\"op\": \"consume_extremal\", \"color\": int, \"replacement\": int, "
        "\"axis\": \"row\"|\"col\", \"extreme\": \"min\"|\"max\", optional \"rate\": [p,q]}  — "
        "per row/col containing the color, recolor its extremal-index cell(s); optional "
        "\"component_scope\": {\"colors\": [..], \"select\": \"all\"|\"largest\"|\"widest\", "
        "\"min_size\": int, \"min_width\": int, \"min_height\": int} restricts this to selected "
        "4-connected components\n"
        "  {\"op\": \"accumulate_extremal\", \"color\": int, \"from\": int (empty, default 0), "
        "\"axis\": \"row\"|\"col\", \"extreme\": \"min\"|\"max\", optional \"rate\": [p,q]}  — "
        "the mirror: per row/col, fill its extremal-index EMPTY cell with the color; accepts "
        "the same optional component_scope\n"
        "  " + render_region_event_contract() + "\n"
        '  {"op": "bind_region_value", "target_rect": [y0,x0,y1,x1], '
        '"source_offset": [dy,dx], "expected_current": int} — while the current '
        "carrier image still equals the expected value over the target region, "
        "copy the source-state value at (target top-left + offset) into that region\n"
        "  {\"op\": \"identity\"}\n"
        "GUARD for RULE-COUPLING: give a rule an \"id\": \"<name>\" and gate another rule with "
        "\"when_effect\": [\"<name>\", true] — it fires iff the id'd rule CHANGED the grid earlier "
        "this step (e.g. a timer that ticks iff the mover actually moved; false = iff it did NOT).\n"
        "GUARD for DESTINATION CONTENT (relational): \"when_dest\": [\"<name>\", [colors], flag] — "
        "fires iff the current action's id'd translate rule has a destination cell (its components "
        "displaced by that rule's own dy/dx) holding one of the colors == flag; object-anchored, "
        "never an absolute rect (e.g. a timer that pauses only while the mover transits void).\n"
        "A spec beats hand-written step(): your analysis is preserved, coding slips are "
        "impossible. Fall back to step(grid, action, t) only for dynamics the catalog "
        "cannot express."
    )


def calibration_summary(projects_dir) -> dict:
    """Aggregate ratified-spec receipts across game projects: per-operator use
    counts and the games they closed. The catalog self-ranks from RATIFIED
    verdicts only (the move-calibration pattern) — no counts from failed specs,
    so amplification stays honest."""
    import json
    from pathlib import Path
    stats: dict = {}
    for path in Path(projects_dir).glob("*/workspace/spec_receipts.jsonl"):
        for line in path.read_text().splitlines():
            try:
                d = json.loads(line)
            except Exception:
                continue
            if "pass" not in str(d.get("verdict", "")):
                continue
            for op in d.get("ops", []):
                st = stats.setdefault(op, {"ratified_uses": 0, "games": set()})
                st["ratified_uses"] += 1
                st["games"].add(d.get("project", "?"))
    return {op: {"ratified_uses": v["ratified_uses"], "games": sorted(v["games"])}
            for op, v in stats.items()}


def spec_description_length(spec: dict) -> int:
    """Description length of a WORLD_MODEL_SPEC in catalog units: one per rule
    plus one per bound parameter (guards, colors, offsets). The size_fn for
    MDL selection — same pattern as leanmill's `lean_description_length` plug
    into `ztare.fit.mdl.MDLLibrary`; kept a plain int so the assembler's argmin
    and a future MDLLibrary keep/retire share one metric (no bespoke reinvention)."""
    def _rule_dl(r: dict) -> int:
        n = 1
        for k, v in r.items():
            if k == "op":
                continue
            n += len(v) if isinstance(v, (list, tuple)) else (len(v) if isinstance(v, dict) else 1)
        return n
    total = sum(_rule_dl(r) for rules in spec.get("actions", {}).values() for r in rules)
    total += sum(_rule_dl(r) for r in spec.get("always", []))
    return total
