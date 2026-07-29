"""Content-addressed construction problems with exact, data-only semantics.

The object defined here is the stable construction identity shared by finite
enumeration and future symbolic backends.  A campaign leaf chooses the
parameters, exact constraints, and an inert artifact template.  The common
kernel validates those bytes, enforces deterministic ceilings, and returns a
closed residual algebra.  It never imports campaign-authored code and never
grants adapter, verifier, or ratification authority.

Finite parameterizations lower to the existing reviewed-family executor.  The
parameterization, Forge authority, and exact execution remain separate frozen
origins; the derived family carries only their content identities.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping as MappingABC
from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator, SchemaError, ValidationError

from ztare.common.artifact_refs import canonical_sha256_ref
from ztare.leanmill.data_only_json import strict_json_data
from ztare.leanmill.construction_wire_projection import (
    canonical_json_wire_bytes,
    project_rendered_template_wire_bytes,
)
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.theory_adapter_registry import (
    materialize_theory_adapter_capability,
    theory_adapter_capabilities,
    theory_adapter_capability_contract,
)
from ztare.leanmill.witness_construction_boundary import (
    validate_witness_construction_interface,
)


CONSTRUCTION_PARAMETERIZATION_SCHEMA = (
    "leanmill.construction_parameterization.v2"
)
SAFE_ARTIFACT_TEMPLATE_SCHEMA = "leanmill.safe_json_artifact_template.v1"
CONSTRUCTION_EXECUTION_SCHEMA = (
    "leanmill.construction_parameterization_execution.v2"
)
CONSTRUCTION_RESIDUAL_SCHEMA = "leanmill.construction_parameter_residual.v1"
CONSTRUCTION_PARAMETERIZATION_CLAIM_SCOPE = (
    "parameterized_construction_only_no_target_verification_or_ratification"
)

_RESIDUAL_KINDS = frozenset({"candidate", "rejection", "backend_unavailable"})
_MAX_IDENTITY_LENGTH = 256
_MAX_SOURCE_REF_LENGTH = 2_048
_MAX_SOURCE_REFS = 256
_MAX_PROTOCOL_INTEGER_BITS = 4_096
_MAX_PARAMETERIZATION_ENVELOPE_BYTES = 64_000_000

_COMMON_LIMIT_FIELDS = {
    "max_assignments",
    "max_template_nodes",
    "max_template_bytes",
    "max_materialized_artifact_bytes",
    "max_execution_receipt_bytes",
    "max_materialized_family_bytes",
}
_COMMON_HARD_LIMITS = {
    "max_assignments": 65_536,
    "max_template_nodes": 100_000,
    "max_template_bytes": 4_000_000,
    "max_materialized_artifact_bytes": 32_000_000,
    "max_execution_receipt_bytes": 64_000_000,
    "max_materialized_family_bytes": 64_000_000,
}
_MIN_LIMITS = {
    "max_execution_receipt_bytes": 8_192,
    "max_materialized_family_bytes": 8_192,
}

class ConstructionParameterizationError(ValueError):
    """Stable validation class for a malformed construction problem."""


class ConstructionResourceCeilingExceeded(RuntimeError):
    """Internal signal projected to a typed backend-unavailable residual."""

    def __init__(
        self,
        reason_code: str,
        *,
        resource: str = "unspecified_resource",
        observed: int = 0,
        ceiling: int = 0,
        counters: Mapping[str, int] | None = None,
        certified_assignment_count: int = 0,
        attempted_assignment_count: int = 0,
    ) -> None:
        if counters is not None and not isinstance(counters, Mapping):
            raise ValueError("construction resource metadata is malformed")
        frozen_counters = dict(counters or {})
        if (
            type(reason_code) is not str
            or not reason_code
            or len(reason_code) > 256
            or type(resource) is not str
            or not resource
            or len(resource) > 128
            or type(observed) is not int
            or observed < 0
            or type(ceiling) is not int
            or ceiling < 0
            or type(certified_assignment_count) is not int
            or certified_assignment_count < 0
            or type(attempted_assignment_count) is not int
            or attempted_assignment_count < 0
            or len(frozen_counters) > 64
            or any(
                type(field) is not str
                or not field
                or len(field) > 128
                or type(amount) is not int
                or amount < 0
                for field, amount in frozen_counters.items()
            )
        ):
            raise ValueError("construction resource metadata is malformed")
        self.reason_code = reason_code
        self.resource = resource
        self.observed = observed
        self.ceiling = ceiling
        self.counters = {
            field: int(frozen_counters[field])
            for field in sorted(frozen_counters)
        }
        self.certified_assignment_count = certified_assignment_count
        self.attempted_assignment_count = attempted_assignment_count
        super().__init__(self.reason_code)


class ConstructionBackendCapabilityUnavailable(RuntimeError):
    """Operational failure of an otherwise reviewed construction backend."""

    def __init__(
        self,
        reason_code: str,
        *,
        operation: str,
        adapter_id: str,
        capability_id: str,
        error_type: str,
        certified_assignment_count: int = 0,
        attempted_assignment_count: int = 0,
    ) -> None:
        strings = {
            "reason_code": reason_code,
            "operation": operation,
            "adapter_id": adapter_id,
            "capability_id": capability_id,
            "error_type": error_type,
        }
        if (
            any(
                type(value) is not str or not value or len(value) > 256
                for value in strings.values()
            )
            or type(certified_assignment_count) is not int
            or certified_assignment_count < 0
            or type(attempted_assignment_count) is not int
            or attempted_assignment_count < 0
        ):
            raise ValueError("construction backend-unavailable metadata is malformed")
        self.reason_code = reason_code
        self.operation = operation
        self.adapter_id = adapter_id
        self.capability_id = capability_id
        self.error_type = error_type
        self.certified_assignment_count = certified_assignment_count
        self.attempted_assignment_count = attempted_assignment_count
        super().__init__(self.reason_code)


_ADMISSION_TOKEN = object()


class AdmittedConstructionParameterization(MappingABC[str, Any]):
    """Runtime authority for one normalized problem and enumerated domain.

    The JSON mapping remains the persistent identity.  The projection and
    assignment snapshot are deliberately runtime-only: cold JSON must be
    admitted again before any consumer can treat it as semantic authority.
    """

    __slots__ = (
        "_json_bytes",
        "_backend_projection_bytes",
        "_assignment_domain_bytes",
        "_assignment_domain_receipt_bytes",
        "_sealed",
    )

    def __init__(
        self,
        value: Mapping[str, Any],
        *,
        _token: object,
        backend_projection: Mapping[str, Any],
        assignment_domain: Sequence[tuple[str, Mapping[str, Any]]],
        assignment_domain_receipt: Mapping[str, Any],
    ) -> None:
        if _token is not _ADMISSION_TOKEN:
            raise TypeError("construction admission is host-minted")
        object.__setattr__(
            self,
            "_json_bytes",
            json.dumps(
                dict(value), sort_keys=True, separators=(",", ":")
            ).encode("utf-8"),
        )
        object.__setattr__(
            self,
            "_backend_projection_bytes",
            json.dumps(
                dict(backend_projection), sort_keys=True, separators=(",", ":")
            ).encode("utf-8"),
        )
        snapshot = [
            [str(parameter_id), dict(assignment)]
            for parameter_id, assignment in assignment_domain
        ]
        object.__setattr__(
            self,
            "_assignment_domain_bytes",
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            ),
        )
        object.__setattr__(
            self,
            "_assignment_domain_receipt_bytes",
            json.dumps(
                dict(assignment_domain_receipt),
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"),
        )
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, _name: str, _value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise TypeError("admitted construction parameterization is immutable")
        object.__setattr__(self, _name, _value)

    def to_json(self) -> dict[str, Any]:
        return json.loads(self._json_bytes)

    def __getitem__(self, key: str) -> Any:
        return self.to_json()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(json.loads(self._json_bytes))

    def __len__(self) -> int:
        return len(json.loads(self._json_bytes))

    @property
    def backend_projection(self) -> dict[str, Any]:
        return json.loads(self._backend_projection_bytes)

    @property
    def assignment_domain(self) -> tuple[tuple[str, dict[str, Any]], ...]:
        return tuple(
            (str(parameter_id), dict(assignment))
            for parameter_id, assignment in json.loads(
                self._assignment_domain_bytes
            )
        )

    @property
    def assignment_domain_receipt(self) -> dict[str, Any]:
        return json.loads(self._assignment_domain_receipt_bytes)

    @property
    def certified_assignment_count(self) -> int:
        return len(json.loads(self._assignment_domain_bytes))

    def __deepcopy__(self, memo: dict[int, Any]) -> dict[str, Any]:
        # A copied/persisted mapping has bytes, not the originating admission.
        return deepcopy(self.to_json(), memo)

    def __reduce_ex__(self, _protocol: int) -> tuple[Any, tuple[str]]:
        # Pickle round trips persistent bytes only; semantic authority is lost.
        return json.loads, (self._json_bytes.decode("utf-8"),)


class AdmittedConstructionExecution(MappingABC[str, Any]):
    """Execution whose residual semantics were produced by one admitted run."""

    __slots__ = (
        "_json_bytes",
        "_admitted_parameterization",
        "_witness_schema_sha256",
        "_sealed",
    )

    def __init__(
        self,
        value: Mapping[str, Any],
        *,
        _token: object,
        parameterization: AdmittedConstructionParameterization,
        witness_schema_sha256: str,
    ) -> None:
        if _token is not _ADMISSION_TOKEN:
            raise TypeError("construction execution admission is host-minted")
        object.__setattr__(
            self,
            "_json_bytes",
            json.dumps(
                dict(value), sort_keys=True, separators=(",", ":")
            ).encode("utf-8"),
        )
        object.__setattr__(self, "_admitted_parameterization", parameterization)
        object.__setattr__(
            self, "_witness_schema_sha256", str(witness_schema_sha256)
        )
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, _name: str, _value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise TypeError("admitted construction execution is immutable")
        object.__setattr__(self, _name, _value)

    def to_json(self) -> dict[str, Any]:
        return json.loads(self._json_bytes)

    def __getitem__(self, key: str) -> Any:
        return self.to_json()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(json.loads(self._json_bytes))

    def __len__(self) -> int:
        return len(json.loads(self._json_bytes))

    @property
    def admitted_parameterization(self) -> AdmittedConstructionParameterization:
        return self._admitted_parameterization

    @property
    def certified_assignment_count(self) -> int:
        return self._admitted_parameterization.certified_assignment_count

    @property
    def attempted_assignment_count(self) -> int:
        return sum(
            1
            for residual in self.to_json().get("residuals", ())
            if isinstance(residual, Mapping)
            and isinstance(residual.get("assignment"), Mapping)
        )

    @property
    def witness_schema_sha256(self) -> str:
        return self._witness_schema_sha256

    def __deepcopy__(self, memo: dict[int, Any]) -> dict[str, Any]:
        return deepcopy(self.to_json(), memo)

    def __reduce_ex__(self, _protocol: int) -> tuple[Any, tuple[str]]:
        return json.loads, (self._json_bytes.decode("utf-8"),)


def _json_data(value: Any, *, context: str) -> Any:
    try:
        return strict_json_data(
            value,
            context=context,
            max_wire_bytes=_MAX_PARAMETERIZATION_ENVELOPE_BYTES,
            max_integer_bits=_MAX_PROTOCOL_INTEGER_BITS,
        )
    except ValueError as exc:
        raise ConstructionParameterizationError(str(exc)) from exc


def _digest(value: Any, *, context: str) -> str:
    digest = str(value or "").removeprefix("sha256:")
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ConstructionParameterizationError(f"{context} digest is malformed")
    return digest


def _canonical_json_size(value: Any) -> int:
    return canonical_json_wire_bytes(value)


def _resource_usage(value: Any) -> dict[str, int]:
    if (
        not isinstance(value, dict)
        or not value
        or len(value) > 64
        or list(value) != sorted(value)
        or any(
            not isinstance(field, str)
            or not field
            or len(field) > 128
            or type(amount) is not int
            or amount < 0
            for field, amount in value.items()
        )
    ):
        raise ConstructionParameterizationError(
            "construction execution resource usage is malformed"
        )
    return {field: int(value[field]) for field in sorted(value)}


def _bounded_receipt(
    value: Mapping[str, Any],
    *,
    maximum: int,
    context: str,
) -> dict[str, Any]:
    row = dict(value)
    observed = _canonical_json_size(row)
    if observed > maximum:
        raise ConstructionResourceCeilingExceeded(
            f"{context}_byte_limit_exhausted",
            resource=context + "_bytes",
            observed=observed,
            ceiling=maximum,
        )
    return row


def _limits(value: Any) -> dict[str, int]:
    row = _json_data(value, context="construction resource limits")
    if (
        not isinstance(row, dict)
        or set(row) != _COMMON_LIMIT_FIELDS
        or any(type(selected) is not int or selected < 1 for selected in row.values())
    ):
        raise ConstructionParameterizationError(
            "construction resource-limit fields changed identity"
        )
    for field, hard_max in _COMMON_HARD_LIMITS.items():
        selected = row.get(field)
        hard_min = _MIN_LIMITS.get(field, 1)
        if type(selected) is not int or not hard_min <= selected <= hard_max:
            raise ConstructionParameterizationError(
                f"construction resource limit {field} is invalid"
            )
    return {field: int(row[field]) for field in sorted(row)}


def _backend_capability_identity(
    value: Any, *, adapter_id: str, operation: str = "resolve"
) -> tuple[dict[str, Any], str]:
    """Bind an inert backend descriptor to one reviewed adapter capability."""

    row = _json_data(value, context="construction backend")
    if not isinstance(row, dict):
        raise ConstructionParameterizationError(
            "construction backend descriptor is malformed"
        )
    if set(row) == {"backend_id", "contract"}:
        capability_id = str(row.get("backend_id") or "")
        contract = row.get("contract")
        if not capability_id or not isinstance(contract, Mapping) or not contract:
            raise ConstructionParameterizationError(
                "construction backend descriptor is incomplete"
            )
        descriptor = dict(row)
    elif set(row) == {
        "adapter_id", "capability_id", "contract_sha256",
    }:
        if str(row.get("adapter_id") or "") != str(adapter_id):
            raise ConstructionParameterizationError(
                "construction backend capability crossed adapter identity"
            )
        capability_id = str(row.get("capability_id") or "")
        if not capability_id:
            raise ConstructionParameterizationError(
                "construction backend capability id is empty"
            )
        _digest(row.get("contract_sha256"), context="backend capability contract")
        descriptor = dict(row)
    else:
        raise ConstructionParameterizationError(
            "construction backend descriptor fields changed identity"
        )
    if capability_id not in theory_adapter_capabilities(adapter_id):
        raise ConstructionBackendCapabilityUnavailable(
            "construction_backend_capability_unavailable",
            operation=operation,
            adapter_id=adapter_id,
            capability_id=capability_id,
            error_type="CapabilityNotRegistered",
        )
    try:
        metadata = theory_adapter_capability_contract(adapter_id, capability_id)
    except ValueError as exc:
        raise ConstructionParameterizationError(
            "adapter capability lacks reviewed construction-backend role metadata"
        ) from exc
    if metadata["role"] != "construction_backend":
        raise ConstructionParameterizationError(
            "adapter capability is not a construction backend"
        )
    supplied_contract_sha256 = (
        content_hash(descriptor["contract"])
        if "contract" in descriptor
        else str(descriptor["contract_sha256"])
    )
    if supplied_contract_sha256 != metadata["contract_sha256"]:
        raise ConstructionParameterizationError(
            "construction backend contract digest is not reviewed"
        )
    return descriptor, capability_id


def _call_construction_backend(
    *,
    adapter_id: str,
    backend: Mapping[str, Any],
    operation: str,
    **kwargs: Any,
) -> Any:
    descriptor, capability_id = _backend_capability_identity(
        backend, adapter_id=adapter_id, operation=operation
    )
    try:
        return materialize_theory_adapter_capability(
            adapter_id,
            capability_id,
            operation=operation,
            backend=descriptor,
            **kwargs,
        )
    except ConstructionResourceCeilingExceeded:
        raise
    except (TimeoutError, OSError) as exc:
        raise ConstructionBackendCapabilityUnavailable(
            "construction_backend_runtime_unavailable",
            operation=operation,
            adapter_id=adapter_id,
            capability_id=capability_id,
            error_type=type(exc).__name__,
        ) from exc
    except ValueError as exc:
        if isinstance(exc, ConstructionParameterizationError):
            raise
        raise ConstructionParameterizationError(str(exc)) from exc


def _validated_backend_problem(
    *,
    adapter_id: str,
    backend: Mapping[str, Any],
    parameter_space: Any,
    backend_problem: Any,
    limits: Mapping[str, int],
) -> dict[str, Any]:
    result = _call_construction_backend(
        adapter_id=adapter_id,
        backend=backend,
        operation="validate_problem",
        parameter_space=parameter_space,
        backend_problem=backend_problem,
        resource_limits=limits,
        json_data=_json_data,
    )
    row = _json_data(result, context="construction backend problem validation")
    required = {
        "backend", "parameter_space", "backend_problem", "parameter_ids",
        "parameter_sorts", "cardinality", "projected_assignment_wire_bytes",
    }
    if (
        not isinstance(row, dict)
        or set(row) != required
        or row.get("backend") != dict(backend)
        or not isinstance(row.get("parameter_ids"), list)
        or not isinstance(row.get("parameter_sorts"), dict)
        or list(row["parameter_sorts"]) != row["parameter_ids"]
        or any(
            not isinstance(value, str) or not value
            for value in row["parameter_ids"]
        )
        or len(row["parameter_ids"]) != len(set(row["parameter_ids"]))
        or type(row.get("cardinality")) is not int
        or not 1 <= row["cardinality"] <= int(limits["max_assignments"])
        or type(row.get("projected_assignment_wire_bytes")) is not int
        or row["projected_assignment_wire_bytes"] < 1
    ):
        raise ConstructionParameterizationError(
            "construction backend returned an invalid problem projection"
        )
    wire_ceiling = int(limits["max_execution_receipt_bytes"])
    projected_wire_bytes = int(row["projected_assignment_wire_bytes"])
    if projected_wire_bytes > wire_ceiling:
        raise ConstructionResourceCeilingExceeded(
            "construction_assignment_wire_limit_exhausted",
            resource="assignment_wire_bytes",
            observed=projected_wire_bytes,
            ceiling=wire_ceiling,
            counters={
                "certified_assignment_count": int(row["cardinality"]),
                "projected_assignment_wire_bytes": projected_wire_bytes,
            },
            certified_assignment_count=int(row["cardinality"]),
            attempted_assignment_count=0,
        )
    return row


def _template_node_count(
    value: Any,
    *,
    parameter_sorts: Mapping[str, str],
    depth: int = 0,
) -> int:
    if depth > 128:
        raise ConstructionParameterizationError("artifact template is too deep")
    if isinstance(value, Mapping):
        if "$parameter" in value:
            if set(value) != {"$parameter"}:
                raise ConstructionParameterizationError(
                    "parameter template node fields changed identity"
                )
            parameter_id = str(value.get("$parameter") or "")
            if parameter_id not in parameter_sorts:
                raise ConstructionParameterizationError(
                    "artifact template references an unknown parameter"
                )
            return 1
        if any(str(key).startswith("$") for key in value):
            raise ConstructionParameterizationError(
                "artifact template contains an executable reserved node"
            )
        return 1 + sum(
            _template_node_count(
                item, parameter_sorts=parameter_sorts, depth=depth + 1
            )
            for item in value.values()
        )
    if isinstance(value, list):
        return 1 + sum(
            _template_node_count(
                item, parameter_sorts=parameter_sorts, depth=depth + 1
            )
            for item in value
        )
    if type(value) in {str, int, bool} or value is None:
        return 1
    raise ConstructionParameterizationError(
        "artifact template contains a non-JSON value"
    )


def _materializer(
    value: Any,
    *,
    parameter_sorts: Mapping[str, str],
    limits: Mapping[str, int],
) -> dict[str, Any]:
    row = _json_data(value, context="construction materializer")
    if not isinstance(row, dict) or set(row) != {"schema", "template"}:
        raise ConstructionParameterizationError(
            "construction materializer fields changed identity"
        )
    if row.get("schema") != SAFE_ARTIFACT_TEMPLATE_SCHEMA:
        raise ConstructionParameterizationError(
            "construction materializer must be a safe JSON template"
        )
    nodes = _template_node_count(
        row.get("template"), parameter_sorts=parameter_sorts
    )
    if nodes > int(limits["max_template_nodes"]):
        raise ConstructionParameterizationError(
            "artifact template node ceiling exceeded"
        )
    template = _json_data(row["template"], context="artifact template")
    template_bytes = len(
        json.dumps(
            template,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    )
    if template_bytes > int(limits["max_template_bytes"]):
        raise ConstructionParameterizationError(
            "artifact template byte ceiling exceeded"
        )
    return {
        "schema": SAFE_ARTIFACT_TEMPLATE_SCHEMA,
        "template": template,
    }


def _search_order(value: Any, *, parameter_ids: Sequence[str]) -> dict[str, Any]:
    row = _json_data(value, context="construction search order")
    expected = {
        "kind": "lexicographic",
        "parameter_ids": list(parameter_ids),
        "domain_order": "declared_canonical",
    }
    if row != expected:
        raise ConstructionParameterizationError(
            "construction search order crossed parameter identity"
        )
    return expected


def _structural_search_order(value: Any) -> dict[str, Any]:
    """Validate the field-neutral search-order envelope without a backend call."""

    row = _json_data(value, context="construction search order")
    if (
        not isinstance(row, dict)
        or set(row) != {"kind", "parameter_ids", "domain_order"}
        or row.get("kind") != "lexicographic"
        or row.get("domain_order") != "declared_canonical"
        or not isinstance(row.get("parameter_ids"), list)
        or not row["parameter_ids"]
        or any(
            not isinstance(parameter_id, str) or not parameter_id
            for parameter_id in row["parameter_ids"]
        )
        or len(row["parameter_ids"]) != len(set(row["parameter_ids"]))
    ):
        raise ConstructionParameterizationError(
            "construction search order is malformed"
        )
    return dict(row)


def _symmetry_policy(value: Any) -> dict[str, Any]:
    row = _json_data(value, context="construction symmetry policy")
    if row == {"kind": "none"}:
        return row
    if not isinstance(row, dict) or set(row) != {
        "kind",
        "equivalence_id",
        "representative_policy",
        "coverage_witness_ref",
    }:
        raise ConstructionParameterizationError(
            "construction symmetry policy fields changed identity"
        )
    if (
        row.get("kind") != "reviewed_explicit_quotient"
        or not all(
            isinstance(row.get(field), str) and str(row[field]).strip()
            for field in (
                "equivalence_id",
                "representative_policy",
                "coverage_witness_ref",
            )
        )
    ):
        raise ConstructionParameterizationError(
            "construction explicit quotient is incomplete"
        )
    try:
        canonical_coverage_ref = canonical_sha256_ref(
            row["coverage_witness_ref"]
        )
    except ValueError as exc:
        raise ConstructionParameterizationError(
            "construction quotient coverage witness is not content-addressed"
        ) from exc
    if row["coverage_witness_ref"] != canonical_coverage_ref:
        raise ConstructionParameterizationError(
            "construction quotient coverage witness ref is not canonical"
        )
    return row


def _lineage_and_authorship(
    lineage: Any, authorship: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    lineage_row = _json_data(lineage, context="construction lineage")
    authorship_row = _json_data(authorship, context="construction authorship")
    if not isinstance(lineage_row, dict) or not isinstance(authorship_row, dict):
        raise ConstructionParameterizationError(
            "construction lineage/authorship is malformed"
        )
    phase = str(authorship_row.get("phase") or "")
    expected_authorship_fields = {
        "authority",
        "role",
        "phase",
        "registry_mutation",
        "generated_code_import",
    }
    if (
        set(authorship_row) != expected_authorship_fields
        or authorship_row.get("authority")
        != "campaign_local_subscription_leaf"
        or authorship_row.get("role") != "adapter_forge"
        or authorship_row.get("registry_mutation") is not False
        or authorship_row.get("generated_code_import") is not False
    ):
        raise ConstructionParameterizationError(
            "construction authorship claims unsupported authority"
        )
    if lineage_row.get("kind") == "root":
        if set(lineage_row) != {"kind"} or phase != "pre_outcome_parameterization":
            raise ConstructionParameterizationError(
                "root construction parameterization must precede outcomes"
            )
    else:
        raise ConstructionParameterizationError(
            "construction lineage kind is unsupported"
        )
    return lineage_row, authorship_row


def build_construction_parameterization(
    *,
    campaign_id: str,
    request_id: str,
    gap_id: str,
    context_hash: str,
    context_epoch: int,
    adapter_id: str,
    target_interface_sha256: str,
    source_refs: Sequence[str],
    parameter_space: Mapping[str, Any],
    backend_problem: Mapping[str, Any],
    materializer: Mapping[str, Any],
    backend: Mapping[str, Any],
    resource_limits: Mapping[str, Any],
    search_order: Mapping[str, Any],
    symmetry_policy: Mapping[str, Any] | None = None,
    lineage: Mapping[str, Any] | None = None,
    authorship: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    limits = _limits(resource_limits)
    backend_descriptor, _capability_id = _backend_capability_identity(
        backend, adapter_id=str(adapter_id)
    )
    space = _json_data(
        parameter_space, context="construction parameter space draft"
    )
    problem = _json_data(
        backend_problem, context="construction backend problem draft"
    )
    if not isinstance(space, dict) or not space:
        raise ConstructionParameterizationError(
            "construction parameter space must be one nonempty object"
        )
    if not isinstance(problem, dict) or not problem:
        raise ConstructionParameterizationError(
            "construction backend problem must be one nonempty object"
        )
    normalized_search_order = _structural_search_order(search_order)
    parameter_ids = list(normalized_search_order["parameter_ids"])
    normalized_materializer = _materializer(
        materializer,
        parameter_sorts={parameter_id: "opaque" for parameter_id in parameter_ids},
        limits=limits,
    )
    core = {
        "schema": CONSTRUCTION_PARAMETERIZATION_SCHEMA,
        "campaign_id": str(campaign_id),
        "request_id": str(request_id),
        "gap_id": str(gap_id),
        "context_hash": str(context_hash),
        "context_epoch": context_epoch,
        "adapter_id": str(adapter_id),
        "target_interface_sha256": str(target_interface_sha256),
        "source_refs": [str(ref) for ref in source_refs],
        "parameter_space": space,
        "backend_problem": problem,
        "materializer": normalized_materializer,
        "backend": backend_descriptor,
        "resource_limits": limits,
        "search_order": normalized_search_order,
        "symmetry_policy": dict(symmetry_policy or {"kind": "none"}),
        "lineage": dict(lineage or {"kind": "root"}),
        "authorship": dict(
            authorship
            or {
                "authority": "campaign_local_subscription_leaf",
                "role": "adapter_forge",
                "phase": "pre_outcome_parameterization",
                "registry_mutation": False,
                "generated_code_import": False,
            }
        ),
        "claim_scope": CONSTRUCTION_PARAMETERIZATION_CLAIM_SCOPE,
    }
    core = _json_data(core, context="construction parameterization draft")
    identity = "construction-parameterization:" + content_hash(core)
    return validate_construction_parameterization(
        {
            **core,
            "parameterization_id": identity,
            "receipt_sha256": content_hash(
                {**core, "parameterization_id": identity}
            ),
        }
    )


def validate_construction_parameterization(
    value: Mapping[str, Any],
    *,
    campaign_id: str | None = None,
    request_id: str | None = None,
    gap_id: str | None = None,
    context_hash: str | None = None,
    context_epoch: int | None = None,
    adapter_id: str | None = None,
    target_interface_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate only the persistent, content-addressed protocol identity.

    This parser intentionally does not invoke a construction backend.  Call
    :func:`admit_construction_parameterization` at the owned semantic boundary.
    """

    original = value
    row = _json_data(
        value.to_json()
        if isinstance(value, AdmittedConstructionParameterization)
        else value,
        context="construction parameterization",
    )
    required = {
        "schema",
        "campaign_id",
        "request_id",
        "gap_id",
        "context_hash",
        "context_epoch",
        "adapter_id",
        "target_interface_sha256",
        "source_refs",
        "parameter_space",
        "backend_problem",
        "materializer",
        "backend",
        "resource_limits",
        "search_order",
        "symmetry_policy",
        "lineage",
        "authorship",
        "claim_scope",
        "parameterization_id",
        "receipt_sha256",
    }
    if not isinstance(row, dict) or set(row) != required:
        raise ConstructionParameterizationError(
            "construction parameterization fields changed identity"
        )
    if (
        row.get("schema") != CONSTRUCTION_PARAMETERIZATION_SCHEMA
        or row.get("claim_scope") != CONSTRUCTION_PARAMETERIZATION_CLAIM_SCOPE
        or type(row.get("context_epoch")) is not int
        or int(row["context_epoch"]) < 0
    ):
        raise ConstructionParameterizationError(
            "construction parameterization identity is malformed"
        )
    for field, expected in (
        ("campaign_id", campaign_id),
        ("request_id", request_id),
        ("gap_id", gap_id),
        ("context_hash", context_hash),
        ("adapter_id", adapter_id),
        ("target_interface_sha256", target_interface_sha256),
    ):
        actual = str(row.get(field) or "")
        if (
            not actual
            or len(actual) > _MAX_IDENTITY_LENGTH
            or (expected is not None and actual != str(expected))
        ):
            raise ConstructionParameterizationError(
                f"construction parameterization crossed {field}"
            )
    if context_epoch is not None and row["context_epoch"] != context_epoch:
        raise ConstructionParameterizationError(
            "construction parameterization crossed context_epoch"
        )
    _digest(row["target_interface_sha256"], context="target interface")
    refs = row.get("source_refs")
    if (
        not isinstance(refs, list)
        or not refs
        or len(refs) > _MAX_SOURCE_REFS
        or any(not isinstance(ref, str) or not ref for ref in refs)
        or any(len(ref) > _MAX_SOURCE_REF_LENGTH for ref in refs)
        or refs != sorted(refs)
        or len(refs) != len(set(refs))
    ):
        raise ConstructionParameterizationError(
            "construction parameterization source refs are not canonical"
        )
    limits = _limits(row.get("resource_limits"))
    backend, _capability_id = _backend_capability_identity(
        row.get("backend"), adapter_id=str(row["adapter_id"])
    )
    space = _json_data(
        row.get("parameter_space"), context="construction parameter space"
    )
    normalized_problem = _json_data(
        row.get("backend_problem"), context="construction backend problem"
    )
    if not isinstance(space, dict) or not space:
        raise ConstructionParameterizationError(
            "construction parameter space must be one nonempty object"
        )
    if not isinstance(normalized_problem, dict) or not normalized_problem:
        raise ConstructionParameterizationError(
            "construction backend problem must be one nonempty object"
        )
    search_order = _structural_search_order(row.get("search_order"))
    parameter_ids = list(search_order["parameter_ids"])
    materializer = _materializer(
        row.get("materializer"),
        parameter_sorts={parameter_id: "opaque" for parameter_id in parameter_ids},
        limits=limits,
    )
    symmetry_policy = _symmetry_policy(row.get("symmetry_policy"))
    lineage, authorship = _lineage_and_authorship(
        row.get("lineage"), row.get("authorship")
    )
    core = {
        "schema": CONSTRUCTION_PARAMETERIZATION_SCHEMA,
        "campaign_id": str(row["campaign_id"]),
        "request_id": str(row["request_id"]),
        "gap_id": str(row["gap_id"]),
        "context_hash": str(row["context_hash"]),
        "context_epoch": int(row["context_epoch"]),
        "adapter_id": str(row["adapter_id"]),
        "target_interface_sha256": str(row["target_interface_sha256"]),
        "source_refs": list(refs),
        "parameter_space": space,
        "backend_problem": normalized_problem,
        "materializer": materializer,
        "backend": backend,
        "resource_limits": limits,
        "search_order": search_order,
        "symmetry_policy": symmetry_policy,
        "lineage": lineage,
        "authorship": authorship,
        "claim_scope": CONSTRUCTION_PARAMETERIZATION_CLAIM_SCOPE,
    }
    expected_id = "construction-parameterization:" + content_hash(core)
    signed_core = {**core, "parameterization_id": expected_id}
    if (
        row.get("parameterization_id") != expected_id
        or row.get("receipt_sha256") != content_hash(signed_core)
    ):
        raise ConstructionParameterizationError(
            "construction parameterization digest mismatch"
        )
    validated = {
        **signed_core,
        "receipt_sha256": content_hash(signed_core),
    }
    if (
        isinstance(original, AdmittedConstructionParameterization)
        and dict(original) == validated
    ):
        return original
    return validated


