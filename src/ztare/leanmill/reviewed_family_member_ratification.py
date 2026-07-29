"""Ratification admission for one reviewed finite-family witness.

AdapterForge owns the family bytes, its independent reviewer owns pre-outcome
admission, and the registered adapter owns normalization and predicate replay.
This module joins those immutable decisions into one formal-ratification input.
It never constructs or impersonates a ``witness_constructor`` artifact.
"""
from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any, Callable, Mapping

from ztare.leanmill.finite_construction_family import (
    FINITE_CONSTRUCTION_FAMILY_CLAIM_SCOPE,
    FINITE_CONSTRUCTION_FAMILY_SCHEMA,
    validate_finite_construction_family,
    validate_finite_construction_family_execution,
)
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.data_only_json import strict_json_data
from ztare.leanmill.protocol_validation import (
    require_sha256_digest,
    validate_content_bound_row,
)
from ztare.leanmill.witness_construction_boundary import (
    WITNESS_CONSTRUCTION_CLAIM_SCOPE,
    validate_witness_construction_interface,
)


REVIEWED_FAMILY_MEMBER_ADMISSION_SCHEMA = (
    "leanmill.reviewed_family_member_ratification_admission.v1"
)
REVIEWED_FAMILY_MEMBER_FORMAL_INPUT_SCHEMA = (
    "leanmill.reviewed_family_member_formal_input.v1"
)
REVIEWED_FAMILY_MEMBER_RATIFICATION_AGGREGATE_SCHEMA = (
    "leanmill.reviewed_family_member_ratification_aggregate.v2"
)


def _json_data(value: Any, *, context: str) -> Any:
    return strict_json_data(
        value,
        context=context,
        max_wire_bytes=64_000_000,
        max_integer_bits=4_096,
    )


_digest = require_sha256_digest
_content_bound = partial(validate_content_bound_row, copy_json=_json_data)


