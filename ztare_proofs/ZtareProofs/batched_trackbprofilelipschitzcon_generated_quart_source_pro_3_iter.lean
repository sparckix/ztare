import ZtareProofs.ns_profile_lipschitz_clay_bridge
import ZtareProofs.ns_leray_gain_tax_trackb_obligation

namespace ZtareProofs.NS

def trackB_generated_quartic_survival_amplitude_observable_source_from_threshold_inputs
    (lipschitz_bridge : LowFrequencyLipschitzBridge)
    (I : GeneratedQuarticSurvivalThresholdRootAmplitudeSourceInputs lipschitz_bridge)
    (U : NSEvolution) (n : ℕ) :
    QuarticSurvivalAmplitudeObservableSource ((lipschitz_bridge.ledger_of_evolution U).block n) :=
  generated_amplitude_sources_of_threshold_root_source_inputs
    lipschitz_bridge
    I
    U
    n

end ZtareProofs.NS
