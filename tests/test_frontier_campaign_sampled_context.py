from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from typing import Any

import pytest

from ztare.common.finite_protocol_theory_adapter import (
    FiniteProtocolTheoryAdapter,
    ProtocolObservation,
)
from ztare.leanmill.adapters.finite_protocol import build_evidence_context
from ztare.leanmill.axiompack_leaf_workbench import (
    AXIOMPACK_LEAF_WORKBENCH_CONTRACT,
)
from ztare.leanmill.formal_verification_provider import generate_keypair
from ztare.leanmill.frontier_blueprint import FrontierTheoryBlueprint
from ztare.leanmill.frontier_campaign import (
    packet_for_context,
    packet_for_exact_context,
    sign_frontier_campaign,
    validate_campaign_artifact_binding,
)
from ztare.leanmill.explore_axiom_space import freeze_frontier_context_packet
from ztare.leanmill.theory_campaign_journal import TheoryCampaignJournal
from ztare.leanmill.theory_interest import profile_theory_program_predictions
from ztare.leanmill.theory_navigator import run_interactive_theory_navigator


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _sampled_context():
    config = {
        "states": ["s0", "s1"],
        "actions": ["step"],
        "observations": [
            {
                "observation_id": "obs-0",
                "state": "s0",
                "action": "step",
                "next_state": "s1",
            }
        ],
    }
    adapter = FiniteProtocolTheoryAdapter(
        states=config["states"], actions=config["actions"]
    )
    state = adapter.abstract(
        (ProtocolObservation("obs-0", "s0", "step", "s1"),)
    )
    return build_evidence_context(
        adapter.signature(state), adapter_config=config, strata=()
    )


def _sampled_packet(*, context=None):
    context = context or _sampled_context()
    return packet_for_context(
        campaign_id="sampled-protocol-smoke",
        blueprint_id="blueprint:sampled-protocol-smoke",
        eigenquestion="Which transition programs survive this observed panel?",
        context=context,
        formula_grammar={"schema": "protocol-program-grammar-v1"},
        pack_arity=2,
        navigator_contract=AXIOMPACK_LEAF_WORKBENCH_CONTRACT,
        sealed_context_manifest_digest="sha256:" + "0" * 64,
        query_budget={"raw_checks": 2},
        stop_rule={"max_finalists": 2},
        mode="evidence_induced",
    )


def _sampled_blueprint(context) -> FrontierTheoryBlueprint:
    return FrontierTheoryBlueprint(
        brief_digest="brief:" + "a" * 64,
        mode="evidence_induced",
        eigenquestion="Which transition programs predict the withheld panel cells?",
        signature=context.signature.to_json(),
        primitive_semantics={"adapter_owned": True},
        base_axioms=(),
        base_theory_status="explicit_empty",
        adapter_id="finite_deterministic_protocol.v1",
        adapter_config={"sampled_panel": True},
        formula_grammar={"schema": "protocol-program-grammar-v1"},
        model_or_observation_strata=(
            {"stratum_id": "observed-transition", "object_count": 1},
        ),
        pack_arity=2,
        collapse_controls=(),
        visible_evidence_manifest={"object_count": 1},
        sealed_evidence_manifest_digest="sha256:" + "0" * 64,
        deanchoring_policy={"cold_after_compilation": True},
        navigator_contract={
            "adapter_id": "axiompack",
            "selection_mode": "theory_program",
        },
        query_budget={"max_finalists": 1},
        stop_rule={"freeze_after_finalists": 1},
        verification_plan={"raw_panel_replay": True},
        codec_versions={"context": context.schema},
        authority_refs=("campaign-authority",),
        compiler_receipt={"authority_role": "blueprint-compiler"},
        semantic_review_receipt={
            "authority_role": "semantic-reviewer",
            "accepted": True,
        },
        executable_preflight_receipt={"ok": True},
    )


def test_sampled_packet_exposes_panel_uses_without_census_or_closure_authority():
    context = _sampled_context()
    packet = _sampled_packet(context=context)
    manifest = packet.visible_context_manifest

    assert manifest["context_exact"] is False
    assert manifest["claim_scope"] == "sampled_panel_behavior"
    assert manifest["permitted_semantic_uses"] == [
        "behavioral_routing",
        "prediction_profiles",
    ]
    assert manifest["exact_closure_authority"] is False
    assert manifest["canonical_model_count"] is None
    assert manifest["model_ids_digest"] == ""
    assert manifest["model_census_receipt_digest"] == ""
    assert manifest["completeness_receipt_digest"] == ""
    assert packet.navigator_contract["schema"] == (
        "leanmill-axiompack-sampled-leaf-workbench-v1"
    )
    assert "list_theory_nodes" not in packet.navigator_contract["capability_ids"]
    assert "inspect_theory_node" not in packet.navigator_contract["capability_ids"]
    assert "compare_theory_nodes" not in packet.navigator_contract["capability_ids"]

    assert context.semantic_formula_classes()
    supported = [
        row.attribute_id
        for row in context.incidence.profiles
        if row.truth_bits == context.incidence.base_mask
    ]
    profile = profile_theory_program_predictions(
        context, (supported[0],), (supported[1],)
    )
    assert profile["context_exact"] is False
    assert profile["predictions"][0]["chart_status"] == "holds_on_observed_context"
    assert profile["predictions"][0]["consequence_class"] == (
        "unpriced_sample_relative_support"
    )
    with pytest.raises(ValueError, match="exact closure"):
        context.closure_ids((supported[0],))
    with pytest.raises(ValueError, match="complete context"):
        packet_for_exact_context(
            campaign_id="invalid-exact-door",
            blueprint_id="blueprint:invalid-exact-door",
            eigenquestion="Can this panel close a theory?",
            context=context,
            formula_grammar={"schema": "protocol-program-grammar-v1"},
            pack_arity=1,
            navigator_contract=AXIOMPACK_LEAF_WORKBENCH_CONTRACT,
            sealed_context_manifest_digest="sha256:" + "0" * 64,
            query_budget={"raw_checks": 1},
            stop_rule={"max_finalists": 1},
            mode="evidence_induced",
        )


