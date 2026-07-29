from __future__ import annotations

from copy import deepcopy

import pytest

from ztare.leanmill.adapters.construction_backends import (
    finite_prime_polynomial as prime_backend,
)
from ztare.leanmill.adapters.construction_backends.finite_rational_polynomial import (
    build_exact_constraint_system,
)
from ztare.leanmill.adapters.rational_polynomial_map import (
    ADAPTER_ID,
    POLYNOMIAL_MAP_SCHEMA,
    rational_polynomial_map_witness_construction_interface,
)
from ztare.leanmill.construction_parameterization import (
    SAFE_ARTIFACT_TEMPLATE_SCHEMA,
    ConstructionParameterizationError,
    admit_persisted_construction_execution,
    build_construction_parameterization,
    construction_parameterization_authoring_contract,
    execute_construction_parameterization,
)
from ztare.leanmill.theory_adapter_registry import (
    materialize_theory_adapter_capability,
)
from ztare.leanmill.theory_ir import content_hash


def _term(coefficient, *exponents: int) -> dict:
    return {"coefficient": coefficient, "exponents": list(exponents)}


def _common_limits() -> dict[str, int]:
    return {
        "max_assignments": 16,
        "max_template_nodes": 1_000,
        "max_template_bytes": 40_000,
        "max_materialized_artifact_bytes": 100_000,
        "max_execution_receipt_bytes": 1_000_000,
        "max_materialized_family_bytes": 4_000_000,
    }


def _source_limits() -> dict[str, int]:
    return {
        "max_constraints": 8,
        "max_constraint_evaluations": 1_000,
        "max_terms_per_polynomial": 8,
        "max_exponent": 8,
        "max_exact_operations": 1_000,
        "max_rational_bits": 256,
        "max_cumulative_rational_bit_work": 100_000,
        "max_rational_output_bytes": 10_000,
    }


def _polynomial(*terms: tuple[str, list[int]]) -> dict:
    return {
        "schema": "leanmill.exact_sparse_polynomial.v1",
        "terms": [
            {"coefficient": coefficient, "exponents": exponents}
            for coefficient, exponents in terms
        ],
    }


def _interface() -> dict:
    return rational_polynomial_map_witness_construction_interface(
        variables=["x", "y", "z"],
        jacobian_condition={"kind": "constant_nonzero"},
        minimum_distinct_collision_points=2,
        target_snapshot_sha256="a" * 64,
        target_config_sha256="b" * 64,
    )


def _space(domain: list[str]) -> dict:
    return {
        "schema": "leanmill.explicit_finite_parameter_space.v1",
        "variables": [{
            "parameter_id": "a",
            "sort": "rational",
            "domain": domain,
        }],
    }


def _template() -> dict:
    return {
        "schema": POLYNOMIAL_MAP_SCHEMA,
        "coefficient_domain": "Q",
        "variables": ["x", "y", "z"],
        "components": [
            {"terms": [_term({"$parameter": "a"}, 1, 0, 0)]},
            {"terms": [_term("1", 0, 1, 0)]},
            {"terms": [_term("1", 0, 0, 1)]},
        ],
        "collision_inputs": [["0", "0", "0"], ["1", "0", "0"]],
    }


def _descriptor() -> dict[str, str]:
    return {
        "adapter_id": ADAPTER_ID,
        "capability_id": prime_backend.CAPABILITY_ID,
        "contract_sha256": content_hash(prime_backend.CONTRACT),
    }


def _parameterization(
    *,
    domain: list[str],
    constraints: list[dict],
    characteristic: int,
    guards: list[dict] | None = None,
) -> tuple[dict, dict]:
    space = _space(domain)
    source = build_exact_constraint_system(
        parameter_ids=["a"],
        constraints=constraints,
        backend_resource_limits=_source_limits(),
    )
    problem = prime_backend.build_prime_field_reduction_problem(
        parameter_space=space,
        source_constraint_system=source,
        characteristic=characteristic,
        reduction_guards=guards or [],
        resource_limits=_common_limits(),
    )
    interface = _interface()
    parameterization = build_construction_parameterization(
        campaign_id="campaign:prime-field-fixture",
        request_id="request:prime-field-fixture",
        gap_id="gap:prime-field-fixture",
        context_hash="context:prime-field-fixture",
        context_epoch=1,
        adapter_id=ADAPTER_ID,
        target_interface_sha256=interface["interface_sha256"],
        source_refs=["fixture:prime-field-rational-reduction"],
        parameter_space=space,
        backend_problem=problem,
        materializer={
            "schema": SAFE_ARTIFACT_TEMPLATE_SCHEMA,
            "template": _template(),
        },
        backend=_descriptor(),
        resource_limits=_common_limits(),
        search_order={
            "kind": "lexicographic",
            "parameter_ids": ["a"],
            "domain_order": "declared_canonical",
        },
    )
    return parameterization, interface


def test_modular_equality_filter_rejects_only_sound_rational_failures() -> None:
    constraints = [{
        "constraint_id": "unit_square",
        "relation": "eq",
        "left": _polynomial(("1", [2])),
        "right": _polynomial(("1", [0])),
    }]
    parameterization, interface = _parameterization(
        domain=["1", "3/2", "2"],
        constraints=constraints,
        characteristic=3,
    )
    execution = execute_construction_parameterization(
        parameterization,
        witness_schema=interface["witness_schema"],
    )
    by_value = {
        row["assignment"]["a"]: row for row in execution["residuals"]
    }
    assert by_value["1"]["kind"] == "candidate"
    assert by_value["2"]["kind"] == "candidate"
    assert by_value["3/2"]["kind"] == "rejection"
    assert by_value["3/2"]["observed"]["transport_effect"] == (
        "refutes_same_rational_assignment"
    )
    assert by_value["2"]["reason_code"] == (
        "modular_survivor_requires_exact_rational_replay"
    )
    replayed = admit_persisted_construction_execution(
        parameterization,
        dict(execution),
        witness_schema=interface["witness_schema"],
    )
    assert dict(replayed) == dict(execution)


