import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

theorem gp216_generated_branch_threshold_coordinate_receipt_source_witness_refine
    (R : GP216BridgeCompositionReceipt) :
    BranchSelfTaxThresholdCoordinateIdentities
      (GP216GeneratedProfileLipschitzBranchBlock
        R.continuationSource.handoff
        R.profileLipschitzBranchIndex)
      R.selfTaxStream := by
  refine GP216BridgeCompositionReceipt.generatedBranchSelfTaxThresholdCoordinateIdentities R

end ZtareProofs.NS
