from __future__ import annotations

import copy
from fractions import Fraction
import inspect
from itertools import permutations
from pathlib import Path
from types import SimpleNamespace

import pytest

from ztare.common.task_discharge import TaskDischargeContract
from ztare.leanmill.adapters import (
    rational_polynomial_map as rational_adapter_module,
)
from ztare.leanmill.adapters.rational_polynomial_map import (
    ADAPTER_ID,
    EVIDENCE_PANEL_SCHEMA,
    MAX_DETERMINANT_EXACT_OPERATIONS,
    MAX_CUMULATIVE_RATIONAL_BIT_WORK,
    MAX_EXACT_RATIONAL_BITS,
    MAX_EXACT_RATIONAL_DECIMAL_DIGITS,
    MAX_EXACT_RATIONAL_OUTPUT_BYTES,
    MAX_EXPANDED_DETERMINANT_TERMS,
    MAX_LIVE_DETERMINANT_COEFFICIENT_BITS,
    MAX_LIVE_DETERMINANT_TERMS,
    MAX_NORMALIZATION_EXACT_OPERATIONS,
    MAX_RATIONAL_WIRE_LENGTH,
    NORMALIZER_CAPABILITY,
    POLYNOMIAL_MAP_SCHEMA,
    RationalPolynomialMapArtifactError,
    TARGET_CONFIG_SCHEMA,
    VERIFIER_CAPABILITY,
    build_evidence_context,
    exact_jacobian_determinant,
    normalize_rational_polynomial_map_candidate,
    preflight_blueprint,
    rational_polynomial_map_predicate,
    theory_task_capabilities,
    verify_rational_polynomial_map,
    verify_rational_polynomial_map_candidate,
)
from ztare.leanmill.theory_adapter_registry import (
    adjudicate_theory_adapter_task,
    materialize_theory_adapter_capability,
    registered_theory_adapter_ids,
    theory_task_capability_catalog,
)
from ztare.leanmill.theory_ir import SortDecl, TheorySignature, content_hash
from ztare.leanmill.witness_construction_boundary import (
    WitnessConstructionCapabilityUnavailable,
    build_witness_constructor_output,
    build_witness_constructor_request,
    execute_registered_witness_artifact,
    execute_governed_witness_construction_task,
    validate_witness_construction_boundary_result,
)


REPO = Path(__file__).resolve().parents[1]


def _term(coefficient: str, *exponents: int) -> dict:
    return {"coefficient": coefficient, "exponents": list(exponents)}


def _published_map() -> dict:
    # Expanded form of the public three-variable counterexample fixture.
    return {
        "schema": POLYNOMIAL_MAP_SCHEMA,
        "coefficient_domain": "Q",
        "variables": ["x", "y", "z"],
        "components": [
            {
                "terms": [
                    _term("1", 0, 0, 1),
                    _term("3", 1, 1, 1),
                    _term("3", 2, 2, 1),
                    _term("1", 3, 3, 1),
                    _term("4", 0, 2, 0),
                    _term("7", 1, 3, 0),
                    _term("3", 2, 4, 0),
                ]
            },
            {
                "terms": [
                    _term("1", 0, 1, 0),
                    _term("3", 1, 0, 1),
                    _term("6", 2, 1, 1),
                    _term("3", 3, 2, 1),
                    _term("12", 1, 2, 0),
                    _term("9", 2, 3, 0),
                ]
            },
            {
                "terms": [
                    _term("2", 1, 0, 0),
                    _term("-3", 2, 1, 0),
                    _term("-1", 3, 0, 1),
                ]
            },
        ],
        "collision_inputs": [
            ["0", "0", "-1/4"],
            ["1", "-3/2", "13/2"],
            ["-1", "3/2", "13/2"],
        ],
    }


def _factorized_public_map(point: tuple[Fraction, Fraction, Fraction]) -> tuple:
    x, y, z = point
    unit = 1 + x * y
    return (
        unit**3 * z + y**2 * unit * (4 + 3 * x * y),
        y + 3 * x * unit**2 * z + 3 * x * y**2 * (4 + 3 * x * y),
        2 * x - 3 * x**2 * y - x**3 * z,
    )


def _evaluate_sparse_wire(component: dict, point: tuple[Fraction, ...]) -> Fraction:
    total = Fraction(0)
    for term in component["terms"]:
        value = Fraction(term["coefficient"])
        for coordinate, exponent in zip(
            point, term["exponents"], strict=True
        ):
            value *= coordinate**exponent
        total += value
    return total


