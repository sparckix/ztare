import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

def macroscopicFlatTorusClockSource_le_GP216BridgeCompositionReceipt_phaseCapacityHandoff
    {P : PhaseLatencyLipschitzReserveBridge}
    (M : MacroscopicFlatTorusClockSource P) :
    GP216FlatTorusPhaseCapacityHandoff P M.killingMode M.lowHighPDE :=
  M.toPhaseCapacityHandoff

end ZtareProofs.NS