def test_sampled_packet_round_trip_revalidates_claim_authority():
    context = _sampled_context()
    packet = _sampled_packet(context=context)
    private, _public = generate_keypair()
    campaign = sign_frontier_campaign(
        packet, private_key_pem=private, signer_ref="campaign-authority"
    ).to_json()

    replayed = validate_campaign_artifact_binding(
        campaign,
        blueprint_id=packet.blueprint_id,
        context_hash=context.context_hash,
        expected_packet_digest=packet.digest,
    )
    assert replayed["visible_context_manifest"]["exact_closure_authority"] is False


def test_sampled_packet_and_navigator_freeze_remain_panel_relative(tmp_path):
    context = _sampled_context()
    blueprint = _sampled_blueprint(context)
    private, _public = generate_keypair()

    packet = freeze_frontier_context_packet(
        tmp_path,
        blueprint,
        context,
        campaign_id="sampled-protocol-freeze",
        context_epoch=0,
        formula_proposal_hashes=(),
        packet_signer=lambda value: sign_frontier_campaign(
            value,
            private_key_pem=private,
            signer_ref="campaign-authority",
        ),
    )
    signed_artifact = json.loads((tmp_path / "campaign.json").read_text())
    assert signed_artifact["packet_digest"] == packet.digest
    assert packet.visible_context_manifest["exact_closure_authority"] is False
    assert "list_theory_nodes" not in packet.navigator_contract["capability_ids"]

    supported = [
        row.attribute_id
        for row in context.incidence.profiles
        if row.truth_bits == context.incidence.base_mask
    ]
    navigation = run_interactive_theory_navigator(
        context,
        blueprint,
        TheoryCampaignJournal(tmp_path / "events.jsonl"),
        agent_fn=lambda _prompt: {
            "decision": "freeze",
            "formula_ids": [supported[0]],
            "boundary_target_ids": [supported[1]],
            "rationale": "Freeze this panel-relative prediction for raw replay.",
        },
        attempt_id="sampled-attempt",
        campaign_id="sampled-protocol-freeze",
        max_rounds=1,
        max_finalists=1,
    )
    finalist = navigation["finalists"][0]
    assert finalist["candidate_kind"] == "theory_program"
    assert finalist["closure_size"] is None
    assert finalist["residual_prediction_formula_ids"] == []
    assert finalist["prediction_profile"]["context_exact"] is False
    assert finalist["prediction_profile"]["predictions"][0]["chart_status"] == (
        "holds_on_observed_context"
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("claim_scope", "exact_bounded_closure"),
        ("exact_closure_authority", True),
        (
            "permitted_semantic_uses",
            ["behavioral_routing", "prediction_profiles", "exact_bounded_closure"],
        ),
        ("completeness_receipt_digest", "forged-completeness"),
        ("canonical_model_count", 1),
    ),
)
def test_artifact_replay_rejects_sampled_exactness_laundering(field, value):
    context = _sampled_context()
    packet = _sampled_packet(context=context)
    private, _public = generate_keypair()
    campaign = deepcopy(
        sign_frontier_campaign(
            packet, private_key_pem=private, signer_ref="campaign-authority"
        ).to_json()
    )
    campaign["packet"]["visible_context_manifest"][field] = value
    campaign["packet_digest"] = _digest(campaign["packet"])

    with pytest.raises(ValueError):
        validate_campaign_artifact_binding(
            campaign,
            blueprint_id=packet.blueprint_id,
            context_hash=context.context_hash,
        )


def test_artifact_replay_rejects_exact_only_sampled_navigator_capabilities():
    context = _sampled_context()
    packet = _sampled_packet(context=context)
    private, _public = generate_keypair()
    campaign = deepcopy(
        sign_frontier_campaign(
            packet, private_key_pem=private, signer_ref="campaign-authority"
        ).to_json()
    )
    campaign["packet"]["navigator_contract"]["capability_ids"].append(
        "list_theory_nodes"
    )
    campaign["packet_digest"] = _digest(campaign["packet"])

    with pytest.raises(ValueError, match="exact-context capabilities"):
        validate_campaign_artifact_binding(
            campaign,
            blueprint_id=packet.blueprint_id,
            context_hash=context.context_hash,
        )


def test_sampled_context_receipt_cannot_be_emitted_as_completeness_authority():
    context = replace(
        _sampled_context(), completeness_receipt_digest="sample-panel-provenance"
    )
    manifest = _sampled_packet(context=context).visible_context_manifest
    assert manifest["context_exact"] is False
    assert manifest["completeness_receipt_digest"] == ""
    assert manifest["model_census_receipt_digest"] == ""
