import Mathlib.Tactic
import ZtareProofs.ns_sos_certificate_bridge

/-!
# Stealth coverage case split

Phase 5BQ initially labeled the spectral ladder as `truncation_collapse` because
the current reduced-block certificate is not uniformly positive across every
tested resolution.  Phase 5BR isolates the more useful proof object:

* no tested row at any `N` had positive net budget;
* every high-resolution reduced block that actually existed was positive;
* at `N = 96, 128`, the optimizer did not find the stealth tube, so there was
  no local SOS receipt to check.

The formal lesson is a coverage split, not a single certificate:

* outside the pressure-stealth tube, the state is exposed/taxable;
* inside the tube, a budget or SOS receipt must prove sterility.

This file records that split so missing high-`N` block rows are not
misinterpreted as counterexamples to the proof spine.
-/

namespace ZtareProofs.NS

noncomputable section

/--
The exposed side of the atlas: if a state is not in the pressure-stealth tube,
the pressure-footprint mechanism already rules it out as a hidden
growth-bearing segment.

This is intentionally a proposition, not a theorem: a PDE lemma must instantiate
it from the pressure-tax / topological-gridlock side of the proof.
-/
def exposedStateNotGrowthBearing
    (s : StealthGrowthState) (eps derivBound torqueFloor : ℝ) : Prop :=
  ¬ inPressureStealthTube s eps derivBound torqueFloor → ¬ growthBearingSegment s

/--
The in-tube side of the atlas: a stealth state has an exact SOS receipt for the
dissipation-production gap.
-/
def inTubeSosReceipt
    (s : StealthGrowthState) (eps derivBound torqueFloor slack : ℝ)
    (terms : List ℝ) : Prop :=
  inPressureStealthTube s eps derivBound torqueFloor ∧
    0 < slack ∧
    dissipationProductionGap s = slack + sumSquares terms

/--
One-state coverage alternative: either the state is outside the stealth tube,
or it is inside the tube and has a sterile-budget certificate.

This is the theorem-level version of the 5BR interpretation.  High-`N` missing
block rows support the left branch; certified 5BO/5BP/5BQ rows support the
right branch.
-/
def stealthCoverageAlternative
    (s : StealthGrowthState) (eps derivBound torqueFloor slack : ℝ)
    (terms : List ℝ) : Prop :=
  ¬ inPressureStealthTube s eps derivBound torqueFloor ∨
    inTubeSosReceipt s eps derivBound torqueFloor slack terms

/--
Coverage split for a single segment.

If exposed states cannot be hidden growth-bearing segments, and in-tube states
carry an SOS gap receipt, then the segment cannot be growth-bearing.
-/
theorem no_growth_bearing_of_stealth_coverage_alternative
    (s : StealthGrowthState)
    (eps derivBound torqueFloor slack : ℝ) (terms : List ℝ)
    (hbudget : enstrophyBudgetConsistent s)
    (hexposed : exposedStateNotGrowthBearing s eps derivBound torqueFloor)
    (hcover : stealthCoverageAlternative s eps derivBound torqueFloor slack terms) :
    ¬ growthBearingSegment s := by
  unfold stealthCoverageAlternative at hcover
  cases hcover with
  | inl hnotTube =>
      exact hexposed hnotTube
  | inr hreceipt =>
      unfold inTubeSosReceipt at hreceipt
      rcases hreceipt with ⟨htube, hslack, hcert⟩
      exact no_growth_bearing_segment_of_sos_gap_certificate
        s eps derivBound torqueFloor slack terms htube hbudget hslack hcert

/--
Uniform coverage over a family of candidate trajectory segments.

This is the next formalization target after 5BQ/5BR: for every sufficiently
intense candidate return segment, prove either exposure or in-tube sterility.
-/
theorem no_growth_bearing_of_uniform_stealth_coverage
    {ι : Type} (state : ι → StealthGrowthState)
    (eps derivBound torqueFloor : ℝ)
    (slack : ι → ℝ) (terms : ι → List ℝ)
    (hbudget : ∀ i, enstrophyBudgetConsistent (state i))
    (hexposed : ∀ i, exposedStateNotGrowthBearing (state i) eps derivBound torqueFloor)
    (hcover :
      ∀ i, stealthCoverageAlternative
        (state i) eps derivBound torqueFloor (slack i) (terms i))
    (i : ι) :
    ¬ growthBearingSegment (state i) := by
  exact no_growth_bearing_of_stealth_coverage_alternative
    (state i) eps derivBound torqueFloor (slack i) (terms i)
    (hbudget i) (hexposed i) (hcover i)

end

end ZtareProofs.NS