def test_modular_disequality_failure_remains_a_candidate_for_q_replay() -> None:
    constraints = [{
        "constraint_id": "nonzero",
        "relation": "ne",
        "left": _polynomial(("1", [1])),
        "right": _polynomial(),
    }]
    parameterization, interface = _parameterization(
        domain=["3"],
        constraints=constraints,
        characteristic=3,
    )
    execution = execute_construction_parameterization(
        parameterization,
        witness_schema=interface["witness_schema"],
    )
    row = execution["residuals"][0]
    assert row["kind"] == "candidate"
    assert row["reason_code"] == (
        "modular_inconclusive_requires_exact_rational_replay"
    )
    assert row["observed"]["inconclusive_disequality_ids"] == ["nonzero"]


def test_exceptional_prime_is_typed_before_any_assignment_verdict() -> None:
    parameterization, interface = _parameterization(
        domain=["-1/4"],
        constraints=[],
        characteristic=2,
        guards=[{"guard_id": "jacobian_constant", "value": "-2"}],
    )
    execution = execute_construction_parameterization(
        parameterization,
        witness_schema=interface["witness_schema"],
    )
    assert execution["status"] == "backend_unavailable"
    assert execution["coverage_complete"] is False
    row = execution["residuals"][0]
    assert row["reason_code"] == "prime_field_reduction_excluded"
    kinds = {item["kind"] for item in row["observed"]["exclusions"]}
    assert kinds == {
        "noninvertible_denominator",
        "required_nonzero_vanished",
    }


def _published_map() -> dict:
    return {
        "schema": POLYNOMIAL_MAP_SCHEMA,
        "coefficient_domain": "Q",
        "variables": ["x", "y", "z"],
        "components": [
            {"terms": [
                _term("1", 0, 0, 1), _term("3", 1, 1, 1),
                _term("3", 2, 2, 1), _term("1", 3, 3, 1),
                _term("4", 0, 2, 0), _term("7", 1, 3, 0),
                _term("3", 2, 4, 0),
            ]},
            {"terms": [
                _term("1", 0, 1, 0), _term("3", 1, 0, 1),
                _term("6", 2, 1, 1), _term("3", 3, 2, 1),
                _term("12", 1, 2, 0), _term("9", 2, 3, 0),
            ]},
            {"terms": [
                _term("2", 1, 0, 0), _term("-3", 2, 1, 0),
                _term("-1", 3, 0, 1),
            ]},
        ],
        "collision_inputs": [
            ["0", "0", "-1/4"],
            ["1", "-3/2", "13/2"],
            ["-1", "3/2", "13/2"],
        ],
    }


def test_public_map_replays_over_f3_and_excludes_f2() -> None:
    predicate = _interface()["predicate_ir"]
    accepted = materialize_theory_adapter_capability(
        ADAPTER_ID,
        prime_backend.MAP_REDUCTION_VERIFIER_CAPABILITY,
        artifact=_published_map(),
        predicate_ir=predicate,
        characteristic=3,
    )
    assert accepted["status"] == "accepted"
    assert accepted["jacobian_determinant"] == {
        "terms": [_term("1", 0, 0, 0)]
    }
    assert accepted["common_image"] == ["2", "0", "0"]
    excluded = materialize_theory_adapter_capability(
        ADAPTER_ID,
        prime_backend.MAP_REDUCTION_VERIFIER_CAPABILITY,
        artifact=_published_map(),
        predicate_ir=predicate,
        characteristic=2,
    )
    assert excluded["status"] == "excluded"
    assert {row["kind"] for row in excluded["exclusions"]} == {
        "jacobian_constant_vanished",
        "noninvertible_denominator",
    }


def test_prime_problem_identity_and_authoring_contract_are_closed() -> None:
    with pytest.raises(ValueError, match="reviewed prime"):
        prime_backend.prime_field_descriptor(15)
    parameterization, interface = _parameterization(
        domain=["1"], constraints=[], characteristic=3
    )
    changed = deepcopy(parameterization)
    changed["backend_problem"]["field"]["characteristic"] = 5
    # Re-signing the outer object cannot forge the adapter-owned reduction
    # receipt; semantic admission recomputes it from the signed source bytes.
    core = {
        key: value for key, value in changed.items()
        if key not in {"parameterization_id", "receipt_sha256"}
    }
    changed["parameterization_id"] = (
        "construction-parameterization:" + content_hash(core)
    )
    changed["receipt_sha256"] = content_hash({
        **core,
        "parameterization_id": changed["parameterization_id"],
    })
    with pytest.raises(
        ConstructionParameterizationError,
        match="prime-field backend problem is not canonical",
    ):
        execute_construction_parameterization(
            changed, witness_schema=interface["witness_schema"]
        )
    authoring = construction_parameterization_authoring_contract(
        campaign_id="campaign:prime-field-fixture",
        request_id="request:prime-field-fixture",
        gap_id="gap:prime-field-fixture",
        context_hash="context:prime-field-fixture",
        context_epoch=1,
        adapter_id=ADAPTER_ID,
        witness_interface=interface,
    )
    rows = authoring["construction_backend_capabilities"]
    prime = next(
        row for row in rows
        if row["backend_capability"]["capability_id"]
        == prime_backend.CAPABILITY_ID
    )
    assert prime["field_descriptor_schema"] == prime_backend.FIELD_SCHEMA
    assert prime["transport_policy"]["reverse_field_verdict"] == "forbidden"
