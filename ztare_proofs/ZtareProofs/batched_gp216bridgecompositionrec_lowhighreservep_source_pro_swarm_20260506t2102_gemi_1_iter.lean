import ZtareProofs.ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

theorem lowHighReservePDESource_obligation_satisfaction_at_continuation
    (R : GP216BridgeCompositionReceipt) :
    R.lowHighReservePDESource.satisfied.obligation = R.lowHighReservePDESource.obligation := by
  apply Eq.symm
  exact GP216LowHighReservePDESourceBundle.satisfied R.lowHighReservePDESource ▸ rfl

end ZtareProofs.NS
