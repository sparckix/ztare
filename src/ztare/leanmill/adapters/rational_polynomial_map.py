"""Exact construction semantics for sparse polynomial maps over ``Q``.

The adapter verifies one data-only candidate against a frozen predicate.  It
does not propose coefficients, monomial supports, collision points, or search
strategies.  Every derivative, determinant coefficient, and point image is
recomputed from the normalized sparse map with :class:`fractions.Fraction`.
"""
from __future__ import annotations

from fractions import Fraction
import re
from typing import Any, Mapping, MutableMapping, Sequence

from ztare.leanmill.adapters.exact_rational_wire import (
    MAX_CANONICAL_INTEGER_DECIMAL_DIGITS,
    project_canonical_rational_wire,
)
from ztare.leanmill.protocol_validation import (
    require_exact_fields as _exact_fields,
)
from ztare.leanmill.theory_ir import TheorySignature, content_hash


ADAPTER_ID = "rational_polynomial_map.v1"
POLYNOMIAL_MAP_SCHEMA = "leanmill.rational_polynomial_map.v1"
PREDICATE_SCHEMA = "leanmill.rational_polynomial_map_predicate.v1"
TARGET_CONFIG_SCHEMA = "leanmill.rational_polynomial_map_target_config.v1"
VERIFICATION_RECEIPT_SCHEMA = (
    "leanmill.rational_polynomial_map_verification.v1"
)
EVIDENCE_PANEL_SCHEMA = "leanmill.rational_polynomial_map_evidence_panel.v1"
NORMALIZER_CAPABILITY = "rational_sparse_polynomial_map_normalizer"
VERIFIER_CAPABILITY = "rational_polynomial_map_exact_verifier"

MAX_DIMENSION = 8
MAX_COMPONENT_TERMS = 256
MAX_EXPONENT = 64
MAX_TOTAL_DEGREE = 128
MAX_COLLISION_POINTS = 32
MAX_RATIONAL_WIRE_LENGTH = 128
MAX_EXPANDED_DETERMINANT_TERMS = 250_000
MAX_DETERMINANT_EXACT_OPERATIONS = 2_000_000
MAX_NORMALIZATION_EXACT_OPERATIONS = 100_000
MAX_EXACT_RATIONAL_BITS = 16_384
MAX_CUMULATIVE_RATIONAL_BIT_WORK = 64_000_000
MAX_EXACT_RATIONAL_OUTPUT_BYTES = 8_000_000
MAX_EXACT_RATIONAL_DECIMAL_DIGITS = (
    MAX_CANONICAL_INTEGER_DECIMAL_DIGITS
)
MAX_LIVE_DETERMINANT_TERMS = 1_000_000
MAX_LIVE_DETERMINANT_COEFFICIENT_BITS = 64_000_000

_RATIONAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?$")
_VARIABLE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_DERIVED_ARTIFACT_FIELDS = frozenset(
    {
        "certificate",
        "collision_images",
        "common_image",
        "determinant",
        "evidence_refs",
        "jacobian_determinant",
        "receipt_sha256",
        "verification",
    }
)

Exponent = tuple[int, ...]
Polynomial = dict[Exponent, Fraction]


class RationalPolynomialMapArtifactError(ValueError):
    """A candidate artifact failed a stable adapter validation class."""

    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = str(reason_code)
        super().__init__(f"{self.reason_code}: {detail}")


def _artifact_fields(
    value: Mapping[str, Any], required: set[str], *, context: str
) -> None:
    missing = required - set(value)
    unknown = set(value) - required
    if unknown & _DERIVED_ARTIFACT_FIELDS:
        raise RationalPolynomialMapArtifactError(
            "candidate_supplied_derived_certificate",
            f"{context} contains host-derived fields "
            f"{sorted(unknown & _DERIVED_ARTIFACT_FIELDS)}",
        )
    if any("authority" in key.lower() for key in unknown):
        raise RationalPolynomialMapArtifactError(
            "unknown_authority_field",
            f"{context} contains authority fields {sorted(unknown)}",
        )
    if missing or unknown:
        raise RationalPolynomialMapArtifactError(
            "artifact_field_mismatch",
            f"{context} missing={sorted(missing)}, unknown={sorted(unknown)}",
        )


def parse_rational(value: Any) -> Fraction:
    """Parse the adapter's exact, non-decimal rational wire format."""

    if (
        not isinstance(value, str)
        or len(value) > MAX_RATIONAL_WIRE_LENGTH
        or _RATIONAL_RE.fullmatch(value) is None
    ):
        raise RationalPolynomialMapArtifactError(
            "malformed_rational", "expected an integer or n/d string"
        )
    numerator_text, separator, denominator_text = value.partition("/")
    denominator = int(denominator_text) if separator else 1
    try:
        return Fraction(int(numerator_text), denominator)
    except (ValueError, ZeroDivisionError) as exc:
        raise RationalPolynomialMapArtifactError(
            "malformed_rational", "rational denominator must be nonzero"
        ) from exc


def format_rational(value: Fraction) -> str:
    value = Fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _variables(value: Any) -> tuple[str, ...]:
    if (
        not isinstance(value, (list, tuple))
        or not 1 <= len(value) <= MAX_DIMENSION
        or any(
            not isinstance(name, str)
            or _VARIABLE_RE.fullmatch(name) is None
            for name in value
        )
    ):
        raise ValueError(
            f"rational polynomial maps require 1..{MAX_DIMENSION} variable names"
        )
    names = tuple(value)
    if len(set(names)) != len(names):
        raise ValueError("rational polynomial map variables must be distinct")
    return names


def _target_digest(value: Any) -> str:
    digest = str(value or "").removeprefix("sha256:")
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError("polynomial-map target requires a snapshot SHA-256")
    return "sha256:" + digest


def _jacobian_condition(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("polynomial-map predicate requires a Jacobian condition")
    kind = value.get("kind")
    if kind == "constant_nonzero":
        _exact_fields(value, {"kind"}, context="Jacobian condition")
        return {"kind": "constant_nonzero"}
    if kind == "equals_constant":
        _exact_fields(value, {"kind", "constant"}, context="Jacobian condition")
        constant = parse_rational(value.get("constant"))
        if constant == 0:
            raise ValueError("declared Jacobian constant must be nonzero")
        return {
            "kind": "equals_constant",
            "constant": format_rational(constant),
        }
    raise ValueError("unsupported polynomial-map Jacobian condition")


def rational_polynomial_map_predicate(
    *,
    variables: Sequence[str],
    jacobian_condition: Mapping[str, Any],
    minimum_distinct_collision_points: int,
    target_snapshot_sha256: str,
) -> dict[str, Any]:
    names = _variables(variables)
    if (
        type(minimum_distinct_collision_points) is not int
        or not 2
        <= minimum_distinct_collision_points
        <= MAX_COLLISION_POINTS
    ):
        raise ValueError(
            "polynomial-map predicate requires at least two collision points"
        )
    return {
        "schema": PREDICATE_SCHEMA,
        "coefficient_domain": "Q",
        "variables": list(names),
        "jacobian_condition": _jacobian_condition(jacobian_condition),
        "minimum_distinct_collision_points": minimum_distinct_collision_points,
        "target_snapshot_sha256": _target_digest(target_snapshot_sha256),
    }


def rational_polynomial_map_schema(
    *, variables: Sequence[str]
) -> dict[str, Any]:
    names = _variables(variables)
    dimension = len(names)
    rational = {
        "type": "string",
        "maxLength": MAX_RATIONAL_WIRE_LENGTH,
        "pattern": r"^-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?$",
    }
    exponent_vector = {
        "type": "array",
        "minItems": dimension,
        "maxItems": dimension,
        "items": {
            "type": "integer",
            "minimum": 0,
            "maximum": MAX_EXPONENT,
        },
    }
    term = {
        "type": "object",
        "additionalProperties": False,
        "required": ["coefficient", "exponents"],
        "properties": {
            "coefficient": rational,
            "exponents": exponent_vector,
        },
    }
    polynomial = {
        "type": "object",
        "additionalProperties": False,
        "required": ["terms"],
        "properties": {
            "terms": {
                "type": "array",
                "maxItems": MAX_COMPONENT_TERMS,
                "items": term,
            }
        },
    }
    point = {
        "type": "array",
        "minItems": dimension,
        "maxItems": dimension,
        "items": rational,
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema",
            "coefficient_domain",
            "variables",
            "components",
            "collision_inputs",
        ],
        "properties": {
            "schema": {"type": "string", "const": POLYNOMIAL_MAP_SCHEMA},
            "coefficient_domain": {"type": "string", "const": "Q"},
            "variables": {
                "type": "array",
                "const": list(names),
            },
            "components": {
                "type": "array",
                "minItems": dimension,
                "maxItems": dimension,
                "items": polynomial,
            },
            "collision_inputs": {
                "type": "array",
                "minItems": 2,
                "maxItems": MAX_COLLISION_POINTS,
                "items": point,
            },
        },
    }