def _validated_review_join(
    family: Mapping[str, Any],
    forge_quarantine_receipt: Mapping[str, Any],
    *,
    witness_interface: Mapping[str, Any] | None = None,
    construction_origin: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Replay the pre-outcome host/reviewer admission of one family."""

    spec = family.get("family_spec")
    if isinstance(spec, Mapping) and spec.get("kind") == (
        "typed_construction_parameterization.v1"
    ):
        from ztare.leanmill.finite_construction_family import (
            AdmittedConstructionOrigin,
        )

        if witness_interface is None or not isinstance(
            construction_origin, AdmittedConstructionOrigin
        ):
            raise ValueError("parameterized family review requires its exact origin")
        from ztare.leanmill.adapter_forge import (
            validate_reviewed_construction_parameterization_authority,
        )
        from ztare.leanmill.finite_construction_family import (
            lower_reviewed_construction_parameterization,
        )

        origin_forge = construction_origin.forge_receipt
        if origin_forge != forge_quarantine_receipt:
            raise ValueError("parameterized family crossed its Forge authority")
        parameterization, forge = (
            validate_reviewed_construction_parameterization_authority(
                construction_origin.parameterization,
                forge_quarantine_receipt,
                witness_interface=witness_interface,
            )
        )
        replayed_family, replayed_execution = (
            lower_reviewed_construction_parameterization(
                parameterization,
                forge_quarantine_receipt=forge,
                witness_interface=witness_interface,
                parameterization_execution=construction_origin.execution,
            )
        )
        if (
            replayed_family != family
            or replayed_execution != construction_origin.execution
        ):
            raise ValueError("parameterized family lowering does not replay")
        host = dict(forge["host_conformance"])
        binding = dict(forge["review_evidence_binding"])
        return forge, host, binding

    from ztare.leanmill.adapter_forge import (
        ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        bind_adapter_review_evidence,
    )

    receipt = _json_data(
        forge_quarantine_receipt, context="finite-family Forge quarantine receipt"
    )
    required = {
        "schema",
        "gap_id",
        "proposed_adapter_id",
        "proposal_digest",
        "host_conformance",
        "independent_review",
        "review_evidence_binding",
        "status",
        "live_registry_mutated",
        "exactness_authority_granted",
        "next_step",
    }
    if not isinstance(receipt, dict) or set(receipt) != required | {"receipt_sha256"}:
        raise ValueError("finite-family Forge receipt fields changed identity")
    receipt_core = {
        key: item for key, item in receipt.items() if key != "receipt_sha256"
    }
    host = receipt.get("host_conformance")
    review = receipt.get("independent_review")
    binding = receipt.get("review_evidence_binding")
    if (
        receipt.get("schema") != "leanmill.adapter_forge_quarantine_receipt.v1"
        or receipt.get("receipt_sha256") != content_hash(receipt_core)
        or receipt.get("status") != "quarantined_registry_proposal"
        or receipt.get("live_registry_mutated") is not False
        or receipt.get("exactness_authority_granted") is not False
        or receipt.get("next_step")
        != "execute_reviewed_finite_construction_family"
        or receipt.get("gap_id") != family.get("gap_id")
        or receipt.get("proposed_adapter_id") != family.get("adapter_id")
        or not isinstance(host, Mapping)
        or not isinstance(review, Mapping)
        or not isinstance(binding, Mapping)
    ):
        raise ValueError("finite family lacks accepted Forge quarantine authority")
    host = dict(host)
    host_core = {key: item for key, item in host.items() if key != "receipt_sha256"}
    if (
        host.get("receipt_sha256") != content_hash(host_core)
        or host.get("ok") is not True
        or host.get("interface") != FINITE_CONSTRUCTION_FAMILY_SCHEMA
        or host.get("host_conformance_contract")
        != ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT
        or host.get("outcomes_evaluated") is not False
        or host.get("gap_id") != family.get("gap_id")
        or host.get("context_hash") != family.get("context_hash")
        or host.get("adapter_id") != family.get("adapter_id")
        or host.get("family_id") != family.get("family_id")
        or host.get("finite_family_receipt_sha256")
        != family.get("receipt_sha256")
        or host.get("target_interface_sha256")
        != family.get("target_interface_sha256")
    ):
        raise ValueError("finite-family Forge host conformance crossed family identity")
    expected_binding = bind_adapter_review_evidence(review, host)
    if review.get("accepted") is not True or dict(binding) != expected_binding:
        raise ValueError("finite-family independent review is not host-bound")
    return receipt, host, expected_binding


def validate_reviewed_finite_family_authority(
    family: Mapping[str, Any],
    forge_quarantine_receipt: Mapping[str, Any],
    *,
    witness_interface: Mapping[str, Any] | None = None,
    construction_origin: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Replay the pre-outcome family review independently of member success.

    Positive ratification and negative family exhaustion consume the same
    reviewed-family identity.  This public seam prevents the latter from
    borrowing a positive-member admission that it can never satisfy.
    """

    return _validated_review_join(
        family,
        forge_quarantine_receipt,
        witness_interface=witness_interface,
        construction_origin=construction_origin,
    )


def build_reviewed_family_member_ratification_admission(
    *,
    family: Mapping[str, Any],
    family_execution: Mapping[str, Any],
    forge_quarantine_receipt: Mapping[str, Any],
    witness_interface: Mapping[str, Any],
    parameter_id: str,
    construction_origin: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Admit one canonical verified family artifact to formal ratification."""

    interface = validate_witness_construction_interface(witness_interface)
    frozen_family = validate_finite_construction_family(
        family,
        witness_interface=interface,
        construction_origin=construction_origin,
    )
    execution = validate_finite_construction_family_execution(
        family_execution,
        family=frozen_family,
        witness_interface=interface,
        construction_origin=construction_origin,
    )
    forge, host, review_binding = _validated_review_join(
        frozen_family,
        forge_quarantine_receipt,
        witness_interface=interface,
        construction_origin=construction_origin,
    )
    if (
        execution["family_receipt_sha256"] != frozen_family["receipt_sha256"]
        or execution["family_id"] != frozen_family["family_id"]
        or execution["request_id"] != frozen_family["request_id"]
        or execution["gap_id"] != frozen_family["gap_id"]
        or execution["context_hash"] != frozen_family["context_hash"]
        or execution["adapter_id"] != frozen_family["adapter_id"]
        or execution["target_interface_sha256"] != interface["interface_sha256"]
        or execution["status"] != "witness_found"
        or interface["discharge_policy"]
        != "construction_artifact_ratification_required"
    ):
        raise ValueError("finite-family execution cannot enter ratification")

    family_members = {
        str(row["parameter_id"]): dict(row) for row in frozen_family["members"]
    }
    results = [dict(row) for row in execution["member_results"]]
    selected = next(
        (row for row in results if row["parameter_id"] == str(parameter_id)), None
    )
    if (
        selected is None
        or selected["registered_witness_execution"].get("status") != "verified"
        or selected["registered_witness_execution"].get("stage") != "complete"
        or not isinstance(
            selected["registered_witness_execution"].get("normalized_artifact"),
            Mapping,
        )
    ):
        raise ValueError("family ratification requires a verified member")
    normalized_sha = str(
        selected["registered_witness_execution"]["normalized_artifact_sha256"]
    )
    aliases = [
        row
        for row in results
        if row["registered_witness_execution"].get("status") == "verified"
        and row["registered_witness_execution"].get(
            "normalized_artifact_sha256"
        ) == normalized_sha
    ]
    if not aliases or aliases[0]["parameter_id"] != str(parameter_id):
        raise ValueError(
            "family ratification admission requires the first parameter for one artifact"
        )
    normalized = dict(
        selected["registered_witness_execution"]["normalized_artifact"]
    )
    if content_hash(normalized) != normalized_sha:
        raise ValueError("verified family member normalized digest mismatch")
    source_hashes: list[str] = []
    member_receipts: list[str] = []
    observations: list[dict[str, Any]] = []
    evidence_refs: list[str] = []
    for result in aliases:
        parameter = str(result["parameter_id"])
        source = family_members.get(parameter)
        registered = result["registered_witness_execution"]
        if (
            source is None
            or source.get("artifact_sha256") != result.get("source_artifact_sha256")
            or dict(registered.get("normalized_artifact") or {}) != normalized
        ):
            raise ValueError("verified family member crossed its authored artifact")
        source_hashes.append(str(result["source_artifact_sha256"]))
        member_receipts.append(str(result["receipt_sha256"]))
        refs = [str(ref) for ref in registered.get("evidence_refs") or ()]
        evidence_refs.extend(refs)
        observations.append(
            {
                "parameter_id": parameter,
                "observed": registered.get("observed"),
                "evidence_refs": refs,
                "member_result_receipt_sha256": str(result["receipt_sha256"]),
            }
        )

    predicate = dict(interface["predicate_ir"])
    schema = dict(interface["witness_schema"])
    core = {
        "schema": REVIEWED_FAMILY_MEMBER_ADMISSION_SCHEMA,
        "request_id": str(frozen_family["request_id"]),
        "gap_id": str(frozen_family["gap_id"]),
        "context_hash": str(frozen_family["context_hash"]),
        "adapter_id": str(frozen_family["adapter_id"]),
        "family_id": str(frozen_family["family_id"]),
        "family_receipt_sha256": str(frozen_family["receipt_sha256"]),
        "family_execution_receipt_sha256": str(execution["receipt_sha256"]),
        "primary_parameter_id": str(parameter_id),
        "parameter_ids": [str(row["parameter_id"]) for row in aliases],
        "source_artifact_sha256s": source_hashes,
        "member_result_receipt_sha256s": member_receipts,
        "normalized_artifact": normalized,
        "normalized_artifact_sha256": normalized_sha,
        "verifier_observations": observations,
        "verifier_evidence_refs": list(dict.fromkeys(evidence_refs)),
        "forge_quarantine_receipt_sha256": str(forge["receipt_sha256"]),
        "forge_host_conformance_receipt_sha256": str(host["receipt_sha256"]),
        "forge_review_binding_receipt_sha256": str(
            review_binding["receipt_sha256"]
        ),
        "forge_proposal_digest": str(forge["proposal_digest"]),
        "family_authorship": dict(frozen_family["authorship"]),
        "construction_origin_sha256s": dict(
            execution["construction_origin_sha256s"]
        ),
        "interface_sha256": str(interface["interface_sha256"]),
        "target_config_sha256": str(interface["target_config_sha256"]),
        "predicate_ir": predicate,
        "predicate_sha256": content_hash(predicate),
        "witness_schema": schema,
        "witness_schema_sha256": content_hash(schema),
        "discharge_policy": str(interface["discharge_policy"]),
        "source_claim_scope": FINITE_CONSTRUCTION_FAMILY_CLAIM_SCOPE,
        "ratification_claim_scope": WITNESS_CONSTRUCTION_CLAIM_SCOPE,
        "kernel_ratification_authority": False,
        "authority": "reviewed_family_member_to_ratification_admission",
    }
    return validate_reviewed_family_member_ratification_admission(
        {**core, "receipt_sha256": content_hash(core)}
    )


def validate_reviewed_family_member_ratification_admission(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    required = {
        "schema", "request_id", "gap_id", "context_hash", "adapter_id",
        "family_id", "family_receipt_sha256",
        "family_execution_receipt_sha256", "primary_parameter_id",
        "parameter_ids", "source_artifact_sha256s",
        "member_result_receipt_sha256s", "normalized_artifact",
        "normalized_artifact_sha256", "verifier_observations",
        "verifier_evidence_refs", "forge_quarantine_receipt_sha256",
        "forge_host_conformance_receipt_sha256",
        "forge_review_binding_receipt_sha256", "forge_proposal_digest",
        "family_authorship", "construction_origin_sha256s",
        "interface_sha256", "target_config_sha256",
        "predicate_ir", "predicate_sha256", "witness_schema",
        "witness_schema_sha256", "discharge_policy", "source_claim_scope",
        "ratification_claim_scope", "kernel_ratification_authority", "authority",
    }
    row = _content_bound(
        value,
        schema=REVIEWED_FAMILY_MEMBER_ADMISSION_SCHEMA,
        digest_field="receipt_sha256",
        required=required,
        context="reviewed family-member ratification admission",
    )
    for field in (
        "family_receipt_sha256", "family_execution_receipt_sha256",
        "normalized_artifact_sha256", "forge_quarantine_receipt_sha256",
        "forge_host_conformance_receipt_sha256",
        "forge_review_binding_receipt_sha256", "forge_proposal_digest",
        "interface_sha256", "target_config_sha256", "predicate_sha256",
        "witness_schema_sha256",
    ):
        _digest(row[field], context=field)
    parameters = row.get("parameter_ids")
    sources = row.get("source_artifact_sha256s")
    member_receipts = row.get("member_result_receipt_sha256s")
    observations = row.get("verifier_observations")
    refs = row.get("verifier_evidence_refs")
    origin_hashes = row.get("construction_origin_sha256s")
    parameterized = bool(
        isinstance(origin_hashes, Mapping)
        and origin_hashes.get("parameterization_sha256")
    )
    if (
        not all(str(row.get(field) or "").strip() for field in (
            "request_id", "gap_id", "context_hash", "adapter_id", "family_id"
        ))
        or not isinstance(parameters, list)
        or not parameters
        or len(set(parameters)) != len(parameters)
        or row.get("primary_parameter_id") != parameters[0]
        or not isinstance(sources, list)
        or not isinstance(member_receipts, list)
        or not isinstance(observations, list)
        or len(parameters) != len(sources)
        or len(parameters) != len(member_receipts)
        or len(parameters) != len(observations)
        or not isinstance(refs, list)
        or any(not isinstance(ref, str) or not ref for ref in refs)
        or len(refs) != len(set(refs))
        or not isinstance(row.get("normalized_artifact"), Mapping)
        or not row["normalized_artifact"]
        or row["normalized_artifact_sha256"]
        != content_hash(row["normalized_artifact"])
        or not isinstance(row.get("predicate_ir"), Mapping)
        or row["predicate_sha256"] != content_hash(row["predicate_ir"])
        or not isinstance(row.get("witness_schema"), Mapping)
        or row["witness_schema_sha256"] != content_hash(row["witness_schema"])
        or not isinstance(origin_hashes, Mapping)
        or set(origin_hashes) != {
            "parameterization_sha256",
            "adapter_forge_quarantine_receipt_sha256",
            "parameterization_execution_sha256",
        }
        or not parameterized
        and any(value != "" for value in origin_hashes.values())
        or parameterized
        and any(
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
            for value in origin_hashes.values()
        )
        or row.get("family_authorship")
        != (
            {
                "authority": "deterministic_parameterization_materializer",
                "role": "host",
            }
            if parameterized
            else {
                "authority": "campaign_local_subscription_leaf",
                "role": "adapter_forge",
            }
        )
        or row.get("discharge_policy")
        != "construction_artifact_ratification_required"
        or row.get("source_claim_scope") != FINITE_CONSTRUCTION_FAMILY_CLAIM_SCOPE
        or row.get("ratification_claim_scope") != WITNESS_CONSTRUCTION_CLAIM_SCOPE
        or row.get("kernel_ratification_authority") is not False
        or row.get("authority")
        != "reviewed_family_member_to_ratification_admission"
    ):
        raise ValueError("reviewed family-member admission crossed identity")
    for source in sources:
        _digest(source, context="source artifact")
    for member_receipt in member_receipts:
        _digest(member_receipt, context="member result")
    for index, observation in enumerate(observations):
        if (
            not isinstance(observation, Mapping)
            or set(observation) != {
                "parameter_id", "observed", "evidence_refs",
                "member_result_receipt_sha256",
            }
            or observation.get("parameter_id") != parameters[index]
            or observation.get("member_result_receipt_sha256")
            != member_receipts[index]
            or not isinstance(observation.get("evidence_refs"), list)
            or any(
                not isinstance(ref, str) or not ref
                for ref in observation.get("evidence_refs") or ()
            )
        ):
            raise ValueError("family-member verifier observation changed identity")
        _json_data(observation.get("observed"), context="verifier observation")
    expected_refs = list(
        dict.fromkeys(
            str(ref)
            for observation in observations
            for ref in observation["evidence_refs"]
        )
    )
    if refs != expected_refs:
        raise ValueError("family-member verifier evidence refs changed identity")
    return row


def build_reviewed_family_member_formal_input(
    admission: Mapping[str, Any],
) -> dict[str, Any]:
    frozen = validate_reviewed_family_member_ratification_admission(admission)
    core = {
        "schema": REVIEWED_FAMILY_MEMBER_FORMAL_INPUT_SCHEMA,
        "source_admission_sha256": str(frozen["receipt_sha256"]),
        "request_id": str(frozen["request_id"]),
        "context_hash": str(frozen["context_hash"]),
        "adapter_id": str(frozen["adapter_id"]),
        "interface_sha256": str(frozen["interface_sha256"]),
        "target_config_sha256": str(frozen["target_config_sha256"]),
        "predicate_ir": dict(frozen["predicate_ir"]),
        "predicate_sha256": str(frozen["predicate_sha256"]),
        "witness_schema": dict(frozen["witness_schema"]),
        "witness_schema_sha256": str(frozen["witness_schema_sha256"]),
        "normalized_artifact": dict(frozen["normalized_artifact"]),
        "normalized_artifact_sha256": str(frozen["normalized_artifact_sha256"]),
        "verification_receipt_sha256": str(
            frozen["member_result_receipt_sha256s"][0]
        ),
        "origin_evidence_refs": list(
            dict.fromkeys(
                [
                    str(frozen["receipt_sha256"]),
                    str(frozen["forge_quarantine_receipt_sha256"]),
                    str(frozen["family_execution_receipt_sha256"]),
                    *[
                        str(value)
                        for value in frozen["member_result_receipt_sha256s"]
                    ],
                    *[str(value) for value in frozen["verifier_evidence_refs"]],
                ]
            )
        ),
        "claim_scope": WITNESS_CONSTRUCTION_CLAIM_SCOPE,
        "discharge_policy": str(frozen["discharge_policy"]),
        "authority": "reviewed_family_member_to_formal_ratification_join",
    }
    return validate_reviewed_family_member_formal_input(
        {**core, "input_sha256": content_hash(core)}
    )


def validate_reviewed_family_member_formal_input(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    required = {
        "schema", "source_admission_sha256", "request_id", "context_hash",
        "adapter_id", "interface_sha256", "target_config_sha256", "predicate_ir",
        "predicate_sha256", "witness_schema", "witness_schema_sha256",
        "normalized_artifact", "normalized_artifact_sha256",
        "verification_receipt_sha256", "origin_evidence_refs", "claim_scope",
        "discharge_policy", "authority",
    }
    row = _content_bound(
        value,
        schema=REVIEWED_FAMILY_MEMBER_FORMAL_INPUT_SCHEMA,
        digest_field="input_sha256",
        required=required,
        context="reviewed family-member formal input",
    )
    for field in (
        "source_admission_sha256", "interface_sha256", "target_config_sha256",
        "predicate_sha256", "witness_schema_sha256",
        "normalized_artifact_sha256", "verification_receipt_sha256",
    ):
        _digest(row[field], context=field)
    refs = row.get("origin_evidence_refs")
    if (
        not all(str(row.get(field) or "").strip() for field in (
            "request_id", "context_hash", "adapter_id"
        ))
        or not isinstance(row.get("predicate_ir"), Mapping)
        or row["predicate_sha256"] != content_hash(row["predicate_ir"])
        or not isinstance(row.get("witness_schema"), Mapping)
        or row["witness_schema_sha256"] != content_hash(row["witness_schema"])
        or not isinstance(row.get("normalized_artifact"), Mapping)
        or row["normalized_artifact_sha256"]
        != content_hash(row["normalized_artifact"])
        or not isinstance(refs, list)
        or not refs
        or refs[0] != row["source_admission_sha256"]
        or any(not isinstance(ref, str) or not ref for ref in refs)
        or len(refs) != len(set(refs))
        or row.get("claim_scope") != WITNESS_CONSTRUCTION_CLAIM_SCOPE
        or row.get("discharge_policy")
        != "construction_artifact_ratification_required"
        or row.get("authority")
        != "reviewed_family_member_to_formal_ratification_join"
    ):
        raise ValueError("reviewed family-member formal input crossed identity")
    return row


def _family_ratification_aggregate(
    admission: Mapping[str, Any], result: Mapping[str, Any]
) -> dict[str, Any]:
    frozen = validate_reviewed_family_member_ratification_admission(admission)
    expected_input = build_reviewed_family_member_formal_input(frozen)
    from ztare.leanmill.construction_artifact_ratification import (
        replay_ratified_construction_artifact_result,
        validate_construction_artifact_ratification_result,
    )

    ratification = validate_construction_artifact_ratification_result(result)
    if ratification["formal_input"] != expected_input:
        raise ValueError("family ratification result crossed its admission")
    governed_closure_record = None
    if ratification["status"] == "ratified":
        ratification, governed_closure_record = (
            replay_ratified_construction_artifact_result(ratification)
        )
    core = {
        "schema": REVIEWED_FAMILY_MEMBER_RATIFICATION_AGGREGATE_SCHEMA,
        "admission": frozen,
        "admission_sha256": str(frozen["receipt_sha256"]),
        "ratification_result": ratification,
        "ratification_result_sha256": str(ratification["receipt_sha256"]),
        "governed_closure_record": governed_closure_record,
        "status": str(ratification["status"]),
        "persistence_kind": "content_addressed_family_origin_no_authorship_relabel",
        "authority": "leanmill.ratify_reviewed_family_member_action",
    }
    return validate_reviewed_family_member_ratification_aggregate(
        {**core, "aggregate_sha256": content_hash(core)}
    )


def validate_reviewed_family_member_ratification_aggregate(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    required = {
        "schema", "admission", "admission_sha256", "ratification_result",
        "ratification_result_sha256", "governed_closure_record", "status",
        "persistence_kind", "authority",
    }
    row = _content_bound(
        value,
        schema=REVIEWED_FAMILY_MEMBER_RATIFICATION_AGGREGATE_SCHEMA,
        digest_field="aggregate_sha256",
        required=required,
        context="reviewed family-member ratification aggregate",
    )
    admission = validate_reviewed_family_member_ratification_admission(
        row["admission"]
    )
    expected_input = build_reviewed_family_member_formal_input(admission)
    from ztare.leanmill.construction_artifact_ratification import (
        replay_ratified_construction_artifact_result,
        validate_construction_artifact_ratification_result,
    )

    result = validate_construction_artifact_ratification_result(
        row["ratification_result"]
    )
    closure_record = row.get("governed_closure_record")
    if result["status"] == "ratified":
        if not isinstance(closure_record, Mapping):
            raise ValueError(
                "ratified family aggregate lacks its governed closure record"
            )
        result, selected_record = replay_ratified_construction_artifact_result(
            result, closure_record=closure_record
        )
        if selected_record != closure_record:
            raise ValueError("family aggregate changed its governed closure record")
    elif closure_record is not None:
        raise ValueError("non-ratified family aggregate carries closure credit")
    if (
        row["admission_sha256"] != admission["receipt_sha256"]
        or row["ratification_result_sha256"] != result["receipt_sha256"]
        or row["status"] != result["status"]
        or result["formal_input"] != expected_input
        or row.get("persistence_kind")
        != "content_addressed_family_origin_no_authorship_relabel"
        or row.get("authority")
        != "leanmill.ratify_reviewed_family_member_action"
    ):
        raise ValueError("reviewed family-member aggregate crossed identity")
    return row


def ratify_reviewed_family_member_action(
    admission: Mapping[str, Any],
    *,
    substrate: str | Path,
    timeout_s: int = 500,
    formal_interface_fn: Callable[..., Mapping[str, Any]] | None = None,
    formal_certificate_fn: Callable[..., Mapping[str, Any]] | None = None,
    governed_solve_fn: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run one admitted family artifact through provider-free governance."""

    frozen = validate_reviewed_family_member_ratification_admission(admission)
    formal_input = build_reviewed_family_member_formal_input(frozen)
    from ztare.leanmill.construction_artifact_ratification import (
        ratify_construction_artifact_formal_input_action,
    )

    result = ratify_construction_artifact_formal_input_action(
        formal_input,
        substrate=substrate,
        timeout_s=timeout_s,
        formal_interface_fn=formal_interface_fn,
        formal_certificate_fn=formal_certificate_fn,
        governed_solve_fn=governed_solve_fn,
    )
    return _family_ratification_aggregate(frozen, result)


__all__ = [
    "REVIEWED_FAMILY_MEMBER_ADMISSION_SCHEMA",
    "REVIEWED_FAMILY_MEMBER_FORMAL_INPUT_SCHEMA",
    "REVIEWED_FAMILY_MEMBER_RATIFICATION_AGGREGATE_SCHEMA",
    "build_reviewed_family_member_formal_input",
    "build_reviewed_family_member_ratification_admission",
    "ratify_reviewed_family_member_action",
    "validate_reviewed_finite_family_authority",
    "validate_reviewed_family_member_formal_input",
    "validate_reviewed_family_member_ratification_admission",
    "validate_reviewed_family_member_ratification_aggregate",
]