def construction_parameterization_authoring_contract(
    *,
    campaign_id: str,
    request_id: str,
    gap_id: str,
    context_hash: str,
    context_epoch: int,
    adapter_id: str,
    witness_interface: Mapping[str, Any],
) -> dict[str, Any]:
    """Expose the frozen common schema to a campaign-local author."""

    interface = validate_witness_construction_interface(witness_interface)
    backend_contracts: list[dict[str, Any]] = []
    for capability_id in theory_adapter_capabilities(adapter_id):
        try:
            metadata = theory_adapter_capability_contract(
                adapter_id, capability_id
            )
        except ValueError:
            continue
        if metadata["role"] != "construction_backend":
            continue
        descriptor = {
            "adapter_id": str(adapter_id),
            "capability_id": capability_id,
            "contract_sha256": metadata["contract_sha256"],
        }
        row = _call_construction_backend(
            adapter_id=str(adapter_id),
            backend=descriptor,
            operation="authoring_contract",
        )
        canonical = _json_data(
            row, context="construction backend authoring contract"
        )
        if (
            not isinstance(canonical, dict)
            or canonical.get("backend_capability") != descriptor
            or not str(canonical.get("parameter_space_schema") or "")
            or not str(canonical.get("backend_problem_schema") or "")
            or canonical.get("availability")
            not in {"available", "typed_unavailable"}
        ):
            raise ConstructionParameterizationError(
                "reviewed construction backend exposed an invalid authoring contract"
            )
        backend_contracts.append(canonical)
    if not backend_contracts:
        raise ConstructionBackendCapabilityUnavailable(
            "construction_backend_capability_unavailable",
            operation="authoring_contract",
            adapter_id=str(adapter_id),
            capability_id="none_registered",
            error_type="NoRegisteredConstructionBackend",
        )
    constants = {
        "schema": CONSTRUCTION_PARAMETERIZATION_SCHEMA,
        "campaign_id": str(campaign_id),
        "request_id": str(request_id),
        "gap_id": str(gap_id),
        "context_hash": str(context_hash),
        "context_epoch": int(context_epoch),
        "adapter_id": str(adapter_id),
        "target_interface_sha256": str(interface["interface_sha256"]),
        "claim_scope": CONSTRUCTION_PARAMETERIZATION_CLAIM_SCOPE,
        "authorship": {
            "authority": "campaign_local_subscription_leaf",
            "role": "adapter_forge",
            "phase": "pre_outcome_parameterization",
            "registry_mutation": False,
            "generated_code_import": False,
        },
    }
    core = {
        "schema": "leanmill.construction_parameterization_authoring_contract.v1",
        "constants": constants,
        "safe_materializer_schema": SAFE_ARTIFACT_TEMPLATE_SCHEMA,
        "construction_backend_capabilities": backend_contracts,
        "search_order": {
            "kind": "lexicographic",
            "parameter_ids": "the canonical parameter-space ids in order",
            "domain_order": "declared_canonical",
        },
        "symmetry_policies": ["none", "reviewed_explicit_quotient"],
        "common_resource_ceilings": dict(_COMMON_HARD_LIMITS),
        "witness_schema": dict(interface["witness_schema"]),
        "execution_boundary": (
            "data_only_no_generated_code_import_no_registry_mutation"
        ),
        "review_ordering": (
            "parameterization and materialized artifacts are reviewed before "
            "constraint or target outcomes"
        ),
        "authority": "construction_parameterization_common_interface",
    }
    return {**core, "receipt_sha256": content_hash(core)}



