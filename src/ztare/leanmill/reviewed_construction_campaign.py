"""Campaign-owned transitions for reviewed, data-only constructions.

The frontier runner selects this lifecycle; this module owns construction
identity, replay, and persistence.  Adapter mathematics remains in registered
capabilities and authored candidates remain inert JSON.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable, Mapping, Sequence

from ztare.common.task_discharge import TaskDischargeContract
from ztare.leanmill.authority_slot import read_bounded_json_authority_slot
from ztare.leanmill.common import read_json, sha256_file, write_json_atomic
from ztare.leanmill.exploration_budget import (
    BudgetExceeded,
    BudgetLedgerResourceUnavailable,
    BudgetStopReceipt,
    ExplorationBudget,
    ExplorationBudgetLedger,
)
from ztare.leanmill.frontier_campaign_roles import (
    frontier_role_artifact_directories,
)
from ztare.leanmill.frontier_agent_runtime import (
    parse_bounded_frontier_json,
    read_completed_frontier_role_call,
    read_frontier_role_call_receipt,
)
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.theory_program import TheoryProgram
from ztare.leanmill.witness_construction_boundary import (
    GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR,
    WITNESS_CONSTRUCTION_BOUNDARY_RESULT_SCHEMA,
    WITNESS_CONSTRUCTION_EXECUTION_COORDINATE_SCHEMA,
    WitnessConstructionCandidateEnvelope,
    build_witness_construction_candidate,
    build_witness_constructor_output,
    validate_witness_construction_boundary_result,
    validate_witness_constructor_output,
    validate_witness_constructor_request,
    witness_construction_parameters,
)


RECOVERED_BOUNDARY_FEEDBACK_SCHEMA = (
    "leanmill.recovered_boundary_artifact_feedback.v2"
)
CONSTRUCTION_RECOVERY_TRANSITION_SCHEMA = (
    "leanmill.reviewed_construction_recovery_transition.v1"
)
CONSTRUCTION_ADVANCEMENT_TRANSITION_SCHEMA = (
    "leanmill.reviewed_construction_advancement_transition.v1"
)
CONSTRUCTION_RECOVERY_ROLLBACK_SCHEMA = (
    "leanmill.construction_recovery_rollback_reconciliation.v1"
)
_MAX_RECOVERY_ROLE_DIRECTORIES = 256
_MAX_RECOVERY_ROLE_FILES = 8_192
_MAX_RECOVERY_ROLE_FILE_BYTES = 32_000_000
_MAX_RECOVERY_ROLE_AGGREGATE_BYTES = 256_000_000
_MAX_ATTEMPT_ROOT_ENTRIES = 8_192
_MAX_LEGACY_PARAMETERIZATION_EXECUTIONS = 64
_MAX_LEGACY_PARAMETERIZATION_EXECUTION_BYTES = 128_000_000
_MAX_CONSTRUCTION_PARAMETERIZATION_BYTES = 64_000_000
_MAX_CONSTRUCTION_AUTHORITY_SLOT_BYTES = 64_000_000
_MAX_FAMILY_EXECUTION_REPLAY_AGGREGATE_BYTES = 128_000_000
_MAX_RECOVERY_CONTROL_NODES = 8_192


def _is_exact_protocol_discriminant(
    value: Any,
    allowed: tuple[str, ...],
) -> bool:
    """Recognize a JSON protocol tag without hashing container-shaped input."""

    return type(value) is str and value in allowed


def _consume_recovery_control_nodes(
    counter: list[int],
    amount: int = 1,
) -> None:
    """Bound traversal of host-owned control slots, excluding inert payloads."""

    counter[0] += amount
    if counter[0] > _MAX_RECOVERY_CONTROL_NODES:
        raise ValueError("construction recovery control-node ceiling exhausted")


def _optional_control_sequence(
    owner: Mapping[str, Any],
    field: str,
    *,
    context: str,
) -> tuple[Any, ...]:
    value = owner.get(field)
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{context} {field} must be an array")
    return tuple(value)


@dataclass(frozen=True)
class ReviewedConstructionHooks:
    approved_parameterization: Callable[..., Any]
    language_outcome_feedback: Callable[..., Any]
    approved_family: Callable[..., Any]
    persist_ratification_admissions: Callable[..., Any]
    family_synthesis_provenance: Callable[..., Any]
    frozen_terminal_lineage_ids: Callable[..., Any]
    language_request_from_run: Callable[..., Any]
    current_family_exhaustion_discharge: Callable[..., Any]

    def __post_init__(self) -> None:
        for name, value in self.__dict__.items():
            if not callable(value):
                raise ValueError(f"reviewed construction hook {name} is not callable")


def _read_bounded_authority_slot(
    path: Path,
    *,
    max_bytes: int,
    context: str,
) -> tuple[dict[str, Any], int] | None:
    """Compatibility alias for the invariant-owned authority-slot reader."""

    return read_bounded_json_authority_slot(
        path,
        max_bytes=max_bytes,
        context=context,
    )


def _persist_exact(
    path: Path,
    value: Mapping[str, Any],
    *,
    context: str,
    max_bytes: int = _MAX_CONSTRUCTION_AUTHORITY_SLOT_BYTES,
) -> None:
    """Publish one immutable authority object without replacing an owner."""

    frozen = dict(value)
    payload = (json.dumps(frozen, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    if len(payload) > max_bytes:
        raise ValueError(f"{context} exceeds its byte ceiling")
    prior = _read_bounded_authority_slot(
        path, max_bytes=max_bytes, context=context
    )
    if prior is not None:
        if prior[0] != frozen:
            raise ValueError(f"{context} identity conflicts with persisted bytes")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_name, path, follow_symlinks=False)
        except FileExistsError:
            occupied = _read_bounded_authority_slot(
                path, max_bytes=max_bytes, context=context
            )
            if occupied is None or occupied[0] != frozen:
                raise ValueError(
                    f"{context} identity conflicts with persisted bytes"
                )
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def witness_execution_coordinate_from_contract(
    contract: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Recover the complete coordinate only from a validated candidate envelope."""

    schema = contract.get("schema")
    if schema is not None and not _is_exact_protocol_discriminant(
        schema,
        ("ztare-task-discharge-contract-v1",),
    ):
        return None
    if (
        contract.get("adjudicator_id")
        != GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR
    ):
        return None
    try:
        frozen = TaskDischargeContract.from_dict(contract)
        parameters = witness_construction_parameters(frozen)
    except (KeyError, TypeError, ValueError):
        return None
    envelope = parameters.get("candidate_envelope")
    if not isinstance(envelope, Mapping):
        return None
    try:
        candidate = WitnessConstructionCandidateEnvelope.from_json(envelope)
    except (KeyError, TypeError, ValueError):
        return None
    return candidate.execution_coordinate


def bind_recovered_boundary_artifact_feedback(
    directory: Path,
    navigation: Mapping[str, Any],
) -> dict[str, Any]:
    """Project boundary outcomes only across equal execution coordinates.

    Historical rows without a complete coordinate are ignored.  In particular,
    verifier observations are evidence, never semantic matching keys.
    """

    projected = dict(navigation)
    completion = read_json(directory / "boundary_completion.json", None)
    if not isinstance(completion, Mapping):
        return projected
    completion_core = {
        key: value for key, value in completion.items() if key != "completion_sha256"
    }
    if completion.get("completion_sha256") != content_hash(completion_core):
        raise ValueError("recovered boundary completion digest mismatch")
    boundary = completion.get("boundary_result")
    if not isinstance(boundary, Mapping):
        return projected
    boundary_core = {
        key: value for key, value in boundary.items() if key != "result_sha256"
    }
    if boundary.get("result_sha256") != content_hash(boundary_core):
        raise ValueError("recovered boundary result digest mismatch")

    exact_rows: list[dict[str, Any]] = []
    for raw in boundary.get("query_results") or ():
        if (
            not isinstance(raw, Mapping)
            or raw.get("candidate_kind") != "theory_task"
            or not _is_exact_protocol_discriminant(
                raw.get("status"),
                (
                    "witness_rejected",
                    "witness_verified",
                    "capability_unavailable",
                ),
            )
        ):
            continue
        row = dict(raw)
        row_core = {
            key: value for key, value in row.items() if key != "receipt_sha256"
        }
        coordinate = row.get("execution_coordinate")
        if (
            row.get("receipt_sha256") != content_hash(row_core)
            or not isinstance(coordinate, Mapping)
            or coordinate.get("coordinate_sha256")
            != content_hash(
                {
                    key: value
                    for key, value in coordinate.items()
                    if key != "coordinate_sha256"
                }
            )
            or row.get("execution_coordinate_sha256")
            != coordinate.get("coordinate_sha256")
        ):
            # A legacy task result has no authority to migrate to a rebuilt
            # program.  It may still be consumed by its original contract.
            continue
        exact_rows.append(row)
    if not exact_rows:
        return projected

    source_contracts: dict[str, TaskDischargeContract] = {}
    discharge = completion.get("theory_task_discharge")
    for bundle_row in (
        discharge.get("rows")
        if isinstance(discharge, Mapping)
        and isinstance(discharge.get("rows"), list)
        else ()
    ):
        contract_row = (
            bundle_row.get("contract")
            if isinstance(bundle_row, Mapping)
            else None
        )
        if not isinstance(contract_row, Mapping):
            continue
        source_contract = TaskDischargeContract.from_dict(contract_row)
        if bundle_row.get("contract_sha256") != source_contract.sha256:
            raise ValueError("recovered task-discharge contract digest mismatch")
        source_contracts[source_contract.sha256] = source_contract

    finalists: list[dict[str, Any]] = []
    history = [
        dict(row)
        for row in projected.get("objective_review_history") or ()
        if isinstance(row, Mapping)
    ]
    for raw_finalist in projected.get("finalists") or ():
        finalist = dict(raw_finalist)
        program = finalist.get("theory_program")
        matches: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
        if isinstance(program, Mapping):
            frozen_program = TheoryProgram.from_json(program)
            supplied_program_id = finalist.get("theory_program_id")
            if (
                supplied_program_id is not None
                and supplied_program_id != frozen_program.program_id
            ):
                raise ValueError("recovered finalist changed theory-program identity")
            for contract_object in frozen_program.task_discharge_contracts:
                contract = contract_object.to_dict()
                coordinate = witness_execution_coordinate_from_contract(contract)
                if coordinate is None:
                    continue
                for boundary_row in exact_rows:
                    if dict(boundary_row["execution_coordinate"]) == coordinate:
                        current_contract = TaskDischargeContract.from_dict(contract)
                        source_contract = source_contracts.get(
                            str(boundary_row.get("contract_sha256") or "")
                        )
                        if source_contract is None and (
                            current_contract.sha256
                            == boundary_row.get("contract_sha256")
                        ):
                            source_contract = current_contract
                        if source_contract is None:
                            continue
                        validated = validate_witness_construction_boundary_result(
                            source_contract, boundary_row
                        )
                        matches.append((contract, validated))
        identities = {
            (
                str(contract.get("contract_id") or ""),
                str(row.get("receipt_sha256") or ""),
            )
            for contract, row in matches
        }
        if len(identities) > 1:
            raise ValueError("recovered coordinate has ambiguous boundary feedback")
        if matches:
            contract, boundary_row = matches[0]
            coordinate = dict(boundary_row["execution_coordinate"])
            verification = boundary_row.get("verification_receipt")
            observed = (
                verification.get("observed")
                if isinstance(verification, Mapping)
                else None
            )
            feedback_core = {
                "schema": RECOVERED_BOUNDARY_FEEDBACK_SCHEMA,
                "context_hash": str(projected.get("context_hash") or ""),
                "context_epoch": int(projected.get("context_epoch", 0)),
                "program_id": str(finalist.get("theory_program_id") or ""),
                "contract_id": str(contract.get("contract_id") or ""),
                "execution_coordinate": coordinate,
                "execution_coordinate_sha256": coordinate["coordinate_sha256"],
                "boundary_result_sha256": str(boundary["result_sha256"]),
                "boundary_row_receipt_sha256": str(
                    boundary_row["receipt_sha256"]
                ),
                "status": str(boundary_row["status"]),
                "stage": str(boundary_row.get("stage") or ""),
                "reason_code": str(boundary_row.get("reason_code") or ""),
                "outcome": (
                    "rejected"
                    if boundary_row["status"] == "witness_rejected"
                    else "verified"
                    if boundary_row["status"] == "witness_verified"
                    else "unavailable"
                ),
                "observed": observed,
                "route": (
                    "revise_construction"
                    if boundary_row["status"] == "witness_rejected"
                    else "ratify_verified_construction"
                    if boundary_row["status"] == "witness_verified"
                    else "retry_registered_capability"
                ),
                "authority": "exact_execution_coordinate_replay",
                "claim_boundary": (
                    "reuses one registered execution only; makes no code "
                    "existence or nonexistence claim"
                ),
            }
            feedback = {
                **feedback_core,
                "receipt_sha256": content_hash(feedback_core),
            }
            finalist["objective_feedback"] = feedback
            if not any(
                row.get("receipt_sha256") == feedback["receipt_sha256"]
                for row in history
            ):
                history.append(feedback)
            _persist_exact(
                directory
                / (
                    "recovered_boundary_artifact_feedback."
                    f"{feedback['receipt_sha256'][:16]}.json"
                ),
                feedback,
                context="recovered boundary feedback",
            )
        finalists.append(finalist)
    projected["finalists"] = finalists
    if history:
        projected["objective_review_history"] = history
    return projected


