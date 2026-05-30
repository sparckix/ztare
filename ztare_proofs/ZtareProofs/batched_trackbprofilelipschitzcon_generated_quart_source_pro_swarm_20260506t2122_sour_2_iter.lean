import ZtareProofs.ns_profile_lipschitz_clay_bridge

namespace ZtareProofs.NS

def generated_quartic_survival_amplitude_observable_source_from_threshold_sources
    (lipschitz_bridge : LowFrequencyLipschitzBridge)
    (source :
      ∀ (U : NSEvolution) (n : ℕ),
        QuarticSurvivalThresholdRootObservableSource
          ((lipschitz_bridge.ledger_of_evolution U).block n)) :
    ∀ (U : NSEvolution) (n : ℕ),
      QuarticSurvivalAmplitudeObservableSource
        ((lipschitz_bridge.ledger_of_evolution U).block n) :=
  generated_amplitude_sources_of_threshold_root_observable_sources lipschitz_bridge source

end ZtareProofs.NS
