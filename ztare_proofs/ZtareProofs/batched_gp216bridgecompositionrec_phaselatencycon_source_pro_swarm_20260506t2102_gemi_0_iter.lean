import ZtareProofs.ZtareProofs.ns_gp216_bridge_composition_receipt
import ZtareProofs.ZtareProofs.ns_low_high_lipschitz_reserve_adapter

namespace ZtareProofs.NS

theorem phase_latency_concrete_fourier_symbol_le_event_recurrence_budget
    (R : GP216BridgeCompositionReceipt) :
    R.phaseLatencyConcreteFourierSymbol.symbolConstant ≤ 
      R.eventRecurrenceSource.ledger.budget_constant := by
  apply le_of_not_gt
  intro hcontra
  exact gp216_no_concrete_fourier_latency_symbol_escape R 
    ⟨R.phaseLatencyConcreteFourierSymbol, 
     fun B => ⟨0, by exact hcontra⟩⟩

end ZtareProofs.NS
