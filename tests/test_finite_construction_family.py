from __future__ import annotations

from copy import deepcopy
import json

import pytest

from ztare.leanmill.finite_construction_family import (
    FINITE_CONSTRUCTION_FAMILY_CLAIM_SCOPE,
    FINITE_CONSTRUCTION_FAMILY_SCHEMA,
    FiniteConstructionFamilyResourceUnavailable,
    construction_witness_interface,
    execute_finite_construction_family,
    finite_construction_family_authoring_contract,
    validate_finite_construction_family,
    validate_finite_construction_family_execution,
)
from ztare.leanmill.theory_adapter_registry import (
    materialize_theory_adapter_capability,
)
from ztare.leanmill.theory_ir import content_hash


def _config() -> dict:
    return {
        "construction_target": {
            "schema": "leanmill.binary_linear_code_target_config.v1",
            "field_order": 2,
            "length": 4,
            "dimension": 2,
            "minimum_distance": 2,
            "max_nonzero_messages": 3,
            "target_snapshot_sha256": "1" * 64,
        }
    }


def _artifact(*rows: str) -> dict:
    return {
        "schema": "leanmill.binary_linear_generator_matrix.v1",
        "field_order": 2,
        "length": 4,
        "dimension": 2,
        "coordinate_convention": "bit_i_is_coordinate_i",
        "rows_hex": list(rows),
    }


def _family(*artifacts: dict) -> tuple[dict, dict]:
    interface = construction_witness_interface("binary_linear_code.v1", _config())
    parameter_ids = [f"p{index}" for index in range(len(artifacts))]
    core = {
        "schema": FINITE_CONSTRUCTION_FAMILY_SCHEMA,
        "request_id": "theory-language-request:test",
        "gap_id": "adapter-gap:test",
        "context_hash": "context:test",
        "adapter_id": "binary_linear_code.v1",
        "family_id": "family:test-explicit-relation",
        "family_scope": "the exact ordered test relation only",
        "family_spec": {"kind": "explicit_test_relation", "version": 1},
        "authorship": {
            "authority": "campaign_local_subscription_leaf",
            "role": "adapter_forge",
        },
        "symmetry_policy": {"kind": "none"},
        "target_interface_sha256": interface["interface_sha256"],
        "declared_cardinality": len(artifacts),
        "parameter_ids": parameter_ids,
        "parameter_domain_sha256": content_hash(parameter_ids),
        "members": [
            {
                "parameter_id": parameter_id,
                "artifact": artifact,
                "artifact_sha256": content_hash(artifact),
                "derivation": {"kind": "fixture", "index": index},
                "source_refs": ["fixture:seed"],
            }
            for index, (parameter_id, artifact) in enumerate(
                zip(parameter_ids, artifacts, strict=True)
            )
        ],
        "claim_scope": FINITE_CONSTRUCTION_FAMILY_CLAIM_SCOPE,
    }
    return {**core, "receipt_sha256": content_hash(core)}, interface


def _capability(**kwargs):
    descriptor = kwargs.pop("descriptor")
    return materialize_theory_adapter_capability(
        descriptor["adapter_id"], descriptor["capability_id"],
        descriptor=descriptor, **kwargs,
    )


def test_finite_family_executes_registered_adapter_and_separates_ratification():
    family, interface = _family(_artifact("0x3", "0xc"), _artifact("0x1", "0x2"))
    result = execute_finite_construction_family(
        family, witness_interface=interface, capability_fn=_capability
    )

    assert result["status"] == "witness_found"
    assert [
        row["registered_witness_execution"]["status"]
        for row in result["member_results"]
    ] == [
        "verified", "rejected"
    ]
    assert result["ratification_status"] == "discovered_pending_ratification"
    assert result["kernel_ratification_authority"] is False
    assert result["global_nonexistence_authority"] is False
    assert validate_finite_construction_family_execution(result) == result