def _target_config(*, constant: str | None = "-2") -> dict:
    condition = (
        {"kind": "constant_nonzero"}
        if constant is None
        else {"kind": "equals_constant", "constant": constant}
    )
    return {
        "construction_target": {
            "schema": TARGET_CONFIG_SCHEMA,
            "variables": ["x", "y", "z"],
            "jacobian_condition": condition,
            "minimum_distinct_collision_points": 2,
            "target_snapshot_sha256": "a" * 64,
        }
    }


def _campaign_config() -> dict:
    return {
        **_target_config(),
        "evidence_panel": {
            "schema": EVIDENCE_PANEL_SCHEMA,
            "completeness_scope": "declared_control_panel_only",
            "completeness_ref": "fixture:rational-polynomial-map-controls",
            "objects": [
                {
                    "object_id": "control:published-map",
                    "stratum_id": "matched_positive",
                    "payload": {"artifact_ref": "fixture:published-map"},
                },
                {
                    "object_id": "control:perturbed-map",
                    "stratum_id": "matched_negative",
                    "payload": {"artifact_ref": "fixture:perturbed-map"},
                },
            ],
            "hypotheses": [
                {
                    "hypothesis_id": "property:constant-jacobian-collision",
                    "satisfied_object_ids": ["control:published-map"],
                    "anonymous_shape": {
                        "kind": "exact_polynomial_map_property",
                        "complexity": 1,
                    },
                    "payload": {"checker_ref": "polynomial-map:exact"},
                }
            ],
        },
    }


def _interface(*, constant: str | None = "-2") -> dict:
    return theory_task_capabilities(
        adapter_config=_target_config(constant=constant)
    )[0]["interface"]


def _callbacks(interface: dict, artifact: dict) -> tuple[dict, dict]:
    normalizer = {"adapter_id": ADAPTER_ID, **interface["normalizer"]}
    verifier = {"adapter_id": ADAPTER_ID, **interface["verifier"]}
    normalized = normalize_rational_polynomial_map_candidate(
        descriptor=normalizer,
        artifact=artifact,
        predicate_ir=interface["predicate_ir"],
        witness_schema=interface["witness_schema"],
    )
    result = verify_rational_polynomial_map_candidate(
        descriptor=verifier,
        normalized_artifact=normalized,
        predicate_ir=interface["predicate_ir"],
        witness_schema=interface["witness_schema"],
    )
    return normalized, result


def _reference_polynomial_product(left: dict, right: dict) -> dict:
    product: dict[tuple[int, ...], Fraction] = {}
    for left_exponents, left_coefficient in left.items():
        for right_exponents, right_coefficient in right.items():
            exponents = tuple(
                left_power + right_power
                for left_power, right_power in zip(
                    left_exponents, right_exponents, strict=True
                )
            )
            product[exponents] = product.get(exponents, Fraction(0)) + (
                left_coefficient * right_coefficient
            )
            if product[exponents] == 0:
                del product[exponents]
    return product


def _reference_jacobian_determinant(components: tuple[dict, ...]) -> dict:
    """Small-test Leibniz expansion, independent of the adapter's subset DP."""

    dimension = len(components)
    derivatives: list[list[dict]] = []
    for component in components:
        row = []
        for variable in range(dimension):
            derivative = {}
            for exponents, coefficient in component.items():
                power = exponents[variable]
                if power:
                    lowered = list(exponents)
                    lowered[variable] -= 1
                    derivative[tuple(lowered)] = coefficient * power
            row.append(derivative)
        derivatives.append(row)
    determinant: dict[tuple[int, ...], Fraction] = {}
    unit = {(0,) * dimension: Fraction(1)}
    for permutation in permutations(range(dimension)):
        inversions = sum(
            permutation[left] > permutation[right]
            for left in range(dimension)
            for right in range(left + 1, dimension)
        )
        term = unit
        for row, column in enumerate(permutation):
            term = _reference_polynomial_product(
                term, derivatives[row][column]
            )
        sign = Fraction(-1 if inversions % 2 else 1)
        for exponents, coefficient in term.items():
            determinant[exponents] = determinant.get(
                exponents, Fraction(0)
            ) + sign * coefficient
            if determinant[exponents] == 0:
                del determinant[exponents]
    return determinant


def test_public_map_recomputes_constant_jacobian_and_collision_exactly() -> None:
    normalized, result = _callbacks(_interface(), _published_map())
    observed = result["observed"]

    assert result["outcome"] == "accepted"
    assert observed["reason_code"] == "predicate_satisfied"
    assert observed["jacobian_determinant"] == {
        "terms": [_term("-2", 0, 0, 0)]
    }
    assert observed["common_image"] == ["-1/4", "0", "0"]
    assert observed["collision_inputs"] == normalized["collision_inputs"]
    assert observed["normalized_map"] == normalized
    assert observed["predicate"] == _interface()["predicate_ir"]
    receipt_core = {
        key: value
        for key, value in observed.items()
        if key != "receipt_sha256"
    }
    assert observed["receipt_sha256"] == content_hash(receipt_core)


