import ZtareProofs.ns_profile_lipschitz_clay_bridge

namespace ZtareProofs.NS

def generated_quartic_survival_amplitude_observable_source_of_inputs
    (lipschitz_bridge : LowFrequencyLipschitzBridge)
    (I : GeneratedQuarticSurvivalAmplitudeSourceInputs lipschitz_bridge) :
    ∀ (U : NSEvolution) (n : ℕ),
      QuarticSurvivalAmplitudeObservableSource
        ((lipschitz_bridge.ledger_of_evolution U).block n) :=
  generated_amplitude_sources_of_input_receipts lipschitz_bridge I

end ZtareProofs.NS
