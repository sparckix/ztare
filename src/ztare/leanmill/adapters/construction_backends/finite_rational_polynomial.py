"""Exact finite polynomial construction over ``Q``.

This module owns the scalar wire format, polynomial language, and evaluator.
The common construction protocol treats the problem as bounded opaque JSON and
invokes this code only through a statically registered theory-adapter
capability.  Consequently another exact field or solver can implement the
same capability result algebra without changing the campaign runner or common
protocol.
"""
from __future__ import annotations

from fractions import Fraction
import itertools
import json
import math
import re
from typing import Any, Callable, Mapping, Sequence

from ztare.leanmill.adapters.exact_rational_wire import (
    MAX_CANONICAL_INTEGER_DECIMAL_DIGITS,
    project_canonical_rational_wire,
)
from ztare.leanmill.construction_wire_projection import (
    project_explicit_assignment_wire_bytes,
)
from ztare.leanmill.data_only_json import strict_json_data
from ztare.leanmill.theory_ir import content_hash


EXACT_CONSTRAINT_SYSTEM_SCHEMA = "leanmill.exact_constraint_system.v1"
EXACT_POLYNOMIAL_SCHEMA = "leanmill.exact_sparse_polynomial.v1"
FINITE_EXACT_BACKEND_ID = "finite_exact_enumerator.v1"
GROEBNER_RATIONAL_BACKEND_ID = "exact_groebner_rational.v1"

FINITE_EXACT_BACKEND = {
    "backend_id": FINITE_EXACT_BACKEND_ID,
    "contract": {
        "arithmetic": "Q",
        "domain": "explicit_finite",
        "ordering": "lexicographic_parameter_order",
        "failure_mode": "typed_residual",
    },
}
GROEBNER_RATIONAL_BACKEND = {
    "backend_id": GROEBNER_RATIONAL_BACKEND_ID,
    "contract": {
        "arithmetic": "Q",
        "constraint_fragment": "polynomial_equalities_and_disequalities",
        "monomial_order": "grevlex",
        "certificate_policy": "exact_rational_reconstruction_and_host_replay",
        "failure_mode": "typed_backend_unavailable",
    },
}

_PARAMETER_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")
_RATIONAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?$")
_RELATIONS = frozenset({"eq", "ne", "le", "ge"})
_MAX_RATIONAL_WIRE_LENGTH = 128
_MAX_JSON_ATOM_WIRE_BYTES = 65_536
_MAX_PROTOCOL_INTEGER_BITS = 4_096
_RESOURCE_HARD_LIMITS = {
    "max_constraints": 1_024,
    "max_constraint_evaluations": 1_000_000,
    "max_terms_per_polynomial": 4_096,
    "max_exponent": 128,
    "max_exact_operations": 20_000_000,
    "max_rational_bits": 1_000_000,
    "max_cumulative_rational_bit_work": 64_000_000,
    "max_rational_output_bytes": 8_000_000,
}


def _validate_resource_limits(value: Any) -> dict[str, int]:
    if not isinstance(value, Mapping) or set(value) != set(
        _RESOURCE_HARD_LIMITS
    ):
        raise ValueError(
            "rational polynomial backend resource-limit fields changed identity"
        )
    for field, hard_max in _RESOURCE_HARD_LIMITS.items():
        selected = value.get(field)
        if type(selected) is not int or not 1 <= selected <= hard_max:
            raise ValueError(
                "rational polynomial backend resource limit is invalid: "
                + field
            )
    return {
        field: int(value[field]) for field in sorted(_RESOURCE_HARD_LIMITS)
    }


def parse_canonical_rational(value: Any) -> Fraction:
    """Parse the unique integer-or-reduced-fraction wire representation."""

    if (
        not isinstance(value, str)
        or len(value) > _MAX_RATIONAL_WIRE_LENGTH
        or _RATIONAL_RE.fullmatch(value) is None
    ):
        raise ValueError(
            "exact rational must be an integer or positive-denominator n/d string"
        )
    numerator_text, separator, denominator_text = value.partition("/")
    denominator = int(denominator_text) if separator else 1
    try:
        result = Fraction(int(numerator_text), denominator)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError("exact rational denominator must be nonzero") from exc
    if format_canonical_rational(result) != value:
        raise ValueError("exact rational is not canonical")
    return result


