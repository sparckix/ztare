import ZtareProofs.ns_gp216_bridge_composition_receipt
import ZtareProofs.ns_low_high_lipschitz_reserve_adapter

namespace ZtareProofs.NS

theorem GP216BridgeCompositionReceipt.phaseLatencyConcreteFourierSymbol_bound_refine
    (R : GP216BridgeCompositionReceipt) :
    ∀ n : ℕ, R.phaseLatencyConcreteFourierSymbol.requiredLowLipschitz n ≤
    (trackBGeneratedLowFrequencyLipschitzLedger R.profileLipschitzObligation R.profileLipschitzInitialData).lipschitzCost n := by
  intro n
  refine R.phaseLatencyConcreteFourierSymbol.required_lipschitz_embeds_in_lipschitz_ledger n

end ZtareProofs.NS
