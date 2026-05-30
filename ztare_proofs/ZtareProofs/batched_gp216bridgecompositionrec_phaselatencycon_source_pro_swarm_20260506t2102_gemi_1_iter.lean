import ZtareProofs.ZtareProofs.ns_gp216_bridge_composition_receipt
import ZtareProofs.ZtareProofs.ns_low_high_lipschitz_reserve_adapter

namespace ZtareProofs.NS

theorem phase_latency_concrete_fourier_symbol_embeds_in_lipschitz_ledger
    (R : GP216BridgeCompositionReceipt)
    (n : ℕ) :
    R.phaseLatencyConcreteFourierSymbol.requiredLowLipschitz n ≤ 
      (trackBGeneratedLowFrequencyLipschitzLedger R.profileLipschitzObligation 
        R.profileLipschitzInitialData).lipschitzCost n := by
  exact R.phaseLatencyConcreteFourierSymbol.required_lipschitz_embeds_in_lipschitz_ledger n

end ZtareProofs.NS
