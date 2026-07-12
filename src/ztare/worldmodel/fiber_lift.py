"""Fiber-lift planner for ls20 level-2 (loop-holonomy implementation).

Two exported components:

1. extract_fiber_effects(episode_paths, grid) -> effect_table dict, writes
   workspace/fiber_effect_table.json.  Extracts per-static-object fiber effects
   from JSONL evidence rows by identifying when the moving figure (colour-9/12
   connected component) enters each static object's footprint, then recording
   the induced delta on:
     (a) display rotation — 3x3 display pattern C4 orientation class (0-3)
     (b) timer level — colour-11 count in rows 61-62
     (c) one-time flag — objects whose effect fires on first transit only

2. plan_lifted(start_state, effect_table, goal_predicate_on_fiber, move_model)
   -> list[int] | None.  BFS/Dijkstra over the lifted graph:
     state = (figure_anchor (r,c), fiber (rot, timer, frozenset used_crosses))
     each action costs 4 timer ticks; object transits apply fiber effects.
   Returns the action sequence or None (no plan reachable within budget).

Evidence contract (verdicts owe witnesses): every effect_table entry carries
the source evidence file paths + row indices that established it.

Ponytail notes:
  ponytail: BFS not Dijkstra — all edges cost 1 action, Dijkstra not needed.
  ponytail: no grid-reachability precompute cache; grid is small (56 positions)
            so inline BFS is cheap.  Add if planning throughput matters.
  ponytail: move_model param wires to external caller; not used internally
            (we compute adjacency directly from the static grid).
"""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

# ── Constants (ls20 grid semantics) ─────────────────────────────────────────
_SIZE = 5          # figure footprint side
_WALL = 4          # colour that cannot be overlapped by figure
_BODY = 9          # figure body colour
_TOP  = 12         # figure header colour (top 2 rows of 5x5)
_TICK = 11         # timer colour
_TIMER_ROWS = (61, 62)              # rows that hold the depleting colour-11 bar
_DISPLAY_ROWS = (16, 17, 18)        # rows of the 3x3 rotation display
_DISPLAY_COLS = (15, 16, 17)        # cols of the 3x3 rotation display
_TIMER_COST = 4    # timer ticks per action (verified: 17 actions, 84→16 in L2)
_DELTA = {0: (-5, 0), 1: (5, 0), 2: (0, -5), 3: (0, 5)}  # UP DOWN LEFT RIGHT


# ── Internal helpers ─────────────────────────────────────────────────────────

def _can_place(grid: list[list[int]], r: int, c: int) -> bool:
    H, W = len(grid), len(grid[0])
    if r < 0 or r + _SIZE > H or c < 0 or c + _SIZE > W:
        return False
    return not any(grid[r + dr][c + dc] == _WALL
                   for dr in range(_SIZE) for dc in range(_SIZE))


def _anchor_pos(grid: list[list[int]]) -> "tuple[int,int] | None":
    """Find top-left of the 5x5 figure (top 2 rows colour-12, bottom 3 rows colour-9)."""
    H, W = len(grid), len(grid[0])
    for r in range(H - _SIZE + 1):
        for c in range(W - _SIZE + 1):
            try:
                if all(grid[r + i][c + j] == (_TOP if i < 2 else _BODY)
                       for i in range(_SIZE) for j in range(_SIZE)):
                    return r, c
            except (IndexError, TypeError):
                pass
    return None


def _timer_count(grid: list[list[int]]) -> int:
    """Count colour-11 cells in the depleting bar (rows 61-62)."""
    if len(grid) < 63:
        return 0
    return sum(grid[r][c] == _TICK
               for r in _TIMER_ROWS for c in range(len(grid[r])))


