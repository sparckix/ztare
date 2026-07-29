"""Field-neutral finite assignment backend for inert JSON templates."""
from __future__ import annotations

import itertools
import json
import re
from typing import Any, Callable, Mapping

from ztare.leanmill.construction_wire_projection import (
    project_explicit_assignment_wire_bytes,
)
from ztare.leanmill.theory_ir import content_hash


CAPABILITY_ID = "explicit_finite_json_assignment_enumerator.v1"
CONTRACT = {
    "parameter_domain": "bounded_canonical_json_scalars",
    "problem_fragment": "accept_all",
    "ordering": "lexicographic_parameter_order",
    "failure_mode": "typed_residual",
}
PROBLEM_SCHEMA = "leanmill.accept_all_construction_backend_problem.v1"
_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")
_MAX_ATOM_BYTES = 65_536
_MAX_INTEGER_BITS = 4_096


def _descriptor(value: Mapping[str, Any]) -> dict[str, Any]:
    adapter_id = str(value.get("adapter_id") or "")
    expected = {
        "adapter_id": str(adapter_id),
        "capability_id": CAPABILITY_ID,
        "contract_sha256": content_hash(CONTRACT),
    }
    if dict(value) != expected:
        raise ValueError("explicit finite backend descriptor crossed its contract")
    return expected


def _space(
    value: Any,
    *,
    limits: Mapping[str, int],
    json_data: Callable[..., Any],
) -> tuple[dict[str, Any], list[str], dict[str, str], int]:
    row = json_data(value, context="explicit finite parameter space")
    if (
        not isinstance(row, dict)
        or set(row) != {"schema", "variables"}
        or row.get("schema") != "leanmill.explicit_finite_parameter_space.v1"
        or not isinstance(row.get("variables"), list)
        or not row["variables"]
        or len(row["variables"]) > 64
    ):
        raise ValueError("explicit finite parameter space is malformed")
    variables: list[dict[str, Any]] = []
    for raw in row["variables"]:
        if not isinstance(raw, Mapping) or set(raw) != {
            "parameter_id", "sort", "domain",
        }:
            raise ValueError("explicit finite variable is malformed")
        parameter_id = str(raw.get("parameter_id") or "")
        sort = str(raw.get("sort") or "")
        domain = raw.get("domain")
        if (
            _ID_RE.fullmatch(parameter_id) is None
            or sort not in {"boolean", "json_atom"}
            or not isinstance(domain, list)
            or not domain
            or len(domain) > 256
        ):
            raise ValueError("explicit finite variable crossed its contract")
        if sort == "boolean":
            if any(type(item) is not bool for item in domain):
                raise ValueError("Boolean domain contains a non-Boolean")
            canonical = sorted(domain)
        else:
            if any(
                type(item) not in {str, int, bool} and item is not None
                for item in domain
            ):
                raise ValueError("JSON-scalar domain contains a container")
            if any(
                (type(item) is int and abs(item).bit_length() > _MAX_INTEGER_BITS)
                or len(
                    json.dumps(
                        item,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=True,
                    ).encode("utf-8")
                )
                > _MAX_ATOM_BYTES
                for item in domain
            ):
                raise ValueError("JSON-scalar domain exceeds its wire ceiling")
            canonical = sorted(
                domain,
                key=lambda item: json.dumps(
                    item, sort_keys=True, separators=(",", ":")
                ),
            )
        if domain != canonical or len(domain) != len(
            {json.dumps(item, sort_keys=True) for item in domain}
        ):
            raise ValueError("explicit finite domain is not canonical")
        variables.append({
            "parameter_id": parameter_id,
            "sort": sort,
            "domain": list(canonical),
        })
    ids = [row["parameter_id"] for row in variables]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise ValueError("explicit finite parameter ids are not canonical")
    cardinality = 1
    for variable in variables:
        cardinality *= len(variable["domain"])
    if cardinality > int(limits["max_assignments"]):
        raise ValueError("explicit finite parameter count exceeds its ceiling")
    return (
        {"schema": row["schema"], "variables": variables},
        ids,
        {variable["parameter_id"]: variable["sort"] for variable in variables},
        cardinality,
    )


def build_problem(*, parameter_ids: list[str]) -> dict[str, Any]:
    core = {
        "schema": PROBLEM_SCHEMA,
        "parameter_ids": list(parameter_ids),
        "predicate": "accept_all",
        "claim_boundary": "assignment_enumeration_only_no_target_verdict",
    }
    return {**core, "problem_sha256": content_hash(core)}


def _problem(value: Any, *, parameter_ids: list[str], json_data) -> dict[str, Any]:
    row = json_data(value, context="explicit finite backend problem")
    required = {
        "schema", "parameter_ids", "predicate", "claim_boundary",
        "problem_sha256",
    }
    core = {
        key: item for key, item in row.items()
        if key != "problem_sha256"
    } if isinstance(row, dict) else {}
    if (
        not isinstance(row, dict)
        or set(row) != required
        or row.get("schema") != PROBLEM_SCHEMA
        or row.get("parameter_ids") != parameter_ids
        or row.get("predicate") != "accept_all"
        or row.get("claim_boundary")
        != "assignment_enumeration_only_no_target_verdict"
        or row.get("problem_sha256") != content_hash(core)
    ):
        raise ValueError("explicit finite backend problem changed identity")
    return row


