import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

universe u

theorem selected_compactness_source_of_family_compactness_source_gp216_candidate3
    {τ : ContinuumLPProfileTopology.{u}}
    {H : TrackBContinuationHandoffReceipt}
    {n : ℕ}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    (family_compactness_source :
      LeraySelfTaxCompactnessProvenanceMeasureValuedProfilePriceStreamFamilySource
        source.stream_of_block)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock H n)) :
    GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource
      H n source := by
  let selected_compactness_source :
      GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource
        H n source :=
    GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource.ofFamilyCompactnessSource
      H n source family_compactness_source branch_is_global
  exact selected_compactness_source

end ZtareProofs.NS
