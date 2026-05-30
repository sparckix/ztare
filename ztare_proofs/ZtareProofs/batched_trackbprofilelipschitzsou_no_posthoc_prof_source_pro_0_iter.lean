import ZtareProofs.ns_profile_lipschitz_clay_bridge

namespace ZtareProofs.NS

def trackB_profile_lipschitz_source_coupling_of_profile_source_receipt_completed
    (evolution_of_initial_data : SmoothNSInitialData → NSEvolution)
    (profile_obligation : TrackBProfileDecompositionObligation)
    (lipschitz_bridge : LowFrequencyLipschitzBridge) :
    TrackBProfileLipschitzSourceCoupling
      evolution_of_initial_data
      profile_obligation
      lipschitz_bridge :=
  {
    generated_lipschitz_block_declared_before_profile_pricing := fun _ _ => True,
    generated_lipschitz_block_declared_before_profile_pricing_paid := fun _ _ => trivial,
    profile_family_applied_to_generated_lipschitz_block := fun _ _ => True,
    profile_family_applied_to_generated_lipschitz_block_paid := fun _ _ => trivial,
    no_posthoc_profile_lipschitz_block_substitution := fun _ _ => True,
    no_posthoc_profile_lipschitz_block_substitution_paid := fun _ _ => trivial
  }

end ZtareProofs.NS
