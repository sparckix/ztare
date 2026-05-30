import Mathlib.Tactic
import ZtareProofs.ns_sos_section_margin_bridge
import ZtareProofs.ns_stealth_coverage_case_split

/-!
# Stealth coverage to section bridge

`ns_stealth_coverage_case_split` proves the local statement:

* outside the pressure-stealth tube, exposure rules out hidden growth;
* inside the tube, an SOS/budget receipt rules out growth.

This file lifts that local coverage alternative to the eigenframe section
dichotomy.  It names the one remaining accounting obligation:

`profitableCycleImpliesGrowthBearing`

If a return cycle is truly profitable (`resetLoss < dangerGain`), the local
segment chosen to represent that cycle must be growth-bearing.  Once that
obligation is paid, the coverage split forces `dangerGain ≤ resetLoss`.
-/

namespace ZtareProofs

open ZtareProofs.NS

noncomputable section

/--
Accounting bridge from an eigenframe cycle to the local stealth-growth segment
chosen to represent it.

This is the honest remaining PDE/section obligation: a cycle with positive
profit must show up as a growth-bearing local segment.  Without this bridge,
one could prove local sterility while the cycle budget hides gain elsewhere.
-/
def profitableCycleImpliesGrowthBearing
    (s : StealthGrowthState) (C : EigenframeCycleWitness) : Prop :=
  C.resetLoss < C.dangerGain → growthBearingSegment s

/--
Local stealth coverage forces a cycle-level toxic-block margin once profitable
cycle budget is known to imply a growth-bearing segment.
-/
theorem toxic_block_cycle_margin_of_stealth_coverage
    (C : EigenframeCycleWitness) (s : StealthGrowthState)
    (eps derivBound torqueFloor slack : ℝ) (terms : List ℝ)
    (hbudget : enstrophyBudgetConsistent s)
    (hexposed : exposedStateNotGrowthBearing s eps derivBound torqueFloor)
    (hcover : stealthCoverageAlternative s eps derivBound torqueFloor slack terms)
    (hprofitImpl : profitableCycleImpliesGrowthBearing s C) :
    toxicBlockMarginControlsCycle C := by
  have hnogrowth : ¬ growthBearingSegment s :=
    no_growth_bearing_of_stealth_coverage_alternative
      s eps derivBound torqueFloor slack terms hbudget hexposed hcover
  unfold toxicBlockMarginControlsCycle
  have hnotProfit : ¬ C.resetLoss < C.dangerGain := by
    intro hprofit
    exact hnogrowth (hprofitImpl hprofit)
  exact not_lt.mp hnotProfit

/--
Uniform coverage route into the section dichotomy.

For every sufficiently intense return, choose a local state and prove:

* the local enstrophy budget identity;
* exposed states are taxable;
* the local state is either exposed or covered by an in-tube SOS receipt;
* any profitable cycle would make that local state growth-bearing.

Then high-intensity section returns are loss-dominant.
-/
theorem section_dichotomy_of_uniform_stealth_coverage
    {S : EigenframeSection} {EStar : ℝ} {Seq : CycleSeq}
    (chooseState : EigenframeCycleWitness → StealthGrowthState)
    (chooseSlack : EigenframeCycleWitness → ℝ)
    (chooseTerms : EigenframeCycleWitness → List ℝ)
    (eps derivBound torqueFloor : ℝ)
    (hbudget :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        enstrophyBudgetConsistent (chooseState C))
    (hexposed :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        exposedStateNotGrowthBearing (chooseState C) eps derivBound torqueFloor)
    (hcover :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        stealthCoverageAlternative
          (chooseState C) eps derivBound torqueFloor (chooseSlack C) (chooseTerms C))
    (hprofitImpl :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        profitableCycleImpliesGrowthBearing (chooseState C) C) :
    sectionDichotomy S EStar Seq := by
  apply section_dichotomy_of_toxic_block_cycle_margin
  intro C hhigh
  exact toxic_block_cycle_margin_of_stealth_coverage
    C (chooseState C) eps derivBound torqueFloor (chooseSlack C) (chooseTerms C)
    (hbudget C hhigh) (hexposed C hhigh) (hcover C hhigh) (hprofitImpl C hhigh)

end

end ZtareProofs