def rational_polynomial_map_witness_construction_interface(
    *,
    variables: Sequence[str],
    jacobian_condition: Mapping[str, Any],
    minimum_distinct_collision_points: int,
    target_snapshot_sha256: str,
    target_config_sha256: str,
) -> dict[str, Any]:
    from ztare.leanmill.witness_construction_boundary import (
        build_witness_construction_interface,
    )

    predicate = rational_polynomial_map_predicate(
        variables=variables,
        jacobian_condition=jacobian_condition,
        minimum_distinct_collision_points=minimum_distinct_collision_points,
        target_snapshot_sha256=target_snapshot_sha256,
    )
    return build_witness_construction_interface(
        predicate_ir=predicate,
        witness_schema=rational_polynomial_map_schema(
            variables=predicate["variables"]
        ),
        normalizer={
            "capability_id": NORMALIZER_CAPABILITY,
            "contract": {
                "kind": "canonical_sparse_polynomial_map",
                "coefficient_domain": "Q",
                "monomial_order": "graded_lex_ascending",
                "combine_duplicate_monomials": True,
                "max_exact_operations": MAX_NORMALIZATION_EXACT_OPERATIONS,
                "max_rational_bits": MAX_EXACT_RATIONAL_BITS,
                "max_cumulative_rational_bit_work": (
                    MAX_CUMULATIVE_RATIONAL_BIT_WORK
                ),
                "max_rational_output_bytes": (
                    MAX_EXACT_RATIONAL_OUTPUT_BYTES
                ),
            },
        },
        verifier={
            "capability_id": VERIFIER_CAPABILITY,
            "contract": {
                "kind": "exact_full_jacobian_and_collision_replay",
                "determinant_algorithm": "subset_dynamic_programming",
                "max_expanded_terms": MAX_EXPANDED_DETERMINANT_TERMS,
                "max_exact_operations": MAX_DETERMINANT_EXACT_OPERATIONS,
                "max_rational_bits": MAX_EXACT_RATIONAL_BITS,
                "max_cumulative_rational_bit_work": (
                    MAX_CUMULATIVE_RATIONAL_BIT_WORK
                ),
                "max_rational_output_bytes": (
                    MAX_EXACT_RATIONAL_OUTPUT_BYTES
                ),
                "max_live_determinant_terms": MAX_LIVE_DETERMINANT_TERMS,
                "max_live_determinant_coefficient_bits": (
                    MAX_LIVE_DETERMINANT_COEFFICIENT_BITS
                ),
            },
        },
        discharge_policy="construction_artifact_ratification_required",
        target_config_sha256=target_config_sha256,
    )


def _bind_predicate(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema",
        "coefficient_domain",
        "variables",
        "jacobian_condition",
        "minimum_distinct_collision_points",
        "target_snapshot_sha256",
    }
    _exact_fields(value, required, context="polynomial-map predicate")
    if value.get("schema") != PREDICATE_SCHEMA:
        raise ValueError("unsupported polynomial-map predicate schema")
    if value.get("coefficient_domain") != "Q":
        raise ValueError("polynomial-map predicate crossed coefficient domain")
    expected = rational_polynomial_map_predicate(
        variables=value.get("variables"),
        jacobian_condition=value.get("jacobian_condition"),
        minimum_distinct_collision_points=value.get(
            "minimum_distinct_collision_points"
        ),
        target_snapshot_sha256=str(value.get("target_snapshot_sha256") or ""),
    )
    if expected != dict(value):
        raise ValueError("polynomial-map predicate is not in canonical wire form")
    return expected


def _polynomial_wire(
    polynomial: Mapping[Exponent, Fraction],
    *,
    arithmetic_budget: _ExactArithmeticBudget | None = None,
    max_coefficient_wire_bytes: int | None = None,
) -> dict[str, Any]:
    ordered = sorted(polynomial.items(), key=lambda item: (sum(item[0]), item[0]))
    return {
        "terms": [
            {
                "coefficient": (
                    arithmetic_budget.serialize(
                        coefficient,
                        max_wire_bytes=max_coefficient_wire_bytes,
                    )
                    if arithmetic_budget is not None
                    else format_rational(coefficient)
                ),
                "exponents": list(exponents),
            }
            for exponents, coefficient in ordered
            if coefficient
        ]
    }


def _parse_polynomial(
    value: Any,
    *,
    dimension: int,
    context: str,
    arithmetic_budget: _ExactArithmeticBudget | None = None,
) -> Polynomial:
    if not isinstance(value, Mapping):
        raise RationalPolynomialMapArtifactError(
            "malformed_polynomial", f"{context} must be an object"
        )
    _artifact_fields(value, {"terms"}, context=context)
    terms = value.get("terms")
    if not isinstance(terms, list) or len(terms) > MAX_COMPONENT_TERMS:
        raise RationalPolynomialMapArtifactError(
            "polynomial_term_bound_exceeded",
            f"{context} has more than {MAX_COMPONENT_TERMS} source terms",
        )
    result: Polynomial = {}
    for index, raw in enumerate(terms):
        term_context = f"{context} term {index}"
        if not isinstance(raw, Mapping):
            raise RationalPolynomialMapArtifactError(
                "malformed_polynomial_term", f"{term_context} must be an object"
            )
        _artifact_fields(raw, {"coefficient", "exponents"}, context=term_context)
        exponents_raw = raw.get("exponents")
        if (
            not isinstance(exponents_raw, list)
            or len(exponents_raw) != dimension
            or any(
                type(exponent) is not int
                or exponent < 0
                or exponent > MAX_EXPONENT
                for exponent in exponents_raw
            )
        ):
            raise RationalPolynomialMapArtifactError(
                "malformed_exponent_vector",
                f"{term_context} must have {dimension} bounded exponents",
            )
        exponents = tuple(exponents_raw)
        if sum(exponents) > MAX_TOTAL_DEGREE:
            raise RationalPolynomialMapArtifactError(
                "polynomial_degree_bound_exceeded",
                f"{term_context} exceeds total degree {MAX_TOTAL_DEGREE}",
            )
        coefficient = parse_rational(raw.get("coefficient"))
        if arithmetic_budget is not None:
            coefficient = arithmetic_budget.admit(coefficient)
            combined = arithmetic_budget.add(
                result.get(exponents, Fraction(0)), coefficient
            )
        else:
            combined = result.get(exponents, Fraction(0)) + coefficient
        result[exponents] = combined
        if combined == 0:
            del result[exponents]
    return result


