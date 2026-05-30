import Mathlib.Tactic
import ZtareProofs.ns_coherent_stretch_depletion

namespace ZtareProofs

/-!
`ns_exhaust_scale_reserve_bridge` isolates the exact next analytic slice after
Phase 5CG.

The replay and proxy backtest no longer support a raw scrambling -> depletion
claim. The only surviving candidate is weaker:

* directional scrambling reduces usable organization;
* shell-centroid growth tracks continued spectral exhaust;
* the effective coherent-stretch reserve should therefore be evaluated per
  active exhaust scale, not in raw form.

This file does not prove that statement. It names it precisely.
-/

/-- Relative growth of the active exhaust scale across a transition. -/
noncomputable def shellCentroidGrowthFactor
    (S : CoherentStretchSeq) (i j : Nat) : Real :=
  (S j).shellCentroid / max (S i).shellCentroid 1

/-- Relative contraction of the exhaust-discounted coherent-stretch reserve. -/
noncomputable def exhaustDiscountedReserveRatio
    (S : CoherentStretchSeq) (i j : Nat) : Real :=
  exhaustDiscountedCoherentStretch (S j) / max (exhaustDiscountedCoherentStretch (S i)) 1

/-- The exhaust scale genuinely grows by at least a declared factor. -/
def shellCentroidScaleAmplified
    (S : CoherentStretchSeq) (i j : Nat) (lam : Real) : Prop :=
  lam ≤ shellCentroidGrowthFactor S i j

/-- The effective reserve contracts by at least a declared factor. -/
def exhaustDiscountedReserveContracts
    (S : CoherentStretchSeq) (i j : Nat) (θ : Real) : Prop :=
  exhaustDiscountedReserveRatio S i j ≤ θ

/--
Exact next bridge target.

If angular/vector scrambling occurs and the active exhaust scale amplifies
enough, then the exhaust-discounted coherent-stretch reserve contracts.
-/
def exhaustScaleReserveBridgeTarget
    (S : CoherentStretchSeq) (i j : Nat) (α β lam θ : Real) : Prop :=
  angularVectorScrambling S i j α β ∧ shellCentroidScaleAmplified S i j lam →
    exhaustDiscountedReserveContracts S i j θ

/--
Thresholded version used by the recurrence bridge:
after enough exhaust amplification and scrambling, the discounted reserve falls
below a fixed cap.
-/
def exhaustScaleReserveCapTarget
    (S : CoherentStretchSeq) (i j : Nat) (α β lam cap : Real) : Prop :=
  angularVectorScrambling S i j α β ∧ shellCentroidScaleAmplified S i j lam →
    exhaustDiscountedDepleted S i j cap

/--
If the thresholded bridge target is paid, then the Phase 5CG discounted proxy
gap is discharged on any transition where the declared scale amplification
actually holds.
-/
theorem phase5cg_discounted_proxy_gap_of_cap_target
    {S : CoherentStretchSeq} {i j : Nat} {α β lam cap : Real}
    (hbridge : exhaustScaleReserveCapTarget S i j α β lam cap)
    (hscale : shellCentroidScaleAmplified S i j lam) :
    phase5cgExhaustDiscountedProxyGap S i j α β cap := by
  intro hscramble
  exact hbridge (And.intro hscramble hscale)

/--
Clean theorem shape without fake witness construction:
once the bridge is paid, it yields discounted depletion whenever scrambling and
declared scale amplification both hold.
-/
theorem exhaust_discounted_depleted_of_bridge_target
    {S : CoherentStretchSeq} {i j : Nat} {α β lam cap : Real}
    (hbridge : exhaustScaleReserveCapTarget S i j α β lam cap)
    (hscramble : angularVectorScrambling S i j α β)
    (hscale : shellCentroidScaleAmplified S i j lam) :
    exhaustDiscountedDepleted S i j cap := by
  exact hbridge (And.intro hscramble hscale)

end ZtareProofs
