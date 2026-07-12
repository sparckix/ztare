from __future__ import annotations

from dataclasses import replace

import pytest

from ztare.leanmill.axiompack_leaf_workbench import AXIOMPACK_LEAF_WORKBENCH_CONTRACT
from ztare.leanmill.finite_model_census import enumerate_magma_model_universe
from ztare.leanmill.finite_theory_context import build_formal_theory_context
from ztare.leanmill.formal_verification_provider import generate_keypair
from ztare.leanmill.frontier_campaign import (
    packet_for_exact_context,
    sign_frontier_campaign,
    validate_campaign_artifact_binding,
    verify_frontier_campaign,
)
from ztare.leanmill.magma_law_universe import anonymous_magma_signature, magma_laws_through_order


def _packet(*, presentation_size=None):
    signature = anonymous_magma_signature()
    laws = magma_laws_through_order(1)
    context = build_formal_theory_context(
        signature=signature,
        formulas=tuple(row.axiom for row in laws),
        universe=enumerate_magma_model_universe(signature, carrier_sizes=(2,)),
    )
    return packet_for_exact_context(
        campaign_id="cold-magma-smoke",
        blueprint_id="blueprint:test-cold-magma-smoke",
        eigenquestion="Which anonymous two-law regions have conjunction-only consequences?",
        context=context,
        formula_grammar={"schema": "magma-law-grammar-v1", "max_total_order": 1},
        pack_arity=2,
        navigator_contract=AXIOMPACK_LEAF_WORKBENCH_CONTRACT,
        sealed_context_manifest_digest="sha256:" + "0" * 64,
        query_budget={"countermodels": 3, "lean_consequences": 2},
        stop_rule={"max_finalists": 4, "freeze_before_interpretation": True},
        presentation_size=presentation_size,
    )


def test_exact_campaign_packet_binds_context_and_seals_hidden_manifest():
    packet = _packet()
    assert packet.visible_context_manifest["interpretation_labels_visible"] is False
    assert packet.model_strata[0]["labeled_interpretation_count"] == 16
    assert "sealed" not in packet.visible_context_manifest


def test_campaign_signature_detects_mutation():
    private, public = generate_keypair()
    packet = _packet()
    signed = sign_frontier_campaign(packet, private_key_pem=private, signer_ref="campaign-authority")
    assert verify_frontier_campaign(signed, public_key_pem=public, expected_signer_ref="campaign-authority")
    tampered = replace(signed, packet=replace(packet, pack_arity=1))
    assert not verify_frontier_campaign(tampered, public_key_pem=public, expected_signer_ref="campaign-authority")


def test_campaign_packet_binds_full_reviewed_blueprint():
    private, _public = generate_keypair()
    packet = _packet()
    campaign = sign_frontier_campaign(
        packet,
        private_key_pem=private,
        signer_ref="campaign-authority",
    ).to_json()

    validate_campaign_artifact_binding(
        campaign,
        blueprint_id=packet.blueprint_id,
        context_hash=packet.visible_context_manifest["context_hash"],
        expected_packet_digest=packet.digest,
    )
    with pytest.raises(ValueError, match="reviewed blueprint"):
        validate_campaign_artifact_binding(
            campaign,
            blueprint_id="blueprint:drifted",
            context_hash=packet.visible_context_manifest["context_hash"],
        )


def test_exact_campaign_packet_signs_presentation_size_constraint():
    packet = _packet(presentation_size={"minimum": 2, "maximum": 2})
    assert packet.navigator_contract["presentation_size"] == {
        "minimum": 2,
        "maximum": 2,
    }
    with pytest.raises(ValueError, match="violates pack_arity"):
        _packet(presentation_size={"minimum": 2, "maximum": 3})
