import ZtareProofs.ns_gp216_bridge_composition_receipt
import ZtareProofs.ns_profile_lsc_self_tax_obligation

namespace ZtareProofs.NS

theorem gp216_generated_branch_self_tax_limit_price_bound
    (R : GP216BridgeCompositionReceipt)
    (habove : sharpTarget < (GP216GeneratedProfileLipschitzBranchBlock R.continuationSource.handoff R.profileLipschitzBranchIndex).gamma) :
    R.selfTaxStream.selfTaxLimitPrice =
      (GP216GeneratedProfileLipschitzBranchBlock R.continuationSource.handoff R.profileLipschitzBranchIndex).selfTax * (Real.sqrt (sharpTarget / (GP216GeneratedProfileLipschitzBranchBlock R.continuationSource.handoff R.profileLipschitzBranchIndex).gamma)) ^ (4 : Nat) :=
  branch_self_tax_limit_price_eq_root_component_of_threshold_coordinate_identities
    (GP216GeneratedProfileLipschitzBranchBlock R.continuationSource.handoff R.profileLipschitzBranchIndex)
    R.selfTaxStream
    R.generatedBranchSelfTaxThresholdCoordinateIdentities
    habove

end ZtareProofs.NS