def recovered_boundary_feedback_disposition_program_id(
    directory: Path,
    value: Any,
    *,
    context_hash: str,
) -> str | None:
    """Return the exact program disposed by one recovered boundary row."""

    if not isinstance(value, Mapping):
        return None
    required = {
        "schema",
        "context_hash",
        "context_epoch",
        "program_id",
        "contract_id",
        "execution_coordinate",
        "execution_coordinate_sha256",
        "boundary_result_sha256",
        "boundary_row_receipt_sha256",
        "status",
        "stage",
        "reason_code",
        "outcome",
        "observed",
        "route",
        "authority",
        "claim_boundary",
        "receipt_sha256",
    }
    core = {
        key: item for key, item in value.items() if key != "receipt_sha256"
    }
    coordinate = value.get("execution_coordinate")
    coordinate_core = (
        {
            key: item
            for key, item in coordinate.items()
            if key != "coordinate_sha256"
        }
        if isinstance(coordinate, Mapping)
        else {}
    )
    disposition = {
        "witness_rejected": ("rejected", "revise_construction"),
        "witness_verified": ("verified", "ratify_verified_construction"),
    }.get(str(value.get("status") or ""))
    program_id = value.get("program_id")
    coordinate_fields = {
        "schema",
        "context_hash",
        "adapter_id",
        "interface_sha256",
        "target_config_sha256",
        "artifact_sha256",
        "predicate_sha256",
        "witness_schema_sha256",
        "normalizer_sha256",
        "verifier_sha256",
        "coordinate_sha256",
    }
    if (
        set(value) != required
        or value.get("schema") != RECOVERED_BOUNDARY_FEEDBACK_SCHEMA
        or value.get("context_hash") != context_hash
        or type(value.get("context_epoch")) is not int
        or type(program_id) is not str
        or not program_id
        or type(value.get("contract_id")) is not str
        or value.get("receipt_sha256") != content_hash(core)
        or not isinstance(coordinate, Mapping)
        or set(coordinate) != coordinate_fields
        or coordinate.get("schema")
        != WITNESS_CONSTRUCTION_EXECUTION_COORDINATE_SCHEMA
        or coordinate.get("coordinate_sha256") != content_hash(coordinate_core)
        or coordinate.get("context_hash") != context_hash
        or not str(coordinate.get("adapter_id") or "").strip()
        or any(
            not _is_sha256_hex(coordinate.get(field))
            for field in (
                "interface_sha256",
                "target_config_sha256",
                "artifact_sha256",
                "predicate_sha256",
                "witness_schema_sha256",
                "normalizer_sha256",
                "verifier_sha256",
            )
        )
        or value.get("execution_coordinate_sha256")
        != coordinate.get("coordinate_sha256")
        or not _is_sha256_hex(value.get("boundary_result_sha256"))
        or not _is_sha256_hex(value.get("boundary_row_receipt_sha256"))
        or disposition is None
        or (value.get("outcome"), value.get("route")) != disposition
        or value.get("stage") != "complete"
        or value.get("authority") != "exact_execution_coordinate_replay"
        or not str(value.get("claim_boundary") or "").strip()
    ):
        return None
    feedback_slot = _read_bounded_authority_slot(
        directory
        / (
            "recovered_boundary_artifact_feedback."
            f"{str(value['receipt_sha256'])[:16]}.json"
        ),
        max_bytes=_MAX_CONSTRUCTION_AUTHORITY_SLOT_BYTES,
        context="recovered boundary feedback",
    )
    if feedback_slot is None or feedback_slot[0] != dict(value):
        return None
    completion_slot = _read_bounded_authority_slot(
        directory / "boundary_completion.json",
        max_bytes=_MAX_CONSTRUCTION_AUTHORITY_SLOT_BYTES,
        context="recovered boundary completion",
    )
    completion = completion_slot[0] if completion_slot is not None else None
    completion_core = (
        {
            key: item
            for key, item in completion.items()
            if key != "completion_sha256"
        }
        if isinstance(completion, Mapping)
        else {}
    )
    boundary = (
        completion.get("boundary_result")
        if isinstance(completion, Mapping)
        else None
    )
    boundary_core = (
        {
            key: item
            for key, item in boundary.items()
            if key != "result_sha256"
        }
        if isinstance(boundary, Mapping)
        else {}
    )
    if (
        not isinstance(completion, Mapping)
        or completion.get("completion_sha256") != content_hash(completion_core)
        or completion.get("context_hash") != context_hash
        or not isinstance(boundary, Mapping)
        or boundary.get("result_sha256") != content_hash(boundary_core)
        or boundary.get("context_hash") != context_hash
        or value.get("boundary_result_sha256")
        != boundary.get("result_sha256")
    ):
        return None
    matching_boundary_rows = [
        row
        for row in boundary.get("query_results") or ()
        if isinstance(row, Mapping)
        and row.get("receipt_sha256")
        == value.get("boundary_row_receipt_sha256")
    ]
    if len(matching_boundary_rows) != 1:
        return None
    boundary_row = matching_boundary_rows[0]
    boundary_row_core = {
        key: item
        for key, item in boundary_row.items()
        if key != "receipt_sha256"
    }
    if (
        boundary_row.get("receipt_sha256") != content_hash(boundary_row_core)
        or boundary_row.get("candidate_kind") != "theory_task"
        or boundary_row.get("status") != value.get("status")
        or boundary_row.get("stage") != value.get("stage")
        or boundary_row.get("execution_coordinate_sha256")
        != value.get("execution_coordinate_sha256")
        or boundary_row.get("execution_coordinate") != coordinate
    ):
        return None
    return program_id


def _durable_constructor_candidate(
    prompt_text: str,
    raw: Mapping[str, Any],
    call: Mapping[str, Any],
) -> WitnessConstructionCandidateEnvelope:
    marker = "\n\nconstruction_request="
    if marker not in prompt_text:
        raise ValueError("durable constructor prompt lacks its frozen request")
    request_raw = parse_bounded_frontier_json(
        prompt_text.rsplit(marker, 1)[1],
        context="durable witness constructor request",
        maximum=16_000_000,
    )
    if not isinstance(request_raw, Mapping):
        raise ValueError("durable constructor request is malformed")
    request = validate_witness_constructor_request(request_raw)
    if not isinstance(raw, Mapping) or set(raw) != {"artifact", "orientation"}:
        raise ValueError("durable constructor output is malformed")
    call_fields = (
        "schema",
        "role",
        "agent_id",
        "runtime",
        "model",
        "prompt_digest",
        "returncode",
        "provider_call_charge",
        "stdout_digest",
        "stderr_digest",
        "result_digest",
        "output_schema_digest",
    )
    call_receipt = {field: call.get(field) for field in call_fields}
    if call_receipt["role"] != "witness_constructor" or not str(
        call_receipt["agent_id"] or ""
    ):
        raise ValueError("durable constructor call crossed runtime role")
    output = build_witness_constructor_output(
        request,
        artifact=raw["artifact"],
        orientation=raw["orientation"],
        role="witness_constructor",
        agent_id=str(call_receipt["agent_id"]),
        call_receipt_sha256=content_hash(call_receipt),
    )
    output = validate_witness_constructor_output(request, output)
    interface = request["construction_interface"]
    return build_witness_construction_candidate(
        # The navigator-owned outer task request is not part of the constructor
        # prompt.  This deterministic local identity exists only to validate
        # the envelope and derive its request-independent execution coordinate.
        request_id="durable-constructor-request:" + request["request_sha256"],
        context_hash=str(request["context_hash"]),
        adapter_id=str(request["adapter_id"]),
        specification={
            "predicate_ir": interface["predicate_ir"],
            "witness_schema": interface["witness_schema"],
            "normalizer": interface["normalizer"],
            "verifier": interface["verifier"],
            "constructor_request": request,
            "artifact": output["artifact"],
            "orientation": output["orientation"],
            "authorship_receipt": output["authorship_receipt"],
            "discharge_policy": interface["discharge_policy"],
            "target_config_sha256": interface["target_config_sha256"],
            "interface_sha256": interface["interface_sha256"],
        },
    )


def _expected_role_call_identity(
    directory: Path,
    *,
    role_dir: Path,
    role: str,
) -> dict[str, str]:
    """Derive one durable call identity from the frozen campaign definition."""

    from ztare.common.llm_runtime import subscription_model_route
    from ztare.leanmill.frontier_campaign_definition import (
        load_frontier_campaign_definition,
    )

    definition = load_frontier_campaign_definition(
        directory / "campaign_definition.yaml"
    )
    prefix = role + "."
    instance = "" if role_dir.name == role else role_dir.name.removeprefix(prefix)
    if role_dir.name != role and not role_dir.name.startswith(prefix):
        raise ValueError("durable role directory crossed role identity")
    runtime = dict(definition.runtime)
    values = dict(runtime.get("defaults") or {})
    values.update(dict((runtime.get("role_overrides") or {}).get(role) or {}))
    resolved_runtime, resolved_model = subscription_model_route(
        str(values.get("model") or "gpt-5.4-mini"),
        requested_runtime=str(values.get("runtime") or "codex"),
    )
    return {
        "role": role,
        "agent_id": f"axiompack-{role}" + (f"-{instance}" if instance else ""),
        "runtime": resolved_runtime,
        "model": resolved_model,
    }


def _bounded_role_call_directories(
    directory: Path,
    role: str,
) -> tuple[Path, ...]:
    """Bound discovery before any durable role artifact is parsed or hashed."""

    rows = frontier_role_artifact_directories(directory / "agent_calls", role)
    if len(rows) > _MAX_RECOVERY_ROLE_DIRECTORIES:
        raise ValueError("construction recovery role-directory ceiling exhausted")
    file_count = 0
    aggregate_bytes = 0
    for role_dir in rows:
        for path in role_dir.iterdir():
            if path.is_symlink() or not path.is_file():
                raise ValueError(
                    "construction recovery contains a nonregular role artifact"
                )
            file_count += 1
            if file_count > _MAX_RECOVERY_ROLE_FILES:
                raise ValueError("construction recovery role-file ceiling exhausted")
            observed = path.stat().st_size
            if observed > _MAX_RECOVERY_ROLE_FILE_BYTES:
                raise ValueError(
                    "construction recovery role-file byte ceiling exhausted"
                )
            aggregate_bytes += observed
            if aggregate_bytes > _MAX_RECOVERY_ROLE_AGGREGATE_BYTES:
                raise ValueError(
                    "construction recovery aggregate byte ceiling exhausted"
                )
    return rows


def durable_witness_construction_candidates(
    directory: Path,
) -> tuple[WitnessConstructionCandidateEnvelope, ...]:
    """Return only frozen-campaign, sibling-navigator-authored candidates."""

    run = read_json(directory / "run.json", None)
    if not isinstance(run, Mapping):
        raise ValueError("durable construction recovery lacks campaign state")
    return _durable_current_constructor_candidates(
        directory, context_hash=str(run.get("context_hash") or "")
    )


