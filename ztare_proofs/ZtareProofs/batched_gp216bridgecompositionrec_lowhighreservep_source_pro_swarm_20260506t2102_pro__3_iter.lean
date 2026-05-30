import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

theorem no_gp216_low_high_reserve_pde_source_falsifier
    (R : GP216BridgeCompositionReceipt)
    (F : LowHighLipschitzReservePDEObligationFalsifier R.lowHighReservePDESource.obligation) :
    False :=
  F.not_satisfied R.lowHighReservePDESource.satisfied

end ZtareProofs.NS
