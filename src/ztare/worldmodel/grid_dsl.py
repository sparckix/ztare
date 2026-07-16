"""Typed seed grammar for grid transition programs (GP-250 P0').

A transition program predicts the next grid from the current grid, the action
taken, and the step index. Programs are frozen tuple ASTs — hashable, tiny,
and enumerable — interpreted by `evaluate`.

The seed library is deliberately minimal and named for mathematical operations:
grid indexing/translation, color relabeling, cell counting, arithmetic,
equality, and conditionals. Nothing mechanic-shaped (collision, gravity,
toggling) is baked in: under the GP-250 provenance rule, such abstractions may
only enter the grammar by being compressed out of earned episode data and
promoted through the learning-promotion contract. `STEP` exposes the episode
step index, which covers simple latent state (parity, period-k counters)
without a POMDP.

Evaluation is fail-closed: any undefined operation returns None and the
candidate fails that transition. There is no clamping, no wrapping, no repair.

Expression types:
    IntExpr : ("lit", k) | ("action",) | ("step",) | ("add", i, i)
              | ("mod", i, i) | ("count", color_lit)
    BoolExpr: ("eq", i, i)
    GridExpr: ("s",) | ("shift", g, dy, dx) | ("recolor", g, from_i, to_i)
              | ("if", b, g, g)

A Program is a GridExpr evaluated against (grid, action, step).
"""

from __future__ import annotations

from itertools import product
from types import MappingProxyType
from typing import Iterator, Mapping, Optional

Grid = tuple  # tuple[tuple[int, ...], ...]
Program = tuple  # frozen AST node

# Seed literal pools. Colors 0..3 cover the P0' suite; the shift offsets are the
# 4-neighborhood plus identity components. Extending these pools is a grammar
# change and must be recorded on the seam.
COLOR_LITS = (0, 1, 2, 3)

# Earned grammar extensions (GP-250 provenance rule): plain Grid -> Grid
# transforms proposed at a grammar-ceiling event, compiled in the sandbox, and
# promoted only if the re-synthesized champion survives replay + rollout.
# Registered under operation names; receipts live in the project workspace.
EXTENSIONS: "dict[str, object]" = {}


def register_extension(name: str, fn) -> None:
    EXTENSIONS[name] = fn


def unregister_extension(name: str) -> None:
    EXTENSIONS.pop(name, None)
STEP_MODULI = (2, 3)
SHIFT_OFFSETS = (-1, 0, 1)


def grid_from_lists(rows) -> Grid:
    return tuple(tuple(int(c) for c in row) for row in rows)


def grid_to_lists(g: Grid) -> list:
    return [list(row) for row in g]


# ── evaluator ───────────────────────────────────────────────────────────────

def _eval_int(node: tuple, grid: Grid, action: int, step: int) -> Optional[int]:
    op = node[0]
    if op == "lit":
        return node[1]
    if op == "action":
        return action
    if op == "step":
        return step
    if op == "add":
        a = _eval_int(node[1], grid, action, step)
        b = _eval_int(node[2], grid, action, step)
        return None if a is None or b is None else a + b
    if op == "mod":
        a = _eval_int(node[1], grid, action, step)
        b = _eval_int(node[2], grid, action, step)
        if a is None or b is None or b == 0:
            return None
        return a % b
    if op == "count":
        color = node[1]
        return sum(1 for row in grid for c in row if c == color)
    return None


def _eval_bool(node: tuple, grid: Grid, action: int, step: int) -> Optional[bool]:
    if node[0] == "eq":
        a = _eval_int(node[1], grid, action, step)
        b = _eval_int(node[2], grid, action, step)
        return None if a is None or b is None else a == b
    return None


def _shift(grid: Grid, dy: int, dx: int) -> Grid:
    """Translate all non-background cells by (dy, dx). Vacated cells become 0;
    cells translated off the grid disappear. Background is color 0."""
    h, w = len(grid), len(grid[0])
    out = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            c = grid[y][x]
            if c == 0:
                continue
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w:
                out[ny][nx] = c
    return tuple(tuple(row) for row in out)


def evaluate(
    program: Program,
    grid: Grid,
    action: int,
    step: int,
    *,
    extensions: "Mapping[str, object] | None" = None,
) -> Optional[Grid]:
    """Interpret a GridExpr. Returns the predicted next grid, or None (fail-closed).

    Fail-closed is a hard guarantee: a malformed node returns None rather than
    raising (observed 2026-07-02: a lit-wrapped shift delta raised TypeError out
    of the interpreter, and the gate misread a near-correct candidate as
    inexpressible)."""
    try:
        registry = EXTENSIONS if extensions is None else extensions
        return _evaluate_unsafe(program, grid, action, step, registry)
    except Exception:  # noqa: BLE001 — fail-closed by contract
        return None