def format_canonical_rational(value: Fraction) -> str:
    frozen = Fraction(value)
    return (
        str(frozen.numerator)
        if frozen.denominator == 1
        else f"{frozen.numerator}/{frozen.denominator}"
    )


def validate_parameter_space(
    value: Any,
    *,
    limits: Mapping[str, int],
    json_data: Callable[..., Any],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...], int]:
    row = json_data(value, context="construction parameter space")
    if not isinstance(row, dict) or set(row) != {"schema", "variables"}:
        raise ValueError("construction parameter-space fields changed identity")
    if row.get("schema") != "leanmill.explicit_finite_parameter_space.v1":
        raise ValueError("construction variables require explicit finite domains")
    raw_variables = row.get("variables")
    if not isinstance(raw_variables, list) or not raw_variables:
        raise ValueError("construction parameter space requires variables")
    if len(raw_variables) > 64:
        raise ValueError("too many construction variables")
    variables: list[dict[str, Any]] = []
    for raw in raw_variables:
        if not isinstance(raw, Mapping) or set(raw) != {
            "parameter_id", "sort", "domain",
        }:
            raise ValueError("construction variable fields changed identity")
        parameter_id = str(raw.get("parameter_id") or "")
        sort = str(raw.get("sort") or "")
        domain = raw.get("domain")
        if _PARAMETER_ID_RE.fullmatch(parameter_id) is None:
            raise ValueError("construction parameter id is malformed")
        if not isinstance(domain, list) or not domain or len(domain) > 256:
            raise ValueError(
                "construction parameter domain must be bounded and nonempty"
            )
        if sort == "boolean":
            if any(type(item) is not bool for item in domain):
                raise ValueError(
                    "boolean construction domain contains a non-Boolean"
                )
            normalized_domain: list[Any] = sorted(domain)
        elif sort == "rational":
            parsed = [parse_canonical_rational(item) for item in domain]
            maximum_bits = int(limits["max_rational_bits"])
            if any(
                abs(item.numerator).bit_length() > maximum_bits
                or item.denominator.bit_length() > maximum_bits
                for item in parsed
            ):
                raise ValueError(
                    "construction rational domain exceeds its bit ceiling"
                )
            normalized_domain = [
                format_canonical_rational(item) for item in sorted(parsed)
            ]
        elif sort == "json_atom":
            if any(
                type(item) not in {str, int, bool} and item is not None
                for item in domain
            ):
                raise ValueError(
                    "JSON-atom construction domain contains a container"
                )
            if any(
                (
                    isinstance(item, str)
                    and len(item) > _MAX_JSON_ATOM_WIRE_BYTES
                )
                or (
                    type(item) is int
                    and abs(item).bit_length() > _MAX_PROTOCOL_INTEGER_BITS
                )
                or len(
                    json.dumps(
                        item,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=True,
                    ).encode("utf-8")
                )
                > _MAX_JSON_ATOM_WIRE_BYTES
                for item in domain
            ):
                raise ValueError(
                    "JSON-atom construction domain exceeds its wire ceiling"
                )
            normalized_domain = sorted(
                domain,
                key=lambda item: json.dumps(
                    item, sort_keys=True, separators=(",", ":")
                ),
            )
        else:
            raise ValueError("construction parameter sort is unsupported")
        if domain != normalized_domain or len(domain) != len(
            {json.dumps(item, sort_keys=True) for item in domain}
        ):
            raise ValueError("construction parameter domain is not canonical")
        variables.append(
            {
                "parameter_id": parameter_id,
                "sort": sort,
                "domain": list(normalized_domain),
            }
        )
    parameter_ids = [row["parameter_id"] for row in variables]
    if parameter_ids != sorted(parameter_ids) or len(parameter_ids) != len(
        set(parameter_ids)
    ):
        raise ValueError(
            "construction variables must have unique canonical ids"
        )
    cardinality = math.prod(len(row["domain"]) for row in variables)
    if cardinality > int(limits["max_assignments"]):
        raise ValueError("construction parameter domain exceeds max_assignments")
    return (
        {
            "schema": "leanmill.explicit_finite_parameter_space.v1",
            "variables": variables,
        },
        tuple(variables),
        cardinality,
    )