def normalize_rational_polynomial_map(
    artifact: Mapping[str, Any],
    *,
    predicate_ir: Mapping[str, Any],
    _arithmetic_budget: _ExactArithmeticBudget | None = None,
) -> dict[str, Any]:
    arithmetic_budget = _arithmetic_budget or _ExactArithmeticBudget(
        max_exact_operations=MAX_NORMALIZATION_EXACT_OPERATIONS,
        max_rational_bits=MAX_EXACT_RATIONAL_BITS,
        max_cumulative_rational_bit_work=(
            MAX_CUMULATIVE_RATIONAL_BIT_WORK
        ),
        max_rational_output_bytes=MAX_EXACT_RATIONAL_OUTPUT_BYTES,
        operation_reason_code=(
            "polynomial_normalization_operation_budget_exceeded"
        ),
    )
    predicate = _bind_predicate(predicate_ir)
    required = {
        "schema",
        "coefficient_domain",
        "variables",
        "components",
        "collision_inputs",
    }
    if not isinstance(artifact, Mapping):
        raise RationalPolynomialMapArtifactError(
            "malformed_artifact", "polynomial map must be an object"
        )
    _artifact_fields(artifact, required, context="polynomial-map artifact")
    if artifact.get("schema") != POLYNOMIAL_MAP_SCHEMA:
        raise RationalPolynomialMapArtifactError(
            "unsupported_artifact_schema", "polynomial-map schema changed"
        )
    if artifact.get("coefficient_domain") != "Q":
        raise RationalPolynomialMapArtifactError(
            "coefficient_domain_mismatch", "only exact rationals are supported"
        )
    variables = _variables(artifact.get("variables"))
    expected_variables = tuple(predicate["variables"])
    if variables != expected_variables:
        raise RationalPolynomialMapArtifactError(
            "variable_identity_mismatch", "map variables crossed the predicate"
        )
    dimension = len(variables)
    components_raw = artifact.get("components")
    if not isinstance(components_raw, list) or len(components_raw) != dimension:
        raise RationalPolynomialMapArtifactError(
            "component_arity_mismatch",
            "a polynomial self-map needs one component per variable",
        )
    components = [
        _polynomial_wire(
            _parse_polynomial(
                component,
                dimension=dimension,
                context=f"polynomial component {index}",
                arithmetic_budget=arithmetic_budget,
            )
            ,
            arithmetic_budget=arithmetic_budget,
            max_coefficient_wire_bytes=MAX_RATIONAL_WIRE_LENGTH,
        )
        for index, component in enumerate(components_raw)
    ]
    points_raw = artifact.get("collision_inputs")
    if (
        not isinstance(points_raw, list)
        or not 2 <= len(points_raw) <= MAX_COLLISION_POINTS
    ):
        raise RationalPolynomialMapArtifactError(
            "collision_point_count_invalid",
            f"supply 2..{MAX_COLLISION_POINTS} collision inputs",
        )
    points: list[list[str]] = []
    for index, point in enumerate(points_raw):
        if not isinstance(point, list) or len(point) != dimension:
            raise RationalPolynomialMapArtifactError(
                "collision_point_arity_mismatch",
                f"collision input {index} must have {dimension} coordinates",
            )
        normalized_point = []
        for value in point:
            coordinate = arithmetic_budget.admit(parse_rational(value))
            normalized_point.append(
                arithmetic_budget.serialize(
                    coordinate,
                    max_wire_bytes=MAX_RATIONAL_WIRE_LENGTH,
                )
            )
        points.append(normalized_point)
    return {
        "schema": POLYNOMIAL_MAP_SCHEMA,
        "coefficient_domain": "Q",
        "variables": list(variables),
        "components": components,
        "collision_inputs": points,
    }


def _polynomial_from_wire(
    value: Mapping[str, Any],
    dimension: int,
    *,
    arithmetic_budget: _ExactArithmeticBudget | None = None,
) -> Polynomial:
    return _parse_polynomial(
        value,
        dimension=dimension,
        context="polynomial",
        arithmetic_budget=arithmetic_budget,
    )


def _capability_unavailable(
    reason_code: str,
    *,
    resource: str = "",
    observed: int | None = None,
    ceiling: int | None = None,
    counters: Mapping[str, int] | None = None,
) -> None:
    from ztare.leanmill.witness_construction_boundary import (
        WitnessConstructionCapabilityUnavailable,
    )

    raise WitnessConstructionCapabilityUnavailable(
        reason_code,
        resource=resource,
        observed=observed,
        ceiling=ceiling,
        counters=counters,
    )


def _positive_limit(value: int, *, context: str) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{context} must be a positive integer")
    return value


def _integer_bits(value: int) -> int:
    return max(1, abs(int(value)).bit_length())


def _fraction_bits(value: Fraction) -> tuple[int, int]:
    return _integer_bits(value.numerator), value.denominator.bit_length()


