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

import h124_uncertainty_bearing_identity_replication_probe as h124  # noqa: E402
from h121_cold_level2_fast_state_counterfactual_probe import (  # noqa: E402
    _LocalArcade,
    _load_game_module,
)
from ztare.substrates.arc_agi3 import ArcAgi3Adapter  # noqa: E402


OUTPUT = DIRECTORY / "h124_uncertainty_bearing_identity_replication_audit_result.json"
VALID_REPLICATIONS = (1, 2, 5)
LABELS = (
    "uncertainty_bearing_identity",
    "neutral_uncertainty_control",
)
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
    terminal_actions = []
    for index, action in enumerate(actions, start=1):
        grids.append(adapter.reset() if action == -1 else adapter.step(action))
        identity = adapter.last_transition_identity
        boundary = identity.boundary_kind if identity is not None else None
        if boundary == "level_completed" or str(boundary).startswith(
            "terminal_state:"
        ):
            terminal_actions.append({
                "action_count": index,
                "boundary_kind": boundary,
            })
    expected_grids = [h124._grid(row) for row in report["observations"]]
    return {
        "all_observations_match": grids == expected_grids,
        "final_levels_completed": adapter.levels_completed,
        "terminal_actions": terminal_actions,
    }


def _audit_arm(
    replication: int,
    label: str,
    capsules: dict[str, Any],
) -> dict[str, Any]:
    stem = f"replication_{replication}_{label}"
    report_path = h124.OUTPUT_DIR / f"{stem}_report.json"
    trace_path = h124.OUTPUT_DIR / f"{stem}_trace.jsonl"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    trace = _read_jsonl(trace_path)
    counts = Counter(str(row.get("schema")) for row in trace)
    exchanges = [
        row
        for row in trace
        if row.get("schema") == "ztare-codex-subscription-exchange-v1"
    ]
    decoded = [json.loads(row["stdout"]) for row in exchanges]
    actions = [int(row["action"]) for row in report["turns"]]
    capsule_text = h124._rendered_capsule(capsules[label]).decode("utf-8")
    capsule_prompt_turns = [
        int(row["turn_index"])
        for row in exchanges
        if capsule_text in str(row["prompt"])
    ]
    return {
        "replication": replication,
        "label": label,
        "report_sha256": _sha256(report_path),
        "trace_sha256": _sha256(trace_path),
        "schema_counts_match": dict(counts) == EXPECTED_SCHEMAS,
        "exchange_returncodes_zero": all(
            int(row["returncode"]) == 0 for row in exchanges
        ),
        "exchange_actions_match": [
            int(row["action"]) for row in decoded
        ] == actions,
        "capsule_prompt_turns": capsule_prompt_turns,
        "capsule_is_one_shot": capsule_prompt_turns == [0],
        "session_ids": sorted({
            str(row["session_id"]) for row in report["turns"]
        }),
        "action_sequence": actions,
        "direct_head_on_prefix": actions[:4] == [0, 3, 3, 3],
        "levels_gained": int(report["levels_gained"]),
        "first_prediction": str(decoded[0]["prediction"]),
        "replay": _replay(actions, report),
    }


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("H124 audit output must be new")
    result = json.loads(h124.RESULT.read_text(encoding="utf-8"))
    manifest = json.loads(
        (h124.OUTPUT_DIR / "manifest.json").read_text(encoding="utf-8")
    )
    stored_capsules = manifest["capsules"]
    rebuilt_capsules, rebuilt_receipt = h124._capsules(
        target_member_count=int(manifest["target_matching_mover_count"])
    )
    if stored_capsules != rebuilt_capsules:
        raise SystemExit("H124 capsule bytes drifted")
    if manifest["capsule_receipt"] != rebuilt_receipt:
        raise SystemExit("H124 capsule receipt drifted")
    # JSON object equality ignores insertion order, but the actor prompt used
    # compact insertion-order rendering. Rebuild that exact byte order here.
    capsules = rebuilt_capsules

    arms = [
        _audit_arm(replication, label, capsules)
        for replication in VALID_REPLICATIONS
        for label in LABELS
    ]
    sessions = [
        session
        for row in arms
        for session in row["session_ids"]
    ]
    failed_trace_path = (
        h124.OUTPUT_DIR
        / "replication_3_neutral_uncertainty_control_trace.jsonl"
    )
    failed_trace = _read_jsonl(failed_trace_path)
    failed_exchanges = [
        row
        for row in failed_trace
        if row.get("schema") == "ztare-codex-subscription-exchange-v1"
    ]
    excluded_treatment = _audit_arm(
        3,
        "uncertainty_bearing_identity",
        capsules,
    )
    pair4_actual_prompt_hashes = {}
    for label in LABELS:
        trace = _read_jsonl(
            h124.OUTPUT_DIR / f"replication_4_{label}_trace.jsonl"
        )
        first_prompt = str(next(
            row["prompt"]
            for row in trace
            if row.get("schema") == "ztare-codex-subscription-exchange-v1"
        ))
        canonical_text = h124._rendered_capsule(capsules[label]).decode(
            "utf-8"
        )
        stored_text = h124._rendered_capsule(
            stored_capsules[label]
        ).decode("utf-8")
        if canonical_text in first_prompt or stored_text not in first_prompt:
            raise SystemExit("H124 pair-4 carrier mismatch is not preserved")
        pair4_actual_prompt_hashes[label] = hashlib.sha256(
            stored_text.encode("utf-8")
        ).hexdigest()
    checks_passed = (
        len(sessions) == 6
        and len(set(sessions)) == 6
        and all(len(row["session_ids"]) == 1 for row in arms)
        and all(row["schema_counts_match"] for row in arms)
        and all(row["exchange_returncodes_zero"] for row in arms)
        and all(row["exchange_actions_match"] for row in arms)
        and all(row["capsule_is_one_shot"] for row in arms)
        and all(row["replay"]["all_observations_match"] for row in arms)
        and [int(row["returncode"]) for row in failed_exchanges] == [0, 124]
        and excluded_treatment["replay"]["all_observations_match"]
    )
    if not checks_passed:
        raise SystemExit("H124 audit failed")
    output = {
        "schema": "ztare-h124-uncertainty-bearing-identity-audit-v1",
        "status": "passed",
        "environment_contact": False,
        "controller_contact": False,
        "result_sha256": _sha256(h124.RESULT),
        "capsule_receipt": rebuilt_receipt,
        "valid_replications": list(VALID_REPLICATIONS),
        "valid_arm_count": len(arms),
        "unique_valid_session_count": len(set(sessions)),
        "treatment_completions": sum(
            row["levels_gained"] > 0
            for row in arms
            if row["label"] == "uncertainty_bearing_identity"
        ),
        "control_completions": sum(
            row["levels_gained"] > 0
            for row in arms
            if row["label"] == "neutral_uncertainty_control"
        ),
        "direct_head_on_prefix_count": sum(
            row["direct_head_on_prefix"] for row in arms
        ),
        "arms": arms,
        "excluded_pairs": [
            {
                "replication": 3,
                "reason": "control_transport_timeout_before_endpoint",
                "control_returncodes": [
                    int(row["returncode"]) for row in failed_exchanges
                ],
                "control_checkpoint_count": sum(
                    row.get("schema")
                    == "ztare-arc3-probe-turn-checkpoint-v1"
                    for row in failed_trace
                ),
                "control_final_count": sum(
                    row.get("schema")
                    == "ztare-arc3-probe-final-result-v1"
                    for row in failed_trace
                ),
                "treatment": excluded_treatment,
            },
            {
                "replication": 4,
                "reason": "compact_prompt_key_order_hash_mismatch",
                "actual_prompt_hashes": pair4_actual_prompt_hashes,
                "registered_prompt_hashes": {
                    "uncertainty_bearing_identity": rebuilt_receipt[
                        "uncertainty_bearing_identity_sha256"
                    ],
                    "neutral_uncertainty_control": rebuilt_receipt[
                        "neutral_uncertainty_control_sha256"
                    ],
                },
            },
        ],
        "registered_disposition": result["disposition"],
        "settlement": {
            "disposition": "refuted",
            "information_gain": (
                "The uncertainty-bearing D4 mover identity produced zero "
                "completions in three valid treatment arms, tied three "
                "neutral controls, and did not control the directional "
                "hazard-side decision."
            ),
        },
    }
    OUTPUT.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": output["status"],
        "result_sha256": output["result_sha256"],
        "registered_disposition": output["registered_disposition"],
        "valid_arm_count": output["valid_arm_count"],
        "unique_valid_session_count": output["unique_valid_session_count"],
        "treatment_completions": output["treatment_completions"],
        "control_completions": output["control_completions"],
        "direct_head_on_prefix_count": output[
            "direct_head_on_prefix_count"
        ],
        "excluded_control_returncodes": output[
            "excluded_pairs"
        ][0]["control_returncodes"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
