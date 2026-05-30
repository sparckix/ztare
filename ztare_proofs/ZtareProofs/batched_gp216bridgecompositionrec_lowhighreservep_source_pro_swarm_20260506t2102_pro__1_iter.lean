import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

theorem GP216BridgeCompositionReceipt.lowHighReservePDESource_obligation_satisfied
    (R : GP216BridgeCompositionReceipt) :
    LowHighLipschitzReservePDEObligationSatisfied R.lowHighReservePDESource.obligation :=
  R.lowHighReservePDESource.satisfied

end ZtareProofs.NS
