-- Curriculum variant: TrackBProfileLipschitzControlObligation → TrackBProfileLipschitzControlObligation_OneD
-- Transform: DIMENSION_REDUCE (drop spatial dimensions (3D → 1D))
-- HONEST CAVEAT: template-based; may be ill-typed.
-- Codex must validate before sending to typed_endpoint_pack.

tiate these
fixed maps and certificates before scoring a profitable route.
-/

namespace ZtareProofs.NS

/-- Source coupling between the profile-decomposition side and the generated
low-frequency Lipschitz ledger.

This is the seam where a closure attempt can otherwise become tautological:
the profile family and generated Lipschitz block must be declared as the same
block-level object before no-survivor pricing is used. The quartic projection
itself is carried by the typed amplitude receipt on
`TrackBProfileLipschitzControlObligation_OneD`, not by an opaque coupling `Prop`.
-/
structure TrackBProfileLipschitzSourceCoupling
    (evolution_of_initial_data : SmoothNSInitialData → NSEvolution)
    (profile_obligation : TrackBProfileDecompositionObligation)
    (lipschitz_bridge : LowFrequencyLipschitzBridge) where
  generated_lipschitz_block_declared_before_profile_pricing :
    ∀ _u0 : SmoothNSInitialData, ∀ _n : ℕ, Prop
  generated_lipschitz_block_declared_before_profile_pricing_paid :
    ∀ u0 : SmoothNSInitialData, ∀ n : ℕ,
      generated_lipschitz_block_declared_before_profile_pricing u0 n
  profile_family_applied_to_generated_lipschitz_block :
    ∀ _u0 : SmoothNSInitialData, ∀ _n : ℕ, Prop
  profile_family_applied_to_generated_lipschitz_block_paid :
    ∀ u0 : SmoothNSInitialData, ∀ n : ℕ,
      profile_family_applied_to_generated_lipschitz_block u0 n
  no_posthoc_profile_lipschitz_block_substitution :
    ∀ _u0 : SmoothNSInitialData, ∀ _n : ℕ, Prop
  no_posthoc_profile_lipschitz_block_substitution_paid :
    ∀ u0 : SmoothNSInitialData, ∀ n : ℕ,
      no_posthoc_profile_lipschitz_block_substitution u0 n

/-- Profile-pricing plus Lipschitz-control obligation, before any continuation
criterion is attached.

The key anti-tautology requirement is that both maps are fixed:

* `profile_bundle.profile_family_of_block` decomposes the block before
  payoff is scored;
* `lipschitz_bridge.ledger_of_evolution` declares the continuation-relevant
  low-frequency budget before no-survivor is used.
-/
structure TrackBProfileLipschitzControlObligation_OneD where
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

/-- Derived profile-decomposition obligation for a profile/Lipschitz endpoint.

The obligation is no longer a free field: it is projected from the same-family
profile bridge bundle, so instantiating the top-level profile/Lipschitz object
must pay the branch-bridge provenance first. -/
def TrackBProfileLipschitzControlObligation_OneD.profile_obligation
    (O : TrackBProfileLipschitzControlObligation_OneD) :
    TrackBProfileDecompositionObligation :=
  trackb_profile_decomposition_obligation_of_bridge_bundle O.profile_bundle

/-- The generated block is source-ready for profile pricing and Lipschitz
reserve pricing under the same predeclared block identity. -/
def TrackBProfileLipschitzGeneratedBlockSourceReady
    (O : TrackBProfileLipschitzControlObligation_OneD)
    (u0 : SmoothNSInitialData)
    (n : ℕ) : Prop :=
  let U := O.evolution_of_initial_data u0
  let L := O.lipschitz_bridge.ledger_of_evolution U
  let hglobal :=
    (O.lipschitz_bridge.audited_certificate_of_evolution U).block_is_global n
  O.source_coupling.generated_lipschitz_block_declared_before_profile_pricing
      u0 n ∧
    O.source_coupling.profile_family_applied_to_generated_lipschitz_block
        u0 n ∧
      O.source_coupling.no_posthoc_profile_lipschitz_block_substitution
          u0 n ∧
        TrackBProfileDecompositionBranchSourceReady
          O.profile_obligation.source_receipt
          (L.block n)
          hglobal

/-- The declared source coupling and the profile-decomposition source receipt
make every generated Lipschitz block ready for non-tautological profile
pricing. -/
theorem trackB_profile_lipschitz_generated_block_source_ready
    (O : TrackBProfileLipschitzControlObligation_OneD)
    (u0 : SmoothNSInitialData)
    (n : ℕ) :
    TrackBProfileLipschitzGeneratedBlockSourceReady O u0 n := by
  dsimp [TrackBProfileLipschitzGeneratedBlockSourceReady]
  exact
    ⟨(O.source_coupling).generated_lipschitz_block_declared_before_profile_pricing_paid u0 n,
      (O.source_coupling).profile_family_applied_to_generated_lipschitz_block_paid u0 n,
      (O.source_coupling).no_posthoc_profile_lipschitz_block_substitution_paid u0 n,
      trackb_profile_decomposition_branch_source_ready
        O.profile_obligation.source_receipt
        ((O.lipschitz_bridge.ledger_of_evolution
          (O.evolution_of_initial_data u0)).block 