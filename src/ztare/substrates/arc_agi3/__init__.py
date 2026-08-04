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

from pathlib import Path

from ztare.common.task_discharge import (
    TaskDischargeContract,
    TaskDischargeReceipt,
)
from ztare.worldmodel.grid_dsl import Grid
from ztare.worldmodel.transition_identity import TransitionIdentity


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
        self._epoch_serial = -1
        self._last_transition_identity: "TransitionIdentity | None" = None
        self._task_discharge_baselines: dict[str, int] = {}
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
    def current_epoch(self) -> int:
        """Adapter-owned lifecycle identity of the current environment state."""
        return self._epoch_serial

    @property
    def state(self) -> Grid:
        if self._grid is None:
            self.reset()
        return self._grid

    @property
    def last_transition_identity(self) -> "TransitionIdentity | None":
        """Identity of the most recent action-bearing transition.

        The adapter, rather than grid-difference code or a candidate carrier,
        owns this classification because it alone observes the environment's
        level/reset lifecycle signal.
        """
        return self._last_transition_identity

    def adjudicate_task_discharge(
        self,
        contract: TaskDischargeContract,
    ) -> TaskDischargeReceipt:
        """Lower one registered ARC adjudicator into an authority receipt.

        The counter and comparison remain ARC adapter vocabulary.  Common
        lifecycle code sees only ``open`` or ``discharged``.
        """
        if contract.adjudicator_id != "arc.level_count.v1":
            raise KeyError(
                f"unknown ARC task adjudicator: {contract.adjudicator_id}"
            )
        comparison = contract.parameters.get("comparison")
        observed = int(self.levels_completed)
        baseline = None
        if comparison == "increase_from_run_entry":
            target_delta = contract.parameters.get("target_delta", 1)
            if isinstance(target_delta, bool) or not isinstance(target_delta, int):
                raise TypeError("ARC level-count target_delta must be an integer")
            if target_delta < 1:
                raise ValueError("ARC level-count target_delta must be positive")
            baseline = self._task_discharge_baselines.setdefault(
                contract.sha256,
                observed,
            )
            discharged = observed - baseline >= target_delta
        else:
            target = contract.parameters.get("target")
            if comparison not in {"at_least", "equals"}:
                raise ValueError(
                    "ARC level-count comparison must be at_least, equals, or "
                    "increase_from_run_entry"
                )
            if isinstance(target, bool) or not isinstance(target, int):
                raise TypeError("ARC level-count target must be an integer")
            discharged = (
                observed >= target if comparison == "at_least" else observed == target
            )
        refs = tuple(
            self._last_transition_identity.evidence_refs
            if discharged and self._last_transition_identity is not None
            else ()
        )
        if discharged and not refs:
            refs = (f"arc_adapter:levels_completed:{observed}",)
        return TaskDischargeReceipt(
            contract_sha256=contract.sha256,
            adjudicator_id=contract.adjudicator_id,
            status="discharged" if discharged else "open",
            authority="environment_adapter",
            observed={
                "levels_completed": observed,
                "run_entry_levels_completed": baseline,
                "delta_from_run_entry": None if baseline is None else observed - baseline,
            },
            evidence_refs=refs,
        )

    def reset(self) -> Grid:
        from arcengine import GameAction
        source_epoch = self._epoch_serial if self._epoch_serial >= 0 else None
        obs = self._env.step(GameAction.RESET)
        self._ingest(obs)
        self._t = 0
        self._epoch_serial += 1
        self._last_transition_identity = TransitionIdentity(
            kind="reset_boundary",
            authority="environment_adapter",
            source_epoch=source_epoch,
            target_epoch=self._epoch_serial,
            boundary_kind="environment_reset",
        )
        return self._grid

    def step(self, action: int) -> Grid:
        if not 0 <= action < self.action_arity:
            raise ArcAgi3Error(f"action {action} outside arity {self.action_arity}")
        source_epoch = self._epoch_serial if self._epoch_serial >= 0 else None
        reset_before_action = self._grid is None or self._finished()
        if self._grid is None or self._finished():
            self.reset()
        levels_before = self.levels_completed
        obs = self._env.step(self._actions[action])
        self._ingest(obs)
        self._t += 1
        self.steps_taken += 1
        if reset_before_action:
            # reset() already minted the target epoch.  The recorded row spans
            # the old state, environment reset, and the first action in the new
            # epoch; it therefore cannot be charged to one within-epoch law.
            self._last_transition_identity = TransitionIdentity(
                kind="reset_boundary",
                authority="environment_adapter",
                source_epoch=source_epoch,
                target_epoch=self._epoch_serial,
                boundary_kind="reset_before_action",
            )
        elif self.levels_completed != levels_before:
            target_epoch = self._epoch_serial + 1
            self._last_transition_identity = TransitionIdentity(
                kind="epoch_boundary",
                authority="environment_adapter",
                source_epoch=self._epoch_serial,
                target_epoch=target_epoch,
                boundary_kind="level_completed",
                evidence_refs=(
                    f"levels_completed:{levels_before}->{self.levels_completed}",
                ),
            )
            self._epoch_serial = target_epoch
        elif self._finished():
            target_epoch = self._epoch_serial + 1
            terminal_state = self._state_name()
            self._last_transition_identity = TransitionIdentity(
                kind="epoch_boundary",
                authority="environment_adapter",
                source_epoch=self._epoch_serial,
                target_epoch=target_epoch,
                boundary_kind=f"terminal_state:{terminal_state}",
                evidence_refs=(f"environment_state:{terminal_state}",),
            )
            self._epoch_serial = target_epoch
        else:
            # The public adapter reports level/terminal changes, but it does
            # not report every environment-owned respawn.  Absence of one of
            # those signals is therefore not positive evidence that this row
            # belongs to the within-epoch dynamics law.  Keep the identity
            # open so evidence-side reset classification can act; a future
            # adapter may emit ``dynamics`` only with a positive attestation.
            self._last_transition_identity = TransitionIdentity(
                kind="unclassified",
                authority="environment_adapter",
                source_epoch=self._epoch_serial,
                target_epoch=self._epoch_serial,
            )
        return self._grid

    # ── internals ────────────────────────────────────────────────────────
    def _finished(self) -> bool:
        name = self._state_name()
        return name in ("WIN", "GAME_OVER")

    def _state_name(self) -> str:
        return str(getattr(self._state, "name", self._state))

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


def adapter_from_project(project_dir, *, config=None):
    """Resolve one ARC adapter from adapter-owned project presentation."""
    project = Path(project_dir)
    config = config if isinstance(config, dict) else {}
    hint = str(config.get("game") or "").strip()
    if not hint:
        parts = project.name.split("_")
        hint = parts[1] if len(parts) >= 2 and parts[0] == "arc3" else ""
    game_id = hint if "-" in hint else next(
        (game for game in list_games() if game.startswith(hint)),
        None,
    )
    if not game_id:
        raise ValueError(f"could not resolve ARC game from project {project.name!r}")
    return ArcAgi3Adapter(game_id)
