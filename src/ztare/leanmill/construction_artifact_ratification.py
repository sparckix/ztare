"""Kernel ratification successor for one verified construction artifact.

The upstream witness boundary owns normalization and deterministic predicate
replay.  This module owns the next lifecycle: bind that exact open receipt,
ask the registered adapter for a frozen Lean formalization interface and proof
term, then carry the resulting theorem through LeanMill's bounded
carried-theorem ratifier.
"""
from __future__ import annotations

from functools import partial
import re
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ztare.common.task_discharge import (
    TaskDischargeContract,
    TaskDischargeReceipt,
    bind_task_discharge_receipt,
)
from ztare.leanmill.governed_ratification import (
    normalized_target_signature,
    resolve_content_addressed_ratification_record,
    validate_governed_ratification_record,
)
from ztare.leanmill.data_only_json import strict_json_data
from ztare.leanmill.protocol_validation import (
    require_sha256_digest,
    validate_content_bound_row,
)
from ztare.leanmill.lean_source import (
    decl_blocks,
    decl_kind,
    has_sorry,
    open_decl_for_ratification,
    resolve_theorem_target,
    strip_comments,
)
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.witness_construction_boundary import (
    WITNESS_CONSTRUCTION_CLAIM_SCOPE,
    WitnessConstructionCandidateEnvelope,
    adjudicate_governed_witness_construction_task,
    validate_witness_construction_boundary_result,
    witness_construction_parameters,
)


CONSTRUCTION_ARTIFACT_FORMAL_INTERFACE_CAPABILITY = (
    "construction_artifact_formal_interface"
)
CONSTRUCTION_ARTIFACT_RATIFICATION_CAPABILITY = (
    "construction_artifact_ratification"
)
CONSTRUCTION_ARTIFACT_FORMAL_INPUT_SCHEMA = (
    "leanmill.construction_artifact_formal_input.v1"
)
CONSTRUCTION_ARTIFACT_FORMAL_INTERFACE_SCHEMA = (
    "leanmill.construction_artifact_formal_interface.v1"
)
CONSTRUCTION_ARTIFACT_PROOF_RECEIPT_SCHEMA = (
    "leanmill.construction_artifact_formal_proof.v1"
)
CONSTRUCTION_ARTIFACT_RATIFICATION_CONTRACT_SCHEMA = (
    "leanmill.construction_artifact_ratification_contract.v1"
)
CONSTRUCTION_ARTIFACT_RATIFICATION_CONTRACT_V2_SCHEMA = (
    "leanmill.construction_artifact_ratification_contract.v2"
)
CONSTRUCTION_ARTIFACT_RATIFICATION_RESULT_SCHEMA = (
    "leanmill.construction_artifact_ratification_result.v1"
)
CONSTRUCTION_ARTIFACT_RATIFICATION_RESULT_V2_SCHEMA = (
    "leanmill.construction_artifact_ratification_result.v2"
)
CONSTRUCTION_ARTIFACT_RATIFICATION_AGGREGATE_SCHEMA = (
    "leanmill.construction_artifact_ratification_aggregate.v1"
)
CONSTRUCTION_ARTIFACT_RATIFICATION_PROVIDER = (
    "construction_artifact_certificate"
)

_QUALIFIED_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)*")
_WRITTEN_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")
_FORBIDDEN_SOURCE_WORDS = (
    "sorry",
    "admit",
    "native_decide",
    "ofReduceBool",
)
_MAX_PROTOCOL_JSON_DEPTH = 128
_MAX_PROTOCOL_JSON_BYTES = 64_000_000
_MAX_PROTOCOL_INTEGER_BITS = 4_096
_MAX_FORMAL_SOURCE_COMPONENT_BYTES = 16_000_000
_MAX_FORMAL_PROOF_BYTES = 16_000_000
_MAX_CLOSED_FORMAL_SOURCE_BYTES = 32_000_000
_MAX_FORMAL_IDENTIFIER_BYTES = 4_096
_MAX_FORMAL_SIGNATURE_BYTES = 1_000_000


class ConstructionArtifactRatificationCapabilityUnavailable(RuntimeError):
    """The registered adapter cannot yet produce the required Lean artifact."""


class ConstructionArtifactRatificationResourceUnavailable(RuntimeError):
    """A bounded formalization input cannot enter the kernel action."""

    def __init__(
        self,
        reason_code: str,
        *,
        resource: str,
        observed: int,
        ceiling: int,
    ) -> None:
        if (
            type(reason_code) is not str
            or not reason_code
            or type(resource) is not str
            or not resource
            or type(observed) is not int
            or observed < 0
            or type(ceiling) is not int
            or ceiling < 0
        ):
            raise ValueError("construction ratification resource metadata is malformed")
        self.reason_code = reason_code
        self.resource = resource
        self.observed = observed
        self.ceiling = ceiling
        super().__init__(reason_code)


def _json_data(value: Any, *, context: str) -> Any:
    if hasattr(value, "to_dict") and type(value) not in {
        dict,
        list,
        str,
        int,
        float,
        bool,
    }:
        value = value.to_dict()
    if isinstance(value, Mapping) and type(value) is not dict:
        value = dict(value)
    elif isinstance(value, tuple):
        value = list(value)
    try:
        return strict_json_data(
            value,
            context=context,
            max_depth=_MAX_PROTOCOL_JSON_DEPTH,
            max_wire_bytes=_MAX_PROTOCOL_JSON_BYTES,
            max_integer_bits=_MAX_PROTOCOL_INTEGER_BITS,
            allow_finite_floats=True,
        )
    except ValueError as exc:
        message = str(exc)
        if "maximum JSON nesting depth" in message:
            raise ConstructionArtifactRatificationResourceUnavailable(
                "construction_formal_json_depth_limit_exhausted",
                resource="formal_protocol_json_depth",
                observed=_MAX_PROTOCOL_JSON_DEPTH + 1,
                ceiling=_MAX_PROTOCOL_JSON_DEPTH,
            ) from exc
        if "maximum JSON wire size" in message:
            raise ConstructionArtifactRatificationResourceUnavailable(
                "construction_formal_json_byte_limit_exhausted",
                resource="formal_protocol_json_bytes",
                observed=_MAX_PROTOCOL_JSON_BYTES + 1,
                ceiling=_MAX_PROTOCOL_JSON_BYTES,
            ) from exc
        if "JSON integer bit ceiling" in message:
            raise ConstructionArtifactRatificationResourceUnavailable(
                "construction_formal_json_integer_limit_exhausted",
                resource="formal_protocol_integer_bits",
                observed=_MAX_PROTOCOL_INTEGER_BITS + 1,
                ceiling=_MAX_PROTOCOL_INTEGER_BITS,
            ) from exc
        raise


_digest = require_sha256_digest
_content_bound = partial(validate_content_bound_row, copy_json=_json_data)


