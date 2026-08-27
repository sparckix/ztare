#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[2]
sys.path.insert(0, str(DIRECTORY))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import h123_pose_action_mediator_surgery_probe as h123  # noqa: E402
from h121_cold_level2_fast_state_counterfactual_probe import (  # noqa: E402
    _LocalArcade,
    _load_game_module,
)
from ztare.substrates.arc_agi3 import ArcAgi3Adapter  # noqa: E402


RESULT = DIRECTORY / "h123_pose_action_mediator_surgery_result.json"
OUTPUT = DIRECTORY / "h123_pose_action_mediator_surgery_audit_result.json"
EXPECTED_SCHEMAS = {
    "ztare-arc3-probe-run-manifest-v1": 1,
    "ztare-codex-subscription-exchange-v1": 10,
    "ztare-arc3-probe-turn-checkpoint-v1": 10,
    "ztare-arc3-probe-final-result-v1": 1,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _replay(actions: list[int], report: dict[str, Any]) -> dict[str, Any]:
    adapter = ArcAgi3Adapter(
        "tu93-0768757b",
        arcade=_LocalArcade(_load_game_module()),
    )
    grids = [adapter.state]
    transitions = []
    for action in actions:
        grids.append(adapter.step(action))
        identity = adapter.last_transition_identity
        transitions.append({
            "kind": identity.kind if identity is not None else None,
            "boundary_kind": (
                identity.boundary_kind if identity is not None else None
            ),
            "adapter_epoch": adapter.current_epoch,
            "levels_completed": adapter.levels_completed,
        })
    expected_grids = [h123._grid(row) for row in report["observations"]]
    return {
        "observation_count": len(grids),
        "all_observations_match": grids == expected_grids,
        "final_levels_completed": adapter.levels_completed,
        "first_terminal_action": next(
            (
                index + 1
                for index, row in enumerate(transitions)
                if row["boundary_kind"] == "level_completed"
                or str(row["boundary_kind"]).startswith("terminal_state:")
            ),
            None,
        ),
        "transition_rows": transitions,
    }


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("H123 audit output must be new")
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    manifest = json.loads(
        (h123.OUTPUT_DIR / "manifest.json").read_text(encoding="utf-8")
    )
    capsules, receipt = h123._capsules(
        target_member_count=int(manifest["target_matching_mover_count"])
    )
    if receipt != manifest["capsule_receipt"]:
        raise SystemExit("H123 capsule receipt drifted")

    arms = {}
    for label in ("pose_action_map", "pose_only_placebo"):
        report_path = h123.OUTPUT_DIR / f"{label}_report.json"
        trace_path = h123.OUTPUT_DIR / f"{label}_trace.jsonl"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        trace = _read_jsonl(trace_path)
        counts = Counter(str(row.get("schema")) for row in trace)
        exchanges = [
            row
            for row in trace
            if row.get("schema") == "ztare-codex-subscription-exchange-v1"
        ]
        decoded_outputs = [json.loads(row["stdout"]) for row in exchanges]
        capsule_text = h123._rendered_capsule(capsules[label]).decode("utf-8")
        capsule_prompt_turns = [
            int(row["turn_index"])
            for row in exchanges
            if capsule_text in str(row["prompt"])
        ]
        actions = [int(row["action"]) for row in report["turns"]]
        replay = _replay(actions, report)
        arms[label] = {
            "report_sha256": _sha256(report_path),
            "trace_sha256": _sha256(trace_path),
            "schema_counts": dict(sorted(counts.items())),
            "trace_schema_counts_match": dict(counts) == EXPECTED_SCHEMAS,
            "all_exchange_returncodes_zero": all(
                int(row["returncode"]) == 0 for row in exchanges
            ),
            "all_exchange_outputs_parse": len(decoded_outputs) == 10,
            "exchange_actions_match_report": [
                int(row["action"]) for row in decoded_outputs
            ] == actions,
            "capsule_prompt_turns": capsule_prompt_turns,
            "capsule_is_one_shot": capsule_prompt_turns == [0],
            "stable_session": len({
                str(row["session_id"]) for row in report["turns"]
            }) == 1,
            "action_sequence": actions,
            "levels_gained": int(report["levels_gained"]),
            "first_prediction": str(decoded_outputs[0]["prediction"]),
            "replay": replay,
        }

    passed = all(
        row[check]
        for row in arms.values()
        for check in (
            "trace_schema_counts_match",
            "all_exchange_returncodes_zero",
            "all_exchange_outputs_parse",
            "exchange_actions_match_report",
            "capsule_is_one_shot",
            "stable_session",
        )
    ) and all(
        row["replay"]["all_observations_match"] for row in arms.values()
    )
    if not passed:
        raise SystemExit("H123 audit failed")
    output = {
        "schema": "ztare-h123-pose-action-mediator-surgery-audit-v1",
        "status": "passed",
        "environment_contact": False,
        "controller_contact": False,
        "result_sha256": _sha256(RESULT),
        "capsule_receipt": receipt,
        "arm_order": result["arm_order"],
        "registered_disposition": result["disposition"],
        "arms": arms,
        "settlement": {
            "causal_levels": arms["pose_action_map"]["levels_gained"],
            "placebo_levels": arms["pose_only_placebo"]["levels_gained"],
            "disposition": "inverted_refuted",
            "information_gain": (
                "A correct actuator map was not a sufficient behavioral "
                "mediator in this pair. The uncertainty-bearing placebo "
                "selected the oracle route; the map arm selected a fatal "
                "head-on route."
            ),
        },
    }
    OUTPUT.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
