import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

theorem macroscopicFlatTorusClockSource_capacity_bound
    (R : GP216BridgeCompositionReceipt)
    (j : ℕ) :
    R.phaseLatencyLipschitzReserve.phase.reach j * R.phaseLatencyLipschitzReserve.phase.kNorm j ≤
      R.phaseLatencyLipschitzReserve.phase.gramianConstant := by
  exact gp216_flat_torus_feeds_phase_latency_capacity_of_macroscopic_clock_source R j

end ZtareProofs.NS
