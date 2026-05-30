import ZtareProofs.ns_low_high_kinematic_dichotomy

namespace ZtareProofs.NS

theorem positive_deformation_charged_by_reserve_loss_of_sources
    (O : FlatTorusLowHighKinematicPDEObligation)
    (C : FlatTorusKillingModeConclusion)
    (A : FlatTorusKillingModePDEAdapter O C) :
    O.positive_deformation_charged_by_reserve_loss :=
  (flat_torus_phase_capacity_sources_of_killing_mode_adapter O C A).2.2.1

end ZtareProofs.NS
