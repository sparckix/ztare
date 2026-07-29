"""Prime-field scouting for exact rational construction assignments.

The persistent construction object remains a rational ansatz.  This reviewed
adapter capability reduces its finite parameter domain and exact polynomial
constraints modulo one named prime, then emits only directionally valid
feedback:

* a failed modular equality refutes the same rational assignment;
* every other nonterminal outcome still requires exact rational replay.

The common construction protocol sees this module only through its registered
capability contract.  It does not parse field elements or branch on fields.
"""
from __future__ import annotations

from fractions import Fraction
import itertools
import json
from typing import Any, Callable, Mapping, Sequence

from ztare.leanmill.adapters.construction_backends import (
    finite_rational_polynomial as rational_backend,
)
from ztare.leanmill.construction_wire_projection import (
    project_explicit_assignment_wire_bytes,
)
from ztare.leanmill.data_only_json import strict_json_data
from ztare.leanmill.theory_ir import content_hash


CAPABILITY_ID = "finite_prime_field_reduction_enumerator.v1"
MAP_REDUCTION_VERIFIER_CAPABILITY = (
    "rational_polynomial_map_prime_reduction_verifier"
)
CONTRACT = {
    "source_arithmetic": "Q",
    "scouting_arithmetic": "prime_field",
    "parameter_domain": "explicit_finite_rational_assignments",
    "constraint_fragment": "polynomial_equalities_and_disequalities",
    "transport": "one_way_relation_sensitive_reduction",
    "failure_mode": "typed_residual",
}
FIELD_SCHEMA = "leanmill.prime_field_descriptor.v1"
PROBLEM_SCHEMA = "leanmill.prime_field_reduction_problem.v1"
REDUCTION_RECEIPT_SCHEMA = "leanmill.prime_field_reduction_receipt.v1"
MAP_REDUCTION_VERIFICATION_SCHEMA = (
    "leanmill.rational_polynomial_map_prime_reduction_verification.v1"
)

_MAX_PRIME = (1 << 64) - 1
_TRANSPORT_POLICY = {
    "equality_failure": "refutes_same_rational_assignment",
    "equality_survival": "modular_only_requires_exact_rational_replay",
    "disequality_survival": "supports_same_rational_disequality",
    "disequality_failure": "inconclusive_requires_exact_rational_replay",
    "reverse_field_verdict": "forbidden",
}


def _is_prime_64(value: int) -> bool:
    """Deterministic Miller--Rabin for unsigned 64-bit integers."""

    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    if value in small:
        return True
    if any(value % prime == 0 for prime in small):
        return False
    odd = value - 1
    shifts = 0
    while odd % 2 == 0:
        shifts += 1
        odd //= 2
    # This base set is deterministic for n < 2^64.
    for base in (2, 325, 9_375, 28_178, 450_775, 9_780_504, 1_795_265_022):
        if base % value == 0:
            continue
        witness = pow(base, odd, value)
        if witness in {1, value - 1}:
            continue
        for _ in range(shifts - 1):
            witness = witness * witness % value
            if witness == value - 1:
                break
        else:
            return False
    return True


def prime_field_descriptor(characteristic: int) -> dict[str, Any]:
    if (
        type(characteristic) is not int
        or characteristic > _MAX_PRIME
        or not _is_prime_64(characteristic)
    ):
        raise ValueError("prime-field characteristic is not a reviewed prime")
    return {
        "schema": FIELD_SCHEMA,
        "kind": "prime_field",
        "characteristic": characteristic,
        "element_wire": "least_nonnegative_residue",
    }


def _descriptor(value: Mapping[str, Any]) -> dict[str, Any]:
    adapter_id = str(value.get("adapter_id") or "")
    expected = {
        "adapter_id": adapter_id,
        "capability_id": CAPABILITY_ID,
        "contract_sha256": content_hash(CONTRACT),
    }
    if not adapter_id or dict(value) != expected:
        raise ValueError("prime-field backend descriptor crossed its contract")
    return expected


