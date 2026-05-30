import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

universe u

theorem gp216_branchSelfTaxThresholdCoordinateIdentities_source_of_continuum_phase5fb_sigma_observable_alignment_at_generated_branch
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (profile_stream_source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (phase5fb_alignment :
      ContinuumPhase5FBSigmaObservableAlignmentSource
        H.profile_lipschitz.profile_bundle.profile_family_of_block
        profile_stream_source
        H.profile_lipschitz.lipschitz_bridge)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock H n))
    (branch_stream_matches_self_tax_output :
      profile_stream_source.stream_of_block
        (GP216GeneratedProfileLipschitzBranchBlock H n) =
          selfTaxOutputSource.stream) :
    BranchSelfTaxThresholdCoordinateIdentities
      (GP216GeneratedProfileLipschitzBranchBlock H n)
      selfTaxOutputSource.stream := by
  refine
    branch_threshold_coordinates_of_continuum_phase5fb_sigma_observable_alignment_at_generated_branch
      H
      n
      selfTaxOutputSource
      profile_stream_source
      phase5fb_alignment
      branch_is_global
      branch_stream_matches_self_tax_output

end ZtareProofs.NS
