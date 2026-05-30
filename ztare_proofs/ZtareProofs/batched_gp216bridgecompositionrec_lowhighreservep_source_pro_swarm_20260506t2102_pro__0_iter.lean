import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

theorem lowHighReservePDESource_le_GP216BridgeCompositionReceipt_continuationSource
    (s : GP216BridgeCompositionReceipt) : s.lowHighReservePDESource ≤ s.continuationSource := by
  exact s.continuationSource.handoff

end ZtareProofs.NS
