#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.public.control.arc3_responses_agent_probe import (  # noqa: E402
    _append_trace_event,
    _emit_turn_progress,
    run_subscription_probe,
)
from ztare.substrates.arc_agi3 import ArcAgi3Adapter  # noqa: E402
from ztare.worldmodel.episode_log import EpisodeLog  # noqa: E402
from ztare.worldmodel.object_roles import (  # noqa: E402
    induce_roles,
    object_signature,
)
from ztare.worldmodel.transition_identity import TransitionIdentity  # noqa: E402

from h121_cold_level2_fast_state_counterfactual_probe import (  # noqa: E402
    _LocalArcade,
    _load_game_module,
)


DIRECTORY = Path(__file__).resolve().parent
H119_REPORT = DIRECTORY / "h119_tu93_persistent_sol_max_report.json"
H122_RESULT = DIRECTORY / "h122_pose_quotiented_mover_identity_result.json"
OUTPUT_DIR = DIRECTORY / "h123_pose_action_mediator_surgery"
RESULT = DIRECTORY / "h123_pose_action_mediator_surgery_result.json"
H122_SHA256 = (
    "60dbf8f66377625a28f08a1252c07f11f99f17673848cd16dab535ae712f0dd7"
)
TARGET_GRID_CARRIER_SHA256 = (
    "dde09802332964a1530f9c3b3509a3732aec0d69325f2d3af29cca5162c06b24"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _grid(observation):
    grid = []
    for encoded in observation["grid_rle_rows"]:
        row = []
        for run in encoded.split(","):
            value, count = (int(part) for part in run.split("x"))
            row.extend([value] * count)
        grid.append(tuple(row))
    return tuple(grid)


def _grid_carrier(observation):
    return {
        "grid_shape": observation["grid_shape"],
        "grid_rle_rows": observation["grid_rle_rows"],
    }


def _source_roles(report):
    log = EpisodeLog()
    for index, turn in enumerate(report["turns"][:22]):
        log.append(
            _grid(report["observations"][index]),
            int(turn["action"]),
            _grid(report["observations"][index + 1]),
            t=index,
            identity=TransitionIdentity.from_dict(
                turn["transition_identity"]
            ),
        )
    return induce_roles(log, 4).roles


def _rendered_capsule(capsule: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(capsule),
        separators=(",", ":"),
    ).encode("utf-8")


def _capsules(*, target_member_count: int):
    common = {
        "schema": "ztare-arc3-selected-sleep-memory-v1",
        "source_result_sha256": H122_SHA256,
        "source_game": "tu93-0768757b",
        "source_epoch": 0,
        "target_compatibility": {
            "identity_relation": "d4_pose_v1",
            "matching_mover_count": target_member_count,
            "action_namespace": [0, 1, 2, 3],
            "status": "witnessed",
        },
        "memories": [],
        "active_uncertainties": [
            "The target route, obstacle effects, and hazard rules are unknown."
        ],
        "next_decision_questions": [
            "Which graph route reaches the visible target while respecting new entities?"
        ],
        "padding": "",
    }
    causal = {
        **common,
        "memories": [{
            "memory_id": "h122_pose_action_map",
            "claim": (
                "The D4 orbit identifies the controlled 3x3 color-9 component "
                "with one color-4 pose marker. Under the stable target action "
                "namespace, action 0 moves up, action 1 moves down, action 2 "
                "moves left, and action 3 moves right."
            ),
            "support": {
                "action_0": 3,
                "action_1": 7,
                "action_2": 3,
                "action_3": 8,
            },
            "guard": (
                "Consume only when exactly one D4-matching mover is visible "
                "and the action namespace remains [0,1,2,3]."
            ),
            "refusal": (
                "Do not import source coordinates, route, obstacle behavior, "
                "or a target action sequence."
            ),
        }],
    }
    placebo = {
        **common,
        "memories": [{
            "memory_id": "h122_pose_only_placebo",
            "claim": (
                "The D4 orbit identifies the controlled 3x3 color-9 component "
                "with one color-4 pose marker. Four stable target action "
                "indices moved it in the source episode; their direction "
                "assignment is withheld and must be inferred locally."
            ),
            "support": {
                "source_transition_count": 21,
                "observed_pose_count": 4,
                "distinct_action_count": 4,
                "total_motion_support": 21,
            },
            "guard": (
                "Consume only when exactly one D4-matching mover is visible "
                "and the action namespace remains [0,1,2,3]."
            ),
            "refusal": (
                "Do not import a direction assignment, source coordinates, "
                "route, obstacle behavior, or a target action sequence."
            ),
        }],
    }
    causal_bytes = _rendered_capsule(causal)
    placebo_bytes = _rendered_capsule(placebo)
    if len(causal_bytes) < len(placebo_bytes):
        causal["padding"] = " " * (len(placebo_bytes) - len(causal_bytes))
    elif len(placebo_bytes) < len(causal_bytes):
        placebo["padding"] = " " * (len(causal_bytes) - len(placebo_bytes))
    causal_bytes = _rendered_capsule(causal)
    placebo_bytes = _rendered_capsule(placebo)
    if len(causal_bytes) != len(placebo_bytes):
        raise RuntimeError("H123 capsule rendering is not exact-byte matched")
    return {
        "pose_action_map": causal,
        "pose_only_placebo": placebo,
    }, {
        "rendered_prompt_bytes": len(causal_bytes),
        "pose_action_map_sha256": hashlib.sha256(causal_bytes).hexdigest(),
        "pose_only_placebo_sha256": hashlib.sha256(placebo_bytes).hexdigest(),
        "pair_sha256": hashlib.sha256(
            causal_bytes + b"\x00" + placebo_bytes
        ).hexdigest(),
    }


def _run_arm(
    *,
    label: str,
    capsule: Mapping[str, Any],
    capsule_receipt: Mapping[str, Any],
    order_index: int,
    treatment_carrier,
):
    trace_path = OUTPUT_DIR / f"{label}_trace.jsonl"
    report_path = OUTPUT_DIR / f"{label}_report.json"
    if trace_path.exists() or report_path.exists():
        raise RuntimeError(f"H123 arm output already exists: {label}")
    adapter = ArcAgi3Adapter(
        "tu93-0768757b",
        # The game mutates module-level level objects. A fresh module is part
        # of the arm boundary, so the second arm cannot inherit board state
        # produced by the first.
        arcade=_LocalArcade(_load_game_module()),
    )

    def trace_event(event: Mapping[str, Any]) -> None:
        _append_trace_event(trace_path, event)

    def observe_turn(turn: Mapping[str, Any]) -> None:
        _emit_turn_progress(turn)
        trace_event({
            "schema": "ztare-arc3-probe-turn-checkpoint-v1",
            "arm": label,
            "turn": dict(turn),
        })

    trace_event({
        "schema": "ztare-arc3-probe-run-manifest-v1",
        "hypothesis": "H123",
        "arm": label,
        "order_index": order_index,
        "budget": 10,
        "model": "gpt-5.6-sol",
        "reasoning_effort": "max",
        "start_level": 2,
        "capsule_pair_receipt": dict(capsule_receipt),
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
        initial_recall_digest=capsule,
    )
    if _grid_carrier(payload["observations"][0]) != treatment_carrier:
        raise RuntimeError(f"H123 {label} start-grid carrier drifted")
    injected_turns = [
        index
        for index, turn in enumerate(payload["turns"])
        if turn.get("recall_injection") is not None
    ]
    if injected_turns != [0]:
        raise RuntimeError(f"H123 {label} recall was not exactly one-shot")
    report_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    trace_event({
        "schema": "ztare-arc3-probe-final-result-v1",
        "arm": label,
        "result": payload,
        "report_path": str(report_path),
    })
    return {
        "label": label,
        "status": payload["status"],
        "levels_gained": int(payload["levels_gained"]),
        "first_level_action": payload["first_level_action"],
        "actions_executed": int(payload["actions_executed"]),
        "action_sequence": [
            int(turn["action"]) for turn in payload["turns"]
        ],
        "session_ids": sorted({
            str(turn["session_id"]) for turn in payload["turns"]
        }),
        "one_shot_recall": injected_turns == [0],
        "report_path": str(report_path),
        "trace_path": str(trace_path),
    }


def main() -> int:
    if RESULT.exists() or OUTPUT_DIR.exists():
        raise SystemExit("H123 outputs must be new")
    if _sha256(H122_RESULT) != H122_SHA256:
        raise SystemExit("frozen H122 result identity drifted")
    h119 = json.loads(H119_REPORT.read_text(encoding="utf-8"))
    target_observation = h119["observations"][22]
    treatment_carrier = _grid_carrier(target_observation)
    if _canonical_sha256(treatment_carrier) != TARGET_GRID_CARRIER_SHA256:
        raise SystemExit("H123 target grid-carrier identity drifted")
    roles = _source_roles(h119)
    target_agent, _resource, _reactive = object_signature(
        _grid(target_observation), roles
    )
    target_member_count = len(target_agent)
    if target_member_count != 1:
        raise SystemExit("H123 target-local mover compatibility failed")
    capsules, capsule_receipt = _capsules(
        target_member_count=target_member_count
    )
    pair_sha256 = str(capsule_receipt["pair_sha256"])
    order = (
        ["pose_action_map", "pose_only_placebo"]
        if int(pair_sha256[-1], 16) % 2 == 0
        else ["pose_only_placebo", "pose_action_map"]
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    (OUTPUT_DIR / "manifest.json").write_text(json.dumps({
        "schema": "ztare-h123-pose-action-mediator-manifest-v1",
        "order": order,
        "capsule_receipt": capsule_receipt,
        "target_grid_carrier_sha256": TARGET_GRID_CARRIER_SHA256,
        "target_matching_mover_count": target_member_count,
        "capsules": capsules,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rows = []
    for order_index, label in enumerate(order):
        rows.append(_run_arm(
            label=label,
            capsule=capsules[label],
            capsule_receipt=capsule_receipt,
            order_index=order_index,
            treatment_carrier=treatment_carrier,
        ))
    by_label = {row["label"]: row for row in rows}
    causal = by_label["pose_action_map"]["levels_gained"]
    placebo = by_label["pose_only_placebo"]["levels_gained"]
    disposition = {
        (1, 0): "supported_single_pair",
        (0, 0): "map_insufficient",
        (1, 1): "content_not_isolated",
        (0, 1): "inverted_refuted",
    }.get((causal, placebo), "invalid_unexpected_level_count")
    output = {
        "schema": "ztare-h123-pose-action-mediator-surgery-v1",
        "hypothesis_id": (
            "H-GPSA-POSE-ACTION-MEDIATOR-SURGERY-20260808-123"
        ),
        "status": "complete",
        "disposition": disposition,
        "environment_contact": False,
        "controller_contact": True,
        "identities": {
            "h122_result_sha256": _sha256(H122_RESULT),
            "target_grid_carrier_sha256": TARGET_GRID_CARRIER_SHA256,
            "target_matching_mover_count": target_member_count,
        },
        "capsule_receipt": capsule_receipt,
        "arm_order": order,
        "arms": by_label,
        "claim_boundary": (
            "One exact-byte within-game cross-level mediation pair. No "
            "population, cross-game, multi-generation, broad-capability, or "
            "literature-novelty conclusion follows."
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