def _parameter_ids(value: Any) -> list[str]:
    if not isinstance(value, Mapping) or not isinstance(
        value.get("variables"), list
    ):
        raise ValueError("prime-field parameter space is malformed")
    ids = [
        str(row.get("parameter_id") or "")
        for row in value["variables"]
        if isinstance(row, Mapping)
    ]
    if len(ids) != len(value["variables"]):
        raise ValueError("prime-field parameter variables are malformed")
    return ids


def _normalize_guards(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, (list, tuple)) or len(value) > 1_024:
        raise ValueError("prime-field reduction guards are malformed")
    rows: list[dict[str, str]] = []
    for raw in value:
        if not isinstance(raw, Mapping) or set(raw) != {"guard_id", "value"}:
            raise ValueError("prime-field reduction guard fields changed identity")
        guard_id = str(raw.get("guard_id") or "")
        if not guard_id or len(guard_id) > 128:
            raise ValueError("prime-field reduction guard id is malformed")
        rational = rational_backend.parse_canonical_rational(raw.get("value"))
        if rational == 0:
            raise ValueError("prime-field reduction guard must be nonzero over Q")
        rows.append({
            "guard_id": guard_id,
            "value": rational_backend.format_canonical_rational(rational),
        })
    if rows != sorted(rows, key=lambda row: row["guard_id"]) or len(
        {row["guard_id"] for row in rows}
    ) != len(rows):
        raise ValueError("prime-field reduction guards are not canonical")
    return rows


def _constraint_rationals(
    constraint_system: Mapping[str, Any],
) -> tuple[Fraction, ...]:
    values: list[Fraction] = []
    for constraint in constraint_system["constraints"]:
        for side in ("left", "right"):
            values.extend(
                rational_backend.parse_canonical_rational(term["coefficient"])
                for term in constraint[side]["terms"]
            )
    return tuple(values)


def _domain_rationals(parameter_space: Mapping[str, Any]) -> tuple[Fraction, ...]:
    values: list[Fraction] = []
    for variable in parameter_space["variables"]:
        if variable["sort"] == "rational":
            values.extend(
                rational_backend.parse_canonical_rational(item)
                for item in variable["domain"]
            )
    return tuple(values)


def _reduce(value: Fraction, characteristic: int) -> int:
    frozen = Fraction(value)
    denominator = frozen.denominator % characteristic
    if denominator == 0:
        raise ValueError("rational denominator is not invertible in target field")
    return (
        frozen.numerator % characteristic
    ) * pow(denominator, characteristic - 2, characteristic) % characteristic


