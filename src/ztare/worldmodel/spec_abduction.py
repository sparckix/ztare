"""Spec abduction: recover catalog-expressible laws from diffs, zero model calls.

The deductive seed-grammar synthesis generalized to the operator catalog
(GP-250). A transition's changed-cell diff nearly dictates its rule:

  translate_block   a moved rigid block shows up as source cells -> fill plus
                    an identically-shaped copy at a uniform displacement; the
                    displacement, block colors, fill color, and destination
                    colors are READ OFF the diff
  consume_extremal  exactly one cell per affected row (or column) flipping the
                    same color -> same replacement, at that row's extremal
                    index of the color
  accumulate_extremal  the fill mirror of consume, mined only where consume's
                    moved-color filter drops a genuine extremal fill (additive)
  recolor_map       a global color-to-color flip across all changed cells

Abduction PROPOSES per-transition rules; proposals are pooled per action,
assembled into a WORLD_MODEL_SPEC, lowered, and VERIFIED through the same
replay gate as any candidate — abduction never bypasses the gates, it just
makes the mutator the fallback instead of the workhorse. MDL prefers the
fewest-rule spec among gate-passing assemblies.

Performance (literature anchors; all preserve the hypothesis space + arbiters):
  - CEGIS warm start: `abduce_spec(prior_spec=...)` verifies the standing
    champion through the replay gate FIRST and returns it if still clean (one
    replay vs the full search); else seeds its rules as high-priority options.
  - Version-space / candidate-elimination: per-action OPTION lists filtered
    against only that action's transitions.
  - E-graph / observational equivalence: two shared sub-evaluations. (1) The
    assembler — a combo's mismatch is the SUM over actions of each action's
    own-transition mismatch under its chosen option, scored once and reused
    across the <=64 combos. (2) The physics closure — a mined region_event is a
    guard-free rule appended LAST, so scoring base+[event] applies that one
    write on top of the cached current-chain prediction, not a fresh 64x64
    chain replay per candidate.
  - Espresso (two-level minimization): the write-function learner
    (_fit_write_function) fits constant/involution/permutation by consistency +
    MDL; the guard side composes when_dest as a conjunct rather than replacing.

DESIGN NOTE — incremental version space (deferred): on log GROWTH, the standing
per-action option lists could be filtered against ONLY the new transitions
(keyed by evidence-sha), with full re-enumeration only when a list empties. Not
built: the CEGIS warm start already collapses the common growth case (champion
still holds) to one replay, which captures the same win with far less state.
"""

from __future__ import annotations

import json
import os
from contextvars import ContextVar
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.gates import replay_consistency_gate, rollout_depth
from ztare.worldmodel.spec_catalog import lower_spec, spec_description_length


_ACTIVE_SCORE_CONTEXT: ContextVar = ContextVar("ztare_abduction_score_context", default=None)
_ACTIVE_GALOIS_STATS: ContextVar = ContextVar("ztare_abduction_galois_stats", default=None)


def _diff(s, s_next):
    return [(y, x, s[y][x], s_next[y][x])
            for y in range(len(s)) for x in range(len(s[0]))
            if s[y][x] != s_next[y][x]]


def _count(g, c):
    return sum(1 for row in g for v in row if v == int(c))


def _cells_bbox(trs, colors):
    """Inclusive bounding rect (y0, x0, y1, x1) of every cell whose color is in
    `colors`, over the step-start grids of `trs`; None if none present."""
    cs = {int(c) for c in colors}
    ys, xs = [], []
    for tr in trs:
        for y, row in enumerate(tr.s):
            for x, v in enumerate(row):
                if v in cs:
                    ys.append(y)
                    xs.append(x)
    return (min(ys), min(xs), max(ys), max(xs)) if ys else None


def _abduce_translate_block(s, s_next, diff) -> "list[dict]":
    """A rigid move: cells that lost a color reappear at a uniform offset."""
    lost = defaultdict(list)     # color -> positions that changed away from it
    gained = defaultdict(list)   # color -> positions that changed to it
    for (y, x, a, b) in diff:
        lost[a].append((y, x))
        gained[b].append((y, x))
    rules = []
    for color, src in lost.items():
        dst = gained.get(color)
        if not dst or len(dst) != len(src):
            continue
        offs = {(dy, dx) for (dy, dx) in
                {(d[0] - s0[0], d[1] - s0[1]) for s0, d in zip(sorted(src), sorted(dst))}}
        if len(offs) != 1:
            continue
        dy, dx = next(iter(offs))
        if (dy, dx) == (0, 0):
            continue
        # the whole moving block may span several colors sharing this offset
        block_colors = sorted({c for c, ps in lost.items()
                               if gained.get(c) and len(gained[c]) == len(ps)
                               and {(d[0] - s0[0], d[1] - s0[1])
                                    for s0, d in zip(sorted(ps), sorted(gained[c]))} == {(dy, dx)}})
        # fill = what the vacated cells became; dest requirement = what the
        # occupied destination cells were before the move
        fills = Counter(b for (y, x, a, b) in diff if a in block_colors and (y, x) not in
                        {(yy, xx) for c in block_colors for (yy, xx) in gained.get(c, [])})
        dest_was = Counter(a for (y, x, a, b) in diff if b in block_colors and a not in block_colors)
        if not fills:
            continue
        rule = {"op": "translate_block", "match_colors": block_colors,
                "dy": dy, "dx": dx,
                "require_dest_colors": sorted(dest_was) or [fills.most_common(1)[0][0]],
                "fill_color": fills.most_common(1)[0][0]}
        # if vacated cells took DIFFERENT colors, constant fill cannot be the
        # law — emit the surround (terrain-restore) variant as well
        if len(fills) > 1:
            alt = dict(rule)
            alt["fill_color"] = "surround"
            if len(block_colors) > 1:
                alt["component_min_colors"] = len(block_colors)
            rules.append(alt)
        if len(block_colors) > 1:
            # the witnessed mover is multi-colored — pin that as the component
            # selector so same-palette single-color decorations stay static
            rule["component_min_colors"] = len(block_colors)
        rules.append(rule)
    return rules


def _abduce_translate_com(s, s_next, diff) -> "list[dict]":
    """FALLBACK detector (runtime witnessed-need: fires only when exact rigid
    matching found nothing for a color that clearly moved): center-of-mass
    displacement, robust to partial occlusion / minor shape change (external
    L10 review, geometric-fragility fix). Emits a rigid rule at the CoM
    offset — the gates decide if it is the law."""
    lost = defaultdict(list)
    gained = defaultdict(list)
    for (y, x, a, b) in diff:
        lost[a].append((y, x))
        gained[b].append((y, x))
    rules = []
    for color, src in lost.items():
        dst = gained.get(color)
        if not dst or len(dst) == len(src):
            continue          # equal counts are the exact detector's territory
        cy = round(sum(y for y, _ in dst) / len(dst) - sum(y for y, _ in src) / len(src))
        cx = round(sum(x for _, x in dst) / len(dst) - sum(x for _, x in src) / len(src))
        if (cy, cx) == (0, 0):
            continue
        fills = Counter(b for (y, x, a, b) in diff if a == color)
        dest_was = Counter(a for (y, x, a, b) in diff if b == color and a != color)
        if not fills:
            continue
        rules.append({"op": "translate_block", "match_colors": [color],
                      "dy": cy, "dx": cx,
                      "require_dest_colors": sorted(dest_was) or [fills.most_common(1)[0][0]],
                      "fill_color": fills.most_common(1)[0][0]})
    return rules


def _abduce_consume_extremal(s, s_next, diff) -> "list[dict]":
    """One cell per affected row (or col) flipping color c -> r at the row's
    extremal index of c."""
    rules = []
    flips = Counter((a, b) for (_, _, a, b) in diff)
    gained_colors = {bb for (_, _, _, bb) in diff}
    for (a, b), _n in flips.items():
        if a in gained_colors:
            # the color reappears elsewhere in the diff -> it MOVED, it was not
            # consumed; without this filter a block move masquerades as a
            # count-k consume and poisons per-action selection
            continue
        cells = [(y, x) for (y, x, aa, bb) in diff if (aa, bb) == (a, b)]
        by_row = defaultdict(list)
        for (y, x) in cells:
            by_row[y].append(x)
        counts = {len(xs) for xs in by_row.values()}
        if len(counts) == 1:
            k = counts.pop()
            for extreme, pick in (("min", min), ("max", max)):
                def _extremal_run(y, n):
                    idxs = sorted(x for x in range(len(s[0])) if s[y][x] == a)
                    return idxs[:n] if extreme == "min" else idxs[-n:]
                if all(sorted(xs) == _extremal_run(y, k) for y, xs in by_row.items()):
                    rule = {"op": "consume_extremal", "color": a, "replacement": b,
                            "axis": "row", "extreme": extreme}
                    if k > 1:
                        rule["count"] = k
                    rules.append(rule)
                    break
    return rules


def _abduce_accumulate_extremal(s, s_next, diff) -> "list[dict]":
    """Mirror of _abduce_consume_extremal, kept strictly ADDITIVE: recovers
    extremal-FILL laws on exactly the diffs consume mining drops. consume skips a
    flip a->b when the source color `a` also appears as a GAINED color (it reads
    `a` as having MOVED, not been consumed); a filling bar whose empty color `a`
    is simultaneously produced elsewhere in the same step trips that filter, so
    consume never proposes the fill. Same extremal-run test, keyed on the fill:
    emitted as accumulate(color=b, from=a). Gated to a IN gained_colors so it
    never duplicates a consume proposal (a NOT in gained is consume's territory)."""
    rules = []
    flips = Counter((a, b) for (_, _, a, b) in diff)
    gained_colors = {bb for (_, _, _, bb) in diff}
    lost_colors = {aa for (_, _, aa, _) in diff}
    for (a, b), _n in flips.items():
        if a not in gained_colors:
            continue                      # consume mining owns this; stay additive
        if b in lost_colors:
            # the fill color is ALSO lost somewhere this step -> it is a moving
            # block, not a growing bar (a translate vacates its source cells of
            # the same color). A genuine accumulation only ever GAINS its color.
            continue
        cells = [(y, x) for (y, x, aa, bb) in diff if (aa, bb) == (a, b)]
        by_row = defaultdict(list)
        for (y, x) in cells:
            by_row[y].append(x)
        counts = {len(xs) for xs in by_row.values()}
        if len(counts) == 1:
            k = counts.pop()
            for extreme in ("min", "max"):
                def _extremal_run(y, n):
                    idxs = sorted(x for x in range(len(s[0])) if s[y][x] == a)
                    return idxs[:n] if extreme == "min" else idxs[-n:]
                if all(sorted(xs) == _extremal_run(y, k) for y, xs in by_row.items()):
                    rule = {"op": "accumulate_extremal", "color": b, "from": a,
                            "axis": "row", "extreme": extreme}
                    if k > 1:
                        rule["count"] = k
                    rules.append(rule)
                    break
    return rules


def _abduce_recolor_map(s, s_next, diff) -> "list[dict]":
    """Global recolor: every cell of color a became b, for each flipped pair."""
    mapping = {}
    for (y, x, a, b) in diff:
        if a in mapping and mapping[a] != b:
            return []
        mapping[a] = b
    for a, b in mapping.items():
        for y in range(len(s)):
            for x in range(len(s[0])):
                if s[y][x] == a and s_next[y][x] != b:
                    return []
    return [{"op": "recolor_map", "mapping": {str(k): v for k, v in mapping.items()}}] \
        if mapping else []


def _extremal_component_scope_candidates(rule: dict) -> "list[dict]":
    """Structural scope refinements shared by abduction and transport checks.

    An extremal write over-fires when the same presentation value belongs to
    more than one connected component.  The existing refinement pass already
    resolves that ambiguity by quotienting components by size or width.  Keep
    the candidate language in one place so a finite transport witness and the
    full-log assembler cannot silently mean different things by "component".
    """
    op = rule.get("op")
    if op == "consume_extremal":
        match = int(rule["color"])
        companion = int(rule["replacement"])
    elif op == "accumulate_extremal":
        match = int(rule.get("from", 0))
        companion = int(rule["color"])
    else:
        return []
    scopes = [
        {"colors": [match], "select": "largest", "min_size": 2},
        {"colors": [match], "select": "widest", "min_width": 2},
    ]
    if companion != match:
        scopes.extend([
            {
                "colors": [match, companion],
                "select": "largest",
                "min_size": 2,
            },
            {
                "colors": [match, companion],
                "select": "widest",
                "min_width": 2,
            },
        ])
    return scopes


def catalog_state_morphisms(source, target) -> "list[dict]":
    """Return catalog rules whose lowered pointwise map is exactly source→target.

    This is a bounded adapter operation, not a law or symmetry certificate.  It
    answers a smaller question: whether two observed presentations are related
    by one already-registered operation.  Callers must separately establish
    lifecycle compatibility and test the same operation on consequences before
    claiming a finite commuting square.
    """
    diff = _diff(source, target)
    if not diff:
        return [{"op": "identity"}]
    proposed: "list[dict]" = []
    for abducer in (
        _abduce_translate_block,
        _abduce_translate_com,
        _abduce_consume_extremal,
        _abduce_accumulate_extremal,
        _abduce_recolor_map,
    ):
        for rule in abducer(source, target, diff):
            proposed.append(rule)
            proposed.extend(
                {**rule, "component_scope": scope}
                for scope in _extremal_component_scope_candidates(rule)
            )

    target_key = tuple(tuple(row) for row in target)
    exact: "list[dict]" = []
    seen: "set[str]" = set()
    for rule in proposed:
        key = json.dumps(rule, sort_keys=True, separators=(",", ":"))
        if key in seen:
            continue
        seen.add(key)
        step, _error = lower_spec(
            {"actions": {"0": [rule]}, "always": []}
        )
        if step is not None and step(source, 0, 0) == target_key:
            exact.append(rule)
    return exact


def _broaden_dests(actions: dict, log, mover_colors) -> dict:
    """A sprite crossing varied terrain refuses moves whenever the per-diff
    require_dest set (learned from ONE frame) omits a terrain color it actually
    passes over — and on noisy frames (a marker/HUD nearby) the abductor may
    even mis-read the palette, so unioning per-candidate is unreliable. Learn
    passability from GROUND TRUTH instead: a color is passable for the mover
    iff some transition shows a cell of that color BECOME a mover color (the
    sprite moved onto it). A wall the mover never enters is never added, so
    genuine refusals survive; the strict-improvement gate drops the broaden if
    it opens one anyway."""
    mc = {int(c) for c in mover_colors}
    passable = set()
    for tr in log:
        for y in range(len(tr.s)):
            for x in range(len(tr.s[0])):
                if tr.s[y][x] not in mc and tr.s_next[y][x] in mc:
                    passable.add(tr.s[y][x])
    out = {}
    for a_str, rules in actions.items():
        new_rules = []
        for r in rules:
            if r.get("op") == "translate_block":
                r = dict(r)
                r["require_dest_colors"] = sorted(
                    {int(c) for c in r["require_dest_colors"]} | passable)
            new_rules.append(r)
        out[a_str] = new_rules
    return out


def _perm_cycles(m: dict) -> "list[list]":
    """Decompose a permutation map (from->to, a bijection with no fixed points)
    into disjoint cycles."""
    seen, out = set(), []
    for start in sorted(m):
        if start in seen:
            continue
        cyc, nxt = [start], m[start]
        seen.add(start)
        while nxt != start:
            cyc.append(nxt)
            seen.add(nxt)
            nxt = m[nxt]
        out.append(cyc)
    return out


def _cluster_rects(rects) -> "list[list]":
    """Merge overlapping rects into disjoint union rects — one per trigger site.
    Toggles over the SAME cell-set at DIFFERENT sites must have disjoint rects so
    exactly one fires per crossing (two overlapping toggles would cancel)."""
    def overlap(a, b):
        return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])
    clusters: "list[list]" = []
    for r in rects:
        merged, rest = [list(r)], []
        for c in clusters:
            (merged if overlap(c, r) else rest).append(c)
        clusters = rest + [[min(m[0] for m in merged), min(m[1] for m in merged),
                            max(m[2] for m in merged), max(m[3] for m in merged)]]
    return clusters


def _fit_write_function(site, cell_pairs, mover_colors) -> "dict | None":
    """UNIFIED region-write learner (replaces the bespoke fixed/toggle/cycle
    miners, symmetric to the Espresso guard learner): given a SITE and the
    per-cell observed (before -> after) pairs across its fired crossings, fit the
    minimal write function by consistency + MDL —
      constant    -> fixed write  (each cell writes ONE colour, MDL-simplest)
      involution  -> toggle       (the GLOBAL colour map is a self-inverse
                                    non-identity bijection: colours swap)
      permutation -> cycle        (a bijection carrying a >2 cycle)
      none        -> None         (no consistent function; leave for a card)
    The permutation arm is built from the global colour map, so an N-cell HUD bar
    whose cells each witness only ONE phase (both phases spread ACROSS cells, no
    single cell showing c1->c2 AND c2->c1) still resolves to a toggle — the case
    the per-cell bespoke miner missed. Returns a region_event dict or None."""
    if not cell_pairs:
        return None
    cells = sorted(cell_pairs)
    # CONSTANT (fixed write) first — the MDL-simplest consistent family. Only when
    # some cell's `after` VARIES (a genuine state-dependent switch witnessed in
    # both phases) does constant fail and a permutation become necessary.
    per_cell_after = {c: {b for _, b in ps} for c, ps in cell_pairs.items()}
    if all(len(v) == 1 for v in per_cell_after.values()):
        by_color: "dict[int, list]" = defaultdict(list)
        for c, v in per_cell_after.items():
            by_color[next(iter(v))].append([c[0], c[1]])
        wr = [[col, sorted(cs)] for col, cs in sorted(by_color.items())]
        return {"op": "region_event", "mover_colors": mover_colors, "rect": list(site),
                "edge": "exit", "writes": wr}
    # PERMUTATION: `after` is a function of `before` over the site's colours, a
    # bijection with no fixed point -> a colour permutation applied on every
    # crossing (correct on every phase; a fixed write is wrong on half).
    sigma: "dict[int, int]" = {}
    for _c, ps in cell_pairs.items():
        for a, b in ps:
            if a == b:
                continue
            if sigma.get(a, b) != b:
                return None                              # not a function -> no clean law
            sigma[a] = b
    if not sigma or set(sigma) != set(sigma.values()):
        return None                                      # not a bijection over the moving set
    cycles = _perm_cycles(sigma)
    ev = {"op": "region_event", "mover_colors": mover_colors, "rect": list(site),
          "edge": "exit", "writes": [[min(sigma), [list(c) for c in cells]]]}
    if all(len(cy) == 2 for cy in cycles):
        ev["toggle"] = [[cy[0], cy[1]] for cy in cycles]     # k=2 spelling (involution)
    else:
        ev["cycle"] = [list(cy) for cy in cycles]
    return ev


