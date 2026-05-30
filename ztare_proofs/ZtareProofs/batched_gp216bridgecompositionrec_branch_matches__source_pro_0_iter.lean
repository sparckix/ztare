import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

theorem branch_matches_profile_lipschitz_generated_block_le_continuationSource_handoff
    (R : GP216BridgeCompositionReceipt) :
    R.branchBlock = (trackBGeneratedLowFrequencyLipschitzLedger
      R.continuationSource.handoff.profile_lipschitz
      R.continuationSource.handoff.initialData).block
      R.profileLipschitzBranchIndex := by
  exact R.branch_matches_profile_lipschitz_generated_block

end ZtareProofs.NS