def test_finite_family_preserves_duplicate_parameter_coverage_and_reuses_work():
    artifact = _artifact("0x1", "0x2")
    family, interface = _family(artifact, artifact)
    calls = 0

    def counted(**kwargs):
        nonlocal calls
        calls += 1
        return _capability(**kwargs)

    result = execute_finite_construction_family(
        family, witness_interface=interface, capability_fn=counted
    )

    assert result["status"] == "exhausted"
    assert result["expected_parameter_ids"] == ["p0", "p1"]
    assert result["observed_parameter_ids"] == ["p0", "p1"]
    assert result["unique_source_artifact_count"] == 1
    assert result["member_results"][1]["reused_from_parameter_id"] == "p0"
    assert calls == 4  # two normalization and two verification replays


def test_duplicate_execution_amplification_hits_incremental_host_ceiling(
    monkeypatch,
):
    import ztare.leanmill.finite_construction_family as family_module

    artifact = _artifact("0x1", "0x2")
    one, interface = _family(artifact)
    baseline = execute_finite_construction_family(
        one, witness_interface=interface, capability_fn=_capability
    )
    one_result_bytes = len(
        json.dumps(
            baseline["member_results"][0],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    monkeypatch.setattr(
        family_module,
        "_MAX_FAMILY_EXECUTION_MEMBER_BYTES",
        one_result_bytes + 1,
    )
    aliases, interface = _family(artifact, artifact, artifact)
    with pytest.raises(FiniteConstructionFamilyResourceUnavailable) as caught:
        execute_finite_construction_family(
            aliases,
            witness_interface=interface,
            capability_fn=_capability,
        )
    assert caught.value.reason_code == (
        "finite_family_execution_byte_limit_exhausted"
    )
    assert caught.value.completed_members == 1
    assert caught.value.attempted_members == 2
    assert caught.value.observed > caught.value.ceiling


def test_finite_family_refuses_missing_member_and_post_review_mutation():
    family, interface = _family(_artifact("0x1", "0x2"), _artifact("0x3", "0xc"))
    missing = deepcopy(family)
    missing["members"].pop()
    missing_core = {key: value for key, value in missing.items() if key != "receipt_sha256"}
    missing["receipt_sha256"] = content_hash(missing_core)
    with pytest.raises(ValueError, match="parameter domain is not exact"):
        validate_finite_construction_family(missing, witness_interface=interface)

    mutated = deepcopy(family)
    mutated["members"][0]["artifact"] = _artifact("0x3", "0xc")
    with pytest.raises(ValueError, match="digest"):
        validate_finite_construction_family(mutated, witness_interface=interface)


def test_finite_family_authoring_contract_requires_string_refs_and_no_outcomes():
    family, interface = _family(_artifact("0x1", "0x2"))
    contract = finite_construction_family_authoring_contract(
        request_id=family["request_id"],
        gap_id=family["gap_id"],
        context_hash=family["context_hash"],
        adapter_id=family["adapter_id"],
        witness_interface=interface,
    )

    assert "nonempty string identities" in contract["field_contracts"]["source_refs"]
    assert "must not run" in contract["pre_review_self_test_boundary"]

    embedded = deepcopy(family)
    embedded["members"][0]["source_refs"] = [{"artifact_ref": "fixture:seed"}]
    embedded_core = {
        key: value for key, value in embedded.items() if key != "receipt_sha256"
    }
    embedded["receipt_sha256"] = content_hash(embedded_core)
    with pytest.raises(ValueError, match="source_refs must be strings"):
        validate_finite_construction_family(embedded, witness_interface=interface)


def test_unavailable_member_prevents_family_exhaustion():
    family, interface = _family(_artifact("0x1", "0x2"))

    def unavailable(*, descriptor, **kwargs):
        if descriptor["capability_id"] == "binary_linear_code_exact_verifier":
            return {"outcome": "unavailable", "observed": {}, "evidence_refs": []}
        return _capability(descriptor=descriptor, **kwargs)

    result = execute_finite_construction_family(
        family, witness_interface=interface, capability_fn=unavailable
    )
    assert result["status"] == "unavailable"
    assert result["coverage_complete"] is True
    assert (
        result["member_results"][0]["registered_witness_execution"]["status"]
        == "unavailable"
    )


def test_finite_family_detects_nondeterministic_registered_capability():
    family, interface = _family(_artifact("0x1", "0x2"))
    calls = 0

    def nondeterministic(*, descriptor, **kwargs):
        nonlocal calls
        calls += 1
        value = _capability(descriptor=descriptor, **kwargs)
        if descriptor["capability_id"] == "binary_generator_row_basis_normalizer" and calls == 2:
            changed = deepcopy(value)
            changed["rows_hex"] = list(reversed(changed["rows_hex"]))
            return changed
        return value

    with pytest.raises(ValueError, match="normalizer is nondeterministic"):
        execute_finite_construction_family(
            family, witness_interface=interface, capability_fn=nondeterministic
        )


def test_family_execution_replay_rejects_member_injection_and_false_exhaustion():
    artifact = _artifact("0x1", "0x2")
    family, interface = _family(artifact, artifact)
    result = execute_finite_construction_family(
        family, witness_interface=interface, capability_fn=_capability
    )

    injected = deepcopy(result)
    injected["member_results"][0]["unreviewed"] = True
    member_core = {
        key: value
        for key, value in injected["member_results"][0].items()
        if key != "receipt_sha256"
    }
    injected["member_results"][0]["receipt_sha256"] = content_hash(member_core)
    injected_core = {
        key: value for key, value in injected.items() if key != "receipt_sha256"
    }
    injected["receipt_sha256"] = content_hash(injected_core)
    with pytest.raises(ValueError, match="member fields changed identity"):
        validate_finite_construction_family_execution(injected)

    unavailable = deepcopy(result)
    registered = unavailable["member_results"][0]["registered_witness_execution"]
    registered["reason_code"] = "invented_relabel"
    registered_core = {
        key: value for key, value in registered.items() if key != "receipt_sha256"
    }
    registered["receipt_sha256"] = content_hash(registered_core)
    unavailable["member_results"][0]["registered_witness_execution_sha256"] = (
        registered["receipt_sha256"]
    )
    member_core = {
        key: value
        for key, value in unavailable["member_results"][0].items()
        if key != "receipt_sha256"
    }
    unavailable["member_results"][0]["receipt_sha256"] = content_hash(member_core)
    unavailable_core = {
        key: value for key, value in unavailable.items() if key != "receipt_sha256"
    }
    unavailable["receipt_sha256"] = content_hash(unavailable_core)
    with pytest.raises(ValueError, match="completion is malformed"):
        validate_finite_construction_family_execution(
            unavailable,
            family=family,
            witness_interface=interface,
        )


def test_ordinary_family_cannot_borrow_exact_constraint_authority():
    family, interface = _family(_artifact("0x1", "0x2"))
    result = execute_finite_construction_family(
        family, witness_interface=interface, capability_fn=_capability
    )
    forged = deepcopy(result)
    member = forged["member_results"][0]
    member["authority"] = "exact_construction_parameterization_join"
    member_core = {
        key: value for key, value in member.items() if key != "receipt_sha256"
    }
    member["receipt_sha256"] = content_hash(member_core)
    result_core = {
        key: value for key, value in forged.items() if key != "receipt_sha256"
    }
    forged["receipt_sha256"] = content_hash(result_core)

    with pytest.raises(ValueError, match="digest mismatch"):
        validate_finite_construction_family_execution(
            forged,
            family=family,
            witness_interface=interface,
        )


def test_ordinary_family_cannot_borrow_parameterized_status_or_claim():
    family, interface = _family(_artifact("0x3", "0xc"))
    result = execute_finite_construction_family(
        family, witness_interface=interface, capability_fn=_capability
    )
    assert result["status"] == "witness_found"

    for field, value in (
        (
            "ratification_status",
            "construction_witness_pending_source_neutral_ratification",
        ),
        ("family_claim", "an invented reviewed-family claim"),
    ):
        forged = deepcopy(result)
        forged[field] = value
        core = {
            key: item for key, item in forged.items() if key != "receipt_sha256"
        }
        forged["receipt_sha256"] = content_hash(core)
        with pytest.raises(ValueError, match="outcome algebra"):
            validate_finite_construction_family_execution(
                forged,
                family=family,
                witness_interface=interface,
            )