def _reduction_receipt(
    *,
    field: Mapping[str, Any],
    parameter_space: Mapping[str, Any],
    source_constraint_system: Mapping[str, Any],
    reduction_guards: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    characteristic = int(field["characteristic"])
    rationals = (
        *_domain_rationals(parameter_space),
        *_constraint_rationals(source_constraint_system),
        *(
            rational_backend.parse_canonical_rational(row["value"])
            for row in reduction_guards
        ),
    )
    denominators = sorted({value.denominator for value in rationals})
    exclusions: list[dict[str, str]] = [
        {
            "kind": "noninvertible_denominator",
            "value": str(denominator),
        }
        for denominator in denominators
        if denominator % characteristic == 0
    ]
    reduced_guards: list[dict[str, str]] = []
    for row in reduction_guards:
        value = rational_backend.parse_canonical_rational(row["value"])
        target = ""
        if value.denominator % characteristic != 0:
            target = str(_reduce(value, characteristic))
            if target == "0":
                exclusions.append({
                    "kind": "required_nonzero_vanished",
                    "value": str(row["guard_id"]),
                })
        reduced_guards.append({
            "guard_id": str(row["guard_id"]),
            "source_value": str(row["value"]),
            "target_value": target,
        })
    exclusions = sorted(
        {json.dumps(row, sort_keys=True): row for row in exclusions}.values(),
        key=lambda row: (row["kind"], row["value"]),
    )
    core = {
        "schema": REDUCTION_RECEIPT_SCHEMA,
        "field": dict(field),
        "source_constraint_system_sha256": content_hash(
            source_constraint_system
        ),
        "parameter_space_sha256": content_hash(parameter_space),
        "checked_denominators": [str(value) for value in denominators],
        "reduction_guards": reduced_guards,
        "status": "excluded" if exclusions else "admissible",
        "exclusions": exclusions,
        "transport_policy": dict(_TRANSPORT_POLICY),
        "authority": "reviewed_prime_field_reduction_capability",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _normalized_problem(
    *,
    parameter_space: Any,
    source_constraint_system: Any,
    characteristic: int,
    reduction_guards: Any,
    resource_limits: Mapping[str, int],
    json_data: Callable[..., Any],
) -> tuple[dict[str, Any], dict[str, Any], list[str], dict[str, str], int]:
    raw_space = json_data(parameter_space, context="prime-field parameter space")
    parameter_ids = _parameter_ids(raw_space)
    source = rational_backend.validate_constraint_system(
        source_constraint_system,
        parameter_ids=parameter_ids,
        json_data=json_data,
    )
    if any(
        constraint["relation"] not in {"eq", "ne"}
        for constraint in source["constraints"]
    ):
        raise ValueError(
            "prime-field reduction supports only equality and disequality"
        )
    combined_limits = {
        **dict(resource_limits),
        **dict(source["resource_limits"]),
    }
    space, variables, cardinality = rational_backend.validate_parameter_space(
        raw_space,
        limits=combined_limits,
        json_data=json_data,
    )
    ids = [row["parameter_id"] for row in variables]
    sorts = {row["parameter_id"]: row["sort"] for row in variables}
    nonnumeric_indices = {
        index
        for index, parameter_id in enumerate(ids)
        if sorts[parameter_id] == "json_atom"
    }
    if any(
        term["exponents"][index] != 0
        for constraint in source["constraints"]
        for side in ("left", "right")
        for term in constraint[side]["terms"]
        for index in nonnumeric_indices
    ):
        raise ValueError("prime-field polynomials depend on JSON-atom parameters")
    field = prime_field_descriptor(characteristic)
    guards = _normalize_guards(reduction_guards)
    receipt = _reduction_receipt(
        field=field,
        parameter_space=space,
        source_constraint_system=source,
        reduction_guards=guards,
    )
    core = {
        "schema": PROBLEM_SCHEMA,
        "field": field,
        "source_constraint_system": source,
        "parameter_space_sha256": content_hash(space),
        "reduction_guards": guards,
        "reduction_receipt": receipt,
        "claim_boundary": (
            "modular_refutation_filter_only_no_characteristic_zero_"
            "certification"
        ),
    }
    problem = {**core, "problem_sha256": content_hash(core)}
    return problem, space, ids, sorts, cardinality


def build_prime_field_reduction_problem(
    *,
    parameter_space: Mapping[str, Any],
    source_constraint_system: Mapping[str, Any],
    characteristic: int,
    reduction_guards: Sequence[Mapping[str, Any]],
    resource_limits: Mapping[str, int],
) -> dict[str, Any]:
    """Build one content-bound modular sibling of a rational problem."""

    problem, _space, _ids, _sorts, _cardinality = _normalized_problem(
        parameter_space=parameter_space,
        source_constraint_system=source_constraint_system,
        characteristic=characteristic,
        reduction_guards=reduction_guards,
        resource_limits=resource_limits,
        json_data=strict_json_data,
    )
    return problem


def validate_problem(
    *,
    backend: Mapping[str, Any],
    parameter_space: Any,
    backend_problem: Any,
    resource_limits: Mapping[str, int],
    json_data: Callable[..., Any],
) -> dict[str, Any]:
    descriptor = _descriptor(backend)
    raw = json_data(backend_problem, context="prime-field backend problem")
    if not isinstance(raw, Mapping):
        raise ValueError("prime-field backend problem is malformed")
    field = raw.get("field")
    characteristic = (
        field.get("characteristic") if isinstance(field, Mapping) else None
    )
    expected, space, ids, sorts, cardinality = _normalized_problem(
        parameter_space=parameter_space,
        source_constraint_system=raw.get("source_constraint_system"),
        characteristic=characteristic,
        reduction_guards=raw.get("reduction_guards"),
        resource_limits=resource_limits,
        json_data=json_data,
    )
    if dict(raw) != expected:
        raise ValueError("prime-field backend problem is not canonical")
    return {
        "backend": descriptor,
        "parameter_space": space,
        "backend_problem": expected,
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
    rows: list[tuple[str, dict[str, Any]]] = []
    for values in itertools.product(*(row["domain"] for row in variables)):
        assignment = {
            row["parameter_id"]: value
            for row, value in zip(variables, values, strict=True)
        }
        rows.append(("assignment:" + content_hash(assignment), assignment))
    return tuple(rows)


class _FieldBudget:
    def __init__(
        self,
        *,
        common_limits: Mapping[str, int],
        source_limits: Mapping[str, int],
        resource_error: type[RuntimeError],
    ) -> None:
        self.max_constraints = int(source_limits["max_constraint_evaluations"])
        self.max_operations = int(source_limits["max_exact_operations"])
        self.max_artifact_bytes = int(
            common_limits["max_materialized_artifact_bytes"]
        )
        self.resource_error = resource_error
        self.constraint_evaluations = 0
        self.field_operations = 0
        self.materialized_artifact_bytes = 0

    def _raise(self, reason: str, resource: str, observed: int, ceiling: int):
        raise self.resource_error(
            reason,
            resource=resource,
            observed=observed,
            ceiling=ceiling,
            counters=self.usage(),
        )

    def operation(self, amount: int = 1) -> None:
        if self.field_operations + amount > self.max_operations:
            self._raise(
                "prime_field_operation_limit_exhausted",
                "field_operations",
                self.field_operations + amount,
                self.max_operations,
            )
        self.field_operations += amount

    def constraint(self) -> None:
        if self.constraint_evaluations + 1 > self.max_constraints:
            self._raise(
                "prime_field_constraint_limit_exhausted",
                "constraint_evaluations",
                self.constraint_evaluations + 1,
                self.max_constraints,
            )
        self.constraint_evaluations += 1

    def artifact(self, value: Mapping[str, Any]) -> None:
        amount = len(
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        )
        if self.materialized_artifact_bytes + amount > self.max_artifact_bytes:
            self._raise(
                "materialized_artifact_byte_limit_exhausted",
                "materialized_artifact_bytes",
                self.materialized_artifact_bytes + amount,
                self.max_artifact_bytes,
            )
        self.materialized_artifact_bytes += amount

    def usage(self) -> dict[str, int]:
        return {
            "constraint_evaluations": self.constraint_evaluations,
            "field_operations": self.field_operations,
            "materialized_artifact_bytes": self.materialized_artifact_bytes,
        }


def _assignment_values(
    parameter_space: Mapping[str, Any],
    assignment: Mapping[str, Any],
    characteristic: int,
) -> tuple[int, ...]:
    values: list[int] = []
    for variable in parameter_space["variables"]:
        raw = assignment[variable["parameter_id"]]
        if variable["sort"] == "boolean":
            values.append(int(raw) % characteristic)
        elif variable["sort"] == "rational":
            values.append(
                _reduce(
                    rational_backend.parse_canonical_rational(raw),
                    characteristic,
                )
            )
        else:
            values.append(0)
    return tuple(values)


def _evaluate_polynomial(
    polynomial: Mapping[str, Any],
    values: Sequence[int],
    characteristic: int,
    budget: _FieldBudget,
) -> int:
    result = 0
    for term in polynomial["terms"]:
        value = _reduce(
            rational_backend.parse_canonical_rational(term["coefficient"]),
            characteristic,
        )
        for coordinate, exponent in zip(
            values, term["exponents"], strict=True
        ):
            exponent = int(exponent)
            if exponent == 0:
                continue
            budget.operation(max(1, exponent.bit_length()))
            value = value * pow(coordinate, exponent, characteristic) % characteristic
            budget.operation()
        result = (result + value) % characteristic
        budget.operation()
    return result


def _unavailable_result(
    *,
    assignments: Sequence[tuple[str, Mapping[str, Any]]],
    reason_code: str,
    observed: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "status": "backend_unavailable",
        "expected_parameter_count": len(assignments),
        "residuals": [{
            "parameter_id": "",
            "assignment": None,
            "artifact_sha256": "",
            "kind": "backend_unavailable",
            "reason_code": reason_code,
            "backend_check_id": "",
            "observed": dict(observed),
        }],
        "coverage_complete": False,
        "resource_usage": {
            "constraint_evaluations": 0,
            "field_operations": 0,
            "materialized_artifact_bytes": 0,
        },
    }


def verify_rational_polynomial_map_prime_reduction(
    *,
    artifact: Mapping[str, Any],
    predicate_ir: Mapping[str, Any],
    characteristic: int,
) -> dict[str, Any]:
    """Replay one rational map after exact reduction to ``GF(p)``.

    The rational verifier supplies a normalized map, a fully expanded
    determinant, and exact point images.  Reduction commutes with
    differentiation, determinant expansion, and evaluation whenever all
    displayed denominators remain units, so reducing that exact trace is a
    second field replay rather than a sampled check.
    """

    from ztare.leanmill.adapters.rational_polynomial_map import (
        parse_rational,
        verify_rational_polynomial_map,
    )

    field = prime_field_descriptor(characteristic)
    source = verify_rational_polynomial_map(
        artifact,
        predicate_ir=predicate_ir,
    )
    normalized = source["normalized_map"]
    predicate = source["predicate"]
    rationals: list[Fraction] = []
    for component in normalized["components"]:
        rationals.extend(
            parse_rational(term["coefficient"])
            for term in component["terms"]
        )
    rationals.extend(
        parse_rational(value)
        for point in normalized["collision_inputs"]
        for value in point
    )
    for term in source["jacobian_determinant"]["terms"]:
        rationals.append(parse_rational(term["coefficient"]))
    rationals.extend(
        parse_rational(value)
        for image in source["collision_images"]
        for value in image
    )
    condition = predicate["jacobian_condition"]
    if condition["kind"] == "equals_constant":
        rationals.append(parse_rational(condition["constant"]))
    bad_denominators = sorted({
        value.denominator
        for value in rationals
        if value.denominator % characteristic == 0
    })
    exclusions: list[dict[str, Any]] = [
        {"kind": "noninvertible_denominator", "value": str(value)}
        for value in bad_denominators
    ]
    source_determinant_terms = source["jacobian_determinant"].get("terms", ())
    if len(source_determinant_terms) == 1:
        source_constant = parse_rational(
            source_determinant_terms[0]["coefficient"]
        )
        if (
            not any(source_determinant_terms[0]["exponents"])
            and source_constant != 0
            and source_constant.denominator % characteristic != 0
            and _reduce(source_constant, characteristic) == 0
        ):
            exclusions.append({
                "kind": "jacobian_constant_vanished",
                "value": str(characteristic),
            })

    determinant: dict[tuple[int, ...], int] = {}
    points: list[list[str]] = []
    images: list[list[str]] = []
    if not bad_denominators:
        for term in source["jacobian_determinant"]["terms"]:
            exponents = tuple(int(value) for value in term["exponents"])
            coefficient = _reduce(
                parse_rational(term["coefficient"]), characteristic
            )
            combined = (determinant.get(exponents, 0) + coefficient) % characteristic
            if combined:
                determinant[exponents] = combined
            else:
                determinant.pop(exponents, None)
        points = [
            [str(_reduce(parse_rational(value), characteristic)) for value in point]
            for point in normalized["collision_inputs"]
        ]
        images = [
            [str(_reduce(parse_rational(value), characteristic)) for value in image]
            for image in source["collision_images"]
        ]
        dimension = len(predicate["variables"])
        zero = (0,) * dimension
        if len({tuple(point) for point in points}) != len(points):
            exclusions.append({
                "kind": "collision_inputs_coalesced",
                "value": str(characteristic),
            })

    reason_code = "predicate_satisfied"
    common_image: list[str] | None = None
    if exclusions:
        status = "excluded"
        reason_code = "exceptional_prime"
    else:
        dimension = len(predicate["variables"])
        zero = (0,) * dimension
        if len(points) < int(predicate["minimum_distinct_collision_points"]):
            reason_code = "insufficient_collision_points"
        elif not determinant:
            reason_code = "jacobian_determinant_zero"
        elif set(determinant) != {zero}:
            reason_code = "jacobian_determinant_nonconstant"
        elif determinant[zero] == 0:
            reason_code = "jacobian_determinant_zero"
        elif condition["kind"] == "equals_constant" and determinant[zero] != (
            _reduce(parse_rational(condition["constant"]), characteristic)
        ):
            reason_code = "jacobian_determinant_mismatch"
        elif any(image != images[0] for image in images[1:]):
            reason_code = "collision_image_mismatch"
        else:
            common_image = images[0]
        status = "accepted" if reason_code == "predicate_satisfied" else "rejected"
    determinant_wire = {
        "terms": [
            {
                "coefficient": str(coefficient),
                "exponents": list(exponents),
            }
            for exponents, coefficient in sorted(
                determinant.items(), key=lambda item: (sum(item[0]), item[0])
            )
        ]
    }
    core = {
        "schema": MAP_REDUCTION_VERIFICATION_SCHEMA,
        "adapter_id": "rational_polynomial_map.v1",
        "field": field,
        "source_verification_sha256": source["receipt_sha256"],
        "normalized_source_map_sha256": source["normalized_map_sha256"],
        "predicate_sha256": source["predicate_sha256"],
        "jacobian_determinant": determinant_wire,
        "collision_inputs": points,
        "collision_images": images,
        "common_image": common_image,
        "status": status,
        "reason_code": reason_code,
        "exclusions": sorted(
            exclusions, key=lambda row: (row["kind"], row["value"])
        ),
        "transport_effect": "finite_field_replay_only_no_Q_certification",
        "authority": "reviewed_prime_field_reduction_capability",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def execute_problem(
    *,
    backend: Mapping[str, Any],
    parameter_space: Mapping[str, Any],
    backend_problem: Mapping[str, Any],
    symmetry_policy: Mapping[str, Any],
    resource_limits: Mapping[str, int],
    witness_schema: Mapping[str, Any],
    materialize,
    resource_error: type[RuntimeError],
) -> dict[str, Any]:
    del witness_schema
    descriptor = _descriptor(backend)
    projection = validate_problem(
        backend=descriptor,
        parameter_space=parameter_space,
        backend_problem=backend_problem,
        resource_limits=resource_limits,
        json_data=strict_json_data,
    )
    problem = projection["backend_problem"]
    assignments = enumerate_assignments(
        backend=descriptor,
        parameter_space=projection["parameter_space"],
    )
    receipt = problem["reduction_receipt"]
    field = problem["field"]
    if receipt["status"] == "excluded":
        return _unavailable_result(
            assignments=assignments,
            reason_code="prime_field_reduction_excluded",
            observed={
                "field": field,
                "reduction_receipt_sha256": receipt["receipt_sha256"],
                "exclusions": receipt["exclusions"],
            },
        )
    if symmetry_policy.get("kind") != "none":
        return _unavailable_result(
            assignments=assignments,
            reason_code="reviewed_explicit_quotient_executor_absent",
            observed={
                "field": field,
                "requested_symmetry_kind": symmetry_policy.get("kind"),
            },
        )
    source = problem["source_constraint_system"]
    characteristic = int(field["characteristic"])
    budget = _FieldBudget(
        common_limits=resource_limits,
        source_limits=source["resource_limits"],
        resource_error=resource_error,
    )
    residuals: list[dict[str, Any]] = []
    for parameter_id, assignment in assignments:
        artifact = materialize(assignment)
        budget.artifact(artifact)
        artifact_sha256 = content_hash(artifact)
        values = _assignment_values(
            projection["parameter_space"], assignment, characteristic
        )
        safe_rejection: tuple[Mapping[str, Any], int, int] | None = None
        inconclusive: list[str] = []
        evaluated = 0
        for constraint in source["constraints"]:
            budget.constraint()
            left = _evaluate_polynomial(
                constraint["left"], values, characteristic, budget
            )
            right = _evaluate_polynomial(
                constraint["right"], values, characteristic, budget
            )
            evaluated += 1
            if constraint["relation"] == "eq" and left != right:
                safe_rejection = (constraint, left, right)
                break
            if constraint["relation"] == "ne" and left == right:
                inconclusive.append(str(constraint["constraint_id"]))
        base_observed = {
            "field": field,
            "reduction_receipt_sha256": receipt["receipt_sha256"],
            "source_constraint_system_sha256": source[
                "constraint_system_sha256"
            ],
            "evaluated_constraint_count": evaluated,
        }
        if safe_rejection is not None:
            constraint, left, right = safe_rejection
            residuals.append({
                "parameter_id": parameter_id,
                "assignment": assignment,
                "artifact_sha256": artifact_sha256,
                "kind": "rejection",
                "reason_code": "modular_equality_refutes_rational_assignment",
                "backend_check_id": str(constraint["constraint_id"]),
                "observed": {
                    **base_observed,
                    "source_relation": "eq",
                    "left_residue": str(left),
                    "right_residue": str(right),
                    "transport_effect": _TRANSPORT_POLICY[
                        "equality_failure"
                    ],
                },
            })
            continue
        residuals.append({
            "parameter_id": parameter_id,
            "assignment": assignment,
            "artifact_sha256": artifact_sha256,
            "kind": "candidate",
            "reason_code": (
                "modular_inconclusive_requires_exact_rational_replay"
                if inconclusive
                else "modular_survivor_requires_exact_rational_replay"
            ),
            "backend_check_id": "",
            "observed": {
                **base_observed,
                "inconclusive_disequality_ids": inconclusive,
                "transport_effect": (
                    _TRANSPORT_POLICY["disequality_failure"]
                    if inconclusive
                    else _TRANSPORT_POLICY["equality_survival"]
                ),
            },
        })
    return {
        "status": "completed",
        "expected_parameter_count": len(assignments),
        "residuals": residuals,
        "coverage_complete": True,
        "resource_usage": budget.usage(),
    }


def capability(*, operation: str, **kwargs: Any) -> Any:
    backend = kwargs.get("backend")
    if not isinstance(backend, Mapping):
        raise ValueError("prime-field backend descriptor is malformed")
    descriptor = _descriptor(backend)
    if operation == "authoring_contract":
        return {
            "backend_capability": descriptor,
            "parameter_space_schema": (
                "leanmill.explicit_finite_parameter_space.v1"
            ),
            "allowed_parameter_sorts": ["boolean", "rational", "json_atom"],
            "backend_problem_schema": PROBLEM_SCHEMA,
            "field_descriptor_schema": FIELD_SCHEMA,
            "constraint_fragment": "polynomial_equalities_and_disequalities",
            "transport_policy": dict(_TRANSPORT_POLICY),
            "backend_resource_ceilings": {},
            "availability": "available",
        }
    if operation == "validate_problem":
        return validate_problem(**kwargs)
    if operation == "enumerate_assignments":
        return enumerate_assignments(**kwargs)
    if operation == "execute_problem":
        return execute_problem(**kwargs)
    raise ValueError("unknown prime-field construction backend operation")


__all__ = [
    "CAPABILITY_ID",
    "CONTRACT",
    "FIELD_SCHEMA",
    "MAP_REDUCTION_VERIFICATION_SCHEMA",
    "MAP_REDUCTION_VERIFIER_CAPABILITY",
    "PROBLEM_SCHEMA",
    "REDUCTION_RECEIPT_SCHEMA",
    "build_prime_field_reduction_problem",
    "capability",
    "prime_field_descriptor",
    "verify_rational_polynomial_map_prime_reduction",
]
