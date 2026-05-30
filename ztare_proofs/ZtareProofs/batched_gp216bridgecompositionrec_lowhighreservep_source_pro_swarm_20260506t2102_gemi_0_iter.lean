import ZtareProofs.ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

theorem lowHighReservePDESource_continuation_handoff_consistency
    (R : GP216BridgeCompositionReceipt) :
    R.lowHighReservePDESource.energyBudgetPDEHandoff.handoff = R.continuationHandoff := by
  refine (congr_arg GP216ContinuationSourceBundle.handoff _).symm
  exact R.continuationSource.to_handoff_consistent

end ZtareProofs.NS