class _ExactArithmeticBudget:
    """Pre-allocation bounds for every exact-rational adapter operation."""

    def __init__(
        self,
        *,
        max_exact_operations: int,
        max_rational_bits: int,
        max_cumulative_rational_bit_work: int,
        max_rational_output_bytes: int,
        operation_reason_code: str,
    ) -> None:
        self.max_exact_operations = _positive_limit(
            max_exact_operations, context="exact polynomial operation budget"
        )
        self.max_rational_bits = _positive_limit(
            max_rational_bits, context="exact rational bit budget"
        )
        self.max_cumulative_rational_bit_work = _positive_limit(
            max_cumulative_rational_bit_work,
            context="cumulative exact rational bit-work budget",
        )
        self.max_rational_output_bytes = _positive_limit(
            max_rational_output_bytes,
            context="exact rational output budget",
        )
        self.max_decimal_digits_per_integer = (
            MAX_EXACT_RATIONAL_DECIMAL_DIGITS
        )
        self.operation_reason_code = str(operation_reason_code)
        self.used_exact_operations = 0
        self.used_rational_bit_work = 0
        self.used_rational_output_bytes = 0
        self.current_projected_rational_decimal_digits = 0
        self.current_projected_rational_wire_bytes = 0
        self.peak_projected_rational_decimal_digits = 0
        self.peak_projected_rational_wire_bytes = 0
        self.current_live_determinant_terms = 0
        self.current_live_determinant_coefficient_bits = 0
        self.peak_live_determinant_terms = 0
        self.peak_live_determinant_coefficient_bits = 0

    def counters(self) -> dict[str, int]:
        return {
            "current_live_determinant_coefficient_bits": (
                self.current_live_determinant_coefficient_bits
            ),
            "current_live_determinant_terms": (
                self.current_live_determinant_terms
            ),
            "exact_operations": self.used_exact_operations,
            "current_projected_rational_decimal_digits": (
                self.current_projected_rational_decimal_digits
            ),
            "current_projected_rational_wire_bytes": (
                self.current_projected_rational_wire_bytes
            ),
            "peak_live_determinant_coefficient_bits": (
                self.peak_live_determinant_coefficient_bits
            ),
            "peak_live_determinant_terms": self.peak_live_determinant_terms,
            "peak_projected_rational_decimal_digits": (
                self.peak_projected_rational_decimal_digits
            ),
            "peak_projected_rational_wire_bytes": (
                self.peak_projected_rational_wire_bytes
            ),
            "rational_bit_work": self.used_rational_bit_work,
            "rational_output_bytes": self.used_rational_output_bytes,
        }

    def limits(self) -> dict[str, int]:
        return {
            "max_cumulative_rational_bit_work": (
                self.max_cumulative_rational_bit_work
            ),
            "max_exact_operations": self.max_exact_operations,
            "max_decimal_digits_per_integer": (
                self.max_decimal_digits_per_integer
            ),
            "max_rational_bits": self.max_rational_bits,
            "max_rational_output_bytes": self.max_rational_output_bytes,
        }

    def unavailable(
        self,
        reason_code: str,
        *,
        resource: str,
        observed: int,
        ceiling: int,
    ) -> None:
        _capability_unavailable(
            reason_code,
            resource=resource,
            observed=observed,
            ceiling=ceiling,
            counters=self.counters(),
        )

    def observe_live_determinant(
        self, *, terms: int, coefficient_bits: int
    ) -> None:
        self.current_live_determinant_terms = terms
        self.current_live_determinant_coefficient_bits = coefficient_bits
        self.peak_live_determinant_terms = max(
            self.peak_live_determinant_terms, terms
        )
        self.peak_live_determinant_coefficient_bits = max(
            self.peak_live_determinant_coefficient_bits, coefficient_bits
        )

    def observe_rational_wire_projection(
        self, *, decimal_digits: int, wire_bytes: int
    ) -> None:
        self.current_projected_rational_decimal_digits = decimal_digits
        self.current_projected_rational_wire_bytes = wire_bytes
        self.peak_projected_rational_decimal_digits = max(
            self.peak_projected_rational_decimal_digits, decimal_digits
        )
        self.peak_projected_rational_wire_bytes = max(
            self.peak_projected_rational_wire_bytes, wire_bytes
        )

    def charge_operations(self, amount: int) -> None:
        if type(amount) is not int or amount < 0:
            raise ValueError("exact polynomial operation charge is invalid")
        if self.used_exact_operations + amount > self.max_exact_operations:
            self.unavailable(
                self.operation_reason_code,
                resource="exact_operations",
                observed=self.used_exact_operations + amount,
                ceiling=self.max_exact_operations,
            )
        self.used_exact_operations += amount

    def _preflight_bits(self, numerator_bits: int, denominator_bits: int) -> None:
        numerator_bits = _positive_limit(
            numerator_bits, context="predicted rational numerator bits"
        )
        denominator_bits = _positive_limit(
            denominator_bits, context="predicted rational denominator bits"
        )
        if (
            numerator_bits > self.max_rational_bits
            or denominator_bits > self.max_rational_bits
        ):
            self.unavailable(
                "polynomial_exact_rational_bit_budget_exceeded",
                resource="rational_bits",
                observed=max(numerator_bits, denominator_bits),
                ceiling=self.max_rational_bits,
            )
        bit_work = numerator_bits + denominator_bits
        if (
            self.used_rational_bit_work + bit_work
            > self.max_cumulative_rational_bit_work
        ):
            self.unavailable(
                "polynomial_cumulative_rational_bit_work_budget_exceeded",
                resource="cumulative_rational_bit_work",
                observed=self.used_rational_bit_work + bit_work,
                ceiling=self.max_cumulative_rational_bit_work,
            )
        self.used_rational_bit_work += bit_work

    def _check_result(self, value: Fraction) -> Fraction:
        frozen = Fraction(value)
        numerator_bits, denominator_bits = _fraction_bits(frozen)
        if (
            numerator_bits > self.max_rational_bits
            or denominator_bits > self.max_rational_bits
        ):
            raise RuntimeError(
                "exact rational result exceeded its preflight growth bound"
            )
        return frozen

    def admit(self, value: Fraction) -> Fraction:
        frozen = Fraction(value)
        self._preflight_bits(*_fraction_bits(frozen))
        return frozen

    def add(self, left: Fraction, right: Fraction) -> Fraction:
        left = Fraction(left)
        right = Fraction(right)
        self.charge_operations(1)
        if left == 0:
            predicted = _fraction_bits(right)
        elif right == 0:
            predicted = _fraction_bits(left)
        else:
            left_n, left_d = _fraction_bits(left)
            right_n, right_d = _fraction_bits(right)
            predicted = (
                max(left_n + right_d, right_n + left_d) + 1,
                left_d + right_d,
            )
        self._preflight_bits(*predicted)
        return self._check_result(left + right)

    def multiply(self, left: Fraction, right: Fraction) -> Fraction:
        left = Fraction(left)
        right = Fraction(right)
        self.charge_operations(1)
        if left == 0 or right == 0:
            predicted = (1, 1)
        else:
            left_n, left_d = _fraction_bits(left)
            right_n, right_d = _fraction_bits(right)
            predicted = (left_n + right_n, left_d + right_d)
        self._preflight_bits(*predicted)
        return self._check_result(left * right)

    def multiply_integer(self, value: Fraction, factor: int) -> Fraction:
        if type(factor) is not int:
            raise ValueError("exact rational integer scale is malformed")
        return self.multiply(value, Fraction(factor))

    def power(self, value: Fraction, exponent: int) -> Fraction:
        if type(exponent) is not int or exponent < 0:
            raise ValueError("exact rational exponent is malformed")
        value = Fraction(value)
        self.charge_operations(max(1, exponent.bit_length()))
        if exponent == 0 or value in {Fraction(1), Fraction(-1)}:
            predicted = (1, 1)
        elif value == 0:
            predicted = (1, 1)
        else:
            numerator_bits, denominator_bits = _fraction_bits(value)
            predicted = (
                max(1, numerator_bits * exponent),
                max(1, denominator_bits * exponent),
            )
        self._preflight_bits(*predicted)
        return self._check_result(value**exponent)

    def serialize(
        self,
        value: Fraction,
        *,
        max_wire_bytes: int | None = None,
    ) -> str:
        frozen = self._check_result(Fraction(value))
        projection = project_canonical_rational_wire(frozen)
        decimal_digits = projection["max_integer_decimal_digits"]
        wire_bytes = projection["wire_bytes"]
        self.observe_rational_wire_projection(
            decimal_digits=decimal_digits,
            wire_bytes=wire_bytes,
        )
        if decimal_digits > self.max_decimal_digits_per_integer:
            self.unavailable(
                "polynomial_decimal_digit_budget_exceeded",
                resource="rational_decimal_digits",
                observed=decimal_digits,
                ceiling=self.max_decimal_digits_per_integer,
            )
        if max_wire_bytes is not None and wire_bytes > max_wire_bytes:
            self.unavailable(
                "polynomial_rational_output_wire_limit_exceeded",
                resource="rational_output_item_bytes",
                observed=wire_bytes,
                ceiling=max_wire_bytes,
            )
        if (
            self.used_rational_output_bytes + wire_bytes
            > self.max_rational_output_bytes
        ):
            self.unavailable(
                "polynomial_rational_output_budget_exceeded",
                resource="rational_output_bytes",
                observed=self.used_rational_output_bytes + wire_bytes,
                ceiling=self.max_rational_output_bytes,
            )
        try:
            wire = format_rational(frozen)
        except ValueError:
            self.unavailable(
                "polynomial_decimal_conversion_runtime_unavailable",
                resource="rational_decimal_digits",
                observed=decimal_digits,
                ceiling=self.max_decimal_digits_per_integer,
            )
            raise RuntimeError("unreachable typed decimal conversion failure")
        if len(wire.encode("ascii")) != wire_bytes:
            raise RuntimeError(
                "canonical rational wire crossed its exact size projection"
            )
        self.used_rational_output_bytes += wire_bytes
        return wire


