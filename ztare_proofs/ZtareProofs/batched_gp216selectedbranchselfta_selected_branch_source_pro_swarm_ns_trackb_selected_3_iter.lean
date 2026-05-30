import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

theorem selected_branch_stream_matches_self_tax_output_if_fixed_atoms_falsifier
    {H : TrackBContinuationHandoffReceipt}
    {n : ℕ}
    {selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle}
    {S : LeraySelfTaxProfilePriceStream}
    {E : EventRecurrencePriceLedger}
    (B : GP216ContinuumAllOutputSourceBundle S E) :
    GP216ContinuumAllOutputFixedAtomsProvenanceFalsifier B →
      stream_of_block (GP216GeneratedProfileLipschitzBranchBlock H n) =
        selfTaxOutputSource.stream := by
  intro F
  exfalso
  exact no_gp216_continuum_all_output_fixed_atoms_provenance_falsifier B F

end ZtareProofs.NS
