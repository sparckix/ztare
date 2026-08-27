#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.public.control.arc3_responses_agent_probe import grid_rle  # noqa: E402
from scripts.public.control.arc3_responses_agent_probe import (  # noqa: E402
    settled_observation_receipt,
)
from ztare.substrates.arc_agi3 import ArcAgi3Adapter  # noqa: E402

from h121_cold_level2_fast_state_counterfactual_probe import (  # noqa: E402
    _LocalArcade,
    _load_game_module,
)


DIRECTORY = Path(__file__).resolve().parent
H119_REPORT = DIRECTORY / "h119_tu93_persistent_sol_max_report.json"
TRACE = DIRECTORY / "h121_cold_level2_fast_state_counterfactual_trace.jsonl"
RESULT = DIRECTORY / "h121_cold_level2_fast_state_counterfactual_result.json"
GRID_CARRIER_SHA256 = (
    "dde09802332964a1530f9c3b3509a3732aec0d69325f2d3af29cca5162c06b24"
)


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _grid_carrier(observation: dict[str, Any]) -> dict[str, Any]:
    return {
        "grid_shape": observation["grid_shape"],
        "grid_rle_rows": observation["grid_rle_rows"],
    }


def main() -> int:
    if RESULT.exists():
        raise SystemExit("H121 result path already exists")
    h119 = json.loads(H119_REPORT.read_text(encoding="utf-8"))
    treatment_start = h119["observations"][22]
    treatment_carrier = _grid_carrier(treatment_start)
    if _canonical_sha256(treatment_carrier) != GRID_CARRIER_SHA256:
        raise SystemExit("frozen treatment grid-carrier identity drifted")

    rows = [
        json.loads(line)
        for line in TRACE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    manifests = [
        row for row in rows
        if row.get("schema") == "ztare-arc3-probe-run-manifest-v1"
    ]
    exchanges = [
        row for row in rows
        if row.get("schema") == "ztare-codex-subscription-exchange-v1"
    ]
    turns = [
        row["turn"] for row in rows
        if row.get("schema") == "ztare-arc3-probe-turn-checkpoint-v1"
    ]
    if len(manifests) != 1 or len(exchanges) != 10 or len(turns) != 10:
        raise SystemExit("H121 trace cardinality failed")
    if any(row["returncode"] != 0 or not row["stdout"] for row in exchanges):
        raise SystemExit("H121 inference exchange failed or omitted output")
    session_ids = {str(row["session_id"]) for row in turns}
    exchange_session_ids = {
        str(row["final_session_state"]["session_id"])
        for row in exchanges
    }
    tick_counts = [
        int(row["final_session_state"]["tick_count"])
        for row in exchanges
    ]
    if len(session_ids) != 1 or session_ids != exchange_session_ids:
        raise SystemExit("H121 session identity drifted")
    if tick_counts != list(range(1, 11)):
        raise SystemExit("H121 session chronology drifted")

    module = _load_game_module()
    adapter = ArcAgi3Adapter(
        "tu93-0768757b",
        arcade=_LocalArcade(module),
    )
    grid = adapter.reset()
    cold_start = settled_observation_receipt(
        grid,
        observation_index=0,
        action_count=0,
        levels_completed=0,
        adapter_epoch=int(adapter.current_epoch),
        available_action_indices=(0, 1, 2, 3),
    )
    cold_carrier = {
        "grid_shape": [len(grid), len(grid[0])],
        "grid_rle_rows": grid_rle(grid),
    }
    if cold_carrier != treatment_carrier:
        raise SystemExit("H121 start grid carrier does not match H119")
    replay_levels = []
    replay_epochs = []
    for turn in turns:
        action = int(turn["action"])
        if action == -1:
            adapter.reset()
        else:
            adapter.step(action)
        replay_levels.append(int(adapter.levels_completed))
        replay_epochs.append(int(adapter.current_epoch))
    recorded_levels = [int(row["levels_completed"]) for row in turns]
    recorded_epochs = [int(row["adapter_epoch"]) for row in turns]
    if replay_levels != recorded_levels or replay_epochs != recorded_epochs:
        raise SystemExit("H121 deterministic replay disagrees with checkpoints")

    treatment_actions = [
        int(row["action"])
        for row in h119["turns"][22:32]
    ]
    control_actions = [int(row["action"]) for row in turns]
    control_levels = max(recorded_levels, default=0)
    disposition = (
        "fast_state_supported_single_pair"
        if control_levels == 0
        else "observation_sufficient"
    )
    output = {
        "schema": "ztare-h121-cold-level2-fast-state-counterfactual-v1",
        "hypothesis_id": (
            "H-GPSA-COLD-LEVEL2-FAST-STATE-COUNTERFACTUAL-20260808-121"
        ),
        "status": "complete",
        "disposition": disposition,
        "environment_contact": False,
        "controller_contact": True,
        "matched_start": {
            "equal": True,
            "grid_carrier_sha256": GRID_CARRIER_SHA256,
            "treatment_observation_receipt_sha256": treatment_start["sha256"],
            "control_observation_receipt_sha256": cold_start["sha256"],
        },
        "treatment": {
            "history": "persistent_after_level_1",
            "budget": 10,
            "levels_gained": 1,
            "action_sequence": treatment_actions,
            "oracle_excess_action_count": 0,
        },
        "control": {
            "history": "cold_level_2",
            "budget": 10,
            "levels_gained": control_levels,
            "action_sequence": control_actions,
            "recorded_adapter_epochs": recorded_epochs,
            "terminal_boundary_action": next(
                (
                    int(row["action_count"])
                    for row in turns
                    if (row.get("transition_identity") or {}).get(
                        "boundary_kind"
                    ) == "terminal_state:GAME_OVER"
                ),
                None,
            ),
        },
        "trace_integrity": {
            "event_count": len(rows),
            "exchange_count": len(exchanges),
            "turn_count": len(turns),
            "session_ids": sorted(session_ids),
            "session_tick_counts": tick_counts,
            "exchange_returncodes": sorted({
                int(row["returncode"]) for row in exchanges
            }),
            "empty_stdout_count": sum(not row["stdout"] for row in exchanges),
            "deterministic_replay_matched": True,
        },
        "information_gain": (
            "In this matched pair, prior session history saved at least the "
            "cold controller's action-map exploration and hazardous approach. "
            "The carried object is not identified by this test."
        ),
        "claim_boundary": (
            "One matched treatment-control pair on one Level-2 start. The "
            "result selects a representation-extraction test but does not "
            "estimate a population effect or credit external ZTARE memory."
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
