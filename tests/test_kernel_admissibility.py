from ztare.common.kernel_admissibility import (
    admissibility_payload_for_receipt,
    validate_kernel_change_admissibility,
)


def test_provenance_change_is_admissible_when_seed_bytes_are_snapshotted():
    receipt = admissibility_payload_for_receipt(
        change_class="provenance",
        math_anchors=["content_addressed_provenance", "raw_gate_authority"],
        raw_evidence_refs=["workspace/level2_seed.json"],
        verification_refs=["arc3_level_transfer_probe", "replay_consistency_gate"],
        content_addressed_refs=["workspace/level_boundary_seeds/<sha>.json"],
    )

    result = validate_kernel_change_admissibility(receipt)

    assert result.passed is True
    assert result.failures == ()


def test_quotient_change_is_admissible_when_raw_witness_projection_is_kept():
    receipt = admissibility_payload_for_receipt(
        change_class="quotient_compression",
        math_anchors=["finite_quotient", "mdl", "raw_gate_authority"],
        raw_evidence_refs=["raw/episodes/episode_001.jsonl"],
        verification_refs=["replay_consistency_gate", "holdout_rollout_exact"],
        quotient_or_abstraction="duplicate residual signature -> counted residual class",
        raw_witness_projection=["first_t", "t_values", "cells"],
    )

    result = validate_kernel_change_admissibility(receipt)

    assert result.passed is True
    assert result.failures == ()


def test_substrate_specific_rule_or_gate_bypass_is_not_admissible():
    receipt = admissibility_payload_for_receipt(
        change_class="quotient_compression",
        math_anchors=["finite_quotient"],
        raw_evidence_refs=["raw/episodes/episode_001.jsonl"],
        verification_refs=["unit test only"],
        quotient_or_abstraction="row 61 resource-bar special case",
        raw_witness_projection=["row 61"],
    )
    receipt["introduces_substrate_specific_rule"] = True
    receipt["candidate_promotion_authority"] = True

    result = validate_kernel_change_admissibility(receipt)

    assert result.passed is False
    assert "substrate_specific_rule_not_excluded" in result.failures
    assert "candidate_promotion_authority_not_false" in result.failures


def test_quotient_without_raw_projection_is_not_admissible():
    receipt = admissibility_payload_for_receipt(
        change_class="quotient_compression",
        math_anchors=["finite_quotient"],
        raw_evidence_refs=["raw/episodes/episode_001.jsonl"],
        verification_refs=["replay_consistency_gate"],
        quotient_or_abstraction="residual signature quotient",
    )

    result = validate_kernel_change_admissibility(receipt)

    assert result.passed is False
    assert "missing_raw_witness_projection" in result.failures