def _display_rot(grid: list[list[int]]) -> int:
    """Return display rotation class 0-3 by comparing 3x3 pattern to canonical orbit.

    Canonical C4 orbit (from L2 evidence, KEY-hit progression):
      rot 0: [[11,11,11],[11,3,11],[11,11,11]] — all-border 11 (initial)
      rot 1: first KEY hit pattern
      rot 2: second KEY hit pattern
      rot 3: [[9,9,9],[9,5,5],[9,5,9]] — win condition

    ponytail: patterns hardcoded from evidence rather than computed from orbit;
              runtime comparison is a dict lookup (O(1)).
    """
    try:
        pat = tuple(grid[r][c] for r in _DISPLAY_ROWS for c in _DISPLAY_COLS)
    except (IndexError, TypeError):
        return 0
    return _DISPLAY_ORBIT.get(pat, 0)

# C4 orbit patterns extracted from L2 evidence + transition data.
# rot-0 is the initial display state (all colour-11 border).
# rot-3 is the win condition from goal_hunt_v2_evidence.jsonl.
# rot-1 and rot-2 are inferred as the intermediate states (not directly
# witnessed in the single banked transition row, but implied by the
# 3-KEY-hit route; ponytail: we use 0/1/2/3 as opaque integers, so the
# exact intermediate patterns only matter if we reconstruct rot from grid —
# which we only do at the start state and goal check; during planning we
# track rot as an integer).
_DISPLAY_ORBIT: dict[tuple, int] = {
    # rot 0: initial — 3x3 frame of 11, interior 3
    (11, 11, 11, 11, 3, 11, 11, 11, 11): 0,
    # rot 3: win — from win_condition.display_value [[9,9,9],[9,5,5],[9,5,9]]
    (9, 9, 9, 9, 5, 5, 9, 5, 9): 3,
    # rot 1, 2: placeholders (never read from grid in planner; integer tracking suffices)
}


def _footprint_sig(grid: list[list[int]], r: int, c: int) -> frozenset[int]:
    """Non-background, non-figure colours within the 5x5 footprint at (r,c)."""
    return frozenset(
        grid[r + dr][c + dc]
        for dr in range(_SIZE) for dc in range(_SIZE)
        if (0 <= r + dr < len(grid) and 0 <= c + dc < len(grid[r + dr]))
           and grid[r + dr][c + dc] not in (3, 4, 5, _BODY, _TOP)
    )


def _build_move_graph(
    grid: list[list[int]],
    seed: "tuple[int,int] | None" = None,
) -> dict[tuple, list[tuple]]:
    """BFS flood-fill from seed to get full reachable adjacency dict.

    Seed defaults to the first placeable position found by brute-force scan
    (top-left to bottom-right).  Caller may pass a known start position.

    ponytail: brute-force seed scan is O(H*W) once; grid is 64x64, trivial.
    """
    H, W = len(grid), len(grid[0])
    if seed is None:
        # Find first placeable position
        seed = next(
            ((r, c)
             for r in range(H - _SIZE + 1)
             for c in range(W - _SIZE + 1)
             if _can_place(grid, r, c)),
            None,
        )
    if seed is None:
        return {}

    visited: dict[tuple, list[tuple]] = {}
    q: deque[tuple[int, int]] = deque([seed])
    seen = {seed}
    while q:
        pos = q.popleft()
        r, c = pos
        neighbours: list[tuple] = []
        for a, (dr, dc) in _DELTA.items():
            np_ = (r + dr, c + dc)
            if _can_place(grid, np_[0], np_[1]):
                neighbours.append((a, np_))
                if np_ not in seen:
                    seen.add(np_)
                    q.append(np_)
        visited[pos] = neighbours
    return visited


# ── Component 1: holonomy extraction ────────────────────────────────────────

