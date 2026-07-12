from __future__ import annotations

import pytest

from ztare.leanmill.adapter_forge import (
    AdapterGapRequired,
    execute_adapter_forge_attempt,
    render_adapter_forge_prompt,
    run_adapter_forge,
)
from ztare.leanmill.exploration_budget import budget_preset
from ztare.leanmill.explore_axiom_space import explore_axiom_space
from ztare.leanmill.frontier_campaign_definition import FrontierCampaignDefinition
from ztare.leanmill.frontier_blueprint import FrontierExplorationBrief
from ztare.leanmill.frontier_blueprint_compiler import compile_frontier_blueprint
from ztare.leanmill.magma_law_universe import anonymous_magma_signature
from ztare.leanmill.theory_adapter_registry import registered_theory_adapter_ids


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
        host_conformance_fn=lambda _proposal, _gap: {"ok": True, "tests": 8},
        independent_review_fn=lambda _payload: {"accepted": True, "reviewer_ref": "cold-reviewer"},
    )
    assert receipt["status"] == "quarantined_registry_proposal"
    assert receipt["live_registry_mutated"] is False
    assert receipt["exactness_authority_granted"] is False


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
        return {"ok": True, "tests": 9, "fixture_replay": True}

    def review(_payload):
        calls["review"] += 1
        return {
            "accepted": True,
            "reviewer_ref": "independent-adapter-reviewer",
            "rationale": "typed semantics and claim boundary match the frozen gap",
            "evidence_refs": ["sha256:determinism", "sha256:roundtrip"],
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
