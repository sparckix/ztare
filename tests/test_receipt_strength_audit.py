from ztare.research_director.receipt_strength_audit import (
    run_receipt_strength_audit,
)


def test_prop_only_no_overlap_is_weak_even_with_numeric_owner_bound() -> None:
    result = run_receipt_strength_audit([
        "jointChannel_le_ownerRootBudget:jointCollarTailChannel <= ownerRootBudget",
        "jointChannelNoOverlapWithExistingCollarReserves:Prop",
        "jointChannelNotDefinedFromPayoff:Prop",
        "jointChannelRefinesOwnerPreimage:Prop",
        "projectedCollarNoReuse:Prop",
    ])

    assert result["passed"] is False
    assert "no_overlap_or_disjointness" in result["weak_receipts"]
    assert "payoff_independence" in result["weak_receipts"]
    assert "owner_root_numeric_bound" not in result["weak_receipts"]


def test_typed_and_numeric_receipts_pass_default_profile() -> None:
    result = run_receipt_strength_audit([
        "jointChannel_le_ownerRootBudget:jointCollarTailChannel <= ownerRootBudget",
        "jointChannelNoOverlapWithExistingCollarReserves:NoOverlapReceipt",
        "jointChannelNotDefinedFromPayoff:PayoffIndependenceReceipt",
        "jointChannelRefinesOwnerPreimage:OwnerPreimageRefinementReceipt",
        "projectedCollarNoReuse:NoReuseReceipt",
    ])

    assert result["passed"] is True
    assert not result["weak_receipts"]
    assert not result["missing_receipts"]


def test_free_text_receipt_is_not_typed_evidence() -> None:
    result = run_receipt_strength_audit([
        "jointChannel_le_ownerRootBudget:jointCollarTailChannel <= ownerRootBudget",
        "jointChannelNoOverlapWithExistingCollarReserves:no overlap by construction",
        "jointChannelNotDefinedFromPayoff:fixed before payoff by construction",
        "jointChannelRefinesOwnerPreimage:OwnerPreimageRefinementReceipt",
        "projectedCollarNoReuse:NoReuseReceipt",
    ])

    assert result["passed"] is False
    assert "no_overlap_or_disjointness" in result["weak_receipts"]
    assert "payoff_independence" in result["weak_receipts"]


def test_proof_of_prop_field_does_not_upgrade_receipt_strength() -> None:
    result = run_receipt_strength_audit([
        "jointChannel_le_ownerRootBudget:jointCollarTailChannel <= ownerRootBudget",
        "jointChannelNoOverlapWithExistingCollarReserves:Prop",
        "jointChannelNoOverlapWithExistingCollarReserves_proof:jointChannelNoOverlapWithExistingCollarReserves",
        "jointChannelNotDefinedFromPayoff:Prop",
        "jointChannelNotDefinedFromPayoff_proof:jointChannelNotDefinedFromPayoff",
        "jointChannelRefinesOwnerPreimage:OwnerPreimageRefinementReceipt",
        "projectedCollarNoReuse:NoReuseReceipt",
    ])

    assert result["passed"] is False
    assert "no_overlap_or_disjointness" in result["weak_receipts"]
    assert "payoff_independence" in result["weak_receipts"]

