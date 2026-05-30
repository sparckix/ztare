import Mathlib.Tactic
import ZtareProofs.ns_commutator_cutoff_penalty

namespace ZtareProofs

/-!
`ns_global_tail_coercivity_bridge` is the positive companion to the cutoff
penalty obstruction.

The proof-search substrate identified the negative claim first:
localizing Calderon commutators incurs inverse-width penalties, so the tower is
not primary without a tail offset.

This file names the positive bridge the reranking points toward:

1. establish enough far-field decay / coercivity to offset localization cost;
2. only then reopen the commutator tower as a viable downstream route.
-/

/-- Far-field decay strength available from the global pressure-tail route. -/
abbrev GlobalTailDecayStrength := Real

/-- Residual transition-layer burden left after tail compensation. -/
abbrev ResidualTransitionBurden := Real

/--
Global tail coercivity bridge: the tail bootstrap pays enough to dominate the
inverse-width cutoff penalty with positive margin.
-/
def globalTailCoercivityBridge
    (δ penalty K tailDecay margin : Real) : Prop :=
  inverseCutoffWidthPenalty δ penalty K ∧
    tailDecayOffsetsCutoffPenalty tailDecay penalty margin

/--
After the tail bridge lands, the remaining transition burden is subcritical.
-/
def residualTransitionBurdenSubcritical
    (tailDecay penalty residual : Real) : Prop :=
  0 ≤ residual ∧
    residual = max (penalty - tailDecay) 0

/--
Positive route-2 target: pay the global tail bridge and reduce the remaining
transition burden to a subcritical residual.
-/
def ns_global_tail_coercivity_bridge
    (δ penalty K tailDecay margin residual : Real) : Prop :=
  globalTailCoercivityBridge δ penalty K tailDecay margin ∧
    residualTransitionBurdenSubcritical tailDecay penalty residual

/--
If the tail bridge is paid, then the negative reranking obstruction is removed.
-/
theorem tail_bridge_removes_cutoff_obstruction
    {δ penalty K tailDecay margin residual : Real}
    (h :
      ns_global_tail_coercivity_bridge
        δ penalty K tailDecay margin residual) :
    inverseCutoffWidthPenalty δ penalty K := by
  exact h.1.1

/--
This is the exact route handoff encoded by the 89-point substrate result:
route `2` is not the end of the story; it is the coercive antecedent that
reopens route `1`.
-/
def route2ReopensRoute1
    (δ penalty K tailDecay margin residual budget currentStep ratio : Real) : Prop :=
  ns_global_tail_coercivity_bridge δ penalty K tailDecay margin residual ∧
    defectBudgetSubcriticalityEstimate budget currentStep ratio

/--
Strict-margin route-2 handoff into route 1.

The tail/coercivity margin and the route-1 budget margin are deliberately
separate variables: the former offsets cutoff localization, while the latter is
the unpaid scalar contraction certificate.
-/
def route2ReopensRoute1WithStrictMargin
    (δ penalty K tailDecay margin residual
      budget currentStep ratio budgetMargin : Real) : Prop :=
  ns_global_tail_coercivity_bridge δ penalty K tailDecay margin residual ∧
    defectBudgetStrictMarginCertificate budget currentStep ratio budgetMargin

/--
The strict-margin route-2 handoff pays the previous route-2 handoff.
-/
theorem route2ReopensRoute1_of_strictMargin
    {δ penalty K tailDecay margin residual
      budget currentStep ratio budgetMargin : Real}
    (h :
      route2ReopensRoute1WithStrictMargin
        δ penalty K tailDecay margin residual
        budget currentStep ratio budgetMargin) :
    route2ReopensRoute1
      δ penalty K tailDecay margin residual budget currentStep ratio := by
  exact ⟨h.1,
    defectBudgetSubcriticalityEstimate_of_strictMarginCertificate h.2⟩

/--
Anti-laundering falsifier: a paid global-tail/coercivity margin does not by
itself pay the route-1 strict budget margin certificate.

The witness has the cutoff/tail bridge fully paid, while the route-1 budget
slack fails. Any theorem that tries to reuse the cutoff margin directly as
`budgetMargin` must add a real coupling hypothesis.
-/
theorem globalTailCoercivityBridge_does_not_imply_strictBudgetMargin :
    ∃ δ penalty K tailDecay tailMargin residual
      budget currentStep ratio budgetMargin : Real,
      ns_global_tail_coercivity_bridge δ penalty K tailDecay tailMargin residual ∧
        0 < budgetMargin ∧
        0 ≤ budget ∧
        0 ≤ currentStep ∧
        0 ≤ ratio ∧
        ¬ defectBudgetStrictMarginCertificate budget currentStep ratio budgetMargin := by
  refine ⟨1, 0, 0, 1, 1, 0, 2, 1, (1 / 2), 1, ?_⟩
  norm_num [ns_global_tail_coercivity_bridge, globalTailCoercivityBridge,
    inverseCutoffWidthPenalty, tailDecayOffsetsCutoffPenalty,
    residualTransitionBurdenSubcritical, defectBudgetStrictMarginCertificate]

end ZtareProofs
