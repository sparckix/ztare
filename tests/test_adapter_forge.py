from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re

import pytest

import ztare.leanmill.adapter_forge as adapter_forge_module

from ztare.common.schema_routes import audit_project_schema_routes
from ztare.leanmill.adapter_forge import (
    ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT,
    ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
    ADAPTER_FORGE_REJECTION_PRE_REVIEW_LEAKAGE,
    ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT,
    AdapterGap,
    AdapterGapRequired,
    AdapterForgeHostCapabilityUnavailable,
    AdapterForgeHostConformanceRejected,
    _normalize_object_coordinates,
    _normalize_observable_path,
    adapter_forge_agent_output_schema,
    adapter_forge_attempt_directory,
    adapter_forge_gap_directory,
    execute_adapter_forge_attempt,
    host_capability_conformance,
    read_adapter_forge_completion,
    read_scoped_adapter_forge_completion,
    render_adapter_forge_prompt,
    run_adapter_forge,
    stage_adapter_forge_workspace,
)
from ztare.leanmill.common import read_json, write_json_atomic, write_text_atomic
from ztare.leanmill.exploration_budget import (
    BudgetExceeded,
    ExplorationBudget,
    ExplorationBudgetLedger,
    budget_preset,
)
from ztare.leanmill.equational_formula_universe import (
    EQUATIONAL_GRAMMAR_SCHEMA,
)
from ztare.leanmill.explore_axiom_space import (
    _resolve_workbench_evidence_receipts,
    explore_axiom_space,
)
from ztare.leanmill.finite_model import FiniteModel, evaluate_axiom
from ztare.leanmill.finite_theory_context import load_formal_theory_context
from ztare.leanmill.evidence_theory_context import save_evidence_theory_context
from ztare.leanmill.adapters.generic_finite_evidence import build_evidence_context
from ztare.leanmill.adapters.binary_linear_code import (
    ADAPTER_ID as BINARY_ADAPTER_ID,
    binary_witness_construction_interface,
)
from ztare.leanmill.adapters.construction_backends import explicit_finite_json
from ztare.leanmill.construction_parameterization import (
    CONSTRUCTION_PARAMETERIZATION_SCHEMA,
    SAFE_ARTIFACT_TEMPLATE_SCHEMA,
    build_construction_parameterization,
)
from ztare.leanmill.formal_verification_provider import generate_keypair
from ztare.leanmill.frontier_campaign import sign_frontier_campaign
from ztare.leanmill.frontier_campaign_definition import FrontierCampaignDefinition
from ztare.leanmill.frontier_blueprint import (
    FrontierExplorationBrief,
    THEORY_TASK_CAPABILITY_SCOPE_SCHEMA,
)
from ztare.leanmill.frontier_blueprint_compiler import compile_frontier_blueprint
from ztare.leanmill.frontier_campaign_runner import (
    _approved_finite_family_candidate,
    _adapter_forge_frozen_input_manifest,
    _read_adapter_forge_lifecycle_completion,
    _validate_adapter_forge_recovery_transition,
    _verify_adapter_forge_frozen_inputs,
    _language_outcome_feedback,
    _reopen_extended_adapter_recovery,
    advance_frontier_language_expansion,
    execute_frontier_adapter_forge,
    next_frontier_campaign_action,
)
from ztare.leanmill.frontier_agent_runtime import (
    FrontierAgentConfig,
    _validate_codex_strict_schema,
)
from ztare.leanmill.generative_representation import (
    CANDIDATE_SCHEMA,
    ISOMORPHISM_POLICY,
)
from ztare.leanmill.finite_construction_family import (
    FINITE_CONSTRUCTION_FAMILY_CLAIM_SCOPE,
    FINITE_CONSTRUCTION_FAMILY_SCHEMA,
    construction_witness_interface,
)
from ztare.leanmill.magma_law_universe import anonymous_magma_signature
from ztare.leanmill.theory_ir import OperationSymbol, SortDecl, TheorySignature
from ztare.leanmill.theory_navigator import run_interactive_theory_navigator
from ztare.leanmill.theory_adapter_registry import registered_theory_adapter_ids
from ztare.leanmill.theory_adapter_registry import materialize_theory_adapter_capability
from ztare.leanmill.theory_ir import content_hash

from test_explore_axiom_space import _draft


def _evidence_family_gap(context_hash: str) -> AdapterGap:
    binding_core = {
        "schema": "leanmill.governed_mixed_evidence_binding.v1",
        "receipt_ids": [],
        "evidence": [],
        "contrast_object_pairs": [],
    }
    request = {
        "schema": "leanmill.theory_language_expansion_request.v1",
        "request_id": "theory-language-request:evidence-family",
        "source_context_hash": context_hash,
        "source_epoch": 0,
        "change_kind": "new_operation",
        "blind_spot": "The frozen evidence has no finite lowering operation.",
        "proposed_interface": "One explicit finite construction relation.",
        "evidence_refs": [],
        "discriminating_test": "Enumerate and verify every reviewed member.",
        "kill_condition": "Any member is absent or unverifiable.",
        "required_transition": "new_reviewed_blueprint_or_adapter_capability",
        "authority": "proposal_only",
    }
    return AdapterGap(
        brief_digest="brief:evidence-family",
        proposed_adapter_id="binary_linear_code.v1",
        primitive_semantics_contract={
            "source_adapter_id": "binary_linear_code.v1",
            "theory_language_request": request,
            "evidence_binding": {
                **binding_core,
                "receipt_sha256": content_hash(binding_core),
            },
        },
        raw_fixture_refs=(),
        required_context_kind="exact",
        required_operations=("lower_theory_language_request", "build_context"),
        required_receipts=("determinism", "coverage"),
        forbidden_authorities=("live_registry_mutation",),
        acceptance_tests=("every reviewed family member is joined",),
        gap_kind="capability_missing",
        missing_capabilities=("theory_language:new_operation",),
    )


def test_capability_forge_prompt_exposes_v2_functor_formula_grammar():
    gap = AdapterGap(
        brief_digest="brief:prompt-contract",
        proposed_adapter_id="example.v1",
        primitive_semantics_contract={},
        raw_fixture_refs=("fixture:prompt",),
        required_context_kind="exact",
        required_operations=(),
        required_receipts=("host_conformance",),
        forbidden_authorities=("registry_mutation",),
        acceptance_tests=("target grammar compiles",),
        gap_kind="capability_missing",
        missing_capabilities=("coordinate_functor",),
    )

    prompt = render_adapter_forge_prompt(gap)

    assert "`formula_grammar`" in prompt
    assert "inert JSON artifact" in prompt
    assert "Python module exposing" not in prompt
    assert "Evidence-incidence and cross-signature successor" in prompt
    assert "applications require v2" in prompt


def test_adapter_forge_subscription_schema_is_codex_strict():
    schema = adapter_forge_agent_output_schema()
    assert "uniqueItems" not in json.dumps(schema)
    _validate_codex_strict_schema(schema)


def test_adapter_review_subscription_schema_is_codex_strict():
    schema = adapter_forge_module.adapter_review_output_schema()
    assert "uniqueItems" not in json.dumps(schema)
    _validate_codex_strict_schema(schema)


def test_coding_contract_failure_is_rejected_before_host_or_review():
    gap = _evidence_family_gap("context:coding-contract")
    calls = {"host": 0, "review": 0}

    def host(_proposal, _gap):
        calls["host"] += 1
        raise AssertionError("coding-contract rejection must skip host")

    def review(_payload):
        calls["review"] += 1
        raise AssertionError("coding-contract rejection must skip review")

    receipt = run_adapter_forge(
        gap,
        coding_agent_fn=lambda _prompt: (_ for _ in ()).throw(
            ValueError("Codex output schema object has optional fields at $")
        ),
        host_conformance_fn=host,
        independent_review_fn=review,
    )

    assert calls == {"host": 0, "review": 0}
    assert receipt["status"] == "quarantined_capability_rejected"
    assert receipt["host_conformance"]["rejection_class"] == (
        ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT
    )


def _three_object_evidence_context():
    return build_evidence_context(
        TheorySignature(name="Evidence", sorts=(SortDecl("Observation"),)),
        adapter_config={
            "completeness_ref": "fixture:complete",
            "objects": [
                {"object_id": "o0", "payload": {"source": "left"}},
                {"object_id": "o1", "payload": {"source": "middle"}},
                {"object_id": "o2", "payload": {"source": "right"}},
            ],
            "hypotheses": [
                {
                    "hypothesis_id": "h0",
                    "satisfied_object_ids": ["o0", "o1", "o2"],
                    "anonymous_shape": {"kind": "predicate", "slot": 0},
                }
            ],
        },
        strata=(),
    )


def test_object_coordinate_interface_accepts_its_declared_envelope():
    request_id = "theory-language-request:" + "a" * 64
    coordinates = {
        "object:one": {"profile": "left"},
        "object:two": {"profile": "right"},
    }
    envelope = {
        "schema": "leanmill.object_coordinates.v1",
        "request_id": request_id,
        "coordinates": coordinates,
    }

    assert _normalize_object_coordinates(
        envelope,
        request_id=request_id,
    ) == coordinates
    with pytest.raises(ValueError, match="crossed its request"):
        _normalize_object_coordinates(
            envelope,
            request_id="theory-language-request:" + "b" * 64,
        )


def test_object_coordinate_observable_paths_compile_to_local_keys():
    assert _normalize_observable_path(
        "/coordinates/*/quotient/class_count"
    ) == ("quotient", "class_count")
    assert _normalize_observable_path("quotient.class_count") == (
        "quotient",
        "class_count",
    )
    with pytest.raises(ValueError, match="must select /coordinates/\\*"):
        _normalize_observable_path("/objects/*/quotient")


def _unknown_draft():
    return {
        "mode": "anonymous_signature_census",
        "eigenquestion": "Which regions form?",
        "signature": anonymous_magma_signature().to_json(),
        "primitive_semantics": {
            "operation_bindings": {"op0": "custom executable binary law"},
            "relation_bindings": {},
        },
        "base_axioms": (), "base_theory_status": "explicit_empty",
        "adapter_id": "unbuilt_custom_substrate.v1",
        "adapter_config": {}, "formula_grammar": {"kind": "bounded"},
        "model_or_observation_strata": ({"carrier_size": 2},),
        "pack_arity": 2, "collapse_controls": (),
        "visible_evidence_manifest": {},
        "sealed_evidence_manifest_digest": "sha256:" + "0" * 64,
        "deanchoring_policy": {"cold": True}, "navigator_contract": {},
        "query_budget": {}, "stop_rule": {}, "verification_plan": {},
        "codec_versions": {}, "authority_refs": ("authority",),
    }


def test_unknown_adapter_becomes_typed_gap_not_guessed_campaign():
    brief = FrontierExplorationBrief(
        direction="Explore a custom finite substrate.",
        source_mode="human_directed",
        evidence_refs=("fixture:one",),
    )
    with pytest.raises(AdapterGapRequired) as caught:
        compile_frontier_blueprint(
            brief,
            draft_fn=lambda _brief: _unknown_draft(),
            semantic_review_fn=lambda _payload: {
                "accepted": True, "candidate_law_leakage": False,
                "rationale": "direction preserved", "evidence_refs": ["fixture:one"],
            },
            compiler_ref="compiler", reviewer_ref="reviewer",
        )
    gap = caught.value.gap
    assert gap.raw_fixture_refs == ("fixture:one",)
    assert gap.required_context_kind == "exact"
    assert "candidate axioms" in render_adapter_forge_prompt(gap)


def test_adapter_forge_only_emits_quarantined_proposal():
    brief = FrontierExplorationBrief(direction="Explore custom.", source_mode="human_directed")
    try:
        compile_frontier_blueprint(
            brief, draft_fn=lambda _brief: _unknown_draft(),
            semantic_review_fn=lambda _payload: {
                "accepted": True, "candidate_law_leakage": False,
                "rationale": "preserved", "evidence_refs": [brief.brief_id],
            }, compiler_ref="a", reviewer_ref="b",
        )
    except AdapterGapRequired as exc:
        gap = exc.gap
    receipt = run_adapter_forge(
        gap,
        coding_agent_fn=lambda _prompt: {
            "source_paths": ["adapter.py"], "test_paths": ["test_adapter.py"],
            "manifest": {"adapter_id": gap.proposed_adapter_id},
            "self_test_receipts": ["sha256:test"],
        },
        host_conformance_fn=lambda _proposal, _gap: {
            "ok": True,
            "tests": 8,
            "receipt_sha256": content_hash({"ok": True, "tests": 8}),
        },
        independent_review_fn=lambda payload: {
            "accepted": True,
            "reviewer_ref": "cold-reviewer",
            "rationale": "the frozen host receipt satisfies the review contract",
            "evidence_refs": [
                payload["host_conformance"]["receipt_sha256"]
            ],
        },
    )
    assert receipt["status"] == "quarantined_registry_proposal"
    assert receipt["live_registry_mutated"] is False
    assert receipt["exactness_authority_granted"] is False


def test_adapter_forge_review_binding_accepts_typed_host_digest_label():
    gap = AdapterGap(
        brief_digest="brief:test",
        proposed_adapter_id="magma_equational.v1",
        primitive_semantics_contract={"test": "frozen"},
        raw_fixture_refs=("sha256:fixture",),
        required_context_kind="exact",
        required_operations=("lower_theory_language_request",),
        required_receipts=("determinism",),
        forbidden_authorities=("live_registry_mutation",),
        acceptance_tests=("cover every frozen object",),
        gap_kind="capability_missing",
        missing_capabilities=("theory_language:new_observable",),
    )
    receipt = run_adapter_forge(
        gap,
        coding_agent_fn=lambda _prompt: {
            "source_paths": ["coordinate.py"],
            "test_paths": ["test_coordinate.py"],
            "manifest": {"request_id": "campaign-local-coordinate"},
            "self_test_receipts": ["sha256:deterministic"],
            "registry_mutation": False,
        },
        host_conformance_fn=lambda _proposal, _gap: (
            lambda core: {**core, "receipt_sha256": content_hash(core)}
        )({"ok": True, "tests": 8}),
        independent_review_fn=lambda payload: {
            "accepted": False,
            "reviewer_ref": "cold-reviewer",
            "rationale": "the coordinate retains too much source identity",
            "evidence_refs": [
                payload["host_conformance"]["receipt_sha256"]
            ],
        },
    )

    assert receipt["status"] == "quarantined_capability_rejected"
    assert receipt["review_evidence_binding"]["matched_refs"] == [
        "sha256:" + receipt["host_conformance"]["receipt_sha256"]
    ]


def test_adapter_forge_recovers_review_only_after_host_receipt_binding():
    gap = AdapterGap(
        brief_digest="brief:test",
        proposed_adapter_id="magma_equational.v1",
        primitive_semantics_contract={"test": "frozen"},
        raw_fixture_refs=("sha256:fixture",),
        required_context_kind="exact",
        required_operations=("lower_theory_language_request",),
        required_receipts=("determinism",),
        forbidden_authorities=("live_registry_mutation",),
        acceptance_tests=("cover every frozen object",),
        gap_kind="capability_missing",
        missing_capabilities=("theory_language:new_observable",),
    )
    calls = {"recover": 0, "live": 0}

    def review(payload):
        calls["live"] += 1
        return {
            "accepted": True,
            "reviewer_ref": "live-reviewer",
            "rationale": "live fallback",
            "evidence_refs": [payload["host_conformance"]["receipt_sha256"]],
        }

    def recover(host_receipt):
        calls["recover"] += 1
        return {
            "accepted": True,
            "reviewer_ref": "recovered-reviewer",
            "rationale": "bound replay",
            "evidence_refs": [host_receipt["receipt_sha256"]],
        }

    review.recover_for_host_receipt = recover
    receipt = run_adapter_forge(
        gap,
        coding_agent_fn=lambda _prompt: {
            "source_paths": ["coordinate.py"],
            "test_paths": ["test_coordinate.py"],
            "manifest": {"request_id": "campaign-local-coordinate"},
            "self_test_receipts": ["sha256:deterministic"],
            "registry_mutation": False,
        },
        host_conformance_fn=lambda _proposal, _gap: (
            lambda core: {**core, "receipt_sha256": content_hash(core)}
        )({"ok": True, "tests": 8}),
        independent_review_fn=review,
    )

    assert calls == {"recover": 1, "live": 0}
    assert receipt["independent_review"]["reviewer_ref"] == "recovered-reviewer"