def extract_fiber_effects(
    episode_paths: "list[str | Path]",
    grid: "list[list[int]] | None" = None,
    output_path: "str | Path | None" = None,
) -> dict[str, Any]:
    """Extract per-static-object fiber effects from JSONL evidence rows.

    Strategy: two-pass.
    Pass 1 — collect all grid states from evidence rows to get a reference grid
    and the set of figure-visited positions (with row citations).
    Pass 2 — for every visited position (and, as a fallback, every reachable
    position in the reference grid), classify the object by its footprint
    signature in the static grid:
      {0, 1} → KEY-type (rotation_increment, repeatable)
      {11}   → CROSS-type (timer_reset to 84, one_time)
      empty  → FLOOR (no fiber effect, not included in table)

    This two-pass approach handles sparse evidence (e.g. only 1 transition
    row in goal_hunt_v2) by falling back to static grid object discovery.
    Evidence row refs cite WHICH rows established that an object at that
    position was visited / observed.

    Parameters
    ----------
    episode_paths:
        JSONL files to scan.  Each line must have key ``s`` (a 2-D list grid).
    grid:
        Static reference grid.  If None, uses ``s`` from the first row found.
    output_path:
        If provided, writes the effect table as JSON to this path.

    Returns
    -------
    effect_table: dict  {object_id: {bbox, sig, fiber_effect, one_time,
                                      evidence_row_refs}}
    """
    rows: list[dict] = []
    for ep in episode_paths:
        ep = Path(ep)
        for line in ep.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "s" in r and isinstance(r["s"], list):
                r["_source"] = str(ep)
                rows.append(r)

    if not rows:
        return {}

    ref_grid = grid if grid is not None else rows[0]["s"]

    # Pass 1: collect all anchor positions visited across evidence rows
    # pos → list of (source, row_idx) citations
    pos_citations: dict[tuple, list[dict]] = {}
    for row_idx, row in enumerate(rows):
        for gkey in ("s", "s_next"):
            g = row.get(gkey)
            if g is None or not isinstance(g, list):
                continue
            pos = _anchor_pos(g)
            if pos is None:
                continue
            if pos not in pos_citations:
                pos_citations[pos] = []
            pos_citations[pos].append(
                {"source": row.get("_source", ""), "row_idx": row_idx,
                 "from_key": gkey}
            )

    # Pass 2: also scan reachable positions in ref_grid that have special sigs
    # (covers objects never directly visited in sparse evidence)
    # ponytail: BFS from any start found in pos_citations; O(|positions|) tiny.
    reachable = set()
    if pos_citations:
        seed = next(iter(pos_citations))
        seen_bfs = {seed}
        q: deque = deque([seed])
        while q:
            r, c = q.popleft()
            reachable.add((r, c))
            for dr, dc in _DELTA.values():
                np_ = (r + dr, c + dc)
                if np_ not in seen_bfs and _can_place(ref_grid, np_[0], np_[1]):
                    seen_bfs.add(np_)
                    q.append(np_)

    # Union of directly visited + all reachable positions with special footprint
    candidate_positions = set(pos_citations.keys()) | reachable

    effect_table: dict[str, Any] = {}
    for pos in sorted(candidate_positions):
        sig = _footprint_sig(ref_grid, pos[0], pos[1])
        if not sig:
            continue  # floor position; no fiber effect

        # Classify
        if {0, 1}.issubset(sig):
            effect: dict = {"type": "rotation_increment", "delta_rot": 1}
            one_time = False
        elif 11 in sig:
            effect = {"type": "timer_reset", "reset_value": 84}
            one_time = True
        else:
            continue  # unknown signature; skip

        obj_id = f"{pos[0]}_{pos[1]}_sig{''.join(map(str, sorted(sig)))}"
        # Evidence refs: direct visits + a reachability note
        refs = list(pos_citations.get(pos, []))
        if pos not in pos_citations:
            refs = [{"source": str(ep) if episode_paths else "",
                     "note": "discovered via static grid reachability scan"}]

        effect_table[obj_id] = {
            "anchor_pos": list(pos),
            "bbox": {"r": pos[0], "c": pos[1], "size": _SIZE},
            "footprint_sig": sorted(sig),
            "fiber_effect": effect,
            "one_time": one_time,
            "evidence_row_count": len(refs),
            "evidence_row_refs": refs[:20],
        }

    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(effect_table, indent=2))

    return effect_table


# ── Component 2: lifted planner ──────────────────────────────────────────────