def _learn_site_writes(crossings, mover_colors, non_constant_only=False) -> "list[dict]":
    """Group fired crossings into SITES (clustered trigger rects) and fit one
    write function per site via _fit_write_function. Grouping by site — not by the
    exact write pattern — is what lets both toggle phases share one group even when
    they arrive on different crossings/paths (the real-log failure). With
    `non_constant_only`, returns just toggle/cycle events: in the live pipeline the
    existing fixed-write emission owns the constant arm byte-for-byte, so this stays
    additive (non-iatrogenic) while closing the phase-inversion gap."""
    if not crossings:
        return []
    sites = _cluster_rects([r for r, _ in crossings])

    def _in(rect, site):
        return not (rect[2] < site[0] or site[2] < rect[0]
                    or rect[3] < site[1] or site[3] < rect[1])

    events = []
    for site in sites:
        cell_pairs: "dict[tuple, list]" = defaultdict(list)
        for rect, fromto in crossings:
            if _in(rect, site):
                for cell, ab in fromto.items():
                    cell_pairs[cell].append(ab)
        ev = _fit_write_function(site, cell_pairs, mover_colors)
        if ev is None:
            continue
        if non_constant_only and not (ev.get("toggle") or ev.get("cycle")):
            continue
        events.append(ev)
    return events


def _abduce_region_events(step, log, mover_colors, resource_colors) -> "list[dict]":
    """Learn region-crossing events from the residual of the best move/consume
    assembly. For each mis-predicted transition, the cells where reality
    differs from the moved-sprite prediction ARE the write; the mover's
    step-start bounding box IS the rect it crossed out of. Transitions sharing
    a write-set become one rule (a mechanic that recurs is a mechanic, not a
    memorized frame). TOGGLE/CYCLE events (a state-dependent switch) are mined
    first, then FIXED writes. Excluded, on principle: resource refills (a level
    reset, not a write) and resource-colored cells (the consume rule's job)."""
    first = next(iter(log), None)
    if first is None:
        return []
    H, W = len(first.s), len(first.s[0])
    mc = {int(c) for c in mover_colors}
    rc = {int(c) for c in resource_colors}
    # Two trigger anchorings per crossing. SOURCE footprint + edge=exit: the
    # cells the sprite VACATED (terrain restored behind it). DEST footprint +
    # edge=enter: the cells it LANDED ON. A write bound to a fixed CHECKPOINT the
    # mover reaches is one rect under dest-anchoring, but its SOURCE footprint
    # splits by approach direction into per-path sites — one real dock, one
    # spurious corridor position — so the write never assembles under exit-
    # anchoring when the dock is reached from >1 direction (the ls20 HUD toggle,
    # hit by both a lateral and a vertical move: 23 crossings anchor one dock, the
    # 24th a corridor, and the corridor site over-fires and is rejected). Mine
    # both; the strict-improvement closure keeps whichever generalizes.
    exit_g: "dict[tuple, list]" = defaultdict(list)
    enter_g: "dict[tuple, list]" = defaultdict(list)
    exit_x: "list[tuple]" = []
    enter_x: "list[tuple]" = []
    for tr in log:
        p = step(tr.s, tr.a, tr.t)
        if p == tr.s_next:
            continue
        if any(_count(tr.s_next, c) > _count(tr.s, c) for c in rc):
            continue                                   # resource refill = reset
        residual = [(y, x) for y in range(H) for x in range(W)
                    if p[y][x] != tr.s_next[y][x] and tr.s_next[y][x] not in rc]
        writes = tuple(sorted((y, x, tr.s_next[y][x]) for (y, x) in residual))
        if not writes:
            continue
        fromto = {(y, x): (p[y][x], tr.s_next[y][x]) for (y, x) in residual}
        # anchoring to the MOVED component (not every same-colored cell) keeps
        # the rect a tight local trigger.
        src = [(y, x) for y in range(H) for x in range(W)
               if tr.s[y][x] in mc and p[y][x] != tr.s[y][x]]
        dst = [(y, x) for y in range(H) for x in range(W)
               if p[y][x] in mc and tr.s[y][x] != p[y][x]]
        if src:
            rect = (min(y for y, x in src), min(x for y, x in src),
                    max(y for y, x in src), max(x for y, x in src))
            exit_g[writes].append(rect)
            exit_x.append((rect, fromto))
        if dst:
            rect = (min(y for y, x in dst), min(x for y, x in dst),
                    max(y for y, x in dst), max(x for y, x in dst))
            enter_g[writes].append(rect)
            enter_x.append((rect, fromto, writes))

    def _fixed_writes(groups, edge):
        out = []
        for writes, rects in groups.items():
            by_color: "dict[int, list]" = defaultdict(list)
            for (y, x, c) in writes:
                by_color[c].append([y, x])
            wr = [[c, sorted(cs)] for c, cs in sorted(by_color.items())]
            # one event per TRIGGER SITE (footprints clustered), not a single
            # union rect: the same write may fire at two docks a sprite oscillates
            # between; a union rect spans both, so the sprite stays inside and the
            # edge never fires.
            for site in _cluster_rects(rects):
                out.append({"op": "region_event", "mover_colors": sorted(mc),
                            "rect": site, "edge": edge, "writes": wr})
        return out

    # EXIT anchoring — byte-identical to the original emission (toggle/cycle from
    # the write-function learner, then the fixed-write constant arm).
    events = _learn_site_writes(exit_x, sorted(mc), non_constant_only=True)
    events += _fixed_writes(exit_g, "exit")
    # DEST-anchored ENTER events, added ONLY for a write that CONVERGES to one
    # destination (a fixed checkpoint the mover reaches) yet whose SOURCE
    # footprints split across >1 dock (it is reached from several move
    # directions). That convergent-dest / divergent-source signature is exactly
    # the multi-approach checkpoint the exit anchoring fragments and cannot
    # assemble; requiring it keeps enter inert for ordinary local writes (whose
    # destination also varies), so it never preempts the guard/pause refinement.
    # Pooling the convergent crossings by dest also lets the write-function
    # learner see BOTH phases at the checkpoint (each approach witnesses its own),
    # recovering an involution TOGGLE the per-source split would miss. The strict-
    # improvement closure drops any enter event that ties or double-fires.
    conv = {w for w in enter_g
            if len(_cluster_rects(enter_g[w])) == 1
            and len(_cluster_rects(exit_g.get(w, []))) >= 2}
    if conv:
        conv_x = [(r, f) for (r, f, w) in enter_x if w in conv]
        events += [dict(ev, edge="enter")
                   for ev in _learn_site_writes(conv_x, sorted(mc), non_constant_only=True)]
        events += _fixed_writes({w: enter_g[w] for w in conv}, "enter")
    return events


@dataclass
class AbductionResult:
    status: str                       # spec_identified | partial | no_catalog_law
    spec: "dict | None" = None
    step_fn: object = None
    rules_by_action: dict = field(default_factory=dict)
    replay_ok: bool = False
    detail: str = ""
    quotient_stats: dict = field(default_factory=dict)
    galois_stats: dict = field(default_factory=dict)


@dataclass(frozen=True)
class _TimeFeatures:
    """Time coordinates a candidate can observe while scoring.

    Catalog rules see `t` only through periodic guards (`when_t_mod` /
    `when_phase`) unless a consume/accumulate rule carries `rate`, whose
    Bresenham arithmetic depends on raw `t`. Quotient keys therefore use raw
    `t` for rate-bearing candidates and only the candidate's visible residues
    otherwise.
    """
    raw_t: bool
    periods: tuple


@dataclass(frozen=True)
class _TransitionClass:
    representative: object
    multiplicity: int
    row_indices: tuple
    target_counts: Counter


@dataclass(frozen=True)
class _PredictionRows:
    rows: list
    features: _TimeFeatures

    def __getitem__(self, idx):
        return self.rows[idx]


@dataclass
class _GaloisStats:
    bounded_candidates: int = 0
    footprint_pruned: int = 0
    full_scored: int = 0
    early_exited: int = 0
    nogood_pruned: int = 0

    def summary(self) -> dict:
        frac = (self.footprint_pruned / self.bounded_candidates
                if self.bounded_candidates else 0.0)
        return {
            "enabled": _galois_prune_enabled(),
            "bounded_candidates": self.bounded_candidates,
            "footprint_pruned": self.footprint_pruned,
            "full_scored": self.full_scored,
            "early_exited": self.early_exited,
            "footprint_pruned_fraction": frac,
            "nogood_pruned": self.nogood_pruned,
        }


class _ScoreContext:
    """Per-abduction transition quotient with feature-sensitive class caches."""

    def __init__(self, log):
        self.rows = list(log)
        self.row_ids = {id(tr): i for i, tr in enumerate(self.rows)}
        self._class_cache = {}
        # FIX C: observed_diff_cells is only consumed by the Galois lower-bound
        # path (ZTARE_GALOIS_PRUNE=1, off by default). Building it eagerly costs
        # ~180K set_add_entry ops per abduce_spec call even when Galois is disabled.
        # Lazy property: built on first access, absent when Galois is off.
        self._observed_diff_cells: "dict | None" = None
        # FIX B (interner pattern from planner, idiomatic reuse): intern each
        # tr.s once per run → int id; the int id replaces the 64×64 nested-tuple
        # as the class-grouping dict key in classes_for (hashing a single int vs
        # hashing ~4096 values recursively). Pure-Python dict, no numpy, so no
        # numpy.array construction overhead. Semantics unchanged (bijection).
        # target_counts stays tuple-keyed (tr.s_next is already a tuple — cheap).
        # ponytail: no new class — reuse the tuple→id idiom the planner uses.
        _gk2id: dict = {}
        _nxt_id = [0]
        def _intern_s(g):
            k = _grid_key(g)
            v = _gk2id.get(k)
            if v is None:
                v = _nxt_id[0]
                _gk2id[k] = v
                _nxt_id[0] += 1
            return v
        self._s_ids: list = [_intern_s(tr.s) for tr in self.rows]

    @property
    def observed_diff_cells(self) -> dict:
        # ponytail: lazy build — only materialises when Galois prune is enabled.
        # If the caller checks _galois_prune_enabled() before using this, the dict
        # is never built in the common (off) path.
        if self._observed_diff_cells is None:
            self._observed_diff_cells = {
                i: _diff_cell_set(tr.s, tr.s_next) for i, tr in enumerate(self.rows)
            }
        return self._observed_diff_cells

    def _indices_for(self, log):
        if log is self.rows:
            return tuple(range(len(self.rows))), self.rows
        rows = list(log)
        idxs = []
        for local_i, tr in enumerate(rows):
            if id(tr) not in self.row_ids:
                return None, rows
            idxs.append(self.row_ids[id(tr)])
        return tuple(idxs), rows

    def classes_for(self, log, features: _TimeFeatures, env=frozenset()):
        idxs, rows = self._indices_for(log)
        if idxs is None:
            return None
        env = frozenset(int(i) for i in env)
        key = (features, idxs, env)
        if key in self._class_cache:
            return self._class_cache[key]
        grouped = {}
        for local_i, idx in enumerate(idxs):
            if local_i in env:
                continue
            tr = rows[local_i]
            # ponytail: int-keyed class key — O(1) int hash replaces O(H*W)
            # nested-tuple hash on every dict setdefault/lookup during grouping.
            cls_key = _transition_class_key_id(tr, self._s_ids[idx], features)
            entry = grouped.setdefault(cls_key, [tr, [], Counter()])
            entry[1].append(local_i)
            entry[2][_grid_key(tr.s_next)] += 1
        classes = tuple(_TransitionClass(rep, len(indices), tuple(indices), targets)
                        for rep, indices, targets in grouped.values())
        self._class_cache[key] = classes
        return classes

    def summary_for_spec(self, spec, env=frozenset()):
        features = _spec_time_features(spec)
        classes = self.classes_for(self.rows, features, env)
        return {
            "rows": len(self.rows) - len(set(env)),
            "classes": len(classes) if classes is not None else len(self.rows),
            "raw_t": features.raw_t,
            "periods": list(features.periods),
        }


def _quotient_enabled() -> bool:
    return os.environ.get("ZTARE_QUOTIENT_SCORE", "1") != "0"


def _galois_prune_enabled() -> bool:
    return os.environ.get("ZTARE_GALOIS_PRUNE", "0") != "0"


def _display_refine_fast_enabled() -> bool:
    return os.environ.get("ZTARE_DISPLAY_REFINE_FAST", "1") != "0"


def _refine_full_replay_cap(default: int = 24) -> int:
    try:
        return max(0, int(os.environ.get("ZTARE_REFINE_FULL_REPLAY_CAP", str(default))))
    except ValueError:
        return default


def _hot_region_write_budget(default: int = 128) -> int:
    try:
        return max(0, int(os.environ.get("ZTARE_HOT_REGION_WRITE_BUDGET", str(default))))
    except ValueError:
        return default


def _refine_signal_eval_budget(default: int = 10_000) -> int:
    try:
        return max(0, int(os.environ.get("ZTARE_REFINE_SIGNAL_EVAL_BUDGET", str(default))))
    except ValueError:
        return default


def _display_candidate_budget(default: int = 256) -> int:
    try:
        return max(0, int(os.environ.get("ZTARE_DISPLAY_CANDIDATE_BUDGET", str(default))))
    except ValueError:
        return default


def _display_write_cell_budget(default: int = 128) -> int:
    try:
        return max(0, int(os.environ.get("ZTARE_DISPLAY_WRITE_CELL_BUDGET", str(default))))
    except ValueError:
        return default


def _display_context_budget(default: int = 32) -> int:
    try:
        return max(0, int(os.environ.get("ZTARE_DISPLAY_CONTEXT_BUDGET", str(default))))
    except ValueError:
        return default


def _install_score_context(log) -> "_ScoreContext | None":
    _ACTIVE_GALOIS_STATS.set(_GaloisStats())
    if not _quotient_enabled():
        _ACTIVE_SCORE_CONTEXT.set(None)
        return None
    ctx = _ScoreContext(log)
    _ACTIVE_SCORE_CONTEXT.set(ctx)
    return ctx


def _score_context_for(log) -> "_ScoreContext | None":
    if not _quotient_enabled():
        return None
    ctx = _ACTIVE_SCORE_CONTEXT.get()
    if ctx is None:
        return None
    idxs, _rows = ctx._indices_for(log)
    return ctx if idxs is not None else None


def _galois_stats() -> "_GaloisStats | None":
    return _ACTIVE_GALOIS_STATS.get()


def _galois_summary() -> dict:
    stats = _galois_stats()
    return stats.summary() if stats is not None else {
        "enabled": _galois_prune_enabled(),
        "bounded_candidates": 0,
        "footprint_pruned": 0,
        "full_scored": 0,
        "early_exited": 0,
        "footprint_pruned_fraction": 0.0,
        "nogood_pruned": 0,
    }


def _grid_key(g) -> tuple:
    return g if isinstance(g, tuple) and all(isinstance(r, tuple) for r in g) \
        else tuple(tuple(r) for r in g)


def _all_spec_rules(spec):
    if not isinstance(spec, dict):
        return []
    rules = [r for rs in spec.get("actions", {}).values() for r in (rs or [])]
    rules.extend(spec.get("always") or [])
    return [r for r in rules if isinstance(r, dict)]


def _spec_time_features(spec) -> _TimeFeatures:
    rules = _all_spec_rules(spec)
    raw_t = any("rate" in r for r in rules)
    periods = sorted({int(r[k][0]) for r in rules for k in ("when_t_mod", "when_phase")
                      if r.get(k) is not None})
    return _TimeFeatures(raw_t=raw_t, periods=tuple(periods))


def _step_time_features(step) -> _TimeFeatures:
    feat = getattr(step, "_ztare_score_time_features", None)
    if feat is not None:
        return feat
    spec = getattr(step, "_ztare_world_model_spec", None)
    # Unknown callables may inspect raw `t`; do not quotient them across time.
    feat = _spec_time_features(spec) if spec is not None else _TimeFeatures(True, ())
    try:
        step._ztare_score_time_features = feat
    except Exception:
        pass
    return feat


def _transition_class_key(tr, features: _TimeFeatures):
    if features.raw_t:
        t_key = ("raw", int(tr.t))
    elif features.periods:
        t_key = tuple((m, int(tr.t) % m) for m in features.periods)
    else:
        t_key = ()
    return (_grid_key(tr.s), int(tr.a), t_key)


def _transition_class_key_id(tr, s_id: int, features: _TimeFeatures):
    """Int-keyed variant: s_id replaces _grid_key(tr.s) — O(1) hash."""
    if features.raw_t:
        t_key = ("raw", int(tr.t))
    elif features.periods:
        t_key = tuple((m, int(tr.t) % m) for m in features.periods)
    else:
        t_key = ()
    return (s_id, int(tr.a), t_key)


def _grid_wrong_cells(pred, target) -> int:
    """Count mismatches without memoizing ephemeral Python identities."""
    try:
        import numpy as _np
        return int((_np.asarray(pred, dtype=_np.uint8)
                    != _np.asarray(target, dtype=_np.uint8)).sum())
    except ImportError:
        return sum(1 for y in range(len(target)) for x in range(len(target[0]))
                   if pred[y][x] != target[y][x])


def _diff_cell_set(s, target) -> "set[tuple[int, int]]":
    return {(y, x) for y in range(len(target)) for x in range(len(target[0]))
            if s[y][x] != target[y][x]}


def _extremal_cells(g, match, axis, extreme, count) -> "set[tuple[int, int]]":
    n = int(count)
    if n <= 0:
        return set()
    cells = set()
    if axis == "row":
        for y, row in enumerate(g):
            idxs = [x for x, c in enumerate(row) if c == match]
            for x in (idxs[:n] if extreme == "min" else idxs[-n:]):
                cells.add((y, x))
    else:
        w = len(g[0])
        for x in range(w):
            idxs = [y for y in range(len(g)) if g[y][x] == match]
            for y in (idxs[:n] if extreme == "min" else idxs[-n:]):
                cells.add((y, x))
    return cells


def _rule_rate_count(rule: dict, t: int) -> int:
    if "rate" not in rule:
        return int(rule.get("count", 1))
    p, q = int(rule["rate"][0]), int(rule["rate"][1])
    tt = int(t)
    return ((tt + 1) * p) // q - (tt * p) // q


