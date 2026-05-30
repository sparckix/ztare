import ZtareProofs.ns_low_high_kinematic_dichotomy

namespace ZtareProofs.NS

theorem positive_deformation_charged_by_reserve_loss_of_satisfied
    (O : FlatTorusLowHighKinematicPDEObligation)
    (H : FlatTorusLowHighKinematicPDEObligationSatisfied O) :
    O.positive_deformation_charged_by_reserve_loss :=
  H.positive_deformation_charged_by_reserve_loss

end ZtareProofs.NS