def test_adapter_forge_host_conformance_rejection_is_typed_without_review():
    gap = AdapterGap(
        brief_digest="brief:test",
        proposed_adapter_id="magma_equational.v1",
        primitive_semantics_contract={"test": "frozen"},
        raw_fixture_refs=("sha256:fixture",),
        required_context_kind="exact",
        required_operations=("lower_theory_language_request",),
        required_receipts=("determinism",),
        forbidden_authorities=("live_registry_mutation",),
        acceptance_tests=("cover every frozen object",),
        gap_kind="capability_missing",
        missing_capabilities=("theory_language:new_observable",),
    )
    review_calls = 0

    def review(_payload):
        nonlocal review_calls
        review_calls += 1
        raise AssertionError("host-rejected proposal must not reach review")

    receipt = run_adapter_forge(
        gap,
        coding_agent_fn=lambda _prompt: {
            "source_paths": ["coordinate.py"],
            "test_paths": ["test_coordinate.py"],
            "manifest": {"request_id": "campaign-local-coordinate"},
            "self_test_receipts": ["sha256:deterministic"],
            "registry_mutation": False,
        },
        host_conformance_fn=lambda _proposal, _gap: (_ for _ in ()).throw(
            ValueError("capability coordinates do not cover the frozen objects exactly")
        ),
        independent_review_fn=review,
    )

    assert review_calls == 0
    assert receipt["status"] == "quarantined_capability_rejected"
    assert receipt["next_step"] == "return_typed_structural_repair_to_campaign"
    assert receipt["host_conformance"]["schema"] == (
        "leanmill.adapter_forge_host_rejection.v2"
    )
    assert receipt["host_conformance"]["rejection_class"] == (
        "repairable_structural_contract_error"
    )
    assert receipt["host_conformance"]["same_agent_repair_allowed"] is True
    assert receipt["independent_review"]["accepted"] is False
    assert receipt["review_evidence_binding"] is None


