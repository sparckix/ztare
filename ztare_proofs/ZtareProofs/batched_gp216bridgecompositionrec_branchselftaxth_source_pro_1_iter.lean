import ZtareProofs.ns_gp216_bridge_composition_receipt
import ZtareProofs.ns_profile_lsc_self_tax_obligation

namespace ZtareProofs.NS

theorem gp216_generated_branch_payoff_limit_eq_one
    (R : GP216BridgeCompositionReceipt)
    (habove : sharpTarget < (GP216GeneratedProfileLipschitzBranchBlock R.continuationSource.handoff R.profileLipschitzBranchIndex).gamma) :
    R.selfTaxStream.payoffLimit = 1 :=
  branch_payoff_limit_eq_one_of_threshold_coordinate_identities
    (GP216GeneratedProfileLipschitzBranchBlock R.continuationSource.handoff R.profileLipschitzBranchIndex)
    R.selfTaxStream
    R.generatedBranchSelfTaxThresholdCoordinateIdentities
    habove

end ZtareProofs.NS