def enumerate_parameter_assignments(
    parameterization: Mapping[str, Any]
) -> tuple[tuple[str, dict[str, Any]], ...]:
    if not isinstance(parameterization, AdmittedConstructionParameterization):
        raise ConstructionParameterizationError(
            "assignment enumeration requires explicit semantic admission"
        )
    admitted = _validate_admitted_parameterization(parameterization)
    return admitted.assignment_domain


def certified_construction_parameter_count(
    parameterization: Mapping[str, Any],
) -> int:
    """Return an already-admitted backend cardinality without backend replay."""

    if not isinstance(parameterization, AdmittedConstructionParameterization):
        raise ConstructionParameterizationError(
            "certified parameter count requires explicit semantic admission"
        )
    admitted = _validate_admitted_parameterization(parameterization)
    return admitted.certified_assignment_count


def _annotate_assignment_progress(
    error: ConstructionResourceCeilingExceeded
    | ConstructionBackendCapabilityUnavailable,
    *,
    certified: int,
    attempted: int,
) -> None:
    error.certified_assignment_count = max(
        int(error.certified_assignment_count), int(certified)
    )
    error.attempted_assignment_count = max(
        int(error.attempted_assignment_count), int(attempted)
    )


def _assignment_domain_receipt(
    frozen: Mapping[str, Any],
    projection: Mapping[str, Any],
    assignments: Sequence[tuple[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    snapshot = [
        {"parameter_id": parameter_id, "assignment": dict(assignment)}
        for parameter_id, assignment in assignments
    ]
    core = {
        "schema": "leanmill.certified_construction_assignment_domain.v1",
        "parameterization_sha256": str(frozen["receipt_sha256"]),
        "backend_projection_sha256": content_hash(dict(projection)),
        "assignment_count": len(snapshot),
        "assignment_ids": [row["parameter_id"] for row in snapshot],
        "assignment_domain_sha256": content_hash(snapshot),
        "assignment_wire_bytes": _canonical_json_size(snapshot),
        "authority": "reviewed_construction_backend_semantic_admission",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _validate_admitted_parameterization(
    value: AdmittedConstructionParameterization,
) -> AdmittedConstructionParameterization:
    frozen = validate_construction_parameterization(value)
    if frozen is not value:
        raise ConstructionParameterizationError(
            "construction parameterization lost its runtime admission"
        )
    projection = value.backend_projection
    assignments = value.assignment_domain
    expected_receipt = _assignment_domain_receipt(
        value, projection, assignments
    )
    if (
        projection.get("backend") != value["backend"]
        or projection.get("parameter_space") != value["parameter_space"]
        or projection.get("backend_problem") != value["backend_problem"]
        or projection.get("parameter_ids")
        != value["search_order"]["parameter_ids"]
        or projection.get("cardinality") != len(assignments)
        or value.assignment_domain_receipt != expected_receipt
    ):
        raise ConstructionParameterizationError(
            "construction parameterization admission changed identity"
        )
    return value


def admit_construction_parameterization(
    parameterization: Mapping[str, Any],
) -> AdmittedConstructionParameterization:
    """Explicitly admit backend semantics and freeze one assignment snapshot."""

    if isinstance(parameterization, AdmittedConstructionParameterization):
        return _validate_admitted_parameterization(parameterization)
    frozen = validate_construction_parameterization(parameterization)
    try:
        projection = _validated_backend_problem(
            adapter_id=str(frozen["adapter_id"]),
            backend=frozen["backend"],
            parameter_space=frozen["parameter_space"],
            backend_problem=frozen["backend_problem"],
            limits=frozen["resource_limits"],
        )
    except (
        ConstructionResourceCeilingExceeded,
        ConstructionBackendCapabilityUnavailable,
    ) as exc:
        _annotate_assignment_progress(exc, certified=0, attempted=0)
        raise
    if (
        projection["backend"] != frozen["backend"]
        or projection["parameter_space"] != frozen["parameter_space"]
        or projection["backend_problem"] != frozen["backend_problem"]
    ):
        raise ConstructionParameterizationError(
            "construction backend semantic projection changed signed bytes"
        )
    parameter_ids = list(projection["parameter_ids"])
    _search_order(frozen["search_order"], parameter_ids=parameter_ids)
    if _materializer(
        frozen["materializer"],
        parameter_sorts=dict(projection["parameter_sorts"]),
        limits=frozen["resource_limits"],
    ) != frozen["materializer"]:
        raise ConstructionParameterizationError(
            "construction materializer changed during semantic admission"
        )
    assignments = _enumerate_parameter_assignments_projection(
        frozen, projection
    )
    receipt = _assignment_domain_receipt(frozen, projection, assignments)
    return AdmittedConstructionParameterization(
        frozen,
        _token=_ADMISSION_TOKEN,
        backend_projection=projection,
        assignment_domain=assignments,
        assignment_domain_receipt=receipt,
    )


def _enumerate_parameter_assignments_projection(
    frozen: Mapping[str, Any],
    problem: Mapping[str, Any],
) -> tuple[tuple[str, dict[str, Any]], ...]:
    parameter_ids = list(problem["parameter_ids"])
    cardinality = int(problem["cardinality"])
    try:
        result = _call_construction_backend(
            adapter_id=str(frozen["adapter_id"]),
            backend=frozen["backend"],
            operation="enumerate_assignments",
            parameter_space=frozen["parameter_space"],
        )
    except (
        ConstructionResourceCeilingExceeded,
        ConstructionBackendCapabilityUnavailable,
    ) as exc:
        _annotate_assignment_progress(exc, certified=cardinality, attempted=0)
        raise
    if not isinstance(result, (list, tuple)):
        raise ConstructionParameterizationError(
            "construction backend assignment enumeration is malformed"
        )
    if len(result) != cardinality:
        raise ConstructionParameterizationError(
            "construction backend assignment coverage is invalid"
        )
    rows: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    cumulative_wire_bytes = 2 + max(0, cardinality - 1)
    wire_ceiling = int(
        frozen["resource_limits"]["max_execution_receipt_bytes"]
    )
    for raw in result:
        if (
            not isinstance(raw, (list, tuple))
            or len(raw) != 2
            or not isinstance(raw[0], str)
            or not isinstance(raw[1], Mapping)
        ):
            raise ConstructionParameterizationError(
                "construction backend assignment row is malformed"
            )
        assignment = _json_data(
            raw[1], context="construction backend assignment"
        )
        if not isinstance(assignment, dict) or not assignment:
            raise ConstructionParameterizationError(
                "construction backend assignment must be one nonempty object"
            )
        cumulative_wire_bytes += (
            5
            + _canonical_json_size("assignment")
            + _canonical_json_size(assignment)
            + _canonical_json_size("parameter_id")
            + _canonical_json_size(raw[0])
        )
        if cumulative_wire_bytes > wire_ceiling:
            error = ConstructionResourceCeilingExceeded(
                "construction_assignment_wire_limit_exhausted",
                resource="assignment_wire_bytes",
                observed=cumulative_wire_bytes,
                ceiling=wire_ceiling,
                counters={
                    "certified_assignment_count": cardinality,
                    "observed_assignment_wire_bytes": cumulative_wire_bytes,
                },
                certified_assignment_count=cardinality,
                attempted_assignment_count=len(rows) + 1,
            )
            raise error
        if list(assignment) != parameter_ids:
            raise ConstructionParameterizationError(
                "construction backend assignments crossed parameter order"
            )
        parameter_id = "assignment:" + content_hash(assignment)
        if raw[0] != parameter_id:
            raise ConstructionParameterizationError(
                "construction backend assignment changed content identity"
            )
        if parameter_id in seen:
            raise ConstructionParameterizationError(
                "construction backend repeated an assignment"
            )
        seen.add(parameter_id)
        rows.append((parameter_id, assignment))
    projected_wire_bytes = int(problem["projected_assignment_wire_bytes"])
    if cumulative_wire_bytes != projected_wire_bytes:
        raise ConstructionParameterizationError(
            "construction backend assignment wire projection changed identity"
        )
    return tuple(rows)


def _enumerate_parameter_assignments_frozen(
    frozen: Mapping[str, Any],
) -> tuple[tuple[str, dict[str, Any]], ...]:
    """Compatibility helper whose call is explicitly a semantic admission."""

    return admit_construction_parameterization(frozen).assignment_domain


def _render_template(value: Any, assignment: Mapping[str, Any]) -> Any:
    if isinstance(value, Mapping):
        if set(value) == {"$parameter"}:
            return _json_data(
                assignment[str(value["$parameter"])], context="parameter value"
            )
        return {
            key: _render_template(item, assignment)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_render_template(item, assignment) for item in value]
    return value


def materialize_parameter_artifact(
    parameterization: Mapping[str, Any],
    assignment: Mapping[str, Any],
    *,
    witness_schema: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(parameterization, AdmittedConstructionParameterization):
        raise ConstructionParameterizationError(
            "artifact materialization requires explicit semantic admission"
        )
    frozen = _validate_admitted_parameterization(parameterization)
    try:
        Draft202012Validator.check_schema(dict(witness_schema))
        validator = Draft202012Validator(dict(witness_schema))
    except SchemaError as exc:
        raise ConstructionParameterizationError(
            "construction target witness schema is invalid"
        ) from exc
    return _materialize_frozen_parameter_artifact(
        frozen,
        assignment,
        validator=validator,
        materialization_budget=_MaterializationBudget(
            frozen["resource_limits"]
        ),
        certified_assignments=dict(frozen.assignment_domain),
    )


def _materialize_frozen_parameter_artifact(
    frozen: Mapping[str, Any],
    assignment: Mapping[str, Any],
    *,
    validator: Draft202012Validator,
    materialization_budget: _MaterializationBudget,
    certified_assignments: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    candidate = _json_data(assignment, context="construction assignment")
    certified = (
        dict(certified_assignments)
        if certified_assignments is not None
        else dict(_enumerate_parameter_assignments_frozen(frozen))
    )
    parameter_id = "assignment:" + content_hash(candidate)
    expected = certified.get(parameter_id)
    if (
        not isinstance(candidate, dict)
        or not candidate
        or not isinstance(expected, Mapping)
        or candidate != dict(expected)
    ):
        raise ConstructionParameterizationError(
            "construction assignment lacks backend coverage authority"
        )
    projected_bytes = materialization_budget.preflight(
        frozen["materializer"]["template"],
        candidate,
    )
    artifact = _render_template(frozen["materializer"]["template"], candidate)
    if not isinstance(artifact, Mapping) or not artifact:
        raise ConstructionParameterizationError(
            "construction artifact template produced no JSON object"
        )
    try:
        validator.validate(dict(artifact))
    except ValidationError as exc:
        raise ConstructionParameterizationError(
            "construction artifact violates the target witness schema"
        ) from exc
    materialization_budget.commit(artifact, projected_bytes=projected_bytes)
    return dict(artifact)


class _MaterializationBudget:
    def __init__(self, limits: Mapping[str, int]) -> None:
        self.limits = limits
        self.materialized_artifact_bytes = 0
        self.attempted_artifacts = 0

    def preflight(
        self,
        template: Any,
        assignment: Mapping[str, Any],
    ) -> int:
        self.attempted_artifacts += 1
        ceiling = int(self.limits["max_materialized_artifact_bytes"])
        remaining = ceiling - self.materialized_artifact_bytes
        amount = project_rendered_template_wire_bytes(
            template,
            assignment,
            max_bytes=remaining,
        )
        if self.materialized_artifact_bytes + amount > ceiling:
            raise ConstructionResourceCeilingExceeded(
                "materialized_artifact_byte_limit_exhausted",
                resource="materialized_artifact_bytes",
                observed=self.materialized_artifact_bytes + amount,
                ceiling=ceiling,
                counters={
                    "attempted_artifacts": self.attempted_artifacts,
                    "materialized_artifact_bytes": (
                        self.materialized_artifact_bytes
                    ),
                    "observed_artifact_bytes_lower_bound": amount,
                    "projection_complete": 0,
                },
                attempted_assignment_count=self.attempted_artifacts,
            )
        return amount

    def commit(
        self,
        artifact: Mapping[str, Any],
        *,
        projected_bytes: int,
    ) -> None:
        actual = _canonical_json_size(artifact)
        if actual != projected_bytes:
            raise RuntimeError(
                "rendered construction artifact crossed its wire projection"
            )
        self.materialized_artifact_bytes += actual

def replay_parameter_artifact_schema(
    parameterization: Mapping[str, Any],
    *,
    witness_schema: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay all safe materializations once, under the declared byte ceiling."""

    if not isinstance(parameterization, AdmittedConstructionParameterization):
        raise ConstructionParameterizationError(
            "artifact schema replay requires explicit semantic admission"
        )
    frozen = _validate_admitted_parameterization(parameterization)
    try:
        Draft202012Validator.check_schema(dict(witness_schema))
        validator = Draft202012Validator(dict(witness_schema))
    except SchemaError as exc:
        raise ConstructionParameterizationError(
            "construction target witness schema is invalid"
        ) from exc
    budget = _MaterializationBudget(frozen["resource_limits"])
    certified_assignments = dict(frozen.assignment_domain)
    chain = "0" * 64
    count = 0
    for parameter_id, assignment in frozen.assignment_domain:
        artifact = _materialize_frozen_parameter_artifact(
            frozen,
            assignment,
            validator=validator,
            materialization_budget=budget,
            certified_assignments=certified_assignments,
        )
        chain = content_hash(
            {
                "prior_sha256": chain,
                "parameter_id": parameter_id,
                "artifact_sha256": content_hash(artifact),
            }
        )
        count += 1
    core = {
        "schema": "leanmill.parameter_artifact_schema_replay.v1",
        "parameterization_sha256": frozen["receipt_sha256"],
        "witness_schema_sha256": content_hash(dict(witness_schema)),
        "assignment_count": count,
        "assignment_domain_receipt_sha256": frozen.assignment_domain_receipt[
            "receipt_sha256"
        ],
        "artifact_digest_chain_sha256": chain,
        "materialized_artifact_bytes": budget.materialized_artifact_bytes,
        "complete": True,
        "authority": "safe_construction_materializer",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def materialize_construction_candidates(
    parameterization: Mapping[str, Any],
    execution: Mapping[str, Any],
    *,
    witness_schema: Mapping[str, Any],
) -> tuple[tuple[dict[str, Any], dict[str, Any]], ...]:
    """Materialize exactly the candidate residuals after one frozen replay."""

    frozen = admit_construction_parameterization(parameterization)
    if not isinstance(execution, AdmittedConstructionExecution):
        raise ConstructionParameterizationError(
            "construction execution requires explicit semantic admission"
        )
    result = _validate_admitted_execution(
        execution,
        parameterization=frozen,
        witness_schema=witness_schema,
    )
    try:
        Draft202012Validator.check_schema(dict(witness_schema))
        validator = Draft202012Validator(dict(witness_schema))
    except SchemaError as exc:
        raise ConstructionParameterizationError(
            "construction target witness schema is invalid"
        ) from exc
    budget = _MaterializationBudget(frozen["resource_limits"])
    certified_assignments = dict(frozen.assignment_domain)
    rows = []
    for residual in result["residuals"]:
        if residual["kind"] != "candidate":
            continue
        artifact = _materialize_frozen_parameter_artifact(
            frozen,
            residual["assignment"],
            validator=validator,
            materialization_budget=budget,
            certified_assignments=certified_assignments,
        )
        if residual["artifact_sha256"] != content_hash(artifact):
            raise ConstructionParameterizationError(
                "construction candidate artifact changed before lowering"
            )
        rows.append((dict(residual), artifact))
    return tuple(rows)


def _materialize_persisted_construction_candidates_projection(
    parameterization: Mapping[str, Any],
    execution: Mapping[str, Any],
    *,
    witness_schema: Mapping[str, Any],
) -> tuple[tuple[dict[str, Any], dict[str, Any]], ...]:
    """Replay only the signed template projection; grant no backend authority."""

    frozen = validate_construction_parameterization(parameterization)
    result = validate_construction_parameterization_execution(
        execution,
        parameterization=frozen,
        witness_schema=witness_schema,
    )
    try:
        Draft202012Validator.check_schema(dict(witness_schema))
        validator = Draft202012Validator(dict(witness_schema))
    except SchemaError as exc:
        raise ConstructionParameterizationError(
            "construction target witness schema is invalid"
        ) from exc
    persisted_assignments = {
        str(residual["parameter_id"]): dict(residual["assignment"])
        for residual in result["residuals"]
        if isinstance(residual.get("assignment"), Mapping)
    }
    budget = _MaterializationBudget(frozen["resource_limits"])
    rows: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for residual in result["residuals"]:
        if residual["kind"] != "candidate":
            continue
        artifact = _materialize_frozen_parameter_artifact(
            frozen,
            residual["assignment"],
            validator=validator,
            materialization_budget=budget,
            certified_assignments=persisted_assignments,
        )
        if residual["artifact_sha256"] != content_hash(artifact):
            raise ConstructionParameterizationError(
                "persisted construction projection changed candidate artifact"
            )
        rows.append((dict(residual), artifact))
    return tuple(rows)


def _residual(
    frozen: Mapping[str, Any],
    *,
    parameter_id: str,
    assignment: Mapping[str, Any] | None,
    artifact_sha256: str,
    kind: str,
    reason_code: str,
    backend_check_id: str,
    observed: Mapping[str, Any],
) -> dict[str, Any]:
    if kind not in _RESIDUAL_KINDS:
        raise ConstructionParameterizationError(
            "unknown construction residual kind"
        )
    assignment_row = (
        _json_data(assignment, context="construction residual assignment")
        if assignment is not None
        else None
    )
    core = {
        "schema": CONSTRUCTION_RESIDUAL_SCHEMA,
        "campaign_id": frozen["campaign_id"],
        "request_id": frozen["request_id"],
        "gap_id": frozen["gap_id"],
        "context_hash": frozen["context_hash"],
        "context_epoch": frozen["context_epoch"],
        "adapter_id": frozen["adapter_id"],
        "target_interface_sha256": frozen["target_interface_sha256"],
        "parameterization_sha256": frozen["receipt_sha256"],
        "backend_problem_sha256": content_hash(frozen["backend_problem"]),
        "backend_sha256": content_hash(frozen["backend"]),
        "parameter_id": str(parameter_id),
        "assignment": assignment_row,
        "assignment_sha256": (
            content_hash(assignment_row) if assignment_row is not None else ""
        ),
        "artifact_sha256": str(artifact_sha256),
        "kind": kind,
        "reason_code": str(reason_code),
        "backend_check_id": str(backend_check_id),
        "observed": _json_data(observed, context="construction residual observed"),
        "authority": "exact_construction_parameterization_executor",
        "claim_boundary": (
            "constraint_candidate_only_target_adapter_replay_still_required"
            if kind == "candidate"
            else "construction_constraint_or_backend_residual_only"
        ),
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _finalize_execution_receipt(
    frozen: Mapping[str, Any],
    core: Mapping[str, Any],
) -> dict[str, Any]:
    """Bound execution-envelope amplification and project it to one residual."""

    maximum = int(frozen["resource_limits"]["max_execution_receipt_bytes"])
    signed = {**core, "receipt_sha256": content_hash(core)}
    attempted_bytes = _canonical_json_size(signed)
    if attempted_bytes <= maximum:
        return validate_construction_parameterization_execution(signed)
    residual = _residual(
        frozen,
        parameter_id="",
        assignment=None,
        artifact_sha256="",
        kind="backend_unavailable",
        reason_code="construction_execution_receipt_byte_limit_exhausted",
        backend_check_id="",
        observed={
            "attempted_receipt_bytes": attempted_bytes,
            "max_execution_receipt_bytes": maximum,
        },
    )
    fallback_core = {
        **dict(core),
        "status": "backend_unavailable",
        "residuals": [residual],
        "coverage_complete": False,
    }
    fallback = {
        **fallback_core,
        "receipt_sha256": content_hash(fallback_core),
    }
    return validate_construction_parameterization_execution(
        _bounded_receipt(
            fallback,
            maximum=maximum,
            context="construction_execution_receipt",
        )
    )


def execute_construction_parameterization(
    parameterization: Mapping[str, Any],
    *,
    witness_schema: Mapping[str, Any],
) -> AdmittedConstructionExecution:
    """Execute one construction problem under the closed residual algebra."""

    frozen = admit_construction_parameterization(parameterization)
    try:
        Draft202012Validator.check_schema(dict(witness_schema))
        validator = Draft202012Validator(dict(witness_schema))
    except SchemaError as exc:
        raise ConstructionParameterizationError(
            "construction target witness schema is invalid"
        ) from exc
    certified_assignments = dict(frozen.assignment_domain)
    materialization_budget = _MaterializationBudget(
        frozen["resource_limits"]
    )

    def materialize_checked(
        assignment: Mapping[str, Any],
    ) -> dict[str, Any]:
        artifact = _materialize_frozen_parameter_artifact(
            frozen,
            assignment,
            validator=validator,
            materialization_budget=materialization_budget,
            certified_assignments=certified_assignments,
        )
        return artifact

    try:
        raw_result = _call_construction_backend(
            adapter_id=str(frozen["adapter_id"]),
            backend=frozen["backend"],
            operation="execute_problem",
            parameter_space=frozen["parameter_space"],
            backend_problem=frozen["backend_problem"],
            symmetry_policy=frozen["symmetry_policy"],
            resource_limits=frozen["resource_limits"],
            witness_schema=dict(witness_schema),
            materialize=materialize_checked,
            resource_error=ConstructionResourceCeilingExceeded,
        )
    except (
        ConstructionResourceCeilingExceeded,
        ConstructionBackendCapabilityUnavailable,
    ) as exc:
        _annotate_assignment_progress(
            exc,
            certified=len(certified_assignments),
            attempted=materialization_budget.attempted_artifacts,
        )
        raise
    backend_result = _json_data(
        raw_result, context="construction backend execution"
    )
    required_backend_fields = {
        "status", "expected_parameter_count", "residuals",
        "coverage_complete", "resource_usage",
    }
    if (
        not isinstance(backend_result, dict)
        or set(backend_result) != required_backend_fields
        or backend_result.get("status") not in {
            "completed", "backend_unavailable",
        }
        or type(backend_result.get("expected_parameter_count")) is not int
        or backend_result["expected_parameter_count"] < 1
        or type(backend_result.get("coverage_complete")) is not bool
        or not isinstance(backend_result.get("residuals"), list)
        or not backend_result["residuals"]
    ):
        raise ConstructionParameterizationError(
            "construction backend returned an invalid execution projection"
        )
    backend_usage = _resource_usage(backend_result.get("resource_usage"))
    if "host_materialized_artifact_bytes" in backend_usage:
        raise ConstructionParameterizationError(
            "construction backend claimed host-owned resource usage"
        )
    if backend_result["expected_parameter_count"] != len(
        certified_assignments
    ):
        raise ConstructionParameterizationError(
            "construction backend changed the certified assignment count"
        )
    residuals: list[dict[str, Any]] = []
    seen_parameter_ids: set[str] = set()
    for raw in backend_result["residuals"]:
        if not isinstance(raw, Mapping) or set(raw) != {
            "parameter_id", "assignment", "artifact_sha256", "kind",
            "reason_code", "backend_check_id", "observed",
        }:
            raise ConstructionParameterizationError(
                "construction backend residual projection is malformed"
            )
        assignment = raw["assignment"]
        parameter_id = str(raw["parameter_id"])
        if assignment is None:
            if parameter_id or raw["kind"] != "backend_unavailable":
                raise ConstructionParameterizationError(
                    "construction backend emitted an unauthorised global residual"
                )
        else:
            if not isinstance(assignment, Mapping):
                raise ConstructionParameterizationError(
                    "construction backend residual assignment is malformed"
                )
            frozen_assignment = _json_data(
                assignment,
                context="construction backend residual assignment",
            )
            expected_parameter_id = "assignment:" + content_hash(
                frozen_assignment
            )
            certified_assignment = certified_assignments.get(
                expected_parameter_id
            )
            if (
                parameter_id != expected_parameter_id
                or not isinstance(certified_assignment, Mapping)
                or frozen_assignment != dict(certified_assignment)
            ):
                raise ConstructionParameterizationError(
                    "construction backend residual lacks assignment authority"
                )
            if parameter_id in seen_parameter_ids:
                raise ConstructionParameterizationError(
                    "construction backend repeated a certified assignment"
                )
            seen_parameter_ids.add(parameter_id)
            if raw["kind"] == "candidate":
                artifact = materialize_checked(frozen_assignment)
                if str(raw["artifact_sha256"]) != content_hash(artifact):
                    raise ConstructionParameterizationError(
                        "construction backend candidate artifact digest mismatch"
                    )
        residuals.append(
            _residual(
                frozen,
                parameter_id=parameter_id,
                assignment=assignment,
                artifact_sha256=str(raw["artifact_sha256"]),
                kind=str(raw["kind"]),
                reason_code=str(raw["reason_code"]),
                backend_check_id=str(raw["backend_check_id"]),
                observed=raw["observed"],
            )
        )
    if backend_result["coverage_complete"] and seen_parameter_ids != set(
        certified_assignments
    ):
        raise ConstructionParameterizationError(
            "construction backend claimed incomplete assignment coverage"
        )
    usage_with_host = {
        **backend_usage,
        "host_materialized_artifact_bytes": (
            materialization_budget.materialized_artifact_bytes
        ),
    }
    usage_with_host = {
        field: usage_with_host[field] for field in sorted(usage_with_host)
    }
    core = {
        "schema": CONSTRUCTION_EXECUTION_SCHEMA,
        "campaign_id": frozen["campaign_id"],
        "request_id": frozen["request_id"],
        "gap_id": frozen["gap_id"],
        "context_hash": frozen["context_hash"],
        "context_epoch": frozen["context_epoch"],
        "adapter_id": frozen["adapter_id"],
        "target_interface_sha256": frozen["target_interface_sha256"],
        "parameterization_sha256": frozen["receipt_sha256"],
        "backend_problem_sha256": content_hash(frozen["backend_problem"]),
        "backend": dict(frozen["backend"]),
        "backend_sha256": content_hash(frozen["backend"]),
        "status": backend_result["status"],
        "expected_parameter_count": backend_result["expected_parameter_count"],
        "residuals": residuals,
        "coverage_complete": backend_result["coverage_complete"],
        "resource_usage": usage_with_host,
        "provider_calls": 0,
        "authority": "exact_construction_parameterization_executor",
        "claim_scope": CONSTRUCTION_PARAMETERIZATION_CLAIM_SCOPE,
    }
    receipt = _finalize_execution_receipt(frozen, core)
    return _mint_admitted_execution(
        receipt,
        parameterization=frozen,
        witness_schema=witness_schema,
    )

def validate_construction_parameterization_execution(
    value: Mapping[str, Any],
    *,
    parameterization: Mapping[str, Any] | None = None,
    witness_schema: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate execution bytes and joins without invoking a backend.

    A successful parse is not semantic admission.  Persistent executions must
    pass :func:`admit_persisted_construction_execution` before consumption.
    """

    original = value
    row = _json_data(
        value.to_json()
        if isinstance(value, AdmittedConstructionExecution)
        else value,
        context="construction parameterization execution",
    )
    required = {
        "schema",
        "campaign_id",
        "request_id",
        "gap_id",
        "context_hash",
        "context_epoch",
        "adapter_id",
        "target_interface_sha256",
        "parameterization_sha256",
        "backend_problem_sha256",
        "backend",
        "backend_sha256",
        "status",
        "expected_parameter_count",
        "residuals",
        "coverage_complete",
        "resource_usage",
        "provider_calls",
        "authority",
        "claim_scope",
        "receipt_sha256",
    }
    if not isinstance(row, dict) or set(row) != required:
        raise ConstructionParameterizationError(
            "construction execution fields changed identity"
        )
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    if (
        row.get("schema") != CONSTRUCTION_EXECUTION_SCHEMA
        or row.get("receipt_sha256") != content_hash(core)
        or row.get("status") not in {"completed", "backend_unavailable"}
        or row.get("authority")
        != "exact_construction_parameterization_executor"
        or row.get("claim_scope") != CONSTRUCTION_PARAMETERIZATION_CLAIM_SCOPE
        or row.get("provider_calls") != 0
        or type(row.get("context_epoch")) is not int
        or type(row.get("expected_parameter_count")) is not int
        or int(row["expected_parameter_count"]) < 1
        or type(row.get("coverage_complete")) is not bool
        or row.get("backend_sha256") != content_hash(row.get("backend"))
    ):
        raise ConstructionParameterizationError(
            "construction execution identity is invalid"
        )
    for field in (
        "target_interface_sha256",
        "parameterization_sha256",
        "backend_problem_sha256",
        "backend_sha256",
    ):
        _digest(row[field], context=field)
    usage = _resource_usage(row.get("resource_usage"))
    residuals = row.get("residuals")
    if not isinstance(residuals, list) or not residuals:
        raise ConstructionParameterizationError(
            "construction execution carries no residuals"
        )
    parameter_ids: list[str] = []
    for residual in residuals:
        if not isinstance(residual, Mapping):
            raise ConstructionParameterizationError(
                "construction residual is malformed"
            )
        residual_core = {
            key: item for key, item in residual.items() if key != "receipt_sha256"
        }
        if (
            residual.get("schema") != CONSTRUCTION_RESIDUAL_SCHEMA
            or residual.get("receipt_sha256") != content_hash(residual_core)
            or residual.get("kind") not in _RESIDUAL_KINDS
            or residual.get("authority")
            != "exact_construction_parameterization_executor"
            or residual.get("campaign_id") != row.get("campaign_id")
            or residual.get("request_id") != row.get("request_id")
            or residual.get("gap_id") != row.get("gap_id")
            or residual.get("context_hash") != row.get("context_hash")
            or residual.get("context_epoch") != row.get("context_epoch")
            or residual.get("adapter_id") != row.get("adapter_id")
            or residual.get("target_interface_sha256")
            != row.get("target_interface_sha256")
            or residual.get("parameterization_sha256")
            != row.get("parameterization_sha256")
            or residual.get("backend_problem_sha256")
            != row.get("backend_problem_sha256")
            or residual.get("backend_sha256") != row.get("backend_sha256")
            or not str(residual.get("reason_code") or "")
        ):
            raise ConstructionParameterizationError(
                "construction residual crossed execution identity"
            )
        assignment = residual.get("assignment")
        if assignment is None:
            if residual.get("assignment_sha256") != "" or residual.get(
                "parameter_id"
            ) != "":
                raise ConstructionParameterizationError(
                    "global backend residual carries assignment identity"
                )
        else:
            if (
                not isinstance(assignment, Mapping)
                or residual.get("assignment_sha256") != content_hash(assignment)
                or residual.get("parameter_id")
                != "assignment:" + content_hash(assignment)
            ):
                raise ConstructionParameterizationError(
                    "construction residual assignment digest mismatch"
                )
            parameter_ids.append(str(residual["parameter_id"]))
        artifact_sha = str(residual.get("artifact_sha256") or "")
        if artifact_sha:
            _digest(artifact_sha, context="construction residual artifact")
        if residual.get("kind") == "candidate" and not artifact_sha:
            raise ConstructionParameterizationError(
                "construction candidate residual lacks artifact identity"
            )
    if row["coverage_complete"] is True and (
        len(parameter_ids) != row["expected_parameter_count"]
        or len(parameter_ids) != len(set(parameter_ids))
    ):
        raise ConstructionParameterizationError(
            "construction execution parameter coverage is incomplete"
        )
    if (row["status"] == "backend_unavailable") != any(
        residual["kind"] == "backend_unavailable" for residual in residuals
    ):
        raise ConstructionParameterizationError(
            "construction execution backend status is inconsistent"
        )
    if parameterization is not None:
        frozen = validate_construction_parameterization(parameterization)
        if (
            row["campaign_id"] != frozen["campaign_id"]
            or row["request_id"] != frozen["request_id"]
            or row["gap_id"] != frozen["gap_id"]
            or row["context_hash"] != frozen["context_hash"]
            or row["context_epoch"] != frozen["context_epoch"]
            or row["adapter_id"] != frozen["adapter_id"]
            or row["target_interface_sha256"]
            != frozen["target_interface_sha256"]
            or row["parameterization_sha256"] != frozen["receipt_sha256"]
            or row["backend_problem_sha256"]
            != content_hash(frozen["backend_problem"])
        ):
            raise ConstructionParameterizationError(
                "construction execution crossed its parameterization"
            )
        if isinstance(frozen, AdmittedConstructionParameterization):
            certified_assignments = dict(frozen.assignment_domain)
            if row["expected_parameter_count"] != len(certified_assignments):
                raise ConstructionParameterizationError(
                    "construction execution changed certified parameter count"
                )
            joined: set[str] = set()
            for residual in residuals:
                assignment = residual.get("assignment")
                if assignment is None:
                    continue
                parameter_id = str(residual["parameter_id"])
                if (
                    parameter_id not in certified_assignments
                    or dict(assignment) != certified_assignments[parameter_id]
                    or parameter_id in joined
                ):
                    raise ConstructionParameterizationError(
                        "construction execution residual lacks certified assignment authority"
                    )
                joined.add(parameter_id)
            if row["coverage_complete"] and joined != set(certified_assignments):
                raise ConstructionParameterizationError(
                    "construction execution does not cover its certified parameters"
                )
    if (
        isinstance(original, AdmittedConstructionExecution)
        and dict(original) == row
    ):
        return original
    return row


def _mint_admitted_execution(
    value: Mapping[str, Any],
    *,
    parameterization: AdmittedConstructionParameterization,
    witness_schema: Mapping[str, Any],
) -> AdmittedConstructionExecution:
    row = validate_construction_parameterization_execution(
        value,
        parameterization=parameterization,
        witness_schema=witness_schema,
    )
    return AdmittedConstructionExecution(
        row,
        _token=_ADMISSION_TOKEN,
        parameterization=parameterization,
        witness_schema_sha256=content_hash(dict(witness_schema)),
    )


def _validate_admitted_execution(
    value: AdmittedConstructionExecution,
    *,
    parameterization: AdmittedConstructionParameterization,
    witness_schema: Mapping[str, Any],
) -> AdmittedConstructionExecution:
    row = validate_construction_parameterization_execution(
        value,
        parameterization=parameterization,
        witness_schema=witness_schema,
    )
    same_parameterization = (
        value.admitted_parameterization is parameterization
        or value.admitted_parameterization.assignment_domain_receipt
        == parameterization.assignment_domain_receipt
    )
    if (
        row is not value
        or not same_parameterization
        or value._witness_schema_sha256 != content_hash(dict(witness_schema))
    ):
        raise ConstructionParameterizationError(
            "construction execution admission changed identity"
        )
    return value


def admit_persisted_construction_execution(
    parameterization: Mapping[str, Any],
    execution: Mapping[str, Any],
    *,
    witness_schema: Mapping[str, Any],
) -> AdmittedConstructionExecution:
    """Reexecute cold bytes once and mint authority only on exact equality."""

    admitted = admit_construction_parameterization(parameterization)
    if isinstance(execution, AdmittedConstructionExecution):
        return _validate_admitted_execution(
            execution,
            parameterization=admitted,
            witness_schema=witness_schema,
        )
    persisted = validate_construction_parameterization_execution(
        execution,
        parameterization=admitted,
        witness_schema=witness_schema,
    )
    replayed = execute_construction_parameterization(
        admitted,
        witness_schema=witness_schema,
    )
    if dict(persisted) != dict(replayed):
        raise ConstructionParameterizationError(
            "persisted construction execution failed semantic replay"
        )
    return replayed



__all__ = [
    "CONSTRUCTION_EXECUTION_SCHEMA",
    "CONSTRUCTION_PARAMETERIZATION_CLAIM_SCOPE",
    "CONSTRUCTION_PARAMETERIZATION_SCHEMA",
    "CONSTRUCTION_RESIDUAL_SCHEMA",
    "SAFE_ARTIFACT_TEMPLATE_SCHEMA",
    "AdmittedConstructionExecution",
    "AdmittedConstructionParameterization",
    "ConstructionParameterizationError",
    "ConstructionBackendCapabilityUnavailable",
    "ConstructionResourceCeilingExceeded",
    "admit_construction_parameterization",
    "admit_persisted_construction_execution",
    "build_construction_parameterization",
    "certified_construction_parameter_count",
    "construction_parameterization_authoring_contract",
    "enumerate_parameter_assignments",
    "execute_construction_parameterization",
    "materialize_construction_candidates",
    "materialize_parameter_artifact",
    "validate_construction_parameterization",
    "validate_construction_parameterization_execution",
    "replay_parameter_artifact_schema",
]
