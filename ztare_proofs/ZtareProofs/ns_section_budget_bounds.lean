import Mathlib.Tactic
import ZtareProofs.ns_eigenframe_poincare_section

namespace ZtareProofs

/-!
`ns_section_budget_bounds` bridges the return-section object to actual gain/loss
bounds.

The current NS branch has isolated the right return object. The next unpaid
bridge is not "does a cycle exist?" but "can danger gain and reset loss be
bounded on that section strongly enough to decide the sign of the cycle budget?"
-/

/-- Local intensity predicate used to avoid circular imports. -/
def highIntensityState (EStar : Real) : EigenframeState → Prop :=
  fun X => EStar ≤ X.peak

/-- Pointwise upper bound on danger gain by entry peak intensity. -/
def dangerGainUpperBoundOnSection
    (Cgain : Real) (α : Nat) (C : EigenframeCycleWitness) : Prop :=
  C.dangerGain ≤ Cgain * C.entry.peak ^ α

/-- Pointwise lower bound on reset loss by entry peak intensity. -/
def resetLossLowerBoundOnSection
    (Closs : Real) (β : Nat) (C : EigenframeCycleWitness) : Prop :=
  Closs * C.entry.peak ^ β ≤ C.resetLoss

/--
Uniform section-level gain upper bound on all high-intensity returns.
-/
def eventualDangerGainUpperBound
    (_S : EigenframeSection) (EStar Cgain : Real) (α : Nat) : Prop :=
  ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
    dangerGainUpperBoundOnSection Cgain α C

/--
Uniform section-level reset-loss lower bound on all high-intensity returns.
-/
def eventualResetLossLowerBound
    (_S : EigenframeSection) (EStar Closs : Real) (β : Nat) : Prop :=
  ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
    resetLossLowerBoundOnSection Closs β C

/--
If every sufficiently intense return has a gain upper bound and a stronger loss
lower bound, then the section is eventually loss-dominant.

This is still a theorem cage: it turns coefficient/exponent control on the
section into the loss-dominant side of the dichotomy.
-/
theorem eventual_loss_dominance_of_section_budget_bounds
    {S : EigenframeSection} {EStar Cgain Closs : Real} {α β : Nat}
    (hgain : eventualDangerGainUpperBound S EStar Cgain α)
    (hloss : eventualResetLossLowerBound S EStar Closs β)
    (hdom :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        Cgain * C.entry.peak ^ α ≤ Closs * C.entry.peak ^ β) :
    eventualLossDominanceOnSection S (highIntensityState EStar) := by
  intro C hhigh
  have hG : C.dangerGain ≤ Cgain * C.entry.peak ^ α := (hgain C hhigh)
  have hL : Closs * C.entry.peak ^ β ≤ C.resetLoss := (hloss C hhigh)
  have hC : Cgain * C.entry.peak ^ α ≤ Closs * C.entry.peak ^ β := hdom C hhigh
  linarith

/--
Target-shape theorem for the current proof seam.
-/
theorem section_budget_target_shape
    {S : EigenframeSection} {EStar Cgain Closs : Real} {α β : Nat}
    (hgain : eventualDangerGainUpperBound S EStar Cgain α)
    (hloss : eventualResetLossLowerBound S EStar Closs β)
    (hdom :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        Cgain * C.entry.peak ^ α ≤ Closs * C.entry.peak ^ β) :
    eventualLossDominanceOnSection S (highIntensityState EStar) := by
  exact eventual_loss_dominance_of_section_budget_bounds hgain hloss hdom

end ZtareProofs
