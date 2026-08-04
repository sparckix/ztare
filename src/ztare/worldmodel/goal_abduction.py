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

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any, Callable, ClassVar

from ztare.common.equivariance import stable_sha256
from ztare.common.relational_task_contract import TaskHypothesisVersionSpace

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
            elif isinstance(m, dict):
                # Adapter role descriptors keep feature values as presentation
                # metadata while their behavioral identity remains structural.
                got.update(
                    int(x) for x in (m.get("feature_values") or [])
                    if isinstance(x, int) and not isinstance(x, bool)
                )
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


def _authoritative_completions(rows) -> list[int]:
    """Environment-owned level boundaries; grid properties have no veto."""
    return [
        index
        for index, transition in enumerate(rows)
        if transition.identity is not None
        and transition.identity.is_authoritative
        and transition.identity.kind == "epoch_boundary"
        and transition.identity.boundary_kind == "level_completed"
    ]


@dataclass(frozen=True)
class AuthoritativeGoalEdgePredicate:
    """Finite, bank-witnessed success edges with no cross-level claim."""

    time_aware: ClassVar[bool] = True
    witnesses: tuple[tuple[object, int, int, str, object], ...]

    def __call__(self, grid, action, time=None) -> bool:
        return any(
            grid == source
            and action == expected
            and (time is None or time == witness_time)
            for source, expected, witness_time, _evidence_ref, _source_epoch
            in self.witnesses
        )

    @property
    def goal_source_states(self) -> tuple[object, ...]:
        # Preserve evidence order while quotienting byte-identical sources.
        out = []
        for source, _action, _time, _ref, _source_epoch in self.witnesses:
            if source not in out:
                out.append(source)
        return tuple(out)

    def nearest_future_sources(self, start_time: int) -> tuple[object, ...]:
        future = [row for row in self.witnesses if row[2] >= start_time]
        if not future:
            return ()
        nearest_time = min(row[2] for row in future)
        return tuple(row[0] for row in future if row[2] == nearest_time)

    def for_source_epoch(self, source_epoch: object) -> "AuthoritativeGoalEdgePredicate | None":
        """Restrict exemplars to the lifecycle in which their edge occurred.

        A boundary outcome has a reusable identity, but its source grid is only
        a presentation inside one epoch.  Returning ``None`` when the bank has
        no exemplar for the active epoch prevents an old source presentation
        from becoming a target in a new ontology.
        """
        selected = tuple(row for row in self.witnesses if row[4] == source_epoch)
        return AuthoritativeGoalEdgePredicate(selected) if selected else None


