import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

theorem lowHighReservePDESource_satisfied
    (R : GP216BridgeCompositionReceipt) :
    LowHighLipschitzReservePDEObligationSatisfied R.lowHighReservePDESource.obligation :=
  GP216LowHighReservePDESourceBundle.satisfied R.lowHighReservePDESource

end ZtareProofs.NS