def test_sparse_fixture_is_the_exact_expansion_of_the_public_formula() -> None:
    normalized, _result = _callbacks(_interface(), _published_map())
    points = (
        (Fraction(0), Fraction(0), Fraction(-1, 4)),
        (Fraction(1), Fraction(-3, 2), Fraction(13, 2)),
        (Fraction(-1), Fraction(3, 2), Fraction(13, 2)),
        (Fraction(2), Fraction(-1, 3), Fraction(5, 7)),
    )
    for point in points:
        sparse_image = tuple(
            _evaluate_sparse_wire(component, point)
            for component in normalized["components"]
        )
        assert sparse_image == _factorized_public_map(point)


def test_full_determinant_keeps_cross_terms_and_orientation() -> None:
    # F(x,y) = (x^2 + y, x + y^2), so det JF = 4xy - 1.
    determinant = exact_jacobian_determinant(
        (
            {(2, 0): Fraction(1), (0, 1): Fraction(1)},
            {(1, 0): Fraction(1), (0, 2): Fraction(1)},
        ),
        dimension=2,
    )
    assert determinant == {
        (0, 0): Fraction(-1),
        (1, 1): Fraction(4),
    }


def test_subset_determinant_matches_independent_leibniz_expansion_in_3d() -> None:
    components = (
        {
            (2, 1, 0): Fraction(1, 2),
            (0, 0, 1): Fraction(3),
            (1, 0, 0): Fraction(-2),
        },
        {
            (0, 2, 1): Fraction(-3, 5),
            (1, 0, 1): Fraction(4),
            (0, 1, 0): Fraction(1),
        },
        {
            (1, 1, 1): Fraction(2, 3),
            (2, 0, 0): Fraction(5),
            (0, 0, 2): Fraction(-1),
        },
    )
    assert exact_jacobian_determinant(components, dimension=3) == (
        _reference_jacobian_determinant(components)
    )


def test_normalizer_combines_terms_and_canonicalizes_rationals() -> None:
    artifact = _published_map()
    artifact["components"][2]["terms"].extend(
        [_term("2/4", 0, 0, 0), _term("-1/2", 0, 0, 0)]
    )
    artifact["collision_inputs"][0][2] = "-2/8"
    normalized, result = _callbacks(_interface(), artifact)

    assert result["outcome"] == "accepted"
    assert normalized["collision_inputs"][0][2] == "-1/4"
    assert all(
        term["exponents"] != [0, 0, 0]
        for term in normalized["components"][2]["terms"]
    )


def test_coefficient_perturbation_is_rejected_by_exact_replay() -> None:
    artifact = _published_map()
    artifact["components"][0]["terms"][0]["coefficient"] = "2"
    _normalized, result = _callbacks(_interface(), artifact)

    assert result["outcome"] == "rejected"
    assert result["observed"]["reason_code"] in {
        "jacobian_determinant_nonconstant",
        "jacobian_determinant_mismatch",
        "collision_image_mismatch",
    }


def test_nonconstant_jacobian_is_rejected_even_with_a_valid_collision() -> None:
    artifact = {
        "schema": POLYNOMIAL_MAP_SCHEMA,
        "coefficient_domain": "Q",
        "variables": ["x", "y", "z"],
        "components": [
            {"terms": [_term("1", 2, 0, 0)]},
            {"terms": [_term("1", 0, 1, 0)]},
            {"terms": [_term("1", 0, 0, 1)]},
        ],
        "collision_inputs": [["1", "0", "0"], ["-1", "0", "0"]],
    }
    _normalized, result = _callbacks(_interface(), artifact)

    assert result["outcome"] == "rejected"
    assert result["observed"]["reason_code"] == (
        "jacobian_determinant_nonconstant"
    )
    assert result["observed"]["common_image"] == ["1", "0", "0"]


def test_false_collision_and_duplicate_inputs_have_typed_rejections() -> None:
    false_collision = _published_map()
    false_collision["collision_inputs"][2] = ["0", "0", "0"]
    _normalized, result = _callbacks(_interface(), false_collision)
    assert result["outcome"] == "rejected"
    assert result["observed"]["reason_code"] == "collision_image_mismatch"
    assert result["observed"]["common_image"] is None

    duplicate = _published_map()
    duplicate["collision_inputs"] = [
        duplicate["collision_inputs"][0],
        duplicate["collision_inputs"][0],
    ]
    _normalized, result = _callbacks(_interface(), duplicate)
    assert result["outcome"] == "rejected"
    assert result["observed"]["reason_code"] == "duplicate_collision_input"