def _polynomial(
    value: Any,
    *,
    parameter_count: int,
    limits: Mapping[str, int],
    json_data: Callable[..., Any],
) -> dict[str, Any]:
    row = json_data(value, context="exact sparse polynomial")
    if not isinstance(row, dict) or set(row) != {"schema", "terms"}:
        raise ValueError("exact polynomial fields changed identity")
    terms = row.get("terms")
    if row.get("schema") != EXACT_POLYNOMIAL_SCHEMA or not isinstance(
        terms, list
    ):
        raise ValueError("exact polynomial is malformed")
    if len(terms) > int(limits["max_terms_per_polynomial"]):
        raise ValueError("exact polynomial term ceiling exceeded")
    normalized: list[dict[str, Any]] = []
    for term in terms:
        if not isinstance(term, Mapping) or set(term) != {
            "coefficient", "exponents",
        }:
            raise ValueError("exact polynomial term fields changed identity")
        coefficient = parse_canonical_rational(term.get("coefficient"))
        maximum_bits = int(limits["max_rational_bits"])
        if (
            abs(coefficient.numerator).bit_length() > maximum_bits
            or coefficient.denominator.bit_length() > maximum_bits
        ):
            raise ValueError("exact polynomial coefficient exceeds its bit ceiling")
        exponents = term.get("exponents")
        if coefficient == 0:
            raise ValueError("exact polynomial cannot carry zero terms")
        if (
            not isinstance(exponents, list)
            or len(exponents) != parameter_count
            or any(
                type(exponent) is not int
                or exponent < 0
                or exponent > int(limits["max_exponent"])
                for exponent in exponents
            )
        ):
            raise ValueError("exact polynomial exponent vector is malformed")
        normalized.append(
            {
                "coefficient": format_canonical_rational(coefficient),
                "exponents": list(exponents),
            }
        )
    ordering = lambda term: (sum(term["exponents"]), tuple(term["exponents"]))
    if normalized != sorted(normalized, key=ordering) or len(
        {tuple(term["exponents"]) for term in normalized}
    ) != len(normalized):
        raise ValueError("exact polynomial terms are not canonical")
    return {"schema": EXACT_POLYNOMIAL_SCHEMA, "terms": normalized}


