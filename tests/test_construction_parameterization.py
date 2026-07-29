from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import json
import pickle
from types import SimpleNamespace

import pytest

from ztare.leanmill.adapter_forge import (
    ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT,
    adapter_forge_attempt_directory,
    bind_adapter_review_evidence,
    build_adapter_forge_construction_parameterization_conformance,
    validate_adapter_forge_review,
    validate_reviewed_construction_parameterization_authority,
)
from ztare.leanmill.adapters.binary_linear_code import (
    ADAPTER_ID as BINARY_ADAPTER_ID,
    binary_witness_construction_interface,
)
from ztare.leanmill.adapters.rational_polynomial_map import (
    ADAPTER_ID as RATIONAL_ADAPTER_ID,
    POLYNOMIAL_MAP_SCHEMA,
    rational_polynomial_map_witness_construction_interface,
)
from ztare.leanmill.adapters.construction_backends import explicit_finite_json
from ztare.leanmill.adapters import binary_linear_code as binary_adapter_module
from ztare.leanmill.adapters.construction_backends import (
    finite_rational_polynomial as rational_backend,
)
from ztare.leanmill.adapters.construction_backends.finite_rational_polynomial import (
    EXACT_CONSTRAINT_SYSTEM_SCHEMA,
    FINITE_EXACT_BACKEND,
    FINITE_EXACT_BACKEND_ID,
    GROEBNER_RATIONAL_BACKEND,
    GROEBNER_RATIONAL_BACKEND_ID,
    build_exact_constraint_system,
    parse_canonical_rational,
)
from ztare.leanmill.construction_parameterization import (
    CONSTRUCTION_PARAMETERIZATION_SCHEMA,
    SAFE_ARTIFACT_TEMPLATE_SCHEMA,
    ConstructionBackendCapabilityUnavailable,
    ConstructionParameterizationError,
    ConstructionResourceCeilingExceeded,
    admit_construction_parameterization,
    admit_persisted_construction_execution,
    build_construction_parameterization,
    construction_parameterization_authoring_contract,
    certified_construction_parameter_count,
    enumerate_parameter_assignments,
    execute_construction_parameterization,
    materialize_construction_candidates,
    materialize_parameter_artifact,
    replay_parameter_artifact_schema,
    validate_construction_parameterization,
    validate_construction_parameterization_execution,
)
from ztare.leanmill.data_only_json import strict_json_data
from ztare.leanmill.construction_wire_projection import (
    project_explicit_assignment_wire_bytes,
)
from ztare.leanmill.common import read_json, write_json_atomic
from ztare.leanmill.exploration_budget import (
    ExplorationBudgetLedger,
    budget_preset,
)
from ztare.leanmill.finite_construction_family import (
    AdmittedConstructionOrigin,
    admit_construction_origin,
    execute_finite_construction_family,
    lower_reviewed_construction_parameterization,
    validate_finite_construction_family,
    validate_finite_construction_family_execution,
)
from ztare.leanmill.theory_adapter_registry import (
    materialize_theory_adapter_capability,
    theory_adapter_capabilities,
)
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.reviewed_family_member_ratification import (
    build_reviewed_family_member_ratification_admission,
    validate_reviewed_family_member_ratification_admission,
)
from ztare.leanmill.reviewed_family_exhaustion_discharge import (
    validate_reviewed_family_exhaustion_observation,
)
from ztare.leanmill.reviewed_family_objective_discharge import (
    validate_reviewed_family_objective_discharge,
)
from ztare.leanmill.reviewed_construction_campaign import (
    ReviewedConstructionHooks,
    advance_reviewed_construction_campaign,
)
from ztare.leanmill.frontier_campaign_runner import (
    _approved_construction_parameterization_candidate,
    _persist_reviewed_family_member_ratification_admissions,
    _read_adapter_forge_lifecycle_completion,
    _replay_reviewed_family_member_ratification_admissions,
)
from ztare.leanmill.theory_language import (
    build_theory_language_expansion_request,
)
from ztare.leanmill.witness_construction_boundary import (
    execute_registered_witness_artifact,
)


def _limits(**overrides: int) -> dict[str, int]:
    limits = {
        "max_assignments": 16,
        "max_template_nodes": 1_000,
        "max_template_bytes": 40_000,
        "max_materialized_artifact_bytes": 100_000,
        "max_execution_receipt_bytes": 1_000_000,
        "max_materialized_family_bytes": 4_000_000,
    }
    limits.update(overrides)
    return limits


def _q_limits(**overrides: int) -> dict[str, int]:
    limits = {
        "max_constraints": 8,
        "max_constraint_evaluations": 1_000,
        "max_terms_per_polynomial": 8,
        "max_exponent": 8,
        "max_exact_operations": 1_000,
        "max_rational_bits": 256,
        "max_cumulative_rational_bit_work": 100_000,
        "max_rational_output_bytes": 10_000,
    }
    limits.update(overrides)
    return limits


def _polynomial(*terms: tuple[str, list[int]]) -> dict:
    return {
        "schema": "leanmill.exact_sparse_polynomial.v1",
        "terms": [
            {"coefficient": coefficient, "exponents": exponents}
            for coefficient, exponents in terms
        ],
    }


def _capability(**kwargs):
    descriptor = kwargs.pop("descriptor")
    return materialize_theory_adapter_capability(
        descriptor["adapter_id"],
        descriptor["capability_id"],
        descriptor=descriptor,
        **kwargs,
    )


