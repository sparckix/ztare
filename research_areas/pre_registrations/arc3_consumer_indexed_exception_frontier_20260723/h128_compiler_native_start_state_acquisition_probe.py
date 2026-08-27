#!/usr/bin/env python3
from __future__ import annotations

import argparse
from copy import deepcopy
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
from ztare.common.wake_sleep_credit_router import (  # noqa: E402
    MemoryAcquisitionProvenance,
    WakeSleepCreditState,
)
from ztare.substrates.arc_agi3 import ArcAgi3Adapter  # noqa: E402
from ztare.worldmodel.relational_affordance_recall import (  # noqa: E402
    select_relational_affordance_recall,
)

import h125_palette_quotiented_pose_motion_affordance_audit as h125  # noqa: E402
import h127_autonomous_relational_affordance_recall_audit as h127  # noqa: E402
from h121_cold_level2_fast_state_counterfactual_probe import (  # noqa: E402
    _LocalArcade,
    _load_game_module,
)


DIRECTORY = Path(__file__).resolve().parent
H119_REPORT = DIRECTORY / "h119_tu93_persistent_sol_max_report.json"
H127_RESULT = DIRECTORY / "h127_autonomous_relational_affordance_recall_result.json"
OUTPUT_DIR = DIRECTORY / "h128_compiler_native_start_state_acquisition"
RESULT = DIRECTORY / "h128_compiler_native_start_state_acquisition_result.json"
H127_RESULT_SHA256 = (
    "9a61127622e25ad4f16fb16edffa2ccf6f8ea2f2e835dda89281d1c52422df4b"
)
H127_MEMORY_REVISION_SHA256 = (
    "858791e0752c25121f1f04c0c702346b91bd104a93a6e140ad2784243f0dc935"
)
H127_PROPOSAL_SHA256 = (
    "a606753f1fa48bd9c583d89e13b3f567633df34876695cb04fce30d97de28ced"
)
H127_FRONTIER_SHA256 = (
    "54c6bfeb79bf0e9eccee4650e88b9d55155b8378ef2960d47e1387f60dc9570f"
)
FRESH_START_OBSERVATION_SHA256 = (
    "910f639b419322c3cedb66764b31513a1a4c6ea5643297004c9afee5eb05da31"
)
TARGET_GRID_CARRIER_SHA256 = (
    "dde09802332964a1530f9c3b3509a3732aec0d69325f2d3af29cca5162c06b24"
)
REPLICATION_COUNT = 3
BUDGET = 10
LABELS = ("compiler_native_recall", "relation_redacted_control")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _canonical_object(value: Mapping[str, Any]) -> dict[str, Any]:
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


def _grid_carrier(observation: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "grid_shape": list(observation["grid_shape"]),
        "grid_rle_rows": list(observation["grid_rle_rows"]),
    }


def _fresh_scope():
    return h127._scope(
        context_sha256=FRESH_START_OBSERVATION_SHA256,
    )


def _compile_fresh_digest() -> tuple[Any, Any, dict[str, Any]]:
    report = json.loads(H119_REPORT.read_text(encoding="utf-8"))
    log = h125._log(report)
    source_refs, boundary_refs, support_hashes = h127._support(report)
    session_ids = sorted({
        str(turn["session_id"]) for turn in report["turns"][:22]
    })
    provenance = MemoryAcquisitionProvenance(
        episode_sha256=h127.H119_SHA256,
        observation_sha256=str(report["observations"][21]["sha256"]),
        controller_instance_sha256=_canonical_sha256(session_ids),
        support_sha256s=support_hashes,
        boundary_support_sha256s=(support_hashes[-1],),
    )
    proposal = h127._compile(
        report=report,
        log=log,
        target_grid=h125._grid(report["observations"][22]),
        target_observation_sha256=FRESH_START_OBSERVATION_SHA256,
        scope=_fresh_scope(),
        source_refs=source_refs,
        boundary_refs=boundary_refs,
        provenance=provenance,
        budget=BUDGET,
    )
    selected = select_relational_affordance_recall(
        proposal,
        WakeSleepCreditState(),
        consumption_scope=_fresh_scope(),
    )
    if not selected.selected or selected.digest is None:
        raise RuntimeError("H128 fresh-scope compiler digest was not selected")
    if proposal.memory_revision.sha256 != H127_MEMORY_REVISION_SHA256:
        raise RuntimeError("H128 source memory identity drifted")
    if proposal.decision_seam.frontier_sha256 != H127_FRONTIER_SHA256:
        raise RuntimeError("H128 frontier identity drifted")
    if proposal.sha256 == H127_PROPOSAL_SHA256:
        raise RuntimeError("H128 fresh proposal failed to change context identity")
    return proposal, selected, _canonical_object(selected.digest)


