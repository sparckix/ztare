#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping


DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[2]
sys.path.insert(0, str(DIRECTORY))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import h128_compiler_native_start_state_acquisition_probe as h128  # noqa: E402
from h121_cold_level2_fast_state_counterfactual_probe import (  # noqa: E402
    _LocalArcade,
    _load_game_module,
)
from ztare.substrates.arc_agi3 import ArcAgi3Adapter  # noqa: E402


OUTPUT = DIRECTORY / "h128_compiler_native_start_state_acquisition_audit_result.json"
EXPECTED_SCHEMAS = {
    "ztare-arc3-probe-run-manifest-v1": 1,
    "ztare-codex-subscription-exchange-v1": 10,
    "ztare-arc3-probe-turn-checkpoint-v1": 10,
    "ztare-arc3-probe-final-result-v1": 1,
}
EXPECTED_REDACTION_PATHS = {
    "active_uncertainties[0]",
    "decision_seam.branches[0].contact_kind",
    "decision_seam.branches[0].risk_rank",
    "decision_seam.branches[1].contact_kind",
    "decision_seam.branches[1].risk_rank",
    "decision_seam.selected_action",
    "decision_seam.selected_contact_kind",
    "decision_seam.selected_direction",
    "decision_seam.sha256",
    "memory_revision.relation.kind",
    "memory_revision.relation.mismatch_count",
    "memory_revision.relation.passed",
    "memory_revision.relation.support_count",
    "memory_revision.sha256",
    "target_compatibility.status",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _replay(actions: list[int], report: Mapping[str, Any]) -> dict[str, Any]:
    adapter = ArcAgi3Adapter(
        "tu93-0768757b",
        arcade=_LocalArcade(_load_game_module()),
    )
    grid = adapter.reset()
    grids = [grid]
    identities = []
    terminal_rows = []
    for action_count, action in enumerate(actions, start=1):
        grid = adapter.reset() if action == -1 else adapter.step(action)
        grids.append(grid)
        identity = adapter.last_transition_identity
        receipt = identity.to_dict() if identity is not None else None
        identities.append(receipt)
        boundary = None if receipt is None else receipt.get("boundary_kind")
        if boundary:
            terminal_rows.append({
                "action_count": action_count,
                "boundary_kind": boundary,
            })
    expected_grids = [h128.h125._grid(row) for row in report["observations"]]
    return {
        "all_grids_match": grids == expected_grids,
        "transition_identities_match": identities == [
            row["transition_identity"] for row in report["turns"]
        ],
        "final_levels_completed": int(adapter.levels_completed),
        "terminal_rows": terminal_rows,
    }


def _audit_arm(
    row: Mapping[str, Any],
    capsules: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    label = str(row["label"])
    report_path = ROOT / str(row["report_path"])
    trace_path = ROOT / str(row["trace_path"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    trace = _read_jsonl(trace_path)
    counts = Counter(str(item.get("schema")) for item in trace)
    exchanges = [
        item for item in trace
        if item.get("schema") == "ztare-codex-subscription-exchange-v1"
    ]
    decoded = [json.loads(str(item["stdout"]).strip()) for item in exchanges]
    actions = [int(turn["action"]) for turn in report["turns"]]
    capsule_text = h128._rendered_capsule(capsules[label]).decode("utf-8")
    capsule_prompt_turns = [
        int(item["turn_index"])
        for item in exchanges
        if capsule_text in str(item["prompt"])
    ]
    session_ids = sorted({
        str(turn["session_id"]) for turn in report["turns"]
    })
    exchange_sessions = sorted({
        str(item["final_session_state"]["session_id"])
        for item in exchanges
    })
    replay = _replay(actions, report)
    checks = {
        "schema_counts_match": dict(counts) == EXPECTED_SCHEMAS,
        "exchange_returncodes_zero": all(
            int(item["returncode"]) == 0 for item in exchanges
        ),
        "exchange_actions_match": [
            int(item["action"]) for item in decoded
        ] == actions,
        "result_actions_match": actions == list(row["action_sequence"]),
        "capsule_is_one_shot": capsule_prompt_turns == [0],
        "recall_receipt_is_one_shot": [
            index for index, turn in enumerate(report["turns"])
            if turn.get("recall_injection") is not None
        ] == [0],
        "one_session": len(session_ids) == 1,
        "exchange_session_matches": exchange_sessions == session_ids,
        "fresh_start_exact": (
            report["observations"][0]["sha256"]
            == h128.FRESH_START_OBSERVATION_SHA256
        ),
        "start_carrier_exact": (
            h128._canonical_sha256(
                h128._grid_carrier(report["observations"][0])
            ) == h128.TARGET_GRID_CARRIER_SHA256
        ),
        "budget_exact": len(actions) == h128.BUDGET,
        "grid_replay_exact": replay["all_grids_match"],
        "identity_replay_exact": replay["transition_identities_match"],
        "outcome_matches": (
            replay["final_levels_completed"]
            == int(report["end_levels_completed"])
        ),
    }
    return {
        "replication": int(row["replication"]),
        "label": label,
        "report_sha256": _sha256(report_path),
        "trace_sha256": _sha256(trace_path),
        "session_ids": session_ids,
        "capsule_prompt_turns": capsule_prompt_turns,
        "action_sequence": actions,
        "decision_seam_acquired": actions[:4] == [0, 3, 3, 1],
        "oracle_sequence_exact": (
            actions == [0, 3, 3, 1, 3, 3, 0, 3, 3, 0]
        ),
        "levels_gained": int(report["levels_gained"]),
        "attempt_index": int(row["attempt_index"]),
        "prior_transport_failures": list(row["prior_transport_failures"]),
        "replay": replay,
        "checks": checks,
        "passed": all(checks.values()),
    }


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("H128 audit output must be new")
    result = json.loads(h128.RESULT.read_text(encoding="utf-8"))
    manifest_path = h128.OUTPUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rebuilt_manifest = h128._manifest_payload()
    if manifest != rebuilt_manifest:
        raise SystemExit("H128 manifest or compiler digest drifted")
    capsules = manifest["capsules"]
    treatment_digest = capsules["compiler_native_recall"][
        "arm_payload"
    ]["compiler_digest"]
    control_digest = capsules["relation_redacted_control"][
        "arm_payload"
    ]["compiler_digest"]
    _proposal, selected, independent_digest = h128._compile_fresh_digest()
    redaction_paths = h128._difference_paths(
        treatment_digest,
        control_digest,
    )
    rows = [
        pair["arms"][label]
        for pair in result["pairs"]
        for label in h128.LABELS
    ]
    arms = [_audit_arm(row, capsules) for row in rows]
    sessions = [session for arm in arms for session in arm["session_ids"]]
    treatment = [
        arm for arm in arms if arm["label"] == "compiler_native_recall"
    ]
    controls = [
        arm for arm in arms if arm["label"] == "relation_redacted_control"
    ]
    global_checks = {
        "result_identity_current": (
            result["identities"]["h127_result_sha256"]
            == h128.H127_RESULT_SHA256
        ),
        "manifest_rebuild_exact": manifest == rebuilt_manifest,
        "treatment_digest_is_independent_compiler_output": (
            treatment_digest == independent_digest == selected.digest
        ),
        "memory_identity_preserved": (
            treatment_digest["memory_revision"]["sha256"]
            == h128.H127_MEMORY_REVISION_SHA256
        ),
        "fresh_context_bound": (
            treatment_digest["scope"]["context_sha256"]
            == h128.FRESH_START_OBSERVATION_SHA256
            and treatment_digest["target_compatibility"][
                "observation_sha256"
            ] == h128.FRESH_START_OBSERVATION_SHA256
        ),
        "capsule_lengths_equal": (
            len(h128._rendered_capsule(capsules[h128.LABELS[0]]))
            == len(h128._rendered_capsule(capsules[h128.LABELS[1]]))
            == int(manifest["capsule_receipt"]["rendered_prompt_bytes"])
        ),
        "redaction_paths_exact": redaction_paths == EXPECTED_REDACTION_PATHS,
        "six_valid_arms": len(arms) == 6,
        "all_arms_pass": all(arm["passed"] for arm in arms),
        "six_unique_sessions": len(sessions) == len(set(sessions)) == 6,
        "no_transport_exclusions": all(
            not arm["prior_transport_failures"] and arm["attempt_index"] == 0
            for arm in arms
        ),
        "treatment_seams_3_of_3": sum(
            arm["decision_seam_acquired"] for arm in treatment
        ) == 3,
        "control_seams_0_of_3": sum(
            arm["decision_seam_acquired"] for arm in controls
        ) == 0,
        "treatment_completions_1_of_3": sum(
            arm["levels_gained"] > 0 for arm in treatment
        ) == 1,
        "control_completions_0_of_3": sum(
            arm["levels_gained"] > 0 for arm in controls
        ) == 0,
        "result_disposition_matches": (
            result["disposition"] == "supported_compiler_consumption_only"
        ),
    }
    if not all(global_checks.values()):
        raise SystemExit(json.dumps({
            "failed_global_checks": [
                key for key, value in global_checks.items() if not value
            ],
            "failed_arms": [
                [arm["replication"], arm["label"]]
                for arm in arms if not arm["passed"]
            ],
            "redaction_paths": sorted(redaction_paths),
        }, sort_keys=True))
    output = {
        "schema": "ztare-h128-compiler-native-start-state-audit-v1",
        "status": "passed",
        "environment_contact": False,
        "controller_contact": False,
        "result_sha256": _sha256(h128.RESULT),
        "manifest_sha256": _sha256(manifest_path),
        "capsule_receipt": manifest["capsule_receipt"],
        "redaction_difference_paths": sorted(redaction_paths),
        "global_checks": global_checks,
        "valid_arm_count": len(arms),
        "unique_session_count": len(set(sessions)),
        "successful_exchange_count": 10 * len(arms),
        "treatment_acquisitions": sum(
            arm["decision_seam_acquired"] for arm in treatment
        ),
        "control_acquisitions": sum(
            arm["decision_seam_acquired"] for arm in controls
        ),
        "treatment_completions": sum(
            arm["levels_gained"] > 0 for arm in treatment
        ),
        "control_completions": sum(
            arm["levels_gained"] > 0 for arm in controls
        ),
        "arms": arms,
        "claim_boundary": (
            "Audit validates automatic compiler consumption at the delayed "
            "decision seam. Recurrent post-transition recompilation, online "
            "settlement, cross-game transfer, later acquisition catalysis, "
            "broad capability, and novelty remain unsettled."
        ),
    }
    OUTPUT.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": output["status"],
        "result_sha256": output["result_sha256"],
        "valid_arm_count": output["valid_arm_count"],
        "unique_session_count": output["unique_session_count"],
        "successful_exchange_count": output["successful_exchange_count"],
        "treatment_acquisitions": output["treatment_acquisitions"],
        "control_acquisitions": output["control_acquisitions"],
        "treatment_completions": output["treatment_completions"],
        "control_completions": output["control_completions"],
        "global_check_count": len(global_checks),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
