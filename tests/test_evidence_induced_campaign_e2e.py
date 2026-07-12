from __future__ import annotations

from ztare.leanmill.exploration_budget import budget_preset
from ztare.leanmill.explore_axiom_space import (
    execute_frontier_boundaries,
    explore_axiom_space,
)
from ztare.leanmill.formal_verification_provider import generate_keypair
from ztare.leanmill.frontier_campaign import sign_frontier_campaign
from ztare.leanmill.frontier_campaign_definition import FrontierCampaignDefinition
from ztare.leanmill.theory_ir import SortDecl, TheorySignature
from ztare.leanmill.theory_ir import content_hash


def _signer():
    private, _public = generate_keypair()
    return lambda packet: sign_frontier_campaign(
        packet,
        private_key_pem=private,
        signer_ref="campaign-authority",
    )


def test_campaign_yaml_routes_evidence_incidence_through_public_inlet(tmp_path):
    signature = TheorySignature(
        name="AnonymousEvidenceSurface",
        sorts=(SortDecl("Observation"),),
    )
    adapter_config = {
        "completeness_ref": "fixture:complete-five-observation-panel",
        "objects": [
            {"object_id": f"object:{index}", "payload": {"sealed_row_ref": f"row:{index}"}}
            for index in range(5)
        ],
        "hypotheses": [
            {
                "hypothesis_id": "hypothesis:a",
                "satisfied_object_ids": ["object:0", "object:1", "object:2"],
                "anonymous_shape": {"kind": "typed_predicate", "complexity": 1},
                "payload": {"checker_ref": "fixture:checker:a"},
            },
            {
                "hypothesis_id": "hypothesis:b",
                "satisfied_object_ids": ["object:0", "object:1", "object:3"],
                "anonymous_shape": {"kind": "typed_predicate", "complexity": 1},
                "payload": {"checker_ref": "fixture:checker:b"},
            },
            {
                "hypothesis_id": "hypothesis:joint",
                "satisfied_object_ids": ["object:0", "object:1", "object:4"],
                "anonymous_shape": {"kind": "typed_predicate", "complexity": 2},
                "payload": {"checker_ref": "fixture:checker:joint"},
            },
        ],
    }
    definition = FrontierCampaignDefinition(
        direction="Explore joint constraints in this complete anonymous observation panel.",
        source_mode="structure_first",
        requested_mode="evidence_induced",
        budget=budget_preset("local_only"),
    )
    draft = {
        "mode": "evidence_induced",
        "eigenquestion": "Which compact hypothesis packs create joint-only constraints?",
        "signature": signature.to_json(),
        "primitive_semantics": {"operation_bindings": {}, "relation_bindings": {}},
        "base_axioms": (),
        "base_theory_status": "explicit_empty",
        "adapter_id": "generic_finite_evidence.v1",
        "adapter_config": adapter_config,
        "formula_grammar": {"kind": "declared_executable_hypothesis_panel"},
        "model_or_observation_strata": ({"stratum_id": "declared_observations"},),
        "pack_arity": 2,
        "collapse_controls": (),
        "visible_evidence_manifest": {"object_ids_visible": False},
        "sealed_evidence_manifest_digest": "sha256:" + "0" * 64,
        "deanchoring_policy": {"cold_after_compilation": True},
        "navigator_contract": {
            "adapter_id": "axiompack",
            "selection_mode": "compact_axiom_pack",
        },
        "query_budget": {"max_finalists": 2, "max_ranked_queries": 2},
        "stop_rule": {"freeze_after_finalists": 2},
        "verification_plan": {"raw_boundary_checker": True},
        "codec_versions": {"context": "finite-incidence-v1"},
        "authority_refs": ("campaign-authority",),
    }
    attempt = tmp_path / "evidence-campaign"
    run = explore_axiom_space(
        definition,
        attempt_dir=attempt,
        typed_draft=draft,
        packet_signer=_signer(),
    )
    assert run.status == "frontier_candidates_frozen_awaiting_boundary_approval"
    assert run.context_summary["context_kind"] == "evidence_incidence"
    assert run.provider_calls == 0
    assert run.navigation["finalists"]
    finalist = run.navigation["finalists"][0]
    assert finalist["formula_ids"] == ["hypothesis:a", "hypothesis:b"]
    assert finalist["joint_only_consequence_ids"] == ["hypothesis:joint"]
    assert (attempt / "campaign_definition.yaml").is_file()
    assert (attempt / "evidence_context.json").is_file()
    completion = execute_frontier_boundaries(
        attempt,
        raw_boundary_fn=lambda _context, premises, target, _plan: {
            "schema": "test.raw_boundary.v1",
            "status": "counterexample_found",
            "premises": list(premises),
            "target": target,
            "receipt_sha256": content_hash({"premises": premises, "target": target}),
        },
    )
    assert completion["status"] == "campaign_completed"
    assert completion["boundary_result"]["query_results"][0]["raw_boundary"]["status"] == "counterexample_found"
    assert completion["boundary_result"]["next_epoch_proposal"]["proposed_additions"][0]["kind"] == "raw_counterexample"
    assert (attempt / "budget_stop_receipt.json").is_file()
    assert execute_frontier_boundaries(attempt) == completion

    replay = explore_axiom_space("ignored", attempt_dir=attempt)
    assert replay.to_json() == run.to_json()
