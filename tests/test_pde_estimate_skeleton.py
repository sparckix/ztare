from ztare.research_director.pde_estimate_skeleton import (
    generate_estimate_skeletons,
)


def test_coarea_collar_skeleton_names_owner_prefix_receipts() -> None:
    skeletons = generate_estimate_skeletons(
        target="AngularCoareaCollarSelectionSource",
        field="coareaCharge_le_totalInvoice",
        gap_type="AUXILIARY",
    )

    coarea = next(item for item in skeletons if item["id"] == "coarea_threshold_charge")
    assert "same_owner_prefix_charge" in coarea["required_receipts"]
    assert "bounded_projection_multiplicity" in coarea["required_receipts"]
    assert coarea["hostile_packet"]["name"] == "good_threshold_bad_owner_prefix"


def test_cutoff_boundary_skeleton_demands_separated_channels() -> None:
    skeletons = generate_estimate_skeletons(
        target="AngularConeCutoffBoundaryInvoicePaymentSource",
        field="angularBoundaryInvoice_le_totalInvoice",
        gap_type="COERCIVITY",
    )

    cutoff = next(item for item in skeletons if item["id"] == "cutoff_commutator_invoice")
    assert "typed_spend_channels" in cutoff["required_receipts"]
    assert "no_post_projection_payment" in cutoff["required_receipts"]
    assert "production + pressure_reserve" in cutoff["target_inequality"]
