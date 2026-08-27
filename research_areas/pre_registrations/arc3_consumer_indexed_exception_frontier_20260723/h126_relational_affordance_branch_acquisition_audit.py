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

import h126_relational_affordance_branch_acquisition_probe as h126  # noqa: E402
from h121_cold_level2_fast_state_counterfactual_probe import (  # noqa: E402
    _LocalArcade,
    _load_game_module,
)
from ztare.substrates.arc_agi3 import ArcAgi3Adapter  # noqa: E402


OUTPUT = (
    DIRECTORY
    / "h126_relational_affordance_branch_acquisition_audit_result.json"
)
EXPECTED_SCHEMAS = {
    "ztare-arc3-probe-run-manifest-v1": 1,
    "ztare-codex-subscription-exchange-v1": 7,
    "ztare-arc3-probe-turn-checkpoint-v1": 7,
    "ztare-arc3-probe-final-result-v1": 1,
}
EXPECTED_DIFFERENCE_PATHS = {
    "intervention.arm_kind",
    "intervention.branch_judgment.direct_contact",
    "intervention.branch_judgment.lower_contact",
    "intervention.branch_judgment.reason",
    "intervention.branch_judgment.selected_action",
    "intervention.branch_judgment.selected_direction",
    "intervention.relation.claim",
    "intervention.relation.mismatch_count",
    "intervention.relation.status",
    "intervention.relation.support_count",
    "intervention.relation.transported_motion_bearing",
    "padding",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _difference_paths(
    first: Any,
    second: Any,
    *,
    prefix: str = "",
) -> set[str]:
    if isinstance(first, dict) and isinstance(second, dict):
        paths = set()
        for key in set(first) | set(second):
            child = f"{prefix}.{key}" if prefix else str(key)
            if key not in first or key not in second:
                paths.add(child)
            else:
                paths |= _difference_paths(
                    first[key], second[key], prefix=child
                )
        return paths
    if isinstance(first, list) and isinstance(second, list):
        if len(first) != len(second):
            return {prefix}
        paths = set()
        for index, (left, right) in enumerate(zip(first, second)):
            paths |= _difference_paths(
                left, right, prefix=f"{prefix}[{index}]"
            )
        return paths
    return set() if first == second else {prefix}


def _replay(
    actions: list[int],
    report: Mapping[str, Any],
) -> dict[str, Any]:
    adapter = ArcAgi3Adapter(
        "tu93-0768757b",
        arcade=_LocalArcade(_load_game_module()),
    )
    grid = adapter.reset()
    prefix_grids = [grid]
    prefix_identities = []
    for action in h126.RESTORED_PREFIX:
        grid = adapter.step(action)
        prefix_grids.append(grid)
        prefix_identities.append(
            adapter.last_transition_identity.to_dict()
            if adapter.last_transition_identity is not None
            else None
        )
    controller_grids = [grid]
    controller_identities = []
    terminal_rows = []
    for action_count, action in enumerate(actions, start=1):
        grid = adapter.reset() if action == -1 else adapter.step(action)
        controller_grids.append(grid)
        identity = adapter.last_transition_identity
        receipt = identity.to_dict() if identity is not None else None
        controller_identities.append(receipt)
        boundary = None if receipt is None else receipt.get("boundary_kind")
        if boundary:
            terminal_rows.append({
                "action_count": action_count,
                "boundary_kind": boundary,
            })
    expected_prefix = [
        h126._grid(row)
        for row in report["restored_prefix"]["observations"]
    ]
    expected_controller = [
        h126._grid(row) for row in report["observations"]
    ]
    return {
        "prefix_grids_match": prefix_grids == expected_prefix,
        "controller_grids_match": controller_grids == expected_controller,
        "prefix_transition_identities_match": prefix_identities == [
            row["transition_identity"]
            for row in report["restored_prefix"]["transitions"]
        ],
        "controller_transition_identities_match": (
            controller_identities
            == [row["transition_identity"] for row in report["turns"]]
        ),
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
        item
        for item in trace
        if item.get("schema") == "ztare-codex-subscription-exchange-v1"
    ]
    decoded = [json.loads(str(item["stdout"]).strip()) for item in exchanges]
    actions = [int(turn["action"]) for turn in report["turns"]]
    capsule_text = h126._rendered_capsule(capsules[label]).decode("utf-8")
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
    branch_carrier = h126._grid_carrier(report["observations"][0])
    replay = _replay(actions, report)
    checks = {
        "schema_counts_match": dict(counts) == EXPECTED_SCHEMAS,
        "exchange_returncodes_zero": all(
            int(item["returncode"]) == 0 for item in exchanges
        ),
        "exchange_actions_match": [
            int(item["action"]) for item in decoded
        ] == actions,
        "report_actions_match_result": actions == list(row["action_sequence"]),
        "capsule_is_one_shot": capsule_prompt_turns == [0],
        "recall_receipt_is_one_shot": [
            index
            for index, turn in enumerate(report["turns"])
            if turn.get("recall_injection") is not None
        ] == [0],
        "one_session": len(session_ids) == 1,
        "exchange_session_matches": exchange_sessions == session_ids,
        "restored_prefix_exact": (
            report["restored_prefix"]["actions"]
            == list(h126.RESTORED_PREFIX)
        ),
        "branch_carrier_exact": (
            h126._canonical_sha256(branch_carrier)
            == h126.BRANCH_GRID_CARRIER_SHA256
        ),
        "budget_exact": len(actions) == h126.REMAINING_BUDGET,
        "prefix_replay_exact": (
            replay["prefix_grids_match"]
            and replay["prefix_transition_identities_match"]
        ),
        "controller_replay_exact": (
            replay["controller_grids_match"]
            and replay["controller_transition_identities_match"]
        ),
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
        "first_action": actions[0],
        "levels_gained": int(report["levels_gained"]),
        "oracle_suffix_exact": actions == [1, 3, 3, 0, 3, 3, 0],
        "attempt_index": int(row["attempt_index"]),
        "prior_transport_failures": list(row["prior_transport_failures"]),
        "replay": replay,
        "checks": checks,
        "passed": all(checks.values()),
    }


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("H126 audit output must be new")
    result = json.loads(h126.RESULT.read_text(encoding="utf-8"))
    manifest_path = h126.OUTPUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rebuilt_manifest = h126._manifest_payload()
    if manifest != rebuilt_manifest:
        raise SystemExit("H126 manifest or capsule bytes drifted")
    capsules = manifest["capsules"]
    difference_paths = _difference_paths(
        capsules["relational_affordance"],
        capsules["relation_withheld_control"],
    )
    result_rows = [
        pair["arms"][label]
        for pair in result["pairs"]
        for label in h126.LABELS
    ]
    arms = [_audit_arm(row, capsules) for row in result_rows]
    sessions = [
        session for arm in arms for session in arm["session_ids"]
    ]
    transport_failures = [
        failure
        for arm in arms
        for failure in arm["prior_transport_failures"]
    ]
    failure_trace = _read_jsonl(
        ROOT / str(transport_failures[0]["trace_path"])
    ) if len(transport_failures) == 1 else []
    failure_exchanges = [
        row
        for row in failure_trace
        if row.get("schema") == "ztare-codex-subscription-exchange-v1"
    ]
    treatment = [
        arm for arm in arms if arm["label"] == "relational_affordance"
    ]
    controls = [
        arm for arm in arms if arm["label"] == "relation_withheld_control"
    ]
    global_checks = {
        "result_identity_current": (
            result["identities"]["h125_result_sha256"]
            == h126.H125_SHA256
        ),
        "manifest_rebuild_exact": manifest == rebuilt_manifest,
        "capsule_lengths_equal": (
            len(h126._rendered_capsule(capsules[h126.LABELS[0]]))
            == len(h126._rendered_capsule(capsules[h126.LABELS[1]]))
            == int(manifest["capsule_receipt"]["rendered_prompt_bytes"])
        ),
        "capsule_difference_paths_exact": (
            difference_paths == EXPECTED_DIFFERENCE_PATHS
        ),
        "six_valid_arms": len(arms) == 6,
        "all_arms_pass": all(arm["passed"] for arm in arms),
        "six_unique_sessions": len(sessions) == len(set(sessions)) == 6,
        "one_excluded_pre_action_transport": (
            len(transport_failures) == 1
            and len(failure_exchanges) == 1
            and int(failure_exchanges[0]["returncode"]) == 1
            and not failure_exchanges[0].get("final_session_state")
            and sum(
                row.get("schema") == "ztare-arc3-probe-turn-checkpoint-v1"
                for row in failure_trace
            ) == 0
        ),
        "treatment_actions_3_of_3": sum(
            arm["first_action"] == 1 for arm in treatment
        ) == 3,
        "control_actions_1_of_3": sum(
            arm["first_action"] == 1 for arm in controls
        ) == 1,
        "treatment_completions_3_of_3": sum(
            arm["levels_gained"] > 0 for arm in treatment
        ) == 3,
        "control_completions_1_of_3": sum(
            arm["levels_gained"] > 0 for arm in controls
        ) == 1,
        "treatment_oracle_suffix_3_of_3": sum(
            arm["oracle_suffix_exact"] for arm in treatment
        ) == 3,
        "result_disposition_matches": (
            result["disposition"] == "supported_task_effect"
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
            "difference_paths": sorted(difference_paths),
        }, sort_keys=True))
    output = {
        "schema": "ztare-h126-relational-affordance-acquisition-audit-v1",
        "status": "passed",
        "environment_contact": False,
        "controller_contact": False,
        "result_sha256": _sha256(h126.RESULT),
        "manifest_sha256": _sha256(manifest_path),
        "capsule_receipt": manifest["capsule_receipt"],
        "capsule_difference_paths": sorted(difference_paths),
        "global_checks": global_checks,
        "valid_arm_count": len(arms),
        "unique_session_count": len(set(sessions)),
        "successful_exchange_count": sum(
            EXPECTED_SCHEMAS["ztare-codex-subscription-exchange-v1"]
            for _arm in arms
        ),
        "excluded_pre_action_transport_failures": transport_failures,
        "treatment_acquisitions": sum(
            arm["first_action"] == 1 for arm in treatment
        ),
        "control_acquisitions": sum(
            arm["first_action"] == 1 for arm in controls
        ),
        "treatment_completions": sum(
            arm["levels_gained"] > 0 for arm in treatment
        ),
        "control_completions": sum(
            arm["levels_gained"] > 0 for arm in controls
        ),
        "arms": arms,
        "claim_boundary": (
            "Audit validates the fixed within-game restored-branch causal "
            "result. Transfer, autonomous target-consequence discovery, "
            "multi-generation compounding, broad capability, and literature "
            "novelty remain unsettled."
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
