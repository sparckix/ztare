"""Reviewed, data-only finite construction families.

The common layer owns family identity, exact parameter coverage, deterministic
joins, and the closed outcome algebra.  It does not know how a substrate
normalizes or verifies one witness: those operations remain registered adapter
capabilities.  Family producers supply inert JSON artifacts only.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Mapping

from jsonschema import Draft202012Validator, ValidationError

from ztare.leanmill.data_only_json import strict_json_data
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.witness_construction_boundary import (
    GOVERNED_WITNESS_CONSTRUCTION_CAPABILITY,
    validate_witness_construction_interface,
)


FINITE_CONSTRUCTION_FAMILY_SCHEMA = (
    "leanmill.reviewed_finite_construction_family.v1"
)
FINITE_CONSTRUCTION_FAMILY_EXECUTION_SCHEMA = (
    "leanmill.finite_construction_family_execution.v1"
)
FINITE_CONSTRUCTION_FAMILY_CLAIM_SCOPE = (
    "exact_reviewed_family_only_no_ambient_nonexistence_or_ratification"
)
_MEMBER_STATUSES = frozenset({"verified", "rejected", "unavailable"})
_AGGREGATE_STATUSES = frozenset({"witness_found", "exhausted", "unavailable"})
PARAMETERIZED_FAMILY_SPEC_KIND = "typed_construction_parameterization.v1"
_MAX_FAMILY_PROTOCOL_BYTES = 64_000_000
_MAX_FAMILY_PROTOCOL_INTEGER_BITS = 4_096
_MAX_FAMILY_EXECUTION_MEMBER_BYTES = 48_000_000
_ORIGIN_ADMISSION_TOKEN = object()


class FiniteConstructionFamilyResourceUnavailable(RuntimeError):
    """The host cannot materialize a bounded family-execution envelope."""

    def __init__(
        self,
        reason_code: str,
        *,
        observed: int,
        ceiling: int,
        completed_members: int,
        attempted_members: int,
    ) -> None:
        self.reason_code = str(reason_code)
        self.observed = int(observed)
        self.ceiling = int(ceiling)
        self.completed_members = int(completed_members)
        self.attempted_members = int(attempted_members)
        super().__init__(self.reason_code)


class AdmittedConstructionOrigin:
    """One runtime-only parameterization/Forge/execution authority bundle."""

    __slots__ = (
        "_parameterization",
        "_execution",
        "_forge_bytes",
        "_witness_interface_sha256",
        "_sealed",
    )

    def __init__(
        self,
        *,
        parameterization,
        execution,
        forge_receipt: Mapping[str, Any],
        witness_interface_sha256: str,
        witness_schema_sha256: str,
        _token: object,
    ) -> None:
        from ztare.leanmill.construction_parameterization import (
            AdmittedConstructionExecution,
            AdmittedConstructionParameterization,
            admit_construction_parameterization,
            validate_construction_parameterization_execution,
        )

        if _token is not _ORIGIN_ADMISSION_TOKEN:
            raise TypeError("construction origin admission is host-minted")
        if not isinstance(parameterization, AdmittedConstructionParameterization):
            raise TypeError(
                "construction origin requires admitted parameterization authority"
            )
        if not isinstance(execution, AdmittedConstructionExecution):
            raise TypeError("construction origin requires admitted execution authority")
        if admit_construction_parameterization(parameterization) is not parameterization:
            raise TypeError("construction origin parameterization admission is invalid")
        if execution.admitted_parameterization is not parameterization and (
            execution.admitted_parameterization.assignment_domain_receipt
            != parameterization.assignment_domain_receipt
        ):
            raise TypeError("construction origin crossed parameterization admission")
        if validate_construction_parameterization_execution(
            execution, parameterization=parameterization
        ) is not execution:
            raise TypeError("construction origin execution admission is invalid")
        if execution.witness_schema_sha256 != str(witness_schema_sha256):
            raise TypeError("construction origin crossed witness schema admission")
        object.__setattr__(self, "_parameterization", parameterization)
        object.__setattr__(self, "_execution", execution)
        object.__setattr__(
            self,
            "_forge_bytes",
            json.dumps(
                dict(forge_receipt), sort_keys=True, separators=(",", ":")
            ).encode("utf-8"),
        )
        object.__setattr__(
            self,
            "_witness_interface_sha256",
            str(witness_interface_sha256),
        )
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, _name: str, _value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise TypeError("admitted construction origin is immutable")
        object.__setattr__(self, _name, _value)

    @property
    def parameterization(self):
        return self._parameterization

    @property
    def execution(self):
        return self._execution

    @property
    def forge_receipt(self) -> dict[str, Any]:
        return json.loads(self._forge_bytes)

    @property
    def witness_interface_sha256(self) -> str:
        return self._witness_interface_sha256

    def to_json(self) -> dict[str, Any]:
        return {
            "parameterization": dict(self._parameterization),
            "adapter_forge_quarantine_receipt": self.forge_receipt,
            "parameterization_execution": dict(self._execution),
        }

    def __deepcopy__(self, _memo: dict[int, Any]) -> dict[str, Any]:
        return self.to_json()

    def __reduce_ex__(self, _protocol: int) -> tuple[Any, tuple[str]]:
        return json.loads, (
            json.dumps(self.to_json(), sort_keys=True, separators=(",", ":")),
        )


def admit_construction_origin(
    *,
    parameterization: Mapping[str, Any],
    forge_quarantine_receipt: Mapping[str, Any],
    parameterization_execution: Mapping[str, Any],
    witness_interface: Mapping[str, Any],
) -> AdmittedConstructionOrigin:
    """Explicitly admit one cold origin once before all family consumers."""

    interface = validate_witness_construction_interface(witness_interface)
    from ztare.leanmill.adapter_forge import (
        validate_reviewed_construction_parameterization_bytes_authority,
    )
    from ztare.leanmill.construction_parameterization import (
        AdmittedConstructionExecution,
        admit_persisted_construction_execution,
    )

    authority_parameterization = parameterization
    if isinstance(parameterization_execution, AdmittedConstructionExecution):
        carried = parameterization_execution.admitted_parameterization
        if dict(carried) != dict(parameterization):
            raise ValueError(
                "construction origin execution crossed parameterization bytes"
            )
        authority_parameterization = carried
    frozen, forge = validate_reviewed_construction_parameterization_bytes_authority(
        authority_parameterization,
        forge_quarantine_receipt,
        witness_interface=interface,
    )
    execution = admit_persisted_construction_execution(
        authority_parameterization,
        parameterization_execution,
        witness_schema=interface["witness_schema"],
    )
    admitted = execution.admitted_parameterization
    if dict(admitted) != dict(frozen):
        raise ValueError("construction origin admission crossed parameterization")
    return AdmittedConstructionOrigin(
        parameterization=admitted,
        execution=execution,
        forge_receipt=forge,
        witness_interface_sha256=str(interface["interface_sha256"]),
        witness_schema_sha256=content_hash(interface["witness_schema"]),
        _token=_ORIGIN_ADMISSION_TOKEN,
    )


def _json_data(value: Any, *, context: str) -> Any:
    return strict_json_data(
        value,
        context=context,
        max_wire_bytes=_MAX_FAMILY_PROTOCOL_BYTES,
        max_integer_bits=_MAX_FAMILY_PROTOCOL_INTEGER_BITS,
    )


def _canonical_json_bytes(value: Any) -> int:
    return len(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    )


def construction_witness_interface(
    adapter_id: str,
    adapter_config: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve the one reviewed witness interface owned by an adapter config."""

    from ztare.leanmill.theory_adapter_registry import (
        theory_task_capability_catalog,
    )

    rows = [
        row
        for row in theory_task_capability_catalog(
            adapter_id, adapter_config=adapter_config
        )
        if row.get("capability_id") == GOVERNED_WITNESS_CONSTRUCTION_CAPABILITY
        and isinstance(row.get("interface"), Mapping)
    ]
    if len(rows) != 1:
        raise ValueError(
            "finite construction family requires one reviewed witness interface"
        )
    return validate_witness_construction_interface(rows[0]["interface"])