def _redact_digest(digest: Mapping[str, Any]) -> dict[str, Any]:
    """Remove only relation support and its contact/selection consequence."""

    redacted = deepcopy(dict(digest))
    revision = redacted["memory_revision"]
    relation = revision["relation"]
    relation["kind"] = "relation_withheld_control"
    relation["support_count"] = None
    relation["mismatch_count"] = None
    relation["passed"] = False
    revision["sha256"] = None
    compatibility = redacted["target_compatibility"]
    compatibility["status"] = "relation_withheld_control"
    seam = redacted["decision_seam"]
    for branch in seam["branches"]:
        branch["contact_kind"] = "unknown"
        branch["risk_rank"] = None
    seam["selected_direction"] = None
    seam["selected_action"] = None
    seam["selected_contact_kind"] = "unknown"
    seam["sha256"] = None
    redacted["active_uncertainties"] = [
        "marker-to-motion relation, target dynamics, and contact outcome remain unsettled"
    ]
    return _canonical_object(redacted)


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
                paths |= _difference_paths(first[key], second[key], prefix=child)
        return paths
    if isinstance(first, list) and isinstance(second, list):
        if len(first) != len(second):
            return {prefix}
        paths = set()
        for index, (left, right) in enumerate(zip(first, second)):
            paths |= _difference_paths(
                left,
                right,
                prefix=f"{prefix}[{index}]",
            )
        return paths
    return set() if first == second else {prefix}


