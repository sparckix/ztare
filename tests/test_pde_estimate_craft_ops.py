from src.ztare.research_director.pde_estimate_craft_ops import (
    CROSS_VOCABULARY_MAPPING,
    PORTABLE_RECEIPT_OVERLAP_MAP,
    get,
    portable_receipt_candidates,
    render_vocabulary_summary,
)
from src.ztare.research_director.structural_fingerprint import (
    build_structural_fingerprint,
)


def test_distribution_tail_upgrade_op_is_registered() -> None:
    op = get("pec_h")
    assert op is not None
    assert op.name == "Distribution / Tail Upgrade"
    assert op.tier == "proto"
    assert "weak-L^q" in op.structural_mechanism
    assert "pec_e" in (op.boundary_collapse_risk or "")


def test_distribution_tail_upgrade_has_cross_vocab_boundary() -> None:
    mapping = CROSS_VOCABULARY_MAPPING["pec_h"]
    assert mapping["v5_neighbor"].startswith("broad_02")
    assert "distribution-tail" in mapping["boundary"]


def test_phase_space_packet_ownership_op_is_registered() -> None:
    op = get("pec_k")
    assert op is not None
    assert op.name == "Phase-Space Packet Ownership Receipt"
    assert "owner preimages" in op.structural_mechanism
    assert "full output-scale packet" in op.structural_mechanism
    assert op.gate_mechanization == "src/ztare/gates/owner_preimage_prefix_gate.py"
    assert "pec_j" in (op.boundary_collapse_risk or "")


def test_phase_space_packet_ownership_has_cross_vocab_boundary() -> None:
    mapping = CROSS_VOCABULARY_MAPPING["pec_k"]
    assert mapping["v5_neighbor"].startswith("core_04")
    assert "owner preimages" in mapping["boundary"]


def test_symbol_cancellation_coercivity_audit_op_is_registered() -> None:
    op = get("pec_l")
    assert op is not None
    assert op.name == "Symbol / Cancellation Coercivity Audit"
    assert "signed-to-positive" in op.structural_mechanism
    assert "positive/coercive target" in (op.boundary_collapse_risk or "")


def test_symbol_cancellation_coercivity_has_cross_vocab_boundary() -> None:
    mapping = CROSS_VOCABULARY_MAPPING["pec_l"]
    assert mapping["v5_neighbor"].startswith("core_05")
    assert "signed symbol cancellation" in mapping["boundary"]


def test_render_summary_does_not_bake_stale_counts() -> None:
    text = render_vocabulary_summary()
    assert "pec_h  Distribution / Tail Upgrade" in text
    assert "pec_k  Phase-Space Packet Ownership Receipt" in text
    assert "pec_l  Symbol / Cancellation Coercivity Audit" in text
    assert "6 proto" not in text


def test_structural_fingerprint_routes_tail_language_to_pec_h() -> None:
    fingerprint = build_structural_fingerprint(
        (
            "signed average control must be upgraded into a reverse Holder "
            "tail estimate for a positive part"
        ),
        substrate="generic pde",
    )
    assert not isinstance(fingerprint.pde_ops_or_not_applicable, str)
    ids = {signal.op_id for signal in fingerprint.pde_ops_or_not_applicable}
    assert "pec_h" in ids


def test_structural_fingerprint_routes_owner_preimage_language_to_pec_k() -> None:
    fingerprint = build_structural_fingerprint(
        (
            "selected events require phase-space packet ownership with an "
            "owner map, owner preimage bound, and owned event prefix budget"
        ),
        substrate="generic pde",
    )
    assert not isinstance(fingerprint.pde_ops_or_not_applicable, str)
    ids = {signal.op_id for signal in fingerprint.pde_ops_or_not_applicable}
    assert "pec_k" in ids


def test_structural_fingerprint_routes_factor_reuse_language_to_pec_k() -> None:
    fingerprint = build_structural_fingerprint(
        (
            "a low-high catalyst factor cannot be reused as the owner of many "
            "full output-scale bilinear packets"
        ),
        substrate="generic pde",
    )
    assert not isinstance(fingerprint.pde_ops_or_not_applicable, str)
    ids = {signal.op_id for signal in fingerprint.pde_ops_or_not_applicable}
    assert "pec_k" in ids


def test_structural_fingerprint_routes_null_form_language_to_pec_l() -> None:
    fingerprint = build_structural_fingerprint(
        (
            "a high-high null-form or energy skew cancellation must prove a "
            "signed-to-positive estimate for the positive source square"
        ),
        substrate="generic pde",
    )
    assert not isinstance(fingerprint.pde_ops_or_not_applicable, str)
    ids = {signal.op_id for signal in fingerprint.pde_ops_or_not_applicable}
    assert "pec_l" in ids


def test_portable_receipt_candidates_have_schema_fields_and_overlap_map() -> None:
    candidates = {op.op_id: op for op in portable_receipt_candidates()}
    assert {"pec_a", "pec_b", "pec_e", "cand_g"} <= set(candidates)
    assert "comparison_map" in candidates["pec_a"].portable_receipt_fields
    assert "scope_breaker" in candidates["pec_b"].portable_receipt_fields
    assert "claim_boundary_update" in candidates["pec_e"].portable_receipt_fields
    assert "translation_rule" in candidates["cand_g"].portable_receipt_fields
    assert PORTABLE_RECEIPT_OVERLAP_MAP["pec_a"]["nearest_universal_ops"]
    assert PORTABLE_RECEIPT_OVERLAP_MAP["pec_e"]["overlap_status"] == "boundary_ambiguous"


def test_structural_fingerprint_routes_portable_receipts_outside_pde() -> None:
    fingerprint = build_structural_fingerprint(
        (
            "A general research residual needs an auxiliary object and a "
            "failure witness, but the nearest confuser is a coordinate "
            "reformulation in the same formal system."
        ),
        substrate="generic non-pde research",
    )

    assert fingerprint.pde_ops_or_not_applicable == "not_applicable"
    ids = {signal.op_id for signal in fingerprint.portable_receipt_ops}
    assert {"pec_a", "pec_e", "cand_g"} <= ids
    pec_a = next(
        signal for signal in fingerprint.portable_receipt_ops
        if signal.op_id == "pec_a"
    )
    assert pec_a.family == "gp219_portable_receipt_candidate"
    assert pec_a.nearest_universal_ops
    assert "comparison_map" in pec_a.required_schema_fields