def _navigator_segment_authors_candidate(
    directory: Path,
    *,
    constructor_dir: Path,
    candidate: WitnessConstructionCandidateEnvelope,
) -> bool:
    suffix = constructor_dir.name.removeprefix("witness_constructor")
    navigator_name = "navigator" + suffix
    navigators = {
        path.name: path
        for path in _bounded_role_call_directories(directory, "navigator")
    }
    navigator_dir = navigators.get(navigator_name)
    if navigator_dir is None:
        return False
    expected = _expected_role_call_identity(
        directory, role_dir=navigator_dir, role="navigator"
    )
    intent = candidate.constructor_request["task_intent"]
    for call_path in sorted(navigator_dir.glob("[0-9][0-9][0-9].call.json")):
        prefix = call_path.with_suffix("")
        receipt = read_frontier_role_call_receipt(prefix)
        if receipt.get("returncode") != 0:
            continue
        durable = read_completed_frontier_role_call(
            prefix,
            expected_role=expected["role"],
            expected_agent_id=expected["agent_id"],
            expected_runtime=expected["runtime"],
            expected_model=expected["model"],
        )
        decision = durable["result"]
        from jsonschema import Draft202012Validator
        from ztare.leanmill.axiompack_leaf_workbench import (
            navigator_decision_output_schema,
        )

        expected_schema = navigator_decision_output_schema()
        if expected["runtime"] == "codex":
            if durable["call"].get("output_schema_digest") != content_hash(
                expected_schema
            ):
                raise ValueError(
                    "durable navigator call crossed its frozen output schema"
                )
        Draft202012Validator(expected_schema).validate(decision)
        inputs = decision.get("input_refs") if isinstance(decision, Mapping) else None
        if (
            not isinstance(inputs, Mapping)
            or decision.get("decision") != "request"
            or str(decision.get("capability_id") or "").split("@", 1)[0]
            != "propose_theory_task"
        ):
            continue
        visible_refs = [
            str(value)
            for value in inputs.get("evidence_refs") or ()
            if not str(value).startswith("witness-constructor-authorship:")
        ]
        if (
            list(inputs.get("formula_ids") or ())
            == list(intent["presentation_formula_ids"])
            and str(inputs.get("goal") or "") == intent["goal"]
            and str(inputs.get("observable") or "") == intent["observable"]
            and str(inputs.get("kill_condition") or "")
            == intent["kill_condition"]
            and visible_refs == list(intent["evidence_refs"])
        ):
            return True
    return False


def _durable_current_constructor_candidates(
    directory: Path,
    *,
    context_hash: str,
) -> tuple[WitnessConstructionCandidateEnvelope, ...]:
    rows: dict[str, WitnessConstructionCandidateEnvelope] = {}
    for constructor_dir in _bounded_role_call_directories(
        directory, "witness_constructor"
    ):
        expected = _expected_role_call_identity(
            directory,
            role_dir=constructor_dir,
            role="witness_constructor",
        )
        for call_path in sorted(
            constructor_dir.glob("[0-9][0-9][0-9].call.json")
        ):
            prefix = call_path.with_suffix("")
            receipt = read_frontier_role_call_receipt(prefix)
            if receipt.get("returncode") != 0:
                continue
            durable = read_completed_frontier_role_call(
                prefix,
                expected_role=expected["role"],
                expected_agent_id=expected["agent_id"],
                expected_runtime=expected["runtime"],
                expected_model=expected["model"],
            )
            candidate = _durable_constructor_candidate(
                durable["prompt"], durable["result"], durable["call"]
            )
            if (
                candidate.context_hash == context_hash
                and _navigator_segment_authors_candidate(
                    directory,
                    constructor_dir=constructor_dir,
                    candidate=candidate,
                )
            ):
                rows[candidate.receipt_sha256] = candidate
    return tuple(rows[key] for key in sorted(rows))


def pending_cold_witness_boundary_recovery(
    directory: Path,
    run: Mapping[str, Any],
) -> bool:
    """Recognize a completed authored candidate hidden behind a stale stop."""

    return bool(_pending_cold_witness_candidates(directory, run))


def _completed_witness_coordinate_statuses(directory: Path) -> dict[str, str]:
    path = directory / "boundary_completion.json"
    if not path.exists():
        return {}
    completion = read_json(path, None)
    if not isinstance(completion, Mapping):
        raise ValueError("persisted boundary completion is malformed")
    core = {
        key: value for key, value in completion.items() if key != "completion_sha256"
    }
    if completion.get("completion_sha256") != content_hash(core):
        raise ValueError("persisted boundary completion digest mismatch")
    boundary = completion.get("boundary_result")
    if not isinstance(boundary, Mapping):
        raise ValueError("persisted boundary result is malformed")
    boundary_core = {
        key: value for key, value in boundary.items() if key != "result_sha256"
    }
    if boundary.get("result_sha256") != content_hash(boundary_core):
        raise ValueError("persisted boundary result digest mismatch")
    source_contracts: dict[str, TaskDischargeContract] = {}
    discharge = completion.get("theory_task_discharge")
    for bundle_row in (
        discharge.get("rows")
        if isinstance(discharge, Mapping)
        and isinstance(discharge.get("rows"), list)
        else ()
    ):
        contract_row = (
            bundle_row.get("contract")
            if isinstance(bundle_row, Mapping)
            else None
        )
        if not isinstance(contract_row, Mapping):
            continue
        contract = TaskDischargeContract.from_dict(contract_row)
        if bundle_row.get("contract_sha256") != contract.sha256:
            raise ValueError("persisted boundary contract digest mismatch")
        source_contracts[contract.sha256] = contract
    covered: dict[str, str] = {}
    for row in boundary.get("query_results") or ():
        if not isinstance(row, Mapping):
            raise ValueError("persisted boundary query result is malformed")
        row_core = {
            key: value for key, value in row.items() if key != "receipt_sha256"
        }
        coordinate = row.get("execution_coordinate")
        if row.get("receipt_sha256") != content_hash(row_core):
            raise ValueError("persisted boundary query result digest mismatch")
        if (
            row.get("schema") != WITNESS_CONSTRUCTION_BOUNDARY_RESULT_SCHEMA
            or row.get("candidate_kind") != "theory_task"
            or not _is_exact_protocol_discriminant(
                row.get("status"),
                (
                    "witness_rejected",
                    "witness_verified",
                    "capability_unavailable",
                ),
            )
            or row.get("authority")
            != "frontier_boundary_witness_construction_join"
        ):
            continue
        contract = source_contracts.get(str(row.get("contract_sha256") or ""))
        if contract is None:
            continue
        try:
            validate_witness_construction_boundary_result(contract, row)
        except (KeyError, TypeError, ValueError):
            continue
        if not isinstance(coordinate, Mapping):
            continue
        coordinate_core = {
            key: value
            for key, value in coordinate.items()
            if key != "coordinate_sha256"
        }
        if (
            coordinate.get("coordinate_sha256") != content_hash(coordinate_core)
            or row.get("execution_coordinate_sha256")
            != coordinate.get("coordinate_sha256")
        ):
            raise ValueError("persisted boundary execution coordinate is malformed")
        coordinate_sha256 = str(coordinate["coordinate_sha256"])
        status = str(row["status"])
        if coordinate_sha256 in covered and covered[coordinate_sha256] != status:
            raise ValueError("persisted boundary coordinate has conflicting outcomes")
        covered[coordinate_sha256] = status
    return covered


def _validated_trace_constructor_request_refs(
    navigation: Mapping[str, Any],
    *,
    context_hash: str,
    control_nodes: list[int],
) -> set[str]:
    """Read constructor identities only from host-owned navigation receipts."""

    trace_owners: list[tuple[Mapping[str, Any], str]] = [
        (navigation, "navigation")
    ]
    for index, lineage in enumerate(
        _optional_control_sequence(
            navigation,
            "lineages",
            context="construction recovery navigation",
        )
    ):
        _consume_recovery_control_nodes(control_nodes)
        if not isinstance(lineage, Mapping):
            continue
        lineage_navigation = lineage.get("navigation")
        if lineage_navigation is None:
            continue
        if not isinstance(lineage_navigation, Mapping):
            raise ValueError(
                "construction recovery lineage navigation must be an object"
            )
        trace_owners.append(
            (lineage_navigation, f"construction recovery lineage {index}")
        )

    refs: set[str] = set()
    for owner, context in trace_owners:
        trace = _optional_control_sequence(owner, "trace", context=context)
        for turn in trace:
            _consume_recovery_control_nodes(control_nodes)
            if not isinstance(turn, Mapping):
                continue
            receipt = turn.get("receipt")
            if (
                not isinstance(receipt, Mapping)
                or receipt.get("schema")
                != "leanmill.axiompack_workbench_receipt.v1"
                or receipt.get("capability_id") != "propose_theory_task"
                or receipt.get("context_hash") != context_hash
                or receipt.get("authority") != "deterministic_host"
            ):
                continue
            if (
                set(receipt)
                != {
                    "schema",
                    "capability_id",
                    "context_hash",
                    "input_hashes",
                    "output_summary",
                    "claim_bindings",
                    "authority",
                    "receipt_id",
                }
                or not isinstance(receipt.get("input_hashes"), Mapping)
                or receipt.get("claim_bindings") != ["propose_theory_task"]
            ):
                raise ValueError(
                    "construction recovery workbench receipt fields changed identity"
                )
            receipt_core = {
                key: value
                for key, value in receipt.items()
                if key != "receipt_id"
            }
            if receipt.get("receipt_id") != "sha256:" + content_hash(
                receipt_core
            ):
                raise ValueError(
                    "construction recovery workbench receipt digest mismatch"
                )
            summary = receipt.get("output_summary")
            if not isinstance(summary, Mapping):
                continue
            request = summary.get("task_request")
            if not isinstance(request, Mapping):
                continue
            request_core = {
                key: value
                for key, value in request.items()
                if key != "request_id"
            }
            if (
                request.get("schema") != "leanmill.theory_task_request.v1"
                or request.get("authority") != "leaf_request_host_bound"
                or request.get("context_hash") != context_hash
                or request.get("adjudicator_capability")
                != "governed_witness_construction"
                or request.get("request_id")
                != "theory-task-request:" + content_hash(request_core)
            ):
                raise ValueError(
                    "construction recovery theory-task request failed host binding"
                )
            witness = request.get("witness_construction")
            constructor_request = (
                witness.get("constructor_request")
                if isinstance(witness, Mapping)
                else None
            )
            if not isinstance(constructor_request, Mapping):
                continue
            try:
                frozen_request = validate_witness_constructor_request(
                    constructor_request
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    "construction recovery constructor request is malformed"
                ) from exc
            if frozen_request.get("context_hash") != context_hash:
                raise ValueError(
                    "construction recovery constructor request crossed context"
                )
            refs.add(str(frozen_request["request_sha256"]))
    return refs


def _validated_program_coordinate_refs(
    navigation: Mapping[str, Any],
    *,
    context_hash: str,
    control_nodes: list[int],
) -> set[str]:
    """Read task coordinates only from validated current program owner slots."""

    refs: set[str] = set()
    owners: list[tuple[Mapping[str, Any], tuple[str, ...], str]] = [
        (
            navigation,
            ("finalists", "objective_survivors", "deferred_finalists"),
            "construction recovery navigation",
        )
    ]
    for index, lineage in enumerate(
        _optional_control_sequence(
            navigation,
            "lineages",
            context="construction recovery navigation",
        )
    ):
        _consume_recovery_control_nodes(control_nodes)
        if not isinstance(lineage, Mapping):
            continue
        lineage_navigation = lineage.get("navigation")
        if lineage_navigation is None:
            continue
        if not isinstance(lineage_navigation, Mapping):
            raise ValueError(
                "construction recovery lineage navigation must be an object"
            )
        owners.append(
            (
                lineage_navigation,
                ("finalists",),
                f"construction recovery lineage {index}",
            )
        )

    for owner, fields, context in owners:
        for field in fields:
            rows = _optional_control_sequence(
                owner,
                field,
                context=context,
            )
            for raw in rows:
                _consume_recovery_control_nodes(control_nodes)
                if not isinstance(raw, Mapping):
                    continue
                raw_program = raw.get("theory_program")
                if not isinstance(raw_program, Mapping):
                    continue
                raw_tasks = raw_program.get("task_discharge_contracts")
                if isinstance(raw_tasks, (list, tuple)):
                    _consume_recovery_control_nodes(
                        control_nodes,
                        len(raw_tasks),
                    )
                try:
                    program = TheoryProgram.from_json(raw_program)
                except (KeyError, TypeError, ValueError):
                    continue
                supplied_program_id = raw.get("theory_program_id")
                if (
                    (
                        supplied_program_id is not None
                        and supplied_program_id != program.program_id
                    )
                    or program.context_hash != context_hash
                ):
                    continue
                for contract in program.task_discharge_contracts:
                    coordinate = witness_execution_coordinate_from_contract(
                        contract.to_dict()
                    )
                    if coordinate is not None:
                        refs.add(str(coordinate["coordinate_sha256"]))
    return refs


