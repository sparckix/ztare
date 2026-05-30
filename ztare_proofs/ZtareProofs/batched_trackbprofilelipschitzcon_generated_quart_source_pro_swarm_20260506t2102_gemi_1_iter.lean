import ZtareProofs.ZtareProofs.ns_profile_lipschitz_clay_bridge
import ZtareProofs.ZtareProofs.ns_leray_gain_tax_trackb_obligation

namespace ZtareProofs.NS

theorem generated_amplitude_source_provenance_via_threshold_root
    (O : TrackBProfileLipschitzControlObligation)
    (U : NSEvolution) (n : ℕ) :
    QuarticSurvivalAmplitudeObservableSource ((O.lipschitz_bridge.ledger_of_evolution U).block n) :=
  let B := (O.lipschitz_bridge.ledger_of_evolution U).block n
  let S := O.generated_quartic_survival_amplitude_observable_source U n
  quartic_survival_amplitude_observable_source_of_threshold_root_observable_source B
    { observable := S.observable,
      observable_fully_charged := S.observable_fully_charged,
      ampSq := S.ampSq,
      observable_match := ⟨S.amplitude_observable_matches_survival_profit_paid⟩,
      root_ledger_match := ⟨S.root_defect_ledger_same_as_survival_observable_paid⟩ }

end ZtareProofs.NS
