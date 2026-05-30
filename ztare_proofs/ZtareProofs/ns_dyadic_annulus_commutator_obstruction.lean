import Mathlib.Tactic
import ZtareProofs.ns_global_tail_coercivity_bridge

namespace ZtareProofs

/-!
`ns_dyadic_annulus_commutator_obstruction` captures the informative core of
iter 2 from the proof-search substrate.

The question is no longer "could some clever partition help?" in the abstract.
The sharper question is:

> can a dyadic annulus cutoff construction beat the generic mass-growth versus
> gradient-smoothing imbalance for `L^3_{uloc}` data?

This file records the theorem-shaped obstruction claimed by that reranking.
-/

/-- Spatial scale of a dyadic transition annulus. -/
abbrev AnnulusScale := Real

/-- Cutoff gradient magnitude on the transition annulus. -/
abbrev MaskGradientScale := Real

/-- Uniform-local advection mass on the annulus. -/
abbrev AnnulusMassScale := Real

/-- Fractional-integration gain when lifting the commutator residual. -/
abbrev FractionalIntegrationGain := Real

/--
Dyadic annulus scaling law used by the route-2 reranking.
-/
def dyadicAnnulusScalingLaw
    (R gradientScale massScale fractionalGain residualScale : Real) : Prop :=
  0 < R ∧
    gradientScale = 1 / R ∧
    massScale = R ^ (2 : Nat) ∧
    fractionalGain = Real.sqrt R ∧
    residualScale = gradientScale * massScale * fractionalGain

/--
The obstruction claim: for `R > 1`, the dyadic annulus residual grows rather
than decays, so multi-scale cutoff partitioning alone cannot neutralize the
commutator tower.
-/
def dyadicAnnulusCommutatorObstruction
    (R residualScale : Real) : Prop :=
  1 < R ∧
    R ^ (3 : Nat) ≤ residualScale ^ (2 : Nat)

/--
If the route-2 scaling law is paid, the annulus residual has the expected
`R^(3/2)` form, written as `R * sqrt R`.
-/
theorem residual_scaling_of_dyadicAnnulusScalingLaw
    {R gradientScale massScale fractionalGain residualScale : Real}
    (h :
      dyadicAnnulusScalingLaw
        R gradientScale massScale fractionalGain residualScale)
    (hR : 1 < R) :
    residualScale = R * Real.sqrt R := by
  rcases h with ⟨_, hg, hm, hf, hr⟩
  calc
    residualScale = (1 / R) * (R ^ (2 : Nat)) * Real.sqrt R := by
      simpa [hg, hm, hf] using hr
    _ = R * Real.sqrt R := by
      field_simp [hR.ne']

/--
Route-2 sharpened obstruction: unless the global tail bridge is already paying
the localization cost, dyadic annulus partitioning is not a true escape route.
-/
def dyadicAnnulusDoesNotBypassTailAntecedent
    (R gradientScale massScale fractionalGain residualScale
      δ penalty K tailDecay margin : Real) : Prop :=
  dyadicAnnulusScalingLaw
      R gradientScale massScale fractionalGain residualScale ∧
    globalTailPrecedesCommutatorTower δ penalty K tailDecay margin

end ZtareProofs
