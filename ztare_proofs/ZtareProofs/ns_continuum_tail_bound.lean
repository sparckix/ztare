import Mathlib.Tactic
import ZtareProofs.ns_core_tail_budget_bridge

/-!
# Continuum tail bound interface

Phase 5BP supports a fixed-`N` substitution-portability claim for the toxic
block.  It does **not** by itself prove a continuum Navier-Stokes statement.

This file isolates the remaining continuum bridge as a small set of scalar
obligations:

1. an SOS/core certificate controls the finite core;
2. a Fourier/Sobolev estimate bounds nonlinear tail gain by a lower-order
   constant times the tail frequency;
3. Stokes dissipation bounds tail loss below by `ν k^2`;
4. low/high leakage is either directly controlled or absorbed by a reserve
   loss channel.

The theorem here is intentionally an adapter, not the PDE estimate itself.
It is the exact place where a future analytic lemma must pay the constants.
-/

namespace ZtareProofs

noncomputable section

/-- Scalar estimates needed to turn the high-frequency tail into a
loss-dominant budget channel. -/
structure TailDominationEstimate where
  nonlinearCoeff : ℝ
  viscosity : ℝ
  tailFrequency : ℝ
  gainUpper : ℝ
  lossLower : ℝ

/--
The estimate is in the dissipative regime when the lowest tail frequency is
large enough that `ν k` dominates the nonlinear coefficient.
-/
def TailDominationEstimate.dissipativeRegime (T : TailDominationEstimate) : Prop :=
  T.nonlinearCoeff ≤ T.viscosity * T.tailFrequency

/-- The nonlinear tail-gain estimate has been paid. -/
def TailDominationEstimate.gainEstimate
    (T : TailDominationEstimate) (B : CoreTailBudget) : Prop :=
  B.tailGain ≤ T.nonlinearCoeff * T.tailFrequency

/-- The Stokes/Laplacian tail-loss estimate has been paid. -/
def TailDominationEstimate.lossEstimate
    (T : TailDominationEstimate) (B : CoreTailBudget) : Prop :=
  T.viscosity * T.tailFrequency * T.tailFrequency ≤ B.tailLoss

/--
Tail domination follows from the scalar Stokes-vs-nonlinear estimates.

This is the precise replacement for the informal phrase "`ν k^2` beats `k`":
the frequency threshold and constants are explicit.
-/
theorem tail_budget_nonpositive_of_tail_domination_estimate
    (B : CoreTailBudget) (T : TailDominationEstimate)
    (hgain : T.gainEstimate B)
    (hloss : T.lossEstimate B)
    (hk : 0 ≤ T.tailFrequency)
    (hregime : T.dissipativeRegime) :
    tailBudgetNonpositive B := by
  unfold tailBudgetNonpositive
  unfold TailDominationEstimate.gainEstimate at hgain
  unfold TailDominationEstimate.lossEstimate at hloss
  unfold TailDominationEstimate.dissipativeRegime at hregime
  exact stokes_tail_scalar_domination hgain hloss hk hregime

/-- A reserve channel that can absorb low/high leakage. -/
structure LeakageAbsorptionEstimate where
  leakageUpper : ℝ
  reserveLossLower : ℝ

/-- The leakage estimate has been paid for the budget. -/
def LeakageAbsorptionEstimate.represents
    (L : LeakageAbsorptionEstimate) (B : CoreTailBudget) : Prop :=
  B.leakageGain ≤ L.leakageUpper ∧ L.reserveLossLower ≤ B.leakageLoss

/-- Leakage is controlled when its upper bound is no larger than the reserved
loss lower bound. -/
def LeakageAbsorptionEstimate.absorbing
    (L : LeakageAbsorptionEstimate) : Prop :=
  L.leakageUpper ≤ L.reserveLossLower

/--
Low/high leakage control follows from an explicit absorption reserve.