class _LiveDeterminantBudget:
    """Aggregate live-state ceiling for determinant polynomials."""

    def __init__(
        self,
        *,
        max_terms: int,
        max_coefficient_bits: int,
        accounting: _ExactArithmeticBudget,
    ) -> None:
        self.max_terms = _positive_limit(
            max_terms, context="live determinant term budget"
        )
        self.max_coefficient_bits = _positive_limit(
            max_coefficient_bits,
            context="live determinant coefficient-bit budget",
        )
        self.terms = 0
        self.coefficient_bits = 0
        self.accounting = accounting

    @staticmethod
    def _coefficient_bits(value: Fraction) -> int:
        return sum(_fraction_bits(Fraction(value)))

    def replace(
        self,
        prior: Fraction | None,
        replacement: Fraction | None,
    ) -> None:
        terms = self.terms - (prior is not None) + (replacement is not None)
        coefficient_bits = self.coefficient_bits
        if prior is not None:
            coefficient_bits -= self._coefficient_bits(prior)
        if replacement is not None:
            coefficient_bits += self._coefficient_bits(replacement)
        self.accounting.observe_live_determinant(
            terms=terms, coefficient_bits=coefficient_bits
        )
        if terms > self.max_terms:
            self.accounting.unavailable(
                "polynomial_live_determinant_term_budget_exceeded",
                resource="live_determinant_terms",
                observed=terms,
                ceiling=self.max_terms,
            )
        if coefficient_bits > self.max_coefficient_bits:
            self.accounting.unavailable(
                "polynomial_live_determinant_coefficient_budget_exceeded",
                resource="live_determinant_coefficient_bits",
                observed=coefficient_bits,
                ceiling=self.max_coefficient_bits,
            )
        self.terms = terms
        self.coefficient_bits = coefficient_bits

    def reserve_polynomial(self, polynomial: Mapping[Exponent, Fraction]) -> None:
        for coefficient in polynomial.values():
            self.replace(None, coefficient)

    def release_polynomial(self, polynomial: Mapping[Exponent, Fraction]) -> None:
        for coefficient in polynomial.values():
            self.replace(coefficient, None)


def _add_scaled(
    target: MutableMapping[Exponent, Fraction],
    source: Mapping[Exponent, Fraction],
    scale: Fraction,
    *,
    max_terms: int,
    arithmetic_budget: _ExactArithmeticBudget,
    live_budget: _LiveDeterminantBudget,
) -> None:
    for exponents, coefficient in source.items():
        prior = target.get(exponents)
        scaled = arithmetic_budget.multiply(scale, coefficient)
        replacement = arithmetic_budget.add(
            prior if prior is not None else Fraction(0), scaled
        )
        stored = replacement if replacement != 0 else None
        live_budget.replace(prior, stored)
        if stored is None:
            target.pop(exponents, None)
        else:
            target[exponents] = stored
        if len(target) > max_terms:
            arithmetic_budget.unavailable(
                "polynomial_determinant_term_budget_exceeded",
                resource="determinant_polynomial_terms",
                observed=len(target),
                ceiling=max_terms,
            )


def _multiply(
    left: Mapping[Exponent, Fraction],
    right: Mapping[Exponent, Fraction],
    *,
    max_terms: int,
    arithmetic_budget: _ExactArithmeticBudget,
    live_budget: _LiveDeterminantBudget,
) -> Polynomial:
    if not left or not right:
        return {}
    product: Polynomial = {}
    for left_exponents, left_coefficient in left.items():
        for right_exponents, right_coefficient in right.items():
            exponents = tuple(
                a + b for a, b in zip(left_exponents, right_exponents, strict=True)
            )
            prior = product.get(exponents)
            multiplied = arithmetic_budget.multiply(
                left_coefficient, right_coefficient
            )
            replacement = arithmetic_budget.add(
                prior if prior is not None else Fraction(0), multiplied
            )
            stored = replacement if replacement != 0 else None
            live_budget.replace(prior, stored)
            if stored is None:
                product.pop(exponents, None)
            else:
                product[exponents] = stored
            if len(product) > max_terms:
                arithmetic_budget.unavailable(
                    "polynomial_determinant_term_budget_exceeded",
                    resource="determinant_polynomial_terms",
                    observed=len(product),
                    ceiling=max_terms,
                )
    return product


def _derivative(
    polynomial: Mapping[Exponent, Fraction],
    variable: int,
    *,
    arithmetic_budget: _ExactArithmeticBudget,
) -> Polynomial:
    derivative: Polynomial = {}
    for exponents, coefficient in polynomial.items():
        power = exponents[variable]
        if power == 0:
            continue
        lowered = list(exponents)
        lowered[variable] -= 1
        derivative[tuple(lowered)] = arithmetic_budget.multiply_integer(
            coefficient, power
        )
    return derivative


def exact_jacobian_determinant(
    components: Sequence[Mapping[Exponent, Fraction]],
    *,
    dimension: int,
    max_terms: int = MAX_EXPANDED_DETERMINANT_TERMS,
    max_exact_operations: int = MAX_DETERMINANT_EXACT_OPERATIONS,
    max_rational_bits: int = MAX_EXACT_RATIONAL_BITS,
    max_cumulative_rational_bit_work: int = (
        MAX_CUMULATIVE_RATIONAL_BIT_WORK
    ),
    max_rational_output_bytes: int = MAX_EXACT_RATIONAL_OUTPUT_BYTES,
    max_live_terms: int = MAX_LIVE_DETERMINANT_TERMS,
    max_live_coefficient_bits: int = (
        MAX_LIVE_DETERMINANT_COEFFICIENT_BITS
    ),
    _arithmetic_budget: _ExactArithmeticBudget | None = None,
) -> Polynomial:
    """Compute the full determinant by exact subset dynamic programming."""

    if len(components) != dimension or dimension < 1:
        raise ValueError("Jacobian determinant requires a square polynomial map")
    arithmetic_budget = _arithmetic_budget or _ExactArithmeticBudget(
        max_exact_operations=max_exact_operations,
        max_rational_bits=max_rational_bits,
        max_cumulative_rational_bit_work=(
            max_cumulative_rational_bit_work
        ),
        max_rational_output_bytes=max_rational_output_bytes,
        operation_reason_code=(
            "polynomial_determinant_operation_budget_exceeded"
        ),
    )
    jacobian = [
        [
            _derivative(
                component,
                variable,
                arithmetic_budget=arithmetic_budget,
            )
            for variable in range(dimension)
        ]
        for component in components
    ]
    live_budget = _LiveDeterminantBudget(
        max_terms=max_live_terms,
        max_coefficient_bits=max_live_coefficient_bits,
        accounting=arithmetic_budget,
    )
    for row in jacobian:
        for polynomial in row:
            live_budget.reserve_polynomial(polynomial)
    zero_exponent = (0,) * dimension
    unit = arithmetic_budget.admit(Fraction(1))
    states: dict[int, Polynomial] = {0: {zero_exponent: unit}}
    live_budget.reserve_polynomial(states[0])
    for row in range(dimension):
        next_states: dict[int, Polynomial] = {}
        for mask, partial in states.items():
            if mask.bit_count() != row:
                raise RuntimeError("determinant state crossed its row")
            for column in range(dimension):
                if mask & (1 << column):
                    continue
                term = _multiply(
                    partial,
                    jacobian[row][column],
                    max_terms=max_terms,
                    arithmetic_budget=arithmetic_budget,
                    live_budget=live_budget,
                )
                sign = -1 if (mask >> (column + 1)).bit_count() % 2 else 1
                target = next_states.setdefault(mask | (1 << column), {})
                try:
                    _add_scaled(
                        target,
                        term,
                        Fraction(sign),
                        max_terms=max_terms,
                        arithmetic_budget=arithmetic_budget,
                        live_budget=live_budget,
                    )
                finally:
                    live_budget.release_polynomial(term)
        for partial in states.values():
            live_budget.release_polynomial(partial)
        states = next_states
    return states.get((1 << dimension) - 1, {})


