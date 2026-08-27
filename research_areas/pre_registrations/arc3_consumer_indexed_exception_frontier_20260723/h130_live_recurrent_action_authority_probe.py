#!/usr/bin/env python3
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
DIRECTORY = Path(__file__).resolve().parent
sys.path[:0] = [str(DIRECTORY), str(ROOT), str(ROOT / "src")]

from scripts.public.control.arc3_responses_agent_probe import (  # noqa: E402
    _append_trace_event,
    _emit_turn_progress,
    run_subscription_probe,
)
from ztare.substrates.arc_agi3 import ArcAgi3Adapter  # noqa: E402
from ztare.worldmodel.relational_affordance_recall import (  # noqa: E402
    ActiveRelationalWorkingRevision,
    SettledResidualWorkingRevision,
    advance_relational_working_revision,
    compile_active_relational_working_revision,
)

import h125_palette_quotiented_pose_motion_affordance_audit as h125  # noqa: E402
import h127_autonomous_relational_affordance_recall_audit as h127  # noqa: E402
import h128_compiler_native_start_state_acquisition_probe as h128  # noqa: E402
from h121_cold_level2_fast_state_counterfactual_probe import (  # noqa: E402
    _LocalArcade,
    _load_game_module,
)


H129_RESULT = DIRECTORY / "h129_recurrent_relational_working_memory_result.json"
H129_RESULT_SHA256 = "9b44881450716c38a69fdad31d422a28783d8abf59d00dfd493e21c2b53714e2"
OUTPUT_DIR = DIRECTORY / "h130_live_recurrent_action_authority"
RESULT = DIRECTORY / "h130_live_recurrent_action_authority_result.json"
SIMULATION = DIRECTORY / "h130_live_recurrent_action_authority_prelive_simulation.json"
MEMORY_SHA256 = "858791e0752c25121f1f04c0c702346b91bd104a93a6e140ad2784243f0dc935"
INITIAL_CAPSULE_SHA256 = "07cb6fc716ce91671f9ed98332cf88689024e49b644a839cc5d3e67e917bba83"
FRESH_START_OBSERVATION_SHA256 = h128.FRESH_START_OBSERVATION_SHA256
TARGET_GRID_CARRIER_SHA256 = h128.TARGET_GRID_CARRIER_SHA256
REPLICATION_COUNT = 3
BUDGET = 10
REFRESH_BYTES = 2048
LABELS = ("current_action_authority", "current_action_withheld")
REDACTION_PATHS = (
    "current_action.action",
    "current_action.contact_kind",
    "current_action.direction",
    "guard",
    "refusal",
    "revision_schema",
    "working_revision_sha256",
)


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


def _rendered(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), separators=(",", ":")).encode("utf-8")


def _difference_paths(first: Any, second: Any, prefix: str = "") -> set[str]:
    if isinstance(first, dict) and isinstance(second, dict):
        paths = set()
        for key in set(first) | set(second):
            child = f"{prefix}.{key}" if prefix else str(key)
            if key not in first or key not in second:
                paths.add(child)
            else:
                paths |= _difference_paths(first[key], second[key], child)
        return paths
    if isinstance(first, list) and isinstance(second, list):
        if len(first) != len(second):
            return {prefix}
        paths = set()
        for index, (left, right) in enumerate(zip(first, second)):
            paths |= _difference_paths(left, right, f"{prefix}[{index}]")
        return paths
    return set() if first == second else {prefix}


def _redact_action_authority(digest: Mapping[str, Any]) -> dict[str, Any]:
    control = deepcopy(dict(digest))
    control["revision_schema"] = "ztare-current-action-authority-withheld-v1"
    control["working_revision_sha256"] = None
    control["current_action"] = {
        "direction": None,
        "action": None,
        "contact_kind": "withheld",
    }
    control["guard"] = (
        "current observation and source memory are retained; current action "
        "authority is withheld"
    )
    control["refusal"] = "no alternative action is supplied"
    return _canonical_object(control)