This keeps the referee attack surface honest: the proof must pay either a
direct leakage inequality or a reserve-loss inequality.
-/
theorem low_high_leakage_controlled_of_absorption
    (B : CoreTailBudget) (L : LeakageAbsorptionEstimate)
    (hrep : L.represents B)
    (habsorb : L.absorbing) :
    lowHighLeakageControlled B := by
  unfold lowHighLeakageControlled
  unfold LeakageAbsorptionEstimate.represents at hrep
  unfold LeakageAbsorptionEstimate.absorbing at habsorb
  rcases hrep with ⟨hgain, hloss⟩
  linarith

/--
Core SOS margin + continuum tail domination + leakage absorption close a cycle.

This is the theorem-shaped continuum bridge after Phase 5BP.  It is not a
claim that the estimates are already available; it records the minimal
interfaces they must satisfy.
-/
theorem toxic_block_cycle_margin_of_core_sos_tail_and_leakage
    (B : CoreTailBudget) (C : EigenframeCycleWitness)
    (T : TailDominationEstimate) (L : LeakageAbsorptionEstimate)
    (hrepCycle : CoreTailBudgetRepresentsCycle B C)
    (hcore : coreBudgetNonpositive B)
    (hTailGain : T.gainEstimate B)
    (hTailLoss : T.lossEstimate B)
    (hk : 0 ≤ T.tailFrequency)
    (hTailRegime : T.dissipativeRegime)
    (hLeakRep : L.represents B)
    (hLeakAbsorb : L.absorbing) :
    toxicBlockMarginControlsCycle C := by
  have htail : tailBudgetNonpositive B :=
    tail_budget_nonpositive_of_tail_domination_estimate B T hTailGain hTailLoss hk hTailRegime
  have hleak : lowHighLeakageControlled B :=
    low_high_leakage_controlled_of_absorption B L hLeakRep hLeakAbsorb
  exact toxic_block_cycle_margin_of_core_tail_budget B C hrepCycle hcore htail hleak

/--
Uniform version for the section dichotomy.

This is the exact finite-core-to-continuum proof skeleton:
choose a split budget, a tail estimate, and a leakage reserve for every
sufficiently intense return; then the existing section dichotomy resolves to
the loss-dominant side.
-/
theorem section_dichotomy_of_uniform_core_tail_continuum_estimates
    {S : EigenframeSection} {EStar : ℝ} {Seq : CycleSeq}
    (chooseBudget : EigenframeCycleWitness → CoreTailBudget)
    (chooseTail : EigenframeCycleWitness → TailDominationEstimate)
    (chooseLeakage : EigenframeCycleWitness → LeakageAbsorptionEstimate)
    (hrepCycle :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        CoreTailBudgetRepresentsCycle (chooseBudget C) C)
    (hcore :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        coreBudgetNonpositive (chooseBudget C))
    (hTailGain :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        (chooseTail C).gainEstimate (chooseBudget C))
    (hTailLoss :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        (chooseTail C).lossEstimate (chooseBudget C))
    (hk :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        0 ≤ (chooseTail C).tailFrequency)
    (hTailRegime :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        (chooseTail C).dissipativeRegime)
    (hLeakRep :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        (chooseLeakage C).represents (chooseBudget C))
    (hLeakAbsorb :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        (chooseLeakage C).absorbing) :
    sectionDichotomy S EStar Seq := by
  apply section_dichotomy_of_toxic_block_cycle_margin
  intro C hhigh
  exact toxic_block_cycle_margin_of_core_sos_tail_and_leakage
    (chooseBudget C) C (chooseTail C) (chooseLeakage C)
    (hrepCycle C hhigh)
    (hcore C hhigh)
    (hTailGain C hhigh)
    (hTailLoss C hhigh)
    (hk C hhigh)
    (hTailRegime C hhigh)
    (hLeakRep C hhigh)
    (hLeakAbsorb C hhigh)

end

end ZtareProofs