def _evaluate(
    polynomial: Mapping[Exponent, Fraction],
    point: Sequence[Fraction],
    *,
    arithmetic_budget: _ExactArithmeticBudget,
) -> Fraction:
    total = Fraction(0)
    for exponents, coefficient in polynomial.items():
        monomial = coefficient
        for coordinate, power in zip(point, exponents, strict=True):
            factor = arithmetic_budget.power(coordinate, power)
            monomial = arithmetic_budget.multiply(monomial, factor)
        total = arithmetic_budget.add(total, monomial)
    return total


def verify_rational_polynomial_map(
    candidate: Mapping[str, Any],
    *,
    predicate_ir: Mapping[str, Any],
    max_expanded_terms: int = MAX_EXPANDED_DETERMINANT_TERMS,
    max_exact_operations: int = MAX_DETERMINANT_EXACT_OPERATIONS,
    max_rational_bits: int = MAX_EXACT_RATIONAL_BITS,
    max_cumulative_rational_bit_work: int = (
        MAX_CUMULATIVE_RATIONAL_BIT_WORK
    ),
    max_rational_output_bytes: int = MAX_EXACT_RATIONAL_OUTPUT_BYTES,
    max_live_determinant_terms: int = MAX_LIVE_DETERMINANT_TERMS,
    max_live_determinant_coefficient_bits: int = (
        MAX_LIVE_DETERMINANT_COEFFICIENT_BITS
    ),
    _require_canonical_input: bool = False,
) -> dict[str, Any]:
    """Recompute one map's exact Jacobian and collision predicate."""

    arithmetic_budget = _ExactArithmeticBudget(
        max_exact_operations=max_exact_operations,
        max_rational_bits=max_rational_bits,
        max_cumulative_rational_bit_work=(
            max_cumulative_rational_bit_work
        ),
        max_rational_output_bytes=max_rational_output_bytes,
        operation_reason_code="polynomial_exact_operation_budget_exceeded",
    )
    predicate = _bind_predicate(predicate_ir)
    normalized = normalize_rational_polynomial_map(
        candidate,
        predicate_ir=predicate,
        _arithmetic_budget=arithmetic_budget,
    )
    if _require_canonical_input and normalized != dict(candidate):
        raise ValueError(
            "polynomial-map verifier requires normalized artifact bytes"
        )
    dimension = len(predicate["variables"])
    components = [
        _polynomial_from_wire(
            component,
            dimension,
            arithmetic_budget=arithmetic_budget,
        )
        for component in normalized["components"]
    ]
    determinant = exact_jacobian_determinant(
        components,
        dimension=dimension,
        max_terms=max_expanded_terms,
        max_exact_operations=max_exact_operations,
        max_rational_bits=max_rational_bits,
        max_cumulative_rational_bit_work=(
            max_cumulative_rational_bit_work
        ),
        max_rational_output_bytes=max_rational_output_bytes,
        max_live_terms=max_live_determinant_terms,
        max_live_coefficient_bits=max_live_determinant_coefficient_bits,
        _arithmetic_budget=arithmetic_budget,
    )
    points = [
        tuple(
            arithmetic_budget.admit(parse_rational(value))
            for value in point
        )
        for point in normalized["collision_inputs"]
    ]
    images = [
        tuple(
            _evaluate(
                component,
                point,
                arithmetic_budget=arithmetic_budget,
            )
            for component in components
        )
        for point in points
    ]
    all_images_equal = all(image == images[0] for image in images[1:])
    common_image = images[0] if all_images_equal else None

    required_points = int(predicate["minimum_distinct_collision_points"])
    reason_code = "predicate_satisfied"
    if len(points) < required_points:
        reason_code = "insufficient_collision_points"
    elif len(set(points)) != len(points):
        reason_code = "duplicate_collision_input"
    else:
        zero_exponent = (0,) * dimension
        if not determinant:
            reason_code = "jacobian_determinant_zero"
        elif set(determinant) != {zero_exponent}:
            reason_code = "jacobian_determinant_nonconstant"
        else:
            constant = determinant[zero_exponent]
            condition = predicate["jacobian_condition"]
            if constant == 0:
                reason_code = "jacobian_determinant_zero"
            elif (
                condition["kind"] == "equals_constant"
                and constant
                != arithmetic_budget.admit(
                    parse_rational(condition["constant"])
                )
            ):
                reason_code = "jacobian_determinant_mismatch"
            elif not all_images_equal:
                reason_code = "collision_image_mismatch"

    status = "satisfied" if reason_code == "predicate_satisfied" else "rejected"
    determinant_wire = _polynomial_wire(
        determinant, arithmetic_budget=arithmetic_budget
    )
    images_wire = [
        [arithmetic_budget.serialize(value) for value in image]
        for image in images
    ]
    common_image_wire = (
        [arithmetic_budget.serialize(value) for value in common_image]
        if common_image is not None
        else None
    )
    resource_usage = {
        "schema": "leanmill.rational_polynomial_exact_resource_usage.v1",
        "counters": arithmetic_budget.counters(),
        "limits": {
            **arithmetic_budget.limits(),
            "max_expanded_terms": max_expanded_terms,
            "max_live_determinant_coefficient_bits": (
                max_live_determinant_coefficient_bits
            ),
            "max_live_determinant_terms": max_live_determinant_terms,
        },
    }
    core = {
        "schema": VERIFICATION_RECEIPT_SCHEMA,
        "adapter_id": ADAPTER_ID,
        "normalized_map": normalized,
        "normalized_map_sha256": content_hash(normalized),
        "predicate": predicate,
        "predicate_sha256": content_hash(predicate),
        "jacobian_determinant": determinant_wire,
        "collision_inputs": normalized["collision_inputs"],
        "collision_images": images_wire,
        "common_image": common_image_wire,
        "resource_usage": resource_usage,
        "status": status,
        "reason_code": reason_code,
        "claim_scope": (
            "one_explicit_rational_polynomial_map_satisfies_the_frozen_predicate"
            if status == "satisfied"
            else "candidate_replay_only_no_construction_or_global_claim"
        ),
    }
    return {**core, "receipt_sha256": content_hash(core)}