def _pending_cold_witness_candidates(
    directory: Path,
    run: Mapping[str, Any],
) -> tuple[WitnessConstructionCandidateEnvelope, ...]:
    """Return only current, navigator-authored, not-yet-executed candidates."""

    if not isinstance(run, Mapping) or run.get("status") != "budget_stopped":
        return ()
    context_hash = str(run.get("context_hash") or "")
    candidates = _durable_current_constructor_candidates(
        directory,
        context_hash=context_hash,
    )
    if not candidates:
        return ()

    navigation = run.get("navigation")
    control_nodes = [0]
    _consume_recovery_control_nodes(control_nodes, len(candidates))
    if isinstance(navigation, Mapping):
        active_request_refs = _validated_trace_constructor_request_refs(
            navigation,
            context_hash=context_hash,
            control_nodes=control_nodes,
        )
        active_coordinate_refs = _validated_program_coordinate_refs(
            navigation,
            context_hash=context_hash,
            control_nodes=control_nodes,
        )
    else:
        active_request_refs = set()
        active_coordinate_refs = set()
    if active_request_refs:
        candidates = tuple(
            candidate
            for candidate in candidates
            if candidate.constructor_request["request_sha256"]
            in active_request_refs
        )
    if active_coordinate_refs:
        candidates = tuple(
            candidate
            for candidate in candidates
            if candidate.execution_coordinate["coordinate_sha256"]
            in active_coordinate_refs
        )
    completed = _completed_witness_coordinate_statuses(directory)
    navigation_object = navigation if isinstance(navigation, Mapping) else {}
    raw_history = navigation_object.get("objective_review_history")
    history = raw_history if isinstance(raw_history, (list, tuple)) else ()
    _consume_recovery_control_nodes(control_nodes, len(history))
    consumed = {
        str(row.get("execution_coordinate_sha256") or "")
        for row in history
        if isinstance(row, Mapping)
        and row.get("schema") == RECOVERED_BOUNDARY_FEEDBACK_SCHEMA
    }
    return tuple(
        candidate
        for candidate in candidates
        if (
            candidate.execution_coordinate["coordinate_sha256"] not in completed
            or completed[candidate.execution_coordinate["coordinate_sha256"]]
            == "capability_unavailable"
            or candidate.execution_coordinate["coordinate_sha256"] not in consumed
        )
    )


def _role_output_inventory(directory: Path) -> tuple[tuple[str, str], ...]:
    root = directory / "agent_calls"
    role_dirs = tuple(
        path
        for role in ("navigator", "witness_constructor")
        for path in _bounded_role_call_directories(directory, role)
    )
    if len(role_dirs) > _MAX_RECOVERY_ROLE_DIRECTORIES:
        raise ValueError("construction recovery role-directory ceiling exhausted")
    rows: list[tuple[str, str]] = []
    total_bytes = 0
    for role_dir in role_dirs:
        for path in role_dir.iterdir():
            if path.is_symlink() or not path.is_file():
                raise ValueError("role output inventory contains a nonregular artifact")
            if len(rows) >= _MAX_RECOVERY_ROLE_FILES:
                raise ValueError("construction recovery role-file ceiling exhausted")
            observed = path.stat().st_size
            if observed > _MAX_RECOVERY_ROLE_FILE_BYTES:
                raise ValueError("construction recovery role-file byte ceiling exhausted")
            total_bytes += observed
            if total_bytes > _MAX_RECOVERY_ROLE_AGGREGATE_BYTES:
                raise ValueError(
                    "construction recovery aggregate byte ceiling exhausted"
                )
            rows.append((str(path.relative_to(root)), sha256_file(path)))
    return tuple(sorted(rows))


