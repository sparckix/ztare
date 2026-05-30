import Mathlib.Tactic
import ZtareProofs.ns_commutator_tower_defect_budget

namespace ZtareProofs

/-!
`ns_commutator_tower_irreducible_estimate` records the exact scalar estimate
route `1` now reduces to.

After the previous compressions, the branch no longer needs a vague
"commutator tower argument". It needs one irreducible estimate:

> the pressure-side defect budget must be subcritical relative to the current
> tower level by a ratio strictly below one.

Everything else in route `1` is now bookkeeping around that statement.
-/

/--
Irreducible route-1 estimate: the defect budget is a strict fraction of the
current tower level.
-/
def defectBudgetSubcriticalityEstimate
    (budget currentStep ratio : Real) : Prop :=
  0 ≤ budget ∧
    0 ≤ currentStep ∧
    0 ≤ ratio ∧
    ratio < 1 ∧
    budget ≤ ratio * currentStep

/--
Strict-margin certificate for the route-1 subcriticality estimate.

This is deliberately stronger than `defectBudgetSubcriticalityEstimate`: it
requires an explicit positive gap both below the endpoint ratio `1` and below
the budget-facing contraction bound. The analytic work is still the production
of this margin certificate.
-/
def defectBudgetStrictMarginCertificate
    (budget currentStep ratio margin : Real) : Prop :=
  0 < margin ∧
    0 ≤ budget ∧
    0 ≤ currentStep ∧
    0 ≤ ratio ∧
    ratio + margin ≤ 1 ∧
    budget + margin ≤ ratio * currentStep

/--
Endpoint slack channel for the strict route-1 margin.

This is the part that keeps the contraction ratio genuinely below the endpoint
`1`.
-/
def endpointRatioSlack
    (ratio margin : Real) : Prop :=
  0 < margin ∧
    0 ≤ ratio ∧
    ratio + margin ≤ 1

/--
Budget-facing slack channel for the strict route-1 margin.

This is the part that pays the actual defect budget below the current tower
level. It is separate from endpoint slack because the endpoint gap alone does
not control the pressure-side budget.
-/
def budgetContractionSlack
    (budget currentStep ratio margin : Real) : Prop :=
  0 ≤ budget ∧
    0 ≤ currentStep ∧
    budget + margin ≤ ratio * currentStep

/--
Strict full-budget subcriticality produces a positive budget-contraction
margin.

The chosen margin is half the gap between the contraction capacity
`ratio * currentStep` and the actual budget.
-/
theorem exists_budgetContractionSlack_of_strict_budget_subcriticality
    {budget currentStep ratio : Real}
    (hb : 0 ≤ budget)
    (hc : 0 ≤ currentStep)
    (hstrict : budget < ratio * currentStep) :
    ∃ budgetMargin : Real,
      0 < budgetMargin ∧
        budgetContractionSlack budget currentStep ratio budgetMargin := by
  refine ⟨(ratio * currentStep - budget) / 2, ?_⟩
  constructor
  · linarith
  · refine ⟨hb, hc, ?_⟩
    linarith

/--
A strict subratio budget bound produces positive budget-contraction slack for
the larger route ratio.