def normalize_rational_polynomial_map_candidate(
    *,
    descriptor: Mapping[str, Any],
    artifact: Mapping[str, Any],
    predicate_ir: Mapping[str, Any],
    witness_schema: Mapping[str, Any],
) -> dict[str, Any]:
    expected_descriptor = {
        "adapter_id": ADAPTER_ID,
        "capability_id": NORMALIZER_CAPABILITY,
        "contract": {
            "kind": "canonical_sparse_polynomial_map",
            "coefficient_domain": "Q",
            "monomial_order": "graded_lex_ascending",
            "combine_duplicate_monomials": True,
            "max_exact_operations": MAX_NORMALIZATION_EXACT_OPERATIONS,
            "max_rational_bits": MAX_EXACT_RATIONAL_BITS,
            "max_cumulative_rational_bit_work": (
                MAX_CUMULATIVE_RATIONAL_BIT_WORK
            ),
            "max_rational_output_bytes": MAX_EXACT_RATIONAL_OUTPUT_BYTES,
        },
    }
    if dict(descriptor) != expected_descriptor:
        raise ValueError("polynomial-map normalizer descriptor changed identity")
    predicate = _bind_predicate(predicate_ir)
    expected_schema = rational_polynomial_map_schema(
        variables=predicate["variables"]
    )
    if dict(witness_schema) != expected_schema:
        raise ValueError("polynomial-map witness schema changed identity")
    return normalize_rational_polynomial_map(artifact, predicate_ir=predicate)


def verify_rational_polynomial_map_candidate(
    *,
    descriptor: Mapping[str, Any],
    normalized_artifact: Mapping[str, Any],
    predicate_ir: Mapping[str, Any],
    witness_schema: Mapping[str, Any],
) -> dict[str, Any]:
    predicate = _bind_predicate(predicate_ir)
    contract = descriptor.get("contract") if isinstance(descriptor, Mapping) else None
    if (
        not isinstance(contract, Mapping)
        or set(descriptor) != {"adapter_id", "capability_id", "contract"}
        or descriptor.get("adapter_id") != ADAPTER_ID
        or descriptor.get("capability_id") != VERIFIER_CAPABILITY
        or set(contract)
        != {
            "kind",
            "determinant_algorithm",
            "max_expanded_terms",
            "max_exact_operations",
            "max_rational_bits",
            "max_cumulative_rational_bit_work",
            "max_rational_output_bytes",
            "max_live_determinant_terms",
            "max_live_determinant_coefficient_bits",
        }
        or contract.get("kind")
        != "exact_full_jacobian_and_collision_replay"
        or contract.get("determinant_algorithm")
        != "subset_dynamic_programming"
        or type(contract.get("max_expanded_terms")) is not int
        or int(contract["max_expanded_terms"])
        != MAX_EXPANDED_DETERMINANT_TERMS
        or type(contract.get("max_exact_operations")) is not int
        or int(contract["max_exact_operations"])
        != MAX_DETERMINANT_EXACT_OPERATIONS
        or type(contract.get("max_rational_bits")) is not int
        or int(contract["max_rational_bits"]) != MAX_EXACT_RATIONAL_BITS
        or type(contract.get("max_cumulative_rational_bit_work")) is not int
        or int(contract["max_cumulative_rational_bit_work"])
        != MAX_CUMULATIVE_RATIONAL_BIT_WORK
        or type(contract.get("max_rational_output_bytes")) is not int
        or int(contract["max_rational_output_bytes"])
        != MAX_EXACT_RATIONAL_OUTPUT_BYTES
        or type(contract.get("max_live_determinant_terms")) is not int
        or int(contract["max_live_determinant_terms"])
        != MAX_LIVE_DETERMINANT_TERMS
        or type(contract.get("max_live_determinant_coefficient_bits"))
        is not int
        or int(contract["max_live_determinant_coefficient_bits"])
        != MAX_LIVE_DETERMINANT_COEFFICIENT_BITS
    ):
        raise ValueError("polynomial-map verifier descriptor changed identity")
    expected_schema = rational_polynomial_map_schema(
        variables=predicate["variables"]
    )
    if dict(witness_schema) != expected_schema:
        raise ValueError("polynomial-map verifier witness schema changed identity")
    receipt = verify_rational_polynomial_map(
        normalized_artifact,
        predicate_ir=predicate,
        max_expanded_terms=int(contract["max_expanded_terms"]),
        max_exact_operations=int(contract["max_exact_operations"]),
        max_rational_bits=int(contract["max_rational_bits"]),
        max_cumulative_rational_bit_work=int(
            contract["max_cumulative_rational_bit_work"]
        ),
        max_rational_output_bytes=int(contract["max_rational_output_bytes"]),
        max_live_determinant_terms=int(
            contract["max_live_determinant_terms"]
        ),
        max_live_determinant_coefficient_bits=int(
            contract["max_live_determinant_coefficient_bits"]
        ),
        _require_canonical_input=True,
    )
    return {
        "outcome": "accepted" if receipt["status"] == "satisfied" else "rejected",
        "observed": receipt,
        "evidence_refs": [
            "rational-polynomial-map-verification:" + receipt["receipt_sha256"]
        ],
    }


def _construction_target(adapter_config: Mapping[str, Any]) -> dict[str, Any]:
    raw = adapter_config.get("construction_target")
    required = {
        "schema",
        "variables",
        "jacobian_condition",
        "minimum_distinct_collision_points",
        "target_snapshot_sha256",
    }
    if not isinstance(raw, Mapping) or set(raw) != required:
        raise ValueError("polynomial-map adapter requires one construction_target")
    if raw.get("schema") != TARGET_CONFIG_SCHEMA:
        raise ValueError("polynomial-map construction target schema is unsupported")
    predicate = rational_polynomial_map_predicate(
        variables=raw.get("variables"),
        jacobian_condition=raw.get("jacobian_condition"),
        minimum_distinct_collision_points=raw.get(
            "minimum_distinct_collision_points"
        ),
        target_snapshot_sha256=str(raw.get("target_snapshot_sha256") or ""),
    )
    return {
        "variables": predicate["variables"],
        "jacobian_condition": predicate["jacobian_condition"],
        "minimum_distinct_collision_points": predicate[
            "minimum_distinct_collision_points"
        ],
        "target_snapshot_sha256": predicate["target_snapshot_sha256"],
    }


def _construction_interface(adapter_config: Mapping[str, Any]) -> dict[str, Any]:
    target = _construction_target(adapter_config)
    return rational_polynomial_map_witness_construction_interface(
        **target,
        target_config_sha256=content_hash(dict(adapter_config)),
    )


def _evidence_panel(adapter_config: Mapping[str, Any]) -> dict[str, Any]:
    raw = adapter_config.get("evidence_panel")
    required = {
        "schema",
        "completeness_scope",
        "completeness_ref",
        "objects",
        "hypotheses",
    }
    if not isinstance(raw, Mapping) or set(raw) != required:
        raise ValueError("polynomial-map adapter requires one exact evidence_panel")
    if (
        raw.get("schema") != EVIDENCE_PANEL_SCHEMA
        or raw.get("completeness_scope") != "declared_control_panel_only"
    ):
        raise ValueError("polynomial-map evidence panel identity is unsupported")
    completeness_ref = str(raw.get("completeness_ref") or "").strip()
    if not completeness_ref:
        raise ValueError("polynomial-map evidence panel requires a completeness_ref")
    return {
        "completeness_ref": completeness_ref,
        "objects": list(raw.get("objects") or ()),
        "hypotheses": list(raw.get("hypotheses") or ()),
    }


