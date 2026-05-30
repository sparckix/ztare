import ZtareProofs.ns_low_high_kinematic_dichotomy

namespace ZtareProofs.NS

theorem positive_deformation_charged_by_reserve_loss_of_killing_mode_adapter
    (O : FlatTorusLowHighKinematicPDEObligation)
    (C : FlatTorusKillingModeConclusion)
    (A : FlatTorusKillingModePDEAdapter O C) :
    O.positive_deformation_charged_by_reserve_loss :=
  A.positive_deformation_charged_by_reserve_loss

end ZtareProofs.NS
