"""Exact allocation-free wire projections for construction protocol data."""
from __future__ import annotations

import json
import math
from typing import Any, Mapping, Sequence


def canonical_json_wire_bytes(value: Any) -> int:
    """Return the byte length of LeanMill's canonical JSON encoding."""

    return len(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    )


def project_explicit_assignment_wire_bytes(
    *,
    parameter_ids: Sequence[str],
    domains: Sequence[Sequence[Any]],
) -> int:
    """Project all canonical assignment objects plus their content ids.

    The formula is additive over finite Cartesian coordinates and therefore
    does not materialize a product.  It exactly matches the canonical
    ``[{"assignment": ..., "parameter_id": ...}, ...]`` admission snapshot.
    """

    ids = list(parameter_ids)
    domain_rows = [list(domain) for domain in domains]
    if (
        not ids
        or len(ids) != len(domain_rows)
        or any(type(parameter_id) is not str or not parameter_id for parameter_id in ids)
        or any(not domain for domain in domain_rows)
    ):
        raise ValueError("assignment wire projection inputs are malformed")
    cardinality = math.prod(len(domain) for domain in domain_rows)
    fixed_object_bytes = 2 + max(0, len(ids) - 1)
    fixed_object_bytes += sum(
        canonical_json_wire_bytes(parameter_id) + 1
        for parameter_id in ids
    )
    assignment_bytes = cardinality * fixed_object_bytes
    for domain in domain_rows:
        repetitions = cardinality // len(domain)
        assignment_bytes += repetitions * sum(
            canonical_json_wire_bytes(value) for value in domain
        )
    snapshot_bytes = 2 + max(0, cardinality - 1)
    row_fixed_bytes = (
        2
        + 1
        + canonical_json_wire_bytes("assignment")
        + 1
        + canonical_json_wire_bytes("parameter_id")
        + 1
        + canonical_json_wire_bytes("assignment:" + "0" * 64)
    )
    return snapshot_bytes + assignment_bytes + cardinality * row_fixed_bytes


def project_rendered_template_wire_bytes(
    template: Any,
    assignment: Mapping[str, Any],
    *,
    max_bytes: int | None = None,
) -> int:
    """Project canonical rendered JSON bytes without expanding the template."""

    if max_bytes is not None and (type(max_bytes) is not int or max_bytes < 0):
        raise ValueError("rendered template wire ceiling is malformed")
    stack: list[tuple[Any, int]] = [(template, 0)]
    total = 0
    parameter_wire_bytes: dict[str, int] = {}

    def add(amount: int) -> bool:
        nonlocal total
        total += amount
        return max_bytes is not None and total > max_bytes

    while stack:
        value, depth = stack.pop()
        if depth > 128:
            raise ValueError("artifact template is too deep")
        if isinstance(value, Mapping):
            if set(value) == {"$parameter"}:
                parameter_id = value.get("$parameter")
                if type(parameter_id) is not str or parameter_id not in assignment:
                    raise ValueError(
                        "artifact template references an unknown assignment parameter"
                    )
                amount = parameter_wire_bytes.get(parameter_id)
                if amount is None:
                    amount = canonical_json_wire_bytes(assignment[parameter_id])
                    parameter_wire_bytes[parameter_id] = amount
                if add(amount):
                    return total
                continue
            if add(2 + max(0, len(value) - 1)):
                return total
            for key, item in value.items():
                if type(key) is not str:
                    raise ValueError("artifact template object key is not a string")
                if add(canonical_json_wire_bytes(key) + 1):
                    return total
                stack.append((item, depth + 1))
        elif isinstance(value, list):
            if add(2 + max(0, len(value) - 1)):
                return total
            stack.extend((item, depth + 1) for item in value)
        elif type(value) in {str, int, bool} or value is None:
            if add(canonical_json_wire_bytes(value)):
                return total
        else:
            raise ValueError("artifact template contains a non-JSON value")
    return total


__all__ = [
    "canonical_json_wire_bytes",
    "project_explicit_assignment_wire_bytes",
    "project_rendered_template_wire_bytes",
]
