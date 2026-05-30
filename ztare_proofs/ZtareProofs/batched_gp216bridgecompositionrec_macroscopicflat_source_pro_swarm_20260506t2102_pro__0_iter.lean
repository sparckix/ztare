import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

theorem macroscopicFlatTorusClockSource_le_GP216BridgeCompositionReceipt_bound
    {P : PhaseLatencyLipschitzReserveBridge}
    (duhamelReceipt : LowHighDuhamelBernsteinReceipt)
    (viscousShellGuard : LowHighDuhamelViscousShellGuard duhamelReceipt)
    (K : FlatTorusKillingModeConclusion)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (Cert : LowFrequencyLipschitzAuditedControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (provenance : FlatTorusKillingModeProvenance K)
    (lp_bony_constant_declared_before_payoff_paid : R.lp_bony_constant_declared_before_payoff)
    (lipschitz_cost_declared_before_payoff_paid : R.lipschitz_cost_declared_before_payoff)
    (high_shell_energy_declared_before_payoff_paid : R.high_shell_energy_declared_before_payoff) :
    MacroscopicFlatTorusClockSource P :=
  macroscopic_flat_torus_clock_source_of_typed_audited_lipschitz_reserve_source
    duhamelReceipt
    viscousShellGuard
    K
    L
    R
    G
    Cert
    n
    link
    hnosurvivor
    provenance
    lp_bony_constant_declared_before_payoff_paid
    lipschitz_cost_declared_before_payoff_paid
    high_shell_energy_declared_before_payoff_paid

end ZtareProofs.NS
