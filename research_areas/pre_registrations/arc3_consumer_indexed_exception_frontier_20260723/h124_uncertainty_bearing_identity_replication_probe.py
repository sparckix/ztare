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
H123_RESULT = DIRECTORY / "h123_pose_action_mediator_surgery_result.json"
H123_AUDIT = DIRECTORY / "h123_pose_action_mediator_surgery_audit_result.json"
OUTPUT_DIR = DIRECTORY / "h124_uncertainty_bearing_identity_replication"
RESULT = DIRECTORY / "h124_uncertainty_bearing_identity_replication_result.json"
H122_SHA256 = (
    "60dbf8f66377625a28f08a1252c07f11f99f17673848cd16dab535ae712f0dd7"
)
H123_SHA256 = (
    "2ceb8612a292aa66af7a7c7a5a0c07d608fda8936764ce1a07cc8f5497d4c966"
)
H123_AUDIT_SHA256 = (
    "e9a681df3d1aae8bf34d14f5427525bece3081d4199f218e3d8bacb6d629bf33"
)
TARGET_GRID_CARRIER_SHA256 = (
    "dde09802332964a1530f9c3b3509a3732aec0d69325f2d3af29cca5162c06b24"
)
REPLICATION_COUNT = 3


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
        "schema": "ztare-arc3-causal-memory-candidate-v1",
        "selected_from_result_sha256": H123_SHA256,
        "source_mechanism_sha256": H122_SHA256,
        "source_game": "tu93-0768757b",
        "source_epoch": 0,
        "target_grid_carrier_sha256": TARGET_GRID_CARRIER_SHA256,
        "memories": [],
        "active_uncertainties": [],
        "next_decision_questions": [],
        "padding": "",
    }
    treatment = {
        **common,
        "target_compatibility": {
            "identity_relation": "d4_pose_v1",
            "matching_mover_count": target_member_count,
            "action_namespace": [0, 1, 2, 3],
            "status": "witnessed",
        },
        "memories": [{
            "memory_id": "h124_uncertainty_bearing_identity",
            "claim": (
                "The D4 orbit identifies the controlled 3x3 color-9 "
                "component with one color-4 pose marker. Four stable action "
                "indices moved it in the source episode; their direction "
                "assignment remains unknown here and must be inferred "
                "locally."
            ),
            "support": {
                "source_transition_count": 21,
                "observed_pose_count": 4,
                "distinct_action_count": 4,
            },
            "guard": (
                "Treat the recalled role as a candidate only when exactly "
                "one D4-matching component is visible; verify its response."
            ),
            "refusal": (
                "Do not import an action-direction map, source coordinates, "
                "route, obstacle behavior, hazard rule, or target actions."
            ),
        }],
        "active_uncertainties": [
            "Verify the candidate mover; action directions, route, obstacle effects, and hazard rules remain unknown."
        ],
        "next_decision_questions": [
            "Which discriminating local action verifies direction while preserving viable routes?"
        ],
    }
    control = {
        **common,
        "target_compatibility": {
            "identity_relation": "withheld_control",
            "matching_mover_count": None,
            "action_namespace": [0, 1, 2, 3],
            "status": "unsettled",
        },
        "memories": [{
            "memory_id": "h124_neutral_uncertainty_control",
            "claim": (
                "The source episode contained colored components and four "
                "stable action indices. No source-to-target object-role "
                "match or direction assignment is supplied; identify the "
                "controlled component and action meanings locally."
            ),
            "support": {
                "source_transition_count": 21,
                "observed_component_classes": 4,
                "distinct_action_count": 4,
            },
            "guard": (
                "This control carries no object-role compatibility claim; "
                "verify every candidate role from target-local response."
            ),
            "refusal": (
                "Do not import an object identity, action-direction map, "
                "source coordinates, route, hazard rule, or target actions."
            ),
        }],
        "active_uncertainties": [
            "Identify the mover; action directions, route, obstacle effects, and hazard rules remain unknown."
        ],
        "next_decision_questions": [
            "Which discriminating local action identifies the mover and direction while preserving viable routes?"
        ],
    }
    treatment_bytes = _rendered_capsule(treatment)
    control_bytes = _rendered_capsule(control)
    if len(treatment_bytes) < len(control_bytes):
        treatment["padding"] = " " * (
            len(control_bytes) - len(treatment_bytes)
        )
    elif len(control_bytes) < len(treatment_bytes):
        control["padding"] = " " * (
            len(treatment_bytes) - len(control_bytes)
        )
    treatment_bytes = _rendered_capsule(treatment)
    control_bytes = _rendered_capsule(control)
    if len(treatment_bytes) != len(control_bytes):
        raise RuntimeError("H124 capsule rendering is not exact-byte matched")
    return {
        "uncertainty_bearing_identity": treatment,
        "neutral_uncertainty_control": control,
    }, {
        "rendered_prompt_bytes": len(treatment_bytes),
        "uncertainty_bearing_identity_sha256": hashlib.sha256(
            treatment_bytes
        ).hexdigest(),
        "neutral_uncertainty_control_sha256": hashlib.sha256(
            control_bytes
        ).hexdigest(),
        "pair_sha256": hashlib.sha256(
            treatment_bytes + b"\x00" + control_bytes
        ).hexdigest(),
    }


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def _run_arm(
    *,
    replication: int,
    label: str,
    capsule: Mapping[str, Any],
    capsule_receipt: Mapping[str, Any],
    order_index: int,
    treatment_carrier,
):
    stem = f"replication_{replication}_{label}"
    trace_path = OUTPUT_DIR / f"{stem}_trace.jsonl"
    report_path = OUTPUT_DIR / f"{stem}_report.json"
    if trace_path.exists() or report_path.exists():
        raise RuntimeError(f"H124 arm output already exists: {stem}")
    adapter = ArcAgi3Adapter(
        "tu93-0768757b",
        # Local dynamics mutate module-level level objects. Reloading the
        # module here makes the environment lifecycle part of each arm.
        arcade=_LocalArcade(_load_game_module()),
    )

    def trace_event(event: Mapping[str, Any]) -> None:
        _append_trace_event(trace_path, event)

    def observe_turn(turn: Mapping[str, Any]) -> None:
        _emit_turn_progress(turn)
        trace_event({
            "schema": "ztare-arc3-probe-turn-checkpoint-v1",
            "hypothesis": "H124",
            "replication": replication,
            "arm": label,
            "turn": dict(turn),
        })

    trace_event({
        "schema": "ztare-arc3-probe-run-manifest-v1",
        "hypothesis": "H124",
        "replication": replication,
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
        raise RuntimeError(f"H124 {stem} start-grid carrier drifted")
    injected_turns = [
        index
        for index, turn in enumerate(payload["turns"])
        if turn.get("recall_injection") is not None
    ]
    if injected_turns != [0]:
        raise RuntimeError(f"H124 {stem} recall was not exactly one-shot")
    report_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    trace_event({
        "schema": "ztare-arc3-probe-final-result-v1",
        "hypothesis": "H124",
        "replication": replication,
        "arm": label,
        "result": payload,
        "report_path": _relative(report_path),
    })
    actions = [int(turn["action"]) for turn in payload["turns"]]
    return {
        "replication": replication,
        "label": label,
        "status": payload["status"],
        "levels_gained": int(payload["levels_gained"]),
        "first_level_action": payload["first_level_action"],
        "actions_executed": int(payload["actions_executed"]),
        "action_sequence": actions,
        "first_action": actions[0] if actions else None,
        "lower_branch_by_action_4": len(actions) >= 4 and actions[:4] == [
            0, 3, 3, 1
        ],
        "session_ids": sorted({
            str(turn["session_id"]) for turn in payload["turns"]
        }),
        "one_shot_recall": injected_turns == [0],
        "report_path": _relative(report_path),
        "trace_path": _relative(trace_path),
    }


def main() -> int:
    if RESULT.exists() or OUTPUT_DIR.exists():
        raise SystemExit("H124 outputs must be new")
    for path, expected in (
        (H122_RESULT, H122_SHA256),
        (H123_RESULT, H123_SHA256),
        (H123_AUDIT, H123_AUDIT_SHA256),
    ):
        if _sha256(path) != expected:
            raise SystemExit(f"frozen evidence identity drifted: {path.name}")
    h119 = json.loads(H119_REPORT.read_text(encoding="utf-8"))
    target_observation = h119["observations"][22]
    treatment_carrier = _grid_carrier(target_observation)
    if _canonical_sha256(treatment_carrier) != TARGET_GRID_CARRIER_SHA256:
        raise SystemExit("H124 target grid-carrier identity drifted")
    roles = _source_roles(h119)
    target_agent, _resource, _reactive = object_signature(
        _grid(target_observation), roles
    )
    target_member_count = len(target_agent)
    if target_member_count != 1:
        raise SystemExit("H124 target-local mover compatibility failed")
    capsules, capsule_receipt = _capsules(
        target_member_count=target_member_count
    )
    pair_sha256 = str(capsule_receipt["pair_sha256"])
    orders = {}
    base_treatment_first = int(pair_sha256[-1], 16) % 2 == 0
    for replication in range(1, REPLICATION_COUNT + 1):
        treatment_first = (
            base_treatment_first
            if replication % 2 == 1
            else not base_treatment_first
        )
        orders[str(replication)] = (
            ["uncertainty_bearing_identity", "neutral_uncertainty_control"]
            if treatment_first
            else ["neutral_uncertainty_control", "uncertainty_bearing_identity"]
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps({
            "schema": "ztare-h124-uncertainty-bearing-identity-manifest-v1",
            "replication_count": REPLICATION_COUNT,
            "orders": orders,
            "capsule_receipt": capsule_receipt,
            "target_grid_carrier_sha256": TARGET_GRID_CARRIER_SHA256,
            "target_matching_mover_count": target_member_count,
            "capsules": capsules,
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    pairs = []
    seen_sessions: set[str] = set()
    for replication in range(1, REPLICATION_COUNT + 1):
        rows = []
        for order_index, label in enumerate(orders[str(replication)]):
            row = _run_arm(
                replication=replication,
                label=label,
                capsule=capsules[label],
                capsule_receipt=capsule_receipt,
                order_index=order_index,
                treatment_carrier=treatment_carrier,
            )
            arm_sessions = set(row["session_ids"])
            if len(arm_sessions) != 1 or seen_sessions & arm_sessions:
                raise RuntimeError("H124 session identity crossed an arm")
            seen_sessions |= arm_sessions
            rows.append(row)
        by_label = {row["label"]: row for row in rows}
        treatment = by_label["uncertainty_bearing_identity"]["levels_gained"]
        control = by_label["neutral_uncertainty_control"]["levels_gained"]
        pairs.append({
            "replication": replication,
            "order": orders[str(replication)],
            "pair_outcome": (
                "treatment_win" if treatment > control
                else "control_win" if control > treatment
                else "tie"
            ),
            "arms": by_label,
        })
    treatment_completions = sum(
        pair["arms"]["uncertainty_bearing_identity"]["levels_gained"] > 0
        for pair in pairs
    )
    control_completions = sum(
        pair["arms"]["neutral_uncertainty_control"]["levels_gained"] > 0
        for pair in pairs
    )
    if treatment_completions >= 2 and (
        treatment_completions - control_completions >= 2
    ):
        disposition = "supported_repeated_within_game"
    elif control_completions >= treatment_completions:
        disposition = "refuted"
    else:
        disposition = "inconclusive"
    output = {
        "schema": "ztare-h124-uncertainty-bearing-identity-replication-v1",
        "hypothesis_id": (
            "H-GPSA-UNCERTAINTY-BEARING-IDENTITY-REPLICATION-20260808-124"
        ),
        "status": "complete",
        "disposition": disposition,
        "environment_contact": False,
        "controller_contact": True,
        "identities": {
            "h122_result_sha256": _sha256(H122_RESULT),
            "h123_result_sha256": _sha256(H123_RESULT),
            "h123_audit_sha256": _sha256(H123_AUDIT),
            "target_grid_carrier_sha256": TARGET_GRID_CARRIER_SHA256,
            "target_matching_mover_count": target_member_count,
        },
        "capsule_receipt": capsule_receipt,
        "replication_count": REPLICATION_COUNT,
        "treatment_completions": treatment_completions,
        "control_completions": control_completions,
        "completion_difference": (
            treatment_completions - control_completions
        ),
        "pairs": pairs,
        "claim_boundary": (
            "Three repeated exact-byte within-game cross-level pairs. No "
            "cross-game, multi-generation, broad-capability, population, or "
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