def validate_problem(
    *,
    backend: Mapping[str, Any],
    parameter_space: Any,
    backend_problem: Any,
    resource_limits: Mapping[str, int],
    json_data,
) -> dict[str, Any]:
    descriptor = _descriptor(backend)
    space, ids, sorts, cardinality = _space(
        parameter_space, limits=resource_limits, json_data=json_data
    )
    problem = _problem(
        backend_problem, parameter_ids=ids, json_data=json_data
    )
    return {
        "backend": descriptor,
        "parameter_space": space,
        "backend_problem": problem,
        "parameter_ids": ids,
        "parameter_sorts": sorts,
        "cardinality": cardinality,
        "projected_assignment_wire_bytes": (
            project_explicit_assignment_wire_bytes(
                parameter_ids=ids,
                domains=[row["domain"] for row in space["variables"]],
            )
        ),
    }


def enumerate_assignments(
    *,
    backend: Mapping[str, Any],
    parameter_space: Mapping[str, Any],
) -> tuple[tuple[str, dict[str, Any]], ...]:
    _descriptor(backend)
    variables = parameter_space["variables"]
    rows = []
    for values in itertools.product(*(row["domain"] for row in variables)):
        assignment = {
            row["parameter_id"]: value
            for row, value in zip(variables, values, strict=True)
        }
        rows.append(("assignment:" + content_hash(assignment), assignment))
    return tuple(rows)


def execute_problem(
    *,
    backend: Mapping[str, Any],
    parameter_space: Mapping[str, Any],
    backend_problem: Mapping[str, Any],
    symmetry_policy: Mapping[str, Any],
    resource_limits: Mapping[str, int],
    witness_schema: Mapping[str, Any],
    materialize,
    resource_error,
) -> dict[str, Any]:
    del backend_problem, witness_schema
    assignments = enumerate_assignments(
        backend=backend,
        parameter_space=parameter_space,
    )
    if symmetry_policy.get("kind") != "none":
        return {
            "status": "backend_unavailable",
            "expected_parameter_count": len(assignments),
            "residuals": [{
                "parameter_id": "",
                "assignment": None,
                "artifact_sha256": "",
                "kind": "backend_unavailable",
                "reason_code": "reviewed_explicit_quotient_executor_absent",
                "backend_check_id": "",
                "observed": {
                    "requested_symmetry_kind": symmetry_policy.get("kind")
                },
            }],
            "coverage_complete": False,
            "resource_usage": {
                "constraint_evaluations": 0,
                "exact_operations": 0,
                "materialized_artifact_bytes": 0,
            },
        }
    residuals = []
    artifact_bytes = 0
    for parameter_id, assignment in assignments:
        artifact = materialize(assignment)
        amount = len(json.dumps(
            artifact,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8"))
        if artifact_bytes + amount > int(
            resource_limits["max_materialized_artifact_bytes"]
        ):
            raise resource_error(
                "materialized_artifact_byte_limit_exhausted",
                resource="materialized_artifact_bytes",
                observed=artifact_bytes + amount,
                ceiling=int(
                    resource_limits["max_materialized_artifact_bytes"]
                ),
                counters={"materialized_artifact_bytes": artifact_bytes},
            )
        artifact_bytes += amount
        residuals.append({
            "parameter_id": parameter_id,
            "assignment": assignment,
            "artifact_sha256": content_hash(artifact),
            "kind": "candidate",
            "reason_code": "constraints_satisfied",
            "backend_check_id": "",
            "observed": {"evaluated_constraint_count": 0},
        })
    return {
        "status": "completed",
        "expected_parameter_count": len(assignments),
        "residuals": residuals,
        "coverage_complete": True,
        "resource_usage": {
            "constraint_evaluations": 0,
            "exact_operations": 0,
            "materialized_artifact_bytes": artifact_bytes,
        },
    }


def capability(*, operation: str, **kwargs: Any) -> Any:
    if operation == "authoring_contract":
        backend = kwargs.get("backend")
        _descriptor(backend)
        return {
            "backend_capability": dict(backend),
            "parameter_space_schema": (
                "leanmill.explicit_finite_parameter_space.v1"
            ),
            "allowed_parameter_sorts": ["boolean", "json_atom"],
            "backend_problem_schema": PROBLEM_SCHEMA,
            "backend_problem_fragment": "accept_all",
            "backend_resource_ceilings": {},
            "availability": "available",
        }
    if operation == "validate_problem":
        return validate_problem(**kwargs)
    if operation == "enumerate_assignments":
        return enumerate_assignments(**kwargs)
    if operation == "execute_problem":
        return execute_problem(**kwargs)
    raise ValueError("unknown explicit finite backend operation")


__all__ = [
    "CAPABILITY_ID", "CONTRACT", "PROBLEM_SCHEMA", "build_problem", "capability",
]
