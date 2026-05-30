import ZtareProofs.ns_profile_lipschitz_clay_bridge

namespace ZtareProofs.NS

def generated_quartic_survival_amplitude_observable_source_from_projections
    (lipschitz_bridge : LowFrequencyLipschitzBridge)
    (hamplitude_projection :
      ∀ (U : NSEvolution) (n : ℕ),
        QuarticSurvivalAmplitudeProjectionReceipt
          ((lipschitz_bridge.ledger_of_evolution U).block n))
    (observable_of_generated_block :
      ∀ (_U : NSEvolution) (_n : ℕ), SignedObservable)
    (observable_fully_charged :
      ∀ (U : NSEvolution) (n : ℕ),
        GlobalSignedObservableFullyCharged
          (observable_of_generated_block U n))
    (observable_matches_survival_profit :
      ∀ (_U : NSEvolution) (_n : ℕ), Prop)
    (observable_matches_survival_profit_paid :
      ∀ (U : NSEvolution) (n : ℕ),
        observable_matches_survival_profit U n) :
    ∀ (U : NSEvolution) (n : ℕ),
      QuarticSurvivalAmplitudeObservableSource
        ((lipschitz_bridge.ledger_of_evolution U).block n) :=
  generated_amplitude_sources_of_projections_and_observables
    lipschitz_bridge
    hamplitude_projection
    observable_of_generated_block
    observable_fully_charged
    observable_matches_survival_profit
    observable_matches_survival_profit_paid

end ZtareProofs.NS