def validate_constraint_system(
    value: Any,
    *,
    parameter_ids: Sequence[str],
    json_data: Callable[..., Any] = strict_json_data,
) -> dict[str, Any]:
    row = json_data(value, context="exact constraint system")
    required = {
        "schema", "coefficient_domain", "parameter_ids", "constraints",
        "claim_boundary", "resource_limits",
    }
    if not isinstance(row, dict) or frozenset(row) not in {
        frozenset(required),
        frozenset(required | {"constraint_system_sha256"}),
    }:
        raise ValueError("exact constraint-system fields changed identity")
    limits = _validate_resource_limits(row.get("resource_limits"))
    if (
        row.get("schema") != EXACT_CONSTRAINT_SYSTEM_SCHEMA
        or row.get("coefficient_domain") != "Q"
        or row.get("parameter_ids") != list(parameter_ids)
        or row.get("claim_boundary")
        != "exact_constraint_bytes_only_no_solver_verdict"
    ):
        raise ValueError("exact constraint system crossed parameter identity")
    raw_constraints = row.get("constraints")
    if (
        not isinstance(raw_constraints, list)
        or len(raw_constraints) > int(limits["max_constraints"])
    ):
        raise ValueError("exact constraint count ceiling exceeded")
    normalized: list[dict[str, Any]] = []
    for raw in raw_constraints:
        if not isinstance(raw, Mapping) or set(raw) != {
            "constraint_id", "relation", "left", "right",
        }:
            raise ValueError("exact constraint fields changed identity")
        constraint_id = str(raw.get("constraint_id") or "")
        relation = str(raw.get("relation") or "")
        if _PARAMETER_ID_RE.fullmatch(constraint_id) is None:
            raise ValueError("exact constraint id is malformed")
        if relation not in _RELATIONS:
            raise ValueError("exact constraint relation is unsupported")
        normalized.append(
            {
                "constraint_id": constraint_id,
                "relation": relation,
                "left": _polynomial(
                    raw.get("left"),
                    parameter_count=len(parameter_ids),
                    limits=limits,
                    json_data=json_data,
                ),
                "right": _polynomial(
                    raw.get("right"),
                    parameter_count=len(parameter_ids),
                    limits=limits,
                    json_data=json_data,
                ),
            }
        )
    constraint_ids = [row["constraint_id"] for row in normalized]
    if constraint_ids != sorted(constraint_ids) or len(constraint_ids) != len(
        set(constraint_ids)
    ):
        raise ValueError("exact constraints must have unique canonical ids")
    core = {
        "schema": EXACT_CONSTRAINT_SYSTEM_SCHEMA,
        "coefficient_domain": "Q",
        "parameter_ids": list(parameter_ids),
        "constraints": normalized,
        "resource_limits": limits,
        "claim_boundary": "exact_constraint_bytes_only_no_solver_verdict",
    }
    supplied = row.get("constraint_system_sha256")
    if supplied is not None and supplied != content_hash(core):
        raise ValueError("exact constraint-system digest mismatch")
    return {**core, "constraint_system_sha256": content_hash(core)}


def build_exact_constraint_system(
    *,
    parameter_ids: Sequence[str],
    constraints: Sequence[Mapping[str, Any]],
    backend_resource_limits: Mapping[str, Any],
    json_data: Callable[..., Any] = strict_json_data,
) -> dict[str, Any]:
    limits = _validate_resource_limits(backend_resource_limits)
    raw = {
        "schema": EXACT_CONSTRAINT_SYSTEM_SCHEMA,
        "coefficient_domain": "Q",
        "parameter_ids": [str(value) for value in parameter_ids],
        "constraints": [dict(row) for row in constraints],
        "resource_limits": limits,
        "claim_boundary": "exact_constraint_bytes_only_no_solver_verdict",
    }
    return validate_constraint_system(
        raw,
        parameter_ids=parameter_ids,
        json_data=json_data,
    )


