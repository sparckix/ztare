import Mathlib.Tactic
import ZtareProofs.ns_continuum_tail_bound
import ZtareProofs.ns_stealth_coverage_section_bridge

/-!
# Asymptotic margin extraction

The Phase 5BS high-`N` rows are evidence for the expected scaling direction:
recovered stealth states at `N = 96` have materially positive toxic-block
margins and negative net budgets.

But a finite ladder is not a continuum proof.  A hostile PDE referee can ask:

> What stops low/high leakage, which may scale like `k`, from overtaking the
> observed toxic-block margin at larger `k`?

This file records the exact formal answer.  The proof spine needs a scalar
asymptotic inequality.  There are two admissible ways to pay it:

* leakage gain is bounded above by `C * k`;
* viscous/toxic margin is bounded below by `ν * k^2`;
* the tail frequency is above the explicit threshold `C ≤ ν * k`.

or, more directly:

* the normalized toxic-block reserve exceeds normalized leakage by a uniform
  positive floor `δ`.

The first route is exponent separation.  The second route is scale-invariant
constant margin.  Phase 5BT did not certify the first route; Phase 5BS makes
the second route the cleaner formal target.  The GPU data estimates and
falsifies candidate constants; Lean checks only the resulting inequalities.
-/

namespace ZtareProofs

open ZtareProofs.NS

noncomputable section

/--
Scalar asymptotic margin model for one high-frequency channel.

`leakageGain` is the low/high nonlinear transfer the rival tries to use.
`taxMargin` is the viscous/toxic-block margin available to absorb it.
`leakageCoeff * k` is the linear leakage upper bound.
`viscosity * k^2` is the quadratic tax lower bound.
-/
structure AsymptoticMarginEstimate where
  leakageGain : ℝ
  taxMargin : ℝ
  leakageCoeff : ℝ
  viscosity : ℝ
  frequency : ℝ

/-- The linear leakage estimate has been paid. -/
def AsymptoticMarginEstimate.linearLeakageBound
    (A : AsymptoticMarginEstimate) : Prop :=
  A.leakageGain ≤ A.leakageCoeff * A.frequency

/-- The quadratic tax estimate has been paid. -/
def AsymptoticMarginEstimate.quadraticTaxBound
    (A : AsymptoticMarginEstimate) : Prop :=
  A.viscosity * A.frequency * A.frequency ≤ A.taxMargin

/-- The channel is beyond the minimum efficient spectral scale. -/
def AsymptoticMarginEstimate.aboveCriticalFrequency
    (A : AsymptoticMarginEstimate) : Prop :=
  A.leakageCoeff ≤ A.viscosity * A.frequency

/--
Scale-invariant constant-margin model for one high-frequency channel.

This is the formal version of the Phase 5BS/5BT pivot: a margin does not need
to grow with frequency if it is uniformly positive in the normalized variables
that represent the leakage/tax budget.

`scale` is the normalization weight for the channel.  In a concrete PDE
instantiation it may be an energy, enstrophy, or block-coordinate norm.  Lean
does not choose it; the analytic bridge must.
-/
structure ConstantMarginEstimate where
  leakageGain : ℝ
  taxMargin : ℝ
  marginFloor : ℝ
  scale : ℝ

/-- The normalized reserve exceeds leakage by a uniform floor. -/
def ConstantMarginEstimate.uniformPositiveMargin
    (M : ConstantMarginEstimate) : Prop :=
  M.leakageGain + M.marginFloor * M.scale ≤ M.taxMargin

/-- The floor is genuinely positive on a nonnegative scale. -/
def ConstantMarginEstimate.validFloor
    (M : ConstantMarginEstimate) : Prop :=
  0 < M.marginFloor ∧ 0 ≤ M.scale

/--
Quadratic tax dominates linear leakage above the explicit critical frequency.

This is the formal replacement for the business shorthand "`k^2` beats `k`".
The constants are not hidden: a future analytic/SOS step must provide
`leakageCoeff`, `viscosity`, and the threshold inequality.
-/
theorem tax_margin_dominates_linear_leakage
    (A : AsymptoticMarginEstimate)
    (hleak : A.linearLeakageBound)
    (htax : A.quadraticTaxBound)
    (hk : 0 ≤ A.frequency)
    (hcrit : A.aboveCriticalFrequency) :
    A.leakageGain ≤ A.taxMargin := by
  unfold AsymptoticMarginEstimate.linearLeakageBound at hleak
  unfold AsymptoticMarginEstimate.quadraticTaxBound at htax
  unfold AsymptoticMarginEstimate.aboveCriticalFrequency at hcrit
  have hscaled :
      A.leakageCoeff * A.frequency ≤
        (A.viscosity * A.frequency) * A.frequency :=
    mul_le_mul_of_nonneg_right hcrit hk
  have hscaled' :
      A.leakageCoeff * A.frequency ≤
        A.viscosity * A.frequency * A.frequency := by
    simpa [mul_assoc] using hscaled
  linarith

/--
A uniform positive normalized margin is already enough to control leakage.

