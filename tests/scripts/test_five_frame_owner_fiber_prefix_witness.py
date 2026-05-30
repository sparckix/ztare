from projects.ns_millennium_hunt.scripts.five_frame_owner_fiber_prefix_witness import (
    build_witness,
)


def test_five_frame_tomography_does_not_supply_owner_prefix_budget() -> None:
    witness = build_witness(max_prefix=64, owner_budget=4.0)

    assert witness["first_failure"] is not None
    assert witness["first_failure"]["owner_id"] == 0
    assert witness["final_five_frame_abs_prefix"] > witness["owner_budget"]
    assert "does not create a cofinal owner-preimage budget" in witness["interpretation"]


def test_required_repair_names_owner_fiber_preimage_packing() -> None:
    witness = build_witness(max_prefix=4, owner_budget=100.0)

    assert "owner_invoice_fibers" in witness["required_repair_field"]
    assert "selected_prefix_preimage_packing" in witness["required_repair_field"]
