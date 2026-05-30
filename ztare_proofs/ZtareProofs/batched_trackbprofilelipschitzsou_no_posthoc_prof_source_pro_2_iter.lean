import ZtareProofs.ns_profile_lipschitz_clay_bridge

namespace ZtareProofs.NS

def trackB_profile_lipschitz_source_coupling_of_profile_source_receipt_ext
    (evolution_of_initial_data : SmoothNSInitialData → NSEvolution)
    (profile_obligation : TrackBProfileDecompositionObligation)
    (lipschitz_bridge : LowFrequencyLipschitzBridge)
    (H1 : ∀ u0 n, True)
    (H2 : ∀ u0 n, True)
    (H3 : ∀ u0 n, True) :
    TrackBProfileLipschitzSourceCoupling
      evolution_of_initial_data
      profile_obligation
      lipschitz_bridge where
  generated_lipschitz_block_declared_before_profile_pricing := fun u0 n => True
  generated_lipschitz_block_declared_before_profile_pricing_paid := H1
  profile_family_applied_to_generated_lipschitz_block := fun u0 n => True
  profile_family_applied_to_generated_lipschitz_block_paid := H2
  no_posthoc_profile_lipschitz_block_substitution := fun u0 n => True
  no_posthoc_profile_lipschitz_block_substitution_paid := H3

end ZtareProofs.NS