This is intentionally weaker than an exponent-gap theorem.  It captures the
case where leakage and tax scale in the same way, but their normalized
difference stays bounded below by `δ > 0`.
-/
theorem tax_margin_dominates_leakage_of_constant_margin
    (M : ConstantMarginEstimate)
    (hmargin : M.uniformPositiveMargin)
    (hfloor : M.validFloor) :
    M.leakageGain ≤ M.taxMargin := by
  unfold ConstantMarginEstimate.uniformPositiveMargin at hmargin
  unfold ConstantMarginEstimate.validFloor at hfloor
  rcases hfloor with ⟨hδ, hscale⟩
  have hδ_nonneg : 0 ≤ M.marginFloor := le_of_lt hδ
  have hprod : 0 ≤ M.marginFloor * M.scale := mul_nonneg hδ_nonneg hscale
  linarith

/-- Route the asymptotic margin estimate into the existing leakage budget
predicate. -/
theorem leakage_controlled_of_asymptotic_margin
    (B : CoreTailBudget) (A : AsymptoticMarginEstimate)
    (hrepGain : B.leakageGain ≤ A.leakageGain)
    (hrepLoss : A.taxMargin ≤ B.leakageLoss)
    (hleak : A.linearLeakageBound)
    (htax : A.quadraticTaxBound)
    (hk : 0 ≤ A.frequency)
    (hcrit : A.aboveCriticalFrequency) :
    lowHighLeakageControlled B := by
  unfold lowHighLeakageControlled
  have hmargin : A.leakageGain ≤ A.taxMargin :=
    tax_margin_dominates_linear_leakage A hleak htax hk hcrit
  linarith

/-- Route a scale-invariant constant-margin estimate into the leakage budget. -/
theorem leakage_controlled_of_constant_margin
    (B : CoreTailBudget) (M : ConstantMarginEstimate)
    (hrepGain : B.leakageGain ≤ M.leakageGain)
    (hrepLoss : M.taxMargin ≤ B.leakageLoss)
    (hmargin : M.uniformPositiveMargin)
    (hfloor : M.validFloor) :
    lowHighLeakageControlled B := by
  unfold lowHighLeakageControlled
  have hmargin' : M.leakageGain ≤ M.taxMargin :=
    tax_margin_dominates_leakage_of_constant_margin M hmargin hfloor
  linarith

/--
Tail domination and leakage domination from the same asymptotic threshold close
the core/tail budget.

This theorem is intentionally scalar.  It makes the remaining continuum bridge
auditable: pay `coreBudgetNonpositive`, pay the Fourier/Sobolev tail estimates,
pay the linear-leakage/quadratic-tax estimates, and the cycle margin follows.
-/
theorem toxic_block_cycle_margin_of_asymptotic_margin_estimates
    (B : CoreTailBudget) (C : EigenframeCycleWitness)
    (T : TailDominationEstimate) (A : AsymptoticMarginEstimate)
    (hrepCycle : CoreTailBudgetRepresentsCycle B C)
    (hcore : coreBudgetNonpositive B)
    (hTailGain : T.gainEstimate B)
    (hTailLoss : T.lossEstimate B)
    (htailFreq : 0 ≤ T.tailFrequency)
    (hTailRegime : T.dissipativeRegime)
    (hLeakRepGain : B.leakageGain ≤ A.leakageGain)
    (hLeakRepLoss : A.taxMargin ≤ B.leakageLoss)
    (hLeakLinear : A.linearLeakageBound)
    (hTaxQuad : A.quadraticTaxBound)
    (hFreq : 0 ≤ A.frequency)
    (hCrit : A.aboveCriticalFrequency) :
    toxicBlockMarginControlsCycle C := by
  have htail : tailBudgetNonpositive B :=
    tail_budget_nonpositive_of_tail_domination_estimate
      B T hTailGain hTailLoss htailFreq hTailRegime
  have hleak : lowHighLeakageControlled B :=
    leakage_controlled_of_asymptotic_margin
      B A hLeakRepGain hLeakRepLoss hLeakLinear hTaxQuad hFreq hCrit
  exact toxic_block_cycle_margin_of_core_tail_budget B C hrepCycle hcore htail hleak

/--
Constant normalized leakage margin closes the core/tail budget without an
exponent gap.

Use this theorem when the empirical/analytic object is a scale-invariant
positive floor rather than `k^2` asymptotic separation.
-/
theorem toxic_block_cycle_margin_of_constant_margin_estimates
    (B : CoreTailBudget) (C : EigenframeCycleWitness)
    (T : TailDominationEstimate) (M : ConstantMarginEstimate)
    (hrepCycle : CoreTailBudgetRepresentsCycle B C)
    (hcore : coreBudgetNonpositive B)
    (hTailGain : T.gainEstimate B)
    (hTailLoss : T.lossEstimate B)
    (htailFreq : 0 ≤ T.tailFrequency)
    (hTailRegime : T.dissipativeRegime)
    (hLeakRepGain : B.leakageGain ≤ M.leakageGain)
    (hLeakRepLoss : M.taxMargin ≤ B.leakageLoss)
    (hConstantMargin : M.uniformPositiveMargin)
    (hFloor : M.validFloor) :
    toxicBlockMarginControlsCycle C := by
  have htail : tailBudgetNonpositive B :=
    tail_budget_nonpositive_of_tail_domination_estimate
      B T hTailGain hTailLoss htailFreq hTailRegime
  have hleak : lowHighLeakageControlled B :=
    leakage_controlled_of_constant_margin
      B M hLeakRepGain hLeakRepLoss hConstantMargin hFloor
  exact toxic_block_cycle_margin_of_core_tail_budget B C hrepCycle hcore htail hleak

end

end ZtareProofs