def _pad_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    envelope = _canonical_object(value)
    if envelope.get("padding") != "":
        raise ValueError("refresh envelope must start with empty padding")
    shortfall = REFRESH_BYTES - len(_rendered(envelope))
    if shortfall < 0:
        raise ValueError(
            f"refresh envelope exceeds {REFRESH_BYTES} bytes by {-shortfall}"
        )
    envelope["padding"] = " " * shortfall
    envelope = _canonical_object(envelope)
    if len(_rendered(envelope)) != REFRESH_BYTES:
        raise RuntimeError("refresh envelope padding failed")
    return envelope


def _envelope_pair(
    *,
    refresh_index: int,
    observation_sha256: str,
    treatment_digest: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    treatment_digest = _canonical_object(treatment_digest)
    control_digest = _redact_action_authority(treatment_digest)
    common = {
        "schema": "ztare-h130-current-working-refresh-envelope-v1",
        "source_h129_result_sha256": H129_RESULT_SHA256,
        "source_memory_sha256": MEMORY_SHA256,
        "refresh_index": int(refresh_index),
        "observation_sha256": str(observation_sha256),
        "arm_payload": {},
        "padding": "",
    }
    treatment = _pad_envelope({
        **common,
        "arm_payload": {
            "kind": "current_action_authority",
            "working_digest": treatment_digest,
        },
    })
    control = _pad_envelope({
        **common,
        "arm_payload": {
            "kind": "current_action_withheld",
            "working_digest": control_digest,
        },
    })
    paths = sorted(_difference_paths(treatment_digest, control_digest))
    if not set(paths).issubset(set(REDACTION_PATHS)):
        raise RuntimeError(f"H130 undeclared redaction paths: {paths}")
    return {
        "current_action_authority": treatment,
        "current_action_withheld": control,
    }, {
        "refresh_index": int(refresh_index),
        "observation_sha256": str(observation_sha256),
        "rendered_bytes": REFRESH_BYTES,
        "treatment_digest_sha256": _canonical_sha256(treatment_digest),
        "control_digest_sha256": _canonical_sha256(control_digest),
        "treatment_envelope_sha256": hashlib.sha256(
            _rendered(treatment)
        ).hexdigest(),
        "control_envelope_sha256": hashlib.sha256(
            _rendered(control)
        ).hexdigest(),
        "redaction_difference_paths": paths,
    }


def _scope(observation_sha256: str):
    return h127._scope(context_sha256=str(observation_sha256))


def _refusal_digest(
    *,
    observation_sha256: str,
    remaining_budget: int,
    reason: str,
) -> dict[str, Any]:
    return {
        "schema": "ztare-relational-working-action-v1",
        "revision_schema": "ztare-working-revision-refusal-v1",
        "working_revision_sha256": None,
        "source_memory_sha256": MEMORY_SHA256,
        "observation_sha256": str(observation_sha256),
        "scope_sha256": _scope(str(observation_sha256)).sha256,
        "remaining_budget": int(remaining_budget),
        "current_action": {
            "direction": None,
            "action": None,
            "contact_kind": "unavailable",
        },
        "guard": "no working action is authorized for this observation",
        "refusal": str(reason),
    }


class _WorkingRefreshProvider:
    def __init__(
        self,
        *,
        label: str,
        memory,
    ) -> None:
        if label not in LABELS:
            raise ValueError(f"unknown H130 arm: {label}")
        self.label = label
        self.memory = memory
        self.revision = None
        self.events: list[dict[str, Any]] = []

    def __call__(
        self,
        observation: Mapping[str, Any],
        turn_index: int,
        observations: Sequence[Mapping[str, Any]],
        turns: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any] | None:
        if int(turn_index) == 0:
            if self.revision is not None:
                raise RuntimeError("H130 provider initialized more than once")
            self.revision = compile_active_relational_working_revision(
                self.memory,
                target_grid=h125._grid(observation),
                observation_sha256=str(observation["sha256"]),
                scope=_scope(str(observation["sha256"])),
                remaining_budget=BUDGET,
            )
            return None
        if self.revision is None:
            raise RuntimeError("H130 provider lacks turn-zero initialization")
        if len(turns) != int(turn_index):
            raise RuntimeError("H130 provider chronology drifted")
        if len(observations) != int(turn_index) + 1:
            raise RuntimeError("H130 provider observation chronology drifted")
        observation_sha256 = str(observation["sha256"])
        remaining_budget = BUDGET - int(turn_index)
        previous_action = int(turns[-1]["action"])
        prior_revision_sha256 = self.revision.sha256
        advance_receipt = None
        rebind_kind = "advanced_executed_revision"
        refusal_reason = None
        try:
            if (
                isinstance(self.revision, ActiveRelationalWorkingRevision)
                and previous_action != self.revision.selected_action
            ):
                rebind_kind = "recompiled_after_unexecuted_revision"
                self.revision = compile_active_relational_working_revision(
                    self.memory,
                    target_grid=h125._grid(observation),
                    observation_sha256=observation_sha256,
                    scope=_scope(observation_sha256),
                    remaining_budget=remaining_budget,
                    predecessor_revision_sha256=prior_revision_sha256,
                )
            else:
                advance = advance_relational_working_revision(
                    self.revision,
                    successor_grid=h125._grid(observation),
                    successor_observation_sha256=observation_sha256,
                    successor_scope=_scope(observation_sha256),
                    remaining_budget=remaining_budget,
                )
                self.revision = advance.revision
                advance_receipt = advance.to_receipt()
            treatment_digest = self.revision.digest_payload()
            compiled_action = self.revision.selected_action
            revision_schema = self.revision.to_receipt()["schema"]
            working_revision_sha256 = self.revision.sha256
            source_memory_sha256 = self.revision.memory_revision.sha256
            settlement_status = (
                advance_receipt.get("settlement", {}).get("status")
                if isinstance(advance_receipt, dict)
                and isinstance(advance_receipt.get("settlement"), dict)
                else None
            )
        except ValueError as exc:
            rebind_kind = "typed_working_refusal"
            refusal_reason = f"{type(exc).__name__}: {exc}"
            treatment_digest = _refusal_digest(
                observation_sha256=observation_sha256,
                remaining_budget=remaining_budget,
                reason=refusal_reason,
            )
            compiled_action = None
            revision_schema = treatment_digest["revision_schema"]
            working_revision_sha256 = None
            source_memory_sha256 = MEMORY_SHA256
            settlement_status = None
        if source_memory_sha256 != MEMORY_SHA256:
            raise RuntimeError("H130 source memory identity drifted")
        envelopes, pair_receipt = _envelope_pair(
            refresh_index=int(turn_index),
            observation_sha256=observation_sha256,
            treatment_digest=treatment_digest,
        )
        injected = envelopes[self.label]
        event = {
            "schema": "ztare-h130-working-refresh-event-v1",
            "arm": self.label,
            "turn_index": int(turn_index),
            "observation_sha256": observation_sha256,
            "remaining_budget": remaining_budget,
            "previous_action": previous_action,
            "prior_revision_sha256": prior_revision_sha256,
            "rebind_kind": rebind_kind,
            "working_revision_sha256": working_revision_sha256,
            "revision_schema": revision_schema,
            "compiled_action": compiled_action,
            "settlement_status": settlement_status,
            "refusal_reason": refusal_reason,
            "advance_receipt": advance_receipt,
            "pair_receipt": pair_receipt,
            "injected_envelope_sha256": hashlib.sha256(
                _rendered(injected)
            ).hexdigest(),
        }
        self.events.append(event)
        return {"digest": injected}


def _initial_capsule_and_memory():
    manifest = h128._manifest_payload()
    initial = manifest["capsules"]["compiler_native_recall"]
    if hashlib.sha256(_rendered(initial)).hexdigest() != INITIAL_CAPSULE_SHA256:
        raise RuntimeError("H130 initial H128 capsule identity drifted")
    proposal, _selected, _digest = h128._compile_fresh_digest()
    if proposal.memory_revision.sha256 != MEMORY_SHA256:
        raise RuntimeError("H130 source memory identity drifted")
    return initial, proposal.memory_revision


def _orders(order_sha256: str) -> dict[str, list[str]]:
    treatment_first = int(order_sha256[-1], 16) % 2 == 0
    rows = {}
    for replication in range(1, REPLICATION_COUNT + 1):
        first = treatment_first if replication % 2 == 1 else not treatment_first
        rows[str(replication)] = (
            ["current_action_authority", "current_action_withheld"]
            if first else
            ["current_action_withheld", "current_action_authority"]
        )
    return rows


def _simulation_payload(initial_capsule, memory) -> dict[str, Any]:
    successful = json.loads((
        h128.OUTPUT_DIR / "replication_1_compiler_native_recall_report.json"
    ).read_text(encoding="utf-8"))
    treatment_provider = _WorkingRefreshProvider(
        label="current_action_authority",
        memory=memory,
    )
    control_provider = _WorkingRefreshProvider(
        label="current_action_withheld",
        memory=memory,
    )
    for index in range(BUDGET):
        prefix_observations = tuple(successful["observations"][:index + 1])
        prefix_turns = tuple(successful["turns"][:index])
        treatment_provider(
            successful["observations"][index],
            index,
            prefix_observations,
            prefix_turns,
        )
        control_provider(
            successful["observations"][index],
            index,
            prefix_observations,
            prefix_turns,
        )
    expected_later_actions = [
        int(row["action"]) for row in successful["turns"][1:]
    ]
    compiled_later_actions = [
        row["compiled_action"] for row in treatment_provider.events
    ]

    ignored = json.loads((
        h128.OUTPUT_DIR / "replication_2_compiler_native_recall_report.json"
    ).read_text(encoding="utf-8"))
    ignored_provider = _WorkingRefreshProvider(
        label="current_action_withheld",
        memory=memory,
    )
    ignored_digest_count = 0
    for index in range(BUDGET):
        provided = ignored_provider(
            ignored["observations"][index],
            index,
            tuple(ignored["observations"][:index + 1]),
            tuple(ignored["turns"][:index]),
        )
        ignored_digest_count += provided is not None

    checks = {
        "initial_capsule_bytes": len(_rendered(initial_capsule)) == 3912,
        "initial_capsule_sha256": (
            hashlib.sha256(_rendered(initial_capsule)).hexdigest()
            == INITIAL_CAPSULE_SHA256
        ),
        "nine_treatment_refreshes": len(treatment_provider.events) == 9,
        "nine_control_refreshes": len(control_provider.events) == 9,
        "successful_actions_reconstructed": (
            compiled_later_actions == expected_later_actions
        ),
        "all_refreshes_exact_bytes": all(
            row["pair_receipt"]["rendered_bytes"] == REFRESH_BYTES
            for row in treatment_provider.events + control_provider.events
        ),
        "redaction_paths_bounded": all(
            set(row["pair_receipt"]["redaction_difference_paths"])
            .issubset(set(REDACTION_PATHS))
            for row in treatment_provider.events + control_provider.events
        ),
        "ignored_action_path_remains_total": ignored_digest_count == 9,
        "ignored_action_emits_typed_refusal": any(
            row["rebind_kind"] == "typed_working_refusal"
            for row in ignored_provider.events
        ),
        "provider_instances_isolated": (
            treatment_provider.events is not control_provider.events
            and treatment_provider.revision is not control_provider.revision
        ),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise RuntimeError(f"H130 pre-live simulation failed: {failed}")
    return {
        "schema": "ztare-h130-prelive-simulation-v1",
        "status": "passed",
        "controller_contact": False,
        "environment_contact": False,
        "checks": checks,
        "successful_treatment_events": treatment_provider.events,
        "successful_control_events": control_provider.events,
        "ignored_action_events": ignored_provider.events,
    }


def _manifest_payload() -> dict[str, Any]:
    if _sha256(H129_RESULT) != H129_RESULT_SHA256:
        raise RuntimeError("H130 frozen H129 identity drifted")
    initial, memory = _initial_capsule_and_memory()
    simulation = _simulation_payload(initial, memory)
    simulation_sha256 = _canonical_sha256(simulation)
    order_sha256 = hashlib.sha256(
        _rendered(initial)
        + b"\x00"
        + bytes.fromhex(H129_RESULT_SHA256)
        + b"\x00"
        + bytes.fromhex(simulation_sha256)
    ).hexdigest()
    return {
        "schema": "ztare-h130-live-recurrent-action-authority-manifest-v1",
        "hypothesis_id": (
            "H-GPSA-LIVE-RECURRENT-ACTION-AUTHORITY-20260808-130"
        ),
        "replication_count": REPLICATION_COUNT,
        "budget": BUDGET,
        "refresh_bytes": REFRESH_BYTES,
        "redaction_paths": list(REDACTION_PATHS),
        "source_h129_result_sha256": H129_RESULT_SHA256,
        "source_memory_sha256": MEMORY_SHA256,
        "initial_capsule_sha256": INITIAL_CAPSULE_SHA256,
        "fresh_start_observation_sha256": FRESH_START_OBSERVATION_SHA256,
        "target_grid_carrier_sha256": TARGET_GRID_CARRIER_SHA256,
        "simulation_sha256": simulation_sha256,
        "order_sha256": order_sha256,
        "orders": _orders(order_sha256),
        "initial_capsule": initial,
        "simulation": simulation,
    }


def _prepare_manifest() -> dict[str, Any]:
    payload = _manifest_payload()
    manifest_path = OUTPUT_DIR / "manifest.json"
    if OUTPUT_DIR.exists():
        if not manifest_path.exists():
            raise RuntimeError("H130 output directory lacks manifest")
        stored = json.loads(manifest_path.read_text(encoding="utf-8"))
        if stored != payload:
            raise RuntimeError("H130 frozen manifest drifted")
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
        manifest_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if SIMULATION.exists():
        stored_simulation = json.loads(SIMULATION.read_text(encoding="utf-8"))
        if stored_simulation != payload["simulation"]:
            raise RuntimeError("H130 pre-live simulation drifted")
    else:
        SIMULATION.write_text(
            json.dumps(payload["simulation"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return payload


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
            raise RuntimeError(f"H130 completed or malformed arm exists: {stem}")
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
        precontact_instrument_failure = (
            not exchanges and not checkpoints and not finals
        )
        preaction_transport_failure = (
            len(exchanges) == 1
            and int(exchanges[0].get("returncode") or 0) != 0
            and not checkpoints
            and not finals
            and not exchanges[0].get("final_session_state")
        )
        if not (precontact_instrument_failure or preaction_transport_failure):
            raise RuntimeError(
                f"H130 existing attempt is not an excludable pre-action "
                f"transport failure: {trace_path.name}"
            )
        failures.append({
            "attempt_index": attempt_index,
            "trace_path": _relative(trace_path),
            "failure_kind": (
                "precontact_provider_initialization"
                if precontact_instrument_failure
                else "preaction_transport"
            ),
            "returncode": (
                int(exchanges[0]["returncode"]) if exchanges else None
            ),
            "checkpoint_count": 0,
            "final_session_state": {},
        })
        attempt_index += 1


def _run_arm(
    *,
    replication: int,
    label: str,
    initial_capsule: Mapping[str, Any],
    order_index: int,
) -> dict[str, Any]:
    stem = f"replication_{replication}_{label}"
    trace_path, report_path, prior_failures = _allocate_attempt(stem)
    adapter = ArcAgi3Adapter(
        "tu93-0768757b",
        arcade=_LocalArcade(_load_game_module()),
    )
    _proposal, _selected, _digest = h128._compile_fresh_digest()
    provider = _WorkingRefreshProvider(
        label=label,
        memory=_proposal.memory_revision,
    )

    def trace_event(event: Mapping[str, Any]) -> None:
        _append_trace_event(trace_path, event)

    def observe_turn(turn: Mapping[str, Any]) -> None:
        _emit_turn_progress(turn)
        trace_event({
            "schema": "ztare-arc3-probe-turn-checkpoint-v1",
            "hypothesis": "H130",
            "replication": replication,
            "arm": label,
            "turn": dict(turn),
        })

    trace_event({
        "schema": "ztare-arc3-probe-run-manifest-v1",
        "hypothesis": "H130",
        "replication": replication,
        "arm": label,
        "order_index": order_index,
        "attempt_index": len(prior_failures),
        "budget": BUDGET,
        "model": "gpt-5.6-sol",
        "reasoning_effort": "max",
        "initial_capsule_sha256": INITIAL_CAPSULE_SHA256,
        "refresh_bytes": REFRESH_BYTES,
        "redaction_paths": list(REDACTION_PATHS),
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
        initial_recall_digest=initial_capsule,
        decision_recall_provider=provider,
    )
    if str(payload["observations"][0]["sha256"]) != FRESH_START_OBSERVATION_SHA256:
        raise RuntimeError("H130 fresh start observation drifted")
    if payload["actor"]["decision_recall_count"] != 9:
        raise RuntimeError("H130 dynamic refresh count drifted")
    if len(provider.events) != 9:
        raise RuntimeError("H130 provider event count drifted")
    for event in provider.events:
        turn = payload["turns"][event["turn_index"]]
        injection = turn.get("recall_injection") or {}
        if (
            str(injection.get("digest_sha256") or "")
            != event["injected_envelope_sha256"]
        ):
            raise RuntimeError("H130 injected refresh identity drifted")
    report = {
        **payload,
        "h130": {
            "replication": replication,
            "arm": label,
            "working_refresh_events": provider.events,
            "initial_capsule_sha256": INITIAL_CAPSULE_SHA256,
        },
    }
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    trace_event({
        "schema": "ztare-arc3-probe-final-result-v1",
        "hypothesis": "H130",
        "replication": replication,
        "arm": label,
        "result": report,
        "report_path": _relative(report_path),
    })
    refresh_adherence = sum(
        event["compiled_action"] is not None
        and int(payload["turns"][event["turn_index"]]["action"])
        == int(event["compiled_action"])
        for event in provider.events
    )
    actions = [int(turn["action"]) for turn in payload["turns"]]
    return {
        "replication": replication,
        "label": label,
        "status": payload["status"],
        "levels_gained": int(payload["levels_gained"]),
        "first_level_action": payload["first_level_action"],
        "actions_executed": int(payload["actions_executed"]),
        "action_sequence": actions,
        "refresh_adherence_count": refresh_adherence,
        "refresh_opportunity_count": len(provider.events),
        "refresh_adherence_rate": refresh_adherence / len(provider.events),
        "compiled_refresh_count": sum(
            row["compiled_action"] is not None for row in provider.events
        ),
        "typed_refusal_count": sum(
            row["rebind_kind"] == "typed_working_refusal"
            for row in provider.events
        ),
        "target_refutation_count": sum(
            row["settlement_status"] == "target_transport_refuted"
            for row in provider.events
        ),
        "session_ids": sorted({
            str(turn["session_id"]) for turn in payload["turns"]
        }),
        "initial_and_dynamic_injection_count": sum(
            turn.get("recall_injection") is not None for turn in payload["turns"]
        ),
        "attempt_index": len(prior_failures),
        "prior_transport_failures": prior_failures,
        "report_path": _relative(report_path),
        "trace_path": _relative(trace_path),
    }


def _disposition(
    treatment_completions: int,
    control_completions: int,
    treatment_adherence: float,
    control_adherence: float,
) -> str:
    if (
        treatment_completions >= 2
        and treatment_completions - control_completions >= 2
    ):
        return "supported_recurrent_task_effect"
    if treatment_adherence >= 0.90 and treatment_adherence - control_adherence >= 0.20:
        return "supported_action_consumption_only"
    if (
        treatment_completions <= control_completions
        and treatment_adherence <= control_adherence
    ):
        return "refuted"
    return "inconclusive"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if RESULT.exists():
        raise SystemExit("H130 result output must be new")
    manifest = _prepare_manifest()
    if args.prepare_only:
        print(json.dumps({
            "status": "prepared_no_controller_contact",
            "manifest_path": _relative(OUTPUT_DIR / "manifest.json"),
            "simulation_path": _relative(SIMULATION),
            "simulation_sha256": manifest["simulation_sha256"],
            "orders": manifest["orders"],
            "refresh_bytes": manifest["refresh_bytes"],
        }, indent=2, sort_keys=True))
        return 0

    pairs = []
    seen_sessions: set[str] = set()
    for replication in range(1, REPLICATION_COUNT + 1):
        arms = []
        for order_index, label in enumerate(manifest["orders"][str(replication)]):
            row = _run_arm(
                replication=replication,
                label=label,
                initial_capsule=manifest["initial_capsule"],
                order_index=order_index,
            )
            sessions = set(row["session_ids"])
            if len(sessions) != 1 or sessions & seen_sessions:
                raise RuntimeError("H130 session identity crossed an arm")
            seen_sessions |= sessions
            arms.append(row)
        by_label = {row["label"]: row for row in arms}
        pairs.append({
            "replication": replication,
            "order": manifest["orders"][str(replication)],
            "arms": by_label,
        })

    treatment = [pair["arms"]["current_action_authority"] for pair in pairs]
    controls = [pair["arms"]["current_action_withheld"] for pair in pairs]
    treatment_completions = sum(row["levels_gained"] > 0 for row in treatment)
    control_completions = sum(row["levels_gained"] > 0 for row in controls)
    treatment_adherence = sum(
        row["refresh_adherence_count"] for row in treatment
    ) / sum(row["refresh_opportunity_count"] for row in treatment)
    control_adherence = sum(
        row["refresh_adherence_count"] for row in controls
    ) / sum(row["refresh_opportunity_count"] for row in controls)
    output = {
        "schema": "ztare-h130-live-recurrent-action-authority-v1",
        "hypothesis_id": manifest["hypothesis_id"],
        "status": "complete",
        "disposition": _disposition(
            treatment_completions,
            control_completions,
            treatment_adherence,
            control_adherence,
        ),
        "environment_contact": False,
        "controller_contact": True,
        "identities": {
            "h129_result_sha256": H129_RESULT_SHA256,
            "source_memory_sha256": MEMORY_SHA256,
            "initial_capsule_sha256": INITIAL_CAPSULE_SHA256,
            "fresh_start_observation_sha256": FRESH_START_OBSERVATION_SHA256,
            "target_grid_carrier_sha256": TARGET_GRID_CARRIER_SHA256,
            "simulation_sha256": manifest["simulation_sha256"],
        },
        "replication_count": REPLICATION_COUNT,
        "treatment_completions": treatment_completions,
        "control_completions": control_completions,
        "completion_difference": treatment_completions - control_completions,
        "treatment_refresh_adherence": treatment_adherence,
        "control_compiler_counterfactual_adherence": control_adherence,
        "refresh_adherence_difference": treatment_adherence - control_adherence,
        "pairs": pairs,
        "claim_boundary": (
            "Three within-game recurrent-action pairs. Cross-game transfer, "
            "later non-equivalent acquisition savings, second-generation "
            "reproduction, critical mass, biological fidelity, and novelty "
            "remain unsettled."
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
            "treatment_completions",
            "control_completions",
            "completion_difference",
            "treatment_refresh_adherence",
            "control_compiler_counterfactual_adherence",
            "refresh_adherence_difference",
        )
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
