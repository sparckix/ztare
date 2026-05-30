import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

universe u

theorem selected_compactness_source_of_family_compactness_source_gp216_candidate2
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock H n))
    (family_compactness_source :
      LeraySelfTaxCompactnessProvenanceMeasureValuedProfilePriceStreamFamilySource
        source.stream_of_block) :
    GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource
      H n source := by
  refine
    GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource.ofFamilyCompactnessSource
      H n source ?_ ?_
  · exact family_compactness_source
  · exact branch_is_global

end ZtareProofs.NS
