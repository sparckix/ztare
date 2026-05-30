import ZtareProofs.ns_low_high_lipschitz_reserve_adapter

namespace ZtareProofs.NS

theorem smooth_limit_preserves_cost_and_reserve_from_satisfaction
    (O : LowHighLipschitzReservePDEObligation)
    (h : LowHighLipschitzReservePDEObligationSatisfied O) :
    O.smooth_limit_preserves_cost_and_reserve := by
  rcases h with ⟨_, _, _, _, _, _, _, _, _, h_smooth, _⟩
  exact h_smooth

end ZtareProofs.NS
