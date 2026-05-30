import ZtareProofs.ns_profile_lipschitz_clay_bridge
import ZtareProofs.ns_leray_gain_tax_trackb_obligation

namespace ZtareProofs.NS

def TrackBProfileLipschitzControlObligation.generated_quartic_survival_amplitude_observable_source_of_threshold
    (O : TrackBProfileLipschitzControlObligation)
    (U : NSEvolution) (n : ℕ)
    (S : QuarticSurvivalThresholdRootObservableSource ((O.lipschitz_bridge.ledger_of_evolution U).block n)) :
    QuarticSurvivalAmplitudeObservableSource ((O.lipschitz_bridge.ledger_of_evolution U).block n) :=
  quartic_survival_amplitude_observable_source_of_threshold_root_observable_source
    ((O.lipschitz_bridge.ledger_of_evolution U).block n)
    S

end ZtareProofs.NS
