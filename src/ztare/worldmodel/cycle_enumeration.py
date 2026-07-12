"""State-cycle enumeration: an exploration policy for under-sampled switches.

PROVENANCE (read before editing): these primitives are justified by (a) ARC Core
Knowledge priors — objectness (a switch is an object carrying internal state) and
goal-directedness — and (b) screen-visible observations available to any human
player: the game renders display cells whose value changes on interaction, and no
player (or model) can know a multi-state switch's CYCLE LENGTH without crossing it
repeatedly. They encode NOTHING specific to any environment's source: every rect,
trigger action, write cell, palette, and cycle length is learned from the champion
spec and the evidence log — never from constants.

The failure mode this addresses is general: a multi-state switch crossed only once
or twice masquerades as a binary flag. The fixed-write abduction captures a single
phase and the true cycle stays hidden. This module (1) finds EVENT SOURCES whose
write cells have shown >=2 distinct DISPLAY values across evidence, and (2) emits an
ENUMERATION PLAN that re-triggers each source (re-crossing its rect, planning the
exit+re-enter between crossings on the champion) until the written value cycle
REPEATS (closed) or a visit budget is hit. The observed cycle is filled by live
execution; `cycles_from_evidence` is a pure report that feeds the strategy battery.
"""
from __future__ import annotations

from collections import deque

from ztare.worldmodel.goal_abduction import _all_rules, _norm_spec
from ztare.worldmodel.spec_catalog import _overlap

DEFAULT_BUDGET = 12


# ── event sources & mover geometry (spec/evidence-derived, no constants) ──────

def _all_mover_colors(spec) -> set:
    """Colours that MOVE under actions — the union of every region_event's
    mover_colors and every translate_block's match_colors. Used only to mask
    transient sprite transit over a display cell, never as a level constant."""
    out: set = set()
    for rule in _all_rules(spec):
        for k in ("mover_colors", "match_colors"):
            out.update(int(c) for c in (rule.get(k) or []))
    return out


def event_sources(spec) -> list:
    """One record per region_event rule: its trigger rect, edge, mover colours,
    and the cell-set it writes. Display-law writers (region_event) ARE the event
    sources; a source with a state cycle hides behind its fixed-write phase."""
    spec = _norm_spec(spec)
    out = []
    for rule in _all_rules(spec):
        if rule.get("op") != "region_event":
            continue
        cells = tuple(sorted((int(y), int(x))
                             for _c, cs in (rule.get("writes") or []) for (y, x) in cs))
        if not cells:
            continue
        rect = [int(v) for v in rule["rect"]]
        wa = rule.get("when_action")
        out.append({
            "source_id": f"region_event@{rect}",
            "rect": rect,
            "edge": rule.get("edge", "exit"),
            "mover_colors": sorted(int(c) for c in (rule.get("mover_colors") or [])),
            "write_cells": [list(c) for c in cells],
            # the interaction that fires the source: its learned trigger action(s),
            # if the rule gates on one (an exit "moving left" is a directed use, not
            # mere departure). None => any crossing fires it.
            "trigger_actions": sorted(int(a) for a in wa) if wa else None,
        })
    return out


def _sprite_cells(g, mover) -> set:
    """Cells of the SPRITE in grid `g`: a connected mover-coloured component that
    carries >=2 distinct mover colours (the object's full palette). A mono-colour
    blob that merely shares one mover colour — e.g. a HUD fill whose colour equals
    a sprite colour — is NOT the sprite, so it is never masked. When the mover
    palette is a single colour there is no such collision to resolve; return {}."""
    from ztare.worldmodel.object_roles import _components
    mc = set(mover)
    if len(mc) < 2:
        return set()
    out: set = set()
    for comp in _components(g, mc):
        if len({g[y][x] for (y, x) in comp}) >= 2:
            out.update(comp)
    return out


def _mover_footprint(rows, mover) -> set:
    """Every cell the sprite ever occupied across the evidence — the positions
    whose mover-coloured frames are transient transit, not display state.
    Positional, so it survives the palette collision colour-subtraction cannot
    (a display cell sharing a sprite colour but never under the sprite is kept)."""
    fp: set = set()
    for tr in rows:
        fp |= _sprite_cells(tr.s, mover)
        fp |= _sprite_cells(tr.s_next, mover)
    return fp


# ── pure report: per-source observed distinct values so far ───────────────────

