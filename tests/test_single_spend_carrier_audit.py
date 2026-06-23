from ztare.research_director.single_spend_carrier_audit import (
    run_single_spend_carrier_audit,
)


def test_free_text_type_does_not_count_as_paid_evidence():
    result = run_single_spend_carrier_audit([
        "sourceSpend:source reserve paid by construction",
        "targetChargeSpend:target charge is separated by prose",
        "reserveSpend:reserve exists because the argument says so",
        "totalBudgetPartition:sourceSpend+targetChargeSpend+reserveSpend≤totalBudget",
        "sameIndexIdentityReceipt:CarrierIdentityReceipt",
    ])

    assert not result["passed"]
    assert "source" in result["free_text_evidence_channels"]
    assert "target_charge" in result["free_text_evidence_channels"]
    assert "source" in result["missing_nonnegative_spend_channels"]


def test_named_receipts_and_inequalities_count_as_structural_evidence():
    result = run_single_spend_carrier_audit([
        "sourceSpend:Real",
        "sourceSpend_nonnegative:0≤sourceSpend",
        "targetChargeSpend:Real",
        "targetChargeSpend_nonnegative:0≤targetChargeSpend",
        "reserveSpend:Real",
        "reserveSpend_nonnegative:0≤reserveSpend",
        "totalBudgetPartition:sourceSpend+targetChargeSpend+reserveSpend≤totalBudget",
        "sameIndexIdentityReceipt:CarrierIdentityReceipt",
        "fixedBeforeAccounting:TimingReceipt",
        "noReuseReceipt:NoReuseReceipt",
    ])

    assert result["passed"]
    assert not result["free_text_evidence_channels"]


def test_bare_timing_field_counts_as_timing_channel() -> None:
    result = run_single_spend_carrier_audit([
        "sourceSpend:Real",
        "sourceSpend_nonnegative:0<=sourceSpend",
        "targetChargeSpend:Real",
        "targetChargeSpend_nonnegative:0<=targetChargeSpend",
        "reserveSpend:Real",
        "reserveSpend_nonnegative:0<=reserveSpend",
        "totalBudgetPartition:sourceSpend+targetChargeSpend+reserveSpend<=totalBudget",
        "sameIndexIdentityReceipt:CarrierIdentityReceipt",
        "timing:TimingReceipt",
        "noReuseReceipt:NoReuseReceipt",
    ])
    assert result["passed"] is True
    assert "timing" not in result["missing_channels"]