def test_evidence_context_workspace_stages_only_manifest_bound_fragments(tmp_path):
    repo = tmp_path / "repo"
    attempt = tmp_path / "attempt"
    source = repo / "fixtures" / "control.json"
    source.parent.mkdir(parents=True)
    artifact = {
        "schema": "leanmill.binary_linear_generator_matrix.v1",
        "field_order": 2,
        "length": 4,
        "dimension": 2,
        "coordinate_convention": "bit_i_is_coordinate_i",
        "rows_hex": ["0x3", "0xc"],
    }
    write_json_atomic(source, {"seed": artifact})
    context_hash = "context:evidence-family"
    write_json_atomic(
        attempt / "evidence_context.json",
        {
            "schema": "leanmill.evidence_theory_context.v1",
            "context_hash": context_hash,
            "object_records": [
                {
                    "object_id": "control:seed",
                    "payload": {
                        "artifact_ref": "control.json#seed",
                        "artifact_sha256": content_hash(artifact),
                    },
                }
            ],
        },
    )
    write_json_atomic(
        attempt / "campaign_manifest.json",
        {"metadata": {"evidence_refs": ["fixtures/control.json"]}},
    )
    adapter_config = {
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
    write_json_atomic(
        attempt / "blueprint.json",
        {"adapter_id": "binary_linear_code.v1", "adapter_config": adapter_config},
    )
    gap = _evidence_family_gap(context_hash)

    workspace = stage_adapter_forge_workspace(
        attempt, gap, source_repo=repo
    )
    fixture = read_json(workspace / "context_fixture.json", {})
    materialization = read_json(workspace / "evidence_materialization.json", {})
    assert fixture["context_kind"] == "evidence_incidence"
    assert (workspace / "evidence_context.json").is_file()
    assert (workspace / "evidence" / "control.json").is_file()
    assert materialization["object_bindings"] == [
        {
            "object_id": "control:seed",
            "artifact_ref": "control.json#seed",
            "artifact_sha256": content_hash(artifact),
            "staged_path": "evidence/control.json",
        }
    ]
    assert read_json(workspace / "witness_construction_interface.json", {})[
        "interface_sha256"
    ] == construction_witness_interface(
        "binary_linear_code.v1", adapter_config
    )["interface_sha256"]
    authoring = read_json(
        workspace / "finite_construction_family_contract.json", {}
    )
    assert authoring["constants"]["gap_id"] == gap.gap_id
    assert authoring["constants"]["context_hash"] == context_hash
    assert "sort_keys=True" in authoring["digest_rule"]

    changed = dict(artifact)
    changed["rows_hex"] = ["0x1", "0x2"]
    write_json_atomic(source, {"seed": changed})
    with pytest.raises(ValueError, match="fragment digest mismatch"):
        stage_adapter_forge_workspace(attempt, gap, source_repo=repo)


def test_forge_frozen_manifest_covers_staged_authoring_contracts(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    for name in (
        "adapter_gap.json",
        "witness_construction_interface.json",
        "finite_construction_family_contract.json",
        "future_authoring_contract.json",
    ):
        write_json_atomic(workspace / name, {"name": name})

    manifest = _adapter_forge_frozen_input_manifest(workspace)
    frozen_paths = {row["path"] for row in manifest}
    assert frozen_paths == {
        "adapter_gap.json",
        "witness_construction_interface.json",
        "finite_construction_family_contract.json",
        "future_authoring_contract.json",
    }
    _verify_adapter_forge_frozen_inputs(workspace, manifest)

    write_json_atomic(
        workspace / "future_authoring_contract.json", {"name": "mutated"}
    )
    with pytest.raises(ValueError, match="changed a frozen host input"):
        _verify_adapter_forge_frozen_inputs(workspace, manifest)


def test_forge_frozen_manifest_rejects_same_byte_symlink_substitution(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    frozen = workspace / "adapter_gap.json"
    replacement = workspace / "same_bytes.json"
    write_json_atomic(frozen, {"gap_id": "frozen"})
    write_json_atomic(replacement, {"gap_id": "frozen"})
    manifest = _adapter_forge_frozen_input_manifest(workspace)
    _verify_adapter_forge_frozen_inputs(workspace, manifest)

    frozen.unlink()
    frozen.symlink_to(replacement.name)
    with pytest.raises(ValueError, match="escaped or disappeared"):
        _verify_adapter_forge_frozen_inputs(workspace, manifest)


def test_coordinate_conformance_uses_evidence_context_owner(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    context = _three_object_evidence_context()
    save_evidence_theory_context(context, workspace / "evidence_context.json")
    gap = _evidence_family_gap(context.context_hash)
    request_id = gap.primitive_semantics_contract[
        "theory_language_request"
    ]["request_id"]
    source = workspace / "coordinates.json"
    write_json_atomic(
        source,
        {
            "schema": "leanmill.object_coordinates.v1",
            "request_id": request_id,
            "coordinates": {
                object_id: {"bucket": int(object_id == "o2")}
                for object_id in context.object_ids
            },
        },
    )
    write_text_atomic(workspace / "test_coordinates.py", "assert True\n")
    proposal = {
        "source_paths": [source.name],
        "test_paths": ["test_coordinates.py"],
        "manifest": {
            "interface": "leanmill.object_coordinates.v1",
            "request_id": request_id,
            "capability_source": source.name,
            "observable_paths": ["/coordinates/*/bucket"],
        },
    }

    receipt = host_capability_conformance(
        proposal,
        gap,
        workspace=workspace,
        output_path=tmp_path / "coordinates.json",
    )

    assert receipt["ok"] is True
    assert receipt["context_kind"] == "evidence_incidence"
    assert receipt["context_hash"] == context.context_hash
    assert receipt["separated_indistinguishable_pair_count"] == 2


@pytest.mark.parametrize("legacy_compiler_receipt", [False, True])
def test_required_successor_application_rejects_coordinate_only_capability(
    tmp_path,
    legacy_compiler_receipt,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    context = _three_object_evidence_context()
    save_evidence_theory_context(context, workspace / "evidence_context.json")
    base_gap = _evidence_family_gap(context.context_hash)
    gap_row = base_gap.to_json(include_id=False)
    compiler_requirement = (
        {
            "compiler_attempts": [
                {
                    "adapter_id": "generic_fol_finite.v1",
                    "status": "unavailable",
                    "reason": (
                        "approved_campaign_local_functor_application_required"
                    ),
                }
            ]
        }
        if legacy_compiler_receipt
        else {
            "required_application": {
                "schema": "leanmill.theory_language_required_application.v1",
                "consumer": (
                    "generic_fol_finite.v1:"
                    "compile_theory_language_expansion"
                ),
                "application_kind": "finite_model_functor",
                "application_schema": (
                    "leanmill.finite_model_functor_application.v2"
                ),
                "source_context_kind": "evidence_incidence",
                "required_fields": [
                    "functor_id",
                    "signature",
                    "formula_grammar",
                    "models",
                ],
                "claim_boundary": "fixture",
            }
        }
    )
    gap_row["primitive_semantics_contract"] = {
        **gap_row["primitive_semantics_contract"],
        **compiler_requirement,
    }
    gap = AdapterGap.from_json(gap_row)
    request_id = gap.primitive_semantics_contract[
        "theory_language_request"
    ]["request_id"]
    source = workspace / "coordinates.json"
    write_json_atomic(
        source,
        {
            "schema": "leanmill.object_coordinates.v1",
            "request_id": request_id,
            "coordinates": {
                object_id: {"bucket": int(object_id == "o2")}
                for object_id in context.object_ids
            },
        },
    )
    write_text_atomic(workspace / "test_coordinates.py", "assert True\n")
    proposal = {
        "source_paths": [source.name],
        "test_paths": ["test_coordinates.py"],
        "manifest": {
            "interface": "leanmill.object_coordinates.v1",
            "request_id": request_id,
            "capability_source": source.name,
            "observable_paths": ["/coordinates/*/bucket"],
        },
    }

    with pytest.raises(AdapterForgeHostConformanceRejected) as caught:
        host_capability_conformance(
            proposal,
            gap,
            workspace=workspace,
            output_path=tmp_path / "coordinates.json",
        )

    assert caught.value.rejection_class == (
        ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT
    )
    assert caught.value.violations[0]["code"] == (
        "successor_functor_image_required"
    )


def test_coordinate_conformance_rejects_null_target_formula_grammar(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    context = _three_object_evidence_context()
    save_evidence_theory_context(context, workspace / "evidence_context.json")
    gap = _evidence_family_gap(context.context_hash)
    request_id = gap.primitive_semantics_contract[
        "theory_language_request"
    ]["request_id"]
    signature = TheorySignature(
        name="MechanismCoordinate",
        sorts=(SortDecl("S"),),
        operations=(OperationSymbol("step", ("S",), "S"),),
    )
    identity = FiniteModel(
        sort_sizes=(("S", 2),),
        operations=(("step", (0, 1)),),
    )
    source = workspace / "coordinates.json"
    write_json_atomic(
        source,
        {
            "coordinates": {
                object_id: {"bucket": 0} for object_id in context.object_ids
            },
            "functor_image": {
                "functor_id": "fixture:null-target-grammar",
                "signature": signature.to_json(),
                "formula_grammar": None,
                "models": {
                    object_id: identity.to_json()
                    for object_id in context.object_ids
                },
            },
        },
    )
    write_text_atomic(workspace / "test_coordinates.py", "assert True\n")
    proposal = {
        "source_paths": [source.name],
        "test_paths": ["test_coordinates.py"],
        "manifest": {
            "interface": "leanmill.object_coordinates.v1",
            "request_id": request_id,
            "capability_source": source.name,
            "observable_paths": ["/coordinates/*/bucket"],
        },
    }

    with pytest.raises(ValueError, match="target formula grammar must be an object"):
        host_capability_conformance(
            proposal,
            gap,
            workspace=workspace,
            output_path=tmp_path / "coordinates.json",
        )


def test_coordinate_conformance_rejects_campaign_authored_python(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    context = _three_object_evidence_context()
    save_evidence_theory_context(context, workspace / "evidence_context.json")
    gap = _evidence_family_gap(context.context_hash)
    request_id = gap.primitive_semantics_contract[
        "theory_language_request"
    ]["request_id"]
    source = workspace / "coordinates.py"
    write_text_atomic(source, "raise AssertionError('must never import')\n")
    write_text_atomic(workspace / "test_coordinates.py", "assert True\n")
    proposal = {
        "source_paths": [source.name],
        "test_paths": ["test_coordinates.py"],
        "manifest": {
            "interface": "leanmill.object_coordinates.v1",
            "request_id": request_id,
            "capability_source": source.name,
            "observable_paths": ["/coordinates/*/bucket"],
        },
    }

    with pytest.raises(
        AdapterForgeHostConformanceRejected,
        match="inert JSON snapshots",
    ):
        host_capability_conformance(
            proposal,
            gap,
            workspace=workspace,
            output_path=tmp_path / "coordinates.json",
        )


def test_staged_artifact_resource_preflight_returns_typed_unavailable(
    tmp_path, monkeypatch
):
    import ztare.leanmill.adapter_forge as forge_module

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    context = _three_object_evidence_context()
    gap = _evidence_family_gap(context.context_hash)
    request_id = gap.primitive_semantics_contract["theory_language_request"][
        "request_id"
    ]
    write_text_atomic(workspace / "source.py", "12345")
    write_text_atomic(workspace / "test.py", "x")
    base = {
        "source_paths": ["source.py"],
        "test_paths": ["test.py"],
        "manifest": {
            "interface": "leanmill.object_coordinates.v1",
            "request_id": request_id,
            "capability_source": "source.py",
            "observable_paths": ["/coordinates/*/bucket"],
        },
        "self_test_receipts": ["sha256:resource-preflight"],
        "registry_mutation": False,
    }
    review_calls = 0

    def review(_payload):
        nonlocal review_calls
        review_calls += 1
        raise AssertionError("resource-unavailable proposals must not reach review")

    monkeypatch.setattr(forge_module, "_MAX_STAGED_ARTIFACT_BYTES", 4)
    unavailable = run_adapter_forge(
        gap,
        coding_agent_fn=lambda _prompt: base,
        host_conformance_fn=lambda proposal, active_gap: (
            host_capability_conformance(
                proposal,
                active_gap,
                workspace=workspace,
                output_path=tmp_path / "out.json",
            )
        ),
        independent_review_fn=review,
    )
    assert review_calls == 0
    assert unavailable["status"] == "quarantined_capability_unavailable"
    assert unavailable["next_step"] == "return_unavailable_to_theory_search"
    assert unavailable["host_conformance"]["outcome"] == "unavailable"
    assert unavailable["host_conformance"]["reason_code"] == (
        "staged_artifact_byte_limit_exhausted"
    )

    monkeypatch.setattr(forge_module, "_MAX_STAGED_ARTIFACT_BYTES", 8)
    monkeypatch.setattr(forge_module, "_MAX_STAGED_ARTIFACTS_PER_ROLE", 1)
    too_many = {**base, "source_paths": ["source.py", "missing.py"]}
    unavailable = run_adapter_forge(
        gap,
        coding_agent_fn=lambda _prompt: too_many,
        host_conformance_fn=lambda proposal, active_gap: (
            host_capability_conformance(
                proposal,
                active_gap,
                workspace=workspace,
                output_path=tmp_path / "out.json",
            )
        ),
        independent_review_fn=review,
    )
    assert unavailable["host_conformance"]["reason_code"] == (
        "staged_artifact_count_limit_exhausted"
    )


def test_host_conformance_consumes_frozen_staged_snapshots_without_reopen(
    tmp_path, monkeypatch
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    context = _three_object_evidence_context()
    save_evidence_theory_context(context, workspace / "evidence_context.json")
    gap = _evidence_family_gap(context.context_hash)
    request_id = gap.primitive_semantics_contract["theory_language_request"][
        "request_id"
    ]
    source = workspace / "coordinates.json"
    test = workspace / "test_coordinates.py"
    source_row = {
        "schema": "leanmill.object_coordinates.v1",
        "request_id": request_id,
        "coordinates": {
            object_id: {"bucket": int(object_id == "o2")}
            for object_id in context.object_ids
        },
    }
    write_json_atomic(source, source_row)
    write_text_atomic(test, "assert True\n")
    original_source = source.read_text(encoding="utf-8")
    original_test = test.read_text(encoding="utf-8")
    proposal = {
        "source_paths": [source.name],
        "test_paths": [test.name],
        "manifest": {
            "interface": "leanmill.object_coordinates.v1",
            "request_id": request_id,
            "capability_source": source.name,
            "observable_paths": ["/coordinates/*/bucket"],
        },
    }
    original_preflight = adapter_forge_module._preflight_staged_artifact_paths

    def freeze_then_replace(*args, **kwargs):
        frozen = original_preflight(*args, **kwargs)
        write_text_atomic(source, "not the frozen source\n")
        write_text_atomic(test, "raise AssertionError('must not reopen')\n")

        def forbidden_reopen(*_args, **_kwargs):
            raise AssertionError("host conformance reopened a frozen staged path")

        monkeypatch.setattr(Path, "read_text", forbidden_reopen)
        return frozen

    monkeypatch.setattr(
        adapter_forge_module,
        "_preflight_staged_artifact_paths",
        freeze_then_replace,
    )
    receipt = host_capability_conformance(
        proposal,
        gap,
        workspace=workspace,
        output_path=tmp_path / "coordinates.json",
    )

    assert receipt["source_artifacts"][0]["content"] == original_source
    assert receipt["test_artifacts"][0]["content"] == original_test
    assert receipt["source_artifacts"][0]["content_sha256"] == content_hash(
        {"bytes": original_source}
    )


def test_staged_ingress_rejects_symlink_and_mid_read_growth(
    tmp_path, monkeypatch
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "target.json"
    source = workspace / "source.json"
    test = workspace / "test.py"
    write_text_atomic(target, "{}\n")
    source.symlink_to(target.name)
    write_text_atomic(test, "assert True\n")
    proposal = {
        "source_paths": [source.name],
        "test_paths": [test.name],
    }
    with pytest.raises(ValueError, match="non-staged file"):
        adapter_forge_module._preflight_staged_artifact_paths(
            proposal,
            root=workspace.resolve(),
            interface="fixture.interface.v1",
        )

    source.unlink()
    write_text_atomic(source, "{}\n")
    source_identity = source.stat()
    original_read = os.read
    appended = False

    def grow_during_read(descriptor, amount):
        nonlocal appended
        chunk = original_read(descriptor, amount)
        opened = os.fstat(descriptor)
        if (
            chunk
            and not appended
            and opened.st_dev == source_identity.st_dev
            and opened.st_ino == source_identity.st_ino
        ):
            appended = True
            with source.open("ab") as stream:
                stream.write(b"x")
        return chunk

    monkeypatch.setattr(adapter_forge_module.os, "read", grow_during_read)
    with pytest.raises(ValueError, match="changed while being read"):
        adapter_forge_module._preflight_staged_artifact_paths(
            proposal,
            root=workspace.resolve(),
            interface="fixture.interface.v1",
        )
    assert appended is True


def test_staged_aggregate_ceiling_rejects_before_next_payload_read(
    tmp_path, monkeypatch
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "source.json"
    test = workspace / "test.py"
    write_text_atomic(source, "1234")
    write_text_atomic(test, "xy")
    proposal = {
        "source_paths": [source.name],
        "test_paths": [test.name],
    }
    test_identity = test.stat()
    test_reads = 0
    original_read = os.read

    def observe_read(descriptor, amount):
        nonlocal test_reads
        opened = os.fstat(descriptor)
        if (
            opened.st_dev == test_identity.st_dev
            and opened.st_ino == test_identity.st_ino
        ):
            test_reads += 1
        return original_read(descriptor, amount)

    monkeypatch.setattr(adapter_forge_module.os, "read", observe_read)
    monkeypatch.setattr(
        adapter_forge_module,
        "_MAX_STAGED_ARTIFACT_AGGREGATE_BYTES",
        5,
    )
    with pytest.raises(AdapterForgeHostCapabilityUnavailable) as raised:
        adapter_forge_module._preflight_staged_artifact_paths(
            proposal,
            root=workspace.resolve(),
            interface="fixture.interface.v1",
        )
    assert raised.value.reason_code == (
        "staged_artifact_aggregate_byte_limit_exhausted"
    )
    assert raised.value.observed == 6
    assert raised.value.ceiling == 5
    assert test_reads == 0


def test_coding_agent_runtime_failure_is_typed_and_charged_once(tmp_path):
    gap = _evidence_family_gap("context:coding-runtime")
    calls = {"host": 0, "review": 0}
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget_preset("smoke_20m"),
        attempt_id="coding-runtime",
    )

    def coding(_prompt):
        raise TimeoutError("provider timed out")

    def host(_proposal, _gap):
        calls["host"] += 1
        raise AssertionError("unavailable coding must skip host conformance")

    def review(_payload):
        calls["review"] += 1
        raise AssertionError("unavailable coding must skip review")

    receipt = run_adapter_forge(
        gap,
        coding_agent_fn=coding,
        host_conformance_fn=host,
        independent_review_fn=review,
        budget_ledger=ledger,
    )
    assert calls == {"host": 0, "review": 0}
    assert receipt["status"] == "quarantined_capability_unavailable", receipt[
        "host_conformance"
    ].get("reason")
    assert receipt["host_conformance"]["reason_code"] == (
        "adapter_forge_coding_agent_runtime_unavailable"
    )
    usage = ledger.state()["usage"]
    assert usage["adapter_forge_attempts"] == 1
    assert usage["provider_calls"] == 1
    assert usage["agent_turns"] == 1


def test_review_resource_failure_is_typed_unavailable(tmp_path, monkeypatch):
    import ztare.leanmill.adapter_forge as forge_module

    gap = _evidence_family_gap("context:review-resource")
    host_core = {"ok": True, "tests": 1}
    host = {**host_core, "receipt_sha256": content_hash(host_core)}
    monkeypatch.setattr(forge_module, "_MAX_ADAPTER_FORGE_REVIEW_BYTES", 64)
    receipt = run_adapter_forge(
        gap,
        coding_agent_fn=lambda _prompt: {
            "source_paths": ["fixture.json"],
            "test_paths": ["check.json"],
            "manifest": {"request_id": "fixture"},
            "self_test_receipts": ["sha256:fixture"],
            "registry_mutation": False,
        },
        host_conformance_fn=lambda _proposal, _gap: host,
        independent_review_fn=lambda payload: {
            "accepted": True,
            "reviewer_ref": "reviewer",
            "rationale": "x" * 512,
            "evidence_refs": [payload["host_conformance"]["receipt_sha256"]],
        },
    )
    assert receipt["status"] == "quarantined_capability_unavailable"
    assert receipt["independent_review"]["outcome"] == "unavailable"
    assert receipt["independent_review"]["error_type"] == (
        "AdapterForgeHostCapabilityUnavailable"
    )


def test_host_runtime_failure_is_typed_and_skips_review():
    gap = _evidence_family_gap("context:host-runtime")
    review_calls = 0

    def review(_payload):
        nonlocal review_calls
        review_calls += 1
        raise AssertionError("unavailable host runtime must skip review")

    receipt = run_adapter_forge(
        gap,
        coding_agent_fn=lambda _prompt: {
            "source_paths": ["fixture.json"],
            "test_paths": ["check.json"],
            "manifest": {"request_id": "fixture"},
            "self_test_receipts": ["sha256:fixture"],
            "registry_mutation": False,
        },
        host_conformance_fn=lambda _proposal, _gap: (
            _ for _ in ()
        ).throw(TimeoutError("host worker timed out")),
        independent_review_fn=review,
    )
    assert review_calls == 0
    assert receipt["status"] == "quarantined_capability_unavailable"
    assert receipt["host_conformance"]["reason_code"] == (
        "adapter_forge_host_runtime_unavailable"
    )


def test_absent_construction_backend_is_typed_before_review(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    context = _three_object_evidence_context()
    save_evidence_theory_context(context, workspace / "evidence_context.json")
    gap = _evidence_family_gap(context.context_hash)
    request = gap.primitive_semantics_contract["theory_language_request"]
    adapter_config = {
        "construction_target": {
            "schema": "leanmill.binary_linear_code_target_config.v1",
            "field_order": 2,
            "length": 2,
            "dimension": 1,
            "minimum_distance": 1,
            "max_nonzero_messages": 1,
            "target_snapshot_sha256": "a" * 64,
        }
    }
    interface = construction_witness_interface(
        BINARY_ADAPTER_ID, adapter_config
    )
    write_json_atomic(
        workspace / "blueprint.json",
        {"adapter_id": BINARY_ADAPTER_ID, "adapter_config": adapter_config},
    )
    limits = {
        "max_assignments": 4,
        "max_template_nodes": 100,
        "max_template_bytes": 10_000,
        "max_materialized_artifact_bytes": 20_000,
        "max_execution_receipt_bytes": 100_000,
        "max_materialized_family_bytes": 100_000,
    }
    parameterization = build_construction_parameterization(
        campaign_id="adapter-forge:" + gap.gap_id,
        request_id=request["request_id"],
        gap_id=gap.gap_id,
        context_hash=context.context_hash,
        context_epoch=int(request.get("source_epoch") or 0),
        adapter_id=BINARY_ADAPTER_ID,
        target_interface_sha256=interface["interface_sha256"],
        source_refs=["fixture:absent-backend"],
        parameter_space={
            "schema": "leanmill.explicit_finite_parameter_space.v1",
            "variables": [{
                "parameter_id": "row",
                "sort": "json_atom",
                "domain": ["0x1"],
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
                "rows_hex": [{"$parameter": "row"}],
            },
        },
        backend={
            "adapter_id": BINARY_ADAPTER_ID,
            "capability_id": explicit_finite_json.CAPABILITY_ID,
            "contract_sha256": content_hash(explicit_finite_json.CONTRACT),
        },
        resource_limits=limits,
        search_order={
            "kind": "lexicographic",
            "parameter_ids": ["row"],
            "domain_order": "declared_canonical",
        },
    )
    parameterization["backend"] = {
        "adapter_id": BINARY_ADAPTER_ID,
        "capability_id": "absent_backend.v1",
        "contract_sha256": "f" * 64,
    }
    write_json_atomic(workspace / "parameterization.json", parameterization)
    write_json_atomic(workspace / "check.json", {"kind": "shape_only"})
    proposal = {
        "source_paths": ["parameterization.json"],
        "test_paths": ["check.json"],
        "manifest": {
            "interface": CONSTRUCTION_PARAMETERIZATION_SCHEMA,
            "request_id": request["request_id"],
            "capability_source": "parameterization.json",
            "observable_paths": [],
        },
        "self_test_receipts": ["sha256:shape-only"],
        "registry_mutation": False,
    }
    review_calls = 0

    def review(_payload):
        nonlocal review_calls
        review_calls += 1
        raise AssertionError("absent backend must not reach review")

    receipt = run_adapter_forge(
        gap,
        coding_agent_fn=lambda _prompt: proposal,
        host_conformance_fn=lambda candidate, active_gap: (
            host_capability_conformance(
                candidate,
                active_gap,
                workspace=workspace,
                output_path=tmp_path / "out.json",
            )
        ),
        independent_review_fn=review,
    )
    assert review_calls == 0
    assert receipt["status"] == "quarantined_capability_unavailable", receipt[
        "host_conformance"
    ].get("reason")
    assert receipt["host_conformance"]["reason_code"] == (
        "construction_backend_capability_unavailable"
    )


def test_generative_conformance_passes_evidence_owner_to_validator(
    tmp_path, monkeypatch
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    context = _three_object_evidence_context()
    save_evidence_theory_context(context, workspace / "evidence_context.json")
    gap = _evidence_family_gap(context.context_hash)
    request_id = gap.primitive_semantics_contract["theory_language_request"][
        "request_id"
    ]
    candidate = {"request_id": request_id, "gap_id": gap.gap_id}
    write_json_atomic(workspace / "candidate.json", candidate)
    write_text_atomic(workspace / "test_candidate.py", "assert True\n")
    captured = {}

    def validate(value, source_context):
        captured["candidate"] = value
        captured["context"] = source_context
        core = {
            "ok": True,
            "interface": CANDIDATE_SCHEMA,
            "context_hash": source_context.context_hash,
        }
        return {**core, "receipt_sha256": content_hash(core)}

    monkeypatch.setattr(
        "ztare.leanmill.adapter_forge.validate_materialized_generative_candidate",
        validate,
    )
    proposal = {
        "source_paths": ["candidate.json"],
        "test_paths": ["test_candidate.py"],
        "manifest": {
            "interface": CANDIDATE_SCHEMA,
            "request_id": request_id,
            "capability_source": "candidate.json",
            "observable_paths": [],
        },
    }

    receipt = host_capability_conformance(
        proposal,
        gap,
        workspace=workspace,
        output_path=tmp_path / "candidate-output.json",
    )

    assert captured["candidate"] == candidate
    assert captured["context"] == context
    assert receipt["context_hash"] == context.context_hash


def test_finite_family_host_conformance_precedes_member_outcomes(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    context_hash = "context:evidence-family"
    write_json_atomic(
        workspace / "evidence_context.json",
        {"schema": "leanmill.evidence_theory_context.v1", "context_hash": context_hash},
    )
    adapter_config = {
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
    write_json_atomic(
        workspace / "blueprint.json",
        {"adapter_id": "binary_linear_code.v1", "adapter_config": adapter_config},
    )
    interface = construction_witness_interface(
        "binary_linear_code.v1", adapter_config
    )
    artifact = {
        "schema": "leanmill.binary_linear_generator_matrix.v1",
        "field_order": 2,
        "length": 4,
        "dimension": 2,
        "coordinate_convention": "bit_i_is_coordinate_i",
        "rows_hex": ["0x1", "0x2"],
    }
    parameter_ids = ["delete:0"]
    gap = _evidence_family_gap(context_hash)
    forge_prompt = render_adapter_forge_prompt(gap)
    assert "fresh cold author" in forge_prompt
    assert "same agent or workspace" in forge_prompt
    family_core = {
        "schema": FINITE_CONSTRUCTION_FAMILY_SCHEMA,
        "request_id": "theory-language-request:evidence-family",
        "gap_id": gap.gap_id,
        "context_hash": context_hash,
        "adapter_id": "binary_linear_code.v1",
        "family_id": "family:one-explicit-control",
        "family_scope": "one byte-frozen control family",
        "family_spec": {"kind": "coordinate_deletion", "source": "control:seed"},
        "authorship": {
            "authority": "campaign_local_subscription_leaf",
            "role": "adapter_forge",
        },
        "symmetry_policy": {"kind": "none"},
        "target_interface_sha256": interface["interface_sha256"],
        "declared_cardinality": 1,
        "parameter_ids": parameter_ids,
        "parameter_domain_sha256": content_hash(parameter_ids),
        "members": [
            {
                "parameter_id": "delete:0",
                "artifact": artifact,
                "artifact_sha256": content_hash(artifact),
                "derivation": {"kind": "coordinate_deletion", "coordinate": 0},
                "source_refs": ["control:seed"],
            }
        ],
        "claim_scope": FINITE_CONSTRUCTION_FAMILY_CLAIM_SCOPE,
    }
    family = {**family_core, "receipt_sha256": content_hash(family_core)}
    write_json_atomic(workspace / "family.json", family)
    write_json_atomic(workspace / "family_checks.json", {"domain": parameter_ids})
    proposal = {
        "source_paths": ["family.json"],
        "test_paths": ["family_checks.json"],
        "manifest": {
            "capability_source": "family.json",
            "interface": FINITE_CONSTRUCTION_FAMILY_SCHEMA,
            "request_id": "theory-language-request:evidence-family",
            "observable_paths": [],
        },
        "self_test_receipts": ["sha256:family-domain"],
        "registry_mutation": False,
    }
    conformance = host_capability_conformance(
        proposal,
        gap,
        workspace=workspace,
        output_path=tmp_path / "out" / "coordinates.json",
    )
    assert conformance["ok"] is True
    assert conformance["interface"] == FINITE_CONSTRUCTION_FAMILY_SCHEMA
    assert conformance["outcomes_evaluated"] is False
    assert conformance["declared_cardinality"] == 1
    assert conformance["finite_family_receipt_sha256"] == family["receipt_sha256"]

    tainted = dict(family)
    tainted_members = [dict(family["members"][0])]
    tainted_members[0]["source_refs"] = [{"object_id": "control:seed"}]
    tainted_members[0]["derivation"] = {
        "kind": "coordinate_deletion",
        "coordinate": 0,
        "rank": 2,
        "outcome": "rejected",
    }
    tainted["members"] = tainted_members
    tainted_core = {
        key: value for key, value in tainted.items() if key != "receipt_sha256"
    }
    tainted["receipt_sha256"] = content_hash(tainted_core)
    write_json_atomic(workspace / "family.json", tainted)
    write_json_atomic(
        workspace / "family_checks.json",
        {"observed_rank": 2, "outcome": "rejected"},
    )
    review_calls = 0

    def forbidden_review(_payload):
        nonlocal review_calls
        review_calls += 1
        raise AssertionError("pre-review contamination must not reach review")

    rejected = run_adapter_forge(
        gap,
        coding_agent_fn=lambda _prompt: proposal,
        host_conformance_fn=lambda candidate, active_gap: (
            host_capability_conformance(
                candidate,
                active_gap,
                workspace=workspace,
                output_path=tmp_path / "tainted" / "coordinates.json",
            )
        ),
        independent_review_fn=forbidden_review,
    )
    host_rejection = rejected["host_conformance"]
    assert review_calls == 0
    assert host_rejection["rejection_class"] == (
        "epistemic_pre_review_outcome_leakage"
    )
    assert host_rejection["same_agent_repair_allowed"] is False
    assert host_rejection["workspace_reuse_allowed"] is False
    assert host_rejection["required_agent_identity"] == (
        "fresh_cold_adapter_forge_leaf"
    )
    assert rejected["next_step"] == (
        "reauthor_in_fresh_cold_workspace_with_new_agent_identity"
    )
    violation_codes = {row["code"] for row in host_rejection["violations"]}
    assert "member_source_refs_not_string_identities" in violation_codes
    assert "pre_review_target_outcome_in_derivation" in violation_codes
    assert "pre_review_target_outcome_in_self_test" in violation_codes

    write_json_atomic(workspace / "family.json", family)
    write_json_atomic(workspace / "family_checks.json", {"domain": parameter_ids})
    quarantine = run_adapter_forge(
        gap,
        coding_agent_fn=lambda _prompt: proposal,
        host_conformance_fn=lambda _proposal, _gap: conformance,
        independent_review_fn=lambda payload: {
            "accepted": True,
            "reviewer_ref": "independent-family-reviewer",
            "rationale": "the explicit domain and family scope are admissible",
            "evidence_refs": [
                payload["host_conformance"]["receipt_sha256"]
            ],
        },
    )
    assert quarantine["status"] == "quarantined_registry_proposal"
    assert quarantine["next_step"] == (
        "execute_reviewed_finite_construction_family"
    )
    attempt = tmp_path / "approved-attempt"
    write_json_atomic(
        attempt / "blueprint.json",
        {"adapter_id": "binary_linear_code.v1", "adapter_config": adapter_config},
    )
    write_json_atomic(attempt / "adapter_gap.json", gap.to_json())
    owner = adapter_forge_attempt_directory(attempt, gap.gap_id, create=True)
    write_json_atomic(
        owner / "theory_language_finite_family_candidate.json", family
    )
    completion_core = {
        "schema": "leanmill.adapter_forge_completion.v1",
        "status": "reviewed_campaign_local_finite_family_available",
        "attempt_dir": str(attempt),
        "gap_id": gap.gap_id,
        "host_conformance_contract": ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        "quarantine_receipt": quarantine,
        "reason": "the explicit domain and family scope are admissible",
        "rejection_class": "",
        "recovery_route": "",
        "evidence_refs": [quarantine["receipt_sha256"]],
        "provider_calls": 2,
    }
    approved, approved_receipt = _approved_finite_family_candidate(
        attempt,
        {**completion_core, "completion_sha256": content_hash(completion_core)},
    )
    assert approved == family
    assert approved_receipt == quarantine


def test_blocked_public_campaign_resumes_through_adapter_forge_quarantine(tmp_path):
    attempt = tmp_path / "new-substrate"
    run = explore_axiom_space(
        FrontierCampaignDefinition(
            direction="Explore a finite colored-composition substrate with executable fixtures.",
            source_mode="structure_first",
            budget=budget_preset("smoke"),
        ),
        attempt_dir=attempt,
        typed_draft=_unknown_draft(),
    )
    assert run.status == "blocked_adapter_gap"
    before = registered_theory_adapter_ids()
    calls = {"coding": 0, "review": 0, "host": 0}

    def coding(_prompt):
        calls["coding"] += 1
        return {
            "source_paths": ["quarantine/finite_color_adapter.py"],
            "test_paths": ["quarantine/test_finite_color_adapter.py"],
            "manifest": {"adapter_id": "unbuilt_custom_substrate.v1"},
            "self_test_receipts": ["sha256:determinism", "sha256:roundtrip"],
        }

    def conformance(_proposal, _gap):
        calls["host"] += 1
        core = {"ok": True, "tests": 9, "fixture_replay": True}
        return {**core, "receipt_sha256": content_hash(core)}

    def review(payload):
        calls["review"] += 1
        return {
            "accepted": True,
            "reviewer_ref": "independent-adapter-reviewer",
            "rationale": "typed semantics and claim boundary match the frozen gap",
            "evidence_refs": [payload["host_conformance"]["receipt_sha256"]],
        }

    completion = execute_adapter_forge_attempt(
        attempt,
        coding_agent_fn=coding,
        host_conformance_fn=conformance,
        independent_review_fn=review,
    )
    assert completion["status"] == (
        "quarantined_adapter_proposal_requires_authority_and_new_attempt"
    )
    assert completion["provider_calls"] == 2
    assert registered_theory_adapter_ids() == before
    assert calls == {"coding": 1, "review": 1, "host": 1}
    assert execute_adapter_forge_attempt(
        attempt,
        coding_agent_fn=lambda _prompt: (_ for _ in ()).throw(AssertionError("called")),
        host_conformance_fn=lambda _proposal, _gap: (_ for _ in ()).throw(AssertionError("called")),
        independent_review_fn=lambda _payload: (_ for _ in ()).throw(AssertionError("called")),
    ) == completion


def test_host_rejection_cause_and_receipt_return_to_navigation(tmp_path):
    attempt = _language_attempt(tmp_path, "typed-host-rejection")

    def forge(path, *, _attempt_lease):
        return execute_adapter_forge_attempt(
            path,
            coding_agent_fn=lambda _prompt: {
                "source_paths": ["family.json"],
                "test_paths": ["test_family.py"],
                "manifest": {"request_id": "campaign-local-family"},
                "self_test_receipts": ["sha256:domain"],
                "registry_mutation": False,
            },
            host_conformance_fn=lambda _proposal, _gap: (_ for _ in ()).throw(
                ValueError("finite family source_refs must be strings")
            ),
            independent_review_fn=lambda _payload: (_ for _ in ()).throw(
                AssertionError("host rejection must precede review")
            ),
        )

    advance_frontier_language_expansion(
        attempt,
        forge_fn=forge,
        resume_fn=lambda path, **_kwargs: path,
    )
    gap = AdapterGap.from_json(read_json(attempt / "adapter_gap.json", {}))
    completion = read_adapter_forge_completion(attempt, gap)
    assert completion is not None
    assert completion["reason"] == (
        "host_conformance_rejected:finite family source_refs must be strings"
    )
    assert completion["rejection_class"] == (
        "repairable_structural_contract_error"
    )
    assert completion["recovery_route"] == (
        "return_typed_structural_repair_to_campaign"
    )
    updated = read_json(attempt / "run.json", {})
    feedback = updated["navigation"]["objective_review_history"][-1]
    receipt = completion["quarantine_receipt"]
    violation = receipt["host_conformance"]["violations"][0]
    assert violation["category"] == "structural_contract"
    assert violation["repair_scope"] == "same_agent_new_bytes_permitted"
    assert feedback["reason"] == completion["reason"]
    assert _resolve_workbench_evidence_receipts(
        attempt,
        updated["navigation"],
        [receipt["receipt_sha256"]],
    ) == [receipt]


def _language_attempt(
    tmp_path,
    name="language-successor",
    expected_status="frontier_language_expansion_requested",
    source_task_scope=False,
):
    attempt = tmp_path / name
    private, public = generate_keypair()
    typed_draft = _draft()
    if source_task_scope:
        typed_draft["navigator_contract"] = {
            **typed_draft["navigator_contract"],
            "theory_task_capability_scope": {
                "schema": THEORY_TASK_CAPABILITY_SCOPE_SCHEMA,
                "adapter_id": typed_draft["adapter_id"],
                "allowed_capability_ids": [],
            },
        }

    def navigator(context, blueprint, journal, *, budget_ledger):
        calls = 0

        def decide(prompt):
            nonlocal calls
            calls += 1
            if calls == 1:
                return {
                    "decision": "request",
                    "capability_id": "inspect_presentation_extent",
                    "input_refs": {"formula_ids": [], "offset": 0, "limit": 2},
                    "rationale": "Freeze an evidence receipt for the language request.",
                }
            refs = re.findall(r'"receipt_id":"(sha256:[0-9a-f]{64})"', prompt)
            assert refs
            return {
                "decision": "request",
                "capability_id": "propose_theory_language_expansion",
                "input_refs": {
                    "change_kind": "new_operation",
                    "blind_spot": "Current equations alias the receipted source extent.",
                    "proposed_interface": "One executable unary structural coordinate.",
                    "evidence_refs": [refs[-1]],
                    "discriminating_test": "The new coordinate refines the receipted extent.",
                    "kill_condition": "The coordinate is absent, partial, or source-injective.",
                },
                "rationale": "Request a successor chart rather than mutate this epoch.",
            }

        return run_interactive_theory_navigator(
            context,
            blueprint,
            journal,
            agent_fn=decide,
            attempt_id=attempt.name,
            campaign_id="campaign:" + blueprint.blueprint_id.split(":", 1)[1][:24],
            budget_ledger=budget_ledger,
            max_rounds=2,
        )

    navigator.accepts_budget_ledger = True
    run = explore_axiom_space(
        FrontierCampaignDefinition(
            direction="Explore an anonymous finite language and invent a successor chart.",
            source_mode="structure_first",
            budget=budget_preset("smoke_20m"),
        ),
        attempt_dir=attempt,
        typed_draft=typed_draft,
        packet_signer=lambda packet: sign_frontier_campaign(
            packet, private_key_pem=private, signer_ref="campaign-authority"
        ),
        navigator_fn=navigator,
    )
    assert run.status == expected_status
    (attempt / "private").mkdir(exist_ok=True)
    write_text_atomic(attempt / "private" / "campaign_signer.pem", private)
    write_text_atomic(attempt / "campaign_signer_public.pem", public)
    return attempt


def _evidence_language_attempt(tmp_path):
    attempt = tmp_path / "evidence-language-successor"
    private, public = generate_keypair()
    source_signature = TheorySignature(
        name="ExactObservations",
        sorts=(SortDecl("Observation"),),
    )
    draft = {
        "mode": "evidence_induced",
        "eigenquestion": (
            "Which reviewed coordinate separates the flat observation image?"
        ),
        "signature": source_signature.to_json(),
        "primitive_semantics": {
            "operation_bindings": {},
            "relation_bindings": {},
        },
        "base_axioms": (),
        "base_theory_status": "explicit_empty",
        "adapter_id": "generic_finite_evidence.v1",
        "adapter_config": {
            "completeness_ref": "fixture:three-exact-observations",
            "objects": [
                {
                    "object_id": "o0",
                    "stratum_id": "coefficient",
                    "payload": {"order": 0},
                },
                {
                    "object_id": "o1",
                    "stratum_id": "coefficient",
                    "payload": {"order": 1},
                },
                {
                    "object_id": "o2",
                    "stratum_id": "coefficient",
                    "payload": {"order": 2},
                },
            ],
            "hypotheses": [
                {
                    "hypothesis_id": "h0",
                    "satisfied_object_ids": ["o0", "o1", "o2"],
                    "anonymous_shape": {"kind": "exact_observation"},
                    "payload": {"checker_ref": "fixture:exact"},
                }
            ],
        },
        "formula_grammar": {},
        "model_or_observation_strata": (),
        "pack_arity": 1,
        "collapse_controls": (),
        "visible_evidence_manifest": {},
        "sealed_evidence_manifest_digest": "sha256:" + "0" * 64,
        "deanchoring_policy": {"cold_after_compilation": True},
        "navigator_contract": {
            "adapter_id": "axiompack",
            "selection_mode": "compact_axiom_pack",
        },
        "query_budget": {"max_finalists": 1, "max_ranked_queries": 2},
        "stop_rule": {"freeze_after_finalists": 1},
        "verification_plan": {},
        "codec_versions": {"evidence": "fixture-v1"},
        "authority_refs": ("campaign-authority",),
    }

    def navigator(context, blueprint, journal, *, budget_ledger):
        calls = 0

        def decide(prompt):
            nonlocal calls
            calls += 1
            if calls == 1:
                return {
                    "decision": "request",
                    "capability_id": "inspect_presentation_extent",
                    "input_refs": {
                        "formula_ids": [],
                        "offset": 0,
                        "limit": 3,
                    },
                    "rationale": (
                        "Freeze the aliased observation extent before changing "
                        "the chart."
                    ),
                }
            refs = re.findall(
                r'"receipt_id":"(sha256:[0-9a-f]{64})"', prompt
            )
            assert refs
            return {
                "decision": "request",
                "capability_id": "propose_theory_language_expansion",
                "input_refs": {
                    "change_kind": "quotient_or_coordinate_change",
                    "blind_spot": (
                        "The current observation profile aliases all three "
                        "coefficient orders."
                    ),
                    "proposed_interface": (
                        "A finite unary mechanism coordinate with an explicit "
                        "target equation grammar."
                    ),
                    "evidence_refs": [refs[-1]],
                    "discriminating_test": (
                        "The reviewed coordinate splits the frozen alias class "
                        "and compiles a nonempty successor formula universe."
                    ),
                    "kill_condition": (
                        "The coordinate is partial, source-injective, or lacks "
                        "an executable target grammar."
                    ),
                },
                "rationale": (
                    "Move the observation panel into a reviewed mechanism chart."
                ),
            }

        return run_interactive_theory_navigator(
            context,
            blueprint,
            journal,
            agent_fn=decide,
            attempt_id=attempt.name,
            campaign_id=(
                "campaign:" + blueprint.blueprint_id.split(":", 1)[1][:24]
            ),
            budget_ledger=budget_ledger,
            max_rounds=2,
        )

    navigator.accepts_budget_ledger = True
    run = explore_axiom_space(
        FrontierCampaignDefinition(
            direction=(
                "Explore exact observations and author a mechanism successor."
            ),
            source_mode="structure_first",
            budget=budget_preset("smoke_20m"),
        ),
        attempt_dir=attempt,
        typed_draft=draft,
        packet_signer=lambda packet: sign_frontier_campaign(
            packet,
            private_key_pem=private,
            signer_ref="campaign-authority",
        ),
        navigator_fn=navigator,
    )
    assert run.status == "frontier_language_expansion_requested"
    (attempt / "private").mkdir(exist_ok=True)
    write_text_atomic(attempt / "private" / "campaign_signer.pem", private)
    write_text_atomic(attempt / "campaign_signer_public.pem", public)
    return attempt


def test_evidence_language_request_compiles_and_resumes_as_formal_epoch(
    tmp_path,
):
    attempt = _evidence_language_attempt(tmp_path)
    source = read_json(attempt / "evidence_context.json", {})
    source_ids = [
        str(row["object_id"]) for row in source["object_records"]
    ]
    target_signature = TheorySignature(
        name="MechanismCoordinate",
        sorts=(SortDecl("S"),),
        operations=(OperationSymbol("step", ("S",), "S"),),
    )
    identity = FiniteModel(
        sort_sizes=(("S", 2),),
        operations=(("step", (0, 1)),),
    )
    constant = FiniteModel(
        sort_sizes=(("S", 2),),
        operations=(("step", (0, 0)),),
    )
    target_grammar = {
        "schema": EQUATIONAL_GRAMMAR_SCHEMA,
        "max_total_operation_order": 2,
        "max_formulas": 1_000,
        "variable_renaming_quotient": True,
        "equation_side_quotient": True,
        "exclude_nonvariable_reflexive": True,
    }

    def forge(path, *, _attempt_lease):
        gap = AdapterGap.from_json(read_json(path / "adapter_gap.json", {}))
        required_application = gap.primitive_semantics_contract[
            "required_application"
        ]
        assert required_application["application_kind"] == (
            "finite_model_functor"
        )
        assert required_application["application_schema"] == (
            "leanmill.finite_model_functor_application.v2"
        )
        assert required_application["source_context_kind"] == (
            "evidence_incidence"
        )
        workspace = stage_adapter_forge_workspace(path, gap)
        request_id = gap.primitive_semantics_contract[
            "theory_language_request"
        ]["request_id"]
        source_path = workspace / "mechanism_coordinate.json"
        write_json_atomic(
            source_path,
            {
                "coordinates": {
                    source_ids[0]: {"bucket": 0},
                    source_ids[1]: {"bucket": 0},
                    source_ids[2]: {"bucket": 1},
                },
                "functor_image": {
                    "functor_id": "fixture:evidence-mechanism",
                    "signature": target_signature.to_json(),
                    "formula_grammar": target_grammar,
                    "models": {
                        source_ids[0]: identity.to_json(),
                        source_ids[1]: identity.to_json(),
                        source_ids[2]: constant.to_json(),
                    },
                },
            },
        )
        write_json_atomic(
            workspace / "mechanism_coordinate_checks.json",
            {"source_object_ids": source_ids},
        )

        def host(proposal, active_gap):
            owner = adapter_forge_attempt_directory(
                path, active_gap.gap_id, create=True
            )
            return host_capability_conformance(
                proposal,
                active_gap,
                workspace=workspace,
                output_path=owner / "theory_language_coordinates.json",
            )

        return execute_adapter_forge_attempt(
            path,
            coding_agent_fn=lambda _prompt: {
                "source_paths": [source_path.name],
                "test_paths": ["mechanism_coordinate_checks.json"],
                "manifest": {
                    "capability_source": source_path.name,
                    "interface": "leanmill.object_coordinates.v1",
                    "request_id": request_id,
                    "observable_paths": ["/coordinates/*/bucket"],
                },
                "self_test_receipts": ["sha256:mechanism-coordinate"],
                "registry_mutation": False,
            },
            host_conformance_fn=host,
            independent_review_fn=lambda payload: {
                "accepted": True,
                "reviewer_ref": "fixture:independent-mechanism-review",
                "rationale": (
                    "The coordinate and target grammar replay against the "
                    "frozen evidence objects."
                ),
                "evidence_refs": [
                    payload["host_conformance"]["receipt_sha256"]
                ],
            },
        )

    resumed = []

    def resume(path, *, _attempt_lease):
        resumed.append(
            {
                "context": load_formal_theory_context(
                    path / "formal_context.json"
                ).context_hash,
                "blueprint": read_json(path / "blueprint.json", {}),
            }
        )
        return path

    result = advance_frontier_language_expansion(
        attempt, forge_fn=forge, resume_fn=resume
    )

    assert result["status"] == "successor_epoch_admitted"
    assert len(resumed) == 1
    assert resumed[0]["blueprint"]["mode"] == "anonymous_signature_census"
    assert resumed[0]["blueprint"]["formula_grammar"] == target_grammar
    assert not (attempt / "evidence_context.json").exists()
    assert (attempt / "evidence_context.epoch-000.json").is_file()
    assert (attempt / "formal_context.epoch-001.json").is_file()


def _typed_host_rejection_completion(attempt, gap, rejection_class):
    leakage = rejection_class == ADAPTER_FORGE_REJECTION_PRE_REVIEW_LEAKAGE
    proposal_digest = content_hash({"fixture": "prior-contaminated-proposal"})
    host_core = {
        "schema": "leanmill.adapter_forge_host_rejection.v2",
        "gap_id": gap.gap_id,
        "interface": "leanmill.object_coordinates.v1",
        "host_conformance_contract": ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        "proposal_digest": proposal_digest,
        "ok": False,
        "error_type": "AdapterForgeHostConformanceRejected",
        "reason": (
            "pre-review target-evaluation leakage contaminated the proposal"
            if leakage
            else "finite family source_refs must contain strings"
        ),
        "rejection_class": rejection_class,
        "violations": [
            {
                "code": (
                    "pre_review_target_outcome_in_self_test"
                    if leakage
                    else "member_source_refs_not_string_identities"
                ),
                "category": (
                    "epistemic_ordering" if leakage else "structural_contract"
                ),
                "artifact_role": "self_test" if leakage else "capability_source",
                "artifact_path": "prior_proposal.json",
                "json_path": "$",
                "summary": "typed fixture violation",
                "repair_scope": (
                    "fresh_cold_reauthor_required"
                    if leakage
                    else "same_agent_new_bytes_permitted"
                ),
            }
        ],
        "same_agent_repair_allowed": not leakage,
        "workspace_reuse_allowed": not leakage,
        "automatic_retry_performed": False,
        "required_agent_identity": (
            "fresh_cold_adapter_forge_leaf"
            if leakage
            else "same_adapter_forge_leaf_permitted"
        ),
        "recovery_route": (
            "reauthor_in_fresh_cold_workspace_with_new_agent_identity"
            if leakage
            else "return_typed_structural_repair_to_campaign"
        ),
        "authority": "deterministic_host_conformance",
        "claim_boundary": "the rejected proposal grants no capability authority",
    }
    host = {**host_core, "receipt_sha256": content_hash(host_core)}
    skipped = {
        "schema": "leanmill.adapter_forge_review_skipped.v1",
        "accepted": False,
        "rationale": "host conformance rejected the proposal before review",
        "host_rejection_receipt_sha256": host["receipt_sha256"],
        "authority": "host_lifecycle",
    }
    receipt_core = {
        "schema": "leanmill.adapter_forge_quarantine_receipt.v1",
        "gap_id": gap.gap_id,
        "proposed_adapter_id": gap.proposed_adapter_id,
        "proposal_digest": proposal_digest,
        "host_conformance": host,
        "independent_review": skipped,
        "review_evidence_binding": None,
        "status": "quarantined_capability_rejected",
        "live_registry_mutated": False,
        "exactness_authority_granted": False,
        "next_step": host["recovery_route"],
    }
    receipt = {**receipt_core, "receipt_sha256": content_hash(receipt_core)}
    completion_core = {
        "schema": "leanmill.adapter_forge_completion.v1",
        "status": "adapter_proposal_rejected_return_to_search",
        "attempt_dir": str(attempt),
        "gap_id": gap.gap_id,
        "host_conformance_contract": ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        "quarantine_receipt": receipt,
        "reason": "host_conformance_rejected:" + host["reason"],
        "rejection_class": rejection_class,
        "recovery_route": host["recovery_route"],
        "evidence_refs": [receipt["receipt_sha256"]],
        "provider_calls": 1,
    }
    return {
        **completion_core,
        "completion_sha256": content_hash(completion_core),
    }


def _recovery_transition_fixture(
    attempt,
    owner,
    workspace,
    gap,
    predecessor,
    *,
    index=1,
):
    frozen_path = workspace / "adapter_gap.json"
    if not frozen_path.is_file():
        write_text_atomic(frozen_path, '{"schema":"fixture"}')
    frozen_digest = hashlib.sha256(frozen_path.read_bytes()).hexdigest()
    rejection = predecessor["quarantine_receipt"]["host_conformance"]
    leakage = rejection["rejection_class"] == (
        ADAPTER_FORGE_REJECTION_PRE_REVIEW_LEAKAGE
    )
    request = gap.primitive_semantics_contract["theory_language_request"]
    core = {
        "schema": "leanmill.adapter_forge_recovery_transition.v1",
        "gap_id": gap.gap_id,
        "request_id": request["request_id"],
        "context_hash": request["source_context_hash"],
        "source_epoch": int(request.get("source_epoch", 0)),
        "predecessor_completion_sha256": predecessor["completion_sha256"],
        "host_rejection_receipt_sha256": rejection["receipt_sha256"],
        "rejection_class": rejection["rejection_class"],
        "recovery_mode": (
            "fresh_cold_reauthor" if leakage else "typed_structural_repair"
        ),
        "recovery_attempt_index": index,
        "workspace": str(workspace.relative_to(attempt)),
        "workspace_input_manifest": [
            {"path": "adapter_gap.json", "bytes_sha256": frozen_digest}
        ],
        "frozen_input_manifest": [
            {"path": "adapter_gap.json", "bytes_sha256": frozen_digest}
        ],
        "prior_proposal_bytes_available": not leakage,
        "prior_proposal_resubmission_allowed": False,
        "prior_workspace_reused": not leakage,
        "prior_agent_identity_reused": False,
        "prior_agent_calls_replayed": False,
        "agent_instance_id": "attempt-002",
        "budget_phase": "expansion",
        "authority": "deterministic_campaign_lifecycle",
        "claim_boundary": "fixture",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def test_recovery_transition_rejects_workspace_escape(tmp_path):
    attempt = tmp_path / "attempt"
    gap = _evidence_family_gap("context:recovery-path")
    predecessor = _typed_host_rejection_completion(
        attempt, gap, ADAPTER_FORGE_REJECTION_PRE_REVIEW_LEAKAGE
    )
    owner = (
        adapter_forge_attempt_directory(attempt, gap.gap_id, create=True)
        / "recovery_attempts"
        / "attempt-001"
    )
    workspace = owner / "cold_input" / "workspace"
    workspace.mkdir(parents=True)
    transition = _recovery_transition_fixture(
        attempt, owner, workspace, gap, predecessor
    )

    replayed, resolved = _validate_adapter_forge_recovery_transition(
        attempt,
        owner=owner,
        transition=transition,
        gap=gap,
        predecessor=predecessor,
        recovery_attempt_index=1,
    )
    assert replayed == transition
    assert resolved == workspace.resolve()

    outside = attempt / "outside-workspace"
    outside.mkdir(parents=True)
    escaped_core = {
        **{
            key: value
            for key, value in transition.items()
            if key != "receipt_sha256"
        },
        "workspace": str(outside.relative_to(attempt)),
    }
    escaped = {
        **escaped_core,
        "receipt_sha256": content_hash(escaped_core),
    }
    with pytest.raises(ValueError, match="changed identity"):
        _validate_adapter_forge_recovery_transition(
            attempt,
            owner=owner,
            transition=escaped,
            gap=gap,
            predecessor=predecessor,
            recovery_attempt_index=1,
        )


def test_forge_conformance_rejects_coding_leaf_frozen_input_mutation(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    frozen = workspace / "adapter_gap.json"
    write_text_atomic(frozen, '{"gap_id":"frozen"}')
    manifest = [
        {
            "path": "adapter_gap.json",
            "bytes_sha256": hashlib.sha256(frozen.read_bytes()).hexdigest(),
        }
    ]

    _verify_adapter_forge_frozen_inputs(workspace, manifest)
    write_text_atomic(frozen, '{"gap_id":"mutated"}')
    with pytest.raises(ValueError, match="changed a frozen host input"):
        _verify_adapter_forge_frozen_inputs(workspace, manifest)


def test_recovery_completion_rejects_ambiguous_successor_branch(tmp_path):
    attempt = tmp_path / "attempt"
    gap = _evidence_family_gap("context:recovery-branch")
    predecessor = _typed_host_rejection_completion(
        attempt, gap, ADAPTER_FORGE_REJECTION_PRE_REVIEW_LEAKAGE
    )
    base = adapter_forge_attempt_directory(attempt, gap.gap_id, create=True)
    write_json_atomic(base / "adapter_forge_completion.json", predecessor)
    for index in (1, 2):
        owner = base / "recovery_attempts" / f"attempt-{index:03d}"
        owner.mkdir(parents=True)
        core = {
            "schema": "leanmill.adapter_forge_completion.v1",
            "status": "adapter_proposal_rejected_return_to_search",
            "gap_id": gap.gap_id,
            "host_conformance_contract": ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
            "artifact_owner": str(owner.relative_to(attempt)),
            "recovery_attempt_index": index,
            "predecessor_completion_sha256": predecessor["completion_sha256"],
        }
        write_json_atomic(
            owner / "adapter_forge_completion.json",
            {**core, "completion_sha256": content_hash(core)},
        )

    with pytest.raises(ValueError, match="multiple successors"):
        _read_adapter_forge_lifecycle_completion(attempt, gap)


@pytest.mark.parametrize(
    ("rejection_class", "expected_mode", "prior_workspace_visible"),
    [
        (
            ADAPTER_FORGE_REJECTION_PRE_REVIEW_LEAKAGE,
            "fresh_cold_reauthor",
            False,
        ),
        (
            ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT,
            "typed_structural_repair",
            True,
        ),
    ],
)
def test_runner_reauthors_typed_forge_rejection_under_subordinate_identity(
    tmp_path,
    monkeypatch,
    rejection_class,
    expected_mode,
    prior_workspace_visible,
):
    import ztare.leanmill.adapter_forge as forge_module
    import ztare.leanmill.frontier_campaign_runner as runner_module

    attempt = _language_attempt(tmp_path, "runner-cold-forge-recovery")
    assert advance_frontier_language_expansion(attempt)["status"] == (
        "adapter_forge_required"
    )
    gap = AdapterGap.from_json(read_json(attempt / "adapter_gap.json", {}))
    prior_workspace = stage_adapter_forge_workspace(
        attempt, gap, source_repo=Path.cwd()
    )
    write_text_atomic(prior_workspace / "prior_proposal.json", "contaminated-bytes")
    write_text_atomic(prior_workspace / "prior_test.py", "outcome = 'accepted'\n")
    prior_call_dir = attempt / "agent_calls" / "adapter_forge.attempt-001"
    prior_call_dir.mkdir(parents=True)
    prior_result = {"proposal": "contaminated-call-result"}
    write_json_atomic(prior_call_dir / "000.result.json", prior_result)
    write_json_atomic(
        prior_call_dir / "000.call.json",
        {"returncode": 0, "agent_id": "axiompack-adapter_forge-attempt-001"},
    )
    completion = _typed_host_rejection_completion(
        attempt, gap, rejection_class
    )
    base_owner = adapter_forge_attempt_directory(
        attempt, gap.gap_id, create=True
    )
    write_json_atomic(base_owner / "adapter_forge_completion.json", completion)

    role_calls = []

    class FakeRole:
        def __init__(self, role_name, repo, artifact_dir, instance_id):
            self.role = role_name
            self.repo = repo
            self.artifact_dir = artifact_dir
            self.agent_id = f"fixture-{role_name}-{instance_id}"
            self.instance_id = instance_id
            self.config = FrontierAgentConfig(
                runtime="claude",
                model="fixture",
                reasoning_effort="low",
                timeout_seconds=30,
                visible_workbench=role_name == "adapter_forge",
            )
            self.output_schema = None
            self.provider_call_count = 0

        def __call__(self, prompt):
            self.provider_call_count += 1
            role_calls.append(
                {
                    "role": self.role,
                    "instance_id": self.instance_id,
                    "repo": self.repo,
                    "prompt": prompt,
                }
            )
            if self.role == "adapter_reviewer":
                return {
                    "accepted": False,
                    "reviewer_ref": self.agent_id,
                    "rationale": "fixture review wrapper accepted a mapping payload",
                    "evidence_refs": [],
                }
            return {
                "source_paths": ["new_proposal.json"],
                "test_paths": ["new_test.py"],
                "manifest": {
                    "capability_source": "new_proposal.json",
                    "interface": "leanmill.finite_construction_family.v1",
                    "request_id": "fixture",
                    "observable_paths": [],
                },
                "self_test_receipts": ["sha256:fresh"],
                "registry_mutation": False,
            }

    def fake_role(_definition, *, role_name, repo, artifact_dir, instance_id=""):
        return FakeRole(role_name, repo, artifact_dir, instance_id)

    def fake_run(
        active_gap,
        *,
        coding_agent_fn,
        host_conformance_fn,
        independent_review_fn,
        budget_ledger,
    ):
        proposal = coding_agent_fn("frozen-gap-prompt")
        review_probe = independent_review_fn(
            {"gap": active_gap.to_json(), "proposal": proposal}
        )
        assert review_probe["accepted"] is False
        host_core = {
            "schema": "leanmill.adapter_forge_host_rejection.v2",
            "gap_id": active_gap.gap_id,
            "host_conformance_contract": ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
            "proposal_digest": content_hash(dict(proposal)),
            "ok": False,
            "reason": "fixture stops after inspecting recovery isolation",
            "rejection_class": "unclassified_host_conformance_error",
            "violations": [],
            "same_agent_repair_allowed": False,
            "workspace_reuse_allowed": False,
            "automatic_retry_performed": False,
            "required_agent_identity": "fresh_campaign_disposition_required",
            "recovery_route": "return_rejection_to_theory_search",
            "authority": "deterministic_host_conformance",
            "claim_boundary": "fixture rejection grants no authority",
        }
        host = {**host_core, "receipt_sha256": content_hash(host_core)}
        skipped = {
            "schema": "leanmill.adapter_forge_review_skipped.v1",
            "accepted": False,
            "rationale": "host conformance rejected the proposal before review",
            "host_rejection_receipt_sha256": host["receipt_sha256"],
            "authority": "host_lifecycle",
        }
        receipt_core = {
            "schema": "leanmill.adapter_forge_quarantine_receipt.v1",
            "gap_id": active_gap.gap_id,
            "proposed_adapter_id": active_gap.proposed_adapter_id,
            "proposal_digest": content_hash(dict(proposal)),
            "host_conformance": host,
            "independent_review": skipped,
            "review_evidence_binding": None,
            "status": "quarantined_capability_rejected",
            "live_registry_mutated": False,
            "exactness_authority_granted": False,
            "next_step": "return_rejection_to_theory_search",
        }
        return {**receipt_core, "receipt_sha256": content_hash(receipt_core)}

    monkeypatch.setattr(runner_module, "frontier_agent_role", fake_role)
    monkeypatch.setattr(forge_module, "run_adapter_forge", fake_run)

    result = execute_frontier_adapter_forge(attempt, repo=Path.cwd())

    assert result["recovery_attempt_index"] == 1
    assert result["predecessor_completion_sha256"] == completion[
        "completion_sha256"
    ]
    coding_call = next(row for row in role_calls if row["role"] == "adapter_forge")
    assert coding_call["instance_id"] == "attempt-002"
    assert coding_call["instance_id"] != "attempt-001"
    recovery_workspace = Path(coding_call["repo"])
    assert (recovery_workspace / "prior_proposal.json").is_file() is (
        prior_workspace_visible
    )
    assert read_json(prior_call_dir / "000.result.json", {}) == prior_result
    transition = read_json(
        attempt
        / result["artifact_owner"]
        / "adapter_forge_recovery_transition.json",
        {},
    )
    assert transition["recovery_mode"] == expected_mode
    assert transition["prior_proposal_bytes_available"] is (
        prior_workspace_visible
    )
    assert transition["prior_proposal_resubmission_allowed"] is False
    assert transition["prior_agent_identity_reused"] is False
    assert transition["prior_agent_calls_replayed"] is False
    if prior_workspace_visible:
        repair = read_json(
            recovery_workspace / "adapter_forge_structural_repair_input.json", {}
        )
        assert repair["authority"] == "repair_input_only"
        assert repair["allowed_reuse"]["prior_proposal_as_output"] is False
    else:
        assert not (recovery_workspace / "prior_test.py").exists()
        cold = read_json(
            recovery_workspace / "adapter_forge_cold_reauthor_input.json", {}
        )
        assert cold["prior_proposal_available"] is False
        assert "contaminated-call-result" not in coding_call["prompt"]


def test_adapter_forge_budget_unavailable_returns_typed_navigation_input(
    tmp_path,
):
    attempt = _language_attempt(tmp_path, "forge-budget-feedback")
    resumed = []

    def exhausted_forge(_path, *, _attempt_lease):
        raise BudgetExceeded("hard_cap_reached:provider_calls")

    result = advance_frontier_language_expansion(
        attempt,
        forge_fn=exhausted_forge,
        resume_fn=lambda path, **_kwargs: resumed.append(path),
    )

    assert result["status"] == "unavailable"
    run = read_json(attempt / "run.json", {})
    assert run["status"] == "frontier_objective_unmet"
    feedback = run["navigation"]["objective_review_history"][-1]
    assert feedback["outcome"] == "unavailable"
    assert feedback["reason"] == (
        "adapter_forge_budget_unavailable:hard_cap_reached:provider_calls"
    )
    assert feedback["route"] == "continue_search"
    assert len(resumed) == 1


def test_recovery_budget_receipts_are_carried_into_navigation(tmp_path):
    attempt = _language_attempt(tmp_path, "forge-recovery-budget-feedback")

    def unavailable_recovery(path, *, _attempt_lease):
        gap = AdapterGap.from_json(read_json(path / "adapter_gap.json", {}))
        transition_core = {
            "schema": "leanmill.adapter_forge_recovery_transition.v1",
            "gap_id": gap.gap_id,
            "recovery_mode": "fresh_cold_reauthor",
        }
        transition = {
            **transition_core,
            "receipt_sha256": content_hash(transition_core),
        }
        input_core = {
            "schema": "leanmill.adapter_forge_cold_reauthor_input.v1",
            "gap_id": gap.gap_id,
            "recovery_transition_receipt_sha256": transition["receipt_sha256"],
        }
        recovery_input = {
            **input_core,
            "receipt_sha256": content_hash(input_core),
        }
        unavailable_core = {
            "schema": "leanmill.adapter_forge_recovery_unavailable.v1",
            "gap_id": gap.gap_id,
            "reason": "adapter_forge_recovery_budget_unavailable:provider_calls",
        }
        unavailable = {
            **unavailable_core,
            "receipt_sha256": content_hash(unavailable_core),
        }
        return {
            "schema": "leanmill.adapter_forge_recovery_outcome.v1",
            "status": "unavailable",
            "gap_id": gap.gap_id,
            "reason": unavailable["reason"],
            "evidence_refs": [
                transition["receipt_sha256"],
                recovery_input["receipt_sha256"],
                unavailable["receipt_sha256"],
            ],
            "recovery_transition": transition,
            "recovery_input": recovery_input,
            "unavailability_receipt": unavailable,
        }

    result = advance_frontier_language_expansion(
        attempt, forge_fn=unavailable_recovery
    )

    assert result["status"] == "unavailable"
    run = read_json(attempt / "run.json", {})
    feedback = run["navigation"]["objective_review_history"][-1]
    carried = run["navigation"]["carried_evidence_receipts"]
    assert feedback["outcome"] == "unavailable"
    assert {row["evidence_ref"] for row in carried} == set(
        feedback["evidence_refs"]
    )
    assert {row["receipt"]["schema"] for row in carried} == {
        "leanmill.adapter_forge_recovery_transition.v1",
        "leanmill.adapter_forge_cold_reauthor_input.v1",
        "leanmill.adapter_forge_recovery_unavailable.v1",
    }


def test_budget_extension_reopens_the_exact_pending_forge_recovery(tmp_path):
    attempt = _language_attempt(tmp_path, "forge-recovery-budget-reopen")

    def reject_once(path, **_kwargs):
        gap = AdapterGap.from_json(read_json(path / "adapter_gap.json", {}))
        completion = _typed_host_rejection_completion(
            path, gap, ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT
        )
        write_json_atomic(
            adapter_forge_attempt_directory(
                path, gap.gap_id, create=True
            )
            / "adapter_forge_completion.json",
            completion,
        )
        return completion

    advance_frontier_language_expansion(
        attempt,
        forge_fn=reject_once,
    )
    gap = AdapterGap.from_json(read_json(attempt / "adapter_gap.json", {}))
    predecessor = read_adapter_forge_completion(attempt, gap)
    assert predecessor is not None
    recovery_owner = (
        adapter_forge_attempt_directory(attempt, gap.gap_id)
        / "recovery_attempts"
        / "attempt-001"
    )
    workspace = recovery_owner / "workspace"
    workspace.mkdir(parents=True)
    transition = _recovery_transition_fixture(
        attempt,
        recovery_owner,
        workspace,
        gap,
        predecessor,
    )
    write_json_atomic(
        recovery_owner / "adapter_forge_recovery_transition.json",
        transition,
    )
    input_core = {
        "schema": "leanmill.adapter_forge_structural_repair_input.v1",
        "gap_id": gap.gap_id,
        "recovery_transition_receipt_sha256": transition["receipt_sha256"],
    }
    recovery_input = {
        **input_core,
        "receipt_sha256": content_hash(input_core),
    }
    unavailable_core = {
        "schema": "leanmill.adapter_forge_recovery_unavailable.v1",
        "gap_id": gap.gap_id,
        "recovery_attempt_index": 1,
        "recovery_transition_receipt_sha256": transition["receipt_sha256"],
        "reason": (
            "adapter_forge_recovery_budget_unavailable:"
            "adapter_forge_attempts"
        ),
        "authority": "exploration_budget_ledger",
    }
    unavailable = {
        **unavailable_core,
        "receipt_sha256": content_hash(unavailable_core),
    }
    current = read_json(attempt / "run.json", {})
    navigation = dict(current.get("navigation") or {})
    navigation["adapter_gap"] = gap.to_json()
    blocked_core = {
        **{
            key: value
            for key, value in current.items()
            if key not in {"run_digest", "adapter_gap"}
        },
        "status": "blocked_adapter_gap",
        "adapter_gap": gap.to_json(),
        "navigation": navigation,
    }
    current = {
        **blocked_core,
        "run_digest": content_hash(blocked_core),
    }
    write_json_atomic(attempt / "run.json", current)
    feedback = _language_outcome_feedback(
        attempt,
        current,
        outcome="unavailable",
        reason=unavailable["reason"],
        evidence_refs=(
            transition["receipt_sha256"],
            recovery_input["receipt_sha256"],
            unavailable["receipt_sha256"],
        ),
        evidence_receipts=(transition, recovery_input, unavailable),
    )
    assert feedback["request_id"] == transition["request_id"]
    budget = ExplorationBudget.from_json(
        read_json(attempt / "budget.json", {})
    )
    ExplorationBudgetLedger(
        attempt / "budget.events.jsonl",
        budget,
        attempt_id=attempt.name,
    ).extend_resources(
        phase="expansion",
        resources={"adapter_forge_attempts": 1},
        authority_ref="principal:test",
        reason="resume the exact pending structural recovery",
    )

    assert next_frontier_campaign_action(attempt) == (
        "reopen_extended_adapter_recovery"
    )
    _reopen_extended_adapter_recovery(attempt)
    reopened = read_json(attempt / "run.json", {})
    assert reopened["status"] == "blocked_adapter_gap"
    receipt = reopened["navigation"]["objective_review_history"][-1]
    assert receipt["predecessor_completion_sha256"] == (
        predecessor["completion_sha256"]
    )
    assert receipt["recovery_transition_receipt_sha256"] == (
        transition["receipt_sha256"]
    )
    assert next_frontier_campaign_action(attempt) == "advance_language"


def test_language_feedback_carries_typed_outcome_into_next_request(tmp_path):
    attempt = _language_attempt(tmp_path, "typed-language-outcome-transport")
    run = read_json(attempt / "run.json", {})
    outcome_core = {
        "schema": "leanmill.test_typed_campaign_outcome.v1",
        "context_hash": run["context_hash"],
        "status": "exhausted",
        "authority": "deterministic_campaign_lifecycle",
    }
    outcome = {
        **outcome_core,
        "receipt_sha256": content_hash(outcome_core),
    }

    feedback = _language_outcome_feedback(
        attempt,
        run,
        outcome="rejected",
        reason="reviewed_family_exhausted",
        evidence_refs=(outcome["receipt_sha256"],),
        evidence_receipts=(outcome,),
    )
    updated = read_json(attempt / "run.json", {})
    carried = updated["navigation"]["carried_evidence_receipts"]

    assert feedback["evidence_refs"] == [outcome["receipt_sha256"]]
    assert carried == [
        {
            "evidence_ref": outcome["receipt_sha256"],
            "receipt": outcome,
        }
    ]
    assert _resolve_workbench_evidence_receipts(
        attempt,
        updated["navigation"],
        [outcome["receipt_sha256"]],
    ) == [outcome]


def test_language_feedback_rejects_unlisted_typed_outcome(tmp_path):
    attempt = _language_attempt(tmp_path, "unlisted-language-outcome")
    run = read_json(attempt / "run.json", {})
    core = {
        "schema": "leanmill.test_typed_campaign_outcome.v1",
        "status": "exhausted",
        "authority": "deterministic_campaign_lifecycle",
    }
    outcome = {**core, "receipt_sha256": content_hash(core)}

    with pytest.raises(ValueError, match="outside its refs"):
        _language_outcome_feedback(
            attempt,
            run,
            outcome="rejected",
            reason="reviewed_family_exhausted",
            evidence_refs=("another-receipt",),
            evidence_receipts=(outcome,),
        )


def _coordinate_application(source, gap_id: str) -> dict:
    source_sort = source.signature.sorts[0].name
    signature = TheorySignature(
        name=source.signature.name,
        sorts=source.signature.sorts,
        operations=(
            *source.signature.operations,
            OperationSymbol("coordinate", (source_sort,), source_sort),
        ),
        relations=source.signature.relations,
    )
    models = {}
    for record in source.universe.models:
        model = record.model
        size = dict(model.sort_sizes)[source_sort]
        image = FiniteModel(
            sort_sizes=model.sort_sizes,
            operations=(*model.operations, ("coordinate", tuple(range(size)))),
            relations=model.relations,
        )
        models[record.model_id] = image.to_json()
    core = {
        "schema": "leanmill.finite_model_functor_application.v1",
        "gap_id": gap_id,
        "context_hash": source.context_hash,
        "functor_id": "campaign-local:test-coordinate",
        "signature": signature.to_json(),
        "models": models,
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _materialized_coordinate_generator(source, gap: AdapterGap) -> dict:
    image = _coordinate_application(source, gap.gap_id)
    raw_sort = source.signature.sorts[0].name
    raw_model = FiniteModel(
        sort_sizes=((raw_sort, 3),),
        operations=((source.signature.operations[0].name, (0,) * 9),),
    )
    abstract_signature = TheorySignature.from_json(image["signature"])
    abstract_model = FiniteModel(
        sort_sizes=raw_model.sort_sizes,
        operations=(*raw_model.operations, ("coordinate", (0, 1, 2))),
    )
    request = gap.primitive_semantics_contract["theory_language_request"]
    core = {
        "schema": CANDIDATE_SCHEMA,
        "request_id": request["request_id"],
        "gap_id": gap.gap_id,
        "context_hash": source.context_hash,
        "codec_id": "campaign-local:coordinate-factorization",
        "raw_signature": source.signature.to_json(),
        "abstract_signature": abstract_signature.to_json(),
        "raw_base_axioms": [row.to_json() for row in source.base_axioms],
        "source_alpha_models": image["models"],
        "source_lowered_models": {
            row.model_id: row.model.to_json() for row in source.universe.models
        },
        "generated_batches": [
            {
                "raw_sort_sizes": {raw_sort: 3},
                "abstract_sort_sizes": {raw_sort: 3},
                "models": [{
                    "abstract_model": abstract_model.to_json(),
                    "raw_model": raw_model.to_json(),
                }],
                "generator_ref": "fixture:order-three-coordinate-construction",
            }
        ],
        "generator_provenance_refs": ["fixture:construction-replay"],
        "max_relabelings": 720,
        "isomorphism_policy": ISOMORPHISM_POLICY,
    }
    return {**core, "receipt_sha256": content_hash(core)}


def test_functor_application_requires_exact_source_coverage(tmp_path):
    from ztare.leanmill.adapters.generic_fol_finite import (
        build_context_from_functor_application,
    )

    attempt = _language_attempt(tmp_path, "partial-functor-image")
    source = load_formal_theory_context(attempt / "formal_context.json")
    application = _coordinate_application(source, "partial-image")
    application["models"].pop(next(iter(application["models"])))
    core = {key: value for key, value in application.items() if key != "receipt_sha256"}
    application["receipt_sha256"] = content_hash(core)
    with pytest.raises(ValueError, match="cover every source object exactly"):
        build_context_from_functor_application(
            source,
            application,
            formula_grammar={
                "schema": "leanmill.universal_equation_grammar.v1",
                "max_total_operation_order": 2,
            },
        )


def test_language_request_forge_review_builds_successor_and_resumes_without_provider(tmp_path):
    attempt = _language_attempt(tmp_path, source_task_scope=True)
    source = load_formal_theory_context(attempt / "formal_context.json")

    def forge(path, *, _attempt_lease):
        def host(_proposal, typed_gap):
            application = _coordinate_application(source, typed_gap.gap_id)
            owner = adapter_forge_attempt_directory(
                path, typed_gap.gap_id, create=True
            )
            write_json_atomic(owner / "theory_language_functor_image.json", application)
            core = {
                "ok": True,
                "context_hash": source.context_hash,
                "functor_image_receipt_sha256": application["receipt_sha256"],
            }
            return {**core, "receipt_sha256": content_hash(core)}

        return execute_adapter_forge_attempt(
            path,
                coding_agent_fn=lambda _prompt: {
                    "source_paths": ["coordinate.py"],
                    "test_paths": ["test_coordinate.py"],
                    "manifest": {"request_id": "campaign-local-coordinate"},
                "self_test_receipts": ["sha256:deterministic"],
                "registry_mutation": False,
            },
            host_conformance_fn=host,
            independent_review_fn=lambda payload: {
                "accepted": True,
                "reviewer_ref": "independent-language-reviewer",
                "rationale": "The total finite image passes the frozen host boundary.",
                "evidence_refs": [payload["host_conformance"]["receipt_sha256"]],
            },
        )

    resumed = []

    def resume(path, *, _attempt_lease):
        checkpoint = read_json(path / "navigation_epoch_checkpoint.json", {})
        resumed.append(checkpoint["trace"][0]["decision"])
        return path

    result = advance_frontier_language_expansion(
        attempt, forge_fn=forge, resume_fn=resume
    )
    assert result["status"] == "successor_epoch_admitted"
    assert result["target_epoch"] == 1
    assert resumed == ["language_successor_admitted"]
    assert not (attempt / "run.json").exists()
    assert (attempt / "formal_context.epoch-001.json").is_file()
    successor = load_formal_theory_context(attempt / "formal_context.epoch-001.json")
    assert "coordinate" in successor.signature.operation_map
    successor_blueprint = read_json(attempt / "blueprint.epoch-001.json", {})
    assert "theory_task_capability_scope" not in successor_blueprint[
        "navigator_contract"
    ]
    verification = successor_blueprint["verification_plan"]
    assert not {
        "larger_carriers", "larger_model_strata", "heldout_strata"
    }.intersection(verification)
    assert verification["successor_claim_boundary"]["model_scope"] == (
        "exact_frozen_source_functor_image"
    )
    assert "fixed_size_countermodel_finder" not in successor_blueprint[
        "executable_preflight_receipt"
    ]["adapter_capabilities"]
    consumption = read_json(
        attempt / "theory_language_successor_consumption.epoch-001.json", {}
    )
    assert consumption["global_registry_mutated"] is False
    audit = audit_project_schema_routes(attempt)
    route = next(
        row for row in audit["routes"]
        if row["route_id"] == "theory_language_compilation_outcome_totality.v1"
    )
    assert route["unconsumed_count"] == 0
    assert route["produced_count"] == route["consumed_count"] == 2


def test_blocked_language_request_consumes_reviewed_data_only_generator(tmp_path):
    attempt = _language_attempt(tmp_path, "generative-language-successor")
    source = load_formal_theory_context(attempt / "formal_context.json")
    registry_before = registered_theory_adapter_ids()

    def forge(path, *, _attempt_lease):
        gap = AdapterGap.from_json(read_json(path / "adapter_gap.json", {}))
        workspace = stage_adapter_forge_workspace(path, gap)
        candidate = _materialized_coordinate_generator(source, gap)
        write_json_atomic(workspace / "generative_candidate.json", candidate)
        write_json_atomic(
            workspace / "candidate_checks.json",
            {"candidate_receipt_sha256": candidate["receipt_sha256"]},
        )

        def host(proposal, typed_gap):
            owner = adapter_forge_attempt_directory(
                path, typed_gap.gap_id, create=True
            )
            return host_capability_conformance(
                proposal,
                typed_gap,
                workspace=workspace,
                output_path=owner / "theory_language_coordinates.json",
            )

        return execute_adapter_forge_attempt(
            path,
            coding_agent_fn=lambda _prompt: {
                "source_paths": ["generative_candidate.json"],
                "test_paths": ["candidate_checks.json"],
                "manifest": {
                    "capability_source": "generative_candidate.json",
                    "interface": CANDIDATE_SCHEMA,
                    "request_id": candidate["request_id"],
                    "observable_paths": [],
                },
                "self_test_receipts": [candidate["receipt_sha256"]],
                "registry_mutation": False,
            },
            host_conformance_fn=host,
            independent_review_fn=lambda payload: {
                "accepted": True,
                "reviewer_ref": "fixture:independent-generative-review",
                "rationale": "The fixed materialization replays through the host.",
                "evidence_refs": [
                    payload["host_conformance"]["receipt_sha256"]
                ],
            },
        )

    result = advance_frontier_language_expansion(attempt, forge_fn=forge)
    assert result["status"] == "successor_epoch_admitted"
    assert registered_theory_adapter_ids() == registry_before
    active_gap = AdapterGap.from_json(read_json(attempt / "adapter_gap.json", {}))
    owner = adapter_forge_attempt_directory(attempt, active_gap.gap_id)
    assert (owner / "theory_language_generative_candidate.json").is_file()
    assert (owner / "theory_language_generative_application.json").is_file()

    successor = load_formal_theory_context(attempt / "formal_context.epoch-001.json")
    blueprint = read_json(attempt / "blueprint.epoch-001.json", {})
    representation = blueprint["adapter_config"]["generative_representation"]
    assert blueprint["verification_plan"]["heldout_strata"] == [
        {"sort_sizes": {successor.signature.sorts[0].name: 3}}
    ]
    generated = FiniteModel.from_json(
        representation["candidate"]["generated_batches"][0]["models"][0][
            "abstract_model"
        ]
    )
    target = next(
        row.axiom
        for row in successor.formula_profiles
        if not evaluate_axiom(successor.signature, row.axiom, generated)
    )
    finder = materialize_theory_adapter_capability(
        blueprint["adapter_id"],
        "fixed_size_countermodel_finder",
        signature=successor.signature,
        adapter_config=blueprint["adapter_config"],
    )
    boundary = finder(
        (),
        target,
        sort_sizes=dict(generated.sort_sizes),
        base_axioms=successor.base_axioms,
        timeout_ms=1,
    )
    assert boundary.status == "countermodel_found"
    assert boundary.solver.startswith("reviewed_generative_representation:")


def test_registered_language_compiler_admits_successor_without_forge(
    tmp_path, monkeypatch
):
    from ztare.leanmill.adapters import generic_fol_finite

    compiler = generic_fol_finite.compile_theory_language_expansion

    def registered_compiler(**kwargs):
        application = _coordinate_application(
            kwargs["source_context"], "registered-compiler"
        )
        return compiler(**{**kwargs, "approved_application": application})

    monkeypatch.setitem(
        generic_fol_finite.CAPABILITIES,
        "theory_language_expansion_compiler",
        registered_compiler,
    )
    attempt = _language_attempt(
        tmp_path,
        "registered-language-successor",
        expected_status="frontier_language_expansion_requested",
    )
    stale_wave = attempt / "agent_calls" / "navigator.wave-003"
    stale_wave.mkdir(parents=True)
    write_json_atomic(stale_wave / "000.result.json", {"decision": "request"})
    resumed = []
    result = advance_frontier_language_expansion(
        attempt,
        forge_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("registered compiler must bypass AdapterForge")
        ),
    )
    assert result["status"] == "successor_epoch_admitted"
    assert (attempt / "theory_language_successor_commit.json").is_file()
    assert not stale_wave.exists()
    assert (
        attempt / "agent_calls" / "navigator.wave-003.epoch-000"
    ).is_dir()
    assert next_frontier_campaign_action(attempt) == (
        "recover_language_successor"
    )
    recovered = advance_frontier_language_expansion(
        attempt,
        forge_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("committed successor must bypass AdapterForge")
        ),
        resume_fn=lambda path, **_kwargs: resumed.append(path),
    )
    assert recovered["recovered"] is True
    assert len(resumed) == 1
    assert not (attempt / "theory_language_successor_commit.json").exists()
    assert (attempt / "theory_language_successor_commit.epoch-001.json").is_file()
    successor = load_formal_theory_context(attempt / "formal_context.epoch-001.json")
    assert "coordinate" in successor.signature.operation_map
    admission = read_json(attempt / "registered_language_compiler_admission.json", {})
    assert admission["authority"] == "leanmill.theory_adapter_registry"
    audit = audit_project_schema_routes(attempt)
    route = next(
        row for row in audit["routes"]
        if row["route_id"] == "theory_language_compilation_outcome_totality.v1"
    )
    assert route["unconsumed_count"] == 0
    assert route["produced_count"] == route["consumed_count"] == 1


@pytest.mark.parametrize(
    ("forge_outcome", "expected_outcome"),
    [
        ("rejected", "rejected"),
        ("unavailable", "unavailable"),
        ("coordinate_only", "unavailable"),
    ],
)
def test_language_advancement_returns_nonadmitted_outcomes_to_navigation(
    tmp_path, forge_outcome, expected_outcome
):
    attempt = _language_attempt(tmp_path, f"language-{forge_outcome}")
    resumed = []

    def forge(path, *, _attempt_lease):
        if forge_outcome == "coordinate_only":
            return execute_adapter_forge_attempt(
                path,
                coding_agent_fn=lambda _prompt: {
                    "source_paths": ["coordinate.py"],
                    "test_paths": ["test_coordinate.py"],
                    "manifest": {"request_id": "coordinate-only"},
                    "self_test_receipts": ["sha256:deterministic"],
                    "registry_mutation": False,
                },
                host_conformance_fn=lambda _proposal, _gap: (
                    lambda core: {**core, "receipt_sha256": content_hash(core)}
                )({"ok": True, "coordinate_receipt_sha256": "sha256:" + "a" * 64}),
                independent_review_fn=lambda payload: {
                    "accepted": True,
                    "reviewer_ref": "coordinate-reviewer",
                    "rationale": "Coordinate bytes pass, but no functor image was supplied.",
                    "evidence_refs": [payload["host_conformance"]["receipt_sha256"]],
                },
            )
        return {
            "status": (
                "adapter_proposal_rejected_return_to_search"
                if forge_outcome == "rejected"
                else "unavailable"
            ),
            "reason": f"fixture_{forge_outcome}",
            "evidence_refs": [f"receipt:{forge_outcome}"],
        }

    advance_frontier_language_expansion(
        attempt,
        forge_fn=forge,
        resume_fn=lambda path, **_kwargs: resumed.append(path),
    )
    run = read_json(attempt / "run.json", {})
    assert run["status"] == "frontier_objective_unmet"
    feedback = run["navigation"]["objective_review_history"][-1]
    assert feedback["outcome"] == expected_outcome
    assert feedback["request_id"].startswith("theory-language-request:")
    assert feedback["repeat_requires_new_evidence"] is True
    assert "next_discriminator" not in feedback
    assert "kill_condition" not in feedback
    assert len(resumed) == 1
    audit = audit_project_schema_routes(attempt)
    route = next(
        row for row in audit["routes"]
        if row["route_id"] == "theory_language_compilation_outcome_totality.v1"
    )
    assert route["unconsumed_count"] == 0


def test_language_advancement_ignores_completion_owned_by_an_older_gap(tmp_path):
    attempt = _language_attempt(tmp_path, "cross-gap-forge-completion")
    stale_completion_core = {
        "schema": "leanmill.adapter_forge_completion.v1",
        "gap_id": "adapter-gap:historical",
        "status": "adapter_proposal_rejected_return_to_search",
        "reason": "historical_gap_rejection",
        "evidence_refs": ["receipt:historical"],
    }
    write_json_atomic(
        attempt / "adapter_forge_completion.json",
        {
            **stale_completion_core,
            "completion_sha256": content_hash(stale_completion_core),
        },
    )
    stale_receipt_core = {
        "schema": "leanmill.adapter_forge_quarantine_receipt.v1",
        "gap_id": "adapter-gap:historical",
        "status": "quarantined_capability_rejected",
    }
    write_json_atomic(
        attempt / "adapter_forge_receipt.json",
        {
            **stale_receipt_core,
            "receipt_sha256": content_hash(stale_receipt_core),
        },
    )
    calls = []

    def forge(_path, *, _attempt_lease):
        calls.append("current_gap")
        return {
            "status": "unavailable",
            "reason": "current_gap_runtime_unavailable",
            "evidence_refs": ["receipt:current"],
        }

    result = advance_frontier_language_expansion(attempt, forge_fn=forge)

    assert result["status"] == "unavailable"
    assert calls == ["current_gap"]
    assert read_json(attempt / "adapter_forge_completion.json", {})["gap_id"] == (
        "adapter-gap:historical"
    )
    feedback = read_json(attempt / "theory_language_compilation_feedback.json", {})
    assert feedback["reason"] == "current_gap_runtime_unavailable"


def test_matching_flat_completion_migrates_only_at_the_execution_door(tmp_path):
    attempt = _language_attempt(tmp_path, "legacy-forge-migration")
    run = read_json(attempt / "run.json", {})
    advance_frontier_language_expansion(attempt)
    gap = AdapterGap.from_json(read_json(attempt / "adapter_gap.json", {}))
    completion_core = {
        "schema": "leanmill.adapter_forge_completion.v1",
        "gap_id": gap.gap_id,
        "host_conformance_contract": ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        "status": "adapter_proposal_rejected_return_to_search",
        "reason": "legacy_exact_gap",
        "evidence_refs": ["receipt:legacy"],
    }
    completion = {
        **completion_core,
        "completion_sha256": content_hash(completion_core),
    }
    write_json_atomic(attempt / "adapter_forge_completion.json", completion)
    owner = adapter_forge_attempt_directory(attempt, gap.gap_id)

    assert read_adapter_forge_completion(attempt, gap) == completion
    assert not owner.exists()
    assert read_adapter_forge_completion(
        attempt, gap, migrate_legacy=True
    ) == completion
    assert read_json(owner / "adapter_forge_completion.json", {}) == completion
    assert (owner / "legacy_migration.json").is_file()
    assert run["context_hash"] == gap.primitive_semantics_contract[
        "theory_language_request"
    ]["source_context_hash"]


def test_legacy_migration_preflights_all_occupied_targets_before_writing(tmp_path):
    attempt = _language_attempt(tmp_path, "legacy-forge-occupied-target")
    advance_frontier_language_expansion(attempt)
    gap = AdapterGap.from_json(read_json(attempt / "adapter_gap.json", {}))
    completion_core = {
        "schema": "leanmill.adapter_forge_completion.v1",
        "gap_id": gap.gap_id,
        "host_conformance_contract": ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        "status": "adapter_proposal_rejected_return_to_search",
        "reason": "legacy_exact_gap",
        "evidence_refs": ["receipt:legacy"],
    }
    completion = {
        **completion_core,
        "completion_sha256": content_hash(completion_core),
    }
    write_json_atomic(attempt / "adapter_forge_completion.json", completion)
    owner = adapter_forge_attempt_directory(
        attempt,
        gap.gap_id,
        create=True,
    )
    occupied = owner / "legacy_migration.json"
    write_text_atomic(occupied, "null\n")
    before = occupied.read_bytes()

    with pytest.raises(ValueError, match="slot conflicts with occupied bytes"):
        read_adapter_forge_completion(attempt, gap, migrate_legacy=True)
    assert occupied.read_bytes() == before
    assert not (owner / "adapter_forge_completion.json").exists()
    assert read_json(attempt / "adapter_forge_completion.json", {}) == completion


def test_precontract_gap_completion_remains_history_for_current_host(tmp_path):
    attempt = _language_attempt(tmp_path, "precontract-forge-history")
    advance_frontier_language_expansion(attempt)
    gap = AdapterGap.from_json(read_json(attempt / "adapter_gap.json", {}))
    old_core = {
        "schema": "leanmill.adapter_forge_completion.v1",
        "gap_id": gap.gap_id,
        "status": "adapter_proposal_rejected_return_to_search",
        "reason": "evaluated_by_precontract_host",
    }
    old_completion = {
        **old_core,
        "completion_sha256": content_hash(old_core),
    }
    gap_owner = adapter_forge_gap_directory(attempt, gap.gap_id, create=True)
    old_path = gap_owner / "adapter_forge_completion.json"
    write_json_atomic(old_path, old_completion)

    assert read_adapter_forge_completion(attempt, gap) is None
    assert read_json(old_path, {}) == old_completion
    assert not adapter_forge_attempt_directory(attempt, gap.gap_id).exists()


def test_scoped_completion_rejects_stale_nested_host_contract(tmp_path):
    attempt = tmp_path / "stale-contract-attempt"
    gap = _evidence_family_gap("context:stale-contract")
    receipt = run_adapter_forge(
        gap,
        coding_agent_fn=lambda _prompt: {
            "source_paths": ["fixture.json"],
            "test_paths": ["check.json"],
            "manifest": {"request_id": "fixture"},
            "self_test_receipts": ["sha256:fixture"],
            "registry_mutation": False,
        },
        host_conformance_fn=lambda _proposal, _gap: (
            lambda core: {**core, "receipt_sha256": content_hash(core)}
        )({"ok": True, "tests": 1}),
        independent_review_fn=lambda payload: {
            "accepted": True,
            "reviewer_ref": "reviewer",
            "rationale": "generic host receipt",
            "evidence_refs": [
                payload["host_conformance"]["receipt_sha256"]
            ],
        },
    )
    core = {
        "schema": "leanmill.adapter_forge_completion.v1",
        "status": "quarantined_adapter_proposal_requires_authority_and_new_attempt",
        "attempt_dir": str(attempt),
        "gap_id": gap.gap_id,
        "host_conformance_contract": (
            ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT
        ),
        "quarantine_receipt": receipt,
        "reason": "stale nested contract",
        "rejection_class": "",
        "recovery_route": "",
        "evidence_refs": [receipt["receipt_sha256"]],
        "provider_calls": 2,
    }
    completion = {**core, "completion_sha256": content_hash(core)}
    owner = adapter_forge_attempt_directory(
        attempt,
        gap.gap_id,
        host_conformance_contract=(
            ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT
        ),
        create=True,
    )
    write_json_atomic(owner / "adapter_forge_completion.json", completion)
    with pytest.raises(ValueError, match="crossed its host contract"):
        read_adapter_forge_completion(attempt, gap)


def test_scoped_completion_rejects_occupied_nonobject_slot(tmp_path):
    attempt = tmp_path / "occupied-completion-attempt"
    gap = _evidence_family_gap("context:occupied-completion")
    owner = adapter_forge_attempt_directory(
        attempt, gap.gap_id, create=True
    )
    write_text_atomic(owner / "adapter_forge_completion.json", "null\n")
    with pytest.raises(ValueError, match="slot is malformed"):
        read_adapter_forge_completion(attempt, gap)


def test_scoped_completion_reader_binds_receipt_and_rejects_symlinks(tmp_path):
    attempt = tmp_path / "safe-scoped-completion"
    gap = _evidence_family_gap("context:safe-scoped-completion")
    completion = _typed_host_rejection_completion(
        attempt,
        gap,
        ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT,
    )
    owner = adapter_forge_attempt_directory(
        attempt,
        gap.gap_id,
        create=True,
    )
    completion_path = owner / "adapter_forge_completion.json"
    write_json_atomic(completion_path, completion)
    receipt_sha256 = completion["quarantine_receipt"]["receipt_sha256"]
    assert read_scoped_adapter_forge_completion(
        attempt,
        gap_id=gap.gap_id,
        host_conformance_contract=ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        quarantine_receipt_sha256=receipt_sha256,
    ) == completion
    with pytest.raises(ValueError, match="crossed frozen receipt identity"):
        read_scoped_adapter_forge_completion(
            attempt,
            gap_id=gap.gap_id,
            host_conformance_contract=ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
            quarantine_receipt_sha256="f" * 64,
        )

    replacement = tmp_path / "replacement-completion.json"
    write_json_atomic(replacement, completion)
    completion_path.unlink()
    completion_path.symlink_to(replacement)
    with pytest.raises(ValueError, match="not a regular file"):
        read_adapter_forge_completion(attempt, gap)


def test_scoped_and_legacy_completion_reads_are_byte_bounded(
    tmp_path,
    monkeypatch,
):
    import ztare.leanmill.adapter_forge as forge_module

    attempt = tmp_path / "bounded-completion"
    gap = _evidence_family_gap("context:bounded-completion")
    completion = _typed_host_rejection_completion(
        attempt,
        gap,
        ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT,
    )
    owner = adapter_forge_attempt_directory(
        attempt,
        gap.gap_id,
        create=True,
    )
    write_json_atomic(owner / "adapter_forge_completion.json", completion)
    monkeypatch.setattr(
        forge_module,
        "_MAX_ADAPTER_FORGE_CONFORMANCE_BYTES",
        64,
    )
    with pytest.raises(ValueError, match="byte ceiling"):
        read_adapter_forge_completion(attempt, gap)

    legacy_attempt = tmp_path / "bounded-legacy-completion"
    legacy_attempt.mkdir()
    legacy_completion_path = legacy_attempt / "adapter_forge_completion.json"
    legacy_receipt_path = legacy_attempt / "adapter_forge_receipt.json"
    write_json_atomic(legacy_completion_path, completion)
    write_json_atomic(
        legacy_receipt_path,
        completion["quarantine_receipt"],
    )
    monkeypatch.setattr(
        forge_module,
        "_MAX_ADAPTER_FORGE_CONFORMANCE_BYTES",
        max(
            legacy_completion_path.stat().st_size,
            legacy_receipt_path.stat().st_size,
        ) + 1,
    )
    with pytest.raises(ValueError, match="aggregate byte ceiling"):
        read_adapter_forge_completion(legacy_attempt, gap, migrate_legacy=True)


def test_construction_rejection_persists_under_construction_host_contract(
    tmp_path,
):
    attempt = _language_attempt(tmp_path, "construction-contract-rejection")
    advance_frontier_language_expansion(attempt)
    gap = AdapterGap.from_json(read_json(attempt / "adapter_gap.json", {}))
    completion = execute_adapter_forge_attempt(
        attempt,
        coding_agent_fn=lambda _prompt: {
            "source_paths": ["parameterization.json"],
            "test_paths": ["check.json"],
            "manifest": {
                "interface": CONSTRUCTION_PARAMETERIZATION_SCHEMA,
                "request_id": "fixture",
                "capability_source": "parameterization.json",
                "observable_paths": [],
            },
            "self_test_receipts": ["sha256:fixture"],
            "registry_mutation": False,
        },
        host_conformance_fn=lambda _proposal, _gap: (
            _ for _ in ()
        ).throw(ValueError("construction backend problem is malformed")),
        independent_review_fn=lambda _payload: (_ for _ in ()).throw(
            AssertionError("host rejection must skip review")
        ),
    )
    assert completion["host_conformance_contract"] == (
        ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT
    )
    construction_owner = adapter_forge_attempt_directory(
        attempt,
        gap.gap_id,
        host_conformance_contract=(
            ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT
        ),
    )
    assert read_json(
        construction_owner / "adapter_forge_completion.json", {}
    ) == completion
    assert read_adapter_forge_completion(attempt, gap) == completion


def test_live_forge_does_not_overwrite_crash_left_conflicting_receipt(tmp_path):
    attempt = _language_attempt(tmp_path, "crash-left-forge-receipt")
    advance_frontier_language_expansion(attempt)
    gap = AdapterGap.from_json(read_json(attempt / "adapter_gap.json", {}))
    owner = adapter_forge_attempt_directory(
        attempt,
        gap.gap_id,
        create=True,
    )
    receipt_path = owner / "adapter_forge_receipt.json"
    write_json_atomic(receipt_path, {"schema": "crash-left-fixture.v1"})
    before = receipt_path.read_bytes()

    with pytest.raises(ValueError, match="slot conflicts with occupied bytes"):
        execute_adapter_forge_attempt(
            attempt,
            coding_agent_fn=lambda _prompt: {
                "source_paths": ["fixture.json"],
                "test_paths": ["check.json"],
                "manifest": {"request_id": "fixture"},
                "self_test_receipts": ["sha256:fixture"],
                "registry_mutation": False,
            },
            host_conformance_fn=lambda _proposal, _gap: (
                _ for _ in ()
            ).throw(ValueError("typed crash-left rejection")),
            independent_review_fn=lambda _payload: (
                _ for _ in ()
            ).throw(AssertionError("host rejection must skip review")),
        )
    assert receipt_path.read_bytes() == before
    assert not (owner / "adapter_forge_completion.json").exists()



def test_direct_compiler_rejection_becomes_feedback_without_forge(tmp_path, monkeypatch):
    from ztare.leanmill.adapters import generic_fol_finite
    from ztare.leanmill.frontier_campaign_actions import replay_frontier_campaign

    monkeypatch.setitem(
        generic_fol_finite.CAPABILITIES,
        "theory_language_expansion_compiler",
        lambda **_kwargs: {"status": "rejected", "reason": "typed_fixture_rejection"},
    )
    attempt = _language_attempt(
        tmp_path,
        "language-direct-rejected",
        expected_status="frontier_language_expansion_requested",
    )
    result = advance_frontier_language_expansion(
        attempt,
        forge_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("compiler rejection must bypass AdapterForge")
        ),
    )
    assert result["status"] == "rejected"
    run = read_json(attempt / "run.json", {})
    feedback = run["navigation"]["objective_review_history"][-1]
    assert feedback["outcome"] == "rejected"
    assert feedback["repeat_requires_new_evidence"] is True
    assert not (attempt / "adapter_gap.json").exists()
    replay = replay_frontier_campaign(attempt)
    assert replay["ok"] is True
    assert replay["language_compilation_feedback_check"]["outcome"] == "rejected"
    audit = audit_project_schema_routes(attempt)
    route = next(
        row for row in audit["routes"]
        if row["route_id"] == "theory_language_compilation_outcome_totality.v1"
    )
    assert route["unconsumed_count"] == 0
