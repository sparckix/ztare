from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from test_construction_artifact_ratification import _successful_fake_solver
from test_finite_construction_family import _artifact, _capability
from ztare.leanmill.adapter_forge import (
    ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
    bind_adapter_review_evidence,
)
from ztare.leanmill.finite_construction_family import (
    FINITE_CONSTRUCTION_FAMILY_CLAIM_SCOPE,
    FINITE_CONSTRUCTION_FAMILY_SCHEMA,
    construction_witness_interface,
    execute_finite_construction_family,
)
from ztare.leanmill.frontier_blueprint import (
    FrontierExplorationBrief,
    frontier_objective_contract,
)
from ztare.leanmill.frontier_blueprint_compiler import (
    compile_structure_first_blueprint,
)
from ztare.leanmill.reviewed_family_member_ratification import (
    build_reviewed_family_member_ratification_admission,
    ratify_reviewed_family_member_action,
)
from ztare.leanmill.reviewed_family_objective_discharge import (
    build_reviewed_family_objective_discharge,
    validate_reviewed_family_objective_discharge,
)
from ztare.leanmill.theory_ir import SortDecl, TheorySignature, content_hash
from ztare.leanmill.theory_language import (
    build_theory_language_expansion_request,
)
from ztare.leanmill.theory_lineage_synthesis import (
    lineage_synthesis_input,
    validate_lineage_synthesis_decision,
)


def _adapter_config() -> dict:
    return {
        "construction_target": {
            "schema": "leanmill.binary_linear_code_target_config.v1",
            "field_order": 2,
            "length": 4,
            "dimension": 2,
            "minimum_distance": 2,
            "max_nonzero_messages": 3,
            "target_snapshot_sha256": "1" * 64,
        },
        "evidence_panel": {
            "schema": "leanmill.binary_linear_code_evidence_panel.v1",
            "field_order": 1,
            "completeness_scope": "declared_control_panel_only",
            "completeness_ref": "fixture:reviewed-family-objective",
            "objects": [
                {
                    "object_id": "control:one",
                    "stratum_id": "control",
                    "payload": {"label": "one"},
                }
            ],
            "hypotheses": [
                {
                    "hypothesis_id": "property:one",
                    "satisfied_object_ids": ["control:one"],
                    "anonymous_shape": {"kind": "control", "complexity": 1},
                    "payload": {"checker_ref": "fixture:one"},
                }
            ],
        },
    }


def _blueprint():
    brief = FrontierExplorationBrief(
        "Exercise the reviewed finite-family terminal transition.",
        source_mode="structure_first",
    )
    return compile_structure_first_blueprint(
        brief,
        {
            "mode": "evidence_induced",
            "eigenquestion": "Does a reviewed family contain the target witness?",
            "signature": TheorySignature(
                name="Evidence", sorts=(SortDecl("Observation"),)
            ).to_json(),
            "primitive_semantics": {
                "operation_bindings": {},
                "relation_bindings": {},
            },
            "base_axioms": (),
            "base_theory_status": "explicit_empty",
            "adapter_id": "binary_linear_code.v1",
            "adapter_config": _adapter_config(),
            "formula_grammar": {},
            "model_or_observation_strata": (),
            "pack_arity": 1,
            "collapse_controls": (),
            "visible_evidence_manifest": {"source_refs": ["fixture:panel"]},
            "sealed_evidence_manifest_digest": "sha256:" + "0" * 64,
            "deanchoring_policy": {"cold_after_signature_compilation": True},
            "navigator_contract": {"selection_mode": "theory_program"},
            "query_budget": {"max_finalists": 1},
            "stop_rule": {
                "user_instruction": "Construct and ratify the frozen binary code.",
                "executable_condition": {
                    "kind": "late_lineage_objective_review"
                },
            },
            "verification_plan": {},
            "codec_versions": {"evidence": "fixture-v1"},
            "authority_refs": ("fixture:campaign-authority",),
        },
    )


