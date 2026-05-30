import ZtareProofs.ZtareProofs.ns_gp216_bridge_composition_receipt
import ZtareProofs.ZtareProofs.ns_low_high_lipschitz_reserve_adapter
import ZtareProofs.ZtareProofs.ns_low_high_profile_lipschitz_composition
import ZtareProofs.ZtareProofs.ns_phase_latency_clay_bridge

namespace ZtareProofs.NS

theorem GP216BridgeCompositionReceipt_symbol_escape_falsifier_alt
    (R : GP216BridgeCompositionReceipt) :
    ¬ GP216ConcreteFourierLatencySymbolEscape R := by
  intro h
  exact gp216_no_concrete_fourier_latency_symbol_escape R h

end ZtareProofs.NS
