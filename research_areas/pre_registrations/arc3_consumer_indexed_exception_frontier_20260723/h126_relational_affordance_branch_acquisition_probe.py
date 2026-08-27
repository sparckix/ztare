#!/usr/bin/env python3
from __future__ import annotations

import argparse
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

from h121_cold_level2_fast_state_counterfactual_probe import (  # noqa: E402
    _LocalArcade,
    _load_game_module,
)


DIRECTORY = Path(__file__).resolve().parent
H119_REPORT = DIRECTORY / "h119_tu93_persistent_sol_max_report.json"
H125_RESULT = (
    DIRECTORY / "h125_palette_quotiented_pose_motion_affordance_result.json"
)
OUTPUT_DIR = DIRECTORY / "h126_relational_affordance_branch_acquisition"
RESULT = DIRECTORY / "h126_relational_affordance_branch_acquisition_result.json"
H125_SHA256 = (
    "bf2dfe105aa9bad163cacaf47c45ca87310abe65e59ec17d804cb3e77cd077f1"
)
BRANCH_GRID_CARRIER_SHA256 = (
    "ca4abcef3c6f6861cffda7087786b546a7d5cdfaf4c0e2723d342e4c3d7cd9a5"
)
RESTORED_PREFIX = (0, 3, 3)
REMAINING_BUDGET = 7
REPLICATION_COUNT = 3
LABELS = ("relational_affordance", "relation_withheld_control")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _canonical_object(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return a recursively key-ordered object matching actor serialization."""

    return json.loads(json.dumps(
        dict(value),
        sort_keys=True,
        separators=(",", ":"),
    ))


def _rendered_capsule(capsule: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(capsule),
        separators=(",", ":"),
    ).encode("utf-8")


def _grid(observation: Mapping[str, Any]) -> tuple[tuple[int, ...], ...]:
    grid = []
    for encoded in observation["grid_rle_rows"]:
        row = []
        for run in encoded.split(","):
            value, count = (int(part) for part in run.split("x"))
            row.extend([value] * count)
        grid.append(tuple(row))
    return tuple(grid)


def _grid_carrier(observation: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "grid_shape": list(observation["grid_shape"]),
        "grid_rle_rows": list(observation["grid_rle_rows"]),
    }


def _capsules() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    common = {
        "schema": "ztare-arc3-relational-affordance-recall-v1",
        "source_result_sha256": H125_SHA256,
        "source_game": "tu93-0768757b",
        "source_epoch": 0,
        "target_state": {
            "grid_carrier_sha256": BRANCH_GRID_CARRIER_SHA256,
            "restored_primitive_action_cost": len(RESTORED_PREFIX),
            "remaining_action_budget": REMAINING_BUDGET,
        },
        "shared_evidence": {
            "action_by_direction": {
                "up": 0,
                "down": 1,
                "left": 2,
                "right": 3,
            },
            "controlled_token": {
                "kind": "palette_quotiented_oriented_token_v1",
                "count": 1,
            },
            "distinct_entity": {
                "kind": "palette_quotiented_oriented_token_v1",
                "count": 1,
                "observed_marker_bearing": "left",
            },
            "branch_candidates": [
                {
                    "name": "direct",
                    "first_direction": "right",
                    "graph_distance_to_goal": 5,
                },
                {
                    "name": "lower",
                    "first_direction": "down",
                    "graph_distance_to_goal": 7,
                },
            ],
            "goal_role": "source_derived_uniform_region",
        },
        "intervention": {},
        "active_uncertainties": [
            "The target entity dynamics and contact outcome have not been observed in this epoch."
        ],
        "guard": (
            "Use the branch judgment only at the bound grid carrier with one "
            "controlled token, one distinct oriented entity, the stated "
            "action namespace, and both route candidates."
        ),
        "refusal": (
            "Do not import source coordinates, a target contact outcome, or "
            "an exact future action sequence. Re-evaluate after each observed "
            "target transition."
        ),
        "padding": "",
    }
    treatment = {
        **common,
        "intervention": {
            "arm_kind": "compiled_relation_available",
            "relation": {
                "kind": "palette_quotiented_pose_motion_relation_v1",
                "status": "supported_source_transport_candidate",
                "support_count": 21,
                "mismatch_count": 0,
                "claim": "marker bearing predicts motion bearing",
                "transported_motion_bearing": "left",
            },
            "branch_judgment": {
                "direct_contact": "closing_head_on",
                "lower_contact": "transverse",
                "selected_direction": "down",
                "selected_action": 1,
                "reason": (
                    "preserve the budget-feasible nonclosing route while the "
                    "target outcome remains uncertain"
                ),
            },
        },
    }
    control = {
        **common,
        "intervention": {
            "arm_kind": "compiled_relation_withheld",
            "relation": {
                "kind": "palette_quotiented_pose_motion_relation_v1",
                "status": "withheld_control",
                "support_count": None,
                "mismatch_count": None,
                "claim": "marker-to-motion relation unresolved",
                "transported_motion_bearing": None,
            },
            "branch_judgment": {
                "direct_contact": "unknown",
                "lower_contact": "unknown",
                "selected_direction": None,
                "selected_action": None,
                "reason": (
                    "relative exposure remains unscored while the target "
                    "outcome and marker-to-motion relation are uncertain"
                ),
            },
        },
    }
    treatment = _canonical_object(treatment)
    control = _canonical_object(control)
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
    treatment = _canonical_object(treatment)
    control = _canonical_object(control)
    treatment_bytes = _rendered_capsule(treatment)
    control_bytes = _rendered_capsule(control)
    if len(treatment_bytes) != len(control_bytes):
        raise RuntimeError("H126 capsule rendering is not exact-byte matched")
    capsules = {
        "relational_affordance": treatment,
        "relation_withheld_control": control,
    }
    receipt = {
        "rendered_prompt_bytes": len(treatment_bytes),
        "relational_affordance_sha256": hashlib.sha256(
            treatment_bytes
        ).hexdigest(),
        "relation_withheld_control_sha256": hashlib.sha256(
            control_bytes
        ).hexdigest(),
        "pair_sha256": hashlib.sha256(
            treatment_bytes + b"\x00" + control_bytes
        ).hexdigest(),
        "shared_payload_equal": all(
            treatment[key] == control[key]
            for key in treatment
            if key not in {"intervention", "padding"}
        ),
        "difference_roots": ["intervention", "padding"],
    }
    if not receipt["shared_payload_equal"]:
        raise RuntimeError("H126 shared capsule payload drifted")
    return capsules, receipt


def _orders(pair_sha256: str) -> dict[str, list[str]]:
    base_treatment_first = int(pair_sha256[-1], 16) % 2 == 0
    rows = {}
    for replication in range(1, REPLICATION_COUNT + 1):
        treatment_first = (
            base_treatment_first
            if replication % 2 == 1
            else not base_treatment_first
        )
        rows[str(replication)] = (
            ["relational_affordance", "relation_withheld_control"]
            if treatment_first
            else ["relation_withheld_control", "relational_affordance"]
        )
    return rows


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _attempt_paths(stem: str, attempt_index: int) -> tuple[Path, Path]:
    suffix = "" if attempt_index == 0 else f"_retry_{attempt_index:02d}"
    return (
        OUTPUT_DIR / f"{stem}{suffix}_trace.jsonl",
        OUTPUT_DIR / f"{stem}{suffix}_report.json",
    )


def _allocate_attempt(stem: str) -> tuple[Path, Path, list[dict[str, Any]]]:
    """Preserve failed pre-action transports and allocate the next attempt."""

    failures = []
    attempt_index = 0
    while True:
        trace_path, report_path = _attempt_paths(stem, attempt_index)
        if not trace_path.exists() and not report_path.exists():
            return trace_path, report_path, failures
        if report_path.exists() or not trace_path.exists():
            raise RuntimeError(f"H126 completed or malformed arm exists: {stem}")
        rows = _read_jsonl(trace_path)
        exchanges = [
            row
            for row in rows
            if row.get("schema") == "ztare-codex-subscription-exchange-v1"
        ]
        checkpoints = [
            row
            for row in rows
            if row.get("schema") == "ztare-arc3-probe-turn-checkpoint-v1"
        ]
        finals = [
            row
            for row in rows
            if row.get("schema") == "ztare-arc3-probe-final-result-v1"
        ]
        if (
            len(exchanges) != 1
            or int(exchanges[0].get("returncode") or 0) == 0
            or checkpoints
            or finals
            or exchanges[0].get("final_session_state")
        ):
            raise RuntimeError(
                f"H126 existing attempt is not an excludable pre-action "
                f"transport failure: {trace_path.name}"
            )
        failures.append({
            "attempt_index": attempt_index,
            "trace_path": _relative(trace_path),
            "returncode": int(exchanges[0]["returncode"]),
            "stdout_tail": str(exchanges[0].get("stdout") or "")[-500:],
            "stderr_tail": str(exchanges[0].get("stderr") or "")[-500:],
            "checkpoint_count": 0,
            "final_session_state": {},
        })
        attempt_index += 1


def _manifest_payload() -> dict[str, Any]:
    if _sha256(H125_RESULT) != H125_SHA256:
        raise RuntimeError("frozen H125 result identity drifted")
    h119 = json.loads(H119_REPORT.read_text(encoding="utf-8"))
    branch_carrier = _grid_carrier(h119["observations"][25])
    if _canonical_sha256(branch_carrier) != BRANCH_GRID_CARRIER_SHA256:
        raise RuntimeError("frozen H126 branch carrier identity drifted")
    capsules, receipt = _capsules()
    return {
        "schema": "ztare-h126-relational-affordance-manifest-v1",
        "hypothesis_id": (
            "H-GPSA-RELATIONAL-AFFORDANCE-BRANCH-ACQUISITION-20260808-126"
        ),
        "replication_count": REPLICATION_COUNT,
        "restored_prefix_actions": list(RESTORED_PREFIX),
        "remaining_budget": REMAINING_BUDGET,
        "branch_grid_carrier_sha256": BRANCH_GRID_CARRIER_SHA256,
        "h125_result_sha256": H125_SHA256,
        "capsule_receipt": receipt,
        "orders": _orders(str(receipt["pair_sha256"])),
        "capsules": capsules,
    }


def _prepare_manifest() -> dict[str, Any]:
    payload = _manifest_payload()
    manifest_path = OUTPUT_DIR / "manifest.json"
    if OUTPUT_DIR.exists():
        if not manifest_path.exists():
            raise RuntimeError("H126 output directory lacks a manifest")
        stored = json.loads(manifest_path.read_text(encoding="utf-8"))
        if stored != payload:
            raise RuntimeError("H126 frozen manifest drifted")
        return stored
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    manifest_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def _run_arm(
    *,
    replication: int,
    label: str,
    capsule: Mapping[str, Any],
    capsule_receipt: Mapping[str, Any],
    order_index: int,
) -> dict[str, Any]:
    stem = f"replication_{replication}_{label}"
    trace_path, report_path, prior_transport_failures = _allocate_attempt(stem)
    attempt_index = len(prior_transport_failures)
    adapter = ArcAgi3Adapter(
        "tu93-0768757b",
        arcade=_LocalArcade(_load_game_module()),
    )

    def trace_event(event: Mapping[str, Any]) -> None:
        _append_trace_event(trace_path, event)

    def observe_turn(turn: Mapping[str, Any]) -> None:
        _emit_turn_progress(turn)
        trace_event({
            "schema": "ztare-arc3-probe-turn-checkpoint-v1",
            "hypothesis": "H126",
            "replication": replication,
            "arm": label,
            "turn": dict(turn),
        })

    trace_event({
        "schema": "ztare-arc3-probe-run-manifest-v1",
        "hypothesis": "H126",
        "replication": replication,
        "arm": label,
        "order_index": order_index,
        "attempt_index": attempt_index,
        "restored_prefix_actions": list(RESTORED_PREFIX),
        "budget": REMAINING_BUDGET,
        "model": "gpt-5.6-sol",
        "reasoning_effort": "max",
        "start_level": 2,
        "capsule_pair_receipt": dict(capsule_receipt),
    })
    payload = run_subscription_probe(
        adapter=adapter,
        game_id="tu93-0768757b",
        budget=REMAINING_BUDGET,
        model_id="gpt-5.6-sol",
        reasoning_effort="max",
        timeout_seconds=300,
        resume_session=True,
        turn_observer=observe_turn,
        exchange_observer=trace_event,
        level_boundary_sleep_top_k=0,
        initial_recall_digest=capsule,
        restored_prefix_actions=RESTORED_PREFIX,
    )
    branch_carrier = _grid_carrier(payload["observations"][0])
    if _canonical_sha256(branch_carrier) != BRANCH_GRID_CARRIER_SHA256:
        raise RuntimeError(f"H126 {stem} branch-grid carrier drifted")
    if payload["restored_prefix"]["actions"] != list(RESTORED_PREFIX):
        raise RuntimeError(f"H126 {stem} restored prefix drifted")
    injected_turns = [
        index
        for index, turn in enumerate(payload["turns"])
        if turn.get("recall_injection") is not None
    ]
    if injected_turns != [0]:
        raise RuntimeError(f"H126 {stem} recall was not exactly one-shot")
    report_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    trace_event({
        "schema": "ztare-arc3-probe-final-result-v1",
        "hypothesis": "H126",
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
        "total_actions_executed": int(payload["total_actions_executed"]),
        "action_sequence": actions,
        "first_action": actions[0] if actions else None,
        "branch_acquired": bool(actions and actions[0] == 1),
        "oracle_suffix_exact": actions == [1, 3, 3, 0, 3, 3, 0],
        "session_ids": sorted({
            str(turn["session_id"]) for turn in payload["turns"]
        }),
        "one_shot_recall": injected_turns == [0],
        "attempt_index": attempt_index,
        "prior_transport_failures": prior_transport_failures,
        "report_path": _relative(report_path),
        "trace_path": _relative(trace_path),
    }


def _disposition(
    *,
    treatment_acquisitions: int,
    control_acquisitions: int,
    treatment_completions: int,
    control_completions: int,
) -> str:
    task_supported = (
        treatment_completions >= 2
        and treatment_completions - control_completions >= 2
    )
    acquisition_supported = (
        treatment_acquisitions >= 2
        and treatment_acquisitions - control_acquisitions >= 2
    )
    if task_supported:
        return "supported_task_effect"
    if acquisition_supported:
        return "supported_acquisition_only"
    if (
        treatment_acquisitions <= control_acquisitions
        and treatment_completions <= control_completions
    ):
        return "refuted"
    return "inconclusive"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if RESULT.exists():
        raise SystemExit("H126 result output must be new")
    manifest = _prepare_manifest()
    if args.prepare_only:
        print(json.dumps({
            "status": "prepared_no_controller_contact",
            "manifest_path": _relative(OUTPUT_DIR / "manifest.json"),
            "capsule_receipt": manifest["capsule_receipt"],
            "orders": manifest["orders"],
        }, indent=2, sort_keys=True))
        return 0

    pairs = []
    seen_sessions: set[str] = set()
    for replication in range(1, REPLICATION_COUNT + 1):
        rows = []
        for order_index, label in enumerate(
            manifest["orders"][str(replication)]
        ):
            row = _run_arm(
                replication=replication,
                label=label,
                capsule=manifest["capsules"][label],
                capsule_receipt=manifest["capsule_receipt"],
                order_index=order_index,
            )
            arm_sessions = set(row["session_ids"])
            if len(arm_sessions) != 1 or seen_sessions & arm_sessions:
                raise RuntimeError("H126 session identity crossed an arm")
            seen_sessions |= arm_sessions
            rows.append(row)
        by_label = {row["label"]: row for row in rows}
        treatment = by_label["relational_affordance"]
        control = by_label["relation_withheld_control"]
        pairs.append({
            "replication": replication,
            "order": manifest["orders"][str(replication)],
            "branch_pair_outcome": (
                "treatment_win"
                if treatment["branch_acquired"] > control["branch_acquired"]
                else "control_win"
                if control["branch_acquired"] > treatment["branch_acquired"]
                else "tie"
            ),
            "task_pair_outcome": (
                "treatment_win"
                if treatment["levels_gained"] > control["levels_gained"]
                else "control_win"
                if control["levels_gained"] > treatment["levels_gained"]
                else "tie"
            ),
            "arms": by_label,
        })
    treatment_acquisitions = sum(
        pair["arms"]["relational_affordance"]["branch_acquired"]
        for pair in pairs
    )
    control_acquisitions = sum(
        pair["arms"]["relation_withheld_control"]["branch_acquired"]
        for pair in pairs
    )
    treatment_completions = sum(
        pair["arms"]["relational_affordance"]["levels_gained"] > 0
        for pair in pairs
    )
    control_completions = sum(
        pair["arms"]["relation_withheld_control"]["levels_gained"] > 0
        for pair in pairs
    )
    output = {
        "schema": "ztare-h126-relational-affordance-branch-acquisition-v1",
        "hypothesis_id": manifest["hypothesis_id"],
        "status": "complete",
        "disposition": _disposition(
            treatment_acquisitions=treatment_acquisitions,
            control_acquisitions=control_acquisitions,
            treatment_completions=treatment_completions,
            control_completions=control_completions,
        ),
        "environment_contact": False,
        "controller_contact": True,
        "identities": {
            "h125_result_sha256": _sha256(H125_RESULT),
            "branch_grid_carrier_sha256": BRANCH_GRID_CARRIER_SHA256,
            "restored_prefix_actions": list(RESTORED_PREFIX),
            "remaining_budget": REMAINING_BUDGET,
        },
        "capsule_receipt": manifest["capsule_receipt"],
        "replication_count": REPLICATION_COUNT,
        "treatment_acquisitions": treatment_acquisitions,
        "control_acquisitions": control_acquisitions,
        "acquisition_difference": (
            treatment_acquisitions - control_acquisitions
        ),
        "treatment_completions": treatment_completions,
        "control_completions": control_completions,
        "completion_difference": (
            treatment_completions - control_completions
        ),
        "pairs": pairs,
        "claim_boundary": (
            "Three repeated exact-byte within-game restored-branch pairs. "
            "Cross-game transfer, autonomous target-consequence discovery, "
            "multi-generation compounding, broad capability, population, "
            "and literature novelty remain unsettled."
        ),
    }
    RESULT.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        key: output[key]
        for key in (
            "status",
            "disposition",
            "treatment_acquisitions",
            "control_acquisitions",
            "acquisition_difference",
            "treatment_completions",
            "control_completions",
            "completion_difference",
        )
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
