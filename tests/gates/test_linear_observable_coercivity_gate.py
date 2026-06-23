from ztare.gates.linear_observable_coercivity_gate import run_gate


def test_rejects_rank_one_observable_for_five_dimensional_target_without_receipt():
    result = run_gate(
        target_dimension=5,
        observable_rank=1,
        kernel_witness_present=True,
        dimensionally_compatible=True,
        labels={"target": "tracefree_tensor", "observable": "scalar_sample"},
    )

    assert result["passed"] is False
    assert result["rank_deficient"] is True
    assert result["violations"][0]["kind"] == "observable_rank_defect"


def test_full_rank_still_requires_reconstruction_or_coercivity_receipt():
    result = run_gate(target_dimension=5, observable_rank=5)

    assert result["passed"] is False
    assert result["violations"][0]["kind"] == "missing_reconstruction_or_coercivity_receipt"


def test_accepts_full_rank_with_reconstruction_receipt():
    result = run_gate(
        target_dimension=5,
        observable_rank=5,
        full_reconstruction_receipt=True,
    )

    assert result["passed"] is True
    assert result["receipts"]["full_reconstruction_receipt"] is True


def test_accepts_rank_defect_only_when_quotient_target_is_receipted():
    result = run_gate(
        target_dimension=5,
        observable_rank=1,
        kernel_quotient_dimension=1,
        kernel_quotient_receipt=True,
    )

    assert result["passed"] is True
    assert result["warnings"][0]["kind"] == "quotient_target_only"


def test_rejects_contradictory_full_receipt_under_rank_defect():
    result = run_gate(
        target_dimension=5,
        observable_rank=1,
        coercivity_receipt=True,
    )

    assert result["passed"] is False
    assert {v["kind"] for v in result["violations"]} >= {
        "contradictory_rank_receipt",
        "observable_rank_defect",
    }
