import ZtareProofs.ns_low_high_lipschitz_reserve_adapter

namespace ZtareProofs.NS

theorem smooth_limit_preserves_cost_and_reserve_of_handoff
    {O : LowHighLipschitzReservePDEObligation}
    {G : LowFrequencyLipschitzLedger}
    {S : LowHighEnergyBudgetShellReserveClosure G}
    (H : LowHighEnergyBudgetShellReservePDEHandoff O G S) :
    O.smooth_limit_preserves_cost_and_reserve :=
  H.smooth_limit_preserves_cost_and_reserve

end ZtareProofs.NS
