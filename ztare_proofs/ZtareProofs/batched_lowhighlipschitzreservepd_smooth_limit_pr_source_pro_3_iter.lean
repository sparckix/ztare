import ZtareProofs.ns_low_high_lipschitz_reserve_adapter

namespace ZtareProofs.NS

theorem smooth_limit_preserves_cost_and_reserve_from_audited_closure
    (O : LowHighLipschitzReservePDEObligation)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzAuditedControlCertificate G)
    (S : LowHighEnergyBudgetShellReserveClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (H : LowHighEnergyBudgetShellReservePDEHandoff O G S) :
    O.smooth_limit_preserves_cost_and_reserve := by
  have h_sat := low_high_lipschitz_reserve_pde_obligation_satisfied_of_audited_energy_budget_shell_closure O G C S hnosurvivor H
  exact h_sat.right.right.right.right.right.right.right.right.right.left

end ZtareProofs.NS
