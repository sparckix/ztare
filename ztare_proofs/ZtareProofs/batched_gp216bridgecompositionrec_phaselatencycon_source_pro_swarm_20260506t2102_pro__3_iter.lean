import ZtareProofs.ZtareProofs.ns_gp216_bridge_composition_receipt
import ZtareProofs.ZtareProofs.ns_low_high_lipschitz_reserve_adapter
import ZtareProofs.ZtareProofs.ns_low_high_profile_lipschitz_composition
import ZtareProofs.ZtareProofs.ns_phase_latency_clay_bridge

namespace ZtareProofs.NS

theorem GP216BridgeCompositionReceipt_concreteFourierLatency_unbounded_falsifier_alt
    (R : GP216BridgeCompositionReceipt)
    (S : ConcreteFourierLatencySymbolReceipt
      (trackBGeneratedLowFrequencyLipschitzLedger
        R.profileLipschitzObligation
        R.profileLipschitzInitialData)) :
    ¬ (∀ B : Real, ∃ n : ℕ, B < S.shellOverIndex n) := by
  intro hunbounded
  exact no_concrete_fourier_latency_symbol_escape_under_trackB_profile_closure
    R.profileLipschitzObligation
    R.profileLipschitzInitialData
    S
    hunbounded

end ZtareProofs.NS
