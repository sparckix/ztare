import ZtareProofs.ZtareProofs.ns_profile_lipschitz_clay_bridge
import ZtareProofs.ZtareProofs.ns_leray_gain_tax_trackb_obligation

namespace ZtareProofs.NS

theorem generated_amplitude_source_provenance_via_projection
    (O : TrackBProfileLipschitzControlObligation)
    (U : NSEvolution) (n : ℕ) :
    QuarticSurvivalAmplitudeObservableSource ((O.lipschitz_bridge.ledger_of_evolution U).block n) :=
  quartic_survival_amplitude_observable_source_of_projection_and_match_receipt
    ((O.lipschitz_bridge.ledger_of_evolution U).block n)
    (O.generated_quartic_survival_amplitude_projection U n)
    ((O.generated_quartic_survival_amplitude_observable_source U n).observable)
    ((O.generated_quartic_survival_amplitude_observable_source U n).observable_fully_charged)
    ⟨((O.generated_quartic_survival_amplitude_observable_source U n).amplitude_observable_matches_survival_profit_paid)⟩

end ZtareProofs.NS
