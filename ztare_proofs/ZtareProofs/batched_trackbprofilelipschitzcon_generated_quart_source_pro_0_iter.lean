import ZtareProofs.ns_profile_lipschitz_clay_bridge
import ZtareProofs.ns_leray_gain_tax_trackb_obligation

namespace ZtareProofs.NS

def TrackBProfileLipschitzControlObligation.generated_quartic_survival_amplitude_observable_source_of_match
    (O : TrackBProfileLipschitzControlObligation)
    (U : NSEvolution) (n : ℕ)
    (C : SignedObservable)
    (hC : GlobalSignedObservableFullyCharged C)
    (M : QuarticSurvivalAmplitudeObservableMatchReceipt ((O.lipschitz_bridge.ledger_of_evolution U).block n) C (O.generated_quartic_survival_amplitude_projection U n).ampSq) :
    QuarticSurvivalAmplitudeObservableSource ((O.lipschitz_bridge.ledger_of_evolution U).block n) :=
  quartic_survival_amplitude_observable_source_of_projection_and_match_receipt
    ((O.lipschitz_bridge.ledger_of_evolution U).block n)
    (O.generated_quartic_survival_amplitude_projection U n)
    C
    hC
    M

end ZtareProofs.NS