def _rule_static_footprint(g, rule: dict, t: int) -> "set[tuple[int, int]] | None":
    """Cells a single rule may write, over-approximated from the step-start grid.

    Soundness is by abstraction: the concrete write set of a rule is mapped
    upward to a per-cell footprint element, and every later lower-bound query
    only reasons about cells outside that element. Guards are ignored, which can
    only add cells. When a rule pattern would require a relational abstract state
    we do not track, callers fall back to TOP (the whole grid), preserving
    `abstract_footprint >= concrete_writes`.
    """
    op = rule.get("op")
    h = len(g)
    w = len(g[0]) if h else 0
    if op == "identity":
        return set()
    if op == "translate_block":
        from ztare.worldmodel.spec_catalog import _qualifying_components
        out = set()
        dy, dx = int(rule["dy"]), int(rule["dx"])
        for comp in _qualifying_components(g, rule):
            for (y, x) in comp:
                out.add((y, x))
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w:
                    out.add((ny, nx))
        return out
    if op == "recolor_map":
        keys = {int(k) for k in rule["mapping"].keys()}
        return {(y, x) for y, row in enumerate(g) for x, c in enumerate(row) if c in keys}
    if op == "consume_extremal":
        return _extremal_cells(g, int(rule["color"]), rule.get("axis", "row"),
                               rule.get("extreme", "min"), _rule_rate_count(rule, t))
    if op == "accumulate_extremal":
        return _extremal_cells(g, int(rule.get("from", 0)), rule.get("axis", "row"),
                               rule.get("extreme", "min"), _rule_rate_count(rule, t))
    if op == "region_event":
        if rule.get("content_states") is not None:
            y0, x0, y1, x1 = (int(v) for v in rule["region"])
            return {(y, x) for y in range(max(0, y0), min(h - 1, y1) + 1)
                    for x in range(max(0, x0), min(w - 1, x1) + 1)}
        if isinstance(rule.get("writes"), (list, tuple)):
            return {(int(y), int(x)) for _c, cs in rule.get("writes", []) for (y, x) in cs
                    if 0 <= int(y) < h and 0 <= int(x) < w}
    return None


# Warm-start verify memo: prior_spec x log identity → replay_consistency_gate().ok bool.
# Key: (prior_spec_sha, log_len, log_fingerprint)
# log_fingerprint: sha256 of repr of first+last transition (fast; detects log growth or swap).
# Cleared lazily when log_len changes vs last seen (log growth always changes len).
# ponytail: module-level dict; never evicted (prior_spec changes every warm start; log grows
# monotonically; stale entries are unreachable by key collision).
_WARM_VERIFY_MEMO: dict[tuple, bool] = {}


def _log_fingerprint(log: EpisodeLog) -> str:
    """O(1) content fingerprint of the log using first+last row from _rows list."""
    import hashlib as _hl
    rows = log._rows  # list[Transition]; O(1) access
    if not rows:
        return "empty"
    first, last = rows[0], rows[-1]
    raw = f"{first.t}:{first.a}:{hash(first.s_next)}|{last.t}:{last.a}:{hash(last.s_next)}"
    return _hl.sha256(raw.encode()).hexdigest()[:12]


