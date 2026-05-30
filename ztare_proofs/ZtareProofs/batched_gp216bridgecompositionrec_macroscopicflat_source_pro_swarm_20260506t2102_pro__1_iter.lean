import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

def GP216BridgeCompositionReceipt.macroscopicFlatTorusClockSource
    {P : PhaseLatencyLipschitzReserveBridge}
    (duhamelReceipt : LowHighDuhamelBernsteinReceipt)
    (viscousShellGuard : LowHighDuhamelViscousShellGuard duhamelReceipt)
    (S : FlatTorusSmoothKillingFourierSource)
    (L : LowHighKinematicDichotomyLedger)
    (R_est : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (Cert : LowFrequencyLipschitzAuditedControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R_est G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (lp_bony_constant_declared_before_payoff_paid : R_est.lp_bony_constant_declared_before_payoff)
    (lipschitz_cost_declared_before_payoff_paid : R_est.lipschitz_cost_declared_before_payoff)
    (high_shell_energy_declared_before_payoff_paid : R_est.high_shell_energy_declared_before_payoff) :
    MacroscopicFlatTorusClockSource P :=
  macroscopic_flat_torus_clock_source_of_smooth_fourier_and_typed_audited_lipschitz_reserve
    duhamelReceipt viscousShellGuard S L R_est G Cert n link hnosurvivor
    lp_bony_constant_declared_before_payoff_paid
    lipschitz_cost_declared_before_payoff_paid
    high_shell_energy_declared_before_payoff_paid

end ZtareProofs.NS