def test_declared_jacobian_constant_is_checked_exactly() -> None:
    _normalized, result = _callbacks(_interface(constant="-1"), _published_map())
    assert result["outcome"] == "rejected"
    assert result["observed"]["reason_code"] == "jacobian_determinant_mismatch"


def test_constant_nonzero_predicate_accepts_recomputed_nonzero_constant() -> None:
    _normalized, result = _callbacks(_interface(constant=None), _published_map())
    assert result["outcome"] == "accepted"
    assert result["observed"]["jacobian_determinant"] == {
        "terms": [_term("-2", 0, 0, 0)]
    }


@pytest.mark.parametrize("bad_value", ["1/0", "0.5", "1//2", 0.5])
def test_malformed_rationals_never_enter_exact_replay(bad_value: object) -> None:
    artifact = _published_map()
    artifact["components"][0]["terms"][0]["coefficient"] = bad_value
    interface = _interface()
    descriptor = {"adapter_id": ADAPTER_ID, **interface["normalizer"]}
    with pytest.raises(RationalPolynomialMapArtifactError) as caught:
        normalize_rational_polynomial_map_candidate(
            descriptor=descriptor,
            artifact=artifact,
            predicate_ir=interface["predicate_ir"],
            witness_schema=interface["witness_schema"],
        )
    assert caught.value.reason_code == "malformed_rational"


def test_rational_wire_and_determinant_work_are_bounded() -> None:
    artifact = _published_map()
    artifact["collision_inputs"][0][0] = "1" * (
        MAX_RATIONAL_WIRE_LENGTH + 1
    )
    interface = _interface()
    descriptor = {"adapter_id": ADAPTER_ID, **interface["normalizer"]}
    with pytest.raises(RationalPolynomialMapArtifactError) as caught:
        normalize_rational_polynomial_map_candidate(
            descriptor=descriptor,
            artifact=artifact,
            predicate_ir=interface["predicate_ir"],
            witness_schema=interface["witness_schema"],
        )
    assert caught.value.reason_code == "malformed_rational"
    rational_schema = interface["witness_schema"]["properties"][
        "collision_inputs"
    ]["items"]["items"]
    assert rational_schema["maxLength"] == MAX_RATIONAL_WIRE_LENGTH

    components = (
        {(2, 0): Fraction(1), (0, 1): Fraction(1)},
        {(1, 0): Fraction(1), (0, 2): Fraction(1)},
    )
    with pytest.raises(
        WitnessConstructionCapabilityUnavailable,
        match="polynomial_determinant_operation_budget_exceeded",
    ):
        exact_jacobian_determinant(
            components,
            dimension=2,
            max_exact_operations=1,
        )
    with pytest.raises(
        WitnessConstructionCapabilityUnavailable,
        match="polynomial_determinant_term_budget_exceeded",
    ):
        exact_jacobian_determinant(
            components,
            dimension=2,
            max_terms=1,
            max_exact_operations=MAX_DETERMINANT_EXACT_OPERATIONS,
        )


