"""ARC-AGI-3 environment adapter (GP-250 P1-external).

Wraps the official `arc-agi` SDK (pip install arc-agi; docs.arcprize.org/toolkit)
behind the worldmodel `EnvironmentAdapter` protocol. The SDK runs games on the
LOCAL ARCEngine by default (anonymous key for online), so first contact needs
no credentials.

Verified contract (SDK 0.9.x, probed live 2026-07-03):
  arc_agi.Arcade().make(game_id) -> env
  env.action_space               -> [GameAction.ACTION1..]
  env.step(GameAction.X)         -> FrameDataRaw: .frame (list of 64x64 int8
                                    grids; LAST is the settled observation —
                                    the absorbing-worlds lesson), .state
                                    (GameState), .available_actions,
                                    .levels_completed, .full_reset

Sealed-target rule: this module relays frames and never inspects game
semantics; game docs must never reach loop-visible files.
"""

from __future__ import annotations

from ztare.worldmodel.grid_dsl import Grid


class ArcAgi3Error(RuntimeError):
    pass


def _grid(obs) -> Grid:
    frames = getattr(obs, "frame", None) or []
    if not frames:
        raise ArcAgi3Error("observation carried no frame")
    return tuple(tuple(int(c) for c in row) for row in frames[-1])


class ArcAgi3Adapter:
    """One game behind the worldmodel adapter protocol (reset/step/arity/t).

    Action index i maps onto the game's declared action space, fixed at
    construction so guard-family synthesis sees a stable arity. A finished
    game (WIN / GAME_OVER) auto-resets on the next step; `t` restarts with
    the episode and callers record it via append(..., t=adapter.t).
    """

    def __init__(self, game_id: str, arcade=None) -> None:
        import arc_agi
        self._arcade = arcade or arc_agi.Arcade()
        self._env = self._arcade.make(game_id)
        self.game_id = game_id
        self.env_id = f"arc3_{game_id.split('-')[0]}"
        self._actions = tuple(self._env.action_space)
        self._grid: "Grid | None" = None
        self._state = None
        self._t = 0
        self.levels_completed = 0
        self.steps_taken = 0
        # 2D coloured grids: shapes match up to the dihedral group D4 (Core
        # Knowledge geometry). A substrate on a different lattice registers its own
        # group and shape-comparison predicates follow with no call-site change.
        self.symmetry_group = "dihedral"

    # ── EnvironmentAdapter protocol ──────────────────────────────────────
    @property
    def action_arity(self) -> int:
        return len(self._actions)

    @property
    def t(self) -> int:
        return self._t

    @property
    def state(self) -> Grid:
        if self._grid is None:
            self.reset()
        return self._grid

    def reset(self) -> Grid:
        from arcengine import GameAction
        obs = self._env.step(GameAction.RESET)
        self._ingest(obs)
        self._t = 0
        return self._grid

    def step(self, action: int) -> Grid:
        if not 0 <= action < self.action_arity:
            raise ArcAgi3Error(f"action {action} outside arity {self.action_arity}")
        if self._grid is None or self._finished():
            self.reset()
        obs = self._env.step(self._actions[action])
        self._ingest(obs)
        self._t += 1
        self.steps_taken += 1
        return self._grid

    # ── internals ────────────────────────────────────────────────────────
    def _finished(self) -> bool:
        name = getattr(self._state, "name", str(self._state))
        return name in ("WIN", "GAME_OVER")

    def _ingest(self, obs) -> None:
        self._grid = _grid(obs)
        self._state = getattr(obs, "state", self._state)
        lv = getattr(obs, "levels_completed", None)
        if lv is not None:
            self.levels_completed = lv


def list_games(arcade=None) -> list:
    import arc_agi
    arc = arcade or arc_agi.Arcade()
    envs = arc.get_environments()
    return [getattr(e, "game_id", str(e)) for e in envs]