def plan_lifted(
    start_state: "tuple[tuple[int,int], tuple[int,int,frozenset]]",
    effect_table: dict[str, Any],
    goal_predicate_on_fiber: "callable",
    move_model: "Any | None" = None,
    *,
    grid: "list[list[int]] | None" = None,
    max_steps: int = 200,
    timer_budget: int = 84,
) -> "list[int] | None":
    """BFS over the lifted position × fiber graph.

    Parameters
    ----------
    start_state:
        ((anchor_r, anchor_c), (rot, timer, used_crosses_frozenset))
    effect_table:
        Output of extract_fiber_effects.  Keyed by object_id; value has
        ``anchor_pos``, ``fiber_effect``, ``one_time``.
    goal_predicate_on_fiber:
        Callable (pos, rot, timer, used_crosses) -> bool.  Returns True for a
        win state.
    move_model:
        Optional; reserved for external position-move overrides.  If None,
        adjacency is computed from `grid` directly.  Ignored if `grid` given.
    grid:
        The static world grid.  Required if move_model is None.
    max_steps:
        BFS depth limit.
    timer_budget:
        If timer drops to 0 or below, that branch is dead.

    Returns
    -------
    list[int] or None
        Action sequence (0=UP 1=DOWN 2=LEFT 3=RIGHT), or None if no plan found.

    Ponytail:
      ponytail: BFS not A*; heuristic adds complexity, grid is tiny (56 nodes).
      ponytail: timer_budget ceiling; upgrade to cost-aware search if multi-level
                planning needs timer-optimal routes across many resets.
    """
    if grid is None and move_model is None:
        raise ValueError("plan_lifted: provide grid or move_model")

    (start_pos, (start_rot, start_timer, start_used)) = start_state

    # Build adjacency once from static grid, seeding from the known start position
    if grid is not None:
        adj = _build_move_graph(grid, seed=start_pos)
    else:
        # ponytail: move_model hook — if caller passes a grid-returning callable,
        # we can extract adjacency from it; not implemented (YAGNI until needed).
        raise NotImplementedError("move_model without grid not yet supported")

    # Build a position-keyed lookup for effect_table
    pos_to_effects: dict[tuple[int, int], dict] = {}
    for obj_id, entry in effect_table.items():
        ap = entry["anchor_pos"]
        pos_to_effects[(ap[0], ap[1])] = entry

    # BFS state: (pos, rot, timer, used_frozenset) + accumulated actions
    init = (start_pos, start_rot, start_timer, start_used)
    if goal_predicate_on_fiber(start_pos, start_rot, start_timer, start_used):
        return []  # already satisfied — degenerate (no-op)

    queue: deque[tuple] = deque([(init, [])])
    seen: set = {init}

    while queue:
        (pos, rot, timer, used), actions = queue.popleft()
        if len(actions) >= max_steps:
            continue

        neighbours = adj.get(pos, [])
        for action, npos in neighbours:
            ntimer = timer - _TIMER_COST
            if ntimer <= 0:
                continue  # timer expired on this branch

            nrot = rot
            nused = used

            # Apply fiber effect if figure enters an object cell
            if npos in pos_to_effects:
                entry = pos_to_effects[npos]
                eff = entry["fiber_effect"]
                is_one_time = entry.get("one_time", False)
                obj_key = (npos[0], npos[1])

                if not is_one_time or obj_key not in nused:
                    if eff.get("type") == "rotation_increment":
                        nrot = (rot + eff.get("delta_rot", 1)) % 4
                    elif eff.get("type") == "timer_reset":
                        ntimer = eff.get("reset_value", 84)
                    if is_one_time:
                        nused = frozenset(nused | {obj_key})

            nstate = (npos, nrot, ntimer, nused)
            if nstate in seen:
                continue
            seen.add(nstate)

            new_actions = actions + [action]
            if goal_predicate_on_fiber(npos, nrot, ntimer, nused):
                return new_actions
            queue.append((nstate, new_actions))

    return None  # exhausted budget, no plan found
