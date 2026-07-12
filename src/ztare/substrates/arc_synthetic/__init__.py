"""Sealed synthetic interactive-grid fixtures for GP-250 P0'.

Each environment hides a deterministic generating transition law behind a
turn-based act/observe interface, exactly as the numeric `*_gt.py` fixtures
hide a generating function. The sealed-target rule applies unchanged: the
synthesis kernel and the exploration policy may only ever see transitions
earned through `step()` (via the episode log). Only the BC harness's
equivalence check may import `generating_program` semantics, and only after
synthesis has finished — that firewall is what makes recovery a result.

Suite design (panel record, 2026-07-02): eight environments expressible in the
seed grammar (including two whose latent state is reachable through the step
index), two deliberately beyond it (iteration, rotation) that must close as
`grammar_ceiling`, and one degenerate identity world where the committee
collapses immediately and the policy must not lose to random by more than
overhead — kimi's standing inversion.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from ztare.worldmodel.grid_dsl import Grid, evaluate, grid_from_lists


def _rot90(g: Grid) -> Grid:
    return tuple(tuple(row) for row in zip(*g[::-1]))


def _gravity(g: Grid) -> Grid:
    """Iterate unit downward translation until stable (columns settle)."""
    h, w = len(g), len(g[0])
    out = [[0] * w for _ in range(h)]
    for x in range(w):
        col = [g[y][x] for y in range(h) if g[y][x] != 0]
        for i, c in enumerate(col):
            out[h - len(col) + i][x] = c
    return tuple(tuple(row) for row in out)


@dataclass(frozen=True)
class SealedEnv:
    """A sealed generating law. `transition(s, a, t)` is the hidden target."""
    env_id: str
    action_arity: int
    initial: Grid
    transition: "object"            # Callable[[Grid, int, int], Grid]
    expressible: bool               # in the seed grammar (harness bookkeeping only)
    note: str = ""
    episode_budget: int = 60
    # The sealed law's own AST when authored in the seed grammar. Consumed ONLY
    # by post-hoc certificate emission (Lean equivalence), never by synthesis
    # or the policy — same firewall as the equivalence check.
    sealed_program: "tuple | None" = None

    def rollout(self, actions: "list[int]") -> "list[tuple[Grid, int, Grid]]":
        s, out = self.initial, []
        for t, a in enumerate(actions):
            nxt = self.transition(s, a, t)
            out.append((s, a, nxt))
            s = nxt
        return out


def _dsl(program):
    """Author a sealed law as a seed-grammar program (kept private to this module)."""
    fn = lambda s, a, t: evaluate(program, s, a, t)  # noqa: E731
    fn.sealed_ast = program
    return fn


_BASE = grid_from_lists([[0, 1, 0, 0], [0, 0, 2, 0], [0, 0, 0, 0], [3, 0, 0, 0]])
_SPARSE = grid_from_lists([[0, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 0], [0, 0, 0, 2]])


ENVIRONMENTS: "tuple[SealedEnv, ...]" = (
    SealedEnv("e01_shift_on_a0", 6, _BASE,
              _dsl(("if", ("eq", ("action",), ("lit", 0)), ("shift", ("s",), 0, 1), ("s",))),
              True, "action 0 translates right; five other actions are inert"),
    SealedEnv("e02_recolor_swap", 3, _BASE,
              _dsl(("if", ("eq", ("action",), ("lit", 1)), ("recolor", ("s",), ("lit", 1), ("lit", 2)),
                    ("if", ("eq", ("action",), ("lit", 2)), ("recolor", ("s",), ("lit", 2), ("lit", 1)), ("s",)))),
              True, "action 1 relabels 1->2, action 2 relabels back: non-absorbing"),
    SealedEnv("e03_gravity", 2, _BASE, lambda s, a, t: _gravity(s) if a == 0 else s,
              False, "action 0 settles columns: iteration beyond the seed grammar"),
    SealedEnv("e04_step_parity_swap", 2, _BASE,
              _dsl(("if", ("eq", ("mod", ("step",), ("lit", 2)), ("lit", 0)),
                    ("recolor", ("s",), ("lit", 1), ("lit", 2)),
                    ("recolor", ("s",), ("lit", 2), ("lit", 1)))),
              True, "even steps 1->2, odd steps 2->1: latent state via step index"),
    SealedEnv("e05_period3_cycle", 2, _BASE,
              _dsl(("if", ("eq", ("mod", ("step",), ("lit", 3)), ("lit", 0)),
                    ("recolor", ("s",), ("lit", 1), ("lit", 2)),
                    ("recolor", ("s",), ("lit", 2), ("lit", 1)))),
              True, "period-3 relabel cycle: latent counter, non-absorbing"),
    SealedEnv("e06_directional_moves", 6, _BASE,
              _dsl(("if", ("eq", ("action",), ("lit", 0)), ("shift", ("s",), 0, 1),
                    ("if", ("eq", ("action",), ("lit", 1)), ("shift", ("s",), 0, -1), ("s",)))),
              True, "action-indexed translation left/right; four inert actions"),
    SealedEnv("e07_move_then_recolor", 2, _BASE,
              _dsl(("if", ("eq", ("action",), ("lit", 0)),
                    ("recolor", ("shift", ("s",), 1, 0), ("lit", 3), ("lit", 2)), ("s",))),
              True, "composed mechanic: translate down, then relabel 3 to 2"),
    SealedEnv("e08_identity", 3, _BASE, _dsl(("s",)),
              True, "degenerate world: nothing acts; the adversarial baseline env"),
    SealedEnv("e09_rotation", 2, _BASE, lambda s, a, t: _rot90(s) if a == 1 else s,
              False, "action 1 rotates the grid: outside the seed grammar"),
    SealedEnv("e10_count_gated_recolor", 2, _SPARSE,
              _dsl(("if", ("eq", ("count", 2), ("lit", 1)),
                    ("recolor", ("s",), ("lit", 2), ("lit", 1)),
                    ("recolor", ("s",), ("lit", 1), ("lit", 2)))),
              True, "count-gated relabel oscillation: state-dependent, non-absorbing"),
)


# BC-1'' high-arity suite: the regime the run-2 finding names (probe ordering
# matters when most actions are inert). Sealed like everything above.
HIGH_ARITY_SUITE: "tuple[SealedEnv, ...]" = (
    SealedEnv("h1_one_live_action_a3", 8, _BASE,
              _dsl(("if", ("eq", ("action",), ("lit", 3)), ("shift", ("s",), 0, 1), ("s",))),
              True, "one informative action among eight"),
    SealedEnv("h2_two_directions", 6, _BASE,
              _dsl(("if", ("eq", ("action",), ("lit", 0)), ("shift", ("s",), 0, 1),
                    ("if", ("eq", ("action",), ("lit", 1)), ("shift", ("s",), 1, 0), ("s",)))),
              True, "right/down among six actions"),
    SealedEnv("h3_count_gated_high_arity", 6, _SPARSE,
              _dsl(("if", ("eq", ("count", 2), ("lit", 1)),
                    ("recolor", ("s",), ("lit", 2), ("lit", 1)),
                    ("recolor", ("s",), ("lit", 1), ("lit", 2)))),
              True, "action-independent count oscillation; six actions all inert"),
    SealedEnv("h4_four_directions", 6, _BASE,
              _dsl(("if", ("eq", ("action",), ("lit", 0)), ("shift", ("s",), 0, 1),
                    ("if", ("eq", ("action",), ("lit", 1)), ("shift", ("s",), 0, -1),
                     ("if", ("eq", ("action",), ("lit", 2)), ("shift", ("s",), 1, 0),
                      ("if", ("eq", ("action",), ("lit", 3)), ("shift", ("s",), -1, 0), ("s",)))))),
              True, "four directional actions, two inert"),
)


def scripted_random_actions(env: SealedEnv, n: int, seed: int) -> "list[int]":
    rng = random.Random(seed)
    return [rng.randrange(env.action_arity) for _ in range(n)]
