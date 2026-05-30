import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

theorem branch_matches_profile_lipschitz_generated_block_eq_handoff_block
    (R : GP216BridgeCompositionReceipt) :
    (trackBGeneratedLowFrequencyLipschitzLedger
      R.continuationSource.handoff.profile_lipschitz
      R.continuationSource.handoff.initialData).block
      R.profileLipschitzBranchIndex = R.branchBlock := by
  exact R.branch_matches_profile_lipschitz_generated_block.symm

end ZtareProofs.NS
