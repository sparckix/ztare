import Mathlib.Tactic
import ZtareProofs.ns_section_dichotomy
import ZtareProofs.ns_sos_section_margin_bridge

/-!
# Core/tail budget bridge

This file records the finite-to-continuum split suggested by Phase 5BO/5BP.

The intended proof architecture is:

* a finite low/mid-frequency core is certified by an SOS receipt;
* the high-frequency tail is loss-dominant because the Stokes/Laplacian cost
  grows quadratically in frequency;
* low-high leakage is explicitly bounded, rather than hidden in prose;
* the combined budget routes into the existing section dichotomy.

The PDE content is isolated in hypotheses such as
`tailBudgetNonpositive` and `lowHighLeakageControlled`.  This prevents the
finite certificate from being laundered into a continuum theorem before the
interaction constants are actually paid.
-/

namespace ZtareProofs

noncomputable section

/-- A split section-cycle budget: certified core, high-frequency tail, and
low/high interaction leakage. -/
structure CoreTailBudget where
  coreGain : ℝ
  coreLoss : ℝ
  tailGain : ℝ
  tailLoss : ℝ
  leakageGain : ℝ
  leakageLoss : ℝ

/-- Total danger gain after splitting core, tail, and leakage channels. -/
def CoreTailBudget.totalGain (B : CoreTailBudget) : ℝ :=
  B.coreGain + B.tailGain + B.leakageGain

/-- Total reset loss after splitting core, tail, and leakage channels. -/
def CoreTailBudget.totalLoss (B : CoreTailBudget) : ℝ :=
  B.coreLoss + B.tailLoss + B.leakageLoss

/-- The finite SOS/core certificate supplies nonpositive core budget. -/
def coreBudgetNonpositive (B : CoreTailBudget) : Prop :=
  B.coreGain ≤ B.coreLoss

/-- The high-frequency tail is loss-dominant. -/
def tailBudgetNonpositive (B : CoreTailBudget) : Prop :=
  B.tailGain ≤ B.tailLoss

/-- Low/high interaction leakage is explicitly paid for by an interaction loss. -/
def lowHighLeakageControlled (B : CoreTailBudget) : Prop :=
  B.leakageGain ≤ B.leakageLoss

/-- Core, tail, and leakage controls combine into total loss dominance. -/
theorem total_budget_nonpositive_of_core_tail_leakage
    (B : CoreTailBudget)
    (hcore : coreBudgetNonpositive B)
    (htail : tailBudgetNonpositive B)
    (hleak : lowHighLeakageControlled B) :
    B.totalGain ≤ B.totalLoss := by
  unfold coreBudgetNonpositive tailBudgetNonpositive lowHighLeakageControlled at *
  unfold CoreTailBudget.totalGain CoreTailBudget.totalLoss
  linarith

/--
The Stokes-tail scalar shape: if the nonlinear tail gain coefficient is bounded
by `Ctail * k`, and viscous loss is bounded below by `ν * k^2`, then the tail is
nonpositive whenever `Ctail ≤ ν * k`.

This is deliberately scalar.  A later PDE lemma must instantiate `k` as the
lowest active tail frequency and prove the gain/loss estimates from Sobolev or
Fourier product bounds.
-/
theorem stokes_tail_scalar_domination
    {Ctail ν k tailGain tailLoss : ℝ}
    (hgain : tailGain ≤ Ctail * k)
    (hloss : ν * k * k ≤ tailLoss)
    (hk_nonneg : 0 ≤ k)
    (hscale : Ctail ≤ ν * k) :
    tailGain ≤ tailLoss := by
  have hmul : Ctail * k ≤ (ν * k) * k := mul_le_mul_of_nonneg_right hscale hk_nonneg
  have hmul' : Ctail * k ≤ ν * k * k := by
    simpa [mul_assoc] using hmul
  linarith

/-- A cycle-level representation of the split budget. -/
structure CoreTailBudgetRepresentsCycle
    (B : CoreTailBudget) (C : EigenframeCycleWitness) : Prop where
  gain_eq : B.totalGain = C.dangerGain
  loss_eq : B.totalLoss = C.resetLoss

/--
If the split budget represents an eigenframe cycle and every split channel is
loss-dominant, then the cycle has toxic-block margin.
-/
theorem toxic_block_cycle_margin_of_core_tail_budget
    (B : CoreTailBudget) (C : EigenframeCycleWitness)
    (hrep : CoreTailBudgetRepresentsCycle B C)
    (hcore : coreBudgetNonpositive B)
    (htail : tailBudgetNonpositive B)
    (hleak : lowHighLeakageControlled B) :
    toxicBlockMarginControlsCycle C := by
  unfold toxicBlockMarginControlsCycle
  have htotal := total_budget_nonpositive_of_core_tail_leakage B hcore htail hleak
  rw [hrep.gain_eq, hrep.loss_eq] at htotal
  exact htotal

/--
Uniform core/tail/leakage budgets close the section dichotomy.

This is the exact bridge that lets the Phase 5BO finite certificate coexist
with a continuum tail argument without pretending either half proves the other.
-/
theorem section_dichotomy_of_uniform_core_tail_budgets
    {S : EigenframeSection} {EStar : ℝ} {Seq : CycleSeq}
    (chooseBudget : EigenframeCycleWitness → CoreTailBudget)
    (hrep :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        CoreTailBudgetRepresentsCycle (chooseBudget C) C)
    (hcore :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        coreBudgetNonpositive (chooseBudget C))
    (htail :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        tailBudgetNonpositive (chooseBudget C))
    (hleak :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        lowHighLeakageControlled (chooseBudget C)) :
    sectionDichotomy S EStar Seq := by
  apply section_dichotomy_of_toxic_block_cycle_margin
  intro C hhigh
  exact toxic_block_cycle_margin_of_core_tail_budget (chooseBudget C) C
    (hrep C hhigh) (hcore C hhigh) (htail C hhigh) (hleak C hhigh)

end

end ZtareProofs
