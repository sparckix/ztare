import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

universe u

theorem selected_compactness_source_of_family_compactness_source_gp216_candidate4
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (family_compactness_source :
      LeraySelfTaxCompactnessProvenanceMeasureValuedProfilePriceStreamFamilySource
        source.stream_of_block)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock H n)) :
    GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource
      H n source := by
  apply
    GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource.ofFamilyCompactnessSource
  · exact family_compactness_source
  · exact branch_is_global

end ZtareProofs.NS
