import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

theorem gp216GeneratedBranchSelfTaxThresholdCoordinateSource_of_bridge_composition_receipt
    (R : GP216BridgeCompositionReceipt) :
    BranchSelfTaxThresholdCoordinateIdentities
      (GP216GeneratedProfileLipschitzBranchBlock
        R.continuationSource.handoff
        R.profileLipschitzBranchIndex)
      R.selfTaxStream := by
  exact
    GP216BridgeCompositionReceipt.generatedBranchSelfTaxThresholdCoordinateIdentities R

end ZtareProofs.NS
