#!/usr/bin/env python3
from __future__ import annotations

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
from h124_uncertainty_bearing_identity_replication_recovery import (  # noqa: E402
    _pair,
    _read_jsonl,
)


SECOND_REPLACEMENT_MANIFEST = (
    h124.OUTPUT_DIR / "second_replacement_manifest.json"
)
VALID_REPLICATIONS = (1, 2, 5)
REPLACEMENT_ORDER = (
    "uncertainty_bearing_identity",
    "neutral_uncertainty_control",
)


def _prompt_render_sha256(trace_path: Path, capsule_texts: list[str]) -> str:
    exchanges = [
        row
        for row in _read_jsonl(trace_path)
        if row.get("schema") == "ztare-codex-subscription-exchange-v1"
    ]
    if not exchanges:
        raise RuntimeError(f"no exchanges in {trace_path.name}")
    prompt = str(exchanges[0]["prompt"])
    matches = [text for text in capsule_texts if text in prompt]
    if len(matches) != 1:
        raise RuntimeError(
            f"could not identify exact recalled bytes in {trace_path.name}"
        )
    return hashlib.sha256(matches[0].encode("utf-8")).hexdigest()


def main() -> int:
    if h124.RESULT.exists() or SECOND_REPLACEMENT_MANIFEST.exists():
        raise SystemExit("H124 second recovery outputs must be new")
    manifest = json.loads(
        (h124.OUTPUT_DIR / "manifest.json").read_text(encoding="utf-8")
    )
    stored_capsules = manifest["capsules"]
    canonical_capsules, canonical_receipt = h124._capsules(
        target_member_count=int(manifest["target_matching_mover_count"])
    )
    if stored_capsules != canonical_capsules:
        raise SystemExit("H124 capsule content drifted")
    if canonical_receipt != manifest["capsule_receipt"]:
        raise SystemExit("H124 frozen capsule receipt drifted")

    actual_pair4_hashes = {}
    for label in REPLACEMENT_ORDER:
        canonical_text = h124._rendered_capsule(
            canonical_capsules[label]
        ).decode("utf-8")
        stored_text = h124._rendered_capsule(
            stored_capsules[label]
        ).decode("utf-8")
        if canonical_text == stored_text:
            raise SystemExit("H124 pair-4 mismatch witness disappeared")
        trace_path = (
            h124.OUTPUT_DIR / f"replication_4_{label}_trace.jsonl"
        )
        actual_pair4_hashes[label] = _prompt_render_sha256(
            trace_path,
            [canonical_text, stored_text],
        )
        expected_stored_hash = hashlib.sha256(
            stored_text.encode("utf-8")
        ).hexdigest()
        if actual_pair4_hashes[label] != expected_stored_hash:
            raise SystemExit("H124 pair-4 mismatch witness drifted")

    failed_trace_path = (
        h124.OUTPUT_DIR
        / "replication_3_neutral_uncertainty_control_trace.jsonl"
    )
    failed_exchanges = [
        row
        for row in _read_jsonl(failed_trace_path)
        if row.get("schema") == "ztare-codex-subscription-exchange-v1"
    ]
    if [int(row["returncode"]) for row in failed_exchanges] != [0, 124]:
        raise SystemExit("H124 pair-3 failure receipt drifted")

    h119 = json.loads(h124.H119_REPORT.read_text(encoding="utf-8"))
    target_observation = h119["observations"][22]
    treatment_carrier = h124._grid_carrier(target_observation)
    if h124._canonical_sha256(
        treatment_carrier
    ) != h124.TARGET_GRID_CARRIER_SHA256:
        raise SystemExit("H124 second replacement target carrier drifted")

    SECOND_REPLACEMENT_MANIFEST.write_text(
        json.dumps({
            "schema": "ztare-h124-canonical-carrier-replacement-manifest-v1",
            "excluded_replications": [3, 4],
            "replication_3_reason": "control_transport_timeout_before_endpoint",
            "replication_4_reason": "compact_prompt_key_order_hash_mismatch",
            "replication_4_actual_prompt_hashes": actual_pair4_hashes,
            "replacement_replication": 5,
            "replacement_order": list(REPLACEMENT_ORDER),
            "canonical_capsule_receipt": canonical_receipt,
            "target_grid_carrier_sha256": h124.TARGET_GRID_CARRIER_SHA256,
            "endpoint_and_thresholds_changed": False,
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for order_index, label in enumerate(REPLACEMENT_ORDER):
        h124._run_arm(
            replication=5,
            label=label,
            capsule=canonical_capsules[label],
            capsule_receipt=canonical_receipt,
            order_index=order_index,
            treatment_carrier=treatment_carrier,
        )

    orders = {
        1: list(manifest["orders"]["1"]),
        2: list(manifest["orders"]["2"]),
        5: list(REPLACEMENT_ORDER),
    }
    pairs = [
        _pair(replication, orders[replication])
        for replication in VALID_REPLICATIONS
    ]
    all_sessions = [
        session
        for pair in pairs
        for row in pair["arms"].values()
        for session in row["session_ids"]
    ]
    if len(all_sessions) != 6 or len(set(all_sessions)) != 6:
        raise SystemExit("H124 canonical-pair session identities crossed")
    if not all(
        row["one_shot_recall"]
        for pair in pairs
        for row in pair["arms"].values()
    ):
        raise SystemExit("H124 canonical-pair recall was not one-shot")

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
    output: dict[str, Any] = {
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
        "capsule_receipt": canonical_receipt,
        "attempted_replication_count": 5,
        "valid_replication_count": 3,
        "valid_replications": list(VALID_REPLICATIONS),
        "excluded_pairs": [
            {
                "replication": 3,
                "reason": "control_transport_timeout_before_endpoint",
                "control_returncodes": [0, 124],
                "trace_path": h124._relative(failed_trace_path),
            },
            {
                "replication": 4,
                "reason": "compact_prompt_key_order_hash_mismatch",
                "actual_prompt_hashes": actual_pair4_hashes,
                "registered_prompt_hashes": {
                    "uncertainty_bearing_identity": canonical_receipt[
                        "uncertainty_bearing_identity_sha256"
                    ],
                    "neutral_uncertainty_control": canonical_receipt[
                        "neutral_uncertainty_control_sha256"
                    ],
                },
            },
        ],
        "treatment_completions": treatment_completions,
        "control_completions": control_completions,
        "completion_difference": (
            treatment_completions - control_completions
        ),
        "pairs": pairs,
        "claim_boundary": (
            "Three complete canonical-byte within-game cross-level pairs "
            "after excluding transport- and carrier-invalid pairs. No "
            "cross-game, multi-generation, broad-capability, population, or "
            "literature-novelty conclusion follows."
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