def _family(request_id: str, interface: dict) -> dict:
    artifact = _artifact("0x3", "0xc")
    parameter_ids = ["p0"]
    core = {
        "schema": FINITE_CONSTRUCTION_FAMILY_SCHEMA,
        "request_id": request_id,
        "gap_id": "adapter-gap:test",
        "context_hash": "context:test",
        "adapter_id": "binary_linear_code.v1",
        "family_id": "family:reviewed-objective",
        "family_scope": "the exact one-member fixture family",
        "family_spec": {"kind": "explicit_test_relation", "version": 1},
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
                "parameter_id": "p0",
                "artifact": artifact,
                "artifact_sha256": content_hash(artifact),
                "derivation": {"kind": "fixture", "index": 0},
                "source_refs": ["fixture:seed"],
            }
        ],
        "claim_scope": FINITE_CONSTRUCTION_FAMILY_CLAIM_SCOPE,
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _forge_receipt(family: dict, interface: dict) -> dict:
    host_core = {
        "ok": True,
        "interface": FINITE_CONSTRUCTION_FAMILY_SCHEMA,
        "host_conformance_contract": ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        "gap_id": family["gap_id"],
        "context_hash": family["context_hash"],
        "adapter_id": family["adapter_id"],
        "family_id": family["family_id"],
        "finite_family_receipt_sha256": family["receipt_sha256"],
        "target_interface_sha256": interface["interface_sha256"],
        "outcomes_evaluated": False,
    }
    host = {**host_core, "receipt_sha256": content_hash(host_core)}
    review = {
        "accepted": True,
        "reviewer_ref": "independent-family-reviewer",
        "rationale": "the frozen family and scope are admissible",
        "evidence_refs": [host["receipt_sha256"]],
    }
    binding = bind_adapter_review_evidence(review, host)
    core = {
        "schema": "leanmill.adapter_forge_quarantine_receipt.v1",
        "gap_id": family["gap_id"],
        "proposed_adapter_id": family["adapter_id"],
        "proposal_digest": "2" * 64,
        "host_conformance": host,
        "independent_review": review,
        "review_evidence_binding": binding,
        "status": "quarantined_registry_proposal",
        "live_registry_mutated": False,
        "exactness_authority_granted": False,
        "next_step": "execute_reviewed_finite_construction_family",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _fixture(tmp_path: Path) -> tuple[dict, object]:
    blueprint = _blueprint()
    request = build_theory_language_expansion_request(
        source_context_hash="context:test",
        source_epoch=0,
        change_kind="quotient_or_coordinate_change",
        blind_spot="The current chart cannot enumerate the finite family.",
        proposed_interface="A reviewed explicit parameter-to-generator relation.",
        evidence_refs=("evidence:test",),
        discriminating_test="Execute every member and ratify a passing witness.",
        kill_condition="Return rejection or formal unavailability to navigation.",
    )
    lineage_id = "lineage:family-author"
    wrapper = {
        "lineage_id": lineage_id,
        "request_id": request.request_id,
        "request": request.to_json(),
    }
    navigation = {
        "context_hash": "context:test",
        "context_epoch": 0,
        "theory_language_expansion_requests": [wrapper],
        "finalists": [],
    }
    objective = frontier_objective_contract(blueprint)
    synthesis_input = lineage_synthesis_input(
        navigation, objective_contract=objective
    )
    synthesis = validate_lineage_synthesis_decision(
        synthesis_input,
        {
            "route": "escalate_language",
            "selected_request_ids": [request.request_id],
            "deferred_request_ids": [],
            "rationale": "The authored family is the selected discriminator.",
            "next_discriminator": request.discriminating_test,
            "kill_condition": request.kill_condition,
            "program_ids": [],
            "next_discriminator_request_ids": [request.request_id],
        },
    )
    interface = construction_witness_interface(
        blueprint.adapter_id, blueprint.adapter_config
    )
    family = _family(request.request_id, interface)
    execution = execute_finite_construction_family(
        family, witness_interface=interface, capability_fn=_capability
    )
    admission = build_reviewed_family_member_ratification_admission(
        family=family,
        family_execution=execution,
        forge_quarantine_receipt=_forge_receipt(family, interface),
        witness_interface=interface,
        parameter_id="p0",
    )
    aggregate = ratify_reviewed_family_member_action(
        admission,
        substrate=tmp_path,
        governed_solve_fn=_successful_fake_solver(tmp_path, {}),
    )
    navigation.update(
        {
            "lineage_synthesis": synthesis,
            "language_expansion_request": request.to_json(),
            "finite_construction_family_execution": execution,
        }
    )
    run_core = {
        "schema": "leanmill.frontier_exploration_run.v1",
        "status": "frontier_objective_witness_found_pending_ratification",
        "context_hash": "context:test",
        "context_summary": {"context_epoch": 0},
        "navigation": navigation,
    }
    source_run = {**run_core, "run_digest": content_hash(run_core)}
    receipt = build_reviewed_family_objective_discharge(
        source_pending_run=source_run,
        blueprint=blueprint,
        active_request=request,
        synthesis_input=synthesis_input,
        synthesis_decision=synthesis,
        family_execution=execution,
        admission=admission,
        ratification_aggregate=aggregate,
        attempted_ratification_aggregate_sha256s=(
            aggregate["aggregate_sha256"],
        ),
        frozen_lineage_ids=(lineage_id,),
    )
    return receipt, blueprint


def _rehash_receipt(receipt: dict) -> None:
    core = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    receipt["receipt_sha256"] = content_hash(core)


def test_reviewed_family_discharge_replays_every_embedded_authority(
    tmp_path: Path,
) -> None:
    receipt, blueprint = _fixture(tmp_path)

    assert validate_reviewed_family_objective_discharge(
        receipt, current_blueprint=blueprint
    ) == receipt
    assert receipt["source_lineage_ids"] == ["lineage:family-author"]
    assert receipt["frozen_lineage_ids"] == ["lineage:family-author"]
    objective = receipt["construction_objective"]
    assert objective["adapter_config"] == _adapter_config()
    assert objective["frozen_nl_objective"] == (
        "Construct and ratify the frozen binary code."
    )


def test_reviewed_family_discharge_rejects_rehashed_objective_mutation(
    tmp_path: Path,
) -> None:
    receipt, _blueprint_value = _fixture(tmp_path)
    tampered = deepcopy(receipt)
    objective = tampered["construction_objective"]
    objective["frozen_nl_objective"] = "A residual-hunter replacement objective."
    objective_core = {
        key: value for key, value in objective.items() if key != "objective_sha256"
    }
    objective["objective_sha256"] = content_hash(objective_core)
    tampered["construction_objective_sha256"] = objective["objective_sha256"]
    _rehash_receipt(tampered)

    with pytest.raises(ValueError, match="construction objective changed identity"):
        validate_reviewed_family_objective_discharge(tampered)


def test_reviewed_family_discharge_rejects_request_and_synthesis_tampering(
    tmp_path: Path,
) -> None:
    receipt, _blueprint_value = _fixture(tmp_path)

    request_tampered = deepcopy(receipt)
    replacement = build_theory_language_expansion_request(
        source_context_hash="context:test",
        source_epoch=0,
        change_kind="quotient_or_coordinate_change",
        blind_spot="A different but individually valid request.",
        proposed_interface="A different reviewed relation.",
        evidence_refs=("evidence:test",),
        discriminating_test="Execute a different relation.",
        kill_condition="Return its outcome.",
    )
    request_tampered["active_language_request"] = replacement.to_json()
    request_tampered["language_request_id"] = replacement.request_id
    _rehash_receipt(request_tampered)
    with pytest.raises(ValueError, match="active language request differs"):
        validate_reviewed_family_objective_discharge(request_tampered)

    synthesis_tampered = deepcopy(receipt)
    decision = synthesis_tampered["lineage_synthesis_decision"]
    decision["rationale"] = "A re-authored synthesis rationale."
    decision_core = {
        key: value for key, value in decision.items() if key != "receipt_sha256"
    }
    decision["receipt_sha256"] = content_hash(decision_core)
    synthesis_tampered["lineage_synthesis_decision_sha256"] = decision[
        "receipt_sha256"
    ]
    _rehash_receipt(synthesis_tampered)
    with pytest.raises(ValueError, match="pending run lacks the exact"):
        validate_reviewed_family_objective_discharge(synthesis_tampered)