def _is_sha256_hex(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _source_recovery_rollback_reconciliation(
    directory: Path,
    source_run: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    navigation = source_run.get("navigation")
    row = (
        navigation.get("construction_recovery_rollback_reconciliation")
        if isinstance(navigation, Mapping)
        else None
    )
    if row is None:
        return None
    if not isinstance(row, Mapping):
        raise ValueError("construction recovery rollback provenance is malformed")
    core = {key: value for key, value in row.items() if key != "receipt_sha256"}
    required = {
        "schema",
        "source_run_sha256",
        "source_budget_stop_receipt_sha256",
        "latest_budget_stop_receipt_sha256",
        "prior_reconciliation_receipt_sha256",
        "orphaned_activation_receipt_sha256s",
        "provider_calls_before",
        "provider_calls_after",
        "authority",
        "receipt_sha256",
    }
    orphaned = row.get("orphaned_activation_receipt_sha256s")
    prior = row.get("prior_reconciliation_receipt_sha256")
    if (
        set(row) != required
        or row.get("schema") != CONSTRUCTION_RECOVERY_ROLLBACK_SCHEMA
        or row.get("authority")
        != "reviewed_construction_campaign_transition"
        or row.get("receipt_sha256") != content_hash(core)
        or not _is_sha256_hex(row.get("source_run_sha256"))
        or not _is_sha256_hex(row.get("source_budget_stop_receipt_sha256"))
        or not _is_sha256_hex(row.get("latest_budget_stop_receipt_sha256"))
        or not isinstance(prior, str)
        or (prior != "" and not _is_sha256_hex(prior))
        or not isinstance(orphaned, list)
        or any(not _is_sha256_hex(value) for value in orphaned)
        or orphaned != sorted(set(orphaned))
        or type(row.get("provider_calls_before")) is not int
        or type(row.get("provider_calls_after")) is not int
    ):
        raise ValueError("construction recovery rollback provenance is invalid")
    slot = _read_bounded_authority_slot(
        directory
        / (
            "construction_recovery_rollback_reconciliation."
            f"{str(row['receipt_sha256'])[:16]}.json"
        ),
        max_bytes=_MAX_CONSTRUCTION_AUTHORITY_SLOT_BYTES,
        context="construction recovery rollback reconciliation",
    )
    if slot is None or slot[0] != dict(row):
        raise ValueError("construction recovery rollback provenance is not frozen")
    return dict(row)


def _validated_latest_recovery_stop(
    ledger: ExplorationBudgetLedger,
    budget: ExplorationBudget,
    *,
    attempt_id: str,
    context_hash: str,
) -> BudgetStopReceipt:
    latest = ledger.latest_stop_receipt()
    state = ledger.state()
    if (
        latest is None
        or latest.schema != "leanmill.budget_stop_receipt.v1"
        or latest.budget_digest != budget.digest
        or latest.attempt_id != attempt_id
        or latest.context_hash != context_hash
        or dict(latest.usage) != dict(state["usage"])
        or dict(latest.phase_usage) != dict(state["phase_usage"])
    ):
        raise ValueError("construction recovery latest budget stop is invalid")
    return latest


def _validated_recovery_activation_artifact(
    directory: Path,
    receipt_sha256: str,
) -> Mapping[str, Any]:
    if not _is_sha256_hex(receipt_sha256):
        raise ValueError("construction recovery activation digest is malformed")
    slot = _read_bounded_authority_slot(
        directory
        / (
            "construction_boundary_recovery_activation."
            f"{receipt_sha256[:16]}.json"
        ),
        max_bytes=_MAX_CONSTRUCTION_AUTHORITY_SLOT_BYTES,
        context="construction boundary recovery activation",
    )
    row = slot[0] if slot is not None else None
    core = (
        {key: value for key, value in row.items() if key != "receipt_sha256"}
        if isinstance(row, Mapping)
        else {}
    )
    if (
        not isinstance(row, Mapping)
        or row.get("schema")
        != "leanmill.construction_boundary_recovery_activation.v1"
        or row.get("receipt_sha256") != receipt_sha256
        or receipt_sha256 != content_hash(core)
    ):
        raise ValueError("construction recovery activation artifact is invalid")
    return dict(row)


def _restore_recovery_read_model_after_failure(
    directory: Path,
    *,
    source_run: Mapping[str, Any],
    source_stop: BudgetStopReceipt,
    ledger: ExplorationBudgetLedger,
    budget: ExplorationBudget,
    recovery_activation: Mapping[str, Any] | None,
) -> None:
    """Project the append-only ledger head without erasing source provenance."""

    latest = _validated_latest_recovery_stop(
        ledger,
        budget,
        attempt_id=directory.name,
        context_hash=str(source_run.get("context_hash") or ""),
    )
    prior = _source_recovery_rollback_reconciliation(directory, source_run)
    current_activation_sha256 = (
        str(recovery_activation.get("receipt_sha256") or "")
        if isinstance(recovery_activation, Mapping)
        else ""
    )
    if latest.to_json() == source_stop.to_json() and not current_activation_sha256:
        write_json_atomic(directory / "run.json", dict(source_run))
        write_json_atomic(
            directory / "budget_stop_receipt.json", source_stop.to_json()
        )
        return
    orphaned = set(
        prior.get("orphaned_activation_receipt_sha256s") or ()
        if isinstance(prior, Mapping)
        else ()
    )
    if current_activation_sha256:
        _validated_recovery_activation_artifact(
            directory, current_activation_sha256
        )
        orphaned.add(current_activation_sha256)
    reconciliation_core = {
        "schema": CONSTRUCTION_RECOVERY_ROLLBACK_SCHEMA,
        "source_run_sha256": str(source_run["run_digest"]),
        "source_budget_stop_receipt_sha256": str(
            source_stop.to_json()["receipt_sha256"]
        ),
        "latest_budget_stop_receipt_sha256": str(
            latest.to_json()["receipt_sha256"]
        ),
        "prior_reconciliation_receipt_sha256": (
            str(prior["receipt_sha256"]) if isinstance(prior, Mapping) else ""
        ),
        "orphaned_activation_receipt_sha256s": sorted(orphaned),
        "provider_calls_before": int(source_stop.usage["provider_calls"]),
        "provider_calls_after": int(latest.usage["provider_calls"]),
        "authority": "reviewed_construction_campaign_transition",
    }
    reconciliation = {
        **reconciliation_core,
        "receipt_sha256": content_hash(reconciliation_core),
    }
    _persist_exact(
        directory
        / (
            "construction_recovery_rollback_reconciliation."
            f"{reconciliation['receipt_sha256'][:16]}.json"
        ),
        reconciliation,
        context="construction recovery rollback reconciliation",
    )
    source_navigation = source_run.get("navigation")
    navigation = (
        dict(source_navigation) if isinstance(source_navigation, Mapping) else {}
    )
    navigation.pop("construction_boundary_recovery_activation", None)
    navigation["construction_recovery_rollback_reconciliation"] = reconciliation
    rollback_core = {
        **{key: value for key, value in source_run.items() if key != "run_digest"},
        "status": "budget_stopped",
        "provider_calls": int(latest.usage["provider_calls"]),
        "budget_stop_receipt": latest.to_json(),
        "navigation": navigation,
    }
    write_json_atomic(
        directory / "run.json",
        {**rollback_core, "run_digest": content_hash(rollback_core)},
    )
    write_json_atomic(directory / "budget_stop_receipt.json", latest.to_json())


def recover_cold_witness_boundary(
    directory: Path,
    *,
    materialize_fn: Callable[[Path, str], Any],
    verify_fn: Callable[[Path], Mapping[str, Any]],
) -> dict[str, Any]:
    """Replay authored bytes and execute their registered boundary provider-free."""

    source_run = read_json(directory / "run.json", None)
    source_core = (
        {key: value for key, value in source_run.items() if key != "run_digest"}
        if isinstance(source_run, Mapping)
        else {}
    )
    if (
        not isinstance(source_run, Mapping)
        or source_run.get("run_digest") != content_hash(source_core)
        or not pending_cold_witness_boundary_recovery(directory, source_run)
    ):
        raise ValueError("cold witness recovery has no pending durable candidate")
    candidates = _pending_cold_witness_candidates(directory, source_run)
    durable_coordinates = {
        row.execution_coordinate["coordinate_sha256"]: row.execution_coordinate
        for row in candidates
    }
    inventory_before = _role_output_inventory(directory)
    budget = ExplorationBudget.from_json(read_json(directory / "budget.json", {}))
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl", budget, attempt_id=directory.name
    )
    raw_stop = source_run.get("budget_stop_receipt")
    persisted_stop = read_json(directory / "budget_stop_receipt.json", None)
    if (
        source_run.get("status") != "budget_stopped"
        or not isinstance(raw_stop, Mapping)
        or not isinstance(persisted_stop, Mapping)
        or dict(persisted_stop) != dict(raw_stop)
    ):
        raise ValueError("cold witness recovery lost its source budget stop")
    source_stop = BudgetStopReceipt.from_json(raw_stop)
    latest_stop = ledger.latest_stop_receipt()
    ledger_state = ledger.state()
    if (
        source_stop.schema != "leanmill.budget_stop_receipt.v1"
        or latest_stop is None
        or latest_stop.to_json() != source_stop.to_json()
        or not source_stop.reason.strip()
        or source_stop.budget_digest != budget.digest
        or source_run.get("budget_digest") != budget.digest
        or source_stop.attempt_id != directory.name
        or source_stop.context_hash != source_run.get("context_hash")
        or dict(source_stop.usage) != dict(ledger_state["usage"])
        or dict(source_stop.phase_usage) != dict(ledger_state["phase_usage"])
        or int(source_run.get("provider_calls", -1))
        != int(source_stop.usage["provider_calls"])
    ):
        raise ValueError("cold witness recovery budget stop changed identity")
    source_reconciliation = _source_recovery_rollback_reconciliation(
        directory, source_run
    )
    if (
        isinstance(source_reconciliation, Mapping)
        and int(source_reconciliation["provider_calls_before"])
        != int(source_reconciliation["provider_calls_after"])
    ):
        raise ValueError(
            "construction recovery rollback consumed provider calls"
        )
    _persist_exact(
        directory
        / (
            "construction_recovery_source_budget_stop."
            f"{source_stop.to_json()['receipt_sha256'][:16]}.json"
        ),
        source_stop.to_json(),
        context="construction recovery source budget stop",
    )
    _persist_exact(
        directory
        / (
            "construction_recovery_source_run."
            f"{str(source_run['run_digest'])[:16]}.json"
        ),
        dict(source_run),
        context="construction recovery source run",
    )
    usage_before = dict(ledger.state()["usage"])
    frozen = False
    recovery_activation: Mapping[str, Any] | None = None
    prior_completion_statuses = _completed_witness_coordinate_statuses(directory)
    try:
        materialize_fn(directory, source_stop.reason)
        rebuilt = read_json(directory / "run.json", None)
        rebuilt_core = (
            {key: value for key, value in rebuilt.items() if key != "run_digest"}
            if isinstance(rebuilt, Mapping)
            else {}
        )
        if (
            not isinstance(rebuilt, Mapping)
            or rebuilt.get("run_digest") != content_hash(rebuilt_core)
        ):
            raise ValueError("construction recovery did not rebuild campaign state")
        rebuilt_stop_raw = rebuilt.get("budget_stop_receipt")
        rebuilt_stop = (
            BudgetStopReceipt.from_json(rebuilt_stop_raw)
            if isinstance(rebuilt_stop_raw, Mapping)
            else None
        )
        latest_rebuilt_stop = ledger.latest_stop_receipt()
        if (
            rebuilt.get("status") != "budget_stopped"
            or rebuilt_stop is None
            or latest_rebuilt_stop is None
            or latest_rebuilt_stop.to_json() != rebuilt_stop.to_json()
            or rebuilt_stop.reason != source_stop.reason
        ):
            raise ValueError(
                "construction recovery materialization lost its budget stop"
            )
        rebuilt_core["status"] = "budget_stopped"
        rebuilt_core["budget_stop_receipt"] = source_stop.to_json()
        rebuilt = {
            **rebuilt_core,
            "run_digest": content_hash(rebuilt_core),
        }
        write_json_atomic(directory / "run.json", rebuilt)
        write_json_atomic(
            directory / "budget_stop_receipt.json", source_stop.to_json()
        )
        rebuilt_coordinates = {
            coordinate["coordinate_sha256"]: coordinate
            for finalist in (rebuilt.get("navigation") or {}).get("finalists") or ()
            if isinstance(finalist, Mapping)
            and isinstance(finalist.get("theory_program"), Mapping)
            for contract in finalist["theory_program"].get(
                "task_discharge_contracts", ()
            )
            if isinstance(contract, Mapping)
            for coordinate in [witness_execution_coordinate_from_contract(contract)]
            if coordinate is not None
        }
        missing_coordinates = sorted(
            set(durable_coordinates) - set(rebuilt_coordinates)
        )
        if missing_coordinates:
            raise ValueError(
                "durable constructor coordinates were lost during materialization: "
                + ",".join(missing_coordinates)
            )
        matching = sorted(durable_coordinates)
        verification_required = not matching or any(
            not _is_exact_protocol_discriminant(
                prior_completion_statuses.get(coordinate),
                ("witness_rejected", "witness_verified"),
            )
            for coordinate in matching
        )
        if verification_required:
            activation_core = {
                "schema": "leanmill.construction_boundary_recovery_activation.v1",
                "source_run_sha256": str(source_run["run_digest"]),
                "rebuilt_run_sha256": str(rebuilt["run_digest"]),
                "source_budget_stop_receipt_sha256": str(
                    source_stop.to_json()["receipt_sha256"]
                ),
                "latest_budget_stop_receipt_sha256": str(
                    rebuilt_stop.to_json()["receipt_sha256"]
                ),
                "execution_coordinate_sha256s": matching,
                "executor_kind": "data_only_witness_construction",
                "authority": "reviewed_construction_campaign_transition",
            }
            activation = {
                **activation_core,
                "receipt_sha256": content_hash(activation_core),
            }
            recovery_activation = activation
            _persist_exact(
                directory
                / (
                    "construction_boundary_recovery_activation."
                    f"{activation['receipt_sha256'][:16]}.json"
                ),
                activation,
                context="construction boundary recovery activation",
            )
            activated_navigation = dict(rebuilt.get("navigation") or {})
            activated_navigation[
                "construction_boundary_recovery_activation"
            ] = activation
            activated_core = {
                **rebuilt_core,
                "status": "budget_stopped",
                "navigation": activated_navigation,
                "budget_stop_receipt": source_stop.to_json(),
            }
            write_json_atomic(
                directory / "run.json",
                {
                    **activated_core,
                    "run_digest": content_hash(activated_core),
                },
            )
            verify_fn(directory)
        boundary_run = read_json(directory / "run.json", None)
        if not isinstance(boundary_run, Mapping):
            raise ValueError("construction boundary did not persist campaign state")
        navigation = bind_recovered_boundary_artifact_feedback(
            directory, boundary_run.get("navigation") or {}
        )
        feedback_rows = [
            row
            for row in navigation.get("objective_review_history") or ()
            if isinstance(row, Mapping)
            and row.get("schema") == RECOVERED_BOUNDARY_FEEDBACK_SCHEMA
            and row.get("execution_coordinate_sha256") in matching
        ]
        feedback_coordinates = {
            str(row["execution_coordinate_sha256"]) for row in feedback_rows
        }
        if feedback_coordinates != set(matching):
            raise ValueError(
                "registered construction boundary did not cover every admitted coordinate"
            )
        completion = read_json(directory / "boundary_completion.json", None)
        if not isinstance(completion, Mapping):
            raise ValueError("registered construction boundary completion is missing")
        final_stop = _validated_latest_recovery_stop(
            ledger,
            budget,
            attempt_id=directory.name,
            context_hash=str(source_run.get("context_hash") or ""),
        )
        active_activation = navigation.pop(
            "construction_boundary_recovery_activation", None
        )
        orphaned_activation_sha256s = sorted(
            set(
                source_reconciliation.get(
                    "orphaned_activation_receipt_sha256s", ()
                )
                if isinstance(source_reconciliation, Mapping)
                else ()
            )
        )
        if recovery_activation is not None:
            if active_activation != recovery_activation:
                raise ValueError(
                    "construction boundary recovery activation changed before consumption"
                )
        elif active_activation is not None:
            raise ValueError("unowned construction recovery activation survived")
        active_activation_sha256 = (
            str(recovery_activation["receipt_sha256"])
            if recovery_activation is not None
            else ""
        )
        audited_activation_sha256s = sorted(
            set(orphaned_activation_sha256s)
            | ({active_activation_sha256} if active_activation_sha256 else set())
        )
        if audited_activation_sha256s:
            for activation_sha256 in audited_activation_sha256s:
                _validated_recovery_activation_artifact(
                    directory, activation_sha256
                )
            consumption_core = {
                "schema": (
                    "leanmill.construction_boundary_recovery_activation_consumed.v1"
                ),
                "active_activation_receipt_sha256": active_activation_sha256,
                "orphaned_activation_receipt_sha256s": (
                    orphaned_activation_sha256s
                ),
                "audited_activation_receipt_sha256s": (
                    audited_activation_sha256s
                ),
                "boundary_completion_sha256": str(
                    completion.get("completion_sha256") or ""
                ),
                "execution_coordinate_sha256s": matching,
                "rollback_reconciliation_receipt_sha256": (
                    str(source_reconciliation["receipt_sha256"])
                    if isinstance(source_reconciliation, Mapping)
                    else ""
                ),
                "authority": "reviewed_construction_campaign_transition",
            }
            consumption = {
                **consumption_core,
                "receipt_sha256": content_hash(consumption_core),
            }
            _persist_exact(
                directory
                / (
                    "construction_boundary_recovery_activation_consumed."
                    f"{consumption['receipt_sha256'][:16]}.json"
                ),
                consumption,
                context="construction boundary recovery activation consumption",
            )
            navigation[
                "construction_boundary_recovery_activation_consumed"
            ] = consumption
        if isinstance(source_reconciliation, Mapping):
            navigation[
                "construction_recovery_rollback_reconciliation"
            ] = dict(source_reconciliation)
        status = (
            str(boundary_run.get("status") or "")
            if any(row.get("status") == "witness_verified" for row in feedback_rows)
            else "budget_stopped"
        )
        run_core = {
            **{
                key: value
                for key, value in boundary_run.items()
                if key != "run_digest"
            },
            "status": status,
            "navigation": navigation,
        }
        if status == "budget_stopped":
            run_core["budget_stop_receipt"] = final_stop.to_json()
            run_core["provider_calls"] = int(
                final_stop.usage["provider_calls"]
            )
        updated = {**run_core, "run_digest": content_hash(run_core)}
        frozen_elapsed_ms = ledger.freeze_wall_clock(
            reason="reviewed_construction_recovery_transition"
        )
        frozen = True
        frozen_budget_state = ledger.state()
        transition_core = {
            "schema": CONSTRUCTION_RECOVERY_TRANSITION_SCHEMA,
            "source_run_sha256": str(source_run.get("run_digest") or ""),
            "recovered_run_sha256": updated["run_digest"],
            "boundary_completion_sha256": str(
                completion.get("completion_sha256") or ""
            ),
            "source_budget_stop_receipt_sha256": str(
                source_stop.to_json()["receipt_sha256"]
            ),
            "final_budget_stop_receipt_sha256": str(
                final_stop.to_json()["receipt_sha256"]
            ),
            "rollback_reconciliation_receipt_sha256": (
                str(source_reconciliation["receipt_sha256"])
                if isinstance(source_reconciliation, Mapping)
                else ""
            ),
            "execution_coordinate_sha256s": matching,
            "feedback_receipt_sha256s": sorted(
                str(row["receipt_sha256"]) for row in feedback_rows
            ),
            "provider_calls_before": int(usage_before["provider_calls"]),
            "provider_calls_after": int(ledger.state()["usage"]["provider_calls"]),
            "frozen_elapsed_ms": int(frozen_elapsed_ms),
            "frozen_budget_state_sha256": content_hash(frozen_budget_state),
            "navigator_constructor_outputs_unchanged": (
                inventory_before == _role_output_inventory(directory)
            ),
            "authority": "reviewed_construction_campaign_transition",
        }
        transition = {
            **transition_core,
            "receipt_sha256": content_hash(transition_core),
        }
        if transition["provider_calls_before"] != transition["provider_calls_after"]:
            raise ValueError("provider-free construction recovery consumed provider calls")
        if transition["navigator_constructor_outputs_unchanged"] is not True:
            raise ValueError("construction recovery authored new role outputs")
        _persist_exact(
            directory
            / (
                "reviewed_construction_recovery_transition."
                f"{transition['receipt_sha256'][:16]}.json"
            ),
            transition,
            context="construction recovery transition",
        )
        navigation["construction_recovery_transition"] = transition
        run_core["navigation"] = navigation
        updated = {**run_core, "run_digest": content_hash(run_core)}
        write_json_atomic(directory / "run.json", updated)
        if status == "budget_stopped":
            write_json_atomic(
                directory / "budget_stop_receipt.json", final_stop.to_json()
            )
        return transition
    except BaseException:
        # Materialization and boundary execution may publish immutable evidence,
        # but ``run.json`` is only their mutable read model.  If the transition
        # does not complete, put that projection back at the authenticated
        # source identity so the lifecycle retries this provider-free recovery
        # instead of routing the partially materialized state to navigation.
        _restore_recovery_read_model_after_failure(
            directory,
            source_run=source_run,
            source_stop=source_stop,
            ledger=ledger,
            budget=budget,
            recovery_activation=recovery_activation,
        )
        raise
    finally:
        # Boundary execution owns any reservation commits.  This owner freezes
        # elapsed time before control can return to navigation.
        if not frozen:
            ledger.freeze_wall_clock(reason="reviewed_construction_recovery_exit")


def validate_persisted_family_execution_slot(
    path: Path,
    *,
    family_receipt_sha256: str,
    aggregate_budget: dict[str, int] | None = None,
) -> Mapping[str, Any] | None:
    """Fail closed on every occupied content-addressed execution conflict."""

    occupied = _read_bounded_authority_slot(
        path,
        max_bytes=_MAX_CONSTRUCTION_AUTHORITY_SLOT_BYTES,
        context="content-addressed family execution",
    )
    if occupied is None:
        return None
    row, observed = occupied
    if aggregate_budget is not None:
        total = int(aggregate_budget.get("bytes", 0)) + observed
        if total > _MAX_FAMILY_EXECUTION_REPLAY_AGGREGATE_BYTES:
            raise ValueError(
                "finite family execution replay aggregate byte ceiling exhausted"
            )
        aggregate_budget["bytes"] = total
    if row.get("family_receipt_sha256") != family_receipt_sha256:
        raise ValueError("content-addressed family execution crossed family identity")
    return row


def _persisted_parameterization_execution(
    directory: Path,
    *,
    parameterization: Mapping[str, Any],
    witness_schema: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    """Read the parameterization-owned slot, with one bounded legacy migration."""

    from ztare.leanmill.construction_parameterization import (
        validate_construction_parameterization_execution,
    )

    parameterization_sha256 = str(parameterization["receipt_sha256"])
    current_path = directory / (
        "construction_parameterization_execution_by_parameterization_"
        + parameterization_sha256[:16]
        + ".json"
    )
    maximum = int(
        parameterization["resource_limits"]["max_execution_receipt_bytes"]
    )
    occupied = _read_bounded_authority_slot(
        current_path,
        max_bytes=maximum,
        context="construction execution",
    )
    if occupied is not None:
        raw, _observed = occupied
        return validate_construction_parameterization_execution(
            raw,
            parameterization=parameterization,
            witness_schema=witness_schema,
        )

    legacy_paths: list[Path] = []
    root_entries = 0
    aggregate_bytes = 0
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("construction attempt directory is unavailable")
    with os.scandir(directory) as entries:
        for entry in entries:
            root_entries += 1
            if root_entries > _MAX_ATTEMPT_ROOT_ENTRIES:
                raise ValueError("construction attempt root-entry ceiling exhausted")
            name = entry.name
            if not (
                name.startswith("construction_parameterization_execution.")
                and name.endswith(".json")
            ):
                continue
            if len(legacy_paths) >= _MAX_LEGACY_PARAMETERIZATION_EXECUTIONS:
                raise ValueError(
                    "legacy construction execution file ceiling exhausted"
                )
            legacy_paths.append(Path(entry.path))

    matches: list[Mapping[str, Any]] = []
    for path in sorted(legacy_paths):
        occupied = _read_bounded_authority_slot(
            path,
            max_bytes=maximum,
            context="legacy construction execution",
        )
        if occupied is None:
            raise ValueError("legacy construction execution disappeared")
        raw, observed = occupied
        aggregate_bytes += observed
        if aggregate_bytes > _MAX_LEGACY_PARAMETERIZATION_EXECUTION_BYTES:
            raise ValueError(
                "legacy construction execution aggregate byte ceiling exhausted"
            )
        frozen = validate_construction_parameterization_execution(raw)
        expected_name = (
            "construction_parameterization_execution."
            + str(frozen["receipt_sha256"])[:16]
            + ".json"
        )
        if path.name != expected_name:
            raise ValueError("construction execution crossed content-addressed slot")
        if frozen["parameterization_sha256"] == parameterization_sha256:
            matches.append(
                validate_construction_parameterization_execution(
                    frozen,
                    parameterization=parameterization,
                    witness_schema=witness_schema,
                )
            )
    identities = {str(row["receipt_sha256"]) for row in matches}
    if len(identities) > 1:
        raise ValueError("parameterization has multiple persisted executions")
    if not matches:
        return None
    migrated = matches[0]
    _persist_exact(
        current_path,
        migrated,
        context="migrated construction parameterization execution",
    )
    return migrated


def admit_persisted_construction_origin_for_campaign(
    directory: Path,
    *,
    parameterization_sha256: str,
    parameterization_execution_sha256: str,
    forge_quarantine_receipt: Mapping[str, Any],
    witness_interface: Mapping[str, Any],
    budget_ledger: ExplorationBudgetLedger,
):
    """Mint the one cold runtime origin under its original budget identity."""

    from ztare.leanmill.adapter_forge import (
        validate_reviewed_construction_parameterization_bytes_authority,
    )
    from ztare.leanmill.construction_parameterization import (
        ConstructionBackendCapabilityUnavailable,
        ConstructionResourceCeilingExceeded,
    )
    from ztare.leanmill.finite_construction_family import (
        admit_construction_origin,
    )

    parameterization_ref = str(parameterization_sha256)
    execution_ref = str(parameterization_execution_sha256)
    if (
        len(parameterization_ref) != 64
        or len(execution_ref) != 64
        or any(character not in "0123456789abcdef" for character in parameterization_ref)
        or any(character not in "0123456789abcdef" for character in execution_ref)
    ):
        raise ValueError("construction origin has malformed content identities")
    parameterization_path = directory / (
        "construction_parameterization."
        + parameterization_ref[:16]
        + ".json"
    )
    occupied_parameterization = _read_bounded_authority_slot(
        parameterization_path,
        max_bytes=_MAX_CONSTRUCTION_PARAMETERIZATION_BYTES,
        context="construction origin parameterization",
    )
    if occupied_parameterization is None:
        raise ValueError("construction origin parameterization slot is unavailable")
    raw_parameterization, _observed = occupied_parameterization
    parameterization, forge = (
        validate_reviewed_construction_parameterization_bytes_authority(
            raw_parameterization,
            forge_quarantine_receipt,
            witness_interface=witness_interface,
        )
    )
    if parameterization["receipt_sha256"] != parameterization_ref:
        raise ValueError("construction origin crossed parameterization identity")
    execution = _persisted_parameterization_execution(
        directory,
        parameterization=parameterization,
        witness_schema=witness_interface["witness_schema"],
    )
    if (
        not isinstance(execution, Mapping)
        or execution.get("receipt_sha256") != execution_ref
    ):
        raise ValueError("construction origin execution identity is unavailable")

    action_id = "construction-parameterization:" + parameterization_ref
    expected_count = int(execution["expected_parameter_count"])
    already_charged = budget_ledger.has_committed_action_resources(
        action_id,
        phase="expansion",
        minimum_resources={"workbench_actions": expected_count},
    )
    reservation = None
    if not already_charged:
        reservation = budget_ledger.reserve(
            action_id,
            "expansion",
            {
                "workbench_actions": int(
                    parameterization["resource_limits"]["max_assignments"]
                )
            },
        )
    try:
        origin = admit_construction_origin(
            parameterization=parameterization,
            forge_quarantine_receipt=forge,
            parameterization_execution=execution,
            witness_interface=witness_interface,
        )
    except (
        ConstructionResourceCeilingExceeded,
        ConstructionBackendCapabilityUnavailable,
    ) as exc:
        if reservation is not None:
            attempted = int(
                getattr(exc, "attempted_assignment_count", expected_count)
            )
            ceiling = int(
                parameterization["resource_limits"]["max_assignments"]
            )
            if not 0 <= attempted <= ceiling:
                attempted = ceiling
            budget_ledger.commit(
                reservation,
                {"workbench_actions": attempted},
            )
        raise
    except Exception:
        if reservation is not None:
            budget_ledger.commit(
                reservation,
                {
                    "workbench_actions": int(
                        parameterization["resource_limits"]["max_assignments"]
                    )
                },
            )
        raise
    else:
        if reservation is not None:
            budget_ledger.commit(
                reservation,
                {"workbench_actions": expected_count},
            )
    return origin


def _finish_advancement_transition(
    directory: Path,
    *,
    ledger: ExplorationBudgetLedger,
    result: Mapping[str, Any],
    context_hash: str,
    adapter_id: str,
    identity_ref: str,
    resume_fn: Callable[..., Any] | None,
    _attempt_lease: Any,
) -> dict[str, Any]:
    """Freeze and persist one owned transition before optional navigation resume."""

    frozen_elapsed_ms = ledger.freeze_wall_clock(
        reason="reviewed_construction_advancement_transition"
    )
    budget_state = ledger.state()
    transition_core = {
        "schema": CONSTRUCTION_ADVANCEMENT_TRANSITION_SCHEMA,
        "status": str(result.get("status") or ""),
        "context_hash": str(context_hash),
        "adapter_id": str(adapter_id),
        "identity_ref": str(identity_ref),
        "result_sha256": content_hash(dict(result)),
        "frozen_elapsed_ms": int(frozen_elapsed_ms),
        "frozen_budget_state_sha256": content_hash(budget_state),
        "authority": "reviewed_construction_campaign_transition",
    }
    transition = {
        **transition_core,
        "receipt_sha256": content_hash(transition_core),
    }
    _persist_exact(
        directory
        / (
            "reviewed_construction_advancement_transition."
            + str(transition["receipt_sha256"])[:16]
            + ".json"
        ),
        transition,
        context="reviewed construction advancement transition",
    )
    enriched = {
        **dict(result),
        "transition_receipt_sha256": transition["receipt_sha256"],
    }
    if resume_fn is not None:
        resume_fn(directory, _attempt_lease=_attempt_lease)
    return enriched


def advance_reviewed_construction_campaign(
    directory: Path,
    *,
    completion: Mapping[str, Any],
    run: Mapping[str, Any],
    blueprint: Any,
    resume_fn: Callable[..., Any] | None,
    _attempt_lease: Any,
    hooks: ReviewedConstructionHooks,
) -> dict[str, Any] | None:
    """Advance a reviewed parameterization/family through one owned lifecycle."""

    parameterization, parameterization_forge_receipt = (
        hooks.approved_parameterization(directory, completion)
    )
    construction_origin = None
    family = None
    family_forge_receipt = None
    if parameterization is not None:
        from ztare.leanmill.construction_parameterization import (
            ConstructionBackendCapabilityUnavailable,
            ConstructionResourceCeilingExceeded,
            admit_construction_parameterization,
            admit_persisted_construction_execution,
            execute_construction_parameterization,
        )
        from ztare.leanmill.finite_construction_family import (
            admit_construction_origin,
            construction_witness_interface,
            lower_reviewed_construction_parameterization,
        )

        interface = construction_witness_interface(
            str(blueprint.adapter_id), dict(blueprint.adapter_config)
        )
        if not isinstance(parameterization_forge_receipt, Mapping):
            raise ValueError(
                "reviewed construction parameterization lacks Forge authority"
            )

        parameterization_budget = ExplorationBudget.from_json(
            read_json(directory / "budget.json", {})
        )
        parameterization_ledger = ExplorationBudgetLedger(
            directory / "budget.events.jsonl",
            parameterization_budget,
            attempt_id=directory.name,
        )
        parameterization_ledger.recover_interrupted_wall_clock()
        parameterization_ledger.recover_interrupted_reservations()
        parameterization_ledger.resume_wall_clock()
        parameterization_phase = "expansion"
        parameterization_execution = None
        admitted_parameterization = None
        parameterization_exit: dict[str, Any] | None = None
        reservation = None
        certified_count = 0
        try:
            _persist_exact(
                directory
                / (
                    "construction_parameterization."
                    + str(parameterization["receipt_sha256"])[:16]
                    + ".json"
                ),
                parameterization,
                context="construction parameterization",
            )
            parameterization_execution = _persisted_parameterization_execution(
                directory,
                parameterization=parameterization,
                witness_schema=interface["witness_schema"],
            )
            replaying_execution = parameterization_execution is not None
            declared_ceiling = int(
                parameterization["resource_limits"]["max_assignments"]
            )
            parameterization_action_id = (
                "construction-parameterization:"
                + str(parameterization["receipt_sha256"])
            )
            try:
                replay_already_charged = bool(
                    replaying_execution
                    and parameterization_ledger.has_committed_action_resources(
                        parameterization_action_id,
                        phase=parameterization_phase,
                        minimum_resources={
                            "workbench_actions": int(
                                parameterization_execution[
                                    "expected_parameter_count"
                                ]
                            )
                        },
                    )
                )
                if not replay_already_charged:
                    reservation = parameterization_ledger.reserve(
                        parameterization_action_id,
                        parameterization_phase,
                        {"workbench_actions": declared_ceiling},
                    )
            except (BudgetExceeded, BudgetLedgerResourceUnavailable) as exc:
                budget_reason = str(
                    getattr(exc, "reason", getattr(exc, "reason_code", str(exc)))
                )
                resource_core = {
                    "schema": (
                        "leanmill.construction_parameterization_"
                        "budget_unavailable.v1"
                    ),
                    "parameterization_id": str(
                        parameterization["parameterization_id"]
                    ),
                    "parameterization_sha256": str(
                        parameterization["receipt_sha256"]
                    ),
                    "context_hash": str(parameterization["context_hash"]),
                    "adapter_id": str(parameterization["adapter_id"]),
                    "reason_code": budget_reason,
                    "declared_assignment_ceiling": declared_ceiling,
                    "budget_phase": parameterization_phase,
                    "outcome": "unavailable",
                    "provider_calls": 0,
                    "authority": "construction_parameterization_budget_boundary",
                }
                resource = {
                    **resource_core,
                    "receipt_sha256": content_hash(resource_core),
                }
                _persist_exact(
                    directory
                    / (
                        "construction_parameterization_unavailable."
                        + str(resource["receipt_sha256"])[:16]
                        + ".json"
                    ),
                    resource,
                    context="construction parameterization unavailable",
                )
                feedback = hooks.language_outcome_feedback(
                    directory,
                    run,
                    outcome="unavailable",
                    reason="construction_parameterization_budget_unavailable:"
                    + budget_reason,
                    evidence_refs=(
                        str(parameterization_forge_receipt["receipt_sha256"]),
                        str(parameterization["receipt_sha256"]),
                        str(resource["receipt_sha256"]),
                    ),
                    evidence_receipts=(resource,),
                )
                parameterization_exit = {
                    "schema": "leanmill.theory_language_advancement.v1",
                    "status": "unavailable",
                    "resource_receipt_sha256": resource["receipt_sha256"],
                    "feedback_receipt_sha256": feedback["receipt_sha256"],
                    "attempt_dir": str(directory),
                }
            if parameterization_exit is None:
                try:
                    if replaying_execution:
                        parameterization_execution = (
                            admit_persisted_construction_execution(
                                parameterization,
                                parameterization_execution,
                                witness_schema=interface["witness_schema"],
                            )
                        )
                        certified_count = int(
                            parameterization_execution.certified_assignment_count
                        )
                        admitted_parameterization = (
                            parameterization_execution.admitted_parameterization
                        )
                    else:
                        admitted_parameterization = (
                            admit_construction_parameterization(parameterization)
                        )
                        certified_count = int(
                            admitted_parameterization.certified_assignment_count
                        )
                        parameterization_execution = (
                            execute_construction_parameterization(
                                admitted_parameterization,
                                witness_schema=interface["witness_schema"],
                            )
                        )
                        _persist_exact(
                            directory
                            / (
                                "construction_parameterization_execution_"
                                "by_parameterization_"
                                + str(parameterization["receipt_sha256"])[:16]
                                + ".json"
                            ),
                            parameterization_execution,
                            context="construction parameterization execution",
                        )
                except (
                    ConstructionResourceCeilingExceeded,
                    ConstructionBackendCapabilityUnavailable,
                ) as exc:
                    exception_counters = dict(
                        getattr(exc, "counters", {}) or {}
                    )
                    reported_certified = int(
                        getattr(
                            exc,
                            "certified_assignment_count",
                            exception_counters.get(
                                "certified_assignment_count", 0
                            ),
                        )
                    )
                    certified_count = max(certified_count, reported_certified)
                    if not 0 <= certified_count <= declared_ceiling:
                        raise ValueError(
                            "construction backend crossed its declared assignment ceiling"
                        ) from exc
                    attempted_count = int(
                        getattr(
                            exc,
                            "attempted_assignment_count",
                            exception_counters.get(
                                "attempted_assignment_count", certified_count
                            ),
                        )
                    )
                    if not 0 <= attempted_count <= declared_ceiling:
                        raise ValueError(
                            "construction backend reported impossible attempted work"
                        ) from exc
                    if reservation is not None:
                        parameterization_ledger.commit(
                            reservation,
                            {"workbench_actions": attempted_count},
                        )
                        reservation = None
                    is_resource = isinstance(
                        exc, ConstructionResourceCeilingExceeded
                    )
                    resource_core = {
                        "schema": (
                            "leanmill.construction_parameterization_"
                            "resource_unavailable.v2"
                        ),
                        "parameterization_id": str(
                            parameterization["parameterization_id"]
                        ),
                        "parameterization_sha256": str(
                            parameterization["receipt_sha256"]
                        ),
                        "context_hash": str(parameterization["context_hash"]),
                        "adapter_id": str(parameterization["adapter_id"]),
                        "stage": (
                            "resource_ceiling"
                            if is_resource
                            else "backend_capability"
                        ),
                        "reason_code": str(exc.reason_code),
                        "resource": str(getattr(exc, "resource", "")),
                        "observed": getattr(exc, "observed", None),
                        "ceiling": getattr(exc, "ceiling", None),
                        "counters": exception_counters,
                        "operation": str(getattr(exc, "operation", "")),
                        "capability_id": str(
                            getattr(exc, "capability_id", "")
                        ),
                        "error_type": str(getattr(exc, "error_type", "")),
                        "certified_parameter_count": certified_count,
                        "attempted_parameter_count": attempted_count,
                        "declared_assignment_ceiling": declared_ceiling,
                        "budget_phase": parameterization_phase,
                        "persisted_semantic_replay": replaying_execution,
                        "outcome": "unavailable",
                        "provider_calls": 0,
                        "authority": (
                            "construction_parameterization_resource_boundary"
                        ),
                    }
                    resource = {
                        **resource_core,
                        "receipt_sha256": content_hash(resource_core),
                    }
                    _persist_exact(
                        directory
                        / (
                            "construction_parameterization_unavailable."
                            + str(resource["receipt_sha256"])[:16]
                            + ".json"
                        ),
                        resource,
                        context="construction parameterization unavailable",
                    )
                    feedback = hooks.language_outcome_feedback(
                        directory,
                        run,
                        outcome="unavailable",
                        reason=(
                            "construction_parameterization_unavailable:"
                            + str(exc.reason_code)
                        ),
                        evidence_refs=(
                            str(parameterization_forge_receipt["receipt_sha256"]),
                            str(parameterization["receipt_sha256"]),
                            str(resource["receipt_sha256"]),
                        ),
                        evidence_receipts=(resource,),
                    )
                    parameterization_exit = {
                        "schema": "leanmill.theory_language_advancement.v1",
                        "status": "unavailable",
                        "resource_receipt_sha256": resource["receipt_sha256"],
                        "feedback_receipt_sha256": feedback["receipt_sha256"],
                        "attempt_dir": str(directory),
                    }
                except Exception:
                    if reservation is not None:
                        parameterization_ledger.commit(
                            reservation,
                            {"workbench_actions": declared_ceiling},
                        )
                        reservation = None
                    raise
                else:
                    if reservation is not None:
                        parameterization_ledger.commit(
                            reservation,
                            {
                                "workbench_actions": int(
                                    parameterization_execution[
                                        "expected_parameter_count"
                                    ]
                                )
                            },
                        )
                        reservation = None
            if parameterization_exit is None:
                if not isinstance(parameterization_execution, Mapping):
                    raise ValueError(
                        "construction parameterization produced no execution receipt"
                    )
                if admitted_parameterization is None:
                    raise ValueError(
                        "construction parameterization lacks semantic admission"
                    )
                family, parameterization_execution = (
                    lower_reviewed_construction_parameterization(
                        admitted_parameterization,
                        forge_quarantine_receipt=parameterization_forge_receipt,
                        witness_interface=interface,
                        parameterization_execution=parameterization_execution,
                    )
                )
                if family is not None:
                    _persist_exact(
                        directory
                        / (
                            "finite_construction_family."
                            + str(family["receipt_sha256"])[:16]
                            + ".json"
                        ),
                        family,
                        context="finite construction family",
                    )
        finally:
            parameterization_ledger.freeze_wall_clock(
                reason="construction_parameterization_lowering_exit"
            )
        if parameterization_exit is not None:
            return _finish_advancement_transition(
                directory,
                ledger=parameterization_ledger,
                result=parameterization_exit,
                context_hash=str(parameterization["context_hash"]),
                adapter_id=str(parameterization["adapter_id"]),
                identity_ref=str(parameterization["receipt_sha256"]),
                resume_fn=resume_fn,
                _attempt_lease=_attempt_lease,
            )
        if not isinstance(parameterization_execution, Mapping):
            raise ValueError(
                "construction parameterization produced no execution receipt"
            )
        construction_origin = admit_construction_origin(
            parameterization=admitted_parameterization,
            forge_quarantine_receipt=parameterization_forge_receipt,
            parameterization_execution=parameterization_execution,
            witness_interface=interface,
        )
        family_forge_receipt = parameterization_forge_receipt
        if family is None:
            available = (
                parameterization_execution["coverage_complete"] is True
                and parameterization_execution["status"] == "completed"
            )
            feedback = hooks.language_outcome_feedback(
                directory,
                run,
                outcome="rejected" if available else "unavailable",
                reason=(
                    "construction_parameterization_has_no_candidates:"
                    + str(parameterization["parameterization_id"])
                    if available
                    else "construction_parameterization_backend_unavailable:"
                    + str(parameterization["parameterization_id"])
                ),
                evidence_refs=(
                    str(parameterization_forge_receipt["receipt_sha256"]),
                    str(parameterization_execution["receipt_sha256"]),
                ),
                evidence_receipts=(parameterization_execution,),
            )
            result = {
                "schema": "leanmill.theory_language_advancement.v1",
                "status": (
                    "construction_parameterization_exhausted"
                    if available
                    else "unavailable"
                ),
                "execution_receipt_sha256": parameterization_execution[
                    "receipt_sha256"
                ],
                "feedback_receipt_sha256": feedback["receipt_sha256"],
                "attempt_dir": str(directory),
            }
            return _finish_advancement_transition(
                directory,
                ledger=parameterization_ledger,
                result=result,
                context_hash=str(parameterization["context_hash"]),
                adapter_id=str(parameterization["adapter_id"]),
                identity_ref=str(parameterization_execution["receipt_sha256"]),
                resume_fn=resume_fn,
                _attempt_lease=_attempt_lease,
            )
    else:
        family, family_forge_receipt = hooks.approved_family(
            directory, completion
        )
    if family is not None:
        from ztare.leanmill.finite_construction_family import (
            FiniteConstructionFamilyResourceUnavailable,
            construction_witness_interface,
            execute_finite_construction_family,
        )
        from ztare.leanmill.theory_adapter_registry import (
            materialize_theory_adapter_capability,
            theory_adapter_capabilities,
        )
        from ztare.leanmill.witness_construction_boundary import (
            WitnessConstructionCapabilityUnavailable,
        )

        adapter_id = str(blueprint.adapter_id)
        if not isinstance(family_forge_receipt, Mapping):
            raise ValueError("reviewed finite family lacks Forge authority")
        interface = construction_witness_interface(
            adapter_id, dict(blueprint.adapter_config)
        )
        unique_family_query_count = len(
            {
                str(member.get("artifact_sha256") or "")
                for member in family.get("members") or ()
                if isinstance(member, Mapping)
            }
        )
        if unique_family_query_count < 1:
            raise ValueError("reviewed finite family has no source artifacts")
        from ztare.leanmill.reviewed_family_exhaustion_discharge import (
            validate_reviewed_family_execution_join,
        )

        def family_capability(*, descriptor, **kwargs):
            if (
                not isinstance(descriptor, Mapping)
                or str(descriptor.get("adapter_id") or "") != adapter_id
            ):
                raise ValueError("finite family capability crossed active adapter")
            capability_id = str(descriptor.get("capability_id") or "")
            if capability_id not in theory_adapter_capabilities(adapter_id):
                raise WitnessConstructionCapabilityUnavailable(
                    "adapter_capability_unavailable:" + capability_id
                )
            return materialize_theory_adapter_capability(
                adapter_id,
                capability_id,
                descriptor=dict(descriptor),
                **kwargs,
            )

        budget = ExplorationBudget.from_json(
            read_json(directory / "budget.json", {})
        )
        ledger = ExplorationBudgetLedger(
            directory / "budget.events.jsonl",
            budget,
            attempt_id=directory.name,
        )
        ledger.recover_interrupted_wall_clock()
        ledger.recover_interrupted_reservations()
        ledger.resume_wall_clock()

        def family_resource_unavailable(
            exc: FiniteConstructionFamilyResourceUnavailable,
        ) -> dict[str, Any]:
            counters = dict(getattr(exc, "counters", {}) or {})
            resource_core = {
                "schema": "leanmill.finite_family_resource_unavailable.v1",
                "family_id": str(family["family_id"]),
                "family_receipt_sha256": str(family["receipt_sha256"]),
                "request_id": str(family["request_id"]),
                "gap_id": str(family["gap_id"]),
                "context_hash": str(family["context_hash"]),
                "adapter_id": adapter_id,
                "reason_code": exc.reason_code,
                "resource": str(getattr(exc, "resource", "")),
                "observed": getattr(exc, "observed", None),
                "ceiling": getattr(exc, "ceiling", None),
                "counters": counters,
                "completed_members": int(
                    getattr(
                        exc,
                        "completed_members",
                        counters.get("completed_members", 0),
                    )
                ),
                "attempted_members": int(
                    getattr(
                        exc,
                        "attempted_members",
                        counters.get("attempted_members", 0),
                    )
                ),
                "outcome": "unavailable",
                "provider_calls": 0,
                "authority": "finite_construction_family_resource_boundary",
            }
            resource = {
                **resource_core,
                "receipt_sha256": content_hash(resource_core),
            }
            _persist_exact(
                directory
                / (
                    "finite_family_resource_unavailable."
                    + str(resource["receipt_sha256"])[:16]
                    + ".json"
                ),
                resource,
                context="finite family resource unavailable",
            )
            evidence_refs = [
                str(family_forge_receipt["receipt_sha256"]),
                str(family["receipt_sha256"]),
                str(resource["receipt_sha256"]),
            ]
            evidence_receipts: list[Mapping[str, Any]] = [resource]
            if construction_origin is not None:
                bound_execution = construction_origin.execution
                if isinstance(bound_execution, Mapping):
                    evidence_refs.append(str(bound_execution["receipt_sha256"]))
                    evidence_receipts.append(bound_execution)
            feedback = hooks.language_outcome_feedback(
                directory,
                run,
                outcome="unavailable",
                reason="finite_family_resource_unavailable:" + exc.reason_code,
                evidence_refs=tuple(evidence_refs),
                evidence_receipts=tuple(evidence_receipts),
            )
            return {
                "schema": "leanmill.theory_language_advancement.v1",
                "status": "unavailable",
                "resource_receipt_sha256": resource["receipt_sha256"],
                "feedback_receipt_sha256": feedback["receipt_sha256"],
                "attempt_dir": str(directory),
            }
        execution_path = directory / (
            "finite_construction_family_execution."
            + str(family["receipt_sha256"])[:16]
            + ".json"
        )
        legacy_execution_path = (
            directory / "finite_construction_family_execution.json"
        )
        try:
            family_execution_read_budget = {"bytes": 0}
            persisted_execution = validate_persisted_family_execution_slot(
                execution_path,
                family_receipt_sha256=str(family["receipt_sha256"]),
                aggregate_budget=family_execution_read_budget,
            )
        except (TypeError, ValueError):
            ledger.freeze_wall_clock(
                reason="finite_family_execution_identity_conflict"
            )
            raise
        try:
            legacy_occupied = _read_bounded_authority_slot(
                legacy_execution_path,
                max_bytes=_MAX_CONSTRUCTION_AUTHORITY_SLOT_BYTES,
                context="legacy finite family execution",
            )
        except ValueError:
            ledger.freeze_wall_clock(reason="finite_family_legacy_malformed")
            raise
        legacy_execution = (
            legacy_occupied[0] if legacy_occupied is not None else None
        )
        if legacy_occupied is not None:
            total_family_execution_bytes = int(
                family_execution_read_budget.get("bytes", 0)
            ) + int(legacy_occupied[1])
            if (
                total_family_execution_bytes
                > _MAX_FAMILY_EXECUTION_REPLAY_AGGREGATE_BYTES
            ):
                ledger.freeze_wall_clock(
                    reason="finite_family_execution_replay_aggregate_exhausted"
                )
                raise ValueError(
                    "finite family execution replay aggregate byte ceiling exhausted"
                )
        if (
            isinstance(persisted_execution, Mapping)
            and isinstance(legacy_execution, Mapping)
            and legacy_execution.get("family_receipt_sha256")
            == family["receipt_sha256"]
            and dict(legacy_execution) != dict(persisted_execution)
        ):
            ledger.freeze_wall_clock(
                reason="finite_family_execution_conflict_exit"
            )
            raise ValueError(
                "legacy and content-addressed family executions conflict"
            )
        migrate_legacy_execution = False
        if (
            persisted_execution is None
            and isinstance(legacy_execution, Mapping)
            and legacy_execution.get("family_receipt_sha256")
            == family["receipt_sha256"]
        ):
            persisted_execution = legacy_execution
            migrate_legacy_execution = True
        execution = None
        if isinstance(persisted_execution, Mapping):
            replay_unavailable = None
            try:
                _frozen_family, execution = validate_reviewed_family_execution_join(
                    family=family,
                    family_execution=persisted_execution,
                    request_id=str(family["request_id"]),
                    context_hash=str(family["context_hash"]),
                    adapter_id=adapter_id,
                    witness_interface=interface,
                    construction_origin=construction_origin,
                )
                if migrate_legacy_execution:
                    _persist_exact(
                        execution_path,
                        execution,
                        context="migrated finite family execution",
                    )
            except FiniteConstructionFamilyResourceUnavailable as exc:
                replay_unavailable = family_resource_unavailable(exc)
            finally:
                ledger.freeze_wall_clock(reason="finite_family_replay_exit")
            if replay_unavailable is not None:
                return _finish_advancement_transition(
                    directory,
                    ledger=ledger,
                    result=replay_unavailable,
                    context_hash=str(family["context_hash"]),
                    adapter_id=adapter_id,
                    identity_ref=str(family["receipt_sha256"]),
                    resume_fn=resume_fn,
                    _attempt_lease=_attempt_lease,
                )
        if execution is None:
            try:
                reservation = ledger.reserve(
                    f"finite-family:{family['receipt_sha256']}",
                    "boundary",
                    {"boundary_queries": unique_family_query_count},
                )
            except BudgetExceeded as exc:
                ledger.freeze_wall_clock(
                    reason="finite_family_execution_budget_unavailable"
                )
                feedback = hooks.language_outcome_feedback(
                    directory,
                    run,
                    outcome="unavailable",
                    reason="finite_family_execution_budget_unavailable:" + exc.reason,
                    evidence_refs=(
                        str(family_forge_receipt["receipt_sha256"]),
                        str(family["receipt_sha256"]),
                    ),
                )
                result = {
                    "schema": "leanmill.theory_language_advancement.v1",
                    "status": "unavailable",
                    "feedback_receipt_sha256": feedback["receipt_sha256"],
                    "attempt_dir": str(directory),
                }
                return _finish_advancement_transition(
                    directory,
                    ledger=ledger,
                    result=result,
                    context_hash=str(family["context_hash"]),
                    adapter_id=adapter_id,
                    identity_ref=str(family["receipt_sha256"]),
                    resume_fn=resume_fn,
                    _attempt_lease=_attempt_lease,
                )
            execution_unavailable = None
            try:
                try:
                    execution = execute_finite_construction_family(
                        family,
                        witness_interface=interface,
                        capability_fn=family_capability,
                        construction_origin=construction_origin,
                    )
                except FiniteConstructionFamilyResourceUnavailable as exc:
                    attempted_artifacts = {
                        str(member.get("artifact_sha256") or "")
                        for member in list(family.get("members") or ())[
                            : int(exc.attempted_members)
                        ]
                        if isinstance(member, Mapping)
                    }
                    ledger.commit(
                        reservation,
                        {"boundary_queries": len(attempted_artifacts)},
                    )
                    execution_unavailable = family_resource_unavailable(exc)
                if execution_unavailable is None:
                    _persist_exact(
                        execution_path,
                        execution,
                        context="finite family execution",
                    )
                if execution_unavailable is None and not legacy_execution_path.exists():
                    write_json_atomic(legacy_execution_path, execution)
                if execution_unavailable is None:
                    ledger.commit(
                        reservation,
                        {
                            "boundary_queries": int(
                                execution["unique_source_artifact_count"]
                            )
                        },
                    )
            finally:
                ledger.freeze_wall_clock(reason="finite_family_execution_exit")
            if execution_unavailable is not None:
                return _finish_advancement_transition(
                    directory,
                    ledger=ledger,
                    result=execution_unavailable,
                    context_hash=str(family["context_hash"]),
                    adapter_id=adapter_id,
                    identity_ref=str(family["receipt_sha256"]),
                    resume_fn=resume_fn,
                    _attempt_lease=_attempt_lease,
                )
        if execution["status"] == "witness_found":
            admissions = hooks.persist_ratification_admissions(
                directory,
                family=family,
                execution=execution,
                forge_quarantine_receipt=family_forge_receipt,
                witness_interface=interface,
                construction_origin=construction_origin,
            )
            current = read_json(directory / "run.json", run)
            current_navigation = dict(current.get("navigation") or {})
            current_navigation["finite_construction_family_execution"] = execution
            current_navigation[
                "reviewed_family_member_ratification_admission_sha256s"
            ] = [str(row["receipt_sha256"]) for row in admissions]
            run_core = {
                **{
                    key: value
                    for key, value in current.items()
                    if key not in {"run_digest", "adapter_gap"}
                },
                "status": "frontier_objective_witness_found_pending_ratification",
                "navigation": current_navigation,
                "adapter_gap": None,
            }
            write_json_atomic(
                directory / "run.json",
                {**run_core, "run_digest": content_hash(run_core)},
            )
            result = {
                "schema": "leanmill.theory_language_advancement.v1",
                "status": "witness_found_pending_ratification",
                "execution_receipt_sha256": execution["receipt_sha256"],
                "attempt_dir": str(directory),
            }
            return _finish_advancement_transition(
                directory,
                ledger=ledger,
                result=result,
                context_hash=str(family["context_hash"]),
                adapter_id=adapter_id,
                identity_ref=str(execution["receipt_sha256"]),
                resume_fn=None,
                _attempt_lease=_attempt_lease,
            )
        if execution["status"] == "exhausted":
            from ztare.leanmill.reviewed_family_exhaustion_discharge import (
                build_reviewed_family_exhaustion_observation,
                reviewed_family_exhaustion_stop_permission,
            )

            provenance = hooks.family_synthesis_provenance(directory, run)
            frozen_lineages = hooks.frozen_terminal_lineage_ids(
                run.get("navigation") or {}
            )
            if (
                reviewed_family_exhaustion_stop_permission(blueprint) is not None
                and provenance is not None
                and frozen_lineages
            ):
                synthesis_input, synthesis_decision = provenance
                observation = build_reviewed_family_exhaustion_observation(
                    source_family_run=run,
                    blueprint=blueprint,
                    active_request=hooks.language_request_from_run(run),
                    synthesis_input=synthesis_input,
                    synthesis_decision=synthesis_decision,
                    family=family,
                    forge_quarantine_receipt=family_forge_receipt,
                    family_execution=execution,
                    frozen_lineage_ids=frozen_lineages,
                    construction_origin=construction_origin,
                )
                observation_path = directory / (
                    "reviewed_family_exhaustion_observation.by-family-execution."
                    + str(observation["finite_family_execution_sha256"])
                    + ".json"
                )
                _persist_exact(
                    observation_path,
                    observation,
                    context="family exhaustion observation",
                )
        feedback = hooks.language_outcome_feedback(
            directory,
            run,
            outcome=(
                "rejected" if execution["status"] == "exhausted" else "unavailable"
            ),
            reason=(
                "reviewed_finite_family_exhausted:" + str(execution["family_id"])
                if execution["status"] == "exhausted"
                else "reviewed_finite_family_has_unavailable_member:"
                + str(execution["family_id"])
            ),
            evidence_refs=(
                str(family_forge_receipt["receipt_sha256"]),
                str(execution["receipt_sha256"]),
            ),
            evidence_receipts=(execution,),
        )
        result = {
            "schema": "leanmill.theory_language_advancement.v1",
            "status": (
                "finite_family_exhausted"
                if execution["status"] == "exhausted"
                else "unavailable"
            ),
            "execution_receipt_sha256": execution["receipt_sha256"],
            "feedback_receipt_sha256": feedback["receipt_sha256"],
            "attempt_dir": str(directory),
        }
        result = _finish_advancement_transition(
            directory,
            ledger=ledger,
            result=result,
            context_hash=str(family["context_hash"]),
            adapter_id=adapter_id,
            identity_ref=str(execution["receipt_sha256"]),
            resume_fn=resume_fn,
            _attempt_lease=_attempt_lease,
        )
        resumed_run = read_json(directory / "run.json", {})
        family_discharge = (
            hooks.current_family_exhaustion_discharge(
                directory, resumed_run
            )
            if isinstance(resumed_run, Mapping)
            else None
        )
        return {
            **result,
            "status": (
                "finite_family_exhausted_objective_discharged"
                if family_discharge is not None
                else result["status"]
            ),
        }

    return None



__all__ = [
    "advance_reviewed_construction_campaign",
    "bind_recovered_boundary_artifact_feedback",
    "durable_witness_construction_candidates",
    "pending_cold_witness_boundary_recovery",
    "recovered_boundary_feedback_disposition_program_id",
    "recover_cold_witness_boundary",
    "validate_persisted_family_execution_slot",
    "witness_execution_coordinate_from_contract",
]
