import ZtareProofs.ns_profile_lipschitz_clay_bridge
import ZtareProofs.ns_leray_gain_tax_trackb_obligation

namespace ZtareProofs.NS

def TrackBProfileLipschitzControlObligation.generated_quartic_survival_amplitude_observable_source_of_inputs
    (O : TrackBProfileLipschitzControlObligation)
    (I : GeneratedQuarticSurvivalAmplitudeSourceInputs O.lipschitz_bridge)
    (U : NSEvolution) (n : ℕ) :
    QuarticSurvivalAmplitudeObservableSource ((O.lipschitz_bridge.ledger_of_evolution U).block n) :=
  generated_amplitude_sources_of_input_receipts
    O.lipschitz_bridge
    I
    U
    n

end ZtareProofs.NS