def preflight_blueprint(
    signature: TheorySignature,
    *,
    adapter_config: Mapping[str, Any],
    formula_grammar: Mapping[str, Any],
    strata: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if set(adapter_config) != {"construction_target", "evidence_panel"}:
        raise ValueError(
            "polynomial-map campaign adapter configuration fields changed identity"
        )
    _construction_target(adapter_config)
    from ztare.leanmill.adapters.generic_finite_evidence import (
        preflight_blueprint as preflight_evidence_panel,
    )

    result = preflight_evidence_panel(
        signature,
        adapter_config=_evidence_panel(adapter_config),
        formula_grammar=formula_grammar,
        strata=strata,
    )
    return {
        **result,
        "adapter_id": ADAPTER_ID,
        "completeness_scope": "declared_control_panel_only",
        "claim_boundary": (
            "exact incidence over the declared control panel; no completeness "
            "claim over rational polynomial maps or construction grammars"
        ),
        "target_config_sha256": content_hash(dict(adapter_config)),
    }


def build_evidence_context(
    signature: TheorySignature,
    *,
    adapter_config: Mapping[str, Any],
    strata: Sequence[Mapping[str, Any]],
) -> Any:
    if set(adapter_config) != {"construction_target", "evidence_panel"}:
        raise ValueError(
            "polynomial-map campaign adapter configuration fields changed identity"
        )
    _construction_target(adapter_config)
    from ztare.leanmill.adapters.generic_finite_evidence import (
        build_evidence_context as build_declared_panel,
    )
    from ztare.leanmill.evidence_theory_context import EvidenceTheoryContext

    context = build_declared_panel(
        signature,
        adapter_config=_evidence_panel(adapter_config),
        strata=strata,
    )
    return EvidenceTheoryContext(
        signature=context.signature,
        adapter_id=ADAPTER_ID,
        incidence=context.incidence,
        formula_profiles=context.formula_profiles,
        object_records=context.object_records,
        completeness_receipt_digest=context.completeness_receipt_digest,
        base_axioms=context.base_axioms,
    )


def theory_task_capabilities(
    *, adapter_config: Mapping[str, Any]
) -> tuple[dict[str, Any], ...]:
    return (
        {
            "capability_id": "governed_witness_construction",
            "purpose": (
                "canonically normalize and exactly verify one sparse rational "
                "polynomial map against the frozen Jacobian and collision predicate"
            ),
            "use_when": (
                "the campaign has authored explicit polynomial coefficients and "
                "collision inputs; exact host replay remains open"
            ),
            "interface": _construction_interface(adapter_config),
        },
    )


def compile_theory_task(
    *,
    request: Mapping[str, Any],
    context: Any,
    adapter_config: Mapping[str, Any],
) -> dict[str, Any] | None:
    from ztare.leanmill.witness_construction_boundary import (
        compile_governed_witness_construction_task,
    )

    return compile_governed_witness_construction_task(
        request=request,
        context=context,
        adapter_id=ADAPTER_ID,
        construction_interface=_construction_interface(adapter_config),
    )


def adjudicate_theory_task(
    *, contract: Any, boundary_result: Mapping[str, Any]
) -> Any:
    from ztare.leanmill.witness_construction_boundary import (
        GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR,
        adjudicate_governed_witness_construction_task,
    )

    if contract.adjudicator_id != GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR:
        raise KeyError(
            "unsupported polynomial-map task adjudicator: "
            f"{contract.adjudicator_id}"
        )
    return adjudicate_governed_witness_construction_task(
        contract=contract,
        boundary_result=boundary_result,
    )


CAPABILITIES = {
    NORMALIZER_CAPABILITY: normalize_rational_polynomial_map_candidate,
    VERIFIER_CAPABILITY: verify_rational_polynomial_map_candidate,
    "theory_task_compiler": compile_theory_task,
    "task_discharge_adjudicator": adjudicate_theory_task,
}

from ztare.leanmill.adapters.construction_backends import (  # noqa: E402
    finite_rational_polynomial as _finite_rational_construction,
    finite_prime_polynomial as _finite_prime_construction,
)

CAPABILITIES.update({
    _finite_rational_construction.FINITE_EXACT_BACKEND_ID:
        _finite_rational_construction.capability,
    _finite_rational_construction.GROEBNER_RATIONAL_BACKEND_ID:
        _finite_rational_construction.capability,
    _finite_prime_construction.CAPABILITY_ID:
        _finite_prime_construction.capability,
    _finite_prime_construction.MAP_REDUCTION_VERIFIER_CAPABILITY:
        _finite_prime_construction.verify_rational_polynomial_map_prime_reduction,
})

CAPABILITY_CONTRACTS = {
    _finite_rational_construction.FINITE_EXACT_BACKEND_ID: {
        "role": "construction_backend",
        "contract": dict(_finite_rational_construction.FINITE_EXACT_BACKEND["contract"]),
        "contract_sha256": content_hash(
            _finite_rational_construction.FINITE_EXACT_BACKEND["contract"]
        ),
    },
    _finite_rational_construction.GROEBNER_RATIONAL_BACKEND_ID: {
        "role": "construction_backend",
        "contract": dict(_finite_rational_construction.GROEBNER_RATIONAL_BACKEND["contract"]),
        "contract_sha256": content_hash(
            _finite_rational_construction.GROEBNER_RATIONAL_BACKEND["contract"]
        ),
    },
    _finite_prime_construction.CAPABILITY_ID: {
        "role": "construction_backend",
        "contract": dict(_finite_prime_construction.CONTRACT),
        "contract_sha256": content_hash(_finite_prime_construction.CONTRACT),
    },
}


__all__ = [
    "ADAPTER_ID",
    "CAPABILITIES",
    "EVIDENCE_PANEL_SCHEMA",
    "MAX_COLLISION_POINTS",
    "MAX_COMPONENT_TERMS",
    "MAX_CUMULATIVE_RATIONAL_BIT_WORK",
    "MAX_DETERMINANT_EXACT_OPERATIONS",
    "MAX_DIMENSION",
    "MAX_EXACT_RATIONAL_BITS",
    "MAX_EXACT_RATIONAL_DECIMAL_DIGITS",
    "MAX_EXACT_RATIONAL_OUTPUT_BYTES",
    "MAX_EXPANDED_DETERMINANT_TERMS",
    "MAX_LIVE_DETERMINANT_COEFFICIENT_BITS",
    "MAX_LIVE_DETERMINANT_TERMS",
    "MAX_NORMALIZATION_EXACT_OPERATIONS",
    "MAX_RATIONAL_WIRE_LENGTH",
    "NORMALIZER_CAPABILITY",
    "POLYNOMIAL_MAP_SCHEMA",
    "PREDICATE_SCHEMA",
    "RationalPolynomialMapArtifactError",
    "TARGET_CONFIG_SCHEMA",
    "VERIFICATION_RECEIPT_SCHEMA",
    "VERIFIER_CAPABILITY",
    "build_evidence_context",
    "exact_jacobian_determinant",
    "format_rational",
    "normalize_rational_polynomial_map",
    "normalize_rational_polynomial_map_candidate",
    "parse_rational",
    "preflight_blueprint",
    "rational_polynomial_map_predicate",
    "rational_polynomial_map_schema",
    "rational_polynomial_map_witness_construction_interface",
    "theory_task_capabilities",
    "verify_rational_polynomial_map",
    "verify_rational_polynomial_map_candidate",
]