def _bounded_formal_text(
    value: Any,
    *,
    context: str,
    maximum_bytes: int,
    strip: bool = False,
) -> str:
    if type(value) is not str:
        raise TypeError(f"{context} must be a string")
    text = value.strip() if strip else value
    observed = len(text.encode("utf-8"))
    if observed > maximum_bytes:
        resource = re.sub(r"[^a-z0-9]+", "_", context.lower()).strip("_")
        raise ConstructionArtifactRatificationResourceUnavailable(
            resource + "_limit_exhausted",
            resource=resource + "_bytes",
            observed=observed,
            ceiling=maximum_bytes,
        )
    return text


def _matching_witness_row(
    task_contract: TaskDischargeContract,
    outer_boundary_result: Mapping[str, Any],
) -> dict[str, Any]:
    rows = outer_boundary_result.get("query_results")
    if not isinstance(rows, list):
        raise ValueError("frontier boundary query rows are malformed")
    matches = [
        dict(row)
        for row in rows
        if isinstance(row, Mapping)
        and row.get("candidate_kind") == "theory_task"
        and row.get("contract_sha256") == task_contract.sha256
        and row.get("adjudicator_id") == task_contract.adjudicator_id
    ]
    if len(matches) != 1:
        raise ValueError("ratification requires exactly one governed witness row")
    return validate_witness_construction_boundary_result(task_contract, matches[0])


def _verified_witness_join(
    task_contract: TaskDischargeContract,
    outer_boundary_result: Mapping[str, Any],
    prior_open_receipt: TaskDischargeReceipt | Mapping[str, Any],
) -> tuple[
    dict[str, Any],
    TaskDischargeReceipt,
    WitnessConstructionCandidateEnvelope,
]:
    """Re-adjudicate the outer boundary before any formal contract is minted."""

    outer = _json_data(outer_boundary_result, context="frontier boundary result")
    if not isinstance(outer, dict):
        raise TypeError("frontier boundary result must be an object")
    replayed = adjudicate_governed_witness_construction_task(
        contract=task_contract,
        boundary_result=outer,
    )
    _bound_contract, supplied = bind_task_discharge_receipt(
        task_contract, prior_open_receipt
    )
    if supplied.to_dict() != replayed.to_dict():
        raise ValueError("prior open receipt is not the replayed frontier adjudication")
    observed = supplied.observed if isinstance(supplied.observed, Mapping) else {}
    if (
        supplied.status != "open"
        or observed.get("next_obligation")
        != CONSTRUCTION_ARTIFACT_RATIFICATION_CAPABILITY
        or observed.get("discharge_policy")
        != "construction_artifact_ratification_required"
    ):
        raise ValueError("task is not at the construction-ratification transition")
    row = _matching_witness_row(task_contract, outer)
    if row.get("status") != "witness_verified":
        raise ValueError("construction ratification requires a verified witness")
    parameters = witness_construction_parameters(task_contract)
    candidate = WitnessConstructionCandidateEnvelope.from_json(
        parameters["candidate_envelope"]
    )
    verification = row.get("verification_receipt")
    if (
        candidate.discharge_policy
        != "construction_artifact_ratification_required"
        or not isinstance(row.get("normalized_artifact"), Mapping)
        or not isinstance(row.get("normalization_receipt"), Mapping)
        or not isinstance(verification, Mapping)
        or verification.get("outcome") != "accepted"
    ):
        raise ValueError("verified witness lacks its frozen ratification inputs")
    return row, supplied, candidate


def build_construction_artifact_formal_input(
    task_contract: TaskDischargeContract,
    outer_boundary_result: Mapping[str, Any],
    prior_open_receipt: TaskDischargeReceipt | Mapping[str, Any],
) -> dict[str, Any]:
    row, supplied, candidate = _verified_witness_join(
        task_contract, outer_boundary_result, prior_open_receipt
    )
    candidate_row = candidate.to_json()
    normalization = dict(row["normalization_receipt"])
    verification = dict(row["verification_receipt"])
    normalized = dict(row["normalized_artifact"])
    core = {
        "schema": CONSTRUCTION_ARTIFACT_FORMAL_INPUT_SCHEMA,
        "task_contract_sha256": task_contract.sha256,
        "outer_boundary_result_sha256": str(
            outer_boundary_result.get("result_sha256") or ""
        ),
        "prior_open_discharge_receipt_sha256": supplied.sha256,
        "boundary_result_receipt_sha256": str(row["receipt_sha256"]),
        "candidate_envelope_sha256": candidate.receipt_sha256,
        "request_id": candidate.request_id,
        "context_hash": candidate.context_hash,
        "adapter_id": candidate.adapter_id,
        "interface_sha256": candidate.interface_sha256,
        "target_config_sha256": candidate.target_config_sha256,
        "predicate_ir": dict(candidate.predicate_ir),
        "predicate_sha256": str(candidate_row["predicate_sha256"]),
        "witness_schema": dict(candidate.witness_schema),
        "witness_schema_sha256": str(candidate_row["witness_schema_sha256"]),
        "normalized_artifact": normalized,
        "normalized_artifact_sha256": content_hash(normalized),
        "normalization_receipt_sha256": str(normalization["receipt_sha256"]),
        "verification_receipt_sha256": str(verification["receipt_sha256"]),
        "claim_scope": WITNESS_CONSTRUCTION_CLAIM_SCOPE,
        "discharge_policy": candidate.discharge_policy,
        "authority": "governed_witness_to_formal_ratification_join",
    }
    return validate_construction_artifact_formal_input(
        {**core, "input_sha256": content_hash(core)}
    )


