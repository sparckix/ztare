import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

theorem macroscopicFlatTorusClockSource_capacity_zero
    (R : GP216BridgeCompositionReceipt) :
    R.phaseLatencyLipschitzReserve.phase.reach 0 * R.phaseLatencyLipschitzReserve.phase.kNorm 0 ≤
      R.phaseLatencyLipschitzReserve.phase.gramianConstant := by
  exact gp216_flat_torus_feeds_phase_latency_capacity_of_macroscopic_clock_source R 0

end ZtareProofs.NS
