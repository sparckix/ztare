import ZtareProofs.ns_gp216_bridge_composition_receipt
import ZtareProofs.ns_low_high_lipschitz_reserve_adapter
import ZtareProofs.ns_phase_latency_clay_bridge
import ZtareProofs.ns_low_high_profile_lipschitz_composition

namespace ZtareProofs.NS

/-- Extracts the target concrete Fourier latency symbol from a hypothetical falsifier escape. -/
def concreteFourierLatencySymbolReceipt_of_falsifier_escape
    (O : TrackBProfileLipschitzControlObligation)
    (u0 : SmoothNSInitialData)
    (escape : ∃ S : ConcreteFourierLatencySymbolReceipt (trackBGeneratedLowFrequencyLipschitzLedger O u0), ∀ B, ∃ n, B < S.shellOverIndex n) :
    ConcreteFourierLatencySymbolReceipt (trackBGeneratedLowFrequencyLipschitzLedger O u0) :=
  escape.choose

end ZtareProofs.NS