@dataclass
class RelationalGoalEdgeHypothesisSet:
    """Lower relational task candidates into the planner's edge protocol.

    ``describe_edge`` is a substrate adapter from a source, operation, and
    optional time coordinate to an opaque relation descriptor.  The common
    version space decides which descriptors satisfy active hypotheses.
    """

    time_aware: ClassVar[bool] = True
    target_kind: ClassVar[str] = "hypothesis_edge_version_space"

    hypotheses: TaskHypothesisVersionSpace
    describe_edge: Callable[[Any, Any, Any], Any]
    descriptor_id: str
    operations: tuple[Any, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not str(self.descriptor_id).strip():
            raise ValueError("relational goal edges require descriptor_id")
        if not self.hypotheses.edge_hypotheses:
            raise ValueError(
                "relational goal edges require at least one edge hypothesis"
            )
        if len(self.operations) != len(set(self.operations)):
            raise ValueError("relational goal-edge operations must be unique")

    @property
    def active_count(self) -> int:
        return self.hypotheses.active_count

    @property
    def task_contract_sha256(self) -> str:
        return self.hypotheses.task_contract_sha256

    @property
    def identity_sha256(self) -> str:
        return stable_sha256({
            "task_hypotheses": self.hypotheses.identity_sha256,
            "descriptor_id": self.descriptor_id,
            "operations": list(map(repr, self.operations)),
            "evidence_refs": self.evidence_refs,
        })

    def relation_projection_key(
        self,
        source: Any,
        time: Any = None,
    ) -> tuple[tuple[Any, tuple[tuple[str, bool], ...]], ...]:
        """Truth vector whose equality preserves every nominated edge test."""
        return tuple(
            (
                operation,
                self.hypotheses.edge_projection_key(
                    source,
                    operation,
                    self.describe_edge(source, operation, time),
                ),
            )
            for operation in self.operations
        )

    def satisfied_ids(
        self,
        source: Any,
        operation: Any,
        time: Any = None,
    ) -> tuple[str, ...]:
        descriptor = self.describe_edge(source, operation, time)
        return self.hypotheses.edge_satisfied_ids(
            source,
            operation,
            descriptor,
        )

    def __call__(
        self,
        source: Any,
        operation: Any,
        time: Any = None,
    ) -> bool:
        return bool(self.satisfied_ids(source, operation, time))

    def refute_satisfied(
        self,
        source: Any,
        operation: Any,
        time: Any = None,
    ) -> tuple[str, ...]:
        descriptor = self.describe_edge(source, operation, time)
        return self.hypotheses.refute_edge_satisfied(
            source,
            operation,
            descriptor,
        )

    def for_source_epoch(
        self,
        source_epoch: object,
    ) -> "RelationalGoalEdgeHypothesisSet | None":
        chart = self.hypotheses.source_epoch
        return self if chart is None or chart == source_epoch else None


def authoritative_goal_edge_predicate(log, *, source_epoch: object | None = None):
    """Compile environment-success receipts into an edge predicate.

    A completion is an intervention-bearing transition identity. Treating it
    as a property of the successor frame loses the action and asks the learned
    dynamics to predict an environment-owned repaint. The returned predicate
    recognizes only bank-witnessed ``(source_state, action)`` edges and makes no
    cross-level or symmetry claim.
    """
    witnesses = [
        (
            transition.s,
            transition.a,
            transition.t,
            next(iter(transition.identity.evidence_refs), f"episode_row:{index}"),
            transition.identity.source_epoch,
        )
        for index, transition in enumerate(log)
        if transition.identity is not None
        and transition.identity.is_authoritative
        and transition.identity.kind == "epoch_boundary"
        and transition.identity.boundary_kind == "level_completed"
    ]
    if not witnesses:
        return None, 0

    predicate = AuthoritativeGoalEdgePredicate(tuple(witnesses))
    if source_epoch is not None:
        predicate = predicate.for_source_epoch(source_epoch)
        if predicate is None:
            return None, 0
    return predicate, len(predicate.witnesses)


def goal_edge_matches(predicate, grid, action, time) -> bool:
    """Invoke a typed time-aware edge, preserving legacy two-argument callers."""
    if getattr(predicate, "time_aware", False):
        return predicate(grid, action, time)
    return bool(predicate(grid, action))


# ── entry point ──────────────────────────────────────────────────────────────

def abduce_goal_candidates(log, spec, roles) -> dict:
    rows = list(log)
    spec = _norm_spec(spec)
    resource = _role_members(roles, "monotone_depleting")
    completions = _authoritative_completions(rows)
    if not completions and resource and rows:
        completions = _completions(rows, resource)
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


def _support_predicate(positions, *, differs_from_start=True):
    """Exact grid-support identity plus a derived display rectangle."""
    cells = sorted({(int(y), int(x)) for y, x in positions})
    return {
        "cells": [[y, x] for y, x in cells],
        "region": _region(cells),
        "differs_from_start": bool(differs_from_start),
    }


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
            "predicate_spec": _support_predicate((y, x) for y, x, _c in cells),
            "experiment_specs": [dict(rule)],
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
            candidate_positions = set(cand_pos)
            candidates.append({
                "kind": "never_visited_indicator",
                "predicate_spec": _support_predicate(cand_pos),
                "experiment_specs": [
                    dict(rule)
                    for rule in _all_rules(spec)
                    if rule.get("op") == "region_event"
                    and candidate_positions
                    & {(y, x) for y, x, _color in _event_write_cells(rule)}
                ],
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
        sub = [_support_predicate(cells, differs_from_start=changed)
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


def _norm_support_pattern(grid, cells, bg) -> frozenset:
    """Normalize values only on the declared support, excluding its hull."""
    selected = [
        (int(y), int(x))
        for y, x in cells
        if _in(grid, int(y), int(x)) and grid[int(y)][int(x)] not in bg
    ]
    if not selected:
        return frozenset()
    my = min(y for y, _x in selected)
    mx = min(x for _y, x in selected)
    return frozenset((y - my, x - mx, grid[y][x]) for y, x in selected)


def _support_components(cells) -> list[set[tuple[int, int]]]:
    """4-connected components of an exact write support."""
    remaining = {(int(y), int(x)) for y, x in cells}
    out = []
    while remaining:
        seed = remaining.pop()
        component = {seed}
        frontier = [seed]
        while frontier:
            y, x = frontier.pop()
            for neighbour in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    component.add(neighbour)
                    frontier.append(neighbour)
        out.append(component)
    return out


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
        written = {(y, x): c for y, x, c in triples}
        if not written:
            continue
        for cells in _support_components(written):
            pal = {written[cell] for cell in cells}
            pal |= {start[y][x] for y, x in cells if _in(start, y, x)}
            copies.append((cells, pal - bg, rule))
    out, seen = [], set()
    for (ccells, cpal, source_rule) in copies:
        for (tcells, tpal) in templates:
            if ccells == tcells or not (cpal & tpal):
                continue
            crect, trect = tuple(_region(sorted(ccells))), tuple(_region(sorted(tcells)))
            if (crect, trect) in seen:
                continue
            seen.add((crect, trect))
            # already-matched at start => nothing to achieve => not a goal (drops a
            # copy sub-shape that coincidentally equals a template)
            if _norm_support_pattern(start, ccells, bg) == _norm_support_pattern(
                start, tcells, bg
            ):
                continue
            out.append({
                "kind": "template_match",
                "predicate_spec": {
                    "copy_cells": [[y, x] for y, x in sorted(ccells)],
                    "template_cells": [[y, x] for y, x in sorted(tcells)],
                    "copy_region": list(crect),
                    "template_region": list(trect),
                    "relation": "content_equal_up_to_alignment",
                    "background": sorted(bg),
                },
                "experiment_specs": [dict(source_rule)],
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
    event_rules = [
        rule for rule in _all_rules(spec) if rule.get("op") == "region_event"
    ]
    for combo in combos:
        if any(all(_region_changed(g, start, cells) for cells in combo) for g in grids):
            continue                                   # co-witnessed -> not dormant
        out.append({
            "kind": "dormant_conjunction",
            "predicate_spec": {"conjunction": [
                _support_predicate(cells)
                for cells in combo]},
            "experiment_specs": [
                dict(rule)
                for rule in event_rules
                if set().union(*combo)
                & {(y, x) for y, x, _color in _event_write_cells(rule)}
            ],
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
            "goal_predicate_spec": _support_predicate(goal_pos),
            "support": len(completions)}


# ── predicate compilation (usable by reachability_sweep goal_fn) ─────────────


class GoalHypothesisSet:
    """Version space of task predicates under adapter adjudication.

    A state predicate proposes where to intervene; it does not own task
    discharge.  If the registered adjudicator remains open after a reached
    predicate, that exact hypothesis is removed while its siblings survive.
    """

    target_kind: ClassVar[str] = "hypothesis_version_space"

    def __init__(
        self,
        hypotheses,
        experiments=None,
        *,
        source_epoch=None,
        task_contract_sha256="",
    ):
        self.hypotheses = tuple(hypotheses)
        self.experiments = {
            hypothesis_id: tuple(rules)
            for hypothesis_id, rules in dict(experiments or {}).items()
        }
        self.refuted_ids: set[str] = set()
        self._ztare_source_epoch = source_epoch
        self.task_contract_sha256 = str(task_contract_sha256 or "")

    def _active(self):
        return (
            row for row in self.hypotheses if row[0] not in self.refuted_ids
        )

    @property
    def identity_sha256(self) -> str:
        from ztare.common.equivariance import stable_sha256

        return stable_sha256({
            "active_goal_hypotheses": sorted(
                hypothesis_id for hypothesis_id, *_rest in self._active()
            ),
            "source_epoch": self._ztare_source_epoch,
            "task_contract_sha256": self.task_contract_sha256,
        })

    def __call__(self, grid) -> bool:
        return any(
            predicate(grid)
            for _id, predicate, _kind, _spec in self._active()
        )

    def satisfied_ids(self, grid) -> tuple[str, ...]:
        return tuple(
            hypothesis_id
            for hypothesis_id, predicate, _kind, _spec in self._active()
            if predicate(grid)
        )

    def refute_satisfied(self, grid) -> tuple[str, ...]:
        refuted = self.satisfied_ids(grid)
        self.refuted_ids.update(refuted)
        return refuted

    def predicate_for(self, hypothesis_id: str):
        """Return the predicate owned by one exact hypothesis identity."""
        return next(
            (
                predicate
                for candidate_id, predicate, _kind, _spec in self.hypotheses
                if candidate_id == str(hypothesis_id)
            ),
            None,
        )

    def refute_ids(self, hypothesis_ids) -> tuple[str, ...]:
        """Remove only identities present in this version space.

        Stored task consequences are scoped and witness-checked by the caller;
        this method deliberately owns no persistence or substrate semantics.
        """
        known = {hypothesis_id for hypothesis_id, *_rest in self.hypotheses}
        admitted = tuple(
            dict.fromkeys(
                str(hypothesis_id)
                for hypothesis_id in hypothesis_ids
                if str(hypothesis_id) in known
            )
        )
        self.refuted_ids.update(admitted)
        return admitted

    def for_source_epoch(self, source_epoch):
        """Return this version space only in the chart that induced it."""

        if self._ztare_source_epoch is None:
            return self
        return self if self._ztare_source_epoch == source_epoch else None

    def projection_key(self, grid) -> tuple:
        """Truth vector of the active terminal hypotheses.

        Pixel presentations belong to the substrate chart.  The goal consumer
        only distinguishes which candidate conditions hold; transition and
        feasibility coordinates remain in the composed search problem.
        """
        return tuple(
            (hypothesis_id, bool(predicate(grid)))
            for hypothesis_id, predicate, _kind, _spec in self._active()
        )

    @property
    def active_experiment_domain_ids(self) -> tuple[str, ...]:
        from ztare.common.equivariance import stable_sha256

        return tuple(dict.fromkeys(
            "operation_domain_" + stable_sha256(rule)[:16]
            for hypothesis_id, rules in self.experiments.items()
            if hypothesis_id not in self.refuted_ids
            for rule in rules
        ))

    def experiment_edge_ids(self, source, successor) -> tuple[str, ...]:
        """Active hypotheses whose evidence-derived operation fires here."""
        from ztare.worldmodel.spec_catalog import region_event_triggered

        return tuple(
            hypothesis_id
            for hypothesis_id, rules in self.experiments.items()
            if hypothesis_id not in self.refuted_ids
            and any(
                region_event_triggered(source, successor, rule)
                for rule in rules
            )
        )

    @property
    def active_count(self) -> int:
        return sum(1 for _row in self._active())


def compose_goal_hypothesis_sets(*spaces):
    """Union compatible task-predicate version spaces without type erasure.

    Producers may contribute different presentations of the same hypothesis or
    different experiment domains.  Composition is keyed by hypothesis identity
    and is defined only inside one lifecycle/task chart.
    """

    active_spaces = tuple(space for space in spaces if space is not None)
    if not active_spaces:
        return None
    if len(active_spaces) == 1:
        return active_spaces[0]
    if not all(isinstance(space, GoalHypothesisSet) for space in active_spaces):
        raise TypeError("task-hypothesis composition requires version-space operands")
    chart = {
        (space._ztare_source_epoch, space.task_contract_sha256)
        for space in active_spaces
    }
    if len(chart) != 1:
        raise ValueError("cannot compose task hypotheses across lifecycle charts")

    hypotheses: dict[str, tuple] = {}
    experiments: dict[str, list[dict]] = {}
    experiment_ids: dict[str, set[str]] = {}
    from ztare.common.equivariance import stable_sha256

    for space in active_spaces:
        for row in space.hypotheses:
            hypotheses.setdefault(row[0], row)
        for hypothesis_id, rules in space.experiments.items():
            seen = experiment_ids.setdefault(hypothesis_id, set())
            for rule in rules:
                rule_id = stable_sha256(rule)
                if rule_id not in seen:
                    seen.add(rule_id)
                    experiments.setdefault(hypothesis_id, []).append(rule)
    source_epoch, task_contract_sha256 = next(iter(chart))
    result = GoalHypothesisSet(
        tuple(hypotheses.values()),
        experiments,
        source_epoch=source_epoch,
        task_contract_sha256=task_contract_sha256,
    )
    result.refuted_ids.update(
        hypothesis_id
        for space in active_spaces
        for hypothesis_id in space.refuted_ids
        if hypothesis_id in hypotheses
    )
    return result


def compile_goal_hypothesis_set(
    candidates,
    start_grid,
    symmetry_group="identity",
    *,
    task_open_states=(),
    source_epoch=None,
    task_contract_sha256="",
):
    """Compile a task-predicate version space and replay negative evidence.

    ``task_open_states`` are adapter-attested observations at which the task
    adjudicator remained open.  Any state predicate already true on one of
    those observations is behaviorally refuted regardless of its source name.
    """

    from ztare.common.equivariance import stable_sha256

    hypotheses: dict[str, tuple] = {}
    experiments: dict[str, list[dict]] = {}
    experiment_ids: dict[str, set[str]] = {}
    for candidate in candidates:
        spec = candidate.get("predicate_spec")
        if not spec:
            continue
        identity = {
            "kind": str(candidate.get("kind") or "candidate_goal"),
            "predicate_spec": spec,
        }
        hypothesis_id = stable_sha256(identity)
        hypotheses.setdefault(
            hypothesis_id,
            (
                hypothesis_id,
                predicate_from_spec(spec, start_grid, symmetry_group),
                identity["kind"],
                spec,
            ),
        )
        candidate_experiments = candidate.get("experiment_specs") or ()
        admitted_experiments = tuple(
            dict(experiment)
            for experiment in candidate_experiments
            if isinstance(experiment, dict)
            and experiment.get("op") == "region_event"
        )
        for experiment in admitted_experiments:
            experiment_id = stable_sha256(experiment)
            seen = experiment_ids.setdefault(hypothesis_id, set())
            if experiment_id in seen:
                continue
            seen.add(experiment_id)
            experiments.setdefault(hypothesis_id, []).append(experiment)
    if not hypotheses:
        return None
    result = GoalHypothesisSet(
        tuple(hypotheses.values()),
        experiments,
        source_epoch=source_epoch,
        task_contract_sha256=task_contract_sha256,
    )
    for state in task_open_states:
        result.refute_satisfied(state)
    return result


def compile_candidate_goal_hypothesis_set(
    project_dir,
    *,
    source_epoch,
    task_contract_sha256,
    witness_states=(),
    task_open_states=(),
    records=None,
):
    """Project leaf-authored task predicates independently of carrier adoption.

    Candidate memory is an evidence-epoch-bound audit population.  A transition
    carrier may lose its promotion contest while the task predicate carried in
    the same submission remains a useful, falsifiable steering hypothesis.  The
    adapter therefore projects ``GOAL_PREDICATE`` from current candidate rows
    into its own version space.  Task discharge authority remains external.

    Program-byte identity is deliberately conservative: executable predicate
    equivalence is undecidable.  Negative task receipts transfer across new
    program presentations by replaying their states through each predicate,
    rather than by pretending two source files are identical.
    """

    contract_sha = str(task_contract_sha256 or "").strip().lower()
    if (
        len(contract_sha) != 64
        or any(ch not in "0123456789abcdef" for ch in contract_sha)
    ):
        return None
    project = Path(project_dir).resolve()
    if records is None:
        from ztare.common.candidate_memory import (
            admissible_candidate_memory_records,
        )

        records = admissible_candidate_memory_records(
            project,
            artifact_roles={"task_hypothesis"},
            require_submission_source=True,
        )
    from ztare.common.candidate_memory import (
        candidate_memory_source,
        candidate_memory_submission_path,
    )
    from ztare.common.equivariance import stable_sha256

    probes = tuple(witness_states)[:16]
    hypotheses: list[tuple] = []
    seen_sources: set[str] = set()
    for record in sorted(
        (row for row in (records or ()) if isinstance(row, dict)),
        key=lambda row: str(row.get("observed_at_utc") or ""),
        reverse=True,
    ):
        path = candidate_memory_submission_path(project, record)
        source = candidate_memory_source(project, record)
        if path is None or not source:
            continue
        source_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
        if source_sha in seen_sources:
            continue
        seen_sources.add(source_sha)
        namespace = {"__name__": "candidate_task_hypothesis"}
        try:
            exec(compile(source, str(path), "exec"), namespace)  # noqa: S102
            predicate = namespace.get("GOAL_PREDICATE")
            if not callable(predicate):
                continue
            if any(type(predicate(state)) is not bool for state in probes):
                continue
        except Exception:  # noqa: BLE001 - one bad proposal cannot hide siblings
            continue
        binding = record.get("carrier_evidence_identity")
        binding = binding if isinstance(binding, dict) else {}
        evidence_epoch = str(
            record.get("evidence_epoch_sha256")
            or binding.get("evidence_epoch_sha256")
            or ""
        )
        identity = {
            "kind": "candidate_task_hypothesis",
            "task_contract_sha256": contract_sha,
            "source_epoch": source_epoch,
            "evidence_epoch_sha256": evidence_epoch,
            "candidate_source_sha256": source_sha,
        }
        hypothesis_id = stable_sha256(identity)
        hypotheses.append(
            (
                hypothesis_id,
                predicate,
                identity["kind"],
                {
                    "source_ref": str(path.relative_to(project)),
                    "source_sha256": source_sha,
                },
            )
        )
    if not hypotheses:
        return None
    result = GoalHypothesisSet(
        hypotheses,
        source_epoch=source_epoch,
        task_contract_sha256=contract_sha,
    )
    for state in task_open_states:
        result.refute_satisfied(state)
    return result


def predicate_spec_supported(pspec) -> bool:
    """Whether the adapter has a non-vacuous lowering for this predicate."""
    if not isinstance(pspec, dict) or not pspec:
        return False
    conjunction = pspec.get("conjunction")
    if conjunction is not None:
        return (
            isinstance(conjunction, list)
            and bool(conjunction)
            and all(predicate_spec_supported(sub) for sub in conjunction)
        )
    if pspec.get("relation") == "content_equal_up_to_alignment":
        return (
            _valid_cell_support(pspec.get("template_cells"))
            and _valid_cell_support(pspec.get("copy_cells"))
        ) or all(
            isinstance(pspec.get(key), (list, tuple)) and len(pspec[key]) == 4
            for key in ("template_region", "copy_region")
        )
    if "resource_zero" in pspec:
        value = pspec.get("resource_zero")
        return isinstance(value, int) and not isinstance(value, bool)
    if pspec.get("cells") is not None:
        return _valid_cell_support(pspec.get("cells"))
    region = pspec.get("region")
    return (
        isinstance(region, (list, tuple))
        and len(region) == 4
        and all(isinstance(value, int) and not isinstance(value, bool) for value in region)
    )


def _valid_cell_support(cells) -> bool:
    return (
        isinstance(cells, (list, tuple))
        and bool(cells)
        and all(
            isinstance(cell, (list, tuple))
            and len(cell) == 2
            and all(isinstance(value, int) and not isinstance(value, bool) for value in cell)
            for cell in cells
        )
    )


def predicate_from_spec(pspec, start_grid, symmetry_group="identity"):
    """Compile a predicate_spec to ``goal_fn(grid) -> bool`` with region-differs-
    from-start semantics. A ``conjunction`` spec compiles to the AND of its
    sub-predicates. Fail-closed: a malformed spec / out-of-range grid -> False.

    `symmetry_group` is supplied by the substrate after it has earned the
    corresponding quotient authority.  The default preserves only the
    predicate's declared alignment relation; it does not promote a geometric
    prior into object identity.  A certified 2D adapter may pass ``dihedral``;
    another substrate may pass its own executable action."""
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
        tcells, ccells = pspec.get("template_cells"), pspec.get("copy_cells")
        if tcells and ccells:
            tpat = _norm_support_pattern(start_grid, tcells, bg)
            observed = lambda grid: _norm_support_pattern(grid, ccells, bg)
        elif trect and crect:
            tpat = _norm_pattern(start_grid, trect, bg)
            observed = lambda grid: _norm_pattern(grid, crect, bg)
        else:
            return lambda g: False
        if not tpat:                                   # empty template => no goal
            return lambda g: False
        tcanon = canonical_form(tpat, symmetry_group)

        def tm_fn(grid):
            try:
                return canonical_form(observed(grid), symmetry_group) == tcanon
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
    differs = bool(pspec.get("differs_from_start", True))
    H = len(start_grid)
    W = len(start_grid[0]) if H else 0
    if pspec.get("cells") is not None:
        try:
            cells = {(int(y), int(x)) for y, x in pspec["cells"]}
        except (TypeError, ValueError):
            return lambda g: False
        if not cells or any(not (0 <= y < H and 0 <= x < W) for y, x in cells):
            return lambda g: False
        base = {(y, x): start_grid[y][x] for y, x in cells}
    else:
        if pspec.get("region") is None:
            return lambda g: False
        y0, x0, y1, x1 = (int(v) for v in pspec["region"])
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
