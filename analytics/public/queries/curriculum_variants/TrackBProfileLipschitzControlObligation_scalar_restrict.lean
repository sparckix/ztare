-- Curriculum variant: TrackBProfileLipschitzControlObligation → TrackBProfileLipschitzControlObligation_Scalar
-- Transform: SCALAR_RESTRICT (vector-valued → scalar)
-- HONEST CAVEAT: template-based; may be ill-typed.
-- Codex must validate before sending to typed_endpoint_pack.

import ZtareProofs.ns_profile_lipschitz_clay_bridge

namespace ZtareProofs.NS

/-- Profile-pricing plus Lipschitz-control obligation, before any continuation
criterion is attached.

The key anti-tautology requirement is that both maps are fixed:

* `profile_bundle.profile_family_of_block` decomposes the block before
  payoff is scored;
* `lipschitz_bridge.ledger_of_evolution` declares the continuation-relevant
  low-frequency budget before no-survivor is used.
-/
structure TrackBProfileLipschitzControlObligation_Scalar where
  evolution_of_initial_data : SmoothNSInitialData → NSEvolution
  profile_bundle : TrackBProfileDecompositionBridgeBundle
  lipschitz_bridge : LowFrequencyLipschitzBridge
  source_coupling :
    TrackBProfileLipschitzSourceCoupling
      evolution_of_initial_data
      (trackb_profile_decomposition_obligation_of_bridge_bundle
        profile_bundle)
      lipschitz_bridge
  generated_quartic_survival_amplitude_projection :
    ∀ (U : NSEvolution) (n : ℕ),
      QuarticSurvivalAmplitudeProjectionReceipt
        ((lipschitz_bridge.ledger_of_evolution U).block n)


end ZtareProofs.NS