def finite_construction_family_authoring_contract(
    *,
    request_id: str,
    gap_id: str,
    context_hash: str,
    adapter_id: str,
    witness_interface: Mapping[str, Any],
) -> dict[str, Any]:
    """Expose the exact inert-family envelope to a quarantined producer."""

    interface = validate_witness_construction_interface(witness_interface)
    core = {
        "schema": "leanmill.finite_construction_family_authoring_contract.v1",
        "constants": {
            "schema": FINITE_CONSTRUCTION_FAMILY_SCHEMA,
            "request_id": str(request_id),
            "gap_id": str(gap_id),
            "context_hash": str(context_hash),
            "adapter_id": str(adapter_id),
            "target_interface_sha256": str(interface["interface_sha256"]),
            "authorship": {
                "authority": "campaign_local_subscription_leaf",
                "role": "adapter_forge",
            },
            "claim_scope": FINITE_CONSTRUCTION_FAMILY_CLAIM_SCOPE,
        },
        "top_level_fields": sorted(
            {
                "schema", "request_id", "gap_id", "context_hash", "adapter_id",
                "family_id", "family_scope", "family_spec", "authorship",
                "symmetry_policy", "target_interface_sha256",
                "declared_cardinality", "parameter_ids",
                "parameter_domain_sha256", "members", "claim_scope",
                "receipt_sha256",
            }
        ),
        "member_fields": [
            "artifact", "artifact_sha256", "derivation", "parameter_id",
            "source_refs",
        ],
        "field_contracts": {
            "parameter_id": "the matching entry from parameter_ids",
            "artifact": "one nonempty inert JSON object satisfying witness_schema",
            "artifact_sha256": "canonical digest of artifact",
            "derivation": (
                "one nonempty JSON construction-relation description; it must not "
                "contain target normalizer/verifier outcomes"
            ),
            "source_refs": (
                "a JSON list of nonempty string identities only; never embedded "
                "objects"
            ),
        },
        "symmetry_kinds": ["none", "explicit_quotient"],
        "witness_schema": dict(interface["witness_schema"]),
        "digest_rule": (
            "sha256(json.dumps(value,sort_keys=True,separators=(',',':'),"
            "ensure_ascii=True).encode('utf-8'))"
        ),
        "digest_applications": {
            "artifact_sha256": "member.artifact",
            "parameter_domain_sha256": "parameter_ids",
            "receipt_sha256": "the complete family object without receipt_sha256",
        },
        "outcome_ordering": (
            "the family is authored and independently reviewed before the host "
            "evaluates any member"
        ),
        "pre_review_self_test_boundary": (
            "self-tests may replay family generation, schema, digests, ordered "
            "domain coverage, and construction relations only; they must not run "
            "the target normalizer/verifier or report member acceptance, rejection, "
            "target metrics, target verdicts, or aggregate outcome counts"
        ),
        "authority": "reviewed_finite_family_common_interface",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _parameterization_bundle_from_family(
    family: Mapping[str, Any],
    *,
    witness_interface: Mapping[str, Any],
    construction_origin: AdmittedConstructionOrigin | None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    spec = family.get("family_spec")
    if not isinstance(spec, Mapping) or spec.get("kind") != PARAMETERIZED_FAMILY_SPEC_KIND:
        return None
    required = {
        "kind", "parameterization_sha256",
        "adapter_forge_quarantine_receipt_sha256", "backend_problem_sha256",
        "parameterization_execution_sha256", "candidate_residual_sha256s",
        "materialization_policy",
    }
    if set(spec) != required or not isinstance(
        construction_origin, AdmittedConstructionOrigin
    ):
        raise ValueError("parameterized family specification changed identity")
    if (
        construction_origin.witness_interface_sha256
        != witness_interface["interface_sha256"]
    ):
        raise ValueError("parameterized family origin crossed witness interface")
    parameterization = construction_origin.parameterization
    execution = construction_origin.execution
    forge_receipt = construction_origin.forge_receipt
    candidate_residual_sha256s = [
        residual["receipt_sha256"]
        for residual in execution["residuals"]
        if residual["kind"] == "candidate"
    ]
    if (
        spec["parameterization_sha256"] != parameterization["receipt_sha256"]
        or spec["adapter_forge_quarantine_receipt_sha256"]
        != forge_receipt["receipt_sha256"]
        or spec["backend_problem_sha256"]
        != content_hash(parameterization["backend_problem"])
        or spec["parameterization_execution_sha256"]
        != execution["receipt_sha256"]
        or spec["candidate_residual_sha256s"] != candidate_residual_sha256s
        or spec["materialization_policy"]
        != "exact_constraint_candidates_from_bound_execution_only"
    ):
        raise ValueError("parameterized family authority does not replay")
    return parameterization, execution, forge_receipt


def _persisted_parameterization_bundle_from_family(
    family: Mapping[str, Any],
    *,
    witness_interface: Mapping[str, Any],
    parameterization: Mapping[str, Any],
    parameterization_execution: Mapping[str, Any],
    forge_quarantine_receipt: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Validate cold origin bytes structurally, without backend admission."""

    from ztare.leanmill.adapter_forge import (
        validate_reviewed_construction_parameterization_bytes_authority,
    )
    from ztare.leanmill.construction_parameterization import (
        validate_construction_parameterization_execution,
    )

    frozen, forge = validate_reviewed_construction_parameterization_bytes_authority(
        parameterization,
        forge_quarantine_receipt,
        witness_interface=witness_interface,
    )
    execution = validate_construction_parameterization_execution(
        parameterization_execution,
        parameterization=frozen,
        witness_schema=witness_interface["witness_schema"],
    )
    spec = family.get("family_spec")
    candidate_residual_sha256s = [
        residual["receipt_sha256"]
        for residual in execution["residuals"]
        if residual["kind"] == "candidate"
    ]
    if not isinstance(spec, Mapping) or (
        spec.get("parameterization_sha256") != frozen["receipt_sha256"]
        or spec.get("adapter_forge_quarantine_receipt_sha256")
        != forge["receipt_sha256"]
        or spec.get("backend_problem_sha256")
        != content_hash(frozen["backend_problem"])
        or spec.get("parameterization_execution_sha256")
        != execution["receipt_sha256"]
        or spec.get("candidate_residual_sha256s")
        != candidate_residual_sha256s
        or spec.get("materialization_policy")
        != "exact_constraint_candidates_from_bound_execution_only"
    ):
        raise ValueError("persisted parameterized family authority does not replay")
    return frozen, execution, forge


def lower_reviewed_construction_parameterization(
    parameterization: Mapping[str, Any],
    *,
    forge_quarantine_receipt: Mapping[str, Any],
    witness_interface: Mapping[str, Any],
    parameterization_execution: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Compile reviewed exact candidates into the one finite-family carrier."""

    interface = validate_witness_construction_interface(witness_interface)
    from ztare.leanmill.adapter_forge import (
        validate_reviewed_construction_parameterization_authority,
    )
    from ztare.leanmill.construction_parameterization import (
        AdmittedConstructionExecution,
        admit_persisted_construction_execution,
        execute_construction_parameterization,
        materialize_construction_candidates,
    )

    authority_parameterization = parameterization
    if isinstance(parameterization_execution, AdmittedConstructionExecution):
        admitted_parameterization = (
            parameterization_execution.admitted_parameterization
        )
        if dict(admitted_parameterization) != dict(parameterization):
            raise ValueError(
                "construction execution crossed its parameterization bytes"
            )
        authority_parameterization = admitted_parameterization
    structural_parameterization, forge_receipt = (
        validate_reviewed_construction_parameterization_authority(
        authority_parameterization,
        forge_quarantine_receipt,
        witness_interface=interface,
        )
    )
    execution = (
        execute_construction_parameterization(
            authority_parameterization,
            witness_schema=interface["witness_schema"],
        )
        if parameterization_execution is None
        else admit_persisted_construction_execution(
            authority_parameterization,
            parameterization_execution,
            witness_schema=interface["witness_schema"],
        )
    )
    frozen = execution.admitted_parameterization
    if dict(frozen) != dict(structural_parameterization):
        raise ValueError(
            "construction execution crossed statically reviewed parameterization"
        )
    candidates = materialize_construction_candidates(
        frozen, execution, witness_schema=interface["witness_schema"]
    )
    if not candidates:
        return None, execution
    members = []
    for residual, artifact in candidates:
        assignment = dict(residual["assignment"])
        members.append(
            {
                "parameter_id": str(residual["parameter_id"]),
                "artifact": artifact,
                "artifact_sha256": content_hash(artifact),
                "derivation": {
                    "kind": "typed_construction_parameterization_member.v1",
                    "parameterization_sha256": frozen["receipt_sha256"],
                    "backend_problem_sha256": content_hash(
                        frozen["backend_problem"]
                    ),
                    "parameterization_execution_sha256": execution[
                        "receipt_sha256"
                    ],
                    "construction_residual_sha256": residual["receipt_sha256"],
                    "assignment": assignment,
                    "assignment_sha256": content_hash(assignment),
                },
                "source_refs": list(frozen["source_refs"]),
            }
        )
    parameter_ids = [row["parameter_id"] for row in members]
    spec = {
        "kind": PARAMETERIZED_FAMILY_SPEC_KIND,
        "parameterization_sha256": frozen["receipt_sha256"],
        "adapter_forge_quarantine_receipt_sha256": forge_receipt[
            "receipt_sha256"
        ],
        "backend_problem_sha256": content_hash(frozen["backend_problem"]),
        "parameterization_execution_sha256": execution["receipt_sha256"],
        "candidate_residual_sha256s": [
            residual["receipt_sha256"] for residual, _artifact in candidates
        ],
        "materialization_policy": (
            "exact_constraint_candidates_from_bound_execution_only"
        ),
    }
    identity = {
        "parameterization_sha256": frozen["receipt_sha256"],
        "adapter_forge_quarantine_receipt_sha256": forge_receipt[
            "receipt_sha256"
        ],
        "target_interface_sha256": interface["interface_sha256"],
    }
    core = {
        "schema": FINITE_CONSTRUCTION_FAMILY_SCHEMA,
        "request_id": frozen["request_id"],
        "gap_id": frozen["gap_id"],
        "context_hash": frozen["context_hash"],
        "adapter_id": frozen["adapter_id"],
        "family_id": "family:parameterization:" + content_hash(identity),
        "family_scope": (
            "the exact constraint-candidate subset of parameterization "
            + frozen["parameterization_id"]
        ),
        "family_spec": spec,
        "authorship": {
            "authority": "deterministic_parameterization_materializer",
            "role": "host",
        },
        "symmetry_policy": {"kind": "none"},
        "target_interface_sha256": interface["interface_sha256"],
        "declared_cardinality": len(members),
        "parameter_ids": parameter_ids,
        "parameter_domain_sha256": content_hash(parameter_ids),
        "members": members,
        "claim_scope": FINITE_CONSTRUCTION_FAMILY_CLAIM_SCOPE,
    }
    family = {**core, "receipt_sha256": content_hash(core)}
    size = len(
        json.dumps(
            family, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    )
    if size > int(frozen["resource_limits"]["max_materialized_family_bytes"]):
        from ztare.leanmill.construction_parameterization import (
            ConstructionResourceCeilingExceeded,
        )

        raise ConstructionResourceCeilingExceeded(
            "construction_family_byte_limit_exhausted",
            resource="materialized_family_bytes",
            observed=size,
            ceiling=int(
                frozen["resource_limits"]["max_materialized_family_bytes"]
            ),
        )
    admitted_origin = admit_construction_origin(
        parameterization=frozen,
        forge_quarantine_receipt=forge_receipt,
        parameterization_execution=execution,
        witness_interface=interface,
    )
    return (
        validate_finite_construction_family(
            family,
            request_id=frozen["request_id"],
            gap_id=frozen["gap_id"],
            context_hash=frozen["context_hash"],
            adapter_id=frozen["adapter_id"],
            witness_interface=interface,
            construction_origin=admitted_origin,
        ),
        execution,
    )


def validate_finite_construction_family(
    value: Mapping[str, Any],
    *,
    request_id: str | None = None,
    gap_id: str | None = None,
    context_hash: str | None = None,
    adapter_id: str | None = None,
    witness_interface: Mapping[str, Any] | None = None,
    construction_origin: AdmittedConstructionOrigin | None = None,
    _persisted_construction_projection: tuple[
        Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]
    ]
    | None = None,
) -> dict[str, Any]:
    """Validate one byte-frozen explicit parameter-to-artifact relation."""

    row = _json_data(value, context="finite construction family")
    required = {
        "schema",
        "request_id",
        "gap_id",
        "context_hash",
        "adapter_id",
        "family_id",
        "family_scope",
        "family_spec",
        "authorship",
        "symmetry_policy",
        "target_interface_sha256",
        "declared_cardinality",
        "parameter_ids",
        "parameter_domain_sha256",
        "members",
        "claim_scope",
    }
    if not isinstance(row, dict) or set(row) != required | {"receipt_sha256"}:
        raise ValueError("finite construction family fields changed identity")
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    if (
        row.get("schema") != FINITE_CONSTRUCTION_FAMILY_SCHEMA
        or row.get("receipt_sha256") != content_hash(core)
        or row.get("claim_scope") != FINITE_CONSTRUCTION_FAMILY_CLAIM_SCOPE
    ):
        raise ValueError("finite construction family digest or claim scope mismatch")
    for field, expected in (
        ("request_id", request_id),
        ("gap_id", gap_id),
        ("context_hash", context_hash),
        ("adapter_id", adapter_id),
    ):
        actual = str(row.get(field) or "")
        if not actual or (expected is not None and actual != str(expected)):
            raise ValueError(f"finite construction family crossed {field}")
    if not all(
        str(row.get(field) or "").strip()
        for field in ("family_id", "family_scope", "target_interface_sha256")
    ):
        raise ValueError("finite construction family identity is incomplete")
    family_spec = row.get("family_spec")
    authorship = row.get("authorship")
    symmetry = row.get("symmetry_policy")
    if not isinstance(family_spec, Mapping) or not family_spec:
        raise ValueError("finite construction family requires a mathematical spec")
    parameterization = None
    parameterization_bundle = None
    if family_spec.get("kind") == PARAMETERIZED_FAMILY_SPEC_KIND:
        if witness_interface is None:
            raise ValueError(
                "parameterized finite family requires its witness interface"
            )
        interface = validate_witness_construction_interface(witness_interface)
        if _persisted_construction_projection is not None:
            if construction_origin is not None:
                raise ValueError(
                    "finite family mixed runtime and persisted construction origins"
                )
            parameterization_bundle = (
                _persisted_parameterization_bundle_from_family(
                    row,
                    witness_interface=interface,
                    parameterization=_persisted_construction_projection[0],
                    parameterization_execution=(
                        _persisted_construction_projection[1]
                    ),
                    forge_quarantine_receipt=(
                        _persisted_construction_projection[2]
                    ),
                )
            )
        else:
            parameterization_bundle = _parameterization_bundle_from_family(
                row,
                witness_interface=interface,
                construction_origin=construction_origin,
            )
        if parameterization_bundle is None:
            raise ValueError("parameterized family origin admission is missing")
        parameterization = parameterization_bundle[0]
        expected_authorship = {
            "authority": "deterministic_parameterization_materializer",
            "role": "host",
        }
    else:
        if construction_origin is not None:
            raise ValueError("ordinary finite family borrowed construction origin")
        expected_authorship = {
            "authority": "campaign_local_subscription_leaf",
            "role": "adapter_forge",
        }
    if authorship != expected_authorship:
        raise ValueError("finite construction family lacks its declared authorship")
    if (
        not isinstance(symmetry, Mapping)
        or symmetry.get("kind") not in {"none", "explicit_quotient"}
        or (
            symmetry.get("kind") == "explicit_quotient"
            and not isinstance(symmetry.get("coverage_witness"), Mapping)
        )
    ):
        raise ValueError("finite construction family symmetry policy is incomplete")
    parameter_ids = row.get("parameter_ids")
    members = row.get("members")
    cardinality = row.get("declared_cardinality")
    if (
        type(cardinality) is not int
        or cardinality < 1
        or not isinstance(parameter_ids, list)
        or not isinstance(members, list)
        or len(parameter_ids) != cardinality
        or len(members) != cardinality
        or any(not isinstance(value, str) or not value for value in parameter_ids)
        or len(set(parameter_ids)) != cardinality
        or row.get("parameter_domain_sha256") != content_hash(parameter_ids)
    ):
        raise ValueError("finite construction family parameter domain is not exact")

    schema = None
    if witness_interface is not None:
        interface = validate_witness_construction_interface(witness_interface)
        if row["target_interface_sha256"] != interface["interface_sha256"]:
            raise ValueError("finite construction family crossed target interface")
        schema = dict(interface["witness_schema"])
    normalized_members: list[dict[str, Any]] = []
    for expected_parameter, raw_member in zip(parameter_ids, members, strict=True):
        if not isinstance(raw_member, Mapping):
            raise ValueError("finite construction family member must be an object")
        member = _json_data(raw_member, context="finite family member")
        if set(member) != {
            "parameter_id",
            "artifact",
            "artifact_sha256",
            "derivation",
            "source_refs",
        }:
            raise ValueError("finite construction family member fields changed identity")
        artifact = member.get("artifact")
        derivation = member.get("derivation")
        refs = member.get("source_refs")
        if member.get("parameter_id") != expected_parameter:
            raise ValueError(
                "finite construction family member crossed ordered parameter identity"
            )
        if not isinstance(artifact, Mapping) or not artifact:
            raise ValueError("finite construction family member artifact is empty")
        if member.get("artifact_sha256") != content_hash(dict(artifact)):
            raise ValueError("finite construction family member artifact digest mismatch")
        if not isinstance(derivation, Mapping) or not derivation:
            raise ValueError("finite construction family member derivation is empty")
        if not isinstance(refs, list) or any(
            not isinstance(ref, str) or not ref for ref in refs
        ):
            raise ValueError(
                "finite construction family member source_refs must be strings"
            )
        if schema is not None:
            try:
                Draft202012Validator(schema).validate(dict(artifact))
            except ValidationError as exc:
                raise ValueError(
                    "finite construction family member violates witness schema"
                ) from exc
        normalized_members.append(dict(member))
    if parameterization is not None:
        if witness_interface is None:
            raise ValueError(
                "parameterized finite family requires its witness interface"
            )
        from ztare.leanmill.construction_parameterization import (
            materialize_construction_candidates,
        )

        if (
            parameterization["request_id"] != row["request_id"]
            or parameterization["gap_id"] != row["gap_id"]
            or parameterization["context_hash"] != row["context_hash"]
            or parameterization["adapter_id"] != row["adapter_id"]
            or parameterization["target_interface_sha256"]
            != row["target_interface_sha256"]
        ):
            raise ValueError("parameterized family crossed construction identity")
        if parameterization_bundle is None:
            raise ValueError("parameterized family origin admission is missing")
        parameterization_execution = parameterization_bundle[1]
        candidate_residuals = [
            residual
            for residual in parameterization_execution["residuals"]
            if residual["kind"] == "candidate"
        ]
        if [residual["parameter_id"] for residual in candidate_residuals] != parameter_ids:
            raise ValueError(
                "parameterized family candidate domain changed after materialization"
            )
        if _persisted_construction_projection is not None:
            from ztare.leanmill.construction_parameterization import (
                _materialize_persisted_construction_candidates_projection,
            )

            expected_candidates = (
                _materialize_persisted_construction_candidates_projection(
                    parameterization,
                    parameterization_execution,
                    witness_schema=schema or {},
                )
            )
        else:
            expected_candidates = materialize_construction_candidates(
                parameterization,
                parameterization_execution,
                witness_schema=schema or {},
            )
        for member, (residual, expected_artifact) in zip(
            normalized_members, expected_candidates, strict=True
        ):
            parameter_id = str(residual["parameter_id"])
            assignment = dict(residual["assignment"])
            expected_derivation = {
                "kind": "typed_construction_parameterization_member.v1",
                "parameterization_sha256": parameterization["receipt_sha256"],
                "backend_problem_sha256": content_hash(
                    parameterization["backend_problem"]
                ),
                "parameterization_execution_sha256": parameterization_execution[
                    "receipt_sha256"
                ],
                "construction_residual_sha256": residual["receipt_sha256"],
                "assignment": assignment,
                "assignment_sha256": content_hash(assignment),
            }
            if (
                member["parameter_id"] != parameter_id
                or member["artifact"] != expected_artifact
                or member["artifact_sha256"] != content_hash(expected_artifact)
                or member["derivation"] != expected_derivation
                or member["source_refs"] != parameterization["source_refs"]
            ):
                raise ValueError(
                    "parameterized family member changed after deterministic materialization"
                )
    return {**core, "members": normalized_members, "receipt_sha256": row["receipt_sha256"]}


def validate_persisted_parameterized_finite_construction_family(
    value: Mapping[str, Any],
    *,
    request_id: str,
    gap_id: str,
    context_hash: str,
    adapter_id: str,
    witness_interface: Mapping[str, Any],
    parameterization: Mapping[str, Any],
    parameterization_execution: Mapping[str, Any],
    forge_quarantine_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one cold family projection without restoring runtime authority."""

    if (value.get("family_spec") or {}).get("kind") != (
        PARAMETERIZED_FAMILY_SPEC_KIND
    ):
        raise ValueError("persisted construction projection requires parameterized family")
    return validate_finite_construction_family(
        value,
        request_id=request_id,
        gap_id=gap_id,
        context_hash=context_hash,
        adapter_id=adapter_id,
        witness_interface=witness_interface,
        _persisted_construction_projection=(
            parameterization,
            parameterization_execution,
            forge_quarantine_receipt,
        ),
    )


def execute_finite_construction_family(
    family: Mapping[str, Any],
    *,
    witness_interface: Mapping[str, Any],
    capability_fn: Callable[..., Mapping[str, Any]],
    construction_origin: AdmittedConstructionOrigin | None = None,
) -> dict[str, Any]:
    """Execute a reviewed family through registered adapter capabilities."""

    interface = validate_witness_construction_interface(witness_interface)
    candidate = validate_finite_construction_family(
        family,
        witness_interface=interface,
        construction_origin=construction_origin,
    )
    adapter_id = str(candidate["adapter_id"])
    schema = dict(interface["witness_schema"])
    cache: dict[str, dict[str, Any]] = {}
    member_results: list[dict[str, Any]] = []
    cumulative_member_bytes = 0
    parameterization_bundle = _parameterization_bundle_from_family(
        candidate,
        witness_interface=interface,
        construction_origin=construction_origin,
    )
    parameterization = (
        parameterization_bundle[0] if parameterization_bundle is not None else None
    )
    parameterization_execution = (
        parameterization_bundle[1] if parameterization_bundle is not None else None
    )
    construction_residuals = (
        {
            str(row["parameter_id"]): dict(row)
            for row in parameterization_execution["residuals"]
            if str(row.get("parameter_id") or "")
        }
        if parameterization_execution is not None
        else {}
    )

    for member in candidate["members"]:
        source_sha = str(member["artifact_sha256"])
        construction_residual = construction_residuals.get(
            str(member["parameter_id"])
        )
        if parameterization is not None and construction_residual is None:
            raise ValueError(
                "parameterized family execution lacks a member residual"
            )
        if construction_residual is not None and construction_residual["kind"] != "candidate":
            raise ValueError(
                "parameterized target family contains a noncandidate residual"
            )
        cached = cache.get(source_sha)
        if cached is None:
            from ztare.leanmill.witness_construction_boundary import (
                execute_registered_witness_artifact,
            )

            registered_execution = execute_registered_witness_artifact(
                adapter_id=adapter_id,
                witness_interface=interface,
                artifact=member["artifact"],
                normalizer_fn=capability_fn,
                verifier_fn=capability_fn,
            )
            cached = cache[source_sha] = {
                "registered_execution": registered_execution,
                "source_parameter_id": str(member["parameter_id"]),
            }
        registered_execution = cached["registered_execution"]
        result_core = {
            "schema": "leanmill.finite_construction_family_member_result.v1",
            "family_receipt_sha256": str(candidate["receipt_sha256"]),
            "parameter_id": str(member["parameter_id"]),
            "source_artifact_sha256": source_sha,
            "registered_witness_execution": registered_execution,
            "registered_witness_execution_sha256": registered_execution[
                "receipt_sha256"
            ],
            "construction_residual_sha256": (
                str(construction_residual["receipt_sha256"])
                if construction_residual is not None
                else ""
            ),
            "reused_from_parameter_id": (
                ""
                if cached["source_parameter_id"] == member["parameter_id"]
                else cached["source_parameter_id"]
            ),
            "authority": "registered_witness_artifact_family_join",
        }
        result = {**result_core, "receipt_sha256": content_hash(result_core)}
        result_bytes = _canonical_json_bytes(result)
        if (
            cumulative_member_bytes + result_bytes
            > _MAX_FAMILY_EXECUTION_MEMBER_BYTES
        ):
            raise FiniteConstructionFamilyResourceUnavailable(
                "finite_family_execution_byte_limit_exhausted",
                observed=cumulative_member_bytes + result_bytes,
                ceiling=_MAX_FAMILY_EXECUTION_MEMBER_BYTES,
                completed_members=len(member_results),
                attempted_members=len(member_results) + 1,
            )
        cumulative_member_bytes += result_bytes
        member_results.append(result)

    statuses = [
        str(row["registered_witness_execution"]["status"])
        for row in member_results
    ]
    aggregate_status = (
        "witness_found"
        if "verified" in statuses
        else "unavailable"
        if "unavailable" in statuses
        or (
            parameterization_execution is not None
            and parameterization_execution["coverage_complete"] is False
        )
        else "exhausted"
    )
    construction_incomplete = bool(
        parameterization_execution is not None
        and parameterization_execution["coverage_complete"] is False
    )
    core = {
        "schema": FINITE_CONSTRUCTION_FAMILY_EXECUTION_SCHEMA,
        "family_id": str(candidate["family_id"]),
        "family_receipt_sha256": str(candidate["receipt_sha256"]),
        "request_id": str(candidate["request_id"]),
        "gap_id": str(candidate["gap_id"]),
        "context_hash": str(candidate["context_hash"]),
        "adapter_id": adapter_id,
        "target_interface_sha256": str(candidate["target_interface_sha256"]),
        "expected_parameter_ids": list(candidate["parameter_ids"]),
        "observed_parameter_ids": [row["parameter_id"] for row in member_results],
        "member_results": member_results,
        "construction_origin_sha256s": {
            "parameterization_sha256": (
                str(parameterization["receipt_sha256"])
                if parameterization is not None
                else ""
            ),
            "adapter_forge_quarantine_receipt_sha256": (
                str(parameterization_bundle[2]["receipt_sha256"])
                if parameterization_bundle is not None
                else ""
            ),
            "parameterization_execution_sha256": (
                str(parameterization_execution["receipt_sha256"])
                if parameterization_execution is not None
                else ""
            ),
        },
        "unique_source_artifact_count": len(
            {str(row["artifact_sha256"]) for row in candidate["members"]}
        ),
        "status": aggregate_status,
        "coverage_complete": (
            bool(parameterization_execution["coverage_complete"])
            if parameterization_execution is not None
            else True
        ),
        "family_claim": (
            f"all {len(member_results)} members of family {candidate['family_id']} "
            "were rejected by the registered verifier"
            if aggregate_status == "exhausted"
            else f"family {candidate['family_id']} contains a verified witness"
            if aggregate_status == "witness_found"
            else f"family {candidate['family_id']} has incomplete construction coverage"
            if construction_incomplete
            else f"family {candidate['family_id']} has at least one unavailable member"
        ),
        "ratification_status": (
            "construction_witness_pending_source_neutral_ratification"
            if aggregate_status == "witness_found" and parameterization is not None
            else "discovered_pending_ratification"
            if aggregate_status == "witness_found"
            else "not_applicable"
        ),
        "claim_scope": FINITE_CONSTRUCTION_FAMILY_CLAIM_SCOPE,
        "global_nonexistence_authority": False,
        "kernel_ratification_authority": False,
        "authority": "reviewed_finite_construction_family_executor",
    }
    try:
        bounded_core = _json_data(
            core, context="finite construction family execution"
        )
    except ValueError as exc:
        if "maximum JSON wire size" not in str(exc):
            raise
        raise FiniteConstructionFamilyResourceUnavailable(
            "finite_family_execution_envelope_limit_exhausted",
            observed=_MAX_FAMILY_PROTOCOL_BYTES + 1,
            ceiling=_MAX_FAMILY_PROTOCOL_BYTES,
            completed_members=len(member_results),
            attempted_members=len(member_results),
        ) from exc
    return validate_finite_construction_family_execution(
        {**bounded_core, "receipt_sha256": content_hash(bounded_core)},
        family=candidate,
        witness_interface=interface,
        construction_origin=construction_origin,
    )


def validate_finite_construction_family_execution(
    value: Mapping[str, Any],
    *,
    family: Mapping[str, Any] | None = None,
    witness_interface: Mapping[str, Any] | None = None,
    construction_origin: AdmittedConstructionOrigin | None = None,
) -> dict[str, Any]:
    row = _json_data(value, context="finite construction family execution")
    required = {
        "schema",
        "family_id",
        "family_receipt_sha256",
        "request_id",
        "gap_id",
        "context_hash",
        "adapter_id",
        "target_interface_sha256",
        "expected_parameter_ids",
        "observed_parameter_ids",
        "member_results",
        "construction_origin_sha256s",
        "unique_source_artifact_count",
        "status",
        "coverage_complete",
        "family_claim",
        "ratification_status",
        "claim_scope",
        "global_nonexistence_authority",
        "kernel_ratification_authority",
        "authority",
    }
    if not isinstance(row, dict) or set(row) != required | {"receipt_sha256"}:
        raise ValueError("finite family execution fields changed identity")
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    expected = row.get("expected_parameter_ids")
    observed = row.get("observed_parameter_ids")
    members = row.get("member_results")
    origin_hashes = row.get("construction_origin_sha256s")
    if not isinstance(origin_hashes, Mapping) or set(origin_hashes) != {
        "parameterization_sha256",
        "adapter_forge_quarantine_receipt_sha256",
        "parameterization_execution_sha256",
    }:
        raise ValueError("finite family execution origin hashes are malformed")
    origin_values = list(origin_hashes.values())
    if not (
        all(value == "" for value in origin_values)
        or all(
            isinstance(value, str)
            and len(value) == 64
            and all(character in "0123456789abcdef" for character in value)
            for value in origin_values
        )
    ):
        raise ValueError("finite family execution origin hashes are incomplete")
    parameterization_execution = None
    member_required = {
        "schema",
        "family_receipt_sha256",
        "parameter_id",
        "source_artifact_sha256",
        "registered_witness_execution",
        "registered_witness_execution_sha256",
        "construction_residual_sha256",
        "reused_from_parameter_id",
        "authority",
    }
    member_statuses = (
        [
            str(
                (member.get("registered_witness_execution") or {}).get(
                    "status"
                )
            )
            for member in members
        ]
        if isinstance(members, list)
        else []
    )
    expected_ratification_status = (
        "construction_witness_pending_source_neutral_ratification"
        if row.get("status") == "witness_found"
        and bool(origin_hashes["parameterization_sha256"])
        else "discovered_pending_ratification"
        if row.get("status") == "witness_found"
        else "not_applicable"
    )
    if row.get("status") == "exhausted":
        expected_family_claim = (
            f"all {len(members) if isinstance(members, list) else 0} "
            f"members of family {row.get('family_id')} were rejected by the registered verifier"
        )
    elif row.get("status") == "witness_found":
        expected_family_claim = (
            f"family {row.get('family_id')} contains a verified witness"
        )
    else:
        expected_family_claim = (
            f"family {row.get('family_id')} has incomplete construction coverage"
            if row.get("coverage_complete") is False
            else f"family {row.get('family_id')} has at least one unavailable member"
        )
    if (
        row.get("schema") != FINITE_CONSTRUCTION_FAMILY_EXECUTION_SCHEMA
        or row.get("receipt_sha256") != content_hash(core)
        or row.get("status") not in _AGGREGATE_STATUSES
        or row.get("claim_scope") != FINITE_CONSTRUCTION_FAMILY_CLAIM_SCOPE
        or type(row.get("coverage_complete")) is not bool
        or row.get("global_nonexistence_authority") is not False
        or row.get("kernel_ratification_authority") is not False
        or row.get("authority") != "reviewed_finite_construction_family_executor"
        or not isinstance(expected, list)
        or not expected
        or len(set(expected)) != len(expected)
        or expected != observed
        or not isinstance(members, list)
        or [member.get("parameter_id") for member in members] != expected
        or any(status not in _MEMBER_STATUSES for status in member_statuses)
        or (
            row.get("status") == "exhausted"
            and any(status != "rejected" for status in member_statuses)
        )
        or (
            row.get("status") == "witness_found"
            and not any(status == "verified" for status in member_statuses)
        )
        or (
            row.get("status") == "unavailable"
            and (
                any(status == "verified" for status in member_statuses)
                or (
                    row.get("coverage_complete") is True
                    and not any(
                        status == "unavailable" for status in member_statuses
                    )
                )
            )
        )
        or row.get("ratification_status") != expected_ratification_status
        or row.get("family_claim") != expected_family_claim
        or row.get("coverage_complete") is False
        and row.get("status") not in {"unavailable", "witness_found"}
        or row.get("unique_source_artifact_count")
        != len(
            {
                str(member.get("source_artifact_sha256") or "")
                for member in members
            }
        )
    ):
        raise ValueError("finite family execution outcome algebra is invalid")
    first_parameter_by_source: dict[str, str] = {}
    for member in members:
        if not isinstance(member, Mapping):
            raise ValueError("finite family execution member is malformed")
        if set(member) != member_required | {"receipt_sha256"}:
            raise ValueError("finite family execution member fields changed identity")
        member_core = {
            key: item for key, item in member.items() if key != "receipt_sha256"
        }
        registered_execution = member.get("registered_witness_execution")
        source_sha = str(member.get("source_artifact_sha256") or "")
        first_parameter = first_parameter_by_source.get(source_sha)
        expected_reuse = first_parameter or ""
        if (
            member.get("schema")
            != "leanmill.finite_construction_family_member_result.v1"
            or member.get("family_receipt_sha256")
            != row.get("family_receipt_sha256")
            or member.get("authority")
            != "registered_witness_artifact_family_join"
            or member.get("receipt_sha256") != content_hash(member_core)
            or member.get("reused_from_parameter_id") != expected_reuse
            or not isinstance(registered_execution, Mapping)
            or member.get("registered_witness_execution_sha256")
            != registered_execution.get("receipt_sha256")
            or registered_execution.get("schema")
            != "leanmill.registered_witness_artifact_execution.v1"
            or registered_execution.get("receipt_sha256")
            != content_hash(
                {
                    key: item
                    for key, item in registered_execution.items()
                    if key != "receipt_sha256"
                }
            )
            or not isinstance(member.get("construction_residual_sha256"), str)
            or member.get("construction_residual_sha256")
            and (
                len(member["construction_residual_sha256"]) != 64
                or any(
                    character not in "0123456789abcdef"
                    for character in member["construction_residual_sha256"]
                )
            )
        ):
            raise ValueError("finite family execution member digest mismatch")
        first_parameter_by_source.setdefault(
            source_sha, str(member.get("parameter_id") or "")
        )
    if family is not None:
        if witness_interface is None:
            raise ValueError(
                "family-bound execution replay requires its witness interface"
            )
        interface = validate_witness_construction_interface(witness_interface)
        frozen_family = validate_finite_construction_family(
            family,
            request_id=str(row["request_id"]),
            gap_id=str(row["gap_id"]),
            context_hash=str(row["context_hash"]),
            adapter_id=str(row["adapter_id"]),
            witness_interface=interface,
            construction_origin=construction_origin,
        )
        if (
            row["family_id"] != frozen_family["family_id"]
            or row["family_receipt_sha256"] != frozen_family["receipt_sha256"]
            or row["target_interface_sha256"] != interface["interface_sha256"]
            or row["expected_parameter_ids"] != frozen_family["parameter_ids"]
            or any(
                result["source_artifact_sha256"] != member["artifact_sha256"]
                for member, result in zip(
                    frozen_family["members"], members, strict=True
                )
            )
        ):
            raise ValueError("finite family execution crossed its frozen family")
        from ztare.leanmill.witness_construction_boundary import (
            validate_registered_witness_artifact_execution,
        )

        for source_member, result in zip(
            frozen_family["members"], members, strict=True
        ):
            validate_registered_witness_artifact_execution(
                result["registered_witness_execution"],
                adapter_id=str(frozen_family["adapter_id"]),
                witness_interface=interface,
                artifact=source_member["artifact"],
            )
        parameterization_bundle = _parameterization_bundle_from_family(
            frozen_family,
            witness_interface=interface,
            construction_origin=construction_origin,
        )
        if parameterization_bundle is None:
            if any(origin_values):
                raise ValueError("ordinary finite family borrowed construction origin")
            if any(result["construction_residual_sha256"] for result in members):
                raise ValueError(
                    "ordinary finite family borrowed a construction residual"
                )
        else:
            parameterization, frozen_parameterization_execution, forge = (
                parameterization_bundle
            )
            parameterization_execution = frozen_parameterization_execution
            if origin_hashes != {
                "parameterization_sha256": parameterization["receipt_sha256"],
                "adapter_forge_quarantine_receipt_sha256": forge[
                    "receipt_sha256"
                ],
                "parameterization_execution_sha256": parameterization_execution[
                    "receipt_sha256"
                ],
            }:
                raise ValueError(
                    "finite family execution changed its construction origin"
                )
            if row["coverage_complete"] is not bool(
                parameterization_execution["coverage_complete"]
            ):
                raise ValueError("finite family execution changed construction coverage")
            expected_candidates = [
                residual["parameter_id"]
                for residual in parameterization_execution["residuals"]
                if residual["kind"] == "candidate"
            ]
            if expected != expected_candidates:
                raise ValueError("finite family execution changed candidate coverage")
            candidate_by_id = {
                str(residual["parameter_id"]): residual
                for residual in frozen_parameterization_execution["residuals"]
                if residual["kind"] == "candidate"
            }
            for result in members:
                residual = candidate_by_id.get(str(result["parameter_id"]))
                if (
                    residual is None
                    or result["construction_residual_sha256"]
                    != residual["receipt_sha256"]
                ):
                    raise ValueError(
                        "finite family member changed its frozen candidate residual"
                    )
    return row


__all__ = [
    "AdmittedConstructionOrigin",
    "FiniteConstructionFamilyResourceUnavailable",
    "FINITE_CONSTRUCTION_FAMILY_CLAIM_SCOPE",
    "FINITE_CONSTRUCTION_FAMILY_EXECUTION_SCHEMA",
    "FINITE_CONSTRUCTION_FAMILY_SCHEMA",
    "PARAMETERIZED_FAMILY_SPEC_KIND",
    "admit_construction_origin",
    "construction_witness_interface",
    "execute_finite_construction_family",
    "finite_construction_family_authoring_contract",
    "lower_reviewed_construction_parameterization",
    "validate_finite_construction_family",
    "validate_finite_construction_family_execution",
    "validate_persisted_parameterized_finite_construction_family",
]