This is the useful scalar bridge above the raw strict inequality: if the budget
is controlled at `ratio'` and `ratio' < ratio`, then the gap between the two
ratios pays an additive budget margin.
-/
theorem exists_budgetContractionSlack_of_strict_subratio_bound
    {budget currentStep ratio ratio' : Real}
    (hb : 0 ≤ budget)
    (hcpos : 0 < currentStep)
    (hgap : ratio' < ratio)
    (hbudget : budget ≤ ratio' * currentStep) :
    ∃ budgetMargin : Real,
      0 < budgetMargin ∧
        budgetContractionSlack budget currentStep ratio budgetMargin := by
  refine ⟨((ratio - ratio') * currentStep) / 2, ?_⟩
  have hc : 0 ≤ currentStep := le_of_lt hcpos
  have hgapPos : 0 < (ratio - ratio') * currentStep := by
    nlinarith
  constructor
  · nlinarith
  · refine ⟨hb, hc, ?_⟩
    nlinarith

/--
Anti-wrapper guard: a non-strict budget subcriticality estimate alone cannot
pay any positive additive budget slack.
-/
theorem nonstrict_budget_subcriticality_does_not_imply_positive_budget_slack :
    ¬ (∀ budget currentStep ratio margin : Real,
      0 < margin →
        budget ≤ ratio * currentStep →
          budget + margin ≤ ratio * currentStep) := by
  intro h
  have hbad := h 0 0 0 1 (by norm_num) (by norm_num)
  norm_num at hbad

/--
A strict ratio bound mechanically supplies endpoint slack.

The chosen margin is half the remaining gap to the endpoint `1`.
-/
theorem endpointRatioSlack_of_strict_ratio
    {ratio : Real}
    (hr0 : 0 ≤ ratio)
    (hr1 : ratio < 1) :
    endpointRatioSlack ratio ((1 - ratio) / 2) := by
  refine ⟨?_, hr0, ?_⟩
  · linarith
  · linarith

/--
The strict route-1 margin certificate is exactly the conjunction of endpoint
ratio slack and budget-facing contraction slack.

This is only a scalar target split. It does not prove either analytic channel.
-/
theorem defectBudgetStrictMarginCertificate_of_endpoint_and_budget_slack
    {budget currentStep ratio margin : Real}
    (hend : endpointRatioSlack ratio margin)
    (hbudget : budgetContractionSlack budget currentStep ratio margin) :
    defectBudgetStrictMarginCertificate budget currentStep ratio margin := by
  rcases hend with ⟨hm, hr0, hendpoint⟩
  rcases hbudget with ⟨hb, hc, hbudgetBound⟩
  exact ⟨hm, hb, hc, hr0, hendpoint, hbudgetBound⟩

/--
Separate endpoint and budget margins can be reconciled by taking their minimum.

This removes an artificial fixed-margin coupling requirement: downstream
analytic work may produce one positive endpoint margin and one positive budget
margin, then use their minimum as the shared strict certificate margin.
-/
theorem defectBudgetStrictMarginCertificate_of_separate_endpoint_and_budget_slack
    {budget currentStep ratio endpointMargin budgetMargin : Real}
    (hend : endpointRatioSlack ratio endpointMargin)
    (hbudgetMargin : 0 < budgetMargin)
    (hbudget :
      budgetContractionSlack budget currentStep ratio budgetMargin) :
    defectBudgetStrictMarginCertificate
      budget currentStep ratio (min endpointMargin budgetMargin) := by
  rcases hend with ⟨hendPos, hr0, hendpoint⟩
  rcases hbudget with ⟨hb, hc, hbudgetBound⟩
  have hminPos : 0 < min endpointMargin budgetMargin := by
    exact lt_min hendPos hbudgetMargin
  have hendpointMin :
      ratio + min endpointMargin budgetMargin ≤ 1 := by
    have hle : min endpointMargin budgetMargin ≤ endpointMargin :=
      min_le_left endpointMargin budgetMargin
    linarith
  have hbudgetMin :
      budget + min endpointMargin budgetMargin ≤ ratio * currentStep := by
    have hle : min endpointMargin budgetMargin ≤ budgetMargin :=
      min_le_right endpointMargin budgetMargin
    linarith
  exact ⟨hminPos, hb, hc, hr0, hendpointMin, hbudgetMin⟩

/--
Strict ratio plus positive budget slack pays the full route-1 strict-margin
certificate.

After v17.21, endpoint slack is automatic from `ratio < 1`; the only remaining
scalar producer is the positive budget-contraction margin.
-/
theorem defectBudgetStrictMarginCertificate_of_strict_ratio_and_budget_slack
    {budget currentStep ratio budgetMargin : Real}
    (hr0 : 0 ≤ ratio)
    (hr1 : ratio < 1)
    (hbudgetMargin : 0 < budgetMargin)
    (hbudget :
      budgetContractionSlack budget currentStep ratio budgetMargin) :
    defectBudgetStrictMarginCertificate
      budget currentStep ratio (min ((1 - ratio) / 2) budgetMargin) := by
  exact
    defectBudgetStrictMarginCertificate_of_separate_endpoint_and_budget_slack
      (endpointRatioSlack_of_strict_ratio hr0 hr1)
      hbudgetMargin
      hbudget

/--
Anti-collapse guard: endpoint ratio slack alone does not pay the budget-facing
contraction slack, even with nonnegative budget/current-step data.
-/
theorem endpointRatioSlack_does_not_imply_budgetContractionSlack :
    ∃ budget currentStep ratio margin : Real,
      endpointRatioSlack ratio margin ∧
        0 ≤ budget ∧
        0 ≤ currentStep ∧
        ¬ budgetContractionSlack budget currentStep ratio margin := by
  refine ⟨1, 0, (1 / 2), (1 / 4), ?_⟩
  norm_num [endpointRatioSlack, budgetContractionSlack]

/--
Anti-collapse guard: budget-facing contraction slack alone does not pay the
endpoint ratio slack.
-/
theorem budgetContractionSlack_does_not_imply_endpointRatioSlack :
    ∃ budget currentStep ratio margin : Real,
      budgetContractionSlack budget currentStep ratio margin ∧
        0 < margin ∧
        0 ≤ ratio ∧
        ¬ endpointRatioSlack ratio margin := by
  refine ⟨0, 1, 2, 1, ?_⟩
  norm_num [endpointRatioSlack, budgetContractionSlack]

/--
A positive scalar margin pays the irreducible route-1 subcriticality estimate.

This theorem only decomposes the target. It does not prove the analytic margin.
-/
theorem defectBudgetSubcriticalityEstimate_of_strictMarginCertificate
    {budget currentStep ratio margin : Real}
    (h :
      defectBudgetStrictMarginCertificate
        budget currentStep ratio margin) :
    defectBudgetSubcriticalityEstimate budget currentStep ratio := by
  rcases h with ⟨hm, hb, hc, hr0, hratio, hbudget⟩
  refine ⟨hb, hc, hr0, ?_, ?_⟩
  · linarith
  · linarith

/--
Translate the budget-facing subcriticality estimate into the radial-grade
ratio atom used by the stepwise commutator target.

This is only an interface adapter: it still requires the subcritical budget
estimate with `budget = kernelGain + multiplierGain` and
`currentStep = max radialGrade 1`.
-/
theorem radialGradeExtractsTowerRatio_of_defectBudgetSubcriticalityEstimate
    {radialGrade kernelGain multiplierGain ratio : Real}
    (hkg : 0 ≤ kernelGain)
    (hmg : 0 ≤ multiplierGain)
    (hsub :
      defectBudgetSubcriticalityEstimate
        (kernelGain + multiplierGain) (max radialGrade 1) ratio) :
    radialGradeExtractsTowerRatio radialGrade kernelGain multiplierGain ratio := by
  rcases hsub with ⟨_, _, hr0, hr1, hbound⟩
  exact ⟨hkg, hmg, hr0, hr1, hbound⟩

/--
Strict-margin route into the radial-grade ratio atom used by the stepwise
commutator target.

The remaining unpaid scalar duty is now the explicit margin certificate for
`kernelGain + multiplierGain` against `max radialGrade 1`.
-/
theorem radialGradeExtractsTowerRatio_of_strictBudgetMarginCertificate
    {radialGrade kernelGain multiplierGain ratio margin : Real}
    (hkg : 0 ≤ kernelGain)
    (hmg : 0 ≤ multiplierGain)
    (hmargin :
      defectBudgetStrictMarginCertificate
        (kernelGain + multiplierGain) (max radialGrade 1) ratio margin) :
    radialGradeExtractsTowerRatio radialGrade kernelGain multiplierGain ratio := by
  exact radialGradeExtractsTowerRatio_of_defectBudgetSubcriticalityEstimate
    hkg hmg
    (defectBudgetSubcriticalityEstimate_of_strictMarginCertificate hmargin)

/--
If the budget is already subcritical relative to the current tower level, then
it yields the budget-facing contraction target for any admissible next step
fed by that budget.
-/
theorem budgetFacingContractionTarget_of_subcriticality
    {budget currentStep nextStep ratio : Real}
    (hsub :
      defectBudgetSubcriticalityEstimate budget currentStep ratio)
    (hfeed :
      defectBudgetFeedsNextTowerStep budget nextStep) :
    budgetFacingContractionTarget budget currentStep nextStep ratio := by
  rcases hsub with ⟨hb, hc, hr0, hr1, hsubcrit⟩
  rcases hfeed with ⟨_, hn, hnext⟩
  refine ⟨?_, hr0, hr1, ?_⟩
  · refine ⟨hb, by positivity, ?_⟩
    simpa using hnext
  · nlinarith

/--
Strict-margin route into the budget-facing contraction target.

This is the route-1 close-or-gap split: after the pressure-side budget feeds the
next tower step, the only scalar analytic atom is the explicit positive margin
certificate below.
-/
theorem budgetFacingContractionTarget_of_strictMarginCertificate
    {budget currentStep nextStep ratio margin : Real}
    (hmargin :
      defectBudgetStrictMarginCertificate budget currentStep ratio margin)
    (hfeed :
      defectBudgetFeedsNextTowerStep budget nextStep) :
    budgetFacingContractionTarget budget currentStep nextStep ratio := by
  exact budgetFacingContractionTarget_of_subcriticality
    (defectBudgetSubcriticalityEstimate_of_strictMarginCertificate hmargin)
    hfeed

/--
This is the cleanest current route-1 target in repo-native terms.

Interpretation:
- first pay the pressure transport obligation,
- then pay the defect budget target,
- finally prove subcriticality of that budget against the current tower level.
-/
def route1IrreducibleNextTarget
    (stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio : Real) : Prop :=
  pressureL2TransportDefectObligation
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual ∧
    route1DefectBudgetTarget
      transportDefect localQuadratic advectedPressure commutatorResidual budget nextStep ∧
    defectBudgetSubcriticalityEstimate budget currentStep ratio

/--
Strict-margin variant of the current route-1 irreducible target.

This makes the next scalar atom explicit at the route-1 target level rather
than hiding it inside `defectBudgetSubcriticalityEstimate`.
-/
def route1StrictMarginNextTarget
    (stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio margin : Real) : Prop :=
  pressureL2TransportDefectObligation
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual ∧
    route1DefectBudgetTarget
      transportDefect localQuadratic advectedPressure commutatorResidual budget nextStep ∧
    defectBudgetStrictMarginCertificate budget currentStep ratio margin

/--
Endpoint commutator-defect visibility.

At the endpoint, the commutator defect may be reduced only by an explicitly
named strong-tail compactness loss. This is intentionally weaker than any
strict budget or subratio claim: it only says which quantity must stay visible.
-/
structure EndpointCommutatorDefectVisibility
    (endpointDefect commutatorDefect compactTailLoss : Real) : Prop where
  endpoint_nonnegative : 0 ≤ endpointDefect
  commutator_nonnegative : 0 ≤ commutatorDefect
  compact_tail_loss_nonnegative : 0 ≤ compactTailLoss
  endpoint_visible : endpointDefect ≤ commutatorDefect + compactTailLoss

/--
No-escape obligation for the endpoint commutator channel.

The possible escape channels are deliberately named as endpoint-facing losses.
The obligation says their total must be charged to the visible endpoint defect,
not hidden inside a source-budget subratio.
-/
structure EndpointCommutatorNoEscapeObligation
    (escapeMass microstructureLeak frequencyLeak residualFloor
      endpointDefect : Real) : Prop where
  escape_mass_nonnegative : 0 ≤ escapeMass
  microstructure_leak_nonnegative : 0 ≤ microstructureLeak
  frequency_leak_nonnegative : 0 ≤ frequencyLeak
  residual_floor_nonnegative : 0 ≤ residualFloor
  escape_charged_to_endpoint :
    escapeMass + microstructureLeak + frequencyLeak + residualFloor ≤
      endpointDefect

/--
Strong-tail compactness obligation for the endpoint commutator channel.

This is the compactness duty left by the critical-tail visibility response:
tail mass and tail oscillation must be controlled strongly enough to account
for the compact tail loss used in the endpoint defect bound.
-/
structure StrongTailCompactnessObligation
    (tailMass tailOscillation compactTailLoss compactnessModulus : Real) :
    Prop where
  tail_mass_nonnegative : 0 ≤ tailMass
  tail_oscillation_nonnegative : 0 ≤ tailOscillation
  compact_tail_loss_nonnegative : 0 ≤ compactTailLoss
  compactness_modulus_nonnegative : 0 ≤ compactnessModulus
  tail_strongly_compact : tailMass + tailOscillation ≤ compactnessModulus
  compactness_pays_tail_loss : compactTailLoss ≤ compactnessModulus

/--
Independent receipt for endpoint commutator visibility.

The receipt names the algebraic consequence of the three endpoint surfaces:
visible commutator defect, no-escape charging, and strong-tail compactness. It
does not assert a strict source subratio and does not define visibility by a
residual subtraction formula.
-/
structure EndpointCommutatorVisibilityReceipt
    (endpointDefect commutatorResidual compactTailLoss
      escapeMass microstructureLeak frequencyLeak residualFloor
      tailMass tailOscillation compactnessModulus : Real) : Prop where
  defect_visibility :
    EndpointCommutatorDefectVisibility
      endpointDefect commutatorResidual compactTailLoss
  no_escape :
    EndpointCommutatorNoEscapeObligation
      escapeMass microstructureLeak frequencyLeak residualFloor endpointDefect
  strong_tail_compactness :
    StrongTailCompactnessObligation
      tailMass tailOscillation compactTailLoss compactnessModulus
  named_escape_bound :
    escapeMass + microstructureLeak + frequencyLeak + residualFloor ≤
      commutatorResidual + compactTailLoss
  compactness_modulus_escape_bound :
    escapeMass + microstructureLeak + frequencyLeak + residualFloor ≤
      commutatorResidual + compactnessModulus

/--
Route-1 critical-tail visibility target.

This is the commutator-specific obligation package surfaced by the endpoint
tail critique. It includes the ordinary defect-budget target because the
commutator residual still has to enter the next tower step, but it does not
assume `defectBudgetStrictMarginCertificate`,
`defectBudgetSubcriticalityEstimate`, or a strict source-budget subratio.
-/
def route1CriticalTailVisibilityObligation
    (transportDefect localQuadratic advectedPressure commutatorResidual
      budget nextStep
      endpointDefect compactTailLoss
      escapeMass microstructureLeak frequencyLeak residualFloor
      tailMass tailOscillation compactnessModulus : Real) : Prop :=
  route1DefectBudgetTarget
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget nextStep ∧
    EndpointCommutatorDefectVisibility
      endpointDefect commutatorResidual compactTailLoss ∧
    EndpointCommutatorNoEscapeObligation
      escapeMass microstructureLeak frequencyLeak residualFloor
      endpointDefect ∧
    StrongTailCompactnessObligation
      tailMass tailOscillation compactTailLoss compactnessModulus

/--
The critical-tail visibility target still exposes the ordinary route-1
defect-budget target, but does not upgrade it to a strict ratio estimate.
-/
theorem route1DefectBudgetTarget_of_route1CriticalTailVisibilityObligation
    {transportDefect localQuadratic advectedPressure commutatorResidual
      budget nextStep
      endpointDefect compactTailLoss
      escapeMass microstructureLeak frequencyLeak residualFloor
      tailMass tailOscillation compactnessModulus : Real}
    (h :
      route1CriticalTailVisibilityObligation
        transportDefect localQuadratic advectedPressure commutatorResidual
        budget nextStep
        endpointDefect compactTailLoss
        escapeMass microstructureLeak frequencyLeak residualFloor
        tailMass tailOscillation compactnessModulus) :
    route1DefectBudgetTarget
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget nextStep := by
  exact h.1

/--
Endpoint visibility plus no-escape charges every named escape channel to the
commutator residual and strong-tail compactness loss.
-/
theorem endpoint_escape_bound_of_visibility_and_noEscape
    {endpointDefect commutatorResidual compactTailLoss
      escapeMass microstructureLeak frequencyLeak residualFloor : Real}
    (hvisible :
      EndpointCommutatorDefectVisibility
        endpointDefect commutatorResidual compactTailLoss)
    (hescape :
      EndpointCommutatorNoEscapeObligation
        escapeMass microstructureLeak frequencyLeak residualFloor
        endpointDefect) :
    escapeMass + microstructureLeak + frequencyLeak + residualFloor ≤
      commutatorResidual + compactTailLoss := by
  linarith [
    hescape.escape_charged_to_endpoint,
    hvisible.endpoint_visible]

/--
The three endpoint surfaces produce the independently named commutator
visibility receipt.
-/
theorem endpointCommutatorVisibilityReceipt_of_surfaces
    {endpointDefect commutatorResidual compactTailLoss
      escapeMass microstructureLeak frequencyLeak residualFloor
      tailMass tailOscillation compactnessModulus : Real}
    (hvisible :
      EndpointCommutatorDefectVisibility
        endpointDefect commutatorResidual compactTailLoss)
    (hescape :
      EndpointCommutatorNoEscapeObligation
        escapeMass microstructureLeak frequencyLeak residualFloor
        endpointDefect)
    (htail :
      StrongTailCompactnessObligation
        tailMass tailOscillation compactTailLoss compactnessModulus) :
    EndpointCommutatorVisibilityReceipt
      endpointDefect commutatorResidual compactTailLoss
      escapeMass microstructureLeak frequencyLeak residualFloor
      tailMass tailOscillation compactnessModulus := by
  have hnamed :
      escapeMass + microstructureLeak + frequencyLeak + residualFloor ≤
        commutatorResidual + compactTailLoss :=
    endpoint_escape_bound_of_visibility_and_noEscape hvisible hescape
  have hmodulus :
      escapeMass + microstructureLeak + frequencyLeak + residualFloor ≤
        commutatorResidual + compactnessModulus := by
    linarith [hnamed, htail.compactness_pays_tail_loss]
  exact ⟨hvisible, hescape, htail, hnamed, hmodulus⟩

/--
Projection of endpoint defect visibility from the named commutator visibility
receipt.
-/
theorem endpointCommutatorDefectVisibility_of_visibilityReceipt
    {endpointDefect commutatorResidual compactTailLoss
      escapeMass microstructureLeak frequencyLeak residualFloor
      tailMass tailOscillation compactnessModulus : Real}
    (h :
      EndpointCommutatorVisibilityReceipt
        endpointDefect commutatorResidual compactTailLoss
        escapeMass microstructureLeak frequencyLeak residualFloor
        tailMass tailOscillation compactnessModulus) :
    EndpointCommutatorDefectVisibility
      endpointDefect commutatorResidual compactTailLoss := by
  exact h.defect_visibility

/--
Projection of no-escape charging from the named commutator visibility receipt.
-/
theorem endpointCommutatorNoEscapeObligation_of_visibilityReceipt
    {endpointDefect commutatorResidual compactTailLoss
      escapeMass microstructureLeak frequencyLeak residualFloor
      tailMass tailOscillation compactnessModulus : Real}
    (h :
      EndpointCommutatorVisibilityReceipt
        endpointDefect commutatorResidual compactTailLoss
        escapeMass microstructureLeak frequencyLeak residualFloor
        tailMass tailOscillation compactnessModulus) :
    EndpointCommutatorNoEscapeObligation
      escapeMass microstructureLeak frequencyLeak residualFloor
      endpointDefect := by
  exact h.no_escape

/--
Projection of strong-tail compactness from the named commutator visibility
receipt.
-/
theorem strongTailCompactnessObligation_of_visibilityReceipt
    {endpointDefect commutatorResidual compactTailLoss
      escapeMass microstructureLeak frequencyLeak residualFloor
      tailMass tailOscillation compactnessModulus : Real}
    (h :
      EndpointCommutatorVisibilityReceipt
        endpointDefect commutatorResidual compactTailLoss
        escapeMass microstructureLeak frequencyLeak residualFloor
        tailMass tailOscillation compactnessModulus) :
    StrongTailCompactnessObligation
      tailMass tailOscillation compactTailLoss compactnessModulus := by
  exact h.strong_tail_compactness

/--
Algebra surface carried by the named receipt: all endpoint escape channels are
charged to the visible commutator residual plus the named compact-tail loss.
-/
theorem endpoint_escape_bound_of_visibilityReceipt
    {endpointDefect commutatorResidual compactTailLoss
      escapeMass microstructureLeak frequencyLeak residualFloor
      tailMass tailOscillation compactnessModulus : Real}
    (h :
      EndpointCommutatorVisibilityReceipt
        endpointDefect commutatorResidual compactTailLoss
        escapeMass microstructureLeak frequencyLeak residualFloor
        tailMass tailOscillation compactnessModulus) :
    escapeMass + microstructureLeak + frequencyLeak + residualFloor ≤
      commutatorResidual + compactTailLoss := by
  exact h.named_escape_bound

/--
Compactness-modulus algebra surface carried by the named receipt.
-/
theorem endpoint_escape_bound_by_compactnessModulus_of_visibilityReceipt
    {endpointDefect commutatorResidual compactTailLoss
      escapeMass microstructureLeak frequencyLeak residualFloor
      tailMass tailOscillation compactnessModulus : Real}
    (h :
      EndpointCommutatorVisibilityReceipt
        endpointDefect commutatorResidual compactTailLoss
        escapeMass microstructureLeak frequencyLeak residualFloor
        tailMass tailOscillation compactnessModulus) :
    escapeMass + microstructureLeak + frequencyLeak + residualFloor ≤
      commutatorResidual + compactnessModulus := by
  exact h.compactness_modulus_escape_bound

/--
The package-level endpoint escape bound: no source-budget strictness is used.
-/
theorem endpoint_escape_bound_of_route1CriticalTailVisibilityObligation
    {transportDefect localQuadratic advectedPressure commutatorResidual
      budget nextStep
      endpointDefect compactTailLoss
      escapeMass microstructureLeak frequencyLeak residualFloor
      tailMass tailOscillation compactnessModulus : Real}
    (h :
      route1CriticalTailVisibilityObligation
        transportDefect localQuadratic advectedPressure commutatorResidual
        budget nextStep
        endpointDefect compactTailLoss
        escapeMass microstructureLeak frequencyLeak residualFloor
        tailMass tailOscillation compactnessModulus) :
    escapeMass + microstructureLeak + frequencyLeak + residualFloor ≤
      commutatorResidual + compactTailLoss := by
  exact endpoint_escape_bound_of_visibility_and_noEscape h.2.1 h.2.2.1

/--
Projection of the named commutator visibility receipt from the route-1
critical-tail package.
-/
theorem endpointCommutatorVisibilityReceipt_of_route1CriticalTailVisibilityObligation
    {transportDefect localQuadratic advectedPressure commutatorResidual
      budget nextStep
      endpointDefect compactTailLoss
      escapeMass microstructureLeak frequencyLeak residualFloor
      tailMass tailOscillation compactnessModulus : Real}
    (h :
      route1CriticalTailVisibilityObligation
        transportDefect localQuadratic advectedPressure commutatorResidual
        budget nextStep
        endpointDefect compactTailLoss
        escapeMass microstructureLeak frequencyLeak residualFloor
        tailMass tailOscillation compactnessModulus) :
    EndpointCommutatorVisibilityReceipt
      endpointDefect commutatorResidual compactTailLoss
      escapeMass microstructureLeak frequencyLeak residualFloor
      tailMass tailOscillation compactnessModulus := by
  exact endpointCommutatorVisibilityReceipt_of_surfaces h.2.1 h.2.2.1 h.2.2.2

/--
Projection of the strong-tail compactness duty from the critical-tail
visibility package.
-/
theorem strongTailCompactnessObligation_of_route1CriticalTailVisibilityObligation
    {transportDefect localQuadratic advectedPressure commutatorResidual
      budget nextStep
      endpointDefect compactTailLoss
      escapeMass microstructureLeak frequencyLeak residualFloor
      tailMass tailOscillation compactnessModulus : Real}
    (h :
      route1CriticalTailVisibilityObligation
        transportDefect localQuadratic advectedPressure commutatorResidual
        budget nextStep
        endpointDefect compactTailLoss
        escapeMass microstructureLeak frequencyLeak residualFloor
        tailMass tailOscillation compactnessModulus) :
    StrongTailCompactnessObligation
      tailMass tailOscillation compactTailLoss compactnessModulus := by
  exact h.2.2.2

/--
Strict source-sum subcriticality pays an existential strict-margin route-1
target.

This is the source-facing version of the v17.24 scalar bridge: it does not
prove the analytic inequality, but it makes the exact remaining inequality
native to the pressure-transport budget decomposition.
-/
theorem exists_route1StrictMarginNextTarget_of_source_sum_strict_subcriticality
    {stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio : Real}
    (htransport :
      pressureL2TransportDefectObligation
        stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
        transportDefect localQuadratic advectedPressure commutatorResidual)
    (hbudget :
      route1DefectBudgetTarget
        transportDefect localQuadratic advectedPressure commutatorResidual budget nextStep)
    (hr0 : 0 ≤ ratio)
    (hr1 : ratio < 1)
    (hc : 0 ≤ currentStep)
    (hstrict :
      transportDefect + localQuadratic + advectedPressure + commutatorResidual <
        ratio * currentStep) :
    ∃ margin : Real,
      route1StrictMarginNextTarget
        stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
        transportDefect localQuadratic advectedPressure commutatorResidual
        budget currentStep nextStep ratio margin := by
  rcases hbudget with ⟨htransportBudget, hfeed⟩
  rcases htransportBudget with ⟨ht, hl, ha, hcomm, hsum⟩
  rcases hfeed with ⟨hb, hn, hnext⟩
  have hbudgetStrict : budget < ratio * currentStep := by
    simpa [hsum] using hstrict
  rcases exists_budgetContractionSlack_of_strict_budget_subcriticality
      hb hc hbudgetStrict with
    ⟨budgetMargin, hbudgetMargin, hbudgetSlack⟩
  refine ⟨min ((1 - ratio) / 2) budgetMargin, htransport, ?_, ?_⟩
  · exact ⟨⟨ht, hl, ha, hcomm, hsum⟩, ⟨hb, hn, hnext⟩⟩
  · exact
      defectBudgetStrictMarginCertificate_of_strict_ratio_and_budget_slack
        hr0 hr1 hbudgetMargin hbudgetSlack

/--
The strict-margin route-1 target pays the previous irreducible route-1 target.
-/
theorem route1IrreducibleNextTarget_of_route1StrictMarginNextTarget
    {stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio margin : Real}
    (h :
      route1StrictMarginNextTarget
        stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
        transportDefect localQuadratic advectedPressure commutatorResidual
        budget currentStep nextStep ratio margin) :
    route1IrreducibleNextTarget
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio := by
  rcases h with ⟨htransport, hbudget, hmargin⟩
  exact ⟨htransport, hbudget,
    defectBudgetSubcriticalityEstimate_of_strictMarginCertificate hmargin⟩

/--
The strict-margin route-1 target pays the exact-next route-1 target.
-/
theorem route1ExactNextTarget_of_route1StrictMarginNextTarget
    {stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio margin : Real}
    (h :
      route1StrictMarginNextTarget
        stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
        transportDefect localQuadratic advectedPressure commutatorResidual
        budget currentStep nextStep ratio margin) :
    route1ExactNextTarget
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio := by
  rcases h with ⟨htransport, hbudget, hmargin⟩
  refine ⟨htransport, hbudget, ?_⟩
  exact budgetFacingContractionTarget_of_strictMarginCertificate hmargin hbudget.2

/--
If the irreducible route-1 target is paid, then the exact-next-target object is
already available.
-/
theorem route1ExactNextTarget_of_route1IrreducibleNextTarget
    {stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio : Real}
    (h :
      route1IrreducibleNextTarget
        stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
        transportDefect localQuadratic advectedPressure commutatorResidual
        budget currentStep nextStep ratio) :
    route1ExactNextTarget
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio := by
  rcases h with ⟨htransport, hbudget, hsub⟩
  refine ⟨htransport, hbudget, ?_⟩
  exact budgetFacingContractionTarget_of_subcriticality hsub hbudget.2

end ZtareProofs
