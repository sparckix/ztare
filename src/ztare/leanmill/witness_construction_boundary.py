"""Typed, data-only boundary for one frozen constructive witness.

The common task-discharge object remains the stopping authority.  This module
only defines the payload and deterministic boundary result for a task whose
claim is that one explicit JSON witness satisfies one frozen predicate.
Substrate mathematics stays behind registered normalizer and verifier
capabilities; candidate bytes are never imported or executed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from jsonschema import Draft202012Validator, SchemaError, ValidationError

from ztare.common.task_discharge import (
    TaskDischargeContract,
    TaskDischargeReceipt,
    bind_task_discharge_receipt,
)
from ztare.leanmill.data_only_json import strict_json_data
from ztare.leanmill.protocol_validation import (
    require_sha256_digest as _digest,
)
from ztare.leanmill.theory_ir import content_hash


GOVERNED_WITNESS_CONSTRUCTION_CAPABILITY = "governed_witness_construction"
GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR = (
    "leanmill.governed_witness_construction.v1"
)
WITNESS_CONSTRUCTION_CANDIDATE_SCHEMA = (
    "leanmill.witness_construction_candidate.v1"
)
WITNESS_CONSTRUCTION_INTERFACE_SCHEMA = (
    "leanmill.witness_construction_interface.v1"
)
WITNESS_CONSTRUCTION_BOUNDARY_RESULT_SCHEMA = (
    "leanmill.witness_construction_boundary_result.v1"
)
WITNESS_CONSTRUCTION_EXECUTION_COORDINATE_SCHEMA = (
    "leanmill.witness_construction_execution_coordinate.v1"
)
WITNESS_NORMALIZATION_RECEIPT_SCHEMA = (
    "leanmill.witness_construction_normalization.v1"
)
WITNESS_VERIFICATION_RECEIPT_SCHEMA = (
    "leanmill.witness_construction_verification.v1"
)
REGISTERED_WITNESS_ARTIFACT_EXECUTION_SCHEMA = (
    "leanmill.registered_witness_artifact_execution.v1"
)
WITNESS_CONSTRUCTOR_REQUEST_SCHEMA = "leanmill.witness_constructor_request.v1"
WITNESS_CONSTRUCTOR_REQUEST_MEMORY_SCHEMA = (
    "leanmill.witness_constructor_request.v2"
)
WITNESS_CANDIDATE_OUTCOME_MEMORY_SCHEMA = (
    "leanmill.witness_candidate_outcome_memory.v1"
)
_LEGACY_WITNESS_CANDIDATE_OUTCOME_MEMORY_SCHEMA = (
    "leanmill.construction_candidate_outcome_memory.v1"
)
WITNESS_CONSTRUCTOR_OUTPUT_SCHEMA = "leanmill.witness_constructor_output.v1"
WITNESS_CONSTRUCTOR_AUTHORSHIP_SCHEMA = (
    "leanmill.witness_constructor_authorship.v1"
)
WITNESS_CONSTRUCTION_CLAIM_SCOPE = (
    "one_explicit_data_witness_satisfies_one_frozen_predicate"
)

_BOUNDARY_STATUSES = frozenset(
    {"witness_verified", "witness_rejected", "capability_unavailable"}
)
_VERIFIER_OUTCOMES = frozenset({"accepted", "rejected", "unavailable"})
_DISCHARGE_POLICIES = frozenset(
    {
        "verifier_acceptance_is_terminal",
        "construction_artifact_ratification_required",
    }
)
_MAX_REGISTERED_WITNESS_PROTOCOL_BYTES = 16_000_000
_MAX_REGISTERED_WITNESS_PROTOCOL_INTEGER_BITS = 4_096


def _json_data(value: Any, *, context: str) -> Any:
    return strict_json_data(
        value,
        context=context,
        max_wire_bytes=_MAX_REGISTERED_WITNESS_PROTOCOL_BYTES,
        max_integer_bits=_MAX_REGISTERED_WITNESS_PROTOCOL_INTEGER_BITS,
    )


class WitnessConstructionCapabilityUnavailable(RuntimeError):
    """A registered witness task cannot reach one declared adapter capability."""

    def __init__(
        self,
        reason_code: str,
        *,
        resource: str = "",
        observed: int | None = None,
        ceiling: int | None = None,
        counters: Mapping[str, int] | None = None,
    ) -> None:
        self.reason_code = str(reason_code)
        self.resource = str(resource)
        self.observed = observed
        self.ceiling = ceiling
        self.counters = {
            str(key): int(value) for key, value in (counters or {}).items()
        }
        super().__init__(self.reason_code)

    def to_observed(self) -> dict[str, Any]:
        return {
            "schema": "leanmill.witness_capability_unavailable_observed.v1",
            "reason_code": self.reason_code,
            "resource": self.resource,
            "observed": self.observed,
            "ceiling": self.ceiling,
            "counters": {
                key: self.counters[key] for key in sorted(self.counters)
            },
        }


class WitnessConstructorUnavailable(RuntimeError):
    """The distinct campaign witness-authoring role could not be invoked."""


def _capability_unavailable_observed(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "schema", "reason_code", "resource", "observed", "ceiling", "counters",
    }:
        raise ValueError("witness capability-unavailable observation is malformed")
    counters = value.get("counters")
    if (
        value.get("schema")
        != "leanmill.witness_capability_unavailable_observed.v1"
        or not isinstance(value.get("reason_code"), str)
        or not value["reason_code"]
        or not isinstance(value.get("resource"), str)
        or not isinstance(counters, Mapping)
        or list(counters) != sorted(counters)
        or any(
            not isinstance(key, str)
            or not key
            or type(amount) is not int
            or amount < 0
            for key, amount in counters.items()
        )
        or ((value.get("observed") is None) != (value.get("ceiling") is None))
        or (
            value.get("observed") is not None
            and (
                type(value["observed"]) is not int
                or int(value["observed"]) < 0
                or type(value["ceiling"]) is not int
                or int(value["ceiling"]) < 0
            )
        )
    ):
        raise ValueError("witness capability-unavailable observation is invalid")
    return dict(value)


def _capability_output_json(value: Any, *, context: str) -> Any:
    try:
        return _json_data(value, context=context)
    except ValueError as exc:
        if (
            "maximum JSON wire size" in str(exc)
            or "integer bit ceiling" in str(exc)
        ):
            raise WitnessConstructionCapabilityUnavailable(
                "registered_witness_output_resource_unavailable"
            ) from exc
        raise


def validate_witness_construction_interface(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the reviewed public descriptor shown losslessly to a leaf."""

    required = {
        "schema",
        "predicate_ir",
        "witness_schema",
        "normalizer",
        "verifier",
        "discharge_policy",
        "target_config_sha256",
        "claim_boundary",
        "interface_sha256",
    }
    canonical = _json_data(value, context="witness-construction interface")
    if not isinstance(canonical, dict) or set(canonical) != required:
        raise ValueError("witness-construction interface fields changed identity")
    value = canonical

    def forbidden_visible_key(payload: Any) -> str:
        if isinstance(payload, Mapping):
            for key, item in payload.items():
                lowered = str(key).lower()
                if "sealed" in lowered or lowered in {
                    "evidence_refs",
                    "raw_fixture_refs",
                    "source_examples",
                }:
                    return str(key)
                nested = forbidden_visible_key(item)
                if nested:
                    return nested
        elif isinstance(payload, list):
            for item in payload:
                nested = forbidden_visible_key(item)
                if nested:
                    return nested
        return ""

    forbidden_key = forbidden_visible_key(value)
    if forbidden_key:
        raise ValueError(
            "witness-construction interface exposes forbidden evidence field: "
            + forbidden_key
        )
    core = {key: item for key, item in value.items() if key != "interface_sha256"}
    target_config_sha256 = str(value.get("target_config_sha256") or "")
    if (
        value.get("schema") != WITNESS_CONSTRUCTION_INTERFACE_SCHEMA
        or value.get("claim_boundary")
        != "reviewed_public_construction_interface_no_sealed_evidence"
        or value.get("discharge_policy") not in _DISCHARGE_POLICIES
        or len(target_config_sha256) != 64
        or any(character not in "0123456789abcdef" for character in target_config_sha256)
        or value.get("interface_sha256") != content_hash(core)
    ):
        raise ValueError("witness-construction interface claims unsupported authority")
    predicate = _json_data(
        value.get("predicate_ir"), context="construction-interface predicate"
    )
    witness_schema = _json_data(
        value.get("witness_schema"), context="construction-interface schema"
    )
    if not isinstance(predicate, Mapping) or not predicate:
        raise ValueError("construction interface requires a nonempty predicate IR")
    if not isinstance(witness_schema, Mapping) or not witness_schema:
        raise ValueError("construction interface requires a nonempty witness schema")
    try:
        Draft202012Validator.check_schema(dict(witness_schema))
    except SchemaError as exc:
        raise ValueError("construction interface witness schema is invalid") from exc
    normalizer = value.get("normalizer")
    verifier = value.get("verifier")
    if not isinstance(normalizer, Mapping) or not isinstance(verifier, Mapping):
        raise ValueError("construction interface requires capability descriptors")

    def visible_descriptor(raw: Mapping[str, Any], *, context: str) -> dict[str, Any]:
        if set(raw) != {"capability_id", "contract"}:
            raise ValueError(f"{context} descriptor fields changed identity")
        capability_id = str(raw.get("capability_id") or "").strip()
        contract = _json_data(raw.get("contract"), context=f"{context} contract")
        if not capability_id or not isinstance(contract, Mapping) or not contract:
            raise ValueError(f"{context} descriptor is incomplete")
        return {"capability_id": capability_id, "contract": dict(contract)}

    return {
        "schema": WITNESS_CONSTRUCTION_INTERFACE_SCHEMA,
        "predicate_ir": dict(predicate),
        "witness_schema": dict(witness_schema),
        "normalizer": visible_descriptor(
            normalizer, context="construction-interface normalizer"
        ),
        "verifier": visible_descriptor(
            verifier, context="construction-interface verifier"
        ),
        "discharge_policy": str(value["discharge_policy"]),
        "target_config_sha256": target_config_sha256,
        "claim_boundary": (
            "reviewed_public_construction_interface_no_sealed_evidence"
        ),
        "interface_sha256": str(value["interface_sha256"]),
    }


