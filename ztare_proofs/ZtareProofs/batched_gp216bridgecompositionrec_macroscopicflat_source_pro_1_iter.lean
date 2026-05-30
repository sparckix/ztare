import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

theorem macroscopicFlatTorusClockSource_profile_capacity_bound
    (R : GP216BridgeCompositionReceipt)
    (j : ℕ) :
    R.phaseLatencyProfileReserveSource.phase.reach j * R.phaseLatencyProfileReserveSource.phase.kNorm j ≤
      R.phaseLatencyProfileReserveSource.phase.gramianConstant := by
  exact R.flat_torus_pde_feeds_profile_phase_capacity j

end ZtareProofs.NS
