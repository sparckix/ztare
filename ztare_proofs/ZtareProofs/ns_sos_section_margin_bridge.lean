import Mathlib.Tactic
import ZtareProofs.ns_section_dichotomy
import ZtareProofs.ns_sos_certificate_bridge
import ZtareProofs.ns_spectral_diseconomy_toxic_block

/-!
# SOS margin to section-budget bridge

Phase 5BO suggests that the reduced toxic block supplies a strict scalar margin.
The existing section spine does not need to know the block geometry.  It only
needs a loss lower bound strong enough to dominate the gain upper bound.

This file is the adapter: if a certified stealth-growth state is the local
budget model for a return-section cycle, and that certificate yields the scalar
margin `resetLoss >= dangerGain`, then the existing section dichotomy resolves
to the anti-blowup side.

This is intentionally not a PDE theorem.  It isolates the remaining obligations:

1. instantiate the SOS/toxic-block certificate for the state or cycle;
2. prove the certified scalar margin matches the section gain/loss quantities;
3. prove the margin is uniform over the relevant high-intensity section.
-/

namespace ZtareProofs

open ZtareProofs.NS

/--
Cycle-level scalar margin supplied by a certified local toxic block.

This avoids pretending that a finite-dimensional SOS receipt is already a PDE
bound.  The PDE work must produce this proposition for each high-intensity
cycle.
-/
def toxicBlockMarginControlsCycle (C : EigenframeCycleWitness) : Prop :=
  C.dangerGain ≤ C.resetLoss

/--
The concrete data needed to match a local stealth-growth budget segment to an
eigenframe section cycle.

This is the exact missing bridge named by the current proof spine.  The
equalities are deliberately explicit so peer review can attack them one by one:

* `signedProduction` is the cycle's danger gain;
* `viscousDissipation` is the cycle's reset loss;
* the segment's net budget is the cycle profit.
-/
structure LocalBudgetRepresentsCycle
    (s : StealthGrowthState) (C : EigenframeCycleWitness) : Prop where
  production_eq_dangerGain : s.signedProduction = C.dangerGain
  dissipation_eq_resetLoss : s.viscousDissipation = C.resetLoss

/--
The local budget representation converts negative net budget into cycle-level
loss dominance.
-/
theorem toxic_block_cycle_margin_of_local_budget_representation
    (C : EigenframeCycleWitness) (s : StealthGrowthState)
    (hrep : LocalBudgetRepresentsCycle s C)
    (hnet : netEnstrophyBudget s ≤ 0) :
    toxicBlockMarginControlsCycle C := by
  unfold toxicBlockMarginControlsCycle
  unfold netEnstrophyBudget at hnet
  rw [hrep.production_eq_dangerGain, hrep.dissipation_eq_resetLoss] at hnet
  linarith

/--
Strict local negative budget is more than enough for cycle margin.
-/
theorem toxic_block_cycle_margin_of_strict_local_budget_representation
    (C : EigenframeCycleWitness) (s : StealthGrowthState)
    (hrep : LocalBudgetRepresentsCycle s C)
    (hnet : netEnstrophyBudget s < 0) :
    toxicBlockMarginControlsCycle C := by
  exact toxic_block_cycle_margin_of_local_budget_representation C s hrep (le_of_lt hnet)

/--
If every high-intensity return has a toxic-block margin, the section is
eventually loss-dominant.
-/
theorem eventual_loss_dominance_of_toxic_block_cycle_margin
    {S : EigenframeSection} {EStar : Real}
    (hmargin :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        toxicBlockMarginControlsCycle C) :
    eventualLossDominanceOnSection S (highIntensityState EStar) := by
  intro C hhigh
  exact hmargin C hhigh

/--
Toxic-block margins route directly into the section dichotomy.
-/
theorem section_dichotomy_of_toxic_block_cycle_margin
    {S : EigenframeSection} {EStar : Real} {Seq : CycleSeq}
    (hmargin :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        toxicBlockMarginControlsCycle C) :
    sectionDichotomy S EStar Seq := by
  exact Or.inl (eventual_loss_dominance_of_toxic_block_cycle_margin hmargin)

/--
An SOS certificate for a stealth-growth state gives a negative net budget for
that state.  This is the local scalar part of the bridge.
-/
theorem negative_budget_of_local_sos_receipt
    (s : StealthGrowthState) (slack : ℝ) (terms : List ℝ)
    (hslack : 0 < slack)
    (hcert : dissipationProductionGap s = slack + sumSquares terms) :
    netEnstrophyBudget s < 0 := by
  exact nonpositive_net_budget_of_sos_gap_certificate s slack terms hslack hcert

/--
If a local SOS receipt is known to represent the section-cycle loss/gain
accounting, the cycle margin follows.
-/
theorem toxic_block_cycle_margin_of_local_sos_receipt
    (C : EigenframeCycleWitness)
    (s : StealthGrowthState) (slack : ℝ) (terms : List ℝ)
    (hslack : 0 < slack)
    (hcert : dissipationProductionGap s = slack + sumSquares terms)
    (hrep : LocalBudgetRepresentsCycle s C) :
    toxicBlockMarginControlsCycle C := by
  exact toxic_block_cycle_margin_of_strict_local_budget_representation C s hrep
    (negative_budget_of_local_sos_receipt s slack terms hslack hcert)

/--
Uniform local SOS receipts plus uniform local-to-cycle representations close the
section side of the dichotomy.
-/
theorem section_dichotomy_of_uniform_local_sos_receipts
    {S : EigenframeSection} {EStar : Real} {Seq : CycleSeq}
    (chooseState : EigenframeCycleWitness → StealthGrowthState)
    (chooseSlack : EigenframeCycleWitness → ℝ)
    (chooseTerms : EigenframeCycleWitness → List ℝ)
    (hslack :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        0 < chooseSlack C)
    (hcert :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        dissipationProductionGap (chooseState C) =
          chooseSlack C + sumSquares (chooseTerms C))
    (hrep :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        LocalBudgetRepresentsCycle (chooseState C) C) :
    sectionDichotomy S EStar Seq := by
  apply section_dichotomy_of_toxic_block_cycle_margin
  intro C hhigh
  exact toxic_block_cycle_margin_of_local_sos_receipt C (chooseState C)
    (chooseSlack C) (chooseTerms C) (hslack C hhigh) (hcert C hhigh) (hrep C hhigh)

end ZtareProofs