def build_witness_construction_interface(
    *,
    predicate_ir: Mapping[str, Any],
    witness_schema: Mapping[str, Any],
    normalizer: Mapping[str, Any],
    verifier: Mapping[str, Any],
    discharge_policy: str,
    target_config_sha256: str,
) -> dict[str, Any]:
    core = {
        "schema": WITNESS_CONSTRUCTION_INTERFACE_SCHEMA,
        "predicate_ir": dict(predicate_ir),
        "witness_schema": dict(witness_schema),
        "normalizer": dict(normalizer),
        "verifier": dict(verifier),
        "discharge_policy": str(discharge_policy),
        "target_config_sha256": str(target_config_sha256),
        "claim_boundary": (
            "reviewed_public_construction_interface_no_sealed_evidence"
        ),
    }
    return validate_witness_construction_interface(
        {**core, "interface_sha256": content_hash(core)}
    )


def _capability_descriptor(
    value: Mapping[str, Any], *, adapter_id: str, context: str
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {"capability_id", "contract"}:
        raise ValueError(f"{context} descriptor fields do not match its contract")
    capability_id = str(value.get("capability_id") or "").strip()
    contract = value.get("contract")
    if not capability_id or not isinstance(contract, Mapping) or not contract:
        raise ValueError(f"{context} descriptor is incomplete")
    return {
        "adapter_id": str(adapter_id),
        "capability_id": capability_id,
        "contract": _json_data(contract, context=f"{context} contract"),
    }


def _bound_capability_descriptor(
    value: Mapping[str, Any], *, adapter_id: str, context: str
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "adapter_id",
        "capability_id",
        "contract",
    }:
        raise ValueError(f"{context} descriptor fields do not match its envelope")
    if str(value.get("adapter_id") or "") != str(adapter_id):
        raise ValueError(f"{context} descriptor crossed adapter identity")
    return _capability_descriptor(
        {
            "capability_id": value.get("capability_id"),
            "contract": value.get("contract"),
        },
        adapter_id=adapter_id,
        context=context,
    )


def _validate_artifact_schema(schema: Mapping[str, Any], artifact: Mapping[str, Any]) -> None:
    try:
        Draft202012Validator.check_schema(dict(schema))
        Draft202012Validator(dict(schema)).validate(dict(artifact))
    except (SchemaError, ValidationError) as exc:
        raise ValueError("witness artifact does not satisfy its frozen schema") from exc


_ORIENTATION_FIELDS = {
    "eigenquestion",
    "representation_choice",
    "expected_failure_mode",
    "next_revision_if_rejected",
}


def _orientation_record(value: Any) -> dict[str, str]:
    row = _json_data(value, context="witness-constructor orientation")
    if not isinstance(row, dict) or set(row) != _ORIENTATION_FIELDS or any(
        not isinstance(row[field], str) or not row[field].strip()
        for field in _ORIENTATION_FIELDS
    ):
        raise ValueError("witness-constructor orientation is incomplete")
    return {field: str(row[field]) for field in sorted(_ORIENTATION_FIELDS)}


def _candidate_outcome_rows(value: Any) -> list[dict[str, Any]]:
    rows = _json_data(value, context="witness candidate outcome memory")
    fields = {
        "source_artifact_sha256",
        "normalized_artifact_sha256",
        "boundary_status",
        "verifier_status",
        "observed",
        "evidence_refs",
    }
    if not isinstance(rows, list):
        raise ValueError("witness candidate outcomes must be an array")
    for row in rows:
        if (
            not isinstance(row, dict)
            or set(row) != fields
            or row["boundary_status"]
            not in {"witness_rejected", "witness_verified", "witness_unavailable"}
            or not str(row["verifier_status"]).strip()
            or not isinstance(row["observed"], dict)
            or not isinstance(row["evidence_refs"], list)
            or not row["evidence_refs"]
            or any(not str(ref).strip() for ref in row["evidence_refs"])
        ):
            raise ValueError("witness candidate outcome is malformed")
        for field in ("source_artifact_sha256", "normalized_artifact_sha256"):
            _digest(row[field], context=field)
    ordered = sorted(
        rows,
        key=lambda row: (
            row["source_artifact_sha256"],
            row["normalized_artifact_sha256"],
        ),
    )
    identities = [
        (row["source_artifact_sha256"], row["normalized_artifact_sha256"])
        for row in ordered
    ]
    if rows != ordered or len(identities) != len(set(identities)):
        raise ValueError("witness candidate outcomes are not canonical")
    return rows


def build_witness_candidate_outcome_memory(
    *,
    adapter_id: str,
    construction_interface: Mapping[str, Any],
    outcomes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind prior exact artifact outcomes to one public construction interface."""

    interface = validate_witness_construction_interface(construction_interface)
    ordered = sorted(
        (_json_data(row, context="witness candidate outcome") for row in outcomes),
        key=lambda row: (
            row.get("source_artifact_sha256", ""),
            row.get("normalized_artifact_sha256", ""),
        ),
    )
    ordered = _candidate_outcome_rows(ordered)
    core = {
        "schema": WITNESS_CANDIDATE_OUTCOME_MEMORY_SCHEMA,
        "adapter_id": str(adapter_id),
        "interface_sha256": interface["interface_sha256"],
        "target_config_sha256": interface["target_config_sha256"],
        "predicate_sha256": content_hash(interface["predicate_ir"]),
        "outcomes": ordered,
        "authority": "registered_task_discharge_projection",
        "claim_boundary": (
            "prior candidate outcomes only; no construction-existence or "
            "nonexistence conclusion"
        ),
    }
    if not core["adapter_id"].strip():
        raise ValueError("witness candidate memory lacks adapter identity")
    return {**core, "receipt_sha256": content_hash(core)}


def validate_witness_candidate_outcome_memory(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    memory = _json_data(value, context="witness candidate outcome memory")
    fields = {
        "schema",
        "adapter_id",
        "interface_sha256",
        "target_config_sha256",
        "predicate_sha256",
        "outcomes",
        "authority",
        "claim_boundary",
        "receipt_sha256",
    }
    core = {
        key: item for key, item in memory.items() if key != "receipt_sha256"
    } if isinstance(memory, dict) else {}
    if (
        isinstance(memory, dict)
        and memory.get("schema")
        == _LEGACY_WITNESS_CANDIDATE_OUTCOME_MEMORY_SCHEMA
    ):
        legacy_fields = fields
        legacy_row_fields = {
            "schema",
            "adapter_id",
            "interface_sha256",
            "target_config_sha256",
            "predicate_sha256",
            "source_artifact_sha256",
            "normalized_artifact_sha256",
            "boundary_status",
            "task_receipt_status",
            "verifier_status",
            "observed",
            "evidence_refs",
            "authority",
            "receipt_sha256",
        }
        rows = memory.get("outcomes")
        if (
            set(memory) != legacy_fields
            or memory.get("authority")
            != "campaign_target_scoped_outcome_projection"
            or memory.get("receipt_sha256") != content_hash(core)
            or not isinstance(rows, list)
        ):
            raise ValueError("legacy witness candidate memory failed replay")
        for row in rows:
            row_core = {
                key: item for key, item in row.items() if key != "receipt_sha256"
            } if isinstance(row, dict) else {}
            if (
                not isinstance(row, dict)
                or set(row) != legacy_row_fields
                or row.get("schema")
                != "leanmill.construction_candidate_outcome.v1"
                or row.get("authority") != "registered_task_discharge_replay"
                or row.get("receipt_sha256") != content_hash(row_core)
                or any(row.get(field) != memory.get(field) for field in (
                    "adapter_id",
                    "interface_sha256",
                    "target_config_sha256",
                    "predicate_sha256",
                ))
                or not isinstance(row.get("observed"), dict)
            ):
                raise ValueError("legacy witness candidate outcome failed replay")
        return memory
    if (
        not isinstance(memory, dict)
        or set(memory) != fields
        or memory.get("schema") != WITNESS_CANDIDATE_OUTCOME_MEMORY_SCHEMA
        or memory.get("authority") != "registered_task_discharge_projection"
        or memory.get("receipt_sha256") != content_hash(core)
        or not str(memory.get("adapter_id") or "").strip()
        or not str(memory.get("claim_boundary") or "").strip()
    ):
        raise ValueError("witness candidate outcome memory failed replay")
    for field in (
        "interface_sha256",
        "target_config_sha256",
        "predicate_sha256",
    ):
        _digest(memory[field], context=field)
    _candidate_outcome_rows(memory["outcomes"])
    return memory


def matching_witness_candidate_outcome(
    memory: Mapping[str, Any], artifact_sha256: str
) -> dict[str, Any] | None:
    frozen = validate_witness_candidate_outcome_memory(memory)
    digest = _digest(artifact_sha256, context="candidate artifact")
    matches = [
        dict(row)
        for row in frozen["outcomes"]
        if digest
        in {
            row["source_artifact_sha256"],
            row["normalized_artifact_sha256"],
        }
    ]
    if len(matches) > 1:
        raise ValueError("candidate artifact matches multiple prior outcomes")
    return matches[0] if matches else None


def build_witness_constructor_request(
    *,
    context_hash: str,
    adapter_id: str,
    construction_interface: Mapping[str, Any],
    task_intent: Mapping[str, Any],
    candidate_outcome_memory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind one artifact-authoring call to public task bytes only."""

    interface = validate_witness_construction_interface(construction_interface)
    intent = _json_data(task_intent, context="witness-constructor task intent")
    required_intent = {
        "presentation_formula_ids",
        "goal",
        "observable",
        "evidence_refs",
        "kill_condition",
        "construction_brief",
    }
    if (
        not isinstance(intent, dict)
        or set(intent) != required_intent
        or not isinstance(intent["presentation_formula_ids"], list)
        or not intent["presentation_formula_ids"]
        or not isinstance(intent["evidence_refs"], list)
        or not intent["evidence_refs"]
        or any(
            not isinstance(intent[field], str) or not intent[field].strip()
            for field in (
                "goal",
                "observable",
                "kill_condition",
                "construction_brief",
            )
        )
        or any(
            not isinstance(value, str) or not value.strip()
            for field in ("presentation_formula_ids", "evidence_refs")
            for value in intent[field]
        )
    ):
        raise ValueError("witness-constructor task intent is malformed")
    memory = None
    if candidate_outcome_memory is not None:
        memory = validate_witness_candidate_outcome_memory(candidate_outcome_memory)
        if (
            memory["adapter_id"] != str(adapter_id)
            or memory["interface_sha256"] != interface["interface_sha256"]
            or memory["target_config_sha256"]
            != interface["target_config_sha256"]
            or memory["predicate_sha256"]
            != content_hash(interface["predicate_ir"])
        ):
            raise ValueError(
                "witness-constructor memory crossed its construction interface"
            )
    core = {
        "schema": (
            WITNESS_CONSTRUCTOR_REQUEST_MEMORY_SCHEMA
            if memory is not None
            else WITNESS_CONSTRUCTOR_REQUEST_SCHEMA
        ),
        "context_hash": str(context_hash),
        "adapter_id": str(adapter_id),
        "construction_interface": interface,
        "interface_sha256": interface["interface_sha256"],
        "task_intent": intent,
        "task_intent_sha256": content_hash(intent),
        "claim_boundary": (
            "campaign_role_authors_data_only_artifact_from_public_interface"
        ),
        "authority": "navigator_task_request_host_bound",
    }
    if memory is not None:
        core["candidate_outcome_memory"] = memory
    if not core["context_hash"].strip() or not core["adapter_id"].strip():
        raise ValueError("witness-constructor request lacks context or adapter identity")
    return {**core, "request_sha256": content_hash(core)}


def validate_witness_constructor_request(value: Mapping[str, Any]) -> dict[str, Any]:
    row = _json_data(value, context="witness-constructor request")
    required = {
        "schema",
        "context_hash",
        "adapter_id",
        "construction_interface",
        "interface_sha256",
        "task_intent",
        "task_intent_sha256",
        "claim_boundary",
        "authority",
        "request_sha256",
    }
    memory = None
    if row.get("schema") == WITNESS_CONSTRUCTOR_REQUEST_MEMORY_SCHEMA:
        required.add("candidate_outcome_memory")
        memory = row.get("candidate_outcome_memory")
    elif row.get("schema") != WITNESS_CONSTRUCTOR_REQUEST_SCHEMA:
        raise ValueError("unsupported witness-constructor request schema")
    if not isinstance(row, dict) or set(row) != required:
        raise ValueError("witness-constructor request fields changed identity")
    rebuilt = build_witness_constructor_request(
        context_hash=str(row["context_hash"]),
        adapter_id=str(row["adapter_id"]),
        construction_interface=row["construction_interface"],
        task_intent=row["task_intent"],
        candidate_outcome_memory=memory,
    )
    if rebuilt != row:
        raise ValueError("witness-constructor request digest mismatch")
    return rebuilt


def build_witness_constructor_output(
    request: Mapping[str, Any],
    *,
    artifact: Mapping[str, Any],
    orientation: Mapping[str, Any],
    role: str,
    agent_id: str,
    call_receipt_sha256: str,
) -> dict[str, Any]:
    """Bind role-authored data and non-authoritative orientation to one call."""

    frozen = validate_witness_constructor_request(request)
    public_interface = frozen["construction_interface"]
    candidate = _json_data(artifact, context="witness-constructor artifact")
    if not isinstance(candidate, dict) or not candidate:
        raise ValueError("witness constructor returned no data artifact")
    _validate_artifact_schema(public_interface["witness_schema"], candidate)
    orientation_row = _orientation_record(orientation)
    call_digest = _digest(
        call_receipt_sha256, context="witness-constructor call receipt"
    )
    if role != "witness_constructor" or not str(agent_id).strip():
        raise ValueError("witness-constructor output crossed its runtime role")
    authorship_core = {
        "schema": WITNESS_CONSTRUCTOR_AUTHORSHIP_SCHEMA,
        "constructor_request_sha256": frozen["request_sha256"],
        "task_intent_sha256": frozen["task_intent_sha256"],
        "context_hash": frozen["context_hash"],
        "adapter_id": frozen["adapter_id"],
        "interface_sha256": frozen["interface_sha256"],
        "artifact_sha256": content_hash(candidate),
        "orientation_sha256": content_hash(orientation_row),
        "role": role,
        "agent_id": str(agent_id),
        "call_receipt_sha256": call_digest,
        "authority": "campaign_witness_constructor_role",
    }
    authorship = {
        **authorship_core,
        "receipt_sha256": content_hash(authorship_core),
    }
    core = {
        "schema": WITNESS_CONSTRUCTOR_OUTPUT_SCHEMA,
        "artifact": candidate,
        "orientation": orientation_row,
        "authorship_receipt": authorship,
        "claim_boundary": (
            "orientation_is_non_authoritative_boundary_consumes_artifact_only"
        ),
    }
    return {**core, "output_sha256": content_hash(core)}


def validate_witness_constructor_output(
    request: Mapping[str, Any], value: Mapping[str, Any]
) -> dict[str, Any]:
    frozen = validate_witness_constructor_request(request)
    row = _json_data(value, context="witness-constructor output")
    required = {
        "schema",
        "artifact",
        "orientation",
        "authorship_receipt",
        "claim_boundary",
        "output_sha256",
    }
    if not isinstance(row, dict) or set(row) != required:
        raise ValueError("witness-constructor output fields changed identity")
    authorship = row.get("authorship_receipt")
    if not isinstance(authorship, dict):
        raise ValueError("witness-constructor output lacks authorship")
    rebuilt = build_witness_constructor_output(
        frozen,
        artifact=row["artifact"],
        orientation=row["orientation"],
        role=str(authorship.get("role") or ""),
        agent_id=str(authorship.get("agent_id") or ""),
        call_receipt_sha256=str(authorship.get("call_receipt_sha256") or ""),
    )
    if rebuilt != row:
        raise ValueError("witness-constructor output or authorship digest mismatch")
    return rebuilt


@dataclass(frozen=True)
class WitnessConstructionCandidateEnvelope:
    """One inert candidate bound to every contract that can interpret it."""

    request_id: str
    context_hash: str
    adapter_id: str
    predicate_ir: Mapping[str, Any]
    witness_schema: Mapping[str, Any]
    normalizer: Mapping[str, Any]
    verifier: Mapping[str, Any]
    constructor_request: Mapping[str, Any]
    artifact: Mapping[str, Any]
    orientation: Mapping[str, Any]
    authorship_receipt: Mapping[str, Any]
    discharge_policy: str
    target_config_sha256: str
    interface_sha256: str
    schema: str = WITNESS_CONSTRUCTION_CANDIDATE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != WITNESS_CONSTRUCTION_CANDIDATE_SCHEMA:
            raise ValueError("unsupported witness-construction candidate schema")
        if any(
            not str(value).strip()
            for value in (self.request_id, self.context_hash, self.adapter_id)
        ):
            raise ValueError("witness candidate requires request, context, and adapter identity")
        if self.discharge_policy not in _DISCHARGE_POLICIES:
            raise ValueError("witness candidate has an unsupported discharge policy")
        for label, digest in (
            ("target configuration", self.target_config_sha256),
            ("construction interface", self.interface_sha256),
        ):
            if len(digest) != 64 or any(
                character not in "0123456789abcdef" for character in digest
            ):
                raise ValueError(f"witness candidate {label} digest is malformed")
        predicate = _json_data(self.predicate_ir, context="witness predicate IR")
        schema = _json_data(self.witness_schema, context="witness schema")
        artifact = _json_data(self.artifact, context="witness artifact")
        constructor_request = validate_witness_constructor_request(
            self.constructor_request
        )
        orientation = _orientation_record(self.orientation)
        authorship = _json_data(
            self.authorship_receipt, context="witness authorship receipt"
        )
        if not isinstance(predicate, Mapping) or not predicate:
            raise ValueError("witness candidate requires a nonempty predicate IR")
        if not isinstance(schema, Mapping) or not schema:
            raise ValueError("witness candidate requires a nonempty JSON schema")
        if not isinstance(artifact, Mapping) or not artifact:
            raise ValueError("witness candidate artifact must be a nonempty JSON object")
        if not isinstance(authorship, dict):
            raise ValueError("witness candidate lacks constructor authorship")
        normalizer = _bound_capability_descriptor(
            self.normalizer,
            adapter_id=self.adapter_id,
            context="witness normalizer",
        )
        verifier = _bound_capability_descriptor(
            self.verifier,
            adapter_id=self.adapter_id,
            context="witness verifier",
        )
        _validate_artifact_schema(schema, artifact)
        visible_normalizer = {
            "capability_id": normalizer["capability_id"],
            "contract": normalizer["contract"],
        }
        visible_verifier = {
            "capability_id": verifier["capability_id"],
            "contract": verifier["contract"],
        }
        public_interface = constructor_request["construction_interface"]
        if (
            constructor_request["context_hash"] != self.context_hash
            or constructor_request["adapter_id"] != self.adapter_id
            or public_interface["predicate_ir"] != predicate
            or public_interface["witness_schema"] != schema
            or public_interface["normalizer"] != visible_normalizer
            or public_interface["verifier"] != visible_verifier
            or public_interface["discharge_policy"] != self.discharge_policy
            or public_interface["target_config_sha256"]
            != self.target_config_sha256
            or public_interface["interface_sha256"] != self.interface_sha256
        ):
            raise ValueError("witness candidate crossed its constructor interface")
        rebuilt_authorship = build_witness_constructor_output(
            constructor_request,
            artifact=artifact,
            orientation=orientation,
            role=str(authorship.get("role") or ""),
            agent_id=str(authorship.get("agent_id") or ""),
            call_receipt_sha256=str(
                authorship.get("call_receipt_sha256") or ""
            ),
        )["authorship_receipt"]
        if authorship != rebuilt_authorship:
            raise ValueError("witness candidate authorship crossed its role call")
        object.__setattr__(self, "predicate_ir", predicate)
        object.__setattr__(self, "witness_schema", schema)
        object.__setattr__(self, "normalizer", normalizer)
        object.__setattr__(self, "verifier", verifier)
        object.__setattr__(self, "constructor_request", constructor_request)
        object.__setattr__(self, "artifact", artifact)
        object.__setattr__(self, "orientation", orientation)
        object.__setattr__(self, "authorship_receipt", authorship)

    @property
    def receipt_sha256(self) -> str:
        return str(self.to_json()["receipt_sha256"])

    @property
    def execution_coordinate(self) -> dict[str, Any]:
        """Return every immutable input that can change artifact semantics."""

        row = self.to_json()
        core = {
            "schema": WITNESS_CONSTRUCTION_EXECUTION_COORDINATE_SCHEMA,
            "context_hash": self.context_hash,
            "adapter_id": self.adapter_id,
            "interface_sha256": self.interface_sha256,
            "target_config_sha256": self.target_config_sha256,
            "artifact_sha256": row["artifact_sha256"],
            "predicate_sha256": row["predicate_sha256"],
            "witness_schema_sha256": row["witness_schema_sha256"],
            "normalizer_sha256": row["normalizer_sha256"],
            "verifier_sha256": row["verifier_sha256"],
        }
        return {**core, "coordinate_sha256": content_hash(core)}

    def to_json(self) -> dict[str, Any]:
        predicate = dict(self.predicate_ir)
        schema = dict(self.witness_schema)
        normalizer = dict(self.normalizer)
        verifier = dict(self.verifier)
        constructor_request = dict(self.constructor_request)
        artifact = dict(self.artifact)
        orientation = dict(self.orientation)
        authorship = dict(self.authorship_receipt)
        core = {
            "schema": self.schema,
            "request_id": self.request_id,
            "context_hash": self.context_hash,
            "adapter_id": self.adapter_id,
            "predicate_ir": predicate,
            "predicate_sha256": content_hash(predicate),
            "witness_schema": schema,
            "witness_schema_sha256": content_hash(schema),
            "normalizer": normalizer,
            "normalizer_sha256": content_hash(normalizer),
            "verifier": verifier,
            "verifier_sha256": content_hash(verifier),
            "constructor_request": constructor_request,
            "constructor_request_sha256": content_hash(constructor_request),
            "artifact": artifact,
            "artifact_sha256": content_hash(artifact),
            "orientation": orientation,
            "orientation_sha256": content_hash(orientation),
            "authorship_receipt": authorship,
            "authorship_receipt_sha256": content_hash(authorship),
            "discharge_policy": self.discharge_policy,
            "target_config_sha256": self.target_config_sha256,
            "interface_sha256": self.interface_sha256,
            "claim_scope": WITNESS_CONSTRUCTION_CLAIM_SCOPE,
        }
        return {**core, "receipt_sha256": content_hash(core)}

    @classmethod
    def from_json(
        cls, value: Mapping[str, Any]
    ) -> "WitnessConstructionCandidateEnvelope":
        required = {
            "schema",
            "request_id",
            "context_hash",
            "adapter_id",
            "predicate_ir",
            "predicate_sha256",
            "witness_schema",
            "witness_schema_sha256",
            "normalizer",
            "normalizer_sha256",
            "verifier",
            "verifier_sha256",
            "constructor_request",
            "constructor_request_sha256",
            "artifact",
            "artifact_sha256",
            "orientation",
            "orientation_sha256",
            "authorship_receipt",
            "authorship_receipt_sha256",
            "discharge_policy",
            "target_config_sha256",
            "interface_sha256",
            "claim_scope",
            "receipt_sha256",
        }
        canonical = _json_data(value, context="witness candidate envelope")
        if not isinstance(canonical, dict) or set(canonical) != required:
            raise ValueError("witness candidate envelope fields changed identity")
        value = canonical
        candidate = cls(
            schema=str(value["schema"]),
            request_id=str(value["request_id"]),
            context_hash=str(value["context_hash"]),
            adapter_id=str(value["adapter_id"]),
            predicate_ir=dict(value["predicate_ir"]),
            witness_schema=dict(value["witness_schema"]),
            normalizer=dict(value["normalizer"]),
            verifier=dict(value["verifier"]),
            constructor_request=dict(value["constructor_request"]),
            artifact=dict(value["artifact"]),
            orientation=dict(value["orientation"]),
            authorship_receipt=dict(value["authorship_receipt"]),
            discharge_policy=str(value["discharge_policy"]),
            target_config_sha256=str(value["target_config_sha256"]),
            interface_sha256=str(value["interface_sha256"]),
        )
        if candidate.to_json() != dict(value):
            raise ValueError("witness candidate envelope digest mismatch")
        return candidate


def build_witness_construction_candidate(
    *,
    request_id: str,
    context_hash: str,
    adapter_id: str,
    specification: Mapping[str, Any],
) -> WitnessConstructionCandidateEnvelope:
    required = {
        "predicate_ir",
        "witness_schema",
        "normalizer",
        "verifier",
        "constructor_request",
        "artifact",
        "orientation",
        "authorship_receipt",
        "discharge_policy",
        "target_config_sha256",
        "interface_sha256",
    }
    canonical = _json_data(
        specification, context="witness-construction specification"
    )
    if not isinstance(canonical, dict) or set(canonical) != required:
        raise ValueError("witness-construction specification fields changed identity")
    specification = canonical
    return WitnessConstructionCandidateEnvelope(
        request_id=str(request_id),
        context_hash=str(context_hash),
        adapter_id=str(adapter_id),
        predicate_ir=dict(specification["predicate_ir"]),
        witness_schema=dict(specification["witness_schema"]),
        normalizer=_capability_descriptor(
            specification["normalizer"],
            adapter_id=adapter_id,
            context="witness normalizer",
        ),
        verifier=_capability_descriptor(
            specification["verifier"],
            adapter_id=adapter_id,
            context="witness verifier",
        ),
        constructor_request=dict(specification["constructor_request"]),
        artifact=dict(specification["artifact"]),
        orientation=dict(specification["orientation"]),
        authorship_receipt=dict(specification["authorship_receipt"]),
        discharge_policy=str(specification["discharge_policy"]),
        target_config_sha256=str(specification["target_config_sha256"]),
        interface_sha256=str(specification["interface_sha256"]),
    )


def compile_governed_witness_construction_task(
    *,
    request: Mapping[str, Any],
    context: Any,
    adapter_id: str,
    construction_interface: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Lower only the registered constructive-witness task kind."""

    if request.get("adjudicator_capability") != GOVERNED_WITNESS_CONSTRUCTION_CAPABILITY:
        return None
    request_core = {key: value for key, value in request.items() if key != "request_id"}
    if (
        request.get("schema") != "leanmill.theory_task_request.v1"
        or request.get("request_id")
        != "theory-task-request:" + content_hash(request_core)
        or request.get("context_hash") != getattr(context, "context_hash", None)
        or request.get("authority") != "leaf_request_host_bound"
        or not str(adapter_id).strip()
    ):
        raise ValueError("witness-construction task request changed identity")
    presentations = validate_witness_construction_presentation(
        context=context,
        presentation_formula_ids=request.get("presentation_formula_ids"),
        context_epoch=request.get("context_epoch"),
    )
    evidence_refs = request.get("evidence_refs")
    if not isinstance(evidence_refs, list) or not evidence_refs or any(
        not str(value).strip() for value in evidence_refs
    ):
        raise ValueError("witness-construction task requires receipted input evidence")
    if any(
        not str(request.get(field) or "").strip()
        for field in ("goal", "observable", "kill_condition")
    ):
        raise ValueError("witness-construction task text cannot be empty")
    if "finite_witness_residual" in request:
        raise ValueError("a constructive candidate cannot impersonate a finite residual")
    specification = request.get("witness_construction") or {}
    if construction_interface is None:
        raise ValueError(
            "witness construction requires a reviewed visible adapter interface"
        )
    reviewed_interface = validate_witness_construction_interface(
        construction_interface
    )
    if not isinstance(specification, Mapping) or any(
        _json_data(specification.get(field), context=f"witness {field}")
        != reviewed_interface[field]
        for field in (
            "predicate_ir",
            "witness_schema",
            "normalizer",
            "verifier",
            "discharge_policy",
            "target_config_sha256",
            "interface_sha256",
        )
    ):
        raise ValueError(
            "witness-construction request crossed its visible adapter interface"
        )
    candidate = build_witness_construction_candidate(
        request_id=str(request["request_id"]),
        context_hash=str(request["context_hash"]),
        adapter_id=str(adapter_id),
        specification=specification,
    )
    expected_constructor_request = build_witness_constructor_request(
        context_hash=str(request["context_hash"]),
        adapter_id=str(adapter_id),
        construction_interface=reviewed_interface,
        task_intent={
            "presentation_formula_ids": list(presentations),
            "goal": str(request["goal"]),
            "observable": str(request["observable"]),
            "evidence_refs": [
                str(value)
                for value in evidence_refs
                if not str(value).startswith("witness-constructor-authorship:")
            ],
            "kill_condition": str(request["kill_condition"]),
            "construction_brief": str(
                candidate.constructor_request["task_intent"][
                    "construction_brief"
                ]
            ),
        },
        candidate_outcome_memory=candidate.constructor_request.get(
            "candidate_outcome_memory"
        ),
    )
    if dict(candidate.constructor_request) != expected_constructor_request:
        raise ValueError("witness constructor authorship crossed the frozen task intent")
    task_specification = {
        "goal": str(request["goal"]),
        "observable": str(request["observable"]),
        "kill_condition": str(request["kill_condition"]),
    }
    return {
        "adjudicator_id": GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR,
        "parameters": {
            "kind": "governed_witness_construction",
            "request_id": str(request["request_id"]),
            "context_hash": str(request["context_hash"]),
            "context_epoch": int(request["context_epoch"]),
            "presentation_formula_ids": list(presentations),
            "task_specification": task_specification,
            "task_specification_sha256": content_hash(task_specification),
            "input_evidence_refs": [str(value) for value in evidence_refs],
            "candidate_envelope": candidate.to_json(),
            "candidate_envelope_sha256": candidate.receipt_sha256,
            "claim_scope": WITNESS_CONSTRUCTION_CLAIM_SCOPE,
        },
    }


def validate_witness_construction_presentation(
    *,
    context: Any,
    presentation_formula_ids: Any,
    context_epoch: Any,
) -> tuple[str, ...]:
    """Validate frozen task coordinates before any provider-backed authorship."""

    presentations = tuple(str(value) for value in presentation_formula_ids or ())
    known = set(getattr(context, "formula_ids", ()))
    if (
        not presentations
        or len(set(presentations)) != len(presentations)
        or not set(presentations) <= known
        or type(context_epoch) is not int
        or context_epoch < 0
    ):
        raise ValueError("witness-construction task crossed its frozen presentation")
    return presentations


def witness_construction_parameters(
    contract: TaskDischargeContract,
) -> dict[str, Any]:
    if contract.adjudicator_id != GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR:
        raise KeyError(
            f"unsupported witness-construction adjudicator: {contract.adjudicator_id}"
        )
    parameters = dict(contract.parameters)
    required = {
        "kind",
        "request_id",
        "context_hash",
        "context_epoch",
        "presentation_formula_ids",
        "task_specification",
        "task_specification_sha256",
        "input_evidence_refs",
        "candidate_envelope",
        "candidate_envelope_sha256",
        "claim_scope",
    }
    if (
        set(parameters) != required
        or parameters.get("kind") != "governed_witness_construction"
        or parameters.get("claim_scope") != WITNESS_CONSTRUCTION_CLAIM_SCOPE
        or type(parameters.get("context_epoch")) is not int
        or int(parameters["context_epoch"]) < 0
        or not isinstance(parameters.get("presentation_formula_ids"), list)
        or not parameters["presentation_formula_ids"]
        or not isinstance(parameters.get("input_evidence_refs"), list)
        or not parameters["input_evidence_refs"]
        or any(not str(ref).strip() for ref in parameters["input_evidence_refs"])
        or not isinstance(parameters.get("task_specification"), Mapping)
        or set(parameters["task_specification"])
        != {"goal", "observable", "kill_condition"}
        or any(
            not str(parameters["task_specification"].get(field) or "").strip()
            for field in ("goal", "observable", "kill_condition")
        )
        or parameters.get("task_specification_sha256")
        != content_hash(dict(parameters["task_specification"]))
    ):
        raise ValueError("witness-construction task parameters changed identity")
    candidate = WitnessConstructionCandidateEnvelope.from_json(
        parameters.get("candidate_envelope") or {}
    )
    if (
        candidate.receipt_sha256 != parameters.get("candidate_envelope_sha256")
        or candidate.request_id != parameters.get("request_id")
        or candidate.context_hash != parameters.get("context_hash")
    ):
        raise ValueError("witness candidate crossed its frozen task")
    parameters["candidate_envelope"] = candidate.to_json()
    return parameters


def execute_registered_witness_artifact(
    *,
    adapter_id: str,
    witness_interface: Mapping[str, Any],
    artifact: Mapping[str, Any],
    normalizer_fn: Callable[..., Mapping[str, Any]],
    verifier_fn: Callable[..., Mapping[str, Any]],
) -> dict[str, Any]:
    """Run the one canonical registered normalizer/verifier boundary."""

    interface = validate_witness_construction_interface(witness_interface)
    source = _json_data(artifact, context="registered witness artifact")
    if not isinstance(source, dict) or not source:
        raise ValueError("registered witness artifact must be one nonempty object")
    _validate_artifact_schema(interface["witness_schema"], source)
    normalizer = _capability_descriptor(
        interface["normalizer"],
        adapter_id=str(adapter_id),
        context="registered witness normalizer",
    )
    verifier = _capability_descriptor(
        interface["verifier"],
        adapter_id=str(adapter_id),
        context="registered witness verifier",
    )

    def normalizer_kwargs() -> dict[str, Any]:
        return _json_data(
            {
                "descriptor": normalizer,
                "artifact": source,
                "predicate_ir": interface["predicate_ir"],
                "witness_schema": interface["witness_schema"],
            },
            context="registered witness normalizer input",
        )

    normalized: dict[str, Any] | None = None
    verifier_outcome = ""
    observed: Any = None
    evidence_refs: list[str] = []
    try:
        first = _capability_output_json(
            normalizer_fn(**normalizer_kwargs()),
            context="normalized witness artifact",
        )
        second = _capability_output_json(
            normalizer_fn(**normalizer_kwargs()),
            context="normalized witness artifact",
        )
    except WitnessConstructionCapabilityUnavailable as exc:
        status = "unavailable"
        stage = "normalization"
        reason_code = exc.reason_code
        observed = exc.to_observed()
    else:
        if first != second:
            raise ValueError("witness normalizer is nondeterministic")
        if not isinstance(first, Mapping) or not first:
            raise ValueError("witness normalizer returned no data object")
        normalized = dict(first)
        _validate_artifact_schema(interface["witness_schema"], normalized)

        def verifier_kwargs() -> dict[str, Any]:
            return _json_data(
                {
                    "descriptor": verifier,
                    "normalized_artifact": normalized,
                    "predicate_ir": interface["predicate_ir"],
                    "witness_schema": interface["witness_schema"],
                },
                context="registered witness verifier input",
            )

        try:
            first_verification = _verification_payload(
                verifier_fn(**verifier_kwargs())
            )
            second_verification = _verification_payload(
                verifier_fn(**verifier_kwargs())
            )
        except WitnessConstructionCapabilityUnavailable as exc:
            status = "unavailable"
            stage = "verification"
            reason_code = exc.reason_code
            verifier_outcome = "unavailable"
            observed = exc.to_observed()
        else:
            if first_verification != second_verification:
                raise ValueError("witness verifier is nondeterministic")
            verifier_outcome = str(first_verification["outcome"])
            observed = first_verification["observed"]
            evidence_refs = list(first_verification["evidence_refs"])
            status = (
                "verified"
                if verifier_outcome == "accepted"
                else "rejected"
                if verifier_outcome == "rejected"
                else "unavailable"
            )
            stage = "complete" if verifier_outcome != "unavailable" else "verification"
            reason_code = (
                "predicate_satisfied"
                if verifier_outcome == "accepted"
                else "predicate_rejected"
                if verifier_outcome == "rejected"
                else "verifier_reported_unavailable"
            )
    core = {
        "schema": REGISTERED_WITNESS_ARTIFACT_EXECUTION_SCHEMA,
        "adapter_id": str(adapter_id),
        "interface_sha256": interface["interface_sha256"],
        "predicate_sha256": content_hash(interface["predicate_ir"]),
        "witness_schema_sha256": content_hash(interface["witness_schema"]),
        "normalizer_sha256": content_hash(normalizer),
        "verifier_sha256": content_hash(verifier),
        "source_artifact_sha256": content_hash(source),
        "normalized_artifact": normalized,
        "normalized_artifact_sha256": (
            content_hash(normalized) if normalized is not None else ""
        ),
        "verifier_outcome": verifier_outcome,
        "observed": observed,
        "evidence_refs": evidence_refs,
        "status": status,
        "stage": stage,
        "reason_code": reason_code,
        "deterministic_replay": True,
        "authority": "registered_witness_artifact_executor",
    }
    return validate_registered_witness_artifact_execution(
        {**core, "receipt_sha256": content_hash(core)},
        adapter_id=adapter_id,
        witness_interface=interface,
        artifact=source,
    )


def validate_registered_witness_artifact_execution(
    value: Mapping[str, Any],
    *,
    adapter_id: str,
    witness_interface: Mapping[str, Any],
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    interface = validate_witness_construction_interface(witness_interface)
    source = _json_data(artifact, context="registered witness artifact")
    _validate_artifact_schema(interface["witness_schema"], source)
    row = _json_data(value, context="registered witness execution")
    required = {
        "schema", "adapter_id", "interface_sha256", "predicate_sha256",
        "witness_schema_sha256", "normalizer_sha256", "verifier_sha256",
        "source_artifact_sha256", "normalized_artifact",
        "normalized_artifact_sha256", "verifier_outcome", "observed",
        "evidence_refs", "status", "stage", "reason_code",
        "deterministic_replay", "authority", "receipt_sha256",
    }
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    normalizer = _capability_descriptor(
        interface["normalizer"], adapter_id=str(adapter_id),
        context="registered witness normalizer",
    )
    verifier = _capability_descriptor(
        interface["verifier"], adapter_id=str(adapter_id),
        context="registered witness verifier",
    )
    normalized = row.get("normalized_artifact")
    refs = row.get("evidence_refs")
    if (
        not isinstance(row, dict)
        or set(row) != required
        or row.get("schema") != REGISTERED_WITNESS_ARTIFACT_EXECUTION_SCHEMA
        or row.get("receipt_sha256") != content_hash(core)
        or row.get("adapter_id") != str(adapter_id)
        or row.get("interface_sha256") != interface["interface_sha256"]
        or row.get("predicate_sha256") != content_hash(interface["predicate_ir"])
        or row.get("witness_schema_sha256")
        != content_hash(interface["witness_schema"])
        or row.get("normalizer_sha256") != content_hash(normalizer)
        or row.get("verifier_sha256") != content_hash(verifier)
        or row.get("source_artifact_sha256") != content_hash(source)
        or row.get("deterministic_replay") is not True
        or row.get("authority") != "registered_witness_artifact_executor"
        or not str(row.get("reason_code") or "")
        or not isinstance(refs, list)
        or any(not isinstance(ref, str) or not ref for ref in refs)
    ):
        raise ValueError("registered witness execution crossed its interface")
    if normalized is None:
        unavailable_observed = (
            _capability_unavailable_observed(row["observed"])
            if isinstance(row.get("observed"), Mapping)
            else None
        )
        expected_reason = (
            unavailable_observed["reason_code"]
            if unavailable_observed is not None
            else "normalizer_unavailable"
        )
        if (
            row.get("normalized_artifact_sha256") != ""
            or row.get("status") != "unavailable"
            or row.get("stage") != "normalization"
            or row.get("verifier_outcome") != ""
            or refs
            or row.get("observed") is not None
            and unavailable_observed is None
            or row.get("reason_code") != expected_reason
        ):
            raise ValueError("registered witness normalization failure is malformed")
    else:
        if not isinstance(normalized, Mapping) or not normalized:
            raise ValueError("registered normalized witness is malformed")
        _validate_artifact_schema(interface["witness_schema"], normalized)
        if row.get("normalized_artifact_sha256") != content_hash(normalized):
            raise ValueError("registered normalized witness digest mismatch")
        outcome = str(row.get("verifier_outcome") or "")
        if row.get("stage") == "complete":
            expected_status = "verified" if outcome == "accepted" else "rejected"
            expected_reason = (
                "predicate_satisfied"
                if outcome == "accepted"
                else "predicate_rejected"
            )
            if (
                outcome not in {"accepted", "rejected"}
                or row.get("status") != expected_status
                or row.get("reason_code") != expected_reason
            ):
                raise ValueError("registered witness completion is malformed")
        elif row.get("stage") == "verification":
            if row.get("status") != "unavailable" or outcome not in {"", "unavailable"}:
                raise ValueError("registered witness verification failure is malformed")
            if outcome == "" and (row.get("observed") is not None or refs):
                raise ValueError("unreached witness verifier carries evidence")
            if outcome == "unavailable" and isinstance(
                row.get("observed"), Mapping
            ) and row["observed"].get("schema") == (
                "leanmill.witness_capability_unavailable_observed.v1"
            ):
                unavailable_observed = _capability_unavailable_observed(
                    row["observed"]
                )
                expected_reason = unavailable_observed["reason_code"]
            else:
                expected_reason = (
                    "verifier_unavailable"
                    if outcome == ""
                    else "verifier_reported_unavailable"
                )
            if row.get("reason_code") != expected_reason:
                raise ValueError("registered witness verification reason is malformed")
        else:
            raise ValueError("registered witness execution stage is invalid")
    return row


def _normalization_receipt(
    contract: TaskDischargeContract,
    candidate: WitnessConstructionCandidateEnvelope,
    normalized_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    core = {
        "schema": WITNESS_NORMALIZATION_RECEIPT_SCHEMA,
        "contract_sha256": contract.sha256,
        "candidate_envelope_sha256": candidate.receipt_sha256,
        "normalizer_sha256": candidate.to_json()["normalizer_sha256"],
        "source_artifact_sha256": candidate.to_json()["artifact_sha256"],
        "normalized_artifact_sha256": content_hash(dict(normalized_artifact)),
        "deterministic_replay": True,
        "authority": "registered_adapter_witness_normalizer",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _verification_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    canonical = _capability_output_json(
        value, context="witness verifier output"
    )
    if not isinstance(canonical, dict) or set(canonical) != {
        "outcome",
        "observed",
        "evidence_refs",
    }:
        raise ValueError("witness verifier output fields changed identity")
    value = canonical
    outcome = str(value.get("outcome") or "")
    refs = value.get("evidence_refs")
    if outcome not in _VERIFIER_OUTCOMES or not isinstance(refs, list) or any(
        not str(ref).strip() for ref in refs
    ):
        raise ValueError("witness verifier returned an invalid outcome")
    return {
        "outcome": outcome,
        "observed": _json_data(value.get("observed"), context="witness verification"),
        "evidence_refs": [str(ref) for ref in refs],
    }


def _verification_receipt(
    contract: TaskDischargeContract,
    candidate: WitnessConstructionCandidateEnvelope,
    normalized_artifact: Mapping[str, Any],
    verified: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_row = candidate.to_json()
    core = {
        "schema": WITNESS_VERIFICATION_RECEIPT_SCHEMA,
        "contract_sha256": contract.sha256,
        "candidate_envelope_sha256": candidate.receipt_sha256,
        "predicate_sha256": candidate_row["predicate_sha256"],
        "witness_schema_sha256": candidate_row["witness_schema_sha256"],
        "verifier_sha256": candidate_row["verifier_sha256"],
        "normalized_artifact_sha256": content_hash(dict(normalized_artifact)),
        "outcome": str(verified["outcome"]),
        "observed": verified["observed"],
        "evidence_refs": list(verified["evidence_refs"]),
        "deterministic_replay": True,
        "authority": "registered_adapter_witness_verifier",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _boundary_result(
    contract: TaskDischargeContract,
    *,
    status: str,
    stage: str,
    reason_code: str,
    normalized_artifact: Mapping[str, Any] | None,
    normalization_receipt: Mapping[str, Any] | None,
    verification_receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    parameters = witness_construction_parameters(contract)
    candidate = WitnessConstructionCandidateEnvelope.from_json(
        parameters["candidate_envelope"]
    )
    execution_coordinate = candidate.execution_coordinate
    core = {
        "schema": WITNESS_CONSTRUCTION_BOUNDARY_RESULT_SCHEMA,
        "candidate_kind": "theory_task",
        "context_hash": str(parameters["context_hash"]),
        "contract_sha256": contract.sha256,
        "adjudicator_id": contract.adjudicator_id,
        "request_id": str(parameters["request_id"]),
        "status": str(status),
        "stage": str(stage),
        "reason_code": str(reason_code),
        "candidate_envelope_sha256": candidate.receipt_sha256,
        "execution_coordinate": execution_coordinate,
        "execution_coordinate_sha256": execution_coordinate[
            "coordinate_sha256"
        ],
        "source_artifact_sha256": candidate.to_json()["artifact_sha256"],
        "normalized_artifact": (
            dict(normalized_artifact) if normalized_artifact is not None else None
        ),
        "normalization_receipt": (
            dict(normalization_receipt)
            if normalization_receipt is not None
            else None
        ),
        "verification_receipt": (
            dict(verification_receipt)
            if verification_receipt is not None
            else None
        ),
        "authority": "frontier_boundary_witness_construction_join",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def build_witness_construction_unavailable_result(
    contract: TaskDischargeContract,
    *,
    stage: str,
    reason_code: str,
    normalized_artifact: Mapping[str, Any] | None = None,
    normalization_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if stage not in {"normalization", "verification"} or not str(reason_code).strip():
        raise ValueError("witness capability failure requires a typed stage and reason")
    if stage == "normalization" and (
        normalized_artifact is not None or normalization_receipt is not None
    ):
        raise ValueError("normalization-unavailable result cannot carry normalized bytes")
    return _boundary_result(
        contract,
        status="capability_unavailable",
        stage=stage,
        reason_code=reason_code,
        normalized_artifact=normalized_artifact,
        normalization_receipt=normalization_receipt,
        verification_receipt=None,
    )


def execute_governed_witness_construction_task(
    contract: TaskDischargeContract,
    *,
    normalizer_fn: Callable[..., Mapping[str, Any]],
    verifier_fn: Callable[..., Mapping[str, Any]],
) -> dict[str, Any]:
    """Normalize and verify inert candidate bytes through registered callbacks."""

    parameters = witness_construction_parameters(contract)
    candidate = WitnessConstructionCandidateEnvelope.from_json(
        parameters["candidate_envelope"]
    )
    interface = {
        "schema": WITNESS_CONSTRUCTION_INTERFACE_SCHEMA,
        "predicate_ir": dict(candidate.predicate_ir),
        "witness_schema": dict(candidate.witness_schema),
        "normalizer": {
            "capability_id": candidate.normalizer["capability_id"],
            "contract": dict(candidate.normalizer["contract"]),
        },
        "verifier": {
            "capability_id": candidate.verifier["capability_id"],
            "contract": dict(candidate.verifier["contract"]),
        },
        "discharge_policy": candidate.discharge_policy,
        "target_config_sha256": candidate.target_config_sha256,
        "claim_boundary": (
            "reviewed_public_construction_interface_no_sealed_evidence"
        ),
        "interface_sha256": candidate.interface_sha256,
    }
    execution = execute_registered_witness_artifact(
        adapter_id=candidate.adapter_id,
        witness_interface=interface,
        artifact=candidate.artifact,
        normalizer_fn=normalizer_fn,
        verifier_fn=verifier_fn,
    )
    normalized = execution["normalized_artifact"]
    if normalized is None:
        return build_witness_construction_unavailable_result(
            contract,
            stage="normalization",
            reason_code=str(execution["reason_code"]),
        )
    normalization = _normalization_receipt(contract, candidate, normalized)
    verifier_outcome = str(execution["verifier_outcome"])
    if not verifier_outcome:
        return build_witness_construction_unavailable_result(
            contract,
            stage="verification",
            reason_code=str(execution["reason_code"]),
            normalized_artifact=normalized,
            normalization_receipt=normalization,
        )
    verified = {
        "outcome": verifier_outcome,
        "observed": execution["observed"],
        "evidence_refs": list(execution["evidence_refs"]),
    }
    verification = _verification_receipt(
        contract, candidate, normalized, verified
    )
    if verifier_outcome == "unavailable":
        return _boundary_result(
            contract,
            status="capability_unavailable",
            stage="verification",
            reason_code=str(execution["reason_code"]),
            normalized_artifact=normalized,
            normalization_receipt=normalization,
            verification_receipt=verification,
        )
    return _boundary_result(
        contract,
        status=(
            "witness_verified"
            if verifier_outcome == "accepted"
            else "witness_rejected"
        ),
        stage="complete",
        reason_code=str(execution["reason_code"]),
        normalized_artifact=normalized,
        normalization_receipt=normalization,
        verification_receipt=verification,
    )


def _validate_content_receipt(
    value: Mapping[str, Any], *, schema: str, required: set[str]
) -> dict[str, Any]:
    row = dict(value)
    if set(row) != required | {"receipt_sha256"}:
        raise ValueError(f"{schema} fields changed identity")
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    if row.get("schema") != schema or row.get("receipt_sha256") != content_hash(core):
        raise ValueError(f"{schema} digest mismatch")
    return row


def validate_witness_construction_boundary_result(
    contract: TaskDischargeContract, value: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate one witness handler result before boundary admission."""

    parameters = witness_construction_parameters(contract)
    candidate = WitnessConstructionCandidateEnvelope.from_json(
        parameters["candidate_envelope"]
    )
    required = {
        "schema",
        "candidate_kind",
        "context_hash",
        "contract_sha256",
        "adjudicator_id",
        "request_id",
        "status",
        "stage",
        "reason_code",
        "candidate_envelope_sha256",
        "execution_coordinate",
        "execution_coordinate_sha256",
        "source_artifact_sha256",
        "normalized_artifact",
        "normalization_receipt",
        "verification_receipt",
        "authority",
    }
    row = _validate_content_receipt(
        value,
        schema=WITNESS_CONSTRUCTION_BOUNDARY_RESULT_SCHEMA,
        required=required,
    )
    candidate_row = candidate.to_json()
    execution_coordinate = candidate.execution_coordinate
    if (
        row.get("candidate_kind") != "theory_task"
        or row.get("context_hash") != parameters["context_hash"]
        or row.get("contract_sha256") != contract.sha256
        or row.get("adjudicator_id") != contract.adjudicator_id
        or row.get("request_id") != parameters["request_id"]
        or row.get("status") not in _BOUNDARY_STATUSES
        or row.get("candidate_envelope_sha256") != candidate.receipt_sha256
        or row.get("execution_coordinate") != execution_coordinate
        or row.get("execution_coordinate_sha256")
        != execution_coordinate["coordinate_sha256"]
        or row.get("source_artifact_sha256") != candidate_row["artifact_sha256"]
        or row.get("authority") != "frontier_boundary_witness_construction_join"
        or not str(row.get("reason_code") or "").strip()
    ):
        raise ValueError("witness boundary result crossed its frozen contract")

    normalized_raw = row.get("normalized_artifact")
    normalization_raw = row.get("normalization_receipt")
    verification_raw = row.get("verification_receipt")
    normalized = (
        _json_data(normalized_raw, context="normalized witness artifact")
        if normalized_raw is not None
        else None
    )
    if normalized is not None:
        if not isinstance(normalized, Mapping) or not normalized:
            raise ValueError("witness boundary normalized artifact is malformed")
        _validate_artifact_schema(candidate.witness_schema, normalized)
    normalization = None
    if normalization_raw is not None:
        normalization = _validate_content_receipt(
            normalization_raw,
            schema=WITNESS_NORMALIZATION_RECEIPT_SCHEMA,
            required={
                "schema",
                "contract_sha256",
                "candidate_envelope_sha256",
                "normalizer_sha256",
                "source_artifact_sha256",
                "normalized_artifact_sha256",
                "deterministic_replay",
                "authority",
            },
        )
        if (
            normalized is None
            or normalization.get("contract_sha256") != contract.sha256
            or normalization.get("candidate_envelope_sha256")
            != candidate.receipt_sha256
            or normalization.get("normalizer_sha256")
            != candidate_row["normalizer_sha256"]
            or normalization.get("source_artifact_sha256")
            != candidate_row["artifact_sha256"]
            or normalization.get("normalized_artifact_sha256")
            != content_hash(dict(normalized))
            or normalization.get("deterministic_replay") is not True
            or normalization.get("authority")
            != "registered_adapter_witness_normalizer"
        ):
            raise ValueError("witness normalization receipt crossed candidate identity")

    verification = None
    if verification_raw is not None:
        verification = _validate_content_receipt(
            verification_raw,
            schema=WITNESS_VERIFICATION_RECEIPT_SCHEMA,
            required={
                "schema",
                "contract_sha256",
                "candidate_envelope_sha256",
                "predicate_sha256",
                "witness_schema_sha256",
                "verifier_sha256",
                "normalized_artifact_sha256",
                "outcome",
                "observed",
                "evidence_refs",
                "deterministic_replay",
                "authority",
            },
        )
        refs = verification.get("evidence_refs")
        if (
            normalized is None
            or verification.get("contract_sha256") != contract.sha256
            or verification.get("candidate_envelope_sha256")
            != candidate.receipt_sha256
            or verification.get("predicate_sha256") != candidate_row["predicate_sha256"]
            or verification.get("witness_schema_sha256")
            != candidate_row["witness_schema_sha256"]
            or verification.get("verifier_sha256") != candidate_row["verifier_sha256"]
            or verification.get("normalized_artifact_sha256")
            != content_hash(dict(normalized))
            or verification.get("outcome") not in _VERIFIER_OUTCOMES
            or not isinstance(refs, list)
            or any(not str(ref).strip() for ref in refs)
            or verification.get("deterministic_replay") is not True
            or verification.get("authority")
            != "registered_adapter_witness_verifier"
        ):
            raise ValueError("witness verification receipt crossed candidate identity")
        _json_data(verification.get("observed"), context="witness verification")

    status = str(row["status"])
    if status in {"witness_verified", "witness_rejected"}:
        expected_outcome = "accepted" if status == "witness_verified" else "rejected"
        if (
            row.get("stage") != "complete"
            or normalized is None
            or normalization is None
            or verification is None
            or verification.get("outcome") != expected_outcome
        ):
            raise ValueError("completed witness result lacks its deterministic receipts")
    elif row.get("stage") not in {"normalization", "verification"}:
        raise ValueError("unavailable witness result has an invalid stage")
    elif row.get("stage") == "normalization" and any(
        value is not None for value in (normalized, normalization, verification)
    ):
        raise ValueError("normalization-unavailable result carries downstream evidence")
    elif row.get("stage") == "verification" and (
        normalized is None
        or normalization is None
        or (
            verification is not None
            and verification.get("outcome") != "unavailable"
        )
    ):
        raise ValueError("verification-unavailable result changed its evidence boundary")
    return row


def adjudicate_governed_witness_construction_task(
    *,
    contract: TaskDischargeContract,
    boundary_result: Mapping[str, Any],
) -> TaskDischargeReceipt:
    """Project one immutable witness boundary row into task-discharge algebra."""

    parameters = witness_construction_parameters(contract)
    candidate = WitnessConstructionCandidateEnvelope.from_json(
        parameters["candidate_envelope"]
    )
    if boundary_result.get("schema") != "leanmill.frontier_boundary_result.v1":
        raise ValueError("witness task requires a frontier boundary result")
    boundary_core = {
        key: value
        for key, value in boundary_result.items()
        if key != "result_sha256"
    }
    boundary_ref = str(boundary_result.get("result_sha256") or "")
    if not boundary_ref or boundary_ref != content_hash(boundary_core):
        raise ValueError("witness task boundary result digest mismatch")
    if boundary_result.get("context_hash") != parameters["context_hash"]:
        raise ValueError("witness task boundary crossed its context")
    rows = boundary_result.get("query_results")
    if not isinstance(rows, list):
        raise ValueError("witness task boundary query rows are malformed")
    matches = [
        dict(row)
        for row in rows
        if isinstance(row, Mapping)
        and row.get("candidate_kind") == "theory_task"
        and row.get("contract_sha256") == contract.sha256
        and row.get("adjudicator_id") == contract.adjudicator_id
    ]
    if len(matches) > 1:
        raise ValueError("witness task boundary duplicated one task identity")
    if not matches:
        return TaskDischargeReceipt(
            contract_sha256=contract.sha256,
            adjudicator_id=contract.adjudicator_id,
            status="unavailable",
            authority="leanmill.frontier_boundary",
            observed={
                "request_id": parameters["request_id"],
                "boundary_status": "not_observed",
            },
            evidence_refs=(boundary_ref,),
        )
    row = validate_witness_construction_boundary_result(contract, matches[0])
    boundary_status = str(row["status"])
    status = {
        "witness_verified": (
            "discharged"
            if candidate.discharge_policy == "verifier_acceptance_is_terminal"
            else "open"
        ),
        "witness_rejected": "open",
        "capability_unavailable": "unavailable",
    }[boundary_status]
    verification = row.get("verification_receipt")
    extra_refs: Sequence[str] = (
        tuple(str(ref) for ref in verification.get("evidence_refs") or ())
        if isinstance(verification, Mapping)
        else ()
    )
    observed = {
        "request_id": parameters["request_id"],
        "boundary_status": boundary_status,
        "candidate_envelope_sha256": row["candidate_envelope_sha256"],
        "normalized_artifact_sha256": (
            verification.get("normalized_artifact_sha256")
            if isinstance(verification, Mapping)
            else None
        ),
        "verifier_observed": (
            verification.get("observed")
            if isinstance(verification, Mapping)
            else None
        ),
        "claim_scope": parameters["claim_scope"],
        "discharge_policy": candidate.discharge_policy,
        "next_obligation": (
            "construction_artifact_ratification"
            if boundary_status == "witness_verified"
            and candidate.discharge_policy
            == "construction_artifact_ratification_required"
            else None
        ),
    }
    return TaskDischargeReceipt(
        contract_sha256=contract.sha256,
        adjudicator_id=contract.adjudicator_id,
        status=status,
        authority="leanmill.frontier_boundary",
        observed=observed,
        evidence_refs=tuple(
            dict.fromkeys(
                (
                    str(row["receipt_sha256"]),
                    *extra_refs,
                    boundary_ref,
                )
            )
        ),
    )


def validate_governed_witness_construction_task_receipt(
    contract: TaskDischargeContract | Mapping[str, Any],
    receipt: TaskDischargeReceipt | Mapping[str, Any],
) -> tuple[TaskDischargeContract, TaskDischargeReceipt]:
    """Replay one task receipt through its construction-specific authority."""

    frozen_contract, frozen_receipt = bind_task_discharge_receipt(
        contract, receipt
    )
    parameters = witness_construction_parameters(frozen_contract)
    candidate = WitnessConstructionCandidateEnvelope.from_json(
        parameters["candidate_envelope"]
    )
    observed = frozen_receipt.observed
    if (
        frozen_receipt.authority != "leanmill.frontier_boundary"
        or not isinstance(observed, Mapping)
        or not frozen_receipt.evidence_refs
    ):
        raise ValueError("witness task receipt has unsupported authority")
    boundary_status = str(observed.get("boundary_status") or "")
    if boundary_status == "not_observed":
        if (
            set(observed) != {"request_id", "boundary_status"}
            or observed.get("request_id") != parameters["request_id"]
            or frozen_receipt.status != "unavailable"
        ):
            raise ValueError("unobserved witness task receipt changed identity")
        return frozen_contract, frozen_receipt
    required = {
        "request_id",
        "boundary_status",
        "candidate_envelope_sha256",
        "normalized_artifact_sha256",
        "verifier_observed",
        "claim_scope",
        "discharge_policy",
        "next_obligation",
    }
    expected_status = {
        "witness_verified": (
            "discharged"
            if candidate.discharge_policy == "verifier_acceptance_is_terminal"
            else "open"
        ),
        "witness_rejected": "open",
        "capability_unavailable": "unavailable",
    }.get(boundary_status)
    expected_obligation = (
        "construction_artifact_ratification"
        if boundary_status == "witness_verified"
        and candidate.discharge_policy
        == "construction_artifact_ratification_required"
        else None
    )
    if (
        set(observed) != required
        or expected_status is None
        or frozen_receipt.status != expected_status
        or observed.get("request_id") != parameters["request_id"]
        or observed.get("candidate_envelope_sha256")
        != candidate.receipt_sha256
        or observed.get("claim_scope") != parameters["claim_scope"]
        or observed.get("discharge_policy") != candidate.discharge_policy
        or observed.get("next_obligation") != expected_obligation
    ):
        raise ValueError("witness task receipt changed construction identity")
    normalized = observed.get("normalized_artifact_sha256")
    verifier_observed = observed.get("verifier_observed")
    if boundary_status in {"witness_rejected", "witness_verified"}:
        _digest(normalized, context="normalized witness artifact")
        if not isinstance(verifier_observed, Mapping):
            raise ValueError("completed witness task receipt lost verifier evidence")
    elif normalized is not None:
        _digest(normalized, context="normalized witness artifact")
    return frozen_contract, frozen_receipt


__all__ = [
    "GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR",
    "GOVERNED_WITNESS_CONSTRUCTION_CAPABILITY",
    "REGISTERED_WITNESS_ARTIFACT_EXECUTION_SCHEMA",
    "WITNESS_CONSTRUCTION_BOUNDARY_RESULT_SCHEMA",
    "WITNESS_CONSTRUCTION_CANDIDATE_SCHEMA",
    "WITNESS_CONSTRUCTION_CLAIM_SCOPE",
    "WITNESS_CONSTRUCTION_INTERFACE_SCHEMA",
    "WITNESS_CONSTRUCTOR_AUTHORSHIP_SCHEMA",
    "WITNESS_CONSTRUCTOR_OUTPUT_SCHEMA",
    "WITNESS_CONSTRUCTOR_REQUEST_MEMORY_SCHEMA",
    "WITNESS_CONSTRUCTOR_REQUEST_SCHEMA",
    "WITNESS_CANDIDATE_OUTCOME_MEMORY_SCHEMA",
    "WitnessConstructionCandidateEnvelope",
    "WitnessConstructionCapabilityUnavailable",
    "WitnessConstructorUnavailable",
    "adjudicate_governed_witness_construction_task",
    "build_witness_construction_candidate",
    "build_witness_construction_interface",
    "build_witness_candidate_outcome_memory",
    "build_witness_constructor_output",
    "build_witness_constructor_request",
    "build_witness_construction_unavailable_result",
    "compile_governed_witness_construction_task",
    "execute_governed_witness_construction_task",
    "execute_registered_witness_artifact",
    "matching_witness_candidate_outcome",
    "validate_witness_construction_boundary_result",
    "validate_registered_witness_artifact_execution",
    "validate_witness_construction_interface",
    "validate_governed_witness_construction_task_receipt",
    "validate_witness_candidate_outcome_memory",
    "validate_witness_constructor_output",
    "validate_witness_constructor_request",
    "witness_construction_parameters",
]
