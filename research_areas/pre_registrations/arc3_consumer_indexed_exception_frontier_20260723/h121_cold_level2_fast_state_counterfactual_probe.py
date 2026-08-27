#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Any, Mapping

from arcengine import ActionInput, GameAction

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.public.control.arc3_responses_agent_probe import (
    _append_trace_event,
    _emit_turn_progress,
    run_subscription_probe,
)
from ztare.substrates.arc_agi3 import ArcAgi3Adapter


GAME_SOURCE = ROOT / "environment_files/tu93/0768757b/tu93.py"
TRACE = Path(__file__).with_name(
    "h121_cold_level2_fast_state_counterfactual_trace.jsonl"
)
REPORT = Path(__file__).with_name(
    "h121_cold_level2_fast_state_counterfactual_report.json"
)
FROZEN_START_SHA256 = (
    "c654ced9fcd15bcc9937e6748e64c4d55b5fe15b21547acbb982068947f7eae4"
)
ACTION_SPACE = (
    GameAction.ACTION1,
    GameAction.ACTION2,
    GameAction.ACTION3,
    GameAction.ACTION4,
)


def _load_game_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ztare_h121_tu93", GAME_SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load local tu93 control environment")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _LevelTwoEnvironment:
    def __init__(self, module: ModuleType) -> None:
        self.module = module
        self.action_space = ACTION_SPACE
        self.game: Any | None = None

    def _reset_level_two(self) -> SimpleNamespace:
        self.game = self.module.Tu93()
        self.game.full_reset()
        self.game.set_level(1)
        frame = self.game.camera.render(
            self.game.current_level.get_sprites()
        )
        return SimpleNamespace(
            frame=[frame],
            state=self.game._state,
            levels_completed=0,
            available_actions=ACTION_SPACE,
            full_reset=True,
        )

    def step(self, action: GameAction) -> Any:
        if action == GameAction.RESET or self.game is None:
            return self._reset_level_two()
        return self.game.perform_action(ActionInput(id=action), raw=True)


class _LocalArcade:
    def __init__(self, module: ModuleType) -> None:
        self.module = module

    def make(self, _game_id: str) -> _LevelTwoEnvironment:
        return _LevelTwoEnvironment(self.module)


def main() -> int:
    if TRACE.exists() or REPORT.exists():
        raise SystemExit("H121 output paths must be new")
    module = _load_game_module()
    adapter = ArcAgi3Adapter(
        "tu93-0768757b",
        arcade=_LocalArcade(module),
    )

    def trace_event(event: Mapping[str, Any]) -> None:
        _append_trace_event(TRACE, event)

    def observe_turn(turn: Mapping[str, Any]) -> None:
        _emit_turn_progress(turn)
        trace_event({
            "schema": "ztare-arc3-probe-turn-checkpoint-v1",
            "turn": dict(turn),
        })

    trace_event({
        "schema": "ztare-arc3-probe-run-manifest-v1",
        "game": "tu93-0768757b",
        "start_level": 2,
        "budget": 10,
        "model": "gpt-5.6-sol",
        "reasoning_effort": "max",
        "transport": "subscription",
        "subscription_session": "new_then_resume",
        "level_one_history_injected": False,
        "frozen_start_observation_sha256": FROZEN_START_SHA256,
    })
    payload = run_subscription_probe(
        adapter=adapter,
        game_id="tu93-0768757b",
        budget=10,
        model_id="gpt-5.6-sol",
        reasoning_effort="max",
        timeout_seconds=300,
        resume_session=True,
        turn_observer=observe_turn,
        exchange_observer=trace_event,
        level_boundary_sleep_top_k=0,
    )
    start_sha256 = str(payload["observations"][0]["sha256"])
    if start_sha256 != FROZEN_START_SHA256:
        raise SystemExit(
            "cold control start observation does not match H119 Level 2"
        )
    REPORT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    trace_event({
        "schema": "ztare-arc3-probe-final-result-v1",
        "result": payload,
        "report_path": str(REPORT),
    })
    print(json.dumps({
        "status": payload["status"],
        "actions_executed": payload["actions_executed"],
        "levels_gained": payload["levels_gained"],
        "first_level_action": payload["first_level_action"],
        "start_observation_sha256": start_sha256,
        "action_sequence": [row["action"] for row in payload["turns"]],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
