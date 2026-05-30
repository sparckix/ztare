import Mathlib.Tactic
import ZtareProofs.ns_eigenframe_poincare_section
import ZtareProofs.ns_fractal_recurrence_target
import ZtareProofs.ns_section_budget_bounds

namespace ZtareProofs

/-!
`ns_section_dichotomy` is the pincer object for the current NS branch.

The numerical side no longer supports broad geometric storytelling. What
remains is a section-level competition between two rival futures:

* eventual loss dominance on sufficiently intense returns
* profitable shrinking recurrence along a subsequence

This file does not prove which side wins. It formalizes the exact dichotomy so
future lemmas have to pay one side or the other explicitly.
-/

/--
Intensity predicate for section entries above a critical threshold.
-/
def highIntensityEntry (EStar : Real) : EigenframeState → Prop :=
  fun X => EStar ≤ X.peak

/--
Loss-dominant side of the section dichotomy.
-/
def lossDominantSide (S : EigenframeSection) (EStar : Real) : Prop :=
  eventualLossDominanceOnSection S (highIntensityEntry EStar)

/--
Profitable shrinking side of the section dichotomy.

This is the clean rival to the exhaust horizon: there exists a subsequence of
returns with positive carry and strict scale shrink.
-/
def profitableShrinkingSubsequence (Seq : CycleSeq) : Prop :=
  profitableRecurrence Seq ∧ shrinkingRecurrence Seq

/--
Section-level dichotomy object.

Either high-intensity returns are eventually loss-dominant, or there exists a
profitable shrinking-return subsequence that keeps the ratchet alive as a live
rival mechanism.
-/
def sectionDichotomy
    (S : EigenframeSection) (EStar : Real) (Seq : CycleSeq) : Prop :=
  lossDominantSide S EStar ∨ profitableShrinkingSubsequence Seq

/--
If eventual loss dominance holds on the section, the dichotomy resolves to the
anti-blowup side.
-/
theorem section_dichotomy_of_loss_dominance
    {S : EigenframeSection} {EStar : Real} {Seq : CycleSeq}
    (hloss : lossDominantSide S EStar) :
    sectionDichotomy S EStar Seq := by
  exact Or.inl hloss

/--
If a profitable shrinking-return subsequence exists, the dichotomy resolves to
the rival fractal side.
-/
theorem section_dichotomy_of_profitable_shrinking
    {S : EigenframeSection} {EStar : Real} {Seq : CycleSeq}
    (hrival : profitableShrinkingSubsequence Seq) :
    sectionDichotomy S EStar Seq := by
  exact Or.inr hrival

/--
Target-shape theorem for the current branch.

This is the precise pincer now in force: a future theorem must pay for either
eventual loss dominance or a profitable shrinking subsequence.
-/
theorem section_dichotomy_target_shape
    {S : EigenframeSection} {EStar : Real} {Seq : CycleSeq}
    (h : sectionDichotomy S EStar Seq) :
    sectionDichotomy S EStar Seq := by
  exact h

/--
Budget-bound route into the dichotomy.

If high-intensity returns admit section-level gain/loss bounds strong enough to
force eventual loss dominance, then the dichotomy resolves to the anti-blowup
side immediately.
-/
theorem section_dichotomy_of_section_budget_bounds
    {S : EigenframeSection} {EStar Cgain Closs : Real} {α β : Nat} {Seq : CycleSeq}
    (hgain : eventualDangerGainUpperBound S EStar Cgain α)
    (hloss : eventualResetLossLowerBound S EStar Closs β)
    (hdom :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        Cgain * C.entry.peak ^ α ≤ Closs * C.entry.peak ^ β) :
    sectionDichotomy S EStar Seq := by
  exact Or.inl (eventual_loss_dominance_of_section_budget_bounds hgain hloss hdom)

end ZtareProofs
