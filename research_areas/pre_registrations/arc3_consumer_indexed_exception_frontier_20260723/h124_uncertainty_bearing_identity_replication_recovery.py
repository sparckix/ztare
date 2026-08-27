#!/usr/bin/env python3
from __future__ import annotations

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


REPLACEMENT_MANIFEST = h124.OUTPUT_DIR / "replacement_manifest.json"
VALID_REPLICATIONS = (1, 2, 4)
REPLACEMENT_ORDER = (
    "neutral_uncertainty_control",
    "uncertainty_bearing_identity",
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _row_from_report(replication: int, label: str) -> dict[str, Any]:
    stem = f"replication_{replication}_{label}"
    report_path = h124.OUTPUT_DIR / f"{stem}_report.json"
    trace_path = h124.OUTPUT_DIR / f"{stem}_trace.jsonl"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    actions = [int(turn["action"]) for turn in report["turns"]]
    injected_turns = [
        index
        for index, turn in enumerate(report["turns"])
        if turn.get("recall_injection") is not None
    ]
    return {
        "replication": replication,
        "label": label,
        "status": report["status"],
        "levels_gained": int(report["levels_gained"]),
        "first_level_action": report["first_level_action"],
        "actions_executed": int(report["actions_executed"]),
        "action_sequence": actions,
        "first_action": actions[0] if actions else None,
        "lower_branch_by_action_4": len(actions) >= 4 and actions[:4] == [
            0, 3, 3, 1
        ],
        "session_ids": sorted({
            str(turn["session_id"]) for turn in report["turns"]
        }),
        "one_shot_recall": injected_turns == [0],
        "report_path": h124._relative(report_path),
        "trace_path": h124._relative(trace_path),
    }


def _pair(replication: int, order: list[str]) -> dict[str, Any]:
    by_label = {
        label: _row_from_report(replication, label)
        for label in (
            "uncertainty_bearing_identity",
            "neutral_uncertainty_control",
        )
    }
    treatment = by_label["uncertainty_bearing_identity"]["levels_gained"]
    control = by_label["neutral_uncertainty_control"]["levels_gained"]
    return {
        "replication": replication,
        "order": order,
        "pair_outcome": (
            "treatment_win" if treatment > control
            else "control_win" if control > treatment
            else "tie"
        ),
        "arms": by_label,
    }


def main() -> int:
    if h124.RESULT.exists() or REPLACEMENT_MANIFEST.exists():
        raise SystemExit("H124 recovery outputs must be new")
    manifest = json.loads(
        (h124.OUTPUT_DIR / "manifest.json").read_text(encoding="utf-8")
    )
    failed_trace_path = (
        h124.OUTPUT_DIR
        / "replication_3_neutral_uncertainty_control_trace.jsonl"
    )
    failed_report_path = (
        h124.OUTPUT_DIR
        / "replication_3_neutral_uncertainty_control_report.json"
    )
    failed_trace = _read_jsonl(failed_trace_path)
    failed_exchanges = [
        row
        for row in failed_trace
        if row.get("schema") == "ztare-codex-subscription-exchange-v1"
    ]
    if [int(row["returncode"]) for row in failed_exchanges] != [0, 124]:
        raise SystemExit("H124 failed-arm receipt drifted")
    if failed_report_path.exists():
        raise SystemExit("H124 failed arm unexpectedly has a report")
    if not all(
        (
            h124.OUTPUT_DIR
            / f"replication_{replication}_{label}_report.json"
        ).exists()
        for replication in (1, 2)
        for label in (
            "uncertainty_bearing_identity",
            "neutral_uncertainty_control",
        )
    ):
        raise SystemExit("H124 complete pre-failure pairs are missing")
    if not (
        h124.OUTPUT_DIR
        / "replication_3_uncertainty_bearing_identity_report.json"
    ).exists():
        raise SystemExit("H124 excluded treatment evidence is missing")

    h119 = json.loads(h124.H119_REPORT.read_text(encoding="utf-8"))
    target_observation = h119["observations"][22]
    treatment_carrier = h124._grid_carrier(target_observation)
    if h124._canonical_sha256(
        treatment_carrier
    ) != h124.TARGET_GRID_CARRIER_SHA256:
        raise SystemExit("H124 replacement target carrier drifted")
    capsules = manifest["capsules"]
    capsule_receipt = manifest["capsule_receipt"]
    rebuilt_capsules, rebuilt_receipt = h124._capsules(
        target_member_count=int(manifest["target_matching_mover_count"])
    )
    if capsules != rebuilt_capsules or capsule_receipt != rebuilt_receipt:
        raise SystemExit("H124 replacement capsule identity drifted")

    REPLACEMENT_MANIFEST.write_text(
        json.dumps({
            "schema": "ztare-h124-failed-pair-replacement-manifest-v1",
            "excluded_replication": 3,
            "failed_arm": "neutral_uncertainty_control",
            "failed_returncodes": [0, 124],
            "failed_trace_path": h124._relative(failed_trace_path),
            "replacement_replication": 4,
            "replacement_order": list(REPLACEMENT_ORDER),
            "capsule_receipt": capsule_receipt,
            "target_grid_carrier_sha256": h124.TARGET_GRID_CARRIER_SHA256,
            "endpoint_and_thresholds_changed": False,
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    replacement_rows = []
    for order_index, label in enumerate(REPLACEMENT_ORDER):
        replacement_rows.append(h124._run_arm(
            replication=4,
            label=label,
            capsule=capsules[label],
            capsule_receipt=capsule_receipt,
            order_index=order_index,
            treatment_carrier=treatment_carrier,
        ))

    orders = {
        1: list(manifest["orders"]["1"]),
        2: list(manifest["orders"]["2"]),
        4: list(REPLACEMENT_ORDER),
    }
    pairs = [_pair(replication, orders[replication]) for replication in VALID_REPLICATIONS]
    all_sessions = [
        session
        for pair in pairs
        for row in pair["arms"].values()
        for session in row["session_ids"]
    ]
    if len(all_sessions) != 6 or len(set(all_sessions)) != 6:
        raise SystemExit("H124 valid-pair session identities crossed")
    if not all(
        row["one_shot_recall"]
        for pair in pairs
        for row in pair["arms"].values()
    ):
        raise SystemExit("H124 valid-pair recall was not one-shot")

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
            "h122_result_sha256": h124._sha256(h124.H122_RESULT),
            "h123_result_sha256": h124._sha256(h124.H123_RESULT),
            "h123_audit_sha256": h124._sha256(h124.H123_AUDIT),
            "target_grid_carrier_sha256": h124.TARGET_GRID_CARRIER_SHA256,
            "target_matching_mover_count": int(
                manifest["target_matching_mover_count"]
            ),
        },
        "capsule_receipt": capsule_receipt,
        "attempted_replication_count": 4,
        "valid_replication_count": 3,
        "valid_replications": list(VALID_REPLICATIONS),
        "excluded_pair": {
            "replication": 3,
            "reason": "control_transport_timeout_before_endpoint",
            "failed_returncodes": [0, 124],
            "failed_trace_path": h124._relative(failed_trace_path),
            "treatment_report_path": h124._relative(
                h124.OUTPUT_DIR
                / "replication_3_uncertainty_bearing_identity_report.json"
            ),
        },
        "treatment_completions": treatment_completions,
        "control_completions": control_completions,
        "completion_difference": (
            treatment_completions - control_completions
        ),
        "pairs": pairs,
        "claim_boundary": (
            "Three complete exact-byte within-game cross-level pairs after "
            "excluding one transport-failed pair under the registered rule. "
            "No cross-game, multi-generation, broad-capability, population, "
            "or literature-novelty conclusion follows."
        ),
    }
    h124.RESULT.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