def _evaluate_unsafe(
    program: Program,
    grid: Grid,
    action: int,
    step: int,
    extensions: "Mapping[str, object]",
) -> Optional[Grid]:
    op = program[0]
    if op == "s":
        return grid
    if op == "shift":
        g = evaluate(program[1], grid, action, step, extensions=extensions)
        # deltas are raw ints in the seed grammar; int-expr nodes (a mutator's
        # natural ("lit", k) wrapping) are accepted as a benign superset
        dy = program[2] if isinstance(program[2], int) \
            else _eval_int(program[2], grid, action, step)
        dx = program[3] if isinstance(program[3], int) \
            else _eval_int(program[3], grid, action, step)
        if g is None or dy is None or dx is None:
            return None
        return _shift(g, dy, dx)
    if op == "recolor":
        g = evaluate(program[1], grid, action, step, extensions=extensions)
        a = _eval_int(program[2], grid, action, step)
        b = _eval_int(program[3], grid, action, step)
        if g is None or a is None or b is None:
            return None
        return tuple(tuple(b if c == a else c for c in row) for row in g)
    if op == "if":
        cond = _eval_bool(program[1], grid, action, step)
        if cond is None:
            return None
        return evaluate(
            program[2] if cond else program[3],
            grid,
            action,
            step,
            extensions=extensions,
        )
    if op == "ext":
        fn = extensions.get(program[1])
        if fn is None:
            return None
        g = evaluate(program[2], grid, action, step, extensions=extensions)
        if g is None:
            return None
        try:
            out = fn(g)
        except Exception:
            return None
        if (not isinstance(out, tuple) or not out
                or not all(isinstance(r, tuple) for r in out)):
            return None
        return out
    return None


def bind_extensions(program: Program, extensions: Mapping[str, object]):
    """Return a predictor whose earned-operation names resolve immutably.

    A persisted carrier owns the operation implementations it declares.  The
    process-wide registry remains the synthesis vocabulary, while executable
    carriers capture a read-only snapshot so later lowering cannot change an
    already-loaded program's meaning.
    """
    registry = MappingProxyType(dict(extensions))

    def bound(grid: Grid, action: int, step: int) -> Optional[Grid]:
        return evaluate(program, grid, action, step, extensions=registry)

    bound._ztare_program = program
    bound._ztare_extension_names = tuple(sorted(registry))
    return bound


def program_size(program: tuple) -> int:
    """Description length proxy: AST node count (uniform prior over the seed
    library). The DreamCoder-style learned prior is the P2 growth hook, via
    `ztare.fit.mdl.MDLLibrary` with this function as `size_fn`."""
    if not isinstance(program, tuple):
        return 1
    return 1 + sum(program_size(child) for child in program[1:] if isinstance(child, tuple)) \
             + sum(1 for child in program[1:] if not isinstance(child, tuple))


# ── type-directed enumeration ───────────────────────────────────────────────

def _int_exprs(max_size: int) -> Iterator[tuple]:
    yield ("action",)
    yield ("step",)
    for k in COLOR_LITS:
        yield ("lit", k)
    if max_size >= 3:
        for m in STEP_MODULI:
            yield ("mod", ("step",), ("lit", m))
        for c in COLOR_LITS:
            yield ("count", c)


def _bool_exprs(max_size: int) -> Iterator[tuple]:
    ints = list(_int_exprs(max_size - 1))
    for a, b in product(ints, repeat=2):
        if a[0] == "lit" and b[0] == "lit":
            continue  # constant comparisons are dead weight
        if program_size(("eq", a, b)) <= max_size:
            yield ("eq", a, b)


def _grid_exprs(max_size: int, depth: int) -> Iterator[tuple]:
    yield ("s",)
    if depth <= 0 or max_size < 3:
        return
    for g in _grid_exprs(max_size - 3, depth - 1):
        for dy, dx in product(SHIFT_OFFSETS, repeat=2):
            if (dy, dx) == (0, 0):
                continue
            cand = ("shift", g, dy, dx)
            if program_size(cand) <= max_size:
                yield cand
    for g in _grid_exprs(max_size - 3, depth - 1):
        for a, b in product(COLOR_LITS, repeat=2):
            if a == b:
                continue
            cand = ("recolor", g, ("lit", a), ("lit", b))
            if program_size(cand) <= max_size:
                yield cand


def enumerate_programs(max_size: int = 12, max_if_depth: int = 2) -> Iterator[Program]:
    """Yield seed-library programs in roughly increasing size: plain grid
    expressions first, then conditionals over them up to `max_if_depth` nested
    branches. The space is small by design; the LLM mutator enters only on a
    grammar-ceiling event, never here."""
    plain = [g for g in _grid_exprs(max_size, depth=2)]
    for g in plain:
        yield g
    if max_if_depth < 1:
        return
    bools = list(_bool_exprs(6))
    level = plain
    for _ in range(max_if_depth):
        nxt = []
        for cond in bools:
            for then_g, else_g in product(level, plain):
                if then_g == else_g:
                    continue
                cand = ("if", cond, then_g, else_g)
                if program_size(cand) <= max_size:
                    nxt.append(cand)
                    yield cand
        level = nxt
