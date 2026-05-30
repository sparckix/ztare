import ZtareProofs.ns_gp216_bridge_composition_receipt
import ZtareProofs.ns_profile_lsc_self_tax_obligation

namespace ZtareProofs.NS

theorem no_generated_branch_self_tax_threshold_guard_mismatch
    (R : GP216BridgeCompositionReceipt)
    (F : BranchSelfTaxThresholdCoordinateGuardFalsifier
      (GP216GeneratedProfileLipschitzBranchBlock R.continuationSource.handoff R.profileLipschitzBranchIndex)
      R.selfTaxStream
      R.generatedBranchSelfTaxThresholdCoordinateIdentities) :
    False :=
  no_branch_self_tax_threshold_coordinate_guard_falsifier
    (GP216GeneratedProfileLipschitzBranchBlock R.continuationSource.handoff R.profileLipschitzBranchIndex)
    R.selfTaxStream
    R.generatedBranchSelfTaxThresholdCoordinateIdentities
    F

end ZtareProofs.NS