def _warm_verify_ok(pstep: "object", prior_spec: dict, log: EpisodeLog) -> bool:
    """Memoized replay_consistency_gate(pstep, log).ok for warm-start verification.

    Key includes prior_spec content hash so a changed spec never hits a stale entry.
    Cleared automatically when log length changes between calls (log growth path).
    """
    import hashlib as _hl
    spec_sha = _hl.sha256(
        json.dumps(prior_spec, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    key = (spec_sha, len(log), _log_fingerprint(log))
    if key in _WARM_VERIFY_MEMO:
        import logging as _logging
        _logging.getLogger(__name__).debug("warm_verify memo hit spec_sha=%s", spec_sha)
        return _WARM_VERIFY_MEMO[key]
    result = replay_consistency_gate(pstep, log).ok
    _WARM_VERIFY_MEMO[key] = result
    return result


def _spec_static_footprint(spec, tr) -> "set[tuple[int, int]] | None":
    """Per-transition write-footprint abstraction for a WORLD_MODEL_SPEC.

    Galois framing: concrete semantics map a candidate to the exact cells where
    `step(s,a,t)` differs from identity; the abstraction maps it to an
    over-approximate footprint in the powerset lattice of grid cells, with TOP
    represented by `None`. Because every rule's concrete writes are contained in
    this footprint, any observed changed cell outside it must remain at the
    identity value under the candidate and is therefore a guaranteed wrong cell.
    Multiple translations after prior writes can change component geometry, so
    that relational case uses TOP rather than risking an under-approximation.
    """
    if not isinstance(spec, dict):
        return None
    actions = spec.get("actions", {})
    rules = list(actions.get(str(tr.a), actions.get(int(tr.a), [])) or [])
    rules += list(spec.get("always") or [])
    translate_seen = 0
    prior_may_write = False
    fp = set()
    for rule in rules:
        if not isinstance(rule, dict):
            return None
        if rule.get("op") == "translate_block":
            translate_seen += 1
            if translate_seen > 1 or prior_may_write:
                return None
        rfp = _rule_static_footprint(tr.s, rule, tr.t)
        if rfp is None:
            return None
        fp |= rfp
        if rule.get("op") != "identity" and rfp:
            prior_may_write = True
    return fp


def _target_diff_from_key(start, target_key) -> "set[tuple[int, int]]":
    return {(y, x) for y in range(len(target_key)) for x in range(len(target_key[0]))
            if start[y][x] != target_key[y][x]}


def _galois_footprint_lower_bound(step, log, metric: str, env=frozenset()) -> int:
    """Sound lower bound on a candidate score from observed diffs outside footprint.

    The abstract domain is the per-cell footprint powerset, ordered by subset
    with TOP = whole grid/unknown. The abstraction over-approximates concrete
    candidate writes. Therefore, for any transition, every observed changed cell
    outside the abstract footprint is a cell where the candidate must predict the
    identity value while the target differs. For `cell` scoring we sum those
    cells. For `transition` scoring we count one guaranteed bad transition when
    the outside set is non-empty. In both cases the lower bound is <= the true
    score, including quotient multiplicities.
    """
    spec = getattr(step, "_ztare_world_model_spec", None)
    if spec is None:
        return 0
    ctx = _score_context_for(log)
    env = frozenset(int(i) for i in env)
    if ctx is not None:
        classes = ctx.classes_for(log, _step_time_features(step), env)
        if classes is not None:
            total = 0
            for cls in classes:
                fp = _spec_static_footprint(spec, cls.representative)
                if fp is None:
                    return 0
                for target, n in cls.target_counts.items():
                    outside = _target_diff_from_key(cls.representative.s, target) - fp
                    total += n * (len(outside) if metric == "cell" else int(bool(outside)))
            return total
    total = 0
    for i, tr in enumerate(log):
        if i in env:
            continue
        fp = _spec_static_footprint(spec, tr)
        if fp is None:
            return 0
        outside = _diff_cell_set(tr.s, tr.s_next) - fp
        total += len(outside) if metric == "cell" else int(bool(outside))
    return total


def _galois_before_full_score(step, log, incumbent, metric: str, env=frozenset()):
    """Return a pruning score when the footprint bound already beats incumbent.

    This never changes a winner: pruning fires only on `lower_bound > incumbent`,
    so the candidate cannot improve the primary score or tie for a shorter MDL
    comparison. With `ZTARE_GALOIS_PRUNE=0` this hook is inert and callers take
    the exact old scoring path.
    """
    if incumbent is None or not _galois_prune_enabled():
        return None
    stats = _galois_stats()
    if stats is not None:
        stats.bounded_candidates += 1
    lb = _galois_footprint_lower_bound(step, log, metric, env)
    if lb > incumbent:
        if stats is not None:
            stats.footprint_pruned += 1
        return lb
    if stats is not None:
        stats.full_scored += 1
    return None


def _galois_note_early_exit():
    stats = _galois_stats()
    if stats is not None:
        stats.early_exited += 1


def abduce_spec(log: EpisodeLog, action_arity: int,
                _effect_refine: bool = True,
                prior_spec: "dict | None" = None,
                verified_prefix: int = 0,
                _display_refine: bool = True,
                warm_only: bool = False,
                nogood_project: "str | None" = None) -> AbductionResult:
    """Per-transition rule abduction -> pooled per-action assembly -> lowering
    -> replay verification. Deterministic; zero model calls. `_effect_refine`
    toggles the rule-coupling (when_effect) post-pass — the harness computes the
    pre-coupling baseline with it off, so 'strictly improves' is measurable.

    `prior_spec` (CEGIS warm start / version-space standing hypothesis): a
    champion from a prior round. Verified FIRST against the log through the same
    replay gate; if still clean it is returned immediately (no ~5-min search),
    else its per-action rule-lists seed the search as high-priority options.

    `warm_only` asks only the champion-first question. It is for callers that
    already run the full miner elsewhere and need a proportional checkpoint:
    prove the standing champion still gates, or return a bounded refutation
    without re-identifying the whole log.
    """
    score_ctx = _install_score_context(log)
    # ---- CHAMPION-FIRST WARM START ----------------------------------------
    # The standing champion is the first hypothesis to test. If it still replays
    # the log clean — the SAME gate over the SAME env frames the full pipeline
    # uses — it is already a gate-passing champion; skip the search. Else fall
    # through, seeding its per-action rule-lists as first options (below).
    prior_actions: "dict[int, list]" = {}
    if prior_spec is not None:
        pstep, _perr = lower_spec(prior_spec)
        if pstep is not None:
            # FULL-LOG VERIFY: always verify the prior against the complete log.
            # The suffix shortcut was REMOVED (2026-07-09, F1 soundness fix):
            # env_frame_indices uses majority heuristics over the full episode;
            # a suffix's env-frame set systematically excludes the reset rows
            # that appear early in the log — exactly the rows a misfit spec
            # tends to mispredict. Verifying only the suffix would let a
            # refuted prior pass if its only counterexamples were reset-adjacent
            # frames that the suffix's env-frame classifier happened to promote.
            # Always use the full log so the gate's frame classification and the
            # verify scope are identical. verified_prefix parameter is retained
            # for the caller's API but no longer shortcuts the verify path.
            if _warm_verify_ok(pstep, prior_spec, log):  # ponytail: memoized; key = (spec_sha, log_len, log_fingerprint)
                return AbductionResult(
                    status="spec_identified", spec=prior_spec, step_fn=pstep,
                    rules_by_action={int(a): len(rs)
                                     for a, rs in prior_spec.get("actions", {}).items()},
                    replay_ok=True,
                    detail="warm: prior replay-consistent (full-log verified)",
                    quotient_stats=(score_ctx.summary_for_spec(prior_spec)
                                    if score_ctx is not None else {}),
                    galois_stats=_galois_summary())
        prior_actions = {int(a): list(rs)
                         for a, rs in prior_spec.get("actions", {}).items()}
        if warm_only:
            return AbductionResult(
                status="prior_refuted",
                spec=prior_spec,
                step_fn=pstep,
                rules_by_action={int(a): len(rs)
                                 for a, rs in prior_spec.get("actions", {}).items()},
                replay_ok=False,
                detail=(
                    "warm_only: prior failed replay; full re-abduction deferred "
                    "to the producer path"
                ),
                quotient_stats=(score_ctx.summary_for_spec(prior_spec)
                                if score_ctx is not None else {}),
                galois_stats=_galois_summary(),
            )

    # NOISE DEFERRAL (2026-07-05): mining sees only recurring-signature frames;
    # gates and final status judge the FULL log (deferred frames stay residual,
    # visible to cards/checkpoints — deferred, never dropped).
    full_log = log
    from ztare.worldmodel.gates import env_frame_indices as _efi
    _deferred = _noise_deferred_frames(log, _efi(log))
    if _deferred:
        # Preserve Transition object identity so the active score context can
        # quotient the filtered log against the original installed rows.
        _kept = type(log)([_tr for _i, _tr in enumerate(log) if _i not in _deferred])
        log = _kept

    # collect candidate rules per action; separate the action-independent
    # residue (rules appearing for every action = "always" dynamics)
    per_action: "dict[int, Counter]" = defaultdict(Counter)
    for tr in log:
        d = _diff(tr.s, tr.s_next)
        if not d:
            per_action[tr.a][("identity",)] += 1
            continue
        found = (_abduce_translate_block(tr.s, tr.s_next, d)
                 + _abduce_consume_extremal(tr.s, tr.s_next, d)
                 + _abduce_accumulate_extremal(tr.s, tr.s_next, d)
                 + _abduce_recolor_map(tr.s, tr.s_next, d))
        # subsumption lattice, not sequential fallback (external review):
        # CoM translation is the GENERAL family, rigid its DeltaPixels=0
        # member — emit both; behavioral dedup collapses them where they
        # coincide, the population/MDL machinery keeps both alive where they
        # diverge, and disagreement probing discriminates (version-space via
        # the candidate pool, preserving the specificity bias MDL provides)
        found += _abduce_translate_com(tr.s, tr.s_next, d)
        for r in found:
            per_action[tr.a][_freeze(r)] += 1

    # rules seen under every action are action-independent ("always")
    always_keys = None
    for a in range(action_arity):
        keys = {k for k in per_action.get(a, ()) if k != ("identity",)}
        always_keys = keys if always_keys is None else (always_keys & keys)
    always_keys = always_keys or set()
    always_rules = [_thaw(k) for k in sorted(always_keys, key=repr)]

    # PER-ACTION SELECTION (not pooling): abduction proposes VARIANTS per
    # action (e.g. a free move and a stale parameter set from another state);
    # applying all of them breaks replay. For each action, test each variant
    # (plus the always rules) against ONLY that action's transitions and keep
    # the most frequent variant that explains them all — refusal semantics in
    # translate_block make blocked transitions consistent for free.
    by_action_transitions = defaultdict(list)
    for tr in log:
        by_action_transitions[tr.a].append(tr)

    # ---- CROSS-RUN NOGOOD LEDGER (env-gated, default off) ------------------
    # FEED: a candidate rule-list rejected on a VISIBLE replay counterexample is
    # persisted (behavior signature + first mismatch). CONSULT: a candidate that
    # PROVABLY reproduces a recorded visible counterexample is skipped, so a spec
    # refuted in run N is not re-scored from scratch in run N+1. Inert unless
    # both a project is threaded AND ZTARE_SPEC_NOGOOD is on.
    _nogood = None
    _visible_clauses: dict = {}
    if nogood_project is not None:
        from ztare.worldmodel import spec_nogood as _sng
        if _sng.enabled():
            _nogood = _sng.SpecNogoodLedger(nogood_project)
            _visible_clauses = _nogood.visible_clauses()

    def _nogood_pruned(rules, frag) -> bool:
        """CONSULT: True iff a recorded visible clause matches this candidate's
        behavior signature AND the candidate provably reproduces that recorded
        wrong prediction (never prunes a spec that would gate clean)."""
        if not _visible_clauses or frag is None:
            return False
        from ztare.worldmodel import spec_nogood as _sng
        clause = _visible_clauses.get(_sng.behavior_signature(rules))
        if clause is not None and _sng.reproduces(clause, frag):
            stats = _galois_stats()
            if stats is not None:
                stats.nogood_pruned += 1
            return True
        return False

    def _explains(rules: "list[dict]", trs) -> bool:
        frag, _e = lower_spec({"actions": {"0": rules}, "always": always_rules})
        if frag is None:
            return False
        return all(frag(tr.s, 0, tr.t) == tr.s_next for tr in trs)

    # ---- POPULATION ASSEMBLER (multi-hypothesis, void-mining lesson) ----
    # per-action OPTION LISTS: every candidate rule-list that explains ALL of
    # that action's transitions (singles, then guarded/conditional pairs);
    # cross-product with always-variants; verify each assembly on the full
    # log; best = fewest mismatches, then fewest rules (MDL).
    from itertools import permutations, product as _product

    def _options_for(a, always_opt):
        trs = by_action_transitions.get(a, [])
        cands = [k for k, _n in per_action.get(a, Counter()).most_common()
                 if k != ("identity",) and k not in always_keys]
        expl_cache = {}

        def expl(rules):
            key = tuple(_freeze_deep(r) for r in rules)
            if key in expl_cache:
                return expl_cache[key]
            frag, _e = lower_spec({"actions": {"0": rules}, "always": always_opt})
            ok = frag is not None
            if ok:
                for tr in trs:
                    if frag(tr.s, 0, tr.t) != tr.s_next:
                        ok = False
                        # FEED: this candidate rule-list is refuted by a VISIBLE
                        # replay counterexample — persist the behavior signature
                        # + first mismatch as a visible-provenance nogood.
                        if _nogood is not None:
                            _nogood.record_visible(rules, tr, frag(tr.s, 0, tr.t))
                        break
            expl_cache[key] = ok
            return ok

        # CONSULT (cross-run): a single-rule candidate that PROVABLY reproduces a
        # recorded visible counterexample would fail `expl` as a single anyway, so
        # skipping it here only saves the replay — it never removes an option
        # `expl` would have kept, so the winner is unchanged (it stays available to
        # the pair/guard search below via `cands`). Never changes a winner.
        def _single_option(k):
            r = _thaw(k)
            if _visible_clauses:
                frag, _e = lower_spec({"actions": {"0": [r]}, "always": always_opt})
                if _nogood_pruned([r], frag):
                    return None
            return [r] if expl([r]) else None

        opts = [o for o in (_single_option(k) for k in cands[:8]) if o is not None]
        if not opts and expl([{"op": "identity"}]):
            opts = [[{"op": "identity"}]]
        if not opts:
            for k1, k2 in permutations(cands[:6], 2):
                r1, r2 = _thaw(k1), _thaw(k2)
                if expl([r1, r2]):
                    opts.append([r1, r2])
                    if len(opts) >= 2:
                        break
                if r1.get("op") == r2.get("op"):
                    base_frag, _ = lower_spec(
                        {"actions": {"0": [{"op": "identity"}]},
                         "always": always_opt}
                    )
                    frag1, _ = lower_spec(
                        {"actions": {"0": [r1]}, "always": always_opt}
                    )
                    frag2, _ = lower_spec(
                        {"actions": {"0": [r2]}, "always": always_opt}
                    )
                    set1 = [
                        tr for tr in trs
                        if frag1 is not None
                        and base_frag is not None
                        and frag1(tr.s, 0, tr.t) == tr.s_next
                        and frag1(tr.s, 0, tr.t) != base_frag(tr.s, 0, tr.t)
                    ]
                    set2 = [
                        tr for tr in trs
                        if tr not in set1
                        and frag2 is not None
                        and base_frag is not None
                        and frag2(tr.s, 0, tr.t) == tr.s_next
                        and frag2(tr.s, 0, tr.t) != base_frag(tr.s, 0, tr.t)
                    ]
                    if set1 and set2:
                        guard = _separating_count(set2, set1)
                        if guard is not None:
                            g2 = dict(r2)
                            g2["when_count"] = guard
                            g2["stop_if_applied"] = True
                            if expl([g2, r1]):
                                opts.append([g2, r1])
        if not opts:
            best = [_thaw(cands[0])] if cands else [{"op": "identity"}]
            opts = [best]
        # warm-start seed: the prior champion's rule-list for this action is the
        # standing hypothesis — try it FIRST (highest priority) when it still
        # explains this action's transitions. MDL remains the arbiter.
        seed = prior_actions.get(a)
        if seed is not None and seed not in opts and expl(seed):
            return ([seed] + opts)[:3]
        return opts[:3]

    # colors that translate under actions = the mover palette (rect locators)
    mover_colors = sorted({int(c)
                           for a in per_action for k in per_action[a]
                           for r in (_thaw(k),) if r.get("op") == "translate_block"
                           for c in r.get("match_colors", [])})

    # always-variants: unguarded, and per-rule stump-guarded (fired/paused split)
    always_variants = [always_rules]
    overlap_variants = []
    if always_rules:
        guarded = []
        any_guard = False
        for idx, ar0 in enumerate(always_rules):
            frag, _e = lower_spec({"actions": {"0": [{"op": "identity"}]}, "always": [ar0]})
            fired, paused = [], []
            for tr in log:
                (fired if (frag and frag(tr.s, 0, tr.t) == tr.s_next) or
                 _effect_present(ar0, tr) else paused).append(tr)
            g = _separating_count(fired, paused) if (fired and paused) else None
            ar = ar0
            if g is not None:
                ar = dict(ar0)
                ar["when_count"] = g
                any_guard = True
            guarded.append(ar)
            # POSITIONAL PAUSE candidates: a mechanic may be suppressed not by a
            # count but by the mover overlapping a fixed region (a key-window).
            # Learn the rect from the mover's cells on the ACTIVE, non-reset
            # paused steps — drop no-op frames and refills, neither is a real
            # pause — and emit when_overlap variants; the assembler/MDL keeps one
            # iff it cuts mismatches. Try each mover color alone too: a compound
            # mover's pure color localizes the rect where the full palette
            # (static same-color twins) blows the bbox up to the whole grid.
            color = ar0.get("color")
            active_paused = [tr for tr in paused if _diff(tr.s, tr.s_next)
                             and not (color is not None
                                      and _count(tr.s_next, color) > _count(tr.s, color))]
            if active_paused and fired and mover_colors:
                for cols in [mover_colors] + [[c] for c in mover_colors]:
                    box = _cells_bbox(active_paused, cols)
                    if box is None:
                        continue
                    for m in (0, 1):
                        wo = [cols, max(0, box[0] - m), max(0, box[1] - m),
                              box[2] + m, box[3] + m]
                        og = dict(ar0)
                        og["when_overlap"] = wo
                        overlap_variants.append(
                            [og if i == idx else dict(r)
                             for i, r in enumerate(always_rules)])
            # PERIODIC PAUSE (when_phase): a blinker fires on a t-period that no
            # count/overlap guard can express; learn (m, r) from the fired-frame
            # residues when the split is clean under some small divisor.
            if fired and paused and active_paused:
                ph = _separating_phase(fired, active_paused, _candidate_periods(log))
                if ph is not None:
                    pg = dict(ar0)
                    pg["when_phase"] = ph
                    overlap_variants.append(
                        [pg if i == idx else dict(r)
                         for i, r in enumerate(always_rules)])
        if any_guard:
            always_variants.append(guarded)

    best_spec, best_step, best_bad, best_rules = None, None, None, 10**9
    if prior_spec is not None:
        pstep, _perr = lower_spec(prior_spec)
        if pstep is not None:
            pbad = _mismatch_count(pstep, log)
            best_spec, best_step = prior_spec, pstep
            best_bad = pbad
            best_rules = spec_description_length(prior_spec)
    tried = 0
    for always_opt in always_variants:
        per_a_opts = {a: _options_for(a, always_opt) for a in range(action_arity)}
        # OBSERVATIONAL-EQUIVALENCE MEMO (e-graph shared sub-evaluation): a
        # transition of action a consults only actions[a] + always, never any
        # other action's rules (see lower_spec: `actions.get(int(action))`). So
        # a combo's full-log mismatch is EXACTLY the sum, over actions, of the
        # mismatch on that action's own transitions under its chosen option.
        # Score each (action, option) once here and reuse across the <=64 combos
        # below, replacing 64 full-log replays with sum_a|options_a| partial ones.
        partial = {}
        for a in range(action_arity):
            trs_a = by_action_transitions.get(a, [])
            col = []
            for opt in per_a_opts[a]:
                st, _e = lower_spec({"actions": {str(a): list(opt)}, "always": always_opt})
                col.append(_mismatch_count(st, trs_a) if st is not None else None)
            partial[a] = col
        for idxs in _product(*(range(len(per_a_opts[a])) for a in range(action_arity))):
            tried += 1
            if tried > 64:
                break
            combo = [per_a_opts[a][idxs[a]] for a in range(action_arity)]
            cand_spec = {"actions": {str(a): list(combo[a]) for a in range(action_arity)},
                         "always": always_opt}
            parts = [partial[a][idxs[a]] for a in range(action_arity)]
            if any(p is None for p in parts):        # a mini failed to lower -> full replay
                step_c, _e = lower_spec(cand_spec)
                if step_c is None:
                    continue
                bad = _mismatch_count(step_c, log, incumbent=best_bad)
            else:
                bad = sum(parts)                     # == _mismatch_count(full, log), by decomposition
            # MDL: fewest mismatches, then shortest description length (the
            # kernel's size-based MDL, not a bespoke rule count — same metric a
            # future MDLLibrary keep/retire would use; cf. leanmill size_fn)
            dl = spec_description_length(cand_spec)
            if best_bad is None or bad < best_bad or (bad == best_bad and dl < best_rules):
                step_c, _e = lower_spec(cand_spec)
                best_spec, best_step, best_bad, best_rules = cand_spec, step_c, bad, dl
            if bad == 0:
                break
        if best_bad == 0:
            break

    # POSITIONAL PAUSE (post-selection): swap each positional-guard variant into
    # the winning always-block and keep it only if it STRICTLY cuts mismatches —
    # a guard earns its place by explaining more, never by tying (MDL). Cheap: a
    # handful of full-log replays, no per-action re-optioning, so a mechanic no
    # count guard can express is still recoverable without slowing the assembler.
    if best_spec is not None and overlap_variants:
        for og_always in overlap_variants:
            cand = {"actions": best_spec["actions"], "always": og_always}
            st, _e = lower_spec(cand)
            if st is None:
                continue
            bad = _mismatch_count(st, log, incumbent=best_bad)
            if bad < best_bad:
                best_spec, best_step, best_bad = cand, st, bad

    # ---- PHYSICS CLOSURE (broaden dests + region-event mining) ----
    # The residual after the best move/consume assembly is, on real
    # substrates: moves the model REFUSED because the sprite crosses terrain
    # its witnessed require_dest set excluded, and region-crossing WRITES
    # (terrain restored behind the moved sprite, a plate/flag toggled, a HUD
    # updated at a distance). Broaden each mover's destinations to every
    # witnessed-passable color, then learn one region_event per recurring
    # residual-write. The timer-pause (when_overlap) and a region write are
    # coupled on the same frames — a frame stays wrong until BOTH land — so
    # each overlap-variant always-block is tried as the mining base and the
    # min-mismatch closure wins. Every step is kept only if it STRICTLY cuts
    # mismatches (MDL: a guard/write earns its place by explaining more).
    sel_mover = mover_colors
    if best_spec is not None:
        # the mover palette for closure is the SELECTED movers' colors, not the
        # global candidate pool — the pool is polluted by spurious single-color
        # (floor/patch) translate proposals from the noisy frames, and a
        # floor-colored "mover" makes every rect overlap-true forever
        sel_mover = sorted({int(c) for rules in best_spec["actions"].values()
                            for r in rules if r.get("op") == "translate_block"
                            for c in r.get("match_colors", [])}) or mover_colors
    prior_region_receipt = (
        prior_spec is not None
        and best_spec == prior_spec
        and any(r.get("op") == "region_event"
                for r in prior_spec.get("always", []))
    )
    if best_spec is not None and not prior_region_receipt:
        b_actions = _broaden_dests(best_spec["actions"], log, sel_mover)
        for base_always in [best_spec["always"]] + overlap_variants:
            st0, _e = lower_spec({"actions": b_actions, "always": base_always})
            if st0 is None:
                continue
            rc_all = [r["color"] for r in base_always if r.get("op") == "consume_extremal"]
            cur_always, cur_step = list(base_always), st0
            cur_bad = _mismatch_count(st0, log)
            # cache the current chain's per-transition prediction; a mined event
            # appends LAST and carries no guard, so scoring base+[ev] is one
            # region-write apply on top of the cache — not a fresh 64x64 chain
            # replay per event. Refresh the cache only when an event is accepted
            # (the chain changed); that is a handful of times, not once per event.
            preds = _predict_all(cur_step, log)
            for ev in _abduce_region_events(cur_step, log, sel_mover, rc_all):
                if any(str(k).startswith("when_") for k in ev):   # guarded -> exact replay
                    stc, _e = lower_spec({"actions": b_actions, "always": cur_always + [ev]})
                    b = _mismatch_count(stc, log, incumbent=cur_bad) if stc is not None else None
                else:
                    b = _append_event_mismatch(preds, ev, log, incumbent=cur_bad)
                if b is not None and b < cur_bad:
                    cur_always = cur_always + [ev]
                    cur_step, _e = lower_spec({"actions": b_actions, "always": cur_always})
                    cur_bad, preds = b, _predict_all(cur_step, log)
            if cur_bad < best_bad:
                best_spec = {"actions": b_actions, "always": cur_always}
                best_step, best_bad = cur_step, cur_bad

    # ---- ACTION-SCOPING (post-closure) ----
    # the positional pause / region_event learned above are action-independent;
    # scope any that an action counterexample refutes (a mover in the same
    # key-window cell that ticks the timer under one action, pauses under
    # another). No-op unless the log carries the disambiguating frame.
    if best_spec is not None:
        if os.environ.get("ZTARE_REFINE_LADDER", "1") != "0":
            from ztare.worldmodel.refinement_ladder import run_refinement_ladder

            best_spec, best_step = run_refinement_ladder(
                best_spec, best_step, log,
                {"effect_refine": _effect_refine,
                 "display_refine": _display_refine,
                 "selected_mover_colors": sel_mover},
            )
        else:
            best_spec, best_step = _action_scope_refine(best_spec, log)
            best_spec, best_step = _region_guard_refine(best_spec, log)
            if _effect_refine:
                best_spec, best_step = _effect_guard_refine(best_spec, log)
                best_spec, best_step = _dest_guard_refine(best_spec, log)
                # a refusal-broadening the physics closure DROPPED (its improvement
                # was masked by the then-unguarded coupled rule on the same frames)
                # may strictly improve now that the guard landed — retry it once
                b2 = _broaden_dests(best_spec["actions"], log, sel_mover)
                st2, _e2 = lower_spec({"actions": b2, "always": best_spec["always"]})
                cur_mismatch = _mismatch_count(best_step, log)
                if st2 is not None and _mismatch_count(st2, log, incumbent=cur_mismatch) < cur_mismatch:
                    best_spec = {"actions": b2, "always": best_spec["always"]}
                    best_step = st2
            best_spec, best_step = _rational_rate_consume_refine(best_spec, log)
            best_spec, best_step = _periodic_consume_refine(best_spec, log)
            best_spec, best_step = _prune_region_writes(best_spec, log)
            # DISPLAY-LAW closure (LAST): a residual display latched to persistent
            # state. First the REGION-STATE MACHINE (a whole-region glyph that cycles
            # through k>=3 patterns — the shift no cell-wise write can fit), then the
            # fixed-write enter-latch for any residual flag it doesn't own.
            if _display_refine:
                best_spec, best_step = _region_state_refine(best_spec, log)
                best_spec, best_step = _derived_display_refine(best_spec, log)

    spec, step = best_spec, best_step
    if step is None:
        return AbductionResult(status="no_catalog_law", detail="no assembly lowered",
                               quotient_stats=(score_ctx.summary_for_spec(best_spec)
                                               if score_ctx is not None and best_spec is not None
                                               else {}),
                               galois_stats=_galois_summary())
    replay = replay_consistency_gate(step, full_log)
    status = "spec_identified" if replay.ok else "partial"
    detail = replay.detail
    return AbductionResult(status=status, spec=spec, step_fn=step,
                           rules_by_action={a: len(v) for a, v in per_action.items()},
                           replay_ok=replay.ok, detail=detail,
                           quotient_stats=(score_ctx.summary_for_spec(spec)
                                           if score_ctx is not None else {}),
                           galois_stats=_galois_summary())


def _diff_key_numpy(s, s_next) -> tuple:
    """FIX D: sparse diff signature using numpy nonzero — O(changed cells) instead
    of O(H*W) Python loop + sort.  Output is byte-identical to the pure-Python form:
    a sorted tuple of (y, x, before, after) for every changed cell.
    The sort order is (y, x) ascending — numpy nonzero returns row-major order so
    the result is already sorted; we do NOT re-sort (that was the expensive step)."""
    try:
        import numpy as _np
        a = _np.array(s, dtype=_np.uint8)
        b = _np.array(s_next, dtype=_np.uint8)
        mask = a != b
        if not mask.any():
            return ()
        ys, xs = _np.where(mask)
        # row-major (y, x) order from np.where — equivalent to sorted() by (y,x)
        return tuple(
            (int(y), int(x), int(a[y, x]), int(b[y, x]))
            for y, x in zip(ys, xs)
        )
    except ImportError:
        # numpy absent: fall back to the original sorted-tuple path
        return tuple(sorted(
            (y, x, s[y][x], s_next[y][x])
            for y in range(len(s)) for x in range(len(s[0]))
            if s[y][x] != s_next[y][x]
        ))


def _noise_deferred_frames(log, env, min_support: int = 2) -> "set[int]":
    """Frames whose full diff-signature occurs fewer than `min_support` times
    (2026-07-05, measured: 72% of tu93 bootstrap signatures are singletons).
    A deterministic law needs recurrence; a single witness is indistinguishable
    from noise by any deterministic test, so such frames may not SEED or steer
    mining. They remain fully counted by replay gates and remain visible as
    residual for cards/checkpoints — deferred, never dropped. ZTARE_MIN_SUPPORT
    (default 2; 1 disables)."""
    import os as _os
    from collections import Counter as _C
    ms = int(_os.environ.get("ZTARE_MIN_SUPPORT", str(min_support)))
    if ms <= 1:
        return set()
    trs = list(log)
    keys = []
    segments: "list[list[int]]" = []
    cur_segment: "list[int]" = []
    prev_t = None
    for i, tr in enumerate(trs):
        t = int(tr.t)
        if cur_segment and prev_t is not None and t <= prev_t:
            segments.append(cur_segment)
            cur_segment = []
        cur_segment.append(i)
        prev_t = t
        if i in env:
            keys.append(None)
            continue
        # FIX D: use numpy sparse diff — ~6× faster at H=10,W=10; the output
        # tuple is identical in (y,x,before,after) order (np.where → row-major).
        d = _diff_key_numpy(tr.s, tr.s_next)
        k = (tr.a, d) if d else None
        keys.append(k)
    if cur_segment:
        segments.append(cur_segment)

    deferred: set[int] = set()
    for segment in segments:
        # Scope: this gate exists for large noise-dominated segments
        # (random-walk bootstrap). Short reset/branch segments are often the
        # exact new evidence a learner must mine, even when their signatures
        # are unique in the global log.
        if len(segment) < 200:
            continue
        sigs = _C(keys[i] for i in segment if keys[i] is not None)
        segment_deferred = {
            i for i in segment
            if keys[i] is not None and sigs[keys[i]] < ms
        }
        if len(segment_deferred) >= 0.4 * max(1, len(sigs)):
            deferred.update(segment_deferred)
    return deferred


def _mismatch_count(step, log, incumbent: "int | None" = None) -> int:
    pruned = _galois_before_full_score(step, log, incumbent, "transition")
    if pruned is not None:
        return pruned
    ctx = _score_context_for(log)
    if ctx is not None:
        classes = ctx.classes_for(log, _step_time_features(step))
        if classes is not None:
            bad = 0
            for cls in classes:
                pred = step(cls.representative.s, cls.representative.a, cls.representative.t)
                if pred is None:
                    bad += cls.multiplicity
                    if incumbent is not None and bad > incumbent:
                        _galois_note_early_exit()
                        return bad
                    continue
                bad += cls.multiplicity - cls.target_counts.get(_grid_key(pred), 0)
                if incumbent is not None and bad > incumbent:
                    _galois_note_early_exit()
                    return bad
            return bad
    bad = 0
    for tr in log:
        if step(tr.s, tr.a, tr.t) != tr.s_next:
            bad += 1
            if incumbent is not None and bad > incumbent:
                _galois_note_early_exit()
                return bad
    return bad


def _predict_all(step, log) -> "list[list[list[int]]]":
    """Per-transition prediction of `step` as MUTABLE list-of-lists grids — the
    cache the closure applies candidate events on top of."""
    return _PredictionRows([[list(r) for r in step(tr.s, tr.a, tr.t)] for tr in log],
                           _step_time_features(step))


def _append_event_mismatch(preds, ev, log, incumbent: "int | None" = None) -> int:
    """Mismatch count of (the chain that produced `preds`) + one region_event
    appended LAST. A mined region_event is guard-free and its trigger reads the
    step-start grid, so its ONLY effect is applying its write on top of the
    current prediction (e-graph observational equivalence: every earlier rule is
    unchanged). One O(rect) apply per transition replaces a full 64x64 chain
    replay per candidate. Byte-equivalent to _mismatch_count(lower(base+[ev]))."""
    from ztare.worldmodel.spec_catalog import _apply_region_event
    ctx = _score_context_for(log)
    if ctx is not None and isinstance(preds, _PredictionRows):
        classes = ctx.classes_for(log, preds.features)
        if classes is not None:
            bad = 0
            for cls in classes:
                rep_idx = cls.row_indices[0]
                g = _apply_region_event(preds[rep_idx], ev, cls.representative.s)
                g_key = _grid_key(g)
                bad += cls.multiplicity - cls.target_counts.get(g_key, 0)
                if incumbent is not None and bad > incumbent:
                    _galois_note_early_exit()
                    return bad
            return bad
    bad = 0
    for i, tr in enumerate(log):
        g = _apply_region_event(preds[i], ev, tr.s)
        if any(tuple(g[y]) != tr.s_next[y] for y in range(len(g))):
            bad += 1
            if incumbent is not None and bad > incumbent:
                _galois_note_early_exit()
                return bad
    return bad


def _candidate_event_guard_fires(rule, tr) -> bool:
    """Step-start guard subset used by display-refine candidate events."""
    tm = rule.get("when_t_mod")
    if tm is not None and int(tr.t) % int(tm[0]) != int(tm[1]):
        return False
    wp = rule.get("when_phase")
    if wp is not None and int(tr.t) % int(wp[0]) != int(wp[1]):
        return False
    wa = rule.get("when_action")
    if wa is not None and int(tr.a) not in {int(a) for a in wa}:
        return False
    wc = rule.get("when_count")
    if wc is not None:
        color, lo, hi = wc
        n = sum(1 for row in tr.s for c in row if c == int(color))
        if (lo is not None and n < int(lo)) or (hi is not None and n > int(hi)):
            return False
    wr = rule.get("when_region")
    if wr is not None:
        y0, x0, y1, x1, pat = (int(wr[0]), int(wr[1]), int(wr[2]),
                               int(wr[3]), [int(v) for v in wr[4]])
        h, w = len(tr.s), len(tr.s[0])
        k = 0
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                if not (0 <= yy < h and 0 <= xx < w) or k >= len(pat) \
                        or tr.s[yy][xx] != pat[k]:
                    return False
                k += 1
        if k != len(pat):
            return False
    return True


def _append_event_wrong_cell_count(preds, ev, log, env, incumbent: "int | None" = None) -> int:
    """Cell-mismatch count of cached base predictions plus one display event.

    `_derived_display_refine` appends a single region_event last. The earlier
    chain is unchanged, so each candidate can be scored by applying only that
    event to cached base predictions. This preserves the transition quotient and
    avoids lowering/replaying the full candidate spec for every rejected event.
    """
    write_map = {}
    for color, cells in ev.get("writes", []):
        for (y, x) in cells:
            write_map[(int(y), int(x))] = int(color)
    if incumbent is None or not write_map:
        from ztare.worldmodel.spec_catalog import _apply_region_event
    else:
        _apply_region_event = None

    def event_fires(tr, pred) -> bool:
        if not _candidate_event_guard_fires(ev, tr):
            return False
        wo = [list(ev["mover_colors"])] + list(ev["rect"])
        o0, o1 = _overlap_holds(tr.s, wo), _overlap_holds(pred, wo)
        return (o0 and not o1) if ev.get("edge", "exit") == "exit" else ((not o0) and o1)

    def apply_delta(total, tr, pred, target, n=1):
        if not event_fires(tr, pred):
            return total
        h, w = len(target), len(target[0])
        for (y, x), color in write_map.items():
            if 0 <= y < h and 0 <= x < w:
                total += n * ((color != target[y][x]) - (pred[y][x] != target[y][x]))
        return total

    ctx = _score_context_for(log)
    env = frozenset(int(i) for i in env)
    if ctx is not None and isinstance(preds, _PredictionRows):
        classes = ctx.classes_for(log, preds.features, env)
        if classes is not None:
            total = int(incumbent) if incumbent is not None and write_map else 0
            if write_map and incumbent is not None:
                for cls in classes:
                    rep = cls.representative
                    pred = preds[cls.row_indices[0]]
                    for target, n in cls.target_counts.items():
                        total = apply_delta(total, rep, pred, target, n)
                return total
            for cls in classes:
                rep = cls.representative
                pred = _apply_region_event(preds[cls.row_indices[0]], ev, rep.s) \
                    if _candidate_event_guard_fires(ev, rep) else preds[cls.row_indices[0]]
                for target, n in cls.target_counts.items():
                    total += n * _grid_wrong_cells(pred, target)
            return total
    total = int(incumbent) if incumbent is not None and write_map else 0
    for i, tr in enumerate(log):
        if i in env:
            continue
        if write_map and incumbent is not None:
            total = apply_delta(total, tr, preds[i], tr.s_next)
            continue
        if _candidate_event_guard_fires(ev, tr):
            pred = _apply_region_event(preds[i], ev, tr.s)
        else:
            pred = preds[i]
        total += _grid_wrong_cells(pred, tr.s_next)
    return total


def _effect_present(rule, tr) -> bool:
    """Did reality show this always-rule's effect in the transition? For
    consume rules: some cell of (color -> replacement) flipped."""
    if rule.get("op") != "consume_extremal":
        return False
    a, b = int(rule["color"]), int(rule["replacement"])
    return any(tr.s[y][x] == a and tr.s_next[y][x] == b
               for y in range(len(tr.s)) for x in range(len(tr.s[0])))


def _wrong_cell_count(step, log, env, incumbent: "int | None" = None) -> int:
    """Total mispredicted CELLS over non-env transitions — a finer strict-
    improvement metric than the transition count: when several mechanics
    misfire on the SAME frame, each partial fix earns credit (the transition
    stays 'bad' until all land, so a transition metric would reject every
    single fix and the coupled repair could never assemble)."""
    pruned = _galois_before_full_score(step, log, incumbent, "cell", env)
    if pruned is not None:
        return pruned
    ctx = _score_context_for(log)
    if ctx is not None:
        classes = ctx.classes_for(log, _step_time_features(step), frozenset(env))
        if classes is not None:
            total = 0
            for cls in classes:
                p = step(cls.representative.s, cls.representative.a, cls.representative.t)
                if p is None:
                    target = cls.representative.s_next
                    total += cls.multiplicity * len(target) * len(target[0])
                    if incumbent is not None and total > incumbent:
                        _galois_note_early_exit()
                        return total
                    continue
                for target, n in cls.target_counts.items():
                    total += n * _grid_wrong_cells(p, target)
                    if incumbent is not None and total > incumbent:
                        _galois_note_early_exit()
                        return total
            return total
    total = 0
    for i, tr in enumerate(log):
        if i in env:
            continue
        p = step(tr.s, tr.a, tr.t)
        if p is None:
            total += len(tr.s_next) * len(tr.s_next[0])
            if incumbent is not None and total > incumbent:
                _galois_note_early_exit()
                return total
            continue
        total += sum(1 for y in range(len(p)) for x in range(len(p[0]))
                     if p[y][x] != tr.s_next[y][x])
        if incumbent is not None and total > incumbent:
            _galois_note_early_exit()
            return total
    return total


def _overlap_holds(g, wo) -> bool:
    cs = {int(c) for c in wo[0]}
    y0, x0, y1, x1 = int(wo[1]), int(wo[2]), int(wo[3]), int(wo[4])
    return _overlap_holds_parts(g, cs, y0, x0, y1, x1)


def _overlap_holds_parts(g, cs, y0, x0, y1, x1) -> bool:
    h, w = len(g), len(g[0])
    for y in range(max(0, y0), min(h - 1, y1) + 1):
        for x in range(max(0, x0), min(w - 1, x1) + 1):
            if g[y][x] in cs:
                return True
    return False


def _event_crosses(tr, rule) -> bool:
    """Approximate the region_event trigger over a whole transition (mover in
    the rect at step-start xor at step-end, per edge). Close enough to the
    lowering's g0-vs-mid-chain test for detection: the mover's translate is the
    only thing that moves it across the rect."""
    wo = [list(rule["mover_colors"])] + list(rule["rect"])
    o0, o1 = _overlap_holds(tr.s, wo), _overlap_holds(tr.s_next, wo)
    return (o0 and not o1) if rule.get("edge", "exit") == "exit" else ((not o0) and o1)


def _event_write_present(tr, rule) -> bool:
    cells = [(int(y), int(x), int(c)) for c, cs in rule.get("writes", []) for (y, x) in cs]
    return all(0 <= y < len(tr.s_next) and 0 <= x < len(tr.s_next[0])
               and tr.s_next[y][x] == c for (y, x, c) in cells)


def _action_scope_refine(spec, log):
    """Post-closure: an always when_overlap pause, or a region_event, may
    OVER-fire across the action space — a frame where its positional guard
    holds (or its rect is crossed) yet reality shows the mechanic did NOT
    trigger. When such an action counterexample exists (two actions leave the
    mover in the same place but only one trips the mechanic — provable ONLY
    from the counterexample, never from a single episode), scope the guard to
    the actions where it genuinely fires, read straight off the log. Kept only
    if it strictly cuts wrong cells: same MDL/strict-improvement discipline as
    the physics-closure pass, on the finer cell metric (coupled mechanics on
    one frame each earn their fix)."""
    from ztare.worldmodel.gates import env_frame_indices
    env = env_frame_indices(log)
    rows = list(log)
    best_step, _e = lower_spec(spec)
    if best_step is None:
        return spec, best_step
    fired_by_sig: dict = {}
    bare_frag_by_sig: dict = {}

    def _effect_for(rule):
        rsig = _rule_signature(rule)
        if rsig not in fired_by_sig:
            bare_frag_by_sig[rsig] = _rule_bare_frag(rule)
            fired_by_sig[rsig] = [_rule_fired_in_reality(bare_frag_by_sig[rsig], tr) for tr in rows]
        return fired_by_sig[rsig]

    best_spec, best_wrong = spec, _wrong_cell_count(best_step, log, env)
    for idx, rule in enumerate(spec.get("always", [])):
        new_rule = None
        wo = rule.get("when_overlap")
        if rule.get("op") == "consume_extremal" and wo is not None and len(wo) == 5:
            pause_acts, tick_acts = set(), set()
            for tr in rows:
                if _overlap_holds(tr.s, wo):
                    (pause_acts if not _effect_present(rule, tr) else tick_acts).add(tr.a)
            if pause_acts and (tick_acts - pause_acts):
                new_rule = dict(rule)
                new_rule["when_overlap"] = list(wo) + [sorted(pause_acts)]
        elif rule.get("op") == "region_event" and "when_action" not in rule:
            write_acts, cross_only = set(), set()
            for tr in rows:
                if _event_crosses(tr, rule):
                    (write_acts if _event_write_present(tr, rule) else cross_only).add(tr.a)
            if write_acts and (cross_only - write_acts):
                new_rule = dict(rule)
                new_rule["when_action"] = sorted(write_acts)
        if new_rule is None:
            continue
        cand = {"actions": best_spec["actions"],
                "always": [new_rule if i == idx else r
                           for i, r in enumerate(best_spec["always"])]}
        st, _e = lower_spec(cand)
        if st is None:
            continue
        w = _wrong_cell_count(st, log, env, incumbent=best_wrong)
        if w < best_wrong:
            best_spec, best_step, best_wrong = cand, st, w
    return best_spec, best_step


def _candidate_periods(log) -> "list[int]":
    """Small periods to try for a blinker guard: divisors of the observed
    episode length (max t + 1) plus the small integers — evidence-derived from
    the log's own clock, no game constants."""
    ts = [tr.t for tr in log]
    if not ts:
        return []
    L = max(ts) + 1
    return sorted({m for m in range(2, L + 1) if L % m == 0} | set(range(2, 9)))


def _separating_phase(fired, paused, periods) -> "list | None":
    """A period m and residue r such that EVERY fired frame has t % m == r and NO
    paused frame does -> [m, r]. The blinker/clock guard, learned from t-residues
    when count/overlap/action cannot separate the fired/paused split."""
    for m in periods:
        fr = {int(tr.t) % m for tr in fired}
        if len(fr) != 1:
            continue
        r = next(iter(fr))
        if all(int(tr.t) % m != r for tr in paused):
            return [m, r]
    return None


def _is_unguarded_consume(rule) -> bool:
    return rule.get("op") == "consume_extremal" and not any(
        str(k).startswith("when_") for k in rule)


def _consume_schedule_key(rule) -> tuple:
    return (int(rule["color"]), int(rule["replacement"]),
            rule.get("axis", "row"), rule.get("extreme", "min"))


def _strip_consume_count(rule, count: int) -> dict:
    out = {k: v for k, v in rule.items()
           if k not in ("count", "rate") and not str(k).startswith("when_")}
    if int(count) > 1:
        out["count"] = int(count)
    return out


def _consume_variant(rule, count: int) -> dict:
    out = {k: v for k, v in rule.items() if k not in ("count", "rate")}
    if int(count) > 1:
        out["count"] = int(count)
    return out


def _transition_consume_count(tr, rule) -> "int | None":
    """Per-line consume count witnessed by one transition for a consume rule.
    Returns None when the colour's diff is not a pure extremal consume."""
    color, repl, axis, extreme = _consume_schedule_key(rule)
    scope_cells = None
    if rule.get("component_scope"):
        from ztare.worldmodel.spec_catalog import _selected_component_scope_cells

        scope_cells = _selected_component_scope_cells(
            [list(row) for row in tr.s], rule, {color}
        )
        if scope_cells is None:
            return None
    line_cells: "dict[int, list[int]]" = defaultdict(list)
    line_changed: "dict[int, list[int]]" = defaultdict(list)
    for y in range(len(tr.s)):
        for x in range(len(tr.s[0])):
            if scope_cells is not None and (y, x) not in scope_cells:
                continue
            a, b = tr.s[y][x], tr.s_next[y][x]
            if axis == "row":
                line, pos = y, x
            else:
                line, pos = x, y
            if a == color:
                line_cells[line].append(pos)
                if b == repl:
                    line_changed[line].append(pos)
                elif b != color:
                    return None
            elif b == color:
                return None
    if not line_cells:
        return 0
    counts = []
    for line, positions in line_cells.items():
        changed = sorted(line_changed.get(line, []))
        n = len(changed)
        ordered = sorted(positions)
        expected = ordered[:n] if extreme == "min" else ordered[-n:]
        if changed != expected:
            return None
        counts.append(n)
    uniq = set(counts)
    return next(iter(uniq)) if len(uniq) == 1 else None


def _fit_count_guard_consume_rules(rule, log, env) -> "list[dict] | None":
    """Split a variable consume magnitude by an observable source-count
    threshold. This is the finite decision-tree sibling of phase/rate refine:
    if rows with larger per-line consume count are exactly the rows whose
    step-start count(color) crosses a threshold, express the schedule as a base
    consume plus guarded extra consumes. Existing guards are preserved; an
    existing when_count is not compounded here."""
    if "when_count" in rule:
        return None
    color = int(rule["color"])
    obs = []
    for i, tr in enumerate(log):
        if i in env:
            continue
        n = _transition_consume_count(tr, rule)
        if n is None:
            return None
        feature = sum(1 for row in tr.s for c in row if c == color)
        obs.append((feature, int(n)))
    levels = sorted({n for _feature, n in obs})
    if len(levels) < 2:
        return None
    feats = sorted({f for f, _n in obs})

    def threshold(target):
        for lo in feats:
            if all((f >= lo) == target(f, n) for f, n in obs):
                return [color, int(lo), None]
        for hi in feats:
            if all((f <= hi) == target(f, n) for f, n in obs):
                return [color, None, int(hi)]
        return None

    out = []
    base = levels[0]
    if base > 0:
        out.append(_consume_variant(rule, base))
    prev = base
    for level in levels[1:]:
        guard = threshold(lambda _f, n, level=level: n >= level)
        if guard is None:
            return None
        extra = int(level) - int(prev)
        if extra <= 0:
            return None
        er = _consume_variant(rule, extra)
        er["when_count"] = guard
        out.append(er)
        prev = level
    return out or None


def _fit_periodic_consume_rules(rule, log, env) -> "list[dict] | None":
    obs = []
    for i, tr in enumerate(log):
        if i in env:
            continue
        n = _transition_consume_count(tr, rule)
        if n is None:
            return None
        obs.append((int(tr.t), int(n)))
    if len({n for _t, n in obs}) < 2:
        return None
    for m in range(2, 33):
        by_res = {}
        ok = True
        for t, n in obs:
            r = t % m
            if r in by_res and by_res[r] != n:
                ok = False
                break
            by_res[r] = n
        if not ok or len(set(by_res.values())) < 2:
            continue
        base = min(by_res.values())
        out = []
        if base > 0:
            out.append(_strip_consume_count(rule, base))
        for r, n in sorted(by_res.items()):
            extra = n - base
            if extra <= 0:
                continue
            er = _strip_consume_count(rule, extra)
            er["when_phase"] = [m, r]
            out.append(er)
        return out or None
    return None


def _fit_rational_rate_consume_rule(rule, log, env) -> "dict | None":
    """Fit a Bresenham-style rational consume count exactly:
    n_t = floor((t+1)*p/q) - floor(t*p/q), q <= 64. Only varying observed counts
    are considered; fixed counts stay on the existing count parameter."""
    from math import gcd
    obs = []
    for i, tr in enumerate(log):
        if i in env:
            continue
        n = _transition_consume_count(tr, rule)
        if n is None:
            return None
        obs.append((int(tr.t), int(n)))
    if len({n for _t, n in obs}) < 2:
        return None
    max_n = max(n for _t, n in obs)
    fits = set()
    for q in range(1, 65):
        for p in range(1, (max_n + 2) * q + 1):
            if all((((t + 1) * p) // q - (t * p) // q) == n for t, n in obs):
                g = gcd(p, q)
                fits.add((p // g, q // g))
    if not fits:
        return None
    p, q = min(fits, key=lambda pq: (pq[1], pq[0]))
    out = {k: v for k, v in rule.items()
           if k not in ("count", "rate") and not str(k).startswith("when_")}
    out["rate"] = [int(p), int(q)]
    return out


def _count_guard_consume_refine(spec, log):
    """Observable-state split for consume magnitude. Kept only on strict
    wrong-cell improvement."""
    import copy
    from ztare.worldmodel.gates import env_frame_indices
    env = env_frame_indices(log)
    best_step, _e = lower_spec(spec)
    if best_step is None:
        return spec, best_step
    best_spec = spec
    best_wrong = _wrong_cell_count(best_step, log, env)
    improved = True
    while improved:
        improved = False
        rules = list(best_spec.get("always", []))
        for idx, rule in enumerate(rules):
            if rule.get("op") != "consume_extremal" or "rate" in rule:
                continue
            mined = _fit_count_guard_consume_rules(rule, log, env)
            if not mined:
                continue
            cand_always = []
            for j, r in enumerate(rules):
                cand_always.extend(copy.deepcopy(mined) if j == idx else [copy.deepcopy(r)])
            cand = {"actions": copy.deepcopy(best_spec.get("actions", {})),
                    "always": cand_always}
            st, _e = lower_spec(cand)
            if st is None:
                continue
            w = _wrong_cell_count(st, log, env, incumbent=best_wrong)
            if w < best_wrong:
                best_spec, best_step, best_wrong = cand, st, w
                improved = True
                break
    return best_spec, best_step


def _rational_rate_consume_refine(spec, log):
    """Variable-rate consume schedule: prefer a single rational-rate rule over
    phase decomposition when the observed counts fit exactly. Kept only on
    strict non-env wrong-cell improvement."""
    import copy
    from ztare.worldmodel.gates import env_frame_indices
    env = env_frame_indices(log)
    best_step, _e = lower_spec(spec)
    if best_step is None:
        return spec, best_step
    best_spec = spec
    best_wrong = _wrong_cell_count(best_step, log, env)
    improved = True
    while improved:
        improved = False
        rules = list(best_spec.get("always", []))
        seen = set()
        for idx, rule in enumerate(rules):
            if not _is_unguarded_consume(rule):
                continue
            sig = _consume_schedule_key(rule)
            if sig in seen:
                continue
            seen.add(sig)
            mined = _fit_rational_rate_consume_rule(rule, log, env)
            if not mined:
                continue
            replace = {j for j, r in enumerate(rules)
                       if _is_unguarded_consume(r) and _consume_schedule_key(r) == sig}
            cand_always, inserted = [], False
            for j, r in enumerate(rules):
                if j in replace:
                    if not inserted:
                        cand_always.append(copy.deepcopy(mined))
                        inserted = True
                    continue
                cand_always.append(copy.deepcopy(r))
            cand = {"actions": copy.deepcopy(best_spec.get("actions", {})),
                    "always": cand_always}
            st, _e = lower_spec(cand)
            if st is None:
                continue
            w = _wrong_cell_count(st, log, env, incumbent=best_wrong)
            if w < best_wrong:
                best_spec, best_step, best_wrong = cand, st, w
                improved = True
                break
    return best_spec, best_step


def _component_scope_consume_refine(spec, log):
    """Quotient-scope an extremal consume law to the right component class.

    If an otherwise plausible consume rule over-fires on same-colour sibling
    components, restrict the rule to a selected connected-component quotient
    (largest/widest) and keep it only on strict full-log improvement. This is a
    parameter refinement of an existing operator, not a new substrate rule.
    """
    import copy
    from ztare.worldmodel.gates import env_frame_indices
    env = env_frame_indices(log)
    best_step, _e = lower_spec(spec)
    if best_step is None:
        return spec, best_step
    best_spec = spec
    best_wrong = _wrong_cell_count(best_step, log, env)
    improved = True
    while improved:
        improved = False
        locations = [("always", None, list(best_spec.get("always", [])))]
        for action, rules in best_spec.get("actions", {}).items():
            locations.append(("actions", action, list(rules)))
        for loc, action, rules in locations:
            for idx, rule in enumerate(rules):
                if rule.get("op") != "consume_extremal" or rule.get("component_scope"):
                    continue
                color = int(rule["color"])
                scope_candidates = _extremal_component_scope_candidates(rule)
                feature_values = sorted({
                    sum(1 for row in tr.s for c in row if c == color)
                    for i, tr in enumerate(log) if i not in env
                })
                seen = set()
                local_best_spec, local_best_step, local_best_wrong = None, None, best_wrong
                for scope in scope_candidates:
                    skey = json.dumps(scope, sort_keys=True)
                    if skey in seen:
                        continue
                    seen.add(skey)
                    cand = copy.deepcopy(best_spec)
                    target = cand["always"] if loc == "always" else cand["actions"][action]
                    target[idx] = {**target[idx], "component_scope": scope}
                    st, _e = lower_spec(cand)
                    if st is None:
                        continue
                    w = _wrong_cell_count(st, log, env, incumbent=local_best_wrong)
                    if w < local_best_wrong:
                        local_best_spec, local_best_step, local_best_wrong = cand, st, w
                    scoped_rule = {**rule, "component_scope": scope}
                    obs = []
                    for i, tr in enumerate(log):
                        if i in env:
                            continue
                        n = _transition_consume_count(tr, scoped_rule)
                        if n is None:
                            obs = []
                            break
                        feature = sum(1 for row in tr.s for c in row if c == color)
                        obs.append((feature, int(n)))
                    base_count = int(rule.get("count", 1))
                    for level in sorted({n for _f, n in obs if n > base_count}):
                        for lo in feature_values:
                            if not all((f >= lo) == (n >= level) for f, n in obs):
                                continue
                            low = dict(rule)
                            low["when_count"] = [color, None, int(lo) - 1]
                            high = {k: v for k, v in rule.items()
                                    if k not in ("count", "rate")
                                    and not str(k).startswith("when_")}
                            high["component_scope"] = scope
                            if level > 1:
                                high["count"] = int(level)
                            high["when_count"] = [color, int(lo), None]
                            cand = copy.deepcopy(best_spec)
                            target = cand["always"] if loc == "always" else cand["actions"][action]
                            target[idx:idx + 1] = [low, high]
                            st, _e = lower_spec(cand)
                            if st is None:
                                continue
                            w = _wrong_cell_count(st, log, env, incumbent=local_best_wrong)
                            if w < local_best_wrong:
                                local_best_spec, local_best_step, local_best_wrong = cand, st, w
                    if local_best_spec is not None and local_best_wrong < best_wrong:
                        best_spec, best_step, best_wrong = (
                            local_best_spec, local_best_step, local_best_wrong
                        )
                        improved = True
                        break
                if improved:
                    break
            if improved:
                break
    return best_spec, best_step


def _periodic_consume_refine(spec, log):
    """Variable-rate consume schedule: replace an underfitting consume group with
    a base consume plus phase-gated extras when the log's per-step counts fit a
    small period exactly. Kept only on strict non-env wrong-cell improvement."""
    import copy
    from ztare.worldmodel.gates import env_frame_indices
    env = env_frame_indices(log)
    best_step, _e = lower_spec(spec)
    if best_step is None:
        return spec, best_step
    best_spec = spec
    best_wrong = _wrong_cell_count(best_step, log, env)
    improved = True
    while improved:
        improved = False
        rules = list(best_spec.get("always", []))
        seen = set()
        for idx, rule in enumerate(rules):
            if not _is_unguarded_consume(rule):
                continue
            sig = _consume_schedule_key(rule)
            if sig in seen:
                continue
            seen.add(sig)
            mined = _fit_periodic_consume_rules(rule, log, env)
            if not mined:
                continue
            replace = {j for j, r in enumerate(rules)
                       if _is_unguarded_consume(r) and _consume_schedule_key(r) == sig}
            cand_always, inserted = [], False
            for j, r in enumerate(rules):
                if j in replace:
                    if not inserted:
                        cand_always.extend(copy.deepcopy(mined))
                        inserted = True
                    continue
                cand_always.append(copy.deepcopy(r))
            cand = {"actions": copy.deepcopy(best_spec.get("actions", {})),
                    "always": cand_always}
            st, _e = lower_spec(cand)
            if st is None:
                continue
            w = _wrong_cell_count(st, log, env, incumbent=best_wrong)
            if w < best_wrong:
                best_spec, best_step, best_wrong = cand, st, w
                improved = True
                break
    return best_spec, best_step


def _separating_region(fired, paused, indicators) -> "list | None":
    """A when_region guard: an indicator region whose step-start contents are a
    CONSTANT pattern across every fired frame and DIFFERENT on every paused frame
    -> [y0, x0, y1, x1, pattern]. The 'legal only while the indicator holds X'
    gate, provable when count/overlap/action/phase all fail to separate."""
    for cells in indicators:
        ys = [c[0] for c in cells]
        xs = [c[1] for c in cells]
        y0, x0, y1, x1 = min(ys), min(xs), max(ys), max(xs)

        def pat(tr):
            g = tr.s
            h, w = len(g), len(g[0])
            return tuple(g[y][x] for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)
                         if 0 <= y < h and 0 <= x < w)
        fpats = {pat(tr) for tr in fired}
        if len(fpats) != 1:
            continue
        p = next(iter(fpats))
        if all(pat(tr) != p for tr in paused):
            return [y0, x0, y1, x1, list(p)]
    return None


def _spec_indicator_regions(spec) -> "list[list]":
    """Region-event write-target cell-sets (deduped) — the indicators a
    when_region guard may test. Same notion as goal_abduction._indicator_regions,
    inlined to keep the module dependency-light."""
    seen, out = set(), []
    for rules in spec.get("actions", {}).values():
        for rule in rules:
            if rule.get("op") == "region_event":
                cells = tuple(sorted((int(y), int(x))
                                     for _c, cs in rule.get("writes", []) for (y, x) in cs))
                if cells and cells not in seen:
                    seen.add(cells)
                    out.append([list(c) for c in cells])
    for rule in spec.get("always", []):
        if rule.get("op") == "region_event":
            cells = tuple(sorted((int(y), int(x))
                                 for _c, cs in rule.get("writes", []) for (y, x) in cs))
            if cells and cells not in seen:
                seen.add(cells)
                out.append([list(c) for c in cells])
    return out


def _mover_moved(rule, tr) -> bool:
    """Did the mover block actually relocate in reality (its cell-set changed)?"""
    mc = {int(c) for c in rule.get("match_colors", [])}
    if not mc:
        return False
    for row_s, row_n in zip(tr.s, tr.s_next):
        for c_s, c_n in zip(row_s, row_n):
            if (c_s in mc) != (c_n in mc):
                return True
    return False


def _region_guard_refine(spec, log):
    """Post-closure (needs the indicator regions region_events supply): an
    ACTION move that is geometrically legal on a frame yet reality REFUSED — not
    a wall (the destination is clear) but a STATE gate — is 'legal only while an
    indicator region holds a pattern'. When an indicator region's step-start
    pattern separates the moved frames from the refused ones, add when_region.
    Strict wrong-cell improvement, same discipline as _action_scope_refine."""
    from ztare.worldmodel.gates import env_frame_indices
    indicators = _spec_indicator_regions(spec)
    best_step, _e = lower_spec(spec)
    if best_step is None or not indicators:
        return spec, best_step
    env = env_frame_indices(log)
    rows = list(log)
    best_spec, best_wrong = spec, _wrong_cell_count(best_step, log, env)
    for a_str, rules in spec.get("actions", {}).items():
        a = int(a_str)
        a_frames = [tr for tr in rows if tr.a == a]
        for idx, rule in enumerate(rules):
            if rule.get("op") != "translate_block" or "when_region" in rule:
                continue
            bare = {k: v for k, v in rule.items() if not k.startswith("when_")}
            frag, _e = lower_spec({"actions": {"0": [bare]}, "always": []})
            if frag is None:
                continue
            legal = [tr for tr in a_frames if frag(tr.s, 0, tr.t) != tr.s]
            fired, paused = [], []
            for tr in legal:
                (fired if _mover_moved(rule, tr) else paused).append(tr)
            if not (fired and paused):
                continue
            wr = _separating_region(fired, paused, indicators)
            if wr is None:
                continue
            new_rule = dict(rule)
            new_rule["when_region"] = wr
            cand = {"actions": {**spec["actions"],
                                a_str: [new_rule if i == idx else r
                                        for i, r in enumerate(rules)]},
                    "always": spec.get("always", [])}
            st, _e = lower_spec(cand)
            if st is None:
                continue
            w = _wrong_cell_count(st, log, env, incumbent=best_wrong)
            if w < best_wrong:
                best_spec, best_step, best_wrong = cand, st, w
    return best_spec, best_step


def _colors_key(rule) -> tuple:
    return tuple(sorted(int(c) for c in rule.get("match_colors", [])))


def _freeze_deep(v):
    if isinstance(v, dict):
        return tuple(sorted((k, _freeze_deep(x)) for k, x in v.items()))
    if isinstance(v, (list, tuple)):
        return tuple(_freeze_deep(x) for x in v)
    return v


def _rule_signature(rule) -> tuple:
    """Structural identity of a rule ignoring id/guards/stop — twins across
    actions (a mover facing several directions is NOT a twin; same op+params is)
    share it, so a reference rule gets ONE shared coupling id."""
    return _freeze_deep({k: v for k, v in rule.items()
                         if not k.startswith("when_") and k not in ("id", "stop_if_applied")})


def _rule_bare_frag(rule):
    """Lower a single rule with guards/id/stop stripped -> step(g, 0, t) or None."""
    bare = {k: v for k, v in rule.items()
            if not k.startswith("when_") and k not in ("id", "stop_if_applied")}
    frag, _e = lower_spec({"actions": {"0": [bare]}, "always": []})
    return frag


def _rule_fired_in_reality(frag, tr) -> bool:
    """Op-AGNOSTIC 'this rule fired this step': the bare rule applied to the
    step-start grid changes some cells AND reality's successor matches the rule's
    write on every changed cell (the write actually landed). Works for any op —
    consume, recolor, translate — with no per-op effect code."""
    if frag is None:
        return False
    g = frag(tr.s, 0, tr.t)
    changed = False
    for y in range(len(tr.s)):
        rs, rg, rn = tr.s[y], g[y], tr.s_next[y]
        for x in range(len(rs)):
            if rg[x] != rs[x]:
                changed = True
                if rn[x] != rg[x]:
                    return False
    return changed


def _effect_guard_refine(spec, log):
    """General RULE-COUPLING refine (op-agnostic; mirrors _region_guard_refine):
    when one rule's fire/pause split coincides EXACTLY with whether ANOTHER
    reference fired this step, gate the first with when_effect [ref_id, pol]. NO
    op, colour, geometry, or action is hardcoded — every rule is a candidate on
    the gated side, and the reference side spans (a) each MOVER OBJECT relocating
    (translate palettes grouped by colour-set, so 'the object moved under whatever
    action/direction' — the multi-rule union a single directional rule cannot
    express) and (b) each individual rule firing. Cheap perfect-biconditional
    pre-filter before any full-log replay; strict wrong-cell improvement is the
    final arbiter, exactly the sibling's self-gating discipline."""
    import copy
    from ztare.worldmodel.gates import env_frame_indices
    best_step, _e = lower_spec(spec)
    if best_step is None:
        return spec, best_step
    env = env_frame_indices(log)
    rows = [tr for i, tr in enumerate(log) if i not in env]
    if not rows:
        return spec, best_step

    all_rules = [("actions", a, i, r) for a, rs in spec.get("actions", {}).items()
                 for i, r in enumerate(rs)]
    all_rules += [("always", None, i, r) for i, r in enumerate(spec.get("always", []))]
    if len(all_rules) * len(rows) > _refine_signal_eval_budget():
        return spec, best_step

    # ---- reference signals (what could gate another rule), all general ----
    refs = []   # (id, signal-over-rows, tagger(cand, gid))
    # (a) mover OBJECTS: one per translate colour-set; reality = the object relocated
    palettes = {}
    for _l, _a, _i, r in all_rules:
        if r.get("op") == "translate_block":
            palettes.setdefault(tuple(sorted(int(c) for c in r.get("match_colors", []))), True)
    for pal in palettes:
        sig = [_mover_moved({"match_colors": list(pal)}, tr) for tr in rows]
        def _tag_pal(cand, gid, pal=pal):
            for rs in list(cand.get("actions", {}).values()) + [cand.get("always", [])]:
                for r in rs:
                    if r.get("op") == "translate_block" and \
                            tuple(sorted(int(c) for c in r.get("match_colors", []))) == pal:
                        r["id"] = gid
        refs.append((("mover", pal), sig, _tag_pal))
    # per-signature firing signal, computed ONCE and reused on both the gated and
    # reference sides (a rule's own firing IS its reference signal) — the scans
    # over the grid are the cost, so cache them by structural signature
    fired_by_sig: dict = {}
    for _l, _a, _i, r in all_rules:
        rsig = _rule_signature(r)
        if rsig not in fired_by_sig:
            fired_by_sig[rsig] = [_rule_fired_in_reality(_rule_bare_frag(r), tr) for tr in rows]
    # (b) each individual rule firing (op-agnostic), shared id per structural twin
    for rsig in fired_by_sig:
        def _tag_sig(cand, gid, rsig=rsig):
            for rs in list(cand.get("actions", {}).values()) + [cand.get("always", [])]:
                for rr in rs:
                    if _rule_signature(rr) == rsig:
                        rr["id"] = gid
        refs.append((("rule", rsig), fired_by_sig[rsig], _tag_sig))

    id_of = {}
    lowerings = 0        # cap full-log replays: a coincidence storm can't stall us
    best_spec, best_wrong = spec, _wrong_cell_count(best_step, log, env)
    for (loc, a_str, idx, rule) in all_rules:
        if "when_effect" in rule or lowerings >= 24:
            continue
        rsig_R = _rule_signature(rule)
        effect = fired_by_sig[rsig_R]
        if all(effect) or not any(effect):
            continue        # R always/never fires in reality -> no split to explain
        for (rkey, rsig, tagger) in refs:
            # never couple a rule to its own firing (or its own object's motion)
            if rkey == ("rule", rsig_R):
                continue
            if rkey[0] == "mover" and rule.get("op") == "translate_block" and \
                    tuple(sorted(int(c) for c in rule.get("match_colors", []))) == rkey[1]:
                continue
            if all(rsig) or not any(rsig):
                continue
            if all(e == m for e, m in zip(effect, rsig)):
                pol = True
            elif all(e == (not m) for e, m in zip(effect, rsig)):
                pol = False
            # IMPLICATION polarity (compose case): the rule NEVER fires when the
            # reference didn't (e -> m). A conjunction of guards (e.g. timer =
            # mover-fired AND dest-ok) has no perfect single-reference
            # biconditional; the implication leg is still sound to attach — the
            # OTHER guards explain the rest, and the wrong-cell arbiter decides.
            elif all((not e) or m for e, m in zip(effect, rsig)):
                pol = True
            elif all((not e) or (not m) for e, m in zip(effect, rsig)):
                pol = False
            else:
                continue
            gid = id_of.setdefault(rkey, f"rc{len(id_of)}")
            for keep_guards in (True, False):
                cand = copy.deepcopy(best_spec)
                tagger(cand, gid)
                tgt_list = cand["actions"][a_str] if loc == "actions" else cand["always"]
                if keep_guards:
                    new_rule = dict(tgt_list[idx])       # COMPOSE with existing guards
                else:
                    new_rule = {k: v for k, v in tgt_list[idx].items()
                                if not k.startswith("when_")}   # replace mis-learned
                new_rule["when_effect"] = [gid, pol]
                tgt_list[idx] = new_rule
                st, _e = lower_spec(cand)
                if st is None:
                    continue
                lowerings += 1
                w = _wrong_cell_count(st, log, env, incumbent=best_wrong)
                if w < best_wrong:
                    best_spec, best_step, best_wrong = cand, st, w
            if lowerings >= 24:
                break
    return best_spec, best_step


def _dest_guard_refine(spec, log):
    """RELATIONAL destination-content refine (when_dest; same discipline as
    _effect_guard_refine): when a rule's real fire/pause split coincides EXACTLY
    with 'the acting translate's destination window holds color c', gate it with
    when_dest [mover_id, [c], pol]. Everything is evidence-learned and
    object-anchored: the displacement is each ACTION's own abduced translate
    (never a constant), the window is the mover's current qualifying components
    displaced by it (never an absolute rect or frame index), and the colors come
    from SET SEPARATION — intersection over paused frames minus union over fired
    frames (and the reverse for the opposite polarity). Strict wrong-cell
    improvement is the final arbiter; the coupling REPLACES any mis-learned
    positional/periodic guard on the gated rule (bare-first, like the siblings)."""
    import copy
    from ztare.worldmodel.spec_catalog import _dest_holds
    from ztare.worldmodel.gates import env_frame_indices
    best_step, _e = lower_spec(spec)
    if best_step is None:
        return spec, best_step
    env = env_frame_indices(log)
    rows = [tr for i, tr in enumerate(log) if i not in env]
    if not rows:
        return spec, best_step

    # mover palettes -> per-frame destination COLOR-SET under the acting
    # translate (the action the frame actually took); no rule for that action
    # -> empty set (predicate False for every color)
    palettes = {}
    for a_str, rs in spec.get("actions", {}).items():
        for r in rs:
            if r.get("op") == "translate_block":
                palettes.setdefault(_colors_key(r), {})[int(a_str)] = r
    if not palettes:
        return spec, best_step

    def _dest_set(ref, tr):
        h, w = len(tr.s), len(tr.s[0])
        out = set()
        dy, dx = int(ref["dy"]), int(ref["dx"])
        from ztare.worldmodel.spec_catalog import _qualifying_components
        for comp in _qualifying_components([list(r) for r in tr.s], ref):
            src = set(comp)
            for (y, x) in comp:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and (ny, nx) not in src:
                    out.add(tr.s[ny][nx])
        return out

    dest_sets = {pal: [_dest_set(by_a[tr.a], tr) if tr.a in by_a else set()
                       for tr in rows]
                 for pal, by_a in palettes.items()}

    all_rules = [("actions", a, i, r) for a, rs in spec.get("actions", {}).items()
                 for i, r in enumerate(rs)]
    all_rules += [("always", None, i, r) for i, r in enumerate(spec.get("always", []))]

    fired_by_sig: dict = {}

    def _effect_for(rule):
        rsig = _rule_signature(rule)
        if rsig not in fired_by_sig:
            fired_by_sig[rsig] = [_rule_fired_in_reality(_rule_bare_frag(rule), tr) for tr in rows]
        return fired_by_sig[rsig]

    best_spec, best_wrong = spec, _wrong_cell_count(best_step, log, env)
    gid_of = {}
    lowerings = 0
    cap = _refine_full_replay_cap()
    for (loc, a_str, idx, rule) in all_rules:
        if lowerings >= cap:
            break
        if "when_dest" in rule or rule.get("op") == "translate_block":
            continue
        effect = _effect_for(rule)
        if all(effect) or not any(effect):
            continue
        for pal, by_a in palettes.items():
            ds = dest_sets[pal]
            fired = [d for e, d in zip(effect, ds) if e]
            paused = [d for e, d in zip(effect, ds) if not e]
            # SEPARATING COLOR SET, both polarities (pure set algebra, no replay).
            # A rule may pause for SEVERAL destination contents at once — e.g. a
            # timer that freezes both on a void dock-transit AND when a sprite
            # blocks the mover's path. No single colour is then shared across every
            # paused frame (their intersection is empty), so the old "in EVERY
            # paused" test found nothing and the guard never landed. The SOUND set
            # is instead colour-by-colour: for pol=False ("fire iff dest holds none
            # of L") a colour is safe to include iff it appears in NO fired dest
            # (else it would wrongly pause a tick), so L = paused-union minus
            # fired-union captures the whole pause vocabulary; symmetric for
            # pol=True. Gating on the full set (not one colour) is what closes the
            # multi-mechanic pause; strict wrong-cell improvement stays the arbiter.
            pu = set().union(*paused) if paused else set()
            fu = set().union(*fired) if fired else set()
            cands = [(sorted(pu - fu), False), (sorted(fu - pu), True)]
            def _apply_dest(colors, pol, keep_guards):
                """Build best_spec + when_dest[colors,pol] on rule idx and score it;
                return (cand, st, w) if it STRICTLY cuts wrong cells, else None.
                keep_guards=False (bare) replaces any mis-learned guard; True KEEPS
                the existing guard and AND's when_dest (a conjunction)."""
                src = (best_spec["actions"][a_str] if loc == "actions"
                       else best_spec["always"])[idx]
                if keep_guards and "when_dest" in src:
                    return None
                # bare mints the canonical mover id; COMPOSE reuses the mover's
                # EXISTING id (a prior refine's when_effect references it — re-minting
                # would orphan that reference and silently disable the kept guard)
                if keep_guards:
                    gid = next((r.get("id") for rs in
                                list(best_spec.get("actions", {}).values())
                                + [best_spec.get("always", [])] for r in rs
                                if r.get("op") == "translate_block"
                                and _colors_key(r) == pal and r.get("id")), None) \
                        or gid_of.setdefault(pal, f"dm{len(gid_of)}")
                else:
                    gid = gid_of.setdefault(pal, f"dm{len(gid_of)}")
                cand = copy.deepcopy(best_spec)
                for rs in list(cand.get("actions", {}).values()) + [cand.get("always", [])]:
                    for r in rs:
                        if r.get("op") == "translate_block" and _colors_key(r) == pal:
                            r["id"] = gid
                tgt_list = cand["actions"][a_str] if loc == "actions" else cand["always"]
                new_rule = (dict(tgt_list[idx]) if keep_guards
                            else {k: v for k, v in tgt_list[idx].items()
                                  if not k.startswith("when_")})
                new_rule["when_dest"] = [gid, colors, pol]
                tgt_list[idx] = new_rule
                st, _e = lower_spec(cand)
                if st is None:
                    return None
                nonlocal lowerings
                lowerings += 1
                w = _wrong_cell_count(st, log, env, incumbent=best_wrong)
                return (cand, st, w) if w < best_wrong else None

            landed = False
            for colors, pol in cands:            # BARE pass — unchanged from baseline
                if lowerings >= cap:
                    break
                if not colors:
                    continue
                res = _apply_dest(colors, pol, False)
                if res is not None:
                    best_spec, best_step, best_wrong = res
                    landed = True
                    break
            if not landed:
                # COMPOSE fallback (guard CONJUNCTION, Espresso product term): run ONLY
                # where the bare pass found nothing, so it is strictly additive — the
                # real-log champion path (bare lands) is byte-for-byte untouched, while
                # a mechanic needing when_effect AND when_dest is now recoverable.
                for colors, pol in cands:
                    if lowerings >= cap:
                        break
                    if not colors:
                        continue
                    res = _apply_dest(colors, pol, True)
                    if res is not None:
                        best_spec, best_step, best_wrong = res
                        landed = True
                        break
            if not landed:
                continue
            break       # this rule is gated; move on
    return best_spec, best_step


def _prune_region_writes(spec, log):
    """Post-closure cleanup (never perturbs the greedy assembly): a resource cell
    that briefly went residual during mining (11->3 depletion, s_next=3 is floor)
    can leak into a region-event write and then DOUBLE-CONSUME the bar on later
    crossings. Drop region-write cells at RESOURCE positions when removal strictly
    cuts wrong cells — the consume rule already owns those cells. Only resource-
    position cells are tested, so this stays cheap; strict improvement keeps it
    safe (a genuinely needed write never loses cells)."""
    from ztare.worldmodel.gates import env_frame_indices
    res_cols = {int(r["color"]) for r in spec.get("always", [])
                if r.get("op") == "consume_extremal"}
    res_cols |= {int(r["color"]) for rules in spec.get("actions", {}).values()
                 for r in rules if r.get("op") == "consume_extremal"}
    step, _e = lower_spec(spec)
    if step is None or not res_cols:
        return spec, step
    region_write_cells = sum(
        len(cells)
        for rules in [spec.get("always", [])] + list(spec.get("actions", {}).values())
        for r in rules if r.get("op") == "region_event"
        for _c, cells in r.get("writes", [])
    )
    if (region_write_cells > _hot_region_write_budget()
            and os.environ.get("ZTARE_PRUNE_REGION_FULL_FALLBACK", "0") != "1"):
        return spec, step
    rows = list(log)
    res_pos = {(y, x) for tr in rows for y in range(len(tr.s))
               for x in range(len(tr.s[0])) if tr.s[y][x] in res_cols}
    if not res_pos:
        return spec, step
    import copy
    cur = copy.deepcopy(spec)
    env = env_frame_indices(log)
    best_wrong = _wrong_cell_count(step, log, env)

    def _region_rules(s):
        for idx, r in enumerate(s.get("always", [])):
            if r.get("op") == "region_event":
                yield ("always", None, idx, r)
        for a, rules in s.get("actions", {}).items():
            for idx, r in enumerate(rules):
                if r.get("op") == "region_event":
                    yield ("action", a, idx, r)

    def _fixed_write_event(rule):
        return (
            rule.get("op") == "region_event"
            and rule.get("content_states") is None
            and rule.get("toggle") is None
            and rule.get("cycle") is None
            and isinstance(rule.get("writes"), list)
        )

    def _without_one_write(rule, c0, cell0):
        new_writes = []
        removed = False
        for c, cells in rule.get("writes", []):
            kept = []
            for cl in cells:
                if not removed and c == c0 and cl == cell0:
                    removed = True
                    continue
                kept.append(cl)
            if kept:
                new_writes.append([c, kept])
        out = copy.deepcopy(rule)
        out["writes"] = new_writes
        return out

    def _write_cells(rule):
        return {(int(y), int(x)) for _c, cells in rule.get("writes", [])
                for y, x in cells}

    prefix_cache = {}

    def _score_last_always_fixed_delete(idx, rule, c0, cell0, preds):
        """Exact fast score for deleting one write from the final always event.

        If the target event is the last rule in the chain, the full replay
        factors into prefix(state) followed by this event. Deleting one fixed
        write changes only the event image, so the sufficient statistic is the
        prefix grid plus the event's written cell set. Any suffix or stateful
        event is not certified for this hot-path scorer.
        """
        always = cur.get("always", [])
        if idx != len(always) - 1 or not _fixed_write_event(rule):
            return None
        key = ("always_prefix", idx)
        if key not in prefix_cache:
            prefix_spec = {"actions": cur.get("actions", {}), "always": always[:idx]}
            prefix_step, _err = lower_spec(prefix_spec)
            if prefix_step is None:
                prefix_cache[key] = None
            else:
                prefix_cache[key] = _predict_all(prefix_step, log)
        prefix_preds = prefix_cache.get(key)
        if prefix_preds is None:
            return None
        from ztare.worldmodel.spec_catalog import _apply_region_event
        modified = _without_one_write(rule, c0, cell0)
        affected = _write_cells(rule) | _write_cells(modified)
        if not affected:
            return best_wrong
        total = best_wrong
        for i, tr in enumerate(rows):
            if i in env:
                continue
            old = preds[i]
            new = _apply_region_event(prefix_preds[i], modified, tr.s)
            h, w = len(tr.s_next), len(tr.s_next[0])
            for y, x in affected:
                if 0 <= y < h and 0 <= x < w:
                    total += ((new[y][x] != tr.s_next[y][x])
                              - (old[y][x] != tr.s_next[y][x]))
        return total

    improved = True
    while improved:
        improved = False
        preds = _predict_all(step, log)
        for loc, action, idx, rule in _region_rules(cur):
            for c0, cs in list(rule.get("writes", [])):
                for cell0 in list(cs):
                    if (int(cell0[0]), int(cell0[1])) not in res_pos:
                        continue                       # only resource-position writes
                    w = (None if loc != "always" else
                         _score_last_always_fixed_delete(idx, rule, c0, cell0, preds))
                    saved = rule["writes"]
                    if w is None:
                        if os.environ.get("ZTARE_PRUNE_REGION_FULL_FALLBACK", "0") != "1":
                            continue
                        rule["writes"] = _without_one_write(rule, c0, cell0)["writes"]
                        st, _e = lower_spec(cur)
                        w = _wrong_cell_count(st, log, env, incumbent=best_wrong) if st is not None else None
                    else:
                        st = None
                    if w is not None and w < best_wrong:
                        rule["writes"] = _without_one_write(rule, c0, cell0)["writes"]
                        st, _e = lower_spec(cur)
                        if st is None:
                            rule["writes"] = saved
                            continue
                        best_wrong, step, improved = w, st, True
                    else:
                        rule["writes"] = saved
    return cur, step


def _bbox(cells) -> tuple:
    ys = [int(c[0]) for c in cells]
    xs = [int(c[1]) for c in cells]
    return (min(ys), min(xs), max(ys), max(xs))


def _display_event_candidates(rt, mover, indicators, flaglike):
    """Enter-triggered display-write candidates from the current residual. For
    each still-wrong transition, the write is the residual cells set to their
    step-END colours (the display pattern), and the trigger is a CROSSING read on
    the mid-chain grid — the mover (or any colour) ENTERING a rect on the post-
    action grid. An optional when_region on a source cell that did NOT change this
    step (its step-start == step-end value) disambiguates a display that is a
    JOINT function of several flags — a panel = f(flagA, flagB) needs the
    unchanged flag's value as a guard, which no single crossing can carry. None-
    context is offered FIRST (the un-gated latch is MDL-simplest and closes the
    ls20 HUD without ever reaching a guard)."""
    cands, seen = [], set()
    cand_budget = _display_candidate_budget()
    write_budget = _display_write_cell_budget()
    context_budget = _display_context_budget()
    mc = set(mover)
    for (i, tr, p, wrong) in rt:
        if len(cands) >= cand_budget:
            break
        H, W = len(p), len(p[0])
        wrong_set = set(wrong)
        by_color: "dict[int, list]" = defaultdict(list)
        for (y, x) in wrong:
            by_color[tr.s_next[y][x]].append([y, x])
        writes = [[c, sorted(cs)] for c, cs in sorted(by_color.items())]
        if sum(len(cs) for _c, cs in writes) > write_budget:
            continue
        # TRIGGERS: (a) the game mover's step-END footprint (it entered the rect);
        #           (b) any non-display colour that entered a cell this step.
        triggers = []
        dst = [(y, x) for y in range(H) for x in range(W)
               if p[y][x] in mc and tr.s[y][x] not in mc]
        if dst:
            triggers.append((mover, _bbox(dst)))
        entered: "dict[int, list]" = defaultdict(list)
        for y in range(H):
            for x in range(W):
                if (y, x) not in wrong_set and tr.s[y][x] != tr.s_next[y][x]:
                    entered[tr.s_next[y][x]].append((y, x))
        for c, cells in entered.items():
            triggers.append(([c], _bbox(cells)))
        # CONTEXTS (None first): source regions / flag cells unchanged this step.
        contexts = [None]
        srcs = list(indicators) + [[list(c)] for c in flaglike]
        for cells in srcs:
            if len(contexts) >= context_budget:
                break
            cset = {(int(y), int(x)) for (y, x) in cells}
            if cset & wrong_set or not all(tr.s[y][x] == tr.s_next[y][x] for (y, x) in cset):
                continue
            y0, x0, y1, x1 = _bbox([list(c) for c in cset])
            pat = [tr.s[y][x] for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]
            contexts.append([y0, x0, y1, x1, pat])
        for (mcs, rect) in triggers:
            for ctx in contexts:
                if len(cands) >= cand_budget:
                    break
                ev = {"op": "region_event", "mover_colors": sorted(int(c) for c in mcs),
                      "rect": list(rect), "edge": "enter", "writes": writes}
                if ctx is not None:
                    ev["when_region"] = ctx
                key = _freeze_deep(ev)
                if key not in seen:
                    seen.add(key)
                    cands.append(ev)
            if len(cands) >= cand_budget:
                break
    return cands


def _display_event_cells(ev) -> frozenset:
    return frozenset((int(y), int(x)) for _c, cs in ev.get("writes", []) for (y, x) in cs)


def _display_event_source_key(ev) -> tuple:
    return (
        tuple(sorted(int(c) for c in ev.get("mover_colors", []))),
        tuple(int(v) for v in ev.get("rect", [])),
        ev.get("edge", "exit"),
        _freeze_deep(ev.get("when_region")),
        _freeze_deep(ev.get("when_t_mod")),
        _freeze_deep(ev.get("when_phase")),
        _freeze_deep(ev.get("when_action")),
        _freeze_deep(ev.get("when_count")),
    )


def _source_event_from_key(key) -> dict:
    colors, rect, edge, wr, tm, wp, wa, wc = key
    ev = {"op": "region_event", "mover_colors": list(colors), "rect": list(rect), "edge": edge,
          "writes": []}
    if wr is not None:
        ev["when_region"] = _thaw_deep(wr)
    if tm is not None:
        ev["when_t_mod"] = _thaw_deep(tm)
    if wp is not None:
        ev["when_phase"] = _thaw_deep(wp)
    if wa is not None:
        ev["when_action"] = _thaw_deep(wa)
    if wc is not None:
        ev["when_count"] = _thaw_deep(wc)
    return ev


def _thaw_deep(v):
    if isinstance(v, tuple):
        return [_thaw_deep(x) for x in v]
    return v


def _display_row_diffs(rows, env, cache):
    key = ("row_diffs", frozenset(int(i) for i in env))
    if key not in cache:
        cache[key] = {i: _diff_cell_set(tr.s, tr.s_next)
                      for i, tr in enumerate(rows) if i not in env}
    return cache[key]


def _display_source_support(rows, env, source, cache) -> set:
    if source in cache:
        return cache[source]
    colors, rect, edge, wr, tm, wp, wa, wc = source
    cs = {int(c) for c in colors}
    y0, x0, y1, x1 = (int(v) for v in rect)
    guard_ev = None
    if any(v is not None for v in (wr, tm, wp, wa, wc)):
        guard_ev = _source_event_from_key(source)
    changed = set()
    row_diffs = _display_row_diffs(rows, env, cache)
    fired = False
    for i, tr in enumerate(rows):
        if i in env:
            continue
        if guard_ev is not None and not _candidate_event_guard_fires(guard_ev, tr):
            continue
        o0 = _overlap_holds_parts(tr.s, cs, y0, x0, y1, x1)
        o1 = _overlap_holds_parts(tr.s_next, cs, y0, x0, y1, x1)
        crosses = (o0 and not o1) if edge == "exit" else ((not o0) and o1)
        if crosses:
            fired = True
            changed.update(row_diffs.get(i, ()))
    cache[source] = changed if changed else ({None} if fired else set())
    return cache[source]


def _display_support_counts(rows, env, cands, cache=None) -> dict:
    """Observed support for candidate display-cells x source-region pairs.

    A display latch needs at least one logged transition where its trigger source
    fires. When display cells co-change with that source, the support count is
    the changed-cell overlap. A source-fired stable display candidate is also
    kept: after a broader display event lands, those candidates can restore the
    stable target value on source crossings where the panel should remain off.
    """
    env = frozenset(int(i) for i in env)
    cache = {} if cache is None else cache
    pairs = {(_display_event_cells(ev), _display_event_source_key(ev)) for ev in cands}
    out = {}
    for cells, source in pairs:
        source_support = _display_source_support(rows, env, source, cache)
        cochange = len(set(cells) & source_support)
        out[(cells, source)] = cochange if cochange else int(bool(source_support))
    return out


def _filter_display_supported_candidates(cands, rows, env, cache=None):
    if not cands:
        return []
    support = _display_support_counts(rows, env, cands, cache=cache)
    return [ev for ev in cands
            if support.get((_display_event_cells(ev), _display_event_source_key(ev)), 0) > 0]


def _bare_superseded_writes(spec, log, env, display_cells):
    """A display law learned as an ENTER latch supersedes the fragile crossing-
    triggered writes an exit-anchored miner produced for the SAME cells (the ls20
    HUD: the champion wrote it on 'sprite exits the right dock', which fires on the
    horizontal approach only). Drop the display cells from every OTHER region_event
    when removal does not worsen the fit — bares the now-wrong event writes (MDL)."""
    if os.environ.get("ZTARE_BARE_SUPERSEDED_FULL_FALLBACK", "0") != "1":
        step, _e = lower_spec(spec)
        return spec, step
    import copy
    step, _e = lower_spec(spec)
    if step is None:
        return spec, step
    best_wrong = _wrong_cell_count(step, log, env)
    disp = {(int(y), int(x)) for (y, x) in display_cells}
    cur = copy.deepcopy(spec)
    improved = True
    while improved:
        improved = False
        for lst in [cur.get("always", [])] + list(cur.get("actions", {}).values()):
            for idx in range(len(lst)):
                r = lst[idx]
                if r.get("op") != "region_event" or r.get("edge") != "exit" \
                        or "writes" not in r:                # content_states rule: no cells to bare
                    continue
                new_writes = [[c, [cl for cl in cs
                                   if (int(cl[0]), int(cl[1])) not in disp]]
                              for c, cs in r.get("writes", [])]
                new_writes = [[c, cs] for c, cs in new_writes if cs]
                if new_writes == r["writes"]:
                    continue
                saved = list(lst)
                if new_writes:
                    lst[idx] = {**r, "writes": new_writes}
                else:
                    lst.pop(idx)                          # fully superseded -> drop it
                st, _e = lower_spec(cur)
                w = _wrong_cell_count(st, log, env, incumbent=best_wrong) if st is not None else None
                if w is not None and w <= best_wrong:
                    best_wrong, step, improved = w, st, True
                    break                                 # list mutated; restart scan
                lst[:] = saved
            if improved:
                break
    return cur, step


def _cellwise_reproducible(states: list, m: dict) -> bool:
    """Is the whole-region transition m (from_idx -> to_idx) reproducible by a
    SINGLE global colour map applied cell-wise? True iff one substitution sigma
    carries states[f] to states[t] for every edge — exactly the family
    `_fit_write_function` already owns (fixed write, toggle, colour-cycle). When
    it is False the glyph SHIFTS (a colour must map two ways at once), so no
    cell-wise function fits and only a region-state machine can place it. This is
    the substrate-agnostic generality gate — a functional-dependency check, not a
    hardcoded state-count threshold: a stateful 2-state directional latch whose
    lit block moves (not recolours) returns False here and is captured, while an
    ordinary bi-directional toggle returns True and is left to the toggle learner."""
    sigma: "dict[int, int]" = {}
    for f, t in m.items():
        for cf, ct in zip(states[f], states[t]):
            if sigma.get(cf, ct) != ct:
                return False
            sigma[cf] = ct
    return True


def _as_cycle_or_graph(m: dict, states: list):
    """Render a mined transition map (from_idx -> to_idx over 0..k-1) as the
    MDL-simplest catalog form. A single ring covering every state becomes the
    'cycle' shorthand (states reordered along the ring so successor = (i+1)%k);
    anything else — a partial map, a reset, a direction-dependent edge — is kept
    as the explicit [[from, to], ...] graph. Returns (state_transition, states)."""
    k = len(states)
    if set(m) == set(range(k)) and set(m.values()) == set(range(k)):
        order, nxt = [0], m[0]
        while nxt != 0 and len(order) < k:
            order.append(nxt)
            nxt = m[nxt]
        if nxt == 0 and len(order) == k:
            return "cycle", [states[i] for i in order]
    return [[int(f), int(t)] for f, t in sorted(m.items())], states


def _mine_content_state_machine(observations, *, eligible_states=None):
    """Return the MDL-smallest whole-content transition machine in observations.

    ``observations`` contains pairs of equal-sized, hashable presentations.  The
    resulting machine is an identity over whole contents: a conflicting
    successor refutes functionality, while a single cell-wise substitution is
    left to the cheaper write-function family.  ``eligible_states`` lets a
    caller impose its own recurrence/authority filter without duplicating the
    transition-algebra test.
    """
    pairs = [(tuple(before), tuple(after)) for before, after in observations
             if tuple(before) != tuple(after)]
    if not pairs:
        return None
    if eligible_states is None:
        states = []
        for before, after in pairs:
            for state in (before, after):
                if state not in states:
                    states.append(state)
    else:
        states = [tuple(state) for state in eligible_states]
    if len(states) < 2 or len({len(state) for state in states}) != 1:
        return None
    index = {state: position for position, state in enumerate(states)}
    transitions = {}
    for before, after in pairs:
        if before not in index or after not in index:
            continue
        source, target = index[before], index[after]
        if source in transitions and transitions[source] != target:
            return None
        transitions[source] = target
    if not transitions or _cellwise_reproducible(states, transitions):
        return None
    state_transition, ordered = _as_cycle_or_graph(transitions, states)
    return state_transition, ordered


def _gap_tolerant_components(cells, *, gap=3):
    """Connected components under a bounded Chebyshev-neighbour relation."""
    components = []
    for point in sorted({(int(row), int(col)) for row, col in cells}):
        touching = [component for component in components
                    if any(max(abs(point[0] - other[0]),
                               abs(point[1] - other[1])) <= gap
                           for other in component)]
        if not touching:
            components.append({point})
            continue
        merged = {point}
        for component in touching:
            merged.update(component)
            components.remove(component)
        components.append(merged)
    return components


def _residual_regions(rows, env, step, res_cols=frozenset()) -> "list[tuple]":
    """Bounding boxes of the cell-sets the current step still mispredicts. The
    whole-residual bbox is offered first (when the resource/guard refines already
    closed everything but the display, it IS the display glyph exactly); each
    gap-tolerant connected cluster is offered as a fallback so a residual split
    across two panels still yields a tight per-panel region. Resource-coloured
    residual cells are dropped (the consume rule owns a depleting bar, which is
    not a finite-state glyph) so a bar adjacent to the display never fuses into
    the region. A glyph, not a single flag or the whole board: 4 <= area <= 400."""
    resid = set()
    for i, tr in enumerate(rows):
        if i in env:
            continue
        p = step(tr.s, tr.a, tr.t)
        if p is None:
            continue
        for y in range(len(p)):
            for x in range(len(p[0])):
                if p[y][x] != tr.s_next[y][x] and tr.s_next[y][x] not in res_cols:
                    resid.add((y, x))
    if not resid:
        return []
    regions = [_bbox([list(c) for c in resid])]
    # gap-tolerant clustering (Chebyshev <= 3): the display's scattered residual
    # cells fuse into one glyph without bridging to a distant bar.
    clusters = _gap_tolerant_components(resid)
    for c in clusters:
        if len(c) >= 4:
            regions.append(_bbox([list(q) for q in c]))
    out, seen = [], set()
    for (y0, x0, y1, x1) in regions:
        area = (y1 - y0 + 1) * (x1 - x0 + 1)
        if 4 <= area <= 400 and (y0, x0, y1, x1) not in seen:
            seen.add((y0, x0, y1, x1))
            out.append((y0, x0, y1, x1))
    return out


def _region_state_refine(spec, log):
    """REGION-STATE MACHINE mining — the operator a cell-wise write cannot be.

    A DISPLAY region whose whole-region content cycles through k>=3 distinct GLYPH
    PATTERNS on a trigger crossing: the lit block SHIFTS position rather than
    recolours in place, so no per-cell function (constant fixed-write, involution
    toggle, or colour-cycle) fits it — one crossing must write different cells
    depending on the current phase, which a cell-wise map provably cannot do.
    (Negative check: `_derived_display_refine`'s fixed-write latch and
    `_fit_write_function`'s permutation arm both leave >=1 phase residual on such a
    region; only matching the WHOLE-region content to a state and advancing closes
    it.) We mine the region from the residual, find the crossing that advances it,
    and emit a region_event carrying `content_states` + a `state_transition` (a ring
    'cycle' or the explicit [[from,to],...] graph when the evidence is a partial /
    direction-dependent map). Greedy strict-improvement on wrong-cell count; every
    parameter — region, glyph states, trigger rect/edge, transition — is read from
    the log (Core-Knowledge objectness: a switch is an object with hidden internal
    state; its cycle length is unknowable without repeated crossings)."""
    from ztare.worldmodel.gates import env_frame_indices
    step, _e = lower_spec(spec)
    if step is None:
        return spec, step
    env = env_frame_indices(log)
    rows = list(log)
    if not rows:
        return spec, step
    H, W = len(rows[0].s), len(rows[0].s[0])
    mover = sorted({int(c) for rs in spec.get("actions", {}).values() for r in rs
                    if r.get("op") == "translate_block" for c in r.get("match_colors", [])})
    mc = set(mover)
    if not mc:
        return spec, step
    res_cols = frozenset(int(v) for rules in
                         [spec.get("always", [])] + list(spec.get("actions", {}).values())
                         for r in rules if r.get("op") == "consume_extremal"
                         for v in (r.get("color"), r.get("replacement")) if v is not None)

    def _in(rect, site):
        return not (rect[2] < site[0] or site[2] < rect[0]
                    or rect[3] < site[1] or site[3] < rect[1])

    best_spec, best_step = spec, step
    best_wrong = _wrong_cell_count(step, log, env)
    display_cells: "set[tuple]" = set()
    lowerings = 0
    cap = _refine_full_replay_cap()

    from ztare.worldmodel.spec_catalog import _overlap
    # candidate trigger sites: the region_event rects the physics closure already
    # found (known switch geometry — one rect per plate), each tried on BOTH edges,
    # plus footprint-clustered residual sites as a fallback. Reusing the spec rects
    # keeps two adjacent plates (a 5x5 mover straddles both) from fusing into one
    # site the way a raw-footprint cluster does.
    spec_rects = []
    for lst in [best_spec.get("always", [])] + list(best_spec.get("actions", {}).values()):
        for r in lst:
            if r.get("op") == "region_event" and r.get("rect"):
                spec_rects.append(tuple(int(v) for v in r["rect"]))

    for (y0, x0, y1, x1) in _residual_regions(rows, env, best_step, res_cols):
        rcells = [(y, x) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]

        def rcontent(g, cs=rcells):
            return tuple(g[y][x] for (y, x) in cs)

        # states that RECUR (a finite machine, not a depleting bar whose content is
        # a fresh value every frame) — indexed in first-seen order.
        cnt = Counter(rcontent(tr.s) for tr in rows)
        cnt.update(rcontent(tr.s_next) for tr in rows)
        states, sidx = [], {}
        for c in cnt:
            if cnt[c] >= 2:
                sidx[c] = len(states)
                states.append(c)
        if len(states) < 2:                      # nothing transitions
            continue

        # footprint sites from the frames the region advances (fallback triggers)
        cur_step, _e = lower_spec(best_spec)
        fp = []
        for i, tr in enumerate(rows):
            if i in env:
                continue
            c0, c1 = rcontent(tr.s), rcontent(tr.s_next)
            if c0 == c1 or c0 not in sidx or c1 not in sidx:
                continue
            p = cur_step(tr.s, tr.a, tr.t)
            src = [(y, x) for y in range(H) for x in range(W)
                   if tr.s[y][x] in mc and p[y][x] != tr.s[y][x]]
            if src:
                fp.append(_bbox(src))
        site_rects = [(list(r), e) for r in spec_rects for e in ("exit", "enter")]
        site_rects += [(list(r), e) for r in _cluster_rects(fp) for e in ("exit", "enter")]

        cands = []
        seen_site = set()
        for rect, edge in site_rects:
            key = (tuple(rect), edge)
            if key in seen_site:
                continue
            seen_site.add(key)
            # Whole-content observations over frames this crossing fires.  The
            # shared miner owns functionality, cell-wise reducibility, and the
            # cycle/partial-graph representation.
            observations = []
            for i, tr in enumerate(rows):
                if i in env:
                    continue
                c0, c1 = rcontent(tr.s), rcontent(tr.s_next)
                if c0 == c1 or c0 not in sidx or c1 not in sidx:
                    continue
                o0, o1 = _overlap(tr.s, mc, rect), _overlap(tr.s_next, mc, rect)
                fired = (o0 and not o1) if edge == "exit" else ((not o0) and o1)
                if not fired:
                    continue
                observations.append((c0, c1))
            machine = _mine_content_state_machine(
                observations,
                eligible_states=states,
            )
            if machine is None:
                continue
            trans, ordered = machine
            cands.append({"op": "region_event", "mover_colors": sorted(mc),
                          "rect": list(rect), "edge": edge, "region": [y0, x0, y1, x1],
                          "content_states": [list(s) for s in ordered],
                          "state_transition": trans})

        for ev in cands:
            if lowerings >= cap:
                break
            trial = {"actions": best_spec["actions"],
                     "always": list(best_spec.get("always", [])) + [ev]}
            st, _e = lower_spec(trial)
            if st is None:
                continue
            lowerings += 1
            w = _wrong_cell_count(st, log, env, incumbent=best_wrong)
            if w < best_wrong:
                best_spec, best_step, best_wrong = trial, st, w
                display_cells.update(rcells)

    if best_spec is spec:
        return spec, step
    # the state machine owns those cells now — bare any fixed exit-write over them.
    return _bare_superseded_writes(best_spec, log, env, display_cells)


def _derived_display_refine(spec, log):
    """Readout/latch mining over a compact recurring residual support.

    The rule class is substrate-neutral: a residual support whose value is a
    latched function of persistent state and updates on the same transition that
    changes that state. The encoding reads the source at step-end via an
    enter-style region event, so the latch is independent of the approach path.

    Greedy: add latch rules while each strictly cuts wrong cells, then remove
    superseded writes to the same support. Parameters are induced from evidence:
    support cells, source colours, source region, and written pattern."""
    from ztare.worldmodel.gates import env_frame_indices
    step, _e = lower_spec(spec)
    if step is None:
        return spec, step
    env = env_frame_indices(log)
    rows = list(log)
    mover = sorted({int(c) for rs in spec.get("actions", {}).values()
                    for r in rs if r.get("op") == "translate_block"
                    for c in r.get("match_colors", [])})
    # flag-like cells (few distinct values, never a mover colour): the state a
    # JOINT display may be gated on. Cheap single-cell when_region candidates.
    mc = set(mover)
    valset: "dict[tuple, set]" = defaultdict(set)
    for tr in rows:
        for y in range(len(tr.s)):
            for x in range(len(tr.s[0])):
                valset[(y, x)].add(tr.s[y][x])
    flaglike = [c for c, vs in valset.items()
                if 2 <= len(vs) <= 3 and not (vs & mc)]

    def _residual(st):
        out = []
        for i, tr in enumerate(rows):
            if i in env:
                continue
            p = st(tr.s, tr.a, tr.t)
            if p is None:
                return None
            w = [(y, x) for y in range(len(p)) for x in range(len(p[0]))
                 if p[y][x] != tr.s_next[y][x]]
            if w:
                out.append((i, tr, p, w))
        return out

    best_spec, best_step = spec, step
    best_wrong = _wrong_cell_count(step, log, env)
    display_cells: "set[tuple]" = set()
    fast = _display_refine_fast_enabled()
    support_cache = {} if fast else None
    for _round in range(8):            # a display law is a handful of rules
        rt = _residual(best_step)
        if not rt:
            break
        indicators = _spec_indicator_regions(best_spec)     # refresh: newly-latched flags gate later ones
        preds = _predict_all(best_step, log) if fast else None
        landed = None
        cands = _display_event_candidates(rt, mover, indicators, flaglike)
        if fast:
            cands = _filter_display_supported_candidates(cands, rows, env, cache=support_cache)
        for ev in cands:
            cand = {"actions": best_spec["actions"],
                    "always": list(best_spec["always"]) + [ev]}
            if fast:
                w = _append_event_wrong_cell_count(preds, ev, log, env, incumbent=best_wrong)
                st = None
            else:
                st, _e = lower_spec(cand)
                if st is None:
                    continue
                w = _wrong_cell_count(st, log, env, incumbent=best_wrong)
            if w < best_wrong:
                if st is None:
                    st, _e = lower_spec(cand)
                    if st is None:
                        continue
                landed = (cand, st, w, ev)
                break
        if landed is None:
            break
        best_spec, best_step, best_wrong, ev = landed
        for _c, cs in ev["writes"]:
            display_cells.update((int(y), int(x)) for (y, x) in cs)

    if best_spec is spec:
        return spec, step
    return _bare_superseded_writes(best_spec, log, env, display_cells)


def _separating_count(set_a, set_b) -> "list | None":
    """Decision stump: a color whose count ranges on set_a's states and
    set_b's states are disjoint -> [color, lo, hi] covering set_a only."""
    colors = set()
    for tr in list(set_a)[:4] + list(set_b)[:4]:
        for row in tr.s:
            colors.update(row)
    for color in sorted(colors):
        def counts(trs):
            return [sum(1 for row in tr.s for c in row if c == color) for tr in trs]
        ca, cb = counts(set_a), counts(set_b)
        if not ca or not cb:
            continue
        if max(ca) < min(cb):
            return [color, None, max(ca)]
        if min(ca) > max(cb):
            return [color, min(ca), None]
    return None


def _freeze(rule: dict):
    return tuple(sorted((k, tuple(v) if isinstance(v, list) else
                         (tuple(sorted(v.items())) if isinstance(v, dict) else v))
                        for k, v in rule.items()))


def _thaw(frozen) -> dict:
    if frozen == ("identity",):
        return {"op": "identity"}
    out = {}
    for k, v in frozen:
        if isinstance(v, tuple) and v and isinstance(v[0], tuple):
            out[k] = {kk: vv for kk, vv in v}
        elif isinstance(v, tuple):
            out[k] = list(v)
        else:
            out[k] = v
    return out
