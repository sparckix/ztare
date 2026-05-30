import ZtareProofs.ns_profile_lsc_self_tax_obligation

namespace ZtareProofs.NS

universe u

theorem no_global_survivor_of_projected_threshold_coordinate_receipt_of_global
    {τ : ContinuumLPProfileTopology.{u}}
    (all_output_source_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ContinuumAllOutputLPBonySource τ)
    (component_source_of_global :
      ∀ B : FullLedgerBlock,
        (hglobal : IsGlobalTrackBBlock B) →
          LeraySelfTaxContinuumComponentLimitPassageSource
            (all_output_source_of_global B hglobal))
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        BranchSelfTaxThresholdCoordinateIdentities
          B
          (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
            (all_output_source_of_global B hglobal)
            ((component_source_of_global B hglobal).split)))
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (R : QuarticSurvivalAmplitudeProjectionReceipt B) :
    FullLedgerNoSurvivor B := by
  exact
    no_global_survivor_of_continuum_all_output_self_tax_source
      B
      (all_output_source_of_global B hglobal)
      (component_source_of_global B hglobal)
      (threshold_coordinate_receipt_of_global B hglobal)
      R

end ZtareProofs.NS