def cycles_from_evidence(log, spec) -> dict:
    """Per event source, the distinct DISPLAY values its write cells have shown
    across the evidence (masking transient sprite transit). `multi_state` marks a
    source whose cells vary (some cell shows >=2 display values) — an under-
    sampled switch whose fixed-write abduction may hide a longer cycle. Pure; the
    strategy battery reports it, and enumeration_plans acts on the flagged sources.
    """
    rows = list(log)
    spec = _norm_spec(spec)
    if not rows:
        return {}
    mover = _all_mover_colors(spec)
    fp = _mover_footprint(rows, mover)
    report: dict = {}
    for src in event_sources(spec):
        cells = [tuple(c) for c in src["write_cells"]]
        per_cell = {c: set() for c in cells}
        for tr in rows:
            for c in cells:
                for g in (tr.s, tr.s_next):
                    if not (0 <= c[0] < len(g) and 0 <= c[1] < len(g[0])):
                        continue
                    v = g[c[0]][c[1]]
                    if c in fp and v in mover:        # transient sprite transit
                        continue
                    per_cell[c].add(int(v))
        max_cell = max((len(v) for v in per_cell.values()), default=0)
        distinct = sorted(set().union(*per_cell.values())) if per_cell else []
        report[src["source_id"]] = {
            "rect": src["rect"],
            "edge": src["edge"],
            "write_cells": src["write_cells"],
            "distinct_values": distinct,
            "max_distinct_at_a_cell": max_cell,
            "multi_state": max_cell >= 2,
        }
    return report


# ── cycle closure (pure) ──────────────────────────────────────────────────────

def close_cycle(seq: list):
    """Given the ordered observed write-states (each a hashable value-tuple),
    return the repeating cycle unit once any state reappears, else None (still
    open / under-sampled). A 2-cycle [A,B,A,...] -> [A,B]; a 3-cycle -> [A,B,C]."""
    for j in range(1, len(seq)):
        if seq[j] in seq[:j]:
            i = seq.index(seq[j])
            return seq[i:j]
    return None


def state_at(grid, write_cells) -> tuple:
    """The current value-tuple of a source's write cells — the hashable 'state'
    of the switch used to detect cycle closure."""
    return tuple(int(grid[y][x]) for (y, x) in write_cells
                 if 0 <= y < len(grid) and 0 <= x < len(grid[0]))


# ── crossing planner (reachability on the champion; reused live) ──────────────

def _mover_key(g, mc) -> frozenset:
    return frozenset((y, x) for y in range(len(g)) for x in range(len(g[0]))
                     if g[y][x] in mc)


def plan_next_crossing(step, grid, rect, mover, edge, action_arity, *,
                       trigger_actions=None, resource=None, max_depth=64, max_nodes=40000):
    """BFS on the champion for the shortest action sequence from `grid` whose
    final step CROSSES `rect` in the source's `edge` direction (mover overlaps the
    rect on the step-start grid XOR on the post-step grid) via one of the source's
    `trigger_actions` (any action if None). Handles exit+re-enter implicitly: from
    a post-exit grid the mover is outside, so the next call finds an enter-then-exit
    path. Resource-guarded (never plans through a state whose horizon resource is
    exhausted). Returns (path, grid_after) or (None, None)."""
    mc = {int(c) for c in mover}
    rc = set(resource or [])
    trig = set(trigger_actions) if trigger_actions else None

    def occ(g):
        return _overlap(g, mc, rect)

    def alive(g):
        return (not rc) or any(c in rc for row in g for c in row)

    seen = {_mover_key(grid, mc)}
    q = deque([(grid, [])])
    nodes = 0
    while q and nodes < max_nodes:
        g, path = q.popleft()
        if len(path) >= max_depth:
            continue
        o0 = occ(g)
        for a in range(action_arity):
            nx = step(g, a, 0)
            crossed = (o0 and not occ(nx)) if edge == "exit" else ((not o0) and occ(nx))
            if crossed and (trig is None or a in trig):
                return path + [a], nx
            k = _mover_key(nx, mc)
            if k in seen or not alive(nx):
                continue
            seen.add(k)
            nodes += 1
            q.append((nx, path + [a]))
    return None, None


def enumeration_plans(log, spec, start_grid, step_fn, action_arity, *,
                      budget=DEFAULT_BUDGET, resource=None) -> list:
    """One ENUMERATION PLAN per multi-state source: a `visit_plan` of action
    sub-sequences that re-cross the source's rect up to `budget` times (chained on
    the champion as a dry-run artifact; live execution re-plans adaptively and
    fills `observed_cycle`). stop_condition is value repetition — the cycle closes
    when a written value-state reappears."""
    rep = cycles_from_evidence(log, spec)
    plans = []
    for src in event_sources(spec):
        r = rep.get(src["source_id"], {})
        if not r.get("multi_state"):
            continue
        visit, g = [], start_grid
        for _ in range(budget):
            path, g2 = plan_next_crossing(step_fn, g, src["rect"], src["mover_colors"],
                                          src["edge"], action_arity,
                                          trigger_actions=src.get("trigger_actions"),
                                          resource=resource)
            if path is None:
                break
            visit.append(path)
            g = g2
        plans.append({
            "source_id": src["source_id"],
            "rect": src["rect"],
            "edge": src["edge"],
            "mover_colors": src["mover_colors"],
            "write_cells": src["write_cells"],
            "distinct_values_so_far": r.get("distinct_values"),
            "visit_plan": visit,
            "budget": budget,
            "stop_condition": "value repetition",
            "observed_cycle": [],          # filled by live execution
        })
    return plans
