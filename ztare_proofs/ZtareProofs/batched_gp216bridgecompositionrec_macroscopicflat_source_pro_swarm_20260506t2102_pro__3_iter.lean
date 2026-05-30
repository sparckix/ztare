import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

def macroscopicFlatTorusClockSource_le_GP216BridgeCompositionReceipt_bundle
    {P : PhaseLatencyLipschitzReserveBridge}
    (M : MacroscopicFlatTorusClockSource P) :
    GP216FlatTorusPhaseCapacitySourceBundle P :=
  GP216FlatTorusPhaseCapacitySourceBundle.ofMacroscopicClockSource M

end ZtareProofs.NS
