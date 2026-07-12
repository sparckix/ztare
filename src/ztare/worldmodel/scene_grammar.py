"""The screen grammar: a deterministic scene parser (the perception layer).

Game screens are composed BY human designers FOR human players. A frame is not
a flat field of physics cells: it is a play field, plus framed goal insets,
status readouts, resource bars, and chrome (title strips, borders, spacers).
The human eye decodes this layout for free. Raw-cell physics mining does not,
so it makes two mistakes that poison everything downstream: a status readout
that ticks in lock-step with events gets mined as *physics* (a spurious law),
and a framed goal display that never moves gets read as *background* (the goal
goes unread).

This layer types the frame's PANELS before roles or goal abduction run, using
only algebra over the evidence log:

  * connected background margins (recursive XY-cut) partition the canvas,
  * uniform rectangular rings recover framed insets a margin-cut can't split
    (a goal inset stays a clean ring even when a corridor attaches below it),
  * per-panel palette, temporal variance, and change-frame sets — read off the
    evidence log — drive the type tags.

Zero game constants. Zero LLM. Core-knowledge provenance: connected components,
rectangles, margins, palette statistics, temporal variance. Types are TAGS with
a confidence and an evidence receipt, never hard claims — a downstream consumer
(goal abduction, the mutator briefing) weighs them; this layer only proposes.

The single calibration knob is `SceneParams` (variance floors, thinness, sync
threshold): real screens are noisy and the right cut points are tuned, not
derived. Everything else is exact.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Iterable, NamedTuple, Optional

# A grid is anything indexable as grid[y][x] -> int (tuple-of-tuples in the log).
Grid = "Iterable"


class SceneParams(NamedTuple):
    """The calibration knob. Real screens are noisy; these cut points are tuned
    to the substrate, not derived. Defaults suit 64x64 ARC-style frames."""
    var_floor: float = 0.02        # variance below this counts as "static"
    thin_max: int = 3              # a panel is thin if its short side <= this
    thin_aspect: float = 4.0       # ...or if long/short side >= this
    sync_min: float = 0.5          # Jaccard(change-frames, play-field) for readout
    readout_area_frac: float = 0.5 # a readout is smaller than this * play-field
    min_area: int = 3              # drop panels smaller than this (noise)
    monotone_frac: float = 0.8     # fraction of adjacent steps that must agree


class PanelTag(NamedTuple):
    kind: str
    confidence: float
    evidence: str


@dataclass(frozen=True)
class Panel:
    id: int
    y0: int
    x0: int
    y1: int
    x1: int
    palette: tuple          # ((color, count), ...) sorted by color, from frame 0
    temporal_variance: float
    change_frames: frozenset
    frame_color: Optional[int]      # border color if a uniform ring, else None
    isolation: float                # fraction of the exterior ring that is background
    is_inset: bool                  # recovered by ring detection (may nest in a bigger panel)
    tags: tuple = field(default_factory=tuple)

    @property
    def h(self) -> int:
        return self.y1 - self.y0 + 1

    @property
    def w(self) -> int:
        return self.x1 - self.x0 + 1

    @property
    def area(self) -> int:
        return self.h * self.w

    @property
    def bbox(self) -> tuple:
        return (self.y0, self.x0, self.y1, self.x1)

    @property
    def kind(self) -> str:
        return self.tags[0].kind if self.tags else "unknown"

    @property
    def kinds(self) -> frozenset:
        return frozenset(t.kind for t in self.tags)

    def _replace_tags(self, tags: tuple) -> "Panel":
        return Panel(self.id, self.y0, self.x0, self.y1, self.x1, self.palette,
                     self.temporal_variance, self.change_frames, self.frame_color,
                     self.isolation, self.is_inset, tags)


@dataclass(frozen=True)
class Scene:
    height: int
    width: int
    background: int
    n_frames: int
    panels: tuple

    def panels_of(self, kind: str) -> "list[Panel]":
        return [p for p in self.panels if kind in p.kinds]

    def panel_pairs(self, kind_a: str, kind_b: str) -> "list[tuple]":
        """Consumer hook: every (a, b) panel pair matching the two tags — e.g.
        `panel_pairs("goal_display", "readout")` yields the template/copy
        candidates goal abduction consumes. Does not touch goal abduction; only
        exposes clean structures for it to read."""
        aa = self.panels_of(kind_a)
        bb = self.panels_of(kind_b)
        return [(a, b) for a in aa for b in bb if a.id != b.id]

    def to_briefing(self) -> str:
        """Compact human-readable panel map for the mutator briefing."""
        lines = [f"SCENE {self.height}x{self.width}  bg={self.background}  "
                 f"frames={self.n_frames}  panels={len(self.panels)}"]
        for p in sorted(self.panels, key=lambda q: (-q.area, q.y0, q.x0)):
            top = p.tags[0] if p.tags else PanelTag("unknown", 0.0, "no tag")
            pal = ",".join(f"{c}:{n}" for c, n in p.palette[:5])
            frame = f" frame={p.frame_color}" if p.frame_color is not None else ""
            inset = " inset" if p.is_inset else ""
            lines.append(
                f"  #{p.id} [{p.y0},{p.x0}]-[{p.y1},{p.x1}] {p.h}x{p.w}"
                f"{frame}{inset}  var={p.temporal_variance:.2f} iso={p.isolation:.2f}"
                f"  {top.kind}({top.confidence:.2f})  pal[{pal}]")
            lines.append(f"        - {top.evidence}")
            for t in p.tags[1:]:
                lines.append(f"        · also {t.kind}({t.confidence:.2f}): {t.evidence}")
        return "\n".join(lines)


# ── frame extraction ─────────────────────────────────────────────────────────

def _states(log) -> list:
    """The full observed grid sequence from an (s, a, s') evidence log: every s
    in order, then the final s'. Consecutive entries are the frames whose diffs
    give temporal variance."""
    rows = list(log)
    if not rows:
        return []
    states = [r.s for r in rows]
    states.append(rows[-1].s_next)
    return states


def _background(grid) -> int:
    return Counter(c for row in grid for c in row).most_common(1)[0][0]


# ── segmentation: recursive XY-cut on background margins ──────────────────────

def _runs(is_sep: "list[bool]") -> "list[tuple]":
    """Maximal (start, end) inclusive index ranges of NON-separator cells."""
    out, i, n = [], 0, len(is_sep)
    while i < n:
        if is_sep[i]:
            i += 1
            continue
        j = i
        while j < n and not is_sep[j]:
            j += 1
        out.append((i, j - 1))
        i = j
    return out


def _xy_cut(grid, bg, y0, y1, x0, x1, axis) -> "list[tuple]":
    """Recursive XY-cut: split a region at runs of all-background rows/cols,
    alternating axes. Leaves are rectangular content blocks with no interior
    background margin. The classic document-layout algorithm — deterministic,
    pure algebra."""
    if y1 < y0 or x1 < x0:
        return []
    if axis == "row":
        sep = [all(grid[y][x] == bg for x in range(x0, x1 + 1)) for y in range(y0, y1 + 1)]
        runs = _runs(sep)
        if not runs:
            return []
        if len(runs) > 1 or runs[0] != (0, y1 - y0):   # a split or a trim happened
            out = []
            for a, b in runs:
                out += _xy_cut(grid, bg, y0 + a, y0 + b, x0, x1, "col")
            return out
        return _xy_cut(grid, bg, y0, y1, x0, x1, "col")
    else:
        sep = [all(grid[y][x] == bg for y in range(y0, y1 + 1)) for x in range(x0, x1 + 1)]
        runs = _runs(sep)
        if not runs:
            return []
        if len(runs) > 1 or runs[0] != (0, x1 - x0):
            out = []
            for a, b in runs:
                out += _xy_cut(grid, bg, y0, y1, x0 + a, x0 + b, "row")
            return out
        return [(y0, y1, x0, x1)]                       # neither axis cuts -> leaf


# ── framed insets: uniform rectangular rings ─────────────────────────────────

def _find_frames(grid, bg) -> "list[tuple]":
    """Uniform-color rectangular rings enclosing structured content. Recovers
    framed insets a margin cut cannot split: a goal inset stays a complete ring
    even when a corridor attaches to the OUTSIDE of its border. Pairs identical
    horizontal border runs (top/bottom), then verifies the two vertical borders
    close the ring and the interior carries non-background, non-border content
    (an empty maze room is only bg+border -> rejected; the busy play field has
    no complete uniform ring -> rejected).

    ponytail: one ring per (color, span) via min/max row — two insets sharing an
    exact border span would merge. Upgrade to per-run-cluster if it ever bites.
    """
    h, w = len(grid), len(grid[0])
    spans: "dict[tuple, list[int]]" = defaultdict(list)
    for y in range(h):
        x = 0
        while x < w:
            c = grid[y][x]
            if c == bg:
                x += 1
                continue
            x2 = x
            while x2 + 1 < w and grid[y][x2 + 1] == c:
                x2 += 1
            if x2 - x >= 2:                     # a border run needs length >= 3
                spans[(c, x, x2)].append(y)
            x = x2 + 1
    frames = []
    for (c, x0, x1), ys in spans.items():
        y0, y1 = min(ys), max(ys)
        if y1 - y0 < 2:                         # ring height >= 3
            continue
        if not all(grid[y][x0] == c and grid[y][x1] == c for y in range(y0, y1 + 1)):
            continue                            # vertical borders must close the ring
        interior = {grid[y][x] for y in range(y0 + 1, y1) for x in range(x0 + 1, x1)}
        if interior <= {bg, c}:                 # empty room / solid block -> not a display
            continue
        frames.append((c, y0, y1, x0, x1))
    # drop a ring strictly inside another ring: the outer is the panel, the
    # inner is its content structure (a framed inset with a decorative inner border).
    def _within(f, g):  # frame tuple is (c, y0, y1, x0, x1); is f inside g?
        return (f != g and g[1] <= f[1] and g[3] <= f[3]
                and f[2] <= g[2] and f[4] <= g[4])
    return [f for f in frames if not any(_within(f, g) for g in frames)]


# ── per-panel temporal + palette features ────────────────────────────────────

def _palette(grid, y0, y1, x0, x1) -> tuple:
    cnt = Counter(grid[y][x] for y in range(y0, y1 + 1) for x in range(x0, x1 + 1))
    return tuple(sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0])))


def _isolation(grid, bg, y0, y1, x0, x1) -> float:
    """Fraction of the immediate exterior ring (one cell outside the bbox) that
    is background — how cleanly the panel is set apart from other content."""
    h, w = len(grid), len(grid[0])
    ring = []
    for x in range(x0 - 1, x1 + 2):
        ring += [(y0 - 1, x), (y1 + 1, x)]
    for y in range(y0, y1 + 1):
        ring += [(y, x0 - 1), (y, x1 + 1)]
    inb = [(y, x) for (y, x) in ring if 0 <= y < h and 0 <= x < w]
    if not inb:
        return 1.0
    return sum(1 for (y, x) in inb if grid[y][x] == bg) / len(inb)


def _change_frames(states, y0, y1, x0, x1) -> frozenset:
    """Indices k where the panel's bbox content differs between frame k-1 and k."""
    changed = set()
    prev = None
    for k, g in enumerate(states):
        block = tuple(tuple(g[y][x] for x in range(x0, x1 + 1)) for y in range(y0, y1 + 1))
        if prev is not None and block != prev:
            changed.add(k)
        prev = block
    return frozenset(changed)


def _nonbg_counts(states, bg, y0, y1, x0, x1) -> "list[int]":
    return [sum(1 for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if g[y][x] != bg)
            for g in states]


# ── typing ───────────────────────────────────────────────────────────────────

def _build_panels(grid, states, bg, params) -> "list[Panel]":
    """XY-cut leaves plus framed insets; drop a leaf that a frame already covers
    (the frame carries strictly more information). Panels get geometry, palette,
    variance, and change-frames — but no type tags yet."""
    leaves = _xy_cut(grid, bg, 0, len(grid) - 1, 0, len(grid[0]) - 1, "row")
    frames = _find_frames(grid, bg)
    frame_boxes = [(y0, y1, x0, x1) for (_, y0, y1, x0, x1) in frames]

    boxes = []                                          # (y0, x0, y1, x1, frame_color, is_inset)
    for (c, y0, y1, x0, x1) in frames:
        boxes.append((y0, x0, y1, x1, c, True))
    for (y0, y1, x0, x1) in leaves:
        covered = any(fy0 <= y0 and fx0 <= x0 and y1 <= fy1 and x1 <= fx1
                      for (fy0, fy1, fx0, fx1) in frame_boxes)
        if not covered:
            boxes.append((y0, x0, y1, x1, None, False))

    n_pairs = max(1, len(states) - 1)
    panels = []
    for pid, (y0, x0, y1, x1, fcolor, inset) in enumerate(
            sorted(boxes, key=lambda b: (b[0], b[1], b[2], b[3]))):
        if (y1 - y0 + 1) * (x1 - x0 + 1) < params.min_area:
            continue
        cf = _change_frames(states, y0, y1, x0, x1)
        panels.append(Panel(
            id=len(panels), y0=y0, x0=x0, y1=y1, x1=x1,
            palette=_palette(grid, y0, y1, x0, x1),
            temporal_variance=len(cf) / n_pairs,
            change_frames=cf,
            frame_color=fcolor,
            isolation=_isolation(grid, bg, y0, y1, x0, x1),
            is_inset=inset))
    return panels


def _monotone(seq: "list[int]") -> "tuple[float, str]":
    """Max fraction of adjacent steps that are non-increasing vs non-decreasing,
    with the winning direction. A resource bar's filled length moves one way."""
    if len(seq) < 2:
        return 0.0, "flat"
    inc = sum(1 for a, b in zip(seq, seq[1:]) if b >= a) / (len(seq) - 1)
    dec = sum(1 for a, b in zip(seq, seq[1:]) if b <= a) / (len(seq) - 1)
    return (dec, "shrinks") if dec >= inc else (inc, "grows")


def _type_panels(panels, states, bg, mover_colors, params) -> "list[Panel]":
    if not panels:
        return panels

    # play_field: the largest high-variance panel (optionally one holding a
    # mover-role color). Exactly one panel wins the tag; it anchors readout sync.
    movers = set(mover_colors or ())
    active = [p for p in panels if p.temporal_variance >= params.var_floor]
    cand = [p for p in active if movers & {c for c, _ in p.palette}] if movers else []
    if not cand:
        cand = active

    pf = None
    if cand:
        pf = max(cand, key=lambda p: (p.area, -p.y0, -p.x0))
    pf_cf = pf.change_frames if pf else frozenset()
    pf_area = pf.area if pf else 0

    out = []
    for p in panels:
        tags: "list[PanelTag]" = []

        if pf is not None and p.id == pf.id:
            conf = min(0.95, 0.6 + 0.3 * p.temporal_variance)
            ev = (f"largest high-variance region ({p.h}x{p.w}, var={p.temporal_variance:.2f})")
            if movers & {c for c, _ in p.palette}:
                conf = min(0.95, conf + 0.1)
                ev += f"; holds mover color(s) {sorted(movers & {c for c, _ in p.palette})}"
            tags.append(PanelTag("play_field", conf, ev))

        # goal_display: framed, static across ALL evidence, multi-color interior.
        interior_colors = {c for c, _ in p.palette if c not in (bg, p.frame_color)}
        if (p.frame_color is not None and p.temporal_variance < params.var_floor
                and len(interior_colors) >= 2):
            tags.append(PanelTag("goal_display", 0.9,
                                 f"framed (border={p.frame_color}), static across all "
                                 f"{len(states)} frames, {len(interior_colors)}-color content "
                                 f"{sorted(interior_colors)}"))

        # resource_bar: thin, content length changes monotonically.
        thin = min(p.h, p.w) <= params.thin_max or max(p.h, p.w) / max(1, min(p.h, p.w)) >= params.thin_aspect
        if thin and p.temporal_variance > 0 and (pf is None or p.id != pf.id):
            counts = _nonbg_counts(states, bg, p.y0, p.y1, p.x0, p.x1)
            mono, direction = _monotone(counts)
            if mono >= params.monotone_frac and len(set(counts)) > 1:
                # more specific than bare synchrony, so it outranks a co-firing readout
                tags.append(PanelTag("resource_bar", min(0.95, 0.55 + 0.4 * mono),
                                     f"thin {p.h}x{p.w}, filled length {direction} monotonically "
                                     f"({mono:.0%} of steps, {min(counts)}..{max(counts)} cells)"))

        # readout: small, mutable, its OWN changes coincide with play-field events.
        # Containment (not symmetric Jaccard): a readout ticks on SOME events, so
        # the test is "when this panel changes, did the field change too" — a rare
        # ticker against a busy field would never clear a symmetric threshold.
        if (pf is not None and p.id != pf.id and p.change_frames
                and p.temporal_variance >= params.var_floor
                and p.area < pf_area * params.readout_area_frac):
            sync = len(p.change_frames & pf_cf) / len(p.change_frames)
            if sync >= params.sync_min:
                tags.append(PanelTag("readout", min(0.9, 0.4 + 0.5 * sync),
                                     f"small ({p.h}x{p.w}), {sync:.0%} of its changes coincide "
                                     f"with play-field events"))

        # chrome: static and not a structured display.
        if p.temporal_variance < params.var_floor and not any(t.kind == "goal_display" for t in tags):
            edge = p.x0 == 0 or p.y0 == 0 or p.x1 == len(states[0][0]) - 1 or p.y1 == len(states[0]) - 1
            tags.append(PanelTag("chrome", 0.75 if edge else 0.6,
                                 "unchanged in every frame" + (" (canvas edge)" if edge else "")))

        tags.sort(key=lambda t: (-t.confidence, t.kind))
        out.append(p._replace_tags(tuple(tags)))
    return out


# ── entry point ──────────────────────────────────────────────────────────────

def parse_scene(log, mover_colors: "Optional[set]" = None,
                params: SceneParams = SceneParams()) -> Scene:
    """Parse an evidence log into a typed Scene: the perception layer.

    Segments the canvas into panels (XY-cut on background margins, plus framed
    insets recovered as uniform rings), reads each panel's palette, temporal
    variance, and change-frame set off the log, and tags each with proposed
    types (play_field / resource_bar / readout / goal_display / chrome), each
    carrying a confidence and an evidence receipt. Deterministic; no game
    constants; no LLM.

    `mover_colors` (optional) are role colors from a prior pass — if given, the
    play field is chosen among panels holding one. Segmentation uses the first
    frame; variance and synchrony use the whole log.
    """
    states = _states(log)
    if not states:
        return Scene(0, 0, 0, 0, ())
    grid = states[0]
    bg = _background(grid)
    panels = _build_panels(grid, states, bg, params)
    panels = _type_panels(panels, states, bg, mover_colors, params)
    return Scene(height=len(grid), width=len(grid[0]), background=bg,
                 n_frames=len(states), panels=tuple(panels))
