import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

theorem gp216_branchSelfTaxThresholdCoordinateIdentities_source_of_noncircular_mv_scalar_alignment_at_generated_branch
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (source :
      LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource)
    (alignment :
      NoncircularMeasureValuedProfileFamilyScalarAlignmentSource
        H.profile_lipschitz.profile_bundle.profile_family_of_block
        source)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock H n))
    (branch_stream_matches_self_tax_output :
      source.stream_of_block
        (GP216GeneratedProfileLipschitzBranchBlock H n) =
          selfTaxOutputSource.stream) :
    BranchSelfTaxThresholdCoordinateIdentities
      (GP216GeneratedProfileLipschitzBranchBlock H n)
      selfTaxOutputSource.stream := by
  apply branch_threshold_coordinates_of_noncircular_mv_scalar_alignment_at_generated_branch
  exact H
  exact n
  exact selfTaxOutputSource
  exact source
  exact alignment
  exact branch_is_global
  exact branch_stream_matches_self_tax_output

end ZtareProofs.NS