def _legacy_descriptor(value: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(value)
    if row not in (FINITE_EXACT_BACKEND, GROEBNER_RATIONAL_BACKEND):
        raise ValueError("construction backend descriptor is unsupported or mutable")
    return row


def validate_problem(
    *,
    backend: Mapping[str, Any],
    parameter_space: Any,
    backend_problem: Any,
    resource_limits: Mapping[str, int],
    json_data: Callable[..., Any],
) -> dict[str, Any]:
    descriptor = _legacy_descriptor(backend)
    raw_problem = json_data(
        backend_problem, context="exact rational backend problem"
    )
    if not isinstance(raw_problem, Mapping):
        raise ValueError("exact rational backend problem is malformed")
    backend_limits = _validate_resource_limits(
        raw_problem.get("resource_limits")
    )
    combined_limits = {**dict(resource_limits), **backend_limits}
    space, variables, cardinality = validate_parameter_space(
        parameter_space, limits=combined_limits, json_data=json_data
    )
    parameter_ids = [variable["parameter_id"] for variable in variables]
    constraints = validate_constraint_system(
        raw_problem,
        parameter_ids=parameter_ids,
        json_data=json_data,
    )
    sorts = {variable["parameter_id"]: variable["sort"] for variable in variables}
    nonnumeric_indices = {
        index
        for index, parameter_id in enumerate(parameter_ids)
        if sorts[parameter_id] == "json_atom"
    }
    if any(
        term["exponents"][index] != 0
        for constraint in constraints["constraints"]
        for side in ("left", "right")
        for term in constraint[side]["terms"]
        for index in nonnumeric_indices
    ):
        raise ValueError("exact polynomials cannot depend on JSON-atom parameters")
    return {
        "backend": descriptor,
        "parameter_space": space,
        "backend_problem": constraints,
        "parameter_ids": parameter_ids,
        "parameter_sorts": sorts,
        "cardinality": cardinality,
        "projected_assignment_wire_bytes": (
            project_explicit_assignment_wire_bytes(
                parameter_ids=parameter_ids,
                domains=[row["domain"] for row in space["variables"]],
            )
        ),
    }


def enumerate_assignments(
    *,
    parameter_space: Mapping[str, Any],
    backend: Mapping[str, Any] | None = None,
) -> tuple[tuple[str, dict[str, Any]], ...]:
    if backend is not None:
        _legacy_descriptor(backend)
    variables = parameter_space["variables"]
    rows: list[tuple[str, dict[str, Any]]] = []
    for values in itertools.product(*(row["domain"] for row in variables)):
        assignment = {
            row["parameter_id"]: value
            for row, value in zip(variables, values, strict=True)
        }
        rows.append(("assignment:" + content_hash(assignment), assignment))
    return tuple(rows)


class _ExecutionBudget:
    def __init__(
        self,
        limits: Mapping[str, int],
        resource_error: type[RuntimeError],
    ) -> None:
        self.limits = limits
        self.resource_error = resource_error
        self.constraint_evaluations = 0
        self.exact_operations = 0
        self.materialized_artifact_bytes = 0
        self.rational_bit_work = 0
        self.rational_output_bytes = 0
        self.current_projected_rational_decimal_digits = 0
        self.current_projected_rational_wire_bytes = 0
        self.peak_projected_rational_decimal_digits = 0
        self.peak_projected_rational_wire_bytes = 0

    def _raise(
        self,
        reason: str,
        *,
        resource: str,
        observed: int,
        ceiling: int,
    ) -> None:
        raise self.resource_error(
            reason,
            resource=resource,
            observed=observed,
            ceiling=ceiling,
            counters=self.usage(),
        )

    def exact(self, amount: int) -> None:
        if self.exact_operations + amount > int(
            self.limits["max_exact_operations"]
        ):
            self._raise(
                "exact_operation_limit_exhausted",
                resource="exact_operations",
                observed=self.exact_operations + amount,
                ceiling=int(self.limits["max_exact_operations"]),
            )
        self.exact_operations += amount

    def constraint(self) -> None:
        if self.constraint_evaluations + 1 > int(
            self.limits["max_constraint_evaluations"]
        ):
            ceiling = int(self.limits["max_constraint_evaluations"])
            self._raise(
                "constraint_evaluation_limit_exhausted",
                resource="constraint_evaluations",
                observed=self.constraint_evaluations + 1,
                ceiling=ceiling,
            )
        self.constraint_evaluations += 1

    def artifact(self, artifact: Mapping[str, Any]) -> None:
        amount = len(
            json.dumps(
                artifact,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        )
        if self.materialized_artifact_bytes + amount > int(
            self.limits["max_materialized_artifact_bytes"]
        ):
            self._raise(
                "materialized_artifact_byte_limit_exhausted",
                resource="materialized_artifact_bytes",
                observed=self.materialized_artifact_bytes + amount,
                ceiling=int(
                    self.limits["max_materialized_artifact_bytes"]
                ),
            )
        self.materialized_artifact_bytes += amount

    @staticmethod
    def _bits(value: Fraction) -> tuple[int, int]:
        return (
            max(1, abs(value.numerator).bit_length()),
            value.denominator.bit_length(),
        )

    def _rational_preflight(
        self, numerator_bits: int, denominator_bits: int
    ) -> None:
        maximum = int(self.limits["max_rational_bits"])
        observed = max(numerator_bits, denominator_bits)
        if observed > maximum:
            self._raise(
                "exact_rational_bit_limit_exhausted",
                resource="rational_bits",
                observed=observed,
                ceiling=maximum,
            )
        bit_work = numerator_bits + denominator_bits
        ceiling = int(self.limits["max_cumulative_rational_bit_work"])
        if self.rational_bit_work + bit_work > ceiling:
            self._raise(
                "cumulative_exact_rational_bit_work_limit_exhausted",
                resource="cumulative_rational_bit_work",
                observed=self.rational_bit_work + bit_work,
                ceiling=ceiling,
            )
        self.rational_bit_work += bit_work

    def rational(self, value: Fraction) -> Fraction:
        frozen = Fraction(value)
        self._rational_preflight(*self._bits(frozen))
        return frozen

    def add(self, left: Fraction, right: Fraction) -> Fraction:
        left = Fraction(left)
        right = Fraction(right)
        self.exact(1)
        if left == 0:
            predicted = self._bits(right)
        elif right == 0:
            predicted = self._bits(left)
        else:
            left_n, left_d = self._bits(left)
            right_n, right_d = self._bits(right)
            predicted = (
                max(left_n + right_d, right_n + left_d) + 1,
                left_d + right_d,
            )
        self._rational_preflight(*predicted)
        result = left + right
        if max(self._bits(result)) > int(self.limits["max_rational_bits"]):
            raise RuntimeError("rational addition crossed its preflight bound")
        return result

    def multiply(self, left: Fraction, right: Fraction) -> Fraction:
        left = Fraction(left)
        right = Fraction(right)
        self.exact(1)
        if left == 0 or right == 0:
            predicted = (1, 1)
        else:
            left_n, left_d = self._bits(left)
            right_n, right_d = self._bits(right)
            predicted = (left_n + right_n, left_d + right_d)
        self._rational_preflight(*predicted)
        result = left * right
        if max(self._bits(result)) > int(self.limits["max_rational_bits"]):
            raise RuntimeError("rational product crossed its preflight bound")
        return result

    def power(self, value: Fraction, exponent: int) -> Fraction:
        if type(exponent) is not int or exponent < 0:
            raise ValueError("exact rational exponent is malformed")
        frozen = Fraction(value)
        self.exact(max(1, exponent.bit_length()))
        if exponent == 0 or frozen in {Fraction(-1), Fraction(0), Fraction(1)}:
            predicted = (1, 1)
        else:
            numerator_bits, denominator_bits = self._bits(frozen)
            predicted = (
                max(1, numerator_bits * exponent),
                max(1, denominator_bits * exponent),
            )
        self._rational_preflight(*predicted)
        result = frozen**exponent
        if max(self._bits(result)) > int(self.limits["max_rational_bits"]):
            raise RuntimeError("rational power crossed its preflight bound")
        return result

    def format(self, value: Fraction) -> str:
        frozen = Fraction(value)
        projection = project_canonical_rational_wire(frozen)
        decimal_digits = projection["max_integer_decimal_digits"]
        amount = projection["wire_bytes"]
        self.current_projected_rational_decimal_digits = decimal_digits
        self.current_projected_rational_wire_bytes = amount
        self.peak_projected_rational_decimal_digits = max(
            self.peak_projected_rational_decimal_digits, decimal_digits
        )
        self.peak_projected_rational_wire_bytes = max(
            self.peak_projected_rational_wire_bytes, amount
        )
        decimal_ceiling = MAX_CANONICAL_INTEGER_DECIMAL_DIGITS
        if decimal_digits > decimal_ceiling:
            self._raise(
                "exact_rational_decimal_digit_limit_exhausted",
                resource="rational_decimal_digits",
                observed=decimal_digits,
                ceiling=decimal_ceiling,
            )
        ceiling = int(self.limits["max_rational_output_bytes"])
        if self.rational_output_bytes + amount > ceiling:
            self._raise(
                "exact_rational_output_byte_limit_exhausted",
                resource="rational_output_bytes",
                observed=self.rational_output_bytes + amount,
                ceiling=ceiling,
            )
        try:
            wire = format_canonical_rational(frozen)
        except ValueError:
            self._raise(
                "exact_rational_decimal_conversion_runtime_unavailable",
                resource="rational_decimal_digits",
                observed=decimal_digits,
                ceiling=decimal_ceiling,
            )
            raise RuntimeError("unreachable typed decimal conversion failure")
        if len(wire.encode("ascii")) != amount:
            raise RuntimeError(
                "canonical rational wire crossed its exact size projection"
            )
        self.rational_output_bytes += amount
        return wire

    def usage(self) -> dict[str, int]:
        return {
            "constraint_evaluations": self.constraint_evaluations,
            "current_projected_rational_decimal_digits": (
                self.current_projected_rational_decimal_digits
            ),
            "current_projected_rational_wire_bytes": (
                self.current_projected_rational_wire_bytes
            ),
            "exact_operations": self.exact_operations,
            "materialized_artifact_bytes": self.materialized_artifact_bytes,
            "peak_projected_rational_decimal_digits": (
                self.peak_projected_rational_decimal_digits
            ),
            "peak_projected_rational_wire_bytes": (
                self.peak_projected_rational_wire_bytes
            ),
            "rational_bit_work": self.rational_bit_work,
            "rational_output_bytes": self.rational_output_bytes,
        }


def _assignment_values(
    parameter_space: Mapping[str, Any],
    assignment: Mapping[str, Any],
    budget: _ExecutionBudget,
) -> tuple[Fraction, ...]:
    values: list[Fraction] = []
    for variable in parameter_space["variables"]:
        value = assignment[variable["parameter_id"]]
        values.append(budget.rational(
            Fraction(int(value), 1)
            if variable["sort"] == "boolean"
            else parse_canonical_rational(value)
            if variable["sort"] == "rational"
            else Fraction(0, 1)
        ))
    return tuple(values)


def _evaluate_polynomial(
    polynomial: Mapping[str, Any],
    values: Sequence[Fraction],
    budget: _ExecutionBudget,
) -> Fraction:
    result = Fraction(0)
    for term in polynomial["terms"]:
        coefficient = budget.rational(
            parse_canonical_rational(term["coefficient"])
        )
        value = coefficient
        for coordinate, exponent in zip(
            values, term["exponents"], strict=True
        ):
            if int(exponent) == 0:
                continue
            power = budget.power(coordinate, int(exponent))
            value = budget.multiply(value, power)
        result = budget.add(result, value)
    return result


def _relation_holds(relation: str, left: Fraction, right: Fraction) -> bool:
    return {
        "eq": left == right,
        "ne": left != right,
        "le": left <= right,
        "ge": left >= right,
    }[relation]


def execute_problem(
    *,
    backend: Mapping[str, Any],
    parameter_space: Mapping[str, Any],
    backend_problem: Mapping[str, Any],
    symmetry_policy: Mapping[str, Any],
    resource_limits: Mapping[str, int],
    witness_schema: Mapping[str, Any],
    materialize: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    resource_error: type[RuntimeError],
) -> dict[str, Any]:
    descriptor = _legacy_descriptor(backend)
    assignments = enumerate_assignments(parameter_space=parameter_space)
    if (
        descriptor["backend_id"] != FINITE_EXACT_BACKEND_ID
        or symmetry_policy.get("kind") != "none"
    ):
        reason_code = (
            "registered_exact_groebner_backend_absent"
            if descriptor["backend_id"] != FINITE_EXACT_BACKEND_ID
            else "reviewed_explicit_quotient_executor_absent"
        )
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
                "observed": {
                    "requested_backend_id": descriptor["backend_id"],
                    "requested_symmetry_kind": symmetry_policy.get("kind"),
                    "constraint_system_sha256": backend_problem[
                        "constraint_system_sha256"
                    ],
                },
            }],
            "coverage_complete": False,
            "resource_usage": {
                "constraint_evaluations": 0,
                "exact_operations": 0,
                "materialized_artifact_bytes": 0,
                "rational_bit_work": 0,
                "rational_output_bytes": 0,
            },
        }

    budget = _ExecutionBudget(
        {**dict(resource_limits), **dict(backend_problem["resource_limits"])},
        resource_error,
    )
    residuals: list[dict[str, Any]] = []
    for parameter_id, assignment in assignments:
        artifact_sha256 = ""
        try:
            artifact = materialize(assignment)
            artifact_sha256 = content_hash(artifact)
            budget.artifact(artifact)
            values = _assignment_values(parameter_space, assignment, budget)
            rejected = None
            evaluated = 0
            for constraint in backend_problem["constraints"]:
                budget.constraint()
                left = _evaluate_polynomial(constraint["left"], values, budget)
                right = _evaluate_polynomial(constraint["right"], values, budget)
                evaluated += 1
                if not _relation_holds(constraint["relation"], left, right):
                    rejected = (constraint, left, right)
                    break
            if rejected is not None:
                constraint, left, right = rejected
                rejected = (
                    constraint,
                    budget.format(left),
                    budget.format(right),
                )
        except resource_error:
            raise
        if rejected is None:
            residuals.append({
                "parameter_id": parameter_id,
                "assignment": assignment,
                "artifact_sha256": artifact_sha256,
                "kind": "candidate",
                "reason_code": "constraints_satisfied",
                "backend_check_id": "",
                "observed": {"evaluated_constraint_count": evaluated},
            })
        else:
            constraint, left_wire, right_wire = rejected
            residuals.append({
                "parameter_id": parameter_id,
                "assignment": assignment,
                "artifact_sha256": artifact_sha256,
                "kind": "rejection",
                "reason_code": "constraint_not_satisfied",
                "backend_check_id": str(constraint["constraint_id"]),
                "observed": {
                    "relation": str(constraint["relation"]),
                    "left": left_wire,
                    "right": right_wire,
                },
            })
    return {
        "status": (
            "backend_unavailable"
            if any(row["kind"] == "backend_unavailable" for row in residuals)
            else "completed"
        ),
        "expected_parameter_count": len(assignments),
        "residuals": residuals,
        "coverage_complete": True,
        "resource_usage": budget.usage(),
    }