def test_normalizer_predictively_bounds_duplicate_rational_growth() -> None:
    def first_primes(count: int) -> list[int]:
        primes: list[int] = []
        candidate = 2
        while len(primes) < count:
            if all(candidate % prime for prime in primes if prime * prime <= candidate):
                primes.append(candidate)
            candidate += 1
        return primes

    artifact = _published_map()
    denominators = [
        prime ** max(1, 390 // prime.bit_length())
        for prime in first_primes(50)
    ]
    artifact["components"][0]["terms"] = [
        _term(f"1/{denominator}", 0, 0, 0)
        for denominator in denominators
    ]
    interface = _interface()
    descriptor = {"adapter_id": ADAPTER_ID, **interface["normalizer"]}
    with pytest.raises(
        WitnessConstructionCapabilityUnavailable,
        match="polynomial_exact_rational_bit_budget_exceeded",
    ):
        normalize_rational_polynomial_map_candidate(
            descriptor=descriptor,
            artifact=artifact,
            predicate_ir=interface["predicate_ir"],
            witness_schema=interface["witness_schema"],
        )


def test_collision_evaluation_power_is_predictively_bounded() -> None:
    interface = _interface(constant=None)
    huge = "1" + "0" * 119
    artifact = {
        "schema": POLYNOMIAL_MAP_SCHEMA,
        "coefficient_domain": "Q",
        "variables": ["x", "y", "z"],
        "components": [
            {"terms": [_term("1", 64, 0, 0)]},
            {"terms": [_term("1", 0, 1, 0)]},
            {"terms": [_term("1", 0, 0, 1)]},
        ],
        "collision_inputs": [[huge, "0", "0"], ["-" + huge, "0", "0"]],
    }
    normalized = normalize_rational_polynomial_map_candidate(
        descriptor={"adapter_id": ADAPTER_ID, **interface["normalizer"]},
        artifact=artifact,
        predicate_ir=interface["predicate_ir"],
        witness_schema=interface["witness_schema"],
    )
    with pytest.raises(
        WitnessConstructionCapabilityUnavailable,
        match="polynomial_exact_rational_bit_budget_exceeded",
    ) as caught:
        verify_rational_polynomial_map_candidate(
            descriptor={"adapter_id": ADAPTER_ID, **interface["verifier"]},
            normalized_artifact=normalized,
            predicate_ir=interface["predicate_ir"],
            witness_schema=interface["witness_schema"],
        )
    assert caught.value.resource == "rational_bits"
    assert caught.value.observed > caught.value.ceiling
    assert caught.value.counters["exact_operations"] > 0
    assert "peak_live_determinant_terms" in caught.value.counters

    registered = execute_registered_witness_artifact(
        adapter_id=ADAPTER_ID,
        witness_interface=interface,
        artifact=artifact,
        normalizer_fn=normalize_rational_polynomial_map_candidate,
        verifier_fn=verify_rational_polynomial_map_candidate,
    )
    assert registered["status"] == "unavailable"
    assert registered["verifier_outcome"] == "unavailable"
    assert registered["reason_code"] == (
        "polynomial_exact_rational_bit_budget_exceeded"
    )
    assert registered["observed"] == caught.value.to_observed()


def test_exact_rational_and_live_determinant_limits_are_typed() -> None:
    with pytest.raises(
        WitnessConstructionCapabilityUnavailable,
        match="polynomial_exact_rational_bit_budget_exceeded",
    ):
        exact_jacobian_determinant(
            ({(1,): Fraction(1, 17)},),
            dimension=1,
            max_rational_bits=4,
        )

    identity = (
        {(1, 0): Fraction(1)},
        {(0, 1): Fraction(1)},
    )
    with pytest.raises(
        WitnessConstructionCapabilityUnavailable,
        match="polynomial_live_determinant_term_budget_exceeded",
    ):
        exact_jacobian_determinant(
            identity,
            dimension=2,
            max_live_terms=4,
        )
    with pytest.raises(
        WitnessConstructionCapabilityUnavailable,
        match="polynomial_live_determinant_coefficient_budget_exceeded",
    ) as caught:
        exact_jacobian_determinant(
            identity,
            dimension=2,
            max_live_coefficient_bits=3,
        )
    assert caught.value.resource == "live_determinant_coefficient_bits"
    assert caught.value.counters[
        "peak_live_determinant_coefficient_bits"
    ] == 4


def test_cumulative_bit_work_and_rational_serialization_are_typed() -> None:
    predicate = _interface()["predicate_ir"]
    with pytest.raises(
        WitnessConstructionCapabilityUnavailable,
        match="polynomial_cumulative_rational_bit_work_budget_exceeded",
    ):
        verify_rational_polynomial_map(
            _published_map(),
            predicate_ir=predicate,
            max_cumulative_rational_bit_work=1,
        )
    with pytest.raises(
        WitnessConstructionCapabilityUnavailable,
        match="polynomial_rational_output_budget_exceeded",
    ):
        verify_rational_polynomial_map(
            _published_map(),
            predicate_ir=predicate,
            max_rational_output_bytes=1,
        )


def test_public_verifier_preflights_large_decimal_conversion() -> None:
    base = 10**75 + 1
    predicate = rational_polynomial_map_predicate(
        variables=["x"],
        jacobian_condition={"kind": "constant_nonzero"},
        minimum_distinct_collision_points=2,
        target_snapshot_sha256="e" * 64,
    )
    candidate = {
        "schema": POLYNOMIAL_MAP_SCHEMA,
        "coefficient_domain": "Q",
        "variables": ["x"],
        "components": [{"terms": [_term("1", 64)]}],
        "collision_inputs": [[str(base)], ["0"]],
    }

    with pytest.raises(WitnessConstructionCapabilityUnavailable) as caught:
        verify_rational_polynomial_map(candidate, predicate_ir=predicate)

    assert caught.value.reason_code == (
        "polynomial_decimal_digit_budget_exceeded"
    )
    assert caught.value.resource == "rational_decimal_digits"
    assert caught.value.observed == 4_801
    assert caught.value.ceiling == MAX_EXACT_RATIONAL_DECIMAL_DIGITS
    assert caught.value.counters[
        "current_projected_rational_decimal_digits"
    ] == 4_801
    assert caught.value.counters[
        "current_projected_rational_wire_bytes"
    ] == 4_801


def test_public_verifier_maps_stricter_runtime_decimal_guard(
    monkeypatch,
) -> None:
    base = 10**75 + 1
    predicate = rational_polynomial_map_predicate(
        variables=["x"],
        jacobian_condition={"kind": "constant_nonzero"},
        minimum_distinct_collision_points=2,
        target_snapshot_sha256="f" * 64,
    )
    candidate = {
        "schema": POLYNOMIAL_MAP_SCHEMA,
        "coefficient_domain": "Q",
        "variables": ["x"],
        "components": [{"terms": [_term("1", 10)]}],
        "collision_inputs": [[str(base)], ["0"]],
    }
    original = rational_adapter_module.format_rational

    def stricter_runtime_guard(value: Fraction) -> str:
        if abs(Fraction(value).numerator).bit_length() > 1_000:
            raise ValueError("simulated stricter integer conversion guard")
        return original(value)

    monkeypatch.setattr(
        rational_adapter_module,
        "format_rational",
        stricter_runtime_guard,
    )
    with pytest.raises(WitnessConstructionCapabilityUnavailable) as caught:
        verify_rational_polynomial_map(candidate, predicate_ir=predicate)

    assert caught.value.reason_code == (
        "polynomial_decimal_conversion_runtime_unavailable"
    )
    assert caught.value.resource == "rational_decimal_digits"
    assert caught.value.observed == 751
    assert caught.value.ceiling == MAX_EXACT_RATIONAL_DECIMAL_DIGITS


def test_success_and_rejection_receipts_expose_exact_resource_usage() -> None:
    interface = _interface()
    _normalized, accepted = _callbacks(interface, _published_map())
    usage = accepted["observed"]["resource_usage"]
    assert usage["schema"] == (
        "leanmill.rational_polynomial_exact_resource_usage.v1"
    )
    assert usage["counters"]["exact_operations"] > 0
    assert usage["counters"]["rational_bit_work"] > 0
    assert usage["counters"]["rational_output_bytes"] > 0
    assert usage["counters"]["peak_live_determinant_terms"] >= (
        usage["counters"]["current_live_determinant_terms"]
    )
    assert usage["limits"]["max_rational_bits"] == MAX_EXACT_RATIONAL_BITS
    assert usage["limits"]["max_decimal_digits_per_integer"] == (
        MAX_EXACT_RATIONAL_DECIMAL_DIGITS
    )

    changed = _published_map()
    changed["collision_inputs"][1][0] = "2"
    _normalized, rejected = _callbacks(interface, changed)
    assert rejected["outcome"] == "rejected"
    assert rejected["observed"]["resource_usage"]["counters"][
        "exact_operations"
    ] > 0


def test_determinant_invariant_is_not_python_assert_dependent() -> None:
    source = inspect.getsource(exact_jacobian_determinant)
    assert "assert " not in source


def test_verifier_resource_contract_cannot_be_rewritten_at_call_time() -> None:
    interface = _interface()
    normalized, _result = _callbacks(interface, _published_map())
    descriptor = {"adapter_id": ADAPTER_ID, **interface["verifier"]}
    assert descriptor["contract"]["max_expanded_terms"] == (
        MAX_EXPANDED_DETERMINANT_TERMS
    )
    assert descriptor["contract"]["max_exact_operations"] == (
        MAX_DETERMINANT_EXACT_OPERATIONS
    )
    assert descriptor["contract"]["max_rational_bits"] == (
        MAX_EXACT_RATIONAL_BITS
    )
    assert descriptor["contract"]["max_cumulative_rational_bit_work"] == (
        MAX_CUMULATIVE_RATIONAL_BIT_WORK
    )
    assert descriptor["contract"]["max_rational_output_bytes"] == (
        MAX_EXACT_RATIONAL_OUTPUT_BYTES
    )
    assert "max_decimal_digits_per_integer" not in descriptor["contract"]
    assert descriptor["contract"]["max_live_determinant_terms"] == (
        MAX_LIVE_DETERMINANT_TERMS
    )
    assert descriptor["contract"][
        "max_live_determinant_coefficient_bits"
    ] == MAX_LIVE_DETERMINANT_COEFFICIENT_BITS
    assert interface["normalizer"]["contract"]["max_exact_operations"] == (
        MAX_NORMALIZATION_EXACT_OPERATIONS
    )
    assert "max_decimal_digits_per_integer" not in inspect.signature(
        verify_rational_polynomial_map
    ).parameters
    assert "max_decimal_digits_per_integer" not in inspect.signature(
        exact_jacobian_determinant
    ).parameters
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        verify_rational_polynomial_map(
            normalized,
            predicate_ir=interface["predicate_ir"],
            **{"max_decimal_digits_per_integer": 10_000},
        )
    crossed = copy.deepcopy(descriptor)
    crossed["contract"]["max_exact_operations"] += 1
    with pytest.raises(ValueError, match="descriptor changed identity"):
        verify_rational_polynomial_map_candidate(
            descriptor=crossed,
            normalized_artifact=normalized,
            predicate_ir=interface["predicate_ir"],
            witness_schema=interface["witness_schema"],
        )


def test_candidate_cannot_supply_derived_or_authority_fields() -> None:
    interface = _interface()
    descriptor = {"adapter_id": ADAPTER_ID, **interface["normalizer"]}

    supplied = _published_map()
    supplied["jacobian_determinant"] = "-2"
    with pytest.raises(RationalPolynomialMapArtifactError) as caught:
        normalize_rational_polynomial_map_candidate(
            descriptor=descriptor,
            artifact=supplied,
            predicate_ir=interface["predicate_ir"],
            witness_schema=interface["witness_schema"],
        )
    assert caught.value.reason_code == "candidate_supplied_derived_certificate"

    authority = _published_map()
    authority["verification_authority"] = "candidate"
    with pytest.raises(RationalPolynomialMapArtifactError) as caught:
        normalize_rational_polynomial_map_candidate(
            descriptor=descriptor,
            artifact=authority,
            predicate_ir=interface["predicate_ir"],
            witness_schema=interface["witness_schema"],
        )
    assert caught.value.reason_code == "unknown_authority_field"

    nested = _published_map()
    nested["components"][0]["terms"][0]["certificate"] = {"det": "-2"}
    with pytest.raises(RationalPolynomialMapArtifactError) as caught:
        normalize_rational_polynomial_map_candidate(
            descriptor=descriptor,
            artifact=nested,
            predicate_ir=interface["predicate_ir"],
            witness_schema=interface["witness_schema"],
        )
    assert caught.value.reason_code == "candidate_supplied_derived_certificate"

    crossed_predicate = copy.deepcopy(interface["predicate_ir"])
    crossed_predicate["authority"] = "candidate"
    with pytest.raises(ValueError, match="predicate field mismatch"):
        normalize_rational_polynomial_map_candidate(
            descriptor=descriptor,
            artifact=_published_map(),
            predicate_ir=crossed_predicate,
            witness_schema=interface["witness_schema"],
        )


def test_registered_catalog_binds_interface_to_full_target_config() -> None:
    config = _target_config()
    assert ADAPTER_ID in registered_theory_adapter_ids()
    catalog = theory_task_capability_catalog(ADAPTER_ID, adapter_config=config)
    assert len(catalog) == 1
    assert catalog[0]["capability_id"] == "governed_witness_construction"
    assert catalog[0]["interface"]["target_config_sha256"] == content_hash(config)
    assert catalog[0]["interface"]["predicate_ir"]["jacobian_condition"] == {
        "kind": "equals_constant",
        "constant": "-2",
    }


def test_registered_adapter_is_vps_sync_allowlisted() -> None:
    entries = {
        line.strip()
        for line in (REPO / "deploy/vps_sync_files.txt").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert (
        "src/ztare/leanmill/adapters/rational_polynomial_map.py" in entries
    )
    assert "src/ztare/leanmill/theory_adapter_registry.py" in entries


def test_declared_panel_preflight_keeps_construction_search_outside_adapter() -> None:
    signature = TheorySignature(
        name="RationalPolynomialMapObservation",
        sorts=(SortDecl("Observation"),),
    )
    config = _campaign_config()
    preflight = preflight_blueprint(
        signature,
        adapter_config=config,
        formula_grammar={"kind": "declared_executable_hypothesis_panel"},
        strata=({"stratum_id": "declared_controls"},),
    )
    context = build_evidence_context(
        signature,
        adapter_config=config,
        strata=({"stratum_id": "declared_controls"},),
    )
    assert preflight["complete_census_available"] is True
    assert preflight["completeness_scope"] == "declared_control_panel_only"
    assert context.adapter_id == ADAPTER_ID
    assert context.object_ids == (
        "control:perturbed-map",
        "control:published-map",
    )


def _shared_boundary_trace(artifact: dict) -> tuple[dict, object]:
    config = _target_config()
    interface = theory_task_capability_catalog(
        ADAPTER_ID, adapter_config=config
    )[0]["interface"]
    context = SimpleNamespace(
        context_hash="context:rational-polynomial-map",
        formula_ids=("property:constant-jacobian-collision",),
    )
    intent = {
        "presentation_formula_ids": ["property:constant-jacobian-collision"],
        "goal": "Construct one exact rational polynomial map.",
        "observable": "The registered exact predicate accepts it.",
        "evidence_refs": ["selection:public-conformance-fixture"],
        "kill_condition": "Reject any failed coefficient or collision identity.",
        "construction_brief": "Author sparse coefficients and collision inputs.",
    }
    constructor_request = build_witness_constructor_request(
        context_hash=context.context_hash,
        adapter_id=ADAPTER_ID,
        construction_interface=interface,
        task_intent=intent,
    )
    authored = build_witness_constructor_output(
        constructor_request,
        artifact=artifact,
        orientation={
            "eigenquestion": "Does the supplied map satisfy the frozen predicate?",
            "representation_choice": "Use canonical sparse rational coordinates.",
            "expected_failure_mode": "An exact determinant or collision may fail.",
            "next_revision_if_rejected": "Return the typed failure to navigation.",
        },
        role="witness_constructor",
        agent_id="polynomial-map-conformance-author",
        call_receipt_sha256="c" * 64,
    )
    public_fields = (
        "predicate_ir",
        "witness_schema",
        "normalizer",
        "verifier",
        "discharge_policy",
        "target_config_sha256",
        "interface_sha256",
    )
    core = {
        "schema": "leanmill.theory_task_request.v1",
        "context_hash": context.context_hash,
        "context_epoch": 0,
        "presentation_formula_ids": intent["presentation_formula_ids"],
        "goal": intent["goal"],
        "observable": intent["observable"],
        "adjudicator_capability": "governed_witness_construction",
        "evidence_refs": intent["evidence_refs"]
        + [
            "witness-constructor-authorship:"
            + authored["authorship_receipt"]["receipt_sha256"]
        ],
        "kill_condition": intent["kill_condition"],
        "authority": "leaf_request_host_bound",
        "witness_construction": {
            **{field: interface[field] for field in public_fields},
            "constructor_request": constructor_request,
            "artifact": authored["artifact"],
            "orientation": authored["orientation"],
            "authorship_receipt": authored["authorship_receipt"],
        },
    }
    request = {
        **core,
        "request_id": "theory-task-request:" + content_hash(core),
    }
    lowered = materialize_theory_adapter_capability(
        ADAPTER_ID,
        "theory_task_compiler",
        request=request,
        context=context,
        adapter_config=config,
    )
    assert lowered is not None
    contract = TaskDischargeContract(
        contract_id="task:rational-polynomial-map",
        adjudicator_id=lowered["adjudicator_id"],
        lifecycle_scope="campaign:polynomial-map-conformance",
        owner="lineage:public-fixture",
        parameters=lowered["parameters"],
    )
    boundary = execute_governed_witness_construction_task(
        contract,
        normalizer_fn=lambda **kwargs: materialize_theory_adapter_capability(
            ADAPTER_ID, NORMALIZER_CAPABILITY, **kwargs
        ),
        verifier_fn=lambda **kwargs: materialize_theory_adapter_capability(
            ADAPTER_ID, VERIFIER_CAPABILITY, **kwargs
        ),
    )
    validated = validate_witness_construction_boundary_result(contract, boundary)
    outer_core = {
        "schema": "leanmill.frontier_boundary_result.v1",
        "context_hash": context.context_hash,
        "query_results": [validated],
        "stop_reason": "completed",
        "next_epoch_proposal": None,
    }
    outer_boundary = {
        **outer_core,
        "result_sha256": content_hash(outer_core),
    }
    discharge = adjudicate_theory_adapter_task(
        ADAPTER_ID,
        contract,
        boundary_result=outer_boundary,
    )
    return validated, discharge


def test_public_fixture_executes_through_shared_witness_boundary() -> None:
    validated, discharge = _shared_boundary_trace(_published_map())
    assert validated["status"] == "witness_verified"
    assert validated["verification_receipt"]["observed"]["common_image"] == [
        "-1/4",
        "0",
        "0",
    ]
    assert discharge.status == "open"
    assert discharge.authority == "leanmill.frontier_boundary"
    assert discharge.observed["boundary_status"] == "witness_verified"
    assert discharge.observed["next_obligation"] == (
        "construction_artifact_ratification"
    )


def test_exact_rejection_returns_typed_cegis_feedback_through_discharge() -> None:
    artifact = _published_map()
    artifact["collision_inputs"][2] = ["0", "0", "0"]
    validated, discharge = _shared_boundary_trace(artifact)

    assert validated["status"] == "witness_rejected"
    observed = validated["verification_receipt"]["observed"]
    assert observed["reason_code"] == "collision_image_mismatch"
    assert observed["jacobian_determinant"] == {
        "terms": [_term("-2", 0, 0, 0)]
    }
    assert observed["common_image"] is None
    assert discharge.status == "open"
    assert discharge.observed["boundary_status"] == "witness_rejected"
    assert discharge.observed["verifier_observed"]["reason_code"] == (
        "collision_image_mismatch"
    )
    assert discharge.observed["next_obligation"] is None
