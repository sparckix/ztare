#!/usr/bin/env python3
from __future__ import annotations

from collections import deque
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

from arcengine import ActionInput, GameAction


ROOT = Path(__file__).resolve().parents[3]
GAME_SOURCE = ROOT / "environment_files/tu93/0768757b/tu93.py"
H119_REPORT = Path(__file__).with_name(
    "h119_tu93_persistent_sol_max_report.json"
)
RESULT = Path(__file__).with_name(
    "h120_geometry_normalized_acquisition_derivative_result.json"
)
ACTION_IDS = (
    GameAction.ACTION1,
    GameAction.ACTION2,
    GameAction.ACTION3,
    GameAction.ACTION4,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_game_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ztare_h120_tu93", GAME_SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load local tu93 evaluator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sprite_key(sprite: Any) -> tuple[Any, ...]:
    pixels = sprite.pixels
    return (
        str(sprite.name),
        tuple(str(tag) for tag in sprite.tags),
        int(sprite.x),
        int(sprite.y),
        int(sprite.rotation),
        bool(sprite.is_visible),
        tuple(int(value) for value in pixels.shape),
        hashlib.sha256(pixels.tobytes()).hexdigest(),
    )


def _state_key(game: Any) -> tuple[Any, ...]:
    sprites = list(game.current_level.get_sprites())
    sprite_indices = {id(sprite): index for index, sprite in enumerate(sprites)}
    delayed = tuple(sorted(
        (
            sprite_indices.get(id(sprite), -1),
            tuple(int(value) for value in values),
        )
        for sprite, values in game.ylmdnwbdyy.items()
    ))
    return (
        int(game.level_index),
        str(game._state),
        int(game.kdkehgjrzq),
        tuple(_sprite_key(sprite) for sprite in sprites),
        delayed,
    )


def _root_game(module: ModuleType, level_index: int) -> Any:
    game = module.Tu93()
    game.full_reset()
    game.set_level(level_index)
    return game


def _completed_level(game: Any, level_index: int) -> bool:
    return int(game.level_index) != int(level_index) or int(game._score) > 0


def _shortest_witness(
    module: ModuleType,
    *,
    level_index: int,
    max_depth: int,
) -> tuple[tuple[int, ...], dict[str, int]]:
    root = _root_game(module, level_index)
    queue = deque([(root, tuple())])
    seen = {_state_key(root)}
    expanded = 0
    generated = 0
    while queue:
        game, prefix = queue.popleft()
        if len(prefix) >= max_depth:
            continue
        expanded += 1
        for action_index, action_id in enumerate(ACTION_IDS):
            child = copy.deepcopy(game)
            child.perform_action(ActionInput(id=action_id), raw=False)
            generated += 1
            witness = prefix + (action_index,)
            if _completed_level(child, level_index):
                return witness, {
                    "expanded_state_count": expanded,
                    "generated_transition_count": generated,
                    "distinct_state_count": len(seen),
                }
            if str(child._state).endswith("GAME_OVER"):
                continue
            key = _state_key(child)
            if key in seen:
                continue
            seen.add(key)
            queue.append((child, witness))
    raise RuntimeError(
        f"no Level {level_index + 1} witness through depth {max_depth}"
    )


def _replay(
    module: ModuleType,
    *,
    level_index: int,
    witness: tuple[int, ...],
) -> dict[str, Any]:
    game = _root_game(module, level_index)
    completion_step = None
    for step, action_index in enumerate(witness, start=1):
        game.perform_action(
            ActionInput(id=ACTION_IDS[action_index]),
            raw=False,
        )
        if _completed_level(game, level_index):
            completion_step = step
            break
    return {
        "completed": completion_step is not None,
        "completion_step": completion_step,
        "witness_length": len(witness),
        "ended_level_index": int(game.level_index),
        "ended_score": int(game._score),
    }


def main() -> int:
    report = json.loads(H119_REPORT.read_text(encoding="utf-8"))
    if _sha256(H119_REPORT) != (
        "e0482a75e6d657315e43bf5860a3c15ceec51e7fbda272593dd169529e9ed2c3"
    ):
        raise SystemExit("frozen H119 report identity drifted")
    boundaries = report["level_boundary_actions"]
    observed = (
        int(boundaries[0]["action_count"]),
        int(boundaries[1]["action_count"])
        - int(boundaries[0]["action_count"]),
    )
    module = _load_game_module()
    level_rows = []
    excesses = []
    for level_index, observed_actions in enumerate(observed):
        witness, search = _shortest_witness(
            module,
            level_index=level_index,
            max_depth=observed_actions,
        )
        replay = _replay(
            module,
            level_index=level_index,
            witness=witness,
        )
        if not replay["completed"] or replay["completion_step"] != len(witness):
            raise SystemExit(f"Level {level_index + 1} witness replay failed")
        excess = observed_actions - len(witness)
        excesses.append(excess)
        level_rows.append({
            "level": level_index + 1,
            "observed_action_count": observed_actions,
            "oracle_minimum_action_count": len(witness),
            "excess_action_count": excess,
            "oracle_witness": list(witness),
            "search": search,
            "replay": replay,
        })
    if excesses == [0, 0]:
        disposition = "ceiling_limited"
    elif excesses[0] > 0 and excesses[1] < excesses[0]:
        disposition = "compounding_signal"
    else:
        disposition = "no_acceleration"
    output = {
        "schema": "ztare-h120-geometry-normalized-acquisition-derivative-v1",
        "hypothesis_id": (
            "H-GPSA-GEOMETRY-NORMALIZED-ACQUISITION-DERIVATIVE-20260808-120"
        ),
        "status": "offline_complete",
        "disposition": disposition,
        "environment_contact": False,
        "controller_contact": False,
        "identities": {
            "h119_report_sha256": _sha256(H119_REPORT),
            "game_source_sha256": _sha256(GAME_SOURCE),
            "game": str(report["game"]),
        },
        "levels": level_rows,
        "observed_segment_action_counts": list(observed),
        "oracle_minimum_action_counts": [
            row["oracle_minimum_action_count"] for row in level_rows
        ],
        "excess_action_counts": excesses,
        "claim_boundary": (
            "Exact local full-dynamics normalization of H119 Levels 1 and 2 "
            "only; oracle information was not exposed to an actor."
        ),
    }
    RESULT.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
