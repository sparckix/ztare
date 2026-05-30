import ZtareProofs.ns_profile_lsc_self_tax_obligation

namespace ZtareProofs.NS

universe u

theorem exists_threshold_coordinate_receipt_of_global_from_projected_sources
    {τ : ContinuumLPProfileTopology.{u}}
    (default_stream : LeraySelfTaxProfilePriceStream)
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
    (hglobal : IsGlobalTrackBBlock B) :
    ∃ source : LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ,
      BranchSelfTaxThresholdCoordinateIdentities B (source.stream_of_block B) := by
  let source : LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ :=
    leray_self_tax_continuum_all_output_stream_family_source_of_projected_sources
      default_stream
      all_output_source_of_global
      component_source_of_global
      threshold_coordinate_receipt_of_global
  refine ⟨source, ?_⟩
  have hmatch :
      leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
          (all_output_source_of_global B hglobal)
          ((component_source_of_global B hglobal).split) =
        source.stream_of_block B :=
    source.projected_stream_matches_block B hglobal
  exact hmatch ▸ threshold_coordinate_receipt_of_global B hglobal

end ZtareProofs.NS