def validate_construction_artifact_formal_input(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if value.get("schema") == "leanmill.reviewed_family_member_formal_input.v1":
        from ztare.leanmill.reviewed_family_member_ratification import (
            validate_reviewed_family_member_formal_input,
        )

        return validate_reviewed_family_member_formal_input(value)
    required = {
        "schema", "task_contract_sha256", "outer_boundary_result_sha256",
        "prior_open_discharge_receipt_sha256", "boundary_result_receipt_sha256",
        "candidate_envelope_sha256", "request_id", "context_hash", "adapter_id",
        "interface_sha256", "target_config_sha256", "predicate_ir",
        "predicate_sha256", "witness_schema", "witness_schema_sha256",
        "normalized_artifact", "normalized_artifact_sha256",
        "normalization_receipt_sha256", "verification_receipt_sha256",
        "claim_scope", "discharge_policy", "authority",
    }
    row = _content_bound(
        value,
        schema=CONSTRUCTION_ARTIFACT_FORMAL_INPUT_SCHEMA,
        digest_field="input_sha256",
        required=required,
        context="construction-artifact formal input",
    )
    for field in (
        "task_contract_sha256", "outer_boundary_result_sha256",
        "prior_open_discharge_receipt_sha256", "boundary_result_receipt_sha256",
        "candidate_envelope_sha256", "interface_sha256", "target_config_sha256",
        "predicate_sha256", "witness_schema_sha256", "normalized_artifact_sha256",
        "normalization_receipt_sha256", "verification_receipt_sha256",
    ):
        _digest(row[field], context=field)
    if (
        not all(str(row.get(field) or "").strip() for field in (
            "request_id", "context_hash", "adapter_id"
        ))
        or not isinstance(row.get("predicate_ir"), Mapping)
        or not isinstance(row.get("witness_schema"), Mapping)
        or not isinstance(row.get("normalized_artifact"), Mapping)
        or row["predicate_sha256"] != content_hash(row["predicate_ir"])
        or row["witness_schema_sha256"] != content_hash(row["witness_schema"])
        or row["normalized_artifact_sha256"]
        != content_hash(row["normalized_artifact"])
        or row.get("claim_scope") != WITNESS_CONSTRUCTION_CLAIM_SCOPE
        or row.get("discharge_policy")
        != "construction_artifact_ratification_required"
        or row.get("authority") != "governed_witness_to_formal_ratification_join"
    ):
        raise ValueError("construction-artifact formal input crossed witness identity")
    return row


def _forbidden_formal_source(source: str) -> str:
    clean = strip_comments(source or "")
    for word in _FORBIDDEN_SOURCE_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", clean):
            return word
    if re.search(r"\bunsafe\b", clean):
        return "unsafe"
    for _name, block in decl_blocks(clean):
        kind = decl_kind(block)
        if kind in {"axiom", "opaque"}:
            return str(kind)
        if kind in {"def", "abbrev"}:
            from ztare.leanmill.solver.autoformalize import _degenerate_def_body

            if _degenerate_def_body(block) is not None:
                return "degenerate_definition"
    return ""


def build_construction_artifact_formal_interface(
    formal_input: Mapping[str, Any],
    *,
    adapter_id: str,
    certificate_capability_id: str,
    target_selector: str,
    target_written_name: str,
    target_signature: str,
    source_prefix: str,
    source_suffix: str,
    claim_predicate: str,
    artifact_constructor: str,
) -> dict[str, Any]:
    frozen_input = validate_construction_artifact_formal_input(formal_input)
    core = {
        "schema": CONSTRUCTION_ARTIFACT_FORMAL_INTERFACE_SCHEMA,
        "adapter_id": str(adapter_id),
        "certificate_capability_id": str(certificate_capability_id),
        "target_selector": str(target_selector),
        "target_written_name": str(target_written_name),
        "target_signature": " ".join(str(target_signature).split()),
        "source_prefix": str(source_prefix),
        "source_suffix": str(source_suffix),
        "claim_predicate": str(claim_predicate),
        "artifact_constructor": str(artifact_constructor),
        "formal_input_sha256": str(frozen_input["input_sha256"]),
        "claim_boundary": (
            "reviewed_adapter_compiles_exact_artifact_and_predicate_to_one_lean_proposition"
        ),
        "authority": "registered_adapter_construction_formal_interface",
    }
    return validate_construction_artifact_formal_interface(
        frozen_input, {**core, "interface_sha256": content_hash(core)}
    )


def validate_construction_artifact_formal_interface(
    formal_input: Mapping[str, Any],
    value: Mapping[str, Any],
) -> dict[str, Any]:
    frozen_input = validate_construction_artifact_formal_input(formal_input)
    required = {
        "schema", "adapter_id", "certificate_capability_id", "target_selector",
        "target_written_name", "target_signature", "source_prefix", "source_suffix",
        "claim_predicate", "artifact_constructor", "formal_input_sha256",
        "claim_boundary", "authority",
    }
    row = _content_bound(
        value,
        schema=CONSTRUCTION_ARTIFACT_FORMAL_INTERFACE_SCHEMA,
        digest_field="interface_sha256",
        required=required,
        context="construction-artifact formal interface",
    )
    target = _bounded_formal_text(
        row.get("target_selector"),
        context="construction target selector",
        maximum_bytes=_MAX_FORMAL_IDENTIFIER_BYTES,
    )
    written = _bounded_formal_text(
        row.get("target_written_name"),
        context="construction target written name",
        maximum_bytes=_MAX_FORMAL_IDENTIFIER_BYTES,
    )
    signature = " ".join(
        _bounded_formal_text(
            row.get("target_signature"),
            context="construction target signature",
            maximum_bytes=_MAX_FORMAL_SIGNATURE_BYTES,
        ).split()
    )
    predicate = _bounded_formal_text(
        row.get("claim_predicate"),
        context="construction claim predicate",
        maximum_bytes=_MAX_FORMAL_IDENTIFIER_BYTES,
    )
    constructor = _bounded_formal_text(
        row.get("artifact_constructor"),
        context="construction artifact constructor",
        maximum_bytes=_MAX_FORMAL_IDENTIFIER_BYTES,
    )
    source_prefix = _bounded_formal_text(
        row.get("source_prefix"),
        context="construction formal source prefix",
        maximum_bytes=_MAX_FORMAL_SOURCE_COMPONENT_BYTES,
    )
    source_suffix = _bounded_formal_text(
        row.get("source_suffix"),
        context="construction formal source suffix",
        maximum_bytes=_MAX_FORMAL_SOURCE_COMPONENT_BYTES,
    )
    forbidden = _forbidden_formal_source(
        source_prefix + "\n" + source_suffix
    )
    if (
        row.get("adapter_id") != frozen_input["adapter_id"]
        or row.get("formal_input_sha256") != frozen_input["input_sha256"]
        or not str(row.get("certificate_capability_id") or "").strip()
        or not _QUALIFIED_NAME.fullmatch(target)
        or not _WRITTEN_NAME.fullmatch(written)
        or target.rsplit(".", 1)[-1] != written
        or not signature.startswith(": ")
        or signature in {": True", ": Prop"}
        or not _QUALIFIED_NAME.fullmatch(predicate)
        or not _QUALIFIED_NAME.fullmatch(constructor)
        or predicate == constructor
        or predicate not in signature
        or constructor not in signature
        or forbidden
        or row.get("claim_boundary")
        != "reviewed_adapter_compiles_exact_artifact_and_predicate_to_one_lean_proposition"
        or row.get("authority")
        != "registered_adapter_construction_formal_interface"
    ):
        raise ValueError("construction-artifact formal interface is not a semantic theorem bridge")
    return row


def build_construction_artifact_ratification_contract(
    task_contract: TaskDischargeContract,
    outer_boundary_result: Mapping[str, Any],
    prior_open_receipt: TaskDischargeReceipt | Mapping[str, Any],
    formal_interface: Mapping[str, Any],
) -> dict[str, Any]:
    formal_input = build_construction_artifact_formal_input(
        task_contract, outer_boundary_result, prior_open_receipt
    )
    interface = validate_construction_artifact_formal_interface(
        formal_input, formal_interface
    )
    core = {
        "schema": CONSTRUCTION_ARTIFACT_RATIFICATION_CONTRACT_SCHEMA,
        "formal_input": formal_input,
        "formal_interface": interface,
        "lifecycle_transition": (
            "verified_governed_witness_to_kernel_ratification"
        ),
        "authority": "leanmill.construction_artifact_ratification_contract",
    }
    return validate_construction_artifact_ratification_contract_record(
        {**core, "contract_sha256": content_hash(core)}
    )


def build_construction_artifact_ratification_contract_from_formal_input(
    formal_input: Mapping[str, Any],
    formal_interface: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind any admitted verified-artifact origin to the common kernel action."""

    frozen_input = validate_construction_artifact_formal_input(formal_input)
    interface = validate_construction_artifact_formal_interface(
        frozen_input, formal_interface
    )
    core = {
        "schema": CONSTRUCTION_ARTIFACT_RATIFICATION_CONTRACT_V2_SCHEMA,
        "formal_input": frozen_input,
        "formal_interface": interface,
        "lifecycle_transition": (
            "verified_construction_artifact_to_kernel_ratification"
        ),
        "authority": "leanmill.construction_artifact_ratification_contract",
    }
    return validate_construction_artifact_ratification_contract_record(
        {**core, "contract_sha256": content_hash(core)}
    )


def validate_construction_artifact_ratification_contract_record(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    required = {
        "schema", "formal_input", "formal_interface", "lifecycle_transition",
        "authority",
    }
    schema = str(value.get("schema") or "")
    if schema not in {
        CONSTRUCTION_ARTIFACT_RATIFICATION_CONTRACT_SCHEMA,
        CONSTRUCTION_ARTIFACT_RATIFICATION_CONTRACT_V2_SCHEMA,
    }:
        raise ValueError("construction-artifact ratification contract schema changed")
    row = _content_bound(
        value,
        schema=schema,
        digest_field="contract_sha256",
        required=required,
        context="construction-artifact ratification contract",
    )
    formal_input = validate_construction_artifact_formal_input(row["formal_input"])
    interface = validate_construction_artifact_formal_interface(
        formal_input, row["formal_interface"]
    )
    expected_transition = (
        "verified_governed_witness_to_kernel_ratification"
        if schema == CONSTRUCTION_ARTIFACT_RATIFICATION_CONTRACT_SCHEMA
        else "verified_construction_artifact_to_kernel_ratification"
    )
    if (
        interface["formal_input_sha256"] != formal_input["input_sha256"]
        or row.get("lifecycle_transition") != expected_transition
        or row.get("authority")
        != "leanmill.construction_artifact_ratification_contract"
    ):
        raise ValueError("construction-artifact ratification contract crossed identity")
    return row


def build_construction_artifact_proof_receipt(
    ratification_contract: Mapping[str, Any],
    *,
    proof_text: str,
) -> dict[str, Any]:
    contract = validate_construction_artifact_ratification_contract_record(
        ratification_contract
    )
    proof = _bounded_formal_text(
        proof_text,
        context="construction formal proof",
        maximum_bytes=_MAX_FORMAL_PROOF_BYTES,
        strip=True,
    )
    if not proof or _forbidden_formal_source(proof):
        raise ValueError("construction-artifact proof uses a forbidden trust shortcut")
    core = {
        "schema": CONSTRUCTION_ARTIFACT_PROOF_RECEIPT_SCHEMA,
        "ratification_contract_sha256": contract["contract_sha256"],
        "formal_interface_sha256": contract["formal_interface"]["interface_sha256"],
        "proof_text": proof,
        "proof_sha256": content_hash({"proof_text": proof}),
        "authority": "registered_adapter_construction_formal_certificate",
    }
    return validate_construction_artifact_proof_receipt(
        contract, {**core, "receipt_sha256": content_hash(core)}
    )


def validate_construction_artifact_proof_receipt(
    ratification_contract: Mapping[str, Any],
    value: Mapping[str, Any],
) -> dict[str, Any]:
    contract = validate_construction_artifact_ratification_contract_record(
        ratification_contract
    )
    required = {
        "schema", "ratification_contract_sha256", "formal_interface_sha256",
        "proof_text", "proof_sha256", "authority",
    }
    row = _content_bound(
        value,
        schema=CONSTRUCTION_ARTIFACT_PROOF_RECEIPT_SCHEMA,
        digest_field="receipt_sha256",
        required=required,
        context="construction-artifact proof receipt",
    )
    proof = _bounded_formal_text(
        row.get("proof_text"),
        context="construction formal proof",
        maximum_bytes=_MAX_FORMAL_PROOF_BYTES,
        strip=True,
    )
    if (
        row["ratification_contract_sha256"] != contract["contract_sha256"]
        or row["formal_interface_sha256"]
        != contract["formal_interface"]["interface_sha256"]
        or row["proof_sha256"] != content_hash({"proof_text": proof})
        or not proof
        or _forbidden_formal_source(proof)
        or row.get("authority")
        != "registered_adapter_construction_formal_certificate"
    ):
        raise ValueError("construction-artifact proof receipt crossed its contract")
    return row


def render_construction_artifact_certificate(
    ratification_contract: Mapping[str, Any],
    proof_receipt: Mapping[str, Any],
) -> tuple[str, str, str, str]:
    """Return ``closed source, posed source, carried proof, target selector``."""

    contract = validate_construction_artifact_ratification_contract_record(
        ratification_contract
    )
    proof = validate_construction_artifact_proof_receipt(contract, proof_receipt)
    interface = contract["formal_interface"]
    source_prefix = _bounded_formal_text(
        interface["source_prefix"],
        context="construction formal source prefix",
        maximum_bytes=_MAX_FORMAL_SOURCE_COMPONENT_BYTES,
    )
    source_suffix = _bounded_formal_text(
        interface["source_suffix"],
        context="construction formal source suffix",
        maximum_bytes=_MAX_FORMAL_SOURCE_COMPONENT_BYTES,
    )
    proof_text = _bounded_formal_text(
        proof["proof_text"],
        context="construction formal proof",
        maximum_bytes=_MAX_FORMAL_PROOF_BYTES,
        strip=True,
    )
    declaration = (
        f"theorem {interface['target_written_name']} "
        f"{interface['target_signature']} := {proof_text}"
    )
    projected_closed_bytes = sum(
        len(part.encode("utf-8"))
        for part in (
            source_prefix.rstrip(),
            "\n\n",
            declaration,
            "\n",
            source_suffix.lstrip(),
        )
    )
    if projected_closed_bytes > _MAX_CLOSED_FORMAL_SOURCE_BYTES:
        raise ConstructionArtifactRatificationResourceUnavailable(
            "closed_construction_certificate_byte_limit_exhausted",
            resource="closed_construction_certificate_bytes",
            observed=projected_closed_bytes,
            ceiling=_MAX_CLOSED_FORMAL_SOURCE_BYTES,
        )
    closed = (
        source_prefix.rstrip()
        + "\n\n"
        + declaration
        + "\n"
        + source_suffix.lstrip()
    )
    forbidden = _forbidden_formal_source(closed)
    if forbidden or has_sorry(closed):
        raise ValueError("closed construction certificate contains a forbidden declaration")
    target = str(interface["target_selector"])
    identity = resolve_theorem_target(closed, target)
    if identity is None:
        raise ValueError("construction certificate target is absent or ambiguous")
    target_blocks = [
        (name, block)
        for name, block in decl_blocks(closed)
        if name == interface["target_written_name"]
    ]
    if len(target_blocks) != 1 or decl_kind(target_blocks[0][1]) not in {
        "theorem", "lemma"
    }:
        raise ValueError("construction certificate target is not one theorem")
    if normalized_target_signature(closed, target) != interface["target_signature"]:
        raise ValueError("construction certificate changed its frozen signature")
    posed, carried = open_decl_for_ratification(closed, target)
    if carried.strip() != proof_text:
        raise ValueError("construction certificate changed its proof bytes")
    return closed, posed, carried, target


def _ratification_result(
    formal_input: Mapping[str, Any],
    *,
    status: str,
    stage: str,
    reason_code: str,
    ratification_contract: Mapping[str, Any] | None,
    proof_receipt: Mapping[str, Any] | None,
    governed_solver_result: Mapping[str, Any] | None,
    closure_record_ref: Mapping[str, Any] | None,
    resource_unavailable: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if status not in {"ratified", "open", "unavailable"}:
        raise ValueError("construction ratification status is unsupported")
    frozen_input = validate_construction_artifact_formal_input(formal_input)
    solver_result = (
        _json_data(governed_solver_result, context="governed solver result")
        if governed_solver_result is not None else None
    )
    core = {
        "schema": CONSTRUCTION_ARTIFACT_RATIFICATION_RESULT_V2_SCHEMA,
        "formal_input": frozen_input,
        "ratification_contract": (
            dict(ratification_contract) if ratification_contract is not None else None
        ),
        "proof_receipt": dict(proof_receipt) if proof_receipt is not None else None,
        "governed_solver_result": solver_result,
        "closure_record_ref": (
            dict(closure_record_ref) if closure_record_ref is not None else None
        ),
        "status": status,
        "stage": str(stage),
        "reason_code": str(reason_code),
        "resource_unavailable": (
            dict(resource_unavailable)
            if resource_unavailable is not None
            else None
        ),
        "authority": "leanmill.construction_artifact_ratification",
    }
    return validate_construction_artifact_ratification_result(
        {**core, "receipt_sha256": content_hash(core)}
    )


def validate_construction_artifact_ratification_result(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    base_required = {
        "schema", "formal_input", "ratification_contract", "proof_receipt",
        "governed_solver_result", "closure_record_ref", "status", "stage",
        "reason_code", "authority",
    }
    schema = str(value.get("schema") or "")
    if schema not in {
        CONSTRUCTION_ARTIFACT_RATIFICATION_RESULT_SCHEMA,
        CONSTRUCTION_ARTIFACT_RATIFICATION_RESULT_V2_SCHEMA,
    }:
        raise ValueError("construction-artifact ratification result schema changed")
    required = set(base_required)
    if schema == CONSTRUCTION_ARTIFACT_RATIFICATION_RESULT_V2_SCHEMA:
        required.add("resource_unavailable")
    row = _content_bound(
        value,
        schema=schema,
        digest_field="receipt_sha256",
        required=required,
        context="construction-artifact ratification result",
    )
    formal_input = validate_construction_artifact_formal_input(row["formal_input"])
    contract = row.get("ratification_contract")
    proof = row.get("proof_receipt")
    solver = row.get("governed_solver_result")
    closure_ref = row.get("closure_record_ref")
    resource = row.get("resource_unavailable")
    if contract is not None:
        contract = validate_construction_artifact_ratification_contract_record(contract)
    if proof is not None:
        if contract is None:
            raise ValueError("formal proof receipt lacks its ratification contract")
        proof = validate_construction_artifact_proof_receipt(contract, proof)
    if row.get("status") not in {"ratified", "open", "unavailable"} or not str(
        row.get("reason_code") or ""
    ).strip():
        raise ValueError("construction-artifact ratification result is untyped")
    if resource is not None:
        if (
            not isinstance(resource, Mapping)
            or set(resource) != {"reason_code", "resource", "observed", "ceiling"}
            or resource.get("reason_code") != row.get("reason_code")
            or type(resource.get("resource")) is not str
            or not resource.get("resource")
            or type(resource.get("observed")) is not int
            or int(resource["observed"]) < 0
            or type(resource.get("ceiling")) is not int
            or int(resource["ceiling"]) < 0
            or row.get("status") != "unavailable"
        ):
            raise ValueError(
                "construction-artifact resource unavailability is malformed"
            )
    if (
        (contract is not None and contract["formal_input"] != formal_input)
        or (proof is not None and proof["ratification_contract_sha256"]
            != contract["contract_sha256"])
        or row.get("authority") != "leanmill.construction_artifact_ratification"
    ):
        raise ValueError("construction-artifact ratification result crossed identity")
    if row["status"] == "ratified":
        if (
            row.get("stage") != "complete"
            or contract is None
            or proof is None
            or solver is None
            or not isinstance(closure_ref, Mapping)
            or set(closure_ref) != {"ledger", "record_sha256"}
        ):
            raise ValueError("ratified construction result lacks governed evidence")
        _digest(closure_ref["record_sha256"], context="closure record")
    elif closure_ref is not None:
        raise ValueError("non-ratified construction result carries closure credit")
    return row


def replay_ratified_construction_artifact_result(
    value: Mapping[str, Any],
    *,
    closure_record: Mapping[str, Any] | None = None,
    repo_root: str | Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Replay one ratified result against its exact governed certificate.

    ``closure_record`` is the content-addressed record copied into a durable
    successor artifact.  When it is absent, the record is resolved from the
    ledger reference carried by the result.  Either route verifies the same
    digest and then re-renders the frozen theorem before governance replay.
    """

    row = validate_construction_artifact_ratification_result(value)
    if row["status"] != "ratified":
        raise ValueError("authoritative replay requires a ratified construction result")

    contract = row["ratification_contract"]
    proof = row["proof_receipt"]
    _closed, posed, carried, target = render_construction_artifact_certificate(
        contract, proof
    )
    goal = str(contract["formal_interface"]["target_signature"])
    raw_solver = row["governed_solver_result"]
    closure_ref = row["closure_record_ref"]
    results = raw_solver.get("results") if isinstance(raw_solver, Mapping) else None
    primary = results[0] if isinstance(results, list) and len(results) == 1 else None
    providers = primary.get("providers_tried") if isinstance(primary, Mapping) else None
    provider = (
        providers[0]
        if isinstance(providers, list) and len(providers) == 1
        else None
    )
    if (
        not isinstance(primary, Mapping)
        or primary.get("outcome") != "closed"
        or primary.get("provider") != CONSTRUCTION_ARTIFACT_RATIFICATION_PROVIDER
        or str(primary.get("proof_text") or "").strip() != carried.strip()
        or not isinstance(provider, Mapping)
        or provider.get("provider") != CONSTRUCTION_ARTIFACT_RATIFICATION_PROVIDER
        or provider.get("agent_kind") != "preverified_champion"
        or raw_solver.get("outcome") != "closed"
        or raw_solver.get("ratification_only") is not True
        or type(raw_solver.get("provider_calls")) is not int
        or raw_solver.get("provider_calls") != 0
        or type(raw_solver.get("closure_candidates")) is not int
        or raw_solver.get("closure_candidates") != 1
        or str(raw_solver.get("closure_certificate") or "")
        != str(closure_ref["ledger"])
        or str(raw_solver.get("closure_certificate_record_sha256") or "")
        != str(closure_ref["record_sha256"])
    ):
        raise ValueError(
            "ratified construction result lacks its exact provider-free solver outcome"
        )

    if closure_record is None:
        _ledger_path, selected = resolve_content_addressed_ratification_record(
            str(closure_ref["ledger"]),
            str(closure_ref["record_sha256"]),
            repo_root=repo_root,
        )
    else:
        selected = _json_data(
            closure_record, context="governed construction closure record"
        )
        if not isinstance(selected, dict):
            raise TypeError("governed construction closure record must be an object")
        if content_hash(selected) != closure_ref["record_sha256"]:
            raise ValueError("supplied governed closure record digest mismatch")

    governed_record = validate_governed_ratification_record(
        selected,
        target=target,
        expected_signature=goal,
        posed_source=posed,
        proof_text=carried,
        goal=goal,
        expected_provider=CONSTRUCTION_ARTIFACT_RATIFICATION_PROVIDER,
    )
    if (
        raw_solver.get("governance") != governed_record.get("governance")
        or primary.get("contract_validation")
        != governed_record.get("solver_validation")
        or primary.get("matched_negative_control")
        != governed_record.get("matched_negative_control")
        or raw_solver.get("closure_lean") != governed_record.get("closure_lean")
    ):
        raise ValueError("governed closure record crossed its raw solver receipt")
    return row, governed_record


def _final_task_receipt(
    task_contract: TaskDischargeContract,
    result: Mapping[str, Any],
) -> TaskDischargeReceipt:
    row = validate_construction_artifact_ratification_result(result)
    formal_input = row["formal_input"]
    contract = row.get("ratification_contract") or {}
    proof = row.get("proof_receipt") or {}
    closure = row.get("closure_record_ref") or {}
    status = "discharged" if row["status"] == "ratified" else "open"
    evidence: list[str] = [
        str(formal_input["outer_boundary_result_sha256"]),
        str(formal_input["prior_open_discharge_receipt_sha256"]),
        str(formal_input["boundary_result_receipt_sha256"]),
        str(row["receipt_sha256"]),
    ]
    evidence.extend(
        str(value)
        for value in (
            contract.get("contract_sha256"),
            proof.get("receipt_sha256"),
            closure.get("record_sha256"),
        )
        if value
    )
    observed = {
        "request_id": formal_input["request_id"],
        "context_hash": formal_input["context_hash"],
        "adapter_id": formal_input["adapter_id"],
        "outer_boundary_result_sha256": formal_input[
            "outer_boundary_result_sha256"
        ],
        "prior_open_discharge_receipt_sha256": formal_input[
            "prior_open_discharge_receipt_sha256"
        ],
        "ratification_result_sha256": row["receipt_sha256"],
        "ratification_contract_sha256": contract.get("contract_sha256"),
        "normalized_artifact_sha256": formal_input[
            "normalized_artifact_sha256"
        ],
        "predicate_sha256": formal_input["predicate_sha256"],
        "formal_interface_sha256": (
            (contract.get("formal_interface") or {}).get("interface_sha256")
            if contract else None
        ),
        "formal_proof_receipt_sha256": proof.get("receipt_sha256"),
        "governed_closure_record_sha256": closure.get("record_sha256"),
        "ratification_status": row["status"],
        "stage": row["stage"],
        "reason_code": row["reason_code"],
        "claim_scope": formal_input["claim_scope"],
        "discharge_policy": formal_input["discharge_policy"],
        "next_obligation": (
            None
            if row["status"] == "ratified"
            else CONSTRUCTION_ARTIFACT_RATIFICATION_CAPABILITY
        ),
    }
    return TaskDischargeReceipt(
        contract_sha256=task_contract.sha256,
        adjudicator_id=task_contract.adjudicator_id,
        status=status,
        authority="leanmill.construction_artifact_ratification",
        observed=observed,
        evidence_refs=tuple(dict.fromkeys(evidence)),
    )


def _aggregate(
    task_contract: TaskDischargeContract,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    validated = validate_construction_artifact_ratification_result(result)
    final_receipt = _final_task_receipt(task_contract, validated)
    core = {
        "schema": CONSTRUCTION_ARTIFACT_RATIFICATION_AGGREGATE_SCHEMA,
        "task_contract_sha256": task_contract.sha256,
        "ratification_result": validated,
        "ratification_result_sha256": validated["receipt_sha256"],
        "final_task_discharge_receipt": final_receipt.to_dict(),
        "persistence_kind": "content_addressed_successor_no_prior_receipt_mutation",
        "authority": "leanmill.ratify_construction_artifact_action",
    }
    return {**core, "aggregate_sha256": content_hash(core)}


def validate_construction_artifact_ratification_aggregate(
    task_contract: TaskDischargeContract,
    outer_boundary_result: Mapping[str, Any],
    prior_open_receipt: TaskDischargeReceipt | Mapping[str, Any],
    value: Mapping[str, Any],
) -> dict[str, Any]:
    formal_input = build_construction_artifact_formal_input(
        task_contract, outer_boundary_result, prior_open_receipt
    )
    required = {
        "schema", "task_contract_sha256", "ratification_result",
        "ratification_result_sha256", "final_task_discharge_receipt",
        "persistence_kind", "authority",
    }
    row = _content_bound(
        value,
        schema=CONSTRUCTION_ARTIFACT_RATIFICATION_AGGREGATE_SCHEMA,
        digest_field="aggregate_sha256",
        required=required,
        context="construction-artifact ratification aggregate",
    )
    result = validate_construction_artifact_ratification_result(
        row["ratification_result"]
    )
    _bound, supplied_final = bind_task_discharge_receipt(
        task_contract, row["final_task_discharge_receipt"]
    )
    expected_final = _final_task_receipt(task_contract, result)
    if (
        row["task_contract_sha256"] != task_contract.sha256
        or row["ratification_result_sha256"] != result["receipt_sha256"]
        or result["formal_input"]["input_sha256"] != formal_input["input_sha256"]
        or supplied_final.to_dict() != expected_final.to_dict()
        or row.get("persistence_kind")
        != "content_addressed_successor_no_prior_receipt_mutation"
        or row.get("authority") != "leanmill.ratify_construction_artifact_action"
    ):
        raise ValueError("construction-artifact aggregate crossed action identity")
    return row


def construction_artifact_ratification_filename(
    aggregate: Mapping[str, Any],
) -> str:
    digest = _digest(aggregate.get("aggregate_sha256"), context="aggregate")
    return f"construction_artifact_ratification.{digest[:16]}.json"


def _unavailable_result(
    formal_input: Mapping[str, Any],
    *,
    stage: str,
    reason_code: str,
    ratification_contract: Mapping[str, Any] | None = None,
    proof_receipt: Mapping[str, Any] | None = None,
    solver_result: Mapping[str, Any] | None = None,
    resource_error: ConstructionArtifactRatificationResourceUnavailable | None = None,
) -> dict[str, Any]:
    resource_unavailable = (
        {
            "reason_code": resource_error.reason_code,
            "resource": resource_error.resource,
            "observed": resource_error.observed,
            "ceiling": resource_error.ceiling,
        }
        if resource_error is not None
        else None
    )
    return _ratification_result(
        formal_input,
        status="unavailable",
        stage=stage,
        reason_code=reason_code,
        ratification_contract=ratification_contract,
        proof_receipt=proof_receipt,
        governed_solver_result=solver_result,
        closure_record_ref=None,
        resource_unavailable=resource_unavailable,
    )


def _ratify_construction_artifact_formal_input_action(
    formal_input: Mapping[str, Any],
    *,
    substrate: str | Path,
    timeout_s: int = 500,
    formal_interface_fn: Callable[..., Mapping[str, Any]] | None = None,
    formal_certificate_fn: Callable[..., Mapping[str, Any]] | None = None,
    governed_solve_fn: Callable[..., Mapping[str, Any]] | None = None,
    ratification_contract_fn: Callable[
        [Mapping[str, Any]], Mapping[str, Any]
    ] | None = None,
) -> dict[str, Any]:
    """Execute the shared provider-free core for one validated formal input."""

    if type(timeout_s) is not int or timeout_s < 1:
        raise ValueError("construction ratification timeout must be positive")
    formal_input = validate_construction_artifact_formal_input(formal_input)

    def resolve_interface() -> Mapping[str, Any]:
        if formal_interface_fn is not None:
            return formal_interface_fn(formal_input=formal_input)
        from ztare.leanmill.theory_adapter_registry import (
            materialize_theory_adapter_capability,
        )
        return materialize_theory_adapter_capability(
            str(formal_input["adapter_id"]),
            CONSTRUCTION_ARTIFACT_FORMAL_INTERFACE_CAPABILITY,
            formal_input=formal_input,
        )

    try:
        first_interface = _json_data(
            resolve_interface(), context="construction formal interface"
        )
        second_interface = _json_data(
            resolve_interface(), context="construction formal interface"
        )
    except ConstructionArtifactRatificationResourceUnavailable as exc:
        return _unavailable_result(
            formal_input,
            stage="formal_interface",
            reason_code=exc.reason_code,
            resource_error=exc,
        )
    except ConstructionArtifactRatificationCapabilityUnavailable as exc:
        return _unavailable_result(
            formal_input,
            stage="formal_interface",
            reason_code=str(exc) or "formal_interface_unavailable",
        )
    except ValueError as exc:
        if "lacks capability" not in str(exc):
            raise
        return _unavailable_result(
            formal_input,
            stage="formal_interface",
            reason_code="formal_interface_capability_unavailable",
        )
    if first_interface != second_interface:
        raise ValueError("construction formal interface is nondeterministic")
    try:
        interface = validate_construction_artifact_formal_interface(
            formal_input, first_interface
        )
        ratification_contract = (
            validate_construction_artifact_ratification_contract_record(
                ratification_contract_fn(interface)
                if ratification_contract_fn is not None
                else build_construction_artifact_ratification_contract_from_formal_input(
                    formal_input, interface
                )
            )
        )
    except ConstructionArtifactRatificationResourceUnavailable as exc:
        return _unavailable_result(
            formal_input,
            stage="formal_interface",
            reason_code=exc.reason_code,
            resource_error=exc,
        )
    if ratification_contract["formal_input"] != formal_input:
        raise ValueError("construction ratification contract crossed formal input")

    def resolve_certificate() -> Mapping[str, Any]:
        if formal_certificate_fn is not None:
            return formal_certificate_fn(
                ratification_contract=ratification_contract
            )
        from ztare.leanmill.theory_adapter_registry import (
            materialize_theory_adapter_capability,
        )
        return materialize_theory_adapter_capability(
            str(formal_input["adapter_id"]),
            str(interface["certificate_capability_id"]),
            ratification_contract=ratification_contract,
        )

    try:
        first_proof = _json_data(
            resolve_certificate(), context="construction formal proof"
        )
        second_proof = _json_data(
            resolve_certificate(), context="construction formal proof"
        )
    except ConstructionArtifactRatificationResourceUnavailable as exc:
        return _unavailable_result(
            formal_input,
            stage="formal_certificate",
            reason_code=exc.reason_code,
            ratification_contract=ratification_contract,
            resource_error=exc,
        )
    except ConstructionArtifactRatificationCapabilityUnavailable as exc:
        return _unavailable_result(
            formal_input,
            stage="formal_certificate",
            reason_code=str(exc) or "formal_certificate_unavailable",
            ratification_contract=ratification_contract,
        )
    except ValueError as exc:
        if "lacks capability" not in str(exc):
            raise
        return _unavailable_result(
            formal_input,
            stage="formal_certificate",
            reason_code="formal_certificate_capability_unavailable",
            ratification_contract=ratification_contract,
        )
    if first_proof != second_proof:
        raise ValueError("construction formal proof producer is nondeterministic")
    try:
        proof_receipt = validate_construction_artifact_proof_receipt(
            ratification_contract, first_proof
        )
        _closed, posed, carried, target = render_construction_artifact_certificate(
            ratification_contract, proof_receipt
        )
    except ConstructionArtifactRatificationResourceUnavailable as exc:
        return _unavailable_result(
            formal_input,
            stage="formal_certificate",
            reason_code=exc.reason_code,
            ratification_contract=ratification_contract,
            resource_error=exc,
        )
    goal = str(interface["target_signature"])
    try:
        if governed_solve_fn is None:
            from ztare.leanmill.carried_theorem_ratification import (
                ratify_carried_theorem,
            )

            governed = ratify_carried_theorem(
                target,
                posed,
                carried,
                goal,
                lean_root=Path(substrate),
                timeout_s=timeout_s,
                provider_label=CONSTRUCTION_ARTIFACT_RATIFICATION_PROVIDER,
            )
        else:
            governed = governed_solve_fn(
                target,
                posed,
                goal,
                provider=None,
                timeout_s=timeout_s,
                mode="cascade",
                substrate=Path(substrate),
                preverified_proof=carried,
                preverified_provider=CONSTRUCTION_ARTIFACT_RATIFICATION_PROVIDER,
                preverified_only=True,
                require_positive_axiom_receipt=True,
            )
        raw_solver = _json_data(governed, context="governed solver result")
    except ConstructionArtifactRatificationResourceUnavailable as exc:
        return _unavailable_result(
            formal_input,
            stage="governance",
            reason_code=exc.reason_code,
            ratification_contract=ratification_contract,
            proof_receipt=proof_receipt,
            resource_error=exc,
        )
    except Exception as exc:  # noqa: BLE001 - typed runtime unavailability
        return _unavailable_result(
            formal_input,
            stage="governance",
            reason_code="governance_runtime_unavailable:" + type(exc).__name__,
            ratification_contract=ratification_contract,
            proof_receipt=proof_receipt,
        )
    results = raw_solver.get("results") if isinstance(raw_solver, Mapping) else None
    primary = results[0] if isinstance(results, list) and results else None
    if not isinstance(primary, Mapping) or primary.get("outcome") != "closed":
        return _ratification_result(
            formal_input,
            status="open",
            stage="governance",
            reason_code=str(
                primary.get("outcome") if isinstance(primary, Mapping)
                else "governance_returned_no_primary_result"
            ),
            ratification_contract=ratification_contract,
            proof_receipt=proof_receipt,
            governed_solver_result=raw_solver,
            closure_record_ref=None,
        )
    providers = primary.get("providers_tried")
    if (
        not isinstance(providers, list)
        or len(providers) != 1
        or providers[0].get("provider")
        != CONSTRUCTION_ARTIFACT_RATIFICATION_PROVIDER
        or providers[0].get("agent_kind") != "preverified_champion"
    ):
        return _ratification_result(
            formal_input,
            status="open",
            stage="governance",
            reason_code="provider_free_ratification_contract_not_observed",
            ratification_contract=ratification_contract,
            proof_receipt=proof_receipt,
            governed_solver_result=raw_solver,
            closure_record_ref=None,
        )
    ledger = str(raw_solver.get("closure_certificate") or "")
    record_digest = str(
        raw_solver.get("closure_certificate_record_sha256") or ""
    )
    closure_ref = {"ledger": ledger, "record_sha256": record_digest}
    try:
        candidate = _ratification_result(
            formal_input,
            status="ratified",
            stage="complete",
            reason_code="kernel_governed_certificate_ratified",
            ratification_contract=ratification_contract,
            proof_receipt=proof_receipt,
            governed_solver_result=raw_solver,
            closure_record_ref=closure_ref,
        )
        replayed, _record = replay_ratified_construction_artifact_result(candidate)
    except (TypeError, ValueError) as exc:
        return _ratification_result(
            formal_input,
            status="open",
            stage="governance",
            reason_code="governed_closure_evidence_rejected:" + type(exc).__name__,
            ratification_contract=ratification_contract,
            proof_receipt=proof_receipt,
            governed_solver_result=raw_solver,
            closure_record_ref=None,
        )
    return replayed


def ratify_construction_artifact_formal_input_action(
    formal_input: Mapping[str, Any],
    *,
    substrate: str | Path,
    timeout_s: int = 500,
    formal_interface_fn: Callable[..., Mapping[str, Any]] | None = None,
    formal_certificate_fn: Callable[..., Mapping[str, Any]] | None = None,
    governed_solve_fn: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Ratify one admitted construction artifact without provider search."""

    return _ratify_construction_artifact_formal_input_action(
        formal_input,
        substrate=substrate,
        timeout_s=timeout_s,
        formal_interface_fn=formal_interface_fn,
        formal_certificate_fn=formal_certificate_fn,
        governed_solve_fn=governed_solve_fn,
    )


def ratify_construction_artifact_action(
    task_contract: TaskDischargeContract,
    outer_boundary_result: Mapping[str, Any],
    prior_open_receipt: TaskDischargeReceipt | Mapping[str, Any],
    *,
    substrate: str | Path,
    timeout_s: int = 500,
    formal_interface_fn: Callable[..., Mapping[str, Any]] | None = None,
    formal_certificate_fn: Callable[..., Mapping[str, Any]] | None = None,
    governed_solve_fn: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Preserve the v1 governed-witness action and aggregate contract."""

    formal_input = build_construction_artifact_formal_input(
        task_contract, outer_boundary_result, prior_open_receipt
    )
    result = _ratify_construction_artifact_formal_input_action(
        formal_input,
        substrate=substrate,
        timeout_s=timeout_s,
        formal_interface_fn=formal_interface_fn,
        formal_certificate_fn=formal_certificate_fn,
        governed_solve_fn=governed_solve_fn,
        ratification_contract_fn=lambda interface: (
            build_construction_artifact_ratification_contract(
                task_contract,
                outer_boundary_result,
                prior_open_receipt,
                interface,
            )
        ),
    )
    aggregate = _aggregate(task_contract, result)
    return validate_construction_artifact_ratification_aggregate(
        task_contract, outer_boundary_result, prior_open_receipt, aggregate
    )


__all__ = [
    "CONSTRUCTION_ARTIFACT_FORMAL_INTERFACE_CAPABILITY",
    "CONSTRUCTION_ARTIFACT_RATIFICATION_CAPABILITY",
    "CONSTRUCTION_ARTIFACT_RATIFICATION_CONTRACT_V2_SCHEMA",
    "CONSTRUCTION_ARTIFACT_RATIFICATION_RESULT_V2_SCHEMA",
    "ConstructionArtifactRatificationCapabilityUnavailable",
    "ConstructionArtifactRatificationResourceUnavailable",
    "build_construction_artifact_ratification_contract_from_formal_input",
    "build_construction_artifact_formal_input",
    "build_construction_artifact_formal_interface",
    "build_construction_artifact_proof_receipt",
    "build_construction_artifact_ratification_contract",
    "construction_artifact_ratification_filename",
    "replay_ratified_construction_artifact_result",
    "ratify_construction_artifact_action",
    "ratify_construction_artifact_formal_input_action",
    "render_construction_artifact_certificate",
    "validate_construction_artifact_formal_input",
    "validate_construction_artifact_formal_interface",
    "validate_construction_artifact_proof_receipt",
    "validate_construction_artifact_ratification_aggregate",
    "validate_construction_artifact_ratification_contract_record",
    "validate_construction_artifact_ratification_result",
]
