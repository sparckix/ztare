import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs
namespace NS

universe u

def GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource_from_measure_valued_compactness_provenance
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock H n))
    (measure_valued_output_limit :
      LeraySelfTaxMeasureValuedOutputLimitSource
        (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
          (source.all_output_source_of_global
            (GP216GeneratedProfileLipschitzBranchBlock H n)
            branch_is_global)
          ((source.component_source_of_global
            (GP216GeneratedProfileLipschitzBranchBlock H n)
            branch_is_global).split)))
    (compactness_provenance :
      LeraySelfTaxMeasureValuedOutputCompactnessProvenance
        (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
          (source.all_output_source_of_global
            (GP216GeneratedProfileLipschitzBranchBlock H n)
            branch_is_global)
          ((source.component_source_of_global
            (GP216GeneratedProfileLipschitzBranchBlock H n)
            branch_is_global).split))
        measure_valued_output_limit) :
    GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource
      H n source :=
{ branch_is_global := branch_is_global
  projected_compactness_measure_valued_source :=
    { measure_valued_output_limit := measure_valued_output_limit
      compactness_provenance := compactness_provenance } }

theorem GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource_from_measure_valued_compactness_provenance_projected
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock H n))
    (measure_valued_output_limit :
      LeraySelfTaxMeasureValuedOutputLimitSource
        (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
          (source.all_output_source_of_global
            (GP216GeneratedProfileLipschitzBranchBlock H n)
            branch_is_global)
          ((source.component_source_of_global
            (GP216GeneratedProfileLipschitzBranchBlock H n)
            branch_is_global).split)))
    (compactness_provenance :
      LeraySelfTaxMeasureValuedOutputCompactnessProvenance
        (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
          (source.all_output_source_of_global
            (GP216GeneratedProfileLipschitzBranchBlock H n)
            branch_is_global)
          ((source.component_source_of_global
            (GP216GeneratedProfileLipschitzBranchBlock H n)
            branch_is_global).split))
        measure_valued_output_limit) :
    (GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource_from_measure_valued_compactness_provenance
      H n source branch_is_global
      measure_valued_output_limit compactness_provenance).projected_compactness_measure_valued_source =
      { measure_valued_output_limit := measure_valued_output_limit
        compactness_provenance := compactness_provenance } := by
  rfl

end NS
end ZtareProofs