def _capsules() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    proposal, selected, treatment_digest = _compile_fresh_digest()
    control_digest = _redact_digest(treatment_digest)
    common = {
        "schema": "ztare-h128-compiler-native-recall-envelope-v1",
        "source_h127_result_sha256": H127_RESULT_SHA256,
        "memory_revision_sha256": proposal.memory_revision.sha256,
        "proposal_sha256": proposal.sha256,
        "frontier_sha256": proposal.decision_seam.frontier_sha256,
        "scope_sha256": proposal.scope.sha256,
        "fresh_start_observation_sha256": FRESH_START_OBSERVATION_SHA256,
        "compiler_recall_sha256": selected.recall.sha256,
        "arm_payload": {},
        "padding": "",
    }
    treatment = {
        **common,
        "arm_payload": {
            "kind": "compiler_native_recall",
            "compiler_digest": treatment_digest,
        },
    }
    control = {
        **common,
        "arm_payload": {
            "kind": "relation_redacted_control",
            "compiler_digest": control_digest,
        },
    }
    treatment = _canonical_object(treatment)
    control = _canonical_object(control)
    treatment_bytes = _rendered_capsule(treatment)
    control_bytes = _rendered_capsule(control)
    if len(treatment_bytes) < len(control_bytes):
        treatment["padding"] = " " * (len(control_bytes) - len(treatment_bytes))
    elif len(control_bytes) < len(treatment_bytes):
        control["padding"] = " " * (len(treatment_bytes) - len(control_bytes))
    treatment = _canonical_object(treatment)
    control = _canonical_object(control)
    treatment_bytes = _rendered_capsule(treatment)
    control_bytes = _rendered_capsule(control)
    if len(treatment_bytes) != len(control_bytes):
        raise RuntimeError("H128 capsules are not exact-byte matched")
    capsules = {
        "compiler_native_recall": treatment,
        "relation_redacted_control": control,
    }
    return capsules, {
        "rendered_prompt_bytes": len(treatment_bytes),
        "compiler_native_recall_sha256": hashlib.sha256(
            treatment_bytes
        ).hexdigest(),
        "relation_redacted_control_sha256": hashlib.sha256(
            control_bytes
        ).hexdigest(),
        "pair_sha256": hashlib.sha256(
            treatment_bytes + b"\x00" + control_bytes
        ).hexdigest(),
        "embedded_treatment_digest_sha256": _canonical_sha256(treatment_digest),
        "embedded_control_digest_sha256": _canonical_sha256(control_digest),
        "compiler_proposal_sha256": proposal.sha256,
        "compiler_scope_sha256": proposal.scope.sha256,
        "compiler_recall_sha256": selected.recall.sha256,
        "redaction_difference_paths": sorted(
            _difference_paths(treatment_digest, control_digest)
        ),
    }


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
            ["compiler_native_recall", "relation_redacted_control"]
            if treatment_first
            else ["relation_redacted_control", "compiler_native_recall"]
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
    failures = []
    attempt_index = 0
    while True:
        trace_path, report_path = _attempt_paths(stem, attempt_index)
        if not trace_path.exists() and not report_path.exists():
            return trace_path, report_path, failures
        if report_path.exists() or not trace_path.exists():
            raise RuntimeError(f"H128 completed or malformed arm exists: {stem}")
        rows = _read_jsonl(trace_path)
        exchanges = [
            row for row in rows
            if row.get("schema") == "ztare-codex-subscription-exchange-v1"
        ]
        checkpoints = [
            row for row in rows
            if row.get("schema") == "ztare-arc3-probe-turn-checkpoint-v1"
        ]
        finals = [
            row for row in rows
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
                f"H128 existing attempt is not an excludable pre-action "
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
    if _sha256(H127_RESULT) != H127_RESULT_SHA256:
        raise RuntimeError("frozen H127 result identity drifted")
    h127_result = json.loads(H127_RESULT.read_text(encoding="utf-8"))
    if h127_result["memory_revision"]["sha256"] != H127_MEMORY_REVISION_SHA256:
        raise RuntimeError("frozen H127 memory identity drifted")
    if h127_result["proposal"]["proposal_sha256"] != H127_PROPOSAL_SHA256:
        raise RuntimeError("frozen H127 proposal identity drifted")
    capsules, receipt = _capsules()
    return {
        "schema": "ztare-h128-compiler-native-start-manifest-v1",
        "hypothesis_id": (
            "H-GPSA-COMPILER-NATIVE-START-STATE-ACQUISITION-20260808-128"
        ),
        "replication_count": REPLICATION_COUNT,
        "budget": BUDGET,
        "fresh_start_observation_sha256": FRESH_START_OBSERVATION_SHA256,
        "target_grid_carrier_sha256": TARGET_GRID_CARRIER_SHA256,
        "h127_result_sha256": H127_RESULT_SHA256,
        "capsule_receipt": receipt,
        "orders": _orders(str(receipt["pair_sha256"])),
        "capsules": capsules,
    }


def _prepare_manifest() -> dict[str, Any]:
    payload = _manifest_payload()
    manifest_path = OUTPUT_DIR / "manifest.json"
    if OUTPUT_DIR.exists():
        if not manifest_path.exists():
            raise RuntimeError("H128 output directory lacks a manifest")
        stored = json.loads(manifest_path.read_text(encoding="utf-8"))
        if stored != payload:
            raise RuntimeError("H128 frozen manifest drifted")
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
            "hypothesis": "H128",
            "replication": replication,
            "arm": label,
            "turn": dict(turn),
        })

    trace_event({
        "schema": "ztare-arc3-probe-run-manifest-v1",
        "hypothesis": "H128",
        "replication": replication,
        "arm": label,
        "order_index": order_index,
        "attempt_index": attempt_index,
        "budget": BUDGET,
        "model": "gpt-5.6-sol",
        "reasoning_effort": "max",
        "start_level": 2,
        "capsule_pair_receipt": dict(capsule_receipt),
    })
    payload = run_subscription_probe(
        adapter=adapter,
        game_id="tu93-0768757b",
        budget=BUDGET,
        model_id="gpt-5.6-sol",
        reasoning_effort="max",
        timeout_seconds=300,
        resume_session=True,
        turn_observer=observe_turn,
        exchange_observer=trace_event,
        level_boundary_sleep_top_k=0,
        initial_recall_digest=capsule,
    )
    if str(payload["observations"][0]["sha256"]) != FRESH_START_OBSERVATION_SHA256:
        raise RuntimeError(f"H128 {stem} fresh start observation drifted")
    if _canonical_sha256(
        _grid_carrier(payload["observations"][0])
    ) != TARGET_GRID_CARRIER_SHA256:
        raise RuntimeError(f"H128 {stem} start grid carrier drifted")
    injected_turns = [
        index for index, turn in enumerate(payload["turns"])
        if turn.get("recall_injection") is not None
    ]
    if injected_turns != [0]:
        raise RuntimeError(f"H128 {stem} recall was not exactly one-shot")
    report_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    trace_event({
        "schema": "ztare-arc3-probe-final-result-v1",
        "hypothesis": "H128",
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
        "decision_seam_acquired": actions[:4] == [0, 3, 3, 1],
        "oracle_sequence_exact": actions == [0, 3, 3, 1, 3, 3, 0, 3, 3, 0],
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
    treatment_acquisitions: int,
    control_acquisitions: int,
    treatment_completions: int,
    control_completions: int,
) -> str:
    task = (
        treatment_completions >= 2
        and treatment_completions - control_completions >= 2
    )
    acquisition = (
        treatment_acquisitions >= 2
        and treatment_acquisitions - control_acquisitions >= 2
    )
    if task:
        return "supported_task_effect"
    if acquisition:
        return "supported_compiler_consumption_only"
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
        raise SystemExit("H128 result output must be new")
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
                raise RuntimeError("H128 session identity crossed an arm")
            seen_sessions |= arm_sessions
            rows.append(row)
        by_label = {row["label"]: row for row in rows}
        treatment = by_label["compiler_native_recall"]
        control = by_label["relation_redacted_control"]
        pairs.append({
            "replication": replication,
            "order": manifest["orders"][str(replication)],
            "seam_pair_outcome": (
                "treatment_win"
                if treatment["decision_seam_acquired"]
                > control["decision_seam_acquired"]
                else "control_win"
                if control["decision_seam_acquired"]
                > treatment["decision_seam_acquired"]
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
        pair["arms"]["compiler_native_recall"]["decision_seam_acquired"]
        for pair in pairs
    )
    control_acquisitions = sum(
        pair["arms"]["relation_redacted_control"]["decision_seam_acquired"]
        for pair in pairs
    )
    treatment_completions = sum(
        pair["arms"]["compiler_native_recall"]["levels_gained"] > 0
        for pair in pairs
    )
    control_completions = sum(
        pair["arms"]["relation_redacted_control"]["levels_gained"] > 0
        for pair in pairs
    )
    output = {
        "schema": "ztare-h128-compiler-native-start-state-acquisition-v1",
        "hypothesis_id": manifest["hypothesis_id"],
        "status": "complete",
        "disposition": _disposition(
            treatment_acquisitions,
            control_acquisitions,
            treatment_completions,
            control_completions,
        ),
        "environment_contact": False,
        "controller_contact": True,
        "identities": {
            "h127_result_sha256": _sha256(H127_RESULT),
            "h127_memory_revision_sha256": H127_MEMORY_REVISION_SHA256,
            "h127_evidence_proposal_sha256": H127_PROPOSAL_SHA256,
            "fresh_compiler_proposal_sha256": manifest[
                "capsule_receipt"
            ]["compiler_proposal_sha256"],
            "fresh_compiler_scope_sha256": manifest[
                "capsule_receipt"
            ]["compiler_scope_sha256"],
            "fresh_start_observation_sha256": FRESH_START_OBSERVATION_SHA256,
            "target_grid_carrier_sha256": TARGET_GRID_CARRIER_SHA256,
        },
        "capsule_receipt": manifest["capsule_receipt"],
        "replication_count": REPLICATION_COUNT,
        "treatment_acquisitions": treatment_acquisitions,
        "control_acquisitions": control_acquisitions,
        "acquisition_difference": treatment_acquisitions - control_acquisitions,
        "treatment_completions": treatment_completions,
        "control_completions": control_completions,
        "completion_difference": treatment_completions - control_completions,
        "pairs": pairs,
        "claim_boundary": (
            "Three repeated exact-byte within-game full-start pairs using "
            "compiler-native treatment. Online target settlement, cross-game "
            "transfer, later acquisition catalysis, broad capability, "
            "population, and literature novelty remain unsettled."
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