def _forge_receipt(parameterization: dict, interface: dict) -> dict:
    source_content = "{}\n"
    test_content = "inert construction interface check\n"
    host = build_adapter_forge_construction_parameterization_conformance(
        parameterization,
        witness_interface=interface,
        source_artifacts=[
            {
                "path": "fixture.json",
                "content_sha256": content_hash({"bytes": source_content}),
                "content": source_content,
            }
        ],
        test_artifacts=[
            {
                "path": "check.txt",
                "content_sha256": content_hash({"bytes": test_content}),
                "content": test_content,
            }
        ],
        manifest_capability_source="fixture.json",
        resolved_capability_source="fixture.json",
    )
    review = {
        "accepted": True,
        "reviewer_ref": "independent-agent:fixture-reviewer",
        "rationale": "Frozen data and deterministic host replay agree.",
        "evidence_refs": ["sha256:" + host["receipt_sha256"]],
    }
    core = {
        "schema": "leanmill.adapter_forge_quarantine_receipt.v1",
        "gap_id": parameterization["gap_id"],
        "proposed_adapter_id": parameterization["adapter_id"],
        "proposal_digest": content_hash(
            {"parameterization_sha256": parameterization["receipt_sha256"]}
        ),
        "host_conformance": host,
        "independent_review": review,
        "review_evidence_binding": bind_adapter_review_evidence(review, host),
        "status": "quarantined_registry_proposal",
        "live_registry_mutated": False,
        "exactness_authority_granted": False,
        "next_step": "execute_reviewed_construction_parameterization",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _origin(
    parameterization: dict,
    forge: dict,
    execution: dict,
    interface: dict,
):
    return admit_construction_origin(
        parameterization=parameterization,
        forge_quarantine_receipt=forge,
        parameterization_execution=execution,
        witness_interface=interface,
    )


def _binary_interface() -> dict:
    return binary_witness_construction_interface(
        length=2,
        dimension=1,
        minimum_distance=1,
        target_snapshot_sha256="a" * 64,
        max_nonzero_messages=1,
        target_config_sha256="b" * 64,
    )


def _binary_parameterization(
    *,
    rows: list[str] | None = None,
    limits: dict[str, int] | None = None,
    backend: dict | None = None,
    symmetry_policy: dict | None = None,
    source_refs: list[str] | None = None,
    request_id: str = "request:binary-fixture",
    gap_id: str = "gap:binary-fixture",
) -> tuple[dict, dict]:
    interface = _binary_interface()
    selected_limits = limits or _limits()
    parameter_ids = ["row"]
    selected_backend = backend or {
        "adapter_id": BINARY_ADAPTER_ID,
        "capability_id": explicit_finite_json.CAPABILITY_ID,
        "contract_sha256": content_hash(explicit_finite_json.CONTRACT),
    }
    parameterization = build_construction_parameterization(
        campaign_id="campaign:binary-fixture",
        request_id=request_id,
        gap_id=gap_id,
        context_hash="context:binary-fixture",
        context_epoch=3,
        adapter_id=BINARY_ADAPTER_ID,
        target_interface_sha256=interface["interface_sha256"],
        source_refs=source_refs or ["fixture:binary-construction"],
        parameter_space={
            "schema": "leanmill.explicit_finite_parameter_space.v1",
            "variables": [
                {
                    "parameter_id": "row",
                    "sort": "json_atom",
                    "domain": rows or ["0x1", "0x2"],
                }
            ],
        },
        backend_problem=explicit_finite_json.build_problem(
            parameter_ids=parameter_ids
        ),
        materializer={
            "schema": SAFE_ARTIFACT_TEMPLATE_SCHEMA,
            "template": {
                "schema": "leanmill.binary_linear_generator_matrix.v1",
                "field_order": 2,
                "length": 2,
                "dimension": 1,
                "coordinate_convention": "bit_i_is_coordinate_i",
                "rows_hex": [{"$parameter": "row"}],
            },
        },
        backend=selected_backend,
        resource_limits=selected_limits,
        search_order={
            "kind": "lexicographic",
            "parameter_ids": parameter_ids,
            "domain_order": "declared_canonical",
        },
        symmetry_policy=symmetry_policy,
    )
    return parameterization, interface


def _term(coefficient: object, *exponents: int) -> dict:
    return {"coefficient": coefficient, "exponents": list(exponents)}


def _rational_template() -> dict:
    return {
        "schema": POLYNOMIAL_MAP_SCHEMA,
        "coefficient_domain": "Q",
        "variables": ["x", "y", "z"],
        "components": [
            {
                "terms": [
                    _term("1", 0, 0, 1),
                    _term({"$parameter": "c"}, 1, 1, 1),
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
            ["0", "0", {"$parameter": "p"}],
            ["1", "-3/2", "13/2"],
            ["-1", "3/2", "13/2"],
        ],
    }


def _rational_parameterization(
    *,
    p_domain: list[str] | None = None,
    source_refs: list[str] | None = None,
    backend: dict | None = None,
    backend_limits: dict[str, int] | None = None,
    constraints: list[dict] | None = None,
) -> tuple[dict, dict]:
    interface = rational_polynomial_map_witness_construction_interface(
        variables=["x", "y", "z"],
        jacobian_condition={"kind": "equals_constant", "constant": "-2"},
        minimum_distinct_collision_points=2,
        target_snapshot_sha256="c" * 64,
        target_config_sha256="d" * 64,
    )
    limits = _limits(max_template_nodes=2_000)
    parameter_ids = ["c", "p"]
    parameterization = build_construction_parameterization(
        campaign_id="campaign:rational-fixture",
        request_id="request:rational-fixture",
        gap_id="gap:rational-fixture",
        context_hash="context:rational-fixture",
        context_epoch=7,
        adapter_id=RATIONAL_ADAPTER_ID,
        target_interface_sha256=interface["interface_sha256"],
        source_refs=source_refs or ["fixture:rational-polynomial-construction"],
        parameter_space={
            "schema": "leanmill.explicit_finite_parameter_space.v1",
            "variables": [
                {"parameter_id": "c", "sort": "rational", "domain": ["3"]},
                {
                    "parameter_id": "p",
                    "sort": "rational",
                    "domain": p_domain or ["-1/4"],
                },
            ],
        },
        backend_problem=build_exact_constraint_system(
            parameter_ids=parameter_ids,
            backend_resource_limits=backend_limits or _q_limits(),
            constraints=constraints or [],
        ),
        materializer={
            "schema": SAFE_ARTIFACT_TEMPLATE_SCHEMA,
            "template": _rational_template(),
        },
        backend=backend or FINITE_EXACT_BACKEND,
        resource_limits=limits,
        search_order={
            "kind": "lexicographic",
            "parameter_ids": parameter_ids,
            "domain_order": "declared_canonical",
        },
    )
    return parameterization, interface


def _lower_and_execute(parameterization: dict, interface: dict):
    forge = _forge_receipt(parameterization, interface)
    family, execution = lower_reviewed_construction_parameterization(
        parameterization,
        forge_quarantine_receipt=forge,
        witness_interface=interface,
    )
    assert family is not None
    origin = _origin(parameterization, forge, execution, interface)
    result = execute_finite_construction_family(
        family,
        witness_interface=interface,
        capability_fn=_capability,
        construction_origin=origin,
    )
    return forge, family, execution, origin, result


def test_same_ir_lowers_binary_and_rational_through_one_family_executor() -> None:
    binary, binary_interface = _binary_parameterization()
    rational, rational_interface = _rational_parameterization()
    assert binary["schema"] == rational["schema"] == CONSTRUCTION_PARAMETERIZATION_SCHEMA
    assert binary["backend_problem"]["schema"] == (
        explicit_finite_json.PROBLEM_SCHEMA
    )
    assert rational["backend_problem"]["schema"] == EXACT_CONSTRAINT_SYSTEM_SCHEMA

    _forge, binary_family, _execution, origin, binary_result = _lower_and_execute(
        binary, binary_interface
    )
    assert binary_result["status"] == "witness_found"
    assert binary_family["family_spec"]["parameterization_sha256"] == binary[
        "receipt_sha256"
    ]
    assert "parameterization" not in binary_family["family_spec"]
    assert "parameterization_execution" not in binary_result
    assert validate_finite_construction_family_execution(
        binary_result,
        family=binary_family,
        witness_interface=binary_interface,
        construction_origin=origin,
    ) == binary_result

    _forge, _family, _execution, _origin_row, rational_result = _lower_and_execute(
        rational, rational_interface
    )
    observed = rational_result["member_results"][0][
        "registered_witness_execution"
    ]["observed"]
    assert observed["jacobian_determinant"] == {
        "terms": [{"coefficient": "-2", "exponents": [0, 0, 0]}]
    }


def test_zero_candidates_stays_in_exact_residual_algebra() -> None:
    parameterization, interface = _rational_parameterization()
    limits = parameterization["resource_limits"]
    impossible = build_construction_parameterization(
        campaign_id=parameterization["campaign_id"],
        request_id=parameterization["request_id"],
        gap_id=parameterization["gap_id"],
        context_hash=parameterization["context_hash"],
        context_epoch=parameterization["context_epoch"],
        adapter_id=parameterization["adapter_id"],
        target_interface_sha256=parameterization["target_interface_sha256"],
        source_refs=parameterization["source_refs"],
        parameter_space=parameterization["parameter_space"],
        backend_problem=build_exact_constraint_system(
            parameter_ids=["c", "p"],
            backend_resource_limits=parameterization["backend_problem"][
                "resource_limits"
            ],
            constraints=[
                {
                    "constraint_id": "impossible",
                    "relation": "eq",
                    "left": _polynomial(("1", [1, 0])),
                    "right": _polynomial(),
                }
            ],
        ),
        materializer=parameterization["materializer"],
        backend=FINITE_EXACT_BACKEND,
        resource_limits=limits,
        search_order=parameterization["search_order"],
    )
    forge = _forge_receipt(impossible, interface)
    family, execution = lower_reviewed_construction_parameterization(
        impossible,
        forge_quarantine_receipt=forge,
        witness_interface=interface,
    )
    assert family is None
    assert execution["coverage_complete"] is True
    assert [row["kind"] for row in execution["residuals"]] == ["rejection"]


def test_adapter_forge_is_the_only_review_authority_and_replays_exact_bytes() -> None:
    parameterization, interface = _binary_parameterization()
    forge = _forge_receipt(parameterization, interface)
    frozen, receipt = validate_reviewed_construction_parameterization_authority(
        parameterization, forge, witness_interface=interface
    )
    assert frozen == parameterization
    assert receipt == forge

    mutated = deepcopy(forge)
    host = mutated["host_conformance"]
    host["materializer_sha256"] = "e" * 64
    host_core = {key: value for key, value in host.items() if key != "receipt_sha256"}
    host["receipt_sha256"] = content_hash(host_core)
    review = mutated["independent_review"]
    review["evidence_refs"] = ["sha256:" + host["receipt_sha256"]]
    mutated["review_evidence_binding"] = bind_adapter_review_evidence(review, host)
    mutated_core = {
        key: value for key, value in mutated.items() if key != "receipt_sha256"
    }
    mutated["receipt_sha256"] = content_hash(mutated_core)
    with pytest.raises(ValueError, match="does not join"):
        validate_reviewed_construction_parameterization_authority(
            parameterization, mutated, witness_interface=interface
        )

    for bad_review in (
        {
            "accepted": True,
            "reviewer_ref": "",
            "rationale": "x",
            "evidence_refs": [host["receipt_sha256"]],
        },
        {
            "accepted": True,
            "reviewer_ref": "reviewer",
            "rationale": "x",
            "evidence_refs": ["host:" + host["receipt_sha256"]],
        },
        {
            "accepted": True,
            "reviewer_ref": "reviewer",
            "rationale": "x",
            "evidence_refs": [host["receipt_sha256"]],
            "post_outcome_score": 1,
        },
    ):
        with pytest.raises(ValueError, match="independent review"):
            validate_adapter_forge_review(bad_review)


def test_construction_forge_authority_requires_nonempty_staged_provenance() -> None:
    parameterization, interface = _binary_parameterization()
    with pytest.raises(ValueError, match="requires staged source artifacts"):
        build_adapter_forge_construction_parameterization_conformance(
            parameterization,
            witness_interface=interface,
            source_artifacts=[],
            test_artifacts=[],
            manifest_capability_source="fixture.json",
            resolved_capability_source="fixture.json",
        )

    source_content = "{}\n"
    test_content = "inert check\n"
    source = {
        "path": "fixture.json",
        "content_sha256": content_hash({"bytes": source_content}),
        "content": source_content,
    }
    check = {
        "path": "check.txt",
        "content_sha256": content_hash({"bytes": test_content}),
        "content": test_content,
    }
    with pytest.raises(ValueError, match="lacks staged source membership"):
        build_adapter_forge_construction_parameterization_conformance(
            parameterization,
            witness_interface=interface,
            source_artifacts=[source],
            test_artifacts=[check],
            manifest_capability_source="absent.json",
            resolved_capability_source="fixture.json",
        )

    forged = deepcopy(_forge_receipt(parameterization, interface))
    forged_host = forged["host_conformance"]
    forged_host["source_artifacts"] = []
    forged_host["test_artifacts"] = []
    forged_host_core = {
        key: value
        for key, value in forged_host.items()
        if key != "receipt_sha256"
    }
    forged_host["receipt_sha256"] = content_hash(forged_host_core)
    forged_core = {
        key: value for key, value in forged.items() if key != "receipt_sha256"
    }
    forged["receipt_sha256"] = content_hash(forged_core)
    with pytest.raises(ValueError, match="requires staged source artifacts"):
        validate_reviewed_construction_parameterization_authority(
            parameterization,
            forged,
            witness_interface=interface,
        )

def test_generic_json_atom_replaces_fixture_shaped_bit_packing() -> None:
    parameterization, interface = _binary_parameterization(rows=["0x1"])
    execution = execute_construction_parameterization(
        parameterization, witness_schema=interface["witness_schema"]
    )
    artifact = materialize_parameter_artifact(
        execution.admitted_parameterization,
        execution["residuals"][0]["assignment"],
        witness_schema=interface["witness_schema"],
    )
    assert artifact["rows_hex"] == ["0x1"]

    changed = deepcopy(parameterization)
    changed["materializer"] = {
        "schema": SAFE_ARTIFACT_TEMPLATE_SCHEMA,
        "template": {"row": {"$bit_vector_hex": {"parameters": ["row"], "hex_width": 1}}},
    }
    core = {
        key: value
        for key, value in changed.items()
        if key not in {"parameterization_id", "receipt_sha256"}
    }
    changed["parameterization_id"] = "construction-parameterization:" + content_hash(core)
    changed["receipt_sha256"] = content_hash(
        {**core, "parameterization_id": changed["parameterization_id"]}
    )
    with pytest.raises(ConstructionParameterizationError, match="reserved"):
        validate_construction_parameterization(changed)

    numeric_use = deepcopy(parameterization)
    numeric_use["backend_problem"] = build_exact_constraint_system(
        parameter_ids=["row"],
        backend_resource_limits=_q_limits(),
        constraints=[
            {
                "constraint_id": "bad",
                "relation": "eq",
                "left": _polynomial(("1", [1])),
                "right": _polynomial(),
            }
        ],
    )
    core = {
        key: value
        for key, value in numeric_use.items()
        if key not in {"parameterization_id", "receipt_sha256"}
    }
    numeric_use["parameterization_id"] = "construction-parameterization:" + content_hash(core)
    numeric_use["receipt_sha256"] = content_hash(
        {**core, "parameterization_id": numeric_use["parameterization_id"]}
    )
    assert validate_construction_parameterization(numeric_use) == numeric_use
    with pytest.raises(
        ConstructionParameterizationError,
        match="explicit finite backend problem",
    ):
        admit_construction_parameterization(numeric_use)


def test_resource_and_symbolic_unavailability_are_typed_and_compact() -> None:
    parameterization, interface = _rational_parameterization(
        backend=GROEBNER_RATIONAL_BACKEND
    )
    execution = execute_construction_parameterization(
        parameterization, witness_schema=interface["witness_schema"]
    )
    assert execution["status"] == "backend_unavailable"
    assert execution["residuals"][0]["reason_code"] == (
        "registered_exact_groebner_backend_absent"
    )

    # Exercise the backend's typed-unavailability projection as well as the
    # common protocol's authoring-time short circuit above.  A registered but
    # absent solver must preserve the exact problem identity for navigation;
    # it must not raise while constructing that feedback.
    backend_execution = rational_backend.capability(
        operation="execute_problem",
        backend=GROEBNER_RATIONAL_BACKEND,
        parameter_space=parameterization["parameter_space"],
        backend_problem=parameterization["backend_problem"],
        symmetry_policy=parameterization["symmetry_policy"],
        resource_limits=parameterization["resource_limits"],
        witness_schema=interface["witness_schema"],
        materialize=lambda _assignment: {},
        resource_error=ConstructionResourceCeilingExceeded,
    )
    assert backend_execution["status"] == "backend_unavailable"
    assert backend_execution["coverage_complete"] is False
    assert backend_execution["residuals"][0]["observed"] == {
        "requested_backend_id": GROEBNER_RATIONAL_BACKEND_ID,
        "requested_symmetry_kind": "none",
        "constraint_system_sha256": parameterization["backend_problem"][
            "constraint_system_sha256"
        ],
    }

    limited, limited_interface = _binary_parameterization(
        rows=["0x1"],
        limits=_limits(max_materialized_artifact_bytes=50),
    )
    with pytest.raises(
        ConstructionResourceCeilingExceeded,
        match="materialized_artifact_byte_limit_exhausted",
    ):
        replay_parameter_artifact_schema(
            admit_construction_parameterization(limited),
            witness_schema=limited_interface["witness_schema"],
        )


def test_assignment_wire_projection_rejects_before_backend_enumeration(
    monkeypatch,
) -> None:
    original = binary_adapter_module.CAPABILITIES[
        explicit_finite_json.CAPABILITY_ID
    ]
    calls = {"validate_problem": 0, "enumerate_assignments": 0}

    def counted(**kwargs):
        operation = str(kwargs.get("operation") or "")
        if operation in calls:
            calls[operation] += 1
        return original(**kwargs)

    monkeypatch.setitem(
        binary_adapter_module.CAPABILITIES,
        explicit_finite_json.CAPABILITY_ID,
        counted,
    )
    parameterization, _interface = _binary_parameterization(
        rows=["x" * 9_000],
        limits=_limits(max_execution_receipt_bytes=8_192),
    )
    with pytest.raises(
        ConstructionResourceCeilingExceeded,
        match="construction_assignment_wire_limit_exhausted",
    ) as caught:
        admit_construction_parameterization(parameterization)
    assert caught.value.resource == "assignment_wire_bytes"
    assert caught.value.observed > caught.value.ceiling == 8_192
    assert caught.value.counters["certified_assignment_count"] == 1
    assert calls == {"validate_problem": 1, "enumerate_assignments": 0}


def test_assignment_wire_projection_must_equal_enumerated_snapshot(
    monkeypatch,
) -> None:
    original = binary_adapter_module.CAPABILITIES[
        explicit_finite_json.CAPABILITY_ID
    ]
    projection_delta = 0

    def projected(**kwargs):
        result = original(**kwargs)
        if kwargs.get("operation") == "validate_problem":
            result = dict(result)
            result["projected_assignment_wire_bytes"] += projection_delta
        return result

    monkeypatch.setitem(
        binary_adapter_module.CAPABILITIES,
        explicit_finite_json.CAPABILITY_ID,
        projected,
    )
    parameterization, _interface = _binary_parameterization()
    for projection_delta in (-1, 1):
        with pytest.raises(
            ConstructionParameterizationError,
            match="assignment wire projection changed identity",
        ):
            admit_construction_parameterization(parameterization)


def test_rendered_template_projection_rejects_before_expansion(monkeypatch) -> None:
    from ztare.leanmill import construction_parameterization as construction_module
    from ztare.leanmill import construction_wire_projection as wire_module

    interface = _binary_interface()
    parameterization = build_construction_parameterization(
        campaign_id="campaign:template-projection",
        request_id="request:template-projection",
        gap_id="gap:template-projection",
        context_hash="context:template-projection",
        context_epoch=1,
        adapter_id=BINARY_ADAPTER_ID,
        target_interface_sha256=interface["interface_sha256"],
        source_refs=["fixture:template-projection"],
        parameter_space={
            "schema": "leanmill.explicit_finite_parameter_space.v1",
            "variables": [{
                "parameter_id": "row",
                "sort": "json_atom",
                "domain": ["x" * 1_000],
            }],
        },
        backend_problem=explicit_finite_json.build_problem(
            parameter_ids=["row"]
        ),
        materializer={
            "schema": SAFE_ARTIFACT_TEMPLATE_SCHEMA,
            "template": {
                "schema": "leanmill.binary_linear_generator_matrix.v1",
                "field_order": 2,
                "length": 2,
                "dimension": 1,
                "coordinate_convention": "bit_i_is_coordinate_i",
                "rows_hex": [
                    {"$parameter": "row"} for _ in range(200)
                ],
            },
        },
        backend={
            "adapter_id": BINARY_ADAPTER_ID,
            "capability_id": explicit_finite_json.CAPABILITY_ID,
            "contract_sha256": content_hash(explicit_finite_json.CONTRACT),
        },
        resource_limits=_limits(),
        search_order={
            "kind": "lexicographic",
            "parameter_ids": ["row"],
            "domain_order": "declared_canonical",
        },
    )
    admitted = admit_construction_parameterization(parameterization)
    render_calls = 0
    assignment_value_serializations = 0
    original_wire_size = wire_module.canonical_json_wire_bytes

    def counted_wire_size(value):
        nonlocal assignment_value_serializations
        if value == "x" * 1_000:
            assignment_value_serializations += 1
        return original_wire_size(value)

    def forbidden_render(*_args, **_kwargs):
        nonlocal render_calls
        render_calls += 1
        raise AssertionError("oversized template must not be expanded")

    monkeypatch.setattr(construction_module, "_render_template", forbidden_render)
    monkeypatch.setattr(wire_module, "canonical_json_wire_bytes", counted_wire_size)
    with pytest.raises(
        ConstructionResourceCeilingExceeded,
        match="materialized_artifact_byte_limit_exhausted",
    ) as caught:
        execute_construction_parameterization(
            admitted,
            witness_schema=interface["witness_schema"],
        )
    assert caught.value.resource == "materialized_artifact_bytes"
    assert caught.value.observed > caught.value.ceiling == 100_000
    assert caught.value.counters["attempted_artifacts"] == 1
    assert render_calls == 0
    assert assignment_value_serializations == 1


def test_typed_construction_failure_metadata_rejects_coercion() -> None:
    for field, value in (
        ("observed", True),
        ("observed", -1),
        ("observed", 1.0),
        ("ceiling", "1"),
        ("certified_assignment_count", False),
        ("attempted_assignment_count", -1),
    ):
        kwargs = {
            "resource": "fixture_units",
            "observed": 1,
            "ceiling": 1,
            "certified_assignment_count": 0,
            "attempted_assignment_count": 0,
        }
        kwargs[field] = value
        with pytest.raises(ValueError, match="resource metadata is malformed"):
            ConstructionResourceCeilingExceeded("fixture_limit", **kwargs)

    with pytest.raises(ValueError, match="backend-unavailable metadata"):
        ConstructionBackendCapabilityUnavailable(
            "fixture_unavailable",
            operation="resolve",
            adapter_id=BINARY_ADAPTER_ID,
            capability_id="",
            error_type="CapabilityNotRegistered",
        )


def test_missing_backend_is_capability_unavailable_not_resource_exhaustion(
    monkeypatch,
) -> None:
    from ztare.leanmill import construction_parameterization as construction_module

    monkeypatch.setattr(
        construction_module,
        "theory_adapter_capabilities",
        lambda _adapter_id: (),
    )
    with pytest.raises(ConstructionBackendCapabilityUnavailable) as caught:
        construction_parameterization_authoring_contract(
            campaign_id="campaign:no-backend",
            request_id="request:no-backend",
            gap_id="gap:no-backend",
            context_hash="context:no-backend",
            context_epoch=1,
            adapter_id="fixture.adapter_without_backend.v1",
            witness_interface=_binary_interface(),
        )
    assert caught.value.operation == "authoring_contract"
    assert caught.value.adapter_id == "fixture.adapter_without_backend.v1"
    assert caught.value.capability_id == "none_registered"
    assert caught.value.error_type == "NoRegisteredConstructionBackend"


def test_rational_backend_bounds_cumulative_bit_work_and_output_bytes() -> None:
    bit_limited, interface = _rational_parameterization(
        backend_limits=_q_limits(max_cumulative_rational_bit_work=1)
    )
    with pytest.raises(ConstructionResourceCeilingExceeded) as bit_error:
        execute_construction_parameterization(
            bit_limited, witness_schema=interface["witness_schema"]
        )
    assert bit_error.value.reason_code == (
        "cumulative_exact_rational_bit_work_limit_exhausted"
    )
    assert bit_error.value.resource == "cumulative_rational_bit_work"
    assert bit_error.value.counters["rational_bit_work"] == 0

    output_limited, interface = _rational_parameterization(
        backend_limits=_q_limits(max_rational_output_bytes=1),
        constraints=[{
            "constraint_id": "reject_nonzero_c",
            "relation": "eq",
            "left": _polynomial(("1", [1, 0])),
            "right": _polynomial(),
        }],
    )
    with pytest.raises(ConstructionResourceCeilingExceeded) as output_error:
        execute_construction_parameterization(
            output_limited, witness_schema=interface["witness_schema"]
        )
    assert output_error.value.reason_code == (
        "exact_rational_output_byte_limit_exhausted"
    )
    assert output_error.value.resource == "rational_output_bytes"
    assert output_error.value.observed == 2
    assert output_error.value.ceiling == 1
    assert output_error.value.counters["rational_output_bytes"] == 1


def test_rational_backend_preflights_large_decimal_conversion() -> None:
    base = 10**75 + 1
    parameterization, interface = _rational_parameterization(
        p_domain=[str(base)],
        backend_limits=_q_limits(
            max_exponent=64,
            max_rational_bits=16_384,
        ),
        constraints=[{
            "constraint_id": "reject_large_power",
            "relation": "eq",
            "left": _polynomial(("1", [0, 64])),
            "right": _polynomial(),
        }],
    )

    with pytest.raises(ConstructionResourceCeilingExceeded) as caught:
        execute_construction_parameterization(
            parameterization,
            witness_schema=interface["witness_schema"],
        )

    assert caught.value.reason_code == (
        "exact_rational_decimal_digit_limit_exhausted"
    )
    assert caught.value.resource == "rational_decimal_digits"
    assert caught.value.observed == 4_801
    assert caught.value.ceiling == 4_096
    assert caught.value.counters[
        "current_projected_rational_decimal_digits"
    ] == 4_801
    assert caught.value.counters[
        "current_projected_rational_wire_bytes"
    ] == 4_801


def test_rational_backend_maps_stricter_runtime_decimal_guard(
    monkeypatch,
) -> None:
    base = 10**75 + 1
    parameterization, interface = _rational_parameterization(
        p_domain=[str(base)],
        backend_limits=_q_limits(
            max_exponent=10,
            max_rational_bits=4_096,
        ),
        constraints=[{
            "constraint_id": "reject_guarded_power",
            "relation": "eq",
            "left": _polynomial(("1", [0, 10])),
            "right": _polynomial(),
        }],
    )
    original = rational_backend.format_canonical_rational

    def stricter_runtime_guard(value: Fraction) -> str:
        if abs(Fraction(value).numerator).bit_length() > 1_000:
            raise ValueError("simulated stricter integer conversion guard")
        return original(value)

    monkeypatch.setattr(
        rational_backend,
        "format_canonical_rational",
        stricter_runtime_guard,
    )
    with pytest.raises(ConstructionResourceCeilingExceeded) as caught:
        execute_construction_parameterization(
            parameterization,
            witness_schema=interface["witness_schema"],
        )

    assert caught.value.reason_code == (
        "exact_rational_decimal_conversion_runtime_unavailable"
    )
    assert caught.value.resource == "rational_decimal_digits"
    assert caught.value.observed == 751
    assert caught.value.ceiling == 4_096


def test_persisted_v1_rational_resource_limits_replay_without_new_field() -> None:
    parameterization, interface = _rational_parameterization()
    legacy_limits = parameterization["backend_problem"]["resource_limits"]
    assert set(legacy_limits) == {
        "max_constraints",
        "max_constraint_evaluations",
        "max_terms_per_polynomial",
        "max_exponent",
        "max_exact_operations",
        "max_rational_bits",
        "max_cumulative_rational_bit_work",
        "max_rational_output_bytes",
    }

    persisted = deepcopy(parameterization)
    assert validate_construction_parameterization(persisted) == persisted
    admitted = admit_construction_parameterization(persisted)
    execution = execute_construction_parameterization(
        admitted,
        witness_schema=interface["witness_schema"],
    )
    assert execution["status"] == "completed"


def test_rational_backend_bounds_empty_polynomial_constraint_evaluations() -> None:
    limited, interface = _rational_parameterization(
        p_domain=["0", "1/4"],
        backend_limits=_q_limits(max_constraint_evaluations=1),
        constraints=[{
            "constraint_id": "empty_identity",
            "relation": "eq",
            "left": _polynomial(),
            "right": _polynomial(),
        }],
    )
    with pytest.raises(ConstructionResourceCeilingExceeded) as caught:
        execute_construction_parameterization(
            limited,
            witness_schema=interface["witness_schema"],
        )
    assert caught.value.reason_code == (
        "constraint_evaluation_limit_exhausted"
    )
    assert caught.value.resource == "constraint_evaluations"
    assert caught.value.observed == 2
    assert caught.value.ceiling == 1
    assert caught.value.counters["constraint_evaluations"] == 1
    assert caught.value.counters["exact_operations"] == 0


def test_resource_exhaustion_precedes_family_outcome_algebra() -> None:
    def parameterization_for(
        label: str, p_domain: list[str]
    ) -> tuple[dict, dict]:
        base, interface = _rational_parameterization(p_domain=p_domain)
        limits = _limits(max_template_nodes=2_000)
        backend_limits = _q_limits(max_exact_operations=3)
        return (
            build_construction_parameterization(
                campaign_id="campaign:partial:" + label,
                request_id="request:partial:" + label,
                gap_id="gap:partial:" + label,
                context_hash="context:partial:" + label,
                context_epoch=1,
                adapter_id=RATIONAL_ADAPTER_ID,
                target_interface_sha256=interface["interface_sha256"],
                source_refs=["fixture:partial"],
                parameter_space=base["parameter_space"],
                backend_problem=build_exact_constraint_system(
                    parameter_ids=["c", "p"],
                    backend_resource_limits=backend_limits,
                    constraints=[{
                        "constraint_id": "nonnegative",
                        "relation": "ge",
                        "left": _polynomial(("1", [1, 0])),
                        "right": _polynomial(),
                    }],
                ),
                materializer=base["materializer"],
                backend=FINITE_EXACT_BACKEND,
                resource_limits=limits,
                search_order=base["search_order"],
            ),
            interface,
        )

    for label, domain in (
        ("valid", ["-1/4", "0"]),
        ("invalid", ["0", "1/4"]),
    ):
        parameterization, interface = parameterization_for(label, domain)
        with pytest.raises(
            ConstructionResourceCeilingExceeded,
            match="exact_operation_limit_exhausted",
        ) as caught:
            execute_construction_parameterization(
                parameterization,
                witness_schema=interface["witness_schema"],
            )
        assert caught.value.resource == "exact_operations"
        assert caught.value.observed > caught.value.ceiling == 3
        assert caught.value.certified_assignment_count == 2


def test_existing_feedback_drives_a_fresh_leaf_without_custom_revision_state() -> None:
    first, interface = _rational_parameterization(p_domain=["0"])
    _forge, _family, _execution, _origin_row, rejected = _lower_and_execute(
        first, interface
    )
    assert rejected["status"] == "exhausted"
    assert rejected["member_results"][0]["registered_witness_execution"][
        "observed"
    ]["reason_code"] == "collision_image_mismatch"

    second, interface = _rational_parameterization(
        p_domain=["-1/4"],
        source_refs=["sha256:" + rejected["receipt_sha256"]],
    )
    assert second["lineage"] == {"kind": "root"}
    forge, family, _execution, origin_row, accepted = _lower_and_execute(
        second, interface
    )
    assert accepted["status"] == "witness_found"
    assert accepted["ratification_status"] == (
        "construction_witness_pending_source_neutral_ratification"
    )
    admission = build_reviewed_family_member_ratification_admission(
        family=family,
        family_execution=accepted,
        forge_quarantine_receipt=forge,
        witness_interface=interface,
        parameter_id=family["parameter_ids"][0],
        construction_origin=origin_row,
    )
    assert admission["construction_origin_sha256s"] == accepted[
        "construction_origin_sha256s"
    ]


def test_execution_join_rejects_self_hashed_uncertified_assignment() -> None:
    parameterization, interface = _binary_parameterization()
    execution = execute_construction_parameterization(
        parameterization, witness_schema=interface["witness_schema"]
    )
    forged = deepcopy(execution)
    residual = forged["residuals"][0]
    residual["assignment"] = {"row": "0x3"}
    residual["assignment_sha256"] = content_hash(residual["assignment"])
    residual["parameter_id"] = "assignment:" + residual[
        "assignment_sha256"
    ]
    residual_core = {key: value for key, value in residual.items() if key != "receipt_sha256"}
    residual["receipt_sha256"] = content_hash(residual_core)
    core = {key: value for key, value in forged.items() if key != "receipt_sha256"}
    forged["receipt_sha256"] = content_hash(core)
    validate_construction_parameterization_execution(forged)
    with pytest.raises(
        ConstructionParameterizationError,
        match="certified assignment authority",
    ):
        admit_persisted_construction_execution(
            parameterization,
            forged,
            witness_schema=interface["witness_schema"],
        )


def test_runtime_admission_is_immutable_and_copy_loses_authority() -> None:
    parameterization, interface = _binary_parameterization(rows=["0x1"])
    admitted = admit_construction_parameterization(parameterization)
    materializer = admitted["materializer"]
    materializer["template"]["rows_hex"] = []
    assert admitted["materializer"] == parameterization["materializer"]
    with pytest.raises(TypeError, match="immutable"):
        admitted._json_bytes = b"{}"
    copied = deepcopy(admitted)
    pickled = pickle.loads(pickle.dumps(admitted))
    assert type(copied) is dict
    assert type(pickled) is dict
    with pytest.raises(
        ConstructionParameterizationError, match="explicit semantic admission"
    ):
        enumerate_parameter_assignments(parameterization)
    with pytest.raises(
        ConstructionParameterizationError, match="explicit semantic admission"
    ):
        certified_construction_parameter_count(parameterization)
    with pytest.raises(
        ConstructionParameterizationError, match="explicit semantic admission"
    ):
        materialize_parameter_artifact(
            parameterization,
            execution_assignment := admitted.assignment_domain[0][1],
            witness_schema=interface["witness_schema"],
        )
    assert execution_assignment
    with pytest.raises(
        ConstructionParameterizationError, match="explicit semantic admission"
    ):
        replay_parameter_artifact_schema(
            parameterization, witness_schema=interface["witness_schema"]
        )

    execution = execute_construction_parameterization(
        admitted, witness_schema=interface["witness_schema"]
    )
    residuals = execution["residuals"]
    residuals[0]["kind"] = "rejection"
    assert execution["residuals"][0]["kind"] == "candidate"
    with pytest.raises(TypeError, match="immutable"):
        execution._json_bytes = b"{}"
    copied_execution = deepcopy(execution)
    pickled_execution = pickle.loads(pickle.dumps(execution))
    assert type(copied_execution) is dict
    assert type(pickled_execution) is dict

    forge = _forge_receipt(parameterization, interface)
    origin = admit_construction_origin(
        parameterization=admitted,
        forge_quarantine_receipt=forge,
        parameterization_execution=execution,
        witness_interface=interface,
    )
    with pytest.raises(TypeError, match="immutable"):
        origin._execution = copied_execution
    copied_origin = deepcopy(origin)
    pickled_origin = pickle.loads(pickle.dumps(origin))
    assert type(copied_origin) is dict
    assert type(pickled_origin) is dict
    assert copied_origin == pickled_origin == origin.to_json()
    with pytest.raises(TypeError, match="host-minted"):
        AdmittedConstructionOrigin(
            parameterization=admitted,
            execution=execution,
            forge_receipt=forge,
            witness_interface_sha256=interface["interface_sha256"],
            witness_schema_sha256=content_hash(interface["witness_schema"]),
            _token=object(),
        )


def test_depth_guard_is_shared_and_callbacks_are_never_reached() -> None:
    nested: object = "leaf"
    for _ in range(1_200):
        nested = [nested]
    with pytest.raises(ValueError, match="nesting depth"):
        strict_json_data(nested, context="deep fixture")

    parameterization, interface = _binary_parameterization()
    deep = deepcopy(parameterization)
    deep["materializer"] = {
        "schema": SAFE_ARTIFACT_TEMPLATE_SCHEMA,
        "template": {"deep": nested},
    }
    with pytest.raises(ConstructionParameterizationError, match="nesting depth"):
        validate_construction_parameterization(deep)

    family, execution = lower_reviewed_construction_parameterization(
        parameterization,
        forge_quarantine_receipt=_forge_receipt(parameterization, interface),
        witness_interface=interface,
    )
    assert family is not None
    deep_family = deepcopy(family)
    deep_family["members"][0]["derivation"] = {"deep": nested}
    with pytest.raises(ValueError, match="nesting depth"):
        validate_finite_construction_family(deep_family)

    calls = 0

    def unreachable(**_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("callback reached")

    with pytest.raises(ValueError, match="nesting depth"):
        execute_registered_witness_artifact(
            adapter_id=BINARY_ADAPTER_ID,
            witness_interface=interface,
            artifact={"deep": nested},
            normalizer_fn=unreachable,
            verifier_fn=unreachable,
        )
    assert calls == 0


def test_direct_parameterization_validation_bounds_atom_and_envelope_bytes(
    monkeypatch,
) -> None:
    import ztare.leanmill.construction_parameterization as construction_module

    parameterization, _interface = _binary_parameterization(rows=["0x1"])
    oversized_atom = deepcopy(parameterization)
    oversized_atom["parameter_space"]["variables"][0]["domain"] = [
        "x" * 65_537
    ]
    atom_core = {
        key: value
        for key, value in oversized_atom.items()
        if key not in {"parameterization_id", "receipt_sha256"}
    }
    oversized_atom["parameterization_id"] = (
        "construction-parameterization:" + content_hash(atom_core)
    )
    oversized_atom["receipt_sha256"] = content_hash(
        {**atom_core, "parameterization_id": oversized_atom["parameterization_id"]}
    )
    assert validate_construction_parameterization(oversized_atom) == oversized_atom
    with pytest.raises(
        ConstructionParameterizationError, match="JSON-(?:atom|scalar).*wire ceiling"
    ):
        admit_construction_parameterization(oversized_atom)

    oversized_integer = deepcopy(parameterization)
    oversized_integer["parameter_space"]["variables"][0]["domain"] = [
        1 << 4_096
    ]
    with pytest.raises(
        ConstructionParameterizationError, match="integer bit ceiling"
    ):
        validate_construction_parameterization(oversized_integer)

    monkeypatch.setattr(
        construction_module,
        "_MAX_PARAMETERIZATION_ENVELOPE_BYTES",
        1_024,
    )
    with pytest.raises(
        ConstructionParameterizationError, match="maximum JSON wire size"
    ):
        validate_construction_parameterization(parameterization)


def test_reviewed_family_public_validators_are_depth_total() -> None:
    nested: object = "leaf"
    for _ in range(1_200):
        nested = [nested]
    hostile = {"deep": nested}
    for validator in (
        validate_reviewed_family_member_ratification_admission,
        validate_reviewed_family_exhaustion_observation,
        validate_reviewed_family_objective_discharge,
    ):
        with pytest.raises(ValueError, match="nesting depth"):
            validator(hostile)


def test_rational_wire_and_root_lineage_remain_canonical() -> None:
    assert str(parse_canonical_rational("-1/4")) == "-1/4"
    for value in ("2/4", "01", "1/" + "1" * 129):
        with pytest.raises(ValueError, match="rational"):
            parse_canonical_rational(value)

    parameterization, interface = _binary_parameterization()
    with pytest.raises(ConstructionParameterizationError, match="lineage kind"):
        build_construction_parameterization(
            campaign_id=parameterization["campaign_id"],
            request_id=parameterization["request_id"],
            gap_id=parameterization["gap_id"],
            context_hash=parameterization["context_hash"],
            context_epoch=parameterization["context_epoch"],
            adapter_id=parameterization["adapter_id"],
            target_interface_sha256=interface["interface_sha256"],
            source_refs=parameterization["source_refs"],
            parameter_space=parameterization["parameter_space"],
            backend_problem=parameterization["backend_problem"],
            materializer=parameterization["materializer"],
            backend=parameterization["backend"],
            resource_limits=parameterization["resource_limits"],
            search_order=parameterization["search_order"],
            lineage={
                "kind": "typed_residual_revision",
                "parent_parameterization_sha256": "f" * 64,
            },
            authorship={
                **parameterization["authorship"],
                "phase": "typed_residual_revision",
            },
        )


def test_binary_capabilities_exclude_rational_backends_and_authoring_is_dynamic() -> None:
    capabilities = theory_adapter_capabilities(BINARY_ADAPTER_ID)
    assert explicit_finite_json.CAPABILITY_ID in capabilities
    assert FINITE_EXACT_BACKEND_ID not in capabilities
    assert GROEBNER_RATIONAL_BACKEND_ID not in capabilities

    contract = construction_parameterization_authoring_contract(
        campaign_id="campaign:binary-contract",
        request_id="request:binary-contract",
        gap_id="gap:binary-contract",
        context_hash="context:binary-contract",
        context_epoch=1,
        adapter_id=BINARY_ADAPTER_ID,
        witness_interface=_binary_interface(),
    )
    rows = contract["construction_backend_capabilities"]
    assert [row["backend_capability"]["capability_id"] for row in rows] == [
        explicit_finite_json.CAPABILITY_ID
    ]
    assert "rational" not in json.dumps(contract).lower()
    assert "groebner" not in json.dumps(contract).lower()


def test_wrong_capability_role_is_rejected_before_invocation(monkeypatch) -> None:
    capability_id = next(
        item
        for item in theory_adapter_capabilities(BINARY_ADAPTER_ID)
        if item != explicit_finite_json.CAPABILITY_ID
    )
    calls = 0
    original = binary_adapter_module.CAPABILITIES[capability_id]

    def forbidden(**kwargs):
        nonlocal calls
        calls += 1
        return original(**kwargs)

    monkeypatch.setitem(
        binary_adapter_module.CAPABILITIES, capability_id, forbidden
    )
    with pytest.raises(
        ConstructionParameterizationError,
        match="construction-backend role metadata",
    ):
        _binary_parameterization(
            backend={
                "adapter_id": BINARY_ADAPTER_ID,
                "capability_id": capability_id,
                "contract_sha256": "e" * 64,
            }
        )
    assert calls == 0


def test_opaque_custom_backend_dispatch_needs_no_common_protocol_branch(
    monkeypatch,
) -> None:
    capability_id = "fixture_opaque_construction_backend.v1"
    contract = {
        "scalar_semantics": "opaque_fixture_domain",
        "problem_fragment": "custom_decidable_fixture",
        "failure_mode": "typed_residual",
    }
    descriptor = {
        "adapter_id": BINARY_ADAPTER_ID,
        "capability_id": capability_id,
        "contract_sha256": content_hash(contract),
    }
    space = {
        "schema": "fixture.opaque_parameter_space.v1",
        "variables": [{
            "parameter_id": "row",
            "sort": "opaque_atom",
            "domain": ["0x1", "0x2"],
        }],
    }
    problem = {
        "schema": "fixture.opaque_backend_problem.v1",
        "semantics": "defined_only_by_registered_fixture_capability",
        "predicate": "accept_all",
    }
    assignments = tuple(
        (
            "assignment:" + content_hash({"row": value}),
            {"row": value},
        )
        for value in ("0x1", "0x2")
    )
    mode = {"enumeration": "valid", "execution": "valid"}
    calls = {"validate": 0, "enumerate": 0, "execute": 0}

    def capability(*, operation: str, backend: dict, **kwargs):
        assert backend == descriptor
        if operation == "authoring_contract":
            return {
                "backend_capability": descriptor,
                "parameter_space_schema": space["schema"],
                "allowed_parameter_sorts": ["opaque_atom"],
                "backend_problem_schema": problem["schema"],
                "backend_resource_ceilings": {},
                "availability": "available",
            }
        if operation == "validate_problem":
            calls["validate"] += 1
            assert kwargs["parameter_space"] == space
            assert kwargs["backend_problem"] == problem
            return {
                "backend": descriptor,
                "parameter_space": space,
                "backend_problem": problem,
                "parameter_ids": ["row"],
                "parameter_sorts": {"row": "opaque_atom"},
                "cardinality": 2,
                "projected_assignment_wire_bytes": (
                    project_explicit_assignment_wire_bytes(
                        parameter_ids=["row"],
                        domains=[["0x1", "0x2"]],
                    )
                ),
            }
        if operation == "enumerate_assignments":
            calls["enumerate"] += 1
            if mode["enumeration"] == "omit":
                return assignments[:1]
            if mode["enumeration"] == "duplicate":
                return (assignments[0], assignments[0])
            if mode["enumeration"] == "amplify":
                return (*assignments, assignments[0])
            return assignments
        if operation == "execute_problem":
            calls["execute"] += 1
            if mode["execution"] == "runtime_unavailable":
                raise TimeoutError("fixture backend timeout")
            if mode["execution"] == "spam_materialize":
                for _ in range(10_000):
                    kwargs["materialize"](assignments[0][1])
            selected = assignments
            if mode["execution"] == "invent":
                invented = {"row": "0x3"}
                selected = (("assignment:" + content_hash(invented), invented),)
            elif mode["execution"] == "omit":
                selected = assignments[:1]
            residuals = []
            for parameter_id, assignment in selected:
                rejecting = mode["execution"] == "reject"
                artifact = (
                    None if rejecting else kwargs["materialize"](assignment)
                )
                residuals.append({
                    "parameter_id": parameter_id,
                    "assignment": assignment,
                    "artifact_sha256": (
                        "0" * 64
                        if mode["execution"] == "bad_digest"
                        else ""
                        if rejecting
                        else content_hash(artifact)
                    ),
                    "kind": "rejection" if rejecting else "candidate",
                    "reason_code": (
                        "custom_predicate_rejected"
                        if rejecting
                        else "custom_predicate_satisfied"
                    ),
                    "backend_check_id": "",
                    "observed": {"custom_backend": "opaque_fixture"},
                })
            return {
                "status": "completed",
                "expected_parameter_count": 2,
                "residuals": residuals,
                "coverage_complete": True,
                "resource_usage": {
                    "field_operations": 0,
                    "materialized_artifact_bytes": 0,
                },
            }
        raise AssertionError(operation)

    monkeypatch.setitem(
        binary_adapter_module.CAPABILITIES, capability_id, capability
    )
    monkeypatch.setitem(
        binary_adapter_module.CAPABILITY_CONTRACTS,
        capability_id,
        {
            "role": "construction_backend",
            "contract": contract,
            "contract_sha256": content_hash(contract),
        },
    )
    monkeypatch.setattr(
        rational_backend,
        "parse_canonical_rational",
        lambda _value: (_ for _ in ()).throw(
            AssertionError("the common protocol called an unrelated Q backend")
        ),
    )
    interface = _binary_interface()
    common_limits = _limits()
    parameterization = build_construction_parameterization(
        campaign_id="campaign:opaque-fixture",
        request_id="request:opaque-fixture",
        gap_id="gap:opaque-fixture",
        context_hash="context:opaque-fixture",
        context_epoch=1,
        adapter_id=BINARY_ADAPTER_ID,
        target_interface_sha256=interface["interface_sha256"],
        source_refs=["fixture:opaque-custom-backend"],
        parameter_space=space,
        backend_problem=problem,
        materializer={
            "schema": SAFE_ARTIFACT_TEMPLATE_SCHEMA,
            "template": {
                "schema": "leanmill.binary_linear_generator_matrix.v1",
                "field_order": 2,
                "length": 2,
                "dimension": 1,
                "coordinate_convention": "bit_i_is_coordinate_i",
                "rows_hex": [{"$parameter": "row"}],
            },
        },
        backend=descriptor,
        resource_limits=common_limits,
        search_order={
            "kind": "lexicographic",
            "parameter_ids": ["row"],
            "domain_order": "declared_canonical",
        },
    )
    authoring = construction_parameterization_authoring_contract(
        campaign_id="campaign:opaque-fixture",
        request_id="request:opaque-fixture",
        gap_id="gap:opaque-fixture",
        context_hash="context:opaque-fixture",
        context_epoch=1,
        adapter_id=BINARY_ADAPTER_ID,
        witness_interface=interface,
    )
    assert descriptor in [
        row["backend_capability"]
        for row in authoring["construction_backend_capabilities"]
    ]
    assert calls == {"validate": 0, "enumerate": 0, "execute": 0}
    forge = _forge_receipt(parameterization, interface)
    assert calls == {"validate": 0, "enumerate": 0, "execute": 0}
    execution = execute_construction_parameterization(
        parameterization,
        witness_schema=interface["witness_schema"],
    )
    assert execution["coverage_complete"] is True
    assert len(execution["residuals"]) == 2
    assert execution["resource_usage"][
        "host_materialized_artifact_bytes"
    ] > 0
    assert execution["resource_usage"]["materialized_artifact_bytes"] == 0
    family, lowered_execution = lower_reviewed_construction_parameterization(
        parameterization,
        forge_quarantine_receipt=forge,
        witness_interface=interface,
        parameterization_execution=execution,
    )
    assert family is not None
    assert lowered_execution == execution
    assert family["family_spec"]["backend_problem_sha256"] == content_hash(
        parameterization["backend_problem"]
    )
    assert calls == {"validate": 1, "enumerate": 1, "execute": 1}

    before_downstream = dict(calls)
    materialize_construction_candidates(
        execution.admitted_parameterization,
        execution,
        witness_schema=interface["witness_schema"],
    )
    assert calls == before_downstream

    cold_parameterization = deepcopy(parameterization)
    cold_execution = deepcopy(execution)
    calls.update(validate=0, enumerate=0, execute=0)
    cold_admitted = admit_persisted_construction_execution(
        cold_parameterization,
        cold_execution,
        witness_schema=interface["witness_schema"],
    )
    assert cold_admitted == execution
    assert calls == {"validate": 1, "enumerate": 1, "execute": 1}
    materialize_construction_candidates(
        cold_admitted.admitted_parameterization,
        cold_admitted,
        witness_schema=interface["witness_schema"],
    )
    assert calls == {"validate": 1, "enumerate": 1, "execute": 1}

    mode["execution"] = "reject"
    rejected = execute_construction_parameterization(
        parameterization,
        witness_schema=interface["witness_schema"],
    )
    forged = deepcopy(rejected)
    forged_residual = forged["residuals"][0]
    forged_artifact = {
        "schema": "leanmill.binary_linear_generator_matrix.v1",
        "field_order": 2,
        "length": 2,
        "dimension": 1,
        "coordinate_convention": "bit_i_is_coordinate_i",
        "rows_hex": [forged_residual["assignment"]["row"]],
    }
    forged_residual["kind"] = "candidate"
    forged_residual["reason_code"] = "custom_predicate_satisfied"
    forged_residual["artifact_sha256"] = content_hash(forged_artifact)
    forged_residual["claim_boundary"] = (
        "constraint_candidate_only_target_adapter_replay_still_required"
    )
    forged_residual_core = {
        key: value
        for key, value in forged_residual.items()
        if key != "receipt_sha256"
    }
    forged_residual["receipt_sha256"] = content_hash(forged_residual_core)
    forged_core = {
        key: value for key, value in forged.items() if key != "receipt_sha256"
    }
    forged["receipt_sha256"] = content_hash(forged_core)
    calls.update(validate=0, enumerate=0, execute=0)
    with pytest.raises(
        ConstructionParameterizationError,
        match="failed semantic replay",
    ):
        admit_persisted_construction_execution(
            deepcopy(parameterization),
            forged,
            witness_schema=interface["witness_schema"],
        )
    assert calls == {"validate": 1, "enumerate": 1, "execute": 1}

    for enumeration_mode, message in (
        ("omit", "assignment coverage"),
        ("duplicate", "repeated an assignment"),
        ("amplify", "assignment coverage"),
    ):
        mode["enumeration"] = enumeration_mode
        with pytest.raises(ConstructionParameterizationError, match=message):
            execute_construction_parameterization(
                parameterization,
                witness_schema=interface["witness_schema"],
            )

    mode["enumeration"] = "valid"
    mode["execution"] = "runtime_unavailable"
    with pytest.raises(
        ConstructionBackendCapabilityUnavailable,
        match="construction_backend_runtime_unavailable",
    ) as unavailable:
        execute_construction_parameterization(
            parameterization,
            witness_schema=interface["witness_schema"],
        )
    assert unavailable.value.operation == "execute_problem"
    assert unavailable.value.capability_id == capability_id
    assert unavailable.value.error_type == "TimeoutError"
    mode["execution"] = "spam_materialize"
    with pytest.raises(
        ConstructionResourceCeilingExceeded,
        match="materialized_artifact_byte_limit_exhausted",
    ):
        execute_construction_parameterization(
            parameterization,
            witness_schema=interface["witness_schema"],
        )
    for execution_mode, message in (
        ("invent", "coverage authority"),
        ("omit", "incomplete assignment coverage"),
        ("bad_digest", "artifact digest mismatch"),
    ):
        mode["execution"] = execution_mode
        with pytest.raises(ConstructionParameterizationError, match=message):
            execute_construction_parameterization(
                parameterization,
                witness_schema=interface["witness_schema"],
            )


def test_campaign_transition_reserves_before_semantics_and_cold_replay_is_free(
    tmp_path, monkeypatch
) -> None:
    from ztare.leanmill import finite_construction_family as family_module

    parameterization, interface = _binary_parameterization()
    forge = _forge_receipt(parameterization, interface)
    budget = budget_preset("smoke_20m")
    write_json_atomic(tmp_path / "budget.json", budget.to_json())
    original_capability = binary_adapter_module.CAPABILITIES[
        explicit_finite_json.CAPABILITY_ID
    ]
    calls = {"validate_problem": 0, "enumerate_assignments": 0, "execute_problem": 0}

    def counted_capability(**kwargs):
        operation = str(kwargs.get("operation") or "")
        if operation in calls:
            calls[operation] += 1
            events = [
                json.loads(line)
                for line in (tmp_path / "budget.events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
                if line.strip()
            ]
            assert any(
                row.get("event_type") == "resources_reserved"
                and row.get("action_id")
                == "construction-parameterization:"
                + parameterization["receipt_sha256"]
                and row.get("phase") == "expansion"
                for row in events
            ) or ExplorationBudgetLedger(
                tmp_path / "budget.events.jsonl",
                budget,
                attempt_id=tmp_path.name,
            ).committed_action_resources(
                "construction-parameterization:"
                + parameterization["receipt_sha256"],
                phase="expansion",
            )["workbench_actions"] >= 2
        return original_capability(**kwargs)

    monkeypatch.setitem(
        binary_adapter_module.CAPABILITIES,
        explicit_finite_json.CAPABILITY_ID,
        counted_capability,
    )
    monkeypatch.setattr(
        family_module,
        "construction_witness_interface",
        lambda *_args, **_kwargs: interface,
    )
    monkeypatch.setattr(
        family_module,
        "lower_reviewed_construction_parameterization",
        lambda _parameterization, **kwargs: (
            None,
            kwargs["parameterization_execution"],
        ),
    )

    def feedback(_directory, _run, **kwargs):
        core = {
            "schema": "fixture.construction_feedback.v1",
            "outcome": kwargs["outcome"],
            "reason": kwargs["reason"],
            "evidence_refs": list(kwargs.get("evidence_refs") or ()),
        }
        return {**core, "receipt_sha256": content_hash(core)}

    def unused(*_args, **_kwargs):
        raise AssertionError("unused construction hook was invoked")

    hooks = ReviewedConstructionHooks(
        approved_parameterization=lambda _directory, _completion: (
            parameterization,
            forge,
        ),
        language_outcome_feedback=feedback,
        approved_family=unused,
        persist_ratification_admissions=unused,
        family_synthesis_provenance=unused,
        frozen_terminal_lineage_ids=unused,
        language_request_from_run=unused,
        current_family_exhaustion_discharge=unused,
    )
    resume_observations = []

    def resume(_directory, **_kwargs):
        events = [
            json.loads(line)
            for line in (tmp_path / "budget.events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        resume_observations.append(events[-1]["event_type"])
        assert events[-1]["event_type"] == "wall_clock_frozen"
        assert list(
            tmp_path.glob("reviewed_construction_advancement_transition.*.json")
        )

    blueprint = SimpleNamespace(
        adapter_id=BINARY_ADAPTER_ID,
        adapter_config={},
    )
    run = {"context_hash": parameterization["context_hash"], "navigation": {}}
    first = advance_reviewed_construction_campaign(
        tmp_path,
        completion={},
        run=run,
        blueprint=blueprint,
        resume_fn=resume,
        _attempt_lease=None,
        hooks=hooks,
    )
    assert first is not None
    assert first["status"] == "construction_parameterization_exhausted"
    assert calls == {
        "validate_problem": 1,
        "enumerate_assignments": 1,
        "execute_problem": 1,
    }
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl", budget, attempt_id=tmp_path.name
    )
    assert ledger.state()["usage"]["workbench_actions"] == 2
    execution_slot = (
        tmp_path
        / (
            "construction_parameterization_execution_by_parameterization_"
            + parameterization["receipt_sha256"][:16]
            + ".json"
        )
    )
    assert execution_slot.is_file()
    assert not list(
        tmp_path.glob("construction_parameterization_execution.*.json")
    )

    exhaust = ledger.reserve(
        "fixture:exhaust-workbench-after-construction",
        "expansion",
        {"workbench_actions": 14},
    )
    ledger.commit(exhaust)
    assert ledger.remaining_capacity("expansion", "workbench_actions") == 0

    calls.update({key: 0 for key in calls})
    second = advance_reviewed_construction_campaign(
        tmp_path,
        completion={},
        run=run,
        blueprint=blueprint,
        resume_fn=resume,
        _attempt_lease=None,
        hooks=hooks,
    )
    assert second is not None
    assert calls == {
        "validate_problem": 1,
        "enumerate_assignments": 1,
        "execute_problem": 1,
    }
    assert ledger.state()["usage"]["workbench_actions"] == 16
    assert resume_observations == ["wall_clock_frozen", "wall_clock_frozen"]

    write_json_atomic(execution_slot, {"malformed": True})
    calls.update({key: 0 for key in calls})
    with pytest.raises(ValueError, match="construction"):
        advance_reviewed_construction_campaign(
            tmp_path,
            completion={},
            run=run,
            blueprint=blueprint,
            resume_fn=resume,
            _attempt_lease=None,
            hooks=hooks,
        )
    assert calls == {
        "validate_problem": 0,
        "enumerate_assignments": 0,
        "execute_problem": 0,
    }


def test_full_cold_transition_family_ratification_replays_backend_once(
    tmp_path, monkeypatch
) -> None:
    from ztare.leanmill import finite_construction_family as family_module

    request = build_theory_language_expansion_request(
        source_context_hash="context:binary-fixture",
        source_epoch=3,
        change_kind="quotient_or_coordinate_change",
        blind_spot="The current chart lacks an executable generator family.",
        proposed_interface="A reviewed parameterized binary-code construction.",
        evidence_refs=("fixture:binary-construction",),
        discriminating_test="Execute every generated matrix and ratify a witness.",
        kill_condition="Return exact rejection or unavailability to navigation.",
    )
    gap_id = "adapter-gap:" + content_hash(
        {"fixture": "full-cold-parameterized-ratification"}
    )
    parameterization, interface = _binary_parameterization(
        request_id=request.request_id,
        gap_id=gap_id,
    )
    forge = _forge_receipt(parameterization, interface)
    monkeypatch.setattr(
        family_module,
        "construction_witness_interface",
        lambda *_args, **_kwargs: interface,
    )
    budget = budget_preset("smoke_20m")
    write_json_atomic(tmp_path / "budget.json", budget.to_json())
    original_capability = binary_adapter_module.CAPABILITIES[
        explicit_finite_json.CAPABILITY_ID
    ]
    calls = {
        "validate_problem": 0,
        "enumerate_assignments": 0,
        "execute_problem": 0,
    }

    def counted_capability(**kwargs):
        operation = str(kwargs.get("operation") or "")
        if operation in calls:
            calls[operation] += 1
        return original_capability(**kwargs)

    monkeypatch.setitem(
        binary_adapter_module.CAPABILITIES,
        explicit_finite_json.CAPABILITY_ID,
        counted_capability,
    )
    admissions: list[dict] = []

    def persist_admissions(directory, **kwargs):
        rows = _persist_reviewed_family_member_ratification_admissions(
            directory, **kwargs
        )
        admissions.extend(rows)
        return rows

    def feedback(*_args, **_kwargs):
        raise AssertionError("witness-found transition emitted language feedback")

    def unused(*_args, **_kwargs):
        raise AssertionError("unused construction hook was invoked")

    hooks = ReviewedConstructionHooks(
        approved_parameterization=lambda _directory, _completion: (
            parameterization,
            forge,
        ),
        language_outcome_feedback=feedback,
        approved_family=unused,
        persist_ratification_admissions=persist_admissions,
        family_synthesis_provenance=unused,
        frozen_terminal_lineage_ids=unused,
        language_request_from_run=unused,
        current_family_exhaustion_discharge=unused,
    )
    run = {
        "context_hash": parameterization["context_hash"],
        "navigation": {
            "context_hash": parameterization["context_hash"],
            "context_epoch": parameterization["context_epoch"],
            "language_expansion_request": request.to_json(),
        },
    }
    result = advance_reviewed_construction_campaign(
        tmp_path,
        completion={},
        run=run,
        blueprint=SimpleNamespace(
            adapter_id=BINARY_ADAPTER_ID,
            adapter_config={},
        ),
        resume_fn=None,
        _attempt_lease=None,
        hooks=hooks,
    )
    assert result is not None
    assert result["status"] == "witness_found_pending_ratification"
    assert calls == {
        "validate_problem": 1,
        "enumerate_assignments": 1,
        "execute_problem": 1,
    }
    assert admissions

    family_paths = list(tmp_path.glob("finite_construction_family.*.json"))
    assert len(family_paths) == 1
    family = read_json(family_paths[0], {})
    family_execution = read_json(
        tmp_path
        / (
            "finite_construction_family_execution."
            + family["receipt_sha256"][:16]
            + ".json"
        ),
        {},
    )
    owner = adapter_forge_attempt_directory(
        tmp_path,
        gap_id,
        host_conformance_contract=(
            ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT
        ),
        create=True,
    )
    completion_core = {
        "schema": "leanmill.adapter_forge_completion.v1",
        "status": (
            "reviewed_campaign_local_construction_parameterization_available"
        ),
        "attempt_dir": str(tmp_path),
        "gap_id": gap_id,
        "host_conformance_contract": (
            ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT
        ),
        "quarantine_receipt": forge,
        "reason": forge["independent_review"]["rationale"],
        "rejection_class": "",
        "recovery_route": "",
        "evidence_refs": [forge["receipt_sha256"]],
        "provider_calls": 0,
    }
    completion = {
        **completion_core,
        "completion_sha256": content_hash(completion_core),
    }
    write_json_atomic(
        owner / "theory_language_construction_parameterization_candidate.json",
        parameterization,
    )
    write_json_atomic(
        tmp_path / "blueprint.json",
        {"adapter_id": BINARY_ADAPTER_ID, "adapter_config": {}},
    )
    write_json_atomic(
        owner / "adapter_forge_completion.json",
        completion,
    )
    hot_completion = _read_adapter_forge_lifecycle_completion(
        tmp_path, SimpleNamespace(gap_id=gap_id)
    )
    assert hot_completion == completion
    approved_parameterization, approved_forge = (
        _approved_construction_parameterization_candidate(
            tmp_path, hot_completion
        )
    )
    assert approved_parameterization == parameterization
    assert approved_forge == forge

    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget,
        attempt_id=tmp_path.name,
    )
    exhaust = ledger.reserve(
        "fixture:exhaust-workbench-before-cold-ratification",
        "expansion",
        {"workbench_actions": 14},
    )
    ledger.commit(exhaust)
    assert ledger.remaining_capacity("expansion", "workbench_actions") == 0
    assert ledger.remaining_capacity("boundary", "boundary_queries") == 0
    calls.update({key: 0 for key in calls})
    provider_calls_before = ledger.state()["usage"]["provider_calls"]
    ledger.recover_interrupted_wall_clock()
    ledger.recover_interrupted_reservations()
    ledger.resume_wall_clock()
    try:
        replayed = _replay_reviewed_family_member_ratification_admissions(
            tmp_path,
            execution=family_execution,
            request=request,
            witness_interface=interface,
            admissions=admissions,
            budget_ledger=ledger,
        )
    finally:
        ledger.freeze_wall_clock(reason="fixture_cold_ratification_exit")

    assert replayed == tuple(admissions)
    assert calls == {
        "validate_problem": 1,
        "enumerate_assignments": 1,
        "execute_problem": 1,
    }
    assert ledger.state()["usage"]["provider_calls"] == provider_calls_before
    assert ledger.state()["usage"]["workbench_actions"] == 16
    assert ledger.state()["usage"]["boundary_queries"] == 2

    from test_reviewed_family_member_ratification import _campaign_blueprint
    from ztare.leanmill.frontier_campaign_runner import (
        execute_frontier_construction_artifact_ratification,
        next_frontier_campaign_action,
    )

    write_json_atomic(
        tmp_path / "blueprint.json", _campaign_blueprint().to_json()
    )
    assert next_frontier_campaign_action(tmp_path) == (
        "ratify_construction_artifact"
    )

    calls.update({key: 0 for key in calls})

    def unavailable_capability(**kwargs):
        operation = str(kwargs.get("operation") or "")
        if operation in calls:
            calls[operation] += 1
        if operation == "validate_problem":
            raise TimeoutError("fixture construction backend unavailable")
        return original_capability(**kwargs)

    monkeypatch.setitem(
        binary_adapter_module.CAPABILITIES,
        explicit_finite_json.CAPABILITY_ID,
        unavailable_capability,
    )
    typed = execute_frontier_construction_artifact_ratification(
        tmp_path,
        lean_root=tmp_path,
        family_ratify_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("unavailable construction replay reached ratification")
        ),
        _attempt_lease=SimpleNamespace(
            binding={"root_context_hash": parameterization["context_hash"]},
            bind_epoch=lambda **_kwargs: None,
        ),
    )
    assert typed["status"] == "returned_to_navigation"
    feedback_row = read_json(
        tmp_path / "theory_language_compilation_feedback.json", {}
    )
    assert feedback_row["outcome"] == "unavailable"
    assert feedback_row["reason"].startswith(
        "reviewed_family_cold_replay_unavailable:"
    )
    assert calls == {
        "validate_problem": 1,
        "enumerate_assignments": 0,
        "execute_problem": 0,
    }
    unavailable_receipts = list(
        tmp_path.glob("reviewed_family_cold_replay_unavailable.*.json")
    )
    assert len(unavailable_receipts) == 1
    unavailable_receipt = read_json(unavailable_receipts[0], {})
    assert unavailable_receipt["operation"] == "validate_problem"
    assert unavailable_receipt["adapter_id"] == BINARY_ADAPTER_ID
    assert unavailable_receipt["capability_id"] == (
        explicit_finite_json.CAPABILITY_ID
    )
    assert unavailable_receipt["cause_error_type"] == "TimeoutError"
    assert unavailable_receipt["certified_assignment_count"] == 0
    assert unavailable_receipt["attempted_assignment_count"] == 0
    assert ledger.state()["usage"]["provider_calls"] == provider_calls_before
    final_events = [
        json.loads(line)
        for line in (tmp_path / "budget.events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert final_events[-1]["event_type"] == "wall_clock_frozen"