def capability(*, operation: str, **kwargs: Any) -> Any:
    """Single reviewed capability surface used by the static adapter registry."""

    if operation == "authoring_contract":
        backend = kwargs.get("backend")
        if not isinstance(backend, Mapping):
            raise ValueError("construction backend descriptor is malformed")
        capability_id = str(
            backend.get("capability_id") or backend.get("backend_id") or ""
        )
        contracts = {
            FINITE_EXACT_BACKEND_ID: FINITE_EXACT_BACKEND["contract"],
            GROEBNER_RATIONAL_BACKEND_ID: GROEBNER_RATIONAL_BACKEND["contract"],
        }
        contract = contracts.get(capability_id)
        if (
            contract is None
            or str(backend.get("contract_sha256") or "")
            != content_hash(contract)
        ):
            raise ValueError("construction backend contract is not reviewed")
        return {
            "backend_capability": dict(backend),
            "parameter_space_schema": (
                "leanmill.explicit_finite_parameter_space.v1"
            ),
            "allowed_parameter_sorts": ["boolean", "rational", "json_atom"],
            "backend_problem_schema": EXACT_CONSTRAINT_SYSTEM_SCHEMA,
            "exact_polynomial_schema": EXACT_POLYNOMIAL_SCHEMA,
            "backend_resource_ceilings": dict(_RESOURCE_HARD_LIMITS),
            "availability": (
                "available"
                if capability_id == FINITE_EXACT_BACKEND_ID
                else "typed_unavailable"
            ),
        }
    if operation == "validate_problem":
        return validate_problem(**kwargs)
    if operation == "enumerate_assignments":
        return enumerate_assignments(**kwargs)
    if operation == "execute_problem":
        return execute_problem(**kwargs)
    raise ValueError("unknown construction backend operation")


__all__ = [
    "EXACT_CONSTRAINT_SYSTEM_SCHEMA",
    "EXACT_POLYNOMIAL_SCHEMA",
    "FINITE_EXACT_BACKEND",
    "FINITE_EXACT_BACKEND_ID",
    "GROEBNER_RATIONAL_BACKEND",
    "GROEBNER_RATIONAL_BACKEND_ID",
    "build_exact_constraint_system",
    "capability",
    "format_canonical_rational",
    "parse_canonical_rational",
    "validate_constraint_system",
]
