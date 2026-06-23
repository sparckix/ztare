from ztare.gates.owner_preimage_prefix_gate import (
    run_owner_preimage_prefix_gate,
)


def test_owner_preimage_gate_flags_pointwise_only_receipt() -> None:
    result = run_owner_preimage_prefix_gate({
        "owner_preimage_receipts": [{
            "name": "pointwise_only",
            "owner_map": "ownerOfEvent",
            "pointwise_payment": "eventPay e <= atomCharge (ownerOfEvent e)",
            "finite_atom_budget": "prefix atomCharge <= B",
            "finite_owner_palette": "ownerOfEvent e < 2",
        }],
    })

    assert result["passed"] is True
    assert result["n_complete_receipts"] == 0
    assert any(
        v["type"] == "owner_preimage_receipt_incomplete"
        and "owner_preimage_prefix_inequality" in v["missing_fields"]
        for v in result["violations"]
    )


def test_owner_preimage_gate_accepts_scaled_prefix_receipt() -> None:
    result = run_owner_preimage_prefix_gate({
        "owner_preimage_receipts": [{
            "name": "scaled_prefix",
            "owner_map": "ownerOfEvent",
            "pre_payoff_timing": "owner fixed before payoff",
            "full_output_scale_owner": "owner is full output-scale packet",
            "pointwise_payment": "routeActiveTail e <= scaledAtomCharge owner",
            "finite_atom_budget": "prefix scaledAtomCharge <= scaledBudget",
            "multiplicity_bound": "M",
            "owner_preimage_prefix_inequality": (
                "prefix routeActiveTail N <= "
                "M * prefix scaledAtomCharge (activeOwnerAtomBound N)"
            ),
        }],
    })

    assert result["passed"] is True
    assert result["n_complete_receipts"] == 1
    assert result["violations"] == []


def test_owner_preimage_gate_blocks_when_enforced() -> None:
    result = run_owner_preimage_prefix_gate(
        {
            "owner_preimage_receipts": [{
                "name": "palette_only",
                "owner_map": "ownerOfEvent",
                "finite_owner_palette": "two owners",
            }],
        },
        enforce_block=True,
    )

    assert result["passed"] is False
    assert any(v["severity"] == "blocking" for v in result["violations"])


def test_owner_preimage_gate_treats_missing_strings_as_absent() -> None:
    result = run_owner_preimage_prefix_gate({
        "owner_preimage_receipts": [{
            "name": "quadratic_size_sum_only",
            "owner_map": "missing: no coareaOwner map",
            "pre_payoff_timing": "quadratic cap fixed before payoff",
            "full_output_scale_owner": "missing: threshold owner not output-scale owner",
            "pointwise_payment": "missing: no pointwise owner payment",
            "finite_atom_budget": "finite quadratic cap only",
            "multiplicity_bound": "missing: no preimage multiplicity bound",
            "owner_preimage_prefix_inequality": "missing: no prefix inequality",
        }],
    })

    assert result["passed"] is True
    assert result["n_complete_receipts"] == 0
    violation = next(
        v for v in result["violations"]
        if v["type"] == "owner_preimage_receipt_incomplete"
    )
    assert "owner_map" in violation["missing_fields"]
    assert "owner_preimage_prefix_inequality" in violation["missing_fields"]

