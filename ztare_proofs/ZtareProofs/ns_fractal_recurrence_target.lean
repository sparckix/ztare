import Mathlib.Tactic
import ZtareProofs.ns_discrete_recurrence_map
import ZtareProofs.ns_eigenframe_poincare_section

namespace ZtareProofs

/-!
`ns_fractal_recurrence_target` captures the strongest live rival to the
viscous-exhaust route.

The current NS branch does **not** prove fractal / Zeno recurrence. But if the
branch survives the exhaust-horizon attack, this is the exact alternative
mechanism class left standing:

* profitable returns on an eigenframe section,
* geometric scale shrink across returns,
* summable cycle times.

This file names that rival cleanly so it can be attacked without rhetoric.
-/

/-- Abstract spatial scale attached to an eigenframe cycle witness. -/
noncomputable def cycleScale (C : EigenframeCycleWitness) : Real :=
  1 / C.entry.peak

/-- Return profitability on a witness. -/
def profitableReturn (C : EigenframeCycleWitness) : Prop :=
  C.resetLoss < C.dangerGain

/-- Scale shrink across a witness. -/
def shrinkingReturn (C : EigenframeCycleWitness) : Prop :=
  C.ret.peak > C.entry.peak

/-- Abstract sequence of eigenframe return witnesses. -/
def CycleSeq := Nat → EigenframeCycleWitness

/--
Uniformly profitable recurrence along a sequence.
-/
def profitableRecurrence (S : CycleSeq) : Prop :=
  ∀ n : Nat, profitableReturn (S n)

/--
Strict scale shrink along a sequence, expressed through peak growth.
-/
def shrinkingRecurrence (S : CycleSeq) : Prop :=
  ∀ n : Nat, shrinkingReturn (S n)

/--
Summable geometric-time surrogate: cycle times shrink by a fixed ratio `ρ < 1`.
-/
def zenoTimeCompression (S : CycleSeq) (ρ : Real) : Prop :=
  0 ≤ ρ ∧ ρ < 1 ∧
    ∀ n : Nat, eigenframeCycleTime (S (n + 1)) ≤ ρ * eigenframeCycleTime (S n)

/--
Fractal/Zeno target shape: profitable returns, shrinking scales, and summable
cycle times all at once.
-/
def fractalRecurrenceTarget (S : CycleSeq) (ρ : Real) : Prop :=
  profitableRecurrence S ∧ shrinkingRecurrence S ∧ zenoTimeCompression S ρ

/--
If every witness in a sequence has gain-dominant budget, then the induced
cycle map is locally profitable on every return.
-/
theorem profitable_cycle_map_on_profitable_sequence
    {S : CycleSeq} :
    profitableRecurrence S →
      ∀ n : Nat, 0 < eigenframeCycleProfit (S n) := by
  intro hprofit n
  unfold profitableRecurrence profitableReturn at hprofit
  unfold eigenframeCycleProfit
  have h := hprofit n
  linarith

/--
If return peaks strictly exceed entry peaks on every witness, the abstract
scale `1 / peak` strictly shrinks on every return, provided peaks stay positive.
-/
theorem scale_shrink_of_peak_growth
    {C : EigenframeCycleWitness}
    (hpos : 0 < C.entry.peak)
    (hgrow : C.ret.peak > C.entry.peak) :
    1 / C.ret.peak < cycleScale C := by
  have hretpos : 0 < C.ret.peak := lt_trans hpos hgrow
  unfold cycleScale
  exact (one_div_lt_one_div hretpos hpos).2 hgrow

/--
This is the exact rival mechanism cage to the exhaust-horizon route.

It does not prove fractal recurrence. It names the theorem burden cleanly:
one must simultaneously pay for profitable returns, shrinking scales, and
compressed cycle times.
-/
theorem fractal_recurrence_target_shape
    {S : CycleSeq} {ρ : Real}
    (h : fractalRecurrenceTarget S ρ) :
    fractalRecurrenceTarget S ρ := by
  exact h

end ZtareProofs
